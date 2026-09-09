# Landing Zone, OU와 조직 Control

> **마지막 업데이트**: 2026년 9월 9일

## 1. Control Tower Landing Zone 4.0의 baseline 의존 관계

멀티 어카운트 환경을 표준화할 때 가장 먼저 마주치는 도구는 AWS Control Tower입니다. Control Tower는 Account 생성과 조직 baseline·control을 관리형으로 제공하지만, **Landing Zone 4.0에서는 여러 baseline 사이에 활성화 순서를 강제하는 의존 관계**가 있습니다. 이 의존 관계를 모르고 OU와 IAM 설계를 먼저 확정하면 재작업이 발생합니다.

### 활성화 의존 체인

```
CentralConfigBaseline
  └─▶ CentralSecurityRolesBaseline
        ├─▶ IdentityCenterBaseline
        ├─▶ BackupAdminBaseline
        └─▶ BackupCentralVaultBaseline
```

`IdentityCenterBaseline`(Identity Center 연동)을 쓰려면 `CentralSecurityRolesBaseline`이 먼저 활성화되어 있어야 하고, 그것은 다시 `CentralConfigBaseline`(AWS Config)을 요구합니다. **비활성화는 반드시 역순**입니다 — 오른쪽 세 개(IdentityCenter/BackupAdmin/BackupCentralVault)를 모두 끈 뒤에야 SecurityRoles를, 그것을 끈 뒤에야 Config를 끌 수 있습니다.

> **왜 중요한가**: "Identity Center는 도입하지만 Config는 CNAPP 도구와 비교한 뒤 나중에 결정한다"처럼 두 결정을 독립적으로 미루는 설계는 성립하지 않습니다. **Config 활성화 여부가 Identity Center baseline 사용 가능 여부를 직접 결정**합니다.

Landing Zone 수준의 Config integration은 service integration Account에만 중앙 리소스를 배포합니다. 일반 member Account에 Config Recorder를 배포하려면 OU별로 Config baseline을 따로 활성화해야 하지만, **Landing Zone 수준에서 Config integration 자체를 비활성화하면 OU baseline도 켤 수 없습니다.** "Config는 플랫폼 팀 내부 파이프라인이 소유한다"는 방향을 택하려면, Landing Zone 수준 integration은 켠 채로 OU baseline만 선택적으로 적용하는 형태가 되어야 합니다.

### Security OU는 더 이상 자유롭게 설계할 수 없다

Control Tower 3.x에서는 지정 Security OU를 관리자가 직접 만들었지만, **4.0에서는 service integration Account들이 위치한 OU가 자동으로 Security OU로 지정**됩니다. 여기서 파생되는 제약이 세 가지 있습니다.

1. 이 OU에는 `AWSControlTowerBaseline`과 Config Baseline을 적용할 수 없습니다(`Not Applicable` 상태로 표시되며 정상 동작입니다). `BackupBaseline`은 적용 가능합니다.
2. Security OU 안에 service integration Account가 아닌 일반 Account를 두면 baseline 리소스를 받지 못합니다.
3. Control Tower는 Logging Account와 SecurityRoles Account용 Identity Center permission set만 자동으로 만들어줍니다. **Config Account와 Backup Account용 permission set은 직접 생성해야 합니다.**

또한 **일반 Account를 Security OU 계열로 옮기면 해당 OU의 enabled control이 drift 상태**가 됩니다. auto-enrollment 설정과 무관하게 발생하므로, 인수·이전한 Account를 검사하는 `Transitional` OU를 Security OU 계열 아래 두면 안 됩니다.

> **설계 권장**: `Security`(4.0의 service integration Account 전용, 일반 Account는 절대 두지 않음)와 `SecurityOperations`(보안팀이 실제로 쓰는 SIEM·CNAPP 연동 Account 등 일반 Account)를 **분리**하세요. 두 성격의 Account를 하나의 OU로 묶으면 나중에 반드시 재작업이 필요합니다.

