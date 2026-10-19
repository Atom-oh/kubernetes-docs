# Cuestionario sobre optimización de costos de Amazon EKS

> **Última actualización**: 16 de octubre de 2026

Los ejemplos son alternativas de configuración independientes; no son despliegues ejecutados ni ahorros medidos. Integra los cambios con quien administra el recurso existente; no apliques todos los ejemplos uno tras otro sobre la misma carga de trabajo. Sustituye las imágenes de aplicación de ejemplo y los hooks propios de la aplicación, verifica la cuenta, el contexto, la región y la compatibilidad de los controladores, y prueba el comportamiento antes de usarlo en operaciones.

Este cuestionario evalúa tu comprensión de las estrategias, herramientas y buenas prácticas para optimizar los costos de los clústeres de Amazon EKS.

## Descripción general del cuestionario
- Optimización de recursos de cómputo
- Optimización de costos de almacenamiento
- Optimización de costos de red
- Optimización de costos de administración del clúster
- Monitoreo y análisis de costos
- Herramientas y buenas prácticas para optimizar costos

## Preguntas de opción múltiple

### 1. ¿Qué estrategia es más eficaz para optimizar los costos de cómputo en Amazon EKS?

- A. Usar siempre los tipos de instancia más grandes
- B. Usar solo instancias bajo demanda para todas las cargas de trabajo
- C. Combinar instancias Spot, dimensionamiento adecuado y escalado automático
- D. Consolidar todas las cargas de trabajo en un único grupo de nodos
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Combinar instancias Spot, dimensionamiento adecuado y escalado automático**

**Explicación:**
La estrategia más eficaz para optimizar los costos de cómputo en Amazon EKS combina instancias Spot, dimensionamiento adecuado y escalado automático. Usa Spot solo cuando la carga tolere interrupciones y haya capacidad disponible, y verifica los ahorros frente a los SLO de la carga de trabajo. Esta combinación ni el descuento máximo anunciado garantizan un costo menor o el mismo rendimiento.

**Estrategias clave para optimizar el cómputo:**

1. **Uso de instancias Spot**:
   - Ahorro de hasta un 90 % frente a instancias bajo demanda
   - Adecuadas para cargas de trabajo tolerantes a fallos
   - Implementar mecanismos para gestionar interrupciones

2. **Dimensionamiento adecuado**:
   - Seleccionar instancias según el uso real de recursos
   - Eliminar recursos sobreaprovisionados
   - Optimizar las solicitudes y los límites de recursos

3. **Implementación del escalado automático**:
   - Escalado de nodos mediante Cluster Autoscaler o Karpenter
   - Escalado de pods mediante Horizontal Pod Autoscaler
   - Ajuste de recursos según la demanda

NodePool/EC2NodeClass requieren un controlador Karpenter compatible y sus CRD instalados, permisos IAM acotados para el controlador, un rol de nodo, recursos de descubrimiento y una cola de interrupciones. En la matriz actual, EKS 1.36 requiere Karpenter >=1.13. `al2023@latest` es un selector variable: revisa las AMI resueltas y fija un alias o una AMI probados para controlar el despliegue gradual. Las listas de instancias y los límites de capacidad son ilustrativos, no un tope de gasto. Los grupos de nodos administrados tienen su propio mecanismo para interrupciones; no superpongas otro controlador de interrupciones sobre los nodos administrados por Karpenter.

HPA requiere métricas de recursos y solicitudes; con objetivos de CPU y memoria, elige el mayor recuento de réplicas deseado. El VPA siguiente está en modo **Off** para ofrecer recomendaciones sin cambiar esos denominadores. `Auto` está obsoleto y se reemplaza por modos explícitos como `Recreate`; coordina con HPA cualquier cambio automático de CPU o memoria. Un hook preStop consume el período de gracia de terminación y no puede garantizar que se cumpla un plazo de Spot ni que la limpieza termine correctamente.

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

**Estrategias de optimización por tipo de carga de trabajo:**

1. **Aplicaciones sin estado**:
   - Dar prioridad a instancias Spot
   - Implementar escalado horizontal
   - Desplegar en varias zonas de disponibilidad

2. **Aplicaciones con estado**:
   - Combinar instancias bajo demanda y Spot
   - Seleccionar tipos de instancia adecuados
   - Equilibrar el rendimiento y el costo del almacenamiento

3. **Trabajos por lotes**:
   - Maximizar el uso de instancias Spot
   - Implementar mecanismos para reintentar trabajos
   - Programarlos dentro de los plazos y según la capacidad disponible; no existe una tarifa general de instancias bajo demanda más barata fuera de hora punta

**Buenas prácticas:**

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

2. **Optimizar la afinidad de nodos y la distribución de pods**:
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

