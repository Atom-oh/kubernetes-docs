# Cuestionario de almacenamiento de EKS - Parte 3

Este cuestionario evalúa tu comprensión del monitoreo, la resolución de problemas, la optimización de costos y la seguridad del almacenamiento en Amazon EKS.

## Pregunta 1: Métricas de monitoreo de almacenamiento

<details>
<summary>¿Cuáles son las métricas clave para monitorear el rendimiento del almacenamiento en EKS?</summary>

**Respuesta:**
**Métricas de EBS:**
- VolumeReadOps/VolumeWriteOps: uso de IOPS
- VolumeReadBytes/VolumeWriteBytes: Throughput
- VolumeTotalReadTime/VolumeTotalWriteTime: Latencia
- VolumeQueueLength: Número de solicitudes de I/O pendientes
- BurstBalance: Saldo de créditos de burst

**Métricas de EFS:**
- DataReadIOBytes/DataWriteIOBytes: Volumen de transferencia de datos
- MetadataIOBytes: Volumen de operaciones de metadatos
- ClientConnections: Número de conexiones de clientes
- PercentIOLimit: Utilización del límite de I/O

**Métricas de Kubernetes:**
- kubelet_volume_stats_used_bytes: Uso del volumen
- kubelet_volume_stats_capacity_bytes: Capacidad del volumen
- container_fs_usage_bytes: Uso del sistema de archivos del contenedor
</details>

## Pregunta 2: Diagnóstico de problemas de almacenamiento

<details>
<summary>¿Qué deberías comprobar cuando un Pod en EKS está atascado en estado "Pending" y no puede montar un PVC?</summary>

**Respuesta:**
1. **Comprobar el estado del PVC**:
   ```bash
   kubectl get pvc
   kubectl describe pvc <pvc-name>
   ```

2. **Comprobar Storage Class**:
   ```bash
   kubectl get storageclass
   kubectl describe storageclass <storage-class-name>
   ```

3. **Comprobar el estado del CSI Driver**:
   ```bash
   kubectl get pods -n kube-system -l app=ebs-csi-controller
   kubectl logs -n kube-system -l app=ebs-csi-controller
   ```

4. **Comprobar permisos del nodo**:
   - Verifica los permisos de IAM requeridos en el perfil de instancia EC2
   - Verifica los permisos de la service account del EBS CSI driver

5. **Compatibilidad de Availability Zone**:
   - Verifica que el Pod y el volumen EBS estén en la misma AZ

6. **Límites de recursos**:
   - Límites de volúmenes EBS (volúmenes máximos por instancia)
   - Verifica los límites de tamaño del volumen
</details>

## Pregunta 3: Optimización del rendimiento

<details>
<summary>¿Cómo puedes optimizar el rendimiento del almacenamiento para cargas de trabajo de bases de datos en EKS?</summary>

**Respuesta:**
1. **Seleccionar el tipo de volumen adecuado**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: fast-ssd
   provisioner: ebs.csi.aws.com
   parameters:
     type: io2
     iops: "10000"
     encrypted: "true"
   volumeBindingMode: WaitForFirstConsumer
   ```

2. **Usar volúmenes Multi-Attach** (para cargas de trabajo de solo lectura):
   ```yaml
   parameters:
     type: io2
     multiAttach: "true"
   ```

3. **Utilizar Instance Store**:
   ```yaml
   # Instance store for temporary data
   volumeMounts:
   - name: instance-store
     mountPath: /tmp
   volumes:
   - name: instance-store
     hostPath:
       path: /mnt/instance-store
   ```

4. **Seleccionar el sistema de archivos adecuado**:
   - XFS: Archivos grandes y alta concurrencia
   - ext4: Propósito general
   - Configura opciones de mount adecuadas

5. **Optimización del I/O Scheduler**:
   ```bash
   # noop or deadline scheduler for SSD
   echo noop > /sys/block/nvme0n1/queue/scheduler
   ```
</details>

## Pregunta 4: Estrategias de optimización de costos

<details>
<summary>¿Qué estrategias se pueden usar para optimizar los costos de almacenamiento en EKS?</summary>

**Respuesta:**
1. **Seleccionar el tipo de volumen adecuado**:
   - gp3: Rentable para la mayoría de las cargas de trabajo
   - Migrar de gp2 a gp3
   - Usar provisioned IOPS solo cuando sea necesario

2. **Optimizar el tamaño del volumen**:
   ```bash
   # Monitor usage
   kubectl top pods --containers
   df -h # Inside pod
   ```

3. **Administración del ciclo de vida**:
   ```yaml
   # Snapshot automation
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: csi-aws-vsc
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

