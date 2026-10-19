# Cuestionario de scheduler personalizado (Parte 3)

> **Base de los ejemplos**: Kubernetes 1.35.8 y Go 1.27.2; las funciones nativas de 1.37 se indican por separado
> **Última actualización**: 16 de octubre de 2026

Este cuestionario evalúa los conocimientos avanzados sobre la implementación y el uso de schedulers personalizados en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Qué afirmación sobre el uso de varios schedulers es incorrecta?

A. Los schedulers adicionales aumentan el trabajo de observación de la API y de caché
B. Las asignaciones que cada scheduler supone de forma independiente pueden competir por los recursos
C. Añadir un scheduler aumenta automáticamente la capacidad de los nodos
D. Los grupos de schedulers independientes necesitan Leases de elección de líder distintos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Añadir un scheduler aumenta automáticamente la capacidad de los nodos**

**Explicación:**
Un scheduler asigna Pods; no crea capacidad en los nodos. Los schedulers adicionales pueden aumentar la carga de la API y de la red. Cada uno observa el estado de los Pods ya registrado, pero sus asignaciones supuestas en memoria no forman una transacción de reserva compartida con los demás. Mantenga los filtros de recursos y pruebe la planificación simultánea en grupos de nodos compartidos.

Omitir `schedulerName` selecciona `default-scheduler`; no permite que todos los schedulers que cumplen el contrato vinculen ese Pod. Las réplicas de un mismo scheduler comparten intencionadamente un Lease para ofrecer alta disponibilidad. Los grupos independientes que comparten ese Lease pueden bloquearse entre sí; los procesos que usan el mismo perfil sin coordinar el liderazgo pueden competir.

**Ejemplos de selección del scheduler de un Pod:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: default-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: custom-pod
spec:
  schedulerName: custom-scheduler
  tolerations:
  - key: dedicated
    operator: Equal
    value: custom-scheduler
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

**Separar la identidad del scheduler de la política del grupo de nodos:**
Use el Deployment y el RBAC completos de la Parte 1. Los nombres y la identidad del Lease se definen en `KubeSchedulerConfiguration`, no mediante la opción obsoleta `--scheduler-name`. El plugin integrado `NodeAffinity` admite `addedAffinity` en el perfil; no existe un plugin predeterminado llamado `NodeSelector`.

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
  pluginConfig:
  - name: NodeAffinity
    args:
      addedAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
          - matchExpressions:
            - key: training.example.com/scheduler-pool
              operator: In
              values:
              - custom
```

```bash
# Only label/taint a node selected for this isolated lab.
: "${CUSTOM_NODE:?Select the lab node}"
kubectl label node "$CUSTOM_NODE" training.example.com/scheduler-pool=custom --overwrite
kubectl taint node "$CUSTOM_NODE" dedicated=custom-scheduler:NoSchedule --overwrite
```

El Pod personalizado anterior tolera el taint del ejemplo. Las tolerancias no fuerzan la ubicación; los nombres de los schedulers, las etiquetas de los nodos y las cuotas tampoco constituyen límites de seguridad. Las siguientes cuotas por namespace limitan las solicitudes admitidas, pero no reservan un grupo de nodos. Cree primero los namespaces y defina las solicitudes de recursos de las cargas sujetas a estas cuotas.
**Ejemplos de cuotas por namespace:**
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: default-scheduler-quota
     namespace: default-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi

   ---
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: custom-scheduler-quota
     namespace: custom-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi
   ```

**Monitorización del scheduler secundario mediante consultas:**
Use su namespace y sus etiquetas reales. Los componentes del plano de control administrado de EKS no son el Deployment secundario mostrado aquí.

```bash
kubectl -n scheduler-lab get pods -l app=custom-scheduler
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
kubectl -n scheduler-lab get lease custom-scheduler
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**Otras opciones:** A, B y D describen aspectos reales de carga de trabajo o coordinación.
</details>

### 2. ¿Qué función cumple el punto de extensión "Permit" del scheduler de Kubernetes?

A. Vincular Pods a nodos
B. Permitir, rechazar o retrasar la planificación de Pods
C. Excluir los nodos donde los Pods no pueden ejecutarse
D. Asignar puntuaciones a los nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir, rechazar o retrasar la planificación de Pods**

**Explicación:**
El punto de extensión "Permit" del framework de planificación de Kubernetes permite, rechaza o retrasa la planificación de un Pod. Sus plugins se ejecutan después de seleccionar un nodo y antes de la fase de vinculación, para aprobar o rechazar finalmente la decisión.

**Funciones principales del punto de extensión Permit:**
1. **Permitir**: Deja que la planificación continúe hasta la fase de vinculación.
2. **Rechazar**: Rechaza el intento para que pueda seleccionarse otro nodo.
3. **Esperar**: Retrasa temporalmente la planificación hasta que se cumplan determinadas condiciones.

**Contrato de Permit para la versión indicada:**
`Permit(ctx, fwk.CycleState, pod, nodeName)` devuelve un estado y un tiempo de espera. `Success` permite continuar; `Wait` pide al framework que mantenga el Pod en espera; un estado de fallo como `Unschedulable` rechaza el intento. No existe un valor de enumeración `framework.Deny`. El rechazo no vincula inmediatamente el Pod a otro nodo: después se aplican los reintentos, la espera entre intentos y la limpieza de reservas.

`TaintToleration` y `PodTopologySpread` no son plugins Permit predeterminados. La configuración base conserva sus fases Filter y Score reales.

**Demostración completa de la interfaz (`quizplugins/permit.go`):**
Los valores de la anotación son instrucciones de prueba, no un mecanismo de autorización fiable. No se proporciona un servicio externo de aprobación. Un Pod con el valor `wait` agota el tiempo de espera si un controlador de pruebas integrado no lo libera después de que el framework lo registre; un canal privado sin un consumidor no puede liberar los Pods que esperan en el framework.

```go
package quizplugins

