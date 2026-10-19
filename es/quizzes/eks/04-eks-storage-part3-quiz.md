# Cuestionario de almacenamiento de EKS - Parte 3

> **Última actualización**: 11 de septiembre de 2026.

Repase el monitoreo, el diagnóstico, los costos y la seguridad con los recopiladores y ejemplos de almacenamiento configurados en el capítulo. Los ejemplos siguientes se comprobaron localmente; no afirman que se hayan ejecutado operaciones en AWS, realizado una recuperación de producción ni verificado paneles en vivo. Sustituya los marcadores de posición y confirme quién es responsable de cada recurso antes de implementarlos.

## Preguntas de opción múltiple

### 1. ¿Qué cálculo permite obtener las IOPS de lectura a partir de VolumeReadOps?

- A. Usar Average directamente como IOPS
- B. Dividir Sum entre los segundos del período
- C. Multiplicar los bytes por la cantidad de Pods
- D. Usar VolumeQueueLength como IOPS completadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Divida Sum entre la duración del período en segundos. Para obtener bytes/s, normalice del mismo modo VolumeReadBytes/VolumeWriteBytes. VolumeTotalReadTime/VolumeTotalWriteTime acumulan segundos de operación: divida Sum por el Sum de las operaciones correspondientes para calcular los segundos medios por operación y contemple el caso de cero operaciones. No describa cada contador bruto como si fuera una tasa o una latencia.

Las métricas actuales de Nitro también incluyen VolumeAvgIOPS, VolumeAvgThroughput y métricas de latencia promedio, con sus unidades y limitaciones documentadas. BurstBalance se aplica a gp2/st1/sc1, no a gp3. Las métricas de bytes y bytes medidos de EFS, así como las métricas por OSS/OST de FSx, tienen dimensiones y estadísticas diferentes. kubelet_volume_stats_* puede proporcionar el uso del sistema de archivos cuando sea compatible; container_fs_usage_bytes no mide de forma universal el uso de los PVC.

</details>

### 2. ¿Qué debe comprobar primero si un PVC o un consumidor está en estado Pending?

- A. Eliminar el PVC de inmediato
- B. Conceder acceso completo a EC2 a todos los nodos
- C. Revisar los eventos, el modo de vinculación y las restricciones de planificación
- D. Suponer que un PVC sin vincular ya determina la AZ

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Revise el espacio de nombres, el claim, los eventos del consumidor, la StorageClass y la topología reales. WaitForFirstConsumer puede mantener intencionalmente un PVC nuevo en Pending hasta que se planifique un Pod; eso no indica automáticamente un fallo del driver. Después de vincularlo, importan la afinidad de nodo y la AZ del PV de EBS, así como los límites de conexión. Evite spec.nodeName si omite el planificador que se necesita para la vinculación.

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

Compruebe el rol real de Pod Identity/IRSA del driver y sus concesiones de KMS, no solo el perfil de instancia EC2 del nodo. Si el controlador tiene varios contenedores, seleccione el registro del driver o sidecar pertinente. ContainerCreating también puede deberse a la conexión o el montaje del volumen, el software cliente, la descarga de la imagen o los permisos de la aplicación. No elimine datos para intentar restablecer el estado.

</details>

### 3. ¿Qué método es apropiado para ajustar el almacenamiento de una base de datos?

