# Part 2: MLflow Model Registry

> **검토 기준**: MLflow 3.16.0 · 2026-09-12

## 실습 환경 준비

Python 3.10 이상과 `mlflow==3.16.0`을 사용합니다. Registry API는 로컬 SQLite에서도 실습할 수 있으며 별도 HTTP 서버가 필수는 아닙니다. 팀 배포는 [Part 3](03-eks-deployment.md), Tracking 설정은 [Part 1](01-tracking.md)을 참고합니다. 다음 설명은 OSS MLflow 기준이며 Databricks Unity Catalog 같은 관리형 registry의 권한·복사·보존 동작과 구분합니다.

## Model Registry란 무엇인가

Registry는 모델의 논리적 이름, 번호가 붙은 버전, alias와 metadata를 관리합니다. 후보 모델을 기록하는 것, 검토·승격하는 것, 실제 endpoint에 배포하는 것은 별도 단계입니다. Registry가 있다는 사실만으로 승인 절차나 serving 경로가 자동 완성되지는 않습니다.

## 핵심 개념

| 엔티티 | 의미와 변경 범위 |
|---|---|
| Registered Model | `fraud-detector` 같은 논리적 이름 아래의 버전 모음 |
| Model Version | 이름 아래 발급된 버전 번호와 source 등 기록; 설명·태그·stage/alias 관계는 변경 가능 |
| Alias | 한 버전을 가리키는 변경 가능한 이름; 한 버전에 여러 alias를 연결할 수 있음 |
| LoggedModel | Tracking의 독립 모델 엔티티; Registered Model/Version과 동일하지 않음 |

### Model Version

새 모델 결과는 새 버전으로 등록하는 것이 일반적입니다. 하지만 **Model Version의 모든 필드와 파일이 불변이라는 뜻은 아닙니다.** `update_model_version`으로 설명을 바꾸고 version tag도 수정할 수 있습니다. 외부 `source` URI가 가리키는 파일에 쓰기 권한이 있으면 그 바이트도 바뀔 수 있습니다. Registry 버전 번호가 object immutability나 content hash를 강제하지 않습니다.

`create_model_version`의 `run_id`와 `model_id`는 선택 사항입니다. 직접 source URI로 등록하면 학습 run 연결이 없을 수 있습니다. 등록이 항상 원본의 단순 포인터인지, artifact 복사나 다른 보관 위치를 만드는지는 registry backend와 호출 경로에 따라 확인해야 합니다.

### Alias

`models:/fraud-detector@champion`은 **resolve/load하는 시점**에 alias의 버전을 찾습니다. `models:/fraud-detector/7`은 명시적 버전 참조입니다. Alias를 이동해도 이미 메모리에 로드된 모델이나 캐시가 자동 교체되지는 않습니다. serving controller의 재배포·재로드·캐시 정책을 따로 구현하고 어떤 버전이 실제 서비스 중인지 기록합니다.

`champion`, `challenger`는 팀이 정한 이름입니다. 자체적으로 정식 트래픽·shadow traffic 비율을 설정하거나 평가를 실행하지 않습니다. Alias 변경이 생산 모델의 품질·보안 승인을 증명하지도 않습니다.

### 참고: 레거시 Stage 모델

기존 stage는 `None`, `Staging`, `Production`, `Archived`입니다. `transition_model_version_stage`는 **2.9.0부터 deprecated**이며 3.16.0 API에도 남아 있습니다. 따라서 “이미 모든 버전에서 제거됐다”고 설명하면 안 됩니다. 새 흐름은 alias·tag, 필요하면 환경별 Registered Model과 명시적 권한을 조합합니다. Stage 이름이나 tag 자체는 접근 제어가 아닙니다.

## 모델 등록하기

실제 flavor 모델을 로깅한 뒤 `mlflow.register_model(model_uri, name)`으로 등록하거나, flavor별 `log_model(..., registered_model_name=...)`에 등록 이름을 전달할 수 있습니다. `MlflowClient.create_model_version`으로 source를 직접 지정하는 낮은 수준의 API도 있습니다. 등록과 alias 이동은 별도 작업입니다.

