# Cuestionario sobre Custom Scheduler (parte 2)

> **Versiones de referencia del ejemplo**: Kubernetes 1.35.8, Go 1.27.2
> **Última actualización**: 16 de octubre de 2026

Este cuestionario evalúa tu comprensión avanzada de la implementación y el uso de schedulers personalizados en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Cuál es el rol del punto de extensión "Bind" en el framework de planificación de Kubernetes?

A. Vincular Pods a nodos para finalizar las decisiones de planificación
B. Configurar la vinculación de red entre Pods y nodos
C. Crear una vinculación entre Pods y Services
D. Configurar la vinculación entre Pods y volúmenes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Vincular Pods a nodos para finalizar las decisiones de planificación**

**Explicación:**
El punto de extensión Bind vincula los Pods con los nodos seleccionados para confirmar la decisión de planificación. La asignación se registra durante el ciclo de vinculación; después se ejecuta PostBind. Aun así, kubelet puede encontrar fallos de imagen, almacenamiento o ejecución.

**Proceso de vinculación:**
1. El scheduler selecciona el nodo óptimo mediante filtrado y puntuación.
2. Reserva el Pod en el nodo seleccionado (reserve).
3. En la etapa de vinculación, actualiza el campo `spec.nodeName` del Pod con el nombre del nodo seleccionado.
4. La información actualizada del Pod se almacena en el API server.
5. kubelet detecta la información del Pod y ejecuta el Pod en ese nodo.

**Ejemplo de solicitud de vinculación:**
La vinculación ocurre después de seleccionar el nodo, asumir o reservar la asignación y ejecutar Permit y PreBind. Registra la asignación, pero no confirma que los contenedores hayan arrancado. Conserva el plugin integrado `DefaultBinder`, que también gestiona la ruta de caché de la API y los errores de vinculación de la versión de referencia. Esta función completa muestra cómo identificar la solicitud sin enviarla:

```go
package bindingexample

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// This only constructs a request; it neither selects a node nor calls the API.
// Use DefaultBinder within the complete scheduler pipeline for actual binding.
func BindingFor(pod *v1.Pod, nodeName string) (*v1.Binding, error) {
	if pod == nil || pod.Name == "" || pod.Namespace == "" || pod.UID == "" || nodeName == "" {
		return nil, fmt.Errorf("admitted Pod name, namespace, UID and selected node are required")
	}
	return &v1.Binding{
		ObjectMeta: metav1.ObjectMeta{Name: pod.Name, Namespace: pod.Namespace, UID: pod.UID},
		Target:     v1.ObjectReference{Kind: "Node", Name: nodeName},
	}, nil
}
```

El UID del Pod evita confundir un Pod eliminado con otro creado posteriormente con el mismo nombre. La solicitud de vinculación no comprueba por sí misma los recursos, la afinidad ni los taints; estas comprobaciones corresponden a las etapas anteriores del proceso completo de planificación.

**Configuración del binder predeterminado:**
La siguiente configuración conserva todos los valores predeterminados, incluido `DefaultBinder`; no habilita un binder personalizado sin registrar.

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

**Comprobación de eventos de vinculación:**
```bash
# Check pod scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**Solución de problemas de fallos de vinculación:**
Causas comunes de fallo en la etapa de vinculación:
1. Problemas de conexión con el API server
2. Permisos insuficientes
3. Errores en el nombre del nodo
4. Condiciones de carrera (otro scheduler intenta vincular el mismo Pod simultáneamente)

**Por qué las demás opciones no son correctas:**
- B. Configurar la vinculación de red entre Pods y nodos: los plugins CNI gestionan la red; esta tarea no corresponde a la etapa Bind del scheduler.
- C. Crear una vinculación entre Pods y Services: los Services seleccionan los Pods mediante selectores de etiquetas; esta relación no corresponde a la etapa Bind.
- D. Configurar la vinculación entre Pods y volúmenes: la vinculación PV/PVC y el aprovisionamiento CSI también implican a los controladores de almacenamiento y al plugin VolumeBinding del scheduler, incluida la vinculación diferida. Bind entre un Pod y un nodo es una operación distinta.
</details>

### 2. ¿Cuál de los siguientes NO es un operador de afinidad de nodo en Kubernetes?

A. In
B. NotIn
C. Exists
D. Contains

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Contains**

**Explicación:**
`Contains` no es un operador de afinidad de nodo. Kubernetes no proporciona un operador `Contains` para este fin.

**Operadores de afinidad de nodo:**
1. **In**: el valor de la etiqueta debe coincidir con uno de los valores indicados.
2. **NotIn**: el valor de la etiqueta no debe coincidir con los valores indicados.
3. **Exists**: la clave de la etiqueta debe existir.
4. **DoesNotExist**: la clave de la etiqueta no debe existir.
5. **Gt**: el valor de la etiqueta debe ser mayor que el valor indicado.
6. **Lt**: el valor de la etiqueta debe ser menor que el valor indicado.

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
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: Exists
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**Tipos de afinidad de nodo:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Reglas que deben cumplirse para que el Pod se programe en un nodo (requisito estricto).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Reglas que se prefiere que se cumplan, pero no son obligatorias (requisito flexible).

**Ejemplos de uso de operadores:**
1. **Operador In**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: In
     values:
     - us-east-1a
     - us-east-1b
   ```
   El valor de la etiqueta `topology.kubernetes.io/zone` del nodo debe ser `us-east-1a` o `us-east-1b`.

2. **Operador NotIn**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: NotIn
     values:
     - us-east-1c
   ```
   El valor de la etiqueta `topology.kubernetes.io/zone` del nodo no debe ser `us-east-1c`.

3. **Operador Exists**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: Exists
   ```
   La etiqueta `topology.kubernetes.io/zone` debe existir en el nodo.

4. **Operador DoesNotExist**:
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   La etiqueta `emptyLabel` no debe existir en el nodo.

5. **Operadores Gt/Lt**:
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   El valor de la etiqueta `node-size` del nodo debe ser mayor que 10.

