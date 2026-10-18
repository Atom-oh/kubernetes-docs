# Parte 2: Implementación

> **Base de los ejemplos**: Kubernetes 1.35.8, Go 1.27.2
> **Última actualización**: 16 de octubre de 2026

Use la [configuración del módulo de la Parte 1 y su RBAC/Deployment completo para el planificador secundario](01-custom-scheduler-part1.md). Son dos métodos alternativos para ampliar ese planificador. Los ejemplos se comprobaron localmente; no se probó el despliegue en EKS, la ejecución en una GPU, la puesta en marcha de TLS ni la conmutación por error en producción. Vuelva a validar otras versiones menores de Kubernetes; no dé por sentada la compatibilidad de las interfaces de Go.

## Enfoque de Scheduler Extender

El patrón Scheduler Extender amplía las funciones del planificador predeterminado. En este patrón, el planificador predeterminado envía solicitudes HTTP a un servicio externo (extensor del planificador) para obtener funciones adicionales de filtrado y priorización.

### Arquitectura de Scheduler Extender

El extensor se ejecuta como un servicio independiente al que llama el planificador. En EKS, configure el planificador secundario descrito en la Parte 1.

### Flujo de trabajo de Scheduler Extender

El flujo de trabajo de Scheduler Extender es el siguiente:

![Diagrama de secuencia: el planificador observa el estado del Pod mediante la API, aplica el filtrado y la puntuación internos, delega las llamadas HTTP de filtrado y priorización en el extensor, selecciona un nodo, solicita la vinculación y programa el Pod en ese nodo.](../.gitbook/assets/en-scheduling-02-custom-scheduler-part2-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-scheduling-02-custom-scheduler-part2-0.html)

### Implementación de Scheduler Extender

El extensor implementa el subconjunto configurado de callbacks HTTP **filter**, **prioritize**, **preempt** y **bind**. Este ejemplo implementa solo los callbacks de filtrado y priorización. El extensor no tiene hooks HTTP `PreFilter` ni `PreScore`; esos son puntos de extensión del framework que se ejecutan dentro del proceso. Deje `bindVerb` sin definir para conservar el vinculador predeterminado.

Las prioridades del extensor van de **0 a 10**, mientras que las puntuaciones del framework van de **0 a 100** después de normalizarse. Mantenga las restricciones obligatorias en Filter: en esta versión fijada del planificador, si falla una solicitud de priorización, el error se registra y se omiten sus puntuaciones; por eso, Prioritize no es un punto fiable para hacer cumplir restricciones.

El planificador observa la API y administra su propia cola y caché. Aplica los filtros integrados antes del filtrado del extensor y combina las preferencias de este con las puntuaciones del framework. El servidor de API no inserta los Pods en una cola compartida.

Este ejemplo añade una **condición declarada de memoria por GPU** y conserva las comprobaciones de ajuste de recursos del planificador original. No detecta GPU, no mide la VRAM libre ni reserva memoria del dispositivo.

La política compartida presupone que la API ya aplicó los valores predeterminados a los Pods, que hay un plugin de dispositivos instalado, que las GPU son homogéneas y no usan MIG ni división temporal, y que un administrador mantiene la etiqueta de nodo `training.example.com/gpu-memory-mib`, que declara la memoria mínima de cada GPU elegible. Estas son **claves específicas del laboratorio**, no etiquetas estándar de detección de NVIDIA. Valide el inventario antes de etiquetar los nodos; para GPU heterogéneas o compartidas, use un mecanismo de asignación que conozca los dispositivos. Una etiqueta de nodo por sí sola no garantiza las características del dispositivo que se asignará después.

Guarde los siguientes archivos en el módulo de la Parte 1.

**`gpupolicy/policy.go`**

