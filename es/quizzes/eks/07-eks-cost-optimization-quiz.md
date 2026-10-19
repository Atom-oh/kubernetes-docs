# Cuestionario de optimización de costos de Amazon EKS

> **Última actualización**: 16 de octubre de 2026

Los ejemplos son alternativas de configuración independientes; no son implementaciones ejecutadas ni ahorros medidos. Integre los cambios en el recurso existente que sea de su propiedad; no aplique todos los ejemplos sucesivamente a la misma carga de trabajo. Sustituya las imágenes de aplicaciones de marcador de posición y los hooks propiedad de la aplicación, compruebe la cuenta, el contexto y la Región, así como la compatibilidad de los controladores, y pruebe el comportamiento antes de usarlo en operaciones.

Este cuestionario evalúa su comprensión de las estrategias, herramientas y prácticas recomendadas para optimizar los costos en clústeres de Amazon EKS.

## Resumen del cuestionario
- Optimización de los recursos de cómputo
- Optimización de los costos de almacenamiento
- Optimización de los costos de redes
- Optimización de los costos de administración de clústeres
- Supervisión y análisis de costos
- Herramientas y prácticas recomendadas para la optimización de costos

## Preguntas de opción múltiple

### 1. ¿Cuál es la estrategia más eficaz para optimizar los costos de cómputo en Amazon EKS?

- A. Usar siempre los tipos de instancia más grandes
- B. Usar únicamente instancias bajo demanda para todas las cargas de trabajo
- C. Combinar instancias Spot, ajuste de tamaño y escalado automático
- D. Consolidar todas las cargas de trabajo en un solo grupo de nodos
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Combinar instancias Spot, ajuste de tamaño y escalado automático**

**Explicación:**
La estrategia más eficaz para optimizar los costos de cómputo en Amazon EKS consiste en combinar instancias Spot, ajuste de tamaño y escalado automático. Use Spot solo cuando la carga de trabajo tolere interrupciones y haya capacidad disponible; compruebe los ahorros en relación con los SLO de la carga de trabajo. Ni esta combinación ni un descuento máximo anunciado garantizan un menor costo o un rendimiento sin cambios.

**Estrategias clave para optimizar el cómputo:**

1. **Uso de instancias Spot**:
   - Ahorros de hasta un 90 % en comparación con las instancias bajo demanda
   - Adecuadas para cargas de trabajo tolerantes a fallos
   - Implemente mecanismos para gestionar interrupciones

2. **Ajuste de tamaño**:
   - Seleccione las instancias según el uso real de recursos
   - Elimine los recursos aprovisionados en exceso
   - Optimice las solicitudes y los límites de recursos

3. **Implementación del escalado automático**:
   - Escalado a nivel de nodo mediante Cluster Autoscaler o Karpenter
   - Escalado a nivel de Pod mediante Horizontal Pod Autoscaler
   - Ajuste de recursos según la demanda

NodePool/EC2NodeClass requieren un controlador Karpenter compatible y CRD instalados, permisos de IAM con alcance limitado para el controlador, un rol de nodo, recursos de detección y una cola de interrupciones. EKS 1.36 requiere Karpenter >=1.13 en la matriz actual. `al2023@latest` es un selector cambiante: revise las AMI resueltas y fije un alias/AMI probado para un lanzamiento controlado. Las listas de instancias y los límites de capacidad son ilustrativos y no constituyen un tope de gasto. Los grupos de nodos administrados gestionan su propia ruta de interrupción; evite un segundo controlador de interrupciones para los nodos administrados por Karpenter.

HPA requiere métricas de recursos y solicitudes; cuando se usan objetivos de CPU y memoria, selecciona el mayor número deseado de réplicas. El VPA siguiente está en modo **Off** para ofrecer recomendaciones sin cambiar esos denominadores. `Auto` está obsoleto y se recomienda usar modos explícitos como `Recreate`; los cambios automáticos de CPU/memoria deben coordinarse con HPA. Un hook preStop consume el período de gracia de terminación y no puede garantizar que se cumpla el plazo de Spot ni que la limpieza termine correctamente.

**Métodos de implementación:**

1. **Crear un grupo de nodos con instancias Spot**:
   ```bash
   # Create Spot Instance node group using eksctl
   eksctl create nodegroup \
     --cluster my-cluster \
     --region us-west-2 \
     --managed \
     --name spot-ng \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --spot
   ```

2. **Implementar y configurar Karpenter**:
   ```yaml
   # Karpenter NodePool
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m4.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   # Karpenter NodeClass
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Configurar Horizontal Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Configurar Vertical Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**Estrategias de optimización según el tipo de carga de trabajo:**

1. **Aplicaciones sin estado**:
   - Dar prioridad a las instancias Spot
   - Implementar escalado horizontal
   - Implementar en varias zonas de disponibilidad

2. **Aplicaciones con estado**:
   - Combinar instancias bajo demanda y Spot
   - Seleccionar los tipos de instancia adecuados
   - Equilibrar el rendimiento y el costo del almacenamiento

3. **Trabajos por lotes**:
   - Maximizar el uso de instancias Spot
   - Implementar mecanismos para reintentar trabajos
   - Programar dentro de los plazos y según la disponibilidad de capacidad; no hay una tarifa general de instancias bajo demanda fuera de las horas punta

**Prácticas recomendadas:**

1. **Optimizar las solicitudes y los límites de recursos**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         containers:
         - name: web-app
           image: web-app:1.0
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **Optimizar la afinidad de nodos y la distribución de Pods**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         affinity:
           nodeAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 1
               preference:
                 matchExpressions:
                 - key: node.kubernetes.io/instance-type
                   operator: In
                   values:
                   - m5.large
                   - m5a.large
           podAntiAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               podAffinityTerm:
                 labelSelector:
                   matchExpressions:
                   - key: app
                     operator: In
                     values:
                     - web-app
                 topologyKey: kubernetes.io/hostname
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

3. **Gestionar las interrupciones de instancias Spot**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         terminationGracePeriodSeconds: 60
         containers:
         - name: web-app
           image: web-app:1.0
           lifecycle:
             preStop:
               exec:
                 command:
                 - /bin/sh
                 - -c
                 - sleep 10; /app/cleanup.sh
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

**Consideraciones adicionales de implementación**

- Una configuración de eksctl puede definir un grupo On-Demand para las cargas de trabajo del sistema y un grupo Spot diversificado para las aplicaciones. Las etiquetas por sí solas no aíslan las cargas de trabajo. Configure deliberadamente los selectores y las tolerancias; no aplique taints a los únicos nodos de arranque antes de que puedan ejecutarse los controladores del sistema.
- En un módulo de Terraform existente, `aws_eks_node_group` puede establecer `capacity_type = "SPOT"` y `scaling_config`. El clúster, el rol de IAM de los nodos y sus políticas, las subredes y el proveedor deben estar definidos de antemano. Coordine quién administra `desired_size` con el autoscaler.
- Las etiquetas de los grupos de nodos de EKS no sustituyen las etiquetas de detección de los **ASG reales** que usa Cluster Autoscaler. Inspeccione los ASG y quién administra sus etiquetas actuales antes de modificarlas. Asocie la política del autoscaler a una identidad de controlador dedicada; los permisos de complementos del rol de nodo no son la identidad prevista.
- Mantenga separadas las acciones de lectura/detección de AWS y las dos acciones de escritura de escalado. Restrinja `autoscaling:SetDesiredCapacity` y `autoscaling:TerminateInstanceInAutoScalingGroup` a los ASG que tengan las etiquetas de propiedad de clúster y habilitación revisadas, como en la [política oficial de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html).

El siguiente fragmento de eksctl agrega grupos de nodos a un clúster existente. Compruebe las subredes privadas del propietario, las políticas de IAM de los nodos y las etiquetas existentes de los grupos/ASG; no es una receta independiente para crear un clúster.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: system-ng
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 4
  labels:
    workload-type: system
  privateNetworking: true
- name: app-spot-ng
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m4.large
  spot: true
  desiredCapacity: 3
  minSize: 1
  maxSize: 10
  labels:
    workload-type: application
  privateNetworking: true
```

El fragmento de Terraform presupone que los recursos con nombre del clúster/rol de nodo, la variable de subredes privadas y el proveedor ya existen en el módulo propietario. La política de IAM debe estar asociada a la identidad de controlador dedicada.

```hcl
# Spot managed node group
resource "aws_eks_node_group" "spot" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "spot-ng"
  node_role_arn   = aws_iam_role.node_role.arn
  subnet_ids      = var.private_subnet_ids

  capacity_type  = "SPOT"
  instance_types = ["m5.large", "m5a.large", "m5d.large", "m4.large"]

  scaling_config {
    desired_size = 3
    min_size     = 1
    max_size     = 10
  }

  labels = {
    "workload-type" = "application"
  }

  tags = {
    Team        = "platform"
    Environment = "development"
  }
}

# Cluster Autoscaler IAM policy
resource "aws_iam_policy" "cluster_autoscaler" {
  name        = "EKSClusterAutoscalerPolicy"
  description = "Policy for Cluster Autoscaler"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeTags",
          "autoscaling:DescribeScalingActivities",
          "ec2:DescribeImages",
          "ec2:DescribeInstanceTypes",
          "ec2:GetInstanceTypesFromInstanceRequirements",
          "eks:DescribeNodegroup",
          "ec2:DescribeLaunchTemplateVersions"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup"
        ],
        Resource = "*",
        Condition = {
          StringEquals = {
            "aws:ResourceTag/k8s.io/cluster-autoscaler/enabled"                      = "true",
            "aws:ResourceTag/k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
          }
        }
      }
    ]
  })
}
```

