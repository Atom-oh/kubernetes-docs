# Backstage를 활용한 내부 개발자 포털

> **마지막 업데이트**: 2026년 9월 12일 · Backstage 1.54.7 / Helm chart 2.10.0

## 역할과 도입 범위

Backstage는 Spotify에서 시작된 오픈소스 개발자 포털 프레임워크이며 Apache 2.0 라이선스입니다. CNCF 프로젝트 페이지는 Incubating 상태로 안내합니다. 포털은 IDP의 사용자 접점이 될 수 있지만 인프라·배포·정책·운영 자동화 전체를 대신하지 않습니다.

Software Catalog는 소유권·API·리소스 관계를, Software Templates는 준비된 action과 skeleton의 실행을, TechDocs는 문서 빌드·게시·열람을 제공합니다. Search는 구성한 collator와 backend의 인덱싱이 필요합니다. 코드와 문서를 같은 저장소에 둔다고 내용이 자동으로 최신화되지는 않습니다.

Port, Cortex, Humanitec, OpsLevel 같은 제품과 비교할 때 hosting, 데이터 경계, 확장 API, 유지보수 인력·구독·인프라 비용을 현재 제품 조건으로 평가합니다. 검증하지 않은 플러그인 수·도입 조직 수·최고 점수나 “인프라 비용만 든다”는 비교표는 사용하지 않습니다. Backstage의 라이선스와 실제 운영 비용도 구분합니다.

## 아키텍처와 플러그인

React frontend와 Node.js backend가 catalog, scaffolder, auth, TechDocs 등의 플러그인을 조합합니다. frontend/backend 모듈의 설치·등록이 필요하며 서로 별도 배포·보안 격리를 보장하는 것은 아닙니다. legacy EntityPage와 새 frontend extension API는 선택한 app 구조에 맞춰 사용합니다.

![Backstage 프론트엔드·백엔드와 외부 연동](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-0.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-06-backstage-idp-0.html)

## 앱 생성·빌드와 버전

Backstage release 번호, 개별 npm package 버전, Helm chart 버전과 직접 빌드하는 image revision은 서로 다릅니다. 1.54.7 소스는 Node.js 22 또는 24를 요구합니다. 기존 Node 20 Dockerfile을 새 기본값으로 사용하지 않습니다.

검토한 create-app package는 0.9.1입니다. 생성 후 lockfile·packageManager와 실제 frontend/backend 구조를 확인합니다. 아래 명령은 앱을 생성·빌드할 때의 흐름이며 이번 검토에서 전체 Backstage 앱을 빌드하지는 않았습니다.

```bash
npx @backstage/create-app@0.9.1
# In the generated app, using its supported Node/Yarn versions:
yarn install --immutable
yarn tsc
yarn build:backend
```

생성된 packages/backend/Dockerfile을 기준으로 검토합니다. 현재 template은 skeleton.tar.gz를 풀어 production dependency를 설치하고 bundle.tar.gz를 풀어 packages/backend를 실행합니다. dist 디렉터리만 복사하여 node packages/backend/dist로 실행하는 기존 예제는 이 bundle 형식과 맞지 않습니다.

host build와 container의 Node major/native ABI를 맞추고 실제 OS/architecture image를 검증합니다. 기존 node 사용자의 UID 1000과 충돌하는 사용자를 또 만들지 않습니다. ECR repository·push 권한과 image digest/배포 경로는 별도로 준비하고 credential을 image·build arg·환경 변수에 넣지 않습니다. external TechDocs builder를 쓰면 모든 reader image에서 MkDocs 빌드 도구를 실행할 필요가 없습니다.

## EKS 설정: 파일 기반 credential

다음은 구성 예제입니다. example.invalid와 승인 조직·bucket·OIDC client 값은 치환해야 합니다. PostgreSQL, provider, GitHub, S3에 실제 연결한 결과가 아닙니다.

