# MLflow Tracking 퀴즈

이 퀴즈는 MLflow Tracking의 핵심 개념, MLflow 3에서 모델이 1급 엔티티로 바뀐 변화, 오토로깅, GenAI 트레이싱, backend store와 artifact store의 구분에 대한 이해도를 테스트합니다.

## 객관식 문제

1. MLflow의 Experiment란 무엇인가요?
   - A) 자신만의 파라미터와 메트릭을 가진, 학습 코드의 단일 실행
   - B) 이름이 붙은 Run들의 모음
   - C) MLflow의 메타데이터를 저장하는 데이터베이스
   - D) 직렬화된 모델 파일

<details>

<summary>정답 보기</summary>

**정답: B) 이름이 붙은 Run들의 모음**

**설명:**
Experiment는 보통 프로젝트 하나 또는 반복 실험 중인 모델 하나에 대응하는, 이름이 붙은 Run들의 모음입니다. 자신만의 파라미터, 메트릭, 태그, 아티팩트를 가진 학습 코드의 단일 실행은 Run이라는 별개의 개념입니다(A는 Run에 대한 설명).
</details>

2. MLflow 1.x/2.x의 run 중심 모델에서, 기록된 모델은 일반적으로 어떻게 표현되었나요?
   - A) 어떤 run과도 독립적인 `LoggedModel` 엔티티로
   - B) 그 모델을 만들어낸 Run 아래에 종속된 아티팩트로
   - C) backend store의 메트릭 테이블에 있는 행으로
   - D) 독립적인 experiment로

<details>

<summary>정답 보기</summary>

**정답: B) 그 모델을 만들어낸 Run 아래에 종속된 아티팩트로**

**설명:**
MLflow 3 이전에는 기록된 모델이 run의 아티팩트 디렉터리 안에 저장되는 또 하나의 아티팩트일 뿐이었습니다. 모델을 찾으려면 먼저 그 모델을 만들어낸 run을 찾아야 했습니다. MLflow 3는 `LoggedModel`을 독립적인 1급 엔티티로 도입해 이 구조를 바꿨습니다.
</details>

3. MLflow 3의 `LoggedModel` 엔티티가 가능하게 만든, 이전의 run 종속형 모델에는 없던 핵심 기능은 무엇인가요?
   - A) 활성화된 `mlflow.start_run()` 컨텍스트 없이 `mlflow.sklearn.log_model(...)`을 직접 호출하는 것
   - B) tracking 서버 없이 메트릭을 기록하는 것
   - C) Python 없이 학습 코드를 실행하는 것
   - D) artifact store 없이 아티팩트를 저장하는 것

<details>

<summary>정답 보기</summary>

**정답: A) 활성화된 `mlflow.start_run()` 컨텍스트 없이 `mlflow.sklearn.log_model(...)`을 직접 호출하는 것**

**설명:**
`LoggedModel`이 Run과 별개인 1급 엔티티가 되었기 때문에, 더 이상 추적을 위해 활성화된 run 아래에 종속될 필요가 없습니다. 이로써 모델의 버저닝과 비교가 특정 학습 run 하나에 묶이지 않게 됩니다.
</details>

4. `mlflow.autolog()`는 무엇을 하나요?
   - A) 학습된 모델을 서빙 엔드포인트에 자동으로 배포한다
   - B) 지원되는 ML 라이브러리를 계측하여, 수동 로깅 호출 없이도 학습 중 파라미터·메트릭·아티팩트가 자동으로 기록되게 한다
   - C) 저장 공간을 절약하기 위해 오래된 run을 자동으로 삭제한다
   - D) Run을 LoggedModel로 변환한다

<details>

<summary>정답 보기</summary>

**정답: B) 지원되는 ML 라이브러리를 계측하여, 수동 로깅 호출 없이도 학습 중 파라미터·메트릭·아티팩트가 자동으로 기록되게 한다**

**설명:**
오토로깅은 지원되는 프레임워크에 대해 일반적인 학습 데이터를 자동으로 기록합니다. MLflow는 scikit-learn, PyTorch처럼 프레임워크별 오토로그 함수도 제공하므로, 감지된 모든 프레임워크가 아니라 특정 라이브러리 하나에만 오토로깅을 적용할 수도 있습니다.
</details>

5. MLflow 3의 "트레이싱(tracing)"은 주로 무엇을 위해 사용되나요?
   - A) 전통적인 scikit-learn 학습 run의 파라미터와 메트릭을 기록하기 위해
   - B) LLM·에이전트 호출의 내부 단계(span), 토큰 사용량, 비용을 기록해 GenAI 관찰성을 제공하기 위해
   - C) artifact store의 디스크 사용량을 추적하기 위해
   - D) Experiments/Runs 화면을 완전히 대체하기 위해

<details>

<summary>정답 보기</summary>

**정답: B) LLM·에이전트 호출의 내부 단계(span), 토큰 사용량, 비용을 기록해 GenAI 관찰성을 제공하기 위해**

**설명:**
트레이싱은 LLM 또는 에이전트 호출을 span들의 트리 구조로 기록하며, 각 span은 검색 호출이나 도구 호출 같은 한 단계를 나타내고 토큰 사용량과 비용도 함께 기록됩니다. 이는 별도의 도구 없이 MLflow Tracking 자체의 핵심 기능으로 GenAI·에이전트 관찰성을 확장한 것입니다.
</details>

