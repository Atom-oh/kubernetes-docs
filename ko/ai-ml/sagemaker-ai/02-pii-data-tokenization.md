# Part 2: 합성 PII 데이터와 결정론적 토큰화

> 구현·문서 검토: 2026-09-12. Generator 1.0.0 / seed 42의 기존 데이터 해시는 유지했습니다.

## 추출 후보와 치환을 분리

모델 출력 계약은 한 줄당 `TYPE<TAB>ORIGINAL`입니다.
다음은 합성 예시이며 모델이 문서를 직접 다시 작성하지 않습니다.

```text
PERSON	김가상
EMAIL	synthetic.ko.408@example.com
```

Parser는 허용 유형과 source 일치를 검사합니다. 이 검사는 값이 실제 PII인지,
유형이 맞는지 또는 모델이 모든 PII를 찾았는지를 증명하지 않습니다.
최종 치환과 원문 표기 복원은 별도 코드가 담당하며 token mapping은 민감한 값으로 취급합니다.

## 데이터와 평가 범위

총 2,200개 문서이며 split별 한국어/영어 비율은 80/20입니다.
구현 수정 후 다시 생성해 기존 manifest 해시가 유지되는 것을 확인했습니다.

| Split | Records | Korean | English | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| train | 1,600 | 1,280 | 320 | `b98429fef0b103f24e8eaded069cbd2f6def5fbf8c083a5c7baf366c9fc1d21a` |
| validation | 200 | 160 | 40 | `25ca38198d38e04be181e15b4e21a3c96d672f46f775ae1bc6c422ee4514f820` |
| test | 400 | 320 | 80 | `6f6ef9a6b42297738b292d5149f2e6e323f7bcd6f2325b6bfbc04ae6d9d0ec21` |

유형은 PERSON, RRN, DOB, REL, ADDRESS, PHONE, EMAIL, ACCOUNT, CARD입니다.
이는 이 실험의 annotation 정책입니다. 관계 단어는 positive에 포함되고 회사
대표번호 등 일부 문자열은 negative 문서에 포함됩니다.
모든 업무에 통용되는 민감도 분류라고 해석하지 않습니다.

생성기는 정해진 template·작은 이름 목록·합성 숫자를 사용합니다.
RRN/CARD는 예제의 checksum 함수에 실패하도록 만들지만 이것만으로 공식 유효성이나
미할당을 증명하지는 않습니다. PHONE은 합성 placeholder이며 국가별 번호 형식이나
공식 예약 대역을 검증한 것이 아닙니다. 고객 자료를 사용하지 않았다는 사실과
실제 식별자 검증은 다릅니다.

Train/validation/test의 record/hash가 다르더라도 template·이름·표현은 공유될 수 있습니다.
이 데이터의 성능을 실제 업무나 unseen entity/template 일반화 성능으로 제시하지 않습니다.
실제 평가에는 별도 holdout과 annotation 검토가 필요합니다.

## 원문 표기를 복원하는 치환 파이프라인

수정한 구현은 다음 순서를 따릅니다.

1. Source와 값을 NFC로 정규화하고 type/value의 바깥 공백을 정리합니다.
2. 완결된 `<think>...</think>` 블록을 제거하고 tab이 있는 행에서 허용 유형과 비어 있지 않은 값을 읽습니다.
3. 중복 후보를 제거하고 literal 또는 제한된 variant가 source에 실제로 일치하는지 확인합니다.
   숫자 경계는 parser와 치환에서 같은 규칙을 사용합니다.
4. Literal prediction은 다른 prediction이 만든 variant보다 우선합니다.
   같은 값에 여러 type이 있으면 고정 우선순위를 적용하며 의미적 정답을 추론하지는 않습니다.
5. 긴 pattern 우선의 정규식으로 source를 한 번 스캔합니다.
6. **실제 일치한 NFC 표기와 type별**로 source 순서에 따라 token을 할당합니다.
   같은 표기는 재사용하고, 공백·구분자가 다른 표기는 복원을 위해 별도 token을 사용합니다.
7. Source에 이미 있는 token 모양 문자열은 새 token 이름에서 제외합니다.
8. Mapping에는 **실제로 가린 source 표기**를 저장하고,
   `spans`에는 NFC source의 반열린 구간 `[start, end)`을 기록합니다.

```text
Source: 김가상 / 김 가 상 / [PERSON_1]
Candidate: PERSON	김가상
Masked: [PERSON_2] / [PERSON_3] / [PERSON_1]
```

기존 marker는 그대로 남고 두 표기는 각각 복원됩니다.
Token 번호가 항상 1부터 시작하는 것은 아니며, token 일치가 동일한 실세계 인물을
판별한다는 뜻도 아닙니다.

`PERSON` variant는 공백을 제거한 2–6문자 이름의 제한된 공백/tab/줄바꿈 형태입니다.
숫자형 variant는 정해진 숫자·공백·구분자만 정규화합니다. 임의의 문자를 제거해
숫자만 맞추지 않습니다. Source에 없는 `alias123456`을 ACCOUNT 후보로 주었다고
source의 `123456`을 찾아 통과시키지 않습니다. 문자가 포함된 원본 값도 실제
source에 literal로 있으면 일치할 수 있습니다. 공식 전화/계좌/신분번호 validator는 아닙니다.

