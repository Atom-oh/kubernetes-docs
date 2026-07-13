# Cuestionario de almacenamiento de EKS - Parte 2

Este cuestionario evalúa tu comprensión de conceptos avanzados de almacenamiento en Amazon EKS, incluida la optimización del almacenamiento, las estrategias de copia de seguridad y recuperación, y las soluciones de almacenamiento para diversas cargas de trabajo.

## Preguntas de opción múltiple

### 1. ¿Cuál es el método más efectivo para crear PersistentVolumeClaims cuando se usa StatefulSet en Amazon EKS?

A. Crear PVCs manualmente para cada pod B. Usar volumeClaimTemplates C. Usar ConfigMap para definir PVCs D. Deshabilitar el aprovisionamiento dinámico

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar volumeClaimTemplates**

**Explicación:** El método más efectivo para crear PersistentVolumeClaims (PVCs) cuando se usa StatefulSet en Amazon EKS es usar `volumeClaimTemplates`. Este método crea automáticamente PVCs únicos para cada pod en el StatefulSet, y se administran independientemente del ciclo de vida del pod.

**Características clave de volumeClaimTemplates:**

1.  **Creación automática de PVC**: Se crean automáticamente PVCs únicos para cada pod en el StatefulSet.

    ```yaml
    volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ "ReadWriteOnce" ]
        storageClassName: ebs-sc
        resources:
          requests:
            storage: 10Gi
    ```
2. **Almacenamiento estable**: El mismo PVC se reutiliza incluso cuando un pod se reinicia o se reprograma.
3. **Convención de nombres**: Los nombres de PVC se crean con el formato `<volumeClaimTemplate-name>-<statefulset-name>-<ordinal>`. Ejemplo: `data-mysql-0`, `data-mysql-1`, `data-mysql-2`
4. **Deployment secuencial**: StatefulSet crea y elimina pods secuencialmente, por lo que las operaciones de almacenamiento también se procesan secuencialmente.

**Ejemplo de StatefulSet:**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 3
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:5.7
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 10Gi
```

**Beneficios de volumeClaimTemplates:**

1. **Automatización**: No es necesario crear ni administrar PVCs manualmente.
2. **Escalabilidad**: Los PVCs se crean automáticamente al ajustar las réplicas del StatefulSet.
3. **Persistencia de datos**: Los PVCs y los datos se conservan incluso cuando los pods se eliminan.
4. **Garantía de orden**: Se garantiza el orden de creación y eliminación de pods y PVCs.

**Precauciones:**

1.  **Política de eliminación de PVC**: Los PVCs no se eliminan automáticamente cuando se elimina el StatefulSet. Esto está diseñado para evitar la pérdida de datos.

    ```bash
    # Check PVCs after StatefulSet deletion
    kubectl get pvc -l app=mysql

    # Manually delete PVCs if needed
    kubectl delete pvc data-mysql-0 data-mysql-1 data-mysql-2
    ```
2. **Selección de Storage Class**: Selecciona una storage class adecuada para cumplir con los requisitos de la carga de trabajo.
   * EBS: Acceso de un solo nodo (RWO)
   * EFS: Acceso de múltiples nodos (RWX)
3.  **Volume Binding Mode**: Usa `WaitForFirstConsumer` para garantizar que los volúmenes se creen en la availability zone donde se programa el pod.

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```

Problemas con las otras opciones:

* **A. Crear PVCs manualmente para cada pod**: La creación manual es propensa a errores, carece de escalabilidad y no aprovecha los beneficios de automatización de StatefulSet.
* **C. Usar ConfigMap para definir PVCs**: ConfigMap se usa para almacenar datos de configuración y no se puede usar directamente para crear PVCs.
* **D. Deshabilitar el aprovisionamiento dinámico**: Deshabilitar el aprovisionamiento dinámico aumenta la sobrecarga de administración, ya que los PVCs deben crearse manualmente.

</details>

### 2. ¿Cuál es el método más efectivo para optimizar el rendimiento de volúmenes EBS en Amazon EKS?

A. Usar el tipo provisioned IOPS (io1) para todos los volúmenes EBS B. Seleccionar tipos de volumen EBS adecuados según los requisitos de la carga de trabajo C. Aprovisionar el tamaño máximo para todos los volúmenes EBS D. Colocar todos los pods en la misma availability zone

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B. Seleccionar tipos de volumen EBS adecuados según los requisitos de la carga de trabajo**

**Explicación:** El método más efectivo para optimizar el rendimiento de volúmenes EBS en Amazon EKS es seleccionar tipos de volumen EBS adecuados según los requisitos de la carga de trabajo. Cada tipo de volumen EBS tiene diferentes características de rendimiento y estructuras de costos, por lo que es importante elegir el tipo de volumen que coincida con las características de tu carga de trabajo.

