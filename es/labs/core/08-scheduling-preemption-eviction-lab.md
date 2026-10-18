# Laboratorio sobre estrategias de puntuación del planificador: LeastAllocated frente a MostAllocated

> **Dificultad**: Intermedia
> **Tiempo estimado**: 30 minutos
> **Última actualización**: 17 de septiembre de 2026

## Objetivos de aprendizaje
- Crear un clúster `kind` desechable de varios nodos dedicado a este laboratorio
- Forzar una utilización de CPU inicial desigual entre nodos mediante Pods fijados con `nodeName`
- Observar el comportamiento de ubicación `LeastAllocated` del planificador predeterminado en esa situación inicial
- Implementar un segundo planificador configurado con la estrategia de puntuación `MostAllocated` de `NodeResourcesFit` y comparar las decisiones de ubicación
- Explicar por qué el empaquetado compacto de `MostAllocated` beneficia a las cargas de trabajo por lotes que se ejecutan junto con Karpenter/Cluster Autoscaler

## Requisitos previos
- [ ] `kubectl`, `docker` (u otro runtime de contenedores compatible con kind)
- [ ] `kind` v0.20 o posterior (este laboratorio lo instala localmente si falta)
- [ ] Haber completado [Programación, prioridad de desalojo y desalojo](../../core/08-scheduling-preemption-eviction.md), en especial la sección [Estrategia de puntuación de NodeResourcesFit](../../core/08-scheduling-preemption-eviction.md#noderesourcesfit-scoring-strategy-leastallocated-vs-mostallocated)

Este laboratorio crea su propio clúster `kind` desechable de varios nodos; no reutiliza un clúster existente, ya que el experimento necesita al menos 3 nodos de trabajo con asignación de CPU observable de forma independiente. Al final del laboratorio se elimina todo. Ejecute los comandos en orden dentro de la misma shell; deténgase si falla un paso.

```bash
SCHED_LAB_DIR=$(mktemp -d /tmp/k8s-docs-sched.XXXXXX)
: "${SCHED_LAB_DIR:?mktemp failed}"
cd "$SCHED_LAB_DIR"

if ! command -v kind >/dev/null 2>&1; then
  KIND_ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
  curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-${KIND_ARCH}"
  chmod +x ./kind
  SCHED_LAB_KIND=./kind
else
  SCHED_LAB_KIND=kind
fi
"$SCHED_LAB_KIND" version
```

---

## Laboratorio 1: Crear el clúster de prueba y establecer una línea base desigual

### Pasos

**Paso 1.1: Crear un clúster kind con 3 nodos de trabajo**
```bash
cat > "$SCHED_LAB_DIR/kind-config.yaml" << 'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: scheduler-strategy-lab
nodes:
- role: control-plane
- role: worker
- role: worker
- role: worker
EOF

export KUBECONFIG="$SCHED_LAB_DIR/kubeconfig"
"$SCHED_LAB_KIND" create cluster --config "$SCHED_LAB_DIR/kind-config.yaml"
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"  cpu="}{.status.allocatable.cpu}{"\n"}{end}'
```
Los cuatro nodos informan la misma CPU asignable (los nodos kind son contenedores que comparten el host, por lo que la CPU asignable refleja el host y no una división real del hardware por nodo; espere un valor como `cpu=16` en cada nodo; el número exacto depende de su máquina).

**Paso 1.2: Registrar los nombres de los nodos de trabajo**
```bash
mapfile -t SCHED_LAB_WORKERS < <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep -v control-plane)
printf 'Workers: %s\n' "${SCHED_LAB_WORKERS[*]}"
kubectl create namespace sched-lab
```

**Paso 1.3: Fijar Pods de relleno para crear una utilización de CPU desigual**

Usamos `spec.nodeName` (que omite por completo el planificador) para que los tres nodos de trabajo partan de distintos niveles de utilización: el primero al 75 %, el segundo a aproximadamente el 37 % y el tercero al 0 %.

```bash
{
  for i in $(seq 1 12); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-busy-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[0]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
  for i in $(seq 1 6); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-medium-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[1]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
} > "$SCHED_LAB_DIR/filler-pods.yaml"

kubectl apply -f "$SCHED_LAB_DIR/filler-pods.yaml"
kubectl -n sched-lab wait --for=condition=Ready pod -l role=filler --timeout=120s
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### Resultado esperado
Debería observar aproximadamente lo siguiente:
- `${SCHED_LAB_WORKERS[0]}` (denominado **A**): 12000m solicitados, aproximadamente 75 %
- `${SCHED_LAB_WORKERS[1]}` (denominado **B**): 6000m solicitados, aproximadamente 37 %
- `${SCHED_LAB_WORKERS[2]}` (denominado **C**): aproximadamente 0m solicitados, 0 %

El porcentaje exacto depende del número de CPU del host que kind detecte; lo que importa es el orden A > B > C.

---

## Laboratorio 2: Observar el planificador predeterminado (`LeastAllocated`)

### Pasos

**Paso 2.1: Programar 6 Pods nuevos con el planificador predeterminado**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-default-${i}
  namespace: sched-lab
  labels: { role: batch-default }
spec:
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-default --timeout=60s
```

**Paso 2.2: Registrar dónde se ubicaron**
```bash
kubectl -n sched-lab get pods -l role=batch-default -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### Resultado esperado
Los 6 Pods se ubicarán en el nodo **C** (el que está más vacío), y su utilización quedará aproximadamente igual que la de B. Así funciona `LeastAllocated`: para cada Pod nuevo, el planificador predeterminado sigue eligiendo el nodo con más capacidad libre, de modo que la utilización converge entre los nodos en lugar de concentrarse en unos pocos. Después de este paso, los tres nodos de trabajo tendrán algo de carga y ninguno será un candidato claro para reducir la escala.

---

## Laboratorio 3: Implementar un segundo planificador con `MostAllocated` y comparar

### Pasos

**Paso 3.1: Restablecer el entorno (eliminar los Pods programados en el laboratorio 2 y mantener la línea base de relleno)**
```bash
kubectl -n sched-lab delete pod -l role=batch-default --wait=true
```

**Paso 3.2: Implementar un segundo kube-scheduler configurado con `MostAllocated`**
```bash
cat > "$SCHED_LAB_DIR/most-allocated-scheduler.yaml" << 'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-kube-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:kube-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-volume-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:volume-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: most-allocated-scheduler-config
  namespace: kube-system
data:
  config.yaml: |
    apiVersion: kubescheduler.config.k8s.io/v1
    kind: KubeSchedulerConfiguration
    leaderElection:
      leaderElect: false
    profiles:
    - schedulerName: most-allocated-scheduler
      pluginConfig:
      - name: NodeResourcesFit
        args:
          scoringStrategy:
            type: MostAllocated
            resources:
            - { name: cpu, weight: 1 }
            - { name: memory, weight: 1 }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector: { matchLabels: { app: most-allocated-scheduler } }
  template:
    metadata: { labels: { app: most-allocated-scheduler } }
    spec:
      serviceAccountName: most-allocated-scheduler
      containers:
      - name: kube-scheduler
        image: registry.k8s.io/kube-scheduler:v1.37.0
        command: ["kube-scheduler", "--config=/etc/kubernetes/scheduler-config/config.yaml", "-v=2"]
        volumeMounts:
        - { name: config, mountPath: /etc/kubernetes/scheduler-config }
      volumes:
      - name: config
        configMap: { name: most-allocated-scheduler-config }
EOF

kubectl apply -f "$SCHED_LAB_DIR/most-allocated-scheduler.yaml"
kubectl -n kube-system rollout status deployment/most-allocated-scheduler --timeout=120s
```
Ajuste `image: registry.k8s.io/kube-scheduler:v1.37.0` a la versión menor real de su clúster; compruébela con `kubectl version`. Un binario del planificador que se aleje más de una versión menor del servidor de API puede negarse a iniciar o comportarse de forma impredecible.

**Paso 3.3: Programar los mismos 6 Pods, esta vez mediante `schedulerName`**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-mostalloc-${i}
  namespace: sched-lab
  labels: { role: batch-mostalloc }
spec:
  schedulerName: most-allocated-scheduler
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-mostalloc --timeout=60s
```

**Paso 3.4: Registrar dónde se ubicaron y comparar**
```bash
kubectl -n sched-lab get pods -l role=batch-mostalloc -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### Resultado esperado y resultados de referencia

Este procedimiento exacto se ejecutó una vez durante la preparación de este laboratorio, en un clúster kind con 3 nodos de trabajo y 16 CPU asignables por nodo (`kubectl version` informó `v1.37.0`):

| Planificador / estrategia | Ubicación de los 6 Pods nuevos | Utilización final de CPU (A / B / C) |
|---|---|---|
| Predeterminado (`LeastAllocated`) | Los 6 en el nodo C | 75 % / 37 % / 37 % (los tres nodos ocupados) |
| `MostAllocated` | 3 en el nodo A, 3 en el nodo B | 93 % / 56 % / 0 % (el nodo C quedó completamente inactivo) |

Los porcentajes absolutos variarán según el número de CPU del host, pero el **patrón** debería reproducirse: `LeastAllocated` llena el nodo inactivo hasta igualarlo con los vecinos, mientras que `MostAllocated` sigue añadiendo Pods a los nodos ya ocupados y deja intacto el inactivo. Ese nodo inactivo es precisamente el que Cluster Autoscaler o una pasada de consolidación de Karpenter terminaría eliminando. Por eso `MostAllocated` encaja mejor con cargas de trabajo por lotes o trabajos de corta duración que se ejecutan junto con un autoscaler, mientras que `LeastAllocated` sigue siendo el valor predeterminado más seguro para servicios de larga duración y sensibles a la latencia que necesitan margen en cada nodo.

---

## Limpieza
```bash
unset KUBECONFIG
"$SCHED_LAB_KIND" delete cluster --name scheduler-strategy-lab --kubeconfig "$SCHED_LAB_DIR/kubeconfig"
rm -rf -- "$SCHED_LAB_DIR"
unset SCHED_LAB_DIR SCHED_LAB_KIND SCHED_LAB_WORKERS
```

## Referencias y alcance de la verificación

- [Configuración del planificador: documentación de Kubernetes](https://kubernetes.io/docs/reference/scheduling/config/)
- [Estrategias de puntuación de NodeResourcesFit](https://kubernetes.io/docs/reference/config-api/kube-scheduler-config.v1/)
- [Configurar varios planificadores](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/)

Este laboratorio se ejecutó de principio a fin (creación del clúster, Pods de relleno, ambas pasadas del planificador y limpieza) en un clúster `kind` aislado y desechable; no se tocó ningún clúster compartido ni recurso en la nube. La tabla de resultados de referencia anterior registra la salida realmente observada en esa ejecución, no una predicción hipotética.

## Pasos siguientes
- [Cuestionario sobre programación, prioridad de desalojo y desalojo](../../quizzes/core/08-scheduling-preemption-eviction-quiz.md)
- [Crear un planificador personalizado](../../scheduling/01-custom-scheduler-part1.md)
