# Parte 2: Clases de almacenamiento

> **Última actualización**: 16 de octubre de 2026

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

FSx for Lustre es un sistema de archivos paralelo para cargas de trabajo compatibles de HPC, aprendizaje automático y análisis. Su rendimiento depende del tipo de implementación y almacenamiento, la capacidad, el rendimiento aprovisionado, los clientes y la red. Un sistema de archivos pequeño como el del ejemplo no alcanza todos los máximos agregados anunciados para el servicio.

El diagrama ilustra la integración opcional con un repositorio de datos de S3. Deben configurarse las políticas, tareas y permisos de importación/exportación; crear un volumen CSI por sí solo no establece una sincronización bidireccional automática.

![Diagrama de arquitectura de los Pods de entrenamiento e inferencia de ML que montan FSx for Lustre a través del controlador FSx CSI, con FSx sincronizando datos con S3.](../.gitbook/assets/en-eks-04-eks-storage-part2-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-0.html)

### Instalación del controlador FSx for Lustre CSI

Usa el complemento de EKS compatible o la versión publicada del chart de Helm, según el método que gestione el responsable de la infraestructura. Para el ejemplo de complemento administrado siguiente, establece `CSI_ADDON_NAME=aws-fsx-csi-driver`. Prepara un rol para `kube-system/fsx-csi-controller-sa` con los permisos revisados del controlador FSx, la relación de confianza de Pod Identity y su agente. También se admite IRSA mediante una relación de confianza OIDC y la opción de rol correspondiente del complemento. Pod Identity requiere su agente; IRSA no. FSx CSI no admite Fargate como entorno de nodos. Comprueba la compatibilidad del kernel de Linux, el cliente Lustre y el entorno de cómputo que vas a utilizar.

Crear un rol con `eksctl --role-only` no crea una ServiceAccount de Kubernetes. El complemento administrado crea su propia cuenta; una instalación de Helm debe crear o utilizar la cuenta real y asociarle la identidad prevista. Antes de combinar la creación del rol con `serviceAccount.create=false`, prepara esa cuenta.
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
Este procedimiento se detiene si detecta una instalación existente. En ese caso, coordina la migración o actualización con su responsable. Que el complemento esté Active no demuestra que el sistema de archivos se pueda montar. Los ejemplos siguientes reutilizan el espacio de nombres dedicado `storage-demo` de la Parte 1; también requieren revisar los nombres de los recursos de ámbito de clúster.

### Creación de un sistema de archivos FSx for Lustre

**Elige aprovisionamiento dinámico o estático.** El aprovisionamiento dinámico crea un sistema de archivos a partir del PVC; no adopta otro que hayas creado antes. El procedimiento manual opcional siguiente corresponde al aprovisionamiento estático. Selecciona una subred aprobada en una zona de disponibilidad compatible y un grupo de seguridad de Lustre preparado con las reglas necesarias entre clientes y sistema de archivos. No elijas `Subnets[0]` ni des por hecho que TCP 988 basta para cualquier configuración compatible. Este ejemplo requiere que los recursos estén en la VPC del clúster; las VPC conectadas necesitan una revisión independiente del enrutamiento y la seguridad. El procedimiento crea recursos facturables y conserva los ID devueltos para poder inspeccionarlos si falla.
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

Para el aprovisionamiento **dinámico**, especifica la subred y el grupo de seguridad reales en la clase. La capacidad se obtiene de la solicitud del PVC; el parámetro `storageCapacity` de la clase se ignora. No combines SCRATCH_2 con opciones de rendimiento por unidad o de copias de seguridad exclusivas de las implementaciones persistentes. El nombre de montaje devuelto corresponde a volumeAttributes de un PV estático, no a un parámetro `mountName` de la clase.
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

Este consumidor de solo lectura comprueba únicamente que el montaje sea accesible. No ejecuta una carga de GPU ni mide el rendimiento, por lo que no necesita una imagen CUDA. Prepara los permisos del sistema de archivos para UID/GID 1000 y la ruta de red que utilizará el cliente.
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

Consulta el ID, DNSName, MountName y la capacidad reales del sistema de archivos existente. Esta opción sustituye al PVC dinámico. Reemplaza los marcadores de posición siguientes con los datos de la consulta y vincula el PV y el PVC estáticos reservados. `storageClassName: ""` evita el aprovisionamiento dinámico predeterminado. El consumidor debe utilizar `fsx-static-claim`.
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