- Una configuración de eksctl puede definir un grupo bajo demanda para las cargas del sistema y un grupo Spot diversificado para las aplicaciones. Las etiquetas por sí solas no aíslan las cargas. Configura deliberadamente los selectores y las tolerancias; no apliques taints a los únicos nodos de arranque antes de que puedan ejecutarse los controladores del sistema.
- En un módulo Terraform existente, `aws_eks_node_group` puede establecer `capacity_type = "SPOT"` y `scaling_config`. El clúster, el rol y las políticas IAM de los nodos, las subredes y el proveedor deben estar definidos previamente. Coordina quién controla `desired_size` con el escalador automático.
- Las etiquetas de los grupos de nodos de EKS no sustituyen las etiquetas del **ASG real** que usa Cluster Autoscaler para el descubrimiento. Inspecciona los ASG y quién administra sus etiquetas antes de modificarlas. Asocia la política del escalador automático a una identidad de controlador dedicada; los permisos adicionales del rol de nodo no son la identidad prevista.
- Mantén separadas las acciones de lectura y descubrimiento de AWS de las dos acciones de escritura de escalado. Restringe `autoscaling:SetDesiredCapacity` y `autoscaling:TerminateInstanceInAutoScalingGroup` a los ASG que tengan las etiquetas de propiedad del clúster y de habilitación revisadas, como indica la [política oficial de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html).

El siguiente fragmento de eksctl agrega grupos de nodos a un clúster existente. Verifica las subredes privadas del propietario, las políticas IAM de los nodos y las etiquetas existentes de los grupos/ASG; no es una receta independiente para crear un clúster.

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

El fragmento de Terraform presupone que los recursos del clúster y del rol de nodo nombrados, la variable de subredes privadas y el proveedor ya existen en el módulo propietario. La política IAM debe asociarse a la identidad dedicada del controlador.

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

Problemas de las otras opciones:
- **A. Usar siempre los tipos de instancia más grandes**: Esto causa sobreaprovisionamiento y costos innecesarios, y puede no ajustarse a los requisitos de la carga de trabajo.
- **B. Usar solo instancias bajo demanda para todas las cargas de trabajo**: Cuestan más que las instancias Spot, y muchas cargas pueden ejecutarse eficazmente en Spot.
- **D. Consolidar todas las cargas de trabajo en un único grupo de nodos**: Dificulta satisfacer los distintos requisitos, no proporciona aislamiento de recursos y complica la asignación y optimización de costos.
</details>

### 2. ¿Qué método es más eficaz para optimizar los costos de almacenamiento en Amazon EKS?

- A. Usar el tipo de almacenamiento más barato para todas las cargas de trabajo
- B. Migrar todos los datos a S3
- C. Elegir tipos de almacenamiento que satisfagan los requisitos de la carga e implementar la administración del ciclo de vida
- D. Reducir al mínimo el tamaño de todos los volúmenes
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Elegir tipos de almacenamiento que satisfagan los requisitos de la carga e implementar la administración del ciclo de vida**

**Explicación:**
El método más eficaz para optimizar los costos de almacenamiento en Amazon EKS es elegir tipos que satisfagan los requisitos de la carga de trabajo y administrar su ciclo de vida. Así se reducen costos sin dejar de cumplir los requisitos de rendimiento y se aprovechan niveles de almacenamiento adecuados al valor de los datos y a sus patrones de acceso.

**Estrategias clave para optimizar el almacenamiento:**

1. **Elegir tipos de almacenamiento adecuados para cada carga**:
   - Necesidades de alto rendimiento: io2, gp3 (EBS)
   - Acceso compartido: EFS
   - Procesamiento de datos a gran escala: FSx for Lustre
   - Datos de archivo: S3, S3 Glacier

2. **Administrar el ciclo de vida del almacenamiento**:
   - Datos de acceso frecuente: almacenamiento de alto rendimiento
   - Datos de acceso ocasional: almacenamiento estándar
   - Datos de acceso poco frecuente: almacenamiento de archivo de bajo costo

3. **Administrar los volúmenes de forma eficiente**:
   - Definir tamaños adecuados
   - Identificar y eliminar volúmenes sin uso
   - Administrar el ciclo de vida de las instantáneas

Los ejemplos de StorageClass requieren que estén instalados los controladores CSI y que la configuración de IAM, KMS y topología sea correcta. `WaitForFirstConsumer` coordina el aprovisionamiento de EBS con la planificación; `Retain` deja facturables los volúmenes liberados hasta que su propietario se ocupe de ellos. No se puede cambiar la clase de una PVC enlazada ni reducirla in situ. Las instantáneas, la restauración o una modificación admitida del tipo de volumen requieren una migración revisada por el propietario y una prueba de restauración. Auto Mode usa otro aprovisionador EBS; no lo sustituyas en silencio por los ejemplos de CSI estándar.

`create-file-system` no admite la opción `--lifecycle-policies`. En el sistema de archivos existente, usa `put-lifecycle-configuration` y conserva la matriz completa de políticas deseadas, como se muestra abajo. Las transiciones de S3 también requieren revisar la duración y el tamaño mínimos, los costos de solicitudes, el versionado y la latencia de recuperación; al reemplazar la configuración del ciclo de vida hay que conservar las reglas no relacionadas.

**Métodos de implementación:**

1. **Optimizar volúmenes EBS**:
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

2. **Administrar el ciclo de vida de EFS**:
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

3. **Definir una política de ciclo de vida de S3**:
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

4. **Administrar el ciclo de vida de instantáneas EBS**:
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

**Instantáneas programadas y revisión del almacenamiento**

