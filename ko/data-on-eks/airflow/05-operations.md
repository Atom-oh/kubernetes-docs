# Part 5: 운영과 보안

> **마지막 업데이트**: 2026년 7월 15일

지금까지 Airflow 3의 컴포넌트 아키텍처(Part 1), Helm 배포와 `KubernetesExecutor`/`CeleryExecutor` 선택(Part 2), Kubernetes 환경에 맞는 DAG 작성 패턴(Part 3), MWAA 연동(Part 4)을 다뤘습니다. 이 마지막 문서는 배포를 실제 프로덕션에 올리기 전에 남은 항목들 — 스케줄러 HA, 안전한 업그레이드, 시크릿, 로깅, 모니터링, 보안 체크리스트 — 을 다루고, 시리즈 전체(Part 1~5)를 하나의 운영 체크리스트로 정리합니다.

## 1. 스케줄러 고가용성(HA)

스케줄러 레플리카를 여러 개 띄우는 것은 스케줄링 단일 장애점(SPOF)을 없애는 표준적인 방법입니다. Airflow 2에서는 이 구성이 실제로 꽤 불안정했습니다. 스케줄러 프로세스가 작업 스케줄링과 DAG 파일 파싱을 동시에 담당했기 때문에, 여러 스케줄러 레플리카가 같은 DAG 묶음을 동시에 파싱하면서 경쟁 상태와 중복 작업이 발생해 부하가 높을 때 스케줄링 지연이 불안정해질 수 있었습니다.

Part 1에서 다룬 것처럼 Airflow 3에서는 이 문제가 더 이상 존재하지 않습니다. DAG 파싱이 스케줄러에서 완전히 분리되어 별도의 필수 서비스인 `dag-processor`로 옮겨졌기 때문입니다. 이제 모든 스케줄러 레플리카는 동일하게 동작합니다 — Postgres의 작업 상태와 `serialized_dag` 테이블을 읽어 준비된 작업 인스턴스를 큐에 넣는 것뿐이며, 파일 파싱을 두고 서로 경쟁할 필요가 없습니다. 파싱과 스케줄링이 완전히 분리되었기 때문에 스케줄러 레플리카를 늘리는 것은 새로운 경쟁을 유발하지 않는, 단순한 수평 확장·HA 수단이 됩니다.

```yaml
# values.yaml — 스케줄러 레플리카 수
scheduler:
  replicas: 2
```

공식 Helm 차트에서는 이 값 하나만 조정하면 됩니다. 실제 조정(coordination) 지점은 여전히 Postgres입니다(스케줄러들은 행 단위 잠금을 사용해 동일한 작업 인스턴스를 중복으로 큐에 넣지 않도록 방지합니다). 즉, 스케줄러 HA를 위해 데이터베이스가 이미 제공하는 것 이상의 별도 리더 선출 메커니즘이 필요하지 않습니다.

## 2. DB 마이그레이션과 업그레이드

메타데이터 Postgres 데이터베이스에는 배포의 모든 DAG 실행, 작업 인스턴스, 커넥션, 변수, XCom이 저장되어 있습니다. 메이저 버전 업그레이드 전에는 예외 없이 반드시 백업을 받아야 합니다.

* **핫 백업**: Airflow를 계속 운영 상태로 두면서 일관된 스냅샷(예: RDS 자동/수동 스냅샷, `pg_dump`)을 뜨는 방식으로, 업그레이드 자체는 이후 스키마 마이그레이션 단계에서 진행되므로 대부분의 경우 충분합니다.
* **콜드 백업**: 최고 수준의 일관성을 원한다면 스케줄러, dag-processor, triggerer를 먼저 정지시켜(작업 상태를 쓰는 프로세스가 없는 상태) 백업한 뒤 마이그레이션을 진행합니다.

```bash
# 업그레이드 전 RDS 수동 스냅샷
aws rds create-db-snapshot \
  --db-instance-identifier airflow-metadata-db \
  --db-snapshot-identifier airflow-pre-upgrade-$(date +%Y%m%d)
```