4. **Utilizar EFS Storage Classes**:
   ```yaml
   # Infrequent Access storage class
   parameters:
     performanceMode: generalPurpose
     throughputMode: provisioned
     provisionedThroughputInMibps: "100"
   ```

5. **Limpiar volúmenes no usados**:
   ```bash
   # Check unused PVs
   kubectl get pv | grep Available

   # Clean up old snapshots
   aws ec2 describe-snapshots --owner-ids self \
     --query 'Snapshots[?StartTime<=`2023-01-01`]'
   ```
</details>

## Pregunta 5: Mejores prácticas de seguridad

<details>
<summary>¿Cómo puedes mejorar la seguridad del almacenamiento en EKS?</summary>

**Respuesta:**
1. **Habilitar cifrado**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: encrypted-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     encrypted: "true"
     kmsKeyId: "arn:aws:kms:region:account:key/key-id"
   ```

2. **Minimizar permisos de IAM**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:CreateVolume",
           "ec2:AttachVolume",
           "ec2:DetachVolume",
           "ec2:DeleteVolume",
           "ec2:DescribeVolumes",
           "ec2:CreateSnapshot",
           "ec2:DeleteSnapshot",
           "ec2:DescribeSnapshots"
         ],
         "Resource": "*",
         "Condition": {
           "StringEquals": {
             "aws:RequestedRegion": "us-west-2"
           }
         }
       }
     ]
   }
   ```

3. **Seguridad de red**:
   ```yaml
   # EFS mount target security group
   securityGroupSelector:
     matchLabels:
       Name: "efs-mount-target-sg"
   ```

4. **Control de acceso**:
   ```yaml
   # RBAC configuration
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: storage-admin
   rules:
   - apiGroups: [""]
     resources: ["persistentvolumes", "persistentvolumeclaims"]
     verbs: ["get", "list", "create", "delete"]
   ```

5. **Registro de auditoría**:
   ```yaml
   # Storage-related audit policy
   - level: Metadata
     resources:
     - group: ""
       resources: ["persistentvolumes", "persistentvolumeclaims"]
   ```
</details>

### 6. ¿Cuál es la combinación de herramientas más efectiva para el monitoreo y la administración del almacenamiento en Amazon EKS?

A. Usar solo CloudWatch y AWS Console
B. CloudWatch, Prometheus, Grafana y herramientas de administración automatizada
C. Inspección manual y análisis de logs
D. Usar solo herramientas de monitoreo de terceros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. CloudWatch, Prometheus, Grafana y herramientas de administración automatizada**

**Explicación:**
La combinación de herramientas más efectiva para el monitoreo y la administración del almacenamiento en Amazon EKS es usar CloudWatch, Prometheus, Grafana y herramientas de administración automatizada en conjunto. Este enfoque integrado recopila tanto métricas nativas de AWS como métricas detalladas a nivel de Kubernetes, las visualiza y mejora la eficiencia operativa mediante administración automatizada.

**Arquitectura integrada de monitoreo y administración:**

1. **CloudWatch**:
   - Recopila métricas a nivel de infraestructura de AWS
   - Métricas de rendimiento de almacenamiento EBS, EFS y FSx
   - Administración de alarmas y eventos

2. **Prometheus**:
   - Recopila métricas detalladas a nivel de Kubernetes
   - Recopila métricas de almacenamiento personalizadas
   - Retención y consulta de datos a largo plazo

3. **Grafana**:
   - Dashboards integrados y visualización
   - Integración de fuentes de datos de CloudWatch y Prometheus
   - Alertas y reportes personalizados

4. **Herramientas de administración automatizada**:
   - Automatización del aprovisionamiento de almacenamiento
   - Planificación y escalado de capacidad
   - Detección y resolución de problemas
</details>

---

**Cálculo de puntuación:**
- 5-6 respuestas correctas: Excelente (nivel de experto en almacenamiento de EKS)
- 3-4 respuestas correctas: Bueno (se recomienda aprendizaje adicional)
- 1-2 respuestas correctas: Aceptable (se necesita repasar conceptos básicos)
- 0 respuestas correctas: Necesita mejorar (se requiere volver a estudiar todo el contenido)

**Ejemplos de implementación:**

1. **Configuración de CloudWatch Container Insights**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cwagent-config
     namespace: amazon-cloudwatch
   data:
     cwagentconfig.json: |
       {
         "logs": {
           "metrics_collected": {
             "kubernetes": {
               "cluster_name": "my-cluster",
               "metrics_collection_interval": 60
             }
           },
           "force_flush_interval": 5
         },
         "metrics": {
           "namespace": "EKS/Storage",
           "metrics_collected": {
             "statsd": {
               "service_address": ":8125"
             }
           }
         }
       }
   ```

2. **Configuración de Prometheus y Storage Exporter**:
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: storage-monitor
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: storage-exporter
     endpoints:
     - port: metrics
       interval: 30s
       path: /metrics
   ```

