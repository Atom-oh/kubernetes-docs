# Cuestionario de almacenamiento de EKS - Parte 2

> **Última actualización**: 11 de septiembre de 2026

Este cuestionario aborda la selección de almacenamiento, las reclamaciones de StatefulSet, S3/Mountpoint, la clonación, las copias de seguridad y la recuperación. Los ejemplos reutilizan los controladores y las clases preparados en el capítulo, así como espacios de nombres dedicados. Durante esta revisión no se ejecutaron aprovisionamientos en la nube, recuperaciones de bases de datos ni pruebas de rendimiento. Comprueba quién es el propietario y sustituye los marcadores de posición antes de usar los ejemplos.

## Preguntas de opción múltiple

### 1. ¿Cómo debe StatefulSet asignar un PVC separado a cada ordinal?

- A. Asignar manualmente el nombre de cada reclamación en un ConfigMap
- B. Usar volumeClaimTemplates
- C. Dar a todas las réplicas el mismo directorio de base de datos
- D. Deshabilitar el controlador CSI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

`volumeClaimTemplates` proporciona a cada ordinal de StatefulSet su propia reclamación, con el nombre `<template>-<statefulset>-<ordinal>`. Normalmente, un Pod reiniciado reutiliza su reclamación, sujeto a la topología del almacenamiento y al ciclo de vida de la reclamación. StatefulSet no copia los datos de la base de datos entre réplicas.

`OrderedReady` es la política de administración de Pods predeterminada; `Parallel` modifica el comportamiento del escalado. No hay una garantía universal de que la creación o eliminación de cada PVC siga el orden de los Pods. La retención de PVC se puede configurar con `persistentVolumeClaimRetentionPolicy`; Retain es el valor predeterminado, mientras que Delete puede eliminar reclamaciones al reducir la escala o borrar StatefulSet. reclaimPolicy del PV es una decisión de ciclo de vida del backend independiente.

Las tres réplicas siguientes solo muestran archivos de marcador persistentes independientes. **No son una base de datos replicada**. El Service headless aporta identidad; esta demostración de archivos con procesos inactivos no implementa un servidor HTTP en su puerto de servicio ilustrativo. Reutiliza la clase `ebs-gp3` preparada en el capítulo:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  clusterIP: None
  selector:
    app: stateful-files
  ports:
  - name: unused-demo
    port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  serviceName: stateful-files
  replicas: 3
  podManagementPolicy: OrderedReady
  selector:
    matchLabels:
      app: stateful-files
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: stateful-files
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
      - name: file-owner
        image: busybox:1.38.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          if [ ! -e /data/owner ]; then (set -C; printf "%s\n" "$POD_NAME" > /data/owner); fi
          cat /data/owner
          sleep 3600
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
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        storage-demo: stateful-files
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: ebs-gp3
      resources:
        requests:
          storage: 10Gi
