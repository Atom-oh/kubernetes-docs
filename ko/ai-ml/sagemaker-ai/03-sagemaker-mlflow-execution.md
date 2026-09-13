# Part 3: SageMaker AI와 MLflow 실행

> **마지막 업데이트**: 2026년 9월 12일

## 실행 전 주의

**현재 커밋된 GPU 실행 경로는 지원 종료 이미지 때문에 차단됩니다.** 예제의 PyTorch `2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` DLC는 공식 카탈로그에서 패치 지원 종료일을 `2026-08-06`으로 명시합니다. `src/runtime_contract.py`는 preflight·provisioning·Training Job 제출·EKS 생성·학습 진입점에서 이 기준을 검사합니다. 이미지, `torch` 및 의존성을 함께 갱신하고 GPU smoke 검증을 수행하기 전에 날짜 검사만 제거하면 안 됩니다.

아래는 `examples/ai-ml/qwen-pii-finetuning/`의 수정된 실행 계약입니다. 로컬 테스트·요청 미리보기·소유 자원 정리는 사용할 수 있습니다. 2026년 9월 1일 AWS 실험은 **학습 제출 전에 중단**됐으며, 이번 검토에서도 AWS 자원 생성이나 GPU 학습은 수행하지 않았습니다.

새 SageMaker 관리형 MLflow 배포에는 AWS가 권장하는 **MLflow App**을 사용합니다. 기존 Tracking Server도 별도 리소스로 존재합니다. 현재 App 문서는 MLflow `3.10`을 안내하지만 이 과거 예제의 client·EKS server pin은 `3.1.4`입니다. 로컬 3.1.4 artifact export를 확인한 것이 관리형 App과의 전체 호환성을 검증한 것은 아닙니다. 런타임 갱신 시 이 조합도 검증해야 합니다.

## 관리형 경로의 8단계

### 1. Read-only preflight

명령은 패키지 README의 의존성을 설치한 **Python 3.12 가상환경을 활성화한 상태**에서 실행합니다.

```bash
cd examples/ai-ml/qwen-pii-finetuning
export AWS_REGION=ap-northeast-2
python3 src/runtime_contract.py --check-execution
```

현재 이 명령은 지원 종료 사유와 함께 실패하는 것이 정상입니다. 지원되는 런타임으로 예제를 갱신한 다음, 관리자가 확인한 `EXPECTED_ACCOUNT_ID`, `DATAZONE_DOMAIN_ID`, `DATAZONE_PROJECT_PROFILE_ID`, `DATAZONE_OWNER_GROUP_ID`를 환경에 설정하고 `./launch/aws/preflight.sh`를 실행합니다. 비밀번호나 서비스 계정 키를 넣는 변수가 아닙니다.

preflight는 도구·호출자·리전·쿼터·DLC 및 기존 실험 충돌을 확인합니다. 도메인·profile·group을 이름이나 STS role 문자열에서 추측하지 않습니다. 목록이 비어 있어도 모든 자원의 부재나 이후 생성 권한을 보장하지 않습니다. 같은 prefix의 자원이 있으면 소유자를 확인하며, 무조건 삭제하지 않습니다.

### 2. 소스 번들 생성

```bash
./launch/aws/build_source_bundle.sh
```

번들은 `src/*.py`, `config/experiment.yaml`, `requirements.lock`와 같은 내용의 `requirements.txt`를 포함합니다. 데이터 파일이나 로컬 credential 파일을 재귀적으로 묶지 않습니다. 다만 소스·설정에 직접 넣은 민감값까지 탐지하는 도구는 아니므로 번들 내용을 검토해야 합니다. 번들 SHA-256은 **그 빌드의 값**이며 tar timestamp까지 재현 가능하다는 보장은 없습니다.

### 3. MLflow App과 Unified Studio project 생성

지원되는 런타임과 권한 검증을 완료한 이후에 실행하는 **AWS 변경·비용 발생 단계**입니다.

```bash
./launch/aws/provision.sh
```

