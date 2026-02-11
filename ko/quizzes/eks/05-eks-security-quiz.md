# Amazon EKS 보안 퀴즈

이 퀴즈는 Amazon EKS의 보안 기능, 모범 사례 및 구성에 대한 이해를 테스트합니다.

## 퀴즈 개요
- EKS 인증 및 권한 부여
- 네트워크 보안
- 컨테이너 보안
- 데이터 보안
- 규정 준수 및 감사
- 보안 모범 사례

## 객관식 문제

### 1. Amazon EKS에서 Kubernetes API 서버에 대한 액세스를 제어하는 가장 효과적인 방법은 무엇인가요?

A. IAM 사용자 및 역할만 사용  
B. Kubernetes RBAC만 사용  
C. IAM 및 Kubernetes RBAC 통합 사용  
D. API 서버에 대한 네트워크 액세스 제한만 사용  

<details>
<summary>정답 및 설명</summary>

**정답: C. IAM 및 Kubernetes RBAC 통합 사용**

**설명:**
Amazon EKS에서 Kubernetes API 서버에 대한 액세스를 제어하는 가장 효과적인 방법은 AWS IAM과 Kubernetes RBAC(역할 기반 액세스 제어)를 통합하여 사용하는 것입니다. 이 접근 방식은 AWS의 강력한 ID 관리 기능과 Kubernetes의 세분화된 권한 제어를 결합하여 포괄적인 보안 모델을 제공합니다.

**IAM 및 RBAC 통합의 주요 이점:**

1. **다중 계층 인증 및 권한 부여**:
   - IAM은 "누가" API 서버에 연결할 수 있는지 제어 (인증)
   - RBAC은 인증된 사용자가 "무엇을" 할 수 있는지 제어 (권한 부여)

2. **AWS 서비스와의 원활한 통합**:
   - 기존 AWS IAM 정책 및 역할 활용
   - AWS 서비스 계정 및 워크로드 ID 활용

3. **세분화된 권한 제어**:
   - 네임스페이스, 리소스 유형, 특정 리소스에 대한 세부적인 권한 정의
   - 최소 권한 원칙 구현

**구현 방법:**

1. **aws-auth ConfigMap 구성**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: aws-auth
     namespace: kube-system
   data:
     mapRoles: |
       - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
         username: admin
         groups:
         - system:masters
       - rolearn: arn:aws:iam::123456789012:role/EKSDeveloperRole
         username: developer
         groups:
         - developers
     mapUsers: |
       - userarn: arn:aws:iam::123456789012:user/security-auditor
         username: security-auditor
         groups:
         - security-auditors
   ```

2. **Kubernetes RBAC 역할 및 바인딩 정의**:
   ```yaml
   # 개발자 역할 정의
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: dev
     name: developer
   rules:
   - apiGroups: ["", "apps", "batch"]
     resources: ["pods", "deployments", "jobs"]
     verbs: ["get", "list", "watch", "create", "update", "patch"]
   ---
   # 개발자 역할 바인딩
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: developer-binding
     namespace: dev
   subjects:
   - kind: Group
     name: developers
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: developer
     apiGroup: rbac.authorization.k8s.io
   ```

3. **IAM 정책 예시**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "eks:DescribeCluster",
           "eks:ListClusters"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

**모범 사례:**

1. **최소 권한 원칙 적용**:
   - 필요한 최소한의 권한만 부여
   - 정기적인 권한 검토 및 감사

2. **역할 기반 액세스 구현**:
   - 직무 기능에 따른 역할 정의
   - 개인이 아닌 역할에 권한 할당

3. **임시 자격 증명 사용**:
   - 장기 자격 증명 대신 임시 자격 증명 사용
   - AWS STS(Security Token Service) 활용

4. **정기적인 감사 및 모니터링**:
   - CloudTrail을 통한 API 호출 로깅
   - Kubernetes 감사 로그 활성화 및 분석

**실제 구현 예시:**

1. **EKS 클러스터 액세스를 위한 IAM 역할 생성**:
   ```bash
   aws iam create-role \
     --role-name EKSDevRole \
     --assume-role-policy-document file://trust-policy.json

   aws iam attach-role-policy \
     --role-name EKSDevRole \
     --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
   ```

2. **kubeconfig 업데이트**:
   ```bash
   aws eks update-kubeconfig \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSDevRole \
     --region us-west-2
   ```

3. **RBAC 구성 적용**:
   ```bash
   kubectl apply -f rbac-config.yaml
   ```

다른 옵션들의 문제점:
- **A. IAM 사용자 및 역할만 사용**: IAM은 클러스터 액세스를 제어할 수 있지만, Kubernetes 리소스에 대한 세분화된 권한을 제공하지 않습니다.
- **B. Kubernetes RBAC만 사용**: RBAC은 클러스터 내 권한을 제어하지만, AWS 서비스와의 통합이 부족하고 AWS 인프라 수준의 보안을 제공하지 않습니다.
- **D. API 서버에 대한 네트워크 액세스 제한만 사용**: 네트워크 수준의 제어는 중요하지만, 인증된 사용자의 권한을 제한하지 않으며 세분화된 액세스 제어를 제공하지 않습니다.
</details>
### 2. Amazon EKS에서 파드 간 네트워크 트래픽을 제한하는 가장 효과적인 방법은 무엇인가요?

A. 보안 그룹만 사용  
B. Kubernetes 네트워크 정책 사용  
C. VPC 엔드포인트 정책 사용  
D. 호스트 기반 방화벽 사용  

<details>
<summary>정답 및 설명</summary>

**정답: B. Kubernetes 네트워크 정책 사용**

**설명:**
Amazon EKS에서 파드 간 네트워크 트래픽을 제한하는 가장 효과적인 방법은 Kubernetes 네트워크 정책을 사용하는 것입니다. 네트워크 정책은 파드 수준에서 마이크로세그멘테이션을 제공하여 파드 간의 통신을 세밀하게 제어할 수 있습니다.

**Kubernetes 네트워크 정책의 주요 이점:**

1. **파드 수준의 세분화된 제어**:
   - IP 주소, 포트, 프로토콜 기반 필터링
   - 레이블 기반 선택기를 통한 동적 정책 적용
   - 인그레스 및 이그레스 트래픽 모두 제어

2. **선언적 구성**:
   - Kubernetes 리소스로 관리
   - GitOps 및 IaC 워크플로우와 통합
   - 버전 제어 및 감사 가능

3. **CNI 플러그인과의 통합**:
   - Amazon VPC CNI, Calico, Cilium 등과 통합
   - 네트워크 정책 시행을 위한 다양한 옵션

**구현 방법:**

1. **기본 거부 정책 구현**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
     namespace: prod
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

2. **특정 애플리케이션 간 통신 허용**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-allow
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: api
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: frontend
       ports:
       - protocol: TCP
         port: 8080
   ```

