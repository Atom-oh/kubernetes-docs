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

재시도 한도와 Job deadline 설정입니다. 컨트롤러·노드 장애 중 모든 자원이 정확히 3시간 안에 회수되거나 전체 비용이 제한된다는 보장은 아닙니다.
</details>

4. `verify_cleanup.sh`가 1을 반환해야 하는 경우는 무엇인가요?
   - A) 잔존 자원이 0개
   - B) 잔존 자원이 있거나 권한 오류 등으로 상태를 확인할 수 없음
   - C) smoke run 성공
   - D) dataset hash 일치

<details>
<summary>정답 보기</summary>

**정답: B**

잔존 0개만으로 충분하지 않습니다. 조회 오류를 미확인으로 남기고, 소유권 없는 과거 inventory를 이름만으로 자동 삭제하지 않습니다.
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

6. 2026년 9월 12일 현재 GPU 실행이 차단되는 이유는 무엇인가요?
   - A) PyTorch 2.8 DLC의 패치 지원이 8월 6일 종료됨
   - B) 소스 번들 생성이 유료임
   - C) 모든 MLflow App이 삭제됨
   - D) 로컬 단위 테스트가 GPU를 요구함

<details>
<summary>정답 보기</summary>

**정답: A**

지원되는 DLC·torch·의존성 조합과 GPU smoke 검증이 필요합니다. 날짜 검사만 제거하는 것은 갱신이 아닙니다.
</details>

7. `--execute` 없이 SageMaker launcher를 호출하면 무엇을 하나요?
   - A) 즉시 full Job 제출
   - B) 요청 JSON만 작성
   - C) 기존 Job 삭제
   - D) 비용 추정치 보장

<details>
<summary>정답 보기</summary>

**정답: B**

기본값은 요청 미리보기입니다. 실제 제출 전에는 실행 지원 검사와 별도 검토가 필요합니다.
</details>

8. EKS MLflow의 metric·parameter JSON만 저장하면 충분한가요?
   - A) 어댑터가 자동 포함되므로 충분함
   - B) 최종 어댑터·집계 artifact를 내려받고 해시까지 확인해야 함
   - C) `emptyDir`가 클러스터 삭제 후에도 보존함
   - D) 로그 tail이 모델을 복원함

<details>
<summary>정답 보기</summary>

**정답: B**

실제 파일 보존과 metadata export는 다릅니다. export 실패 시 남긴 클러스터도 비용과 후속 정리를 확인해야 합니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
