# Cuestionario de Custom Scheduler (Parte 3)

Este cuestionario evalúa tu comprensión avanzada de la implementación y el uso de Custom Schedulers en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Cuál de los siguientes NO es un problema que puede ocurrir al ejecutar múltiples schedulers simultáneamente en Kubernetes?

A. Contención de recursos
B. Conflictos en decisiones de scheduling
C. Mayor ancho de banda de red
D. Conflictos de leader election

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Mayor ancho de banda de red**

**Explicación:**
"Mayor ancho de banda de red" NO es un problema que pueda ocurrir al ejecutar múltiples schedulers simultáneamente en Kubernetes. Aunque los schedulers se comunican con el API server, el uso de ancho de banda de red suele ser mínimo y no representa una preocupación.

**Problemas reales que pueden ocurrir al ejecutar múltiples schedulers:**

1. **Contención de recursos**:
   - La contención de recursos puede ocurrir cuando múltiples schedulers intentan programar Pods en el mismo pool de Nodes.
   - Como cada scheduler opera de forma independiente sin conocer las decisiones de otros schedulers, existe el riesgo de sobreasignar recursos de los Nodes.
   - Ejemplo: dos schedulers pueden programar Pods simultáneamente en el mismo Node, excediendo la capacidad del Node.

2. **Conflictos en decisiones de scheduling**:
   - Los conflictos pueden ocurrir cuando múltiples schedulers intentan programar el mismo Pod.
   - Esto puede suceder cuando los Pods no especifican explícitamente un `schedulerName`, o cuando múltiples schedulers usan el mismo nombre.
   - Ejemplo: ocurren race conditions cuando dos schedulers intentan vincular el mismo Pod a diferentes Nodes.

3. **Conflictos de leader election**:
   - Si múltiples instancias de scheduler con el mismo nombre se ejecutan con leader election habilitado, pueden ocurrir conflictos en el mecanismo de leader election.
   - Ejemplo: múltiples instancias de scheduler con el mismo nombre compitiendo por el liderazgo pueden causar transiciones de liderazgo inestables.

**Mejores prácticas al ejecutar múltiples schedulers:**

1. **Separación clara de responsabilidades**:
   ```yaml
   # Pod for default scheduler
   apiVersion: v1
   kind: Pod
   metadata:
     name: default-pod
   spec:
     # Uses default scheduler when schedulerName is not specified
     containers:
     - name: nginx
       image: nginx

   # Pod for custom scheduler
   apiVersion: v1
   kind: Pod
   metadata:
     name: custom-pod
   spec:
     schedulerName: my-custom-scheduler  # Specify custom scheduler
     containers:
     - name: nginx
       image: nginx
   ```

2. **Usar nombres de scheduler únicos**:
   ```yaml
   # Custom scheduler deployment
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: my-custom-scheduler
     namespace: kube-system
   spec:
     replicas: 1
     selector:
       matchLabels:
         component: my-custom-scheduler
     template:
       metadata:
         labels:
           component: my-custom-scheduler
       spec:
         containers:
         - name: scheduler
           image: my-custom-scheduler:v1.0
           args:
           - --scheduler-name=my-custom-scheduler  # Use unique name
           - --leader-elect=true
           - --leader-elect-resource-name=my-custom-scheduler  # Use unique resource name
   ```

3. **Separar pools de Nodes usando etiquetas de Node y taints**:
   ```yaml
   # Apply node labels and taints
   kubectl label node node1 scheduler=default
   kubectl label node node2 scheduler=custom

   kubectl taint nodes node2 dedicated=custom-scheduler:NoSchedule

   # Custom scheduler configuration
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: my-custom-scheduler
     plugins:
       filter:
         enabled:
         - name: NodeSelector
     pluginConfig:
     - name: NodeSelector
       args:
         nodeSelector:
           scheduler: custom
   ```

4. **Establecer resource quotas**:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: default-scheduler-quota
     namespace: default-workloads
   spec:
     hard:
       pods: "10"
       cpu: "20"
       memory: 40Gi

   ---
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: custom-scheduler-quota
     namespace: custom-workloads
   spec:
     hard:
       pods: "10"
       cpu: "20"
       memory: 40Gi
   ```

**Monitoreo de múltiples schedulers:**
```bash
# Check scheduler pods
kubectl get pods -n kube-system -l component=kube-scheduler
kubectl get pods -n kube-system -l component=my-custom-scheduler

# Check scheduler logs
kubectl logs -n kube-system -l component=kube-scheduler
kubectl logs -n kube-system -l component=my-custom-scheduler

# Check scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**Explicación de las otras opciones:**
- A. Contención de recursos: un problema real que puede ocurrir cuando múltiples schedulers programan Pods en el mismo pool de Nodes.
- B. Conflictos en decisiones de scheduling: un problema real que puede ocurrir cuando múltiples schedulers intentan programar el mismo Pod.
- D. Conflictos de leader election: un problema real que puede ocurrir cuando múltiples instancias de scheduler con el mismo nombre compiten por el liderazgo.
</details>

### 2. ¿Cuál es el rol del punto de extensión "Permit" en el scheduler de Kubernetes?

A. Vincular Pods a Nodes
B. Permitir, denegar o retrasar el scheduling de Pods
C. Excluir Nodes donde los Pods no pueden ejecutarse
D. Asignar puntuaciones a Nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir, denegar o retrasar el scheduling de Pods**

**Explicación:**
El rol del punto de extensión "Permit" en el framework de scheduling de Kubernetes es permitir, denegar o retrasar el scheduling de Pods. Los plugins Permit se ejecutan después de que se selecciona un Node, pero antes de la fase de binding, proporcionando aprobación o rechazo final para las decisiones de scheduling de Pods.

**Funciones clave del punto de extensión Permit:**
1. **Allow**: Permite que el scheduling del Pod continúe hacia la fase de binding.
2. **Deny**: Rechaza el scheduling del Pod para que se pueda seleccionar otro Node.
3. **Wait**: Retrasa temporalmente el scheduling del Pod y espera hasta que se cumplan condiciones específicas.

**Interfaz del plugin Permit:**
```go
type PermitPlugin interface {
    Plugin
    // Permit allows, denies, or delays pod scheduling.
    // Return values:
    // - Success: Allows pod scheduling.
    // - Deny: Rejects pod scheduling.
    // - Wait: Delays pod scheduling and waits until timeout or allowed.
    Permit(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) (*Status, time.Duration)
}
```

**Tipos de resultado de Permit:**
1. **Success**: Permite el scheduling del Pod.
2. **Deny**: Rechaza el scheduling del Pod.
3. **Wait**: Retrasa el scheduling del Pod y espera durante el tiempo especificado.

**Plugins Permit predeterminados:**
Kubernetes proporciona los siguientes plugins Permit predeterminados:

1. **TaintToleration**: Comprueba los taints de Node y las tolerations de Pod.
2. **PodTopologySpread**: Comprueba las restricciones de distribución topológica de Pods.

