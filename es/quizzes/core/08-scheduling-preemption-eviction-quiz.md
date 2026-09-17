# Cuestionario de Scheduling, Preemption y Eviction

Este cuestionario cubre el scheduling (planificación) de Kubernetes, la selección de nodos, la affinity, los taints, la prioridad, la eviction (desalojo), los presupuestos de interrupción y el descheduling.

## Preguntas de opción múltiple

1. ¿Cuál de las etapas de filtrado, puntuación y binding ocurre primero al evaluar los nodos candidatos?
   - A) Puntuación de nodos
   - B) Filtrado de nodos
   - C) Determinación de la prioridad del Pod
   - D) Binding

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Filtrado de nodos**

**Explicación:**
El scheduler filtra los nodos no adecuados, puntúa los nodos viables, selecciona un nodo y hace el binding del Pod. El encolado y otros puntos de extensión del framework rodean estos pasos.
</details>

2. ¿Cuál es la principal diferencia entre node affinity y Pod affinity?
   - A) La node affinity solo admite restricciones estrictas; la Pod affinity solo admite restricciones flexibles
   - B) La node affinity coincide con etiquetas de nodo; la Pod affinity relaciona la ubicación con Pods coincidentes
   - C) La node affinity es a nivel de clúster mientras que la Pod affinity es a nivel de namespace
   - D) Solo la Pod affinity cambia automáticamente la ubicación en tiempo de ejecución

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La node affinity coincide con etiquetas de nodo; la Pod affinity relaciona la ubicación con Pods coincidentes**

**Explicación:**
Ambas admiten reglas required (obligatorias) y preferred (preferidas). La Pod affinity usa Pods coincidentes y una clave de topología para expresar la co-ubicación. IgnoredDuringExecution no desaloja Pods automáticamente cuando cambian las etiquetas.
</details>

3. ¿Cuál es el propósito de los taints y las tolerations?
   - A) Garantizar que un Pod se ejecute solo en un nodo específico
   - B) Permitir que los nodos repelan Pods a menos que tengan una toleration coincidente
   - C) Establecer la affinity entre Pods
   - D) Optimizar automáticamente la utilización del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permitir que los nodos repelan Pods a menos que tengan una toleration coincidente**

**Explicación:**
Una toleration permite que se considere un nodo con taint; no atrae al Pod ni garantiza su ubicación. Combínala con node affinity para cargas de trabajo dedicadas y controla quién puede usar la toleration.
</details>

4. ¿Cómo se relacionan la prioridad de Pod y la preemption?
   - A) Un Pod de mayor prioridad puede desplazar (preempt) Pods de menor prioridad durante el scheduling
   - B) La prioridad establece directamente las asignaciones de CPU/memoria
   - C) La preemption solo ocurre durante el mantenimiento
   - D) No están relacionadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Un Pod de mayor prioridad puede desplazar (preempt) Pods de menor prioridad durante el scheduling**

**Explicación:**
El scheduler puede eliminar víctimas de menor prioridad si al hacerlo un Pod pendiente pasa a ser planificable. Esto no es una garantía de capacidad ni de ubicación. Una PriorityClass con preemptionPolicy: Never no desplaza a otros Pods.
</details>

5. ¿En qué se diferencian nodeSelector y node affinity?
   - A) nodeSelector es una restricción estricta; la node affinity admite restricciones estrictas y flexibles
   - B) nodeSelector solo admite una etiqueta
   - C) La node affinity no puede coincidir con valores de etiqueta
   - D) nodeSelector se aplica solo después del scheduling

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) nodeSelector es una restricción estricta; la node affinity admite restricciones estrictas y flexibles**

**Explicación:**
La node affinity admite además In, NotIn, Exists, DoesNotExist, Gt y Lt. Todas las entradas de nodeSelector deben coincidir. La node affinity required debe coincidir; las reglas preferred afectan a las puntuaciones.
</details>

6. ¿Qué condición desencadena normalmente la eviction por presión de nodo?
   - A) Que un Pod tenga por sí mismo un valor de prioridad bajo
   - B) Que el nodo tenga escasez de memoria, espacio en disco u otros recursos monitorizados
   - C) Que un Pod haya existido durante mucho tiempo por sí mismo
   - D) Que un ReplicaSet tenga demasiadas réplicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Que el nodo tenga escasez de memoria, espacio en disco u otros recursos monitorizados**

