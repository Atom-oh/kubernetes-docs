# Gestión y optimización de costos

> **Versiones compatibles**: EKS Auto Mode GA; ejemplos revisados para EKS 1.36
> **Última actualización**: September 12, 2026

La optimización de costos requiere evidencia de facturación para comparar trabajo útil equivalente. Una instantánea del número de nodos, un uso bajo de CPU o un descuento anunciado no constituyen ahorros medidos. Estos ejemplos se comprobaron localmente frente a contratos de fuentes, esquemas y CLI; no se realizó ninguna compra, implementación en la nube ni consulta de facturación en vivo.

## Qué incluye la factura

Ten en cuenta la tarifa del clúster de EKS, el uso de EC2, los **cargos adicionales de Auto Mode**, EBS, balanceadores de carga, NAT/transferencia de datos, observabilidad y otros servicios de las cargas de trabajo. Los cargos de cómputo de Auto Mode se facturan por segundo, con un mínimo de un minuto, y son independientes de la opción de compra de EC2. Los descuentos de EC2 Savings Plans/RI no descuentan el cargo independiente de Auto Mode.

### Reducción de la tarifa de GPU de julio de 2026

El anuncio de AWS de julio confirma que, a partir del 1 de julio, las **tarifas de administración de Auto Mode** para la serie G bajaron un 35 %, y las tarifas para la serie P/Trainium bajaron un 60 %, automáticamente en las regiones compatibles. Esto reduce ese componente de la tarifa; no equivale al mismo porcentaje de descuento sobre la factura total de GPU. El anuncio también describe la extracción y descompresión paralelas de imágenes en instancias de GPU con NVMe local, así como una reparación que tiene en cuenta los aceleradores; no establece un tiempo medido de inicio o recuperación de la aplicación para este ejemplo.

## Ubicación orientada a los costos

Primero, usa la protección de cuenta/punto de enlace de API y el `WORK_DIR` privado de [Operaciones](./05-operations.md). Los ejemplos suponen que se revisó un NodeClass `default` y que hay capacidad compatible disponible. Revisa los costos antes de implementarlos.

La carga de trabajo completa del laboratorio que aparece a continuación corrige el selector y la imagen que faltaban en el ejemplo antiguo en inglés. Usa la imagen de nginx no root verificada en el capítulo de operaciones, un namespace Restricted y un selector/toleration de pool. Las solicitudes ilustrativas **no representan uso medido**. Comprueba las imágenes multiarquitectura, las bibliotecas y el comportamiento de la aplicación antes de permitir ARM.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cost-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
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
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
  namespace: cost-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cost-efficient
  template:
    metadata:
      labels:
        app: cost-efficient
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
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
        karpenter.sh/nodepool: cost-optimized
      tolerations:
      - key: cost-lab
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
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values:
                - spot