**Principales tipos de volumen EBS y características:**

1.  **gp3 (General Purpose SSD)**:

    * Rendimiento base: 3,000 IOPS, 125MB/s de throughput
    * Rendimiento máximo: 16,000 IOPS, 1,000MB/s de throughput
    * Casos de uso: Volúmenes de arranque, entornos de desarrollo y prueba, bases de datos pequeñas a medianas

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-gp3
    provisioner: ebs.csi.aws.com
    parameters:
      type: gp3
      iops: "8000"
      throughput: "500"
    ```
2.  **io1/io2 (Provisioned IOPS SSD)**:

    * Rendimiento máximo: 64,000 IOPS, 1,000MB/s de throughput
    * Casos de uso: Bases de datos intensivas en I/O, cargas de trabajo sensibles a la latencia

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-io2
    provisioner: ebs.csi.aws.com
    parameters:
      type: io2
      iops: "25000"
    ```
3.  **st1 (Throughput Optimized HDD)**:

    * Rendimiento máximo: 500 IOPS, 500MB/s de throughput
    * Casos de uso: Big data, data warehouses, procesamiento de logs

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-st1
    provisioner: ebs.csi.aws.com
    parameters:
      type: st1
    ```
4.  **sc1 (Cold HDD)**:

    * Rendimiento máximo: 250 IOPS, 250MB/s de throughput
    * Casos de uso: Datos de acceso poco frecuente, archivos

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc1
    provisioner: ebs.csi.aws.com
    parameters:
      type: sc1
    ```

**Selección óptima del tipo de volumen por carga de trabajo:**

1.  **Cargas de trabajo de bases de datos**:

    * Se necesita alto rendimiento: io2 o gp3 de alto rendimiento
    * Se necesita rendimiento medio: gp3

    ```yaml
    # StorageClass for high-performance database
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: database-storage
    provisioner: ebs.csi.aws.com
    parameters:
      type: io2
      iops: "25000"
    volumeBindingMode: WaitForFirstConsumer
    ```
2.  **Cargas de trabajo de logs y streaming**:

    * Se necesita alto throughput: st1 o gp3 de alto throughput

    ```yaml
    # StorageClass for log processing
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: log-storage
    provisioner: ebs.csi.aws.com
    parameters:
      type: st1
    volumeBindingMode: WaitForFirstConsumer
    ```
3.  **Servidores web y de aplicaciones**:

    * Se necesita rendimiento medio: gp3

    ```yaml
    # StorageClass for web servers
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: web-storage
    provisioner: ebs.csi.aws.com
    parameters:
      type: gp3
      iops: "3000"
      throughput: "125"
    volumeBindingMode: WaitForFirstConsumer
    ```

**Estrategias adicionales de optimización del rendimiento:**

1. **Optimización del tamaño del volumen**: Algunos tipos de volumen (por ejemplo, gp2) escalan el rendimiento según el tamaño.
2. **Consideración del tipo de instancia**: Usa instancias optimizadas para EBS para asegurar ancho de banda dedicado para volúmenes EBS.
3.  **Configuración RAID**: Configura múltiples volúmenes EBS en RAID 0 para mejorar el rendimiento

    ```yaml
    # RAID configuration within pod
    apiVersion: v1
    kind: Pod
    metadata:
      name: raid-pod
    spec:
      containers:
      - name: raid-container
        image: ubuntu:latest
        command: ["/bin/bash", "-c"]
        args:
        - |
          apt-get update && apt-get install -y mdadm
          mdadm --create --verbose /dev/md0 --level=0 --raid-devices=2 /dev/xvdf /dev/xvdg
          mkfs.ext4 /dev/md0
          mount /dev/md0 /data
          # Run application
        volumeMounts:
        - name: vol1
          mountPath: /dev/xvdf
        - name: vol2
          mountPath: /dev/xvdg
        - name: raid-mount
          mountPath: /data
      volumes:
      - name: vol1
        persistentVolumeClaim:
          claimName: ebs-claim-1
      - name: vol2
        persistentVolumeClaim:
          claimName: ebs-claim-2
      - name: raid-mount
        emptyDir: {}
    ```
4. **Optimización del sistema de archivos**: Selecciona y optimiza el sistema de archivos adecuado para la carga de trabajo
   * XFS: Adecuado para archivos grandes y I/O paralelo
   * ext4: Adecuado para propósitos generales
5. **Monitoreo y ajuste**: Monitorea métricas de CloudWatch y ajusta el tipo o la configuración del volumen según sea necesario