- **SCRATCH_1/SCRATCH_2** están destinados a datos temporales que se puedan reproducir. Montarlos como PV no les añade la replicación ni la recuperación de una implementación persistente. SCRATCH_2 aporta otras características de ráfaga, rendimiento y cifrado.
- **PERSISTENT_1/PERSISTENT_2** ofrecen implementaciones persistentes con distintas opciones de almacenamiento, rendimiento y latencia. PERSISTENT_2 no está disponible en todas las combinaciones de Región y zona de disponibilidad.
- Adapta los campos de rendimiento al tipo de implementación y almacenamiento elegido. PERSISTENT_2 con SSD admite 125/250/500/1000 MB/s/TiB; las demás combinaciones tienen opciones diferentes. Retain regula el ciclo de vida del recurso en Kubernetes; no aumenta la durabilidad de los datos del almacenamiento temporal.

### Configuración de FSx for Lustre para vLLM

vLLM es un proyecto de inferencia y servicio de LLM, no «Vector Language Model». El ejemplo siguiente muestra una asignación de almacenamiento para archivos de modelos; no representa una implementación de vLLM optimizada o medida. La carga de modelos también depende del formato de archivo, la deserialización en CPU, el estado de la caché y la inicialización de la GPU. Mide el efecto de la compresión, ya que puede añadir trabajo sin beneficio cuando los datos ya están comprimidos.
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

Reutiliza el espacio de nombres dedicado `storage-demo` de la Parte 1. Prepara un bucket existente, su Región y un rol de IAM con permisos limitados al bucket y prefijo previstos. La política de ejemplo permite listar un bucket y leer únicamente `training/`; no concede escritura. Los objetos SSE-KMS también requieren una política de clave adecuada y permisos de descifrado de KMS limitados al alcance necesario. Las políticas de bucket, los endpoints y la confianza entre cuentas pueden añadir restricciones.

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

La ServiceAccount siguiente ilustra **IRSA**. Sustituye el ARN de ejemplo por el del rol preparado, cuya confianza OIDC debe admitir únicamente este clúster, `system:serviceaccount:storage-demo:s3-access-sa` y la audiencia STS. La anotación no crea el rol ni su relación de confianza. Para **EKS Pod Identity**, omite la anotación IRSA y prepara la asociación revisada para la misma cuenta de aplicación, con un agente compatible. Evita configurar ambos mecanismos como una alternativa accidental. No incluyas claves estáticas de AWS en el manifiesto.

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

Este Job de solo lectura, con límites de ejecución, lista objetos mediante la imagen oficial de AWS CLI y la cuenta preparada. Sustituye el bucket y la Región antes de utilizarlo. Sus directorios privados de escritura permiten ejecutar la CLI sin privilegios. Un código de salida satisfactorio no demuestra que la aplicación pueda leer todos los objetos previstos: comprueba el Job, sus registros y la lectura de un objeto autorizado representativo.

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

S3A es la implementación del sistema de archivos `s3a://` de Hadoop, no un montaje de volumen de Kubernetes. Hadoop 3.5.0 utiliza AWS SDK for Java v2. Crea y revisa una imagen con versiones coincidentes de `hadoop-common` y `hadoop-aws`, junto con el paquete compatible del SDK con dependencias reubicadas (shaded). La imagen indicada abajo es un marcador de posición, no una distribución publicada lista para ejecutar. Debe incluir `hadoop` en PATH, `/opt/hadoop/etc/hadoop` y compatibilidad con UID 1000. Combina `hadoop-aws` con las demás herramientas opcionales que necesites. El proveedor de credenciales predeterminado de v2 puede utilizar la identidad de carga de trabajo seleccionada si la versión del SDK incluida la admite. No reutilices una clase de proveedor v1 `com.amazonaws`.

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

Montar una clave del ConfigMap mediante subPath conserva los demás archivos de configuración de Hadoop incluidos en la imagen. Ese montaje no recibe las actualizaciones posteriores del ConfigMap; vuelve a crear el Job cuando cambies la configuración.

### Montaje de un bucket existente con Mountpoint CSI

La combinación revisada del proyecto original es CSI 2.8.0 con Mountpoint 1.23.0 incluido. Instalar Mountpoint 1.24.0 por separado no actualiza automáticamente la imagen de CSI. Comprueba la versión real del complemento de EKS y la compatibilidad del entorno de cómputo: esta versión de CSI requiere Kubernetes 1.31+ y ya no admite AL2 ni Ubuntu 22.04. Coordina la instalación con el responsable de la infraestructura existente; no instales Helm sobre un complemento administrado u otro controlador.

