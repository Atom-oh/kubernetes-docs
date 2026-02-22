# EKS 보안 모범 사례 퀴즈

다음 질문들을 통해 Amazon EKS 보안 모범 사례에 대한 이해도를 점검해보세요.

---

## 문제

### 1. IRSA(IAM Roles for Service Accounts)에서 Pod가 AWS API를 호출할 때 사용하는 인증 방식은?

- A) IAM User Access Key
- B) EC2 Instance Profile
- C) OIDC 토큰 기반 AssumeRoleWithWebIdentity
- D) Kubernetes Secret에 저장된 자격 증명

<details>
<summary>정답 보기</summary>

**정답: C) OIDC 토큰 기반 AssumeRoleWithWebIdentity**

**설명:**
IRSA의 동작 방식:
1. EKS 클러스터의 OIDC Provider가 ServiceAccount 토큰 발급
2. Pod가 AWS STS의 `AssumeRoleWithWebIdentity` API 호출
3. OIDC 토큰을 검증하고 임시 자격 증명 발급
4. Pod가 임시 자격 증명으로 AWS API 호출

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/S3ReaderRole
```

IRSA는 노드 수준이 아닌 Pod 수준의 세밀한 권한 관리를 가능하게 합니다.

</details>

---

### 2. EKS Pod Identity가 IRSA와 비교하여 가지는 주요 장점은?

- A) 더 강력한 암호화
- B) 더 빠른 성능
- C) OIDC Provider 설정 불필요, 간소화된 관리
- D) 더 많은 AWS 서비스 지원

<details>
<summary>정답 보기</summary>

**정답: C) OIDC Provider 설정 불필요, 간소화된 관리**

**설명:**
EKS Pod Identity의 장점:
- OIDC Provider 설정 불필요
- IAM Role의 Trust Policy 간소화
- Pod Identity Agent를 통한 자동 자격 증명 관리
- 크로스 어카운트 접근 간소화

```bash
# Pod Identity 연결 (CLI로 간단히 설정)
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account myapp-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

IRSA는 각 클러스터마다 OIDC Provider 설정과 복잡한 Trust Policy가 필요합니다.

</details>

---

### 3. Security Groups for Pods 기능을 사용하기 위한 필수 요구사항이 아닌 것은?

- A) Nitro 기반 인스턴스 타입
- B) Amazon VPC CNI 플러그인
- C) Fargate 프로파일
- D) ENIConfig 또는 SecurityGroupPolicy CRD

<details>
<summary>정답 보기</summary>

**정답: C) Fargate 프로파일**

**설명:**
Security Groups for Pods 요구사항:
- **필수**: Nitro 기반 EC2 인스턴스 (m5, c5, r5 등)
- **필수**: Amazon VPC CNI 플러그인 v1.7.7+
- **필수**: SecurityGroupPolicy CRD 설정
- **선택**: Fargate (별도의 설정 방식)

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-access-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Fargate는 자체적으로 각 Pod에 ENI를 할당하므로 별도 설정이 필요합니다.

</details>

---

### 4. EKS 클러스터의 Kubernetes API 서버 엔드포인트를 프라이빗으로만 설정할 때의 영향은?

- A) kubectl을 전혀 사용할 수 없음
- B) VPC 내부 또는 연결된 네트워크에서만 접근 가능
- C) AWS Console에서 클러스터 관리 불가
- D) 워커 노드가 API 서버에 연결 불가

<details>
<summary>정답 보기</summary>

**정답: B) VPC 내부 또는 연결된 네트워크에서만 접근 가능**

**설명:**
프라이빗 엔드포인트 설정 시:
- VPC 내부에서 접근 가능
- VPN, Direct Connect, VPC Peering 등으로 연결된 네트워크에서 접근 가능
- 퍼블릭 인터넷에서 접근 불가

```bash
# 엔드포인트 설정
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config \
    endpointPublicAccess=false,endpointPrivateAccess=true
```

