# Guía de laboratorio de Services and Networking

> **Dificultad**: Intermedio
> **Tiempo estimado**: 45 minutos
> **Última actualización**: February 11, 2026

## Objetivos de aprendizaje
- Crear Services ClusterIP y NodePort
- Practicar el acceso a Pods a través de Services
- Verificar el descubrimiento de Services basado en DNS

## Requisitos previos
- [ ] kubectl, cluster de Kubernetes (minikube/kind)
- [ ] Haber completado el aprendizaje de [Services and Networking](../../core/03-services-networking.md)

---

## Ejercicio 1: Service ClusterIP

### Pasos

**Paso 1.1: Crear Deployment de backend**
```bash
kubectl create deployment web --image=nginx:1.25 --replicas=3
kubectl wait --for=condition=available deployment/web --timeout=60s
```

**Paso 1.2: Crear Service ClusterIP**
```bash
cat > /tmp/clusterip-svc.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-clusterip
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f /tmp/clusterip-svc.yaml
kubectl get svc web-clusterip
```

**Paso 1.3: Probar el acceso desde dentro del cluster**
```bash
# Access the Service from a temporary Pod
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
```

<details>
<summary>¿Necesitas una pista?</summary>

- ClusterIP solo es accesible desde dentro del cluster
- Formato DNS del Service: `<service-name>.<namespace>.svc.cluster.local`
- Dentro del mismo namespace, puedes acceder usando solo `<service-name>`
</details>

### Verificación
```bash
kubectl get endpoints web-clusterip
# Should display 3 Pod IPs
```

---

## Ejercicio 2: Service NodePort

### Pasos

**Paso 2.1: Crear Service NodePort**
```bash
cat > /tmp/nodeport-svc.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport
spec:
  type: NodePort
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
EOF

kubectl apply -f /tmp/nodeport-svc.yaml
kubectl get svc web-nodeport
```

**Paso 2.2: Acceder desde fuera**
```bash
# For minikube
minikube service web-nodeport --url 2>/dev/null || echo "NodePort: 30080"

# Get node IP
kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
```

### Verificación
```bash
kubectl get svc web-nodeport -o jsonpath='{.spec.type}'
# Output: NodePort
```

---

## Ejercicio 3: Descubrimiento de Services con DNS

### Pasos

**Paso 3.1: Prueba de búsqueda DNS**
```bash
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup web-clusterip
```

Salida esperada:
```
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      web-clusterip.default.svc.cluster.local
Address:   10.96.x.x
```

**Paso 3.2: Acceder desde un namespace diferente**
```bash
kubectl create namespace test-ns
kubectl run cross-ns-test -n test-ns --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
kubectl delete namespace test-ns
```

<details>
<summary>¿Necesitas una pista?</summary>

- Al acceder desde un namespace diferente, debes usar el FQDN
- CoreDNS administra el DNS del cluster
- Comprueba los Pods de DNS con `kubectl get pods -n kube-system -l k8s-app=kube-dns`
</details>

---

## Limpieza
```bash
kubectl delete deployment web
kubectl delete svc web-clusterip web-nodeport
rm -f /tmp/clusterip-svc.yaml /tmp/nodeport-svc.yaml
```

## Próximos pasos
- [Quiz de Services and Networking](../../quizzes/core/03-services-networking-quiz.md)
- [Laboratorio de Storage](./04-storage-lab.md)