```go
package gpupolicy

import (
	"fmt"
	"strconv"

	v1 "k8s.io/api/core/v1"
	resourcehelper "k8s.io/component-helpers/resource"
)

const (
	MinMemoryAnnotation = "training.example.com/min-gpu-memory-mib"
	NodeMemoryLabel     = "training.example.com/gpu-memory-mib"
	ScoreCeilingMiB     = int64(80 * 1024)
)

// These are lab policy keys, not automatically populated NVIDIA labels.
// NodeMemoryLabel must describe the minimum memory per eligible GPU on a
// homogeneous, non-shared GPU node, not total or currently free VRAM.
type Requirement struct {
	HasGPU       bool
	MinMemoryMiB int64
}

func FromPod(pod *v1.Pod) (Requirement, error) {
	if pod == nil {
		return Requirement{}, fmt.Errorf("missing pod")
	}
	requests := resourcehelper.PodRequests(pod, resourcehelper.PodResourcesOptions{})
	gpu := requests[v1.ResourceName("nvidia.com/gpu")]
	req := Requirement{HasGPU: gpu.Sign() > 0}
	if raw, exists := pod.Annotations[MinMemoryAnnotation]; exists {
		value, err := strconv.ParseInt(raw, 10, 64)
		if err != nil || value <= 0 || value > 1024*1024 {
			return req, fmt.Errorf("minimum GPU memory must be 1..1048576 MiB")
		}
		if !req.HasGPU {
			return req, fmt.Errorf("minimum GPU memory requires a positive GPU request")
		}
		req.MinMemoryMiB = value
	}
	return req, nil
}

func nodeMemory(node *v1.Node) (int64, error) {
	if node == nil {
		return 0, fmt.Errorf("missing node")
	}
	value, err := strconv.ParseInt(node.Labels[NodeMemoryLabel], 10, 64)
	if err != nil || value <= 0 || value > 1024*1024 {
		return 0, fmt.Errorf("missing or invalid administrator GPU-memory label")
	}
	return value, nil
}

// FitsMemory checks only the declared memory label. The default scheduler
// filters must still check free GPU counts, taints, affinity, volumes, etc.
func FitsMemory(req Requirement, node *v1.Node) (bool, string) {
	if req.MinMemoryMiB == 0 {
		return true, ""
	}
	memory, err := nodeMemory(node)
	if err != nil {
		return false, err.Error()
	}
	if memory < req.MinMemoryMiB {
		return false, "GPU memory label is below the required minimum"
	}
	return true, ""
}

// The 80-GiB ceiling is a chosen scoring scale, not a hardware maximum.
func Score100(req Requirement, node *v1.Node) int64 {
	if !req.HasGPU {
		return 0
	}
	memory, err := nodeMemory(node)
	if err != nil {
		return 0
	}
	if memory >= ScoreCeilingMiB {
		return 100
	}
	return memory * 100 / ScoreCeilingMiB
}
```

**`extenderserver/handler.go`**

El manejador cumple el contrato `nodeCacheCapable: false`, limita las solicitudes del laboratorio a 4 MiB y 512 nodos, rechaza entradas ausentes o mal formadas y devuelve solo un subconjunto de los candidatos recibidos. Esos límites deben dimensionarse para un clúster real. Las etiquetas de memoria obligatorias que no sean válidas excluyen el nodo; la preempción de otros Pods no puede corregir la etiqueta.

