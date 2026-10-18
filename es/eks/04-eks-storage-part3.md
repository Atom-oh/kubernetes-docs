# Almacenamiento de Amazon EKS - Parte 3: Supervisión, solución de problemas, optimización de costos y seguridad

> **Última actualización**: October 16, 2026

Este documento es la tercera y última parte de la serie sobre almacenamiento de Amazon EKS. Abarca la supervisión del almacenamiento, la solución de problemas, la optimización de costos y la seguridad.

## Tabla de contenido

1. [Supervisión del almacenamiento](#storage-monitoring)
2. [Solución de problemas de almacenamiento](#storage-troubleshooting)
3. [Optimización de costos de almacenamiento](#storage-cost-optimization)
4. [Seguridad del almacenamiento](#storage-security)
5. [Prácticas recomendadas de administración del almacenamiento](#storage-management-best-practices)

## Supervisión del almacenamiento {#storage-monitoring}

Combine observaciones del backend, Kubernetes y las aplicaciones. Los contadores de E/S del backend no miden el espacio libre del sistema de archivos, y la disponibilidad de Kubernetes no confirma la coherencia de la base de datos. Registre las unidades, dimensiones, períodos de agregación y el comportamiento ante datos faltantes antes de crear una alarma.

<!-- Diagram repair pending: ServiceMonitor configures Prometheus discovery; node-exporter is not a PVC usage exporter.
![Diagram showing three parallel EKS storage-monitoring pipelines: AWS CloudWatch turning EBS, EFS and FSx for Lustre metrics into key monitoring metrics, alarms and a dashboard; Prometheus feeding ServiceMonitor/PodMonitor discovery into Grafana plus PrometheusRule alert rules; and a volume-usage exporter DaemonSet driving custom metrics and alerts.](../.gitbook/assets/en-eks-04-eks-storage-part3-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-0.html)
-->

### Supervisión con CloudWatch

EBS/EFS/FSx publican sus métricas de servicio sin necesidad de un exportador de Kubernetes. El acceso a consultas y visualizaciones de CloudWatch sigue requiriendo los permisos de IAM adecuados. Una llamada get-dashboard recupera la definición de un dashboard que ya existe; no crea un dashboard ni habilita métricas.

#### Métricas de volúmenes EBS

| Métrica | Interpretación correcta |
|---|---|
| VolumeReadBytes / VolumeWriteBytes | La suma representa los bytes transferidos durante el período seleccionado; divídala por los segundos del período para obtener bytes/s |
| VolumeReadOps / VolumeWriteOps | La suma representa las operaciones completadas; divídala por los segundos del período para obtener IOPS |
| VolumeTotalReadTime / VolumeTotalWriteTime | La suma representa los segundos acumulados de operación; divídala por la suma de operaciones correspondiente para obtener el promedio de segundos por operación, teniendo en cuenta los casos con cero operaciones |
| VolumeQueueLength | Indicador de E/S pendiente; Average/Maximum ayudan a distinguir entre colas sostenidas y picos |
| BurstBalance | Créditos restantes para gp2, st1 y sc1; no es una métrica de créditos de gp3 |

En las conexiones Nitro compatibles, las métricas actuales también incluyen VolumeAvgIOPS (Ops/s), VolumeAvgThroughput (KiB/s), VolumeAvgReadLatency/VolumeAvgWriteLatency (milisegundos) y comprobaciones de E/S excedidas o bloqueadas. Compruebe las restricciones de Multi-Attach, cómputo y zona de cada métrica. Las métricas estándar de volumen se publican para los volúmenes conectados; la ausencia de datos no equivale automáticamente a un uso cero. Los contadores de tiempo existentes pueden superar el período de reloj cuando las operaciones se superponen.

#### Métricas de sistemas de archivos EFS

TotalIOBytes, DataReadIOBytes, DataWriteIOBytes y MetadataIOBytes describen bytes, no una velocidad de transferencia ya normalizada. Divida la suma correspondiente por el período para obtener bytes/s. MeteredIOBytes refleja la medición del rendimiento de EFS, incluidos los descuentos por lectura; no es intercambiable con los bytes transferidos sin procesar. PermittedThroughput es una tasa. Compare períodos y unidades coincidentes, y supervise ClientConnections, PercentIOLimit según el modo y las clases de almacenamiento cuando sea necesario. BurstCreditBalance se aplica al rendimiento Bursting, no al rendimiento Elastic.

#### Métricas de FSx for Lustre

DataReadBytes/DataWriteBytes y DataReadOperations/DataWriteOperations usan FileSystemId; Sum/período da el rendimiento o las operaciones/s. **NetworkThroughputUtilization es válida**: corresponde a cada servidor de almacenamiento de objetos (OSS), tiene las dimensiones FileSystemId y FileServer e informa el porcentaje de utilización. FreeDataStorageCapacity es por OST y tiene las dimensiones FileSystemId y StorageTargetId. Inspeccione los desequilibrios por destino y los indicadores de capacidad alineados; sumar un indicador a lo largo del tiempo no proporciona la capacidad libre actual.

LogicalDiskUsage y PhysicalDiskUsage también son métricas válidas: describen bytes lógicos sin comprimir y bytes físicos comprimidos. Su agregación a nivel del sistema de archivos ayuda a evaluar la compresión; no convierte los precios de capacidad aprovisionada en precios basados únicamente en el uso.

### Supervisión con Prometheus y Grafana

Reutilice la pila existente del responsable de la supervisión. Para una nueva instalación revisada, el chart publicado kube-prometheus-stack92.9.0 es una referencia verificada con operator0.94.1; no es una instrucción para actualizar automáticamente un clúster existente. Lo siguiente solo representa los manifiestos. Prepare `monitoring/grafana-admin` con las claves admin-user/admin-password y la clase ebs-gp3 ampliable de este capítulo. Ajuste la versión real del clúster, el tamaño del almacenamiento y la retención. La entrega de alertas, la persistencia de Grafana, la disponibilidad y los valores predeterminados de TLS/autenticación de kubelet aún requieren una revisión específica para el despliegue:

```yaml
grafana:
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
prometheus:
  prometheusSpec:
    retention: 14d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ebs-gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 20Gi
```



```bash
set -euo pipefail
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm template prometheus prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring --kube-version 1.36.0 \
  --include-crds -f monitoring-values.yaml > monitoring-review.yaml
```

Un ServiceMonitor selecciona **Services** y, a continuación, sus endpoints; tanto su namespaceSelector como los selectores de ServiceMonitor de la instancia de Prometheus deben coincidir. De forma predeterminada, el chart de Helm de EBS CSI1.66 establece controller.enableMetrics en false. Para una instalación administrada mediante ese chart, revise estos valores con su responsable actual; habilitan el endpoint de métricas 3301 del driver, los Services de métricas de sidecar y los ServiceMonitors generados. Haga coincidir la etiqueta de la versión con el selector real de Prometheus:

```yaml
controller:
  enableMetrics: true
  serviceMonitor:
    labels:
      release: prometheus
```

Es posible que un complemento administrado de EKS exponga otras opciones de configuración; inspeccione su versión/configuración y los recursos reales en lugar de aplicarle valores de Helm. El ServiceMonitor independiente siguiente es una **alternativa** únicamente si el responsable ya expone el Service mostrado y no ha creado un monitor coincidente. No lo despliegue junto con un monitor generado equivalente:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: csi-metrics-reviewed
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
    - kube-system
  selector:
    matchLabels:
      app: ebs-csi-controller
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```



```bash
set -euo pipefail
kubectl -n kube-system get svc ebs-csi-controller -o yaml
kubectl -n kube-system get endpointslice \
  -l kubernetes.io/service-name=ebs-csi-controller -o wide
kubectl -n monitoring get prometheus -o yaml
```

Confirme que el destino seleccionado esté Up y exponga las métricas previstas. El driver y el provisioner/attacher/resizer/snapshotter tienen endpoints de métricas separados; un único Service del driver no recopila las métricas de todos los sidecars. La latencia de las operaciones de la API de CSI es distinta de la latencia de E/S de datos de la aplicación/EBS.

### Uso del sistema de archivos y alertas

Use métricas autenticadas de kubelet para kubelet_volume_stats_* cuando el driver de CSI implemente las estadísticas de volumen necesarias. kube-state-metrics proporciona información sobre el estado de los objetos y las solicitudes, y node-exporter proporciona métricas del sistema de archivos del host; instalar otro DaemonSet de node-exporter no crea métricas de uso por PVC. kube-prometheus-stack ya incluye una opción para node-exporter. Evite duplicar sus montajes y privilegios de host.

Es posible que los volúmenes de bloques sin procesar y los drivers que no admiten estadísticas no publiquen la capacidad del sistema de archivos. Las solicitudes de PVC/punto de acceso de EFS no son cuotas por directorio; la capacidad informada puede describir el sistema de archivos compartido. container_fs_usage_bytes no es una medición universal de PVC. Verifique el recopilador, el montaje y la correspondencia entre los espacios de nombres y los claims, y gestione las métricas faltantes por separado.

Las siguientes reglas eliminan duplicados de scrapes equivalentes usando max en lugar de sumar claims duplicados. Los datos federados deben incluir una etiqueta de clúster fiable. Se excluyen las series con capacidad cero. Las predicciones utilizan indicadores y tendencias recientes; revise las interrupciones de scrape, la recreación o el cambio de tamaño de los claims y los cambios en la carga de trabajo antes de actuar. Adapte los selectores para conjuntos de datos estáticos o de solo lectura, u otros claims que no deberían generar una alerta para un operador:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: storage-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: storage-reviewed
    rules:
    - record: pvc:storage_used_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes)
    - record: pvc:storage_capacity_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_capacity_bytes)
    - alert: VolumeUsageHigh
      expr: (pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max > 0.85) and
        (pvc:storage_capacity_bytes:max > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Volume usage high ({{ $value | humanizePercentage }})
        description: PVC {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim
          }} requires capacity review.
    - alert: VolumeMayFillIn24Hours
      expr: (predict_linear(pvc:storage_used_bytes:max[6h], 86400) > pvc:storage_capacity_bytes:max)
        and (pvc:storage_capacity_bytes:max > 0) and (delta(pvc:storage_used_bytes:max[1h])
        > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Recent trend projects capacity exhaustion
        description: Review the trend and workload for PVC {{ $labels.namespace }}/{{
          $labels.persistentvolumeclaim }}; this is not a guarantee.
```

Las etiquetas de espacio de nombres/versión deben coincidir con el selector de reglas de Prometheus. Valide la sintaxis de las reglas y los escenarios sintéticos; luego, verifique la cobertura de métricas en vivo y el enrutamiento de alertas en el despliegue previsto. En esta revisión no se ejecutó ninguna recopilación de métricas en vivo ni entrega de alertas.

## Solución de problemas de almacenamiento {#storage-troubleshooting}

Empiece por la identidad del objeto y los eventos. Pending, ContainerCreating y las E/S lentas pueden tener causas distintas; la descarga de imágenes, la planificación y la disponibilidad de la aplicación no necesariamente indican fallos de almacenamiento. El diagrama es una guía de triaje, no una correspondencia exhaustiva entre síntomas y causas.

![Cuatro problemas comunes de almacenamiento de EKS (PVC pendiente, fallo de aprovisionamiento, problemas de montaje y problemas de rendimiento) organizados en dos grupos que conducen a comprobaciones de diagnóstico y acciones correctivas compartidas: registros del driver de CSI, permisos de IAM y StorageClass para el grupo de aprovisionamiento; estado del nodo para el grupo de montaje y rendimiento.](../.gitbook/assets/en-eks-04-eks-storage-part3-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-1.html)

### Aprovisionamiento y WaitForFirstConsumer

Use el espacio de nombres, el claim y el consumidor previsto reales de la carga de trabajo. Inspeccione la clase a la que se hace referencia, los eventos del controlador, la identidad del driver/permisos de KMS, las cuotas y los límites de conexión de los nodos, en lugar de conceder acceso amplio basándose en suposiciones:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the workload namespace}"
: "${PVC_NAME:?Set the claim name}"
: "${POD_NAME:?Set its intended consumer Pod}"
kubectl -n "$NAMESPACE" get pvc "$PVC_NAME" -o yaml
kubectl -n "$NAMESPACE" describe pvc "$PVC_NAME"
kubectl -n "$NAMESPACE" describe pod "$POD_NAME"
kubectl get storageclass
kubectl get nodes -L topology.kubernetes.io/zone
```



```bash
set -euo pipefail
: "${CSI_CONTROLLER_POD:?Select the actual controller Pod}"
: "${CSI_CONTAINER:?Select the relevant driver/sidecar container}"
kubectl -n kube-system get pod "$CSI_CONTROLLER_POD" \
  -o jsonpath='{.spec.containers[*].name}'
kubectl -n kube-system logs "$CSI_CONTROLLER_POD" -c "$CSI_CONTAINER" --since=15m --tail=200
```

WaitForFirstConsumer deja intencionalmente un PVC nuevo en Pending hasta que un consumidor que pueda planificarse determine la topología. Un PVC nuevo sin vincular todavía no tiene una AZ a la que haya que mover un grupo de nodos. Inspeccione los selectores del Pod, la afinidad, los taints, los recursos y la topología del almacenamiento. El uso de spec.nodeName omite el planificador y puede impedir esta ruta de vinculación; use restricciones de planificación compatibles. Una vez vinculado, la afinidad de AZ/nodo de un PV de EBS es importante. No elimine un claim ni edite la capacidad del PV solo para quitarlo de Pending.

### Fallos de montaje

Distinga entre errores de conexión, errores de publicación/montaje en el nodo, clientes de sistema de archivos faltantes, errores de identidad/permisos y permisos de la aplicación. Al consultar los registros, seleccione el driver/sidecar de CSI pertinente; los registros predeterminados de un Pod con varios contenedores no muestran todos los componentes. Inspeccione VolumeAttachment, el driver/handle del PV vinculado y el nodo asignado, según sea necesario.

Para los registros del nodo, use el mecanismo de acceso/diagnóstico compatible con el responsable del nodo. El acceso mediante SSH como ec2-user y journalctl no son universales en Bottlerocket, Auto Mode u otros entornos de cómputo administrados. Un contenedor auxiliar privilegiado amazonlinux:2 no sustituye la configuración correcta del cliente/CSI; AL2 ya superó el fin del soporte de su sistema operativo en 2026. Reutilice la prueba compatible de consumidor de CSI del capítulo e inspeccione sus eventos antes de considerar un montaje manual independiente a nivel del nodo, aprobado por separado.

En EFS, inspeccione los destinos de montaje/DNS y TCP2049 desde el cliente de montaje real. Lustre requiere TCP988 y1018–1023, además de las reglas de cliente/servidor del servicio; las configuraciones de EFA tienen requisitos adicionales de referencias a grupos de seguridad. Compruebe también el tráfico de retorno de NACL y las rutas. Que falle el ping ICMP no demuestra que NFS no esté disponible, y no se garantiza que un contenedor de AWS CLI incluya las utilidades ping/telnet/mount. Una prueba de red de un Pod puede usar un origen/grupo de seguridad distinto del que usa un montaje de CSI originado en el nodo.

### E/S lentas

Compruebe el tamaño de operación medido, la puesta en cola, la concurrencia de la aplicación, el rendimiento aprovisionado del volumen, los límites de EBS de la instancia y el estado de inicialización. El siguiente cálculo de tiempo portátil en Python usa intervalos cerrados de cinco minutos; VolumeReadOps Sum/300 equivale a IOPS de lectura, a diferencia de Average, que se interpreta directamente como una tasa:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the volume Region}"
: "${EBS_VOLUME_ID:?Set the verified owned EBS volume ID}"
read -r START_TIME END_TIME < <(python3 - <<'PY'
import datetime, time
end = int(time.time()) // 300 * 300
fmt = lambda value: datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(fmt(end - 3600), fmt(end))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --namespace AWS/EBS --metric-name VolumeReadOps \
  --dimensions "Name=VolumeId,Value=$EBS_VOLUME_ID" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --period 300 --statistics Sum --output json > ebs-read-ops.json
python3 - ebs-read-ops.json <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    points = json.load(stream)["Datapoints"]
for point in sorted(points, key=lambda p: p["Timestamp"]):
    print(point["Timestamp"], "read IOPS:", point["Sum"] / 300)
if not points:
    print("No datapoints: check dimensions, attachment/activity, Region and publication delay")
PY
```

La prueba de escritura del sistema de archivos debe usar un directorio desechable aprobado en el montaje verificado. Guarde este script en el entorno de prueba previsto; crea un archivo único de 64 MiB y solo limpia su propio archivo/directorio. La lectura puede servirse desde la caché, así que estos tiempos no demuestran el rendimiento del almacenamiento en frío. No sobrescriba `/data/test` con un nombre predecible ni escriba ceros en bruto en un dispositivo con datos activos:

```bash
set -euo pipefail
: "${STORAGE_TEST_DIR:?Set an approved disposable directory on the verified disposable filesystem mount}"
test -d "$STORAGE_TEST_DIR" && test -w "$STORAGE_TEST_DIR"
STORAGE_TEST_PATH=$(mktemp -d "$STORAGE_TEST_DIR/storage-test.XXXXXX")
cleanup() { rm -f -- "$STORAGE_TEST_PATH/payload"; rmdir -- "$STORAGE_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$STORAGE_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$STORAGE_TEST_PATH/payload" of=/dev/null bs=1M
```

En esta revisión no se ejecutó ningún benchmark de almacenamiento. Considere la fragmentación una hipótesis que requiere pruebas; recrear/formatear un sistema de archivos es una migración de datos, no una solución inicial rutinaria. No cambie un planificador de E/S supuesto para nvme0n1: podría ser otro volumen o el dispositivo raíz, y los nombres/compatibilidad de los planificadores modernos blk-mq varían.

En EFS son importantes General Purpose, el modo de rendimiento real, los límites de clientes, la demanda de metadatos y la concurrencia. Use las opciones compatibles del asistente de montaje de la Parte 2, incluidas las opciones hard/TLS y un comportamiento adecuado de timeout/reintento. Agrupar archivos o usar accesos más secuenciales puede ayudar con una carga de trabajo medida, pero cambiar la organización de los datos de la aplicación no siempre es beneficioso.

## Optimización de costos de almacenamiento {#storage-cost-optimization}

Optimice el costo total de la carga de trabajo sin dejar de cumplir los requisitos de latencia, durabilidad, recuperación y propiedad. Los descuentos de cómputo, el almacenamiento asignado, el rendimiento aprovisionado, los cargos por solicitudes/transferencia y las copias de seguridad retenidas son costos independientes.

<!-- Diagram repair pending: align each storage service with its actual optimization strategy; do not map S3 to FSx optimization or FSx to EFS optimization.
![Diagram showing four AWS storage types (EBS, EFS, FSx for Lustre, S3), each feeding its matching optimization strategy (volume optimization, lifecycle management, EFS optimization, FSx optimization), with all four strategies rolling up into a single cost-monitoring node built on Cost Explorer, Kubernetes cost allocation, and anomaly detection.](../.gitbook/assets/en-eks-04-eks-storage-part3-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-2.html)
-->

### Tipo de volumen, tamaño y migración

Compare gp3 con el perfil real de costo/rendimiento de gp2; considere los tipos HDD solo para patrones de acceso adecuados. Aprovisione un margen de capacidad medido y alertas, no un tamaño máximo arbitrario. La capacidad de EBS/PVC generalmente se amplía, no se reduce; reducir la capacidad asignada requiere una migración compatible a un volumen nuevo más pequeño, con validación de los datos.

Crear una StorageClass gp3 o marcarla como predeterminada **no migra los volúmenes gp2 existentes**. Cambiar la clase predeterminada también afecta a otros claims nuevos. Reutilice la clase con nombre explícito de la Parte 1. Para los volúmenes existentes, elija el flujo de trabajo de modificación compatible con el driver desplegado o una migración de copia de seguridad/restauración probada a un claim nuevo; inspeccione la propiedad, la coherencia de la aplicación y la reversión antes de cambiar el almacenamiento.

### Ciclo de vida y retención

Una VolumeSnapshotClass define el comportamiento del driver y la retención; no programa las instantáneas ni las elimina en función de su antigüedad. Use la programación y la política de retención del responsable de las copias de seguridad. La Parte 2 explica el ciclo de vida de las instantáneas CSI de Velero, incluida la eliminación incluso cuando la clase original era Retain.

Un PV marcado como Available o Released no es necesariamente descartable, y Bound no demuestra que esté en uso activo. Antes de limpiar recursos, inventaríe claimRef/UID, los responsables de las cargas de trabajo, las instantáneas, las obligaciones de retención y los recursos reales del backend. Retain puede dejar recursos con cargos; el comportamiento de Delete depende del driver. Eliminar un punto de acceso de EFS no equivale a eliminar su sistema de archivos/datos. La organización por niveles de archivos en S3/Archive también requiere un plan de restauración/acceso compatible con la aplicación.

### Optimización de costos de EFS

AWS recomienda Elastic throughput para cargas de trabajo impredecibles o con picos. Compárelo con Provisioned para una demanda sostenida conocida y con Bursting para su modelo de tamaño/créditos, usando E/S medidas reales y los precios vigentes. General Purpose es el modo de rendimiento recomendado. Los puntos de acceso pueden compartir un sistema de archivos con identidades POSIX distintas; no reservan capacidad por PVC ni proporcionan facturación automática por aplicación.

Lea la configuración de ciclo de vida existente completa antes de proponer un cambio:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the filesystem Region}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned filesystem ID}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --output json > efs-filesystem-review.json
aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
  --file-system-id "$EFS_FILE_SYSTEM_ID" --output json > efs-lifecycle-before.json
```

Una solicitud put-lifecycle-configuration actualiza la configuración del sistema de archivos; conserve en la matriz revisada todas las transiciones existentes previstas. Una matriz vacía deshabilita la administración del ciclo de vida. Cada objeto de política contiene una transición. Archive requiere una configuración compatible de General Purpose/Elastic y una transición posterior a IA. Incluya en el análisis de costos los cargos de acceso y duración mínima de IA/Archive; no sobrescriba sin más una política existente con un único ejemplo de 30 días.

### FSx for Lustre y atribución de costos

Elija scratch solo para datos que puedan recrearse y use opciones de despliegue/almacenamiento persistentes para el ciclo de vida necesario. LZ4 puede reducir el tamaño físico de los datos, pero no reduce automáticamente la factura de una asignación SSD ya aprovisionada; evalúe el modelo de precios de almacenamiento seleccionado, la tasa de compresión y los efectos en el rendimiento/CPU. La integración con un repositorio S3 requiere comportamientos de importación/exportación/liberación configurados, no solo un nombre de bucket.

Cost Explorer y las herramientas de asignación de costos de Kubernetes requieren datos de facturación configurados, etiquetas de asignación de costos activadas cuando corresponda y una correspondencia probada entre el PVC/PV y los ID de recursos en la nube. Las etiquetas del espacio de nombres no etiquetan automáticamente todos los cargos de AWS. Haga seguimiento de los volúmenes/instantáneas retenidos, los costos de solicitudes/transferencia y la retención de telemetría. Las instancias reservadas de EC2/Compute Savings Plans pueden cambiar los costos de cómputo elegibles; no reducen automáticamente la factura independiente de almacenamiento de EBS/EFS/FSx.

## Seguridad del almacenamiento {#storage-security}

Proteja por separado el backend, la ruta del nodo/montaje y el plano de control de Kubernetes. Un nombre de clase, una política de espacio de nombres o una raíz de contenedor de solo lectura no protegen por sí solos el contenido de un PVC con permisos de escritura.

<!-- Diagram repair pending: TLS, at-rest key management, IAM, network rules, RBAC and admission are distinct controls; neither RBAC nor PSS proves backend encryption.
![Diagram showing EBS/FSx, EFS, and S3 storage security feeding data-at-rest and data-in-transit encryption that converge on AWS KMS key management, security groups and IAM roles leading through Kubernetes RBAC to OPA Gatekeeper/Kyverno policy enforcement, and the pod security context enforced by Pod Security Standards.](../.gitbook/assets/en-eks-04-eks-storage-part3-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-3.html)
-->

### Cifrado de datos

El cifrado de EBS se solicita al aprovisionar un volumen; cambiar una StorageClass no cifra retroactivamente un volumen existente. Este ejemplo de clase nueva solicita almacenamiento gp3 cifrado, con vinculación de topología diferida y retención explícita. Si se requiere una clave administrada por el cliente, añada un kmsKeyId real y revisado, y prepare su política de clave/concesiones del driver; un ARN de ejemplo no es una clave funcional.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

Configure el cifrado de EFS al crear el sistema de archivos mediante el flujo de trabajo de infraestructura protegido de la Parte 1. Los datos existentes sin cifrar requieren una migración compatible a un sistema de archivos cifrado, no una opción de montaje. FSx for Lustre cifra automáticamente los datos en reposo: los sistemas de archivos scratch usan claves administradas por el servicio; una clave de KMS administrada por AWS/administrada por el cliente que se pueda seleccionar es una opción de **sistema de archivos persistente**. No pase kms-key-id de cliente al ejemplo SCRATCH_2.

Inspeccione los recursos reales en la nube, haga coincidir los ID de EBS con volumeHandles de PV vinculados y confirme la cuenta/Región. Una respuesta de FSx scratch sin una clave de cliente seleccionada no demuestra que el almacenamiento esté sin cifrar:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resources Region}"
: "${EBS_VOLUME_ID:?Identify the actual volume from its bound PV}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned EFS filesystem ID}"
: "${FSX_FILE_SYSTEM_ID:?Set the owned FSx filesystem ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[0].{Id:VolumeId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Type:LustreConfiguration.DeploymentType,KmsKeyId:KmsKeyId}' --output json
```

Para los datos en tránsito, use la opción `tls` compatible de EFS CSI/asistente de montaje y verifique la ruta de montaje real. El cifrado en tránsito de FSx depende de la configuración compatible del sistema de archivos/cliente/instancia; siga las indicaciones del servicio. **S3 HTTPS/TLS protege el transporte; `aws s3 cp --sse AES256` selecciona el cifrado en reposo SSE-S3.** Esa marca no habilita TLS. Use endpoints HTTPS y validación de certificados, y revise las políticas de bucket que exigen un transporte seguro. La política de clave de KMS es distinta de la administración de certificados de transporte.

### Control de acceso

Use la identidad CSI preparada en la Parte 1: el rol de Pod Identity/IRSA compatible del controlador y los permisos exactos del driver, además de las concesiones de KMS cuando corresponda. No vuelva a crear una ServiceAccount existente de un complemento administrado mediante un comando eksctl no relacionado ni transfiera los permisos del controlador a todos los nodos/aplicaciones. La identidad a nivel de Pod de Mountpoint, los montajes IAM de EFS y las identidades POSIX/puntos de acceso del sistema de archivos siguen rutas de autorización distintas.

Para el acceso de red, permita que el grupo de seguridad real del origen cliente/nodo alcance los destinos de montaje de EFS por TCP2049. Lustre requiere las reglas documentadas de TCP988 y1018–1023 entre clientes y servidores de archivos, incluido el tráfico propio/de cliente requerido. En cambio, Lustre habilitado para EFA requiere las reglas especificadas de todo el tráfico, con referencias a grupos de seguridad; un CIDR abierto a Internet no es un sustituto. Inspeccione las rutas, DNS, NACL y el origen real del montaje de CSI, además de los grupos de seguridad. Una NetworkPolicy de Kubernetes no controla automáticamente todas las conexiones al sistema de archivos originadas en el nodo.

El lector con ámbito de espacio de nombres siguiente puede inspeccionar objetos PVC; no puede crearlos, cambiar su tamaño ni eliminarlos. El acceso a PV de ámbito de clúster requiere un ClusterRole revisado por separado. Ninguno de los dos roles controla directamente los bytes de los archivos. Un principal capaz de crear Pods en un espacio de nombres podría montar sus PVC, por lo que también deben controlarse la creación de Pods, la identidad de las cargas de trabajo, los permisos POSIX/de puntos de acceso y el aislamiento entre inquilinos:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: storage-auditor
  namespace: storage-demo
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pvc-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - persistentvolumeclaims
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pvc-reader
  namespace: storage-demo
subjects:
- kind: ServiceAccount
  name: storage-auditor
  namespace: storage-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pvc-reader
```

### Contexto de seguridad de Pod

Este ejemplo completo separa runAsUser/runAsGroup/fsGroup/seccomp a nivel de Pod de allowPrivilegeEscalation/capabilities/readOnlyRootFilesystem a nivel de contenedor. Usa una clase cifrada preparada y un PVC declarado, en lugar de un volumen de datos indefinido y una imagen nginx sin rutas de ejecución escribibles proporcionadas. La versión de la política del espacio de nombres corresponde al ejemplo revisado de Kubernetes1.36; use la versión de política apropiada para su clúster.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: secure-data
  namespace: secure-ns
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-encrypted
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: secure-ns
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
    - test -w /data && sleep 3600
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
      claimName: secure-data
```

Una raíz de solo lectura no hace que `/data` sea de solo lectura: esta carga de trabajo comprueba intencionalmente que el PVC permita escritura. El comportamiento de fsGroup depende de CSI/sistema de archivos; un punto de acceso de EFS puede imponer una identidad POSIX distinta. Los perfiles SELinux/AppArmor requieren compatibilidad real del nodo/entorno de ejecución y una política preparada. No copie etiquetas MCS ni nombres de perfiles arbitrarios. Pod Security Standards restringe la configuración de los Pods; no cifra los volúmenes en la nube ni concede permisos de IAM. Los agentes de supervisión/CSI de nodo con acceso al host necesitan su propio diseño de seguridad/espacio de nombres revisado.

### Aplicación de políticas de seguridad

Un patrón de nombre de PVC o una lista de permitidos de StorageClass por sí solos no pueden demostrar el cifrado de EBS. La siguiente **Kyverno ValidatingPolicy** usa la API publicada `policies.kyverno.io/v1`, comprobada con Kyverno1.19.1 y su CRD. Requiere que estén instalados el controlador/CRD y que la propiedad de admisión sea adecuada. Los ejemplos anteriores de ClusterPolicy están obsoletos en esa versión; realice la migración de forma intencional en lugar de asumir compatibilidad de API.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-declared-ebs-encryption
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - storage.k8s.io
      apiVersions:
      - v1
      resources:
      - storageclasses
      operations:
      - CREATE
      - UPDATE
      scope: Cluster
  validations:
  - expression: '!(object.provisioner in [''ebs.csi.aws.com'', ''ebs.csi.eks.amazonaws.com''])
      || (has(object.parameters) && ''encrypted'' in object.parameters && object.parameters[''encrypted'']
      == ''true'')'
    message: EBS StorageClasses must explicitly request encryption.
```

La política comprueba el **parámetro de cifrado declarado en las operaciones de creación/actualización de StorageClass de EBS**, incluido el provisioner de Auto Mode. No inspecciona los volúmenes existentes de AWS, los PV estáticos, el contenido de las instantáneas ni las rutas de omisión fuera de su ámbito. Restrinja la administración de StorageClass/PV y use comprobaciones de cumplimiento del backend además de la admisión. Despliéguela tras probarla con recursos representativos y supervise los informes de políticas/el estado del webhook antes de aplicar la política ampliamente. El cifrado de datos existentes aún requiere su propia migración.

## Prácticas recomendadas de administración del almacenamiento {#storage-management-best-practices}

![Diagrama que relaciona las cuatro fases del ciclo de vida del almacenamiento (planificación, implementación, operación y optimización) con sus áreas correspondientes de prácticas recomendadas (planificación y diseño, automatización e IaC, copias de seguridad y recuperación ante desastres, rendimiento y optimización de costos); cada área enumera sus tres prácticas en orden.](../.gitbook/assets/en-eks-04-eks-storage-part3-4.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-4.html)

### Planificación y capacidad

Documente por separado la latencia/IOPS/velocidad de transferencia, el crecimiento de la capacidad, los patrones de lectura/escritura, la concurrencia, la disponibilidad, la durabilidad y el RPO/RTO. Elija almacenamiento en bloques, NFS compartido, Lustre paralelo o acceso a objetos en función de esos requisitos. Use un margen medido y procedimientos de ampliación limitados; un escalador automático o el cambio de tamaño de un PVC no proporcionan replicación de aplicaciones ni una reducción arbitraria de la capacidad.

### Copias de seguridad y recuperación ante desastres

Use una programación compatible con identidades de copia de seguridad únicas y un responsable de la retención. Una línea cron de shell que cree repetidamente una instantánea con nombre fijo falla después de que exista el primer objeto; una copia de seguridad de Velero de una sola ejecución llamada daily-backup no es una programación. Con la instalación de Velero/CSI revisada y los requisitos de coherencia de la base de datos de la Parte 2, este comando genera una programación diaria para su revisión:

```bash
velero schedule create storage-daily --schedule="0 0 * * *" \
  --include-namespaces=storage-demo --ttl=720h0m0s -o yaml > storage-schedule-review.yaml
```

Despliegue la configuración a través de su responsable después de revisarla; luego, genere alertas ante copias de seguridad faltantes o fallidas y pruebe restauraciones aisladas. Una copia de seguridad en S3 puede hacer referencia a instantáneas nativas en lugar de contener todos los bytes del volumen. La recuperación entre zonas/regiones requiere datos, claves, drivers/asignaciones de almacenamiento accesibles y validación de la aplicación. Conserve el origen hasta que se complete correctamente una transición controlada; registre el tiempo de recuperación medido en lugar de afirmar un RPO/RTO basándose en una programación.

### Infraestructura como código y GitOps

Use los ejemplos protegidos de creación de sistemas de archivos de la Parte 1/Parte 2 o un módulo Terraform/CloudFormation propio con versiones de proveedor/esquema revisadas, configuración de subred/destino de montaje/grupo de seguridad y protección contra eliminación. Un recurso de Terraform que solo crea un sistema de archivos no proporciona una ruta de montaje lista para EKS. Separe la retención de copias de seguridad del comportamiento de destrucción/poda de IaC.

Los valores de Helm son entradas específicas del chart: un valor personalizado `storage.encrypted: true` no hace nada a menos que una plantilla lo asigne al campo real compatible del recurso. Renderice y valide la StorageClass/PVC/carga de trabajo resultantes antes del despliegue. La poda de GitOps, la desinstalación del chart y la configuración de retención de claims pueden tener distintos efectos sobre los datos; documente qué sistema es responsable de cada recurso y pruebe los cambios de ciclo de vida con datos desechables.

Por ejemplo, este recurso de sistema de archivos solicita cifrado y rendimiento Elastic, conserva la política educativa de IA a 30 días y añade una protección contra la destrucción de Terraform. Sustituya el token de creación por un valor estable y específico del proyecto, configure el proveedor/cuenta/Región y añada los recursos de red/destinos de montaje revisados. prevent_destroy es una protección para operaciones de Terraform, no una copia de seguridad ni una protección contra todas las eliminaciones externas:

```hcl
resource "aws_efs_file_system" "example" {
  creation_token   = "example"
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  encrypted        = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = "ExampleFileSystem"
  }
}
```

### Revisión continua

Revise los cuellos de botella, los límites de aprovisionamiento, los costos de retención y los controles de seguridad a medida que cambien las cargas de trabajo. Mantenga los informes de limpieza en modo de solo lectura hasta verificar la propiedad de los recursos, la copia de seguridad/recuperación y los efectos de la eliminación. Genere alertas y proponga cambios acotados antes de automatizarlos. Los ejemplos del capítulo son configuraciones de referencia verificadas localmente; el rendimiento del backend, el despliegue de la admisión y la recuperación siguen requiriendo validación en el entorno previsto.

## Conclusión

En este documento, abordamos la supervisión, la solución de problemas, la optimización de costos y la seguridad del almacenamiento de Amazon EKS. Una administración eficaz del almacenamiento es fundamental para garantizar el rendimiento, la fiabilidad y la rentabilidad del clúster de EKS.

Los requisitos de almacenamiento varían según la aplicación, por lo que es importante comprender las características de la carga de trabajo y seleccionar la solución de almacenamiento adecuada. Además, debe administrar eficazmente los recursos de almacenamiento mediante revisiones periódicas de supervisión, solución de problemas, optimización de costos y seguridad.

## Referencias

- [Prácticas recomendadas de almacenamiento de Amazon EKS](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)
- [Solución de problemas de almacenamiento de Kubernetes](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-application/#debugging-pods)
- [Seguridad del almacenamiento de Kubernetes](https://kubernetes.io/docs/concepts/security/)

- [Métricas de CloudWatch de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [Dimensiones de métricas de FSx Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [Modos de rendimiento de EFS](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [API del ciclo de vida de EFS](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [Cifrado en reposo de FSx](https://docs.aws.amazon.com/fsx/latest/LustreGuide/encryption-at-rest.html)
- [Acceso de red de FSx](https://docs.aws.amazon.com/fsx/latest/LustreGuide/limit-access-security-groups.html)
- [Cifrado en reposo de S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html)
- [Migración CEL de Kyverno](https://kyverno.io/docs/guides/migration-to-cel/)

## Cuestionario

Para poner a prueba lo que aprendió en este capítulo, pruebe el [cuestionario del tema](../quizzes/eks/04-eks-storage-part3-quiz.md).
