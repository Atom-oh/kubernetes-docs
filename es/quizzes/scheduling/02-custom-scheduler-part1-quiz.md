# Cuestionario de Custom Scheduler (Parte 1)

Este cuestionario evalúa tu comprensión sobre la implementación y el uso de Custom Schedulers en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Cuál es el rol principal de un scheduler en Kubernetes?

A. Creación y eliminación de Pods
B. Asignar pods a nodes adecuados
C. Monitoreo de recursos de nodes
D. Descarga de imágenes de contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Asignar pods a nodes adecuados**

**Explicación:**
El rol principal de un scheduler en Kubernetes es asignar pods a nodes adecuados. El scheduler observa los pods recién creados y encuentra el mejor node para ejecutar los pods que aún no han sido asignados a un node.

**Funciones principales del Scheduler:**
1. **Asignación Pod-Node**: Selecciona el node óptimo considerando los requisitos del pod y los recursos disponibles del node.
2. **Filtrado**: Excluye los nodes que no pueden ejecutar el pod (por ejemplo, recursos insuficientes, taints, etc.).
3. **Puntuación**: Puntúa los nodes adecuados para seleccionar el node óptimo.
4. **Binding**: Vincula el pod al node seleccionado para finalizar la decisión de scheduling.

**Proceso de scheduling:**
1. **Etapa de filtrado (Predicates)**: Excluye los nodes que no pueden ejecutar el pod.
   - PodFitsResources: Comprueba si el node tiene recursos suficientes para cumplir con las solicitudes de recursos del pod
   - PodFitsHostPorts: Comprueba si los host ports solicitados están disponibles
   - PodMatchNodeSelector: Comprueba si el node selector del pod coincide con las labels del node
   - NoVolumeZoneConflict: Comprueba las restricciones de zona de volúmenes
   - CheckNodeMemoryPressure: Comprueba el estado de presión de memoria del node
   - CheckNodeDiskPressure: Comprueba el estado de presión de disco del node

2. **Etapa de puntuación (Priorities)**: Puntúa los nodes adecuados.
   - LeastRequestedPriority: Da puntuaciones más altas a los nodes con menos recursos solicitados
   - BalancedResourceAllocation: Da puntuaciones más altas a los nodes con buen equilibrio de uso de recursos
   - NodeAffinityPriority: Puntúa según las reglas de node affinity
   - TaintTolerationPriority: Puntúa según la tolerancia a taints
   - InterPodAffinityPriority: Puntúa según la afinidad/anti-afinidad entre pods

3. **Binding**: Vincula el pod al node con la puntuación más alta.