Secret은 승인된 provider/ESO 등으로 backstage-credentials에 준비하고 파일로 mount합니다. app-config의 `$file`은 실제 Backstage loader가 읽으며 끝의 줄바꿈을 제거합니다. 설정 파일과 마운트 경로를 맞추고, rotation 이후 각 plugin이 언제 새 값을 읽는지 확인합니다. subPath mount나 시작 시 고정된 설정은 rollout이 필요할 수 있습니다.

이 DB 예제는 하나의 PostgreSQL database 안에서 plugin별 schema를 사용합니다. database/schema를 미리 준비하도록 ensureExists/ensureSchemaExists를 껐습니다. 같은 credential로 구분한 schema가 별도 보안 경계가 되는 것은 아닙니다. migrations에 필요한 권한과 connection pool의 **plugin 수 × replica 수**에 따른 최대 연결을 검토하세요. RDS CA를 검증하고 TLS 검증을 끄지 않습니다.

```yaml
app:
  title: Example Developer Portal
  baseUrl: https://backstage.example.com
backend:
  baseUrl: https://backstage.example.com
  listen:
    port: 7007
  cors:
    origin: https://backstage.example.com
    credentials: true
  database:
    client: pg
    pluginDivisionMode: schema
    ensureExists: false
    ensureSchemaExists: false
    connection:
      host: backstage-db.example.invalid
      port: 5432
      database: backstage
      user: backstage
      password:
        $file: /var/run/backstage-secrets/postgres-password
      ssl:
        rejectUnauthorized: true
        ca:
          $file: /var/run/backstage-public/rds-ca.pem
    knexConfig:
      pool:
        min: 0
        max: 10
  auditor:
    severityLogLevelMappings:
      low: debug
      medium: info
      high: warn
      critical: error
auth:
  environment: production
  session:
    secret:
      $file: /var/run/backstage-secrets/auth-session-secret
  providers:
    oidc:
      production:
        metadataUrl: https://issuer.example.invalid/.well-known/openid-configuration
        clientId: replace-with-approved-client-id
        clientSecret:
          $file: /var/run/backstage-secrets/oidc-client-secret
        additionalScopes: [profile, email]
        signIn:
          resolvers:
            - resolver: emailMatchingUserEntityProfileEmail
permission:
  enabled: true
integrations:
  github:
    - host: github.com
      token:
        $file: /var/run/backstage-secrets/github-token
catalog:
  providers:
    github:
      approvedOrg:
        organization: replace-approved-org
        catalogPath: /catalog-info.yaml
        filters:
          branch: main
          repository: "^approved-.*$"
        schedule:
          frequency: {minutes: 30}
          timeout: {minutes: 3}
  rules:
    - allow: [Component, API, Resource, System, Domain, Group, User, Template, Location]
techdocs:
  builder: external
  publisher:
    type: awsS3
    awsS3:
      bucketName: replace-approved-techdocs-bucket
      region: us-west-2
```

RDS IAM authentication도 현재 backend가 지원하지만 필요한 signer package, rds-db:connect, DB 사용자와 TLS를 별도로 구성해야 합니다. 이 문서의 password-file 예제와 자동으로 혼합하지 않습니다.

## Helm 배포 구성과 HA

운영 image는 직접 빌드한 Backstage 앱이어야 합니다. 아래 example.invalid image는 placeholder입니다. ServiceAccount, credential Secret, RDS CA ConfigMap과 app-config ConfigMap을 준비한 후 사용합니다. 공개 ingress는 기본으로 생성하지 않았습니다. 승인된 내부 또는 CloudFront 앞단 경로, 인증·TLS·네트워크 접근 제어는 별도 운영 구성입니다.

