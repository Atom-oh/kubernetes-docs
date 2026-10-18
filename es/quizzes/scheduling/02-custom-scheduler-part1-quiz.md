# Cuestionario sobre Custom Scheduler (parte 1)

> **Base del ejemplo**: Kubernetes 1.35.8, Go 1.27.2
> **Última actualización**: 16 de octubre de 2026

Este cuestionario comprueba tu comprensión de la implementación y el uso de schedulers personalizados en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Cuál es la función principal de un scheduler en Kubernetes?

A. Crear y eliminar pods
B. Asignar pods a los nodos adecuados
C. Supervisar los recursos de los nodos
D. Descargar imágenes de contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Asignar pods a los nodos adecuados**

**Explicación:**
La función principal del scheduler de Kubernetes es asignar los pods a los nodos adecuados. El scheduler observa los pods nuevos y busca el mejor nodo para ejecutar los que aún no tienen un nodo asignado.

**Funciones principales del scheduler:**
1. **Asignación de pods a nodos**: elige el nodo más adecuado teniendo en cuenta los requisitos del pod y los recursos disponibles del nodo.
2. **Filtrado**: excluye los nodos que no pueden ejecutar el pod, por ejemplo, por falta de recursos o por taints incompatibles.
3. **Puntuación**: puntúa los nodos aptos para elegir el más adecuado.
4. **Binding**: vincula el pod al nodo seleccionado para finalizar la decisión de programación.

**Proceso de programación (Kubernetes 1.35.8):**
1. **Filtrado**: `NodeResourcesFit` compara las solicitudes efectivas de recursos con los recursos asignables restantes; `NodePorts` comprueba los host ports solicitados; `NodeAffinity` gestiona selectores y afinidad de nodo; `TaintToleration` comprueba los taints. Complementos de volumen como `VolumeBinding`, `VolumeZone` y `NodeVolumeLimits` aplican las restricciones de almacenamiento. La presión del nodo se refleja en sus condiciones/taints; nombres como `CheckNodeDiskPressure` corresponden a predicados históricos, no a complementos configurables actuales.
2. **Puntuación**: `NodeResourcesFit` (con `LeastAllocated` de forma predeterminada), `NodeResourcesBalancedAllocation`, `NodeAffinity`, `InterPodAffinity`, `PodTopologySpread`, `TaintToleration` e `ImageLocality` contribuyen preferencias. No todos miden la utilización actual de recursos.
3. **Binding**: cuando se completan las demás fases del framework, el scheduler registra la asignación del nodo. Después, kubelet y el runtime administran la ejecución. Una puntuación alta no garantiza que el pod arranque, tenga baja latencia o esté disponible.

**Ejemplo de configuración de un scheduler secundario:**
Esto cambia el peso de puntuación y conserva los filtros predeterminados. En este cuestionario, las configuraciones son archivos que se consumen con `--config`, no recursos de la API de Kubernetes que se apliquen con `kubectl`.
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
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

**Por qué las otras opciones no son correctas:**
- A. Crear y eliminar pods: corresponde principalmente al controller manager y al API server.
- C. Supervisar los recursos de los nodos: corresponde principalmente a kubelet y Metrics Server.
- D. Descargar imágenes de contenedor: corresponde a kubelet y al runtime de contenedores.
</details>

### 2. ¿Cuál de las siguientes opciones NO es un método para implementar un scheduler personalizado?

A. Ampliar el kube-scheduler existente
B. Implementar un scheduler completamente nuevo
C. Desarrollar un complemento del scheduling framework
D. Modificar kubelet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Modificar kubelet**

**Explicación:**
Modificar kubelet no es un método para implementar un scheduler personalizado. kubelet es un agente que se ejecuta en cada nodo y administra la ejecución de los pods, pero no toma decisiones de programación. Estas decisiones corresponden a kube-scheduler o a schedulers personalizados.

**Métodos para implementar un scheduler personalizado:**

1. **Configurar un scheduler secundario basado en kube-scheduler**: conserva los complementos predeterminados y ajusta solo el comportamiento necesario. La parte 1 proporciona un comando, RBAC, ConfigMap y Deployment completos.

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
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

