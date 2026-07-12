# Cuestionario de Custom Scheduler (Parte 2)

Este cuestionario evalúa tu comprensión avanzada de la implementación y el uso de Custom Schedulers en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Cuál es el rol del punto de extensión "Bind" en el framework de scheduling de Kubernetes?

A. Vincular Pods a Nodes para finalizar las decisiones de scheduling
B. Configurar la vinculación de red entre Pods y Nodes
C. Crear una vinculación entre Pods y Services
D. Configurar la vinculación entre Pods y volúmenes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Vincular Pods a Nodes para finalizar las decisiones de scheduling**

**Explicación:**
El rol del punto de extensión "Bind" en el framework de scheduling de Kubernetes es vincular Pods a los Nodes seleccionados para finalizar las decisiones de scheduling. La etapa de binding es la etapa final del ciclo de scheduling, donde se establece el campo `spec.nodeName` del Pod para que kubelet pueda ejecutar el Pod.

**Proceso de Binding:**
1. El scheduler selecciona el Node óptimo mediante filtering y scoring.
2. Reserva el Pod en el Node seleccionado (reserve).
3. En la etapa de binding, actualiza el campo `spec.nodeName` del Pod con el nombre del Node seleccionado.
4. La información actualizada del Pod se almacena en el API server.
5. kubelet detecta la información del Pod y ejecuta el Pod en ese Node.

**Ejemplo de implementación de Bind Plugin:**
```go
// Bind plugin example
type MyBindPlugin struct {
    handle framework.Handle
}

func (bp *MyBindPlugin) Name() string {
    return "MyBindPlugin"
}

// Bind method implementation
func (bp *MyBindPlugin) Bind(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) *framework.Status {
    // Create pod binding object
    binding := &v1.Binding{
        ObjectMeta: metav1.ObjectMeta{
            Name:      pod.Name,
            Namespace: pod.Namespace,
        },
        Target: v1.ObjectReference{
            Kind:       "Node",
            Name:       nodeName,
            APIVersion: "v1",
        },
    }

    // Send binding request to API server
    err := bp.handle.ClientSet().CoreV1().Pods(pod.Namespace).Bind(ctx, binding, metav1.CreateOptions{})
    if err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    return nil
}
```

**Habilitación de Bind Plugin en la configuración del Scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    bind:
      enabled:
      - name: MyBindPlugin
      disabled:
      - name: DefaultBinder  # Disable default binder
```

**Comprobación de eventos relacionados con Binding:**
```bash
# Check pod scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**Solución de problemas de fallos de Binding:**
Causas comunes de fallo en la etapa de binding:
1. Problemas de conexión con el API server
2. Permisos insuficientes
3. Errores en el nombre del Node
4. Condiciones de carrera (otro scheduler intenta vincular el mismo Pod simultáneamente)

**Problemas con las otras opciones:**
- B. Configurar la vinculación de red entre Pods y Nodes: La configuración de red es el rol de los CNI plugins y no está relacionada con la etapa de bind del scheduler.
- C. Crear una vinculación entre Pods y Services: La conexión entre Services y Pods se realiza mediante label selectors y no está relacionada con la etapa de bind del scheduler.
- D. Configurar la vinculación entre Pods y volúmenes: El volume binding lo gestiona el PersistentVolumeClaim controller y es un proceso separado de la etapa de bind del scheduler.
</details>

### 2. ¿Cuál de los siguientes NO es un operador relacionado con Node Affinity en Kubernetes?

A. In
B. NotIn
C. Exists
D. Contains

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Contains**

**Explicación:**
El operador no relacionado con Node Affinity en Kubernetes es `Contains`. Kubernetes no proporciona un operador `Contains` para node affinity.

**Operadores admitidos en Node Affinity:**
1. **In**: El valor de la label debe coincidir con uno de los valores especificados.
2. **NotIn**: El valor de la label no debe coincidir con los valores especificados.
3. **Exists**: La clave de la label especificada debe existir.
4. **DoesNotExist**: La clave de la label especificada no debe existir.
5. **Gt**: El valor de la label debe ser mayor que el valor especificado (Greater than).
6. **Lt**: El valor de la label debe ser menor que el valor especificado (Less than).

**Ejemplo de Node Affinity:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: with-node-affinity
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/e2e-az-name
            operator: In
            values:
            - e2e-az1
            - e2e-az2
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: Exists
```

**Tipos de Node Affinity:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Reglas que deben cumplirse para que el Pod se programe en un Node (requisito estricto).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Reglas que se prefiere que se cumplan, pero no son obligatorias (requisito flexible).

**Ejemplos de uso de operadores:**
1. **Operador In**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: In
     values:
     - e2e-az1
     - e2e-az2
   ```
   El valor de la label `kubernetes.io/e2e-az-name` del Node debe ser `e2e-az1` o `e2e-az2`.

2. **Operador NotIn**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: NotIn
     values:
     - e2e-az3
   ```
   El valor de la label `kubernetes.io/e2e-az-name` del Node no debe ser `e2e-az3`.

3. **Operador Exists**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: Exists
   ```
   La label `kubernetes.io/e2e-az-name` debe existir en el Node.

4. **Operador DoesNotExist**:
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   La label `emptyLabel` no debe existir en el Node.

5. **Operadores Gt/Lt**:
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   El valor de la label `node-size` del Node debe ser mayor que 10.

**Manejo de Node Affinity en un Custom Scheduler:**
Al implementar un custom scheduler, debes considerar los requisitos de node affinity del Pod.

