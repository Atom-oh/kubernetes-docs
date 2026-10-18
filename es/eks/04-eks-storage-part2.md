# Parte 2: Clases de almacenamiento

> **Última actualización**: October 16, 2026

Este documento es la segunda parte de la serie sobre almacenamiento de Amazon EKS y abarca FSx for Lustre, Amazon S3, las instantáneas, la expansión de volúmenes y la optimización del rendimiento.

## Tabla de contenido

1. [Amazon FSx for Lustre](04-eks-storage-part2.md#amazon-fsx-for-lustre)
2. [Integración de almacenamiento de Amazon S3](04-eks-storage-part2.md#amazon-s3-storage-integration)
3. [Instantáneas y copias de seguridad](04-eks-storage-part2.md#snapshots-and-backups)
4. [Expansión y cambio de tamaño de volúmenes](04-eks-storage-part2.md#volume-expansion-and-resizing)
5. [Clonación de volúmenes](04-eks-storage-part2.md#volume-cloning)
6. [Multi-Attach de EBS](04-eks-storage-part2.md#multi-attach-ebs)
7. [Análisis detallado de Mountpoint para S3 CSI](04-eks-storage-part2.md#mountpoint-for-s3-csi-deep-dive)
8. [Optimización del rendimiento del almacenamiento](04-eks-storage-part2.md#storage-performance-optimization)

## Amazon FSx for Lustre

FSx for Lustre es un sistema de archivos paralelo para cargas de trabajo HPC/ML/analíticas compatibles. El rendimiento depende del tipo de implementación y almacenamiento, la capacidad, el rendimiento aprovisionado, los clientes y la red; un sistema de archivos de ejemplo pequeño no ofrece todos los máximos agregados anunciados.

El diagrama ilustra la integración opcional con un repositorio de datos de S3. Deben configurarse las políticas, tareas y permisos de importación/exportación; crear un volumen CSI por sí solo no establece una sincronización bidireccional automática.

![Diagrama de arquitectura de los Pods de entrenamiento e inferencia de ML que montan FSx for Lustre a través del controlador FSx CSI, con FSx sincronizando datos con S3.](../.gitbook/assets/en-eks-04-eks-storage-part2-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-0.html)

### Instalación del controlador FSx for Lustre CSI

Usa el complemento de EKS compatible del propietario de la infraestructura o la versión publicada de Helm. Para el ejemplo del complemento administrado que aparece a continuación, establece `CSI_ADDON_NAME=aws-fsx-csi-driver`. Prepara un rol para `kube-system/fsx-csi-controller-sa` con permisos del controlador FSx revisados y confianza/agente de Pod Identity. También se admite IRSA con una confianza OIDC y la opción de rol correspondiente del complemento. El agente de Pod Identity es necesario para ese método de identidad, pero no para IRSA. Fargate no es un entorno de nodo compatible con FSx CSI; verifica el kernel de Linux/cliente Lustre y la compatibilidad del entorno de cómputo real.

Un rol creado con `eksctl --role-only` no es una ServiceAccount de Kubernetes. El complemento administrado crea su propia cuenta; una instalación de Helm debe crear o usar la cuenta real y asociarle la identidad prevista. No uses la creación de un rol solamente junto con `serviceAccount.create=false` sin preparar esa cuenta.
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CSI_ADDON_NAME:?Use aws-fsx-csi-driver}"
case "$CSI_ADDON_NAME" in
  aws-fsx-csi-driver) ;;
  *) echo "Unexpected add-on"; exit 1 ;;
esac
KUBERNETES_VERSION=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.version --output text)
CLUSTER_ENDPOINT=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.endpoint --output text)
CURRENT_ENDPOINT=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
test "$CURRENT_ENDPOINT" = "$CLUSTER_ENDPOINT" || { echo "kubeconfig points to another cluster"; exit 1; }
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$CSI_ADDON_NAME" \
  --kubernetes-version "$KUBERNETES_VERSION" --output json > csi-addon-versions.json
aws eks list-addons --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" --output json
```

```bash
set -euo pipefail
: "${CSI_ADDON_VERSION:?Choose a reviewed compatible version from csi-addon-versions.json}"
: "${CSI_ROLE_ARN:?Set the prepared Pod Identity role ARN}"
: "${CLUSTER_NAME:?Run the inspection step first}"
: "${AWS_REGION:?Run the inspection step first}"
: "${CSI_ADDON_NAME:?Run the inspection step first}"
case "$CSI_ADDON_NAME" in
  aws-fsx-csi-driver) CSI_SA=fsx-csi-controller-sa; CSI_PREFIX=fsx-csi ;;
  *) echo "Unexpected add-on"; exit 1 ;;
esac
python3 - "$CSI_ADDON_NAME" "$CSI_ADDON_VERSION" <<'PY'
import json, sys
with open("csi-addon-versions.json") as stream:
    catalog = json.load(stream)
versions = [v["addonVersion"] for a in catalog["addons"]
            if a["addonName"] == sys.argv[1] for v in a["addonVersions"]]
if sys.argv[2] not in versions:
    raise SystemExit("Version not present in the inspected compatible catalog")
PY
aws eks list-addons --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --output json > csi-existing-addons.json
python3 - "$CSI_ADDON_NAME" <<'PY'
import json, sys
with open("csi-existing-addons.json") as stream:
    names = json.load(stream)["addons"]
if sys.argv[1] in names:
    raise SystemExit("Existing add-on: use its owner's update procedure")
PY
EXISTING_CSI=$(kubectl -n kube-system get "deployment/$CSI_PREFIX-controller" \
  "daemonset/$CSI_PREFIX-node" --ignore-not-found -o name)
test -z "$EXISTING_CSI" || { echo "Existing CSI installation: review its owner"; exit 1; }
aws eks describe-addon-configuration --region "$AWS_REGION" \
  --addon-name "$CSI_ADDON_NAME" --addon-version "$CSI_ADDON_VERSION"
aws eks create-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$CSI_ADDON_NAME" --addon-version "$CSI_ADDON_VERSION" \
  --pod-identity-associations "serviceAccount=$CSI_SA,roleArn=$CSI_ROLE_ARN" \
  --resolve-conflicts NONE
aws eks wait addon-active --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$CSI_ADDON_NAME"
```
Este procedimiento se detiene si hay instalaciones existentes; migra o actualiza mediante su propietario. El estado Active del complemento no demuestra que el montaje del sistema de archivos se haya realizado correctamente. Los ejemplos que aparecen a continuación reutilizan el espacio de nombres dedicado `storage-demo` de la Parte 1 y requieren nombres revisados para recursos de ámbito de clúster.

### Creación de un sistema de archivos FSx for Lustre

**Elige aprovisionamiento dinámico o estático.** El aprovisionamiento dinámico crea un sistema de archivos a partir del PVC; no crees primero otro sistema de archivos esperando que la clase dinámica lo adopte. El siguiente procedimiento manual opcional corresponde a la ruta estática. Selecciona una subred aprobada en una zona de disponibilidad compatible y un grupo de seguridad de Lustre preconfigurado con las reglas necesarias para el tráfico de cliente/sistema de archivos. No elijas `Subnets[0]` ni supongas que TCP988 por sí solo completa todos los diseños compatibles. Este ejemplo acotado requiere la VPC del clúster; los diseños con VPC conectadas necesitan una revisión independiente del enrutamiento y la seguridad. Al ejecutarse, crea recursos facturables y conserva los ID devueltos en caso de error.
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set the filesystem Region}"
: "${FSX_SUBNET_ID:?Select an approved subnet in a supported AZ}"
: "${FSX_SECURITY_GROUP_ID:?Set the reviewed Lustre filesystem SG}"
: "${FSX_CREATION_TOKEN:?Set a unique stable token for this new filesystem}"
FSX_SETUP_DIR=$(mktemp -d -t eks-fsx-setup.XXXXXX)
printf 'Creation records: %s\n' "$FSX_SETUP_DIR"
VPC_ID=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$FSX_SUBNET_ID" \
  --output json > "$FSX_SETUP_DIR/subnet.json"
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$FSX_SECURITY_GROUP_ID" \
  --output json > "$FSX_SETUP_DIR/sg.json"
python3 - "$FSX_SETUP_DIR" "$VPC_ID" <<'PY'
import pathlib, json, sys
root, vpc = pathlib.Path(sys.argv[1]), sys.argv[2]
subnets = json.loads((root / "subnet.json").read_text())["Subnets"]
groups = json.loads((root / "sg.json").read_text())["SecurityGroups"]
if len(subnets) != 1 or len(groups) != 1 or subnets[0]["VpcId"] != vpc or groups[0]["VpcId"] != vpc:
    raise SystemExit("This example requires one subnet and SG in the cluster VPC")
PY
aws fsx create-file-system --region "$AWS_REGION" --file-system-type LUSTRE \
  --client-request-token "$FSX_CREATION_TOKEN" --storage-capacity 1200 --storage-type SSD \
  --subnet-ids "$FSX_SUBNET_ID" --security-group-ids "$FSX_SECURITY_GROUP_ID" \
  --lustre-configuration DeploymentType=SCRATCH_2,DataCompressionType=NONE \
  --tags Key=Name,Value=eks-lustre-demo --output json > "$FSX_SETUP_DIR/created.json"
FSX_FILE_SYSTEM_ID=$(python3 - "$FSX_SETUP_DIR/created.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    print(json.load(stream)["FileSystem"]["FileSystemId"])
PY
)
FSX_READY=false
for ((attempt=0; attempt<60; attempt++)); do
  STATE=$(aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
    --query 'FileSystems[0].Lifecycle' --output text)
  case "$STATE" in
    AVAILABLE) FSX_READY=true; break ;;
    CREATING) sleep 10 ;;
    *) echo "Unexpected filesystem state: $STATE"; exit 1 ;;
  esac
done
test "$FSX_READY" = true || { echo "Filesystem creation still pending; inspect recorded ID"; exit 1; }
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,State:Lifecycle,DNS:DNSName,MountName:LustreConfiguration.MountName,CapacityGiB:StorageCapacity}' \
  --output json > "$FSX_SETUP_DIR/available.json"
cat "$FSX_SETUP_DIR/available.json"
```


### Creación de una StorageClass para FSx for Lustre

Para la ruta **dinámica**, especifica la subred y el grupo de seguridad reales en la clase. La capacidad se obtiene de la solicitud del PVC, no de un parámetro `storageCapacity` ignorado de la clase. SCRATCH_2 no debe combinarse con opciones de rendimiento por unidad o copias de seguridad exclusivas de almacenamiento persistente. El nombre de montaje devuelto debe ir en volumeAttributes de un PV estático, no en un parámetro `mountName` de la clase.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: NONE
```


### Creación de un PVC y montaje en un Pod

Este consumidor de solo lectura comprueba únicamente que se puede acceder al montaje. No es una carga de trabajo de GPU ni una prueba de rendimiento; para esta comprobación no hace falta una imagen CUDA. Prepara los permisos del sistema de archivos para UID/GID1000 y la ruta de red real del cliente.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fsx-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-fsx
  namespace: storage-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - test -r /data && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: data
      mountPath: /data
      readOnly: true
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: fsx-claim
```


### Aprovisionamiento estático para montar FSx for Lustre

Usa el ID, DNSName, MountName y la capacidad reales del sistema de archivos existente. Esta opción es una alternativa al PVC dinámico. Sustituye los marcadores de posición que aparecen a continuación con los datos obtenidos en la consulta y, luego, vincula el PV/PVC estático reservado; `storageClassName: ""` evita el aprovisionamiento dinámico predeterminado. El consumidor debe usar `fsx-static-claim`.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the filesystem Region}"
: "${FSX_FILE_SYSTEM_ID:?Set the owned existing filesystem ID}"
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,State:Lifecycle,DNS:DNSName,MountName:LustreConfiguration.MountName,CapacityGiB:StorageCapacity}' \
  --output json