```yaml
fullnameOverride: backstage
backstage:
  image:
    registry: example.invalid
    repository: backstage
    tag: replace-with-reviewed-app-revision
  replicas: 3
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: "1"
      memory: 1Gi
  extraEnvVarsSecrets: []
  extraAppConfig:
    - filename: app-config.production.yaml
      configMapRef: backstage-app-config
  extraVolumeMounts:
    - name: credentials
      mountPath: /var/run/backstage-secrets
      readOnly: true
    - name: public-config
      mountPath: /var/run/backstage-public
      readOnly: true
  extraVolumes:
    - name: credentials
      secret:
        secretName: backstage-credentials
    - name: public-config
      configMap:
        name: backstage-public-config
  readinessProbe:
    httpGet:
      path: /.backstage/health/v1/readiness
      port: 7007
  livenessProbe:
    httpGet:
      path: /.backstage/health/v1/liveness
      port: 7007
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
serviceAccount:
  create: false
  name: backstage
  automountServiceAccountToken: false
postgresql:
  enabled: false
ingress:
  enabled: false
```

examples/platform/backstage/app-config-configmap.yaml은 위 app-config를 data.app-config.production.yaml로 담습니다. extraAppConfig의 filename과 configMapRef에 일치하며 Secret 값 대신 파일 참조만 포함합니다.

```bash
helm template backstage backstage/backstage   --version 2.10.0 --namespace backstage   -f examples/platform/backstage/helm-values.yaml
```

Helm repository는 공식 backstage.github.io/charts를 먼저 등록합니다. 검토에서는 해당 chart를 내려받아 로컬에서 렌더링했습니다. ServiceAccount는 chart의 최상위 serviceAccount이며 backstage.serviceAccount가 아닙니다. chart 2.10.0에서 기존 backstage.podDisruptionBudget 값은 PDB를 만들지 않으므로 아래 리소스를 별도로 준비합니다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: backstage
  namespace: backstage
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: backstage
      app.kubernetes.io/instance: backstage
```

health 경로는 /.backstage/health/v1/readiness와 liveness입니다. ALB health check도 실제 경로에 맞춥니다. replica 3개나 PDB만으로 AZ 분산·DB HA·무중단이 보장되지는 않습니다. topology spread/anti-affinity, shared PostgreSQL·auth session 설정, background task 처리와 upgrade migration을 검증해야 합니다.

## OIDC 로그인과 신원 연결

OIDC provider module을 backend에 등록하고 frontend sign-in도 구성합니다. metadataUrl은 신뢰한 issuer의 discovery이며 Cognito user pool 또는 Okta issuer에 맞춰 설정합니다. 현재 provider의 추가 scope는 additionalScopes입니다.

emailMatchingUserEntityProfileEmail은 catalog 사용자를 찾아 연결하는 예입니다. issuer·email 검증·사용자 등록 경계와 중복 email을 점검하고, 외부 claim을 임의 catalog 관리자 신원으로 연결하지 않습니다. dangerouslyAllowSignInWithoutUserInCatalog를 켜지 않습니다. built-in provider와 같은 provider ID의 custom resolver module을 동시에 중복 등록하지 않습니다.

## Software Catalog

아래 8개 엔티티는 7가지 kind를 포함하며 owner/system/domain 참조가 서로 연결됩니다. Component의 dependsOn에서 Resource 관계를 선언합니다. 임의 dependencyOf 필드를 써서 backend가 관계를 자동 처리한다고 가정하지 않습니다. Resource 등록은 실제 AWS 리소스 생성이 아닙니다.

![카탈로그 구조와 소유권 예제](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-1.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-06-backstage-idp-1.html)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Domain
metadata:
  name: commerce
spec:
  owner: group:default/platform-team
---
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: order-system
spec:
  owner: group:default/backend-team
  domain: commerce
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: order-api
  annotations:
    backstage.io/techdocs-ref: dir:.
    backstage.io/kubernetes-id: order-api
    backstage.io/kubernetes-namespace: production
    github.com/project-slug: replace-approved-org/order-api
    argocd/app-name: order-api
spec:
  type: service
  lifecycle: production
  owner: group:default/backend-team
  system: order-system
  providesApis:
  - order-rest-api
  dependsOn:
  - resource:default/order-db
---
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: order-rest-api
spec:
  type: openapi
  lifecycle: production
  owner: group:default/backend-team
  system: order-system
  definition: "openapi: 3.0.3\ninfo:\n  title: Order API\n  version: 1.0.0\npaths:\n\
    \  /orders:\n    get:\n      responses:\n        \"200\":\n          description:\
    \ Orders returned\n"
---
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: order-db
spec:
  type: database
  owner: group:default/backend-team
  system: order-system
---
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: platform-team
spec:
  type: team
  children: []
---
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: backend-team
spec:
  type: team
  children: []
  members:
  - alice
---
apiVersion: backstage.io/v1alpha1
kind: User
metadata:
  name: alice
spec:
  profile:
    displayName: Alice
    email: alice@example.com
  memberOf:
  - backend-team
```

