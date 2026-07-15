# DAG 패턴과 KubernetesPodOperator 퀴즈

이 퀴즈는 `KubernetesPodOperator`가 선택된 Executor와 어떤 관계인지, Pod 스펙 우선순위, 태스크별 IRSA 권한 분리, Airflow 3의 DAG Bundle 모델에 대한 이해도를 테스트합니다.

## 객관식 문제

1. `CeleryExecutor`로 동작하는 DAG에 `KubernetesPodOperator` 태스크가 하나 있습니다. 이 태스크가 실행될 때 실제로 어떤 일이 벌어지나요?
   - A) 이 태스크 인스턴스만 예외적으로 Celery 워커가 아니라 Kubernetes Pod로 실행된다
   - B) 이미 떠 있는 Celery 워커가 KPO 태스크의 `execute()` 메서드를 실행하고, 그 메서드가 실제 작업을 위한 별도의 Pod를 생성해 감시한다
   - C) 해당 태스크에 대해서만 Airflow가 배포 전체의 Executor를 `KubernetesExecutor`로 조용히 전환한다
   - D) `KubernetesPodOperator`는 `KubernetesExecutor`를 요구하므로 태스크가 실패한다

<details>

<summary>정답 보기</summary>

**정답: B) 이미 떠 있는 Celery 워커가 KPO 태스크의 `execute()` 메서드를 실행하고, 그 메서드가 실제 작업을 위한 별도의 Pod를 생성해 감시한다**

**설명:**
`KubernetesPodOperator`는 어떤 Executor에서든 사용할 수 있습니다. 태스크 인스턴스 자체를 실행하는 주체가 `CeleryExecutor`에서는 Celery 워커, `KubernetesExecutor`에서는 태스크마다 새로 뜨는 Pod이라는 차이만 있을 뿐, 그 프로세스가 KPO의 `execute()`를 호출하면 Kubernetes API를 통해 두 번째 Pod를 새로 생성하고 완료될 때까지 기다립니다. Executor 선택이 KPO 사용을 막거나 요구하지는 않습니다.
</details>

2. 어떤 팀이 DAG가 실행되는 배포를 `CeleryExecutor`에서 `KubernetesExecutor`로 전환했습니다. 이 DAG에는 `KubernetesPodOperator` 태스크가 하나 있습니다. 이 태스크가 생성하는 Pod 개수는 어떻게 바뀔까요?
   - A) 원래 1개였던 Pod가 2개로 늘어난다
   - B) 원래 2개였던 Pod가 1개로 줄어든다
   - C) 달라지지 않는다 — 원래도 태스크 실행 컨텍스트(Pod 또는 프로세스) + KPO가 직접 띄우는 Pod, 이렇게 두 단위였고 지금도 그렇다
   - D) Pod를 전혀 사용하지 않고 로컬 프로세스로 실행되도록 바뀐다

<details>

<summary>정답 보기</summary>

**정답: C) 달라지지 않는다 — 원래도 태스크 실행 컨텍스트(Pod 또는 프로세스) + KPO가 직접 띄우는 Pod, 이렇게 두 단위였고 지금도 그렇다**

**설명:**
KPO 태스크는 항상 두 개의 서로 다른 실행 단위로 구성됩니다: 태스크 인스턴스를 실행하는 컨텍스트(Celery 워커 프로세스 또는 `KubernetesExecutor` Pod)와, KPO 자신이 Kubernetes API를 통해 실제 작업용으로 생성하는 별도의 Pod입니다. Executor를 바꿔도 바뀌는 것은 앞쪽 절반이 어떻게 스케줄링되는지일 뿐이며, KPO가 띄우는 Pod가 추가되거나 사라지지는 않습니다.
</details>