```

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: fsx-lustre-static
spec:
  capacity:
    storage: 1200Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ''
  claimRef:
    namespace: storage-demo
    name: fsx-static-claim
  csi:
    driver: fsx.csi.aws.com
    volumeHandle: fs-0123456789abcdef0
    volumeAttributes:
      dnsname: replace-with-filesystem-dns.example.internal
      mountname: replace-with-mountname
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fsx-static-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: ''
  volumeName: fsx-lustre-static
  resources:
    requests:
      storage: 1200Gi
```


### Tipos de implementación de FSx for Lustre

- **SCRATCH_1/SCRATCH_2** son para datos temporales y reproducibles. El almacenamiento temporal no ofrece replicación/recuperación de implementación persistente por el mero hecho de montarlo como PV; SCRATCH_2 añade distintas características de ráfaga/rendimiento y cifrado.
- **PERSISTENT_1/PERSISTENT_2** ofrecen opciones de implementación persistente con distintas capacidades de almacenamiento/rendimiento/latencia. PERSISTENT_2 no está disponible en todas las configuraciones de Región/zona de disponibilidad.
- Adapta los campos de rendimiento al tipo de implementación/almacenamiento elegido. PERSISTENT_2 SSD admite opciones de 125/250/500/1000MB/s/TiB; las demás combinaciones de implementación/almacenamiento son distintas. Retain es una política del ciclo de vida de Kubernetes, no una mejora de durabilidad de datos para el almacenamiento temporal.

### Configuración de FSx for Lustre para vLLM

vLLM es un proyecto de inferencia/servicio de LLM, no «Vector Language Model». Lo siguiente es una asignación ilustrativa de almacenamiento para archivos de modelos, no una implementación optimizada o medida de vLLM. La carga de modelos también depende del formato de archivo, la deserialización de CPU, el estado de la caché y la inicialización de GPU. La compresión puede añadir sobrecarga a datos que ya están comprimidos; mídela.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-vllm
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: PERSISTENT_2
  dataCompressionType: LZ4
  perUnitStorageThroughput: '1000'
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-vllm
  resources:
    requests:
      storage: 4800Gi
