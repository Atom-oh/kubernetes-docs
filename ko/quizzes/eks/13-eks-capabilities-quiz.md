# Amazon EKS Capabilities 퀴즈

> **마지막 업데이트**: 2026년 10월 23일

[본문](../../eks/13-eks-capabilities.md)의 실측 결과와 문서 기준 내용을 구분해 확인하세요.

1. EKS Capabilities의 Argo CD, kro, ACK 컨트롤러는 어디에서 실행되나요?

   - A) 각 워커 노드의 DaemonSet
   - B) `kube-system` 네임스페이스의 Deployment
   - C) AWS 소유 인프라. 워커 노드에 Pod를 만들지 않음
   - D) 고객 VPC에 자동 생성되는 Fargate 프로필

<details>
<summary>정답 보기</summary>

**정답: C) AWS 소유 인프라. 워커 노드에 Pod를 만들지 않음**

세 capability 모두 워커 노드의 Pod는 0개였습니다. 컨트롤러는 capability role과 EKS access entry로 API 서버를 호출하므로 API 엔드포인트가 private 전용이어도 동작합니다. 같은 이유로 `kubectl logs`로는 로그를 볼 수 없고 Vended Logs를 써야 합니다.

</details>

---

2. 관리형 Argo CD를 만든 직후 자기 클러스터에 Application을 동기화하려면 무엇이 필요한가요?

   - A) 아무것도 필요 없음. 로컬 클러스터가 자동 등록됨
   - B) EKS ARN으로 cluster Secret을 만들고, capability role의 access entry에 배포 권한을 추가
   - C) `argocd cluster add` 명령 실행
   - D) `system:masters`가 반드시 필요

<details>
<summary>정답 보기</summary>

**정답: B) EKS ARN으로 cluster Secret을 만들고, capability role의 access entry에 배포 권한을 추가**

자동 access entry만으로는 `podtemplates is forbidden`으로 실패했습니다. Argo CD는 모든 리소스 타입을 캐시하려고 목록을 조회하므로 `AmazonEKSEditPolicy`만으로도 부족했고, `AmazonEKSAdminViewPolicy`를 함께 붙이자 동기화됐습니다. cluster-admin은 필요하지 않았습니다.

</details>

---

3. 관리형 Argo CD에서 commit부터 Synced까지 분 단위로 걸리는 지연을 없애려면 어떻게 하나요?

   - A) `argocd-cm`의 `timeout.reconciliation`을 30초로 낮춤
   - B) 매번 capability를 다시 만듦
   - C) GitHub webhook을 capability 서버 URL의 `/api/webhook`으로 등록
   - D) 노드 수를 늘림

<details>
<summary>정답 보기</summary>

**정답: C) GitHub webhook을 capability 서버 URL의 `/api/webhook`으로 등록**

기본 폴링은 실측 342~697초였고, 폴링 주기는 관리형에서 바꿀 수 있는 키가 아닙니다. webhook을 연결하자 7.0~7.3초로 줄었습니다. 서버 URL이 AWS 호스팅 주소라 별도 공개 엔드포인트를 만들 필요가 없습니다.

</details>

---

4. 관리형 kro에 RGD를 적용했더니 `ControllerReady=False`와 "cache sync timeout"이 나왔습니다. 가장 가능성 높은 원인은 무엇인가요?

   - A) AWS 쪽 컨트롤러 장애
   - B) `AmazonEKSKROPolicy`에 RGD가 만든 API와 하위 리소스 권한이 없음
   - C) RGD의 CEL 문법 오류
   - D) 노드 메모리 부족

<details>
<summary>정답 보기</summary>

**정답: B) `AmazonEKSKROPolicy`에 RGD가 만든 API와 하위 리소스 권한이 없음**

기본 정책은 `kro.run` 그룹과 CRD만 다룹니다. 메시지가 forbidden이 아니라서 컨트롤러 장애로 오해하기 쉽습니다. access entry에 Kubernetes 그룹을 붙이고 RGD별 ClusterRole을 바인딩하며, RGD보다 먼저 적용하자 대기(실측 228초, 컨트롤러 재시도 간격으로 추정)가 생기지 않았습니다.

</details>

---

5. kro 인스턴스의 하위 리소스와 같은 이름의 ACK Table CR이 이미 있을 때 실측에서 일어난 일은 무엇인가요?

   - A) kro가 인스턴스 생성을 거부함
   - B) kro가 기존 CR을 가져가 `spec.tableName`을 바꾸고, 원래 테이블은 관리되지 않는 상태로 남음
   - C) 관리형 kro에서만 생기고 OSS에서는 재현되지 않음
   - D) ACK가 두 CR을 자동으로 병합함

<details>
<summary>정답 보기</summary>

**정답: B) kro가 기존 CR을 가져가 `spec.tableName`을 바꾸고, 원래 테이블은 관리되지 않는 상태로 남음**

kro는 server-side apply로 덮어쓰고 `kro.run/owned=true`를 붙였습니다. 인스턴스를 지우자 가져간 CR도 삭제됐습니다. OSS 0.9.4에서도 같았으므로 upstream 동작입니다. 하위 리소스 이름에 RGD 고유 접미사를 붙이고 네임스페이스를 나누는 것이 대책입니다.

</details>

---

