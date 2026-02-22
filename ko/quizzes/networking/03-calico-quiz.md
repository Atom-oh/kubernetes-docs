# Calico 퀴즈

이 퀴즈는 Calico CNI의 아키텍처, Network Policy, BGP 설정, 그리고 운영에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Calico의 핵심 컴포넌트 중 각 노드에서 Network Policy를 적용하는 에이전트는?

A. BIRD
B. Felix
C. confd
D. Typha

<details>
<summary>정답 및 설명</summary>

**정답: B. Felix**

**설명:**
Calico 컴포넌트 역할:
- **Felix**: 각 노드에서 실행되는 핵심 에이전트. 인터페이스 관리, 라우팅 테이블 프로그래밍, iptables/eBPF 규칙 관리, Network Policy 적용
- **BIRD**: BGP 라우팅 데몬. 라우트 교환 및 전파
- **confd**: BIRD 설정 파일 동적 생성
- **Typha**: 대규모 클러스터에서 데이터스토어 연결 집계

</details>

### 2. Calico에서 50개 이상의 노드를 가진 클러스터에서 권장되는 컴포넌트는?

A. Felix
B. BIRD
C. Typha
D. confd

<details>
<summary>정답 및 설명</summary>

**정답: C. Typha**

**설명:**
Typha는 대규모 클러스터(50+ 노드)에서 필수적인 컴포넌트입니다:
- 데이터스토어(etcd/Kubernetes API) 연결을 집계
- Felix에게 캐시된 데이터 제공
- API 서버 부하 감소
- 각 Felix가 직접 API 서버에 연결하는 대신 Typha를 통해 데이터 수신

Typha 없이 대규모 클러스터를 운영하면 API 서버에 과부하가 발생할 수 있습니다.

</details>

### 3. Calico의 IPIP 모드에서 CrossSubnet 옵션의 동작으로 올바른 것은?

A. 항상 IPIP 캡슐화를 사용한다
B. 같은 서브넷 내에서만 IPIP 캡슐화를 사용한다
C. 다른 서브넷으로의 트래픽에만 IPIP 캡슐화를 사용한다
D. IPIP 캡슐화를 완전히 비활성화한다

<details>
<summary>정답 및 설명</summary>

**정답: C. 다른 서브넷으로의 트래픽에만 IPIP 캡슐화를 사용한다**

**설명:**
IPIP 모드 옵션:
- **Always**: 모든 Pod 간 트래픽에 IPIP 캡슐화
- **CrossSubnet**: 다른 서브넷으로의 트래픽에만 캡슐화 (같은 서브넷은 직접 라우팅)
- **Never**: IPIP 비활성화, BGP 직접 라우팅 사용

CrossSubnet은 하이브리드 환경에서 유용합니다 - 같은 L2 도메인 내에서는 오버헤드 없이 직접 통신하고, 다른 서브넷으로는 캡슐화합니다.

</details>

### 4. Calico GlobalNetworkPolicy와 NetworkPolicy의 차이점으로 올바른 것은?

A. GlobalNetworkPolicy는 특정 네임스페이스에만 적용되고, NetworkPolicy는 클러스터 전체에 적용된다
B. GlobalNetworkPolicy는 클러스터 전체에 적용되고, NetworkPolicy는 특정 네임스페이스에 적용된다
C. GlobalNetworkPolicy는 Ingress 규칙만 지원하고, NetworkPolicy는 Egress 규칙만 지원한다
D. GlobalNetworkPolicy와 NetworkPolicy는 동일한 기능을 제공한다

<details>
<summary>정답 및 설명</summary>

**정답: B. GlobalNetworkPolicy는 클러스터 전체에 적용되고, NetworkPolicy는 특정 네임스페이스에 적용된다**

**설명:**
Calico Policy 유형:
- **NetworkPolicy**: 특정 네임스페이스 내의 Pod에 적용. 네임스페이스 스코프.
- **GlobalNetworkPolicy**: 클러스터 전체에 적용. 클러스터 스코프. Host Endpoint에도 적용 가능.

GlobalNetworkPolicy 사용 예:
- 기본 거부 정책 (Default Deny)
- DNS 허용 정책
- 모니터링 시스템 접근 허용

</details>

### 5. Calico에서 Tier 기반 정책의 목적으로 올바른 것은?