```go
// Node affinity check example
func checkNodeAffinity(pod *v1.Pod, node *v1.Node) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.NodeAffinity == nil {
        return true  // All nodes are suitable if there's no node affinity
    }

    // Check required node affinity
    if required := affinity.NodeAffinity.RequiredDuringSchedulingIgnoredDuringExecution; required != nil {
        for _, term := range required.NodeSelectorTerms {
            if matchNodeSelectorTerm(term, node) {
                return true
            }
        }
        return false  // No NodeSelectorTerm matched
    }

    return true
}

// Check if NodeSelectorTerm matches
func matchNodeSelectorTerm(term v1.NodeSelectorTerm, node *v1.Node) bool {
    // Implementation omitted
    return true
}
```

**Explicación de las otras opciones:**
- A. In: Un operador de node affinity válido.
- B. NotIn: Un operador de node affinity válido.
- C. Exists: Un operador de node affinity válido.
</details>

### 3. ¿Cuál es el propósito principal de Pod Topology Spread Constraints en Kubernetes?

A. Distribuir Pods de manera uniforme entre varios Nodes
B. Colocar Pods solo en Nodes específicos
C. Colocar Pods solo en zonas específicas
D. Colocar Pods solo en Nodes con labels específicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Distribuir Pods de manera uniforme entre varios Nodes**

**Explicación:**
El propósito principal de Pod Topology Spread Constraints en Kubernetes es distribuir Pods de manera uniforme entre varios dominios de topología (Nodes, zonas, regiones, etc.). Esto mejora la alta disponibilidad de la aplicación, optimiza el uso de recursos y mejora la tolerancia a fallos.

**Componentes principales de Pod Topology Spread Constraints:**
1. **maxSkew**: Especifica la diferencia máxima en el recuento de Pods entre dominios de topología.
2. **topologyKey**: Clave de label del Node que define el dominio de topología entre el cual distribuir Pods.
3. **whenUnsatisfiable**: Especifica el comportamiento cuando la restricción no se puede satisfacer.
   - `DoNotSchedule`: No programar el Pod si la restricción no se cumple.
   - `ScheduleAnyway`: Programar el Pod aunque la restricción no se cumpla.
4. **labelSelector**: Label selector para seleccionar los Pods existentes que se deben considerar en el cálculo de distribución.

**Ejemplo de Pod Topology Spread Constraints:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web
  - maxSkew: 2
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web
  containers:
  - name: nginx
    image: nginx
```

En este ejemplo, se definen dos restricciones:
1. La diferencia en el recuento de Pods con la label `app=web` entre cada Node (`kubernetes.io/hostname`) debe ser como máximo 1.
2. La diferencia en el recuento de Pods con la label `app=web` entre cada zona (`topology.kubernetes.io/zone`) debe ser como máximo 2.

**Método de cálculo de Topology Spread:**
1. Calcular el número de Pods que coinciden con el label selector en cada dominio de topología.
2. Calcular la diferencia entre el dominio con más Pods y el dominio con menos Pods.
3. Si esta diferencia es mayor que `maxSkew`, se infringe la restricción.

**Topology Keys comunes:**
1. **kubernetes.io/hostname**: Distribución a nivel de Node
2. **topology.kubernetes.io/zone**: Distribución a nivel de zona
3. **topology.kubernetes.io/region**: Distribución a nivel de región
4. **node.kubernetes.io/instance-type**: Distribución a nivel de tipo de instancia

**Casos de uso:**
1. **Alta disponibilidad**: Mejorar la tolerancia a fallos distribuyendo Pods entre múltiples Nodes, zonas y regiones
2. **Balance de recursos**: Distribuir workloads de manera uniforme en el cluster
3. **Optimización de costos**: Distribuir workloads entre tipos específicos de Nodes
4. **Optimización de rendimiento**: Distribuir para minimizar la latencia de red

**Manejo de Topology Spread en un Custom Scheduler:**
Al implementar un custom scheduler, debes considerar las restricciones de topology spread del Pod.

```go
// Topology spread constraint check example
func checkTopologySpreadConstraints(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    constraints := pod.Spec.TopologySpreadConstraints
    if len(constraints) == 0 {
        return true  // All nodes are suitable if there are no constraints
    }

    for _, constraint := range constraints {
        // Get topology key value
        topologyValue, ok := node.Labels[constraint.TopologyKey]
        if !ok {
            // Skip this constraint if the node doesn't have the topology key
            if constraint.WhenUnsatisfiable == v1.DoNotSchedule {
                return false
            }
            continue
        }

        // Calculate the number of matching pods in the current topology domain
        var matchingPods int
        for _, existingPod := range allPods {
            // Check if the pod matches the label selector and is in the same topology domain
            if podMatchesLabelSelector(existingPod, constraint.LabelSelector) {
                podNode, err := getNodeForPod(existingPod)
                if err != nil {
                    continue
                }
                if podNode.Labels[constraint.TopologyKey] == topologyValue {
                    matchingPods++
                }
            }
        }

        // Calculate pod count in other topology domains and check skew
        // (Implementation omitted)

        // Check maxSkew violation
        if skew > constraint.MaxSkew && constraint.WhenUnsatisfiable == v1.DoNotSchedule {
            return false
        }
    }

    return true
}
```

**Problemas con las otras opciones:**
- B. Colocar Pods solo en Nodes específicos: Este es el rol de nodeSelector o nodeAffinity.
- C. Colocar Pods solo en zonas específicas: Esto consiste en colocar Pods en zonas específicas usando node affinity; el propósito principal de topology spread constraints es la distribución uniforme.
- D. Colocar Pods solo en Nodes con labels específicas: Este es el rol de nodeSelector o nodeAffinity.
</details>
### 4. ¿Cuál es el propósito principal de Taints and Tolerations en Kubernetes?

A. Garantizar que Pods específicos se programen solo en Nodes específicos
B. Evitar que Pods específicos se programen en Nodes específicos
C. Permitir que los Nodes rechacen ciertos Pods y que los Pods lo toleren
D. Restringir la comunicación entre Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir que los Nodes rechacen ciertos Pods y que los Pods lo toleren**

**Explicación:**
El propósito principal de Taints and Tolerations en Kubernetes es permitir que los Nodes rechacen ciertos Pods y que los Pods lo toleren. Los taints se aplican a los Nodes para impedir que se programen Pods, y las tolerations se aplican a los Pods para permitir el scheduling en Nodes con ciertos taints.

**Cómo funcionan Taints and Tolerations:**
1. **Taints**: Se aplican a los Nodes para restringir el scheduling de Pods en ese Node.
2. **Tolerations**: Se aplican a los Pods para permitir el scheduling en Nodes con ciertos taints.
3. **Effect**: El efecto de un taint define el comportamiento para Pods sin tolerations.

**Tipos de efecto de Taint:**
1. **NoSchedule**: Los Pods sin tolerations no se programan en el Node.
2. **PreferNoSchedule**: Preferentemente, los Pods sin tolerations no se programan en el Node, pero pueden programarse si los recursos del cluster son insuficientes.
3. **NoExecute**: Los Pods sin tolerations no se programan en el Node, y los Pods que ya se están ejecutando se eliminan.

**Ejemplo de aplicación de Taint:**
```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Remove taint from node
kubectl taint nodes node1 key=value:NoSchedule-
```

**Ejemplo de Taint y Toleration:**
```yaml
# Apply taint to node
apiVersion: v1
kind: Node
metadata:
  name: node1
