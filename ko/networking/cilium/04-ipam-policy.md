# IPAM 및 네트워크 정책

> **검토 기준**: Cilium 1.20.1, 테스트된 Kubernetes 1.33–1.36. 리소스 API 버전과 플랫폼 조건은 별도로 확인합니다.
> **최종 검토**: 2026년 9월 12일

## 실습 환경 설정

[설치 프로필](README.md)과 [네트워킹 조건](03-networking.md)에 따라 일회용 Linux 클러스터를 준비합니다. kubectl은 API 서버와 지원되는 버전 차이로 맞춥니다. 아래 IPAM 프로필은 설치·문서화된 마이그레이션의 선택지이며 실행 중인 클러스터에 ConfigMap을 순서대로 바꾸는 절차가 아닙니다.

정책 실습은 아래 별도 namespace와 일치하는 workload를 사용합니다. 이전 Cilium 1.14 Star Wars manifest는 정책의 label과 맞지 않았습니다. 기존 Kubernetes/Cilium cluster-wide 정책과 admission 설정부터 확인하며 새 namespace가 이를 무효화하지는 않습니다.

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

Namespace·release 이름이 다르면 실제 값을 사용합니다. 의도한 Helm values·ConfigMap, 노드 override, operator 설정, 에이전트 실현 상태는 다른 질문에 답합니다. `ipam`을 포함한 grep 결과만으로 전체 유효 설정을 확인할 수 없습니다.

## IP 주소 관리 전략

Cilium Pod IPAM은 workload 주소를 할당합니다. Service **ClusterIP**는 Kubernetes가 할당하며 Cilium **LoadBalancer IPAM**은 LoadBalancer 주소를 위한 별도 기능입니다. `CiliumPodIPPool`이 Service ClusterIP를 할당하지 않습니다.

### 할당 주체와 기준 데이터

| 설정 | 노드 용량·Pod IP 할당 주체 | 확인할 상태 |
|---|---|---|
| `cluster-pool`(일반 기본값) | Cilium Operator가 노드 CIDR, 각 에이전트가 로컬 주소 할당 | `CiliumNode.spec.ipam.podCIDRs`, operator 상태 |
| `kubernetes` / host scope | Kubernetes가 노드 PodCIDR 제공, 에이전트가 범위 내 할당 | Kubernetes `Node.spec.podCIDRs` / `spec.podCIDR`, 지원 provider annotation |
| `multi-pool` | 에이전트 수요에 따라 Operator가 이름 있는 풀의 블록 할당, 에이전트가 Pod IP 할당 | `CiliumPodIPPool`, `CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | 외부 할당기가 주소를 공급하고 에이전트가 사용·반납 | `CiliumNode.spec.ipam.pool` / `status.ipam.used` 및 해당 IPv6 필드 |
| `eni` | Operator가 AWS ENI·IP·prefix 관리, 에이전트가 인터페이스 상태를 multi-pool allocator로 변환 | `CiliumNode.status.eni.enis`, 모드별 pool·수요 상태 |
| `azure` | 자체 관리 Azure VM/VMSS용 upstream operator·agent 통합 | Azure/CiliumNode 할당 상태 |
| `delegated-plugin` | Cilium CNI가 관리형 AKS의 Azure IPAM 같은 외부 플러그인 호출 | Provider·plugin 상태. Upstream Azure IPAM 설정으로 대체하지 않음 |
| GKE 통합 | Upstream GKE 통합은 host-scope `kubernetes` IPAM 사용, 관리형 Dataplane V2는 별도 관리 주체 | Provider 설정·Node CIDR. 별도 `gke` IPAM 값이 아님 |

Cluster-pool과 Kubernetes host scope 모두 개별 Pod 주소를 로컬에서 할당합니다. 차이는 **노드 prefix**를 누가 할당하는지입니다. 조정이 없어지거나 사용자가 지정한 풀이 VPC·노드·Service·다른 클러스터와 겹치지 않는다고 보장하지 않습니다.

릴리스된 CRD·타입은 일반 CRD-backed 할당에 `pool`, `used`를 사용합니다. 일부 설명에 남아 있는 `available`/`inuse` 대신 설치된 스키마와 모드별 필드를 기준으로 합니다. 1.20.1의 ENI는 인터페이스·multi-pool 경로를 사용하므로 일반 CRD-backed 필드가 모든 ENI 상태의 기준은 아닙니다.

### Kubernetes/CNI 통합

Kubelet이 컨테이너 런타임에 Pod sandbox 작업을 요청하고 CNI 지원 런타임이 Cilium CNI 플러그인을 호출합니다. 선택한 backend로 주소를 할당한 뒤 plugin·agent가 endpoint 네트워크를 구성합니다. Host-scope 모드에서는 적절히 설정된 node-CIDR allocator 등으로 Kubernetes가 필요한 주소 계열의 CIDR을 제공해야 합니다.

## IPAM 구성

해당 설치 프로필과 합칠 **Helm values 조각**입니다. Pod·Service·노드·외부 네트워크 범위를 먼저 확인합니다.

### 클러스터 풀

**`cluster-pool-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
ipv4:
  enabled: true