Para una instalación gestionada por Helm, genera primero los manifiestos de la **versión publicada del chart** y revísalos. Usa la versión real del clúster en `--kube-version`. El chart de una copia de trabajo de Git no es la distribución admitida; no eludas su restricción de publicación. Antes de desplegar mediante el responsable elegido, revisa los componentes privilegiados de nodo, quién gestiona las CRD y el espacio de nombres `mount-s3`:

```bash
set -euo pipefail
helm repo add aws-mountpoint-s3-csi-driver https://awslabs.github.io/mountpoint-s3-csi-driver
helm repo update aws-mountpoint-s3-csi-driver
helm template aws-mountpoint-s3-csi-driver \
  aws-mountpoint-s3-csi-driver/aws-mountpoint-s3-csi-driver \
  --version 2.8.0 --namespace kube-system --kube-version 1.36.0 --include-crds \
  > s3-driver-review.yaml
```

El chart publicado crea `s3-csi-driver-sa` y `s3-csi-driver-controller-sa` de forma predeterminada. El PV siguiente selecciona explícitamente **credenciales a nivel de Pod** mediante `s3-access-sa`; para este volumen se ignoran las credenciales del controlador. Se admiten tanto IRSA como EKS Pod Identity. Para que el volumen esté disponible deben estar instalados el controlador y la identidad; generar correctamente los manifiestos de Helm no basta.

Mountpoint CSI utiliza **aprovisionamiento estático** de un bucket existente, no la StorageClass dinámica de ejemplos antiguos. Mantén vacíos los dos campos storageClassName y vincula explícitamente el PV y el PVC, con un volumeHandle único en el clúster. Los campos de capacidad sirven para los metadatos de vinculación de Kubernetes; no crean ni limitan la capacidad del bucket de S3. Sustituye conjuntamente el bucket, el prefijo y la Región. El montaje de solo lectura y los permisos de IAM son controles independientes:

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

Las opciones de montaje asignan UID/GID 1000 a la propiedad de los archivos expuestos; no cambian la propiedad de los objetos de S3. `allow-other` permite que ese UID de la aplicación acceda al montaje creado por el controlador. Los contenedores de aplicación no necesitan AWS CLI ni privilegios FUSE para leer mediante este montaje.

### Casos de uso de S3

S3 puede almacenar lagos de datos, repositorios de modelos, archivos históricos, recursos estáticos y objetos de auditoría. Usa directamente la API cuando la aplicación necesite versiones de objetos, solicitudes condicionales u otras capacidades fuera de la interfaz de sistema de archivos de Mountpoint. Un directorio de base de datos con escritura que requiera actualizaciones aleatorias y bloqueos POSIX necesita otro diseño de almacenamiento.

## Instantáneas y copias de seguridad {#snapshots-and-backups}

Las instantáneas CSI dependen de la compatibilidad del controlador y el almacenamiento subyacente; disponer de un PVC no garantiza que estén admitidas. El ejemplo de EBS siguiente captura un volumen de bloques en un momento concreto. Cuando sea necesario, pausa las escrituras y vacía los búferes de la aplicación, o utiliza copias de seguridad específicas de la base de datos y archivado de WAL. Una instantánea completada no demuestra coherencia de la aplicación ni capacidad de recuperación de la base de datos a un momento dado.

![Diagrama del flujo de instantáneas desde el PVC de origen, pasando por VolumeSnapshot y SnapshotContent, hasta una instantánea de EBS; luego se restaura en un PVC nuevo.](../.gitbook/assets/en-eks-04-eks-storage-part2-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-2.html)

### Preparación del controlador de instantáneas

Primero inspecciona las CRD de instantáneas existentes, quién gestiona el controlador y el snapshotter de CSI. Usa un complemento de EKS compatible o una versión revisada y fijada de external-snapshotter. No apliques las CRD de la rama master sobre una instalación existente. External-snapshotter 8.6.0 es una referencia revisada del proyecto original, no una actualización automática para todos los complementos. También se aplican los requisitos del controlador y del espacio de nombres de la Parte 1.

```bash
set -euo pipefail
kubectl get crd volumesnapshots.snapshot.storage.k8s.io \
  volumesnapshotcontents.snapshot.storage.k8s.io volumesnapshotclasses.snapshot.storage.k8s.io
kubectl -n storage-demo get pvc ebs-claim -o yaml
```

### Creación de la clase y la instantánea

El controlador de la clase debe coincidir con el del PV. Esta clase administrada manualmente utiliza Retain: eliminar la instantánea de Kubernetes no elimina automáticamente la instantánea de EBS retenida. Registra su responsable y coste, y distingue esta política del ciclo de vida de Velero explicado más adelante. El ejemplo de EBS no necesita parámetros vacíos de secretos del snapshotter.

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