**Comprobación de la afinidad de nodo obligatoria:**
Conserva el plugin predeterminado `NodeAffinity`. Para una comprobación de solo lectura, usa la función auxiliar del componente en la versión de referencia, en lugar de una función `matchNodeSelectorTerm` incompleta que devuelva siempre true.

```go
package affinityexample

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
	nodeaffinity "k8s.io/component-helpers/scheduling/corev1/nodeaffinity"
)

// A read-only check of Pod nodeSelector and required node affinity.
// The scheduler's NodeAffinity plugin also handles profile-level addedAffinity.
func MatchesRequired(pod *v1.Pod, node *v1.Node) (bool, error) {
	if pod == nil || node == nil {
		return false, fmt.Errorf("pod and node are required")
	}
	return nodeaffinity.GetRequiredNodeAffinity(pod).Match(node)
}
```

Deben cumplirse tanto `nodeSelector` como la afinidad de nodo obligatoria. Los términos del selector se combinan con OR y las expresiones de cada término con AND; un término vacío no coincide con ningún nodo. `NotIn` también coincide cuando la clave no existe; añade `Exists` si necesitas exigir su presencia. `Gt`/`Lt` requieren exactamente un valor entero de comparación y un valor entero en la etiqueta del nodo. `IgnoredDuringExecution` significa que los cambios posteriores de etiquetas no expulsan por sí mismos un Pod ya asignado. La afinidad `addedAffinity` del perfil sigue siendo responsabilidad del plugin del scheduler.

**Explicación de las otras opciones:**
- A. In: Un operador de afinidad de nodo válido.
- B. NotIn: Un operador de afinidad de nodo válido.
- C. Exists: Un operador de afinidad de nodo válido.
</details>

### 3. ¿Cuál es el propósito principal de las restricciones de distribución topológica de Pods en Kubernetes?

A. Distribuir Pods de manera uniforme entre varios nodos
B. Colocar Pods solo en nodos específicos
C. Colocar Pods solo en zonas específicas
D. Colocar Pods solo en nodos con etiquetas específicas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Distribuir Pods de manera uniforme entre varios nodos**

**Explicación:**
Las restricciones de distribución topológica limitan dónde puede colocarse cada Pod entrante entre los dominios elegibles. Pueden mejorar la tolerancia a fallos, pero no redistribuyen los Pods existentes ni garantizan latencia, capacidad o disponibilidad.

**Campos principales:**
1. **maxSkew**: con `DoNotSchedule`, limita el recuento del dominio candidato del Pod entrante respecto al mínimo global de los dominios elegibles.
2. **topologyKey**: etiqueta de nodo que define un dominio.
3. **whenUnsatisfiable**: `DoNotSchedule` es una restricción obligatoria; `ScheduleAnyway` es una preferencia de puntuación y no evita los demás filtros obligatorios.
4. **labelSelector**: selecciona los Pods que se cuentan en el namespace del Pod entrante. Comprueba que este Pod coincida con el selector previsto.
5. **minDomains / nodeAffinityPolicy / nodeTaintsPolicy**: influyen en el recuento de dominios elegibles. No crean nodos ni capacidad en las zonas de disponibilidad.

**Ejemplo de restricciones de distribución topológica:**
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
    image: nginx:1.30.6