**Explicación:**
Kubelet monitoriza las señales de presión y puede reclamar recursos y terminar Pods. El orden de los candidatos considera el uso por encima de los requests, la prioridad del Pod y el uso relativo, no un orden fijo basado únicamente en la QoS. Otros mecanismos de eviction incluyen el drain y los taints NoExecute.
</details>

7. ¿Cómo se ubican los Pods de un DaemonSet?
   - A) Un Pod en cada nodo de destino elegible
   - B) Solo en los nodos del control plane
   - C) Siempre omiten kube-scheduler
   - D) El número de réplicas es independiente del número de nodos elegibles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Un Pod en cada nodo de destino elegible**

**Explicación:**
El controlador del DaemonSet crea Pods dirigidos a los nodos elegibles; el scheduler hace el binding. Los selectores, la affinity, las tolerations y la capacidad siguen siendo relevantes. El comportamiento histórico de binding directo no debe usarse para describir los DaemonSets actuales.
</details>

8. Sin configuración de recursos a nivel de Pod, ¿qué clase de QoS se aplica cuando cada contenedor tiene requests/limits de CPU iguales y requests/limits de memoria iguales?
   - A) BestEffort
   - B) Burstable
   - C) Guaranteed
   - D) Critical

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Guaranteed**

**Explicación:**
Guaranteed tiene requests/limits de CPU y memoria iguales en cada contenedor. BestEffort no tiene ninguno de los dos, mientras que las configuraciones intermedias son Burstable. La QoS no es una PriorityClass y no garantiza la supervivencia ante cualquier fallo o condición de presión.
</details>

9. ¿Qué permite que se considere el scheduling en un nodo con el taint node-role.kubernetes.io/control-plane:NoSchedule?
   - A) Solo la node affinity
   - B) Solo la Pod affinity
   - C) Una toleration coincidente
   - D) Solo una PriorityClass más alta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Una toleration coincidente**

**Explicación:**
La toleration permite el taint, pero aún deben satisfacerse los recursos y otras restricciones de ubicación. Usa la ubicación en el control plane solo para las cargas de trabajo previstas.

```yaml
tolerations:
- key: "node-role.kubernetes.io/control-plane"
  operator: "Exists"
  effect: "NoSchedule"
```
</details>

10. ¿Qué controla principalmente un PodDisruptionBudget?
   - A) El consumo de recursos de los contenedores
   - B) La eviction voluntaria a través de la Eviction API
   - C) La prioridad de scheduling
   - D) La política de reinicio de los contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La eviction voluntaria a través de la Eviction API**

**Explicación:**
Un PDB limita las solicitudes permitidas de la Eviction API, incluidas las operaciones normales de drain/descheduler. La eliminación directa de Pods, los rollouts de los controladores de cargas de trabajo y la eviction por presión de nodo omiten este control. No crea réplicas saludables ni previene fallos de nodo.
</details>

## Preguntas de respuesta corta

1. Describe al menos tres plugins Filter del scheduler.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

- **NodeResourcesFit** compara los recursos solicitados con la capacidad allocatable del nodo y los requests existentes.
- **NodeAffinity** comprueba las reglas obligatorias de selección de nodos; **NodeUnschedulable** rechaza los nodos con cordon a menos que se aplique la toleration correspondiente.
- **InterPodAffinity** comprueba tanto la Pod affinity como la anti-affinity; **PodTopologySpread** comprueba las restricciones estrictas de distribución.
- **TaintToleration** comprueba los taints. **NodePorts** detecta conflictos de puertos del host.
- **VolumeBinding** comprueba el binding/topología de los PVC; **NodeVolumeLimits** comprueba los límites de attachment de CSI.
- Un `spec.nodeName` asignado directamente normalmente omite el scheduler. NodeName no debe describirse como un filtro de máxima prioridad.

Los nombres antiguos específicos de cada proveedor, como EBSLimits, no son los nombres actuales de los plugins CSI.
</details>

2. Explica cómo funcionan conjuntamente la node affinity y los taints/tolerations para nodos GPU dedicados.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