La programación de instantáneas de abajo queda suspendida hasta que el propietario confirme la PVC existente `team-a/database-data`, el controlador EBS CSI estándar, el controlador y las CRD de instantáneas, y la clase `ebs-snapshot`. La plantilla montada usa `generateName` para evitar colisiones con un nombre fijo. El Role permite crear instantáneas en este espacio de nombres; no restringe el campo de PVC de origen. La coherencia de la aplicación, su pausa y la comprobación de la restauración son responsabilidades aparte. Un Job exitoso confirma la creación mediante la API, pero no que la instantánea esté lista; supervisa aparte `readyToUse` y los errores. Los límites del historial de Jobs **no** eliminan VolumeSnapshots ni instantáneas EBS. Define la retención y quién responde por la recuperación antes de habilitar la programación; `deletionPolicy: Delete` elimina la instantánea de respaldo cuando se elimina su objeto de instantánea de Kubernetes.

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

Elige el almacenamiento según el acceso y los objetivos de recuperación: una base de datos puede necesitar IOPS de io2/gp3, el contenido web compartido puede usar EFS, los registros y archivos suelen encajar en S3, y la analítica o la IA pueden necesitar FSx for Lustre o el rendimiento de EBS. «Caliente/templado/frío» es un ejemplo de clasificación, no un proceso automático de migración de EBS a EFS y luego a S3. Prepara por separado las clases `efs-standard` y `ebs-io2` mencionadas. Una solicitud de PVC `100Gi` no impone una cuota al sistema de archivos ni compra esa capacidad, y las etiquetas de una PVC no se convierten automáticamente en etiquetas de facturación de AWS.

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

El siguiente fragmento de Terraform requiere proveedores y una identidad del llamador configurados, además de una titularidad de recursos revisada. Los destinos de montaje, el acceso de red/IAM, las copias de seguridad de la aplicación y la retención son requisitos independientes; no constituye un despliegue completo de almacenamiento para producción.

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

**Inventario de candidatos de PVC de solo lectura**

Guarda el código Python siguiente como `unreferenced_pvcs.py` y ejecuta los comandos con un contexto y espacio de nombres explícitos. Informa de las PVC enlazadas que no aparecen referenciadas en la instantánea de Pods proporcionada; compara `(namespace, name)` y contempla los volúmenes que no son PVC. Kubernetes no proporciona una anotación estándar `pv_used`. Las listas de recursos no son instantáneas atómicas y omiten consumidores futuros o reducidos a cero de controladores, trabajos pendientes y requisitos de copia de seguridad/recuperación. Este resultado no justifica ninguna eliminación. Para candidatos EBS usa la consulta acotada por cuenta y etiquetas de la [pregunta 6 de EKS06](06-eks-monitoring-logging-quiz.md); `available` significa «sin adjuntar», no «sin uso».

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

Problemas de las otras opciones:
- **A. Usar el tipo de almacenamiento más barato para todas las cargas de trabajo**: Puede que no cumpla los requisitos de rendimiento y que perjudique a la aplicación y al negocio.
- **B. Migrar todos los datos a S3**: S3 sirve para ciertos datos, pero no para cargas sensibles a la latencia ni aplicaciones que necesitan almacenamiento de bloques.
- **D. Reducir al mínimo el tamaño de todos los volúmenes**: Una reducción excesiva puede dejar el volumen sin espacio; en algunos tipos, como gp2, el rendimiento depende del tamaño.
</details>

### 3. ¿Qué estrategia es más eficaz para optimizar los costos de red en Amazon EKS?

- A. Usar el ancho de banda de red más caro para todo el tráfico
- B. Colocar todos los servicios en una sola zona de disponibilidad
- C. Optimizar los patrones de tráfico, reducir los costos de transferencia y usar VPC endpoints
- D. Bloquear todo el tráfico de red
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Optimizar los patrones de tráfico, reducir los costos de transferencia y usar VPC endpoints**

**Explicación:**
La estrategia más eficaz para optimizar los costos de red en Amazon EKS es optimizar los patrones de tráfico, reducir el costo de transferencia de datos y utilizar VPC endpoints. Esto mejora la eficiencia del tráfico y evita costos innecesarios teniendo en cuenta los modelos de precios de red de AWS.

**Estrategias clave para optimizar los costos de red:**

1. **Optimizar los patrones de tráfico**:
   - Reducir el tráfico entre zonas de disponibilidad
   - Reducir el tráfico entre regiones
   - Implementar enrutamiento que tenga en cuenta la localidad

2. **Reducir los costos de transferencia de datos**:
   - Usar compresión y formatos de datos eficientes
   - Implementar estrategias de caché
   - Eliminar transferencias de datos innecesarias

3. **Usar VPC endpoints**:
   - Conexiones privadas a los servicios de AWS
   - Evitar pasar por los internet gateways
   - Reducir los costos de transferencia de datos

La distribución de topología controla la ubicación de los Pods; no selecciona los endpoints del tráfico de Service. `spec.topologyKeys` se eliminó. El ejemplo usa `trafficDistribution: PreferSameZone` (estable desde Kubernetes 1.35) con alternativa de reserva; no garantiza tráfico entre zonas igual a cero. Verifica el comportamiento real del proxy/CNI y las restricciones de disponibilidad.

Los gateway endpoints de S3/DynamoDB tienen precios distintos de los interface endpoints. Para extraer imágenes de ECR se necesita conectividad a `ecr.api`, `ecr.dkr` y S3, DNS privado y una regla de entrada TCP 443 en el security group del endpoint desde los nodos/Pods previstos. La CLI muestra un interface endpoint; aprovisiona también el equivalente DKR del fragmento Terraform de abajo. Revisa las políticas de endpoints y el modelo real de tráfico y costos por región; «privado» no significa «gratuito».

