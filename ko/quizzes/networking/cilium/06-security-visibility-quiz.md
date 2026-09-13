# Cilium 보안 및 가시성 퀴즈

> **검토 기준**: Cilium 1.20.1; Hubble CLI 1.19.4.
> **최종 검토**: 2026년 9월 12일.

[본문으로 돌아가기](../../../networking/cilium/06-security-visibility.md)

## 네트워크 정책 기본

1. **CiliumNetworkPolicy는 표준 Kubernetes NetworkPolicy를 어떻게 확장하나요?**

   - A) Pod를 선택할 수 없습니다
   - B) 지원되는 L7 프로토콜 규칙을 추가할 수 있습니다
   - C) 노드만 보호합니다
   - D) 더 낮은 지연을 보장합니다

   <details>
   <summary>정답 보기</summary>

   **정답: B) 지원되는 L7 프로토콜 규칙을 추가할 수 있습니다**

   표준 NetworkPolicy는 L3/L4 연결을 제어하며 Cilium은 HTTP·DNS 정책 등을 추가합니다. API 선택만으로 성능이 보장되지는 않습니다.

   </details>

2. **CiliumNetworkPolicy의 API 버전은 무엇인가요?**

   - A) networking.k8s.io/v1
   - B) cilium.io/v2
   - C) policy.cilium.io/v1
   - D) network.cilium.io/v1

   <details>
   <summary>정답 보기</summary>

   **정답: B) cilium.io/v2**

   그룹은 cilium.io이며 이 장에서 사용하는 정책 버전은 v2입니다.

   </details>

3. **네임스페이스 범위의 CiliumNetworkPolicy에서 endpointSelector는 무엇을 선택하나요?**

   - A) 정책 네임스페이스의 일치하는 엔드포인트
   - B) 모든 Kubernetes 노드
   - C) Prometheus 서버
   - D) LoadBalancer Service만

   <details>
   <summary>정답 보기</summary>

   **정답: A) 정책 네임스페이스의 일치하는 엔드포인트**

   정책의 적용 대상 엔드포인트를 식별합니다. 노드 정책에는 별도의 클러스터 범위 nodeSelector 방식을 사용합니다.

   </details>

4. **policyTypes: [Ingress]인 표준 NetworkPolicy에서 ingress 허용 규칙이 없는 값은 무엇인가요?**

   - A) ingress: [{}]
   - B) ingress: []
   - C) ingress: [{from: [{}]}]
   - D) 모든 출발지 주소에 대한 허용 규칙

   <details>
   <summary>정답 보기</summary>

   **정답: B) ingress: []**

   빈 목록에는 허용 규칙이 없으며 빈 규칙 객체는 모든 ingress를 허용합니다. 다른 적용 대상 정책의 허용은 여전히 합산됩니다.

   </details>

5. **선택된 Pod의 egress 정책은 어느 방향을 제어하나요?**

   - A) 들어오는 연결만
   - B) 나가는 연결
   - C) 프로세스 내부 트래픽만
   - D) API 서버 응답만

   <details>
   <summary>정답 보기</summary>

   **정답: B) 나가는 연결**

   Egress는 외부로 나가는 연결을 제어합니다. 격리된 Pod에는 실제 DNS 서버 등 의존성의 명시적 허용이 필요합니다.

   </details>

## L7 정책

6. **Cilium HTTP 정책의 요청 일치 필드가 아닌 것은 무엇인가요?**

   - A) 경로
   - B) 메서드
   - C) 헤더
   - D) 응답 지연

   <details>
   <summary>정답 보기</summary>

   **정답: D) 응답 지연**

   HTTP 정책은 지원되는 요청 속성을 검사합니다. 응답 시간을 관측한다고 지연이 HTTP 허용 규칙 필드가 되는 것은 아닙니다.

   </details>

7. **예제의 toFQDNs 정책이 DNS 응답을 학습하려면 무엇이 필요한가요?**

   - A) TCP 443 규칙만
   - B) 임의의 외부 IP만
   - C) 접근 가능한 DNS 서버와 일치하는 DNS 프록시 규칙
   - D) Kafka 토픽 규칙

   <details>
   <summary>정답 보기</summary>

   **정답: C) 접근 가능한 DNS 서버와 일치하는 DNS 프록시 규칙**

   DNS 허용·프록시 관측과 이후 목적지 IP 연결 허용은 별개입니다. 예제는 검증한 DNS 엔드포인트의 UDP/TCP DNS를 모두 다룹니다.

   </details>