La node affinity restringe una carga de trabajo a los nodos previstos, mientras que un taint repele los Pods que carecen de una toleration coincidente. Por ejemplo, etiqueta los nodos GPU reales, exige la etiqueta de GPU correspondiente, aplícales un taint y tolera ese taint solo en las cargas de trabajo GPU aprobadas.

Una toleration por sí sola no garantiza la ubicación en un nodo GPU. También se requiere una solicitud de GPU como `nvidia.com/gpu: 1` y un device plugin en funcionamiento para reservar una GPU. Es necesario restringir quién puede añadir tolerations/etiquetas cuando esta separación constituye un límite de seguridad.
</details>

3. Explica la prioridad de Pod y la preemption, incluyendo sus límites.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Crea una PriorityClass y referénciala con `spec.priorityClassName`. La cola del scheduler usa la prioridad, y la preemption puede seleccionar víctimas de menor prioridad si eliminarlas hace viable un Pod pendiente.

El scheduler solicita la eliminación de las víctimas a través de la API; kubelet/el runtime llevan a cabo la terminación. La terminación de las víctimas puede retrasar el Pod entrante, y un nodo nominado no es una reserva incondicional. La preemption no elimina Pods de prioridad igual o superior y puede no resolver restricciones de affinity o de capacidad.

Los PDB se consideran en la medida de lo posible (best-effort), no de forma garantizada. Los valores de prioridad definidos por el usuario no deben superar 1.000.000.000; las clases del sistema tienen valores superiores reservados. El simple hecho de ejecutarse en kube-system no exime a un Pod. Revisa los eventos y prueba el impacto.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical production workloads."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: web-server
    image: nginx
```
</details>

4. Distingue entre la eviction por presión de nodo, las solicitudes de la Eviction API y la eliminación basada en taints.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Presión de nodo:** Kubelet observa la disponibilidad de memoria, del sistema de archivos y de PID, y puede reclamar recursos antes de terminar Pods. Los valores hard predeterminados típicos en Linux incluyen memory.available por debajo de 100Mi, nodefs.available por debajo del 10 %, imagefs.available por debajo del 15 % e inodos libres por debajo del 5 %. PID no tiene un umbral predeterminado del 10 %. Los valores predeterminados de memoria en Windows son distintos.

**Soft frente a hard:** Los umbrales soft y sus periodos de gracia deben configurarse explícitamente. Los umbrales hard pueden terminar Pods sin un periodo de gracia. La terminación soft también está limitada por evictionMaxPodGracePeriod. Conserva todos los umbrales previstos al sobrescribir los valores predeterminados.

**Eviction API:** El drain normal y la automatización compatible envían solicitudes Eviction de policy/v1. Los PDB controlan estas solicitudes. Un DELETE directo del Pod es diferente y omite las comprobaciones del PDB.

**Eliminación basada en taints:** Los taints NoExecute pueden eliminar los Pods que no los toleran. Los Pods ordinarios suelen tener tolerations de not-ready/unreachable de 300 segundos. Esto es independiente de la eviction por presión de kubelet y del control de la Eviction API.

La eviction termina un Pod; un controlador de carga de trabajo puede crear un reemplazo con un nuevo UID. Ningún mecanismo mueve de forma segura el mismo Pod a otro nodo. La disponibilidad requiere réplicas, planificación de almacenamiento/capacidad y una gestión de fallos probada.
</details>

5. ¿En qué se diferencia el scheduling actual de un DaemonSet del scheduling de los Pods de un Deployment?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

Un controlador de DaemonSet crea un Pod por cada nodo elegible y establece la affinity al nodo de destino. El scheduler realiza el binding. Un Deployment, en cambio, mantiene un número deseado de réplicas mediante ReplicaSets, con una ubicación basada en recursos y restricciones; el número de Pods no es uno por nodo.

Los DaemonSets obtienen varias tolerations automáticas para las condiciones de nodo, incluidas tolerations NoExecute indefinidas de not-ready/unreachable. No omiten todas las restricciones de recursos ni se ejecutan automáticamente en todos los nodos del control plane con taint.
</details>

## Preguntas prácticas

1. Crea un Pod llamado web-server con nginx:1.30.4 que requiera us-east-1a o us-east-1b y prefiera nodos m5.large.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-east-1a
            - us-east-1b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: node.kubernetes.io/instance-type
            operator: In
            values:
            - m5.large
```