GitHub discovery는 integration credential과 catalog-backend-module-github 등록이 필요합니다. catalogPath, branch/repository filter와 schedule을 실제 조직에 맞춥니다. 모든 repository·임의 Location을 허용하면 읽기 범위와 template 실행 입력이 넓어지므로 신뢰한 source를 제한합니다. backend 파일 location은 container의 실제 경로와 일치해야 하며 glob 문자열만 적었다고 모두 등록되는 것은 아닙니다.

## Software Templates와 GitOps

아래 template은 **카탈로그와 TechDocs 파일만 만드는 완전한 작은 skeleton**입니다. 앱·Dockerfile·Helm·CI가 모두 구현된 마이크로서비스라고 표시하지 않습니다. runtime golden path를 만들려면 선택한 언어마다 실제 소스, 테스트, image build, chart, 환경별 values와 CI가 필요합니다. 입력 checkbox만 추가해도 DB/HPA가 생기는 것은 아닙니다.

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: reviewed-documentation-starter
  title: Reviewed documentation starter
  description: Creates a catalog and TechDocs skeleton; it does not deploy an application.
spec:
  owner: group:default/platform-team
  type: documentation
  parameters:
    - title: Service metadata
      required: [name, description, owner, repoUrl]
      properties:
        name:
          type: string
          pattern: "^[a-z][a-z0-9-]{1,38}[a-z0-9]$"
        description:
          type: string
          maxLength: 200
        owner:
          type: string
          enum: [group:default/backend-team, group:default/platform-team]
        repoUrl:
          type: string
          ui:field: RepoUrlPicker
          ui:options:
            allowedHosts: [github.com]
            allowedOwners: [replace-approved-org]
  steps:
    - id: fetch
      name: Render the complete documentation skeleton
      action: fetch:template
      input:
        url: ./skeleton
        values:
          name: ${{ parameters.name }}
          description: ${{ parameters.description }}
          owner: ${{ parameters.owner }}
    - id: publish
      name: Create the approved repository
      action: publish:github
      input:
        repoUrl: ${{ parameters.repoUrl }}
        allowedHosts: [github.com]
        repoVisibility: private
        defaultBranch: main
        description: ${{ parameters.description }}
    - id: register
      name: Register the published catalog entity
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps.publish.output.repoContentsUrl }}
        catalogInfoPath: /catalog-info.yaml
  output:
    links:
      - title: Repository
        url: ${{ steps.publish.output.remoteUrl }}
      - title: Catalog
        entityRef: ${{ steps.register.output.entityRef }}