import (
	"context"
	"time"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	fwk "k8s.io/kube-scheduler/framework"
)

type CustomPermit struct{ handle fwk.Handle }

var _ fwk.PermitPlugin = &CustomPermit{}

func (*CustomPermit) Name() string { return "CustomPermit" }

func (*CustomPermit) Permit(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) (*fwk.Status, time.Duration) {
	// These are test directives, not an authorization or approval mechanism.
	switch pod.Annotations["training.example.com/permit"] {
	case "", "allow":
		return nil, 0
	case "wait":
		return fwk.NewStatus(fwk.Wait, "waiting for the test driver"), 30 * time.Second
	case "deny":
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "test driver denied"), 0
	default:
		return fwk.NewStatus(fwk.Error, "unknown test permit directive"), 0
	}
}

// Call only after the framework has registered the waiting Pod. The caller
// must handle false (not registered yet, already released, deleted or timed out).
func (p *CustomPermit) Allow(uid types.UID) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Allow(p.Name())
	return true
}

func (p *CustomPermit) Reject(uid types.UID, reason string) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Reject(p.Name(), reason)
	return true
}

func NewPermit(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &CustomPermit{handle: handle}, nil
}
```

Registre este ejemplo y el de PreBind posterior en `cmd/quiz-scheduler/main.go`; guarde ambos archivos de código antes de compilar:

```go
package main

import (
	"os"

	"example.com/custom-scheduler/quizplugins"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin("CustomPermit", quizplugins.NewPermit),
		app.WithPlugin("IdentityPreBind", quizplugins.NewPreBind),
	)
	os.Exit(cli.Run(command))
}
```

Compile con el módulo de la Parte 1 mediante `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`. Habilite solo el punto de extensión correspondiente y conserve los valores predeterminados:

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
    permit:
      enabled:
      - name: CustomPermit
```

**Casos de uso de Permit:**
1. **Planificación en grupo**: Retrasar la planificación de un grupo de Pods hasta que todos los relacionados estén listos para planificarse.
2. **Reserva de recursos**: Reservar recursos externos antes de planificar los Pods.
3. **Validación de políticas**: Comprobar que la planificación cumple las políticas de la organización.
4. **Flujos de aprobación**: Solicitar una aprobación externa para planificar los Pods.

**Por qué una barrera Permit no constituye un scheduler completo para grupos:**
Una implementación real debe delimitar la identidad del grupo por namespace y UID, contar miembros únicos, gestionar reintentos, eliminaciones y tiempos de espera, liberar las reservas cuando falle y tener en cuenta los fallos de vinculación. No construya un `WaitingPod` privado, no cuente dos veces el mismo reintento ni considere registrado el Pod actual antes de que Permit devuelva el resultado. La barrera no garantiza un arranque simultáneo de los contenedores ni evita que algunas cargas queden sin recursos indefinidamente. La pregunta 3 describe implementaciones mantenidas.

**Por qué las otras opciones son incorrectas:**
- A. Vincular Pods a nodos: Es la función del punto de extensión "Bind".
- C. Excluir los nodos donde los Pods no pueden ejecutarse: Es la función de "Filter".
- D. Asignar puntuaciones a los nodos: Es la función de "Score".
</details>

### 3. ¿Cuál es el objetivo principal de la planificación en grupo en Kubernetes?

A. Ubicar los Pods únicamente en nodos concretos
B. Coordinar la ubicación de un grupo de Pods requerido
C. Distribuir los Pods de manera uniforme entre varios nodos
D. Planificar los Pods según su prioridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Coordinar la ubicación de un grupo de Pods requerido**

**Explicación:**
La planificación en grupo coordina la ubicación del grupo requerido antes de permitir que continúe. Es importante para cargas como el entrenamiento y el procesamiento de datos distribuidos, cuyos componentes deben ejecutarse al mismo tiempo.

**Por qué se necesita la planificación en grupo:**
1. **Requisito de todo o nada**: Algunas cargas requieren que todos sus componentes se ejecuten al mismo tiempo; si solo se ejecuta una parte, la tarea no avanza.
2. **Evitar el desperdicio de recursos**: Si algunos Pods se planifican mientras otros esperan, pueden desperdiciarse los recursos de los ya planificados.
3. **Evitar interbloqueos**: Los Pods con dependencias mutuas pueden bloquearse cuando se planifican en momentos distintos.

**Alternativas de implementación y versiones:**
Kubernetes 1.35 incorporó las funciones alfa `GenericWorkload` y `GangScheduling`, que deben habilitarse expresamente. En la versión upstream 1.37, la planificación de PodGroup está en **beta y deshabilitada de forma predeterminada**; requiere `GenericWorkload` y la API `scheduling.k8s.io/v1beta1`. Esto no demuestra que la función esté disponible en EKS ni autoriza a cambiar las opciones de su plano de control administrado.

