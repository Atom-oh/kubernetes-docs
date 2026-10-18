# Operaciones y administración

> **Versiones compatibles**: EKS Auto Mode GA; versión de referencia de ejemplo: EKS 1.36
> **Última actualización**: September 12, 2026

Las operaciones del día 2 deben distinguir entre la capacidad deseada, el ciclo de vida de los nodos, la disponibilidad de las aplicaciones y las señales que realmente se recopilan. Los ejemplos siguientes son configuraciones de laboratorio controladas, no un procedimiento operativo de producción probado. Durante esta auditoría no se realizaron cambios en recursos de la nube ni ejecuciones de nodos/Pod activos.

Los manifiestos de NodePool se comprobaron con el esquema estructural de Karpenter 1.14.1 publicado. Los ejemplos de cargas de trabajo superaron las comprobaciones del esquema estructural de Kubernetes 1.36.2 y de la política Restricted de Pod Security; se verificaron la etiqueta y el digest del índice de la imagen nginx, así como el diseño documentado sin privilegios de root. Las extracciones de imágenes en tiempo de ejecución, IAM, las redes y el comportamiento de las aplicaciones aún deben validarse en su entorno.

## Confirmar el contexto operativo

Use credenciales temporales y el kubeconfig previsto. Esta comprobación de solo lectura compara la cuenta y el endpoint directo de la API; si el kubeconfig usa deliberadamente un proxy, debe revisarse por separado, no eludirse una discrepancia.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${AWS_REGION:?Set the cluster region}"
: "${CLUSTER_NAME:?Set the intended cluster name}"
: "${KUBECONFIG:?Set the reviewed kubeconfig path}"
export KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-ops.XXXXXXXX")
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,endpoint:endpoint}' --output json > "$WORK_DIR/cluster.json"
endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$WORK_DIR/cluster.json" >/dev/null
printf 'Private diagnostic directory: %s\n' "$WORK_DIR"
```

Los manifiestos suponen que se ha revisado un NodeClass `default`. Seleccione solo los ejemplos que necesite, sustituya deliberadamente los nombres de recursos y los identificadores de red, y revise la capacidad y los costos resultantes. Los pools de laboratorio usan una taint `ops-lab` y las cargas de trabajo usan tolerations y selectores de pool coincidentes; son controles de ubicación, no una frontera de seguridad entre tenants.

## Los presupuestos se combinan, no se sustituyen

Cada presupuesto de NodePool aplicable contribuye al mínimo permitido de disrupciones. Agregar un presupuesto programado de `30%` no puede hacer más permisivo un presupuesto siempre activo de `10%`. Los porcentajes se redondean hacia arriba, y los nodos que se están eliminando o no están listos reducen la cantidad restante permitida.

Este calendario explícito usa un límite máximo del 30%, un límite máximo del 10% entre semana y un límite de un nodo durante el horario laboral. Los horarios de Karpenter están en UTC:

| Entrada | Horario UTC | Ventana prevista |
|-------|--------------|-----------------|
| 30% | Siempre | Límite máximo exterior |
| 10% | Domingo–jueves 15:00, duración 24h | Días naturales de lunes a viernes en Seúl |
| 1 nodo | Lunes–viernes 00:00, duración 9h | Horario laboral de Seúl: 09:00–18:00 |
| 0 nodos | Primer día del mes 00:00, duración 24h | Congelación mensual explícita en **UTC** |

Para 20 nodos que, por lo demás, están en buen estado, el ejemplo permite seis nuevas disrupciones voluntarias durante el fin de semana, dos entre semana fuera del horario laboral, una durante el horario laboral y cero durante la congelación. Estas son opciones de política de ejemplo, no recomendaciones universales para producción.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-calendar
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 30%
    - nodes: 10%
      schedule: 0 15 * * sun-thu
      duration: 24h
    - nodes: '1'
      schedule: 0 0 * * mon-fri
      duration: 9h
    - nodes: '0'
      schedule: 0 0 1 * *
      duration: 24h
  limits:
    cpu: '100'
    memory: 400Gi
```

