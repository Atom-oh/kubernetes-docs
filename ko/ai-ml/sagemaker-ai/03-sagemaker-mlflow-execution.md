# Part 3: SageMaker AI와 MLflow 실행

> **마지막 업데이트**: 2026년 9월 2일

## 실행 전 주의

이 장의 명령은 `examples/ai-ml/qwen-pii-finetuning/`에 커밋된 실행 구현을 설명합니다. 그러나 2026년 9월 1일 기록은 **Training Job 제출 전에 중단**됐습니다. 아래 절차가 실행 가능하다는 사실과 GPU 학습이 실제 완료됐다는 주장을 혼동하면 안 됩니다.

SageMaker 관리형 MLflow의 새 배포에는 legacy Tracking Server가 아니라 **SageMaker MLflow App**을 사용합니다. MLflow App은 run과 experiment를 추적하는 독립 HTTP 서버이며, 이 예제는 S3 artifact store와 최소 권한 IAM 역할을 연결합니다.

## 관리형 경로의 8단계

### 1. Read-only preflight

```bash
cd examples/ai-ml/qwen-pii-finetuning
export AWS_REGION=ap-northeast-2
./launch/aws/preflight.sh
```

preflight는 도구 설치, 호출자 인증, 리전, `ml.g6e.4xlarge` Training Job 쿼터, EC2 GPU vCPU 쿼터, PyTorch DLC와 기존 `qwen-pii-*` App·클러스터·버킷·IAM role·Unified Studio project 충돌을 검사합니다.

기존 `results/resource-inventory.json`이 있거나 잔존 자원이 발견되면 새 실행을 시작하지 않습니다.

### 2. 소스 번들 생성

```bash
./launch/aws/build_source_bundle.sh
```

번들은 다음 파일만 포함합니다.

- `src/*.py`
- `config/experiment.yaml`
- `requirements.lock`와 동일 내용의 `requirements.txt`

데이터셋, raw prediction, 로컬 credential은 번들에 포함하지 않습니다.

### 3. Dataset upload

`provision.sh`가 만든 inventory에는 실행별 S3 prefix와 `source_s3_uri`가 기록됩니다. CI 또는 승인된 artifact publisher는 다음 키 구조로 번들과 네 데이터 파일을 올려야 합니다.

```text
qwen-pii/<experiment-id>/source/source.tar.gz
qwen-pii/<experiment-id>/dataset/train.jsonl
qwen-pii/<experiment-id>/dataset/validation.jsonl
qwen-pii/<experiment-id>/dataset/test.jsonl
qwen-pii/<experiment-id>/dataset/dataset-manifest.json
```

업로드 후 원격 객체 해시를 `data/dataset-manifest.json`의 split SHA-256과 대조합니다. bucket 이름이나 presigned URL은 문서·로그에 게시하지 않습니다.

### 4. MLflow App과 Unified Studio project 생성

```bash
./launch/aws/provision.sh
```

스크립트는 다음 순서로 진행합니다.

1. Block Public Access, AES-256 암호화, versioning을 적용한 임시 S3 bucket 생성
2. SageMaker 실행 role과 MLflow role 생성
3. IAM policy를 Access Analyzer로 검사
4. `create-mlflow-app`으로 MLflow App 생성
5. App 상태가 `Created` 또는 `Updated`인지 확인
6. enabled `All capabilities` project profile 확인
7. 호출 role의 DataZone group profile을 찾고 `PROJECT_OWNER` membership으로 project 생성
8. 모든 생성 자원을 inventory에 기록

오류·인터럽트가 발생하면 trap이 inventory를 기록하고 teardown을 호출합니다.

### 5. SageMaker Training Job request

smoke request:

```bash
python3 launch/sagemaker_train.py \
  --mode smoke \
  --inventory results/resource-inventory.json
```

smoke가 완료되고 로그 안전성 검사가 통과한 뒤에만 full request를 허용합니다.

```bash
python3 launch/sagemaker_train.py \
  --mode full \
  --inventory results/resource-inventory.json
```

두 모드는 같은 `ml.g6e.4xlarge`, 300 GiB volume, 최대 `10,800`초, source bundle, 데이터 channel과 MLflow App을 사용합니다. 차이는 `10` step과 `80` step뿐입니다.

> **기록된 결과**: 위 두 Training Job 명령은 2026년 9월 1일 검증에서 실행되지 않았습니다.

### 6. Smoke/full gate

smoke가 성공했다는 것만으로 full run을 승인하지 않습니다. 다음 항목을 모두 확인합니다.