**Métodos de implementación:**

1. **Ubicar los Pods teniendo en cuenta las zonas de disponibilidad**:
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

2. **Enrutar según la topología del Service**:
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

3. **Configurar un VPC endpoint**:
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

4. **Enrutar por localidad con Istio**:
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

El failover por localidad de Istio requiere información de localidad de los endpoints y detección de valores atípicos. `failover.from/to` identifican **regiones**; usar ahí nombres de zonas de disponibilidad es incorrecto. DestinationRule usa las prioridades de localidad predeterminadas (primero la misma zona, después otras zonas/regiones) junto con la detección de valores atípicos. Los umbrales de expulsión del ejemplo deben probarse con la carga de trabajo. Es una opción independiente de la distribución del tráfico de Service mediante kube-proxy; no hace falta una service mesh solo para reducir costos de transferencia.



**Ejemplos adicionales de enrutamiento, endpoints y facturación**

NetworkPolicy permite el tráfico frontend→API→base de datos dentro del mismo espacio de nombres y la ruta estándar de Deployment de CoreDNS. Agrega otras dependencias requeridas y verifica que el CNI aplique las políticas. DNS local de nodos de Auto Mode u otra ruta del resolvedor requieren su propia regla apropiada. Ajusta los selectores a las etiquetas administradas reales.

VirtualService evalúa la primera regla coincidente, por eso la coincidencia premium va antes de la regla general y se definen los subsets correspondientes de DestinationRule. Las cargas deben tener esas etiquetas de versión. Un encabezado enviado por el cliente no demuestra que tenga autorización; aplícala en el servidor. EnvoyFilter apunta al espacio de nombres y las etiquetas reales del gateway de entrada, y debe validarse con la versión instalada de Istio/Envoy. Comprime las respuestas HTTP en el gateway; instalar un compresor en un sidecar de salida no comprime por sí solo las cargas enviadas. Los campos heredados `content_length`/`content_type` están obsoletos, pero no se eliminaron. Este ejemplo usa `response_direction_config/common_config`; prueba CPU, latencia, seguridad y protocolo.

El fragmento Terraform presupone que la VPC, las subredes privadas, el security group de endpoints y la tabla de rutas ya existen en el módulo propietario. El propietario de esa VPC mantiene NAT y asociaciones de rutas. Compartir un NAT zonal entre zonas es un compromiso entre disponibilidad y costo de transferencia, no el ahorro predeterminado para alta disponibilidad; evalúa por separado la opción de NAT regional.

Guarda el código Python como `network_costs.py`. Define `EXPECTED_CALLER_ACCOUNT`, `LINKED_ACCOUNT_ID`, `START_DATE` y `END_DATE`. `reviewed-usage-types.json` debe contener una matriz JSON con valores `USAGE_TYPE` exactos, seleccionados mediante Cost Explorer/GetDimensionValues. El ejemplo usa el endpoint comercial de facturación de AWS en us-east-1; verifica la cuenta llamadora y los permisos de lectura. Las consultas a la API pueden tener costo. Las dimensiones de GetCostAndUsage no admiten CONTAINS, así que el helper usa filtros exactos EQUALS. Completa la paginación y conserva cantidades Decimal, unidades monetarias y el estado estimado. Un resultado vacío o un error no demuestra que el costo total de red sea cero. Las filas a nivel de cuenta requieren una asignación verificada adicional de etiquetas y recursos antes de atribuirlas a un clúster EKS concreto. Solo se incluyen los tipos de uso seleccionados; buscar coincidencias parciales ambiguas de servicio/región/zona no permite clasificar con fiabilidad los cargos de Internet, entre zonas o entre regiones. Las fechas usan UTC y `End` es exclusivo; comprueba el historial disponible y el cierre definitivo de facturación. Los umbrales anteriores de 100/50/200 USD eran parámetros ilustrativos de triaje, no criterios universales de optimización.

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

Problemas de las otras opciones:
- **A. Usar el ancho de banda de red más caro para todo el tráfico**: Genera costos innecesarios y no todas las cargas requieren mucho ancho de banda.
- **B. Colocar todos los servicios en una sola zona de disponibilidad**: Puede incumplir los requisitos de disponibilidad multizona de las cargas críticas. Una sola zona en un entorno no crítico también requiere una decisión explícita sobre la tolerancia a fallos.
- **D. Bloquear todo el tráfico de red**: Es poco práctico y limita gravemente la funcionalidad de las aplicaciones.
</details>

### 4. ¿Qué método es más eficaz para optimizar los costos de administración de clústeres de Amazon EKS?

- A. Crear tantos clústeres como sea posible
- B. Consolidar todas las cargas de trabajo en un único clúster
- C. Ajustar la cantidad de clústeres a los requisitos de las cargas y reducir la sobrecarga de administración
- D. Administrar los clústeres manualmente
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ajustar la cantidad de clústeres a los requisitos de las cargas y reducir la sobrecarga de administración**

**Explicación:**
El método más eficaz para optimizar los costos de administración de clústeres de Amazon EKS es ajustar su cantidad a los requisitos de las cargas de trabajo y reducir la sobrecarga administrativa. Así se equilibran los costos de administrar los clústeres y la complejidad operativa, a la vez que se satisfacen las necesidades de aislamiento y seguridad.

