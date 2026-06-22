# Backstage IDP 퀴즈

1. Backstage의 Software Catalog에서 마이크로서비스를 등록하는 데 사용되는 Entity Kind는?
   - A) Service
   - B) Component
   - C) Application
   - D) Workload

<details>
<summary>정답 보기</summary>

**정답: B) Component**

**설명:**
Backstage Software Catalog에서 마이크로서비스, 웹사이트, 라이브러리 등은 모두 `Component` Kind로 등록됩니다. Component의 `spec.type` 필드에서 service, website, library 등으로 유형을 구분합니다.

</details>

---

2. Backstage Software Templates(Golden Paths)의 주요 목적은?
   - A) 기존 서비스의 성능을 모니터링
   - B) 새 서비스/인프라를 표준화된 방식으로 자동 생성
   - C) Kubernetes 클러스터의 보안을 감사
   - D) CI/CD 파이프라인을 모니터링

<details>
<summary>정답 보기</summary>

**정답: B) 새 서비스/인프라를 표준화된 방식으로 자동 생성**

**설명:**
Software Templates(Golden Paths)는 개발자가 Backstage UI에서 몇 가지 파라미터를 입력하면, 표준화된 프로젝트 구조(Dockerfile, Helm chart, CI/CD, catalog-info.yaml 등)를 자동으로 스캐폴딩합니다. 이를 통해 조직의 모범 사례를 강제하지 않고 자연스럽게 적용합니다.

</details>

---

3. Backstage에서 Kubernetes 클러스터의 Pod 상태를 표시하려면 catalog-info.yaml에 어떤 어노테이션이 필요한가요?
   - A) kubernetes.io/pod-name
   - B) backstage.io/kubernetes-id
   - C) app.kubernetes.io/managed-by
   - D) backstage.io/k8s-cluster

<details>
<summary>정답 보기</summary>

**정답: B) backstage.io/kubernetes-id**

**설명:**
`backstage.io/kubernetes-id` 어노테이션은 Backstage Kubernetes 플러그인이 카탈로그 엔터티와 Kubernetes 리소스를 매칭하는 데 사용합니다. 이 값은 Kubernetes Deployment의 레이블 `backstage.io/kubernetes-id`와 일치해야 합니다.

</details>

---

4. Backstage를 EKS 프로덕션 환경에 배포할 때 PostgreSQL 구성으로 가장 적절한 것은?
   - A) 내장 SQLite 사용
   - B) In-cluster PostgreSQL StatefulSet
   - C) Amazon RDS PostgreSQL (외부 관리형)
   - D) DynamoDB

<details>
<summary>정답 보기</summary>

**정답: C) Amazon RDS PostgreSQL (외부 관리형)**

**설명:**
프로덕션 환경에서는 Amazon RDS 같은 관리형 데이터베이스를 사용하여 자동 백업, 고가용성(Multi-AZ), 모니터링을 확보해야 합니다. Helm values에서 `postgresql.enabled: false`로 설정하고 외부 RDS 연결 정보를 Secret으로 제공합니다.

</details>

---

5. Backstage의 TechDocs 기능이 사용하는 문서 빌드 도구는?
   - A) Docusaurus
   - B) GitBook
   - C) MkDocs
   - D) Sphinx

<details>
<summary>정답 보기</summary>

**정답: C) MkDocs**

**설명:**
Backstage TechDocs는 MkDocs를 기반으로 합니다. 각 서비스 레포의 `docs/` 디렉토리와 `mkdocs.yml` 파일을 기반으로 문서를 빌드하고, S3 같은 스토리지에 퍼블리시하여 카탈로그에서 직접 조회할 수 있습니다.

</details>

---

6. Backstage에서 점진적으로 도입할 때 가장 먼저 시작해야 하는 기능은?
   - A) Software Templates
   - B) Software Catalog
   - C) TechDocs
   - D) RBAC Permission Framework

<details>
<summary>정답 보기</summary>

**정답: B) Software Catalog**

**설명:**
Software Catalog는 Backstage의 핵심이자 다른 모든 기능의 기반입니다. 먼저 조직의 서비스, API, 팀 정보를 카탈로그에 등록한 후, 그 위에 Templates와 TechDocs를 단계적으로 추가하는 것이 권장됩니다.

</details>

---

7. Backstage Software Template에서 GitHub 레포 생성과 ArgoCD Application 생성을 자동화할 수 있는 이유는?
   - A) Backstage가 직접 Kubernetes API를 호출하므로
   - B) Template의 steps에서 publish:github와 argocd:create-resources 액션을 순차 실행하므로
   - C) GitHub Webhook이 ArgoCD를 자동 트리거하므로
   - D) Helm chart가 모든 리소스를 포함하고 있으므로

<details>
<summary>정답 보기</summary>

**정답: B) Template의 steps에서 publish:github와 argocd:create-resources 액션을 순차 실행하므로**

**설명:**
Backstage Scaffolder는 Template의 `steps` 섹션에 정의된 액션들을 순차적으로 실행합니다. `publish:github`으로 레포를 생성하고, 그 결과(remoteUrl)를 `argocd:create-resources`의 입력으로 전달하여 ArgoCD Application을 자동 생성합니다. 마지막으로 `catalog:register`로 카탈로그에 등록합니다.

</details>

---

8. Backstage Permission Framework에서 팀이 자기 팀의 엔터티만 수정할 수 있도록 제한하려면 어떤 설정이 필요한가요?
   - A) Kubernetes RBAC ClusterRole
   - B) policy에 conditions 필드로 spec.owner 매칭
   - C) GitHub 레포 권한 설정
   - D) Ingress 네트워크 정책

<details>
<summary>정답 보기</summary>

**정답: B) policy에 conditions 필드로 spec.owner 매칭**

**설명:**
Backstage Permission Framework의 정책에서 `conditions` 필드를 사용하여 `spec.owner`가 해당 팀 이름과 일치하는 엔터티에 대해서만 수정 권한을 부여할 수 있습니다. 이를 통해 팀별 자율성을 유지하면서도 다른 팀의 엔터티는 읽기만 가능하게 제한합니다.

</details>
