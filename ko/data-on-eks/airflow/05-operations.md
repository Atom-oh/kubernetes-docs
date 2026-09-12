# Part 5: 운영과 보안

> 검토 기준: Airflow 3.3.1, Helm chart 1.22.0, Amazon provider 9.34.0 / Kubernetes provider 10.21.0.

Part 2의 자체 EKS 배포를 기준으로 HA·업그레이드·시크릿·로그·관측·복구를 정리합니다.
운영 기준은 설정 존재 여부보다 **장애 후 실행과 데이터·로그를 복구할 수 있는지**입니다.
MWAA의 환경 업그레이드와 CloudWatch 관리 절차는 Part 4의 서비스 경로를 사용합니다.

## 1. Scheduler HA는 데이터베이스와 함께 검증

Airflow 2도 scheduler HA와 별도 DAG processor 구성을 지원했습니다.
Airflow 3의 필수 dag-processor 분리는 자원·역할 경계를 명확히 하지만, 모든
DB 경합을 없애거나 scheduler 수에 비례한 성능 향상을 보장하지 않습니다.
Scheduler는 직렬화된 DAG를 활용하고 DB row lock으로 scheduling 임계 구역을 조정합니다.
별도 scheduler leader-election 서비스를 추가할 필요는 없습니다.

```yaml
scheduler:
  replicas: 2
```

이 값은 replica 수만 바꿉니다. 서로 다른 node/AZ 배치, DB failover와 연결 한도,
API server·processor 가용성, probe/PDB, executor와 broker 상태를 함께 검증합니다.
Node/AZ 장애와 DB failover 때 scheduling 지연·재시도·중복 외부 쓰기를 측정합니다.
HA용 SQL 기능 설명을 전체 DB 지원 표로 해석하지 말고 Part 1의 지원 버전을 따릅니다.
Triggerer는 deferrable task 등 trigger를 사용하는 경우에 필요합니다.

## 2. 백업·복원·마이그레이션

메타데이터 DB에는 실행 상태와 여러 Airflow 설정이 저장됩니다. 외부 secrets나
object-storage XCom backend를 쓰면 모든 값이 DB 안에 있는 것은 아닙니다.
DB 백업 외에도 Fernet key, DAG/bundle 이력, image·provider 버전, 외부 데이터·로그와
시크릿 보존을 관리합니다. 복호화 key가 없으면 DB만 복원해도 충분하지 않습니다.

스키마 migration 전에는 다음 순서를 환경별 runbook으로 검증합니다.

1. 지원 upgrade 경로와 breaking change를 확인하고 실제 DB 크기의 복제본에서
   migration 시간·lock·디스크 여유와 DAG/provider 호환성을 측정합니다.
2. Hot backup은 해당 DB가 제공하는 일관성 보장을 사용하고 복원까지 시험합니다.
   Snapshot 생성 요청 성공만으로 snapshot 완료나 복원 가능성을 판정하지 않습니다.
3. 새 DAG 실행 유입을 제어하고 진행 중 작업을 drain하거나 계획에 따라 종료합니다.
   Migration 중에는 worker/task·API server와 외부 자동화까지 포함한 모든 관련
   DB writer를 조정합니다. Scheduler·processor·triggerer만 중단해도 쓰기가
   모두 멈춘다는 가정은 틀립니다.
4. 백업과 복구 지점을 확정한 후 하나의 migration 경로만 실행합니다.
   Helm migration Job/hook과 수동 airflow db migrate가 경쟁하지 않게 합니다.
5. DB 상태, 새 실행·재시도·로그·secret lookup을 검증한 뒤 유입을 재개합니다.
   Schema가 바뀐 DB에 이전 image만 재배포하는 것을 rollback 계획으로 삼지 않습니다.

### 이력 정리는 보존 정책에 따라

모든 upgrade 전에 일정 기간의 이력을 무조건 삭제하지 않습니다. 먼저 필요한
감사·재실행·depends_on_past 요구와 foreign-key cascade를 확인합니다.
아래는 **삭제하지 않는 preview**입니다.

```bash
# Preview only: replace the cutoff and table selection with your retention policy.
airflow db clean \
  --clean-before-timestamp '2026-07-01T00:00:00+00:00' \
  --tables dag_run,task_instance \
  --dry-run \
  --error-on-cleanup-failure
```

실제 실행은 검토한 cutoff/table과 백업을 확인한 뒤 별도로 진행합니다.
기본 archive table도 같은 DB 공간을 사용하므로 clean이 디스크를 즉시 줄이거나
모든 migration을 빠르게 만든다는 보장은 없습니다.
3.3.1에서는 일부 cleanup 실패가 기본적으로 exit 0에 가려질 수 있어 자동화 시
--error-on-cleanup-failure와 결과 로그를 함께 확인합니다.

## 3. Fernet과 secrets 조회 경로

