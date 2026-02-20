# EKS Hybrid Nodes 노드 부트스트래핑 퀴즈

> **관련 문서**: [노드 부트스트래핑](../../eks-hybrid-nodes/04-node-bootstrap.md)

## 객관식 문제

### 1. nodeadm의 주요 역할은 무엇인가요?

A. EKS 클러스터 생성
B. 노드의 kubelet, containerd 등 구성 요소 설치 및 부트스트래핑
C. Pod 스케줄링 결정
D. 클러스터 네트워크 정책 관리

<details>
<summary>정답 보기</summary>

**정답: B. 노드의 kubelet, containerd 등 구성 요소 설치 및 부트스트래핑**

**설명:**
nodeadm은 EKS 노드 부트스트래핑을 위한 공식 도구로, kubelet, containerd, aws-iam-authenticator 등 필요한 구성 요소를 설치하고 구성합니다.

```bash
# nodeadm 설치
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# nodeadm으로 노드 초기화
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

**nodeadm 기능:**
- Kubernetes 구성 요소 설치 (kubelet, containerd)
- AWS IAM Authenticator 구성
- kubelet 인증서 부트스트래핑
- 노드 레이블 및 taints 설정

</details>

### 2. nodeadm을 사용하여 Hybrid Node를 초기화할 때 반드시 제공해야 하는 3가지 클러스터 정보는 무엇인가요?

A. 클러스터 이름, VPC ID, 서브넷 ID
B. 클러스터 이름, API 서버 엔드포인트, CA 인증서
C. 클러스터 이름, IAM 역할, 보안 그룹
D. 클러스터 이름, 리전, 가용 영역

<details>
<summary>정답 보기</summary>

**정답: B. 클러스터 이름, API 서버 엔드포인트, CA 인증서**

**설명:**
nodeadm 설정 파일에서 필수 항목:

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster                    # 필수 1
    region: ap-northeast-2
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com  # 필수 2
    certificateAuthority: LS0tLS1CRUdJTi...             # 필수 3
```

```bash
# EKS에서 필수 정보 가져오기
aws eks describe-cluster --name my-cluster \
  --query "cluster.{name:name,endpoint:endpoint,ca:certificateAuthority.data}" \
  --output json
```

</details>

### 3. EKS Hybrid Nodes에서 IAM 인증에 사용되는 방식은?

A. 정적 토큰
B. x509 인증서만
C. IAM Roles Anywhere 또는 IAM 사용자 자격 증명
D. LDAP 인증

<details>
<summary>정답 보기</summary>

**정답: C. IAM Roles Anywhere 또는 IAM 사용자 자격 증명**

**설명:**
EKS Hybrid Nodes는 온프레미스에서 AWS IAM 인증이 필요합니다. IAM Roles Anywhere를 사용하면 온프레미스 서버에서도 IAM 역할을 사용할 수 있습니다.

```bash
# IAM Roles Anywhere Trust Anchor 생성
aws rolesanywhere create-trust-anchor \
  --name hybrid-nodes-anchor \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CERT_DATA}"

# IAM Roles Anywhere Profile 생성
aws rolesanywhere create-profile \
  --name hybrid-node-profile \
  --role-arns arn:aws:iam::123456789012:role/HybridNodeRole \
  --duration-seconds 3600
```

```yaml
# nodeadm 설정에서 IAM Roles Anywhere 사용
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  iam:
    mode: rolesAnywhere
    rolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/HybridNodeRole
```

</details>

### 4. NodeConfig에서 kubelet 설정 시 사용할 수 있는 옵션이 아닌 것은?

A. maxPods
B. clusterDNS
C. clusterCIDR
D. podScheduler

<details>
<summary>정답 보기</summary>

**정답: D. podScheduler**

**설명:**
`podScheduler`는 NodeConfig의 kubelet 설정 옵션이 아닙니다. 스케줄링은 컨트롤 플레인의 kube-scheduler가 담당합니다.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      maxPods: 110              # 노드당 최대 Pod 수
      clusterDNS:               # 클러스터 DNS 서버
        - 10.100.0.10
      clusterDomain: cluster.local
      evictionHard:             # 리소스 부족 시 Pod 퇴거 임계값
        memory.available: "100Mi"
        nodefs.available: "10%"
    flags:
      - "--node-labels=location=onprem"
      - "--register-with-taints=dedicated=hybrid:NoSchedule"