ipv6:
  enabled: false
```


Operator는 노드 블록을 조정하며 Pod마다 중앙에서 주소를 요청하는 구조가 아닙니다. `clusterPoolIPv4PodCIDRList`의 여러 CIDR은 공통 할당 공간을 확장합니다. Workload별 이름 있는 풀 선택과는 다릅니다.

실행 중인 클러스터를 확장할 때 기존 목록 항목을 교체하지 않습니다. 문서화된 절차로 겹치지 않는 CIDR을 추가하며 노드 mask size를 일반적인 가변 설정으로 취급하지 않습니다. 예약 주소·노드 기능 때문에 블록 주소 수가 사용 가능한 Pod 수와 같지는 않습니다.

이미 Kubernetes/Cilium dual stack을 준비한 클러스터의 예입니다.

**`dual-stack-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList:
    - fd00:10:244::/104
    clusterPoolIPv6MaskSize: 120
ipv4:
  enabled: true
ipv6:
  enabled: true
```


이 두 Cilium 주소 계열 flag만으로 Kubernetes Service CIDR, underlay IPv6 연결이나 클라우드 지원이 구성되지 않습니다.

### Multi-Pool과 CiliumPodIPPool

문서화된 모드는 `multi-pool`이며 리소스 API는 여전히 `cilium.io/v2alpha1`입니다. API 접미사만으로 기능 성숙도를 추론하지 않습니다. 이 모드의 새 클러스터에는 일반 할당용 default pool을 준비합니다.

**`multi-pool-values.yaml`**

```yaml
ipam:
  mode: multi-pool
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4:
          cidrs:
          - 10.244.0.0/16
          maskSize: 24
```


추가 풀은 현재 필드인 `cidrs`, `maskSize`를 사용합니다.

**`blue-pool.yaml`**

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumPodIPPool
metadata:
  name: blue-pool
spec:
  ipv4:
    cidrs:
    - 10.245.0.0/16
    maskSize: 24
  namespaceSelector:
    matchLabels:
      ipam-pool: blue
  podSelector:
    matchLabels:
      role: blue
```


풀 리소스는 cluster 범위입니다. `podSelector`와 `namespaceSelector`는 별도 필드이며 둘 다 설정하면 모두 일치해야 합니다. 이전 `ipv4.cidr`, `blockSize`, 일반 `selector` 예제는 잘못되었습니다.

선택기 예제입니다.

**`blue-namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ipam-selection-demo
  labels:
    ipam-pool: blue
  annotations:
    ipam.cilium.io/require-pool-match: 'true'
```


**`blue-pod.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: blue-client
  namespace: ipam-selection-demo
  labels:
    role: blue
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


준비된 multi-pool 설치에서만 적용합니다. Namespace의 `require-pool-match`는 비기본 selector match가 필요할 때 자동 default pool fallback을 방지합니다.

풀 선택은 명시적인 Pod·namespace의 `ipam.cilium.io/ip-pool` 또는 주소 계열별 pool annotation, 자동 selector, default pool 순서입니다. 자동 선택은 주소 계열별로 정확히 한 풀과 일치해야 하며 겹치는 selector는 할당 실패를 일으킵니다. Pool annotation은 **새 할당**에 적용되고 기존 Pod IP를 바꾸지 않습니다. 노드별 기본 풀은 `CiliumNodeConfig`로도 구성할 수 있습니다.

풀 선택이 네트워크 인가를 대신하지 않습니다. Workload label·annotation 변경 권한을 통제하고 트래픽 정책을 별도로 적용합니다. 풀 CIDR은 겹치면 안 되며 사용 중인 범위·풀을 임의로 삭제하지 않습니다. `maskSize`, `allowFirstIP`, `allowLastIP`는 불변이고 첫·마지막 주소 예약에는 문서화된 작은 prefix 예외가 있습니다.

현재 **cluster-pool→multi-pool** 온라인 마이그레이션 절차가 문서화되어 있습니다. 임의의 실행 중 IPAM 전환이나 계획 없는 역방향 전환을 뜻하지 않습니다. 조건과 workload·용량을 검증해야 하며 이 장에서는 마이그레이션을 실행하지 않습니다.

### AWS ENI

라우팅, operator IAM, subnet·인스턴스 용량과 노드 준비는 전체 EKS/ENI 설치 프로필을 따릅니다. 다음은 선택적 IPv4 prefix delegation을 포함한 현재 키의 예입니다.

**`eni-values-fragment.yaml`**

```yaml
ipam:
  mode: eni
