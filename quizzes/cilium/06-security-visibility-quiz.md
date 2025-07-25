# Cilium 보안 및 가시성 퀴즈

> **지원 버전**: Cilium 1.17  
> **마지막 업데이트**: 2025년 7월 21일

## 네트워크 정책 기본

1. **Kubernetes NetworkPolicy와 Cilium NetworkPolicy의 주요 차이점은 무엇인가요?**
   - A) Cilium NetworkPolicy는 L7 정책을 지원하지 않음
   - B) Kubernetes NetworkPolicy는 L7 정책을 지원하지 않음
   - C) Cilium NetworkPolicy는 특정 노드에만 적용 가능
   - D) Kubernetes NetworkPolicy는 더 높은 성능 제공
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) Kubernetes NetworkPolicy는 L7 정책을 지원하지 않음</p>
   <p><strong>설명</strong>: Kubernetes NetworkPolicy는 L3/L4 수준의 정책만 지원하는 반면, Cilium NetworkPolicy는 L3부터 L7까지 더 광범위한 정책을 지원합니다.</p>
   </details>

2. **Cilium NetworkPolicy의 API 그룹은 무엇인가요?**
   - A) networking.k8s.io
   - B) cilium.io
   - C) policy.cilium.io
   - D) network.cilium.io
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) cilium.io</p>
   <p><strong>설명</strong>: Cilium NetworkPolicy는 cilium.io API 그룹을 사용합니다.</p>
   </details>

3. **Cilium NetworkPolicy에서 'endpointSelector'의 역할은 무엇인가요?**
   - A) 정책이 적용될 대상 Pod 선택
   - B) 정책이 적용될 대상 노드 선택
   - C) 정책이 적용될 대상 네임스페이스 선택
   - D) 정책이 적용될 대상 서비스 선택
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) 정책이 적용될 대상 Pod 선택</p>
   <p><strong>설명</strong>: endpointSelector는 정책이 적용될 대상 Pod(엔드포인트)를 선택하는 데 사용됩니다.</p>
   </details>

4. **Cilium NetworkPolicy에서 'ingress' 규칙은 무엇을 제어하나요?**
   - A) 선택된 Pod로 들어오는 트래픽
   - B) 선택된 Pod에서 나가는 트래픽
   - C) 선택된 Pod 내부의 트래픽
   - D) 클러스터 외부로의 트래픽
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) 선택된 Pod로 들어오는 트래픽</p>
   <p><strong>설명</strong>: ingress 규칙은 선택된 Pod로 들어오는 트래픽을 제어합니다.</p>
   </details>

5. **Cilium NetworkPolicy에서 'egress' 규칙은 무엇을 제어하나요?**
   - A) 선택된 Pod로 들어오는 트래픽
   - B) 선택된 Pod에서 나가는 트래픽
   - C) 선택된 Pod 내부의 트래픽
   - D) 클러스터 외부에서의 트래픽
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) 선택된 Pod에서 나가는 트래픽</p>
   <p><strong>설명</strong>: egress 규칙은 선택된 Pod에서 나가는 트래픽을 제어합니다.</p>
   </details>

## L7 정책

6. **Cilium의 L7 HTTP 정책에서 필터링할 수 있는 속성이 아닌 것은?**
   - A) 경로(Path)
   - B) 메서드(Method)
   - C) 헤더(Headers)
   - D) 응답 시간(Response Time)
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: D) 응답 시간(Response Time)</p>
   <p><strong>설명</strong>: Cilium의 L7 HTTP 정책은 경로, 메서드, 헤더와 같은 HTTP 요청 속성을 필터링할 수 있지만 응답 시간은 필터링 대상이 아닙니다.</p>
   </details>

7. **Cilium의 L7 Kafka 정책에서 필터링할 수 있는 속성은?**
   - A) 토픽(Topic)
   - B) 파티션(Partition)
   - C) 오프셋(Offset)
   - D) 위의 모든 것
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: A) 토픽(Topic)</p>
   <p><strong>설명</strong>: Cilium의 L7 Kafka 정책은 주로 토픽, API 키 등을 기반으로 필터링할 수 있습니다.</p>
   </details>

8. **Cilium의 L7 DNS 정책에서 'matchPattern' 규칙은 무엇을 허용하나요?**
   - A) 정확한 도메인 이름 일치
   - B) 와일드카드를 포함한 도메인 이름 패턴 일치
   - C) IP 주소 일치
   - D) 포트 번호 일치
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) 와일드카드를 포함한 도메인 이름 패턴 일치</p>
   <p><strong>설명</strong>: matchPattern 규칙은 와일드카드(*)를 포함한 도메인 이름 패턴을 일치시킬 수 있습니다. 예: *.example.com</p>
   </details>

9. **Cilium의 L7 정책을 적용하기 위해 필요한 구성 요소는?**
   - A) kube-proxy
   - B) Envoy 프록시
   - C) NGINX 인그레스 컨트롤러
   - D) HAProxy
   
   <details>
   <summary>정답 보기</summary>
   <p><strong>정답</strong>: B) Envoy 프록시</p>
   <p><strong>설명</strong>: Cilium은 L7 정책을 적용하기 위해 Envoy 프록시를 사용합니다.</p>
   </details>

10. **Cilium의 L7 정책이 지원하는 프로토콜이 아닌 것은?**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) SMTP</p>
    <p><strong>설명</strong>: Cilium은 HTTP, gRPC, Kafka 등의 L7 프로토콜을 지원하지만, SMTP는 기본적으로 지원하지 않습니다.</p>
    </details>

