# Pods and Workloads Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 50 minutes
> **Last Updated**: September 11, 2026

## Learning Objectives
- Create and manage Pods using YAML
- Deploy and scale Deployments
- Perform rolling updates and rollbacks

## Prerequisites
- [ ] kubectl installed and cluster access (minikube or kind)
- [ ] Completed [Pods and Workloads](../../core/02-pods-and-workloads.md) learning

Use an existing disposable kind/minikube cluster with permission to create a lab namespace and pull the example images. Confirm the selected context before running the setup. Keep one Bash session; the wrapper pins context and namespace. These steps make real changes when you run them; this audit performed no cluster operations.

```bash
WORKLOADS_LAB_DIR=$(mktemp -d /tmp/k8s-docs-workloads.XXXXXX)
: "${WORKLOADS_LAB_DIR:?mktemp failed}"
WORKLOADS_LAB_CONTEXT=$(kubectl config current-context)
: "${WORKLOADS_LAB_CONTEXT:?No current context selected}"
printf 'Selected context: %s\n' "$WORKLOADS_LAB_CONTEXT"
WORKLOADS_LAB_CANDIDATE=$(basename "$WORKLOADS_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset WORKLOADS_LAB_NAMESPACE WORKLOADS_LAB_GOOD_REVISION
if WORKLOADS_LAB_UID=$(kubectl --context "$WORKLOADS_LAB_CONTEXT" create namespace "$WORKLOADS_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  WORKLOADS_LAB_NAMESPACE=$WORKLOADS_LAB_CANDIDATE
else
  printf 'Namespace creation failed; do not continue with workload commands\n' >&2
fi
workload_kubectl() {
  kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" \
    --namespace "${WORKLOADS_LAB_NAMESPACE:?Create the lab namespace first}" "$@"
}
```

---

## Exercise 1: Pod Creation and Management

### Steps

**Step 1.1: Write Pod YAML**
```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: nginx-lab
  labels:
    app: nginx
    env: lab
spec:
  automountServiceAccountToken: false
  containers:
  - name: nginx
    image: nginx:1.30.4
    ports:
    - name: http
      containerPort: 80
    resources:
      requests:
        memory: 64Mi
        cpu: 100m
      limits:
        memory: 128Mi
        cpu: 200m
    readinessProbe:
      httpGet:
        path: /
        port: http
      periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-pod.yaml"
```

**Step 1.2: Check Pod status**
Running phase alone is not readiness. Wait for the configured HTTP readiness probe before logs/exec, and inspect failures rather than treating a timeout as success.

```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
workload_kubectl describe pod nginx-lab
workload_kubectl logs nginx-lab
```

**Step 1.3: Access Pod internals**
```bash
workload_kubectl exec -it nginx-lab -- sh
# Inside the container:
nginx -v
ls /usr/share/nginx/html/
exit
```

### Verification
```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
```

---

## Exercise 2: Deployment

### Steps

**Step 2.1: Create Deployment**
The Deployment retains old ready replicas during the intentional bad-image rollout with maxUnavailable0 and maxSurge1. Spare capacity is needed for surge and terminating Pods, plus the standalone Pod. This does not guarantee availability during unrelated failures.

```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  revisionHistoryLimit: 5
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: nginx-deploy
  template:
    metadata:
      labels:
        app: nginx-deploy
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.4
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
        readinessProbe:
          httpGet:
            path: /
            port: http
          periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
```

**Step 2.2: Check deployment status**
```bash
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get deployment nginx-deploy
workload_kubectl get replicasets,pods -l app=nginx-deploy
```

**Step 2.3: Scaling**
```bash
workload_kubectl scale deployment nginx-deploy --replicas=5
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get pods -l app=nginx-deploy
```

<details>
<summary>Need a hint?</summary>

- `kubectl get pods -w` monitors changes in real-time
- ReplicaSet is automatically managed by the Deployment
- Use the `-l` option for label-based filtering
</details>

