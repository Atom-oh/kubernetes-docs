# Amazon ECR (Elastic Container Registry)

> **마지막 업데이트**: 2026년 9월 11일

## 개요

Amazon Elastic Container Registry(ECR)는 AWS에서 제공하는 완전관리형 컨테이너 레지스트리 서비스입니다. Docker 이미지, OCI 이미지 및 OCI 호환 아티팩트를 저장, 관리, 배포할 수 있으며, AWS IAM과 통합되어 세밀한 접근 제어가 가능합니다.

이후 CLI/CDK/IAM/lifecycle 예제는 별도 표시가 없으면 ECR Private 기준입니다. 서로 다른 구성 대안이므로 같은 이름의 리포지터리를 중복 생성하지 말고 사용할 방식을 선택합니다. 조회·스캔 예제에는 해당 리포지터리와 이미지 태그가 먼저 존재해야 합니다. AWS 자격 증명을 구성하고 예시 계정 ID·리소스 이름을 실제 값으로 바꿉니다.

```bash
export AWS_REGION=ap-northeast-2
export AWS_DEFAULT_REGION="$AWS_REGION"
```

### 아키텍처

![AWS 계정 안에서 Amazon ECR Private가 IAM 인증, 수명주기 정책, 암호화, 스캔 기능으로 비공개 리포지토리를 관리하고, ECR Public이 별도로 공개 리포지토리를 제공하는 구조를 보여준다.](../.gitbook/assets/ko-container-registry-02-amazon-ecr-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-02-amazon-ecr-0.html)

### Private vs Public ECR

| 특성 | ECR Private | ECR Public |
|------|-------------|------------|
| **URL 형식** | `<account>.dkr.ecr.<region>.amazonaws.com/<repo>` | `public.ecr.aws/<alias>/<repo>` |
| **인증** | IAM 기반 필수 | 선택적 (익명 pull 가능) |
| **리전** | 리전별 서비스·엔드포인트 확인 | 관리 API는 us-east-1/us-west-2, 이미지 URL은 글로벌 배포 |
| **비용** | 스토리지 + 전송 등 | 저장·익명/인증 전송의 무료 허용량을 각각 확인 |
| **사용 사례** | 프라이빗 워크로드 | 오픈소스, 공개 배포 |

### 가격 모델

| 항목 | 비용 | 비고 |
|------|------|------|
| **스토리지** | 리전·스토리지 클래스별 요금 | 공식 예제의 standard 저장 단가는 $0.10/GB-month |
| **같은 리전 AWS 컴퓨트 전송** | 지원 경로는 ECR 전송 요금 없음 | VPC endpoint/NAT 등 네트워크 서비스 비용은 별도 |
| **리전 간/인터넷 전송** | 출발·도착 리전과 전송량별 | 고정 $0.01-0.02로 가정하지 않음 |
| **부가 기능** | Inspector, Signer, KMS 등의 해당 요금 | 설정에 따라 달라짐 |

**산식 예시 (실제 청구 견적이 아님):**
```
저장 이미지: 50GB = $5.00
리전 내 전송: 100GB = $0.00
인터넷 전송: 목적지·계정 무료 허용량·요율에 따라 별도 산정
---
전체 비용: 저장 + 해당 전송/네트워크/부가 기능 비용
```

