# Data·Security 경계

> **마지막 업데이트**: 2026년 9월 13일

## 1. Data ownership 옵션

| 옵션 | 구성 |
|---|---|
| 중앙 DB 운영 Account | 모든 데이터베이스를 플랫폼 팀이 소유한 Account에서 운영 |
| Workload-owned data | 각 워크로드 팀이 자신의 데이터베이스를 소유·운영 |
| **Hybrid** | 운영 DB는 워크로드별로 선택, data lake·warehouse·streaming backbone 같은 공통 자산은 별도 Data Platform이 소유 |

Hybrid가 대부분의 조직에서 현실적인 시작점입니다. 다만 이 선택보다 실제 아키텍처를 더 크게 좌우하는 것은, 다음 절에서 다루는 **cross-account 백업·복구의 기술적 제약**입니다.

<span id="_2-cross-account-데이터-복구-제약-—-실제로-선택을-바꾸는-조건"></span>

## 2. Cross-account 복구는 리소스와 vault 유형별로 검증한다

데이터 소유권과 복구 위치를 함께 정하되, 특정 snapshot API 제한을 모든 복구 경로의 불가능으로 해석하지 않습니다.

<span id="rds-스냅샷"></span>

### RDS snapshot 공유

- RDS DB instance의 automated snapshot은 manual snapshot으로 복사한 후 공유합니다. RDS 공유 절차에서는 AWS Backup이 생성한 snapshot에도 같은 설명이 적용됩니다. 이것을 모든 AWS Backup 복구 방식의 단계로 확대하지 않습니다.
- 암호화된 shared DB instance snapshot은 recipient가 복사한 뒤 restore합니다. AWS 관리형 기본 KMS key로 암호화된 snapshot은 그대로 공유할 수 없으므로 승인된 customer-managed key로 복사하는 경로를 검토합니다.
- Manual snapshot의 공유 대상은 최대20Account입니다. Oracle/SQL Server의 permanent/persistent option에 추가 제약이 있습니다.
- **Multi-AZ DB cluster snapshot은 이 RDS snapshot-sharing 경로에서 공유할 수 없습니다.** 이것이 논리 백업·검증된 데이터 복제 등 모든 cross-account 복구 경로가 없다는 뜻은 아니며, workload-owned DB를 강제하지도 않습니다. engine·snapshot 종류·리전별 지원 범위와 대체 복구의 RTO/RPO를 확인합니다.

<span id="aws-backup-cross-account-copy"></span>

### AWS Backup의 일반 vault: copy 후 restore

- 같은 Organization의 source/destination과 management Account의 cross-account backup 활성화가 필요합니다.
- Source role에는 `backup:CopyFromBackupVault`와 `backup:CopyIntoBackupVault`, destination vault에는 후자를 허용하는 resource policy가 필요합니다. 서비스별 backup/copy 권한과 KMS 사용 권한도 충족해야 합니다.
- 암호화는 resource 유형에 따라 다릅니다. AWS Backup이 완전 관리하는 resource의 destination은 `aws/backup` 또는 customer-managed key를 지원하고, 다른 유형은 customer-managed key가 필요합니다. 공식 copy 페이지의 default-vault 금지 안내도 함께 확인하고, 이 가이드에서는 **전용 destination vault와 명시적 key/policy**를 설계 기준으로 사용합니다. 이름만으로 암호화·copy 적합성을 판정하지 않습니다.
- 일반 vault의 cross-account 복구는 copy 후 destination에서 restore하는 흐름입니다. 해당 resource의 service-linked role·restore role·subnet/SG 등이 준비되어 있어야 합니다.
- Cold tier의 cross-account copy는 지원되지 않습니다. resource와 Region의 기능 지원표를 확인합니다.

### Logically air-gapped vault: 공유받은 Account에서 직접 restore

논리적 에어갭 vault는 AWS RAM으로 개별 Account와 공유할 수 있으며 **다른 Organization의 Account도 가능**합니다. 공유받은 Account는 지원 resource의 recovery point를 직접 restore할 수 있어 recipient vault로 먼저 복사하는 단계가 필요하지 않습니다. 따라서 “AWS Backup은 cross-account 직접 restore를 전혀 지원하지 않는다”는 표현은 부정확합니다.

일반 vault의 copy 허용 policy와 에어갭 vault의 RAM share를 구분하세요. resource/Region 지원, restore IAM, 암호화 key 유형, sharing 승인, source Account 접근 불능 시 복구 절차를 각각 확인합니다. 이 경로가 모든 DB 유형을 지원한다고 가정하지 않습니다.

<span id="정리"></span>

### 승인되지 않은 copy/share 차단

Destination이 Organization을 떠나더라도 기존 copy는 보유할 수 있습니다. source의 `backup:CopyTargets`/`backup:CopyTargetOrgPaths` 조건, destination vault policy, KMS, RAM share 권한과 조직 이탈 절차를 함께 검토합니다. cross-account 기능 활성화는 모든 사용자에게 copy 권한을 부여하지 않으며 IAM·vault·KMS의 Deny를 우회하지 않습니다.

