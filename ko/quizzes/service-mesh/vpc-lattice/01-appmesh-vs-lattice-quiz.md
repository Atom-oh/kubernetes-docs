# App Mesh와 VPC Lattice 아키텍처 대비 퀴즈

이 퀴즈는 sidecar 모델과 관리형 데이터플레인 모델의 구조적 차이, 리소스 매핑, 기능 GAP에 대한 이해도를 테스트합니다.

## 객관식 문제

1. VPC Lattice에서 circuit breaker와 outlier detection이 제공되지 않는 근본적인 이유는?
   - A) AWS가 아직 해당 기능을 구현하지 않았을 뿐이며 곧 추가될 예정이다
   - B) Lattice의 프록시는 서비스 앞단에 있고 호출자별 상태를 갖지 않기 때문이다
   - C) 해당 기능들이 HTTP/2에서 동작하지 않기 때문이다
   - D) IAM 정책으로 대체할 수 있어 불필요하기 때문이다

<details>

<summary>정답 보기</summary>

**정답: B) Lattice의 프록시는 서비스 앞단에 있고 호출자별 상태를 갖지 않기 때문이다**

**설명:**
circuit breaker는 호출자 쪽에서 동시 연결·대기 요청 수를 세야 하고, outlier detection은 호출자별 업스트림 실패 이력을 기억해야 합니다. sidecar 모델은 프록시가 호출자 Pod 안에 있어 이 상태를 자연스럽게 갖지만, Lattice의 프록시는 인프라 계층의 서비스 앞단에 있어 "이 호출자가 최근 어떤 실패를 겪었는가"를 호출자 단위로 유지하지 않습니다. 즉 기능 누락이 아니라 설계 선택의 필연적 결과이며, 대안은 애플리케이션 라이브러리(Resilience4j 등)입니다.
</details>

2. App Mesh의 VirtualNode가 VPC Lattice의 Target Group과 1:1로 대응되지 않는다고 말하는 이유는?
   - A) VirtualNode는 여러 개, Target Group은 하나만 만들 수 있기 때문이다
   - B) VirtualNode가 담고 있던 신원·backend·connection pool·outlier detection 속성이 여러 곳으로 흩어지거나 사라지기 때문이다
   - C) Target Group은 Lambda를 지원하지 않기 때문이다
   - D) VirtualNode는 Cloud Map에 종속되어 있어 변환이 불가능하기 때문이다

<details>

<summary>정답 보기</summary>

**정답: B) VirtualNode가 담고 있던 신원·backend·connection pool·outlier detection 속성이 여러 곳으로 흩어지거나 사라지기 때문이다**

**설명:**
VirtualNode는 "이 워크로드가 누구인지(신원), 어디로 나가는지(backends), 어디서 받는지(listeners, health check, connection pool, outlier detection)"를 하나의 리소스에 담았습니다. Lattice에서 대상 집합과 health check만 Target Group으로 가고, "어디로 나가는지"는 auth policy와 IAM 권한의 문제가 되며, "누구인지"는 IAM Role이 되고, connection pool과 outlier detection은 대응 리소스가 아예 없습니다. 매핑표는 리소스 이름의 대응이며 기능의 대응이 아닙니다.
</details>

3. 이 전환에서 실무적으로 가장 과소평가되는 기능 GAP은 무엇이며 그 이유는?
   - A) circuit breaker — 구현 난도가 가장 높기 때문
   - B) 관측성(분산 추적 span) — AS-IS에서는 애플리케이션 코드를 건드리지 않고 얻었던 것이 TO-BE에서는 애플리케이션 계측 작업이 되기 때문
   - C) traffic mirroring — 대안이 전혀 없기 때문
   - D) fault injection — 프로덕션 장애 대응에 필수이기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 관측성(분산 추적 span) — AS-IS에서는 애플리케이션 코드를 건드리지 않고 얻었던 것이 TO-BE에서는 애플리케이션 계측 작업이 되기 때문**

**설명:**
circuit breaker나 retry는 "라이브러리를 넣는다"는 명확한 대안과 산정 가능한 비용이 있습니다. 반면 Envoy가 자동으로 만들어주던 span은 애플리케이션 코드 무변경으로 얻은 것이었고, 같은 수준의 추적을 얻으려면 모든 서비스에 OpenTelemetry 계측이 필요해 애플리케이션 팀의 작업 항목이 됩니다. 게다가 Lattice 구간 자체는 span이 없어 추적 그래프에 빈 구간으로 남고, 그 간격에 네트워크 지연과 Lattice 처리 지연이 섞여 분리되지 않습니다.
</details>

