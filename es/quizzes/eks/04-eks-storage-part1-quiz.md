# Cuestionario de almacenamiento de EKS - Parte 1

Este cuestionario evalúa tu comprensión de los conceptos de almacenamiento en Amazon EKS, incluidos persistent volumes, storage classes y dynamic provisioning.

## Preguntas de opción múltiple

### 1. ¿Qué storage driver es compatible de forma nativa con Amazon EKS de manera predeterminada?

A. Amazon EFS CSI Driver B. Amazon EBS CSI Driver C. Amazon FSx for Lustre CSI Driver D. Amazon S3 CSI Driver

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Amazon EBS CSI Driver**

**Explicación:** El storage driver compatible de forma nativa con Amazon EKS de manera predeterminada es Amazon EBS CSI (Container Storage Interface) Driver. Este driver permite usar volúmenes de Amazon Elastic Block Store (EBS) como almacenamiento persistente en clusters de Amazon EKS.

**Características clave:**

1.  **Disponible como EKS Add-on**: Amazon EBS CSI driver se proporciona como EKS add-on para facilitar la instalación y la administración.

    ```bash
    aws eks create-addon \
      --cluster-name my-cluster \
      --addon-name aws-ebs-csi-driver \
      --service-account-role-arn arn:aws:iam::111122223333:role/AmazonEKS_EBS_CSI_DriverRole
    ```
2.  **Compatibilidad con Dynamic Provisioning**: Admite dynamic provisioning de volúmenes EBS mediante StorageClass.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
3.  **Compatibilidad con Volume Snapshot**: Admite la funcionalidad de snapshot y restauración de volúmenes.

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      name: ebs-volume-snapshot
    spec:
      volumeSnapshotClassName: ebs-snapshot-class
      source:
        persistentVolumeClaimName: ebs-claim
    ```
4. **Varios tipos de volúmenes EBS**: Admite varios tipos de volúmenes EBS, incluidos gp2, gp3, io1, io2, sc1, st1.

**Permisos IAM requeridos:**

El EBS CSI driver requiere los siguientes permisos IAM para operar:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSnapshot",
        "ec2:AttachVolume",
        "ec2:DetachVolume",
        "ec2:ModifyVolume",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeInstances",
        "ec2:DescribeSnapshots",
        "ec2:DescribeTags",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumesModifications"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:volume/*",
        "arn:aws:ec2:*:*:snapshot/*"
      ],
      "Condition": {
        "StringEquals": {
          "ec2:CreateAction": [
            "CreateVolume",
            "CreateSnapshot"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteTags"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:volume/*",
        "arn:aws:ec2:*:*:snapshot/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:RequestTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:RequestTag/CSIVolumeName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/CSIVolumeName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/kubernetes.io/created-for/pvc/name": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/CSIVolumeSnapshotName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    }
  ]
}
```

**Limitaciones:**

1. **Restricción de Availability Zone**: Los volúmenes EBS están restringidos a una sola availability zone, por lo que los pods deben ejecutarse en la misma availability zone que el volumen.
2. **Montaje en un solo Node**: Los volúmenes EBS solo pueden montarse en un node a la vez (modo de acceso ReadWriteOnce).
3. **Limitación de Fargate**: Amazon EKS Fargate actualmente no admite el EBS CSI driver.

Problemas con las otras opciones:

* **A. Amazon EFS CSI Driver**: El EFS CSI driver es compatible con EKS, pero no se instala de forma predeterminada. Debe instalarse por separado.
* **C. Amazon FSx for Lustre CSI Driver**: El FSx for Lustre CSI driver es compatible con EKS, pero no se instala de forma predeterminada. Debe instalarse por separado.
* **D. Amazon S3 CSI Driver**: Actualmente no existe un Amazon S3 CSI driver oficial. Normalmente se accede a S3 mediante la API de S3 en lugar de montarlo directamente mediante CSI.

</details>

### 2. ¿Cuál es la solución de almacenamiento más adecuada cuando múltiples pods en Amazon EKS necesitan acceso simultáneo de lectura/escritura?

A. Amazon EBS B. Amazon EFS C. Amazon S3 D. Amazon FSx for Lustre

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Amazon EFS**

**Explicación:** La solución de almacenamiento más adecuada cuando múltiples pods en Amazon EKS necesitan acceso simultáneo de lectura/escritura es Amazon EFS (Elastic File System). EFS es un servicio NFS (Network File System) administrado que admite el modo de acceso ReadWriteMany (RWX), lo que permite que varios pods lean y escriban simultáneamente en el mismo volumen.

