# Backstage를 활용한 Internal Developer Platform (IDP) 구축

> **지원 버전**: Backstage 1.35+, Kubernetes 1.31, 1.32, 1.33, Amazon EKS
> **마지막 업데이트**: 2026년 6월 22일

## 개요

### Internal Developer Platform (IDP)이란?

Internal Developer Platform(IDP)은 개발자가 인프라의 복잡성을 직접 다루지 않고도 애플리케이션을 빠르고 안전하게 배포할 수 있도록 셀프서비스 기능을 제공하는 내부 플랫폼입니다. [Platform Engineering 개요](./00-platform-engineering-overview.md)에서 설명한 것처럼, IDP는 플랫폼 엔지니어링의 핵심 산출물입니다.

IDP는 다음과 같은 문제를 해결합니다:

- **인지 부하 감소**: 개발자가 Kubernetes, AWS, CI/CD 파이프라인의 세부 사항을 모두 이해할 필요 없이 서비스를 배포
- **표준화**: 조직 전체에 일관된 배포 패턴과 보안 정책을 적용
- **셀프서비스**: 티켓 시스템 없이 개발자가 직접 인프라를 프로비저닝
- **가시성**: 서비스 소유권, 의존성, 기술 문서를 한곳에서 관리

### Backstage란?

[Backstage](https://backstage.io/)는 Spotify가 개발하고 오픈소스로 공개한 IDP 프레임워크입니다. 현재 CNCF Incubating 프로젝트로, 전 세계 수천 개의 조직에서 사용되고 있습니다.

**Backstage의 핵심 가치:**

1. **Software Catalog**: 조직의 모든 소프트웨어(서비스, 라이브러리, 웹사이트, 파이프라인)를 하나의 카탈로그에서 관리
2. **Software Templates**: Golden Path를 통한 표준화된 프로젝트 생성
3. **TechDocs**: 코드와 함께 관리되는 기술 문서를 통합 UI에서 제공
4. **Plugin 생태계**: 200개 이상의 오픈소스 플러그인으로 확장 가능

### IDP 도구 비교

| 비교 기준 | Backstage | Port | Cortex | Humanitec | 자체 구축 |
|-----------|-----------|------|--------|-----------|----------|
| **라이선스** | 오픈소스 (Apache 2.0) | 상용 (무료 티어 있음) | 상용 | 상용 | 해당 없음 |
| **CNCF 프로젝트** | Incubating | 아니오 | 아니오 | 아니오 | 해당 없음 |
| **커스터마이징** | 매우 높음 (React 플러그인) | 중간 (위젯 기반) | 낮음 (SaaS) | 중간 (Score 기반) | 무제한 |
| **호스팅 방식** | 자체 호스팅 | SaaS 또는 자체 호스팅 | SaaS 전용 | SaaS 또는 자체 호스팅 | 자체 호스팅 |
| **플러그인 생태계** | 200+ 오픈소스 플러그인 | 빌트인 통합 | 빌트인 통합 | 빌트인 오케스트레이터 | 직접 구축 |
| **초기 설정 난이도** | 높음 (개발 필요) | 낮음 (노코드 설정) | 낮음 (SaaS) | 중간 | 매우 높음 |
| **운영 비용** | 인프라 + 개발팀 필요 | 구독료 | 구독료 | 구독료 | 인프라 + 개발팀 |

> **참고**: Backstage는 높은 커스터마이징 자유도와 풍부한 플러그인 생태계가 장점이지만, 자체 호스팅과 개발 역량이 필요합니다. 조직의 규모와 엔지니어링 역량에 따라 적합한 도구가 다릅니다.

### 학습 목표

이 문서를 통해 다음을 학습합니다:

1. **Backstage 아키텍처**를 이해하고 핵심 구성 요소의 역할을 설명할 수 있다
2. **Amazon EKS에 Backstage를 배포**하고 RDS, ALB, OIDC 인증을 구성할 수 있다
3. **Software Catalog**를 활용하여 조직의 서비스, 팀, API를 체계적으로 관리할 수 있다
4. **Software Templates**로 Golden Path를 구현하여 표준화된 서비스/인프라 프로비저닝을 자동화할 수 있다
5. **TechDocs**를 S3 백엔드와 통합하여 기술 문서를 중앙 관리할 수 있다
6. **EKS 전용 플러그인**(Kubernetes, ArgoCD, Kubecost)을 설치하고 운영할 수 있다
7. **RBAC과 거버넌스**를 구성하여 팀 기반 접근 제어를 적용할 수 있다

---

## Backstage 아키텍처

### 전체 아키텍처

Backstage는 프론트엔드(React SPA)와 백엔드(Node.js)로 구성된 웹 애플리케이션이며, 플러그인 기반 아키텍처를 통해 기능을 확장합니다.

![개발자와 플랫폼 엔지니어가 Backstage UI를 통해 백엔드 API와 플러그인 백엔드를 거쳐 PostgreSQL, S3, GitHub, EKS, ArgoCD, Cognito/Okta 등 저장소 및 외부 시스템과 연동되는 Backstage 애플리케이션 아키텍처를 보여준다.](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-0.png)

### 핵심 구성 요소

Backstage는 네 가지 핵심 기능을 제공합니다:

#### 1. Software Catalog

소프트웨어 카탈로그는 조직의 모든 소프트웨어 자산을 하나의 통합 뷰에서 관리합니다.

- **Entity 기반 모델**: Component, API, System, Domain, Resource, Group, User 등의 엔티티로 소프트웨어를 모델링
- **소유권 추적**: 각 서비스의 소유 팀과 담당자를 명확하게 관리
- **의존성 시각화**: 서비스 간 의존성을 그래프로 시각화
- **자동 발견**: GitHub, GitLab 등에서 `catalog-info.yaml`을 자동으로 검색하여 카탈로그에 등록

#### 2. Software Templates (Scaffolder)

소프트웨어 템플릿은 Golden Path를 구현하는 도구입니다.

- **프로젝트 스캐폴딩**: 표준화된 프로젝트 구조를 자동 생성
- **매개변수 UI**: 사용자 입력을 받아 템플릿을 커스터마이징
- **액션 체인**: Git 저장소 생성, CI/CD 파이프라인 설정, 카탈로그 등록 등을 자동화
- **Golden Path 제공**: 검증된 배포 패턴을 개발자에게 제공

#### 3. TechDocs

TechDocs는 "docs-as-code" 철학을 구현합니다.

- **MkDocs 기반**: Markdown으로 작성된 문서를 자동으로 빌드하고 렌더링
- **코드 리포지토리 통합**: 문서가 코드와 같은 저장소에 위치하여 항상 최신 상태 유지
- **검색 통합**: Backstage 검색을 통해 모든 기술 문서를 검색 가능
- **S3 백엔드**: 빌드된 문서를 S3에 저장하여 확장성 확보

#### 4. Plugin 시스템

Backstage의 확장성의 핵심입니다.

- **프론트엔드 플러그인**: React 컴포넌트로 UI 확장
- **백엔드 플러그인**: Node.js 모듈로 API 확장
- **풍부한 생태계**: Kubernetes, ArgoCD, Prometheus, Grafana, Jenkins, GitHub Actions 등 200개 이상의 플러그인

### 플러그인 아키텍처 상세

Backstage의 플러그인은 독립적으로 개발되고 배포될 수 있는 모듈입니다:

```
backstage-app/
├── packages/
│   ├── app/                          # 프론트엔드 애플리케이션
│   │   └── src/
│   │       └── App.tsx               # 플러그인 라우트 등록
│   └── backend/                      # 백엔드 애플리케이션
│       └── src/
│           └── index.ts              # 백엔드 플러그인 등록
├── plugins/                          # 커스텀 플러그인 디렉토리
│   ├── my-custom-plugin/             # 프론트엔드 플러그인
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── api/
│   │   │   └── plugin.ts
│   │   └── package.json
│   └── my-custom-plugin-backend/     # 백엔드 플러그인
│       ├── src/
│       │   ├── service/
│       │   └── plugin.ts
│       └── package.json
├── app-config.yaml                   # 애플리케이션 설정
└── package.json
```

플러그인 개발 시 주요 구성 요소:

- **plugin.ts**: 플러그인 진입점, API 참조와 라우트 정의
- **ApiRef**: 백엔드 API와의 통신을 위한 인터페이스
- **EntityPage**: 카탈로그 엔티티 페이지에 탭/카드를 추가하는 컴포넌트
- **Extension Point**: 다른 플러그인이 확장할 수 있는 지점을 정의

---

## EKS 배포

### 사전 요구 사항

Amazon EKS에 Backstage를 배포하기 위해 다음 리소스가 필요합니다:

| 리소스 | 용도 | 설명 |
|--------|------|------|
| **EKS 클러스터** | Backstage 호스팅 | Kubernetes 1.31 이상 권장 |
| **Amazon ECR** | 컨테이너 이미지 저장소 | Backstage Docker 이미지를 저장 |
| **Amazon RDS (PostgreSQL)** | 데이터베이스 | Software Catalog, 검색 인덱스 등의 데이터 저장 |
| **Amazon ALB** | 로드 밸런서 | HTTPS 트래픽 처리 및 SSL 종료 |
| **Amazon S3** | TechDocs 저장소 | 빌드된 기술 문서 저장 |
| **Amazon Cognito 또는 Okta** | 인증 | OIDC 기반 사용자 인증 |
| **ACM 인증서** | SSL/TLS | ALB용 HTTPS 인증서 |
| **Route 53** | DNS | backstage.example.com 도메인 설정 |

### Backstage 앱 생성

Backstage 공식 CLI를 사용하여 애플리케이션을 스캐폴딩합니다:

```bash
# Backstage CLI 설치
npm install -g @backstage/create-app

# 새 Backstage 앱 생성
npx @backstage/create-app@latest --name my-backstage-app

# 생성된 디렉토리로 이동
cd my-backstage-app

# 의존성 설치 확인
yarn install

# 로컬 개발 서버 실행 (선택 사항)
yarn dev
```

### Dockerfile 작성

프로덕션 배포를 위한 멀티 스테이지 Dockerfile을 작성합니다:

```dockerfile
# Stage 1: 의존성 설치 및 빌드
FROM node:20-bookworm-slim AS build

# Python과 빌드 도구 설치 (네이티브 모듈 빌드에 필요)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

USER node
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY --chown=node:node package.json yarn.lock ./
COPY --chown=node:node packages/backend/package.json packages/backend/
COPY --chown=node:node packages/app/package.json packages/app/
COPY --chown=node:node plugins/ plugins/

RUN yarn install --frozen-lockfile --network-timeout 600000

# 소스 코드 복사 및 빌드
COPY --chown=node:node . .
RUN yarn tsc
RUN yarn build:backend --config ../../app-config.yaml

# Stage 2: 프로덕션 이미지
FROM node:20-bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    && rm -rf /var/lib/apt/lists/*

USER node
WORKDIR /app

# 빌드된 백엔드 복사
COPY --from=build --chown=node:node /app/packages/backend/dist ./packages/backend/dist
COPY --from=build --chown=node:node /app/node_modules ./node_modules

# app-config 복사
COPY --chown=node:node app-config.yaml ./
COPY --chown=node:node app-config.production.yaml ./

# 환경 변수 설정
ENV NODE_ENV=production

# 포트 노출
EXPOSE 7007

# 백엔드 실행
CMD ["node", "packages/backend/dist", "--config", "app-config.yaml", "--config", "app-config.production.yaml"]
```

ECR에 이미지를 푸시합니다:

```bash
# ECR 리포지토리 생성
aws ecr create-repository --repository-name backstage --region ap-northeast-2

# Docker 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com

# 이미지 빌드 및 푸시
docker build -t backstage .
docker tag backstage:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/backstage:v1.0.0
docker push 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/backstage:v1.0.0
```

### Helm Chart 배포

Backstage 공식 Helm Chart를 사용하여 EKS에 배포합니다. 아래는 프로덕션 환경을 위한 `values.yaml`입니다:

```yaml
# Backstage Helm Chart values.yaml
# Chart: backstage/backstage

global:
  imageRegistry: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com

backstage:
  image:
    registry: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
    repository: backstage
    tag: "v1.0.0"
    pullPolicy: IfNotPresent

  replicas: 2

  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "1000m"

  extraEnvVars:
    - name: APP_CONFIG_app_baseUrl
      value: "https://backstage.example.com"
    - name: APP_CONFIG_backend_baseUrl
      value: "https://backstage.example.com"

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

serviceAccount:
  create: true
  name: backstage
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/backstage-irsa-role

service:
  type: ClusterIP
  ports:
    backend: 7007

postgresql:
  enabled: false  # 외부 RDS 사용

ingress:
  enabled: false  # ALB Ingress를 별도로 관리
```

Helm Chart를 설치합니다:

```bash
# Backstage Helm 리포지토리 추가
helm repo add backstage https://backstage.github.io/charts
helm repo update

# Namespace 생성
kubectl create namespace backstage

# Secrets 생성 (RDS 접속 정보)
kubectl create secret generic backstage-secrets \
  --namespace backstage \
  --from-literal=POSTGRES_HOST=backstage-db.cluster-xxxxxxxxxxxx.ap-northeast-2.rds.amazonaws.com \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_USER=backstage \
  --from-literal=POSTGRES_PASSWORD='<secure-password>' \
  --from-literal=GITHUB_TOKEN='ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# Helm 설치
helm install backstage backstage/backstage \
  --namespace backstage \
  --values values.yaml \
  --wait
```

### ALB Ingress 구성

AWS Load Balancer Controller를 사용하여 ALB Ingress를 구성합니다:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: backstage-ingress
  namespace: backstage
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:123456789012:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /healthcheck
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "30"
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: "5"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "3"
    alb.ingress.kubernetes.io/security-groups: sg-xxxxxxxxxxxxxxxxx
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:ap-northeast-2:123456789012:regional/webacl/backstage-waf/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    alb.ingress.kubernetes.io/tags: Environment=production,Team=platform
spec:
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

### PostgreSQL via RDS 구성

[ACK](./02-ack.md)를 사용하여 RDS를 프로비저닝하거나 AWS 콘솔/Terraform으로 생성할 수 있습니다. Backstage의 `app-config.yaml`에서 데이터베이스 연결을 설정합니다:

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
        idleTimeoutMillis: 600000
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

> **참고**: RDS 인스턴스는 반드시 EKS 클러스터와 동일한 VPC 또는 VPC 피어링이 설정된 네트워크에 있어야 합니다. 보안 그룹에서 EKS 워커 노드의 서브넷에서 5432 포트 접근을 허용하세요.

### OIDC 인증 설정 (Amazon Cognito)

Backstage의 인증을 Amazon Cognito OIDC와 통합합니다:

```yaml
# app-config.production.yaml - 인증 섹션
auth:
  environment: production
  providers:
    oidc:
      production:
        metadataUrl: https://cognito-idp.ap-northeast-2.amazonaws.com/<user-pool-id>/.well-known/openid-configuration
        clientId: ${AUTH_OIDC_CLIENT_ID}
        clientSecret: ${AUTH_OIDC_CLIENT_SECRET}
        prompt: auto
        scope: "openid profile email"
        signIn:
          resolvers:
            - resolver: emailMatchingUserEntityProfileEmail
```

Okta를 사용하는 경우:

```yaml
# app-config.production.yaml - Okta 인증
auth:
  environment: production
  providers:
    okta:
      production:
        clientId: ${AUTH_OKTA_CLIENT_ID}
        clientSecret: ${AUTH_OKTA_CLIENT_SECRET}
        audience: ${AUTH_OKTA_AUDIENCE}
        authServerId: ${AUTH_OKTA_AUTH_SERVER_ID}
        idp: ${AUTH_OKTA_IDP}
        signIn:
          resolvers:
            - resolver: emailMatchingUserEntityProfileEmail
```

인증 백엔드 플러그인을 등록합니다:

```typescript
// packages/backend/src/index.ts
import { createBackend } from '@backstage/backend-defaults';

const backend = createBackend();

// 핵심 플러그인
backend.add(import('@backstage/plugin-app-backend'));
backend.add(import('@backstage/plugin-catalog-backend'));
backend.add(import('@backstage/plugin-scaffolder-backend'));
backend.add(import('@backstage/plugin-techdocs-backend'));
backend.add(import('@backstage/plugin-search-backend'));

// 인증 플러그인
backend.add(import('@backstage/plugin-auth-backend'));
backend.add(import('@backstage/plugin-auth-backend-module-oidc-provider'));
// 또는 Okta 사용 시:
// backend.add(import('@backstage/plugin-auth-backend-module-okta-provider'));

backend.start();
```

---

## Software Catalog

### Entity 모델

Backstage Software Catalog는 다양한 Entity 타입을 사용하여 조직의 소프트웨어 생태계를 모델링합니다.

![payments-domain 아래 order-system과 payment-system이 있고 각 시스템의 컴포넌트가 API를 제공/소비하고 리소스에 의존하며, platform-team과 backend-team이 각 시스템을 소유하는 Backstage 카탈로그 엔티티 관계를 보여준다.](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-1.png)

### Entity 타입 개요

| Entity 타입 | 설명 | 예시 |
|-------------|------|------|
| **Component** | 소프트웨어 구성 요소 (서비스, 라이브러리, 웹사이트) | order-api, payment-sdk |
| **System** | 관련 Component들의 논리적 그룹 | order-system |
| **Domain** | 비즈니스 영역 | commerce-domain |
| **API** | Component가 제공하거나 소비하는 인터페이스 | order-rest-api |
| **Resource** | Component가 의존하는 인프라 | order-db, payment-queue |
| **Group** | 조직 내 팀 또는 부서 | backend-team |
| **User** | 조직 내 개별 사용자 | alice |

### Entity 타입별 catalog-info.yaml 예제

#### Component (서비스)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: order-api
  title: Order API Service
  description: 주문 처리를 위한 REST API 서비스
  annotations:
    backstage.io/techdocs-ref: dir:.
    github.com/project-slug: my-org/order-api
    backstage.io/kubernetes-id: order-api
    backstage.io/kubernetes-namespace: production
    argocd/app-name: order-api
    backstage.io/kubernetes-label-selector: app=order-api
  tags:
    - java
    - spring-boot
    - grpc
  links:
    - url: https://grafana.example.com/d/order-api
      title: Grafana Dashboard
      icon: dashboard
    - url: https://argocd.example.com/applications/order-api
      title: ArgoCD
      icon: deployment
spec:
  type: service
  lifecycle: production
  owner: group:backend-team
  system: order-system
  providesApis:
    - order-rest-api
  consumesApis:
    - payment-grpc-api
  dependsOn:
    - resource:order-db
    - component:auth-service
```

#### System

```yaml
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: order-system
  title: Order Management System
  description: 주문 접수, 처리, 이행을 관리하는 시스템
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - core-business
spec:
  owner: group:backend-team
  domain: commerce-domain
```

#### Domain

```yaml
apiVersion: backstage.io/v1alpha1
kind: Domain
metadata:
  name: commerce-domain
  title: Commerce Domain
  description: 전자상거래 핵심 도메인 -- 주문, 결제, 재고 관리
spec:
  owner: group:platform-team
```

#### API

```yaml
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: order-rest-api
  title: Order REST API
  description: 주문 생성, 조회, 수정을 위한 RESTful API
  tags:
    - rest
    - json
spec:
  type: openapi
  lifecycle: production
  owner: group:backend-team
  system: order-system
  definition: |
    openapi: "3.0.0"
    info:
      title: Order API
      version: "1.0.0"
      description: 주문 관리 REST API
    paths:
      /orders:
        get:
          summary: 주문 목록 조회
          responses:
            "200":
              description: 주문 목록 반환
        post:
          summary: 새 주문 생성
          responses:
            "201":
              description: 주문 생성 완료
      /orders/{orderId}:
        get:
          summary: 주문 상세 조회
          parameters:
            - name: orderId
              in: path
              required: true
              schema:
                type: string
          responses:
            "200":
              description: 주문 상세 정보 반환
```

#### Resource

```yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: order-db
  title: Order Database
  description: 주문 데이터를 저장하는 Aurora PostgreSQL 인스턴스
  annotations:
    aws.amazon.com/rds-instance: order-db-cluster
  tags:
    - postgresql
    - aurora
spec:
  type: database
  lifecycle: production
  owner: group:platform-team
  system: order-system
  dependencyOf:
    - component:order-api
    - component:order-worker
```

#### Group (팀)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: backend-team
  title: Backend Engineering Team
  description: 백엔드 서비스 개발 및 운영 담당 팀
spec:
  type: team
  profile:
    displayName: Backend Team
    email: backend-team@example.com
    picture: https://example.com/teams/backend.png
  parent: engineering-department
  children: []
  members:
    - alice
    - bob
    - charlie
```

#### User

```yaml
apiVersion: backstage.io/v1alpha1
kind: User
metadata:
  name: alice
  title: Alice Kim
spec:
  profile:
    displayName: Alice Kim
    email: alice@example.com
    picture: https://example.com/photos/alice.jpg
  memberOf:
    - backend-team
```

### GitHub 자동 발견 (Auto-Discovery)

GitHub Organization의 모든 저장소에서 `catalog-info.yaml`을 자동으로 검색하여 카탈로그에 등록할 수 있습니다.

플러그인을 설치합니다:

```bash
# 백엔드 플러그인 설치
yarn --cwd packages/backend add @backstage/plugin-catalog-backend-module-github
```

백엔드에 플러그인을 등록합니다:

```typescript
// packages/backend/src/index.ts
backend.add(import('@backstage/plugin-catalog-backend-module-github'));
```

`app-config.yaml`에 GitHub 통합과 자동 발견을 설정합니다:

```yaml
# app-config.yaml - GitHub 통합 및 자동 발견
integrations:
  github:
    - host: github.com
      token: ${GITHUB_TOKEN}

catalog:
  providers:
    github:
      myOrgProvider:
        organization: "my-org"
        catalogPath: "/catalog-info.yaml"
        filters:
          branch: "main"
          repository: ".*"
        schedule:
          frequency:
            minutes: 30
          timeout:
            minutes: 3
          initialDelay:
            seconds: 15

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

  locations:
    # 조직 전체 엔티티 (팀, 도메인 등)
    - type: url
      target: https://github.com/my-org/backstage-entities/blob/main/org-structure.yaml
      rules:
        - allow: [Group, User, Domain, System]

    # 로컬 템플릿 (Software Templates)
    - type: file
      target: ../../templates/*/template.yaml
      rules:
        - allow: [Template]
```

### Kubernetes 클러스터 통합

Backstage에서 EKS 클러스터의 워크로드 상태를 확인하려면 Kubernetes 플러그인을 설치하고 설정해야 합니다.

#### 플러그인 설치

```bash
# 프론트엔드 플러그인
yarn --cwd packages/app add @backstage/plugin-kubernetes

# 백엔드 플러그인
yarn --cwd packages/backend add @backstage/plugin-kubernetes-backend
```

#### 백엔드 플러그인 등록

```typescript
// packages/backend/src/index.ts
backend.add(import('@backstage/plugin-kubernetes-backend'));
```

#### 프론트엔드 Entity 페이지에 탭 추가

```typescript
// packages/app/src/components/catalog/EntityPage.tsx
import { EntityKubernetesContent } from '@backstage/plugin-kubernetes';

const serviceEntityPage = (
  <EntityLayout>
    <EntityLayout.Route path="/" title="Overview">
      {/* ... */}
    </EntityLayout.Route>
    <EntityLayout.Route path="/kubernetes" title="Kubernetes">
      <EntityKubernetesContent refreshIntervalMs={30000} />
    </EntityLayout.Route>
  </EntityLayout>
);
```

#### EKS 클러스터 연결 설정

`app-config.yaml`에 EKS 클러스터 정보를 설정합니다:

```yaml
# app-config.yaml - Kubernetes 설정
kubernetes:
  serviceLocatorMethod:
    type: multiTenant
  clusterLocatorMethods:
    - type: config
      clusters:
        - url: https://ABCDEF1234567890.gr7.ap-northeast-2.eks.amazonaws.com
          name: production-eks
          authProvider: serviceAccount
          skipTLSVerify: false
          skipMetricsLookup: false
          serviceAccountToken: ${K8S_PRODUCTION_SA_TOKEN}
          caData: ${K8S_PRODUCTION_CA_DATA}
          dashboardUrl: https://console.aws.amazon.com/eks/home?region=ap-northeast-2#/clusters/production-eks
          dashboardApp: aws
        - url: https://FEDCBA0987654321.gr7.ap-northeast-2.eks.amazonaws.com
          name: staging-eks
          authProvider: serviceAccount
          serviceAccountToken: ${K8S_STAGING_SA_TOKEN}
          caData: ${K8S_STAGING_CA_DATA}
          dashboardUrl: https://console.aws.amazon.com/eks/home?region=ap-northeast-2#/clusters/staging-eks
          dashboardApp: aws
  customResources:
    - group: "argoproj.io"
      apiVersion: "v1alpha1"
      plural: "rollouts"
    - group: "keda.sh"
      apiVersion: "v1alpha1"
      plural: "scaledobjects"
```

#### Backstage 전용 ServiceAccount 및 RBAC

EKS 클러스터에서 Backstage가 리소스를 읽을 수 있도록 ServiceAccount와 ClusterRole을 생성합니다:

```yaml
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
  annotations:
    description: "Backstage가 클러스터 리소스를 읽기 위한 ServiceAccount"
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
      - events
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
  - apiGroups: ["argoproj.io"]
    resources:
      - rollouts
      - applications
    verbs: ["get", "list", "watch"]
  - apiGroups: ["keda.sh"]
    resources:
      - scaledobjects
      - scaledjobs
    verbs: ["get", "list", "watch"]
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

ServiceAccount 토큰을 추출하여 Backstage 설정에 사용합니다:

```bash
# ServiceAccount 토큰 추출
kubectl get secret backstage-reader-token \
  -n backstage-system \
  -o jsonpath='{.data.token}' | base64 --decode

# CA 인증서 추출
kubectl get secret backstage-reader-token \
  -n backstage-system \
  -o jsonpath='{.data.ca\.crt}'
```

---

## Software Templates (Golden Paths)

### 템플릿 구조

Backstage Software Templates는 Scaffolder 플러그인을 통해 실행됩니다. 각 템플릿은 `template.yaml` 파일로 정의되며, 다음 구조를 따릅니다:

```
templates/
├── microservice-golden-path/
│   ├── template.yaml          # 템플릿 정의
│   ├── skeleton/              # 스캐폴딩 파일
│   │   ├── catalog-info.yaml  # Backstage 카탈로그 등록
│   │   ├── Dockerfile
│   │   ├── src/
│   │   ├── helm/
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   └── templates/
│   │   ├── .github/
│   │   │   └── workflows/
│   │   │       └── ci.yaml
│   │   └── argocd/
│   │       └── application.yaml
│   └── docs/
│       └── index.md
├── infra-provisioning/
│   ├── template.yaml
│   └── skeleton/
└── frontend-app/
    ├── template.yaml
    └── skeleton/
```

### 마이크로서비스 Golden Path 템플릿

개발자가 새로운 마이크로서비스를 생성할 때 사용하는 템플릿입니다. Dockerfile, Helm Chart, ArgoCD Application, GitHub Actions CI 파이프라인을 자동으로 스캐폴딩합니다.

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: microservice-golden-path
  title: Microservice Golden Path
  description: |
    표준화된 마이크로서비스를 생성합니다.
    Dockerfile, Helm Chart, ArgoCD Application, GitHub Actions CI를 포함합니다.
  tags:
    - microservice
    - golden-path
    - recommended
  annotations:
    backstage.io/techdocs-ref: dir:.
spec:
  owner: group:platform-team
  type: service

  parameters:
    - title: 서비스 기본 정보
      required:
        - serviceName
        - owner
        - description
      properties:
        serviceName:
          title: 서비스 이름
          type: string
          description: 마이크로서비스의 이름 (소문자, 하이픈 구분)
          pattern: "^[a-z][a-z0-9-]*$"
          maxLength: 40
          ui:autofocus: true
          ui:help: "예: order-api, payment-service"
        description:
          title: 서비스 설명
          type: string
          description: 서비스에 대한 간략한 설명
        owner:
          title: 소유 팀
          type: string
          description: 서비스를 소유하는 팀
          ui:field: OwnerPicker
          ui:options:
            catalogFilter:
              kind: Group
        system:
          title: 시스템
          type: string
          description: 서비스가 속하는 시스템
          ui:field: EntityPicker
          ui:options:
            catalogFilter:
              kind: System

    - title: 기술 스택 선택
      required:
        - language
        - port
      properties:
        language:
          title: 프로그래밍 언어
          type: string
          description: 마이크로서비스의 프로그래밍 언어
          enum:
            - java-spring-boot
            - node-express
            - python-fastapi
            - go-gin
          enumNames:
            - "Java (Spring Boot 3.x)"
            - "Node.js (Express)"
            - "Python (FastAPI)"
            - "Go (Gin)"
        port:
          title: 서비스 포트
          type: integer
          description: 컨테이너 리스닝 포트
          default: 8080
        needsDatabase:
          title: 데이터베이스 필요 여부
          type: boolean
          description: PostgreSQL 데이터베이스가 필요한 경우 체크
          default: false

    - title: 배포 환경 설정
      required:
        - environment
      properties:
        environment:
          title: 배포 환경
          type: string
          description: 초기 배포 환경
          enum:
            - staging
            - production
          default: staging
        replicas:
          title: 레플리카 수
          type: integer
          description: 초기 레플리카 수
          default: 2
          minimum: 1
          maximum: 10
        cpuRequest:
          title: CPU 요청량
          type: string
          default: "250m"
        memoryRequest:
          title: 메모리 요청량
          type: string
          default: "256Mi"

  steps:
    # Step 1: 소스코드 스캐폴딩
    - id: fetch-skeleton
      name: 프로젝트 스캐폴딩
      action: fetch:template
      input:
        url: ./skeleton
        values:
          serviceName: ${{ parameters.serviceName }}
          description: ${{ parameters.description }}
          owner: ${{ parameters.owner }}
          system: ${{ parameters.system }}
          language: ${{ parameters.language }}
          port: ${{ parameters.port }}
          needsDatabase: ${{ parameters.needsDatabase }}
          environment: ${{ parameters.environment }}
          replicas: ${{ parameters.replicas }}
          cpuRequest: ${{ parameters.cpuRequest }}
          memoryRequest: ${{ parameters.memoryRequest }}

    # Step 2: GitHub 리포지토리 생성
    - id: publish
      name: GitHub 리포지토리 생성
      action: publish:github
      input:
        allowedHosts: ["github.com"]
        repoUrl: github.com?owner=my-org&repo=${{ parameters.serviceName }}
        description: ${{ parameters.description }}
        defaultBranch: main
        repoVisibility: internal
        collaborators:
          - team: ${{ parameters.owner }}
            access: maintain
          - team: platform-team
            access: admin
        topics:
          - backstage
          - microservice
          - ${{ parameters.language }}

    # Step 3: ArgoCD Application 등록
    - id: create-argocd-app
      name: ArgoCD Application 생성
      action: argocd:create-resources
      input:
        appName: ${{ parameters.serviceName }}
        argoInstance: production
        projectName: default
        namespace: ${{ parameters.serviceName }}
        repoUrl: https://github.com/my-org/${{ parameters.serviceName }}.git
        path: helm
        revision: main

    # Step 4: Backstage 카탈로그 등록
    - id: register
      name: Backstage 카탈로그 등록
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps['publish'].output.repoContentsUrl }}
        catalogInfoPath: "/catalog-info.yaml"

  output:
    links:
      - title: GitHub 저장소
        url: ${{ steps['publish'].output.remoteUrl }}
      - title: Backstage 카탈로그
        icon: catalog
        entityRef: ${{ steps['register'].output.entityRef }}
      - title: ArgoCD Application
        url: https://argocd.example.com/applications/${{ parameters.serviceName }}
```

#### 스캐폴딩되는 Helm Chart (skeleton/helm/values.yaml)

```yaml
# skeleton/helm/values.yaml
replicaCount: ${{ values.replicas }}

image:
  repository: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/${{ values.serviceName }}
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: ${{ values.port }}

resources:
  requests:
    cpu: ${{ values.cpuRequest }}
    memory: ${{ values.memoryRequest }}
  limits:
    cpu: "1000m"
    memory: "512Mi"

autoscaling:
  enabled: true
  minReplicas: ${{ values.replicas }}
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: ""

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "${{ values.port }}"
  prometheus.io/path: "/metrics"

livenessProbe:
  httpGet:
    path: /health/live
    port: ${{ values.port }}
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: ${{ values.port }}
  initialDelaySeconds: 5
  periodSeconds: 5
```

#### 스캐폴딩되는 ArgoCD Application (skeleton/argocd/application.yaml)

ArgoCD 통합에 대한 자세한 내용은 [ArgoCD Applications](../gitops/argocd/02-applications.md)를 참조하세요.

```yaml
# skeleton/argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ${{ values.serviceName }}
  namespace: argocd
  labels:
    app.kubernetes.io/managed-by: backstage
    backstage.io/template: microservice-golden-path
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/my-org/${{ values.serviceName }}.git
    targetRevision: main
    path: helm
    helm:
      valueFiles:
        - values.yaml
        - values-${{ values.environment }}.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: ${{ values.serviceName }}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

#### 스캐폴딩되는 GitHub Actions CI (skeleton/.github/workflows/ci.yaml)

```yaml
# skeleton/.github/workflows/ci.yaml
name: CI Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: ${{ values.serviceName }}

permissions:
  id-token: write
  contents: read

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Tests
        run: |
          make test

      - name: Configure AWS Credentials
        if: github.ref == 'refs/heads/main'
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
          aws-region: ap-northeast-2

      - name: Login to Amazon ECR
        if: github.ref == 'refs/heads/main'
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and Push Docker Image
        if: github.ref == 'refs/heads/main'
        env:
          ECR_REGISTRY: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
          IMAGE_TAG: ${{ "{{" }} github.sha {{ "}}" }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

      - name: Update Helm Values
        if: github.ref == 'refs/heads/main'
        env:
          IMAGE_TAG: ${{ "{{" }} github.sha {{ "}}" }}
        run: |
          sed -i "s|tag:.*|tag: \"$IMAGE_TAG\"|" helm/values.yaml
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add helm/values.yaml
          git commit -m "chore: update image tag to $IMAGE_TAG"
          git push
```

### 인프라 프로비저닝 템플릿

[ACK](./02-ack.md)와 [KRO](./03-kro.md)를 활용하여 AWS 인프라를 프로비저닝하는 템플릿입니다. 개발자는 Backstage UI에서 데이터베이스 타입, 크기, 환경을 선택하기만 하면 인프라가 자동으로 생성됩니다.

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: infra-provisioning
  title: AWS Infrastructure Provisioning
  description: |
    ACK와 KRO를 활용하여 AWS 인프라를 프로비저닝합니다.
    데이터베이스, 메시지 큐, 캐시 등의 리소스를 셀프서비스로 생성할 수 있습니다.
  tags:
    - infrastructure
    - aws
    - self-service
spec:
  owner: group:platform-team
  type: resource

  parameters:
    - title: 리소스 기본 정보
      required:
        - resourceName
        - owner
        - resourceType
      properties:
        resourceName:
          title: 리소스 이름
          type: string
          description: 프로비저닝할 리소스의 이름
          pattern: "^[a-z][a-z0-9-]*$"
          maxLength: 40
        owner:
          title: 소유 팀
          type: string
          ui:field: OwnerPicker
          ui:options:
            catalogFilter:
              kind: Group
        resourceType:
          title: 리소스 타입
          type: string
          description: 생성할 AWS 리소스 타입
          enum:
            - rds-postgresql
            - rds-mysql
            - elasticache-redis
            - sqs-queue
            - s3-bucket
          enumNames:
            - "RDS PostgreSQL"
            - "RDS MySQL"
            - "ElastiCache Redis"
            - "SQS Queue"
            - "S3 Bucket"

    - title: 리소스 사양
      properties:
        environment:
          title: 환경
          type: string
          enum:
            - development
            - staging
            - production
          default: development
        size:
          title: 인스턴스 크기
          type: string
          description: 리소스 인스턴스 크기
          enum:
            - small
            - medium
            - large
          enumNames:
            - "Small (db.t3.medium / cache.t3.medium)"
            - "Medium (db.r6g.large / cache.r6g.large)"
            - "Large (db.r6g.xlarge / cache.r6g.xlarge)"
          default: small
        storageGb:
          title: 스토리지 크기 (GB)
          type: integer
          description: 데이터베이스 스토리지 크기 (RDS만 해당)
          default: 20
          minimum: 20
          maximum: 1000
        multiAz:
          title: Multi-AZ 배포
          type: boolean
          description: 고가용성을 위한 Multi-AZ 활성화
          default: false

  steps:
    # Step 1: 인프라 매니페스트 생성
    - id: fetch-infra-template
      name: 인프라 매니페스트 생성
      action: fetch:template
      input:
        url: ./skeleton/${{ parameters.resourceType }}
        targetPath: infra
        values:
          resourceName: ${{ parameters.resourceName }}
          owner: ${{ parameters.owner }}
          environment: ${{ parameters.environment }}
          size: ${{ parameters.size }}
          storageGb: ${{ parameters.storageGb }}
          multiAz: ${{ parameters.multiAz }}

    # Step 2: GitOps 리포지토리에 매니페스트 커밋
    - id: publish-to-gitops
      name: GitOps 리포지토리에 커밋
      action: publish:github:pull-request
      input:
        repoUrl: github.com?owner=my-org&repo=infrastructure-gitops
        branchName: infra/${{ parameters.resourceName }}
        title: "[Backstage] Provision ${{ parameters.resourceType }}: ${{ parameters.resourceName }}"
        description: |
          ## 인프라 프로비저닝 요청

          - **리소스 타입**: ${{ parameters.resourceType }}
          - **리소스 이름**: ${{ parameters.resourceName }}
          - **환경**: ${{ parameters.environment }}
          - **크기**: ${{ parameters.size }}
          - **요청자**: ${{ parameters.owner }}

          이 PR이 머지되면 ArgoCD를 통해 ACK/KRO가 AWS 리소스를 자동으로 프로비저닝합니다.
        sourcePath: infra
        targetPath: resources/${{ parameters.environment }}/${{ parameters.resourceName }}

    # Step 3: 카탈로그 리소스 등록
    - id: register-resource
      name: 카탈로그 리소스 등록
      action: catalog:register
      input:
        catalogInfoUrl: https://github.com/my-org/infrastructure-gitops/blob/main/resources/${{ parameters.environment }}/${{ parameters.resourceName }}/catalog-info.yaml

  output:
    links:
      - title: 인프라 프로비저닝 PR
        url: ${{ steps['publish-to-gitops'].output.remoteUrl }}
      - title: Backstage 카탈로그
        icon: catalog
        entityRef: ${{ steps['register-resource'].output.entityRef }}
```

#### 인프라 스켈레톤 예시 (RDS PostgreSQL)

KRO Claim을 사용하여 RDS를 프로비저닝합니다:

```yaml
# skeleton/rds-postgresql/kro-claim.yaml
apiVersion: kro.run/v1alpha1
kind: DatabaseInstance
metadata:
  name: ${{ values.resourceName }}
  namespace: infrastructure
  labels:
    backstage.io/managed-by: backstage
    backstage.io/owner: ${{ values.owner }}
    environment: ${{ values.environment }}
spec:
  engine: postgresql
  engineVersion: "15.4"
  instanceClass: >-
    {%- if values.size == "small" %}
    db.t3.medium
    {%- elif values.size == "medium" %}
    db.r6g.large
    {%- else %}
    db.r6g.xlarge
    {%- endif %}
  allocatedStorage: ${{ values.storageGb }}
  multiAZ: ${{ values.multiAz }}
  storageEncrypted: true
  deletionProtection: true
  backupRetentionPeriod: 7
  tags:
    - key: Environment
      value: ${{ values.environment }}
    - key: ManagedBy
      value: backstage
    - key: Owner
      value: ${{ values.owner }}
```

카탈로그 등록을 위한 `catalog-info.yaml`:

```yaml
# skeleton/rds-postgresql/catalog-info.yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: ${{ values.resourceName }}
  title: "${{ values.resourceName }} (PostgreSQL)"
  description: "Backstage에서 프로비저닝한 PostgreSQL 데이터베이스"
  annotations:
    backstage.io/managed-by-location: url:https://github.com/my-org/infrastructure-gitops/blob/main/resources/${{ values.environment }}/${{ values.resourceName }}/catalog-info.yaml
  tags:
    - postgresql
    - rds
    - ${{ values.environment }}
spec:
  type: database
  lifecycle: ${{ values.environment }}
  owner: ${{ values.owner }}
```

### ArgoCD 통합 플러그인 설정

Backstage에서 ArgoCD 배포 상태를 확인하고, Software Templates에서 ArgoCD Application을 생성하려면 ArgoCD 플러그인을 설치합니다.

```bash
# ArgoCD 프론트엔드 플러그인
yarn --cwd packages/app add @roadiehq/backstage-plugin-argo-cd

# ArgoCD 백엔드 플러그인
yarn --cwd packages/backend add @roadiehq/backstage-plugin-argo-cd-backend

# Scaffolder ArgoCD 액션 (템플릿에서 ArgoCD App 생성)
yarn --cwd packages/backend add @roadiehq/scaffolder-backend-argocd
```

ArgoCD 연결 설정:

```yaml
# app-config.yaml - ArgoCD 설정
argocd:
  appLocatorMethods:
    - type: config
      instances:
        - name: production
          url: https://argocd.example.com
          token: ${ARGOCD_AUTH_TOKEN}
```

---

## TechDocs

### 개요

TechDocs는 Backstage의 "docs-as-code" 솔루션으로, MkDocs를 기반으로 합니다. 개발자는 코드 리포지토리에 Markdown 문서를 작성하고, Backstage가 자동으로 빌드하여 통합 UI에서 제공합니다.

### TechDocs 워크플로우

![개발자가 작성한 Markdown이 Git Repository, CI 빌드, S3 업로드를 거쳐 Backstage TechDocs UI에서 렌더링되고 개발자가 그 UI에서 문서를 열람하는 TechDocs 빌드 파이프라인을 보여준다.](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-2.png)

### S3 스토리지 백엔드 구성

TechDocs의 빌드된 문서를 S3에 저장하면 Backstage 인스턴스 간에 문서를 공유할 수 있고 확장성이 향상됩니다.

```yaml
# app-config.yaml - TechDocs 설정
techdocs:
  builder: external
  publisher:
    type: awsS3
    awsS3:
      bucketName: my-company-techdocs
      region: ap-northeast-2
      bucketRootPath: /
      credentials:
        roleArn: arn:aws:iam::123456789012:role/backstage-techdocs-role
      s3ForcePathStyle: false
  generator:
    runIn: local
    mkdocs:
      omitTechDocsCoreMkDocsPlugin: false
  cache:
    ttl: 3600000
```

### S3 버킷 및 IAM 정책

ACK를 사용하여 S3 버킷을 생성하거나 AWS 콘솔/Terraform을 사용할 수 있습니다:

```yaml
# ACK로 S3 버킷 생성
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-company-techdocs
  namespace: backstage
spec:
  name: my-company-techdocs
  versioning:
    status: Enabled
  encryption:
    rules:
      - applyServerSideEncryptionByDefault:
          sseAlgorithm: aws:kms
  publicAccessBlock:
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
  tagging:
    tagSet:
      - key: ManagedBy
        value: backstage
      - key: Purpose
        value: techdocs
```

IAM 정책 (IRSA에 연결):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-company-techdocs",
        "arn:aws:s3:::my-company-techdocs/*"
      ]
    }
  ]
}
```

### MkDocs 설정 파일

각 리포지토리에 `mkdocs.yml`을 추가하여 TechDocs를 활성화합니다:

```yaml
# mkdocs.yml (각 서비스 리포지토리의 루트)
site_name: Order API Documentation
site_description: 주문 API 서비스 기술 문서