```

Permitir tanto Spot como On-Demand habilita la selección de capacidad; una preferencia flexible del Pod no garantiza un porcentaje ni una alternativa inmediata. La diversidad de categorías solo ayuda cuando la región, el NodeClass, la carga de trabajo y el inventario real lo permiten. Un pool de nivel independiente puede expresar restricciones de interrupción, GPU o arquitectura, pero una fragmentación innecesaria puede reducir la eficiencia de empaquetamiento.

`WhenEmptyOrUnderutilized` evalúa si los Pods se pueden reprogramar de forma más económica usando solicitudes y restricciones; no es un umbral de utilización de CPU. `consolidateAfter` es un período de espera, no un plazo para eliminar nodos. Los PDB, la afinidad y los presupuestos pueden impedir la consolidación. Los límites de CPU/memoria del pool limitan el crecimiento de la infraestructura solicitada; la consistencia eventual puede provocar excesos temporales durante un aprovisionamiento rápido. No son un presupuesto monetario ni un límite máximo estricto de gasto para toda la cuenta.

## Separar la facturación de las métricas operativas

Una métrica instantánea de nodos no equivale a horas de nodo, y las horas de nodo no equivalen a dólares sin datos de instancia, tarifa y tiempo. Auto Mode no publica automáticamente las métricas de costos `Karpenter` inventadas de los ejemplos antiguos en CloudWatch. Para el dinero, usa exportaciones de facturación/Cost Explorer reales; para la capacidad y el rendimiento, usa recopiladores configurados.

### Resumen de facturación de CloudWatch

Tras habilitar las alertas/métricas de facturación, los cargos estimados de `AWS/Billing` se publican en **us-east-1** para los cargos globales de la cuenta. Son cargos estimados acumulados para el mes en curso; no representan el gasto diario de EC2, el total del clúster de EKS ni una previsión. Una cuenta de pagador tiene su propio ámbito de cuentas vinculadas. Esta definición local del panel usa la dimensión de moneda y la región requeridas:

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "Account estimated charges, month to date (USD)",
        "region": "us-east-1",
        "view": "timeSeries",
        "metrics": [
          [
            "AWS/Billing",
            "EstimatedCharges",
            "Currency",
            "USD"
          ]
        ],
        "period": 21600,
        "stat": "Maximum"
      }
    }
  ]
}
```

Usa Cost Explorer/CUR o Data Exports para asignar costos por servicio/clúster y consultar los cambios diarios. AWS Budgets y Cost Anomaly Detection pueden enviar notificaciones cuando se alcanzan umbrales monetarios revisados; no son límites máximos estrictos de gasto. Una alarma de cantidad de nodos es una protección de capacidad independiente y necesita un publicador real configurado, dimensiones y un destino de notificación. La alarma antigua hacía referencia tanto a una métrica inventada como a un recurso SNS sin definir.

### Kubecost

El chart/aplicación estable revisado es **3.2.4**, con el nombre de chart `kubecost` en el nuevo repositorio que aparece a continuación; no se usa una versión candidata más reciente como objetivo de actualización a ciegas. La versión 3 usa su agente FinOps y una arquitectura basada en ClickHouse. No reutilices el repositorio antiguo `cost-analyzer`, el ejemplo de línea de comandos `kubecostToken` ni las suposiciones de una implementación de Prometheus de la versión 2.

Prepara un archivo de valores específico para la versión, que incluya licencias, identidad del clúster, integración de facturación, IAM de cargas de trabajo con ámbito limitado, autenticación, retención y almacenamiento. Un StorageClass de EBS de Auto Mode usa `ebs.csi.eks.amazonaws.com`; selecciónalo explícitamente cuando sea necesario y revisa el cifrado. Este chart tiene anotaciones para conservar/retener datos persistentes, por lo que desinstalarlo no demuestra que se haya eliminado todo el almacenamiento facturable. Mantén el acceso privado y revisa el comportamiento de los recopiladores y la telemetría. Renderiza localmente antes de cualquier instalación:

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```

El comando de renderizado no instala nada. La asignación de costos de Pods/namespaces/capacidad inactiva requiere el agente y fuentes de datos compatibles; la conciliación real de la facturación necesita la integración de AWS. Las etiquetas de namespace por sí solas no generan datos de facturación. Concilia los costos inactivos/compartidos, los descuentos y los costos sin asignar en lugar de sumar estimaciones incompatibles.

## Medición de los ahorros de Spot

Esta instantánea estructurada gestiona cero nodos, etiquetas ausentes y tipos de instancia mixtos. Cuenta **objetos Node de Auto Mode**, no horas facturadas ni gasto:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[] | {
  capacity: (.metadata.labels["karpenter.sh/capacity-type"] // "unknown"),
  instanceType: (.metadata.labels["node.kubernetes.io/instance-type"] // "unknown")
}] as $nodes |
{
  totalNodeObjects: ($nodes | length),
  byCapacityAndType: ($nodes | group_by([.capacity,.instanceType]) |
    map({capacity: .[0].capacity, instanceType: .[0].instanceType, count:length})),
  spotNodePercent: (if ($nodes|length) == 0 then null
    else 100 * ([$nodes[]|select(.capacity=="spot")]|length) / ($nodes|length) end)
}'
```

