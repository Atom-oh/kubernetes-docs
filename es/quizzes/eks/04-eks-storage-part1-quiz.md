# Cuestionario de almacenamiento de EKS - Parte 1

> **Última actualización**: 11 de septiembre de 2026

Estas respuestas respetan los responsables y los requisitos previos descritos en [el capítulo de almacenamiento](../../eks/04-eks-storage-part1.md). Salvo que se indique lo contrario, los ejemplos usan almacenamiento convencional de EC2 con Linux; la compatibilidad varía entre Auto Mode, Fargate y Hybrid. Las comprobaciones locales de esquemas o simulaciones no demuestran que un volumen de AWS se haya conectado, que los datos se hayan recuperado ni cuál será el rendimiento en producción.

### 1. ¿Qué controlador administra los volúmenes EBS convencionales con el provisioner ebs.csi.aws.com?

- A. Controlador CSI de Amazon EFS
- B. Controlador CSI de Amazon EBS
- C. Controlador CSI de FSx for Lustre
- D. Controlador CSI de Mountpoint for Amazon S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Controlador CSI de Amazon EBS**

El controlador está disponible como complemento de EKS, pero eso no significa que se instale automáticamente en todos los clústeres. EKS Auto Mode tiene su propia ruta integrada, `ebs.csi.eks.amazonaws.com`. Comprueba el entorno de cómputo elegido, quién administra el complemento, la compatibilidad entre Kubernetes y el controlador, y el estado real de la instalación.

Prepara la relación de confianza de Pod Identity o IRSA para el controlador y revisa `AmazonEBSCSIDriverPolicyV2` o los permisos de alcance limitado, incluidos los permisos sobre la clave de KMS del cliente cuando hagan falta. Una política histórica copiada no sustituye la política vigente del controlador ni su relación de confianza. Usa el flujo controlado de catálogo e instalación del capítulo de origen; no uses el valor literal `latest` para la versión del complemento en la API de AWS ni sobrescribas la instalación de otro responsable.

Esta StorageClass permite usar gp3 cifrado, aprovisionar teniendo en cuenta el planificador, ampliar el volumen y definir su retención:
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
Los snapshots también requieren las CRD de snapshots y su controlador, además de una VolumeSnapshotClass compatible. El controlador admite varios tipos de volumen EBS, cada uno con restricciones de tamaño y rendimiento. Los volúmenes EBS convencionales permanecen en una sola zona de disponibilidad (AZ); los Pods de Fargate no pueden montarlos, aunque un controlador EBS diseñado por separado sí puede ejecutarse en Fargate. EBS no es compatible con Hybrid Nodes.

EFS y FSx tienen sus propios controladores compatibles. La afirmación anterior de que no existía un controlador CSI oficial para S3 era falsa: Mountpoint CSI expone buckets S3 existentes con semántica POSIX limitada, mientras que S3 Files usa EFS CSI 3.0 o posterior para ofrecer una interfaz de sistema de archivos compartido distinta.

</details>

### 2. ¿Qué servicio NFS administrado permite compartir archivos entre nodos Linux sin un cliente Lustre?

- A. Sistema de archivos gp3 convencional
- B. Amazon EFS
- C. API GET/PUT de objetos de S3
- D. FSx for Lustre

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Amazon EFS**

EFS ofrece acceso NFS compartido y admite RWX. Que haya varios Pods no basta para elegir EFS: RWO permite que varios Pods de un mismo nodo compartan el volumen, y FSx for Lustre también admite acceso compartido. Elige según los requisitos reales de protocolo, coherencia, latencia, rendimiento, durabilidad y costo.

