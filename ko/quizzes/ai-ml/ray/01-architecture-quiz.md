# Ray 아키텍처 퀴즈

## 객관식 문제

1. 원격 함수를 어떻게 제출하나요?
   - A) f(...)를 일반 함수처럼 호출
   - B) @ray.remote 함수에 f.remote(...) 사용
   - C) ray.get(f)만 호출
   - D) Pod를 직접 생성해야 함

<details>
<summary>정답 보기</summary>

**정답: B**

단일 반환 예제는 ObjectRef를 반환하며 ray.get으로 값을 읽습니다.
</details>

2. Ray task는 모두 독립적이며 부작용이 없나요?
   - A) 그렇다. dependency를 추적하지 않는다
   - B) 아니다. ObjectRef dependency와 외부 부작용·재시도를 고려한다
   - C) 오직 actor만 ObjectRef를 반환한다
   - D) 모든 함수는 정확히 한 번만 실행된다

<details>
<summary>정답 보기</summary>

**정답: B**

Stateless 실행 단위라는 설명은 순수 함수나 exactly-once 보장이 아닙니다.
</details>

3. Actor 상태에 대한 정확한 설명은?
   - A) 인스턴스 메모리를 호출 사이에 유지하지만 장애 후 복구는 별도다
   - B) 자동으로 모든 상태를 영구 저장한다
   - C) head에서만 실행한다
   - D) restart만 켜면 이전 메모리가 복구된다

<details>
<summary>정답 보기</summary>

**정답: A**

max_restarts는 constructor를 다시 실행하며 checkpoint 복구를 대신하지 않습니다.
</details>

4. 확인한 zero-copy 범위는?
   - A) 모든 Python 객체와 GPU 메모리
   - B) 모든 노드가 같은 물리 RAM 공유
   - C) 같은 노드의 NumPy 배열을 읽기 전용 공유 view로 접근
   - D) 네트워크 전송 비용이 항상 0

<details>
<summary>정답 보기</summary>

**정답: C**

수정에는 복사가 필요하며 다른 객체·GPU·노드 간 전달까지 일반화하지 않습니다.
</details>

5. GCS의 현재 이름과 역할은?
   - A) Global Control Service; actor/node/placement group 등의 cluster metadata
   - B) GPU Copy Store; 모든 가중치 공유
   - C) Global Control Store; 모든 ObjectRef metadata의 유일한 owner
   - D) Kubernetes API server 대체

<details>
<summary>정답 보기</summary>

**정답: A**

객체 ownership metadata는 원래 ObjectRef를 만든 process가 관리하며 GCS와 구분합니다.
</details>

6. CPU 1개씩 남은 두 노드로 CPU 2개 단일 task를 실행할 수 있나요?
   - A) 합이 2이므로 항상 가능
   - B) 자동으로 task를 반으로 나눈다
   - C) 아니다. 단일 task는 한 feasible node에 들어가야 한다
   - D) 메모리만 충분하면 CPU는 무관하다

<details>
<summary>정답 보기</summary>

**정답: C**

Cluster 후보 선택과 노드별 resource feasibility를 함께 봅니다.
</details>

7. num_cpus=1의 의미는?
   - A) 운영체제가 모든 thread를 한 core로 강제 제한
   - B) Ray의 논리 scheduling/admission 요구이며 OS 제한과 다름
   - C) 항상 물리 core 한 개 전용 배정
   - D) GPU memory도 자동 제한

<details>
<summary>정답 보기</summary>

**정답: B**

Container limits와 library thread 설정은 별도입니다.
</details>

8. KubeRay가 하는 일은?
   - A) 애플리케이션 대신 Train/Tune/Serve를 자동 선택
   - B) Ray CR과 Pod 등의 수명주기를 Kubernetes에서 조정
   - C) 기본 kube-scheduler를 교체
   - D) 모든 Ray task마다 EC2를 새로 생성

<details>
<summary>정답 보기</summary>

**정답: B**

Ray작업·Pod배치·EC2공급은 서로 다른 계층입니다.
</details>

## 단답형 문제

9. 여러 요청에 걸쳐 모델을 메모리에 유지하려면 왜 actor가 적합한가요?

<details>
<summary>정답 보기</summary>

명시적인 원격 인스턴스가 상태를 소유하기 때문입니다. Task worker의 우연한 global cache 재사용을 correctness에 의존하지 않습니다. Actor 장애 후에는 checkpoint·복구가 별도로 필요합니다.
</details>

10. GCS 복구와 object/actor 애플리케이션 복구를 구분해야 하는 이유는?

<details>
<summary>정답 보기</summary>

GCS의 cluster metadata 내구성, object owner/lineage/value 복구, actor checkpoint는 다른 문제입니다. Redis 또는 alpha RocksDB 설정만으로 모든 데이터와 애플리케이션 상태가 복구되는 것은 아닙니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/01-architecture.md)