**Características clave:**

1. **Acceso Multi-Availability Zone**: Se puede acceder a EFS desde múltiples availability zones, lo que permite que pods que se ejecutan en diferentes nodes y availability zones accedan a los mismos datos.
2.  **Compatibilidad con ReadWriteMany**: EFS admite el modo de acceso ReadWriteMany (RWX), lo que permite que varios pods lean y escriban simultáneamente en el mismo volumen.

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: efs-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: efs-sc
      resources:
        requests:
          storage: 5Gi
    ```
3. **Escalabilidad**: EFS escala automáticamente, eliminando la necesidad de planificar capacidad.
4. **Durabilidad y disponibilidad**: Proporciona 99.999999999% (11 nueves) de durabilidad y 99.99% de disponibilidad.

**Instalación del EFS CSI Driver:**

```bash
# Install using Helm
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

**Creación de EFS File System:**

```bash
# Create EFS file system
aws efs create-file-system \
  --creation-token eks-efs \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=EKS-EFS

# Create mount target
aws efs create-mount-target \
  --file-system-id fs-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0 \
  --security-groups sg-0123456789abcdef0
```

**Configuración de StorageClass y PVC:**

```yaml
# Create StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"

# Create PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

**Casos de uso:**

1. **Shared File System**: Cuando múltiples pods necesitan acceder a los mismos archivos
2. **Contenido de Web Server**: Cuando múltiples pods de web server necesitan servir el mismo contenido estático
3. **Agregación de logs**: Cuando múltiples pods escriben en el mismo directorio de logs
4. **Pipelines CI/CD**: Cuando los artefactos de build deben compartirse

**Consideraciones de rendimiento:**

1. **Modos de rendimiento**:
   * General Purpose: Adecuado para la mayoría de las cargas de trabajo
   * Max I/O: Adecuado para cargas de trabajo que requieren alto throughput
2. **Modos de throughput**:
   * Bursting: Modo predeterminado, proporciona burst credits según el tamaño del file system
   * Provisioned: Aprovisiona throughput específico cuando se necesita throughput constante
3. **Latencia**: EFS puede tener mayor latencia que el block storage, por lo que puede no ser adecuado para aplicaciones sensibles a la latencia.

**Consideraciones de seguridad:**

1.  **Cifrado**: EFS admite cifrado en tránsito y en reposo.

    ```bash
    aws efs create-file-system \
      --creation-token eks-efs \
      --encrypted \
      --kms-key-id 1234abcd-12ab-34cd-56ef-1234567890ab
    ```
2. **Control de acceso**: El acceso puede controlarse mediante políticas IAM, network ACLs y security groups.
3. **Access Points**: Los EFS access points pueden usarse para restringir el acceso a directorios específicos.

Problemas con las otras opciones:

* **A. Amazon EBS**: EBS solo admite el modo de acceso ReadWriteOnce (RWO), por lo que solo puede montarse en un node a la vez.
* **C. Amazon S3**: S3 es object storage, no un file system, por lo que no puede montarse directamente mediante interfaces estándar de file system.
* **D. Amazon FSx for Lustre**: FSx for Lustre es adecuado para cargas de trabajo de alto rendimiento, pero tiene una configuración más compleja y costos más altos en comparación con EFS.

</details>

### 4. ¿Cuál es una limitación al usar volúmenes EBS en Amazon EKS?

A. Los volúmenes EBS pueden tener acceso simultáneo de lectura/escritura desde múltiples pods B. Se puede acceder a los volúmenes EBS desde múltiples availability zones C. Los volúmenes EBS solo pueden tener acceso de lectura/escritura desde un pod a la vez D. Los volúmenes EBS pueden usarse con pods de Fargate

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. Los volúmenes EBS solo pueden tener acceso de lectura/escritura desde un pod a la vez**

**Explicación:** Los volúmenes de Amazon EBS (Elastic Block Store) solo pueden tener acceso de lectura/escritura desde un pod a la vez. Esta es una limitación fundamental de EBS, ya que los volúmenes EBS solo admiten el modo de acceso ReadWriteOnce (RWO).

**Limitaciones clave:**

1. **Montaje en un solo Node**: Los volúmenes EBS solo pueden montarse en una instancia EC2 a la vez. Por lo tanto, los pods en múltiples nodes no pueden acceder al mismo volumen EBS.
2.  **Restricción de Availability Zone**: Los volúmenes EBS están restringidos a la availability zone donde se crearon. Los pods que se ejecutan en nodes de diferentes availability zones no pueden acceder a ese volumen.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer  # Delay volume creation until pod is scheduled
    ```
