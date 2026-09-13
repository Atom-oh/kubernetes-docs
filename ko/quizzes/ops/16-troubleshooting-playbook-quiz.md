# 트러블슈팅 플레이북 퀴즈

> **관련 문서**: [Kubernetes/EKS 트러블슈팅 플레이북](../../ops/16-troubleshooting-playbook.md)

## 객관식 문제

### 1. FailedScheduling에 CPU 부족 1개, 메모리 부족 1개, affinity 불일치 6개, taint 불일치 8개가 기록됐습니다. 올바른 해석은?

- A) 실패 이유별 집계이므로 중복 가능성을 고려하고 노드별 상태를 대조한다
- B) 반드시 동일한 노드 하나만 CPU와 메모리가 부족하다
- C) 15개 노드 모두 CPU가 부족하다
- D) 스케줄러가 노드를 평가하지 않았다

<details>
<summary>정답 보기</summary>

**정답: A) 실패 이유별 집계이므로 중복 가능성을 고려하고 노드별 상태를 대조한다**

스케줄러는 각 노드의 여러 실패 reason을 집계할 수 있습니다. 요약 숫자만으로 노드 집합을 서로 배타적으로 나누거나 특정 노드를 확정하지 않습니다. nodeName과 PodScheduled를 확인해 이미지·CNI 초기화 대기도 구분합니다.

</details>

### 2. 일반 EC2 워커에서 ECR pull이 401 Unauthorized로 실패합니다. 먼저 확인할 것은?

- A) Docker Hub rate limit
- B) kubelet 이미지 인증 경로와 노드 역할의 ECR 권한
- C) 컨테이너의 liveness 경로
- D) 애플리케이션의 S3 버킷 이름

<details>
<summary>정답 보기</summary>

**정답: B) kubelet 이미지 인증 경로와 노드 역할의 ECR 권한**

애플리케이션의 IRSA 역할을 이미지 pull 주체와 혼동하지 않습니다. Fargate는 Pod 실행 역할을 확인합니다. crictl pull은 kubelet credential provider나 imagePullSecrets를 자동 재사용하지 않으므로 인증 경로가 같은 테스트가 아닙니다.

</details>

### 3. 컨테이너 종료 reason이 OOMKilled, exit code가 137일 때 올바른 조치는?

- A) 시간이 오래 지났으면 반드시 메모리 누수다
- B) 컨테이너 limit·노드 메모리 압박·사용량 시계열과 커널 이벤트를 확인한다
- C) 항상 limit을 무조건 두 배로 늘린다
- D) SIGTERM 정상 종료이므로 무시한다

<details>
<summary>정답 보기</summary>

**정답: B) 컨테이너 limit·노드 메모리 압박·사용량 시계열과 커널 이벤트를 확인한다**

137은 보통 SIGKILL(128+9)을 나타내며 OOMKilled가 OOM 판단의 단서입니다. 이것만으로 누수나 컨테이너 limit 초과만을 확정하지 않습니다. 137이라도 다른 reason이면 별도 강제 종료 원인을 확인하고, SIGTERM 처리는 앱에 따라 143 외 코드로 종료할 수도 있습니다.

</details>

### 4. EndpointSlice의 ENDPOINTS 열에 IP가 보이면 어떤 결론을 낼 수 있나요?

- A) 모든 파드가 Ready다
- B) Service 요청은 반드시 성공한다
- C) 주소가 존재하며 ready·serving·terminating 조건은 별도로 확인해야 한다
- D) NetworkPolicy가 모두 허용되어 있다

<details>
<summary>정답 보기</summary>

**정답: C) 주소가 존재하며 ready·serving·terminating 조건은 별도로 확인해야 한다**

not-ready 파드도 ready=false인 주소로 포함될 수 있습니다. Pod의 컨테이너 READY 개수와 Pod Ready 조건도 구분합니다. 주소가 없다면 selector·네임스페이스·수동 관리 여부를 확인하며, selector가 없는 Service에는 별도 EndpointSlice 관리가 필요할 수 있습니다.

</details>

### 5. DiskPressure=True에 대응하는 자동 taint는?

- A) node.kubernetes.io/unreachable
- B) node.kubernetes.io/not-ready
- C) node.kubernetes.io/disk-pressure
- D) node.kubernetes.io/memory-pressure

<details>
<summary>정답 보기</summary>

**정답: C) node.kubernetes.io/disk-pressure**