3. 하나의 `KubernetesPodOperator` 태스크에 여러 Pod 설정 소스가 동시에 지정되어 있을 때, 어느 소스가 우선하나요?
   - A) `pod_template_dict`가 항상 다른 모든 것보다 우선한다
   - B) 가장 안전한 대안이라는 이유로 기본값인 빈 `V1Pod`가 항상 우선한다
   - C) KPO 생성자 인자(`image`, `resources` 등)가 `full_pod_spec`보다 우선하고, `full_pod_spec`은 `pod_template_file`보다 우선하며, `pod_template_file`은 `pod_template_dict`보다 우선한다
   - D) DAG 파일에서 가장 나중에 선언된 소스가 우선한다

<details>

<summary>정답 보기</summary>

**정답: C) KPO 생성자 인자(`image`, `resources` 등)가 `full_pod_spec`보다 우선하고, `full_pod_spec`은 `pod_template_file`보다 우선하며, `pod_template_file`은 `pod_template_dict`보다 우선한다**

**설명:**
우선순위는 높은 순으로 KPO 생성자 인자 → `full_pod_spec` → `pod_template_file` → `pod_template_dict` → 기본값인 빈 `V1Pod` 순입니다. 이 덕분에 배포 전체에 공유되는 `pod_template_file`이 기본값을 제공하면서, 개별 태스크는 생성자 인자로 필요한 필드만 덮어쓸 수 있습니다.
</details>

4. 기본 `pod_template_file`에는 `image: python:3.12-slim`이 지정되어 있고, 특정 `KubernetesPodOperator` 태스크에는 생성자 인자로 `image="my-registry/orders-extractor:1.4.0"`이 전달되었습니다. 실제로 실행되는 Pod는 어느 이미지를 사용하나요?
   - A) 템플릿 파일이 진실의 원천으로 간주되어 `python:3.12-slim`이 사용된다
   - B) 생성자 인자가 `pod_template_file`보다 우선하므로 `my-registry/orders-extractor:1.4.0`이 사용된다
   - C) 두 이미지가 병합되어 컨테이너가 두 개인 Pod가 만들어진다
   - D) 둘 다 아니다 — KPO가 설정 충돌 오류를 발생시킨다

<details>

<summary>정답 보기</summary>

**정답: B) 생성자 인자가 `pod_template_file`보다 우선하므로 `my-registry/orders-extractor:1.4.0`이 사용된다**

**설명:**
KPO 생성자 인자는 우선순위의 최상위에 있으며, `pod_template_file`이 지정한 같은 필드를 항상 덮어씁니다. 이것이 바로 의도된 사용 방식입니다 — 템플릿은 공유 기본값을 제공하고, 생성자 인자는 실제로 태스크마다 달라지는 몇몇 필드만 덮어씁니다.
</details>

5. 기본 Pod 템플릿이 이미 서비스 어카운트를 지정하고 있는데도, `KubernetesPodOperator` 태스크에 별도의 `service_account_name`을 지정하는 목적은 무엇인가요?
   - A) 어떤 Executor가 태스크를 실행할지를 바꾼다
   - B) 그 태스크만 IRSA를 통해 자신만의 IAM 역할을 가지도록 하여, 그 태스크에 필요한 AWS 권한만으로 범위를 제한한다
   - C) 그 태스크에 대해서만 IRSA를 완전히 비활성화한다
   - D) `pod_template_file`이 동작하려면 반드시 필요한 설정이다

<details>

<summary>정답 보기</summary>

**정답: B) 그 태스크만 IRSA를 통해 자신만의 IAM 역할을 가지도록 하여, 그 태스크에 필요한 AWS 권한만으로 범위를 제한한다**

**설명:**
`service_account_name`이 참조하는 Kubernetes ServiceAccount에는 IRSA 방식으로 IAM 역할 ARN을 어노테이션으로 달 수 있습니다. KPO가 생성한 태스크 Pod을 포함해 그 ServiceAccount로 실행되는 모든 Pod은 살아있는 동안 그 역할의 권한을 갖게 됩니다. 태스크마다 이를 덮어쓰면, 기본 Pod 템플릿의 서비스 어카운트나 Airflow 컨트롤 플레인 컴포넌트가 사용하는 역할과는 별개의 권한 경계를 그 태스크에 부여할 수 있습니다.
</details>

