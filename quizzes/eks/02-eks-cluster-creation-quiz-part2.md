# Amazon EKS 클러스터 생성 퀴즈 (Part 2)

이 퀴즈는 Amazon EKS 클러스터 생성과 관련된 고급 개념, 보안 설정, 네트워킹 구성에 대한 이해를 테스트합니다. 클러스터 보안, 네트워크 정책, 서비스 계정 등의 주제를 다룹니다.

## 기본 개념 문제

1. Amazon EKS 클러스터에서 IRSA(IAM Roles for Service Accounts)의 주요 목적은 무엇인가요?
   - A) 클러스터 관리자에게 IAM 권한 부여
   - B) 워커 노드에 IAM 역할 할당
   - C) Kubernetes 서비스 계정에 AWS 서비스 접근 권한 부여
   - D) EKS 컨트롤 플레인에 IAM 권한 부여
   
<details>
<summary>정답 보기</summary>

**정답: C) Kubernetes 서비스 계정에 AWS 서비스 접근 권한 부여**

**설명:**
IRSA(IAM Roles for Service Accounts)의 주요 목적은 Kubernetes 서비스 계정에 AWS 서비스 접근 권한을 부여하는 것입니다. 이 기능을 통해 포드 수준에서 세분화된 권한을 제공할 수 있으며, 노드 수준의 IAM 역할을 공유하는 대신 각 애플리케이션에 필요한 최소한의 권한만 부여할 수 있습니다.

#### IRSA의 작동 방식:

1. **OpenID Connect(OIDC) 제공자 설정**:
   - EKS 클러스터는 OIDC 제공자로 구성됩니다.
   - 이를 통해 Kubernetes 서비스 계정 토큰이 AWS IAM에서 신뢰할 수 있는 인증 메커니즘이 됩니다.
   ```bash
   # OIDC 제공자 연결
   eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
   ```

2. **IAM 역할 생성 및 신뢰 정책 구성**:
   - Kubernetes 서비스 계정이 맡을 수 있는 IAM 역할을 생성합니다.
   - 신뢰 정책은 특정 네임스페이스의 특정 서비스 계정만 역할을 맡을 수 있도록 제한합니다.
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
           }
         }
       }
     ]
   }
   ```

3. **서비스 계정 생성 및 IAM 역할 연결**:
   - 서비스 계정에 IAM 역할 ARN을 주석으로 추가합니다.
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: my-service-account
     namespace: default
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
   ```

4. **포드에서 서비스 계정 사용**:
   - 포드 매니페스트에서 서비스 계정을 지정합니다.
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: my-pod
   spec:
     serviceAccountName: my-service-account
     containers:
     - name: my-container
       image: my-image
   ```

#### IRSA의 이점:

1. **최소 권한 원칙**:
   - 각 애플리케이션에 필요한 최소한의 권한만 부여할 수 있습니다.
   - 노드 수준의 IAM 역할을 공유하는 대신 포드별로 다른 권한 설정 가능

2. **보안 강화**:
   - AWS 자격 증명을 코드나 환경 변수에 저장할 필요가 없습니다.
   - 자격 증명 유출 위험 감소

3. **권한 격리**:
   - 같은 노드에서 실행되는 다른 포드는 서로 다른 IAM 권한을 가질 수 있습니다.
   - 멀티테넌트 환경에서 중요

4. **자격 증명 관리 간소화**:
   - AWS 자격 증명을 직접 관리할 필요가 없습니다.
   - 자격 증명 순환이 자동으로 처리됩니다.

#### eksctl을 사용한 IRSA 설정 예시:

```bash
# 서비스 계정과 IAM 역할 생성
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve

# 생성된 서비스 계정 확인
kubectl get serviceaccount my-service-account -o yaml
```

#### 다른 옵션들의 문제점:

- **클러스터 관리자에게 IAM 권한 부여**: 이는 IRSA의 목적이 아닙니다. 클러스터 관리자 권한은 일반적으로 aws-auth ConfigMap을 통해 관리됩니다.

- **워커 노드에 IAM 역할 할당**: 이는 노드 IAM 역할을 통해 수행되며, IRSA와는 별개입니다. 노드 IAM 역할은 모든 포드가 공유하므로 최소 권한 원칙을 위반할 수 있습니다.

- **EKS 컨트롤 플레인에 IAM 권한 부여**: EKS 컨트롤 플레인 권한은 클러스터 IAM 역할을 통해 관리되며, IRSA와는 관련이 없습니다.

IRSA는 Kubernetes 워크로드가 AWS 서비스에 안전하게 접근할 수 있도록 하는 중요한 기능으로, EKS 클러스터에서 애플리케이션을 실행할 때 권장되는 접근 방식입니다.
</details>
2. Amazon EKS 클러스터에서 보안 그룹의 주요 역할은 무엇인가요?
   - A) 포드 간 네트워크 트래픽 제어
   - B) 클러스터 API 서버 및 노드 간 트래픽 제어
   - C) Kubernetes RBAC 정책 적용
   - D) 사용자 인증 관리
   
<details>
<summary>정답 보기</summary>

**정답: B) 클러스터 API 서버 및 노드 간 트래픽 제어**

**설명:**
Amazon EKS 클러스터에서 보안 그룹의 주요 역할은 클러스터 API 서버와 노드 간의 트래픽을 제어하는 것입니다. 보안 그룹은 AWS의 가상 방화벽으로, EC2 인스턴스 수준에서 인바운드 및 아웃바운드 트래픽을 제어합니다. EKS에서는 클러스터 보안 그룹과 노드 보안 그룹이 있으며, 이들은 클러스터 구성 요소 간의 통신을 보호합니다.

#### EKS 클러스터의 보안 그룹 유형:

1. **클러스터 보안 그룹**:
   - EKS 컨트롤 플레인에 적용됩니다.
   - 워커 노드와 컨트롤 플레인 간의 통신을 허용합니다.
   - 기본적으로 EKS 클러스터 생성 시 자동으로 생성됩니다.
   - 주요 규칙:
     - 노드 보안 그룹으로부터의 443 포트 인바운드 트래픽 허용
     - 노드 보안 그룹으로의 아웃바운드 트래픽 허용

2. **노드 보안 그룹**:
   - 워커 노드에 적용됩니다.
   - 노드 간 통신 및 노드와 컨트롤 플레인 간의 통신을 허용합니다.
   - 주요 규칙:
     - 노드 간 모든 트래픽 허용
     - 클러스터 보안 그룹으로의 443 포트 아웃바운드 트래픽 허용
     - 클러스터 보안 그룹으로부터의 인바운드 트래픽 허용
     - kubelet을 위한 10250 포트 허용

#### 보안 그룹 구성 예시:

**클러스터 보안 그룹 규칙**:
```
인바운드:
- 프로토콜: TCP
- 포트 범위: 443
- 소스: 노드 보안 그룹

아웃바운드:
- 프로토콜: 모든 트래픽
- 포트 범위: 모든 포트
- 대상: 0.0.0.0/0
```

**노드 보안 그룹 규칙**:
```
인바운드:
- 프로토콜: 모든 트래픽
- 소스: 노드 보안 그룹 자체 (노드 간 통신)

- 프로토콜: TCP
- 포트 범위: 10250
- 소스: 클러스터 보안 그룹 (kubelet 통신)

아웃바운드:
- 프로토콜: 모든 트래픽
- 포트 범위: 모든 포트
- 대상: 0.0.0.0/0
```

#### 보안 그룹 사용자 지정:

EKS 클러스터 생성 시 사용자 지정 보안 그룹을 지정할 수 있습니다:

```bash
# AWS CLI를 사용한 사용자 지정 보안 그룹 지정
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345

# eksctl을 사용한 사용자 지정 보안 그룹 지정
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-12345
  securityGroup: sg-12345
  subnets:
    private:
      us-west-2a: subnet-12345
      us-west-2b: subnet-67890
```

#### 포드 보안 그룹:

최근에는 EKS에서 포드 수준의 보안 그룹도 지원합니다(SecurityGroupsForPods 기능). 이를 통해 개별 포드에 보안 그룹을 적용할 수 있습니다:

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: my-security-group-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: my-app
  securityGroups:
    groupIds:
      - sg-12345
```

#### 다른 옵션들의 문제점:

- **포드 간 네트워크 트래픽 제어**: 기본적으로 포드 간 네트워크 트래픽은 AWS 보안 그룹이 아닌 Kubernetes 네트워크 정책(NetworkPolicy)을 통해 제어됩니다. SecurityGroupsForPods 기능을 사용하면 포드 수준에서 보안 그룹을 적용할 수 있지만, 이는 보안 그룹의 주요 역할이 아닙니다.

- **Kubernetes RBAC 정책 적용**: RBAC(Role-Based Access Control)는 Kubernetes API 리소스에 대한 접근을 제어하는 메커니즘으로, AWS 보안 그룹과는 별개입니다.

- **사용자 인증 관리**: EKS 클러스터의 사용자 인증은 AWS IAM과 Kubernetes RBAC의 통합을 통해 관리되며, 보안 그룹과는 관련이 없습니다.

보안 그룹은 EKS 클러스터의 네트워크 보안에 중요한 역할을 하며, 클러스터 구성 요소 간의 통신을 보호하고 불필요한 트래픽을 차단합니다. 적절한 보안 그룹 구성은 EKS 클러스터의 보안 태세를 강화하는 데 필수적입니다.
</details>

3. Amazon EKS 클러스터에서 Kubernetes 네트워크 정책(NetworkPolicy)을 구현하기 위해 필요한 것은 무엇인가요?
   - A) AWS 보안 그룹 구성
   - B) Calico 또는 Cilium과 같은 네트워크 정책 지원 CNI 플러그인
   - C) AWS Network Firewall 설정
   - D) VPC 흐름 로그 활성화
   
<details>
<summary>정답 보기</summary>

**정답: B) Calico 또는 Cilium과 같은 네트워크 정책 지원 CNI 플러그인**

**설명:**
Amazon EKS 클러스터에서 Kubernetes 네트워크 정책(NetworkPolicy)을 구현하기 위해서는 Calico 또는 Cilium과 같은 네트워크 정책을 지원하는 CNI(Container Network Interface) 플러그인이 필요합니다. 기본 Amazon VPC CNI 플러그인은 네트워크 정책을 지원하지 않으므로, 추가 구성 요소를 설치해야 합니다.

#### 네트워크 정책 지원 CNI 옵션:

1. **Calico**:
   - 널리 사용되는 오픈 소스 네트워킹 및 네트워크 보안 솔루션
   - EKS에서 Amazon VPC CNI와 함께 사용 가능
   - 설치 방법:
     ```bash
     # Helm을 사용한 Calico 설치
     helm repo add projectcalico https://docs.projectcalico.org/charts
     helm install calico projectcalico/tigera-operator --namespace tigera-operator --create-namespace
     
     # 또는 매니페스트 파일을 사용한 설치
     kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
     ```

2. **Cilium**:
   - eBPF 기반 네트워킹, 보안 및 관찰성 솔루션
   - 고성능 및 고급 기능 제공
   - 설치 방법:
     ```bash
     # Helm을 사용한 Cilium 설치
     helm repo add cilium https://helm.cilium.io/
     helm install cilium cilium/cilium --namespace kube-system
     ```

