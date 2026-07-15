# Part 5: 운영과 보안 퀴즈

이 퀴즈는 스케줄러 HA, 데이터베이스 업그레이드, 시크릿 백엔드 일관성, 리모트 로깅, 모니터링, 오토스케일링, 보안 체크리스트 등 Airflow 딥다이브 시리즈 전체를 아우르는 운영 이해도를 테스트합니다.

## 객관식 문제

1. Airflow 3에서 스케줄러 레플리카를 여러 개 운영하는 것이 Airflow 2보다 더 안전한 이유는 무엇인가요?
   - A) Airflow 3의 스케줄러는 더 이상 Postgres가 필요 없다
   - B) DAG 파싱이 별도의 필수 서비스인 `dag-processor`로 옮겨져, 스케줄러들이 같은 DAG 묶음을 파싱하려고 서로 경쟁할 필요가 없어졌다
   - C) Airflow 3의 스케줄러는 데이터베이스 대신 자체 리더 선출 프로토콜을 사용한다
   - D) Airflow 3에서는 메타데이터 데이터베이스가 완전히 제거되었다

<details>

<summary>정답 보기</summary>

**정답: B) DAG 파싱이 별도의 필수 서비스인 `dag-processor`로 옮겨져, 스케줄러들이 같은 DAG 묶음을 파싱하려고 서로 경쟁할 필요가 없어졌다**

**설명:**
Airflow 2에서는 스케줄러가 작업 스케줄링과 DAG 파일 파싱을 동시에 담당했기 때문에, 여러 스케줄러 레플리카가 동시에 같은 DAG를 파싱하면 경쟁 상태와 중복 작업이 발생했습니다. Airflow 3는 파싱을 전담하는 별도의 필수 서비스 `dag-processor`를 도입했고, 스케줄러는 오직 `serialized_dag` 테이블을 읽어 준비된 작업 인스턴스를 큐에 넣는 역할만 합니다. 따라서 스케줄러 레플리카를 늘리는 것은 새로운 경쟁을 유발하지 않는 단순한 확장·HA 수단이 됩니다. 중복 큐잉을 막는 것은 별도의 리더 선출 메커니즘이 아니라 Postgres의 행 단위 잠금입니다.
</details>

2. 메타데이터 데이터베이스 스키마 변경을 포함하는 Airflow 메이저 버전 업그레이드 전에 해야 할 일은 무엇인가요?
   - A) 마이그레이션을 깨끗하게 시작하기 위해 `serialized_dag` 테이블을 삭제한다
   - B) 메타데이터 데이터베이스를 백업하고, 오래된 DAG 실행/작업 인스턴스 이력을 먼저 정리하는 것을 고려한다
   - C) dag-processor를 영구적으로 비활성화한다
   - D) 아무것도 할 필요 없다 — Airflow 마이그레이션은 항상 하위 호환되고 되돌릴 수 있다

<details>

<summary>정답 보기</summary>

**정답: B) 메타데이터 데이터베이스를 백업하고, 오래된 DAG 실행/작업 인스턴스 이력을 먼저 정리하는 것을 고려한다**

**설명:**
메타데이터 데이터베이스에는 모든 DAG 실행, 작업 인스턴스, 커넥션, 변수, XCom이 저장되어 있으므로 메이저 업그레이드 전에는 반드시 백업(핫 또는 콜드)을 받아야 합니다. Airflow 3의 마이그레이션에는 대규모 데이터베이스에서 느릴 수 있는 스키마 변경이 포함되므로, `airflow db clean` 등으로 오래된 이력을 먼저 정리하면 마이그레이션이 처리해야 할 행 수를 줄일 수 있습니다.
</details>

3. Secrets Manager 백엔드 설정이 api-server, scheduler, worker 전체에서 반드시 동일해야 하는 이유는 무엇인가요?
   - A) 사실 그렇지 않다 — scheduler에만 설정하면 된다
   - B) 각 컴포넌트가 런타임에 독립적으로 커넥션/변수를 조회하며, 설정이 어긋나면 해당 컴포넌트만 조용히 메타데이터 데이터베이스로 폴백한다
   - C) Helm 차트가 모든 Pod에 `airflow.cfg`를 자동으로 동기화한다
   - D) Secrets Manager는 한 번에 하나의 클라이언트만 특정 시크릿을 읽을 수 있다

<details>

<summary>정답 보기</summary>

