# Calico 운영 퀴즈

> **관련 문서**: [Calico 운영](../../../networking/calico/09-operations.md)
> **마지막 업데이트**: 2026년 9월 12일

## 퀴즈

1. Calico 설치 소유권에 대한 올바른 설명은?
   - A) 이중화를 위해 매니페스트와 Helm operator를 함께 설치
   - B) 플랫폼에 맞는 operator/Helm 또는 직접 매니페스트 소유 경로 선택
   - C) 모든 설치에서 BPF 활성화 필수
   - D) 새 operator 매니페스트 하나에 모든 Calico CRD가 자동 포함

<details>
<summary>정답 보기</summary>

**정답: B) 플랫폼에 맞는 operator/Helm 또는 직접 매니페스트 소유 경로 선택**

**설명:**
Helm 차트는 Tigera Operator를 설치합니다. 하나의 소유 경로와 고정 버전, 일치하는 CRD, 실제 네트워킹 구성을 사용하세요. 본문 예제는 자체 관리 Linux의 전체 Calico CNI이며 EKS VPC CNI policy-only는 별도 구성입니다.

</details>

2. `calicoctl node status`가 검사하는 것은?
   - A) Kubeconfig context의 모든 노드
   - B) 필요한 노드 접근 조건에서 로컬 노드의 BGP 상태
   - C) 모든 애플리케이션 HTTP readiness
   - D) 모든 IPAM 할당 누수

<details>
<summary>정답 보기</summary>

**정답: B) 필요한 노드 접근 조건에서 로컬 노드의 BGP 상태**

**설명:**
로컬 BGP 진단이며 클러스터 전체 readiness 프로브가 아닙니다. BGP 비활성 구성에서 BGP 성공 결과를 요구하지 않습니다. 문제가 있는 노드를 선택하고 필요한 경우 실제 BIRD 소켓을 조회하세요.

</details>

3. `calicoctl ipam show --show-blocks`가 제공하는 것은?
   - A) Calico IPAM 블록 사용률이며 노드 affinity는 별도 확인
   - B) 빈 블록의 자동 안전 해제
   - C) 모든 VPC CNI ENI 할당
   - D) 트랜잭션 일관성이 있는 데이터스토어 백업

<details>
<summary>정답 보기</summary>

**정답: A) Calico IPAM 블록 사용률이며 노드 affinity는 별도 확인**

**설명:**
IP 블록/pool 사용을 보여줍니다. 블록과 노드의 관계는 BlockAffinity로 확인합니다. Calico IPAM용 명령이며 VPC CNI나 host-local에서는 실제 할당자를 조사해야 합니다.

</details>

4. 검토한 릴리스에서 `felix_int_dataplane_apply_time_seconds`의 타입은?
   - A) 거부 패킷 Counter
   - B) 반드시 _bucket series가 있는 Histogram
   - C) quantile, _sum, _count를 제공하는 Summary
   - D) 할당 IP 블록 Gauge

<details>
<summary>정답 보기</summary>

**정답: C) quantile, _sum, _count를 제공하는 Summary**

**설명:**
증분 데이터플레인 적용 시간 Summary입니다. 로컬 quantile은 클러스터 전체 p99가 아닙니다. 관측이 있는 구간의 평균에는 sum/count rate를 사용하며 없는 histogram bucket을 만들면 안 됩니다.

</details>

5. Typha 메트릭 포트의 올바른 설명은?
   - A) 바이너리 기본값은 9091이며 본문에서 operator Typha 포트를 9093으로 명시
   - B) 모든 설치가 자동으로 9093 사용
   - C) 항상 kube-controllers의 9094 공유
   - D) Service 생성만으로 메트릭 활성화

<details>
<summary>정답 보기</summary>

**정답: A) 바이너리 기본값은 9091이며 본문에서 operator Typha 포트를 9093으로 명시**

**설명:**
Typha 메트릭은 기본 비활성화입니다. Operator의 typhaMetricsPort가 보고와 Service를 설정합니다. ServiceMonitor는 맞는 Service 포트를 선택해야 하며 Prometheus에서도 선택되어야 합니다.

</details>

6. Pod에 IP가 없을 때 확인할 것은?
   - A) 즉시 주소를 해제하고 모든 Calico 에이전트 재시작
   - B) 스케줄링/이벤트, 선택한 노드, 실제 CNI/IPAM 할당자
   - C) DNS 레코드만 확인
   - D) 모든 BGP 세션의 ASN이 같은지만 확인

<details>
<summary>정답 보기</summary>

**정답: B) 스케줄링/이벤트, 선택한 노드, 실제 CNI/IPAM 할당자**

**설명:**
Pending Pod는 아직 스케줄링되지 않았을 수 있습니다. 할당 실패라면 kubelet/CNI 및 할당자 근거, 적격 pool과 용량/affinity 제약을 조사합니다. 모든 Pod 할당 오류가 Felix 프로세스 로그에 있는 것은 아닙니다.

</details>

