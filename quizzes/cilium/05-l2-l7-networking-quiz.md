# Cilium L2-L7 네트워킹 퀴즈

이 퀴즈는 Cilium의 L2-L7 네트워킹 기능에 대한 이해도를 테스트합니다.

## 문제 1: 로드 밸런싱

<details>
<summary>Cilium에서 지원하는 로드 밸런싱 알고리즘은 무엇인가요?</summary>

**답변:**
- Round Robin
- Least Connection
- Source IP Hash
- Maglev Consistent Hashing
- Random

Cilium은 다양한 로드 밸런싱 알고리즘을 지원하여 트래픽을 효율적으로 분산시킵니다.
</details>

## 문제 2: DSR (Direct Server Return)

<details>
<summary>Cilium의 DSR 모드의 장점은 무엇인가요?</summary>

**답변:**
- **성능 향상**: 응답 트래픽이 로드 밸런서를 거치지 않음
- **대역폭 절약**: 로드 밸런서의 네트워크 대역폭 사용량 감소
- **지연 시간 단축**: 직접 응답으로 인한 지연 시간 감소
- **확장성**: 로드 밸런서의 부하 감소로 더 많은 연결 처리 가능
</details>

## 문제 3: L7 프록시

<details>
<summary>Cilium의 L7 프록시 기능을 활성화하는 방법은?</summary>

**답변:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-policy"
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/.*"
```

L7 정책을 정의하면 자동으로 Envoy 프록시가 활성화됩니다.
</details>

## 문제 4: 마스커레이딩

<details>
<summary>Cilium에서 eBPF 기반 마스커레이딩의 장점은?</summary>

**답변:**
- **성능**: iptables보다 빠른 처리 속도
- **확장성**: 더 많은 연결 처리 가능
- **효율성**: 커널 공간에서 직접 처리
- **유연성**: 세밀한 제어 가능
- **디버깅**: 더 나은 관찰성 제공
</details>

## 문제 5: 서비스 메시 통합

<details>
<summary>Cilium이 Istio와 통합될 때의 이점은?</summary>

**답변:**
- **성능 향상**: eBPF 기반 데이터 플레인으로 더 빠른 처리
- **리소스 효율성**: 사이드카 프록시 오버헤드 감소
- **네트워크 정책**: Cilium의 강력한 네트워크 정책 활용
- **관찰성**: Hubble을 통한 네트워크 가시성
- **보안**: 투명한 암호화 및 인증
</details>

## 문제 6: 트래픽 분할

<details>
<summary>Cilium에서 카나리 배포를 위한 트래픽 분할을 구현하는 방법은?</summary>

**답변:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.cilium.io/lb-mode: "dsr"
spec:
  selector:
    app: my-app
  ports:
  - port: 80
---
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "canary-policy"
spec:
  endpointSelector:
    matchLabels:
      app: my-app
  ingress:
  - fromEndpoints: []
    toPorts:
    - ports:
      - port: "80"
      rules:
        http:
        - headers:
          - "X-Canary: true"
          method: "GET"
```
</details>

## 문제 7: 상태 확인

<details>
<summary>Cilium 로드 밸런서의 상태 확인 메커니즘은?</summary>

**답변:**
- **TCP 상태 확인**: 포트 연결 가능성 확인
- **HTTP 상태 확인**: HTTP 응답 코드 확인
- **사용자 정의 상태 확인**: 애플리케이션별 상태 확인
- **자동 복구**: 비정상 백엔드 자동 제외
- **가중치 조정**: 상태에 따른 트래픽 가중치 조정
</details>

## 문제 8: 네트워크 정책과 L7

<details>
<summary>L7 네트워크 정책에서 지원되는 프로토콜은?</summary>

**답변:**
- **HTTP/HTTPS**: REST API 및 웹 트래픽
- **gRPC**: 마이크로서비스 간 통신
- **Kafka**: 메시지 큐 프로토콜
- **DNS**: DNS 쿼리 제어
- **사용자 정의**: Envoy 필터를 통한 확장
</details>

## 문제 9: 성능 최적화

<details>
<summary>Cilium L4 로드 밸런서의 성능을 최적화하는 방법은?</summary>

**답변:**
- **XDP 모드 활성화**: 커널 바이패스로 최고 성능
- **DSR 모드 사용**: 응답 트래픽 최적화
- **Maglev 해싱**: 일관된 해싱으로 연결 유지
- **CPU 어피니티**: 특정 CPU 코어에 바인딩
- **메모리 튜닝**: 적절한 버퍼 크기 설정
</details>

## 문제 10: 문제 해결

<details>
<summary>L7 정책이 작동하지 않을 때 확인해야 할 사항은?</summary>

**답변:**
1. **Envoy 프록시 상태**: `cilium status` 명령으로 확인
2. **정책 구문**: YAML 구문 및 셀렉터 확인
3. **포드 레이블**: 정책 셀렉터와 포드 레이블 일치 확인
4. **로그 확인**: `cilium monitor` 및 Envoy 로그 확인
5. **네트워크 연결**: 기본 L3/L4 연결 확인
6. **리소스 제한**: CPU/메모리 리소스 충분성 확인
</details>

---

**점수 계산:**
- 8-10개 정답: 우수 (Cilium L2-L7 네트워킹 전문가 수준)
- 6-7개 정답: 양호 (추가 학습 권장)
- 4-5개 정답: 보통 (기본 개념 복습 필요)
- 0-3개 정답: 미흡 (전체 내용 재학습 권장)