Problemas con las otras opciones:

* **A. Usar el tipo provisioned IOPS (io1) para todos los volúmenes EBS**: Usar provisioned IOPS para todas las cargas de trabajo no es rentable, y algunas cargas de trabajo pueden ser más adecuadas para otros tipos de volumen.
* **C. Aprovisionar el tamaño máximo para todos los volúmenes EBS**: Aprovisionar volúmenes más grandes de lo necesario genera costos innecesarios.
* **D. Colocar todos los pods en la misma availability zone**: Esto compromete la alta disponibilidad, y toda la aplicación puede verse afectada por una falla de una sola availability zone.

</details>

### 4. ¿Cuál es el principal beneficio de usar FSx for Lustre en Amazon EKS?

A. Eficiencia de costos B. Configuración simple C. Sistema de archivos paralelo de alto rendimiento D. Integración nativa con EKS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C. Sistema de archivos paralelo de alto rendimiento**

**Explicación:** El principal beneficio de usar FSx for Lustre en Amazon EKS es que proporciona un sistema de archivos paralelo de alto rendimiento. FSx for Lustre es un sistema de archivos completamente administrado diseñado para cargas de trabajo intensivas en cómputo, como high-performance computing (HPC), machine learning y análisis de big data, que ofrece cientos de GB/s de throughput, millones de IOPS y latencia inferior al milisegundo.

**Características clave de rendimiento de FSx for Lustre:**

1. **Alto throughput**:
   * Hasta 1,000GB/s de throughput
   * Hasta 200MB/s de throughput por 1TiB de almacenamiento (basado en SSD)
   * Adecuado para procesar grandes conjuntos de datos
2. **Baja latencia**:
   * Latencia inferior al milisegundo
   * Adecuado para aplicaciones sensibles a la latencia
3. **Acceso paralelo**:
   * Acceso simultáneo desde miles de instancias de cómputo
   * Mejora del rendimiento mediante procesamiento paralelo
4. **Escalabilidad**:
   * Escala a cientos de GB/s de throughput
   * Soporta conjuntos de datos a escala de petabytes

**Integración de FSx for Lustre con EKS:**

1.  **CSI Driver**:

    ```bash
    # Install FSx for Lustre CSI driver
    helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
    helm repo update
    helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
      --namespace kube-system \
      --set controller.serviceAccount.create=true \
      --set controller.serviceAccount.name=fsx-csi-controller-sa
    ```
2.  **Configuración de StorageClass**:

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
      perUnitStorageThroughput: "200"
      dataCompressionType: "LZ4"
    mountOptions:
      - flock
    ```
3.  **Creación de PersistentVolumeClaim**:

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: fsx-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: fsx-lustre
      resources:
        requests:
          storage: 1200Gi  # Minimum 1.2TiB
    ```

**Cargas de trabajo adecuadas para FSx for Lustre:**

1. **Machine Learning y Deep Learning**:
   * Entrenamiento con grandes conjuntos de datos
   * Jobs de entrenamiento distribuido
   * Serving de modelos
2. **High-Performance Computing (HPC)**:
   * Simulaciones científicas
   * Pronóstico del tiempo
   * Genómica
3. **Análisis de Big Data**:
   * Procesamiento de datos a gran escala
   * Analítica en tiempo real
   * Jobs ETL
4. **Procesamiento de medios**:
   * Renderizado de video
   * Procesamiento de imágenes
   * Creación de contenido

**Integración con S3:**

FSx for Lustre se integra sin problemas con Amazon S3, lo que facilita importar y procesar datos de S3 con el sistema de archivos de alto rendimiento.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-s3
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  perUnitStorageThroughput: "200"
  s3ImportPath: s3://my-bucket/prefix
  s3ExportPath: s3://my-bucket/export