```go
package extenderserver

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"

	"example.com/custom-scheduler/gpupolicy"
	v1 "k8s.io/api/core/v1"
	extender "k8s.io/kube-scheduler/extender/v1"
)

const maxBodyBytes = 4 << 20

func NewHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /filter", filter)
	mux.HandleFunc("POST /prioritize", prioritize)
	return mux
}

func readArgs(w http.ResponseWriter, r *http.Request) (extender.ExtenderArgs, gpupolicy.Requirement, bool) {
	var args extender.ExtenderArgs
	body := http.MaxBytesReader(w, r.Body, maxBodyBytes)
	defer body.Close()
	decoder := json.NewDecoder(body)
	if err := decoder.Decode(&args); err != nil {
		var large *http.MaxBytesError
		status := http.StatusBadRequest
		if errors.As(err, &large) {
			status = http.StatusRequestEntityTooLarge
		}
		http.Error(w, "invalid or oversized extender request", status)
		return args, gpupolicy.Requirement{}, false
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		http.Error(w, "expected exactly one JSON object", http.StatusBadRequest)
		return args, gpupolicy.Requirement{}, false
	}
	if args.Pod == nil || args.Nodes == nil || args.NodeNames != nil {
		http.Error(w, "Pod and Nodes required; nodeCacheCapable must be false", http.StatusBadRequest)
		return args, gpupolicy.Requirement{}, false
	}
	if len(args.Nodes.Items) > 512 {
		http.Error(w, "lab candidate-node limit exceeded", http.StatusRequestEntityTooLarge)
		return args, gpupolicy.Requirement{}, false
	}
	seen := make(map[string]bool, len(args.Nodes.Items))
	for _, node := range args.Nodes.Items {
		if node.Name == "" || seen[node.Name] {
			http.Error(w, "missing or duplicate node name", http.StatusBadRequest)
			return args, gpupolicy.Requirement{}, false
		}
		seen[node.Name] = true
	}
	req, err := gpupolicy.FromPod(args.Pod)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return args, req, false
	}
	return args, req, true
}

func writeJSON(w http.ResponseWriter, value any) {
	data, err := json.Marshal(value)
	if err != nil {
		http.Error(w, "response encoding failed", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write(data)
}

func filter(w http.ResponseWriter, r *http.Request) {
	args, req, ok := readArgs(w, r)
	if !ok {
		return
	}
	result := extender.ExtenderFilterResult{
		Nodes:                      &v1.NodeList{Items: []v1.Node{}},
		FailedAndUnresolvableNodes: extender.FailedNodesMap{},
	}
	for _, node := range args.Nodes.Items {
		if fits, reason := gpupolicy.FitsMemory(req, &node); fits {
			result.Nodes.Items = append(result.Nodes.Items, node)
		} else {
			// Preempting other Pods cannot change a hardware inventory label.
			result.FailedAndUnresolvableNodes[node.Name] = reason
		}
	}
	writeJSON(w, result)
}

func prioritize(w http.ResponseWriter, r *http.Request) {
	args, req, ok := readArgs(w, r)
	if !ok {
		return
	}
	result := make(extender.HostPriorityList, 0, len(args.Nodes.Items))
	for _, node := range args.Nodes.Items {
		result = append(result, extender.HostPriority{
			Host: node.Name, Score: gpupolicy.Score100(req, &node) / 10,
		})
	}
	// The wire response is an array, not a hostPriorities wrapper object.
	writeJSON(w, result)
}
```

**`cmd/extender/main.go`**

El servidor exige un certificado de cliente firmado por la CA de cliente configurada. Restrinja esa CA a los clientes del planificador y rote los certificados mediante su proceso habitual de gestión de secretos.

```go
package main

import (
	"crypto/tls"
	"crypto/x509"
	"flag"
	"log"
	"net/http"
	"os"
	"time"

	"example.com/custom-scheduler/extenderserver"
)

func main() {
	certFile := flag.String("tls-cert", "/etc/extender-tls/tls.crt", "server certificate")
	keyFile := flag.String("tls-key", "/etc/extender-tls/tls.key", "server private key")
	caFile := flag.String("client-ca", "/etc/extender-tls/client-ca.crt", "trusted scheduler client CA")
	flag.Parse()
	caPEM, err := os.ReadFile(*caFile)
	if err != nil {
		log.Fatal(err)
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(caPEM) {
		log.Fatal("client CA contains no certificates")
	}
	server := &http.Server{
		Addr:              ":8443",
		Handler:           extenderserver.NewHandler(),
		ReadHeaderTimeout: 2 * time.Second,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
		IdleTimeout:       30 * time.Second,
		TLSConfig: &tls.Config{
			MinVersion: tls.VersionTLS12,
			ClientAuth: tls.RequireAndVerifyClientCert,
			ClientCAs:  roots,
		},
	}
	log.Fatal(server.ListenAndServeTLS(*certFile, *keyFile))
}
```