3. **네임스페이스 간 통신 제어**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-from-monitoring
     namespace: prod
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             purpose: monitoring
       ports:
       - protocol: TCP
         port: 9090
   ```

**EKS에서의 네트워크 정책 구현:**

1. **호환되는 CNI 플러그인 선택**:
   - Amazon VPC CNI + Calico
   - Cilium
   - Antrea

2. **Calico 설치 예시**:
   ```bash
   kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
   ```

3. **Cilium 설치 예시**:
   ```bash
   helm repo add cilium https://helm.cilium.io/
   helm install cilium cilium/cilium \
     --namespace kube-system \
     --set nodeinit.enabled=true \
     --set kubeProxyReplacement=partial \
     --set hostServices.enabled=false \
     --set externalIPs.enabled=true \
     --set nodePort.enabled=true \
     --set hostPort.enabled=true \
     --set bpf.masquerade=false \
     --set image.pullPolicy=IfNotPresent
   ```

**모범 사례:**

1. **기본 거부 정책으로 시작**:
   - 모든 트래픽을 기본적으로 차단
   - 필요한 통신만 명시적으로 허용

2. **최소 권한 원칙 적용**:
   - 필요한 최소한의 통신만 허용
   - 특정 포트 및 프로토콜로 제한

3. **레이블 기반 정책 사용**:
   - IP 주소 대신 레이블 사용
   - 동적 환경에서 유연성 제공

4. **정책 테스트 및 검증**:
   - 비프로덕션 환경에서 정책 테스트
   - 네트워크 정책 시뮬레이터 도구 활용

**실제 구현 예시:**

1. **마이크로서비스 아키텍처의 네트워크 정책**:
   ```yaml
   # 프론트엔드에서 API로의 통신만 허용
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-backend
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: api
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: frontend
       ports:
       - protocol: TCP
         port: 8080
     egress:
     - to:
       - podSelector:
           matchLabels:
             app: database
       ports:
       - protocol: TCP
         port: 5432
   ```

2. **외부 서비스 액세스 제한**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: limit-external
     namespace: prod
   spec:
     podSelector:
       matchLabels:
         app: backend
     policyTypes:
     - Egress
     egress:
     - to:
       - ipBlock:
           cidr: 10.0.0.0/8
     - to:
       - ipBlock:
           cidr: 0.0.0.0/0
           except:
           - 169.254.0.0/16
           - 10.0.0.0/8
       ports:
       - protocol: TCP
         port: 443
   ```

