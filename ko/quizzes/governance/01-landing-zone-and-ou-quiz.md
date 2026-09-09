# Landing Zone, OU와 조직 Control 퀴즈

> 이 퀴즈는 [Landing Zone, OU와 조직 Control](../../governance/01-landing-zone-and-ou.md) 문서의 학습 내용을 테스트합니다.

---

1. Control Tower Landing Zone 4.0에서 `IdentityCenterBaseline`을 활성화하기 위한 전제 조건은?
   - A) 아무 baseline도 필요 없이 독립적으로 활성화할 수 있다
   - B) `CentralSecurityRolesBaseline`이 먼저 활성화되어 있어야 하며, 이는 다시 `CentralConfigBaseline`을 요구한다
   - C) `BackupCentralVaultBaseline`이 먼저 활성화되어 있어야 한다
   - D) Security OU가 수동으로 생성되어 있어야 한다

<details>
<summary>정답 보기</summary>

**정답: B) `CentralSecurityRolesBaseline`이 먼저 활성화되어 있어야 하며, 이는 다시 `CentralConfigBaseline`을 요구한다**

**설명:**
Landing Zone 4.0의 baseline 활성화 의존 체인은 `CentralConfigBaseline` → `CentralSecurityRolesBaseline` → `IdentityCenterBaseline`/`BackupAdminBaseline`/`BackupCentralVaultBaseline` 순서입니다. 즉 Config 활성화 여부가 Identity Center baseline 사용 가능 여부를 직접 결정하므로, 이 둘을 독립적인 결정으로 다룰 수 없습니다.

</details>

---

2. Control Tower Landing Zone 4.0에서 Security OU에 대한 설명으로 옳은 것은?
   - A) 3.x와 동일하게 관리자가 자유롭게 지정 Security OU를 만들 수 있다
   - B) service integration Account들이 위치한 OU가 자동으로 Security OU로 지정된다
   - C) Security OU는 4.0부터 완전히 폐지되었다
   - D) 모든 Account가 기본적으로 Security OU에 속한다

<details>
<summary>정답 보기</summary>

**정답: B) service integration Account들이 위치한 OU가 자동으로 Security OU로 지정된다**

**설명:**
4.0에서는 지정 Security OU를 관리자가 만들지 않고, service integration Account들이 위치한 OU가 자동으로 Security OU로 지정됩니다. 이 OU에는 AWSControlTowerBaseline과 Config Baseline을 적용할 수 없고, 일반 Account를 여기 두면 baseline 리소스를 받지 못하는 등의 파생 제약이 생깁니다.

</details>

---

3. Organizations의 SCP 연결 전략 중 "Layered bundle"이 quota 관점에서 유리한 이유는?
   - A) SCP 문서 크기 한도가 더 크기 때문이다
   - B) 상속된 정책은 entity당 연결 개수 한도(10개)를 소비하지 않기 때문이다
   - C) RCP와 동일한 quota를 공유하기 때문이다
   - D) Root에는 SCP 개수 제한이 없기 때문이다

<details>
<summary>정답 보기</summary>

**정답: B) 상속된 정책은 entity당 연결 개수 한도(10개)를 소비하지 않기 때문이다**

**설명:**
Root에 예외 없는 최소 SCP만 두고 나머지는 OU별 정책 묶음으로 상속시키는 Layered bundle 전략은 상속을 적극 활용하므로 OU별 direct-attach 한도를 절약합니다. 반면 OU별 완성형 직접 연결 전략은 상속을 쓰지 않아 OU 하나에서 10개 한도를 그대로 소비합니다.

</details>

---

4. RCP(Resource Control Policy)를 SCP와 다르게 다뤄야 하는 이유는?
   - A) RCP는 SCP보다 문서 크기가 더 크다
   - B) RCP는 조직 전체 최대 연결 수가 SCP보다 많다
   - C) RCP는 실사용 4개뿐이고 문서 크기도 SCP의 절반이라, 계층적 bundle 전략을 쓸 여유가 없다
   - D) RCP는 principal의 권한을 부여하는 정책이다

<details>
<summary>정답 보기</summary>

**정답: C) RCP는 실사용 4개뿐이고 문서 크기도 SCP의 절반이라, 계층적 bundle 전략을 쓸 여유가 없다**

**설명:**
RCP는 entity당 최대 5개(RCPFullAWSAccess 포함, 실사용 4개)이고 문서 크기도 5,120자로 SCP의 절반입니다. 이 때문에 RCP는 외부 principal 접근 차단, confused deputy 방어처럼 조직 전체의 소수 절대 규칙에 한정하고, 세분화는 SCP와 리소스 정책에 위임하는 것이 권장됩니다.

</details>
