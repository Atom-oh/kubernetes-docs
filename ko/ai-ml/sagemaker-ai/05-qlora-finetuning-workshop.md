# 실습: PII 추출을 위한 QLoRA 파인튜닝

> **마지막 업데이트**: 2026년 9월 15일

공식 근거는 2026년 9월 15일 확인했습니다.

이 워크숍의 목표는 판단 근거가 있는 학습 실험을 만드는 것입니다. 모델이 무엇을 예측하는지, 어떤 파라미터가 바뀌는지, 학습 step이 무엇인지, 어떤 증거가 있어야 어댑터를 채택할 수 있는지 설명합니다. Training Job의 완료는 그 실험을 구성하는 한 단계입니다.

합성 문서를 사용하며 저장소의 [Qwen PII trainer](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/train.py)를 따라갑니다. 제출·소유권·export·정리는 [Part 3의 실행 계약](03-sagemaker-mlflow-execution.md)을 함께 확인하세요. 이후에는 [데이터 증강 워크숍](06-data-augmentation-workshop.md)과 [PII 평가·릴리스 워크숍](07-pii-evaluation-release.md)으로 이어집니다.

**실행 상태:** 커밋된 GPU 경로는 PyTorch 2.8 DLC의 패치 지원이 2026년 8월 6일 종료되어 의도적으로 중단됩니다. `src/runtime_contract.py`를 유지하세요. 아래 CPU 연습은 모델 가중치를 불러오지 않습니다. 모델 로딩·학습 코드는 고정 버전 구현의 설명이며, GPU 연습에는 별도로 검증한 런타임 이관이 필요합니다. GPU 학습에 성공했다는 실행 기록이 아닙니다.

## 1. 학습 방법을 고르기 전에 예측 결과를 정의하기

다음은 전부 가상의 정보로 만든 문서입니다.

```text
Synthetic contact Alex Example; email alex@example.com.
```

모델이 반환해야 하는 결과는 문서에서 그대로 복사한 엔터티 목록입니다.

```text
PERSON	Alex Example
EMAIL	alex@example.com
```

모델은 문서 전체를 다시 쓰는 대신 **구조화된 추출**을 학습합니다. 출력 계약은 0개 이상의 `TYPE<TAB>ORIGINAL` 행입니다. 허용하는 타입은 `PERSON`, `RRN`, `DOB`, `REL`, `ADDRESS`, `PHONE`, `EMAIL`, `ACCOUNT`, `CARD`입니다. “사람 이름과 이메일을 찾았습니다”라는 문장은 의미가 맞더라도 요구한 출력 형식이 아닙니다.

추출 이후에는 결정론적 코드가 타입과 원문 일치를 검증하고 선택한 구간을 `[PERSON_1]` 같은 토큰으로 바꿉니다. 이렇게 분리하면 오류의 위치를 알 수 있습니다. 엔터티 누락은 추출 오류, 잘못된 치환 경계는 치환 오류, 잘못된 응답 구조는 형식 오류입니다. 모두 “LLM이 문서를 비식별화한다”로 묶으면 이 차이가 보이지 않습니다.

### CPU 연습: 추출 결과를 복원 가능한 토큰으로 바꾸기

패키지의 Python 3.12 환경에서 `examples/ai-ml/qwen-pii-finetuning`을 작업 디렉터리로 사용합니다. 기존 로컬 함수와 합성 문자열만 사용하며 모델이나 AWS를 호출하지 않습니다.

```python
from src.pii_tokens import parse_tsv, pseudonymize_text, reassemble_text

source = "Synthetic contact Alex Example; email alex@example.com."
completion = "PERSON\tAlex Example\nEMAIL\talex@example.com"

entities = parse_tsv(completion, source)
result = pseudonymize_text(source, entities)

assert result.masked_text == (
    "Synthetic contact [PERSON_1]; email [EMAIL_1]."
)
assert reassemble_text(result.masked_text, result.mapping) == source
print(result.masked_text)
```

매핑을 가지고 복원할 수 있으므로 이는 **가역적 가명처리**입니다. 비가역적 제거 또는 익명화의 증명이라고 부르면 안 됩니다. 실제 업무에서는 원문·매핑·raw prediction·학습된 어댑터에 적절한 접근 및 보존 정책이 필요합니다. Round-trip 검사는 복원 가능성을 확인합니다. 아무것도 치환하지 않아도 이 검사는 통과할 수 있습니다.

현재 `parse_tsv()`는 관대한 parser입니다. 잘못된 행을 버리고 유효한 행만 남길 수 있습니다. 엔터티가 없는 문서도 유효하므로 `train.py`는 빈 completion을 파싱 가능한 결과로 셀 수 있습니다. 따라서 parse success만으로 정확한 추출을 입증할 수 없습니다. PII 평가 워크숍에서는 엄격한 형식 유효성, 엔터티 recall, 잔존 PII를 분리합니다.

### 문제에 맞는 기준 모델 선택하기

| 방법 | 먼저 해 볼 실험 | 자동으로 해결하지 못하는 것 |
|---|---|---|
| 정규식과 결정론적 규칙 | 안정된 전화·이메일 형식과 정확한 치환 규칙 | 문맥에 따라 달라지는 이름·관계, OCR 변형, 애매한 숫자 |
| Token classification/NER 모델 | 안정된 엔터티 분류 체계의 구간 라벨 | 새 도메인, annotation 품질, 후속 치환 정책 |
| Prompt-only 생성 | 기본 모델의 추출과 TSV 출력 능력 확인 | 형식 안정성, 완전한 recall, 문서 안 지시에 대한 내성 |
| LoRA | 저랭크 업데이트만 학습해 사전학습 모델 적응 | 양자화하지 않은 기본 모델의 저장 메모리 감소 |
| QLoRA | 메모리 제약에서 고정된 양자화 기본 모델을 통해 어댑터 학습 | 활성값·optimizer state·모든 모델 텐서를 자동으로 4비트화 |