```

En el ejemplo, la ubicación candidata debe satisfacer ambas restricciones. Para `DoNotSchedule`, calcula lo siguiente:

1. Cuenta los Pods coincidentes en cada dominio elegible, incluidos los dominios vacíos.
2. Obtén el mínimo global de los dominios elegibles; es cero si hay menos dominios que `minDomains`.
3. Incluye el Pod entrante en su dominio candidato si coincide con el selector y compara ese recuento con el mínimo.

Con recuentos **2,2,1** y `maxSkew: 1`, otro Pod coincidente puede entrar en el tercer dominio (2−1=1), pero no en los dos primeros (3−1=2). Esta comprobación evalúa la ubicación candidata; no garantiza que todos los pares de dominios existentes estén equilibrados en todo momento.

**Claves topológicas habituales:**
1. **kubernetes.io/hostname**: distribución por nodo.
2. **topology.kubernetes.io/zone**: distribución por zona.
3. **topology.kubernetes.io/region**: distribución por región.
4. **node.kubernetes.io/instance-type**: distribución por tipo de instancia.

**Casos de uso:**
1. **Alta disponibilidad**: mejorar la tolerancia a fallos distribuyendo Pods entre varios nodos, zonas y regiones.
2. **Equilibrio de recursos**: distribuir las cargas de trabajo por el clúster.
3. **Optimización de costes**: distribuir las cargas entre tipos de nodo concretos.
4. **Política topológica**: equilibrar la tolerancia a fallos con el tráfico entre dominios y la latencia medida.

**Gestión en un scheduler personalizado:**
Conserva `PodTopologySpread` y sus etapas PreFilter, Filter y Score. La implementación correcta necesita la instantánea del scheduler, la coincidencia de namespaces y selectores, los dominios elegibles y vacíos, el Pod entrante, `minDomains`, las políticas de afinidad y taints, y los eventos que devuelven Pods a la cola. Un bucle sobre Pods en estado Running que omita el cálculo de skew no constituye una implementación.

Este laboratorio de EKS utiliza nodos EC2 en una sola región de AWS; una etiqueta `topology.kubernetes.io/region` no lo convierte en un clúster multirregión. La distribución entre zonas de disponibilidad puede aumentar el tráfico entre zonas y no minimiza por sí misma la latencia de red.

**Por qué las demás opciones no son correctas:**
- B. Colocar Pods solo en nodos específicos: es el cometido de nodeSelector o nodeAffinity.
- C. Colocar Pods solo en zonas específicas: la afinidad de nodo permite restringir la ubicación a determinadas zonas; las restricciones de distribución topológica buscan repartir los Pods.
- D. Colocar Pods solo en nodos con etiquetas específicas: es el cometido de nodeSelector o nodeAffinity.
</details>

### 4. ¿Cuál es el propósito principal de los taints y las tolerations en Kubernetes?

A. Garantizar que Pods específicos se programen solo en nodos específicos
B. Evitar que Pods específicos se programen en nodos específicos
C. Permitir que los nodos rechacen ciertos Pods y que los Pods lo toleren
D. Restringir la comunicación entre Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir que los nodos rechacen ciertos Pods y que los Pods lo toleren**

**Explicación:**
Los taints repelen Pods; las tolerations permiten ignorar un taint coincidente. Una toleration no obliga a colocar el Pod en ese nodo ni evita los filtros de recursos o afinidad.

**Efectos:**
1. **NoSchedule**: un taint sin toleration impide nuevas asignaciones, pero no expulsa los Pods existentes.
2. **PreferNoSchedule**: es una preferencia flexible; otras puntuaciones pueden prevalecer incluso cuando existe capacidad en otros nodos.
3. **NoExecute**: impide nuevas asignaciones sin una toleration coincidente y activa la gestión de expulsión de los Pods existentes que no la tengan o cuyo periodo de tolerancia haya vencido. Eliminar el Pod de la API no demuestra que su proceso haya parado en un nodo inaccesible.

**Ejemplo de aplicación de un taint:**
```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Remove taint from node
kubectl taint nodes node1 key=value:NoSchedule-
```

**Ejemplo de taint y toleration:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-toleration
spec:
  tolerations:
  - key: key
    operator: Equal
    value: value
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**Campos de las tolerations:**
* `Equal`, el operador predeterminado, compara clave y valor. Con `Exists` se debe omitir el valor.
* Si se especifica un efecto, debe coincidir; un efecto vacío coincide con todos los efectos de esa clave. Una clave vacía exige `Exists` y coincide con todas las claves, así que úsala deliberadamente.
* `tolerationSeconds` solo se aplica a `NoExecute`. Omitirlo permite tolerar ese taint coincidente indefinidamente; especificarlo limita el periodo tolerado.
* El ejemplo utiliza el comportamiento predeterminado de `Equal`/`Exists`. La función opcional de operadores de comparación de Kubernetes 1.35 es alfa y está deshabilitada aquí.

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**Casos de uso habituales:**
1. **Nodos dedicados**: combina taints, tolerations controladas y afinidad obligatoria. Los taints por sí solos no obligan a ejecutar esas cargas en los nodos dedicados.
2. **Hardware especial**: planificar determinados Pods solo en nodos con hardware especial, como GPU.
3. **Mantenimiento de nodos**: impedir nuevas asignaciones de Pods durante el mantenimiento.
4. **Protección del nodo de control**: impedir que las cargas generales se asignen a nodos del plano de control.

**Taints del sistema:**
Kubernetes aplica automáticamente los siguientes taints del sistema:
1. **node.kubernetes.io/not-ready**: El nodo no está listo
2. **node.kubernetes.io/unreachable**: El nodo no es alcanzable
3. **node.kubernetes.io/memory-pressure**: El nodo tiene presión de memoria
4. **node.kubernetes.io/disk-pressure**: El nodo tiene presión de disco
5. **node.kubernetes.io/pid-pressure**: El nodo tiene presión de PID
6. **node.kubernetes.io/network-unavailable**: La red del nodo no está disponible
7. **node.kubernetes.io/unschedulable**: El nodo está marcado como no programable

**Comprobación de taints obligatorios:**
Esta función auxiliar completa utiliza la semántica de coincidencia de la versión de referencia, incluidos los efectos y comodines. Excluye `PreferNoSchedule` de la comprobación obligatoria e incluye `NoExecute`. No sustituye los demás filtros del scheduler ni el controlador de expulsión por taints.

```go
package taintexample

import (
    v1 "k8s.io/api/core/v1"
    corehelpers "k8s.io/component-helpers/scheduling/corev1"
    "k8s.io/klog/v2"
)

