# Backstage 作为内部开发者门户

> **最后更新**：October 16, 2026 · Backstage 1.54.7 / Helm chart 2.10.2

## 角色与采用范围

Backstage 是一个源自 Spotify、采用 Apache 2.0 许可证的开源开发者门户框架。CNCF 将其列为孵化项目。门户可以作为 IDP 面向用户的部分；它并不能取代所有基础设施、交付、策略或运维自动化。

Software Catalog 用于建模所有权、API 和资源关系。Software Templates 可在准备好的骨架上执行已配置的操作。TechDocs 负责文档构建、发布和阅读。Search 需要配置整理器和索引后端。将代码和文档放在一起，并不会自动确保内容保持最新。

比较 Port、Cortex、Humanitec、OpsLevel 或其他产品时，应评估其当前托管方式、数据边界、扩展 API，以及人员、订阅和基础设施成本。避免使用未经验证的插件/采用数量、普遍排名，或声称 Backstage 只产生基础设施成本。许可证条款与运营成本是不同的问题。

## 架构与插件

React 前端和 Node.js 后端由 catalog、scaffolder、auth 和 TechDocs 插件组成。安装并注册所需模块。插件本身并不提供独立部署或安全隔离。应根据所选的应用架构使用旧版 EntityPage 或新版前端扩展 API。

![Backstage 前端、后端和集成](../.gitbook/assets/en-platform-engineering-06-backstage-idp-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-06-backstage-idp-0.html)

## 应用创建、构建与版本

Backstage 发布版本、单个 npm 软件包版本、Helm chart 版本和自定义镜像修订版本是不同的值。1.54.7 版需要 Node.js 22 或 24；之前的 Node 20 Dockerfile 并非当前默认配置。

检查过的 create-app 软件包版本为 0.9.1。生成后，请检查其 lockfile、packageManager 以及前端/后端结构。这些命令描述了应用构建流程；本次审计未构建完整的 Backstage 应用。

```bash
npx @backstage/create-app@0.9.1
# In the generated app, using its supported Node/Yarn versions:
yarn install --immutable
yarn tsc
yarn build:backend
```

检查生成的 packages/backend/Dockerfile。当前模板会提取 skeleton.tar.gz、安装生产依赖、提取 bundle.tar.gz 并运行 packages/backend。仅复制 dist 并运行 node packages/backend/dist 与该 bundle 格式不符。

确保主机/容器的 Node 主版本和原生模块 ABI 一致，并验证操作系统/架构镜像。不要创建与镜像中的 node 用户冲突的第二个 UID-1000 用户。单独准备 ECR/推送权限和镜像摘要；不要将凭证写入镜像、构建参数或环境变量。使用外部 TechDocs 构建时，reader 镜像无需运行文档构建工具链。

## 使用凭证文件配置 EKS

以下是一个配置示例。请替换 example.invalid 以及经批准的组织、存储桶和 OIDC 客户端值。此示例不代表已连接 PostgreSQL、身份提供商、GitHub 或 S3。

通过经批准的 provider/ESO 流程准备 backstage-credentials，并将其作为文件挂载。Backstage 的实际加载器会解析 `$file` 并去除末尾换行符。请确保配置路径与挂载路径一致，并验证各插件何时重新读取轮换后的值。SubPath 挂载和仅在启动时读取的配置可能需要滚动更新。

此示例将一个 PostgreSQL 数据库划分为多个插件 schema。ensureExists/ensureSchemaExists 已禁用，因此必须预先准备 schema/数据库。通过同一凭证访问的 schema 并非独立的安全边界。检查迁移权限，并汇总 **插件数 × 副本数** 所产生的连接池连接数。验证 RDS CA，并保持 TLS 验证启用。

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

后端也支持 RDS IAM 身份验证，但需要 signer 软件包、rds-db:connect、数据库用户配置和 TLS。不要自动将该流程与密码文件示例混用。

## Helm 配置与高可用

构建包含已配置 Backstage 应用的镜像。下面的 example.invalid 镜像是占位符。请先准备 ServiceAccount、凭证 Secret、RDS CA ConfigMap 和 app-config ConfigMap。默认不会创建公共 ingress；经批准的内部访问或经 CloudFront 接入的访问、身份验证、TLS 和网络控制仍是运维要求。

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

examples/platform/backstage/app-config-configmap.yaml 会将该配置存储在 data.app-config.production.yaml 下。它与 extraAppConfig 的 filename/configMapRef 相匹配，并包含文件引用，而非 Secret 值。

```bash
helm template backstage backstage/backstage   --version 2.10.2 --namespace backstage   -f examples/platform/backstage/helm-values.yaml
```

请先注册官方 backstage.github.io/charts 仓库。本次审计在本地下载并渲染了该 chart。serviceAccount 是 chart 顶层值，而不是 backstage.serviceAccount。之前的 backstage.podDisruptionBudget 值不会在 chart 2.10.2 中创建 PDB；请单独准备此资源。

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