3. **Incompatibilidad con Fargate**: Amazon EKS Fargate actualmente no admite volúmenes EBS. Los pods de Fargate no pueden montar volúmenes EBS.
4.  **Limitación del modo de acceso**: EBS solo admite el siguiente modo de acceso:

    * ReadWriteOnce (RWO): Montaje de lectura-escritura por un solo node

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim
    spec:
      accessModes:
        - ReadWriteOnce  # The only access mode supported by EBS
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 10Gi
    ```

**Alternativas para abordar estas limitaciones:**

1.  **Usar StatefulSet**: Ejecutar aplicaciones stateful proporcionando volúmenes EBS dedicados a cada pod

    ```yaml
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: web
    spec:
      serviceName: "nginx"
      replicas: 3
      selector:
        matchLabels:
          app: nginx
      template:
        metadata:
          labels:
            app: nginx
        spec:
          containers:
          - name: nginx
            image: nginx
            volumeMounts:
            - name: www
              mountPath: /usr/share/nginx/html
      volumeClaimTemplates:
      - metadata:
          name: www
        spec:
          accessModes: [ "ReadWriteOnce" ]
          storageClassName: ebs-sc
          resources:
            requests:
              storage: 10Gi
    ```
2. **Usar Amazon EFS**: Usar EFS, que admite el modo de acceso ReadWriteMany (RWX), cuando múltiples pods necesitan acceder al mismo volumen
3. **Replicación de volúmenes**: Replicar datos en múltiples volúmenes EBS para permitir el acceso desde múltiples pods
4. **Scheduling con conocimiento de topología**: Usar `volumeBindingMode: WaitForFirstConsumer` para crear volúmenes en la availability zone donde se programa el pod

**Consideraciones de Availability Zone:**

1.  **Usar Node Selector**: Programar pods en nodes de availability zones específicas

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: az-pod
    spec:
      nodeSelector:
        topology.kubernetes.io/zone: us-west-2a
      containers:
      - name: app
        image: nginx
    ```
2.  **Volume Snapshot y restauración**: Usar volume snapshots cuando sea necesario mover datos a diferentes availability zones

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      name: ebs-snapshot
    spec:
      volumeSnapshotClassName: ebs-snapshot-class
      source:
        persistentVolumeClaimName: ebs-claim
    ```

**Buenas prácticas:**

1. **Selección de almacenamiento adecuada**: Selecciona el tipo de almacenamiento adecuado según los requisitos de la carga de trabajo
   * Acceso de un solo pod: EBS
   * Acceso de múltiples pods: EFS
   * Cargas de trabajo de alto rendimiento: FSx for Lustre
2. **Deployment con conocimiento de Availability Zone**: Asegúrate de que los pods y los volúmenes estén en la misma availability zone
3. **Backup de volúmenes**: Protege los datos con snapshots regulares

Problemas con las otras opciones:

* **A. Los volúmenes EBS pueden tener acceso simultáneo de lectura/escritura desde múltiples pods**: Esto es incorrecto. Los volúmenes EBS solo admiten el modo de acceso ReadWriteOnce (RWO).
* **B. Se puede acceder a los volúmenes EBS desde múltiples availability zones**: Esto es incorrecto. Los volúmenes EBS están restringidos a la availability zone donde se crearon.
* **D. Los volúmenes EBS pueden usarse con pods de Fargate**: Esto es incorrecto. Amazon EKS Fargate actualmente no admite volúmenes EBS.

</details>

## Preguntas de respuesta corta

### 6. ¿Qué modo de acceso debe especificarse en un PersistentVolumeClaim para el dynamic provisioning de volúmenes EBS en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** ReadWriteOnce (RWO)

**Explicación detallada:**

El modo de acceso que debe especificarse en un PersistentVolumeClaim (PVC) para el dynamic provisioning de volúmenes EBS en Amazon EKS es ReadWriteOnce (RWO). Esto se debe a las características fundamentales de los volúmenes EBS, que solo pueden tener acceso de lectura/escritura desde un node a la vez.

**Descripciones de modos de acceso:**

1. **ReadWriteOnce (RWO)**: El volumen puede montarse en modo lectura-escritura por un solo node.
2. **ReadOnlyMany (ROX)**: El volumen puede montarse en modo solo lectura por múltiples nodes.
3. **ReadWriteMany (RWX)**: El volumen puede montarse en modo lectura-escritura por múltiples nodes.

**Por qué EBS solo admite RWO:**

Amazon EBS es un servicio de block storage diseñado para adjuntarse a una sola instancia EC2 a la vez. Esto no es una limitación de hardware, sino una característica de diseño del servicio EBS. Por lo tanto, los volúmenes EBS solo admiten el modo de acceso ReadWriteOnce.

**Ejemplo de PVC:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce  # The only access mode supported by EBS
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 10Gi
```