Usa una instalación compatible de EFS CSI con el rol de IAM requerido para el controlador y un sistema de archivos ya cifrado. Prepara destinos de montaje en las AZ donde estén los clientes, con un máximo de una subred por AZ, y configura las rutas de grupos de seguridad (SG), DNS y NFS. La configuración del capítulo de origen captura los ID y comprueba la pertenencia a la AZ y la VPC. Reutilizar un token de creación con otros parámetros de cifrado no cifra in situ un sistema de archivos existente.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```
La solicitud de 5 Gi en la PVC es metadato de vinculación, no una cuota para el directorio. Los puntos de acceso aplican una identidad POSIX y un directorio raíz; las políticas de IAM y del sistema de archivos, junto con los controles de red, determinan qué acceso se permite. El aprovisionamiento dinámico de puntos de acceso no es la opción para Fargate; usa su integración estática compatible. La autorización TLS del montaje del cliente es independiente de los permisos de aprovisionamiento del controlador.

EFS Regional y EFS One Zone tienen características distintas ante fallos. Los objetivos publicados de diseño o durabilidad y los compromisos de nivel de servicio no garantizan el tiempo de actividad medido de esta aplicación. El crecimiento automático del almacenamiento no elimina la necesidad de planificar el rendimiento, las IOPS, las cuotas, las copias de seguridad y el costo. AWS recomienda el modo de rendimiento General Purpose; Max I/O tiene mayor latencia por operación. Elige conscientemente entre los modos Elastic, Provisioned o Bursting en lugar de asumir un valor predeterminado universal.

Para los parámetros estáticos de una aplicación, ConfigMaps o Secrets pueden ser más apropiados que el almacenamiento compartido. Los archivos compartidos que se modifican requieren mecanismos de bloqueo y coherencia en la aplicación. Las API de S3, Mountpoint y S3 Files son interfaces distintas; no descartes todo acceso a archivos de S3. FSx for Lustre es un sistema de archivos paralelo alternativo; que su configuración sea distinta no lo vuelve inadecuado por sí sola.

</details>

### 3. ¿Qué afirmación describe correctamente las limitaciones de los sistemas de archivos EBS convencionales?

- A. El mismo volumen se conecta en cualquier AZ
- B. Los Pods de Fargate montan cualquier volumen EBS
- C. Una AZ; RWO puede servir a varios Pods del mismo nodo
- D. RWO garantiza que haya exactamente un Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. El volumen permanece en una sola AZ; los Pods de un mismo nodo pueden compartirlo con RWO.**

RWO significa lectura y escritura desde un nodo, no desde un único Pod. Tras separar el volumen de forma segura y volver a conectarlo, un Pod de reemplazo puede usar la misma PVC en otro nodo adecuado de esa AZ. El mismo volumen no se puede conectar desde distintas AZ. Restaurar un snapshot crea otro volumen en la AZ de destino; no mueve el volumen existente ni proporciona replicación continua.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```
Usa `WaitForFirstConsumer` para que las restricciones de planificación determinen la ubicación inicial del volumen. Una PVC ya vinculada sigue sujeta a la topología de su PV; cambiar el selector de nodo no traslada los datos. Las PVC independientes de un StatefulSet por réplica crean volúmenes separados, no replicación de la base de datos. La disponibilidad Multi-AZ requiere un diseño de replicación de datos o recuperación en la aplicación.

EBS CSI 1.66.0 también admite una modalidad Multi-Attach de bloque sin formato para io2 con RWX y la coordinación compatible de la infraestructura y la aplicación. Esto no convierte un volumen gp3/ext4 convencional en un sistema de archivos compartido entre varios nodos. Los Pods de Fargate siguen sin poder montar EBS. Si necesitas compartir archivos, usa un sistema de archivos adecuado.

</details>

### 4. ¿Todas las PVC de EBS aprovisionadas dinámicamente deben usar únicamente ReadWriteOnce?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: No. RWO es la opción habitual; RWOP y los modos especializados de bloque sin formato tienen otros requisitos.**