Volcano es una alternativa que se instala como scheduler. Kube-batch es su predecesor histórico, no otra recomendación actual. Se necesita un controlador compatible, sus CRD, la planificación en grupo habilitada y una cola en estado Open.

**Ejemplo de Job de Volcano (esquema comprobado con 1.15.2):**
El controlador crea el PodGroup. El ejemplo define los cuatro miembros, a diferencia de un grupo con minMember igual a 4 que contiene un solo Pod. La carga solo usa CPU y ejecuta sleep para mostrar la relación entre los manifiestos; no es un entrenamiento distribuido ni un benchmark. No se ha desplegado.

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: gang-demo
  namespace: default
spec:
  minAvailable: 4
  schedulerName: volcano
  queue: default
  maxRetry: 1
  tasks:
  - name: workers
    replicas: 4
    template:
      spec:
        restartPolicy: Never
        containers:
        - name: worker
          image: busybox:1.38.0
          command:
          - sh
          - -c
          - sleep 60
          resources:
            requests:
              cpu: 250m
              memory: 128Mi
            limits:
              memory: 256Mi
```

La decisión de planificación coordina el grupo mínimo; no hace que sus procesos arranquen en el mismo instante. La aplicación todavía necesita barreras, una política de tiempos de espera, un reparto justo y mecanismos de recuperación. La ubicación nativa de PodGroup también tiene limitaciones documentadas para Pods heterogéneos y dependencias entre Pods: su algoritmo de ordenación no siempre encuentra una ubicación factible.

**Ventajas y desventajas de la planificación en grupo:**
Ventajas:
- Coordina el grupo mínimo configurado
- Evita desperdiciar recursos
- Puede reducir los interbloqueos por asignaciones parciales; el reparto justo y los tiempos de espera siguen siendo necesarios

Desventajas:
- Mayor complejidad de implementación
- Posibles retrasos en la planificación
- Posible reducción del uso de recursos del clúster

**Cargas que necesitan planificación en grupo:**
1. **Entrenamiento distribuido**: Frameworks como TensorFlow y PyTorch
2. **Procesamiento de datos distribuido**: Frameworks como Spark y Flink
3. **Trabajos MPI**: Cargas de computación de alto rendimiento, o HPC
4. **Trabajos paralelos estrechamente relacionados**: Cargas que necesitan un conjunto mínimo declarado de procesos de trabajo

**Por qué las otras opciones son incorrectas:**
- A. Ubicar los Pods únicamente en nodos concretos: Es la función de los selectores de nodos o de la afinidad de nodo.
- C. Distribuir los Pods de manera uniforme: Es la función de las restricciones de distribución topológica de Pods.
- D. Planificar los Pods según su prioridad: Es la función de la prioridad y la preempción.
</details>

### 4. ¿Qué función no forma parte del contrato de callbacks de un extender de kube-scheduler?

A. Filtrar los nodos candidatos
B. Asignar prioridades a los nodos candidatos
C. Vincular opcionalmente un Pod a un nodo
D. Validar la admisión mediante ValidatingWebhookConfiguration

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Validar la admisión mediante ValidatingWebhookConfiguration**

Un extender puede implementar los callbacks configurados de filtrado, priorización, preempción y vinculación. Ninguna ruta literal de URL es obligatoria: `filterVerb` podría incluso definir una ruta llamada `validate`, pero su contenido y significado seguirían correspondiendo al filtrado. Los webhooks de admisión tienen un contrato de API distinto.

**Configuración:**
Reutilice los requisitos del servicio TLS y de los certificados de la Parte 2. `extenders` se configura en el nivel superior. Mantenga el filtrado obligatorio de modo que rechace los intentos si falla, y conserve la contabilidad de recursos del propio scheduler.

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

**Contrato de solicitudes y respuestas:**
* Filter y prioritize usan `ExtenderArgs` con `Pod` y con `Nodes` completos o `NodeNames`, según `nodeCacheCapable`.
* Filter devuelve `Nodes` o `NodeNames`, mapas de fallos y `Error`.
* Prioritize devuelve directamente un array, por ejemplo `[{"Host":"node-a","Score":7}]`; las puntuaciones van de 0 a 10, no hasta 100. Si la priorización falla, se omiten las puntuaciones de ese extender; por tanto, estas no pueden imponer restricciones obligatorias.
* Bind usa `PodName`, `PodNamespace`, `PodUID` y `Node`. Devuelva un resultado satisfactorio solo después de que la vinculación real se complete; una función de relleno `customBind` que devuelve nil no implementa la vinculación.
* Preempt usa `ExtenderPreemptionArgs` con los mapas de candidatos y víctimas, y devuelve `ExtenderPreemptionResult.NodeNameToMetaVictims`. No devuelve una estructura inventada `podsToPreempt`.

Use el manejador completo con límites de la [Parte 2](../../scheduling/02-custom-scheduler-part2.md). Este deja `bindVerb` sin configurar para conservar `DefaultBinder`. Aquí no se proporciona otro servidor HTTP ni un endpoint de vinculación que informe falsamente de éxito.
</details>

### 5. ¿Qué función cumple el punto de extensión "PostFilter" del framework de planificación de Kubernetes?

A. Asignar puntuaciones a los nodos después del filtrado
B. Vincular Pods a nodos después del filtrado
C. Ejecutar la lógica de preempción cuando el filtrado falla
D. Actualizar el estado del Pod después del filtrado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ejecutar la lógica de preempción cuando el filtrado falla**

**Explicación:**
PostFilter intenta recuperar la planificación cuando el filtrado no encuentra ningún nodo factible; la preempción predeterminada es una de sus implementaciones. Cuando todos los nodos quedan excluidos y el Pod no puede planificarse, sus plugins pueden intentar acciones que hagan viable un intento posterior.

**Funciones principales del punto de extensión PostFilter:**
1. **Identificar candidatos a la preempción**: Identifica los Pods y nodos que pueden participar.
2. **Simular la preempción**: Comprueba si el Pod podría planificarse después de desalojar las víctimas.
3. **Decidir la preempción**: Determina la estrategia óptima.

**Interfaz de la versión indicada y extensión adecuada:**
La API fijada usa `fwk.CycleState` y `fwk.NodeToStatusReader`; `PostFilterResult` incorpora `NominatingInfo`. Una nominación indica un posible destino para el siguiente intento, no una vinculación ya confirmada.

Conserve `DefaultPreemption`, la implementación predeterminada, salvo que disponga de una alternativa completa y probada. Evalúa víctimas de menor prioridad frente a las restricciones restantes e intenta evitar incumplimientos de PDB, sin garantizarlo. Un bucle que omite la selección de víctimas y elimina directamente los Pods no es una alternativa segura. Los plugins de recuperación pueden realizar otras acciones apropiadas: PostFilter no se limita por definición a la preempción.

La siguiente configuración ajusta la implementación predeterminada sin deshabilitarla. Los límites de candidatos acotan la búsqueda; no garantizan un resultado globalmente óptimo ni que el Pod llegue a planificarse.

**Opciones relacionadas con la preempción:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: DefaultPreemption
    args:
      minCandidateNodesPercentage: 10
      minCandidateNodesAbsolute: 100
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Proceso de preempción:**
1. Se invoca PostFilter cuando el Pod no supera el filtrado en ningún nodo.
2. El plugin identifica los nodos candidatos.
3. Determina qué Pods deben desalojarse en cada nodo.
4. Comprueba que el Pod pueda planificarse después.
5. Selecciona la estrategia óptima.
6. Establece el nodo elegido como nominatedNodeName del Pod.
7. Los Pods desalojados terminan de forma ordenada.
8. Cuando las víctimas terminan, se reintenta la planificación; la nominación no garantiza la vinculación.

**Monitorización de métricas de preempción:**
```bash
# Inspect nominations; scheduler metrics require its authenticated HTTPS endpoint.
kubectl get pods -A -o custom-columns=NAME:.metadata.name,NOMINATED:.status.nominatedNodeName
```

**Consultar eventos de preempción:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Por qué las otras opciones son incorrectas:**
- A. Asignar puntuaciones después del filtrado: Es la función de "Score".
- B. Vincular Pods a nodos después del filtrado: Es la función de "Bind".
- D. Actualizar el estado del Pod: No es un punto de extensión del framework de planificación.
</details>

### 6. ¿Cuál es el objetivo principal del plugin "NodeResourcesBalancedAllocation" del scheduler de Kubernetes?

A. Puntuar mejor los nodos con fracciones equilibradas de CPU y memoria solicitadas
B. Puntuar mejor los nodos con menor uso de recursos
C. Puntuar mejor los nodos con mayor uso de recursos
D. Establecer límites de recursos en los nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Puntuar mejor los nodos con fracciones equilibradas de CPU y memoria solicitadas**

**Explicación:**
`NodeResourcesBalancedAllocation` equilibra las **fracciones de recursos efectivamente solicitados respecto a los asignables**, no el uso medido de CPU y memoria. Para dos recursos incluidos en la implementación fijada:

```
cpuFraction = min(requestedCPU / allocatableCPU, 1)
memoryFraction = min(requestedMemory / allocatableMemory, 1)
std = abs(cpuFraction - memoryFraction) / 2
score = int((1 - std) * 100)
```

Los totales solicitados incluyen el Pod entrante y las solicitudes contabilizadas por el scheduler. El plugin completo también gestiona las opciones de recursos propias de su versión. Cuando se incluyen más de dos recursos, usa la desviación estándar poblacional.

Estos son cálculos ilustrativos, no mediciones: las fracciones 80 %/80 % dan una puntuación de 100; 90 %/50 %, de 80; y 30 %/90 %, de 70. Los demás plugins y sus pesos también influyen en la selección del nodo.

**Habilitar NodeResourcesBalancedAllocation en la configuración del scheduler:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Configuración del plugin:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: NodeResourcesBalancedAllocation
    args:
      resources:
      - name: cpu
        weight: 1
      - name: memory
        weight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**NodeResourcesBalancedAllocation frente a otras estrategias de puntuación:**
1. **NodeResourcesBalancedAllocation**: Prefiere fracciones equilibradas de recursos solicitados respecto a los asignables.
2. **NodeResourcesFit**: Usa la estrategia configurada: LeastAllocated, MostAllocated o RequestedToCapacityRatio.
3. **Estrategia LeastAllocated de NodeResourcesFit**: Prefiere fracciones solicitadas más bajas.
4. **Estrategia MostAllocated de NodeResourcesFit**: Prefiere fracciones solicitadas más altas.

**Casos de uso:**
1. **Equilibrio de recursos**: Mejora el equilibrio de CPU y memoria en el clúster.
2. **Reducir desequilibrios**: Puede reducir el desequilibrio entre los recursos solicitados; no evita los cuellos de botella durante la ejecución.
3. **Mejorar la escalabilidad**: Los clústeres con un uso equilibrado de recursos pueden escalar con mayor eficiencia.

**Funciones auxiliares de cálculo (`scoring/formulas.go`):**
Comprueban la fórmula y la ponderación opcional 70:30 para GPU descrita en el capítulo de origen. No constituyen un plugin completo de scheduler. Mantenga la contabilidad de recursos integrada, incluidos los milicores de CPU, los contenedores de inicialización y sidecar, la sobrecarga y el tratamiento específico de las funciones habilitadas.

```go
package scoring