**Alternativas cuando se necesitan otros modos de acceso:**

1. **Cuando se necesita ReadOnlyMany (ROX):**
   * Crear un EBS snapshot y crear múltiples volúmenes EBS de solo lectura
   * Proporcionar volúmenes separados de solo lectura a cada node
2.  **Cuando se necesita ReadWriteMany (RWX):**

    * Usar Amazon EFS (file system basado en NFS)

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: efs-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: efs-sc
      resources:
        requests:
          storage: 5Gi
    ```

**Consideraciones al usar volúmenes EBS:**

1. **Pod Scheduling**: Los pods que usan volúmenes EBS solo pueden ejecutarse en nodes donde el volumen está adjunto.
2. **Restricción de Availability Zone**: Los volúmenes EBS están restringidos a la availability zone donde se crearon. Por lo tanto, los pods solo pueden ejecutarse en nodes de esa availability zone.
3.  **Volume Binding Mode**: Se recomienda usar `WaitForFirstConsumer` para crear volúmenes después de que el pod se programe.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```
4. **Uso con StatefulSet**: StatefulSet proporciona PVCs únicos a cada pod, lo que lo hace adecuado para su uso con volúmenes EBS.

**Guía de selección de modos de acceso:**

| Tipo de almacenamiento | ReadWriteOnce | ReadOnlyMany | ReadWriteMany |
| ---------------------- | ------------- | ------------ | ------------- |
| Amazon EBS             | ✓             | ✗            | ✗             |
| Amazon EFS             | ✓             | ✓            | ✓             |
| FSx for Lustre         | ✓             | ✓            | ✓             |

Cuando uses volúmenes EBS, especifica siempre el modo de acceso ReadWriteOnce. Si se requiere acceso simultáneo desde múltiples nodes, considera alternativas como EFS o FSx for Lustre.

</details>

### 7. ¿Qué sucede con los datos cuando un pod que usa un volumen EBS en Amazon EKS se mueve a un node diferente?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** El volumen EBS se separa del node anterior y se adjunta al nuevo node. Los datos se conservan, pero puede haber demoras durante el proceso de readjunción del volumen.

**Explicación detallada:**

Cuando un pod que usa un volumen EBS en Amazon EKS se mueve a un node diferente (por ejemplo, debido a una falla de node, escalado, actualizaciones, etc.), el volumen EBS se separa del node anterior y se adjunta al nuevo node. Durante este proceso, los datos se conservan, pero puede haber demoras durante el proceso de readjunción del volumen.

**Proceso de readjunción del volumen:**

1. **Terminación del Pod**: El pod se termina en el node original.
2. **Separación del volumen**: El volumen EBS se separa del node original.
3. **Adjunción del volumen**: El volumen EBS se adjunta al nuevo node.
4. **Inicio del Pod**: El pod se inicia en el nuevo node y el volumen se monta.

**Impacto de este proceso:**

1. **Tiempo de demora**: Las operaciones de separación y adjunción de volúmenes suelen tardar entre 10 y 30 segundos, pero pueden tardar más en algunos casos.
2. **Restricción de Availability Zone**: Los volúmenes EBS están restringidos a la availability zone donde se crearon, por lo que los pods solo pueden moverse a otros nodes dentro de la misma availability zone.
3. **Persistencia de datos**: Los datos se conservan y no se pierden durante el proceso de readjunción del volumen.

**Estrategias para manejar este comportamiento:**

