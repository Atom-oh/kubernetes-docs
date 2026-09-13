# Crossplane

> **마지막 업데이트**: 2026년 9월 13일 · Crossplane 2.4.0 / AWS provider 2.7.0

## 개념과 v2 변경

Crossplane은 Kubernetes API와 controller로 인프라 및 애플리케이션 리소스를 조정합니다. CNCF 합류는 2020년 6월 25일, Incubating은 2021년 9월 14일, Graduated는 2025년 10월 28일입니다. 원문에 서로 다르게 적힌 2023/2024년 졸업 설명을 수정했습니다.

| 구성 요소 | 역할과 현재 범위 |
| --- | --- |
| Provider | CRD와 controller를 설치하는 package입니다. 서비스별 AWS package를 선택할 수 있으며 하나가 모든 AWS API를 지원하는 것은 아닙니다. |
| Managed Resource (MR) | Provider가 외부 리소스를 관리하는 API입니다. 예제의 v2 MR은 namespace 범위입니다. |
| Composite Resource (XR) | 플랫폼 API의 인스턴스입니다. XRD v2는 기본적으로 Namespaced입니다. |
| XRD | XR schema와 scope를 정의합니다. v1 LegacyCluster와 v2 Namespaced를 구분합니다. |
| Composition | Function pipeline이 XR 입력으로 원하는 자원과 상태를 계산하도록 정의합니다. |
| Claim | 기존 LegacyCluster XR의 namespace 인터페이스입니다. 새 namespace XR에 반드시 필요한 계층이 아닙니다. |

![Crossplane v2 핵심 개념](../.gitbook/assets/ko-platform-engineering-07-crossplane-0.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-07-crossplane-0.html)

기존 v1 XRD는 LegacyCluster로 Claims를 계속 사용할 수 있고 기존 cluster MR도 호환 경로가 있습니다. 그러나 native Resources-mode Composition, ControllerConfig와 XR native connection publication 등 제거된 기능을 그대로 두고 core 버전만 바꾸면 안 됩니다. 공식 v2 migration 안내는 1.20에서 준비 작업을 수행하도록 설명합니다.

Terraform도 선언적 desired state를 사용하는 도구이며 plan/apply를 CI에서 자동화할 수 있습니다. 차이는 주로 실행 workflow와 controller의 지속적 reconciliation입니다. Crossplane 역시 managementPolicies, provider 지원 범위와 오류·quota에 따라 조정하며 모든 drift를 즉시 고치지는 않습니다.

## Core 설치·Provider·권한

검토한 Helm chart는 2.4.0입니다. 아래는 cluster에 설치하지 않는 오프라인 검사 명령입니다.

```bash
helm repo add crossplane-stable https://charts.crossplane.io/stable
helm repo update
helm template crossplane crossplane-stable/crossplane   --version 2.4.0 --namespace crossplane-system   --set metrics.enabled=true
```

현재 chart의 provider.defaultActivations 기본값은 ["*"]입니다. MRD/ManagedResourceActivationPolicy와 설치한 서비스 범위를 확인하고 필요한 API만 활성화하는 전략을 검토합니다. Provider가 Installed라고 실제 AWS 인증·리소스 readiness가 검증되는 것은 아닙니다.

아래 S3 Provider 예제의 IAM role은 placeholder입니다. 정확한 EKS OIDC issuer, audience와 ServiceAccount subject를 trust에 제한하고 서비스별 IAM actions/resources를 검토하세요. RequestedRegion 조건 하나를 붙인 s3:*/rds:*/ec2:*/iam:*는 최소 권한 policy가 아닙니다. RDS·EC2 Provider에도 각각 검토한 runtime/identity가 필요합니다.

