# Part 3: MLflow를 EKS에 배포하기

> **검토 기준**: MLflow 3.16.0 · community chart 1.11.7 · 2026-09-12

## 실습 환경 준비

EKS의 지원 중인 Kubernetes 버전, 그 API 서버와 호환되는 kubectl, Helm 3, metadata DB와 artifact 저장소를 준비합니다. `kubectl >=1.34`처럼 하한만 맞추면 모든 서버와 호환되는 것은 아닙니다. 실제 클러스터 버전에 대한 client/server skew 정책을 확인합니다.

이 장은 Helm chart를 내려받아 실제 manifest를 렌더링하고 MLflow 3.16.0의 서버 소스와 대조한 결과입니다. **AWS 자원 생성, RDS 연결, S3 업로드 또는 EKS 배포 성공을 검증한 기록은 아닙니다.** 로컬 SQLite/API 검사는 [Part 1](01-tracking.md), Registry 검사는 [Part 2](02-model-registry.md)에 있습니다.

## MLflow 트래킹 서버를 EKS에서 운영하는 이유

기존 Kubernetes 배포·관측·IAM 패턴을 사용할 수 있는 대신 서버, DB, artifact, 접근 제어, 백업과 업그레이드를 직접 운영합니다. SageMaker MLflow App과 다른 관리형 registry도 선택지이지만 지원 버전·인증·기능·비용이 동일하다고 가정하지 않습니다.

한 팀이 공유한다는 이유만으로 반드시 RDS와 S3를 각각 새로 만들어야 하는 것은 아닙니다. 작은 실습용 SQLite/PVC 구성도 가능하지만, 동시성·내구성·장애 복구 요구에 맞춰 운영 구성을 선택합니다.

## 아키텍처

| 계층 | 책임과 확인할 상태 |
|---|---|
| HTTP 서버 | SDK API·UI·artifact proxy; 인증·인가·host/CORS 정책·worker 상태 |
| Metadata DB | experiment/run/metric/model/registry metadata; 연결 pool·migration·백업 |
| Artifact store | 모델·플롯·데이터 파일; bucket/prefix·IAM·암호화·보존 |
| 인증 저장소 | 선택한 auth 방식의 사용자·권한 DB, session/signing secret·cache |
| 추가 기능 상태 | 사용 중인 비동기 job·trace/evaluation·gateway 기능의 queue/cache/임시 파일 |

PostgreSQL과 S3를 연결한 것만으로 모든 기능이 무상태가 되는 것은 아닙니다. 예를 들어 basic-auth가 Pod 로컬 SQLite를 쓰면 replica마다 사용자·권한 상태가 달라질 수 있습니다. OIDC plugin의 cache나 job 저장소도 별도로 확인해야 합니다.

SQLite는 관계형 DB이며 여러 프로세스의 접근과 직렬화된 쓰기를 지원합니다. “두 사용자가 접근하는 순간 깨진다”는 설명은 부정확합니다. 다만 여러 노드의 Pod가 각자의 SQLite 파일을 쓰면 공유 DB가 아니고, 같은 파일을 공유해도 동시 쓰기·파일 잠금·복구 한계를 고려해야 합니다. 운영용 PostgreSQL을 쓰는 이유를 이런 요구사항과 연결합니다.

![보호된 접근 경로를 통해 MLflow 서버에 연결하고, 서버가 metadata 및 인증 DB와 S3 artifact 저장소를 사용하는 구조. S3 IAM 권한과 PostgreSQL 로그인 권한은 별도로 관리하며 공유 상태를 외부화한 뒤 replica를 확장한다.](../../.gitbook/assets/ko-ai-ml-mlflow-03-eks-deployment-0.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-mlflow-03-eks-deployment-0.html)

## 설치 방식과 버전 고정

| 경로 | 이번에 확인한 내용 |
|---|---|
| Community chart | `community-charts/mlflow` 1.11.7을 실제 내려받아 렌더링; appVersion 3.16.0, 기본 image는 `burakince/mlflow` |
| MLflow 저장소 chart | `v3.16.0/charts`에 chart 0.1.1·appVersion 3.15.2가 존재; source tag·chart version·image version은 별개 |
| 직접 manifest | 파일 기반 credential 전달, 네트워크·인증·migration 정책을 직접 제어할 때 선택 |

공식 저장소의 소스가 존재한다고 같은 버전의 OCI package가 반드시 배포돼 있는 것은 아닙니다. 검토 시 공식 OCI chart 0.1.1 pull은 `not found`였으므로 그 명령을 검증된 설치 절차로 제시하지 않습니다.

다음은 chart 기본값을 검토하는 검색·다운로드·렌더링 과정입니다. 운영 값은 아래 항목에 따라 별도로 작성합니다.

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

실제 적용 전에 `rendered.yaml`의 image/digest, ServiceAccount, Secret 전달 방식, CLI 인자, probe, Service/Ingress를 검토합니다. 차트가 사용하는 image는 upstream MLflow image와 다른 커뮤니티 image이므로 포함된 DB driver·AWS SDK·auth plugin도 확인합니다.

### 중요한 chart 1.11.7 기본값

