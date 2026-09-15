# 실습: PII 모델 평가와 비식별화 파이프라인

> 검토 기준: 2026-09-15. 이 장의 실행 예제는 합성 레코드와 수동 예측을 사용하는 CPU 실습입니다. 실제 학습 모델의 성능 수치가 아닙니다.

학습 loss가 내려갔다고 PII 제거가 잘되는 것은 아닙니다. 이름은 찾지만 이메일을 놓칠 수도 있고, 개인정보가 아닌 문서번호까지 가릴 수도 있습니다. 이 장에서는 **추출 모델과 실제 치환 결과를 함께 평가**하고, 어떤 오류를 데이터 보강으로 해결할지 판단합니다.

먼저 [QLoRA 학습 실습](05-qlora-finetuning-workshop.md)과 [데이터 증강 실습](06-data-augmentation-workshop.md)을 읽습니다. 실행 명령은 저장소 루트에서 시작하며 Python 3.12를 사용합니다.

## 1. 모델의 책임과 처리 코드의 책임

이 예제의 모델은 완성된 비식별 문서를 생성하지 않습니다. 문서에서 찾은 후보를 `TYPE<TAB>ORIGINAL`로 출력합니다.

| 단계 | 입력 → 출력 | 확인할 항목 |
| --- | --- | --- |
| 추출 | 원문 → 유형·원문 값 후보 | 누락, 잘못된 유형, 원문에 없는 값 |
| 검증 | 후보 → 원문에 일치하는 허용 후보 | 형식, 길이, 허용 유형, source 일치 |
| 치환 | 원문·후보 → 치환 문서·mapping·구간 | 반복 등장, 부분 가림, 충돌, 중첩 |
| 잔여 검사 | 치환 결과 → 승인 또는 검토 대기 | 별도 규칙/탐지기, 정책, 미지원 입력 |
| 전달 | 승인된 문서 → 다음 시스템 | mapping 전달 금지, 접근 제어, 기록 범위 |

원문에 일치한다는 검사는 **후보가 원문에 있다는 사실**을 확인합니다. 후보의 의미가 맞거나 다른 PII가 없다는 뜻은 아닙니다. 서로 다른 탐지기를 결합해도 그 오류가 독립적이라고 가정해서는 안 됩니다.

`pseudonymize_text()`는 복원 가능한 token mapping을 만듭니다. `[PERSON_1]`로 바꾸고 mapping을 보관하는 방식과, 복원 기능 없이 값을 삭제하는 방식은 목적이 다릅니다. Mapping을 버렸다는 이유만으로 나머지 문맥에서 사람을 식별할 수 없다고 결론 내리지 않습니다.

## 2. 학습·검증·최종 시험의 역할을 고정하기

1. **Train:** 모델 파라미터를 갱신하고 학습용 증강을 적용합니다.
2. **Validation:** rank, learning rate, epoch/step, 데이터 혼합 비율, 출력 규칙을 선택합니다.
3. **Locked test:** 선택이 끝난 모델과 처리 정책을 최종 평가합니다.
4. **Challenge set:** OCR, 긴 문서, 새로운 서식, 희귀 유형, 지시문 삽입 등 실패하기 쉬운 조건을 별도로 확인합니다.

최종 test에서 실패를 보고 데이터를 고친 뒤 다시 같은 test를 보면서 선택하면, 그 test도 개발 과정에 사용된 것입니다. 결과를 숨기지 말고 새로운 평가 버전을 준비합니다. 문서 family·고객·서식·시간 기준 중 어떤 축을 분리했는지도 함께 기록합니다.

**현재 역사적 `src/train.py`는 매 실행에서 `test_records`로 baseline과 tuned 지표를 계산합니다.** 이 동작을 그대로 반복 HPO에 사용하지 않습니다. 실제 튜닝 루프를 만들 때는 후보 선택용 평가를 validation으로 분리하고, 최종 test를 읽는 별도 단계와 그 접근 기록을 구현해야 합니다. 아래 CPU 예제는 그 launcher를 실행하지 않습니다.

## 3. CPU에서 “F1이 올라도 문제가 남는 경우” 재현하기

다음 두 문서를 사용합니다.

- 양성 문서: 합성 이름과 `example.com` 이메일이 정답입니다.
- 음성 문서: 문서번호는 이 annotation 정책에서 PII가 아닙니다.