spec:
  taints:
  - key: "key"
    value: "value"
    effect: "NoSchedule"

# Apply toleration to pod
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-toleration
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
  containers:
  - name: nginx
    image: nginx
```

**Operadores de Toleration:**
1. **Equal**: La clave y el valor deben coincidir.
2. **Exists**: Solo la clave debe coincidir (el valor se ignora).

**Campo adicional de Toleration:**
- **tolerationSeconds**: Especifica el tiempo (en segundos) que un Pod puede permanecer en un Node antes de ser eliminado con el efecto NoExecute.

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**Casos de uso comunes:**
1. **Nodes dedicados**: Reservar Nodes solo para workloads específicos
2. **Hardware especial**: Programar Pods específicos solo en Nodes con hardware especial como GPUs
3. **Mantenimiento de Node**: Evitar el scheduling de nuevos Pods durante el mantenimiento del Node
4. **Protección del master Node**: Evitar que workloads generales se programen en Nodes del control plane

**Taints del sistema:**
Kubernetes aplica automáticamente los siguientes taints del sistema:
1. **node.kubernetes.io/not-ready**: El Node no está listo
2. **node.kubernetes.io/unreachable**: El Node no es alcanzable
3. **node.kubernetes.io/memory-pressure**: El Node tiene presión de memoria
4. **node.kubernetes.io/disk-pressure**: El Node tiene presión de disco
5. **node.kubernetes.io/pid-pressure**: El Node tiene presión de PID
6. **node.kubernetes.io/network-unavailable**: La red del Node no está disponible
7. **node.kubernetes.io/unschedulable**: El Node está marcado como no programable

**Manejo de Taints and Tolerations en un Custom Scheduler:**
Al implementar un custom scheduler, debes considerar los taints de Node y las tolerations de Pod.

```go
// Taint and toleration check example
func checkTaintsAndTolerations(pod *v1.Pod, node *v1.Node) bool {
    // All pods can be scheduled if the node has no taints
    if len(node.Spec.Taints) == 0 {
        return true
    }

    // Check if the pod has tolerations for each taint
    for _, taint := range node.Spec.Taints {
        if taint.Effect == v1.TaintEffectNoSchedule || taint.Effect == v1.TaintEffectPreferNoSchedule {
            // Check if the pod tolerates this taint
            if !tolerationsTolerateTaint(pod.Spec.Tolerations, &taint) {
                return false
            }
        }
    }

    return true
}

// Check if tolerations tolerate a taint
func tolerationsTolerateTaint(tolerations []v1.Toleration, taint *v1.Taint) bool {
    for _, toleration := range tolerations {
        if toleration.Key == taint.Key {
            if toleration.Operator == v1.TolerationOpExists {
                return true
            } else if toleration.Operator == v1.TolerationOpEqual && toleration.Value == taint.Value {
                return true
            }
        }
    }
    return false
}
```

**Problemas con las otras opciones:**
- A. Garantizar que Pods específicos se programen solo en Nodes específicos: Este es el rol de nodeSelector o nodeAffinity.
- B. Evitar que Pods específicos se programen en Nodes específicos: Este es el rol de podAntiAffinity.
- D. Restringir la comunicación entre Pods: Este es el rol de NetworkPolicy.
</details>

### 5. ¿Cuál de las siguientes NO es una característica principal de Scheduler Extender en Kubernetes?

A. Se comunica con el scheduler mediante HTTP webhooks
B. Proporciona capacidades de filtering y prioritization
C. Está integrado directamente con el código base del scheduler
D. Se ejecuta como un proceso externo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Está integrado directamente con el código base del scheduler**

**Explicación:**
"Está integrado directamente con el código base del scheduler" NO es una característica principal de Scheduler Extender en Kubernetes. Los scheduler extenders no están integrados directamente con el código base del scheduler; se comunican mediante HTTP webhooks y se ejecutan como procesos externos. Esta es la principal diferencia con los scheduling framework plugins.

**Características principales de Scheduler Extender:**
1. **HTTP webhooks**: El scheduler se comunica con los extenders mediante solicitudes HTTP.
2. **Proceso externo**: Los extenders se ejecutan como procesos separados del scheduler.
3. **Filtering y prioritization**: Los extenders pueden proporcionar capacidades de filtering y prioritization de Nodes.
4. **Binding**: Los extenders pueden vincular Pods a Nodes opcionalmente.

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
    weight: 5
    bindVerb: "bind"
    enableHTTPS: false
    nodeCacheCapable: false
    ignorable: true
    managedResources:
    - name: example.com/foo
      ignoredByScheduler: true
```