- A. Medir y ajustar la configuración a los límites del volumen, el sistema de archivos y la instancia
- B. Habilitar siempre multiAttach:true
- C. Suponer que cualquier hostPath corresponde a un NVMe rápido
- D. Cambiar el planificador del disco raíz sin identificar el dispositivo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Mida el patrón de E/S, las colas, la latencia y los límites de la instancia; después, elija el tipo de almacenamiento y sus parámetros de rendimiento. Esta StorageClass io2 de 10,000 IOPS es una asignación ilustrativa, no una prueba de que cumpla el SLO de una base de datos:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '10000'
```

Multi-Attach no es un interruptor genérico para mejorar el rendimiento de cargas de solo lectura. La configuración de EBS CSI revisada usa io2, RWX y el modo de bloque sin procesar (raw Block), además de coordinación en la aplicación, como se describe en la Parte 2. Un hostPath llamado /mnt/instance-store no demuestra que apunte al almacén físico de la instancia; use un diseño de almacenamiento local al nodo preparado de antemano y trate sus datos como efímeros. EC2 instance-store CSI es una integración compatible, con sus propios requisitos previos.

No establezca noop en un planificador nvme0n1 supuesto: podría ser el disco raíz u otro dispositivo, y los nombres modernos de blk-mq son distintos. Identifique el dispositivo y el planificador compatible antes de evaluar por separado ese cambio. La selección del sistema de archivos y las opciones de montaje también requieren datos de la carga de trabajo; ni XFS ni ext4 garantizan por sí solos un resultado de rendimiento.

</details>

### 4. ¿Crear una StorageClass gp3 predeterminada migra los volúmenes gp2 existentes?

- A. Sí, todos los volúmenes conectados cambian de inmediato
- B. Sí, pero solo después de cambiar el nombre de la StorageClass
- C. Sí, las StorageClass predeterminadas cifran y migran los datos antiguos
- D. No; los volúmenes existentes requieren un procedimiento compatible independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

No. Una StorageClass controla el aprovisionamiento que se le aplica; no modifica todos los PV ya vinculados ni el almacenamiento de backend. Cambiar la StorageClass predeterminada puede afectar a otros claims nuevos que no estén relacionados. Elija una modificación compatible cuya gestión le corresponda o migre los datos, conserve puntos de recuperación y valide los datos de la aplicación. Ampliar y reducir capacidad son operaciones distintas; por lo general, no se puede reducir in situ el tamaño de un PVC o volumen EBS.

Compare la capacidad asignada, las IOPS y el rendimiento aprovisionados, la retención, las solicitudes y los costos de transferencia. Los descuentos de cómputo no reducen automáticamente los cargos independientes de almacenamiento. Una VolumeSnapshotClass no programa instantáneas; este ejemplo solo define el comportamiento de borrado para instantáneas temporales deliberadas:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: temporary-ebs-snapshots
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

No sustituya de forma general la StorageClass que el capítulo mantiene por esta clase temporal para reducir costos. La persona responsable de las copias de seguridad debe programar las instantáneas y gestionar su retención; Velero tiene su propio ciclo de vida de instantáneas CSI.

</details>

### 5. ¿Qué afirmación distingue correctamente los controles de seguridad del almacenamiento?

- A. El nombre de un PVC garantiza el cifrado
- B. Cada control requiere el alcance correcto y su correspondencia con los recursos reales
- C. Un Role puede conceder permisos sobre todos los PV del clúster
- D. PSS sustituye a IAM y KMS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

IAM/KMS, el acceso a la red, la autorización de la API de Kubernetes, la admisión y las identidades del sistema de archivos protegen operaciones distintas. Una lista de acciones de EC2 limitada a una región no constituye automáticamente una política CSI completa de privilegio mínimo. Use la política real del rol del driver y las concesiones de clave necesarias. Un kmsKeyId ficticio no crea una clave de KMS.

Los objetos Role con ámbito de espacio de nombres pueden conceder acceso a los PVC, pero no a los PV, que tienen ámbito de clúster. Quien puede crear Pods quizá pueda montar los PVC del espacio de nombres aunque este Role en particular no permita leer los objetos; proteja también la creación de cargas de trabajo y los límites entre tenants. El lector de espacios de nombres del capítulo es un ejemplo para inspeccionar objetos:

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

Los grupos de seguridad de EFS se aplican a destinos de montaje y clientes reales, no a un fragmento inventado de securityGroupSelector. Use la ruta real de TCP 2049; las reglas de Lustre/EFA son diferentes. Pod Security Standards no configura el cifrado en la nube ni los permisos de IAM.

</details>

### 6. ¿Qué afirmación sobre la integración de monitoreo es correcta?

- A. Un ConfigMap de Grafana recopila automáticamente métricas de PVC
- B. Prometheus conserva siempre los datos de forma indefinida
- C. Hay que configurar los recopiladores, el descubrimiento, la autorización y el almacenamiento
- D. CloudWatch nunca puede recibir métricas personalizadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

CloudWatch cubre las métricas nativas de los servicios; Prometheus puede recopilar las métricas de destinos de Kubernetes y de aplicaciones que se hayan configurado; Grafana visualiza las fuentes de datos configuradas. También hay que configurar recopiladores, descubrimiento de servicios, IAM/autenticación, retención, etiquetas y rutas de alertas. Un ConfigMap de paneles no crea por sí solo las métricas que faltan.

CloudWatch puede recibir métricas personalizadas o de Kubernetes mediante un agente o una integración configurados, y Prometheus no es automáticamente un almacén duradero a largo plazo. Elija una política de retención y una arquitectura de almacenamiento o escritura remota adecuadas a la carga. La administración automatizada debe empezar por la observación y propuestas acotadas, no por cambios incondicionales.

</details>

### 7. ¿Qué observación, por sí sola, autoriza a eliminar un volumen?

- A. El PV está Available
- B. El PVC no aparece en ningún Pod actual
- C. La anotación lastUsed es antigua
- D. Ninguna de estas observaciones por sí sola

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Pueden importar los datos retenidos, los controladores escalados a cero, los Jobs futuros, las obligaciones de copia de seguridad y los responsables externos. lastUsed no es un campo estándar y fiable para determinar el uso de un PVC. Conserve el espacio de nombres y el UID, y compruebe la identidad del backend antes de cualquier limpieza.

</details>

### 8. ¿kubectl top pods mide el uso de disco de un PVC?

- A. No; principalmente informa sobre CPU y memoria
- B. Sí; el uso de memoria equivale al de disco
- C. Sí; enumera todos los bloques libres de EBS
- D. Solo si la StorageClass se llama gp3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Use estadísticas del sistema de archivos compatibles, obtenidas desde la ruta montada y el driver correctos, e identifique el PVC real. df dentro de un contenedor podría describir otro montaje o el sistema de archivos EFS compartido; una solicitud de PVC de EFS no establece una cuota por directorio.

</details>

### 9. ¿Cómo se configura el ciclo de vida de EFS IA/Archive?

- A. Con parámetros performanceMode arbitrarios en una StorageClass de punto de acceso
- B. Mediante la configuración del ciclo de vida del sistema de archivos, conservando las transiciones previstas
- C. Reduciendo la solicitud de un PVC
- D. Cambiando una etiqueta del Pod a IA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los parámetros de puntos de acceso de EFS CSI no configuran todas las propiedades de rendimiento ni de ciclo de vida del sistema de archivos. Lea las políticas existentes antes de actualizar la lista: una lista vacía desactiva la administración del ciclo de vida. Elastic es el punto de partida recomendado cuando la demanda es impredecible; Archive tiene requisitos específicos de disponibilidad y orden de transición.

</details>

### 10. ¿Qué selecciona aws s3 cp --sse AES256?

- A. La versión del protocolo TLS
- B. El cifrado de NetworkPolicy
- C. El cifrado en reposo SSE-S3
- D. El cifrado del montaje EFS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

HTTPS/TLS protege los datos en tránsito; --sse no lo habilita. Use el endpoint correcto y valide los certificados. Los datos de FSx scratch se cifran con claves administradas por el servicio; las claves de cliente seleccionables solo están disponibles para los sistemas de archivos persistentes.

</details>

## Preguntas de respuesta breve

### 11. ¿Cómo se deben validar los cálculos de tasas y las previsiones de capacidad?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Compruebe las unidades, los períodos, los datos ausentes y los escenarios representativos**

En un intervalo de 300 segundos, 30,000 operaciones de lectura completadas equivalen a 100 IOPS de lectura. Los 1,500 segundos de lectura acumulados divididos entre 30,000 operaciones equivalen a 0.05 segundos por operación, o 50 milisegundos. Las operaciones superpuestas pueden hacer que el tiempo acumulado supere el tiempo transcurrido. Use períodos alineados y trate por separado los períodos con cero operaciones o sin muestras.

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

Son ejemplos aritméticos, no resultados medidos de una carga de trabajo. Use predict_linear para proyectar gauges, no contadores; elimine series duplicadas de scrape y excluya capacidades no válidas. Una tendencia reciente no garantiza que la capacidad se agote en el futuro. Las reglas del capítulo se probaron con datos sintéticos para casos de uso elevado sostenido, destinos duplicados, capacidad cero, series ausentes y uso creciente.

</details>

### 12. ¿En qué se diferencian la identidad CSI, Multi-Attach y el almacenamiento local al nodo?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Resuelven, respectivamente, problemas de autorización, conexión y ubicación**

La identidad del controlador CSI autoriza las API de ciclo de vida del backend; no es la identidad de cada aplicación. EBS Multi-Attach permite conectar de forma compartida un dispositivo de bloques sin procesar, sujeto a restricciones del servicio, del driver y de la AZ, y requiere coordinación de escrituras y mecanismos de fencing en la aplicación. Un campo multiAttach arbitrario en una StorageClass no es una opción compatible.

El almacenamiento de instancia local al nodo (instance store) está físicamente ligado al ciclo de vida del nodo y requiere aprovisionar y planificar correctamente el dispositivo. Una ruta hostPath no demuestra cuál es el dispositivo subyacente ni cuánto duran sus datos. Reutilice las configuraciones CSI revisadas en el capítulo; no conceda privilegios ni formatee un disco supuesto para hacer funcionar un ejemplo de rendimiento.

</details>

### 13. ¿Qué pueden demostrar la admisión y el registro de auditoría de EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Solo el alcance de solicitudes configurado y los eventos registrados**

La ValidatingPolicy de Kyverno, de la API policies.kyverno.io/v1, que se incluye en el capítulo, comprueba el parámetro de cifrado declarado en las StorageClass de EBS que coinciden. No inspecciona los volúmenes de AWS existentes, el contenido de los PV estáticos ni todas las vías para eludirla. Además de la admisión, restrinja los permisos administrativos y verifique el cifrado real del backend.

EKS administra la política de auditoría del plano de control; pida a quien administra el clúster que habilite el tipo de registro compatible y revise los registros entregados. Un fragmento de política audit.k8s.io pegado no es una API de EKS para reemplazar la política administrada. Los eventos de auditoría de Kubernetes y los eventos de API de backend de CloudTrail se complementan, pero tienen políticas de retención, acceso y cobertura independientes. El registro de auditoría no evita por sí solo la pérdida de datos.

</details>

## Preguntas prácticas

### 14. Cree una configuración revisable de monitoreo y paneles.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Configure cada dependencia de forma explícita**

Use la pila de monitoreo y los recopiladores revisados en el capítulo; no suponga que un ConfigMap instala por sí solo un agente. Para una instalación tradicional del agente de CloudWatch, inspeccione el espacio de nombres, la carga de trabajo y la identidad reales. Adapte estos nombres a la integración elegida y a la compatibilidad del tipo de cómputo:

```bash
set -euo pipefail
kubectl -n amazon-cloudwatch get daemonsets,pods
kubectl -n amazon-cloudwatch get serviceaccount cloudwatch-agent -o yaml
```

El [ejemplo de monitoreo del clúster](../../eks/02-eks-cluster-creation-part3.md) cubre los requisitos previos del agente o add-on administrado. Un receptor StatsD no genera automáticamente métricas de EBS/PVC. No añada claves estáticas de AWS ni habilite un agente duplicado para completar un panel.

Para EBS CSI, habilite la configuración de métricas compatible mediante el responsable actual. Use los monitores generados por el capítulo **o** el monitor independiente siguiente si ya existe el Service; evite recopilar las mismas métricas dos veces. Prometheus debe seleccionar el espacio de nombres y las etiquetas del monitor, y acceder al puerto con nombre de su Service:

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

Instale las reglas de recording y alertas del capítulo mediante el responsable del monitoreo; después, verifique que los destinos estén Up, que existan las series esperadas y que se entreguen las alertas. El endpoint del driver EBS informa métricas de operaciones CSI, no todas las métricas de sidecars ni el uso bruto del sistema de archivos.

Este ConfigMap contiene un **modelo de panel Classic** para despliegues que admiten esa vía de importación o aprovisionamiento. Grafana también dispone actualmente de los modelos V1 Resource y V2 Resource (predeterminado); no envíe este objeto Classic sin envoltorio a otra API que espere un contenedor de recurso. Sustituya el UID de la fuente de datos de Prometheus, compruebe que existan las reglas de recording de origen y haga coincidir la configuración de etiquetas y espacios de nombres del sidecar de Grafana. Exporte e importe el modelo con la versión de Grafana de destino antes de adoptarlo:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: storage-dashboard-reviewed
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  storage-dashboard.json: |
    {
      "id": null,
      "uid": "eks-storage-reviewed",
      "title": "EKS Storage: PVC Filesystem Usage",
      "tags": [
        "storage"
      ],
      "timezone": "browser",
      "schemaVersion": 42,
      "version": 1,
      "refresh": "30s",
      "time": {
        "from": "now-6h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "type": "timeseries",
          "title": "PVC filesystem utilization",
          "gridPos": {
            "x": 0,
            "y": 0,
            "w": 24,
            "h": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "(pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max) and (pvc:storage_capacity_bytes:max > 0)",
              "legendFormat": "{{cluster}} {{namespace}}/{{persistentvolumeclaim}}"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percentunit",
              "min": 0,
              "max": 1
            },
            "overrides": []
          }
        }
      ]
    }
```

