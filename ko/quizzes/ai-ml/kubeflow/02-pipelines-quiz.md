# Kubeflow Pipelines 퀴즈

이 퀴즈는 Kubeflow Pipelines의 아키텍처, KFP v2의 IR YAML 컴파일 모델, 핵심 개념(Pipeline, Component, Run, Experiment, Artifact, MLMD), EKS에서의 아티팩트 저장소 고려사항, 캐싱 동작에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubeflow Pipelines 백엔드가 파이프라인 단계의 Pod를 실제로 스케줄링하고 실행하기 위해 내부적으로 사용하는 워크플로 엔진은 무엇인가요?
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) 별도의 워크플로 엔진 없이 Kubernetes CronJob을 직접 사용

<details>

<summary>정답 보기</summary>

**정답: B) Argo Workflows**

**설명:**
KFP의 백엔드는 Argo Workflows 위에 구축되어 있습니다. 컴파일된 파이프라인이 KFP API 서버에 도달하면 Argo `Workflow` 리소스로 변환되고, Argo의 컨트롤러가 Pod를 생성하고 순서를 조율합니다. KFP는 그 위에 Python SDK, UI, Experiment/Run 추적, MLMD 저장소를 얹습니다.
</details>

2. KFP v1 SDK 컴파일러와 KFP v2 SDK 컴파일러의 핵심적인 아키텍처 차이는 무엇인가요?
   - A) v1은 IR YAML로 컴파일하고, v2는 Argo Workflow YAML로 직접 컴파일한다
   - B) v1은 Argo Workflow YAML로 직접 컴파일하고, v2는 백엔드에 종속되지 않는 중간 표현(IR) YAML로 컴파일한다
   - C) 차이가 없다 — 둘 다 동일한 결과물을 생성한다
   - D) v2에서는 컴파일 과정 자체가 완전히 없어졌다

<details>

<summary>정답 보기</summary>

**정답: B) v1은 Argo Workflow YAML로 직접 컴파일하고, v2는 백엔드에 종속되지 않는 중간 표현(IR) YAML로 컴파일한다**

**설명:**
v1 SDK의 `dsl-compile`은 Argo에 특화된 `Workflow` YAML 매니페스트를 직접 생성했습니다. v2 SDK는 DAG, 컴포넌트, 타입이 지정된 아티팩트를 기술하는 백엔드 종속적이지 않은 IR YAML(`PipelineSpec`)로 컴파일하며, KFP 백엔드가 제출 시점에 이 IR을 Argo `Workflow`로 변환합니다.
</details>

3. 모든 컴포넌트 실행과 그 입출력, 관련 아티팩트를 기록하여 KFP UI에서 리니지 추적을 가능하게 하는 컴포넌트는 무엇인가요?
   - A) Argo Workflow 컨트롤러
   - B) ML Metadata(MLMD) 저장소
   - C) MinIO 아티팩트 저장소
   - D) KFP SDK 컴파일러

<details>

<summary>정답 보기</summary>

**정답: B) ML Metadata(MLMD) 저장소**

**설명:**
보통 MySQL 기반으로 동작하는 MLMD는 모든 컴포넌트 실행과 그 입출력, 연관된 아티팩트를 기록합니다. 이 덕분에 KFP UI에서 학습된 모델을 거꾸로 추적해 어떤 데이터셋과 코드로 만들어졌는지 여러 실행에 걸쳐 확인할 수 있습니다.
</details>

4. KFP v2 SDK에서 컴포넌트가 다운스트림 컴포넌트가 소비할 `Dataset` 타입의 아티팩트를 생성한다고 선언하는 방법은 무엇인가요?
   - A) 일반 Python 딕셔너리를 반환한다
   - B) `Output[Dataset]` 타입의 파라미터를 선언한다
   - C) 타입 선언 없이 고정된 `/tmp/dataset.csv` 경로에 파일을 쓴다
   - D) `DATASET`이라는 환경 변수를 설정한다

<details>

<summary>정답 보기</summary>

**정답: B) `Output[Dataset]` 타입의 파라미터를 선언한다**

**설명:**
KFP v2는 아티팩트에 `Dataset`, `Model`, `Metrics` 등 1급 타입을 부여합니다. `Output[Dataset]` 타입의 컴포넌트 파라미터는 SDK에게 저장 경로를 준비하고, 이 아티팩트를 매칭되는 `Input[Dataset]` 파라미터를 선언한 다운스트림 컴포넌트에 연결하도록 지시합니다.
</details>