**Ejemplo de configuración del Default Scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      disabled:
      - name: NodeResourcesLeastAllocated
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 1
```

**Problemas con las otras opciones:**
- A. Creación y eliminación de Pods: Este es principalmente el rol del controller manager y del API server.
- C. Monitoreo de recursos de nodes: Este es principalmente el rol de kubelet y del metrics server.
- D. Descarga de imágenes de contenedores: Este es el rol de kubelet y del container runtime.
</details>

### 2. ¿Cuál de las siguientes NO es un método para implementar un Custom Scheduler?

A. Extender el kube-scheduler existente
B. Implementar un scheduler completamente nuevo
C. Desarrollar un plugin de scheduling framework
D. Modificar kubelet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Modificar kubelet**

**Explicación:**
Modificar kubelet no es un método para implementar un Custom Scheduler. kubelet es un agente que se ejecuta en cada node y administra la ejecución de pods, pero no toma decisiones de scheduling. El scheduling lo realiza kube-scheduler o custom schedulers.

**Métodos para implementar un Custom Scheduler:**

1. **Extender el kube-scheduler existente**:
   - Usa KubeSchedulerConfiguration para personalizar el comportamiento del scheduler predeterminado.
   - Ajusta pesos de plugins, habilita/deshabilita, etc.

   ```yaml
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: custom-scheduler
     plugins:
       score:
         disabled:
         - name: NodeResourcesLeastAllocated
         enabled:
         - name: NodeResourcesBalancedAllocation
           weight: 2
   ```

2. **Implementar un scheduler completamente nuevo**:
   - Desarrolla un scheduler independiente que se comunica con la API de Kubernetes.
   - Implementa directamente la observación de pods, la selección de nodes y la lógica de binding.

   ```go
   // Simple Go scheduler example
   func main() {
       config, err := clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
       if err != nil {
           log.Fatal(err)
       }

       clientset, err := kubernetes.NewForConfig(config)
       if err != nil {
           log.Fatal(err)
       }

       // Watch unscheduled pods
       watchPods(clientset)
   }

   func watchPods(clientset *kubernetes.Clientset) {
       watch, err := clientset.CoreV1().Pods("").Watch(context.TODO(), metav1.ListOptions{
           FieldSelector: "spec.schedulerName=custom-scheduler,spec.nodeName=",
       })
       if err != nil {
           log.Fatal(err)
       }

       for event := range watch.ResultChan() {
           if event.Type != watch.Added {
               continue
           }

           pod := event.Object.(*v1.Pod)
           // Implement node selection logic
           node := selectNode(clientset, pod)
           if node != "" {
               bindPod(clientset, pod, node)
           }
       }
   }
   ```

3. **Desarrollar un plugin de scheduling framework**:
   - Usa el scheduling framework de Kubernetes para desarrollar plugins para etapas específicas de scheduling.
   - Implementa extension points como filter, score, bind, etc.

   ```go
   // Scoring plugin example
   type MyScorePlugin struct{}

   func (pl *MyScorePlugin) Name() string {
       return "MyScorePlugin"
   }

   func (pl *MyScorePlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
       // Implement custom scoring logic
       return score, nil
   }

   func (pl *MyScorePlugin) ScoreExtensions() framework.ScoreExtensions {
       return pl
   }

   func (pl *MyScorePlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
       // Implement score normalization logic
       return nil
   }
   ```

**Rol de kubelet:**
kubelet es un agente que se ejecuta en cada node y realiza los siguientes roles:
- Ejecutar y administrar contenedores según las especificaciones de pods
- Monitorear e informar el estado del node
- Realizar comprobaciones de salud de contenedores
- Administrar montajes de volúmenes

kubelet ejecuta las decisiones tomadas por el scheduler (qué pod ejecutar en qué node) y no toma decisiones de scheduling por sí mismo.

**Explicación de las otras opciones:**
- A. Extender el kube-scheduler existente: Un método válido de implementación de Custom Scheduler.
- B. Implementar un scheduler completamente nuevo: Un método válido de implementación de Custom Scheduler.
- C. Desarrollar un plugin de scheduling framework: Un método válido de implementación de Custom Scheduler.
</details>

### 3. ¿Qué campo se usa en un pod para especificar un scheduler concreto?

A. spec.scheduler
B. spec.schedulerName
C. metadata.scheduler
D. spec.nodeName

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. spec.schedulerName**

**Explicación:**
El campo usado en un pod para especificar un scheduler concreto es `spec.schedulerName`. Cuando se establece este campo, el pod es programado únicamente por el scheduler con el nombre especificado. El valor predeterminado es "default-scheduler".

**Ejemplo de Pod Spec:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
  labels:
    app: my-app
spec:
  schedulerName: my-custom-scheduler  # Specify custom scheduler
  containers:
  - name: main-container
    image: nginx:1.19
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

Este pod es programado únicamente por el scheduler llamado "my-custom-scheduler". Si no existe un scheduler con ese nombre en el cluster, el pod permanecerá en estado `Pending`.

**Ejemplo de despliegue de múltiples schedulers:**
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
      serviceAccountName: my-custom-scheduler
      containers:
      - name: scheduler
        image: my-custom-scheduler:v1.0
        args:
        - --scheduler-name=my-custom-scheduler
        - --leader-elect=false
```

**Consideraciones al seleccionar un scheduler:**
1. **Disponibilidad**: Si el scheduler especificado no está en ejecución, el pod no será programado.
2. **Funcionalidad**: Cada scheduler puede tener algoritmos y políticas de scheduling diferentes.
3. **Aislamiento de recursos**: Se pueden usar diferentes schedulers para aislar workloads.
4. **Hardware especial**: Se pueden usar schedulers dedicados para hardware especial como GPUs o FPGAs.