plugins:
  - techdocs-core

nav:
  - Home: index.md
  - Architecture: architecture.md
  - API Reference: api-reference.md
  - Runbook: runbook.md
  - ADR:
      - "001 - Database Selection": adr/001-database-selection.md
      - "002 - API Versioning": adr/002-api-versioning.md

markdown_extensions:
  - admonition
  - codehilite
  - pymdownx.details
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
```

### CI에서 TechDocs 빌드 및 S3 업로드

```yaml
# .github/workflows/techdocs.yaml
name: TechDocs Build and Publish

on:
  push:
    branches: [main]
    paths:
      - "docs/**"
      - "mkdocs.yml"

permissions:
  id-token: write
  contents: read

jobs:
  publish-techdocs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install techdocs-cli
        run: |
          pip install mkdocs-techdocs-core
          npm install -g @techdocs/cli

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-techdocs
          aws-region: ap-northeast-2

      - name: Generate and Publish TechDocs
        run: |
          techdocs-cli generate --no-docker
          techdocs-cli publish \
            --publisher-type awsS3 \
            --storage-name my-company-techdocs \
            --entity default/Component/order-api \
            --awsRegion ap-northeast-2
```

---

## EKS 전용 Plugin 생태계

Backstage의 플러그인 생태계는 EKS 운영에 필요한 다양한 기능을 제공합니다.

### Kubernetes 플러그인: Pod/Deployment 상태 시각화

앞서 설치한 `@backstage/plugin-kubernetes`는 카탈로그의 각 서비스에 대해 다음 정보를 제공합니다:

- **Pod 상태**: Running, Pending, Failed, CrashLoopBackOff 등
- **Deployment 상태**: Available Replicas, Desired Replicas
- **ReplicaSet 히스토리**: 최근 배포 이력
- **HPA 상태**: 현재 메트릭 대비 목표값
- **로그 확인**: Pod 로그를 Backstage UI에서 직접 확인

카탈로그 엔티티의 `catalog-info.yaml`에 다음 어노테이션을 추가하면 자동으로 연결됩니다:

```yaml
metadata:
  annotations:
    # 방법 1: 서비스 이름 기반 (kubernetes-id)
    backstage.io/kubernetes-id: order-api

    # 방법 2: 레이블 셀렉터 기반
    backstage.io/kubernetes-label-selector: app=order-api

    # 특정 네임스페이스 지정
    backstage.io/kubernetes-namespace: production

    # 특정 클러스터 지정 (멀티 클러스터 환경)
    backstage.io/kubernetes-cluster: production-eks