```

</details>

### 5. SSM(Systems Manager)을 사용하여 Hybrid Node를 등록할 때 필요한 구성 요소는?

A. SSM Agent와 활성화 코드
B. CloudWatch Agent만
C. AWS CLI만
D. EC2 인스턴스 프로파일

<details>
<summary>정답 보기</summary>

**정답: A. SSM Agent와 활성화 코드**

**설명:**
온프레미스 서버를 SSM으로 관리하려면 SSM Agent를 설치하고 하이브리드 활성화를 통해 등록해야 합니다.

```bash
# 1. SSM 하이브리드 활성화 생성 (AWS 콘솔 또는 CLI)
aws ssm create-activation \
  --default-instance-name "hybrid-node" \
  --iam-role service-role/AmazonEC2RunCommandRoleForManagedInstances \
  --registration-limit 10

# 출력: ActivationId, ActivationCode

# 2. 온프레미스 서버에서 SSM Agent 설치 및 등록
sudo amazon-ssm-agent -register \
  -code "activation-code" \
  -id "activation-id" \
  -region "ap-northeast-2"

# 3. SSM Agent 시작
sudo systemctl start amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
```

```yaml
# nodeadm에서 SSM 모드 사용
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  hybrid:
    ssm: true
    ssmActivationId: "activation-id"
    ssmActivationCode: "activation-code"
```

</details>

### 6. CA 인증서를 nodeadm 설정에 제공하는 목적은?

A. 노드 간 트래픽 암호화
B. kubelet이 API 서버의 신뢰성을 검증
C. Pod 간 mTLS 구성
D. Harbor 레지스트리 인증

<details>
<summary>정답 보기</summary>

**정답: B. kubelet이 API 서버의 신뢰성을 검증**

**설명:**
CA(Certificate Authority) 인증서는 kubelet이 EKS API 서버에 연결할 때 서버의 신뢰성을 검증하는 데 사용됩니다.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com
    certificateAuthority: |
      LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUM...
      # Base64 인코딩된 CA 인증서
```

**인증서 흐름:**
```
kubelet ----TLS 연결----> EKS API Server
   |                          |
   |-- CA로 서버 인증서 검증 --|
   |                          |
   |<-- 클라이언트 인증서 발급 -|
```

```bash
# EKS 클러스터에서 CA 인증서 가져오기
aws eks describe-cluster --name my-cluster \
  --query "cluster.certificateAuthority.data" \
  --output text | base64 -d > ca.crt

# CA 인증서 내용 확인
openssl x509 -in ca.crt -text -noout
```

</details>

### 7. nodeadm init 명령 실행 후 노드가 클러스터에 조인되지 않는 경우, 가장 먼저 확인해야 할 항목은?

A. Pod 배포 상태
B. kubelet 로그 및 네트워크 연결
C. Deployment 설정
D. ConfigMap 내용

<details>
<summary>정답 보기</summary>

**정답: B. kubelet 로그 및 네트워크 연결**

**설명:**
노드 조인 실패 시 kubelet 로그와 네트워크 연결 상태를 먼저 확인해야 합니다.

```bash
# 1. kubelet 서비스 상태 확인
sudo systemctl status kubelet

# 2. kubelet 로그 확인
sudo journalctl -u kubelet -f

# 3. 네트워크 연결 테스트
curl -vk https://<eks-api-endpoint>:443

# 4. DNS 해결 확인
nslookup <eks-api-endpoint>

# 5. 방화벽 규칙 확인
sudo iptables -L -n | grep 443

# 6. nodeadm 상태 확인
sudo nodeadm status
```

**일반적인 실패 원인:**
- API 서버 엔드포인트 접근 불가 (방화벽)
- CA 인증서 불일치
- IAM 인증 실패
- DNS 해결 실패
- 시간 동기화 문제 (NTP)

</details>

