# Operaciones y administración

> **Versiones compatibles**: EKS Auto Mode GA; versión de referencia de ejemplo: EKS 1.36
> **Última actualización**: 12 de septiembre de 2026

En las operaciones tras la puesta en marcha, distinga la capacidad deseada, el ciclo de vida de los nodos, la disponibilidad de las aplicaciones y las señales que realmente se recopilan. Los ejemplos siguientes corresponden a configuraciones de laboratorio controladas; no constituyen un procedimiento operativo probado en producción. Durante la revisión documentada no se modificaron recursos de la nube ni se ejecutaron operaciones sobre nodos o Pods en funcionamiento.

La revisión documentada comprobó los manifiestos de NodePool con el esquema estructural publicado de Karpenter 1.14.1. Los ejemplos de cargas de trabajo superaron las comprobaciones del esquema estructural de Kubernetes 1.36.2 y de la política Restricted de Pod Security. También se verificaron la etiqueta y el digest del índice de la imagen nginx, así como su configuración documentada para ejecutarse sin root. La descarga de imágenes en tiempo de ejecución, IAM, la red y el comportamiento de las aplicaciones aún deben validarse en su entorno.

## Confirmar el contexto operativo

Use credenciales temporales y el kubeconfig previsto. Esta comprobación de solo lectura compara la cuenta y el endpoint directo de la API. Si el kubeconfig utiliza un proxy de forma deliberada, revise ese caso por separado antes de continuar ante una discrepancia.

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

Los manifiestos presuponen un NodeClass `default` que ya se ha revisado. Elija los ejemplos que necesite, sustituya de forma consciente los nombres de recursos y los identificadores de red, y revise la capacidad y los costes resultantes. Los grupos de nodos del laboratorio utilizan el taint `ops-lab`; las cargas de trabajo tienen las tolerancias y los selectores de grupo correspondientes. Estos mecanismos controlan la ubicación de los Pods, pero no proporcionan aislamiento de seguridad entre inquilinos.

## Los presupuestos se combinan, no se sustituyen

De todos los presupuestos de NodePool aplicables, se utiliza el menor número de interrupciones permitido. Añadir un presupuesto programado del `30%` no amplía un presupuesto del `10%` que permanece activo en todo momento. Los porcentajes se redondean hacia arriba; los nodos que se están eliminando o no están listos reducen el margen restante.

Este calendario establece un límite general del 30%, un límite del 10% entre semana y un límite de un nodo durante el horario laboral. Las programaciones de Karpenter se expresan en UTC:

| Entrada | Programación UTC | Intervalo previsto |
|-------|--------------|-----------------|
| 30% | Siempre | Límite general |
| 10% | Domingo–jueves a las 15:00, duración de 24h | Días naturales de lunes a viernes en Seúl |
| 1 nodo | Lunes–viernes a las 00:00, duración de 9h | Horario laboral de Seúl: 09:00–18:00 |
| 0 nodos | Primer día del mes a las 00:00, duración de 24h | Suspensión mensual explícita en **UTC** |

Con 20 nodos en buen estado y sin otras restricciones, el ejemplo permite seis nuevas interrupciones voluntarias durante el fin de semana, dos entre semana fuera del horario laboral, una durante el horario laboral y ninguna durante la suspensión mensual. Son decisiones de política para este ejemplo, no recomendaciones universales para producción.

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

Los intervalos cron anteriores `9-18`/`9-21` y las ventanas repetidas de 48 horas del fin de semana se solapaban más allá del horario indicado. Cada ejecución programada inicia una ventana; el rango de horas no describe el horario de aplicación de una ventana larga, sino las horas a las que vuelve a iniciarse.

## Sustitución y disponibilidad de las aplicaciones

Un presupuesto de un nodo limita las interrupciones controladas a las que se aplica. No garantiza que la expiración, las interrupciones o las reparaciones se produzcan de una en una. `expireAfter` no garantiza un tiempo mínimo de funcionamiento, y modificarlo no actualiza los NodeClaims existentes. Siguen aplicándose el comportamiento predeterminado de expiración y del período de gracia de Auto Mode, así como su vida útil máxima.

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