8. **DNS matchPattern은 무엇을 제공하나요?**

   - A) 포트 할당
   - B) 도메인 이름 와일드카드 일치
   - C) JWT 서명 검증
   - D) 자동 악성 도메인 평판

   <details>
   <summary>정답 보기</summary>

   **정답: B) 도메인 이름 와일드카드 일치**

   지원되는 와일드카드 문법으로 질의·도메인 이름을 검사합니다. 위협 인텔리전스 피드를 가져오지는 않습니다.

   </details>

9. **이 장에서 설명한 HTTP 규칙은 어느 프록시가 구현하나요?**

   - A) kube-proxy
   - B) Envoy
   - C) Prometheus
   - D) Hubble Relay

   <details>
   <summary>정답 보기</summary>

   **정답: B) Envoy**

   Cilium은 HTTP 정책에 Envoy를 연동합니다. DNS 정책은 DNS 프록시를 사용하므로 모든 L7 규칙을 Envoy 규칙으로 설명하면 안 됩니다.

   </details>

10. **현재 API에 없는 과거 Cilium L7 정책 기능은 무엇인가요?**

   - A) HTTP 메서드 검사
   - B) HTTP 경로 검사
   - C) Kafka 토픽 규칙
   - D) DNS 이름 규칙

   <details>
   <summary>정답 보기</summary>

   **정답: C) Kafka 토픽 규칙**

   Kafka L7 정책은 제거되었습니다. 이전 kafka 규칙을 현재 CiliumNetworkPolicy에 복사하지 않습니다.

   </details>

## 암호화 및 보안

11. **Cilium 노드 전송 암호화의 대안 모드를 나열한 것은 무엇인가요?**

   - A) IPsec와 WireGuard
   - B) HTTP와 DNS
   - C) Relay와 Grafana
   - D) SYN과 ACK

   <details>
   <summary>정답 보기</summary>

   **정답: A) IPsec와 WireGuard**

   필요한 모드와 전제 조건을 선택합니다. SPIRE 상호 인증과 Beta ztunnel 워크로드 mTLS는 범위가 다른 별도 기능입니다.

   </details>

12. **이 장의 기본 WireGuard 노드 터널 프로필은 무엇을 보호하나요?**

   - A) 임의의 외부 트래픽을 포함한 모든 패킷
   - B) 노드를 가로지르는 지원 대상 Cilium 관리 Pod 트래픽
   - C) 터널을 통과하는 모든 동일 노드 Pod 트래픽
   - D) 예외 없는 모든 호스트 트래픽

   <details>
   <summary>정답 보기</summary>

   **정답: B) 노드를 가로지르는 지원 대상 Cilium 관리 Pod 트래픽**

   동일 노드 트래픽은 이 노드 터널을 사용하지 않습니다. 노드 간 암호화 확장은 컨트롤 플레인 제외 조건이 있는 별도 Beta 옵션이며 애플리케이션 TLS가 필요할 수 있습니다.

   </details>

13. **Cilium Host Firewall의 보호 대상은 무엇인가요?**

   - A) 브라우저 JavaScript만
   - B) 호스트의 네트워크 트래픽
   - C) 모든 컨테이너 시스템 호출 자동 보호
   - D) Grafana 비밀번호 데이터베이스

   <details>
   <summary>정답 보기</summary>

   **정답: B) 호스트의 네트워크 트래픽**

   호스트 정책은 네트워크 제어입니다. 프로세스·시스템 호출 집행에는 구성된 Tetragon 정책 등의 별도 수단이 필요하며 암호화 호환성도 확인해야 합니다.

   </details>

14. **Authorization 헤더를 일치시키면 해당 사용자가 인증되나요?**

   - A) 예, 존재하는 모든 헤더는 검증된 JWT입니다
   - B) 예, 정규식처럼 보이는 값이 서명을 검증합니다
   - C) 아니요, 헤더 일치는 토큰을 검증하지 않습니다
   - D) 예, HTTP가 8443 포트를 사용하면 됩니다

   <details>
   <summary>정답 보기</summary>

   **정답: C) 아니요, 헤더 일치는 토큰을 검증하지 않습니다**

   실제 인증·인가 로직을 사용합니다. 값을 가진 headers 문자열은 리터럴 일치이며 TLS 포트 번호가 페이로드를 복호화하지도 않습니다.

   </details>