2. **Implementar un scheduler independiente**: requiere una caché, cola, recuperación de list/watch, contabilidad de recursos, coordinación de volúmenes, reintentos, elección de líder y binding correctos. Un bucle que solo observa eventos no detecta los pods existentes y falla durante las desconexiones; en producción conviene usar informers/workqueues y gestionar tombstones, cancelación y objetos obsoletos. Elegir un nodo Ready no demuestra que el pod quepa en él. Por eso, el ejemplo de la parte 1 delega estas responsabilidades al kube-scheduler upstream.

3. **Desarrollar un complemento del framework**: compila el complemento dentro del binario del scheduler y regístralo con `app.WithPlugin`. La pregunta 4 incluye un complemento Filter completo, la pregunta 6 uno de tipo Score y la pregunta 7 el comando de registro. Sus interfaces corresponden a `k8s.io/kube-scheduler/framework` v0.35.8; las firmas varían entre versiones menores de Kubernetes.

**Función de kubelet:**
kubelet es un agente que se ejecuta en cada nodo y desempeña estas funciones:
- Ejecutar y administrar contenedores según las especificaciones de los pods.
- Supervisar e informar sobre el estado del nodo.
- Realizar comprobaciones de salud de los contenedores.
- Administrar los montajes de volúmenes.

kubelet ejecuta las decisiones del scheduler (qué pod se ejecuta en qué nodo), pero no decide dónde programar los pods.

**Por qué las otras opciones sí son válidas:**
- A. Ampliar el kube-scheduler existente: es un método válido para implementar un scheduler personalizado.
- B. Implementar un scheduler completamente nuevo: es un método válido para implementar un scheduler personalizado.
- C. Desarrollar un complemento del scheduling framework: es un método válido para implementar un scheduler personalizado.
</details>

### 3. ¿Qué campo de un pod especifica un scheduler concreto?

A. spec.scheduler
B. spec.schedulerName
C. metadata.scheduler
D. spec.nodeName

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. spec.schedulerName**

**Explicación:**
El campo para especificar un scheduler concreto en un pod es `spec.schedulerName`. Cuando se establece, el pod solo lo programa el scheduler cuyo nombre se indica. Su valor predeterminado es "default-scheduler".

**Ejemplo de Pod Spec:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
  labels:
    app: my-app
spec:
  schedulerName: custom-scheduler  # Specify custom scheduler
  containers:
  - name: main-container
    image: nginx:1.30.6
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

Este pod solo lo programa el scheduler llamado "custom-scheduler". Si el clúster no tiene un scheduler con ese nombre, el pod permanecerá en estado `Pending`.

**Configuración del nombre del scheduler:**
Usa el Deployment completo de la parte 1 y monta esta configuración en `/etc/scheduler/config.yaml`, con `--config=/etc/scheduler/config.yaml`. `--scheduler-name` no es el mecanismo de configuración actual. Los permisos de ServiceAccount y Lease son requisitos previos.

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
```

**Aspectos que debes tener en cuenta al elegir un scheduler:**
1. **Disponibilidad**: si el scheduler indicado no se está ejecutando, no se programará el pod.
2. **Funcionalidad**: cada scheduler puede tener algoritmos y políticas de programación distintos.
3. **Enrutamiento según política**: `schedulerName` selecciona un perfil de scheduler; por sí solo no proporciona seguridad ni aislamiento de recursos.
4. **Hardware especializado**: se pueden usar schedulers dedicados para hardware como GPU o FPGA.

**Comprobación del estado del scheduler:**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100
```

**Por qué las otras opciones no son correctas:**
- A. spec.scheduler: este campo no existe en la API de Kubernetes.
- C. metadata.scheduler: este campo no existe en la API de Kubernetes.
- D. spec.nodeName: este campo omite el scheduler y asigna directamente un pod a un nodo concreto; no sirve para indicar un scheduler.
</details>
### 4. ¿Qué función cumple el punto de extensión "Filter" del scheduling framework de Kubernetes?

A. Puntuar nodos
B. Vincular pods a nodos
C. Excluir los nodos en los que no se puede ejecutar el pod
D. Ordenar los pods en la cola de programación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Excluir los nodos en los que no se puede ejecutar el pod**

**Explicación:**
La función del punto de extensión "Filter" (antes llamado "Predicate") del scheduling framework es excluir los nodos en los que no se puede ejecutar un pod. Los complementos Filter comprueban si cada nodo cumple los requisitos del pod y eliminan de la lista de candidatos los que no los cumplen.

