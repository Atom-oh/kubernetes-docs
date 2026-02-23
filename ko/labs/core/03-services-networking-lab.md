# 서비스와 네트워킹 실습 가이드

> **난이도**: 중급
> **예상 소요 시간**: 45분
> **마지막 업데이트**: 2026년 2월 11일

## 학습 목표
- ClusterIP, NodePort Service를 생성합니다
- Service를 통한 Pod 접근을 실습합니다
- DNS 기반 서비스 디스커버리를 확인합니다

## 사전 요구 사항
- [ ] kubectl, Kubernetes 클러스터 (minikube/kind)
- [ ] [서비스와 네트워킹](../../core/03-services-networking.md) 학습 완료

---

## 실습 1: ClusterIP Service

### 단계

**Step 1.1: 백엔드 Deployment 생성**
```bash
kubectl create deployment web --image=nginx:1.25 --replicas=3
kubectl wait --for=condition=available deployment/web --timeout=60s
```

**Step 1.2: ClusterIP Service 생성**
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

**Step 1.3: 클러스터 내부에서 접근 테스트**
```bash
# 임시 Pod에서 Service 접근
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
```

<details>
<summary>힌트가 필요하신가요?</summary>

- ClusterIP는 클러스터 내부에서만 접근 가능합니다
- 서비스 DNS 형식: `<서비스명>.<네임스페이스>.svc.cluster.local`
- 같은 네임스페이스에서는 `<서비스명>`만으로도 접근 가능합니다
</details>

### 검증
```bash
kubectl get endpoints web-clusterip
# 3개의 Pod IP가 표시되어야 합니다
```

---

## 실습 2: NodePort Service

### 단계

**Step 2.1: NodePort Service 생성**
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

**Step 2.2: 외부에서 접근**
```bash
# minikube의 경우
minikube service web-nodeport --url 2>/dev/null || echo "NodePort: 30080"

# 노드 IP 확인
kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
```

### 검증
```bash
kubectl get svc web-nodeport -o jsonpath='{.spec.type}'
# 출력: NodePort
```

---

## 실습 3: DNS 서비스 디스커버리

### 단계

**Step 3.1: DNS 조회 테스트**
```bash
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup web-clusterip
```

예상 결과:
```
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      web-clusterip.default.svc.cluster.local
Address:   10.96.x.x
```

**Step 3.2: 다른 네임스페이스에서 접근**
```bash
kubectl create namespace test-ns
kubectl run cross-ns-test -n test-ns --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s http://web-clusterip.default.svc.cluster.local
kubectl delete namespace test-ns
```

<details>
<summary>힌트가 필요하신가요?</summary>

- 다른 네임스페이스에서 접근할 때는 FQDN을 사용해야 합니다
- CoreDNS가 클러스터 DNS를 관리합니다
- `kubectl get pods -n kube-system -l k8s-app=kube-dns`로 DNS Pod를 확인할 수 있습니다
</details>

---

## 정리
```bash
kubectl delete deployment web
kubectl delete svc web-clusterip web-nodeport
rm -f /tmp/clusterip-svc.yaml /tmp/nodeport-svc.yaml
```

## 다음 단계
- [서비스와 네트워킹 퀴즈](../../quizzes/core/03-services-networking-quiz.md)
- [스토리지 실습](./04-storage-lab.md)