Problemas con las otras opciones:
- **A. Usar siempre los tipos de instancia más grandes**: Esto provoca un aprovisionamiento excesivo, con costos innecesarios, y puede no ajustarse a los requisitos de la carga de trabajo.
- **B. Usar únicamente instancias bajo demanda para todas las cargas de trabajo**: Las instancias bajo demanda cuestan más que las Spot y muchas cargas de trabajo pueden ejecutarse eficazmente en instancias Spot.
- **D. Consolidar todas las cargas de trabajo en un solo grupo de nodos**: Esto dificulta satisfacer los distintos requisitos de las cargas de trabajo, carece de aislamiento de recursos y complica la asignación y optimización de costos.
</details>

### 2. ¿Cuál es el enfoque más eficaz para optimizar los costos de almacenamiento en Amazon EKS?

- A. Usar el tipo de almacenamiento más barato para todas las cargas de trabajo
- B. Migrar todos los datos a S3
- C. Elegir tipos de almacenamiento que se ajusten a los requisitos de las cargas de trabajo e implementar la administración del ciclo de vida
- D. Minimizar el tamaño de todos los volúmenes
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Elegir tipos de almacenamiento que se ajusten a los requisitos de las cargas de trabajo e implementar la administración del ciclo de vida**

**Explicación:**
El enfoque más eficaz para optimizar los costos de almacenamiento en Amazon EKS consiste en elegir tipos de almacenamiento que se ajusten a los requisitos de las cargas de trabajo e implementar la administración del ciclo de vida. Este enfoque minimiza los costos sin dejar de cumplir los requisitos de rendimiento y aprovecha los niveles de almacenamiento adecuados según el valor de los datos y los patrones de acceso.

**Estrategias clave para optimizar el almacenamiento:**

1. **Elegir los tipos de almacenamiento adecuados para las cargas de trabajo**:
   - Requisitos de alto rendimiento: io2, gp3 (EBS)
   - Requisitos de acceso compartido: EFS
   - Procesamiento de datos a gran escala: FSx for Lustre
   - Datos de archivo: S3, S3 Glacier

2. **Administración del ciclo de vida del almacenamiento**:
   - Datos a los que se accede con frecuencia: almacenamiento de alto rendimiento
   - Datos a los que se accede ocasionalmente: almacenamiento estándar
   - Datos a los que se accede rara vez: almacenamiento de archivo de bajo costo

3. **Administración eficiente de volúmenes**:
   - Establecer tamaños de volumen adecuados
   - Identificar y eliminar volúmenes sin uso
   - Administrar los ciclos de vida de las instantáneas

Los ejemplos de StorageClass requieren controladores CSI instalados y una configuración correcta de IAM/KMS/topología. `WaitForFirstConsumer` coordina el aprovisionamiento de EBS con la programación; `Retain` deja los volúmenes liberados facturándose hasta que el propietario se ocupe de ellos. Los PVC vinculados no pueden cambiar de clase ni reducirse directamente. La modificación del tipo de volumen compatible o la creación de una instantánea/restauración requieren una migración revisada por el propietario y una prueba de restauración. Auto Mode usa un aprovisionador de EBS distinto; no lo sustituya silenciosamente en los ejemplos de CSI estándar.

`create-file-system` no tiene una opción `--lifecycle-policies`. Use `put-lifecycle-configuration` en el sistema de archivos existente y conserve la matriz completa de políticas deseada, como se muestra a continuación. Las transiciones de S3 también requieren revisar la duración/tamaño mínimos, los costos de solicitud, el control de versiones y la latencia de recuperación; al reemplazar una configuración de ciclo de vida, conserve las reglas no relacionadas.

**Métodos de implementación:**

1. **Optimización de volúmenes de EBS**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: '3000'
     throughput: '125'
     encrypted: 'true'
   allowVolumeExpansion: true
   volumeBindingMode: WaitForFirstConsumer
   reclaimPolicy: Retain
   ```

2. **Administración del ciclo de vida de EFS**:
   ```bash
   set -euo pipefail
   : "${AWS_REGION:?Set the reviewed Region}"
   : "${FILE_SYSTEM_ID:?Set the existing reviewed EFS filesystem ID}"
   aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" --query LifecyclePolicies --output json \
     > efs-lifecycle-policies.json
   # Edit the exported array; an IA entry is {"TransitionToIA":"AFTER_30_DAYS"}.
   # Preserve required Archive/return-to-primary entries before submitting the whole policy.
   aws efs put-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" \
     --lifecycle-policies file://efs-lifecycle-policies.json
   ```

3. **Política del ciclo de vida de S3**:
   ```json
   {
     "Rules": [
       {
         "ID": "Move to IA after 30 days, Glacier after 90 days",
         "Status": "Enabled",
         "Transitions": [
           {
             "Days": 30,
             "StorageClass": "STANDARD_IA"
           },
           {
             "Days": 90,
             "StorageClass": "GLACIER"
           }
         ],
         "Expiration": {
           "Days": 365
         },
         "Filter": {
           "Prefix": "eks-backups/"
         }
       }
     ]
   }
   ```

4. **Administración del ciclo de vida de instantáneas de EBS**:
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

**Instantáneas programadas y revisión del almacenamiento**

La programación de instantáneas siguiente está suspendida hasta que el propietario confirme el PVC existente `team-a/database-data`, el controlador CSI estándar de EBS, el controlador/las CRD de instantáneas y la clase `ebs-snapshot`. La plantilla montada usa `generateName` para evitar conflictos con un nombre fijo. El Role permite crear instantáneas en este namespace; no restringe el campo del PVC de origen. La coherencia/aplicación en quiescencia y la verificación de restauraciones son responsabilidades independientes. Un Job completado correctamente confirma la creación mediante la API, no que la instantánea esté lista; supervise `readyToUse` y los errores por separado. Los límites del historial de Jobs **no** hacen que caduquen los VolumeSnapshots ni las instantáneas de EBS. Defina la retención y quién es responsable de la recuperación antes de habilitar la programación; `deletionPolicy: Delete` elimina la instantánea subyacente cuando se elimina su instantánea de Kubernetes.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: snapshot-creator
  namespace: team-a
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: snapshot-creator
  namespace: team-a
rules:
- apiGroups: ["snapshot.storage.k8s.io"]
  resources: ["volumesnapshots"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: snapshot-creator
  namespace: team-a
subjects:
- kind: ServiceAccount
  name: snapshot-creator
  namespace: team-a
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: snapshot-creator
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: snapshot-templates
  namespace: team-a
data:
  snapshot.yaml: |
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      generateName: database-data-
      namespace: team-a
    spec:
      volumeSnapshotClassName: ebs-snapshot
      source:
        persistentVolumeClaimName: database-data
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: volume-snapshot
  namespace: team-a
spec:
  suspend: true
  schedule: "0 1 * * *"
  timeZone: Etc/UTC
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 1800
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: snapshot-creator
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 65532
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: snapshot-creator
            image: registry.k8s.io/kubectl:v1.36.2
            command: ["kubectl"]
            args: ["create", "-f", "/snapshots/snapshot.yaml", "--namespace=team-a"]
            env:
            - name: HOME
              value: /tmp
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop: ["ALL"]
            resources:
              requests:
                cpu: 10m
                memory: 32Mi
              limits:
                memory: 128Mi
            volumeMounts:
            - name: snapshots
              mountPath: /snapshots
              readOnly: true
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: snapshots
            configMap:
              name: snapshot-templates
          - name: tmp
            emptyDir: {}
```

Adapte el almacenamiento a la semántica de acceso y los objetivos de recuperación: las bases de datos pueden necesitar IOPS de io2/gp3, el contenido web compartido puede usar EFS, los registros y archivos suelen encajar en S3, y las cargas de analítica/IA pueden requerir FSx for Lustre o el rendimiento de EBS. Los niveles caliente/templado/frío son un ejemplo de clasificación, no una canalización automática de migración de EBS→EFS→S3. Prepare por separado las clases `efs-standard`/`ebs-io2` a las que se hace referencia. Una solicitud de PVC de EFS de `100Gi` no impone una cuota al sistema de archivos ni compra esa capacidad, y las etiquetas de PVC no se convierten automáticamente en etiquetas de facturación de AWS.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: hot-data
  namespace: team-a
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: warm-data
  namespace: team-a
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-standard
  resources:
    requests:
      storage: 100Gi
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-data
  labels:
    app: database
    environment: production
    cost-center: cc-123
  namespace: team-a
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-io2
  resources:
    requests:
      storage: 100Gi
```

El siguiente fragmento de Terraform requiere proveedores configurados e identidad del solicitante existentes, así como la propiedad de los recursos revisada. Los destinos de montaje, el acceso de red/IAM, las copias de seguridad de las aplicaciones y la retención son requisitos previos independientes; no es una implementación completa de almacenamiento de producción.

```hcl
# Standard EBS CSI gp3 StorageClass
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "ebs-gp3"
  }
  storage_provisioner = "ebs.csi.aws.com"
  parameters = {
    type       = "gp3"
    iops       = "3000"
    throughput = "125"
    encrypted  = "true"
  }
  allow_volume_expansion = true
  volume_binding_mode    = "WaitForFirstConsumer"
  reclaim_policy         = "Retain"
}

# Encrypted EFS filesystem
resource "aws_efs_file_system" "eks_efs" {
  creation_token = "eks-efs"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name = "eks-efs"
  }
}