```

**Opciones de tipo de Deployment:**

1. **SCRATCH\_1**:
   * Almacenamiento temporal y procesamiento a corto plazo
   * Rentable
   * Sin replicación de datos
2. **SCRATCH\_2**:
   * Almacenamiento temporal y procesamiento a corto plazo
   * Replicación de datos en caso de falla del servidor
   * Mejor disponibilidad que SCRATCH\_1
3. **PERSISTENT**:
   * Almacenamiento a largo plazo y cargas de trabajo
   * Replicación de datos y recuperación automática
   * Alta durabilidad

**Consejos de optimización del rendimiento:**

1. **Selección adecuada de throughput**:
   * Almacenamiento SSD: 50, 100, 200 MB/s/TiB
   * Almacenamiento HDD: 12, 40 MB/s/TiB
2. **Habilitar compresión de datos**:
   * Mejor eficiencia de almacenamiento mediante compresión LZ4
   * Menor uso de ancho de banda de red
3. **Optimización del tamaño del sistema de archivos**:
   * Los sistemas de archivos más grandes proporcionan más servidores y mayor rendimiento agregado
4.  **Optimización de opciones de mount**:

    ```
    mount -t lustre -o noatime,flock file_system_dns_name@tcp:/mountname /mnt/fsx
    ```

Problemas con las otras opciones:

* **A. Eficiencia de costos**: FSx for Lustre proporciona alto rendimiento, pero generalmente es más caro que EBS o EFS.
* **B. Configuración simple**: FSx for Lustre requiere opciones de configuración avanzadas y tiene una configuración más compleja que EBS o EFS.
* **D. Integración nativa con EKS**: FSx for Lustre no está integrado de forma nativa con EKS; el CSI driver debe instalarse por separado.

</details>

## Preguntas de respuesta corta

### 6. ¿Qué configuración RAID se puede usar para mejorar el rendimiento de volúmenes EBS en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** RAID 0 (Striping)

**Explicación detallada:**

La configuración RAID que se puede usar para mejorar el rendimiento de volúmenes EBS en Amazon EKS es RAID 0 (striping). RAID 0 distribuye datos entre múltiples volúmenes EBS para mejorar el rendimiento de I/O.

**Cómo funciona RAID 0:**

RAID 0 almacena datos distribuyéndolos entre múltiples discos, y cada disco maneja una parte de la carga total de I/O, mejorando así el rendimiento general. Por ejemplo, configurar RAID 0 con 2 volúmenes EBS puede, en teoría, duplicar el throughput y los IOPS.

**Características clave de RAID 0:**

1. **Mejora del rendimiento**: Las operaciones de I/O se procesan en paralelo entre múltiples volúmenes, lo que aumenta el throughput y los IOPS.
2. **Agregación de capacidad**: La capacidad de todos los volúmenes se agrega y se usa como un único volumen grande.
3. **Sin tolerancia a fallos**: Si un volumen falla, se pierden todos los datos de todo el arreglo RAID.

**Cómo configurar RAID 0 en EKS:**

1.  **Crear múltiples PVCs:**

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim-1
    spec:
      accessModes:
        - ReadWriteOnce
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 100Gi
    ---
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim-2
    spec:
      accessModes:
        - ReadWriteOnce
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 100Gi
    ```