Cuando `readyToUse=true`, inspecciona restoreSize, el contenido vinculado y el controlador. Usa un nombre distinto en el mismo espacio de nombres, con una capacidad al menos igual a restoreSize. El ejemplo de 20Gi presupone que la instantánea no supera ese tamaño. Conserva el claim en uso. Con WaitForFirstConsumer, el PVC de restauración puede permanecer Pending hasta que se programe un consumidor compatible. Valida los datos con una aplicación aislada y compatible antes de realizar un cambio controlado.

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

La combinación revisada es Velero 1.18.4 con el complemento AWS 1.14.4. Verifica la suma de comprobación de la CLI y la compatibilidad del complemento antes de instalar. Velero incorpora la compatibilidad con CSI, pero este procedimiento sigue requiriendo `EnableCSI`; no añadas el antiguo complemento CSI independiente. Prepara un bucket o prefijo privado de copias de seguridad, acceso de red, permisos IAM/KMS limitados y un rol IRSA para `velero/velero`. El comando siguiente genera un manifiesto de instalación nueva para revisar, sin crear recursos:

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

Incluso esta ejecución de prueba de la CLI requiere un kubeconfig real y válido. Generar el manifiesto no comprueba la autorización ni las copias de seguridad. No sobrescribas una instalación existente de Velero o sus CRD. La ServiceAccount predeterminada se crea con la anotación IRSA; `--service-account-name` selecciona una cuenta existente e ignora `--sa-annotations`. Pod Identity es otra opción, con su propia asociación y configuración del agente. No hace falta un archivo de credenciales estáticas.

Para seleccionar la clase de instantáneas CSI, marca como predeterminada solo una clase por controlador, o selecciona una mediante la anotación admitida para la copia de seguridad o la programación. Revisa la clase siguiente junto con las existentes:

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

**Velero administra el ciclo de vida de sus instantáneas de copia de seguridad CSI.** Cuando la copia vence o se elimina, Velero cambia la política de eliminación de VolumeSnapshotContent a Delete y elimina la instantánea, aunque la clase original utilizara Retain. Define el TTL de la copia y cualquier procedimiento independiente de retención o archivo según tus necesidades. Una copia de Velero en S3 no contiene necesariamente todos los datos de los volúmenes: las instantáneas CSI, las copias del sistema de archivos y los mecanismos de transferencia de datos son procedimientos distintos. Por ejemplo, FSx CSI 1.10.0 no implementa instantáneas CSI; utiliza una estrategia de copia compatible con FSx y la aplicación.

```bash
set -euo pipefail
velero schedule create storage-demo-daily --schedule="0 1 * * *" \
  --include-namespaces=storage-demo --ttl=168h0m0s -o yaml > velero-schedule-review.yaml
```

El comando de programación también genera únicamente YAML. El responsable debe desplegar la programación revisada y comprobar la fase real de Backup, los errores, la finalización de las instantáneas o transferencias de datos y las pruebas de restauración. Programar instantáneas no permite por sí solo recuperar una base de datos a cualquier momento dado.

Para recuperar datos, selecciona una copia de seguridad real y verificada. Incluso con `-o yaml`, este comando consulta la API y lee el Backup elegido, por lo que necesita acceso de lectura al clúster previsto. La vista previa limita los tipos de recursos solicitados y reasigna el espacio de nombres. Antes de enviarla, inspecciona las dependencias y las acciones de restauración de los complementos. Confirma que el espacio de nombres de destino esté aislado, que no haya conflictos de nombres y que sean válidas las correspondencias de StorageClass, controlador CSI, KMS y zona de disponibilidad. El ejemplo no sustituye a un procedimiento completo de recuperación en producción:

```bash
set -euo pipefail
: "${VERIFIED_BACKUP:?Choose an actual completed backup after checking its contents/errors}"
velero restore create storage-demo-recovery-review --from-backup "$VERIFIED_BACKUP" \
  --namespace-mappings storage-demo:storage-recovery \
  --include-namespaces storage-demo \
  --include-resources persistentvolumes,persistentvolumeclaims,volumesnapshots.snapshot.storage.k8s.io,volumesnapshotcontents.snapshot.storage.k8s.io \
  --restore-volumes=true -o yaml > velero-restore-review.yaml
```

Inicia las cargas restauradas cuando los datos hayan superado las comprobaciones de la aplicación y conserva una vía de reversión. La restauración CSI entre clústeres requiere un controlador con el mismo nombre y acceso a las instantáneas y claves. Reasignar el espacio de nombres no hace portátiles los recursos de la nube.

