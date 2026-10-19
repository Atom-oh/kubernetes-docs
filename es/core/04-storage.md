# Almacenamiento

> **Versiones compatibles**: Kubernetes 1.35, 1.36, 1.37
> **Última actualización**: 16 de octubre de 2026

El almacenamiento en Kubernetes permite guardar y gestionar los datos de las aplicaciones en contenedores. En este capítulo examinaremos en detalle los volúmenes, los volúmenes persistentes (Persistent Volumes), las solicitudes de volúmenes persistentes (Persistent Volume Claims) y las clases de almacenamiento (Storage Classes).

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias
- kubectl, con una diferencia de como máximo una versión menor respecto de la del servidor de API
- Un clúster de Kubernetes operativo (EKS, minikube, kind, etc.)
- Un provisionador de almacenamiento (controlador EBS CSI para EKS)

El primer ejemplo requiere un StorageClass predeterminado; de lo contrario, establece `storageClassName` en una clase instalada. Los ejemplos de EBS para EKS que aparecen a continuación usan el controlador EBS CSI estándar en nodos EC2 con permisos de IAM; Auto Mode usa `ebs.csi.eks.amazonaws.com`. EBS no se puede montar en Fargate ni en Hybrid Nodes. Considera los manifiestos posteriores como ejemplos independientes con sus requisitos previos indicados.

### Configuración del ejemplo de almacenamiento

```bash
# Create namespace
kubectl create namespace storage-demo

# Create a simple PVC and Pod
kubectl -n storage-demo apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: data-pod
spec:
  containers:
  - name: data-container
    image: busybox
    command: ["sh", "-c", "while true; do echo $(date) >> /data/output.txt; sleep 5; done"]
    volumeMounts:
    - name: data-volume
      mountPath: /data
  volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: data-pvc
EOF

# Check storage resources
kubectl -n storage-demo get pvc,pod
```

## Tabla de contenido