3. **AWS CNI with Cilium**:
   - Amazon VPC CNI와 Cilium을 함께 사용하는 하이브리드 접근 방식
   - VPC CNI는 포드 네트워킹을 처리하고, Cilium은 네트워크 정책을 처리
   - 설치 방법:
     ```bash
     # Cilium을 네트워크 정책 전용 모드로 설치
     helm install cilium cilium/cilium --namespace kube-system \
       --set enableIPv4Masquerade=false \
       --set tunnel=disabled \
       --set installIptablesRules=false \
       --set autoDirectNodeRoutes=false \
       --set policyEnforcementMode=default
     ```

#### 네트워크 정책 예시:

```yaml
# 기본 거부 정책
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

# 특정 애플리케이션 간 통신 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

#### 네트워크 정책 구현 확인:

```bash
# 네트워크 정책 지원 확인
kubectl get pods -n kube-system | grep -E 'calico|cilium'

# 테스트 네트워크 정책 적용
kubectl apply -f test-network-policy.yaml

# 연결 테스트
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- --timeout=2 http://service-name
```

#### 다른 옵션들의 문제점:

- **AWS 보안 그룹 구성**: AWS 보안 그룹은 EC2 인스턴스 수준에서 작동하며, Kubernetes 포드 간의 세분화된 네트워크 정책을 구현하는 데 사용할 수 없습니다. SecurityGroupsForPods 기능을 사용하면 포드에 보안 그룹을 적용할 수 있지만, 이는 Kubernetes NetworkPolicy와는 다른 메커니즘입니다.

- **AWS Network Firewall 설정**: AWS Network Firewall은 VPC 수준에서 작동하며, Kubernetes 포드 간의 세분화된 네트워크 정책을 구현하는 데 사용할 수 없습니다.

- **VPC 흐름 로그 활성화**: VPC 흐름 로그는 네트워크 트래픽을 모니터링하고 로깅하는 데 사용되지만, 네트워크 정책을 구현하는 데는 사용할 수 없습니다.

네트워크 정책은 Kubernetes 클러스터 내에서 마이크로서비스 간의 통신을 제어하고 보안을 강화하는 중요한 도구입니다. EKS에서 네트워크 정책을 구현하려면 Calico 또는 Cilium과 같은 추가 CNI 플러그인을 설치해야 합니다.
</details>

4. Amazon EKS 클러스터에서 Secrets 암호화를 구성하는 올바른 방법은 무엇인가요?
   - A) AWS KMS 키를 사용하여 EKS 클러스터 생성 시 암호화 활성화
   - B) Kubernetes Secrets를 AWS Secrets Manager로 마이그레이션
   - C) 모든 Secret을 Base64로 인코딩
   - D) EKS 클러스터에 암호화 사이드카 컨테이너 배포
   
<details>
<summary>정답 보기</summary>

**정답: A) AWS KMS 키를 사용하여 EKS 클러스터 생성 시 암호화 활성화**

**설명:**
Amazon EKS 클러스터에서 Secrets 암호화를 구성하는 올바른 방법은 AWS KMS(Key Management Service) 키를 사용하여 EKS 클러스터 생성 시 또는 기존 클러스터에서 암호화를 활성화하는 것입니다. 이 방법을 통해 Kubernetes Secrets가 etcd에 저장될 때 암호화되어 저장됩니다.

#### EKS Secrets 암호화 구성 단계:

1. **KMS 키 생성 또는 기존 키 사용**:
   ```bash
   # KMS 키 생성
   aws kms create-key --description "EKS Secrets Encryption Key"
   
   # 생성된 키 ID 저장
   KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)
   ```

2. **새 클러스터 생성 시 암호화 활성화**:
   ```bash
   # AWS CLI를 사용한 암호화 활성화
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890 \
     --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:region:123456789012:key/'$KEY_ID'"}}]'
   
   # eksctl을 사용한 암호화 활성화
   cat > cluster.yaml << EOF
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   secretsEncryption:
     keyARN: arn:aws:kms:us-west-2:123456789012:key/$KEY_ID
   EOF
   
   eksctl create cluster -f cluster.yaml
   ```

3. **기존 클러스터에서 암호화 활성화**:
   ```bash
   # 기존 클러스터에서는 암호화 구성을 업데이트할 수 없으므로, 새 클러스터를 생성하고 워크로드를 마이그레이션해야 합니다.
   ```

4. **암호화 구성 확인**:
   ```bash
   # 클러스터 정보 확인
   aws eks describe-cluster --name my-cluster --query cluster.encryptionConfig
   ```

#### 암호화된 Secrets 사용:

암호화가 활성화되면 Secrets 생성 및 사용 방법은 변경되지 않습니다. 모든 암호화 및 복호화는 EKS 컨트롤 플레인에서 자동으로 처리됩니다.

```yaml
# Secret 생성
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQ=  # base64 encoded "password"
```

```bash
# Secret 생성
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=password

# Secret 확인
kubectl get secret my-secret -o yaml
```

#### KMS 키 권한 구성:

EKS 클러스터가 KMS 키를 사용할 수 있도록 적절한 권한을 구성해야 합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEKSToUseKMSKey",
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 다른 옵션들의 문제점:

- **Kubernetes Secrets를 AWS Secrets Manager로 마이그레이션**: 이는 가능한 접근 방식이지만, 표준 Kubernetes Secrets API와의 호환성이 떨어지며, 추가 구성 및 통합이 필요합니다. 또한 모든 애플리케이션이 AWS Secrets Manager에서 비밀을 가져오도록 수정해야 합니다.

- **모든 Secret을 Base64로 인코딩**: Kubernetes Secrets는 이미 기본적으로 Base64로 인코딩됩니다. 그러나 Base64는 암호화가 아닌 인코딩 방식으로, 보안을 제공하지 않습니다.

- **EKS 클러스터에 암호화 사이드카 컨테이너 배포**: 이는 표준 접근 방식이 아니며, 모든 포드에 사이드카를 추가해야 하는 복잡성이 있습니다. 또한 Kubernetes API 서버와의 통합이 필요합니다.

AWS KMS를 사용한 EKS Secrets 암호화는 etcd에 저장된 Secrets를 보호하는 가장 효과적이고 통합된 방법입니다. 이를 통해 저장 중인 민감한 데이터를 보호하고, AWS의 강력한 키 관리 기능을 활용할 수 있습니다.
</details>
5. Amazon EKS 클러스터에서 워커 노드의 kubelet 구성을 사용자 지정하는 올바른 방법은 무엇인가요?
   - A) EKS 콘솔에서 클러스터 구성 수정
   - B) 노드 그룹 생성 시 --kubelet-extra-args 파라미터 사용
   - C) kubectl edit node 명령어 사용
   - D) AWS Systems Manager를 사용하여 노드 구성 변경
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드 그룹 생성 시 --kubelet-extra-args 파라미터 사용**

**설명:**
Amazon EKS 클러스터에서 워커 노드의 kubelet 구성을 사용자 지정하는 올바른 방법은 노드 그룹 생성 시 `--kubelet-extra-args` 파라미터를 사용하는 것입니다. 이 방법을 통해 노드가 부트스트랩될 때 kubelet에 추가 인수를 전달할 수 있습니다.

#### kubelet 구성 사용자 지정 방법:

1. **관리형 노드 그룹에서 시작 템플릿 사용**:
   - 시작 템플릿의 사용자 데이터 섹션에서 부트스트랩 스크립트를 사용자 지정합니다.
   ```bash
   #!/bin/bash
   set -o xtrace
   /etc/eks/bootstrap.sh my-cluster \
     --kubelet-extra-args '--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m --system-reserved memory=0.5Gi,cpu=200m --eviction-hard memory.available<500Mi'
   ```

2. **eksctl을 사용한 노드 그룹 생성**:
   ```bash
   # kubelet 인수를 지정하여 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name my-nodegroup \
     --node-type m5.large \
     --nodes 3 \
     --kubelet-extra-args "--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m"
   ```

3. **eksctl 구성 파일 사용**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
     - name: my-nodegroup
       instanceType: m5.large
       minSize: 2
       maxSize: 5
       kubeletExtraArgs:
         max-pods: "110"
         kube-reserved: "memory=0.3Gi,cpu=100m"
         system-reserved: "memory=0.5Gi,cpu=200m"
         eviction-hard: "memory.available<500Mi"
   ```

4. **자체 관리형 노드 그룹에서 사용자 데이터 스크립트 사용**:
   ```bash
   #!/bin/bash
   set -o xtrace
   /etc/eks/bootstrap.sh my-cluster \
     --kubelet-extra-args '--max-pods=110 --node-labels=node.kubernetes.io/role=worker,environment=prod'
   ```

#### 일반적으로 사용자 지정하는 kubelet 파라미터:

1. **max-pods**:
   - 노드당 최대 포드 수 설정
   - 예: `--max-pods=110`

2. **node-labels**:
   - 노드에 레이블 추가
   - 예: `--node-labels=environment=prod,node-type=worker`

3. **kube-reserved**:
   - Kubernetes 시스템 구성 요소를 위한 리소스 예약
   - 예: `--kube-reserved=cpu=100m,memory=0.3Gi,ephemeral-storage=1Gi`

4. **system-reserved**:
   - OS 시스템 데몬을 위한 리소스 예약
   - 예: `--system-reserved=cpu=100m,memory=0.5Gi,ephemeral-storage=1Gi`

5. **eviction-hard**:
   - 강제 축출 임계값 설정
   - 예: `--eviction-hard=memory.available<500Mi,nodefs.available<10%`

6. **cgroup-driver**:
   - cgroup 드라이버 설정
   - 예: `--cgroup-driver=systemd`

#### 구성 확인 방법:

```bash
# 노드에 SSH 접속
ssh -i ~/.ssh/id_rsa ec2-user@<node-ip>

# kubelet 서비스 구성 확인
sudo systemctl status kubelet
sudo cat /etc/systemd/system/kubelet.service.d/10-kubelet-args.conf

# 실행 중인 kubelet 프로세스 인수 확인
ps aux | grep kubelet
```

#### 다른 옵션들의 문제점:

- **EKS 콘솔에서 클러스터 구성 수정**: EKS 콘솔에서는 클러스터 수준 구성을 수정할 수 있지만, 개별 노드의 kubelet 구성을 직접 수정할 수 있는 옵션은 제공하지 않습니다.

- **kubectl edit node 명령어 사용**: `kubectl edit node` 명령어는 노드 객체의 메타데이터를 수정할 수 있지만, kubelet 구성을 변경할 수는 없습니다. kubelet 구성은 노드 OS에서 서비스로 실행되며, Kubernetes API를 통해 직접 수정할 수 없습니다.

- **AWS Systems Manager를 사용하여 노드 구성 변경**: AWS Systems Manager를 사용하여 노드에 명령을 실행하거나 구성을 변경할 수 있지만, 이는 노드가 이미 생성된 후에 적용되는 방법입니다. 또한 kubelet 구성을 변경한 후에는 서비스를 재시작해야 하며, 이는 실행 중인 포드에 영향을 줄 수 있습니다. 따라서 노드 그룹 생성 시 구성하는 것이 더 안전하고 권장되는 방법입니다.

kubelet 구성을 사용자 지정하면 노드 리소스 관리, 포드 밀도, 축출 정책 등을 워크로드 요구 사항에 맞게 최적화할 수 있습니다. 그러나 변경 사항이 클러스터 안정성에 영향을 줄 수 있으므로 신중하게 테스트해야 합니다.
</details>

6. Amazon EKS 클러스터에서 포드 보안 정책(Pod Security Policy)을 대체하는 권장 메커니즘은 무엇인가요?
   - A) AWS Security Hub
   - B) Pod Security Admission 또는 Kyverno와 같은 정책 엔진
   - C) AWS Config Rules
   - D) EKS 보안 그룹
   
