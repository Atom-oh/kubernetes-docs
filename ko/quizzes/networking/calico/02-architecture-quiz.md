# Calico 아키텍처 퀴즈

> **관련 문서**: [Calico 아키텍처](../../../networking/calico/02-architecture.md)
> **마지막 업데이트**: 2026년 9월 12일

## 퀴즈

1. Felix의 주요 역할로 올바르지 않은 것은?
   - A) 워크로드 인터페이스 상태 관리 (veth 생성 자체는 CNI 경로)
   - B) 라우팅 테이블 프로그래밍
   - C) BGP 피어 연결 관리
   - D) Network Policy 적용

<details>
<summary>정답 보기</summary>

**정답: C) BGP 피어 연결 관리**

**설명:**
BGP 세션은 BIRD가 관리합니다. Felix는 엔드포인트 인터페이스 상태·해당 라우트·커널 정책을 조정합니다. Linux Pod의 veth 생성과 주소 할당은 컨테이너 런타임이 호출한 CNI/IPAM 경로가 맡으므로 기존 A의 “veth pair 생성”도 Felix의 직접 책임이라는 설명은 잘못되었습니다.

</details>

2. BIRD (BIRD Internet Routing Daemon)의 주요 역할은 무엇입니까?
   - A) Network Policy 적용
   - B) Pod IP 할당
   - C) BGP 라우팅 및 라우트 교환
   - D) 데이터스토어 연결 집계

<details>
<summary>정답 보기</summary>

**정답: C) BGP 라우팅 및 라우트 교환**

**설명:**
BIRD는 해당 백엔드가 활성일 때 BGP 세션·라우트 교환·리플렉터 역할을 수행합니다. 커널 프로토콜로 BGP에서 배운 경로를 커널에 설치할 수도 있습니다. BGP가 캡슐화나 암호화를 자동 결정하지 않으며 워크로드 패킷이 BIRD 프로세스를 통과하지는 않습니다.

</details>

3. confd의 주요 역할은 무엇입니까?
   - A) Pod 간 트래픽 암호화
   - B) BIRD 설정 파일 동적 생성
   - C) Network Policy 평가
   - D) Kubernetes API 캐싱

<details>
<summary>정답 보기</summary>

**정답: B) BIRD 설정 파일 동적 생성**

**설명:**
confd는 데이터스토어의 관련 변경을 감시해 BIRD 템플릿을 렌더링하고 검증·reload 명령을 실행합니다. 생성된 bird.cfg를 직접 수정하는 대신 BGP API 리소스를 원본으로 관리해야 합니다.

</details>

4. Typha 배포에 대한 정확한 설명은?
   - A) 모든 설치에서 10노드가 되는 순간 필수다
   - B) 25노드 이하에서는 사용할 수 없다
   - C) Operator는 작은 클러스터에도 Typha를 배포하며 버전별 계산과 실제 부하를 확인해야 한다
   - D) 100노드 이상의 eBPF 모드에서만 사용할 수 있다

<details>
<summary>정답 보기</summary>

**정답: C) Operator는 작은 클러스터에도 Typha를 배포하며 버전별 계산과 실제 부하를 확인해야 한다**

**설명:**
고정된 50노드 필수 기준은 없습니다. Operator 1.42.6은 작은 클러스터에도 Typha를 배포하며 집계 노드와 Linux 배치 용량을 고려해 복제 수를 계산합니다. 실제 용량은 정책·엔드포인트·업데이트 부하 등에 따라 달라집니다.

</details>

5. Typha를 사용하지 않을 때 발생할 수 있는 문제는 무엇입니까?
   - A) Network Policy가 작동하지 않음
   - B) BGP 피어링 실패
   - C) API 서버에 과도한 부하
   - D) Pod IP 할당 실패

<details>
<summary>정답 보기</summary>

**정답: C) API 서버에 과도한 부하**

**설명:**
직접 watch는 노드 수와 변경량에 따라 데이터스토어/API 부하를 늘릴 수 있습니다. Typha가 없다고 정책·BGP·IPAM이 반드시 실패한다는 뜻은 아닙니다. Typha를 사용해도 다른 컴포넌트의 API 접근까지 모두 사라지지는 않습니다.

</details>

6. kube-controllers에 포함된 컨트롤러가 아닌 것은?
   - A) Policy Controller
   - B) Node Controller
   - C) BGP Controller
   - D) WorkloadEndpoint Controller

<details>
<summary>정답 보기</summary>

**정답: C) BGP Controller**

**설명:**
BGP 세션은 BIRD와 confd 경로가 담당합니다. kube-controllers의 활성 목록은 데이터스토어·에디션·설정에 따라 달라지며, operator 1.42.6 기본 Open Source 배포는 node와 loadbalancer를 선택합니다. 다섯 가지 기존 컨트롤러가 항상 모두 실행되는 것은 아닙니다.

</details>