임시 버킷, 실행 role·MLflow role, MLflow App과 owner membership을 포함한 프로젝트를 생성합니다. 버킷에는 Block Public Access·AES-256·versioning을 적용하고 IAM 정책을 Access Analyzer로 검사합니다. App은 `Created`/`Updated`를 기다립니다. 프로젝트 `ACTIVE`만으로 모든 프로젝트 환경이 배포 완료됐다고 해석하지 않습니다.

생성 의도와 성공 응답을 private inventory에 구분해 기록합니다. 기존 자원과 충돌하거나 응답을 잃어 생성 여부가 불명확하면 이름만 보고 삭제하지 않습니다. 오류 시 정리는 확인된 소유권 범위에서 시도하며, 미확인 상태는 수동 대조가 필요합니다. 프로세스·인스턴스 강제 중단에는 shell trap이 실행되지 않을 수 있습니다.

### 4. Dataset upload

버킷과 inventory가 먼저 만들어져야 업로드할 수 있습니다. 다섯 입력만 검증합니다.

```bash
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json
# 실제 S3 업로드와 SHA-256 readback 검증:
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json --execute
```

입력은 `generated/source.tar.gz`, `data/{train,validation,test}.jsonl`, `data/dataset-manifest.json`입니다. split 해시를 manifest와 대조하고 버킷 계정·실험 tag를 확인한 뒤, 실행별 `qwen-pii/<experiment-id>/source/`와 `dataset/` prefix에 올립니다. 업로드 후 객체를 다시 읽어 SHA-256을 비교합니다. 이 작은 합성 예제는 파일당 64 MiB로 제한합니다. 실패하면 일부 객체가 이미 올라갔을 수 있으므로 inventory를 보존합니다.

식별자와 해시는 비공개 운영 기록에서 사용합니다. presigned URL은 접근 자격을 포함하므로 공개 문서·로그에 붙이지 않습니다.

### 5. SageMaker Training Job request

```bash
python3 -m launch.sagemaker_train \
  --mode smoke --inventory results/resource-inventory.json
```

기본 동작은 `results/previews/` 아래 고유한 미리보기 JSON을 작성하며 AWS 제출은 하지 않습니다. 실제 제출 기록인 `<job-name>-request.json`과 `<job-name>-job.json`은 덮어쓰지 않습니다. 지원되는 런타임 검증 후 `--execute`를 붙여야 실제 제출합니다. full은 별도로 `--mode full --execute`를 지정합니다. 성공한 smoke나 입력 해시 확인을 launcher가 자동 승인하는 것은 아닙니다.

설정 파일은 소스 번들의 `/opt/ml/code/config/experiment.yaml`에서 읽습니다. 데이터 channel의 `/opt/ml/input/data/dataset/`에는 네 데이터 파일이 있습니다. 로컬 `--config`와 번들 설정이 일치하도록 같은 소스에서 생성해야 합니다.

제출 전에 request와 job journal을 함께 예약하고 정리 도구와 공유하는 잠금을 사용합니다. 생성 성공을 확인한 작업은 모니터링 오류·인터럽트 시 중지 요청을 시도합니다. `stop_requested`는 종료 확인이 아닙니다. `submission_unknown`·`stop_unconfirmed` 또는 호스트 강제 종료 뒤에는 AWS 상태·소유권을 대조해야 하며, 기존 journal이나 고립된 request를 덮어써 재제출하지 않습니다.

현재 설정은 `ml.g6e.4xlarge` 한 대, 300 GiB, smoke 10/full 80 step, `MaxRuntimeInSeconds: 10800`입니다. runtime 제한은 종료·업로드 시간, MLflow·S3 등 다른 자원 비용까지 포함한 전체 비용 상한이 아닙니다.

### 6. Smoke/full gate

실제 실행을 다시 허용하기 전에는 지원되는 이미지·의존성·MLflow 조합을 검증해야 합니다. 그다음 smoke의 terminal 상태, 데이터 해시, 지표, 어댑터 파일을 확인합니다. 원문·entity value·mapping·raw completion이 로그나 MLflow에 유출되지 않았는지도 검토합니다. **파일명 allowlist는 내용의 안전성을 증명하지 않습니다.** 이 단계는 자동 PII scanner가 구현됐다는 의미가 아닙니다.