```



```bash
kubectl -n storage-demo get pvc -l storage-demo=stateful-files -o wide
```

Las etiquetas de la plantilla de reclamación hacen que el selector de inspección sea útil. No elimines reclamaciones retenidas como parte de la limpieza rutinaria de Pods. WFFC selecciona una zona de disponibilidad adecuada para el volumen según las restricciones de planificación; no hace que los datos de EBS estén disponibles en todas las zonas. RWO es una restricción de acceso a nivel de nodo, no una garantía de acceso por un solo Pod; usa RWOP compatible cuando necesites limitar el acceso a un Pod.

</details>

### 2. ¿Qué debe guiar la selección del rendimiento de EBS?

- A. Elegir siempre io1
- B. Las necesidades medidas de la carga de trabajo y los límites del volumen y la instancia
- C. Aprovisionar siempre la capacidad máxima
- D. Colocar cada aplicación en una sola zona de disponibilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Mide la latencia, las IOPS, el tamaño de E/S, la profundidad de cola y el rendimiento; después, ajusta el volumen y los límites de EBS de la instancia. La instancia puede ser el cuello de botella compartido de varios volúmenes, aunque cada uno tenga un aprovisionamiento generoso. También influyen el sistema de archivos, la inicialización, la caché y el comportamiento de la aplicación.

| Tipo | Límite publicado actual, sujeto a condiciones | Consideración habitual |
|---|---|---|
| gp3 | Región: 80,000 IOPS / 2,000 MiB/s; menor en Outposts | Base de 3,000 IOPS / 125 MiB/s, con ajustes de rendimiento de pago independientes |
| io1 | 64,000 IOPS / 1,000 MiB/s | IOPS aprovisionadas sujetas a los límites de instancia y tamaño |
| io2 Block Express | 256,000 IOPS / 4,000 MiB/s | Requisitos de Nitro, tamaño, IOPS y carga de trabajo compatibles |
| st1 | 500 MiB/s | HDD orientado al rendimiento secuencial y al comportamiento de ráfaga |
| sc1 | 250 MiB/s | Acceso secuencial infrecuente en HDD |

Los ajustes anteriores de gp3 de 16,000 IOPS/1,000 MiB/s siguen siendo ejemplos válidos; no son los máximos universales actuales. El tamaño de gp2 afecta al rendimiento base y de ráfaga, mientras que el rendimiento de gp3 se puede aprovisionar por separado, sujeto a sus proporciones. Ningún tipo de volumen es automáticamente óptimo para todas las bases de datos, registros o servidores web. RAID0 es una alternativa independiente que se trata más abajo, no una optimización CSI predeterminada.

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

</details>

### 3. ¿Cuál es la principal ventaja arquitectónica de FSx for Lustre?

- A. El costo más bajo garantizado
- B. No necesitar controladores ni requisitos de red
- C. Un sistema de archivos paralelo para las cargas de trabajo adecuadas
- D. Garantizar que cada PVC alcance 1,000 GB/s

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

FSx for Lustre ofrece un sistema de archivos paralelo administrado para cargas de trabajo compatibles de HPC, ML, análisis y medios. Elige conjuntamente el tipo de despliegue, el cliente y kernel, la capacidad, el rendimiento aprovisionado y la red. Las cifras máximas agregadas promocionales no representan el rendimiento de cualquier PVC pequeño.

SCRATCH_1 y SCRATCH_2 están destinados a datos temporales reproducibles; SCRATCH_2 no obtiene replicación de servidores persistentes por el mero hecho de usarse con un PV. PERSISTENT_1 y PERSISTENT_2 ofrecen distintas opciones compatibles de almacenamiento y rendimiento. Por ejemplo, SSD en PERSISTENT_2 ofrece 125/250/500/1000 MB/s/TiB; no generalices a todos los sistemas de archivos una cifra de 200 MB/s/TiB o de 1,000 GB/s. Esta revisión no verificó esas afirmaciones agregadas anteriores mediante mediciones.

Prepara el complemento administrado o un controlador compatible bajo tu responsabilidad, como se indica en el capítulo. El ejemplo conserva el parámetro compatible `s3ImportPath`; las importaciones y exportaciones requieren un despliegue compatible, permisos y políticas o tareas del repositorio adecuados. Crear recursos con CSI no sincroniza S3 automáticamente en ambos sentidos:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-import-demo
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: NONE
  s3ImportPath: s3://replace-with-owned-data-bucket/training/
```

Las solicitudes del PVC determinan la capacidad dinámica del sistema de archivos; no existe un campo genérico storageCapacity en StorageClass. Hay que medir la compresión y el striping con los datos y la concurrencia reales. Un paralelismo mayor, más stripes o LZ4 no siempre mejoran el rendimiento. Usa el catálogo de complementos administrados de EKS para comprobar la compatibilidad; «FSx no se integra de forma nativa con EKS» no es una razón correcta para descartarlo.

</details>

### 4. ¿Qué modelo de aprovisionamiento de Mountpoint CSI es correcto?

- A. Un s3-sc dinámico crea un bucket
- B. Vinculación estática de PV/PVC a un bucket existente
- C. Un campo de capacidad del PVC define la cuota de S3
- D. Un PVC de sistema de archivos crea automáticamente un sistema de archivos EFS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Usa `s3.csi.aws.com`, un bucket existente, storageClassName vacío en ambos objetos, claimRef y volumeName explícitos, y un volumeHandle único. Coloca las opciones de la CLI en mountOptions del PV. Los metadatos de capacidad de Kubernetes no limitan la capacidad de S3.

</details>

### 5. Con authenticationSource: pod, ¿qué identidad se usa?

