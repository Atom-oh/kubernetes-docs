# Guía de laboratorio de Pods y Workloads

> **Dificultad**: Principiante
> **Tiempo estimado**: 50 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Crear y administrar Pods usando YAML
- Desplegar y escalar Deployments
- Realizar rolling updates y rollbacks

## Requisitos previos
- [ ] kubectl instalado y acceso al cluster (minikube o kind)
- [ ] Haber completado el aprendizaje de [Pods and Workloads](../../core/02-pods-and-workloads.md)

---

## Ejercicio 1: Creación y administración de Pod

### Pasos

**Paso 1.1: Escribir YAML de Pod**
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

**Paso 1.2: Comprobar el estado del Pod**
```bash
kubectl get pod nginx-lab -o wide
kubectl describe pod nginx-lab
kubectl logs nginx-lab
```

**Paso 1.3: Acceder al interior del Pod**
```bash
kubectl exec -it nginx-lab -- bash
# Run inside:
curl localhost
exit
```

### Verificación
```bash
kubectl get pod nginx-lab -o jsonpath='{.status.phase}'
# Output: Running
```

---

## Ejercicio 2: Deployment

### Pasos

**Paso 2.1: Crear Deployment**
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

**Paso 2.2: Comprobar el estado del Deployment**
```bash
kubectl get deployment nginx-deploy
kubectl get replicaset
kubectl get pods -l app=nginx-deploy
```

**Paso 2.3: Escalado**
```bash
kubectl scale deployment nginx-deploy --replicas=5
kubectl get pods -l app=nginx-deploy -w
# Press Ctrl+C to stop watching
```

<details>
<summary>¿Necesitas una pista?</summary>

- `kubectl get pods -w` supervisa los cambios en tiempo real
- ReplicaSet es administrado automáticamente por el Deployment
- Usa la opción `-l` para filtrar por labels
</details>

### Verificación
```bash
READY=$(kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
echo "Ready replicas: $READY"
```

---

## Ejercicio 3: Rolling Update

### Pasos

**Paso 3.1: Actualizar la imagen**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:1.25 --record
kubectl rollout status deployment/nginx-deploy
```

**Paso 3.2: Comprobar el historial de actualizaciones**
```bash
kubectl rollout history deployment/nginx-deploy
kubectl get replicaset -o wide
```

### Verificación
```bash
kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}'
# Output: nginx:1.25
```

---

## Ejercicio 4: Rollback

### Pasos

**Paso 4.1: Actualizar con una imagen no válida (error intencional)**
```bash
kubectl set image deployment/nginx-deploy nginx=nginx:invalid-tag --record
kubectl rollout status deployment/nginx-deploy --timeout=30s
```

**Paso 4.2: Comprobar el error y hacer rollback**
```bash
kubectl get pods -l app=nginx-deploy
kubectl rollback deployment/nginx-deploy 2>/dev/null || kubectl rollout undo deployment/nginx-deploy
kubectl rollout status deployment/nginx-deploy
```

### Verificación
```bash
IMAGE=$(kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
echo "Current image: $IMAGE"
[ "$IMAGE" = "nginx:1.25" ] && echo "Rollback successful!" || echo "Please verify the image"
```

---

## Limpieza
```bash
kubectl delete pod nginx-lab
kubectl delete deployment nginx-deploy
rm -f /tmp/nginx-pod.yaml /tmp/nginx-deployment.yaml
```

## Próximos pasos
- [Quiz de Pods and Workloads](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Laboratorio de Services and Networking](./03-services-networking-lab.md)
