# Storage Quiz

Este cuestionario evalúa tu comprensión de los conceptos de almacenamiento de Kubernetes, tipos de volúmenes, volúmenes persistentes, clases de almacenamiento y más.

## Multiple Choice Questions

1. ¿Qué recurso de almacenamiento en Kubernetes conserva los datos incluso cuando se reinicia un pod?
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) PersistentVolume**

**Explicación:**
PersistentVolume (PV) es almacenamiento del cluster que es aprovisionado por un administrador del cluster o aprovisionado dinámicamente mediante una clase de almacenamiento. Los PV conservan los datos incluso cuando los pods se reinician o se eliminan. ConfigMap y Secret se utilizan para almacenar datos de configuración e información sensible respectivamente, mientras que emptyDir es un directorio temporal que solo existe mientras el pod está en ejecución.
</details>

2. ¿Qué recurso se utiliza en Kubernetes para solicitar un PersistentVolume?
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) PersistentVolumeClaim**

**Explicación:**
PersistentVolumeClaim (PVC) es la forma en que los usuarios solicitan PersistentVolumes. Un PVC representa una solicitud de almacenamiento con un tamaño y un modo de acceso específicos. Kubernetes encuentra un PV que cumple los requisitos del PVC y los vincula.
</details>

3. ¿Qué recurso se utiliza para el aprovisionamiento dinámico de volúmenes en Kubernetes?
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) StorageClass**

**Explicación:**
StorageClass proporciona una forma para que los administradores describan las "clases" de almacenamiento que ofrecen. Las distintas clases pueden corresponder a niveles de servicio, políticas de respaldo o políticas arbitrarias determinadas por el administrador del cluster. Mediante StorageClass, los PV pueden aprovisionarse dinámicamente cuando se crean los PVC.
</details>

4. ¿Qué política en Kubernetes elimina automáticamente un PersistentVolumeClaim cuando se elimina un pod?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Esta funcionalidad no se proporciona
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Esta funcionalidad no se proporciona**

**Explicación:**
Kubernetes no proporciona funcionalidad integrada para eliminar automáticamente los PVC cuando se eliminan los pods. Los PVC existen independientemente de los pods y se conservan incluso cuando los pods se eliminan. Esta es una decisión de diseño para evitar la pérdida de datos. Para StatefulSets, puedes configurar políticas de eliminación de PVC mediante `persistentVolumeClaimRetentionPolicy`.
</details>

5. ¿Cuál de los siguientes NO es un modo de acceso de PersistentVolume?
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) WriteOnlyMany**

**Explicación:**
Los modos de acceso para PersistentVolumes en Kubernetes son ReadWriteOnce (RWO), ReadOnlyMany (ROX) y ReadWriteMany (RWX). WriteOnlyMany no existe como modo de acceso. ReadWriteOnce permite el montaje de lectura y escritura por un único nodo, ReadOnlyMany permite el montaje de solo lectura por múltiples nodos, y ReadWriteMany permite el montaje de lectura y escritura por múltiples nodos.
</details>

6. ¿Qué política de reclamación de PersistentVolume libera el recurso sin eliminar el volumen?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Retain**

**Explicación:**
La política Retain conserva el PV y sus datos después de que se elimina el PVC. El volumen se considera "Released", pero no está disponible para otras reclamaciones. El administrador debe limpiar manualmente los datos y dejar el volumen disponible para su reutilización. La política Delete elimina el PV y la infraestructura externa (por ejemplo, AWS EBS, GCE PD) cuando se elimina el PVC. La política Recycle está obsoleta, y en su lugar debe utilizarse el aprovisionamiento dinámico.
</details>

7. ¿Qué tipo de volumen proporciona almacenamiento temporal en Kubernetes?
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) awsElasticBlockStore
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) emptyDir**

**Explicación:**
Un volumen emptyDir se crea por primera vez cuando se asigna un pod a un nodo y existe solo mientras ese pod se ejecuta en ese nodo. Como sugiere el nombre, el volumen está inicialmente vacío. Todos los contenedores del pod pueden leer y escribir los mismos archivos en el volumen emptyDir, aunque el volumen puede montarse en las mismas rutas o en rutas diferentes en cada contenedor. Cuando un pod se elimina de un nodo por cualquier motivo, los datos en el emptyDir se eliminan permanentemente.
</details>

8. ¿Qué aprovisionador de almacenamiento se utiliza de forma predeterminada en AWS EKS?
   - A) kubernetes.io/aws-ebs
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) kubernetes.io/aws-ebs**

