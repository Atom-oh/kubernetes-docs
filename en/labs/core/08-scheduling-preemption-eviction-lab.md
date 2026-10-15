# Scheduler Scoring Strategy Lab: LeastAllocated vs. MostAllocated

> **Difficulty**: Intermediate
> **Estimated Time**: 30 minutes
> **Last Updated**: September 17, 2026

## Learning Objectives
- Stand up a disposable, multi-node `kind` cluster dedicated to this lab
- Force an uneven baseline CPU utilization across nodes using `nodeName`-pinned pods
- Observe the default scheduler's `LeastAllocated` placement behavior against that baseline
- Deploy a second scheduler configured with `NodeResourcesFit`'s `MostAllocated` scoring strategy and compare the placement decisions
- Explain why `MostAllocated` bin-packing benefits batch workloads running alongside Karpenter/Cluster Autoscaler

## Prerequisites
- [ ] `kubectl`, `docker` (or another kind-supported container runtime)
- [ ] `kind` v0.20+ (this lab installs it locally if missing)
- [ ] Completed [Scheduling, Preemption, and Eviction](../../core/08-scheduling-preemption-eviction.md), especially the [NodeResourcesFit Scoring Strategy](../../core/08-scheduling-preemption-eviction.md#noderesourcesfit-scoring-strategy-leastallocated-vs-mostallocated) section

This lab creates its own throwaway multi-node `kind` cluster — it does not reuse an existing cluster, since the experiment needs at least 3 worker nodes with independently observable CPU allocation. Everything is deleted at the end of the lab. Run commands in order in the same shell; stop if a step fails.

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

## Lab 1: Create the Test Cluster and an Uneven Baseline

### Steps

**Step 1.1: Create a 3-worker kind cluster**
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
All four nodes report the same allocatable CPU (kind nodes are containers sharing the host, so allocatable reflects the host, not a real per-node hardware split — expect a value like `cpu=16` on every node; the exact number depends on your machine).

**Step 1.2: Record the worker node names**
```bash
mapfile -t SCHED_LAB_WORKERS < <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep -v control-plane)
printf 'Workers: %s\n' "${SCHED_LAB_WORKERS[*]}"
kubectl create namespace sched-lab
```

**Step 1.3: Pin filler pods to create uneven CPU utilization**

We use `spec.nodeName` (which bypasses the scheduler entirely) to put the three workers at different starting utilization: the first worker at 75%, the second at ~37%, the third at 0%.

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

### Expected Outcome
You should see roughly:
- `${SCHED_LAB_WORKERS[0]}` (call it **A**): 12000m requested, ~75%
- `${SCHED_LAB_WORKERS[1]}` (call it **B**): 6000m requested, ~37%
- `${SCHED_LAB_WORKERS[2]}` (call it **C**): ~0m requested, 0%

The exact percentage depends on your host's CPU count reported to kind; what matters is the ordering A > B > C.

---

## Lab 2: Observe the Default Scheduler (`LeastAllocated`)

### Steps

**Step 2.1: Schedule 6 new pods with the default scheduler**
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

**Step 2.2: Record where they landed**
```bash
kubectl -n sched-lab get pods -l role=batch-default -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### Expected Outcome
All 6 pods land on node **C** (the emptiest one), bringing it up to roughly the same utilization as B. This is `LeastAllocated` in action: the default scheduler keeps picking the node with the most free capacity for each new pod, so utilization converges across nodes instead of concentrating on a few. After this step, all three worker nodes carry some load — none of them is a clean candidate for scale-down.

---

## Lab 3: Deploy a Second Scheduler with `MostAllocated` and Compare

### Steps

**Step 3.1: Reset — remove the pods scheduled in Lab 2, keep the filler baseline**
```bash
kubectl -n sched-lab delete pod -l role=batch-default --wait=true
```

**Step 3.2: Deploy a second kube-scheduler configured with `MostAllocated`**
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
Match `image: registry.k8s.io/kube-scheduler:v1.37.0` to your cluster's actual minor version — check with `kubectl version`. A scheduler binary more than one minor version away from the API server may refuse to start or behave unpredictably.

**Step 3.3: Schedule the same 6 pods, this time via `schedulerName`**
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

**Step 3.4: Record where they landed and compare**
```bash
kubectl -n sched-lab get pods -l role=batch-mostalloc -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### Expected Outcome and Reference Results

This exact procedure was run once while writing this lab, on a 3-worker kind cluster with 16 CPU allocatable per node (`kubectl version` reported `v1.37.0`):

| Scheduler / strategy | Where the 6 new pods landed | Final CPU utilization (A / B / C) |
|---|---|---|
| Default (`LeastAllocated`) | All 6 on node C | 75% / 37% / 37% — all three nodes occupied |
| `MostAllocated` | 3 on node A, 3 on node B | 93% / 56% / 0% — node C stayed completely idle |

Your absolute percentages will vary with your host's CPU count, but the **pattern** should reproduce: `LeastAllocated` fills the idle node until it matches its neighbors, while `MostAllocated` keeps piling onto the already-busy nodes and leaves the idle one untouched. That idle node is exactly what a Cluster Autoscaler or Karpenter consolidation pass would then terminate — which is why `MostAllocated` is the better fit for batch/short-lived job workloads that run alongside an autoscaler, while `LeastAllocated` remains the safer default for long-running, latency-sensitive services that want headroom on every node.

---

## Cleanup
```bash
unset KUBECONFIG
"$SCHED_LAB_KIND" delete cluster --name scheduler-strategy-lab --kubeconfig "$SCHED_LAB_DIR/kubeconfig"
rm -rf -- "$SCHED_LAB_DIR"
unset SCHED_LAB_DIR SCHED_LAB_KIND SCHED_LAB_WORKERS
```

## References and Verification Scope

- [Scheduler Configuration — Kubernetes documentation](https://kubernetes.io/docs/reference/scheduling/config/)
- [NodeResourcesFit scoring strategies](https://kubernetes.io/docs/reference/config-api/kube-scheduler-config.v1/)
- [Configure Multiple Schedulers](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/)

This lab was executed end-to-end (cluster creation, filler pods, both scheduler passes, cleanup) on an isolated, disposable `kind` cluster; no shared cluster or cloud resource was touched. The reference results table above records the actual observed output of that run, not a hypothetical prediction.

## Next Steps
- [Scheduling, Preemption, and Eviction Quiz](../../quizzes/core/08-scheduling-preemption-eviction-quiz.md)
- [Building a Custom Scheduler](../../scheduling/01-custom-scheduler-part1.md)