```

## Integración de almacenamiento de Amazon S3 {#amazon-s3-storage-integration}

S3 es almacenamiento de objetos. Las aplicaciones pueden usar directamente su API, Hadoop puede usar S3A y Mountpoint CSI puede exponer un bucket existente mediante una interfaz de sistema de archivos con limitaciones documentadas. Estas opciones no son sistemas de archivos POSIX intercambiables. S3 Files, que se trata en la Parte 1, es otra integración con requisitos propios de EFS CSI.

![Diagrama de métodos de integración con S3: los Pods de aplicaciones obtienen credenciales mediante IRSA y acceden a S3 a través del controlador Mountpoint S3 CSI o del AWS SDK.](../.gitbook/assets/en-eks-04-eks-storage-part2-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-1.html)

### Pod Identity o IRSA para acceder a S3

Reutiliza el espacio de nombres dedicado `storage-demo` de la Parte 1. Prepara un bucket existente, una Región y un rol de IAM con permisos limitados al bucket/prefijo previsto. Esta política de ejemplo permite listar un bucket y leer únicamente `training/`; no concede permisos de escritura. Los objetos SSE-KMS también requieren la política de clave adecuada y permisos de descifrado de KMS con el alcance necesario. Las políticas de bucket, los endpoints y la confianza entre cuentas pueden imponer restricciones adicionales.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOneBucket",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-data-bucket"
    },
    {
      "Sid": "ReadTrainingPrefix",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-data-bucket/training/*"
    }
  ]
}
```

La ServiceAccount siguiente ilustra **IRSA**: sustituye el ARN de ejemplo por el del rol preparado, cuya confianza OIDC solo permite este clúster, `system:serviceaccount:storage-demo:s3-access-sa` y la audiencia STS. La anotación por sí sola no crea ese rol ni la relación de confianza. Para **EKS Pod Identity**, omite la anotación IRSA y crea la asociación revisada para esta misma cuenta de aplicación con un agente compatible; no configures ambos como mecanismo alternativo accidental. No incluyas claves estáticas de AWS en el manifiesto.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: storage-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/storage-demo-s3-reader
```

### Configuración de un Pod para acceder a S3

Este Job acotado de solo lectura, que lista objetos, utiliza la imagen oficial de AWS CLI y la cuenta preparada. Sustituye el bucket y la Región antes de usarlo. Sus directorios privados con permisos de escritura permiten ejecutar la CLI sin privilegios; el estado de salida por sí solo no demuestra que la aplicación pueda leer todos los objetos previstos. Comprueba el Job y sus registros, además de un objeto autorizado representativo, por separado.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: s3-read-check
  namespace: storage-demo
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: s3-access-sa
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: reader
        image: public.ecr.aws/aws-cli/aws-cli:2.36.43
        command:
        - aws
        args:
        - s3api
        - list-objects-v2
        - --bucket
        - replace-with-owned-data-bucket
        - --prefix
        - training/
        - --max-items
        - '5'
        env:
        - name: AWS_REGION
          value: us-west-2
        - name: AWS_EC2_METADATA_DISABLED
          value: 'true'
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        volumeMounts:
        - name: private-home
          mountPath: /root
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: private-home
        emptyDir: {}
      - name: tmp
        emptyDir: {}
```

### Acceso a S3A desde Hadoop

S3A es la implementación del sistema de archivos `s3a://` de Hadoop, no un montaje de volumen de Kubernetes. Hadoop3.5.0 utiliza AWS SDK for Java v2. Crea y revisa una imagen que contenga versiones coincidentes de `hadoop-common`/`hadoop-aws` y su paquete sombreado compatible del SDK; el marcador de posición siguiente no es una imagen publicada lista para ejecutar. El contrato de la imagen requiere `hadoop` en PATH, `/opt/hadoop/etc/hadoop` y compatibilidad con UID1000. Combina `hadoop-aws` con cualquier otra herramienta opcional necesaria. El proveedor de credenciales predeterminado de v2 admite la identidad de carga de trabajo seleccionada si el SDK incluido la admite; no reutilices una clase de proveedor v1 `com.amazonaws`.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hadoop-s3a-config
  namespace: storage-demo
data:
  core-site.xml: |
    <?xml version="1.0" encoding="UTF-8"?>
    <configuration>
      <property>
        <name>fs.s3a.aws.credentials.provider</name>
        <value>software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider</value>
      </property>
      <property>
        <name>fs.s3a.endpoint.region</name>
        <value>us-west-2</value>
      </property>
    </configuration>
---
apiVersion: batch/v1
kind: Job
metadata:
  name: hadoop-s3a-read-check
  namespace: storage-demo
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: s3-access-sa
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: hadoop
        image: registry.example.com/reviewed-hadoop-s3a:3.5.0
        command:
        - hadoop
        args:
        - fs
        - -ls
        - s3a://replace-with-owned-data-bucket/training/
        env:
        - name: AWS_REGION
          value: us-west-2
        - name: AWS_EC2_METADATA_DISABLED
          value: 'true'
        - name: HADOOP_CONF_DIR
          value: /opt/hadoop/etc/hadoop
        - name: HADOOP_OPTIONAL_TOOLS
          value: hadoop-aws
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: hadoop-config
          mountPath: /opt/hadoop/etc/hadoop/core-site.xml
          subPath: core-site.xml
          readOnly: true
      volumes:
      - name: tmp
        emptyDir: {}
      - name: hadoop-config
        configMap:
          name: hadoop-s3a-config
```

Montar una clave de ConfigMap mediante subPath conserva los demás archivos de configuración de Hadoop de la imagen. Un montaje subPath no recibe actualizaciones en vivo de ConfigMap; vuelve a crear el Job después de cambiar la configuración.

### Montaje de un bucket existente con Mountpoint CSI

La combinación revisada de upstream es CSI2.8.0 con Mountpoint1.23.0 incluido. Mountpoint1.24.0 independiente no cambia automáticamente la imagen de CSI. Comprueba la versión real del complemento de EKS y la compatibilidad del entorno de cómputo: esta versión de upstream de CSI requiere Kubernetes1.31+ y ya no admite AL2/Ubuntu22.04. Da preferencia al propietario de infraestructura existente; no instales Helm sobre un complemento administrado o un controlador existente.

Si la instalación de Helm pertenece a otro equipo, primero representa la **versión publicada del chart** para revisarla; usa la versión real del clúster en `--kube-version`. El chart de un checkout de Git no es la distribución compatible y no se debe eludir su restricción de publicación. Revisa los componentes privilegiados de nodo, la propiedad de CRD y el espacio de nombres `mount-s3` antes de implementar mediante el propietario elegido:

```bash
set -euo pipefail
helm repo add aws-mountpoint-s3-csi-driver https://awslabs.github.io/mountpoint-s3-csi-driver
helm repo update aws-mountpoint-s3-csi-driver
helm template aws-mountpoint-s3-csi-driver \
  aws-mountpoint-s3-csi-driver/aws-mountpoint-s3-csi-driver \
  --version 2.8.0 --namespace kube-system --kube-version 1.36.0 --include-crds \
  > s3-driver-review.yaml