다른 옵션들의 문제점:
- **A. 보안 그룹만 사용**: 보안 그룹은 인스턴스 수준에서 작동하며 파드 간의 세분화된 트래픽 제어를 제공하지 않습니다.
- **C. VPC 엔드포인트 정책 사용**: VPC 엔드포인트 정책은 AWS 서비스에 대한 액세스를 제어하지만, 파드 간 통신을 제어하지 않습니다.
- **D. 호스트 기반 방화벽 사용**: 호스트 기반 방화벽은 노드 수준에서 작동하며, 동일한 노드에서 실행되는 파드 간의 통신을 효과적으로 제어하지 못합니다.
</details>
### 3. Amazon EKS에서 컨테이너 이미지 보안을 강화하기 위한 가장 효과적인 접근 방식은 무엇인가요?

A. 모든 이미지에 대해 수동 보안 검사 수행  
B. 신뢰할 수 있는 공식 이미지만 사용  
C. 이미지 스캔, 서명 확인 및 허용 정책을 포함한 통합 파이프라인 구현  
D. 컨테이너 내에서 바이러스 백신 소프트웨어 실행  

<details>
<summary>정답 및 설명</summary>

**정답: C. 이미지 스캔, 서명 확인 및 허용 정책을 포함한 통합 파이프라인 구현**

**설명:**
Amazon EKS에서 컨테이너 이미지 보안을 강화하기 위한 가장 효과적인 접근 방식은 이미지 스캔, 서명 확인 및 허용 정책을 포함한 통합 파이프라인을 구현하는 것입니다. 이 종합적인 접근 방식은 이미지 빌드부터 배포까지 전체 수명 주기에 걸쳐 보안을 보장합니다.

**통합 이미지 보안 파이프라인의 주요 구성 요소:**

1. **이미지 스캔**:
   - 알려진 취약점(CVE) 검사
   - 악성 코드 및 백도어 탐지
   - 구성 오류 및 보안 모범 사례 위반 식별

2. **이미지 서명 및 확인**:
   - 이미지 무결성 보장
   - 신뢰할 수 있는 출처 확인
   - 변조 방지

3. **허용 정책**:
   - 승인된 이미지만 배포 허용
   - 최소 기본 이미지 요구 사항 적용
   - 취약점 심각도 임계값 설정

**구현 방법:**

1. **Amazon ECR 이미지 스캔 구성**:
   ```bash
   # 리포지토리 생성 시 스캔 활성화
   aws ecr create-repository \
     --repository-name my-app \
     --image-scanning-configuration scanOnPush=true
   
   # 기존 리포지토리에 스캔 활성화
   aws ecr put-image-scanning-configuration \
     --repository-name my-app \
     --image-scanning-configuration scanOnPush=true
   ```

2. **AWS Signer를 사용한 이미지 서명**:
   ```bash
   # 서명 프로필 생성
   aws signer put-signing-profile \
     --profile-name MyAppSigningProfile \
     --platform-id Aws::ECR::Image
   
   # 이미지 서명
   aws signer start-signing-job \
     --source "s3={bucketName=my-bucket,key=my-image.tar}" \
     --destination "s3={bucketName=my-bucket,prefix=signed/}" \
     --profile-name MyAppSigningProfile
   ```

3. **Kyverno를 사용한 이미지 정책 적용**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: require-signed-images
   spec:
     validationFailureAction: enforce
     rules:
     - name: verify-image-signature
       match:
         resources:
           kinds:
           - Pod
       verifyImages:
       - image: "*.dkr.ecr.*.amazonaws.com/*"
         key: "https://my-keystore.com/keys/my-key.pub"
   ```

4. **OPA Gatekeeper를 사용한 이미지 정책 적용**:
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sTrustedImages
   metadata:
     name: trusted-repos
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
     parameters:
       repos:
       - "123456789012.dkr.ecr.us-west-2.amazonaws.com/*"
       - "docker.io/library/*"
   ```

**통합 파이프라인 구축:**

1. **CI/CD 파이프라인 통합**:
   ```yaml
   # AWS CodePipeline 예시
   version: 0.2
   phases:
     pre_build:
       commands:
         - echo Logging in to Amazon ECR...
         - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
     build:
       commands:
         - echo Building the Docker image...
         - docker build -t $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION .
     post_build:
       commands:
         - echo Running security scan...
         - trivy image --exit-code 1 --severity HIGH,CRITICAL $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
         - echo Signing the image...
         - aws signer start-signing-job --profile-name MyAppSigningProfile --source-image $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
         - echo Pushing the Docker image...
         - docker push $ECR_REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
   ```

2. **이미지 허용 컨트롤러 배포**:
   ```bash
   # Kyverno 설치
   kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.8.0/install.yaml
   
   # 정책 적용
   kubectl apply -f image-policy.yaml
   ```

**모범 사례:**

1. **최소 기본 이미지 사용**:
   - 공격 표면 최소화
   - 필요한 구성 요소만 포함
   - 디스트로리스 또는 경량 이미지 사용

