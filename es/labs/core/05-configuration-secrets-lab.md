# Guía del laboratorio de ConfigMap y Secret

> **Dificultad**: Principiante
> **Tiempo estimado**: 35 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Crear ConfigMaps y usarlos en Pods
- Crear Secrets e inyectarlos de forma segura
- Comparar los métodos de variables de entorno y volume mount

## Requisitos previos
- [ ] kubectl, clúster de Kubernetes
- [ ] Haber completado el aprendizaje de [Configuration](../../core/05-configuration-secrets.md)

---

## Ejercicio 1: Creación y uso de ConfigMap

### Pasos

**Paso 1.1: Crear ConfigMap**
```bash
# Create from literal values
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

kubectl get configmap app-config -o yaml
```

**Paso 1.2: Crear ConfigMap desde un archivo**
```bash
cat > /tmp/app.properties << 'EOF'
database.host=mysql.default.svc.cluster.local
database.port=3306
database.name=myapp
EOF

kubectl create configmap app-properties --from-file=/tmp/app.properties
kubectl describe configmap app-properties
```

**Paso 1.3: Inyectar ConfigMap como variables de entorno**
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

Salida esperada:
```
APP_ENV=production LOG_LEVEL=info
```

**Paso 1.4: Montar ConfigMap como volumen**
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
<summary>¿Necesitas una pista?</summary>

- `envFrom` inyecta todas las claves de ConfigMap como variables de entorno
- Al montar como volumen, cada clave se convierte en un nombre de archivo
- Los ConfigMaps montados como volumen se actualizan automáticamente (las variables de entorno requieren reiniciar el Pod)
</details>

---

## Ejercicio 2: Gestión de Secret

### Pasos

**Paso 2.1: Crear Secret**
```bash
kubectl create secret generic db-secret \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASSWORD=s3cr3tP@ss

kubectl get secret db-secret -o yaml
```

**Paso 2.2: Inyectar Secret en un Pod**
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

Salida esperada:
```
User=admin
PassLength=10
```

**Paso 2.3: Decodificar Secret**
```bash
# Check base64 encoded value
kubectl get secret db-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
echo ""
```

<details>
<summary>¿Necesitas una pista?</summary>

- Los valores de Secret se almacenan codificados en base64 (¡esto no es cifrado!)
- En producción, usa Sealed Secrets, External Secrets, AWS Secrets Manager, etc.
- En `kubectl get secret -o yaml`, los valores del campo `.data` están codificados en base64
</details>

---

## Ejercicio 3: Comparación entre variables de entorno y volume mount

### Pasos

**Paso 3.1: Comprobar las características de cada método**
```bash
echo "=== Environment Variable Method ==="
kubectl exec config-env-demo -- env | grep -E "APP_ENV|LOG_LEVEL|MAX_CONNECTIONS"

echo ""
echo "=== Volume Mount Method ==="
kubectl exec config-vol-demo -- ls /config/
kubectl exec config-vol-demo -- cat /config/app.properties
```

---

## Limpieza
```bash
kubectl delete pod config-env-demo config-vol-demo secret-demo
kubectl delete configmap app-config app-properties
kubectl delete secret db-secret
rm -f /tmp/app.properties /tmp/configmap-env-pod.yaml /tmp/configmap-vol-pod.yaml /tmp/secret-pod.yaml
```

## Próximos pasos
- [Cuestionario de Configuration](../../quizzes/core/05-configuration-secrets-quiz.md)
- [Laboratorio de creación de clúster EKS](../eks/01-eks-cluster-creation-lab.md)
