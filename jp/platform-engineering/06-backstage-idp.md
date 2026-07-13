# Backstage: Internal Developer Platform Framework

> **サポート対象バージョン**: Backstage 1.35+, Kubernetes 1.31+, EKS
> **最終更新**: June 22, 2026

## Table of Contents

- [Overview](#overview)
- [Learning Objectives](#learning-objectives)
- [Backstage Architecture](#backstage-architecture)
- [EKS Deployment](#eks-deployment)
- [Software Catalog](#software-catalog)
- [Software Templates (Golden Paths)](#software-templates-golden-paths)
- [TechDocs](#techdocs)
- [Plugin Ecosystem for EKS](#plugin-ecosystem-for-eks)
- [RBAC and Governance](#rbac-and-governance)
- [Production Operations](#production-operations)
- [Best Practices](#best-practices)
- [References](#references)

---

## Overview

### What is an Internal Developer Platform (IDP)?

Internal Developer Platform (IDP) は、開発者と基盤となるインフラストラクチャの間に位置するセルフサービスレイヤーであり、アプリケーションのデプロイ、リソースのプロビジョニング、サービスの管理のための標準化されたワークフローを提供します。[Platform Engineering Overview](./00-platform-engineering-overview.md) で説明したように、IDP は運用上の複雑さを抽象化することで、開発者がコードを書くことに集中できるようにします。

IDP は通常、次のものを提供します。

- **Service Catalog**: すべてのサービス、API、インフラストラクチャコンポーネントの集中レジストリ
- **Self-Service Workflows**: 新しいサービス、データベース、環境を作成するためのテンプレート化されたプロセス
- **Documentation Hub**: 集中管理され、発見しやすい技術ドキュメント
- **Visibility**: 組織全体のデプロイ、コスト、所有権、健全性をリアルタイムに可視化

### Why Backstage?

Backstage は Internal Developer Platform を構築するためのオープンソースフレームワークで、もともとは Spotify で作成され、現在は CNCF Incubating プロジェクトです。Spotify は、数百のエンジニアリングチームにまたがる 2,000 を超えるマイクロサービスを管理するために Backstage を構築しました。2020 年にオープンソース化されて以降、Backstage は Kubernetes エコシステムで最も広く採用されている IDP フレームワークになっています。

Backstage を選択する主な理由は次のとおりです。

1. **Open Source and Extensible**: MIT ライセンスで、200 以上のコミュニティプラグインを持つ活発なプラグインエコシステム
2. **CNCF Backing**: 強力なガバナンスを備えた Incubating プロジェクトで、長期的な持続可能性を確保
3. **Plugin Architecture**: すべてがプラグインであり、フォークせずに高度にカスタマイズ可能
4. **Software Catalog**: 技術エコシステム全体をモデル化する集中所有権レジストリ
5. **Software Templates**: 初日から組織標準を適用する Golden Path スキャフォールディング
6. **TechDocs**: 説明対象のコードと同じ場所にドキュメントを保持する docs-like-code アプローチ
7. **Active Community**: 900 名を超えるコントリビューターがおり、American Airlines、Netflix、Zalando、HP などの企業で採用

### IDP Platform Comparison

| Criteria | Backstage | Port | Cortex | Humanitec | OpsLevel |
|----------|-----------|------|--------|-----------|----------|
| **License** | Open Source (MIT) | Commercial (free tier) | Commercial | Commercial | Commercial |
| **Hosting** | Self-hosted | SaaS | SaaS | SaaS + Agent | SaaS |
| **Customization** | Unlimited (plugin system) | API + Blueprints | Limited | Moderate | Moderate |
| **Kubernetes Native** | Strong (plugins) | API-based | Limited | Strong (Score) | API-based |
| **Setup Complexity** | High (DIY) | Low | Low | Medium | Low |
| **Community Ecosystem** | 200+ plugins | Growing marketplace | Limited | Growing | Limited |
| **Cost** | Infrastructure only | Per user/month | Per user/month | Per user/month | Per user/month |

> **Note**: Backstage は SaaS の代替サービスと比較して、セットアップにより多くの初期投資が必要ですが、比類のない柔軟性とライセンスコストゼロを提供します。すでに Kubernetes と GitOps に投資している組織では、Backstage は既存のエコシステムに自然に統合できます。

---

## Learning Objectives

このドキュメントを完了すると、次のことができるようになります。

1. Kubernetes プラットフォームエンジニアリングスタック内での IDP フレームワークとしての Backstage の役割を**説明**する
2. Helm を使用し、RDS PostgreSQL と ALB ingress を組み合わせて Amazon EKS 上に Backstage を**デプロイ**する
3. GitHub リポジトリからサービスを自動検出するように Software Catalog を**設定**する
4. CI/CD とインフラストラクチャを備えたマイクロサービスを生成する Software Templates (Golden Paths) を**作成**する
5. EKS 上のワークロードをリアルタイムに可視化するため、Backstage を Kubernetes プラグインと**統合**する
6. 集中ドキュメントのために S3 ストレージを使用して TechDocs を**セットアップ**する
7. ArgoCD、Kubecost、その他の Kubernetes エコシステムツール向けプラグインを**インストールして設定**する
8. マルチチーム環境向けに RBAC とガバナンスポリシーを**実装**する
9. 高可用性、バックアップ、アップグレード戦略を備えて本番環境で Backstage を**運用**する

---

## Backstage Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Developer Interface"
        Browser["Browser"]
    end

    subgraph "Backstage Application"
        Frontend["Frontend<br/>(React SPA)"]
        Backend["Backend<br/>(Node.js + Express)"]

        subgraph "Core Plugins"
            Catalog["Software Catalog"]
            Templates["Software Templates"]
            TechDocs["TechDocs"]
            Search["Search"]
        end

        subgraph "Integration Plugins"
            K8sPlugin["Kubernetes Plugin"]
            ArgoPlugin["ArgoCD Plugin"]
            GHPlugin["GitHub Plugin"]
            CostPlugin["Kubecost Plugin"]
        end
    end

    subgraph "Data Layer"
        PostgreSQL["PostgreSQL<br/>(RDS)"]
        S3["S3 Bucket<br/>(TechDocs)"]
    end

    subgraph "External Systems"
        GitHub["GitHub / GitLab"]
        EKS["EKS Clusters"]
        ArgoCD["ArgoCD"]
        OIDC["OIDC Provider<br/>(Cognito / Okta)"]
    end

    Browser --> Frontend
    Frontend --> Backend
    Backend --> Catalog
    Backend --> Templates
    Backend --> TechDocs
    Backend --> Search
    Backend --> K8sPlugin
    Backend --> ArgoPlugin
    Backend --> GHPlugin
    Backend --> CostPlugin
    Backend --> PostgreSQL
    TechDocs --> S3
    GHPlugin --> GitHub
    K8sPlugin --> EKS
    ArgoPlugin --> ArgoCD
    Backend --> OIDC
```

### Core Concepts

Backstage は 4 つの基礎的な柱を中心に構築されています。

1. **Software Catalog**: 組織内のすべてのソフトウェアを一元的かつ自動的に更新するインベントリです。すべてのコンポーネントについて、所有権、依存関係、API、ドキュメントリンク、運用メタデータを追跡します。

2. **Software Templates**: 新しいプロジェクト、サービス、またはインフラストラクチャを、CI/CD パイプライン、モニタリング、セキュリティポリシー、ドキュメント構造といったすべての組織標準を組み込んだ状態で作成する、再利用可能なスキャフォールディング定義 (Golden Paths) です。

3. **TechDocs**: Markdown ドキュメントを (MkDocs 経由で) Backstage ポータル内に直接レンダリングする docs-like-code ソリューションです。ドキュメントはコードと同じリポジトリに置かれるため、最新の状態を保ちやすくなります。

4. **Search**: カタログ、TechDocs、その他のデータソースをインデックス化し、エンジニアリング組織内のあらゆるものを発見するための単一の検索バーを提供する統合検索プラットフォームです。

### Plugin Architecture

Backstage は「すべてがプラグインである」という思想に従っています。Software Catalog のようなコア機能でさえプラグインとして実装されています。このアーキテクチャは次を提供します。

- **Frontend Plugins**: UI 要素 (ページ、カード、タブ) をレンダリングする React コンポーネント
- **Backend Plugins**: API を提供し、データ処理を扱い、外部システムと統合する Node.js モジュール
- **Plugin Isolation**: 各プラグインは独自のデータベーススキーマ、API ルート、設定を持つ
- **Composability**: プラグインは、明確に定義された拡張ポイントを通じて他のプラグインに依存し、拡張できる

```
┌─────────────────────────────────────────────────────────────────┐
│                     Backstage App Shell                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Catalog  │  │Templates │  │ TechDocs │  │   Search     │   │
│  │ Plugin   │  │ Plugin   │  │ Plugin   │  │   Plugin     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │   K8s    │  │  ArgoCD  │  │ Kubecost │  │   Custom     │   │
│  │ Plugin   │  │  Plugin  │  │  Plugin  │  │   Plugins    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    Plugin API / Extension Points                 │
├─────────────────────────────────────────────────────────────────┤
│                    Backend Services (Node.js)                    │
├─────────────────────────────────────────────────────────────────┤
│              PostgreSQL          │           S3 / Cache          │
└─────────────────────────────────────────────────────────────────┘
```

プラグインは通常、次の要素で構成されます。

| Component | Location | Purpose |
|-----------|----------|---------|
| **Frontend Plugin** | `plugins/<name>/` | React components, routes, API clients |
| **Backend Plugin** | `plugins/<name>-backend/` | Express routers, database access, external API calls |
| **Common** | `plugins/<name>-common/` | Shared types, constants, API definitions |
| **Node** | `plugins/<name>-node/` | Shared backend utilities, extension points |

---

## EKS Deployment

### Prerequisites

EKS に Backstage をデプロイする前に、次のリソースが利用可能であることを確認してください。

| Resource | Purpose | Notes |
|----------|---------|-------|
| **EKS Cluster** | Backstage runtime | Kubernetes 1.31+ |
| **Amazon RDS (PostgreSQL)** | Persistent storage | PostgreSQL 15+, db.r6g.large or larger |
| **Amazon ECR** | Container image registry | Private repository for Backstage images |
| **AWS ALB** | Ingress controller | AWS Load Balancer Controller installed |
| **Amazon S3** | TechDocs storage | Bucket for generated documentation |
| **AWS Certificate Manager** | TLS certificate | For HTTPS on ALB |
| **Amazon Cognito or Okta** | OIDC authentication | Identity provider for user login |
| **GitHub App or Token** | Source code integration | For catalog discovery and template scaffolding |

### Step 1: Create the Backstage Application

まず、ローカルで新しい Backstage アプリケーションをスキャフォールドします。

```bash
# Ensure Node.js 20+ and Yarn are installed
node --version   # v20.x or higher
yarn --version   # 4.x (Berry)

# Create a new Backstage app
npx @backstage/create-app@latest --skip-install
# When prompted, enter the app name: my-backstage-app

cd my-backstage-app

# Install dependencies
yarn install
```

生成されるプロジェクト構造は次のとおりです。

```
my-backstage-app/
├── app-config.yaml              # Main configuration
├── app-config.production.yaml   # Production overrides
├── catalog-info.yaml            # Backstage's own catalog entry
├── package.json
├── packages/
│   ├── app/                     # Frontend (React)
│   │   ├── src/
│   │   └── package.json
│   └── backend/                 # Backend (Node.js)
│       ├── src/
│       └── package.json
├── plugins/                     # Custom plugins
└── yarn.lock
```

### Step 2: Containerize the Application

本番デプロイ用のマルチステージ Dockerfile を作成します。

```dockerfile
# Stage 1: Build the frontend and backend
FROM node:20-bookworm-slim AS build

WORKDIR /app

# Copy dependency files
COPY package.json yarn.lock .yarnrc.yml ./
COPY .yarn ./.yarn
COPY packages/app/package.json ./packages/app/
COPY packages/backend/package.json ./packages/backend/
COPY plugins/ ./plugins/

# Install all dependencies
RUN yarn install --immutable

# Copy the rest of the source
COPY . .

# Build the app
RUN yarn tsc
RUN yarn build:backend --config ../../app-config.yaml

# Stage 2: Production image
FROM node:20-bookworm-slim

# Install runtime dependencies for TechDocs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv git curl && \
    python3 -m pip install --break-system-packages \
      mkdocs-techdocs-core==1.4.* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 backstage
USER backstage
WORKDIR /app

# Copy the built backend bundle
COPY --from=build --chown=backstage:backstage /app/packages/backend/dist ./packages/backend/dist
COPY --from=build --chown=backstage:backstage /app/node_modules ./node_modules
COPY --from=build --chown=backstage:backstage /app/package.json ./

# Copy configuration files
COPY --chown=backstage:backstage app-config.yaml app-config.production.yaml ./

# Environment variables
ENV NODE_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:7007/healthcheck || exit 1

EXPOSE 7007

CMD ["node", "packages/backend/dist", "--config", "app-config.yaml", "--config", "app-config.production.yaml"]
```

イメージをビルドし、ECR にプッシュします。

```bash
# Authenticate to ECR
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  111122223333.dkr.ecr.ap-northeast-2.amazonaws.com

# Build and push
docker build -t backstage:latest .
docker tag backstage:latest \
  111122223333.dkr.ecr.ap-northeast-2.amazonaws.com/backstage:v1.35.0
docker push \
  111122223333.dkr.ecr.ap-northeast-2.amazonaws.com/backstage:v1.35.0
```

### Step 3: Deploy with Helm

Backstage Helm chart リポジトリを追加し、values ファイルを作成します。

```bash
helm repo add backstage https://backstage.github.io/charts
helm repo update
```

包括的な `values.yaml` を作成します。

```yaml
# backstage-values.yaml
backstage:
  image:
    registry: 111122223333.dkr.ecr.ap-northeast-2.amazonaws.com
    repository: backstage
    tag: v1.35.0
    pullPolicy: IfNotPresent

  replicas: 2

  resources:
    requests:
      memory: 512Mi
      cpu: 250m
    limits:
      memory: 1Gi
      cpu: 1000m

  extraEnvVarsSecrets:
    - backstage-secrets

  appConfig:
    app:
      title: "My Company Developer Portal"
      baseUrl: https://backstage.example.com
    backend:
      baseUrl: https://backstage.example.com
      listen:
        port: 7007
      cors:
        origin: https://backstage.example.com
        methods: [GET, HEAD, PATCH, POST, PUT, DELETE]
        credentials: true
      database:
        client: pg
        connection:
          host: ${POSTGRES_HOST}
          port: ${POSTGRES_PORT}
          user: ${POSTGRES_USER}
          password: ${POSTGRES_PASSWORD}
          database: backstage
          ssl:
            require: true
            rejectUnauthorized: true

  podAnnotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "7007"
    prometheus.io/path: "/metrics"

  serviceAccount:
    create: true
    name: backstage
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/backstage-irsa-role

ingress:
  enabled: true
  className: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:111122223333:certificate/abcd-1234-efgh
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    alb.ingress.kubernetes.io/healthcheck-path: /healthcheck
    alb.ingress.kubernetes.io/group.name: backstage
  hosts:
    - host: backstage.example.com
      paths:
        - path: /
          pathType: Prefix

postgresql:
  enabled: false  # Using external RDS

serviceAccount:
  create: true
  name: backstage
```

EKS にデプロイします。

```bash
# Create the namespace
kubectl create namespace backstage

# Create the secrets (referencing values from AWS Secrets Manager or SSM)
kubectl create secret generic backstage-secrets \
  --namespace backstage \
  --from-literal=POSTGRES_HOST=backstage-db.cluster-xxxxxxx.ap-northeast-2.rds.amazonaws.com \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_USER=backstage \
  --from-literal=POSTGRES_PASSWORD='<secure-password>' \
  --from-literal=GITHUB_TOKEN='ghp_xxxxxxxxxxxxxxxxxxxx' \
  --from-literal=AUTH_OIDC_CLIENT_ID='<client-id>' \
  --from-literal=AUTH_OIDC_CLIENT_SECRET='<client-secret>'

# Install the chart
helm install backstage backstage/backstage \
  --namespace backstage \
  --values backstage-values.yaml \
  --wait --timeout 10m
```

### Step 4: ALB Ingress Configuration

Helm chart とは別に Ingress リソースを管理したい場合は、明示的に作成します。

```yaml
# backstage-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: backstage
  namespace: backstage
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:111122223333:certificate/abcd-1234-efgh
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    alb.ingress.kubernetes.io/healthcheck-path: /healthcheck
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "15"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "3"
    alb.ingress.kubernetes.io/group.name: backstage
    alb.ingress.kubernetes.io/tags: Environment=production,Team=platform
    alb.ingress.kubernetes.io/load-balancer-attributes: >-
      idle_timeout.timeout_seconds=120,
      routing.http.drop_invalid_header_fields.enabled=true
spec:
  ingressClassName: alb
  rules:
    - host: backstage.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backstage
                port:
                  number: 7007
```

```bash
kubectl apply -f backstage-ingress.yaml
```

### Step 5: PostgreSQL via RDS

データベース接続は `app-config.production.yaml` で設定します。次の例は、接続プーリングと SSL を含む完全なデータベースセクションを示しています。

```yaml
# app-config.production.yaml
backend:
  database:
    client: pg
    connection:
      host: ${POSTGRES_HOST}
      port: ${POSTGRES_PORT}
      user: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD}
      database: backstage
      ssl:
        require: true
        rejectUnauthorized: true
    knexConfig:
      pool:
        min: 3
        max: 12
        acquireTimeoutMillis: 60000
        idleTimeoutMillis: 30000
    plugin:
      catalog:
        connection:
          database: backstage_plugin_catalog
      scaffolder:
        connection:
          database: backstage_plugin_scaffolder
      auth:
        connection:
          database: backstage_plugin_auth
      search:
        connection:
          database: backstage_plugin_search
```

> **Note**: Backstage はプラグインごとのデータベース分離をサポートしています。各プラグインは同じ PostgreSQL インスタンス内の別々のデータベースを使用でき、セキュリティを向上させ、バックアップと移行を簡素化します。

### Step 6: OIDC Authentication Setup

Backstage は複数の認証プロバイダーをサポートしています。以下は Amazon Cognito と Okta の両方の設定です。

#### Amazon Cognito Configuration

```yaml
# app-config.production.yaml
auth:
  environment: production
  providers:
    oidc:
      production:
        metadataUrl: https://cognito-idp.ap-northeast-2.amazonaws.com/<user-pool-id>/.well-known/openid-configuration
        clientId: ${AUTH_OIDC_CLIENT_ID}
        clientSecret: ${AUTH_OIDC_CLIENT_SECRET}
        authorizationUrl: https://<domain>.auth.ap-northeast-2.amazoncognito.com/oauth2/authorize
        tokenUrl: https://<domain>.auth.ap-northeast-2.amazoncognito.com/oauth2/token
        scope: openid profile email
        prompt: auto
  session:
    secret: ${AUTH_SESSION_SECRET}
```

#### Okta Configuration

```yaml
# app-config.production.yaml
auth:
  environment: production
  providers:
    okta:
      production:
        clientId: ${AUTH_OKTA_CLIENT_ID}
        clientSecret: ${AUTH_OKTA_CLIENT_SECRET}
        audience: https://dev-123456.okta.com
        authServerId: default
        idp: ${AUTH_OKTA_IDP_ID}
  session:
    secret: ${AUTH_SESSION_SECRET}
```

#### Sign-In Resolver Configuration

バックエンドプラグインコードで、OIDC ID を Backstage ユーザーにどのようにマッピングするかを設定します。

```typescript
// packages/backend/src/plugins/auth.ts
import { createBackendModule } from '@backstage/backend-plugin-api';
import {
  authProvidersExtensionPoint,
  createOAuthProviderFactory,
} from '@backstage/plugin-auth-node';
import { oidcAuthenticator } from '@backstage/plugin-auth-backend-module-oidc-provider';

export const authModuleOidc = createBackendModule({
  pluginId: 'auth',
  moduleId: 'oidc',
  register(reg) {
    reg.registerInit({
      deps: { providers: authProvidersExtensionPoint },
      async init({ providers }) {
        providers.registerProvider({
          providerId: 'oidc',
          factory: createOAuthProviderFactory({
            authenticator: oidcAuthenticator,
            async signInResolver({ result }, ctx) {
              const email = result.userinfo.email;
              if (!email) {
                throw new Error('OIDC login did not provide an email');
              }
              return ctx.signInWithCatalogUser({
                filter: { 'spec.profile.email': email },
              });
            },
          }),
        });
      },
    });
  },
});
```

---

## Software Catalog

### Entity Model

Backstage Software Catalog は、組織のソフトウェアエコシステムを表現するために、明確に定義されたエンティティモデルを使用します。このモデルを理解することは、効果的なカタログ管理に不可欠です。

```mermaid
graph TB
    Domain["Domain<br/>(Business Area)"] --> System["System<br/>(Product/Platform)"]
    System --> Component["Component<br/>(Service/Library)"]
    System --> API["API<br/>(gRPC/REST/Event)"]
    System --> Resource["Resource<br/>(DB/Queue/Bucket)"]
    Component --> API
    Component --> Resource
    Group["Group<br/>(Team)"] --> |owns| System
    Group --> |owns| Component
    User["User<br/>(Person)"] --> |memberOf| Group
```

### Entity Types

| Entity Kind | Description | Example |
|-------------|-------------|---------|
| **Component** | A software component (service, website, library) | `order-service`, `payment-api` |
| **System** | A collection of components that form a product | `order-platform`, `data-pipeline` |
| **Domain** | A business domain grouping related systems | `commerce`, `fulfillment` |
| **API** | An interface exposed by a component | `order-api`, `payment-grpc` |
| **Resource** | Infrastructure dependencies | `order-db`, `events-queue` |
| **Group** | A team or organizational unit | `platform-team`, `commerce-team` |
| **User** | An individual person | `john.doe` |

### catalog-info.yaml Examples

#### Component Entity

```yaml
# catalog-info.yaml (in the service repository root)
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: order-service
  description: Handles order creation, updates, and lifecycle management
  labels:
    app.kubernetes.io/name: order-service
  annotations:
    backstage.io/techdocs-ref: dir:.
    github.com/project-slug: my-org/order-service
    backstage.io/kubernetes-id: order-service
    argocd/app-name: order-service
    backstage.io/kubernetes-namespace: commerce
  tags:
    - java
    - spring-boot
    - grpc
  links:
    - url: https://grafana.example.com/d/order-service
      title: Grafana Dashboard
      icon: dashboard
    - url: https://runbook.example.com/order-service
      title: Runbook
      icon: docs
spec:
  type: service
  lifecycle: production
  owner: group:commerce-team
  system: order-platform
  providesApis:
    - order-api
  consumesApis:
    - payment-api
    - inventory-api
  dependsOn:
    - resource:order-db
    - resource:order-events-queue
```

#### System Entity

```yaml
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: order-platform
  description: End-to-end order management platform including order processing, payment, and fulfillment
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - commerce
    - critical
spec:
  owner: group:commerce-team
  domain: commerce
```

#### Domain Entity

```yaml
apiVersion: backstage.io/v1alpha1
kind: Domain
metadata:
  name: commerce
  description: All systems related to the online commerce experience including ordering, payments, and fulfillment
spec:
  owner: group:commerce-leadership
```

#### API Entity

```yaml
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: order-api
  description: REST API for order management operations
  tags:
    - rest
    - json
spec:
  type: openapi
  lifecycle: production
  owner: group:commerce-team
  system: order-platform
  definition: |
    openapi: "3.0.0"
    info:
      title: Order API
      version: 1.0.0
    paths:
      /orders:
        get:
          summary: List orders
          responses:
            '200':
              description: A list of orders
        post:
          summary: Create an order
          responses:
            '201':
              description: Order created
      /orders/{orderId}:
        get:
          summary: Get order by ID
          parameters:
            - name: orderId
              in: path
              required: true
              schema:
                type: string
          responses:
            '200':
              description: Order details
```

#### Resource Entity

```yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: order-db
  description: Aurora PostgreSQL cluster for order data
  annotations:
    aws.amazon.com/rds-cluster-id: order-db-cluster
  tags:
    - postgresql
    - aurora
spec:
  type: database
  owner: group:commerce-team
  system: order-platform
```

#### Group Entity

```yaml
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: commerce-team
  description: Commerce engineering team responsible for the order platform
spec:
  type: team
  profile:
    displayName: Commerce Team
    email: commerce-team@example.com
    picture: https://avatars.example.com/commerce-team.png
  parent: engineering
  children: []
  members:
    - john.doe
    - jane.smith
    - alex.kim
```

#### User Entity

```yaml
apiVersion: backstage.io/v1alpha1
kind: User
metadata:
  name: john.doe
  description: Senior Backend Engineer
spec:
  profile:
    displayName: John Doe
    email: john.doe@example.com
    picture: https://avatars.example.com/john-doe.png
  memberOf:
    - commerce-team
```

### GitHub Auto-Discovery

GitHub discovery プラグインは、GitHub organization 全体から `catalog-info.yaml` ファイルを自動的に見つけます。

```yaml
# app-config.yaml
catalog:
  providers:
    github:
      myOrgProvider:
        organization: my-org
        catalogPath: /catalog-info.yaml
        filters:
          branch: main
          repository: '.*'  # All repositories
        schedule:
          frequency:
            minutes: 30
          timeout:
            minutes: 3
  rules:
    - allow:
        - Component
        - System
        - Domain
        - API
        - Resource
        - Group
        - User
        - Template
        - Location
```

必要なバックエンドプラグインをインストールします。

```bash
# From the Backstage app root
yarn --cwd packages/backend add @backstage/plugin-catalog-backend-module-github
```

バックエンドでモジュールを登録します。

```typescript
// packages/backend/src/index.ts
import { createBackend } from '@backstage/backend-defaults';

const backend = createBackend();

// Core plugins
backend.add(import('@backstage/plugin-catalog-backend'));
backend.add(import('@backstage/plugin-catalog-backend-module-github'));
// ... other plugins

backend.start();
```

### Kubernetes Cluster Integration

Kubernetes プラグインは、各コンポーネントの Backstage カタログ内で、Pod、Deployment、Service の状態をリアルタイムに直接表示します。

#### Install the Kubernetes Plugin

```bash
# Frontend plugin
yarn --cwd packages/app add @backstage/plugin-kubernetes

# Backend plugin
yarn --cwd packages/backend add @backstage/plugin-kubernetes-backend
```

#### Configure the Backend

Kubernetes バックエンドプラグインを登録します。

```typescript
// packages/backend/src/index.ts
backend.add(import('@backstage/plugin-kubernetes-backend'));
```

#### Configure EKS Cluster Access

```yaml
# app-config.yaml
kubernetes:
  serviceLocatorMethod:
    type: multiTenant
  clusterLocatorMethods:
    - type: config
      clusters:
        - name: production-eks
          url: https://ABCDEF1234567890.gr7.ap-northeast-2.eks.amazonaws.com
          authProvider: serviceAccount
          serviceAccountToken: ${K8S_PROD_SA_TOKEN}
          caData: ${K8S_PROD_CA_DATA}
          skipTLSVerify: false
          skipMetricsLookup: false
          dashboardUrl: https://console.aws.amazon.com/eks/home?region=ap-northeast-2#/clusters/production-eks
          dashboardApp: aws
        - name: staging-eks
          url: https://GHIJKL5678901234.gr7.ap-northeast-2.eks.amazonaws.com
          authProvider: serviceAccount
          serviceAccountToken: ${K8S_STAGING_SA_TOKEN}
          caData: ${K8S_STAGING_CA_DATA}
          skipTLSVerify: false
          skipMetricsLookup: false
```

#### ServiceAccount and RBAC for Backstage

Backstage がワークロードの状態を照会できるように、各 EKS cluster に読み取り専用の ServiceAccount を作成します。

```yaml
# backstage-k8s-rbac.yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: backstage-system
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backstage-reader
  namespace: backstage-system
---
apiVersion: v1
kind: Secret
metadata:
  name: backstage-reader-token
  namespace: backstage-system
  annotations:
    kubernetes.io/service-account.name: backstage-reader
type: kubernetes.io/service-account-token
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: backstage-reader
rules:
  - apiGroups: [""]
    resources:
      - pods
      - services
      - configmaps
      - namespaces
      - endpoints
      - serviceaccounts
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources:
      - deployments
      - replicasets
      - statefulsets
      - daemonsets
    verbs: ["get", "list", "watch"]
  - apiGroups: ["batch"]
    resources:
      - jobs
      - cronjobs
    verbs: ["get", "list", "watch"]
  - apiGroups: ["networking.k8s.io"]
    resources:
      - ingresses
    verbs: ["get", "list", "watch"]
  - apiGroups: ["autoscaling"]
    resources:
      - horizontalpodautoscalers
    verbs: ["get", "list", "watch"]
  - apiGroups: ["metrics.k8s.io"]
    resources:
      - pods
      - nodes
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: backstage-reader-binding
subjects:
  - kind: ServiceAccount
    name: backstage-reader
    namespace: backstage-system
roleRef:
  kind: ClusterRole
  name: backstage-reader
  apiGroup: rbac.authorization.k8s.io
```

```bash
# Apply to each target EKS cluster
kubectl apply -f backstage-k8s-rbac.yaml

# Retrieve the token for Backstage configuration
kubectl get secret backstage-reader-token \
  -n backstage-system \
  -o jsonpath='{.data.token}' | base64 -d
```

#### Annotate Components for Kubernetes Discovery

Kubernetes プラグインが適切なワークロードを見つけられるように、カタログエンティティにアノテーションを付けます。

```yaml
# In catalog-info.yaml
metadata:
  annotations:
    backstage.io/kubernetes-id: order-service
    backstage.io/kubernetes-namespace: commerce
    backstage.io/kubernetes-label-selector: app=order-service
```

プラグインはこれらのアノテーションに基づいてワークロードを照合し、コンポーネントページに Pod、Deployment、ReplicaSet、HPA の状態を直接表示します。

---

## Software Templates (Golden Paths)

Software Templates により、プラットフォームチームは新しいプロジェクトを作成するための標準化されたパスを定義できます。これらの Golden Paths は、新しいサービスが正しい構造、CI/CD パイプライン、モニタリング、セキュリティ設定を備えて開始されることを保証します。Golden Path の概念の背景については、[Platform Engineering Overview](./00-platform-engineering-overview.md) を参照してください。

### Template Structure

Backstage template は次で構成されます。

1. **Parameters**: 開発者に提示される入力フィールド (フォーム)
2. **Steps**: プロジェクトをスキャフォールドするために順次実行されるアクション
3. **Output**: 完了後に表示されるリンクと情報

```
template.yaml
├── parameters:     # What the developer fills in
│   ├── service name
│   ├── team/owner
│   ├── language
│   └── features (database, queue, etc.)
├── steps:          # What happens automatically
│   ├── fetch:template (scaffold files)
│   ├── publish:github (create repository)
│   ├── catalog:register (add to Backstage)
│   └── argocd:create-resources (set up CD)
└── output:         # What the developer sees
    ├── repository URL
    ├── catalog entity link
    └── ArgoCD app link
```

### Microservice Golden Path Template

この template は、Dockerfile、Helm chart、ArgoCD Application、GitHub Actions CI パイプラインを備えた完全なマイクロサービスをスキャフォールドします。

```yaml
# templates/microservice/template.yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: microservice-golden-path
  title: Microservice Golden Path
  description: |
    Create a production-ready microservice with CI/CD pipeline,
    Kubernetes deployment, monitoring, and documentation scaffolding.
  tags:
    - recommended
    - microservice
    - kubernetes
spec:
  owner: group:platform-team
  type: service

  parameters:
    - title: Service Information
      required:
        - serviceName
        - owner
        - description
      properties:
        serviceName:
          title: Service Name
          type: string
          description: Unique name for the microservice (lowercase, hyphens only)
          pattern: "^[a-z][a-z0-9-]*$"
          maxLength: 40
          ui:autofocus: true
        description:
          title: Description
          type: string
          description: Brief description of what this service does
          maxLength: 200
        owner:
          title: Owner Team
          type: string
          description: The team that will own this service
          ui:field: OwnerPicker
          ui:options:
            catalogFilter:
              kind: Group
        system:
          title: System
          type: string
          description: The system this service belongs to
          ui:field: EntityPicker
          ui:options:
            catalogFilter:
              kind: System

    - title: Technical Configuration
      required:
        - language
        - port
      properties:
        language:
          title: Programming Language
          type: string
          enum:
            - java-spring
            - go
            - node-express
            - python-fastapi
          enumNames:
            - Java (Spring Boot 3)
            - Go (Gin)
            - Node.js (Express)
            - Python (FastAPI)
        port:
          title: Service Port
          type: integer
          default: 8080
          description: Port the service listens on
        enableDatabase:
          title: Enable Database
          type: boolean
          default: false
          description: Provision an Aurora PostgreSQL database via ACK
        enableQueue:
          title: Enable Message Queue
          type: boolean
          default: false
          description: Provision an SQS queue via ACK

    - title: Deployment Configuration
      required:
        - namespace
        - environment
      properties:
        namespace:
          title: Kubernetes Namespace
          type: string
          default: default
          description: Target namespace for deployment
        environment:
          title: Environment
          type: string
          enum:
            - dev
            - staging
            - production
          default: dev

    - title: Repository Configuration
      required:
        - repoUrl
      properties:
        repoUrl:
          title: Repository Location
          type: string
          ui:field: RepoUrlPicker
          ui:options:
            allowedHosts:
              - github.com
            allowedOwners:
              - my-org

  steps:
    # Step 1: Scaffold the project from a skeleton template
    - id: fetch-skeleton
      name: Fetch Project Skeleton
      action: fetch:template
      input:
        url: ./skeleton/${{ parameters.language }}
        targetPath: .
        values:
          serviceName: ${{ parameters.serviceName }}
          description: ${{ parameters.description }}
          owner: ${{ parameters.owner }}
          system: ${{ parameters.system }}
          port: ${{ parameters.port }}
          namespace: ${{ parameters.namespace }}
          environment: ${{ parameters.environment }}
          enableDatabase: ${{ parameters.enableDatabase }}
          enableQueue: ${{ parameters.enableQueue }}

    # Step 2: Generate the Helm chart
    - id: fetch-helm
      name: Generate Helm Chart
      action: fetch:template
      input:
        url: ./skeleton/helm-chart
        targetPath: ./deploy/helm
        values:
          serviceName: ${{ parameters.serviceName }}
          port: ${{ parameters.port }}
          namespace: ${{ parameters.namespace }}
          enableDatabase: ${{ parameters.enableDatabase }}
          enableQueue: ${{ parameters.enableQueue }}

    # Step 3: Generate GitHub Actions CI pipeline
    - id: fetch-ci
      name: Generate CI Pipeline
      action: fetch:template
      input:
        url: ./skeleton/github-actions/${{ parameters.language }}
        targetPath: ./.github/workflows
        values:
          serviceName: ${{ parameters.serviceName }}
          language: ${{ parameters.language }}

    # Step 4: Generate ArgoCD Application manifest
    - id: fetch-argocd
      name: Generate ArgoCD Application
      action: fetch:template
      input:
        url: ./skeleton/argocd-app
        targetPath: ./deploy/argocd
        values:
          serviceName: ${{ parameters.serviceName }}
          namespace: ${{ parameters.namespace }}
          environment: ${{ parameters.environment }}
          repoUrl: ${{ (parameters.repoUrl | parseRepoUrl).host }}/${{ (parameters.repoUrl | parseRepoUrl).owner }}/${{ (parameters.repoUrl | parseRepoUrl).repo }}

    # Step 5: Publish to GitHub
    - id: publish
      name: Create GitHub Repository
      action: publish:github
      input:
        repoUrl: ${{ parameters.repoUrl }}
        description: ${{ parameters.description }}
        defaultBranch: main
        protectDefaultBranch: true
        repoVisibility: internal
        collaborators:
          - team: ${{ parameters.owner | replace("group:", "") }}
            access: maintain
          - team: platform-team
            access: admin

    # Step 6: Register in Backstage catalog
    - id: register
      name: Register in Backstage Catalog
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps['publish'].output.repoContentsUrl }}
        catalogInfoPath: /catalog-info.yaml

  output:
    links:
      - title: Source Code Repository
        url: ${{ steps['publish'].output.remoteUrl }}
      - title: Backstage Catalog Entity
        icon: catalog
        entityRef: ${{ steps['register'].output.entityRef }}
      - title: GitHub Actions CI
        url: ${{ steps['publish'].output.remoteUrl }}/actions
```

### Infrastructure Provisioning Template

この template は [ACK](./02-ack.md) と [KRO](./03-kro.md) Claims を通じて AWS インフラストラクチャリソースを作成し、開発者がデータベース、キャッシュ、キューにセルフサービスでアクセスできるようにします。

```yaml
# templates/infrastructure/template.yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: aws-infrastructure-provisioning
  title: AWS Infrastructure Provisioning
  description: |
    Self-service provisioning of AWS infrastructure resources (RDS, ElastiCache, SQS)
    using ACK controllers and KRO resource graphs on EKS.
  tags:
    - infrastructure
    - aws
    - self-service
spec:
  owner: group:platform-team
  type: resource

  parameters:
    - title: Resource Information
      required:
        - resourceName
        - owner
        - resourceType
      properties:
        resourceName:
          title: Resource Name
          type: string
          description: Name for the infrastructure resource
          pattern: "^[a-z][a-z0-9-]*$"
          maxLength: 40
        owner:
          title: Owner Team
          type: string
          ui:field: OwnerPicker
          ui:options:
            catalogFilter:
              kind: Group
        resourceType:
          title: Resource Type
          type: string
          enum:
            - aurora-postgresql
            - aurora-mysql
            - elasticache-redis
            - sqs-queue
            - s3-bucket
          enumNames:
            - Aurora PostgreSQL
            - Aurora MySQL
            - ElastiCache Redis
            - SQS Queue
            - S3 Bucket

    - title: Resource Configuration
      required:
        - environment
        - size
      properties:
        environment:
          title: Environment
          type: string
          enum:
            - dev
            - staging
            - production
          default: dev
        size:
          title: Instance Size
          type: string
          enum:
            - small
            - medium
            - large
          enumNames:
            - "Small (dev/test: db.t4g.medium, cache.t4g.small)"
            - "Medium (staging: db.r6g.large, cache.r6g.large)"
            - "Large (production: db.r6g.xlarge, cache.r6g.xlarge)"
          default: small
        namespace:
          title: Target Namespace
          type: string
          default: default
          description: Kubernetes namespace where the resource claim will be created

    - title: Database-Specific Options
      description: Only applicable for database resource types
      properties:
        dbName:
          title: Database Name
          type: string
          default: appdb
          description: Name of the initial database to create
        storageSize:
          title: Storage Size (GiB)
          type: integer
          default: 20
          minimum: 20
          maximum: 1000
        enableMultiAZ:
          title: Enable Multi-AZ
          type: boolean
          default: false
          description: Enable Multi-AZ deployment for high availability

  steps:
    # Step 1: Generate the KRO resource claim
    - id: generate-claim
      name: Generate Resource Claim
      action: fetch:template
      input:
        url: ./skeleton/infrastructure/${{ parameters.resourceType }}
        targetPath: ./infrastructure
        values:
          resourceName: ${{ parameters.resourceName }}
          environment: ${{ parameters.environment }}
          size: ${{ parameters.size }}
          namespace: ${{ parameters.namespace }}
          dbName: ${{ parameters.dbName }}
          storageSize: ${{ parameters.storageSize }}
          enableMultiAZ: ${{ parameters.enableMultiAZ }}
          owner: ${{ parameters.owner }}

    # Step 2: Publish to the infrastructure GitOps repository
    - id: publish
      name: Create Pull Request
      action: publish:github:pull-request
      input:
        repoUrl: github.com?owner=my-org&repo=infrastructure-gitops
        branchName: provision/${{ parameters.resourceName }}
        title: "Provision ${{ parameters.resourceType }}: ${{ parameters.resourceName }}"
        description: |
          ## Infrastructure Provisioning Request

          | Field | Value |
          |-------|-------|
          | Resource | ${{ parameters.resourceName }} |
          | Type | ${{ parameters.resourceType }} |
          | Environment | ${{ parameters.environment }} |
          | Size | ${{ parameters.size }} |
          | Owner | ${{ parameters.owner }} |

          Provisioned via Backstage Software Template.
        targetPath: claims/${{ parameters.namespace }}

    # Step 3: Register as a Resource entity in the catalog
    - id: register
      name: Register Resource in Catalog
      action: catalog:register
      input:
        repoContentsUrl: https://github.com/my-org/infrastructure-gitops/tree/main
        catalogInfoPath: /claims/${{ parameters.namespace }}/${{ parameters.resourceName }}/catalog-info.yaml

  output:
    links:
      - title: Pull Request
        url: ${{ steps['publish'].output.remoteUrl }}
      - title: Catalog Entity
        icon: catalog
        entityRef: ${{ steps['register'].output.entityRef }}
```

Aurora PostgreSQL データベース用に生成される KRO claim (template skeleton によって作成) は次のとおりです。

```yaml
# claims/<namespace>/<resource-name>/kro-claim.yaml
apiVersion: kro.run/v1alpha1
kind: DatabaseClaim
metadata:
  name: order-db
  namespace: commerce
  labels:
    app.kubernetes.io/managed-by: backstage
    backstage.io/owner: group:commerce-team
    environment: production
spec:
  engine: aurora-postgresql
  engineVersion: "15.4"
  instanceClass: db.r6g.xlarge
  storageSize: 100
  multiAZ: true
  databaseName: appdb
  backupRetentionDays: 30
  deletionProtection: true
```

### ArgoCD Integration Plugin

自動デプロイのために Backstage templates を [ArgoCD](../gitops/argocd/02-applications.md) と連携させるには、ArgoCD scaffolder action をインストールします。

```bash
yarn --cwd packages/backend add @roadiehq/scaffolder-backend-argocd
```

```typescript
// packages/backend/src/index.ts
backend.add(import('@roadiehq/scaffolder-backend-argocd'));
```

ArgoCD 設定を追加します。

```yaml
# app-config.yaml
argocd:
  appLocatorMethods:
    - type: config
      instances:
        - name: main
          url: https://argocd.example.com
          token: ${ARGOCD_AUTH_TOKEN}
```

これにより、templates に ArgoCD steps を含めることができます。

```yaml
# In a template step
- id: create-argocd-app
  name: Create ArgoCD Application
  action: argocd:create-resources
  input:
    appName: ${{ parameters.serviceName }}-${{ parameters.environment }}
    argoInstance: main
    namespace: argocd
    repoUrl: ${{ steps['publish'].output.remoteUrl }}
    path: deploy/helm
    projectName: ${{ parameters.namespace }}
```

---

## TechDocs

TechDocs は、MkDocs ベースの Markdown ドキュメントを developer portal 内に直接レンダリングし、Backstage に「docs-like-code」体験をもたらします。

### How TechDocs Works

1. ドキュメントはソースコードと並べて Markdown ファイルとして記述される
2. `mkdocs.yml` 設定ファイルがドキュメント構造を定義する
3. TechDocs がドキュメントを静的 HTML にビルドする
4. ビルドされたドキュメントは配信のために S3 (または GCS/Azure Blob) に保存される
5. 開発者は、所有コンポーネントに関連付けられたドキュメントを Backstage UI で直接読む

### Configuration for S3 Storage

```yaml
# app-config.yaml
techdocs:
  builder: external
  generator:
    runIn: local
  publisher:
    type: awsS3
    awsS3:
      bucketName: backstage-techdocs
      region: ap-northeast-2
      bucketRootPath: /
      accountId: "111122223333"
      credentials:
        roleArn: arn:aws:iam::111122223333:role/backstage-techdocs-role
```

### S3 Bucket Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BackstageTechDocsReadWrite",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111122223333:role/backstage-techdocs-role"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::backstage-techdocs",
        "arn:aws:s3:::backstage-techdocs/*"
      ]
    }
  ]
}
```

### MkDocs Configuration in Service Repositories

TechDocs を公開する各サービスは、リポジトリのルートに `mkdocs.yml` が必要です。

```yaml
# mkdocs.yml (in the service repository)
site_name: Order Service Documentation
site_description: Technical documentation for the Order Service
plugins:
  - techdocs-core
nav:
  - Home: index.md
  - Architecture: architecture.md
  - API Reference: api-reference.md
  - Runbook: runbook.md
  - ADRs:
      - ADR-001 Database Choice: adrs/001-database-choice.md
      - ADR-002 Event Schema: adrs/002-event-schema.md
```

対応する `catalog-info.yaml` annotation は次のとおりです。

```yaml
metadata:
  annotations:
    backstage.io/techdocs-ref: dir:.
```

### External TechDocs Build Pipeline

`external` builder モードでは、マージのたびにドキュメントをビルドして公開する CI job をセットアップします。

```yaml
# .github/workflows/techdocs.yaml
name: Build and Publish TechDocs
on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - 'mkdocs.yml'

jobs:
  publish-techdocs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install mkdocs-techdocs-core==1.4.*

      - name: Build TechDocs
        run: npx @techdocs/cli generate --no-docker

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::111122223333:role/techdocs-publisher
          aws-region: ap-northeast-2

      - name: Publish TechDocs
        run: |
          npx @techdocs/cli publish \
            --publisher-type awsS3 \
            --storage-name backstage-techdocs \
            --entity default/Component/order-service \
            --awsRoleArn arn:aws:iam::111122223333:role/techdocs-publisher \
            --awsRegion ap-northeast-2
```

---

## Plugin Ecosystem for EKS

Backstage のプラグインシステムは最大の強みです。次のプラグインは、Amazon EKS 上でワークロードを実行しているチームにとって特に価値があります。

### Kubernetes Plugin

Kubernetes プラグインは、カタログエンティティページから直接、Pod と Deployment の状態をリアルタイムに可視化します。

**表示される内容:**

- Pod 数と状態 (Running、Pending、CrashLoopBackOff)
- Deployment replica の状態 (desired と available)
- 最近の Pod event とエラーメッセージ
- HPA の現在値とターゲットメトリクス
- コンテナリソース使用率 (CPU、memory)

**Frontend integration:**

```typescript
// packages/app/src/components/catalog/EntityPage.tsx
import { EntityKubernetesContent } from '@backstage/plugin-kubernetes';

// Add to the service entity page
const serviceEntityPage = (
  <EntityLayout>
    <EntityLayout.Route path="/" title="Overview">
      {/* overview content */}
    </EntityLayout.Route>
    <EntityLayout.Route path="/kubernetes" title="Kubernetes">
      <EntityKubernetesContent refreshIntervalMs={10000} />
    </EntityLayout.Route>
  </EntityLayout>
);
```

### ArgoCD Plugin

ArgoCD プラグインは、各コンポーネントの GitOps デプロイの同期状態、健全性、履歴を表示します。

**Installation:**

```bash
# Frontend
yarn --cwd packages/app add @roadiehq/backstage-plugin-argo-cd

# Backend
yarn --cwd packages/backend add @roadiehq/backstage-plugin-argo-cd-backend
```

**Configuration:**

```yaml
# app-config.yaml
argocd:
  appLocatorMethods:
    - type: config
      instances:
        - name: main
          url: https://argocd.example.com
          token: ${ARGOCD_AUTH_TOKEN}
```

**Catalog annotation:**

```yaml
metadata:
  annotations:
    argocd/app-name: order-service
```

**Frontend integration:**

```typescript
// packages/app/src/components/catalog/EntityPage.tsx
import {
  EntityArgoCDOverviewCard,
  EntityArgoCDHistoryCard,
} from '@roadiehq/backstage-plugin-argo-cd';

// Add to the overview page
const overviewContent = (
  <Grid container spacing={3}>
    <Grid item md={6}>
      <EntityArgoCDOverviewCard />
    </Grid>
    <Grid item md={6}>
      <EntityArgoCDHistoryCard />
    </Grid>
  </Grid>
);
```

### Kubecost Plugin

Kubecost プラグインはサービス単位のコスト可視化を提供し、各コンポーネントがコンピュート、メモリ、ストレージの観点でどれだけコストをかけているかを示します。

**Installation:**

```bash
yarn --cwd packages/app add @kubecost/backstage-plugin
yarn --cwd packages/backend add @kubecost/backstage-plugin-backend
```

**Configuration:**

```yaml
# app-config.yaml
kubecost:
  baseUrl: https://kubecost.example.com
  # Optional: filter by cluster
  clusterFilter: production-eks
```

**Catalog annotation:**

```yaml
metadata:
  annotations:
    kubecost.com/deployment-name: order-service
    kubecost.com/namespace: commerce
```

**Frontend integration:**

```typescript
// packages/app/src/components/catalog/EntityPage.tsx
import { EntityKubecostCard } from '@kubecost/backstage-plugin';

const overviewContent = (
  <Grid container spacing={3}>
    <Grid item md={6}>
      <EntityKubecostCard />
    </Grid>
  </Grid>
);
```

### KEDA and Karpenter Visibility (Custom Plugin Concept)

KEDA や Karpenter の公式 Backstage プラグインはありませんが、Kubernetes API に ScaledObject と NodePool リソースを照会し、スケーリングメトリクスをコンポーネントと並べて表示するカスタムプラグインを構築できます。

**Custom plugin backend concept:**

```typescript
// plugins/keda-backend/src/router.ts
import { Router } from 'express';
import { Logger } from 'winston';
import { Config } from '@backstage/config';

export async function createRouter(options: {
  logger: Logger;
  config: Config;
}): Promise<Router> {
  const router = Router();

  router.get('/scaled-objects/:namespace/:name', async (req, res) => {
    const { namespace, name } = req.params;

    // Query the Kubernetes API for ScaledObject
    const scaledObject = await k8sClient.getNamespacedCustomObject(
      'keda.sh',
      'v1alpha1',
      namespace,
      'scaledobjects',
      name,
    );

    res.json({
      name: scaledObject.body.metadata.name,
      minReplicas: scaledObject.body.spec.minReplicaCount,
      maxReplicas: scaledObject.body.spec.maxReplicaCount,
      triggers: scaledObject.body.spec.triggers,
      currentReplicas: scaledObject.body.status?.currentReplicas,
    });
  });

  return router;
}
```

**Custom plugin frontend concept:**

```typescript
// plugins/keda/src/components/KedaCard.tsx
import React from 'react';
import { InfoCard, Progress } from '@backstage/core-components';
import { useEntity } from '@backstage/plugin-catalog-react';
import useAsync from 'react-use/lib/useAsync';

export const KedaScalingCard = () => {
  const { entity } = useEntity();
  const namespace =
    entity.metadata.annotations?.['backstage.io/kubernetes-namespace'];
  const name = entity.metadata.name;

  const { value, loading, error } = useAsync(async () => {
    const response = await fetch(
      `/api/keda/scaled-objects/${namespace}/${name}`,
    );
    return response.json();
  });

  if (loading) return <Progress />;
  if (error) return <div>Error loading KEDA data: {error.message}</div>;

  return (
    <InfoCard title="KEDA Autoscaling">
      <p>Min Replicas: {value?.minReplicas}</p>
      <p>Max Replicas: {value?.maxReplicas}</p>
      <p>Current Replicas: {value?.currentReplicas}</p>
      <p>Triggers: {value?.triggers?.length}</p>
    </InfoCard>
  );
};
```

### Plugin Summary

| Plugin | Purpose | Data Source | Installation |
|--------|---------|-------------|--------------|
| **@backstage/plugin-kubernetes** | Pod/Deployment status | Kubernetes API | Official |
| **@roadiehq/backstage-plugin-argo-cd** | Sync status, deploy history | ArgoCD API | Community (Roadie) |
| **@kubecost/backstage-plugin** | Per-service cost breakdown | Kubecost API | Community (Kubecost) |
| **Custom KEDA Plugin** | Autoscaler status | Kubernetes API (keda.sh CRDs) | Custom build |
| **Custom Karpenter Plugin** | Node provisioning status | Kubernetes API (karpenter.sh CRDs) | Custom build |
| **@backstage/plugin-techdocs** | Documentation viewer | S3 / GCS | Official |
| **@backstage/plugin-github-actions** | CI pipeline status | GitHub API | Official |

---

## RBAC and Governance

### Permission Framework Overview

Backstage には、カタログエンティティ、templates、プラグイン機能へのアクセスを制御する組み込みの permission framework があります。permission system はポリシーベースで、カタログの所有権モデルと統合されます。

```mermaid
graph LR
    Request["User Request"] --> Policy["Permission Policy"]
    Policy --> Decision{"Allow / Deny / Conditional"}
    Decision -->|Allow| Action["Execute Action"]
    Decision -->|Deny| Reject["403 Forbidden"]
    Decision -->|Conditional| Filter["Filter Results"]

    Catalog["Catalog Ownership"] --> Policy
    Groups["Group Membership"] --> Policy
```

### Enabling the Permission Framework

```yaml
# app-config.yaml
permission:
  enabled: true
```

### Team-Based Access Control

所有権ベースのアクセスを強制するカスタム permission policy を実装します。

```typescript
// packages/backend/src/plugins/permission.ts
import {
  PolicyDecision,
  AuthorizeResult,
  isPermission,
} from '@backstage/plugin-permission-common';
import {
  PermissionPolicy,
  PolicyQuery,
} from '@backstage/plugin-permission-node';
import {
  catalogEntityDeletePermission,
  catalogEntityCreatePermission,
} from '@backstage/plugin-catalog-common/alpha';
import {
  createCatalogConditionalDecision,
  catalogConditions,
} from '@backstage/plugin-catalog-backend/alpha';
import { BackstageIdentityResponse } from '@backstage/plugin-auth-node';
import { createBackendModule } from '@backstage/backend-plugin-api';
import { policyExtensionPoint } from '@backstage/plugin-permission-node/alpha';

class TeamBasedPermissionPolicy implements PermissionPolicy {
  async handle(
    request: PolicyQuery,
    user?: BackstageIdentityResponse,
  ): Promise<PolicyDecision> {
    // Platform team gets full access
    if (
      user?.identity.ownershipEntityRefs.includes(
        'group:default/platform-team',
      )
    ) {
      return { result: AuthorizeResult.ALLOW };
    }

    // Only owners can delete catalog entities
    if (isPermission(request.permission, catalogEntityDeletePermission)) {
      if (!user) {
        return { result: AuthorizeResult.DENY };
      }
      return createCatalogConditionalDecision(request.permission, {
        anyOf: user.identity.ownershipEntityRefs.map((ref) =>
          catalogConditions.isEntityOwner({ claims: [ref] }),
        ),
      });
    }

    // Everyone can create entities and view the catalog
    if (isPermission(request.permission, catalogEntityCreatePermission)) {
      return { result: AuthorizeResult.ALLOW };
    }

    // Default: allow read operations
    return { result: AuthorizeResult.ALLOW };
  }
}

export const permissionModule = createBackendModule({
  pluginId: 'permission',
  moduleId: 'team-based-policy',
  register(reg) {
    reg.registerInit({
      deps: { policy: policyExtensionPoint },
      async init({ policy }) {
        policy.setPolicy(new TeamBasedPermissionPolicy());
      },
    });
  },
});
```

### Governance Rules Examples

| Rule | Implementation | Scope |
|------|---------------|-------|
| **Only owners can delete entities** | Conditional permission on `catalogEntityDeletePermission` | Catalog |
| **Only platform team can create templates** | DENY `templateCreatePermission` unless in platform-team group | Scaffolder |
| **Read-only for external contractors** | DENY all write permissions for contractor group | Global |
| **Template execution requires approval** | Custom approval workflow step in templates | Scaffolder |
| **Production deployments restricted** | Conditional permission based on entity lifecycle | Catalog + ArgoCD |

### Audit Logging

Backstage は、誰が何をしたかを追跡する audit logging をサポートしています。audit log backend を設定します。

```yaml
# app-config.yaml
backend:
  audit:
    enabled: true
    logger:
      type: winston
      options:
        transports:
          - type: console
            level: info
          - type: file
            level: info
            filename: /var/log/backstage/audit.log
            maxsize: 10485760
            maxFiles: 10
```

本番環境では、audit logs を CloudWatch に送信します。

```yaml
# app-config.yaml
backend:
  audit:
    enabled: true
    logger:
      type: winston
      options:
        transports:
          - type: cloudwatch
            level: info
            logGroupName: /backstage/audit
            logStreamName: backstage-production
            region: ap-northeast-2
```

Audit log entries は次を記録します。

- **Who**: 認証されたユーザー ID
- **What**: 実行されたアクション (entity created、template executed、entity deleted)
- **When**: アクションのタイムスタンプ
- **Where**: 対象のエンティティまたはリソース
- **Result**: 成功または失敗とエラー詳細

---

## Production Operations

### High Availability Configuration

本番デプロイでは、ALB の背後で複数の Backstage replicas を実行し、共有外部 PostgreSQL を使用します。

```yaml
# backstage-values.yaml (HA configuration)
backstage:
  replicas: 3

  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 2000m

  podDisruptionBudget:
    enabled: true
    minAvailable: 2

  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchExpressions:
                - key: app.kubernetes.io/name
                  operator: In
                  values:
                    - backstage
            topologyKey: topology.kubernetes.io/zone

  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app.kubernetes.io/name: backstage

  livenessProbe:
    httpGet:
      path: /healthcheck
      port: 7007
    initialDelaySeconds: 60
    periodSeconds: 10
    failureThreshold: 3

  readinessProbe:
    httpGet:
      path: /healthcheck
      port: 7007
    initialDelaySeconds: 30
    periodSeconds: 5
    failureThreshold: 3

postgresql:
  enabled: false  # External RDS with Multi-AZ
```

**HA deployment のアーキテクチャ:**

```
┌─────────────────────────────────────────────────────────────┐
│                        ALB (internet-facing)                 │
│                      backstage.example.com                   │
└──────────┬──────────────────┬──────────────────┬────────────┘
           │                  │                  │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │ Backstage   │    │ Backstage   │    │ Backstage   │
    │ Pod (AZ-a)  │    │ Pod (AZ-b)  │    │ Pod (AZ-c)  │
    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   RDS PostgreSQL   │
                    │   (Multi-AZ)       │
                    └───────────────────┘
```

### Backup and Recovery Strategy

| Component | Backup Method | Frequency | Retention |
|-----------|--------------|-----------|-----------|
| **PostgreSQL (RDS)** | Automated RDS snapshots | Daily | 30 days |
| **PostgreSQL (RDS)** | Point-in-time recovery | Continuous | 35 days |
| **TechDocs (S3)** | S3 versioning + cross-region replication | Continuous | 90 days |
| **Configuration** | Git repository (app-config.yaml) | Every commit | Indefinite |
| **Catalog entities** | Git repositories (catalog-info.yaml) | Every commit | Indefinite |
| **Secrets** | AWS Secrets Manager with rotation | On change | Versioned |

**RDS backup configuration (Terraform example):**

```hcl
resource "aws_rds_cluster" "backstage" {
  cluster_identifier      = "backstage-db"
  engine                  = "aurora-postgresql"
  engine_version          = "15.4"
  master_username         = "backstage"
  database_name           = "backstage"
  backup_retention_period = 30
  preferred_backup_window = "03:00-04:00"
  deletion_protection     = true
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.backstage.arn

  copy_tags_to_snapshot = true

  tags = {
    Environment = "production"
    Service     = "backstage"
    ManagedBy   = "terraform"
  }
}
```

**Disaster recovery procedure:**

1. **Database corruption or loss**: 最新の RDS automated snapshot から復元するか、point-in-time recovery を使用して特定のタイムスタンプに復旧する
2. **TechDocs loss**: S3 versioning により任意の以前のバージョンを復旧できる。cross-region replica はリージョン障害時のフェイルオーバーを提供する
3. **Configuration drift**: すべての設定は Git にあるため、既知の正常な commit から再デプロイする
4. **Catalog data loss**: Catalog entities は Git repositories で定義されているため、GitHub discovery provider を再トリガーして再取り込みする

### Upgrade Strategy

Backstage は頻繁に (おおよそ毎月) 新しいバージョンをリリースします。次のアップグレード戦略に従ってください。

1. **Pin versions explicitly**: Dockerfile と package.json では常に正確なバージョンタグを使用し、`latest` は使わない
2. **Read the changelog**: アップグレード前に [Backstage changelog](https://github.com/backstage/backstage/blob/master/CHANGELOG.md) を確認し、breaking changes を把握する
3. **Upgrade incrementally**: メジャーバージョンを飛ばさず、minor version を 1 つずつアップグレードする
4. **Test in staging**: まず本番データベーススキーマのコピーを使用して staging 環境にデプロイする
5. **Rolling updates**: readiness probes を備えた Kubernetes rolling update strategy を使用してゼロダウンタイムを確保する

```yaml
# Deployment strategy in values.yaml
backstage:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
```

**Upgrade workflow:**

```bash
# 1. Update Backstage packages
yarn backstage-cli versions:bump --release 1.36.0

# 2. Run database migrations
yarn backstage-cli db:migrate

# 3. Build and test locally
yarn build:backend
yarn test

# 4. Build new container image
docker build -t backstage:v1.36.0 .

# 5. Push to ECR
docker tag backstage:v1.36.0 \
  111122223333.dkr.ecr.ap-northeast-2.amazonaws.com/backstage:v1.36.0
docker push \
  111122223333.dkr.ecr.ap-northeast-2.amazonaws.com/backstage:v1.36.0

# 6. Update Helm values and upgrade
helm upgrade backstage backstage/backstage \
  --namespace backstage \
  --set backstage.image.tag=v1.36.0 \
  --values backstage-values.yaml \
  --wait --timeout 10m
```

---

## Best Practices

### Recommended Practices

1. **Start with the Software Catalog**: Templates の構築やプラグインのインストールに進む前に、完全で正確なカタログに投資します。十分に整備されたカタログは、他のすべてを価値あるものにする基盤です。まず、すべての既存サービスを正しい所有権で登録することから始めます。

2. **Treat Backstage as an Internal Product**: プロダクトオーナーを割り当て、開発者からのフィードバックを収集し、機能を反復改善し、採用指標を追跡します。プラットフォームチームは、他のエンジニアリングチームを顧客とするプロダクトチームです。

3. **Define Golden Paths, Not Golden Cages**: Templates にはベストプラクティスと組織標準を組み込みますが、開発者に正当な理由がある場合は常に逸脱できるようにします。目標は、正しいことを簡単にすることであり、それを唯一の選択肢にすることではありません。

4. **Automate Catalog Population**: 手動登録を要求するのではなく、GitHub discovery プラグインを使用して `catalog-info.yaml` ファイルを自動的に見つけて登録します。これにより摩擦が減り、カタログを最新に保てます。

5. **Keep app-config.yaml in Version Control**: 実行中の cluster 上で設定を手動編集してはいけません。すべての Backstage 設定は Git repository に置き、アプリケーション自体と同じ CI/CD pipeline を通じてデプロイする必要があります。

6. **Invest in Documentation (TechDocs)**: ドキュメントのない developer portal は単なるダッシュボードです。TechDocs をすべてのサービスの要件にします。Golden Path templates に含め、新しいサービスが初日からドキュメントのスキャフォールディングを備えて出荷されるようにします。

7. **Monitor Backstage Itself**: Backstage backend から Prometheus metrics を公開し、API latency、error rates、plugin health のダッシュボードをセットアップします。開発者に提供しているものと同じ observability stack を使用します。

8. **Plan for Plugin Maintenance**: コミュニティプラグインは Backstage core releases に遅れることがあります。プラグインバージョンを固定し、staging でアップグレードをテストし、デプロイに不可欠なプラグインの一覧を維持します。

### Common Pitfalls

1. **Building Too Much, Too Fast**: 初日にすべてのプラグインを入れて Backstage をデプロイしようとすると、複雑さと遅延につながります。カタログと 1 つの template から始め、開発者からのフィードバックに基づいてプラグインを段階的に追加します。

2. **Neglecting Ownership Data**: 所有権情報が欠落していたり不正確だったりするカタログは信頼を損ないます。開発者がサービスの所有者を見つけられなければ、カタログを使わなくなります。`catalog-info.yaml` に対する CI checks を通じて所有権を強制します。

3. **Ignoring Authentication from the Start**: staging であっても、適切な OIDC authentication なしで Backstage をデプロイすると、セキュリティギャップが生まれ、後で RBAC を実装することが難しくなります。Backstage をユーザーに公開する前に認証を設定します。

4. **Treating Backstage as Read-Only**: Backstage の真の力は、カタログデータを見るだけではなく、Software Templates とセルフサービスワークフローにあります。開発者が自分のサービスを見られても、ポータルから新しいサービスを作成できなければ、採用は停滞します。

---

## References

### Official Documentation

- [Backstage Official Documentation](https://backstage.io/docs/overview/what-is-backstage)
- [Backstage GitHub Repository](https://github.com/backstage/backstage)
- [Backstage Plugin Marketplace](https://backstage.io/plugins)
- [Backstage Helm Chart](https://github.com/backstage/charts)

### CNCF and Community

- [CNCF Backstage Project Page](https://www.cncf.io/projects/backstage/)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Backstage Community Sessions](https://github.com/backstage/community)

### AWS and EKS Integration

- [AWS EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [AWS Load Balancer Controller Documentation](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Amazon Cognito Developer Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/)

### Related Documentation in This Repository

- [Platform Engineering Overview](./00-platform-engineering-overview.md) -- IDP concepts, maturity model, and reference architecture
- [Helm Package Manager](./01-helm.md) -- Helm chart packaging used for Backstage deployment
- [AWS Controllers for Kubernetes (ACK)](./02-ack.md) -- Infrastructure provisioning through Kubernetes API
- [Kubernetes Resource Operator (KRO)](./03-kro.md) -- Resource graph orchestration for self-service claims
- [Kubernetes Extension Mechanisms](./04-kubernetes-extensions.md) -- CRDs and operators that power Backstage plugins
- [ExampleCorp Integration Example](./05-example-corp-app.md) -- End-to-end ACK + KRO deployment example
- [Crossplane](./07-crossplane.md) -- Infrastructure as Code via Kubernetes API; integrates with Backstage for self-service
- [ArgoCD Applications](../gitops/argocd/02-applications.md) -- GitOps deployment integrated with Backstage templates