```

El chart publicado crea `s3-csi-driver-sa` y `s3-csi-driver-controller-sa` de forma predeterminada. El PV siguiente selecciona explícitamente **credenciales a nivel de Pod** mediante `s3-access-sa`; se ignoran las credenciales a nivel del controlador para este volumen. Aquí se admiten tanto IRSA como EKS Pod Identity. La disponibilidad requiere la instalación real del controlador/la identidad, no solo que Helm se haya representado correctamente.

Mountpoint CSI usa **aprovisionamiento estático** de un bucket existente, no la StorageClass dinámica que aparece en ejemplos antiguos. Mantén vacíos ambos campos storageClassName y usa preasignación explícita PV/PVC junto con un volumeHandle único en el clúster. Los campos de capacidad satisfacen los metadatos de vinculación de Kubernetes; no crean ni limitan la capacidad del bucket de S3. Sustituye el bucket, el prefijo y la Región a la vez. El montaje de solo lectura y los permisos de IAM son controles independientes:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: s3-training-pv
spec:
  capacity:
    storage: 1Ti
  volumeMode: Filesystem
  accessModes:
  - ReadOnlyMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ''
  claimRef:
    namespace: storage-demo
    name: training-data
  mountOptions:
  - read-only
  - region us-west-2
  - prefix training/
  - allow-other
  - uid 1000
  - gid 1000
  - dir-mode 0750
  - file-mode 0440
  csi:
    driver: s3.csi.aws.com
    volumeHandle: storage-demo-s3-training-v1
    volumeAttributes:
      bucketName: replace-with-owned-data-bucket
      authenticationSource: pod
      stsRegion: us-west-2
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: training-data
  namespace: storage-demo
spec:
  accessModes:
  - ReadOnlyMany
  storageClassName: ''
  volumeName: s3-training-pv
  resources:
    requests:
      storage: 1Ti
```



```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-s3
  namespace: storage-demo
spec:
  serviceAccountName: s3-access-sa
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: reader
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - ls -la /data && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: data
      mountPath: /data
      readOnly: true
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: training-data
      readOnly: true
```

Las opciones de montaje asignan la propiedad del sistema de archivos a UID/GID1000; no cambian la propiedad de los objetos de S3. `allow-other` permite que ese UID de la aplicación acceda a un montaje creado por el controlador. Los contenedores de aplicaciones no necesitan AWS CLI ni privilegios FUSE para esta ruta de montaje de solo lectura.

### Casos de uso de S3

S3 puede utilizarse para lagos de datos, repositorios de modelos, archivos, recursos estáticos y objetos de auditoría. Elige el acceso a la API cuando la aplicación necesite versiones de objetos, solicitudes condicionales o capacidades que no forman parte del contrato de sistema de archivos de Mountpoint. Un directorio de base de datos con escritura que requiera actualizaciones aleatorias y bloqueos POSIX necesita otro diseño de almacenamiento.

## Instantáneas y copias de seguridad {#snapshots-and-backups}

Las instantáneas de CSI requieren compatibilidad del controlador/backend específico; tener un PVC no implica que se admitan instantáneas. El siguiente ejemplo de EBS captura un volumen de bloques en un momento dado. Pon las aplicaciones en un estado coherente/vacía sus búferes, o usa copias de seguridad con conocimiento de la base de datos/archivado de WAL cuando sea necesario. Una instantánea correcta no demuestra coherencia de la aplicación ni recuperación de la base de datos a un momento dado.

![Diagrama del flujo de instantáneas desde el PVC de origen, pasando por VolumeSnapshot y SnapshotContent, hasta una instantánea de EBS; luego se restaura en un PVC nuevo.](../.gitbook/assets/en-eks-04-eks-storage-part2-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-2.html)

### Preparación del controlador de instantáneas

Primero inspecciona las CRD de instantáneas existentes, el propietario del controlador y el snapshotter de CSI. Usa el complemento de EKS compatible o una versión externa de external-snapshotter revisada y fijada; no apliques CRD flotantes de master sobre una instalación existente. External-snapshotter8.6.0 es una referencia de upstream revisada, no un destino de actualización automático para todos los complementos. También se aplican los requisitos previos del controlador y el espacio de nombres de la Parte 1.

```bash
set -euo pipefail
kubectl get crd volumesnapshots.snapshot.storage.k8s.io \
  volumesnapshotcontents.snapshot.storage.k8s.io volumesnapshotclasses.snapshot.storage.k8s.io
kubectl -n storage-demo get pvc ebs-claim -o yaml
```

### Creación de la clase y la instantánea

El controlador de la clase debe coincidir con el controlador del PV. Esta clase administrada manualmente usa Retain; eliminar su instantánea de Kubernetes no elimina automáticamente la instantánea de EBS retenida. Registra la propiedad y el costo, y no confundas esta política con el ciclo de vida de Velero que se describe a continuación. Los parámetros de secreto vacíos del snapshotter no son necesarios para este ejemplo de EBS.

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain
```



```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-part2-snapshot
  namespace: storage-demo
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: ebs-claim
```



```bash
set -euo pipefail
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  volumesnapshot/ebs-part2-snapshot --timeout=300s
kubectl -n storage-demo get volumesnapshot ebs-part2-snapshot -o yaml
```

### Restauración en un PVC nuevo

Cuando `readyToUse=true`, inspecciona restoreSize y el contenido/controlador vinculados. Usa un nombre distinto en el mismo espacio de nombres y una capacidad al menos igual a restoreSize. Este ejemplo de 20Gi supone que la instantánea no es mayor. Mantén intacto el claim activo; WaitForFirstConsumer puede dejar el candidato en Pending hasta que se programe un consumidor compatible. Valida los datos restaurados con una aplicación compatible y aislada antes de realizar un cambio controlado.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-part2-restored
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 20Gi
  dataSource:
    name: ebs-part2-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

### Programación de copias de seguridad con Velero

La combinación revisada es Velero1.18.4 con AWS plugin1.14.4. Verifica la suma de comprobación de la versión de la CLI y la compatibilidad del complemento antes de instalar. La compatibilidad con CSI está integrada en Velero, pero para esta ruta sigue siendo necesario `EnableCSI`; no añadas el antiguo complemento CSI independiente. Prepara un bucket/prefijo privado para copias de seguridad, acceso a la red, permisos IAM/KMS con el alcance adecuado y un rol IRSA para `velero/velero`. Lo siguiente genera un manifiesto de revisión para una instalación nueva sin crear recursos:

```bash
set -euo pipefail
: "${BACKUP_BUCKET:?Set the existing private backup bucket}"
: "${VELERO_ROLE_ARN:?Set the reviewed IRSA role for system:serviceaccount:velero:velero}"
: "${AWS_REGION:?Set the bucket/snapshot Region for this example}"
velero install --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.14.4 \
  --bucket "$BACKUP_BUCKET" --prefix eks-storage-demo \
  --backup-location-config "region=$AWS_REGION" \
  --snapshot-location-config "region=$AWS_REGION" \
  --features EnableCSI --no-secret \
  --sa-annotations "eks.amazonaws.com/role-arn=$VELERO_ROLE_ARN" \
  --dry-run -o yaml > velero-review.yaml