A. 정책을 네임스페이스별로 그룹화한다
B. 정책을 계층화하여 평가 순서를 정의하고 관리 권한을 분리한다
C. 정책을 Pod 레이블로 필터링한다
D. 정책 적용 성능을 향상시킨다

<details>
<summary>정답 및 설명</summary>

**정답: B. 정책을 계층화하여 평가 순서를 정의하고 관리 권한을 분리한다**

**설명:**
Tier 기반 정책의 목적:
1. **평가 순서 정의**: 낮은 order의 Tier가 먼저 평가됨
2. **관리 권한 분리**: Security 팀, Platform 팀, Application 팀별로 Tier 할당
3. **Pass 액션**: 현재 Tier에서 결정하지 않고 다음 Tier로 전달

일반적인 Tier 구성:
- Security Tier (order: 100) - 악성 IP 차단
- Platform Tier (order: 200) - 모니터링, 로깅 허용
- Application Tier (order: 300) - 앱별 규칙

</details>

### 6. Calico에서 NetworkSet의 용도로 올바른 것은?

A. 여러 네임스페이스를 하나의 그룹으로 묶는다
B. IP 주소 집합을 정의하여 여러 정책에서 재사용한다
C. 네트워크 인터페이스를 설정한다
D. Pod의 네트워크 대역폭을 제한한다

<details>
<summary>정답 및 설명</summary>

**정답: B. IP 주소 집합을 정의하여 여러 정책에서 재사용한다**

**설명:**
NetworkSet은 IP 주소 또는 CIDR 블록의 집합을 정의합니다:

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-databases
  labels:
    service-type: database
spec:
  nets:
    - 10.0.100.10/32
    - 10.0.100.11/32
```

Policy에서 참조:
```yaml
destination:
  selector: service-type == 'database'
```

용도:
- 외부 서비스 IP 관리
- 파트너/신뢰할 수 있는 IP 목록
- 정책에서 반복되는 IP 주소 추상화

</details>

### 7. Calico에서 BGP Route Reflector를 사용하는 이유로 올바른 것은?

A. 각 노드의 CPU 사용량을 줄이기 위해
B. Full-mesh BGP 연결 수를 줄여 확장성을 향상시키기 위해
C. Pod에 더 많은 IP 주소를 할당하기 위해
D. Network Policy 평가 속도를 높이기 위해

<details>
<summary>정답 및 설명</summary>

**정답: B. Full-mesh BGP 연결 수를 줄여 확장성을 향상시키기 위해**

**설명:**
BGP Full-mesh의 문제:
- N개 노드에서 N×(N-1)/2 개의 연결 필요
- 100개 노드 = 4,950개 연결
- 대규모 클러스터에서 확장성 문제

Route Reflector 사용 시:
- 각 노드는 Route Reflector에만 연결
- Route Reflector가 라우트 정보 전파
- 연결 수 대폭 감소 (N → 2×RR 수)

일반적으로 가용성을 위해 2-3개의 Route Reflector를 구성합니다.

</details>

### 8. Calico eBPF 모드의 장점이 아닌 것은?

A. iptables 대비 높은 처리량
B. kube-proxy 대체 가능
C. Windows 컨테이너 완전 지원
D. CPU 사용량 감소

<details>
<summary>정답 및 설명</summary>

**정답: C. Windows 컨테이너 완전 지원**

**설명:**
Calico eBPF 모드의 장점:
- iptables 대비 20-40% 높은 처리량
- 20-30% 낮은 지연 시간
- 일정한 성능 (규칙 수에 관계없이)
- kube-proxy 대체로 Service 처리
- Direct Server Return (DSR) 지원

제한사항:
- Linux 커널 5.3+ 필요 (권장 5.8+)
- Windows에서는 eBPF를 지원하지 않음
- 일부 오래된 커널 기능과 호환성 문제 가능

</details>

### 9. EKS에서 Calico를 사용할 때 권장되는 구성은?

A. Calico를 CNI와 Network Policy 모두로 사용
B. AWS VPC CNI로 네트워킹, Calico로 Network Policy
C. Calico를 CNI로, AWS VPC CNI를 Network Policy로 사용
D. Calico와 AWS VPC CNI를 함께 사용하지 않음

<details>
<summary>정답 및 설명</summary>

**정답: B. AWS VPC CNI로 네트워킹, Calico로 Network Policy**

**설명:**
EKS에서의 권장 구성:
1. **AWS VPC CNI**: Pod 네트워킹 담당
   - VPC 네이티브 IP 할당
   - AWS 네트워크 기능 활용 (Security Groups, Flow Logs 등)

2. **Calico**: Network Policy 담당
   - 고급 정책 기능 (GlobalNetworkPolicy, NetworkSet, Tiers)
   - DNS 기반 정책
   - 상세한 정책 로깅

설치:
```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico-policy-only.yaml
```

</details>

### 10. Calico에서 다음 정책의 동작으로 올바른 것은?

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny
spec:
  selector: all()
  types:
    - Ingress
    - Egress
```