当前健康检查路径为 /.backstage/health/v1/readiness 和 liveness。将负载均衡器健康检查与实际后端保持一致。仅有三个副本或一个 PDB 并不能确保 AZ 分布、数据库高可用或零停机。请验证拓扑规则、共享数据库/会话状态、后台任务和升级迁移。

## OIDC 登录与身份

注册 OIDC 后端 provider 模块并配置前端登录。metadataUrl 必须指向所选 Cognito 池或 Okta issuer 的可信发现端点。当前 provider 使用 additionalScopes 配置额外作用域。

emailMatchingUserEntityProfileEmail 是一个 catalog 用户 resolver 示例。请检查 issuer/电子邮件验证、用户注册边界和重复电子邮件；不要将任意外部声明映射为 catalog 管理员。保持 dangerouslyAllowSignInWithoutUserInCatalog 禁用。避免在同一 provider ID 下同时注册内置 provider 和自定义 resolver 模块。

## Software Catalog

这八个实体涵盖七种 kind，且 owner/system/domain 引用均可解析。通过 Component.dependsOn 声明 Resource 依赖关系。不要假设臆造的 dependencyOf 字段会自动创建后端关系。注册 Resource 实体并不会配置 AWS 基础设施。

![Catalog 结构和所有权示例](../.gitbook/assets/en-platform-engineering-06-backstage-idp-1.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-06-backstage-idp-1.html)

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

GitHub 发现需要集成凭证和 catalog-backend-module-github 模块。请根据实际组织配置 catalogPath、分支/仓库筛选条件和调度。限制可信来源，不要假设每个仓库或任意 Location 都可以安全导入。文件位置必须与容器路径相匹配；仅有 glob 字符串并不能完成注册。

## Software Templates 与 GitOps

这是一个**仅包含 catalog 和 TechDocs 文件的完整小型骨架**。它并未标注为一个完整实现的微服务，不包含运行时、Dockerfile、Helm 和 CI。运行时黄金路径需要实际的特定语言源代码、测试、镜像构建、chart、环境值和流水线。添加一个复选框并不会配置数据库或 HPA。

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

template/skeleton 目录包含 catalog-info.yaml、mkdocs.yml 和 docs/index.md。转储编码的 description/owner 值可以保留 YAML 字符串，包括经过测试的引号/换行符。OwnerPicker 实体引用并非 GitHub 团队 slug；不要通过简单的字符串替换授予协作者权限。RepoUrlPicker 限制属于 UI 行为，不能替代后端 action 检查或 GitHub 凭证范围控制。

publish:github 需要 GitHub action 模块。检查已注册的 actions 及其实际输入 schema。此示例在仓库发布后进行注册。在基础设施 publish:github:pull-request 流程中，不要立即注册尚不存在、要等到合并后才会出现的主分支文件；应在之后执行发现/注册。

ACK/kro DatabaseClaim 不是内置 kind。请使用当前的 [ACK](02-ack.md)、[kro](03-kro.md) 和 [集成](05-example-corp-app.md) 示例，准备经过验证的 RGD/CRD、控制器和权限。Catalog 实体引用包含 ':' 和 '/'，因此不能原样复制到 Kubernetes 标签值中。

@roadiehq/scaffolder-backend-argocd 1.8.1 提供 argocd:create-resources。它需要 appName、argoInstance、namespace、repoUrl 和 path；projectName/labelValue 为可选项。namespace 是部署目标，且该 action 的 schema 中不包含旧版 revision 输入。注册其后端模块和 token，并限制 AppProject、目标位置和仓库权限。此处未执行仓库创建或 ArgoCD API 调用。

区分工作流骨架中的 Backstage Nunjucks 表达式和 GitHub 表达式。之前的 CI 使用 contents:read 尝试执行 git push，可能触发重复的自提交。应通过单独的 GitOps PR 提交经过审核的镜像摘要，并配置适当的身份验证、分支保护和合并检查。

## TechDocs 与 S3

使用外部构建器时，CI 负责构建/发布，Backstage 后端从 S3 读取。将 reader 和 publisher IAM 角色分开；默认不要授予运行时 reader PutObject/DeleteObject 权限。启用 S3 的全部四项 Block Public Access 设置，并在适用时配置 KMS 密钥策略/权限。ACK 字段名称为 blockPublicACLs/ignorePublicACLs。

![CI 发布与后端中介读取](../.gitbook/assets/en-platform-engineering-06-backstage-idp-2.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-06-backstage-idp-2.html)

TechDocs 仍支持 credentials.roleArn，但已将其标记为弃用。此示例省略该项，改用已准备好的工作负载身份/SDK 凭证；需要时使用 aws 账户/provider 配置。确保 reader/publisher 的 bucketRootPath 一致，并使用实际 CLI 验证 namespace/kind/name 实体键。

