# EKS 보안 모범 사례 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

다음 질문들을 통해 Amazon EKS 보안 모범 사례에 대한 이해도를 점검해보세요.

***

## 문제

<span id="_1-irsa-iam-roles-for-service-accounts-에서-pod가-aws-api를-호출할-때-사용하는-인증-방식은"></span>

### 1. Pod가 IRSA로 임시 AWS 자격 증명을 얻는 방식은?

* A) IAM User Access Key
* B) EC2 Instance Profile
* C) OIDC 토큰 기반 AssumeRoleWithWebIdentity
* D) Kubernetes Secret에 저장된 자격 증명

<details>

<summary>정답 보기</summary>

**정답: C) OIDC 토큰 기반 AssumeRoleWithWebIdentity**

**설명:** Kubernetes API 서버가 projected ServiceAccount JWT를 발급하고 지원 SDK가 STS AssumeRoleWithWebIdentity로 교환합니다. STS는 신뢰한 issuer/JWKS·audience·subject를 확인해 임시 AWS 자격 증명을 반환합니다. IAM OIDC provider 오브젝트가 토큰 발급자는 아니며 JWT를 AWS API 자격 증명 대신 직접 사용하는 것도 아닙니다.

</details>

***

### 2. EKS Pod Identity가 IRSA와 비교하여 가지는 주요 장점은?

* A) 더 강력한 암호화
* B) 더 빠른 성능
* C) OIDC Provider 설정 불필요, 간소화된 관리
* D) 더 많은 AWS 서비스 지원

<details>

<summary>정답 보기</summary>

**정답: C) OIDC Provider 설정 불필요, 간소화된 관리**

**설명:** Pod Identity는 클러스터별 IAM OIDC provider 구성 대신 association·지원 agent/SDK·EKS Auth를 이용합니다. 역할 신뢰·최소 권한은 여전히 필요합니다. Auto Mode에는 agent가 내장되며 다른 플랫폼·교차 계정·역할 연결에는 별도 요건이 있습니다. IRSA를 폐기하거나 모든 앱의 보안을 자동 향상시키지 않습니다.

</details>

***

<span id="_3-security-groups-for-pods-기능을-사용하기-위한-필수-요구사항이-아닌-것은"></span>

### 3. EC2 기반 Security Groups for Pods 경로에 필수적이지 않은 것은?

* A) trunking을 지원하는 EC2 인스턴스 타입
* B) Amazon VPC CNI 플러그인
* C) Fargate 프로파일
* D) SecurityGroupPolicy 구성

<details>

<summary>정답 보기</summary>

**정답: C) Fargate 프로파일**

**설명:** EC2 경로에는 trunking을 지원하는 인스턴스, 호환 Amazon VPC CNI, SecurityGroupPolicy가 필요하며 모든 Nitro가 해당하지 않습니다. VPC Resource Controller 정책은 클러스터 역할에 연결합니다. Fargate는 별도 방식이며 현재 Pod SG 문서는 Windows·Auto Mode를 제외합니다. ENIConfig는 SecurityGroupPolicy의 대체물이 아닙니다.

</details>

***

### 4. EKS 클러스터의 Kubernetes API 서버 엔드포인트를 프라이빗으로만 설정할 때의 영향은?

* A) kubectl을 전혀 사용할 수 없음
* B) VPC 내부 또는 연결된 네트워크에서만 접근 가능
* C) AWS Console에서 클러스터 관리 불가
* D) 워커 노드가 API 서버에 연결 불가

<details>

<summary>정답 보기</summary>

**정답: B) VPC 내부 또는 연결된 네트워크에서만 접근 가능**

**설명:** 프라이빗 API 연결에는 연결된 네트워크·DNS·라우팅·보안 그룹과 IAM 인증/Kubernetes 권한이 모두 필요합니다. 공개 접근을 제거하기 전에 운영자·CI·복구 경로를 시험합니다. EKS 관리 API PrivateLink는 private Kubernetes API endpoint의 대체물이 아닙니다.

</details>

***

### 5. AWS GuardDuty EKS Protection이 탐지하는 위협 유형이 아닌 것은?

* A) 악성 IP와의 통신
* B) 암호화폐 채굴 활동
* C) Pod의 리소스 사용량 초과
* D) Tor 네트워크 연결

<details>

<summary>정답 보기</summary>

**정답: C) Pod의 리소스 사용량 초과**

**설명:** EKS 감사 분석·agent 기반 Runtime Monitoring·기본 GuardDuty 데이터 소스를 구분합니다. 활성화한 플랜과 플랫폼에 따라 범위가 다르며 ECS Fargate 지원은 EKS Fargate 지원이 아닙니다. CPU/메모리 한도 감시는 운영 메트릭 도구의 역할이고 탐지 결과가 없다고 침해가 없음을 입증하지 않습니다.

</details>

***

<span id="_6-eks-클러스터에서-vpc-엔드포인트를-사용해야-하는-aws-서비스가-아닌-것은"></span>

### 6. DNS와 프라이빗 AWS API 접근을 올바르게 구분한 것은?

* A) EKS 관리 endpoint가 Kubernetes API를 대체한다
* B) Pod Identity는 항상 global STS endpoint를 사용한다
* C) 모든 AWS Region의 endpoint 이름·지원 범위는 동일하다
* D) DNS 조회와 Route 53 관리 API PrivateLink를 구분한다

<details>

<summary>정답 보기</summary>

**정답: D) DNS 조회와 Route 53 관리 API PrivateLink를 구분한다**

