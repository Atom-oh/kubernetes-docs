# DAG 패턴과 KubernetesPodOperator 퀴즈

Airflow 3.3.1과 Kubernetes provider 10.21.0 기준입니다. 실행 구조·병합·권한·bundle versioning과 검증 한계를 확인합니다.

## 개념 확인

1. CeleryExecutor에서 동기 KPO 태스크가 새 작업을 시작하면 누가 workload Pod를 생성하나요?

<details>
<summary>정답 보기</summary>

**정답:** 이미 실행 중인 Celery worker에서 KPO가 Kubernetes API를 호출합니다.

**설명:** 별도 workload Pod가 만들어집니다. Worker Pod는 여러 태스크가 공유할 수 있으며, workload image 자체에 Airflow가 반드시 필요하지는 않습니다.

</details>

2. CeleryExecutor에서 KubernetesExecutor로 바꾸면 새 KPO 실행이 만드는 물리적 Pod 수는 어떻게 달라질 수 있나요?

<details>
<summary>정답 보기</summary>

**정답:** 기존 Celery worker를 쓰던 경로와 달리, task-runner Pod와 workload Pod를 각각 새로 만들 수 있습니다.

**설명:** 두 논리적 실행 역할을 두 개의 새 Pod와 동일시하면 안 됩니다. 재시도·reattachment·deferral에 따라 살아 있는 Pod 수도 달라집니다.

</details>

3. Provider 10.21.0에서 pod_template_file과 pod_template_dict를 함께 지정하면 둘 다 차례대로 병합하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 파일이 있으면 파일을 선택하며 같은 호출의 dict는 추가로 병합하지 않습니다.

**설명:** 선택한 template에 full_pod_spec과 KPO가 구성한 Pod를 병합합니다. 단순한 다섯 단계 전체 병합으로 설명할 수 없습니다.

</details>

4. Template에 requests와 limits가 있는데 container_resources에는 limits만 넣으면 기존 requests가 보존되나요?

<details>
<summary>정답 보기</summary>

**정답:** 보존된다고 가정하면 안 됩니다. 이 병합에서는 resources 객체가 교체되어 requests가 빠집니다.

**설명:** 필요한 requests와 limits를 모두 지정하고 최종 Pod를 확인합니다. Env 목록 연결, label별 병합, falsy 값 상속 등 필드별 규칙도 서로 다릅니다.

</details>

5. KPO의 service_account_name 문자열만 지정하면 해당 Pod에 S3 접근 권한이 생기나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Workload ServiceAccount에 맞는 IAM 연결·trust/association과 호환 credential provider가 필요합니다.

**설명:** IRSA나 Pod Identity 구성, SDK 체인, 실제 허용/거부 결과를 확인합니다. KPO caller의 Kubernetes RBAC는 child Pod의 AWS 권한과 별개입니다.

</details>

6. 전용 NodePool의 taint에 대한 toleration만 추가하면 그 노드로 배치가 강제되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Toleration은 해당 taint를 허용할 뿐이며 selector나 required affinity가 별도로 필요할 수 있습니다.

**설명:** KPO가 만든 Pod에도 표준 Kubernetes 스케줄링이 적용됩니다. 전용 pool도 장애·Spot 회수·disk pressure를 없애지는 않습니다.

</details>

7. Versioning이 켜진 GitDagBundle에서 모든 재실행은 반드시 이전 commit을 쓰나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 요청·DAG·전역 rerun 설정과 호출별 기본값에 따라 최신 버전을 선택할 수 있습니다.

**설명:** 3.3.1의 미지정 fallback은 clear/rerun=False, backfill=True입니다. Bundle versioning을 끄면 run의 버전 추적 자체가 사라지며, Git commit만 고정해도 데이터·image까지 재현되지는 않습니다.

</details>

8. LocalDagBundle·S3DagBundle·GCSDagBundle에서 parser가 읽은 코드와 나중 worker가 읽은 코드가 항상 같은 snapshot인가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 이 bundle들은 현재 per-run bundle versioning을 제공하지 않습니다.