**Comprobación del estado del scheduler:**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n kube-system -l component=my-custom-scheduler
```

**Problemas con las otras opciones:**
- A. spec.scheduler: Un campo que no existe en la API de Kubernetes.
- C. metadata.scheduler: Un campo que no existe en la API de Kubernetes.
- D. spec.nodeName: Este campo se usa para omitir el scheduler y asignar directamente un pod a un node específico. No es un campo para especificar un scheduler.
</details>
### 4. ¿Cuál es el rol del extension point "Filter" en el scheduling framework de Kubernetes?

A. Puntuar nodes
B. Vincular pods a nodes
C. Excluir nodes donde los pods no pueden ejecutarse
D. Ordenar pods en la cola de scheduling

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Excluir nodes donde los pods no pueden ejecutarse**

**Explicación:**
El rol del extension point "Filter" (anteriormente llamado "Predicate") en el scheduling framework de Kubernetes es excluir nodes donde los pods no pueden ejecutarse. Los plugins de Filter comprueban si cada node cumple los requisitos del pod y excluyen de la lista de candidatos los nodes que no los cumplen.

**Extension points del Scheduling Framework:**
El scheduling framework proporciona varios extension points donde los plugins pueden integrarse en diferentes etapas del ciclo de scheduling:

1. **Queue Sort**: Determina el orden de los pods en la cola de scheduling.
2. **PreFilter**: Realiza preprocesamiento sobre el pod y el estado del cluster antes del filtrado.
3. **Filter**: Excluye nodes donde los pods no pueden ejecutarse.
4. **PreScore**: Realiza los cálculos necesarios antes de la puntuación.
5. **Score**: Asigna puntuaciones a los nodes que pasaron el filtrado.
6. **NormalizeScore**: Normaliza las puntuaciones de cada plugin de puntuación.
7. **Reserve**: Reserva recursos del pod en el node seleccionado.
8. **Permit**: Permite, deniega o retrasa el scheduling del pod.
9. **PreBind**: Realiza el trabajo necesario antes del binding.
10. **Bind**: Vincula el pod al node.
11. **PostBind**: Realiza trabajo de limpieza después del binding.

**Plugins de Filter predeterminados:**
Kubernetes proporciona los siguientes plugins de filter predeterminados:

1. **NodeResourcesFit**: Comprueba si el node tiene recursos suficientes para cumplir con las solicitudes de recursos del pod.
2. **NodeName**: Comprueba si el campo spec.nodeName del pod coincide con el nombre del node.
3. **NodeUnschedulable**: Comprueba si el node está marcado como no programable.
4. **TaintToleration**: Comprueba si el pod tolera los taints del node.
5. **NodeAffinity**: Comprueba si se cumplen los requisitos de node affinity del pod.
6. **PodAffinity**: Comprueba si se cumplen los requisitos de pod affinity del pod.
7. **VolumeRestrictions**: Comprueba restricciones de volúmenes.
8. **EBSLimits**: Comprueba límites de volúmenes de Amazon EBS.
9. **NoVolumeZoneConflict**: Comprueba restricciones de zona de volúmenes.
10. **CheckNodeMemoryPressure**: Comprueba el estado de presión de memoria del node.
11. **CheckNodeDiskPressure**: Comprueba el estado de presión de disco del node.

**Ejemplo de plugin de Filter personalizado:**
```go
// Custom filter plugin example
type MyFilterPlugin struct{}

func (pl *MyFilterPlugin) Name() string {
    return "MyFilterPlugin"
}

// Filter method implementation
func (pl *MyFilterPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // Check if the node meets certain conditions
    node := nodeInfo.Node()
    if node == nil {
        return framework.NewStatus(framework.Error, "node not found")
    }

    // Example: Only allow nodes with a specific label
    if value, exists := node.Labels["custom-label"]; !exists || value != "required-value" {
        return framework.NewStatus(framework.Unschedulable, "node does not have required label")
    }

    return nil // Returning nil means the node is suitable
}
```

**Habilitación del plugin de Filter en la configuración del Scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    filter:
      enabled:
      - name: MyFilterPlugin
      disabled:
      - name: NodeResourcesFit  # Disable default plugin
```

**Problemas con las otras opciones:**
- A. Puntuar nodes: Este es el rol del extension point "Score".
- B. Vincular pods a nodes: Este es el rol del extension point "Bind".
- D. Ordenar pods en la cola de scheduling: Este es el rol del extension point "Queue Sort".
</details>

### 5. ¿Cuál de las siguientes NO es una consideración al implementar un Custom Scheduler?

A. Uso de recursos del node
B. Prioridad y preemption de pods
C. Tamaño de la imagen del contenedor
D. Node affinity y anti-affinity

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Tamaño de la imagen del contenedor**

**Explicación:**
El tamaño de la imagen del contenedor generalmente no es una consideración al implementar un Custom Scheduler. El tamaño de la imagen afecta el tiempo de descarga de la imagen y de inicio del contenedor, más que las decisiones de scheduling, que son responsabilidad de kubelet y del container runtime.

**Consideraciones clave al implementar un Custom Scheduler:**

1. **Uso de recursos del node**:
   - Uso de recursos como CPU, memoria, disco, red
   - Ubicación óptima considerando el uso actual y las solicitudes
   - Política de sobreasignación de recursos

   ```go
   // Resource usage based filtering example
   func filterByResourceUsage(pod *v1.Pod, node *v1.Node) bool {
       // Check node's allocatable resources
       allocatable := node.Status.Allocatable
       // Calculate sum of resource requests for pods running on the node
       // Check if new pod's resource requests exceed available resources
       return podFitsResources(pod, allocatable, usedResources)
   }
   ```

2. **Prioridad y preemption de pods**:
   - Programar primero los pods de mayor prioridad
   - Realizar preemption de pods de menor prioridad cuando sea necesario
   - Considerar PriorityClass y preemptionPolicy

   ```yaml
   # Priority class example
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000
   globalDefault: false
   description: "High priority pods"
   ```