- A. Siempre el rol IAM del controlador
- B. Una clave estática incrustada en el PV
- C. Pod Identity o IRSA compatible de la ServiceAccount de la aplicación
- D. Las credenciales de la estación de trabajo de quien creó el PVC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

CSI 2.8 admite Pod Identity e IRSA a nivel de Pod; se ignoran las credenciales del controlador para ese volumen. Deben existir el rol, la asociación y la relación de confianza, el agente cuando sea necesario, y los permisos de bucket y KMS. Una anotación en ServiceAccount no es por sí misma un rol IAM.

</details>

### 6. ¿Dónde coloca CSI v2 la caché emptyDir configurada?

- A. En el Pod de Mountpoint
- B. En cualquier emptyDir de un Pod de aplicación que tenga la misma ruta
- C. Dentro del bucket S3 por definición
- D. Automáticamente en el almacenamiento NVMe de una instancia GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Usa atributos del volumen de caché como `cache: emptyDir` y `cacheEmptyDirSizeLimit`. Memory significa RAM tmpfs. El TTL de metadatos de Mountpoint se expresa en segundos; max-cache-size independiente, en MiB; y los tamaños de las partes de lectura y escritura, en bytes. Las opciones específicas de cada versión deben coincidir con el binario Mountpoint integrado.

</details>

### 7. ¿Por qué una montura con caché quizá no muestre de inmediato un cambio externo en S3?

- A. S3 siempre tiene consistencia eventual en las operaciones de listado
- B. El TTL configurado de la caché puede conservar entradas antiguas o negativas
- C. Todas las escrituras en S3 requieren reiniciar CSI
- D. La capacidad del PV es demasiado pequeña

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

S3 tiene consistencia sólida de lectura y listado. La caché opcional de Mountpoint cambia lo que observa el cliente hasta que vence el TTL. No confundas el comportamiento de la caché con el modelo de consistencia de S3. Cuando la reproducibilidad sea importante, usa prefijos de conjuntos de datos inmutables o ajusta la caché de forma adecuada.

</details>

### 8. ¿Qué conjunto de condiciones corresponde a la clonación nativa de un PVC de EBS?

- A. Cualquier espacio de nombres y zona de disponibilidad
- B. Siempre se hereda la clase de origen
- C. El clon es coherente con la aplicación sin coordinación
- D. Controlador compatible, mismo espacio de nombres y zona de origen, modo compatible y tamaño de destino suficiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

EBS CSI 1.66 utiliza la ruta real de copia nativa de volúmenes. dataSource de un PVC normal requiere el mismo espacio de nombres; las copias de EBS permanecen en la zona de disponibilidad de origen. Define explícitamente la clase y solicita al menos el tamaño del volumen de origen. El volumen puede estar disponible antes de que termine su inicialización en segundo plano; detén o coordina las aplicaciones para obtener la coherencia necesaria.

</details>

### 9. ¿Qué ejemplo coincide con Multi-Attach dinámico en EBS CSI1.66?

- A. gp3 + RWO + multiAttachEnabled:true
- B. io2 + RWOP + escritores ext4 independientes
- C. io2 + RWX + Block sin formato y E/S de aplicación coordinada
- D. Cualquier tipo de EBS que abarque varias zonas de disponibilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El controlador asigna la capacidad de escritura multiwriter en bloques de io2 a Multi-Attach; no existe una opción genérica multiAttachEnabled en StorageClass. Las instancias Nitro aptas deben estar en la zona de disponibilidad del volumen. Un dispositivo compartido no coordina las escrituras ni aplica automáticamente mecanismos de cercado. io2 admite modificaciones de tamaño e IOPS sujetas a las condiciones del servicio y del controlador; no es correcto afirmar que nunca se puede redimensionar.

</details>

### 10. ¿Qué ocurre con una instantánea CSI cuando vence la copia de seguridad de Velero que la posee?

- A. Velero puede establecer deletionPolicy: Delete para el contenido y eliminarla aunque la clase fuera Retain
- B. Retain siempre la conserva para siempre
- C. Solo se elimina el PVC
- D. La instantánea se convierte automáticamente en un objeto S3 portátil

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Velero 1.18 es responsable del ciclo de vida de sus instantáneas CSI. Configura deliberadamente el TTL de la copia y usa un proceso independiente de retención o archivado cuando sea necesario. La compatibilidad CSI integrada también requiere EnableCSI; los metadatos de la copia, las instantáneas CSI nativas y los datos del volumen copiados son cosas distintas.

