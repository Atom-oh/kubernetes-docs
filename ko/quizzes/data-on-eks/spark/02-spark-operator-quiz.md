# Spark Operator 퀴즈

이 퀴즈는 두 가지 Spark-on-Kubernetes Operator 선택지, Operator가 순수 `spark-submit` 대비 제공하는 것, mutating admission webhook, 핵심 CRD, EKS 배포 고려사항에 대한 이해도를 테스트합니다.

## 객관식 문제

1. apache/spark-kubernetes-operator와 기존 Kubeflow 커뮤니티 Operator의 관계는 무엇인가요?
   - A) 동일한 코드베이스의 리브랜딩
   - B) kubeflow/spark-operator의 코드를 대부분 재사용한 포크
   - C) Apache Software Foundation 거버넌스 하에 처음부터 새로 만들어진 별개의 Operator이며, Kubeflow 프로젝트를 되살린 것이 아님
   - D) kubeflow/spark-operator를 대체했고, 그 프로젝트는 더 이상 관리되지 않음

<details>

<summary>정답 보기</summary>

**정답: C) Apache Software Foundation 거버넌스 하에 처음부터 새로 만들어진 별개의 Operator이며, Kubeflow 프로젝트를 되살린 것이 아님**

**설명:**
apache/spark-kubernetes-operator는 2023년 11월 SPIP(Spark Improvement Proposal)로 제안되어 ASF 거버넌스 하에 독립적으로 만들어졌습니다. kubeflow/spark-operator와는 별개의 프로젝트이며, kubeflow/spark-operator 역시 별도로 계속 관리되고 활발히 릴리스되고 있습니다(예: v2.5.0).
</details>

2. kubeflow/spark-operator의 v2.5.0 릴리스 시점 상태를 가장 잘 설명하는 것은 무엇인가요?
   - A) ASF Operator로 대체되어 더 이상 사용되지 않음
   - B) 네임스페이스 라벨 기반 감시, SparkConnect 웹훅 검증 같은 기능이 추가되며 여전히 활발히 개발 중
   - C) Spark 3.0 이전 버전만 지원
   - D) Kubernetes 1.34 이상이 필요함

<details>

<summary>정답 보기</summary>

**정답: B) 네임스페이스 라벨 기반 감시, SparkConnect 웹훅 검증 같은 기능이 추가되며 여전히 활발히 개발 중**

**설명:**
kubeflow/spark-operator v2.5.0은 alpha 기능 게이트, 네임스페이스 라벨 기반 감시, Python API 자동 생성, SparkConnect 웹훅 검증을 추가했고, 수년간 Helm을 주요 설치 방식으로 배포해 왔습니다. Kubernetes 1.28 이상에서 동작하며 1.34 이상을 요구하지는 않습니다.
</details>

3. 이미 Spark 4와 Apache DataFusion Comet 가속을 표준으로 채택하려는 팀이 Operator를 선택하려고 합니다. 이 문서 기준으로 더 적합한 선택은 무엇인가요?
   - A) 더 오래되었으므로 kubeflow/spark-operator
   - B) Spark 4 가속 연동을 네이티브로 제공하므로 apache/spark-kubernetes-operator
   - C) 두 Operator 모두 Spark 4를 지원하지 않음
   - D) 어느 Operator를 선택해도 차이가 없음

<details>

<summary>정답 보기</summary>

**정답: B) Spark 4 가속 연동을 네이티브로 제공하므로 apache/spark-kubernetes-operator**

**설명:**
Spark 프로젝트 자체가 만든 apache/spark-kubernetes-operator는 Spark 4의 가속 엔진(Apache DataFusion Comet, Apache Gluten)에 대한 1급 연동을 제공합니다. kubeflow/spark-operator는 더 넓게 채택되어 있지만 가속 기능에 특화되어 있지는 않습니다.
</details>

4. Kubernetes에서 Operator 없이 순수 `spark-submit`만으로 Spark 작업을 실행할 때의 주된 한계는 무엇인가요?
   - A) executor Pod를 전혀 생성할 수 없음
   - B) 실패한 드라이버를 재시도하거나 CRD로 상태를 보고하는 Kubernetes 네이티브 개념이 없음
   - C) Java 애플리케이션만 지원함
   - D) 작업마다 별도의 Kubernetes 클러스터가 필요함

<details>

<summary>정답 보기</summary>

**정답: B) 실패한 드라이버를 재시도하거나 CRD로 상태를 보고하는 Kubernetes 네이티브 개념이 없음**