**Ejemplo de plugin Permit personalizado:**
```go
// CustomPermit implements custom permit logic.
type CustomPermit struct {
    handle framework.Handle
    // Map to track waiting pods
    waitingPods map[string]waitingPod
    // Mutex to synchronize map access
    mu sync.RWMutex
}

// waitingPod stores information about waiting pods.
type waitingPod struct {
    pod      *v1.Pod
    nodeName string
    status   chan bool  // true: allow, false: deny
}

// Name returns the plugin name.
func (pl *CustomPermit) Name() string {
    return "CustomPermit"
}

// Permit allows, denies, or delays pod scheduling.
func (pl *CustomPermit) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    // Example: Allow, deny, or delay pod scheduling based on specific conditions
    if shouldWait(pod, nodeName) {
        // Add pod to waiting list
        key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)

        pl.mu.Lock()
        if pl.waitingPods == nil {
            pl.waitingPods = make(map[string]waitingPod)
        }
        pl.waitingPods[key] = waitingPod{
            pod:      pod,
            nodeName: nodeName,
            status:   make(chan bool),
        }
        pl.mu.Unlock()

        // Wait for up to 10 minutes
        return framework.NewStatus(framework.Wait, "waiting for condition"), 10 * time.Minute
    }

    if shouldDeny(pod, nodeName) {
        return framework.NewStatus(framework.Unschedulable, "denied by custom permit plugin"), 0
    }

    // Allow pod scheduling
    return nil, 0
}

// Allow waiting pod
func (pl *CustomPermit) Allow(pod *v1.Pod) {
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)

    pl.mu.RLock()
    waitingPod, ok := pl.waitingPods[key]
    pl.mu.RUnlock()

    if ok {
        // Allow pod
        waitingPod.status <- true

        pl.mu.Lock()
        delete(pl.waitingPods, key)
        pl.mu.Unlock()
    }
}

// Reject waiting pod
func (pl *CustomPermit) Reject(pod *v1.Pod) {
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)

    pl.mu.RLock()
    waitingPod, ok := pl.waitingPods[key]
    pl.mu.RUnlock()

    if ok {
        // Reject pod
        waitingPod.status <- false

        pl.mu.Lock()
        delete(pl.waitingPods, key)
        pl.mu.Unlock()
    }
}

// Function to check if pod should wait
func shouldWait(pod *v1.Pod, nodeName string) bool {
    // Implement custom logic
    return false
}

// Function to check if pod should be denied
func shouldDeny(pod *v1.Pod, nodeName string) bool {
    // Implement custom logic
    return false
}
```

**Habilitación del plugin Permit en la configuración del scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    permit:
      enabled:
      - name: CustomPermit
      disabled:
      - name: TaintToleration  # Disable default plugin
```

**Casos de uso de Permit:**
1. **Gang scheduling**: Retrasar el scheduling de un grupo de Pods hasta que todos los Pods relacionados estén listos para programarse.
2. **Reserva de recursos**: Reservar recursos externos antes de que los Pods se programen.
3. **Validación de políticas**: Asegurar que el scheduling de Pods cumpla con las políticas organizacionales.
4. **Flujos de aprobación**: Solicitar aprobación externa para el scheduling de Pods.

**Ejemplo de Gang scheduling:**
Gang scheduling es una técnica que asegura que todos los Pods relacionados se programen juntos. Esto es útil para cargas de trabajo como trabajos de entrenamiento distribuido, donde todos los componentes deben ejecutarse simultáneamente.

```go
// GangPermit implements Gang scheduling.
type GangPermit struct {
    handle framework.Handle
    // Map to track waiting pods by group
    waitingGroups map[string]gangGroup
    mu sync.RWMutex
}

// gangGroup stores Gang information.
type gangGroup struct {
    pods      map[string]*v1.Pod
    nodeName  map[string]string
    minCount  int
    readyPods int
}

// Permit allows, denies, or delays pod scheduling.
func (pl *GangPermit) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    // Get Gang ID
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        // Process as regular pod if no Gang ID
        return nil, 0
    }

    pl.mu.Lock()
    defer pl.mu.Unlock()

    // Create group if not exists
    if _, ok := pl.waitingGroups[gangID]; !ok {
        minCount, _ := strconv.Atoi(pod.Labels["gang-min-count"])
        if minCount <= 0 {
            minCount = 1
        }

        pl.waitingGroups[gangID] = gangGroup{
            pods:      make(map[string]*v1.Pod),
            nodeName:  make(map[string]string),
            minCount:  minCount,
            readyPods: 0,
        }
    }

    // Add pod
    group := pl.waitingGroups[gangID]
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    group.pods[key] = pod
    group.nodeName[key] = nodeName
    group.readyPods++

    // Check if minimum count reached
    if group.readyPods >= group.minCount {
        // Allow all pods
        for _, p := range group.pods {
            pl.handle.PermitPlugin().Allow(p)
        }

        // Delete group
        delete(pl.waitingGroups, gangID)

        return nil, 0
    }

    // Wait until minimum count is reached
    return framework.NewStatus(framework.Wait, "waiting for gang members"), 10 * time.Minute
}
```

**Problemas con las otras opciones:**
- A. Vincular Pods a Nodes: este es el rol del punto de extensión "Bind".
- C. Excluir Nodes donde los Pods no pueden ejecutarse: este es el rol del punto de extensión "Filter".
- D. Asignar puntuaciones a Nodes: este es el rol del punto de extensión "Score".
</details>
### 3. ¿Cuál es el propósito principal de Gang Scheduling en Kubernetes?

A. Colocar Pods solo en Nodes específicos
B. Asegurar que todos los Pods relacionados se programen juntos
C. Distribuir Pods de manera uniforme entre varios Nodes
D. Programar Pods según prioridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Asegurar que todos los Pods relacionados se programen juntos**

**Explicación:**
El propósito principal de Gang Scheduling en Kubernetes es asegurar que todos los Pods relacionados se programen juntos. Esto es importante para cargas de trabajo como trabajos de entrenamiento distribuido y trabajos de procesamiento de datos distribuido, donde todos los componentes deben ejecutarse simultáneamente.

**Por qué se necesita Gang scheduling:**
1. **Requisito de todo o nada**: Algunas cargas de trabajo requieren que todos los componentes se ejecuten simultáneamente; si solo algunos se ejecutan, el trabajo no avanza.
2. **Prevención del desperdicio de recursos**: Si solo algunos Pods se programan mientras otros esperan, los recursos utilizados por los Pods ya programados pueden desperdiciarse.
3. **Prevención de deadlock**: Puede ocurrir deadlock cuando Pods interdependientes se programan en momentos diferentes.

**Métodos de implementación de Gang scheduling:**
Kubernetes no admite Gang scheduling de forma nativa, pero puede implementarse mediante:

1. **Custom scheduler**: Implementar Gang scheduling usando el punto de extensión Permit.
2. **Controlador externo**: Implementar un controlador que administre Gang scheduling fuera de Kubernetes.
3. **Soluciones open source**: Usar schedulers open source como Volcano o Kube-batch.

**Ejemplo de Gang scheduling (Volcano):**
```yaml
# PodGroup definition for Gang scheduling
apiVersion: scheduling.volcano.sh/v1beta1
kind: PodGroup
metadata:
  name: tf-training
  namespace: default
spec:
  minMember: 4  # At least 4 pods must be scheduled together
  minResources:
    cpu: 8
    memory: 16Gi
  queue: default

---
# Pod belonging to Gang
apiVersion: v1
kind: Pod
metadata:
  name: tf-worker-0
  namespace: default
  labels:
    app: tf-training
  annotations:
    scheduling.volcano.sh/pod-group: tf-training  # Reference PodGroup