Airflow 3의 업그레이드 경로에는 `serialized_dag` 중심의 새 스케줄러 설계를 지원하기 위한 스키마 변경이 포함되어 있으며, `airflow db migrate`는 수년치 작업 인스턴스·DAG 실행 이력이 쌓인 데이터베이스에서는 시간이 오래 걸릴 수 있습니다 — 마이그레이션이 순회하고 재작성해야 하는 행 수가 이력 규모에 비례하기 때문입니다. 오래 운영해온 배포를 업그레이드하기 전에는 먼저 오래된 이력을 정리해 마이그레이션이 처리할 데이터를 줄이는 것이 좋습니다.

```bash
# 업그레이드 전 60일 이상 지난 작업 인스턴스/DAG 실행 이력 삭제
airflow db clean --clean-before-timestamp "$(date -d '60 days ago' -Iseconds)" --yes
```

`airflow db clean`(또는 이와 동등한 보존 정책 작업)은 업그레이드 직전에만 실행할 것이 아니라 주기적으로 실행하는 것이 좋습니다. 메타데이터 데이터베이스를 작게 유지하면 이후의 모든 마이그레이션이 더 빨라집니다.

## 3. 시크릿 백엔드 설정

커넥션과 변수를 메타데이터 데이터베이스에 평문으로 저장하는 것이 기본 동작이지만, 프로덕션 환경에서는 프로바이더 패키지가 제공하는 `SecretsManagerBackend`로 AWS Secrets Manager를 백엔드로 사용해야 합니다.

```ini
# airflow.cfg
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "config_prefix": "airflow/config"}
```

이렇게 설정하면 `airflow_remote_logging_conn` 커넥션을 조회할 때, 메타데이터 데이터베이스로 넘어가기 전에 먼저 Secrets Manager의 `airflow/connections/airflow_remote_logging_conn` 경로를 확인합니다.

**이 설정은 api-server, scheduler, worker 전체에서 반드시 동일해야 합니다.** 각 컴포넌트는 런타임에 각자 독립적으로 커넥션과 변수를 조회하며, 한 컴포넌트의 `[secrets]` 설정이 다른 컴포넌트를 대신 커버해주는 공유 캐시 같은 것은 존재하지 않습니다. `backend_kwargs`가 컴포넌트마다 다르게 설정되어 있으면(worker에만 옛 prefix가 남아 있거나, api-server에 `[secrets]` 섹션이 아예 빠져 있는 경우 등) 해당 컴포넌트는 조용히 메타데이터 데이터베이스로 폴백하게 되고, 그 결과 커넥션 조회가 컴포넌트별로 제각각 실패하기 시작합니다 — 예를 들어 스케줄러에서는 되는데 워커 Pod에서는 안 되는 식으로, 사후에 원인을 추적하기 매우 까다로운 장애 유형입니다.

이는 특히 리모트 로깅용 커넥션에서 중요합니다. 로그를 남기는 모든 컴포넌트(api-server, scheduler, dag-processor, triggerer, 그리고 `KubernetesExecutor`의 모든 작업 Pod)가 각자 리모트 로깅 커넥션을 독립적으로 조회해 로그를 어디로 보낼지 결정하기 때문에, 컴포넌트 하나만 설정이 잘못돼도 그 컴포넌트의 로그는 요란한 에러 없이 그냥 어디로도 가지 않고 조용히 사라져 버립니다.

## 4. 리모트 로깅

작업 Pod는 일시적(ephemeral)이며, 이는 `KubernetesExecutor`(Part 2)에서 특히 두드러집니다 — Pod는 작업을 위해 생성되고 작업이 끝나면 바로 정리됩니다. 리모트 로깅이 없다면 Pod가 가비지 컬렉션되는 순간 그 작업의 로그도 함께 사라지므로, 실패한 실행을 사후에 디버깅하는 것이 불가능해집니다.

