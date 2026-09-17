# Programación, preemption y eviction de Kubernetes

> **Versiones compatibles**: Kubernetes 1.34 - 1.36 (ejemplo de Descheduler v0.36)
> **Última actualización**: September 17, 2026

En Kubernetes, la programación es el proceso de colocar pods en nodos adecuados. La preemption es el proceso de eliminar pods de menor prioridad para dejar espacio a pods de mayor prioridad, y la eviction termina un Pod; su controlador de carga de trabajo puede crear un reemplazo que el scheduler coloca por separado. En este capítulo, aprenderemos sobre los mecanismos de programación de Kubernetes, la selección de nodos, la preemption, la eviction y los métodos de optimización de programación en Amazon EKS.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesita las siguientes herramientas y entorno:

### Herramientas necesarias
- kubectl dentro de una versión secundaria del servidor de API
- Un clúster de Kubernetes funcional (EKS, minikube, kind, etc.)
- Un clúster con varios nodos (para pruebas de programación)

### Configuración del ejemplo de programación

```bash
# Create namespace
kubectl create namespace scheduling-demo

# Add labels to nodes (if you have multiple nodes)
kubectl label nodes <node-name> disktype=ssd
kubectl label nodes <node-name> gpu=true

# Create a pod using node affinity
kubectl -n scheduling-demo apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx-ssd
  labels:
    app: nginx
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: disktype
            operator: In
            values:
            - ssd
  containers:
  - name: nginx
    image: nginx
EOF

# Create priority class
kubectl apply -f - <<EOF
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical service pods only."
EOF

# Create Pod Disruption Budget (PDB)
kubectl -n scheduling-demo apply -f - <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: nginx
EOF
```

## Arquitectura de programación de Kubernetes

![Arquitectura de programación de Kubernetes: kube-scheduler ejecuta pods mediante encolado, filtrado, puntuación y asociación, condicionado por políticas de colocación, con preemption y eviction basadas en prioridad que retroalimentan la canalización.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-0.html)

## Comparación de conceptos de programación

| Concepto | Propósito | Casos de uso | Versión de Kubernetes |
|---------|---------|-----------|-------------------|
| **Node Selector** | Colocar pods en nodos con etiquetas específicas | Selección simple de nodos | Todas las versiones |
| **Node Affinity** | Definir reglas complejas de selección de nodos | Selección avanzada de nodos | 1.6+ |
| **Pod Affinity** | Colocar pods cerca de otros pods | Ubicar conjuntamente servicios relacionados | 1.6+ |
| **Pod Anti-Affinity** | Colocar pods lejos de otros pods | Garantizar alta disponibilidad | 1.6+ |
| **Taints and Tolerations** | Permitir solo pods específicos en nodos | Nodos dedicados, aislamiento de nodos | 1.6+ |
| **Topology Spread Constraints** | Distribuir pods entre dominios de topología | Distribución entre zonas de disponibilidad | 1.16+ (GA en 1.19) |
| **Priority and Preemption** | Priorizar cargas de trabajo importantes | Garantías para servicios críticos | 1.8+ (GA en 1.11) |
| **Pod Disruption Budget** | Limitar los pods interrumpidos simultáneamente | Garantizar alta disponibilidad | 1.4+ (GA en 1.21) |

## Conceptos básicos de programación

> **Concepto clave**: El scheduler de Kubernetes es un componente del plano de control que selecciona el nodo óptimo para ejecutar pods y opera en dos fases: filtrado y puntuación.

### Proceso de programación

1. **Fase de filtrado (Predicates)**
   - Identifica un conjunto adecuado de nodos que pueden ejecutar el pod
   - Considera requisitos de recursos, selectores de nodos, reglas de affinity, taints/tolerations, etc.
   - Excluye un nodo si no se cumple alguna condición

2. **Fase de puntuación (Priorities)**
   - Asigna puntuaciones a los nodos que superaron el filtrado
   - Considera utilización de recursos, distribución de pods, preferencias de affinity, etc.
   - Selecciona el nodo con la puntuación más alta

3. **Fase de asociación (Binding)**
   - Asigna el pod al nodo seleccionado
   - Actualiza la información de asociación en el servidor de API