Para comparar costos, usa el mismo período, región/AZ, instancia/SO/tenencia, moneda y requisito de trabajo útil. Las tarifas históricas de Spot varían según la AZ y el momento. Un resultado de Pricing API seleccionado solo por tipo de instancia podría corresponder a una región/SO/tenencia/producto incorrecto; además, el script anterior suprimía los errores de la API. Una muestra de precios actuales no puede reconstruir la factura real del mes pasado.

```text
reference_total = cost of the reviewed On-Demand counterfactual for the same useful work
actual_total = actual compute + Auto Mode fees + other allocated costs
               + recovery costs not already included in those billed components
savings_amount = reference_total - actual_total
savings_percent = 100 * savings_amount / reference_total  (reference_total > 0)
```

Incluye una sola vez el trabajo interrumpido/reintentado y los compromisos inactivos/no utilizados, y evita contar dos veces el cómputo de recuperación. La referencia también necesita sus tarifas correspondientes de Auto Mode y otros cargos. Un descuento de Spot supuesto del 70 % o el porcentaje actual de nodos Spot no se pueden presentar como ahorros mensuales reales. Conserva evidencia independiente de los eventos de interrupción; una causa de contador de terminación supuesta no mide todas las interrupciones.

### Cost Explorer, solo lectura

Activa primero la etiqueta **`aws:eks:cluster-name`** generada por AWS; `eks:cluster-name` no es la clave de facturación documentada. Atribuye los costos de las instancias EC2 participantes, **no la tarifa del plano de control ni todos los servicios relacionados con el clúster**. Revisa el ámbito de la cuenta/pagador y la cobertura de las etiquetas. Las solicitudes a la API de Cost Explorer pueden generar cargos.

Elige una fecha de inicio inclusiva y una fecha de fin exclusiva explícitas. Esta solicitud usa `AmortizedCost` monetario; no añade unidades incompatibles de `UsageQuantity` ni trata las proporciones de nodos como dólares.

```bash
: "${COST_START:?Set YYYY-MM-DD inclusive start}"
: "${COST_END:?Set YYYY-MM-DD exclusive end, no later than today UTC}"
export COST_START COST_END CLUSTER_NAME
python3 - <<'PY'
import json, os
from datetime import date, datetime, timezone
from pathlib import Path
start, end = (date.fromisoformat(os.environ[key]) for key in ("COST_START", "COST_END"))
if not start < end <= datetime.now(timezone.utc).date():
    raise SystemExit("Require start < end <= today UTC")
request = {
    "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
    "Granularity": "DAILY",
    "Metrics": ["AmortizedCost"],
    "Filter": {"Tags": {"Key": "aws:eks:cluster-name", "Values": [os.environ["CLUSTER_NAME"]]}},
    "GroupBy": [{"Type": "DIMENSION", "Key": "INSTANCE_TYPE"},
                {"Type": "DIMENSION", "Key": "PURCHASE_TYPE"}]
}
(Path(os.environ["WORK_DIR"]) / "ce-request.json").write_text(json.dumps(request, indent=2) + "\n")
PY
```

```bash
check_account
aws ce get-cost-and-usage --region us-east-1 \
  --cli-input-json "file://$WORK_DIR/ce-request.json" \
  --output json > "$WORK_DIR/ce-result.json"
jq '[.ResultsByTime[] | {period:.TimePeriod,estimated:.Estimated,groups:.Groups}]' \
  "$WORK_DIR/ce-result.json"
```

