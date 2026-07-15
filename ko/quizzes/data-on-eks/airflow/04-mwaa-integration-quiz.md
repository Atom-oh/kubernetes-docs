# MWAA 통합 퀴즈

이 퀴즈는 Amazon MWAA가 직접 접근을 허용하지 않는 부분, MWAA의 DAG가 `KubernetesPodOperator`로 EKS 클러스터의 워크로드를 제어하는 방법, IAM identity mapping의 역할, 그리고 MWAA와 EKS 셀프 매니지드 Airflow 중 무엇을 선택할지에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Amazon MWAA가 직접적인 접근을 제공하지 않는 대상은 무엇인가요?
   - A) DAG 파일 자체
   - B) Airflow 컨트롤 플레인(scheduler, api-server, dag-processor, 워커) — AWS 관리 인프라에서 실행되며 사용자의 EKS 클러스터 바깥에 있음
   - C) Airflow REST API
   - D) 환경의 CloudWatch 로그

<details>

<summary>정답 보기</summary>

**정답: B) Airflow 컨트롤 플레인(scheduler, api-server, dag-processor, 워커) — AWS 관리 인프라에서 실행되며 사용자의 EKS 클러스터 바깥에 있음**

**설명:**
MWAA는 scheduler, api-server, dag-processor, 워커 전체를 AWS 관리 인프라에서 실행하며, 사용자의 VPC나 EKS 클러스터 내부가 아닙니다. 그 결과 Airflow 컨트롤 플레인 자체는 `kubectl`로 조회할 수 없습니다 — 셀프 매니지드 배포처럼 MWAA scheduler의 Pod를 직접 확인할 방법이 없습니다. 이 컴포넌트들의 헬스, 스케일링, 패치는 전부 AWS의 책임이며 Kubernetes 프리미티브가 아니라 CloudWatch와 MWAA 콘솔/API를 통해 노출됩니다.
</details>

2. MWAA에 올라간 DAG가 고객이 소유한 EKS 클러스터에 Pod를 생성하고 관리하려면 어떻게 해야 하나요?
   - A) 불가능하다 — MWAA는 어떤 Kubernetes 클러스터에도 접근할 방법이 없다
   - B) MWAA가 모든 EKS 클러스터 내부에서 자동으로 실행되므로 `in_cluster=True`로 `KubernetesPodOperator`를 사용한다
   - C) `in_cluster=False`와 대상 EKS 클러스터를 가리키는 kubeconfig 파일로 `KubernetesPodOperator`를 사용한다
   - D) MWAA 환경 내부에 Kubernetes Operator를 직접 설치한다

<details>

<summary>정답 보기</summary>

**정답: C) `in_cluster=False`와 대상 EKS 클러스터를 가리키는 kubeconfig 파일로 `KubernetesPodOperator`를 사용한다**

**설명:**
MWAA의 실행 환경에는 in-cluster Kubernetes API 접근 권한이 없으므로, `KubernetesPodOperator`도 다른 외부 클라이언트와 동일하게 인증해야 합니다. `in_cluster=False`를 지정하고, `aws eks update-kubeconfig`로 생성해 환경의 S3 버킷에 DAG와 함께 업로드해둔 kubeconfig를 `config_file`로 지정합니다. `in_cluster=True`는 operator가 대상 클러스터 내부에서 실행될 때만 동작하는데, MWAA에서는 이 조건이 성립하지 않습니다.
</details>

3. MWAA 실행 역할에 대해 `eksctl create iamidentitymapping`을 실행하면 어떤 효과가 있나요?
   - A) MWAA 실행 역할에 AWS 계정 전체의 AdministratorAccess를 부여한다
   - B) MWAA 실행 역할의 IAM ARN을 Kubernetes 사용자명/그룹에 매핑해, EKS 클러스터의 RBAC가 해당 아이덴티티를 인식하고 권한 부여 대상으로 삼을 수 있게 한다
   - C) kubeconfig 파일을 MWAA 환경의 S3 버킷에 업로드한다
   - D) EKS 클러스터를 MWAA와 호환되는 버전으로 업그레이드한다

<details>

<summary>정답 보기</summary>

