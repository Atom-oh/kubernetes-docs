# Data·Security 경계 퀴즈

> 이 퀴즈는 [Data·Security 경계](../../governance/05-data-security-boundaries.md) 문서의 학습 내용을 테스트합니다.

---

1. Multi-AZ DB cluster의 스냅샷 공유 제약이 다른 cross-account 제약들과 다른 점은?
   - A) 비용이 더 많이 든다는 점만 다르다
   - B) 유일하게 데이터 소유 방식(중앙 운영 vs 워크로드 소유) 자체를 강제로 바꾸는 조건이다
   - C) 서울 리전에서만 발생하는 제약이다
   - D) AWS Backup을 쓰지 않으면 발생하지 않는다

<details>
<summary>정답 보기</summary>

**정답: B) 유일하게 데이터 소유 방식(중앙 운영 vs 워크로드 소유) 자체를 강제로 바꾸는 조건이다**

**설명:**
Multi-AZ DB cluster의 스냅샷은 공유할 수 없어 cross-account 복구 경로가 아예 존재하지 않습니다. 이 경우 DB와 복구 책임을 같은 Account에 두는 workload-owned 방식이 사실상 강제됩니다. 다른 cross-account 백업 제약들은 중앙 운영·워크로드 소유 어느 쪽에도 동일하게 적용되는 공통 guardrail입니다.

</details>

---

2. RTO 계산 시 반드시 포함해야 하는데 흔히 빠지는 요소는?
   - A) IAM 정책 시뮬레이션 시간
   - B) 스냅샷을 manual snapshot으로 복사하는 데 걸리는 시간
   - C) VPC 라우팅 테이블 갱신 시간
   - D) Security Hub finding 생성 시간

<details>
<summary>정답 보기</summary>

**정답: B) 스냅샷을 manual snapshot으로 복사하는 데 걸리는 시간**

**설명:**
RDS 자동 백업은 공유할 수 없어 cross-account로 넘기려면 반드시 manual snapshot으로 복사하는 단계가 필요합니다. TB급 데이터베이스에서는 이 복사 시간이 무시할 수 없는 수준이므로 RTO 계산에 반드시 포함해야 합니다.

</details>

---

3. cross-account backup을 활성화했을 때 보안팀이 반드시 확인해야 하는 위험은?
   - A) 백업 비용이 두 배로 증가한다
   - B) 조직의 모든 member Account 사용자가 자기 Account를 destination으로 설정할 수 있어, 개인정보 백업이 미승인 Account로 복사될 위험이 있다
   - C) 백업이 자동으로 암호화되지 않는다
   - D) 백업 vault가 자동으로 public이 된다

<details>
<summary>정답 보기</summary>

**정답: B) 조직의 모든 member Account 사용자가 자기 Account를 destination으로 설정할 수 있어, 개인정보 백업이 미승인 Account로 복사될 위험이 있다**

**설명:**
이를 막기 위해 `backup:CopyFromBackupVault` 권한에 `backup:CopyTargets`/`backup:CopyTargetOrgPaths` 조건을 걸어 승인된 vault·OU로만 복사되도록 강제해야 합니다. IAM·KMS·resource policy·VPC endpoint policy를 모두 막아도 backup copy 경로는 별개로 존재합니다.

</details>

---

4. "Security Hub CSPM은 대부분의 control에 AWS Config를 요구한다"는 사실이 갖는 의미는?
   - A) Config와 무관하게 모든 control finding이 정상적으로 생성된다
   - B) Config 활성화 여부가 Landing Zone, Identity Center, Security Hub CSPM 세 결정의 공통 전제가 된다
   - C) Config는 Security Hub CSPM과 전혀 관련이 없다
   - D) GuardDuty를 대체할 수 있다

<details>
<summary>정답 보기</summary>

**정답: B) Config 활성화 여부가 Landing Zone, Identity Center, Security Hub CSPM 세 결정의 공통 전제가 된다**

**설명:**
Config가 비활성화되어 있으면 대다수 Security Hub CSPM control finding이 생성되지 않습니다. Landing Zone의 baseline 의존 관계와 합쳐지면, Config 활성화 여부가 세 가지 중요한 결정을 동시에 제약하게 됩니다.

</details>
