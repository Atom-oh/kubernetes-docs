# Parte 3: Funciones avanzadas

> **Base de los ejemplos**: Kubernetes 1.35.8, Go 1.27.2; API del cliente de Python 35.0.0
> **Última actualización**: 16 de octubre de 2026

Estos son patrones de implementación ilustrativos que usan el [scheduler secundario de la Parte 1](01-custom-scheduler-part1.md) y las [interfaces del framework de la Parte 2](02-custom-scheduler-part2.md). No describen un despliegue de producción ni una optimización medida. Las comprobaciones locales del código y los esquemas no demuestran que se ejecute una GPU, que la aplicación esté lista, que se aprovisionen certificados ni que haya disponibilidad en producción.

## Casos de implementación de schedulers personalizados en EKS

En esta sección se desarrollan políticas de programación de ejemplo para EKS. La capacidad real, el inventario de dispositivos, los patrones de tráfico y el comportamiento ante fallos deben verificarse en el clúster de destino.

### Caso 1: scheduler para optimizar cargas de trabajo GPU

En los clústeres EKS que ejecutan cargas de trabajo de IA/ML, es importante utilizar eficazmente los recursos GPU. A continuación se presenta un caso de implementación de un scheduler personalizado para optimizar cargas de trabajo GPU.

#### Arquitectura del scheduler de optimización de cargas GPU

El diseño puede combinar una política de colocación con telemetría opcional. El ejemplo implementado más abajo usa solicitudes en caché; el diagrama no demuestra que exista un recopilador de utilización funcional.

#### Flujo de programación de cargas GPU

El scheduler observa el estado de los Pods mediante la API. Las extensiones basadas en métricas que aparecen en el flujo requieren un recopilador independiente y validado.

#### Requisitos

1. Aplicar los requisitos de memoria GPU/modelo mediante etiquetas de nodo verificadas y afinidad de nodo obligatoria.
2. Conservar `NodeResourcesFit` para las solicitudes GPU efectivas y las solicitudes ya asignadas o asumidas.
3. Preferir la consolidación en nodos adecuados usando la instantánea del scheduler; ponderar la utilización en vivo requiere una integración aparte que aquí no está implementada.
4. Compartir GPU requiere una política adecuada de asignación con device-plugin/MIG/compartición temporal o DRA. Una función de puntuación de nodos no particiona dispositivos ni impone límites de memoria GPU por proceso.

#### Enfoque de implementación

Este caso usa el enfoque de plugins del framework del scheduler.

1. **Verifique el inventario antes de asignar etiquetas.** Las claves `training.example.com` que aparecen a continuación son etiquetas de laboratorio definidas por el administrador, no etiquetas de descubrimiento de NVIDIA. El valor de memoria debe describir la memoria mínima por dispositivo apto en un nodo GPU homogéneo y sin recursos compartidos. Lea los recuentos de recursos GPU de `status.allocatable`; una etiqueta con un recuento no representa la capacidad disponible.

```bash
kubectl get nodes -o custom-columns='NAME:.metadata.name,GPUS:.status.allocatable.nvidia\.com/gpu'

# Set only after verifying the actual node and per-device inventory.
: "${NODE_NAME:?Select a verified GPU node}"
: "${GPU_MODEL:?Set the observed model label value}"
: "${GPU_MEMORY_MIB:?Set verified minimum memory per GPU in MiB}"
kubectl label node "$NODE_NAME" \
  "training.example.com/gpu-model=$GPU_MODEL" \
  "training.example.com/gpu-memory-mib=$GPU_MEMORY_MIB" --overwrite
```

2. **Añada un plugin de puntuación sin reemplazar los filtros predeterminados.** Guarde a continuación `packing/plugin.go`. Usa los recursos GPU asignables menos las solicitudes existentes/asumidas y las entrantes; no usa etiquetas de inventario total ni utilización en vivo. Una puntuación cero no excluye un nodo.

