# Almacenamiento de EKS

> **Última actualización**: July 3, 2026

Al ejecutar aplicaciones en Amazon EKS, existen varias opciones de almacenamiento para guardar y administrar datos. Este documento cubre los conceptos básicos del almacenamiento de EKS y cómo usar Amazon EBS (Elastic Block Store) y Amazon EFS (Elastic File System).

## Índice de contenidos

1. [Conceptos básicos de almacenamiento de Kubernetes](04-eks-storage-part1.md#kubernetes-storage-basic-concepts)
2. [Descripción general de las opciones de almacenamiento de Amazon EKS](04-eks-storage-part1.md#amazon-eks-storage-options-overview)
3. [Almacenamiento con Amazon EBS](04-eks-storage-part1.md#storage-with-amazon-ebs)
4. [Almacenamiento con Amazon EFS](04-eks-storage-part1.md#storage-with-amazon-efs)
5. [Storage Classes y aprovisionamiento dinámico](04-eks-storage-part1.md#storage-classes-and-dynamic-provisioning)

## Conceptos básicos de almacenamiento de Kubernetes

Primero, comprendamos los conceptos clave para administrar el almacenamiento en Kubernetes.

![Diagrama de conceptos de almacenamiento de Kubernetes que muestra el flujo desde los contenedores, pasando por PVC, StorageClass y PV, hasta los backends de EBS, EFS, FSx y S3.](../.gitbook/assets/en-eks-04-eks-storage-part1-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-0.html)

### Volume

Un volume es un directorio que puede montarse en contenedores dentro de un Pod, y los datos persisten incluso si el contenedor se reinicia. El ciclo de vida de un volume es el mismo que el del Pod y, cuando se elimina el Pod, el volume también se elimina.

### Persistent Volume (PV)

Un persistent volume es una porción de almacenamiento del clúster aprovisionada por un administrador o aprovisionada dinámicamente mediante una storage class. Los PV tienen un ciclo de vida independiente de los Pods y persisten incluso cuando se eliminan los Pods.

### Persistent Volume Claim (PVC)

Un persistent volume claim es una solicitud de almacenamiento de un usuario. Un PVC solicita almacenamiento con un tamaño y un modo de acceso específicos, y esta solicitud se vincula a un PV adecuado.

### StorageClass

Una storage class describe la «clase» de almacenamiento ofrecida por el administrador. El uso de storage classes permite aprovisionar PV dinámicamente cuando se crean PVC.

### Modos de acceso

Kubernetes admite los siguientes modos de acceso:

* **ReadWriteOnce (RWO)**: Puede montarse como lectura/escritura en un único nodo
* **ReadOnlyMany (ROX)**: Puede montarse como solo lectura en muchos nodos
* **ReadWriteMany (RWX)**: Puede montarse como lectura/escritura en muchos nodos
* **ReadWriteOncePod (RWOP)**: Puede montarse como lectura/escritura únicamente en un solo Pod (Kubernetes 1.22+)

## Descripción general de las opciones de almacenamiento de Amazon EKS

En Amazon EKS, puede aprovechar varios servicios de almacenamiento de AWS para proporcionar almacenamiento a aplicaciones en contenedores.

![Diagrama de opciones de almacenamiento de EKS que compara EBS, EFS y FSx for Lustre junto con sus controladores CSI y los modos de acceso admitidos.](../.gitbook/assets/en-eks-04-eks-storage-part1-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-1.html)

### Opciones principales de almacenamiento

1. **Amazon EBS (Elastic Block Store)**
   * Almacenamiento en bloques, montable en un único nodo (RWO)
   * Almacenamiento en bloques duradero y de alto rendimiento
   * Adecuado para bases de datos y aplicaciones con estado
2. **Amazon EFS (Elastic File System)**
   * Sistema de archivos NFS completamente administrado
   * Puede montarse simultáneamente desde varios nodos (RWX)
   * Adecuado para cargas de trabajo que requieren sistemas de archivos compartidos
3. **Amazon FSx for Lustre**
   * Sistema de archivos de alto rendimiento
   * Adecuado para machine learning, HPC y análisis de big data
   * Puede montarse simultáneamente desde varios nodos (RWX)
4. **Amazon S3 (Simple Storage Service)**
   * Almacenamiento de objetos
   * No puede montarse directamente como un volume, pero es accesible mediante la API de S3
   * Adecuado para almacenamiento de datos a gran escala
5. **EC2 Instance Store (Local NVMe)**
   * Almacenamiento local NVMe efímero conectado físicamente a la instancia EC2, que ofrece una latencia muy baja
   * EC2 Instance Store CSI Driver alcanzó disponibilidad general (GA) como un complemento de Amazon EKS en mayo de 2026, por lo que ahora puede instalarse y administrarse como un complemento estándar desde EKS Console/CLI (anteriormente requería instalación manual mediante manifiestos de la comunidad). El controlador administra automáticamente el ciclo de vida del volume, lo que reduce la sobrecarga operativa
   * Adecuado para el procesamiento de datos efímeros de AI/ML, el almacenamiento en caché local de Spark/Hadoop, el procesamiento de logs de alto rendimiento y las capas de caché de bases de datos
   * Costo: el controlador es gratuito; solo paga por la instancia EC2 subyacente que incluye instance store ([fuente](https://aws.amazon.com/about-aws/whats-new/2026/05/ec2-csi-eks/))

### Comparación de opciones de almacenamiento

| Opción de almacenamiento | Tipo               | Modo de acceso | Rendimiento                   | Casos de uso                                                        |
| ------------------------ | ------------------ | -------------- | ----------------------------- | ------------------------------------------------------------------- |
| Amazon EBS               | Bloque             | RWO            | Alto                          | Bases de datos, aplicaciones con estado                             |
| Amazon EFS               | Archivo            | RWX            | Medio                         | Archivos compartidos, servidores web, CMS                           |
| FSx for Lustre           | Archivo            | RWX            | Muy alto                      | HPC, entrenamiento de ML, big data                                  |
| Amazon S3                | Objeto             | Acceso mediante API | Medio                     | Copia de seguridad, archivo, contenido estático                     |
| EC2 Instance Store       | Bloque (NVMe local) | RWO, efímero  | Muy alto (latencia ultrabaja) | Datos efímeros de AI/ML, caché local, procesamiento de logs de alto rendimiento |

## Almacenamiento con Amazon EBS

Amazon EBS proporciona volumes de almacenamiento a nivel de bloque que pueden adjuntarse a instancias EC2. En EKS, puede montar volumes de EBS en Pods de Kubernetes mediante el controlador EBS CSI (Container Storage Interface).

![Diagrama de arquitectura de EBS CSI que muestra Pods en dos nodos conectando volumes de EBS independientes mediante sus controladores CSI locales del nodo.](../.gitbook/assets/en-eks-04-eks-storage-part1-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-2.html)

### Instalación de EBS CSI Driver

Para usar volumes de EBS en EKS, debe instalar EBS CSI Driver. Este controlador se proporciona como un complemento de Amazon EKS.

```bash
# Install EBS CSI driver
eksctl create addon --name aws-ebs-csi-driver --cluster my-cluster --version latest

# Or using AWS CLI
aws eks create-addon --cluster-name my-cluster --addon-name aws-ebs-csi-driver --addon-version latest
```

### Creación de EBS Storage Class

Cree una storage class para el aprovisionamiento dinámico de volumes de EBS. Aquí usamos el tipo de volume gp3.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
  fsType: ext4
```

### Creación de Persistent Volume Claim (PVC)

Cree un PVC para que lo use su aplicación.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```

### Uso de PVC en un Pod

Monte el PVC creado en un Pod.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ebs
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - mountPath: "/data"
      name: ebs-volume
  volumes:
  - name: ebs-volume
    persistentVolumeClaim:
      claimName: ebs-claim
```

### Snapshots de volumes de EBS

Puede crear snapshots de volumes de EBS para realizar copias de seguridad de los datos.

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-snapshot
spec:
  volumeSnapshotClassName: csi-aws-vsc
  source:
    persistentVolumeClaimName: ebs-claim
```

### Expansión de volumes de EBS

Puede ampliar el tamaño de los volumes de EBS según sea necesario.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 20Gi  # Expanded from 10Gi to 20Gi
```

### Tipos de volume y rendimiento de EBS

Amazon EBS proporciona varios tipos de volume:

| Tipo de volume | Descripción              | Casos de uso                                |
| -------------- | ------------------------ | ------------------------------------------- |
| gp3            | SSD de uso general       | Adecuado para la mayoría de las cargas de trabajo, rentable |
| io2            | SSD de IOPS aprovisionadas | Bases de datos de alto rendimiento          |
| st1            | HDD optimizado para rendimiento | Big data, procesamiento de logs        |
| sc1            | HDD frío                 | Datos a los que se accede con poca frecuencia |

Para EKS, se recomienda el tipo de volume gp3. gp3 es rentable y proporciona un rendimiento uniforme.

## Almacenamiento con Amazon EFS

Amazon EFS es un sistema de archivos NFS completamente administrado al que se puede acceder simultáneamente desde varias instancias EC2. En EKS, puede montar sistemas de archivos EFS en varios Pods simultáneamente mediante EFS CSI Driver.

![Diagrama de arquitectura de EFS CSI que muestra Pods en varios nodos compartiendo un sistema de archivos EFS mediante NFS 4.1 a través del controlador CSI.](../.gitbook/assets/en-eks-04-eks-storage-part1-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-3.html)

### Instalación de EFS CSI Driver

Para usar EFS en EKS, debe instalar EFS CSI Driver.

```bash
# Install EFS CSI driver
eksctl create addon --name aws-efs-csi-driver --cluster my-cluster --version latest

# Or using AWS CLI
aws eks create-addon --cluster-name my-cluster --addon-name aws-efs-csi-driver --addon-version latest
```

### Creación de un sistema de archivos EFS

Cree un sistema de archivos EFS mediante AWS Management Console, AWS CLI o AWS CloudFormation.

```bash
# Create EFS file system using AWS CLI
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=MyEFSFileSystem

# Save file system ID
EFS_FS_ID=$(aws efs describe-file-systems --query "FileSystems[?Name=='MyEFSFileSystem'].FileSystemId" --output text)

# Get EKS cluster VPC ID
VPC_ID=$(aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.vpcId" --output text)

# Create security group
aws ec2 create-security-group \
  --group-name MyEFSSecurityGroup \
  --description "Security group for EFS mount targets" \
  --vpc-id $VPC_ID

SG_ID=$(aws ec2 describe-security-groups \
  --filters Name=group-name,Values=MyEFSSecurityGroup \
  --query "SecurityGroups[0].GroupId" --output text)

# Allow NFS traffic
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 2049 \
  --cidr 10.0.0.0/16

# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].SubnetId" --output text)

# Create mount target in each subnet
for SUBNET_ID in $SUBNET_IDS; do
  aws efs create-mount-target \
    --file-system-id $EFS_FS_ID \
    --subnet-id $SUBNET_ID \
    --security-groups $SG_ID
done
```

### Creación de EFS Storage Class

Cree una storage class para usar EFS.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0  # Created EFS file system ID
  directoryPerms: "700"
```

### Creación de Persistent Volume Claim (PVC)

Cree un PVC para usar EFS.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
spec:
  accessModes:
    - ReadWriteMany  # Can read/write simultaneously from multiple nodes
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

### Uso de EFS PVC en un Pod

Monte el PVC creado en un Pod.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-efs
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - mountPath: "/shared-data"
      name: efs-volume
  volumes:
  - name: efs-volume
    persistentVolumeClaim:
      claimName: efs-claim
```

### Puntos de acceso de EFS

El uso de puntos de acceso de EFS le permite restringir el acceso a directorios específicos y establecer permisos de usuarios y grupos.

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: efs-pv
spec:
  capacity:
    storage: 5Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: efs-sc
  csi:
    driver: efs.csi.aws.com
    volumeHandle: fs-0123456789abcdef0::fsap-0123456789abcdef0
    # volumeHandle format: {EFS file system ID}::{EFS access point ID}
```

### Modos de rendimiento y modos de rendimiento de EFS

Amazon EFS proporciona dos modos de rendimiento y tres modos de throughput:

**Modos de rendimiento**:

* **General Purpose**: Recomendado para la mayoría de las cargas de trabajo
* **Max I/O**: Adecuado para cargas de trabajo que requieren un alto procesamiento paralelo

**Modos de throughput**:

* **Bursting**: Modo predeterminado, proporciona créditos de ráfaga según el tamaño del sistema de archivos
* **Provisioned**: Úselo cuando se necesite un throughput uniforme
* **Elastic**: Ajusta automáticamente el throughput según la carga de trabajo (recomendado)

## Storage Classes y aprovisionamiento dinámico

El uso de storage classes de Kubernetes permite aprovisionar persistent volumes dinámicamente. En EKS, puede configurar storage classes para varios servicios de almacenamiento de AWS.

![Diagrama de flujo de trabajo de aprovisionamiento de almacenamiento que va desde la solicitud de PVC de un Pod, pasando por StorageClass y el controlador CSI, hasta la creación y vinculación de PV.](../.gitbook/assets/en-eks-04-eks-storage-part1-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-4.html)

### Modos de vinculación de volumes

El campo `volumeBindingMode` de una storage class determina cómo se vinculan los PV cuando se crean los PVC:

* **Immediate**: Aprovisiona y vincula el PV inmediatamente cuando se crea el PVC.
* **WaitForFirstConsumer**: Retrasa el aprovisionamiento del PV hasta que un Pod intenta usar el PVC.

Para el almacenamiento local del nodo, como EBS, se recomienda usar `WaitForFirstConsumer`. Esto garantiza que el volume se cree en la misma zona de disponibilidad que el nodo donde se programa el Pod.

### Configuración de Storage Class predeterminada

Configurar una storage class específica como predeterminada permite usarla incluso cuando no se especifica la storage class en el PVC.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
```

### Ejemplos de Storage Class

**1. EBS gp3 Storage Class**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
  iops: "3000"
  throughput: "125"
```

**2. EFS Storage Class**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"
```

**3. FSx for Lustre Storage Class**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  automaticBackupRetentionDays: "0"
  dailyAutomaticBackupStartTime: "00:00"
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
```

### Políticas de recuperación

La política de recuperación de un persistent volume determina cómo se gestionan el PV y sus datos cuando se elimina el PVC:

* **Delete**: Cuando se elimina el PVC, el PV y sus datos también se eliminan.
* **Retain**: Cuando se elimina el PVC, se conservan el PV y los datos. El administrador debe realizar la limpieza manualmente.
* **Recycle**: Política en desuso; use en su lugar el aprovisionamiento dinámico y las storage classes.

Puede establecer la política de recuperación mediante el campo `persistentVolumeReclaimPolicy` de la storage class:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-retain
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
parameters:
  type: gp3
  encrypted: "true"
```

## Conclusión

En Amazon EKS, puede configurar soluciones de almacenamiento que satisfagan los requisitos de su aplicación mediante varias opciones de almacenamiento. Este documento cubrió los conceptos básicos y los métodos de configuración centrados en EBS y EFS. El próximo documento cubrirá configuraciones de almacenamiento avanzadas mediante FSx for Lustre y S3.

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, pruebe el [cuestionario del tema](../quizzes/eks/04-eks-storage-part1-quiz.md).