**설명:** Parser 이후 파일이나 object가 바뀔 수 있습니다. 배포 일관성과 필요한 의존 파일 전달을 별도로 관리합니다.

</details>

9. Airflow 3에서 git-sync sidecar는 제거되었나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 공식 Helm chart에서 계속 사용할 수 있습니다.

**설명:** GitDagBundle의 versioning은 별도 기능입니다. git-sync 사용 자체가 강제 migration이나 per-run commit 보존을 뜻하지 않습니다.

</details>

10. 고정 이름의 SparkApplication에 apply한 뒤 COMPLETED만 기다리는 예제의 문제는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** 이전 실행의 COMPLETED를 새 성공으로 오인하거나, 잘못된 namespace를 관찰하거나, FAILED 처리를 지연할 수 있습니다.

**설명:** 고유 실행 ID·명시적 namespace·종료 상태와 cleanup 계약이 필요합니다. Native Spark operator도 최종 생성 CR과 대상 CRD 호환성을 확인해야 합니다.

</details>

## 단답형 문제

11. KubernetesPodOperator의 import 문과 container 자원 설정 인자를 쓰세요.

<details>
<summary>정답 보기</summary>

**정답:** `from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator`; container 자원은 `container_resources`로 지정합니다.

**설명:** Kubernetes 모델의 V1ResourceRequirements를 사용합니다. 일반 resources 인자를 같은 설정으로 취급하지 않습니다.

</details>

12. 10.21.0에서 is_delete_operator_pod=False만 주면 Pod 보존이 보장되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 이 인자는 생성자에 남아 있지만 사용되지 않으므로 on_finish_action과 on_kill_action을 각각 설정해야 합니다.

**설명:** 정상 종료와 kill 경로는 다릅니다. Reattachment도 외부 데이터 쓰기의 exactly-once를 보장하지 않습니다.

</details>

13. Namespace 범위의 KPO Role을 부여하면 caller가 자기 태스크의 Pod만 관리하도록 제한되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 예제 Role은 그 namespace의 허용된 Pod 리소스 전체에 영향을 줄 수 있습니다.

**설명:** Caller ServiceAccount와 workload ServiceAccount를 구분합니다. 신뢰하지 않는 DAG 작성자가 다른 SA나 위험한 spec을 선택하지 못하도록 별도 admission·신뢰 경계를 설계합니다.

</details>

## 적용 문제

14. 본문의 kpo_smoke DAG에서 run ID 전달과 정상 종료·kill 후 삭제를 담당하는 설정을 쓰세요.

<details>
<summary>정답 보기</summary>

**정답:** 아래는 본문의 DAG 내부에서 사용하는 관련 인자입니다.

```python
run_smoke = KubernetesPodOperator(
    task_id="run_smoke",
cmds=["python", "-B", "-c"],
arguments=[
    "import sys; print('KPO_SMOKE_OK run_id=' + sys.argv[1])",
    "{{ run_id }}",
],
on_finish_action="delete_pod",
on_kill_action="delete_pod",
)
```

**설명:** run_id는 shell 문자열에 결합하지 않고 독립 인자로 전달합니다. Asset-triggered run에 ds가 있다고 가정하지 않습니다. 전체 DAG와 RBAC/template 준비는 본문을 따릅니다.

</details>

15. Template의 automountServiceAccountToken=True를 False로 덮어쓴 뒤 dry_run만 확인했다면 무엇을 추가 점검해야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 최종 병합 값과 실제 admission 이후 Pod를 확인하고, Jinja·task-instance label·실제 실행도 각각 검증해야 합니다.

**설명:** 검토한 merge 함수는 falsy False 대신 base True를 상속할 수 있습니다. dry_run은 admission이나 태스크 성공 증명이 아니며, 이 문서의 로컬 검증도 실제 cluster 실행을 대신하지 않습니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/03-dag-patterns.md)