spec:
  schedulerName: volcano  # Use Volcano scheduler
  containers:
  - name: tensorflow
    image: tensorflow/tensorflow:latest-gpu
    resources:
      requests:
        cpu: 2
        memory: 4Gi
        nvidia.com/gpu: 1
```

**Implementación de Gang scheduling usando un plugin Permit personalizado:**
```go
// GangSchedulingPlugin implements Gang scheduling.
type GangSchedulingPlugin struct {
    handle framework.Handle
    // Pod tracking per Gang
    gangs map[string]*Gang
    mu sync.RWMutex
}

// Gang represents a group of related pods.
type Gang struct {
    MinRequired int
    Scheduled   map[string]string  // pod name -> node name
    Waiting     map[string]*framework.WaitingPod
}

// Name returns the plugin name.
func (pl *GangSchedulingPlugin) Name() string {
    return "GangSchedulingPlugin"
}

// PreFilter initializes Gang information.
func (pl *GangSchedulingPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        return nil  // Process as regular pod if no Gang ID
    }

    pl.mu.Lock()
    defer pl.mu.Unlock()

    if _, ok := pl.gangs[gangID]; !ok {
        minRequired, _ := strconv.Atoi(pod.Labels["gang-min-required"])
        if minRequired <= 0 {
            minRequired = 1
        }

        pl.gangs[gangID] = &Gang{
            MinRequired: minRequired,
            Scheduled:   make(map[string]string),
            Waiting:     make(map[string]*framework.WaitingPod),
        }
    }

    return nil
}

// Permit implements Gang scheduling logic.
func (pl *GangSchedulingPlugin) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        return nil, 0  // Process as regular pod if no Gang ID
    }

    pl.mu.Lock()
    defer pl.mu.Unlock()

    gang, ok := pl.gangs[gangID]
    if !ok {
        return framework.NewStatus(framework.Error, "gang not found"), 0
    }

    podKey := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    gang.Scheduled[podKey] = nodeName

    // Check if enough pods are scheduled
    if len(gang.Scheduled) >= gang.MinRequired {
        // Allow all waiting pods
        for _, waitingPod := range gang.Waiting {
            waitingPod.Allow(pl.Name())
        }
        gang.Waiting = make(map[string]*framework.WaitingPod)
        return nil, 0
    }

    // Wait until enough pods are scheduled
    waitingPod := framework.NewWaitingPod(pod)
    gang.Waiting[podKey] = waitingPod
    return framework.NewStatus(framework.Wait, "waiting for gang members"), 10 * time.Minute
}
```

**Ventajas y desventajas de Gang scheduling:**
Ventajas:
- Asegura que todos los Pods relacionados se programen juntos
- Previene el desperdicio de recursos
- Previene deadlock y starvation

Desventajas:
- Mayor complejidad de implementación
- Posibles retrasos de scheduling
- Posible disminución en la utilización de recursos del clúster

**Cargas de trabajo que necesitan Gang scheduling:**
1. **Trabajos de entrenamiento distribuido**: Frameworks de entrenamiento distribuido como TensorFlow, PyTorch
2. **Procesamiento de datos distribuido**: Frameworks de procesamiento de datos distribuido como Spark, Flink
3. **Trabajos MPI**: Cargas de trabajo de computación de alto rendimiento (HPC)
4. **Service mesh**: Service meshes donde múltiples componentes deben trabajar juntos

**Problemas con las otras opciones:**
- A. Colocar Pods solo en Nodes específicos: este es el rol de node selectors o node affinity.
- C. Distribuir Pods de manera uniforme entre varios Nodes: este es el rol de las restricciones de pod topology spread.
- D. Programar Pods según prioridad: este es el rol de pod priority y preemption.
</details>

### 4. ¿Cuál de los siguientes NO es un endpoint de API requerido al implementar un Scheduler Extender en Kubernetes?

A. /filter
B. /prioritize
C. /bind
D. /validate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. /validate**

**Explicación:**
"/validate" NO es un endpoint de API requerido al implementar un Scheduler Extender en Kubernetes. Los scheduler extenders suelen implementar endpoints como "/filter", "/prioritize", "/bind", "/preempt", pero "/validate" no es una API estándar para scheduler extenders.

**Endpoints de API de Scheduler Extender:**
1. **filter**: Recibe una lista de Nodes y devuelve una lista filtrada de Nodes.
2. **prioritize**: Recibe una lista de Nodes y asigna puntuaciones a cada Node.
3. **bind**: Vincula un Pod a un Node.
4. **preempt**: Devuelve Nodes y Pods para preemption.

**Ejemplo de configuración de Scheduler Extender:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  extenders:
  - urlPrefix: "http://extender-service:8080"
    filterVerb: "filter"
    prioritizeVerb: "prioritize"
    bindVerb: "bind"
    enableHTTPS: false
    nodeCacheCapable: false
    ignorable: true
    managedResources:
    - name: example.com/foo
      ignoredByScheduler: true
```

**Formatos de solicitud y respuesta de la API de Scheduler Extender:**

1. **API filter**:
   - Solicitud:
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - Respuesta:
     ```json
     {
       "nodes": <filtered-nodes>,
       "nodenames": <filtered-node-names>,
       "failedNodes": <failed-nodes>,
       "error": <error-message>
     }
     ```

2. **API prioritize**:
   - Solicitud:
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - Respuesta:
     ```json
     {
       "hostPriorities": [
         {
           "host": <node-name>,
           "score": <score>
         },
         ...
       ],
       "error": <error-message>
     }
     ```

3. **API bind**:
   - Solicitud:
     ```json
     {
       "pod": <pod>,
       "node": <node-name>
     }
     ```
   - Respuesta:
     ```json
     {
       "error": <error-message>
     }
     ```

4. **API preempt**:
   - Solicitud:
     ```json
     {
       "pod": <pod>,
       "nodenames": <node-names>,
       "nodes": <nodes>
     }
     ```
   - Respuesta:
     ```json
     {
       "nodenames": <node-names>,
       "nodes": <nodes>,
       "podsToPreempt": {
         <node-name>: [<pod>, ...],
         ...
       },
       "error": <error-message>
     }
     ```

