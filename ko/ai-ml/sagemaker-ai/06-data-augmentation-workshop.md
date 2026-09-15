# 실습: 합성 PII 데이터 설계와 증강

> **마지막 업데이트**: 2026년 9월 15일

Python 3.12에서 실행하는 합성 데이터 실습이며 모델 weights·AWS 계정·GPU가 필요하지 않습니다.

데이터 증강의 목표는 파일 수를 늘리는 것보다 **실제로 실패하는 입력 조건을 학습 데이터에 추가하는 것**입니다. 같은 문서를 복사하거나 정답이 어긋난 문장을 많이 만들면 학습량만 늘고 평가를 더 믿기 어려워질 수 있습니다.

이 장에서는 annotation 정책을 정하고, 문서 family를 먼저 분리한 뒤, 정답을 유지하는 변환을 적용합니다. 먼저 작은 CPU 실습을 실행하고, 마지막에 실제 업무용 데이터셋으로 확장할 때 필요한 기준을 정리합니다.

## 1. 무엇을 정답으로 학습시키는가

원문, 엔터티 목록, 모델의 목표 출력은 같은 정보를 나타내야 합니다.

```json
{
  "id": "synthetic-train-example",
  "source_text": "신청인 김가상, 이메일 synthetic.01@example.com",
  "entities": [
    {"type": "PERSON", "original": "김가상"},
    {"type": "EMAIL", "original": "synthetic.01@example.com"}
  ],
  "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.01@example.com"
}
```

`source_text`는 입력 문서이고 `target_tsv`는 학습할 assistant completion입니다. `entities`는 데이터 감사와 평가에 사용합니다. 모델이 최종 마스킹 문서 전체를 생성하도록 학습하는 형식과 다릅니다.

Annotation 가이드를 먼저 작성합니다.

| 결정할 항목 | 예시 | 결정하지 않으면 생기는 문제 |
| --- | --- | --- |
| 유형의 의미 | 개인 연락처는 PHONE, 회사 대표번호는 이 정책에서 negative | 같은 형태에 충돌하는 label |
| 정확한 범위 | 이름의 공백, 전화번호 구분자를 원문 그대로 포함 | source와 정답 불일치 |
| 문맥에 따른 분류 | 문서번호와 계좌번호를 구분 | 숫자를 모두 민감값으로 취급 |
| 반복·중첩 | 같은 이름의 반복, 주소 안의 사람 이름 | annotation과 치환 정책의 차이 |
| 정답 없음 | `entities=[]`, `target_tsv=""` | 모든 문서에 무언가를 출력하도록 학습 |
| 판단 유보 | 판독 불가·미지원 유형·불명확한 문맥 | 추측한 정답이 train에 유입 |

위의 회사 대표번호 분류는 예제의 정책이지 모든 조직에 통용되는 기준이 아닙니다. 이 예제의 문서별 `(TYPE, ORIGINAL)` 형식은 같은 문자열의 여러 등장 위치를 개별 annotation으로 구분하지 못합니다. 위치마다 의미가 다른 데이터가 필요하면 offset/span schema와 평가·치환 코드를 함께 확장합니다.

## 2. 합성 데이터와 데이터 증강 구분하기

- **합성:** 원래 없던 문서를 template·합성 값·생성 모델로 만듭니다.
- **증강:** 승인된 train 문서의 정답 의미를 유지하면서 값·표현·서식·잡음을 바꿉니다.
- **검증:** 변환 후 원문과 정답이 여전히 맞는지 확인합니다. 생성이 성공했다고 정답이 보장되지는 않습니다.

외부 생성 모델을 쓰는 경우에도 후보 데이터로 취급합니다. 원래 값을 외부 API로 보내거나, 생성 모델의 출력을 검토 없이 gold로 확정하는 흐름을 기본값으로 두지 않습니다.

## 3. 증강보다 먼저 family를 분리하기

하나의 원본에서 나온 원문·번역·OCR 변환·paraphrase를 하나의 `family_id`로 묶습니다. 먼저 family를 train/validation/test에 배정하고 그 뒤 train family의 변형만 생성합니다.

```text
family-001 → train      → base + context + layout
family-002 → validation → base
family-003 → test       → base
```

증강한 뒤 레코드를 무작위 분할하면 거의 같은 문서가 train과 test에 동시에 들어갈 수 있습니다. 그룹 키는 provenance를 알아야 정의할 수 있습니다. 새 record ID를 붙였다고 독립적인 고객이나 문서 family가 되는 것은 아닙니다.

