# Airflow 아키텍처 퀴즈

Airflow 3.3.1 / Helm chart 1.22.0 · September 2026.

## 1. Airflow 2의 DAG 파싱 구조에 대한 올바른 설명은?

- A) 모든 파일을 scheduler의 같은 loop에서만 파싱
- B) DAG를 Redis에서만 읽음
- C) 별도 file-processing subprocess와 선택적 standalone DAG processor가 이미 있었음
- D) 파싱 없이 task를 실행

<details>
<summary>정답 보기</summary>

**C**

Airflow 2의 scheduler는 manager를 시작할 수 있었고 파일별 subprocess를 사용했습니다. Standalone 설정도 가능했으며 serialized DAG와 multi-scheduler HA도 이미 존재했습니다.

</details>

## 2. Airflow 3 DAG processor의 역할은?

- A) 모든 operator를 실행
- B) UI 사용자에게 JWT만 발급
- C) Celery broker를 대체
- D) Bundle의 DAG를 파싱·직렬화하고 관련 metadata를 갱신

<details>
<summary>정답 보기</summary>

**D**

Airflow 3에서 필요한 별도 구성 역할입니다. 실행할 코드와 의존성은 worker에도 필요하므로 DAG 파일이 processor에만 있으면 된다는 뜻은 아닙니다.

</details>

## 3. DAG processor 분리로 보장되는 것은?

- A) 파싱과 스케줄링을 독립적으로 배포·조정하기 쉬워짐
- B) 모든 scheduling latency 제거
- C) DB 병목 제거
- D) Replica를 늘리면 무조건 HA 확보

<details>
<summary>정답 보기</summary>

**A**

새 DAG 파싱 지연, 공유 자원·DB 부하와 과도한 동시 처리 등은 여전히 영향을 줄 수 있습니다. 분리는 운영 검증을 대신하지 않습니다.

</details>

## 4. 일반 supervised Python Task SDK 실행에서 API 통신을 담당하는 것은?

- A) Task 코드가 metadata DB에 직접 SQL 실행
- B) Worker 쪽 supervisor가 task JWT로 Execution API 호출
- C) Redis만으로 모든 상태 교환
- D) Kubernetes API가 XCom 저장

<details>
<summary>정답 보기</summary>

**B**

Task runner와 supervisor는 socket으로 통신합니다. Worker→API server의 주소·인증·네트워크가 필요하며 Celery result backend 등 내부 요구는 별도로 확인합니다.

</details>

## 5. Triggerer에 관한 올바른 설명은?

- A) 모든 operator 전체를 실행
- B) 모든 최소 Airflow 배포에서 필수
- C) Deferred task의 trigger를 실행하고 task는 이후 worker에서 재개
- D) async task는 항상 worker slot을 반납

<details>
<summary>정답 보기</summary>

**C**

Deferral을 사용하지 않으면 triggerer를 생략할 수 있습니다. Deferred task는 worker slot을 놓고 pool slot은 기본 반납하지만 설정으로 달라질 수 있습니다.

</details>

## 6. Metadata DB와 Celery broker에 대한 설명은?

- A) PostgreSQL과 Redis가 모든 Airflow 구성에서 필수
- B) SQLite가 일반 production 권장 DB
- C) MariaDB와 MySQL은 지원상 동일
- D) PostgreSQL/MySQL 등을 지원하고 Celery broker는 Redis 외 대안도 있음

<details>
<summary>정답 보기</summary>

**D**

이 시리즈는 PostgreSQL을 예로 사용합니다. SQLite는 개발·시험용이고 MariaDB는 지원하지 않습니다. KubernetesExecutor에는 Celery broker가 필수가 아닙니다.

</details>

## 7. Airflow 3.0에서 지원이 중단된 hybrid 클래스는?

- A) LocalKubernetesExecutor와 CeleryKubernetesExecutor
- B) LocalExecutor와 CeleryExecutor
- C) KubernetesExecutor와 모든 broker
- D) DAG processor와 Triggerer

<details>
<summary>정답 보기</summary>

**A**

고정된 두 방식 조합을 구현하던 hybrid 클래스와 여러 executor 동시 설정 기능은 다릅니다. 호환 executor를 명시적으로 구성해 task별로 선택합니다.

</details>

## 8. 여러 executor 동시 설정과 DAG 기본값은?

- A) 3.3에서 처음 도입; 임의의 미설치 executor도 실행
- B) 2.10.0부터 지원; DAG default_args의 executor와 task override 사용
- C) 항상 하나만 허용
- D) 모든 선택을 Redis queue 이름으로만 지정

<details>
<summary>정답 보기</summary>

**B**

첫 configured executor가 기본값이고, task가 설정된 이름/alias를 선택합니다. DAG의 default_args로 task 기본값을 줄 수 있습니다.

</details>

## 9. DAG bundle와 git-sync의 관계는?

- A) Airflow 3에서 git-sync가 제거됨
- B) 모든 S3DagBundle은 S3 versioning만 켜면 버전 고정
- C) git-sync도 계속 지원되며 bundle별 버전 고정 능력은 다름
- D) Worker는 DAG 코드가 불필요

<details>
<summary>정답 보기</summary>

**C**

GitDagBundle은 버전 고정을 지원하지만 검토한 Local/S3/GCS bundle은 지원하지 않습니다. 실제 코드 전달과 retry 시 읽는 버전을 확인합니다.

</details>

[Guide](../../../data-on-eks/airflow/01-architecture.md)
