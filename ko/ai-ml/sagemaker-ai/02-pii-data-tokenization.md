# Part 2: 합성 PII 데이터와 결정론적 토큰화

> **마지막 업데이트**: 2026년 9월 2일

## 학습 계약

모델 프롬프트는 문서에서 허용된 PII 유형을 찾아 **원문 그대로** 반환하도록 제한합니다. 출력 형식은 한 줄당 하나의 `TYPE<TAB>ORIGINAL`입니다.

```text
PERSON	김가상
EMAIL	synthetic.ko.408@example.com
```

이 값은 저장소의 `review-sample.jsonl`에서 가져온 완전 합성 예시입니다. 숫자형 식별자는 문서 예시에서 노출하지 않습니다.

모델 출력으로 바로 원문을 수정하지 않는 이유는 세 가지입니다.

- 모델이 존재하지 않는 값을 만들면 source-containment 검사에서 제거할 수 있습니다.
- 원문 위치와 길이를 기준으로 치환 순서를 결정해 중첩·부분 일치를 제어할 수 있습니다.
- token mapping을 메모리 안에서만 유지하고 로그에는 남기지 않을 수 있습니다.

## 데이터셋 구성

생성기 버전은 `1.0.0`, seed는 `42`입니다.

| Split | 레코드 | 한국어 | 영어 | SHA-256 |
|---|---:|---:|---:|---|
| Train | 1,600 | 1,280 | 320 | `b98429fef0b103f24e8eaded069cbd2f6def5fbf8c083a5c7baf366c9fc1d21a` |
| Validation | 200 | 160 | 40 | `25ca38198d38e04be181e15b4e21a3c96d672f46f775ae1bc6c422ee4514f820` |
| Test | 400 | 320 | 80 | `6f6ef9a6b42297738b292d5149f2e6e323f7bcd6f2325b6bfbc04ae6d9d0ec21` |
| **합계** | **2,200** | **1,760 (80%)** | **440 (20%)** | split별 고정 |

동일 실험을 재현하려면 레코드 수뿐 아니라 세 split 해시가 모두 일치해야 합니다.

## 9개 엔터티 유형

| 유형 | 의미 | 합성 패턴 예 |
|---|---|---|
| `PERSON` | 사람 이름 | `김가상`, `Taylor Sample` |
| `RRN` | 주민등록번호 형태의 무효 체크섬 값 | 실제 값은 문서에 게시하지 않음 |
| `DOB` | 생년월일 | 합성 날짜 |
| `REL` | 가족·신청인 관계 | `보호자`, `guardian` |
| `ADDRESS` | 주소 | 가상 도시와 예시 주소 |
| `PHONE` | 전화번호 | 예약·가상 번호 대역 |
| `EMAIL` | 이메일 | `synthetic.*@example.com` |
| `ACCOUNT` | 계좌번호 형태 | 합성 숫자, 실제 계좌 아님 |
| `CARD` | 카드번호 형태 | Luhn 검사를 의도적으로 통과하지 않음 |

빈 PII 문서도 포함해 모델이 항상 무언가를 출력하는 과잉 추출을 측정합니다. 한국어 데이터에는 OCR 공백, 구분자 변형, NFD 문자열도 포함됩니다.

## 결정론적 치환 파이프라인

`src/pii_tokens.py`의 순서는 다음과 같습니다.

1. source text와 모델 출력을 NFC로 정규화합니다.
2. `<think>...</think>` 블록을 제거하고 tab이 있는 행만 읽습니다.
3. 유형을 whitelist와 대조하고 빈 값·중복을 제거합니다.
4. 값 또는 허용 변형이 source text 안에 실제로 존재하는지 확인합니다.
5. 원문에서 처음 나타난 위치, 긴 문자열 우선 순서로 엔터티를 정렬합니다.
6. 유형별 counter를 사용해 `[PERSON_1]`, `[EMAIL_1]` 같은 토큰을 만듭니다.
7. 원본 표기와 제한된 변형을 하나의 정규식으로 합쳐 한 번에 치환합니다.
8. mapping으로 다시 조립했을 때 NFC 원문과 동일한지 round-trip을 검사합니다.

예를 들면 다음과 같습니다.

```text
입력:  성명 김가상 / 이메일 synthetic.ko.408@example.com
출력:  성명 [PERSON_1] / 이메일 [EMAIL_1]
```

`PERSON`의 공백·tab 변형, `RRN`·전화·카드·계좌·날짜의 제한된 구분자 변형만 허용합니다. 임의의 fuzzy matching은 오탐과 과잉 치환을 키우므로 사용하지 않습니다.

## 평가 지표

| 지표 | 정의 | 실패가 의미하는 것 |
|---|---|---|
| entity precision / recall / F1 | `(TYPE, NFC ORIGINAL)` 집합의 TP/FP/FN | 누락 또는 잘못된 추출 |
| document leakage rate | 치환 후 정답 원문이 하나라도 남은 문서 비율 | 마스킹 실패 |
| entity leakage rate | 남아 있는 정답 엔터티 비율 | 부분 누출 |
| over-redaction rate | 정답에 없는 엔터티를 치환한 비율 | 과잉 마스킹 |
| hallucination rate | TSV처럼 보이지만 source에 없는 행 비율 | 모델 환각 |
| parse success rate | 출력 계약을 파싱할 수 있는 문서 비율 | 형식 불안정 |
| deterministic rate | 엔터티 순서를 뒤집어도 같은 결과가 나오는 비율 | 순서 의존 버그 |
| round-trip rate | mapping으로 복원한 결과가 원문과 같은 비율 | 손실 치환 |

이 지표 코드는 로컬 테스트를 통과했지만, GPU 학습이 미실행이므로 fine-tuned 모델의 측정값은 아직 없습니다.

## 학습 레코드 형태

각 JSONL 레코드는 `source_text`, source-order `entities`, `target_tsv`를 가집니다. 학습 시에는 system/user prompt와 assistant completion으로 변환하고, completion에만 loss를 적용합니다.

```text
System: 허용 유형만 TYPE<TAB>ORIGINAL 형식으로 추출
User:   합성 문서
Assistant:
PERSON	김가상
EMAIL	synthetic.ko.408@example.com
```

raw source와 completion은 런타임 입력이며 MLflow parameter/tag로 기록하지 않습니다.

이전: [Part 1 — 플랫폼 아키텍처](01-platform-architecture.md)

다음: [Part 3 — SageMaker AI와 MLflow 실행](03-sagemaker-mlflow-execution.md)