Los intervalos cron horarios anteriores `9-18`/`9-21` y las ventanas repetidas de fin de semana de 48 horas se superponían más allá de las horas indicadas. Un horario inicia una ventana; no es una lista de horas durante las cuales debe reiniciarse una ventana larga.

## Sustitución y disponibilidad de las aplicaciones

Un presupuesto de un nodo limita la frecuencia de las acciones graduales aplicables. No garantiza que la expiración, la interrupción o la reparación ocurran secuencialmente. `expireAfter` no es una promesa de tiempo de actividad mínimo, y cambiarlo no reescribe los NodeClaims existentes. Siguen aplicándose el comportamiento predeterminado de expiración/gracia de Auto Mode y la vida útil máxima.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-rolling
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
    - nodes: '1'
  limits:
    cpu: '100'
    memory: 400Gi
```

Una política de consolidación para nodos vacíos no deshabilita el drift ni la expiración. `do-not-disrupt` no garantiza una retención indefinida: los controles de Node y Pod tienen ámbitos distintos, y un período de gracia de terminación explícito o predeterminado cambia la forma en que los Pod bloqueantes afectan al drift y a la terminación final. Revise la [guía de disrupciones](https://karpenter.sh/v1.14/concepts/disruption/) antes de usarlo para una ventana de mantenimiento.

### Ejemplo de PDB

El siguiente namespace fija la política Restricted a la versión de Kubernetes revisada. La imagen se ejecuta como UID/GID 101, escucha en el puerto 8080 y usa `/tmp` para las rutas de PID y archivos temporales; necesita el emptyDir con permisos de escritura aunque el sistema de archivos raíz del contenedor sea de solo lectura. La señal de detención de la imagen es SIGQUIT. Estos detalles no son intercambiables con una imagen nginx que se ejecute como root en el puerto 80.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ops-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: ops-lab
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: ops-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-calendar
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

Con cinco réplicas deseadas en buen estado, `minAvailable: 3` permite desalojar voluntariamente hasta dos Pod, sujeto a otras restricciones. `maxUnavailable: 1` sería una opción diferente y más restrictiva, no una forma equivalente de expresarlo.

Los PDB restringen las decisiones de la API de Eviction mediante Pod saludables/Ready; no hacen que existan réplicas ni protegen frente a todos los fallos o eliminaciones directas. Los valores porcentuales se redondean hacia arriba: `minAvailable: "80%"` para seis réplicas exige cinco réplicas saludables, mientras que un presupuesto `maxUnavailable: "30%"` para una réplica puede permitir que esa única réplica sea desalojada.

Para los sistemas con estado, use la semántica real de quórum y disponibilidad de la aplicación. Dos miembros saludables pueden ser adecuados para un sistema de mayoría con tres votantes; un sistema con cinco votantes necesita tres. No hay una recomendación única de `minAvailable: 2` que se ajuste a todas las cargas de trabajo con estado. Un PDB para una única réplica puede bloquear deliberadamente el vaciado voluntario, pero no puede proporcionar alta disponibilidad.

## La ubicación en AZ no garantiza capacidad ni failover

El límite `limits.cpu` del pool dinámico es un límite agregado, no un mínimo por AZ. El ejemplo enumera las AZ posibles, pero las subnets de NodeClass, la capacidad y las restricciones de programación determinan cuáles son aptas.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-multi-az
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
        - ap-northeast-2b
        - ap-northeast-2c
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
  namespace: ops-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: ha-app
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: ha-app
      containers:
      - name: app
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-multi-az
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 60
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

Seis réplicas no demuestran por sí solas una distribución de 3 AZ × 2. Este ejemplo exige al menos dos dominios aptos; ajuste el valor solo después de evaluar la cobertura real de sus subnets y la política de fallos. Las restricciones estrictas `DoNotSchedule` pueden dejar los Pod en estado Pending durante una incidencia en una AZ.

Si necesita una réplica por nodo, puede añadir el siguiente fragmento de afinidad a una plantilla de Pod revisada. Nueve réplicas con esta restricción requieren al menos nueve nodos aptos; aun así, no demuestran disponibilidad en tres AZ sin la topología y la capacidad correspondientes.

```yaml
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector:
      matchLabels:
        app: ha-app
    topologyKey: kubernetes.io/hostname