RWOP impone la restricción de un solo Pod que RWO no ofrece. Es estable desde Kubernetes 1.29 y requiere una pila de sidecars CSI compatible. La traducción de modos de acceso de CSI puede asignar RWOP a SINGLE_NODE_WRITER en controladores sin la capacidad más reciente de escritura en un solo nodo; el valor de esa constante en el controlador no demuestra por sí solo que RWOP no sea compatible. Este es un **PVC alternativo** para una carga de trabajo de un solo Pod:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-exclusive
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOncePod
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```
| Modo | Significado |
|---|---|
| RWO | Un nodo con lectura y escritura; varios Pods de ese nodo pueden compartirlo |
| RWOP | Un Pod en todo el clúster con compatibilidad adecuada de CSI y Kubernetes |
| RWX | Escritura desde varios nodos solo si el backend, el controlador y la aplicación lo admiten |
| ROX | Lectura desde varios nodos; no es compatible con todos los controladores CSI |

La compatibilidad del modo de acceso no sustituye los permisos del sistema de archivos o de IAM ni un montaje explícitamente de solo lectura. Los volúmenes separados restaurados de un snapshot son copias independientes; no forman un único volumen ROX compartido. No montes sistemas ext4/XFS convencionales por separado con varios escritores como sustituto de un diseño de almacenamiento en clúster.

</details>

### 5. ¿Qué ocurre cuando un Pod respaldado por EBS se reemplaza en otro nodo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: El volumen conservado se puede separar y volver a conectar de forma segura dentro de la misma AZ; hay que verificar el tiempo de recuperación y la coherencia de la aplicación.**

Kubernetes crea un Pod de reemplazo; no traslada el objeto Pod original. En un volumen de conexión única, hay que detener o cercar el escritor anterior y separar el volumen de forma segura antes de conectarlo al nuevo nodo. El volumen persiste según su ciclo de vida, pero un fallo abrupto puede perder escrituras que aún no se hayan vaciado o exigir la recuperación del sistema de archivos o de la base de datos. No afirmes que todas las escrituras sobrevivirán con certeza.

La estimación original de “10–30 segundos” para volver a conectar el volumen no tiene aquí una fuente de medición verificada. Se conserva como **estimación histórica no verificada**, no como SLA de AWS ni como garantía de recuperación. La detección del fallo del nodo, el cercado, la reconciliación del controlador, las operaciones del volumen y el inicio de la aplicación pueden tardar más.

Los PDB limitan las expulsiones voluntarias a las que son aplicables, pero no protegen frente a fallos de nodo o AZ. Configúralos según las réplicas y el cuórum reales: un PDB no hace que una base de datos con una sola réplica tenga alta disponibilidad. La sonda `readiness` debe verificar que la aplicación esté lista, no limitarse a buscar un marcador persistente `/data/ready`; la sonda `liveness` reinicia el contenedor, pero no controla el tráfico del Service. El orden del StatefulSet y la distribución topológica no replican un volumen EBS entre AZ. Los PDB por AZ también requieren etiquetas de Pod que coincidan realmente; las etiquetas de zona de los nodos no se copian automáticamente a los Pods.

Cuando sea posible, usa un apagado ordenado, diagnostica los eventos de VolumeAttachment y del Pod junto con el estado real del nodo, y sigue los procedimientos de recuperación documentados. Forzar la separación o borrar metadatos de conexión sin cercar el escritor no es una optimización general de latencia. Prueba la restauración de los datos de la aplicación y los objetivos de recuperación con una copia de seguridad independiente.

</details>

### 6. ¿Qué recurso solicita un snapshot de EBS y qué hace que la copia de seguridad sea utilizable?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: `VolumeSnapshot`**

Prepara CRD y controlador de snapshots compatibles, además del snapshotter de EBS, y usa una clase cuyo controlador coincida con el aprovisionador real. Respeta quién administra los complementos en lugar de aplicar manifiestos flotantes de la rama principal. Para mantener la coherencia del snapshot, puede ser necesario coordinar la copia de seguridad con la base de datos o pausarla temporalmente; que el snapshot a nivel de bloque esté listo no demuestra por sí solo que la aplicación pueda recuperarse.
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-retain
driver: ebs.csi.aws.com
deletionPolicy: Retain
```

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-snapshot
  namespace: storage-demo
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: ebs-claim
```

```bash
set -euo pipefail
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  volumesnapshot/ebs-snapshot --timeout=300s
kubectl -n storage-demo get volumesnapshot ebs-snapshot -o yaml
```
Restaura en una PVC nueva del mismo espacio de nombres, con capacidad igual o superior a `status.restoreSize`; usa un consumidor para la vinculación `WaitForFirstConsumer` y verifica los datos. Este manifiesto restaura el **snapshot de nombre fijo `ebs-snapshot` definido arriba**; cambia el nombre si vas a restaurar otro snapshot.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-restored
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 20Gi
  dataSource:
    name: ebs-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```