```yaml
apiVersion: pkg.crossplane.io/v1beta1
kind: DeploymentRuntimeConfig
metadata:
  name: provider-aws-s3-reviewed
spec:
  deploymentTemplate:
    spec:
      selector: {}
      template:
        spec:
          containers:
          - name: package-runtime
            resources:
              requests:
                cpu: 100m
                memory: 256Mi
              limits:
                cpu: 500m
                memory: 512Mi
            ports:
            - name: metrics
              containerPort: 8080
        metadata:
          labels:
            app: provider-aws-s3-reviewed
  serviceAccountTemplate:
    metadata:
      name: provider-aws-s3-reviewed
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ReplaceApprovedS3ProviderRole
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-aws-s3
spec:
  package: xpkg.crossplane.io/crossplane-contrib/provider-aws-s3:v2.7.0
  packagePullPolicy: IfNotPresent
  revisionActivationPolicy: Manual
  revisionHistoryLimit: 2
  runtimeConfigRef:
    name: provider-aws-s3-reviewed
```

여러 Provider가 같은 고정 ServiceAccount를 소유하도록 설정하지 않습니다. packagePullPolicy는 다운로드 정책이고 revisionActivationPolicy는 revision 활성화 정책입니다. Manual을 사용하면 ProviderRevision 상태와 승인된 버전의 활성화를 별도로 확인합니다.

community와 Upbound registry에서 2.7.0 S3 package manifest 접근을 확인했지만 digest는 서로 달랐습니다. 같은 version 문자열이 같은 artifact라는 뜻은 아닙니다. 선택한 배포판·registry·digest·지원 조건을 고정하세요.

예제는 namespace ProviderConfig와 IRSA를 사용합니다. 2.7.0 schema는 PodIdentity도 지원하지만 실제 association/SDK/runtime을 구성해야 합니다. ProviderConfig를 namespace마다 만드는 것만으로 AWS 권한이 분리되지는 않으며 작성·참조 권한과 role assumption 경계를 제한해야 합니다.

```yaml
apiVersion: aws.m.upbound.io/v1beta1
kind: ProviderConfig
metadata:
  name: team-aws
  namespace: team-alpha
spec:
  credentials:
    source: IRSA
```

![Core와 Provider controller의 역할](../.gitbook/assets/ko-platform-engineering-07-crossplane-1.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-07-crossplane-1.html)

## Namespace 범위 S3 예제

*.aws.m.upbound.io는 여기서 사용하는 namespace MR API입니다. 옛 *.aws.upbound.io cluster API와 구분합니다. providerConfigRef의 kind/name을 명시했고 Delete를 제외한 managementPolicies를 사용하여 외부 자원을 보존하도록 했습니다. 이 namespace API에는 기존 deletionPolicy 필드가 없습니다.

실제 bucket 이름·region·identity를 준비한 뒤 사용합니다. Delete를 제외해도 update는 가능하며, 보존은 backup이나 비용 정리를 뜻하지 않습니다.

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: Bucket
metadata:
  name: app-data
  namespace: team-alpha
  annotations:
    crossplane.io/external-name: replace-with-globally-unique-bucket
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    forceDestroy: false
    tags:
      Environment: Development
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: BucketPublicAccessBlock
metadata:
  name: app-data-public-access
  namespace: team-alpha
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    bucketRef:
      name: app-data
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: BucketVersioning
metadata:
  name: app-data-versioning
  namespace: team-alpha
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    bucketRef:
      name: app-data
    versioningConfiguration:
      status: Enabled
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

```yaml
apiVersion: s3.aws.m.upbound.io/v1beta1
kind: BucketServerSideEncryptionConfiguration
metadata:
  name: app-data-encryption
  namespace: team-alpha
spec:
  managementPolicies:
  - Observe
  - Create
  - Update
  - LateInitialize
  forProvider:
    region: us-west-2
    bucketRef:
      name: app-data
    rule:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  providerConfigRef:
    kind: ProviderConfig
    name: team-aws
```

Block Public Access 네 항목을 모두 켰습니다. versioningConfiguration과 applyServerSideEncryptionByDefault는 이 버전에서 객체이며 이전 배열 모양을 그대로 사용하지 않습니다. forceDestroy=false도 object/version이 남은 bucket 삭제와 함께 검토합니다.

## PostgreSQL 플랫폼 API

다음 예제는 이미 승인된 VPC, 서로 다른 AZ의 private subnet, client SecurityGroup, password Secret을 사용합니다. 네트워크 생성과 database 생성을 한 transaction으로 취급하지 않습니다. VPC/Subnet MR을 별도로 사용한다면 CIDR·route·egress·DNS·AZ를 함께 검증하세요.