</details>

## Preguntas de respuesta breve

### 11. ¿Qué ofrece RAID0 y qué debe tener en cuenta un diseño de EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Distribución en bandas, sin redundancia**

RAID0 distribuye bloques entre volúmenes y agrega la capacidad utilizable. El fallo de un miembro puede inutilizar todo el arreglo; no es una solución de copia de seguridad ni de alta disponibilidad. Dos volúmenes iguales podrían ofrecer teóricamente cerca del doble del rendimiento de uno solo, pero únicamente si lo permiten la aplicación, el sistema de archivos, la CPU y los límites de EBS de la instancia. Es un límite teórico, no un resultado medido de 2×.

Un PVC en modo de sistema de archivos montado en `/volume1` es un directorio, no un disco sin formato para mdadm. Un diseño real de bloques requiere `volumeMode: Block`, `volumeDevices`, la identidad exacta del volumen, un componente de almacenamiento autorizado y un procedimiento explícito para inicializar un dispositivo vacío frente a ensamblar un arreglo existente. No lo formatees en cada reinicio de la aplicación. Planifica la conexión al mismo nodo y zona, la reprogramación, los permisos, el crecimiento y la copia de seguridad/restauración coherente de varios volúmenes.

Por eso, la secuencia incondicional mdadm/mkfs del Pod privilegiado anterior no sirve como receta para copiar y pegar. Los ejemplos antiguos de 2–4 volúmenes y franjas de 4/64/128 KiB son candidatos de ajuste sin mediciones verificadas, no valores óptimos universales. Antes de aceptar esta complejidad adicional, compara un único volumen gp3/io2 adecuado, datos temporales reproducibles en Instance Store o FSx.

</details>

### 12. ¿Qué controlan rsize y wsize de EFS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Tamaño máximo de las cargas útiles RPC de lectura y escritura de NFS**

No son tamaños de búfer de sockets TCP. AWS recomienda 1,048,576 bytes (1 MiB) para ambos, junto con `hard,timeo=600,retrans=2,noresvport`, mediante la ruta de montaje NFS/EFS compatible. timeo se expresa en décimas de segundo, por lo que 600 significa 60 segundos. En un montaje hard, retrans=2 no significa abandonar la operación después de dos intentos. No prescribas valores menores para E/S aleatoria o pérdida de paquetes sin datos de la carga de trabajo que lo justifiquen. Configura las opciones en StorageClass/PV, no en los volúmenes del Pod; EFS no admite nconnect.

Reutiliza el sistema de archivos EFS y la configuración del punto de acceso que pertenecen al capítulo:

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

Si realizas una prueba de escritura autorizada, utiliza un directorio desechable verificado y un archivo único, no una ruta predecible como `/efs/testfile` que podría sobrescribir datos. El ejemplo GNU dd escribe 64 MiB y limpia únicamente su propio archivo/directorio. La lectura podría usar la caché del cliente, por lo que estos tiempos por sí solos no demuestran el rendimiento de EFS sin caché:

```bash
set -euo pipefail
: "${EFS_TEST_DIR:?Set an approved disposable directory on the verified EFS mount}"
test -d "$EFS_TEST_DIR" && test -w "$EFS_TEST_DIR"
EFS_TEST_PATH=$(mktemp -d "$EFS_TEST_DIR/efs-test.XXXXXX")
cleanup() { rm -f -- "$EFS_TEST_PATH/payload"; rmdir -- "$EFS_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$EFS_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$EFS_TEST_PATH/payload" of=/dev/null bs=1M
```

Durante esta revisión no se ejecutó ninguna prueba de rendimiento de EFS. Relaciona la latencia y concurrencia de cliente/aplicación con TotalIOBytes, DataReadIOBytes, DataWriteIOBytes y MetadataIOBytes de EFS, usando las estadísticas y los períodos de CloudWatch adecuados. Un contador de bytes no es una tasa de rendimiento hasta dividirlo por el intervalo de medición.

</details>

### 13. ¿En qué se diferencian el SLA de disponibilidad de EBS y el diseño de durabilidad?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Describen propiedades y condiciones diferentes**

