# Cilium 테스트 가이드

이 문서는 Cilium의 기능을 테스트하고 검증하는 방법을 제공합니다. Cilium 1.17 버전을 기준으로 작성되었으며, Kubernetes 1.30 이상 버전과의 호환성을 확인합니다.

## 사전 요구 사항

- Kubernetes 클러스터 (1.30 이상)
- kubectl 설치 및 구성
- Cilium CLI 설치
- Helm 3.12 이상 (선택 사항)

## 1. Cilium 설치 및 기본 테스트

### 1.1 Cilium CLI 설치

```bash
# Cilium CLI 설치
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# 버전 확인
cilium version
```

### 1.2 Cilium 설치

```bash
# 기본 설치
cilium install --version 1.17.0

# 또는 Helm을 사용한 설치
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.17.0 \
  --namespace kube-system
```

### 1.3 설치 상태 확인

```bash
# Cilium 상태 확인
cilium status

# 모든 Cilium 구성요소가 정상적으로 실행 중인지 확인
kubectl get pods -n kube-system -l k8s-app=cilium
```

### 1.4 기본 연결성 테스트

```bash
# Cilium 연결성 테스트 실행
cilium connectivity test
```

## 2. 네트워크 정책 테스트

### 2.1 테스트 애플리케이션 배포

```bash
# 테스트용 네임스페이스 생성
kubectl create namespace cilium-test

# 테스트 애플리케이션 배포
kubectl -n cilium-test apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  selector:
    matchLabels:
      app: frontend
  replicas: 2
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  selector:
    matchLabels:
      app: backend
  replicas: 2
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  type: ClusterIP
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  type: ClusterIP
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
EOF

# 배포 확인
kubectl -n cilium-test get pods,svc
```

### 2.2 기본 연결성 확인

```bash
# frontend에서 backend로의 연결 테스트
FRONTEND_POD=$(kubectl -n cilium-test get pods -l app=frontend -o jsonpath='{.items[0].metadata.name}')
kubectl -n cilium-test exec $FRONTEND_POD -- curl -s backend
```

### 2.3 네트워크 정책 적용

```bash
# Cilium 네트워크 정책 적용
kubectl -n cilium-test apply -f - <<EOF
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-to-backend"
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
EOF

# 정책 확인
kubectl -n cilium-test get ciliumnetworkpolicies
```

### 2.4 정책 적용 후 연결성 테스트

```bash
# frontend에서 backend로의 연결 테스트 (허용됨)
FRONTEND_POD=$(kubectl -n cilium-test get pods -l app=frontend -o jsonpath='{.items[0].metadata.name}')
kubectl -n cilium-test exec $FRONTEND_POD -- curl -s backend

# 다른 Pod에서 backend로의 연결 테스트 (차단됨)
kubectl -n cilium-test run test-pod --image=curlimages/curl --rm -it -- curl -s --connect-timeout 5 backend
```

## 3. Hubble 가시성 테스트

### 3.1 Hubble 활성화

```bash
# Hubble 활성화
cilium hubble enable

# 상태 확인
cilium status
```

### 3.2 Hubble UI 설치 (선택 사항)

```bash
# Hubble UI 설치
cilium hubble enable --ui

# 포트 포워딩 설정
cilium hubble ui
```

### 3.3 Hubble 흐름 관찰

```bash
# Hubble CLI 설치
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Hubble 연결 설정
cilium hubble port-forward &

# 네트워크 흐름 관찰
hubble observe --namespace cilium-test
```

## 4. 성능 테스트

### 4.1 기본 성능 테스트

```bash
# 성능 테스트용 네임스페이스 생성
kubectl create namespace perf-test

# 성능 테스트 애플리케이션 배포
kubectl -n perf-test apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: perf-client
spec:
  selector:
    matchLabels:
      app: perf-client
  replicas: 1
  template:
    metadata:
      labels:
        app: perf-client
    spec:
      containers:
      - name: netperf
        image: networkstatic/iperf3
        command: ["sleep", "infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: perf-server
spec:
  selector:
    matchLabels:
      app: perf-server
  replicas: 1
  template:
    metadata:
      labels:
        app: perf-server
    spec:
      containers:
      - name: netperf
        image: networkstatic/iperf3
        command: ["iperf3", "-s"]
        ports:
        - containerPort: 5201
---
apiVersion: v1
kind: Service
metadata:
  name: perf-server
spec:
  type: ClusterIP
  selector:
    app: perf-server
  ports:
  - port: 5201
    targetPort: 5201
EOF

# 배포 확인
kubectl -n perf-test get pods
```