**API de Scheduler Extender:**
1. **Filter API**: Recibe una lista de Nodes y devuelve una lista de Nodes filtrada.
   ```
   POST /filter
   ```
   Cuerpo de la solicitud:
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   Cuerpo de la respuesta:
   ```json
   {
     "nodes": <filtered-nodes>,
     "nodenames": <filtered-node-names>,
     "failedNodes": <failed-nodes>,
     "error": <error-message>
   }
   ```

2. **Prioritize API**: Recibe una lista de Nodes y asigna una puntuación a cada Node.
   ```
   POST /prioritize
   ```
   Cuerpo de la solicitud:
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   Cuerpo de la respuesta:
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

3. **Bind API**: Vincula el Pod al Node.
   ```
   POST /bind
   ```
   Cuerpo de la solicitud:
   ```json
   {
     "pod": <pod>,
     "node": <node-name>
   }
   ```
   Cuerpo de la respuesta:
   ```json
   {
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

func main() {
    http.HandleFunc("/filter", filterHandler)
    http.HandleFunc("/prioritize", prioritizeHandler)

    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**Scheduler Extender vs Scheduling Framework Plugin:**

| Feature | Scheduler Extender | Scheduling Framework Plugin |
|---------|-------------------|---------------------------|
| Integration Method | HTTP webhook | Direct codebase integration |
| Execution Mode | External process | Inside scheduler |
| Performance | Relatively slower due to HTTP overhead | Faster due to direct integration |
| Development Language | No restriction | Go |
| Deployment | Separate service | Deployed with scheduler |
| Maintenance | Independent from scheduler | Linked to scheduler version |

**Pros y contras de Scheduler Extender:**
Pros:
- Puede desarrollarse independientemente del código base del scheduler
- Puede implementarse en varios lenguajes de programación
- Se ve menos afectado por las actualizaciones del scheduler

Contras:
- Degradación del rendimiento debido al overhead de comunicación HTTP
- Solo puede extender algunas etapas del ciclo de scheduling
- Posibilidad de fallo de comunicación entre scheduler y extender

**Explicación de las otras opciones:**
- A. Se comunica con el scheduler mediante HTTP webhooks: Una característica válida de scheduler extender.
- B. Proporciona capacidades de filtering y prioritization: Una característica válida de scheduler extender.
- D. Se ejecuta como un proceso externo: Una característica válida de scheduler extender.
</details>
### 6. ¿Cuál es el propósito principal de Pod Affinity and Anti-Affinity en Kubernetes?

A. Definir relaciones entre Pods y Nodes
B. Definir relaciones entre Pods y volúmenes
C. Definir relaciones entre Pods
D. Definir relaciones entre Pods y Services

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Definir relaciones entre Pods**

**Explicación:**
El propósito principal de Pod Affinity and Anti-Affinity en Kubernetes es definir relaciones entre Pods. Esto permite controlar si Pods específicos se colocan en el mismo dominio de topología (Node, zona, región, etc.) que otros Pods (affinity) o no (anti-affinity).

**Componentes principales de Pod Affinity and Anti-Affinity:**
1. **topologyKey**: Clave de label del Node que especifica el dominio de topología que define relaciones entre Pods.
2. **labelSelector**: Label selector para seleccionar Pods con los que establecer relaciones.
3. **namespaces**: Lista de namespaces donde se aplica el label selector.

**Tipos de Pod Affinity:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Reglas que deben cumplirse para que el Pod se programe (requisito estricto).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Reglas que se prefiere que se cumplan, pero no son obligatorias (requisito flexible).

**Ejemplo de Pod Affinity:**
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

En este ejemplo:
1. **Pod Affinity**: El Pod del web server debe programarse en el mismo Node (`kubernetes.io/hostname`) que los Pods con la label `app=cache`.
2. **Pod Anti-Affinity**: Preferentemente, el Pod del web server debe programarse en un Node diferente al de otros Pods con la label `app=web`.

**Topology Keys comunes:**
1. **kubernetes.io/hostname**: Relación a nivel de Node
2. **topology.kubernetes.io/zone**: Relación a nivel de zona
3. **topology.kubernetes.io/region**: Relación a nivel de región

**Casos de uso:**
1. **Alta disponibilidad**: Distribuir instancias de la misma aplicación entre diferentes Nodes, zonas y regiones
2. **Optimización de rendimiento**: Colocar Pods que se comunican entre sí en el mismo Node para minimizar la latencia
3. **Aislamiento de recursos**: Distribuir Pods con uso intensivo de recursos entre diferentes Nodes
4. **Restricciones de licencia**: Concentrar aplicaciones con restricciones de licencia en Nodes específicos

**Pod Affinity vs Node Affinity:**
- **Node Affinity**: Define relaciones entre Pods y Nodes.
- **Pod Affinity**: Define relaciones entre Pods.

**Impacto en el rendimiento de Pod Affinity and Anti-Affinity:**
Pod affinity y anti-affinity pueden ser costosas computacionalmente, ya que necesitan considerar todos los Nodes y Pods. Especialmente en clusters grandes, pueden afectar el rendimiento del scheduling, por lo que deben usarse con cuidado.

**Manejo de Pod Affinity en un Custom Scheduler:**
Al implementar un custom scheduler, debes considerar los requisitos de affinity y anti-affinity del Pod.

```go
// Pod affinity check example
func checkPodAffinity(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.PodAffinity == nil {
        return true  // All nodes are suitable if there's no pod affinity
    }

    // Check required pod affinity
    for _, term := range affinity.PodAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
        if !satisfiesPodAffinityTerm(pod, node, term, allPods) {
            return false
        }
    }

    return true
}