La node affinity required limita las zonas elegibles. La node affinity preferred añade una preferencia de puntuación para m5.large. Las etiquetas estándar las rellena la integración con el proveedor de nube o el nodo; verifica que los nodos del clúster elegidos realmente las tengan.
</details>

2. Aplica el taint dedicated=database:NoSchedule a worker-1 y otorga a un Pod postgres-db una toleration coincidente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```bash
kubectl taint nodes worker-1 dedicated=database:NoSchedule
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres-db
spec:
  containers:
  - name: postgres
    image: postgres:17
    env:
    - name: POSTGRES_PASSWORD
      valueFrom:
        secretKeyRef:
          name: postgres-credentials
          key: password
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "database"
    effect: "NoSchedule"
```

Crea primero postgres-credentials con una clave password en el mismo namespace. El ejemplo demuestra el scheduling y no tiene almacenamiento persistente de base de datos; añade un PVC para un uso duradero. Una toleration permite worker-1, pero no fuerza la ubicación allí.
</details>

3. Crea un Deployment web-frontend de tres réplicas con nginx:1.30.4, co-ubicado con los Pods app=cache pero separado de sus propias réplicas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
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
            topologyKey: "kubernetes.io/hostname"
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-frontend
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: nginx
        image: nginx:1.30.4
```

La Pod affinity y la anti-affinity required se aplican dentro del namespace. Para planificar las tres réplicas, deben existir Pods cache coincidentes en al menos tres nodos elegibles. De lo contrario, las réplicas pueden quedarse en estado Pending. Estas reglas no mueven automáticamente los Pods existentes después de que cambien las etiquetas.
</details>

4. Crea high-priority con el valor 100000 y un Pod critical-service con QoS Guaranteed: CPU 500m y memoria 512Mi tanto en requests como en limits.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "This priority class is for critical services that should be scheduled first."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-service
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

La prioridad afecta al encolado y a la preemption; unos requests/limits de CPU y memoria iguales en el contenedor cumplen los criterios de Guaranteed a nivel de contenedor. Ni la prioridad ni la QoS garantizan inmunidad frente a fallos de nodo o a la eviction.
</details>

5. Crea web-pdb para los Pods app=web-server con minAvailable: 2.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-server
```

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-server
```

El PDB controla las solicitudes normales de la Eviction API para que la eviction voluntaria no reduzca la salud actual por debajo de su presupuesto. La alternativa maxUnavailable: 1 tiene el mismo efecto solo con tres réplicas deseadas. No protege frente a la eliminación directa, las actualizaciones progresivas ni los fallos involuntarios.
</details>

## Temas avanzados

1. ¿Cuál es la forma habitual de ejecutar un scheduler separado para determinados Pods?
   - A) Recompilar kube-scheduler con cada cambio de política
   - B) Despliega un scheduler y selecciónalo con schedulerName
   - C) Añadir cualquier anotación a todos los Pods
   - D) Habilitar el scheduling local en kubelet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Despliega un scheduler y selecciónalo con schedulerName**

**Explicación:**
Debe estar realmente en ejecución un scheduler correspondiente con un RBAC adecuado y una configuración compatible. schedulerName por sí solo no lo instala. El scheduler observa los Pods/nodos y hace el binding de los Pods pendientes elegibles; kubelet no elige la ubicación.

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
</details>

2. ¿Cuál no es una estrategia del Descheduler?
   - A) LowNodeUtilization
   - B) RemoveDuplicates
   - C) PodLifeTimeExtension
   - D) RemovePodsViolatingInterPodAntiAffinity

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) PodLifeTimeExtension**

**Explicación:**
PodLifeTime desaloja los Pods antiguos que coinciden; no extiende su tiempo de vida. Otras estrategias incluyen NodeAffinity, la distribución de topología y las comprobaciones del número de reinicios. LowNodeUtilization normalmente compara los recursos solicitados con la capacidad del nodo. El Descheduler desaloja; los controladores crean los reemplazos y kube-scheduler elige la ubicación, que puede no ser un nodo distinto.
</details>

3. ¿Cuál no es un taint estándar de condición de nodo aplicado automáticamente?
   - A) node.kubernetes.io/not-ready
   - B) node.kubernetes.io/unreachable
   - C) node.kubernetes.io/disk-pressure
   - D) node.kubernetes.io/high-load

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) node.kubernetes.io/high-load**

**Explicación:**
Los taints estándar actuales incluyen not-ready, unreachable, memory-pressure, disk-pressure, pid-pressure, network-unavailable y unschedulable. El antiguo taint out-of-disk no es un taint automático actual. Los taints de presión generalmente usan NoSchedule; el comportamiento NoExecute de not-ready/unreachable y la eviction por presión de kubelet son mecanismos separados.
</details>

4. ¿Qué afirmación sobre las topology spread constraints es falsa?
   - A) Pueden distribuir Pods entre zonas, nodos o racks etiquetados
   - B) DoNotSchedule evalúa el desvío (skew) respecto al mínimo global
   - C) ScheduleAnyway usa una preferencia de distribución
   - D) Reubican automáticamente los Pods existentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Reubican automáticamente los Pods existentes**

**Explicación:**
Las spread constraints afectan al scheduling de los Pods entrantes. No mueven los Pods en ejecución. Con DoNotSchedule, maxSkew compara el número de Pods coincidentes en el dominio de destino con el mínimo global; si los dominios elegibles son menos que minDomains, ese mínimo es cero. Haz coincidir las etiquetas del Pod entrante con labelSelector para que participe en el conteo. Un descheduler puede desalojar los Pods elegibles que incumplen la restricción, pero no garantiza una ubicación de reemplazo concreta.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example-pod
  labels:
    app: web-server
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web-server
  containers:
  - name: nginx
    image: nginx
```
</details>