```

template/skeleton에는 catalog-info.yaml, mkdocs.yml, docs/index.md 세 파일이 있습니다. description·owner는 dump로 YAML 문자열을 안전하게 표현하며 줄바꿈/따옴표도 검증했습니다. OwnerPicker의 entityRef는 GitHub team slug와 다르므로 문자열 치환만으로 collaborator 권한을 부여하지 않습니다. RepoUrlPicker의 제한은 UI 기능이며 GitHub App/token 권한과 backend action 검증을 대신하지 않습니다.

publish:github에는 GitHub action module 등록이 필요하고, 등록한 실제 action 목록과 input schema를 확인해야 합니다. 이 예제는 repository 게시 후 catalog:register를 호출합니다. infrastructure PR을 만드는 publish:github:pull-request 흐름에서는 PR 생성 직후 아직 main에 없는 파일을 등록하지 말고 merge 후 discovery/등록을 수행합니다.

ACK/kro의 DatabaseClaim은 built-in kind가 아닙니다. 미리 검증한 RGD/CRD·controller·RBAC가 있어야 하며 [ACK](02-ack.md), [kro](03-kro.md), [앱 통합](05-example-corp-app.md)의 현재 예제를 사용합니다. catalog entityRef에는 ':'와 '/'가 있으므로 그대로 Kubernetes label 값에 넣지 않습니다.

ArgoCD의 @roadiehq/scaffolder-backend-argocd 1.8.1은 argocd:create-resources action을 제공합니다. appName, argoInstance, namespace, repoUrl, path가 필요하며 projectName/labelValue는 선택입니다. namespace는 배포 대상 namespace이고, 기존 예제의 revision은 이 action의 입력 schema에 없습니다. backend module과 ArgoCD token을 구성하고 AppProject·destination·repository 권한을 제한합니다. 저장소 생성과 ArgoCD API 호출은 이번 검증에서 하지 않았습니다.

GitHub Actions skeleton에서는 Backstage의 Nunjucks 표현식과 GitHub의 표현식을 구분합니다. 예전 contents:read 상태에서 git push하던 CI는 동작하지 않으며 자기 커밋으로 반복 실행될 수 있습니다. 검증한 image digest를 별도의 GitOps PR로 제안하고 CI 인증·branch protection·merge 조건을 갖춘 흐름을 사용합니다.

## TechDocs와 S3

external builder에서는 CI가 문서를 빌드·게시하고 Backstage backend가 S3에서 읽습니다. reader와 publisher IAM 역할을 구분하며 runtime reader에 PutObject/DeleteObject를 기본으로 주지 않습니다. S3 Block Public Access 네 항목을 켜고 KMS를 사용하면 key policy와 필요한 권한도 맞춥니다. ACK 필드명은 blockPublicACLs/ignorePublicACLs입니다.

![CI 게시와 backend를 통한 문서 읽기](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-2.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-06-backstage-idp-2.html)

현재 TechDocs의 credentials.roleArn은 지원되지만 deprecated 구성입니다. 예제에서는 이를 생략하고 준비된 workload identity/SDK credential 경로를 사용합니다. 필요한 경우 aws account 설정을 통한 provider 구성을 따릅니다. bucketRootPath를 reader와 publisher에서 일치시키고 entity key의 namespace/kind/name과 대소문자를 실제 CLI에서 확인합니다.

작은 skeleton의 MkDocs/techdocs-core strict build를 실제 실행했습니다. 모든 서비스 문서를 빌드한 결과는 아닙니다. CI 게시에는 신뢰한 branch/event, id-token:write, 제한된 OIDC trust와 publisher 권한이 필요하며 이 검토에서는 S3에 업로드하지 않았습니다.

## Kubernetes·ArgoCD·비용 플러그인

Kubernetes plugin에는 frontend/backend 등록, 실제 cluster endpoint와 CA, 인증 방식·RBAC가 필요합니다. long-lived ServiceAccount token을 출력해 환경 변수에 복사하는 기존 예제는 사용하지 않습니다. EKS AWS auth provider를 쓰려면 workload identity, target role/EKS access와 Kubernetes 권한을 구성하고 x-k8s-aws-id를 실제 cluster 이름에 맞춥니다.

서버 측 cluster credential은 Backstage 사용자들이 공유할 수 있습니다. multiTenant locator나 catalog의 namespace/id label은 접근 제어 경계가 아닙니다. 사용자별 데이터 범위, backend permission coverage와 cluster RBAC를 검토합니다. Kubernetes metadata label selector와 catalog annotation을 맞추고, Pod log는 pods/log 권한과 해당 기능 구성이 필요합니다. customResources에 KEDA/Karpenter를 추가하는 것만으로 전용 scaling UI가 생기지 않으며 실제 CRD status 필드를 사용해야 합니다.

ArgoCD UI/plugin과 scaffolder action은 별도 package·등록·권한입니다. 검토한 Roadie UI package는 2.12.5입니다. 예전 @kubecost/backstage-plugin 및 backend package 이름은 npm에서 404를 반환했습니다. 설치 가능한 것처럼 명령을 유지하지 않고, 유지되는 integration 또는 검증한 비용 API adapter를 선정하도록 합니다. 비용 계산의 범위·배분·가격 기준도 UI 카드와 별도로 확인합니다.

## Permission Framework

permission.enabled:true만으로 팀 정책이 설치되지는 않습니다. 아래 module을 backend에 등록하고 allow-all policy module과 경쟁 등록하지 않습니다. 현재 PermissionPolicy의 PolicyQueryUser와 AuthService/UserInfoService를 사용하며 deprecated user.info 또는 과거 user.identity 구조에 의존하지 않습니다.

이 예제는 신뢰한 platform-team을 admin으로, catalog read를 인증 사용자에게, catalog delete를 owner 조건으로 허용하고 나머지를 DENY합니다. 전체 포털 기능을 허용하는 완성 정책이 아니므로 필요한 action을 하나씩 명시적으로 추가해야 합니다. Group/User source를 일반 사용자가 변경해 권한을 높이지 못하게 보호합니다.

![현재 예제의 허용·거부·조건부 판정](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-3.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-platform-engineering-06-backstage-idp-3.html)

```typescript
import {
  AuthorizeResult,
  isPermission,
  type PolicyDecision,
} from '@backstage/plugin-permission-common';
import type {
  PermissionPolicy,
  PolicyQuery,
  PolicyQueryUser,
} from '@backstage/plugin-permission-node';
import {
  catalogEntityDeletePermission,
  catalogEntityReadPermission,
} from '@backstage/plugin-catalog-common/alpha';
import {
  coreServices,
  createBackendModule,
  type AuthService,
  type UserInfoService,
} from '@backstage/backend-plugin-api';
import { policyExtensionPoint } from '@backstage/plugin-permission-node/alpha';