1.  **Usar PodDisruptionBudget**: Garantizar la disponibilidad limitando la cantidad de pods que pueden interrumpirse simultáneamente

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
2.  **Configurar readinessProbe y livenessProbe adecuados**: Retrasar la recepción de tráfico hasta que el volumen esté correctamente montado y la aplicación esté lista

    ```yaml
    readinessProbe:
      exec:
        command:
        - cat
        - /data/ready
      initialDelaySeconds: 5
      periodSeconds: 5
    ```
3. **Usar StatefulSet**: StatefulSet proporciona deployment y escalado secuenciales para minimizar el impacto de la readjunción de volúmenes.
4.  **Optimizar Volume Binding Mode**: Usar `WaitForFirstConsumer` para crear volúmenes en la availability zone donde se programa el pod

    ```yaml
    volumeBindingMode: WaitForFirstConsumer
    ```

**Consideraciones de Availability Zone:**

1. **Deployment Multi-AZ**: Desplegar aplicaciones en múltiples availability zones para tener resiliencia frente a fallas de una sola AZ
2.  **Topology Spread**: Usar `topologySpreadConstraints` para distribuir pods entre múltiples availability zones

    ```yaml
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: my-app
    ```
3. **PDB con conocimiento de Availability Zone**: Configurar PodDisruptionBudgets separados para cada availability zone

**Buenas prácticas:**

1. **Optimizar aplicaciones para reinicio rápido**: Diseñar aplicaciones para que se inicien e inicialicen rápidamente
2.  **Establecer un Termination Grace Period adecuado**: Proporcionar tiempo suficiente para que las aplicaciones terminen correctamente

    ```yaml
    terminationGracePeriodSeconds: 60
    ```
3. **Estrategia de backup para datos críticos**: Proteger los datos mediante snapshots o backups regulares
4. **Considerar un diseño stateless**: Cuando sea posible, diseñar aplicaciones como stateless para minimizar el impacto de los movimientos de node

Cuando un pod que usa un volumen EBS se mueve entre nodes, los datos se conservan, pero pueden producirse demoras durante el proceso de readjunción del volumen, por lo que es importante diseñar y configurar la aplicación teniendo esto en cuenta.

</details>

### 9. ¿Qué recurso de la Kubernetes API se usa para crear snapshots de volúmenes EBS en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** VolumeSnapshot

**Explicación detallada:**

El recurso de la Kubernetes API usado para crear snapshots de volúmenes EBS en Amazon EKS es `VolumeSnapshot`. Este recurso forma parte de la Kubernetes Volume Snapshot API y funciona con CSI (Container Storage Interface) drivers para crear copias puntuales de persistent volumes.

**Requisitos previos para usar VolumeSnapshot:**

1. **Instalación del EBS CSI Driver**: El AWS EBS CSI driver debe estar instalado en el cluster.
2.  **Instalación del Snapshot Controller**: El snapshot controller de Kubernetes debe estar instalado en el cluster.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/rbac-snapshot-controller.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/setup-snapshot-controller.yaml
    ```
3. **Crear VolumeSnapshotClass**: Crear una VolumeSnapshotClass que defina cómo se crean los snapshots.

**Ejemplo de VolumeSnapshotClass:**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

**Ejemplo de creación de VolumeSnapshot:**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-volume-snapshot
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: ebs-claim
```

**Verificar el estado del Snapshot:**

```bash
kubectl get volumesnapshot ebs-volume-snapshot
```

**Crear un nuevo PVC desde un Snapshot:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim-from-snapshot
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 10Gi
  dataSource:
    name: ebs-volume-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

**Beneficios clave de VolumeSnapshot:**

1. **Protección de datos**: Crear backups puntuales de datos críticos
2. **Disaster Recovery**: Admitir la recuperación en caso de pérdida o corrupción de datos
3. **Replicación de entornos**: Replicar datos de producción para entornos de desarrollo o prueba
4. **Migración de datos**: Mover datos de un cluster a otro

**Gestión del ciclo de vida de Snapshots:**

