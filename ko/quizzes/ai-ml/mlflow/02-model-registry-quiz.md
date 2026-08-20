# MLflow Model Registry 퀴즈

이 퀴즈는 MLflow Model Registry, 즉 Registered Model, Model Version, alias, 그리고 등록이 Tracking과 어떻게 연결되는지에 대한 이해를 테스트합니다.

## 객관식 문제

1. MLflow의 Registered Model이란 무엇인가요?
   - A) 학습 Run의 메트릭 스냅샷
   - B) 특정 Run 하나에 종속되지 않는 안정적인 정체성을 모델에 부여하는, 이름이 붙은 버전 관리된 모델 버전들의 모음
   - C) 모델 아티팩트로부터 빌드된 컨테이너 이미지
   - D) 트래킹 서버 데이터베이스의 저장된 복사본

<details>

<summary>정답 보기</summary>

**정답: B) 특정 Run 하나에 종속되지 않는 안정적인 정체성을 모델에 부여하는, 이름이 붙은 버전 관리된 모델 버전들의 모음**

**설명:**
Registered Model은 이름(예: `fraud-detector`)으로 식별되며, 생애 동안 Model Version, alias, 태그, 설명이 계속 축적됩니다. "이 모델"이 특정 학습 Run이나 Experiment보다 더 오래 지속되는 정체성을 갖도록 하기 위해 존재합니다.
</details>

2. Model Version은 한 번 생성되고 나면 어떻게 되나요?
   - A) 모델이 개선될 때마다 그 자리에서 수정할 수 있다
   - B) 불변이다 — 새로운 학습 결과는 기존 버전의 수정이 아니라 새로운 버전이 된다
   - C) 30일 후 자동으로 삭제된다
   - D) 같은 이름 아래 다음에 등록되는 버전과 병합된다

<details>

<summary>정답 보기</summary>

**정답: B) 불변이다 — 새로운 학습 결과는 기존 버전의 수정이 아니라 새로운 버전이 된다**

**설명:**
각 Model Version은 번호가 매겨지며(version 1, version 2 등) 한 번 등록되면 변경되지 않습니다. 새로운 후보 모델은 항상 같은 Registered Model 이름 아래의 새로운 버전이 됩니다.
</details>

3. Model Version이 Tracking(Part 1)과의 연결을 위해 유지하는 것은 무엇인가요?
   - A) 레지스트리 내부에 저장된 학습 데이터셋의 복사본
   - B) 그 버전이 유래한 `LoggedModel` 또는 Run으로의 참조
   - C) 클러스터 노드 구성의 스냅샷
   - D) 없음 — Model Version은 Tracking과 완전히 독립적이다

<details>

<summary>정답 보기</summary>

**정답: B) 그 버전이 유래한 `LoggedModel` 또는 Run으로의 참조**

**설명:**
모든 Model Version은 자신을 만들어낸 Run(그리고 Part 1에서 다룬 `LoggedModel` 엔티티)을 다시 가리킵니다. 이 참조가 있기 때문에 모델 계보와 재현성이 가능해집니다.
</details>

4. MLflow Model Registry에서 alias란 무엇인가요?
   - A) 모델 생성 시 부여되어 영구히 변하지 않는 라벨
   - B) `champion`이나 `challenger`처럼 특정 Model Version을 가리키는, 변경 가능한 이름이 붙은 포인터
   - C) 트래킹 서버 URL의 축약형
   - D) Registered Model 이름의 동의어

<details>

<summary>정답 보기</summary>

**정답: B) `champion`이나 `challenger`처럼 특정 Model Version을 가리키는, 변경 가능한 이름이 붙은 포인터**

**설명:**
버전 번호와 달리 alias는 시간이 지나면서 다른 Model Version을 가리키도록 옮길 수 있습니다. 예를 들어 새 버전이 평가를 통과한 뒤 `champion`을 version 4에서 version 7로 다시 가리키게 할 수 있습니다.
</details>

5. 현재 MLflow에서 alias가 기존의 stage 기반 라이프사이클 모델(Staging/Production/Archived)을 대체하게 된 이유는 무엇인가요?
   - A) 어떤 버전의 MLflow에서도 stage는 더 이상 지원되지 않는다
   - B) alias가 더 유연하다 — 하나의 버전이 여러 alias를 가질 수도(또는 하나도 갖지 않을 수도) 있고, alias 이름이 고정된 라이프사이클 라벨 집합에 묶이지 않는다
   - C) alias는 stage보다 디스크 공간을 적게 사용한다
   - D) stage는 API로 조회할 수 없었다

<details>

<summary>정답 보기</summary>

**정답: B) alias가 더 유연하다 — 하나의 버전이 여러 alias를 가질 수도(또는 하나도 갖지 않을 수도) 있고, alias 이름이 고정된 라이프사이클 라벨 집합에 묶이지 않는다**

**설명:**
stage 모델은 모든 버전을 고정된 라벨 집합(`Staging`, `Production`, `Archived`) 중 하나에 묶었습니다. alias와 태그를 조합하면 더 유연하고 커스텀한 이름 지정이 가능하고, 하나의 버전이 동시에 여러 alias를 가질 수도 있습니다. 오래된 MLflow 배포 환경에서는 여전히 stage 모델을 볼 수 있지만, 이는 지금은 지양되는 레거시 방식입니다.
</details>