<details>
<summary>정답 보기</summary>

**정답: B) Pod Security Admission 또는 Kyverno와 같은 정책 엔진**

**설명:**
Amazon EKS 클러스터에서 포드 보안 정책(Pod Security Policy, PSP)을 대체하는 권장 메커니즘은 Pod Security Admission 또는 Kyverno와 같은 정책 엔진입니다. Kubernetes 1.21부터 PSP는 사용 중단(deprecated)되었으며, Kubernetes 1.25에서 완전히 제거되었습니다. 이를 대체하기 위해 Pod Security Admission이 도입되었고, Kyverno나 OPA Gatekeeper와 같은 정책 엔진도 대안으로 사용할 수 있습니다.

#### Pod Security Admission:

Pod Security Admission은 Kubernetes 1.23부터 베타 기능으로 도입되었으며, 1.25부터 안정화 단계에 진입했습니다. 이는 Kubernetes에 내장된 기능으로, 세 가지 보안 수준(Privileged, Baseline, Restricted)을 제공합니다.

1. **구성 방법**:
   ```yaml
   # 네임스페이스에 Pod Security 표준 적용
   apiVersion: v1
   kind: Namespace
   metadata:
     name: my-namespace
     labels:
       pod-security.kubernetes.io/enforce: restricted
       pod-security.kubernetes.io/audit: restricted
       pod-security.kubernetes.io/warn: restricted
   ```

2. **보안 수준**:
   - **Privileged**: 제한 없음, 모든 기능 허용
   - **Baseline**: 알려진 권한 상승 방지
   - **Restricted**: 강력한 보안 강화, 최소 권한 원칙 적용

3. **모드**:
   - **enforce**: 위반 시 포드 생성 거부
   - **audit**: 위반 사항 감사 로그에 기록
   - **warn**: 위반 시 경고 메시지 표시

#### Kyverno:

Kyverno는 Kubernetes 네이티브 정책 엔진으로, YAML 기반의 정책을 사용하여 클러스터 리소스를 검증, 변경, 생성할 수 있습니다.

1. **설치 방법**:
   ```bash
   # Helm을 사용한 Kyverno 설치
   helm repo add kyverno https://kyverno.github.io/kyverno/
   helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace
   ```

2. **정책 예시**:
   ```yaml
   # 권한 있는 컨테이너 방지 정책
   apiVersion: kyverno.io/v1
   kind: ClusterPolicy
   metadata:
     name: disallow-privileged-containers
   spec:
     validationFailureAction: enforce
     rules:
     - name: privileged-containers
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
   ```

#### OPA Gatekeeper:

OPA(Open Policy Agent) Gatekeeper는 Kubernetes의 정책 관리를 위한 또 다른 인기 있는 솔루션입니다.

1. **설치 방법**:
   ```bash
   # Gatekeeper 설치
   kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
   ```

2. **정책 예시**:
   ```yaml
   # ConstraintTemplate 정의
   apiVersion: templates.gatekeeper.sh/v1beta1
   kind: ConstraintTemplate
   metadata:
     name: k8spsprivilegedcontainer
   spec:
     crd:
       spec:
         names:
           kind: K8sPSPPrivilegedContainer
     targets:
     - target: admission.k8s.gatekeeper.sh
       rego: |
         package k8spsprivilegedcontainer
         violation[{"msg": msg}] {
           c := input.review.object.spec.containers[_]
           c.securityContext.privileged
           msg := sprintf("Privileged container is not allowed: %v", [c.name])
         }
   
   # Constraint 적용
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: psp-privileged-container
   spec:
     match:
       kinds:
       - apiGroups: [""]
         kinds: ["Pod"]
   ```

#### EKS에서의 구현 권장 사항:

1. **Pod Security Admission 활성화**:
   - EKS 1.23 이상에서는 기본적으로 사용 가능
   - 네임스페이스에 적절한 레이블 적용

2. **Kyverno 또는 Gatekeeper 설치**:
   - 더 복잡한 정책이 필요한 경우
   - 여러 리소스 유형에 대한 정책이 필요한 경우

3. **점진적 마이그레이션**:
   - PSP에서 새로운 솔루션으로 점진적으로 마이그레이션
   - 감사 모드에서 시작하여 문제 식별 후 적용 모드로 전환

#### 다른 옵션들의 문제점:

- **AWS Security Hub**: AWS Security Hub는 AWS 리소스의 보안 상태를 모니터링하는 서비스이지만, Kubernetes 포드 수준의 보안 정책을 적용하는 데 사용할 수 없습니다.

- **AWS Config Rules**: AWS Config는 AWS 리소스 구성을 평가하는 서비스이지만, Kubernetes 포드 수준의 보안 정책을 적용하는 데 사용할 수 없습니다.

- **EKS 보안 그룹**: EKS 보안 그룹은 네트워크 트래픽을 제어하는 데 사용되며, 포드의 보안 컨텍스트나 권한을 제한하는 데 사용할 수 없습니다.

포드 보안 정책(PSP)이 제거됨에 따라, EKS 클러스터에서는 Pod Security Admission, Kyverno, OPA Gatekeeper와 같은 대체 메커니즘을 사용하여 포드 보안을 강화해야 합니다. 이러한 도구를 통해 권한 있는 컨테이너, 호스트 네임스페이스 접근, 호스트 경로 마운트 등을 제한할 수 있습니다.
</details>
7. Amazon EKS 클러스터에서 포드 ID를 AWS IAM과 통합하기 위한 IRSA(IAM Roles for Service Accounts)를 구성하는 첫 번째 단계는 무엇인가요?
   - A) IAM 역할 생성
   - B) 서비스 계정 생성
   - C) OIDC 제공자 연결
   - D) 포드 매니페스트 수정
   
<details>
<summary>정답 보기</summary>

**정답: C) OIDC 제공자 연결**

**설명:**
Amazon EKS 클러스터에서 IRSA(IAM Roles for Service Accounts)를 구성하는 첫 번째 단계는 OIDC(OpenID Connect) 제공자를 연결하는 것입니다. OIDC 제공자는 AWS IAM과 Kubernetes 서비스 계정 간의 신뢰 관계를 설정하는 데 필요합니다. 이를 통해 Kubernetes 서비스 계정 토큰이 AWS IAM에서 신뢰할 수 있는 인증 메커니즘이 됩니다.

#### IRSA 구성 단계 순서:

1. **OIDC 제공자 연결**:
   - EKS 클러스터의 OIDC 발급자 URL 확인
   - AWS IAM에 OIDC 제공자 생성
   ```bash
   # OIDC 발급자 URL 확인
   aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text
   # 출력 예: https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE
   
   # OIDC 제공자 연결
   eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
   
   # 또는 AWS CLI 사용
   aws iam create-open-id-connect-provider \
     --url https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE \
     --thumbprint-list 9e99a48a9960b14926bb7f3b02e22da2b0ab7280 \
     --client-id-list sts.amazonaws.com
   ```

2. **IAM 역할 생성**:
   - 서비스 계정이 맡을 IAM 역할 생성
   - 신뢰 정책에 OIDC 제공자 및 서비스 계정 조건 포함
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
           }
         }
       }
     ]
   }
   ```

3. **서비스 계정 생성**:
   - IAM 역할 ARN을 주석으로 포함하는 서비스 계정 생성
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: my-service-account
     namespace: default
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
   ```

4. **포드 매니페스트 수정**:
   - 포드 매니페스트에서 서비스 계정 지정
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: my-pod
   spec:
     serviceAccountName: my-service-account
     containers:
     - name: my-container
       image: my-image
   ```

#### eksctl을 사용한 간소화된 IRSA 설정:

eksctl은 위의 모든 단계를 자동화하는 명령어를 제공합니다:

```bash
# OIDC 제공자 연결
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

# 서비스 계정 및 IAM 역할 생성
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

#### IRSA 작동 확인:

```bash
# 서비스 계정 확인
kubectl get serviceaccount my-service-account -o yaml

# 테스트 포드 실행
kubectl run -it --rm \
  --image amazon/aws-cli \
  --serviceaccount my-service-account \
  aws-cli -- s3 ls
```

#### 다른 옵션들의 문제점:

- **IAM 역할 생성**: IAM 역할 생성은 IRSA 구성의 두 번째 단계입니다. OIDC 제공자가 먼저 연결되어야 IAM 역할의 신뢰 정책에서 OIDC 제공자를 참조할 수 있습니다.

- **서비스 계정 생성**: 서비스 계정 생성은 IRSA 구성의 세 번째 단계입니다. IAM 역할이 먼저 생성되어야 서비스 계정에 IAM 역할 ARN을 주석으로 추가할 수 있습니다.

- **포드 매니페스트 수정**: 포드 매니페스트 수정은 IRSA 구성의 마지막 단계입니다. 서비스 계정이 먼저 생성되어야 포드에서 해당 서비스 계정을 참조할 수 있습니다.

IRSA는 Kubernetes 워크로드에 AWS 서비스에 대한 세분화된 권한을 부여하는 안전하고 효율적인 방법입니다. 이를 통해 노드 수준의 IAM 역할을 공유하는 대신 각 애플리케이션에 필요한 최소한의 권한만 부여할 수 있습니다. IRSA 구성의 첫 번째 단계는 OIDC 제공자를 연결하는 것이며, 이는 AWS IAM과 Kubernetes 서비스 계정 간의 신뢰 관계를 설정하는 데 필수적입니다.
</details>

8. Amazon EKS 클러스터에서 컨트롤 플레인 로그를 활성화하는 올바른 방법은 무엇인가요?
   - A) CloudWatch 에이전트를 EKS 컨트롤 플레인에 설치
   - B) AWS CLI 또는 콘솔을 통해 클러스터 로깅 구성 활성화
   - C) Fluentd를 사용하여 로그 전달 구성
   - D) EKS 컨트롤 플레인 노드에 SSH 접속하여 로그 구성 수정
   
<details>
<summary>정답 보기</summary>

**정답: B) AWS CLI 또는 콘솔을 통해 클러스터 로깅 구성 활성화**

**설명:**
Amazon EKS 클러스터에서 컨트롤 플레인 로그를 활성화하는 올바른 방법은 AWS CLI 또는 AWS Management Console을 통해 클러스터 로깅 구성을 활성화하는 것입니다. EKS는 관리형 서비스로, 컨트롤 플레인은 AWS에서 관리하므로 직접 접근하거나 에이전트를 설치할 수 없습니다. 대신 AWS에서 제공하는 API를 통해 로깅을 구성해야 합니다.

#### AWS CLI를 사용한 컨트롤 플레인 로그 활성화:

```bash
# 모든 로그 유형 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# 특정 로그 유형만 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
```

#### eksctl을 사용한 컨트롤 플레인 로그 활성화:

```bash
# 모든 로그 유형 활성화
eksctl utils update-cluster-logging \
  --enable-types api,audit,authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2

# 특정 로그 유형만 활성화
eksctl utils update-cluster-logging \
  --enable-types api,audit \
  --disable-types authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2
```

#### AWS Management Console을 사용한 컨트롤 플레인 로그 활성화:

1. AWS Management Console에 로그인합니다.
2. EKS 서비스로 이동합니다.
3. 클러스터 목록에서 대상 클러스터를 선택합니다.
4. "로깅" 탭을 선택합니다.
5. "관리"를 클릭합니다.
6. 활성화할 로그 유형을 선택합니다:
   - API 서버(api)
   - 감사(audit)
   - 인증자(authenticator)
   - 컨트롤러 관리자(controllerManager)
   - 스케줄러(scheduler)
