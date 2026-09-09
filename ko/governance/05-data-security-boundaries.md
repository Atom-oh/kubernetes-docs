# Data·Security 경계

> **마지막 업데이트**: 2026년 9월 9일

## 1. Data ownership 옵션

| 옵션 | 구성 |
|---|---|
| 중앙 DB 운영 Account | 모든 데이터베이스를 플랫폼 팀이 소유한 Account에서 운영 |
| Workload-owned data | 각 워크로드 팀이 자신의 데이터베이스를 소유·운영 |
| **Hybrid** | 운영 DB는 워크로드별로 선택, data lake·warehouse·streaming backbone 같은 공통 자산은 별도 Data Platform이 소유 |

Hybrid가 대부분의 조직에서 현실적인 시작점입니다. 다만 이 선택보다 실제 아키텍처를 더 크게 좌우하는 것은, 다음 절에서 다루는 **cross-account 백업·복구의 기술적 제약**입니다.

## 2. Cross-account 데이터 복구 제약 — 실제로 선택을 바꾸는 조건

"데이터는 누가 소유하는가"를 정하기 전에, cross-account로 데이터를 옮기거나 복구하는 경로 자체에 어떤 제약이 있는지 확인해야 합니다. 이 제약들은 중앙 운영과 워크로드 소유 어느 쪽을 택해도 동일하게 적용되므로, **양쪽 다 반드시 구현해야 하는 공통 guardrail**로 이해하는 것이 정확합니다.

### RDS 스냅샷

- **RDS 자동 백업은 공유할 수 없습니다.** cross-account로 넘기려면 automated snapshot → manual snapshot으로 복사 → 그 복사본을 공유하는 단계가 필수입니다(AWS Backup 리소스도 동일한 제약을 받습니다). 어느 방향을 택하든 "복사" 단계가 필요하고, 이 단계에는 시간·스토리지 비용·자동화 소유자가 필요합니다.
- **암호화된 공유 스냅샷은 직접 restore할 수 없습니다.** 공유받은 Account가 자기 Account로 복사한 뒤, 그 복사본에서 restore해야 합니다.
  - **AWS 기본 KMS key로 암호화한 스냅샷은 공유 자체가 불가능합니다.** 개인정보를 다루는 저장소는 처음부터 customer-managed key(CMK)가 필수입니다 — 선택이 아니라 cross-account 복구 가능성의 전제조건입니다.
  - 수동 스냅샷은 최대 20개 Account에만 공유할 수 있습니다.
  - **Multi-AZ DB cluster의 스냅샷은 공유할 수 없습니다.** 이 유형을 쓰면 그 DB에는 cross-account 복구 경로가 아예 존재하지 않습니다. 이 경우 DB와 복구 책임을 같은 Account에 두는 workload-owned 방식이 사실상 강제됩니다.
  - Oracle/SQL Server의 permanent/persistent 옵션(TDE 등)을 사용하는 인스턴스는 공유에 추가 제약이 있습니다.

### AWS Backup cross-account copy

다음 전제 조건이 모두 충족되어야 합니다.

- 소스·대상 Account가 동일 Organization에 속해야 합니다.
- Management Account에서 명시적으로 활성화해야 합니다(`UpdateGlobalSettings`).
- **대상 vault는 default vault가 될 수 없습니다**(default vault의 key는 공유할 수 없습니다).
- 대상 vault에 `backup:CopyIntoBackupVault`를 허용하는 resource policy가 필요하고, 소스 role에는 `backup:CopyFromBackupVault`와 `backup:CopyIntoBackupVault`가 모두 필요합니다.
- AWS Backup이 완전 관리하지 않는 리소스 유형은 CMK가 필수입니다(AWS managed key는 cross-account 공유가 불가능합니다).
- **AWS Backup은 계정 간 직접 restore를 지원하지 않습니다.** 이 또한 "복사 후 복사본에서 restore"의 2단계 구조입니다. 대상 Account에 해당 리소스 유형의 service-linked role이 없다면(한 번도 그 서비스를 써본 적 없는 Account) 미리 만들어둬야 합니다.
- Cold tier로 전환된 백업은 cross-account copy를 지원하지 않습니다.

몇 가지는 보안 설계에 직접적인 영향을 줍니다.

