# Kubernetes 클러스터 관리

Kubernetes 클러스터 관리는 클러스터의 설정, 유지 관리, 모니터링, 문제 해결 및 업그레이드를 포함하는 중요한 작업입니다. 이 장에서는 Kubernetes 클러스터 관리의 다양한 측면과 Amazon EKS에서의 클러스터 관리 모범 사례에 대해 알아보겠습니다.

## 목차
1. [클러스터 관리 개요](#클러스터-관리-개요)
2. [클러스터 구성요소 관리](#클러스터-구성요소-관리)
3. [리소스 관리](#리소스-관리)
4. [클러스터 네트워킹](#클러스터-네트워킹)
5. [인증 및 권한 관리](#인증-및-권한-관리)
6. [클러스터 업그레이드](#클러스터-업그레이드)
7. [백업 및 복구](#백업-및-복구)
8. [모니터링 및 로깅](#모니터링-및-로깅)
9. [문제 해결](#문제-해결)
10. [Amazon EKS 클러스터 관리](#amazon-eks-클러스터-관리)
11. [클러스터 관리 모범 사례](#클러스터-관리-모범-사례)
12. [결론](#결론)

## 클러스터 관리 개요

Kubernetes 클러스터 관리는 클러스터의 전체 수명 주기를 관리하는 과정입니다. 이는 다음과 같은 주요 영역을 포함합니다:

1. **클러스터 설정 및 구성**: 클러스터 생성, 노드 추가, 네트워킹 설정, 스토리지 구성 등
2. **운영 관리**: 리소스 모니터링, 성능 최적화, 용량 계획, 문제 해결
3. **보안 관리**: 인증, 권한 부여, 네트워크 정책, 보안 컨텍스트 등
4. **업그레이드 및 패치**: 클러스터 버전 업그레이드, 보안 패치 적용
5. **백업 및 복구**: 클러스터 데이터 백업, 재해 복구 계획

### 클러스터 관리 도구

Kubernetes 클러스터 관리를 위한 다양한 도구가 있습니다:

1. **kubectl**: Kubernetes 클러스터와 상호 작용하기 위한 명령줄 도구
2. **kubeadm**: Kubernetes 클러스터 생성 및 관리를 위한 도구
3. **kops**: Kubernetes 클러스터 생성, 업그레이드, 관리를 위한 도구
4. **eksctl**: Amazon EKS 클러스터 생성 및 관리를 위한 도구
5. **Helm**: Kubernetes 애플리케이션 패키지 관리자
6. **Kubernetes Dashboard**: 웹 기반 Kubernetes 사용자 인터페이스
7. **Prometheus & Grafana**: 모니터링 및 알림 도구
8. **Fluentd & Elasticsearch**: 로깅 도구

## 클러스터 구성요소 관리

Kubernetes 클러스터는 여러 구성요소로 이루어져 있으며, 이러한 구성요소를 효과적으로 관리하는 것이 중요합니다.

### 컨트롤 플레인 구성요소

컨트롤 플레인 구성요소는 클러스터의 전반적인 상태를 관리합니다:

1. **kube-apiserver**: Kubernetes API를 노출하는 컴포넌트
2. **etcd**: 클러스터 데이터를 저장하는 키-값 저장소
3. **kube-scheduler**: 포드를 노드에 스케줄링하는 컴포넌트
4. **kube-controller-manager**: 컨트롤러를 실행하는 컴포넌트
5. **cloud-controller-manager**: 클라우드 제공업체와 상호 작용하는 컴포넌트

#### 컨트롤 플레인 구성요소 모니터링

컨트롤 플레인 구성요소의 상태를 모니터링하는 것이 중요합니다:

```bash
# 컨트롤 플레인 구성요소 상태 확인
kubectl get componentstatuses

# API 서버 로그 확인
kubectl logs -n kube-system kube-apiserver-<node-name>

# etcd 상태 확인
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### 컨트롤 플레인 구성요소 구성

컨트롤 플레인 구성요소의 구성을 관리하는 방법:

```yaml
# kube-apiserver 구성 예시
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - command:
    - kube-apiserver
    - --advertise-address=192.168.1.10
    - --allow-privileged=true
    - --authorization-mode=Node,RBAC
    - --client-ca-file=/etc/kubernetes/pki/ca.crt
    - --enable-admission-plugins=NodeRestriction
    - --enable-bootstrap-token-auth=true
    - --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
    - --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt
    - --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key
    - --etcd-servers=https://127.0.0.1:2379
    - --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt
    - --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
    - --secure-port=6443
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: k8s.gcr.io/kube-apiserver:v1.21.0
    name: kube-apiserver
```

### 노드 구성요소

노드 구성요소는 각 노드에서 실행되며 포드를 관리합니다:

1. **kubelet**: 각 노드에서 실행되는 에이전트로, 포드와 컨테이너가 실행되도록 함
2. **kube-proxy**: 네트워크 규칙을 유지하고 연결 포워딩을 처리
3. **컨테이너 런타임**: 컨테이너를 실행하는 소프트웨어(Docker, containerd, CRI-O 등)

#### 노드 관리

노드 관리를 위한 주요 명령어:

```bash
# 노드 목록 확인
kubectl get nodes

# 노드 상세 정보 확인
kubectl describe node <node-name>

# 노드 레이블 추가
kubectl label node <node-name> key=value

# 노드 테인트 추가
kubectl taint node <node-name> key=value:NoSchedule

# 노드 유지 관리 모드 설정
kubectl cordon <node-name>

# 노드 드레인
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

#### 노드 문제 해결

노드 문제 해결을 위한 명령어:

```bash
# 노드 상태 확인
kubectl describe node <node-name> | grep Conditions -A 10

# 노드 리소스 사용량 확인
kubectl top node <node-name>

# kubelet 로그 확인
journalctl -u kubelet

# 컨테이너 런타임 상태 확인
systemctl status docker  # Docker 사용 시
systemctl status containerd  # containerd 사용 시
```

## 리소스 관리

Kubernetes 클러스터에서 리소스를 효과적으로 관리하는 것은 클러스터의 안정성과 성능을 유지하는 데 중요합니다.

### 리소스 쿼터

리소스 쿼터는 네임스페이스별로 리소스 사용량을 제한합니다:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
  namespace: dev
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    limits.memory: 2Gi
    pods: "10"
```

위 예시에서 `dev` 네임스페이스는 최대 10개의 포드, 1 CPU 및 1Gi 메모리 요청, 2 CPU 및 2Gi 메모리 제한을 가질 수 있습니다.

### 리밋 레인지

리밋 레인지는 네임스페이스 내의 개별 리소스에 대한 기본값과 제한을 설정합니다:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: limit-range
  namespace: dev
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 200m
      memory: 256Mi
    max:
      cpu: 1
      memory: 1Gi
    min:
      cpu: 100m
      memory: 128Mi
    type: Container
```

위 예시에서 `dev` 네임스페이스의 모든 컨테이너는 기본적으로 500m CPU 및 512Mi 메모리 제한, 200m CPU 및 256Mi 메모리 요청을 가지며, 최대 1 CPU 및 1Gi 메모리, 최소 100m CPU 및 128Mi 메모리를 가질 수 있습니다.

### 수평 포드 자동 확장(HPA)

HPA는 CPU 사용량이나 사용자 정의 메트릭을 기반으로 포드 수를 자동으로 조정합니다:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

위 예시에서 `frontend` 디플로이먼트는 CPU 사용률이 80%를 초과하면 자동으로 스케일 아웃되고, 80% 미만이면 스케일 인됩니다. 최소 2개, 최대 10개의 레플리카를 유지합니다.

### 수직 포드 자동 확장(VPA)

VPA는 포드의 CPU 및 메모리 요청을 자동으로 조정합니다:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: frontend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  updatePolicy:
    updateMode: "Auto"
```

위 예시에서 `frontend` 디플로이먼트의 포드는 실제 리소스 사용량을 기반으로 CPU 및 메모리 요청이 자동으로 조정됩니다.
## 클러스터 네트워킹

Kubernetes 클러스터 네트워킹은 포드, 서비스, 노드 간의 통신을 관리합니다.

### 클러스터 네트워크 모델

Kubernetes 네트워크 모델의 기본 요구 사항:

1. 모든 포드는 NAT 없이 다른 모든 포드와 통신할 수 있어야 함
2. 노드의 에이전트(kubelet)는 해당 노드의 모든 포드와 통신할 수 있어야 함
3. NAT 모드에서 실행되는 포드는 외부와 통신할 수 있어야 함

### CNI(Container Network Interface) 플러그인

Kubernetes는 CNI 플러그인을 통해 네트워킹을 구현합니다. 일반적인 CNI 플러그인:

1. **Calico**: 네트워크 정책 및 보안 기능이 강화된 CNI
2. **Flannel**: 간단한 오버레이 네트워크 제공
3. **Cilium**: eBPF 기반의 네트워킹 및 보안 솔루션
4. **AWS VPC CNI**: AWS VPC와 통합된 CNI
5. **Weave Net**: 멀티 호스트 컨테이너 네트워킹 솔루션

#### CNI 플러그인 설치 및 구성

CNI 플러그인 설치 예시(Calico):

```bash
# Calico 설치
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Calico 상태 확인
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### 서비스 네트워킹

Kubernetes 서비스는 포드 집합에 대한 안정적인 엔드포인트를 제공합니다:

1. **ClusterIP**: 클러스터 내부에서만 접근 가능한 서비스
2. **NodePort**: 모든 노드의 특정 포트를 통해 접근 가능한 서비스
3. **LoadBalancer**: 외부 로드 밸런서를 통해 접근 가능한 서비스
4. **ExternalName**: 외부 서비스에 대한 CNAME 레코드 제공

#### 서비스 CIDR 구성

서비스 CIDR은 서비스 IP 주소 범위를 정의합니다:

```bash
# kube-apiserver 구성에서 서비스 CIDR 설정
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS 관리

CoreDNS는 Kubernetes의 DNS 서비스를 제공합니다:

```bash
# CoreDNS 상태 확인
kubectl get pods -n kube-system -l k8s-app=kube-dns

# CoreDNS 구성 확인
kubectl get configmap -n kube-system coredns -o yaml
```

CoreDNS 구성 예시:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
           lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           fallthrough in-addr.arpa ip6.arpa
           ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### 네트워크 정책

네트워크 정책은 포드 간의 통신을 제어합니다:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

위 예시에서 `role=db` 레이블이 있는 포드는 `role=frontend` 레이블이 있는 포드로부터의 TCP 3306 포트 인바운드 트래픽과 `role=monitoring` 레이블이 있는 포드로의 TCP 9090 포트 아웃바운드 트래픽만 허용합니다.

## 인증 및 권한 관리

Kubernetes의 인증 및 권한 관리는 클러스터 보안의 핵심 요소입니다.

### 인증(Authentication)

Kubernetes는 다양한 인증 방법을 지원합니다:

1. **X.509 인증서**: 클라이언트 인증서를 사용한 인증
2. **서비스 계정 토큰**: 서비스 계정에 연결된 JWT 토큰
3. **OpenID Connect(OIDC)**: 외부 ID 제공자를 통한 인증
4. **웹훅 토큰 인증**: 외부 서비스를 통한 토큰 검증
5. **인증 프록시**: 인증 프록시를 통한 요청 처리

#### X.509 인증서 관리

X.509 인증서 생성 및 관리:

```bash
# 인증서 서명 요청(CSR) 생성
openssl req -new -key user.key -out user.csr -subj "/CN=user/O=group"

# CSR을 Kubernetes에 제출
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: user-csr
spec:
  request: $(cat user.csr | base64 | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  usages:
  - client auth
EOF

# CSR 승인
kubectl certificate approve user-csr

# 인증서 가져오기
kubectl get csr user-csr -o jsonpath='{.status.certificate}' | base64 --decode > user.crt
```

#### OIDC 인증 구성

OIDC 인증 구성 예시:

```bash
# kube-apiserver 구성에 OIDC 플래그 추가
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### 권한 부여(Authorization)

Kubernetes는 다양한 권한 부여 모드를 지원합니다:

1. **RBAC(Role-Based Access Control)**: 역할 기반 접근 제어
2. **ABAC(Attribute-Based Access Control)**: 속성 기반 접근 제어
3. **Node**: 노드 권한 부여
4. **Webhook**: 외부 서비스를 통한 권한 부여

#### RBAC 구성

RBAC는 가장 일반적인 권한 부여 메커니즘입니다:

```yaml
# Role 예시
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]

# RoleBinding 예시
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

위 예시에서 `user`는 `default` 네임스페이스의 포드를 조회할 수 있는 권한을 가집니다.

#### ClusterRole 및 ClusterRoleBinding

클러스터 전체 리소스에 대한 권한을 관리합니다:

```yaml
# ClusterRole 예시
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "watch", "list"]

# ClusterRoleBinding 예시
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-nodes
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: node-reader
  apiGroup: rbac.authorization.k8s.io
```

위 예시에서 `user`는 클러스터의 모든 노드를 조회할 수 있는 권한을 가집니다.

### 서비스 계정 관리

서비스 계정은 포드가 API 서버와 통신하는 데 사용됩니다:

```yaml
# 서비스 계정 생성
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default

# 서비스 계정에 권한 부여
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-service-account-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: my-service-account
  namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io

# 포드에서 서비스 계정 사용
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: nginx
```

### 보안 컨텍스트

보안 컨텍스트는 포드 및 컨테이너의 권한과 접근 제어를 정의합니다:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: security-context-container
    image: nginx
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

위 예시에서 포드는 UID 1000, GID 3000으로 실행되며, 컨테이너는 권한 상승이 불가능하고, 모든 Linux 기능이 제거되며, 루트 파일 시스템이 읽기 전용으로 마운트됩니다.

## 클러스터 업그레이드

Kubernetes 클러스터 업그레이드는 새로운 기능, 성능 개선, 보안 패치를 적용하기 위해 필요합니다.

### 업그레이드 계획

클러스터 업그레이드를 계획할 때 고려해야 할 사항:

1. **버전 호환성**: Kubernetes 버전 간의 호환성 확인
2. **업그레이드 경로**: 지원되는 업그레이드 경로 확인
3. **다운타임**: 업그레이드 중 예상되는 다운타임 계획
4. **롤백 계획**: 문제 발생 시 롤백 계획 수립
5. **애플리케이션 영향**: 업그레이드가 애플리케이션에 미치는 영향 평가

### 컨트롤 플레인 업그레이드

kubeadm을 사용한 컨트롤 플레인 업그레이드:

```bash
# 업그레이드 계획 확인
kubeadm upgrade plan

# 첫 번째 컨트롤 플레인 노드 업그레이드
ssh control-plane-1
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade apply v1.22.0

# 추가 컨트롤 플레인 노드 업그레이드
ssh control-plane-2
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# kubelet 및 kubectl 업그레이드
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

### 워커 노드 업그레이드

워커 노드 업그레이드 과정:

```bash
# 노드 드레인
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# SSH로 노드에 접속
ssh <node-name>

# kubeadm 업그레이드
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# kubelet 및 kubectl 업그레이드
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# 노드 언코든
kubectl uncordon <node-name>
```

### 업그레이드 검증

업그레이드 후 클러스터 상태 검증:

```bash
# 노드 버전 확인
kubectl get nodes

# 컴포넌트 상태 확인
kubectl get componentstatuses

# 포드 상태 확인
kubectl get pods --all-namespaces

# 클러스터 기능 테스트
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80
kubectl get svc nginx
```
## 백업 및 복구

Kubernetes 클러스터의 백업 및 복구는 재해 복구 계획의 중요한 부분입니다.

### etcd 백업

etcd는 Kubernetes 클러스터의 모든 상태 정보를 저장하므로 정기적인 백업이 중요합니다:

```bash
# etcd 스냅샷 생성
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db

# 스냅샷 상태 확인
ETCDCTL_API=3 etcdctl --write-out=table snapshot status /backup/etcd-snapshot-2023-01-01-12-00-00.db
```

### etcd 복구

etcd 스냅샷에서 복구:

```bash
# 모든 Kubernetes 서비스 중지
sudo systemctl stop kubelet kube-apiserver kube-controller-manager kube-scheduler

# etcd 데이터 디렉토리 백업
sudo mv /var/lib/etcd /var/lib/etcd.bak

# 스냅샷에서 복구
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  --data-dir=/var/lib/etcd \
  --initial-cluster=master-1=https://192.168.1.10:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://192.168.1.10:2380 \
  snapshot restore /backup/etcd-snapshot-2023-01-01-12-00-00.db

# 권한 설정
sudo chown -R etcd:etcd /var/lib/etcd

# Kubernetes 서비스 재시작
sudo systemctl start etcd
sudo systemctl start kubelet kube-apiserver kube-controller-manager kube-scheduler
```

### 리소스 백업

Kubernetes 리소스를 YAML 파일로 백업:

```bash
# 모든 네임스페이스의 모든 리소스 백업
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  mkdir -p /backup/resources/$ns
  for resource in $(kubectl api-resources --namespaced=true -o name); do
    kubectl get -n $ns $resource -o yaml > /backup/resources/$ns/$resource.yaml
  done
done

# 클러스터 범위 리소스 백업
mkdir -p /backup/resources/cluster-scoped
for resource in $(kubectl api-resources --namespaced=false -o name); do
  kubectl get $resource -o yaml > /backup/resources/cluster-scoped/$resource.yaml
done
```

### 백업 자동화

백업 작업을 CronJob으로 자동화:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 0 * * *"  # 매일 자정에 실행
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: etcd-backup
            image: bitnami/etcd:latest
            command:
            - /bin/sh
            - -c
            - |
              ETCDCTL_API=3 etcdctl --endpoints=https://etcd-client:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db
            volumeMounts:
            - name: etcd-certs
              mountPath: /etc/kubernetes/pki/etcd
              readOnly: true
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd
              type: Directory
          - name: backup
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

## 모니터링 및 로깅

효과적인 모니터링 및 로깅은 클러스터 관리의 핵심 요소입니다.

### 모니터링 도구

Kubernetes 클러스터 모니터링을 위한 도구:

1. **Prometheus**: 메트릭 수집 및 저장
2. **Grafana**: 메트릭 시각화
3. **Alertmanager**: 알림 관리
4. **kube-state-metrics**: Kubernetes 객체 메트릭 생성
5. **metrics-server**: 리소스 사용량 메트릭 제공

#### Prometheus 및 Grafana 설치

Helm을 사용한 Prometheus 및 Grafana 설치:

```bash
# Helm 저장소 추가
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Prometheus 스택 설치
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### 주요 모니터링 메트릭

모니터링해야 할 주요 메트릭:

1. **노드 메트릭**: CPU, 메모리, 디스크, 네트워크 사용량
2. **포드 메트릭**: CPU, 메모리 사용량, 재시작 횟수
3. **컨테이너 메트릭**: CPU, 메모리 사용량, 파일 시스템 사용량
4. **API 서버 메트릭**: 요청 지연 시간, 요청 수, 오류율
5. **etcd 메트릭**: 디스크 I/O, 리더 변경, 커밋 지연 시간

### 로깅 도구

Kubernetes 클러스터 로깅을 위한 도구:

1. **Elasticsearch**: 로그 저장 및 검색
2. **Fluentd/Fluent Bit**: 로그 수집 및 전달
3. **Kibana**: 로그 시각화
4. **Loki**: 로그 집계 시스템
5. **Grafana**: 로그 시각화

#### EFK(Elasticsearch, Fluentd, Kibana) 스택 설치

Helm을 사용한 EFK 스택 설치:

```bash
# Elasticsearch 설치
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

# Fluentd 설치
helm install fluentd fluent/fluentd \
  --namespace logging

# Kibana 설치
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer
```

#### 로그 수집 구성

Fluentd 구성 예시:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: logging
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
      kubernetes_url https://kubernetes.default.svc
      bearer_token_file /var/run/secrets/kubernetes.io/serviceaccount/token
      ca_file /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    </filter>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch-master
      port 9200
      logstash_format true
      logstash_prefix k8s
    </match>
```

## 문제 해결

Kubernetes 클러스터 문제 해결은 클러스터 관리의 중요한 부분입니다.

### 포드 문제 해결

포드 문제 해결을 위한 명령어:

```bash
# 포드 상태 확인
kubectl get pod <pod-name> -o wide

# 포드 상세 정보 확인
kubectl describe pod <pod-name>

# 포드 로그 확인
kubectl logs <pod-name>
kubectl logs <pod-name> -c <container-name>  # 다중 컨테이너 포드의 경우
kubectl logs <pod-name> --previous  # 이전 컨테이너의 로그

# 포드 내 명령 실행
kubectl exec -it <pod-name> -- /bin/sh
```

### 노드 문제 해결

노드 문제 해결을 위한 명령어:

```bash
# 노드 상태 확인
kubectl get node <node-name> -o wide

# 노드 상세 정보 확인
kubectl describe node <node-name>

# 노드 리소스 사용량 확인
kubectl top node <node-name>

# SSH로 노드에 접속
ssh <node-name>

# 노드 시스템 로그 확인
journalctl -u kubelet

# 노드 리소스 사용량 확인
top
df -h
free -m
```

### 네트워킹 문제 해결

네트워킹 문제 해결을 위한 명령어:

```bash
# 서비스 상태 확인
kubectl get svc <service-name>

# 서비스 상세 정보 확인
kubectl describe svc <service-name>

# 엔드포인트 확인
kubectl get endpoints <service-name>

# DNS 확인
kubectl run -it --rm --restart=Never busybox --image=busybox -- nslookup <service-name>

# 네트워크 연결 테스트
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- <service-name>:<port>

# 네트워크 정책 확인
kubectl get networkpolicy
kubectl describe networkpolicy <policy-name>
```

### 컨트롤 플레인 문제 해결

컨트롤 플레인 문제 해결을 위한 명령어:

```bash
# 컴포넌트 상태 확인
kubectl get componentstatuses

# API 서버 로그 확인
kubectl logs -n kube-system kube-apiserver-<node-name>

# 컨트롤러 매니저 로그 확인
kubectl logs -n kube-system kube-controller-manager-<node-name>

# 스케줄러 로그 확인
kubectl logs -n kube-system kube-scheduler-<node-name>

# etcd 로그 확인
kubectl logs -n kube-system etcd-<node-name>
```

## Amazon EKS 클러스터 관리

Amazon EKS는 관리형 Kubernetes 서비스로, 클러스터 관리의 많은 부분을 자동화합니다.

### EKS 클러스터 구성

EKS 클러스터 구성 관리:

```bash
# EKS 클러스터 정보 확인
aws eks describe-cluster --name my-cluster

# EKS 클러스터 업데이트
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true

# EKS 클러스터 버전 업데이트
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.22
```

### EKS 노드 그룹 관리

EKS 노드 그룹 관리:

```bash
# 노드 그룹 정보 확인
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup

# 노드 그룹 스케일링
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=5

# 노드 그룹 업데이트
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### EKS 추가 기능 관리

EKS 추가 기능 관리:

```bash
# 사용 가능한 추가 기능 확인
aws eks describe-addon-versions \
  --kubernetes-version 1.22

# 추가 기능 설치
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.1-eksbuild.1

# 추가 기능 업데이트
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.2-eksbuild.1

# 추가 기능 삭제
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni
```

### EKS 클러스터 업그레이드

EKS 클러스터 업그레이드 과정:

1. **컨트롤 플레인 업그레이드**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.22
   ```

2. **추가 기능 업그레이드**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.2-eksbuild.1
   ```

3. **노드 그룹 업그레이드**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### EKS 클러스터 모니터링

EKS 클러스터 모니터링 도구:

1. **Amazon CloudWatch**: 메트릭, 로그, 알림
2. **AWS CloudTrail**: API 호출 로깅
3. **Amazon Managed Grafana**: 메트릭 시각화
4. **Amazon Managed Service for Prometheus**: 메트릭 수집 및 저장

CloudWatch Container Insights 활성화:

```bash
# Container Insights 활성화
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## 클러스터 관리 모범 사례

Kubernetes 및 EKS 클러스터 관리를 위한 모범 사례:

### 클러스터 구성 모범 사례

1. **Infrastructure as Code(IaC)**: Terraform, AWS CDK, eksctl 등을 사용하여 클러스터 구성 관리
2. **버전 관리**: 클러스터 구성을 버전 관리 시스템에 저장
3. **다중 환경**: 개발, 스테이징, 프로덕션 환경 분리
4. **네트워크 분리**: 적절한 네트워크 분리 및 보안 그룹 구성
5. **최소 권한 원칙**: 필요한 최소한의 권한만 부여

### 운영 모범 사례

1. **정기적인 백업**: etcd 및 중요 리소스 정기 백업
2. **모니터링 및 알림**: 포괄적인 모니터링 및 알림 시스템 구축
3. **로깅 중앙화**: 로그 중앙화 및 분석
4. **자동화**: 반복 작업 자동화
5. **재해 복구 계획**: 명확한 재해 복구 계획 수립 및 테스트

### 보안 모범 사례

1. **정기적인 업데이트**: 클러스터 및 노드 정기 업데이트
2. **네트워크 정책**: 적절한 네트워크 정책 구성
3. **암호화**: 저장 데이터 및 전송 중 데이터 암호화
4. **보안 컨텍스트**: 적절한 보안 컨텍스트 구성
5. **이미지 스캐닝**: 컨테이너 이미지 취약점 스캐닝

### 리소스 관리 모범 사례

1. **리소스 요청 및 제한**: 모든 포드에 적절한 리소스 요청 및 제한 설정
2. **네임스페이스 분리**: 워크로드를 네임스페이스로 분리
3. **리소스 쿼터**: 네임스페이스별 리소스 쿼터 설정
4. **HPA 및 VPA**: 자동 스케일링 구성
5. **노드 어피니티 및 테인트**: 워크로드 배치 최적화

### EKS 특화 모범 사례

1. **관리형 노드 그룹**: 가능한 경우 관리형 노드 그룹 사용
2. **Fargate**: 서버리스 워크로드에 Fargate 사용
3. **EKS 추가 기능**: 공식 EKS 추가 기능 사용
4. **IAM 역할 서비스 계정(IRSA)**: 포드별 IAM 권한 관리
5. **VPC CNI 사용자 지정**: 네트워킹 요구 사항에 맞게 VPC CNI 구성

## 결론

Kubernetes 클러스터 관리는 클러스터의 안정성, 보안, 성능을 유지하는 데 중요한 역할을 합니다. 이 장에서는 클러스터 구성요소 관리, 리소스 관리, 네트워킹, 인증 및 권한 관리, 업그레이드, 백업 및 복구, 모니터링 및 로깅, 문제 해결 등 클러스터 관리의 다양한 측면을 다루었습니다.

Amazon EKS를 사용하면 Kubernetes 컨트롤 플레인 관리의 복잡성을 줄이고, AWS 서비스와의 통합을 통해 클러스터 관리를 간소화할 수 있습니다. 그러나 효과적인 클러스터 관리를 위해서는 여전히 Kubernetes의 기본 개념과 모범 사례를 이해하는 것이 중요합니다.

클러스터 관리는 지속적인 과정이며, 클러스터의 요구 사항과 워크로드 특성에 따라 지속적으로 조정해야 합니다. 모니터링 도구를 활용하여 클러스터 상태를 추적하고, 자동화를 통해 반복 작업을 최소화하며, 모범 사례를 따라 클러스터의 안정성과 보안을 유지하는 것이 중요합니다.
