# KubeRay 오퍼레이터 퀴즈

## 객관식 문제

1. KubeRay operator 설치만으로 무엇이 시작되나요?
   - A) 모든 Ray workload가 자동 시작
   - B) CR을 조정할 controller가 준비되며 workload CR은 별도로 필요
   - C) 모든 GPU node가 생성
   - D) 모든 worker가 Deployment로 생성

<details>
<summary>정답 보기</summary>

**정답: B**

Operator 설치와 RayCluster/RayJob/RayService 생성은 별개입니다.
</details>

2. 1.7.0 chart의 CRD와 RayCronJob 상태는?
   - A) CRD는 세 개뿐이다
   - B) RayCronJob CRD가 있으면 scheduling도 항상 활성
   - C) 네 CRD가 있고 RayCronJob feature gate는 기본 비활성
   - D) v1 API는 없다

<details>
<summary>정답 보기</summary>

**정답: C**

RayCluster/RayJob/RayService/RayCronJob을 구분합니다.
</details>

3. RayJob의 기본 정리 동작은?
   - A) shutdownAfterJobFinishes 생략 시 자동 정리 활성
   - B) TTL 0이면 모든 EC2/PVC 삭제
   - C) shutdownAfterJobFinishes는 기본 false이며 정리·결과 보존을 따로 설정
   - D) 외부 cluster도 항상 삭제

<details>
<summary>정답 보기</summary>

**정답: C**

TTL·deletionStrategy와 공유/생성 cluster 소유권을 확인합니다.
</details>

4. RayService incremental upgrade에 필요한 것은?
   - A) Feature gate 하나만 있으면 무중단 보장
   - B) 적절한 strategy, Gateway API/구현, 용량·readiness·draining 조건
   - C) 기존 Pod 한 개의 image만 수정
   - D) RayJob이 필수

<details>
<summary>정답 보기</summary>

**정답: B**

새 cluster 사이의 점진적 traffic 전환이며 단순 in-place rolling과 다릅니다.
</details>

5. Ray 작업 증가부터 EC2 공급까지의 계층은?
   - A) Ray autoscaler가 곧바로 모든 EC2를 생성
   - B) Ray 규모 요청 → KubeRay Pod 조정 → Kubernetes 배치/용량 공급
   - C) Karpenter가 Ray actor를 직접 호출
   - D) 두 controller가 동일한 resource를 동시에 소유

<details>
<summary>정답 보기</summary>

**정답: B**

Pending 원인이 image/PVC/권한인 경우 node 증설만으로 해결되지 않습니다.
</details>

6. idleTimeoutSeconds 60을 어떻게 해석하나요?
   - A) 언제나 정확히 60초 후 모든 worker 삭제
   - B) 검토한 global 기본값이며 group override·min/max·활동·drain 조건을 함께 봄
   - C) RayJob 전체 TTL
   - D) Karpenter의 고정 생성 시간

<details>
<summary>정답 보기</summary>

**정답: B**

설정값과 실제 삭제 완료 시간은 다릅니다.
</details>

7. GPU 자원 선언의 우선순위는?
   - A) Pod limit만 사용하고 모든 override를 무시
   - B) structured group resources와 rayStartParams가 limit보다 우선할 수 있음
   - C) 항상 GPU 1개
   - D) GPU 개수가 논리 설정대로 물리적으로 증가

<details>
<summary>정답 보기</summary>

**정답: B**

실제 device plugin/driver/가시 GPU와 Ray 논리 자원을 일치시켜야 합니다.
</details>

8. Helm chart를 upgrade하면 기존 CRD schema도 자동 갱신되나요?
   - A) 항상 갱신·삭제된다
   - B) 아니다. 저장된 CR 호환성과 별도 CRD 갱신 절차를 확인한다
   - C) CRD가 일반 Pod라서 불필요
   - D) CRD를 먼저 무조건 삭제하면 안전

<details>
<summary>정답 보기</summary>

**정답: B**

Helm crds/ 방식의 수명주기 한계와 CRD 삭제의 영향을 확인합니다.
</details>

## 서술형 문제

9. worker replica 수와 Ray Pod 수가 항상 같지 않은 이유는?

<details>
<summary>정답 보기</summary>

numOfHosts를 사용하는 group은 replica 하나가 여러 host/Pod에 대응할 수 있습니다. 실제 spec과 생성된 Pod를 대조해야 합니다.
</details>

10. Ray token authentication을 켠 것만으로 보안 설정이 완료되지 않는 이유는?

<details>
<summary>정답 보기</summary>

TLS와 별개이며 모든 application endpoint의 인증·인가를 대신하지 않습니다. 진입점 제한, secret 전달, 버전별 지원 범위와 조직 정책을 함께 확인해야 합니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/ray/02-kuberay-operator.md)
