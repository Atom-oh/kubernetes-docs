# 실습 퀴즈: PII 추출을 위한 QLoRA 파인튜닝

> **마지막 업데이트**: 2026년 9월 15일

> **마지막 업데이트**: 2026년 9월 15일

## 객관식 문제

1. `load_in_4bit=True`, `bnb_4bit_quant_type="nf4"`, `bnb_4bit_compute_dtype=torch.bfloat16`을 사용하는 QLoRA에 대한 올바른 설명은 무엇인가요?
   - A) 기본 가중치뿐 아니라 활성값과 optimizer state도 모두 4비트가 된다.
   - B) 지원하는 기본 가중치는 4비트로 저장하고 고정하며, 양자화 선형 경로의 계산에는 BF16을 사용하고 어댑터를 학습한다.
   - C) BF16 compute 설정이 NF4를 취소하므로 기본 가중치는 모두 16비트로 저장된다.
   - D) Double quantization은 기본 가중치를 두 번 학습한다는 뜻이다.

<details>
<summary>정답 보기</summary>

**정답: B**

가중치 저장 형식, 계산 dtype, 학습 대상은 서로 다른 선택입니다. NF4는 기본 가중치의 저장 공간을 줄이고, BF16은 해당 계산 경로의 dtype을 지정합니다. Double quantization은 양자화 상수를 다시 양자화하는 기능입니다. 어댑터·gradient·optimizer state·활성값·고정밀 모듈의 메모리는 별도로 계산해야 합니다.
</details>

2. 입력 폭 2,048, 출력 폭 768인 선형 계층에 rank 16, alpha 32인 기본 LoRA를 적용합니다. Bias와 추가 학습 모듈이 없다면 어댑터 파라미터 수와 `alpha/r` 배율은 무엇인가요?
   - A) 1,572,864개와 2
   - B) 45,056개와 32
   - C) 45,056개와 2
   - D) 32,768개와 0.5

<details>
<summary>정답 보기</summary>

**정답: C**

`A`는 `(16, 2048)`, `B`는 `(768, 16)`이므로 합계는 `16 × (2048 + 768) = 45,056`개입니다. 기본 LoRA의 배율은 `32 / 16 = 2`입니다. `2048 × 768 = 1,572,864`는 기본 행렬의 파라미터 수이며 어댑터 파라미터 수가 아닙니다. Rank-stabilized LoRA는 별도 배율 규칙을 사용합니다.
</details>

3. Qwen 모델의 “전체 30.5B, 활성 3.3B 파라미터”를 학습 메모리 계획에 적용할 때 올바른 해석은 무엇인가요?
   - A) 활성 수치는 토큰의 희소 계산을 설명하며, 전체 가중치와 어댑터·gradient·optimizer state·활성값의 메모리를 별도로 고려해야 한다.
   - B) 항상 3.3B 파라미터만 로딩하므로 나머지 expert는 메모리를 사용하지 않는다.
   - C) `30.5B × 4비트 = 15.25GB`이므로 전체 학습 메모리도 정확히 15.25GB이다.
   - D) 토큰당 8개 expert를 선택하므로 LoRA도 모델 전체에서 8개 expert에만 삽입된다.

<details>
<summary>정답 보기</summary>

**정답: A**

활성 파라미터 수는 특정 토큰의 계산 경로와 관련되며 전체 모델 저장 공간을 대신하지 않습니다. 15.25 decimal GB는 이상화된 4비트 가중치 계산으로, 양자화 메타데이터와 나머지 학습 메모리가 빠져 있습니다. 어댑터 삽입 대상과 한 batch가 실제로 선택하는 expert도 구분해야 합니다.
</details>

4. Train 레코드 1,600개, microbatch 1, gradient accumulation 8, data-parallel worker 1, optimizer update 80회입니다. Packing과 마지막 불완전 batch가 없다는 가정에서 effective batch, 예제 제시 횟수, epoch 비율은 무엇인가요?
   - A) 1, 80회, 0.05 epoch
   - B) 8, 1,280회, 0.8 epoch
   - C) 80, 6,400회, 4 epoch
   - D) 8, 640회, 0.4 epoch

<details>
<summary>정답 보기</summary>

**정답: D**

Effective batch는 `1 × 8 × 1 = 8`, 예제 제시는 `80 × 8 = 640`회입니다. 한 epoch에는 `1600 / 8 = 200` update가 필요하므로 80 update는 0.4 epoch입니다. 현재의 “full”은 실행 mode 이름이며 한 epoch 완료나 수렴을 의미하지 않습니다. Sequence 길이가 다르면 같은 예제 수라도 학습 토큰 수는 다를 수 있습니다.
</details>