2. **다중 계층 방어 구현**:
   - 빌드 시간 스캔
   - 배포 전 검증
   - 런타임 모니터링

3. **정기적인 이미지 업데이트**:
   - 최신 보안 패치 적용
   - 기본 이미지 정기 업데이트
   - 취약점 지속적 모니터링

4. **불변 이미지 사용**:
   - 배포 후 이미지 수정 금지
   - 변경 필요 시 새 이미지 빌드 및 배포
   - 버전 관리 및 롤백 지원

**실제 구현 예시:**

1. **Amazon ECR, AWS CodePipeline 및 Kyverno 통합**:
   ```yaml
   # buildspec.yml
   version: 0.2
   phases:
     pre_build:
       commands:
         - echo Logging in to Amazon ECR...
         - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
         - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
         - IMAGE_TAG=${COMMIT_HASH:=latest}
     build:
       commands:
         - echo Building the Docker image...
         - docker build -t $ECR_REPOSITORY_URI:$IMAGE_TAG .
     post_build:
       commands:
         - echo Running Trivy security scan...
         - trivy image --exit-code 1 --severity HIGH,CRITICAL $ECR_REPOSITORY_URI:$IMAGE_TAG
         - echo Pushing the Docker image...
         - docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
         - echo Creating image definition file...
         - aws ecr describe-images --repository-name $(echo $ECR_REPOSITORY_URI | cut -d'/' -f2) --image-ids imageTag=$IMAGE_TAG --query 'imageDetails[].imageTags[0]' --output text
   artifacts:
     files:
       - imagedefinitions.json
   ```

2. **Kyverno 이미지 정책**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: restrict-image-registries
   spec:
     validationFailureAction: enforce
     background: true
     rules:
     - name: allowed-registries
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Only images from approved registries are allowed"
         pattern:
           spec:
             containers:
             - image: "{{ regex_match('123456789012.dkr.ecr.*.amazonaws.com/*|docker.io/library/*', '@@') }}"
   ```

다른 옵션들의 문제점:
- **A. 모든 이미지에 대해 수동 보안 검사 수행**: 수동 검사는 확장성이 떨어지고, 일관성이 부족하며, 지속적인 배포 환경에서 실용적이지 않습니다.
- **B. 신뢰할 수 있는 공식 이미지만 사용**: 공식 이미지도 취약점이 있을 수 있으며, 사용자 지정 이미지가 필요한 경우가 많습니다.
- **D. 컨테이너 내에서 바이러스 백신 소프트웨어 실행**: 컨테이너 내 바이러스 백신은 리소스를 많이 사용하고, 컨테이너 설계 원칙에 위배되며, 이미지 빌드 단계에서의 보안 문제를 해결하지 못합니다.
</details>
### 4. Amazon EKS에서 파드 보안을 강화하기 위한 가장 효과적인 방법은 무엇인가요?

A. 모든 파드에 대해 특권 모드 비활성화  
B. 파드 보안 표준(PSS) 및 파드 보안 정책(PSP) 구현  
C. 모든 파드를 루트가 아닌 사용자로 실행  
D. 모든 파드에 대해 읽기 전용 파일 시스템 사용  

<details>
<summary>정답 및 설명</summary>

**정답: B. 파드 보안 표준(PSS) 및 파드 보안 정책(PSP) 구현**

**설명:**
Amazon EKS에서 파드 보안을 강화하기 위한 가장 효과적인 방법은 파드 보안 표준(Pod Security Standards, PSS)과 파드 보안 정책(Pod Security Policy, PSP) 또는 그 대체 메커니즘을 구현하는 것입니다. 이러한 메커니즘은 파드의 보안 컨텍스트를 제어하고 클러스터 전체에 일관된 보안 표준을 적용합니다.

**참고**: Kubernetes 1.25부터 PSP(Pod Security Policy)는 더 이상 사용되지 않으며, 대신 PSS(Pod Security Standards)와 PSA(Pod Security Admission)가 권장됩니다. EKS에서는 Kyverno, OPA Gatekeeper와 같은 정책 엔진을 사용하여 유사한 기능을 구현할 수 있습니다.

**파드 보안 표준 및 정책의 주요 이점:**

1. **일관된 보안 표준 적용**:
   - 클러스터 전체에 일관된 보안 제어 적용
   - 권한 에스컬레이션 방지
   - 컨테이너 이스케이프 위험 감소

2. **다양한 보안 수준 지원**:
   - Privileged: 제한 없음
   - Baseline: 기본적인 제한 적용
   - Restricted: 엄격한 보안 제어 적용

3. **세분화된 보안 제어**:
   - 특권 에스컬레이션 제한
   - 호스트 네임스페이스 액세스 제한
   - 볼륨 유형 제한
   - 사용자 및 그룹 ID 제한

**구현 방법:**

1. **Pod Security Standards(PSS) 적용**:
   ```yaml
   # 네임스페이스에 PSS 레이블 적용
   apiVersion: v1
   kind: Namespace
   metadata:
     name: secure-ns
     labels:
       pod-security.kubernetes.io/enforce: restricted
       pod-security.kubernetes.io/audit: restricted
       pod-security.kubernetes.io/warn: restricted
   ```

2. **Kyverno를 사용한 파드 보안 정책 구현**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: restrict-privileged
   spec:
     validationFailureAction: enforce
     rules:
     - name: no-privileged-pods
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privileged mode is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 privileged: false
   ```