**Ejemplo de implementación de Scheduler Extender (Go):**
```go
package main

import (
    "encoding/json"
    "log"
    "net/http"

    v1 "k8s.io/api/core/v1"
    extender "k8s.io/kube-scheduler/extender/v1"
)

func main() {
    http.HandleFunc("/filter", filterHandler)
    http.HandleFunc("/prioritize", prioritizeHandler)
    http.HandleFunc("/bind", bindHandler)

    log.Fatal(http.ListenAndServe(":8080", nil))
}

// Filter handler
func filterHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderArgs
    var result extender.ExtenderFilterResult

    // Decode request body
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement filtering logic
    filteredNodes := make([]v1.Node, 0, len(args.Nodes.Items))
    failedNodes := make(map[string]string)

    for _, node := range args.Nodes.Items {
        // Custom filtering logic
        if customFilter(&args.Pod, &node) {
            filteredNodes = append(filteredNodes, node)
        } else {
            failedNodes[node.Name] = "Node failed custom filter"
        }
    }

    // Set result
    result.Nodes = &v1.NodeList{Items: filteredNodes}
    result.FailedNodes = failedNodes

    // Send response
    w.Header().Set("Content-Type", "application/json")
    if err := json.NewEncoder(w).Encode(result); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// Prioritize handler
func prioritizeHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderArgs
    var result extender.HostPriorityList

    // Decode request body
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement prioritization logic
    result = make(extender.HostPriorityList, 0, len(args.Nodes.Items))

    for _, node := range args.Nodes.Items {
        // Custom score calculation
        score := customScore(&args.Pod, &node)
        result = append(result, extender.HostPriority{
            Host:  node.Name,
            Score: score,
        })
    }

    // Send response
    w.Header().Set("Content-Type", "application/json")
    if err := json.NewEncoder(w).Encode(result); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// Bind handler
func bindHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderBindingArgs

    // Decode request body
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement binding logic
    err := customBind(&args.Pod, args.Node)

    // Send response
    w.Header().Set("Content-Type", "application/json")
    if err != nil {
        json.NewEncoder(w).Encode(extender.ExtenderBindingResult{
            Error: err.Error(),
        })
    } else {
        json.NewEncoder(w).Encode(extender.ExtenderBindingResult{})
    }
}

// Custom filtering function
func customFilter(pod *v1.Pod, node *v1.Node) bool {
    // Implement custom filtering logic
    return true
}

// Custom score calculation function
func customScore(pod *v1.Pod, node *v1.Node) int64 {
    // Implement custom score calculation logic
    return 100
}

// Custom binding function
func customBind(pod *v1.Pod, nodeName string) error {
    // Implement custom binding logic
    return nil
}
```

**Ventajas y desventajas de Scheduler Extenders:**
Ventajas:
- Pueden desarrollarse de forma independiente del codebase del scheduler
- Pueden implementarse en varios lenguajes de programación
- Se ven menos afectados por las actualizaciones del scheduler

Desventajas:
- Degradación del rendimiento debido a la sobrecarga de comunicación HTTP
- Solo pueden extender algunas etapas del ciclo de scheduling
- Posibilidad de fallo de comunicación entre el scheduler y el extender

**Scheduler Extender vs plugins del Scheduling Framework:**
- **Scheduler Extender**: Se ejecuta como un proceso externo mediante webhooks HTTP.
- **Plugins del Scheduling Framework**: Se ejecutan directamente integrados con el codebase del scheduler.

**Explicación de las otras opciones:**
- A. /filter: Un endpoint de API válido de scheduler extender que filtra la lista de Nodes.
- B. /prioritize: Un endpoint de API válido de scheduler extender que asigna puntuaciones a Nodes.
- C. /bind: Un endpoint de API válido de scheduler extender que vincula Pods a Nodes.
</details>
### 5. ¿Cuál es el rol del punto de extensión "PostFilter" en el framework del scheduler de Kubernetes?

A. Asignar puntuaciones a Nodes después del filtering
B. Vincular Pods a Nodes después del filtering
C. Ejecutar lógica de preemption cuando falla el filtering
D. Actualizar el estado del Pod después del filtering

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ejecutar lógica de preemption cuando falla el filtering**

**Explicación:**
El rol del punto de extensión "PostFilter" en el framework de scheduling de Kubernetes es ejecutar lógica de preemption cuando falla el filtering. Cuando todos los Nodes se excluyen durante la fase de filtering y un Pod no puede programarse, los plugins PostFilter encuentran formas de programar el Pod mediante preemption.

**Funciones clave del punto de extensión PostFilter:**
1. **Identificar candidatos de preemption**: Identifica Pods y Nodes que pueden ser preempted.
2. **Simulación de preemption**: Simula si los Pods pueden programarse después de la preemption.
3. **Decisión de preemption**: Determina la estrategia óptima de preemption.

**Interfaz del plugin PostFilter:**
```go
type PostFilterPlugin interface {
    Plugin
    // PostFilter is called when filtering fails.
    // Finds ways to schedule pods through preemption.
    PostFilter(ctx context.Context, state *CycleState, pod *v1.Pod, filteredNodeStatusMap NodeToStatusMap) (*PostFilterResult, *Status)
}

// PostFilterResult represents the result of PostFilter operation.
type PostFilterResult struct {
    // Node where pod will be scheduled after preemption
    NominatedNodeName string
}
```

**Plugin PostFilter predeterminado:**
Kubernetes proporciona el siguiente plugin PostFilter predeterminado:

1. **DefaultPreemption**: Implementa la lógica de preemption predeterminada.

**Funcionamiento del plugin DefaultPreemption:**
1. Identifica Nodes donde se puede liberar espacio mediante preemption de Pods de menor prioridad.
2. Determina qué Pods preempt en cada Node.
3. Verifica que los Pods puedan programarse después de la preemption.
4. Selecciona la estrategia óptima de preemption.
5. Establece el Node seleccionado como el nominatedNodeName del Pod.

**Ejemplo de plugin PostFilter personalizado:**
```go
// CustomPostFilter implements custom preemption logic.
type CustomPostFilter struct {
    handle framework.Handle
}

// Name returns the plugin name.
func (pl *CustomPostFilter) Name() string {
    return "CustomPostFilter"
}

// PostFilter is called when filtering fails.
func (pl *CustomPostFilter) PostFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, filteredNodeStatusMap framework.NodeToStatusMap) (*framework.PostFilterResult, *framework.Status) {
    // Identify preemptable nodes
    preemptableNodes := identifyPreemptableNodes(pl.handle, pod, filteredNodeStatusMap)
    if len(preemptableNodes) == 0 {
        return nil, framework.NewStatus(framework.Unschedulable, "no preemptable nodes found")
    }

    // Determine pods to preempt on each node
    nodeToVictims := map[string]*framework.Victims{}
    for _, node := range preemptableNodes {
        victims, err := selectVictimsOnNode(pl.handle, pod, node)
        if err != nil {
            continue
        }
        nodeToVictims[node.Name] = victims
    }

    // Select optimal preemption strategy
    nominatedNode, victims := selectBestNodeForPreemption(nodeToVictims)
    if nominatedNode == "" {
        return nil, framework.NewStatus(framework.Unschedulable, "no node for preemption")
    }

    // Execute preemption
    for _, victim := range victims.Pods {
        if err := pl.handle.ClientSet().CoreV1().Pods(victim.Namespace).Delete(ctx, victim.Name, metav1.DeleteOptions{}); err != nil {
            return nil, framework.NewStatus(framework.Error, err.Error())
        }
    }

    return &framework.PostFilterResult{
        NominatedNodeName: nominatedNode,
    }, nil
}

// Identify preemptable nodes
func identifyPreemptableNodes(handle framework.Handle, pod *v1.Pod, filteredNodeStatusMap framework.NodeToStatusMap) []*v1.Node {
    // Implementation omitted
    return nil
}

// Select pods to preempt on node
func selectVictimsOnNode(handle framework.Handle, pod *v1.Pod, node *v1.Node) (*framework.Victims, error) {
    // Implementation omitted
    return nil, nil
}

// Select optimal preemption strategy
func selectBestNodeForPreemption(nodeToVictims map[string]*framework.Victims) (string, *framework.Victims) {
    // Implementation omitted
    return "", nil
}
```

**Habilitación del plugin PostFilter en la configuración del scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    postFilter:
      enabled:
      - name: CustomPostFilter
      disabled:
      - name: DefaultPreemption  # Disable default plugin
