# Helm 배포와 Executor 선택 퀴즈

이 퀴즈는 두 가지 Airflow Helm 차트의 차이, 공식 차트를 이용한 설치, KubernetesExecutor와 CeleryExecutor의 트레이드오프, Celery worker의 KEDA 기반 오토스케일링에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Apache Airflow 프로젝트가 직접 유지보수하는 공식 Helm 차트는 무엇인가요?
   - A) `airflow-helm/charts`
   - B) `apache/airflow`
   - C) `bitnami/airflow`
   - D) 둘 다 동등하게 공식 차트임

<details>

<summary>정답 보기</summary>

**정답: B) `apache/airflow`**

**설명:**
`apache/airflow`는 메인 `apache/airflow` 저장소의 `chart` 디렉터리에서 배포되며, 업스트림 문서와 릴리스 노트가 가리키는 차트입니다. `airflow-helm/charts`는 더 오래된, 독립적으로 유지보수되는 커뮤니티 차트로 values 스키마도 다르고 Apache Airflow 프로젝트와는 무관합니다 — 오래된 튜토리얼을 따라가다 혼동하는 가장 흔한 원인입니다.

</details>

2. 차트 1.22.0 기준으로 공식 `apache/airflow` 차트가 요구하는 최소 Helm 버전은 무엇인가요?
   - A) Helm 2.x
   - B) Helm 3.12.0
   - C) Helm 3.19.0
   - D) Helm 3.x라면 어떤 버전이든 무관

<details>

<summary>정답 보기</summary>

**정답: C) Helm 3.19.0**

**설명:**
차트는 최소 요구 버전으로 Helm 3.19.0을 명시합니다. 이 제약은 차트 자체의 `Chart.yaml`에서 강제되므로, 더 낮은 버전의 Helm 클라이언트로 설치를 시도하면 배포가 어설프게 진행되는 것이 아니라 설치 시점에 곧바로 실패합니다.

</details>

3. 공식 `apache/airflow` 차트가 Kubernetes 1.30+를 요구하기 시작한 차트 버전은 언제부터인가요?
   - A) 1.0.0
   - B) 1.10.0
   - C) 1.16.0
   - D) 1.22.0

<details>

<summary>정답 보기</summary>

**정답: C) 1.16.0**

**설명:**
1.16.0 버전에서 Kubernetes 1.30+ 요구 사항이 도입되었고, 이후 현재의 1.22.0을 포함한 후속 버전까지 그대로 유지되고 있습니다.

</details>

4. 차트가 Celery worker Deployment와 Redis 브로커를 배포할지 여부 자체를 결정하는 최상위 `values.yaml` 필드는 무엇인가요?
   - A) `workers.replicas`
   - B) `executor`
   - C) `postgresql.enabled`
   - D) `scheduler.replicas`

<details>

<summary>정답 보기</summary>

**정답: B) `executor`**

**설명:**
`executor: CeleryExecutor`로 설정하면 worker Deployment와 Redis 브로커가 조건부로 렌더링되고, `executor: KubernetesExecutor`에서는 둘 다 렌더링되지 않습니다. 이 필드가 배포되는 컴포넌트 자체를 바꾸기 때문에, 이미 프로덕션 트래픽을 받고 있는 배포에서 이 값을 변경하는 것은 파급 효과가 큽니다.

</details>

5. 간단한 태스크라도 `KubernetesExecutor`에서 겪는 콜드 스타트 지연은 대략 어느 정도인가요?
   - A) 수 밀리초
   - B) 1~2분
   - C) 10~15분
   - D) KubernetesExecutor에는 콜드 스타트가 없음

<details>

<summary>정답 보기</summary>

**정답: B) 1~2분**

**설명:**
간단한 태스크라도 Pod 스케줄링, (캐시되지 않았다면) 이미지 풀, 그리고 여유 용량이 없을 경우 Karpenter나 Cluster Autoscaler를 통한 노드 스케일 아웃까지 거쳐야 하므로, 태스크가 실제로 실행되기까지 대략 1~2분이 소요됩니다.

</details>

6. `KubernetesExecutor`에는 필요 없지만 `CeleryExecutor`에는 추가로 필요한 인프라는 무엇인가요?
   - A) 전용 StorageClass
   - B) 메시지 브로커(Redis 또는 RabbitMQ)와 worker Deployment
   - C) 별도의 Kubernetes 클러스터
   - D) 서비스 메시

<details>

<summary>정답 보기</summary>

**정답: B) 메시지 브로커(Redis 또는 RabbitMQ)와 worker Deployment**

**설명:**
`CeleryExecutor`는 scheduler와 worker 사이에서 태스크를 큐잉할 브로커와, 그 브로커에서 작업을 계속 가져오는 상시 실행 worker Deployment가 필요합니다. `KubernetesExecutor`는 둘 다 필요 없습니다 — scheduler가 Kubernetes API와 직접 통신해 태스크마다 Pod를 생성하기 때문입니다.

</details>