6. 다음 중 모델을 로깅하는 것과 동시에 새로운 Model Version을 생성하는 방법은 무엇인가요?
   - A) 로깅 후 `mlflow.register_model(model_uri, name)`을 호출하는 것
   - B) 플레이버별 `log_model` 호출에 `registered_model_name`을 전달하는 것
   - C) 모델 파일을 트래킹 서버의 아티팩트 스토어에 직접 복사하는 것
   - D) 기존 Model Version에 태그를 설정하는 것

<details>

<summary>정답 보기</summary>

**정답: B) 플레이버별 `log_model` 호출에 `registered_model_name`을 전달하는 것**

**설명:**
`mlflow.sklearn.log_model(..., registered_model_name="fraud-detector")`와 같이 `registered_model_name`을 넘기면 모델을 로깅하는 동일한 호출 안에서 새로운 Model Version이 등록됩니다. `mlflow.register_model(model_uri, name)`은 이전 단계에서 이미 로깅된 모델을 나중에 등록하는 대안적인 경로입니다.
</details>

7. 일반적인 거버넌스 워크플로우에서 `champion` alias를 새 버전으로 옮기는 것은 무엇인가요?
   - A) Run이 끝나는 즉시 학습 스크립트가 자동으로 옮긴다
   - B) 평가 또는 승인 프로세스 — 흔히 CI/CD 파이프라인의 일부 — 가 후보 버전이 게이트를 통과한 뒤에만 옮긴다
   - C) 서빙 시스템이 `models:/fraud-detector@champion`을 처음 resolve할 때 옮긴다
   - D) MLflow가 버전 번호가 더 높다는 이유로 자동으로 옮긴다

<details>

<summary>정답 보기</summary>

**정답: B) 평가 또는 승인 프로세스 — 흔히 CI/CD 파이프라인의 일부 — 가 후보 버전이 게이트를 통과한 뒤에만 옮긴다**

**설명:**
레지스트리의 거버넌스 가치는 "후보를 만드는 것"과 "후보를 승격하는 것"을 분리하는 데서 나옵니다. `champion` alias를 옮기는 것은 의도적인 행위이며, 보통 평가 기준 통과를 조건으로 승인 파이프라인에서 자동화됩니다.
</details>

8. 서빙 시스템이 `models:/fraud-detector/7` 대신 `models:/fraud-detector@champion`을 resolve할 때 얻는 이점은 무엇인가요?
   - A) 더 빠른 추론 지연 시간
   - B) 코드 변경 없이 현재 `champion` alias를 가진 버전을 자동으로 가져오는 안정적인 참조
   - C) 다른 트래킹 서버에 대한 접근 권한
   - D) 모델의 자동 재학습

<details>

<summary>정답 보기</summary>

**정답: B) 코드 변경 없이 현재 `champion` alias를 가진 버전을 자동으로 가져오는 안정적인 참조**

**설명:**
alias 기반 URI는 모델을 소비하는 쪽을 특정 버전 번호로부터 분리시킵니다. `champion`이 새로 검증된 버전으로 다시 가리켜지면, 그 URI에 대한 다음 resolve는 자연스럽게 새 버전을 가져옵니다.
</details>

## 서술형 문제

9. Model Version과 alias의 차이를 설명하고, 이 차이가 서빙 시스템에 왜 중요한지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Model Version은 불변이며 번호가 매겨집니다 — 한 번 생성되면 변경되지 않고, 새로운 학습 결과는 항상 기존 버전의 수정이 아니라 새로운 버전이 됩니다. alias는 변경 가능합니다 — `champion`이나 `challenger`처럼 이름이 붙은 포인터이며 언제든 다른 Model Version을 가리키도록 다시 지정할 수 있습니다.

이 차이는 서빙 시스템에 중요합니다. 서빙 시스템은 하드코딩된 버전 번호 대신 `models:/fraud-detector@champion`과 같은 안정적인 이름을 한 번만 작성해두면 되기 때문입니다. alias가 새로 승인된 버전으로 옮겨지면, 서빙 시스템은 다음 resolve 시점에 자동으로 그 변경을 반영하며, 별도의 코드나 설정 변경이 필요하지 않습니다.
</details>

10. "지금 프로덕션에서 서빙 중인 모델을 정확히 어떤 코드와 데이터가 만들었는가"와 같은 감사(audit) 질문을 Model Version의 계보가 어떻게 지원하는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
각 Model Version은 자신을 만들어낸 Run(그리고 Part 1에서 다룬 기반이 되는 `LoggedModel`)으로의 참조를 유지합니다. 이 연결을 따라가면 — `champion` alias에서 그것이 가리키는 Model Version으로, 그 버전에서 다시 원본 Run으로 — Tracking 과정에서 그 Run이 기록한 파라미터, 코드 참조, 데이터셋 정보에 도달하게 됩니다.

Model Version이 불변이고 이 계보 연결이 결코 끊어지지 않기 때문에, 감사자는 별도의 기록이나 팀의 기억에 의존하지 않고도 현재 `champion`으로 alias된 모델을 정확히 그것을 만들어낸 학습 Run까지 추적할 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/mlflow/02-model-registry.md) | [다음 퀴즈: EKS Deployment](./03-eks-deployment-quiz.md)
