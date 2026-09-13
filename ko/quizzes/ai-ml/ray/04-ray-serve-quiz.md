# Ray Serve 퀴즈

## 객관식 문제

1. Serve Deployment와 Kubernetes Deployment의 관계는?
   - A) 같은 객체이다
   - B) Serve deployment는 actor replica의 논리 단위이며 Pod와 일대일이 아니다
   - C) Serve replica마다 EC2 하나가 필수
   - D) Serve는 actor를 쓰지 않는다

<details>
<summary>정답 보기</summary>

**정답: B**

한 Ray Pod 안에 여러 replica actor가 배치될 수 있습니다.
</details>

2. 2.58.0의 기본 proxy 위치는?
   - A) 항상 head에만 하나
   - B) replica가 있는 node의 EveryNode
   - C) 항상 모든 EC2 node
   - D) 항상 Disabled

<details>
<summary>정답 보기</summary>

**정답: B**

HeadOnly/Disabled는 명시적 선택이며 오래된 architecture 설명과 현재 API를 구분합니다.
</details>

3. 기본 deployment와 num_replicas="auto"는 어떻게 다른가요?
   - A) 둘 다 무조건 100 replica로 시작
   - B) 기본은 고정 1, auto는 min 1/max 100/target 2 설정을 적용
   - C) 기본은 GPU 1, auto는 GPU 100
   - D) 둘 다 autoscaling 불가

<details>
<summary>정답 보기</summary>

**정답: B**

직접 AutoscalingConfig()를 만들면 max 기본값은1이므로 별도로 지정해야 합니다.
</details>

4. max_queued_requests의 범위는?
   - A) 클러스터 전체 대기열 하나
   - B) 각 caller(proxy/handle)의 대기열
   - C) GPU KV cache 용량
   - D) RayCluster의 Pod 수

<details>
<summary>정답 보기</summary>

**정답: B**

기본 -1은 무제한이며 limit 초과 시 HTTP 거부나 handle BackPressureError가 발생할 수 있습니다.
</details>

5. 새 replica actor가 Pending이면 언제나 새 Pod와 EC2가 생기나요?
   - A) 항상 1:1로 생긴다
   - B) 아니다. 기존 용량·group 한도·placement·autoscaler 활성화에 따라 달라진다
   - C) 자동으로 CPU 모델로 바뀐다
   - D) Ray Serve가 직접 EC2를 만든다

<details>
<summary>정답 보기</summary>

**정답: B**

Actor 배치, Pod 규모, node 공급을 별도로 확인합니다.
</details>

6. 확인한 2.58.0 LLM backend 설명은?
   - A) vLLM만 존재
   - B) vLLM과 SGLang backend가 있으며 의존성/설정 호환성은 각각 확인
   - C) 모든 engine kwargs가 모든 엔진에서 동일
   - D) ray[serve]가 모든 LLM 가중치를 포함

<details>
<summary>정답 보기</summary>

**정답: B**

ray[llm] 추론 의존성과 모델 권한/download는 별도이며 CPU 검사로 LLM을 검증하지 않았습니다.
</details>

7. RayService 업데이트에 대한 정확한 설명은?
   - A) 모든 EKS 운영 배포에서 필수이며 무중단 보장
   - B) 선택적인 수명주기 관리 경로이며 strategy/Gateway/용량/readiness/draining을 검증
   - C) 항상 기존 Pod 이미지만 수정
   - D) 긴 streaming 요청은 언제나 보존

<details>
<summary>정답 보기</summary>

**정답: B**

Application 변경과 cluster 전환, actor 재설정을 구분합니다.
</details>

8. 로컬 Echo 예제로 확인한 것은?
   - A) GPU 성능
   - B) LLM 품질
   - C) HTTP 200 응답과 DeploymentHandle 호출
   - D) 다중 node autoscaling

<details>
<summary>정답 보기</summary>

**정답: C**

작은 단일 node CPU 검사이며 모델/LLM/GPU/cloud를 실행하지 않았습니다.
</details>

## 서술형 문제

9. max ongoing, autoscaling target, caller queue limit을 구분해야 하는 이유는?

<details>
<summary>정답 보기</summary>

Replica에 전달된 요청 상한, autoscaling 목표 부하, 각 caller에 대기할 요청 한도는 서로 다른 제어입니다. 하나를 설정했다고 나머지 상한과 latency가 보장되지 않습니다.
</details>

10. Token auth나 ClusterIP만으로 application 보안이 완료되지 않는 이유는?

<details>
<summary>정답 보기</summary>

TLS, 각 진입점의 인증/인가, model artifact 권한, 민감 요청/log 처리와 resource/queue/timeout 정책은 별도로 확인해야 합니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/04-ray-serve.md)