eni:
  enabled: true
  eniTags:
    team: platform
  awsEnablePrefixDelegation: true
routingMode: native
endpointRoutes:
  enabled: true
ipv4:
  enabled: true
ipv6:
  enabled: false
```


`eni.awsEnablePrefixDelegation`에는 해당 prefix를 지원하는 인스턴스·subnet 구성이 필요합니다. IPv4 `/28`은 주소 16개이며 모든 구성에서 Pod 16개를 추가 스케줄링할 수 있다는 뜻은 아닙니다. 기본값은 비활성입니다. 존재하지 않는 `eni-prefix-delegation-enabled` 키를 추가하지 않습니다.

EC2 API는 Operator가 호출합니다. 사전 할당은 Pod별 지연을 줄이지만 quota·API·subnet 고갈을 없애지 못합니다. `eni.eniTags`는 관리 인터페이스의 태그입니다. 검증된 의도적인 `eni.ec2APIEndpoint` override가 필요하지 않으면 SDK가 적절한 EC2 endpoint를 결정하게 합니다.

이 예제는 IPv4입니다. ENI 참조는 다른 prefix·할당 동작을 가진 IPv6를 beta로 문서화하며 플랫폼 검증은 `ipv6.enabled` 설정과 별개입니다. AWS VPC CNI chaining에서는 주소 관리를 AWS VPC CNI가 유지합니다. 일반 EC2, Hybrid Nodes, Fargate, Auto Mode는 설치·지원 경계가 다르고 Fargate·Auto Mode에는 이 대체 프로필을 사용할 수 없습니다.

<span id="ciliumnode-cr을-활용한-노드별-podcidr-조회"></span>

<span id="ciliumnode-cr을-활용한-노드별-podcidr-조회"></span>


## 노드별 할당 상태 조회

### CiliumNode 예제

**읽기 전용 객체 형태 예시**이며 Operator가 소유한 상태 위에 적용할 manifest가 아닙니다.

**`ciliumnode-example.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNode
metadata:
  name: hybrid-node-001
spec:
  addresses:
  - ip: 10.85.0.1
    type: CiliumInternalIP
  - ip: 10.80.1.10
    type: InternalIP
  ipam:
    podCIDRs:
    - 10.85.0.0/25