**Puntos de extensión del scheduling framework:**
* **PreEnqueue / QueueSort**: controlan la admisión a la cola y el orden de los pods en espera.
* **PreFilter / Filter**: preparan el estado compartido y excluyen los nodos inviables.
* **PostFilter**: intenta recuperarse cuando no hay nodos viables, por ejemplo, mediante preemption.
* **PreScore / Score / NormalizeScore opcional**: preparan y puntúan los nodos viables; las puntuaciones normalizadas deben estar entre 0 y 100.
* **Reserve / Unreserve**: registran el estado asumido y lo revierten si falla la programación. No asignan físicamente CPU ni dispositivos.
* **Permit**: permite, rechaza o espera antes de continuar.
* **PreBind / Bind / PostBind**: preparan dependencias, confirman el binding y ejecutan tareas posteriores. `PostBind` no puede cancelar un binding ya confirmado. Las interfaces pueden incorporar métodos según la versión; compila para la versión de destino.

**Filtros predeterminados:**
`NodeResourcesFit`, `NodeName`, `NodeUnschedulable`, `NodePorts`, `TaintToleration`, `NodeAffinity`, `InterPodAffinity`, `PodTopologySpread`, `VolumeRestrictions`, `NodeVolumeLimits`, `VolumeBinding` y `VolumeZone` cubren distintas restricciones. Los nombres antiguos de predicados y el nombre específico del proveedor `EBSLimits` ya no son los nombres actuales de los complementos.

**Ejemplo de Filter personalizado (`plugins/filter.go`):**
Esta sencilla regla de etiquetas normalmente se expresaría mediante afinidad de nodo obligatoria. Aquí sirve para mostrar la interfaz del framework. Si falta una etiqueta, no se puede resolver el problema mediante preemption de otros pods, aunque un cambio posterior en las etiquetas del nodo puede permitir que se reintente la programación.

```go
package plugins

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyFilterPlugin struct{}

var _ fwk.FilterPlugin = &MyFilterPlugin{}

func (*MyFilterPlugin) Name() string { return "MyFilterPlugin" }

func (*MyFilterPlugin) Filter(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	if info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "missing node")
	}
	if info.Node().Labels["custom-label"] != "required-value" {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "node lacks required label")
	}
	return nil
}

func NewFilter(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyFilterPlugin{}, nil
}
```

**Habilitar el Filter personalizado junto con los valores predeterminados:**
La pregunta 7 registra este complemento. No deshabilites `NodeResourcesFit` para añadir una comprobación de etiquetas.

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
      - name: MyFilterPlugin