`reassemble_text`는 알려진 token을 한 번 치환하고 모르는 token은 보존합니다.
Round-trip 비교는 평가 코드가 수행합니다. NFC 동일성을 검사하므로 원래 NFD byte
표현까지 동일하다는 의미는 아닙니다.

## Placeholder 내용 대신 source 구간으로 누출 확인

기존 구현은 치환 결과에 정답 original 전체가 남아 있는지만 검사했습니다.
이는 다음 두 경우에 잘못된 결과를 냈습니다.

- 정답 `Alpha Beta` 중 `Alpha`만 가리면 전체 문자열이 없어져 누출이 0으로 나왔습니다.
- 원문 값이 `PERSON`이면 생성한 `[PERSON_1]` 안에 그 단어가 있어 누출로 오인했습니다.

수정한 평가는 source에서 찾은 정답 값/허용 variant의 각 구간이 실제 치환 구간의
합집합으로 **완전히 가려졌는지** 확인합니다. 반복 등장도 모두 확인합니다.
부분 구간이나 구분자가 남으면 이 보수적인 coverage 지표에서는 미가림으로 셉니다.
Token 이름의 문자나 숫자는 source 노출로 세지 않습니다.

Gold schema에는 annotation offset이 없으므로 구간은 알려진 값을 source에서
검색해 추론합니다. 실제 PII를 새로 탐지하는 검사가 아니며 문맥상 민감하지 않은
동일 문자열도 일치할 수 있습니다. Annotation 정책에 맞게 해석하며 개인정보
보호의 완전성을 보증하는 값으로 사용하지 않습니다.

## 평가 지표의 정확한 의미

| 결과 필드 | 계산 의미 |
| --- | --- |
| entity/per_type precision·recall·F1 | 문서별 정규화 `(TYPE, ORIGINAL)` 집합의 TP/FP/FN 합산 |
| documents.leak_rate | 정답 구간에 미가림이 있는 문서 / 전체 문서 |
| entities.leak_rate | 일치 구간 중 미가림이 있는 고유 정답 pair / 고유 정답 pair |
| entities.over_redaction_rate | 기존 이름을 유지한 **추가 추출 pair 비율**, 즉 FP / predicted pair |
| entities.hallucination_rate | Source에 일치하지 않는 허용 유형의 비어 있지 않은 TSV row / 해당 row |
| parse.success_rate | Caller의 parse_success flag가 True인 문서 비율 |
| tokenization.deterministic_rate | 후보 순서를 뒤집었을 때 masked text·mapping·spans가 같은 비율 |
| tokenization.round_trip_rate | Mapping 복원 결과가 NFC source와 같은 비율 |

Entity F1은 span-level NER F1이 아닙니다. 문서 안의 같은 pair는 중복 제거하고,
서로 다른 문서의 같은 값은 별도로 셉니다. Type은 trim/uppercase, 값은 trim/NFC로 비교합니다.
Variant로 완전히 가려도 model ORIGINAL과 gold 표기가 다르면 FP/FN이 생길 수 있습니다.
따라서 기존 over_redaction 필드도 실제로 불필요하게 지운 문자 비율과 동일하지 않습니다.

Hallucination은 parse flag와 별도로 source 일치 여부를 계산합니다.
허용되지 않은 type이나 일반 prose는 해당 row 분모에 포함되지 않습니다.
현재 inference helper는 빈 출력 또는 하나 이상의 source-matching row가 있으면
parse flag를 True로 설정하므로 **모든 행이 완전한 형식이라는 증거가 아닙니다**.
평가기는 False flag의 후보를 entity 예측에서 제외합니다.

분모가 0이면 rate는 0이며 빈 entity 집합의 F1도 이 구현에서는 0입니다.
Duplicate record/prediction ID, 평가 대상에 없는 prediction ID, source와 맞지 않는
gold annotation은 오류로 거부합니다. 오류 메시지에 raw entity 값을 넣지 않습니다.

## 학습 레코드와 검증 범위

JSONL은 `source_text`, `entities`, `target_tsv`를 가지며 loader는 system/user prompt와
assistant completion으로 변환합니다. Trainer는 completion-only loss를 요청하지만
실제 tokenizer/template·길이 제한·loss mask와 GPU 실행은 별도로 검증해야 합니다.
원문·completion·mapping을 일반 로그나 MLflow parameter/tag에 기록하지 않는 정책을 유지합니다.

기존 placeholder 충돌, 표기 복원 손실, 숫자 variant 오허용과 평가 오류를 재현한 뒤 수정했습니다.
로컬 테스트 50개가 통과했고, 기존 2,200개 정답을 예측으로 입력한 oracle 점검에서
해시·결정론·복원·coverage를 확인했습니다.
**Oracle 점검은 모델 예측 결과나 fine-tuned F1 측정이 아닙니다.**
GPU 학습이나 실제 고객 PII 처리는 수행하지 않았습니다.

## 참고 자료

- [Synthetic generator](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/data/generate_dataset.py)
- [Dataset manifest](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/data/dataset-manifest.json)
- [Parser and replacement](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py)
- [Evaluation implementation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/metrics.py)

[Previous: Platform architecture](01-platform-architecture.md)

[Next: SageMaker / MLflow execution](03-sagemaker-mlflow-execution.md)

[Quiz](../../quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md)
