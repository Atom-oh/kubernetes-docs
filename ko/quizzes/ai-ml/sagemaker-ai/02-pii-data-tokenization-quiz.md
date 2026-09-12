# 합성 PII 데이터와 토큰화 퀴즈

## 객관식 문제

1. 모델 출력 계약은 무엇이며 어떤 한계가 있나요?

   - A) 최종 익명화 문서를 항상 정확히 생성한다
   - B) 원문에 있는 모든 문자열은 실제 PII다
   - C) 후보 TYPE/TAB/ORIGINAL 행이며 누락·오분류는 별도 평가한다
   - D) Project membership을 반환한다

<details>
<summary>정답 보기</summary>

**정답: C**

Source 일치는 값의 존재를 확인할 뿐 의미적 정답이나 전체 PII 탐지를 보장하지 않습니다.

</details>

2. 다른 공백 표기의 이름과 기존 [PERSON_1]을 어떻게 처리하나요?

   - A) 모든 표기를 같은 mapping 값으로 덮어쓴다
   - B) 실제 표기별로 복원 가능한 token을 만들고 기존 marker와 이름 충돌을 피한다
   - C) 기존 marker를 새 이름으로 무조건 복원한다
   - D) 원문을 NFC 대신 임의로 줄인다

<details>
<summary>정답 보기</summary>

**정답: B**

같은 type/표기는 재사용하지만 다른 표기는 별도 token이며 mapping은 실제 source 표기를 저장합니다.

</details>

3. 데이터 split과 검증 범위에 대한 설명으로 맞는 것은 무엇인가요?

   - A) 1,600/200/400개이며 같은 template·이름이 split 사이에 공유될 수 있다
   - B) Hash가 다르면 실제 업무 일반화가 증명된다
   - C) Checksum 실패가 공식 미할당 번호임을 증명한다
   - D) 모든 PHONE 값은 공식 예약 번호다

<details>
<summary>정답 보기</summary>

**정답: A**

Generator 1.0.0의 기존 해시는 유지했지만 합성 template 데이터와 실제 업무 평가는 구분합니다.

</details>

4. 정답 Alpha Beta 중 Alpha만 가렸을 때 수정한 누출 평가는 어떻게 동작하나요?

   - A) 전체 문자열이 사라졌으므로 항상 누출 0
   - B) Source의 정답 구간에 미가림이 남아 있음을 감지한다
   - C) Placeholder 이름에서만 정답을 찾는다
   - D) Round-trip이 성공하면 누출 0으로 바꾼다

<details>
<summary>정답 보기</summary>

**정답: B**

실제 치환 구간의 합집합으로 모든 정답 발생 구간이 완전히 덮였는지 확인합니다. 복원과 탐지 완전성은 다른 지표입니다.

</details>

5. 정답 TSV를 입력한 2,200개 oracle 점검의 의미는 무엇인가요?

   - A) Fine-tuned 모델 F1 측정이다
   - B) GPU 처리량 측정이다
   - C) 평가기·복원·해시의 sanity check이며 모델 출력 측정이 아니다
   - D) 모든 실제 PII가 탐지된다는 보장이다

<details>
<summary>정답 보기</summary>

**정답: C**

로컬 테스트 50개와 oracle 점검이 통과했지만 GPU 학습이나 fine-tuned 평가를 실행하지 않았습니다.

</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/02-pii-data-tokenization.md)