```go
package packing

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	resourcehelper "k8s.io/component-helpers/resource"
	fwk "k8s.io/kube-scheduler/framework"
)

const Name = "GPUPacking"
const gpu v1.ResourceName = "nvidia.com/gpu"

type Plugin struct{}

var _ fwk.ScorePlugin = &Plugin{}

func (*Plugin) Name() string { return Name }

func (*Plugin) Score(_ context.Context, _ fwk.CycleState, pod *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if pod == nil || info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	requests := resourcehelper.PodRequests(pod, resourcehelper.PodResourcesOptions{})
	request := requests[gpu]
	needed, exact := request.AsInt64()
	if !exact || needed < 0 {
		return 0, fwk.NewStatus(fwk.Error, "GPU request must be a non-negative integer")
	}
	if needed == 0 {
		return 0, nil
	}
	allocatable := info.GetAllocatable().GetScalarResources()[gpu]
	requested := info.GetRequested().GetScalarResources()[gpu]
	remaining := allocatable - requested - needed
	if remaining < 0 {
		// Score cannot exclude a node. NodeResourcesFit must remain enabled.
		return 0, nil
	}
	if remaining >= 10 {
		return 0, nil
	}
	return 100 - remaining*10, nil
}

func (*Plugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func New(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &Plugin{}, nil
}
```

Regístrelo en `cmd/gpu-packing-scheduler/main.go` y luego utilice el flujo de creación de imágenes de la Parte 1 con `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/gpu-packing-scheduler`.

```go
package main

import (
	"os"

	"example.com/custom-scheduler/packing"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(app.WithPlugin(packing.Name, packing.New))
	os.Exit(cli.Run(command))
}
```

La idea original de ponderar 70:30 la consolidación y la utilización se puede expresar con la fórmula ilustrativa `(packingScore * 7 + utilizationScore * 3) / 10`, donde `utilizationScore = (1 - utilization) * 100`. **No está conectada a este binario.** Una implementación real necesita una instantánea coherente y reciente por dispositivo, valores finitos entre 0 y 1, latencia de recopilación acotada y una política explícita para datos faltantes. La telemetría faltante no equivale a una utilización cero; la utilización tampoco equivale a la capacidad GPU sin asignar.

3. **Configuración del scheduler**:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: GPUPacking
        weight: 10
```

4. **Exprese los requisitos estrictos de colocación en el Pod.** Sustituya el modelo/memoria del ejemplo por datos de inventario verificados. `Gt: "40959"` significa una etiqueta entera de al menos 40960 MiB. La imagen BusyBox de abajo solo mantiene una reserva de recursos GPU si se ejecuta en un laboratorio preparado; no ejecuta CUDA ni valida la GPU.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-reservation-demo
  namespace: scheduler-lab
spec:
  schedulerName: custom-scheduler
  automountServiceAccountToken: false
  restartPolicy: Never
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: training.example.com/gpu-model
            operator: In
            values:
            - A100
          - key: training.example.com/gpu-memory-mib
            operator: Gt
            values:
            - '40959'
  containers:
  - name: reservation
    image: busybox:1.38.0
    command:
    - sh
    - -c
    - sleep 60
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
        nvidia.com/gpu: 2
      limits:
        memory: 128Mi
        nvidia.com/gpu: 2
```

### Caso 2: scheduler para optimizar la localidad de red

En los clústeres EKS se puede implementar un scheduler personalizado que tenga en cuenta la localidad de red para optimizar los costos de red.

#### Arquitectura del scheduler de optimización de localidad de red

Un diseño de localidad de red puede combinar la topología con información medida sobre dependencias; las integraciones son ilustrativas.

#### Flujo de trabajo para optimizar la localidad de red

Evalúe las restricciones estrictas de colocación antes de las puntuaciones de localidad opcionales; el tráfico real y los requisitos de dominios de fallo determinan las compensaciones.

Antes de crear otro scheduler, empiece por la afinidad de Pods obligatoria/preferida, la distribución de topología y la topología del almacenamiento. Modele las dependencias reales entre servicios y las zonas de disponibilidad aptas; la colocación conjunta puede reducir parte del tráfico entre zonas, pero también aumentar la concentración de fallos o la contención. Ni las etiquetas de colocación ni una puntuación de programación demuestran menor latencia ni ahorro.

Los diagramas muestran posibles integraciones, no una implementación completa de políticas de red, service mesh o CloudWatch. Mantenga la recopilación de métricas fuera de las llamadas de puntuación por nodo, limite el tiempo de vigencia de los datos y los timeouts, y vuelva a evaluar el equilibrio entre costo y disponibilidad con tráfico real. Este capítulo no incluye un scheduler de localidad de red desplegado.

## Optimización de reducción de escala con Pod Deletion Cost

