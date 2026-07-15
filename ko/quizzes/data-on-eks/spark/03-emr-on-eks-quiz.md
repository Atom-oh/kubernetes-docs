# Amazon EMR on EKS 퀴즈

이 퀴즈는 EMR on EKS의 가상 클러스터, StartJobRun 제출 모델, 작업 실행 IAM 역할, 그리고 EMR on EKS와 셀프 매니지드 Spark Operator 중 언제 무엇을 선택해야 하는지에 대한 이해도를 테스트합니다.

## 객관식 문제

1. EMR on EKS에서 가상 클러스터(virtual cluster)란 무엇인가요?
   - A) EMR을 위해 별도로 만드는 독립된 Kubernetes 클러스터
   - B) EMR 컨트롤 플레인 개념과 실제 EKS 네임스페이스 사이의 매핑
   - C) Spark 드라이버를 호스팅하는 가상 머신
   - D) EKS 클러스터 노드 그룹의 스냅샷

<details>

<summary>정답 보기</summary>

**정답: B) EMR 컨트롤 플레인 개념과 실제 EKS 네임스페이스 사이의 매핑**

**설명:**
가상 클러스터는 기존 EKS 네임스페이스를 EMR 컨트롤 플레인에 등록하는 것입니다. 등록 자체로는 새로운 인프라가 프로비저닝되지 않습니다 — 클러스터가 아니라 포인터에 가깝습니다. 해당 가상 클러스터 ID로 제출된 모든 작업은 그 네임스페이스 안에 드라이버/Executor Pod로 생성되며, 이미 적용된 쿼터와 RBAC의 제약을 그대로 따릅니다.
</details>

2. EMR on EKS와 셀프 매니지드 Spark Operator 방식 사이의 근본적인 UX 차이는 무엇인가요?
   - A) EMR on EKS는 Kubernetes에서 전혀 실행되지 않는다
   - B) 작업을 `SparkApplication` CR에 `kubectl apply`하는 대신 StartJobRun API로 제출한다
   - C) Spark Operator는 EKS에서는 실행할 수 없고 온프레미스에서만 가능하다
   - D) EMR on EKS는 배치 작업만 지원하고 스트리밍은 지원하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) 작업을 `SparkApplication` CR에 `kubectl apply`하는 대신 StartJobRun API로 제출한다**

**설명:**
Spark Operator 방식은 작업을 `SparkApplication` Kubernetes 객체로 정의하고 `kubectl`로(보통 GitOps를 통해) 적용하며, 컨트롤러가 해당 CRD를 조정합니다. EMR on EKS는 대신 작업 제출을 일반적인 AWS API 호출로 노출합니다 — CLI, SDK, 콘솔, Step Functions에서 호출 가능하며, 작업을 실행하는 데 `kubectl` 접근 권한이 필요하지 않습니다.
</details>

3. 작업 실행 IAM 역할을 가상 클러스터에서 사용하려면 사전에 무엇이 필요한가요?
   - A) 아무 설정도 필요 없다 — 계정 내 어떤 IAM 역할이든 자동으로 사용할 수 있다
   - B) 역할을 온보딩해, EMR on EKS가 해당 네임스페이스의 Pod를 위해 이 역할을 위임할 수 있도록 신뢰 정책을 갱신해야 한다
   - C) 역할을 EKS 워커 노드의 인스턴스 프로파일에 직접 연결해야 한다
   - D) 매 작업 실행마다 역할을 삭제하고 다시 생성해야 한다

<details>

<summary>정답 보기</summary>

**정답: B) 역할을 온보딩해, EMR on EKS가 해당 네임스페이스의 Pod를 위해 이 역할을 위임할 수 있도록 신뢰 정책을 갱신해야 한다**

**설명:**
작업 실행 역할은 특정 작업이 접근할 수 있는 범위(S3 버킷, 데이터 카탈로그, KMS 키 등)로 좁혀지며, 매 `start-job-run` 호출마다 명시적으로 전달됩니다. 이 역할이 동작하려면 `update-role-trust-policy`로 신뢰 정책을 갱신해, EMR on EKS가 가상 클러스터 네임스페이스의 Pod를 대신해 이 역할을 위임할 수 있어야 하며, 이는 IRSA와 유사한 OIDC 신뢰 관계로 바인딩됩니다.
</details>

4. EMR 릴리스 레이블에 대한 설명으로 옳은 것은 무엇인가요?
   - A) `emr-x.x.x-latest` 형식을 따르며 AWS가 패치한 특정 Spark 빌드를 고정한다
   - B) EKS Kubernetes 버전만 제어하고 Spark 버전과는 무관하다
   - C) 사용 전에 Docker 이미지로 직접 다시 빌드해야 한다
   - D) 업스트림 Apache Spark 버전 번호와 완전히 동일하며 AWS 패치가 전혀 없다