보안을 위해 프라이빗 엔드포인트만 사용하는 것이 권장됩니다.

</details>

---

### 5. AWS GuardDuty EKS Protection이 탐지하는 위협 유형이 아닌 것은?

- A) 악성 IP와의 통신
- B) 암호화폐 채굴 활동
- C) Pod의 리소스 사용량 초과
- D) Tor 네트워크 연결

<details>
<summary>정답 보기</summary>

**정답: C) Pod의 리소스 사용량 초과**

**설명:**
GuardDuty EKS Protection이 탐지하는 위협:
- 악성 IP 주소와의 통신
- 암호화폐 채굴 (Kubernetes API 남용)
- Tor 네트워크 연결
- DNS Rebinding 공격
- 권한 상승 시도
- 비정상적인 API 호출 패턴

리소스 사용량 모니터링은 다음 도구로 수행:
- Kubernetes Metrics Server
- Prometheus/Grafana
- CloudWatch Container Insights

</details>

---

### 6. EKS 클러스터에서 VPC 엔드포인트를 사용해야 하는 AWS 서비스가 아닌 것은?

- A) ECR (dkr, api)
- B) S3
- C) STS
- D) Route 53

<details>
<summary>정답 보기</summary>

**정답: D) Route 53**

**설명:**
EKS에서 권장되는 VPC 엔드포인트:
- **ECR (dkr, api)**: 컨테이너 이미지 풀
- **S3**: 이미지 레이어 저장소
- **STS**: IRSA/Pod Identity 인증
- **CloudWatch Logs**: 로그 전송
- **EC2, ELB, Auto Scaling**: 노드 관리

Route 53은 글로벌 DNS 서비스로 VPC 엔드포인트가 아닌 일반적인 DNS 해석을 사용합니다.

```bash
# 필수 VPC 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.region.ecr.dkr \
  --vpc-endpoint-type Interface
```

</details>

---

### 7. kube-bench를 사용하여 EKS 클러스터의 보안을 점검할 때 사용하는 벤치마크는?

- A) PCI-DSS
- B) CIS Kubernetes Benchmark
- C) NIST Cybersecurity Framework
- D) SOC 2

<details>
<summary>정답 보기</summary>

**정답: B) CIS Kubernetes Benchmark**

**설명:**
kube-bench는 CIS (Center for Internet Security) Kubernetes Benchmark를 기준으로 클러스터 보안을 점검합니다:

```bash
# EKS 노드에서 kube-bench 실행
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job-eks.yaml

# 결과 확인
kubectl logs job/kube-bench
```

점검 항목:
- Control Plane 구성 (EKS 관리형이므로 일부 N/A)
- Worker Node 구성
- 정책 및 Pod 보안
- 네트워크 정책
- 로깅 및 감사

</details>

---

### 8. EKS에서 Service Account Token Volume Projection이 제공하는 보안 이점은?

- A) 토큰 크기 감소
- B) 바운드 토큰과 만료 시간 설정
- C) 토큰 암호화
- D) 토큰 자동 백업

<details>
<summary>정답 보기</summary>

**정답: B) 바운드 토큰과 만료 시간 설정**

**설명:**
Service Account Token Volume Projection의 보안 이점:
- **바운드 토큰**: 특정 Pod에만 유효
- **만료 시간**: 토큰 자동 만료 (기본 1시간)
- **대상 지정**: 특정 Audience에만 유효

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - name: token
          mountPath: /var/run/secrets/tokens
  volumes:
    - name: token
      projected:
        sources:
          - serviceAccountToken:
              path: token
              expirationSeconds: 3600
              audience: sts.amazonaws.com