결정론적 baseline과 prompt-only baseline부터 만드세요. 제한된 문제에서 prompt-only 모델이 이미 충분하다면 학습이 복잡도만 늘릴 수도 있습니다. 도메인 특화 엔터티를 놓치거나 출력 계약을 반복해서 위반한다면, 지도학습 어댑터 실험의 목적이 더 명확해집니다.

## 2. LoRA가 무엇을 바꾸는지 이해하기

입력 폭이 `d_in`, 출력 폭이 `d_out`인 선형 계층에서 다음과 같이 정의합니다.

- `W`의 shape: `(d_out, d_in)`
- `A`의 shape: `(r, d_in)`
- `B`의 shape: `(d_out, r)`

기본 LoRA의 계산은 다음과 같습니다.

```text
W_effective = W + (alpha / r) * B @ A
y = W @ x + (alpha / r) * B @ A @ x
```

기본 행렬 `W`는 고정합니다. Optimizer는 `A`, `B`를 업데이트하며, 파라미터 수는 `d_in × d_out` 대신 `r × (d_in + d_out)`입니다. 그래디언트는 기본 모델을 사용하는 계산을 통해 계속 전달됩니다. “고정”은 forward나 backward 계산에서 기본 모델이 사라진다는 뜻이 아닙니다. [LoRA 논문](https://arxiv.org/abs/2106.09685)을 참고하세요.

`2048 → 768` projection에 rank 16을 적용해 봅시다.

```python
d_in, d_out, rank, alpha = 2048, 768, 16, 32
base_parameters = d_in * d_out
adapter_parameters = rank * (d_in + d_out)

assert base_parameters == 1_572_864
assert adapter_parameters == 45_056
assert alpha / rank == 2
print(base_parameters, adapter_parameters, alpha / rank)
```

Rank는 업데이트의 표현 용량을 조절하며 epoch 수가 아닙니다. `lora_alpha`는 배율을 조절하고, 이 설정의 `alpha/r`는 2입니다. Alpha를 고려하지 않고 rank만 높이면 이 배율도 달라집니다. PEFT의 선택 기능인 rank-stabilized LoRA는 다른 배율 규칙을 사용하지만 현재 설정은 이를 활성화하지 않습니다.

[PEFT 0.17.1의 기본 초기화](https://huggingface.co/docs/peft/v0.17.1/en/developer_guides/lora)에서는 `B`가 0에서 시작하므로 어댑터가 처음에는 기본 모델의 결과를 바꾸지 않습니다. 첫 backward에서 모든 어댑터 텐서의 gradient가 0이 아니어야 한다고 검사하지 마세요. MoE에서는 특정 batch가 선택하지 않은 expert도 있습니다. 실제로 존재하는 gradient가 유한한지, optimizer step 이후 기대한 어댑터 파라미터가 바뀌는지 확인하는 편이 유용합니다.

## 3. 4비트 가중치 이외의 QLoRA 메모리 계산하기

[QLoRA 논문](https://arxiv.org/abs/2305.14314)은 고정된 양자화 기본 모델과 학습 가능한 어댑터를 결합합니다. 현재 trainer의 다음 항목은 각각 다른 결정입니다.

| 설정 또는 메모리 항목 | 이 예제에서의 의미 |
|---|---|
| `load_in_4bit=True` | 지원하는 기본 선형 가중치를 4비트 양자화 경로로 로딩 |
| `bnb_4bit_quant_type="nf4"` | 정규분포 가중치를 고려한 NormalFloat4 사용 |
| `bnb_4bit_use_double_quant=True` | 양자화 상수를 다시 양자화해 부가 저장 공간 감소 |
| `bnb_4bit_compute_dtype=torch.bfloat16` | 양자화 선형 경로에서 BF16 계산 사용. 모든 연산이 4비트라는 뜻은 아님 |
| LoRA 파라미터와 gradient | 별도의 dtype과 메모리를 사용하는 학습 텐서 |
| Optimizer state | 학습 파라미터를 위한 추가 상태. NF4 설정이 자동으로 8비트 optimizer를 선택하지 않음 |
| 활성값과 임시 텐서 | sequence length, microbatch, attention 구현, checkpointing에 따라 변화 |
| 양자화하지 않은 모듈 | embedding, normalization 등은 더 높은 정밀도를 사용할 수 있음 |

Double quantization은 모델을 2비트로 바꾼다는 뜻이 아닙니다. BF16 설정도 모든 텐서가 2바이트를 차지한다는 보장이 아닙니다. K-bit 준비와 어댑터 처리 중 일부 텐서를 FP32로 유지하거나 변환할 수 있습니다. 하나의 설정 필드에서 전체 메모리를 추측하지 말고 실제 dtype과 학습 파라미터를 검사하세요. [버전이 고정된 bitsandbytes 가이드](https://huggingface.co/docs/transformers/v4.57.6/en/quantization/bitsandbytes)는 NF4, compute dtype, nested quantization을 구분합니다.

Gradient checkpointing은 일부 활성값 저장을 줄이고 backward에서 다시 계산합니다. 계산량과 메모리를 교환하는 방식입니다. Gradient accumulation은 여러 microbatch 이후 한 번 optimizer를 업데이트하며, 모든 microbatch의 활성값 그래프를 동시에 보관하라는 뜻이 아닙니다. 두 기능 모두 optimizer state 자체를 없애지는 않습니다.

### MoE의 전체 파라미터와 활성 파라미터는 다른 예산이다

[Qwen 모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)는 **전체 30.5B, 활성 3.3B 파라미터**, 48개 계층, 128개 expert, 토큰당 8개 expert 선택을 명시합니다. 활성 파라미터는 한 토큰의 희소 계산에 관한 수치입니다. 3.3B만 메모리에 올리면 된다는 뜻이 아닙니다.

`305억 × 4비트`라는 이상화된 계산은 **15.25 decimal GB**입니다. 가중치 저장 공간의 하한을 이해하기 위한 예이지 실제 GPU 메모리 예측이 아닙니다. 양자화 메타데이터, 고정밀 텐서, 어댑터, gradient, optimizer state, 활성값과 할당 부가 비용이 빠져 있습니다. 이 계산만으로 특정 단일 GPU 인스턴스에 들어간다고 단정할 수 없습니다.

## 4. 이 모델의 어댑터 대상 검사하기

과거 실행 패키지의 관련 고정 버전은 다음과 같습니다.

| 패키지 | Pin |
|---|---|
| PyTorch | `2.8.0` |
| Transformers | `4.57.6` |
| PEFT | `0.17.1` |
| TRL | `0.24.0` |
| bitsandbytes | `0.48.2` |
| Accelerate | `1.10.1` |
| datasets | `3.6.0` |

[고정 버전 Qwen3 MoE 구현](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)의 expert는 `gate_proj`, `up_proj`, `down_proj` 선형 계층을 가진 모듈들의 `ModuleList`입니다. Attention에는 `q_proj`, `k_proj`, `v_proj`, `o_proj`가 있습니다. 라우팅 gate의 이름은 별도로 `gate`입니다.

커밋된 `LoraConfig`는 이 일곱 projection suffix를 대상으로 합니다. `gate_proj`에 gate라는 단어가 있다고 router도 학습 대상으로 잡는 것은 아닙니다. 반대로 목록을 `"all-linear"`로 바꾸면 router를 포함한 다른 선형 모듈이 추가될 수 있습니다. 이는 다른 실험입니다.

```python
# Inspection hook after an authorized model load, before adapter insertion.
from collections import Counter

targets = {
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
}
matched = [
    name for name, module in model.named_modules()
    if name.rsplit(".", 1)[-1] in targets
]
counts = Counter(name.rsplit(".", 1)[-1] for name in matched)
assert set(counts) == targets
assert not any(name.endswith(".gate") for name in matched)
print(dict(sorted(counts.items())))  # Module names/counts, not training data.
```

공개 모델 설정의 차원으로 rank 16을 계산하면 attention projection 네 종류에 약 **1,337만**, 모든 expert의 projection 세 종류에 약 **8억 3,047만**, 합계 **843,841,536**개의 어댑터 파라미터가 됩니다. 이는 모델 차원에 근거한 산술 계산이지 GPU 실측이 아닙니다. 어댑터 삽입 후에는 `trainer.model.print_trainable_parameters()`로 실제 값을 확인해야 합니다.

[모델 설정](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json)의 hidden size는 2,048, head dimension은 128, query head는 32개, key/value head는 4개, expert intermediate size는 768입니다. 따라서 Q는 `2048 → 4096`, K/V는 각각 `2048 → 512`, O는 `4096 → 2048` projection입니다. Expert 하나에는 `2048 → 768` projection 두 개와 `768 → 2048` projection 한 개가 있습니다. 모델 import 없이 다음 계산을 재현할 수 있습니다.

```python
# CPU arithmetic from this model/version's configuration; not a GPU benchmark.
layers, experts, rank = 48, 128, 16
hidden, head_dim, q_heads, kv_heads = 2048, 128, 32, 4
expert_hidden = 768
q_width, kv_width = q_heads * head_dim, kv_heads * head_dim

attention = layers * rank * (
    (hidden + q_width)
    + 2 * (hidden + kv_width)
    + (q_width + hidden)
)
expert_adapters = layers * experts * 3 * rank * (hidden + expert_hidden)
total = attention + expert_adapters

assert attention == 13_369_344
assert expert_adapters == 830_472_192
assert total == 843_841_536
assert layers * (4 + 3 * experts) == 18_624  # Targeted linear modules.
print(attention, expert_adapters, total)
```

이 계산은 공개된 48계층 모델의 expert 구조, 앞의 일곱 target suffix, 추가 학습 모듈과 bias가 없음을 가정합니다. 실제 어댑터 목록과 대조할 예상값이며, 그 목록의 확인을 대신하지 않습니다.

따라서 큰 MoE에 넓은 target list를 적용하면서 “LoRA는 파라미터가 적다”라고만 설명하면 부족합니다. Attention-only와 attention-plus-expert를 비교하는 것은 유용한 통제 실험이 될 수 있습니다. 다만 현재 target list는 코드에 고정되어 있으므로 대상 변경은 수업용 코드 수정이 필요한 항목입니다.

일부 다른 모델이나 새 MoE 구현은 `nn.Linear` expert 대신 2차원 또는 3차원 `nn.Parameter`를 사용합니다. [PEFT 0.17.1의 `target_parameters` 설명](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md)은 이 경우를 다루며 expert 축과 다중 어댑터의 제약도 명시합니다. 선택한 모델·버전의 구현을 검사하세요. 이 모듈 기반 구현에 파라미터 직접 대상 지정 예제를 그대로 복사하지 않습니다.

## 5. 한 레코드의 chat 형식과 loss mask 따라가기

실제 [dataset loader](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/dataset.py)는 대화형 **prompt/completion** 데이터를 반환합니다.

```python
from src.dataset import SYSTEM_INSTRUCTION

record = {
    "source_text": "Synthetic contact Alex Example.",
    "target_tsv": "PERSON\tAlex Example",
}
row = {
    "prompt": [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": record["source_text"]},
    ],
    "completion": [
        {"role": "assistant", "content": record["target_tsv"]},
    ],
}
assert row["completion"][0]["role"] == "assistant"
```

`train.py`의 미사용 함수 `format_training_text()`는 `### Instruction` 문자열을 만듭니다. 이것은 현재 dataset 경로가 아닙니다. 그 문자열이 `SFTTrainer`의 실제 입력이라고 설명하면 안 됩니다.

[TRL 0.24.0](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)은 prompt와 prompt-plus-completion에 tokenizer의 chat template을 적용하고, 그 경계로 completion mask를 만듭니다. `completion_only_loss=True`이면 prompt 위치의 label을 `-100`으로 바꾸고 completion 위치를 causal language model loss에 사용합니다. Padding도 무시합니다.

### 빈 추출 정답이 학습 신호도 없다는 뜻은 아니다

대상 엔터티가 없는 문서에는 빈 assistant content 문자열을 사용합니다. 답변은 그래도 assistant turn을 끝내야 합니다. 이 모델의 [tokenizer 설정](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/tokenizer_config.json)은 EOS로 `<|im_end|>`, padding으로 `<|endoftext|>`를 사용합니다.

```python
# CPU-only illustration of a mask, not actual tokenizer output.
input_ids = [101, 102, 103, 104, 151645]
completion_mask = [0, 0, 0, 0, 1]
labels = [
    token if keep else -100
    for token, keep in zip(input_ids, completion_mask)
]
assert labels == [-100, -100, -100, -100, 151645]
assert sum(label != -100 for label in labels) == 1
```

이 예는 negative record에서 EOS를 학습하는 원리를 보여줍니다. 실제 template에는 개행 같은 추가 completion 토큰이 있을 수 있습니다. 실제 tokenized row를 검사하고, 위의 예시 prompt ID나 고정된 completion 길이를 그대로 가정하지 마세요.

Instruct-2507 모델 카드는 이 모델이 **non-thinking**이고 `enable_thinking=False`가 필요 없다고 설명합니다. 현재 예측 코드는 그 인자를 전달하지만, 그것이 checkpoint를 reasoning model로 바꾸지는 않습니다. `assistant_only_loss=True`는 template의 적절한 assistant-mask 지원이 필요한 별도 옵션이며, 이 단일 응답 prompt/completion 계약에는 필요하지 않습니다.

### 첫 학습 step 전에 준비된 데이터 검사하기

다음 hook은 승인된 호환 환경에서 trainer를 만든 뒤 넣는 수업용 검사입니다. 원문이나 디코딩된 label을 출력하지 않고 개수와 mask를 확인합니다.

```python
# Instructional inspection hook; not currently present in src/train.py.
prepared = trainer.train_dataset
for example in prepared:
    mask = example["completion_mask"]
    assert len(mask) == len(example["input_ids"])
    assert any(mask), "No supervised completion survived preprocessing"

examples = [prepared[i] for i in range(min(4, len(prepared)))]
batch = trainer.data_collator(examples)
supervised = (batch["labels"] != -100).sum(dim=1)
assert bool((supervised > 0).all())
if "attention_mask" in batch:
    padding = batch["attention_mask"] == 0
    assert bool((batch["labels"][padding] == -100).all())
print({"examples": len(examples), "target_tokens": supervised.tolist()})
```

Truncation 전 prompt-plus-completion 길이와 답변 EOS 보존 여부도 확인합니다. `max_length=1024`는 문서만의 길이가 아니라 결합된 학습 sequence 길이입니다. 긴 prompt가 예산을 전부 소비하면 답변이 사라질 수 있습니다. 추론에서도 잘린 문서에 PII가 가려져 있는데 평가 정답은 전체 문서의 엔터티를 요구하는 문제가 생길 수 있습니다.

초과 레코드를 거부할지, 불필요한 prompt 지시만 줄일지, annotation 계약을 함께 조정하며 문서를 chunk로 나눌지 명시하세요. Chunk와 증강 후손은 같은 원본 문서 family/split에 둡니다. 활성값 메모리, microbatch, 추론 출력 길이를 검토하지 않고 sequence length만 높이지 않습니다.

## 6. 고정된 학습 설정을 실행 순서대로 읽기

다음은 차단된 GPU 런타임을 실행하는 명령이 아니라 **코드를 읽기 위한 발췌**입니다. 이름과 인자는 PEFT 0.17.1, Transformers 4.57.6, TRL 0.24.0에 맞춥니다.

먼저 `run_training()`에서 다음 단계를 찾아보세요.

| 순서 | 커밋된 진입점의 동작 |
|---|---|
| 1 | 학습 라이브러리를 import하기 전에 지원 상태 guard 실행 |
| 2 | 설정·seed 결정, MLflow 준비, 데이터 파일 읽기 |
| 3 | 양자화 모델/tokenizer 로딩 후 test에서 baseline 평가 |
| 4 | K-bit 학습 준비, adapter와 대화형 dataset 구성 |
| 5 | 학습하며 중간 평가는 validation에서 수행 |
| 6 | 모델 출력을 저장하고 최종 adapter 파일 기록 |
| 7 | Test에서 tuned 모델을 평가하고 집계 결과 작성 |

3·7단계의 test 접근은 현재 동작이며, 8절에서 설명하는 권장 후보 선택 절차가 아닙니다.

```python
import torch
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import BitsAndBytesConfig

quantization = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

# `model` has already been loaded by the reviewed loading path.
model.config.use_cache = False
model = prepare_model_for_kbit_training(
    model, use_gradient_checkpointing=True
)
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)
```

현재 loader는 `AutoModelForCausalLM.from_pretrained(..., quantization_config=..., device_map="auto", torch_dtype=torch.bfloat16)`를 사용합니다. 자동 placement 결과를 검사해야 하며, CPU/disk offload가 유효한 학습 배치를 입증하는 것은 아닙니다. 수업용 단일 GPU 실험에서는 메모리에 들어가는 것을 확인한 뒤 명시적인 placement를 검토할 수 있습니다. 이 장은 loader를 변경하지 않습니다.

현재 코드는 `output_router_logits=True`도 설정합니다. 고정된 MoE 구현에서는 router 보조 loss가 표시되는 loss에 포함될 수 있습니다. 이 설정으로 router가 LoRA 대상이 되는 것은 아닙니다. 실험 간 비교에서 이 선택을 기록하세요.

```python
from trl import SFTConfig, SFTTrainer

sft_args = SFTConfig(
    output_dir=str(output_dir / "checkpoints"),
    max_steps=80,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=0.0002,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=1,
    eval_strategy="steps",
    eval_steps=20,
    save_strategy="steps",
    save_steps=80,
    save_total_limit=1,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    max_length=1024,
    packing=False,
    completion_only_loss=True,
    report_to="none",
    seed=42,
    data_seed=42,
)
trainer = SFTTrainer(
    model=model,
    args=sft_args,
    train_dataset=train_dataset,
    eval_dataset=validation_dataset,
    processing_class=tokenizer,
    peft_config=lora_config,
)
```

위 발췌는 설정된 **full-run** 값을 보여주며 model, tokenizer, dataset, output directory가 이미 준비된 상황을 가정합니다. `max_length`와 `processing_class`를 의도적으로 사용했습니다. 버전을 확인하지 않고 옛 `max_seq_length`/`tokenizer` 예제를 대입하지 마세요. 고정된 `SFTConfig`에는 설정 수준의 `chat_template_kwargs` 필드가 없습니다. 0.24.0은 레코드별 template kwargs를 지원합니다.

실제 tokenizer에는 이미 적절한 EOS가 설정되어 있습니다. 수업에서 계약을 명시적으로 보여주기 위해 `eos_token="<|im_end|>"`을 추가하는 것은 이 SFTConfig에서 지원합니다. 그러나 위 설정에 그 인자가 없다는 사실만으로 현재 tokenizer의 EOS가 잘못되었다고 판단하면 안 됩니다.

`config/experiment.yaml`에는 `quantization`, `double_quant`, `compute_dtype`가 있지만 loader는 현재 NF4/double quantization/BF16을 코드에 고정합니다. YAML 값만 바꿔서는 ablation이 구현되지 않습니다. 고정된 선택으로 유지하고 이를 설명하거나, loader까지 실제 선택을 연결하는 수업용 수정을 별도로 검토해야 합니다.

### 최적화에서 추출 응답 생성까지

검증된 GPU 환경에서 선행 조건과 검사 hook이 통과한 다음, 현재 코드는 `trainer.train()`을 호출하고 모델 출력을 저장한 뒤 tuned 모델을 평가합니다. 다음 발췌는 그 경계를 보여주며 CPU 연습이 아닙니다.

```python
# Code-reading excerpt: assumes an approved, constructed GPU trainer.
train_result = trainer.train()
trainer.save_model(str(output_dir))
trainer.model.config.use_cache = True
```

생성용 prompt는 assistant generation prefix에서 끝나야 하며 정답 completion을 포함하지 않습니다. 응답을 파싱하기 전에 생성된 ID에서 prompt 토큰을 제외하세요. 앞의 합성 `row`, `record`를 사용하는 단일 레코드 진단 예제는 다음과 같습니다.

```python
# Instructional inference hook; not a replacement for the committed CLI.
trainer.model.eval()
prompt = tokenizer.apply_chat_template(
    row["prompt"], tokenize=False, add_generation_prompt=True
)
inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
prompt_length = inputs["input_ids"].shape[1]
if prompt_length > 1024:
    raise ValueError("Apply the reviewed long-document policy first")
inputs = inputs.to(trainer.model.device)

with torch.inference_mode():
    generated = trainer.model.generate(
        **inputs,
        do_sample=False,
        max_new_tokens=512,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
completion = tokenizer.decode(
    generated[0, prompt_length:], skip_special_tokens=True
)
entities = parse_tsv(completion, record["source_text"])
# Evaluate aggregate metrics; do not log raw completions from real documents.
```

현재 `_predict_records()`는 left padding으로 batch를 만들고 truncation을 활성화합니다. 위 hook은 수업의 경계를 드러내기 위해 긴 단일 prompt를 거부합니다. 출력 상한 512토큰은 별도의 제한이므로 긴 TSV 답변은 여전히 잘릴 수 있습니다. Prompt 길이뿐 아니라 응답 종료와 형식도 검사하세요.

## 7. 예제 수, optimizer update, epoch 계산하기

일반적인 data parallel 학습에서는 다음 관계를 사용합니다.

```text
effective batch ≈ microbatch per device × accumulation × data-parallel workers
```

커밋된 단일 인스턴스·단일 GPU 예제에서는 `1 × 8 × 1 = 8`입니다. Accumulation 8은 microbatch 여덟 개를 처리한 뒤 optimizer를 한 번 업데이트한다는 뜻입니다. 각 microbatch에 예제가 여덟 개 있다는 뜻이 아닙니다.

```python
from math import ceil

records = 1600
microbatch, accumulation, workers = 1, 8, 1
effective_batch = microbatch * accumulation * workers
updates_per_epoch = ceil(records / effective_batch)

assert effective_batch == 8
assert updates_per_epoch == 200
assert 10 * effective_batch == 80
assert 80 * effective_batch == 640
assert 80 / updates_per_epoch == 0.4
```

따라서 설정된 smoke는 optimizer update 10회, 약 80회의 예제 제시입니다. “Full”은 update 80회, 약 640회의 예제 제시로, 위의 packing 없음·정수 배치 가정에서 1,600개 데이터셋의 0.4 epoch입니다. Full은 mode 이름이며 수렴이나 한 epoch 완료를 뜻하지 않습니다.

`max_steps`는 업데이트 예산을 결정합니다. Sequence 길이가 가변적이면 같은 step이 같은 정답 토큰 수나 계산량을 뜻하지 않습니다. 긴 문맥이나 증강 데이터셋을 비교할 때는 시간과 loss뿐 아니라 실제 본 예제와 정답 토큰 수도 기록하세요. 분산 환경의 마지막 불완전 batch나 packing에는 추가 계산이 필요하며 위 산술에는 포함하지 않았습니다.

## 8. 작은 과적합 진단과 모델 선택 분리하기

전체 학습 예산을 쓰기 전에 **train** 레코드 8–16개로 별도의 진단을 설계합니다. 단순한 positive, 반복 엔터티, 형식 변형, PII가 없는 예제를 포함하고 validation·locked test와 분리합니다.

런타임 이관 후에는 모델 로딩, prompt/completion mask 확인, 한 번의 forward/backward에서 유한한 값 확인, 기대한 어댑터 파라미터 변경, 작은 부분집합에 대한 학습 개선, 동일 기본 모델로 저장한 어댑터 재로딩과 결정론적 디코딩 재현 순으로 검사합니다.

예를 들어 레코드 8개, effective batch 8, optimizer update 20회라면 그 작은 집합을 약 20회 보게 됩니다. 의도적인 진단 예산이지 전체 데이터셋 권장값은 아닙니다. 그 8개 레코드의 정확한 추출을 비교하고 negative 응답의 종료를 확인하세요. Loss 감소만으로 통과시키지 않습니다.

이는 의도적인 overfit 검사입니다. 성공은 학습 경로가 그 예제들을 배울 수 있음을 알려줍니다. 일반화, 운영 recall, 모든 PII 제거를 입증하지는 않습니다. 실패도 유용합니다. 모델이나 데이터셋을 키우기 전에 mask, target, 데이터 대응, 최적화를 수정할 근거가 됩니다.

### 현재 trainer가 안전한 HPO 반복문은 아닌 이유

커밋된 trainer는 test 파일을 읽고 smoke를 포함해 **매 실행 전후 두 번** 평가합니다. 중간 trainer 평가는 validation을 사용하지만 마지막 baseline/tuned 지표는 매번 test로 계산합니다. Hyperparameter를 선택하면서 그 test 결과를 반복 확인하면 안 됩니다.

수업용 튜닝 절차에서는 실행 진단에 smoke subset, 후보 비교에 validation을 사용하는 수정임을 명시해야 합니다. 일반 튜닝 run에서는 test를 사용할 수 없게 하고, 선택한 설정을 고정한 다음 최종 baseline/candidate test 비교를 수행합니다. 이 구분은 [PII 평가·릴리스 워크숍](07-pii-evaluation-release.md)에서 더 자세히 다룹니다.

| 실험 | 고정할 것 | 의도적으로 바꿀 것 | Validation에서 선택할 근거 |
|---|---|---|---|
| 어댑터 용량 | 데이터, targets, learning rate, 토큰 예산 | 배율 정책을 명시한 rank 비교. 예: 8과 16 | Recall, 잔존 PII, 과잉 제거, 학습 안정성 |
| Target 범위 | 데이터, rank, decoding, 예산 | Attention-only와 현재 attention-plus-expert | 학습 파라미터·실측 메모리 대비 품질 이득 |
| 최적화 | 데이터, targets, rank, sequence 정책 | 한 번에 하나의 learning rate 선택 | Loss만이 아닌 loss 추이와 추출 지표 |
| Sequence 정책 | 평가 레코드와 라벨 계약 | 거부/chunk 정책 또는 근거 있는 길이 증가 | 긴 문서 coverage와 truncation 비율 |
| 증강 | 원본 family와 평가 집합 | Train에만 적용하는 한 종류의 변환 family | 희귀 타입, 형식 변형, negative 성능 |

이 표는 실험 설계이며 구현된 CLI switch나 권장 최적값이 아닙니다. 증강 후손은 원본 family와 함께 묶어야 합니다. Family 분리가 exact-text, entity, template, domain 분리를 자동 보장하지는 않습니다. [데이터 증강 워크숍](06-data-augmentation-workshop.md)에서 이 검사들을 구분합니다.

데이터 증강 워크숍의 CPU 연습은 별도 데이터셋입니다. 여기의 1,600개 기준 계산은 과거 학습 설정에 관한 것이므로, 새 실습 출력에 그 개수를 그대로 적용하지 마세요.

## 9. 실험을 SageMaker AI 경로에 연결하기

[실제 launcher](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py)를 통해 로컬 개념과 작업의 입력·출력을 연결합니다.

| 단계 | 현재 매핑 | 확인할 증거 |
|---|---|---|
| 로컬 설정 | `config/experiment.yaml`과 `requirements.lock` | 설정·소스·의존성 버전 |
| 소스 번들 | `generated/source.tar.gz`의 source/config/requirements | 번들 목록과 SHA-256. credential/data를 재귀적으로 포함하지 않음 |
| S3 입력 | 실험의 `source/`, `dataset/` 분리 prefix | 업로드 객체 해시와 의도한 계정·버킷·prefix |
| 작업 안의 소스 | `/opt/ml/code/config/experiment.yaml`; `SAGEMAKER_PROGRAM=src/train.py` | Toolkit 실행과 설정 파일 존재 |
| Dataset channel | 이름이 `dataset`인 File mode channel 하나 | `/opt/ml/input/data/dataset/{train,validation,test}.jsonl`과 manifest |
| Trainer 평가 | 학습 중 validation. 현재 마지막 비교에는 test 사용 | 실제 split ID·해시와 앞에서 설명한 구분 |
| MLflow | 설정·버전·manifest 파일, 집계 지표, 최종 adapter 파일 | Run 식별, artifact 가용성, client/App 호환성 |
| SageMaker 모델 출력 | 현재 `output-dir=/opt/ml/model` | 최종 디렉터리 내용과 S3 모델 artifact URI |

Channel 이름이 입력 경로를 결정합니다. 이름이 `dataset`이라고 내용 전체가 train 데이터가 되는 것은 아닙니다. 이 channel에는 서로 다른 split 세 개가 들어 있습니다. 학습 전에 관측한 파일 해시를 다시 계산해 비교하세요. Manifest를 기록하기만 했다는 것은 실제 읽은 파일의 일치를 입증하지 않습니다.

### 무엇이 저장되는지 이해하기

현재 SFT 출력 디렉터리는 `output_dir` 아래의 `/opt/ml/model/checkpoints`입니다. SageMaker는 모델 디렉터리를 묶어 업로드하므로 모델 artifact에 최종 어댑터·JSON 파일뿐 아니라 checkpoint도 들어갈 수 있습니다. MLflow의 명시적 adapter 파일 allowlist가 SageMaker 디렉터리 패키징을 바꾸지는 않습니다.

더 명확한 수업용 설계에서는 최종 어댑터를 `/opt/ml/model`, 집계 출력을 `/opt/ml/output/data`, 복구용 checkpoint를 `/opt/ml/checkpoints`로 분리할 수 있습니다. S3 checkpoint 동기화에는 적절한 job 설정이 필요하며 로컬 디렉터리 생성만으로 백업이 되지는 않습니다. [AWS 저장 경로 표](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html)와 [학습 출력 계약](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)을 참고하세요.

어댑터는 기본 모델 전체를 대체하는 독립 모델이 아닙니다. 재로딩에는 올바른 기본 모델/revision, tokenizer, adapter 설정, 호환 런타임이 필요합니다. 현재 코드는 model revision을 고정하지 않습니다. 별도로 검토하는 재현성 개선에서 이를 기록해야 합니다.

## 10. Hyperparameter를 바꾸기 전에 작업 단계 진단하기

SageMaker 상태와 모델 내부 단계 진단은 서로 다른 질문에 답합니다. `SecondaryStatus`는 다운로드·학습·업로드 등을 나타낼 수 있지만, 애플리케이션이 가중치를 읽거나 baseline을 평가하거나 어댑터를 저장하는 동안 모두 `Training` 상태일 수 있습니다.

다음은 **기존의 승인된 작업**을 읽는 진단 명령이며, 이번 문서 작성에서 실행한 명령이 아닙니다.

```bash
: "${TRAINING_JOB_NAME:?Set the existing reviewed job name}"
: "${AWS_REGION:?Set its Region}"
aws sagemaker describe-training-job \
  --region "$AWS_REGION" \
  --training-job-name "$TRAINING_JOB_NAME" \
  --query '{
    status:TrainingJobStatus,
    phase:SecondaryStatus,
    stages:SecondaryStatusTransitions,
    failure:FailureReason,
    model:ModelArtifacts.S3ModelArtifacts,
    trainingSeconds:TrainingTimeInSeconds,
    billableSeconds:BillableTimeInSeconds
  }'
```

실패 상세는 검토 전까지 비공개로 유지합니다. `/aws/sagemaker/TrainingJobs`에서 해당 작업의 stream과 제한된 로그 시간 범위를 사용하고, 다른 작업이나 학습 예제를 함께 덤프하지 않습니다. AWS의 [secondary status 전이](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_SecondaryStatusTransition.html)와 [CloudWatch 로그 설명](https://docs.aws.amazon.com/sagemaker/latest/dg/logging-cloudwatch.html)을 참고하세요.

향후 수업용 trainer에는 데이터 검증 완료, 모델 로딩 완료, baseline 완료, adapter 삽입, 첫 backward 완료, 최적화 완료, artifact 저장, 평가 완료와 같은 집계 정보만 담은 단계 표시를 추가할 수 있습니다. 원문을 로그에 남기지 않고도 어느 단계가 멈췄는지 알 수 있습니다.

| 증상 | 먼저 구분할 것 | 유용한 다음 조치 |
|---|---|---|
| 모델 로딩 전에 실패 | Runtime guard, package/toolkit 오류, 경로 누락 | 단계와 정확한 config/channel 매핑 확인. Rank 튜닝부터 하지 않음 |
| 로딩 중 OOM | 기본 가중치·placement와 optimizer 메모리 | 전체 모델 크기, 양자화, 고정밀 텐서, 실제 placement 확인 |
| Backward OOM | 활성값과 adapter/optimizer state | Microbatch·sequence 예산 감소, checkpointing·target 범위 확인 |
| NaN loss | 잘못된 target과 수치·최적화 문제 | 0개가 아닌 supervised label, 유한한 값, BF16 지원, learning rate 확인 |
| Loss는 감소하지만 recall이 낮음 | 형식 학습과 엔터티 coverage | 타입·언어·길이·positive/negative별 validation 확인 |
| 설명문 또는 잘못된 TSV 출력 | Chat template/EOS/masking과 작업 정의 | Step을 늘리기 전에 실제 prepared example과 decoding 계약 확인 |
| Parse/round-trip은 높지만 PII가 남음 | 관대한 parser와 가역 치환 | 잔존 PII와 entity recall 확인. Parser 성공을 개인정보 보호 성공으로 해석하지 않음 |
| 작업은 완료됐지만 재로딩 실패 | Artifact 디렉터리 또는 기본 모델/revision 불일치 | Artifact 내용을 검사하고 별도 adapter reload 검증 |

현재 `peak_gpu_memory_bytes`는 모델 로딩 후 reset한 기본 CUDA device의 PyTorch allocated-memory peak입니다. 전체 GPU 메모리, 로딩 peak, 여러 device의 합계가 아닙니다. 향후 실측에서도 측정 대상을 정확히 표시하세요.

## 11. 런타임 이관을 검증된 버전 조합으로 다루기

[AWS DLC 지원 정책](https://aws.github.io/deep-learning-containers/reference/support_policy/)과 [이미지 카탈로그](https://aws.github.io/deep-learning-containers/reference/available_images/)는 2026년 9월 15일 확인했습니다. 기존 `pytorch-training` 이미지 계열과 새 `pytorch` 계열을 혼동하면 안 됩니다.

| 카탈로그 항목 | Registry hostname을 제외한 SageMaker tag | Python / OS | 패치 지원 종료 |
|---|---|---|---|
| 현재 과거 예제 | `pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` | 3.12 / Ubuntu 22.04 | 2026-08-06 |
| 새 계열 2.11 | `pytorch:2.11.0-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-04-30 |
| 새 계열 2.12 | `pytorch:2.12.1-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-02 |
| 새 계열 2.13 | `pytorch:2.13.0-cu133-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-20 |

공식 카탈로그의 확인된 항목이며, **이 패키지에서 검증한 대체 실행 환경은 아닙니다**. AWS는 Ubuntu 기반 PyTorch 2.8–2.10을 완전히 패치할 수 없다고도 안내하며 AL2023 기반 PyTorch 2.11 이상으로의 이관을 권고합니다. Launcher에는 이전 repository 이름과 tag가 함께 고정되어 있으므로 버전 숫자만 바꿔서는 부족합니다.

이미지 repository/tag/digest, 리전 가용성, Python, CUDA/driver/architecture, PyTorch, HF/PEFT/TRL/bitsandbytes 의존성, training toolkit, MLflow client/service를 하나의 조합으로 맞춰야 합니다. 새 DLC에 현재 `torch==2.8.0` lock을 설치하면 의도한 framework 이관을 되돌릴 수 있습니다.

이 선택들을 검토한 다음에만 승인된 GPU preflight에서 실제 CUDA/BF16 지원, 양자화 로딩, 예상 target/dtype, forward/backward 한 번, 유한한 loss, adapter 변경과 save/reload를 검증합니다. 이는 **시험 절차**이며 이미 성공했다는 증거가 아닙니다. 대체 조합을 개발하고 검증하는 동안 과거 실행 guard는 유지합니다.

## 12. 이해도 확인

1. Worker 하나, microbatch 1, accumulation 8에서 update 80회는 몇 번의 예제 제시인가요? **약 640회**입니다. 여기서 사용한 packing 없음·정수 배치 가정의 결과입니다.
2. “활성 3.3B”는 3.3B만 메모리에 필요하다는 뜻인가요? **아닙니다.** 희소 계산의 설명이며 전체 가중치와 학습 상태를 고려해야 합니다.
3. Negative 문서는 무엇을 가르쳐야 하나요? **Assistant turn을 끝내는 유효한 빈 추출 응답**입니다. Label이 전부 무시된 sequence가 아닙니다.
4. 매 run의 test 점수로 rank를 선택해도 되나요? **아닙니다.** Validation으로 선택하고 후보를 고정한 뒤 locked test로 최종 비교합니다.
5. Round-trip 성공은 PII 제거를 증명하나요? **아닙니다.** 치환 경로의 복원 가능성을 확인하며, 놓친 PII는 그대로 남을 수 있습니다.
6. 지원 중인 DLC tag만 있으면 현재 launcher를 활성화해도 되나요? **아닙니다.** Repository, 의존성, toolkit, 하드웨어, 통합 계약이 검증된 조합을 이뤄야 합니다.

## 공식 근거

아래 자료는 모두 **2026-09-15** 확인했습니다. 코드 읽기 예제에는 버전이 명시된 자료를 우선합니다.

- [LoRA 논문](https://arxiv.org/abs/2106.09685), [QLoRA 논문](https://arxiv.org/abs/2305.14314)
- [PEFT 0.17.1 LoRA 가이드](https://huggingface.co/docs/peft/v0.17.1/en/developer_guides/lora), [k-bit 준비 코드](https://github.com/huggingface/peft/blob/v0.17.1/src/peft/utils/other.py)
- [Transformers 4.57.6 bitsandbytes 양자화](https://huggingface.co/docs/transformers/v4.57.6/en/quantization/bitsandbytes)
- [bitsandbytes 0.48.2 4비트 모듈](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/0.48.2/docs/source/reference/nn/linear4bit.mdx)
- [TRL 0.24.0 SFT 가이드](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer), [SFTConfig](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_config.py), [SFTTrainer](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_trainer.py)
- [Qwen 모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507), [모델 설정](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json), [고정된 Transformers 구현](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)
- [AWS DLC 지원](https://aws.github.io/deep-learning-containers/reference/support_policy/), [이미지 목록](https://aws.github.io/deep-learning-containers/reference/available_images/)
- [SageMaker 저장 경로·환경 변수](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html), [학습 출력](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)

다음: [데이터 증강 워크숍](06-data-augmentation-workshop.md)

## 퀴즈

[QLoRA 파인튜닝 워크숍 퀴즈](../../quizzes/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop-quiz.md)에서 핵심 개념과 계산을 확인하세요.