15. **Cilium 보안 ID는 주로 무엇으로 결정되나요?**

   - A) 영원히 고유한 Pod IP
   - B) 보안 관련 레이블 집합
   - C) 사용자의 브라우저 쿠키
   - D) 마지막 HTTP 응답

   <details>
   <summary>정답 보기</summary>

   **정답: B) 보안 관련 레이블 집합**

   보안 관련 레이블이 같은 엔드포인트는 ID를 공유할 수 있습니다. ID 기반 정책만으로 최종 사용자 인증이나 트래픽 암호화가 제공되지는 않습니다.

   </details>

## 가시성 및 모니터링

16. **Hubble의 주된 역할은 무엇인가요?**

   - A) 네트워크 흐름 관측
   - B) 컨테이너 이미지 배포
   - C) 규칙 없이 동작하는 완전한 WAF
   - D) 모든 의심 Pod 자동 격리

   <details>
   <summary>정답 보기</summary>

   **정답: A) 네트워크 흐름 관측**

   Hubble은 흐름 메타데이터, 판정과 지원되는 프로토콜 관측 결과를 제공합니다. 탐지 규칙과 대응 연동은 별도 구성이 필요합니다.

   </details>

17. **Hubble UI가 제공하는 기능은 무엇인가요?**

   - A) 애플리케이션 자격 증명 교체
   - B) 서비스 의존성 맵과 흐름 탐색
   - C) Slack 장애 알림 자동 전송
   - D) 런타임 시스템 호출 정책 설치

   <details>
   <summary>정답 보기</summary>

   **정답: B) 서비스 의존성 맵과 흐름 탐색**

   UI는 Relay를 통해 네트워크 관측 결과를 시각화합니다. 알림·배포·런타임 정책 컨트롤러는 아닙니다.

   </details>

18. **frontend Pod가 어느 쪽 엔드포인트인지와 관계없이 흐름 이벤트를 계속 관찰하는 명령은 무엇인가요?**

   - A) `hubble observe --pod cilium-security-demo/frontend --follow`
   - B) `hubble watch --pod frontend`
   - C) `cilium hubble status`
   - D) `hubble observe --pod app=frontend`

   <details>
   <summary>정답 보기</summary>

   **정답: A) `hubble observe --pod cilium-security-demo/frontend --follow`**

   네임스페이스가 포함된 Pod 이름과 스트리밍용 --follow를 사용합니다. Pod 이름은 레이블 선택자가 아니며 방향·레이블 필터는 별도 플래그입니다.

   </details>

19. **예제의 Hubble 메트릭 플러그인이 제공하지 않는 것은 무엇인가요?**

   - A) HTTP 응답 상태별 수
   - B) TCP 플래그 수
   - C) 관측된 드롭 수
   - D) 컨테이너 CPU 사용량

   <details>
   <summary>정답 보기</summary>

   **정답: D) 컨테이너 CPU 사용량**

   이 플러그인은 네트워크·프록시 이벤트를 관측합니다. TCP 플러그인은 일반적인 동시 연결 수나 RTT 메트릭을 제공하지 않으며 관측 부재·손실도 고려해야 합니다.

   </details>

20. **Prometheus Operator가 설치된 환경에서 ServiceMonitor로 Hubble을 수집하려면 무엇이 필요한가요?**

   - A) Grafana 대시보드 가져오기만
   - B) 공인 hubble-metrics.cilium.io:9091 정적 대상
   - C) 메트릭 활성화와 Prometheus가 선택하는 ServiceMonitor
   - D) 무관한 ConfigMap 생성만

   <details>
   <summary>정답 보기</summary>

   **정답: C) 메트릭 활성화와 Prometheus가 선택하는 ServiceMonitor**

   차트의 헤드리스 Service는 일반적으로 9965인 hubble-metrics 이름의 포트를 제공합니다. Prometheus 네임스페이스·레이블 선택자와 엔드포인트 접근성이 맞아야 합니다.

   </details>