Pod Deletion Cost es una **preferencia de mejor esfuerzo para reducir la escala de ReplicaSet**, incluidos los Pods administrados por los ReplicaSets de un Deployment. Apareció como función alfa en 1.21 y pasó a beta habilitada de forma predeterminada en 1.22; sigue siendo beta en la documentación de referencia. No controla la eliminación de ordinales de StatefulSet, la eliminación de Pods independientes, la expulsión ni los fallos de nodo.

### Concepto de Pod Deletion Cost

Defina la anotación `controller.kubernetes.io/pod-deletion-cost` en cada Pod. Los costos se comparan **dentro del mismo ReplicaSet**, no globalmente entre Deployments o nodos. Un costo mayor favorece conservar el Pod solo cuando las condiciones de mayor prioridad lo permiten.

**Propiedades clave:**

* Si falta la anotación, el costo es 0; los valores decimales válidos abarcan el rango int32 con signo, incluidos los negativos. Si la función está habilitada, se rechazan los valores no válidos.
* En el controlador fijado, la asignación, la fase del Pod y su estado de disponibilidad tienen prioridad sobre el costo; la colocación de réplicas y otros desempates se evalúan después.
* No hay un orden de eliminación garantizado. Los costos iguales en la plantilla no distinguen entre réplicas.
* Evite actualizaciones frecuentes impulsadas por métricas. Prefiera cambios generales de estado de la aplicación o una actualización antes de una reducción de escala controlada por la aplicación.

### Arquitectura de Pod Deletion Cost

El diagrama muestra el orden por costo **solo cuando la asignación, la fase, el estado de disponibilidad y otras condiciones relevantes son comparables**; no garantiza una secuencia de eliminación.

![El controlador de ReplicaSet ordena los Pods según la anotación pod-deletion-cost y elimina primero los de costo más bajo: Pod-3 (costo -10) antes que Pod-4 (costo 0), mientras Pod-1 y Pod-2, con costos mayores, sobreviven a la reducción de escala.](../.gitbook/assets/en-scheduling-03-custom-scheduler-part3-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-scheduling-03-custom-scheduler-part3-0.html)

### Casos de uso

#### 1. Proteger Pods con caché precalentada

Este Deployment inicia cada Pod con costo 0. Es un contrato para **su aplicación**: sustituya la imagen e implemente `/readyz` en el puerto 8080 para que la disponibilidad refleje el precalentamiento real. En esta auditoría no se compiló ni ejecutó esa aplicación. No asigne un costo alto solo porque haya transcurrido cierto tiempo de espera.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deletion-cost-lab
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cache-app
  namespace: deletion-cost-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cache-app
  template:
    metadata:
      labels:
        app: cache-app
      annotations:
        controller.kubernetes.io/pod-deletion-cost: '0'
    spec:
      automountServiceAccountToken: false
      containers:
      - name: app
        image: registry.example.com/training/cache-app:validated
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /readyz
            port: http
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: POD_UID
          valueFrom:
            fieldRef:
              fieldPath: metadata.uid
```

Cuando una réplica específica ya esté realmente precalentada, un operador/controlador autorizado puede actualizar la anotación de ese Pod. Actualizar en cambio la plantilla del Deployment inicia un rollout y crea otro ReplicaSet.

```bash
: "${POD_NAME:?Select a verified warm replica of cache-app}"
kubectl -n deletion-cost-lab annotate pod "$POD_NAME" \
  controller.kubernetes.io/pod-deletion-cost=100 --overwrite
```

El Deployment de ejemplo no monta ningún token de API. Los auxiliares dinámicos opcionales de abajo requieren un cliente de Kubernetes configurado y autorizado por separado. El RBAC de namespace con `patch pods` no se limita automáticamente al Pod que realiza la llamada; use un controlador de confianza o una identidad/política de admisión restringida de forma adecuada. Este ejemplo no instala una política de producción de ese tipo.

#### 2. Proteger Pods con conexiones activas

El recuento de conexiones activas puede servir como una señal para conservar un Pod; aun así, se requieren el cierre ordenado y el drenaje porque el costo no impide su eliminación. Esta biblioteca serializa las actualizaciones, usa categorías amplias, verifica el UID del Pod, modifica solo la anotación y omite las señales que no hayan cambiado. Supone que hay un solo escritor de esa anotación y que ya existe un objeto de anotaciones en la plantilla del Pod.

Pase un cliente `client-go` configurado y el nombre/namespace/UID admitidos del Pod. En una integración dentro del Pod, esos identificadores se pueden obtener mediante Downward API; obtenerlos no concede permisos de API. Llame a `UpdateDeletionCost(ctx)` en una transición controlada o antes de una reducción de escala que usted administre, no con cada evento de conexión.

```go
package deletioncost

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"sync"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/kubernetes"
)