### Verification
```bash
READY=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
printf 'Ready replicas: %s\n' "$READY"
[ "$READY" = "5" ]
```

---

## Exercise 3: Rolling Update

### Steps

**Step 3.1: Update image**
This changes the base-image variant of the same maintained NGINX release, not an old unsupported NGINX version. `kubernetes.io/change-cause` records intent without the deprecated --record flag. Capture the completed revision for the rollback exercise.

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="NGINX 1.30.4 Debian to Alpine variant" --overwrite
unset WORKLOADS_LAB_GOOD_REVISION
if workload_kubectl set image deployment/nginx-deploy nginx=nginx:1.30.4-alpine &&
   workload_kubectl rollout status deployment/nginx-deploy --timeout=120s; then
  WORKLOADS_LAB_GOOD_REVISION=$(workload_kubectl get deployment nginx-deploy \
    -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')
  : "${WORKLOADS_LAB_GOOD_REVISION:?No completed revision recorded}"
else
  printf 'Healthy rollout not confirmed; stop before the failure/rollback exercise\n' >&2
fi
```

**Step 3.2: Check update history**
```bash
workload_kubectl rollout history deployment/nginx-deploy
workload_kubectl get replicasets -l app=nginx-deploy -o wide
```

### Verification
```bash
workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
# Expected configured image: nginx:1.30.4-alpine
```

---

## Exercise 4: Rollback

### Steps

**Step 4.1: Update with invalid image (intentional error)**
The reserved .invalid registry is an intentional failure in this isolated lab. A rollout timeout can also result from scheduling, quota or API problems, so confirm Pod events/status. Rollback restores a retained Pod template, not external data, ConfigMap/Secret contents or database migrations.

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="Intentional lab image-pull failure" --overwrite
workload_kubectl set image deployment/nginx-deploy nginx=registry.invalid/training/nginx:unavailable
if workload_kubectl rollout status deployment/nginx-deploy --timeout=30s; then
  printf 'Unexpected completion; inspect which image is running\n'
else
  printf 'Rollout did not complete; inspect Pod status/events to identify the cause\n'
fi
```

**Step 4.2: Check error and rollback**
```bash
workload_kubectl get pods -l app=nginx-deploy
workload_kubectl describe deployment nginx-deploy
workload_kubectl get events --sort-by=.metadata.creationTimestamp
workload_kubectl rollout undo deployment/nginx-deploy \
  --to-revision="${WORKLOADS_LAB_GOOD_REVISION:?Complete Step 3.1 first}"
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

### Verification
```bash
IMAGE=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
printf 'Current image: %s\n' "$IMAGE"
[ "$IMAGE" = "nginx:1.30.4-alpine" ]
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

---

## Cleanup
```bash
# Delete the isolated lab namespace only if its recorded identity still matches.
if [[ -n ${WORKLOADS_LAB_NAMESPACE:-} && -n ${WORKLOADS_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" get namespace "$WORKLOADS_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$WORKLOADS_LAB_UID" ]; then
    kubectl --context "$WORKLOADS_LAB_CONTEXT" delete namespace "$WORKLOADS_LAB_NAMESPACE" --timeout=120s
  else
    printf 'Namespace missing or identity changed; automatic deletion skipped\n'
  fi
fi
if [[ -n ${WORKLOADS_LAB_DIR:-} ]]; then
  rm -f -- "$WORKLOADS_LAB_DIR/nginx-pod.yaml" "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
  rmdir -- "$WORKLOADS_LAB_DIR"
fi
unset -f workload_kubectl
```


## References and validation scope

* [Deployments, rollout and rollback](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
* [kubectl rollout undo](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_undo/)
* [Readiness and liveness probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

Manifests/commands were checked locally. No cluster deployment, image pull, scaling, rollback or namespace deletion was executed for this audit.

## Next Steps
- [Pods and Workloads Quiz](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Services and Networking Lab](./03-services-networking-lab.md)