2.  **Configurar RAID 0 en Pod:**

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: raid0-pod
    spec:
      containers:
      - name: raid-container
        image: ubuntu:latest
        command: ["/bin/bash", "-c"]
        args:
        - |
          apt-get update && apt-get install -y mdadm
          mdadm --create --verbose /dev/md0 --level=0 --raid-devices=2 /dev/xvdf /dev/xvdg
          mkfs.ext4 /dev/md0
          mount /dev/md0 /data
          # Run application
          while true; do sleep 30; done
        volumeMounts:
        - name: vol1
          mountPath: /dev/xvdf
        - name: vol2
          mountPath: /dev/xvdg
        - name: raid-mount
          mountPath: /data
        securityContext:
          privileged: true  # Permissions required for RAID configuration
      volumes:
      - name: vol1
        persistentVolumeClaim:
          claimName: ebs-claim-1
      - name: vol2
        persistentVolumeClaim:
          claimName: ebs-claim-2
      - name: raid-mount
        emptyDir: {}
    ```

**Consejos de optimización del rendimiento de RAID 0:**

1. **Número de volúmenes**: Normalmente, 2-4 volúmenes proporcionan un rendimiento óptimo. Demasiados volúmenes pueden aumentar la sobrecarga de administración.
2. **Tamaño del volumen**: Configura todos los volúmenes con el mismo tamaño para distribuir uniformemente el rendimiento.
3. **Tamaño de stripe**: Selecciona un tamaño de stripe adecuado según la carga de trabajo.
   * I/O aleatorio pequeño: Tamaño de stripe pequeño (por ejemplo, 4KB)
   * I/O secuencial grande: Tamaño de stripe grande (por ejemplo, 64KB o 128KB)
4. **Tipo de instancia**: Usa instancias optimizadas para EBS para asegurar ancho de banda dedicado para volúmenes EBS.

**Casos de uso de RAID 0:**

1. **Bases de datos de alto rendimiento**: Cargas de trabajo de bases de datos que requieren IOPS y throughput altos
2. **Procesamiento de Big Data**: Cargas de trabajo de procesamiento y análisis de datos a gran escala
3. **Procesamiento de medios**: Tareas intensivas en I/O como codificación/decodificación de video y renderizado

**Precauciones:**

1. **Durabilidad de los datos**: RAID 0 no tiene tolerancia a fallos, por lo que se necesita una estrategia de backup adecuada para datos importantes.
2. **Falla de volumen**: Si un volumen falla, todos los datos pueden perderse, por lo que son importantes los backups regulares mediante snapshots.
3. **Complejidad**: La configuración RAID aumenta la complejidad de administración, así que úsala solo cuando realmente sea necesario.
4. **Costo**: Usar múltiples volúmenes EBS aumenta los costos de almacenamiento.

**Consideraciones alternativas:**

1. **Volumen único de alto rendimiento**: Usa volúmenes io2 o gp3 de alto rendimiento para mayor simplicidad
2. **Instance Store**: Considera volúmenes instance store para datos temporales
3. **FSx for Lustre**: Considera un sistema de archivos paralelo cuando se requiere un rendimiento muy alto

RAID 0 es una forma efectiva de mejorar el rendimiento de volúmenes EBS, pero debe usarse con cuidado teniendo en cuenta la durabilidad de los datos y la complejidad de administración.

</details>

### 7. ¿Qué opciones de mount se pueden usar para establecer tamaños de búfer de lectura y escritura para optimizar el rendimiento del sistema de archivos EFS en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** rsize y wsize

**Explicación detallada:**

Las opciones de mount que se pueden usar para establecer tamaños de búfer de lectura y escritura para optimizar el rendimiento del sistema de archivos EFS en Amazon EKS son `rsize` (tamaño de búfer de lectura) y `wsize` (tamaño de búfer de escritura). Estas opciones determinan el tamaño de los bloques de datos usados cuando los clientes NFS se comunican con el sistema de archivos EFS.

**Rol de rsize y wsize:**

1. **rsize (Read Buffer Size)**:
   * Número máximo de bytes usados cuando el cliente NFS lee desde el servidor
   * Los valores más grandes permiten leer más datos con menos solicitudes de red
   * El valor predeterminado suele ser 1MB (1048576 bytes)
2. **wsize (Write Buffer Size)**:
   * Número máximo de bytes usados cuando el cliente NFS escribe en el servidor
   * Los valores más grandes permiten escribir más datos con menos solicitudes de red
   * El valor predeterminado suele ser 1MB (1048576 bytes)

**Configuración de rsize y wsize en EKS:**

1.  **Configuración en StorageClass:**

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc-optimized
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    mountOptions:
      - rsize=1048576
      - wsize=1048576
    ```
2.  **Configuración en PersistentVolume:**

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
      mountOptions:
        - rsize=1048576
        - wsize=1048576
      csi:
        driver: efs.csi.aws.com
        volumeHandle: fs-0123456789abcdef0
    ```

**Selección de valores óptimos:**

1. **Valores generales recomendados**:
   * rsize=1048576 (1MB)
   * wsize=1048576 (1MB)
2. **Optimización específica de la carga de trabajo**:
   * Lectura/escritura secuencial grande: Valores más grandes (por ejemplo, 1MB)
   * Lectura/escritura aleatoria pequeña: Valores más pequeños (por ejemplo, 32KB o 64KB)
3. **Consideración de las condiciones de red**:
   * Red estable: Valores más grandes
   * Red inestable: Valores más pequeños (reduce la sobrecarga de retransmisión ante pérdida de paquetes)

**Opciones adicionales de mount para optimización del rendimiento:**

1.  **timeo**: Tiempo de espera de respuesta del servidor (en unidades de 1/10 de segundo)

    ```
    timeo=600  # 60 seconds
    ```
2.  **retrans**: Número de reintentos antes del timeout

    ```
    retrans=2
    ```
3.  **noresvport**: Usar un nuevo puerto TCP en la recuperación de conexión

    ```
    noresvport
    ```
4.  **noatime**: Deshabilitar actualizaciones de tiempo de acceso a archivos

    ```
    noatime
    ```

**Ejemplo completo de opciones de mount optimizadas:**

```yaml
mountOptions:
  - rsize=1048576
  - wsize=1048576
  - timeo=600
  - retrans=2
  - noresvport
  - noatime