```

Los diseños activo-activo/en espera también necesitan estado de la aplicación, comprobaciones de estado y controles del tráfico/failover. ARC zonal shift es compatible con Auto Mode y puede evitar nueva capacidad en una AZ afectada; autoshift necesita su propia configuración. No hace que un volumen vinculado a una AZ ni una restricción estricta de ubicación puedan trasladarse a otra zona.

### Reservas de capacidad existentes

Llamar `reserved-capacity` a un pool, permitir On-Demand y establecer un límite de CPU no crea una reserva. Para consumir una reserva existente aprobada, selecciónela en un NodeClass personalizado y permita la capacidad `reserved`. Sustituya el ID de reserva de ejemplo y verifique la cuenta, la AZ, el tipo, el estado, los permisos y la capacidad reservada disponible.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: reserved-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  capacityReservationSelectorTerms:
  - id: cr-0123456789abcdef0
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reserved-capacity
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: reserved-nodeclass
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
```

Estos manifiestos no crean la reserva de EC2 ni un número fijo de nodos. Las reservas pueden generar cargos aunque no se utilicen. Para establecer cantidades de nodos deseadas independientes de la demanda de Pod, Auto Mode admite pools estáticos mediante `spec.replicas`, con semánticas distintas para límites/peso/consolidación y escalado; consulte la referencia de capacidad estática. Un número deseado sigue dependiendo de que el aprovisionamiento se realice correctamente y de que la capacidad esté en buen estado.

## La supervisión debe corresponderse con su publicador

Las métricas del plano de control de EKS, Container Insights configurado, los exportadores de Prometheus autogestionados y los registros de componentes de Auto Mode son interfaces distintas. No dé por sentado que se rellena automáticamente un namespace `Karpenter` de CloudWatch que contenga los nombres `karpenter_*` anteriores.

Los registros de cómputo, almacenamiento, balanceador de carga e IPAM administrados por Auto Mode usan una entrega de Vended Logs configurada por separado. El registro básico del plano de control no activa todos los registros de los componentes administrados. Elija un intervalo de tiempo acotado y verifique IAM, el destino y los cargos.

### Crear un dashboard a partir de metadatos de métricas reales

Para el namespace del plano de control `AWS/EKS`, primero descubra las métricas que se devuelven realmente para el clúster revisado:

```bash
check_account
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace AWS/EKS \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" --output json \
  > "$WORK_DIR/metric-catalog.json"
jq '.Metrics | to_entries | map({index:.key,metric:.value})' "$WORK_DIR/metric-catalog.json"
```

Elija el índice exacto del catálogo y la estadística documentada adecuada para la métrica. El siguiente generador local conserva el namespace y las dimensiones reales e incluye la región del widget. Rechaza una entrada ausente o de otro clúster en vez de crear un panel con una métrica inventada.