```

### ArgoCD 플러그인: 배포 동기화 상태

ArgoCD 플러그인은 카탈로그 엔티티에 배포 상태를 표시합니다:

- **Sync 상태**: Synced, OutOfSync, Unknown
- **Health 상태**: Healthy, Degraded, Progressing, Missing
- **최근 배포 이력**: 커밋 해시, 배포 시간, 배포자
- **리소스 트리**: ArgoCD Application이 관리하는 모든 리소스 시각화

프론트엔드에 ArgoCD 카드를 추가합니다:

```typescript
// packages/app/src/components/catalog/EntityPage.tsx
import {
  EntityArgoCDOverviewCard,
  EntityArgoCDHistoryCard,
} from '@roadiehq/backstage-plugin-argo-cd';

const overviewContent = (
  <Grid container spacing={3}>
    {/* 기존 카드들 */}
    <Grid item md={6}>
      <EntityArgoCDOverviewCard />
    </Grid>
    <Grid item md={6}>
      <EntityArgoCDHistoryCard />
    </Grid>
  </Grid>
);
```

카탈로그 엔티티에 ArgoCD 어노테이션을 추가합니다:

```yaml
metadata:
  annotations:
    argocd/app-name: order-api
    # 여러 앱이 있는 경우 (쉼표 구분)
    # argocd/app-name: order-api,order-api-staging
