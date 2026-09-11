# Multi-cluster

> **검토일**: 2026년 9월 11일 · Istio1.31 · Kubernetes1.32–1.36. 아래 설치 예제는 **sidecar** 토폴로지의 독립적인 대안입니다. Ambient의 지원 범위는 다릅니다. 감사에서 클러스터·AWS 배포·운영 부하 시험을 실행하지 않았습니다.

Multi-cluster Service Mesh는 여러 Kubernetes 클러스터를 하나의 통합된 서비스 메시로 연결합니다.

## 목차

1. [Multi-cluster가 정말 필요한가?](02-multi-cluster.md#multi-cluster가-정말-필요한가)
2. [아키텍처 선택 가이드](02-multi-cluster.md#아키텍처-선택-가이드)
3. [Istio vs AWS VPC Lattice](02-multi-cluster.md#istio-vs-aws-vpc-lattice)
4. [토폴로지](02-multi-cluster.md#토폴로지)
5. [Primary-Remote 설정](02-multi-cluster.md#primary-remote-설정)
6. [Multi-Primary 설정](02-multi-cluster.md#multi-primary-설정)
7. [Cross-cluster 통신](02-multi-cluster.md#cross-cluster-통신)
8. [VPC Lattice와 함께 사용하기](02-multi-cluster.md#vpc-lattice와-함께-사용하기)
9. [실전 예제](02-multi-cluster.md#실전-예제)
10. [성능 및 비용 비교](02-multi-cluster.md#성능-및-비용-비교)
11. [문제 해결](02-multi-cluster.md#문제-해결)

## Multi-cluster가 정말 필요한가?

Multi-cluster Service Mesh는 강력하지만 복잡도와 비용이 증가합니다. 도입 전 신중한 검토가 필요합니다.

### 의사결정 흐름

아래 요구사항을 제약으로 사용합니다. 체크리스트 점수만으로 한 구성이 항상 우월해지지는 않습니다.


### Multi-cluster가 필요한 경우 ✅

#### 1. 지리적 분산 및 지연 시간 최적화

![Istio Mesh가 미국, 유럽, 아시아 세 리전의 EKS 클러스터에 구성을 동기화하고, 세 클러스터가 서로 Cross-region mTLS로 통신하는 지리적 분산 구조를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-advanced-02-multi-cluster-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-advanced-02-multi-cluster-1.html)

**필요한 경우**:

* ✅ 글로벌 사용자 대상 서비스 (지연 시간 <100ms 목표)
* ✅ Workload별 데이터 배치 의무; mesh 자체가 규정 준수를 입증하지는 않음
* ✅ 리전별 트래픽 라우팅 및 장애 격리

#### 2. 재해 복구 (Disaster Recovery)

![Global DNS(Route53)가 평상시 100% 트래픽을 활성 클러스터의 Production 워크로드로 보내고, 재해 발생 시 Failover로 대기 클러스터에 100%를 전환하며, 두 클러스터가 실시간 구성 복제로 연결된 Active-Standby 재해 복구 구조를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-advanced-02-multi-cluster-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-advanced-02-multi-cluster-2.html)

**필요한 경우**:

* ✅ RTO (Recovery Time Objective) <1시간
* ✅ RPO (Recovery Point Objective) <15분
* ✅ 리전 장애 시 자동 Failover

위 RTO/RPO는 요구 예시이며 mesh가 보장하는 결과가 아닙니다. DR 그림은 별도로 구현한 배포/데이터 복제·DNS health routing을 전제하며 client·cache·기존 연결이 전환에 영향을 줍니다.

#### 3. 환경 분리 및 단계적 배포

**필요한 경우**:

* ✅ Dev/Staging/Prod 클러스터 분리하되 통합 관리
* ✅ Blue/Green 배포를 클러스터 단위로 수행
* ✅ 카나리 배포를 리전 단위로 점진적 확대

#### 4. 조직적 경계 및 보안 격리

**필요한 경우**:

* ✅ 팀별/부서별 독립 클러스터 운영
* ✅ 멀티 테넌시 (Multi-tenancy) 강화
* ✅ 명시적으로 평가한 격리 경계; mesh 신뢰 공유는 별도 결정

### Multi-cluster가 불필요한 경우 ❌

#### 1. 단일 리전, 소규모 서비스

![Istio Control Plane이 하나의 EKS 클러스터 안에서 prod, staging, dev 세 Namespace를 관리하며 Multi-cluster 없이도 환경을 분리할 수 있음을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-advanced-02-multi-cluster-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-advanced-02-multi-cluster-3.html)

**대신 사용**:

* Kubernetes Namespace 분리
* NetworkPolicy로 네트워크 격리
* RBAC로 접근 제어

#### 2. 운영 복잡도를 감당할 수 없는 경우

**Multi-cluster 운영 요구사항**:

* 네트워크·PKI·upgrade·클러스터 간 장애를 운영할 책임 조직
* East-West Gateway 관리 및 모니터링
* 클러스터 간 인증서 관리
* Cross-cluster 디버깅 능력

**팀이 작다면**:

* Single-cluster Istio 또는
* AWS VPC Lattice (관리형 서비스)

#### 3. 비용이 핵심 고려사항인 경우

**Multi-cluster 추가 비용**:

* 선택 platform의 east-west LoadBalancer 시간·용량·처리 요금
* 과금 대상 리전 간 byte·방향/리전별 단가
* Control-plane/gateway replica·관찰성/스토리지 용량

### 체크리스트

도입 전 다음 질문에 답해보세요:

**아키텍처**:

* [ ] 2개 이상의 클러스터가 이미 운영 중인가?
* [ ] 여러 리전에 배포가 필요한가?
* [ ] 클러스터 간 서비스 호출이 빈번한가?

**비즈니스 요구사항**:

* [ ] 글로벌 사용자 대상인가?
* [ ] 재해 복구 (DR)가 필수인가?
* [ ] RTO/RPO 요구사항이 엄격한가?

**보안 및 규제**:

* [ ] 데이터 로컬리제이션이 필요한가?
* [ ] 강력한 클러스터 간 격리가 필요한가?

**운영 역량**:

* [ ] Istio 전문가가 있는가?
* [ ] 복잡한 네트워킹 디버깅이 가능한가?
* [ ] 추가 비용을 감당할 수 있는가?

**결과**:

답변은 점수식 권장이 아닌 설계 입력입니다. 체크 수와 무관하게 리전·신뢰·API·복구·운영 제약 때문에 선택지가 배제될 수 있습니다.

## 아키텍처 선택 가이드

| 결정 | 필요한 근거 |
|---|---|
|리전 내 HA와 리전 장애 DR|Control-plane/workload 배치·데이터 복제·검증한 복구 절차|
|Cross-cluster mesh|API/gateway 접근·공통 신뢰 설계·namespace/service 신원·별도로 배포한 설정|
|리전 내 Lattice 연결|리전별 service network·VPC association/endpoint·listener/auth mode·target 접근|
|리전 간 연결|명시적 global network/endpoint·앱/데이터 설계; 리전별 VPC association이 전역 망을 만들지는 않음|
|비용·운영 인력|실측 workload·동일 트래픽 가정·실제 청구·운영 노력|

### 각 솔루션 비교

#### Single-cluster Istio

**장점**:

* ✅ 가장 간단한 관리
* 구성 요소가 적어 비용 모델이 단순할 수 있음; 실제 workload로 산정
* ✅ 빠른 디버깅
* ✅ 모든 Istio 기능 사용 가능

**단점**:

* Cluster 장애 도메인 공유; 리전 내 HA 구성은 가능
* 별도 복구 구조가 없으면 리전 장애에 의존
* EKS control plane은 리전 단위이며 더 넓은 장애 도메인 분산에는 추가 설계 필요

**적합한 경우**:

* 단일 리전 서비스
* 리전 내 신뢰성 목표를 이 운영 범위로 충족할 수 있는 팀
* 리전 간 DR 없이 리전 내 HA 요구를 충족할 수 있는 경우

#### Multi-cluster Istio

**장점**:

* ✅ 완전한 지리적 분산
* ✅ 명시적 트래픽 failover 기반; 앱/데이터 DR은 별도
* ✅ 모든 L7 기능 (Retry, Timeout, Circuit Breaker)
* ✅ 세밀한 트래픽 제어
* ✅ 통합 관찰성

**단점**:

* ❌ 높은 운영 복잡도
* ❌ East-West Gateway 관리 필요
* ❌ Cross-region 데이터 전송 비용
* ❌ 디버깅 어려움

**적합한 경우**:

* 글로벌 서비스
* 강력한 DR 필요
* 세밀한 L7 제어 필수

#### AWS VPC Lattice

**장점**:

* ✅ AWS 완전 관리형
* ✅ 간단한 설정
* ✅ 낮은 운영 부담
* ✅ 명시적인 association·접근 정책에 따른 VPC 간 연결
* 실제 workload의 서비스/요청/데이터·운영 비용 산정

**단점**:

* ❌ 복원력 제어가 다르며 listener rule API에 같은 홉별 retry/outlier 설정은 없음
* ❌ AWS에만 종속
* ❌ Header/method/path·가중치 target routing 지원; Istio와 match type·한도가 다름
* ❌ 다른 metrics/log 인터페이스; 전체 trace에는 앱 통합 필요

**적합한 경우**:

* AWS 중심 아키텍처
* 간단한 서비스 간 연결만 필요
* 운영 단순화 우선

## Istio vs AWS VPC Lattice

### 기능 비교

| 영역 | Istio sidecar mesh | VPC Lattice 서비스 |
|---|---|---|
|Routing|VirtualService/DestinationRule 정책|HTTP header exact/prefix/contains·path exact/prefix·method·가중치 target-group 규칙|
|복원력|홉별 retry/timeout·pool breaker·outlier detection|관리형 서비스/연결 한도; 같은 홉별 retry/outlier 설정 API는 아님|
|TLS 신원|호환 mesh 신뢰의 workload mTLS|HTTPS는 Lattice에서 종료; TLS passthrough는 앱 mTLS를 운반할 수 있지만 관리형 SPIFFE 신원은 아님|
|권한|Istio/앱 정책|필요 시 HTTP(S) auth policy·IAM/SigV4; SourceVpc만의 allow는 익명 호출도 포함 가능|
|TLS passthrough 제한|설정한 gateway에 의존|Custom-domain SNI·TCP target group·기본 rule만 사용; HTTP-header IAM 인증이 아닌 익명 principal 정책|
|관찰성|구성한 proxy/앱 메트릭·로그·trace|CloudWatch 메트릭·access log; 앱 trace/context는 별도 통합|
|비용|Compute·gateway·전송·운영|서비스 시간·요청/데이터 처리·해당 resource/endpoint 요금; 항상 저렴한 선택지는 없음|

Lattice 서비스·resource configuration·service network는 리전 단위입니다. 리전 간/온프레미스 client에는 지원되는 별도 network/endpoint 경로가 필요합니다. Peering/transit 트래픽은 association만이 아닌 적절한 service-network VPC endpoint를 사용해야 합니다. TLS passthrough와 HTTPS 종료는 routing/인증 계약이 다르므로 hybrid의 각 TLS·신원 경계를 명시합니다.

### 아키텍처 패턴 비교

#### 패턴 1: Istio Multi-cluster만 사용


**장점**:

* 완전한 Istio 기능
* 통합 관찰성
* 세밀한 제어

**단점**:

* East-West Gateway 관리 필요
* 높은 복잡도
* Cross-region 데이터 전송 비용

#### 패턴 2: VPC Lattice만 사용

![두 VPC의 App Services가 각각 VPC Lattice Service로 등록되고 Service Network를 통해 서로 라우팅되는 AWS VPC Lattice 단독 사용 패턴을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-advanced-02-multi-cluster-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-advanced-02-multi-cluster-5.html)

**장점**:

* AWS 완전 관리형
* 간단한 설정
* 낮은 운영 부담

**단점**:

* Istio 기능 사용 불가
* 제한적인 트래픽 제어
* Kubernetes 통합에는 AWS Gateway API Controller·지원 API 필요

#### 패턴 3: Hybrid (리전 내 연결 선택지)

![두 클러스터 내부에서는 Istio Mesh가 Service A와 Service B 사이의 mTLS·Retry를 담당하고, 클러스터 간 통신은 AWS VPC Lattice Service Network가 담당하는 Hybrid 아키텍처를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-advanced-02-multi-cluster-6.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-advanced-02-multi-cluster-6.html)

**장점**:

* ✅ 클러스터 내부: Istio의 모든 고급 기능 (Retry, Circuit Breaker, 세밀한 라우팅)
* ✅ 클러스터 간: VPC Lattice의 간단한 관리 및 안정성
* ✅ 운영 복잡도 감소 (East-West Gateway 불필요)
* ✅ 비용은 실측 필요; Lattice 선택만으로 필요한 리전 간 byte가 줄지는 않음

**단점**:

* ⚠️ 두 가지 기술 스택 이해 필요
* ⚠️ Cross-cluster는 Lattice 기능에 제한

**적합한 경우**:

* AWS 환경
* 클러스터 내부는 복잡한 트래픽 제어 필요
* 클러스터 간은 간단한 연결만 필요

## Multi-cluster 개요

Multi-cluster Service Mesh를 사용하면:

* 다중 리전 배포
* 재해 복구 (DR)
* 환경 분리 (dev/staging/prod)
* 클러스터 간 서비스 검색 및 통신

## 토폴로지

다음은 sidecar 토폴로지입니다. 현재 ambient multicluster는 별도 제한을 가진 Beta multi-primary/multi-network이며 primary/remote 절차를 재사용하지 않습니다. 각 primary는 허용된 Kubernetes API를 읽습니다. Istiod가 다른 primary로 Istio CRD·앱 설정·DB를 복제하지 않으므로 별도로 배포합니다. 공통 trust domain의 같은 namespace/ServiceAccount는 클러스터 간 같은 신원이므로 클러스터 분리 자체가 권한 격리는 아닙니다.

하나의 primary 설치도 여러 replica로 구성할 수 있습니다. Primary 장애는 discovery·injection·인증서 작업에 영향을 주지만 기존 proxy는 설정을 유지할 수 있어 모든 트래픽의 즉시 장애를 뜻하지는 않습니다. Multi-primary가 그 의존성을 줄여도 모든 공유 장애 원인을 제거하지는 않습니다.


### Primary-Remote

![Primary 클러스터의 단일 Istiod Control Plane이 Remote 클러스터의 Service B, C에 구성을 푸시하고, Service A·B·C가 mTLS로 서로 통신하는 Primary-Remote 토폴로지를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-advanced-02-multi-cluster-7.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-advanced-02-multi-cluster-7.html)

**특징**:

* 하나의 Control Plane (Primary)
* 여러 Data Plane (Remote)
* 간단한 관리
* Discovery/injection/인증서 작업의 primary 배포 의존성

### Multi-Primary


**특징**:

* 여러 Control Plane
* 고가용성
* 복잡한 관리
* 리전별 자율성

### 공통 사전 조건

Istio1.31 배포본 디렉터리에서 기존 호환 클러스터2개·검토한 kubeconfig context를 사용합니다. 예제는 default revision을 가정하며 다르면 namespace label·gateway 생성에도 원래 revision을 반영합니다. 두 Kubernetes API와 필요한 data/control-plane 경로가 접근 가능해야 합니다. 설치 전에 신뢰 체계를 준비합니다. Multi-primary 발급자는 공통 trusted root 또는 명시적으로 지원되는 신뢰 설계를 사용해야 하며 meshID 문자열만 같다고 인증서를 신뢰하지는 않습니다. [공식 사전 조건·CA 준비](https://istio.io/latest/docs/setup/install/multicluster/before-you-begin/)를 따르고 CA 개인키를 보호합니다. 앱/mesh 설정은 별도로 배포하며 remote secret이 이를 복제하지 않습니다.

```bash
export CTX_CLUSTER1=cluster1
export CTX_CLUSTER2=cluster2
kubectl --context="$CTX_CLUSTER1" get nodes
kubectl --context="$CTX_CLUSTER2" get nodes
```

## Primary-Remote 설정

공식 **IP 기반·동일 network의 sidecar** 토폴로지입니다. Cluster 간 Pod 직접 연결과 primary→remote API 접근이 필요하며 EKS NLB hostname용 예제가 아닙니다. 1.31 chart는 DNS remotePilotAddress를 ExternalName Service로 표현할 수 있지만 이 절차의 IP 조회가 완전한 DNS 기반 EKS 설계는 아닙니다. [외부 control-plane 가이드](https://istio.io/latest/docs/setup/install/external-controlplane/)에 따라 injection URL·서명된 DNS 인증서·실제 control-plane 접근을 구성합니다. DNS 값의 render 성공이 배포 검증은 아닙니다. 아래 IstioOperator는 istioctl 입력이며 클러스터 내 operator 리소스가 아닙니다.

### 1. Primary 클러스터 설정

```bash
# Context 설정
export CTX_CLUSTER1=cluster1

# Istio 설치
istioctl install --context="${CTX_CLUSTER1}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      externalIstiod: true
      multiCluster:
        clusterName: cluster1
      network: network1
EOF

# East-West Gateway 설치
samples/multicluster/gen-eastwest-gateway.sh --network network1 > primary-eastwest.yaml
# Review platform-specific L4 load balancer and access settings before applying
istioctl install --context="${CTX_CLUSTER1}" -f primary-eastwest.yaml

# Gateway 노출
kubectl apply --context="${CTX_CLUSTER1}" -f \
  samples/multicluster/expose-istiod.yaml
```

### 2. Remote 클러스터 설정

```bash
# Context 설정
export CTX_CLUSTER2=cluster2

# Prepare the remote namespace and identify its managing primary
kubectl --context="$CTX_CLUSTER2" create namespace istio-system --dry-run=client -o yaml | kubectl --context="$CTX_CLUSTER2" apply -f -
kubectl --context="$CTX_CLUSTER2" annotate namespace istio-system topology.istio.io/controlPlaneClusters=cluster1 --overwrite
DISCOVERY_ADDRESS=$(kubectl --context="$CTX_CLUSTER1" -n istio-system get svc istio-eastwestgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$DISCOVERY_ADDRESS" ]; then
  echo "This IP-based lab requires a reachable LB IP; DNS-based EKS endpoints need the external-control-plane design." >&2
  exit 1
fi




# Remote 구성으로 Istio 설치
istioctl install --context="${CTX_CLUSTER2}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: remote
  values:
    istiodRemote:
      injectionPath: /inject/cluster/cluster2/net/network1
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network1
      remotePilotAddress: ${DISCOVERY_ADDRESS}
EOF

# Give the primary access to the REMOTE API after remote components are configured
istioctl create-remote-secret \
  --context="${CTX_CLUSTER2}" \
  --name=cluster2 | \
  kubectl apply -f - --context="${CTX_CLUSTER1}"
```

## Multi-Primary 설정

다른 network 토폴로지이므로 각 primary가 상대 API·east-west gateway에 접근해야 합니다. Istiod 설치 전에 해당 CA secret을 준비합니다. 실제 platform의 L4 LoadBalancer·gateway 접근·허용 범위를 설정하며 ALB 등 TLS를 종료하는 L7 홉은 AUTO_PASSTHROUGH와 호환되지 않습니다. EKS 조건은 [AWS 통합](../04-aws-integration.md)을 참고합니다.

### 1. 두 클러스터 모두 Primary로 설정

```bash
# Cluster 1
istioctl install --context="${CTX_CLUSTER1}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster1
      network: network1
EOF

# Cluster 2
istioctl install --context="${CTX_CLUSTER2}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
EOF
```

```bash
# Both networks need their own gateway and service exposure
kubectl --context="$CTX_CLUSTER1" label namespace istio-system topology.istio.io/network=network1 --overwrite
kubectl --context="$CTX_CLUSTER2" label namespace istio-system topology.istio.io/network=network2 --overwrite
samples/multicluster/gen-eastwest-gateway.sh --network network1 > eastwest-cluster1.yaml
samples/multicluster/gen-eastwest-gateway.sh --network network2 > eastwest-cluster2.yaml
# Review platform-specific LB/access settings in these generated inputs before installing
istioctl install --context="$CTX_CLUSTER1" -f eastwest-cluster1.yaml
istioctl install --context="$CTX_CLUSTER2" -f eastwest-cluster2.yaml
kubectl --context="$CTX_CLUSTER1" apply -n istio-system -f samples/multicluster/expose-services.yaml
kubectl --context="$CTX_CLUSTER2" apply -n istio-system -f samples/multicluster/expose-services.yaml
```

### 2. Remote Secret 상호 등록

```bash
# Cluster 1의 Secret을 Cluster 2에
istioctl create-remote-secret \
  --context="${CTX_CLUSTER1}" \
  --name=cluster1 | \
  kubectl apply -f - --context="${CTX_CLUSTER2}"

# Cluster 2의 Secret을 Cluster 1에
istioctl create-remote-secret \
  --context="${CTX_CLUSTER2}" \
  --name=cluster2 | \
  kubectl apply -f - --context="${CTX_CLUSTER1}"
```

## Cross-cluster 통신

같은 Service/namespace 이름·필요한 DNS 가시성과 remote discovery를 사용합니다. Istiod가 Service·Deployment 객체를 클러스터 간 복사하지는 않습니다. 실습은 Service를 두 클러스터에 정의하고 backend는 cluster2에만 배포하여 cluster1의 주입된 client에서 호출합니다. 다른 network에서는 Istio가 east-west gateway·SNI/mTLS 경로를 선택하므로 HTTP ServiceEntry를15443으로 보내는 방식으로 대체하지 않습니다.

다음을 `shared-httpbin-service.yaml`로 저장합니다:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: httpbin
  namespace: multicluster-demo
spec:
  selector:
    app: httpbin
  ports:
  - name: http
    port: 8000
    targetPort: 8080
```

```bash
for context in "$CTX_CLUSTER1" "$CTX_CLUSTER2"; do
  kubectl --context="$context" create namespace multicluster-demo --dry-run=client -o yaml | kubectl --context="$context" apply -f -
  # Default revision lab; use the recorded revision label if installed differently
  kubectl --context="$context" label namespace multicluster-demo istio-injection=enabled --overwrite
  kubectl --context="$context" apply -f shared-httpbin-service.yaml
done
kubectl --context="$CTX_CLUSTER2" apply -n multicluster-demo -f samples/httpbin/httpbin.yaml
kubectl --context="$CTX_CLUSTER1" apply -n multicluster-demo -f samples/curl/curl.yaml
kubectl --context="$CTX_CLUSTER2" rollout status deployment/httpbin -n multicluster-demo --timeout=120s
kubectl --context="$CTX_CLUSTER1" rollout status deployment/curl -n multicluster-demo --timeout=120s
istioctl proxy-config endpoints deployment/curl --context="$CTX_CLUSTER1" -n multicluster-demo --cluster 'outbound|8000||httpbin.multicluster-demo.svc.cluster.local'
kubectl --context="$CTX_CLUSTER1" exec -n multicluster-demo deploy/curl -c curl -- curl -sS --max-time 5 http://httpbin:8000/headers
```

HTTP 응답은 앱 경로 시험이며 그 자체로 인증서 신뢰를 증명하지 않습니다. 보안 장처럼 호출자/수신자의 TLS 설정·신원 근거를 확인합니다. 추가 시나리오는 [공식 multicluster 검증](https://istio.io/latest/docs/setup/install/multicluster/verify/)을 참고합니다. 명령은 앞의 신뢰·네트워크·정책·discovery 전제를 만족한다고 가정합니다.

## VPC Lattice와 함께 사용하기

### Hybrid 구성 계약과 설정 조각

독립적인 Istio mesh와 리전 내 Lattice 서비스 경로를 사용하는 대안입니다. `meshID` 변경이나 `multiCluster.enabled` 같은 switch만으로 이미 연결된 mesh를 안전하게 분리할 수는 없습니다. 토폴로지 변경에는 설치 가이드와 검토한 신뢰/remote-secret/정책 전환을 사용합니다.

다음은 운영 전체 배포가 아닌 설정 예제입니다. 허용된 관리 신원·실제 VPC/security-group ID·설치한 AWS Gateway API Controller/CRD·정상 HTTPS Lattice 서비스를 전제합니다. 명령 실행용 관리 자격 증명은 필요한 data-plane 권한만 가지는 앱 caller role과 별개입니다. Lattice 서비스/network는 리전 단위이며 peering/transit client에는 지원되는 service-network endpoint/network 경로가 필요합니다. 같은 리전 VPC2개의 직접 association으로3개 리전 망이 생기지는 않습니다.

#### 1. 리전별 Service Network 생성 또는 선택

새 network는 이름 조회 대신 반환한 ID를 사용합니다. 기존 network가 있으면 새로 만들지 말고 확인한 ID를 사용합니다. VPC association은 client 경로를 제공하며 Kubernetes Service 공개·모든 요청 허용을 자동으로 처리하지는 않습니다.

```bash
# Both VPCs below are in this Region; use real reviewed VPC/security-group IDs
LATTICE_REGION=us-east-1
: "${VPC1_ID:?Set cluster1 VPC ID}"
: "${VPC2_ID:?Set cluster2 VPC ID}"
: "${LATTICE_SG1_ID:?Set cluster1 association security group}"
: "${LATTICE_SG2_ID:?Set cluster2 association security group}"
SERVICE_NETWORK_ID=$(aws vpc-lattice create-service-network   --region "$LATTICE_REGION" --name my-service-network --auth-type AWS_IAM   --query id --output text)
aws vpc-lattice create-service-network-vpc-association --region "$LATTICE_REGION"   --service-network-identifier "$SERVICE_NETWORK_ID" --vpc-identifier "$VPC1_ID"   --security-group-ids "$LATTICE_SG1_ID"
aws vpc-lattice create-service-network-vpc-association --region "$LATTICE_REGION"   --service-network-identifier "$SERVICE_NETWORK_ID" --vpc-identifier "$VPC2_ID"   --security-group-ids "$LATTICE_SG2_ID"
```

#### 2. 명확한 Ingress 경계와 Controller로 서비스 공개

Controller의 `amazon-vpc-lattice` GatewayClass·Gateway는 이름으로 service network를 참조합니다. `my-service-network` Gateway는 앞에서 별도 관리한 network를 가리킬 수 있습니다. 지원되는 HTTPRoute/GRPCRoute가 서비스/listener/target routing과 고유 endpoint를 제공하며 Gateway가 모든 서비스용 단일 DNS endpoint는 아닙니다.

`ServiceExport`는 유효한 controller 전용 API지만 완전한 Lattice 서비스/network 연결이 아닌 **target group**을 만듭니다. 기존 `lattice-service-network` annotation은 그 과정을 구현하지 않았습니다. 다음 선택적 export는80번 port의 기존 `lattice-entry` ingress Service를 전제하며 이것만으로 완전한 route가 공개되지는 않습니다:

```yaml
# Optional target-group export only; assumes this ingress Service already exists
apiVersion: application-networking.k8s.aws/v1alpha1
kind: ServiceExport
metadata:
  name: lattice-entry
  namespace: istio-system
spec:
  exportedPorts:
  - port: 80
    routeType: HTTP
```

실제 공개에는 [Gateway](https://www.gateway-api-controller.eks.aws.dev/latest/api-types/gateway/)·[HTTPRoute](https://www.gateway-api-controller.eks.aws.dev/latest/api-types/http-route/)·필요한 ServiceImport 설정을 완성합니다. 설치 controller/CRD 버전을 맞추며 exportedPorts는 v2.1.3 기준 확인했습니다.

Lattice는 STRICT backend에 Istio SPIFFE mTLS를 시작하지 않습니다. 의도한 Lattice 트래픽을 받고 우회를 제한하며 backend로 mesh mTLS를 시작하는 별도 ingress 경계 또는 명시적으로 설계한 지원 backend 보안 계약이 필요합니다. Backend 정책을 조용히 완화하지 않습니다. Backend가 원래 IAM 호출자 대신 ingress 신원을 볼 수 있어 신뢰한 신원 전달도 별도 설계가 필요합니다. 이 문서는 그 경계·IAM role·ACM 인증서·DNS를 생성하지 않습니다.

#### 3. 실제 HTTPS Endpoint 검색과 호출

Provider route·service-network 연결이 준비된 뒤 실제 DNS 이름을 얻습니다. 앱은 HTTPS·일치하는 인증서 검증을 사용하고 인증이 필요하면 실제 host/path/payload에 서명합니다. 임의 `.lattice.svc.cluster.local` 이름을 만들거나 앱 TLS 위에 SIMPLE TLS를 추가하지 않습니다.

```bash
# Obtain the real service ID from the reconciled provider configuration
: "${LATTICE_SERVICE_ID:?Set the created and associated HTTPS Lattice service ID}"
aws vpc-lattice get-service --region "$LATTICE_REGION"   --service-identifier "$LATTICE_SERVICE_ID" > lattice-service.json
LATTICE_SERVICE_DNS=$(jq -er '.dnsEntry.domainName' lattice-service.json)
LATTICE_SERVICE_ARN=$(jq -er '.arn' lattice-service.json)

# JSON is also a valid Kubernetes manifest; this explicitly renders the hostname
jq -n --arg host "$LATTICE_SERVICE_DNS" '{
  apiVersion:"networking.istio.io/v1",kind:"ServiceEntry",
  metadata:{name:"remote-service-via-lattice",namespace:"default"},
  spec:{hosts:[$host],location:"MESH_EXTERNAL",resolution:"DNS",
        ports:[{number:443,name:"https",protocol:"HTTPS"}]}
}' > lattice-service-entry.json
kubectl --context="$CTX_CLUSTER1" apply -f lattice-service-entry.json
```

이 ServiceEntry는 호출자 Istio registry에 외부 서비스를 알릴 뿐 Lattice 연결·정책·signer를 만들지 않습니다. 앱 HTTPS는 sidecar에 불투명하므로 HTTP proxy routing/메트릭에는 별도로 설계한 TLS 종료 경로가 필요합니다.

#### 4. 의도한 IAM 호출자 요구

`AWS_IAM`은 정책 평가를 켭니다. Wildcard Principal에 SourceVpc만 있으면 익명 호출을 허용할 수 있어 IAM 인증 증명이 아닙니다. 다음은 IAM role을 명시하고 서비스 하나·직접 연결한 VPC2개로 제한합니다.

```bash
: "${CALLER_ROLE_ARN:?Set the explicitly authorized caller IAM role ARN}"
# Compact resource policy; explicit role requires an authenticated caller
jq -cn --arg role "$CALLER_ROLE_ARN" --arg service "$LATTICE_SERVICE_ARN"   --arg vpc1 "$VPC1_ID" --arg vpc2 "$VPC2_ID" '{
  Version:"2012-10-17",Statement:[{
    Effect:"Allow",Principal:{AWS:$role},Action:"vpc-lattice-svcs:Invoke",
    Resource:($service+"/*"),
    Condition:{StringEquals:{"vpc-lattice-svcs:SourceVpc":[$vpc1,$vpc2]}}
  }]
}' > lattice-auth-policy.json
aws vpc-lattice put-auth-policy --region "$LATTICE_REGION"   --resource-identifier "$SERVICE_NETWORK_ID" --policy file://lattice-auth-policy.json
```

Caller role에도 적절한 identity-based Invoke 권한이 필요합니다. 활성화한 모든 service-network/service auth policy가 허용해야 하며 명시적 deny가 우선합니다. Service 인증을 켰다면 해당 정책도 관리하고 CLI/controller가 같은 정책을 경쟁해 변경하지 않게 합니다. Workload 자격 증명을 사용하는 지원 SDK/signer 또는 검증한 signing proxy가 필요합니다. Istio TLS 설정이 SigV4를 만들지는 않으며 서명 후 host/path/body 변경은 서명을 깨뜨릴 수 있습니다.

### 트래픽 흐름과 관찰성

의도한 흐름은 caller 서명·HTTPS → Lattice 권한 확인·HTTPS 종료 → 설정한 ingress 경계로 backend mesh 진입 → 앱 수신입니다. TLS passthrough는 custom-domain SNI/TCP target·기본 rule·익명 principal 정책이라는 다른 계약입니다. 앱 mTLS를 운반할 수 있지만 HTTP-header IAM 인증을 제공하지는 않습니다.

앱 간 trace context·collector/backend 설정을 맞춥니다. Cluster·Lattice 경계 자체가 trace를 분리하지는 않습니다. 기존2-cluster 그림을 완전한 배포로 가정하지 말고 실제 신원·TLS·텔레메트리 경로를 검증합니다.

## 실전 예제

### 예제 1: 글로벌 전자상거래 (Multi-Primary + VPC Lattice)

글로벌 앱에는 리전별 mesh·Lattice service network를 배포할 수 있습니다. 리전 내 Order는 정의한 Lattice/ingress 계약으로 같은 리전 Payment를 호출할 수 있습니다. 리전 간 호출에는 별도의 지원 network/endpoint 설계가 필요하며 삭제한 그림처럼 하나의 service network 주위에3개 리전을 놓는 것으로 경로가 생기지는 않습니다. 데이터 복제·리전 failover는 앱/인프라 책임입니다.

다음 클러스터 내부 예제는 실제 cart Service·일치하는 v1/v2 Pod 레이블을 전제합니다. user-type 헤더는 route 선택이며 인증이 아닙니다. Cart 작업에는 부작용이 있을 수 있어 mesh retry를 끕니다.

#### 구성 예시

**Cluster 1/2: Frontend → Cart (Istio)**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cart-service
  namespace: default
spec:
  hosts:
  - cart.default.svc.cluster.local
  http:
  - match:
    - headers:
        user-type:
          exact: premium
    route:
    - destination:
        host: cart.default.svc.cluster.local
        subset: v2
      weight: 100
    retries:
      attempts: 0
  - route:
    - destination:
        host: cart.default.svc.cluster.local
        subset: v1
      weight: 100
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cart-service
  namespace: default
spec:
  host: cart.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 1024
        maxRequestsPerConnection: 10
    outlierDetection:
      interval: 10s
      baseEjectionTime: 30s
      consecutive5xxErrors: 5
      minHealthPercent: 0
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**리전 내 Order → Payment Lattice 경로**

Hybrid 절차의 실제 HTTPS DNS·렌더링한 ServiceEntry와 정상 provider route·호환 ingress 경계·SigV4 caller를 사용합니다. 앱 HTTPS 위에 SIMPLE TLS를 추가하거나 임의 Kubernetes `.svc.cluster.local` alias를 만들지 않습니다. 리전 내 Lattice 경로만으로 글로벌 routing·데이터 복구가 해결되지는 않습니다.

### 예제 2: 재해 복구 (DR) 시나리오

기존 리전별 NLB2개를 위한 **수동 Route53 alias-failover 설정**입니다. Workload·LoadBalancer·TLS listener·복제·health service를 배포하지 않습니다. 먼저 각 target group의 실제 앱 readiness/health를 구성합니다. 불완전했던 ExternalDNS annotation과 DNS 소유권을 섞거나 health-check ID를 만들어내지 않습니다.

예제는 별도 public HTTPS health check 없이 NLB alias의 `EvaluateTargetHealth`를 사용합니다. 더 깊은 앱/데이터 건강이 필요하면 적절한 endpoint/alarm 신호를 설계합니다. 기존 HTTP80 Service와 HTTPS443 probe는 맞지 않았으며 private-only endpoint를 public Route53 HTTP checker로 단순 점검할 수는 없습니다.

```bash
# Existing, healthy NLBs and a DNS zone controlled by this workflow
PRIMARY_REGION=us-east-1
STANDBY_REGION=us-west-2
RECORD_NAME=api.example.com
: "${PRIMARY_LB_ARN:?Set the primary NLB ARN}"
: "${STANDBY_LB_ARN:?Set the standby NLB ARN}"
: "${ZONE_ID:?Set the Route53 hosted zone ID}"
aws elbv2 describe-load-balancers --region "$PRIMARY_REGION" \
  --load-balancer-arns "$PRIMARY_LB_ARN" > primary-nlb.json
aws elbv2 describe-load-balancers --region "$STANDBY_REGION" \
  --load-balancer-arns "$STANDBY_LB_ARN" > standby-nlb.json

# Each regional load balancer supplies its own canonical hosted-zone ID
jq -n --arg name "$RECORD_NAME" \
  --slurpfile primary primary-nlb.json --slurpfile standby standby-nlb.json '
  def record($id; $mode; $lb):
    {Action:"UPSERT",ResourceRecordSet:{
      Name:$name,Type:"A",SetIdentifier:$id,Failover:$mode,
      AliasTarget:{HostedZoneId:$lb.CanonicalHostedZoneId,
                   DNSName:$lb.DNSName,EvaluateTargetHealth:true}
    }};
  {Changes:[
    record("primary";"PRIMARY";$primary[0].LoadBalancers[0]),
    record("secondary";"SECONDARY";$standby[0].LoadBalancers[0])
  ]}
' > failover-config.json

# Review the records/zone before applying; do not give another DNS controller ownership
aws route53 change-resource-record-sets --hosted-zone-id "$ZONE_ID" \
  --change-batch file://failover-config.json
```

DNS 변경 전에 기존 record·복원/rollback 계획을 확인합니다. Alias A만으로 IPv6 구성이 완성되지 않으며 dualstack에는 적절한 AAAA·접근 경로도 필요합니다. DNS cache·연결 재사용·target-group health 의미·모두 비정상일 때의 동작이 failover에 영향을 줍니다. 앱/데이터 복구와 함께 검증하며 DNS나 Istio만으로15분 RPO·1시간 RTO를 보장하지 않습니다.

## 성능 및 비용 비교

기존 지연/RPS/CPU/메모리 표에는 재현 가능한 benchmark 출처·release·하드웨어·부하 조건이 없었습니다. 비용 표도10TB와5TB라는 다른 트래픽량·임의 인력 예산을 비교했습니다. 더 저렴하거나 빠른 구성을 입증하지 못하므로 이를 현재 측정값으로 바꾸지 않습니다.

| 구성 요소 | 명시적으로 측정·산정할 것 |
|---|---|
|앱 지연/처리량|동일 리전·payload·동시성·TLS·정책·앱 용량·백분위 정의|
|Mesh compute|실제 Istiod/proxy/gateway/telemetry replica·사용량; Kubernetes/EKS 비용은 별도 포함|
|네트워크|동일한 과금 byte/방향·리전 전송·LB/endpoint/TGW/peering 처리·용량|
|Lattice 서비스|서비스 시간·요청·데이터 처리; resource configuration/endpoint는 별도 모델|
|운영/DR|관측한 운영 노력·사고/복구 시험·비즈니스 영향 가정|

[Lattice 가격](https://aws.amazon.com/vpc/lattice/pricing/)과 실제 청구로 산정합니다. VPC peering이 리전 간 전송료를 자동 제거하지는 않습니다. Lattice의 추가 inter-AZ 전송료 없음과 데이터 처리 비용0은 다릅니다. Ambient가90% 리소스 절감을 보장하지 않으므로 같은 정책 조건에서 측정합니다. 고정 인원·시간당$1,000 장애 비용만으로 아키텍처를 선택하지 않습니다.

## 문제 해결

```bash
# 클러스터 간 연결 확인
istioctl ps --context="${CTX_CLUSTER1}"
istioctl ps --context="${CTX_CLUSTER2}"

# Remote Secret 확인
kubectl get secrets -n istio-system --context="${CTX_CLUSTER1}"

# Cross-cluster 트래픽 확인
kubectl logs -n istio-system -l app=istiod --context="${CTX_CLUSTER1}"
```

## 참고 자료

### 공식 문서

* [Istio Multi-cluster](https://istio.io/latest/docs/setup/install/multicluster/)
* [Multi-Primary](https://istio.io/latest/docs/setup/install/multicluster/multi-primary/)
* [Primary-Remote](https://istio.io/latest/docs/setup/install/multicluster/primary-remote/)
* [AWS VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
* [AWS Gateway API Controller](https://www.gateway-api-controller.eks.aws.dev/latest/)

* [Lattice regional components and cross-Region patterns](https://aws.amazon.com/vpc/lattice/faqs/)
* [Lattice auth policy and anonymous callers](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
* [Lattice SigV4 requests](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
* [Lattice TLS passthrough](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html)
* [Route53 failover aliases](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-values-failover-alias.html)

### 블로그 및 사례 연구

* [Tetrate - Multi-cluster Istio](https://tetrate.io/blog/multicluster-istio/)
* [SKT Enterprise - Istio Ambient Mesh 소개](https://www.sktenterprise.com/bizInsight/blogDetail/dev/14768)

### 관련 문서

* [Ambient Mode](01-ambient-mode.md) - 리소스 최적화
* [mTLS](../security/01-mtls.md) - 클러스터 간 보안 통신
* [VPC Lattice](../../../networking/02-vpc-lattice.md) - AWS 관리형 서비스 네트워킹

## 요약

실제 신뢰·네트워크·API·복구 요구로 토폴로지를 선택합니다. 단일 리전 클러스터도 multi-AZ HA를 제공할 수 있습니다. Sidecar multicluster는 전제를 충족하면 discovery·mesh mTLS를 확장하지만 앱 상태를 복제하지 않습니다. Lattice는 listener별 TLS/인증 계약을 가진 관리형 리전 앱 네트워킹입니다. Hybrid는 각 신원/종료 경계·리전 간 경로를 명시하고 동작·동일 workload 비용을 검증한 뒤 선택합니다.