const Annotation = "controller.kubernetes.io/pod-deletion-cost"

type ConnectionTracker struct {
	client                  kubernetes.Interface
	namespace, podName      string
	uid                     types.UID
	connectionsMu, updateMu sync.Mutex
	activeConnections       int64
	lastCost                int32
	lastCostSet             bool
}

func NewConnectionTracker(client kubernetes.Interface, namespace, podName string, uid types.UID) (*ConnectionTracker, error) {
	if client == nil || namespace == "" || podName == "" || uid == "" {
		return nil, fmt.Errorf("client and admitted Pod namespace/name/UID are required")
	}
	return &ConnectionTracker{client: client, namespace: namespace, podName: podName, uid: uid}, nil
}

func (t *ConnectionTracker) OnConnectionOpen() {
	t.connectionsMu.Lock()
	defer t.connectionsMu.Unlock()
	t.activeConnections++
}

func (t *ConnectionTracker) OnConnectionClose() {
	t.connectionsMu.Lock()
	defer t.connectionsMu.Unlock()
	if t.activeConnections > 0 {
		t.activeConnections--
	}
}

// Illustrative coarse policy, not a benchmark or an availability guarantee.
func CostForConnections(count int64) int32 {
	switch {
	case count <= 0:
		return 0
	case count < 10:
		return 100
	case count < 100:
		return 500
	default:
		return 1000
	}
}

// Call at an application-controlled transition or before a controlled scale-down,
// not for every request. Assumes a single owner of this Pod's cost annotation.
func (t *ConnectionTracker) UpdateDeletionCost(parent context.Context) (bool, error) {
	t.updateMu.Lock()
	defer t.updateMu.Unlock()
	if err := parent.Err(); err != nil {
		return false, err
	}
	t.connectionsMu.Lock()
	cost := CostForConnections(t.activeConnections)
	t.connectionsMu.Unlock()
	if t.lastCostSet && t.lastCost == cost {
		return false, nil
	}

	// The Deployment template must already contain an annotations object.
	// JSON Pointer escapes the slash in the annotation key as ~1.
	patch, err := json.Marshal([]map[string]any{
		{"op": "test", "path": "/metadata/uid", "value": string(t.uid)},
		{"op": "add", "path": "/metadata/annotations/controller.kubernetes.io~1pod-deletion-cost", "value": strconv.FormatInt(int64(cost), 10)},
	})
	if err != nil {
		return false, err
	}
	ctx, cancel := context.WithTimeout(parent, 3*time.Second)
	defer cancel()
	_, err = t.client.CoreV1().Pods(t.namespace).Patch(ctx, t.podName, types.JSONPatchType, patch, metav1.PatchOptions{})
	if err != nil {
		return false, err
	}
	t.lastCost, t.lastCostSet = cost, true
	return true, nil
}
```

#### 3. Proteger Pods con localidad de datos

Una señal de localidad puede favorecer una réplica con datos útiles en caché. En el manifiesto de abajo todas las réplicas empiezan con costo 50, así que no hay distinción por costo hasta que un controlador de confianza actualice Pods individuales. El costo no monta, conserva ni restaura datos; las restricciones de almacenamiento y la recuperación de la aplicación siguen siendo responsabilidades independientes.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
spec:
  replicas: 5
  selector:
    matchLabels:
      app: data-processor
  template:
    metadata:
      labels:
        app: data-processor
      annotations:
        # Set high cost for pods with high data locality
        controller.kubernetes.io/pod-deletion-cost: "50"
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - data-processor
              topologyKey: kubernetes.io/hostname
      containers:
      - name: processor
        image: registry.example.com/training/data-processor:validated
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
```

#### 4. Dar prioridad a la eliminación de Pods recién iniciados

Un costo inicial negativo puede favorecer la eliminación de una réplica recién iniciada cuando coinciden los demás criterios del controlador. Elija ese costo en la plantilla **antes** del despliegue inicial y luego actualice un Pod individual después de una transición real de disponibilidad/estado. Un `sleep` fijo en postStart no demuestra que la caché esté lista, y cambiar una plantilla de Deployment existente provoca un rollout.