```

### Kubecost 플러그인: 서비스별 비용 가시성

Kubecost 플러그인은 각 서비스의 Kubernetes 리소스 사용량과 비용을 카탈로그 엔티티 페이지에 표시합니다.

```bash
# Kubecost 프론트엔드 플러그인 설치
yarn --cwd packages/app add @kubecost/backstage-plugin
```

```yaml
# app-config.yaml - Kubecost 설정
kubecost:
  baseUrl: https://kubecost.example.com
  window: "7d"
  aggregate: "namespace"
```

프론트엔드에 비용 카드를 추가합니다:

```typescript
// packages/app/src/components/catalog/EntityPage.tsx
import { EntityKubecostCard } from '@kubecost/backstage-plugin';

const overviewContent = (
  <Grid container spacing={3}>
    {/* 기존 카드들 */}
    <Grid item md={12}>
      <EntityKubecostCard />
    </Grid>
  </Grid>
);
```

### KEDA/Karpenter: 스케일링 가시성 (커스텀 플러그인 컨셉)

KEDA ScaledObject와 Karpenter NodePool 상태를 표시하는 커스텀 플러그인을 구현할 수 있습니다. 기본 Kubernetes 플러그인의 Custom Resources 기능을 활용합니다.

`app-config.yaml`의 Kubernetes 설정에서 커스텀 리소스를 추가합니다:

```yaml
# app-config.yaml - 커스텀 리소스 추가
kubernetes:
  customResources:
    - group: "keda.sh"
      apiVersion: "v1alpha1"
      plural: "scaledobjects"
    - group: "keda.sh"
      apiVersion: "v1alpha1"
      plural: "scaledjobs"
    - group: "karpenter.sh"
      apiVersion: "v1"
      plural: "nodepools"
    - group: "karpenter.k8s.aws"
      apiVersion: "v1"
      plural: "ec2nodeclasses"