6. LangChain과 함께 MLflow가 자동 트레이싱 연동을 제공하는 프레임워크의 예로 올바른 것은 무엇인가요?
   - A) Kubernetes
   - B) PostgreSQL
   - C) PydanticAI
   - D) Terraform

<details>

<summary>정답 보기</summary>

**정답: C) PydanticAI**

**설명:**
MLflow는 LangChain을 포함한 널리 쓰이는 LLM·에이전트 프레임워크에 대한 자동 계측을 제공하며, PydanticAI, smolagents 같은 프레임워크를 위한 새로운 자동 트레이싱 연동도 추가되고 있습니다.
</details>

7. Backend store가 팀 규모에서 일반적으로 PostgreSQL, MySQL 같은 실제 관계형 데이터베이스를 필요로 하는 이유는 무엇인가요?
   - A) 데이터베이스가 객체 스토리지보다 대용량 모델 파일을 더 잘 처리하기 때문에
   - B) 파라미터, 메트릭, 태그, run/experiment/model 레코드 같은 구조화된 메타데이터를 저장하며, 간단한 로컬 실험 수준을 넘어서면 데이터베이스가 유리하기 때문에
   - C) MLflow가 UI를 렌더링하는 데 SQL 데이터베이스를 요구하기 때문에
   - D) 객체 스토리지는 어떤 메타데이터도 전혀 저장할 수 없기 때문에

<details>

<summary>정답 보기</summary>

**정답: B) 파라미터, 메트릭, 태그, run/experiment/model 레코드 같은 구조화된 메타데이터를 저장하며, 간단한 로컬 실험 수준을 넘어서면 데이터베이스가 유리하기 때문에**

**설명:**
Backend store는 구조화된 메타데이터를 저장하며, 이는 관계형 데이터베이스가 처리하기 좋은 작고 구조화된 쓰기·조회 작업에 해당합니다. 반대로 artifact store는 대용량 바이너리 객체를 저장하며 보통 S3 호환 버킷 같은 객체 스토리지를 사용합니다.
</details>

8. 학습 스크립트 -> Tracking API -> tracking 서버 -> backend store + artifact store로 이어지는 흐름에서, Tracking UI는 무엇을 하나요?
   - A) 학습 스크립트가 실행되는 로컬 디스크에 직접 데이터를 기록한다
   - B) backend store와 artifact store를 모두 조회해 experiment, run, logged model, trace를 화면에 표시한다
   - C) tracking 서버를 거치지 않고 backend store만 직접 조회한다
   - D) 메타데이터는 절대 표시하지 않고 아티팩트만 표시한다

<details>

<summary>정답 보기</summary>

**정답: B) backend store와 artifact store를 모두 조회해 experiment, run, logged model, trace를 화면에 표시한다**

**설명:**
학습 스크립트는 오직 Tracking API와만 통신하며, tracking 서버가 메타데이터 쓰기는 backend store로, 파일 쓰기는 artifact store로 라우팅합니다. UI는 필요한 모든 정보를 표시하기 위해 두 저장소를 모두 조회합니다.
</details>

## 단답형 문제

9. MLflow 3가 `LoggedModel`과 그에 연관된 run, trace, 프롬프트, 평가 메트릭 사이의 계보(lineage)를 추적하는 것이 실무적으로 어떤 이점을 주나요?

<details>

<summary>정답 보기</summary>

**정답: 모델이 더 이상 자신을 학습시킨 단 하나의 run에 영구히 묶이지 않으며, 모델을 학습시킨 run, 그 모델을 평가한 run들, 그 모델을 서빙하며 생성된 trace들과 각각 연결될 수 있습니다.**

**설명:**
`LoggedModel`이 특정 run 아래에 종속된 파일이 아니라 1급 엔티티가 되었기 때문에, MLflow 3는 모델과 그에 연관된 모든 것 사이의 관계를 더 풍부하게 표현할 수 있습니다. 이는 같은 모델을 여러 run에 걸쳐 반복 개선하거나, 기존 LLM을 커스텀 로직으로 감싸는 것처럼 전통적인 학습 루프 밖에서 모델이 만들어지는 경우에 특히 중요합니다.
</details>

10. MLflow가 전통적인 ML 실험 추적과 GenAI·에이전트 관찰성을 별도의 두 도구가 아니라 하나의 시스템으로 다루는 이유는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: MLflow 3가 동일한 Tracking 시스템(및 UI)을 확장해 두 영역을 모두 다루도록 했기 때문입니다 — GenAI·에이전트 호출을 위한 트레이싱은 전통적인 학습 run의 파라미터·메트릭·아티팩트와 동일한 tracking 서버, UI, 계보 모델을 사용합니다.**

**설명:**
전통적인 ML 학습과 LLM·에이전트 개발을 모두 하는 팀은, GenAI 쪽을 위한 별도의 관찰성 도구를 따로 구축하지 않고 하나의 MLflow Tracking 배포로 두 영역을 모두 다룰 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/mlflow/01-tracking.md) | [다음 퀴즈: Model Registry](./02-model-registry-quiz.md)