**Estrategias clave para optimizar la administración de clústeres:**

1. **Mantener una cantidad adecuada de clústeres**:
   - Separarlos según los requisitos del negocio
   - Separarlos por entorno (desarrollo, staging y producción)
   - Tener en cuenta la seguridad y el cumplimiento

2. **Reducir la sobrecarga de administración**:
   - Usar herramientas automatizadas para administrar clústeres
   - Implementar infraestructura como código (IaC)
   - Centralizar el monitoreo y los registros

3. **Optimizar los recursos del clúster**:
   - Configurar adecuadamente el plano de control
   - Administrar eficientemente los grupos de nodos
   - Usar servicios compartidos

El comando breve de eksctl ilustra la creación, no una configuración de red/IAM lista para producción. Elige la versión de EKS del catálogo de AWS, revisa la VPC y la exposición del endpoint de API con la [guía de creación](../../eks/02-eks-cluster-creation.md), y asigna los permisos de controladores a identidades dedicadas. Los límites de tamaño de un grupo de nodos no instalan un escalador ni imponen un tope de gasto. También inciden en la comparación las tarifas de soporte estándar/ampliado, la capacidad opcional de Provisioned Control Plane y las dependencias de administración compartida.

El ejemplo de Terraform usa el módulo verificado **21.25.0**, cuya versión mínima del proveedor de AWS es **6.59**; el pin mostrado es 6.69.1. Las entradas no incluyen valores predeterminados inventados para el entorno. Proporciona red privada y acceso a la API bajo control del propietario, access entries revisadas, add-ons compatibles y fijados con sus asociaciones IAM, y grupos de nodos administrados. Los nodos EC2 estándar requieren la ruta de CNI/DNS/proxy adecuada; este no es un ejemplo de Auto Mode. Coordina quién administra `desired_size` con el escalador automático y usa estados/identidades de proveedor separados si el modelo de aislamiento lo exige. No se afirma que se haya ejecutado un plan/apply ni que esté listo para producción.

**Métodos de implementación:**

1. **Configurar de forma optimizada un clúster EKS**:
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

2. **Automatizar la administración del clúster con Terraform**:
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

3. **Administrar la configuración del clúster con GitOps**:
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

4. **Configurar un clúster multiinquilino**:
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

**Aislamiento, entradas de entorno y evidencia según el contexto**

La aplicación de Argo CD requiere un controlador instalado, el repositorio y commit revisados, y un AppProject `cluster-config` creado previamente que restrinja repositorios, destinos y tipos de recursos. Sustituye el SHA y el repositorio de ejemplo antes de usarla. La sincronización y la poda automáticas están deshabilitadas para la revisión inicial; el propietario solo debe habilitar el comportamiento de reconciliación previsto. Las credenciales y los controladores de administración compartidos pueden ampliar el impacto de fallos o seguridad entre clústeres que, de otro modo, estarían separados.

ResourceQuota limita la admisión y el número de objetos; no determina las facturas ni autoriza a los inquilinos. NetworkPolicy se combina de forma aditiva entre políticas y requiere que el CNI la aplique. El ejemplo de namespace permite tráfico dentro de `team-a`, hacia/desde el namespace compartido indicado y hacia un Deployment estándar de CoreDNS; adapta explícitamente DNS de nodo local/Auto Mode y otras dependencias. El ejemplo de API compartida permite solo a `team-a` llegar por TCP 8080 a Pods con la etiqueta `app: shared-api`. Reconcilia las políticas permisivas existentes en vez de dejar activa una política anterior que permita todo. RBAC, admisión, IAM y límites de confianza son controles separados.

El siguiente tfvars de entorno contiene overrides para el módulo revisado de arriba, no invocaciones a `./modules/eks-cluster`, que no se proporciona. Integra los valores apropiados de cuenta, red, versión, add-ons y acceso en las entradas de cada entorno y usa su propio backend/estado e identidad. Las listas y cantidades de instancias son ilustrativas; revisa la tolerancia a interrupciones y las opciones regionales actuales.

El script de recopilación opera sobre **un contexto explícito** por ejecución. Define `KUBE_CONTEXT`, `EXPECTED_API_SERVER`, `EXPECTED_CALLER_ACCOUNT`, `LINKED_ACCOUNT_ID`, `BILLING_TAG_KEY`, `BILLING_TAG_VALUE`, `START_DATE` y `END_DATE`; repite la operación deliberadamente para cada clúster. La URL del servidor de API debe coincidir con el clúster EKS revisado. Guarda muestras reales de Metrics API con sus marcas de tiempo, ventanas, unidades y todas las páginas de Cost Explorer limitadas por etiqueta, en vez de presentar como utilización de todos los clústeres los recursos solicitados de un solo contexto. Metrics Server y permisos de lectura son requisitos previos. La falta de muestras de nodos no equivale a uso cero, y muestras breves no representan el historial de demanda máxima.

Se usan endpoints comerciales de facturación de AWS y fechas finales exclusivas. Elige un período histórico disponible; las fechas de 2023 anteriores eran ejemplos de configuración, no resultados medidos. La asignación por etiquetas debe existir en facturación y puede omitir cargos sin etiqueta o compartidos. Se conservan las unidades monetarias, la base del costo y el estado estimado; el script no infiere el total a partir del primer grupo ni recomienda reducir recursos según un umbral de solicitudes/capacidad.