Para añadir paneles nativos de IOPS de EBS o rendimiento de EFS, configure la fuente de datos de CloudWatch con acceso de IAM revisado y use las dimensiones de métricas y los cálculos normalizados por período de la fuente. No invente series aws_ebs_* de Prometheus a menos que un exporter configurado publique realmente esos nombres y significados. El JSON y las expresiones se inspeccionaron localmente; no se importó el panel en una instancia autenticada de Grafana ni se consultó AWS en vivo.

</details>

### 15. Genere un inventario de almacenamiento sin suponer que sea seguro eliminar recursos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Informe las pruebas; no deduzca que se puede eliminar un recurso**

Sustituya el CronJob de marcador de posición antiguo por un informe de solo lectura. El siguiente script conserva el espacio de nombres y el UID, enumera las referencias directas de Pods y se niega explícitamente a autorizar eliminaciones. No deduce la antigüedad a partir de lastUsed, no considera que Bound signifique que un recurso está sin usar y no omite espacios de nombres en una consulta de todo el clúster.

```python
"""Report direct Pod/PVC references; never infer deletion eligibility."""
import json,sys
def inventory(namespace,claims,pods):
    refs={}
    for pod in pods['items']:
        meta=pod['metadata']
        if meta['namespace']!=namespace:raise ValueError('Pod list contains another namespace')
        seen=set()
        for volume in pod.get('spec',{}).get('volumes',[]):
            claim=volume.get('persistentVolumeClaim',{}).get('claimName')
            if claim and claim not in seen:
                seen.add(claim)
                refs.setdefault(claim,[]).append({'pod':meta['name'],'podUID':meta['uid'],'phase':pod.get('status',{}).get('phase','Unknown')})
    rows=[]
    for pvc in claims['items']:
        meta,spec=pvc['metadata'],pvc.get('spec',{})
        if meta['namespace']!=namespace:raise ValueError('PVC list contains another namespace')
        rows.append({'namespace':namespace,'name':meta['name'],'uid':meta['uid'],
          'phase':pvc.get('status',{}).get('phase','Unknown'),'volumeName':spec.get('volumeName'),
          'storageClassName':spec.get('storageClassName'),'requestedStorage':spec.get('resources',{}).get('requests',{}).get('storage'),
          'directPodReferences':refs.get(meta['name'],[]),'ownerReferences':meta.get('ownerReferences',[]),
          'deletionAuthorized':False,'nextAction':'Review owner, controller templates, retention, backups and actual backend before any change'})
    return {'reviewOnly':True,'namespace':namespace,'rows':sorted(rows,key=lambda x:x['name']),
      'limitations':['The two API reads are not an atomic snapshot.','No Pod reference does not mean unused: scale-to-zero controllers, future Jobs, retained data and indirect/ephemeral references need separate review.','lastUsed is not a standard trustworthy Kubernetes PVC field. This report never authorizes snapshot creation or deletion.']}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: storage-inventory.py namespace pvcs.json pods.json')
    with open(sys.argv[2]) as f:claims=json.load(f)
    with open(sys.argv[3]) as f:pods=json.load(f)
    print(json.dumps(inventory(sys.argv[1],claims,pods),indent=2))
```