3. **Configuración de Grafana Dashboard**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: storage-dashboard
     namespace: monitoring
   data:
     storage-dashboard.json: |
       {
         "title": "EKS Storage Dashboard",
         "panels": [
           {
             "title": "EBS Volume IOPS",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "aws_ebs_volume_read_ops + aws_ebs_volume_write_ops",
                 "legendFormat": "{{volume_id}}"
               }
             ]
           },
           {
             "title": "EFS Throughput",
             "datasource": "CloudWatch",
             "targets": [
               {
                 "namespace": "AWS/EFS",
                 "metricName": "TotalIOBytes",
                 "dimensions": {
                   "FileSystemId": "*"
                 },
                 "statistic": "Sum"
               }
             ]
           }
         ]
       }
   ```

4. **CronJob de administración automatizada de almacenamiento**:
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: storage-manager
   spec:
     schedule: "0 1 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: storage-manager
               image: storage-tools:latest
               command:
               - /bin/bash
               - -c
               - |
                 # Identify unused PVCs
                 UNUSED_PVCS=$(kubectl get pvc -A -o json | jq -r '.items[] | select(.status.phase == "Bound") | select(.metadata.annotations.lastUsed < "'$(date -d "30 days ago" +%Y-%m-%d)'") | .metadata.name')

                 # Create snapshots
                 for PVC in $UNUSED_PVCS; do
                   kubectl create snapshot ...
                 done

                 # Analyze volume usage and generate reports
                 ...
             restartPolicy: OnFailure
   ```

**Métricas clave de monitoreo:**

1. **Métricas de volúmenes EBS**:
   - VolumeReadOps/VolumeWriteOps
   - VolumeReadBytes/VolumeWriteBytes
   - VolumeQueueLength
   - BurstBalance (volúmenes gp2)

2. **Métricas de EFS**:
   - TotalIOBytes
   - DataReadIOBytes/DataWriteIOBytes
   - MetadataIOBytes
   - ClientConnections
   - StorageBytes (Standard/IA)

3. **Métricas de FSx for Lustre**:
   - DataReadBytes/DataWriteBytes
   - DataReadOperations/DataWriteOperations
   - FreeDataStorageCapacity
   - LogicalDiskUsage

4. **Métricas de almacenamiento de Kubernetes**:
   - Uso y capacidad de PVC
   - Estado de mount de volúmenes
   - Uso de storage class

**Características avanzadas de monitoreo y administración:**

1. **Análisis predictivo**:
   - Predicción y planificación de capacidad
   - Análisis de tendencias de rendimiento
   - Pronóstico de costos

2. **Detección de anomalías**:
   - Detectar patrones de I/O anormales
   - Advertencia temprana de degradación del rendimiento
   - Predicción de escasez de capacidad

3. **Optimización automatizada**:
   - Recomendaciones de tipo de volumen basadas en patrones de uso
   - Escalado automático hacia arriba y hacia abajo
   - Recomendaciones de optimización de costos

4. **Reportes integrados**:
   - Reportes de uso y rendimiento de almacenamiento
   - Asignación y análisis de costos
   - Reportes de cumplimiento y auditoría

**Mejores prácticas de implementación:**

1. **Monitoreo multinivel**:
   - Nivel de infraestructura (CloudWatch)
   - Nivel de Kubernetes (Prometheus)
   - Nivel de aplicación (métricas personalizadas)

2. **Estrategia de alertas**:
   - Configurar alertas según la severidad
   - Agrupación y deduplicación de alertas
   - Definir rutas de escalamiento

3. **Política de retención de datos**:
   - Datos de alta resolución: retención a corto plazo
   - Datos agregados: retención a largo plazo
   - Equilibrio entre costo y utilidad

4. **Introducción gradual de automatización**:
   - Implementar primero monitoreo y alertas
   - Agregar capacidades de reportes y análisis
   - Introducir gradualmente la administración automatizada

Problemas con las otras opciones:
- **A. Usar solo CloudWatch y AWS Console**: Proporciona métricas nativas de AWS, pero carece de métricas detalladas a nivel de Kubernetes y tiene capacidades de automatización limitadas.
- **C. Inspección manual y análisis de logs**: Carece de escalabilidad, dificulta el monitoreo en tiempo real e impide la detección proactiva de problemas.
- **D. Usar solo herramientas de monitoreo de terceros**: Puede tener integración limitada con métricas nativas de AWS y puede generar costos adicionales.