Un clúster compartido grande puede reducir la duplicación del plano de control y de servicios comunes, pero aumenta la coordinación y el impacto de los fallos. Clústeres pequeños pueden facilitar el mantenimiento independiente y delimitar las cargas, pero duplican capacidad y operaciones. Elige una separación híbrida según los requisitos de confianza, carga y recuperación; la cantidad de clústeres por sí sola no garantiza aislamiento ni un menor costo total.

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

Problemas de las otras opciones:
- **A. Crear tantos clústeres como sea posible**: Aumenta el costo del plano de control y la sobrecarga administrativa de cada clúster, y reduce el aprovechamiento de los recursos.
- **B. Consolidar todas las cargas de trabajo en un único clúster**: Puede convenir en algunos entornos, pero ignora los requisitos de seguridad, el aislamiento de las cargas y el radio de impacto de los fallos.
- **D. Administrar los clústeres manualmente**: Aumenta la posibilidad de errores, reduce la coherencia e incrementa la sobrecarga operativa.
</details>

### 5. ¿Qué método es más eficaz para monitorear y asignar costos en Amazon EKS?

- A. Revisar solo las facturas de AWS
- B. Implementar etiquetado, herramientas de asignación de costos y monitoreo continuo
- C. Asignar el mismo costo a todos los recursos
- D. Usar recursos sin monitorear sus costos
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Implementar etiquetado, herramientas de asignación de costos y monitoreo continuo**

**Explicación:**
El método más eficaz para monitorear y asignar los costos de Amazon EKS combina una estrategia de etiquetado, herramientas de asignación y monitoreo continuo. Esto permite hacer un seguimiento preciso, asignar costos por equipo o proyecto e identificar oportunidades de optimización.

**Estrategias clave de monitoreo y asignación de costos:**

1. **Estrategia integral de etiquetado**:
   - Etiquetas de unidad de negocio, equipo, proyecto y entorno
   - Reglas de etiquetado coherentes
   - Etiquetado automatizado

2. **Uso de herramientas para asignar costos**:
   - AWS Cost Explorer y AWS Budgets
   - Herramientas especializadas como Kubecost o CloudHealth
   - Paneles e informes personalizados

3. **Monitoreo y optimización continuos**:
   - Revisión y análisis periódicos de costos
   - Detección de anomalías y alertas
   - Aplicación de recomendaciones de optimización

Las etiquetas de Kubernetes, las etiquetas de recursos de AWS y las etiquetas activadas para facturación son distintas. Las etiquetas del namespace no se propagan automáticamente a Pods ni a recursos de AWS; coloca las etiquetas de la carga en la plantilla del Pod. La política de etiquetas de Organizations mostrada valida claves y valores configurados en recursos compatibles, incluidos los clústeres EKS. No agrega etiquetas ni configura su obligatoriedad. Revisa la política heredada y controles separados para detectar etiquetas faltantes. La activación y el backfill de facturación son operaciones aparte; el backfill de hasta 12 meses requiere que las etiquetas ya existieran históricamente.

El comando CUR siguiente crea un **CUR heredado**, no un panel de Cost Explorer ni una exportación CUR 2.0. AWS aún admite el CUR heredado. Los diseños nuevos deben evaluar Data Exports/CUR 2.0 en la [guía FinOps](../../ops/13-finops-cost-platform.md). El ejemplo heredado requiere un bucket existente en la región declarada, una política de entrega CUR revisada y permisos de informes. No crea el bucket, el esquema de Glue, la integración de Athena ni el panel. Sigue la política específica del servicio de entrega; no sustituyas la política `bcm-data-exports` de CUR 2.0 por la del servicio heredado.

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

2. **Configurar una política de etiquetas de AWS**:
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

3. **Instalar y configurar Kubecost**:
Usa la instalación comprobada de Kubecost 3.3.1 de la [guía de origen](../../eks/07-eks-cost-optimization.md), o OpenCost 1.121.2/chart 2.5.31 de la [pregunta 6 de EKS06](06-eks-monitoring-logging-quiz.md). Kubecost 3.x recopila con ClickHouse/direct finops-agent; los valores Prometheus y tokens de licencia de línea de comandos de 2.x no forman parte de esta configuración. Reutiliza un despliegue bajo un único propietario y revisa sus requisitos de migración, licencia y almacenamiento.

4. **Configurar la entrega de CUR heredado**:
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

Reutiliza el recopilador de la pregunta 4, acotado por contexto, cuenta y etiqueta, para obtener muestras reales de Metrics API y páginas de facturación. Solicitudes/límites son configuración declarada, no uso real; una relación solicitudes/límite inferior a 0,5 no justifica reducir las solicitudes. Compara la misma carga, ventana temporal, unidades y cobertura en lugar de comparar réplicas actuales con uso histórico. Concilia las asignaciones por equipo o centro de costos con los cargos sin etiqueta y compartidos. Para informes y alertas operativas usa el flujo explícito de recopilación/validación de la [guía FinOps](../../ops/13-finops-cost-platform.md); los errores y datos faltantes no deben convertirse en cero.