## Expansión y cambio de tamaño de volúmenes {#volume-expansion-and-resizing}

![Diagrama del proceso de expansión de volumen: desde la StorageClass que permite la expansión, pasando por la edición del PVC, la llamada CSI y el crecimiento de EBS, hasta el cambio de tamaño del sistema de archivos.](../.gitbook/assets/en-eks-04-eks-storage-part2-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-3.html)

Utiliza una clase con `allowVolumeExpansion: true` y un controlador CSI y sistema de archivos que admitan la expansión. Conserva el storageClassName del claim vinculado; cambiarlo no sirve para redimensionar el volumen. El ejemplo reutiliza `ebs-gp3` de la Parte 1 y solo aumenta la capacidad solicitada por el claim. Comprueba antes su solicitud y capacidad actuales para no intentar reducir un claim que ya sea mayor.
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
CSI gestiona la expansión del almacenamiento subyacente y del sistema de archivos cuando ambos la admiten. Inspecciona las condiciones del PVC, los registros del controlador y los nodos, y la capacidad montada. Si hace falta, sigue el procedimiento documentado del controlador para volver a montar o reiniciar. No ejecutes `resize2fs` sobre un supuesto `/dev/xvdf` dentro del contenedor de aplicación ni edites la capacidad del PV para eludir la expansión. Planifica límites de cuota y coste; evita aumentos automáticos repetidos mientras siga pendiente uno anterior.

## Clonación de volúmenes {#volume-cloning}

Las versiones actuales de EBS CSI admiten clonar PVC mediante `dataSource` y la capacidad de clonación de CSI. EBS CSI 1.67.0 utiliza la copia nativa de volúmenes de EBS (`CopyVolumes`), no una instantánea oculta. Comprueba antes la compatibilidad del controlador o complemento desplegado. El volumen de destino es independiente, pero estar disponible y haber completado la inicialización para alcanzar el rendimiento previsto son estados diferentes.



Para el procedimiento habitual con dataSource de PVC, usa un origen vinculado en el mismo espacio de nombres, un modo de volumen y controlador compatibles, y una solicitud de capacidad al menos igual a la del origen. Especifica storageClassName: si lo omites se aplican las reglas de clase predeterminada, sin heredar automáticamente la clase del origen. Las copias nativas de EBS permanecen en la zona de disponibilidad del origen. Ofrecen coherencia ante fallos; la coherencia de la aplicación requiere pausar las escrituras y vaciar los búferes cuando corresponda. Solo puede inicializarse una copia de cada origen a la vez, y se aplican las cuotas de cuenta y Región.

Este origen dedicado a la práctica evita iniciar un clon de base de datos sin verificar en un espacio de nombres de producción. Sustituye la zona de disponibilidad de ejemplo **tanto en el escritor como en el lector** por una zona real compatible. El Job de preparación utiliza el PVC de origen, crea un marcador sin sobrescribir otro existente y termina:
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
Cuando finalice el Job de preparación, crea el clon independiente y su consumidor de solo lectura. La comprobación del marcador ilustra qué validar; durante esta revisión no se ejecutó una copia en la nube. Copiar una base de datos no restablece sus contraseñas. Si después arrancas la copia como base de datos, utiliza una versión compatible.
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

No deduzcas la velocidad, el espacio adicional ni el RPO a partir del número de pasos del procedimiento. Las copias nativas de volúmenes no admiten fast snapshot restore ni tasas de inicialización aprovisionadas; sigue las indicaciones de inicialización específicas de la copia.

## Multi-Attach de EBS {#multi-attach-ebs}

EC2 admite Multi-Attach para volúmenes io1/io2 aptos, con hasta 16 instancias Nitro compatibles en una misma zona de disponibilidad, sujeto a las restricciones del tipo de volumen y la Región. El **aprovisionamiento dinámico de EBS CSI 1.66.0 admite io2 + ReadWriteMany + volumeMode: Block** y habilita Multi-Attach a partir de esa capacidad. En este procedimiento, `multiAttachEnabled` no es un parámetro admitido de StorageClass. RWOP limita el volumen a un Pod y no es el modo de acceso para Multi-Attach.