3. **Node affinity y anti-affinity**:
   - Cumplir los requisitos nodeSelector y nodeAffinity del pod
   - Aplicar reglas de afinidad y anti-afinidad entre pods
   - Considerar restricciones de distribución topológica

   ```yaml
   # Node affinity example
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
   ```

4. **Otras consideraciones importantes**:
   - **Taints and tolerations**: Coincidencia entre taints de nodes y tolerations de pods
   - **Topology spread**: Distribución de pods entre diversos dominios de topología
   - **Node status**: Estado del node (Ready, MemoryPressure, DiskPressure, etc.)
   - **Características del workload**: Requisitos de varios tipos de workload como batch, service, daemonset
   - **Topología de red**: Latencia de red y ancho de banda entre nodes
   - **Características de hardware**: Requisitos especiales de hardware como GPUs, FPGAs

**Consideraciones relacionadas con el tamaño de la imagen del contenedor:**
El tamaño de la imagen del contenedor generalmente no afecta directamente las decisiones de scheduling por las siguientes razones:

1. **Disponibilidad de la imagen**: Si la imagen ya está en caché en el node lo gestiona kubelet, no el scheduler.
2. **Tiempo de descarga**: La descarga de la imagen ocurre después de la decisión de scheduling y es responsabilidad de kubelet.
3. **Uso de almacenamiento**: El almacenamiento de imágenes generalmente no se incluye en el cálculo de los recursos asignables del node.

Sin embargo, en casos especiales, se puede implementar un custom scheduler que considere la localidad de la imagen. Esto puede ayudar a reducir el tiempo de inicio al preferir nodes donde la imagen ya está en caché.

**Explicación de las otras opciones:**
- A. Uso de recursos del node: Un factor importante en las decisiones de scheduling, esencial para seleccionar nodes que puedan cumplir con las solicitudes de recursos del pod.
- B. Prioridad y preemption de pods: Importante para decidir qué pods programar primero durante la contención de recursos y qué pods desplazar cuando sea necesario.
- D. Node affinity y anti-affinity: Importante para manejar restricciones donde los pods deben programarse junto con, o separados de, nodes específicos u otros pods.
</details>
### 6. ¿Cuál es el rol del extension point "Score" en el scheduling framework de Kubernetes?

A. Excluir nodes donde los pods no pueden ejecutarse
B. Puntuar nodes que pasaron el filtrado
C. Vincular pods a nodes
D. Ordenar pods en la cola de scheduling

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Puntuar nodes que pasaron el filtrado**

**Explicación:**
El rol del extension point "Score" (anteriormente llamado "Priority") en el scheduling framework de Kubernetes es asignar puntuaciones a los nodes que pasaron el filtrado. Los plugins de scoring asignan puntuaciones a cada node, y el node óptimo se selecciona en función de estas puntuaciones.

**Proceso de scoring:**
1. Cada plugin de scoring calcula una puntuación para cada node (normalmente en el rango de 0-100).
2. La puntuación de cada plugin se pondera según el peso configurado.
3. Se suman las puntuaciones ponderadas de todos los plugins.
4. El node con la puntuación total más alta se selecciona para la ubicación del pod.

**Plugins de scoring predeterminados:**
Kubernetes proporciona los siguientes plugins de scoring predeterminados:

1. **NodeResourcesBalancedAllocation**: Da puntuaciones más altas a los nodes con uso bien equilibrado de CPU y memoria.
2. **NodeResourcesFit**: Da puntuaciones más altas a los nodes con más recursos disponibles en relación con los recursos solicitados.
3. **NodeAffinity**: Puntúa según las reglas de node affinity.
4. **InterPodAffinity**: Puntúa según las reglas de afinidad/anti-afinidad entre pods.
5. **PodTopologySpread**: Da puntuaciones más altas a los nodes que distribuyen pods uniformemente entre dominios de topología.
6. **TaintToleration**: Da puntuaciones más altas a los nodes con menos taints.
7. **ImageLocality**: Da puntuaciones más altas a los nodes que ya tienen las imágenes de contenedor requeridas.

**Ejemplo de plugin de scoring personalizado:**
```go
// Custom scoring plugin example
type MyScorePlugin struct{}

func (pl *MyScorePlugin) Name() string {
    return "MyScorePlugin"
}

// Score method implementation
func (pl *MyScorePlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // Get node info
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    node := nodeInfo.Node()

    // Example: Score based on specific label value
    if value, exists := node.Labels["custom-score-label"]; exists {
        score, err := strconv.ParseInt(value, 10, 64)
        if err != nil {
            return 0, framework.NewStatus(framework.Error, fmt.Sprintf("invalid score value: %v", err))
        }
        // Score range should be 0-100
        if score < 0 {
            score = 0
        } else if score > 100 {
            score = 100
        }
        return score, nil
    }

    return 0, nil
}

// ScoreExtensions interface implementation
func (pl *MyScorePlugin) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore method implementation
func (pl *MyScorePlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    // Score normalization logic
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }

    if highest == 0 {
        return nil
    }

    // Adjust all scores relative to the highest score
    for i := range scores {
        scores[i].Score = scores[i].Score * 100 / highest
    }

    return nil
}
```