```

이렇게 설정하면 Kubernetes 플러그인 UI에서 ScaledObject의 현재 레플리카 수, 최소/최대 레플리카, 활성 트리거 상태를 확인할 수 있습니다.

### 플러그인 설정 요약

| 플러그인 | 패키지 | 용도 | 카탈로그 어노테이션 |
|----------|--------|------|---------------------|
| **Kubernetes** | `@backstage/plugin-kubernetes` | Pod/Deployment 상태 | `backstage.io/kubernetes-id` |
| **ArgoCD** | `@roadiehq/backstage-plugin-argo-cd` | 배포 동기화 상태 | `argocd/app-name` |
| **Kubecost** | `@kubecost/backstage-plugin` | 서비스별 비용 | 네임스페이스 기반 자동 매핑 |
| **GitHub Actions** | `@backstage/plugin-github-actions` | CI/CD 파이프라인 상태 | `github.com/project-slug` |
| **Prometheus** | `@roadiehq/backstage-plugin-prometheus` | 메트릭 대시보드 | `prometheus.io/rule` |
| **PagerDuty** | `@pagerduty/backstage-plugin` | 인시던트 관리 | `pagerduty.com/service-id` |

---

## RBAC과 거버넌스

### Permission Framework 개요

Backstage의 Permission Framework는 플러그인 수준의 세밀한 접근 제어를 제공합니다. 이를 통해 "누가 무엇을 할 수 있는가"를 정책으로 정의할 수 있습니다.

![사용자 요청이 Permission Framework와 Permission Policy를 거쳐 허용, 거부, 조건부 허용 중 하나로 판정되며 platform-team/backend-team/viewer 정책 예시가 참조되는 Backstage 권한 프레임워크 흐름을 보여준다.](../.gitbook/assets/ko-platform-engineering-06-backstage-idp-3.png)

### Permission 플러그인 설치

```bash
# Permission 백엔드 플러그인
yarn --cwd packages/backend add @backstage/plugin-permission-backend
yarn --cwd packages/backend add @backstage/plugin-permission-backend-module-allow-all-policy