7. "변경 사항 저장"을 클릭합니다.

#### 사용 가능한 로그 유형:

1. **API 서버(api)**:
   - Kubernetes API 서버의 로그
   - API 요청 및 응답 정보 포함

2. **감사(audit)**:
   - 클러스터 내 모든 활동에 대한 감사 로그
   - 보안 및 규정 준수 목적으로 중요

3. **인증자(authenticator)**:
   - AWS IAM Authenticator의 로그
   - 인증 관련 문제 해결에 유용

4. **컨트롤러 관리자(controllerManager)**:
   - Kubernetes 컨트롤러 관리자의 로그
   - 리소스 상태 관리 관련 정보 포함

5. **스케줄러(scheduler)**:
   - Kubernetes 스케줄러의 로그
   - 포드 스케줄링 결정 관련 정보 포함

#### 로그 확인 방법:

활성화된 로그는 CloudWatch Logs에 저장되며, 다음 로그 그룹에서 확인할 수 있습니다:
```
/aws/eks/my-cluster/cluster
```

각 로그 유형은 별도의 로그 스트림으로 저장됩니다:
```
kube-apiserver-xxxxx
audit-xxxxx
authenticator-xxxxx
kube-controller-manager-xxxxx
kube-scheduler-xxxxx
```

#### 비용 고려 사항:

- 컨트롤 플레인 로그는 CloudWatch Logs 요금이 적용됩니다.
- 모든 로그 유형을 활성화하면 상당한 양의 로그가 생성될 수 있습니다.
- 비용 최적화를 위해 필요한 로그 유형만 선택적으로 활성화하는 것이 좋습니다.
- 로그 보존 기간을 적절히 설정하여 비용을 관리할 수 있습니다.

#### 다른 옵션들의 문제점:

- **CloudWatch 에이전트를 EKS 컨트롤 플레인에 설치**: EKS 컨트롤 플레인은 AWS에서 관리하므로 직접 접근하거나 에이전트를 설치할 수 없습니다.

- **Fluentd를 사용하여 로그 전달 구성**: Fluentd는 워커 노드의 로그를 수집하는 데 사용할 수 있지만, EKS 컨트롤 플레인 로그에는 접근할 수 없습니다.

- **EKS 컨트롤 플레인 노드에 SSH 접속하여 로그 구성 수정**: EKS 컨트롤 플레인 노드는 AWS에서 관리하므로 직접 SSH 접속할 수 없습니다.

EKS 컨트롤 플레인 로그는 클러스터 문제 해결, 보안 감사, 규정 준수 등에 중요한 정보를 제공합니다. AWS CLI 또는 AWS Management Console을 통해 필요한 로그 유형을 선택적으로 활성화하여 효과적으로 모니터링할 수 있습니다.
</details>

9. Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 변경하는 올바른 방법은 무엇인가요?
   - A) AWS Management Console에서 노드 그룹 인스턴스 유형 직접 수정
   - B) 새 인스턴스 유형으로 새 노드 그룹 생성 후 워크로드 마이그레이션
   - C) kubectl edit 명령어로 노드 사양 수정
   - D) AWS CLI update-nodegroup-config 명령어 사용
   
<details>
<summary>정답 보기</summary>

**정답: B) 새 인스턴스 유형으로 새 노드 그룹 생성 후 워크로드 마이그레이션**

**설명:**
Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 변경하는 올바른 방법은 새 인스턴스 유형으로 새 노드 그룹을 생성한 후 워크로드를 마이그레이션하는 것입니다. EKS 관리형 노드 그룹에서는 생성 후 인스턴스 유형을 직접 변경할 수 없으므로, 새 노드 그룹을 생성하고 워크로드를 마이그레이션한 후 기존 노드 그룹을 삭제하는 방식으로 변경해야 합니다.

#### 노드 그룹 인스턴스 유형 변경 단계:

1. **새 노드 그룹 생성**:
   ```bash
   # eksctl을 사용한 새 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name my-new-nodegroup \
     --node-type m5.large \
     --nodes 3 \
     --nodes-min 1 \
     --nodes-max 5 \
     --node-labels "migration-target=true"
   
   # AWS CLI를 사용한 새 노드 그룹 생성
   aws eks create-nodegroup \
     --cluster-name my-cluster \
     --nodegroup-name my-new-nodegroup \
     --subnets subnet-12345 subnet-67890 \
     --instance-types m5.large \
     --scaling-config minSize=1,maxSize=5,desiredSize=3 \
     --node-role arn:aws:iam::123456789012:role/EksNodeRole \
     --labels migration-target=true
   ```

2. **새 노드 그룹 상태 확인**:
   ```bash
   # 노드 그룹 상태 확인
   aws eks describe-nodegroup \
     --cluster-name my-cluster \
     --nodegroup-name my-new-nodegroup \
     --query "nodegroup.status"
   
   # 노드 확인
   kubectl get nodes --label-columns migration-target
   ```

3. **워크로드 마이그레이션**:
   
   **방법 1: 코드네이션(Cordoning) 및 드레이닝(Draining) 사용**
   ```bash
   # 기존 노드 그룹의 노드 식별
   OLD_NODES=$(kubectl get nodes -l alpha.eksctl.io/nodegroup-name=my-old-nodegroup -o jsonpath='{.items[*].metadata.name}')
   
   # 노드 코드네이션 (새 포드 스케줄링 방지)
   for node in $OLD_NODES; do
     kubectl cordon $node
   done
   
   # 노드 드레이닝 (기존 포드 제거)
   for node in $OLD_NODES; do
     kubectl drain $node --ignore-daemonsets --delete-emptydir-data
   done
   ```
   
   **방법 2: 포드 선택기 사용**
   ```yaml
   # 노드 선택기를 사용하여 새 노드에 배포
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: my-app
   spec:
     template:
       spec:
         nodeSelector:
           migration-target: "true"
   ```
   
   **방법 3: 블루/그린 배포**
   - 새 배포 버전을 새 노드 그룹에 배포
   - 트래픽을 점진적으로 새 버전으로 전환
   - 기존 배포 버전 제거

4. **기존 노드 그룹 삭제**:
   ```bash
   # eksctl을 사용한 노드 그룹 삭제
   eksctl delete nodegroup \
     --cluster my-cluster \
     --name my-old-nodegroup
   
   # AWS CLI를 사용한 노드 그룹 삭제
   aws eks delete-nodegroup \
     --cluster-name my-cluster \
     --nodegroup-name my-old-nodegroup
   ```

#### 마이그레이션 시 고려 사항:

1. **워크로드 중단 최소화**:
   - PodDisruptionBudget 구성
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: my-app-pdb
   spec:
     minAvailable: 2  # 또는 maxUnavailable: 1
     selector:
       matchLabels:
         app: my-app
   ```
   - 롤링 업데이트 전략 사용

2. **리소스 요구 사항**:
   - 새 인스턴스 유형이 워크로드 요구 사항을 충족하는지 확인
   - CPU, 메모리, 스토리지, 네트워킹 요구 사항 고려

3. **상태 저장 워크로드**:
   - 영구 볼륨을 사용하는 워크로드의 경우 데이터 지속성 확인
   - 필요한 경우 백업 수행

4. **비용 영향**:
   - 새 인스턴스 유형의 비용 영향 평가
   - 마이그레이션 중 일시적으로 두 노드 그룹이 동시에 실행되므로 비용 증가

#### 다른 옵션들의 문제점:

- **AWS Management Console에서 노드 그룹 인스턴스 유형 직접 수정**: EKS 관리형 노드 그룹에서는 생성 후 인스턴스 유형을 직접 수정할 수 없습니다.

- **kubectl edit 명령어로 노드 사양 수정**: kubectl은 Kubernetes API 객체를 수정하는 데 사용되지만, 노드의 기본 인스턴스 유형은 AWS 인프라 수준에서 결정되므로 kubectl을 통해 변경할 수 없습니다.

- **AWS CLI update-nodegroup-config 명령어 사용**: `update-nodegroup-config` 명령어는 노드 그룹의 크기 조정 구성, 레이블, 테인트 등을 수정할 수 있지만, 인스턴스 유형은 변경할 수 없습니다.

노드 그룹의 인스턴스 유형을 변경하는 것은 클러스터 성능 최적화, 비용 절감, 또는 새로운 워크로드 요구 사항 충족을 위해 필요할 수 있습니다. 새 노드 그룹을 생성하고 워크로드를 마이그레이션하는 방식은 중단을 최소화하면서 안전하게 인스턴스 유형을 변경할 수 있는 권장 방법입니다.
</details>
10. Amazon EKS 클러스터에서 노드 그룹에 Kubernetes 테인트(Taint)를 적용하는 올바른 방법은 무엇인가요?
    - A) kubectl taint 명령어 사용
    - B) 노드 그룹 생성 시 --taints 파라미터 사용
    - C) AWS Management Console에서 노드 그룹 테인트 구성
    - D) 노드 부트스트랩 스크립트에서 kubelet 구성 수정
    
<details>
<summary>정답 보기</summary>

**정답: B) 노드 그룹 생성 시 --taints 파라미터 사용**

**설명:**
Amazon EKS 클러스터에서 노드 그룹에 Kubernetes 테인트(Taint)를 적용하는 올바른 방법은 노드 그룹 생성 시 `--taints` 파라미터를 사용하는 것입니다. EKS 관리형 노드 그룹은 생성 시 또는 업데이트 시 테인트를 구성할 수 있는 기능을 제공합니다. 이 방법을 사용하면 노드 그룹의 모든 노드에 일관되게 테인트가 적용되며, 노드 교체 시에도 테인트가 유지됩니다.

#### eksctl을 사용한 테인트 구성:

```bash
# 테인트를 포함한 노드 그룹 생성
eksctl create nodegroup \
  --cluster my-cluster \
  --name tainted-ng \
  --node-type m5.large \
  --nodes 3 \
  --taints "dedicated=gpu:NoSchedule,special=true:PreferNoSchedule"

# 구성 파일을 사용한 테인트 구성
cat > nodegroup.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    taints:
      - key: dedicated
        value: gpu
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
EOF

eksctl create nodegroup -f nodegroup.yaml
```

#### AWS CLI를 사용한 테인트 구성:

```bash
# 테인트를 포함한 노드 그룹 생성
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --subnets subnet-12345 subnet-67890 \
  --instance-types m5.large \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role arn:aws:iam::123456789012:role/EksNodeRole \
  --taints "key=dedicated,value=gpu,effect=NoSchedule" "key=special,value=true,effect=PreferNoSchedule"