1.  **Creación automatizada de Snapshots**: Automatizar la creación regular de snapshots mediante CronJob

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: volume-snapshot-job
    spec:
      schedule: "0 0 * * *"  # Daily at midnight
      jobTemplate:
        spec:
          template:
            spec:
              serviceAccountName: snapshot-creator
              containers:
              - name: snapshot-creator
                image: bitnami/kubectl:latest
                command:
                - /bin/sh
                - -c
                - |
                  cat <<EOF | kubectl apply -f -
                  apiVersion: snapshot.storage.k8s.io/v1
                  kind: VolumeSnapshot
                  metadata:
                    name: ebs-snapshot-$(date +%Y%m%d)
                  spec:
                    volumeSnapshotClassName: ebs-snapshot-class
                    source:
                      persistentVolumeClaimName: ebs-claim
                  EOF
              restartPolicy: OnFailure
    ```
2.  **Política de retención de Snapshots**: Eliminar automáticamente snapshots antiguos

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: snapshot-cleanup-job
    spec:
      schedule: "0 1 * * *"  # Daily at 1 AM
      jobTemplate:
        spec:
          template:
            spec:
              serviceAccountName: snapshot-manager
              containers:
              - name: snapshot-cleaner
                image: bitnami/kubectl:latest
                command:
                - /bin/sh
                - -c
                - |
                  # Delete snapshots older than 30 days
                  kubectl get volumesnapshot -o json | jq -r '.items[] | select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) | .metadata.name' | xargs -r kubectl delete volumesnapshot
              restartPolicy: OnFailure
    ```

**Buenas prácticas:**

1. **Snapshots regulares**: Configurar programas de snapshots regulares para datos críticos
2. **Probar Snapshots**: Probar regularmente la restauración desde snapshots para verificar la validez del backup
3. **Etiquetado**: Aplicar tags adecuados a los snapshots para facilitar la administración y el seguimiento de costos
4. **Monitoreo de costos**: Monitorear y optimizar costos, ya que los snapshots de EBS generan cargos adicionales
5. **Cifrado**: Usar snapshots cifrados para datos sensibles

Usar la VolumeSnapshot API te permite crear y administrar snapshots de volúmenes EBS de una manera nativa de Kubernetes, habilitando una implementación eficaz de estrategias de protección y recuperación de datos.

</details>

## Preguntas prácticas

### 10. Diseña una solución de almacenamiento para aplicaciones con diversos requisitos de almacenamiento en un cluster de Amazon EKS. Crea storage classes y persistent volume claims que cumplan los siguientes requisitos:

* Block storage de alto rendimiento para bases de datos
* Archivos de configuración que deben compartirse entre múltiples pods
* Parallel file system de alto rendimiento para cargas de trabajo de AI/ML

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

Aquí tienes una solución de almacenamiento para cumplir diversos requisitos de almacenamiento en un cluster de Amazon EKS:

### 1. Block Storage de alto rendimiento para bases de datos (Amazon EBS gp3)

#### Definición de StorageClass:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-db
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  iops: "16000"  # Maximum IOPS
  throughput: "1000"  # Maximum throughput (MB/s)
  encrypted: "true"
allowVolumeExpansion: true
```

#### Definición de PersistentVolumeClaim:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-data
  namespace: database
spec:
  accessModes:
    - ReadWriteOnce  # EBS can only be mounted to a single node
  storageClassName: ebs-gp3-db
  resources:
    requests:
      storage: 100Gi
```

#### Ejemplo de Database Pod:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: "postgres"
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: ebs-gp3-db
      resources:
        requests:
          storage: 100Gi
```

**Explicación:**

* **Tipo de volumen gp3**: Proporciona hasta 16,000 IOPS y 1,000MB/s de throughput, adecuado para cargas de trabajo de bases de datos.
* **WaitForFirstConsumer**: Retrasa la creación del volumen hasta el scheduling del pod para evitar problemas de availability zone.
* **Cifrado**: Habilita el cifrado de volúmenes EBS para la seguridad de datos en reposo.
* **Expansión de volumen**: Permite expandir el volumen para futuros aumentos de tamaño de la base de datos.
* **StatefulSet**: Proporciona IDs de red estables y almacenamiento persistente para bases de datos.

### 2. Archivos de configuración compartidos entre múltiples pods (Amazon EFS)

#### Instalación del EFS CSI Driver:

```bash
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

#### Definición de StorageClass:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0  # Existing EFS file system ID
  directoryPerms: "700"
```

#### Definición de PersistentVolumeClaim:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage
  namespace: application
spec:
  accessModes:
    - ReadWriteMany  # Multiple pods can read/write simultaneously
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi  # This value is symbolic as EFS auto-scales
```

#### Ejemplo de Deployment usando archivos de configuración:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: application
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: nginx:latest
        volumeMounts:
        - name: config-volume
          mountPath: /etc/config
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
      volumes:
      - name: config-volume
        persistentVolumeClaim:
          claimName: config-storage
