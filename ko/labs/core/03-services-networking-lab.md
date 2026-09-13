# 서비스와 네트워킹 실습 가이드

> **난이도**: 중급
> **예상 소요 시간**: 45분
> **마지막 업데이트**: 2026년 9월 11일

## 학습 목표
- ClusterIP, NodePort Service를 생성합니다
- Service를 통한 Pod 접근을 실습합니다
- DNS 기반 서비스 디스커버리를 확인합니다

## 사전 요구 사항
- [ ] kubectl, Kubernetes 클러스터 (minikube/kind)
- [ ] [서비스와 네트워킹](../../core/03-services-networking.md) 학습 완료

폐기 가능한 kind/minikube 클러스터·일치하는 kubectl context·네임스페이스 생성 권한·정상 DNS/CNI/레지스트리 접근이 필요합니다. NetworkPolicy가 테스트 트래픽을 허용해야 합니다. NodePort는 노드 인터페이스를 노출할 수 있으므로 의도한 테스트 네트워크에서 사용하세요. 같은 Bash 세션에서 실행하며 이번 감사에서는 클러스터·트래픽 테스트를 수행하지 않았습니다.

```bash
SERVICE_LAB_DIR=$(mktemp -d /tmp/k8s-docs-services.XXXXXX)
: "${SERVICE_LAB_DIR:?mktemp failed}"
SERVICE_LAB_CONTEXT=$(kubectl config current-context)
: "${SERVICE_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$SERVICE_LAB_CONTEXT"
SERVICE_LAB_CANDIDATE=$(basename "$SERVICE_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset SERVICE_LAB_NAMESPACE SERVICE_LAB_CLIENT_NAMESPACE SERVICE_LAB_CLIENT_UID
if SERVICE_LAB_UID=$(kubectl --context "$SERVICE_LAB_CONTEXT" create namespace "$SERVICE_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_NAMESPACE=$SERVICE_LAB_CANDIDATE
else
  printf 'Namespace creation failed; stop before resource operations\n' >&2
fi
service_kubectl() {
  kubectl --context "${SERVICE_LAB_CONTEXT:?}" --namespace "${SERVICE_LAB_NAMESPACE:?}" "$@"
}
```

---

## 실습 1: ClusterIP Service

### 단계

**Step 1.1: 백엔드 Deployment 생성**
```bash
cat > "${SERVICE_LAB_DIR:?}/web-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
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
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/web-deployment.yaml"
service_kubectl rollout status deployment/web --timeout=120s
```

**Step 1.2: ClusterIP Service 생성**
```bash
cat > "${SERVICE_LAB_DIR:?}/clusterip-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-clusterip
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/clusterip-svc.yaml"
service_kubectl get service web-clusterip
```

**Step 1.3: 클러스터 내부에서 접근 테스트**
```bash
service_kubectl run http-check --image=busybox:1.37.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- sh -c '
for attempt in 1 2 3 4 5; do
  wget -T 5 -qO- "$1" && exit 0
  sleep 1
done
exit 1
' sh http://web-clusterip/
```
<details>
<summary>힌트가 필요하신가요?</summary>

- ClusterIP는 내부 가상 주소이며 보안 경계가 아닙니다. 라우팅에 따른 접근 가능성은 네트워크 구성에 달려 있습니다.
- 전체 DNS 형식은 `<서비스>.<네임스페이스>.svc.<클러스터 도메인>`이며 `cluster.local`은 흔한 기본값입니다.
- 일반적인 Pod DNS 검색 설정에서는 같은 namespace가 `<서비스>`, 다른 namespace가 `<서비스>.<네임스페이스>`를 사용할 수 있습니다.
</details>

### 검증
deprecated Endpoints 대신 EndpointSlice를 확인합니다. ready backend 주소를 확인하세요. 갱신은 비동기이고 slice·주소 계열별로 나뉠 수 있으므로 ready 복제본3개가 모든 출력에서 정확히3행을 뜻하지는 않습니다.

```bash
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip -o wide
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses}{" ready="}{.conditions.ready}{"\n"}{end}'
```

---

## 실습 2: NodePort Service

### 단계

**Step 2.1: NodePort Service 생성**
```bash
cat > "${SERVICE_LAB_DIR:?}/nodeport-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport
spec:
  type: NodePort
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/nodeport-svc.yaml"
SERVICE_LAB_NODE_PORT=$(service_kubectl get service web-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
: "${SERVICE_LAB_NODE_PORT:?No allocated NodePort}"
service_kubectl get service web-nodeport
```

**Step 2.2: 외부에서 접근**
30080이 비어 있다고 가정하지 않고 NodePort를 할당받습니다. Service 유형·포트 조회는 설정 확인이며 클라이언트 연결 증명이 아닙니다. 직접 노드 주소로 접근하려면 라우팅·nodePortAddresses·방화벽 정책이 허용해야 합니다.

```bash
printf 'Allocated NodePort: %s\n' "${SERVICE_LAB_NODE_PORT:?}"
kubectl --context "${SERVICE_LAB_CONTEXT:?}" get nodes -o wide

# Use only an address reachable from this client and permitted by node/firewall policy.
: "${SERVICE_LAB_NODE_ADDRESS:?Set a reachable node address}"
case "$SERVICE_LAB_NODE_ADDRESS" in
  *:*) SERVICE_LAB_NODE_URL_HOST="[$SERVICE_LAB_NODE_ADDRESS]" ;;
  *) SERVICE_LAB_NODE_URL_HOST=$SERVICE_LAB_NODE_ADDRESS ;;
esac
curl --disable --noproxy '*' --fail --show-error --silent --max-time 5 \
  "http://$SERVICE_LAB_NODE_URL_HOST:$SERVICE_LAB_NODE_PORT/"
```