```

**Monitoreo y ajuste del rendimiento:**

1.  **Medición del rendimiento**:

    ```bash
    # Read performance test
    dd if=/efs/testfile of=/dev/null bs=1M count=1000

    # Write performance test
    dd if=/dev/zero of=/efs/testfile bs=1M count=1000
    ```
2. **Monitoreo de métricas de CloudWatch**:
   * TotalIOBytes
   * DataReadIOBytes
   * DataWriteIOBytes
   * MetadataIOBytes
3. **Ajuste gradual**:
   * Prueba con varios valores de rsize/wsize
   * Selecciona valores óptimos según los patrones de la carga de trabajo

Configurar correctamente las opciones rsize y wsize puede mejorar significativamente el rendimiento del sistema de archivos EFS, especialmente para cargas de trabajo que implican transferencias de archivos grandes o requisitos de alto throughput.

</details>

### 9. ¿Cuál es el SLA (Service Level Agreement) de AWS para la durabilidad de los datos al usar volúmenes EBS en Amazon EKS?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:** 99.999% (5 nueves)

**Explicación detallada:**

El SLA (Service Level Agreement) de AWS para la durabilidad de los datos al usar volúmenes EBS en Amazon EKS es 99.999% (5 nueves). Esto significa que Amazon EBS tiene una probabilidad de pérdida anual de datos inferior al 0.001%.

**Características clave de la durabilidad de EBS:**

1. **Durabilidad de diseño**: Los volúmenes de Amazon EBS están diseñados para proporcionar una durabilidad del 99.999%.
2. **Replicación en Availability Zone**: Los datos de volúmenes EBS se replican automáticamente entre múltiples servidores dentro de una sola availability zone.
3. **Tasa anual de fallas (AFR)**: Apunta a un rango de tasa anual de fallas del 0.1% - 0.2%.

**Durabilidad por tipo de volumen EBS:**

Todos los tipos de volumen EBS (gp2, gp3, io1, io2, st1, sc1) tienen el mismo diseño de durabilidad del 99.999%. Sin embargo, los volúmenes io2 proporcionan garantías adicionales de durabilidad:

* **io2 Block Express**: SLA de disponibilidad del 99.999% además de durabilidad del 99.999%

**Métodos de mejora de protección de datos:**

1.  **EBS Snapshots**:

    * Backup de datos mediante snapshots regulares
    * Los snapshots se almacenan en S3 con una durabilidad del 99.999999999% (11 nueves)

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshotClass
    metadata:
      name: ebs-snapshot-class
    driver: ebs.csi.aws.com
    deletionPolicy: Retain
    ```
2.  **Copia de snapshots entre regiones**:

    * Copiar snapshots a diferentes regiones para disaster recovery

    ```bash
    aws ec2 copy-snapshot \
      --source-region us-west-2 \
      --source-snapshot-id snap-0123456789abcdef0 \
      --destination-region us-east-1 \
      --description "Cross-region backup"
    ```
3.  **Políticas de backup automatizado**:

    * Backups automatizados usando Amazon Data Lifecycle Manager o Kubernetes CronJob

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: ebs-snapshot-job
    spec:
      schedule: "0 0 * * *"  # Daily at midnight
      jobTemplate:
        spec:
          template:
            spec:
              containers:
              - name: snapshot-creator
                image: amazon/aws-cli:latest
                command:
                - /bin/sh
                - -c
                - |
                  # Get volume ID from PVC
                  VOLUME_ID=$(kubectl get pvc my-pvc -o jsonpath='{.spec.volumeName}' | xargs kubectl get pv -o jsonpath='{.spec.csi.volumeHandle}')
                  # Create snapshot
                  aws ec2 create-snapshot --volume-id $VOLUME_ID --description "Daily backup"
              restartPolicy: OnFailure
    ```

**Escenarios de falla de volúmenes EBS y recuperación:**

1. **Corrupción de volumen**:
   * Síntomas: Errores de I/O, degradación del rendimiento
   * Recuperación: Crear un nuevo volumen desde el snapshot más reciente
2. **Falla de Availability Zone**:
   * Síntomas: Volumen inaccesible
   * Recuperación: Restaurar el volumen desde un snapshot en una availability zone diferente
3. **Eliminación accidental de datos**:
   * Recuperación: Restaurar a un punto específico en el tiempo desde un snapshot

**Mejores prácticas de durabilidad de EBS:**

1. **Snapshots regulares**:
   * Crear snapshots diarios o más frecuentes para datos importantes
   * Implementar políticas de retención de snapshots
2. **Pruebas de snapshots**:
   * Probar regularmente la restauración desde snapshots
   * Documentar y practicar procesos de recuperación
3. **Estrategia multirregión**:
   * Copiar snapshots a diferentes regiones para datos críticos
   * Establecer planes de disaster recovery
4. **Monitoreo y alertas**:
   * Monitorear el estado de volúmenes EBS
   * Configurar alarmas de CloudWatch

**Comparación de durabilidad de EBS frente a otros servicios de almacenamiento de AWS:**

| Service        | Durability             | Availability                   |
| -------------- | ---------------------- | ------------------------------ |
| Amazon EBS     | 99.999%                | 99.95-99.999% (varies by type) |
| Amazon EFS     | 99.999999999% (11 9's) | 99.99%                         |
| Amazon S3      | 99.999999999% (11 9's) | 99.99%                         |
| FSx for Lustre | 99.999%                | 99.95%                         |

La durabilidad del 99.999% de Amazon EBS proporciona protección de datos suficiente para la mayoría de las cargas de trabajo, pero para datos críticos se recomienda implementar capas adicionales de protección mediante snapshots regulares y estrategias de backup multirregión.

</details>

## Preguntas prácticas

### 10. Diseña una solución de almacenamiento de alto rendimiento para cargas de trabajo de bases de datos en un cluster de Amazon EKS. Crea storage classes, persistent volume claims y StatefulSet que cumplan los siguientes requisitos:

* Base de datos PostgreSQL que requiere IOPS altos
* Funcionalidad automática de backup y recuperación
* Capacidad de expansión de volumen

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

Así se puede diseñar una solución de almacenamiento de alto rendimiento para cargas de trabajo de bases de datos en un cluster de Amazon EKS:

### 1. Definición de StorageClass de alto rendimiento

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: io2
  iops: "25000"  # High IOPS provision
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:region:account-id:key/key-id"  # Optional: Encryption with KMS key
allowVolumeExpansion: true  # Allow volume expansion
reclaimPolicy: Retain  # Retain PV on PVC deletion
```