// Checks hard scheduling taints only; it does not implement eviction timers.
func ToleratesHardTaints(pod *v1.Pod, node *v1.Node) bool {
	if pod == nil || node == nil {
		return false
	}
	_, untolerated := corehelpers.FindMatchingUntoleratedTaint(
		klog.Background(), node.Spec.Taints, pod.Spec.Tolerations,
		func(taint *v1.Taint) bool {
			return taint.Effect == v1.TaintEffectNoSchedule || taint.Effect == v1.TaintEffectNoExecute
		}, false, // Equal/Exists behavior; comparison-operator feature is not enabled here.
	)
	return !untolerated
}
```

**Por qué las demás opciones no son correctas:**
- A. Garantizar que ciertos Pods se planifiquen solo en determinados nodos: es el cometido de nodeSelector o nodeAffinity.
- B. Evitar que ciertos Pods se planifiquen en determinados nodos: solo describe la parte de rechazo de los taints y las tolerations; podAntiAffinity relaciona la ubicación con otros Pods.
- D. Restringir la comunicación entre Pods: es el cometido de NetworkPolicy.
</details>

### 5. ¿Cuál de las siguientes NO es una característica principal de Scheduler Extender en Kubernetes?

A. Se comunica con el scheduler mediante webhooks HTTP
B. Proporciona filtrado y priorización
C. Está integrado directamente en el código del scheduler
D. Se ejecuta como un proceso externo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Está integrado directamente en el código del scheduler**

**Explicación:**
La integración directa en el código del scheduler NO es una característica de Scheduler Extender. Los extenders se ejecutan como procesos externos y se comunican con el scheduler mediante webhooks HTTP. Esa es la principal diferencia respecto a los plugins del framework de planificación.

**Características principales de Scheduler Extender:**
1. **Webhooks HTTP**: el scheduler se comunica con los extenders mediante solicitudes HTTP.
2. **Proceso externo**: los extenders se ejecutan en procesos separados del scheduler.
3. **Filtrado y priorización**: pueden filtrar nodos y asignarles prioridades.
4. **Vinculación**: opcionalmente, pueden vincular Pods con nodos.

**Configuración del extender:**
Utiliza el servicio TLS y los certificados descritos en la parte 2 con el scheduler secundario. `extenders` se configura en el nivel superior. Mantén `ignorable: false` para un filtro obligatorio; no combines un extender que permita continuar ante fallos con `ignoredByScheduler: true` para recursos cuya disponibilidad deba comprobarse. El ejemplo deja toda la contabilización de GPU al filtro integrado de recursos.

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

**Protocolo de intercambio (Kubernetes 1.35.8):**
Los tipos de Go se serializan con nombres de campo que empiezan en mayúscula. Con `nodeCacheCapable: false`, envía `Pod` y los `Nodes` completos; `NodeNames` es null. Si el valor es true, se necesita una caché de nodos mantenida por separado y respetar el contrato de `NodeNames`. Los siguientes ejemplos son JSON válido, no marcadores de posición entre signos angulares.

1. **Solicitud de filtrado o priorización**:

```json
{
  "Pod": {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
      "name": "gpu-pod",
      "namespace": "default",
      "uid": "00000000-0000-0000-0000-000000000001",
      "annotations": {
        "training.example.com/min-gpu-memory-mib": "16384"
      }
    },
    "spec": {
      "schedulerName": "custom-scheduler",
      "containers": [
        {
          "name": "worker",
          "image": "busybox:1.38.0",
          "resources": {
            "requests": {
              "nvidia.com/gpu": "1"
            },
            "limits": {
              "nvidia.com/gpu": "1"
            }
          }
        }
      ]
    }
  },
  "Nodes": {
    "items": [
      {
        "metadata": {
          "name": "gpu-node",
          "labels": {
            "training.example.com/gpu-memory-mib": "16384"
          }
        },
        "status": {
          "allocatable": {
            "nvidia.com/gpu": "1"
          }
        }
      }
    ]
  },
  "NodeNames": null
}
```

2. **Respuesta de filtrado**: solo puede devolver nodos de la lista candidata recibida. `FailedAndUnresolvableNodes` identifica fallos que la preemption no puede resolver.

```json
{
  "Nodes": {
    "items": [
      {
        "metadata": {
          "name": "gpu-node",
          "labels": {
            "training.example.com/gpu-memory-mib": "16384"
          }
        },
        "status": {
          "allocatable": {
            "nvidia.com/gpu": "1"
          }
        }
      }
    ]
  },
  "NodeNames": null,
  "FailedNodes": {},
  "FailedAndUnresolvableNodes": {},
  "Error": ""
}
```

3. **Respuesta de priorización**: un array de `Host`/`Score` sin objeto envolvente, con puntuaciones de **0 a 10**. Las puntuaciones del framework van de 0 a 100. Si falla la priorización, se omiten las puntuaciones de ese extender; por ello, las reglas obligatorias deben implementarse en Filter.

```json
[
  {
    "Host": "gpu-node",
    "Score": 2
  }
]
```

4. **Solicitud y respuesta de vinculación opcional**: la solicitud identifica el Pod por nombre, namespace y UID, además del nodo elegido. La parte 2 no implementa esta función y deja `bindVerb` sin configurar.

```json
{
  "PodName": "gpu-pod",
  "PodNamespace": "default",
  "PodUID": "00000000-0000-0000-0000-000000000001",
  "Node": "gpu-node"
}
```

```json
{
  "Error": ""
}
```

5. **Función de preemption opcional**: `preemptVerb` intercambia el Pod y las víctimas candidatas mediante `ExtenderPreemptionArgs`/`ExtenderPreemptionResult`. No es una función PreFilter ni PreScore.

**Implementación:**
Utiliza el manejador completo con entrada limitada y el comando TLS de la [parte 2](../../scheduling/02-custom-scheduler-part2.md). Rechazan Pods o nodos ausentes, requisitos de memoria mal formados, entradas demasiado grandes y un contrato de caché incorrecto. Las funciones `customFilter` o `customScore` sin implementar no se presentan como código ejecutable.

**Scheduler Extender frente a los plugins del framework de planificación:**

| Característica | Scheduler Extender | Plugin del framework de planificación |
|---------|-------------------|---------------------------|
| Método de integración | Webhook HTTP | Integración directa en el código |
| Ejecución | Proceso externo | Dentro del scheduler |
| Rendimiento | Relativamente más lento por la comunicación HTTP | Más rápido por la integración directa |
| Lenguaje de desarrollo | Sin restricciones | Go |
| Despliegue | Servicio separado | Se despliega con el scheduler |
| Mantenimiento | Independiente del scheduler | Vinculado a la versión del scheduler |

**Pros y contras de Scheduler Extender:**
Pros:
- Puede desarrollarse independientemente del código base del scheduler
- Puede implementarse en varios lenguajes de programación
- Se ve menos afectado por las actualizaciones del scheduler

Desventajas:
- La comunicación HTTP añade una sobrecarga que puede reducir el rendimiento.
- Solo pueden ampliar algunas etapas del ciclo de planificación.
- La comunicación entre el scheduler y el extender puede fallar.

**Explicación de las demás opciones:**
- A. Se comunica con el scheduler mediante webhooks HTTP: es una característica válida de los extenders.
- B. Proporciona filtrado y priorización: es una característica válida de los extenders.
- D. Se ejecuta como proceso externo: es una característica válida de los extenders.
</details>

### 6. ¿Cuál es el propósito principal de Pod Affinity y Pod Anti-Affinity en Kubernetes?

A. Definir relaciones entre Pods y nodos
B. Definir relaciones entre Pods y volúmenes
C. Definir relaciones entre Pods
D. Definir relaciones entre Pods y Services

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Definir relaciones entre Pods**

**Explicación:**
La afinidad y la antiafinidad entre Pods definen relaciones entre ellos. Permiten controlar si determinados Pods se colocan en el mismo dominio topológico —nodo, zona, región, etc.— que otros Pods, mediante afinidad, o se separan de ellos, mediante antiafinidad.

**Componentes principales de la afinidad y la antiafinidad entre Pods:**
1. **topologyKey**: clave de etiqueta del nodo que define el dominio topológico de la relación.
2. **labelSelector**: selector de etiquetas que identifica los Pods con los que se establece la relación.
3. **namespaces**: lista de namespaces en los que se aplica el selector.

**Tipos de afinidad entre Pods:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: reglas obligatorias para planificar el Pod.
2. **preferredDuringSchedulingIgnoredDuringExecution**: preferencias que no es obligatorio cumplir.

**Ejemplo de afinidad entre Pods:**
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

En este ejemplo:
1. **Afinidad entre Pods**: el Pod del servidor web debe planificarse en el mismo nodo (`kubernetes.io/hostname`) que los Pods con la etiqueta `app=cache`.
2. **Antiafinidad entre Pods**: se prefiere planificar el Pod del servidor web en un nodo distinto del de otros Pods con la etiqueta `app=web`.

**Claves topológicas habituales:**
1. **kubernetes.io/hostname**: relación por nodo.
2. **topology.kubernetes.io/zone**: relación por zona.
3. **topology.kubernetes.io/region**: relación por región.

**Casos de uso:**
1. **Alta disponibilidad**: distribuir instancias de la misma aplicación entre distintos nodos, zonas y regiones.
2. **Preferencia de proximidad**: compartir ubicación puede reducir algunos costes de red; mide la contención y la latencia antes de depender de ello.
3. **Aislamiento de recursos**: distribuir los Pods que consumen muchos recursos entre nodos diferentes.
4. **Restricciones de licencia**: concentrar aplicaciones con restricciones de licencia en determinados nodos.

**Afinidad entre Pods frente a afinidad de nodo:**
- **Afinidad de nodo**: define relaciones entre Pods y nodos.
- **Afinidad entre Pods**: define relaciones entre Pods.

**Impacto de la afinidad y la antiafinidad entre Pods en el rendimiento:**
Estas reglas pueden exigir cálculos costosos porque deben considerar todos los nodos y Pods. En clústeres grandes pueden afectar al rendimiento de la planificación, por lo que deben utilizarse con cuidado.

**Gestión en un scheduler personalizado:**
Conserva `InterPodAffinity`, incluido el preprocesamiento y la puntuación. Debe considerar los términos obligatorios del Pod entrante, la antiafinidad obligatoria de los Pods existentes, la selección de namespaces, las etiquetas topológicas y el comportamiento de inicio de self-affinity. Una función incompleta que devuelva siempre true puede permitir ubicaciones inválidas o, al invertir el resultado para antiafinidad, rechazar todos los nodos.

`namespaces` y `namespaceSelector` seleccionan la unión de namespaces; si se omiten ambos, se utiliza el namespace del Pod entrante. `namespaceSelector: {}` selecciona todos los namespaces. En el ejemplo, el Pod requerido con `app=cache` debe existir ya en el namespace seleccionado, en un nodo elegible. La antiafinidad preferida no garantiza la separación. `IgnoredDuringExecution` no reubica continuamente los Pods cuando cambian las etiquetas o los Pods relacionados.

**Por qué las demás opciones no son correctas:**
- A. Definir relaciones entre Pods y nodos: es el cometido de nodeAffinity.
- B. Definir relaciones entre Pods y volúmenes: es el cometido de la vinculación de volúmenes y de PersistentVolumeClaim.
- D. Definir relaciones entre Pods y Services: se gestiona mediante selectores de etiquetas de los Services.
</details>

### 7. ¿Cuál es el rol del punto de extensión "QueueSort" en el scheduler de Kubernetes?

A. Puntuar nodos
B. Excluir nodos donde los Pods no pueden ejecutarse
C. Ordenar Pods en la cola de planificación
D. Vincular Pods a nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ordenar Pods en la cola de planificación**

**Explicación:**
El rol del punto de extensión "QueueSort" en el framework de planificación de Kubernetes es ordenar Pods en la cola de planificación. Este punto de extensión establece la prioridad que determina qué Pods se programan primero.

**Cola de planificación y QueueSort:**
El scheduler procesa los Pods de la cola uno a uno. El plugin QueueSort determina su orden. Kubernetes utiliza por defecto el plugin `PrioritySort` para ordenar según la prioridad del Pod.

**Interfaz de la versión de referencia:**
En Kubernetes 1.35.8, QueueSort implementa `Less(fwk.QueuedPodInfo, fwk.QueuedPodInfo) bool`; los argumentos son interfaces cuyos datos se consultan mediante métodos de acceso. El plugin predeterminado `PrioritySort` compara primero la prioridad admitida y después la marca de tiempo de la cola.

**Ejemplo personalizado completo (`quizplugins/queue.go`):**
Este ejemplo respeta la prioridad admitida antes de aplicar los criterios de desempate del laboratorio. Las preferencias por namespace o etiqueta pueden causar desigualdad entre Pods de la misma prioridad; no permitas que etiquetas no confiables sustituyan una PriorityClass controlada en la admisión.

```go
package quizplugins

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	corehelpers "k8s.io/component-helpers/scheduling/corev1"
	fwk "k8s.io/kube-scheduler/framework"
)