```yaml
# Deployment Pod-template fragment, chosen before initial deployment.
spec:
  template:
    metadata:
      annotations:
        controller.kubernetes.io/pod-deletion-cost: "-50"
```

### Integración con Horizontal Pod Autoscaler

HPA ajusta el número de réplicas deseado; los controladores de Deployment/ReplicaSet eligen qué Pods eliminar. El costo de eliminación es una señal para esa selección, no una entrada de HPA ni una garantía de protección. Este HPA apunta al Deployment `cache-app` de arriba y requiere métricas funcionales de recursos de CPU y solicitudes de CPU. `selectPolicy: Min` elige la política de reducción de escala más restrictiva.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cache-app
  namespace: deletion-cost-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cache-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
```

### Patrón de actualización dinámica de Pod Deletion Cost

Esta política alternativa combina entradas recientes por Pod (solicitudes, caché y latencia) en señales generales de 100 puntos. Las ponderaciones son ilustrativas, no resultados de rendimiento medidos. No hay un recopilador ficticio ni un ciclo de sondeo en segundo plano: proporcione muestras reales con el UID del Pod y una marca temporal `observed_at` que incluya zona horaria. Si los datos faltan, no son válidos, están obsoletos o corresponden a otro Pod, se genera un error y la anotación no cambia.

Pase un `ApiClient` de Kubernetes para Python que ya esté configurado; la firma de llamada se comprobó con la versión 35.0.0 del cliente. Usa JSON Patch explícitamente, una prueba de UID y timeouts acotados de conexión/lectura. Elija un solo responsable/política para la anotación, en vez de ejecutar ambos ejemplos sobre el mismo Pod.

```python
from datetime import datetime, timezone
import math
import threading

ANNOTATION_PATH = (
    "/metadata/annotations/controller.kubernetes.io~1pod-deletion-cost"
)