```bash
: "${METRIC_INDEX:?Choose an exact entry from the captured catalog}"
: "${METRIC_STAT:?Choose the documented statistic for that metric, such as Maximum}"
export METRIC_INDEX METRIC_STAT AWS_REGION CLUSTER_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
folder = Path(os.environ["WORK_DIR"])
metrics = json.loads((folder / "metric-catalog.json").read_text())["Metrics"]
index = int(os.environ["METRIC_INDEX"])
if index < 0 or index >= len(metrics):
    raise SystemExit("Metric is absent; verify collection instead of creating an empty widget")
metric = metrics[index]
if metric["Namespace"] != "AWS/EKS" or not any(
    d["Name"] == "ClusterName" and d["Value"] == os.environ["CLUSTER_NAME"]
    for d in metric["Dimensions"]
):
    raise SystemExit("Metric catalog entry does not match the reviewed cluster")
stat = os.environ["METRIC_STAT"]
if stat not in {"Average", "Sum", "Minimum", "Maximum", "SampleCount"}:
    if not re.fullmatch(r"p[0-9]+(?:\.[0-9]+)?", stat) or not 0 <= float(stat[1:]) <= 100:
        raise SystemExit("Unsupported statistic for this template")
series = [metric["Namespace"], metric["MetricName"]]
for dim in sorted(metric["Dimensions"], key=lambda d: d["Name"]):
    series.extend([dim["Name"], dim["Value"]])
body = {"widgets": [{"type": "metric", "x": 0, "y": 0, "width": 12, "height": 6,
    "properties": {"title": metric["MetricName"], "region": os.environ["AWS_REGION"],
                   "view": "timeSeries", "metrics": [series], "stat": stat, "period": 60}}]}
(folder / "dashboard.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

Revise `dashboard.json` antes de crear/actualizar un dashboard mediante el flujo de trabajo aprobado. La presencia en el catálogo no demuestra que haya puntos de datos en todos los intervalos de tiempo. Los recuentos de NodePool, la latencia de aprovisionamiento y los SLO de las aplicaciones necesitan sus publicadores/instrumentación reales; no debe suponerse que Container Insights por sí solo produzca todas las señales.

## Diagnósticos estructurados de Kubernetes

Use las condiciones de NodeClaim en lugar de un `.status.phase` inexistente, y evite tratar cada Pod Pending como una solicitud de capacidad de nodo:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodepools -o json |
  jq '[.items[] | {name:.metadata.name,limits:.spec.limits,resources:.status.resources,
      requirements:.spec.template.spec.requirements,disruption:.spec.disruption,
      conditions:[.status.conditions[]? | {type,status,reason,observedGeneration}]}]'
```

```bash
: "${WORKLOAD_NAMESPACE:?Select the workload namespace}"
: "${POD_NAME:?Select the Pod}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pod "$POD_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,phase:.status.phase,
       nodeSelector:.spec.nodeSelector,affinity:.spec.affinity,tolerations:.spec.tolerations,
       conditions:[.status.conditions[]? | {type,status,reason,lastTransitionTime}],
       containers:[.status.containerStatuses[]? |
         {name,ready,restartCount,waitingReason:.state.waiting.reason}]}'
```