import (
	"fmt"
	"math"
)

// Two-resource form of the pinned BalancedAllocation formula.
// Inputs are effective requested/allocatable fractions, not live utilization.
func BalancedScore(cpuFraction, memoryFraction float64) (int64, error) {
	for _, value := range []float64{cpuFraction, memoryFraction} {
		if math.IsNaN(value) || math.IsInf(value, 0) || value < 0 {
			return 0, fmt.Errorf("fractions must be finite and non-negative")
		}
	}
	cpuFraction = math.Min(cpuFraction, 1)
	memoryFraction = math.Min(memoryFraction, 1)
	std := math.Abs(cpuFraction-memoryFraction) / 2
	return int64((1 - std) * 100), nil
}

// Optional policy arithmetic only; no GPU telemetry collector is implemented here.
// The caller must establish freshness and workload/device relevance first.
func WeightedGPUScore(packing int64, utilization float64) (int64, error) {
	if packing < 0 || packing > 100 || math.IsNaN(utilization) || math.IsInf(utilization, 0) || utilization < 0 || utilization > 1 {
		return 0, fmt.Errorf("packing must be 0..100 and utilization finite in 0..1")
	}
	utilizationScore := int64((1 - utilization) * 100)
	return (packing*7 + utilizationScore*3) / 10, nil
}
```

**Por qué las otras opciones son incorrectas:**
- B. Puntuar mejor los nodos con menor uso de recursos: Corresponde a la estrategia LeastAllocated de NodeResourcesFit.
- C. Puntuar mejor los nodos con mayor uso de recursos: Corresponde a la estrategia MostAllocated de NodeResourcesFit.
- D. Establecer límites de recursos: No es la función de los plugins de planificación; los límites son propiedades de los propios nodos.
</details>

### 7. ¿Qué función cumple el punto de extensión "PreBind" del scheduler de Kubernetes?

A. Vincular Pods a nodos
B. Realizar las operaciones necesarias antes de la vinculación
C. Realizar la limpieza después de la vinculación
D. Realizar operaciones de recuperación cuando la vinculación falla

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Realizar las operaciones necesarias antes de la vinculación**

**Explicación:**
PreBind coordina los requisitos previos antes de confirmar la vinculación del Pod. `VolumeBinding` coordina con los controladores de almacenamiento la vinculación y el aprovisionamiento de volúmenes relacionados con la planificación. No existe un plugin predeterminado llamado `DefaultPreBind`.

La interfaz de 1.35.8 incluye **tanto** `PreBindPreFlight` como `PreBind`, y usa `fwk.CycleState`. La comprobación previa puede devolver Skip para evitar trabajo innecesario para un Pod.

**Demostración completa mediante consultas (`quizplugins/prebind.go`):**
Esta comprobación de identidad opcional no aprovisiona volúmenes, configura CNI, crea endpoints de servicios ni asigna GPU. Esas tareas requieren sus controladores o mecanismos de dispositivos correspondientes. `DefaultBinder` ya incluye el UID; esta consulta adicional a la API solo muestra cómo usar la interfaz.

```go
package quizplugins