## 암호화 및 보안

11. **Cilium에서 네트워크 트래픽 암호화에 사용할 수 있는 프로토콜은?**
    - A) IPsec
    - B) WireGuard
    - C) A와 B 모두
    - D) TLS
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) A와 B 모두</p>
    <p><strong>설명</strong>: Cilium은 IPsec과 WireGuard 모두를 사용하여 노드 간 트래픽을 암호화할 수 있습니다.</p>
    </details>

12. **Cilium의 암호화 기능이 보호하는 트래픽은?**
    - A) 노드 간 트래픽만
    - B) Pod 간 트래픽만
    - C) 노드와 Pod 간 트래픽만
    - D) 모든 클러스터 트래픽
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) Pod 간 트래픽만</p>
    <p><strong>설명</strong>: Cilium의 암호화 기능은 주로 Pod 간 트래픽을 보호합니다.</p>
    </details>

13. **Cilium의 Host Firewall 기능은 무엇을 보호하나요?**
    - A) Pod 네트워크 인터페이스
    - B) 호스트 네트워크 인터페이스
    - C) 서비스 엔드포인트
    - D) 컨테이너 런타임
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) 호스트 네트워크 인터페이스</p>
    <p><strong>설명</strong>: Cilium의 Host Firewall은 호스트 자체의 네트워크 인터페이스를 보호하여 호스트 수준의 보안을 강화합니다.</p>
    </details>

14. **Cilium의 보안 기능 중 다음 설명에 해당하는 것은? "특정 애플리케이션 계층 프로토콜의 특정 필드나 패턴을 기반으로 트래픽을 필터링"**
    - A) 네트워크 정책
    - B) L7 정책
    - C) 암호화
    - D) 침입 탐지
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: B) L7 정책</p>
    <p><strong>설명</strong>: L7(애플리케이션 계층) 정책은 HTTP, gRPC, Kafka 등의 프로토콜에서 특정 필드나 패턴을 기반으로 트래픽을 필터링할 수 있습니다.</p>
    </details>

15. **Cilium의 Identity 기반 보안 모델에서 'Identity'는 무엇을 기반으로 하나요?**
    - A) Pod 이름
    - B) 노드 이름
    - C) 레이블
    - D) IP 주소
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) 레이블</p>
    <p><strong>설명</strong>: Cilium의 Identity는 Pod의 레이블을 기반으로 하며, 이는 IP 주소가 변경되더라도 일관된 보안 정책을 적용할 수 있게 합니다.</p>
    </details>

## 가시성 및 모니터링

16. **Hubble은 무엇인가요?**
    - A) Cilium의 네트워크 가시성 도구
    - B) Cilium의 로드 밸런서
    - C) Cilium의 암호화 프로토콜
    - D) Cilium의 DNS 서버
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) Cilium의 네트워크 가시성 도구</p>
    <p><strong>설명</strong>: Hubble은 Cilium의 네트워크 가시성 도구로, eBPF를 기반으로 네트워크 흐름을 관찰하고 분석할 수 있습니다.</p>
    </details>

17. **Hubble UI에서 제공하는 기능이 아닌 것은?**
    - A) 서비스 의존성 맵
    - B) 네트워크 흐름 시각화
    - C) 정책 위반 알림
    - D) 코드 배포 관리
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 코드 배포 관리</p>
    <p><strong>설명</strong>: Hubble UI는 서비스 의존성 맵, 네트워크 흐름 시각화, 정책 위반 알림 등을 제공하지만 코드 배포 관리는 제공하지 않습니다.</p>
    </details>

18. **Hubble CLI를 사용하여 특정 Pod의 네트워크 흐름을 관찰하는 명령어는?**
    - A) `hubble observe --pod <pod-name>`
    - B) `hubble watch --pod <pod-name>`
    - C) `hubble monitor --pod <pod-name>`
    - D) `hubble inspect --pod <pod-name>`
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: A) `hubble observe --pod <pod-name>`</p>
    <p><strong>설명</strong>: `hubble observe --pod <pod-name>` 명령어는 특정 Pod의 네트워크 흐름을 실시간으로 관찰할 수 있습니다.</p>
    </details>

19. **Hubble이 수집하는 메트릭이 아닌 것은?**
    - A) HTTP 상태 코드
    - B) TCP 연결 상태
    - C) 드롭된 패킷 수
    - D) 컨테이너 CPU 사용량
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: D) 컨테이너 CPU 사용량</p>
    <p><strong>설명</strong>: Hubble은 네트워크 관련 메트릭(HTTP 상태 코드, TCP 연결 상태, 드롭된 패킷 수 등)을 수집하지만, 컨테이너 CPU 사용량과 같은 시스템 메트릭은 수집하지 않습니다.</p>
    </details>

20. **Cilium과 Prometheus를 통합하는 방법은?**
    - A) Cilium Operator에 Prometheus 어노테이션 추가
    - B) Prometheus 서버에 Cilium 플러그인 설치
    - C) Cilium에 ServiceMonitor 리소스 생성
    - D) Prometheus에 Cilium 대시보드 가져오기
    
    <details>
    <summary>정답 보기</summary>
    <p><strong>정답</strong>: C) Cilium에 ServiceMonitor 리소스 생성</p>
    <p><strong>설명</strong>: Prometheus Operator를 사용하는 경우, Cilium에 ServiceMonitor 리소스를 생성하여 Cilium 메트릭을 수집할 수 있습니다.</p>
    </details>