```

**Configuraciones relacionadas con preemption:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: DefaultPreemption
    args:
      minCandidateNodesPercentage: 10  # Minimum percentage of preemption candidate nodes
      minCandidateNodesAbsolute: 100   # Minimum number of preemption candidate nodes
```

**Proceso de preemption:**
1. La fase PostFilter se llama cuando un Pod falla la fase de filtering en todos los Nodes.
2. El plugin PostFilter identifica Nodes candidatos para preemption.
3. Determina qué Pods preempt en cada Node.
4. Verifica que los Pods puedan programarse después de la preemption.
5. Selecciona la estrategia óptima de preemption.
6. Establece el Node seleccionado como el nominatedNodeName del Pod.
7. Los Pods preempted pasan por una terminación graceful.
8. Cuando los Pods preempted terminan, los Pods de mayor prioridad se programan.

**Monitoreo de métricas relacionadas con preemption:**
```bash
# Check preemption-related metrics from scheduler metrics
kubectl get --raw /metrics | grep scheduler_preemption
```

**Comprobación de eventos de preemption:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Problemas con las otras opciones:**
- A. Asignar puntuaciones a Nodes después del filtering: este es el rol del punto de extensión "Score".
- B. Vincular Pods a Nodes después del filtering: este es el rol del punto de extensión "Bind".
- D. Actualizar el estado del Pod después del filtering: este no es un punto de extensión en el framework del scheduler.
</details>

### 6. ¿Cuál es el propósito principal del plugin "NodeResourcesBalancedAllocation" en el scheduler de Kubernetes?

A. Dar puntuaciones más altas a Nodes con uso equilibrado de CPU y memoria
B. Dar puntuaciones más altas a Nodes con menor uso de recursos
C. Dar puntuaciones más altas a Nodes con mayor uso de recursos
D. Establecer límites de recursos en Nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Dar puntuaciones más altas a Nodes con uso equilibrado de CPU y memoria**

**Explicación:**
El propósito principal del plugin "NodeResourcesBalancedAllocation" en el scheduler de Kubernetes es dar puntuaciones más altas a Nodes con uso equilibrado de CPU y memoria. Este plugin prefiere Nodes donde la diferencia entre utilización de CPU y memoria es pequeña, mejorando el balance general del uso de recursos en el clúster.

**Funcionamiento del plugin NodeResourcesBalancedAllocation:**
1. Calcula la utilización de CPU y la utilización de memoria para cada Node.
2. Calcula la diferencia entre la utilización de CPU y la utilización de memoria.
3. Da puntuaciones más altas a Nodes con diferencias más pequeñas.

**Método de cálculo de puntuación:**
```
score = 10 - variance(cpuFraction, memoryFraction) * 10
```
Donde:
- cpuFraction = (CPU solicitada + solicitud de CPU del Pod) / CPU asignable
- memoryFraction = (memoria solicitada + solicitud de memoria del Pod) / memoria asignable
- variance(a, b) = |a - b|

**Ejemplo:**
- Node A: utilización de CPU 80%, utilización de memoria 80% -> diferencia: 0% -> puntuación: 10
- Node B: utilización de CPU 90%, utilización de memoria 50% -> diferencia: 40% -> puntuación: 6
- Node C: utilización de CPU 30%, utilización de memoria 90% -> diferencia: 60% -> puntuación: 4

En este caso, Node A recibe la puntuación más alta y es el que tiene mayor probabilidad de ser seleccionado.

**Habilitación del plugin NodeResourcesBalancedAllocation en la configuración del scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2  # Set weight
```

**Configuración del plugin:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  pluginConfig:
  - name: NodeResourcesBalancedAllocation
    args:
      resources:
      - name: cpu
        weight: 1
      - name: memory
        weight: 1
```

**NodeResourcesBalancedAllocation vs otros plugins de scoring:**
1. **NodeResourcesBalancedAllocation**: Prefiere Nodes con uso equilibrado de CPU y memoria.
2. **NodeResourcesFit**: Prefiere Nodes con más recursos disponibles en comparación con los recursos solicitados.
3. **NodeResourcesLeastAllocated**: Prefiere Nodes con menor uso de recursos.
4. **NodeResourcesMostAllocated**: Prefiere Nodes con mayor uso de recursos.

**Casos de uso:**
1. **Balance de recursos**: Mejora el balance de uso de CPU y memoria en todo el clúster.
2. **Prevención de cuellos de botella**: Evita que un tipo de recurso (CPU o memoria) se agote antes que el otro.
3. **Mejora de escalabilidad**: Los clústeres con uso equilibrado de recursos pueden escalar con mayor eficiencia.

**Ejemplo de plugin de balanced allocation personalizado:**
```go
// CustomBalancedAllocation implements custom balanced allocation logic.
type CustomBalancedAllocation struct {
    handle framework.Handle
    // Resource weights
    resourceWeights map[v1.ResourceName]int64
}

// Name returns the plugin name.
func (pl *CustomBalancedAllocation) Name() string {
    return "CustomBalancedAllocation"
}

// Score assigns a score to nodes.
func (pl *CustomBalancedAllocation) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    // Node's allocatable resources
    allocatable := nodeInfo.Node().Status.Allocatable

    // Resources already requested on node
    requested := nodeInfo.RequestedResource()

    // Pod's resource request
    podRequest := calculatePodResourceRequest(pod)

    // Calculate resource utilization
    fractions := make(map[v1.ResourceName]float64)
    for resource, weight := range pl.resourceWeights {
        if weight == 0 {
            continue
        }

        allocatableValue := allocatable[resource]
        if allocatableValue.IsZero() {
            continue
        }

        requestedValue := requested.ResourceList[resource]
        podRequestValue := podRequest[resource]

        fraction := float64(requestedValue.Value()+podRequestValue.Value()) / float64(allocatableValue.Value())
        fractions[resource] = fraction
    }

    // Calculate difference between resource utilizations
    var variance float64
    for _, fraction := range fractions {
        for _, otherFraction := range fractions {
            diff := fraction - otherFraction
            if diff > 0 {
                variance += diff
            } else {
                variance -= diff
            }
        }
    }

    // Calculate score
    score := int64(100 - variance*100)
    if score < 0 {
        score = 0
    }

    return score, nil
}

// ScoreExtensions returns interface for score normalization.
func (pl *CustomBalancedAllocation) ScoreExtensions() framework.ScoreExtensions {
    return nil
}

// Calculate pod's resource request
func calculatePodResourceRequest(pod *v1.Pod) v1.ResourceList {
    result := v1.ResourceList{}
    for _, container := range pod.Spec.Containers {
        for resource, value := range container.Resources.Requests {
            if currentValue, ok := result[resource]; ok {
                currentValue.Add(value)
                result[resource] = currentValue
            } else {
                result[resource] = value.DeepCopy()
            }
        }
    }
    return result
}
```

**Problemas con las otras opciones:**
- B. Dar puntuaciones más altas a Nodes con menor uso de recursos: este es el rol del plugin "NodeResourcesLeastAllocated".
- C. Dar puntuaciones más altas a Nodes con mayor uso de recursos: este es el rol del plugin "NodeResourcesMostAllocated".
- D. Establecer límites de recursos en Nodes: este no es el rol de los plugins de scheduler; los límites de recursos de Node son propiedades de los propios Nodes.
</details>
### 7. ¿Cuál es el rol del punto de extensión "PreBind" en el scheduler de Kubernetes?