새 XR은 namespace 안에 직접 생성합니다. dbName을 별도 입력으로 검증하며 metadata.name의 하이픈을 잘못된 Regexp transform으로 지우려 하지 않습니다. ProviderConfig 이름은 예제에서 team-aws로 제한했습니다.

```yaml
apiVersion: apiextensions.crossplane.io/v2
kind: CompositeResourceDefinition
metadata:
  name: postgresqldatabases.platform.example.com
spec:
  scope: Namespaced
  group: platform.example.com
  names:
    kind: PostgreSQLDatabase
    plural: postgresqldatabases
  versions:
  - name: v1alpha1
    served: true
    referenceable: true
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - parameters
            properties:
              parameters:
                type: object
                required:
                - environment
                - dbName
                - vpcID
                - subnetIDs
                - clientSecurityGroupID
                - passwordSecretName
                properties:
                  storageGB:
                    type: integer
                    minimum: 20
                    maximum: 1000
                    default: 50
                  environment:
                    type: string
                    enum:
                    - dev
                    - production
                  dbName:
                    type: string
                    pattern: ^[a-z][a-z0-9]{0,62}$
                  vpcID:
                    type: string
                  subnetIDs:
                    type: array
                    minItems: 2
                    items:
                      type: string
                  clientSecurityGroupID:
                    type: string
                  passwordSecretName:
                    type: string
                  providerConfigName:
                    type: string
                    default: team-aws
                    enum:
                    - team-aws
          status:
            type: object
            properties:
              endpoint:
                type: string
              port:
                type: integer
```

API version마다 served와 referenceable을 구분하고 referenceable version을 둘 이상으로 설정하지 않습니다. 이번 검토에서는 실제 CLI xrd convert로 Namespaced XRD가 CRD 1개, LegacyCluster+claimNames가 XR/Claim CRD 2개를 생성함을 확인했습니다. 변환은 cluster 설치나 데이터 migration이 아닙니다.

### Function pipeline