### 2. Definición de StatefulSet de PostgreSQL

```yaml
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
  template:
    metadata:
      labels:
        app: postgres
    spec:
      securityContext:
        fsGroup: 999  # PostgreSQL group ID
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        ports:
        - containerPort: 5432
          name: postgres
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 15
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: postgres-io2
      resources:
        requests:
          storage: 100Gi
```

### 3. Definición de Service de PostgreSQL

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None  # Headless service
```

### 4. VolumeSnapshotClass y CronJob para backups automatizados

```yaml
# VolumeSnapshotClass Definition
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: postgres-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain
parameters:
  # Enable snapshot encryption
  encrypted: "true"
  # Add snapshot tags
  tagSpecification_0_resourceType: "snapshot"
  tagSpecification_0_tags_Purpose: "PostgreSQL Backup"
  tagSpecification_0_tags_Environment: "Production"

# CronJob for automated backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: database
spec:
  schedule: "0 1 * * *"  # Daily at 1 AM
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: postgres-backup-sa  # Service account with appropriate permissions
          containers:
          - name: snapshot-creator
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              # Create snapshot name based on current date
              SNAPSHOT_NAME="postgres-snapshot-$(date +%Y%m%d-%H%M%S)"

              # Create snapshot
              cat <<EOF | kubectl apply -f -
              apiVersion: snapshot.storage.k8s.io/v1
              kind: VolumeSnapshot
              metadata:
                name: $SNAPSHOT_NAME
                namespace: database
              spec:
                volumeSnapshotClassName: postgres-snapshot-class
                source:
                  persistentVolumeClaimName: data-postgres-0
              EOF

              # Delete snapshots older than 30 days
              kubectl get volumesnapshot -n database -o json | \
                jq -r '.items[] | select(.metadata.name | startswith("postgres-snapshot-")) |
                select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) |
                .metadata.name' | \
                xargs -r kubectl delete volumesnapshot -n database
          restartPolicy: OnFailure
```

### 5. Script de automatización de expansión de volumen

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-volume-monitor
  namespace: database
spec:
  schedule: "0 */6 * * *"  # Run every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: postgres-volume-monitor-sa
          containers:
          - name: volume-monitor
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              # Get PostgreSQL pod name
              POD_NAME=$(kubectl get pods -n database -l app=postgres -o jsonpath='{.items[0].metadata.name}')

              # Check volume usage
              USAGE_PERCENT=$(kubectl exec -n database $POD_NAME -- df -h /var/lib/postgresql/data | tail -1 | awk '{print $5}' | sed 's/%//')

              # Expand volume if usage is 80% or higher
              if [ $USAGE_PERCENT -ge 80 ]; then
                # Get current PVC size
                CURRENT_SIZE=$(kubectl get pvc data-postgres-0 -n database -o jsonpath='{.spec.resources.requests.storage}')

                # Increase by 50% from current size
                NEW_SIZE=$(echo $CURRENT_SIZE | sed 's/Gi//' | awk '{print int($1 * 1.5)}')

                # Expand PVC
                kubectl patch pvc data-postgres-0 -n database -p "{\"spec\":{\"resources\":{\"requests\":{\"storage\":\"${NEW_SIZE}Gi\"}}}}"

                # Log message
                echo "$(date): Volume expanded from ${CURRENT_SIZE} to ${NEW_SIZE}Gi due to high usage (${USAGE_PERCENT}%)"
              fi
          restartPolicy: OnFailure
```