### CentralizedLogging 비활성화 동작 변경

Control Tower 3.3 이하에서는 CentralizedLogging integration을 비활성화해도 Organization CloudTrail만 꺼지고 이미 배포된 리소스는 유지됐습니다. **4.0에서는 비활성화 시 logging Account의 Config Recorder, Delivery Channel, CloudTrail 관련 스택 인스턴스가 실제로 삭제됩니다.** 이후 Control Tower는 해당 Account를 더 이상 관리하지 않습니다.

단계적 마이그레이션 중 "일단 비활성화하고 나중에 다시 켠다"를 되돌리기 수단으로 쓸 수 없습니다. 되돌리기가 아니라 해체이기 때문입니다.

### Control Tower와 내부 파이프라인의 책임 분리

Control Tower가 활성화할 service integration과 OU baseline 조합에 따라, 두 가지 방향 중 하나를 먼저 결정해야 합니다.

| 방향 | 구성 | 장단점 |
|---|---|---|
| A. Control Tower 최대 활용 | Config/CloudTrail/SecurityRoles/Backup integration 모두 활성화 + OU별 Config baseline | Identity Center baseline 사용 가능. Config 비용은 조직 전체에 발생 |
| B. 최소 활용 | Config integration만 켜고 OU baseline은 선택 적용, Identity Center는 내부 파이프라인이 직접 관리 | Config 비용을 OU 단위로 통제할 수 있지만 Permission Set lifecycle을 직접 운영해야 함 |

## 2. Auto-enrollment

Landing Zone 3.1 이상에서는 Account를 등록된 OU로 이동하면 해당 OU의 baseline·control이 자동으로 적용되는 auto-enrollment를 쓸 수 있습니다. 다만 이 기능이 대신해주지 않는 것들이 있습니다.

- **기존 설정 충돌이나 실패 복구는 자동으로 해결되지 않습니다.** 사전 검사(Config·CloudTrail·SCP·IAM 충돌)는 별도로 수행해야 합니다.
- **등록 해제 시 baseline 리소스가 자동으로 삭제됩니다.** "폐기 예정 Account를 관리 대상에서 빼겠다"는 이유로 등록을 해제하면, 감사 증거로 남아 있던 baseline까지 함께 사라집니다. 폐기 예정 Account는 **등록된 상태를 유지하면서 Deny 중심 SCP로 변경만 막는 편**이 안전합니다.
- Enrollment는 최종적 일관성(eventual consistency) 모델이라 이동하는 Account 수에 따라 수 분에서 수 시간이 걸릴 수 있습니다.
- **auto-enrollment는 Service Catalog provisioned product를 생성·수정·종료하지 않습니다.** Account Factory로 만든 Account를 unenroll하면, 그 provisioned product가 management Account에 고아 리소스로 남습니다.

내부 파이프라인이 "Account 이동 → 자동 enrollment → workload bootstrap" 순서로 자동화를 구성한다면, 시작 조건은 "이동 이벤트"가 아니라 **"baseline 적용 완료 확인"**으로 잡아야 합니다.

## 3. OU와 조직 Control 정책 유형별 quota

Organizations가 지원하는 정책 유형은 서로 역할이 다르고, 기본 quota도 다릅니다.

| 정책 유형 | entity당 최대 연결 | 문서 최대 크기 | 조직 전체 최대 |
|---|---|---|---|
| SCP | 10 | 10,240자 | 10,000 |
| RCP | 5 (`RCPFullAWSAccess` 포함, 실사용 4) | 5,120자 | 2,000 |
| Declarative policy | 10 | 10,000자 | 1,000 |
| Tag policy | 10 | 10,000자 | 1,000 |
| Backup policy | 10 | 10,000자 | 1,000 |
| Security Hub policy | 10 | 10,000자 | 1,000 |

핵심은 **상속된 정책은 entity당 연결 개수 한도를 소비하지 않는다**는 점입니다. 이 사실은 SCP 배치 전략을 크게 좌우합니다.

