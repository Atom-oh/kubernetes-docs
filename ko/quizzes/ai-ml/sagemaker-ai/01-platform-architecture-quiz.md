# SageMaker Qwen 플랫폼 아키텍처 퀴즈

## 객관식 문제

1. 이 설계에서 모델 출력과 Python 처리의 관계는 무엇인가요?

   - A) 모델이 모든 PII를 확실히 제거한다
   - B) 모델은 후보 TSV를 출력하고 코드는 검증·치환하며, 탐지 누락은 별도 평가한다
   - C) 코드의 round-trip 성공이 익명성을 증명한다
   - D) 모델이 project를 삭제한다

<details>
<summary>정답 보기</summary>

**정답: B**

결정론적 치환은 모델이 놓친 엔터티를 자동으로 복구하지 않습니다.

</details>

2. 그림과 검증 기록의 올바른 해석은 무엇인가요?

   - A) GPU 두 경로가 모두 검증됐다
   - B) 목표 설계이며 로컬 테스트와 과거 AWS 관측을 구분해야 한다
   - C) 현재 잔존 project 수를 실시간으로 보여준다
   - D) 학습 후 F1과 비용 비교 결과다

<details>
<summary>정답 보기</summary>

**정답: B**

2026-09-01 기록은 학습 전 중단입니다. 현재 AWS 상태나 GPU 결과를 이번 로컬 테스트로 증명하지 않습니다.

</details>

3. Model ID와 seed만 같으면 두 환경의 결과가 완전히 재현되나요?

   - A) 항상 같다
   - B) 아니요. Revision·data hash·image/dependency·CUDA/hardware와 실행 조건도 확인한다
   - C) EKS에만 seed가 필요하다
   - D) QLoRA에서는 tokenizer가 무관하다

<details>
<summary>정답 보기</summary>

**정답: B**

직접 package pin은 전체 transitive lock이 아니며 GPU 연산의 결정론도 별도 조건입니다.

</details>

4. 일반 MLflow 로그/공개 보고서에서 제외해야 할 것은 무엇인가요?

   - A) Dataset hash
   - B) 검토된 LoRA 설정
   - C) Raw source·completion·token mapping·presigned URL
   - D) 비민감 집계값

<details>
<summary>정답 보기</summary>

**정답: C**

Private inventory에 필요한 ID/ARN을 보관하는 것과 공개 자료에 노출하는 것을 구분합니다. Autolog/tracing도 검증합니다.

</details>

5. Governance 확인과 모델 크기에 대해 맞는 설명은 무엇인가요?

   - A) QLoRA는 반드시 Unified Studio project가 필요하다
   - B) 이 실험의 governance는 선택한 절차이며, 3.3B active가 전체 모델 메모리 크기를 뜻하지 않는다
   - C) Owner assignment가 모든 partial failure를 원자적으로 rollback한다
   - D) 3시간 job limit은 전체 실험 비용 상한이다

<details>
<summary>정답 보기</summary>

**정답: B**

모델 카드는 30.5B total/3.3B active입니다. Resource readiness·ownership과 실제 GPU memory/cost는 별도로 검증해야 합니다.

</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/01-platform-architecture.md)