[공식 요금](https://aws.amazon.com/ecr/pricing/)과 [Public API 엔드포인트](https://docs.aws.amazon.com/general/latest/gr/ecr-public.html)를 확인합니다. 앞의 아키텍처 그림에 표시된 us-east-1은 Public API 사용 예시이며 유일한 관리 엔드포인트라는 뜻은 아닙니다.

---

## 리포지토리 생성 및 구성

### AWS CLI로 리포지토리 생성

```bash
# 기본 리포지토리 생성
aws ecr create-repository \
  --repository-name myapp \
  --region ap-northeast-2

# 별도 리포지토리를 생성하는 대안 예제; KMS 키가 먼저 존재해야 함
aws ecr create-repository \
  --repository-name myapp-secure \
  --region ap-northeast-2 \
  --image-tag-mutability IMMUTABLE \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS,kmsKey=arn:aws:kms:ap-northeast-2:123456789012:key/12345678-1234-1234-1234-123456789012 \
  --tags Key=Environment,Value=Production Key=Team,Value=Platform
```

**주요 옵션:**

| 옵션 | 설명 | 권장 값 |
|------|------|--------|
| `--image-tag-mutability` | 태그 변경 가능 여부 | `IMMUTABLE` (프로덕션) |
| `--image-scanning-configuration` | 기존 Basic 스캔 호환 옵션 | 새 구성은 아래 registry-level scanning 설정 우선 |
| `--encryption-configuration` | 암호화 설정 | `KMS` (민감 데이터) |

### AWS CDK로 리포지토리 생성

```typescript
// lib/ecr-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';

export class EcrStack extends cdk.Stack {
  public readonly repository: ecr.Repository;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 프로덕션 리포지토리
    this.repository = new ecr.Repository(this, 'MyAppRepository', {
      repositoryName: 'myapp-prod',
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.IMMUTABLE,
      encryption: ecr.RepositoryEncryption.AES_256,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          description: 'Keep last 100 production images',
          maxImageCount: 100,
          tagStatus: ecr.TagStatus.TAGGED,
          tagPrefixList: ['v'],
        },
        {
          description: 'Expire untagged images after 3 days',
          maxImageAge: cdk.Duration.days(3),
          tagStatus: ecr.TagStatus.UNTAGGED,
        },
      ],
    });

    // 리포지토리 URL 출력
    new cdk.CfnOutput(this, 'RepositoryUri', {
      value: this.repository.repositoryUri,
    });
  }
}
```

### Immutable Tags 설정

Immutable tags는 한번 푸시된 태그를 덮어쓸 수 없게 합니다:

```bash
# 기존 리포지토리의 태그 불변성 변경
aws ecr put-image-tag-mutability \
  --repository-name myapp \
  --image-tag-mutability IMMUTABLE

# 확인
aws ecr describe-repositories \
  --repository-names myapp \
  --query 'repositories[].imageTagMutability'
```

**Immutable Tags의 장점:**
- 기존 태그의 대상 digest 변경 방지
- 감사 추적 용이
- 롤백 시 일관성 보장

**주의사항:**
- `latest`도 최초 생성은 가능하지만 기존 태그를 다른 digest로 덮어쓸 수 없습니다.
- `IMMUTABLE_WITH_EXCLUSION`은 지정한 태그만 변경 가능하게 하는 별도 옵션입니다.
- 불변성은 삭제 방지가 아닙니다. 삭제 후 재생성, 설정 변경과 삭제 권한도 관리해야 합니다.
- CI/CD 파이프라인 조정 필요

### 암호화 설정

**AES-256 (기본):**
```bash
# Amazon S3 관리형 키(SSE-S3) 사용
aws ecr create-repository \
  --repository-name myapp \
  --encryption-configuration encryptionType=AES256
```

**KMS (AWS 관리형 또는 고객 관리형 KMS 키):**
```bash
# 고객 관리형 KMS 키 사용
aws ecr create-repository \
  --repository-name myapp-sensitive \
  --encryption-configuration \
    encryptionType=KMS,kmsKey=arn:aws:kms:ap-northeast-2:123456789012:key/mrk-xxxxx
```

`KMS`만 지정하면 ECR의 AWS 관리형 KMS 키를 사용할 수 있고, `kmsKey`를 지정하면 해당 키를 사용합니다. 키는 리포지터리와 같은 리전에 있어야 합니다. 기존 리포지터리의 암호화 설정은 변경할 수 없으므로 새 리포지터리로 이동하는 계획과 `cdk diff` 검토가 필요합니다.

**KMS 사용 사례:**
- 규제 준수 (키 로테이션 감사)
- 키 사용 감사와 수명주기 제어
- 세분화된 접근 제어

### 취약점 스캐닝

**Basic Scanning (기본):**
```bash
# 기존 registry 설정을 먼저 확인하고 다른 규칙과 합쳐서 적용
aws ecr get-registry-scanning-configuration
# 독립 실습 registry의 구성 예제 (put은 전체 설정을 대체함)
aws ecr put-registry-scanning-configuration --scan-type BASIC \
  --rules '[{"repositoryFilters":[{"filter":"myapp*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}]'

# 최근 24시간 내 스캔되지 않은 기존 이미지의 수동 스캐닝
aws ecr start-image-scan \
  --repository-name myapp \
  --image-id imageTag=v1.0.0

# 스캐닝 결과 조회
aws ecr wait image-scan-complete \
  --repository-name myapp --image-id imageTag=v1.0.0
aws ecr describe-image-scan-findings \
  --repository-name myapp \
  --image-id imageTag=v1.0.0
```

**Enhanced Scanning (Amazon Inspector):**
```bash
# Enhanced Scanning 활성화 (계정 레벨)
aws ecr put-registry-scanning-configuration \
  --scan-type ENHANCED \
  --rules '[
    {
      "repositoryFilters": [{"filter": "*", "filterType": "WILDCARD"}],
      "scanFrequency": "CONTINUOUS_SCAN"
    }
  ]'
```

| 특성 | Basic Scanning | Enhanced Scanning |
|------|----------------|-------------------|
| **엔진** | AWS native basic scanning | Amazon Inspector |
| **커버리지** | OS 패키지 | OS + 언어 패키지 |
| **주기** | 푸시 시 / 수동 | 지속적 + 새 CVE 발견 시 |
| **비용** | 무료 | Inspector 요금 |

Basic 스캔은 이미지별 24시간 제한이 있고, 지원 종료 OS는 최신 취약점 탐지를 보장하지 않습니다. Enhanced 스캔도 설정한 재스캔 범위·기간을 따릅니다. 위 registry 변경은 계정·리전에 영향을 주므로 기존 운영 규칙을 보존해야 합니다.

### 이미지 서명

ECR은 AWS Signer를 이용한 **관리형 자동 서명**과 Notation 등의 수동 서명을 지원합니다. 서명 저장만으로 EKS가 미서명 이미지를 자동 차단하지는 않습니다. 신뢰할 서명자·digest와 admission 검증 정책을 별도로 구성합니다. [이미지 서명 안내](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-signing.html)를 참고합니다.

관리형 서명을 활성화한 저장소에 push할 주체에는 해당 signing profile에 대한 `signer:SignPayload` 등 공식 설정의 추가 권한도 필요합니다. 아래 ECR-only 정책 예제가 서명 권한까지 포함한다고 가정하지 않습니다.

---

## 인증 및 접근 제어

### Docker 로그인

```bash
# AWS CLI v2로 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com

# 토큰 유효 기간: 12시간
```

### amazon-ecr-credential-helper

Docker 자격 증명을 자동으로 관리합니다:

```bash
# 설치 (Amazon Linux 2023; 다른 배포판은 upstream 설치 안내 확인)
sudo yum install -y amazon-ecr-credential-helper

# macOS
brew install docker-credential-helper-ecr

# Docker 설정에 병합할 JSON 조각 (기존 config.json을 통째로 덮어쓰지 않음)
```

```json
{
  "credHelpers": {
    "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com": "ecr-login",
    "public.ecr.aws": "ecr-login"
  }
}
```

```bash
# 이후 docker push/pull 시 자동 인증
docker push 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.0.0
```

### IAM 정책 예시

**읽기 전용 (Pull):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRPull",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:DescribeImages",
        "ecr:DescribeRepositories",
        "ecr:ListImages"
      ],
      "Resource": [
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-*"
      ]
    }
  ]
}
```

**Push 권한:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "ECRPush",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": [
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-*"
      ]
    }
  ]
}
```