```

Usa un kubeconfig válido incluso para esta ejecución de prueba de la CLI; generar el manifiesto no es una prueba de autorización ni de copia de seguridad. No sobrescribas una instalación existente de Velero/CRD. La ServiceAccount predeterminada se crea con la anotación IRSA; si se usa `--service-account-name`, se selecciona una cuenta ya existente y se ignora `--sa-annotations`. Pod Identity es una alternativa que requiere su propia configuración de asociación/agente. No se necesita ningún archivo de credenciales estáticas.

Para seleccionar la clase de CSI, etiqueta solo una clase predeterminada por controlador o selecciona una clase mediante la anotación de copia de seguridad/programación compatible. Revisa la siguiente clase junto con las clases existentes:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-velero-snapshots
  labels:
    velero.io/csi-volumesnapshot-class: 'true'
driver: ebs.csi.aws.com
deletionPolicy: Retain
```

**Velero administra el ciclo de vida de sus instantáneas de copia de seguridad CSI.** Cuando la copia de seguridad vence o se elimina, Velero cambia la política de eliminación de VolumeSnapshotContent a Delete y elimina la instantánea, aunque la clase original usara Retain. Define deliberadamente el TTL de la copia de seguridad y cualquier procedimiento independiente de retención/archivo. Una copia de seguridad de Velero en S3 no necesariamente contiene todos los bytes del volumen: las instantáneas CSI, la copia de seguridad del sistema de archivos y los agentes de movimiento de datos son rutas diferentes. Por ejemplo, FSx CSI1.10.0 no implementa instantáneas CSI; usa una estrategia de copia de seguridad de FSx/aplicación compatible.

```bash
set -euo pipefail
velero schedule create storage-demo-daily --schedule="0 1 * * *" \
  --include-namespaces=storage-demo --ttl=168h0m0s -o yaml > velero-schedule-review.yaml
```

El comando de programación también genera únicamente YAML. Implementa la programación revisada mediante su propietario y, luego, inspecciona la fase real de Backup, los errores, la finalización de instantáneas/agentes de movimiento de datos y las pruebas de restauración. Las instantáneas programadas por sí solas no ofrecen recuperación de bases de datos a cualquier momento dado (PITR).

Para la recuperación, elige una copia de seguridad verificada real en vez de una marca de tiempo histórica fija. Incluso con `-o yaml`, este comando realiza descubrimiento de la API y lee la copia de seguridad seleccionada, por lo que requiere acceso de lectura al clúster previsto. Esta vista previa del manifiesto limita los tipos de recursos solicitados y asigna el espacio de nombres; inspecciona las dependencias y las acciones de restauración del complemento antes de enviarlo. Confirma que el espacio de nombres de destino esté aislado, que los nombres no entren en conflicto y que las asignaciones de StorageClass/controlador CSI/KMS/zona de disponibilidad sean válidas. No es una guía de recuperación de producción completa:

```bash
set -euo pipefail
: "${VERIFIED_BACKUP:?Choose an actual completed backup after checking its contents/errors}"
velero restore create storage-demo-recovery-review --from-backup "$VERIFIED_BACKUP" \
  --namespace-mappings storage-demo:storage-recovery \
  --include-namespaces storage-demo \
  --include-resources persistentvolumes,persistentvolumeclaims,volumesnapshots.snapshot.storage.k8s.io,volumesnapshotcontents.snapshot.storage.k8s.io \
  --restore-volumes=true -o yaml > velero-restore-review.yaml
```

Inicia las cargas de trabajo restauradas solo después de que los datos candidatos superen las comprobaciones de la aplicación, y conserva una vía de reversión. La restauración CSI entre clústeres requiere un nombre de controlador coincidente y acceso a las instantáneas/clave; la asignación del espacio de nombres por sí sola no hace portables los recursos de la nube.

## Expansión y cambio de tamaño de volúmenes {#volume-expansion-and-resizing}

![Diagrama del proceso de expansión de volumen: desde la StorageClass que permite la expansión, pasando por la edición del PVC, la llamada CSI y el crecimiento de EBS, hasta el cambio de tamaño del sistema de archivos.](../.gitbook/assets/en-eks-04-eks-storage-part2-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-3.html)

Usa una clase con `allowVolumeExpansion: true` y un controlador CSI/sistema de archivos compatible. Conserva el storageClassName existente del claim vinculado; no es un interruptor para cambiar el tamaño. Este ejemplo reutiliza `ebs-gp3` de la Parte 1 y aumenta solo la solicitud del claim. Primero comprueba la solicitud/capacidad actual para no reducir un claim que ya sea más grande.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```
CSI gestiona la expansión del backend y del sistema de archivos cuando es compatible. Inspecciona las condiciones del PVC, los registros del controlador/nodo y la capacidad montada. Sigue el procedimiento documentado del controlador para volver a montar/reiniciar si es necesario; no ejecutes `resize2fs` sobre un `/dev/xvdf` supuesto dentro de un contenedor de aplicación. Nunca edites la capacidad del PV para eludir el cambio de tamaño. Planifica límites de cuota/costo y evita el crecimiento automatizado repetido mientras haya un cambio de tamaño pendiente.

## Clonación de volúmenes {#volume-cloning}

El CSI de EBS actual admite la clonación de PVC mediante `dataSource` y la capacidad de clonación de CSI; EBS CSI1.67.0 usa la copia nativa de volúmenes de EBS (`CopyVolumes`), no una instantánea oculta supuesta. Comprueba la compatibilidad del controlador/complemento implementado antes de usarla. El destino es independiente, pero la disponibilidad y el rendimiento completamente inicializado son estados distintos.



Para el flujo habitual de dataSource de PVC, usa un origen vinculado en el mismo espacio de nombres, un modo de volumen/controlador compatible y una solicitud al menos tan grande como el origen. Especifica storageClassName explícitamente; si se omite, se aplican las reglas de clase predeterminada, no se hereda automáticamente la del origen. Las copias nativas de EBS permanecen en la zona de disponibilidad de origen. Son coherentes ante fallos, salvo que la aplicación se ponga en un estado coherente/se vacíen sus búferes de forma adecuada. Solo se puede inicializar una copia de un origen a la vez; también se aplican las cuotas de cuenta/Región.

Este origen de entrenamiento dedicado evita iniciar un clon de base de datos no verificado en un espacio de nombres de producción. Sustituye la zona de disponibilidad de ejemplo en **el escritor y el lector** por una zona compatible real. El Job de preparación usa el PVC de origen, crea un marcador sin sobrescribir uno existente y, luego, termina:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-clone-source
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: ebs-clone-seed
  namespace: storage-demo
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        app: ebs-clone-seed
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        topology.kubernetes.io/zone: us-west-2a
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: writer
        image: busybox:1.38.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          (set -C; printf 'clone-demo\n' > /data/seed.txt)
          sync
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 64Mi
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: ebs-clone-source
```

