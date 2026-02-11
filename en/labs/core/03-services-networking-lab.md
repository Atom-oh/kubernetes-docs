# Services and Networking Lab Guide

> **Difficulty**: Intermediate
> **Estimated Time**: 45 minutes
> **Last Updated**: February 2025

## Learning Objectives
- Create ClusterIP and NodePort Services
- Practice accessing Pods through Services
- Verify DNS-based service discovery

## Prerequisites
- [ ] kubectl, Kubernetes cluster (minikube/kind)
- [ ] Completed [Services and Networking](../../core/03-services-networking.md) learning

---

## Exercise 1: ClusterIP Service

### Steps

**Step 1.1: Create backend Deployment**
```bash
kubectl create deployment web --image=nginx:1.25 --replicas=3
kubectl wait --for=condition=available deployment/web --timeout=60s
```

**Step 1.2: Create ClusterIP Service**
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

**Step 1.3: Test access from inside the cluster**
```bash
# Access the Service from a temporary Pod
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
```

<details>
<summary>Need a hint?</summary>

- ClusterIP is only accessible from inside the cluster
- Service DNS format: `<service-name>.<namespace>.svc.cluster.local`
- Within the same namespace, you can access using just `<service-name>`
</details>

### Verification
```bash
kubectl get endpoints web-clusterip
# Should display 3 Pod IPs
```

---

## Exercise 2: NodePort Service

### Steps

**Step 2.1: Create NodePort Service**
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

**Step 2.2: Access from outside**
```bash
# For minikube
minikube service web-nodeport --url 2>/dev/null || echo "NodePort: 30080"

# Get node IP
kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
```

### Verification
```bash
kubectl get svc web-nodeport -o jsonpath='{.spec.type}'
# Output: NodePort
```

---

## Exercise 3: DNS Service Discovery

### Steps

**Step 3.1: DNS lookup test**
```bash
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup web-clusterip
```

Expected output:
```
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      web-clusterip.default.svc.cluster.local
Address:   10.96.x.x
```

**Step 3.2: Access from different namespace**
```bash
kubectl create namespace test-ns
kubectl run cross-ns-test -n test-ns --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
kubectl delete namespace test-ns
```

<details>
<summary>Need a hint?</summary>

- When accessing from a different namespace, you must use the FQDN
- CoreDNS manages cluster DNS
- Check DNS Pods with `kubectl get pods -n kube-system -l k8s-app=kube-dns`
</details>

---

## Cleanup
```bash
kubectl delete deployment web
kubectl delete svc web-clusterip web-nodeport
rm -f /tmp/clusterip-svc.yaml /tmp/nodeport-svc.yaml
```

## Next Steps
- [Services and Networking Quiz](../../quizzes/core/03-services-networking-quiz.md)
- [Storage Lab](./04-storage-lab.md)