type CustomQueueSort struct{}

var _ fwk.QueueSortPlugin = &CustomQueueSort{}

func (*CustomQueueSort) Name() string { return "CustomQueueSort" }

func (*CustomQueueSort) Less(a, b fwk.QueuedPodInfo) bool {
	pa, pb := a.GetPodInfo().GetPod(), b.GetPodInfo().GetPod()
	ap, bp := corehelpers.PodPriority(pa), corehelpers.PodPriority(pb)
	if ap != bp {
		return ap > bp
	}
	// Lab tie-breakers only; do not override the admitted Pod priority.
	aPreferred := pa.Namespace == "high-priority-namespace"
	bPreferred := pb.Namespace == "high-priority-namespace"
	if aPreferred != bPreferred {
		return aPreferred
	}
	if critical(pa) != critical(pb) {
		return critical(pa)
	}
	return a.GetTimestamp().Before(b.GetTimestamp())
}

func critical(pod *v1.Pod) bool { return pod.Labels["training.example.com/critical"] == "true" }

func NewQueue(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &CustomQueueSort{}, nil
}
```

Regístralo junto con el ejemplo posterior de PoolConstraint en `cmd/quiz-scheduler/main.go`:

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
		app.WithPlugin("CustomQueueSort", quizplugins.NewQueue),
		app.WithPlugin("PoolConstraint", quizplugins.NewPool),
	)
	os.Exit(cli.Run(command))
}
```

Compila con el módulo de la parte 1: `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`. Habilita solo los plugins necesarios en la configuración elegida.