```bash
kubectl -n storage-demo wait --for=condition=complete job/ebs-clone-seed --timeout=300s
kubectl -n storage-demo get pvc ebs-clone-source -o yaml
```
Crea el clon separado y su consumidor de solo lectura después de que finalice el Job de preparación. La comprobación del marcador muestra qué se debe validar; esta revisión no ejecutó una copia en la nube. Copiar una base de datos no restablece las contraseñas existentes, y el destino debe usar una versión de base de datos compatible si más adelante se inicia como base de datos.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-clone
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
  dataSource:
    kind: PersistentVolumeClaim
    name: ebs-clone-source
---
apiVersion: v1
kind: Pod
metadata:
  name: app-with-clone
  namespace: storage-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - test "$(cat /data/seed.txt)" = clone-demo && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: data
      mountPath: /data
      readOnly: true
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: ebs-clone
  nodeSelector:
    topology.kubernetes.io/zone: us-west-2a
```
| Propiedad | Copia de volumen PVC/nativa | Restauración de instantánea |
|---|---|---|
| Origen | Volumen/PVC existente | Instantánea retenida de un momento dado |
| Disponibilidad | Disponible antes de que finalice la inicialización en segundo plano | Depende del estado de la instantánea/restauración y de la inicialización |
| Ubicación | La copia nativa de EBS permanece en la zona de disponibilidad de origen | Un volumen restaurado nuevo puede apuntar a otra zona de disponibilidad permitida |
| Coherencia | Puede ser necesario poner la aplicación en un estado coherente | Puede ser necesaria una copia de seguridad con conocimiento de la aplicación |
| Espacio de nombres | dataSource de PVC habitual usa el mismo espacio de nombres | Los objetos de instantánea están dentro de un espacio de nombres; la importación entre espacios de nombres/clústeres requiere un flujo de trabajo compatible explícito |
| Costo/retención | Cargos por la operación de copia y el volumen nuevo; ciclo de vida independiente | Almacenamiento de instantáneas más cargos del volumen restaurado; políticas de eliminación independientes |

No deduzcas la velocidad, la sobrecarga de almacenamiento ni el RPO de «un paso» frente a «dos pasos». Las copias de volúmenes nativas no admiten fast snapshot restore ni tasas de inicialización aprovisionadas; sigue las instrucciones reales de inicialización de la copia.

## Multi-Attach de EBS {#multi-attach-ebs}

El servicio EC2 admite Multi-Attach para volúmenes io1/io2 aptos, hasta en16 instancias Nitro compatibles de una AZ, sujeto a restricciones de tipo de volumen/Región. La **ruta dinámica de EBS CSI1.66.0 admite io2 + ReadWriteMany + volumeMode: Block** y habilita Multi-Attach mediante esa capacidad. `multiAttachEnabled` no es un interruptor compatible de StorageClass en esta ruta. RWOP es una restricción de un Pod y no es el modo de acceso Multi-Attach.



Un dispositivo de bloques compartido no proporciona coordinación de escritura de aplicaciones. No se deben montar sistemas ext4/XFS ordinarios de forma independiente y con permisos de lectura/escritura desde varios nodos; usa un sistema de archivos agrupado/en clúster y un diseño de cercado adecuados, coordinados por la aplicación. io2 admite el cercado mediante reservas NVMe, pero la aplicación debe usarlo correctamente. La siguiente demostración, que solo adjunta el volumen, **no realiza E/S ni formatea el dispositivo**. Las etiquetas coincidentes y la anti-afinidad requieren dos nodos aptos en la AZ del volumen. Las cargas de trabajo reales necesitan acceso al dispositivo y coordinación revisados, no este contenedor inactivo:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-io2-multi-attach
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  iops: '10000'
  encrypted: 'true'
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-block-pvc
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  volumeMode: Block
  storageClassName: ebs-io2-multi-attach
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: shared-block-a
  namespace: storage-demo
  labels:
    app: shared-block-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: shared-block-demo
        topologyKey: kubernetes.io/hostname
  containers:
  - name: attachment-only
    image: busybox:1.38.0
    command:
    - sleep
    - '3600'
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeDevices:
    - name: shared
      devicePath: /dev/ebs-shared
  volumes:
  - name: shared
    persistentVolumeClaim:
      claimName: shared-block-pvc
---
apiVersion: v1
kind: Pod
metadata:
  name: shared-block-b
  namespace: storage-demo
  labels:
    app: shared-block-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: shared-block-demo
        topologyKey: kubernetes.io/hostname
  containers:
  - name: attachment-only
    image: busybox:1.38.0
    command:
    - sleep
    - '3600'
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeDevices:
    - name: shared
      devicePath: /dev/ebs-shared
  volumes:
  - name: shared
    persistentVolumeClaim:
      claimName: shared-block-pvc
```
Los volúmenes io2 Multi-Attach admiten modificaciones de tamaño/IOPS según las condiciones del servicio; es incorrecto afirmar de forma general que «no se puede cambiar el tamaño en línea». La compatibilidad de modificación de io1 es distinta. Para habilitar/deshabilitar Multi-Attach, el volumen debe estar desconectado, y la compatibilidad de CSI/sistema de archivos/aplicación sigue determinando un procedimiento de cambio de tamaño seguro. Un fallo de volumen compartido puede afectar a todas las instancias adjuntas. Retain y los ajustes de conexión no son una estrategia de copia de seguridad.

## Análisis detallado de Mountpoint para S3 CSI {#mountpoint-for-s3-csi-deep-dive}

El comportamiento siguiente se verificó con Mountpoint1.23.0 incluido en CSI2.8.0. Comprueba la versión que realmente está instalada antes de adoptar opciones independientes más recientes.



### Características de rendimiento

Las lecturas secuenciales de objetos grandes y las escrituras secuenciales de objetos nuevos son opciones habituales; Mountpoint realiza la precarga automáticamente. Se admiten lecturas de rangos aleatorios, pero los resultados dependen del tamaño del objeto, la tasa de solicitudes, la red, el estado de la caché y la concurrencia de la aplicación. No se admiten escrituras aleatorias arbitrarias in situ; no se trata simplemente de una opción de optimización lenta.

**Cifras históricas, no verificadas:** el texto anterior en inglés enumeraba las siguientes cifras agregadas sin una configuración reproducible ni una fuente rastreable. Se conservan como afirmaciones históricas, no como límites actuales del servicio, resultados medidos en esta revisión ni garantías de dimensionamiento.