7. BGP 트러블슈팅에 포함할 사항은?
   - A) ping 성공만 확인
   - B) 문제 노드의 세션, 출발지/피어 주소와 ASN, TCP 179, 인증/TTL, 필터
   - C) 연결될 때까지 모든 ASN을 무작위 변경
   - D) 노드와 무관하게 클러스터 첫 Calico Pod만 조회

<details>
<summary>정답 보기</summary>

**정답: B) 문제 노드의 세션, 출발지/피어 주소와 ASN, TCP 179, 인증/TTL, 필터**

**설명:**
TCP 연결만으로 BGP Established나 prefix 수용이 증명되지는 않습니다. 기대 경로와 IPv4/IPv6 BIRD 소켓을 확인하세요. 선택한 네트워킹 구성에서 BGP를 사용하는 경우에만 적용합니다.

</details>

8. 정책 오류처럼 보이는 현상에 대한 올바른 설명은?
   - A) kube-proxy와 Service 변환은 조사와 절대 무관
   - B) Pod annotation에 모든 유효 정책 결정이 표시
   - C) Felix Debug 로그는 자동으로 패킷별 deny 로그
   - D) 엔드포인트 identity, selector, 방향, tier/order, 기존 연결, 실제 Service/데이터플레인 경로 확인

<details>
<summary>정답 보기</summary>

**정답: D) 엔드포인트 identity, selector, 방향, tier/order, 기존 연결, 실제 Service/데이터플레인 경로 확인**

**설명:**
정책은 Calico가 적용하지만 Service 변환, endpoint 선택, 출발지 주소 변화는 평가되는 트래픽에 영향을 줄 수 있습니다. 특정 컴포넌트를 무관하다고 단정하지 말고 전체 경로와 허용·거부 사례를 검사하세요.

</details>

9. Calico 업그레이드에 필요한 것은?
   - A) 관리 DaemonSet을 patch하여 모든 canary 에이전트 제거
   - B) 설치/버전별 CRD, operator, 저장 데이터 마이그레이션 절차 준수
   - C) 항상 Installation.spec.version부터 설정
   - D) Helm rollback이 모든 CRD와 데이터 변경을 복구한다고 가정

<details>
<summary>정답 보기</summary>

**정답: B) 설치/버전별 CRD, operator, 저장 데이터 마이그레이션 절차 준수**

**설명:**
호환 출발/목표 버전을 선택하고 기존 설치 소유 경로를 업데이트하며 새 필드를 쓰기 전에 CRD를 관리합니다. Rollout과 복구를 테스트하세요. 이전 operator나 원본 YAML export는 다운그레이드 보장이 아닙니다.

</details>

10. Default-deny 정책을 도입하는 방법은?
   - A) 선택한 네임스페이스와 필수 의존성 허용부터 검증한 뒤 범위 확대
   - B) 즉시 모든 엔드포인트에 빈 GlobalNetworkPolicy 적용
   - C) 존재하지 않는 Pod 레이블로 API 서버 추론
   - D) 엔드포인트 수 0으로 차단 성공 판단

<details>
<summary>정답 보기</summary>

**정답: A) 선택한 네임스페이스와 필수 의존성 허용부터 검증한 뒤 범위 확대**

**설명:**
DNS, API, identity, 모니터링, 애플리케이션 경로를 명시적으로 검토해야 합니다. 허용·거부 사례를 테스트하고 복구 경로를 유지하며 워크로드와 host endpoint 정책을 구분하세요.

</details>

11. 현재 OSS flow 관측성에 대한 올바른 설명은?
   - A) FlowLogsFileReporter가 필수 OSS API 필드
   - B) 모든 flow log는 정확히 패킷 하나의 기록
   - C) Operator/Helm에서 Goldmane와 Whisker를 배포하며 현재 가이드는 tech preview로 표시
   - D) Flow log와 Felix 프로세스 로그는 동일

<details>
<summary>정답 보기</summary>

**정답: C) Operator/Helm에서 Goldmane와 Whisker를 배포하며 현재 가이드는 tech preview로 표시**

**설명:**
Goldmane가 Whisker에 집계 flow 자료를 제공합니다. 문서화된 설치 조건에서 OSS로 사용할 수 있으며 이전 파일/DNS logger 필드로 대체할 수 없습니다. 민감한 자료를 보호하고 preview 상태를 평가하세요.

</details>

12. calicoctl의 Kubernetes 데이터스토어 접근을 설정하는 방법은?
   - A) CNI_PATH만 설정
   - B) 적절한 kubeconfig 접근과 DATASTORE_TYPE=kubernetes 또는 명시적인 지원 설정 파일 사용
   - C) 임의의 ~/.config 경로가 항상 자동 탐색
   - D) Calico kubeconfig로 EKS 관리 etcd에 접근

<details>
<summary>정답 보기</summary>

**정답: B) 적절한 kubeconfig 접근과 DATASTORE_TYPE=kubernetes 또는 명시적인 지원 설정 파일 사용**

**설명:**
본문은 일반적인 환경변수 설정을 보여줍니다. --config로 파일을 명시하는 방법도 지원됩니다. 의도한 클러스터와 RBAC를 선택하며 직접 etcdv3 접근은 별도 배포 설정입니다.

</details>
