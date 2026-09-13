# Landing Zone, OU와 조직 Control 퀴즈

> 이 퀴즈는 [Landing Zone, OU와 조직 Control](../../governance/01-landing-zone-and-ou.md) 문서의 학습 내용을 테스트합니다.

---

1. Control Tower4.0의 IdentityCenterBaseline 활성화 전제는?
   - A) 아무 baseline도 필요 없음
   - B) CentralSecurityRolesBaseline과 그 선행 CentralConfigBaseline
   - C) BackupCentralVaultBaseline
   - D) IAM Identity Center 자체가 모든 환경에서 Config를 요구함

<details>
<summary>정답 보기</summary>

**정답: B) CentralSecurityRolesBaseline과 그 선행 CentralConfigBaseline**

**설명:**
Control Tower가 관리하는 baseline의 의존 관계입니다. IAM Identity Center 서비스 자체의 AWS Config 요구사항으로 확대하지 않습니다.

</details>

---

2. Control Tower4.0 Security OU에 대한 설명으로 맞는 것은?
   - A) 모든 OU가 Security OU임
   - B) Service integration Account가 있는 OU가 Security OU로 지정됨
   - C) Security OU가 폐지됨
   - D) 일반 Account에 모든 baseline을 자동 제공함

<details>
<summary>정답 보기</summary>

**정답: B) Service integration Account가 있는 OU가 Security OU로 지정됨**

**설명:**
Integration Account는 같은 parent OU에 두며 landing zone이 관리합니다. AWSControlTowerBaseline/ConfigBaseline은 해당 Security OU에 적용되지 않습니다. 일반 운영 Account를 별도 OU에 두는 것은 설계 선택입니다.

</details>

---

3. Layered SCP bundle이 direct-attachment quota를 절약하는 이유는?
   - A) 문서 크기 제한이 사라짐
   - B) 상속된 정책은 하위 entity의 직접 연결 개수를 소비하지 않음
   - C) 상위 Deny를 하위 Allow가 해제함
   - D) Root의 quota가 무제한임

<details>
<summary>정답 보기</summary>

**정답: B) 상속된 정책은 하위 entity의 직접 연결 개수를 소비하지 않음**

**설명:**
SCP direct-attachment 한도는 entity당10개입니다. 상속은 별도이지만 모든 상위 정책의 유효 권한 제약은 계속 적용됩니다.

</details>

---

4. RCP의 연결 한도와 상속을 올바르게 설명한 것은?
   - A) 권한을 직접 부여함
   - B) 상속을 지원하지 않음
   - C) 5개 중 RCPFullAWSAccess가1개를 쓰며 나머지 direct slot과 상속을 함께 설계함
   - D) SCP와 같은 문서 크기 한도

<details>
<summary>정답 보기</summary>

**정답: C) 5개 중 RCPFullAWSAccess가1개를 쓰며 나머지 direct slot과 상속을 함께 설계함**

**설명:**
RCP의 direct slot은4개 남고 문서는5,120자입니다. 작은 예산이 계층적 상속을 금지하는 것은 아닙니다. 지원 resource와 principal 예외를 확인합니다.

</details>
