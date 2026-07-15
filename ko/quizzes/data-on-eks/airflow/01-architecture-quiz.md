# Kubernetes에서의 Airflow 아키텍처 퀴즈

이 퀴즈는 Airflow 3의 서비스 분리 구조, DAG 파싱이 스케줄러에서 분리된 이유, dag-processor의 역할, Airflow 2 하이브리드 Executor가 제거된 이유에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Airflow 2에서 스케줄러 프로세스는 작업 인스턴스 스케줄링 외에 어떤 역할을 함께 담당했나요?
   - A) 웹 UI 제공
   - B) 메모리 상의 DAG 표현을 최신 상태로 유지하기 위한 DAG 파일 파싱
   - C) 지연 가능한(deferrable) 오퍼레이터 실행
   - D) Celery 워커 풀 관리

<details>

<summary>정답 보기</summary>

**정답: B) 메모리 상의 DAG 표현을 최신 상태로 유지하기 위한 DAG 파일 파싱**

**설명:**
Airflow 2에서는 스케줄러가 작업 인스턴스를 스케줄링하는 것과 동시에 DAG 파일을 직접 파싱했습니다. DAG 수가 많거나, DAG 중첩이 깊거나, DAG 파일의 최상위 코드가 무거운 환경에서는 이 파싱 작업이 스케줄러의 본연의 스케줄링 루프를 잠식할 수 있었고, 이는 "준비된 작업을 제때 큐에 올린다"는 핵심 신뢰성 지표에 직접적인 악영향을 끼쳤습니다. UI 제공은 스케줄러가 아니라 웹서버의 역할이었습니다.
</details>

2. Airflow 3의 `airflow dag-processor` 서비스가 담당하는 주된 역할은 무엇인가요?
   - A) REST API 제공과 인증 처리
   - B) Celery 워커 Pod 실행
   - C) DAG 파일을 파싱하고 그 결과를 `serialized_dag` 테이블에 기록
   - D) 클러스터 메타데이터를 위한 액티브 컨트롤러 선출

<details>

<summary>정답 보기</summary>

**정답: C) DAG 파일을 파싱하고 그 결과를 `serialized_dag` 테이블에 기록**

**설명:**
dag-processor의 유일한 역할은 DAG 파일을 파싱하고 파싱된 구조를 메타데이터 DB의 `serialized_dag` 테이블에 저장하는 것입니다. 스케줄러는 파일을 다시 파싱하는 대신 이 테이블에서 DAG 구조를 읽어오며, 이것이 DAG 파싱과 스케줄링을 서로 독립적으로 확장할 수 있게 하는 핵심 메커니즘입니다.
</details>

3. Airflow 3가 dag-processor를 Airflow 2에서처럼 선택적(옵트인) 프로세스가 아니라 필수 서비스로 만든 이유는 무엇인가요?
   - A) 필요한 Kubernetes Pod의 총 개수를 줄이기 위해
   - B) DAG 파싱을 스케줄러의 루프에서 완전히 분리해 더 이상 스케줄링 지연을 유발하지 못하게 하기 위해
   - C) 메타데이터 데이터베이스가 필요 없도록 하기 위해
   - D) DAG를 Python 외의 언어로 작성할 수 있게 하기 위해

<details>

<summary>정답 보기</summary>

**정답: B) DAG 파싱을 스케줄러의 루프에서 완전히 분리해 더 이상 스케줄링 지연을 유발하지 못하게 하기 위해**

**설명:**
dag-processor를 필수로 만들면 배포 설정과 무관하게 DAG 파싱이 항상 스케줄러 프로세스 밖에서 이루어지도록 보장할 수 있습니다. 이것이 Airflow 3의 대표적인 고가용성(HA) 개선점입니다 — DAG 수의 급증이나 느린 DAG 파일 하나가 더 이상 배포 전체 다른 DAG들의 작업 큐잉 능력을 잠식할 수 없습니다.
</details>

4. Airflow 3의 아키텍처 분리 이후, 스케줄러는 DAG 구조를 알기 위해 메타데이터 데이터베이스의 어디를 읽나요?
   - A) 매 스케줄링 루프마다 파싱되는 원본 `.py` DAG 파일
   - B) dag-processor가 채워 넣는 `serialized_dag` 테이블
   - C) Redis에 캐시된 DAG 사본
   - D) Celery 브로커의 작업 큐

<details>

<summary>정답 보기</summary>

**정답: B) dag-processor가 채워 넣는 `serialized_dag` 테이블**

**설명:**
Airflow 3에서는 스케줄러가 더 이상 DAG 파일을 전혀 파싱하지 않습니다. 대신 dag-processor가 최신 상태로 유지하는 Postgres의 `serialized_dag` 테이블에서 이미 파싱되고 직렬화된 DAG 구조를 읽어옵니다. 이 구조가 스케줄링 처리량과 DAG 파싱 비용을 서로 분리시키는 메커니즘입니다.
</details>