**설명:** 일반 DNS 조회는 설정한 resolver·네트워크 경로를 사용합니다. Route 53 관리 API 호출은 별개이며 현재 EKS private-cluster 문서는 Route 53 PrivateLink 서비스를 나열합니다. EKS Auth·regional STS·OIDC discovery·ECR/S3도 경로가 다르므로 서비스·Region별 요구를 확인합니다.

</details>

***

### 7. kube-bench를 사용하여 EKS 클러스터의 보안을 점검할 때 사용하는 벤치마크는?

* A) PCI-DSS
* B) 환경에 맞는 CIS Amazon EKS benchmark profile
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>정답 보기</summary>

**정답: B) 환경에 맞는 CIS Amazon EKS benchmark profile**

**설명:** 환경에 맞는 CIS Amazon EKS 판과 kube-bench 프로필을 선택합니다. kube-bench0.16.0에는 여러 EKS 프로필이 있으며 변경 가능한 upstream Job 하나가 전체 노드 검사를 입증하지 않습니다. 수동·해당 없음 항목과 관리형 컨트롤 플레인 한계가 남고 퀴즈·도구 점수는 인증서가 아닙니다.

</details>

***

### 8. EKS에서 Service Account Token Volume Projection이 제공하는 보안 이점은?

* A) 토큰 크기 감소
* B) 바운드 토큰과 만료 시간 설정
* C) 토큰 암호화
* D) 토큰 자동 백업

<details>

<summary>정답 보기</summary>

**정답: B) 바운드 토큰과 만료 시간 설정**

**설명:** projection은 audience·요청 수명·오브젝트 바인딩을 지원합니다. 실제 만료와 수신자 검증을 확인하며 모든 토큰이 정확히 1시간 뒤 만료된다고 가정하지 않습니다. 탈취한 bearer token은 유효하게 받아들여지는 동안 재사용될 수 있어 보호가 여전히 필요합니다. projection만으로 IRSA 구성이 완성되지 않습니다.

</details>

***

### 9. Amazon Inspector가 EKS 환경에서 스캔하는 대상은?

* A) Kubernetes 매니페스트
* B) 컨테이너 이미지의 취약점
* C) IAM 정책
* D) 네트워크 트래픽

<details>

<summary>정답 보기</summary>

**정답: B) 컨테이너 이미지의 취약점**

**설명:** ECR enhanced scanning은 Inspector로 지원 이미지의 패키지 취약점을 검사합니다. 실행 이미지 사용 정보와 런타임 동작 탐지는 다릅니다. 정확한 digest의 성공 상태·완료 시각·명시적 Finding count를 확인한 뒤 통과시키며 대기·누락·오류를 취약점 0건으로 처리하지 않습니다.

</details>

***

### 10. EKS 클러스터의 Control Plane 로그를 CloudWatch로 전송할 때 활성화할 수 있는 로그 유형이 아닌 것은?

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>정답 보기</summary>

**정답: D) kubelet**

**설명:** EKS 컨트롤 플레인 유형은 api·audit·authenticator·controllerManager·scheduler입니다. kubelet·컨테이너 로그는 별도 노드/런타임 수집이 필요합니다. 클러스터 소유자를 통해 export를 구성하고 비동기 변경·실제 유입·보존·접근을 확인합니다.

</details>

***

### 11. EKS에서 노드 IAM Role과 Pod IAM Role(IRSA)을 분리해야 하는 이유는?

* A) 비용 절감
* B) 최소 권한 원칙 적용
* C) 성능 향상
* D) 네트워크 지연 감소

<details>

<summary>정답 보기</summary>

**정답: B) 최소 권한 원칙 적용**

**설명:** 워크로드 역할은 노드 책임과 별개로 앱 권한을 제한합니다. 노드 역할 노출은 metadata 접근·권한에 따라 달라 모든 Pod가 항상 읽는 것은 아닙니다. IRSA만으로 IMDS가 차단되지 않으므로 IMDSv2·네트워크·hostNetwork/특권·SDK 자격 증명 우선순위·노드 침해를 고려합니다.

</details>

***

<span id="_12-eks에서-kubernetes-rbac과-aws-iam의-통합을-담당하는-컴포넌트는"></span>

### 12. EKS 개발자에게 필요한 네임스페이스 범위만 허용하는 방법은?

* A) 모든 개발자를 system:masters에 추가
* B) 모든 개발자와 노드 역할 공유
* C) access entry에 범위 제한 access policy 또는 그룹/RBAC 연결
* D) API 인증 비활성화

<details>

<summary>정답 보기</summary>

**정답: C) access entry에 범위 제한 access policy 또는 그룹/RBAC 연결**

**설명:** 필요한 범위의 EKS access policy 또는 Kubernetes 그룹/RBAC를 연결한 access entry를 사용합니다. 인증과 인가는 별도입니다. aws-auth는 기존 방식이며 인증 mode 이전에는 단방향 제약이 있습니다. 일반 개발자에게 system:masters를 부여하지 않고 EKS 정책 또는 RBAC 각각의 허용을 확인합니다.

</details>

***

## 점수 계산

각 문제당 1점으로 계산합니다.

| 점수    | 평가                         |
| ----- | -------------------------- |
| 11-12 | 내용 복습 완료; 운영 시나리오 검증 필요         |
| 8-10  | 양호 - 기본 개념 이해, 고급 기능 복습 필요 |
| 5-7   | 보통 - 추가 학습 권장              |
| 0-4   | 기초 학습 필요                   |

***

## 관련 문서

* [EKS 보안 모범 사례](../../security/06-eks-security-best-practices.md)
* [Pod Security Standards](../../security/03-pod-security-standards.md)
* [Secrets Management](../../security/05-secrets-management.md)