import (
	"context"
	"fmt"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type IdentityPreBind struct{ handle fwk.Handle }

var _ fwk.PreBindPlugin = &IdentityPreBind{}

func (*IdentityPreBind) Name() string { return "IdentityPreBind" }

func (*IdentityPreBind) PreBindPreFlight(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	if pod.Annotations["training.example.com/check-identity"] != "true" {
		return fwk.NewStatus(fwk.Skip)
	}
	return nil
}

// Read-only interface demonstration. DefaultBinder already carries the Pod UID;
// this extra API round trip is not required for ordinary scheduling.
func (p *IdentityPreBind) PreBind(parent context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	ctx, cancel := context.WithTimeout(parent, 3*time.Second)
	defer cancel()
	current, err := p.handle.ClientSet().CoreV1().Pods(pod.Namespace).Get(ctx, pod.Name, metav1.GetOptions{})
	if err != nil {
		return fwk.AsStatus(err)
	}
	if current.UID != pod.UID || current.DeletionTimestamp != nil || current.Spec.NodeName != "" {
		return fwk.AsStatus(fmt.Errorf("Pod identity/state changed before binding"))
	}
	return nil
}

func NewPreBind(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &IdentityPreBind{handle: handle}, nil
}
```

El comando de la pregunta 2 lo registra. Mantenga `VolumeBinding` habilitado:

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
    preBind:
      enabled:
      - name: IdentityPreBind
```

**Límites de responsabilidad:**
El provisionador o controlador correspondiente aprovisiona el almacenamiento; el scheduler coordina su ubicación y vinculación. La red CNI y los montajes de Secrets y volúmenes se configuran mediante el runtime y kubelet después de la asignación. Los controladores de Service, EndpointSlice y balanceadores de carga reconcilian sus propios recursos. Si un plugin personalizado coordina una reserva externa, debe implementar operaciones limitadas e idempotentes y su propia limpieza Unreserve; el framework no puede deshacer automáticamente cualquier efecto externo.

**Gestión de fallos de PreBind:**
Cuando un plugin PreBind devuelve un fallo:
1. Se aborta el ciclo de planificación.
2. El Pod vuelve a la cola de planificación.
3. Los hooks Unreserve deshacen las reservas supuestas que pertenecen al plugin; la limpieza externa debe implementarse expresamente.
4. Se registran eventos de fallo.

**Monitorización de logs y eventos de PreBind:**
```bash
# Check PreBind-related messages in scheduler logs
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100

# Check pod events
kubectl describe pod <pod-name>
```

**Por qué las otras opciones son incorrectas:**
- A. Vincular Pods a nodos: Es la función de "Bind".
- C. Realizar la limpieza después de la vinculación: Es la función de "PostBind".
- D. La recuperación tras un fallo incluye Unreserve para las reservas del plugin y la gestión de reintentos del framework.
</details>

### 8. ¿Cuál es el objetivo principal del plugin "NodeResourcesFit" del scheduler de Kubernetes?

A. Monitorizar el uso de recursos del nodo
B. Establecer los límites de recursos del nodo
C. Comparar los recursos asignables restantes con las solicitudes efectivas del Pod
D. Mantener el equilibrio del uso de recursos del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Comparar los recursos asignables restantes con las solicitudes efectivas del Pod**

**Explicación:**
`NodeResourcesFit` compara las solicitudes efectivas del Pod con los recursos asignables **menos las solicitudes asignadas o supuestas**, y aplica las restricciones correspondientes de número de Pods y recursos extendidos. Por lo general, no comprueba la suma de los límites de CPU y memoria frente a la capacidad. Deben contabilizarse las solicitudes derivadas de la admisión o de valores predeterminados, los contenedores de inicialización, los sidecars reiniciables, la sobrecarga y las funciones de recursos habilitadas.

Conserve la fase Filter predeterminada. La configuración modifica la puntuación sin sustituir la comprobación de recursos.

**Configuración del plugin NodeResourcesFit:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
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
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Estrategias de puntuación:**
El plugin NodeResourcesFit admite las siguientes estrategias:

1. **LeastAllocated**: Puntúa mejor las fracciones solicitadas más bajas.
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**: Puntúa mejor las fracciones solicitadas más altas.
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**: Usa una curva lineal por tramos configurada sobre las proporciones de recursos solicitados respecto a los asignables. Las fórmulas anteriores son ejemplos simplificados para un solo recurso.

**Precauciones con una implementación personalizada:**
Conserve `NodeResourcesFit` del proyecto upstream. Comprobar solo los recursos de un mapa de pesos de puntuación puede omitir un recurso requerido; además, CPU `Quantity.Value()` pierde la precisión de milicores. Sumar solo las solicitudes de los contenedores convencionales omite el comportamiento de los contenedores de inicialización, los sidecars y la sobrecarga. Una puntuación escrita a mano que trunca las fracciones antes de escalarlas puede devolver únicamente ceros.

La comprobación local de la Parte 1 usa la función real de ajuste de recursos de la versión fijada: si ya se han solicitado 1500m en un nodo de 2 núcleos, otra solicitud de 1 núcleo no cabe, mientras que una de 250m sí cabe aunque tenga límites de CPU mayores. Es una prueba sintética de contabilidad, no un benchmark de clúster.

**Ejemplo de solicitudes y límites de recursos:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "512Mi"
```

**Por qué las otras opciones son incorrectas:**
- A. Monitorizar el uso de recursos del nodo: Es la función de los servidores de métricas o sistemas de monitorización.
- B. Establecer límites de recursos del nodo: Es la función de la configuración del nodo o de kubelet.
- D. Mantener el equilibrio del uso de recursos: Es la función de "NodeResourcesBalancedAllocation".
</details>

### 9. ¿Cuál es el objetivo principal del plugin "InterPodAffinity" del scheduler de Kubernetes?

A. Procesar las reglas de afinidad entre Pods y nodos
B. Procesar las reglas de afinidad y antiafinidad entre Pods
C. Procesar las reglas de afinidad entre Pods y volúmenes
D. Procesar las reglas de afinidad entre Pods y servicios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Procesar las reglas de afinidad y antiafinidad entre Pods**

**Explicación:**
"InterPodAffinity" procesa las reglas de afinidad y antiafinidad entre Pods. Determina si los Pods deben ubicarse en el mismo dominio de topología que otros Pods, como un nodo, una zona o una región, o en dominios distintos.

**Funciones principales del plugin InterPodAffinity:**
1. **Procesar la afinidad de Pod**: Exige que el Pod se ubique en el mismo dominio de topología que otros Pods con determinadas etiquetas.
2. **Procesar la antiafinidad de Pod**: Exige un dominio de topología distinto del de otros Pods con determinadas etiquetas.
3. **Considerar los dominios de topología**: Tiene en cuenta niveles como nodos, zonas y regiones.

**Tipos de afinidad y antiafinidad de Pod:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Reglas que deben cumplirse para planificar el Pod; son requisitos obligatorios.
2. **preferredDuringSchedulingIgnoredDuringExecution**: Reglas preferidas, pero no obligatorias.

**Ejemplo de afinidad y antiafinidad de Pod:**
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
    image: nginx:1.30.6
```

**Configuración del plugin InterPodAffinity:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
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
        weight: 2
  pluginConfig:
  - name: InterPodAffinity
    args:
      hardPodAffinityWeight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Usar la implementación integrada completa:**
Conserve `InterPodAffinity` y su procesamiento previo. Tiene en cuenta la selección de namespaces, los términos obligatorios del Pod entrante, la antiafinidad obligatoria de los Pods existentes, la topología y el arranque de grupos con autoafinidad. Un objeto `*v1.Affinity` sin adaptar no es un StateData del framework con Clone; la ausencia de estado no debe omitir silenciosamente las comprobaciones obligatorias.

En este ejemplo debe existir un Pod `app=cache` adecuado en el namespace seleccionado. La antiafinidad preferida no garantiza la separación. `hardPodAffinityWeight` influye en la puntuación y no relaja las restricciones obligatorias. Pruebe las decisiones de escala y ubicación con cargas reales; ubicar los Pods juntos no demuestra que se consiga una latencia mínima.

**Casos de uso de la afinidad y antiafinidad de Pod:**
1. **Alta disponibilidad**: Distribuir las instancias de una aplicación entre distintos nodos, zonas o regiones.
2. **Optimización del rendimiento**: Ubicar juntos los Pods que se comunican cuando las mediciones respaldan el equilibrio entre contención y latencia.
3. **Aislamiento de recursos**: Distribuir los Pods que consumen muchos recursos entre distintos nodos.
4. **Restricciones de licencia**: Concentrar en nodos concretos las aplicaciones con restricciones de licencia.

**Efecto de la afinidad y antiafinidad de Pod en el rendimiento:**
Estas reglas pueden exigir mucho cálculo porque consideran los nodos y Pods. En clústeres grandes pueden afectar al rendimiento de la planificación; úselas con cuidado.

**Por qué las otras opciones son incorrectas:**
- A. Procesar reglas de afinidad entre Pods y nodos: Es la función de "NodeAffinity".
- C. Procesar reglas de afinidad entre Pods y volúmenes: Es la función de "VolumeBinding".
- D. Procesar reglas de afinidad entre Pods y servicios: No es un plugin del scheduler de Kubernetes.
</details>

### 10. ¿Cuál es el objetivo principal del plugin "NodeName" del scheduler de Kubernetes?

A. Comprobar que el campo spec.nodeName del Pod coincida con el nombre del nodo
B. Asignar nombres a los nodos
C. Asignar nombres de nodos a los Pods
D. Validar el formato del nombre de nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Comprobar que el campo spec.nodeName del Pod coincida con el nombre del nodo**

**Explicación:**
"NodeName" comprueba que el campo `spec.nodeName` del Pod coincida con el nombre del nodo. Si se invoca con un nodeName no vacío, su predicado solo acepta ese nombre. En el funcionamiento habitual, los Pods ya asignados quedan excluidos de la cola de Pods sin planificar; el plugin no es lo que provoca que se omita la planificación.

**Funciones principales del plugin NodeName:**
1. **Comprobar el nombre del nodo**: Si se define `spec.nodeName`, solo se seleccionan nodos con el mismo nombre.
2. **Significado del campo**: spec.nodeName indica directamente el nodo; no selecciona un scheduler.
3. **Omitir el scheduler**: Los Pods con `spec.nodeName` definido omiten la planificación normal y se asignan directamente al nodo indicado.

**Predicado equivalente a la comprobación del nombre:**
Esta función auxiliar ilustra la comprobación integrada; no registre un plugin de reemplazo llamado `NodeName`.

```go
package quizplugins

import v1 "k8s.io/api/core/v1"

// Equivalent name predicate for explanation; not a replacement scheduler.
func NodeNameMatches(pod *v1.Pod, node *v1.Node) bool {
	if pod == nil || node == nil {
		return false
	}
	return pod.Spec.NodeName == "" || pod.Spec.NodeName == node.Name
}
```

**Ejemplo de Pod con nodeName:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  nodeName: worker-node-1  # Direct assignment to specific node
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**Aspectos que deben considerarse al usar nodeName:**
1. **Omitir el scheduler**: Usar `nodeName` omite el filtrado, la puntuación y las demás comprobaciones del scheduler.
2. **Existencia del nodo**: Un nombre incorrecto o inexistente no provoca la selección de otro nodo.
3. **La admisión sigue aplicándose**: Se omiten las comprobaciones de recursos del scheduler, pero kubelet todavía puede rechazar el Pod si no hay recursos suficientes.
4. **Restricciones restantes**: Se omiten NoSchedule y las comprobaciones de afinidad de la planificación, pero siguen aplicándose NoExecute y la admisión del nodo. Los PVC con WaitForFirstConsumer pueden permanecer en Pending porque se ha omitido la coordinación de volúmenes del scheduler.

La etiqueta `kubernetes.io/hostname` no tiene por qué coincidir con el nombre del objeto Node. Consulte su valor real antes de usar los siguientes ejemplos de etiquetas.

**nodeName frente a nodeSelector y nodeAffinity:**
1. **nodeName**: Asigna directamente un nodo concreto. Es la opción más restrictiva y menos flexible.
2. **nodeSelector**: Selecciona nodos por sus etiquetas. Es sencillo, pero tiene una expresividad limitada.
3. **nodeAffinity**: Permite reglas de selección más complejas. Es la opción más flexible y expresiva.

**Casos de uso de nodeName:**
1. **Depuración**: Ejecutar Pods en nodos concretos para investigar problemas.
2. **Pruebas**: Ejecutar pruebas en nodos concretos.
3. **Hardware especial**: Asignar Pods a nodos que disponen de hardware específico.
4. **Distinción respecto a un Pod estático**: Un Pod creado mediante la API con nodeName no es un Pod estático; estos proceden de la configuración local de kubelet.

**Precauciones al usar nodeName:**
1. **Comportamiento de los reemplazos**: Los Pods no se trasladan. Un controlador puede crear reemplazos, pero una plantilla fijada al mismo nombre de nodo averiado sigue restringiendo su ubicación.
2. **Escalabilidad limitada**: Los nombres de nodo se fijan en la definición, lo que limita la escalabilidad.
3. **Mantenimiento más difícil**: Las definiciones deben actualizarse si cambian los nombres de los nodos.
4. **Sin reparto de carga**: No se aprovechan las funciones de reparto de carga del scheduler.

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
       image: nginx:1.30.6
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
       image: nginx:1.30.6
   ```

**Por qué las otras opciones son incorrectas:**
- B. Asignar nombres a los nodos: Se asignan cuando se crea el nodo; no es la función de los plugins de planificación.
- C. Asignar nombres de nodos a los Pods: Ocurre en la fase de vinculación del scheduler, no en NodeName.
- D. Validar el formato del nombre de nodo: Es la función de la validación del servidor de API, no de los plugins del scheduler.
</details>

### 11. ¿Qué controlador usa el coste de eliminación de Pod como preferencia al reducir réplicas?

A. La eliminación por ordinal de StatefulSet
B. ReplicaSet, incluidos los que pertenecen a Deployments
C. La eliminación de cualquier Pod independiente
D. Un scheduler global que clasifica todos los Pods de distintos Deployments

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. ReplicaSet, incluidos los que pertenecen a Deployments**

La anotación se compara dentro de un mismo ReplicaSet y se aplica sin garantías. Si falta, su valor es 0; se admiten valores int32 con signo, incluidos los negativos. La asignación, la fase y el estado de preparación pueden tener precedencia: un Pod de coste alto que no esté preparado puede eliminarse antes que otro de coste menor que sí lo esté. La función estaba en alfa en 1.21 y es beta, habilitada de forma predeterminada, desde 1.22.
</details>

### 12. ¿Qué patrón para actualizar el coste de eliminación coincide con el capítulo de origen?

A. Un coste alto y un PDB garantizan que una réplica sobreviva a una reducción normal de réplicas
B. Sustituir el Pod completo por cada solicitud entrante
C. Cambiar solo el coste en transiciones relevantes, comprobar el UID del Pod y rechazar métricas obsoletas
D. Tratar las métricas no disponibles como actividad nula y reducir inmediatamente el coste

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Cambiar solo el coste en transiciones relevantes, comprobar el UID del Pod y rechazar métricas obsoletas**

Use un único escritor autorizado, solicitudes limitadas y un parche mínimo de la anotación. La comprobación del UID evita modificar por error un Pod nuevo que tenga el mismo nombre. Una simulación de escalado en el servidor no predice qué Pods se eliminarán. La reducción normal de réplicas de ReplicaSet elimina los Pods directamente y no queda bloqueada por un PDB; el drenaje de la aplicación, su estado de preparación y la recuperación siguen siendo necesarios.
</details>

## Referencias

El código usa el [módulo de la Parte 1](../../scheduling/01-custom-scheduler-part1.md). Las pruebas locales de código y configuración no demuestran que exista un sistema de aprobación desplegado, una carga en grupo, ejecución en GPU ni una configuración preparada para producción.

* [Framework de planificación](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Interfaces del framework para la versión fijada](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Configuración del scheduler](https://kubernetes.io/docs/reference/scheduling/config/)
* [Planificación nativa de PodGroup](https://kubernetes.io/docs/concepts/scheduling-eviction/podgroup-scheduling/)
* [Políticas de PodGroup](https://kubernetes.io/docs/concepts/workloads/workload-api/policies/)
* [Job de Volcano](https://volcano.sh/en/docs/vcjob/)
* [CRD de Job de Volcano 1.15.2](https://github.com/volcano-sh/volcano/blob/v1.15.2/config/crd/volcano/bases/batch.volcano.sh_jobs.yaml)
* [Puntuación de BalancedAllocation](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/framework/plugins/noderesources/balanced_allocation.go)
* [Asignación de nodos](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [Coste de eliminación en ReplicaSet](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