minikube에서는 일치하는 profile을 선택합니다. 일부 Docker driver 플랫폼은 별도 터미널에서 service 명령의 tunnel을 유지해야 하며 출력된 URL로 접근합니다. 오류를 숨기거나 고정 포트 출력으로 대체하지 마세요. kind의 호스트 접근은 미리 구성한 extraPortMappings와 Service nodePort가 일치해야 합니다. 노드 IP에 접근할 수 없다면 별도로 선택한 `service_kubectl port-forward --address=127.0.0.1 service/web-nodeport 18080:80`으로 앱을 확인할 수 있지만 **NodePort 데이터 경로 검증은 아닙니다**.

```bash
# Only for minikube: the profile must correspond to SERVICE_LAB_CONTEXT.
: "${SERVICE_LAB_MINIKUBE_PROFILE:?Set the matching minikube profile}"
minikube --profile "$SERVICE_LAB_MINIKUBE_PROFILE" \
  service web-nodeport --namespace "${SERVICE_LAB_NAMESPACE:?}" --url
```
### 검증
```bash
service_kubectl get service web-nodeport -o jsonpath='{.spec.type}{"\n"}{.spec.ports[0].nodePort}{"\n"}'
```

---

## 실습 3: DNS 서비스 디스커버리

### 단계

**Step 3.1: DNS 조회 테스트**
```bash
service_kubectl run dns-check --image=busybox:1.37.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- nslookup web-clusterip
service_kubectl get service web-clusterip -o jsonpath='{.spec.clusterIP}{"\n"}'
```

Resolver IP·응답 IP·클러스터 도메인은 환경에 따라 달라집니다. 일반 ClusterIP Service인 이 예제는 개별 backend Pod IP가 아닌 위 Service 가상 IP로 해석되어야 합니다. 전체 이름에는 고정 default가 아닌 실습 namespace가 들어갑니다.

**Step 3.2: 다른 네임스페이스에서 접근**
```bash
SERVICE_LAB_CLIENT_CANDIDATE="${SERVICE_LAB_NAMESPACE:?}-client"
unset SERVICE_LAB_CLIENT_NAMESPACE
if SERVICE_LAB_CLIENT_UID=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" create namespace "$SERVICE_LAB_CLIENT_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_CLIENT_NAMESPACE=$SERVICE_LAB_CLIENT_CANDIDATE
  kubectl --context "$SERVICE_LAB_CONTEXT" --namespace "$SERVICE_LAB_CLIENT_NAMESPACE" \
    run cross-ns-check --image=busybox:1.37.0 \
    --overrides='{"spec":{"automountServiceAccountToken":false}}' \
    --rm -i --restart=Never --pod-running-timeout=120s --command -- \
    wget -T 5 -qO- "http://web-clusterip.$SERVICE_LAB_NAMESPACE/"
else
  printf 'Client namespace was not created; no cross-namespace test was run\n' >&2
fi
```

<details>
<summary>힌트가 필요하신가요?</summary>

- 표준 DNS 검색 경로에서는 다른 namespace의 `서비스.namespace`로 접근할 수 있으며 전체 도메인도 사용할 수 있습니다.
- CoreDNS 또는 설정한 클러스터 DNS 구현이 Service 레코드를 제공합니다.
- `kubectl get pods -n kube-system -l k8s-app=kube-dns`로 DNS Pod를 확인할 수 있습니다
</details>

---

## 정리
```bash
delete_service_lab_namespace() {
  local name="$1" expected_uid="$2" current_uid
  [[ -n "$name" && -n "$expected_uid" ]] || return 0
  current_uid=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" get namespace "$name" -o jsonpath='{.metadata.uid}') || return 0
  if [ "$current_uid" = "$expected_uid" ]; then
    kubectl --context "$SERVICE_LAB_CONTEXT" delete namespace "$name" --timeout=120s
  else
    printf 'Namespace identity changed; deletion skipped: %s\n' "$name"
  fi
}
delete_service_lab_namespace "${SERVICE_LAB_CLIENT_NAMESPACE:-}" "${SERVICE_LAB_CLIENT_UID:-}"
delete_service_lab_namespace "${SERVICE_LAB_NAMESPACE:-}" "${SERVICE_LAB_UID:-}"
if [[ -n ${SERVICE_LAB_DIR:-} ]]; then
  rm -f -- "$SERVICE_LAB_DIR/web-deployment.yaml" "$SERVICE_LAB_DIR/clusterip-svc.yaml" "$SERVICE_LAB_DIR/nodeport-svc.yaml"
  rmdir -- "$SERVICE_LAB_DIR"
fi
unset -f service_kubectl delete_service_lab_namespace
```


## 참고 자료와 검증 범위

* [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
* [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
* [minikube access](https://minikube.sigs.k8s.io/docs/handbook/accessing/)
* [kind port mappings](https://kind.sigs.k8s.io/docs/user/configuration/#extra-port-mappings)

로컬 매니페스트·명령 검사이며 실제 CNI·DNS·NodePort 실행 기록이 아닙니다. 임시 클라이언트는 명시적인 command를 사용하며 ServiceAccount 토큰이 필요하지 않습니다.

## 다음 단계
- [서비스와 네트워킹 퀴즈](../../quizzes/core/03-services-networking-quiz.md)
- [스토리지 실습](./04-storage-lab.md)