Conserva los indicadores `Estimated` y ten en cuenta los reembolsos, créditos, asignación de descuentos y datos incompletos. Un resultado filtrado por etiqueta puede excluir cargos sin asignar o compromisos no utilizados; concílialo con el conjunto completo de datos de facturación antes de afirmar un total o un ahorro.

## Dimensionamiento adecuado de recursos

Usa la [guía de instalación de VPA 1.8.0](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/installation.md), fijada a esa versión. La compatibilidad documentada para VPA 1.8.x es Kubernetes 1.36–1.38, con requisitos adicionales para determinadas funciones in-place. Las URL antiguas `releases/latest/download/...` no constituían un procedimiento válido de instalación de VPA. Revisa los CRD, RBAC, metrics-server y la configuración de componentes/certificados antes de aplicar scripts de instalación en todo el clúster; `Off` también requiere un recommender funcional.

Este recurso apunta al Deployment real del laboratorio en el mismo namespace:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get vpa cost-app-vpa -o json |
  jq '{conditions:.status.conditions,recommendations:.status.recommendation.containerRecommendations}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get deployment cost-efficient-app -o json |
  jq '[.spec.template.spec.containers[] | {name,resources}]'
```

`Off` proporciona recomendaciones sin aplicarlas. Comprueba todos los contenedores, las condiciones/historial de recomendaciones, la estacionalidad de la carga de trabajo, los picos de inicio, la latencia, la limitación de CPU y el comportamiento de memoria/OOM. Un límite en `resourcePolicy` no demuestra que su recomendación se ajuste a los límites existentes. VPA no garantiza el rendimiento; esta versión revisada también documenta limitaciones con declaraciones de recursos a nivel de Pod.

### Conserva las unidades de cantidad de Kubernetes

`1` CPU significa un núcleo, mientras que `1m` significa un milinúcleo. `1Gi` equivale a 1024Mi; eliminar los sufijos no convierte ninguna de las dos unidades. Captura las solicitudes/límites sin procesar y el uso de cada contenedor, en lugar de sumar los totales antiguos con `sed`/`awk`:

```bash
: "${WORKLOAD_NAMESPACE:?Select a namespace}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pods -o json |
  jq '[.items[] | {pod:.metadata.name,uid:.metadata.uid,
    podResources:.spec.resources,overhead:.spec.overhead,
    containers:[.spec.containers[]|{name,resources}],
    initContainers:[.spec.initContainers[]?|{name,restartPolicy,resources}]}]' \
  > "$WORK_DIR/pod-requests.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  top pods --containers > "$WORK_DIR/container-usage.txt"
```

La consulta de métricas debe completarse correctamente; la falta de datos no equivale a una utilización de cero. Estas dos instantáneas no son simultáneas, y el uso de contenedores no constituye el cálculo completo de solicitudes de Pod que utiliza el scheduler: también importan los contenedores init/restartable-init, los recursos a nivel de Pod y la sobrecarga.

| Observación | Acción de revisión |
|-------------|--------------------|
| La solicitud parece superar 2× el uso representativo | Investiga los picos y el margen para el SLO antes de reducirla; no implica un ahorro automático del 20–50 % |
| La solicitud está dentro de 2× el uso | No demuestra que sea óptima |
| El uso supera la solicitud | Evalúa la programación y el margen disponible; para la aplicación de OOM son relevantes los **límites** de memoria, no simplemente las solicitudes |
| El límite supera ampliamente la solicitud | Evalúa la política de ráfagas/limitación/OOM; reducir solo el límite no suele mejorar el empaquetamiento basado en solicitudes |

### Candidatos opcionales para revisar en Prometheus

Las siguientes reglas informativas suponen **un clúster**, kube-state-metrics con unidades normalizadas de núcleos de CPU/bytes de memoria y uso de cAdvisor a nivel de contenedor con etiquetas de namespace/Pod/contenedor. La consulta de CPU requiere la serie agregada `cpu="total"`; verifica las etiquetas de tu recopilador. Deduplican las réplicas del recopilador, excluyen los cgroups de infraestructura y requieren un denominador positivo de solicitudes. Usa etiquetas reales del clúster en cada agrupación/unión cuando haya varios clústeres. Las series ausentes no se convierten en cero. Revisa los efectos de las series obsoletas y la recreación de contenedores, así como el historial representativo.

El umbral de utilización del 30 % mantenido durante una hora es un disparador ilustrativo para revisar, no una recomendación automática para reducir solicitudes ni un ahorro medido. Instala Prometheus Operator y haz coincidir sus selectores de namespace/reglas antes de usar este recurso:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-review-candidates
  namespace: monitoring
spec:
  groups:
  - name: cost-review-candidates
    rules:
    - alert: LowCpuRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])) and on (namespace,pod,container)\
        \ max by (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        cpu\",unit=\"core\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\n\
        ) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\
        \ > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}) unless\
        \ on (namespace,pod,container) max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m]))\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
    - alert: LowMemoryRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"}) and on (namespace,pod,container) max by\
        \ (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        memory\",unit=\"byte\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }))\n) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        })) > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }) unless on (namespace,pod,container) max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"})\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
```