6. `KubernetesPodOperator` 태스크에 지정하는 `affinity`/`tolerations`는 일반 Kubernetes 워크로드를 전용 노드 풀에 고정하는 방식과 어떤 관계인가요?
   - A) 표준 Kubernetes 스케줄링과는 전혀 무관한, Airflow만의 고유한 메커니즘이다
   - B) 어떤 워크로드에든 쓰이는 동일한 `affinity`/`tolerations` 메커니즘을, KPO가 생성하는 태스크 Pod에 그대로 적용한 것이다
   - C) Executor가 `KubernetesExecutor`일 때만 동작한다
   - D) 노드 풀에 taint를 걸어둘 필요를 완전히 없애준다

<details>

<summary>정답 보기</summary>

**정답: B) 어떤 워크로드에든 쓰이는 동일한 `affinity`/`tolerations` 메커니즘을, KPO가 생성하는 태스크 Pod에 그대로 적용한 것이다**

**설명:**
KPO가 생성하는 Pod은 그냥 일반적인 Kubernetes Pod이므로, 표준 `affinity`/`tolerations` 스케줄링 메커니즘이 다른 워크로드와 똑같이 적용됩니다. KPO에 직접 지정하거나 공유 Pod 템플릿에 미리 넣어두면, Karpenter가 관리하는 NodePool처럼 taint가 걸린 전용 노드 풀에 태스크 Pod을 고정할 수 있으며, 이는 다른 워크로드를 고정할 때와 동일한 방식입니다.
</details>

7. `git-sync` 사이드카만으로는 절대 제공하지 못했던, `GitDagBundle`이 제공하는 핵심 특성은 무엇인가요?
   - A) `git-sync`는 유료 Airflow 라이선스가 필요하지만 `GitDagBundle`은 무료다
   - B) `GitDagBundle`이 `git-sync`보다 속도가 더 빠르다
   - C) 모든 DAG 실행이 자신이 사용한 정확한 Git 커밋 SHA를 기록하므로, 저장소가 그 이후로 바뀌었더라도 재실행이 재현 가능하다
   - D) `GitDagBundle`을 쓰면 dag-processor 자체가 필요 없어진다

<details>

<summary>정답 보기</summary>

**정답: C) 모든 DAG 실행이 자신이 사용한 정확한 Git 커밋 SHA를 기록하므로, 저장소가 그 이후로 바뀌었더라도 재실행이 재현 가능하다**

**설명:**
`GitDagBundle`은 태생적으로 버전 관리를 인식합니다. 각 DAG 실행이 자신이 실행된 커밋 SHA를 기록해두므로, 과거 실행을 다시 돌리면 저장소의 현재 HEAD가 아니라 그 커밋 시점의 코드로 재현됩니다. `git-sync` 사이드카는 작업 복사본을 최신 상태로 유지해줄 뿐, 특정 실행이 실제로 어떤 커밋을 보고 돌았는지는 기록하지 않았습니다.
</details>

8. 실행별 버전 관리가 없어서, 현재 디스크(또는 지정된 오브젝트 키)에 있는 내용이 그대로 실행되는 DAG Bundle 유형은 무엇인가요?
   - A) `GitDagBundle`만 해당한다
   - B) `LocalDagBundle`, `S3DagBundle`, `GCSDagBundle`
   - C) 모든 Bundle 유형이 실행마다 버전을 관리하므로 해당하는 것이 없다
   - D) `S3DagBundle`만 해당한다

<details>

<summary>정답 보기</summary>

**정답: B) `LocalDagBundle`, `S3DagBundle`, `GCSDagBundle`**

**설명:**
`LocalDagBundle`은 로컬 파일시스템 경로에서, `S3DagBundle`/`GCSDagBundle`은 각각 오브젝트 스토리지에서 DAG를 읽어오며, 셋 다 실행별 버전을 추적하지 않습니다. dag-processor가 파싱하는 시점에 존재하는 내용이 그대로 실행됩니다. `GitDagBundle`만이 실행마다 커밋 SHA를 태생적으로 기록하는 유형입니다.
</details>