# 기존 노드 그룹 테인트 업데이트
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --taints "addOrUpdateTaints=[{key=dedicated,value=gpu,effect=NoSchedule}],removeTaints=[{key=special}]"
```

#### AWS Management Console을 사용한 테인트 구성:

1. AWS Management Console에 로그인합니다.
2. EKS 서비스로 이동합니다.
3. 클러스터를 선택합니다.
4. "컴퓨팅" 탭을 선택합니다.
5. "노드 그룹 추가"를 클릭합니다.
6. 노드 그룹 세부 정보를 입력합니다.
7. "Kubernetes 테인트" 섹션에서 "테인트 추가"를 클릭합니다.
8. 키, 값, 효과를 입력합니다.
9. "생성"을 클릭합니다.

#### 테인트 효과 유형:

1. **NoSchedule**:
   - 테인트와 일치하는 톨러레이션이 없는 포드는 노드에 스케줄링되지 않습니다.
   - 기존 포드는 영향을 받지 않습니다.

2. **PreferNoSchedule**:
   - 테인트와 일치하는 톨러레이션이 없는 포드는 가능하면 노드에 스케줄링되지 않지만, 보장되지는 않습니다.
   - 다른 노드에 스케줄링할 수 없는 경우 이 노드에 스케줄링될 수 있습니다.

3. **NoExecute**:
   - 테인트와 일치하는 톨러레이션이 없는 포드는 노드에 스케줄링되지 않습니다.
   - 이미 실행 중인 포드 중 테인트와 일치하는 톨러레이션이 없는 포드는 축출됩니다.

#### 테인트를 사용하는 일반적인 사례:

1. **특수 하드웨어 노드 분리**:
   ```bash
   # GPU 노드에 테인트 적용
   eksctl create nodegroup \
     --cluster my-cluster \
     --name gpu-nodes \
     --node-type p3.2xlarge \
     --taints "dedicated=gpu:NoSchedule"
   
   # GPU 워크로드에 톨러레이션 추가
   apiVersion: v1
   kind: Pod
   metadata:
     name: gpu-pod
   spec:
     tolerations:
     - key: "dedicated"
       operator: "Equal"
       value: "gpu"
       effect: "NoSchedule"
     containers:
     - name: gpu-container
       image: gpu-image
   ```

2. **노드 유지 관리 준비**:
   ```bash
   # 노드에 테인트 적용
   kubectl taint nodes node1 maintenance=planned:NoSchedule
   
   # 유지 관리 후 테인트 제거
   kubectl taint nodes node1 maintenance=planned:NoSchedule-
   ```

3. **특정 워크로드 전용 노드 구성**:
   ```bash
   # 프로덕션 워크로드 전용 노드 그룹
   eksctl create nodegroup \
     --cluster my-cluster \
     --name prod-nodes \
     --node-type m5.large \
     --taints "environment=production:NoSchedule"
   
   # 프로덕션 배포에 톨러레이션 추가
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: prod-app
   spec:
     template:
       spec:
         tolerations:
         - key: "environment"
           operator: "Equal"
           value: "production"
           effect: "NoSchedule"
   ```

#### 다른 옵션들의 문제점:

- **kubectl taint 명령어 사용**: `kubectl taint` 명령어를 사용하여 개별 노드에 테인트를 적용할 수 있지만, 이는 일시적인 변경이며 노드가 교체되면 테인트가 유지되지 않습니다. 또한 노드 그룹의 모든 노드에 일관되게 적용하기 어렵습니다.

- **AWS Management Console에서 노드 그룹 테인트 구성**: AWS Management Console에서도 노드 그룹 생성 시 테인트를 구성할 수 있지만, 이는 "노드 그룹 생성 시 --taints 파라미터 사용"과 동일한 접근 방식입니다. 따라서 이 옵션은 정답이 될 수 있지만, 기술적으로는 노드 그룹 생성 시 테인트를 구성하는 것과 같습니다.

- **노드 부트스트랩 스크립트에서 kubelet 구성 수정**: 부트스트랩 스크립트에서 `--register-with-taints` 플래그를 사용하여 kubelet 구성을 수정할 수 있지만, 이는 복잡하고 오류가 발생하기 쉬운 방법입니다. 또한 EKS 관리형 노드 그룹에서는 권장되지 않습니다.

테인트는 특정 워크로드를 특정 노드에만 배포하거나, 특정 노드에서 특정 워크로드를 제외하는 데 유용한 Kubernetes 기능입니다. EKS 관리형 노드 그룹에서는 노드 그룹 생성 시 또는 업데이트 시 테인트를 구성하는 것이 가장 효과적이고 관리하기 쉬운 방법입니다.
</details>

## 실습 문제

### 실습 1: IRSA(IAM Roles for Service Accounts) 구성

**시나리오:**
당신은 EKS 클러스터에서 실행되는 애플리케이션이 S3 버킷에 접근해야 하는 상황에 있습니다. 보안 모범 사례에 따라 노드 IAM 역할을 공유하는 대신 IRSA를 사용하여 특정 포드에만 필요한 권한을 부여하려고 합니다.

**요구사항:**
1. OIDC 제공자 연결
2. S3 접근 권한이 있는 IAM 역할 생성
3. 서비스 계정 생성 및 IAM 역할 연결
4. 서비스 계정을 사용하는 포드 배포
5. S3 접근 테스트

**해결 방법:**

<details>
<summary>해결 방법 보기</summary>

#### 1. OIDC 제공자 연결

```bash
# 클러스터의 OIDC 발급자 URL 확인
OIDC_PROVIDER=$(aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# OIDC 제공자가 이미 존재하는지 확인
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# OIDC 제공자가 없는 경우 생성
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

#### 2. S3 접근 권한이 있는 IAM 역할 생성

```bash
# 신뢰 정책 생성
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:default:s3-access-sa"
        }
      }
    }
  ]
}
EOF

# IAM 역할 생성
aws iam create-role --role-name s3-access-role --assume-role-policy-document file://trust-policy.json

# S3 접근 정책 연결
aws iam attach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

#### 3. 서비스 계정 생성 및 IAM 역할 연결

```bash
# IAM 역할 ARN 가져오기
ROLE_ARN=$(aws iam get-role --role-name s3-access-role --query Role.Arn --output text)

# 서비스 계정 생성
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml
```

#### 4. 서비스 계정을 사용하는 포드 배포

```bash
# 테스트 포드 배포
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-access-pod
  namespace: default
spec:
  serviceAccountName: s3-access-sa
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f pod.yaml
```

#### 5. S3 접근 테스트

```bash
# 포드가 실행 중인지 확인
kubectl get pod s3-access-pod

# S3 버킷 목록 조회 테스트
kubectl exec -it s3-access-pod -- aws s3 ls

# 특정 S3 버킷의 객체 목록 조회 테스트
kubectl exec -it s3-access-pod -- aws s3 ls s3://my-bucket

# AWS 자격 증명 확인
kubectl exec -it s3-access-pod -- aws sts get-caller-identity
```

#### 6. 정리

```bash
# 포드 삭제
kubectl delete pod s3-access-pod

# 서비스 계정 삭제
kubectl delete serviceaccount s3-access-sa

# IAM 역할 정리
aws iam detach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name s3-access-role
```

#### 추가 설명:

1. **OIDC 제공자 연결**:
   - OIDC 제공자는 AWS IAM과 Kubernetes 서비스 계정 간의 신뢰 관계를 설정합니다.
   - 클러스터당 한 번만 설정하면 됩니다.

2. **IAM 역할 신뢰 정책**:
   - 신뢰 정책은 특정 네임스페이스의 특정 서비스 계정만 역할을 맡을 수 있도록 제한합니다.
   - 조건문을 사용하여 보안을 강화합니다.

3. **서비스 계정 주석**:
   - `eks.amazonaws.com/role-arn` 주석은 서비스 계정이 맡을 IAM 역할을 지정합니다.
   - 이 주석은 EKS Pod Identity Webhook에 의해 처리됩니다.

4. **환경 변수**:
   - EKS Pod Identity Webhook는 포드에 다음 환경 변수를 자동으로 주입합니다:
     - `AWS_ROLE_ARN`
     - `AWS_WEB_IDENTITY_TOKEN_FILE`
     - `AWS_REGION`
   - AWS SDK는 이러한 환경 변수를 사용하여 자격 증명을 획득합니다.

5. **최소 권한 원칙**:
   - 애플리케이션에 필요한 최소한의 권한만 부여합니다.
   - 이 예제에서는 S3 읽기 전용 접근 권한만 부여했습니다.

이 실습을 통해 IRSA를 구성하여 EKS 클러스터에서 실행되는 특정 포드에만 AWS 서비스에 대한 세분화된 권한을 부여하는 방법을 배웠습니다. 이 접근 방식은 노드 IAM 역할을 공유하는 것보다 더 안전하며, 최소 권한 원칙을 따릅니다.
</details>
### 실습 2: EKS 클러스터 보안 강화

**시나리오:**
당신은 회사의 보안 엔지니어로, 새로 생성된 EKS 클러스터의 보안을 강화해야 합니다. 클러스터는 이미 생성되어 있으며, 기본 설정으로 구성되어 있습니다. 보안 모범 사례에 따라 클러스터를 강화하려고 합니다.

**요구사항:**
1. 클러스터 엔드포인트 액세스 제한
2. Secrets 암호화 활성화
3. 네트워크 정책 구현
4. Pod Security 표준 적용
5. 컨트롤 플레인 로깅 활성화

**해결 방법:**

<details>
<summary>해결 방법 보기</summary>

#### 1. 클러스터 엔드포인트 액세스 제한

```bash
# 현재 클러스터 엔드포인트 구성 확인
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPublicAccess"
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPrivateAccess"

# 퍼블릭 액세스 제한 (특정 CIDR 블록만 허용)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]

# 또는 퍼블릭 액세스 비활성화 (프라이빗 클러스터)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

#### 2. Secrets 암호화 활성화

```bash
# KMS 키 생성
aws kms create-key --description "EKS Secrets Encryption Key"
KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)

# KMS 키에 별칭 추가
aws kms create-alias \
  --alias-name alias/eks-secrets \
  --target-key-id $KEY_ID

# 현재 클러스터에서는 암호화를 활성화할 수 없으므로, 새 클러스터를 생성해야 함
# 기존 클러스터 구성 가져오기
aws eks describe-cluster --name my-cluster > cluster-config.json

# 새 클러스터 생성 (실제로는 더 많은 파라미터가 필요)
aws eks create-cluster \
  --name my-cluster-encrypted \
  --role-arn $(aws eks describe-cluster --name my-cluster --query cluster.roleArn --output text) \
  --resources-vpc-config subnetIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.subnetIds --output text | tr -d '[]" ' | tr ',' ' '),securityGroupIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.securityGroupIds --output text | tr -d '[]" ') \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:'$(aws configure get region)':'$(aws sts get-caller-identity --query Account --output text)':key/'$KEY_ID'"}}]'
```

#### 3. 네트워크 정책 구현

```bash
# Calico 설치
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# 기본 거부 네트워크 정책 생성
cat > default-deny.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF

kubectl apply -f default-deny.yaml

# 특정 애플리케이션 간 통신 허용 정책
cat > allow-app-communication.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
EOF

kubectl apply -f allow-app-communication.yaml
```

#### 4. Pod Security 표준 적용

```bash
# 네임스페이스에 Pod Security 표준 적용
cat > pod-security.yaml << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF

kubectl apply -f pod-security.yaml

# 기존 네임스페이스에 레이블 추가
kubectl label namespace default \
  pod-security.kubernetes.io/enforce=baseline \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Kyverno 설치 (추가적인 정책 적용을 위해)
kubectl create namespace kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno --namespace kyverno

# 권한 있는 컨테이너 방지 정책
cat > restrict-privileged.yaml << EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
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
EOF

kubectl apply -f restrict-privileged.yaml
```

#### 5. 컨트롤 플레인 로깅 활성화

```bash
# 모든 컨트롤 플레인 로그 유형 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# 로그 활성화 상태 확인
aws eks describe-cluster --name my-cluster --query "cluster.logging"

# CloudWatch Logs에서 로그 확인
aws logs describe-log-groups --log-group-name-prefix /aws/eks/my-cluster
```

#### 6. 추가 보안 강화 조치

```bash
# AWS Load Balancer Controller에 대한 IAM 정책 제한
cat > alb-controller-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name EksAlbControllerRestrictedPolicy \
  --policy-document file://alb-controller-policy.json

# 정기적인 노드 교체를 위한 노드 그룹 업데이트 구성
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# 노드 그룹 업데이트 시작
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

#### 보안 강화 설명:

1. **클러스터 엔드포인트 액세스 제한**:
   - 퍼블릭 엔드포인트 접근을 특정 IP 범위로 제한하거나 완전히 비활성화합니다.
   - 프라이빗 엔드포인트를 활성화하여 VPC 내에서 클러스터에 접근할 수 있도록 합니다.
   - 이를 통해 클러스터 API 서버에 대한 무단 접근을 방지합니다.

2. **Secrets 암호화 활성화**:
   - AWS KMS 키를 사용하여 etcd에 저장된 Kubernetes Secrets를 암호화합니다.
   - 저장 중인 민감한 데이터를 보호합니다.
   - 참고: 기존 클러스터에서는 암호화를 활성화할 수 없으므로, 새 클러스터를 생성해야 합니다.

3. **네트워크 정책 구현**:
   - Calico를 설치하여 Kubernetes 네트워크 정책을 지원합니다.
   - 기본 거부 정책을 적용하여 명시적으로 허용되지 않은 모든 트래픽을 차단합니다.
   - 필요한 통신만 허용하는 세분화된 정책을 구현합니다.

4. **Pod Security 표준 적용**:
   - Kubernetes 1.23 이상에서 제공하는 Pod Security 표준을 적용합니다.
   - 네임스페이스 수준에서 보안 제약 조건을 설정합니다.
   - Kyverno와 같은 정책 엔진을 사용하여 추가적인 보안 정책을 적용합니다.

5. **컨트롤 플레인 로깅 활성화**:
   - 모든 컨트롤 플레인 로그 유형을 CloudWatch Logs로 전송합니다.
   - 감사 로그를 통해 클러스터 활동을 모니터링합니다.
   - 보안 이벤트 및 문제 해결을 위한 로그를 유지합니다.

이 실습을 통해 EKS 클러스터의 보안을 강화하는 다양한 방법을 배웠습니다. 이러한 보안 조치는 클러스터의 보안 태세를 개선하고, 무단 접근 및 악의적인 활동으로부터 클러스터를 보호하는 데 도움이 됩니다.
</details>

## 고급 주제

다음은 Amazon EKS 클러스터 생성에 관한 고급 주제에 대한 질문입니다. 이 섹션은 EKS 클러스터 생성의 심화 개념과 모범 사례에 대한 이해를 테스트합니다.

1. Amazon EKS 클러스터에서 IPv6 지원을 구성하기 위한 요구 사항이 아닌 것은 무엇인가요?
   - A) IPv6 CIDR 블록이 할당된 VPC
   - B) IPv6 지원 CNI 플러그인 버전
   - C) 듀얼 스택 서브넷
   - D) IPv6 전용 인스턴스 유형
   
<details>
<summary>정답 보기</summary>

**정답: D) IPv6 전용 인스턴스 유형**

**설명:**
"IPv6 전용 인스턴스 유형"은 Amazon EKS 클러스터에서 IPv6 지원을 구성하기 위한 요구 사항이 아닙니다. IPv6를 지원하는 특별한 인스턴스 유형은 필요하지 않으며, 대부분의 EC2 인스턴스 유형은 IPv6를 지원합니다. 실제 요구 사항은 IPv6 CIDR 블록이 할당된 VPC, IPv6 지원 CNI 플러그인 버전, 그리고 듀얼 스택 서브넷입니다.

#### EKS에서 IPv6 지원을 위한 실제 요구 사항:

1. **IPv6 CIDR 블록이 할당된 VPC**:
   - VPC에 IPv6 CIDR 블록을 할당해야 합니다.
   - AWS Management Console 또는 AWS CLI를 통해 구성할 수 있습니다.
   ```bash
   # 기존 VPC에 IPv6 CIDR 블록 할당
   aws ec2 associate-vpc-cidr-block \
     --vpc-id vpc-12345 \
     --amazon-provided-ipv6-cidr-block
   ```

2. **IPv6 지원 CNI 플러그인 버전**:
   - Amazon VPC CNI 플러그인 버전 1.10.0 이상이 필요합니다.
   - IPv6 지원을 위한 구성이 필요합니다.
   ```bash
   # CNI 버전 확인
   kubectl describe daemonset aws-node --namespace kube-system | grep Image
   
   # CNI 업데이트
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
   
   # IPv6 활성화
   kubectl set env daemonset aws-node -n kube-system ENABLE_IPV6=true
   ```

3. **듀얼 스택 서브넷**:
   - 서브넷에 IPv4 및 IPv6 CIDR 블록이 모두 할당되어야 합니다.
   - 라우팅 테이블에 IPv6 라우팅이 구성되어야 합니다.
   ```bash
   # 서브넷에 IPv6 CIDR 블록 할당
   aws ec2 associate-subnet-cidr-block \
     --subnet-id subnet-12345 \
     --ipv6-cidr-block 2600:1f16:d93:e900::/64
   
   # IPv6 인터넷 게이트웨이 생성
   aws ec2 create-egress-only-internet-gateway --vpc-id vpc-12345
   ```

#### EKS IPv6 클러스터 생성:

```bash
# eksctl을 사용한 IPv6 클러스터 생성
cat > ipv6-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-cluster
  region: us-west-2
  version: '1.23'
vpc:
  id: vpc-12345
  subnets:
    private:
      us-west-2a:
        id: subnet-12345
      us-west-2b:
        id: subnet-67890
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
kubernetesNetworkConfig:
  ipFamily: IPv6
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
EOF

eksctl create cluster -f ipv6-cluster.yaml
```

#### IPv6 클러스터 구성 확인:

```bash
# 클러스터 정보 확인
aws eks describe-cluster --name ipv6-cluster --query "cluster.kubernetesNetworkConfig"

# 포드 IP 할당 확인
kubectl get pods -o wide

# 서비스 IP 할당 확인
kubectl get services -o wide
```

#### IPv6 클러스터의 특징:

1. **포드 IP 할당**:
   - 포드는 IPv6 주소만 할당받습니다.
   - 클러스터 내부 통신은 IPv6를 통해 이루어집니다.

2. **서비스 IP 할당**:
   - 클러스터 IP 서비스는 IPv6 주소를 사용합니다.
   - 기본 서비스 CIDR은 fd00::/108입니다.

3. **DNS 구성**:
   - CoreDNS는 IPv6 주소로 구성됩니다.
   - AAAA 레코드를 통해 서비스 이름 확인이 가능합니다.

4. **외부 통신**:
   - 인터넷 통신을 위해 이그레스 전용 인터넷 게이트웨이(Egress-Only Internet Gateway)가 필요합니다.
   - 인바운드 통신을 위해서는 IPv6 지원 로드 밸런서가 필요합니다.

#### IPv6 사용의 이점:

1. **IP 주소 고갈 문제 해결**:
   - IPv4 주소 공간의 제한을 극복합니다.
   - 대규모 클러스터에서 IP 주소 부족 문제를 해결합니다.

2. **단순화된 네트워킹**:
   - NAT가 필요 없어 네트워크 구성이 단순해집니다.
   - 직접 라우팅이 가능해 네트워크 성능이 향상될 수 있습니다.

3. **미래 호환성**:
   - IPv6 전용 환경으로의 전환을 준비합니다.
   - 새로운 네트워킹 기능 및 최적화를 활용할 수 있습니다.

"IPv6 전용 인스턴스 유형"은 존재하지 않는 개념이며, 대부분의 EC2 인스턴스 유형은 IPv6를 지원합니다. EKS에서 IPv6를 구성하기 위해 특별한 인스턴스 유형을 선택할 필요는 없습니다.
</details>
2. Amazon EKS 클러스터에서 사용자 지정 네트워킹을 구성하는 주요 이점은 무엇인가요?
   - A) 포드 IP 주소 범위를 VPC CIDR과 분리하여 IP 주소 충돌 방지
   - B) 클러스터 생성 시간 단축
   - C) 컨트롤 플레인 성능 향상
   - D) 노드 간 통신 암호화
   
<details>
<summary>정답 보기</summary>

**정답: A) 포드 IP 주소 범위를 VPC CIDR과 분리하여 IP 주소 충돌 방지**

**설명:**
Amazon EKS 클러스터에서 사용자 지정 네트워킹을 구성하는 주요 이점은 포드 IP 주소 범위를 VPC CIDR과 분리하여 IP 주소 충돌을 방지하는 것입니다. 이 기능을 통해 기존 네트워크 인프라와의 통합이 용이해지고, 대규모 클러스터에서 IP 주소 관리가 더 효율적으로 이루어질 수 있습니다.

#### 사용자 지정 네트워킹의 작동 방식:

기본적으로 Amazon VPC CNI 플러그인은 노드의 기본 네트워크 인터페이스에서 보조 IP 주소를 할당하여 포드에 IP 주소를 제공합니다. 이 방식에서는 포드 IP 주소가 VPC CIDR 범위 내에서 할당됩니다. 반면, 사용자 지정 네트워킹을 사용하면 VPC CIDR과 별도의 CIDR 블록에서 포드 IP 주소를 할당할 수 있습니다.

#### 사용자 지정 네트워킹 구성 단계:

1. **사용자 지정 네트워킹 활성화**:
   ```bash
   # CNI 플러그인 구성 수정
   kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
   ```

2. **ENIConfig 리소스 생성**:
   ```yaml
   # 각 가용 영역에 대한 ENIConfig 생성
   apiVersion: crd.k8s.amazonaws.com/v1alpha1
   kind: ENIConfig
   metadata:
     name: us-west-2a
   spec:
     subnet: subnet-12345
     securityGroups:
     - sg-12345
   ---
   apiVersion: crd.k8s.amazonaws.com/v1alpha1
   kind: ENIConfig
   metadata:
     name: us-west-2b
   spec:
     subnet: subnet-67890
     securityGroups:
     - sg-12345
   ```

3. **가용 영역 기반 ENIConfig 사용 활성화**:
   ```bash
   kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
   ```

4. **노드 레이블 확인**:
   ```bash
   kubectl get nodes --show-labels | grep topology.kubernetes.io/zone
   ```

#### 사용자 지정 네트워킹의 이점:

1. **IP 주소 충돌 방지**:
   - 포드 IP 주소 범위를 VPC CIDR과 분리하여 IP 주소 충돌을 방지합니다.
   - 기존 네트워크 인프라와의 통합이 용이해집니다.
   - 온프레미스 네트워크와 VPC 간의 피어링 또는 VPN 연결 시 유용합니다.

2. **IP 주소 관리 유연성**:
   - 포드 IP 주소 범위를 별도로 계획하고 관리할 수 있습니다.
   - 대규모 클러스터에서 IP 주소 관리가 더 효율적으로 이루어집니다.

3. **네트워크 세분화**:
   - 포드를 특정 서브넷에 배치하여 네트워크 세분화를 구현할 수 있습니다.
   - 보안 그룹을 통한 네트워크 액세스 제어가 가능합니다.

4. **다중 CIDR 지원**:
   - 여러 CIDR 블록을 사용하여 IP 주소 공간을 확장할 수 있습니다.
   - 기존 VPC CIDR이 제한된 경우에도 대규모 클러스터를 구축할 수 있습니다.

#### 사용자 지정 네트워킹 사용 사례:

1. **하이브리드 네트워크 환경**:
   - 온프레미스 네트워크와 AWS VPC 간의 연결이 있는 경우
   - IP 주소 공간이 중복되는 것을 방지해야 하는 경우

2. **대규모 클러스터**:
   - 많은 수의 포드를 실행해야 하는 경우
   - VPC CIDR 범위가 제한된 경우

3. **멀티테넌트 환경**:
   - 테넌트별로 별도의 서브넷을 사용해야 하는 경우
   - 네트워크 격리가 필요한 경우

4. **규제 요구 사항**:
   - 특정 워크로드를 특정 서브넷에 배치해야 하는 규제 요구 사항이 있는 경우

#### 다른 옵션들의 문제점:

- **클러스터 생성 시간 단축**: 사용자 지정 네트워킹은 클러스터 생성 시간에 영향을 미치지 않으며, 오히려 추가 구성으로 인해 설정 시간이 더 길어질 수 있습니다.

- **컨트롤 플레인 성능 향상**: 사용자 지정 네트워킹은 데이터 플레인(워커 노드 및 포드)의 네트워킹에만 영향을 미치며, 컨트롤 플레인 성능에는 직접적인 영향을 미치지 않습니다.

- **노드 간 통신 암호화**: 사용자 지정 네트워킹은 IP 주소 할당 방식을 변경할 뿐, 노드 간 통신 암호화와는 관련이 없습니다. 노드 간 통신 암호화는 별도의 보안 메커니즘(예: Calico, Cilium의 암호화 기능)을 통해 구현해야 합니다.

사용자 지정 네트워킹은 EKS 클러스터의 네트워킹을 더 유연하게 구성할 수 있게 해주는 강력한 기능이지만, 구성이 복잡하고 추가적인 관리 오버헤드가 발생할 수 있으므로 실제 필요한 경우에만 사용하는 것이 좋습니다.
</details>
3. Amazon EKS 클러스터에서 Windows 워커 노드를 지원하기 위한 요구 사항이 아닌 것은 무엇인가요?
   - A) Amazon Linux 기반 관리 노드 그룹이 최소 2개 이상 필요
   - B) VPC-CNI, kube-proxy, CoreDNS 애드온 설치
   - C) Windows 서버 2019 이상 AMI 사용
   - D) 클러스터 버전 1.14 이상
   
<details>
<summary>정답 보기</summary>

**정답: A) Amazon Linux 기반 관리 노드 그룹이 최소 2개 이상 필요**

**설명:**
Amazon EKS 클러스터에서 Windows 워커 노드를 지원하기 위해서는 Amazon Linux 기반 관리 노드 그룹이 최소 1개 이상 필요합니다(2개 이상이 아님). 이는 CoreDNS와 같은 필수 시스템 포드가 Linux 노드에서 실행되어야 하기 때문입니다. 그러나 최소 2개 이상의 Linux 노드 그룹이 필요하다는 것은 정확하지 않습니다.

#### EKS에서 Windows 워커 노드 지원을 위한 실제 요구 사항:

1. **Linux 노드 그룹 필요**:
   - 클러스터에 최소 1개 이상의 Linux 노드가 필요합니다.
   - CoreDNS, VPC CNI 플러그인, kube-proxy와 같은 시스템 포드는 Linux 노드에서만 실행됩니다.
   ```bash
   # Linux 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name linux-ng \
     --node-type m5.large \
     --nodes 2
   ```

2. **VPC-CNI, kube-proxy, CoreDNS 애드온 설치**:
   - 이러한 애드온은 EKS 클러스터의 기본 구성 요소입니다.
   - Windows 노드 지원을 위해 특정 버전 이상이 필요할 수 있습니다.
   ```bash
   # 애드온 버전 확인
   aws eks describe-addon-versions \
     --addon-name vpc-cni \
     --kubernetes-version 1.23
   
   # 애드온 업데이트
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.4-eksbuild.1
   ```

3. **Windows 서버 2019 이상 AMI 사용**:
   - Windows 워커 노드는 Windows Server 2019 이상 AMI를 사용해야 합니다.
   - EKS 최적화 Windows AMI를 사용하는 것이 권장됩니다.
   ```bash
   # Windows 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name windows-ng \
     --node-type m5.large \
     --nodes 2 \
     --node-ami-family WindowsServer2019FullContainer
   ```

4. **클러스터 버전 1.14 이상**:
   - Windows 노드 지원은 Kubernetes 1.14부터 정식 지원되었습니다.
   - 최신 기능을 위해 더 높은 버전을 사용하는 것이 좋습니다.
   ```bash
   # 클러스터 버전 확인
   aws eks describe-cluster --name my-cluster --query "cluster.version"
   ```

#### Windows 지원 활성화 단계:

1. **Windows 지원 활성화**:
   ```bash
   # Windows 지원 활성화
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml
   
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
   ```

2. **Windows 노드 그룹 생성**:
   ```bash
   # eksctl을 사용한 Windows 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name windows-ng \
     --node-type m5.large \
     --nodes 2 \
     --node-ami-family WindowsServer2019FullContainer
   ```

3. **Windows 노드 확인**:
   ```bash
   # 노드 확인
   kubectl get nodes -o wide
   
   # Windows 노드 레이블 확인
   kubectl get nodes -l kubernetes.io/os=windows
   ```

#### Windows 컨테이너 배포 예시:

```yaml
# Windows 포드 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

#### Windows 노드 제한 사항:

1. **네트워킹 제한**:
   - Windows 노드는 HostPort 및 HostNetwork 모드를 지원하지 않습니다.
   - Windows 노드는 NodeLocal DNSCache를 지원하지 않습니다.

2. **스토리지 제한**:
   - Windows 노드는 일부 스토리지 드라이버만 지원합니다.
   - 호스트 경로 볼륨 마운트에 제한이 있습니다.

3. **컨테이너 런타임**:
   - Windows 노드는 containerd 런타임만 지원합니다.
   - Linux 컨테이너는 Windows 노드에서 실행할 수 없습니다.

4. **기능 제한**:
   - 일부 Kubernetes 기능은 Windows 노드에서 지원되지 않습니다.
   - 권한 있는 컨테이너, 프로세스 네임스페이스 공유 등의 제한이 있습니다.

EKS에서 Windows 워커 노드를 지원하기 위해서는 Linux 노드 그룹이 최소 1개 이상 필요하지만, 반드시 2개 이상의 Linux 노드 그룹이 필요한 것은 아닙니다. 따라서 "Amazon Linux 기반 관리 노드 그룹이 최소 2개 이상 필요"는 정확하지 않은 요구 사항입니다.
</details>
3. Amazon EKS 클러스터에서 Windows 워커 노드를 지원하기 위한 요구 사항이 아닌 것은 무엇인가요?
   - A) Amazon Linux 기반 관리 노드 그룹이 최소 2개 이상 필요
   - B) VPC-CNI, kube-proxy, CoreDNS 애드온 설치
   - C) Windows 서버 2019 이상 AMI 사용
   - D) 클러스터 버전 1.14 이상
   