- Training Job terminal status가 `Completed`
- raw source, entity value, mapping, raw completion이 CloudWatch에 없음
- MLflow parameter/tag에 비민감 설정만 존재
- aggregate metric과 dataset hash가 export됨
- adapter inventory가 허용 파일만 포함
- leak/round-trip 평가가 예외 없이 완료

### 7. Aggregate result export

학습 엔트리포인트는 다음 비민감 파일을 생성하도록 설계됐습니다.

| 파일 | 내용 |
|---|---|
| `resolved-config.json` | 실행 환경과 실제 step을 포함한 설정 |
| `dependency-versions.json` | 고정 dependency 버전 |
| `baseline-metrics.json` | base model 집계 평가 |
| `tuned-metrics.json` | adapter 적용 후 집계 평가 |
| `run-summary.json` | 시간, peak GPU memory, aggregate metric, adapter inventory |

raw prediction JSONL과 token mapping은 결과 아티팩트로 게시하지 않습니다.

### 8. Teardown과 검증

```bash
./launch/aws/teardown.sh
./launch/aws/verify_cleanup.sh
```

teardown은 MLflow App, Unified Studio project, Training Job log stream, versioned S3 objects/bucket, IAM inline policy와 role을 inventory 기준으로 삭제합니다. `verify_cleanup.sh`는 App, project, bucket, role, EKS cluster, EC2 instance와 tag 기반 잔존 자원을 다시 조회하며, 하나라도 남으면 실패합니다.

## EKS + MLflow 비교 경로

동일한 소스와 데이터로 Kubernetes 경로를 실행하는 진입점은 다음과 같습니다.

```bash
./launch/eks/run.sh smoke
```

smoke 결과가 승인된 경우에만:

```bash
./launch/eks/run.sh full
```

이 경로의 계약은 다음과 같습니다.

| 항목 | 구현 |
|---|---|
| 클러스터 | ephemeral Amazon EKS `1.36` |
| GPU node | `g6e.4xlarge` 1대, encrypted 300 GiB gp3 |
| GPU plugin | NVIDIA device plugin `0.20.0` |
| MLflow | namespace 내부 ClusterIP, 외부 공개 없음 |
| 데이터 | 4시간 제한 presigned URL로 같은 S3 객체 다운로드 |
| Job 재시도 | `backoffLimit: 0` |
| 최대 실행 | `activeDeadlineSeconds: 10800` |
| export | MLflow Pod 안에서 집계 JSON을 만든 뒤 `kubectl cp` |
| 종료 | shell trap이 성공·실패·인터럽트 모두에서 클러스터 삭제 |

EKS 경로도 stdout에 원문이나 raw completion을 기록하면 안 됩니다. 현재 `run.sh`의 Job log 출력은 안전성 검사를 거친 집계 로그만 전제로 합니다.

> **기록된 결과**: EKS GPU cluster와 Job도 2026년 9월 1일 검증에서 실행되지 않았습니다.

## 관찰된 오류와 중단 조건

| 조건 | 실제 관찰 또는 방어 | 처리 |
|---|---|---|
| MLflow App 상태 | `Created`/`Updated`가 준비 상태, `Deleted`가 삭제 terminal | 존재하지 않는 `ACTIVE` App 상태를 기다리지 않음 |
| custom project tag 정책 | 도메인이 custom resource tag를 거부할 수 있음 | project 생성 인자에서 금지 태그 제거 |
| project membership | 생성 project에 호출 role group profile이 없으면 조회·삭제 거부 | 생성 시 `PROJECT_OWNER` 지정 |
| Service Quotas throttling | 반복 조회가 제한될 수 있음 | adaptive retry, 최대 시도 설정 |
| 실패 중 정리 | 부분 생성 뒤 실패 가능 | 매 단계 inventory 갱신, trap teardown |
| 잔존 project | owner 권한 없이는 자동 삭제 불가 | GPU 생성 전 중단하고 domain owner 조치 요구 |

## 어떤 경로를 선택할까

- SageMaker AI를 선택하면 Training Job과 최신 관리형 MLflow App의 수명주기를 AWS에 맡길 수 있습니다.
- EKS를 선택하면 cluster와 MLflow를 직접 운영하는 대신 Kubernetes 정책·관측·스케줄링을 그대로 적용할 수 있습니다.
- 비교 실험이라면 두 경로의 config와 dataset hash를 고정하고 environment만 바꿉니다.

이전: [Part 2 — 합성 PII 데이터와 토큰화](02-pii-data-tokenization.md)

다음: [Part 4 — Unified Studio 거버넌스](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
