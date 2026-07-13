# Scheduler personalizado

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33 **Última actualización**: February 19, 2026

El scheduler de Kubernetes es un componente crítico que decide en qué node debe colocarse un Pod. Aunque el scheduler predeterminado funciona bien en la mayoría de los casos, puedes implementar un scheduler personalizado para requisitos específicos. En este capítulo, aprenderemos a implementar un scheduler personalizado en EKS.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Herramientas necesarias

* kubectl v1.31 o superior
* Go 1.19 o superior (para el desarrollo del scheduler personalizado)
* Un cluster de Kubernetes en funcionamiento (EKS, minikube, kind, etc.)

### Configuración del entorno de desarrollo

```bash
# Go development environment setup
mkdir -p $HOME/go/src/custom-scheduler
cd $HOME/go/src/custom-scheduler

# Initialize Go module
go mod init custom-scheduler

# Install required Kubernetes packages
go get k8s.io/kubernetes@v1.26.0
go get k8s.io/client-go@v0.26.0
go get k8s.io/klog/v2
```

## Descripción general del scheduling

### Proceso de scheduling de Kubernetes

El proceso de scheduling de Kubernetes consta de las siguientes etapas:

### Explicación detallada de las etapas de scheduling

1. **Fase de filtrado**
   * La etapa en la que se identifican los nodes adecuados para ejecutar el Pod
   * Cada filter plugin determina si un node puede alojar el Pod
   * Si algún filtro falla, ese node se excluye de los candidatos
2. **Fase de puntuación**
   * La etapa en la que se asignan puntuaciones a los nodes filtrados
   * Cada scoring plugin asigna una puntuación entre 0 y 100 a los nodes
   * Las puntuaciones finales se calculan aplicando pesos
3. **Fase de binding**
   * La etapa en la que el Pod se asigna al node con la puntuación más alta
   * La información de vinculación Pod-node se actualiza mediante la API de Kubernetes

## Cuándo se necesitan schedulers personalizados

Considera un scheduler personalizado en los siguientes casos:

1. **Requisitos de hardware especiales**: GPU, FPGA, dispositivos de red especiales, etc.
2. **Reglas complejas de colocación de workloads**: Colocar workloads específicos en node groups específicos
3. **Optimización de costos**: Colocación óptima entre instancias spot y on-demand
4. **Requisitos de localidad**: Colocación de workloads considerando la localidad de los datos
5. **Escenarios con múltiples schedulers**: Uso de múltiples schedulers para diferentes tipos de workloads

### Casos de uso del mundo real

| Industria          | Caso de uso                         | Beneficios del scheduler personalizado                                             |
| ------------------ | ----------------------------------- | ---------------------------------------------------------------------------------- |
| Finanzas           | Sistemas de trading de alta frecuencia | Colocación consciente de la topología de red para minimizar la latencia          |
| Salud              | Procesamiento de imágenes médicas   | Optimización de recursos GPU y garantía de localidad de datos                     |
| Telecomunicaciones | Funciones de red 5G                 | Garantía de proximidad a dispositivos de red específicos                          |
| Retail             | Manejo de tráfico estacional        | Optimización del uso rentable de instancias spot                                  |
| Medios             | Transcodificación de video          | Selección de nodes CPU/GPU basada en las características del workload             |

1. **Filtrado**: Identifica los nodes donde el Pod puede ejecutarse. Esta etapa considera los requisitos de recursos, node selectors, node affinity, taints y tolerations, etc.
2. **Puntuación**: Puntúa los nodes filtrados. Esta etapa considera el uso de recursos del node, inter-pod affinity, node affinity, etc.
3. **Binding**: Asigna el Pod al node con la puntuación más alta.

### Limitaciones del scheduler predeterminado

El scheduler predeterminado puede tener las siguientes limitaciones:

1. **Requisitos de hardware específicos**: Puede requerirse lógica avanzada de scheduling para hardware especial como GPU o FPGA.
2. **Reglas de affinity complejas**: Puede haber restricciones de colocación complejas que sean difíciles de expresar con reglas básicas de affinity.
3. **Métricas personalizadas**: Es posible que el scheduling deba basarse en métricas personalizadas que el scheduler predeterminado no considera.
4. **Conocimiento específico del dominio**: Puede requerirse lógica de scheduling especializada para dominios de aplicación específicos.

## Métodos de implementación de un scheduler personalizado

Existen tres enfoques principales para implementar un scheduler personalizado:

1. **Enfoque de múltiples schedulers**: Ejecutar un scheduler personalizado junto con el scheduler predeterminado.
2. **Enfoque de Scheduler Extender**: Extender el scheduler predeterminado para proporcionar funciones adicionales de filtrado y prioridad.
3. **Plugins del Scheduler Framework**: Desarrollar plugins usando el scheduler framework introducido en Kubernetes 1.15.

### Enfoque de múltiples schedulers