### Despliegue de Scheduler Extender

Compile `./cmd/extender` con el mismo módulo y la misma versión de Go fijados en la Parte 1, empaquete el binario estático en una imagen que se ejecute con un usuario no root y sustituya el marcador del registro por la imagen o el digest resultante. El Pod del extensor obtiene de cada solicitud todos los datos de programación, por lo que no necesita un token de la API de Kubernetes.

Guarde lo siguiente como `Dockerfile.extender` y compile la imagen localmente. Elija un registro aprobado y sustituya la imagen del despliegue por la que publique.

```dockerfile
FROM gcr.io/distroless/static-debian12:nonroot
COPY scheduler-extender /scheduler-extender
ENTRYPOINT ["/scheduler-extender"]
```

```bash
go mod tidy
CGO_ENABLED=0 go build -buildvcs=false -trimpath -o scheduler-extender ./cmd/extender
: "${REGISTRY:?Set the approved registry/repository prefix}"
docker build -f Dockerfile.extender -t "$REGISTRY/scheduler-extender:v1.35.8-1" .
```

Requisitos previos en `scheduler-lab`: un Secret `extender-server-tls` con `tls.crt`, `tls.key` y `client-ca.crt`, y un Secret `extender-client-tls` con `tls.crt` y `tls.key` del cliente del planificador, además de `ca.crt` del servidor. El certificado del servidor debe cubrir `scheduler-extender.scheduler-lab.svc`. Este documento no crea certificados ni Secrets. NetworkPolicy requiere un CNI que aplique las políticas. Su sonda TCP de preparación solo comprueba que el puerto esté escuchando; no valida el mTLS ni el comportamiento de programación.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scheduler-extender
  namespace: scheduler-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: scheduler-extender
  template:
    metadata:
      labels:
        app: scheduler-extender
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: extender
        image: registry.example.com/training/scheduler-extender:v1.35.8-1
        ports:
        - name: https
          containerPort: 8443
        readinessProbe:
          tcpSocket:
            port: https
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
          seccompProfile:
            type: RuntimeDefault
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
        volumeMounts:
        - name: tls
          mountPath: /etc/extender-tls
          readOnly: true
      volumes:
      - name: tls
        secret:
          secretName: extender-server-tls
          defaultMode: 0440
---
apiVersion: v1
kind: Service
metadata:
  name: scheduler-extender
  namespace: scheduler-lab
spec:
  selector:
    app: scheduler-extender
  ports:
  - name: https
    port: 8443
    targetPort: https
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: scheduler-extender
  namespace: scheduler-lab
spec:
  podSelector:
    matchLabels:
      app: scheduler-extender
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: scheduler-lab
      podSelector:
        matchLabels:
          app: custom-scheduler
    ports:
    - protocol: TCP
      port: 8443
  egress: []
```

### Configuración del planificador

Configure **su planificador secundario**, también en EKS. EKS no expone el archivo de configuración del planificador predeterminado administrado, y `/etc/kubernetes/scheduler.conf` no es una credencial del plano de control que deba montarse desde un nodo de trabajo EC2.

1. Guarde esta configuración. Conserva el perfil de la Parte 1 y su Lease independiente para la elección del líder, mantiene habilitados los filtros integrados y valida el certificado del servidor del extensor. `ignorable: false` hace que los errores de filtrado bloqueen ese intento de programación; no cambia el comportamiento descrito arriba cuando falla la priorización. No establezca `ignoredByScheduler: true` para recursos de GPU: el extensor no tiene en cuenta los dispositivos disponibles.

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
extenders:
- urlPrefix: https://scheduler-extender.scheduler-lab.svc:8443
  filterVerb: filter
  prioritizeVerb: prioritize
  weight: 1
  enableHTTPS: true
  tlsConfig:
    caFile: /etc/extender-client/ca.crt
    certFile: /etc/extender-client/tls.crt
    keyFile: /etc/extender-client/tls.key
  httpTimeout: 2s
  nodeCacheCapable: false
  ignorable: false
```

