# MWAA 통합 퀴즈

Provisioned MWAA 3.3.1/Python 3.12 기준으로 관리 범위와 실제 EKS 연결을 확인합니다.

1. MWAA scheduler를 고객 EKS의 kubectl로 조회할 수 있나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. AWS 관리 Fargate 실행 환경이며 고객 VPC의 private subnet에 연결됩니다.

**설명:** 사용자 VPC와 무관하다는 뜻은 아닙니다. DAG·IAM·네트워크·용량 설정·업그레이드는 사용자 책임을 포함합니다.

</details>

2. MWAA에서 EKS로 Pod를 제출하려면 어떤 세 경계를 확인하나요?

<details>
<summary>정답 보기</summary>

**정답:** 네트워크 도달성, IAM 기반 EKS 인증, Kubernetes RBAC입니다.

**설명:** kubeconfig와 in_cluster=False만으로 endpoint 연결이나 namespace 권한이 생기지는 않습니다.

</details>

3. EKS가 API 인증 모드라면 aws-auth 매핑 추가만으로 접근이 가능한가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 이 모드에서는 access entry를 사용합니다.

**설명:** API_AND_CONFIG_MAP에서도 access entry를 쓸 수 있습니다. Group 이름을 실제 RoleBinding과 맞추고 기존 grant도 확인합니다.

</details>

4. MWAA에서는 Linux runtime이나 시스템 의존성을 설치할 수 없나요?

<details>
<summary>정답 보기</summary>

**정답:** Startup script로 지원되는 runtime 설치가 가능합니다.

**설명:** 공식 예제에는 sudo 사용도 있습니다. 시작 시간·network·환경 버전 제약을 검증하며 자유로운 base-image 교체와 구분합니다.

</details>

5. 이 장의 Git → CI → S3 → MWAA 배포에서 merge 직후 새 DAG 실행이 보장되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 파일 동기화와 DAG 파싱이 완료되어야 합니다.

**설명:** S3 기본 delivery 경로만 보고 모든 Airflow bundle 기능이 불가능하다고 단정하지 않습니다. 별도 설정은 해당 MWAA 버전의 지원을 확인합니다.

</details>

6. 2026-09-12 공식 지원 표에 있는 최신 Airflow 버전과 MWAA 제공 시작일은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** Airflow 3.3.1, 2026-09-01입니다. Python 3.12를 사용합니다.

**설명:** Upstream 3.3.1은 2026-08-12 릴리스이므로 항상 3개월 지연된다는 주장은 맞지 않습니다. 기존 환경 버전은 따로 확인합니다.

</details>

7. MWAA가 PyPI-only 또는 중요도가 낮은 pipeline에만 적합한가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 외부 EKS workload image도 실행할 수 있으며 운영·기능·복구 요구로 판단합니다.

**설명:** KPO child Pod의 image와 MWAA 자체 runtime은 다릅니다. Provisioned MWAA와 YAML 기반 MWAA Serverless도 구분합니다.

</details>

8. 비용 비교에 고정된 셀프 호스팅 30–60% 절감률을 사용해도 되나요?

<details>
<summary>정답 보기</summary>

**정답:** 근거와 동일 조건이 없으면 사용하지 않습니다.

**설명:** 동일 처리량·지연 목표에서 worker 범위·EKS·DB·스토리지·NAT·로그와 운영 인건비를 합산합니다.

</details>

9. 본문 3.3.1/Python 3.12 환경의 Kubernetes provider 의존성은 어떻게 고정하나요?

<details>
<summary>정답 보기</summary>

**정답:** 해당 Airflow/Python constraints와 apache-airflow-providers-cncf-kubernetes==10.21.0을 사용합니다.

**설명:** 기본 image의 설치 상태를 먼저 확인합니다. S3 object 업로드 뒤 environment의 requirements object version과 설치 로그까지 확인합니다.

</details>

10. 개발자 로컬에서 생성한 kubeconfig를 MWAA로 보내기 전에 무엇을 확인하나요?

<details>
<summary>정답 보기</summary>

**정답:** Cluster/context/CA, exec.command와 IAM credential 선택을 확인하고 로컬 AWS_PROFILE 참조를 제거합니다.

**설명:** 고정 token·장기 key를 넣지 않습니다. MWAA runtime에서 aws get-token 실행과 target endpoint 접근을 검증합니다.

</details>

11. data-processing namespace만 위한 Role에 Kubernetes group을 연결할 때 어떤 binding을 사용하나요?

<details>
<summary>정답 보기</summary>

**정답:** 그 namespace의 RoleBinding을 사용합니다.

**설명:** ClusterRoleBinding은 namespace 제한을 표현하지 않습니다. 다른 grant는 합산되며 Pod 생성 권한은 다른 SA 선택 가능성도 고려해야 합니다.

</details>

12. MWAA_EKS_OK 로그가 나오지 않고 child Pod가 ImagePullBackOff라면 MWAA role의 S3 권한부터 늘려야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. EKS node/Fargate의 image pull 역할·registry 접근·image 존재 여부부터 확인합니다.

**설명:** Child Pod는 MWAA execution role을 자동 상속하지 않습니다. 실제 데이터 접근 권한도 workload SA와 별도로 구성합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/04-mwaa-integration.md)