Para crear snapshots de forma repetida, este comando es una **alternativa** que crea un snapshot con nombre único y espera a que esté listo. Registra el nombre resultante. Para programarlo se requiere una ServiceAccount/RBAC de alcance limitado, herramientas con versión fijada, una zona horaria (UTC u otra) elegida deliberadamente, ejecuciones que no se solapen y gestión de errores y retención; las antiguas cuentas de servicio sin especificar no constituían un sistema de copias de seguridad instalado.
```bash
set -euo pipefail
SNAPSHOT_NAME="ebs-snapshot-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
kubectl -n storage-demo create -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: $SNAPSHOT_NAME
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: ebs-claim
EOF
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  "volumesnapshot/$SNAPSHOT_NAME" --timeout=300s
```
Para aplicar la retención, analiza marcas de tiempo absolutas y limita el alcance por espacio de nombres, etiqueta de copia de seguridad y PVC de origen. Lo siguiente genera una **lista candidata solo para revisión**; no elimina nada. Antes de automatizar eliminaciones, comprueba la política `deletionPolicy`, la propiedad, las dependencias y la existencia de un punto de recuperación verificado para cada VolumeSnapshotContent vinculado. La política Delete puede eliminar el snapshot de AWS; Retain lo conserva y puede generar cargos de almacenamiento. Un controlador de copias de seguridad para producción necesita gestionar UID y precondiciones y probar la recuperación; no basta con una canalización `xargs delete` cuyo alcance no esté bien delimitado.
```bash
set -euo pipefail
kubectl -n storage-demo get volumesnapshots -l storage-demo=ebs \
  -o json > storage-demo-snapshots.json
python3 - storage-demo-snapshots.json <<'PY'
import datetime, json, sys
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(days=30)
with open(sys.argv[1]) as stream:
    snapshots = json.load(stream)["items"]
candidates = []
for snapshot in snapshots:
    meta, spec, status = snapshot["metadata"], snapshot["spec"], snapshot.get("status", {})
    if meta.get("namespace") != "storage-demo" or meta.get("labels", {}).get("storage-demo") != "ebs":
        continue
    if spec.get("source", {}).get("persistentVolumeClaimName") != "ebs-claim":
        continue
    if status.get("readyToUse") is not True or meta.get("deletionTimestamp"):
        continue
    created = datetime.datetime.fromisoformat(meta["creationTimestamp"].replace("Z", "+00:00"))
    if created.tzinfo is None:
        raise SystemExit("Snapshot timestamp must include a timezone")
    if created < cutoff:
        candidates.append({"name": meta["name"], "uid": meta["uid"],
                           "content": status.get("boundVolumeSnapshotContentName"),
                           "createdAt": meta["creationTimestamp"]})
print(json.dumps({"reviewOnly": True, "candidates": candidates}, indent=2))
PY
```
Transferir snapshots entre clústeres, cuentas o regiones requiere importar o copiar explícitamente el snapshot, disponer de acceso a KMS y configurar la restauración. Aplica a los datos de producción copiados a entornos de prueba los mismos controles de acceso y retención. Verifica los datos reales; no basta con comprobar que existen objetos VolumeSnapshot.

</details>

### 7. Diseña el almacenamiento para una base de datos, archivos compartidos y datos paralelos de ML.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Elige el backend y el ciclo de vida para cada requisito, y especifica sus requisitos previos.**

Este es un plano de configuración revisado, **no un sistema de producción desplegado**. Primero crea o revisa los espacios de nombres `database`, `application` y `ml-workloads`, los controladores CSI y los roles de IAM compatibles, los permisos de KMS y de red, los recursos reales de EFS/FSx/S3 y la compatibilidad de las imágenes y el entorno de cómputo. Los recursos StorageClass tienen alcance de clúster; los ejemplos son alternativas que debe administrar un único responsable. La capacidad, la recuperación de la aplicación y el rendimiento deben probarse en el entorno de destino.

**1. Almacenamiento en bloques para la base de datos.** Conserva los valores ilustrativos originales de 16 000 IOPS/1000 MiB/s, pero no los presentes como máximos universales de gp3. Actualmente, gp3 Regional admite hasta 80 000 IOPS y 2000 MiB/s, sujeto a las proporciones entre tamaño del volumen e IOPS y a los límites de la instancia; Outposts tiene límites distintos. El ejemplo es una elección de configuración, no una medición de referencia ni una prueba de que la base de datos necesite ese gasto.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-db
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '16000'
  throughput: '1000'