3. **OPA Gatekeeper를 사용한 파드 보안 정책 구현**:
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: no-privileged-containers
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
   ```

**주요 파드 보안 제어:**

1. **특권 모드 제한**:
   ```yaml
   securityContext:
     privileged: false
   ```

2. **루트가 아닌 사용자로 실행**:
   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 3000
     fsGroup: 2000
   ```

3. **기능 제한**:
   ```yaml
   securityContext:
     capabilities:
       drop:
       - ALL
       add:
       - NET_BIND_SERVICE
   ```

4. **읽기 전용 루트 파일 시스템**:
   ```yaml
   securityContext:
     readOnlyRootFilesystem: true
   ```

5. **seccomp 프로필 적용**:
   ```yaml
   securityContext:
     seccompProfile:
       type: RuntimeDefault
   ```

**모범 사례:**

1. **최소 권한 원칙 적용**:
   - 필요한 최소한의 권한만 부여
   - 특권 모드 사용 제한
   - 필요한 기능만 허용

2. **다중 방어 계층 구현**:
   - 네임스페이스 수준 정책
   - 클러스터 수준 정책
   - 런타임 보안 모니터링

3. **보안 컨텍스트 명시적 정의**:
   - 기본값에 의존하지 않음
   - 모든 컨테이너에 보안 컨텍스트 지정
   - 정기적인 보안 구성 검토

4. **정책 예외 관리**:
   - 예외가 필요한 경우 명확한 프로세스 정의
   - 예외 정기적 검토 및 감사
   - 예외 최소화

**실제 구현 예시:**

1. **보안이 강화된 파드 정의**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: secure-pod
   spec:
     securityContext:
       fsGroup: 2000
       runAsNonRoot: true
       runAsUser: 1000
       seccompProfile:
         type: RuntimeDefault
     containers:
     - name: app
       image: my-secure-app:1.0
       securityContext:
         allowPrivilegeEscalation: false
         capabilities:
           drop:
           - ALL
         readOnlyRootFilesystem: true
         runAsNonRoot: true
         runAsUser: 1000
         seccompProfile:
           type: RuntimeDefault
   ```

2. **Kyverno 정책 모음**:
   ```yaml
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: pod-security
   spec:
     validationFailureAction: enforce
     rules:
     - name: no-privileged
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privileged containers are not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 privileged: false
     - name: no-privilege-escalation
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Privilege escalation is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 allowPrivilegeEscalation: false
     - name: require-non-root
       match:
         resources:
           kinds:
           - Pod
       validate:
         message: "Running as root is not allowed"
         pattern:
           spec:
             containers:
             - name: "*"
               securityContext:
                 runAsNonRoot: true
   ```

다른 옵션들의 문제점:
- **A. 모든 파드에 대해 특권 모드 비활성화**: 특권 모드 비활성화는 중요하지만, 파드 보안의 한 측면일 뿐이며 포괄적인 보안 전략을 제공하지 않습니다.
- **C. 모든 파드를 루트가 아닌 사용자로 실행**: 루트가 아닌 사용자로 실행하는 것은 좋은 관행이지만, 다른 중요한 보안 제어(예: 기능, 볼륨 마운트, 호스트 네임스페이스 액세스)를 다루지 않습니다.
- **D. 모든 파드에 대해 읽기 전용 파일 시스템 사용**: 읽기 전용 파일 시스템은 유용한 보안 제어이지만, 모든 애플리케이션에 적합하지 않으며 다른 중요한 보안 측면을 다루지 않습니다.
</details>
### 5. Amazon EKS에서 보안 규정 준수를 모니터링하고 감사하기 위한 가장 효과적인 접근 방식은 무엇인가요?

A. 수동 보안 검토 수행  
B. AWS Config 규칙만 사용  
C. AWS GuardDuty만 사용  
D. AWS Security Hub, GuardDuty, CloudTrail 및 Kubernetes 감사 로그의 통합 사용  

<details>
<summary>정답 및 설명</summary>

**정답: D. AWS Security Hub, GuardDuty, CloudTrail 및 Kubernetes 감사 로그의 통합 사용**

**설명:**
Amazon EKS에서 보안 규정 준수를 모니터링하고 감사하기 위한 가장 효과적인 접근 방식은 AWS Security Hub, GuardDuty, CloudTrail 및 Kubernetes 감사 로그를 통합하여 사용하는 것입니다. 이 통합 접근 방식은 인프라, 클러스터 및 애플리케이션 수준에서 포괄적인 보안 가시성을 제공합니다.

**통합 보안 모니터링 및 감사의 주요 이점:**

1. **다중 계층 보안 가시성**:
   - AWS 인프라 수준 모니터링
   - Kubernetes 클러스터 수준 감사
   - 컨테이너 및 애플리케이션 수준 보안 이벤트

2. **자동화된 규정 준수 검사**:
   - 산업 표준 및 모범 사례 준수 확인
   - 구성 드리프트 감지
   - 지속적인 규정 준수 모니터링

3. **중앙 집중식 보안 관리**:
   - 단일 대시보드에서 보안 상태 확인
   - 통합된 알림 및 대응
   - 포괄적인 보안 보고서

**구현 방법:**

1. **AWS Security Hub 활성화**:
   ```bash
   # Security Hub 활성화
   aws securityhub enable-security-hub \
     --enable-default-standards \
     --tags Environment=Production
   ```

2. **Amazon GuardDuty EKS Protection 활성화**:
   ```bash
   # GuardDuty 활성화
   aws guardduty create-detector \
     --enable \
     --finding-publishing-frequency FIFTEEN_MINUTES
   
   # EKS Protection 활성화
   aws guardduty update-detector \
     --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text) \
     --features '[{"Name": "EKS_RUNTIME_MONITORING", "Status": "ENABLED"}]'
   ```

3. **CloudTrail 로깅 구성**:
   ```bash
   # CloudTrail 트레일 생성
   aws cloudtrail create-trail \
     --name eks-audit-trail \
     --s3-bucket-name my-eks-audit-logs \
     --is-multi-region-trail \
     --enable-log-file-validation
   
   # 트레일 로깅 활성화
   aws cloudtrail start-logging \
     --name eks-audit-trail
   ```

4. **EKS 감사 로그 활성화**:
   ```bash
   # 클러스터 생성 시 감사 로그 활성화
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   
   # 기존 클러스터에 감사 로그 활성화
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