El SLA de EBS es un acuerdo de disponibilidad y créditos de servicio, no un SLA universal de durabilidad de datos del 99.999%. El compromiso a nivel de región usa un umbral del 99.99% para despliegues concurrentes que cumplan los requisitos en varias zonas de disponibilidad; el compromiso de un solo volumen usa el 99.9%. Consulta las definiciones, exclusiones y condiciones para los créditos del acuerdo, en lugar de tratar ninguna cifra como una garantía incondicional.

| Característica de diseño publicada | Tipos de volumen |
|---|---|
| Durabilidad del 99.8–99.9%; AFR del 0.1–0.2% | gp3/gp2/io1 y tipos HDD |
| Durabilidad del 99.999%; AFR del 0.001% | io2 Block Express |

Este acuerdo no incluye un SLA de disponibilidad «cinco nueves» independiente para io2. La durabilidad de diseño y la AFR no equivalen a la probabilidad de que una aplicación concreta pierda todos sus datos; también importan la corrupción, el borrado, las copias de seguridad y la arquitectura de recuperación. La replicación de EBS ocurre dentro de una zona de disponibilidad, no replica automáticamente una base de datos entre zonas.

Usa copias coherentes con la aplicación cuando sea necesario, conserva puntos de recuperación independientes, prueba las restauraciones y supervisa el estado del volumen y de la aplicación. Para recuperarte de un fallo de zona, restaura instantáneas accesibles en una zona permitida; para recuperar registros borrados, usa un punto de recuperación adecuado o el mecanismo PITR de la base de datos. Una instantánea de bloques no permite recuperar cualquier marca temporal arbitraria.

Copiar instantáneas entre regiones es una operación aparte, con permisos de origen/destino/KMS y comprobaciones de finalización. El comando siguiente ilustra la creación; no se ejecutó como prueba de recuperación. Confirma primero quién controla el origen y cuál es el destino permitido, registra el SnapshotId devuelto y espera/comprueba que la copia termine antes de depender de ella:

```bash
set -euo pipefail
: "${SOURCE_REGION:?Set the source snapshot Region}"
: "${DESTINATION_REGION:?Set the recovery Region}"
: "${SOURCE_SNAPSHOT_ID:?Select an owned completed snapshot}"
: "${DESTINATION_KMS_KEY_ARN:?Set a usable customer managed key in the recovery Region}"
STATE=$(aws ec2 describe-snapshots --region "$SOURCE_REGION" \
  --snapshot-ids "$SOURCE_SNAPSHOT_ID" --query 'Snapshots[0].State' --output text)
test "$STATE" = completed || { echo "Snapshot is not completed"; exit 1; }
aws ec2 copy-snapshot --region "$DESTINATION_REGION" --source-region "$SOURCE_REGION" \
  --source-snapshot-id "$SOURCE_SNAPSHOT_ID" --encrypted --kms-key-id "$DESTINATION_KMS_KEY_ARN" \
  --description "Reviewed storage recovery copy" --output json
```

Una imagen de AWS CLI no incluye implícitamente kubectl ni concede permisos de Kubernetes/IAM. Usa un responsable de copias compatible, como Velero, Data Lifecycle Manager o AWS Backup, con el alcance adecuado, en vez de un CronJob sin configurar. Compara por separado el SLA de la clase/despliegue de almacenamiento y el diseño de durabilidad de cada servicio; una tabla universal de porcentajes entre servicios puede inducir a error.

</details>

## Preguntas prácticas

### 14. Diseña un flujo de almacenamiento y recuperación de base de datos con límites explícitos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Una arquitectura de referencia revisada, no una garantía automática de recuperación**

Diseña para una carga de PostgreSQL con demanda alta de E/S, copias programadas, recuperación verificada y expansión controlada. Lo siguiente es una **arquitectura de formación**, no un despliegue de producción probado. Reutiliza un espacio de nombres dedicado `database`, el Secret preparado `postgres-secret/password`, controladores de EBS/instantáneas compatibles y una instalación de Velero bajo tu responsabilidad. No lo apliques sobre recursos existentes sin consultar a su propietario.

#### Almacenamiento y base de datos