**관리자 권한 (워크로드/일반 CI 역할에 사용하지 않는 관리 예제):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAdmin",
      "Effect": "Allow",
      "Action": "ecr:*",
      "Resource": "*"
    }
  ]
}
```

### 교차 계정 접근

**리소스 기반 정책 (대상 리포지토리에 설정):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CrossAccountPull",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::111111111111:root",
          "arn:aws:iam::222222222222:role/EKSNodeRole"
        ]
      },
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ]
    }
  ]
}
```

```bash
# 리소스 정책 적용
aws ecr set-repository-policy \
  --repository-name myapp \
  --policy-text file://ecr-resource-policy.json
```

**교차 계정에서 pull:**
```bash
# 계정 111111111111에서 계정 123456789012의 이미지 pull
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com

docker pull 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.0.0
```

---

## Lifecycle Policy 심화

ECR Lifecycle Policy는 이미지 보존 규칙을 자동화하여 스토리지 비용을 최적화합니다. 이 섹션에서는 다양한 전략과 그 장단점을 상세히 설명합니다.

### Lifecycle Policy 동작 원리

![Lifecycle 규칙 평가 결과에 우선순위를 적용해 만료 또는 보존을 결정하는 과정을 단순화한 그림. 실제 서비스는 모든 규칙을 먼저 평가한 뒤 우선순위를 적용한다.](../.gitbook/assets/ko-container-registry-02-amazon-ecr-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-02-amazon-ecr-1.html)

**규칙 평가와 적용:**
1. 모든 규칙을 우선순위와 무관하게 먼저 평가합니다.
2. 평가 결과에 `rulePriority`를 적용하며 낮은 숫자가 높은 우선순위입니다.
3. 높은 우선순위 규칙의 태그 조건에 해당하는 이미지는 낮은 우선순위 규칙이 만료시킬 수 없습니다.
4. 한 이미지에는 만료/아카이브 규칙이 최대 하나 적용됩니다. 이미지 개수는 태그 개수가 아니라 digest 단위로 이해합니다.
5. 동일 storage class에서 태그 prefix 집합은 고유해야 하고 untagged 규칙은 하나만 둘 수 있습니다. `any` 규칙은 가장 낮은 우선순위에 둡니다.

**선택 기준 (Selection Criteria):**

| 기준 | 설명 | 예시 |
|------|------|------|
| `tagStatus` | 태그 상태 | `tagged`, `untagged`, `any` |
| `tagPatternList` | 문서화된 `*` 와일드카드; 여러 패턴은 AND | `["v*"]` |
| `countType` | 카운트 방식 | `imageCountMoreThan`, `sinceImagePushed` |
| `countNumber` | 선택한 countType의 양수 임계값 | `100` |
| `countUnit` | 시간 단위 | `days` |

**중요 제한사항:**
- 단일 규칙에서 `imageCountMoreThan`과 `sinceImagePushed`를 OR 조건으로 결합할 수 없음
- 서로 다른 태그 그룹은 별도 규칙으로 다룰 수 있지만 만료 규칙들이 일반적인 Boolean 보존식을 구성하지는 않음
- "N개 또는 M일 중 더 많은 쪽" 로직은 네이티브 지원 안 됨

`tagPatternList`는 정규식이나 일반적인 전체 glob 문법이 아닙니다. `?`, `[0-9]`, `^`, `$`로 SemVer를 검사하지 않으며 문자열당 `*`는 최대 4개입니다. 이 예제는 CI에서 `v1.2.3` 형태를 검증한 뒤 `v*`로 분류합니다. 아래는 활성 이미지 만료 예제이며, 아카이브·복원 시간과 참조 아티팩트 규칙은 [현재 lifecycle 문서](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html)를 별도로 확인합니다.

---

### Strategy A: 분리된 리포지토리 (권장)

프로덕션과 개발 이미지를 별도 리포지토리로 분리하면 각각에 최적화된 lifecycle 정책을 적용할 수 있습니다.

**아키텍처:**
```
myapp-prod/          myapp-dev/
├── v1.0.0           ├── dev-abc123
├── v1.1.0           ├── dev-def456
├── v1.2.0           ├── stage-ghi789
├── v2.0.0           ├── feature-xyz
└── ... (최대 100개)  └── ... (60일 이내)
```

**프로덕션 리포지토리 (myapp-prod) Lifecycle Policy:**

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep newest 100 v-prefixed release image digests; CI validates the version format",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "v*"
        ],
        "countType": "imageCountMoreThan",
        "countNumber": 100
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "태그 없는 이미지 1일 후 삭제",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countNumber": 1,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

**개발 리포지토리 (myapp-dev) Lifecycle Policy:**

이 예제는 나이 기준 보존만 적용합니다. 60일보다 오래된 tagged 이미지는 모두 만료될 수 있으며, 다른 count 규칙을 아래에 추가한다고 최소 30개가 보호되지 않습니다. 실행 중인 digest와 롤백 이미지의 별도 보호 정책이 필요합니다.

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire tagged development images older than 60 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "*"
        ],
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 60
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Expire untagged images after 3 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 3
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

**Strategy A 장점:**
- 환경별 명확한 정책 분리
- 프로덕션 이미지 실수 삭제 방지
- 간단하고 예측 가능한 동작
- Immutable tags를 프로덕션에만 적용 가능

