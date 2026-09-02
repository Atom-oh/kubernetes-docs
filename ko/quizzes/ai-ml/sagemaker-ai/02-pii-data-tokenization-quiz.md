# 합성 PII 데이터와 토큰화 퀴즈

## 객관식 문제

1. 모델 출력 계약으로 올바른 것은 무엇인가요?
   - A) 자유 형식 Markdown
   - B) JSON object
   - C) 한 줄당 `TYPE<TAB>ORIGINAL`
   - D) 최종 치환 문서

<details>
<summary>정답 보기</summary>

**정답: C**

허용 유형과 원문 값을 tab으로 구분해 출력합니다.
</details>

2. source-containment 검사의 목적은 무엇인가요?
   - A) 모델이 만든 새로운 값을 허용
   - B) 원문에 없는 환각 값을 제거
   - C) 데이터셋을 압축
   - D) GPU 메모리를 측정

<details>
<summary>정답 보기</summary>

**정답: B**

추출값 또는 허용 변형이 source에 있어야 치환 후보가 됩니다.
</details>

3. 데이터 split은 무엇인가요?
   - A) 1,600 / 200 / 400
   - B) 2,000 / 100 / 100
   - C) 1,100 / 550 / 550
   - D) 400 / 200 / 1,600

<details>
<summary>정답 보기</summary>

**정답: A**

Train/Validation/Test는 1,600/200/400이며 총 2,200개입니다.
</details>

4. 결정론적 토큰화에 포함되는 검사는 무엇인가요?
   - A) 엔터티 순서를 바꾸면 다른 결과가 나와야 함
   - B) mapping으로 복원한 결과가 원문과 같은지 확인
   - C) fuzzy matching을 무제한 적용
   - D) token mapping을 MLflow tag로 기록

<details>
<summary>정답 보기</summary>

**정답: B**

round-trip 검사는 치환이 원문 정보를 손실하지 않았는지 확인합니다.
</details>

5. fine-tuned F1 값이 없는 이유는 무엇인가요?
   - A) F1 코드가 없음
   - B) 테스트 데이터가 없음
   - C) GPU 학습과 tuned evaluation이 미실행
   - D) 엔터티 유형이 하나뿐임

<details>
<summary>정답 보기</summary>

**정답: C**

평가 구현은 검증됐지만 학습이 실행되지 않아 tuned 측정값은 없습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/02-pii-data-tokenization.md)
