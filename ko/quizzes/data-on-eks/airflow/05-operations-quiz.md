# Part 5: 운영과 보안 퀴즈

Airflow 3.3.1의 운영·복구 경계를 확인합니다.

1. Airflow 3의 dag-processor 분리로 scheduler DB 경합이 모두 없어졌나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Airflow 2도 HA를 지원했으며, 3에서도 DB row lock·연결 한도·실행 용량을 검증해야 합니다.

**설명:** replicas=2는 배치 분산·DB failover·전체 서비스 HA를 자동으로 완성하지 않습니다.

</details>

2. Migration 전에 scheduler·processor·triggerer만 멈추면 모든 DB writer가 멈추나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Worker/task, API server와 외부 자동화도 포함해 유입·drain·쓰기 경로를 조정해야 합니다.

**설명:** DB 복원과 Fernet/외부 데이터 복구를 시험하고, 하나의 migration 경로와 검증된 rollback을 사용합니다.

</details>

3. Secrets Manager prefix는 모든 Airflow 컴포넌트에서 반드시 같아야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Worker 전용 backend와 Execution API 조회 경로를 의도적으로 사용할 수 있습니다.

**설명:** 설정 복제 여부보다 실제 조회 순서·권한·fallback·cache를 검증합니다. 예외가 기록되는 경로도 있어 모든 실패가 silent인 것은 아닙니다.

</details>

4. S3 remote_logging=True이면 모든 component 로그가 매 줄 즉시 업로드되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Task log 경로이며, 검토한 supervisor는 task 종료 후 업로드합니다.

**설명:** 서비스 stdout/stderr는 별도 수집이 필요할 수 있습니다. 강제 종료가 업로드보다 빠르면 최근 로그가 손실될 수 있습니다.

</details>

5. Fernet 설정된 metastore의 Connection/Variable은 모두 평문인가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Password/extra와 Variable 값은 암호화되지만 모든 metadata나 로그가 암호화되는 것은 아닙니다.

**설명:** Fernet key 보존·rotation이 필요합니다. 외부 backend는 가능한 선택이며 production에서 AWS Secrets Manager만 강제되는 것은 아닙니다.

</details>

6. Celery KEDA query에서 queued/running 합계만 세면 충분한가요?

<details>
<summary>정답 보기</summary>

**정답:** Queue·executor·alias·worker concurrency·replica 한도를 함께 반영해야 합니다.

**설명:** Worker는 Deployment 또는 StatefulSet일 수 있고 scale-to-zero는 실제 구성에 달려 있습니다.

</details>

7. KubernetesExecutor에 Celery worker-pool 스케일링을 그대로 적용하지 않는 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** Task Pod를 직접 생성하므로 같은 고정 worker pool이 없기 때문입니다.

**설명:** KEDA가 Deployment만 지원한다는 뜻은 아닙니다. Node autoscaler의 용량·quota·disruption 제약은 별도로 검증합니다.

</details>

8. Shared Celery worker의 IAM role을 지정하면 각 task의 AWS 권한이 자동 분리되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 그 worker의 여러 task가 같은 실행 권한을 공유할 수 있습니다.

**설명:** 분리가 필요하면 별도 worker pool·executor·KPO child 등 실제 경계를 설계하고 credential source를 확인합니다.

</details>

9. db clean 자동화에서 preview와 실패 감지는 어떻게 구성하나요?

<details>
<summary>정답 보기</summary>

**정답:** 검토한 cutoff/table에 --dry-run을 먼저 사용하고 --error-on-cleanup-failure와 로그를 확인합니다.

**설명:** 실제 삭제는 별도 실행합니다. 기본 archive도 DB 공간을 쓰고 cascade가 있으므로 cleanup이 항상 디스크를 줄이거나 모든 migration을 빠르게 하지는 않습니다.

</details>

10. NetworkPolicy와 OTLP endpoint만 설정하면 보안·관측 경로가 완성되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. CNI enforcement·실제 허용 경로·인증과 Collector receiver/exporter·저장소·알람까지 검증해야 합니다.

**설명:** NetworkPolicy는 IAM/RBAC/TLS를 대체하지 않습니다. Prometheus가 OTLP/HTTP endpoint를 그대로 scrape하는 것도 아닙니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/airflow/05-operations.md) | [Airflow](../../../data-on-eks/airflow/README.md)