### 7. Aggregate result export

| 파일 | 의미 |
|---|---|
| `dataset-manifest.json` | 생성 조건·개수·split 해시 |
| `resolved-config.json` | 실제 사용 설정·환경·step |
| `dependency-versions.json` | 설치된 버전 관측값; 전체 lock 보장 아님 |
| `baseline-metrics.json`, `tuned-metrics.json` | 동일 test split의 집계 평가 |
| `run-summary.json` | 구간 시간·집계 지표·adapter inventory |
| `adapter/adapter_config.json`, `adapter/adapter_model.safetensors` | MLflow에 보존하는 최종 어댑터 |

SageMaker의 `/opt/ml/model` 출력과 MLflow artifact는 보존 위치가 다릅니다. 버킷·App 삭제 전에 필요한 결과를 내려받아 검증합니다. 어댑터도 공유 전에 접근 권한과 내용을 검토해야 합니다. raw prediction·token mapping·중간 checkpoint 전체를 export하지 않습니다.

`peak_gpu_memory_bytes`는 모델 로딩 뒤 reset한 PyTorch 기본 CUDA device의 allocated-memory peak입니다. 전체 GPU 메모리·로딩 peak·다중 device 합계가 아닙니다. 학습 결과가 없으므로 현재 문서에 성능 향상이나 비용 비교 수치를 게시하지 않습니다.

### 8. Teardown과 검증

```bash
./launch/aws/teardown.sh
./launch/aws/verify_cleanup.sh
```

먼저 기록된 학습 작업을 확인·중지합니다. 학습 기록이 있으면 결과 보존 전에 버킷을 삭제하지 않도록 추가로 중단합니다. 필요한 SageMaker/MLflow artifact를 별도로 보존한 뒤에만 다음 명령으로 삭제를 진행합니다.

```bash
./launch/aws/teardown.sh results/resource-inventory.json \
  --discard-training-artifacts
```

이 옵션은 백업을 대신 수행하지 않습니다. EKS가 남아 있으면 공통 teardown도 중단됩니다. EKS 실행 경로의 검증된 export 후 삭제 또는 아래 수동 복구를 먼저 완료합니다. 이후 소유권이 확인된 App·project·S3·IAM을 정리합니다. AWS `AccessDenied`, 통신 오류, 삭제 대기 시간 초과, S3 객체별 삭제 오류를 자원 부재로 처리하지 않습니다. 소유권 기록이 없는 과거 inventory는 자동 삭제를 거부하며 관리자가 실제 자원과 대조해야 합니다. 공통 TrainingJobs log group 전체나 실험 밖의 자원을 삭제하는 도구가 아닙니다.

검증 보고서의 잔존·미확인 상태가 있으면 실패입니다. 성공도 조회한 계정·리전·inventory와 검사 범위 안에서의 결과이지 전체 AWS 계정에 자원이 없다는 뜻은 아닙니다. 정리 실패나 보존된 클러스터에는 비용이 계속 발생할 수 있습니다.

## EKS + MLflow 비교 경로

런타임 갱신 후의 진입점은 `./launch/eks/run.sh smoke`와, 별도 검토 이후의 `./launch/eks/run.sh full`입니다. 현재는 지원 종료 guard에서 중단됩니다.

| 항목 | 예제 계약과 한계 |
|---|---|
| 클러스터 | 템플릿 EKS `1.36`, `g6e.4xlarge` 한 대; 지역 가용성과 현재 지원을 재확인 |
| GPU plugin | `0.20.0` pin; 새 DLC·AMI·driver와 함께 검증 |
| kubeconfig | 실행별 파일과 명시적 context, 기존 클러스터 충돌 거부 |
| MLflow | ClusterIP·SQLite·`emptyDir`; 인증·영속성·멀티테넌트 격리가 제공되는 구성은 아님 |
| 데이터 | ServiceAccount의 AWS 권한과 SDK로 읽고 manifest SHA-256·버킷 계정을 검증 |
| Job | `backoffLimit: 0`, `activeDeadlineSeconds: 10800`; 장애 시 정확히 3시간 내 모든 자원 회수 보장 아님 |
| export | 실험·클러스터·실행 ID가 일치하는 완료 run의 8개 artifact와 SHA-256을 검증 |
| 종료 | export와 해시 검증 성공 후 소유 클러스터 정리; export 실패 시 복구를 위해 남길 수 있음 |