// Pod anti-affinity check example
func checkPodAntiAffinity(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.PodAntiAffinity == nil {
        return true  // All nodes are suitable if there's no pod anti-affinity
    }

    // Check required pod anti-affinity
    for _, term := range affinity.PodAntiAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
        if satisfiesPodAffinityTerm(pod, node, term, allPods) {
            return false
        }
    }

    return true
}

// Check if pod affinity term is satisfied
func satisfiesPodAffinityTerm(pod *v1.Pod, node *v1.Node, term v1.PodAffinityTerm, allPods []*v1.Pod) bool {
    // Implementation omitted
    return true
}
```

**Problemas con las otras opciones:**
- A. Definir relaciones entre Pods y Nodes: Este es el rol de nodeAffinity.
- B. Definir relaciones entre Pods y volúmenes: Este es el rol de volume binding y PersistentVolumeClaim.
- D. Definir relaciones entre Pods y Services: Esto se maneja mediante service label selectors.
</details>

### 7. ¿Cuál es el rol del punto de extensión "QueueSort" en el scheduler de Kubernetes?

A. Puntuar Nodes
B. Excluir Nodes donde los Pods no pueden ejecutarse
C. Ordenar Pods en la cola de scheduling
D. Vincular Pods a Nodes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ordenar Pods en la cola de scheduling**

**Explicación:**
El rol del punto de extensión "QueueSort" en el framework de scheduling de Kubernetes es ordenar Pods en la cola de scheduling. Este punto de extensión establece la prioridad que determina qué Pods se programan primero.

**Cola de scheduling y QueueSort:**
El scheduler procesa los Pods en la cola de scheduling uno por uno. El QueueSort plugin determina el orden de los Pods en esta cola. De forma predeterminada, Kubernetes usa el plugin `PrioritySort` para ordenar por prioridad de Pod.

**Interfaz de QueueSort Plugin:**
```go
type QueueSortPlugin interface {
    Plugin
    // Less determines which of two pods should be scheduled first.
    // Returns true if pInfo1 should be scheduled before pInfo2.
    Less(*QueuedPodInfo, *QueuedPodInfo) bool
}
```

**QueueSort Plugin predeterminado - PrioritySort:**
```go
// PrioritySort sorts pods by pod priority.
type PrioritySort struct{}

// Name returns the plugin name.
func (pl *PrioritySort) Name() string {
    return Name
}

// Less determines which of two pods should be scheduled first.
func (pl *PrioritySort) Less(pInfo1, pInfo2 *framework.QueuedPodInfo) bool {
    p1 := getPodPriority(pInfo1.Pod)
    p2 := getPodPriority(pInfo2.Pod)

    // Higher priority pods are scheduled first.
    if p1 != p2 {
        return p1 > p2
    }

    // If priorities are equal, pods with longer wait time are scheduled first.
    return pInfo1.Timestamp.Before(pInfo2.Timestamp)
}
```

**Ejemplo de Custom QueueSort Plugin:**
```go
// CustomQueueSort implements custom sorting logic.
type CustomQueueSort struct{}

// Name returns the plugin name.
func (pl *CustomQueueSort) Name() string {
    return "CustomQueueSort"
}

// Less determines which of two pods should be scheduled first.
func (pl *CustomQueueSort) Less(pInfo1, pInfo2 *framework.QueuedPodInfo) bool {
    // Example: Prioritize pods in a specific namespace
    if pInfo1.Pod.Namespace == "high-priority-namespace" && pInfo2.Pod.Namespace != "high-priority-namespace" {
        return true
    }
    if pInfo1.Pod.Namespace != "high-priority-namespace" && pInfo2.Pod.Namespace == "high-priority-namespace" {
        return false
    }

    // Example: Prioritize pods with a specific label
    if hasLabel(pInfo1.Pod, "critical") && !hasLabel(pInfo2.Pod, "critical") {
        return true
    }
    if !hasLabel(pInfo1.Pod, "critical") && hasLabel(pInfo2.Pod, "critical") {
        return false
    }

    // By default, consider priority and wait time
    p1 := getPodPriority(pInfo1.Pod)
    p2 := getPodPriority(pInfo2.Pod)

    if p1 != p2 {
        return p1 > p2
    }

    return pInfo1.Timestamp.Before(pInfo2.Timestamp)
}

// Check if pod has a specific label
func hasLabel(pod *v1.Pod, label string) bool {
    _, exists := pod.Labels[label]
    return exists
}
```

**Habilitación de QueueSort Plugin en la configuración del Scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    queueSort:
      enabled:
      - name: CustomQueueSort
      disabled:
      - name: PrioritySort  # Disable default plugin
```

**Características de QueueSort Plugin:**
1. **Activación única**: Solo un QueueSort plugin puede estar activo a la vez.
2. **Impacto global**: El QueueSort plugin afecta a todos los Pods en la cola de scheduling.
3. **Importancia del rendimiento**: Un algoritmo de ordenamiento eficiente es importante; la lógica compleja puede afectar el rendimiento del scheduling.