| 분리 기준 | 방지하려는 누수 | 별도로 필요한 평가 |
| --- | --- | --- |
| Family | 원문과 그 변형이 다른 split에 들어감 | 새로운 변환/잡음 조건 |
| Entity/customer | 같은 사람·식별자가 양쪽에 반복 | 새 이름·식별자·고객 |
| Template | 같은 서식의 암기 | 처음 보는 서식 |
| Domain/time | 같은 업무·시기의 패턴에 의존 | 새 도메인·미래 기간 |

이 CPU 실습은 **family와 NFC 원문 정확 중복**을 검사합니다. 일부 이름·template·domain은 공유하므로 entity/template/domain 독립성까지 주장하지 않습니다.

## 4. 작은 증강 실습 실행

저장소 루트에서 시작합니다. 생성기는 새 출력 디렉터리만 허용하므로 이미 만들어 둔 디렉터리 자체를 `--output-dir`로 넘기지 않습니다.

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab"
export PII_AUG_RUN="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab/run.XXXXXX")"
export PII_AUG_DIR="$PII_AUG_RUN/dataset"

python3 -m data.augmentation_lab --output-dir "$PII_AUG_DIR" --seed 42
python3 -m data.augmentation_lab --audit-dir "$PII_AUG_DIR"

python3 - <<'PY'
import json
import os
from collections import Counter
from pathlib import Path

root = Path(os.environ["PII_AUG_DIR"])
for split in ("train", "validation", "test"):
    rows = [
        json.loads(line)
        for line in (root / f"{split}.jsonl").read_text().splitlines()
    ]
    print(split, {
        "records": len(rows),
        "families": len({r["provenance"]["family_id"] for r in rows}),
        "negative": sum(not r["entities"] for r in rows),
        "languages": dict(Counter(r["language"] for r in rows)),
    })
PY
```

출력 파일은 `train.jsonl`, `validation.jsonl`, `test.jsonl`, `augmentation-manifest.json`입니다.

| Split | Family | 레코드 | 한국어 / 영어 | 음성 레코드 |
| --- | ---: | ---: | ---: | ---: |
| train | 24 | 72 | 36 / 36 | 36 |
| validation | 8 | 8 | 4 / 4 | 4 |
| test | 8 | 8 | 4 / 4 | 4 |

40 family를 언어·양성/음성별로 나눠 6/2/2 family씩 배정합니다. Train은 원본과 두 변형을 포함하고, validation/test는 원본만 남깁니다. 50% negative와 한영 50/50은 실습을 쉽게 비교하기 위한 구성으로 실제 업무의 출현 비율을 추정한 값이 아닙니다.

이 작은 실습은 PERSON·EMAIL·PHONE 세 유형을 사용합니다. 기존 generator의 9유형 데이터와 목적이 다릅니다. 세 유형의 작은 세트로 RRN·CARD 등 다른 유형의 품질을 평가할 수는 없습니다.

## 5. 레코드의 계보와 변환 읽기

기존 loader가 사용하는 필드는 유지하고 `provenance`를 추가합니다.

| 필드 | 의미 |
| --- | --- |
| `id` | 변형마다 다른 레코드 ID |
| `language`, `domain` | 집계와 오류 분석에 쓰는 구분 |
| `provenance.family_id` | 원문과 변형의 같은 family |
| `provenance.split` | 변형을 만들기 전에 정한 배정 |
| `provenance.parent_id` | 변형이 나온 base 레코드 |
| `provenance.augmentation` | 적용한 변환의 이름 |

Provenance와 양성/음성 구분은 감사용 metadata입니다. 기존 loader처럼 user prompt에는
`source_text`만 넣고, split·정답 유무·gold label을 힌트로 붙이지 않습니다.
`target_tsv`는 학습할 assistant completion에 둡니다.

실행 코드에는 두 종류의 변형이 있습니다.

1. **문맥 wrapper:** 합성 문서의 앞뒤 문맥을 바꿉니다. PII의 값과 annotation 의미는 유지합니다.
2. **Layout/Unicode 변형:** 항목 순서와 배치를 바꾸고 한글 변형에 NFD 표현을 사용합니다. 원문과 `original`을 함께 만들고, 새 순서에 맞춰 TSV를 다시 생성합니다.

NFD는 한글을 자모 등으로 분해한 표현이고 NFC는 정규 조합 표현입니다.
보이는 글자가 같아도 byte가 다를 수 있어 정확 원문 비교 전에 NFC로 정규화합니다.

빈 정답인 negative도 변형 후 빈 정답을 유지합니다. 문자 정규화나 순서 변경을 했다는 이유로 없던 엔터티를 만들지 않습니다. 이 변형만으로 실제 스캐너·OCR 엔진의 잡음 분포가 재현됐다고 주장하지 않습니다.

## 6. 엔터티 치환은 원문과 label을 같이 만들기

이 예시는 같은 유형의 합성 값을 바꿔 새 train 후보를 만드는 최소 패턴입니다. 일반 문서에 문자열 replace를 무조건 적용하는 코드가 아닙니다.

```python
def render_training_candidate(person, email):
    source = f"신청인: {person}\n이메일: {email}"
    entities = [
        {"type": "PERSON", "original": person},
        {"type": "EMAIL", "original": email},
    ]
    target = "\n".join(
        f"{entity['type']}\t{entity['original']}" for entity in entities
    )
    assert all(entity["original"] in source for entity in entities)
    return {"source_text": source, "entities": entities, "target_tsv": target}