<details>

<summary>정답 보기</summary>

**정답: A) `emr-x.x.x-latest` 형식을 따르며 AWS가 패치한 특정 Spark 빌드를 고정한다**

**설명:**
`emr-7.6.0-latest` 같은 릴리스 레이블은 Spark 3.5.3-amzn-0 같은 특정 빌드에 매핑됩니다. `-amzn-N` 접미사는 오픈소스 릴리스 위에 AWS 자체 패치(S3 커넥터 튜닝, AQE·셔플 개선)가 얹혀 있음을 나타냅니다. `start-job-run`에 릴리스 레이블을 전달하면 작업의 Pod에 사용할 Spark 버전과 컨테이너 이미지가 함께 결정됩니다.
</details>

5. EMR on EKS가 오픈소스 Spark Operator를 작업 제출 모델의 한 선택지로 사용할 수 있게 된 것은 몇 버전부터인가요?
   - A) EMR 5.0
   - B) EMR 6.10
   - C) EMR 7.6
   - D) 어떤 버전에서도 불가능하며 둘은 항상 배타적이다

<details>

<summary>정답 보기</summary>

**정답: B) EMR 6.10**

**설명:**
EMR 6.10부터 EMR on EKS는 자체적인 Pod 생성 경로 대신 Spark Operator의 CRD 기반 조정에 작업 제출을 위임할 수 있으며, 이때도 EMR의 AWS 최적화 Spark 런타임과 릴리스 레이블 기반 버전 관리는 그대로 유지됩니다. 즉 EMR on EKS와 셀프 매니지드 Spark Operator가 반드시 양자택일 관계는 아닙니다.
</details>

6. EMR Studio는 무엇인가요?
   - A) EMR 클러스터에 태그를 붙이는 CLI 도구
   - B) EKS 가상 클러스터를 대상으로 Spark 코드를 개발하고 제출할 수 있는 노트북/IDE 스타일 인터페이스
   - C) EMR on EKS 비용을 보여주는 결제 대시보드
   - D) 대화형 코드 실행이 불가능한, `start-job-run` API의 대체 서비스

<details>

<summary>정답 보기</summary>

**정답: B) EKS 가상 클러스터를 대상으로 Spark 코드를 개발하고 제출할 수 있는 노트북/IDE 스타일 인터페이스**

**설명:**
EMR Studio는 예약된 `start-job-run` 파이프라인을 뒷받침하는 동일한 가상 클러스터를 대상으로, 같은 가상 클러스터/실행 역할 모델을 사용하는 Jupyter 스타일의 대화형 개발 환경을 제공합니다.
</details>

7. 다음 중 EMR on EKS가 셀프 매니지드 Spark Operator보다 유리한 점은 무엇인가요?
   - A) AWS가 아닌 포크를 포함해 원하는 Spark 빌드를 완전히 자유롭게 선택할 수 있다
   - B) 직접 구축하지 않아도 CloudWatch Logs/Metrics, Step Functions, EventBridge 통합이 기본 제공된다
   - C) 작업이 Kubernetes 매니페스트라서 어떤 GitOps 파이프라인에도 바로 편입된다
   - D) AWS 컨트롤 플레인이나 API에 전혀 의존하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) 직접 구축하지 않아도 CloudWatch Logs/Metrics, Step Functions, EventBridge 통합이 기본 제공된다**

**설명:**
EMR on EKS는 로깅, 메트릭, 오케스트레이션을 위한 AWS 서비스 통합이 기본으로 내장되어 있습니다. 반대로 셀프 매니지드 Spark Operator는 Spark/Kubernetes 버전 조합을 완전히 통제할 수 있고 매니페스트 기반 GitOps 파이프라인에 자연스럽게 편입되지만, 관측성과 오케스트레이션 연동은 직접 구성해야 합니다.
</details>

8. 팀이 EMR on EKS 대신 셀프 매니지드 Spark Operator를 유지할 만한 이유는 무엇인가요?
   - A) 아직 어떤 EMR 릴리스 레이블에도 반영되지 않은 Spark 빌드나 포크를 실행해야 하는 경우
   - B) 관리형 CloudWatch 통합을 원하는 경우
   - C) `SparkApplication` 매니페스트를 절대 작성하고 싶지 않은 경우
   - D) Spark 버전 업그레이드 일정을 AWS가 대신 결정해주길 원하는 경우