```

**Por qué las otras opciones no son correctas:**
- A. Puntuar nodos: es la función del punto de extensión "Score".
- B. Vincular pods a nodos: es la función del punto de extensión "Bind".
- D. Ordenar los pods en la cola de programación: es la función del punto de extensión "Queue Sort".
</details>

### 5. ¿Qué tarea realizan kubelet y el runtime de contenedores, en vez del scheduler?

A. Evaluar las solicitudes de recursos de los nodos y sus recursos asignables
B. Tener en cuenta la prioridad y preemption de los pods
C. Descargar las capas de imagen y crear contenedores
D. Evaluar la afinidad de nodo y la afinidad entre pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Descargar las capas de imagen y crear contenedores**

**Explicación:**
El scheduler elige un nodo; después, kubelet solicita al runtime que descargue las imágenes y cree los contenedores. **La localidad de imágenes puede influir en la programación**: el complemento predeterminado `ImageLocality` puntúa las imágenes almacenadas en caché que notificó el nodo y sus tamaños. Los informes de caché pueden estar obsoletos y no garantizan que se evite la descarga.

**Aspectos de implementación:**
1. **Recursos**: conserva `NodeResourcesFit`; usa las solicitudes efectivas y el uso asignado/asumido que mantiene la caché del scheduler. Las métricas de CPU/memoria en tiempo real son entradas distintas. Los límites de CPU/memoria pueden sobreasignarse y no forman parte de la comprobación predeterminada de ajuste.
2. **Prioridad**: usa PriorityClass y `preemptionPolicy` deliberadamente. Un pod de prioridad alta puede permanecer en Pending si preemption no puede resolver restricciones de afinidad, volúmenes u otras condiciones.
3. **Ubicación**: la afinidad de nodo obligatoria restringe los nodos aptos; la preferida los puntúa. Sustituye las zonas de disponibilidad del ejemplo siguiente por zonas con capacidad apta real. Los requisitos habituales de GPU y topología no suelen necesitar un scheduler personalizado.

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
            values: [us-east-1a, us-east-1b]
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

4. **Otras restricciones**: conserva taints/tolerations, distribución de topología, topología/límites de conexión del almacenamiento y comprobaciones de recursos de hardware. Modela la localidad de red solo con datos de topología confiables; las etiquetas no demuestran la latencia.
5. **Gestión de imágenes**: `ImageLocality` es una preferencia, no una garantía de capacidad ni de arranque. En el nodo todavía pueden producirse recolección de imágenes, problemas de autenticación del registro y fallos de descarga.

**Las otras opciones:**
A, B y D son consideraciones válidas para la programación. La distinción original es entre ubicar el pod y ejecutar acciones del runtime, no entre programación e información de imágenes.
</details>
### 6. ¿Qué función cumple el punto de extensión "Score" del scheduling framework de Kubernetes?

A. Excluir los nodos en los que no se puede ejecutar el pod
B. Puntuar los nodos que superaron el filtrado
C. Vincular pods a nodos
D. Ordenar los pods en la cola de programación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Puntuar los nodos que superaron el filtrado**

**Explicación:**
La función del punto de extensión "Score" (antes llamado "Priority") es asignar puntuaciones a los nodos que superaron el filtrado. Los complementos de puntuación calculan una puntuación para cada nodo y el scheduler elige en función de ellas.

**Proceso de puntuación:**
1. Cada complemento calcula una puntuación; después de la normalización opcional, debe estar entre 0 y 100.
2. La puntuación de cada complemento se multiplica por su peso configurado.
3. Se suman las puntuaciones ponderadas de todos los complementos.
4. El nodo con la puntuación total más alta se elige para el pod.

**Complementos de puntuación predeterminados:**
Kubernetes proporciona estos complementos de puntuación:

1. **NodeResourcesBalancedAllocation**: prefiere fracciones equilibradas de solicitudes de CPU y memoria, no la utilización medida.
2. **NodeResourcesFit**: aplica la estrategia configurada LeastAllocated, MostAllocated o RequestedToCapacityRatio a las solicitudes y los recursos asignables.
3. **NodeAffinity**: puntúa según las reglas de afinidad de nodo.
4. **InterPodAffinity**: puntúa según las reglas de afinidad/anti-afinidad entre pods.
5. **PodTopologySpread**: favorece los nodos que distribuyen los pods de manera uniforme entre los dominios de topología.
6. **TaintToleration**: penaliza los taints PreferNoSchedule que no se toleran; los taints obligatorios se gestionan al filtrar.
7. **ImageLocality**: da mayor puntuación a los nodos que ya tienen las imágenes necesarias.

**Complemento de puntuación personalizado (`plugins/score.go`):**
En este ejemplo, las etiquetas del nodo son entradas de política administradas por un administrador. Los valores no válidos provocan un error del ciclo de puntuación en lugar de inventar una preferencia. Una puntuación válida de cero no equivale a un filtro.

```go
package plugins