这个小型骨架已通过 MkDocs/techdocs-core 严格模式构建；这并非对每个服务文档的构建。发布 CI 需要可信分支/事件、id-token:write、受限的 OIDC 信任和 publisher 权限。本次审计未向 S3 上传任何内容。

## Kubernetes、ArgoCD 与成本插件

Kubernetes 插件需要前端/后端注册、实际端点/CA、身份验证和 RBAC。不要将打印出来的长期有效 ServiceAccount token 复制到环境变量中。EKS AWS 身份验证需要工作负载身份、目标角色/EKS 访问权限和 Kubernetes 授权，并且 x-k8s-aws-id 必须与实际集群名称相符。

服务器端集群凭证可能会由 Backstage 用户共享。multiTenant 定位器和 catalog namespace/id 选择器并非授权边界。请检查每用户数据范围、后端权限覆盖和集群 RBAC。工作负载标签应与 catalog 注解相匹配。Pod 日志需要 pods/log 授权和功能配置。列出 KEDA/Karpenter customResources 并不会生成专用的扩缩容 UI；应使用实际的 CRD 状态字段。

ArgoCD UI 插件和 scaffolder actions 使用独立的软件包、注册和权限。检查过的 Roadie UI 软件包版本为 2.12.5。旧版 @kubecost/backstage-plugin 和后端软件包名称在 npm 上返回 404，因此不再将其作为可安装命令保留；请选择维护中的集成或经验证的成本 API 适配器。应将分配和定价语义与 UI 卡片分开检查。

## Permission Framework

permission.enabled:true 不会安装团队策略。请在后端注册此模块，且不要与允许所有操作的策略注册竞争。它使用当前的 PolicyQueryUser 和 AuthService/UserInfoService 接口，而不是已弃用的 user.info 或较旧的 user.identity 结构。

此示例明确允许可信的 platform-team 管理员、已验证身份的 catalog 读取，以及基于所有者条件的 catalog 删除，并拒绝其他操作。它并非整个门户的完整允许列表；应有意添加所需操作。请保护 Group/User 来源，避免用户自行授予更高权限。

![示例中的允许、拒绝和条件决策](../.gitbook/assets/en-platform-engineering-06-backstage-idp-3.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-06-backstage-idp-3.html)

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

CONDITIONAL 决策必须由 catalog 后端应用于实际实体关系。Catalog 删除权限与 GitHub 修改或 ArgoCD 部署权限相互独立。不要将此概括为“所有者可以执行每一种更新”。八个策略案例使用的是模拟身份服务，而非真实 OIDC 或 catalog 所有权评估器。

## 审计、恢复与升级

当前 Core Auditor Service 默认通过 rootLogger 记录日志，并支持 backend.auditor.severityLogLevelMappings。之前的 backend.audit 和 backend.events.modules awsCloudWatch 设置不会自动配置审计收集。检查插件实际会发出哪些事件，然后通过单独的流水线转发日志。避免在事件元数据中泄露凭证或个人数据。

根据实际 RPO/RTO 要求，规划 PostgreSQL 快照/PITR、TechDocs 版本控制/复制/生命周期、配置/catalog 来源和 Secret provider 恢复。共享数据库 schema、Aurora 副本或 S3 复制本身并不能提供完整隔离、备份或自动故障转移。Aurora 恢复还需要实例、网络和端点切换验证。

升级时，请检查发布说明和插件兼容性，然后验证 versions:bump、lockfile、类型/测试、镜像和暂存数据库迁移。不要假设存在通用的 backstage-cli db:migrate 命令；请遵循插件/后端的迁移生命周期。恢复旧镜像不会自动恢复数据库 schema。

## 验证范围

已阅读两份原始指南（韩文 2,279 行，英文 2,226 行）、各自 143 行的测验，以及 118 个不重复的代码块。检查包括官方 chart 渲染、五个实际的 loader 文件包含项、八个 catalog 实体和一个无效输入、TypeScript/八个策略案例、两个模板字符串案例，以及一次小型 TechDocs 构建。

未执行完整 Backstage 应用/镜像构建、PostgreSQL/OIDC、GitHub/ArgoCD/Kubernetes/AWS API、真实模板 action、部署、负载或高可用测试。占位符和操作人员前置要求均已明确说明。

- [Backstage 1.54.7](https://github.com/backstage/backstage/tree/v1.54.7)
- [Helm chart 2.10.2](https://github.com/backstage/charts/releases/tag/backstage-2.10.2)
- [配置](https://backstage.io/docs/conf/writing/)
- [Kubernetes 身份验证](https://backstage.io/docs/features/kubernetes/authentication/)
- [权限策略](https://backstage.io/docs/permissions/writing-a-policy/)
- [Auditor](https://backstage.io/docs/backend-system/core-services/auditor/)
- [TechDocs](https://backstage.io/docs/features/techdocs/configuration/)
- [CNCF 项目](https://www.cncf.io/projects/backstage/)

[Backstage 测验](../quizzes/platform-engineering/06-backstage-idp-quiz.md)