9. Airflow 3에서는 `git-sync` 사이드카에 대한 지원이 완전히 사라졌나요?
   - A) 예, Airflow 3의 공식 Helm 차트에서는 `git-sync` 사이드카가 더 이상 동작하지 않는다
   - B) 아니요, 공식 Helm 차트에서 `git-sync`는 여전히 동작하며, 커밋 단위 재현성이 중요한 경우를 위한 현대적 대안으로 `GitDagBundle`이 자리매김한다
   - C) 예, 다만 `KubernetesExecutor` 배포에서만 그렇다
   - D) 아니요, 다만 이제는 `git-sync`를 쓰려면 먼저 `GitDagBundle`을 설정해야 한다

<details>

<summary>정답 보기</summary>

**정답: B) 아니요, 공식 Helm 차트에서 `git-sync`는 여전히 동작하며, 커밋 단위 재현성이 중요한 경우를 위한 현대적 대안으로 `GitDagBundle`이 자리매김한다**

**설명:**
Airflow 3는 `git-sync` 지원을 없애지 않았습니다 — 공식 Helm 차트에서 계속 동작합니다. `GitDagBundle`은 강제 마이그레이션 대상이 아니라, `git-sync` 단독으로는 제공하지 못했던 커밋 SHA 버전 관리 보장을 추가해주는 현대적인 대안으로 제시됩니다.
</details>

10. 이 장의 KPO 기반 Spark 예제에서, Airflow DAG 코드가 Kubernetes API를 직접 호출하는 대신 컨테이너 이미지가 `SparkApplication` 매니페스트를 적용하고 폴링하는 방식을 택한 이유는 무엇인가요?
    - A) Airflow DAG 코드에서는 Kubernetes Python 클라이언트를 import할 수 없기 때문
    - B) 잡 제출 로직을 DAG 코드 안에 재구현하는 대신, Kubernetes 네이티브 Spark 패턴(Spark Operator 경유)을 그대로 따르기 위해서
    - C) `KubernetesPodOperator`는 셸 명령을 실행할 수 없기 때문
    - D) `SparkApplication` 매니페스트는 Pod 내부에서만 적용할 수 있고 DAG 파일에서는 절대 적용할 수 없기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 잡 제출 로직을 DAG 코드 안에 재구현하는 대신, Kubernetes 네이티브 Spark 패턴(Spark Operator 경유)을 그대로 따르기 위해서**

**설명:**
KPO 태스크의 컨테이너 이미지가 `SparkApplication` 매니페스트를 적용하고 완료를 기다리게 하면, (Spark 섹션에서 다룬) Spark Operator가 제출·재시도·상태 보고를 그대로 담당하게 됩니다. 이는 어떤 Kubernetes 네이티브 Spark 잡에서든 쓰이는 동일한 패턴이며, DAG 코드는 Spark 제출 로직을 중복 구현하지 않고 오케스트레이션에만 집중할 수 있습니다.
</details>

## 단답형 문제

11. `KubernetesPodOperator`의 전체 Python import 경로는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `airflow.providers.cncf.kubernetes.operators.pod`**

**설명:**
`KubernetesPodOperator`는 `cncf.kubernetes` 프로바이더 패키지 안, `airflow.providers.cncf.kubernetes.operators.pod`에 위치합니다.
</details>

12. `KubernetesPodOperator`가 병합하는 다섯 가지 Pod 설정 소스를 우선순위가 높은 것부터 나열하세요.

<details>

<summary>정답 보기</summary>

**정답: KPO 생성자 인자, `full_pod_spec`, `pod_template_file`, `pod_template_dict`, 기본값인 빈 `V1Pod`**

**설명:**
KPO 자체의 생성자 인자가 항상 최우선입니다. 그 아래로 `full_pod_spec`(완전한 `V1Pod` 객체)이 `pod_template_file`(YAML 파일 경로)보다 우선하고, `pod_template_file`은 다시 `pod_template_dict`(같은 내용을 메모리 dict로 전달)보다 우선합니다. 이 중 어느 것도 지정하지 않은 필드는 Airflow의 기본값인 빈 `V1Pod`로 떨어집니다.
</details>