| Operación histórica | Afirmación original |
|---|---|
| Lectura secuencial, archivos grandes | Hasta100Gbps agregados |
| Escritura secuencial, archivos nuevos | Hasta50Gbps agregados |
| Lecturas aleatorias pequeñas | Mayor latencia/menor rendimiento, depende de la carga de trabajo |

La clasificación cualitativa anterior de «excelente/bueno/moderado» tampoco se basó en una prueba comparativa controlada.

### Límites del sistema de archivos y coherencia

- S3 ofrece coherencia sólida de lectura/listado. El almacenamiento en caché de Mountpoint puede conservar intencionadamente metadatos/contenido obsoletos o entradas negativas hasta que venza el TTL; no describas S3 como un servicio de coherencia eventual.
- Los archivos nuevos se escriben secuencialmente. Para reemplazar un objeto existente se requieren `allow-overwrite` y una apertura que lo trunque; las actualizaciones aleatorias arbitrarias siguen sin admitirse.
- Los buckets de directorio de S3 Express One Zone en zonas de disponibilidad admiten anexado con `incremental-upload` y el cambio de nombre atómico de archivos individuales. Los buckets de uso general no admiten el cambio de nombre de archivos mediante esta versión de Mountpoint; no se admite cambiar el nombre de directorios. Los buckets de directorio en Local Zones tienen compatibilidad de funciones distinta. Cambiar el nombre de un objeto al reemplazarlo también requiere permiso/opciones de sobrescritura.
- La eliminación es opcional mediante `allow-delete` y permisos de IAM; los ejemplos de solo lectura no habilitan ninguna de las dos cosas. Anexar no es una operación universal para «crear una versión nueva del objeto».
- No se admiten vínculos duros/simbólicos, chmod/chown, atributos extendidos, bloqueos POSIX, archivos de dispositivo ni la semántica habitual de los archivos dispersos. No bases la corrección de una base de datos en estas operaciones no compatibles.

### Ajustes de caché

Coloca las opciones de la CLI de Mountpoint en **PV.spec.mountOptions**, no como parámetros de StorageClass. Los valores son cadenas de opciones como `metadata-ttl 300`. Mountpoint1.23 usa segundos para el TTL de metadatos, **MiB** para `max-cache-size` independiente y **bytes** para read/write-part-size;8MiB son8,388,608bytes. Los ejemplos anteriores de prefetch-bytes/read-ahead/max-read-parallelism/max-cache-size-mb/cache-block-size no son indicadores válidos de la CLI 1.23.

CSI v2 crea almacenamiento de caché para su **Pod de Mountpoint**, normalmente en `mount-s3`. Un emptyDir del Pod de aplicación no se convierte en esa caché. Este PV estático alternativo usa una caché emptyDir respaldada por disco de 10Gi, cuyo límite de tamaño aplica el controlador; Memory equivale a RAM tmpfs, no a NVMe. Sustituye el bucket/prefijo/Región reales y utiliza el PVC preasignado por separado:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: s3-training-cached-pv
spec:
  capacity:
    storage: 1Ti
  volumeMode: Filesystem
  accessModes:
  - ReadOnlyMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ''
  claimRef:
    namespace: storage-demo
    name: training-data-cached
  mountOptions:
  - read-only
  - region us-west-2
  - prefix training/
  - allow-other
  - uid 1000
  - gid 1000
  - dir-mode 0750
  - file-mode 0440
  - metadata-ttl 300
  - read-part-size 8388608
  csi:
    driver: s3.csi.aws.com
    volumeHandle: storage-demo-s3-training-cached-v1
    volumeAttributes:
      bucketName: replace-with-owned-data-bucket
      authenticationSource: pod
      stsRegion: us-west-2
      cache: emptyDir
      cacheEmptyDirSizeLimit: 10Gi
      cacheEmptyDirMedium: ''
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: training-data-cached
  namespace: storage-demo
spec:
  accessModes:
  - ReadOnlyMany
  storageClassName: ''
  volumeName: s3-training-cached-pv
  resources:
    requests:
      storage: 1Ti
```

Un TTL de 300segundos puede ocultar durante ese período los cambios externos; usa prefijos de conjuntos de datos inmutables/versionados cuando esto importe. El contenido en caché está en texto sin cifrar en el almacenamiento local, así que incluye el acceso al nodo/almacenamiento en el modelo de amenazas. Calcula por separado la capacidad de la caché, la expulsión de datos y la memoria del Pod de Mountpoint frente a los contenedores de entrenamiento. Otra opción compatible es una caché PVC efímera con `cache: ephemeral`, su StorageClass y los campos de solicitud de almacenamiento; evalúa su ciclo de vida y costo. No pases una ruta de caché host heredada suponiendo que CSI v2 todavía la usa.

### Ejemplo de entrenamiento con un conjunto de datos grande

Esta es una **plantilla de integración no ejecutada**, no una prueba comparativa optimizada de p4d. Prepara una imagen compatible con GPU y revisada que contenga `/opt/training/train.py`, cuatro GPU programables/complementos de dispositivos, la cuenta y el PVC de datos en caché anteriores, y un PVC RWX de salida con permisos de escritura `reviewed-model-output-rwx` accesible a UID/GID1000. El script debe implementar los argumentos mostrados y crear su directorio de salida independiente. Resuelve todos los marcadores de posición antes de implementar.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: s3-sharded-training
  namespace: storage-demo
spec:
  completions: 4
  parallelism: 4
  completionMode: Indexed
  backoffLimit: 0
  activeDeadlineSeconds: 7200
  template:
    spec:
      serviceAccountName: s3-access-sa
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: trainer
        image: registry.example.com/reviewed-trainer:replace-me
        command:
        - sh
        - -c
        args:
        - exec python /opt/training/train.py --data-dir=/data --shard-index="$JOB_COMPLETION_INDEX"
          --shard-count=4 --output-dir="/models/$JOB_COMPLETION_INDEX"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
          limits:
            cpu: '8'
            memory: 32Gi
            nvidia.com/gpu: 1
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: data
          mountPath: /data
          readOnly: true
        - name: output
          mountPath: /models
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: training-data-cached
          readOnly: true
      - name: output
        persistentVolumeClaim:
          claimName: reviewed-model-output-rwx
      - name: tmp
        emptyDir: {}
```

Las cuatro finalizaciones indexadas son fragmentos de datos independientes, uno por GPU. No configuran la coordinación de entrenamiento distribuido, la sincronización de gradientes ni efectos secundarios exactamente una vez. Haz que el tratamiento de las salidas sea seguro ante reintentos. Los ejemplos anteriores de 4GPU/8GPU eran diseños ilustrativos distintos, no mediciones comparativas; elige hardware/recursos reales según requisitos medidos.

### Cómo elegir entre S3, EFS o FSx

