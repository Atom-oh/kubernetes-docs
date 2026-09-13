# Ray Train / Tune 퀴즈

## 객관식 문제

1. Ray Train이 자동 작성하지 않는 것은?
   - A) worker 기반 조율
   - B) framework process group 준비
   - C) 모델·데이터 분할·상태 저장/복구 로직 전체
   - D) Ray 자원 요청

<details>
<summary>정답 보기</summary>

**정답: C**

prepare_model/data_loader와 실제 모델·optimizer·checkpoint 로직은 사용자가 준비합니다.
</details>

2. 검토한 2.58.0의 Train V2 기본값은?
   - A) 환경 변수가 없으면 V2가 기본
   - B) 항상 V1만 실행
   - C) TorchTrainer import가 없어졌다
   - D) PyTorch도 Ray extra에 자동 포함

<details>
<summary>정답 보기</summary>

**정답: A**

환경 변수로 이전 구현을 선택한 실행과 구분합니다. Framework 자체는 별도 의존성입니다.
</details>

3. V2에서 legacy trainer_resources를 지정하면?
   - A) 항상 추가 controller CPU를 예약
   - B) deprecation 오류가 발생
   - C) GPU 수를 늘림
   - D) Tune trial 수를 변경

<details>
<summary>정답 보기</summary>

**정답: B**

Controller·worker·Tune driver 자원은 서로 다른 범위입니다.
</details>

4. Checkpoint.from_directory는 무엇을 하나요?
   - A) 모든 모델/optimizer/RNG 상태를 자동 수집
   - B) 사용자가 준비한 디렉터리의 파일을 checkpoint로 참조
   - C) 자동으로 모델 배포
   - D) dataset을 자동 익명화

<details>
<summary>정답 보기</summary>

**정답: B**

복구에 필요한 payload를 직접 저장하고 get_checkpoint 결과를 읽어 복원합니다.
</details>

5. 2.58.0 V2 report의 worker 호출 규칙은?
   - A) rank 0만 호출하고 나머지는 생략
   - B) 모든 worker가 같은 횟수로 도달하는 barrier
   - C) 항상 모든 metric의 평균을 계산
   - D) checkpoint가 없으면 호출 불가

<details>
<summary>정답 보기</summary>

**정답: B**

Rank 0만 checkpoint를 저장하더라도 다른 worker도 checkpoint=None으로 참여합니다.
</details>

6. max_failures=0이면 모든 재시도가 꺼지나요?
   - A) 그렇다
   - B) 아니다. controller/preemption retry는 별도 설정이다
   - C) 무조건 무한 재시도다
   - D) Karpenter retry만 꺼진다

<details>
<summary>정답 보기</summary>

**정답: B**

검토한 controller_failure_limit와 max_preemption_failures 기본값은 각각 -1입니다.
</details>

7. 현재 V2 Train/Tune 연동 패턴은?
   - A) V2 Trainer instance를 Tuner에 그대로 전달
   - B) 함수 trainable 안에서 Trainer를 구성하고 fit; 필요한 callback을 연결
   - C) 서로 함께 사용 불가능
   - D) 항상 별도 Kubernetes cluster 필요

<details>
<summary>정답 보기</summary>

**정답: B**

직접 V2 Trainer 전달은 native 검사에서 TuneError였으며 연결 코드와 자원 계획이 필요합니다.
</details>

8. TuneReportCallback이 하는 일은?
   - A) worker metric 평균을 자동 계산
   - B) checkpoint를 다시 업로드
   - C) 첫 worker metric과 기존 checkpoint 경로를 Tune에 전달
   - D) Tune session 밖에서 항상 사용 가능

<details>
<summary>정답 보기</summary>

**정답: C**

Callback은 Tune session 안에서 만들며 metric aggregation은 별도로 수행합니다.
</details>

## 서술형 문제

9. Trial driver와 Train worker 자원을 함께 봐야 하는 이유는?

<details>
<summary>정답 보기</summary>

모든 driver가 CPU를 점유하면 내부 worker/placement group이 자원을 확보하지 못할 수 있습니다. 동시 trial 수와 전체 worker bundle, cluster 한도 및 각 노드 배치 가능성을 함께 확인합니다.
</details>

10. 작은 scalar Tune 예제 성공으로 무엇을 주장할 수 없나요?

<details>
<summary>정답 보기</summary>

실제 모델 정확도, PyTorch/DDP·GPU 성능, 다중 노드 checkpoint 복구, EKS autoscaling 성공을 주장할 수 없습니다. 확인한 것은 API와 두 scalar trial 결과 수집입니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/03-ray-train-tune.md)
