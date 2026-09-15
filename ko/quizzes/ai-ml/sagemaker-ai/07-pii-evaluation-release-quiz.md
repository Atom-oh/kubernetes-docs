# PII 평가와 비식별화 파이프라인 퀴즈

## 객관식 문제

1. 실습의 candidate는 F1이 0.8로 높아졌습니다. 바로 배포하면 안 되는 이유는?

   - A) Recall이 0이기 때문
   - B) Negative 문서번호를 계좌로 잘못 가리며 평가도 두 합성 문서뿐임
   - C) 모든 gold를 놓쳤기 때문
   - D) Round-trip이 실패했기 때문

<details>
<summary>정답 보기</summary>

**정답: B**

TP/FP/FN은 2/1/0입니다. 개선된 집계 점수와 추가 가림 오류를 함께 평가해야 합니다.

</details>

2. Round-trip rate 1.0이 의미하는 것은?

   - A) 실제 PII가 전부 탐지됨
   - B) 원문에 개인정보가 없었음
   - C) Mapping으로 치환 결과를 NFC 원문으로 복원했음
   - D) 모델이 새 고객에게 일반화함

<details>
<summary>정답 보기</summary>

**정답: C**

놓친 PII가 원문에 그대로 남아 있어도 치환한 값의 복원은 성공할 수 있습니다.

</details>

3. 현재 entities.over_redaction_rate의 분모와 분자는?

   - A) 불필요하게 가린 문자 / 전체 문자
   - B) 미가림 문서 / 전체 문서
   - C) FN / gold pair
   - D) FP pair / predicted pair

<details>
<summary>정답 보기</summary>

**정답: D**

역사적 필드 이름이지만 실제 계산은 추가 추출 pair 비율입니다. 문자 단위 과잉 삭제 비율과 다릅니다.

</details>

4. 배포용 strict parser에 필요한 동작은?

   - A) 모든 행·유형·길이·잘림을 검사하고 실패를 명시적으로 반환
   - B) 유효한 행 하나가 있으면 전체 성공
   - C) 잘못된 행을 버리고 PII 없음으로 처리
   - D) 출력에 없는 후보를 추측해서 추가

<details>
<summary>정답 보기</summary>

**정답: A**

현재 tolerant parser의 parse_success와 strict 계약 준수는 다릅니다. 잘린 결과를 완전한 처리로 표시하지 않습니다.

</details>

5. 같은 test를 보며 rank를 여러 번 선택했다면 그 세트의 역할은?

   - A) 계속 독립적인 최종 시험
   - B) 개발·선택에 사용된 평가 세트
   - C) 학습에 쓰지 않았으므로 영향 없음
   - D) 해시가 고정됐으므로 독립성이 보장됨

<details>
<summary>정답 보기</summary>

**정답: B**

Gradient에 쓰지 않아도 선택에 영향을 주면 최종 독립 평가 역할이 손상됩니다. Validation과 locked test를 분리합니다.

</details>

6. max_sequence_length=1024를 데이터 설계에서 해석하는 올바른 방법은?

   - A) 문서 1,024글자만 세면 됨
   - B) 한글과 영문의 글자/token 비율이 같음
   - C) Template·instruction·원문·completion의 tokenizer 예산을 점검
   - D) 모델의 최대 context가 더 크면 이 설정은 무시됨

<details>
<summary>정답 보기</summary>

**정답: C**

정답 token이나 원문 끝의 PII가 잘리지 않는지 확인하고, chunking 시 경계와 offset 복원도 평가합니다.

</details>

7. SageMaker Training Job의 Completed 다음에 여전히 필요한 작업은?

   - A) 품질 검증 없이 endpoint에 즉시 연결
   - B) Adapter만으로 base model 없이 추론
   - C) Mapping을 모든 downstream 로그에 첨부
   - D) 정확한 base/tokenizer/adapter/parser 조합 재로딩·평가·승인

<details>
<summary>정답 보기</summary>

**정답: D**

작업 종료 상태와 서비스 품질·개인정보 처리 승인은 별개입니다. 복구할 전체 조합도 버전 관리합니다.

</details>

8. Gold가 없는 운영 문서에 이 평가기의 leak rate를 그대로 계산할 수 있나요?

   - A) 아니요. 표본 annotation·별도 잔여 검사와 측정 범위를 구분해야 함
   - B) 예. 모델이 출력한 값을 모두 gold로 쓰면 됨
   - C) 예. Round-trip이 성공하면 leak rate는 0
   - D) 예. 빈 출력이면 모든 PII가 제거됨

<details>
<summary>정답 보기</summary>

**정답: A**

현재 지표는 gold 값의 미가림을 검사합니다. 정답 없는 상황에서 같은 완전성 지표를 만들 수 없습니다.

</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/07-pii-evaluation-release.md)