### 4.2 iperf3 성능 테스트 실행

```bash
# 클라이언트 Pod 이름 가져오기
CLIENT_POD=$(kubectl -n perf-test get pods -l app=perf-client -o jsonpath='{.items[0].metadata.name}')

# 서버 서비스 IP 가져오기
SERVER_IP=$(kubectl -n perf-test get svc perf-server -o jsonpath='{.spec.clusterIP}')

# TCP 성능 테스트
kubectl -n perf-test exec $CLIENT_POD -- iperf3 -c $SERVER_IP -t 30

# UDP 성능 테스트
kubectl -n perf-test exec $CLIENT_POD -- iperf3 -c $SERVER_IP -u -b 1G -t 30
```

## 5. 고급 기능 테스트

### 5.1 kube-proxy 대체 모드 테스트

```bash
# kube-proxy 대체 모드로 Cilium 재설치
cilium uninstall
cilium install --kube-proxy-replacement=strict

# 상태 확인
cilium status

# 서비스 연결성 테스트
cilium connectivity test
```

### 5.2 암호화 테스트

```bash
# IPsec 암호화로 Cilium 재설치
cilium uninstall
cilium install --encryption=ipsec

# 또는 WireGuard 암호화로 설치
cilium uninstall
cilium install --encryption=wireguard

# 상태 확인
cilium status

# 암호화 상태 확인
kubectl -n kube-system exec -ti ds/cilium -- cilium encrypt status
```

### 5.3 BGP 테스트 (고급)

```bash
# BGP 구성으로 Cilium 설치
helm install cilium cilium/cilium --version 1.17.0 \
  --namespace kube-system \
  --set bgp.enabled=true \
  --set bgp.announce.loadbalancerIP=true

# BGP 피어링 상태 확인
kubectl -n kube-system exec -ti ds/cilium -- cilium bgp peers
```

## 6. 호환성 테스트

### 6.1 Kubernetes 버전 호환성 확인

```bash
# Kubernetes 버전 확인
kubectl version --short

# Cilium 버전 확인
cilium version
```

### 6.2 커널 버전 호환성 확인

```bash
# 노드 커널 버전 확인
kubectl get nodes -o wide
kubectl debug node/<node-name> -it --image=ubuntu -- uname -r
```

### 6.3 CNI 호환성 확인

```bash
# CNI 구성 확인
kubectl -n kube-system exec -ti ds/cilium -- ls -la /etc/cni/net.d/
kubectl -n kube-system exec -ti ds/cilium -- cat /etc/cni/net.d/05-cilium.conf
```

## 7. 문제 해결 테스트

### 7.1 Cilium 진단 정보 수집

```bash
# Cilium 진단 정보 수집
cilium status --verbose
cilium clustermesh status
cilium hubble status

# 시스템 정보 수집
cilium sysdump
```

### 7.2 로그 분석

```bash
# Cilium 에이전트 로그 확인
kubectl -n kube-system logs -l k8s-app=cilium

# Cilium 오퍼레이터 로그 확인
kubectl -n kube-system logs -l name=cilium-operator

# Hubble 릴레이 로그 확인
kubectl -n kube-system logs -l k8s-app=hubble-relay
```

### 7.3 연결성 문제 해결

```bash
# 특정 엔드포인트 정보 확인
kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint list

# 특정 엔드포인트 상세 정보
ENDPOINT_ID=$(kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint list | grep <pod-name> | awk '{print $1}')
kubectl -n kube-system exec -ti ds/cilium -- cilium endpoint get $ENDPOINT_ID

# 정책 추적
kubectl -n kube-system exec -ti ds/cilium -- cilium policy trace --src-k8s-pod=<namespace>:<pod-name> --dst-k8s-pod=<namespace>:<pod-name> -d TCP/<port>
```

## 8. 정리

```bash
# 테스트 네임스페이스 삭제
kubectl delete namespace cilium-test
kubectl delete namespace perf-test

# Cilium 제거 (필요한 경우)
cilium uninstall
```

## 참고 자료

- [Cilium 공식 문서](https://docs.cilium.io/)
- [Cilium GitHub 저장소](https://github.com/cilium/cilium)
- [Hubble 문서](https://github.com/cilium/hubble)
- [Cilium 네트워크 정책 예제](https://docs.cilium.io/en/stable/policy/language/)