# 커스텀 정책 개발 시 필요
yarn --cwd packages/backend add @backstage/plugin-permission-node
```

### 팀 기반 접근 제어 구현

커스텀 Permission Policy를 구현하여 팀 기반 접근 제어를 적용합니다:

```typescript
// plugins/permission-backend-module-custom-policy/src/policy.ts
import {
  PolicyDecision,
  AuthorizeResult,
} from '@backstage/plugin-permission-common';
import {
  PermissionPolicy,
  PolicyQuery,
} from '@backstage/plugin-permission-node';
import { BackstageIdentityResponse } from '@backstage/plugin-auth-node';

export class CustomPermissionPolicy implements PermissionPolicy {
  async handle(
    request: PolicyQuery,
    user?: BackstageIdentityResponse,
  ): Promise<PolicyDecision> {
    // 인증되지 않은 사용자는 거부
    if (!user) {
      return { result: AuthorizeResult.DENY };
    }

    const userGroups = user.identity.ownershipEntityRefs;

    // platform-team은 모든 권한 허용
    if (userGroups.some(ref => ref === 'group:default/platform-team')) {
      return { result: AuthorizeResult.ALLOW };
    }

    // 카탈로그 읽기는 모든 사용자에게 허용
    if (request.permission.name === 'catalog.entity.read') {
      return { result: AuthorizeResult.ALLOW };
    }

    // 카탈로그 삭제는 소유자만 허용 (조건부)
    if (request.permission.name === 'catalog.entity.delete') {
      return {
        result: AuthorizeResult.CONDITIONAL,
        pluginId: 'catalog',
        resourceType: 'catalog-entity',
        conditions: {
          rule: 'IS_ENTITY_OWNER',
          params: { claims: user.identity.ownershipEntityRefs },
        },
      };
    }

    // 템플릿 실행은 모든 인증된 사용자에게 허용
    if (request.permission.name === 'scaffolder.template.execute') {
      return { result: AuthorizeResult.ALLOW };
    }

    // 기본적으로 허용
    return { result: AuthorizeResult.ALLOW };
  }
}
```

### 역할별 권한 매트릭스

| 권한 | Platform Admin | Service Owner | Developer | Viewer |
|------|:--------------:|:-------------:|:---------:|:------:|
| 카탈로그 조회 | O | O | O | O |
| 카탈로그 등록 | O | O | O | X |
| 카탈로그 삭제 | O | 소유 엔티티만 | X | X |
| 템플릿 실행 | O | O | O | X |
| 템플릿 생성/수정 | O | X | X | X |
| TechDocs 조회 | O | O | O | O |
| 플러그인 설정 변경 | O | X | X | X |
| 사용자/그룹 관리 | O | X | X | X |

### 감사 로깅 설정

Backstage의 이벤트 시스템을 활용하여 주요 작업에 대한 감사 로그를 기록합니다:

```yaml
# app-config.yaml - 감사 로깅
backend:
  events:
    modules:
      - name: audit-log
        config:
          topics:
            - catalog
            - scaffolder
            - permission
          backend:
            type: awsCloudWatch
            config:
              logGroupName: /backstage/audit
              region: ap-northeast-2