```yaml
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-patch-and-transform
spec:
  package: xpkg.crossplane.io/crossplane-contrib/function-patch-and-transform:v0.10.10
---
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-auto-ready
spec:
  package: xpkg.crossplane.io/crossplane-contrib/function-auto-ready:v0.7.0
```

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: postgresql-aws-reviewed
spec:
  compositeTypeRef:
    apiVersion: platform.example.com/v1alpha1
    kind: PostgreSQLDatabase
  mode: Pipeline
  pipeline:
  - step: patch-and-transform
    functionRef:
      name: function-patch-and-transform
    input:
      apiVersion: pt.fn.crossplane.io/v1beta1
      kind: Resources
      resources:
      - name: securityGroup
        base:
          apiVersion: ec2.aws.m.upbound.io/v1beta1
          kind: SecurityGroup
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              description: Application database security group
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - &id001
          type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.providerConfigName
          toFieldPath: spec.providerConfigRef.name
          policy:
            fromFieldPath: Required
        - &id002
          type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.tags.Environment
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.vpcID
          toFieldPath: spec.forProvider.vpcId
          policy:
            fromFieldPath: Required
      - name: securityGroupRule
        base:
          apiVersion: ec2.aws.m.upbound.io/v1beta1
          kind: SecurityGroupRule
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              type: ingress
              protocol: tcp
              fromPort: 5432
              toPort: 5432
              securityGroupIdSelector:
                matchControllerRef: true
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.providerConfigName
          toFieldPath: spec.providerConfigRef.name
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.clientSecurityGroupID
          toFieldPath: spec.forProvider.sourceSecurityGroupId
          policy:
            fromFieldPath: Required
      - name: subnetGroup
        base:
          apiVersion: rds.aws.m.upbound.io/v1beta1
          kind: SubnetGroup
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              description: Approved private database subnets
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - *id001
        - *id002
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.subnetIDs
          toFieldPath: spec.forProvider.subnetIds
          policy:
            fromFieldPath: Required
      - name: database
        base:
          apiVersion: rds.aws.m.upbound.io/v1beta1
          kind: Instance
          spec:
            managementPolicies:
            - Observe
            - Create
            - Update
            - LateInitialize
            forProvider:
              region: us-west-2
              engine: postgres
              engineVersion: '17.10'
              username: dbadmin
              storageType: gp3
              storageEncrypted: true
              publiclyAccessible: false
              skipFinalSnapshot: false
              dbSubnetGroupNameSelector:
                matchControllerRef: true
              vpcSecurityGroupIdSelector:
                matchControllerRef: true
              passwordSecretRef:
                name: replace-secret
                key: password
              port: 5432
            providerConfigRef:
              kind: ProviderConfig
              name: team-aws
        patches:
        - *id001
        - *id002
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.dbName
          toFieldPath: spec.forProvider.dbName
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.storageGB
          toFieldPath: spec.forProvider.allocatedStorage
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.passwordSecretName
          toFieldPath: spec.forProvider.passwordSecretRef.name
          policy:
            fromFieldPath: Required
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.instanceClass
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: db.t4g.medium
              production: db.r6g.large
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.multiAz
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: false
              production: true
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.deletionProtection
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: false
              production: true
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.environment
          toFieldPath: spec.forProvider.backupRetentionPeriod
          policy:
            fromFieldPath: Required
          transforms:
          - type: map
            map:
              dev: 7
              production: 30
        - type: FromCompositeFieldPath
          fromFieldPath: metadata.name
          toFieldPath: spec.forProvider.finalSnapshotIdentifier
          policy:
            fromFieldPath: Required
          transforms:
          - type: string
            string:
              type: Format
              fmt: '%s-final-review-before-delete'
        - type: FromCompositeFieldPath
          fromFieldPath: metadata.name
          toFieldPath: spec.writeConnectionSecretToRef.name
          policy:
            fromFieldPath: Required
          transforms:
          - type: string
            string:
              type: Format
              fmt: '%s-mr-connection'
        - type: ToCompositeFieldPath
          fromFieldPath: status.atProvider.address
          toFieldPath: status.endpoint
          policy:
            fromFieldPath: Optional
        - type: ToCompositeFieldPath
          fromFieldPath: status.atProvider.port
          toFieldPath: status.port
          policy:
            fromFieldPath: Optional
        connectionDetails:
        - name: endpoint
          type: FromFieldPath
          fromFieldPath: status.atProvider.address
        - name: username
          type: FromFieldPath
          fromFieldPath: spec.forProvider.username
  - step: readiness
    functionRef:
      name: function-auto-ready
```

Pipeline은 SG, SG ingress rule, SubnetGroup, RDS Instance를 계산합니다. selector의 matchControllerRef는 같은 XR 소유 관계를 사용하며 잘못된 metadata.uid label patch로 연결하지 않습니다. SG ingress는 전체 VPC CIDR이 아니라 승인된 client SG를 사용합니다.

환경 map은 Boolean·숫자 타입을 그대로 반환합니다. production 입력에서 db.r6g.large, Multi-AZ와 deletionProtection=true, backupRetentionPeriod=30을 실제 Function 실행으로 확인했습니다. 실제 region의 17.10 engine/class 지원과 storage 한도는 AWS에서 확인해야 합니다.

passwordSecretRef는 같은 namespace의 미리 준비한 rds-master-password/password를 참조합니다. 실제 비밀번호를 문서·CLI 인자·환경 변수에 넣지 않습니다. 예제는 autoGeneratePassword나 RDS-managed master password를 동시에 켜지 않습니다.

![환경별로 검증한 동일 Composition](../.gitbook/assets/ko-platform-engineering-07-crossplane-2.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-07-crossplane-2.html)

### 개발·운영 입력

```yaml
apiVersion: platform.example.com/v1alpha1
kind: PostgreSQLDatabase
metadata:
  name: orders-db
  namespace: team-alpha
spec:
  crossplane:
    compositionRef:
      name: postgresql-aws-reviewed
  parameters:
    environment: dev
    dbName: orders
    storageGB: 50
    vpcID: vpc-0123456789abcdef0
    subnetIDs:
    - subnet-0123456789abcdef0
    - subnet-0123456789abcdef1
    clientSecurityGroupID: sg-0123456789abcdef0
    passwordSecretName: rds-master-password
    providerConfigName: team-aws
