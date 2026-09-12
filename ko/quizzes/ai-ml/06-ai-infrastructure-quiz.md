# EKS 기반 AI 인프라 퀴즈

현재 API와 운영 경계를 확인하는15문항입니다.

## 1. JARK는 무엇이며 자동으로 완성되는 플랫폼인가요?

<details>
<summary>정답 및 설명</summary>

JupyterHub/Argo Workflows/Ray/Karpenter의 조합 패턴입니다. 사용자 identity,workflow 제출,Ray 실행,Kubernetes 배치와 node 공급·저장소·권한을 별도로 연결해야 합니다.
</details>

## 2. JupyterHub Cognito 인증에서 명시할 것은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

callback/token/userInfo/scope와 안정적 username claim,허용 사용자·그룹 규칙입니다. client secret은 준비한 파일로 읽으며 provider의 MFA/federation은 별도 설정입니다. 인증 성공만으로 모든 사용자 접근을 허용하지 않습니다.
</details>

## 3. Ray head와 Karpenter의 역할은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

head의 GCS는 Global Control Service이며 raylet과 scheduling을 조율합니다. CPU를 광고하면 head에도 작업이 배치될 수 있습니다. Ray autoscaler의 worker Pod 요구와 Kubernetes scheduling 상태를 통해 Karpenter가 node를 공급합니다.
</details>

## 4. DRA와 Device Plugin의 차이를 어떻게 설명해야 하나요?

<details>
<summary>정답 및 설명</summary>

DRA는 DeviceClass/ResourceSlice/ResourceClaim을 통한 구조화된 요청·속성·할당 경로입니다. Device Plugin도MIG/time-slicing을 지원하므로 공유 불가라고 설명하지 않습니다. 실제 기능은 driver·장치·feature gate에 따릅니다.
</details>

## 5. MIG profile과 격리 범위에서 주의할 점은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

3g.20gb는20GB짜리3개가 아니라 하나의 profile입니다. MIG는 장치 partition 경계를 제공하지만 host/driver/권한 전체 격리를 대신하지 않습니다. MPS/time-slicing을 보안 경계로 간주하지 않습니다.
</details>

## 6. GPU Operator 버전 하나로 전체 DRA 지원을 판정할 수 있나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. Kubernetes API,driver/장치/CDI와 각 feature gate를 확인합니다.26.7의 GPUCluster 경로는 ClusterPolicy와 상호 배타적이고,0.5 standalone chart는 device-plugin 충돌 방지 opt-in guard가 있습니다.
</details>

## 7. Langfuse를 현재 platform에 연결할 때 무엇을 확인하나요?

<details>
<summary>정답 및 설명</summary>

현재 SDK·backend·DB/ClickHouse/object storage 의존성과 파일 credential·trace 계측·민감 데이터 보존을 확인합니다. 예전2.x Deployment나 trace() 호출을 현재4.x API로 취급하지 않습니다.
</details>

## 8. EFS/FSx/Mountpoint를 어떤 기준으로 선택하나요?

<details>
<summary>정답 및 설명</summary>

I/O·권한·namespace/PVC·capacity와 실제 filesystem semantics를 비교합니다. EFS 요청 용량은 quota가 아니고 Mountpoint CSI2.8은 기존 bucket의 static PV 경로이며 완전한POSIX가 아닙니다.
</details>

## 9. EFA 대역폭과 interface 수를 어떻게 해석하나요?

<details>
<summary>정답 및 설명</summary>

instance 전체 bandwidth와 interface별 수치를 구분하며 곱해서 중복 계산하지 않습니다. 같은AZ·실제 interface/driver/libfabric/NCCL·SG·Pod 자원을 확인합니다. RAID0은 EFA 활성화 설정이 아닙니다.
</details>

## 10. GPU 메모리와 XID 지표는 어떻게 해석하나요?

<details>
<summary>정답 및 설명</summary>

FB_USED/FREE는MiB gauge이며 비율이 높다고 즉시OOM은 아닙니다. XID_ERRORS는 마지막 코드 gauge라 increase()로 횟수를 계산하지 않습니다. 실제 오류·캐시·할당 실패와 장치별 기준을 조사합니다.
</details>

## 11. Karpenter consolidation은 GPU 사용률 지표로 동작하나요?

<details>
<summary>정답 및 설명</summary>

DCGM20% 같은 threshold가 아니라 workload requests·배치 가능성·가격·disruption 조건을 사용합니다. limits와budget은 절대 비용·장애 방지 보장이 아니며 실제 종료·복구를 확인해야 합니다.
</details>

## 12. ResourceSlice는 누가 만들며 무엇을 나타내나요?

<details>
<summary>정답 및 설명</summary>

driver가 실제 device inventory와 typed attribute/capacity를 게시합니다. 임의 Slice를 만들면GPU가 생기는 것이 아닙니다. CEL과matchAttribute는 실제 공개된 schema를 사용해야 합니다.
</details>

## 13. Milvus에 GPU를 요청하면 RAG가 완성되나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. 지원 image/index와embedding 차원·model revision·metric/parameter·tenant filter·삭제 갱신을 맞춰야 합니다. 검색 결과의 권한과 근거 부족 처리도 필요합니다.
</details>

## 14. Pending GPU Pod와 node 실패는 어떻게 조사하나요?

<details>
<summary>정답 및 설명</summary>

GPU를 요청한Pending Pod의 수는 원인 확정이 아닙니다. events/PVC/affinity/taint/quota/claim/image를 확인하고 실제checkpoint 저장·resume를 검증합니다. 여러container의 GPU요청도Pod한번으로 집계합니다.
</details>

## 15. MCP protocol이 Kubernetes 자동검색 gateway를 제공하나요?

<details>
<summary>정답 및 설명</summary>

아닙니다. tool 목록/호출 같은 protocol이며 실제 server/gateway 구현·release·transport·인증·권한을 선택해야 합니다. 임의 image/label/config나URL환경변수만으로 도구 discovery와실행이생기지 않습니다.
</details>

[본문으로 돌아가기](../../ai-ml/06-ai-infrastructure.md)