## Tabla de contenidos
1. [Descripción general de programación](#scheduling-overview)
2. [Cómo funciona el scheduler](#how-the-scheduler-works)
3. [Selección de nodos](#node-selection)
4. [Pod Affinity y Anti-Affinity](#pod-affinity-and-anti-affinity)
5. [Taints and Tolerations](#taints-and-tolerations)
6. [Node Affinity](#node-affinity)
7. [Prioridad y preemption de Pod](#pod-priority-and-preemption)
8. [Pod Eviction](#pod-eviction)
9. [Pod Disruption Budget (PDB)](#pod-disruption-budget-pdb)
10. [Node Pressure Eviction](#node-pressure-eviction)
11. [TopologySpreadConstraints](#topologyspreadconstraints)
12. [Costo de eliminación de Pod](#pod-deletion-cost)
13. [Descheduler](#descheduler)
14. [Optimización de programación en Amazon EKS](#scheduling-optimization-in-amazon-eks)
15. [Prácticas recomendadas de programación](#scheduling-best-practices)
16. [Conclusión](#conclusion)

## Descripción general de programación

El scheduler de Kubernetes es un componente del plano de control que coloca pods en nodos adecuados. El scheduler considera diversos factores para determinar el nodo óptimo donde colocar pods:

1. **Requisitos de recursos**: CPU, memoria y otros recursos solicitados por el pod
2. **Restricciones de hardware/software/políticas**: Selectores de nodos, node affinity, taints, etc.
3. **Especificaciones de affinity/anti-affinity**: Relaciones de colocación con otros pods
4. **Localidad de datos**: Colocar pods cerca de los datos
5. **Interferencia entre cargas de trabajo**: Minimizar la interferencia entre distintas cargas de trabajo
6. **Objetivos personalizados**: La programación basada en fechas límite o consciente de la interferencia entre cargas de trabajo requiere lógica personalizada adecuada; el scheduler predeterminado no infiere las fechas límite de la aplicación

### Proceso de programación

El proceso de programación se divide, en términos generales, en dos fases:

1. **Filtrado**: Identifica un conjunto de nodos que pueden ejecutar el pod
   - Comprueba si se cumplen los requisitos de recursos
   - Comprueba restricciones como selectores de nodos, affinity y taints

2. **Puntuación**: Puntúa los nodos filtrados para seleccionar el nodo óptimo
   - Equilibrio de utilización de recursos
   - Affinity/anti-affinity entre pods
   - Localidad de datos
   - Taints/tolerations

## Cómo funciona el scheduler

El scheduler de Kubernetes opera mediante el siguiente proceso:

![Diagrama de canalización que muestra un evento de creación de pod que pasa por la cola de programación, kube-scheduler, plugins de filtro, plugins de puntuación, selección del mejor nodo y una solicitud de asociación al servidor de API hasta que el pod llega a un nodo.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-1.html)

1. **Observación de la cola de Pods**: El scheduler observa el servidor de API en busca de pods sin programar.
2. **Filtrado de nodos**: Identifica un conjunto de nodos que pueden ejecutar el pod.
3. **Puntuación de nodos**: Puntúa los nodos filtrados.
4. **Selección de nodos**: Selecciona el nodo con la puntuación más alta.
5. **Asociación**: Asocia el pod al nodo seleccionado.

### Plugins de programación

El scheduler de Kubernetes está diseñado para ser extensible mediante una arquitectura de plugins. Varios plugins operan en distintas etapas del proceso de programación:

1. **Plugins de filtro**: Filtran los nodos donde el pod no puede ejecutarse
   - NodeResourcesFit: Comprueba la capacidad de recursos del nodo
   - NodeName: Comprueba el campo nodeName del pod
   - NodeUnschedulable: Comprueba la programabilidad del nodo
   - TaintToleration: Comprueba taints y tolerations

2. **Plugins de puntuación**: Asignan puntuaciones a los nodos
   - NodeResourcesBalancedAllocation: Considera el equilibrio del uso de recursos
   - ImageLocality: Considera la localidad de la imagen
   - InterPodAffinity: Considera la affinity entre pods
   - NodeAffinity: Considera la node affinity

### Estrategia de puntuación de NodeResourcesFit: LeastAllocated frente a MostAllocated

`NodeResourcesFit` es tanto un plugin de filtro (¿el nodo tiene suficiente CPU/memoria asignable para el pod?) como un plugin de puntuación. El comportamiento de su plugin de puntuación se controla mediante `scoringStrategy.type`, configurado a través de `KubeSchedulerConfiguration`:

- **`LeastAllocated`** (predeterminado): otorga mayor puntuación a los nodos cuanto *menos* asignados estén. Los nuevos pods se dirigen hacia los nodos más vacíos, distribuyendo la carga de forma uniforme.
- **`MostAllocated`**: otorga mayor puntuación a los nodos cuanto *más* asignados estén (siempre que el pod aún quepa). Los nuevos pods se empaquetan primero en los nodos con mayor carga, dejando otros nodos sin tocar o vacíos.
- **`RequestedToCapacityRatio`**: una curva configurable entre las dos opciones, útil para recursos extendidos como GPU cuando desea una forma personalizada en lugar de un mínimo/máximo puro.

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: most-allocated-scheduler
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

El plano de control de Amazon EKS está totalmente administrado, por lo que no puede editar directamente el `KubeSchedulerConfiguration` del kube-scheduler predeterminado. Para usar `MostAllocated`, ejecute un *segundo* scheduler (un `Deployment` que ejecute el binario `kube-scheduler` con esta configuración, asociado a `system:kube-scheduler`/`system:volume-scheduler` mediante un `ServiceAccount` dedicado) y dirija pods específicos hacia él con `spec.schedulerName`, como se muestra en [Multiple Schedulers](#multiple-schedulers) más adelante; es el mismo patrón utilizado en [Building a Custom Scheduler](../scheduling/01-custom-scheduler-part1.md).

**Prueba verificada — comportamiento de distribución frente a bin-packing.** Para confirmar la diferencia práctica, un clúster `kind` desechable de 3 workers (`kubectl version` v1.37.0, aislado y eliminado después de la prueba; no se modificó infraestructura compartida) se inicializó con carga base desigual usando pods de relleno fijados mediante `nodeName` (16 CPU asignables por nodo): `worker`=12 pods (75 %), `worker2`=6 pods (37 %), `worker3`=0 pods (0 %). A continuación, se programaron seis pods idénticos de 1 CPU dos veces —una con el scheduler predeterminado (`LeastAllocated`) y otra con un segundo scheduler configurado con `MostAllocated`— respecto al mismo estado inicial:

| Scheduler / estrategia | Dónde llegaron los 6 nuevos pods | Utilización final de CPU (worker / worker2 / worker3) |
|---|---|---|
| Predeterminado (`LeastAllocated`) | Los 6 en `worker3` (el nodo más vacío) | 75 % / 37 % / 37 % — los tres nodos ahora están ocupados |
| `MostAllocated` | 3 en `worker`, 3 en `worker2` (los dos nodos con mayor carga) | 93 % / 56 % / 0 % — `worker3` permaneció completamente inactivo |

`LeastAllocated` elevó `worker3` hasta igualarlo con `worker2`, por lo que todos los nodos quedan parcialmente utilizados y ninguno puede reducirse de forma segura. `MostAllocated` continuó concentrando la carga en los nodos ya ocupados y dejó `worker3` intacto, precisamente el nodo que un clúster autoscaler o una pasada de consolidación de Karpenter terminaría después.

Por este motivo, `MostAllocated` se recomienda habitualmente para **cargas de trabajo de jobs por lotes o de corta duración** que se ejecutan junto con Karpenter o Cluster Autoscaler: empaquetar jobs en menos nodos maximiza el número de nodos que quedan completamente inactivos y pasan a ser aptos para consolidación, lo que reduce directamente el coste de cómputo. `LeastAllocated` sigue siendo la mejor opción predeterminada para servicios de larga ejecución y sensibles a la latencia, ya que distribuir la carga deja margen en cada nodo para absorber picos de tráfico o un `kubectl drain` sin trasladar presión en cascada a un único nodo empaquetado.

Reproduzca esta comparación exacta usted mismo, paso a paso, en [Scheduler Scoring Strategy Lab](../labs/core/08-scheduling-preemption-eviction-lab.md).

### Multiple Schedulers

Kubernetes puede ejecutar varios schedulers simultáneamente. Esto permite implementar lógica de programación personalizada para cargas de trabajo específicas.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: my-custom-scheduler
  containers:
  - name: container
    image: nginx
```

En el ejemplo anterior, el campo `schedulerName` especifica el scheduler que programará el pod.

## Selección de nodos

Kubernetes proporciona varios mecanismos para colocar pods en nodos específicos.

![Diagrama que compara tres mecanismos de colocación de nodos: nodeSelector que coincide con una etiqueta de nodo, nodeName que fija un nodo específico y nodeAffinity que evalúa una expresión frente a zonas candidatas.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-2.html)

### Node Selector

El selector de nodos es la forma más sencilla de restringir los pods para que solo se coloquen en nodos con etiquetas específicas.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  nodeSelector:
    gpu: "true"
  containers:
  - name: gpu-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

En el ejemplo anterior, el pod solo se coloca en nodos con la etiqueta `gpu=true`.

El ejemplo de GPU solo prueba la programación: el nodo debe tener realmente una GPU y un device plugin funcional que anuncie `nvidia.com/gpu`. Una etiqueta `gpu=true` por sí sola no asigna recursos de GPU.

### nodeName

Puede usar el campo `nodeName` para colocar directamente un pod en un nodo específico. Este método omite el scheduler y, en general, no se recomienda.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: specific-node-pod
spec:
  nodeName: worker-node-1
  containers:
  - name: container
    image: nginx
```

En el ejemplo anterior, el pod se coloca directamente en el nodo denominado `worker-node-1`.

## Pod Affinity y Anti-Affinity

Pod affinity y anti-affinity proporcionan formas de colocar pods según las relaciones entre ellos.

![Diagrama que contrasta pod affinity, que ubica conjuntamente un pod web con un pod de caché en el mismo nodo, con pod anti-affinity, que separa dos réplicas de pods web en nodos distintos; ambos se pueden configurar como requisitos estrictos o flexibles.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-3.html)

### Pod Affinity

Pod affinity hace que los pods se coloquen en el mismo nodo o dominio de topología que los pods con etiquetas específicas.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
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
  containers:
  - name: frontend
    image: nginx
```

En el ejemplo anterior, el pod `frontend` se coloca en el mismo host que los pods con la etiqueta `app=cache`.

### Pod Anti-Affinity

Pod anti-affinity hace que los pods se coloquen en un nodo o dominio de topología diferente de los pods con etiquetas específicas.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  labels:
    app: frontend
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - frontend
        topologyKey: kubernetes.io/hostname
  containers:
  - name: frontend
    image: nginx
```

En el ejemplo anterior, el pod `frontend` se coloca en un host diferente de otros pods con la etiqueta `app=frontend`. Esto es útil para distribuir instancias de la misma aplicación entre varios nodos para lograr alta disponibilidad.

### Tipos de affinity

Pod affinity y anti-affinity tienen dos tipos:

1. **requiredDuringSchedulingIgnoredDuringExecution**: Requisito estricto que debe cumplirse durante la programación
2. **preferredDuringSchedulingIgnoredDuringExecution**: Requisito flexible que se prefiere, pero no es obligatorio

```yaml
# preferredDuringSchedulingIgnoredDuringExecution example
affinity:
  podAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname
```

En el ejemplo anterior, el campo `weight` indica el peso de esta preferencia. Cuando hay varias preferencias, las de mayor peso se consideran más importantes.

## Taints and Tolerations

Taints y tolerations son mecanismos que permiten a los nodos rechazar pods específicos.

![Diagrama que muestra cómo un taint de nodo rechaza pods salvo que lleven una toleration coincidente, los tres efectos de taint NoSchedule, PreferNoSchedule y NoExecute, y un ejemplo donde un nodo GPU con el taint key=gpu:NoSchedule rechaza un pod normal pero admite un pod GPU con una toleration coincidente.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-4.html)

### Taints

Los taints se aplican a los nodos para impedir que los pods se programen en ellos.

```bash
# Add taint to node
kubectl taint nodes node1 key=value:NoSchedule
```

Hay tres efectos de taint:

1. **NoSchedule**: Los Pods sin tolerations no se programan en el nodo
2. **PreferNoSchedule**: Se prefiere no programar en el nodo los Pods sin tolerations
3. **NoExecute**: Los Pods sin tolerations son expulsados del nodo

### Tolerations

Las tolerations se aplican a los pods para permitir que se programen en nodos con taints.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
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

En el ejemplo anterior, el pod puede programarse en nodos con el taint `key=value:NoSchedule`.

### Casos de uso

Casos de uso habituales de taints y tolerations:

1. **Nodos dedicados**: Designar nodos para ejecutar solo cargas de trabajo específicas
2. **Hardware especial**: Administrar nodos con hardware especial como GPU
3. **Mantenimiento de nodos**: Evitar la programación de nuevos pods en nodos en mantenimiento
4. **Problemas de nodos**: Expulsar pods de nodos con problemas

### Taints predeterminados

Kubernetes aplica taints predeterminados a algunos nodos:

- **node.kubernetes.io/not-ready**: El nodo no está listo
- **node.kubernetes.io/unreachable**: No se puede alcanzar el nodo
- **node.kubernetes.io/memory-pressure**: El nodo tiene presión de memoria
- **node.kubernetes.io/disk-pressure**: El nodo tiene presión de disco
- **node.kubernetes.io/pid-pressure**: El nodo tiene presión de PID
- **node.kubernetes.io/network-unavailable**: La red del nodo no está disponible
- **node.kubernetes.io/unschedulable**: El nodo no es programable

## Node Affinity

Node affinity proporciona una forma más expresiva de colocar pods en conjuntos específicos de nodos. Permite especificar condiciones más complejas que el selector de nodos.

### Tipos de Node Affinity

Node affinity tiene dos tipos:

1. **requiredDuringSchedulingIgnoredDuringExecution**: Requisito estricto que debe cumplirse durante la programación
2. **preferredDuringSchedulingIgnoredDuringExecution**: Requisito flexible que se prefiere, pero no es obligatorio

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
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-west-2a
            - us-west-2b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: In
            values:
            - another-node-label-value
  containers:
  - name: with-node-affinity
    image: nginx
```

En el ejemplo anterior, el pod solo se coloca en nodos donde la etiqueta `topology.kubernetes.io/zone` sea `us-west-2a` o `us-west-2b`. Además, se coloca preferentemente en nodos con la etiqueta `another-node-label-key=another-node-label-value`.

### Operadores

Node affinity admite varios operadores:

- **In**: El valor de la etiqueta coincide con uno de los valores especificados
- **NotIn**: El valor de la etiqueta no coincide con los valores especificados
- **Exists**: Existe una etiqueta con la clave especificada
- **DoesNotExist**: No existe una etiqueta con la clave especificada
- **Gt**: El valor de la etiqueta es mayor que el valor especificado
- **Lt**: El valor de la etiqueta es menor que el valor especificado

## Prioridad y preemption de Pod

Kubernetes proporciona funciones de prioridad y preemption de pods para garantizar que las cargas de trabajo importantes puedan obtener recursos del clúster.

![Diagrama que muestra una PriorityClass asignando prioridad a un pod, desencadenando la preemption de pods de menor prioridad cuando los recursos son insuficientes, junto con el proceso de preemption de cuatro pasos, desde el error de programación hasta programar el pod de mayor prioridad, y clases de prioridad integradas de ejemplo.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-5.html)

### PriorityClass

PriorityClass define la importancia relativa de los pods. Cuanto mayor sea el valor de prioridad, más importante será el pod.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical workloads."
```

En el ejemplo anterior, el campo `value` indica el valor de prioridad. Cuanto mayor sea el valor, mayor será la prioridad. Si el campo `globalDefault` se establece en `true`, esta clase de prioridad se aplica a pods sin una clase de prioridad especificada.

### Aplicar PriorityClass a Pods

Para aplicar una clase de prioridad a un pod, use el campo `priorityClassName`.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: container
    image: nginx
```

### Preemption

La preemption es el proceso de eliminar pods de menor prioridad para programar pods de mayor prioridad. Cuando el scheduler no puede encontrar un nodo donde programar un pod de mayor prioridad, realiza preemption de pods de menor prioridad para obtener recursos.

Proceso de preemption:
1. El scheduler no puede encontrar un nodo donde programar un pod de mayor prioridad
2. El scheduler selecciona un nodo del que eliminar pods de menor prioridad mediante preemption
3. Solicita mediante la API la eliminación de los Pods seleccionados de menor prioridad; kubelet/runtime realizan la terminación
4. Cuando los pods terminan correctamente, programa el pod de mayor prioridad en ese nodo

### Consideraciones sobre preemption

Aspectos que se deben considerar al usar preemption:

1. **Período de terminación correcta**: Los pods sujetos a preemption pasan por el proceso de terminación correcta durante el tiempo especificado en `terminationGracePeriodSeconds`
2. **PodDisruptionBudget**: El scheduler intenta evitar infracciones, pero la preemption puede infringir un PDB cuando ningún conjunto adecuado de víctimas lo evita
3. **Clases de prioridad del sistema**: Kubernetes proporciona clases de prioridad para componentes del sistema
   - `system-cluster-critical`: Pods críticos para el funcionamiento del clúster
   - `system-node-critical`: Pods críticos para el funcionamiento del nodo

## Pod Eviction

La eviction de Pod termina un Pod; su controlador de carga de trabajo puede crear un reemplazo que el scheduler coloca por separado. La eviction puede producirse por diversos motivos.

![Diagrama que agrupa la eviction de pod en tres orígenes: el controller manager que expulsa pods de nodos NotReady o Unreachable, kubelet que expulsa pods ante escasez de recursos o problemas de hardware mientras supervisa las señales de eviction memory, nodefs, imagefs y pid, y usuarios que drenan nodos para mantenimiento.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-6.html)

### Tipos de eviction

1. **Eviction por kube-controller-manager**:
   - El taint-eviction-controller maneja los taints NoExecute. Los Pods normalmente reciben tolerations de 300 segundos para not-ready/unreachable; la eviction sigue su configuración de toleration
   - Cuando un nodo está en estado Unreachable

2. **Eviction por kubelet**:
   - Escasez de recursos del nodo (memoria, disco, etc.)
   - Los fallos de hardware pueden provocar indisponibilidad del nodo; no son una señal genérica de eviction por presión de kubelet

3. **Eviction por el usuario**:
   - Ejecución del comando `kubectl drain`
   - Tareas de mantenimiento del nodo

### Señales de eviction de kubelet

kubelet supervisa las siguientes señales de eviction:

1. **memory.available**: Memoria disponible
2. **nodefs.available**: Espacio disponible en el sistema de archivos del nodo
3. **nodefs.inodesFree**: Inodos disponibles en el sistema de archivos del nodo
4. **imagefs.available**: Espacio disponible en el sistema de archivos de imágenes
5. **imagefs.inodesFree**: Inodos disponibles en el sistema de archivos de imágenes
6. **pid.available**: ID de procesos disponibles

Se pueden establecer umbrales flexibles y estrictos para cada señal:

- **Umbral flexible**: Expulsa pods después de `grace-period` cuando se supera el umbral
- **Umbral estricto**: Expulsa pods inmediatamente cuando se supera el umbral

```yaml
# kubelet configuration example
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
  imagefs.available: "15%"
  imagefs.inodesFree: "5%"
evictionSoft:
  memory.available: "200Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: "1m"
  nodefs.available: "2m"
evictionMaxPodGracePeriod: 30
evictionPressureTransitionPeriod: "30s"
```

### Prioridad de eviction

kubelet clasifica los candidatos según si el uso supera las solicitudes, luego según la prioridad de Pod y después según el uso relativo a las solicitudes. No expulsa simplemente primero todos los Pods BestEffort, luego todos los Burstable y finalmente todos los Guaranteed. La presión de disco/PID tiene restricciones de contabilidad diferentes; QoS no es un orden universal de eviction.

## Pod Disruption Budget (PDB)

Pod Disruption Budget (PDB) es una forma de mantener la disponibilidad de la aplicación durante interrupciones voluntarias. PDB limita el número de pods que pueden interrumpirse simultáneamente.

![Diagrama que muestra cómo los valores minAvailable, maxUnavailable y selector de un PodDisruptionBudget controlan una interrupción voluntaria como el drenaje de nodos, permitiendo o denegando la eviction, con un Deployment de ejemplo donde configuraciones equivalentes de minAvailable y maxUnavailable producen el mismo efecto.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-7.html)

### Definición de PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: frontend
```

u

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: frontend
```

En los ejemplos anteriores:
- `minAvailable`: Número mínimo de pods que siempre deben estar disponibles
- `maxUnavailable`: Número máximo de pods que pueden no estar disponibles al mismo tiempo
- `selector`: Selector de etiquetas que selecciona los pods a los que se aplica el PDB

### Funcionamiento de PDB

1. Cuando ocurren interrupciones voluntarias, como el drenaje de nodos, Kubernetes comprueba el PDB
2. Si se cumplen las condiciones del PDB, continúa con la eviction de pod
3. Si no se cumplen las condiciones del PDB, deniega la eviction de pod

Los PDB controlan las solicitudes de la Eviction API, como las operaciones normales de drain/descheduler. La eliminación directa de Pod, los despliegues de controladores y la eviction por presión de nodo omiten este control. `minAvailable: 2` y `maxUnavailable: 1` son equivalentes solo para una carga de trabajo con tres réplicas deseadas; ninguno crea capacidad de reemplazo.

### Prácticas recomendadas de PDB

1. **Establezca PDB para todas las cargas de trabajo críticas**: Establezca PDB para todas las cargas de trabajo que requieran alta disponibilidad
2. **Elija valores adecuados**: Seleccione valores de `minAvailable` o `maxUnavailable` adecuados para las características de la carga de trabajo
3. **Considere el número de réplicas**: `minAvailable` puede ser igual a las réplicas para bloquear evictions voluntarias, pero el mantenimiento podría detenerse; configure una tolerancia de interrupción deliberada
4. **Pruebas periódicas**: Pruebe el funcionamiento de PDB mediante drenaje de nodos y tareas similares

## Node Pressure Eviction

Node pressure eviction es un mecanismo por el cual los pods son expulsados debido a la escasez de recursos del nodo.

### Estado de las condiciones del nodo

kubelet informa los siguientes estados de condición del nodo:

1. **MemoryPressure**: El nodo tiene poca memoria
2. **DiskPressure**: El nodo tiene poco espacio en disco
3. **PIDPressure**: El nodo tiene pocos ID de proceso

Cuando se producen estas condiciones, kubelet expulsa pods para obtener recursos.

### Configuración de la política de eviction

Las políticas de eviction se pueden establecer en la configuración de kubelet:

```yaml
# kubelet configuration example
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
  imagefs.available: "15%"
  imagefs.inodesFree: "5%"
evictionSoft:
  memory.available: "200Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: "1m"
  nodefs.available: "2m"
evictionMinimumReclaim:
  memory.available: "50Mi"
  nodefs.available: "5%"
evictionMaxPodGracePeriod: 30
evictionPressureTransitionPeriod: "30s"
```

En el ejemplo anterior:
- `evictionMinimumReclaim`: Recursos mínimos que deben recuperarse después de la eviction
- `evictionPressureTransitionPeriod`: Tiempo de espera entre transiciones de estado de presión

## TopologySpreadConstraints

TopologySpreadConstraints proporciona control detallado sobre cómo se distribuyen los pods entre dominios de topología, como zonas de disponibilidad, nodos o regiones. Esta función ofrece más flexibilidad que Pod anti-affinity para lograr alta disponibilidad y una utilización eficiente de recursos.

![Diagrama que muestra TopologySpreadConstraints controlando la distribución de pods entre zonas de disponibilidad mediante maxSkew, topologyKey, whenUnsatisfiable y el habitual labelSelector; las opciones DoNotSchedule y ScheduleAnyway de whenUnsatisfiable; y un ejemplo de EKS donde un nuevo pod con maxSkew=1 llega a ap-northeast-2b, la zona con menos pods.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-8.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-8.html)

### Campos clave

| Campo | Descripción | Obligatorio |
|-------|-------------|----------|
| **maxSkew** | Para DoNotSchedule, diferencia permitida entre un dominio objetivo y el mínimo global; ScheduleAnyway usa el skew como preferencia | Sí |
| **topologyKey** | Clave de etiqueta de nodo que define dominios de topología | Sí |
| **whenUnsatisfiable** | Acción cuando no se pueden satisfacer las restricciones: `DoNotSchedule` o `ScheduleAnyway` | Sí |
| **labelSelector** | Selecciona Pods para contarlos; normalmente especifíquelo junto con las etiquetas de Pod coincidentes | No (null no coincide con ningún Pod) |
| **minDomains** | Número mínimo de dominios elegibles para el cálculo de skew (estable desde v1.30) | No |
| **matchLabelKeys** | Claves de etiquetas de Pod que deben coincidir para el cálculo de distribución (1.27+) | No |

### Opciones de whenUnsatisfiable

- **DoNotSchedule**: El scheduler no programará el pod si no se puede satisfacer la restricción (restricción estricta)
- **ScheduleAnyway**: El scheduler seguirá programando el pod, dando mayor prioridad a los nodos que minimicen el skew (restricción flexible)

### Ejemplo de distribución entre zonas de disponibilidad de EKS

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web
      containers:
      - name: web
        image: nginx:1.30.4
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
```

Esta configuración garantiza:
1. Los Pods se distribuyen uniformemente entre zonas de disponibilidad (restricción estricta)
2. Los Pods se distribuyen preferentemente entre nodos dentro de cada zona (restricción flexible)

### minDomains y matchLabelKeys

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-min-domains
spec:
  replicas: 4
  selector:
    matchLabels:
      app: distributed-app
  template:
    metadata:
      labels:
        app: distributed-app
        version: v1
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: distributed-app
        minDomains: 3
        matchLabelKeys:
        - version
      containers:
      - name: app
        image: myapp:v1
```

- **minDomains**: Si existen menos de 3 dominios elegibles, el mínimo global pasa a ser cero. Con maxSkew 1, aún puede programarse un Pod coincidente por dominio elegible; los Pods adicionales pueden permanecer Pending. No bloquea inmediatamente todos los Pods.
- **matchLabelKeys**: Usa automáticamente el valor de la etiqueta `version` del pod en el selector, lo que permite distribución por revisión sin modificar el selector.

### Ventajas respecto a Pod Anti-Affinity

| Aspecto | TopologySpreadConstraints | Pod Anti-Affinity |
|--------|---------------------------|-------------------|
| **Flexibilidad** | Permite skew controlado (maxSkew > 1) | Binario: mismo dominio o dominio distinto |
| **Restricciones flexibles** | `ScheduleAnyway` para best-effort | `preferredDuringScheduling`, pero con menos control |
| **Varios niveles** | Varias restricciones con distintos topologyKeys | Requiere reglas anidadas complejas |
| **Rendimiento** | Mejor rendimiento del scheduler a escala | Puede ralentizar la programación con muchos pods |
| **Caso de uso** | Distribución uniforme con tolerancia | Separación estricta |

## Costo de eliminación de Pod

El costo de eliminación de Pod es una preferencia de mejor esfuerzo que utiliza el controlador ReplicaSet durante la reducción de escala. HPA cambia el número de réplicas deseado; no elige Pods víctima individuales. La anotación no protege Jobs/StatefulSets, no evita la eviction ni garantiza el orden de eliminación.

### Cómo funciona

Cuando un controlador (como HPA o una reducción de escala manual) necesita reducir réplicas, considera:
1. Los pods con menor costo de eliminación se eliminan primero
2. El costo de eliminación predeterminado es 0
3. Intervalo válido: -2147483648 a 2147483647

### Ejemplo básico

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: worker-pod
  annotations:
    controller.kubernetes.io/pod-deletion-cost: "100"
spec:
  containers:
  - name: worker
    image: worker:latest
```

### Control de prioridad de reducción de escala de HPA

Use el costo de eliminación para proteger pods importantes durante la reducción de escala de HPA:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-service
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
      # Lower cost pods are deleted first during scale-down
      annotations:
        controller.kubernetes.io/pod-deletion-cost: "0"
    spec:
      containers:
      - name: web
        image: nginx:1.30.4
```

### Patrón de protección de caché

Ejecute la caché con solicitudes de CPU explícitas si se va a escalar usando HPA de utilización de CPU. Lo siguiente es un ejemplo de programación, no una configuración completa de Redis para producción:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cache-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cache
  template:
    metadata:
      labels:
        app: cache
    spec:
      automountServiceAccountToken: false
      containers:
      - name: cache
        image: redis:7
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
```

Después de medir la calidez real de la caché, un operador/controlador autorizado puede anotar una vez un Pod seleccionado propiedad de ReplicaSet antes de la reducción de escala:

```bash
kubectl -n default annotate pod "$CACHE_POD" \
  controller.kubernetes.io/pod-deletion-cost="1000" --overwrite
```

Establezca `CACHE_POD` en un Pod de caché real. Las escrituras frecuentes de anotaciones generan carga de API. Un actualizador personalizado necesitaría herramientas de cliente tanto de Redis como de Kubernetes, además de permisos de parche de Pod con alcance limitado; el tiempo transcurrido por sí solo no demuestra que una caché esté caliente. Este ejemplo no instala ningún actualizador.

### Casos de uso prácticos

1. **Cachés con estado administradas por un ReplicaSet**: Preferir conservar réplicas calientes
2. **Elección de líder**: Mantener los pods líderes en ejecución durante más tiempo
3. **Drenaje de conexiones**: Dar tiempo a las conexiones de larga duración
4. **Calentamiento de caché**: Conservar pods con cachés calientes
5. **Limitaciones**: Los controladores Job y StatefulSet no utilizan esta preferencia

## Descheduler

El Descheduler es un componente de Kubernetes que expulsa pods de los nodos para permitir que el scheduler los reprograme en nodos más apropiados. A diferencia del scheduler, que solo coloca pods nuevos, el descheduler ayuda a mantener una colocación óptima de pods con el tiempo.

![Diagrama que muestra cómo el Descheduler restablece el equilibrio cuando las adiciones o eliminaciones de nodos, o cambios en los pods, rompen un clúster distribuido uniformemente: expulsa pods en ejecución para que el scheduler los vuelva a colocar, junto con seis estrategias representativas de Descheduler, como RemoveDuplicates, LowNodeUtilization y PodLifeTime.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-9.html)

### Por qué se necesita la desprogramación

1. **Cambios en el clúster**: Se agregaron nodos nuevos, cambiaron las etiquetas de nodo
2. **Deriva de pods**: La colocación inicial se vuelve subóptima con el tiempo
3. **Infracciones de affinity**: Reglas infringidas después de cambios en el clúster
4. **Desequilibrio de recursos**: Algunos nodos están sobreutilizados y otros subutilizados
5. **Pods con errores**: Pods bloqueados en bucles de reinicio

### Estrategias principales

| Estrategia | Descripción | Caso de uso |
|----------|-------------|----------|
| **RemoveDuplicates** | Elimina pods duplicados del mismo nodo | Garantizar HA después de fallos de nodo |
| **LowNodeUtilization** | Mueve pods de nodos sobreutilizados a nodos subutilizados | Equilibrar recursos del clúster |
| **RemovePodsHavingTooManyRestarts** | Expulsa pods con reinicios excesivos | Limpiar pods problemáticos |
| **PodLifeTime** | Expulsa pods más antiguos que la edad especificada | Forzar una programación nueva |
| **RemovePodsViolatingInterPodAntiAffinity** | Expulsa pods que infringen reglas de anti-affinity | Restaurar el cumplimiento de affinity |
| **RemovePodsViolatingNodeAffinity** | Expulsa pods que infringen node affinity | Restaurar el cumplimiento de affinity |
| **RemovePodsViolatingTopologySpreadConstraint** | Expulsa pods que infringen restricciones de distribución | Restaurar una distribución uniforme |

### Instalación con Helm

Descheduler v0.36.0 es la versión de ejemplo verificada, orientada a Kubernetes v1.36 y las dos versiones secundarias anteriores en su ventana de pruebas. Compruebe la matriz de compatibilidad antes de aplicarla a otra versión. Guarde valores de Helm revisados en `descheduler-values.yaml` con `schedule` y `deschedulerPolicy.profiles` (los perfiles de política mostrados a continuación); los antiguos valores `strategies.*.enabled` no configuran esta API.

```bash
helm repo add descheduler https://kubernetes-sigs.github.io/descheduler/
helm upgrade --install descheduler descheduler/descheduler \
  --version 0.36.0 --namespace kube-system \
  --values descheduler-values.yaml
```

### Configuración de DeschedulerPolicy

```yaml
apiVersion: descheduler/v1alpha2
kind: DeschedulerPolicy
profiles:
- name: default
  pluginConfig:
  - name: DefaultEvictor
    args:
      nodeFit: true
  - name: RemoveDuplicates
    args:
      excludeOwnerKinds: [StatefulSet]
  - name: LowNodeUtilization
    args:
      thresholds:
        cpu: 20
        memory: 20
        pods: 20
      targetThresholds:
        cpu: 50
        memory: 50
        pods: 50
  - name: RemovePodsHavingTooManyRestarts
    args:
      podRestartThreshold: 100
      includingInitContainers: true
  - name: PodLifeTime
    args:
      maxPodLifeTimeSeconds: 86400
      labelSelector:
        matchLabels:
          app.kubernetes.io/lifecycle: ephemeral
  - name: RemovePodsViolatingNodeAffinity
    args:
      nodeAffinityType: [requiredDuringSchedulingIgnoredDuringExecution]
  - name: RemovePodsViolatingTopologySpreadConstraint
    args:
      constraints: [DoNotSchedule]
  plugins:
    balance:
      enabled:
      - RemoveDuplicates
      - LowNodeUtilization
      - RemovePodsViolatingTopologySpreadConstraint
    deschedule:
      enabled:
      - RemovePodsHavingTooManyRestarts
      - PodLifeTime
      - RemovePodsViolatingNodeAffinity
```

### Respeto de PDB

El descheduler respeta los Pod Disruption Budgets (PDB). Si expulsar un pod infringiría un PDB, el descheduler no expulsará ese pod:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```

Con este PDB, el descheduler garantizará que al menos 2 pods con la etiqueta `app: web` permanezcan disponibles durante las operaciones de desprogramación.

La política anterior es un archivo de configuración de Descheduler, no un objeto de API para `kubectl apply`. Utiliza plugins Balance para la redistribución de grupos y plugins Deschedule para decisiones por Pod. LowNodeUtilization normalmente evalúa las solicitudes de recursos en lugar del uso de CPU en tiempo real, y la eviction no garantiza que el Pod de reemplazo llegue a otro lugar. Revise las protecciones y pruebe en modo dry-run antes de habilitar la eviction recurrente.

### Ejemplo de CronJob de Descheduler

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: descheduler
  namespace: kube-system
spec:
  schedule: "*/30 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: descheduler
          containers:
          - name: descheduler
            image: registry.k8s.io/descheduler/descheduler:v0.36.0
            args:
            - --policy-config-file=/policy/policy.yaml
            - --v=3
            volumeMounts:
            - name: policy
              mountPath: /policy
          volumes:
          - name: policy
            configMap:
              name: descheduler-policy
          restartPolicy: OnFailure
```

El CronJob independiente es una alternativa a Helm, no una instalación adicional. Requiere el ServiceAccount/RBAC `descheduler` y un ConfigMap `descheduler-policy` con la clave `policy.yaml`; use el chart/manifiestos oficiales para proporcionar estos requisitos previos.

> **Análisis detallado**: Para información detallada sobre schedulers personalizados, consulte:
> - [Custom Scheduler Part 1: Basic Concepts](../scheduling/01-custom-scheduler-part1.md)
> - [Custom Scheduler Part 2: Implementation](../scheduling/02-custom-scheduler-part2.md)
> - [Custom Scheduler Part 3: Advanced Features](../scheduling/03-custom-scheduler-part3.md)

## Optimización de programación en Amazon EKS

En Amazon EKS, puede optimizar cargas de trabajo mediante las funciones de programación de Kubernetes.

![Diagrama que muestra cuatro palancas de optimización de programación de EKS —elección de grupos de nodos y tipos de instancia, distribución entre zonas de disponibilidad, autoescalado de Karpenter y ajuste de solicitudes y límites de recursos—, cada una conectada al mecanismo o herramienta de automatización que la implementa: Cluster Autoscaler, despliegue multi-AZ, Karpenter NodePool y Vertical Pod Autoscaler.](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-11.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-11.html)

### Grupos de nodos y tipos de instancia

En EKS, puede proporcionar recursos adecuados para las cargas de trabajo utilizando diversos grupos de nodos y tipos de instancia:

1. **Diversos tipos de instancia**: Optimizados para cómputo, memoria, almacenamiento, etc.
2. **Instancias Spot**: Instancias Spot para cargas de trabajo rentables
3. **Instancias GPU**: Instancias GPU para cargas de trabajo de AI/ML

Puede usar etiquetas de nodo y taints para colocar cargas de trabajo específicas en grupos de nodos específicos:

Use una configuración de eksctl revisada para el clúster existente, con Region coincidente, instancia/AMI de GPU compatible y los permisos IAM necesarios:

```yaml
# gpu-nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: gpu-nodes
  instanceType: p3.2xlarge
  desiredCapacity: 1
  privateNetworking: true
  labels:
    workload-type: gpu
  taints:
  - key: gpu
    value: "true"
    effect: NoSchedule
```

```bash
eksctl create nodegroup --config-file=gpu-nodegroup.yaml
```

### Distribución entre zonas de disponibilidad

En EKS, puede distribuir cargas de trabajo entre varias zonas de disponibilidad usando pod anti-affinity y restricciones de distribución de topología:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web
      containers:
      - name: web
        image: nginx
```

En el ejemplo anterior, `topologySpreadConstraints` distribuye los pods de manera uniforme entre varias zonas de disponibilidad.

### Autoescalado con Karpenter

En Amazon EKS, puede usar Karpenter para aprovisionar automáticamente nodos adecuados para las cargas de trabajo:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```

Karpenter optimiza costes seleccionando el tipo de instancia óptimo según los requisitos de recursos del pod.

### Optimización de solicitudes y límites de recursos

Es importante optimizar las solicitudes y límites de recursos de las cargas de trabajo en EKS:

1. **Vertical Pod Autoscaler (VPA)**: Optimizar solicitudes de recursos según el uso real de recursos de la carga de trabajo
2. **Goldilocks**: Visualizar las recomendaciones de VPA para facilitar la optimización de solicitudes de recursos
3. **Resource Quotas**: Limitar el uso de recursos por namespace

```yaml
# VPA example
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: frontend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  updatePolicy:
    updateMode: "Recreate"
```

## Prácticas recomendadas de programación

Prácticas recomendadas para optimizar la programación en Kubernetes y EKS:

1. **Establezca solicitudes y límites de recursos adecuados**:
   - Establezca solicitudes de recursos según el uso real de recursos de la carga de trabajo
   - Establezca límites de recursos adecuados para las cargas de trabajo importantes
   - Use VPA para optimizar automáticamente las solicitudes de recursos

2. **Distribución de cargas de trabajo**:
   - Use pod anti-affinity para distribuir cargas de trabajo importantes entre varios nodos
   - Use restricciones de distribución de topología para distribuir cargas de trabajo entre varias zonas de disponibilidad
   - Use node affinity para colocar cargas de trabajo específicas en nodos específicos

3. **Optimización de recursos de nodos**:
   - Use diversos tipos de instancia para proporcionar recursos adecuados para las cargas de trabajo
   - Use instancias spot para optimizar costes
   - Use Karpenter para el aprovisionamiento automático de nodos adecuado para las cargas de trabajo

4. **Configuración de PDB**:
   - Establezca PDB para cargas de trabajo importantes
   - Seleccione valores de `minAvailable` o `maxUnavailable` adecuados para las características de la carga de trabajo
   - Pruebe periódicamente el funcionamiento de PDB

5. **Configuración de prioridad y preemption**:
   - Establezca clases de alta prioridad para cargas de trabajo importantes
   - Use las clases de prioridad `system-cluster-critical` o `system-node-critical` para componentes del sistema
   - Comprenda y pruebe el impacto de la preemption

6. **Taints y tolerations de nodos**:
   - Establezca nodos dedicados para cargas de trabajo especializadas
   - Aplique taints a los nodos en mantenimiento
   - Establezca tolerations adecuadas

## Conclusión

Los mecanismos de programación, preemption y eviction de Kubernetes desempeñan funciones importantes para administrar eficazmente los recursos del clúster y mantener la disponibilidad de las cargas de trabajo. Al comprender y utilizar estas funciones, puede optimizar y operar de forma fiable las cargas de trabajo en clústeres de Amazon EKS.

La optimización de programación es un proceso continuo, y se deben realizar ajustes continuamente según las características de la carga de trabajo y el estado del clúster. Es importante supervisar el uso de recursos del clúster mediante herramientas de monitorización y ajustar las políticas de programación según sea necesario.

## Cuestionario

Para comprobar lo aprendido en este capítulo, pruebe el [Cuestionario de programación, preemption y eviction](../quizzes/core/08-scheduling-preemption-eviction-quiz.md).
