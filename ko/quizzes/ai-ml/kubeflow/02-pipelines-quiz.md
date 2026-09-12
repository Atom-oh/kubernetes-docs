# Kubeflow Pipelines 퀴즈

이 퀴즈는 Kubeflow Pipelines의 아키텍처, KFP v2의 IR YAML 컴파일 모델, 핵심 개념(Pipeline, Component, Run, Experiment, Artifact, MLMD), EKS에서의 아티팩트 저장소 고려사항, 캐싱 동작에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 이 장의 오픈소스 KFP 2.16.1 백엔드가 워크플로 순서와 Pod 생성을 관리하는 데 사용하는 엔진은 무엇인가요?
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) 별도의 워크플로 엔진 없이 Kubernetes CronJob을 직접 사용

<details>

<summary>정답 보기</summary>

**정답: B) Argo Workflows**

**설명:**
이 장의 백엔드는 Run을 실행할 때 IR을 Argo Workflow로 변환합니다. Argo가 실행 순서와 Pod 생성을 관리하고 Kubernetes 스케줄러가 노드 배치를 담당합니다. 업로드만으로 Run이 생성되지는 않습니다.
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
v1 SDK의 `dsl-compile`은 Argo에 특화된 `Workflow` YAML 매니페스트를 직접 생성했습니다. v2 SDK는 DAG, 컴포넌트, 타입이 지정된 아티팩트를 기술하는 백엔드 종속적이지 않은 IR YAML(`PipelineSpec`)로 컴파일하며, 이 장의 백엔드가 Run 생성 시 IR을 Argo `Workflow`로 변환하며, 백엔드 버전·플랫폼 확장 호환성이 필요합니다.
</details>

3. 등록된 실행과 입출력 아티팩트 관계를 기록하여 KFP UI에서 리니지 추적을 가능하게 하는 컴포넌트는 무엇인가요?
   - A) Argo Workflow 컨트롤러
   - B) ML Metadata(MLMD) 저장소
   - C) MinIO 아티팩트 저장소
   - D) KFP SDK 컴파일러

<details>

<summary>정답 보기</summary>

**정답: B) ML Metadata(MLMD) 저장소**

**설명:**
MLMD는 등록된 실행과 아티팩트의 관계를 저장합니다. 파일 바이트, 모든 외부 부작용, 코드·데이터 무결성을 자동 기록한다는 뜻은 아닙니다. 재현성에는 리비전과 해시 기록이 필요합니다.
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
KFP v2는 아티팩트에 `Dataset`, `Model`, `Metrics` 등 1급 타입을 부여합니다. `Output[Dataset]` 타입의 컴포넌트 파라미터는 SDK에 타입과 연결을 선언합니다. SDK는 호환되는 `Input[Dataset]` 입력과 그래프 연결을 기록하고 실행 환경이 경로·전송을 처리합니다.
</details>

5. 검토한 기본 설치의 MinIO 대신 S3를 사용하려면 무엇이 필요한가요?
   - A) 기본값은 S3이며, 패턴은 이를 MinIO로 바꾼다
   - B) 기본 설치의 MinIO와 별도로 파이프라인 루트, provider, 자격 증명 체인을 S3에 맞게 구성한다
   - C) 기본 아티팩트 저장소는 없으며 항상 수동으로 설정해야 한다
   - D) 기본값은 EFS이며, 패턴은 이를 EBS로 바꾼다

<details>

<summary>정답 보기</summary>

**정답: B) 기본 설치의 MinIO와 별도로 파이프라인 루트, provider, 자격 증명 체인을 S3에 맞게 구성한다**

**설명:**
기본 설치에 MinIO가 포함되어도 모든 배포·URI의 저장소가 같지는 않습니다. 현재 KFP 저장소 가이드로 S3 설정을 확인해야 합니다. S3는 저장·요청·전송 등에 요금이 발생하며, 오래된 AWS 배포판 가이드가 현재 버전의 검증된 설치법은 아닙니다.
</details>

6. KFP의 아티팩트 저장소를 클러스터 내부 MinIO 대신 S3로 연결할 때, 실제 Run의 파이프라인 실행 ServiceAccount와 아티팩트 접근 컴포넌트에 직접적으로 관련되는 신원(identity) 메커니즘은 무엇인가요?
   - A) 없음 — AWS 신원 설정 없이도 S3 접근이 가능하다
   - B) 실제 SDK·신뢰·런타임 조건을 충족한 IRSA 또는 Pod Identity로 S3 권한을 구성한다
   - C) 모든 컴포넌트의 컨테이너 이미지에 하드코딩된 AWS 액세스 키
   - D) S3 접근에는 Kubernetes RBAC만으로 충분하다

<details>