```bash
set -euo pipefail
: "${STORAGE_NAMESPACE:?Set the namespace being reviewed}"
kubectl -n "$STORAGE_NAMESPACE" get pvc -o json > inventory-pvcs.json
kubectl -n "$STORAGE_NAMESPACE" get pods -o json > inventory-pods.json
python3 storage-inventory.py "$STORAGE_NAMESPACE" inventory-pvcs.json inventory-pods.json
```

La identidad que realiza la consulta solo necesita permisos de lectura en este espacio de nombres. Este Role es un ejemplo del alcance; si hace falta, vincúlelo con la identidad revisada del operador o de la automatización. No concede permisos para crear instantáneas, cambiar tamaños ni eliminar recursos:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: storage-inventory-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - persistentvolumeclaims
  verbs:
  - get
  - list
```

Revise por separado las plantillas de controladores escalados a cero, los Jobs/CronJobs, los claims retenidos, las referencias indirectas o efímeras, la política de copias de seguridad y los IDs reales del backend. Que un Pod actual no haga referencia a un recurso no es motivo suficiente para eliminarlo. Si más adelante programa este informe, use una imagen real y revisada que incluya el script y el cliente, ejecución acotada, credenciales de alcance limitado y un destino definido para el informe; storage-tools:latest y los comandos con puntos suspensivos no constituyen una implementación.

Primero automatice la observación; después, las propuestas de cambio acotadas y la recuperación validada de forma independiente. El crecimiento de EBS/PVC no permite reducir la capacidad arbitrariamente. Conserve pruebas de auditoría, defina quién administra el ciclo de vida y aplique controles explícitos de aprobación y operación adecuados al despliegue; no use un script que destruya recursos silenciosamente.

</details>

## Revise sus respuestas

Hay 15 preguntas, incluidas 10 de opción múltiple. Use las respuestas incorrectas para identificar los temas que debe repasar; la puntuación del cuestionario por sí sola no demuestra experiencia en producción. En las respuestas prácticas, evalúe los supuestos, el alcance de los recursos y las pruebas de validación, además de la sintaxis.

## Referencias

- [Capítulo de referencia](../../eks/04-eks-storage-part3.md)
- [Métricas de EBS](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [Métricas de FSx](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [API del ciclo de vida de EFS](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [Auditoría de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)
- [Modelos de panel de Grafana](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)