```

```typescript
// packages/backend/src/index.ts 에 이벤트 모듈 추가
backend.add(import('@backstage/plugin-events-backend'));
backend.add(import('@backstage/plugin-events-backend-module-aws-sqs'));
```

주요 감사 이벤트:

| 이벤트 카테고리 | 감사 대상 | 설명 |
|-----------------|----------|------|
| **카탈로그** | 엔티티 등록/삭제/수정 | 누가 어떤 엔티티를 변경했는지 추적 |
| **Scaffolder** | 템플릿 실행 | 누가, 어떤 템플릿을, 어떤 파라미터로 실행했는지 기록 |
| **인증** | 로그인/로그아웃 | 사용자 세션 추적 |
| **권한** | 권한 거부 이벤트 | 접근 거부된 요청 기록 및 분석 |

---

## 프로덕션 운영

### 고가용성 (HA) 구성

프로덕션 환경에서 Backstage를 안정적으로 운영하려면 다음 사항을 고려해야 합니다:

```yaml
# values-production.yaml - HA 구성
backstage:
  replicas: 3

  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "2000m"

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

  readinessProbe:
    httpGet:
      path: /healthcheck
      port: 7007
    initialDelaySeconds: 30
    periodSeconds: 10
    timeoutSeconds: 5

  livenessProbe:
    httpGet:
      path: /healthcheck
      port: 7007
    initialDelaySeconds: 60
    periodSeconds: 30
    timeoutSeconds: 10