다음은 **Registry metadata 계약만 연습하는 예제**입니다. inference 가능한 모델을 만들지 않습니다. Python 3.12·MLflow 3.16.0·SQLite에서 확인했습니다.

```python
from pathlib import Path
import mlflow
from mlflow import MlflowClient

root = Path(".registry-demo").resolve()
root.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f"sqlite:///{root / 'registry.db'}")
client = MlflowClient()
name = "registry-contract-demo"
# 새 실습 DB에서 한 번 실행합니다. 재실행 전 기존 이름을 확인합니다.
client.create_registered_model(name)
versions = []
for number in (1, 2):
    source = root / f"candidate-{number}"
    source.mkdir(exist_ok=True)
    (source / "metadata.json").write_text('{"fixture": true}')
    versions.append(client.create_model_version(name, source=source.as_uri()))

first, second = versions
assert first.run_id is None
client.update_model_version(name, first.version, description="metadata fixture")
client.set_model_version_tag(name, first.version, "review_state", "demo-only")
client.set_registered_model_alias(name, "champion", first.version)
snapshot = client.get_model_version_by_alias(name, "champion")
client.set_registered_model_alias(name, "champion", second.version)
assert snapshot.version == first.version
assert client.get_model_version_by_alias(name, "champion").version == second.version
```

이 API의 `READY`는 등록 작업 상태입니다. 위처럼 실제 model flavor·가중치가 없는 metadata fixture도 등록되므로, inference 가능성이나 평가 통과를 별도로 검사해야 합니다. `.registry-demo`에는 로컬 DB·fixture가 남습니다.

## 거버넌스와 핸드오프 워크플로우

1. 실제 source artifact, 모델·코드·데이터 hash, dependency와 run/model 참조를 기록합니다.
2. 평가·안전성·업무 기준을 검토하고 승인 증거를 보존합니다.
3. 권한이 있는 주체가 `set_registered_model_alias`로 alias를 변경합니다. 학습 완료가 자동 승인 조건은 아닙니다.
4. serving 시스템이 새 참조를 resolve하고 실제 재로드·배포를 수행합니다. 필요하면 버전 번호와 artifact hash를 고정해 재현성과 rollback을 확보합니다.

후보 생성 권한과 승격 권한을 분리하려면 인증·인가 및 운영 pipeline을 별도로 구성해야 합니다. `review_state=approved` 같은 tag만으로는 쓰기 권한을 제한하거나 승인 근거를 위조할 수 없게 만들지 못합니다. 동시에 alias를 변경하는 여러 배포 작업의 순서도 조정해야 합니다.

![소비자가 champion과 challenger 별칭을 조회해 각 Model Version 참조를 얻는 구조. 별칭 조회는 트래픽 라우팅이나 이미 로드된 모델의 자동 교체를 수행하지 않는다.](../../.gitbook/assets/ko-ai-ml-mlflow-02-model-registry-0.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-mlflow-02-model-registry-0.html)

## 모델 계보와 재현성

계보는 기록하고 보존한 정보만큼만 유효합니다. `run_id`·`model_id`가 없거나 코드 revision·dataset hash를 기록하지 않았으면 Registry가 나중에 복원해 주지 않습니다. 원본 파일 변경, Run/Model Version 삭제, artifact 정리로 연결이 불완전해질 수도 있습니다.

감사에는 실제 서비스 중인 version/model ID, artifact hash와 보관 위치, source code commit, 데이터 snapshot, dependency, 평가·승인 기록이 필요합니다. Metadata DB와 artifact store의 백업·보존 정책을 함께 운영합니다. Alias는 변경 이력을 설명하는 영구 감사 로그를 대신하지 않습니다.

## 다음 단계

[Part 3: EKS 배포](03-eks-deployment.md)에서 서버·DB·artifact 권한 경계를 다룹니다.

## 공식 근거

- [Model Registry](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [3.16.0 Registry client API](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [ModelVersion 필드](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [OSS SQL registry 구현](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[메인 페이지](README.md) · [퀴즈](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