**Habilitación del plugin de scoring y configuración del peso en la configuración del Scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: MyScorePlugin
        weight: 5  # Set weight
      - name: NodeResourcesBalancedAllocation
        weight: 2  # Change default plugin weight
      disabled:
      - name: NodeResourcesFit  # Disable default plugin
```

**Ejemplo de resultado de scoring:**
Suponiendo que los nodes A, B, C pasaron el filtrado y hay dos plugins de scoring:

1. MyScorePlugin (peso: 5)
   - Node A: 80 puntos
   - Node B: 60 puntos
   - Node C: 90 puntos

2. NodeResourcesBalancedAllocation (peso: 2)
   - Node A: 70 puntos
   - Node B: 90 puntos
   - Node C: 50 puntos

Puntuaciones totales ponderadas:
- Node A: (80 x 5) + (70 x 2) = 400 + 140 = 540 puntos
- Node B: (60 x 5) + (90 x 2) = 300 + 180 = 480 puntos
- Node C: (90 x 5) + (50 x 2) = 450 + 100 = 550 puntos

En este caso, Node C recibió la puntuación más alta, por lo que el pod se programa en Node C.

**Problemas con las otras opciones:**
- A. Excluir nodes donde los pods no pueden ejecutarse: Este es el rol del extension point "Filter".
- C. Vincular pods a nodes: Este es el rol del extension point "Bind".
- D. Ordenar pods en la cola de scheduling: Este es el rol del extension point "Queue Sort".
</details>

### 7. ¿Cuál de las siguientes NO es un método para extender el scheduler en Kubernetes?

A. Plugin de scheduling framework
B. Scheduler extender
C. Desplegar múltiples schedulers
D. Modificar el node controller

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Modificar el node controller**

**Explicación:**
Modificar el node controller no es un método para extender el scheduler en Kubernetes. El node controller es un componente del control plane que monitorea y administra el estado de los nodes, y no está directamente relacionado con las decisiones de scheduling.

**Métodos para extender el Scheduler en Kubernetes:**

1. **Plugin de scheduling framework**:
   - Introducido en Kubernetes 1.15, permite insertar plugins en varias etapas del ciclo de scheduling.
   - Proporciona extension points como filter, score, bind, etc.
   - Se integra directamente con el código base del scheduler para mayor eficiencia.

   ```go
   // Scheduling framework plugin registration example
   func NewPlugin(args runtime.Object, handle framework.Handle) (framework.Plugin, error) {
       // Parse plugin configuration
       config, ok := args.(*Config)
       if !ok {
           return nil, fmt.Errorf("want args to be of type Config, got %T", args)
       }

       // Create plugin instance
       return &Plugin{
           handle: handle,
           config: config,
       }, nil
   }

   // Plugin interface implementation
   type Plugin struct {
       handle framework.Handle
       config *Config
   }

   func (pl *Plugin) Name() string { return "MyPlugin" }

   // Implement required extension point methods
   func (pl *Plugin) Filter(...) { ... }
   func (pl *Plugin) Score(...) { ... }
   ```

2. **Scheduler extender**:
   - Extiende la funcionalidad del scheduler mediante un servicio HTTP externo.
   - Puede extender las etapas de filtrado, priorización y binding.
   - Puede tener sobrecarga de rendimiento porque se ejecuta por separado del scheduler.

   ```yaml
   # Scheduler extender configuration example
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
   ```

3. **Desplegar múltiples schedulers**:
   - Despliega custom schedulers junto con el scheduler predeterminado.
   - Cada scheduler opera de forma independiente, y los pods pueden especificar un scheduler particular mediante `spec.schedulerName`.
   - Proporciona flexibilidad completa, pero puede ser complejo de implementar y mantener.

   ```yaml
   # Custom scheduler deployment example
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
         serviceAccountName: my-custom-scheduler
         containers:
         - name: scheduler
           image: my-custom-scheduler:v1.0
           args:
           - --scheduler-name=my-custom-scheduler
           - --leader-elect=false
   ```

**Rol del Node Controller:**
El node controller es un componente del control plane que realiza los siguientes roles:
- Registro de nodes y monitoreo de estado
- Actualizaciones de estado de nodes (Ready, NotReady, etc.)
- Eliminación de pods según el estado del node (cuando un node está NotReady durante mucho tiempo)
- Administración del ciclo de vida de nodes

El node controller no participa directamente en las decisiones de scheduling; actualiza la información de nodes utilizada por el scheduler. Por lo tanto, modificar el node controller no es un método para extender el scheduler.

**Consideraciones al elegir un método de extensión del Scheduler:**
1. **Complejidad**: Los plugins de scheduling framework pueden ser complejos de implementar, pero están estrechamente integrados con el scheduler.
2. **Rendimiento**: Los scheduler extenders pueden tener sobrecarga de llamadas HTTP que puede afectar el rendimiento.
3. **Mantenimiento**: Múltiples schedulers requieren mantener bases de código separadas.
4. **Actualizaciones**: Pueden surgir problemas de compatibilidad durante actualizaciones de Kubernetes.
5. **Funciones**: Cada método proporciona distintos niveles de funcionalidad y flexibilidad.

**Explicación de las otras opciones:**
- A. Plugin de scheduling framework: Un método válido de extensión del scheduler.
- B. Scheduler extender: Un método válido de extensión del scheduler.
- C. Desplegar múltiples schedulers: Un método válido de extensión del scheduler.
</details>
### 8. ¿Cuál es el propósito del flag `--leader-elect` en el scheduler de Kubernetes?

A. Otorgar autoridad de liderazgo al scheduler
B. Activar solo una instancia entre múltiples instancias del scheduler
C. Ejecutar el scheduler solo en el node líder del cluster
D. Dar al scheduler mayor prioridad que otros componentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Activar solo una instancia entre múltiples instancias del scheduler**

**Explicación:**
El propósito del flag `--leader-elect` en el scheduler de Kubernetes es garantizar que solo una instancia del scheduler esté activa y realice trabajo en configuraciones de alta disponibilidad (HA). Esto evita conflictos y condiciones de carrera que podrían ocurrir si varias instancias del scheduler trabajaran simultáneamente.

**Mecanismo de leader election:**
1. Cuando se despliegan múltiples instancias del scheduler, un algoritmo de leader election elige solo una instancia como líder.
2. Solo la instancia elegida como líder realiza el trabajo real de scheduling.
3. Las demás instancias permanecen en modo standby, y se elige un nuevo líder si el líder actual falla.
4. Este mecanismo se implementa usando resource locks de Kubernetes.

**Flags relacionados con leader election:**
```
--leader-elect=true                      # Whether to enable leader election (default: true)
--leader-elect-lease-duration=15s        # Leadership lease duration
--leader-elect-renew-deadline=10s        # Leadership renewal deadline
--leader-elect-retry-period=2s           # Leadership retry period
--leader-elect-resource-lock=leases      # Resource type to use for leadership lock
--leader-elect-resource-name=kube-scheduler  # Leadership lock resource name
--leader-elect-resource-namespace=kube-system  # Leadership lock resource namespace
```

**Ejemplo de despliegue de Scheduler de alta disponibilidad:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-scheduler
  namespace: kube-system
spec:
  replicas: 3  # Deploy multiple instances
  selector:
    matchLabels:
      component: kube-scheduler
  template:
    metadata:
      labels:
        component: kube-scheduler
    spec:
      containers:
      - name: kube-scheduler
        image: k8s.gcr.io/kube-scheduler:v1.23.0
        command:
        - kube-scheduler
        - --leader-elect=true  # Enable leader election
        - --leader-elect-lease-duration=15s
        - --leader-elect-renew-deadline=10s
        - --leader-elect-retry-period=2s
```