**정답: B) 각 컴포넌트가 런타임에 독립적으로 커넥션/변수를 조회하며, 설정이 어긋나면 해당 컴포넌트만 조용히 메타데이터 데이터베이스로 폴백한다**

**설명:**
한 컴포넌트의 `[secrets]` 설정이 다른 컴포넌트를 대신 커버해주는 공유 캐시나 단일 지점은 존재하지 않습니다. `backend_kwargs`(prefix)가 컴포넌트마다 어긋나거나 `[secrets]` 섹션이 누락되면 그 컴포넌트는 Secrets Manager 대신 조용히 메타데이터 데이터베이스로 폴백하게 되고, 그 결과 커넥션 조회가 컴포넌트별로 제각각 실패합니다 — 예를 들어 스케줄러에서는 되는데 워커 Pod에서는 안 되는 식입니다.
</details>

4. 리모트 로깅이 특히 `KubernetesExecutor` 배포에서 중요한 이유는 무엇인가요?
   - A) `KubernetesExecutor`는 StatsD 메트릭을 지원하지 않는다
   - B) 작업 Pod가 일시적이며 작업이 끝나면 정리되므로, 리모트 로깅이 없으면 Pod가 가비지 컬렉션되는 순간 로그도 함께 사라진다
   - C) `KubernetesExecutor`는 로그를 저장하기 위해 Celery 브로커가 필요하다
   - D) 리모트 로깅이 없으면 `KubernetesExecutor` 자체가 동작하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) 작업 Pod가 일시적이며 작업이 끝나면 정리되므로, 리모트 로깅이 없으면 Pod가 가비지 컬렉션되는 순간 로그도 함께 사라진다**

**설명:**
`KubernetesExecutor`에서는 작업마다 전용 Pod가 생성되고 작업이 끝나면 정리됩니다. 로그를 S3 등 내구성 있는 저장소로 전송해두지 않으면 Pod가 가비지 컬렉션되는 순간 로그가 함께 사라져, 실패한 실행을 사후에 디버깅하는 것이 불가능해집니다.
</details>

5. AWS Secrets Manager 기반의 Airflow 시크릿 백엔드를 구현하는 클래스는 무엇인가요?
   - A) `airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend`
   - B) `airflow.secrets.aws.AWSSecretsClient`
   - C) `airflow.providers.aws.secrets_backend.SecretsManagerConnection`
   - D) `airflow.utils.secrets.SecretsManagerHook`

<details>

<summary>정답 보기</summary>

**정답: A) `airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend`**

**설명:**
이 클래스는 `airflow.cfg`의 `[secrets] backend = ...`에 지정하며, `connections_prefix`, `variables_prefix`, `config_prefix`를 지정하는 `backend_kwargs`와 함께 설정합니다. 커넥션이나 변수를 조회하는 모든 컴포넌트에서 동일하게 설정되어 있어야 합니다.
</details>

6. `CeleryExecutor`에서 KEDA는 무엇을 기준으로 스케일하나요? (Part 2 참고)
   - A) 워커 Pod의 CPU/메모리 사용률
   - B) 메타데이터 데이터베이스에서 읽은 큐에 쌓인/실행 중인 작업 인스턴스 수
   - C) dags 폴더에 있는 DAG 파일 수
   - D) Redis 브로커의 네트워크 처리량

<details>

<summary>정답 보기</summary>

**정답: B) 메타데이터 데이터베이스에서 읽은 큐에 쌓인/실행 중인 작업 인스턴스 수**

**설명:**
KEDA는 메타데이터 데이터베이스를 폴링해 실행 중/큐에 쌓인 작업 인스턴스 수를 읽고, 이에 맞춰 Celery 워커 `Deployment`를 스케일합니다(유휴 시 0까지 축소 포함). CPU/메모리 기반 HPA는 실제 큐 깊이를 이만큼 정확하게 반영하지 못합니다.
</details>

7. `KubernetesExecutor`에는 왜 KEDA 기반 오토스케일링 패턴이 없나요?
   - A) KEDA가 Kubernetes 네이티브 워크로드를 지원하지 않기 때문이다
   - B) `KubernetesExecutor`는 이미 작업마다 Pod를 하나씩 생성하므로 크기를 조정할 고정된 워커 풀 자체가 없고, 대신 클러스터 수준 오토스케일링이 용량을 담당한다
   - C) `KubernetesExecutor`는 오토스케일링을 전혀 지원하지 않는다
   - D) KEDA는 Redis 기반 브로커에서만 동작한다

<details>

<summary>정답 보기</summary>