2. Guarde el ConfigMap correspondiente como `extender-scheduler-config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: extender-scheduler-config
  namespace: scheduler-lab
data:
  config.yaml: |
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
    extenders:
    - urlPrefix: https://scheduler-extender.scheduler-lab.svc:8443
      filterVerb: filter
      prioritizeVerb: prioritize
      weight: 1
      enableHTTPS: true
      tlsConfig:
        caFile: /etc/extender-client/ca.crt
        certFile: /etc/extender-client/tls.crt
        keyFile: /etc/extender-client/tls.key
      httpTimeout: 2s
      nodeCacheCapable: false
      ignorable: false
```

3. Guarde este **parche de fusión estratégica**, no un Deployment independiente, como `extender-scheduler-patch.yaml`. Modifica el volumen de configuración del Deployment existente de la Parte 1 y añade los certificados de cliente, pero conserva su ServiceAccount, las comprobaciones de estado, los recursos y el comando.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  template:
    spec:
      volumes:
      - name: config
        configMap:
          name: extender-scheduler-config
      - name: extender-client
        secret:
          secretName: extender-client-tls
          defaultMode: 288
      containers:
      - name: custom-scheduler
        volumeMounts:
        - name: extender-client
          mountPath: /etc/extender-client
          readOnly: true
```

Aplique estos cambios solo en el laboratorio desechable, después de desplegar el extensor y sustituir los marcadores de imagen:

```bash
kubectl -n scheduler-lab apply -f extender-scheduler-config.yaml
kubectl -n scheduler-lab patch deployment custom-scheduler --type=strategic --patch-file=extender-scheduler-patch.yaml
kubectl -n scheduler-lab rollout restart deployment/custom-scheduler
kubectl -n scheduler-lab rollout status deployment/custom-scheduler
```

El planificador lee la configuración al iniciarse; proyectar un ConfigMap no basta para recargarla. Los montajes con `subPath` también impedirían las actualizaciones normales de los archivos proyectados.

## Plugins del Scheduler Framework

El Scheduler Framework, introducido en Kubernetes 1.15, ofrece una arquitectura basada en plugins. Permite implementar plugins en distintas etapas del flujo de programación.

### Arquitectura del Scheduler Framework

Los plugins se ejecutan dentro del proceso del planificador en los puntos de extensión configurados; el planificador sigue siendo responsable de su cola, caché y flujo de vinculación.

### Configuración de plugins del Scheduler Framework

Cada perfil habilita los plugins registrados para el nombre de su planificador. Todos los perfiles de un mismo proceso comparten una cola de programación y deben usar la misma configuración QueueSort.

### Puntos de extensión del Scheduler Framework

El framework incluye `PreEnqueue`, `QueueSort`, `PreFilter`, `Filter`, `PostFilter`, `PreScore`, `Score` con `NormalizeScore` opcional, `Reserve`/`Unreserve`, `Permit`, `PreBind`, `Bind` y `PostBind`.

Los ciclos de programación seleccionan nodos de forma secuencial; los ciclos de vinculación pueden superponerse. Reserve registra el estado asumido y, si ocurre un fallo, Unreserve lo deshace. PostFilter puede intentar la preempción cuando ningún nodo cumple los requisitos. PostBind se ejecuta después de una vinculación correcta y no puede impedirla. Algunas interfaces de Go de la versión fijada pueden exigir métodos adicionales; compile el código con la versión de destino.

### Implementación de un plugin del Scheduler Framework

Guarde este código como `gpuplugin/plugin.go`. Reutiliza la política anterior y recibe directamente `framework.NodeInfo`. No existe un `NodeInfoKey` integrado que se pueda leer desde CycleState. Este plugin solo gestiona la etiqueta de memoria declarada; los filtros predeterminados siguen gestionando la cantidad de GPU, los taints, la afinidad y los volúmenes.

```go
package gpuplugin