**Habilitación del plugin QueueSort en la configuración del scheduler:**
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
    queueSort:
      enabled:
      - name: CustomQueueSort
      disabled:
      - name: PrioritySort  # Disable default plugin
```

**Características del plugin QueueSort:**
1. **Activación única**: solo puede estar activo un plugin QueueSort a la vez.
2. **Cola compartida**: todos los perfiles de un mismo proceso scheduler deben usar el mismo plugin QueueSort y la misma configuración. Los demás procesos scheduler tienen colas independientes.
3. **Rendimiento**: un algoritmo de ordenación eficiente es importante; una lógica compleja puede afectar al rendimiento de la planificación.

**Casos de uso del plugin QueueSort:**
1. **Prioridad de negocio**: ordenar los Pods según su importancia para el negocio.
2. **Eficiencia de recursos**: planificar primero Pods con solicitudes de recursos menores para aprovechar el espacio libre.
3. **Acuerdos de nivel de servicio (SLA)**: ordenar los Pods según los requisitos del SLA.
4. **Procesamiento por lotes**: ajustar la prioridad entre trabajos por lotes e interactivos.

**Monitoreo de la cola de planificación:**
```bash
# Check queue information in scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100

# Check pods pending scheduling
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**Por qué las demás opciones no son correctas:**
- A. Puntuar nodos: es el cometido del punto de extensión Score.
- B. Excluir nodos en los que no puedan ejecutarse los Pods: es el cometido de Filter.
- D. Vincular Pods con nodos: es el cometido de Bind.
</details>

### 8. ¿Cuál es el propósito principal de Pod Priority Preemption en Kubernetes?

A. Eliminar Pods de menor prioridad para que se puedan programar Pods de mayor prioridad
B. Asignar más recursos a Pods de mayor prioridad
C. Ejecutar Pods de mayor prioridad más rápido
D. Colocar Pods de mayor prioridad solo en nodos específicos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Eliminar Pods de menor prioridad para que se puedan programar Pods de mayor prioridad**

**Explicación:**
Pod Priority Preemption permite eliminar Pods de menor prioridad para dar cabida a otros de mayor prioridad. Si un Pod de mayor prioridad no cabe, el scheduler puede hacer preemption sobre Pods de menor prioridad cuando eso permita satisfacer las restricciones aplicables.

**Mecanismo de prioridad y preemption de Pods:**
1. **Definición de PriorityClass**: un recurso de ámbito de clúster define la prioridad del Pod.
2. **Asignación de prioridad**: los Pods referencian una PriorityClass mediante `spec.priorityClassName`.
3. **Orden de planificación**: los Pods de mayor prioridad se procesan primero en la cola.
4. **Preemption**: el scheduler puede eliminar Pods de menor prioridad cuando la política del Pod lo permita y puedan satisfacerse las demás restricciones.

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
    image: nginx:1.30.6
```

**Políticas de preemption:**
El campo `preemptionPolicy` de PriorityClass admite estos valores:
1. **PreemptLowerPriority (predeterminado)**: permite hacer preemption sobre Pods de menor prioridad.
2. **Never**: impide hacer preemption sobre Pods de menor prioridad.

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

**Proceso de preemption:**
1. El scheduler intenta planificar un Pod de mayor prioridad.
2. Si no hay un nodo adecuado, identifica los Pods candidatos a preemption en cada nodo.
3. Selecciona los candidatos entre los Pods de menor prioridad.
4. Elige un nodo candidato y un conjunto de víctimas según su política; no garantiza el mínimo global de víctimas.
5. Los Pods seleccionados terminan de forma ordenada.
6. Cuando terminan las víctimas, se vuelve a intentar la planificación; la nominación no garantiza la vinculación.

**Consideraciones sobre preemption:**
1. **Terminación ordenada**: los Pods afectados disponen de `terminationGracePeriodSeconds`, cuyo valor predeterminado es 30 segundos.
2. **Pod Disruption Budget (PDB)**: se intenta evitar infringir los PDB, pero su cumplimiento se realiza como mejor esfuerzo y no está garantizado.
3. **Nominación**: `status.nominatedNodeName` registra un posible destino. La preemption no lo reserva añadiendo un taint al nodo.
4. **Pods del sistema**: las PriorityClasses críticas tienen prioridades altas reservadas, pero esto no las hace inmunes a cualquier Pod de mayor prioridad ni a otros mecanismos de expulsión.

**Comprobación de eventos de Preemption:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Supervisión de métricas de preemption:**
Consulta `scheduler_preemption_attempts_total` en el endpoint HTTPS autenticado de métricas del **scheduler personalizado**, mediante tu sistema de supervisión configurado. `kubectl get --raw /metrics` consulta métricas del API server, no este endpoint.

```bash
kubectl get pods -A -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority,NOMINATED:.status.nominatedNodeName
```

**Gestión segura de preemption:**
Conserva `DefaultPreemption` en PostFilter. Simula la retirada de Pods de menor prioridad y vuelve a comprobar las restricciones aplicables; eliminar todos los Pods de menor prioridad del primer nodo es inseguro. La selección considera las infracciones de PDB y las prioridades de las víctimas, pero no promete el mínimo global de víctimas.

La preemption no puede corregir etiquetas ausentes, una topología de volúmenes incompatible ni hardware que no exista. Un Pod puede seguir Pending después de la nominación, y otro de mayor prioridad puede alterar el resultado. La creación de reemplazos, la terminación y las actualizaciones de la API son asíncronas. En esta revisión no se ejecutó ningún bucle de expulsión.

**Ventajas y desventajas de preemption:**
Ventajas:
- Puede liberar espacio para cargas de mayor prioridad cuando las restricciones lo permitan.
- Favorece el uso eficiente de los recursos del clúster.
- Ayuda a cumplir los acuerdos de nivel de servicio (SLA).

Desventajas:
- Interrupción de los Pods afectados.
- Sobrecarga al volver a planificar después de la preemption.
- Complejidad de la lógica que decide la preemption.

**Por qué las demás opciones no son correctas:**
- B. Asignar más recursos a Pods de mayor prioridad: la prioridad no cambia directamente la asignación de recursos. Las solicitudes y los límites de recursos se definen por separado en la especificación del Pod.
- C. Ejecutar Pods de mayor prioridad más rápido: la prioridad afecta al orden de planificación, pero no a la velocidad de ejecución del Pod.
- D. Colocar Pods de mayor prioridad solo en nodos específicos: es el cometido de nodeSelector o nodeAffinity, sin relación directa con la prioridad.
</details>

### 9. ¿Cuál es el rol del punto de extensión "PreFilter" en el scheduler de Kubernetes?

A. Preprocesar el Pod y el estado del clúster antes del filtrado
B. Puntuar nodos después del filtrado
C. Verificar antes de vincular Pods con nodos
D. Ordenar Pods en la cola de planificación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Preprocesar el Pod y el estado del clúster antes del filtrado**

**Explicación:**
PreFilter preprocesa el Pod y el estado del clúster antes del filtrado. Sus plugins preparan los datos que se utilizarán en esa etapa y pueden comprobar previamente si el Pod es planificable.

**Funciones principales del punto de extensión PreFilter:**
1. **Preparación de datos**: Inicializar y preparar estructuras de datos que se usarán en la etapa de filtrado.
2. **Comprobaciones previas**: Comprobar previamente si los Pods pueden programarse.
3. **Almacenamiento de estado**: Almacenar información de estado que se usará durante el ciclo de planificación.
4. **Optimización**: Evitar trabajo de filtrado innecesario para optimizar el rendimiento.

**Interfaz de la versión de referencia:**
Kubernetes 1.35.8 utiliza `PreFilter(ctx, state, pod, nodes) (*fwk.PreFilterResult, *fwk.Status)`, donde `state` es `fwk.CycleState` y `nodes` es `[]fwk.NodeInfo`. Las extensiones opcionales AddPod y RemovePod reciben el Pod que se está planificando, el PodInfo simulado que se añade o retira y NodeInfo. Sirven para simular la preemption y pueden ejecutarse sobre estado clonado; no son callbacks ordinarios de un informer.

**Plugins PreFilter predeterminados:**
Kubernetes proporciona los siguientes plugins PreFilter:

1. **InterPodAffinity**: gestiona la afinidad y la antiafinidad entre Pods.
2. **NodeAffinity**: gestiona la afinidad de nodo.
3. **NodePorts**: gestiona los puertos del host solicitados por los Pods.
4. **NodeResourcesFit**: gestiona los requisitos de recursos de nodo.
5. **PodTopologySpread**: gestiona las restricciones de distribución topológica de Pods.
6. **VolumeBinding**: gestiona los requisitos de vinculación de volúmenes.

**Ejemplo completo de PreFilter y Filter (`quizplugins/prefilter.go`):**
Para una etiqueta de pool ordinaria, la afinidad de nodo obligatoria es más sencilla. Este ejemplo muestra un estado validado por ciclo y `Clone()`. No depende de otros Pods, así que no necesita las extensiones AddPod o RemovePod. Si falta el estado de PreFilter, se produce un error; no se permite planificar el Pod.

```go
package quizplugins