```

외부 PostgreSQL (RDS) HA 구성:

| 항목 | 설정 |
|------|------|
| **엔진** | Aurora PostgreSQL 15.x |
| **인스턴스 클래스** | db.r6g.large (프로덕션) |
| **Multi-AZ** | 활성화 (최소 2개 AZ) |
| **Read Replica** | 1개 이상 (읽기 부하 분산) |
| **자동 백업** | 7일 보존 |
| **암호화** | KMS 키로 저장 시 암호화 |
| **Connection Pooling** | PgBouncer 또는 RDS Proxy 사용 |

### 백업 및 복구 전략

Backstage의 핵심 데이터는 PostgreSQL에 저장되므로, 데이터베이스 백업이 가장 중요합니다:

```bash
# RDS 자동 스냅샷 확인
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier backstage-db-cluster \
  --query 'DBClusterSnapshots[*].{ID:DBClusterSnapshotIdentifier,Created:SnapshotCreateTime,Status:Status}' \
  --output table

# 수동 스냅샷 생성 (업그레이드 전)
aws rds create-db-cluster-snapshot \
  --db-cluster-identifier backstage-db-cluster \
  --db-cluster-snapshot-identifier backstage-pre-upgrade-$(date +%Y%m%d)

# 스냅샷에서 복구
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier backstage-db-cluster-restored \
  --snapshot-identifier backstage-pre-upgrade-20260622 \
  --engine aurora-postgresql \
  --engine-version 15.4
```

추가 백업 대상:

| 대상 | 백업 방법 | 주기 | 보존 기간 |
|------|----------|------|----------|
| **PostgreSQL (RDS)** | 자동 스냅샷 + 수동 스냅샷 | 일일 (자동), 업그레이드 전 (수동) | 7일 (자동), 90일 (수동) |
| **S3 (TechDocs)** | S3 버전 관리 + Cross-Region Replication | 실시간 | 30일 |
| **app-config.yaml** | Git 리포지토리 | 모든 변경 시 | 영구 |
| **Secrets** | AWS Secrets Manager 또는 SSM Parameter Store | 변경 시 | 영구 |

### 업그레이드 전략

Backstage는 활발하게 개발되고 있어 정기적인 업그레이드가 필요합니다.

**버전 고정 및 업그레이드 절차:**

```bash
# 1. 현재 버전 확인
yarn backstage-cli info

# 2. 업그레이드 가능 버전 확인
yarn backstage-cli versions:check

# 3. 데이터베이스 백업 (위의 백업 절차 참조)

# 4. Staging 환경에서 먼저 업그레이드
yarn backstage-cli versions:bump --release 1.36.0

# 5. 의존성 업데이트
yarn install

# 6. 빌드 테스트
yarn tsc && yarn build:backend

# 7. 변경 사항 커밋 및 Staging 배포

# 8. Staging 검증 후 Production 배포
```

**Rolling Update 전략:**

```yaml
# Deployment 업데이트 전략
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

> **참고**: 데이터베이스 마이그레이션이 포함된 업그레이드의 경우, 마이그레이션이 하위 호환성을 유지하는지 반드시 확인하세요. Backstage는 일반적으로 하위 호환 마이그레이션을 제공하지만, 릴리스 노트를 항상 확인해야 합니다.

---

## 모범 사례

### Backstage 도입 및 운영 모범 사례

1. **점진적 도입**: 모든 기능을 한 번에 도입하지 말고, Software Catalog부터 시작하여 점진적으로 Templates, TechDocs, 플러그인을 추가하세요. 개발자 피드백을 반영하면서 단계적으로 확장하는 것이 성공의 핵심입니다.

2. **카탈로그 데이터 품질 관리**: `catalog-info.yaml`의 정확성이 Backstage의 가치를 결정합니다. CI 파이프라인에서 카탈로그 파일의 유효성 검사를 수행하고, 소유권 정보가 누락된 서비스를 정기적으로 검토하세요.

3. **Golden Path는 강제가 아닌 권장**: Software Templates로 제공하는 Golden Path는 개발자를 돕기 위한 것입니다. 특수한 요구사항이 있는 경우 벗어날 수 있도록 유연성을 유지하되, 대부분의 경우에 Golden Path가 최적의 선택이 되도록 설계하세요.

4. **플러그인 선택에 신중**: 모든 가용한 플러그인을 설치하는 것이 아니라, 조직에 실질적인 가치를 제공하는 플러그인만 선별하여 도입하세요. 각 플러그인은 유지보수 부담을 수반합니다.

5. **TechDocs를 코드 리뷰에 포함**: 코드 변경 시 관련 문서도 함께 업데이트하도록 문화를 만드세요. PR 템플릿에 "관련 문서가 업데이트되었는가?" 체크리스트를 추가하는 것이 효과적입니다.

6. **메트릭 기반 개선**: Backstage 사용량, 검색 쿼리, 템플릿 실행 횟수 등의 메트릭을 수집하여 플랫폼의 효과를 측정하고 개선 방향을 설정하세요.

7. **전담 플랫폼 팀 운영**: Backstage를 단순한 도구가 아닌 내부 제품으로 다루세요. 전담 플랫폼 팀이 개발자 피드백을 수렴하고, 새로운 플러그인과 템플릿을 지속적으로 개발하여 개발자 경험을 향상시켜야 합니다.

8. **보안 업데이트 자동화**: Backstage와 플러그인의 보안 업데이트를 정기적으로 적용하세요. Dependabot이나 Renovate를 사용하여 의존성 업데이트를 자동화하는 것을 권장합니다.

### 일반적인 실수와 해결 방법

#### 1. 카탈로그에 너무 많은 정보를 한 번에 등록

**문제**: 초기 도입 시 모든 서비스의 `catalog-info.yaml`을 한꺼번에 생성하면 데이터 품질이 낮아지고, 개발자들이 카탈로그를 신뢰하지 않게 됩니다.

**해결**: 핵심 서비스부터 시작하여 점진적으로 확장하세요. 각 팀이 자신의 서비스를 직접 등록하도록 가이드를 제공하고, 정기적으로 데이터 품질을 검토합니다.

#### 2. 템플릿의 과도한 복잡성

**문제**: 하나의 템플릿에 너무 많은 선택지와 조건을 넣으면 유지보수가 어렵고 사용자 경험이 저하됩니다.

**해결**: "한 가지 일을 잘 하는" 작은 템플릿을 여러 개 만드세요. 공통 로직은 커스텀 액션으로 추출하여 재사용합니다.

#### 3. 인증/인가 설정 누락

**문제**: 기본 설정으로 배포하면 모든 사용자가 모든 작업을 수행할 수 있어 보안 위험이 발생합니다.

**해결**: 프로덕션 배포 전 반드시 OIDC 인증과 Permission Framework를 설정하세요. 최소 권한 원칙을 적용하고, 감사 로깅을 활성화합니다.

#### 4. 업그레이드 지연

**문제**: Backstage 업그레이드를 장기간 미루면 보안 취약점에 노출되고, 한 번에 많은 버전을 건너뛰는 업그레이드가 어려워집니다.

**해결**: 월 1회 정기 업그레이드 주기를 설정하고, Staging 환경에서 먼저 검증합니다. Breaking change가 있는 경우 릴리스 노트의 마이그레이션 가이드를 반드시 따르세요.

---

## 참고 자료

### 공식 문서

- [Backstage 공식 문서](https://backstage.io/docs/overview/what-is-backstage)
- [Backstage GitHub 리포지토리](https://github.com/backstage/backstage)
- [Backstage Plugin Marketplace](https://backstage.io/plugins)
- [CNCF Backstage 프로젝트 페이지](https://www.cncf.io/projects/backstage/)
- [Backstage Community](https://backstage.io/community)

### AWS 관련

- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Amazon Cognito Developer Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/)

### 관련 내부 문서

- [Platform Engineering 개요](./00-platform-engineering-overview.md) -- IDP 개념과 플랫폼 엔지니어링 전반
- [AWS Controllers for Kubernetes (ACK)](./02-ack.md) -- Backstage 인프라 프로비저닝 템플릿에서 활용
- [Kubernetes Resource Operator (KRO)](./03-kro.md) -- ACK와 결합한 셀프서비스 인프라 패턴
- [ArgoCD Applications](../gitops/argocd/02-applications.md) -- GitOps 기반 배포와 Backstage 통합
- [ExampleCorp 통합 예제](./05-example-corp-app.md) -- ACK + KRO 실전 배포 예제