<details>

<summary>정답 보기</summary>

**정답: A) 아직 어떤 EMR 릴리스 레이블에도 반영되지 않은 Spark 빌드나 포크를 실행해야 하는 경우**

**설명:**
EMR 릴리스 레이블은 AWS가 패치한 특정 Spark 버전 집합만 큐레이션합니다. 더 최신의 업스트림 릴리스, 커스텀 포크, AWS 패치가 없는 빌드가 필요하거나, 업그레이드 시점과 EKS 외 클러스터로의 이식성을 완전히 통제해야 하는 팀에게는 셀프 매니지드 Spark Operator가 더 적합합니다.
</details>

9. EMR on EKS의 StartJobRun API로 제출한 작업 아래에서 실제로 실행되는 Pod는 어떤 상태인가요?
   - A) `kubectl`로는 보이지 않는, 별도의 숨겨진 클러스터에서 실행된다
   - B) 가상 클러스터의 네임스페이스 안에 있는 평범한 EKS Pod이며 `kubectl get pods`로 조회할 수 있다
   - C) Kubernetes 바깥에서, EMR 전용 AWS Fargate 위에서 완전히 별도로 실행된다
   - D) EMR 콘솔을 통해서만 볼 수 있고 Kubernetes API로는 절대 확인할 수 없다

<details>

<summary>정답 보기</summary>

**정답: B) 가상 클러스터의 네임스페이스 안에 있는 평범한 EKS Pod이며 `kubectl get pods`로 조회할 수 있다**

**설명:**
`kubectl apply` 대신 AWS API로 작업을 제출하더라도, 결과적으로 생성되는 드라이버/Executor Pod는 가상 클러스터가 가리키는 네임스페이스에 스케줄되는 일반 Pod입니다. `kubectl get pods -n <네임스페이스>`로 다른 워크로드처럼 조회할 수 있으며, 다만 그 스펙을 직접 작성하지 않을 뿐입니다.
</details>

10. 가상 클러스터를 삭제하면 어떤 일이 일어나나요?
    - A) 기반이 되는 EKS 네임스페이스와 그 안의 모든 리소스가 함께 삭제된다
    - B) EMR 등록 정보만 삭제되며 네임스페이스와 그 안에서 실행 중인 워크로드는 영향을 받지 않는다
    - C) EKS 클러스터 전체가 삭제된다
    - D) 온보딩된 모든 작업 실행 IAM 역할이 자동으로 삭제된다

<details>

<summary>정답 보기</summary>

**정답: B) EMR 등록 정보만 삭제되며 네임스페이스와 그 안에서 실행 중인 워크로드는 영향을 받지 않는다**

**설명:**
가상 클러스터는 새로운 인프라가 아니라 포인터/등록 정보입니다. 이를 삭제하면 EMR 컨트롤 플레인과 EKS 네임스페이스 사이의 매핑만 제거되며, 네임스페이스 자체와 그 안에서 실행 중인 것들은 영향을 받지 않습니다.
</details>

## 단답형 문제

11. Kubernetes 매니페스트를 적용하는 대신 EMR on EKS에 Spark 작업을 제출할 때 사용하는 AWS API 호출은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `StartJobRun`**

**설명:**
`StartJobRun`(`aws emr-containers start-job-run`으로 호출)은 가상 클러스터에 작업을 제출하는 API입니다. 가상 클러스터 ID, 실행 역할 ARN, 릴리스 레이블, 작업 드라이버 정의를 인자로 받으며, CLI, 모든 AWS SDK, 콘솔, 또는 Step Functions 같은 오케스트레이션 도구에서 호출할 수 있습니다.
</details>

12. 작업 단위로 범위가 좁혀져야 하고, 매 `start-job-run` 호출마다 명시적으로 전달해야 하는 IAM 개념은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 작업 실행 역할(job execution role)**

**설명:**
클러스터에 한 번 연결해두는 역할과 달리, EMR on EKS의 작업 실행 역할은 특정 작업이 접근할 수 있는 범위로 좁혀지며 매 `start-job-run` 호출의 `--execution-role-arn`으로 전달해야 합니다. 사용 전에 신뢰 정책을 갱신해 가상 클러스터에 먼저 온보딩되어야 합니다.
</details>

13. EMR 릴리스 레이블은 어떤 명명 규칙을 따르나요?

<details>

<summary>정답 보기</summary>

**정답: `emr-x.x.x-latest`**