**Explicación:**
AWS EKS utiliza AWS EBS (Elastic Block Store) de forma predeterminada para proporcionar almacenamiento persistente. El nombre del aprovisionador es 'kubernetes.io/aws-ebs'. Este aprovisionador crea y administra automáticamente volúmenes EBS cuando se crean PVC. AWS EKS admite varios tipos de volúmenes EBS, incluidos gp2, gp3, io1, sc1 y st1.
</details>

9. ¿Cuál es el nombre de campo correcto para las plantillas de reclamación de volumen utilizadas en StatefulSets?
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) volumeClaimTemplates**

**Explicación:**
StatefulSets utilizan el campo `volumeClaimTemplates` para crear automáticamente PVC para cada pod. Esta plantilla se utiliza para crear PVC para cada réplica del StatefulSet. Los nombres de los PVC creados siguen el formato `<volume-claim-template-name>-<pod-name>`.
</details>

10. ¿Cuál es el propósito principal de CSI (Container Storage Interface) en Kubernetes?
    - A) Estandarizar la comunicación entre contenedores
    - B) Permitir que los drivers de almacenamiento se desarrollen fuera del código de Kubernetes
    - C) Estandarizar el acceso a registros de imágenes de contenedores
    - D) Automatizar la migración de almacenamiento entre proveedores de nube
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir que los drivers de almacenamiento se desarrollen fuera del código de Kubernetes**

**Explicación:**
CSI (Container Storage Interface) define una interfaz estándar entre sistemas de orquestación de contenedores (como Kubernetes) y proveedores de almacenamiento. El propósito principal de CSI es permitir que los drivers de almacenamiento se desarrollen, desplieguen y administren fuera de la base de código de Kubernetes. Esto permite a los proveedores de almacenamiento desarrollar y mantener sus propios plugins independientemente del ciclo de lanzamiento de Kubernetes.
</details>

## Advanced Questions

1. Explica cómo integrar nuevos tipos de almacenamiento usando drivers CSI (Container Storage Interface) en Kubernetes y sus beneficios.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Método de integración de CSI Driver:**

1. **Desplegar CSI Driver**: Los drivers CSI normalmente constan de los siguientes componentes:
  - **Node Plugin DaemonSet**: Se ejecuta en cada nodo y realiza operaciones de montaje/desmontaje de volúmenes
  - **Controller Plugin Deployment/StatefulSet**: Realiza operaciones de creación/eliminación/snapshot de volúmenes
  - **Recursos RBAC**: Configura los permisos requeridos

2. **Crear StorageClass**: Define una StorageClass que use el driver CSI:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-storage
provisioner: example.csi.k8s.io  # CSI driver name
parameters:
  # Driver-specific parameters
  type: ssd
  fsType: ext4
```

3. **Configurar soporte para CSI Volume Snapshot** (opcional):
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **Probar CSI Driver**: Verifica la funcionalidad creando un PVC y montándolo en un pod

**Beneficios de usar CSI:**

1. **Ciclo de desarrollo independiente**: Los proveedores de almacenamiento pueden desarrollar y desplegar drivers independientemente del ciclo de lanzamiento de Kubernetes.

2. **Interfaz estandarizada**: CSI proporciona una interfaz estándar entre sistemas de orquestación de contenedores y proveedores de almacenamiento.

3. **Funciones avanzadas de almacenamiento**: Admite funciones avanzadas como snapshots de volúmenes, clonación y redimensionamiento de forma estandarizada.

4. **Seguridad mejorada**: Los drivers CSI se ejecutan con privilegios limitados y se les pueden conceder solo los permisos necesarios.

5. **Opciones de almacenamiento diversas**: Integra fácilmente soluciones de almacenamiento de proveedores de nube, open source y comerciales.

6. **Arquitectura de plugins**: Los drivers CSI pueden agregarse o eliminarse según sea necesario.

**Ejemplo de implementación real (AWS EBS CSI Driver):**

```bash
# Install AWS EBS CSI Driver (using Helm)
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  --namespace kube-system \
  --set enableVolumeScheduling=true \
  --set enableVolumeResizing=true \
  --set enableVolumeSnapshot=true

# Create StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
EOF
```

CSI es una parte central del ecosistema de almacenamiento de Kubernetes, que permite la integración de varias soluciones de almacenamiento y el uso de funciones avanzadas de almacenamiento.
</details>

2. Diseña un cluster de base de datos de alta disponibilidad usando StatefulSet y PersistentVolume, y explica la estrategia de persistencia de datos y respaldo.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Diseño de cluster de base de datos de alta disponibilidad:**

1. **Descripción general de la arquitectura**:
  - Cluster de base de datos configurado como un StatefulSet con 3 o más réplicas
  - Cada pod tiene asignado un PersistentVolume único
  - Identificadores de red estables proporcionados mediante un service headless
  - Configuración maestro-esclavo mediante un mecanismo de elección de líder

2. **Configuración de StorageClass**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iopsPerGB: "3000"
  encrypted: "true"
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

3. **Crear Headless Service**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: db-cluster
spec:
  clusterIP: None
  selector:
    app: database
    ports:
      - port: 3306
    name: db
```