```

```yaml
apiVersion: platform.example.com/v1alpha1
kind: PostgreSQLDatabase
metadata:
  name: orders-db
  namespace: team-alpha
spec:
  crossplane:
    compositionRef:
      name: postgresql-aws-reviewed
  parameters:
    environment: production
    dbName: orders
    storageGB: 200
    vpcID: vpc-0123456789abcdef0
    subnetIDs:
    - subnet-0123456789abcdef0
    - subnet-0123456789abcdef1
    clientSecurityGroupID: sg-0123456789abcdef0
    passwordSecretName: rds-master-password
    providerConfigName: team-aws
```

두 파일은 같은 이름의 XR에 대한 대체 입력입니다. 두 환경을 동시에 운영하려면 실제 namespace·이름·정책을 나눠야 합니다. spec.crossplane.compositionRef는 v2 관리 필드이며 기존 Claim의 spec.compositionRef와 혼동하지 않습니다.

## Connection Secret과 readiness

v2 XR의 core native connection publication은 제거됐습니다. MR의 writeConnectionSecretToRef는 남아 있으며, 이 namespace MR에서는 name만 지정합니다. P&T 0.10.10은 connectionDetails를 모아 Secret을 composed resource로 생성할 수 있습니다.

이 예제는 관찰된 RDS address와 username만 orders-db-connection에 넣습니다. password가 자동 포함된다고 주장하지 않습니다. 앱은 endpoint Secret과 별도로 준비한 password Secret을 파일로 mount하고 rotation·TLS·연결 재시도를 처리해야 합니다. Secret의 Base64는 암호화가 아닙니다.

외부 Secrets Manager로 값을 보내려면 적절한 PushSecret/provider 지원을 검토합니다. ExternalSecret은 기본적으로 외부 값을 Kubernetes로 가져오는 방향이며 원문의 반대 방향 예제는 잘못됐습니다.

![합성·관찰·상태와 Secret 처리](../.gitbook/assets/ko-platform-engineering-07-crossplane-3.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-07-crossplane-3.html)

새 리소스 렌더링에서는 Ready=False였고, 합성 관찰값에 Ready=True/address를 넣은 경우 XR 상태와 Secret이 생성됐습니다. 이 날짜·이름·상태는 로컬 시뮬레이션 결과이며 실제 AWS 생성 기록이 아닙니다. Native 렌더링 성공과 AWS 서비스 준비 상태를 구분합니다.

## 기존 리소스·삭제·업그레이드

기존 리소스를 가져올 때 external-name만 붙이고 Create/Update/Delete 전체 권한으로 시작하지 않습니다. 우선 provider가 지원하는 Observe 정책과 정확한 식별자·region·소유권을 확인한 뒤 원하는 필드를 검토해 관리 범위를 늘립니다. initProvider와 forProvider의 조정 의미도 구분하세요.

Namespace MR에서는 managementPolicies에서 Delete를 제외하는 보존 방식을 사용합니다. legacy MR의 deletionPolicy: Orphan과 구분하며, []·Observe·Create·Update 등의 의미와 실제 provider 지원을 확인합니다. RDS deletionProtection, final snapshot, backup은 별도 계층입니다. finalSnapshotIdentifier는 기존 snapshot과 충돌하지 않도록 실제 삭제 전에 검토해야 합니다.

XR을 삭제하면 MR과 composed Secret이 사라질 수 있지만 Delete를 제외한 AWS 리소스는 남을 수 있습니다. 그래서 보존된 database의 credential·backup·후속 소유권도 준비해야 합니다. Usage/ClusterUsage는 현재 protection.crossplane.io API와 대상 scope를 확인하고, 원문의 alpha Usage를 새 기본값으로 사용하지 않습니다.

core/provider/function을 각각 pin하고 revision·CRD·IAM 변경을 검증합니다. API group을 기존 live Composition에서 namespace API로 단순 치환하면 자원이 재생성될 수 있습니다. 새 Composition과 별도의 이전 절차를 사용합니다. 명시적인 snapshot/restore·데이터 검증 없이 “무중단 업그레이드”로 표시하지 않습니다.

## 관찰과 조정 주기

검토한 AWS provider는 --poll 기본 10m, --sync 기본 1h이며 poll jitter도 적용합니다. --max-reconcile-rate는 전역 rate와 해당 구현의 concurrency 설정에 사용되므로 단순 고정 concurrency 숫자로만 설명하지 않습니다. 이 값들은 ProviderConfig의 IRSA 설정이 아니라 provider runtime 설정입니다.

core chart metrics.enabled=true와 provider DRC의 실제 Pod label/metrics port를 연결한 예제입니다. Prometheus Operator 및 scraper 설정은 별도 전제입니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: crossplane
  namespace: crossplane-system
spec:
  jobLabel: app
  selector:
    matchLabels:
      app: crossplane
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: provider-aws-s3
  namespace: crossplane-system
spec:
  jobLabel: app
  selector:
    matchLabels:
      app: provider-aws-s3-reviewed
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
```