```
El StatefulSet crea **data-postgres-0** a partir de su plantilla de PVC `data`. No crees también la PVC `database-data` original, que no se usa, ni generes un snapshot de esa PVC sin uso. Prepara `postgres-secret` con una clave `password` administrada de forma segura; aquí no se proporciona ningún valor de contraseña. La imagen la lee desde un archivo montado, y PGDATA usa un subdirectorio para que los metadatos del sistema de archivos en la raíz del volumen no interfieran con la inicialización.
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
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: ebs-gp3-db
      resources:
        requests:
          storage: 100Gi
```
Este ejemplo usa PostgreSQL 14.24, la versión secundaria vigente verificada de la versión principal 14. El soporte de la versión principal 14 finaliza el 12 de noviembre de 2026. Planifica una migración probada a una versión compatible y fija un digest de imagen aprobado para producción. Esta única réplica no constituye una base de datos replicada ni de alta disponibilidad; escalar réplicas sin diseñar la replicación de la base de datos no es una solución. La política explícita de retención conserva las PVC cuando se elimina o reduce el StatefulSet, por lo que los datos y los posibles cargos de almacenamiento permanecen.

Después de hacer una copia de seguridad coherente con la aplicación o ponerla en pausa, crea un snapshot de la PVC que realmente usa la base de datos. La clase es la clase de snapshot de EBS con política de retención definida anteriormente:
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: database-snapshot
  namespace: database
  labels:
    backup-set: postgres-demo
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: data-postgres-0
```
**2. Archivos compartidos.** La configuración estática suele corresponder a ConfigMaps o Secrets. Si necesitas archivos compartidos modificables, la clase EFS del capítulo de origen proporciona directorios AP separados y UID/GID 1000. Sustituye el ID del sistema de archivos y valida las rutas y los permisos del cliente; esta PVC no impone una cuota de 5 Gi.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage
  namespace: application
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```
Este Job de inicialización solo escribe un parámetro de demostración no confidencial y conserva cualquier archivo existente. Los tres Pods lectores montan el volumen en modo de solo lectura y comprueban que se pueda leer. Esto demuestra la entrega de archivos; una aplicación real debe analizar y volver a cargar su configuración. Montar `/etc/config` en un nginx sin configurar no hará que nginx use esos archivos.
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: config-seed
  namespace: application
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: seed
        image: busybox:1.38.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          if test -e /config/settings.txt; then
            echo "Existing settings preserved"
          else
            (set -C; printf 'MODE=demo\n' > /config/settings.txt)
          fi
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
        - name: config
          mountPath: /config
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: config-storage
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: config-reader
  namespace: application