A. 모든 트래픽을 허용한다
B. 모든 Ingress 트래픽만 거부한다
C. 모든 Egress 트래픽만 거부한다
D. 모든 Ingress와 Egress 트래픽을 거부한다

<details>
<summary>정답 및 설명</summary>

**정답: D. 모든 Ingress와 Egress 트래픽을 거부한다**

**설명:**
이 정책의 분석:
- `selector: all()` - 모든 Pod에 적용
- `types: [Ingress, Egress]` - 양방향 트래픽 제어
- 규칙이 없음 - 명시적 허용 없이 모든 트래픽 거부 (기본 거부)

이것은 Zero Trust 네트워킹의 기본 정책입니다. 이 정책 적용 후에는 필요한 트래픽만 명시적으로 허용하는 추가 정책이 필요합니다:
- DNS 트래픽 허용
- 특정 서비스 간 통신 허용
- 모니터링 시스템 접근 허용

</details>

### 11. calicoctl 명령으로 노드의 BGP 상태를 확인하는 방법은?

A. `calicoctl get bgppeer`
B. `calicoctl node status`
C. `calicoctl show bgp`
D. `calicoctl describe node`

<details>
<summary>정답 및 설명</summary>

**정답: B. `calicoctl node status`**

**설명:**
calicoctl 주요 명령어:
- `calicoctl node status` - 노드의 BGP 피어링 상태 확인
- `calicoctl get bgppeer` - BGPPeer 리소스 목록 조회
- `calicoctl get node -o wide` - 노드 상세 정보
- `calicoctl ipam show` - IPAM 블록 및 IP 할당 현황

`calicoctl node status` 출력 예:
```
Calico process is running.
IPv4 BGP status
+--------------+-------------------+-------+----------+-------------+
| PEER ADDRESS |     PEER TYPE     | STATE |  SINCE   |    INFO     |
+--------------+-------------------+-------+----------+-------------+
| 192.168.1.2  | node-to-node mesh | up    | 10:15:00 | Established |
| 192.168.1.3  | node-to-node mesh | up    | 10:15:05 | Established |
+--------------+-------------------+-------+----------+-------------+
```

</details>

### 12. Calico VXLAN과 IPIP 모드의 비교로 올바른 것은?

A. IPIP는 더 큰 오버헤드(50 bytes)를 가지고, VXLAN은 더 작은 오버헤드(20 bytes)를 가진다
B. IPIP는 더 작은 오버헤드(20 bytes)를 가지고, VXLAN은 더 큰 오버헤드(50 bytes)를 가진다
C. IPIP와 VXLAN은 동일한 오버헤드를 가진다
D. IPIP는 UDP 기반이고, VXLAN은 IP 프로토콜 4 기반이다

<details>
<summary>정답 및 설명</summary>

**정답: B. IPIP는 더 작은 오버헤드(20 bytes)를 가지고, VXLAN은 더 큰 오버헤드(50 bytes)를 가진다**

**설명:**
| 특성 | IPIP | VXLAN |
|------|------|-------|
| 오버헤드 | 20 bytes | 50 bytes |
| 기반 프로토콜 | IP 프로토콜 4 | UDP |
| 성능 | 더 좋음 | 약간 낮음 |
| Azure 지원 | 제한적 | 지원 |
| 하드웨어 오프로드 | 제한적 | 광범위 지원 |

IPIP는 성능이 더 좋지만, 일부 클라우드 환경(특히 Azure)에서는 VXLAN이 더 호환성이 좋습니다.

</details>

---

## 추가 학습 자료

- [Calico 공식 문서](https://docs.tigera.io/calico/latest/about/)
- [Calico Network Policy 레퍼런스](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [BGP 구성 가이드](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