5. Airflow 2의 Flask 기반 `webserver`를 대체한 Airflow 3의 서비스는 무엇인가요?
   - A) `airflow scheduler`
   - B) `airflow dag-processor`
   - C) `airflow api-server`
   - D) `airflow triggerer`

<details>

<summary>정답 보기</summary>

**정답: C) `airflow api-server`**

**설명:**
`airflow api-server`는 UI, REST API v2 제공과 인증을 담당하는 새로운 FastAPI 기반 서비스로, Airflow 2에서 이 역할들을 담당했던 Flask 기반 웹서버를 대체합니다.
</details>

6. `airflow triggerer` 서비스의 역할은 무엇인가요?
   - A) 일정 주기로 DAG 파일을 파싱한다
   - B) 지연 가능한(deferrable) 오퍼레이터를 실행하며, 외부 이벤트가 발생하면 작업을 비동기적으로 재개한다
   - C) Airflow REST API를 제공한다
   - D) 어떤 스케줄러 레플리카가 활성 상태인지 선출한다

<details>

<summary>정답 보기</summary>

**정답: B) 지연 가능한(deferrable) 오퍼레이터를 실행하며, 외부 이벤트가 발생하면 작업을 비동기적으로 재개한다**

**설명:**
triggerer의 역할은 Airflow 2와 동일합니다 — 외부 이벤트(API 응답, 파일 도착, 다른 작업의 완료 등)를 기다리는 동안 워커를 계속 점유하는 대신 워커 슬롯을 반납하고, 이벤트가 발생하면 비동기적으로 작업을 재개하는 지연 가능한 오퍼레이터를 실행합니다.
</details>

7. Airflow 3.0에서 제거된 두 가지 Executor는 무엇인가요?
   - A) `KubernetesExecutor`와 `CeleryExecutor`
   - B) `LocalExecutor`와 `SequentialExecutor`
   - C) `CeleryKubernetesExecutor`와 `LocalKubernetesExecutor`
   - D) `DebugExecutor`와 `DaskExecutor`

<details>

<summary>정답 보기</summary>

**정답: C) `CeleryKubernetesExecutor`와 `LocalKubernetesExecutor`**

**설명:**
Airflow 3.0에서는 두 하이브리드 Executor 클래스인 `CeleryKubernetesExecutor`와 `LocalKubernetesExecutor`가 모두 제거되었습니다. 이들은 Airflow 2에서 작업 단위 큐 이름에 따라 일부 작업을 Celery 워커로, 일부를 Kubernetes Pod로 라우팅하기 위해 존재했습니다.
</details>

8. Airflow 3에서 하이브리드 Executor를 대체한 것은 무엇인가요?
   - A) 모든 조합을 포괄하는 단일 신규 `HybridExecutor` 클래스
   - B) 여러 Executor를 동시에 설정하고 작업 또는 DAG 단위로 하나씩 지정할 수 있는 기능
   - C) `CeleryExecutor` 사용 옵션 자체를 제거
   - D) 모든 작업이 `KubernetesExecutor`로만 실행되도록 강제

<details>

<summary>정답 보기</summary>

**정답: B) 여러 Executor를 동시에 설정하고 작업 또는 DAG 단위로 하나씩 지정할 수 있는 기능**

**설명:**
Celery와 Kubernetes 사이의 특정한 하나의 이원 분할을 하드코딩하는 대신, Airflow 3는 배포가 여러 Executor를 동시에 설정하고 특정 작업이나 DAG 전체에 명시적으로 Executor를 지정할 수 있게 합니다(예: DAG의 나머지는 배포 기본 Executor를 쓰되 작업 하나만 `KubernetesExecutor`를 사용). 이는 하이브리드 Executor의 개념을 일반화한 것으로, 조합마다 전용 클래스를 만들 필요가 없습니다.
</details>

9. 기본 Airflow 3 배포에는 필요 없고 `CeleryExecutor`를 사용할 때만 필요한 백엔드 서비스는 무엇인가요?
   - A) PostgreSQL
   - B) Redis
   - C) dag-processor
   - D) api-server

<details>

<summary>정답 보기</summary>

**정답: B) Redis**

**설명:**
PostgreSQL은 메타데이터 데이터베이스로 항상 필요하며, dag-processor와 api-server는 모든 Airflow 3 배포에서 핵심 서비스입니다. Redis(또는 RabbitMQ)는 `CeleryExecutor`를 사용할 때 Celery 작업 브로커를 뒷받침하기 위해서만 필요하며, `KubernetesExecutor`만 사용하는 배포에서는 필요하지 않습니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/01-architecture.md)
