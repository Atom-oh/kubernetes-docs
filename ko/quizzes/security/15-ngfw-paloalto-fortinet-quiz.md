# Palo Alto·Fortinet NGFW 퀴즈

> **마지막 업데이트**: 2026년 10월 15일

[본문과 공식 출처 보기](../../security/15-ngfw-paloalto-fortinet.md)

### 1. 일반 GENEVE 지원만으로 AWS GWLB 호환성을 입증할 수 있는가?

- A) UDP 6081이면 충분하다
- B) 아니다; 지원 통합과 AWS metadata 처리를 확인한다
- C) 관리 IP를 peer로 쓰면 충분하다
- D) 제품 로고만 중요하다

<details>
<summary>정답 보기</summary>

**정답: B) 아니다; 지원 통합과 AWS metadata 처리를 확인한다**

**설명:** 공식 배포 모드에 맞는 릴리스·interface·정책·metadata 처리를 확인합니다.

</details>

### 2. 장비 health check 성공이 입증하는 것은?

- A) 모든 IPS signature 활성
- B) 모든 client TLS 복호화
- C) 설정 health endpoint 응답이며 완전한 검사 증거는 아님
- D) N-1 업무 용량 충분

<details>
<summary>정답 보기</summary>

**정답: C) 설정 health endpoint 응답이며 완전한 검사 증거는 아님**

**설명:** health 외에 검사 canary·정책·license·앱 측정을 확인합니다.

</details>

### 3. 제조사 health-check 예시를 어떻게 적용해야 하는가?

- A) HTTP 80이 모든 배포의 공통값
- B) 모든 응답 포트는 교환 가능
- C) GENEVE data와 health protocol은 같아야 한다
- D) 실제 template·target group·장비 응답을 맞춘다

<details>
<summary>정답 보기</summary>

**정답: D) 실제 template·target group·장비 응답을 맞춘다**

**설명:** 수동 가이드에서는 HTTP 금지 문장과 뒤의 HTTP profile 문장이 엇갈립니다. 자동 설정으로 옮기지 말고 선택 버전·template의 TCP/HTTPS 지원과 실제 응답을 확인합니다.

</details>

### 4. 암호화 payload 검사에 필요한 것은?

- A) 지원 복호화·종료와 검증된 신뢰·호환 정책
- B) GWLB 배포만
- C) GENEVE VNI만
- D) target healthy만

<details>
<summary>정답 보기</summary>

**정답: A) 지원 복호화·종료와 검증된 신뢰·호환 정책**

**설명:** GENEVE는 암호화나 TLS 종료가 아닙니다. mTLS·pinning·CA 신뢰·protocol·예외를 검증합니다.

</details>

### 5. ALB HTTPS target group은 backend 인증서를 검증하는가?

- A) 항상 그렇다
- B) 아니다; AWS는 ALB가 target 인증서를 검증하지 않는다고 명시한다
- C) GWLB 활성 때만 그렇다
- D) WAF Block일 때만 그렇다

<details>
<summary>정답 보기</summary>

**정답: B) 아니다; AWS는 ALB가 target 인증서를 검증하지 않는다고 명시한다**

**설명:** 전송 암호화와 요구되는 backend 신원 검증은 별개 설계 속성입니다.

</details>

### 6. 노드 SNAT 후 장비가 관측할 수 있는 주소는?

- A) 불변 workload identity
- B) 항상 원래 Pod 주소
- C) 노드 주소이며 Pod 식별에는 CNI·IPAM 연관이 필요
- D) 항상 browser 사용자 주소

<details>
<summary>정답 보기</summary>

**정답: C) 노드 주소이며 Pod 식별에는 CNI·IPAM 연관이 필요**

**설명:** 변환 위치·시각을 기록합니다. 보존된 Pod IP도 영구 신원이 아닙니다.

</details>

### 7. 독립 GWLB target 추가로 firewall 세션 상태가 복제되는가?

- A) 항상 그렇다
- B) GENEVE가 UDP이므로 그렇다
- C) AZ가 같으면 그렇다
- D) 아니다; 지원 제조사 설계와 시험이 필요하다

<details>
<summary>정답 보기</summary>

**정답: D) 아니다; 지원 제조사 설계와 시험이 필요하다**

**설명:** flow 재배치와 state 복제는 다릅니다. 장애·스케일·업그레이드에서 기존/신규 세션을 시험합니다.

</details>

### 8. 장비 설계를 비교하는 적절한 benchmark는?

- A) 실제 profile·복호화·N-1 용량·latency/error를 포함한 업무 트래픽 측정
- B) 데이터시트 최대 처리량만
- C) EC2 가격만
- D) health 성공만

<details>
<summary>정답 보기</summary>

**정답: A) 실제 profile·복호화·N-1 용량·latency/error를 포함한 업무 트래픽 측정**

**설명:** 트래픽·license·기능·AZ·세션 조건을 통제합니다. 이번 문서 보강에는 실측 결과가 없습니다.

</details>