5. 별도로 재구성하지 않았을 때 KFP의 기본 아티팩트 저장소는 무엇이며, `awslabs/kubeflow-manifests` 프로젝트의 S3 패턴은 이를 어떻게 바꾸나요?
   - A) 기본값은 S3이며, 패턴은 이를 MinIO로 바꾼다
   - B) 기본값은 클러스터 내부에 배포되는 MinIO이며, 패턴은 파이프라인 루트와 아티팩트 저장소 자격 증명을 재구성해 대신 S3를 사용하게 만든다
   - C) 기본 아티팩트 저장소는 없으며 항상 수동으로 설정해야 한다
   - D) 기본값은 EFS이며, 패턴은 이를 EBS로 바꾼다

<details>

<summary>정답 보기</summary>

**정답: B) 기본값은 클러스터 내부에 배포되는 MinIO이며, 패턴은 파이프라인 루트와 아티팩트 저장소 자격 증명을 재구성해 대신 S3를 사용하게 만든다**

**설명:**
KFP는 기본 아티팩트 저장소로 클러스터 내부 MinIO 배포를 함께 제공합니다. EKS에서는 이것이 S3가 이미 무료로 제공하는 기능을 중복으로 구현하는 추가적인 스테이트풀 서비스를 운영해야 한다는 의미입니다. `awslabs/kubeflow-manifests`는 컴포넌트가 S3를 직접 읽고 쓰도록 파이프라인 루트와 아티팩트 자격 증명을 재구성하는 방법을 문서화합니다.
</details>

6. KFP의 아티팩트 저장소를 클러스터 내부 MinIO 대신 S3로 연결할 때, KFP 파이프라인 Pod(예: `pipeline-runner` ServiceAccount)에 직접적으로 관련되는 신원(identity) 메커니즘은 무엇인가요?
   - A) 없음 — AWS 신원 설정 없이도 S3 접근이 가능하다
   - B) IRSA 또는 EKS Pod Identity로, ServiceAccount에 해당 S3 버킷에 대한 권한을 부여한다
   - C) 모든 컴포넌트의 컨테이너 이미지에 하드코딩된 AWS 액세스 키
   - D) S3 접근에는 Kubernetes RBAC만으로 충분하다

<details>

<summary>정답 보기</summary>

**정답: B) IRSA 또는 EKS Pod Identity로, ServiceAccount에 해당 S3 버킷에 대한 권한을 부여한다**

**설명:**
아티팩트 읽기/쓰기가 클러스터 내부 MinIO 엔드포인트가 아니라 곧바로 AWS로 향하게 되면, KFP 파이프라인 Pod가 사용하는 ServiceAccount는 해당 S3 버킷에 대한 권한을 가진 IRSA 역할이나 EKS Pod Identity 연결이 필요합니다.
</details>

7. 예시로 든 2단계 파이프라인(`prepare_data` -> `train_model`)에서 `Dataset` 아티팩트는 첫 번째 컴포넌트에서 두 번째 컴포넌트로 어떻게 전달되나요?
   - A) 두 컴포넌트가 공유하는 전역 변수에 기록한다
   - B) `train_model(input_dataset=prep_task.outputs["output_dataset"])`을 통해 첫 번째 컴포넌트의 선언된 출력을 두 번째 컴포넌트의 타입이 지정된 입력에 연결한다
   - C) 환경 변수에 저장한다
   - D) 두 컴포넌트는 데이터를 공유할 수 없으므로 하나로 합쳐야 한다

<details>

<summary>정답 보기</summary>

**정답: B) `train_model(input_dataset=prep_task.outputs["output_dataset"])`을 통해 첫 번째 컴포넌트의 선언된 출력을 두 번째 컴포넌트의 타입이 지정된 입력에 연결한다**

**설명:**
`@dsl.pipeline`로 데코레이트된 함수 안에서 `prep_task.outputs["output_dataset"]`은 `prepare_data`가 선언한 `Output[Dataset]` 파라미터(이름은 `output_dataset`)를 참조하며, 이를 `train_model`의 `input_dataset: Input[Dataset]` 파라미터에 넘기는 것이 SDK가 독립적으로 실행되는 두 Pod 사이의 아티팩트 의존성을 배선하는 방법입니다.
</details>