Compartir un dispositivo de bloques no coordina las escrituras de las aplicaciones. Varios nodos no deben montar por separado un sistema ext4/XFS ordinario en lectura y escritura. Hace falta una aplicación coordinada o un sistema de archivos de clúster adecuado, con un diseño de aislamiento de acceso (fencing). io2 admite fencing mediante reservas NVMe, pero la aplicación debe utilizarlas correctamente. La demostración siguiente solo adjunta el volumen: **no realiza E/S ni formatea el dispositivo**. Sus etiquetas y reglas de antiafinidad requieren dos nodos adecuados en la zona de disponibilidad del volumen. Una carga real necesita revisar el acceso al dispositivo y la coordinación; el contenedor del ejemplo permanece inactivo:
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
Los volúmenes io2 Multi-Attach admiten modificar tamaño e IOPS en las condiciones del servicio; no es correcto afirmar que nunca permiten redimensionar en línea. io1 tiene una compatibilidad diferente. Para habilitar o deshabilitar Multi-Attach, el volumen debe estar desconectado. El procedimiento seguro de expansión depende además de CSI, el sistema de archivos y la aplicación. Un fallo del volumen compartido puede afectar a todas las instancias conectadas. Retain y los ajustes de conexión no sustituyen a las copias de seguridad.

## Análisis detallado de Mountpoint para S3 CSI {#mountpoint-for-s3-csi-deep-dive}

El comportamiento siguiente se comprobó con Mountpoint 1.23.0, incluido en CSI 2.8.0. Verifica la versión instalada antes de utilizar opciones de versiones independientes más recientes.



### Características de rendimiento

Mountpoint suele resultar adecuado para leer secuencialmente objetos grandes y escribir secuencialmente objetos nuevos; realiza la precarga automáticamente. También admite lecturas aleatorias de rangos, cuyo resultado depende del tamaño de los objetos, la tasa de solicitudes, la red, la caché y la concurrencia de la aplicación. Las escrituras aleatorias arbitrarias sobre datos existentes no están admitidas; no son simplemente una operación más lenta.

**Cifras históricas sin verificar:** el texto anterior en inglés incluía estos valores agregados sin una configuración reproducible ni una fuente identificable. Se conservan para documentar esas afirmaciones; no son límites actuales del servicio, mediciones realizadas en esta revisión ni garantías para dimensionar una carga.

| Operación histórica | Afirmación original |
|---|---|
| Lectura secuencial, archivos grandes | Hasta 100 Gbps agregados |
| Escritura secuencial, archivos nuevos | Hasta 50 Gbps agregados |
| Lecturas aleatorias pequeñas | Mayor latencia y menor rendimiento, según la carga |

La clasificación cualitativa anterior de «excelente/bueno/moderado» tampoco se basó en una prueba comparativa controlada.

### Límites del sistema de archivos y coherencia

- S3 ofrece coherencia fuerte en lectura y listado. La caché de Mountpoint puede mantener deliberadamente metadatos, contenido obsoleto o resultados negativos hasta que venza su TTL. Eso no convierte a S3 en un servicio de coherencia eventual.
- Los archivos nuevos se escriben secuencialmente. Reemplazar un objeto requiere `allow-overwrite` y abrirlo con truncamiento; siguen sin admitirse las actualizaciones aleatorias arbitrarias.
- Los buckets de directorio de S3 Express One Zone en zonas de disponibilidad admiten añadir datos al final con `incremental-upload` y renombrar atómicamente un archivo individual. Los buckets de uso general no admiten renombrar archivos mediante esta versión de Mountpoint, y no se admite renombrar directorios. Los buckets de directorio en Local Zones tienen otras capacidades. Renombrar reemplazando un objeto existente requiere además las opciones y permisos de sobrescritura.
- El borrado debe habilitarse con `allow-delete` y permisos IAM. Los ejemplos de solo lectura no habilitan ninguno de los dos. Añadir datos al final no equivale siempre a «crear una nueva versión del objeto».
- No se admiten enlaces duros o simbólicos, chmod/chown, atributos extendidos, bloqueos POSIX, archivos de dispositivo ni la semántica habitual de archivos dispersos. La corrección de una base de datos no puede depender de estas operaciones ausentes.

### Ajustes de caché

Coloca las opciones de la CLI de Mountpoint en **PV.spec.mountOptions**, no en los parámetros de StorageClass. Los valores son cadenas como `metadata-ttl 300`. Mountpoint 1.23 utiliza segundos para el TTL de metadatos, **MiB** para la opción independiente `max-cache-size` y **bytes** para read/write-part-size; 8 MiB equivalen a 8 388 608 bytes. Los ejemplos anteriores de prefetch-bytes/read-ahead/max-read-parallelism/max-cache-size-mb/cache-block-size no son opciones válidas de la CLI 1.23.