“커넥션과 변수가 기본적으로 전부 평문”이라는 설명은 틀립니다. Fernet 설정 시
connection의 password/extra와 Variable 값이 암호화됩니다. 모든 메타데이터 필드나
로그까지 암호화하는 기능은 아니며 key 보존·rotation·접근 제어가 필요합니다.
AWS Secrets Manager는 사용할 수 있는 외부 backend 중 하나입니다.

```ini
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "config_prefix": "airflow/config"}
```

일반 server 조회는 custom backend → 환경 변수 → metastore 순서입니다.
외부 backend 값은 Airflow UI에 모두 나열되지 않으며, 같은 key를 UI에서 수정해도
우선순위가 높은 외부 값이 계속 읽힐 수 있습니다.

Airflow 3은 [workers] secrets_backend / secrets_backend_kwargs로 worker 전용
backend를 구성할 수 있습니다. Task SDK의 일반 task context는 supervisor와
Execution API를 거쳐 server-side 값을 조회하는 경로도 사용합니다.
따라서 모든 컴포넌트가 반드시 같은 prefix·직접 DB 접근 권한을 가져야 하는 것은 아닙니다.

의도한 경로를 문서화하고 API 측 조회, worker override, logging supervisor의
조회/캐시를 각각 확인합니다. 검토한 구현은 backend 예외를 기록하고 다음 경로를
시도하므로 모든 실패가 조용히 사라지는 것도 아닙니다. 잘못된 prefix가 다른 값으로
fallback하는 경우와 명시적인 조회 실패를 둘 다 시험합니다.
Secret 값 자체를 진단 로그에 출력하지 않습니다.

## 4. S3 task 로그는 모든 로그의 즉시 streaming이 아님

```ini
[logging]
remote_logging = True
remote_base_log_folder = s3://my-airflow-logs-bucket/logs
remote_log_conn_id = airflow_remote_logging_conn
delete_local_logs = False
```

Secret 이름은 airflow/connections/airflow_remote_logging_conn이며 값의 예는 다음과 같습니다.

```json
{"conn_type": "aws", "extra": {"region_name": "us-east-1"}}
```

Connection에는 정적 key를 넣지 않았습니다. 실제 S3 reader/writer의 IRSA 또는
Pod Identity와 SDK credential chain, bucket prefix·KMS 권한·네트워크를 구성합니다.
Connection 정보를 API로 전달받았다고 API server의 AWS credentials까지 전달되는
것은 아닙니다. API/UI 로그 읽기와 task/supervisor 로그 쓰기 양쪽을 확인합니다.

검토한 3.3.1 supervisor는 task subprocess가 끝난 뒤 remote upload를 수행하며,
Amazon provider의 S3 handler도 close/upload 경로로 blob을 저장합니다.
S3에 각 로그 줄이 즉시 도착한다는 보장은 없습니다. 정상 종료, task 실패,
worker 강제 종료와 Pod 삭제 뒤 UI 로그 조회를 각각 시험합니다.
SIGKILL·노드 장애가 최종 업로드보다 먼저 발생하면 최근 로그가 손실될 수 있습니다.

S3 remote_logging은 **Airflow task log 경로**입니다. Scheduler/API/processor의
일반 서비스 로그가 전부 자동으로 같은 S3 경로에 저장되지는 않습니다.
Fluent Bit 등 별도 stdout/stderr 수집은 이를 보완하지만, task 로그가 파일에만
쓰이면 container stdout 수집만으로 그 파일이 수집되지는 않습니다.
Pod 삭제 후에도 PVC나 별도 수집본이 남을 수 있으므로 “원격 설정 없으면 항상
사후 분석 불가” 대신 실제 저장 경로와 보존·손실 범위를 확인합니다.

KPO에서는 caller의 get_logs 동작이 child 로그를 Airflow task 로그로 가져옵니다.
Airflow가 없는 임의의 child image에 이 airflow.cfg를 복사한다고 원격 로깅이
생기지는 않습니다.

## 5. Metrics 전송과 실제 수집 경로

버전에 맞는 OTel 의존성이 설치된 image에서 한 metrics backend를 선택합니다.
다음은 OTel을 선택한 설정입니다.

```ini
[metrics]
statsd_on = False
otel_on = True
```

각 metrics 송신 프로세스에 전달할 환경 변수 예시입니다.

```dotenv
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector.monitoring.svc:4318/v1/metrics
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=http/protobuf
OTEL_METRIC_EXPORT_INTERVAL=30000
OTEL_SERVICE_NAME=airflow
```

3.3.1에서 기존 otel_host/otel_port/otel_interval_milliseconds 등의 설정은
deprecated이며 표준 OTel 환경 변수 사용을 권장합니다.
위 endpoint는 cluster 내부 OTLP/HTTP 예시입니다. Collector의 HTTP receiver와
실제 Service port, network policy, 필요한 TLS/인증을 맞춥니다.

Prometheus가 OTLP endpoint를 그대로 scrape하는 것은 아닙니다. Collector의
Prometheus exporter를 scrape하거나, 적합한 remote-write exporter와 인증으로
저장소에 전송하는 등 metrics pipeline을 완성해야 합니다.
AMP를 쓴다면 workspace endpoint와 AWS 인증까지 검증합니다.
StatsD를 선택한 경우에도 exporter의 mapping과 실제 series를 확인합니다.