**Strategy A 단점:**
- 이미지 프로모션 시 cross-repo 복사 필요
- 리포지토리 수 증가

---

### Strategy B: 단일 리포지토리 + 우선순위 규칙

하나의 리포지토리에서 태그 패턴으로 환경을 구분합니다.

**태그 컨벤션:**
```
myapp/
├── v1.0.0         # 프로덕션 (CI에서 SemVer 검증)
├── v1.1.0         # 프로덕션 (CI에서 SemVer 검증)
├── dev-abc123     # 개발
├── dev-def456     # 개발
├── stage-ghi789   # 스테이징
└── staging-xyz    # 스테이징
```

**Lifecycle Policy:**

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep newest 100 v-prefixed release image digests; CI validates the version format",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "v*"
        ],
        "countType": "imageCountMoreThan",
        "countNumber": 100
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Expire dev-* images older than 60 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "dev-*"
        ],
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 60
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 3,
      "description": "Expire stage-* images older than 60 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "stage-*"
        ],
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 60
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 4,
      "description": "Expire staging-* images older than 60 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "staging-*"
        ],
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 60
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 9,
      "description": "태그 없는 이미지 3일 후 삭제",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countNumber": 3,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

**⚠️ Strategy B의 중요한 제한사항:**

독립적인 만료 규칙을 나열하는 것만으로 같은 이미지 집합에 "최근 N개 또는 최근 M일 중 더 많이 보존"이라는 조건을 직접 구성할 수는 없습니다. 별도 dev/stage 규칙은 다른 태그 그룹을 선택하기 위한 것이며, 보존 조건의 합집합과는 다릅니다.

**문제 시나리오:**
```
목표: 개발 이미지를 "최소 10개" 또는 "60일 이내" 중 더 관대한 조건으로 보존

현실:
- 규칙 2 (60일 규칙)가 먼저 적용됨
- 10개 미만의 dev 이미지가 있어도 60일 지나면 모두 삭제됨
- 이 정책에는 최소 개수와 기간을 동시에 보장하는 보존 조건이 없음
```

**구체적 예시:**
```
현재 dev 이미지 상황:
- dev-001 (70일 전) -> 삭제됨 (60일 초과)
- dev-002 (65일 전) -> 삭제됨 (60일 초과)
- dev-003 (55일 전) -> 유지
- dev-004 (30일 전) -> 유지
- dev-005 (10일 전) -> 유지

결과: 3개만 남음 (10개 보존 목표 달성 불가)
```

**이 제한을 다룰 때:**
- 리포지토리 분리는 환경을 격리하지만 같은 이미지 집합의 복합 보존 조건을 자동 구현하지 않습니다.
- 복합 조건에는 별도 판단 로직이 필요합니다. 아래 예제는 안전한 검토를 위한 조회 전용 미리보기입니다.

---

### Strategy C: Lambda 기반 보존 후보 미리보기 (조회 전용)

복합 보존 조건을 계산할 수 있지만 후보 계산과 실제 삭제는 별개입니다. 아래 코드는 삭제 API를 호출하지 않습니다. `REPOSITORY_NAME` 환경변수와 해당 리포지토리의 `ecr:DescribeImages` 권한을 설정하고 현재 ECR 모델을 지원하는 boto3를 사용합니다. dev/stage 태그만 가진 일반 이미지에 보수적으로 적용하며, release·알 수 없는 태그·index·서명 아티팩트·명시적 보호 digest는 후보에서 제외합니다.

**아키텍처:**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ EventBridge │────▶│   Lambda    │────▶│    ECR      │
│ (Schedule)  │     │  Preview    │     │ Repository  │
│ optional    │     │             │     │             │
└─────────────┘     │ - List imgs │     │ - Read      │
                    │ - Review    │     │   metadata  │
                    │   rules     │     │   only      │
                    └─────────────┘     └─────────────┘
```

**Lambda 함수 (Python):** 최신 최소 개수와 최근 기간을 함께 보존합니다. 실제 삭제를 추가하려면 실행 중인 workload·멀티아키텍처 참조·롤백·동시 재태깅을 다시 확인하고 승인을 받아야 합니다. 10,000건을 넘으면 일부 데이터로 판단하지 않고 중단합니다.

```python
# ecr_retention_preview.py -- read-only candidate report, never deletes images
import os
from datetime import datetime, timedelta, timezone

import boto3

ecr = boto3.client("ecr")


def retention_candidates(images, now, min_images=10, max_age_days=60, protected_digests=()):
    if type(min_images) is not int or min_images < 1:
        raise ValueError("min_images must be a positive integer")
    if type(max_age_days) is not int or max_age_days < 1:
        raise ValueError("max_age_days must be a positive integer")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if isinstance(protected_digests, str):
        raise ValueError("protected_digests must be a collection, not a string")
    protected = set(protected_digests)
    by_digest = {image["imageDigest"]: image for image in images if image.get("imageDigest")}
    eligible = []
    manifests = {
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
    }
    configs = {
        None,
        "application/vnd.docker.container.image.v1+json",
        "application/vnd.oci.image.config.v1+json",
    }
    for digest, image in by_digest.items():
        tags = image.get("imageTags") or []
        timestamp = image.get("lastActivatedAt") or image.get("imagePushedAt")
        if digest in protected or not tags:
            continue
        # A dev tag must not hide a release/protected tag on the same digest.
        if not all(tag.startswith(("dev-", "stage-", "staging-")) for tag in tags):
            continue
        # This example does not classify indexes, signatures or unknown artifacts.
        if image.get("imageManifestMediaType") not in manifests:
            continue
        if image.get("artifactMediaType") not in configs:
            continue
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            continue
        eligible.append((timestamp, digest, tags))
    eligible.sort(reverse=True, key=lambda item: item[0])
    cutoff = now - timedelta(days=max_age_days)
    return [
        {"imageDigest": digest, "imageTags": tags, "timestamp": timestamp.isoformat()}
        for timestamp, digest, tags in eligible[min_images:]
        if timestamp < cutoff
    ]