**설명:**
`spark-submit`은 fire-and-forget 방식입니다. 드라이버 Pod가 생성된 후 실패해도 아무것도 재제출하지 않고, 상태를 조회할 CRD도 없습니다. Operator는 `restartPolicy`를 추가하고 `SparkApplication` CR의 `.status` 필드로 상태를 노출합니다.
</details>

5. `spec.driver`/`spec.executor`에 선언된 볼륨, 사이드카, affinity 규칙, secret을 실제 실행 중인 Pod에 주입하는 역할을 하는 컴포넌트는 무엇인가요?
   - A) Kubernetes 스케줄러
   - B) Operator가 등록하는 mutating admission webhook
   - C) `spark-submit` CLI
   - D) EBS CSI 드라이버

<details>

<summary>정답 보기</summary>

**정답: B) Operator가 등록하는 mutating admission webhook**

**설명:**
두 Spark Operator 모두 driver/executor Pod 생성 요청을 가로채는 mutating admission webhook을 등록하고, `SparkApplication` 스펙에 선언된 커스터마이징을 주입합니다 — 이 덕분에 `--conf spark.kubernetes.driver.podTemplateFile`로 pod 템플릿을 직접 만드는 대신 CRD에 pod 수준 커스터마이징을 바로 선언할 수 있습니다.
</details>

6. kubeflow/spark-operator를 Helm으로 설치할 때 `--set webhook.enable=true`는 무엇을 제어하나요?
   - A) CRD 설치 여부
   - B) pod 커스터마이징을 적용하는 mutating admission webhook의 활성화 여부
   - C) S3 접근 활성화 여부
   - D) Spark History Server 배포 여부

<details>

<summary>정답 보기</summary>

**정답: B) pod 커스터마이징을 적용하는 mutating admission webhook의 활성화 여부**

**설명:**
`webhook.enable=true` 없이는 `spec.driver`/`spec.executor`에 선언한 pod 템플릿 커스터마이징(볼륨, 사이드카, affinity, secret)이 적용할 webhook이 없어 조용히 무시됩니다.
</details>

7. `spark-submit`을 호출하는 별도의 외부 `CronJob` 없이 Spark 작업을 cron 스케줄로 반복 실행할 수 있게 해주는 CRD는 무엇인가요?
   - A) `SparkApplication`
   - B) `SparkCronJob`
   - C) `ScheduledSparkApplication`
   - D) `SparkPipeline`

<details>

<summary>정답 보기</summary>

**정답: C) `ScheduledSparkApplication`**

**설명:**
`ScheduledSparkApplication`은 `SparkApplication` 템플릿을 cron `schedule` 필드와 `concurrencyPolicy`(예: 이전 실행이 끝나지 않으면 건너뛰는 `Forbid`)로 감싸, 별도의 외부 스케줄러가 필요 없게 만듭니다.
</details>

8. EKS에서 `SparkApplication`의 driver/executor Pod는 S3 데이터를 읽고 쓰기 위한 AWS 자격 증명을 보통 어떻게 얻나요?
   - A) SparkApplication 스펙에 직접 심어둔 고정 액세스 키
   - B) IRSA(또는 EKS Pod Identity 연결)로 어노테이션된 ServiceAccount를 `spec.driver.serviceAccount`/`spec.executor.serviceAccount`로 참조
   - C) S3 접근에는 AWS 자격 증명이 필요 없음
   - D) Spark 이미지에 박아넣은 IAM 사용자의 `~/.aws/credentials` 파일

<details>

<summary>정답 보기</summary>

**정답: B) IRSA(또는 EKS Pod Identity 연결)로 어노테이션된 ServiceAccount를 `spec.driver.serviceAccount`/`spec.executor.serviceAccount`로 참조**

**설명:**
`eks.amazonaws.com/role-arn`으로 어노테이션된 ServiceAccount를 driver/executor 스펙에서 참조합니다. EKS Pod Identity webhook이 임시 AWS 자격 증명을 자동으로 주입하므로, 작업 스펙 어디에도 고정 키가 등장할 필요가 없습니다.
</details>

9. `spark.local.dir`을 별도로 설정하지 않으면 기본값은 무엇이며, 왜 EKS에서 문제가 될 수 있나요?
   - A) S3 버킷이며, 셔플에는 너무 느림
   - B) 노드의 루트 EBS 볼륨 위에 있는 `emptyDir`이며, 셔플이 많은 작업에서 병목이나 공간 부족을 겪을 수 있음
   - C) ConfigMap이며, 크기가 1MB로 엄격히 제한됨
   - D) 항상 자동으로 인스턴스 스토어 NVMe를 사용함

<details>

<summary>정답 보기</summary>