```


첫 주소가 underlay 노드의 `InternalIP`가 아니라 `CiliumInternalIP`일 수 있습니다. InternalIP·주소 계열·할당 항목이 여러 개일 수도 있습니다. 타입이 InternalIP여도 모든 라우터에서 유효한 next hop이 자동으로 되는 것은 아닙니다.

### 모드별 인벤토리

다음 쿼리를 `ciliumnode-inventory.jq`로 저장합니다.

**`ciliumnode-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.spec.addresses[]? |
    select(.type == "InternalIP") | .ip] | unique),
  clusterPoolPodCIDRs: (.spec.ipam.podCIDRs // []),
  multiPoolAllocations: (.spec.ipam.pools.allocated // []),
  eniInterfaceIDs: ((.status.eni.enis // {}) | keys),
  operatorStatus: (.status.ipam["operator-status"] // {})
}
```


```bash
kubectl get ciliumnodes -o json | jq -f ciliumnode-inventory.jq
```

다른 IPAM 모드에서는 없거나 빈 필드가 정상일 수 있습니다. Kubernetes host scope라면 Kubernetes Node를 확인합니다.

**`kubernetes-node-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.status.addresses[]? |
    select(.type == "InternalIP") | .address] | unique),
  podCIDRs: (.spec.podCIDRs // []),
  legacyPodCIDR: (.spec.podCIDR // null)
}
```


```bash
kubectl get nodes -o json | jq -f kubernetes-node-inventory.jq
```

`[0]`만 고르지 않고 관련 주소·CIDR을 유지하는 인벤토리입니다. `ip route add` 명령을 생성하지 않습니다. 네트워크 라우팅 절차에 따라 인터페이스·next hop과 전달·반환 경로를 검증해야 하며 모든 CIDR을 첫 주소로 설치한다고 가정하지 않습니다.

[EKS Hybrid Nodes 네트워크 계획](../../eks-hybrid-nodes/02-network-configuration.md)에 활용할 수 있지만 해당 환경의 라우팅·도달 가능성 확인을 대신하지 않습니다.

## 네트워크 정책 설계 및 구현

### 리소스와 규칙 의미

- Namespace 범위 `CiliumNetworkPolicy`는 해당 namespace의 endpoint를 선택하고 `CiliumClusterwideNetworkPolicy`는 cluster 범위를 제공합니다. Host firewall의 `nodeSelector`는 후자에서만 지원하며 host firewall 구성이 필요합니다.
- `endpointSelector`는 정책 대상, ingress·egress는 대상 기준의 트래픽 방향입니다. Cilium 규칙의 `spec.labels`는 선택적 식별·메타데이터이며 다른 정책을 상속하는 참조가 아닙니다. Kubernetes `metadata.labels`는 리소스 자체의 label입니다.
- 적용되는 정책의 허용은 합쳐지며 명시적 deny에는 문서화된 우선순위가 있습니다. 별도의 무제한 L4 허용이 겹치는 L7 제한을 우회할 수 있습니다.
- Default deny는 방향별입니다. 필요한 DNS·애플리케이션 경로를 의도적으로 유지하고 실현 정책·실제 플로우를 확인합니다. Default deny 비활성화가 보편적인 L7 dry run은 아닙니다.

### Label이 일치하는 정책 실습

일회용 클러스터의 같은 셸에서 실행합니다.

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

Namespace가 이미 있으면 중단하고 모든 파일·명령에 새 이름을 일관되게 사용합니다. 정책과 일치하는 label 및 공식 CLI 테스트 이미지를 사용하는 workload입니다.

**`policy-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-ipam-policy-demo
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-ipam-policy-demo
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-ipam-policy-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


```bash
kubectl apply -f policy-app.yaml
kubectl -n cilium-ipam-policy-demo wait --for=condition=Ready \
  pod/frontend pod/outsider pod/client --timeout=120s
kubectl -n cilium-ipam-policy-demo rollout status deployment/backend --timeout=120s
kubectl -n cilium-ipam-policy-demo get pods -o wide --show-labels
BACKEND_IP=$(kubectl -n cilium-ipam-policy-demo get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
kubectl -n cilium-ipam-policy-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 "http://$BACKEND_IP:8080/"
```

Outsider의 기본 연결도 먼저 확인합니다. Backend anti-affinity에는 다른 적격 노드가 필요합니다. 아래 database 규칙은 추가 애플리케이션 의존성을 나타내며 실습이 데이터베이스 서버를 배포·검증하지는 않습니다.

### L3/L4 정책

**`backend-l4.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


`backend-l4.yaml`을 적용하고 backend 에이전트에 정책이 실현된 뒤 새 요청을 확인합니다. Frontend 접근은 유지되어야 하고 outsider 거부에는 curl 비정상 종료뿐 아니라 플로우 근거가 필요합니다.

### L7 HTTP 정책

두 번째로 겹치는 허용 정책이 아니라 **같은 `backend-access` 리소스의 대체 정의**입니다. 적용하면 이 실습의 L4 버전을 교체하며 다른 적용 정책도 확인해야 합니다.

**`backend-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/$
          headerMatches:
          - name: content-type
            value: application/json
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


```bash
kubectl apply -f backend-http.yaml
kubectl -n cilium-ipam-policy-demo get cnp backend-access -o yaml
```

실현 후 GET `/`와 정확한 `content-type: application/json`을 가진 POST `/`를 허용합니다. 다른 경로·메서드는 프록시에서 거부되어야 합니다. 허용한 동작을 애플리케이션도 구현해야 하며 정책 허용이 애플리케이션 성공을 보장하지 않습니다. Demo server에서 확인된 readiness 경로는 GET `/`입니다.

HTTP method·path 필드는 정규식입니다. 예제처럼 범위를 고정하고 수정할 때 메타문자를 escape합니다. HTTP/gRPC 규칙에는 Envoy와 보이는 애플리케이션 트래픽이 필요하며 필요한 TLS 종료·가로채기를 구성해야 합니다. gRPC 서비스·메서드는 HTTP/2 path, metadata는 header로 표현되며 별도 `rules.grpc`나 임의 protobuf payload 필터가 아닙니다.

### Kafka 정책의 경계

현재 Cilium에는 제거된 `rules.kafka` API가 없습니다. 이전 topic·API-key·client-ID YAML을 적용하지 않습니다. Broker의 **실제 listener 포트**에 맞는 L4 연결 규칙을 사용하고 topic 접근 같은 인증·인가는 broker에서 설정합니다. NetworkPolicy가 broker 인가를 대신하거나 암호화를 활성화하지 않습니다.

### DNS/FQDN 정책

이 예제는 `kube-system`의 CoreDNS/kube-dns Pod가 TCP/UDP 53 resolver인 환경을 가정합니다. 먼저 Pod의 실제 resolver를 확인합니다. NodeLocal DNS, OpenShift, 관리형 DNS 경로는 맞는 별도 설정이 필요합니다.

**`dns-egress.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-egress
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```


DNS L7 규칙이 해당 resolver 트래픽을 Cilium DNS 프록시로 보내 이름·IP 응답을 학습하게 합니다. 53번 포트 허용만으로는 관찰되지 않습니다. `matchPattern: "*"`는 선택한 resolver로의 DNS 질의를 허용하고 HTTPS egress는 `toFQDNs` 이름에서 학습한 IP로 별도 제한합니다. 외부 테스트 성공을 주장하기 전에 `api.example.com`을 실제 조회 가능한 통제된 이름으로 바꿉니다.

`*.googleapis.com`은 suffix 아래 한 label만 일치하며 apex·여러 단계는 일치하지 않습니다. 이 릴리스의 `**.googleapis.com`은 한 단계 이상 하위 도메인에 일치하지만 apex는 제외합니다. DNS TTL·캐시와 새 조회가 중요합니다. 이름·IP 허용이 HTTP hostname·URL·애플리케이션 사용자 인가 검사는 아닙니다.

기본 DNS 프록시는 agent 내부에서 실행하며 별도 standalone DNS proxy는 alpha로 문서화됩니다. 모든 DNS 정책에 Envoy가 필요한 것은 아닙니다. OpenShift 공식 예제는 이 규칙을 그대로 복사하지 않고 `openshift-dns` resolver 설정과 5353 포트를 사용합니다.

### CIDR·Service·Entity

| 규칙 | 경계 |
|---|---|
| `toCIDR` / `toCIDRSet` | 주로 외부 peer의 IP prefix 선택. 기본적으로 Cilium 관리 Pod·노드 selector를 대신하지 않으며 `pods`/`nodes` 선택적 CIDR 매칭은 beta이고 identity를 소비 |
| `toServices` | Service selector 또는 selectorless EndpointSlice 주소를 정책 selector로 변환. Service·경로를 만들지 않으며 selectorless 경우 CIDR 모드 한계 적용 |
| `world` | 넓은 외부 identity 범주. “공용 인터넷만” 또는 특정 원격 클러스터 선택자가 아님 |
| `cluster` / `cluster-mesh` | `cluster`는 로컬 endpoint와 문서화된 예약 entity·원격 노드, `cluster-mesh`는 연결된 클러스터 endpoint도 포함 |
| `all` | Cluster·mesh·외부 peer를 포함하는 넓은 조합이며 최소 권한의 지름길이 아님 |

API 서버에는 문서화된 `kube-apiserver` entity 동작을 사용하며 `toServices: default/kubernetes`가 일반 workload selector처럼 작동한다고 가정하지 않습니다.

## 멀티 클러스터 시나리오

Cluster Mesh는 상태를 공유하지만 Kubernetes 클러스터·네트워크 네임스페이스는 분리됩니다. 원격 노드가 로컬 Kubernetes Node 객체가 되거나 정책 리소스가 자동 배포되지 않습니다.

```text
상태: cluster A의 Cluster Mesh 제어플레인 <-- mTLS --> cluster B 제어플레인
데이터: Pod A --> 노드 A datapath --> 도달 가능한 네트워크 --> 노드 B datapath --> Pod B
```

Cluster Mesh API server는 상태를 동기화하며 Pod 패킷이 이 서버를 경유할 필요는 없습니다. 제어플레인 mTLS만으로 Pod 간 트래픽이 암호화되지 않습니다.

### 설정 조건과 부분 절차

서로 겹치지 않는 Pod CIDR, 도달 가능한 노드 InternalIP, 허용된 네트워크 경로, 같은 datapath 모드, 문서화된 한 minor 이내 Cilium 버전 차이를 준비합니다. Native routing은 원격 Pod 범위에도 도달하고 native-routing CIDR이 이를 포함해야 합니다. 설치 시 고유 Cilium 이름·ID(예: `cluster-a`/1, `cluster-b`/2)를 지정하고 peer 인증서 신뢰를 구성합니다.

다음은 조건과 사설 NodePort 제어플레인 경로를 준비한 **이후의 부분 절차**입니다. Kubeconfig context 이름과 Cilium cluster 이름은 같을 필요가 없습니다.

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

VPC peering/VPN, route, firewall, private endpoint, 인증서 신뢰를 자동 준비하지 않습니다. 전체 플랫폼 절차를 따르고 실행 중인 클러스터의 이름·ID를 임의로 바꾸지 않습니다.

### Global Service와 클러스터 간 정책

각 준비된 클러스터에 같은 namespace와 실제 backend workload를 만들고 **동일한 Service 이름·namespace** 및 호환 포트를 사용합니다.

**`global-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: global-service
  namespace: mesh-demo
  annotations:
    service.cilium.io/global: 'true'
spec:
  type: ClusterIP
  selector:
    app: global-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
```


현재 annotation은 `service.cilium.io/global`입니다. Global Service는 기본적으로 로컬 backend를 공유하며 `service.cilium.io/shared: "false"`는 peer에 공유를 중지하지만 로컬 client의 원격 backend 사용까지 반드시 막지는 않습니다. 로컬 ClusterIP가 같을 필요는 없습니다.

이 annotation만으로 자동 장애 조치를 보장하지 않습니다. 기본값(`clustermesh.cacheTTL: 0s`)은 연결이 끊긴 클러스터 상태도 유지합니다. 양수 TTL은 제어 연결 단절 후 오래된 원격 정보를 회수할 수 있지만 애플리케이션 health probe나 무중단 보장이 아닙니다.

`cluster-a`에 해당 source workload가 있을 때 목적지 클러스터의 `mesh-demo`에 다음 ingress 정책을 적용합니다.

**`cross-cluster-policy.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cluster-a-frontend
  namespace: mesh-demo
spec:
  endpointSelector:
    matchLabels:
      app: global-app
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: frontend-ns
        k8s:io.cilium.k8s.policy.cluster: cluster-a
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


Cluster label에는 kubeconfig context가 아니라 설정된 **Cilium cluster 이름**을 사용합니다. 현재 Cilium endpoint selector는 peer를 명시하지 않으면 로컬 클러스터가 기본 대상입니다. 각 클러스터에 필요한 정책을 독립적으로 배포하고 양방향 트래픽을 검증합니다.

## 검증과 정리

릴리스별 schema, 설정·소스 계약과 제한된 로컬 fixture로 검토한 예제입니다. 이번 감사에서 실제 IP 할당, 커널 정책 집행, 클라우드 프로비저닝, 동작하는 database 또는 클러스터 간 트래픽을 확인했다고 주장하지 않습니다.

의도·실현 상태와 성공 기준 요청을 확인한 뒤 기대한 거부를 해당 플로우와 대조합니다. 소유를 확인하고 이번 namespace 정책 workload만 정리합니다. 별도 multi-pool 실습은 workload를 해제하고 사용 중인 할당이 없는지 확인한 후 풀 삭제를 검토해야 합니다. 활성 CiliumNode·pool 상태를 지름길로 삭제하지 않습니다.

## 참고 자료

- [IPAM modes/migration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/index.rst), [cluster pool](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool.rst), [host scope](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/kubernetes.rst), [multi-pool](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/multi-pool.rst), [migration procedure](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [PodIPPool schema](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml), [CiliumNode schema](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml), [ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst), [Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml), [EKS CNI boundaries](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Policy rule API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/rule.go), [L3 rules](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer3.rst), [L7 rules](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst), [DNS policies](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/dns.rst), [wildcard implementation](https://github.com/cilium/cilium/blob/v1.20.1/pkg/fqdn/matchpattern/matchpattern.go)
- [Cluster Mesh setup](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/setup.rst), [architecture](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/intro.rst), [global services](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/global-services.rst), [cross-cluster policy](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/policy.rst)


[메인 페이지로 돌아가기](README.md)

## 퀴즈

[IPAM·정책 이해도 확인](../../quizzes/networking/cilium/04-ipam-policy-quiz.md).