리모트 로깅 대상으로 S3를 설정할 때는, 커넥션을 `airflow.cfg`에 직접 넣기보다 Secrets Manager에 저장한 커넥션을 사용합니다.

```ini
# airflow.cfg
[logging]
remote_logging = True
remote_base_log_folder = s3://my-airflow-logs-bucket/logs
remote_log_conn_id = airflow_remote_logging_conn
```

```bash
# 커넥션 자체는 Secrets Manager에 저장되며, 3절의 SecretsManagerBackend를 통해 조회됩니다
# Secret 이름: airflow/connections/airflow_remote_logging_conn
# Secret 값 (JSON으로 인코딩된 Airflow 커넥션):
{"conn_type": "aws", "extra": {"region_name": "us-east-1"}}
```

이렇게 설정하면 단일 작업 하나의 생명주기만큼만 존재하는 작업 Pod를 포함한 모든 컴포넌트가 로그를 기록하는 즉시 S3로 전송하므로, Pod가 사라진 지 오래된 뒤에도 api-server가 해당 작업의 과거 로그를 화면에 그대로 렌더링할 수 있습니다. 3절에서 강조한 "컴포넌트 간 설정 일치"가 실제로 왜 중요한지가 바로 여기서 드러납니다. worker Pod가 api-server와 다른 시크릿 백엔드 설정으로 `airflow_remote_logging_conn`을 조회하게 되면, 작업 로그와 UI에 렌더링되는 로그가 조용히 어긋나기 시작합니다.

## 5. 모니터링

Airflow 컴포넌트는 **StatsD** 또는 **OpenTelemetry** 방식으로 메트릭을 기본 제공합니다 — 두 방식은 `airflow.cfg`의 `[metrics]` 섹션에서 설정하는 서로 대체 가능한 전송 경로이므로 둘 다 켤 필요는 없고 하나를 선택하면 됩니다.

```ini
# airflow.cfg — OpenTelemetry 예시
[metrics]
otel_on = True
otel_host = otel-collector.monitoring.svc
otel_port = 4318
```

EKS에서는 일반적으로 이 메트릭 전송을 **Prometheus 또는 Amazon Managed Prometheus**(저장)와 **Grafana**(대시보드)와 연동하며, OpenTelemetry Collector(StatsD를 사용한다면 StatsD-to-Prometheus exporter)가 Airflow의 기본 전송 형식과 Prometheus의 스크래핑 모델 사이를 이어주는 브리지 역할을 합니다. 컨테이너의 stdout/stderr를 수집하는 로그 전송 계층으로는 보통 **Fluent Bit**를 사용하며, 이는 4절의 S3 리모트 로깅을 대체하는 것이 아니라 보완하는 역할입니다. Fluent Bit는 인프라 수준의 Pod 로그를 원하는 로그 백엔드로 전송하고, 리모트 로깅은 Airflow 자체의 작업 실행 로그를 S3로 보내 UI에서 다시 볼 수 있게 합니다.

## 6. 오토스케일링 정리

Part 2에서 `CeleryExecutor` 워커 Pod를 위한 KEDA 기반 오토스케일링을 깊이 다뤘습니다 — 메타데이터 데이터베이스에서 읽은 큐에 쌓인/실행 중인 작업 수를 기준으로 워커 `Deployment`를 늘리고 줄이며, 유휴 상태에서는 레플리카 0까지 줄어듭니다. 이 메커니즘 자체는 여기서 달라지지 않으므로, 전체 KEDA 설정과 동작은 Part 2를 참고하세요.