**정답: B) 노드의 루트 EBS 볼륨 위에 있는 `emptyDir`이며, 셔플이 많은 작업에서 병목이나 공간 부족을 겪을 수 있음**

**설명:**
Spark의 셔플과 spill 데이터는 `spark.local.dir`에 기록되며, 별도 설정이 없으면 노드 루트 EBS 볼륨 위의 `emptyDir`이 기본값입니다. 셔플이 많은 작업은 전용 `emptyDir`(가능하면 인스턴스 스토어 NVMe)을 따로 마운트하는 것이 좋습니다.
</details>

10. JMX Prometheus Exporter 메트릭 연동의 전체 설정 내용은 이 문서 시리즈의 어디에서 다루나요?
    - A) 어디에서도 다루지 않음
    - B) Part 1: Spark on Kubernetes
    - C) Part 5: 모범 사례
    - D) 이 Spark Operator 장에서 전부 다룸

<details>

<summary>정답 보기</summary>

**정답: C) Part 5: 모범 사례**

**설명:**
이 장에서는 kubeflow/spark-operator의 Helm 차트가 드라이버/executor JVM에 JMX Prometheus Exporter Java 에이전트를 기본으로 연결해준다는 사실만 소개하며, 전체 메트릭 설정과 권장 대시보드는 Part 5: 모범 사례에서 다룹니다.
</details>

## 단답형 문제

11. 이 장에서 다룬, 현재 활발히 관리되고 있는 두 개의 Spark-on-Kubernetes Operator 이름을 쓰세요.

<details>

<summary>정답 보기</summary>

**정답: apache/spark-kubernetes-operator와 kubeflow/spark-operator**

**설명:**
apache/spark-kubernetes-operator는 ASF 거버넌스 하의 신생 프로젝트(최신 릴리스 0.9.0)이고, kubeflow/spark-operator는 더 오래되고 더 널리 채택된 커뮤니티 프로젝트(최신 릴리스 v2.5.0)입니다. 2026년 기준 둘 다 독립적으로 관리되고 있습니다.
</details>

12. apache/spark-kubernetes-operator가 CRD에 사용하는 API 그룹은 무엇이며, kubeflow/spark-operator의 `sparkoperator.k8s.io`와 어떻게 다른가요?

<details>

<summary>정답 보기</summary>

**정답: `spark.apache.org`**

**설명:**
두 Operator는 서로 다른 API 그룹으로 CRD를 정의하며, 같은 네임스페이스를 동시에 감시하도록 설계되지 않았습니다 — 클러스터당(또는 의도적으로 둘 다 쓴다면 네임스페이스당) 하나만 선택해야 합니다.
</details>

13. `SparkApplication` 스펙에서 실패한 드라이버가 자동으로 재제출되는지, 몇 번까지 재시도되는지를 제어하는 필드는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `restartPolicy` (`type: OnFailure`와 `onFailureRetries`)**

**설명:**
`restartPolicy.type`은 `Never`, `OnFailure`, `Always` 중 하나를 지정할 수 있습니다. `onFailureRetries`는 재시도 횟수를, `onFailureRetryInterval`은 재시도 사이의 백오프 간격을 설정합니다 — 순수 `spark-submit`에는 대응하는 기능이 없습니다.
</details>

14. Operator가 Spark 작업의 현재 상태(예: `RUNNING`, `COMPLETED`, `FAILED`)를 추적하고 노출하기 위해 사용하는 Kubernetes 네이티브 기능은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `SparkApplication` CR의 `.status` 필드**

**설명:**
Operator는 작업의 현재 상태를 CR의 `.status` 필드에 기록하며, `kubectl get sparkapplication`이나 `kubectl describe sparkapplication`으로 바로 확인할 수 있습니다 — 순수 `spark-submit`으로는 알 수 없던 정보입니다.
</details>

15. `ScheduledSparkApplication`에서 이전 실행이 아직 진행 중이면 새로운 스케줄 실행이 시작되지 않도록 막는 `concurrencyPolicy` 값은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `Forbid`**

**설명:**
`concurrencyPolicy: Forbid`는 이전 스케줄 실행이 끝나지 않았다면 새 실행을 건너뜁니다 — 실행이 겹치면 공유 결과물이 오염될 수 있는 작업에 유용합니다.
</details>

## 실습 문제

16. kubeflow/spark-operator를 mutating admission webhook을 활성화한 상태로 `spark-operator` 네임스페이스에 Helm으로 설치하는 전체 명령어 시퀀스를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# Spark Operator Helm 저장소 추가
helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update