- **대상 Account가 나중에 Organization을 떠나도 이미 복사된 백업은 그대로 보유됩니다.** 이건 개인정보 유출 경로가 될 수 있으므로, `organizations:LeaveOrganization`을 SCP로 Deny하는 것을 권장합니다.
- **cross-account backup을 활성화하면, 조직의 모든 member Account 사용자가 자기 Account를 destination으로 설정할 수 있습니다.** 개인정보 백업이 미승인 Account로 복사될 위험이 있으므로, `backup:CopyFromBackupVault` 권한에 `backup:CopyTargets`/`backup:CopyTargetOrgPaths` 조건을 걸어 승인된 vault·OU로만 복사되도록 강제해야 합니다. IAM·KMS·resource policy·VPC endpoint policy를 모두 막아도 backup copy 경로는 별개로 존재하므로, 별도로 확인해야 합니다.

### 정리

위 제약들은 중앙 운영과 워크로드 소유 중 한쪽을 유리하게 만들지 않습니다(우열이 갈리지 않습니다). 단, **"Multi-AZ DB cluster 스냅샷 공유 불가"는 유일하게 선택 자체를 바꾸는 조건**입니다. 정당한 복구 경로(production → 격리된 복구 Account)도 개발/QA의 접근 차단과 동일한 제약을 받으므로, **RTO 계산에는 스냅샷 복사 시간을 반드시 포함**해야 합니다(TB급 데이터베이스에서는 무시할 수 없는 시간입니다). **RTO/RPO 목표가 정의되어 있지 않으면 이 판정 자체가 불가능**합니다 — 자세한 내용은 [의사결정 프레임워크](./06-decision-framework-and-poc.md)를 참고하세요.

## 3. 개인정보 저장 계층 분리

VPC에 직접 배치되는 저장소(RDS 등)는 일반 서빙 계층과 별도 VPC에 두는 것이 목적에 맞습니다. 목적은 route·inspection·직접 접근 주체·incident containment 범위를 분리하는 것입니다. 다만 **별도 VPC만으로는 충분하지 않습니다** — IAM, SG, KMS key policy, logging, 승인된 접근 경로를 함께 적용해야 합니다.

> **Shared VPC를 개인정보 계층에 쓸 때의 함정**: participant는 NAT Gateway를 describe조차 할 수 없습니다([04장](./04-shared-vpc-and-connectivity.md) 참고). 개인정보 계층이 participant Account이고 VPC가 중앙 소유라면, 데이터 소유팀이 자기 데이터의 egress 경로를 스스로 검증할 수 없습니다 — 규제 대응 시 "이 데이터가 어디로 나갈 수 있는가"를 증명하기 어렵습니다. 이 근거는 "격리 강도"가 아니라 **"소유팀의 egress 경로 증명 가능성"**으로 프레이밍하는 것이 더 정확합니다. 그래서 개인정보 계층은 전용 VPC(워크로드 소유)가 감사 가능성 측면에서 유리합니다.

S3는 VPC에 배치되는 리소스가 아닙니다. bucket/Account ownership, VPC endpoint + endpoint policy, bucket/access point policy, KMS key policy, 조직 control로 승인된 경로만 허용하는 방식으로 통제합니다.

### 개발/QA의 프로덕션 원본 데이터 직접 접근 차단

"직접 접근을 차단한다"는 목표를 API 수준의 경로로 구체화하면 다음과 같은 coverage matrix가 됩니다.

| 경로 | 통제 수단 |
|---|---|
| AWS Backup cross-account copy | `backup:CopyTargets`/`CopyTargetOrgPaths` SCP 조건, destination vault access policy |
| RDS 수동 스냅샷 공유 | `rds:ModifyDBSnapshotAttribute` SCP Deny 또는 대상 Account 제한 |
| RDS 스냅샷 public 공유 | SCP로 `restore` 속성에 `all` 지정을 차단 |
| EBS 스냅샷 공유 / EC2 Allowed AMIs | `ec2:ModifySnapshotAttribute` 제한, 소스 Account allowlist |
| S3 Batch Replication / cross-account replication | bucket policy, replication role 제한, RCP |
| DMS/Glue 경유 이동 | 해당 서비스의 network·IAM 경로 |
| CDC stream (MSK/Kinesis/DMS) | resource policy + cross-account consumer 제한 |
| Athena/Redshift cross-account query, Lake Formation | Lake Formation cross-account grant 감사 |

KMS key 관점에서는 개인정보 저장소가 워크로드 소유라도 **CMK를 강제**해야 하고, **복구용 Account를 key policy의 principal에 사전에 포함**해야 합니다. 사고가 발생한 뒤에 key policy를 바꾸려면 key owner Account에 접근해야 하는데, 그 Account가 침해 대상이라면 복구 자체가 막힙니다. Backup vault를 destination으로 지정할 수 있는 Account도 SCP로 제한해야 합니다.

## 4. Secrets Manager / KMS cross-account

