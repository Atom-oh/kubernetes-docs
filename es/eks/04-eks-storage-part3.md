# Almacenamiento de Amazon EKS - Parte 3: Supervisión, solución de problemas, optimización de costos y seguridad

> **Última actualización**: 16 de octubre de 2026

Este es el tercer y último documento de la serie sobre almacenamiento de Amazon EKS. Abarca la supervisión, la solución de problemas, la optimización de costos y la seguridad del almacenamiento.

## Tabla de contenido

1. [Supervisión del almacenamiento](#storage-monitoring)
2. [Solución de problemas de almacenamiento](#storage-troubleshooting)
3. [Optimización de costos de almacenamiento](#storage-cost-optimization)
4. [Seguridad del almacenamiento](#storage-security)
5. [Prácticas recomendadas para administrar el almacenamiento](#storage-management-best-practices)

## Supervisión del almacenamiento {#storage-monitoring}

Combine las observaciones del backend, Kubernetes y las aplicaciones. Los contadores de E/S del backend no miden el espacio libre del sistema de archivos, y que Kubernetes indique que un recurso está listo no confirma la coherencia de la base de datos. Antes de crear una alarma, registre las unidades, dimensiones, períodos de agregación y el comportamiento esperado cuando falten datos.

<!-- Pendiente de reparar el diagrama: ServiceMonitor configura el descubrimiento de Prometheus; node-exporter no exporta el uso de PVC.
![Diagrama que muestra tres flujos paralelos de supervisión del almacenamiento en EKS: CloudWatch de AWS convierte las métricas de EBS, EFS y FSx for Lustre en métricas clave, alarmas y un panel; Prometheus envía el descubrimiento de ServiceMonitor/PodMonitor a Grafana y a las reglas de alerta PrometheusRule; y un DaemonSet que exporta el uso de volúmenes genera métricas y alertas personalizadas.](../.gitbook/assets/en-eks-04-eks-storage-part3-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-0.html)
-->

### Supervisión con CloudWatch

EBS, EFS y FSx publican sus métricas de servicio sin necesidad de un exportador de Kubernetes. Para consultar y visualizar datos en CloudWatch también se necesitan los permisos de IAM adecuados. Una llamada a get-dashboard recupera la definición de un panel que ya existe; no crea un panel ni habilita métricas.

#### Métricas de volúmenes EBS

| Métrica | Interpretación correcta |
|---|---|
| VolumeReadBytes / VolumeWriteBytes | La suma corresponde a los bytes transferidos durante el período seleccionado; divídala por los segundos del período para obtener bytes/s |
| VolumeReadOps / VolumeWriteOps | La suma corresponde a las operaciones completadas; divídala por los segundos del período para obtener IOPS |
| VolumeTotalReadTime / VolumeTotalWriteTime | La suma corresponde a los segundos acumulados de operación; divídala por la suma de operaciones correspondiente para calcular los segundos promedio por operación, teniendo en cuenta que puede haber cero operaciones |
| VolumeQueueLength | Indicador de E/S pendiente; Average/Maximum permiten distinguir entre colas sostenidas y picos |
| BurstBalance | Créditos restantes para gp2, st1 y sc1; no es una métrica de créditos de gp3 |

En las conexiones Nitro compatibles, las métricas actuales también incluyen VolumeAvgIOPS (Ops/s), VolumeAvgThroughput (KiB/s), VolumeAvgReadLatency/VolumeAvgWriteLatency (milisegundos) y comprobaciones de E/S excedidas o bloqueadas. Compruebe las restricciones de Multi-Attach, cómputo y zona de cada métrica. Las métricas estándar de volumen se publican para los volúmenes adjuntos; la falta de datos no equivale automáticamente a un uso de cero. Los contadores de tiempo existentes pueden superar el período de reloj cuando se solapan operaciones.

#### Métricas de sistemas de archivos EFS

TotalIOBytes, DataReadIOBytes, DataWriteIOBytes y MetadataIOBytes expresan bytes, no una tasa de transferencia ya normalizada. Divida la suma correspondiente por el período para obtener bytes/s. MeteredIOBytes refleja la medición del rendimiento de EFS e incluye los descuentos por lectura; no equivale a los bytes transferidos sin procesar. PermittedThroughput es una tasa. Compare períodos y unidades coincidentes y, cuando corresponda, supervise ClientConnections, PercentIOLimit según el modo y las clases de almacenamiento. BurstCreditBalance se aplica al rendimiento Bursting, no al rendimiento Elastic.

#### Métricas de FSx for Lustre

DataReadBytes/DataWriteBytes y DataReadOperations/DataWriteOperations usan FileSystemId; Sum/período proporciona el rendimiento o las operaciones/s. **NetworkThroughputUtilization es válida**: se mide por servidor de almacenamiento de objetos (OSS), utiliza las dimensiones FileSystemId y FileServer e informa el porcentaje de utilización. FreeDataStorageCapacity se mide por OST con FileSystemId y StorageTargetId. Revise los desequilibrios por destino y los indicadores de capacidad correspondientes; sumar un indicador a lo largo del tiempo no proporciona la capacidad libre actual.

LogicalDiskUsage y PhysicalDiskUsage también son métricas válidas: representan bytes lógicos sin comprimir y bytes físicos comprimidos. La agregación a nivel del sistema de archivos ayuda a evaluar la compresión, pero no convierte el precio de la capacidad aprovisionada en un precio basado únicamente en el uso.

### Supervisión con Prometheus y Grafana

Reutilice la pila de supervisión que ya administra el responsable del entorno. Para una instalación nueva y revisada, el chart publicado kube-prometheus-stack 92.9.0 es una referencia verificada con operator 0.94.1; no es una instrucción para actualizar automáticamente un clúster existente. Lo siguiente solo renderiza manifiestos. Prepare `monitoring/grafana-admin` con las claves admin-user/admin-password y la clase ebs-gp3 ampliable de este capítulo. Ajuste la versión real del clúster, el tamaño del almacenamiento y la retención. La entrega de alertas, la persistencia y disponibilidad de Grafana, y los valores predeterminados de TLS/autenticación de kubelet aún requieren una revisión específica para el despliegue:

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

Un ServiceMonitor selecciona **Services** y después sus endpoints; tanto su namespaceSelector como los selectores de ServiceMonitor de la instancia de Prometheus deben coincidir. De forma predeterminada, el chart de Helm de EBS CSI 1.66 establece controller.enableMetrics en false. Si la instalación se administra con ese chart, revise estos valores junto con su responsable actual: habilitan el endpoint de métricas 3301 del driver, los Services de métricas de los sidecars y los ServiceMonitors generados. Haga coincidir la etiqueta de la versión con el selector real de Prometheus:

```yaml
controller:
  enableMetrics: true
  serviceMonitor:
    labels:
      release: prometheus
```

Un complemento administrado de EKS puede exponer opciones de configuración diferentes; inspeccione su versión/configuración y los recursos reales en lugar de aplicarle valores de Helm. El ServiceMonitor independiente que se muestra a continuación es una **alternativa** solo si el responsable ya expone el Service indicado y no ha creado un monitor equivalente. No lo implemente junto con un monitor generado equivalente:

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

Confirme que el destino seleccionado esté Up y exponga las métricas previstas. El driver y el provisioner/attacher/resizer/snapshotter tienen endpoints de métricas separados; un Service del driver no recopila las métricas de todos los sidecars. La latencia de las operaciones de la API de CSI es distinta de la latencia de E/S de datos de la aplicación/EBS.

### Uso del sistema de archivos y alertas

Use métricas autenticadas de kubelet para kubelet_volume_stats_* cuando el driver de CSI implemente las estadísticas de volumen necesarias. kube-state-metrics proporciona información sobre el estado de los objetos y las solicitudes; node-exporter proporciona métricas del sistema de archivos del host. Instalar otro DaemonSet de node-exporter no crea métricas de uso por PVC. kube-prometheus-stack ya incluye una opción para node-exporter. Evite duplicar sus montajes del host y privilegios.

Los volúmenes de bloques sin sistema de archivos y los drivers que no admiten estadísticas quizá no publiquen la capacidad del sistema de archivos. Las solicitudes de PVC o puntos de acceso de EFS no son cuotas por directorio; la capacidad informada puede corresponder al sistema de archivos compartido. container_fs_usage_bytes no es una medición universal de PVC. Compruebe el recopilador, el montaje y la correspondencia de espacio de nombres/claim, y trate las métricas faltantes por separado.

Las siguientes reglas deduplican los scrapes equivalentes usando max en vez de sumar claims duplicados. Los datos federados deben incluir una etiqueta de clúster fiable. Se excluyen las series con capacidad cero. Las previsiones usan indicadores y tendencias recientes; antes de actuar, revise las interrupciones de scraping, la recreación o redimensión de claims y los cambios de las cargas de trabajo. Adapte los selectores para conjuntos de datos estáticos o de solo lectura, y para otros claims que no deban generar una página para un operador:

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

Las etiquetas de namespace/release deben coincidir con el selector de la regla de Prometheus. Valide la sintaxis de las reglas y escenarios sintéticos; después, compruebe la cobertura de métricas en vivo y el enrutamiento de alertas en el despliegue previsto. En esta revisión no se ejecutaron recopilación de métricas en vivo ni entrega de alertas.

## Solución de problemas de almacenamiento {#storage-troubleshooting}

Empiece por la identidad del objeto y sus eventos. Pending, ContainerCreating y una E/S lenta pueden tener causas distintas; los problemas al descargar imágenes, programar Pods o iniciar aplicaciones no necesariamente indican un fallo de almacenamiento. El diagrama sirve como guía de diagnóstico inicial, no como una relación exhaustiva entre síntomas y causas.

![Cuatro problemas habituales de almacenamiento en EKS (PVC pendiente, fallo de aprovisionamiento, problemas de montaje y problemas de rendimiento) se agrupan de dos en dos para aplicar comprobaciones y soluciones comunes: registros del driver CSI, permisos de IAM y StorageClass para el aprovisionamiento; estado del nodo para el montaje y el rendimiento.](../.gitbook/assets/en-eks-04-eks-storage-part3-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-1.html)

### Aprovisionamiento y WaitForFirstConsumer

Use el espacio de nombres, claim y consumidor previsto que correspondan a la carga de trabajo real. Inspeccione la clase referenciada, los eventos del controlador, la identidad del driver y los permisos de KMS, las cuotas y los límites de adjuntos del nodo, en vez de conceder acceso amplio basándose en una suposición:

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

WaitForFirstConsumer deja intencionalmente un PVC nuevo en Pending hasta que un consumidor programable determina la topología. Un PVC nuevo sin enlazar aún no tiene una zona de disponibilidad a la que haya que trasladar un grupo de nodos. Revise los selectores del Pod, la afinidad, los taints, los recursos y la topología del almacenamiento. Usar spec.nodeName evita el scheduler y puede impedir esta ruta de enlace; utilice restricciones de programación compatibles. Una vez enlazado, importan la zona de disponibilidad y la afinidad de nodo del PV de EBS. No elimine el claim ni edite la capacidad del PV solo para salir de Pending.

### Errores de montaje

Distinga entre errores de adjunto, publicación/montaje en el nodo, falta de clientes del sistema de archivos, errores de identidad/permisos y permisos de la aplicación. Al leer registros, seleccione el contenedor pertinente del driver CSI o del sidecar; los registros predeterminados de un Pod con varios contenedores no representan todos sus componentes. Cuando sea necesario, inspeccione VolumeAttachment, el driver/handle del PV enlazado y el nodo asignado.

Para los registros del nodo, use el mecanismo de acceso/diagnóstico admitido por quien administra el nodo. El acceso SSH como ec2-user y journalctl no son universales en Bottlerocket, Auto Mode ni otros entornos de cómputo administrados. Un contenedor auxiliar privilegiado amazonlinux:2 no sustituye la configuración correcta del driver/cliente CSI; el soporte de sistema operativo de AL2 terminó en 2026. Reutilice la prueba de consumidor CSI admitida en este capítulo y revise sus eventos antes de considerar un montaje manual independiente en el nodo, que requiere aprobación aparte.

Para EFS, inspeccione los destinos de montaje/DNS y la conexión TCP 2049 desde el cliente de montaje real. Lustre requiere TCP 988 y 1018–1023, además de las reglas de servicio entre cliente y servidor; las configuraciones EFA tienen requisitos adicionales de referencias entre grupos de seguridad. Compruebe también el tráfico de retorno de NACL y las rutas. Que falle ICMP ping no demuestra que NFS no esté disponible, y no se garantiza que un contenedor con AWS CLI incluya utilidades ping/telnet/mount. Una prueba de red desde un Pod puede usar un origen/grupo de seguridad distinto del montaje CSI iniciado por el nodo.

### E/S lenta

Compruebe el tamaño de las operaciones medidas, la cola, la concurrencia de la aplicación, el rendimiento aprovisionado del volumen, los límites EBS de la instancia y el estado de inicialización. El siguiente cálculo portátil en Python usa intervalos cerrados de cinco minutos; la suma de VolumeReadOps dividida por 300 da las IOPS de lectura, a diferencia de interpretar directamente Average como una tasa:

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

La prueba de escritura del sistema de archivos debe usar un directorio desechable aprobado en el montaje verificado. Guarde este script en el entorno de prueba previsto: crea un archivo único de 64 MiB y elimina únicamente el archivo/directorio que creó. La lectura puede servirse desde la caché, por lo que estos tiempos no demuestran el rendimiento del almacenamiento en frío. No sobrescriba una ruta predecible como `/data/test` ni escriba ceros en bruto en un dispositivo con datos activos:

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

En esta revisión no se ejecutó ninguna prueba de rendimiento del almacenamiento. Trate la fragmentación como una hipótesis que requiere pruebas; recrear o formatear un sistema de archivos es una migración de datos, no una primera medida rutinaria. No cambie un scheduler de E/S suponiendo que el dispositivo es nvme0n1: podría ser otro volumen o el dispositivo raíz, y los nombres/compatibilidad de schedulers modernos blk-mq varían.

En EFS importan el modo General Purpose, el modo de rendimiento real, los límites del cliente, la demanda de metadatos y la concurrencia. Use las opciones admitidas del asistente de montaje descritas en la Parte 2, incluidas hard/TLS y el comportamiento apropiado de timeout/reintentos. Agrupar archivos o aumentar el acceso secuencial puede ayudar a una carga de trabajo medida, pero cambiar el diseño de los datos de una aplicación no siempre resulta beneficioso.

## Optimización de costos de almacenamiento {#storage-cost-optimization}

Optimice el costo total de la carga de trabajo sin sacrificar los requisitos de latencia, durabilidad, recuperación y propiedad. Los descuentos de cómputo, el almacenamiento asignado, el rendimiento aprovisionado, las solicitudes/transferencias y las copias de seguridad retenidas son costos distintos.

<!-- Pendiente de reparar el diagrama: asocie cada servicio de almacenamiento con su estrategia de optimización real; no asigne a S3 la optimización de FSx ni a FSx la optimización de EFS.
![Diagrama de cuatro tipos de almacenamiento de AWS (EBS, EFS, FSx for Lustre y S3), cada uno conectado con su estrategia de optimización correspondiente (optimización de volúmenes, administración del ciclo de vida, optimización de EFS y optimización de FSx); las cuatro estrategias convergen en un nodo de supervisión de costos basado en Cost Explorer, asignación de costos de Kubernetes y detección de anomalías.](../.gitbook/assets/en-eks-04-eks-storage-part3-2.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-2.html)
-->

### Tipo, tamaño y migración de volúmenes

Compare gp3 con el perfil real de costo/rendimiento de gp2; considere tipos HDD solo para patrones de acceso adecuados. Aprovisione una reserva de capacidad y alarmas basadas en mediciones, no un tamaño máximo arbitrario. La capacidad de EBS/PVC normalmente aumenta, pero no disminuye; para reducirla se requiere una migración compatible a un volumen nuevo más pequeño y la validación de los datos.

Crear una StorageClass gp3 o establecerla como predeterminada **no migra los volúmenes gp2 existentes**. Cambiar la clase predeterminada también afecta a claims nuevos no relacionados. Reutilice la clase nombrada explícitamente en la Parte 1. Para volúmenes existentes, elija el flujo de modificación admitido por el driver implementado o una migración probada mediante copia de seguridad/restauración a un claim nuevo; antes de cambiar el almacenamiento, revise la propiedad, la coherencia de la aplicación y el plan de reversión.

### Ciclo de vida y retención

Una VolumeSnapshotClass define el comportamiento del driver y la retención; no programa snapshots ni los elimina por antigüedad. Use la programación y política de retención del responsable de las copias de seguridad. La Parte 2 explica el ciclo de vida de snapshots CSI de Velero, incluida su eliminación aunque la clase original tenga Retain.

Un PV marcado Available o Released no se puede descartar automáticamente, y Bound no demuestra que esté en uso. Antes de limpiar, inventaríe claimRef/UID, responsables de las cargas de trabajo, snapshots, obligaciones de retención y recursos reales del backend. Retain puede dejar recursos facturables; el comportamiento de Delete depende del driver. Eliminar un punto de acceso de EFS no equivale a eliminar el sistema de archivos o sus datos. La clasificación por niveles de datos en S3/Archive también requiere un plan de acceso/restauración compatible con la aplicación.

### Optimización de costos de EFS

AWS recomienda el rendimiento Elastic para cargas de trabajo impredecibles o con picos. Compárelo con Provisioned cuando la demanda sostenida sea conocida y con Bursting según su modelo de tamaño/créditos, usando la E/S medida y los precios actuales. General Purpose es el modo de rendimiento recomendado. Los puntos de acceso permiten compartir un sistema de archivos con identidades POSIX distintas; no reservan capacidad por PVC ni facturan automáticamente por aplicación.

Lea toda la configuración de ciclo de vida existente antes de proponer un cambio:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the filesystem Region}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned filesystem ID}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --output json > efs-filesystem-review.json
aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
  --file-system-id "$EFS_FILE_SYSTEM_ID" --output json > efs-lifecycle-before.json
```

Una solicitud put-lifecycle-configuration actualiza la configuración del sistema de archivos; conserve todas las transiciones existentes que deban mantenerse en la matriz revisada. Una matriz vacía desactiva la administración del ciclo de vida. Cada objeto de política contiene una transición. Archive requiere una configuración compatible de General Purpose/Elastic y una transición posterior a IA. Incluya en el análisis de costos los cargos de acceso a IA/Archive y su duración mínima; no sobrescriba a ciegas una política existente con un único ejemplo de 30 días.

### FSx for Lustre y atribución de costos

Elija scratch solo para datos que puedan recrearse, y las opciones persistentes de despliegue/almacenamiento para el ciclo de vida requerido. LZ4 puede reducir el tamaño físico de los datos, pero no reduce automáticamente la factura de una asignación SSD ya aprovisionada; evalúe el modelo de precios de almacenamiento seleccionado, la tasa de compresión y los efectos en el rendimiento/CPU. La integración con un repositorio S3 requiere una configuración de importación/exportación/liberación, no solo el nombre de un bucket.

Cost Explorer y las herramientas de asignación de costos de Kubernetes requieren datos de facturación configurados, etiquetas de asignación de costos activadas cuando corresponda y una correspondencia probada entre PVC/PV e identificadores de recursos en la nube. Las etiquetas de namespace no asignan automáticamente cada cargo de AWS. Haga seguimiento de volúmenes/snapshots retenidos, costos de solicitudes/transferencias y retención de telemetría. Las instancias reservadas de EC2 o Compute Savings Plans pueden cambiar costos de cómputo elegibles; no reducen automáticamente la factura separada del almacenamiento EBS/EFS/FSx.

## Seguridad del almacenamiento {#storage-security}

Proteja por separado el backend, la ruta del nodo/montaje y el plano de control de Kubernetes. El nombre de una clase, una política de namespace o una raíz de contenedor de solo lectura no protegen por sí solos el contenido de un PVC escribible.

<!-- Pendiente de reparar el diagrama: TLS, administración de claves en reposo, IAM, reglas de red, RBAC y admisión son controles distintos; ni RBAC ni PSS demuestran el cifrado del backend.
![Diagrama en el que la seguridad del almacenamiento EBS/FSx, EFS y S3 contempla cifrado de datos en reposo y en tránsito, que converge en la administración de claves AWS KMS; los grupos de seguridad y roles de IAM pasan por RBAC de Kubernetes hasta la aplicación de políticas OPA Gatekeeper/Kyverno; y el contexto de seguridad del Pod se aplica mediante Pod Security Standards.](../.gitbook/assets/en-eks-04-eks-storage-part3-3.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-3.html)
-->

### Cifrado de datos

El cifrado de EBS se solicita al aprovisionar un volumen; cambiar una StorageClass no cifra retroactivamente un volumen existente. Este ejemplo de una clase nueva solicita almacenamiento gp3 cifrado con enlace de topología diferido y retención explícita. Si se requiere una clave administrada por el cliente, agregue un kmsKeyId real y revisado y prepare su política de clave y permisos para el driver; un ARN de ejemplo no es una clave operativa.

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

Configure el cifrado de EFS al crear el sistema de archivos mediante el flujo de infraestructura protegido de la Parte 1. Los datos existentes sin cifrar requieren una migración admitida a un sistema de archivos cifrado, no una opción de montaje. FSx for Lustre cifra automáticamente los datos en reposo: los sistemas scratch usan claves administradas por el servicio; elegir una clave KMS administrada por AWS o por el cliente es una opción de **sistemas de archivos persistentes**. No pase un customer kms-key-id al ejemplo SCRATCH_2.

Inspeccione los recursos reales de la nube, asocie los ID de EBS con los volumeHandles de PV enlazados y confirme la cuenta/región. Una respuesta de FSx para un sistema scratch sin una clave de cliente seleccionada no demuestra que el almacenamiento no esté cifrado:

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

Para los datos en tránsito, use la opción `tls` admitida por EFS CSI/asistente de montaje y compruebe la ruta de montaje real. El cifrado en tránsito de FSx depende de la configuración admitida de sistema de archivos/cliente/instancia; siga las indicaciones del servicio. **S3 HTTPS/TLS protege el transporte; `aws s3 cp --sse AES256` selecciona el cifrado en reposo SSE-S3.** Ese indicador no habilita TLS. Use endpoints HTTPS con validación de certificados y revise las políticas del bucket que exigen transporte seguro. La política de clave KMS es distinta de la administración de certificados de transporte.

### Control de acceso

Use la identidad CSI preparada en la Parte 1: el rol de Pod Identity/IRSA admitido por el controlador y los permisos exactos del driver, además de las concesiones de KMS que correspondan. No vuelva a crear la ServiceAccount de un complemento administrado existente mediante un comando de eksctl no relacionado ni traslade los permisos del controlador a todos los nodos/aplicaciones. La identidad de nivel de Pod de Mountpoint, los montajes EFS con IAM y las identidades POSIX/de puntos de acceso del sistema de archivos tienen rutas de autorización distintas.

Para el acceso de red, permita que el grupo de seguridad de origen del cliente/nodo real llegue a los destinos de montaje EFS por TCP 2049. Lustre requiere las reglas TCP 988 y 1018–1023 documentadas entre los clientes y servidores de archivos, incluido el tráfico necesario entre miembros. Lustre con EFA requiere, en cambio, las reglas especificadas de todo el tráfico referenciadas por grupos de seguridad; un CIDR abierto a Internet no las sustituye. Inspeccione también rutas, DNS, NACL y el origen de montaje CSI real, además de los grupos de seguridad. Una NetworkPolicy de Pod de Kubernetes no controla automáticamente todas las conexiones al sistema de archivos iniciadas por los nodos.

El lector con alcance de namespace que se muestra a continuación puede inspeccionar objetos PVC; no puede crearlos, redimensionarlos ni eliminarlos. El acceso a PV con alcance de clúster necesita un ClusterRole revisado por separado. Ninguno de los roles controla directamente los bytes de archivos. Un principal con permiso para crear Pods en un namespace podría montar sus PVC; por ello también se deben controlar la creación de Pods, la identidad de las cargas de trabajo, los permisos POSIX/de puntos de acceso y el aislamiento entre inquilinos:

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

### Contexto de seguridad del Pod

Este ejemplo completo separa runAsUser/runAsGroup/fsGroup/seccomp a nivel de Pod de allowPrivilegeEscalation/capabilities/readOnlyRootFilesystem a nivel de contenedor. Usa una clase cifrada preparada y un PVC declarado, en vez de un volumen data indefinido y una imagen nginx con rutas de ejecución escribibles que no se habían definido. La versión de la política del namespace corresponde al ejemplo revisado para Kubernetes 1.36; use la versión adecuada para su clúster.

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

Una raíz de solo lectura no vuelve de solo lectura a `/data`: esta carga de trabajo comprueba intencionalmente un PVC escribible. El comportamiento de fsGroup depende de CSI y del sistema de archivos; un punto de acceso EFS puede imponer otra identidad POSIX. Los perfiles SELinux/AppArmor requieren compatibilidad real del nodo/entorno de ejecución y una política preparada. No copie etiquetas MCS ni nombres de perfiles arbitrarios. Pod Security Standards restringe la configuración del Pod, pero no cifra volúmenes en la nube ni concede permisos IAM. Los agentes de supervisión/nodo CSI con acceso al host necesitan su propio diseño de seguridad/namespace revisado.

### Aplicación de políticas de seguridad

Un patrón de nombre de PVC o una lista de StorageClass permitidas por sí solos no demuestran que EBS esté cifrado. La siguiente **Kyverno ValidatingPolicy** usa la API servida `policies.kyverno.io/v1`, verificada con Kyverno 1.19.1 y su CRD. Requiere que el controlador/CRD esté instalado y que la administración de admisión tenga los permisos adecuados. En esa versión, los ejemplos antiguos de ClusterPolicy están obsoletos; migre intencionalmente en vez de dar por supuesta la compatibilidad de API.

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

La política comprueba el **parámetro de cifrado declarado al crear/actualizar una StorageClass de EBS**, incluido el aprovisionador Auto Mode. No inspecciona volúmenes AWS existentes, PV estáticos, contenido de snapshots ni rutas que evadan las condiciones de coincidencia. Restrinja la administración de StorageClass/PV y complemente la admisión con comprobaciones de cumplimiento del backend. Antes de aplicar la política ampliamente, pruébela con recursos representativos y supervise los informes de políticas y el estado del webhook. El cifrado de datos existentes requiere su propia migración.

## Prácticas recomendadas para administrar el almacenamiento {#storage-management-best-practices}

![Diagrama que relaciona las cuatro fases del ciclo de vida del almacenamiento (planificación, implementación, operación y optimización) con sus áreas de prácticas recomendadas (planificación y diseño, automatización e IaC, copias de seguridad y recuperación ante desastres, rendimiento y optimización de costos), cada una con sus tres prácticas en el orden indicado.](../.gitbook/assets/en-eks-04-eks-storage-part3-4.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-4.html)

### Planificación y capacidad

Documente por separado la latencia, IOPS/rendimiento, crecimiento de capacidad, patrones de lectura/escritura, concurrencia, disponibilidad, durabilidad y RPO/RTO. Según esos requisitos, elija almacenamiento de bloques, NFS compartido, Lustre paralelo o acceso a objetos. Use margen basado en mediciones y procedimientos de expansión acotados; un escalador automático o el redimensionamiento de PVC no proporciona replicación de aplicaciones ni reduce arbitrariamente la capacidad.

### Copias de seguridad y recuperación ante desastres

Use una programación compatible, identidades de copia de seguridad únicas y un responsable de retención. Una línea cron de shell que intenta crear repetidamente un snapshot con el mismo nombre falla después de crear el primer objeto; una copia de Velero puntual llamada daily-backup no constituye una programación. Con la instalación Velero/CSI revisada y los requisitos de coherencia de bases de datos de la Parte 2, este comando genera una programación diaria para revisión:

```bash
velero schedule create storage-daily --schedule="0 0 * * *" \
  --include-namespaces=storage-demo --ttl=720h0m0s -o yaml > storage-schedule-review.yaml
```

Tras revisarlo, impleméntelo mediante el responsable y genere alertas por copias faltantes/fallidas; pruebe restauraciones aisladas. Una copia de seguridad en S3 puede hacer referencia a snapshots nativos en lugar de contener todos los bytes del volumen. La recuperación entre zonas/regiones requiere datos accesibles, claves, correspondencias de driver/almacenamiento y validación de la aplicación. Conserve el origen hasta que se complete un cambio controlado; registre el tiempo de recuperación medido en vez de atribuir un RPO/RTO a una programación.

### Infraestructura como código y GitOps

Use los ejemplos protegidos de creación de sistemas de archivos de la Parte 1/Parte 2 o un módulo Terraform/CloudFormation propio con versiones de proveedor/esquema revisadas, configuración de subredes/destinos de montaje/grupos de seguridad y protección contra eliminación. Un recurso Terraform que solo cree el sistema de archivos no deja una ruta de montaje lista para EKS. Mantenga separadas la retención de copias y las acciones destroy/prune de IaC.

Los valores de Helm son entradas específicas de cada chart: el valor personalizado `storage.encrypted: true` no hace nada a menos que una plantilla lo convierta en el campo admitido del recurso real. Renderice y valide StorageClass/PVC/carga de trabajo antes del despliegue. El pruning de GitOps, la desinstalación del chart y la retención de claims pueden tener efectos distintos sobre los datos; documente qué sistema es responsable de cada recurso y pruebe los cambios del ciclo de vida con datos desechables.

Por ejemplo, este recurso de sistema de archivos solicita cifrado y rendimiento Elastic, conserva la política de ejemplo de transición a IA a los 30 días y añade una protección contra destroy de Terraform. Sustituya el token de creación por uno estable y específico del proyecto, configure el proveedor/la cuenta/la región y añada los recursos revisados de red/destino de montaje. prevent_destroy es una protección frente a operaciones de Terraform, no una copia de seguridad ni una defensa contra toda eliminación externa:

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

A medida que cambien las cargas de trabajo, revise los cuellos de botella, límites de aprovisionamiento, costos de retención y controles de seguridad. Mantenga los informes de limpieza en modo de solo lectura hasta verificar la propiedad de los recursos y los efectos sobre copias de seguridad, recuperación y eliminación. Antes de automatizar cambios, genere alertas y proponga ajustes acotados. Los ejemplos del capítulo son configuraciones de referencia verificadas localmente; el rendimiento del backend, el despliegue de admisión y la recuperación aún deben validarse en el entorno previsto.

## Conclusión

En este documento se trataron la supervisión, la solución de problemas, la optimización de costos y la seguridad del almacenamiento de Amazon EKS. Administrarlo correctamente es fundamental para mantener el rendimiento, la fiabilidad y la rentabilidad del clúster de EKS.

Los requisitos de almacenamiento varían según la aplicación, por lo que es importante comprender las características de la carga de trabajo y seleccionar la solución de almacenamiento adecuada. Además, administre eficazmente los recursos de almacenamiento mediante revisiones periódicas de supervisión, solución de problemas, costos y seguridad.

## Referencias

- [Prácticas recomendadas de almacenamiento de Amazon EKS](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)
- [Solución de problemas de almacenamiento de Kubernetes](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-application/#debugging-pods)
- [Seguridad del almacenamiento de Kubernetes](https://kubernetes.io/docs/concepts/security/)

- [Métricas de CloudWatch para EBS](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [Dimensiones de métricas de FSx Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [Modos de rendimiento de EFS](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [API del ciclo de vida de EFS](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [Cifrado en reposo de FSx](https://docs.aws.amazon.com/fsx/latest/LustreGuide/encryption-at-rest.html)
- [Acceso de red a FSx](https://docs.aws.amazon.com/fsx/latest/LustreGuide/limit-access-security-groups.html)
- [Cifrado en reposo de S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html)
- [Migración de CEL de Kyverno](https://kyverno.io/docs/guides/migration-to-cel/)

## Cuestionario

Para poner a prueba lo aprendido en este capítulo, responda el [cuestionario del tema](../quizzes/eks/04-eks-storage-part3-quiz.md).