노드가 Ready여도 별도의 압박 조건 때문에 새 파드가 스케줄되지 않을 수 있습니다. 디스크 바이트뿐 아니라 inode와 실제 파일시스템 구성을 확인합니다. Ready=Unknown은 unreachable, Ready=False는 not-ready와 관련됩니다.

</details>

### 6. WaitForFirstConsumer StorageClass를 사용하는 PVC가 Pending이며 아직 소비 파드를 만들지 않았습니다. 올바른 판단은?

- A) 반드시 CSI IAM 권한 오류다
- B) StorageClass 이름이 gp3이면 무조건 잘못됐다
- C) 정상 대기일 수 있다. 소비 파드의 스케줄링 조건에 맞춰 바인딩·프로비저닝한다
- D) PV를 즉시 삭제한다

<details>
<summary>정답 보기</summary>

**정답: C) 정상 대기일 수 있다. 소비 파드의 스케줄링 조건에 맞춰 바인딩·프로비저닝한다**

동작은 StorageClass 이름이 아니라 volumeBindingMode로 결정됩니다. API 기본값은 Immediate이며, 실제 값을 확인해야 합니다. 소비 파드도 Pending이면 FailedScheduling과 토폴로지 제약을 함께 확인합니다. PVC 삭제는 진단의 기본 조치가 아닙니다.

</details>

### 7. 파드 생성 후 서비스 계정에 IRSA 어노테이션을 추가했고 기존 파드에 주입 필드가 없습니다. 올바른 다음 단계는?

- A) 클러스터 재생성
- B) 대상 serviceAccountName과 webhook 설정을 확인하고 영향 범위를 검토해 파드를 재생성한다
- C) 노드 IAM 역할에 AdministratorAccess 추가
- D) 서비스 계정 이름과 관계없이 기다리면 기존 env가 바뀐다

<details>
<summary>정답 보기</summary>

**정답: B) 대상 serviceAccountName과 webhook 설정을 확인하고 영향 범위를 검토해 파드를 재생성한다**

주입은 파드 생성 시 이루어지므로 기존 파드가 자동 변경되지는 않습니다. 재생성 후 주입과 실제 사용 주체를 확인합니다. SDK의 다른 자격 증명 공급자가 우선할 수 있고 IMDS 접근이 차단되면 노드 역할 폴백도 불가능합니다.

</details>

### 8. Karpenter가 all available instance types exceed limits for nodepool을 보고했습니다. 무엇을 뜻하나요?

- A) 현재 사용량이 limit과 정확히 같아야만 발생한다
- B) 후보 인스턴스 추가 시 남은 NodePool 한도를 초과한다
- C) 어떤 EC2 타입도 해당 리전에 존재하지 않는다
- D) Pod에 toleration이 반드시 없다

<details>
<summary>정답 보기</summary>

**정답: B) 후보 인스턴스 추가 시 남은 NodePool 한도를 초과한다**

현재 CPU 7, limit 8이고 최소 후보가 2 CPU라면 사용량이 한도보다 작아도 발생할 수 있습니다. 다른 리소스 한도·DaemonSet 오버헤드·requirements도 함께 확인합니다. Nominated 이벤트만으로 노드 또는 파드 준비 완료를 판단하지 않습니다.

</details>

### 9. secondary-IP 모드에서 WARM_IP_TARGET=3, MINIMUM_IP_TARGET=6이고 사용 중 IP가 1개입니다. 목표를 올바르게 해석한 것은?

- A) 총 IP는 반드시 4개다
- B) 두 조건을 만족하려면 총 6개, 여분 5개가 필요할 수 있다
- C) MINIMUM_IP_TARGET은 여분 IP가 최소 6개라는 뜻이다
- D) Too many pods는 서브넷 고갈을 확정한다

<details>
<summary>정답 보기</summary>

**정답: B) 두 조건을 만족하려면 총 6개, 여분 5개가 필요할 수 있다**

warm은 여분 목표, minimum은 사용 중과 여분을 합한 전체 하한입니다. 값은 IPAM 조정·ENI 한계·prefix 할당 단위에 따라 달라집니다. WARM_ENI_TARGET보다 양수 IP 목표가 우선하며, prefix 모드는 연속된 /28 블록과 지원 인스턴스를 확인합니다. max-pods 상한과 실제 IP 고갈은 별도 진단합니다.

</details>