import (
	"context"
	"strconv"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyScorePlugin struct{}

var _ fwk.ScorePlugin = &MyScorePlugin{}

func (*MyScorePlugin) Name() string { return "MyScorePlugin" }

func (*MyScorePlugin) Score(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	value := info.Node().Labels["custom-score-label"]
	if value == "" {
		return 0, nil
	}
	score, err := strconv.ParseInt(value, 10, 64)
	if err != nil || score < fwk.MinNodeScore || score > fwk.MaxNodeScore {
		return 0, fwk.NewStatus(fwk.Error, "custom-score-label must be an integer from 0 to 100")
	}
	return score, nil
}

// Scores are already absolute 0-100 values; no relative rescaling is needed.
func (*MyScorePlugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func NewScore(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyScorePlugin{}, nil
}
```

**Pesos para el ejemplo aritmético de dos complementos:**
El siguiente ejemplo sustituye deliberadamente solo el conjunto de complementos **Score**. Los complementos Filter predeterminados siguen habilitados. En una política real, conserva las demás preferencias de puntuación que necesites.

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
      disabled:
      - name: "*"
      enabled:
      - name: MyScorePlugin
        weight: 5
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

**Ejemplo del resultado de puntuación:**
Es un cálculo ilustrativo, no un resultado medido: supón que A, B y C superaron el filtrado y que los dos complementos habilitados producen estas puntuaciones finales de 0–100:

1. MyScorePlugin (peso: 5)
   - Nodo A: 80 puntos
   - Nodo B: 60 puntos
   - Nodo C: 90 puntos

2. NodeResourcesBalancedAllocation (peso: 2)
   - Nodo A: 70 puntos
   - Nodo B: 90 puntos
   - Nodo C: 50 puntos

Puntuaciones ponderadas totales:
- Nodo A: (80 x 5) + (70 x 2) = 400 + 140 = 540 puntos
- Nodo B: (60 x 5) + (90 x 2) = 300 + 180 = 480 puntos
- Nodo C: (90 x 5) + (50 x 2) = 450 + 100 = 550 puntos

En este caso, el nodo C obtuvo la puntuación más alta, así que el pod se programa en ese nodo.

**Por qué las otras opciones no son correctas:**
- A. Excluir los nodos en los que no se puede ejecutar el pod: es la función del punto de extensión "Filter".
- C. Vincular pods a nodos: es la función del punto de extensión "Bind".
- D. Ordenar los pods en la cola de programación: es la función del punto de extensión "Queue Sort".
</details>

### 7. ¿Cuál de las siguientes opciones NO es un método para ampliar el scheduler de Kubernetes?

A. Complemento del scheduling framework
B. Scheduler extender
C. Desplegar varios schedulers
D. Modificar el node controller

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Modificar el node controller**

**Explicación:**
Modificar el node controller no es una forma de ampliar el scheduler de Kubernetes. El node controller es un componente del plano de control que supervisa y administra el estado de los nodos, pero no participa directamente en las decisiones de programación.

**Métodos de ampliación:**

1. **Complementos del framework**: se ejecutan dentro del scheduler. Guarda los ejemplos Filter/Score completos de las preguntas 4 y 6 en `plugins/`, y guarda este comando como `cmd/with-plugins/main.go`. Compílalo con `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/with-plugins`. Registrar un complemento no lo habilita; la configuración debe hacer referencia a él.

```go
package main

import (
	"os"

	"example.com/custom-scheduler/plugins"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin("MyFilterPlugin", plugins.NewFilter),
		app.WithPlugin("MyScorePlugin", plugins.NewScore),
	)
	os.Exit(cli.Run(command))
}
```

En esta versión, las fábricas reciben `(context.Context, runtime.Object, framework.Handle)`. Estos ejemplos no reciben argumentos personalizados. Si añades configuración, decodifica y valida la carga `runtime.Unknown` con el decodificador runtime versionado del framework; no la conviertas mediante aserción en un tipo personalizado no registrado.

2. **HTTP extenders**: añaden filtrado/priorización externos y, opcionalmente, binding. `extenders` va en el **nivel superior**, no dentro de un perfil. Esta configuración ilustrativa requiere un servicio extender implementado, certificados TLS coincidentes en las rutas montadas indicadas, conectividad de red y gestión de errores acotada. No es un servidor funcional independiente ni una configuración de scheduler administrado de EKS. Si se omite `bindVerb`, se conserva el binder predeterminado.

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
- urlPrefix: https://extender.scheduler-lab.svc:8443
  filterVerb: filter
  prioritizeVerb: prioritize
  weight: 5
  enableHTTPS: true
  tlsConfig:
    caFile: /etc/extender-tls/ca.crt
    certFile: /etc/extender-tls/tls.crt
    keyFile: /etc/extender-tls/tls.key
  httpTimeout: 2s
  nodeCacheCapable: false
  ignorable: false
```

Con `ignorable: false`, si falla el filtrado del extender se bloquea ese intento de programación. Si se estableciera en true, podría omitirse una restricción personalizada obligatoria. Los errores de priorización se gestionan de otra forma: Kubernetes 1.35.8 registra el fallo y omite las puntuaciones de ese extender; por tanto, una puntuación no debe aplicar una regla obligatoria. Cuando sea posible, prefiere un complemento del framework y prueba los timeouts, reintentos y fallos.

3. **Varios schedulers**: usan valores `profiles[].schedulerName` diferentes y grupos de elección de líder separados. Usa el Deployment/RBAC completo de la parte 1 en lugar de iniciar un segundo proceso con la identidad o el Lease del scheduler predeterminado.

**Función del node controller:**
kubelet suele registrar el nodo e informar sobre su estado de salud. Los controladores del ciclo de vida del nodo observan los heartbeats, actualizan condiciones/taints y coordinan la respuesta a los nodos no sanos. Esta información afecta a la programación, pero modificar el node controller no es una API de ampliación del scheduler.

**Cómo elegir un método:**
Evalúa la complejidad de implementación, la sobrecarga HTTP por nodo, la coherencia de la caché, el comportamiento ante fallos y la compatibilidad con actualizaciones. En EKS, despliega un scheduler secundario; no puedes sustituir las opciones ni el registro del scheduler predeterminado administrado.

**Por qué las otras opciones sí son válidas:**
- A. Complemento del scheduling framework: es un método válido para ampliar el scheduler.
- B. Scheduler extender: es un método válido para ampliar el scheduler.
- C. Desplegar varios schedulers: es un método válido para ampliar el scheduler.
</details>
### 8. ¿Para qué sirve el flag `--leader-elect` del scheduler de Kubernetes?

A. Conceder autoridad de liderazgo al scheduler
B. Mantener activa solo una instancia entre varias instancias del scheduler
C. Ejecutar el scheduler únicamente en el nodo líder del clúster
D. Dar al scheduler más prioridad que a otros componentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mantener activa solo una instancia entre varias instancias del scheduler**

**Explicación:**
En una configuración de alta disponibilidad (HA), `--leader-elect` coordina las réplicas del mismo grupo Lease para que solo una instancia del scheduler sea líder y realice el trabajo. No actúa como mecanismo de fencing frente a todos los fallos posibles ni sustituye las operaciones de API seguras para concurrencia.

**Mecanismo de elección de líder:**
1. Si se despliegan varias instancias, un algoritmo de elección designa una como líder.
2. Solo la instancia elegida realiza la programación efectiva.
3. Las demás quedan en espera y, si falla el líder actual, se elige otro.
4. El mecanismo usa bloqueos de recursos de Kubernetes.

**Configuración de elección de líder:**
Usa el archivo de configuración versionado para la identidad del Lease y los tiempos:

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
```

**Despliegue de alta disponibilidad:**
El Deployment completo de la parte 1 ya ejecuta dos réplicas con la misma configuración y ServiceAccount. Para un laboratorio aislado, se puede escalar a tres. Esto no demuestra HA en producción: verifica que haya dominios de fallo separados, acceso a la API, capacidad de arranque y comportamiento de conmutación.

```bash
kubectl -n scheduler-lab scale deployment/custom-scheduler --replicas=3
kubectl -n scheduler-lab get lease custom-scheduler -o yaml
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
```

**Implementaciones personalizadas:**
El comando kube-scheduler ya integra la elección de líder de client-go. Las implementaciones independientes necesitan una identidad única por proceso, un Lease compartido por grupo de schedulers, permisos de renovación y cancelación del trabajo de programación cuando se pierde el liderazgo. El mecanismo de client-go no aplica fencing ante todos los posibles procesos superpuestos; los bindings y efectos externos aún deben diseñarse para admitir concurrencia segura. Con `ReleaseOnCancel`, el trabajo protegido debe detenerse antes de liberar el Lease.

**Cuándo deshabilitar la elección:**
Desactívala solo en un experimento deliberadamente aislado o si otro mecanismo garantiza que haya un único proceso activo, incluidas las actualizaciones y los fallos. `replicas: 1` puede solaparse durante una actualización progresiva. Los nombres de scheduler distintos requieren grupos de elección distintos; el nombre, por sí solo, no hace seguro deshabilitarla.

**Por qué las otras opciones no son correctas:**
- A. Conceder autoridad de liderazgo al scheduler: es una descripción vaga que no explica la finalidad concreta de la elección.
- C. Ejecutar el scheduler únicamente en el nodo líder del clúster: el liderazgo corresponde a un proceso, no a un nodo líder universal. Un scheduler secundario puede ejecutarse como Pod en nodos de trabajo.
- D. Dar al scheduler más prioridad que a otros componentes: la elección de líder no guarda relación con la prioridad; coordina varias instancias del scheduler.
</details>

### 9. ¿Qué recurso se usa en Kubernetes para definir la prioridad de programación de los pods?

A. PodSchedulingPolicy
B. PriorityClass
C. SchedulingPriority
D. PodPriority

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. PriorityClass**

**Explicación:**
El recurso de Kubernetes para definir la prioridad de programación de los pods es `PriorityClass`. Define su importancia relativa y permite que el scheduler la tenga en cuenta al programar y hacer preemption.

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
1. **value**: valor de prioridad; un valor mayor indica mayor prioridad. Los valores definidos por el usuario no pueden superar 1000000000; las clases críticas integradas usan el rango reservado superior.
2. **globalDefault**: si se establece en true, la clase se convierte en el valor predeterminado del clúster para los pods nuevos admitidos sin clase; no modifica retroactivamente los pods existentes. Todas las clases del laboratorio que aparecen abajo usan false.
3. **description**: descripción de la clase de prioridad.
4. **preemptionPolicy**: puede ser `PreemptLowerPriority` (valor predeterminado) o `Never`.

**Aplicar PriorityClass a un pod:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority  # Reference PriorityClass name
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**Comportamiento de prioridad y preemption:**
1. **Prioridad de programación**: los pods de prioridad mayor se procesan antes en la cola de programación.
2. **Preemption**: si ningún nodo puede alojar un pod de prioridad alta, el scheduler puede desalojar pods de prioridad menor para liberar espacio.
3. **Política de preemption**: los pods con `preemptionPolicy: Never` no desalojan a otros, pero ellos sí pueden ser desalojados. El retroceso de la cola puede permitir que se programen pods de menor prioridad mientras un pod de mayor prioridad no puede encajar.

**PriorityClasses del sistema:**
Kubernetes proporciona estas PriorityClasses del sistema:
- **system-cluster-critical**: para pods críticos para el funcionamiento del clúster (valor: 2000000000).
- **system-node-critical**: para pods críticos para el funcionamiento del nodo (valor: 2000001000).

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
globalDefault: false
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

**Supervisar las métricas de prioridad y preemption:**
```bash
# Check preemption events
kubectl get events | grep -i preempt

# Check pod priorities
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**Gestionar la prioridad en un scheduler personalizado:**
Al implementar un scheduler personalizado, debes tener en cuenta la prioridad de los pods al tomar decisiones de programación.

```go
package priorityexample

import (
    "sort"
    v1 "k8s.io/api/core/v1"
)

func podPriority(pod *v1.Pod) int32 {
    if pod == nil || pod.Spec.Priority == nil {
        return 0
    }
    return *pod.Spec.Priority
}

// Demonstrates only priority comparison, not queue backoff or requeue handling.
func sortPodsByPriority(pods []*v1.Pod) {
    sort.SliceStable(pods, func(i, j int) bool {
        return podPriority(pods[i]) > podPriority(pods[j])
    })
}
```

**Por qué las otras opciones no son correctas:**
- A. PodSchedulingPolicy: este recurso no existe en la API de Kubernetes.
- C. SchedulingPriority: este recurso no existe en la API de Kubernetes.
- D. PodPriority: no es un tipo de recurso, sino un campo de la especificación del pod (`spec.priority`). PriorityClass establece este campo automáticamente.
</details>

### 10. ¿Qué función cumple el complemento `NodeResourcesFit` del scheduler de Kubernetes?

A. Ubicar pods según la ubicación física de los nodos
B. Comparar los recursos asignables restantes con las solicitudes efectivas del pod
C. Comprobar la compatibilidad entre el sistema operativo del nodo y el pod
D. Medir el ancho de banda de red del nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comparar los recursos asignables restantes con las solicitudes efectivas del pod**

**Explicación:**
`NodeResourcesFit` compara las solicitudes efectivas del pod con los **recursos asignables del nodo menos las solicitudes ya asignadas/asumidas**. También comprueba el límite de pods y los recursos extendidos pertinentes. No compara simplemente el pod nuevo con toda la `Capacity` ni suele rechazar pods porque la suma de sus límites de CPU/memoria supere la capacidad.

**Contabilidad de recursos:**
* Ten en cuenta los contenedores normales, los init containers secuenciales, los sidecars reiniciables, la sobrecarga del pod y los ajustes de recursos a nivel de pod que admita la versión. Los valores predeterminados de la API pueden derivar las solicitudes de los límites.
* Usa la instantánea del scheduler, incluidos los bindings asumidos; sumar solo los pods Running de una lista de la API omite la demanda reservada.
* Respeta los feature gates y el comportamiento DRA de la versión de destino. La aritmética de CPU/memoria no basta para implementar por completo el ajuste de recursos.

**Configuración:**
`NodeResourcesFit` está habilitado de forma predeterminada. Este ejemplo cambia la estrategia de puntuación sin eliminar su fase Filter.

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

**Estrategias de puntuación:**
El complemento NodeResourcesFit admite estas estrategias:

1. **LeastAllocated**: da mayor puntuación a los nodos con una proporción menor de recursos solicitados. Sirve para distribuir el uso de recursos.
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**: da mayor puntuación a los nodos con una proporción mayor de recursos solicitados. Sirve para concentrar el uso y reducir el número de nodos.
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**: puntúa la proporción de recursos solicitados frente a la capacidad con una forma lineal por tramos configurable. Las fórmulas simplificadas anteriores para un solo recurso omiten el redondeo a enteros, los casos de cero/sobrecapacidad y los pesos de recursos; no representan la utilización en tiempo real.

**Tipos de recursos:**
El complemento NodeResourcesFit considera estos tipos de recursos:

1. **CPU**: se mide en cores o millicores.
2. **Memoria**: se mide en bytes.
3. **Almacenamiento efímero**: almacenamiento efímero local del nodo.
4. **Recursos extendidos**: recursos personalizados, como GPU y FPGA.

**Comprobar los recursos del nodo:**
```bash
# Check node's allocatable resources
kubectl describe node <node-name> | grep Allocatable -A 5

# Check node's resource usage
kubectl top node <node-name>
```

**Comprobar las solicitudes de recursos del pod:**
```bash
# Check pod's resource requests
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**Implementar el ajuste de recursos de forma segura:**
Conserva el complemento upstream dentro del framework del scheduler. Una función escrita a mano que sume la CPU/memoria del pod nuevo, ignore la demanda existente y devuelva true no es una sustitución válida. La auditoría complementaria comprueba localmente la implementación fijada de upstream fit con una solicitud existente de 1500m en un nodo de 2 cores: se rechaza otra solicitud de 1 core, pero cabe una de 250m aunque los límites de CPU sean mayores. Es una comprobación local de contabilidad, no una prueba de rendimiento de programación en un clúster.

`kubectl top` informa de las métricas actuales si Metrics Server está disponible; no muestra los totales de recursos solicitados que usa el ajuste/puntuación predeterminados. Si investigas diferencias, revisa las especificaciones completas de los pods, incluidos init containers y overhead.

**Por qué las otras opciones no son correctas:**
- A. Ubicar pods según la ubicación física de los nodos: corresponde a complementos relacionados con la topología, como NodeAffinity y PodTopologySpread.
- C. Comprobar la compatibilidad entre el sistema operativo del nodo y el pod: usa etiquetas del sistema operativo y restricciones de ubicación cuando sea necesario; por sí solas no demuestran compatibilidad de imagen/runtime. Esa no es la función de `NodeResourcesFit`.
- D. Medir el ancho de banda de red del nodo: el scheduler de Kubernetes no considera el ancho de banda de red de forma predeterminada; para ello hacen falta métricas y complementos personalizados.
</details>

## Referencias

Los ejemplos usan el [módulo y Deployment de la parte 1](../../scheduling/01-custom-scheduler-part1.md). Las comprobaciones locales de compilación/configuración/contabilidad no demuestran que esté listo para producción; no se desplegó nada en un clúster ni en AWS.

* [Configuración del scheduler y complementos predeterminados](https://kubernetes.io/docs/reference/scheduling/config/)
* [Puntos de extensión del framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Puntuación de recursos](https://kubernetes.io/docs/concepts/scheduling-eviction/resource-bin-packing/)
* [Prioridad y preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [Interfaces fijadas de Go](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
