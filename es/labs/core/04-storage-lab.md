# Guía del laboratorio de Storage

> **Dificultad**: Intermedia
> **Tiempo estimado**: 40 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Crear PersistentVolume (PV) y PersistentVolumeClaim (PVC)
- Montar y usar volúmenes en Pods
- Comparar los tipos de volumen emptyDir y hostPath

## Requisitos previos
- [ ] kubectl, clúster de Kubernetes
- [ ] Haber completado el aprendizaje de [Storage](../../core/04-storage.md)

---

## Ejercicio 1: Volumen emptyDir

### Pasos

**Paso 1.1: Crear un Pod usando emptyDir**
```bash
cat > /tmp/emptydir-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: emptydir-demo
spec:
  containers:
  - name: writer
    image: busybox
    command: ["sh", "-c", "while true; do echo $(date) >> /data/log.txt; sleep 5; done"]
    volumeMounts:
    - name: shared-data
      mountPath: /data
  - name: reader
    image: busybox
    command: ["sh", "-c", "tail -f /data/log.txt"]
    volumeMounts:
    - name: shared-data
      mountPath: /data
  volumes:
  - name: shared-data
    emptyDir: {}
EOF

kubectl apply -f /tmp/emptydir-pod.yaml
kubectl wait --for=condition=ready pod/emptydir-demo --timeout=30s
```

**Paso 1.2: Verificar el uso compartido de datos entre containers**
```bash
# Check reader container logs
kubectl logs emptydir-demo -c reader --tail=5

# Check file in writer container
kubectl exec emptydir-demo -c writer -- cat /data/log.txt
```

<details>
<summary>¿Necesitas una pista?</summary>

- `emptyDir` se crea cuando un Pod se asigna a un node y se elimina cuando se elimina el Pod
- Se usa para compartir datos entre containers en el mismo Pod
- Se usa con frecuencia en patrones sidecar de K8s
</details>

### Verificación
```bash
kubectl exec emptydir-demo -c writer -- wc -l /data/log.txt
```

---

## Ejercicio 2: Creación de PV/PVC

### Pasos

**Paso 2.1: Crear PersistentVolume**
```bash
cat > /tmp/pv.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolume
metadata:
  name: lab-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /tmp/k8s-lab-pv
EOF

kubectl apply -f /tmp/pv.yaml
kubectl get pv lab-pv
```

**Paso 2.2: Crear PersistentVolumeClaim**
```bash
cat > /tmp/pvc.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lab-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi
EOF

kubectl apply -f /tmp/pvc.yaml
kubectl get pvc lab-pvc
kubectl get pv lab-pv
```

Salida esperada:
```
NAME      STATUS   VOLUME   CAPACITY   ACCESS MODES
lab-pvc   Bound    lab-pv   1Gi        RWO
```

**Paso 2.3: Crear un Pod usando PVC**
```bash
cat > /tmp/pvc-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: pvc-demo
spec:
  containers:
  - name: app
    image: nginx:1.25
    volumeMounts:
    - name: persistent-storage
      mountPath: /usr/share/nginx/html
  volumes:
  - name: persistent-storage
    persistentVolumeClaim:
      claimName: lab-pvc
EOF

kubectl apply -f /tmp/pvc-pod.yaml
kubectl wait --for=condition=ready pod/pvc-demo --timeout=30s
```

**Paso 2.4: Probar la persistencia de datos**
```bash
# Write data
kubectl exec pvc-demo -- sh -c 'echo "Persistent Data" > /usr/share/nginx/html/index.html'

# Delete and recreate Pod
kubectl delete pod pvc-demo
kubectl apply -f /tmp/pvc-pod.yaml
kubectl wait --for=condition=ready pod/pvc-demo --timeout=30s

# Verify data
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
```

<details>
<summary>¿Necesitas una pista?</summary>

- PV es un recurso a nivel de clúster, PVC es un recurso a nivel de namespace
- El estado `Bound` significa que PVC está vinculado a un PV
- `persistentVolumeReclaimPolicy: Retain` conserva los datos incluso después de eliminar el PVC
</details>

### Verificación
```bash
kubectl exec pvc-demo -- cat /usr/share/nginx/html/index.html
# Output: Persistent Data (persists even after Pod recreation)
```

---

## Ejercicio 3: Comparación de tipos de volumen

### Pasos

**Paso 3.1: Comparar la información del volumen**
```bash
echo "=== emptyDir Pod ==="
kubectl get pod emptydir-demo -o jsonpath='{.spec.volumes[*].name}: {.spec.volumes[*].emptyDir}'
echo ""
echo "=== PVC Pod ==="
kubectl get pod pvc-demo -o jsonpath='{.spec.volumes[*].name}: {.spec.volumes[*].persistentVolumeClaim.claimName}'
echo ""
echo "=== PV Details ==="
kubectl get pv lab-pv -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,ACCESS:.spec.accessModes[0],STATUS:.status.phase'
```

---

## Limpieza
```bash
kubectl delete pod emptydir-demo pvc-demo
kubectl delete pvc lab-pvc
kubectl delete pv lab-pv
rm -f /tmp/emptydir-pod.yaml /tmp/pv.yaml /tmp/pvc.yaml /tmp/pvc-pod.yaml
```

## Próximos pasos
- [Cuestionario de Storage](../../quizzes/core/04-storage-quiz.md)
- [Laboratorio de ConfigMap y Secret](./05-configuration-secrets-lab.md)