# S3 bucket and lifecycle policy
resource "aws_s3_bucket" "eks_data" {
  bucket = "eks-data-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "eks-data"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "eks_data_lifecycle" {
  bucket = aws_s3_bucket.eks_data.id

  rule {
    id     = "archive-rule"
    status = "Enabled"

    filter {
      prefix = "eks-backups/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}
```

**Inventario de solo lectura de posibles PVC sin referencias**

Guarde el código Python siguiente como `unreferenced_pvcs.py` y use los comandos con contexto/namespace explícitos. Informa de los PVC Bound a los que no hacen referencia los Pods de la instantánea actual proporcionada, comparando `(namespace, name)` y manejando volúmenes que no son PVC. Kubernetes no proporciona una anotación estándar `pv_used`. Las listas de instantáneas no son atómicas y omiten futuros consumidores de controladores o de carga reducida, trabajos pendientes y requisitos de copia de seguridad/recuperación. Este resultado no justifica ninguna decisión de eliminación. Para posibles recursos de EBS, use la consulta limitada por cuenta/etiqueta de la [pregunta 6 de EKS06](06-eks-monitoring-logging-quiz.md); `available` significa sin conexión, no sin uso.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Select the reviewed cluster context}"
: "${KUBE_NAMESPACE:?Select the reviewed namespace}"
kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
  get pvc --chunk-size=500 -o json > pvcs.json
kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
  get pods --chunk-size=500 -o json > pods.json
python3 unreferenced_pvcs.py
```

```python
import json
from pathlib import Path


def unreferenced_claims(claims, pods):
    referenced = set()
    for pod in pods["items"]:
        namespace = pod["metadata"]["namespace"]
        for volume in pod.get("spec", {}).get("volumes") or []:
            claim = volume.get("persistentVolumeClaim")
            if claim:
                referenced.add((namespace, claim["claimName"]))
    result = []
    for claim in claims["items"]:
        metadata = claim["metadata"]
        identity = (metadata["namespace"], metadata["name"])
        if claim.get("status", {}).get("phase") != "Bound" or identity in referenced:
            continue
        spec = claim.get("spec", {})
        result.append({
            "namespace": identity[0],
            "name": identity[1],
            "storageClass": spec.get("storageClassName"),
            "requested": ((spec.get("resources") or {}).get("requests") or {}).get("storage"),
            "meaning": "not referenced by the supplied current Pod snapshot; review required",
        })
    return result


if __name__ == "__main__":
    claims = json.loads(Path("pvcs.json").read_text())
    pods = json.loads(Path("pods.json").read_text())
    print(json.dumps(unreferenced_claims(claims, pods), indent=2))
```

Problemas con las otras opciones:
- **A. Usar el tipo de almacenamiento más barato para todas las cargas de trabajo**: El almacenamiento más barato puede no cumplir los requisitos de rendimiento, lo que podría degradar el rendimiento de las aplicaciones y afectar al negocio.
- **B. Migrar todos los datos a S3**: S3 es adecuado para algunos tipos de datos, pero no para cargas de trabajo sensibles a la latencia ni para aplicaciones que requieren almacenamiento en bloques.
- **D. Minimizar el tamaño de todos los volúmenes**: Reducir demasiado el tamaño de los volúmenes puede provocar falta de espacio, y en algunos tipos de volumen (por ejemplo, gp2) el rendimiento está determinado por el tamaño.
</details>

### 3. ¿Cuál es la estrategia más eficaz para optimizar los costos de redes en Amazon EKS?

- A. Usar el ancho de banda de red más caro para todo el tráfico
- B. Ubicar todos los servicios en una sola zona de disponibilidad
- C. Optimizar los patrones de tráfico, minimizar los costos de transferencia de datos y utilizar VPC endpoints
- D. Bloquear todo el tráfico de red
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Optimizar los patrones de tráfico, minimizar los costos de transferencia de datos y utilizar VPC endpoints**

**Explicación:**
La estrategia más eficaz para optimizar los costos de redes en Amazon EKS consiste en optimizar los patrones de tráfico, minimizar los costos de transferencia de datos y utilizar VPC endpoints. Este enfoque mejora la eficiencia del tráfico de red y reduce los costos innecesarios teniendo en cuenta los modelos de costos de red de AWS.

**Estrategias clave para optimizar los costos de redes:**

1. **Optimizar los patrones de tráfico**:
   - Minimizar el tráfico entre zonas de disponibilidad
   - Minimizar el tráfico entre regiones
   - Implementar enrutamiento con conciencia de localidad

2. **Minimizar los costos de transferencia de datos**:
   - Usar compresión y formatos de datos eficientes
   - Implementar estrategias de almacenamiento en caché
   - Eliminar transferencias de datos innecesarias

3. **Utilizar VPC endpoints**:
   - Conexiones privadas a los servicios de AWS
   - Evitar las puertas de enlace de Internet
   - Reducir los costos de transferencia de datos

La distribución de la topología controla la ubicación; no selecciona los endpoints que usa el tráfico de Service. Se eliminó `spec.topologyKeys`. El ejemplo usa `trafficDistribution: PreferSameZone` (estable en Kubernetes 1.35+) con alternativa, no garantiza que no haya tráfico entre AZ. Compruebe el comportamiento real del proxy/CNI y las restricciones de disponibilidad.

Los gateway endpoints de S3/DynamoDB tienen precios distintos de los interface endpoints. Para extraer imágenes de ECR se necesitan conectividad con `ecr.api`, `ecr.dkr` y S3, DNS privado y reglas de entrada del grupo de seguridad del endpoint en TCP 443 desde los nodos/Pods previstos. La CLI muestra un interface endpoint; aprovisione también su contraparte DKR, como se hace en el fragmento de Terraform siguiente. Revise las políticas de los endpoints y el modelo real de tráfico/costos regionales; que algo sea «privado» no significa que sea gratis.

**Métodos de implementación:**

1. **Ubicación de Pods según la zona de disponibilidad**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 6
     template:
       spec:
         topologySpreadConstraints:
         - maxSkew: 1
           topologyKey: topology.kubernetes.io/zone
           whenUnsatisfiable: DoNotSchedule
           labelSelector:
             matchLabels:
               app: web-app
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **Enrutamiento de Service según la topología**:
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: web-app
   spec:
     selector:
       app: web-app
     ports:
     - port: 80
       targetPort: 8080
     trafficDistribution: PreferSameZone
   ```

3. **Configuración de VPC endpoints**:
   ```bash
   # Create S3 VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.s3 \
     --route-table-ids rtb-12345678

   # Create DynamoDB VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.dynamodb \
     --route-table-ids rtb-12345678

   # Create ECR API VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.api \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 subnet-87654321 \
     --security-group-ids sg-12345678 \
     --private-dns-enabled
   ```

4. **Enrutamiento por localidad con Istio**:
   ```yaml
   apiVersion: networking.istio.io/v1
   kind: DestinationRule
   metadata:
     name: web-app
   spec:
     host: web-app
     trafficPolicy:
       loadBalancer:
         simple: LEAST_REQUEST
         localityLbSetting:
           enabled: true
       outlierDetection:
         consecutive5xxErrors: 5
         interval: 5s
         baseEjectionTime: 30s
   ```

La conmutación por error según la localidad de Istio necesita información de localidad de los endpoints y detección de valores atípicos. `failover.from/to` identifica **Regiones**, así que no es correcto poner ahí nombres de AZ. La DestinationRule anterior usa las prioridades de localidad predeterminadas (misma zona antes que otras zonas/Regiones) con detección de valores atípicos; los umbrales de expulsión del ejemplo deben probarse con la carga de trabajo. Es una alternativa independiente a la distribución del tráfico de Service de kube-proxy, y no se necesita una malla solo para reducir los costos de transferencia.



**Ejemplos adicionales de enrutamiento, endpoints y facturación**

La NetworkPolicy permite el tráfico frontend→API→base de datos dentro del mismo namespace, además de una ruta de Deployment estándar de CoreDNS. Añada otras dependencias necesarias y compruebe que el CNI aplica las políticas. El DNS local a los nodos de Auto Mode u otra ruta de resolución requiere su propio permiso adecuado. Ajuste los selectores a las etiquetas administradas reales.

VirtualService evalúa primero la primera regla coincidente, por lo que la coincidencia premium precede a la regla general y se definen los subconjuntos correspondientes en DestinationRule. Las cargas de trabajo deben tener esas etiquetas de versión. Un encabezado proporcionado por el cliente no demuestra que tenga derecho de acceso; imponga la autorización en el servidor. EnvoyFilter apunta al namespace/etiquetas reales del gateway de entrada y requiere validación con la versión instalada de Istio/Envoy. Comprime las respuestas HTTP en el gateway; instalar un compresor de sidecar de salida no comprime por sí solo las cargas enviadas. Los campos heredados content_length/content_type están obsoletos, pero no se han eliminado. Este ejemplo usa response_direction_config/common_config; pruebe el comportamiento de CPU, latencia, seguridad y protocolo.

El fragmento de Terraform presupone que la VPC, las subredes privadas, el grupo de seguridad de los endpoints y la tabla de rutas ya existen en el módulo propietario. NAT y las asociaciones de rutas siguen bajo la responsabilidad del propietario de esa VPC. Compartir una NAT zonal entre AZ es una decisión de disponibilidad/costo de transferencia, no un ahorro de alta disponibilidad predeterminado; evalúe por separado una opción de NAT regional.

Guarde el código Python como network_costs.py. Establezca EXPECTED_CALLER_ACCOUNT, LINKED_ACCOUNT_ID, START_DATE y END_DATE. reviewed-usage-types.json debe contener una matriz JSON de valores USAGE_TYPE exactos seleccionados en Cost Explorer/GetDimensionValues. Este ejemplo usa el endpoint comercial de facturación de AWS en us-east-1; compruebe la cuenta que llama y los permisos de lectura. Las consultas a la API pueden generar cargos. Las dimensiones de GetCostAndUsage no admiten CONTAINS, por lo que el helper usa filtros EQUALS exactos. Completa la paginación y conserva los importes Decimal, las unidades monetarias y el estado estimado. Los resultados vacíos o los errores no demuestran que el costo total de redes sea cero. Las filas a nivel de cuenta requieren asignaciones adicionales verificadas de etiquetas/recursos antes de atribuirlas a un clúster de EKS específico. Solo se cubren los tipos de uso seleccionados; la coincidencia ambigua por subcadenas de servicio/Regional/Región no puede clasificar de manera fiable los cargos de Internet, entre AZ y entre regiones. Las fechas usan UTC con un End exclusivo; compruebe el historial disponible y el cierre definitivo de la facturación. Los umbrales anteriores de 100/50/200 USD eran valores ilustrativos para priorizar revisiones, no decisiones de optimización universales.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - api-server
              topologyKey: topology.kubernetes.io/zone
      containers:
      - name: database
        image: registry.example.com/team/database:REVIEWED_TAG
    metadata:
      labels:
        app: database
  selector:
    matchLabels:
      app: database
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
spec:
  hosts:
  - api-service
  http:
  - match:
    - headers:
        end-user:
          exact: premium-user
    route:
    - destination:
        host: api-service
        subset: premium
  - route:
    - destination:
        host: api-service
        subset: v1
      weight: 90
    - destination:
        host: api-service
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-subsets
spec:
  host: api-service
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  - name: premium
    labels:
      version: premium
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: compression-filter
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.compressor
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.compressor.v3.Compressor
          response_direction_config:
            common_config:
              min_content_length: 100
              content_type:
              - application/json
              - text/html
          compressor_library:
            name: gzip
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.compression.gzip.compressor.v3.Gzip
              memory_level: 3
              window_bits: 10
              compression_level: BEST_COMPRESSION
              compression_strategy: DEFAULT_STRATEGY
```

```
+-------------------+    +-------------------+    +-------------------+
|                   |    |                   |    |                   |
|  VPC Endpoint     |    |  NAT Gateway      |    |  Internet         |
|  (AWS Services)   |    |  (External APIs)  |    |  Gateway          |
+-------------------+    +-------------------+    +-------------------+
        |                        |                        |
        v                        v                        v
+---------------------------------------------------------------+
|                                                               |
|                  EKS Cluster VPC                              |
|                                                               |
+---------------------------------------------------------------+
        |                        |                        |
        v                        v                        v
+-------------------+    +-------------------+    +-------------------+
|                   |    |                   |    |                   |
|  AZ-a             |    |  AZ-b             |    |  AZ-c             |
|  Workloads        |    |  Workloads        |    |  Workloads        |
|                   |    |                   |    |                   |
+-------------------+    +-------------------+    +-------------------+
        |                        |                        |
        v                        v                        v
+---------------------------------------------------------------+
|                                                               |
|                  Service Mesh                                 |
|                  (Locality-aware routing)                     |
|                                                               |
+---------------------------------------------------------------+
```

```hcl
# Gateway VPC endpoints
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  route_table_ids   = [aws_route_table.private.id]
  vpc_endpoint_type = "Gateway"

  tags = {
    Name = "s3-endpoint"
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  route_table_ids   = [aws_route_table.private.id]
  vpc_endpoint_type = "Gateway"

  tags = {
    Name = "dynamodb-endpoint"
  }
}

# Interface VPC endpoints
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-dkr-endpoint"
  }
}
```

```python
import json
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import boto3
from botocore.config import Config


def network_cost_rows(client, start, end, linked_account, usage_types):
    for value in [start, end]:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use YYYY-MM-DD dates")
    if start >= end:
        raise ValueError("Start must precede exclusive End")
    if not re.fullmatch(r"[0-9]{12}", linked_account):
        raise ValueError("A reviewed linked account ID is required")
    if not isinstance(usage_types, list) or not usage_types or any(
        not isinstance(value, str) or not value.strip() for value in usage_types
    ):
        raise ValueError("Provide exact reviewed USAGE_TYPE values")
    request = {
        "TimePeriod": {"Start": start, "End": end},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
        ],
        "Filter": {
            "And": [
                {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account],
                                "MatchOptions": ["EQUALS"]}},
                {"Dimensions": {"Key": "USAGE_TYPE", "Values": usage_types,
                                "MatchOptions": ["EQUALS"]}},
            ]
        },
    }
    rows = []
    seen_tokens = set()
    for _ in range(100):
        response = client.get_cost_and_usage(**request)
        for period in response["ResultsByTime"]:
            for group in period["Groups"]:
                service, usage_type = group["Keys"]
                metric = group["Metrics"]["UnblendedCost"]
                amount = Decimal(metric["Amount"])
                if not amount.is_finite() or not metric["Unit"]:
                    raise ValueError("Invalid monetary amount/unit")
                rows.append({
                    "start": period["TimePeriod"]["Start"],
                    "endExclusive": period["TimePeriod"]["End"],
                    "service": service,
                    "usageType": usage_type,
                    "amount": str(amount),
                    "unit": metric["Unit"],
                    "estimated": period.get("Estimated"),
                })
        token = response.get("NextPageToken")
        if not token:
            return rows
        if token in seen_tokens:
            raise RuntimeError("Repeated pagination token")
        seen_tokens.add(token)
        request["NextPageToken"] = token
    raise RuntimeError("Page limit exceeded; narrow the query")


def main():
    expected_caller = os.environ["EXPECTED_CALLER_ACCOUNT"]
    if not re.fullmatch(r"[0-9]{12}", expected_caller):
        raise ValueError("Set the reviewed calling account")
    session = boto3.Session(region_name="us-east-1")
    config = Config(connect_timeout=5, read_timeout=30,
                    retries={"mode": "standard", "total_max_attempts": 4})
    identity = session.client("sts", config=config).get_caller_identity()
    if identity["Account"] != expected_caller:
        raise RuntimeError("Calling account mismatch")
    usage_types = json.loads(Path("reviewed-usage-types.json").read_text())
    rows = network_cost_rows(
        session.client("ce", config=config),
        os.environ["START_DATE"], os.environ["END_DATE"],
        os.environ["LINKED_ACCOUNT_ID"], usage_types,
    )
    print(json.dumps({"basis": "UnblendedCost", "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
```

Problemas con las otras opciones:
- **A. Usar el ancho de banda de red más caro para todo el tráfico**: Esto genera costos innecesarios, y no todas las cargas de trabajo requieren un gran ancho de banda.
- **B. Ubicar todos los servicios en una sola zona de disponibilidad**: Esto puede incumplir los requisitos de disponibilidad en varias AZ de las cargas de trabajo críticas. Elegir una sola AZ para un entorno no crítico también requiere decidir explícitamente qué tolerancia a fallos se necesita.
- **D. Bloquear todo el tráfico de red**: No es práctico y limita gravemente la funcionalidad de las aplicaciones.
</details>

### 4. ¿Cuál es el enfoque más eficaz para optimizar los costos de administración de clústeres de Amazon EKS?

- A. Crear tantos clústeres como sea posible
- B. Consolidar todas las cargas de trabajo en un solo clúster
- C. Optimizar el número de clústeres según los requisitos de las cargas de trabajo y minimizar la sobrecarga de administración
- D. Administrar los clústeres manualmente
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Optimizar el número de clústeres según los requisitos de las cargas de trabajo y minimizar la sobrecarga de administración**

**Explicación:**
El enfoque más eficaz para optimizar los costos de administración de clústeres de Amazon EKS consiste en optimizar el número de clústeres según los requisitos de las cargas de trabajo y minimizar la sobrecarga de administración. Este enfoque equilibra los costos de administración de clústeres y la complejidad operativa, a la vez que satisface los requisitos de aislamiento y seguridad de las cargas de trabajo.

**Estrategias clave para optimizar los costos de administración de clústeres:**

1. **Mantener un número adecuado de clústeres**:
   - Separación de clústeres según los requisitos del negocio
   - Separación de clústeres por entorno (desarrollo, ensayo, producción)
   - Tener en cuenta los requisitos de seguridad y cumplimiento

2. **Minimizar la sobrecarga de administración**:
   - Utilizar herramientas automatizadas de administración de clústeres
   - Implementar IaC (infraestructura como código)
   - Centralizar la supervisión y el registro

3. **Optimizar los recursos del clúster**:
   - Configurar adecuadamente el plano de control
   - Administrar eficientemente los grupos de nodos
   - Utilizar servicios compartidos

El comando breve de eksctl ilustra la creación, no una configuración de red/IAM para producción. Seleccione la versión de EKS del catálogo de AWS, revise la VPC y la exposición del endpoint de la API mediante la [guía de creación](../../eks/02-eks-cluster-creation.md) y mantenga los permisos de los controladores en identidades dedicadas. Los límites de tamaño de los grupos de nodos no instalan un autoscaler ni imponen un tope de gasto. Las tarifas de soporte estándar/ampliado, la capacidad opcional de Provisioned Control Plane y las dependencias de administración compartidas también afectan la comparación.

El ejemplo de Terraform usa el módulo verificado **21.25.0**, cuya versión mínima del proveedor de AWS es **6.59**; el pin del proveedor mostrado es 6.69.1. Las entradas no tienen valores predeterminados de entorno inventados deliberadamente. Proporcione una red privada propia y conectividad con la API, entradas de acceso revisadas, complementos compatibles y fijados con sus asociaciones de IAM, y grupos de nodos administrados. Los nodos EC2 estándar necesitan la ruta adecuada de CNI/DNS/proxy; este no es un ejemplo de Auto Mode. Coordine quién administra desired_size con el autoscaler y use estados/identidades de proveedor separados cuando lo requiera el modelo de aislamiento. No se afirma que se haya ejecutado un plan/apply ni que esté listo para producción.

**Métodos de implementación:**

1. **Configuración optimizada de un clúster de EKS**:
   ```bash
   : "${EKS_VERSION:?Select a version offered by the AWS EKS support catalog}"
   # Create optimized cluster using eksctl
   eksctl create cluster \
     --name optimized-cluster \
     --region us-west-2 \
     --version "$EKS_VERSION" \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --managed
   ```

2. **Automatización de la administración del clúster con Terraform**:
   ```hcl
   terraform {
     required_version = ">= 1.5.7"
     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "= 6.69.1"
       }
     }
   }

   variable "region" { type = string }
   variable "account_id" { type = string }
   variable "cluster_name" { type = string }
   variable "environment" { type = string }
   variable "kubernetes_version" { type = string }
   variable "vpc_id" { type = string }
   variable "private_subnet_ids" { type = list(string) }
   variable "reviewed_addons" { type = any }
   variable "reviewed_access_entries" { type = any }
   variable "managed_groups" { type = any }

   provider "aws" {
     region              = var.region
     allowed_account_ids = [var.account_id]
   }

   module "eks" {
     source  = "terraform-aws-modules/eks/aws"
     version = "21.25.0"

     name                    = var.cluster_name
     kubernetes_version      = var.kubernetes_version
     endpoint_private_access = true
     endpoint_public_access  = false
     vpc_id                  = var.vpc_id
     subnet_ids              = var.private_subnet_ids

     addons                  = var.reviewed_addons
     access_entries          = var.reviewed_access_entries
     eks_managed_node_groups = var.managed_groups
     tags = {
       Environment = var.environment
       Terraform   = "true"
     }
   }
   ```

3. **Administración de la configuración del clúster con GitOps**:
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: cluster-config
     namespace: argocd
   spec:
     project: cluster-config
     source:
       repoURL: https://github.com/myorg/cluster-config.git
       targetRevision: REPLACE_WITH_REVIEWED_COMMIT_SHA
       path: configs
     destination:
       server: https://kubernetes.default.svc
       namespace: default
     syncPolicy:
       automated:
         enabled: false
         prune: false
         selfHeal: false
   ```

4. **Configuración de un clúster multiinquilino**:
   ```yaml
   # Namespace resource quota
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: team-a-quota
     namespace: team-a
   spec:
     hard:
       requests.cpu: "10"
       requests.memory: 20Gi
       limits.cpu: "20"
       limits.memory: 40Gi
       pods: "50"
       services: "20"
       persistentvolumeclaims: "30"
   ```

**Aislamiento, entradas de entorno y evidencias con contexto**

La Application de Argo CD requiere un controlador instalado, el repositorio/commit revisado y un AppProject `cluster-config` creado previamente que restrinja repositorios, destinos y tipos de recursos. Sustituya el SHA y el repositorio de marcador de posición antes de usarla. La sincronización/eliminación automática está deshabilitada para la revisión inicial; habilite únicamente el comportamiento de reconciliación previsto a través del propietario. Las credenciales/controladores de administración compartidos pueden ampliar el impacto de seguridad o de fallos a varios clústeres que, por lo demás, están separados.

ResourceQuota restringe la admisión y el número de objetos, no las facturas ni la autorización de los inquilinos. NetworkPolicy se acumula con las demás políticas y requiere que el CNI la aplique. El ejemplo de namespace permite tráfico dentro de `team-a`, hacia/desde el namespace compartido indicado y hacia un Deployment estándar de CoreDNS; adapte explícitamente el DNS local a los nodos de Auto Mode y otras dependencias. El ejemplo de API compartida permite únicamente el tráfico de `team-a` a Pods etiquetados `app: shared-api` en TCP 8080. Reconcilie las políticas amplias existentes en lugar de dejar activa una política anterior que permita todo. RBAC, admisión, IAM y límites de confianza siguen siendo controles independientes.

Los tfvars de entorno siguientes son anulaciones del módulo revisado anterior, no llamadas a un `./modules/eks-cluster` no proporcionado. Combine los valores adecuados de cuenta/red/versión/complementos/acceso con las entradas de cada entorno y use el estado/backend y la identidad propios de cada uno. Las listas y cantidades de instancias son ilustrativas; revise la tolerancia a interrupciones y las opciones regionales actuales.

El script de recopilación opera sobre **un contexto explícito** en cada ejecución. Establezca `KUBE_CONTEXT`, `EXPECTED_API_SERVER`, `EXPECTED_CALLER_ACCOUNT`, `LINKED_ACCOUNT_ID`, `BILLING_TAG_KEY`, `BILLING_TAG_VALUE`, `START_DATE` y `END_DATE`; repita el proceso deliberadamente para cada clúster. La URL del servidor de la API debe coincidir con el clúster de EKS revisado. Guarda muestras reales de Metrics API con sus marcas de tiempo, ventanas y unidades, así como todas las páginas de Cost Explorer limitadas por etiqueta, en lugar de presentar como uso de todos los clústeres los recursos solicitados de un solo contexto. Metrics Server y los permisos de lectura son requisitos previos. Las muestras de nodos que falten no equivalen a uso cero, y las muestras de poco tiempo no representan el historial de demanda máxima.

Se usan endpoints comerciales de facturación de AWS y fechas finales exclusivas. Elija un historial de facturación disponible; las fechas anteriores de 2023 eran ejemplos de configuración, no resultados medidos. La asignación de etiquetas debe existir en la facturación y puede omitir cargos sin etiquetar o compartidos. Se conservan las unidades monetarias originales, la base de costo y el estado estimado; el script no infiere un total a partir del primer grupo ni recomienda reducir recursos basándose en un umbral de solicitudes/capacidad.

Un clúster compartido grande puede reducir la duplicación de la sobrecarga del plano de control/servicios compartidos, pero aumenta la coordinación y el impacto de los fallos. Los clústeres más pequeños pueden facilitar el mantenimiento independiente y los límites entre cargas de trabajo, pero aumentan la capacidad y las operaciones duplicadas. Elija una división híbrida según los requisitos de confianza, carga de trabajo y recuperación; el número de clústeres por sí solo no garantiza aislamiento ni un menor costo total.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-isolation
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: shared-services
  egress:
  - to:
    - podSelector: {}
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: shared-services
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shared-services
  labels:
    name: shared-services
    access: global
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-team-a
  namespace: shared-services
spec:
  podSelector:
    matchLabels:
      app: shared-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: team-a
    ports:
    - protocol: TCP
      port: 8080
```

```hcl
# production.tfvars: merge with the production account/network/add-on/access inputs.
cluster_name = "production"
environment  = "production"
managed_groups = {
  critical = {
    instance_types = ["m5.large"]
    capacity_type  = "ON_DEMAND"
    min_size       = 3
    max_size       = 10
    desired_size   = 3
  }
  general = {
    instance_types = ["m5.large", "m5a.large"]
    capacity_type  = "SPOT"
    min_size       = 3
    max_size       = 20
    desired_size   = 3
  }
}
```

```hcl
# development.tfvars: use a separate state/backend and the development identity.
cluster_name = "development"
environment  = "development"
managed_groups = {
  default = {
    instance_types = ["m5.large", "m5a.large"]
    capacity_type  = "SPOT"
    min_size       = 1
    max_size       = 5
    desired_size   = 1
  }
}
```

```python
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path


def read_json(command):
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    return json.loads(completed.stdout)


def collect(context, expected_server, caller_account, linked_account, tag_key, tag_value, start, end,
            run=subprocess.run, query=read_json):
    if not all([context, expected_server, tag_key, tag_value]):
        raise ValueError("Explicit context, API server, and billing tag mapping are required")
    if not all(re.fullmatch(r"[0-9]{12}", account) for account in [caller_account, linked_account]):
        raise ValueError("Use reviewed 12-digit account IDs")
    if any(date.fromisoformat(value).isoformat() != value for value in [start, end]) or start >= end:
        raise ValueError("Use YYYY-MM-DD with Start before exclusive End")
    server = run(
        ["kubectl", "--context", context, "config", "view", "--minify",
         "--output", "jsonpath={.clusters[0].cluster.server}"],
        check=True, capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    if server != expected_server:
        raise RuntimeError("Kubernetes context/API-server mismatch")
    identity = query(["aws", "sts", "get-caller-identity", "--region", "us-east-1",
                      "--output", "json", "--no-cli-pager"])
    if identity["Account"] != caller_account:
        raise RuntimeError("Calling AWS account mismatch")
    usage = query(["kubectl", "--context", context, "get", "--raw",
                   "/apis/metrics.k8s.io/v1beta1/nodes"])
    if usage.get("kind") != "NodeMetricsList" or not isinstance(usage.get("items"), list):
        raise ValueError("Unexpected node metrics response")
    expression = {"And": [
        {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account], "MatchOptions": ["EQUALS"]}},
        {"Tags": {"Key": tag_key, "Values": [tag_value], "MatchOptions": ["EQUALS"]}},
    ]}
    base = [
        "aws", "ce", "get-cost-and-usage", "--region", "us-east-1",
        "--time-period", json.dumps({"Start": start, "End": end}),
        "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
        "--group-by", "Type=DIMENSION,Key=SERVICE",
        "--filter", json.dumps(expression), "--output", "json", "--no-cli-pager",
    ]
    pages = []
    token = None
    seen = set()
    for _ in range(100):
        page = query(base + (["--next-page-token", token] if token else []))
        if not isinstance(page.get("ResultsByTime"), list):
            raise ValueError("Unexpected cost response")
        pages.append(page)
        token = page.get("NextPageToken")
        if not token:
            return {
                "context": context, "apiServer": server, "nodeUsage": usage,
                "billingScope": expression, "basis": "UnblendedCost", "costPages": pages,
            }
        if token in seen:
            raise RuntimeError("Repeated cost pagination token")
        seen.add(token)
    raise RuntimeError("Page limit exceeded; narrow the query")


if __name__ == "__main__":
    result = collect(
        os.environ["KUBE_CONTEXT"], os.environ["EXPECTED_API_SERVER"],
        os.environ["EXPECTED_CALLER_ACCOUNT"], os.environ["LINKED_ACCOUNT_ID"],
        os.environ["BILLING_TAG_KEY"], os.environ["BILLING_TAG_VALUE"],
        os.environ["START_DATE"], os.environ["END_DATE"],
    )
    Path("cluster-cost-and-usage.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Saved raw metrics and tag-scoped billing pages; no resizing recommendation was made.")
```

Problemas con las otras opciones:
- **A. Crear tantos clústeres como sea posible**: Esto aumenta los costos del plano de control y la sobrecarga de administración de cada clúster, lo que reduce la utilización de recursos.
- **B. Consolidar todas las cargas de trabajo en un solo clúster**: Puede ser adecuado en algunos entornos, pero no tiene en cuenta los requisitos de seguridad, el aislamiento de cargas de trabajo ni el alcance de impacto de los fallos.
- **D. Administrar los clústeres manualmente**: La administración manual aumenta la posibilidad de errores, reduce la coherencia y aumenta la sobrecarga operativa.
</details>

### 5. ¿Cuál es el enfoque más eficaz para supervisar y asignar costos en Amazon EKS?

- A. Revisar únicamente las facturas de AWS
- B. Implementar una estrategia de etiquetado, herramientas de asignación de costos y supervisión continua
- C. Asignar el mismo costo a todos los recursos
- D. Usar recursos sin supervisar sus costos
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Implementar una estrategia de etiquetado, herramientas de asignación de costos y supervisión continua**

**Explicación:**
El enfoque más eficaz para supervisar y asignar costos en Amazon EKS consiste en implementar una estrategia de etiquetado, herramientas de asignación de costos y supervisión continua. Este enfoque ayuda a realizar un seguimiento preciso de los costos, asignarlos por equipo o proyecto e identificar oportunidades de optimización.

**Estrategias clave para supervisar y asignar costos:**

1. **Estrategia integral de etiquetado**:
   - Etiquetas por unidad de negocio, equipo, proyecto y entorno
   - Aplicar reglas de etiquetado coherentes
   - Implementar etiquetado automatizado

2. **Uso de herramientas de asignación de costos**:
   - AWS Cost Explorer y AWS Budgets
   - Herramientas especializadas como Kubecost o CloudHealth
   - Paneles e informes personalizados

3. **Supervisión y optimización continuas**:
   - Revisión y análisis periódicos de costos
   - Detección de anomalías y alertas
   - Implementación de recomendaciones de optimización

Las etiquetas de Kubernetes, las etiquetas de recursos de AWS y las etiquetas de facturación activadas son elementos distintos. Las etiquetas del namespace no se propagan automáticamente a los Pods ni a los recursos de AWS; coloque las etiquetas de carga de trabajo en la plantilla del Pod. La política de etiquetas de Organizations mostrada valida las claves/valores de etiquetas configurados en los recursos admitidos, incluidos los clústeres de EKS. No agrega etiquetas ni configura la obligatoriedad de etiquetas. Revise la política heredada y los controles independientes para detectar etiquetas faltantes. La activación/recomposición retroactiva de la facturación es una operación independiente; para recuperar hasta 12 meses se necesitan etiquetas que realmente existieran históricamente.

El comando de CUR siguiente crea un **CUR heredado**, no un panel de Cost Explorer ni una exportación CUR 2.0. AWS sigue admitiendo el CUR heredado. Los diseños nuevos deben evaluar Data Exports/CUR 2.0 en la [guía de FinOps](../../ops/13-finops-cost-platform.md). El ejemplo heredado requiere un bucket existente en la Región declarada, una política de entrega de CUR revisada y permisos de informes. No crea el bucket, el esquema de Glue, la integración con Athena ni el panel. Siga la política específica del servicio de entrega; no sustituya la política `bcm-data-exports` de CUR 2.0 por la del servicio heredado.

**Métodos de implementación:**

1. **Implementar una estrategia de etiquetado**:
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
     namespace: team-a
     labels:
       app: web-app
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   spec:
     selector:
       matchLabels:
         app: web-app
     template:
       metadata:
         labels:
           app: web-app
           team: team-a
           cost-center: cc-123
           environment: production
           project: project-x
       spec:
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
   ```

2. **Configuración de una política de etiquetas de AWS**:
   ```json
   {
     "tags": {
       "team": {
         "tag_key": {
           "@@assign": "team"
         },
         "tag_value": {
           "@@assign": [
             "team-a",
             "team-b",
             "platform"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "cost-center": {
         "tag_key": {
           "@@assign": "cost-center"
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "environment": {
         "tag_key": {
           "@@assign": "environment"
         },
         "tag_value": {
           "@@assign": [
             "production",
             "staging",
             "development"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       }
     }
   }
   ```

3. **Instalación y configuración de Kubecost**:
Use la instalación verificada de Kubecost 3.3.1 de la [guía de origen](../../eks/07-eks-cost-optimization.md), o OpenCost 1.121.2/chart 2.5.31 de la [pregunta 6 de EKS06](06-eks-monitoring-logging-quiz.md). Kubecost 3.x usa recopilación mediante ClickHouse/agente finops directo; los valores de Prometheus de 2.x y los tokens de licencia de línea de comandos no forman parte de esta configuración. Reutilice una implementación administrada por su propietario y revise los requisitos de migración, licencia y almacenamiento.

4. **Configuración de entrega de CUR heredado**:
   ```bash
   # Create cost and usage report
   aws cur put-report-definition \
     --report-definition '{
       "ReportName": "eks-cost-report",
       "TimeUnit": "HOURLY",
       "Format": "Parquet",
       "Compression": "Parquet",
       "AdditionalSchemaElements": ["RESOURCES"],
       "S3Bucket": "my-cost-reports",
       "S3Prefix": "eks-costs",
       "S3Region": "us-east-1",
       "AdditionalArtifacts": ["ATHENA"],
       "RefreshClosedReports": true,
       "ReportVersioning": "OVERWRITE_REPORT"
     }'
   ```

**Revisión de asignaciones y configuración complementaria**

Reutilice el recopilador de Q4, limitado por contexto/cuenta/etiqueta, para obtener muestras reales de Metrics API y páginas de facturación. Las solicitudes y los límites son configuraciones declaradas, no uso real; una proporción entre solicitud/límite inferior a 0,5 no justifica reducir las solicitudes. Compare la misma carga de trabajo, ventana de tiempo, unidades y cobertura en lugar del número actual de réplicas con el uso histórico. Reconcilie las asignaciones de equipo/centro de costos con los costos compartidos y sin etiquetar. Para informes/alertas operativos, use el flujo explícito de recopilación/validación de la [guía de FinOps](../../ops/13-finops-cost-platform.md); los errores/datos faltantes no deben convertirse en cero.

El presupuesto de 1.000 USD/80 % siguiente es ilustrativo. Verifique el formato y la cobertura reales del filtro de etiquetas activado en Budgets; las alertas de facturación procesadas no imponen un tope de gasto estricto. El fragmento de Terraform presupone un bucket CUR existente, una identidad del solicitante, proveedores y una entrada de Región. El propietario debe configurar el acceso a los resultados de Athena, la retención/cifrado, las tablas de Glue y los permisos de consulta. Terraform admite `aws_quicksight_dashboard`, pero la edición de la cuenta, los conjuntos de datos/plantillas y los permisos todavía requieren configuración.

```bash
aws resourcegroupstaggingapi tag-resources --region us-west-2 \
  --resource-arn-list arn:aws:eks:us-west-2:123456789012:cluster/my-cluster \
  --tags team=platform,cost-center=cc-100,environment=production
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a-production
  labels:
    team: team-a
    environment: production
    cost-center: cc-123
---
apiVersion: v1
kind: Namespace
metadata:
  name: team-a-development
  labels:
    team: team-a
    environment: development
    cost-center: cc-123
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web-app
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        image: registry.example.com/team/web-app:REVIEWED_TAG
    metadata:
      labels:
        app: web-app
  selector:
    matchLabels:
      app: web-app
```

```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "EKS-Monthly",
    "BudgetLimit": {
      "Amount": "1000",
      "Unit": "USD"
    },
    "CostFilters": {
      "TagKeyValue": [
        "user:kubernetes.io/cluster/my-cluster$owned"
      ]
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "team@example.com"
        }
      ]
    }
  ]'
```

```hcl
resource "aws_cur_report_definition" "eks_cost" {
  report_name                = "eks-cost-report"
  time_unit                  = "HOURLY"
  format                     = "Parquet"
  compression                = "Parquet"
  additional_schema_elements = ["RESOURCES"]
  s3_bucket                  = aws_s3_bucket.cost_reports.id
  s3_prefix                  = "eks-costs"
  s3_region                  = "us-east-1"
  additional_artifacts       = ["ATHENA"]
  refresh_closed_reports     = true
  report_versioning          = "OVERWRITE_REPORT"
}

resource "aws_s3_bucket" "athena_results" {
  bucket = "eks-cost-athena-results-${data.aws_caller_identity.current.account_id}-${var.region}"

  tags = {
    Name = "EKS Cost Athena Results"
  }
}

resource "aws_athena_workgroup" "eks_cost" {
  name = "eks-cost-analysis"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/output/"
    }
  }
}

```

Para la llamada regional a TagResources, compruebe la Región de destino e inspeccione `FailedResourcesMap`; que la CLI termine correctamente no demuestra que se hayan etiquetado todos los recursos solicitados. Confirme las etiquetas reales de los recursos antes de basarse en la asignación de facturación.

**Panel de tasa estimada de asignación**

Esta es una **estimación instantánea de la tasa de asignación de CPU+memoria en USD/hora** para el Prometheus de un clúster. No es una factura ni el costo completo de un namespace. Las entradas son métricas de asignación/precio de OpenCost (`job="opencost"` en este ejemplo) y etiquetas de Pods de kube-state-metrics (`job="kube-state-metrics"`). Confirme las etiquetas reales de job y la cobertura completa de CPU/memoria/precios. Mantenga las etiquetas de namespace de las cargas de trabajo del exportador con la configuración adecuada de honor-labels del ServiceMonitor. Un backend compartido necesita una identidad de clúster coherente en cada agregación y unión.

Combine el primer fragmento de values con la versión de kube-prometheus-stack administrada por el propietario. Las etiquetas team de los Pods deben tener valores acotados y estar presentes en la plantilla del Pod; una etiqueta del namespace no las crea. Las etiquetas team faltantes se agrupan como `unassigned`. Las consultas eliminan duplicados idénticos de scrape; resuelva por separado las fuentes contradictorias de precios/propiedad. GPU, almacenamiento, red, plano de control, asignación ociosa/compartida, descuentos, créditos e impuestos no están incluidos en estos dos componentes. La ausencia de datos no significa que el costo sea cero, y una tasa no es un importe mensual en dólares.

La etiqueta de namespace/release de PrometheusRule debe coincidir con los selectores de la guía de origen. Sustituya `REPLACE_WITH_PROMETHEUS_UID` por el origen de datos revisado de un solo clúster antes de aprovisionar el panel. La etiqueta `grafana_dashboard: "1"` del ConfigMap coincide con el sidecar de la guía de origen; el JSON correspondiente se proporciona a continuación. Compruebe el estado de las reglas, la cobertura de los datos y las consultas del panel. Estos ejemplos no se conectaron a una implementación activa de facturación/Grafana.

```yaml
kube-state-metrics:
  metricLabelsAllowlist:
  - pods=[team]
```

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-allocation-rate
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-allocation-rate
    rules:
    - record: eks_review:pod_cpu_memory_cost_per_hour:sum
      expr: "sum by (namespace, pod) (\n  (\n    max by (namespace, pod, container,\
        \ node) (\n      container_cpu_allocation{job=\"opencost\"}\n    )\n    *\
        \ on (node) group_left\n    max by (node) (node_cpu_hourly_cost{job=\"opencost\"\
        })\n  )\n  +\n  (\n    max by (namespace, pod, container, node) (\n      container_memory_allocation_bytes{job=\"\
        opencost\"}\n    ) / 1073741824\n    * on (node) group_left\n    max by (node)\
        \ (node_ram_hourly_cost{job=\"opencost\"})\n  )\n)"
    - record: eks_review:team_cpu_memory_cost_per_hour:sum
      expr: "sum by (team) (\n  label_replace(\n    eks_review:pod_cpu_memory_cost_per_hour:sum\n\
        \    * on (namespace, pod) group_left (label_team)\n    max by (namespace,\
        \ pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\",label_team!=\"\
        \"}),\n    \"team\", \"$1\", \"label_team\", \"(.+)\"\n  )\n  or\n  label_replace(\n\
        \    eks_review:pod_cpu_memory_cost_per_hour:sum\n    unless on (namespace,\
        \ pod) max by (namespace, pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\"\
        ,label_team!=\"\"}),\n    \"team\", \"unassigned\", \"namespace\", \".*\"\n\
        \  )\n)"
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cost-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  cost-dashboard.json: "{\n  \"title\": \"Estimated CPU and memory allocation rate\"\
    ,\n  \"uid\": \"eks-allocation-rate\",\n  \"schemaVersion\": 39,\n  \"version\"\
    : 1,\n  \"refresh\": \"1m\",\n  \"time\": {\n    \"from\": \"now-6h\",\n    \"\
    to\": \"now\"\n  },\n  \"panels\": [\n    {\n      \"id\": 1,\n      \"title\"\
    : \"CPU + memory allocation by namespace (USD/hour)\",\n      \"type\": \"timeseries\"\
    ,\n      \"gridPos\": {\n        \"x\": 0,\n        \"y\": 0,\n        \"w\":\
    \ 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n        \"type\":\
    \ \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\n      },\n\
    \      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\": \"currencyUSD\"\
    \n        },\n        \"overrides\": []\n      },\n      \"targets\": [\n    \
    \    {\n          \"refId\": \"A\",\n          \"expr\": \"sum by (namespace)\
    \ (eks_review:pod_cpu_memory_cost_per_hour:sum)\",\n          \"legendFormat\"\
    : \"{{namespace}}\"\n        }\n      ]\n    },\n    {\n      \"id\": 2,\n   \
    \   \"title\": \"CPU + memory allocation by team (USD/hour)\",\n      \"type\"\
    : \"timeseries\",\n      \"gridPos\": {\n        \"x\": 12,\n        \"y\": 0,\n\
    \        \"w\": 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n   \
    \     \"type\": \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\
    \n      },\n      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\"\
    : \"currencyUSD\"\n        },\n        \"overrides\": []\n      },\n      \"targets\"\
    : [\n        {\n          \"refId\": \"A\",\n          \"expr\": \"eks_review:team_cpu_memory_cost_per_hour:sum\"\
    ,\n          \"legendFormat\": \"{{team}}\"\n        }\n      ]\n    }\n  ]\n}"
```

Problemas con las otras opciones:
- **A. Revisar únicamente las facturas de AWS**: Las facturas de AWS solo ofrecen información de costos de alto nivel, por lo que es difícil identificar la asignación detallada de costos o las oportunidades de optimización.
- **C. Asignar el mismo costo a todos los recursos**: Esto no refleja con precisión el uso real de recursos ni la generación de costos, y no aclara la responsabilidad de los equipos o proyectos.
- **D. Usar recursos sin supervisar sus costos**: Sin supervisión de costos no se pueden detectar a tiempo los aumentos ni identificar oportunidades de optimización, lo que dificulta administrar el presupuesto.
</details>

### 6. ¿Qué enfoque respalda mejor un flujo de trabajo escalable para optimizar los costos de EKS?

- A. Cambiar los recursos manualmente sin medir los resultados
- B. Tener en cuenta solo los datos de facturación e ignorar la telemetría de las cargas de trabajo
- C. Combinar visibilidad de costos, telemetría de recursos y escalado automático adecuado con responsabilidades claras
- D. Ejecutar optimizadores sin coordinación sobre los mismos recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Combinar visibilidad de costos, telemetría de recursos y escalado automático adecuado con responsabilidades claras**

**Explicación:**
Las herramientas mencionadas son ejemplos de funciones complementarias, no un requisito para instalarlas todas. Elija una ruta de costos/telemetría con propietario y un escalado adecuado a las cargas de trabajo. EKS Auto Mode, Karpenter autoadministrado o Cluster Autoscaler podrían ser ya responsables de la capacidad de los nodos; defina responsabilidades separadas y evite controladores en conflicto. Los ahorros y el mantenimiento de los SLO deben medirse, y la instalación de herramientas de costos no conecta automáticamente los datos de facturación con las políticas de HPA/Karpenter.

**Herramientas y funciones clave para optimizar costos:**

1. **Kubecost**:
   - Visibilidad de los costos de recursos de Kubernetes
   - Asignación de costos por namespace, Deployment y Service
   - Recomendaciones de optimización de costos
   - Previsión de costos y administración de presupuestos

2. **Karpenter**:
   - Aprovisionamiento y administración inteligentes de nodos
   - Selección de instancias dentro de las restricciones de carga de trabajo, capacidad y precio
   - Comportamiento de aprovisionamiento/escalado que debe comprobarse en el entorno real
   - Optimización del uso de instancias Spot

3. **AWS Cost Explorer**:
   - Análisis de costos en los servicios de AWS
   - Asignación de costos basada en etiquetas
   - Tendencias y previsiones de costos
   - Recomendaciones de Reserved Instances y Savings Plans

4. **Herramientas de escalado automático de Kubernetes**:
   - Horizontal Pod Autoscaler (HPA)
   - Vertical Pod Autoscaler (VPA)
   - Cluster Autoscaler
   - Cluster Proportional Autoscaler

**Métodos de implementación:**

1. **Instalación y configuración de Kubecost**:
Reutilice la instalación verificada y los requisitos previos de datos de asignación de la pregunta 5 y la [guía de origen](../../eks/07-eks-cost-optimization.md). Kubecost 3.3.1 usa el chart actual `kubecost/kubecost` y una arquitectura de ClickHouse/agente directo; las funciones del producto dependen de la edición/configuración. OpenCost es una opción independiente. No implemente un segundo recopilador sobre una configuración existente que ya tenga propietario.

2. **Instalación y configuración de Karpenter**:
Guarde lo siguiente como `karpenter-values.yaml`, sustituya la cuenta/rol/clúster/endpoint/cola por valores existentes revisados y siga la [guía de Karpenter](../../autoscaling/02-karpenter.md). El ejemplo verificado usa 1.14.1; EKS 1.36 requiere al menos 1.13 en la matriz de compatibilidad. Son claves `settings.*`, no valores `controller.clusterName/clusterEndpoint` ignorados. La relación de confianza IRSA debe coincidir con `system:serviceaccount:karpenter:karpenter` y su audiencia; no combine asignaciones IRSA/Pod Identity que entren en conflicto. Prepare primero IAM para el controlador/nodos, acceso de nodos, subredes/grupos de seguridad, la cola y la conexión de eventos para interrupciones, y capacidad de arranque fiable. Las instalaciones nuevas de Helm y las actualizaciones de CRD tienen pasos de propiedad/ciclo de vida distintos; actualizar solo el controlador no actualiza las CRD existentes.

```yaml
serviceAccount:
  create: true
  name: karpenter
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/KarpenterControllerRole-my-cluster
settings:
  clusterName: my-cluster
  clusterEndpoint: https://REPLACE_WITH_REVIEWED_EKS_ENDPOINT
  interruptionQueue: my-cluster
```

```bash
: "${KUBE_CONTEXT:?Select the reviewed context matching the values file}"
KARPENTER_VERSION="1.14.1"
helm template karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" --namespace karpenter \
  -f karpenter-values.yaml > karpenter-rendered.yaml
# Fresh installation only after the owned IAM, node access, queue, CRDs, and bootstrap capacity are ready.
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --kube-context "$KUBE_CONTEXT" \
  --version "$KARPENTER_VERSION" --namespace karpenter --create-namespace \
  -f karpenter-values.yaml --wait --timeout 5m
```

   ```yaml
   # Karpenter NodePool and NodeClass configuration
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot", "on-demand"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Configurar Horizontal Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Configurar Vertical Pod Autoscaler**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**Integración de herramientas y flujo de trabajo:**

1. **Visibilidad y análisis de costos**:
   - Kubecost: análisis de costos de recursos dentro del clúster
   - AWS Cost Explorer: análisis de costos en los servicios de AWS
   - Paneles integrados: visión general y tendencias de los costos

2. **Optimización automatizada de recursos**:
   - Karpenter: aprovisionamiento y administración óptimos de nodos
   - HPA/VPA: optimización de recursos a nivel de carga de trabajo
   - Uso de instancias Spot: recursos de cómputo rentables

3. **Asignación de costos y responsabilidades**:
   - Asignación de costos basada en etiquetas
   - Análisis de costos por namespace y etiqueta
   - Informes de costos por equipo y proyecto

4. **Optimización y mejora continuas**:
   - Implementar recomendaciones de optimización de costos
   - Revisar y analizar los costos periódicamente
   - Definir y hacer seguimiento de los objetivos de reducción de costos

**Integración administrada y validación de API**

Los ejemplos de VPA usan Off mientras que HPA usa denominadores de utilización de CPU/memoria. Habilite los cambios automáticos de solicitudes solo después de coordinar ese bucle de control. Cluster Proportional Autoscaler escala las réplicas de los componentes según las señales del tamaño del clúster; no es un aprovisionador de nodos equivalente. Los límites de Karpenter, las preferencias de instancias y el retraso de consolidación no garantizan un gasto ni un plazo de terminación determinados. Inspeccione las AMI resueltas y fije una versión/ID probados para cambios controlados, en lugar de tratar `al2023@latest` como inmutable.

PriorityClass controla la prioridad de programación/expropiación, no la asignación de costos ni la disponibilidad garantizada. Gestione quién puede asignar prioridades; la expropiación del scheduler intenta respetar los PDB, pero hace todo lo posible. Revise la interrupción y la recuperación de las cargas de trabajo. Las observaciones y recomendaciones de costos necesitan una ruta explícita, revisada, de política/cambio antes de que actúen los controladores; el diagrama de arquitectura no implementa esa integración.

La alternativa de Terraform usa configuración con archivo de valores del proveedor Helm 3.3.0 y el proveedor de AWS 6.69.1. Proporcione el contexto de Kubernetes explícito y los valores de chart revisados, incluidas las referencias compatibles de identidad, almacenamiento y secretos de licencia; no crea esos requisitos previos. No incluya credenciales de licencia/nube sin proteger en values ni en el estado. Reconcilie una versión existente con su propietario en lugar de instalarla de nuevo mediante un segundo administrador. El presupuesto de 1.000 USD/80 % es ilustrativo, usa un filtro de etiquetas de facturación verificado y no es un tope de gasto estricto. En esta auditoría no se aprovisionó ningún clúster/Helm ni se envió ninguna notificación.

El ejemplo de API siguiente apunta explícitamente a OpenCost 1.121.2 de la configuración anterior, no a una URL de Kubecost 3.x supuesta. Su API `/allocation` acepta la agregación `namespace,controllerKind,controller`; `deployment` no es una clave de agregación genérica documentada. La respuesta es una matriz de mapas de conjuntos de asignaciones, no un diccionario directo de namespace/Deployment. Valide los errores HTTP/API y la cobertura de los datos; un resultado vacío no significa que el costo sea cero ni demuestra un aprovisionamiento excesivo. Las cantidades de asignación, el uso, las solicitudes, los byte-hours/core-hours y los recuentos actuales de réplicas tienen significados y ventanas de tiempo distintos. Revise el esquema versionado y métricas comparables de la carga de trabajo antes de recomendar ajustes de tamaño. Las estimaciones sin procesar de asignación deben reconciliarse con la facturación y las políticas de costos ociosos/compartidos.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web-app
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        image: registry.example.com/team/web-app:REVIEWED_TAG
    metadata:
      labels:
        app: web-app
  selector:
    matchLabels:
      app: web-app
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-pool
spec:
  template:
    spec:
      requirements:
        - key: "karpenter.sh/capacity-type"
          operator: In
          values: ["spot"]
        - key: "node.kubernetes.io/instance-type"
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
```

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: High priority pods
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: false
description: Low priority pods
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
spec:
  template:
    spec:
      priorityClassName: high-priority
      containers:
      - name: critical-app
        image: registry.example.com/team/critical-app:REVIEWED_TAG
    metadata:
      labels:
        app: critical-app
  selector:
    matchLabels:
      app: critical-app
```

```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "EKS-Monthly",
    "BudgetLimit": {
      "Amount": "1000",
      "Unit": "USD"
    },
    "CostFilters": {
      "TagKeyValue": [
        "user:kubernetes.io/cluster/my-cluster$owned"
      ]
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "team@example.com"
        }
      ]
    }
  ]'
```

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "= 3.3.0"
    }
  }
}

variable "region" { type = string }
variable "account_id" { type = string }
variable "kubeconfig_path" { type = string }
variable "kube_context" { type = string }
variable "reviewed_kubecost_values_path" { type = string }
variable "reviewed_karpenter_values_path" { type = string }
variable "budget_name" { type = string }
variable "budget_tag_filter" {
  type        = string
  description = "Actual activated Budgets TagKeyValue, for example user:cluster$production."
}
variable "notification_email" {
  type        = string
  description = "Approved recipient; applying this configures real notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

provider "helm" {
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

resource "helm_release" "kubecost" {
  name             = "kubecost"
  repository       = "https://kubecost.github.io/kubecost/"
  chart            = "kubecost"
  version          = "3.3.1"
  namespace        = "kubecost"
  create_namespace = true
  values           = [file(var.reviewed_kubecost_values_path)]
  wait             = true
  timeout          = 300
}

resource "helm_release" "karpenter" {
  name             = "karpenter"
  repository       = "oci://public.ecr.aws/karpenter"
  chart            = "karpenter"
  version          = "1.14.1"
  namespace        = "karpenter"
  create_namespace = true
  values           = [file(var.reviewed_karpenter_values_path)]
  wait             = true
  timeout          = 300
}

resource "aws_budgets_budget" "eks" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [var.budget_tag_filter]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

```bash
: "${KUBE_CONTEXT:?Select the reviewed OpenCost cluster context}"
# Terminal 1: authorized local access to the OpenCost 1.121.2 service from EKS06.
kubectl --context "$KUBE_CONTEXT" -n opencost port-forward --address 127.0.0.1 svc/opencost 9003:9003
```

```bash
curl --fail --silent --show-error --max-time 30 --get \
  http://127.0.0.1:9003/allocation \
  --data-urlencode 'window=1d' \
  --data-urlencode 'aggregate=namespace,controllerKind,controller' \
  --data-urlencode 'accumulate=true' > allocation.json
```

```python
import json
from pathlib import Path

response = json.loads(Path("allocation.json").read_text())
if response.get("code") != 200 or not isinstance(response.get("data"), list):
    raise ValueError("Unexpected allocation API response; do not replace failure with zero")
if not all(isinstance(allocation_set, dict) for allocation_set in response["data"]):
    raise ValueError("Expected an array of allocation-set maps")
if not response["data"] or not any(response["data"]):
    raise SystemExit("No allocation data for the selected window; investigate coverage")
else:
    print("Allocation response shape accepted; review units, window, and coverage before analysis")
```

Las otras opciones omiten las mediciones, las señales de las cargas de trabajo o la coordinación de responsabilidades. Los controladores en conflicto pueden perjudicar la estabilidad y la previsibilidad de los costos.
</details>