`KubernetesExecutor`에서는 워크로드 수준에서 스케일할 워커 `Deployment` 자체가 존재하지 않습니다 — 작업 하나가 이미 그 자체로 하나의 Pod이기 때문입니다. 대신 스케일이 필요한 대상은 클러스터 용량입니다. **Karpenter** 또는 **Cluster Autoscaler**가 스케줄러가 생성하는 작업 Pod에 맞춰 노드를 프로비저닝하고, Pod가 끝나면 그 용량을 다시 반납합니다. 두 Executor는 오토스케일링 문제를 서로 다른 계층에 떠넘기는 셈입니다 — `CeleryExecutor`는 KEDA가 고정된 워커 풀을 스케일하고, `KubernetesExecutor`는 클러스터 수준 오토스케일링이 작업별로 생성·소멸하는 Pod의 변동을 흡수합니다.

## 7. 보안 체크리스트

* **시크릿 백엔드 일관성**: `SecretsManagerBackend`(3절)가 api-server, scheduler, dag-processor, triggerer, worker/작업 Pod 전체에서 동일하게(같은 `backend_kwargs`, 같은 prefix) 설정되어 있어, `[secrets]` 설정이 누락되거나 어긋난 컴포넌트가 조용히 메타데이터 데이터베이스로 폴백하는 일이 없다.
* **작업 단위 AWS 권한을 위한 IRSA 스코핑**: `KubernetesExecutor`의 각 작업 Pod(또는 각 Celery 워커)는 관련 없는 여러 DAG가 공유하는 넓은 권한의 롤이 아니라, IRSA를 통해 해당 작업에 실제로 필요한 AWS 액션만 허용된 롤을 assume해야 한다. `KubernetesPodOperator`로 작업별 전용 서비스 어카운트(및 그에 매핑된 IAM 롤)를 지정하는 방법은 Part 3을 참고.
* **Airflow 서비스 어카운트의 최소 권한 RBAC**: 스케줄러와 dag-processor가 작업 Pod를 생성/watch하기 위해 사용하는 Kubernetes 서비스 어카운트는 자신의 네임스페이스 안에서 실제로 필요한 verb와 리소스(`pods`, 필요 시 `pods/log`, `pods/exec`)만 허용받아야 하며, 클러스터 전역 admin 바인딩을 사용해서는 안 된다.
* **네트워크 정책**: scheduler, api-server, dag-processor, worker/작업 Pod 간 트래픽을 실제로 필요한 대상 — 메타데이터 데이터베이스, 시크릿 백엔드의 VPC 엔드포인트, 리모트 로깅 대상, (`CeleryExecutor`의 경우) 브로커 — 로만 제한한다. Airflow 네임스페이스에 기본 거부(deny-by-default) `NetworkPolicy`를 적용하고 컴포넌트별로 명시적 허용 규칙을 두면, 관련 없는 Pod가 침해되더라도 Airflow 컨트롤 플레인으로의 수평 이동을 막을 수 있다.

## 8. 시리즈 마무리: 운영 체크리스트

이 딥다이브 시리즈(Part 1~5)의 핵심 항목을 프로덕션 배포 전 최종 점검 목록으로 정리하면 다음과 같습니다.