5. 엔터티가 없는 문서의 정답이 빈 assistant content일 때, completion-only loss의 올바른 검사는 무엇인가요?
   - A) 모든 label을 `-100`으로 만들어 해당 레코드가 학습에 기여하지 않게 한다.
   - B) Prompt와 padding은 무시하되 assistant turn을 끝내는 EOS 등 유효한 completion 토큰이 남는지 확인한다.
   - C) EOS만 무시하고 원문 prompt 전체를 추출 정답으로 학습한다.
   - D) NF4를 사용하면 EOS와 loss mask가 필요 없으므로 검사하지 않는다.

<details>
<summary>정답 보기</summary>

**정답: B**

Negative record도 “추출할 엔터티 없이 답변을 끝낸다”는 행동을 가르쳐야 합니다. 이 모델의 EOS는 `<|im_end|>`입니다. 실제 chat template 처리와 truncation 이후에도 supervised label이 0개가 아닌지 확인해야 합니다. 실제 completion에는 개행 같은 추가 토큰이 있을 수 있으며, 모든 label이 무시되는 상태를 정상 negative 학습으로 취급하면 안 됩니다.
</details>

6. Rank와 데이터 증강 방법을 비교할 때 평가 집합을 어떻게 사용하는 것이 적절한가요?
   - A) 같은 validation 조건으로 후보를 고르고 설정을 고정한 뒤 locked test에서 최종 baseline/candidate 비교를 수행한다.
   - B) 매 후보의 test 점수를 확인하고 가장 높은 후보를 선택한다.
   - C) 증강 후손을 모두 만든 뒤 무작위로 train/validation/test에 나눈다.
   - D) 작은 overfit 집합의 loss만 낮아지면 일반화 검증 없이 배포한다.

<details>
<summary>정답 보기</summary>

**정답: A**

Validation으로 조정하고 test는 최종 비교를 위해 잠가 둡니다. 현재 trainer는 smoke를 포함해 매 run 전후 test를 평가하므로 그대로 안전한 HPO 반복문이라고 설명할 수 없습니다. 수업용 튜닝 경로는 별도 수정이 필요합니다. 증강은 원본 family를 먼저 분리하고 train 후손에만 적용하며, 작은 과적합 검사는 학습 경로 진단이지 일반화 증명이 아닙니다.
</details>

7. Transformers 4.57.6의 Qwen3 MoE 구현에 현재 일곱 LoRA target suffix를 적용할 때 올바른 확인 방법은 무엇인가요?
   - A) `"all-linear"`로 바꿔도 같은 모듈만 선택되므로 목록 확인은 생략한다.
   - B) 모든 MoE는 raw parameter를 사용하므로 무조건 `target_parameters`로 바꾼다.
   - C) 실제 모듈 목록과 개수를 확인하고 attention projection 및 expert의 `gate_proj`/`up_proj`/`down_proj`가 선택되며 별도 router `gate`는 선택되지 않는지 확인한다.
   - D) Target 이름이 일곱 개이므로 모델 전체에서 선형 모듈 일곱 개만 학습한다.

<details>
<summary>정답 보기</summary>

**정답: C**

해당 버전의 expert는 `ModuleList` 안의 `nn.Linear` projection입니다. 같은 suffix가 여러 계층과 expert에 반복되므로 이름의 종류와 실제 모듈 수는 다릅니다. 공개 모델 설정에서는 `48 × (4 + 3 × 128) = 18,624`개 선형 모듈이 대상이라는 계산을 실제 목록과 대조할 수 있습니다. `"all-linear"`는 router 같은 모듈을 추가할 수 있고, `target_parameters`는 다른 구현의 raw parameter에 필요한 별도 경로입니다.
</details>

8. 현재 카탈로그에서 지원 중인 AL2023 기반 PyTorch DLC를 발견했습니다. 과거 예제의 GPU 실행을 다시 허용하기 위한 적절한 다음 단계는 무엇인가요?
   - A) Image tag만 바꾸고 `torch==2.8.0`을 포함한 기존 lock은 그대로 설치한다.
   - B) ECR에서 이미지를 찾았으므로 날짜 guard를 제거하고 바로 full run을 제출한다.
   - C) CPU 예제가 통과했으므로 GPU 양자화 로딩과 backward도 성공한 것으로 기록한다.
   - D) Image repository/tag/digest, Python/CUDA/driver, 의존성, toolkit 및 MLflow 조합을 검증하고 승인된 GPU smoke를 수행하며, 미검증 상태에서는 기존 guard를 유지한다.

<details>
<summary>정답 보기</summary>

**정답: D**

PyTorch 2.8 DLC는 2026년 8월 6일 패치 지원이 종료되었습니다. 새 카탈로그 항목이 있다는 것은 이 패키지에서 검증된 대체 조합이 있다는 뜻이 아닙니다. 새 계열의 repository도 `pytorch-training`과 다를 수 있고, 기존 torch pin 설치가 이관을 되돌릴 수 있습니다. GPU preflight는 향후 수행할 시험 절차이며 CPU 검사나 이미지 조회가 실제 GPU 성공 증거를 대신하지 않습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/05-qlora-finetuning-workshop.md)