<details>
<summary>정답 보기</summary>

**정답: A) Amazon Linux 기반 관리 노드 그룹이 최소 2개 이상 필요**

**설명:**
Amazon EKS 클러스터에서 Windows 워커 노드를 지원하기 위해서는 Amazon Linux 기반 관리 노드 그룹이 최소 1개 이상 필요합니다(2개 이상이 아님). 이는 CoreDNS와 같은 필수 시스템 포드가 Linux 노드에서 실행되어야 하기 때문입니다. 그러나 최소 2개 이상의 Linux 노드 그룹이 필요하다는 것은 정확하지 않습니다.

#### EKS에서 Windows 워커 노드 지원을 위한 실제 요구 사항:

1. **Linux 노드 그룹 필요**:
   - 클러스터에 최소 1개 이상의 Linux 노드가 필요합니다.
   - CoreDNS, VPC CNI 플러그인, kube-proxy와 같은 시스템 포드는 Linux 노드에서만 실행됩니다.
   ```bash
   # Linux 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name linux-ng \
     --node-type m5.large \
     --nodes 2
   ```

2. **VPC-CNI, kube-proxy, CoreDNS 애드온 설치**:
   - 이러한 애드온은 EKS 클러스터의 기본 구성 요소입니다.
   - Windows 노드 지원을 위해 특정 버전 이상이 필요할 수 있습니다.
   ```bash
   # 애드온 버전 확인
   aws eks describe-addon-versions \
     --addon-name vpc-cni \
     --kubernetes-version 1.23
   
   # 애드온 업데이트
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.4-eksbuild.1
   ```