import (
	"context"
	"strings"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	validation "k8s.io/apimachinery/pkg/util/validation"
	fwk "k8s.io/kube-scheduler/framework"
)

const poolStateKey fwk.StateKey = "training.example.com/pool-constraint"

type poolState struct{ Pool string }

func (s *poolState) Clone() fwk.StateData { return &poolState{Pool: s.Pool} }

type PoolConstraint struct{}

var _ fwk.PreFilterPlugin = &PoolConstraint{}
var _ fwk.FilterPlugin = &PoolConstraint{}

func (*PoolConstraint) Name() string { return "PoolConstraint" }

func (*PoolConstraint) PreFilter(_ context.Context, state fwk.CycleState, pod *v1.Pod, _ []fwk.NodeInfo) (*fwk.PreFilterResult, *fwk.Status) {
	pool := pod.Annotations["training.example.com/required-pool"]
	if problems := validation.IsValidLabelValue(pool); len(problems) != 0 {
		return nil, fwk.NewStatus(fwk.UnschedulableAndUnresolvable, strings.Join(problems, "; "))
	}
	state.Write(poolStateKey, &poolState{Pool: pool})
	return nil, nil
}

func (*PoolConstraint) PreFilterExtensions() fwk.PreFilterExtensions { return nil }

func (*PoolConstraint) Filter(_ context.Context, state fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	data, err := state.Read(poolStateKey)
	if err != nil {
		return fwk.AsStatus(err)
	}
	prepared, ok := data.(*poolState)
	if !ok || info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "invalid prepared state or node")
	}
	if prepared.Pool != "" && info.Node().Labels["training.example.com/pool"] != prepared.Pool {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "required pool label does not match")
	}
	return nil
}

func NewPool(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &PoolConstraint{}, nil
}
```

**Habilita las dos etapas implementadas y conserva las comprobaciones predeterminadas de recursos:**
El comando de registro de la pregunta 7 incluye este plugin.

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
    preFilter:
      enabled:
      - name: PoolConstraint
    filter:
      enabled:
      - name: PoolConstraint
```

**Relación entre PreFilter y Filter:**
1. **PreFilter**: se ejecuta una vez antes de empezar el filtrado de todos los nodos.
2. **Filter**: se ejecuta para cada nodo por separado.

PreFilter prepara datos que se usarán en la etapa Filter y preidentifica casos en los que los Pods no pueden programarse en ningún nodo para evitar trabajo de filtrado innecesario.

**Casos de uso de PreFilter:**
1. **Restricciones complejas**: gestionar con eficiencia restricciones como la afinidad entre Pods o la distribución topológica.
2. **Validación previa**: comprobar si el Pod es planificable para evitar procesamiento innecesario.
3. **Caché de datos**: calcular de antemano los datos que se utilizan repetidamente durante el filtrado.
4. **Estado compartido**: gestionar la información de estado utilizada por varios plugins.

**Problemas con las otras opciones:**
- B. Puntuar nodos después del filtrado: Este es el rol del punto de extensión "Score".
- C. Realizar verificación antes de vincular Pods a nodos: Este es el rol del punto de extensión "PreBind".
- D. Ordenar Pods en la cola de planificación: Este es el rol del punto de extensión "QueueSort".
</details>