Scheduler heartbeat·scheduling 지연, parse 오류/시간, queued task 나이,
worker/triggerer 상태, DB connection/lock, Pod Pending·OOM·disk pressure와
log upload 오류를 관측합니다. Exporter가 바꾼 실제 metric 이름/label을 확인한 뒤
알람을 만들고 장애 주입으로 전달 경로를 시험합니다.

## 6. Autoscaling과 보안 경계

Celery KEDA query는 Part 2처럼 queue/executor/alias를 구분하고 concurrency와
replica 한도를 반영해야 합니다. Worker는 persistence 설정에 따라 Deployment
또는 StatefulSet일 수 있습니다. Scale-to-zero는 구성된 최소값·trigger·cooldown에
달렸으며 서비스 전체의 idle 비용이 사라지는 것은 아닙니다.

KubernetesExecutor는 task Pod를 직접 생성하므로 Celery worker pool을 키우는
동일한 패턴이 필요하지 않습니다. KEDA가 Deployment만 지원한다는 뜻은 아닙니다.
Node autoscaler도 Pod 완료 즉시 모든 node를 없애지 않습니다. 용량·quota·PDB·
disruption 정책과 다른 workload를 함께 확인합니다.

| 경계 | 확인할 사항 |
| --- | --- |
| AWS identity | Shared Celery worker의 role은 여러 task가 공유합니다. Task별 격리는 별도 pool/executor/KPO child 등 실제 실행 경계로 설계합니다 |
| Kubernetes RBAC | KubernetesExecutor caller 또는 KPO caller에 필요한 권한을 부여합니다. DAG processor가 파싱한다는 이유만으로 Pod 생성 권한을 주지 않습니다 |
| Namespace/admission | Pod 생성 권한이 다른 SA·위험한 spec 선택으로 이어질 수 있으므로 신뢰 경계와 admission을 확인합니다 |
| NetworkPolicy | CNI enforcement와 DNS, Execution API, DB/broker, K8s API, credential/secret/log endpoint 경로를 실제로 검증합니다 |

NetworkPolicy는 L3/L4 연결을 제한하며 IAM·RBAC·TLS 인증을 대체하거나 모든
횡적 이동을 막는 보장은 아닙니다. 기본 거부 적용 전 실제 의존 경로를 허용하고,
task에 불필요한 DB 접근을 넓히지 않습니다.

## 7. 운영 인수 기준

- [ ] 지원 runtime/provider와 executor 선택, DAG 전달·재실행 버전 정책을 기록했습니다.
- [ ] 적합한 production DB와 backup·restore·Fernet/외부 데이터 복구를 시험했습니다. RDS는 가능한 선택이며 유일한 선택은 아닙니다.
- [ ] Scheduler/API/processor와 필요한 triggerer의 장애·복구·용량 한도를 시험했습니다.
- [ ] Migration, 실행 유입 제어, drain과 rollback 절차를 실제 복제본으로 검증했습니다.
- [ ] 의도한 secrets 조회 경로와 IAM/RBAC/admission/network 경계를 확인했습니다.
- [ ] 성공·실패·강제 종료·Pod 삭제 후 로그를 확인하고 손실 범위를 기록했습니다.
- [ ] Metrics·service/task 로그·알람과 담당자 대응 절차가 연결되어 있습니다.
- [ ] 목표 부하와 장애 상황에서 지연·재시도·중복 외부 쓰기·복구 시간을 측정했습니다.

체크박스만으로 안정성을 보증하지 않습니다. 목표 SLO·복구 시간·데이터 보존 요구에
맞춘 실측 결과와 미해결 제한을 운영 인수에 포함합니다.

## 검증 범위와 참고 자료

아래 공식 문서와 릴리스 소스로 설정·조회 경로·로그 업로드 시점을 확인했습니다.
예제 구조와 S3 upload 함수의 로컬 파일 동작을 검증했으며 실제 DB migration,
AWS secret/S3 호출, Collector 수집이나 장애 복구 시험은 수행하지 않았습니다.


- [Scheduler HA and database coordination](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/scheduler.html)
- [Database upgrades](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/upgrading.html)
- [Database maintenance CLI](https://airflow.apache.org/docs/apache-airflow/3.3.1/cli-and-env-variables-ref.html)
- [Fernet encryption](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/fernet.html)
- [Secrets backends and worker configuration](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/secrets-backend/index.html)
- [Task logging](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/logging-tasks.html)
- [Metrics configuration](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/metrics.html)
- [Amazon provider 9.34.0 S3 log implementation](https://github.com/apache/airflow/blob/providers-amazon/9.34.0/providers/amazon/src/airflow/providers/amazon/aws/log/s3_task_handler.py)

[README](README.md)

[Quiz](../../quizzes/data-on-eks/airflow/05-operations-quiz.md)