- `replicaCount: 1`, `auth.enabled: false`, `ingress.enabled: false`입니다.
- `backendStore.defaultSqlitePath: ":memory:"`이므로 기본 chart는 metadata를 메모리에 두는 구성입니다. **Upstream CLI의 새 SQLite 파일 기본값과 다릅니다.** 기본 설치를 영속적인 운영 서비스로 간주하면 안 됩니다.
- 외부 DB는 `backendStore.postgres.*`, credential 참조는 `backendStore.existingDatabaseSecret.*`입니다.
- S3 proxy는 `artifactRoot.s3.*`와 `artifactRoot.proxiedArtifactStorage: true`를 함께 확인합니다. 실제 렌더링은 `--artifacts-destination=s3://...`와 `--serve-artifacts`였습니다.
- basic-auth의 DB는 `auth.postgres.*`로 별도 구성합니다. Tracking DB를 바꿔도 auth DB가 자동으로 공유되는 것은 아닙니다.
- `backendStore.databaseMigration: true`는 Pod init container 경로입니다. 여러 replica가 동시에 migration하도록 무조건 켜지 말고, 백업·단일 migration 단계·호환성 검사를 계획합니다.

실제 값과 Secret 없이 이름만 채운 예제는 운영 준비 완료가 아닙니다. 특히 이 chart의 DB/auth credential 참조 일부는 **container 환경 변수로 전달**됩니다. SecretKeyRef는 Git에 plaintext를 쓰지 않게 하지만 프로세스 환경 노출까지 없애지는 않습니다. 환경 변수 secret을 금지하는 정책에서는 Secrets Manager/SSM 등에서 공급한 credential 파일과 이를 읽는 배포 구성을 별도로 준비해야 합니다. 정적 AWS access key를 Helm values나 이미지에 넣지 않습니다.

## IAM과 데이터베이스 인증

S3 권한은 bucket/prefix 범위로 제한합니다. 실제 경로에 따라 `GetObject`, `PutObject`, 목록 조회, multipart, KMS 권한 등을 확인합니다. Proxy 모드는 서버의 AWS 권한, 직접 artifact 모드는 클라이언트의 권한을 사용합니다. 기존 experiment의 URI는 서버 flag 변경만으로 바뀌지 않습니다.

EKS Pod Identity는 Agent·association·지원 SDK가 필요하며 Linux EC2 worker 대상입니다. Fargate·Windows Pod에 무조건 적용되는 선택이 아닙니다. IRSA도 지원 범위와 클러스터의 기존 표준에 맞게 사용할 수 있습니다. ServiceAccount 이름만 지정하거나 annotation 한 줄만 넣었다고 필요한 IAM trust·association·SDK 구성이 모두 완료되는 것은 아닙니다.

S3 접근용 IAM 역할이 PostgreSQL 로그인을 자동 허용하지는 않습니다. DB 네트워크 경로, TLS 검증, 사용자·credential 또는 별도로 구성한 IAM DB authentication을 확인합니다. AWS credential chain이 node role로 의도치 않게 fallback하지 않도록 IMDS·SDK 설정도 점검합니다.

## 서버 접근과 상태 확인

ClusterIP, private ALB, TLS는 각각 네트워크·암호화 계층이며 사용자별 MLflow 권한을 대신하지 않습니다. 공개 ALB를 직접 여는 것을 기본 예제로 삼지 말고 조직의 보호된 진입 경로를 사용합니다.

MLflow 3.16.0에서는 `allowed_hosts`와 CORS origin 설정을 실제 host에 맞게 구성합니다. 이 community chart에서는 `extraArgs.allowedHosts`, `extraArgs.corsAllowedOrigins`로 해당 CLI 인자를 전달할 수 있습니다. Host/CORS 제한 역시 로그인·인가를 대신하지 않습니다. basic-auth는 3.16.0에서 기본 authorization 동작이 fail-closed로 바뀌었으므로 기존 auth plugin·endpoint 호환성도 확인합니다.

확인한 health endpoint는 **`/health`**이며 구현은 `"OK", 200`을 반환합니다. 이것은 process HTTP 응답 검사로, RDS·S3·사용자 권한의 지속적인 정상 동작을 증명하지 않습니다. 이 릴리스의 host 검사는 health endpoint를 예외 처리합니다. `static-prefix`·Ingress rewrite·plugin을 쓰면 실제 서비스 경로를 별도로 검증합니다.

## 운영 시 고려사항

Replica를 늘리기 전에 metadata/auth DB, session secret, 사용 중인 queue/cache를 공유하거나 외부화하고 실제 장애 전환을 검사합니다. 그 후 topology spread·PDB·readiness·resource 제한을 적용합니다. Pod 수가 두 개라는 사실만으로 고가용성을 보장하지 않습니다.

API 호출 한 번이 SQL 쓰기 하나와 항상 일치하지 않습니다. batch logging, transaction, trace payload, metric history와 worker별 DB connection pool을 함께 측정합니다. 여러 replica/worker의 pool이 합쳐지므로 개별 pool 설정만 보고 DB 연결 여유를 판단하지 않습니다.

Aurora Serverless v2도 설정한 capacity 범위, connection·I/O·transaction 제약 안에서 동작합니다. Burst가 자동으로 무제한 흡수되거나 항상 더 저렴한 것은 아닙니다. 부하와 복구 목표에 맞춰 provisioned RDS/Aurora와 비교합니다.

Metadata/auth DB와 artifact를 함께 백업하고 복구를 연습합니다. `mlflow gc` 같은 영구 삭제 작업은 보존 정책과 별도로 검토하며 기본 정리 명령처럼 추가하지 않습니다. 모델 alias 변경과 serving 재배포도 별도 운영 단계입니다.

## 공식 근거

- [MLflow 3.16.0 release](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [MLflow 서버 구조](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [Community chart](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [MLflow 저장소 chart](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [서버 health 구현](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [EKS Pod Identity 제약](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [SQLite 사용 범위와 동시성](https://www.sqlite.org/whentouse.html)
- [Aurora Serverless v2 capacity 설정](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[메인 페이지](README.md) · [퀴즈](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