def lambda_handler(event, context):
    repository = os.environ["REPOSITORY_NAME"]
    images = []
    paginator = ecr.get_paginator("describe_images")
    for page in paginator.paginate(repositoryName=repository, filter={"imageStatus": "ACTIVE"}):
        images.extend(page.get("imageDetails", []))
        if len(images) > 10000:
            raise ValueError("Inventory too large for this example; use a paged batch workflow")
    candidates = retention_candidates(
        images,
        datetime.now(timezone.utc),
        event.get("min_images", 10),
        event.get("max_age_days", 60),
        event.get("protected_digests", []),
    )
    return {
        "repository": repository,
        "dry_run": True,
        "candidate_count": len(candidates),
        "candidates_requiring_review": candidates,
    }
```

### Lifecycle Policy Dry-Run 테스트

정책을 적용하기 전에 미리 결과를 확인할 수 있습니다:

```bash
# Dry-run 시작
aws ecr start-lifecycle-policy-preview \
  --repository-name myapp \
  --lifecycle-policy-text file://lifecycle-policy.json

aws ecr wait lifecycle-policy-preview-complete --repository-name myapp

# 결과 조회
aws ecr get-lifecycle-policy-preview \
  --repository-name myapp

```

출력 구조 예시(축약):

```json
{
  "registryId": "123456789012",
  "repositoryName": "myapp",
  "lifecyclePolicyText": "...",
  "status": "COMPLETE",
  "previewResults": [
    {
      "imageTags": ["dev-old-001"],
      "imageDigest": "sha256:abc123...",
      "imagePushedAt": "2024-01-15T10:00:00Z",
      "action": {
        "type": "EXPIRE"
      },
      "appliedRulePriority": 2
    }
  ]
}
```

---

### Lifecycle Policy 전략 비교

| 전략 | 복잡성 | 유연성 | 운영 부담 | 권장 사용 사례 |
|------|--------|--------|----------|---------------|
| **A: 분리 리포지토리** | 낮음 | 높음 | 낮음 | 대부분의 팀 (권장) |
| **B: 단일 + 우선순위** | 중간 | 중간 | 낮음 | 소규모 프로젝트 |
| **C: 커스텀 후보 미리보기** | 높음 | 높음 | 별도 검토 필요 | 복합 보존 판단; 삭제 구현은 별도 |

---

## 멀티 환경 태그 전략

### 태그 네이밍 컨벤션

**권장 태그 형식:**

| 환경 | 태그 형식 | 예시 |
|------|----------|------|
| 프로덕션 | `v` 접두어 + CI에서 검증한 SemVer | `v1.2.3`, `v2.0.0` |
| 스테이징 | `stage-{semver}` | `stage-1.2.3` |
| 개발 | `dev-{git-sha}` | `dev-abc1234` |
| Feature | `feature-{name}-{sha}` | `feature-login-def5678` |
| PR | `pr-{number}` | `pr-123` |

**CI/CD에서 태그 생성:**

```bash
# Git 정보 기반 태그 생성
GIT_SHA=$(git rev-parse --short HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
BUILD_DATE=$(date +%Y%m%d)

# 브랜치별 태그 전략
case $GIT_BRANCH in
  main)
    # SemVer 태그 (릴리스 시)
    : "${VERSION:?Set MAJOR.MINOR.PATCH}"
    [[ "${VERSION#v}" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || exit 1
    TAG="v${VERSION#v}"
    ;;
  develop)
    TAG="dev-${GIT_SHA}"
    ;;
  release/*)
    TAG="stage-${VERSION}-${GIT_SHA}"
    ;;
  feature/*)
    FEATURE_NAME=$(printf '%s' "$GIT_BRANCH" | sed 's#[^a-zA-Z0-9_.-]#-#g' | cut -c1-90)
    TAG="feature-${FEATURE_NAME}-${GIT_SHA}"
    ;;
  *)
    BRANCH_SLUG=$(printf '%s' "$GIT_BRANCH" | sed 's#[^a-zA-Z0-9_.-]#-#g' | cut -c1-90)
    TAG="branch-${BRANCH_SLUG}-${GIT_SHA}"
    ;;
esac

docker tag myapp:latest ${ECR_REPO}:${TAG}
docker push ${ECR_REPO}:${TAG}
```

### 태그 프로모션 워크플로우

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Build     │────▶│   Stage     │────▶│ Production  │
│             │     │             │     │             │
│ dev-abc123  │     │stage-1.0.0  │     │   1.0.0     │
└─────────────┘     └─────────────┘     └─────────────┘
        │                  │                   │
        ▼                  ▼                   ▼
   myapp-dev/         myapp-stage/       myapp-prod/
   (ECR Repo)         (ECR Repo)         (ECR Repo)
```

**프로모션 예제:** Docker pull/tag/push는 기본적으로 현재 플랫폼 이미지만 이동할 수 있습니다. 멀티아키텍처 index와 하위 manifest를 보존해야 한다면 [Skopeo 전체 복사](https://github.com/containers/skopeo/blob/main/docs/skopeo-copy.1.md) 같은 도구를 사용하고 목적지 digest를 확인합니다. 두 리포지터리에 대한 로그인·권한이 먼저 필요하며, 서명/referrer와 repository 정책은 별도로 검증합니다.

```bash
# Requires skopeo and authenticated access to both existing repositories.
# SOURCE_IMAGE is a complete source repository@sha256:digest reference.
: "${SOURCE_IMAGE:?Set the verified source digest reference}"
: "${TARGET_IMAGE:?Set the destination repository and release tag}"
skopeo copy --all --preserve-digests "docker://$SOURCE_IMAGE" "docker://$TARGET_IMAGE"
```

### Immutable Tags의 범위

`IMMUTABLE`은 존재하는 태그의 덮어쓰기를 막습니다. 이미지 삭제, 태그 삭제 후 재생성, 정책 변경까지 막는 보존 장치는 아닙니다. 배포에는 실제 전체 digest를 사용하고 삭제 권한·lifecycle·롤백 보존을 별도로 관리합니다.

---

## EKS 통합

### 이미지 pull 주체와 워크로드 IAM 역할 구분

컨테이너가 시작되기 **전**의 image pull은 kubelet/노드 실행 환경이 수행합니다. IRSA나 Pod Identity가 파드에 제공하는 AWS SDK 자격 증명을 kubelet이 대신 사용하는 것은 아닙니다.

| 실행 환경 | 초기 ECR image pull에 사용하는 권한 |
|---|---|
| EC2 기반 관리형/자체 관리 노드 | 노드 IAM 역할의 ECR pull 권한 |
| EKS Auto Mode | Auto Mode node role의 ECR pull 권한 |
| Fargate | Fargate Pod execution role |
| 별도 credential provider/Secret을 사용하는 환경 | 해당 provider 또는 같은 namespace의 imagePullSecrets |

[노드 역할](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)의 `AmazonEC2ContainerRegistryPullOnly` 같은 권한을 확인합니다. [Fargate execution role](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html)은 애플리케이션 컨테이너가 직접 가정하는 역할이 아닙니다. 교차 계정 pull에는 대상 repository policy와 호출 주체의 IAM 권한도 필요합니다.

### IRSA / Pod Identity의 용도

이미 실행된 빌드·운영 Pod가 AWS SDK로 ECR을 조회하거나 이미지를 push할 때 워크로드 역할을 사용합니다. 이는 기본 이미지 pull 권한의 대체물이 아닙니다. IRSA는 OIDC/trust 설정이, Pod Identity는 지원 실행 환경·Agent·역할 trust policy·ServiceAccount association이 필요합니다. 관련 설정은 [EKS workload IAM 안내](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)를 따릅니다.

### imagePullSecrets가 필요한 환경

ECR 인증 토큰은 12시간 유효합니다. 아래는 AWS CLI, Python 3, kubectl이 준비된 실행 환경에서 **기존 Secret을 삭제하지 않고** 갱신하는 독립 스크립트입니다. Secret과 Pod는 같은 namespace여야 하고 Kubernetes API에 접근할 자격 증명도 있어야 합니다.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_REGION:?Set the ECR region}"
ECR_ACCOUNT_ID=${ECR_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
export ECR_REGISTRY="$ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
PULL_SECRET_NAMESPACE=${PULL_SECRET_NAMESPACE:-default}
registry_secret_file=$(mktemp)
trap 'rm -f "$registry_secret_file"' EXIT
# Build the config before touching Kubernetes; an AWS failure keeps the old Secret.
aws ecr get-login-password --region "$AWS_REGION" | python3 -c '
import base64, json, os, sys
password = sys.stdin.read().strip()
if not password:
    raise SystemExit("No ECR password returned")
auth = base64.b64encode(("AWS:" + password).encode()).decode()
json.dump({"auths": {os.environ["ECR_REGISTRY"]: {"auth": auth}}}, sys.stdout)
' > "$registry_secret_file"
kubectl create secret generic ecr-secret \
  --namespace "$PULL_SECRET_NAMESPACE" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=.dockerconfigjson="$registry_secret_file" \
  --dry-run=client -o yaml | \
  kubectl apply --server-side --field-manager=ecr-credentials-sync -f -
```

이 스크립트를 CronJob에 넣으려면 세 도구가 실제 포함된 검증된 이미지, `ecr:GetAuthorizationToken`을 호출할 IAM 자격 증명, 대상 Secret의 get/create/patch 권한, 12시간보다 짧은 갱신 주기와 실패 알림을 별도로 준비합니다. `amazon/aws-cli` 이미지에 kubectl이 있다고 가정하면 안 됩니다. 회전 작업 자신의 이미지를 만료될 동일 Secret에 의존시키지 않습니다. 기존 Secret의 필드 관리 충돌도 확인하며 `--force-conflicts`로 다른 컨트롤러를 덮어쓰지 않습니다.

### Private Endpoint 접근

ECR에 사설로 연결하려면 다음 VPC endpoint를 구성합니다. 이는 완전히 단절된 에어갭이 아닙니다. PTC 최초 pull 및 Windows foreign layer 등 추가 통신 요구는 [현재 endpoint 지침](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)을 확인합니다:

- **ecr.api**: ECR API 호출용 Interface 엔드포인트
- **ecr.dkr**: Docker 레지스트리 프로토콜용 Interface 엔드포인트
- **s3**: 이미지 레이어 저장소 접근용 Gateway 엔드포인트

```bash
# VPC Endpoint 생성 (AWS CLI)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.ap-northeast-2.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-11111111 subnet-22222222 \
  --security-group-ids sg-12345678 \
  --private-dns-enabled

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.ap-northeast-2.ecr.dkr \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-11111111 subnet-22222222 \
  --security-group-ids sg-12345678 \
  --private-dns-enabled

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.ap-northeast-2.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids rtb-12345678
```

### ECR Pull-through Cache

외부 레지스트리를 ECR을 통해 캐싱하여 외부 의존성을 줄이고 pull 성능을 향상시킵니다.

![kubelet의 이미지 요청이 ECR 엔드포인트를 거쳐 캐시가 있으면 즉시 제공하고, 캐시가 없으면 업스트림 레지스트리에서 가져와 ECR에 캐시로 저장한 뒤 제공하는 흐름을 보여준다.](../.gitbook/assets/ko-container-registry-02-amazon-ecr-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-02-amazon-ecr-2.html)

#### 지원 Upstream 레지스트리

| Upstream 레지스트리 | ECR Prefix | 인증 필요 | 비고 |
|---|---|---|---|
| Docker Hub | `docker-hub` | Yes (Secrets Manager) | 반복 다운로드 감소; upstream 사용 정책은 여전히 적용 |
| Quay.io | `quay` | No | Red Hat / CoreOS 이미지 |
| GitHub Container Registry | `ghcr` | Yes (Secrets Manager) | GitHub Actions 이미지 |
| registry.k8s.io | `k8s` | No | Kubernetes 핵심 컴포넌트 |
| ECR Public | `ecr-public` | No | AWS 공개 이미지 |

#### Secrets Manager 설정 (인증 필요 레지스트리)

```bash
# Docker Hub 자격 증명 저장
aws secretsmanager create-secret \
  --name ecr-pullthroughcache/docker-hub \
  --secret-string '{"username":"your-dockerhub-username","accessToken":"dckr_pat_xxxxx"}'

# GitHub Container Registry 자격 증명 저장
aws secretsmanager create-secret \
  --name ecr-pullthroughcache/ghcr \
  --secret-string '{"username":"your-github-username","accessToken":"ghp_xxxxx"}'
```

#### Pull-through Cache 규칙 생성

```bash
# Docker Hub 캐시 규칙 생성
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub \
  --upstream-registry-url registry-1.docker.io \
  --credential-arn "$(aws secretsmanager describe-secret --secret-id ecr-pullthroughcache/docker-hub --region "$AWS_REGION" --query ARN --output text)" \
  --region "$AWS_REGION"

# Quay.io 캐시 규칙
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix quay \
  --upstream-registry-url quay.io

# GitHub Container Registry 캐시 규칙
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix ghcr \
  --upstream-registry-url ghcr.io \
  --credential-arn "$(aws secretsmanager describe-secret --secret-id ecr-pullthroughcache/ghcr --region "$AWS_REGION" --query ARN --output text)" \
  --region "$AWS_REGION"

# Kubernetes 레지스트리 캐시 규칙
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix k8s \
  --upstream-registry-url registry.k8s.io

# ECR Public 캐시 규칙
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix ecr-public \
  --upstream-registry-url public.ecr.aws
```

#### Pull-through Cache용 IAM 정책

아래는 캐시 pull·초기 import용 호출 주체의 예시입니다. 캐시 규칙 생성 관리 권한은 별도로 부여합니다. upstream secret 조회는 ECR의 service-linked role이 수행하므로 일반 pull 클라이언트에 Secrets Manager 값을 일괄 공개하지 않습니다. [권한 안내](https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache-iam.html)를 확인합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RegistryAuthentication",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "ReadCachedImages",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": [
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/docker-hub/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/quay/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/ghcr/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/k8s/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/ecr-public/*"
      ]
    },
    {
      "Sid": "ImportCacheMisses",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchImportUpstreamImage",
        "ecr:CreateRepository"
      ],
      "Resource": [
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/docker-hub/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/quay/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/ghcr/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/k8s/*",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/ecr-public/*"
      ]
    }
  ]
}
```

#### 검증

```bash
# 캐시 규칙 확인
aws ecr describe-pull-through-cache-rules

# 테스트 pull (Docker Hub nginx)
docker pull 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/docker-hub/library/nginx:1.30.4

# 캐시된 리포지토리 확인
aws ecr describe-repositories \
  --repository-names docker-hub/library/nginx

# Kubernetes 레지스트리 이미지 테스트
docker pull 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/k8s/pause:3.10
```

#### 이미지 경로를 명시적으로 변경

ECR 캐시의 실제 이미지 URI를 Pod/Helm/Kustomize에 사용하면 노드 인증 흐름과 레지스트리 경로가 명확해집니다. 폐기된 `registry.mirrors`에 ECR URL만 넣어 모든 레지스트리를 투명하게 바꿀 수 있다고 가정하지 않습니다. 그러한 미러 구성이 필요하면 containerd 버전의 hosts 설정, prefix 매핑, TLS와 ECR 인증을 함께 검증해야 합니다.

**사용 예시:**

```yaml
# 원본 이미지 -> Pull-through 캐시
# docker.io/library/nginx:1.30.4
# -> 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/docker-hub/library/nginx:1.30.4

apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/docker-hub/library/nginx:1.30.4
```

---

## 멀티 리전 복제

### 복제 구성

```bash
# 복제 규칙 설정
aws ecr put-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {
            "region": "us-west-2",
            "registryId": "123456789012"
          },
          {
            "region": "eu-west-1",
            "registryId": "123456789012"
          }
        ],
        "repositoryFilters": [
          {
            "filter": "myapp",
            "filterType": "PREFIX_MATCH"
          }
        ]
      }
    ]
  }'
```

복제는 비동기이며 기존 콘텐츠를 자동 backfill하지 않습니다. 설정 이후 push 또는 restore된 이미지가 대상입니다. repository 설정·lifecycle·권한은 대상에서 별도로 구성하고, 필요한 digest의 복제 완료를 확인합니다. 태그 불변성은 삭제 방지나 RPO 0 보장이 아닙니다.

### DR 고려사항

```yaml
# 멀티 리전 배포 시 이미지 참조
# Primary: ap-northeast-2
# DR: us-west-2

# Helm values (region별)
# values-ap-northeast-2.yaml
image:
  repository: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp
  tag: v1.0.0

# values-us-west-2.yaml (DR)
image:
  repository: 123456789012.dkr.ecr.us-west-2.amazonaws.com/myapp
  tag: v1.0.0
```

---

## 모니터링 및 비용 최적화

### CloudWatch 메트릭과 스캔 결과

ECR이 `AWS/ECR`에 기본 제공하는 리포지터리 메트릭은 `RepositoryPullCount`이며 dimension은 `RepositoryName`입니다. [공식 메트릭 목록](https://docs.aws.amazon.com/AmazonECR/latest/userguide/ecr-repository-metrics.html)을 기준으로 설정합니다. `ImagePushCount`나 `ImageScanFindingsSeverityCounts`를 기본 메트릭이라고 가정하면 알람이 실제 취약점을 보지 못합니다.

```bash
# GNU date가 있는 Linux 예제; 지정 리포지터리의 최근 7일 pull 횟수
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECR --metric-name RepositoryPullCount \
  --dimensions Name=RepositoryName,Value=myapp \
  --start-time "$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 86400 --statistics Sum --region "$AWS_REGION"

# 스캔 결과는 ECR/Inspector API에서 조회
aws ecr describe-image-scan-findings \
  --repository-name myapp --image-id imageTag=v1.0.0 \
  --query '{status:imageScanStatus.status,counts:imageScanFindings.findingSeverityCounts}' --region "$AWS_REGION"
```

Basic scan 완료 이벤트나 Inspector finding 이벤트를 EventBridge로 전달해 알림을 구성합니다. CloudWatch 숫자 알람이 필요하면 이 이벤트/API 결과에서 명시적으로 사용자 지정 메트릭을 발행해야 합니다. 기본 제공 메트릭과 사용자 지정 메트릭을 구분합니다. null/누락된 결과를 취약점 0건으로 해석하지 말고 스캔 상태·지원 여부를 확인합니다.

### 비용 분석

이미지 메타데이터의 크기 합은 공유 레이어를 중복 포함하고 아카이브 등 청구 항목과 다릅니다. 이를 저장 청구량이나 절감액으로 단정하지 않습니다.

```bash
# Active-image metadata sizes are logical totals, not billed unique-layer storage.
aws ecr describe-repositories --region "$AWS_REGION" --output json | \
  jq -r '.repositories[].repositoryName' | while IFS= read -r repo; do
    size=$(aws ecr describe-images --repository-name "$repo" \
      --region "$AWS_REGION" --output json | \
      jq '[.imageDetails[].imageSizeInBytes // 0] | add // 0')
    printf '%s: %s logical image bytes\n' "$repo" "$size"
  done
```

실제 비용은 권한이 있는 billing 계정에서 Cost Explorer/CUR로 확인합니다. 기간의 End는 제외 경계입니다. ECR 서비스 필터만으로 Inspector, Signer, KMS, 네트워크 서비스 비용까지 포함되지는 않습니다.

```bash
: "${START_DATE:?Set inclusive YYYY-MM-DD start}"
: "${END_DATE:?Set exclusive YYYY-MM-DD end}"
# Discover the exact billing service name rather than hard-coding a legacy label.
aws ce get-dimension-values --region us-east-1 \
  --time-period Start="$START_DATE",End="$END_DATE" \
  --dimension SERVICE --search-string 'Container Registry'

: "${ECR_BILLING_SERVICE:?Set the returned service name}"
aws ce get-cost-and-usage --region us-east-1 \
  --time-period Start="$START_DATE",End="$END_DATE" \
  --granularity MONTHLY --metrics UnblendedCost \
  --filter "$(jq -nc --arg service "$ECR_BILLING_SERVICE" \
    '{Dimensions:{Key:"SERVICE",Values:[$service]}}')"
```

### 비용 최적화 팁

**1. Lifecycle Policy 적극 활용:**
```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "dev 이미지 14일 후 삭제",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "dev-*"
        ],
        "countType": "sinceImagePushed",
        "countNumber": 14,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

**2. 멀티스테이지 빌드로 이미지 크기 줄이기:**
```dockerfile
# 빌드 스테이지
FROM golang:1.27.1 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o main .

# 런타임 스테이지 (작은 베이스 이미지)
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/main /
ENTRYPOINT ["/main"]
```

**3. 리전 간 전송 최소화:**
```yaml
# 각 리전에서 로컬 ECR 사용
# ap-northeast-2 클러스터
image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.0.0

# us-west-2 클러스터 (복제된 이미지 사용)
image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/myapp:v1.0.0
```

---

## 요약

| 항목 | 권장 사항 |
|------|----------|
| **리포지토리 구조** | 환경별 분리 (prod/dev) |
| **태그 전략** | SemVer (prod), git-sha (dev) |
| **태그 불변성** | 프로덕션: IMMUTABLE |
| **스캐닝** | Enhanced Scanning (프로덕션) |
| **Lifecycle** | Strategy A (분리 리포지토리) |
| **인증** | image pull은 노드/실행 역할; 워크로드 SDK 권한은 별도 |
| **비용** | Lifecycle + 멀티스테이지 빌드 |
| **DR** | 멀티 리전 복제 |

---

## 참고 자료

- [Amazon ECR 사용 설명서](https://docs.aws.amazon.com/AmazonECR/latest/userguide/)
- [ECR Lifecycle Policies](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html)
- [ECR 이미지 스캐닝](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [ECR Pull-through Cache](https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache.html)
- [EKS 노드의 ECR pull 권한](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [ECR 가격](https://aws.amazon.com/ecr/pricing/)
