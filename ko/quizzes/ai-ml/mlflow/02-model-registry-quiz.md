# MLflow Model Registry 퀴즈

## 객관식 문제

1. Registered Model은 무엇인가요?
   - A) GPU endpoint
   - B) 논리적 이름 아래의 Model Version 모음
   - C) 학습 데이터 복사본
   - D) 한 번의 run만 허용하는 기록

<details>
<summary>정답 보기</summary>

**정답: B**

예를 들어 fraud-detector라는 이름 아래 여러 버전과 alias를 관리합니다.
</details>

2. Model Version의 변경 범위에 대한 정확한 설명은?
   - A) 모든 필드와 source 파일 바이트가 영구 불변이다
   - B) 버전 번호를 얻지만 설명·태그는 수정할 수 있고 외부 파일 보존은 별도다
   - C) 모든 버전은 30일 후 자동 삭제된다
   - D) 모든 새 모델은 기존 버전으로 합쳐진다

<details>
<summary>정답 보기</summary>

**정답: B**

새 결과를 새 버전으로 관리하는 관행과 저장소의 실제 immutability를 구분합니다.
</details>

3. 모든 Model Version에 학습 run 연결이 존재하나요?
   - A) 항상 존재하며 삭제도 불가능하다
   - B) model_id가 있으면 데이터 snapshot도 자동 보관된다
   - C) 아니다. create_model_version의 run_id/model_id는 선택 사항이다
   - D) Registry는 원본 연결을 전혀 지원하지 않는다

<details>
<summary>정답 보기</summary>

**정답: C**

직접 source URI로 등록할 수 있습니다. 완전한 계보는 별도 기록과 보존이 필요합니다.
</details>

4. Alias는 무엇인가요?
   - A) 여러 버전을 동시에 하나의 트래픽 비율로 묶는 장치
   - B) 한 버전을 가리키는 변경 가능한 이름
   - C) 고정된 DB 주소
   - D) 수정 불가능한 hash

<details>
<summary>정답 보기</summary>

**정답: B**

한 버전에 여러 alias를 연결할 수 있으며 alias를 다른 버전으로 옮길 수 있습니다.
</details>

5. 레거시 stage API의 상태는?
   - A) 2.9.0부터 deprecated이지만 3.16.0에도 남아 있다
   - B) 모든 MLflow 버전에서 제거됐다
   - C) alias와 같은 접근 제어 정책이다
   - D) 오직 Production만 지원한다

<details>
<summary>정답 보기</summary>

**정답: A**

기존 stage는 None/Staging/Production/Archived입니다. 새 흐름은 alias/tag와 명시적 권한을 설계합니다.
</details>

6. 모델 로깅과 함께 등록하려면 무엇을 사용하나요?
   - A) tag만 설정한다
   - B) flavor log_model의 registered_model_name
   - C) alias를 삭제한다
   - D) 파일 이름을 champion으로 바꾼다

<details>
<summary>정답 보기</summary>

**정답: B**

로그 후 register_model을 호출하는 별도 경로도 있습니다. 등록 자체는 alias 이동이 아닙니다.
</details>

7. champion 승격을 제어하려면 무엇이 필요한가요?
   - A) 가장 높은 버전이면 MLflow가 자동 승인
   - B) review_state tag만 있으면 권한 분리 완료
   - C) 평가·승인 증거와 변경 주체의 인증·인가
   - D) 모든 학습자가 무조건 alias 변경

<details>
<summary>정답 보기</summary>

**정답: C**

태그 문자열은 승인 절차나 접근 제어를 대신하지 않습니다.
</details>

8. Alias 변경 직후 이미 메모리에 로드된 모델은 어떻게 되나요?
   - A) 항상 즉시 교체된다
   - B) 자동 재학습된다
   - C) shadow traffic이 자동 생긴다
   - D) 별도 재로드/배포/캐시 정책 없이는 이전 모델을 계속 사용할 수 있다

<details>
<summary>정답 보기</summary>

**정답: D**

새 resolve와 이미 로드된 인스턴스의 수명주기는 다릅니다.
</details>

## 서술형 문제

9. READY 상태만으로 모델의 inference 가능성과 품질을 증명할 수 있나요?

<details>
<summary>정답 보기</summary>

아닙니다. 등록 상태이며 metadata fixture도 READY가 될 수 있습니다. 실제 flavor·가중치·의존성 로딩과 품질 검증이 별도로 필요합니다.
</details>

10. Registry만으로 정확한 코드·데이터 계보가 항상 복원되지 않는 이유는?

<details>
<summary>정답 보기</summary>

run/model 참조가 선택 사항이고 source 파일·Run·artifact가 변경되거나 삭제될 수 있습니다. 서비스 중인 버전·hash·commit·dataset snapshot·dependency·승인 기록을 보존해야 합니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/mlflow/02-model-registry.md)