En el enfoque de múltiples schedulers, un scheduler personalizado se ejecuta junto con el scheduler predeterminado. Al crear un Pod, puedes especificar qué scheduler usar con el campo `schedulerName`.

#### Implementación del scheduler personalizado

Puedes implementar un scheduler personalizado usando el lenguaje Go. Aquí tienes un ejemplo sencillo:

```go
package main

import (
    "context"
    "fmt"
    "time"

    v1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/client-go/kubernetes"
    "k8s.io/client-go/rest"
)

func main() {
    // Create Kubernetes client
    config, err := rest.InClusterConfig()
    if err != nil {
        panic(err.Error())
    }
    clientset, err := kubernetes.NewForConfig(config)
    if err != nil {
        panic(err.Error())
    }

    // Scheduling loop
    for {
        // Find unscheduled pods
        pods, err := clientset.CoreV1().Pods("").List(context.TODO(), metav1.ListOptions{
            FieldSelector: "spec.schedulerName=custom-scheduler,spec.nodeName=",
        })
        if err != nil {
            fmt.Printf("Error listing pods: %v\n", err)
            time.Sleep(5 * time.Second)
            continue
        }

        // Schedule each pod
        for _, pod := range pods.Items {
            // Select node
            node, err := selectNode(clientset, &pod)
            if err != nil {
                fmt.Printf("Error selecting node for pod %s/%s: %v\n", pod.Namespace, pod.Name, err)
                continue
            }

            // Bind pod to node
            err = bindPod(clientset, &pod, node)
            if err != nil {
                fmt.Printf("Error binding pod %s/%s to node %s: %v\n", pod.Namespace, pod.Name, node, err)
                continue
            }

            fmt.Printf("Successfully scheduled pod %s/%s to node %s\n", pod.Namespace, pod.Name, node)
        }

        time.Sleep(1 * time.Second)
    }
}

// Node selection function
func selectNode(clientset *kubernetes.Clientset, pod *v1.Pod) (string, error) {
    // Get node list
    nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
    if err != nil {
        return "", err
    }

    // Simple example: select the first Ready node
    for _, node := range nodes.Items {
        for _, condition := range node.Status.Conditions {
            if condition.Type == v1.NodeReady && condition.Status == v1.ConditionTrue {
                return node.Name, nil
            }
        }
    }

    return "", fmt.Errorf("no ready nodes available")
}

// Function to bind pod to node
func bindPod(clientset *kubernetes.Clientset, pod *v1.Pod, node string) error {
    binding := &v1.Binding{
        ObjectMeta: metav1.ObjectMeta{
            Name:      pod.Name,
            Namespace: pod.Namespace,
        },
        Target: v1.ObjectReference{
            Kind:       "Node",
            Name:       node,
            APIVersion: "v1",
        },
    }

    return clientset.CoreV1().Pods(pod.Namespace).Bind(context.TODO(), binding, metav1.CreateOptions{})
}
```

#### Deployment del scheduler personalizado

Compila el scheduler personalizado como una imagen de contenedor y despliégalo en Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: custom-scheduler
  template:
    metadata:
      labels:
        app: custom-scheduler
    spec:
      serviceAccountName: custom-scheduler
      containers:
      - name: custom-scheduler
        image: your-registry/custom-scheduler:latest
        resources:
          requests:
            cpu: "100m"
            memory: "100Mi"
          limits:
            cpu: "200m"
            memory: "200Mi"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: custom-scheduler
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch", "update", "patch"]
- apiGroups: [""]
  resources: ["pods/binding"]
  verbs: ["create"]
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: custom-scheduler
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: kube-system
roleRef:
  kind: ClusterRole
  name: custom-scheduler
  apiGroup: rbac.authorization.k8s.io
```

#### Uso del scheduler personalizado

Al crear un Pod, usa el campo `schedulerName` para especificar el scheduler personalizado:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  schedulerName: custom-scheduler
  containers:
  - name: nginx
    image: nginx:latest
```

## Implementación de un scheduler personalizado en EKS

Al implementar un scheduler personalizado en Amazon EKS, considera lo siguiente:

1. **Permisos de IAM**: Se requieren permisos de IAM adecuados para que el scheduler personalizado interactúe con el cluster de EKS.
2. **Gestión de node groups**: La lógica de scheduling debe tener en cuenta diversos node groups (managed, self-managed, Fargate).
3. **Conciencia de Availability Zone**: Puede necesitarse lógica de scheduling para mantener el equilibrio entre Availability Zones.
4. **Conciencia de tipo de instancia**: Puede necesitarse lógica de scheduling para diversos tipos de instancia.

### Arquitectura de scheduler personalizado en EKS

El siguiente diagrama muestra cómo implementar un scheduler personalizado en un cluster de EKS:

### Consideraciones de scheduling específicas de EKS

#### 1. Scheduling consciente del tipo de instancia

En los clusters de EKS se pueden usar diversos tipos de instancia. El scheduler personalizado puede seleccionar tipos de instancia que coincidan con las características del workload.