A. Vincular Pods a Nodes
B. Realizar operaciones necesarias antes del binding
C. Realizar limpieza después del binding
D. Realizar operaciones de recuperación cuando falla el binding

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Realizar operaciones necesarias antes del binding**

**Explicación:**
El rol del punto de extensión "PreBind" en el framework de scheduling de Kubernetes es realizar operaciones necesarias antes de vincular un Pod a un Node. Por ejemplo, pueden realizarse operaciones como aprovisionamiento de volúmenes, configuración de red y reserva de recursos.

**Funciones clave del punto de extensión PreBind:**
1. **Aprovisionamiento de volúmenes**: Crea y prepara los volúmenes necesarios.
2. **Configuración de red**: Configura los recursos de red necesarios.
3. **Reserva de recursos**: Reserva los recursos necesarios.
4. **Prevalidación**: Verificación final de que el binding es posible.

**Interfaz del plugin PreBind:**
```go
type PreBindPlugin interface {
    Plugin
    // PreBind is called before binding a pod to a node.
    PreBind(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) *Status
}
```

**Plugins PreBind predeterminados:**
Kubernetes proporciona los siguientes plugins PreBind predeterminados:

1. **VolumeBinding**: Realiza operaciones de binding de volúmenes.
2. **DefaultPreBind**: Realiza operaciones básicas previas al binding.

**Ejemplo de plugin PreBind personalizado:**
```go
// CustomPreBind implements custom pre-binding logic.
type CustomPreBind struct {
    handle framework.Handle
}

// Name returns the plugin name.
func (pl *CustomPreBind) Name() string {
    return "CustomPreBind"
}

// PreBind is called before binding a pod to a node.
func (pl *CustomPreBind) PreBind(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) *framework.Status {
    // 1. Volume provisioning
    if err := pl.provisionVolumes(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    // 2. Network resource setup
    if err := pl.setupNetworking(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    // 3. Resource reservation
    if err := pl.reserveResources(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    // 4. Final validation
    if err := pl.validateBinding(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    return nil
}

// Volume provisioning
func (pl *CustomPreBind) provisionVolumes(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Identify necessary volumes
    for _, volume := range pod.Spec.Volumes {
        if volume.PersistentVolumeClaim != nil {
            // Check PVC status
            pvc, err := pl.handle.ClientSet().CoreV1().PersistentVolumeClaims(pod.Namespace).Get(ctx, volume.PersistentVolumeClaim.ClaimName, metav1.GetOptions{})
            if err != nil {
                return err
            }

            // If PVC is not bound
            if pvc.Status.Phase != v1.ClaimBound {
                return fmt.Errorf("PVC %s is not bound", pvc.Name)
            }
        }
    }
    return nil
}

// Network resource setup
func (pl *CustomPreBind) setupNetworking(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Example: Network policy setup
    if err := pl.setupNetworkPolicies(ctx, pod, nodeName); err != nil {
        return err
    }

    // Example: Service endpoint setup
    if err := pl.setupServiceEndpoints(ctx, pod, nodeName); err != nil {
        return err
    }

    return nil
}

// Resource reservation
func (pl *CustomPreBind) reserveResources(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Example: GPU resource reservation
    if err := pl.reserveGPUs(ctx, pod, nodeName); err != nil {
        return err
    }

    // Example: Special hardware resource reservation
    if err := pl.reserveSpecialHardware(ctx, pod, nodeName); err != nil {
        return err
    }

    return nil
}

// Binding validation
func (pl *CustomPreBind) validateBinding(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Example: Re-verify node status
    node, err := pl.handle.ClientSet().CoreV1().Nodes().Get(ctx, nodeName, metav1.GetOptions{})
    if err != nil {
        return err
    }

    // Example: Check node resource availability
    if !hasEnoughResources(node, pod) {
        return fmt.Errorf("node %s does not have enough resources", nodeName)
    }

    return nil
}
```

**Habilitación del plugin PreBind en la configuración del scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    preBind:
      enabled:
      - name: CustomPreBind
      disabled:
      - name: VolumeBinding  # Disable default plugin
```

**Casos de uso de PreBind:**
1. **Aprovisionamiento de volúmenes**:
   - Creación y binding de PersistentVolume
   - Preparación de volúmenes efímeros
   - Validación de parámetros de StorageClass

2. **Configuración de red**:
   - Aplicación de NetworkPolicy
   - Configuración de endpoints de Service
   - Configuración de load balancer

3. **Reserva de recursos**:
   - Reserva de recursos GPU
   - Reserva de recursos FPGA
   - Reserva de recursos de hardware especial

4. **Configuración de seguridad**:
   - Aplicación de políticas de seguridad
   - Aprovisionamiento de certificados
   - Preparación de montaje de Secrets

**Manejo de fallos de PreBind:**
Cuando un plugin PreBind devuelve un fallo:
1. El ciclo de scheduling se aborta.
2. El Pod vuelve a la cola de scheduling.
3. Los recursos reservados se liberan.
4. Se registran eventos de fallo.

**Monitoreo de logs y eventos de PreBind:**
```bash
# Check PreBind-related messages in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i prebind

# Check pod events
kubectl describe pod <pod-name> | grep -i prebind
```

**Problemas con las otras opciones:**
- A. Vincular Pods a Nodes: este es el rol del punto de extensión "Bind".
- C. Realizar limpieza después del binding: este es el rol del punto de extensión "PostBind".
- D. Realizar operaciones de recuperación cuando falla el binding: este no es un punto de extensión en el framework del scheduler.
</details>

### 8. ¿Cuál es el propósito principal del plugin "NodeResourcesFit" en el scheduler de Kubernetes?

A. Monitorear el uso de recursos del Node
B. Establecer límites de recursos del Node
C. Comparar la capacidad de recursos del Node con las solicitudes de recursos del Pod
D. Mantener el balance de uso de recursos del Node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Comparar la capacidad de recursos del Node con las solicitudes de recursos del Pod**

**Explicación:**
El propósito principal del plugin "NodeResourcesFit" en el scheduler de Kubernetes es comparar la capacidad de recursos del Node con las solicitudes de recursos del Pod para verificar si los Pods pueden ejecutarse en los Nodes. Este plugin considera varios tipos de recursos, incluidos CPU, memoria, almacenamiento efímero y recursos extendidos (como GPUs).

**Funciones clave del plugin NodeResourcesFit:**
1. **Validación de solicitudes de recursos**: Verifica que las solicitudes de recursos del Pod no excedan los recursos asignables del Node.
2. **Validación de límites de recursos**: Verifica que los límites de recursos del Pod no excedan la capacidad del Node.
3. **Validación de recursos extendidos**: Verifica que las solicitudes de recursos extendidos como GPUs y FPGAs estén disponibles en los Nodes.

**Configuración del plugin NodeResourcesFit:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    filter:
      enabled:
      - name: NodeResourcesFit
    score:
      enabled:
      - name: NodeResourcesFit
        weight: 1
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: LeastAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**Estrategias de scoring:**
El plugin NodeResourcesFit admite las siguientes estrategias de scoring:

1. **LeastAllocated**: Da puntuaciones más altas a Nodes con menos recursos en uso.
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: Da puntuaciones más altas a Nodes con más recursos en uso.
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: Usa funciones personalizadas para asignar puntuaciones según la proporción de recursos solicitados respecto a la capacidad.

**Ejemplo de plugin NodeResourcesFit personalizado:**
```go
// CustomNodeResourcesFit implements custom resource fit logic.
type CustomNodeResourcesFit struct {
    handle framework.Handle
    // Resource weights
    resourceWeights map[v1.ResourceName]int64
}