5. ¿Qué afirmación sobre la QoS y la eviction es falsa?
   - A) Guaranteed requiere la configuración adecuada de requests y limits de CPU/memoria iguales
   - B) Burstable abarca las configuraciones intermedias entre Guaranteed y BestEffort
   - C) BestEffort no tiene requests ni limits de CPU/memoria
   - D) Los Pods Guaranteed siempre se desalojan primero bajo presión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Los Pods Guaranteed siempre se desalojan primero bajo presión**

**Explicación:**
Kubelet no usa la QoS como una secuencia estricta de eviction. Clasifica según el uso por encima de los requests, la prioridad y el uso relativo a los requests; la presión de disco tiene una contabilidad diferente. Los Pods Guaranteed todavía pueden ser desalojados o perderse durante los fallos. La QoS se deriva de los recursos, no se asigna directamente como un campo del Pod.
</details>

6. Una carga de trabajo batch-job se ejecuta junto con Karpenter/Cluster Autoscaler y debería maximizar el número de nodos que queden completamente inactivos para su consolidación. ¿Qué estrategia de puntuación de `NodeResourcesFit` encaja mejor y por qué?
   - A) `LeastAllocated`, porque nivela el uso de CPU/memoria en todos los nodos
   - B) `MostAllocated`, porque agrupa los nuevos pods en los nodos ya más ocupados y deja los demás vacíos
   - C) `RequestedToCapacityRatio` con una curva lineal idéntica a `LeastAllocated`
   - D) Ninguna estrategia importa, ya que EKS permite editar directamente la configuración del scheduler predeterminado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `MostAllocated`, porque agrupa los nuevos pods en los nodos ya más ocupados y deja los demás vacíos**

**Explicación:**
Una prueba desechable con `kind` de 3 workers con carga base desigual (75 %/37 %/0 % de CPU) lo confirmó: el scheduler predeterminado `LeastAllocated` dirigió 6 nuevos pods al nodo más vacío, llevando los tres nodos a 75 %/37 %/37 % (ninguno reducible). Un segundo scheduler configurado con `scoringStrategy.type: MostAllocated` dirigió los mismos 6 pods a los dos nodos más ocupados (93 %/56 %/0 %), dejando el nodo inactivo intacto y apto para la consolidación. El control plane de Amazon EKS es gestionado, por lo que aplicar `MostAllocated` requiere ejecutar un `Deployment` de scheduler adicional y dirigir los pods a él con `schedulerName`, en lugar de editar directamente el scheduler predeterminado.
</details>

[Volver a los materiales de aprendizaje](../../core/08-scheduling-preemption-eviction.md)