Se conserva la asignación original de 25,000 IOPS como ajuste io2 ilustrativo; para saber si basta hay que medir y tener en cuenta los límites de la instancia. Se usa la clave EBS configurada o predeterminada para el cifrado. Si eliges una clave administrada por el cliente, prepara el ARN y la política reales de la clave, así como las concesiones del controlador, en lugar de un kmsKeyId ficticio.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '25000'
```



```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  clusterIP: None
  selector:
    app: postgres
  ports:
  - name: postgres
    port: 5432
    targetPort: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: postgres
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: postgres
        image: postgres:14.24
        env:
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        - name: POSTGRES_PASSWORD_FILE
          value: /run/postgres-secret/password
        ports:
        - name: postgres
          containerPort: 5432
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          periodSeconds: 5
        resources:
          requests:
            cpu: '2'
            memory: 4Gi
          limits:
            cpu: '4'
            memory: 8Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        - name: socket
          mountPath: /var/run/postgresql
        - name: tmp
          mountPath: /tmp
        - name: password
          mountPath: /run/postgres-secret
          readOnly: true
      volumes:
      - name: socket
        emptyDir: {}
      - name: tmp
        emptyDir: {}
      - name: password
        secret:
          secretName: postgres-secret
          defaultMode: 288
          items:
          - key: password
            path: password
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        app: postgres
        storage-review: database-demo
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: postgres-io2
      resources:
        requests:
          storage: 100Gi
```

Esto usa el contrato de imagen verificado de PostgreSQL 14.24 de la Parte 1: UID/GID 999, archivo de contraseña montado, volúmenes de socket/tmp con escritura y un subdirectorio de PGDATA. La versión mayor 14 llega al fin del soporte el 12 de noviembre de 2026; esta versión de enseñanza conservada no es la predeterminada para un despliegue de producción nuevo. Elige y prueba una versión mayor compatible, junto con un plan de migración. Una réplica de StatefulSet no proporciona alta disponibilidad; pg_isready comprueba la conexión, no la integridad de los datos ni la recuperación.

#### Copias de seguridad y retención

Usa los requisitos previos del controlador de instantáneas del capítulo y `ebs-snapshot-class`. Para crear un punto de recuperación manual, detén la base de datos de forma coherente o usa un protocolo de copia compatible antes de crear la instantánea. La reclamación real de StatefulSet es **data-postgres-0**:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-review-snapshot
  namespace: database
  labels:
    storage-review: database-demo
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: data-postgres-0
```

Espera a readyToUse e inspecciona restoreSize, el contenido y el controlador antes de considerarla recuperable. El cifrado de la instantánea sigue la configuración de origen/clave; las claves de cifrado o tagSpecification no compatibles en VolumeSnapshotClass no la configuran. El controlador actual admite parámetros específicos para etiquetas de instantáneas; compruébalos en la versión de ese controlador en lugar de copiar parámetros de la clase de volúmenes.

Lo siguiente crea una programación diaria de Velero con un TTL de 30 días. Aplica la programación mediante el componente responsable de las copias, después de comprobar la selección de clase CSI y los hooks/protocolos de coherencia de la base de datos. El TTL de Velero puede eliminar sus instantáneas CSI incluso si la clase original era Retain. Genera alertas ante copias fallidas o ausentes y prueba restauraciones con regularidad; una programación por sí sola no demuestra que puedas recuperar los datos:

```bash
velero schedule create database-daily --schedule="0 1 * * *" \
  --include-namespaces=database --ttl=720h0m0s -o yaml > database-backup-schedule-review.yaml
```

#### Planificación de una expansión acotada

No amplíes a ciegas un 50% cada seis horas a partir de métricas antiguas. El planificador, solo de revisión, requiere una reclamación enlazada, una clase ampliable coincidente, ninguna ampliación pendiente, métricas recientes que identifiquen el mismo UID de PVC y valores válidos en bytes para el sistema de archivos. Admite cantidades comunes de Kubernetes en formato decimal/binario y rechaza entradas incompatibles. Cuando el uso alcanza el 80%, propone al menos 1.5× la capacidad solicitada, con un límite ilustrativo de 500Gi y precondiciones de UID/resourceVersion/tamaño actual. No aplica cambios a Kubernetes.

Captura `pvc.json` y `storageclass.json` actuales de los objetos exactos. `trusted-metrics.json` debe contener namespace, pvcName, pvcUID, observedAt (con zona horaria), usedBytes y capacityBytes del sistema de archivos realmente montado. El UID proporcionado por quien llama no demuestra por sí solo la procedencia de las métricas. Antes de que un operador o controlador aplique un cambio revisado, valida la correspondencia entre colector y montaje, la cuota, el costo y las restricciones del controlador.