// Name returns the plugin name.
func (pl *CustomNodeResourcesFit) Name() string {
    return "CustomNodeResourcesFit"
}

// Filter checks node resource fitness.
func (pl *CustomNodeResourcesFit) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // Node's allocatable resources
    allocatable := nodeInfo.Node().Status.Allocatable

    // Resources already requested on node
    requested := nodeInfo.RequestedResource()

    // Pod's resource request
    podRequest := calculatePodResourceRequest(pod)

    // Check each resource type
    for resourceName := range pl.resourceWeights {
        allocatableValue := allocatable[resourceName]
        if allocatableValue.IsZero() {
            return framework.NewStatus(framework.Unschedulable, fmt.Sprintf("node does not have resource %s", resourceName))
        }

        requestedValue := requested.ResourceList[resourceName]
        podRequestValue := podRequest[resourceName]

        if requestedValue.Value()+podRequestValue.Value() > allocatableValue.Value() {
            return framework.NewStatus(framework.Unschedulable, fmt.Sprintf("insufficient %s", resourceName))
        }
    }

    return nil
}

// Score assigns scores to nodes.
func (pl *CustomNodeResourcesFit) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    // Node's allocatable resources
    allocatable := nodeInfo.Node().Status.Allocatable

    // Resources already requested on node
    requested := nodeInfo.RequestedResource()

    // Pod's resource request
    podRequest := calculatePodResourceRequest(pod)

    // Calculate score
    var score int64 = 0
    for resourceName, weight := range pl.resourceWeights {
        allocatableValue := allocatable[resourceName]
        if allocatableValue.IsZero() {
            continue
        }

        requestedValue := requested.ResourceList[resourceName]
        podRequestValue := podRequest[resourceName]

        // Use LeastAllocated strategy
        resourceScore := (float64(allocatableValue.Value()) - float64(requestedValue.Value()+podRequestValue.Value())) / float64(allocatableValue.Value())
        score += int64(resourceScore * float64(weight))
    }

    return score, nil
}

// ScoreExtensions returns interface for score normalization.
func (pl *CustomNodeResourcesFit) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore normalizes scores.
func (pl *CustomNodeResourcesFit) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }

    if highest == 0 {
        return nil
    }

    for i := range scores {
        scores[i].Score = scores[i].Score * framework.MaxNodeScore / highest
    }

    return nil
}
```

**Ejemplo de solicitud y límite de recursos:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "512Mi"
```

**Problemas con las otras opciones:**
- A. Monitorear el uso de recursos del Node: este es el rol de metrics servers o sistemas de monitoreo.
- B. Establecer límites de recursos del Node: este es el rol de la configuración del Node o kubelet.
- D. Mantener el balance de uso de recursos del Node: este es el rol del plugin "NodeResourcesBalancedAllocation".
</details>
### 9. ¿Cuál es el propósito principal del plugin "InterPodAffinity" en el scheduler de Kubernetes?

A. Procesar reglas de affinity entre Pods y Nodes
B. Procesar reglas de affinity y anti-affinity entre Pods
C. Procesar reglas de affinity entre Pods y volúmenes
D. Procesar reglas de affinity entre Pods y Services

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Procesar reglas de affinity y anti-affinity entre Pods**

**Explicación:**
El propósito principal del plugin "InterPodAffinity" en el scheduler de Kubernetes es procesar reglas de affinity y anti-affinity entre Pods. Este plugin controla si los Pods se colocan en el mismo dominio topológico (Node, zona, región, etc.) que otros Pods (affinity) o en dominios diferentes (anti-affinity).

**Funciones clave del plugin InterPodAffinity:**
1. **Procesamiento de reglas de Pod affinity**: Asegura que los Pods se coloquen en el mismo dominio topológico que otros Pods con etiquetas específicas.
2. **Procesamiento de reglas de Pod anti-affinity**: Asegura que los Pods se coloquen en dominios topológicos diferentes de otros Pods con etiquetas específicas.
3. **Consideración del dominio topológico**: Considera varios niveles de dominios topológicos, incluidos Nodes, zonas y regiones.

**Tipos de Pod affinity y anti-affinity:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Reglas que deben cumplirse para que los Pods se programen (requisito estricto).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Reglas que son preferidas, pero no obligatorias (requisito flexible).

**Ejemplo de Pod affinity y anti-affinity:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - web
          topologyKey: kubernetes.io/hostname
  containers:
  - name: nginx
    image: nginx
```

**Configuración del plugin InterPodAffinity:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    preFilter:
      enabled:
      - name: InterPodAffinity
    filter:
      enabled:
      - name: InterPodAffinity
    score:
      enabled:
      - name: InterPodAffinity
        weight: 2  # Set weight
  pluginConfig:
  - name: InterPodAffinity
    args:
      hardPodAffinityWeight: 1  # Hard pod affinity weight
```

**Ejemplo de plugin InterPodAffinity personalizado:**
```go
// CustomInterPodAffinity implements custom inter-pod affinity logic.
type CustomInterPodAffinity struct {
    handle framework.Handle
    // Hard pod affinity weight
    hardPodAffinityWeight int64
}

// Name returns the plugin name.
func (pl *CustomInterPodAffinity) Name() string {
    return "CustomInterPodAffinity"
}

// PreFilter initializes inter-pod affinity information.
func (pl *CustomInterPodAffinity) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    // Initialize pod affinity information
    if pod.Spec.Affinity == nil || (pod.Spec.Affinity.PodAffinity == nil && pod.Spec.Affinity.PodAntiAffinity == nil) {
        return nil
    }

    // Store pod affinity information
    affinity := pod.Spec.Affinity
    state.Write(framework.StateKey("CustomInterPodAffinity"), affinity)

    return nil
}

// PreFilterExtensions returns interface providing additional features.
func (pl *CustomInterPodAffinity) PreFilterExtensions() framework.PreFilterExtensions {
    return nil
}

// Filter checks inter-pod affinity rules.
func (pl *CustomInterPodAffinity) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // Get pod affinity information
    obj, err := state.Read(framework.StateKey("CustomInterPodAffinity"))
    if err != nil {
        return nil
    }

    affinity, ok := obj.(*v1.Affinity)
    if !ok || affinity == nil {
        return nil
    }

    // Check required pod affinity rules
    if affinity.PodAffinity != nil {
        for _, term := range affinity.PodAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
            if !satisfiesPodAffinityTerm(pod, term, nodeInfo, pl.handle) {
                return framework.NewStatus(framework.Unschedulable, "node does not satisfy pod affinity rules")
            }
        }
    }

    // Check required pod anti-affinity rules
    if affinity.PodAntiAffinity != nil {
        for _, term := range affinity.PodAntiAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
            if satisfiesPodAffinityTerm(pod, term, nodeInfo, pl.handle) {
                return framework.NewStatus(framework.Unschedulable, "node does not satisfy pod anti-affinity rules")
            }
        }
    }

    return nil
}

// Score assigns scores to nodes.
func (pl *CustomInterPodAffinity) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // Get pod affinity information
    obj, err := state.Read(framework.StateKey("CustomInterPodAffinity"))
    if err != nil {
        return 0, nil
    }

    affinity, ok := obj.(*v1.Affinity)
    if !ok || affinity == nil {
        return 0, nil
    }

    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    var score int64 = 0

    // Calculate preferred pod affinity score
    if affinity.PodAffinity != nil {
        for _, term := range affinity.PodAffinity.PreferredDuringSchedulingIgnoredDuringExecution {
            if satisfiesPodAffinityTerm(pod, term.PodAffinityTerm, nodeInfo, pl.handle) {
                score += term.Weight
            }
        }
    }

    // Calculate preferred pod anti-affinity score
    if affinity.PodAntiAffinity != nil {
        for _, term := range affinity.PodAntiAffinity.PreferredDuringSchedulingIgnoredDuringExecution {
            if !satisfiesPodAffinityTerm(pod, term.PodAffinityTerm, nodeInfo, pl.handle) {
                score += term.Weight
            }
        }
    }

    return score, nil
}

// ScoreExtensions returns interface for score normalization.
func (pl *CustomInterPodAffinity) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore normalizes scores.
func (pl *CustomInterPodAffinity) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }

    if highest == 0 {
        return nil
    }

    for i := range scores {
        scores[i].Score = scores[i].Score * framework.MaxNodeScore / highest
    }

    return nil
}

// Check if pod affinity term is satisfied
func satisfiesPodAffinityTerm(pod *v1.Pod, term v1.PodAffinityTerm, nodeInfo *framework.NodeInfo, handle framework.Handle) bool {
    // Implementation omitted
    return true
}
```