CSI v2 crea almacenamiento de caché para su **Pod de Mountpoint**, normalmente en `mount-s3`. Un emptyDir del Pod de aplicación no se utiliza como esa caché. Este PV estático alternativo tiene una caché emptyDir en disco de 10Gi, cuyo límite aplica el controlador. Memory utilizaría RAM mediante tmpfs, no NVMe. Sustituye el bucket, el prefijo y la Región por los valores reales y usa el PVC independiente vinculado previamente:

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

Un TTL de 300 segundos puede ocultar cambios externos durante ese tiempo. Si esto afecta a la aplicación, usa prefijos de conjuntos de datos inmutables o versionados. El contenido se guarda sin cifrar en el almacenamiento local; incluye el acceso a nodos y almacenamiento en el modelo de amenazas. Planifica la capacidad y expulsión de la caché, y la memoria del Pod de Mountpoint, por separado de los contenedores de entrenamiento. También se admite una caché de PVC efímero con `cache: ephemeral`, su clase de almacenamiento y sus campos de solicitud. Evalúa su ciclo de vida y coste. No pases una ruta de caché del host de versiones anteriores suponiendo que CSI v2 sigue utilizándola.

### Ejemplo de entrenamiento con un conjunto de datos grande

Este ejemplo es una **plantilla de integración que no se ha ejecutado**, no una prueba de rendimiento optimizada de p4d. Prepara una imagen revisada y compatible con GPU que incluya `/opt/training/train.py`, cuatro GPU que se puedan programar y sus complementos de dispositivo, la cuenta y el PVC de datos en caché anteriores, y un PVC RWX de salida `reviewed-model-output-rwx` con escritura para UID/GID 1000. El script debe implementar los argumentos mostrados y crear su propio directorio de salida. Resuelve todos los marcadores de posición antes del despliegue.

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

Las cuatro ejecuciones indexadas procesan fragmentos de datos independientes, con una GPU cada una. No configuran el encuentro inicial del entrenamiento distribuido, la sincronización de gradientes ni la ejecución única de efectos secundarios. Prepara las salidas para admitir reintentos sin dañarlas. Los ejemplos anteriores de 4 y 8 GPU ilustraban distribuciones diferentes; no eran mediciones comparativas. Elige el hardware y los recursos según requisitos medidos.

### Cómo elegir entre S3, EFS o FSx

| Consideración | Mountpoint/S3 | EFS | FSx for Lustre |
|---|---|---|---|
| Interfaz | Parte de una interfaz de sistema de archivos sobre objetos | Sistema de archivos NFS administrado | Sistema de archivos paralelo Lustre |
| Uso habitual | Conjuntos de entrada grandes e inmutables | Archivos de aplicación compartidos | E/S paralela compatible para HPC/ML |
| Escrituras | Límites documentados de escritura secuencial, sobrescritura y anexado según el bucket | Escrituras con coordinación de la aplicación | Escrituras con coordinación de la aplicación |
| Datos para dimensionar | Mezcla de solicitudes, caché, red y distribución de objetos | Modo de rendimiento y caudal, clientes y patrón de acceso | Implementación, capacidad, caudal, clientes y distribución en franjas |
| Coste y concurrencia | Medir solicitudes, transferencia, caché y límites de clientes | Medir caudal, almacenamiento y límites de clientes | Medir asignación, caudal y límites de clientes |

El nombre del servicio no permite establecer una clasificación universal de costo bajo/medio/alto ni de clientes ilimitados.

## Optimización del rendimiento del almacenamiento {#storage-performance-optimization}

Veamos diversas estrategias para optimizar el rendimiento del almacenamiento en EKS.

![Diagrama de ajuste del rendimiento del almacenamiento que asigna cargas de trabajo de bases de datos, servidores web, análisis y aprendizaje automático a EBS, EFS y FSx for Lustre.](../.gitbook/assets/en-eks-04-eks-storage-part2-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-4.html)

### Optimización del rendimiento de EBS

Elige el tipo de volumen, las IOPS y el caudal aprovisionados según los requisitos medidos de la carga y los límites EBS de la instancia. Los ejemplos anteriores de 16 000 IOPS y 1000 MiB/s siguen siendo configuraciones válidas, pero no representan los máximos actuales de gp3 en todos los entornos. En las Regiones, gp3 admite hasta 80 000 IOPS y 2000 MiB/s, sujeto a restricciones de tamaño e IOPS; Outposts tiene límites inferiores. Aprovisionar el máximo no es necesariamente necesario ni suficiente.