# spark-operator 네임스페이스에 설치
helm install spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  --create-namespace \
  --version 2.5.0 \
  --set webhook.enable=true

# 설치 확인
kubectl get pods -n spark-operator
kubectl get crd | grep sparkoperator
```

**설명:**
`--set webhook.enable=true`가 없으면 `spec.driver`/`spec.executor`에 선언한 pod 템플릿 커스터마이징이 조용히 무시되므로 반드시 필요합니다. `--create-namespace`는 `spark-operator` 네임스페이스가 없을 경우 자동으로 생성합니다.
</details>

17. 드라이버 코어 1개, executor 2개(각 2코어)로 클러스터 모드에서 Scala word-count 작업을 실행하고, 실패 시 최대 3회까지 자동 재시도하는 최소한의 `SparkApplication`을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: sparkoperator.k8s.io/v1beta2
kind: SparkApplication
metadata:
  name: word-count
  namespace: spark-operator
spec:
  type: Scala
  mode: cluster
  image: "apache/spark:3.5.3"
  mainClass: org.apache.spark.examples.JavaWordCount
  mainApplicationFile: "local:///opt/spark/examples/jars/spark-examples.jar"
  sparkVersion: "3.5.3"
  restartPolicy:
    type: OnFailure
    onFailureRetries: 3
    onFailureRetryInterval: 10
  driver:
    cores: 1
    memory: "1g"
  executor:
    cores: 2
    instances: 2
    memory: "2g"
```

**설명:**
`restartPolicy.type: OnFailure`와 `onFailureRetries: 3`을 조합하면 드라이버가 최대 3번까지 자동으로 재제출됩니다. `executor.instances: 2`와 `executor.cores: 2`를 조합하면 각각 2코어를 요청하는 executor Pod 2개가 생성됩니다.
</details>

18. 매일 새벽 2시에 실행되고, 이전 실행이 아직 진행 중이면 새 실행을 건너뛰는 일별 ETL용 `ScheduledSparkApplication`을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: sparkoperator.k8s.io/v1beta2
kind: ScheduledSparkApplication
metadata:
  name: daily-etl
  namespace: spark-operator
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  template:
    type: Scala
    mode: cluster
    image: "apache/spark:3.5.3"
    mainClass: com.example.DailyEtlJob
    mainApplicationFile: "s3a://my-bucket/jars/daily-etl.jar"
    sparkVersion: "3.5.3"
    driver:
      cores: 1
      memory: "2g"
    executor:
      cores: 2
      instances: 4
      memory: "4g"
```

**설명:**
`schedule: "0 2 * * *"`는 매일 새벽 2시를 의미하는 표준 cron 표기입니다. `concurrencyPolicy: Forbid`는 이전 스케줄 실행이 끝나지 않았다면 새 실행 자체를 건너뛰어, 동일한 출력 위치에 겹쳐 쓰는 상황을 막아줍니다.
</details>

19. S3 접근 권한을 부여하는 IRSA용 ServiceAccount를 생성하고, 이를 `SparkApplication`의 driver/executor 스펙에서 참조하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-driver
  namespace: spark-operator
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/spark-s3-access
```

```yaml
spec:
  driver:
    serviceAccount: spark-driver
  executor:
    serviceAccount: spark-driver
```

**설명:**
`eks.amazonaws.com/role-arn` 어노테이션은 EKS Pod Identity webhook에게 이 ServiceAccount를 사용하는 Pod에 해당 IAM 역할의 임시 AWS 자격 증명을 주입하라고 알려줍니다. `driver.serviceAccount`와 `executor.serviceAccount`에서 모두 `spark-driver`를 참조하면 입력 읽기와 출력 쓰기에 필요한 S3 접근 권한을 둘 다 갖게 됩니다.
</details>

20. `SparkApplication`의 driver와 executor 모두에 `spark.local.dir` 스크래치 공간용 전용 `emptyDir` 볼륨을 추가하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
spec:
  driver:
    volumes:
      - name: spark-local-dir
        emptyDir: {}
  executor:
    volumes:
      - name: spark-local-dir
        emptyDir: {}
```

**설명:**
`spec.driver`/`spec.executor`에 선언한 `volumes`는 mutating admission webhook에 의해 실제로 실행 중인 Pod에 붙습니다. 여기에 전용 `emptyDir`(가능하면 인스턴스 스토어 NVMe 노드)을 두면 셔플/spill I/O가 노드의 루트 EBS 볼륨과 경합하는 것을 피할 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/spark/02-spark-operator.md) | [다음 퀴즈: EMR on EKS](./03-emr-on-eks-quiz.md)