7. Calico가 지원하는 데이터스토어 옵션은 무엇입니까?
   - A) etcd만
   - B) Kubernetes API만
   - C) etcd와 Kubernetes API 모두
   - D) MySQL과 PostgreSQL

<details>
<summary>정답 보기</summary>

**정답: C) etcd와 Kubernetes API 모두**

**설명:**
Kubernetes API와 직접 etcdv3 경로가 있지만 설치·기능 제약이 다릅니다. Kubernetes API 경로에는 별도 Calico etcd가 필요하지 않으며 Kubernetes 자체 저장소는 여전히 존재합니다. 직접 etcd에는 별도의 TLS·자격 증명·가용성·백업 설계가 필요하고 노드 수만으로 선택하지 않습니다.

</details>

8. Felix와 Typha 간의 관계를 올바르게 설명한 것은?
   - A) Felix가 Typha를 관리한다
   - B) Typha가 Felix에게 캐시된 데이터를 제공한다
   - C) Felix와 Typha는 독립적으로 동작한다
   - D) Typha가 Felix의 Network Policy를 평가한다

<details>
<summary>정답 보기</summary>

**정답: B) Typha가 Felix에게 캐시된 데이터를 제공한다**

**설명:**
Typha는 데이터스토어 업데이트를 캐시해 Felix 클라이언트에 분배합니다. 정책을 커널에 구현하는 주체는 Felix이며 Typha는 일반적인 쓰기 프록시나 사용자 트래픽 프록시가 아닙니다.

</details>

9. Calico CNI 플러그인의 역할은 무엇입니까?
   - A) BGP 라우팅 설정
   - B) Pod 생성 시 네트워크 인터페이스 설정
   - C) Network Policy 적용
   - D) 데이터스토어 동기화

<details>
<summary>정답 보기</summary>

**정답: B) Pod 생성 시 네트워크 인터페이스 설정**

**설명:**
현대 Kubernetes에서는 kubelet이 CRI 컨테이너 런타임에 sandbox 생성을 요청하고 런타임이 CNI 체인을 호출합니다. Calico CNI/IPAM이 Linux 인터페이스·주소·초기 경로를 구성하고 Felix는 변경을 비동기로 반영합니다. 정확한 준비 대기 동작은 CNI 설정에 따릅니다.

</details>

10. FelixConfiguration에서 설정할 수 있는 항목이 아닌 것은?
   - A) bpfEnabled (eBPF 모드 활성화)
   - B) logSeverityScreen (로깅 설정)
   - C) bgpAsNumber (BGP AS 번호)
   - D) healthEnabled (헬스체크)

<details>
<summary>정답 보기</summary>

**정답: C) bgpAsNumber (BGP AS 번호)**

**설명:**
BGP AS 번호는 BGPConfiguration/노드 BGP 설정의 영역이며 bgpAsNumber라는 Felix 필드가 아닙니다. 노드 IP 자동 감지도 Installation의 autodetection 설정이나 노드 시작 환경 변수의 영역입니다. Felix에는 로깅·상태·메트릭·데이터플레인 관련 필드가 있지만 모든 Enterprise 로그 필드가 Open Source에 있는 것은 아닙니다.

</details>

11. 집계 노드가 1,000개일 때 operator 1.42.6의 함수가 계산하는 Typha 목표 복제 수는?
   - A) 노드 수 / 50, 최소 1
   - B) 노드 수 / 100, 최소 2
   - C) 7개: floor(1,000 / 200) + 2
   - D) 노드 수 / 500, 최소 5

<details>
<summary>정답 보기</summary>

**정답: C) 7개: floor(1,000 / 200) + 2**

**설명:**
이 버전은 집계 노드가 5개 이상이면 max(3, floor(N / 200) + 2)를 사용합니다. 1,000개이면 7개이며 이전 ceil(N/200), 최소 3 공식과 다릅니다. 1–2노드는 1개, 3–4노드는 2개입니다. 목표 복제 수이며 실제 스케줄링이나 처리 용량 보장은 아닙니다.

</details>

12. calico-node DaemonSet 컨테이너 안의 프로세스가 아니라 별도 Deployment로 실행되는 것은?
   - A) Felix
   - B) BIRD
   - C) confd
   - D) kube-controllers

<details>
<summary>정답 보기</summary>

**정답: D) kube-controllers**

**설명:**
kube-controllers는 별도 Deployment이지만 물리적으로 calico-node와 같은 Kubernetes 노드에 배치될 수 있습니다. Felix와 BGP 모드의 BIRD/confd는 calico-node 안의 프로세스입니다. policy-only나 BGP 비활성 모드에서 BIRD/confd까지 항상 실행되는 것은 아닙니다.

</details>

---

[학습 자료](../../../networking/calico/02-architecture.md) | [이전 퀴즈](01-introduction-quiz.md) | [다음 퀴즈](03-networking-modes-quiz.md)