Los volúmenes vacíos no necesitan inicialización. Los restaurados de instantáneas y las copias nativas pueden presentar latencia de inicialización, pero utilizan procedimientos diferentes. **Escribir ceros destruye los datos existentes y no es un procedimiento de inicialización seguro.** Identifica primero el volumen exacto. Para restauraciones de instantáneas, evalúa las tasas de inicialización aprovisionadas admitidas, fast snapshot restore o el procedimiento documentado de lectura. Esas funciones de aceleración no se aplican a las copias nativas. El comando siguiente solo inspecciona metadatos en un entorno de nodo autorizado:
```bash
lsblk -o NAME,SERIAL,SIZE,TYPE,MOUNTPOINT
```

### Optimización del rendimiento de EFS

AWS recomienda el modo General Purpose incluso para cargas muy concurrentes. Max I/O pertenece a una generación anterior y tiene mayor latencia por operación. Ajusta el modo de caudal a la demanda observada. Configura las opciones de montaje en una StorageClass o un PV, no en `Pod.spec.volumes`.

Esta clase es una alternativa para claims nuevos. Los tamaños RPC de 1 MiB recomendados por el auxiliar de EFS, el montaje hard, los tiempos de espera y noresvport son un punto de partida, no resultados de una prueba de rendimiento. `retrans=2` activa mecanismos adicionales de recuperación tras los reintentos; un montaje hard no abandona la solicitud después de dos intentos. Prepara el ID del sistema de archivos y la identidad del punto de acceso como en la Parte 1:
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

Selecciona conjuntamente la implementación, el almacenamiento, el caudal y la capacidad de los clientes. Planifica la distribución en franjas de Lustre según el tamaño de los archivos, la concurrencia y los cuellos de botella medidos; aumentar las franjas no siempre mejora la velocidad. Usa opciones de montaje admitidas en PV o StorageClass y elige una sola política atime, sin combinar `noatime` y `relatime`. El efecto de la compresión depende de los datos. CSI admite `s3ImportPath`, pero las funciones y la automatización de importación y exportación dependen de la integración FSx elegida.

### Optimización del almacenamiento para cargas de trabajo vLLM

Reutiliza la asignación explícita de clase y PVC anterior; no la sustituyas por un campo `storageCapacity` de la clase. Mide la carga de modelos con caché fría y caliente, el acceso a metadatos, la inicialización de CPU/GPU y los consumidores simultáneos. La cuantización y fragmentación modifican la memoria y el cómputo del modelo, además de la distribución de archivos; no optimizan automáticamente el almacenamiento. EFA solo aporta beneficios con un sistema de archivos, cliente o pila de comunicación compatibles. Elegir una instancia GPU compatible con EFA no acelera por sí solo todas las rutas de almacenamiento.

## Conclusión

Este documento trató FSx for Lustre, S3, las instantáneas, la expansión de volúmenes y la optimización del rendimiento en Amazon EKS. Cada opción de almacenamiento tiene características y casos de uso distintos, así que es importante seleccionar y optimizar la solución de almacenamiento apropiada para los requisitos de la aplicación.

La próxima parte tratará la supervisión, la resolución de problemas, la optimización de costos y la seguridad del almacenamiento de EKS.

## Referencias

* [Controlador CSI de Amazon FSx for Lustre](https://github.com/kubernetes-sigs/aws-fsx-csi-driver)
* [Controlador CSI de Amazon S3](https://github.com/awslabs/mountpoint-s3-csi-driver)
* [Instantáneas de volúmenes de Kubernetes](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
* [Copia de seguridad y restauración de Velero](https://velero.io/docs/)
* [Prácticas recomendadas de almacenamiento de Amazon EKS](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)

* [Configuración de Mountpoint CSI 2.8](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
* [Caché de Mountpoint CSI 2.8](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CACHING.md)
* [Semántica del sistema de archivos de Mountpoint 1.23](https://github.com/awslabs/mountpoint-s3/blob/mountpoint-s3-1.23.0/doc/SEMANTICS.md)
* [Autenticación S3A de Hadoop 3.5](https://hadoop.apache.org/docs/r3.5.0/hadoop-aws/tools/hadoop-aws/index.html)
* [Ciclo de vida de las instantáneas CSI de Velero 1.18](https://velero.io/docs/v1.18/csi/)
* [Compatibilidad del complemento AWS de Velero](https://github.com/velero-io/velero-plugin-for-aws)
* [Copia nativa de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
* [Multi-Attach de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes-multi.html)
* [Identidades del complemento CSI de FSx](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [cuestionario sobre el tema](../quizzes/eks/04-eks-storage-part2-quiz.md).