Para la distribución de nodos, analice campos estructurados en lugar de una columna de una tabla legible por humanos. Esto cuenta los objetos Pod activos, incluidos los Pod asignados que aún no están listos, y separa los objetos sin asignar:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
  jq '[.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed") |
       {node: (.spec.nodeName // "(unscheduled)"), namespace: .metadata.namespace, pod: .metadata.name}] |
      group_by(.node) | map({node: .[0].node, activePodObjects: length})'
```

Use `kubectl top` solo cuando la API de métricas esté configurada y en buen estado. Una consulta fallida no demuestra que metrics-server esté ausente. Revise los motivos de los eventos y los registros de cómputo administrados para identificar fallos reales, como tipos de instancia incompatibles, falta de disponibilidad de NodeClass, problemas de IAM o de red. Reducir `consolidateAfter` no acelera la recuperación ante una interrupción de Spot.

### La autorización del PDB no es un veredicto de cumplimiento

Que `disruptionsAllowed` sea cero puede ser intencional y estar en buen estado. Compruebe que la generación esté actualizada y compare el estado actual con el deseado antes de interpretarlo:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[] | {
    namespace: .metadata.namespace, name: .metadata.name,
    currentHealthy: .status.currentHealthy, desiredHealthy: .status.desiredHealthy,
    disruptionsAllowed: .status.disruptionsAllowed,
    assessment: (if .status.observedGeneration != .metadata.generation
                    or .status.currentHealthy == null or .status.desiredHealthy == null
                    or .status.disruptionsAllowed == null
                  then "UnknownOrStale"
                  elif .status.currentHealthy < .status.desiredHealthy then "BelowDesiredHealthy"
                  elif .status.disruptionsAllowed == 0 then "HealthyNoVoluntaryEvictions"
                  else "EvictionsPermitted" end)
  }]'
```

No elimine ni flexibilice un PDB bloqueante hasta comprender los requisitos de disponibilidad de la carga de trabajo y el plan de recuperación.

### Antigüedad del objeto Node

La fecha de creación del objeto Node no es la fecha de lanzamiento de EC2 ni la antigüedad de los parches de la AMI. Elija un umbral de diagnóstico adecuado para su política; el script anterior, que comprobaba si la antigüedad era “superior a siete días completos”, truncaba el tiempo y suponía un límite universal inadecuado.

```bash
: "${MAX_NODE_OBJECT_AGE_HOURS:?Set a reviewed diagnostic threshold in hours}"
export MAX_NODE_OBJECT_AGE_HOURS
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
  jq '{items:[.items[] | {name:.metadata.name,createdAt:.metadata.creationTimestamp}]}' \
  > "$WORK_DIR/node-times.json"
python3 - <<'PY'
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
limit = float(os.environ["MAX_NODE_OBJECT_AGE_HOURS"])
if not math.isfinite(limit) or limit <= 0:
    raise SystemExit("Set a finite positive threshold")
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-times.json").read_text())["items"]:
    result = {"node": item["name"], "thresholdHours": limit}
    try:
        created = datetime.fromisoformat(item.get("createdAt").replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("timestamp is not usable")
        hours = (now - created).total_seconds() / 3600
        result.update(nodeObjectAgeHours=round(hours, 3), exceedsThreshold=hours > limit)
    except (ValueError, TypeError, AttributeError):
        result["assessment"] = "UnknownTimestamp"
    rows.append(result)
print(json.dumps(rows, indent=2))
PY
```

Las marcas de tiempo desconocidas o futuras no se consideran saludables. Compare la política observada de NodeClaim, la información de la imagen y el contexto de mantenimiento/seguridad de AWS antes de diagnosticar una rotación atrasada. Este informe local no crea una alarma de CloudWatch.

## Configuración de seguridad

Auto Mode selecciona su imagen Bottlerocket administrada y la configuración fija de IMDSv2/límite de saltos. El ejemplo anterior con `amiFamily`, `metadataOptions`, `blockDeviceMappings` y un ARN de KMS mal formado no era una configuración válida de NodeClass para Auto Mode.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ops-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
```

Revise el rol de nodo y la access entry del perfil, el enrutamiento privado real y las reglas del grupo de seguridad. Las etiquetas por sí solas no demuestran que la red esté restringida. El cifrado de los volúmenes EBS raíz/de datos de los nodos no establece el cifrado de los PVC de las aplicaciones. Para una clave administrada por el cliente o un paquete de CA, siga el procedimiento válido de `ephemeralStorage.kmsKeyID`/certificados en [Configuración de NodePool](./02-nodepool-configuration.md), con políticas de IAM y de claves revisadas.

El ejemplo de namespace Restricted requiere contextos de seguridad compatibles para las cargas de trabajo. No fuerce agentes de supervisión a nivel de nodo con acceso al host dentro de él ni deshabilite la seguridad de todo el clúster para que funcione un agente; revise los permisos independientes del colector y la política del namespace.

## Consultas y alertas opcionales de Prometheus

Estos ejemplos suponen **un clúster**, un colector kube-state-metrics instalado y métricas de node-exporter para Linux. Antes de usarlos:

- Permita las etiquetas de Node `karpenter.sh/nodepool` y `eks.amazonaws.com/compute-type` en kube-state-metrics.
- Asegúrese de que la serie de CPU tenga una etiqueta `node` correctamente asignada. Esa etiqueta no está presente automáticamente en todas las configuraciones de scrape de node-exporter.
- Deduzca las réplicas de kube-state-metrics antes de hacer uniones/recuentos. Debe haber una etiqueta de NodePool actual por nodo.
- Para varios clústeres, conserve una etiqueta de clúster real en todas las fuentes e inclúyala en cada agrupación y unión.

Las consultas de nodos filtran los nodos de Auto Mode; las señales de Pod Pending/no programables abarcan todo el clúster y requieren un diagnóstico antes de atribuirlas a Auto Mode. El uso de CPU que se muestra a continuación es el **tiempo no inactivo por nodo**, no una proporción de solicitudes de recursos ni una media del pool ponderada por capacidad. Una serie ausente no equivale automáticamente a un uso de cero.

```promql
# nodes_by_pool
count by (label_karpenter_sh_nodepool) (max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))

# cpu
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",node!=""}[5m])))
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# pending
sum(max by (namespace, pod, uid) (kube_pod_status_phase{phase="Pending"}))

# unschedulable
sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable))

