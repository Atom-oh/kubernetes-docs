# WAF·origin 보호 퀴즈

> **마지막 업데이트**: 2026년 10월 15일

[본문과 공식 출처 보기](../../security/14-waf-edge-api-security.md)

### 1. 문서의 직접 WAF 연결이 지원되는 API Gateway 리소스는?

- A) REST API
- B) 모든 HTTP API
- C) 모든 WebSocket API
- D) 모든 NLB listener

<details>
<summary>정답 보기</summary>

**정답: A) REST API**

**설명:** 지원 리소스 목록을 확인합니다. 앞단 CloudFront 보호와 직접 연결은 구분합니다.

</details>

### 2. 앞선 넓은 Allow가 일치하면 어떤 일이 생기는가?

- A) 뒤의 모든 규칙이 계속 평가된다
- B) 평가 종료로 뒤의 보호를 건너뛸 수 있다
- C) Count만 종료된다
- D) default Block이 항상 덮어쓴다

<details>
<summary>정답 보기</summary>

**정답: B) 평가 종료로 뒤의 보호를 건너뛸 수 있다**

**설명:** Allow·Block은 종료하고 Count는 계속합니다. priority와 좁은 예외 범위를 검토합니다.

</details>

### 3. body 검사 한도를 올바르게 비교한 것은?

- A) ALB는 항상 64 KB 검사
- B) 모든 리소스 한도가 동일
- C) ALB는 고정 8 KB, CloudFront는 기본 16 KB·지원 설정 최대 64 KB
- D) 검사 한도와 업로드 한도는 같다

<details>
<summary>정답 보기</summary>

**정답: C) ALB는 고정 8 KB, CloudFront는 기본 16 KB·지원 설정 최대 64 KB**

**설명:** 검사 크기는 앱 업로드 한도와 다릅니다. AWS 문서는 gRPC body 검사도 제외합니다.

</details>

### 4. oversize MATCH는 항상 요청을 차단하는가?

- A) action에 관계없이 그렇다
- B) NOT 안에서도 그렇다
- C) 앞의 Allow 후에도 그렇다
- D) 아니다; statement 일치이며 최종 결과는 action·조합에 달렸다

<details>
<summary>정답 보기</summary>

**정답: D) 아니다; statement 일치이며 최종 결과는 action·조합에 달렸다**

**설명:** action·논리 조합·앞선 종료 규칙을 확인합니다. MATCH는 독립 Block action이 아닙니다.

</details>

### 5. CloudFront IP 범위만으로 자신의 distribution을 식별할 수 없는 이유는?

- A) 다른 CloudFront 경로도 같은 인프라를 사용할 수 있다
- B) CloudFront는 HTTPS를 못 쓴다
- C) ALB에는 listener rule이 없다
- D) 모든 origin header는 암호학적 서명이다

<details>
<summary>정답 보기</summary>

**정답: A) 다른 CloudFront 경로도 같은 인프라를 사용할 수 있다**

**설명:** 네트워크 제한과 보호한 origin header·listener 조건 또는 지원 VPC origin을 결합하고 우회를 시험합니다.

</details>

### 6. 바깥의 NOT가 없는 직접 forwarded-IP statement에서 header가 없으면?

- A) fallback이 항상 차단한다
- B) statement는 no match이며 malformed fallback과 다르다
- C) header가 자동 인증된다
- D) 항상 마지막 주소를 쓴다

<details>
<summary>정답 보기</summary>

**정답: B) statement는 no match이며 malformed fallback과 다르다**

**설명:** 누락은 malformed fallback을 호출하지 않습니다. 바깥 NOT는 no match를 match로 반전할 수 있습니다. Geo·ASN·rate는 첫 주소, IP set은 설정한 FIRST·LAST·ANY를 사용합니다.

</details>

### 7. rate-based rule의 올바른 설명은?

- A) 정확한 초당 quota다
- B) window 변경 후 모든 counter가 유지된다
- C) 근사 추적이며 관련 설정 변경은 counter를 초기화한다
- D) client가 바꾸는 집계 키는 회피를 막는다

<details>
<summary>정답 보기</summary>

**정답: C) 근사 추적이며 관련 설정 변경은 counter를 초기화한다**

**설명:** window·집계·초기화·공유 NAT·키 분산을 시험하고 업무 quota는 앱에서 검증합니다.

</details>

### 8. WAF 로그 redaction만으로 자동 확인되는 범위는?

- A) 모든 sampled request도 redaction
- B) 어디에도 민감 정보가 나올 수 없음
- C) 로그 누락 불가
- D) 설정한 로그 필드 처리이며 sampling·data protection은 별도 검토

<details>
<summary>정답 보기</summary>

**정답: D) 설정한 로그 필드 처리이며 sampling·data protection은 별도 검토**

**설명:** 실제 수집 데이터를 확인합니다. sampling과 Security Lake 수집은 로그 redaction으로 자동 보호되지 않습니다.

</details>