## Savings Plans y Reserved Instances

| Opción | Uso elegible / ámbito | Limitación importante |
|--------|------------------------|----------------------|
| Compute Savings Plans | Uso elegible de EC2 en distintas familias, tamaños, regiones, SO y tenencia; también Fargate/Lambda | Hasta un 66 % es un máximo anunciado, no un descuento esperado |
| EC2 Instance Savings Plans | Familia de instancias elegida en una región; flexibilidad de tamaño/SO/tenencia dentro de ese ámbito | Hasta un 72 %; no es un compromiso con un tamaño de instancia exacto |
| EC2 RI | Uso coincidente; la flexibilidad regional de tamaño y las reglas de intercambio dependen de la oferta | Los compromisos existentes que coincidan aún pueden beneficiar a Auto Mode |
| Spot | Precios de Spot independientes | No se acumula con Savings Plans |

El uso elegible de EC2 Graviton y GPU no requiere un «ARM Savings Plan» especial ni una exclusión general de GPU. SageMaker AI Savings Plans cubre el uso de SageMaker, no un nodo EC2 con GPU por el simple hecho de ejecutar ML. Savings Plans no reserva capacidad física; evalúa por separado las reservas de capacidad. La tarifa independiente de Auto Mode sigue quedando fuera de estos descuentos de EC2.

Dimensiona los compromisos en **USD/hora según las tarifas aplicables de Savings Plans**, a partir del uso por hora elegible, sostenido y sin cobertura. Si la referencia ya excluye Spot, no vuelvas a multiplicarla por `(1 - Spot%)`. Ten en cuenta la cobertura actual de RI/SP, los cambios futuros de dimensionamiento/arquitectura, la configuración de uso compartido, la estacionalidad y los compromisos no utilizados. Una tarifa de EC2 más baja o una menor cantidad de nodos no determinan por sí solas una compra segura.

```bash
check_account
aws ce get-savings-plans-purchase-recommendation --region us-east-1 \
  --savings-plans-type COMPUTE_SP --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT --lookback-period-in-days THIRTY_DAYS \
  --output json > "$WORK_DIR/savings-plan-recommendation.json"
```

Esto obtiene una recomendación, no realiza una compra. La consulta retrospectiva de 30 días es una opción seleccionable de la API; compárala con un historial representativo más extenso antes de decidir.

Los porcentajes originales de cobertura de Compute del 60–70 %/70 %, de EC2 Instance del 30–40 %, de On-Demand del 50 % y el diagrama de Spot 40–60 % / cobertura 30–40 % / sin cobertura 10–20 % son **ejemplos de planificación no verificados**, no objetivos universales acumulables. Una carga de trabajo se ejecuta en capacidad Spot o On-Demand; Savings Plans describen la cobertura de facturación del uso elegible, no un tercer tipo de nodo.