**Casos de uso de Pod affinity y anti-affinity:**
1. **Alta disponibilidad**: Distribuir instancias de la misma aplicación entre diferentes Nodes, zonas o regiones
2. **Optimización de rendimiento**: Colocar Pods que se comunican entre sí en el mismo Node para minimizar la latencia
3. **Aislamiento de recursos**: Distribuir Pods con uso intensivo de recursos entre diferentes Nodes
4. **Restricciones de licencia**: Concentrar aplicaciones con restricciones de licencia en Nodes específicos

**Impacto en el rendimiento de Pod affinity y anti-affinity:**
Pod affinity y anti-affinity pueden ser computacionalmente costosas, ya que necesitan considerar todos los Nodes y Pods. En clústeres grandes, esto puede impactar el rendimiento del scheduling, por lo que deben usarse con precaución.

**Problemas con las otras opciones:**
- A. Procesar reglas de affinity entre Pods y Nodes: este es el rol del plugin "NodeAffinity".
- C. Procesar reglas de affinity entre Pods y volúmenes: este es el rol del plugin "VolumeBinding".
- D. Procesar reglas de affinity entre Pods y Services: este no es un plugin del scheduler de Kubernetes.
</details>

### 10. ¿Cuál es el propósito principal del plugin "NodeName" en el scheduler de Kubernetes?

A. Verificar que el campo spec.nodeName del Pod coincida con el nombre del Node
B. Asignar nombres a Nodes
C. Asignar nombres de Node a Pods
D. Validar el formato del nombre de Node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Verificar que el campo spec.nodeName del Pod coincida con el nombre del Node**

**Explicación:**
El propósito principal del plugin "NodeName" en el scheduler de Kubernetes es verificar que el campo `spec.nodeName` del Pod coincida con el nombre del Node. Este plugin comprueba si un Pod ha sido asignado directamente a un Node específico y solo permite pasar por la fase de filtering a los Nodes con nombres coincidentes.

**Funciones clave del plugin NodeName:**
1. **Verificación del nombre del Node**: Si el campo `spec.nodeName` del Pod está configurado, solo se seleccionan Nodes con nombres coincidentes.
2. **Soporte de scheduling directo**: Permite a los usuarios asignar Pods directamente a Nodes específicos.
3. **Omisión del scheduler**: Los Pods con `spec.nodeName` configurado omiten la lógica normal de scheduling y se asignan directamente al Node especificado.

**Implementación del plugin NodeName:**
```go
// NodeName plugin implementation example
type NodeName struct{}

// Name returns the plugin name.
func (pl *NodeName) Name() string {
    return "NodeName"
}

// Filter verifies that the pod's spec.nodeName field matches the node name.
func (pl *NodeName) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    if pod.Spec.NodeName == "" {
        return nil
    }

    if pod.Spec.NodeName != nodeInfo.Node().Name {
        return framework.NewStatus(framework.UnschedulableAndUnresolvable, "node name does not match")
    }

    return nil
}
```

**Ejemplo de Pod con especificación nodeName:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  nodeName: worker-node-1  # Direct assignment to specific node
  containers:
  - name: nginx
    image: nginx
```

**Consideraciones al usar nodeName:**
1. **Omisión del scheduler**: Usar `nodeName` omite el filtering, scoring y otra lógica del scheduler.
2. **Comprobación de existencia del Node**: Si el Node especificado no existe, el Pod permanece en estado `Pending`.
3. **Sin comprobación de recursos**: La disponibilidad de recursos del Node no se comprueba, lo que puede provocar fallos por escasez de recursos.
4. **Ignorar restricciones**: Se ignoran taints, affinity y otras restricciones.

**nodeName vs nodeSelector vs nodeAffinity:**
1. **nodeName**: Asigna directamente a un Node específico. Es la opción más restrictiva y menos flexible.
2. **nodeSelector**: Selecciona Nodes según etiquetas. Simple, pero con expresividad limitada.
3. **nodeAffinity**: Admite reglas complejas de selección de Nodes. Es la opción más flexible y expresiva.

**Casos de uso de nodeName:**
1. **Debugging**: Ejecutar Pods en Nodes específicos para depurar problemas.
2. **Pruebas**: Ejecutar pruebas en Nodes específicos.
3. **Hardware especial**: Asignar Pods a Nodes con hardware específico.
4. **Static Pods**: Usado para Static Pods administrados directamente por kubelet.

**Precauciones al usar nodeName:**
1. **Sin recuperación automática**: Si un Node falla, los Pods no se mueven automáticamente a otros Nodes.
2. **Escalabilidad limitada**: Los nombres de Node están codificados de forma fija, lo que limita la escalabilidad.
3. **Dificultad de mantenimiento**: Las definiciones de Pod necesitan actualizaciones si cambian los nombres de Node.
4. **Sin balanceo de carga**: No se pueden aprovechar las funciones de balanceo de carga del scheduler.

**Alternativas y recomendaciones:**
1. **Usar nodeSelector**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: nginx
   spec:
     nodeSelector:
       kubernetes.io/hostname: worker-node-1
     containers:
     - name: nginx
       image: nginx
   ```

2. **Usar nodeAffinity**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: nginx
   spec:
     affinity:
       nodeAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
           nodeSelectorTerms:
           - matchExpressions:
             - key: kubernetes.io/hostname
               operator: In
               values:
               - worker-node-1
     containers:
     - name: nginx
       image: nginx
   ```

**Problemas con las otras opciones:**
- B. Asignar nombres a Nodes: Los nombres de Node se asignan en la creación del Node y no son el rol de los plugins del scheduler.
- C. Asignar nombres de Node a Pods: Esto se realiza en la fase de binding del scheduler, no por el plugin NodeName.
- D. Validar el formato del nombre de Node: Esto lo realiza la lógica de validación del API server, no los plugins del scheduler.
</details>
