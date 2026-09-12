# MLflow Tracking 퀴즈

## 객관식 문제

1. Experiment와 Run의 관계는 무엇인가요?
   - A) Experiment는 이름 있는 run 모음이며 run은 학습·평가 같은 실행을 표현한다
   - B) Experiment는 GPU 한 대다
   - C) Run은 항상 배포된 모델이다
   - D) 둘은 동일한 엔티티다

<details>
<summary>정답 보기</summary>

**정답: A**

Run은 전처리·평가·비교 작업도 기록할 수 있습니다.
</details>

2. 새 MLflow 3.16.0 환경의 기본 metadata backend는 무엇인가요?
   - A) S3 bucket
   - B) sqlite:///mlflow.db
   - C) 브라우저 localStorage
   - D) 반드시 PostgreSQL

<details>
<summary>정답 보기</summary>

**정답: B**

SQLite가 기본이며 기존 ./mlruns가 있으면 호환 동작을 확인합니다. 명시적 URI를 지정하면 모호함을 줄일 수 있습니다.
</details>

3. MLflow 3 LoggedModel의 핵심 변화는 무엇인가요?
   - A) run과 별개의 model_id·상태와 관계 추적
   - B) 처음으로 start_run 블록 없이 log_model을 호출할 수 있음
   - C) artifact가 더 이상 필요하지 않음
   - D) 등록 즉시 GPU에 배포됨

<details>
<summary>정답 보기</summary>

**정답: A**

2.22.0도 log_model에서 필요한 run을 암묵적으로 시작했습니다. 새 모델 식별 엔티티와 명시적 run context 생략을 혼동하지 않습니다.
</details>

4. Autologging에 대한 올바른 설명은 무엇인가요?
   - A) 어떤 코드든 모든 값이 수집된다
   - B) 항상 PII를 자동 제거한다
   - C) integration별 지원 버전·수집 범위·입출력 저장을 검토해야 한다
   - D) 모델 배포가 자동 완료된다

<details>
<summary>정답 보기</summary>

**정답: C**

지원 framework와 옵션에 따라 동작이 다릅니다. 원문·입력 예제·모델 artifact 수집도 확인합니다.
</details>

5. Tracing과 토큰·비용에 대한 정확한 설명은 무엇인가요?
   - A) 3.x에서 처음 tracing이 생겼다
   - B) 모든 도구 span에 LLM 비용이 있다
   - C) 토큰과 비용은 항상 실제 청구서와 같다
   - D) Tracing은 2.14.0에 도입됐고 사용량 수집은 integration에 의존한다

<details>
<summary>정답 보기</summary>

**정답: D**

3.x의 확장과 최초 도입을 구분합니다. model·usage·가격 정보가 없는 span에 비용을 보장하지 않습니다.
</details>

6. 원격 tracking 서버에서도 클라이언트가 S3 권한을 필요로 할 수 있는 경우는?
   - A) 직접 S3 artifact URI를 사용하는 비프록시 모드
   - B) SQLite parameter 조회만 수행할 때
   - C) 항상 서버와 관계없이 필요 없음
   - D) alias 이름을 읽을 때마다 필수

<details>
<summary>정답 보기</summary>

**정답: A**

metadata API와 artifact 데이터 경로는 다릅니다. 직접 모드는 클라이언트의 storage 권한과 네트워크가 필요합니다.
</details>

7. 같은 metric key를 step 0과 1에 기록하면 어떻게 확인하나요?
   - A) parameter가 자동 변경된다
   - B) 두 번째 값만 영구 보존된다
   - C) get_metric_history로 각 관측을 확인한다
   - D) 모델 두 개가 자동 등록된다

<details>
<summary>정답 보기</summary>

**정답: C**

현재 metric 요약과 timestamp/step을 가진 전체 이력을 구분합니다.
</details>

8. Tracking 웹 UI의 조회 경로로 적절한 것은?
   - A) 브라우저가 PostgreSQL에 직접 연결
   - B) 브라우저가 서버 HTTP API를 호출
   - C) UI가 항상 학습 Pod의 파일을 직접 읽음
   - D) 브라우저에 DB 관리자 비밀번호가 필수

<details>
<summary>정답 보기</summary>

**정답: B**

서버가 backend를 조회합니다. artifact proxy 여부는 별도로 설정합니다.
</details>

## 단답형 문제

9. initialize_logged_model이 PENDING으로 반환되면 즉시 추론에 쓸 수 있나요?

<details>
<summary>정답 보기</summary>

아닙니다. metadata만 생성될 수 있으며 실제 flavor·가중치·artifact 로깅과 finalization이 필요합니다. READY도 품질·배포 승인 자체를 뜻하지 않습니다.
</details>

10. 서버 artifact 설정을 바꿨는데 기존 experiment가 계속 S3에 직접 접근하는 이유는?

<details>
<summary>정답 보기</summary>

기존 experiment/run의 artifact URI는 서버 flag 변경만으로 소급 변경되지 않습니다. 기록된 URI와 실제 권한·전송 경로를 확인해야 합니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/mlflow/01-tracking.md)