**Comprobación del estado de leader election:**
```bash
# Check leadership resource
kubectl get leases -n kube-system | grep kube-scheduler

# Check leadership details
kubectl describe lease kube-scheduler -n kube-system

# Check leadership related messages in scheduler logs
kubectl logs -n kube-system -l component=kube-scheduler | grep -i leader
```

**Leader election en Custom Scheduler:**
Al implementar un custom scheduler, puedes usar el mismo mecanismo de leader election. Esto utiliza el paquete leaderelection de la biblioteca client-go.

```go
// Leader election implementation example in custom scheduler
import (
    "context"
    "time"

    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    clientset "k8s.io/client-go/kubernetes"
    "k8s.io/client-go/tools/leaderelection"
    "k8s.io/client-go/tools/leaderelection/resourcelock"
)

func runWithLeaderElection(ctx context.Context, client clientset.Interface, schedulerName string) {
    // Leader election configuration
    lock := &resourcelock.LeaseLock{
        LeaseMeta: metav1.ObjectMeta{
            Name:      schedulerName,
            Namespace: "kube-system",
        },
        Client: client.CoordinationV1(),
        LockConfig: resourcelock.ResourceLockConfig{
            Identity: schedulerName + "-" + uuid.New().String(),
        },
    }

    // Execute leader election
    leaderelection.RunOrDie(ctx, leaderelection.LeaderElectionConfig{
        Lock:            lock,
        ReleaseOnCancel: true,
        LeaseDuration:   15 * time.Second,
        RenewDeadline:   10 * time.Second,
        RetryPeriod:     2 * time.Second,
        Callbacks: leaderelection.LeaderCallbacks{
            OnStartedLeading: func(ctx context.Context) {
                // Execute scheduler logic when becoming leader
                runScheduler(ctx)
            },
            OnStoppedLeading: func() {
                // Handle when leadership is lost
                log.Printf("Lost leadership, shutting down")
                os.Exit(0)
            },
            OnNewLeader: func(identity string) {
                // Handle when a new leader is elected
                log.Printf("New leader elected: %s", identity)
            },
        },
    })
}
```