6. 관리형 ACK에서 팀별로 다른 IAM 권한을 쓰게 하는 방법은 무엇인가요?

   - A) 서비스별 컨트롤러 ServiceAccount에 IRSA를 연결
   - B) capability role에는 AssumeRole 권한만 두고, `IAMRoleSelector`로 네임스페이스와 팀 역할을 연결
   - C) CARM을 켜고 namespace annotation으로 계정을 지정
   - D) 관리형에서는 팀별 분리가 불가능

<details>
<summary>정답 보기</summary>

**정답: B) capability role에는 AssumeRole 권한만 두고, `IAMRoleSelector`로 네임스페이스와 팀 역할을 연결**

SQS만 허용한 team-b의 S3 Bucket은 `AccessDenied`로 막혔고, 메시지에 실제로 쓰인 역할 이름이 나왔습니다. OSS 컨트롤러에서 같은 구성을 하려면 `featureGates.IAMRoleSelector=true`와 `enableCARM=false`를 함께 줘야 하며, CARM을 켠 채로 두면 CrashLoopBackOff가 납니다.

</details>

---

7. ACK 밖(CLI)에서 바꾼 SQS 속성에 대해 실측으로 확인한 것은 무엇인가요?

   - A) 관리형 ACK는 1분 안에 항상 되돌림
   - B) 관리형과 OSS 모두 25분 동안 주기적으로 되돌리지 않았고, 관리형의 되돌림은 컨트롤러 재시작 직후로 보이는 시점에만 관찰됨
   - C) OSS는 실시간 이벤트로 즉시 되돌림
   - D) 관리형의 resync 주기는 `disabledServices`로 조정함

<details>
<summary>정답 보기</summary>

**정답: B) 관리형과 OSS 모두 25분 동안 주기적으로 되돌리지 않았고, 관리형의 되돌림은 컨트롤러 재시작 직후로 보이는 시점에만 관찰됨**

ACK는 AWS 쪽 변경을 실시간으로 감시하지 않습니다. OSS 기본 resync는 10시간이고 조정할 수 있지만, 관리형 주기는 공개되어 있지 않고 조정할 수 없습니다. 빠른 복구가 필요하면 SCP나 IAM 조건으로 ACK 밖의 변경 자체를 막는 편이 확실합니다.

</details>

---

8. 관리형 capability의 컨트롤러 버전에 대한 설명으로 옳은 것은 무엇인가요?

   - A) `create-capability --version`으로 고정할 수 있음
   - B) 클러스터 버전 rollback으로 capability 버전도 되돌릴 수 있음
   - C) AWS가 정하고 올리며, 클러스터 업그레이드와 상관없이 바뀔 수 있음. `describe-capability`의 `version`으로 확인
   - D) 클러스터 Kubernetes 버전을 올릴 때만 바뀜

<details>
<summary>정답 보기</summary>

**정답: C) AWS가 정하고 올리며, 클러스터 업그레이드와 상관없이 바뀔 수 있음. `describe-capability`의 `version`으로 확인**

생성·변경 API에 버전 인자가 없고, 하루 간격으로 만든 Argo CD가 `3.4.6-eks-2`와 `3.4.7-eks-1`로 달랐습니다. 버전 변화를 기록하고, 검증 클러스터를 두고, RETAIN 기반으로 self-managed에 일시 전환할 수 있게 준비합니다. 버전 고정이 꼭 필요하면 self-managed가 맞습니다.

</details>

---

9. hub의 Argo CD capability로 private 전용 spoke 클러스터에 `CreateNamespace=true` 앱을 배포하려면 spoke에 무엇이 필요했나요?

   - A) Transit Gateway와 보안 그룹 인바운드 규칙
   - B) hub capability role로 만든 access entry에 Edit, AdminView와 `AmazonEKSArgoCDClusterPolicy`
   - C) spoke에도 Argo CD capability 생성
   - D) spoke API 엔드포인트를 public으로 변경

<details>
<summary>정답 보기</summary>

**정답: B) hub capability role로 만든 access entry에 Edit, AdminView와 `AmazonEKSArgoCDClusterPolicy`**

네트워크 설정 없이 연결과 인증은 성공했지만, Edit과 AdminView만으로는 `namespaces is forbidden`으로 실패했습니다. hub에서는 이 정책이 자동으로 붙지만 원격 클러스터에는 직접 붙여야 합니다. 자동 재시도가 끝난 뒤에는 수동 sync가 필요했습니다.

</details>

---

10. 다음 중 관리형 capability보다 self-managed가 맞는 경우는 무엇인가요?

   - A) 여러 private EKS 클러스터에 배포하는 hub를 만들 때
   - B) 조직 로그인이 이미 Identity Center로 모여 있을 때
   - C) Argo CD Notifications나 CMP, ACK FieldExport에 의존하고 EKS가 아닌 클러스터에도 배포할 때
   - D) 여러 AWS 서비스를 다루지만 서비스별 컨트롤러 운영이 부담스러울 때

<details>
<summary>정답 보기</summary>

**정답: C) Argo CD Notifications나 CMP, ACK FieldExport에 의존하고 EKS가 아닌 클러스터에도 배포할 때**

관리형에는 Notifications, CMP, `argocd admin`, Lua 표준 라이브러리, FieldExport가 없고, cluster Secret은 EKS ARN만 받습니다. 나머지 보기는 관리형이 특히 잘 맞는 경우입니다.

</details>