```

**Explicación:**

* **Modo de acceso ReadWriteMany**: EFS admite que múltiples pods lean y escriban simultáneamente en el mismo volumen.
* **Compatibilidad Multi-Availability Zone**: Se puede acceder a EFS desde múltiples availability zones, lo que proporciona resiliencia frente a fallas de node.
* **Auto Scaling**: EFS escala automáticamente según el uso, eliminando la necesidad de planificar capacidad.
* **Access Points**: Los EFS access points pueden usarse para restringir el acceso a directorios específicos.

### 3. Parallel File System de alto rendimiento para cargas de trabajo de AI/ML (Amazon FSx for Lustre)

#### Instalación del FSx CSI Driver:

```bash
helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
helm repo update
helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=fsx-csi-controller-sa
```

#### Definición de StorageClass:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0  # Subnet for FSx file system
  securityGroupIds: sg-0123456789abcdef0  # Security group for FSx file system
  deploymentType: SCRATCH_2  # High-performance temporary storage
  perUnitStorageThroughput: "200"  # MB/s/TiB
  dataCompressionType: "LZ4"  # Enable data compression
  s3ImportPath: s3://ml-training-data-bucket/  # Optional: Import data from S3
mountOptions:
  - flock
```

#### Definición de PersistentVolumeClaim:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-training-data
  namespace: ml-workloads
spec:
  accessModes:
    - ReadWriteMany  # Multiple pods can read/write simultaneously
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi  # FSx for Lustre starts at minimum 1.2TiB
```

#### Ejemplo de ML Training Job:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: ml-workloads
spec:
  parallelism: 4  # Number of parallel jobs
  template:
    spec:
      containers:
      - name: training
        image: tensorflow/tensorflow:latest-gpu
        command:
          - "python"
          - "/training/train.py"
        volumeMounts:
        - name: training-data
          mountPath: "/training"
        resources:
          limits:
            nvidia.com/gpu: 4  # GPU resource request
          requests:
            cpu: "8"
            memory: "32Gi"
      volumes:
      - name: training-data
        persistentVolumeClaim:
          claimName: ml-training-data
      restartPolicy: Never
  backoffLimit: 2
```

**Explicación:**

* **Alto rendimiento**: FSx for Lustre proporciona cientos de GB/s de throughput y millones de IOPS, adecuado para cargas de trabajo de AI/ML.
* **Acceso paralelo**: Múltiples compute nodes pueden acceder a los mismos datos simultáneamente, ideal para distributed training.
* **Integración con S3**: Los datos de training pueden almacenarse en S3 e importarse a FSx for Lustre para su procesamiento.
* **Compresión de datos**: Usa compresión LZ4 para mejorar la eficiencia de almacenamiento.
* **Tipo de Deployment SCRATCH\_2**: Opción de alto rendimiento y rentable para procesamiento temporal.

### Consideraciones adicionales y buenas prácticas

#### 1. Backup y Disaster Recovery:

```yaml
# EBS volume snapshot creation
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain

---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: database-snapshot
  namespace: database
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: database-data
```

#### 2. Monitoreo y alertas:

* Configura alarmas de CloudWatch para monitorear uso de almacenamiento, latencia y throughput.
* Usa Prometheus y Grafana para visualizar métricas de almacenamiento.

#### 3. Optimización de costos:

* Elimina o crea snapshots de volúmenes no utilizados antes de eliminarlos.
* Selecciona tipos y tamaños de almacenamiento adecuados para optimizar costos.
* Para FSx for Lustre, usa el tipo de deployment SCRATCH si no se necesita almacenamiento a largo plazo.

#### 4. Seguridad:

* Habilita el cifrado para todos los volúmenes.
* Configura permisos IAM y security groups adecuados.
* Usa PodSecurityPolicy o SecurityContext para restringir el acceso a volúmenes.

Este diseño proporciona una solución de almacenamiento integral que cumple diversos requisitos de carga de trabajo:

* Volúmenes EBS gp3 de alto rendimiento para bases de datos
* EFS que admite acceso múltiple de lectura/escritura para compartir archivos de configuración
* Parallel file system de alto rendimiento FSx for Lustre para cargas de trabajo de AI/ML

Cada solución de almacenamiento está optimizada para requisitos específicos de carga de trabajo y diseñada teniendo en cuenta escalabilidad, rendimiento y eficiencia de costos.

</details>