- [ ] **아키텍처**: Airflow 3의 4개 서비스(api-server, scheduler, dag-processor, triggerer)가 모두 배포되어 있고, DAG 파싱이 오직 dag-processor에서만 일어나는 것을 확인했다 (Part 1)
- [ ] **메타데이터 데이터베이스**: 랩 수준을 벗어난 환경이라면 차트에 내장된 Postgres가 아니라 Amazon RDS for PostgreSQL을 사용하며, 자동 백업이 활성화되어 있다 (Part 1, 5)
- [ ] **Executor 결정**: `KubernetesExecutor`와 `CeleryExecutor` 중 하나 — 또는 작업/DAG 단위로 의도적으로 혼용하는 방식 — 을 차트 기본값에 맡기지 않고 근거와 함께 문서화했다 (Part 2)
- [ ] **오토스케일링**: `CeleryExecutor` 워커 풀에 KEDA가 연동되어 있거나, `KubernetesExecutor`의 작업 Pod 변동을 클러스터 수준 오토스케일링(Karpenter/Cluster Autoscaler)이 흡수하는 것을 확인했다 (Part 2, 5)
- [ ] **DAG 작성 규칙**: 작업 단위 Executor 오버라이드와 `KubernetesPodOperator` 사용이 dag-processor를 고려해 정립된 패턴을 따른다 (Part 3)
- [ ] **MWAA vs 셀프 매니지드 결정**: 관리형 MWAA와 EKS 셀프 매니지드 배포 중 선택한 근거(운영 부담, 비용)가 문서화되어 있다 (Part 4)
- [ ] **스케줄러 HA**: Airflow 2의 취약한 방식이 아니라, dag-processor로 파싱이 분리된 Airflow 3 구조를 바탕으로 스케줄러 레플리카를 여러 개 운영하고 있다 (Part 5)
- [ ] **업그레이드 리허설**: 메타데이터 데이터베이스 백업과 이력 정리 단계를 메이저 버전 업그레이드 전에 스테이징에서 실제로 검증했다 (Part 5)
- [ ] **시크릿 백엔드**: `SecretsManagerBackend`가 모든 컴포넌트에서 동일하게 설정되어 있고, 리모트 로깅 커넥션까지 end-to-end로 정상 동작함을 확인했다 (Part 5)
- [ ] **리모트 로깅**: S3 리모트 로깅이 활성화되어 있고, 작업 Pod가 가비지 컬렉션된 뒤에도 UI에서 로그를 볼 수 있음을 확인했다 (Part 5)
- [ ] **모니터링**: StatsD 또는 OpenTelemetry 메트릭이 Prometheus/Amazon Managed Prometheus와 Grafana로 흘러가고, Fluent Bit가 컨테이너 로그를 전송하고 있다 (Part 5)
- [ ] **보안**: 7절 체크리스트의 IRSA 스코핑, 최소 권한 RBAC, 네트워크 정책이 모두 적용되어 있다 (Part 5)
- [ ] **부하 테스트**: 예상 피크 시점의 DAG 동시성과 작업량을 실제로 부하 테스트했다

이 체크리스트를 모두 충족한다면, 해당 Airflow 3 배포는 EKS 프로덕션 환경에서 안정적으로 운영될 준비가 되었다고 볼 수 있습니다.

## 실습 환경 준비

이 문서에서 다룬 운영 요소들을 직접 실습해보려면 다음이 필요합니다.

* **Part 2에서 구성한 동작 중인 Airflow 3 배포** (Executor는 무엇이든 상관없습니다).
* **리모트 로깅 전용 S3 버킷**(예: `my-airflow-logs-bucket`). 오래된 로그를 자동으로 정리하려면 라이프사이클 정책도 함께 설정합니다.
* **리모트 로깅 커넥션 JSON을 담은 Secrets Manager Secret**. `connections_prefix`와 일치하는 경로(예: `airflow/connections/airflow_remote_logging_conn`)에 저장합니다.
* **Secrets Manager와 S3에 접근해야 하는 Airflow 서비스 어카운트에 대한 IRSA 설정**. 이것이 있어야 `SecretsManagerBackend`와 리모트 로깅이 정적 자격 증명 없이 인증할 수 있습니다.
* **OpenTelemetry Collector(또는 StatsD exporter)와 Prometheus/Amazon Managed Prometheus + Grafana 스택**. 모니터링 절을 따라 해보려면 필요하며, 기존에 구성된 `kube-prometheus-stack`이 있다면 그대로 활용할 수 있습니다.
* **메타데이터 데이터베이스의 스테이징 복제본**(별도 인스턴스로 복원한 RDS 스냅샷이면 충분합니다). 2절의 백업-후-마이그레이션 업그레이드 절차를 실제 배포에 영향을 주지 않고 안전하게 연습해보려면 필요합니다.

---

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/airflow/05-operations-quiz.md)를 풀어보세요.