**Casos en los que leader election debería deshabilitarse:**
1. **Despliegue de una sola instancia**: Cuando el scheduler se despliega como una sola instancia
2. **Uso de un mecanismo diferente de leader election**: Cuando una herramienta de orquestación externa administra la activación de instancias
3. **Nombres de scheduler diferentes**: Cuando cada instancia del scheduler usa un `schedulerName` diferente

En estos casos, puedes deshabilitar leader election estableciendo `--leader-elect=false`.

**Problemas con las otras opciones:**
- A. Otorgar autoridad de liderazgo al scheduler: Esta es una descripción vaga que no explica el propósito específico de leader election.
- C. Ejecutar el scheduler solo en el node líder del cluster: No existe el concepto de "node líder" en Kubernetes; el scheduler se ejecuta en nodes de control plane.
- D. Dar al scheduler mayor prioridad que otros componentes: Leader election no está relacionado con la prioridad; sirve para la coordinación entre múltiples instancias del scheduler.
</details>

### 9. ¿Qué recurso se usa en Kubernetes para establecer la prioridad de scheduling de pods?

A. PodSchedulingPolicy
B. PriorityClass
C. SchedulingPriority
D. PodPriority

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. PriorityClass**

**Explicación:**
El recurso usado en Kubernetes para establecer la prioridad de scheduling de pods es `PriorityClass`. PriorityClass define la importancia relativa de los pods, lo que permite al scheduler considerar la prioridad al tomar decisiones de scheduling y preemption.

**Recurso PriorityClass:**
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

**Campos clave:**
1. **value**: Valor de prioridad; los valores más altos significan mayor prioridad. Los pods de sistema normalmente usan valores de 1000000000 (mil millones) o superiores.
2. **globalDefault**: Cuando se establece en true, esta priority class se aplica a los pods que no especifican una priority class.
3. **description**: Descripción de la priority class.
4. **preemptionPolicy**: Política de preemption, puede establecerse en `PreemptLowerPriority` (predeterminado) o `Never`.

**Aplicación de PriorityClass a un Pod:**
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

**Comportamiento de prioridad y preemption:**
1. **Prioridad de scheduling**: Los pods de mayor prioridad se procesan primero en la cola de scheduling.
2. **Preemption**: Cuando no hay ningún node para programar un pod de alta prioridad, el scheduler puede eliminar (preempt) pods de menor prioridad para liberar espacio.
3. **Política de preemption**: Los pods que usan una PriorityClass con `preemptionPolicy: Never` no realizan preemption de otros pods.

**PriorityClasses del sistema:**
Kubernetes proporciona las siguientes PriorityClasses del sistema:
- **system-cluster-critical**: Para pods críticos para la operación del cluster (valor: 2000000000)
- **system-node-critical**: Para pods críticos para la operación del node (valor: 2000001000)

```bash
# Check system PriorityClasses
kubectl get priorityclasses | grep system
```

**Ejemplo de uso de PriorityClass:**
```yaml
# Define multiple priority classes
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "High priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: medium-priority
value: 100000
globalDefault: true
description: "Medium priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: false
description: "Low priority pods"
preemptionPolicy: Never  # Do not preempt
```

**Monitoreo de métricas relacionadas con prioridad y preemption:**
```bash
# Check preemption events
kubectl get events | grep -i preempt

# Check pod priorities
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**Manejo de prioridad en un Custom Scheduler:**
Al implementar un custom scheduler, debes considerar la prioridad de los pods al tomar decisiones de scheduling.

```go
// Pod priority check example
func getPodPriority(pod *v1.Pod) int32 {
    if pod.Spec.Priority != nil {
        return *pod.Spec.Priority
    }
    return 0
}

