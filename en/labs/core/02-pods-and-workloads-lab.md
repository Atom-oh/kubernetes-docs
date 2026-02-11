# Pods and Workloads Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 50 minutes
> **Last Updated**: February 2025

## Learning Objectives
- Create and manage Pods using YAML
- Deploy and scale Deployments
- Perform rolling updates and rollbacks

## Prerequisites
- [ ] kubectl installed and cluster access (minikube or kind)
- [ ] Completed [Pods and Workloads](../../core/02-pods-and-workloads.md) learning

---

## Exercise 1: Pod Creation and Management

### Steps

**Step 1.1: Write Pod YAML**
```bash
cat > /tmp/nginx-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: nginx-lab
  labels:
    app: nginx
    env: lab
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "64Mi"
        cpu: "100m"
      limits:
        memory: "128Mi"
        cpu: "200m"
EOF

kubectl apply -f /tmp/nginx-pod.yaml
```

**Step 1.2: Check Pod status**
```bash
kubectl get pod nginx-lab -o wide
kubectl describe pod nginx-lab
kubectl logs nginx-lab
```

**Step 1.3: Access Pod internals**
```bash
kubectl exec -it nginx-lab -- bash
# Run inside:
curl localhost
exit
```

### Verification
```bash
kubectl get pod nginx-lab -o jsonpath='{.status.phase}'
# Output: Running
```

---

## Exercise 2: Deployment

### Steps

**Step 2.1: Create Deployment**
```bash
cat > /tmp/nginx-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx-deploy
  template:
    metadata:
      labels:
        app: nginx-deploy
    spec:
      containers:
      - name: nginx
        image: nginx:1.24
        ports:
        - containerPort: 80
EOF

kubectl apply -f /tmp/nginx-deployment.yaml
```

**Step 2.2: Check deployment status**
```bash
kubectl get deployment nginx-deploy
kubectl get replicaset
kubectl get pods -l app=nginx-deploy
```

**Step 2.3: Scaling**
```bash
kubectl scale deployment nginx-deploy --replicas=5
kubectl get pods -l app=nginx-deploy -w
# Press Ctrl+C to stop watching
```

<details>
<summary>Need a hint?</summary>

- `kubectl get pods -w` monitors changes in real-time
- ReplicaSet is automatically managed by the Deployment
- Use the `-l` option for label-based filtering
</details>

### Verification
```bash
READY=$(kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
echo "Ready replicas: $READY"
```

---

## Exercise 3: Rolling Update

### Steps

**Step 3.1: Update image**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:1.25 --record
kubectl rollout status deployment/nginx-deploy
```

**Step 3.2: Check update history**
```bash
kubectl rollout history deployment/nginx-deploy
kubectl get replicaset -o wide
```

### Verification
```bash
kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}'
# Output: nginx:1.25
```

---

## Exercise 4: Rollback

### Steps

**Step 4.1: Update with invalid image (intentional error)**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:invalid-tag --record
kubectl rollout status deployment/nginx-deploy --timeout=30s
```

**Step 4.2: Check error and rollback**
```bash
kubectl get pods -l app=nginx-deploy
kubectl rollback deployment/nginx-deploy 2>/dev/null || kubectl rollout undo deployment/nginx-deploy
kubectl rollout status deployment/nginx-deploy
```

### Verification
```bash
IMAGE=$(kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "Current image: $IMAGE"
[ "$IMAGE" = "nginx:1.25" ] && echo "Rollback successful!" || echo "Please verify the image"
```

---

## Cleanup
```bash
kubectl delete pod nginx-lab
kubectl delete deployment nginx-deploy
rm -f /tmp/nginx-pod.yaml /tmp/nginx-deployment.yaml
```

## Next Steps
- [Pods and Workloads Quiz](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Services and Networking Lab](./03-services-networking-lab.md)