```

기존 토큰은 만료되지 않아 유출 시 위험했습니다.

</details>

---

### 9. Amazon Inspector가 EKS 환경에서 스캔하는 대상은?

- A) Kubernetes 매니페스트
- B) 컨테이너 이미지의 취약점
- C) IAM 정책
- D) 네트워크 트래픽

<details>
<summary>정답 보기</summary>

**정답: B) 컨테이너 이미지의 취약점**

**설명:**
Amazon Inspector의 EKS 통합:
- ECR에 저장된 컨테이너 이미지 스캔
- 실행 중인 워크로드의 이미지 스캔
- OS 패키지 취약점 탐지
- 애플리케이션 패키지 취약점 탐지 (npm, pip 등)

```bash
# Inspector 활성화
aws inspector2 enable \
  --resource-types ECR

# 스캔 결과 확인
aws inspector2 list-findings \
  --filter-criteria resourceType=AWS_ECR_CONTAINER_IMAGE
```

지속적인 스캔으로 새로운 CVE 발견 시 알림을 받을 수 있습니다.

</details>

---

### 10. EKS 클러스터의 Control Plane 로그를 CloudWatch로 전송할 때 활성화할 수 있는 로그 유형이 아닌 것은?

- A) api
- B) audit
- C) controllerManager
- D) kubelet

<details>
<summary>정답 보기</summary>

**정답: D) kubelet**

**설명:**
EKS Control Plane 로그 유형:
- **api**: API 서버 로그
- **audit**: 감사 로그 (누가 무엇을 했는지)
- **authenticator**: IAM 인증 로그
- **controllerManager**: 컨트롤러 매니저 로그
- **scheduler**: 스케줄러 로그

kubelet 로그는 워커 노드에서 생성되며, Control Plane 로그가 아닙니다.

```bash
# Control Plane 로깅 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

</details>

---

### 11. EKS에서 노드 IAM Role과 Pod IAM Role(IRSA)을 분리해야 하는 이유는?

- A) 비용 절감
- B) 최소 권한 원칙 적용
- C) 성능 향상
- D) 네트워크 지연 감소

<details>
<summary>정답 보기</summary>

**정답: B) 최소 권한 원칙 적용**

**설명:**
권한 분리의 중요성:

**노드 IAM Role (넓은 범위):**
- 모든 Pod가 접근 가능 (Instance Metadata)
- ECR 풀, CloudWatch 로그 등 기본 권한만

**IRSA (좁은 범위):**
- 특정 ServiceAccount에만 연결
- 애플리케이션별 필요한 권한만 부여

```yaml
# 잘못된 예: 노드 Role에 S3 전체 접근 권한
# -> 모든 Pod가 S3에 접근 가능

# 올바른 예: IRSA로 특정 Pod에만 권한 부여
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-processor
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/S3ProcessorRole
```

</details>

---

### 12. EKS에서 Kubernetes RBAC과 AWS IAM의 통합을 담당하는 컴포넌트는?

- A) kube-apiserver
- B) aws-auth ConfigMap
- C) aws-iam-authenticator
- D) kube-proxy

<details>
<summary>정답 보기</summary>

**정답: C) aws-iam-authenticator**

**설명:**
EKS 인증 흐름:
1. kubectl이 AWS STS에서 토큰 획득
2. aws-iam-authenticator가 IAM 자격 증명 검증
3. aws-auth ConfigMap에서 IAM -> Kubernetes 사용자/그룹 매핑
4. Kubernetes RBAC이 권한 결정

```yaml
# aws-auth ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-user
      groups:
        - dev-team
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

</details>

---

## 점수 계산

각 문제당 1점으로 계산합니다.

| 점수 | 평가 |
|------|------|
| 11-12 | 우수 - EKS 보안 전문가 수준 |
| 8-10 | 양호 - 기본 개념 이해, 고급 기능 복습 필요 |
| 5-7 | 보통 - 추가 학습 권장 |
| 0-4 | 기초 학습 필요 |

---

## 관련 문서

- [EKS 보안 모범 사례](../security/06-eks-security-best-practices.md)
- [Pod Security Standards](../security/03-pod-security-standards.md)
- [Secrets Management](../security/05-secrets-management.md)