4. **Administrar la configuración con ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: db-config
data:
  my.cnf: |
    [mysqld]
    server-id = ${HOSTNAME##*-}
    log_bin = /var/lib/mysql/mysql-bin.log
    binlog_format = ROW
    sync_binlog = 1
    innodb_flush_log_at_trx_commit = 1
```

5. **Definición de StatefulSet**:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db-cluster
spec:
  serviceName: db-cluster
  replicas: 3
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      initContainers:
        - name: init-config
          image: busybox
          command: ['sh', '-c', 'cp /config-map/my.cnf /etc/mysql/conf.d/']
          volumeMounts:
            - name: config-map
              mountPath: /config-map
            - name: config-dir
              mountPath: /etc/mysql/conf.d/
      containers:
        - name: mysql
          image: mysql:8.0
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
          ports:
            - containerPort: 3306
              name: db
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
            - name: config-dir
              mountPath: /etc/mysql/conf.d/
          readinessProbe:
            exec:
              command: ["mysql", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}", "-e", "SELECT 1"]
            initialDelaySeconds: 30
            periodSeconds: 10
      volumes:
        - name: config-map
          configMap:
            name: db-config
        - name: config-dir
          emptyDir: {}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ "ReadWriteOnce" ]
        storageClassName: "fast-storage"
        resources:
          requests:
            storage: 50Gi
```

**Estrategia de persistencia de datos y respaldo:**

1. **Garantizar la persistencia de datos**:
  - Usa `reclaimPolicy: Retain` para proteger los PV contra eliminaciones accidentales
  - Habilita la configuración de durabilidad en el motor de base de datos (por ejemplo, `sync_binlog=1` e `innodb_flush_log_at_trx_commit=1` de MySQL)
  - Garantiza la redundancia de datos mediante replicación

2. **Estrategia de respaldo**:
  - **Creación regular de VolumeSnapshot**:
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: db-snapshot-{{date}}
spec:
  volumeSnapshotClassName: csi-snapshot-class
  source:
    persistentVolumeClaimName: data-db-cluster-0
```

  - **Respaldo lógico de la base de datos**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: db-backup
spec:
  schedule: "0 2 * * *"  # Runs daily at 02:00
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: mysql:8.0
              command:
                - /bin/sh
                - -c
                - |
                  mysqldump -h db-cluster-0.db-cluster -u root -p"${MYSQL_ROOT_PASSWORD}" --all-databases > /backup/full-backup-$(date +%Y%m%d).sql
                  aws s3 cp /backup/full-backup-$(date +%Y%m%d).sql s3://my-backup-bucket/
              env:
                - name: MYSQL_ROOT_PASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: mysql-secret
                      key: password
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          volumes:
            - name: backup-volume
              emptyDir: {}
          restartPolicy: OnFailure
```

  - **Verificación de respaldos y pruebas de recuperación**: Realiza regularmente pruebas de recuperación desde respaldos para verificar la validez de los respaldos

3. **Estrategia de recuperación ante desastres**:
  - Distribuye los pods entre múltiples zonas de disponibilidad
  - Replica los respaldos entre regiones
  - Implementa procedimientos de recuperación automatizados

4. **Monitoreo y alertas**:
  - Configura alertas para éxito/fallo de jobs de respaldo
  - Monitorea el uso de almacenamiento
  - Monitorea el retraso de replicación

Este diseño combina los identificadores de red estables de StatefulSet con la persistencia de datos de PersistentVolume para proporcionar un cluster de base de datos de alta disponibilidad. La estrategia de respaldo en múltiples capas evita la pérdida de datos en varios escenarios de fallo.
</details>

## Conclusion

A través de este cuestionario, evaluaste tu comprensión de los conceptos de almacenamiento de Kubernetes. Cubrimos conceptos como volúmenes persistentes, reclamaciones de volúmenes persistentes, clases de almacenamiento, tipos de volúmenes, modos de acceso y políticas de reclamación. También exploramos temas avanzados como la configuración de almacenamiento en AWS EKS, drivers CSI y snapshots de volúmenes. Comprender y utilizar estos conceptos te permite crear soluciones de almacenamiento confiables y escalables en Kubernetes.
