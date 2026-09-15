# 합성 PII 데이터와 증강 실습 퀴즈

> **마지막 업데이트**: 2026년 9월 15일

## 객관식 문제

1. 같은 원문의 paraphrase와 OCR 변형을 만드는 올바른 순서는?

   - A) 모든 변형 생성 후 record ID로 무작위 분할
   - B) 원본 family를 split에 배정한 뒤 train만 증강
   - C) 변형마다 다른 split을 배정
   - D) Test 실패 사례를 먼저 train에 복사

<details>
<summary>정답 보기</summary>

**정답: B**

Family의 모든 자손이 같은 split에 남아야 원문과 변형의 교차 누수를 막습니다.

</details>

2. Train에 24 family가 있고 각각 base와 두 변형을 포함하면 몇 레코드인가요?

   - A) 24
   - B) 48
   - C) 72
   - D) 120

<details>
<summary>정답 보기</summary>

**정답: C**

24 × 3 = 72입니다. Validation/test의 8 family는 각각 base만 유지합니다.

</details>

3. 합성 이름을 다른 이름으로 바꾸는 증강에서 필요한 작업은?

   - A) Record ID만 변경
   - B) 원문만 변경하고 TSV 유지
   - C) TSV만 변경하고 원문 유지
   - D) 원문·entities·TSV를 함께 갱신하고 계보 기록

<details>
<summary>정답 보기</summary>

**정답: D**

변환된 원문을 기준으로 정답을 다시 만들어야 합니다. 문자열 포함 검사만으로 의미나 gold 완전성을 보증하지는 않습니다.

</details>

4. 이 실습의 family/정확 원문 분리로 확인되는 것은?

   - A) 같은 family와 NFC 원문이 split을 넘지 않음
   - B) 모든 사람과 식별자가 split별로 다름
   - C) 모든 template이 split별로 다름
   - D) 실제 업무 일반화 성능이 검증됨

<details>
<summary>정답 보기</summary>

**정답: A**

일부 이름·template·domain을 공유합니다. Entity/template/domain holdout은 별도로 설계해야 합니다.

</details>

5. 이 annotation 정책에서 회사 대표번호만 있는 negative 문서를 변형한 뒤 정답은?

   - A) 대표번호를 PHONE으로 추가
   - B) entities와 target_tsv를 비워 둠
   - C) UNKNOWN 유형을 추가
   - D) 모든 숫자를 ACCOUNT로 추가

<details>
<summary>정답 보기</summary>

**정답: B**

정답 없는 문서도 학습에 필요합니다. Negative 정책은 업무별로 정의하며, 실제 학습에서는 빈 답의 EOS supervision도 확인합니다.

</details>

6. 정답 하나를 빼고 파일 해시까지 다시 계산했을 때 이 실습 감사가 거부할 수 있는 이유는?

   - A) Hash가 생산자의 신원을 인증하기 때문
   - B) 어떤 고객 문서에서도 모든 PII를 찾기 때문
   - C) Seed와 고정 family recipe로 내용도 재검사하기 때문
   - D) 모델 F1이 자동으로 측정되기 때문

<details>
<summary>정답 보기</summary>

**정답: C**

정해진 합성 실습의 재현성 검사입니다. 범용 annotation validator나 신원 인증 기능은 아닙니다.

</details>

7. 원본 train과 증강 train의 효과를 비교할 때 함께 고정·기록할 항목은?

   - A) Test를 매번 보고 가장 좋은 결과만 선택
   - B) 파일 개수만 비교
   - C) 생성 성공 여부만 비교
   - D) 같은 validation/decoding과 example·token·step budget

<details>
<summary>정답 보기</summary>

**정답: D**

같은 step 수라도 데이터 길이와 학습에 노출된 양이 다를 수 있습니다. 후보 선택은 validation으로 합니다.

</details>

8. 기존 corpus의 split pair별 교집합 22·36·9를 더한 값이 고유 교차 원문 그룹 51과 다른 이유는?

   - A) 세 split 모두에 있는 원문이 pair별로 반복 계산됨
   - B) NFC 원문이 항상 다른 문서를 의미함
   - C) Record ID가 모두 같기 때문
   - D) 51은 학습 모델의 오류 수이기 때문

<details>
<summary>정답 보기</summary>

**정답: A**

Pair 교집합의 합은 고유 원문 그룹 수가 아닙니다. 이 값은 CPU 데이터 관찰이며 모델 성능 수치가 아닙니다.

</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/06-data-augmentation-workshop.md)