def calculate_cost(metrics, now):
    """Illustrative coarse hint from a real, fresh per-Pod sample."""
    observed = datetime.fromisoformat(metrics["observed_at"].replace("Z", "+00:00"))
    if observed.tzinfo is None or now.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    age = (now - observed).total_seconds()
    if age < -5 or age > 60:
        raise ValueError("metrics timestamp is in the future or stale")

    active = metrics["active_requests"]
    if isinstance(active, bool) or not isinstance(active, int) or active < 0:
        raise ValueError("active_requests must be a non-negative integer")
    hit_rate = metrics["cache_hit_rate"]
    latency = metrics["avg_response_time_ms"]
    for value in (hit_rate, latency):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("metrics must be finite numbers")
    if not 0 <= hit_rate <= 1 or latency < 0:
        raise ValueError("invalid hit rate or latency")

    raw_cost = active * 5 + int(hit_rate * 100)
    raw_cost += 50 if latency < 100 else 20 if latency < 500 else 0
    # Coarse buckets reduce annotation churn. Weights are an example policy.
    return min(1000, (raw_cost // 100) * 100)


class DeletionCostManager:
    """Uses a configured Kubernetes Python ApiClient; starts no background loop."""

    def __init__(self, api_client, namespace, pod_name, pod_uid):
        if api_client is None or not all((namespace, pod_name, pod_uid)):
            raise ValueError("API client and admitted Pod namespace/name/UID required")
        self.api_client = api_client
        self.namespace = namespace
        self.pod_name = pod_name
        self.pod_uid = pod_uid
        self._last_cost = None
        self._lock = threading.Lock()

    def update_from_metrics(self, metrics, now=None):
        # A single writer should own this annotation. The Pod template must
        # already create the annotations object with an initial deletion cost.
        if metrics["pod_uid"] != self.pod_uid:
            raise ValueError("metrics belong to a different Pod UID")
        now = now or datetime.now(timezone.utc)
        cost = calculate_cost(metrics, now)
        with self._lock:
            if cost == self._last_cost:
                return False
            patch = [
                {"op": "test", "path": "/metadata/uid", "value": self.pod_uid},
                {"op": "add", "path": ANNOTATION_PATH, "value": str(cost)},
            ]
            # Explicit JSON Patch media type; preserve unrelated Pod fields.
            self.api_client.call_api(
                "/api/v1/namespaces/{namespace}/pods/{name}",
                "PATCH",
                path_params={"namespace": self.namespace, "name": self.pod_name},
                header_params={
                    "Accept": "application/json",
                    "Content-Type": "application/json-patch+json",
                },
                body=patch,
                response_type="V1Pod",
                auth_settings=["BearerToken"],
                _return_http_data_only=True,
                _request_timeout=(3, 5),
            )
            self._last_cost = cost
            return True
```

### Supervisión y depuración

Estos comandos inspeccionan anotaciones y validan una solicitud de reducción de escala sin cambiar el número de réplicas. Una ejecución de prueba en el servidor **no simula qué Pod elegirá ReplicaSet para eliminar**. Para experimentar con una reducción real, use una carga aislada bajo su control, tenga en cuenta que HPA podría sobrescribir el número de réplicas y compare los UID de los Pods y sus ReplicaSets propietarios antes y después. Un evento `Killing` de kubelet por sí solo no demuestra que se haya respetado el orden del costo de eliminación.

```bash
kubectl -n deletion-cost-lab get pods -l app=cache-app \
  -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,COST:.metadata.annotations.controller\.kubernetes\.io/pod-deletion-cost'

kubectl -n deletion-cost-lab get pods -l app=cache-app -o json | \
  jq -r '.items[] | [.metadata.name, .metadata.uid, (.metadata.annotations["controller.kubernetes.io/pod-deletion-cost"] // "0")] | @tsv'

# Server-side dry run changes no replicas and does not predict victim selection.
kubectl -n deletion-cost-lab scale deployment/cache-app --replicas=3 --dry-run=server
kubectl -n deletion-cost-lab get replicasets,pods -l app=cache-app
```

### Recopilación de métricas de Prometheus

`kube_pod_annotations` procede de **kube-state-metrics**, no de la aplicación. Habilite la lista permitida de anotaciones específica en el exportador existente y conserve sus otros indicadores y claves permitidas. El destino de scraping existente de Prometheus debe estar en buen estado; lo siguiente es un fragmento de argumentos, no un Deployment nuevo.

```yaml
# Fragment to merge into the existing kube-state-metrics container arguments.
# Preserve its other arguments and allowlisted keys.
args:
- --metric-annotations-allowlist=pods=[controller.kubernetes.io/pod-deletion-cost]
```

La métrica exportada es un indicador con valor 1 y una **etiqueta** `annotation_controller_kubernetes_io_pod_deletion_cost`. Cambiar con relabeling una anotación no convierte su valor en una métrica numérica. La ausencia de una serie puede indicar que no se recopiló; no se debe suponer que equivale a costo 0.

### Panel de Grafana

Este es un objeto JSON de panel para importar, no el contenedor `{"dashboard": ...}` que requiere la API HTTP. Sustituya `PROMETHEUS_UID` por el UID real del origen de datos. Los paneles cuentan Pods según etiquetas explícitas de anotación, incluidos valores negativos; no grafican el valor 1 del indicador como si fuera el costo de eliminación. Compruebe la lista permitida de kube-state-metrics antes de interpretar los resultados.

```json
{
  "id": null,
  "uid": "pod-deletion-cost-hints",
  "title": "Pod Deletion Cost Hints",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "panels": [
    {
      "id": 1,
      "title": "Pods by explicit deletion cost",
      "type": "piechart",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "datasource": {
        "type": "prometheus",
        "uid": "PROMETHEUS_UID"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "count by (annotation_controller_kubernetes_io_pod_deletion_cost) (kube_pod_annotations{namespace=\"deletion-cost-lab\",annotation_controller_kubernetes_io_pod_deletion_cost=~\"-?[0-9]+\"})",
          "legendFormat": "{{annotation_controller_kubernetes_io_pod_deletion_cost}}",
          "instant": true
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "options": {}
    },
    {
      "id": 2,
      "title": "Pods with an explicit cost",
      "type": "stat",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "datasource": {
        "type": "prometheus",
        "uid": "PROMETHEUS_UID"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "count(kube_pod_annotations{namespace=\"deletion-cost-lab\",annotation_controller_kubernetes_io_pod_deletion_cost!=\"\"})",
          "legendFormat": "",
          "instant": true
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "options": {}
    }
  ]
}
```

### Prácticas recomendadas

1. **Use rangos de costo coherentes**: Defina y utilice rangos de costo uniformes para el equipo.
   * `-100 to -1`: Eliminar primero (Pods nuevos o que aún se están precalentando)
   * `0`: Predeterminado (Pods normales)
   * `1 to 100`: Importancia media (Pods con conexiones activas)
   * `100 to 1000`: Importancia alta (Pods con caché precalentada o muchas conexiones)
2. **Limite las actualizaciones**: Use cambios generales de estado o actualice antes de una reducción de escala controlada; evite escribir con cada solicitud o muestra de métricas.
3. **Establezca límites superiores**: Limite el costo de eliminación para evitar problemas con valores excesivamente grandes.
4. **Supervise**: Observe la distribución de los costos de eliminación para confirmar que funciona como se espera.
5. **Pruebe**: Pruebe el comportamiento de reducción de escala en un entorno de preproducción antes de aplicarlo en producción.
6. **Documente**: Explique el significado de cada rango de costo.

### Limitaciones

* **Alcance de PDB**: Una reducción de escala normal de ReplicaSet/Deployment elimina Pods directamente y no está bloqueada por un PDB. Los PDB rigen las solicitudes realizadas mediante la API de eviction; ninguno de los mecanismos garantiza que un Pod sobreviva a un fallo.
* **Versión/función**: alfa en 1.21 y beta habilitada de forma predeterminada desde 1.22; la base de referencia 1.35.8 citada habilita PodDeletionCost. No interprete esto como una razón para desplegar una versión menor antigua sin soporte.
* **Carga de trabajo/propiedad**: la preferencia se aplica dentro de un ReplicaSet. Los Pods independientes, la selección de ordinales de StatefulSet y la eliminación de una carga de trabajo completa siguen rutas distintas.
* **Asincronía**: las actualizaciones concurrentes, los cambios de disponibilidad y otros criterios de selección pueden invalidar la preferencia esperada. Un Pod nuevo necesita su propia anotación; la señal no es un estado persistente de la aplicación.

## Supervisión y depuración de schedulers personalizados

Después de implementar un scheduler personalizado, es importante supervisarlo y depurarlo. En esta sección se explica cómo hacerlo.

### Arquitectura de supervisión

La arquitectura ilustra una posible elección de integraciones de supervisión; la configuración concreta que sigue utiliza el endpoint HTTPS del propio scheduler y Prometheus Operator.

### Métricas clave de supervisión

Use la latencia de intentos, el resultado de los intentos y la profundidad de la cola como señales distintas; sus nombres y unidades se verifican más abajo.

### Registros

Puede comprender las decisiones de programación consultando los registros del scheduler personalizado:

```bash
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100
```

### Comprobación de eventos

Puede consultar los eventos relacionados con la programación de Pods:

```bash
kubectl -n scheduler-lab get events --field-selector involvedObject.name=<pod-name>
```

### Recopilación de métricas

El ejemplo de abajo supervisa el **scheduler secundario**, que expone por sí mismo métricas HTTPS en el puerto 10259; no necesita un sidecar de métricas. AMP, CloudWatch, recopiladores de registros y el enrutamiento de alertas que aparecen en la ilustración requieren integraciones configuradas por separado.

Requisitos previos: una pila existente de Prometheus Operator con acceso de descubrimiento, un certificado de servidor para `custom-scheduler.scheduler-lab.svc` y su clave privada en el Secret `custom-scheduler-serving-tls` de `scheduler-lab`. Coloque la CA pública en `monitoring/custom-scheduler-ca`, bajo la clave `ca.crt`. El Secret `monitoring/scheduler-scrape-token` debe contener un token válido, de **corta duración y con rotación periódica**, para la ServiceAccount de Prometheus; aquí no se implementan su aprovisionamiento ni rotación.

Aplique el siguiente **parche de combinación estratégica** al Deployment completo de la Parte 1 solo después de preparar esa PKI. Conserva la imagen/configuración/ServiceAccount existente y monta la clave del servidor. Use el proceso de rollout que tenga bajo control; en esta auditoría no se ejecutó ningún rollout TLS.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  template:
    spec:
      containers:
      - name: custom-scheduler
        args:
        - --config=/etc/scheduler/config.yaml
        - --tls-cert-file=/etc/scheduler-serving/tls.crt
        - --tls-private-key-file=/etc/scheduler-serving/tls.key
        volumeMounts:
        - name: serving-tls
          mountPath: /etc/scheduler-serving
          readOnly: true
      volumes:
      - name: serving-tls
        secret:
          secretName: custom-scheduler-serving-tls
          defaultMode: 288
```

El Service expone el puerto HTTPS nombrado. Sustituya la ServiceAccount de ejemplo `monitoring/prometheus` por la identidad real del recolector. El ClusterRole adicional solo permite la solicitud GET al recurso no asociado a una API `/metrics`; no proporciona permisos de descubrimiento. Asegúrese de que el recurso Prometheus seleccione las etiquetas/namespace de este ServiceMonitor.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
  labels:
    app: custom-scheduler
spec:
  selector:
    app: custom-scheduler
  ports:
  - name: https
    port: 10259
    targetPort: https
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: custom-scheduler-metrics
rules:
- nonResourceURLs:
  - /metrics
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: custom-scheduler-metrics
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: custom-scheduler-metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: custom-scheduler
  namespace: monitoring
  labels:
    app: custom-scheduler
spec:
  namespaceSelector:
    matchNames:
    - scheduler-lab
  selector:
    matchLabels:
      app: custom-scheduler
  endpoints:
  - port: https
    path: /metrics
    scheme: https
    interval: 15s
    tlsConfig:
      serverName: custom-scheduler.scheduler-lab.svc
      ca:
        configMap:
          name: custom-scheduler-ca
          key: ca.crt
    authorization:
      type: Bearer
      credentials:
        name: scheduler-scrape-token
        key: token
```

### Configuración del panel

La métrica estable `scheduler_scheduling_attempt_duration_seconds` tiene las etiquetas `result` y `profile`; su histograma estima la latencia de intentos. `scheduler_schedule_attempts_total` es un contador, por lo que debe usarse una tasa para medir el rendimiento. El valor bruto `_count` no representa una duración. El scheduler secundario es distinto de `kubectl get --raw /metrics`, que devuelve métricas del servidor de API.

Sustituya `PROMETHEUS_UID` e importe el JSON incrustado, o configure un proveedor/sidecar de paneles de Grafana que lea este ConfigMap. Crear solo el ConfigMap no carga el panel en Grafana. La etiqueta `grafana_dashboard: "1"` es una convención común de proveedor y debe coincidir con la configuración del entorno; no se ejecutaron la importación real ni las consultas.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-scheduler-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  custom-scheduler-dashboard.json: |
    {
      "id": null,
      "uid": "custom-scheduler",
      "title": "Custom Scheduler",
      "schemaVersion": 39,
      "version": 1,
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Successful scheduling attempt p95",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "PROMETHEUS_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "histogram_quantile(0.95, sum by (le, profile) (rate(scheduler_scheduling_attempt_duration_seconds_bucket{profile=\"custom-scheduler\",result=\"scheduled\"}[5m])))",
              "legendFormat": "{{profile}}",
              "instant": false
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "s"
            },
            "overrides": []
          },
          "options": {}
        },
        {
          "id": 2,
          "title": "Scheduling attempts per second",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "PROMETHEUS_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (result) (rate(scheduler_schedule_attempts_total{profile=\"custom-scheduler\"}[5m]))",
              "legendFormat": "{{result}}",
              "instant": false
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "ops"
            },
            "overrides": []
          },
          "options": {}
        }
      ]
    }
```

## Conclusión

Los schedulers personalizados permiten adaptar el comportamiento de programación de Kubernetes a requisitos específicos. En EKS se pueden implementar con varios métodos, como el enfoque de varios schedulers, el de scheduler extender o el de plugin del framework del scheduler.

Pueden utilizarse en distintos casos, como la optimización de cargas GPU y de la localidad de red. Al implementarlos, también es importante configurar herramientas de supervisión y depuración.

## Referencias y alcance de la validación

* [Costo y limitaciones de eliminación de ReplicaSet](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
* [Presupuestos de interrupción de Pods](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
* [Ruta de eliminación de ReplicaSet fijada](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/replicaset/replica_set.go)
* [Orden de eliminación fijado](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/controller_utils.go)
* [Métricas del scheduler](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/metrics/metrics.go)
* [Métricas de Pods de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
* [API del cliente de Kubernetes para Python](https://github.com/kubernetes-client/python/blob/v35.0.0/kubernetes/client/api_client.py)

Las pruebas locales usan Pods sintéticos, clientes de API simulados y datos aritméticos de prueba. No representan nuevas ejecuciones de benchmarks, utilización GPU real, eliminación de Pods en vivo, precalentamiento de aplicaciones, rotación de certificados/tokens ni disponibilidad en producción.

## Cuestionario

Para comprobar lo aprendido en este capítulo, responda el [cuestionario del tema](../quizzes/scheduling/02-custom-scheduler-part3-quiz.md).