8. KFP는 컴포넌트를 다시 실행하는 대신 캐시된 결과를 재사용할지 어떻게 판단하나요?
   - A) 입력과 상관없이 항상 모든 컴포넌트를 다시 실행한다
   - B) 컴포넌트의 입력(파라미터 값, 입력 아티팩트 내용, 컴포넌트 자체의 정의)을 해시로 만들고, 이전에 성공한 실행과 해시가 일치하면 캐시된 출력을 재사용한다
   - C) 파이프라인 이름이 바뀐 경우에만 컴포넌트를 다시 실행한다
   - D) 캐싱은 마지막 실행 이후 경과한 실제 시간에만 기반한다

<details>

<summary>정답 보기</summary>

**정답: B) 컴포넌트의 입력(파라미터 값, 입력 아티팩트 내용, 컴포넌트 자체의 정의)을 해시로 만들고, 이전에 성공한 실행과 해시가 일치하면 캐시된 출력을 재사용한다**

**설명:**
KFP는 컴포넌트의 입력을 해시로 만들어 실행을 캐싱합니다. 이후 실행에서 일치하는 입력 해시를 가진 컴포넌트를 제출하면 재실행을 건너뛰고 이전에 캐시된 출력을 재사용합니다.
</details>

## 단답형 문제

9. 이 장에서 설명한, KFP의 캐싱 동작을 비활성화하는 두 가지 방법을 쓰세요.

<details>

<summary>정답 보기</summary>

**정답: 컴포넌트 단위로는 태스크에 `set_caching_options(enable_caching=False)`를 호출하고, Run 단위로는 KFP UI의 Run 제출 화면에 노출된 캐싱 토글을 사용한다.**

**설명:**
`prep_task.set_caching_options(enable_caching=False)`는 파이프라인 함수 안의 특정 컴포넌트 태스크에 대해서만 캐싱을 비활성화합니다. 반면 파이프라인 제출 전체에 대한 캐싱은 컴포넌트별로가 아니라 Run 제출 시점에 한 번에 비활성화할 수 있습니다.
</details>

10. KFP SDK의 컴파일 단계는 실제로 무엇을 생성하며, 그 결과물이 KFP API 서버에 도달한 이후에는 어떤 일이 일어나나요?

<details>

<summary>정답 보기</summary>

**정답: 백엔드에 종속되지 않는 `PipelineSpec`인 중간 표현(IR) YAML을 생성합니다. API 서버에 도달하면 백엔드가 이 IR YAML을 Argo `Workflow`로 변환하고, Argo의 컨트롤러가 이를 Pod로 스케줄링합니다.**

**설명:**
KFP SDK의 역할은 IR YAML을 생성하는 데서 끝납니다. API 서버 이후의 모든 과정 — Argo Workflow로의 변환과 Pod 스케줄링 — 은 백엔드의 책임이며, 이 구조가 원칙적으로 IR YAML을 백엔드에 종속되지 않게 만드는 이유입니다.
</details>

## 실습 문제

11. `Output[Dataset]` 파라미터 하나를 선언하고 pandas DataFrame을 CSV로 기록하는 `prepare_data`라는 이름의 `@dsl.component` 함수를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.11-slim")
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**설명:**
`output_dataset: Output[Dataset]`은 타입이 지정된 아티팩트 출력을 선언합니다. SDK는 컴포넌트가 쓸 저장 위치로 `output_dataset.path`를 준비하며, 다운스트림 컴포넌트는 이를 `Input[Dataset]`으로 선언해 받을 수 있습니다.
</details>

12. `prepare_data`의 출력을 `train_model` 컴포넌트의 `input_dataset` 파라미터에 연결하는 `@dsl.pipeline` 함수를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```python
from kfp import dsl

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])
```

**설명:**
`prep_task.outputs["output_dataset"]`은 `prepare_data`의 `Output[Dataset]` 파라미터(이름 `output_dataset`)가 생성한 아티팩트를 참조하며, 이를 `train_model`의 `input_dataset` 인자로 넘기면 두 컴포넌트 사이에 DAG 엣지가 생성됩니다.
</details>

13. `prep_task`라는 이름의 파이프라인 태스크에 대해 캐싱을 비활성화하는 코드를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```python
prep_task.set_caching_options(enable_caching=False)
```

**설명:**
파이프라인 함수 안의 태스크 객체에 `set_caching_options(enable_caching=False)`를 호출하면 해당 컴포넌트 실행에 대한 캐싱이 비활성화되어, 이전 실행에서 일치하는 캐시된 결과가 있어도 강제로 다시 실행됩니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/02-pipelines.md) | [다음 퀴즈: Notebooks](./03-notebooks-quiz.md)