### 6. Plantilla de Job para procedimientos de recuperación

```yaml
# Job template for recovering from snapshot
apiVersion: batch/v1
kind: Job
metadata:
  name: postgres-restore
  namespace: database
spec:
  template:
    spec:
      serviceAccountName: postgres-restore-sa
      containers:
      - name: restore-manager
        image: bitnami/kubectl:latest
        command:
        - /bin/bash
        - -c
        - |
          # 1. Scale down StatefulSet
          kubectl scale statefulset postgres -n database --replicas=0

          # 2. Delete existing PVC (caution: data will be lost)
          kubectl delete pvc data-postgres-0 -n database

          # 3. Create PVC from snapshot
          cat <<EOF | kubectl apply -f -
          apiVersion: v1
          kind: PersistentVolumeClaim
          metadata:
            name: data-postgres-0
            namespace: database
          spec:
            accessModes:
              - ReadWriteOnce
            storageClassName: postgres-io2
            resources:
              requests:
                storage: 100Gi
            dataSource:
              name: ${SNAPSHOT_NAME}  # Snapshot name to restore
              kind: VolumeSnapshot
              apiGroup: snapshot.storage.k8s.io
          EOF

          # 4. Scale up StatefulSet
          kubectl scale statefulset postgres -n database --replicas=1

          # 5. Check recovery status
          sleep 60
          kubectl get pods -n database -l app=postgres
      restartPolicy: OnFailure
```

### 7. Configuración de monitoreo y alertas

```yaml
# ServiceMonitor for PostgreSQL metrics collection (assuming Prometheus)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-monitor
  namespace: database
spec:
  selector:
    matchLabels:
      app: postgres
  endpoints:
  - port: postgres
    interval: 15s
  namespaceSelector:
    matchNames:
    - database
```

### Explicación del diseño

#### 1. Selección de almacenamiento de alto rendimiento

* **Tipo de volumen io2**: Tipo de volumen EBS optimizado para cargas de trabajo de bases de datos que requieren IOPS altos
* **25,000 IOPS**: Aprovisionamiento de IOPS suficiente para operaciones de bases de datos de alto rendimiento
* **Cifrado**: Habilita el cifrado de volúmenes EBS para seguridad de datos en reposo

#### 2. Beneficios de usar StatefulSet

* **ID de red estable**: Proporciona nombres DNS predecibles para cada pod
* **Deployment secuencial**: Garantiza actualizaciones seguras para pods de base de datos
* **Administración de volúmenes**: Creación y administración automática de PVC mediante volumeClaimTemplates

#### 3. Estrategia de backup automatizado

* **Snapshots regulares**: Creación automatizada diaria de snapshots
* **Política de retención**: Eliminación automática de snapshots con más de 30 días
* **Etiquetado**: Añade tags a los snapshots para mejorar la capacidad de administración

#### 4. Automatización de expansión de volumen

* **Monitoreo de uso**: Comprobaciones regulares del uso del volumen
* **Expansión automática**: Aumenta automáticamente el tamaño del volumen cuando el uso alcanza el 80% o más
* **allowVolumeExpansion**: Habilita la expansión de volumen en StorageClass

#### 5. Procedimientos de recuperación

* **Restauración basada en snapshots**: Crea un nuevo PVC desde un snapshot
* **Enfoque por fases**: Escala hacia abajo el StatefulSet, reemplaza el PVC, escala hacia arriba
* **Comprobación de estado**: Verifica el estado de la base de datos después de la recuperación

#### 6. Consideraciones de rendimiento y estabilidad

* **Resource Requests y Limits**: Asignación adecuada de CPU y memoria
* **Health checks**: Monitorea el estado de la base de datos mediante readinessProbe y livenessProbe
* **fsGroup**: Configura permisos adecuados del sistema de archivos

#### 7. Consideraciones de seguridad

* **Volúmenes cifrados**: Protegen los datos en reposo
* **Snapshots cifrados**: Protegen los datos de backup
* **Secrets**: Administración segura de credenciales de base de datos

Este diseño proporciona una solución de almacenamiento de alto rendimiento para bases de datos PostgreSQL que requieren IOPS altos, incluida funcionalidad automática de backup y recuperación, y capacidad de expansión de volumen. Además, la configuración de monitoreo y alertas permite la detección y respuesta proactivas ante problemas relacionados con el almacenamiento.

</details>