**정답: B) MWAA 실행 역할의 IAM ARN을 Kubernetes 사용자명/그룹에 매핑해, EKS 클러스터의 RBAC가 해당 아이덴티티를 인식하고 권한 부여 대상으로 삼을 수 있게 한다**

**설명:**
`eksctl create iamidentitymapping`은 클러스터의 `aws-auth` 구성에 항목을 추가해, IAM 역할 ARN을 특정 Kubernetes 사용자명과 그룹에 연결합니다. 이는 MWAA 실행 역할이 클러스터 내부에서 *누구인지*만 결정할 뿐이며, 실제로 *무엇을 할 수 있는지*는 해당 그룹에 바인딩된 별도의 `ClusterRole`/`ClusterRoleBinding`이 결정합니다(예: `system:masters`처럼 광범위하게 두지 않고 특정 네임스페이스의 Pod 생성 권한 정도로 좁히는 것).
</details>

4. 다음 중 EKS 셀프 매니지드 Airflow(Part 1~3)에는 없지만 MWAA에는 실제로 존재하는 제약은 무엇인가요?
   - A) MWAA는 Python 코드를 전혀 실행할 수 없다
   - B) 플러그인은 S3에 업로드하는 압축된 `plugins.zip`으로만 배포해야 하고, Python 의존성도 `requirements.txt`를 통해 빌드 시점에 해석되며 root/시스템 패키지 설치가 불가능하다
   - C) MWAA는 `KubernetesPodOperator`를 사용할 수 없다
   - D) MWAA는 Airflow REST API를 지원하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) 플러그인은 S3에 업로드하는 압축된 `plugins.zip`으로만 배포해야 하고, Python 의존성도 `requirements.txt`를 통해 빌드 시점에 해석되며 root/시스템 패키지 설치가 불가능하다**

**설명:**
셀프 매니지드 Airflow는 이미지에 plugins 폴더와 임의의 시스템 패키지를 자유롭게 빌드해 넣을 수 있습니다. 반면 MWAA는 플러그인을 S3의 `plugins.zip`으로, Python 의존성을 S3의 `requirements.txt`로 업로드해야 하며 MWAA의 빌드 시점 의존성 해석을 거쳐야 합니다 — root나 시스템 수준 패키지 설치는 아예 불가능합니다. `KubernetesPodOperator`와 REST API는 MWAA에서도 그대로 사용할 수 있습니다.
</details>

5. Part 3의 `GitDagBundle`과 비교했을 때, MWAA는 DAG 파일을 scheduler에 어떻게 전달하나요?
   - A) MWAA도 `GitDagBundle`을 네이티브로 지원한다
   - B) MWAA는 오직 S3 버킷을 통해서만 DAG를 동기화하며, git-sync나 DAG 번들 방식은 전혀 지원하지 않는다
   - C) MWAA는 커스텀 컨테이너 이미지에 DAG를 빌드해 넣어야 한다
   - D) MWAA는 중간 저장소 없이 GitHub에서 DAG를 직접 가져온다

<details>

<summary>정답 보기</summary>

**정답: B) MWAA는 오직 S3 버킷을 통해서만 DAG를 동기화하며, git-sync나 DAG 번들 방식은 전혀 지원하지 않는다**

**설명:**
Part 3에서 다룬 Airflow 3의 네이티브 `GitDagBundle`은 셀프 매니지드 dag-processor가 자체 폴링 주기로 git 저장소에서 DAG를 직접 가져오게 해줍니다 — S3 단계가 필요 없습니다. MWAA에는 이에 대응하는 기능이 없습니다. 모든 DAG 변경은 수동 `aws s3 sync`든 이를 대체하는 CI 단계든, 반드시 환경의 S3 버킷에 파일로 먼저 올라가야 하며, 이는 코드 머지와 실제 실행 사이에 한 단계가 더 끼어드는 셈입니다.
</details>

