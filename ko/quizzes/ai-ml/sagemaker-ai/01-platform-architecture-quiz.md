# SageMaker Qwen 플랫폼 아키텍처 퀴즈

이 퀴즈는 목표 아키텍처의 책임 경계와 SageMaker AI/EKS 실행 경로의 차이를 확인합니다.

## 객관식 문제

1. Qwen 모델이 직접 담당하는 출력은 무엇인가요?
   - A) 최종 마스킹 문서
   - B) `TYPE<TAB>ORIGINAL` 엔터티 행
   - C) Unified Studio project
   - D) S3 삭제 보고서

<details>
<summary>정답 보기</summary>

**정답: B**

모델은 엔터티를 추출하고, 결정론적 Python 코드가 검증·정렬·토큰 치환을 수행합니다.
</details>

2. Part 1 다이어그램의 올바른 해석은 무엇인가요?
   - A) SageMaker와 EKS 학습이 모두 완료됐다는 증거
   - B) 재실행을 위한 목표 설계
   - C) GPU 비용 비교 결과
   - D) 프로덕션 배포 승인

<details>
<summary>정답 보기</summary>

**정답: B**

다이어그램은 목표 설계이며, 두 GPU 학습 경로는 실제로 실행되지 않았습니다.
</details>

3. 두 실행 경로의 결과를 비교 가능하게 만드는 조건은 무엇인가요?
   - A) 서로 다른 데이터 split 사용
   - B) 모델 ID, seed, split hash, dependency와 QLoRA 설정 고정
   - C) EKS에서만 MLflow 사용
   - D) full run부터 시작

<details>
<summary>정답 보기</summary>

**정답: B**

실행 환경만 바꾸고 실험 계약을 고정해야 환경 간 비교가 의미를 가집니다.
</details>

4. SageMaker MLflow App에 기록하면 안 되는 값은 무엇인가요?
   - A) 데이터셋 SHA-256
   - B) LoRA rank
   - C) raw source와 token mapping
   - D) dependency 버전

<details>
<summary>정답 보기</summary>

**정답: C**

MLflow에는 집계값과 비민감 설정만 기록합니다.
</details>

5. 왜 project governance를 GPU 학습보다 먼저 확인하나요?
   - A) 모델 다운로드 속도를 높이기 위해
   - B) membership 없는 project가 남으면 자동화가 조회·삭제하지 못할 수 있기 때문에
   - C) QLoRA가 project profile을 요구하기 때문에
   - D) EKS가 DataZone 안에서만 동작하기 때문에

<details>
<summary>정답 보기</summary>

**정답: B**

owner membership을 생성 시점에 보장해야 부분 생성 후 고아 project가 남는 것을 막을 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/01-platform-architecture.md)