**Casos de uso de QueueSort Plugin:**
1. **Prioridad de negocio**: Ordenar Pods por importancia de negocio
2. **Eficiencia de recursos**: Programar primero Pods con solicitudes de recursos más pequeñas para aprovechar el espacio libre
3. **Service Level Agreements (SLA)**: Ordenar Pods según los requisitos de SLA
4. **Procesamiento por lotes**: Ajustar la prioridad entre batch jobs y jobs interactivos

**Monitoreo de la cola de scheduling:**
```bash
# Check queue information in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i queue

# Check pods pending scheduling
kubectl get pods --all-namespaces -o wide | grep -i pending
```

**Problemas con las otras opciones:**
- A. Puntuar Nodes: Este es el rol del punto de extensión "Score".
- B. Excluir Nodes donde los Pods no pueden ejecutarse: Este es el rol del punto de extensión "Filter".
- D. Vincular Pods a Nodes: Este es el rol del punto de extensión "Bind".
</details>
### 8. ¿Cuál es el propósito principal de Pod Priority Preemption en Kubernetes?

A. Eliminar Pods de menor prioridad para que se puedan programar Pods de mayor prioridad
B. Asignar más recursos a Pods de mayor prioridad
C. Ejecutar Pods de mayor prioridad más rápido
D. Colocar Pods de mayor prioridad solo en Nodes específicos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Eliminar Pods de menor prioridad para que se puedan programar Pods de mayor prioridad**

**Explicación:**
El propósito principal de Pod Priority Preemption en Kubernetes es eliminar Pods de menor prioridad para que se puedan programar Pods de mayor prioridad. Cuando los recursos del cluster son insuficientes y los Pods de mayor prioridad no pueden programarse, el scheduler preempts (elimina) Pods de menor prioridad para liberar espacio.

**Mecanismo de Pod Priority y Preemption:**
1. **Definición de PriorityClass**: Un recurso a nivel de cluster que define la prioridad del Pod.
2. **Asignar prioridad al Pod**: Los Pods referencian una PriorityClass mediante `spec.priorityClassName`.
3. **Orden de scheduling**: Los Pods de mayor prioridad se procesan primero en la cola de scheduling.
4. **Proceso de preemption**: Cuando los Pods de mayor prioridad no pueden programarse, el scheduler elimina Pods de menor prioridad para liberar espacio.

**Ejemplo de PriorityClass:**
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000  # Priority value (higher value means higher priority)
globalDefault: false  # Whether to use this class as the default
description: "High priority pods"  # Description
preemptionPolicy: PreemptLowerPriority  # Preemption policy (default: PreemptLowerPriority)
```

**Aplicación de prioridad a un Pod:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority  # Reference PriorityClass name
  containers:
  - name: nginx
    image: nginx
```

**Políticas de Preemption:**
PriorityClass tiene un campo `preemptionPolicy` que puede tener los siguientes valores:
1. **PreemptLowerPriority (default)**: Puede hacer preempt de Pods de menor prioridad.
2. **Never**: No hace preempt de Pods de menor prioridad.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority-no-preemption
value: 1000000
globalDefault: false
description: "High priority pods that do not preempt other pods"
preemptionPolicy: Never  # Do not preempt
```

**Proceso de Preemption:**
1. El scheduler intenta programar un Pod de mayor prioridad.
2. Si no hay un Node adecuado, el scheduler identifica Pods candidatos para preemption en cada Node.
3. Los candidatos para preemption se seleccionan entre Pods de menor prioridad.
4. El scheduler preempts la cantidad mínima de Pods para liberar los recursos requeridos.
5. Los Pods seleccionados se terminan de forma ordenada.
6. Una vez que los Pods preempted terminan, se programa el Pod de mayor prioridad.

**Consideraciones de Preemption:**
1. **Periodo de terminación ordenada**: Los Pods preempted tienen un tiempo de terminación ordenada de `terminationGracePeriodSeconds` (predeterminado: 30 segundos).
2. **Pod Disruption Budget (PDB)**: El scheduler intenta no infringir los PDB cuando es posible.
3. **Node taints**: Después de la preemption, pueden añadirse taints al Node para evitar que se programen nuevos Pods.
4. **System pods**: Los Pods críticos del sistema suelen tener una prioridad muy alta y no se preempt.

**Comprobación de eventos de Preemption:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Monitoreo de métricas relacionadas con Preemption:**
```bash
# Check preemption-related metrics in scheduler metrics
kubectl get --raw /metrics | grep scheduler_preemption
```

**Implementación de Preemption en un Custom Scheduler:**
Al implementar un custom scheduler, debes considerar los mecanismos de pod priority y preemption.

```go
// Preemption logic example
func preempt(pod *v1.Pod, nodes []*v1.Node) *v1.Node {
    // Check pod priority
    podPriority := getPodPriority(pod)

    // Identify preemptable pods on each node
    for _, node := range nodes {
        // Get pods running on the node
        nodePods := getPodsOnNode(node)

        // Identify preemption candidate pods
        var victims []*v1.Pod
        for _, p := range nodePods {
            // Select only lower priority pods
            if getPodPriority(p) < podPriority {
                victims = append(victims, p)
            }
        }

        // Check if resources are sufficient after preemption
        if hasEnoughResourcesAfterPreemption(node, victims, pod) {
            // Execute preemption
            for _, victim := range victims {
                evictPod(victim)
            }
            return node
        }
    }

    return nil  // No suitable node found
}
```

**Pros y contras de Preemption:**
Pros:
- Garantiza el scheduling de workloads importantes
- Uso eficiente de los recursos del cluster
- Admite el cumplimiento de Service Level Agreement (SLA)

Contras:
- Interrupción de los Pods preempted
- Overhead por reprogramación después de la preemption
- Lógica compleja de decisión de preemption

**Problemas con las otras opciones:**
- B. Asignar más recursos a Pods de mayor prioridad: Pod priority no afecta directamente la asignación de recursos. Resource requests y limits se definen por separado en la especificación del Pod.
- C. Ejecutar Pods de mayor prioridad más rápido: La priority afecta el orden de scheduling, pero no cambia la velocidad de ejecución del Pod en sí.
- D. Colocar Pods de mayor prioridad solo en Nodes específicos: Este es el rol de nodeSelector o nodeAffinity y no está directamente relacionado con la priority.
</details>

### 9. ¿Cuál es el rol del punto de extensión "PreFilter" en el scheduler de Kubernetes?

A. Realizar preprocesamiento sobre el Pod y el estado del cluster antes del filtering
B. Puntuar Nodes después del filtering
C. Realizar verificación antes de vincular Pods a Nodes
D. Ordenar Pods en la cola de scheduling

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Realizar preprocesamiento sobre el Pod y el estado del cluster antes del filtering**

**Explicación:**
El rol del punto de extensión "PreFilter" en el framework de scheduling de Kubernetes es realizar preprocesamiento sobre el Pod y el estado del cluster antes del filtering. Los PreFilter plugins preparan datos que se usarán en la etapa de filtering y pueden comprobar previamente si los Pods pueden programarse.

**Funciones principales del punto de extensión PreFilter:**
1. **Preparación de datos**: Inicializar y preparar estructuras de datos que se usarán en la etapa de filtering.
2. **Comprobaciones previas**: Comprobar previamente si los Pods pueden programarse.
3. **Almacenamiento de estado**: Almacenar información de estado que se usará durante el ciclo de scheduling.
4. **Optimización**: Evitar trabajo de filtering innecesario para optimizar el rendimiento.

**Interfaz de PreFilter Plugin:**
```go
type PreFilterPlugin interface {
    Plugin
    // PreFilter performs preprocessing on the pod before filtering.
    PreFilter(ctx context.Context, state *CycleState, pod *v1.Pod) *Status
    // PreFilterExtensions returns an interface that provides additional functionality.
    PreFilterExtensions() PreFilterExtensions
}

