# Cilium 용어집 퀴즈

이 퀴즈는 Cilium 관련 주요 용어들에 대한 이해도를 테스트합니다.

## 문제 1: eBPF

<details>
<summary>eBPF의 정식 명칭과 주요 특징은 무엇인가요?</summary>

**답변:**
**정식 명칭**: Extended Berkeley Packet Filter

**주요 특징:**
- 커널 공간에서 안전하게 실행되는 가상 머신
- 네트워크 패킷 처리, 시스템 호출 추적 등 다양한 용도
- JIT 컴파일을 통한 고성능 실행
- 검증기를 통한 안전성 보장
- 동적 프로그램 로딩 지원
</details>

## 문제 2: CNI

<details>
<summary>CNI란 무엇이며 Cilium과의 관계는?</summary>

**답변:**
**CNI**: Container Network Interface

**Cilium과의 관계:**
- Cilium은 CNI 플러그인으로 구현됨
- Kubernetes 클러스터의 네트워킹을 담당
- 포드 간 통신, 서비스 디스커버리 제공
- 네트워크 정책 구현
- 로드 밸런싱 기능 제공
</details>

## 문제 3: VXLAN

<details>
<summary>VXLAN의 특징과 Cilium에서의 사용 목적은?</summary>

**답답:**
**VXLAN**: Virtual Extensible LAN

**특징:**
- 계층 2 네트워크를 계층 3 네트워크 위에 오버레이
- 24비트 VNI로 최대 1600만 개의 네트워크 세그먼트 지원
- UDP 캡슐화를 통한 터널링

**Cilium에서의 사용:**
- 노드 간 포드 통신을 위한 오버레이 네트워크
- 네트워크 격리 및 멀티 테넌시 지원
- 클라우드 환경에서의 네트워크 가상화
</details>

## 문제 4: Hubble

<details>
<summary>Hubble의 역할과 주요 기능은?</summary>

**답변:**
**역할**: Cilium의 네트워크 관찰성 플랫폼

**주요 기능:**
- 네트워크 플로우 모니터링
- 서비스 의존성 맵 생성
- 네트워크 정책 위반 감지
- 성능 메트릭 수집
- 보안 이벤트 추적
- 그래픽 UI를 통한 시각화
</details>

## 문제 5: Envoy

<details>
<summary>Cilium에서 Envoy 프록시의 역할은?</summary>

**답변:**
**역할**: L7 프록시 및 로드 밸런서

**기능:**
- HTTP/gRPC 트래픽 처리
- L7 네트워크 정책 구현
- 고급 로드 밸런싱
- 트래픽 분할 및 라우팅
- 메트릭 및 추적 데이터 생성
- 서비스 메시 기능 제공
</details>

## 문제 6: IPAM

<details>
<summary>IPAM이란 무엇이며 Cilium에서 지원하는 IPAM 모드는?</summary>

**답변:**
**IPAM**: IP Address Management

**Cilium 지원 모드:**
- **Cluster Pool**: 클러스터 전체 IP 풀 관리
- **Kubernetes**: Kubernetes 노드 CIDR 사용
- **AWS ENI**: AWS Elastic Network Interface 활용
- **Azure**: Azure 네트워킹 통합
- **GKE**: Google Kubernetes Engine 통합
</details>

## 문제 7: XDP

<details>
<summary>XDP의 특징과 Cilium에서의 활용은?</summary>

**답변:**
**XDP**: eXpress Data Path

**특징:**
- 네트워크 드라이버 레벨에서 패킷 처리
- 커널 네트워크 스택 바이패스
- 매우 높은 성능 (수백만 PPS)
- eBPF 프로그램 실행

**Cilium 활용:**
- DDoS 방어
- 고성능 로드 밸런싱
- 패킷 필터링
- 네트워크 모니터링
</details>

## 문제 8: BPF Map

<details>
<summary>BPF Map의 역할과 주요 유형은?</summary>

**답변:**
**역할**: eBPF 프로그램 간 데이터 공유 및 저장

**주요 유형:**
- **Hash Map**: 키-값 저장소
- **Array Map**: 인덱스 기반 배열
- **LRU Map**: 최근 사용 기반 캐시
- **Ring Buffer**: 순환 버퍼
- **Stack/Queue**: 스택 및 큐 자료구조
</details>

## 문제 9: Cilium Agent

<details>
<summary>Cilium Agent의 주요 책임은?</summary>

**답변:**
**주요 책임:**
- eBPF 프로그램 로딩 및 관리
- 네트워크 정책 구현
- 서비스 로드 밸런싱
- IP 주소 관리 (IPAM)
- 네트워크 엔드포인트 관리
- 메트릭 및 로그 수집
- API 서버와의 통신
</details>

## 문제 10: Identity

<details>
<summary>Cilium에서 Identity의 개념과 중요성은?</summary>

**답변:**
**개념**: 포드의 보안 신원을 나타내는 숫자 식별자

**중요성:**
- 레이블 기반 보안 정책 구현
- 효율적인 정책 매칭
- 네트워크 트래픽 추적
- 서비스 간 인증
- 확장 가능한 보안 모델
- 멀티 클러스터 환경에서의 일관성
</details>

---

**점수 계산:**
- 8-10개 정답: 우수 (Cilium 용어 전문가 수준)
- 6-7개 정답: 양호 (추가 학습 권장)
- 4-5개 정답: 보통 (기본 용어 복습 필요)
- 0-3개 정답: 미흡 (전체 용어 재학습 권장)