```python
"""Generate a review-only plan from captured PVC, StorageClass and trusted metrics."""
import datetime,decimal,json,math,re,sys
D=decimal.Decimal
def quantity(s):
    match=re.fullmatch(r'([+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))([EPTGMK]i|[EPTGMk]|m|[eE][+-]?[0-9]+)?',s)
    if not match:raise ValueError('Unsupported/nonpositive quantity: '+s)
    value,suffix=D(match[1]),match[2] or ''
    if suffix.endswith('i'):value*=D(1024)**('KMGTPE'.index(suffix[0])+1)
    elif suffix in ['k','M','G','T','P','E']:value*=D(1000)**('kMGTPE'.index(suffix)+1)
    elif suffix=='m':value/=1000
    elif suffix:value*=D(10)**int(suffix[1:])
    if value<=0:raise ValueError('Capacity must be positive')
    return value
def plan(pvc,sc,metrics,now):
    meta,spec,status=pvc['metadata'],pvc['spec'],pvc['status']
    if (meta['namespace'],meta['name'])!=('database','data-postgres-0'):
        raise ValueError('Unexpected PVC')
    if status.get('phase')!='Bound' or not spec.get('volumeName'):
        raise ValueError('PVC is not Bound')
    if sc['metadata']['name']!=spec['storageClassName'] or sc.get('allowVolumeExpansion') is not True:
        raise ValueError('StorageClass mismatch or expansion disabled')
    if any(c.get('status')=='True' and c.get('type') in ['Resizing','FileSystemResizePending'] for c in status.get('conditions',[])):
        raise ValueError('Resize is pending')
    if status.get('allocatedResourceStatuses',{}).get('storage'):
        raise ValueError('Storage allocation is pending')
    requested=quantity(spec['resources']['requests']['storage'])
    if requested!=quantity(status['capacity']['storage']):
        raise ValueError('Request and capacity differ; inspect before another resize')
    if (metrics['namespace'],metrics['pvcName'],metrics['pvcUID'])!=(meta['namespace'],meta['name'],meta['uid']):
        raise ValueError('Metrics identify a different PVC')
    seen=datetime.datetime.fromisoformat(metrics['observedAt'].replace('Z','+00:00'))
    if seen.tzinfo is None or not 0<=(now-seen).total_seconds()<=300:
        raise ValueError('Metrics are stale or future-dated')
    used,capacity=D(str(metrics['usedBytes'])),D(str(metrics['capacityBytes']))
    if not used.is_finite() or not capacity.is_finite() or not 0<=used<=capacity<=requested or capacity<=0:
        raise ValueError('Invalid filesystem metrics')
    if used/capacity<D('0.8'):return {'reviewOnly':True,'action':'none','reason':'Below 80%'}
    target=math.ceil(max(requested*D('1.5'),used/D('0.7'))/D(1024**3))
    if target>500:return {'reviewOnly':True,'action':'manual-review','reason':'Illustrative 500Gi cap exceeded'}
    return {'reviewOnly':True,'action':'propose-resize','target':str(target)+'Gi','patch':[
      {'op':'test','path':'/metadata/uid','value':meta['uid']},
      {'op':'test','path':'/metadata/resourceVersion','value':meta['resourceVersion']},
      {'op':'test','path':'/spec/resources/requests/storage','value':spec['resources']['requests']['storage']},
      {'op':'replace','path':'/spec/resources/requests/storage','value':str(target)+'Gi'}]}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: resize-plan.py pvc.json storageclass.json trusted-metrics.json')
    inputs=[]
    for name in sys.argv[1:]:
        with open(name) as f:inputs.append(json.load(f))
    print(json.dumps(plan(*inputs,datetime.datetime.now(datetime.timezone.utc)),indent=2))
```

Si cambia el recurso, vuelve a generar el plan; no elimines las precondiciones fallidas ni registres el éxito después de un cambio fallido. Tras una ampliación aprobada, inspecciona las condiciones del PVC y la capacidad real del sistema de archivos. Mantén alineado el tamaño futuro de las reclamaciones en la plantilla de StatefulSet mediante un procedimiento de gestión admitido; no modifiques la capacidad del PV para simular que la ampliación terminó.