El presupuesto siguiente de 1.000 USD/80 % es ilustrativo. Verifica el formato real del filtro de etiquetas de Budgets activado y su cobertura; procesar alertas de facturación no impone un tope de gasto. El fragmento de Terraform presupone que ya existen un bucket CUR, la identidad del llamador, los proveedores y la entrada de región. Su propietario debe configurar acceso a resultados de Athena, retención/cifrado, tablas Glue y permisos de consulta. Terraform admite `aws_quicksight_dashboard`, pero aún deben configurarse la edición de la cuenta, los datasets/plantillas y los permisos.

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

En la llamada regional a TagResources, verifica la región de destino y examina `FailedResourcesMap`; que la CLI termine correctamente no demuestra que se hayan etiquetado todos los recursos solicitados. Confirma las etiquetas reales antes de usarlas para asignar cargos de facturación.

**Panel de tasa estimada de asignación**

Esto es una **estimación instantánea de la tasa de asignación de CPU+memoria en USD/hora** para Prometheus de un clúster. No es una factura ni el costo total de un namespace. Las entradas son métricas de asignación/precio de OpenCost (`job="opencost"` en este ejemplo) y etiquetas de Pods de kube-state-metrics (`job="kube-state-metrics"`). Confirma las etiquetas reales de jobs y la cobertura completa de CPU, memoria y precios. Conserva las etiquetas de namespace de las cargas del exporter mediante la configuración apropiada de `honor_labels` en ServiceMonitor. Un backend compartido necesita una identidad de clúster coherente en cada agregación y unión.

Integra el primer fragmento de values en el release administrado de kube-prometheus-stack. Las etiquetas de equipo del Pod deben estar acotadas y figurar en la plantilla del Pod; una etiqueta de namespace no las crea. Las etiquetas de equipo faltantes se agrupan como `unassigned`. Las consultas eliminan duplicados de copias idénticas de scrapes; resuelve aparte las fuentes de precios o propiedad que entren en conflicto. GPU, almacenamiento, red, plano de control, asignación inactiva/compartida, descuentos, créditos e impuestos no están incluidos en estos dos componentes. Los datos faltantes no equivalen a costo cero y una tasa no representa un monto mensual.

Las etiquetas de namespace/release de PrometheusRule deben coincidir con los selectores de la guía de origen. Antes de aprovisionar el panel, sustituye `REPLACE_WITH_PROMETHEUS_UID` por el origen de datos de un solo clúster que se haya revisado. La etiqueta ConfigMap `grafana_dashboard: "1"` coincide con el sidecar de la guía y el JSON correspondiente se proporciona abajo. Verifica el estado de las reglas, la cobertura de datos y las consultas del panel. Estos ejemplos no se conectaron a un despliegue real de facturación/Grafana.

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

Problemas de las otras opciones:
- **A. Revisar solo las facturas de AWS**: Solo muestran información general de costos, lo que dificulta identificar asignaciones detalladas u oportunidades de optimización.
- **C. Asignar el mismo costo a todos los recursos**: No refleja el uso real ni la generación de costos, y no aclara quién responde por el gasto del equipo o proyecto.
- **D. Usar recursos sin monitorear sus costos**: Impide detectar pronto los aumentos e identificar oportunidades de optimización, lo que complica administrar el presupuesto.
</details>

### 6. ¿Qué método facilita mejor un flujo de trabajo escalable para optimizar costos en EKS?

- A. Cambiar los recursos manualmente sin medir los resultados
- B. Considerar solo los datos de facturación e ignorar la telemetría de las cargas
- C. Combinar visibilidad de costos, telemetría de recursos y escalado apropiado con responsabilidades claras
- D. Ejecutar optimizadores sin coordinación sobre los mismos recursos
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Combinar visibilidad de costos, telemetría de recursos y escalado apropiado con responsabilidades claras**

**Explicación:**
Las herramientas nombradas son ejemplos de funciones complementarias, no un requisito de instalarlas todas. Elige una ruta de costos/telemetría con propietario definido y un escalado adecuado a la carga. EKS Auto Mode, Karpenter autoadministrado o Cluster Autoscaler pueden ya controlar la capacidad de nodos; separa responsabilidades y evita controladores que compitan. Hay que medir los ahorros y comprobar que se mantienen los SLO. Instalar herramientas de costos no conecta automáticamente los datos de facturación con las políticas de HPA/Karpenter.

**Herramientas y funciones clave para optimizar costos:**

1. **Kubecost**:
   - Visibilidad de los costos de recursos de Kubernetes
   - Asignación por namespace, Deployment y Service
   - Recomendaciones para optimizar costos
   - Pronóstico de costos y administración del presupuesto

2. **Karpenter**:
   - Aprovisionamiento y administración inteligentes de nodos
   - Selección de instancias dentro de las restricciones de carga, capacidad y precio
   - Comportamiento de aprovisionamiento/escalado que debe verificarse en el entorno real
   - Optimización del uso de instancias Spot

3. **AWS Cost Explorer**:
   - Análisis de costos de los servicios de AWS
   - Asignación de costos basada en etiquetas
   - Tendencias y pronóstico de costos
   - Recomendaciones de Reserved Instances y Savings Plans

