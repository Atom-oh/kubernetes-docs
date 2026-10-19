# Scheduler personalizado

> **Línea base del ejemplo**: Kubernetes 1.35.8, Go 1.27.2
> **Última actualización**: 16 de octubre de 2026

Kubernetes tiene un componente de planificación crítico que decide en qué nodo se ejecuta cada Pod. El scheduler predeterminado funciona bien en la mayoría de los casos, pero se puede implementar uno personalizado para requisitos específicos. En este capítulo aprenderá a implementar un scheduler personalizado en EKS.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitará las herramientas y el entorno siguientes:

### Herramientas necesarias

* kubectl cuya versión no difiera en más de una versión secundaria de la del servidor de API del clúster
* Go 1.27.2 y Python 3 para el ejemplo reproducible que sigue
* Un clúster Kubernetes 1.35 desechable con nodos de trabajo Linux; para EKS, consulte primero el [calendario de versiones de AWS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

Las interfaces del framework y la configuración se comprobaron con Kubernetes **1.35.8**. Esta es la línea base del ejemplo; no afirma que sea la versión más reciente de Kubernetes o EKS. Adapte el scheduler a la versión secundaria del clúster y vuelva a validar los plugins, las feature gates y RBAC al actualizar. El módulo de Kubernetes usa dependencias de staging; ejecutar `go get k8s.io/kubernetes` por sí solo no resuelve sus dependencias de staging `v0.0.0`.

### Configuración del entorno de desarrollo

```bash
mkdir -p custom-scheduler
cd custom-scheduler

# Generate a standalone module from the pinned upstream staging-module list.
python3 - <<'PY'
from pathlib import Path
import re
from urllib.request import urlopen

version = "v1.35.8"
staging_version = "v0.35.8"
url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/{version}/go.mod"
with urlopen(url, timeout=30) as response:
    upstream = response.read().decode()
modules = re.findall(r"^\s*(k8s\.io/[\w-]+) => \./staging/src/\1\s*$", upstream, re.M)
if not modules:
    raise RuntimeError("No staging modules found; review upstream go.mod")
text = f"module example.com/custom-scheduler\n\ngo 1.27.2\n\nrequire k8s.io/kubernetes {version}\n\nreplace (\n"
text += "".join(f"\t{m} => {m} {staging_version}\n" for m in modules)
Path("go.mod").write_text(text + ")\n")
PY
```

## Descripción general de la planificación

### Proceso de planificación de Kubernetes

El proceso de planificación de Kubernetes consta de las etapas siguientes:

### Explicación detallada de las etapas de planificación

1. **Etapa de filtrado**
   * Identifica los nodos adecuados para ejecutar el Pod.
   * Cada plugin de filtrado determina si un nodo puede alojarlo.
   * Si falla cualquier filtro, ese nodo se excluye de los candidatos.
2. **Etapa de puntuación**
   * Asigna puntuaciones a los nodos que superaron el filtrado.
   * Cada plugin de puntuación devuelve un valor de 0 a 100, después de la normalización opcional.
   * Las puntuaciones finales se calculan aplicando ponderaciones.
3. **Etapa de vinculación**
   * Asigna el Pod al nodo con la puntuación más alta.
   * La API de Kubernetes actualiza la vinculación entre el Pod y el nodo.

## Cuándo se necesitan schedulers personalizados

Considere usar un scheduler personalizado en los casos siguientes:

1. **Requisitos de hardware especiales**: GPU, FPGA, dispositivos de red especiales, etc.
2. **Reglas complejas de ubicación de cargas**: ubicar cargas específicas en grupos de nodos concretos.
3. **Optimización de costes**: ubicación óptima entre instancias Spot y bajo demanda.
4. **Requisitos de localidad**: ubicar cargas teniendo en cuenta la localidad de los datos.
5. **Varios schedulers**: usar distintos schedulers para diferentes tipos de cargas.

### Casos de uso reales

| Sector | Caso de uso | Ventajas del scheduler personalizado |
| ------------------ | ------------------------------ | --------------------------------------------------------- |
| Finanzas | Sistemas de negociación de alta frecuencia | Ubicación consciente de la topología de red para minimizar la latencia |
| Atención sanitaria | Procesamiento de imágenes médicas | Ubicación compatible con GPU y preferencias de localidad de datos |
| Telecomunicaciones | Funciones de red 5G | Restricciones de ubicación para dispositivos de red etiquetados |
| Comercio minorista | Gestión del tráfico estacional | Optimización rentable del uso de instancias Spot |
| Medios | Transcodificación de vídeo | Selección de nodos según los requisitos de CPU/GPU de la carga |

1. **Filtrado**: identifica los nodos donde puede ejecutarse el Pod. Esta etapa considera los requisitos de recursos, los selectores de nodos, la afinidad de nodos, las taints y tolerations, entre otros.
2. **Puntuación**: asigna puntuaciones a los nodos filtrados. Esta etapa considera el uso de recursos del nodo, la afinidad entre Pods, la afinidad de nodos y otros factores.
3. **Vinculación**: asigna el Pod al nodo con la puntuación más alta.

Antes de escribir código, compruebe si los plugins de dispositivos, la afinidad obligatoria o preferida, las taints y tolerations, y la distribución topológica ya expresan el requisito. Las solicitudes ordinarias de GPU no requieren un scheduler personalizado.

### Limitaciones del scheduler predeterminado

El scheduler predeterminado puede tener las limitaciones siguientes:

1. **Requisitos de hardware específicos**: puede ser necesaria una lógica de planificación avanzada para hardware especial, como GPU y FPGA.
2. **Reglas complejas de afinidad**: puede haber restricciones de ubicación difíciles de expresar con reglas básicas de afinidad.
3. **Métricas personalizadas**: la planificación puede tener que basarse en métricas personalizadas que el scheduler predeterminado no considera.
4. **Conocimiento específico del dominio**: puede ser necesaria una lógica de planificación especializada para determinados dominios de aplicación.

## Métodos de implementación de un scheduler personalizado

Hay tres enfoques principales para implementar un scheduler personalizado:

1. **Enfoque de varios schedulers**: ejecutar un scheduler personalizado junto al predeterminado.
2. **Enfoque de extender el scheduler**: ampliar el scheduler predeterminado con funciones adicionales de filtrado y prioridad.
3. **Plugins del Scheduler Framework**: desarrollar plugins mediante el framework de planificación introducido en Kubernetes 1.15.

### Enfoque de varios schedulers

En este enfoque, un scheduler personalizado se ejecuta junto al predeterminado. Al crear un Pod, puede especificar qué scheduler debe usar con el campo `schedulerName`.

#### Implementación del scheduler personalizado

Use el comando del scheduler de Kubernetes como base de un scheduler secundario. Así conserva `NodeResourcesFit`, `TaintToleration`, `NodeAffinity`, `VolumeBinding` y los demás plugins predeterminados. Elegir el primer nodo Ready y llamar a la API de vinculación omitiría esas comprobaciones.

Guarde lo siguiente como `main.go`. Todavía no añade una política personalizada de ubicación; las funciones auxiliares de puntuación posteriores y el cuestionario muestran puntos de extensión.

```go
package main

import (
    "os"

    "k8s.io/component-base/cli"
    "k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
    os.Exit(cli.Run(app.NewSchedulerCommand()))
}
```

#### Implementación del despliegue del scheduler personalizado

Guarde lo siguiente como `Dockerfile`, ejecute los comandos de compilación local y publique la imagen mediante el flujo de trabajo aprobado para su registro. Sustituya `registry.example.com/...` en el manifiesto por esa imagen, preferiblemente fijada mediante digest. El binario y la imagen deben corresponder a la arquitectura de los nodos de trabajo.

```dockerfile
FROM gcr.io/distroless/static-debian12:nonroot
COPY custom-scheduler /custom-scheduler
ENTRYPOINT ["/custom-scheduler"]
```

```bash
go mod tidy
CGO_ENABLED=0 go build -buildvcs=false -trimpath -o custom-scheduler .
# Build for the same architecture as the scheduler's worker nodes.
docker build -t custom-scheduler:v1.35.8-1 .
```

Este despliegue es de laboratorio; no es una receta de alta disponibilidad probada en producción. Los propios Pods del scheduler usan `default-scheduler` para poder iniciarse antes de que `custom-scheduler` esté disponible. Las dos réplicas comparten **un** Lease en `scheduler-lab`; otro grupo de schedulers necesita un Lease distinto. La antiafinidad preferida mejora la distribución, pero no garantiza la separación entre hosts o zonas de disponibilidad.

El administrador debe comprobar que existan los roles RBAC de arranque referenciados. `system:kube-scheduler` y `system:volume-scheduler` conceden permisos potentes en todo el clúster, incluidos los de vinculación y desalojo; `schedulerName` no es un límite de seguridad. El Role independiente añade acceso a nuestro Lease sin modificar los roles de arranque de Kubernetes. Mantenga privado el endpoint HTTPS. Pruebe el dimensionamiento de recursos y el comportamiento ante fallos en el clúster de destino.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: scheduler-lab
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scheduler-lab-scheduling
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:kube-scheduler
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scheduler-lab-volumes
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:volume-scheduler
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: scheduler-lab-authentication
  namespace: kube-system
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: extension-apiserver-authentication-reader
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: custom-scheduler-leader-election
  namespace: scheduler-lab
rules:
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  verbs: ["create"]
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  resourceNames: ["custom-scheduler"]
  verbs: ["get", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: custom-scheduler-leader-election
  namespace: scheduler-lab
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: custom-scheduler-leader-election
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-scheduler-config
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
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: custom-scheduler
  template:
    metadata:
      labels:
        app: custom-scheduler
    spec:
      serviceAccountName: custom-scheduler
      securityContext:
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      nodeSelector:
        kubernetes.io/os: linux
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              topologyKey: kubernetes.io/hostname
              labelSelector:
                matchLabels:
                  app: custom-scheduler
      containers:
      - name: custom-scheduler
        image: registry.example.com/training/custom-scheduler:v1.35.8-1
        args:
        - --config=/etc/scheduler/config.yaml
        - --cert-dir=/tmp
        ports:
        - name: https
          containerPort: 10259
        livenessProbe:
          httpGet:
            path: /healthz
            port: https
            scheme: HTTPS
          initialDelaySeconds: 15
        securityContext:
          runAsNonRoot: true
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
          seccompProfile:
            type: RuntimeDefault
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            memory: 512Mi
        volumeMounts:
        - name: config
          mountPath: /etc/scheduler
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: custom-scheduler-config
      - name: tmp
        emptyDir: {}
```

#### Uso del scheduler personalizado

Al crear un Pod, use el campo `schedulerName` para especificar el scheduler personalizado:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  schedulerName: custom-scheduler
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        memory: 128Mi
```

## Implementación de un scheduler personalizado en EKS

Al implementar un scheduler personalizado en Amazon EKS, tenga en cuenta lo siguiente:

1. **Autenticación y autorización de Kubernetes**: un scheduler dentro del clúster usa el token de su ServiceAccount y RBAC de Kubernetes. IAM solo es necesario si llama a las API de AWS, por ejemplo EC2 o CloudWatch; conceda a esa identidad de carga de trabajo únicamente los permisos de AWS requeridos.
2. **Plano de control administrado**: ejecute su propio scheduler secundario en los nodos de trabajo. No dé por hecho que puede acceder al proceso, los indicadores o el registro de plugins del scheduler predeterminado administrado.
3. **Límites de cómputo**: este ejemplo está dirigido a nodos de trabajo EC2. [EKS Fargate usa un scheduler y controladores de admisión administrados por AWS](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html); seleccionar un nodo Fargate o establecer `custom-scheduler` no aprovisiona capacidad de Fargate.
4. **Topología y etiquetas de instancias**: priorice las etiquetas de nodos existentes, las solicitudes de recursos, la afinidad y la distribución topológica. Un scheduler personalizado no crea capacidad ni garantiza la latencia.

### Arquitectura del scheduler personalizado en EKS

Cada scheduler observa la API de Kubernetes y mantiene su **propia caché y cola** para los Pods que le corresponden. El servidor de API almacena y expone el estado de los Pods; no es propietario de una cola de planificación compartida. La integración con EC2/CloudWatch es opcional; las consultas de métricas lentas o fallidas requieren tiempos de espera acotados y una política de respaldo explícita.

### Consideraciones de planificación específicas de EKS

Las funciones siguientes son **ayudas ilustrativas de puntuación flexible**, guardadas como archivos independientes en un paquete `preferences`. No se registran automáticamente en el binario anterior. Llámelas desde un plugin `Score` del framework probado, solo después de que pasen los filtros predeterminados. Una puntuación de **0 no excluye un nodo**; las reglas obligatorias corresponden a los filtros o a la afinidad requerida. Mantenga las puntuaciones entre 0 y 100.

#### 1. Planificación consciente del tipo de instancia

Las ponderaciones para c5/m5/r5 que siguen muestran preferencias basadas en etiquetas. No son clasificaciones de rendimiento medidas ni recomendaciones de compra para esas generaciones. Para una carga real, compare tipos de instancia adecuados mediante pruebas de rendimiento y configure la preferencia explícitamente.

```go
package preferences

import (
	"strings"

	v1 "k8s.io/api/core/v1"
)

// Illustrative weights, not measured performance or current purchase advice.
func ScoreInstanceType(node *v1.Node) int64 {
	switch {
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "c5."):
		return 100
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "m5."):
		return 50
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "r5."):
		return 30
	default:
		return 10
	}
}
```

#### 2. Planificación para distribuir entre zonas de disponibilidad

Prefiera el plugin integrado `PodTopologySpread` y `topologySpreadConstraints`. Si necesita puntuación personalizada, construya una instantánea coherente del ciclo a partir de la caché del scheduler, limitada a la carga prevista y a todas las zonas elegibles, incluidas las que no tienen Pods. Incluya los Pods asignados o supuestos según corresponda; contar solo los Pods en estado Running omite las reservas. No haga una llamada de listado u obtención a la API por cada nodo candidato ni convierta errores de API en recuentos inventados.

```go
package preferences

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
)

// counts is a consistent snapshot for one workload, including empty eligible zones.
// Build it once per scheduling cycle, not by making API calls for every node.
func ScoreAZ(node *v1.Node, counts map[string]int) (int64, error) {
	zone := node.Labels["topology.kubernetes.io/zone"]
	count, ok := counts[zone]
	if zone == "" || !ok {
		return 0, fmt.Errorf("missing eligible-zone snapshot for node %q", node.Name)
	}
	maxCount := 0
	for _, n := range counts {
		if n < 0 {
			return 0, fmt.Errorf("negative pod count")
		}
		if n > maxCount {
			maxCount = n
		}
	}
	if maxCount == 0 {
		return 100, nil
	}
	return int64(100 * (maxCount - count) / maxCount), nil
}
```

#### 3. Planificación consciente de instancias Spot

Los [grupos de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html) usan los valores `SPOT` / `ON_DEMAND` de `eks.amazonaws.com/capacityType`; [Karpenter](https://karpenter.sh/docs/concepts/nodepools/) usa `spot` / `on-demand` / `reserved` de `karpenter.sh/capacity-type`. `node.kubernetes.io/lifecycle` no es un equivalente estándar. Esta función auxiliar aplica una preferencia explícita del Pod; las etiquetas desconocidas no modifican la puntuación. Use la afinidad obligatoria cuando el tipo de capacidad sea un requisito. La puntuación no permite inferir el precio de Spot ni la tolerancia a interrupciones.

```go
package preferences

import v1 "k8s.io/api/core/v1"

func ScoreCapacityType(node *v1.Node, pod *v1.Pod) int64 {
	preferred := pod.Labels["lifecycle-preference"]
	if preferred != "spot" && preferred != "on-demand" {
		return 50
	}
	actual := node.Labels["karpenter.sh/capacity-type"]
	if actual == "" {
		switch node.Labels["eks.amazonaws.com/capacityType"] {
		case "SPOT":
			actual = "spot"
		case "ON_DEMAND":
			actual = "on-demand"
		}
	}
	if actual != "spot" && actual != "on-demand" && actual != "reserved" {
		return 50
	}
	if actual == preferred {
		return 100
	}
	return 0
}
```

#### 4. Planificación de cargas de trabajo con GPU

Un plugin de dispositivos debe anunciar el recurso GPU y el Pod admitido debe solicitarlo. Para recursos extendidos, si se especifica un límite sin solicitud, Kubernetes asigna a la solicitud el mismo valor que al límite; una solicitud de cero no implica demanda de GPU. `NodeResourcesFit` compara las solicitudes efectivas con los recursos asignables menos las solicitudes existentes o supuestas. El valor `Capacity` por sí solo no indica cuántas GPU están libres.

Esta función auxiliar solo desalienta que las cargas que no usan GPU ocupen nodos compatibles con GPU. Usa el helper de recursos versionado, que contabiliza init containers, sidecars y sobrecarga, y presupone un Pod cuyos valores predeterminados ya asignó la API. **No** establece que un nodo sea apto para GPU, no cubre todos los modelos de recursos DRA ni sustituye el filtro de recursos predeterminado.

```go
package preferences

import (
	v1 "k8s.io/api/core/v1"
	resourcehelper "k8s.io/component-helpers/resource"
)

// pod must be API-defaulted; limits-only extended resources acquire requests.
// NodeResourcesFit still decides whether the effective request fits.
func ScoreGPU(node *v1.Node, pod *v1.Pod) int64 {
	requests := resourcehelper.PodRequests(pod, resourcehelper.PodResourcesOptions{})
	gpuRequest := requests[v1.ResourceName("nvidia.com/gpu")]
	if gpuRequest.Sign() > 0 {
		return 50
	}
	gpuAllocatable := node.Status.Allocatable[v1.ResourceName("nvidia.com/gpu")]
	if gpuAllocatable.Sign() > 0 {
		return 0
	}
	return 100
}
```

## Conclusión

En este capítulo repasamos el proceso de planificación de Kubernetes y cómo implementar un scheduler personalizado con el enfoque de varios schedulers. También vimos consideraciones para implementar schedulers personalizados en clústeres de EKS.

En el capítulo siguiente aprenderemos a implementar schedulers personalizados mediante el enfoque de extender el scheduler y los plugins del Scheduler Framework.

## Verificación y referencias

El comando de Go, los plugins y la configuración se comprobaron localmente con las versiones fijadas de las dependencias. Para esta revisión no se desplegó ningún clúster, se publicó ninguna imagen ni se hicieron llamadas a AWS, pruebas de ubicación ni pruebas de conmutación por error de alta disponibilidad.

* [Configurar varios schedulers](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/): patrón de arquitectura/RBAC; los antiguos ejemplos de imágenes y compilación no son una guía de versiones
* [Configuración del scheduler](https://kubernetes.io/docs/reference/scheduling/config/)
* [Scheduler Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Interfaces del framework de Kubernetes 1.35.8](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Plugins predeterminados de Kubernetes 1.35.8](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/apis/config/v1/default_plugins.go)

## Cuestionario

Para comprobar lo aprendido, pruebe el [cuestionario del tema](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md).