3. **Windows 서버 2019 이상 AMI 사용**:
   - Windows 워커 노드는 Windows Server 2019 이상 AMI를 사용해야 합니다.
   - EKS 최적화 Windows AMI를 사용하는 것이 권장됩니다.
   ```bash
   # Windows 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name windows-ng \
     --node-type m5.large \
     --nodes 2 \
     --node-ami-family WindowsServer2019FullContainer
   ```

4. **클러스터 버전 1.14 이상**:
   - Windows 노드 지원은 Kubernetes 1.14부터 정식 지원되었습니다.
   - 최신 기능을 위해 더 높은 버전을 사용하는 것이 좋습니다.
   ```bash
   # 클러스터 버전 확인
   aws eks describe-cluster --name my-cluster --query "cluster.version"
   ```

#### Windows 지원 활성화 단계:

1. **Windows 지원 활성화**:
   ```bash
   # Windows 지원 활성화
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml
   
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
   ```

2. **Windows 노드 그룹 생성**:
   ```bash
   # eksctl을 사용한 Windows 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name windows-ng \
     --node-type m5.large \
     --nodes 2 \
     --node-ami-family WindowsServer2019FullContainer
   ```

3. **Windows 노드 확인**:
   ```bash
   # 노드 확인
   kubectl get nodes -o wide
   
   # Windows 노드 레이블 확인
   kubectl get nodes -l kubernetes.io/os=windows
   ```

#### Windows 컨테이너 배포 예시:

```yaml
# Windows 포드 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

#### Windows 노드 제한 사항:

1. **네트워킹 제한**:
   - Windows 노드는 HostPort 및 HostNetwork 모드를 지원하지 않습니다.
   - Windows 노드는 NodeLocal DNSCache를 지원하지 않습니다.

2. **스토리지 제한**:
   - Windows 노드는 일부 스토리지 드라이버만 지원합니다.
   - 호스트 경로 볼륨 마운트에 제한이 있습니다.

3. **컨테이너 런타임**:
   - Windows 노드는 containerd 런타임만 지원합니다.
   - Linux 컨테이너는 Windows 노드에서 실행할 수 없습니다.

4. **기능 제한**:
   - 일부 Kubernetes 기능은 Windows 노드에서 지원되지 않습니다.
   - 권한 있는 컨테이너, 프로세스 네임스페이스 공유 등의 제한이 있습니다.

EKS에서 Windows 워커 노드를 지원하기 위해서는 Linux 노드 그룹이 최소 1개 이상 필요하지만, 반드시 2개 이상의 Linux 노드 그룹이 필요한 것은 아닙니다. 따라서 "Amazon Linux 기반 관리 노드 그룹이 최소 2개 이상 필요"는 정확하지 않은 요구 사항입니다.
</details>

4. Amazon EKS 클러스터에서 노드 그룹의 인스턴스 메타데이터 서비스(IMDS)를 보호하는 가장 효과적인 방법은 무엇인가요?
   - A) IMDSv1 비활성화 및 IMDSv2 필수 설정
   - B) 보안 그룹 규칙으로 169.254.169.254 접근 제한
   - C) 노드 IAM 역할에 제한적 권한 설정
   - D) 포드 서비스 계정에 IAM 역할 연결
   
<details>
<summary>정답 보기</summary>

**정답: A) IMDSv1 비활성화 및 IMDSv2 필수 설정**

**설명:**
Amazon EKS 클러스터에서 노드 그룹의 인스턴스 메타데이터 서비스(IMDS)를 보호하는 가장 효과적인 방법은 IMDSv1을 비활성화하고 IMDSv2를 필수로 설정하는 것입니다. IMDSv2는 세션 기반 요청을 사용하여 서버 측 요청 위조(SSRF) 및 유사한 취약점으로부터 보호하는 향상된 보안 기능을 제공합니다.

#### IMDS 보안의 중요성:

인스턴스 메타데이터 서비스는 EC2 인스턴스에 대한 중요한 정보(IAM 역할 자격 증명 포함)를 제공합니다. 이 서비스에 대한 무단 접근은 권한 상승 및 보안 침해로 이어질 수 있습니다. 특히 Kubernetes 환경에서는 포드가 노드의 IMDS에 접근할 수 있어 보안 위험이 증가합니다.

#### IMDSv2 구성 방법:

1. **시작 템플릿을 사용한 IMDSv2 구성**:
   ```bash
   # 시작 템플릿 생성
   aws ec2 create-launch-template \
     --launch-template-name eks-imdsv2-template \
     --version-description "IMDSv2 required" \
     --launch-template-data '{
       "MetadataOptions": {
         "HttpTokens": "required",
         "HttpPutResponseHopLimit": 1,
         "HttpEndpoint": "enabled"
       }
     }'
   
   # 시작 템플릿을 사용한 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name ng-imdsv2 \
     --node-type m5.large \
     --nodes 3 \
     --launch-template-name eks-imdsv2-template \
     --launch-template-version 1
   ```

2. **eksctl 구성 파일을 사용한 IMDSv2 구성**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
     - name: ng-imdsv2
       instanceType: m5.large
       minSize: 2
       maxSize: 5
       disableIMDSv1: true
       metadataOptions:
         httpTokens: required
         httpPutResponseHopLimit: 1
   ```

3. **기존 노드 그룹 수정**:
   기존 노드 그룹의 IMDS 설정을 변경하려면 새 노드 그룹을 생성하고 워크로드를 마이그레이션해야 합니다. 기존 EC2 인스턴스의 IMDS 설정은 다음과 같이 수정할 수 있습니다:
   ```bash
   aws ec2 modify-instance-metadata-options \
     --instance-id i-1234567890abcdef0 \
     --http-tokens required \
     --http-put-response-hop-limit 1 \
     --http-endpoint enabled
   ```

#### IMDSv2의 보안 이점:

1. **세션 기반 인증**:
   - IMDSv2는 PUT 요청을 통해 생성된 토큰을 사용하여 후속 요청을 인증합니다.
   - 이 토큰은 제한된 시간 동안만 유효합니다.

2. **SSRF 공격 방지**:
   - 서버 측 요청 위조(SSRF) 취약점을 통한 메타데이터 접근을 방지합니다.
   - 토큰 없이는 메타데이터에 접근할 수 없습니다.

3. **홉 제한 설정**:
   - HTTP PUT 응답 홉 제한을 설정하여 메타데이터 요청이 인스턴스 외부로 리디렉션되는 것을 방지합니다.
   - 기본값은 1로, 인스턴스 내에서만 요청이 처리되도록 합니다.

#### 추가 IMDS 보안 조치:

1. **IMDS 완전 비활성화**:
   특정 워크로드에서 IMDS가 필요하지 않은 경우 완전히 비활성화할 수 있습니다:
   ```yaml
   metadataOptions:
     httpEndpoint: disabled
   ```

2. **포드의 IMDS 접근 차단**:
   포드가 호스트 네트워크를 사용하지 않는 경우, 다음과 같이 iptables 규칙을 추가하여 IMDS 접근을 차단할 수 있습니다:
   ```bash
   iptables -t nat -A PREROUTING -d 169.254.169.254/32 -i eth0 -p tcp -m tcp --dport 80 -j DNAT --to-destination 127.0.0.1:1
   ```

3. **IRSA 사용**:
   IAM Roles for Service Accounts(IRSA)를 사용하여 포드에 필요한 AWS 권한을 제공하고, 노드 IMDS에 대한 의존성을 제거합니다.

#### 다른 옵션들의 문제점:

- **보안 그룹 규칙으로 169.254.169.254 접근 제한**: 보안 그룹은 인스턴스 외부에서 들어오는 트래픽을 제어하지만, IMDS는 인스턴스 내부에서 접근되므로 보안 그룹으로 제한할 수 없습니다.

- **노드 IAM 역할에 제한적 권한 설정**: 이는 좋은 보안 관행이지만, IMDS 자체의 보안을 강화하지는 않습니다. 공격자가 IMDS에 접근할 수 있다면 제한된 권한이라도 악용할 수 있습니다.

- **포드 서비스 계정에 IAM 역할 연결**: IRSA는 포드가 노드 IMDS에 의존하지 않도록 하는 좋은 방법이지만, 노드 IMDS 자체의 보안을 직접적으로 강화하지는 않습니다.

IMDSv1을 비활성화하고 IMDSv2를 필수로 설정하는 것은 EKS 노드의 메타데이터 서비스를 보호하는 가장 효과적인 방법입니다. 이는 AWS 보안 모범 사례이며, 특히 멀티테넌트 Kubernetes 환경에서 중요합니다.
</details>

5. Amazon EKS 클러스터에서 노드 그룹 생성 시 부트스트랩 스크립트를 사용자 지정하는 주요 목적이 아닌 것은 무엇인가요?
   - A) 클러스터 컨트롤 플레인 구성 요소 수정
   - B) 추가 소프트웨어 설치
   - C) 커널 파라미터 조정
   - D) 노드 레이블 및 테인트 설정
   
<details>
<summary>정답 보기</summary>

**정답: A) 클러스터 컨트롤 플레인 구성 요소 수정**

**설명:**
Amazon EKS 클러스터에서 노드 그룹 생성 시 부트스트랩 스크립트를 사용자 지정하는 주요 목적은 클러스터 컨트롤 플레인 구성 요소를 수정하는 것이 아닙니다. EKS는 관리형 서비스로, 컨트롤 플레인은 AWS에서 관리하며 사용자가 직접 수정할 수 없습니다. 부트스트랩 스크립트는 워커 노드의 구성만 수정할 수 있습니다.

#### 부트스트랩 스크립트의 실제 사용 목적:

1. **추가 소프트웨어 설치**:
   - 모니터링 에이전트(CloudWatch Agent, Prometheus Node Exporter 등)
   - 로깅 도구(Fluentd, Fluent Bit 등)
   - 보안 도구(Falco, Sysdig 등)
   - 성능 최적화 도구
   ```bash
   #!/bin/bash
   # CloudWatch 에이전트 설치
   wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
   rpm -U amazon-cloudwatch-agent.rpm
   
   # 구성 파일 생성
   cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
   {
     "metrics": {
       "metrics_collected": {
         "mem": {
           "measurement": ["mem_used_percent"]
         },
         "swap": {
           "measurement": ["swap_used_percent"]
         }
       }
     }
   }
   EOF
   
   # 에이전트 시작
   /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s
   ```

2. **커널 파라미터 조정**:
   - 네트워크 설정 최적화
   - 메모리 관리 설정
   - 파일 시스템 및 I/O 설정
   ```bash
   #!/bin/bash
   # 커널 파라미터 조정
   cat > /etc/sysctl.d/99-kubernetes.conf << EOF
   net.ipv4.ip_forward = 1
   net.bridge.bridge-nf-call-iptables = 1
   net.ipv4.tcp_keepalive_time = 600
   net.ipv4.tcp_max_syn_backlog = 40000
   net.core.somaxconn = 40000
   net.core.netdev_max_backlog = 40000
   vm.max_map_count = 262144
   EOF
   
   # 변경 사항 적용
   sysctl --system
   ```

3. **노드 레이블 및 테인트 설정**:
   - 노드 역할 레이블 설정
   - 하드웨어 특성 레이블 설정
   - 특정 워크로드를 위한 테인트 설정
   ```bash
   #!/bin/bash
   # EKS 부트스트랩 스크립트 실행
   /etc/eks/bootstrap.sh my-cluster \
     --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker,environment=prod,node-type=compute --register-with-taints=dedicated=compute:NoSchedule'
   ```

4. **디스크 및 파일 시스템 구성**:
   - 추가 볼륨 마운트
   - 파일 시스템 최적화
   - 임시 스토리지 구성
   ```bash
   #!/bin/bash
   # 추가 EBS 볼륨 포맷 및 마운트
   mkfs -t xfs /dev/nvme1n1
   mkdir -p /data
   mount /dev/nvme1n1 /data
   echo "/dev/nvme1n1 /data xfs defaults 0 0" >> /etc/fstab
   ```

5. **보안 구성**:
   - 방화벽 규칙 설정
   - 보안 강화 설정
   - 로그 감사 구성
   ```bash
   #!/bin/bash
   # 방화벽 규칙 설정
   iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
   iptables -A INPUT -p tcp --dport 22 -j DROP
   
   # 보안 강화 설정
   sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
   systemctl restart sshd
   ```

#### 부트스트랩 스크립트 구현 방법:

1. **시작 템플릿을 사용한 사용자 데이터 스크립트**:
   ```bash
   # 시작 템플릿 생성
   aws ec2 create-launch-template \
     --launch-template-name eks-custom-bootstrap \
     --version-description "Custom bootstrap script" \
     --launch-template-data '{
       "UserData": "BASE64_ENCODED_USER_DATA_SCRIPT"
     }'
   
   # 시작 템플릿을 사용한 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name custom-ng \
     --node-type m5.large \
     --nodes 3 \
     --launch-template-name eks-custom-bootstrap \
     --launch-template-version 1
   ```

2. **eksctl 구성 파일을 사용한 사용자 데이터 스크립트**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
     - name: custom-ng
       instanceType: m5.large
       minSize: 2
       maxSize: 5
       preBootstrapCommands:
         - "echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.d/99-kubernetes.conf"
         - "sysctl --system"
       kubeletExtraArgs:
         node-labels: "environment=prod,node-type=compute"
   ```

#### 클러스터 컨트롤 플레인 구성 요소:

EKS 클러스터의 컨트롤 플레인 구성 요소는 AWS에서 관리하며, 부트스트랩 스크립트를 통해 수정할 수 없습니다:

- API 서버
- 컨트롤러 관리자
- 스케줄러
- etcd
- CoreDNS

이러한 구성 요소를 수정하려면 AWS에서 제공하는 API를 통해 클러스터 수준에서 구성해야 합니다. 예를 들어, 컨트롤 플레인 로깅은 다음과 같이 구성할 수 있습니다:

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

부트스트랩 스크립트는 워커 노드의 구성만 수정할 수 있으며, 클러스터 컨트롤 플레인 구성 요소를 수정할 수 없습니다. 따라서 "클러스터 컨트롤 플레인 구성 요소 수정"은 부트스트랩 스크립트의 주요 목적이 아닙니다.
</details>