import (
	"context"

	"example.com/custom-scheduler/gpupolicy"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

const Name = "GPUScheduler"

type Plugin struct{}

var _ fwk.FilterPlugin = &Plugin{}
var _ fwk.ScorePlugin = &Plugin{}

func (*Plugin) Name() string { return Name }

func (*Plugin) Filter(_ context.Context, _ fwk.CycleState, pod *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	if info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "missing node")
	}
	req, err := gpupolicy.FromPod(pod)
	if err != nil {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, err.Error())
	}
	if ok, reason := gpupolicy.FitsMemory(req, info.Node()); !ok {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, reason)
	}
	return nil
}

func (*Plugin) Score(_ context.Context, _ fwk.CycleState, pod *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	req, err := gpupolicy.FromPod(pod)
	if err != nil {
		return 0, fwk.AsStatus(err)
	}
	return gpupolicy.Score100(req, info.Node()), nil
}

func (*Plugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func New(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &Plugin{}, nil
}
```

### Registro de un plugin del Scheduler Framework

Para registrar un plugin, debe compilarse dentro del binario del planificador (consulte el comando siguiente). Esta configuración **habilita** el plugin registrado; el YAML por sí solo no carga código Go. No lo habilite en PreFilter ni PreScore si no implementa esas interfaces.

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
    filter:
      enabled:
      - name: GPUScheduler
    score:
      enabled:
      - name: GPUScheduler
        weight: 10
```

## Implementación del Scheduler Framework en EKS

En EKS, ejecute el planificador personalizado en nodos de trabajo EC2 con el ServiceAccount/RBAC de la Parte 1 y su propio perfil y Lease. El acceso a la API dentro del clúster usa credenciales de Kubernetes; la publicación en ECR y las llamadas opcionales a las API de AWS requieren permisos de IAM adecuados e independientes. AWS administra la programación en EKS Fargate, donde no hay GPU disponibles. Use un espacio de nombres de laboratorio que no esté seleccionado por ningún perfil de Fargate.

Compile el **binario del planificador con el plugin integrado**; no cree una imagen independiente del plugin para inyectarla en el plano de control administrado. Las etiquetas de nodo complementan los recursos del plugin de dispositivos, pero no crean capacidad de GPU.

### Arquitectura del Scheduler Framework en EKS

El planificador secundario observa mediante la API el estado de los Pods y nodos, y ejecuta localmente sus plugins registrados. ECR proporciona la imagen; la integración con CloudWatch es opcional. Este ejemplo solo implementa `GPUScheduler`. Los plugins de Spot y zonas de disponibilidad que aparecen en la ilustración arquitectónica necesitan código y pruebas independientes antes de registrarse o habilitarse.

### Pasos para implementar el Scheduler Framework en EKS

1. **Registre el plugin personalizado** (`cmd/gpu-scheduler/main.go`). El comando original ya registra los plugins integrados; registrarlos otra vez produce errores por nombres duplicados.

```go
package main

import (
	"os"

	"example.com/custom-scheduler/gpuplugin"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	// Upstream already registers all built-in plugins. Register only our addition.
	command := app.NewSchedulerCommand(app.WithPlugin(gpuplugin.Name, gpuplugin.New))
	os.Exit(cli.Run(command))
}
```

2. **Compile la imagen** después de guardar la política compartida y el plugin, y ejecutar `go mod tidy`. Haga coincidir la arquitectura de la imagen con la de los nodos Linux donde se ejecutará el planificador. En el flujo de publicación, fije las imágenes base del registro por digest.

```dockerfile
FROM golang:1.27.2 AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -buildvcs=false -trimpath -o /out/gpu-scheduler ./cmd/gpu-scheduler

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/gpu-scheduler /gpu-scheduler
ENTRYPOINT ["/gpu-scheduler"]
```

3. **Publique mediante el flujo de trabajo de su registro**. Los siguientes comandos requieren que se seleccione explícitamente un registro; esta revisión no los ejecutó:

```bash
: "${REGISTRY:?Set the approved registry/repository prefix}"
docker build -t "$REGISTRY/gpu-scheduler:v1.35.8-1" .
docker push "$REGISTRY/gpu-scheduler:v1.35.8-1"
```

4. **Guarde `gpu-scheduler-config.yaml`**. Habilite solo las interfaces implementadas por el plugin y conserve los valores predeterminados originales:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-scheduler-config
  namespace: scheduler-lab
data:
  config.yaml: |
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
        filter:
          enabled:
          - name: GPUScheduler
        score:
          enabled:
          - name: GPUScheduler
            weight: 10
```

5. **Actualice el Deployment de la Parte 1** con este parche de fusión estratégica, guardado como `gpu-scheduler-patch.yaml`. Sustituya primero el marcador de imagen. Esta es una alternativa a la configuración del extensor; no dé por sentado que ambas políticas están activas solo porque aparecen los dos ejemplos.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  template:
    spec:
      volumes:
      - name: config
        configMap:
          name: gpu-scheduler-config
      containers:
      - name: custom-scheduler
        image: registry.example.com/training/gpu-scheduler:v1.35.8-1
```

```bash
kubectl -n scheduler-lab apply -f gpu-scheduler-config.yaml
kubectl -n scheduler-lab patch deployment custom-scheduler --type=strategic --patch-file=gpu-scheduler-patch.yaml
kubectl -n scheduler-lab rollout restart deployment/custom-scheduler
kubectl -n scheduler-lab rollout status deployment/custom-scheduler
```

6. **Configure el Pod para que use este planificador y solicite una GPU**. Si ejecuta este Pod de BusyBox en un laboratorio preparado, solo comprueba la reserva y ubicación; no ejecuta CUDA. Una prueba real de GPU requiere una imagen de aplicación CUDA validada, controladores compatibles y una comprobación del dispositivo. Añada la tolerancia correspondiente si los nodos con GPU tienen taints.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
  annotations:
    training.example.com/min-gpu-memory-mib: "16384"
spec:
  schedulerName: custom-scheduler
  restartPolicy: Never
  containers:
  - name: gpu-reservation-smoke
    image: busybox:1.38.0
    command: ["sh", "-c", "sleep 60"]
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
        nvidia.com/gpu: 1
      limits:
        memory: 128Mi
        nvidia.com/gpu: 1
```

## Conclusión

En este capítulo vimos cómo implementar planificadores personalizados mediante Scheduler Extender y plugins del Scheduler Framework. También explicamos cómo implementar el framework en clústeres de EKS.

En el próximo capítulo veremos casos de implementación de planificadores personalizados en EKS y métodos de monitorización.

## Referencias y límites de verificación

* [Configuración del planificador y campos del extensor](https://kubernetes.io/docs/reference/scheduling/config/)
* [Tipos de la interfaz del extensor en Kubernetes 1.35.8](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [Interfaces fijadas del Scheduler Framework](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Programación de GPU](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
* [Programación en EKS Fargate y sus limitaciones](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)

Las comprobaciones locales del código y la configuración no verifican las etiquetas del hardware real, la compatibilidad de los controladores, el aprovisionamiento de certificados, la programación en el clúster, la capacidad ni la disponibilidad en producción.

## Cuestionario

Para comprobar lo aprendido en este capítulo, pruebe el [cuestionario del tema](../quizzes/scheduling/02-custom-scheduler-part2-quiz.md).
