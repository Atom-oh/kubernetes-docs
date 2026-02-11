# ConfigMap and Secret Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 35 minutes
> **Last Updated**: February 2025

## Learning Objectives
- Create ConfigMaps and use them in Pods
- Create Secrets and inject them securely
- Compare environment variable and volume mount methods

## Prerequisites
- [ ] kubectl, Kubernetes cluster
- [ ] Completed [Configuration](../../core/05-configuration-secrets.md) learning

---

## Exercise 1: ConfigMap Creation and Usage

### Steps

**Step 1.1: Create ConfigMap**
```bash
# Create from literal values
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

kubectl get configmap app-config -o yaml
```

**Step 1.2: Create ConfigMap from file**
```bash
cat > /tmp/app.properties << 'EOF'
database.host=mysql.default.svc.cluster.local
database.port=3306
database.name=myapp
EOF

kubectl create configmap app-properties --from-file=/tmp/app.properties
kubectl describe configmap app-properties
```

**Step 1.3: Inject ConfigMap as environment variables**
```bash
cat > /tmp/configmap-env-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-env-demo
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "echo APP_ENV=$APP_ENV LOG_LEVEL=$LOG_LEVEL; sleep 3600"]
    envFrom:
    - configMapRef:
        name: app-config
EOF

kubectl apply -f /tmp/configmap-env-pod.yaml
kubectl wait --for=condition=ready pod/config-env-demo --timeout=30s
kubectl logs config-env-demo
```

Expected output:
```
APP_ENV=production LOG_LEVEL=info
```

**Step 1.4: Mount ConfigMap as volume**
```bash
cat > /tmp/configmap-vol-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-vol-demo
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "cat /config/app.properties; sleep 3600"]
    volumeMounts:
    - name: config-volume
      mountPath: /config
  volumes:
  - name: config-volume
    configMap:
      name: app-properties
EOF

kubectl apply -f /tmp/configmap-vol-pod.yaml
kubectl wait --for=condition=ready pod/config-vol-demo --timeout=30s
kubectl logs config-vol-demo
```

<details>
<summary>Need a hint?</summary>

- `envFrom` injects all keys from ConfigMap as environment variables
- When mounting as volume, each key becomes a filename
- Volume-mounted ConfigMaps are automatically updated (environment variables require Pod restart)
</details>

---

## Exercise 2: Secret Management

### Steps

**Step 2.1: Create Secret**
```bash
kubectl create secret generic db-secret \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASSWORD=s3cr3tP@ss

kubectl get secret db-secret -o yaml
```

**Step 2.2: Inject Secret into Pod**
```bash
cat > /tmp/secret-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: secret-demo
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "echo User=$DB_USER; echo PassLength=${#DB_PASSWORD}; sleep 3600"]
    env:
    - name: DB_USER
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_USER
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_PASSWORD
EOF

kubectl apply -f /tmp/secret-pod.yaml
kubectl wait --for=condition=ready pod/secret-demo --timeout=30s
kubectl logs secret-demo
```

Expected output:
```
User=admin
PassLength=10
```

**Step 2.3: Decode Secret**
```bash
# Check base64 encoded value
kubectl get secret db-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
echo ""
```

<details>
<summary>Need a hint?</summary>

- Secret values are stored base64 encoded (this is not encryption!)
- In production, use Sealed Secrets, External Secrets, AWS Secrets Manager, etc.
- In `kubectl get secret -o yaml`, values in the `.data` field are base64 encoded
</details>

---

## Exercise 3: Environment Variables vs Volume Mount Comparison

### Steps

**Step 3.1: Check characteristics of each method**
```bash
echo "=== Environment Variable Method ==="
kubectl exec config-env-demo -- env | grep -E "APP_ENV|LOG_LEVEL|MAX_CONNECTIONS"

echo ""
echo "=== Volume Mount Method ==="
kubectl exec config-vol-demo -- ls /config/
kubectl exec config-vol-demo -- cat /config/app.properties
```

---

## Cleanup
```bash
kubectl delete pod config-env-demo config-vol-demo secret-demo
kubectl delete configmap app-config app-properties
kubectl delete secret db-secret
rm -f /tmp/app.properties /tmp/configmap-env-pod.yaml /tmp/configmap-vol-pod.yaml /tmp/secret-pod.yaml
```

## Next Steps
- [Configuration Quiz](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS Cluster Creation Lab](../eks/01-eks-cluster-creation-lab.md)