type PreFilterExtensions interface {
    // AddPod updates state when a pod is added to a node.
    AddPod(ctx context.Context, state *CycleState, podToAdd *v1.Pod, nodeInfo *NodeInfo) *Status
    // RemovePod updates state when a pod is removed from a node.
    RemovePod(ctx context.Context, state *CycleState, podToRemove *v1.Pod, nodeInfo *NodeInfo) *Status
}
```

**PreFilter Plugins predeterminados:**
Kubernetes proporciona los siguientes PreFilter plugins predeterminados:

1. **InterPodAffinity**: Maneja requisitos de inter-pod affinity y anti-affinity.
2. **NodeAffinity**: Maneja requisitos de node affinity.
3. **NodePorts**: Maneja host ports solicitados por Pods.
4. **NodeResourcesFit**: Maneja requisitos de recursos de Node.
5. **PodTopologySpread**: Maneja pod topology spread constraints.
6. **VolumeBinding**: Maneja requisitos de volume binding.

**Ejemplo de Custom PreFilter Plugin:**
```go
// CustomPreFilter implements custom pre-filtering logic.
type CustomPreFilter struct {
    handle framework.Handle
}

// Name returns the plugin name.
func (pl *CustomPreFilter) Name() string {
    return "CustomPreFilter"
}

// PreFilter performs preprocessing on the pod before filtering.
func (pl *CustomPreFilter) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    // Example: Check if the pod is schedulable according to certain conditions
    if !isPodSchedulable(pod) {
        return framework.NewStatus(framework.Unschedulable, "Pod does not meet custom requirements")
    }

    // Example: Store data to be used in the filtering stage
    data := &customPreFilterState{
        // Initialize required data
    }
    state.Write(stateKey, data)

    return nil
}

// PreFilterExtensions returns an interface that provides additional functionality.
func (pl *CustomPreFilter) PreFilterExtensions() framework.PreFilterExtensions {
    return nil  // Return nil if no extension functionality is needed
}

// State data structure
type customPreFilterState struct {
    // Define required fields
}

// State key
var stateKey = framework.StateKey("CustomPreFilter")

// Function to check if pod is schedulable
func isPodSchedulable(pod *v1.Pod) bool {
    // Implement custom logic
    return true
}
```

**Habilitación de PreFilter Plugin en la configuración del Scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    preFilter:
      enabled:
      - name: CustomPreFilter
      disabled:
      - name: NodeResourcesFit  # Disable default plugin
```

**Relación entre PreFilter y Filter:**
1. **PreFilter**: Se ejecuta una vez antes de iniciar filtering para todos los Nodes.
2. **Filter**: Se ejecuta individualmente para cada Node.

PreFilter prepara datos que se usarán en la etapa Filter y preidentifica casos en los que los Pods no pueden programarse en ningún Node para evitar trabajo de filtering innecesario.

**Casos de uso de PreFilter:**
1. **Manejo de restricciones complejas**: Manejar eficientemente restricciones complejas como inter-pod affinity y topology spread
2. **Prevalidación**: Comprobar previamente si los Pods pueden programarse para evitar procesamiento innecesario
3. **Caché de datos**: Precalcular datos que se usan repetidamente en la etapa de filtering para mejorar el rendimiento
4. **Compartición de estado**: Gestionar información de estado compartida entre múltiples plugins