Secret resource policy와 호출자의 identity policy가 **모두** 필요합니다. Cross-account secret에는 customer-managed KMS key가 필요하며, 그 key 역시 owner의 key policy와 caller의 IAM policy가 모두 필요합니다. 즉 중앙집중형 secret·key 관리는 policy와 rotation뿐 아니라, **양쪽 Account의 permission과 복구 책임을 함께 운영**해야 성립합니다.

## 5. AWS-native security telemetry vs 기존 CNAPP

기존 CNAPP(Cloud-Native Application Protection Platform) 도구가 있는 조직이 AWS-native 기능을 도입할 때는, "제품을 대체한다"는 전제가 아니라 **보안 목적별로 현재 coverage와 AWS 고유 기능을 비교하고, 확인된 공백만 보완하는 접근**이 안전합니다. 목적 분류는 다음과 같이 나눌 수 있습니다.

- 조직 예방 control
- Configuration posture
- Data security posture
- Workload runtime protection
- Threat detection
- Finding workflow
- Workload 맥락 탐지

몇 가지 확인된 사실:

- **"AWS Security Hub"는 "Security Hub CSPM"으로 개칭되었습니다.** CSPM 기능(표준, control, finding aggregation, automation rule)과 별개의 Security Hub 기능이 구분되어 있으므로, 비교표를 작성할 때 어느 쪽을 지칭하는지 명확히 하지 않으면 CNAPP와의 중복 판정이 틀어집니다.
- **Security Hub CSPM은 대부분의 control에 AWS Config를 요구합니다.** Config가 비활성화되어 있으면 대다수 control finding이 생성되지 않습니다. [Landing Zone baseline 의존 관계](./01-landing-zone-and-ou.md)와 합쳐지면, **"Config를 활성화할 것인가"가 Landing Zone / Identity Center / Security Hub CSPM 세 결정의 공통 전제**가 됩니다.
- **Security Hub CSPM은 활성화 이전에 생성된 finding을 소급 수집하지 않으며, 활성화한 리전의 finding만 처리합니다.** CIS 벤치마크 완전 준수를 위해서는 지원되는 모든 리전에서 활성화해야 합니다. GuardDuty도 리전별로 활성화합니다.
- GuardDuty·Security Hub는 서울 리전에서 사용할 수 있지만, 일부 finding type·control의 지원 범위는 리전마다 다릅니다. 비교는 서울 리전의 실제 coverage를 기준으로 해야 합니다.

## 6. Shared subnet에서 리소스를 생성할 수 있는 서비스 목록

Shared VPC subnet에 리소스를 만들 수 있는 서비스는 AWS가 명시적으로 정해두고 있으며, 이 목록 밖의 서비스를 쓰는 워크로드는 Shared VPC 전략에서 예외로 다뤄야 합니다.

| 지원 서비스 | 비고 |
|---|---|
| Amazon RDS, Aurora | 주 대상 |
| ElastiCache (Redis OSS) | |
| Redshift, EMR, Glue | 공통 Data Platform 대상 |
| OpenSearch Service, MSK | |
| EC2, ECS, EKS, Lambda, EFS | |
| ALB/NLB/GWLB | |
| PrivateLink (interface endpoint) | |
| VPC Lattice, TGW, VPC Peering, Traffic Mirroring | |
| Route 53 (PHZ cross-account association) | |
| DMS, Verified Access, SageMaker Unified Studio | |
| **Amazon MQ** | **Apache ActiveMQ만 지원. RabbitMQ는 미지원** |

AWS 스스로도 "이 목록에 누락이 있을 수 있다"고 명시하고 있습니다. 실제 사용 서비스 인벤토리를 이 목록과 대조해서, CUJ 경로에 미지원 서비스가 하나라도 있다면 그 워크로드는 Shared VPC locality 대상에서 제외하는 판정 규칙을 두는 것을 권장합니다. 특히 **RabbitMQ 사용 여부는 별도로 확인**해야 합니다.

## 다음

경계·계정·IAM·네트워크·데이터 결정을 모두 재현 가능한 형태로 만드는 방법은 → [의사결정 프레임워크와 POC 설계](./06-decision-framework-and-poc.md)

## 참고 자료

- [RDS 스냅샷 공유](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html)
- [RDS 암호화 스냅샷 공유](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/share-encrypted-snapshot.html)
- [AWS Backup cross-account copy](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)
- [Secrets Manager cross-account](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html)
- [KMS external account key policy](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)
- [Security Hub CSPM 소개](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [Security Hub CSPM 리전별 control](https://docs.aws.amazon.com/securityhub/latest/userguide/regions-controls.html)
- [GuardDuty 리전별 차이](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_regions.html)
- [AWS SRA Security Tooling](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html)
- [Shared subnet 지원 서비스](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