6. MWAA는 2026년 4월에 어떤 릴리스에 대한 지원을 추가했으며, 이는 MWAA의 버전 최신성 트레이드오프를 어떻게 보여주나요?
   - A) Airflow 2.11, Airflow 자체의 2.11 릴리스보다 약 3개월 늦게
   - B) Airflow 3.2, Airflow 자체의 3.2 릴리스보다 약 3개월 늦게 지원을 추가했으며, 그보다 앞서 2026년 1월에는 Airflow 2.11로 먼저 브릿지됨
   - C) Airflow 4.0, 업스트림 릴리스보다 앞서서
   - D) MWAA는 특정 Airflow 버전을 따로 추적하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) Airflow 3.2, Airflow 자체의 3.2 릴리스보다 약 3개월 늦게 지원을 추가했으며, 그보다 앞서 2026년 1월에는 Airflow 2.11로 먼저 브릿지됨**

**설명:**
MWAA는 2026년 4월에 Airflow 3.2 지원을 추가했는데, 이는 업스트림 Airflow 자체의 3.2 릴리스보다 약 3개월 늦은 시점입니다. 그리고 이보다 앞서 2026년 1월에는 2.x 계열을 브릿지 릴리스인 Airflow 2.11로 먼저 갱신한 바 있습니다. 이 지연은 셀프 매니지드 Airflow(업스트림 릴리스가 나오는 즉시 채택 가능) 대신 MWAA를 선택할 때 감수해야 하는 구체적인 버전 최신성 트레이드오프입니다.
</details>

7. EKS 셀프 매니지드 Airflow보다 Amazon MWAA가 더 적합한 경우는 언제인가요?
   - A) 커스텀 실행기와 태스크 단위 Docker 이미지 격리가 필요할 때
   - B) 멀티클라우드 이식성이 필요할 때
   - C) DAG가 단순한 순수 Python/PyPI 워크로드이고, Airflow 컨트롤 플레인 인프라를 운영할 여력이 부족할 때
   - D) 업스트림의 최신 Airflow 기능을 나온 그달 즉시 쓰고 싶을 때

<details>

<summary>정답 보기</summary>

**정답: C) DAG가 단순한 순수 Python/PyPI 워크로드이고, Airflow 컨트롤 플레인 인프라를 운영할 여력이 부족할 때**

**설명:**
MWAA는 커스텀 실행기나 시스템 수준 의존성이 필요 없는 단순한 DAG를 운영하며, Airflow 컨트롤 플레인의 패치·스케일링·가용성 관리를 전혀 하고 싶지 않은 AWS 전용 조직에 적합합니다. 커스텀 실행기, 태스크 단위 이미지 격리, 멀티클라우드 이식성, 신규 기능의 즉시 채택은 모두 EKS 셀프 매니지드 Airflow를 선호할 이유입니다.
</details>

8. EKS 셀프 매니지드 Airflow와 MWAA의 비용 트레이드오프에 대한 설명 중 가장 정확한 것은 무엇인가요?
   - A) 셀프 매니지드 Airflow는 모든 상황에서 항상 MWAA보다 30~60% 저렴하다
   - B) 대규모에서 잘 튜닝된 셀프 매니지드 배포는 잘 튜닝되지 않은 MWAA 환경보다 30~60% 낮은 비용을 보고한 사례가 있지만, 이는 트래픽 패턴과 튜닝 노력에 크게 의존하며 보장된 수치는 아니다
   - C) AWS가 모든 컴퓨팅 비용을 부담하므로 MWAA에는 의미 있는 비용이 발생하지 않는다
   - D) 규모와 무관하게 두 방식의 비용은 동일하다

<details>

<summary>정답 보기</summary>

**정답: B) 대규모에서 잘 튜닝된 셀프 매니지드 배포는 잘 튜닝되지 않은 MWAA 환경보다 30~60% 낮은 비용을 보고한 사례가 있지만, 이는 트래픽 패턴과 튜닝 노력에 크게 의존하며 보장된 수치는 아니다**

**설명:**
30~60%라는 수치는 대규모의 잘 튜닝된 셀프 매니지드 배포를 잘 튜닝되지 않은 MWAA 환경과 비교했을 때 실제로 보고된 결과이지만, 상황에 따라 달라지는 값이지 보편적으로 보장되는 수치가 아닙니다. 또한 셀프 호스팅에 필요한 지속적인 엔지니어링 노력과 함께 저울질해야 합니다.
</details>

## 단답형 문제