**주요 모니터링 및 감사 구성 요소:**

1. **AWS Security Hub**:
   - EKS 모범 사례 표준 적용
   - CIS Kubernetes 벤치마크 검사
   - 보안 결과 중앙 집중화

2. **Amazon GuardDuty**:
   - EKS 런타임 모니터링
   - 컨테이너 위협 탐지
   - 이상 행동 감지

3. **AWS CloudTrail**:
   - EKS 컨트롤 플레인 API 호출 로깅
   - 관리 이벤트 추적
   - 사용자 활동 감사

4. **Kubernetes 감사 로그**:
   - 클러스터 내 활동 로깅
   - API 서버 요청 추적
   - 권한 변경 모니터링

5. **Amazon CloudWatch**:
   - 로그 중앙 집중화
   - 메트릭 모니터링
   - 알림 구성

**모범 사례:**

1. **포괄적인 로깅 전략 구현**:
   - 모든 관련 로그 소스 활성화
   - 적절한 로그 보존 정책 설정
   - 로그 무결성 보장

2. **자동화된 규정 준수 검사 구성**:
   - 정기적인 규정 준수 스캔 일정 설정
   - 중요한 위반에 대한 알림 구성
   - 규정 준수 보고서 자동화

3. **보안 이벤트에 대한 대응 계획 수립**:
   - 명확한 에스컬레이션 경로 정의
   - 자동화된 대응 구현
   - 정기적인 대응 계획 테스트

4. **최소 권한 원칙 적용**:
   - 감사 로그에 대한 액세스 제한
   - 보안 도구에 대한 역할 기반 액세스 제어
   - 권한 정기적 검토

**실제 구현 예시:**

1. **AWS Security Hub 및 GuardDuty 통합**:
   ```bash
   # Security Hub 결과를 SNS 주제로 전송
   aws events put-rule \
     --name SecurityHubFindings \
     --event-pattern '{"source":["aws.securityhub"],"detail-type":["Security Hub Findings - Imported"]}'
   
   aws events put-targets \
     --rule SecurityHubFindings \
     --targets 'Id"="1","Arn"="arn:aws:sns:us-west-2:123456789012:security-alerts"'
   ```

2. **CloudWatch Logs Insights를 사용한 감사 로그 분석**:
   ```
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-audit/
   | filter @message like "system:serviceaccount"
   | filter @message like "create" or @message like "update" or @message like "delete"
   | sort @timestamp desc
   | limit 100
   ```

3. **AWS Config 규칙을 사용한 EKS 구성 모니터링**:
   ```bash
   # EKS 클러스터 엔드포인트 공개 여부 확인하는 Config 규칙 생성
   aws configservice put-config-rule \
     --config-rule file://eks-endpoint-rule.json
   ```

