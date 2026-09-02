# SageMaker AI와 MLflow 실행 퀴즈

## 객관식 문제

1. 새 관리형 MLflow 배포에 사용하는 리소스는 무엇인가요?
   - A) legacy Tracking Server만 사용
   - B) SageMaker MLflow App
   - C) public EKS LoadBalancer
   - D) 로컬 SQLite 파일만 사용

<details>
<summary>정답 보기</summary>

**정답: B**

새 관리형 경로는 SageMaker MLflow App API를 사용합니다.
</details>

2. full run 전에 반드시 필요한 것은 무엇인가요?
   - A) smoke run과 raw PII logging 검사 통과
   - B) project membership 제거
   - C) 최대 step 즉시 실행
   - D) teardown 비활성화

<details>
<summary>정답 보기</summary>

**정답: A**

smoke 완료, 로그 안전성, 집계 결과와 adapter inventory를 먼저 확인합니다.
</details>

3. EKS Job의 실패·시간 제한 계약은 무엇인가요?
   - A) 무제한 retry와 deadline 없음
   - B) `backoffLimit: 0`, `activeDeadlineSeconds: 10800`
   - C) 10회 retry와 1시간
   - D) Deployment로 영구 실행

<details>
<summary>정답 보기</summary>

**정답: B**

실패를 숨기지 않고 최대 3시간 안에 종료하도록 설계했습니다.
</details>

4. `verify_cleanup.sh`가 1을 반환해야 하는 경우는 무엇인가요?
   - A) 잔존 자원이 0개
   - B) App, project, bucket, role, cluster 중 하나라도 남음
   - C) smoke run 성공
   - D) dataset hash 일치

<details>
<summary>정답 보기</summary>

**정답: B**

정리 검증은 잔존 자원이 하나라도 있으면 실패해야 합니다.
</details>

5. 기록된 9월 1일 검증에서 실행된 것은 무엇인가요?
   - A) SageMaker full Training Job
   - B) EKS full GPU Job
   - C) provisioning과 정리 경로
   - D) tuned model evaluation

<details>
<summary>정답 보기</summary>

**정답: C**

두 GPU 학습 Job은 제출 전에 중단됐습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