Baseline은 이름만 찾고, candidate는 이름·이메일을 모두 찾지만 음성 문서의 번호도 계좌로 잘못 분류하게 만듭니다. 모델 호출 없이 예측을 직접 구성하므로 지표의 의미를 검산할 수 있습니다.

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}"
export PII_EVAL_DIR="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/pii-evaluation.XXXXXX")"
python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
records = [
    {
        "id": "positive-1",
        "source_text": "담당자 김가상, 이메일 synthetic.ko.01@example.com",
        "entities": [
            {"type": "PERSON", "original": "김가상"},
            {"type": "EMAIL", "original": "synthetic.ko.01@example.com"},
        ],
        "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.ko.01@example.com",
    },
    {
        "id": "negative-1",
        "source_text": "문서번호 DOC-2026-001의 처리 상태를 확인합니다.",
        "entities": [],
        "target_tsv": "",
    },
]
baseline = [
    {"id": "positive-1", "content": "PERSON\t김가상", "parse_success": True},
    {"id": "negative-1", "content": "", "parse_success": True},
]
candidate = [
    {
        "id": "positive-1",
        "content": records[0]["target_tsv"],
        "parse_success": True,
    },
    {
        "id": "negative-1",
        "content": "ACCOUNT\tDOC-2026-001",
        "parse_success": True,
    },
]
for name, rows in (
    ("gold", records), ("baseline", baseline), ("candidate", candidate)
):
    with (out / f"{name}.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
PY

for phase in baseline candidate; do
  python3 -m src.evaluate \
    --test-jsonl "$PII_EVAL_DIR/gold.jsonl" \
    --predictions-jsonl "$PII_EVAL_DIR/$phase.jsonl" \
    --output-json "$PII_EVAL_DIR/$phase-metrics.json" \
    --environment cpu-demo --phase "$phase-demo" \
    --model-id synthetic-fixture-no-model \
    --duration-seconds 0 --hourly-usd 0
done

python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
for phase in ("baseline", "candidate"):
    m = json.loads((out / f"{phase}-metrics.json").read_text())["metrics"]
    print(phase, json.dumps({
        "entity": m["entity"],
        "leaked_documents": m["documents"]["leaked"],
        "extra_pairs": m["entities"]["over_redacted"],
        "round_trip": m["tokenization"]["round_trip_rate"],
    }))
PY
```

여기서 `--test-jsonl`은 평가 CLI의 인자 이름입니다. 수동으로 만든 연습 파일을 지정한 것이며 최종 holdout을 여는 명령이 아닙니다.

예상 결과는 다음과 같습니다.

| 지표 | Baseline | Candidate |
| --- | ---: | ---: |
| TP / FP / FN | 1 / 0 / 1 | 2 / 1 / 0 |
| Precision | 1 | 2/3 |
| Recall | 1/2 | 1 |
| Entity F1 | 2/3 | 0.8 |
| 미가림 정답을 포함한 문서 수 | 1/2 문서 | 0/2 문서 |
| 추가 추출 pair | 0 | 1 |
| Round-trip rate | 1 | 1 |

Candidate의 F1은 올랐지만 문서번호를 가리는 오류가 생겼습니다. 두 경우 모두 round-trip은 성공하므로 **복원 성공률은 PII 탐지 품질을 대신할 수 없습니다.** `duration`과 `hourly`의 0은 이 수동 fixture 실습의 값이며 GPU 학습 비용이 0이라는 의미가 아닙니다.

## 4. 같은 이름의 지표라도 계산 단위를 확인하기

이 패키지의 `entity`와 `per_type`은 문서별 `(TYPE, ORIGINAL)` 집합을 비교합니다. 동일 문서의 같은 pair는 한 번 세며, 별도 span annotation에 기반한 NER F1은 아닙니다.

| 지표 | 판단에 사용하는 방법 | 함께 확인할 한계 |
| --- | --- | --- |
| 유형별 recall | 어떤 PII를 놓치는지 찾기 | 희귀 유형의 평가 개수도 제시 |
| 유형별 precision | 비민감 문맥까지 가리는지 확인 | annotation 정책이 일관되어야 함 |
| 문서 leak rate | 하나라도 덜 가려진 문서의 비율 | 정답에 없는 PII는 측정할 수 없음 |
| Entity leak rate | 정답 값의 일치 구간이 모두 가려졌는지 확인 | 값 검색으로 구간을 추론; 실제 offset gold와 다름 |
| `over_redaction_rate` | FP / predicted pair | 실제로 불필요하게 삭제한 문자 비율이 아님 |
| `hallucination_rate` | 원문에 없는 허용 TSV 후보 비율 | 허용되지 않은 유형·일반 문장은 분모에서 제외 |
| Parse success | 호출자가 설정한 형식 처리 상태 | 현재 helper는 일부 유효 행만 있어도 성공으로 봄 |

배포용 strict parser는 모든 행의 문법과 허용 유형을 확인하고, 잘못된 행·잘린 출력·처리 길이 초과를 명시적인 실패 상태로 반환하도록 설계합니다. 잘못된 행을 조용히 버리고 “PII 없음”으로 전달하면 안 됩니다. 현재 `parse.success_rate`만으로 이 strict 동작이 구현됐다고 판단하지 않습니다.

정답이 없는 운영 문서에서는 학습 때와 같은 leak rate를 계산할 수 없습니다. 별도의 표본 annotation, 잔여 탐지, 거절/검토 대기 비율을 관찰하고 측정 범위를 구분합니다.

## 5. 오류를 다음 데이터 작업으로 연결하기

평균 F1 한 개 대신 문서별 오류를 **접근이 제한된 평가 공간**에서 분석합니다. 일반 로그에는 원문 대신 오류 유형·문서 길이 구간·언어·서식 ID·집계 개수를 남깁니다.

| 관찰한 오류 | 먼저 점검할 것 | 다음 실험 |
| --- | --- | --- |
| 이름은 찾지만 계좌를 놓침 | 유형별 정답 개수, annotation 누락 | 계좌 문맥의 train 사례 보강 |
| 띄어쓴 이름/OCR에서 실패 | 원문과 label 표기 일치 | 변환된 원문에 맞춰 label도 바꾼 증강 |
| 문서번호를 계좌로 분류 | 음성 사례·문맥 대비 | 같은 숫자 형태의 positive/negative 쌍 추가 |
| 긴 문서 끝부분의 PII 누락 | prompt truncation, completion 길이 | chunk 경계·overlap·offset 복원 평가 |
| 드문 이름에서 성능 급락 | 이름이 train/test에서 공유됐는지 | entity-held-out 평가와 새 train family |
| 새 서식에서 급락 | template 분리 여부 | template-held-out 평가; 승인된 새 train 서식 |
| 원문 지시문에 따라 설명 출력 | 문서를 데이터로 취급하는지 | 합성 지시문 삽입 사례와 출력 schema 검사 |
| Loss는 감소하지만 recall 악화 | validation 오염, 과적합, 출력 길이 | checkpoint 비교·early stopping 기준 재검토 |

틀린 test 사례를 그대로 train에 복사한 뒤 같은 test 점수를 개선 결과로 발표하지 않습니다. 오류 분석용 세트가 개발에 사용됐다는 사실과 새 최종 평가 세트를 기록합니다.

## 6. 긴 문서는 학습 길이와 추론 길이를 함께 설계하기

`max_sequence_length=1024`는 “문서 1,024글자”가 아닙니다. Chat template, system instruction, 원문, 정답 completion이 tokenizer의 token 예산을 사용합니다. 한글·영문·숫자의 token 개수도 같지 않습니다.

- 학습 시 정답 token이 잘려 loss에 남지 않는 레코드가 없는지 확인합니다.
- 추론 시 잘린 원문 부분에 있던 PII를 “없다”고 평가하지 않습니다.
- Chunk로 나누면 원문 offset, 중복 탐지, 경계에 걸친 이름·번호, 반복 등장 처리까지 평가합니다.
- Chunk overlap만으로 충분하다고 가정하지 말고, PII가 경계에 걸리도록 만든 challenge 문서를 사용합니다.
- 최대 길이를 넘거나 출력이 중간에 끝나면 부분 결과를 완전한 처리로 표시하지 않습니다.

## 7. 배포 승인표를 먼저 작성하기

아래는 **팀이 측정값과 기준을 채우는 승인표**입니다. 이 저장소가 달성한 성능이나 모든 업무에 적용되는 고정 기준이 아닙니다.

| 항목 | 남길 증거 | 미달 시 조치 |
| --- | --- | --- |
| 정답·데이터 분리 | annotation 버전, family/split/hash, subgroup 개수 | 평가 재구성 |
| 후보 선택 | validation 비교표, 바꾼 변수, 선택 이유 | 추가 실험 |
| 최종 품질 | locked test의 유형별 지표와 오류 개수 | 배포 보류 |
| 출력 계약 | 빈 출력·잘못된 행·잘린 응답의 처리 시험 | parser/거절 경로 수정 |
| 처리 정책 | 치환 구간, mapping 수명, 잔여 검사 | 정책·처리 코드 수정 |
| 운영 특성 | 길이별 latency·memory·timeout·처리량 | 용량/길이 제한 조정 |
| 재현·복구 | base/tokenizer revision, adapter hash, 환경, 이전 버전 | 패키징 보완 |

F1, recall, latency 같은 기준은 용도에 맞춰 **평가 전에** 정합니다. 작은 세트에서 오류 0건이 관찰됐다고 실제 오류 확률이 0이라고 보고하지 않습니다. Subgroup 결과에는 분자·분모를 함께 제시합니다.

## 8. SageMaker 출력에서 서비스용 패키지로

Training Job의 `Completed`는 학습 작업의 종료 상태입니다. Endpoint의 생성, adapter 로드, 출력 계약 검사, 비식별화 승인은 별도 단계입니다.

1. `/opt/ml/model`과 MLflow에서 adapter·설정·집계 결과를 보존합니다.
2. Adapter와 함께 사용할 정확한 base model/tokenizer revision, chat template, quantization 설정, parser 버전을 묶어 기록합니다.
3. 같은 환경에서 adapter 재로딩과 결정론적 decoding을 시험합니다. Adapter만으로 standalone 모델 전체를 대체할 수는 없습니다.
4. Shadow 또는 제한된 canary 흐름에서 길이·출력 형식·오류율을 관찰합니다.
5. 이전 **모델+tokenizer+parser+정책** 조합으로 되돌릴 수 있게 버전을 관리합니다.

이 장은 endpoint나 strict release wrapper를 구현·배포하지 않습니다. 실제 배포에서는 raw source·completion·mapping이 CloudWatch, MLflow autolog/tracing, 오류 메시지, 요청 추적에 포함되는 경로도 시험해야 합니다. 최종 adapter 역시 학습 데이터의 영향을 받은 산출물이므로 공개 가능 여부를 별도로 검토합니다.

## 이해 확인

1. 위 candidate의 F1이 높아도 바로 배포할 수 없는 이유는? **음성 문서의 추가 가림이 생겼고, 합성 두 문서는 대표성 있는 평가가 아닙니다.**
2. Round-trip 100%이면 PII가 모두 제거됐는가? **아닙니다. 가린 값의 복원만 성공했을 수 있습니다.**
3. 같은 test로 rank를 여러 번 골랐다면? **그 세트는 모델 선택에 사용됐으므로 독립적인 최종 시험으로 취급하지 않습니다.**
4. 원문에 있는 값을 출력했으면 올바른 PII인가? **아닙니다. 이 실습의 문서번호가 반례입니다.**
5. 정답 없는 운영 트래픽의 leak rate를 모델 출력만으로 계산할 수 있는가? **이 평가기의 gold 기반 leak rate는 계산할 수 없습니다.**

## 참고 자료

- [이 저장소의 평가 CLI](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/evaluate.py)
- [지표의 실제 계산 구현](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/metrics.py)
- [치환·복원 구현](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py)
- [PEFT checkpoint 형식](https://huggingface.co/docs/peft/v0.17.0/en/developer_guides/checkpoint)
- [SageMaker 컨테이너 디렉터리](https://docs.aws.amazon.com/sagemaker/latest/dg/amazon-sagemaker-toolkits.html)
- [Presidio Anonymizer의 연산과 복원 모델](https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/README.md)

이전: [데이터 증강 실습](06-data-augmentation-workshop.md) · [학습 경로](README.md)

[실습 퀴즈](../../quizzes/ai-ml/sagemaker-ai/07-pii-evaluation-release-quiz.md)