9. DAG가 `KubernetesPodOperator`를 사용할 수 있으려면 MWAA 환경의 `requirements.txt`에 무엇을 추가해야 하나요?

<details>

<summary>정답 보기</summary>

**정답: `apache-airflow[cncf.kubernetes]`**

**설명:**
`cncf.kubernetes` 프로바이더 패키지가 `KubernetesPodOperator`와 관련 Kubernetes 통합 클래스를 제공합니다. 이를 `requirements.txt`에 추가하지 않으면 DAG 파일을 파싱하는 시점에 해당 import가 실패합니다.
</details>

10. MWAA에서 실행되는 `KubernetesPodOperator`가 별도의 EKS 클러스터를 대상으로 할 때, MWAA가 그 클러스터 내부에서 실행되는 경우는 없으므로 반드시 `False`로 설정해야 하는 파라미터는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `in_cluster`**

**설명:**
`in_cluster=True`는 operator가 자신이 실행되고 있는 클러스터 내부의 Kubernetes API 접근 권한을 사용하도록 지시하는데, MWAA의 컨트롤 플레인은 별도의 AWS 관리 인프라에서 실행되므로 이 조건이 성립하지 않습니다. `in_cluster=False`로 설정하고 업로드해둔 kubeconfig를 가리키는 `config_file`을 지정해야 operator가 외부 EKS 클러스터에 인증할 수 있습니다.
</details>

## 실습 문제

11. `us-east-1`의 `data-eks-cluster`라는 EKS 클러스터 RBAC에 MWAA 실행 역할(`arn:aws:iam::123456789012:role/mwaa-execution-role-my-environment`)을 Kubernetes 그룹 `mwaa-pod-launcher`로 매핑하는 `eksctl` 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
eksctl create iamidentitymapping \
  --cluster data-eks-cluster \
  --region us-east-1 \
  --arn arn:aws:iam::123456789012:role/mwaa-execution-role-my-environment \
  --username mwaa-executor \
  --group mwaa-pod-launcher
```

**설명:**
이 명령은 클러스터의 `aws-auth` 구성에 항목을 추가해, EKS 클러스터의 RBAC가 MWAA 실행 역할의 IAM ARN을 Kubernetes 사용자 `mwaa-executor`이자 그룹 `mwaa-pod-launcher`의 일원으로 인식하게 합니다. 이 아이덴티티가 실제로 무엇을 할 수 있는지는 `mwaa-pod-launcher`에 바인딩된 별도의 `ClusterRole`/`ClusterRoleBinding` — DAG가 실제로 필요로 하는 범위로 좁혀야 하며 `system:masters`처럼 광범위하게 두면 안 됨 — 이 결정합니다.
</details>

12. 외부 EKS 클러스터의 `data-processing` 네임스페이스에서 `123456789012.dkr.ecr.us-east-1.amazonaws.com/data-etl:latest` 이미지를 실행하는 MWAA DAG의 `KubernetesPodOperator` 태스크를 작성하세요. kubeconfig는 `/usr/local/airflow/dags/kube_config.yaml`에 배치되어 있습니다.

<details>

<summary>정답 보기</summary>

**정답:**
```python
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

process_data = KubernetesPodOperator(
    task_id="process_data_on_eks",
    name="process-data",
    namespace="data-processing",
    image="123456789012.dkr.ecr.us-east-1.amazonaws.com/data-etl:latest",
    cmds=["python", "process.py"],
    in_cluster=False,
    config_file="/usr/local/airflow/dags/kube_config.yaml",
    is_delete_operator_pod=True,
)
```

**설명:**
`in_cluster=False`는 operator가 대상 클러스터 내부에서 실행되고 있다고 가정하지 않도록 지시합니다. `config_file`은 `aws eks update-kubeconfig`로 미리 생성해 환경의 S3 버킷에 DAG 코드와 함께 업로드해둔 kubeconfig를 가리킵니다. `is_delete_operator_pod=True`는 태스크가 끝난 뒤 Pod를 정리해, 완료된 태스크 Pod가 대상 클러스터에 계속 남아있지 않도록 하는 일반적인 관행입니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/04-mwaa-integration.md)
