# SageMaker Qwen 실제 검증 결과 퀴즈

## 객관식 문제

1. 2026년 9월 2일 재확인 결과는 무엇인가요?
   - A) 모든 자원 0
   - B) Unified Studio project 1개 `ACTIVE`
   - C) EKS GPU cluster 1개 실행 중
   - D) Training Job 완료

<details>
<summary>정답 보기</summary>

**정답: B**

당시 기록에서는 App·S3·IAM이 정리되고 project 하나가 남았습니다. 9월 12일 문서 검토로 현재 AWS 상태까지 재확인한 것은 아닙니다.
</details>

2. 세 번째 provisioning 시도의 핵심 실패는 무엇인가요?
   - A) 모델 ID 오타
   - B) project membership 누락
   - C) 데이터 해시 불일치
   - D) CUDA OOM

<details>
<summary>정답 보기</summary>

**정답: B**

호출 role group profile이 project owner/member로 지정되지 않았습니다.
</details>

3. 게시하지 않은 결과는 무엇인가요?
   - A) 레코드 수
   - B) MLflow App 버전
   - C) fine-tuned F1과 GPU 비용
   - D) Python 테스트 수

<details>
<summary>정답 보기</summary>

**정답: C**

GPU 학습이 미실행이므로 해당 비교값은 측정되지 않았습니다. MLflow App·S3 등을 포함한 전체 실험 비용이 0원이라는 뜻은 아닙니다.
</details>

4. 재실행의 첫 번째 게이트는 무엇인가요?
   - A) full Job 제출
   - B) inventory와 실제 자원을 대조해 실험 소유 자원의 잔존·미확인 상태 해결
   - C) EKS cluster 생성
   - D) tuned metric 게시

<details>
<summary>정답 보기</summary>

**정답: B**

권한 오류나 목록에서 보이지 않는 상태를 삭제 완료로 처리하지 않습니다. 같은 prefix를 쓰는 다른 사람의 자원도 삭제하면 안 됩니다.
</details>

5. 목표 아키텍처와 실제 워크플로의 차이는 무엇인가요?
   - A) 둘 다 완료 증거
   - B) 목표 아키텍처는 재실행 설계, 워크플로는 실제 중단 흔적
   - C) 둘 다 비용 보고서
   - D) 실제 워크플로는 GPU 학습 완료를 표시

<details>
<summary>정답 보기</summary>

**정답: B**

실제 워크플로는 GPU 학습 전에 중단된 과거 기록입니다. 현재 계정 상태나 전체 비용 0원을 증명하지 않습니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/04-validation-results.md)