### SCP 연결 위치 전략

| 전략 | 구성 | quota 관점 평가 |
|---|---|---|
| Root-heavy | 조직 전체 공통 SCP를 Root에 연결, OU가 상속 | 신규 Account가 즉시 상속받지만 예외를 만들기 어려움 |
| OU별 완성형 직접 연결 | 각 OU에 필요한 SCP 전체를 직접 연결, 상위 의존 최소화 | 상속을 쓰지 않으므로 OU 하나에서 10개 한도를 그대로 소비 — 한도 도달 시 정책을 병합해야 함 |
| **Layered bundle** | Root에는 예외 없는 최소 SCP만, 나머지는 OU별 버전 관리되는 정책 묶음 + 만료되는 예외 | 상속을 적극 활용해 OU별 direct-attach 한도를 절약 — **quota 관점에서 가장 확장성이 좋음** |

Organizations 자체에는 정책 버전 관리 기능이 없으므로, "버전이 있는 정책 묶음"을 운영하려면 정책 문서의 `Sid`에 버전 문자열을 직접 넣고, effective policy simulation 결과에서 어느 버전이 적용됐는지 판별할 수 있도록 별도로 구현해야 합니다.

몇 가지 추가로 확인된 제약:

- **모든 entity에 SCP가 하나라도 활성화되어 있다면, 마지막 SCP는 제거할 수 없습니다.** "예외 OU에는 통제를 전혀 두지 않는다"는 설계는 성립하지 않으므로, 예외 OU에도 최소 baseline SCP가 필요합니다.
- OU 중첩은 Root 아래 **5단계까지** 가능하고, 조직 전체 OU는 **2,000개**까지 만들 수 있습니다. 평면형이나 얕은 functional 혼합형 구조에는 이 상한이 문제가 되지 않습니다.
- **RCP는 실사용 4개뿐이고 문서 크기도 SCP의 절반(5,120자)**입니다. SCP처럼 계층적 bundle 전략을 쓸 여유가 없습니다. RCP는 "외부 principal의 S3/KMS 접근 전면 차단", "confused deputy 방어(`aws:SourceOrgID` 강제)"처럼 조직 전체에 적용할 소수의 절대 규칙에 한정하고, 세분화된 통제는 SCP와 개별 리소스 정책에 위임하는 것을 권장합니다. 특히 **개인정보를 다루는 저장소의 최후 방어선**으로 RCP를 예약해두는 전략이 유효합니다.
- Organizations에는 **Security Hub policy 유형**도 있습니다. Security Hub 설정을 조직 정책으로 중앙 배포하는 수단으로, SCP/RCP/declarative policy/Tag Policy와 함께 검토 대상입니다.

### 정책 유형별 역할 구분 (확인된 사실)

| 정책 유형 | 역할 |
|---|---|
| SCP | Principal의 최대 권한을 제한 (권한을 부여하지 않음) |
| RCP | 지원되는 resource가 허용할 수 있는 접근의 최대 범위를 제한 (권한을 직접 부여하지 않음) |
| Declarative policy | 지원 서비스의 조직 공통 baseline 설정을 유지 |
| Tag Policy | 태그 표준 준수를 검사·강제 |
| Control Tower control | OU 단위 예방(preventive)·사전검사(proactive)·탐지(detective) control |

SCP 평가 원칙에서 특히 유의할 점: Allow-list 방식을 쓰려면 Root부터 대상 Account까지 이어지는 **모든 계층에** 명시적 Allow가 있어야 하며, 어느 계층에서든 명시적 Deny가 있으면 하위의 Allow로 되돌릴 수 없습니다.

## 4. 허용·차단 방식: Allow-list vs Deny-list

| 방식 | 적합한 상황 | 운영 부담 |
|---|---|---|
| Allow-list 중심 | Sandbox, 규제 구역처럼 사용 가능한 서비스를 사전에 제한할 수 있는 범위 | 신규 서비스·API를 쓰려면 매번 명시적으로 허용해야 함 |
| **Deny-list 중심** | 일반 Workload OU (기본값) | 새 서비스·API의 위험을 지속적으로 탐지하고 Deny catalog를 갱신하는 절차가 필요 |