<summary>정답 보기</summary>

**정답: B) 실제 SDK·신뢰·런타임 조건을 충족한 IRSA 또는 Pod Identity로 S3 권한을 구성한다**

**설명:**
현재 KFP 가이드는 IRSA를 설명합니다. 실제 실행 계정과 API 서버 등의 접근도 확인하고, Pod Identity는 에이전트·association·SDK·지원 환경을 검증해야 합니다. ServiceAccount 이름이나 annotation만으로 권한이 완성되지는 않습니다.
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
   - B) 컴포넌트의 입력(파라미터 값, 입력 아티팩트 이름/ID, 컨테이너 이미지·명령과 출력 스펙 등)을 해시로 만들고, 이전에 성공한 실행과 해시가 일치하면 캐시된 출력을 재사용한다
   - C) 파이프라인 이름이 바뀐 경우에만 컴포넌트를 다시 실행한다
   - D) 캐싱은 마지막 실행 이후 경과한 실제 시간에만 기반한다

<details>

<summary>정답 보기</summary>

**정답: B) 컴포넌트의 입력(파라미터 값, 입력 아티팩트 이름/ID, 컨테이너 이미지·명령과 출력 스펙 등)을 해시로 만들고, 이전에 성공한 실행과 해시가 일치하면 캐시된 출력을 재사용한다**

**설명:**
2.16.1은 입력 파라미터·아티팩트 ID와 컨테이너 스펙 등으로 키를 만들며 파일 바이트를 직접 해시하지 않습니다. 이후 실행에서 일치하는 입력 해시를 가진 컴포넌트를 제출하면 재실행을 건너뛰고 이전에 캐시된 출력을 재사용합니다.

파일 내용, 변경 가능한 이미지 태그, 외부 상태는 자동으로 무효화 근거가 되지 않습니다. 데이터 버전·해시를 명시적 입력으로 기록하거나 캐싱을 끄세요.
</details>

## 단답형 문제

9. 이 장에서 설명한, KFP의 캐싱 동작을 비활성화하는 두 가지 방법을 쓰세요.

<details>

<summary>정답 보기</summary>

**정답: 컴포넌트 단위로는 태스크에 `set_caching_options(enable_caching=False)`를 호출하고, Run 단위로는 인증된 클라이언트의 `enable_caching=False`를 사용한다.**

**설명:**
`prep_task.set_caching_options(enable_caching=False)`는 파이프라인 함수 안의 특정 컴포넌트 태스크에 대해서만 캐싱을 비활성화합니다. 반면 파이프라인 제출 전체에 대한 캐싱은 컴포넌트별로가 아니라 Run 제출 시점에 한 번에 비활성화할 수 있습니다.
</details>

10. KFP SDK의 컴파일 단계는 실제로 무엇을 생성하며, 그 결과물이 KFP API 서버에 도달한 이후에는 어떤 일이 일어나나요?

<details>

<summary>정답 보기</summary>

**정답: 백엔드에 종속되지 않는 `PipelineSpec`인 중간 표현(IR) YAML을 생성합니다. 업로드 후 Run이 생성되면 백엔드가 이 IR YAML을 Argo `Workflow`로 변환하고, Argo가 Pod 생성을 관리하고 Kubernetes가 노드에 배치합니다.**

**설명:**
컴파일은 IR을 만들며 KFP 패키지는 클라이언트 API와 Python 런타임 지원도 제공합니다. Run 생성 후 백엔드가 Argo Workflow를 만들고 Kubernetes 스케줄러가 Pod를 노드에 배치합니다. 백엔드의 IR 버전과 플랫폼 확장 호환성을 확인해야 합니다.
</details>

## 실습 문제

11. `Output[Dataset]` 파라미터 하나를 선언하고 pandas DataFrame을 CSV로 기록하는 `prepare_data`라는 이름의 `@dsl.component` 함수를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.12-slim", packages_to_install=["pandas==2.3.3"])
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**설명:**
`output_dataset: Output[Dataset]`은 타입이 지정된 아티팩트 출력을 선언합니다. 컴파일러는 출력 타입을 기록하고 런타임이 `output_dataset.path`를 준비하며, 다운스트림 컴포넌트는 이를 `Input[Dataset]`으로 선언해 받을 수 있습니다.
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
파이프라인 함수 안의 태스크 객체에 `set_caching_options(enable_caching=False)`를 호출하면 컴파일된 해당 태스크의 캐싱을 끕니다. Run 제출 시 명시적인 enable_caching 값으로 덮어쓸 수 있으므로, 이 설정을 유지하려면 Run 옵션을 None으로 두세요.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/kubeflow/02-pipelines.md) | [다음 퀴즈: Notebooks](./03-notebooks-quiz.md)