**Problemas con las otras opciones:**
- B. Puntuar Nodes después del filtering: Este es el rol del punto de extensión "Score".
- C. Realizar verificación antes de vincular Pods a Nodes: Este es el rol del punto de extensión "PreBind".
- D. Ordenar Pods en la cola de scheduling: Este es el rol del punto de extensión "QueueSort".
</details>

### 10. ¿Qué significa el taint de Node `node.kubernetes.io/unreachable:NoExecute` en Kubernetes?

A. El Node no es alcanzable y los Pods sin tolerations se eliminan
B. El Node no es programable, pero los Pods existentes continúan ejecutándose
C. El Node está en modo de mantenimiento y no se programan nuevos Pods
D. El Node está en estado de escasez de recursos y preferentemente no se programan nuevos Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. El Node no es alcanzable y los Pods sin tolerations se eliminan**

**Explicación:**
El taint de Node `node.kubernetes.io/unreachable:NoExecute` en Kubernetes significa que el Node no es alcanzable y los Pods sin tolerations para este taint se eliminan (evicted) del Node. Este taint lo añade automáticamente el node controller y se aplica cuando el estado del Node cambia de `Ready` a `Unknown`.

**Estado Node Unreachable:**
Causas comunes de que un Node pase a ser no alcanzable:
1. Problemas de conectividad de red
2. Caída del proceso kubelet
3. Fallo del sistema del Node
4. Problemas de alimentación del Node

**Componentes del Taint:**
1. **Key**: `node.kubernetes.io/unreachable`
2. **Value**: Normalmente una cadena vacía, pero puede tener un valor.
3. **Effect**: `NoExecute` - Los Pods sin tolerations se eliminan del Node.

**Efecto NoExecute:**
El efecto `NoExecute` provoca el siguiente comportamiento:
1. No se programan nuevos Pods en Nodes con el taint.
2. Entre los Pods que ya se ejecutan en el Node, aquellos sin tolerations para el taint se eliminan.

**Taints del sistema:**
Kubernetes añade automáticamente los siguientes taints del sistema según el estado del Node:
1. **node.kubernetes.io/not-ready:NoExecute**: El Node no está listo
2. **node.kubernetes.io/unreachable:NoExecute**: El Node no es alcanzable
3. **node.kubernetes.io/memory-pressure:NoSchedule**: El Node tiene presión de memoria
4. **node.kubernetes.io/disk-pressure:NoSchedule**: El Node tiene presión de disco
5. **node.kubernetes.io/pid-pressure:NoSchedule**: El Node tiene presión de PID
6. **node.kubernetes.io/network-unavailable:NoSchedule**: La red del Node no está disponible
7. **node.kubernetes.io/unschedulable:NoSchedule**: El Node está marcado como no programable

**Tolerations predeterminadas:**
Kubernetes añade automáticamente las siguientes tolerations predeterminadas a todos los Pods:
```yaml
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
```

Estas tolerations predeterminadas permiten que los Pods permanezcan en el Node durante 5 minutos (300 segundos) cuando el Node pasa a no estar listo o a no ser alcanzable, lo que evita reprogramaciones innecesarias de Pods debido a problemas temporales de red.

**Tolerations personalizadas:**
Para workloads críticos, puedes configurar tiempos de toleration más largos:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  tolerations:
  - key: node.kubernetes.io/unreachable
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 600  # Tolerate for 10 minutes
  containers:
  - name: nginx
    image: nginx
```

**Configuración del Node Controller:**
El node controller controla los cambios de estado de Node y el comportamiento de aplicación de taints mediante las siguientes configuraciones:
1. **--node-monitor-period**: Periodo para comprobar el estado del Node (predeterminado: 5 segundos)
2. **--node-monitor-grace-period**: Tiempo de espera antes de marcar un Node como `Unknown` (predeterminado: 40 segundos)
3. **--pod-eviction-timeout**: Tiempo de espera antes de eliminar Pods de Nodes `Unknown` o `NotReady` (predeterminado: 5 minutos)

**Comprobación del estado y los taints del Node:**
```bash
# Check node status
kubectl get nodes

# Check node details
kubectl describe node <node-name>

# Check node taints
kubectl get node <node-name> -o jsonpath='{.spec.taints}'
```

**Comprobación de tolerations de Pod:**
```bash
# Check pod tolerations
kubectl get pod <pod-name> -o jsonpath='{.spec.tolerations}'
```

**Manejo de taints en un Custom Scheduler:**
Al implementar un custom scheduler, debes considerar los taints de Node y las tolerations de Pod.

```go
// Taint handling example
func checkNodeUnreachableTaint(node *v1.Node) bool {
    for _, taint := range node.Spec.Taints {
        if taint.Key == "node.kubernetes.io/unreachable" && taint.Effect == v1.TaintEffectNoExecute {
            return true  // Node has unreachable taint
        }
    }
    return false
}
```

**Problemas con las otras opciones:**
- B. El Node no es programable, pero los Pods existentes continúan ejecutándose: Este es el comportamiento del efecto `NoSchedule`; el efecto `NoExecute` también elimina los Pods existentes sin tolerations.
- C. El Node está en modo de mantenimiento y no se programan nuevos Pods: Este suele ser el comportamiento del taint `node.kubernetes.io/unschedulable:NoSchedule`.
- D. El Node está en estado de escasez de recursos y preferentemente no se programan nuevos Pods: Este es el comportamiento del efecto `PreferNoSchedule`, y la escasez de recursos suele indicarse mediante los taints `node.kubernetes.io/memory-pressure` o `node.kubernetes.io/disk-pressure`.
</details>