신규 서비스의 VPC endpoint 지원 여부처럼 계속 바뀌는 정보는, 사람이 주기적으로 조사하는 대신 `aws ec2 describe-vpc-endpoint-services`를 정기적으로 덤프해서 자동으로 대조하는 방식을 권장합니다.

## 5. OU 설계 옵션

| 옵션 | 구성 | 장점 | 단점 |
|---|---|---|---|
| 깊은 계층형 | Root 아래 여러 단계로 분류를 중첩, 상위 control을 하위가 상속 | 분류·공통 control을 hierarchy로 표현하기 쉬움 | 상위 Deny의 영향 범위가 넓음. 실제 상한은 5단계 |
| Root 하위 평면형 | 대부분의 OU를 Root 직속에 두고 control을 직접 연결 | OU별 영향 범위를 설명하기 쉬움 | 공통 정책 중복·누락 위험. 상속 없이 entity당 10개 한도를 소비 |
| **얕은 functional 혼합형** | 쉽게 변하지 않는 기능 OU(`Security`, `Infrastructure`)와 lifecycle/절차 OU(`Workloads/Production`, `Workloads/Non-production`, `Sandbox`, `PolicyStaging`, `Transitional`, `Suspended`)를 얕게 조합 | 조직도 변화의 영향을 줄이면서 운영 상태를 표현 | Functional 분류·lifecycle·상속·정책 묶음을 함께 검증해야 함. 앞서 설명한 Security OU 4.0 제약 때문에 `Security`와 `SecurityOperations`를 분리해야 함 |

`Transitional`은 인수·이전한 Account를 표준 OU에 넣기 전 검사하는 임시 위치이고, `Suspended`는 폐기 예정 Account의 일반 변경을 막는 위치입니다. 둘 다 **등록된 상태를 유지**해야 합니다(2절 참고). 침해 의심 Account를 위한 `Quarantine`은 조사 권한·증거 보존·복구 절차가 `Suspended`와 실제로 다를 때만 별도로 둡니다.

상시 예외를 두는 `Production-Exception` OU와, 만료 기한이 있는 예외 정책은 구분하는 것이 좋습니다. 특정 API나 정책을 일정 기간만 허용해도 되면 표준 Production OU 안에서 승인 범위와 만료일이 있는 예외로 처리하고, Account 전체에 장기간 다른 control이 필요하거나 표준 control과 기술적으로 양립할 수 없을 때만 별도 OU를 만듭니다.

## 다음

Landing Zone과 OU 구조가 정해졌다면, 그 위에서 Account를 어떤 기준으로 나누고 사람·워크로드에게 어떤 IAM 경로를 줄지가 다음 결정입니다 → [Account 구성과 IAM 경계](./02-account-and-iam.md)

## 참고 자료

- [Organizations quotas](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_reference_limits.html)
- [Control Tower landing zone 4.0 key changes](https://docs.aws.amazon.com/controltower/latest/userguide/key-changes-lz-v4.html)
- [Control Tower AWS Config updates (4.0)](https://docs.aws.amazon.com/controltower/latest/userguide/config-updates-v4.html)
- [Control Tower account auto-enrollment](https://docs.aws.amazon.com/controltower/latest/userguide/account-auto-enrollment.html)
- [Baseline 유형](https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html)
- [기존 Account 편입](https://docs.aws.amazon.com/controltower/latest/userguide/enroll-account.html)
- [SCP 평가](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_evaluation.html)
- [RCP](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)
- [Declarative policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_declarative_policies.html)
- [Tag Policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)
- [Control Tower control 목록](https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html)
- [AWS multi-account design principles](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/design-principles-for-your-multi-account-strategy.html)
- [AWS recommended OUs and Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/recommended-ous-and-accounts.html)