4. **Herramientas de escalado automático de Kubernetes**:
   - Horizontal Pod Autoscaler (HPA)
   - Vertical Pod Autoscaler (VPA)
   - Cluster Autoscaler
   - Cluster Proportional Autoscaler

**Métodos de implementación:**

1. **Instalar y configurar Kubecost**:
Reutiliza los requisitos comprobados de instalación y datos de asignación de la pregunta 5 y la [guía de origen](../../eks/07-eks-cost-optimization.md). Kubecost 3.3.1 usa el chart actual `kubecost/kubecost` y una arquitectura de ClickHouse/direct-agent; las funciones dependen de la edición y la configuración. OpenCost es otra opción. No despliegues un segundo colector sobre una instalación que ya tiene propietario.

2. **Instalar y configurar Karpenter**:
Guarda lo siguiente como `karpenter-values.yaml`, sustituye la cuenta, el rol, el clúster, el endpoint y la cola por valores existentes y revisados, y sigue la [guía de Karpenter](../../autoscaling/02-karpenter.md). El ejemplo verificado usa 1.14.1; EKS 1.36 requiere al menos 1.13 según la matriz de compatibilidad. Son claves `settings.*`, no valores `controller.clusterName/clusterEndpoint` que se ignoran. La confianza IRSA debe coincidir con `system:serviceaccount:karpenter:karpenter` y su audiencia; no combines asignaciones IRSA y Pod Identity incompatibles. Prepara primero IAM del controlador y los nodos, acceso de nodos, subredes/security groups, cola y eventos de interrupción y capacidad de arranque fiable. Una instalación Helm nueva y una actualización de CRD tienen propietarios y ciclos de vida distintos; actualizar el controlador no actualiza las CRD existentes.

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
   - Kubecost: análisis de los costos de recursos dentro del clúster
   - AWS Cost Explorer: análisis de costos de todos los servicios AWS
   - Paneles integrados: resumen general y tendencias de costos

2. **Optimización automática de recursos**:
   - Karpenter: aprovisionamiento y administración óptimos de nodos
   - HPA/VPA: optimización de recursos en las cargas de trabajo
   - Instancias Spot: recursos de cómputo eficientes en costos

3. **Asignación de costos y responsabilidades**:
   - Asignación de costos mediante etiquetas
   - Análisis por namespace y etiqueta
   - Informes de costos por equipo y proyecto

4. **Optimización y mejora continuas**:
   - Aplicar recomendaciones para optimizar costos
   - Revisar y analizar los costos periódicamente
   - Fijar y seguir objetivos de reducción de costos

**Integración bajo control y validación de la API**

Los ejemplos de VPA usan Off mientras HPA emplea denominadores de utilización de CPU/memoria. Habilita los cambios automáticos de solicitudes solo después de coordinar ese ciclo de control. Cluster Proportional Autoscaler ajusta las réplicas de componentes según señales del tamaño del clúster; no aprovisiona nodos de forma equivalente. Los límites, preferencias de instancias y demoras de consolidación de Karpenter no garantizan un tope de gasto ni un plazo de terminación. Inspecciona las AMI resueltas y fija una versión/ID probados para los cambios controlados; no trates `al2023@latest` como inmutable.

PriorityClass controla la prioridad de planificación/expulsión, no la asignación de costos ni la disponibilidad garantizada. Controla quién puede asignar prioridades; la expulsión del scheduler hace lo posible por respetar los PDB. Revisa las interrupciones y la recuperación de las cargas. Las observaciones y recomendaciones de costos necesitan una ruta explícita de política/cambio revisada antes de que actúen los controladores; el diagrama de arquitectura no implementa esa integración.

La alternativa Terraform usa la configuración mediante archivo de values del proveedor Helm 3.3.0 y el proveedor AWS 6.69.1. Proporciona el contexto de Kubernetes explícito y valores de chart revisados, incluidas referencias compatibles de identidad, almacenamiento y secreto de licencia; no crea esos requisitos previos. No pongas credenciales sin procesar de licencia o de nube en values ni en el estado. Reconcilia un release existente con su propietario en lugar de instalarlo de nuevo mediante otro gestor. El presupuesto de 1.000 USD/80 % es ilustrativo, usa un filtro de etiqueta de facturación verificado y no es un límite máximo de gasto. En esta auditoría no se aprovisionó ningún clúster/Helm ni se envió notificación.

El ejemplo de API siguiente apunta expresamente a OpenCost 1.121.2 configurado antes, no a una URL de Kubecost 3.x supuesta. Su API `/allocation` admite la agregación `namespace,controllerKind,controller`; `deployment` no es una clave de agregación genérica documentada. La respuesta contiene una matriz de mapas de conjuntos de asignación, no un diccionario directo namespace/Deployment. Valida errores HTTP/API y cobertura de datos; un resultado vacío no significa costo cero ni demuestra sobreaprovisionamiento. Las cantidades de asignación, uso, solicitudes, byte-hours/core-hours y recuentos actuales de réplicas tienen significados y ventanas distintos. Inspecciona el esquema versionado y métricas comparables de la carga antes de recomendar el dimensionamiento. Concilia las estimaciones de asignación sin procesar con facturación y políticas de costos inactivos/compartidos.





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

Las otras opciones omiten la medición, las señales de las cargas o la coordinación de responsabilidades. Los controladores que compiten pueden perjudicar la estabilidad y la previsibilidad de costos.
</details>