Una política de consolidación de nodos vacíos no deshabilita la sustitución por cambios de configuración ni la expiración. `do-not-disrupt` no garantiza conservar un nodo indefinidamente: los controles de Node y Pod tienen alcances distintos. El período de gracia para la terminación, explícito o predeterminado, también cambia cómo los Pods que bloquean el desalojo afectan a la sustitución por drift y a la terminación final. Revise la [guía de interrupciones](https://karpenter.sh/v1.14/concepts/disruption/) antes de utilizar este control en una ventana de mantenimiento.

### Ejemplo de PDB

El namespace siguiente fija la política Restricted a la versión de Kubernetes revisada. La imagen se ejecuta con UID/GID 101, escucha en el puerto 8080 y utiliza `/tmp` para los archivos PID y temporales. Por ello necesita un volumen emptyDir que permita escritura, aunque el sistema de archivos raíz del contenedor sea de solo lectura. La señal de parada de la imagen es SIGQUIT. Esta configuración no es intercambiable con la de una imagen nginx que se ejecute como root y escuche en el puerto 80.

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

Con cinco réplicas deseadas en buen estado, `minAvailable: 3` permite desalojar voluntariamente hasta dos Pods, siempre que lo permitan las demás restricciones. `maxUnavailable: 1` sería una decisión distinta y más restrictiva; no expresa la misma política.

Los PDB limitan las decisiones de la API de Eviction según los Pods en buen estado y Ready. No crean las réplicas ni protegen frente a todos los fallos o eliminaciones directas. Los porcentajes se redondean hacia arriba: `minAvailable: "80%"` exige cinco réplicas en buen estado cuando hay seis, mientras que `maxUnavailable: "30%"` puede permitir desalojar la única réplica de una carga de trabajo.

En sistemas con estado, utilice los requisitos reales de quórum y de readiness de la aplicación. Dos miembros en buen estado pueden bastar para un sistema de mayoría con tres votantes; con cinco votantes se necesitan tres. `minAvailable: 2` no es una recomendación válida para todas las cargas de trabajo con estado. Un PDB para una sola réplica puede bloquear deliberadamente el vaciado voluntario del nodo, pero no crea alta disponibilidad.

## La distribución entre AZ no garantiza capacidad ni conmutación ante fallos

En un grupo dinámico, `limits.cpu` establece un máximo agregado, no una capacidad mínima por AZ. El ejemplo enumera zonas posibles, pero las subredes del NodeClass, la capacidad disponible y las restricciones de programación determinan cuáles se pueden utilizar.

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

Tener seis réplicas no demuestra una distribución de 3 AZ × 2 réplicas. Este ejemplo exige al menos dos dominios que cumplan los requisitos. Ajuste ese valor después de evaluar la cobertura real de sus subredes y la política ante fallos. Las restricciones estrictas `DoNotSchedule` pueden dejar Pods en estado Pending cuando una AZ no esté disponible.

Si necesita una réplica por nodo, puede añadir el siguiente fragmento de afinidad a una plantilla de Pod revisada. Con esta restricción, nueve réplicas requieren al menos nueve nodos aptos. Esto tampoco demuestra disponibilidad en tres AZ si no se dispone de la topología y la capacidad correspondientes.

```yaml
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector:
      matchLabels:
        app: ha-app
    topologyKey: kubernetes.io/hostname
```

Los diseños activo-activo o con un componente en espera también requieren gestionar el estado de la aplicación, las comprobaciones de estado y el tráfico o la conmutación ante fallos. ARC zonal shift es compatible con Auto Mode y puede evitar el aprovisionamiento de capacidad nueva en una AZ afectada. Autoshift requiere su propia configuración. Estos mecanismos no permiten trasladar a otra zona un volumen vinculado a una AZ ni evitan una restricción estricta de ubicación.

### Reservas de capacidad existentes

Asignar a un grupo el nombre `reserved-capacity`, permitir On-Demand y establecer un límite de CPU no crea una reserva. Para utilizar una reserva existente aprobada, selecciónela en un NodeClass personalizado y permita capacidad `reserved`. Sustituya el ID de reserva del ejemplo y compruebe la cuenta, la AZ, el tipo, el estado, los permisos y la capacidad reservada disponible.

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

Estos manifiestos no crean la reserva de EC2 ni un número fijo de nodos. Una reserva puede generar cargos aunque no se utilice. Para mantener un número deseado de nodos independiente de la demanda de Pods, Auto Mode admite grupos estáticos con `spec.replicas`. Sus reglas para los límites, el peso, la consolidación y el escalado son distintas; consulte la referencia de capacidad estática. Alcanzar el número deseado sigue dependiendo de que el aprovisionamiento tenga éxito y de que la capacidad esté en buen estado.

## La supervisión debe corresponder al origen real de las métricas

Las métricas del plano de control de EKS, Container Insights cuando se ha configurado, los exportadores de Prometheus autogestionados y los registros de componentes de Auto Mode son interfaces diferentes. No dé por supuesto que existe un namespace `Karpenter` de CloudWatch que se rellena automáticamente con los antiguos nombres `karpenter_*`.

Los registros de cómputo, almacenamiento, balanceadores de carga e IPAM administrados por Auto Mode utilizan la entrega de Vended Logs, que se configura por separado. Activar los registros básicos del plano de control no activa los de todos los componentes administrados. Elija un intervalo de tiempo acotado y compruebe IAM, el destino y los cargos.

### Crear un panel con los metadatos reales de las métricas

Para el namespace del plano de control `AWS/EKS`, consulte primero qué métricas se devuelven realmente para el clúster revisado:

```bash
check_account
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace AWS/EKS \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" --output json \
  > "$WORK_DIR/metric-catalog.json"
jq '.Metrics | to_entries | map({index:.key,metric:.value})' "$WORK_DIR/metric-catalog.json"
```

Elija el índice exacto del catálogo y la estadística documentada adecuada para la métrica. El generador local siguiente conserva su namespace y sus dimensiones reales e incluye la región del widget. Si la entrada no existe o corresponde a otro clúster, la rechaza en vez de crear un panel con una métrica inventada.

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

Revise `dashboard.json` antes de crear o actualizar el panel mediante el flujo de trabajo aprobado. Que una métrica aparezca en el catálogo no demuestra que tenga puntos de datos en todos los intervalos de tiempo. Los recuentos de grupos de nodos, la latencia de aprovisionamiento y los SLO de las aplicaciones requieren fuentes e instrumentación que proporcionen esas señales. No dé por supuesto que Container Insights por sí solo las produce todas.

## Diagnósticos estructurados de Kubernetes

Utilice las condiciones de NodeClaim en lugar del campo inexistente `.status.phase`. Un Pod Pending no implica necesariamente una solicitud de capacidad de nodo:

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

Para analizar la distribución por nodos, utilice los campos estructurados en lugar de una columna de la salida para personas. El ejemplo cuenta los objetos Pod activos, incluidos los que ya tienen un nodo asignado pero aún no están listos, y presenta por separado los que no tienen nodo:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
  jq '[.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed") |
       {node: (.spec.nodeName // "(unscheduled)"), namespace: .metadata.namespace, pod: .metadata.name}] |
      group_by(.node) | map({node: .[0].node, activePodObjects: length})'
```

Use `kubectl top` cuando la API de métricas esté configurada y en buen estado. Que una consulta falle no demuestra que metrics-server esté ausente. Revise los motivos de los eventos y los registros de cómputo administrados para identificar fallos reales, como tipos de instancia incompatibles, problemas de readiness del NodeClass, IAM o la red. Reducir `consolidateAfter` no acelera la recuperación tras una interrupción de Spot.

### El margen de desalojos del PDB no determina el cumplimiento

Un valor cero de `disruptionsAllowed` puede ser intencional y compatible con un funcionamiento correcto. Compruebe que el estado observado corresponde a la generación actual y compare las réplicas en buen estado con las necesarias antes de interpretarlo:

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

La fecha de creación del objeto Node no indica cuándo se lanzó la instancia EC2 ni la antigüedad de los parches de la AMI. Elija un umbral de diagnóstico acorde con su política. El script anterior usaba el límite fijo de «más de siete días completos», con lo que truncaba el tiempo y suponía un límite universal que no era adecuado.

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

Las marcas de tiempo desconocidas o futuras no se clasifican como un estado correcto. Antes de concluir que una rotación se ha retrasado, compare la política observada del NodeClaim, la información de la imagen y el contexto de mantenimiento y seguridad de AWS. Este informe local no crea una alarma de CloudWatch.

## Configuración de seguridad

Auto Mode selecciona su imagen Bottlerocket administrada y fija la configuración de IMDSv2 y del límite de saltos. El ejemplo anterior con `amiFamily`, `metadataOptions`, `blockDeviceMappings` y un ARN de KMS mal formado no correspondía a una configuración válida de NodeClass para Auto Mode.

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

Revise el rol del nodo y la entrada de acceso asociados al perfil, las rutas privadas reales y las reglas de los grupos de seguridad. Las etiquetas por sí solas no demuestran que el acceso de red esté restringido. Cifrar los volúmenes EBS raíz y de datos de un nodo no demuestra que los PVC de las aplicaciones estén cifrados. Para utilizar una clave administrada por el cliente o un paquete de certificados de CA, siga el procedimiento válido de `ephemeralStorage.kmsKeyID` y certificados de [Configuración de NodePool](./02-nodepool-configuration.md), con políticas de IAM y de claves revisadas.

El namespace Restricted del ejemplo requiere contextos de seguridad compatibles en las cargas de trabajo. Los agentes de supervisión de nodos que necesitan acceso al host requieren una revisión independiente de sus permisos y de la política de su namespace. No los fuerce a funcionar dentro de este namespace ni deshabilite la seguridad de todo el clúster para hacer funcionar un agente.

## Consultas y alertas opcionales de Prometheus

Estos ejemplos presuponen **un clúster**, un recopilador kube-state-metrics instalado y métricas de node-exporter para Linux. Antes de utilizarlos:

- Incluya las etiquetas de Node `karpenter.sh/nodepool` y `eks.amazonaws.com/compute-type` en la lista de permitidas de kube-state-metrics.
- Compruebe que las series de CPU contienen una etiqueta `node` correctamente asociada al nodo. No todas las configuraciones de recopilación de node-exporter la incluyen automáticamente.
- Elimine las series duplicadas de las réplicas de kube-state-metrics antes de las uniones y los recuentos. Cada nodo debe tener una sola etiqueta actual de NodePool.
- Si supervisa varios clústeres, conserve una etiqueta real de clúster en todas las fuentes e inclúyala en todas las agrupaciones y uniones.

Las consultas de nodos filtran los de Auto Mode. En cambio, las señales de Pods Pending o no programables abarcan todo el clúster: diagnostique su causa antes de atribuirlas a Auto Mode. La CPU del ejemplo mide el **tiempo no inactivo por nodo**, no la proporción de recursos solicitados ni la media del grupo ponderada por capacidad. Una serie ausente no equivale automáticamente a un uso de cero.

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

Con Prometheus Operator instalado, coloque la regla siguiente en un namespace seleccionado por su instancia de Prometheus y asegúrese de que coincide con su `ruleSelector`. Los umbrales y las duraciones son ejemplos. Estas reglas no demuestran que un contador de terminaciones represente todos los fallos de aprovisionamiento.

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

| Frecuencia | Evidencia que debe revisar |
|---------|--------------------|
| Diaria | Errores persistentes de programación o NodeClaim, condiciones de Node, estado de las cargas de trabajo, margen actual de desalojos del PDB y actualidad de los datos recopilados |
| Semanal | Eventos de interrupción o drift, antigüedad observada de nodos y objetos, distribución real de capacidad y Spot, solicitudes de recursos y tendencias de facturación |
| Antes de cambios o en la revisión mensual | Políticas de IAM, red y almacenamiento, actualizaciones compatibles de software e imágenes, recuperación probada, cuotas y necesidades futuras de las cargas de trabajo |

Los valores anteriores de «Pending 0–5», «CPU/memoria por debajo del 80%», «inicio en menos de 90 segundos», «disponibilidad del 99,9%» y los intervalos de tiempo de respuesta eran orientaciones para planificar que no se habían validado en un entorno real. No describen rangos normales de Auto Mode ni SLO predeterminados. Defina los umbrales según los objetivos de la aplicación y su comportamiento medido. No clasifique automáticamente cada transición, ni un margen de cero desalojos en el PDB, como un incumplimiento.

## Referencias

- [Comportamiento de NodePool en Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Presupuestos de interrupción, drift y terminación](https://karpenter.sh/v1.14/concepts/disruption/)
- [Configurar un PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Restricciones de distribución topológica](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Capacidad estática de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-static-capacity.html)
- [Selectores de NodeClass y reservas de capacidad](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EKS ARC zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html)
- [Entrega de registros de componentes administrados](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Métricas del plano de control y CloudWatch](https://aws.amazon.com/blogs/containers/proactive-amazon-eks-monitoring-with-amazon-cloudwatch-operator-and-aws-control-plane-metrics/)
- [Estructura de paneles de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html)
- [Métricas de nodos de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Métricas de Pod de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
- [Estándares de seguridad de Pod](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Imagen nginx sin privilegios](https://github.com/nginx/docker-nginx-unprivileged)

< [Anterior: Estrategias de Spot](./04-spot-strategies.md) | [Índice](./README.md) | [Siguiente: Gestión de costos](./06-cost-management.md) >