7. KEDA `ScaledObject`의 쿼리(`SELECT ceil(COUNT(*)/worker_concurrency) FROM task_instance WHERE state IN (running, queued)`)는 Celery worker replica 수를 결정하기 위해 실제로 무엇을 측정하나요?
   - A) 지금까지 등록된 DAG의 총 개수
   - B) Pod당 설정된 동시성으로 현재 실행/대기 중인 모든 태스크 인스턴스를 처리하는 데 필요한 worker replica 수
   - C) scheduler Pod의 CPU 사용률
   - D) PostgreSQL 데이터베이스의 크기

<details>

<summary>정답 보기</summary>

**정답: B) Pod당 설정된 동시성으로 현재 실행/대기 중인 모든 태스크 인스턴스를 처리하는 데 필요한 worker replica 수**

**설명:**
이 쿼리는 현재 `running` 또는 `queued` 상태인 태스크 인스턴스 수를 세고, 이를 `worker_concurrency`로 나눈 뒤 올림 처리하여 해당 작업량을 감당하기 위해 필요한 worker Pod 수를 계산합니다. KEDA는 대략 10초마다 이 값을 폴링해 worker Deployment 크기를 조정합니다.

</details>

8. Celery worker의 태스크 처리 활동이 0이 된 뒤, KEDA가 worker Deployment를 0개 replica로 줄이기까지 대략 얼마나 기다리나요?
   - A) 즉시
   - B) 약 30초
   - C) 약 5분
   - D) 약 1시간

<details>

<summary>정답 보기</summary>

**정답: C) 약 5분**

**설명:**
KEDA는 마지막 태스크 활동 이후 대략 5분을 기다린 뒤에야 worker Deployment를 0으로 줄입니다. 이는 DAG 실행 사이의 짧은 공백 때문에 worker 풀이 내려갔다가 곧바로 다시 올라오는 상황을 막기 위한 것입니다.

</details>

9. Celery worker에 적용하는 것과 대응되는 "KubernetesExecutor용 KEDA" 오토스케일링 패턴이 존재하지 않는 이유는 무엇인가요?
   - A) KEDA는 Kubernetes 기반 Airflow 배포를 전혀 지원하지 않기 때문
   - B) KubernetesExecutor는 이미 태스크마다 Pod 1개를 생성하므로 크기를 조절할 고정 크기의 worker Deployment 자체가 없고, 실제로 스케일이 필요한 것은 Karpenter/Cluster Autoscaler가 담당하는 클러스터 컴퓨트 용량이기 때문
   - C) KubernetesExecutor 태스크는 어떤 상황에서도 스케일링할 수 없기 때문
   - D) KEDA는 Redis 기반 워크로드에만 호환되기 때문

<details>

<summary>정답 보기</summary>

**정답: B) KubernetesExecutor는 이미 태스크마다 Pod 1개를 생성하므로 크기를 조절할 고정 크기의 worker Deployment 자체가 없고, 실제로 스케일이 필요한 것은 Karpenter/Cluster Autoscaler가 담당하는 클러스터 컴퓨트 용량이기 때문**

**설명:**
KEDA의 역할은 외부 지표를 기준으로 장기 실행 중인 Deployment의 크기를 조절하는 것입니다. `KubernetesExecutor`에는 그런 Deployment가 처음부터 존재하지 않습니다 — 스케일링이 이미 태스크당 Pod 1개 단위로 세밀하게 이뤄지기 때문입니다. 따라서 실제로 신경 써야 할 스케일링 대상은 클러스터 수준의 컴퓨트 용량이며, 이는 워크로드 오토스케일러가 아니라 Karpenter나 Cluster Autoscaler의 역할입니다.

</details>

10. Airflow 3의 "여러 executor 동시 사용" 기능은 무엇을 할 수 있게 해주나요?
    - A) 두 개의 독립된 Airflow 설치를 나란히 실행
    - B) 배포 전체에 하나의 executor를 못 박는 대신, 태스크 또는 DAG 단위로 executor를 지정
    - C) 실행 시점에 더 저렴한 executor를 자동으로 선택
    - D) scheduler를 이중화된 두 인스턴스로 대체

<details>

<summary>정답 보기</summary>

**정답: B) 배포 전체에 하나의 executor를 못 박는 대신, 태스크 또는 DAG 단위로 executor를 지정**

**설명:**
이 기능을 이용하면 하나의 배포에서 여러 executor를 섞어 쓸 수 있습니다 — 예를 들어 대부분의 DAG는 지연이 낮은 warm `CeleryExecutor` 풀에서 실행하고, 리소스가 많이 필요하거나 GPU가 필요한 일부 태스크만 격리를 위해 명시적으로 `KubernetesExecutor`로 라우팅하는 방식입니다. 배포 전체를 놓고 하나만 골라야 하는 이분법에서 벗어나게 해줍니다.

</details>

## 단답형 문제

11. 공식 `apache/airflow` 차트와 자주 혼동되는, 더 오래된 독립 유지보수 커뮤니티 Helm 차트의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `airflow-helm/charts`**