**정답: B) `KubernetesExecutor`는 이미 작업마다 Pod를 하나씩 생성하므로 크기를 조정할 고정된 워커 풀 자체가 없고, 대신 클러스터 수준 오토스케일링이 용량을 담당한다**

**설명:**
KEDA의 역할은 외부 메트릭을 기준으로 장시간 실행되는 Deployment의 크기를 조정하는 것입니다. `KubernetesExecutor`는 그런 Deployment를 가지고 있지 않습니다 — 작업 Pod가 각자 독립적으로 생성·소멸되기 때문입니다. 여기서 실제로 스케일해야 하는 대상은 그 Pod들을 위한 클러스터 용량이며, 이는 Karpenter나 Cluster Autoscaler의 역할입니다.
</details>

8. 보안 체크리스트에서, 각 작업의 IRSA 롤을 여러 DAG가 공유하는 넓은 권한 대신 좁게 스코핑해야 하는 이유는 무엇인가요?
   - A) IRSA 롤은 정책을 하나만 가질 수 있다는 제약이 있다
   - B) 공유되는 넓은 권한의 롤은 결국 모든 작업이 필요로 할 수 있는 권한의 합집합을 모든 작업에게 부여하게 되어 최소 권한 원칙을 무력화한다
   - C) 좁은 권한의 롤은 Kubernetes API 서버가 강제하는 요구사항이다
   - D) IRSA는 여러 Pod에서 같은 롤을 재사용하는 것을 지원하지 않는다

<details>

<summary>정답 보기</summary>

**정답: B) 공유되는 넓은 권한의 롤은 결국 모든 작업이 필요로 할 수 있는 권한의 합집합을 모든 작업에게 부여하게 되어 최소 권한 원칙을 무력화한다**

**설명:**
각 작업 Pod(또는 Celery 워커)는 IRSA를 통해 그 작업에 실제로 필요한 AWS 액션만 허용된 롤을 assume해야 합니다. 관련 없는 여러 DAG가 하나의 공유 롤을 재사용하면, 사실상 모든 작업이 다른 모든 작업의 권한을 합친 만큼의 권한을 갖게 되는데, 이는 최소 권한 스코핑이 막고자 하는 상황 그 자체입니다.
</details>

## 단답형 문제

9. 리모트 로깅 커넥션에 대한 Secrets Manager 백엔드 설정이 컴포넌트 간에 어긋났을 때, 로그를 정상적으로 남기지 못하게 되는 컴포넌트를(메타데이터 데이터베이스 제외) 두 가지만 드세요.

<details>

<summary>정답 보기</summary>

**정답: api-server, scheduler, dag-processor, triggerer, (`KubernetesExecutor`의) 작업 Pod, Celery 워커 중 임의의 두 가지**

**설명:**
로그를 남기는 모든 컴포넌트는 런타임에 각자 독립적으로 리모트 로깅 커넥션을 조회합니다. 한 컴포넌트의 시크릿 백엔드 설정이 다른 컴포넌트와 어긋나면 그 컴포넌트는 조용히 메타데이터 데이터베이스로 폴백하거나(혹은 커넥션 조회 자체에 실패하고), 그 컴포넌트의 로그만 리모트 대상으로 전송되지 않게 되며, 나머지 컴포넌트의 로그는 정상 동작을 계속합니다.
</details>

10. 보안 체크리스트에서 Pod 간 트래픽을 제한하는 항목은 무엇이며, 기본적으로 어떤 방향으로 설정해야 하나요?

<details>

<summary>정답 보기</summary>

**정답: 네트워크 정책(NetworkPolicy) — scheduler/api-server/dag-processor/worker의 트래픽을 실제로 필요한 대상으로만 제한. 기본은 거부(deny-by-default)로 설정하고, 컴포넌트별로 명시적인 허용 규칙을 추가한다.**

**설명:**
Airflow 네임스페이스에 기본 거부 `NetworkPolicy`를 적용하고, 각 컴포넌트가 실제로 필요로 하는 대상(메타데이터 데이터베이스, 시크릿 백엔드의 VPC 엔드포인트, 리모트 로깅 대상, `CeleryExecutor`의 경우 브로커)에 대해서만 명시적으로 허용 규칙을 추가하면, 관련 없는 Pod가 침해되더라도 Airflow 컨트롤 플레인으로의 수평 이동을 막을 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/05-operations.md) | [Airflow 딥다이브 홈으로](../../../data-on-eks/airflow/README.md)
