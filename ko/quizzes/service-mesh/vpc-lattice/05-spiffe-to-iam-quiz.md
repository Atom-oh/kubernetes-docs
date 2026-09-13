# 워크로드 신원 모델 전환 퀴즈

이 퀴즈는 SPIFFE/SPIRE의 구조, attestation 원리, IAM Auth와의 유사점과 결정적 차이에 대한 이해도를 테스트합니다.

## 객관식 문제

1. SPIFFE ID에 IP 주소나 호스트명 같은 네트워크 정보가 들어가지 않는 이유는?
   - A) URI 형식이 IP 주소를 표현할 수 없기 때문
   - B) 워크로드가 어디로 스케줄되든 IP가 바뀌든 신원은 그대로 유지되어야 하기 때문
   - C) 네트워크 정보는 SVID에 별도로 담기기 때문
   - D) 보안상 IP를 노출하면 안 되기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 워크로드가 어디로 스케줄되든 IP가 바뀌든 신원은 그대로 유지되어야 하기 때문**

**설명:**
SPIFFE ID는 `spiffe://<trust-domain>/<workload-path>` 형식으로, 경로 부분은 보통 namespace와 ServiceAccount를 반영합니다. 네트워크 정보를 배제한 것은 의도된 설계입니다 — Pod가 재스케줄되고 IP가 바뀌어도 신원이 유지되어야 하기 때문입니다. 이것이 "IP 기반 통제에서 신원 기반 통제로"의 출발점이며, Lattice의 link-local 대역에서 목적지 IP 기반 통제가 무의미해지는 상황과 같은 방향의 사고입니다.
</details>

2. SPIRE의 Workload Attestation에서 bootstrapping 문제가 해소되는 결정적 지점은?
   - A) 워크로드가 미리 심어둔 토큰을 제시하는 단계
   - B) Agent가 신뢰한 kernel/attestor 모델에서 kernel의 peer 정보를 얻고 workload selector와 대조한다
   - C) Server가 SVID에 서명하는 단계
   - D) Envoy가 SDS로 인증서를 받는 단계

<details>

<summary>정답 보기</summary>

**정답: B) Agent가 신뢰한 kernel/attestor 모델에서 kernel의 peer 정보를 얻고 workload selector와 대조한다**

**설명:**
공유 application secret을 workload에 미리 배포할 필요를 줄이지만 host 침해·잘못된 selector·attestor 설정에 대한 무조건적 보장은 아닙니다.
</details>

3. SVID가 짧은 수명으로 설계된 이유는?
   - A) 저장 공간을 절약하기 위해
   - B) 짧은 수명은 자격 증명 사용 기간을 제한하지만 침해 대응이나 인가 제어를 대체하지 않는다
   - C) CA의 서명 부하를 분산하기 위해
   - D) 실행 중 비밀과 모든 침해 대응 요구를 없애기 위해

<details>

<summary>정답 보기</summary>

**정답: B) 짧은 수명은 자격 증명 사용 기간을 제한하지만 침해 대응이나 인가 제어를 대체하지 않는다**

**설명:**
갱신·runtime 저장·replay 노출·긴급 Deny/폐기 동작을 검토합니다. 만료되는 자격 증명에도 비밀이 있으며 만료 전까지 자동으로 안전한 것은 아닙니다.
</details>

4. SPIFFE/SPIRE와 Lattice IAM Auth의 구조적 유사점 두 가지는?
   - A) 둘 다 X.509 인증서를 사용하고 둘 다 mTLS를 수행한다
   - B) 양쪽 모두 이미지 내 장기 비밀을 피할 수 있지만 runtime 개인 키나 임시 비밀 자격 증명은 보호해야 한다
   - C) 둘 다 고객이 CA를 운영하고 둘 다 연결 단위로 인증한다
   - D) 둘 다 AWS 외부 워크로드를 지원하고 둘 다 요청 단위로 인증한다

<details>

<summary>정답 보기</summary>

**정답: B) 양쪽 모두 이미지 내 장기 비밀을 피할 수 있지만 runtime 개인 키나 임시 비밀 자격 증명은 보호해야 한다**

