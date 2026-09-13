# Data·Security 경계 퀴즈

> 이 퀴즈는 [Data·Security 경계](../../governance/05-data-security-boundaries.md) 문서의 학습 내용을 테스트합니다.

---

1. Multi-AZ DB cluster snapshot 공유 불가에서 도출할 수 있는 결론은?
   - A) 모든 복구가 불가능
   - B) 해당 RDS sharing 경로는 사용할 수 없어 engine별 대체 복구를 검증해야 함
   - C) Workload-owned DB가 반드시 강제됨
   - D) AWS Backup의 모든 vault도 동일함

<details>
<summary>정답 보기</summary>

**정답: B) 해당 RDS sharing 경로는 사용할 수 없어 engine별 대체 복구를 검증해야 함**

**설명:**
한 API 제한은 논리 백업·복제 등 모든 대안의 불가능을 뜻하지 않습니다. 지원 범위와 RTO/RPO를 검증해 ownership을 결정합니다.

</details>

---

2. 사고 후 copy가 필요한 복구 경로의 RTO에 포함할 것은?
   - A) 태그 이름만
   - B) copy·restore·애플리케이션 검증 시간
   - C) 과거 backup 보존 기간만
   - D) Security Hub 점수만

<details>
<summary>정답 보기</summary>

**정답: B) copy·restore·애플리케이션 검증 시간**

**설명:**
사전 copy가 있다면 copy 주기는 RPO에 영향을 줍니다. 에어갭 vault의 shared restore처럼 recipient copy가 필요 없는 경로도 구분합니다.

</details>

---

3. Cross-account backup 활성화 후 권한에 대한 맞는 설명은?
   - A) 모든 사용자가 IAM Deny 우회
   - B) IAM·vault·KMS와 copy destination 조건 및 RAM share 권한을 함께 검토
   - C) Vault가 자동 public
   - D) 복사된 백업은 조직 이탈 시 자동 삭제

<details>
<summary>정답 보기</summary>

**정답: B) IAM·vault·KMS와 copy destination 조건 및 RAM share 권한을 함께 검토**

**설명:**
기능 활성화 자체가 권한 부여는 아닙니다. 일반 vault의 copy와 에어갭 vault의 sharing은 별도 경로이며 승인 대상과 source 접근 불능 상황을 시험합니다.

</details>

---

4. Security Hub CSPM의 Config 의존성이 뜻하는 것은?
   - A) Config 없이 모든 control 정상
   - B) 대부분 CSPM control에 recording 필요; Identity Center 자체 의존성으로 확대하지 않음
   - C) GuardDuty를 대체
   - D) 모든 AWS MCP 요청에 Config 필요

<details>
<summary>정답 보기</summary>

**정답: B) 대부분 CSPM control에 recording 필요; Identity Center 자체 의존성으로 확대하지 않음**

**설명:**
Control Tower 관리형 baseline 의존성과 IAM Identity Center 서비스 요구사항을 구분합니다. Security Hub 기능별 scope와 리전 coverage도 확인합니다.

</details>
