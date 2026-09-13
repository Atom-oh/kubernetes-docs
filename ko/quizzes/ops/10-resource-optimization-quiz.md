# 리소스 최적화 퀴즈

> **관련 문서**: [리소스 최적화](../../ops/10-resource-optimization.md)

## 1. 메모리 압박 시 Pod 퇴거 순서를 올바르게 설명한 것은?

- A) QoS 클래스만으로 순서가 결정된다
- B) request 초과 여부, Pod Priority와 request 대비 사용량 등을 고려한다
- C) Guaranteed는 절대 퇴거되지 않는다
- D) PDB가 모든 node-pressure eviction을 막는다

<details>
<summary>정답 보기</summary>

**정답: B**

QoS는 유용한 분류지만 절대적인 퇴거 순서가 아닙니다. 컨테이너 limit OOM, 메모리 압박 퇴거와 DiskPressure도 구별합니다.

</details>

## 2. CPU throttled-period 비율은 무엇을 뜻하나요?

- A) 사용하지 못한 CPU 시간의 정확한 비율
- B) 스로틀링이 있었던 quota period의 비율
- C) CPU request 사용률
- D) 평균 메모리 사용률

<details>
<summary>정답 보기</summary>

**정답: B**

여러 스레드가 quota를 함께 소모할 수 있습니다. period 비율만으로 손실 시간이나 limit 증가 필요성을 확정하지 않습니다.

</details>

## 3. JVM의 최대 힙과 컨테이너 메모리에 대한 올바른 설명은?

- A) 항상 75%가 최적이다
- B) 힙 밖 메모리와 전체 RSS를 측정해 비율을 정한다
- C) MaxRAMPercentage가 Pod limit 변경을 항상 즉시 반영한다
- D) 힙 dump가 커널 SIGKILL에도 보장된다

<details>
<summary>정답 보기</summary>

**정답: B**

metaspace, stack, direct buffer, JNI 등의 공간이 필요합니다. JVM ergonomics 입력과 cgroup 한도, Java OOME와 SIGKILL을 구별합니다.

</details>

## 4. JAVA_OPTS를 설정했는데 JVM 옵션이 적용되지 않을 수 있는 이유는?

- A) JVM이 반드시 무시해야 하는 보안 옵션이라서
- B) entrypoint가 전달하지 않으면 JVM이 자동으로 읽지 않아서
- C) Kubernetes는 환경 변수를 지원하지 않아서
- D) Java 21은 컨테이너를 지원하지 않아서

<details>
<summary>정답 보기</summary>

**정답: B**

JAVA_TOOL_OPTIONS와 명시적 java 명령, 실제 VM.flags 출력으로 적용을 확인할 수 있습니다.

</details>

## 5. VPA upperBound에 대한 올바른 설명은?

- A) 항상 컨테이너 memory limit으로 복사해야 한다
- B) request 추천 범위의 일부이며 limit과 동일한 개념이 아니다
- C) HPA 최대 복제본 수이다
- D) OOM이 절대로 발생하지 않는 메모리 크기다

<details>
<summary>정답 보기</summary>

**정답: B**

target/lowerBound/upperBound/uncappedTarget의 의미를 구별합니다. Initial 모드도 새 request를 통해 HPA 분모에 영향을 줄 수 있습니다.

</details>

## 6. Go 1.25+의 기본 GOMAXPROCS에 대한 설명으로 맞는 것은?

- A) 항상 호스트 CPU만 사용하므로 외부 라이브러리가 필수다
- B) 언어 버전/호환성 조건에 따라 cgroup quota·affinity 등을 고려하며 수동 설정은 자동 갱신을 끈다
- C) CPU request만으로 계산한다
- D) 500m이면 모든 환경에서 반드시 1이다

<details>
<summary>정답 보기</summary>

**정답: B**

Go 1.27.1 런타임과 go.mod 1.25 이상 예제를 검증했습니다. quota 올림과 최소값 조건을 단순 공식으로 축약하지 않습니다.

</details>

## 7. GOMEMLIMIT과 Node old-space limit의 공통적인 한계는?

- A) 전체 프로세스 RSS를 완전히 제한하지 않는다
- B) 모든 native 메모리를 강제로 해제한다
- C) 컨테이너 OOM을 보장해서 막는다
- D) Pod request를 자동 변경한다

<details>
<summary>정답 보기</summary>

**정답: A**

Go의 값은 runtime 관리 메모리 soft limit이고 Node 옵션은 V8 old space입니다. native 할당과 여러 worker의 총량을 따로 계산합니다.

</details>

## 8. Gunicorn/Tokio worker 수를 정할 때 올바른 접근은?

- A) 호스트 CPU 수에 고정 배수를 적용하면 충분하다
- B) 유효한 설정이 실제 적용되는지 확인하고 quota·메모리·워크로드로 시험한다
- C) Rust에는 GC가 없으므로 동시성 제한이 필요 없다
- D) thread와 process 수는 메모리에 영향을 주지 않는다

<details>
<summary>정답 보기</summary>

**정답: B**

WEB_CONCURRENCY를 코드가 읽어야 적용됩니다. Tokio의 명시적 worker_threads 설정은 환경 변수보다 우선하고 blocking pool은 별도입니다.

</details>

## 9. OOM reason과 Pending phase 메트릭을 올바르게 사용하는 방법은?

- A) reason gauge에 increase를 적용해 정확한 OOM 횟수를 센다
- B) Pending 시계열 개수를 count하면 현재 Pending 수가 된다
- C) 0/1 gauge의 값을 평가하며 reason은 마지막 상태라는 한계를 유지한다
- D) Pending은 항상 CPU 부족이다

<details>
<summary>정답 보기</summary>

**정답: C**

0인 Pending 시계열도 존재합니다. 최근 restart와 마지막 OOM reason을 결합해도 기간 내 모든 OOM 횟수를 복원하지는 못합니다.

</details>

## 10. Auto Mode bin-packing과 placeholder Pod에 대한 올바른 설명은?

- A) 4 vCPU 인스턴스에는 애플리케이션 request 4 CPU가 항상 들어간다
- B) placeholder는 EC2 Capacity Reservation과 같다
- C) allocatable·overhead·배치 제약을 고려하며 placeholder는 용량 보장이 아니다
- D) preemptionPolicy Never는 자신이 선점되는 것을 막는다

<details>
<summary>정답 보기</summary>

**정답: C**

Never는 이 Pod가 다른 Pod를 선점하지 않도록 합니다. NodePool은 karpenter.sh/v1이며 Auto Mode NodeClass group은 eks.amazonaws.com입니다.

</details>