4. AWS Gateway API Controller가 멈추면 어떤 일이 발생하는가?
   - A) 모든 트래픽이 즉시 차단된다
   - B) 트래픽은 계속 흐르지만 새로 뜬 Pod가 Target으로 등록되지 않고 죽은 Pod가 해제되지 않는다
   - C) Lattice Service가 자동 삭제된다
   - D) IAM 인증이 비활성화된다

<details>

<summary>정답 보기</summary>

**정답: B) 트래픽은 계속 흐르지만 새로 뜬 Pod가 Target으로 등록되지 않고 죽은 Pod가 해제되지 않는다**

**설명:**
컨트롤러의 본업은 Kubernetes의 선언적 상태와 Lattice의 실제 대상 목록을 계속 맞춰주는 것입니다. `backendRefs`가 가리키는 Service의 엔드포인트 변화를 감시해 Target을 등록·해제합니다. 컨트롤러가 멈추면 Lattice는 마지막으로 알려진 Target 목록으로 트래픽을 계속 흘려보내지만 그 목록이 낡습니다. 따라서 컨트롤러 Deployment의 가용성과 IAM 권한이 데이터 경로의 신뢰성에 직접 연결됩니다.
</details>

5. ingress-nginx를 함께 쓰는 환경에서 Lattice 전환의 범위에 대한 설명으로 올바른 것은?
   - A) ingress-nginx도 Lattice로 대체해야 한다
   - B) AWS Gateway API Controller는 현재 Lattice를 통한 동서(East-West) 트래픽에만 집중하므로, ingress-nginx가 처리하던 남북 트래픽은 전환 대상이 아니며 두 경로가 공존하는 것이 정상이다
   - C) ingress-nginx와 Lattice는 동시에 사용할 수 없다
   - D) Gateway API Controller가 남북 트래픽까지 처리하므로 ingress-nginx는 즉시 제거해야 한다

<details>

<summary>정답 보기</summary>

**정답: B) AWS Gateway API Controller는 현재 Lattice를 통한 동서(East-West) 트래픽에만 집중하므로, ingress-nginx가 처리하던 남북 트래픽은 전환 대상이 아니며 두 경로가 공존하는 것이 정상이다**

**설명:**
Kubernetes Gateway API는 원래 남북(Ingress)과 동서(Mesh) 트래픽 모두를 다루도록 설계되었지만, AWS Gateway API Controller는 현재 동서 트래픽에만 집중합니다. ALB/NLB 형태의 남북 기능은 AWS Load Balancer Controller의 영역입니다. 따라서 ingress-nginx가 담당하던 인그레스 경로는 이 전환의 대상이 아니고, 동서 트래픽만 Lattice로 옮겨가며 두 경로가 공존하는 구성이 정상적인 결과입니다.
</details>

6. Pod readiness gate를 Lattice 환경에서 사용하는 이유는?
   - A) Pod의 CPU 사용률을 제한하기 위해
   - B) Lattice Target Group의 health가 Healthy가 될 때까지 Pod를 Ready로 표시하지 않아, 롤링 업데이트가 새 Pod가 건강해질 때까지 구 Pod를 종료하지 않게 하기 위해
   - C) IAM credential이 준비될 때까지 트래픽을 막기 위해
   - D) Envoy sidecar 주입을 대기하기 위해

<details>

<summary>정답 보기</summary>

**정답: B) Lattice Target Group의 health가 Healthy가 될 때까지 Pod를 Ready로 표시하지 않아, 롤링 업데이트가 새 Pod가 건강해질 때까지 구 Pod를 종료하지 않게 하기 위해**

**설명:**
Kubernetes가 Pod를 Ready로 보더라도 Lattice Target Group에서는 아직 Healthy가 아닐 수 있습니다. 이 상태에서 롤링 업데이트가 구 Pod를 종료하면 순간적으로 건강한 Target이 없어지는 구간이 생깁니다. Pod readiness gate는 Lattice 관점의 health를 Pod의 Ready 조건에 연결해 이 문제를 막으며, 전환 기간 중 무중단을 확보하는 데 중요한 장치입니다.
</details>