### 10. ¿Qué significa el taint de nodo `node.kubernetes.io/unreachable:NoExecute` en Kubernetes?

A. El nodo no es alcanzable y los Pods sin tolerations se eliminan
B. El nodo no es programable, pero los Pods existentes continúan ejecutándose
C. El nodo está en modo de mantenimiento y no se programan nuevos Pods
D. El nodo está en estado de escasez de recursos y preferentemente no se programan nuevos Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. El nodo no es alcanzable y los Pods sin tolerations se eliminan**

**Explicación:**
El taint `node.kubernetes.io/unreachable:NoExecute` indica que el nodo no es accesible y que se eliminan o expulsan los Pods sin una toleration coincidente. El controlador de nodos lo añade automáticamente cuando el estado del nodo pasa de `Ready` a `Unknown`.

**Causas habituales de que un nodo no sea accesible:**
1. Problemas de conectividad de red.
2. Caída del proceso kubelet.
3. Fallo del sistema del nodo.
4. Problemas de alimentación del nodo.

**Componentes del taint:**
1. **Clave**: `node.kubernetes.io/unreachable`.
2. **Valor**: normalmente una cadena vacía, aunque puede tener un valor.
3. **Efecto**: `NoExecute`; se eliminan los Pods que no tengan una toleration coincidente.

**Efecto `NoExecute`:**
1. Los Pods nuevos sin una toleration coincidente no se planifican en el nodo que tenga ese taint.
2. Entre los Pods que ya se ejecutan en el nodo, se eliminan los que no tengan una toleration para el taint.

**Taints del sistema:**
Kubernetes añade automáticamente los siguientes taints del sistema según el estado del nodo:
1. **node.kubernetes.io/not-ready:NoExecute**: El nodo no está listo
2. **node.kubernetes.io/unreachable:NoExecute**: El nodo no es alcanzable
3. **node.kubernetes.io/memory-pressure:NoSchedule**: El nodo tiene presión de memoria
4. **node.kubernetes.io/disk-pressure:NoSchedule**: El nodo tiene presión de disco
5. **node.kubernetes.io/pid-pressure:NoSchedule**: El nodo tiene presión de PID
6. **node.kubernetes.io/network-unavailable:NoSchedule**: La red del nodo no está disponible
7. **node.kubernetes.io/unschedulable:NoSchedule**: El nodo está marcado como no programable

**Tolerations predeterminadas:**
Con el comportamiento de admisión predeterminado, Kubernetes añade estas tolerations solo si no se han especificado ya otras equivalentes. Los Pods de DaemonSet reciben, en cambio, tolerations NoExecute indefinidas para not-ready y unreachable:
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

Estas tolerations predeterminadas permiten tolerar el taint durante 300 segundos desde que empieza su gestión; no constituyen un plazo exacto entre el fallo y el reemplazo. La detección del plano de control y la eliminación añaden demora, y un proceso desconectado puede seguir ejecutándose.

**Tolerations personalizadas:**
Las tolerations más largas retrasan el reemplazo y pueden prolongar una interrupción. Elige su duración según los requisitos de recuperación de la aplicación, sin asumir que un periodo mayor es más seguro:
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
    image: nginx:1.30.6
```

**Controlador de nodos y tiempos de expulsión:**
En la versión de referencia 1.35.8 del proyecto Kubernetes, `--node-monitor-period` tiene un valor predeterminado de 5 s y `--node-monitor-grace-period` de **50 s**, no 40 s. La opción antigua `--pod-eviction-timeout` no es el mecanismo actual para la expulsión por taints; esta depende de las tolerations coincidentes del Pod y del controlador de expulsión por taints. La detección, la publicación del taint, los límites de frecuencia del controlador y la eliminación pueden añadir demora.

Desde Kubernetes 1.29, la expulsión por taints se ejecuta en el controlador independiente `taint-eviction-controller`, habilitado por defecto y configurable por separado en planos de control autogestionados. Estos valores no son instrucciones de configuración de EKS ni una garantía del tiempo de conmutación ante fallos. Antes de forzar la eliminación de un Pod con estado en un nodo inaccesible, confirma que el escritor anterior está detenido o aislado para evitar escritores concurrentes.

**Comprobación del estado y los taints del nodo:**
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

**Gestión de taints en un scheduler personalizado:**
Al implementar un scheduler personalizado, debes considerar los taints de los nodos y las tolerations de los Pods.

```go
package diagnostic

import v1 "k8s.io/api/core/v1"

// This observes a taint; it is not a network probe or proof a process stopped.
func HasUnreachableTaint(node *v1.Node) bool {
    if node == nil {
        return false
    }
    for _, taint := range node.Spec.Taints {
        if taint.Key == "node.kubernetes.io/unreachable" && taint.Effect == v1.TaintEffectNoExecute {
            return true
        }
    }
    return false
}
```

**Por qué las demás opciones no son correctas:**
- B. El nodo no es planificable, pero los Pods existentes siguen ejecutándose: describe `NoSchedule`; `NoExecute` también elimina los Pods existentes sin tolerations.
- C. El nodo está en mantenimiento y no se planifican nuevos Pods: suele describir el taint `node.kubernetes.io/unschedulable:NoSchedule`.
- D. PreferNoSchedule es una preferencia flexible. Los taints habituales de presión de memoria y disco utilizan NoSchedule; ninguno describe unreachable:NoExecute.
</details>

## Referencias

Utiliza el [módulo de la parte 1](../../scheduling/01-custom-scheduler-part1.md) y la [implementación de la parte 2](../../scheduling/02-custom-scheduler-part2.md). Las comprobaciones de código y configuración son locales; no se realizó ningún despliegue en la nube ni ninguna expulsión.

* [Interfaces del framework en v1.35.8](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Tipos del protocolo de extenders](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [Afinidad de nodos y Pods](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [Restricciones de distribución topológica](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
* [Taints y tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
* [Prioridad y preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [Valores predeterminados del ciclo de vida de nodos](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/nodelifecycle/config/v1alpha1/defaults.go)