export class TeamPolicy implements PermissionPolicy {
  constructor(
    private readonly userInfo: UserInfoService,
    private readonly auth: Pick<AuthService, 'isPrincipal'>,
  ) {}

  async handle(
    request: PolicyQuery,
    user?: PolicyQueryUser,
  ): Promise<PolicyDecision> {
    if (!user || !this.auth.isPrincipal(user.credentials, 'user')) {
      return { result: AuthorizeResult.DENY };
    }
    const { ownershipEntityRefs } = await this.userInfo.getUserInfo(
      user.credentials,
    );
    if (ownershipEntityRefs.includes('group:default/platform-team')) {
      return { result: AuthorizeResult.ALLOW };
    }
    if (isPermission(request.permission, catalogEntityReadPermission)) {
      return { result: AuthorizeResult.ALLOW };
    }
    if (
      isPermission(request.permission, catalogEntityDeletePermission) &&
      ownershipEntityRefs.length > 0
    ) {
      return {
        result: AuthorizeResult.CONDITIONAL,
        pluginId: 'catalog',
        resourceType: 'catalog-entity',
        conditions: {
          resourceType: 'catalog-entity',
          rule: 'IS_ENTITY_OWNER',
          params: { claims: ownershipEntityRefs },
        },
      };
    }
    // Add explicit grants for required plugin actions after reviewing their scope.
    return { result: AuthorizeResult.DENY };
  }
}