RTO에는 사고 후 실제 수행하는 copy·restore·애플리케이션 검증 시간을 포함합니다. 사전 copy가 있다면 복사 주기는 RPO에 영향을 줍니다. [의사결정 프레임워크](./06-decision-framework-and-poc.md)에서 resource 유형별 복구 시험과 목표를 기록하세요.

## 3. 개인정보 저장 계층 분리

VPC에 직접 배치되는 저장소(RDS 등)는 일반 서빙 계층과 별도 VPC에 두는 것이 목적에 맞습니다. 목적은 route·inspection·직접 접근 주체·incident containment 범위를 분리하는 것입니다. 다만 **별도 VPC만으로는 충분하지 않습니다** — IAM, SG, KMS key policy, logging, 승인된 접근 경로를 함께 적용해야 합니다.

> **Shared VPC의 감사 경로**: participant는 owner의 NAT Gateway를 describe할 수 없지만 owner가 제공하는 route/NAT inventory·Config·Flow Logs와 위임된 읽기 권한으로 증거를 구성할 수 있습니다. 전용 VPC는 소유권을 단순화하는 선택지이며 Shared VPC가 본질적으로 감사 불가능하다는 뜻은 아닙니다.

S3는 VPC에 배치되는 리소스가 아닙니다. bucket/Account ownership, VPC endpoint + endpoint policy, bucket/access point policy, KMS key policy, 조직 control로 승인된 경로만 허용하는 방식으로 통제합니다.

### 개발/QA의 프로덕션 원본 데이터 직접 접근 차단

"직접 접근을 차단한다"는 목표를 API 수준의 경로로 구체화하면 다음과 같은 coverage matrix가 됩니다.

| 경로 | 통제 수단 |
|---|---|
| AWS Backup cross-account copy | `backup:CopyTargets`/`CopyTargetOrgPaths` SCP 조건, destination vault access policy |
| RDS 수동 스냅샷 공유 | `rds:ModifyDBSnapshotAttribute`를 승인된 자동화로 제한; 대상 Account는 배포 검증에서 검사 |
| RDS 스냅샷 public 공유 | 공유 변경 API를 제한하고 자동화에서 `restore=all` 거부; 탐지·복구 병행 |
| EBS 스냅샷 공유 / EC2 Allowed AMIs | `ec2:ModifySnapshotAttribute` 제한, 소스 Account allowlist |
| S3 Batch Replication / cross-account replication | bucket policy, replication role 제한, RCP |
| DMS/Glue 경유 이동 | 해당 서비스의 network·IAM 경로 |
| CDC stream (MSK/Kinesis/DMS) | resource policy + cross-account consumer 제한 |
| Athena/Redshift cross-account query, Lake Formation | Lake Formation cross-account grant 감사 |

KMS key 유형과 복구 권한은 선택한 copy/restore 경로 및 조직 요구로 정합니다. 모든 개인정보 저장소에 customer-managed key가 AWS 공통 의무인 것은 아닙니다. source Account를 사용할 수 없는 상황에서도 작동하도록 destination key·사전 copy·허용된 key policy/grant·에어갭 vault와 공유 절차를 시험합니다.

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

- Security Hub CSPM의 표준·control·ASFF finding 기능과 별도 Security Hub 기능을 구분해 비교합니다. 이름만으로 기능 범위나 Config 의존성이 같다고 가정하지 않습니다.
- Security Hub CSPM의 대부분 control은 AWS Config recording이 필요합니다. 이는 Control Tower 4.0의 관리형 baseline 의존성과 함께 검토할 사항이지만 IAM Identity Center 서비스 자체의 Config 필수 조건은 아닙니다.
- **Security Hub CSPM은 활성화 이전에 생성된 finding을 소급 수집하지 않으며, 활성화한 리전의 finding만 처리합니다.** 공식 가이드의 CIS AWS Foundations Benchmark 전체 보안 검사 coverage를 위해서는 지원되는 모든 리전에서 활성화해야 합니다. GuardDuty도 리전별로 활성화합니다.
- GuardDuty·Security Hub는 서울 리전에서 사용할 수 있지만, 일부 finding type·control의 지원 범위는 리전마다 다릅니다. 비교는 서울 리전의 실제 coverage를 기준으로 해야 합니다.

## 6. Shared subnet에서 리소스를 생성할 수 있는 서비스 목록

아래는 공식 Shared VPC 지원 목록의 요약입니다. 이 목록은 누락 가능성을 명시하므로 이름이 없으면 해당 서비스 문서를 추가 확인합니다. 명시적 미지원과 문서 미기재를 구분합니다.

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

Amazon MQ의 RabbitMQ처럼 공식 목록에 명시적으로 제외된 engine은 별도 배치를 검토합니다. CUJ 전체를 Shared VPC에서 제외하기 전에 해당 dependency만 별도 VPC/API 경로로 연결할 수 있는지도 평가합니다.

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
- [Logically air-gapped vault sharing and restore](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)