4. **Terraform을 사용한 보안 모니터링 인프라 구성**:
   ```hcl
   # GuardDuty 활성화
   resource "aws_guardduty_detector" "main" {
     enable = true
     finding_publishing_frequency = "FIFTEEN_MINUTES"
   }
   
   # EKS Protection 활성화
   resource "aws_guardduty_detector_feature" "eks_runtime" {
     detector_id = aws_guardduty_detector.main.id
     name        = "EKS_RUNTIME_MONITORING"
     status      = "ENABLED"
   }
   
   # Security Hub 활성화
   resource "aws_securityhub_account" "main" {}
   
   # EKS 표준 활성화
   resource "aws_securityhub_standards_subscription" "cis_eks" {
     depends_on    = [aws_securityhub_account.main]
     standards_arn = "arn:aws:securityhub:${data.aws_region.current.name}::standards/aws-foundational-security-best-practices/v/1.0.0"
   }
   ```

다른 옵션들의 문제점:
- **A. 수동 보안 검토 수행**: 수동 검토는 확장성이 떨어지고, 실시간 위협 탐지를 제공하지 않으며, 인적 오류에 취약합니다.
- **B. AWS Config 규칙만 사용**: AWS Config는 구성 규정 준수를 모니터링하는 데 유용하지만, 런타임 위협 탐지나 포괄적인 로깅을 제공하지 않습니다.
- **C. AWS GuardDuty만 사용**: GuardDuty는 위협 탐지에 중점을 두지만, 구성 규정 준수 검사나 포괄적인 감사 로깅을 제공하지 않습니다.
</details>
### 6. Amazon EKS에서 비밀(Secrets) 관리를 위한 가장 안전한 접근 방식은 무엇인가요?

A. Kubernetes Secrets를 기본 설정으로 사용  
B. 환경 변수로 비밀 전달  
C. AWS Secrets Manager 또는 AWS Parameter Store와 통합  
D. 컨테이너 이미지에 비밀 하드코딩  

<details>
<summary>정답 및 설명</summary>

**정답: C. AWS Secrets Manager 또는 AWS Parameter Store와 통합**

**설명:**
Amazon EKS에서 비밀(Secrets) 관리를 위한 가장 안전한 접근 방식은 AWS Secrets Manager 또는 AWS Parameter Store와 같은 전용 비밀 관리 서비스와 통합하는 것입니다. 이러한 서비스는 암호화, 액세스 제어, 자동 교체 및 감사와 같은 고급 보안 기능을 제공합니다.

**AWS 비밀 관리 서비스 통합의 주요 이점:**

1. **강력한 암호화**:
   - AWS KMS를 사용한 저장 데이터 암호화
   - 전송 중 데이터 암호화
   - 세분화된 암호화 키 관리

2. **세분화된 액세스 제어**:
   - IAM 정책을 통한 액세스 제어
   - 최소 권한 원칙 적용
   - 임시 자격 증명 지원

3. **비밀 자동 교체**:
   - 정기적인 비밀 교체 자동화
   - 애플리케이션 중단 없는 교체
   - 교체 일정 및 정책 관리

4. **포괄적인 감사 및 로깅**:
   - 비밀 액세스 감사
   - CloudTrail과의 통합
   - 규정 준수 요구 사항 충족

**구현 방법:**

1. **AWS Secrets Manager와 통합**:

   a. **ASCP(AWS Secrets and Configuration Provider) 설치**:
   ```bash
   helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
   helm install -n kube-system csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver
   
   kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
   ```

   b. **SecretProviderClass 생성**:
   ```yaml
   apiVersion: secrets-store.csi.x-k8s.io/v1
   kind: SecretProviderClass
   metadata:
     name: aws-secrets
   spec:
     provider: aws
     parameters:
       objects: |
         - objectName: "prod/myapp/db-creds"
           objectType: "secretsmanager"
           objectAlias: "db-creds.json"
     secretObjects:
     - secretName: db-credentials
       type: Opaque
       data:
       - objectName: db-creds.json
         key: username
         property: username
       - objectName: db-creds.json
         key: password
         property: password
   ```

   c. **파드에 비밀 마운트**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: app
   spec:
     containers:
     - name: app
       image: myapp:1.0
       volumeMounts:
       - name: secrets-store
         mountPath: "/mnt/secrets"
         readOnly: true
       env:
       - name: DB_USERNAME
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: username
       - name: DB_PASSWORD
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: password
     volumes:
     - name: secrets-store
       csi:
         driver: secrets-store.csi.k8s.io
         readOnly: true
         volumeAttributes:
           secretProviderClass: aws-secrets
   ```

2. **AWS Parameter Store와 통합**:

   a. **External Secrets Operator 설치**:
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     -n external-secrets \
     --create-namespace
   ```

   b. **SecretStore 생성**:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: SecretStore
   metadata:
     name: aws-parameter-store
   spec:
     provider:
       aws:
         service: ParameterStore
         region: us-west-2
         auth:
           jwt:
             serviceAccountRef:
               name: external-secrets-sa
   ```

   c. **ExternalSecret 생성**:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: db-credentials
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: aws-parameter-store
       kind: SecretStore
     target:
       name: db-credentials
     data:
     - secretKey: username
       remoteRef:
         key: /prod/myapp/db/username
     - secretKey: password
       remoteRef:
         key: /prod/myapp/db/password
   ```