// Priority-based pod sorting example
func sortPodsByPriority(pods []*v1.Pod) {
    sort.Slice(pods, func(i, j int) bool {
        return getPodPriority(pods[i]) > getPodPriority(pods[j])
    })
}
```

**Problemas con las otras opciones:**
- A. PodSchedulingPolicy: Un recurso que no existe en la API de Kubernetes.
- C. SchedulingPriority: Un recurso que no existe en la API de Kubernetes.
- D. PodPriority: Este no es un tipo de recurso, sino un campo en la especificación del pod (`spec.priority`). Este campo lo establece automáticamente la PriorityClass.
</details>

### 10. ¿Cuál es el rol del plugin `NodeResourcesFit` del scheduler de Kubernetes?

A. Colocar pods según la ubicación física de los nodes
B. Comparar la capacidad de recursos del node con las solicitudes de recursos del pod
C. Comprobar la compatibilidad entre el sistema operativo del node y el pod
D. Medir el ancho de banda de red del node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comparar la capacidad de recursos del node con las solicitudes de recursos del pod**

**Explicación:**
El rol del plugin `NodeResourcesFit` del scheduler de Kubernetes es comparar la capacidad de recursos del node con las solicitudes de recursos del pod para comprobar si el pod puede ejecutarse en el node. Este plugin considera varios tipos de recursos, incluidos CPU, memoria, almacenamiento efímero y recursos extendidos (GPUs, etc.).

**Funciones principales del plugin NodeResourcesFit:**
1. **Verificación de solicitudes de recursos**: Comprueba si las solicitudes de recursos del pod no superan los recursos asignables del node.
2. **Verificación de límites de recursos**: Comprueba si los límites de recursos del pod no superan la capacidad del node.
3. **Verificación de recursos extendidos**: Comprueba si las solicitudes de recursos extendidos como GPUs, FPGAs están disponibles en el node.
4. **Scoring**: Asigna puntuaciones a los nodes que pasaron la etapa de filtrado según el uso de recursos.

**Proceso de verificación de recursos:**
1. Sumar las solicitudes de recursos de todos los contenedores del pod.
2. Comprobar los recursos asignables del node.
3. Comprobar si las solicitudes de recursos del pod no superan los recursos asignables del node.
4. Si los superan, el node se filtra.

**Configuración de NodeResourcesFit en el Scheduler:**
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
        type: MostAllocated  # or LeastAllocated, RequestedToCapacityRatio
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**Estrategias de scoring:**
El plugin NodeResourcesFit admite las siguientes estrategias de scoring:

1. **LeastAllocated**: Da puntuaciones más altas a los nodes con menos recursos usados. Esto es útil para distribuir el uso de recursos.
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: Da puntuaciones más altas a los nodes con más recursos usados. Esto es útil para concentrar el uso de recursos y minimizar el número de nodes.
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: Asigna puntuaciones según la proporción entre los recursos solicitados y la capacidad usando una función personalizada.

**Tipos de recursos:**
El plugin NodeResourcesFit considera los siguientes tipos de recursos:

1. **CPU**: Medida en cores o millicores.
2. **Memoria**: Medida en bytes.
3. **Almacenamiento efímero**: Almacenamiento efímero local del node.
4. **Recursos extendidos**: Recursos personalizados como GPUs, FPGAs.

**Comprobación de recursos del node:**
```bash
# Check node's allocatable resources
kubectl describe node <node-name> | grep Allocatable -A 5

# Check node's resource usage
kubectl top node <node-name>
```

**Comprobación de solicitudes de recursos del Pod:**
```bash
# Check pod's resource requests
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**Implementación de comprobación Resource Fit en Custom Scheduler:**
```go
// Node resource fit check example
func checkNodeResourcesFit(pod *v1.Pod, node *v1.Node) bool {
    // Get node's allocatable resources
    allocatable := node.Status.Allocatable

    // Calculate pod's resource requests
    var requestedCPU, requestedMemory resource.Quantity
    for _, container := range pod.Spec.Containers {
        if request, ok := container.Resources.Requests[v1.ResourceCPU]; ok {
            requestedCPU.Add(request)
        }
        if request, ok := container.Resources.Requests[v1.ResourceMemory]; ok {
            requestedMemory.Add(request)
        }
    }

    // Calculate resources already in use on the node
    // (In actual implementation, sum resource requests of all pods running on the node)

    // Check resource fit
    if allocatableCPU, ok := allocatable[v1.ResourceCPU]; ok {
        if requestedCPU.Cmp(allocatableCPU) > 0 {
            return false  // CPU request exceeds allocatable amount
        }
    }

    if allocatableMemory, ok := allocatable[v1.ResourceMemory]; ok {
        if requestedMemory.Cmp(allocatableMemory) > 0 {
            return false  // Memory request exceeds allocatable amount
        }
    }

    return true  // All resource requests are satisfied
}
```

**Problemas con las otras opciones:**
- A. Colocar pods según la ubicación física de los nodes: Este es el rol de los plugins relacionados con topología (por ejemplo, NodeAffinity, PodTopologySpread).
- C. Comprobar la compatibilidad entre el sistema operativo del node y el pod: Esto se maneja mediante NodeSelector o NodeAffinity, no con un plugin separado.
- D. Medir el ancho de banda de red del node: El scheduler de Kubernetes no considera el ancho de banda de red de forma predeterminada. Se necesitan métricas y plugins personalizados para esto.
</details>