spec:
  replicas: 3
  selector:
    matchLabels:
      app: config-reader
  template:
    metadata:
      labels:
        app: config-reader
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
      - name: reader
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
        readinessProbe:
          exec:
            command:
            - test
            - -r
            - /etc/config/settings.txt
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 64Mi
        volumeMounts:
        - name: config
          mountPath: /etc/config
          readOnly: true
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: config-storage
```
**3. Datos paralelos de ML.** Prepara un cliente y un kernel compatibles con Lustre, CSI/IAM y la integración del sistema de archivos con S3. Este ejemplo SCRATCH_2 es para datos que se puedan volver a generar; omite los parámetros de rendimiento por unidad y copia de seguridad automática, que solo corresponden a configuraciones persistentes. `s3ImportPath` es un parámetro válido de FSx CSI 1.10.0; sustituye el bucket/prefijo por un conjunto de datos accesible y de tu propiedad, y revisa la integración y la configuración de la región admitidas. LZ4 es una función de almacenamiento, no una prueba de que se haya medido una mejora de compresión o rendimiento.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: LZ4
  s3ImportPath: s3://example-training-data/dataset/
mountOptions:
- flock
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-training-data
  namespace: ml-workloads
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi
```
La solicitud de PVC de 1200 Gi es una asignación de ejemplo; confirma cómo redondea el controlador y qué opciones de capacidad ofrece el servicio. El Job siguiente es una **plantilla**: sustituye el marcador de posición por una imagen GPU probada y sin privilegios de root que incluya `/opt/training/train.py` y acepte los argumentos indicados, y carga el conjunto de datos antes de ejecutarlo. El código de entrenamiento permanece en la imagen para que el montaje de datos no lo oculte. Cuatro Pods simultáneos que soliciten cuatro GPU cada uno pueden requerir **16 GPU**, además de la CPU, memoria y cuotas aplicables solicitadas. Las tareas completadas con índice identifican cuatro tareas, pero no implementan automáticamente el entrenamiento distribuido ni la sincronización de gradientes.
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: ml-workloads
spec:
  parallelism: 4
  completions: 4
  completionMode: Indexed
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: training
        image: registry.example.com/team/trainer:reviewed
        command:
        - python
        - /opt/training/train.py
        args:
        - --data-dir
        - /training
        - --shard-index
        - $(JOB_COMPLETION_INDEX)
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
        resources:
          limits:
            nvidia.com/gpu: '4'
          requests:
            cpu: '8'
            memory: 32Gi
        volumeMounts:
        - name: data
          mountPath: /training
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: ml-training-data
```
Las afirmaciones originales sobre rendimiento agregado («cientos de GB/s» y «millones de IOPS») no eran mediciones de este pequeño ejemplo SCRATCH_2. No uses esas cifras para dimensionar; verifica la configuración elegida del sistema de archivos y el cliente con una carga de trabajo representativa. No se ejecutó ningún entrenamiento.

**Recuperación, supervisión y costo:** elige explícitamente las métricas del backend y del sistema de archivos o la aplicación, supervisa las cuotas, el rendimiento, la latencia y el uso reales, y prueba las restauraciones con datos conocidos. Conservar un PV o un snapshot no constituye un programa de copias de seguridad. Antes de eliminar un volumen que parezca no usarse, comprueba quién es su responsable, sus referencias y que exista una copia de recuperación verificada. Para la seguridad, usa admisión de Pod Security, `securityContext`, IAM de alcance limitado, TLS y permisos del sistema de archivos; PodSecurityPolicy ya no está disponible. Este plano no demuestra que la solución esté lista para producción ni que su costo/rendimiento estén optimizados.

</details>

### 8. ¿Eliminar un Pod siempre borra los datos de su volumen?

- A. Sí, se elimina cada volumen
- B. No, hay que comprobar su ciclo de vida
- C. Solo si el Pod tiene dos contenedores
- D. Nunca; todos los volúmenes son persistentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. No; la duración depende del tipo de volumen, la propiedad de la PVC y la política de recuperación.**

Los datos de `emptyDir` pertenecen al ámbito del Pod, mientras que un volumen respaldado por una PVC con retención puede durar más que el Pod. Las PVC efímeras genéricas pueden pertenecer al Pod. Los datos de los discos locales de instancia siguen ligados a la vida útil del nodo y del medio físico, aunque un controlador CSI los presente como PV; el complemento oficial de EC2 Instance Store CSI, disponible desde mayo de 2026, no convierte ese almacenamiento en duradero y replicado.

</details>

### 9. ¿Una PVC de EFS que solicita 5 Gi impone una cuota de 5 Gi al directorio?

- A. Sí, las escrituras fallan al superar 5 Gi
- B. Sí, cada punto de acceso obtiene un dispositivo de bloques
- C. No, la solicitud es metadato de vinculación
- D. Solo con directoryPerms700

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. No; es metadato de capacidad y vinculación de Kubernetes.**

EFS crece a medida que se almacenan datos y la PVC no reserva de antemano esa capacidad ni limita el directorio a ese tamaño. Planifica por separado el rendimiento del sistema de archivos, los puntos de acceso, el comportamiento del cliente, la retención y los costos. Si necesitas imponer una cuota, usa controles explícitos de la aplicación o de la cuenta.

</details>

### 10. ¿Qué campo define la política inicial de recuperación de una StorageClass?

- A. `persistentVolumeReclaimPolicy`
- B. `reclaimPolicy`
- C. `deletionPolicy`
- D. `dataRetention`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `reclaimPolicy`**

`persistentVolumeReclaimPolicy` pertenece a `PersistentVolume.spec`. La política de una StorageClass se copia a los PV que se aprovisionan después; cambiar la clase no modifica automáticamente todos los PV existentes. La deletionPolicy del snapshot es otro parámetro independiente del ciclo de vida.

</details>

### 11. ¿Qué elimina normalmente Delete en un punto de acceso EFS aprovisionado dinámicamente?

- A. Todos los sistemas de archivos de la VPC
- B. Siempre todo el sistema de archivos EFS
- C. El punto de acceso; limpiar el directorio raíz es opcional
- D. Nunca se elimina ningún recurso de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. El punto de acceso; la eliminación de los datos del directorio depende de la configuración del controlador.**

El aprovisionador de puntos de acceso normalmente no elimina el sistema de archivos EFS. En el chart revisado, deleteAccessPointRootDir tiene el valor predeterminado false; habilitarlo cambia cómo se eliminan los datos. Antes de borrar cualquier PVC, inspecciona los valores reales del controlador y quién es responsable de los puntos de acceso compartidos o reutilizados.

</details>

### 12. ¿Qué afirmación sobre el acceso a S3 desde EKS es correcta?

- A. No existe un controlador CSI oficial para S3
- B. Las interfaces y los requisitos previos son distintos
- C. Mountpoint crea buckets nuevos automáticamente
- D. Todos los montajes de S3 admiten todas las operaciones POSIX

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Las API de S3, Mountpoint CSI y S3 Files ofrecen interfaces y requisitos diferentes.**

Mountpoint CSI, producto oficial, admite buckets existentes mediante una interfaz de archivos con semántica POSIX limitada. S3 Files es un servicio distinto de sistema de archivos compartido, compatible con EFS CSI 3.0 o posterior y con otros permisos para el controlador y los nodos. No supongas que todas las rutas respaldadas por S3 admiten las mismas operaciones, modos de cómputo o modelo de aprovisionamiento.

</details>

### 13. ¿Qué puede hacer que una PVC con WaitForFirstConsumer permanezca legítimamente en Pending?

- A. Todos los controladores CSI están averiados
- B. Aún no se ha planificado ningún consumidor adecuado
- C. Retain impide la vinculación
- D. La PVC debe usar una clase vacía

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Aún no se ha planificado un consumidor adecuado.**

La vinculación diferida permite que la topología y las restricciones de recursos del planificador determinen la ubicación. No siempre significa que haya fallado el almacenamiento. Establecer `spec.nodeName` omite el planificador y puede impedir este proceso de vinculación; usa las restricciones de planificación admitidas. Comprueba los eventos antes de cambiar la StorageClass o aprovisionar volúmenes manualmente.

</details>

### 14. ¿Qué modo de acceso impone una restricción de un solo Pod con compatibilidad CSI adecuada?

- A. ReadWriteOnce
- B. ReadWriteMany
- C. ReadOnlyMany
- D. ReadWriteOncePod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. ReadWriteOncePod**

RWO limita la conexión de lectura y escritura a un nodo y puede servir a varios Pods de ese nodo. RWOP es el modo independiente para un solo Pod; aun así, no sustituye el diseño de coherencia de la aplicación, copias de seguridad o autorización. No combines RWOP con otros modos de acceso en la misma PVC.

</details>

### 15. ¿Cómo debes ampliar el ejemplo EBS de 10 Gi y verificar la recuperación?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Habilita una ampliación compatible, aumenta la solicitud de la PVC, verifica la capacidad real y prueba una restauración independiente.**

Confirma `allowVolumeExpansion` en la StorageClass y la compatibilidad del controlador y del sistema de archivos, haz una copia de seguridad adecuada y coherente con la aplicación, y después actualiza la solicitud de la PVC desde el recurso que la administra. En esta demostración, el objetivo es 20 Gi. No reduzcas un volumen ni edites la capacidad del PV para simular el cambio de tamaño:
```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```
Comprueba las condiciones y el estado de la PVC, el sistema de archivos montado y las operaciones de entrada/salida de la aplicación. Si el redimensionamiento del sistema de archivos sigue pendiente, sigue el procedimiento documentado para volver a montarlo o reiniciarlo. Restaura un snapshot en una PVC nueva, móntala con un consumidor adecuado y verifica datos conocidos de la aplicación. Aumentar la solicitud de la PVC o tener un objeto snapshot listo no basta para dar por probada la recuperación de datos.

</details>

Referencias oficiales: [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html), [PV de Kubernetes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [especificaciones de gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html), [soporte de PostgreSQL](https://www.postgresql.org/support/versioning/), [S3 Files](https://docs.aws.amazon.com/eks/latest/userguide/s3files-csi.html).