base = render_training_candidate("김가상", "synthetic.base@example.com")
variant = render_training_candidate("이샘플", "synthetic.variant@example.com")
assert base["source_text"] != variant["source_text"]
```

실제 augmentation pipeline에 넣을 때는 train에서 허용한 entity bank만 사용하고 family·parent·seed·operator 버전을 기록합니다. Holdout의 값 목록이나 실패 사례를 학습용 bank로 끌어오면 분리 목적이 깨질 수 있습니다. 위 코드는 별도 최소 설명 예제이며 앞의 CLI가 자동으로 실행하는 세 번째 operator는 아닙니다.

## 7. 확장할 증강 방법과 정답 검증

| 방법 | 노리는 실패 조건 | 통과시켜야 하는 검사 |
| --- | --- | --- |
| 같은 유형의 값 치환 | 이름/번호 암기 | 유형 유지, 모든 등장 위치·gold 동시 갱신 |
| 서식 재배치 | 표·폼·상담 기록 차이 | 필드 순서와 TSV 일치, 누락 필드 검사 |
| 제한된 OCR/띄어쓰기 | 구분자·줄바꿈·문자 표현 변화 | 변환된 원문 기준의 annotation과 경계 |
| 문맥 paraphrase | 특정 문장 template 의존 | 새로운 PII 추가/삭제 여부, 의미 보존 |
| Back-translation | 표현 다양성 | 이름·주소·숫자 변형과 재annotation 확인 |
| Hard negatives | 문서번호/금액을 PII로 오인 | positive와 같은 모양, 다른 문맥 |
| 희귀 유형 보강 | RRN·CARD 등 적은 사례 | 지원 유형별 개수와 문맥의 다양성 |
| 긴 문서·경계 사례 | 잘림·chunk 경계의 누락 | tokenizer 길이, offset, 중복/경계 처리 |
| 지시문 삽입 사례 | 원문을 지시로 따름 | 문서를 데이터로 취급, TSV 계약 준수 |

Paraphrase와 back-translation 결과에는 자동 검증으로 확인하지 못하는 annotation 오류가 남을 수 있습니다. 원문 문자열 포함 검사만으로 gold의 완전성과 의미를 검증했다고 하지 않습니다. 새 후보를 검토하고 승인한 뒤 train에 포함합니다.

## 8. 데이터 감사가 막는 오류

`--audit-dir`은 이 실습 생성물의 계약을 검증합니다.

- 파일 해시와 manifest, split·언어·negative 개수.
- ID와 NFC 원문의 정확 중복.
- Family의 split 소유권과 parent/변형 연결.
- Validation/test에 train용 변형이 섞이지 않았는지.
- 허용 label, 원문에 있는 값, entities와 TSV의 일치.
- Seed로 재생성한 실습 내용과의 일치.

마지막 항목 때문에 label 하나를 빼고 파일 해시도 다시 계산하는 변경까지 거부할 수 있습니다. 이는 **정해진 합성 실습의 재현성 검사**이며 임의의 고객 데이터에 쓸 수 있는 범용 gold validator는 아닙니다. Hash는 데이터 생산자의 신원이나 신뢰성을 인증하는 서명이 아닙니다.

학습 실험 전에 이런 조건을 실패로 처리하면 누수가 포함된 결과를 나중에 모델 문제로 분석하는 일을 줄일 수 있습니다. 다만 near-duplicate, annotation 의미, tokenizer 길이, PII 완전성은 별도 검사 대상입니다.

## 9. 기존 2,200개 데이터와 함께 읽기

기존 generator 1.0.0의 seed 42·split 해시는 [Part 2](02-pii-data-tokenization.md)에 보존돼 있습니다. 이번 CPU 재생성에서도 해당 해시는 유지됩니다.

NFC 원문 전체를 비교하면 기존 corpus에는 다음 정확 중복이 관찰됩니다.

| 비교 | 공통 NFC 원문 수 |
| --- | ---: |
| train / validation | 22 |
| train / test | 36 |
| validation / test | 9 |

두 개 이상의 split에 등장하는 고유 원문 그룹은 총 51개입니다. Pair별 교집합에는 세 split 모두에 있는 원문이 중복 계산되므로 단순 합산한 값과 다릅니다. 이 관찰은 기존 corpus를 새롭게 “누수 없는 평가 세트”로 해석하면 안 된다는 구체적인 이유입니다.

새 실습은 역사적 데이터를 덮어쓰거나 그 성능을 다시 발표하지 않습니다. 9유형 업무용 버전을 만들 때는 기존 값·서식을 무작위 재분할하기보다 family/고객/template provenance를 확보하고 새 manifest와 평가 버전을 만듭니다.

## 10. SageMaker 학습 입력으로 확장하기

실습 JSONL은 기존 `src.dataset`의 prompt/completion 변환에 사용할 수 있는 필드를 가집니다. 그러나 augmentation manifest는 기존 uploader의 `dataset-manifest.json`을 그대로 대체하는 파일이 아닙니다.

실제 학습 버전은 다음을 함께 준비합니다.

1. 승인된 train/validation/test와 사용한 annotation·증강 정책.
2. 실제 count와 SHA-256에 맞는 업로더 입력 manifest.
3. 실제 데이터 규모·모델·학습 budget에 맞는 `config/experiment.yaml`.
4. 그 설정이 들어 있는 source bundle과 동일 버전의 로컬 제출 설정.
5. 지원되는 런타임 검증과 학습 안에서 관측한 입력 hash/count.

현재 source bundler와 uploader는 기존 패키지의 고정 경로를 사용합니다. `--output-dir`로 만든 실습 디렉터리가 자동으로 SageMaker 학습에 연결되는 기능은 없습니다. 새 dataset release를 별도 작업 복사본에서 통합·검증하고, [QLoRA 실습](05-qlora-finetuning-workshop.md)과 [실행 계약](03-sagemaker-mlflow-execution.md)에 맞춰 제출합니다.

증강 효과는 같은 validation, 같은 decoding, 같은 비교 budget에서 **원본 train 대 증강 train**으로 비교합니다. Step 수가 같아도 학습 레코드 수나 token 길이가 달라지면 본 데이터의 양이 달라질 수 있으므로 example/token budget도 함께 기록합니다.

## 이해 확인

1. 증강 후 무작위 split이 위험한 이유는? **같은 원문의 변형이 train과 holdout에 동시에 들어갈 수 있습니다.**
2. 새 ID를 붙이면 고객 누수가 사라지는가? **아닙니다. 고객·원본 계보가 같은지 확인해야 합니다.**
3. 이름만 바꾸고 TSV를 유지해도 되는가? **아닙니다. 원문과 gold를 함께 갱신해야 합니다.**
4. 이 실습이 새 template에 대한 성능을 보장하는가? **아닙니다. Template을 공유하며 모델 평가도 수행하지 않습니다.**
5. 증강을 많이 했는데 품질이 나빠지면? **오류 label·중복·분포 왜곡·학습 budget을 먼저 점검하고 validation으로 비교합니다.**

## 참고 자료

- [학습·시험 분리와 전처리 누수](https://scikit-learn.org/stable/common_pitfalls.html)
- [Grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [Dai and Adel: NER 데이터 증강 분석](https://aclanthology.org/2020.coling-main.343/)
- [CheckList: NLP 행동 검증](https://aclanthology.org/2020.acl-main.442/)
- [기존 데이터와 치환 구현 설명](02-pii-data-tokenization.md)

다음: [QLoRA 학습 실습](05-qlora-finetuning-workshop.md) · [평가와 비식별화](07-pii-evaluation-release.md)

[실습 퀴즈](../../quizzes/ai-ml/sagemaker-ai/06-data-augmentation-workshop-quiz.md)