입력 로더는 ConfigMap에 있는 코드와 업로드 hash manifest를 읽고, EKS Pod Identity로 다섯 S3 객체만 다운로드합니다. ServiceAccount는 `qwen-input-reader`이며 Pod Identity Agent·지원 SDK·연결 설정이 필요합니다. EC2 instance metadata credential fallback은 끕니다. 이것은 현재 지원 종료 DLC의 실행 차단을 해제하는 절차가 아닙니다.

학습 Pod와 MLflow Pod의 `emptyDir`는 Pod/클러스터 삭제 시 사라집니다. 실행별 `results/eks-<mode>.<suffix>/mlflow-export-<mode>.tar.gz`와 export receipt를 호스트에 받는 것만으로 원격 백업이 되지는 않습니다. 별도 보관 위치에 복사하고 정리 결과를 확인해야 합니다.

실패한 학습에 완료 run이나 export가 없으면 자동 삭제 조건을 충족하지 못합니다. private inventory의 계정·클러스터 ARN·생성 시각·ownership tag·stack ID를 실제 AWS 상태와 대조하고, 필요한 결과를 회수하거나 폐기하기로 결정한 뒤 **그 소유 클러스터만** `eksctl delete cluster --name ... --region ... --wait`로 정리합니다. 부분 생성·응답 유실도 같은 수동 대조가 필요합니다. 그 뒤 `verify_cleanup.sh`로 확인하며, stack 삭제에서 retain된 자원은 별도로 조사합니다. journal의 소유권 flag를 임의로 바꿔 검사를 통과시키면 안 됩니다.

## 관찰된 오류와 중단 조건

| 조건 | 처리 |
|---|---|
| 패치 지원 종료 DLC | 생성·학습 차단; 지원되는 실행 환경을 함께 갱신 |
| 잘못된 설정 파일 경로 | 데이터 channel 대신 source bundle의 config 사용 |
| 기존 이름 충돌·생성 응답 유실 | 소유권 불명확 자원 자동 삭제 금지 |
| export 누락·실패 | adapter와 집계 파일 확인 전 성공 처리 금지 |
| 조회 권한 오류·삭제 timeout | 미확인/실패로 기록 |
| 과거 project membership 누락 | domain administrator·project owner와 권한 대조 |

## 어떤 경로를 선택할까

SageMaker는 Training Job과 MLflow 관리 부담을 줄여 주지만 artifact 보존·권한·실험 정리까지 대신 완료하지는 않습니다. EKS는 Kubernetes 제어권을 제공하며 cluster·GPU plugin·MLflow 저장소 운영 책임이 추가됩니다. 비교 시 설정·데이터·모델 revision·실제 dependency와 GPU 환경을 함께 기록해야 합니다.

## 공식 근거

- [AWS DLC PyTorch 2.8 카탈로그와 패치 종료일](https://github.com/aws/deep-learning-containers/blob/main/docs/src/data/pytorch-training/2.8-gpu-sagemaker.yml)
- [SageMaker Training Toolkit 코드 디렉터리](https://github.com/aws/sagemaker-training-toolkit/blob/master/src/sagemaker_training/entry_point.py)
- [MLflow App 설정](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow-app-setup.html)
- [SageMaker MLflow 버전](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow.html)
- [S3 presigned URL 만료](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [EKS Pod Identity의 동작과 제약](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Kubernetes Job의 실패·종료](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

이전: [Part 2 — 합성 PII 데이터와 토큰화](02-pii-data-tokenization.md)

다음: [Part 4 — Unified Studio 거버넌스](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