ProviderRevision 이름이 바뀌는 label을 고정값으로 selector에 넣지 않습니다. kube_customresource_status_condition은 자동으로 생기는 Crossplane 기본 메트릭이 아니며 kube-state-metrics custom resource 설정 등이 필요합니다. 실제 metric 이름·label을 확인한 후 counter에는 rate/increase, histogram에는 올바른 le 집계를 사용하세요.

## ACK·Backstage·GitOps

ACK 리소스도 namespace 범위이며 kro 등으로 조합할 수 있습니다. ACK가 cluster CR만 제공한다거나 CNCF 프로젝트라는 비교는 잘못됐습니다. Crossplane의 namespace도 IAM·ProviderConfig·Composition 작성 권한을 대신하지 않습니다. 동일 외부 리소스를 ACK·Terraform·Crossplane이 동시에 수정하지 않게 소유권을 정합니다.

Backstage의 준비된 skeleton/action으로 XR YAML을 만들고 검토된 GitOps PR을 거쳐 ArgoCD가 적용하도록 합니다. PR을 만들었다고 database가 생성된 것은 아니고, merge 전 main에 없는 파일을 catalog에 등록하지 않습니다. Git history와 AWS API 감사 로그도 별도입니다. ArgoCD prune은 외부 리소스의 삭제·보존 정책과 함께 검토합니다.

![검토한 GitOps 변경에서 XR 조정까지](../.gitbook/assets/ko-platform-engineering-07-crossplane-4.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-07-crossplane-4.html)

## 검증 범위

원문 본문 한국어 1,958줄·영어 1,827줄, 각 퀴즈 143줄과 고유 fenced block 83개 및 추가 indented block을 읽었습니다. 공식 CLI/core 2.4.0과 P&T 0.10.10, auto-ready 0.7.0을 checksum/source 기준으로 준비했습니다.

localhost의 실제 Function과 core render engine으로 dev/prod/관찰 상태 3사례를 렌더링했습니다. 공식 CLI의 API-server 검증 라이브러리로 MR, XR, DRC·Provider를 검사했고, 기본 Secret schema는 별도 공식 Kubernetes OpenAPI로 검사했습니다. 잘못된 dbName/provider/storage 입력도 거부됐습니다. 함수 프로세스는 검증 후 종료했습니다.

AWS/Kubernetes 자원 생성, 실제 RDS·network·IAM 인증, backup/restore·HA·부하·Prometheus scrape는 실행하지 않았습니다. 로컬 결과를 운영 배포 성공으로 표시하지 않습니다.

- [Crossplane 2.4](https://docs.crossplane.io/v2.4/)
- [Upgrade to v2](https://docs.crossplane.io/latest/guides/upgrade-to-crossplane-v2/)
- [Connection details](https://docs.crossplane.io/v2.4/guides/connection-details-composition/)
- [AWS provider 2.7.0](https://github.com/crossplane-contrib/provider-upjet-aws/tree/v2.7.0)
- [Patch and Transform 0.10.10](https://github.com/crossplane-contrib/function-patch-and-transform/tree/v0.10.10)
- [CNCF](https://www.cncf.io/projects/crossplane/)

[Crossplane 퀴즈](../quizzes/platform-engineering/07-crossplane-quiz.md)