## Atribución de costos

Usa selectores válidos de identidad/red de NodeClass y permisos de etiquetado aprobados. Los NodeClass personalizados necesitan una entrada de acceso para el rol del nodo. Las etiquetas describen recursos; no crean aislamiento de red ni cubren automáticamente todos los servicios dependientes.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
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
  tags:
    Environment: lab
    Team: platform
    Project: web-services
    CostCenter: CC-12345
    Application: cost-lab
    ManagedBy: eks-auto-mode
```

Haz referencia deliberadamente a `tagged-nodeclass` desde el pool previsto para usar este ejemplo. `amiFamily: AL2023` no es un campo de NodeClass de Auto Mode. Verifica las etiquetas en los recursos reales y activa las claves pertinentes en Billing. Las claves definidas por el usuario pueden tardar hasta 24 horas en aparecer para su activación y hasta otras 24 horas en activarse; la actualización de los informes es un proceso independiente. No prometas que todos los datos estarán disponibles exactamente 24 horas después.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: team-a
    environment: production
```

Las etiquetas de namespace pueden ayudar a las herramientas de asignación de costos de Kubernetes; no se propagan automáticamente a las etiquetas de asignación de costos de AWS. La atribución de EC2 basada en etiquetas tampoco sustituye la asignación de costos compartidos, del plano de control, del almacenamiento o de la red.

## Lista de comprobación de optimización y ejemplos numéricos anteriores

Mantén la diversidad de instancias compatibles, el uso de Spot adaptado a la carga de trabajo, el dimensionamiento medido de solicitudes, la consolidación viable, la integración de facturación y la revisión de compromisos como tareas independientes. Mide el costo total del trabajo útil y la disponibilidad antes y después de un cambio.

Las estimaciones anteriores que aparecen a continuación no tienen una procedencia verificada de pruebas comparativas ni de facturación. Se conservan como contexto, no están garantizadas y no deben sumarse ni multiplicarse para afirmar un ahorro total:

| Tema anterior | Intervalos del ejemplo original |
|-------------|--------------------------------|
| Spot | 60–70 %, 60–90 %, 70–90 % |
| ARM/Graviton | 20 % |
| Dimensionamiento de solicitudes / VPA | 10–30 %, 15–30 %, 20–40 %, 20–50 % |
| Consolidación | 10–20 %, 10–30 % |
| Savings Plans | 20–30 %, 20–40 % |
| Multi-AZ / programación | 5–10 % / 10–20 % |

Reducir la resiliencia de AZ no es una optimización genérica de costos. Incluye la transferencia de datos, la recuperación ante fallos, la retención del almacenamiento y los objetivos de la carga de trabajo en cualquier experimento de ubicación/programación.

## Referencias

- [Precios de EKS y cargos de Auto Mode](https://aws.amazon.com/eks/pricing/)
- [Reducción de las tarifas de administración de GPU de julio de 2026](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price/)
- [Controles de costos de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cost-control.html)
- [Límites de recursos y disrupciones de NodePool](https://karpenter.sh/v1.14/concepts/nodepools/)
- [Tipos de Savings Plans](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [Savings Plans y RI: comparación](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-ris.html)
- [Etiquetas de facturación de EKS](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
- [Activación de etiquetas de asignación de costos](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)
- [Cargos de facturación estimados de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html)
- [Chart de Kubecost 3.2.4](https://kubecost.github.io/kubecost/kubecost-3.2.4.tgz)
- [Instalación de VPA 1.8.0](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/installation.md)
- [Limitaciones conocidas de VPA](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/known-limitations.md)
- [Unidades de recursos y programación de Kubernetes](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [NodeClass y etiquetas de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)

< [Anterior: Operaciones](./05-operations.md) | [Tabla de contenido](./README.md) | [Siguiente: Ciclo de vida de los nodos](./07-node-lifecycle.md) >