```go
// Function to calculate score based on instance type
func scoreNodeByInstanceType(node *v1.Node) int {
    instanceType, exists := node.Labels["node.kubernetes.io/instance-type"]
    if !exists {
        return 0
    }

    // Assign scores to instance types based on workload characteristics
    switch {
    case strings.HasPrefix(instanceType, "c5"):
        return 10  // Compute-optimized instances
    case strings.HasPrefix(instanceType, "m5"):
        return 5   // General-purpose instances
    case strings.HasPrefix(instanceType, "r5"):
        return 3   // Memory-optimized instances
    default:
        return 1
    }
}
```

#### 2. Scheduling de distribución por Availability Zone

Puedes implementar lógica de scheduling para distribuir Pods entre múltiples Availability Zones y lograr alta disponibilidad en clusters de EKS.

```go
// Function to calculate score for availability zone distribution
func scoreNodeByAZ(node *v1.Node, pod *v1.Pod, clientset *kubernetes.Clientset) int {
    // Check node's availability zone
    zone, exists := node.Labels["topology.kubernetes.io/zone"]
    if !exists {
        return 0
    }

    // Query running pods in the current pod's namespace
    pods, err := clientset.CoreV1().Pods(pod.Namespace).List(context.TODO(), metav1.ListOptions{
        FieldSelector: "status.phase=Running",
    })
    if err != nil {
        return 0
    }

    // Calculate the number of pods in each availability zone
    azPodCount := make(map[string]int)
    for _, p := range pods.Items {
        if p.Spec.NodeName == "" {
            continue
        }

        node, err := clientset.CoreV1().Nodes().Get(context.TODO(), p.Spec.NodeName, metav1.GetOptions{})
        if err != nil {
            continue
        }

        if az, exists := node.Labels["topology.kubernetes.io/zone"]; exists {
            azPodCount[az]++
        }
    }

    // Assign higher score to availability zones with fewer pods
    totalAZs := len(azPodCount)
    if totalAZs == 0 {
        return 10
    }

    // Assign higher score if current AZ has fewer pods than average
    totalPods := 0
    for _, count := range azPodCount {
        totalPods += count
    }
    averagePods := float64(totalPods) / float64(totalAZs)

    if float64(azPodCount[zone]) < averagePods {
        return 10
    } else {
        return 5
    }
}
```

#### 3. Scheduling consciente de instancias spot

Puedes diferenciar entre instancias spot y on-demand para el scheduling y optimizar costos.

```go
// Spot instance-aware scheduling function
func scoreNodeByLifecycle(node *v1.Node, pod *v1.Pod) int {
    // Check node's lifecycle
    lifecycle, exists := node.Labels["node.kubernetes.io/lifecycle"]
    if !exists {
        return 5  // Middle score if no lifecycle info
    }

    // Check if pod has specific lifecycle requirements
    if pod.Labels["lifecycle-preference"] == "on-demand" {
        // Prefer on-demand instances
        if lifecycle == "on-demand" {
            return 10
        } else {
            return 1
        }
    } else if pod.Labels["lifecycle-preference"] == "spot" {
        // Prefer spot instances
        if lifecycle == "spot" {
            return 10
        } else {
            return 1
        }
    } else {
        // Default: prefer spot instances for cost optimization
        if lifecycle == "spot" {
            return 8
        } else {
            return 5
        }
    }
}
```

#### 4. Scheduling de workloads GPU

Puedes implementar lógica para programar workloads GPU de manera eficiente en clusters de EKS.

```go
// GPU workload scheduling function
func scoreNodeByGPU(node *v1.Node, pod *v1.Pod) int {
    // Check pod's GPU request
    gpuRequested := false
    for _, container := range pod.Spec.Containers {
        if _, exists := container.Resources.Requests["nvidia.com/gpu"]; exists {
            gpuRequested = true
            break
        }
    }

    // Check node's GPU availability
    gpuCapacity := 0
    if capacity, exists := node.Status.Capacity["nvidia.com/gpu"]; exists {
        gpuCapacity, _ = capacity.AsInt64()
    }

    // For GPU requests, assign higher score to nodes with GPUs
    if gpuRequested {
        if gpuCapacity > 0 {
            return 10
        } else {
            return 0  // Don't schedule on nodes without GPUs
        }
    } else {
        if gpuCapacity > 0 {
            return 1  // Lower score for non-GPU workloads on GPU nodes
        } else {
            return 5  // Higher score for non-GPU workloads on non-GPU nodes
        }
    }
}
```

## Conclusión

En este capítulo, cubrimos una descripción general del proceso de scheduling de Kubernetes y cómo implementar un scheduler personalizado usando el enfoque de múltiples schedulers. También exploramos consideraciones para implementar schedulers personalizados en clusters de EKS.

En el próximo capítulo, aprenderemos sobre la implementación de schedulers personalizados usando el enfoque de scheduler extender y plugins del scheduler framework.

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [cuestionario del tema](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md).