13. 기본 Pod 템플릿이 이미 서비스 어카운트를 지정하고 있는데도, KPO 태스크에 자신만의 `service_account_name`을 주는 것이 왜 중요한가요?

<details>

<summary>정답 보기</summary>

**정답: 해당 태스크만 IRSA를 통해 자신만의 IAM 역할을 갖도록 하여, 템플릿의 기본값이나 Airflow 컨트롤 플레인 컴포넌트의 역할과는 별개의 권한 범위를 부여할 수 있기 때문입니다.**

**설명:**
태스크별 `service_account_name`은 KPO의 다른 필드와 동일한 우선순위 규칙을 따르므로, 기본 템플릿의 서비스 어카운트를 덮어씁니다. 이를 통해 좁은 권한(예: 특정 S3 prefix)만 필요한 태스크가 정확히 그 범위만 가진 채로 실행될 수 있으며, 더 넓은 기본값이나 scheduler/api-server/dag-processor가 사용하는 역할을 그대로 물려받지 않게 됩니다.
</details>

## 실습 문제

14. `/opt/airflow/dags/templates/base-pod-template.yaml`을 공유 Pod 템플릿으로 사용하고, 이미지를 `my-registry/orders-extractor:1.4.0`으로 덮어쓰며, `python extract.py --date {{ ds }}`를 실행하고, 서비스 어카운트로 `orders-extractor-sa`를 사용하며, 완료 후 Pod를 삭제하는 `extract_orders`라는 이름의 `KubernetesPodOperator` 태스크를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```python
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

extract_orders = KubernetesPodOperator(
    task_id="extract_orders",
    namespace="airflow",
    name="extract-orders",
    image="my-registry/orders-extractor:1.4.0",
    cmds=["python", "extract.py"],
    arguments=["--date", "{{ ds }}"],
    pod_template_file="/opt/airflow/dags/templates/base-pod-template.yaml",
    service_account_name="orders-extractor-sa",
    is_delete_operator_pod=True,
)
```

**설명:**
`pod_template_file`이 공유 기본값(리소스, toleration, 기본 서비스 어카운트)을 제공하고, `image`, `cmds`, `arguments`, `service_account_name`은 KPO의 "생성자 인자가 우선한다" 규칙에 따라 이 태스크에 고유한 필드만 정확히 덮어씁니다. `is_delete_operator_pod=True`는 태스크가 끝나면 생성된 Pod을 정리합니다.
</details>

15. `affinity`/`tolerations`로 KPO 태스크 Pod을 taint가 걸린 전용 노드 풀에 고정하는 것이, Airflow 전용 기능이 아니라 다른 어떤 Kubernetes 워크로드에도 쓰이는 것과 동일한 메커니즘인 이유를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:** `KubernetesPodOperator`가 생성하는 Pod는 특별한 래핑 없이 그냥 일반적인 Kubernetes Pod이기 때문에, 표준 `affinity`/`tolerations` 스케줄링 필드가 다른 Deployment나 Job의 Pod에 적용되는 것과 똑같이 이 Pod에도 그대로 적용됩니다. KPO 생성자 인자로 직접 지정하든 공유 `pod_template_file`에 미리 넣어두든 마찬가지입니다.

**설명:**
이는 KPO가 Kubernetes API를 통해 평범한 `V1Pod`를 생성한다는 사실에서 곧바로 따라오는 결과입니다. Airflow 전용의 별도 스케줄링 계층이 존재하지 않으므로, 일반적인 Kubernetes 워크로드에 쓰는 노드 고정 기법(NodeGroup/NodePool의 taint와 toleration을 맞추거나 `nodeAffinity` 규칙을 쓰는 것)이 KPO가 생성한 Pod에도 변형 없이 그대로 적용됩니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/03-dag-patterns.md)