**설명:**
공식 차트보다 먼저 존재했고 values 스키마도 다르며, Apache Airflow 프로젝트와는 관련이 없습니다. `apache/airflow`에는 적용되지 않는 values.yaml 스니펫이 돌아다니는 흔한 원인입니다.

</details>

12. Celery worker Deployment를 유휴 상태에서 완전히 0까지 줄일 수 있게 해주는 최소 `minReplicaCount` 값은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 0**

**설명:**
`workers.celery.keda.minReplicaCount: 0`으로 설정하면 태스크 활동이 대략 5분간 없을 때 ScaledObject가 worker Deployment를 0개 replica까지 줄일 수 있어, 유휴 worker 비용을 완전히 제거할 수 있습니다.

</details>

13. `KubernetesExecutor` 태스크 Pod를 위한 워크로드 단위 KEDA 스케일러가 없는 대신, 클러스터 수준에서 용량을 담당하는 두 가지 오토스케일러는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Karpenter와 Cluster Autoscaler**

**설명:**
`KubernetesExecutor`는 고정된 worker 풀을 유지하는 대신 태스크마다 Pod를 하나씩 생성하므로, 스케일링 문제는 결국 그 태스크 Pod들을 위한 충분한 노드를 프로비저닝하는 클러스터 컴퓨트 용량 문제로 넘어가며, 이는 Karpenter나 Cluster Autoscaler의 책임입니다.

</details>

14. KEDA `ScaledObject` 쿼리가 필요한 Celery worker replica 수를 계산할 때 집계하는 두 가지 `task_instance` 상태는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `running`과 `queued`**

**설명:**
이 쿼리는 `running` 또는 `queued` 상태인 태스크 인스턴스 수를 합산한 뒤 `worker_concurrency`로 나누어, 현재 수요를 감당하기 위해 필요한 worker Pod 수를 계산합니다.

</details>

15. `workers.celery.keda.enabled`가 의미를 가지려면 그 전에 최상위 `values.yaml` 필드 `executor`를 어떤 값으로 설정해야 하나요?

<details>

<summary>정답 보기</summary>

**정답: `CeleryExecutor`**

**설명:**
`workers.celery` 하위의 KEDA 오토스케일링 설정은 `executor: CeleryExecutor`가 설정되어 있을 때만 의미가 있습니다. `KubernetesExecutor` 배포에는 KEDA가 대상으로 삼을 Celery worker Deployment 자체가 렌더링되지 않습니다.

</details>

## 실습 문제

16. Apache Airflow 공식 Helm 저장소를 추가하고, 새 `airflow` 네임스페이스에 차트 버전 1.22.0을 설치하는 전체 명령어 시퀀스를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# Apache Airflow 공식 Helm 저장소 추가
helm repo add apache-airflow https://airflow.apache.org/
helm repo update

# 전용 네임스페이스에 특정 차트 버전으로 설치
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --create-namespace \
  --version 1.22.0

# 설치 확인
kubectl get pods -n airflow
helm list -n airflow
```

**설명:**
`helm repo add`는 공식 저장소를 등록합니다(`airflow-helm/charts`와 혼동하지 않도록 주의). `--create-namespace`를 사용하면 별도의 `kubectl create namespace` 단계가 필요 없습니다. `--version 1.22.0`으로 버전을 고정하면 설치 시점에 우연히 최신이던 버전이 아니라 재현 가능한 배포를 얻을 수 있습니다.

</details>

17. `KubernetesExecutor`를 선택하고 차트에 내장된 PostgreSQL을 비활성화(외부 RDS 인스턴스 사용 목적)하는 `values.yaml` 스니펫을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
executor: KubernetesExecutor

postgresql:
  enabled: false
```

**설명:**
`executor: KubernetesExecutor`로 설정하면 Celery worker Deployment나 Redis 브로커가 전혀 렌더링되지 않습니다. `postgresql.enabled: false`는 차트에 내장된 인클러스터 PostgreSQL Pod를 건너뛰어, `values.yaml`의 다른 연결 설정을 통해 외부 데이터베이스를 가리킬 수 있게 합니다.

</details>

18. `CeleryExecutor`를 선택하고, Celery worker에 대해 0개부터 최대 20개 replica까지 스케일하는 KEDA 오토스케일링을 활성화하는 `values.yaml` 스니펫을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
executor: CeleryExecutor

workers:
  celery:
    keda:
      enabled: true
      minReplicaCount: 0
      maxReplicaCount: 20
```

**설명:**
`executor: CeleryExecutor`는 worker Deployment와 Redis 브로커를 렌더링합니다. `workers.celery.keda.enabled: true`는 KEDA `ScaledObject`를 생성해 대략 10초마다 메타데이터 DB를 폴링하고, 실행/대기 중인 태스크 수를 기준으로 worker Deployment를 0~20개 replica 사이에서 조정하며, 활동이 대략 5분간 없으면 0으로 스케일합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/02-helm-deployment.md) | [이전 퀴즈: Airflow 아키텍처](./01-architecture-quiz.md)