export const teamPolicyModule = createBackendModule({
  pluginId: 'permission',
  moduleId: 'reviewed-team-policy',
  register(reg) {
    reg.registerInit({
      deps: {
        policy: policyExtensionPoint,
        userInfo: coreServices.userInfo,
        auth: coreServices.auth,
      },
      async init({ policy, userInfo, auth }) {
        policy.setPolicy(new TeamPolicy(userInfo, auth));
      },
    });
  },
});
```

CONDITIONAL은 catalog backend가 실제 entity 관계에 적용해야 합니다. catalog entity 삭제와 GitHub 저장소 수정·ArgoCD 배포 권한은 별개입니다. “소유자만 모든 수정 가능”이라는 일반 규칙으로 확대하지 않습니다. 정책 8사례는 mock 신원 서비스로 검사했으며 실제 OIDC 로그인이나 catalog ownership evaluator를 실행한 것은 아닙니다.

## 감사·복구·업그레이드

현재 core Auditor Service는 기본 rootLogger에 기록하고 backend.auditor.severityLogLevelMappings로 수준을 설정합니다. 기존 backend.audit나 backend.events.modules의 awsCloudWatch 설정이 자동 감사 수집을 구성한다는 설명은 잘못됐습니다. plugin이 실제로 발행하는 event와 누락 범위를 확인하고, 로그 pipeline을 별도로 CloudWatch 등으로 전달합니다. Secret·개인정보가 event metadata에 포함되지 않도록 설계합니다.

PostgreSQL snapshot/PITR, TechDocs versioning·복제·lifecycle, config·catalog source와 secret provider 복구를 실제 RPO/RTO에 맞춰 설계합니다. 동일 DB의 schema 구분, Aurora replica 또는 S3 복제만으로 완전한 격리·backup·자동 failover가 되지는 않습니다. Aurora cluster 복원은 DB instance와 subnet/security group, endpoint 전환도 검증해야 합니다.

업그레이드에서는 release notes와 plugin compatibility를 확인하고 versions:bump, lockfile, 타입 검사·테스트·실제 image·staging DB migration을 함께 검증합니다. 존재하지 않는 일반 backstage-cli db:migrate 명령을 가정하지 말고 plugin/backend의 migration lifecycle을 따릅니다. 이전 image로 돌아가도 DB schema가 자동 복원되지는 않습니다.

## 검증 범위

원문 한국어 2,279줄·영어 2,226줄, 각 퀴즈 143줄과 118개 고유 code block을 모두 읽었습니다. 공식 chart 렌더링, 실제 config loader 파일 참조 5개, catalog-model 엔티티 8개/잘못된 입력 1개, 타입 검사 및 정책 8사례, template 문자열 2사례와 작은 TechDocs build를 수행했습니다.

전체 Backstage app/Docker image, PostgreSQL/OIDC, GitHub/ArgoCD/Kubernetes/AWS API, 실제 template action 실행·배포·부하·HA는 검증하지 않았습니다. placeholder와 운영자가 준비할 경로를 명시했습니다.

- [Backstage 1.54.7](https://github.com/backstage/backstage/tree/v1.54.7)
- [Helm chart 2.10.0](https://github.com/backstage/charts/releases/tag/backstage-2.10.0)
- [Configuration](https://backstage.io/docs/conf/writing/)
- [Kubernetes authentication](https://backstage.io/docs/features/kubernetes/authentication/)
- [Permission policy](https://backstage.io/docs/permissions/writing-a-policy/)
- [Auditor](https://backstage.io/docs/backend-system/core-services/auditor/)
- [TechDocs](https://backstage.io/docs/features/techdocs/configuration/)
- [CNCF project](https://www.cncf.io/projects/backstage/)

[Backstage 퀴즈](../quizzes/platform-engineering/06-backstage-idp-quiz.md)