**비밀 관리 모범 사례:**

1. **최소 권한 원칙 적용**:
   - 필요한 비밀에만 액세스 권한 부여
   - 서비스 계정별 IAM 역할 사용
   - 정기적인 권한 검토

2. **비밀 자동 교체 구현**:
   ```bash
   # AWS Secrets Manager 자동 교체 구성
   aws secretsmanager rotate-secret \
     --secret-id prod/myapp/db-creds \
     --rotation-lambda-arn arn:aws:lambda:us-west-2:123456789012:function:RotateDBCreds \
     --rotation-rules '{"AutomaticallyAfterDays": 30}'
   ```

3. **비밀 암호화 강화**:
   ```bash
   # 고객 관리형 KMS 키로 비밀 암호화
   aws secretsmanager create-secret \
     --name prod/myapp/api-key \
     --secret-string '{"api-key": "abcdef12345"}' \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **비밀 액세스 감사**:
   ```bash
   # CloudTrail 이벤트 필터링
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=EventName,AttributeValue=GetSecretValue
   ```

**실제 구현 예시:**

1. **AWS Secrets Manager와 IRSA(IAM Roles for Service Accounts) 통합**:
   ```yaml
   # 서비스 계정 생성
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: app-sa
     namespace: default
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/app-role
   ---
   # 배포 구성
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: app
   spec:
     selector:
       matchLabels:
         app: myapp
     template:
       metadata:
         labels:
           app: myapp
       spec:
         serviceAccountName: app-sa
         containers:
         - name: app
           image: myapp:1.0
           volumeMounts:
           - name: secrets-store
             mountPath: "/mnt/secrets"
             readOnly: true
         volumes:
         - name: secrets-store
           csi:
             driver: secrets-store.csi.k8s.io
             readOnly: true
             volumeAttributes:
               secretProviderClass: aws-secrets
   ```

2. **Terraform을 사용한 비밀 관리 인프라 구성**:
   ```hcl
   # AWS Secrets Manager 비밀 생성
   resource "aws_secretsmanager_secret" "db_credentials" {
     name                    = "prod/myapp/db-creds"
     recovery_window_in_days = 7
     kms_key_id              = aws_kms_key.secrets_key.arn
   }
   
   resource "aws_secretsmanager_secret_version" "db_credentials" {
     secret_id     = aws_secretsmanager_secret.db_credentials.id
     secret_string = jsonencode({
       username = "dbuser",
       password = random_password.db_password.result
     })
   }
   
   # IAM 역할 및 정책
   resource "aws_iam_role" "app_role" {
     name = "app-role"
     assume_role_policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Principal = {
           Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${module.eks.oidc_provider}"
         },
         Action = "sts:AssumeRoleWithWebIdentity",
         Condition = {
           StringEquals = {
             "${module.eks.oidc_provider}:sub" = "system:serviceaccount:default:app-sa"
           }
         }
       }]
     })
   }
   
   resource "aws_iam_policy" "secrets_access" {
     name = "secrets-access"
     policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Action = [
           "secretsmanager:GetSecretValue",
           "secretsmanager:DescribeSecret"
         ],
         Resource = aws_secretsmanager_secret.db_credentials.arn
       }]
     })
   }
   
   resource "aws_iam_role_policy_attachment" "secrets_access" {
     role       = aws_iam_role.app_role.name
     policy_arn = aws_iam_policy.secrets_access.arn
   }
   ```

다른 옵션들의 문제점:
- **A. Kubernetes Secrets를 기본 설정으로 사용**: 기본 Kubernetes Secrets는 base64로 인코딩되어 있을 뿐 암호화되지 않으며, 자동 교체나 세분화된 액세스 제어 기능이 부족합니다.
- **B. 환경 변수로 비밀 전달**: 환경 변수는 로그에 노출되거나 프로세스 정보를 통해 액세스될 수 있으며, 자동 교체나 감사 기능이 없습니다.
- **D. 컨테이너 이미지에 비밀 하드코딩**: 이미지에 비밀을 하드코딩하는 것은 심각한 보안 위험을 초래하며, 비밀 교체 시 이미지를 다시 빌드하고 배포해야 합니다.
</details>