**설명:**
예를 들어 `emr-7.0.0-latest`는 Spark 3.5.0-amzn-0에 매핑되고, `emr-7.6.0-latest`는 Spark 3.5.3-amzn-0에 매핑됩니다. 이 레이블이 작업의 드라이버/Executor Pod에 사용할 Spark 버전과 컨테이너 이미지를 함께 결정합니다.
</details>

14. EMR on EC2, EMR Serverless, EMR on EKS 전체에 Spark 4.0을 GA로 가져오는 예정된 릴리스 라인은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `emr-spark-8.0` 릴리스 라인**

**설명:**
`emr-spark-8.0` 릴리스 라인은 EC2, Serverless, EKS라는 세 가지 EMR 배포 대상 전체에 동일하게 Spark 4.0 GA를 가져오는 릴리스입니다.
</details>

15. EMR 6.10부터 EMR on EKS가 내부적으로 위임할 수 있게 된 대체 작업 제출 메커니즘은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 오픈소스 Spark Operator**

**설명:**
EMR 6.10부터 EMR on EKS는 자체적인 Pod 생성 경로만이 아니라, 오픈소스 Spark Operator의 CRD 기반 조정을 작업 제출 모델의 한 선택지로 사용할 수 있습니다 — 이때도 EMR의 최적화된 Spark 런타임과 릴리스 레이블 기반 버전 관리는 그대로 유지됩니다.
</details>

## 실습 문제

16. `my-eks-cluster` 클러스터의 기존 EKS 네임스페이스 `emr-spark`를 `my-spark-vc`라는 이름의 EMR 가상 클러스터로 등록하는 AWS CLI 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
aws emr-containers create-virtual-cluster \
  --name my-spark-vc \
  --container-provider '{
    "id": "my-eks-cluster",
    "type": "EKS",
    "info": {
      "eksInfo": {
        "namespace": "emr-spark"
      }
    }
  }'
```

**설명:**
`create-virtual-cluster`는 EKS 클러스터 `my-eks-cluster`의 네임스페이스 `emr-spark`를 EMR 컨트롤 플레인에 등록합니다. 이 호출은 이후 모든 `start-job-run` 호출에서 사용할 `virtualClusterId`를 반환합니다. 이 호출 자체로는 새로운 인프라가 프로비저닝되지 않고 등록 정보만 생성됩니다.
</details>

17. `my-eks-cluster` 클러스터의 `emr-spark` 네임스페이스에 있는 Pod를 위해, EMR on EKS 서비스가 작업 실행 역할 `my-job-execution-role`을 위임할 수 있도록 권한을 부여하는 AWS CLI 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
aws emr-containers update-role-trust-policy \
  --cluster-name my-eks-cluster \
  --namespace emr-spark \
  --role-name my-job-execution-role
```

**설명:**
`update-role-trust-policy`는 역할의 신뢰 정책을 갱신해 해당 역할을 가상 클러스터에 온보딩합니다. 이를 통해 EMR on EKS가 해당 네임스페이스에서 실행되는 Pod를 대신해 이 역할을 위임할 수 있게 되며, 이는 IRSA와 유사한 OIDC 신뢰 관계로 바인딩됩니다. 이 작업이 성공해야 이후 `start-job-run` 호출의 `--execution-role-arn`으로 이 역할을 전달할 수 있습니다.
</details>

18. 가상 클러스터 `abcd1234efgh5678ijkl9012mnop`에, 실행 역할 `arn:aws:iam::111122223333:role/my-job-execution-role`과 릴리스 레이블 `emr-7.6.0-latest`를 사용해 PySpark 작업(`s3://my-bucket/jobs/etl-job.py`)을 제출하는 AWS CLI 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
aws emr-containers start-job-run \
  --virtual-cluster-id abcd1234efgh5678ijkl9012mnop \
  --name my-etl-job \
  --execution-role-arn arn:aws:iam::111122223333:role/my-job-execution-role \
  --release-label emr-7.6.0-latest \
  --job-driver '{
    "sparkSubmitJobDriver": {
      "entryPoint": "s3://my-bucket/jobs/etl-job.py",
      "sparkSubmitParameters": "--conf spark.executor.instances=4 --conf spark.executor.memory=4G"
    }
  }'
```

**설명:**
`--virtual-cluster-id`는 작업이 실행될 네임스페이스를 지정하고, `--execution-role-arn`은 작업이 접근할 수 있는 범위를 제한하며, `--release-label`은 Spark 버전과 컨테이너 이미지를 결정합니다. `--job-driver` 인자의 `sparkSubmitJobDriver.entryPoint`와 `sparkSubmitParameters`는 `spark-submit`에 직접 전달하던 인자와 동일한 역할을 합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/spark/03-emr-on-eks.md)