**설명:**
X.509-SVID 전달에는 key material이, IAM 자격 증명에는 secret access key와 session token이 포함됩니다. 플랫폼 attestation이 바꾸는 것은 provisioning이며 socket/endpoint·메모리·캐시 보호 필요성은 사라지지 않습니다.
</details>

5. 이 전환의 "결정적 차이 (a)"인 인증 방향성 변화의 실무적 함의는?
   - A) 클라이언트 증명이 약화되므로 애플리케이션에서 보완해야 한다
   - B) 서버 신원 증명이 TLS 서버 인증서 수준으로 내려가므로, 방어선이 워크로드 간 상호 인증에서 Lattice 리소스 생성 권한의 IAM 통제로 이동한다
   - C) 양방향 인증이 유지되므로 심의에 영향이 없다
   - D) 인증 자체가 불필요해진다

<details>

<summary>정답 보기</summary>

**정답: B) 서버 신원 증명이 TLS 서버 인증서 수준으로 내려가므로, 방어선이 워크로드 간 상호 인증에서 Lattice 리소스 생성 권한의 IAM 통제로 이동한다**

**설명:**
클라이언트 증명은 오히려 세밀해집니다(요청 단위 SigV4 검증). 문제는 서버 증명입니다 — 클라이언트가 확인할 수 있는 것은 "TLS 인증서가 유효하고 도메인이 맞다"까지이고, "이 서비스가 진짜 그 팀의 서비스인가"를 워크로드 신원 체계로 확인하는 단계가 없습니다. 대응은 Lattice Service를 만들 수 있는 주체를 IAM으로 엄격히 제한하고 service network association을 통제하며 CloudTrail로 감시하는 것입니다. 심의 문서에 "상호 인증"이라고 적혀 있었다면 그 항목을 다시 써야 합니다.
</details>

6. 금융권 심의에서 "결정적 차이 (b)"인 신뢰 근원 소유권 이전이 무거운 항목인 이유는?
   - A) AWS IAM이 SPIRE보다 보안성이 낮기 때문
   - B) 많은 조직의 보안 기준이 "인증 체계의 신뢰 근원을 자체 통제해야 한다"를 요구하거나 그렇게 해석되는 조항을 갖고 있고, 자체 CA 운영이 그 요구를 만족시키는 직접적 방법이었기 때문
   - C) CloudTrail이 감사 증적을 제공하지 않기 때문
   - D) IAM 정책 결정권이 AWS로 넘어가기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 많은 조직의 보안 기준이 "인증 체계의 신뢰 근원을 자체 통제해야 한다"를 요구하거나 그렇게 해석되는 조항을 갖고 있고, 자체 CA 운영이 그 요구를 만족시키는 직접적 방법이었기 때문**

**설명:**
SPIRE 도입 자체가 그 심의를 통과한 결과일 가능성이 높습니다. Lattice IAM Auth로 옮기면 논거를 다시 세워야 하며, 제시 가능한 근거는 책임 공유 모델, 정책 결정권 유지(누가 무엇을 호출할 수 있는가는 고객이 IAM으로 정의), CloudTrail·access log를 통한 감사 증적, 고객이 CA 개인키를 보유하지 않으므로 키 유출 위험 자체가 제거되는 이점 등입니다. 다만 이것은 "동등하다"가 아니라 "다른 방식으로 통제된다"는 주장이며, 수용 여부는 조직 기준에 달려 있습니다. D는 틀렸습니다 — 정책 결정권은 고객이 유지합니다.
</details>

7. Lattice로 전환하면서 SPIRE를 계속 운영해야 할 수 있는 상황은?
   - A) IAM Auth를 쓰는 모든 경우
   - B) 선택한 설계에 endpoint mTLS나 지원되는 AWS 외부 workload의 SPIFFE 신원이 계속 필요할 때
   - C) Gateway API Controller를 사용하는 경우
   - D) 멀티 클러스터 구성인 경우

<details>

<summary>정답 보기</summary>

**정답: B) 선택한 설계에 endpoint mTLS나 지원되는 AWS 외부 workload의 SPIFFE 신원이 계속 필요할 때**

**설명:**
SPIRE 유지는 설계 선택이며 모든 AWS 외부 workload의 보편적 필수 사항은 아닙니다. 다른 credential provider와 지원 사설 network 경로도 평가할 수 있습니다.
</details>