# age
((time() - max by (node) (kube_node_created)) / 86400)
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# not_ready
max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})
```

Con Prometheus Operator instalado, coloque la siguiente regla en un namespace seleccionado por su instancia de Prometheus y que coincida con su `ruleSelector`. Los umbrales y las duraciones son ilustrativos. Las reglas no demuestran que todos los fallos de aprovisionamiento queden representados por un contador de terminaciones.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: auto-ops-example
  namespace: monitoring
spec:
  groups:
  - name: auto-ops-example
    rules:
    - alert: ReportedUnschedulablePods
      expr: sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable)) > 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Reported unschedulable Pods exceed the example threshold
    - alert: AutoNodeNotReady
      expr: '(max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})

        * on (node) group_left (label_karpenter_sh_nodepool)

        max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))
        == 1'
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A registered Auto Mode node is not Ready
```

## Frecuencia de revisión

| Frecuencia | Evidencia que se debe revisar |
|---------|--------------------|
| Diaria | Errores persistentes de programación/NodeClaim, condiciones de Node, estado de las cargas de trabajo, autorización actual del PDB y frescura del colector |
| Semanal | Eventos de disrupción/drift, antigüedad observada de nodos/objetos, distribución real de capacidad/Spot, solicitudes de recursos y tendencias de facturación |
| Antes de cambios/revisión mensual | Política de IAM/red/almacenamiento, actualizaciones de software e imágenes compatibles, recuperación probada, cuotas y necesidades futuras de las cargas de trabajo |

Los valores anteriores de “Pending 0–5”, “CPU/memoria por debajo del 80%”, “inicio en menos de 90 segundos”, “disponibilidad del 99,9%” y los intervalos de tiempo de respuesta eran heurísticas de planificación no verificadas, no rangos normales de Auto Mode ni SLO predeterminados. Defina los umbrales a partir de los objetivos de las aplicaciones y del comportamiento medido, en lugar de etiquetar cada transición o una autorización PDB de cero como una infracción.

## Referencias

- [Comportamiento de NodePool en Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Presupuestos de disrupción, drift y terminación](https://karpenter.sh/v1.14/concepts/disruption/)
- [Configurar un PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Restricciones de distribución topológica](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Capacidad estática de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-static-capacity.html)
- [Selectores de NodeClass y reservas de capacidad](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EKS ARC zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html)
- [Entrega de registros de componentes administrados](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Métricas del plano de control y CloudWatch](https://aws.amazon.com/blogs/containers/proactive-amazon-eks-monitoring-with-amazon-cloudwatch-operator-and-aws-control-plane-metrics/)
- [Estructura de dashboards de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html)
- [Métricas de nodos de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Métricas de Pod de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
- [Estándares de seguridad de Pod](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Imagen nginx sin privilegios](https://github.com/nginx/docker-nginx-unprivileged)

< [Anterior: Estrategias de Spot](./04-spot-strategies.md) | [Índice](./README.md) | [Siguiente: Gestión de costos](./06-cost-management.md) >