| Consideración | Mountpoint/S3 | EFS | FSx for Lustre |
|---|---|---|---|
| Interfaz | Subconjunto de sistema de archivos con respaldo en objetos | Sistema de archivos NFS administrado | Sistema de archivos Lustre paralelo |
| Uso habitual | Conjuntos de datos de entrada grandes e inmutables | Archivos compartidos de aplicaciones | E/S paralela HPC/ML compatible |
| Escrituras | Límites documentados de escritura secuencial/sobrescritura y anexado específico del bucket | Escrituras del sistema de archivos con coordinación de la aplicación | Escrituras del sistema de archivos con coordinación de la aplicación |
| Evidencia para el dimensionamiento | Mezcla de solicitudes, caché, red y distribución de objetos | Modo de rendimiento/caudal, clientes y patrón de acceso | Implementación, capacidad, rendimiento, clientes y distribución en franjas |
| Costo/concurrencia | Mide solicitudes, transferencia, caché y límites del cliente | Mide rendimiento, almacenamiento y límites del cliente | Mide asignación, rendimiento y límites del cliente |

El nombre del servicio no permite establecer una clasificación universal de costo bajo/medio/alto ni de clientes ilimitados.

## Optimización del rendimiento del almacenamiento {#storage-performance-optimization}

Veamos diversas estrategias para optimizar el rendimiento del almacenamiento en EKS.

![Diagrama de ajuste del rendimiento del almacenamiento que asigna cargas de trabajo de bases de datos, servidores web, análisis y aprendizaje automático a EBS, EFS y FSx for Lustre.](../.gitbook/assets/en-eks-04-eks-storage-part2-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-4.html)

### Optimización del rendimiento de EBS

Elige el tipo de volumen y las IOPS/rendimiento aprovisionados según los requisitos medidos de la carga de trabajo y los límites EBS de la instancia. Los valores anteriores de 16,000IOPS/1,000MiB/s siguen siendo ejemplos válidos de configuración, pero no son los máximos universales actuales de gp3: gp3 admite hasta 80,000IOPS/2,000MiB/s en las Regiones, sujeto a restricciones de tamaño/IOPS, con límites inferiores en Outposts. No supongas que el aprovisionamiento al máximo es necesario o suficiente.

Los volúmenes vacíos no necesitan inicialización. Los volúmenes restaurados a partir de instantáneas y las copias nativas pueden sufrir latencia de inicialización; los procedimientos son distintos. **Escribir ceros destruye los datos existentes y no es un procedimiento de inicialización seguro.** Identifica primero el volumen exacto. Para las restauraciones de instantáneas, evalúa las tasas de inicialización aprovisionadas compatibles, fast snapshot restore o el procedimiento documentado basado en lectura; esas funciones de aceleración no se aplican a las copias nativas. Lo siguiente solo inspecciona metadatos en un entorno de nodo autorizado:
```bash
lsblk -o NAME,SERIAL,SIZE,TYPE,MOUNTPOINT
```

### Optimización del rendimiento de EFS

AWS recomienda el modo de rendimiento General Purpose, incluso para cargas de trabajo muy concurrentes; Max I/O es una opción de generación anterior con mayor latencia de operaciones. Adapta el modo de rendimiento a la demanda observada. Configura las opciones de montaje en una StorageClass o un PV, no en `Pod.spec.volumes`.

Esta es una clase alternativa para nuevos claims. Los tamaños RPC recomendados de 1MiB por el auxiliar de EFS, el montaje hard, los tiempos de espera y noresvport son un punto de partida, no una prueba comparativa. `retrans=2` activa una recuperación adicional después de los reintentos; un montaje hard no abandona las solicitudes después de dos intentos. Prepara el ID del sistema de archivos y la identidad del punto de acceso como en la Parte 1:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-tuned
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
- rsize=1048576
- wsize=1048576
- hard
- timeo=600
- retrans=2
- noresvport
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

### Optimización del rendimiento de FSx for Lustre

Selecciona conjuntamente la implementación, el almacenamiento, el rendimiento y la capacidad de los clientes. Planifica la distribución en franjas de Lustre según el tamaño de los archivos, la concurrencia y los cuellos de botella medidos; más franjas no siempre implican más velocidad. Usa las opciones de montaje compatibles de PV/StorageClass y elige una política atime, en lugar de combinar `noatime` y `relatime`, que son incompatibles. Los efectos de la compresión dependen de los datos. `s3ImportPath` es un parámetro CSI compatible, pero la disponibilidad y automatización de importación/exportación dependen de la integración FSx seleccionada.

### Optimización del almacenamiento para cargas de trabajo vLLM

Reutiliza la asignación explícita de clase/PVC anterior en lugar de un campo `storageCapacity` que solo figure en la clase. Compara mediante pruebas el estado frío/cálido de la carga de modelos, el acceso a metadatos, la inicialización de CPU/GPU y los consumidores simultáneos. La cuantización/división en fragmentos cambia el comportamiento de memoria/cómputo del modelo, además de la distribución de archivos, y no es una optimización automática de almacenamiento. EFA solo ayuda a un sistema de archivos/pila de comunicación compatible; elegir una instancia de GPU compatible con EFA no acelera por sí solo todas las rutas de almacenamiento.

## Conclusión

Este documento trató FSx for Lustre, S3, las instantáneas, la expansión de volúmenes y la optimización del rendimiento en Amazon EKS. Cada opción de almacenamiento tiene características y casos de uso distintos, así que es importante seleccionar y optimizar la solución de almacenamiento apropiada para los requisitos de la aplicación.

La próxima parte tratará la supervisión, la resolución de problemas, la optimización de costos y la seguridad del almacenamiento de EKS.

## Referencias

* [Controlador CSI de Amazon FSx for Lustre](https://github.com/kubernetes-sigs/aws-fsx-csi-driver)
* [Controlador CSI de Amazon S3](https://github.com/awslabs/mountpoint-s3-csi-driver)
* [Instantáneas de volúmenes de Kubernetes](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
* [Copia de seguridad y restauración de Velero](https://velero.io/docs/)
* [Prácticas recomendadas de almacenamiento de Amazon EKS](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)

* [Configuración de Mountpoint CSI2.8](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
* [Caché de Mountpoint CSI2.8](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CACHING.md)
* [Semántica del sistema de archivos Mountpoint1.23](https://github.com/awslabs/mountpoint-s3/blob/mountpoint-s3-1.23.0/doc/SEMANTICS.md)
* [Autenticación S3A de Hadoop3.5](https://hadoop.apache.org/docs/r3.5.0/hadoop-aws/tools/hadoop-aws/index.html)
* [Ciclo de vida de instantáneas CSI de Velero1.18](https://velero.io/docs/v1.18/csi/)
* [Compatibilidad del complemento AWS de Velero](https://github.com/velero-io/velero-plugin-for-aws)
* [Copia nativa de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
* [Multi-Attach de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes-multi.html)
* [Identidades del complemento CSI de FSx](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [cuestionario sobre el tema](../quizzes/eks/04-eks-storage-part2-quiz.md).