#### Candidato de recuperación

No configures un Job con reintentos para que reduzca la escala y elimine la reclamación activa como primer paso de restauración. Usa un candidato independiente cuyo tamaño sea al menos restoreSize; el ejemplo de 100Gi supone que este punto de recuperación no es mayor. Si la reclamación original se amplió, ajusta el candidato en consecuencia:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-restore-candidate
  namespace: database
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: postgres-io2
  resources:
    requests:
      storage: 100Gi
  dataSource:
    name: postgres-review-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

Programa un consumidor PostgreSQL aislado y compatible, con las credenciales y la versión necesarias; espera a que se enlace y recupere, y verifica las consultas y los datos de la aplicación antes de realizar una transición controlada. Conserva los datos originales y un plan para revertir la transición. Establecer una nueva variable POSTGRES_PASSWORD no restablece las credenciales en una base de datos restaurada existente.

#### Supervisión

El puerto PostgreSQL 5432 habla el protocolo de base de datos, no HTTP de Prometheus. Prepara un despliegue revisado de postgres-exporter con la etiqueta `app: postgres-exporter`, un puerto con nombre `metrics` en 9187 y credenciales de base de datos con el alcance adecuado. Este Service y ServiceMonitor seleccionan ese exporter; no lo instalan. Comprueba que Prometheus seleccione este ServiceMonitor y su espacio de nombres, y que NetworkPolicy/TLS/autenticación coincidan con el despliegue:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    monitoring: postgres-exporter
spec:
  selector:
    app: postgres-exporter
  ports:
  - name: metrics
    port: 9187
    targetPort: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-exporter
  namespace: database
spec:
  selector:
    matchLabels:
      monitoring: postgres-exporter
  namespaceSelector:
    matchNames:
    - database
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

Genera alertas sobre la antigüedad o el fallo de las copias, el margen del sistema de archivos, los errores de ampliación del PVC y los límites medidos de latencia y cola de E/S. Esta arquitectura de referencia requiere pruebas de alta disponibilidad, restauración, rotación de credenciales y carga específicas para la aplicación antes de poder afirmar que está lista para producción.

</details>

### 15. ¿Cómo investigarías un clon nuevo lento y una vista antigua de un conjunto de datos S3?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Separa la inicialización, la caché y la coherencia de la aplicación**

Para el clon de EBS, verifica la versión real del controlador, la zona y el tamaño de origen, el estado de la copia, el avance de la inicialización y el rendimiento aprovisionado y de la instancia. Una copia nativa recién disponible quizá todavía se esté inicializando en segundo plano. No escribas ceros, no la trates como un volumen vacío ni supongas que se aplican aceleradores de inicialización exclusivos de instantáneas.

Para Mountpoint, inspecciona la versión instalada de CSI/binario, las opciones del PV, la identidad del Pod, el bucket/prefijo y el TTL de caché, incluidas las entradas negativas. La consistencia sólida de S3 no evita una caché configurada en el cliente. Comprueba si la operación de la aplicación es compatible con ese tipo de bucket; las suposiciones sobre anexado y cambio de nombre son distintas en buckets de uso general y de directorio.

Usa el marcador de clonación aislado del capítulo y un conjunto de datos S3 con versiones para probar hipótesis. Conserva los valores históricos de benchmarks como contexto no verificado; si luego se autorizan pruebas, registra las mediciones junto con el entorno real. Ni una prueba de lectura ni la creación de una instantánea demuestran coherencia con la aplicación de base de datos.

</details>

## Referencias

- [Capítulo y ejemplos alineados con la fuente](../../eks/04-eks-storage-part2.md)
- [Retención de PVC de StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Tipos de volumen de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- [SLA de EBS](https://aws.amazon.com/ebs/sla/)
- [Copia nativa de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
- [Opciones de montaje de EFS](https://docs.aws.amazon.com/efs/latest/ug/mounting-fs-nfs-mount-settings.html)
- [Configuración de Mountpoint CSI](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
- [Ciclo de vida de CSI en Velero](https://velero.io/docs/v1.18/csi/)
- [Referencia de la API de Prometheus Operator](https://prometheus-operator.dev/docs/api-reference/api/)
- [Política de versiones de PostgreSQL](https://www.postgresql.org/support/versioning/)