1. [Volúmenes](#volumes)
2. [Volúmenes persistentes](#persistent-volumes)
3. [Solicitudes de volúmenes persistentes](#persistent-volume-claims)
4. [Clases de almacenamiento](#storage-classes)
5. [Aprovisionamiento dinámico](#dynamic-provisioning)
6. [Instantáneas de volúmenes](#volume-snapshots)
7. [Ampliación de volúmenes](#volume-expansion)
8. [Volúmenes proyectados](#projected-volumes)
9. [Volúmenes efímeros genéricos](#generic-ephemeral-volumes)
10. [Modo de volumen de bloques](#block-volume-mode)
11. [Clonación de volúmenes](#volume-cloning)
12. [ResourceQuota de almacenamiento](#storage-resourcequota)
13. [Opciones de almacenamiento en EKS](#storage-options-in-eks)

## Volúmenes {#volumes}

> **Concepto clave**: Los volúmenes de Kubernetes son directorios donde los contenedores de un Pod pueden almacenar y compartir datos, que se conservan aunque se reinicien los contenedores.

Los volúmenes de Kubernetes son directorios donde los contenedores de un Pod pueden almacenar y compartir datos. El montaje existe durante la vida del Pod, mientras que la conservación de los datos en el almacenamiento subyacente depende del tipo de volumen. Los datos de emptyDir se eliminan junto con el Pod; el almacenamiento persistente puede conservarlos después.

### Arquitectura de almacenamiento de Kubernetes

![Los Pods solicitan almacenamiento mediante un PersistentVolumeClaim, que se enlaza a un PersistentVolume aprovisionado por un StorageClass; el CSI Driver conecta ese volumen al almacenamiento de backend subyacente en la nube, local o NFS.](../.gitbook/assets/en-core-04-storage-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-0.html)

### Por qué se necesitan los volúmenes

1. **Persistencia de datos tras reiniciar un contenedor**: Cuando se reinicia un contenedor, su sistema de archivos se restablece, pero el uso de volúmenes permite que los datos persistan.
2. **Intercambio de datos entre contenedores**: Varios contenedores del mismo Pod pueden compartir datos mediante volúmenes.

### Comparación de los principales tipos de volúmenes

| Tipo de volumen | Ciclo de vida | Persistencia de datos | Caso de uso | Características |
|------------|----------|-----------------|----------|----------|
| **emptyDir** | Pod | Temporal | Datos temporales, caché, puntos de control | Los datos se eliminan cuando se elimina el Pod |
| **hostPath** | Nodo | A nivel de nodo | Acceso al sistema de archivos del nodo, supervisión | Riesgo de seguridad: úsalo con precaución |
| **configMap** | Configuración | Datos de configuración | Configuración de aplicaciones | Monta datos de configuración como volumen |
| **secret** | Configuración | Datos sensibles | Certificados, contraseñas | Monta datos sensibles como volumen |
| **persistentVolumeClaim** | Clúster | Permanente | Bases de datos, almacenamiento de archivos | Los datos persisten tras reiniciar el Pod o reasignarlo a otro nodo |

### emptyDir

Un volumen `emptyDir` se crea cuando se asigna un Pod a un nodo y persiste mientras el Pod se ejecuta en ese nodo. Cuando se elimina el Pod del nodo, los datos de `emptyDir` se eliminan de forma permanente.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - image: nginx
    name: test-container
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}
```

### hostPath

Un volumen `hostPath` monta un archivo o directorio del sistema de archivos del nodo en el Pod. Esto es útil para los Pods que necesitan acceder al sistema de archivos del nodo, pero debe usarse con precaución debido a los riesgos de seguridad.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-hostpath
spec:
  containers:
  - image: nginx
    name: test-container
    volumeMounts:
    - mountPath: /test-pd
      name: test-volume
  volumes:
  - name: test-volume
    hostPath:
      path: /data
      type: Directory  # DirectoryOrCreate, Directory, FileOrCreate, File, Socket, CharDevice, BlockDevice
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - image: nginx
    name: test-container
    volumeMounts:
    - mountPath: /test-pd
      name: test-volume
  volumes:
  - name: test-volume
    hostPath:
      path: /data
      type: Directory
```

#### configMap

Un volumen `configMap` monta datos de ConfigMap en un Pod. Los ConfigMaps se usan para almacenar datos de configuración en pares clave-valor.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: config-vol
      mountPath: /etc/config
  volumes:
  - name: config-vol
    configMap:
      name: log-config
      items:
      - key: log_level
        path: log_level
```

#### secret

Un volumen `secret` monta datos de Secret en un Pod. Los Secrets se usan para almacenar información sensible, como contraseñas, tokens y claves.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: secret-vol
      mountPath: /etc/secret
      readOnly: true
  volumes:
  - name: secret-vol
    secret:
      secretName: mysecret
      items:
      - key: username
        path: my-username
```

#### nfs

Un volumen `nfs` monta un recurso compartido NFS (Network File System) existente en un Pod.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nfs-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: nfs-vol
      mountPath: /mnt/nfs
  volumes:
  - name: nfs-vol
    nfs:
      server: nfs-server.example.com
      path: /share
```

#### persistentVolumeClaim

Un volumen `persistentVolumeClaim` monta un PersistentVolumeClaim en un Pod. Este es uno de los tipos de volúmenes más utilizados.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pvc-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: pvc-vol
      mountPath: /mnt/pvc
  volumes:
  - name: pvc-vol
    persistentVolumeClaim:
      claimName: my-pvc
```

#### CSI (Container Storage Interface)

Los volúmenes CSI proporcionan una interfaz estándar entre Kubernetes y los sistemas de almacenamiento externos. Con CSI, los proveedores de almacenamiento pueden desarrollar sus propios controladores de almacenamiento sin modificar el código de Kubernetes.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: csi-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: csi-vol
      mountPath: /mnt/csi
  volumes:
  - name: csi-vol
    csi:
      driver: csi-driver.example.com
      volumeAttributes:
        foo: bar
      nodePublishSecretRef:
        name: csi-secret
```

## Volúmenes persistentes {#persistent-volumes}

Un Persistent Volume (PV) es almacenamiento del clúster aprovisionado por un administrador o aprovisionado dinámicamente mediante un Storage Class. Los PV tienen un ciclo de vida independiente de los Pods y se conservan incluso cuando se eliminan los Pods.

![Un administrador del clúster crea un PersistentVolume conectado al almacenamiento físico; la solicitud PersistentVolumeClaim de un usuario se enlaza a ese volumen y un Pod utiliza la solicitud para acceder al volumen mediante aprovisionamiento estático.](../.gitbook/assets/en-core-04-storage-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-1.html)

### Creación de PV

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv0001
  labels:
    release: stable
    environment: dev
spec:
  capacity:
    storage: 10Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: slow
  mountOptions:
    - hard
    - nfsvers=4.1
  nfs:
    path: /tmp
    server: 172.17.0.2
```

### Modos de acceso de PV

Los PV admiten los siguientes modos de acceso:

- **ReadWriteOnce (RWO)**: Un solo nodo puede montar el volumen con acceso de lectura y escritura.
- **ReadOnlyMany (ROX)**: Varios nodos pueden montar el volumen con acceso de solo lectura.
- **ReadWriteMany (RWX)**: Varios nodos pueden montar el volumen con acceso de lectura y escritura.
- **ReadWriteOncePod (RWOP)**: Un solo Pod puede montar el volumen con acceso de lectura y escritura (solo CSI; estable desde v1.29).

RWO restringe el montaje con escritura a un solo **nodo**, no a un solo Pod: varios Pods de ese nodo pueden compartir el volumen. RWOP exige un único Pod con un controlador CSI compatible. Los modos de acceso no sustituyen a los permisos del sistema de archivos.

### Políticas de recuperación de PV

Los PV pueden tener las siguientes políticas de recuperación:

- **Retain**: Cuando se elimina un PVC, se conservan el PV y los datos. El administrador debe limpiarlos manualmente.
- **Delete**: Cuando se elimina un PVC, el PV y los recursos de almacenamiento externos se eliminan automáticamente.
- **Recycle**: Cuando se elimina un PVC, se eliminan los datos del PV y este vuelve a estar disponible (obsoleto).

### Estado de PV

Los PV pueden tener los siguientes estados:

- **Available**: Recurso disponible que aún no está enlazado a una solicitud de almacenamiento.
- **Bound**: Enlazado a una solicitud.
- **Released**: La solicitud se ha eliminado, pero el clúster aún no ha recuperado el recurso.
- **Failed**: Ha fallado la recuperación automática.

## Solicitudes de volúmenes persistentes {#persistent-volume-claims}

Una solicitud de volumen persistente (Persistent Volume Claim, PVC) es una petición de almacenamiento de un usuario. Los PVC y los PV se complementan: el usuario solicita almacenamiento mediante un PVC y el administrador lo proporciona mediante un PV.

### Creación de PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: myclaim
spec:
  accessModes:
    - ReadWriteOnce
  volumeMode: Filesystem
  resources:
    requests:
      storage: 8Gi
  storageClassName: slow
  selector:
    matchLabels:
      release: "stable"
    matchExpressions:
      - {key: environment, operator: In, values: [dev]}
```

### Enlace de PVC y PV

Cuando se crea un PVC, Kubernetes busca y enlaza un PV que cumpla sus requisitos de capacidad, modos de acceso, clase de almacenamiento, selector y demás propiedades. Si no encuentra uno, un StorageClass adecuado puede aprovisionarlo de forma dinámica. Un PVC con un selector no vacío, como el anterior, no admite aprovisionamiento dinámico y permanece en estado Pending si no existe un PV estático que cumpla los requisitos. WaitForFirstConsumer también retrasa deliberadamente el enlace hasta la planificación del Pod.

### Uso de PVC

Los PVC se pueden usar como volúmenes en Pods:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: myclaim
```

## Clases de almacenamiento {#storage-classes}

Los Storage Classes describen las «clases» de almacenamiento que ofrecen los administradores. Se usan para aprovisionar PV dinámicamente.

![La solicitud PersistentVolumeClaim de un usuario hace referencia a un StorageClass, que aprovisiona dinámicamente un PersistentVolume. La solicitud se enlaza a ese volumen y un Pod lo utiliza para acceder al almacenamiento físico.](../.gitbook/assets/en-core-04-storage-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-2.html)

### Creación de Storage Class

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  csi.storage.k8s.io/fstype: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

Este ejemplo crea una clase de almacenamiento que aprovisiona volúmenes AWS EBS gp3.

### Provisionadores

Los Storage Classes especifican un provisionador que se usa para aprovisionar volúmenes. Entre los provisionadores CSI actuales se incluyen:

- `ebs.csi.aws.com`: AWS EBS
- `efs.csi.aws.com`: AWS EFS
- `fsx.csi.aws.com`: FSx for Lustre
- `pd.csi.storage.gke.io`: Google Persistent Disk
- `disk.csi.azure.com` / `file.csi.azure.com`: Azure Disk/File
- `nfs.csi.k8s.io`: controlador NFS CSI (requiere un servidor NFS existente)

Los complementos de nube heredados integrados en el árbol de código se han eliminado o migrado. Instala el controlador CSI apropiado; Kubernetes no tiene un provisionador dinámico `kubernetes.io/nfs` integrado.

### Modos de enlace de volúmenes

Los Storage Classes admiten los siguientes modos de enlace de volúmenes:

- **Immediate**: Es el modo predeterminado; los volúmenes se aprovisionan inmediatamente cuando se crea el PVC.
- **WaitForFirstConsumer**: Retrasa el aprovisionamiento del volumen hasta que un Pod intenta usar el PVC. Esto resulta útil para garantizar que los volúmenes se aprovisionen en la misma zona que los Pods.

### Storage Class predeterminado

Se puede establecer un Storage Class predeterminado para el clúster. Si no se especifica una clase de almacenamiento en un PVC, se usa la clase predeterminada.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

## Aprovisionamiento dinámico {#dynamic-provisioning}

El aprovisionamiento dinámico es una función que crea automáticamente PV cuando se crean PVC. Esto permite que los usuarios soliciten almacenamiento cuando lo necesitan, sin que los administradores tengan que crear PV de antemano.

### Ejemplo de aprovisionamiento dinámico

1. Crea un Storage Class:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  encrypted: "true"
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

2. Crea un PVC:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: myclaim
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast
```

3. Usa el PVC en un Pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: myclaim
```

## Instantáneas de volúmenes {#volume-snapshots}

Kubernetes admite instantáneas de volúmenes para crear copias puntuales de PV. Esto resulta útil en escenarios de copia de seguridad y restauración.

![Una Volume Snapshot hace referencia a una Volume Snapshot Class y captura un PersistentVolumeClaim existente; un nuevo PVC que usa esa instantánea como origen de datos se enlaza a un nuevo PV restaurado a partir de ella.](../.gitbook/assets/en-core-04-storage-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-3.html)

Instala las CRD de instantáneas, el controlador de instantáneas y un controlador CSI que admita esta función. El ejemplo siguiente usa EBS; el PVC de origen y el StorageClass de restauración deben utilizar ese controlador. Espera a que el estado indique `readyToUse: true` y solicita una capacidad igual o superior al tamaño de restauración de la instantánea. Una instantánea de almacenamiento por sí sola no garantiza la coherencia de la base de datos; pausa las escrituras o utiliza copias de seguridad que tengan en cuenta el funcionamiento de la base de datos.

### Clase de instantáneas de volumen

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapclass
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

### Crear una instantánea de volumen

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: new-snapshot
spec:
  volumeSnapshotClassName: ebs-snapclass
  source:
    persistentVolumeClaimName: myclaim
```

### Crear un PVC a partir de una instantánea

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restore-pvc
spec:
  storageClassName: standard
  dataSource:
    name: new-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

## Ampliación de volúmenes {#volume-expansion}

Kubernetes permite ampliar el tamaño de los PVC. Para ello, se debe establecer `allowVolumeExpansion: true` en el Storage Class.

![La solicitud de un usuario para ampliar un PersistentVolumeClaim pasa por el StorageClass, que comprueba si la ampliación de volúmenes está habilitada antes de que el PersistentVolume aumente el tamaño del disco subyacente y del sistema de archivos del Pod.](../.gitbook/assets/en-core-04-storage-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-4.html)

### Ampliación de PVC

Para un PVC existente de 100Gi en un StorageClass de EBS compatible con la ampliación, cambia únicamente el tamaño solicitado:

```bash
kubectl patch pvc myclaim --type merge -p '{"spec":{"resources":{"requests":{"storage":"120Gi"}}}}'
```

Usa el namespace del PVC y el StorageClass existente. El controlador y el sistema de archivos deben admitir la ampliación; no se admite la reducción. No cambies la clase del PVC enlazado ni edites directamente la capacidad del PV para simular un cambio de tamaño.

## Volúmenes proyectados {#projected-volumes}

Los volúmenes proyectados permiten combinar varias fuentes en un único montaje. Esto permite exponer conjuntamente datos de secrets, configMaps, downwardAPI y serviceAccountToken en un solo directorio.

### Fuentes compatibles

- **secret**: Montar datos de secret
- **configMap**: Montar datos de configuración
- **downwardAPI**: Exponer metadatos del Pod y del contenedor
- **serviceAccountToken**: Montar tokens de cuenta de servicio con una caducidad configurable

### Ejemplo de volumen proyectado

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: projected-volume-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "ls -la /etc/projected && sleep 3600"]
    volumeMounts:
    - name: all-in-one
      mountPath: /etc/projected
      readOnly: true
  volumes:
  - name: all-in-one
    projected:
      sources:
      - secret:
          name: db-credentials
          items:
          - key: username
            path: db/username
          - key: password
            path: db/password
      - configMap:
          name: app-config
          items:
          - key: config.yaml
            path: config/app.yaml
      - downwardAPI:
          items:
          - path: labels
            fieldRef:
              fieldPath: metadata.labels
          - path: cpu-request
            resourceFieldRef:
              containerName: app
              resource: requests.cpu
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600
          audience: api
```

Esta configuración crea un solo volumen en `/etc/projected` que contiene:
- `/etc/projected/db/username` y `/etc/projected/db/password` del secret
- `/etc/projected/config/app.yaml` del configMap
- `/etc/projected/labels` y `/etc/projected/cpu-request` de downwardAPI
- `/etc/projected/token` con un token de cuenta de servicio que se renueva automáticamente

### Proyección de tokens de cuenta de servicio

La proyección de tokens de cuenta de servicio proporciona tokens con una duración y una audiencia limitadas:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: token-projected-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: api-token
          expirationSeconds: 7200  # 2 hours
          audience: my-api-service
```

Los tokens proyectados se renuevan; las aplicaciones deben volver a leer el archivo para obtener el token actualizado. Si se especifica `audience`, su valor debe coincidir con el verificador previsto; no garantiza por sí solo que el token sea válido para acceder a la API de Kubernetes.

## Volúmenes efímeros genéricos {#generic-ephemeral-volumes}

Los volúmenes efímeros genéricos proporcionan almacenamiento similar al de un PVC, vinculado al ciclo de vida del Pod. A diferencia de emptyDir, permiten utilizar las funciones de los PVC y las clases de almacenamiento, incluido el aprovisionamiento dinámico.

### Diferencias con emptyDir

| Característica | emptyDir | Volumen efímero genérico |
|---------|----------|--------------------------|
| **Backend de almacenamiento** | Almacenamiento local del nodo o memoria | Cualquier controlador CSI |
| **Aprovisionamiento** | Automático, sencillo | Usa StorageClass, aprovisionamiento dinámico |
| **Límites de tamaño** | sizeLimit (flexible) | Gestión completa de la capacidad del PVC |
| **Instantáneas** | No compatible | Compatible (si el controlador CSI lo admite) |
| **Funciones de almacenamiento** | Básicas | Funciones CSI completas (cifrado, IOPS, etc.) |
| **Persistencia** | Se pierde cuando se elimina el Pod | El PVC se elimina con el Pod; el backend sigue la política de recuperación |

### Ejemplo de volumen efímero genérico

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ephemeral-volume-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "dd if=/dev/zero of=/scratch/data bs=1M count=100 && sleep 3600"]
    volumeMounts:
    - name: scratch
      mountPath: /scratch
  volumes:
  - name: scratch
    ephemeral:
      volumeClaimTemplate:
        metadata:
          labels:
            type: scratch-storage
        spec:
          accessModes:
          - ReadWriteOnce
          storageClassName: fast-ssd
          resources:
            requests:
              storage: 10Gi
```

### Casos de uso

1. **Canalizaciones de CI/CD**: Artefactos de compilación temporales con capacidad de almacenamiento garantizada
2. **Procesamiento de datos**: Espacio temporal con requisitos de rendimiento específicos
3. **Pruebas**: Bases de datos o cachés temporales con funciones CSI
4. **Aprendizaje automático**: Puntos de control temporales de modelos con almacenamiento de alto rendimiento

### Deployment con volúmenes efímeros genéricos

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-training
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-training
  template:
    metadata:
      labels:
        app: ml-training
    spec:
      containers:
      - name: trainer
        image: ml-trainer:latest
        volumeMounts:
        - name: checkpoint-storage
          mountPath: /checkpoints
      volumes:
      - name: checkpoint-storage
        ephemeral:
          volumeClaimTemplate:
            spec:
              accessModes:
              - ReadWriteOnce
              storageClassName: high-iops
              resources:
                requests:
                  storage: 50Gi
```

Los PVC efímeros genéricos pertenecen a su Pod y se eliminan junto con él mediante la recolección de basura. La eliminación de los datos subyacentes depende de la política de recuperación del PV: `Retain` conserva el almacenamiento hasta que se limpie manualmente. Exporta a almacenamiento duradero los puntos de control que deban sobrevivir a la pérdida del Pod.

## Modo de volumen de bloques {#block-volume-mode}

Kubernetes admite volúmenes de bloques sin sistema de archivos, además de los volúmenes que lo utilizan. El almacenamiento se presenta como un dispositivo de bloques directamente accesible, lo que resulta útil para aplicaciones que gestionan su propia organización de datos.

### Modo de sistema de archivos frente a modo de bloques

| Aspecto | Sistema de archivos (predeterminado) | Bloque |
|--------|---------------------|-------|
| **volumeMode** | `Filesystem` | `Block` |
| **Tipo de montaje** | Montado como directorio | Expuesto como archivo de dispositivo |
| **Sistema de archivos** | ext4, xfs, etc. | Ninguno (sin formato) |
| **Acceso en el Pod** | `/mnt/data/` | `/dev/xvda` |
| **Caso de uso** | Aplicaciones generales | Bases de datos, aplicaciones especializadas |

### PV y PVC de volumen de bloques

```yaml
# PersistentVolume with Block mode
apiVersion: v1
kind: PersistentVolume
metadata:
  name: block-pv
spec:
  capacity:
    storage: 100Gi
  volumeMode: Block
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: block-storage
  csi:
    driver: ebs.csi.aws.com
    volumeHandle: vol-0123456789abcdef0
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values: [us-west-2a]
---
# PersistentVolumeClaim for Block volume
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: block-pvc
spec:
  volumeMode: Block
  accessModes:
  - ReadWriteOnce
  storageClassName: block-storage
  resources:
    requests:
      storage: 100Gi
```

### Uso de volúmenes de bloques en Pods

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: block-volume-pod
spec:
  containers:
  - name: database
    image: custom-database:latest
    volumeDevices:
    - name: data
      devicePath: /dev/xvda
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: block-pvc
```

Nota: Los volúmenes de bloques usan `volumeDevices` y `devicePath` en lugar de `volumeMounts` y `mountPath`.

### Casos de uso de volúmenes de bloques

1. **Motores de almacenamiento especializados**: Solo software diseñado expresamente para dispositivos de bloques sin sistema de archivos; los directorios de datos habituales de MySQL/PostgreSQL necesitan un sistema de archivos.
2. **Sistemas de archivos personalizados**: Aplicaciones que utilizan sistemas de archivos especializados como ZFS o LVM.
3. **Almacenamiento de alto rendimiento**: Aplicaciones que necesitan E/S directa sin la sobrecarga de un sistema de archivos.
4. **Virtualización del almacenamiento**: Soluciones de almacenamiento definido por software.

Reemplaza el ID del volumen EBS estático y la zona de nodeAffinity por el volumen real y su zona de disponibilidad. La imagen `custom-database` es un marcador de posición para software compatible con dispositivos de bloques sin formato.

## Clonación de volúmenes {#volume-cloning}

La clonación de volúmenes crea un nuevo PVC con el contenido de un PVC existente. Esto resulta útil para crear entornos de prueba, duplicar datos o migrar cargas de trabajo.

### Requisitos previos

EBS CSI admite la clonación de PVC a partir de v1.51.0 ([ejemplo con versión especificada](https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/v1.67.0/examples/kubernetes/clone/README.md)); verifica la versión del controlador instalado y los permisos de IAM. FSx for Lustre CSI no anuncia `CLONE_VOLUME`; tampoco deduzcas que EFS lo admite. `kubectl get csidriver` no expone las capacidades de RPC de CSI.

- El controlador CSI debe admitir la clonación de volúmenes.
- Los PVC de origen y destino deben estar en el mismo namespace.
- Se permiten clases de almacenamiento diferentes si el controlador lo admite; el PVC de origen debe estar enlazado y disponible, sin estar en uso.
- El origen y el destino deben tener el mismo volumeMode.

### Ejemplo de clonación de PVC

```yaml
# Source PVC (existing)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: source-pvc
  namespace: production
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 100Gi
---
# Clone PVC using dataSource
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cloned-pvc
  namespace: production
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 100Gi  # Must be >= source size
  dataSource:
    kind: PersistentVolumeClaim
    name: source-pvc
```

### Clonación frente a instantáneas

| Característica | Clonación de volúmenes | Instantáneas de volúmenes |
|---------|---------------|------------------|
| **Resultado** | Nuevo PVC con datos | Objeto de instantánea |
| **Caso de uso** | Duplicar un volumen de origen disponible | Copia de seguridad de un momento determinado |
| **Rendimiento** | Depende del controlador/backend | Depende del controlador/backend |
| **Entre namespaces** | No | No |
| **Sobrecarga de almacenamiento** | Depende del backend | Depende del backend |

### Clonación para pruebas

Primero, crea un PVC `staging-source-pvc` enlazado y con datos coherentes en `staging`. Un `dataSource` no puede hacer referencia directamente a un PVC de `production`. El clon debe contener ya un directorio de datos de PostgreSQL compatible; el ejemplo no muestra cómo inicializarlo.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-db-clone
  namespace: staging
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 100Gi
  dataSource:
    kind: PersistentVolumeClaim
    name: staging-source-pvc
---
apiVersion: v1
kind: Pod
metadata:
  name: test-database
  namespace: staging
spec:
  containers:
  - name: postgres
    image: postgres:15
    volumeMounts:
    - name: data
      mountPath: /var/lib/postgresql/data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: test-db-clone
```

## ResourceQuota de almacenamiento {#storage-resourcequota}

ResourceQuota puede limitar el consumo de almacenamiento dentro de un namespace, incluido el número de PVC y la capacidad total de almacenamiento.

### Campos de cuota relacionados con el almacenamiento

| Campo | Descripción |
|-------|-------------|
| **persistentvolumeclaims** | Número total de PVC permitidos |
| **requests.storage** | Capacidad total de almacenamiento de todos los PVC |
| **\<storage-class\>.storageclass.storage.k8s.io/requests.storage** | Capacidad de almacenamiento para un StorageClass específico |
| **\<storage-class\>.storageclass.storage.k8s.io/persistentvolumeclaims** | Número de PVC para un StorageClass específico |

### Ejemplo de ResourceQuota

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: storage-quota
  namespace: team-a
spec:
  hard:
    # Total limits
    persistentvolumeclaims: "10"
    requests.storage: "500Gi"

    # Per-StorageClass limits
    ebs-sc.storageclass.storage.k8s.io/requests.storage: "200Gi"
    ebs-sc.storageclass.storage.k8s.io/persistentvolumeclaims: "5"

    efs-sc.storageclass.storage.k8s.io/requests.storage: "300Gi"
    efs-sc.storageclass.storage.k8s.io/persistentvolumeclaims: "5"
```

### Comprobación del estado de ResourceQuota

```bash
# View quota status
kubectl get resourcequota storage-quota -n team-a -o yaml

# Example output
status:
  hard:
    persistentvolumeclaims: "10"
    requests.storage: "500Gi"
  used:
    persistentvolumeclaims: "3"
    requests.storage: "150Gi"
```

### LimitRange para el almacenamiento

LimitRange permite exigir un tamaño mínimo y máximo en las solicitudes de almacenamiento de los PVC; no asigna un tamaño predeterminado cuando falta la solicitud:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: storage-limits
  namespace: team-a
spec:
  limits:
  - type: PersistentVolumeClaim
    min:
      storage: 1Gi
    max:
      storage: 100Gi
```

Esto garantiza que:
- El tamaño mínimo del PVC sea 1Gi
- El tamaño máximo del PVC sea 100Gi
- Cada PVC solicite almacenamiento explícitamente; LimitRange no establece valores predeterminados para PVC

## Opciones de almacenamiento en EKS {#storage-options-in-eks}

Amazon EKS ofrece varias opciones de almacenamiento. Cada opción tiene diferentes casos de uso y características de rendimiento, por lo que es importante elegir el almacenamiento adecuado según los requisitos de tu aplicación.

![Los Pods de Amazon EKS consumen almacenamiento de bloques de EBS, almacenamiento de archivos compartido de EFS y almacenamiento paralelo de alto rendimiento de FSx for Lustre; cada uno se aprovisiona mediante su propio controlador CSI, StorageClass y PersistentVolume.](../.gitbook/assets/en-core-04-storage-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-5.html)

### Amazon EBS

Amazon EBS (Elastic Block Store) proporciona volúmenes de almacenamiento de bloques que se pueden conectar a instancias EC2. En EKS, puedes usar el controlador EBS CSI para montar volúmenes EBS en Pods de Kubernetes.

#### Instalación del controlador EBS CSI

Sigue la [guía de instalación del controlador de EKS](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), selecciona una versión compatible del complemento/controlador y configura su rol de IAM y los requisitos previos de los nodos antes de crear PVC. Un StorageClass por sí solo no instala el controlador.

#### Storage Class de EBS

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  csi.storage.k8s.io/fstype: ext4
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

#### Tipos de volúmenes EBS

Amazon EBS ofrece varios tipos de volúmenes:

1. **gp3**: Volúmenes SSD de uso general, adecuados para la mayoría de las cargas de trabajo. Proporcionan una base de 3,000 IOPS y 125 MiB/s; los límites actuales de volumen por región alcanzan 80,000 IOPS y 2,000 MiB/s, sujetos a las proporciones de capacidad/IOPS y a los límites de las instancias. Outposts tiene límites inferiores ([especificaciones de AWS](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)).

2. **io2**: Volúmenes SSD de alto rendimiento, adecuados para cargas de trabajo que requieren muchas IOPS. io2 Block Express actual admite hasta 1,000 IOPS/GiB y 256,000 IOPS en instancias Nitro compatibles, sujeto a los límites de las instancias y de los volúmenes ([especificaciones de AWS](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)).

3. **st1**: Volúmenes HDD optimizados para la tasa de transferencia, adecuados para cargas que mueven grandes cantidades de datos, como big data, almacenes de datos y procesamiento de registros.

4. **sc1**: Volúmenes HDD fríos, adecuados para datos a los que se accede con poca frecuencia.

#### Ejemplo de Storage Class de EBS (gp3)

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab"
volumeBindingMode: WaitForFirstConsumer
```

#### Ejemplo de Storage Class de EBS (io2)

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-io2
provisioner: ebs.csi.aws.com
parameters:
  type: io2
  iops: "10000"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

### Amazon EFS

Amazon EFS (Elastic File System) proporciona almacenamiento de archivos escalable al que pueden acceder simultáneamente varias instancias EC2. EFS admite el modo de acceso ReadWriteMany, lo que resulta útil cuando varios Pods necesitan compartir el mismo volumen.

#### Instalación del controlador EFS CSI

Sigue la [guía de instalación del controlador de EKS](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html), selecciona una versión compatible del complemento/controlador y configura su rol de IAM y los requisitos previos de los nodos antes de crear PVC. Un StorageClass por sí solo no instala el controlador.

#### Creación de un sistema de archivos EFS

Para crear un sistema de archivos EFS, puedes usar AWS Management Console, AWS CLI o AWS CloudFormation.

Ejemplo de AWS CLI:

```bash
# Create EFS file system
aws efs create-file-system \
  --creation-token eks-efs \
  --performance-mode generalPurpose \
  --encrypted \
  --throughput-mode bursting \
  --tags Key=Name,Value=EKS-EFS

# Store file system ID
FS_ID=$(aws efs describe-file-systems \
  --creation-token eks-efs \
  --query "FileSystems[0].FileSystemId" \
  --output text)

# Create one mount target per Availability Zone
aws efs create-mount-target \
  --file-system-id "$FS_ID" \
  --subnet-id subnet-0eabfaa81fb22bcaf \
  --security-groups sg-068000ccf82dfba88
```

#### Storage Class de EFS

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-1234abcd
  directoryPerms: "700"
```

#### EFS Access Point con PV y PVC

```yaml
# Persistent Volume
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
    volumeHandle: fs-1234abcd::fsap-0123456789abcdef
---
# Persistent Volume Claim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

Sustituye los ID del sistema de archivos y del punto de acceso, y permite NFS sobre TCP 2049 desde el grupo de seguridad del cliente hacia los destinos de montaje. El aprovisionamiento dinámico crea puntos de acceso en un sistema de archivos existente, sin crear el propio sistema de archivos. La capacidad del PVC de EFS es un valor usado para el enlace, no una cuota por PVC; EFS crece de forma elástica. Fargate solo admite el aprovisionamiento estático de EFS.

#### Modos de rendimiento de EFS

EFS ofrece dos modos de rendimiento:

1. **General Purpose**: Modo predeterminado recomendado para la mayoría de las cargas de trabajo de sistemas de archivos. Ofrece baja latencia.

2. **Max I/O**: Modo de generación anterior con mayor latencia por operación; AWS recomienda General Purpose para las nuevas cargas de trabajo. Max I/O no es compatible con Elastic throughput.

#### Modos de tasa de transferencia de EFS

EFS ofrece tres modos de tasa de transferencia:

1. **Bursting**: La tasa de transferencia base depende del tamaño del sistema de archivos; los créditos de ráfaga permiten aumentarla temporalmente.

2. **Provisioned**: Proporciona una tasa de transferencia especificada, independientemente del tamaño del sistema de archivos.

3. **Elastic**: Aumenta o reduce automáticamente la tasa de transferencia según la carga de trabajo.

### Amazon FSx for Lustre

Amazon FSx for Lustre proporciona sistemas de archivos de alto rendimiento para cargas de trabajo de computación de alto rendimiento. FSx for Lustre es adecuado para el procesamiento de datos a gran escala, el aprendizaje automático y las cargas de trabajo de analítica.

#### Instalación del controlador FSx for Lustre CSI

Sigue la [guía de instalación del controlador de EKS](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html), selecciona una versión compatible del complemento/controlador y configura su rol de IAM y los requisitos previos de los nodos antes de crear PVC. Un StorageClass por sí solo no instala el controlador.

#### Creación de un sistema de archivos FSx for Lustre

Ejemplo de AWS CLI:

```bash
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 1200 \
  --subnet-ids subnet-0eabfaa81fb22bcaf \
  --lustre-configuration DeploymentType=SCRATCH_2
```

#### Storage Class de FSx for Lustre

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-sc
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: SCRATCH_2
  dataCompressionType: "NONE"
  weeklyMaintenanceStartTime: "7:09:00"
```

#### Tipos de implementación de FSx for Lustre

FSx for Lustre distingue entre almacenamiento temporal y persistente:

- **SCRATCH_1 / SCRATCH_2**: Almacenamiento temporal sin replicación de datos. Los servidores de archivos que fallen no se reemplazan y los datos afectados pueden perderse; SCRATCH_2 no recupera esos datos automáticamente.
- **PERSISTENT_1 / PERSISTENT_2**: Almacenamiento replicado con reemplazo automático de componentes. Las clases de almacenamiento admitidas, los incrementos de capacidad, las opciones de rendimiento y las regiones varían según el tipo de implementación.

Scratch ofrece una tasa base de 200 MBps/TiB y puede alcanzar temporalmente hasta seis veces ese valor. `PerUnitStorageThroughput` se utiliza en configuraciones SSD/HDD persistentes, no en SCRATCH_2. Las opciones de SSD persistente incluyen 50/100/200 MBps/TiB para PERSISTENT_1 y 125/250/500/1000 para PERSISTENT_2. Intelligent-Tiering tiene una configuración diferente de capacidad y tasa de transferencia. Consulta las [especificaciones de implementación](https://docs.aws.amazon.com/fsx/latest/LustreGuide/using-fsx-lustre.html) y la API antes de elegir la capacidad.

### Configuración de FSx for Lustre para cargas de trabajo de vLLM

Las cargas de trabajo con modelos de IA a gran escala, como vLLM, un motor de inferencia y servicio de LLM, necesitan almacenamiento con una tasa de transferencia elevada y baja latencia. FSx for Lustre ofrece una solución adecuada para estos requisitos.

#### Storage Class de FSx for Lustre para vLLM

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-vllm
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: PERSISTENT_1
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
reclaimPolicy: Retain
volumeBindingMode: Immediate
```

El controlador FSx CSI obtiene la capacidad de la solicitud del PVC, no de un parámetro `storageCapacity` del StorageClass. Reemplaza los ID de subred/grupo de seguridad, instala un cliente Lustre/controlador CSI compatible y asegúrate de que la capacidad solicitada sea válida para el tipo de implementación seleccionado. La imagen de inferencia siguiente es un marcador de posición que debe incluir el comando para servir el modelo.

#### PVC para cargas de trabajo de vLLM

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-model-storage
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 4800Gi
  storageClassName: fsx-lustre-vllm
```

#### Ejemplo de Deployment de vLLM

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: g5.12xlarge
      containers:
      - name: vllm
        image: vllm-inference:latest
        resources:
          limits:
            nvidia.com/gpu: 4
          requests:
            nvidia.com/gpu: 4
            memory: "64Gi"
            cpu: "32"
        volumeMounts:
        - name: model-storage
          mountPath: /models
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: vllm-model-storage
```

#### Consejos para optimizar el rendimiento de vLLM

1. **Selecciona una tasa de transferencia adecuada**: Para vLLM, elige la tasa de transferencia a partir de mediciones de la concurrencia durante la carga de modelos y del acceso a los conjuntos de datos.

2. **Optimiza la capacidad de almacenamiento**: Asigna suficiente capacidad de almacenamiento teniendo en cuenta el tamaño del modelo y del conjunto de datos.

3. **Optimización de red**: Asegúrate de que el sistema de archivos FSx for Lustre y los nodos EKS estén en la misma zona de disponibilidad.

4. **Selección del tipo de instancia**: Usa instancias GPU (p. ej., g5.12xlarge) para optimizar el rendimiento de las cargas de trabajo de vLLM.

5. **Configuración de memoria**: Asigna suficiente memoria según el tamaño del modelo.

6. **Opciones de montaje del sistema de archivos**: Usa las opciones de montaje adecuadas para lograr un rendimiento óptimo.

   ```bash
   mount -t lustre -o noatime,flock fs-1234abcd.fsx.us-west-2.amazonaws.com@tcp:/fsx /mnt/fsx
   ```

### Comparación de opciones de almacenamiento

| Opción de almacenamiento | Modo de acceso | Caso de uso | Rendimiento | Costo | Escalabilidad |
|---------------|-------------|----------|-------------|------|-------------|
| Amazon EBS | ReadWriteOnce | Almacenamiento de bloques montado en un nodo | Medio-alto | Medio | Limitada (un solo nodo) |
| Amazon EFS | ReadWriteMany | Almacenamiento de archivos compartido por varios Pods | Medio | Medio-alto | Alta (varios nodos) |
| Amazon FSx for Lustre | ReadWriteMany | HPC, ML, analítica | Muy alto | Alto | Muy alta (acceso paralelo) |

### Guía para elegir almacenamiento en EKS

1. **Cuando se necesita almacenamiento de bloques montado en un nodo**: Amazon EBS
   - Bases de datos
   - Aplicaciones con estado
   - Cargas de trabajo que se ejecutan en un solo nodo

2. **Cuando se necesita almacenamiento de archivos compartido por varios Pods**: Amazon EFS
   - Contenido de servidores web
   - Archivos de configuración compartidos
   - Procesamiento de datos a mediana escala

3. **Cuando se necesita almacenamiento de archivos de alto rendimiento**: Amazon FSx for Lustre
   - Procesamiento de datos a gran escala
   - Cargas de trabajo de aprendizaje automático e IA (vLLM, etc.)
   - Computación de alto rendimiento (HPC)
   - Analítica de big data

## Conclusión

En este capítulo hemos examinado los conceptos de almacenamiento de Kubernetes. Los volúmenes permiten que los contenedores de un Pod almacenen y compartan datos. Los volúmenes persistentes y sus solicitudes proporcionan almacenamiento con un ciclo de vida independiente del Pod. Las clases de almacenamiento permiten solicitarlo cuando hace falta mediante aprovisionamiento dinámico.

EKS ofrece distintas opciones de almacenamiento, entre ellas Amazon EBS, Amazon EFS y Amazon FSx for Lustre, cada una con usos y características de rendimiento diferentes. Para cargas de modelos de IA a gran escala, como vLLM, FSx for Lustre es una opción adecuada por su elevada tasa de transferencia y baja latencia. Su sistema de archivos paralelo permite acceder a los datos simultáneamente desde varios nodos, lo que facilita el entrenamiento y la inferencia de modelos a gran escala.

Es importante elegir la opción de almacenamiento adecuada según los requisitos de tu aplicación. Elige Amazon EBS cuando necesites almacenamiento de bloques montado en un nodo, Amazon EFS cuando necesites almacenamiento de archivos compartido por varios Pods y Amazon FSx for Lustre cuando necesites almacenamiento de archivos de alto rendimiento.

En el próximo capítulo estudiaremos la configuración y los secretos de Kubernetes.

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [cuestionario sobre almacenamiento](../quizzes/core/04-storage-quiz.md).

## Referencias

- [Documentación oficial de Kubernetes: Volumes](https://kubernetes.io/docs/concepts/storage/volumes/)
- [Documentación oficial de Kubernetes: Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Documentación oficial de Kubernetes: Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Documentación oficial de Kubernetes: Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Controlador AWS EBS CSI](https://github.com/kubernetes-sigs/aws-ebs-csi-driver)
- [Controlador AWS EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)
- [Controlador AWS FSx for Lustre CSI](https://github.com/kubernetes-sigs/aws-fsx-csi-driver)
- [Blog de AWS: Cómo escalar las cargas de trabajo de inferencia de LLM: implementación multinodo con TensorRT-LLM y Triton en Amazon EKS](https://aws.amazon.com/ko/blogs/hpc/scaling-your-llm-inference-workloads-multi-node-deployment-with-tensorrt-llm-and-triton-on-amazon-eks/)
- [Taller de AWS: GenAI FSx EKS](https://catalog.workshops.aws/genaifsxeks/en-US/200-module2-genai/210-deploy)
