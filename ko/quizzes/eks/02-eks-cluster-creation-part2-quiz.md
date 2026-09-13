# EKS 클러스터 생성 퀴즈 - Part 2

> **마지막 업데이트**: 2026년 9월 11일

> 문항별 예제는 독립된 대안입니다. Part 1 사전 준비와 명시적으로 선택한 교육용 계정·클러스터를 사용합니다. 각 실습 안에서는 같은 Bash 세션에서 순서대로 진행합니다. 아래 클라우드·호스트 명령은 검토했지만 이 감사에서 실제 AWS·노드를 대상으로 실행하지 않았습니다.

이 퀴즈는 Amazon EKS 클러스터 생성과 관련된 고급 개념, 보안 설정, 네트워킹 구성에 대한 이해를 테스트합니다. 클러스터 보안, 네트워크 정책, 서비스 계정 등의 주제를 다룹니다.

## 기본 개념 문제

1. EKS 클러스터에서 IRSA의 주요 목적은 무엇인가요?
   * A) Kubernetes 관리자 접근 부여
   * B) EC2 노드 IAM 역할 할당
   * C) Kubernetes 서비스 계정을 통해 워크로드에 임시 AWS 권한 부여
   * D) EKS 컨트롤 플레인 역할 수정

<details>
<summary>정답 보기</summary>

**정답: C) Kubernetes 서비스 계정을 통해 워크로드에 임시 AWS 권한 부여**

IRSA는 워크로드가 Kubernetes 서비스 계정의 자격 증명을 이용해 임시 AWS 자격 증명을 얻도록 합니다. 허용되는 AWS 작업은 IAM 역할의 권한 정책으로 정합니다. 이는 Kubernetes RBAC, EKS 컨트롤 플레인 역할, EC2 노드 역할과 별개입니다.

**신뢰 흐름:** EKS가 projected 서비스 계정 토큰을 발급합니다. 실제 클러스터 OIDC 발급자를 IAM OIDC 공급자로 등록하고 대상 audience와 네임스페이스·서비스 계정 subject를 신뢰하도록 구성합니다. 지원되는 AWS SDK의 기본 자격 증명 체인이 토큰을 STS `AssumeRoleWithWebIdentity`로 교환합니다. 다음 예제의 공급자 ARN·발급자·서비스 계정은 실제 값으로 바꿉니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:irsa-lab:my-service-account"
      }
    }
  }]
}
```

서비스 계정에 역할 ARN을 주석으로 지정하고 포드에서 그 계정을 참조합니다. 먼저 사용하지 않는 `irsa-lab` 네임스페이스를 만듭니다. 다음 두 매니페스트와 아래 eksctl 서비스 계정 생성은 대안이며 다른 애플리케이션의 서비스 계정을 덮어쓰지 않습니다:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: irsa-lab
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ReviewedIrsaRole
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: irsa-identity-check
  namespace: irsa-lab
spec:
  serviceAccountName: my-service-account
  restartPolicy: Never
  containers:
    - name: aws-cli
      image: public.ecr.aws/aws-cli/aws-cli:2.36.43
      command: ["aws"]
      args: ["sts", "get-caller-identity"]
```

포드는 확인된 AWS CLI v2 이미지 태그로 호출자 신원을 출력하며 비밀 액세스 키나 web-identity 토큰은 출력하지 않습니다. 반환된 역할이 의도한 워크로드 역할인지 확인합니다. STS 신원 조회 성공만으로 S3 등 대상 리소스 권한이 입증되지는 않습니다. 실습 1처럼 실제 필요한 작업을 별도로 시험합니다.

**eksctl 대안:** 단일 버킷 작업에 광범위한 AWS 관리형 S3 정책을 부여하는 대신 필요한 리소스·작업으로 제한한 정책을 사용합니다. 기존 서비스 계정과 역할의 소유권을 먼저 확인하고 `--override-existing-serviceaccounts`를 일반적인 해결책으로 추가하지 않습니다.

```bash
# For a new service account and dedicated role, with a reviewed scoped policy.
eksctl utils associate-iam-oidc-provider \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
KUBECONFIG="${EXAMPLE_KUBECONFIG:?}" eksctl create iamserviceaccount \
  --name "${IRSA_SERVICE_ACCOUNT:?}" --namespace "${IRSA_NAMESPACE:?}" \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --attach-policy-arn "${SCOPED_POLICY_ARN:?}" --approve
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get serviceaccount "$IRSA_SERVICE_ACCOUNT" -o yaml
```

**한계와 책임:**

- 지원되는 SDK와 자격 증명 체인을 사용합니다. 하드코딩한 자격 증명이나 체인에서 우선하는 공급자가 IRSA보다 먼저 선택될 수 있습니다. 웹훅이 역할·토큰 파일 설정을 주입하고 SDK가 임시 자격 증명을 갱신합니다. 토큰·자격 증명 값을 출력하거나 복사하지 않습니다.
- IRSA 자체는 노드 IMDS 접근을 차단하지 않으며 같은 노드를 공유하는 컨테이너가 강한 보안 경계는 아닙니다. IMDS와 노드 권한을 별도로 제한합니다. `hostNetwork` 포드는 IMDS에 접근할 수 있습니다.
- IAM 조건은 역할 수임 범위를 제한하지만 그 서비스 계정으로 포드를 만들 수 있는 주체는 해당 AWS 권한을 얻을 수 있습니다. Kubernetes 워크로드·서비스 계정 관리 권한도 통제합니다.
- EKS Pod Identity는 별도 지원 조건이 있는 워크로드 자격 증명 대안입니다. EKS Auth·에이전트 흐름은 IRSA의 OIDC·STS 흐름과 다릅니다.
- 클러스터 사용자는 EKS 액세스 항목·정책 또는 구성된 기존 `aws-auth` 매핑으로 Kubernetes 접근 권한을 얻습니다. 이는 워크로드의 IAM 권한 정책을 대체하지 않습니다.

참고: [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html), [서비스 계정 역할 연결](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [SDK 요구사항](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html), [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html).

</details>

2. EKS 설계에서 AWS 보안 그룹은 무엇을 제어하나요?
   * A) Kubernetes 리소스 권한 부여
   * B) 연결된 인터페이스의 허용 네트워크 통신과 지원되는 포드 인터페이스 통신
   * C) 서비스 계정 토큰 audience
   * D) Deployment 복제본 수

<details>
<summary>정답 보기</summary>

**정답: B) 연결된 인터페이스의 허용 네트워크 통신과 지원되는 포드 인터페이스 통신**

보안 그룹은 네트워크 인터페이스에 연결되는 상태 저장 네트워크 필터입니다. EKS에서는 클러스터 인터페이스·노드 및 지원되는 Security Groups for Pods 기능으로 선택한 포드의 트래픽을 제어합니다. Kubernetes RBAC를 적용하거나 사용자를 인증하는 수단은 아닙니다.

**기본 규칙과 필수 규칙은 다릅니다.** EKS는 자체 참조 인바운드, 광범위한 아웃바운드, EFA에 사용하는 자체 참조 아웃바운드 규칙을 가진 `eks-cluster-sg-<cluster>-<id>`를 생성합니다. 이는 확인할 기본값이지 최소 권한 구성 예제가 아닙니다. EKS는 이 그룹을 클러스터 인터페이스와 일반적으로 관리형 노드 인터페이스에 연결하지만 시작 템플릿의 사용자 지정 보안 그룹을 사용하면 동작이 달라집니다.

기본 아웃바운드를 제한할 때는 문서화된 최소 통신과 실제 워크로드의 추가 의존성을 유지합니다:

| 필요한 클러스터 그룹 아웃바운드 | 대상 |
| --- | --- |
| TCP 443 | 클러스터 보안 그룹 |
| TCP 10250 | 클러스터 보안 그룹 |
| TCP·UDP 53 | 클러스터 보안 그룹 |

이 표만으로 네트워크 설계가 완성되지는 않습니다. 노드 간·애플리케이션 포트, API·레지스트리, S3, DNS 경로, IPv4·IPv6 규칙을 검토합니다. 프라이빗 엔드포인트로 일반 인터넷 송신 없이 AWS 서비스에 접근할 수도 있습니다. EKS가 클러스터 업데이트 때 자체 참조 규칙을 다시 만들 수 있으므로 삭제가 영구적인 제한이라고 설명하지 않습니다.

**추가 그룹:** 클러스터의 `resourcesVpcConfig.securityGroupIds`는 클러스터 네트워크 인터페이스에 적용되며 노드 그룹에 자동 적용되지 않습니다. 노드 시작 템플릿에 사용자 지정 보안 그룹을 지정하면 EKS가 클러스터 보안 그룹을 추가하지 않으므로 사용자 지정 그룹에서 필요한 노드·API 통신을 허용해야 합니다.

다음 AWS CLI 예제는 새 컨트롤 플레인에 추가 그룹을 지정하는 방법입니다. 노드 용량이나 운영자 액세스 항목을 만들지는 않습니다. 생성자의 자동 관리자 접근을 비활성화했으므로 프로비저닝 자격 증명에는 필요한 운영자 액세스 항목을 생성할 권한이 있어야 합니다:

```bash
# Cluster creation fragment: use reviewed roles/subnets/groups and a new name.
aws eks create-cluster --name "${NEW_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --kubernetes-version 1.36 \
  --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API,bootstrapClusterCreatorAdminPermissions=false \
  --resources-vpc-config "subnetIds=${PRIVATE_SUBNET_A:?},${PRIVATE_SUBNET_B:?},securityGroupIds=${ADDITIONAL_CONTROL_PLANE_SG:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"
```

동등한 eksctl 네트워크 필드는 [Part 2](../../eks/02-eks-cluster-creation-part2.md)의 검토한 전체 구성에 넣습니다. 문서용 CIDR과 모든 ID를 실제 값으로 바꿉니다:

```yaml
# Networking example; merge into a reviewed full ClusterConfig.
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"
vpc:
  id: vpc-0123456789abcdef0
  controlPlaneSecurityGroupIDs:
    - sg-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
```

**퍼블릭·프라이빗 API:** 퍼블릭 Kubernetes 엔드포인트는 클러스터 보안 그룹이 아니라 `publicAccessCidrs`로 제한합니다. 클러스터 보안 그룹은 프라이빗 엔드포인트 통신에 적용됩니다. CIDR 허용 목록이나 보안 그룹 규칙이 IAM·RBAC 권한을 부여하지는 않습니다.

**포드 보안 그룹:** 지원되는 컴퓨팅에서 필요한 IAM·VPC CNI 설정과 기능을 먼저 구성하고 `SecurityGroupPolicy`를 생성합니다. 인스턴스 trunking 호환성, CNI 버전, 적용 모드, DNS, 실제 보안 그룹 규칙을 확인합니다. Windows와 EKS Auto Mode는 이 기능을 지원하지 않으며 EC2 `t` 계열도 지원하지 않습니다. Fargate에는 별도의 지원 구성이 있습니다.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: application-sg
  namespace: sg-lab
spec:
  podSelector:
    matchLabels:
      app: my-app
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

정책은 별도로 만든 `sg-lab` 네임스페이스의 포드를 선택하며 CRD 객체 생성만으로 실제 보안 그룹 연결을 입증하지는 못합니다. 포드 보안 그룹의 standard·strict 모드와 SNAT에 따라 VPC 외부 트래픽에 적용되는 그룹이 달라집니다. 현재 설정의 모드별 동작을 문서로 확인합니다.

Kubernetes NetworkPolicy는 구성된 네트워크 플러그인이 적용하는 별도 메커니즘입니다. 클러스터가 NetworkPolicy를 지원한다고 포드 통신이 자동으로 기본 차단되는 것은 아닙니다. 의도적인 정책 구성은 문제 3을 참고합니다.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,publicAccess:endpointPublicAccess,privateAccess:endpointPrivateAccess,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_SECURITY_GROUP_ID:?}"
```

참고: [클러스터 보안 그룹](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html), [API 엔드포인트 접근](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [포드 보안 그룹](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html).

</details>

3. EKS에서 Kubernetes NetworkPolicy를 실제 적용하려면 무엇이 필요한가요?
   * A) 보안 그룹 규칙만 필요
   * B) Amazon VPC CNI·Calico·Cilium 등 지원되며 활성화된 정책 구현체
   * C) VPC Flow Logs만 필요
   * D) 적용 구현체 없이 NetworkPolicy 객체만 생성

<details>
<summary>정답 보기</summary>

**정답: B) Amazon VPC CNI·Calico·Cilium 등 지원되며 활성화된 정책 구현체**

구성된 네트워크 정책 구현체가 필요하며 `NetworkPolicy` 객체 생성만으로 트래픽 규칙이 적용되지는 않습니다. **Amazon VPC CNI도 NetworkPolicy를 지원**하므로 이 기능만을 위해 Calico나 Cilium이 반드시 필요한 것은 아닙니다.

**Amazon VPC CNI 경로:** 지원되는 클러스터·플랫폼, Linux 커널, CNI 버전을 확인하고 애드온을 소유한 구성 경로에서 정책 기능을 활성화합니다. 현재 AWS 지침은 표준·관리자 정책을 함께 사용하기 위해 VPC CNI 1.21.0 이상과 Linux 커널 5.10 이상을 안내합니다. 과거의 최소 버전을 현재 클러스터의 업데이트 목표로 사용하지 않습니다.

```bash
aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --query 'addon.{version:addonVersion,status:status,configuration:configurationValues}'
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_CNI_VERSION:?}" \
  --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  get daemonset aws-node -o jsonpath='{.spec.template.spec.containers[*].name}{"\n"}'
```

EKS 관리형 애드온의 관련 구성 값은 다음과 같습니다:

```json
{
  "enableNetworkPolicy": "true"
}
```

필요한 기존 설정을 유지하며 **검토한 전체 구성**에 병합합니다. 새 `configurationValues` 문서는 JSON 패치가 아닙니다. 오래된 업스트림 매니페스트로 EKS 관리형 DaemonSet을 덮어쓰거나 애드온을 다운그레이드하지 않습니다. Helm·자체 관리형 설치는 해당 설치의 문서화된 구성 경로를 사용합니다.

standard 시작 모드에서는 새 포드에 정책이 설정되기 전까지 통신이 허용될 수 있습니다. strict 모드는 기본 차단으로 시작하지만 CoreDNS 의존성을 포함해 필요한 모든 연결 정책을 미리 준비해야 합니다. 기존 클러스터를 검토 없이 strict 모드로 전환하지 않습니다.

**대안 구현체:**

- **Amazon VPC 네트워킹과 Calico:** AWS IPAM·CNI를 유지하고 운영자의 `Installation`을 `AmazonVPC`로 구성합니다. 공식 EKS 안내의 고정 버전 운영자·CRD와 AWS 포드 IP 주석·RBAC 전제조건을 따릅니다. 이 Calico 경로에서는 AWS 자체 정책 적용을 비활성화합니다. 운영자만 설치하거나 임의의 VXLAN 매니페스트를 적용하는 것은 같은 설계가 아닙니다.

```yaml
# Installation resource for the Amazon VPC networking path, after operator/CRDs.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
```

- **Amazon VPC CNI와 Cilium:** 문서화된 chaining 구성이 필요하며 터널·masquerade만 끈다고 chaining이 구성되지는 않습니다. 다음 값은 릴리스된 1.20.1 안내의 참조입니다. 릴리스·클러스터 호환성과 전체 전제조건을 확인합니다. 기존 포드에는 새 chaining 경로가 자동 적용되지 않으므로 통제된 롤아웃으로 다시 생성해야 합니다.

```yaml
# Relevant Helm values from the Cilium 1.20.1 AWS-CNI chaining guide.
# This is not a complete install or migration command.
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
```

검토하지 않은 CNI·정책 설치를 겹치지 말고 의도한 구현체를 선택해 검증합니다. 구현체 교체 후 노드 수준 규칙이 남을 수 있으므로 계획적인 전환이 필요합니다.

**정책 예제:** 새 `policy-lab` 네임스페이스에서 frontend→backend TCP 8080과 DNS를 허용하고 다른 트래픽을 차단합니다. 백엔드는 실제로 8080에서 수신해야 합니다. AWS 구현체에는 Service와 컨테이너의 같은 포트를 사용합니다. 아래 DNS 선택기는 `kube-system`의 일반 CoreDNS 포드를 전제로 하므로 NodeLocal DNSCache·사용자 지정 DNS에는 별도 규칙 검토가 필요합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

양쪽 엔드포인트가 다른 통신을 차단하므로 frontend 송신과 backend 수신을 모두 허용합니다. 여러 표준 NetworkPolicy의 허용 규칙은 합쳐지며 기본 거부 객체가 허용 규칙을 덮어쓰지는 않습니다. 애플리케이션 연결 거부를 DNS 실패와 혼동하지 않도록 테스트 네임스페이스의 DNS는 허용합니다.

**의미 있는 검증:** Deployment가 관리하는 frontend·backend·무관한 클라이언트 포드를 사용합니다. AWS는 `metadata.ownerReferences`가 없는 독립 포드의 정책 적용이 불안정할 수 있다고 안내하므로 단독 `kubectl run` 포드만으로 검증하지 않습니다. 정책 전 연결을 확인하고 정책 적용 후 frontend는 성공하고 무관한 클라이언트는 실패하며 DNS는 계속 동작하는지 확인합니다. 정책 반영을 기다린 뒤 새 연결로 시험합니다. CNI 포드가 보이거나 YAML 적용이 성공하는 것만으로 충분하지 않습니다.

AWS VPC CNI 정책 적용은 지원되는 EC2 Linux 노드에 해당하며 Windows·Fargate에는 적용되지 않습니다. 포드 기본 인터페이스와 클러스터 IP 계열에 적용되고 추가 인터페이스 및 IPv6 포드의 IPv4 송신에는 제약이 있습니다. 보안 그룹·Network Firewall·흐름 로그는 별도의 역할을 하며 이 Kubernetes 정책 구성을 대체하지 않습니다.

참고: [VPC CNI 정책 구성](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [AWS 정책 제약](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [EKS의 Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks), [Cilium 1.20.1 chaining 원문](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst), [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

4. EKS 1.28 이상에서 Kubernetes API 데이터의 저장 시 암호화를 올바르게 설명한 것은 무엇인가요?
   * A) 봉투 암호화가 기본 적용되며 고객 관리 KMS 키는 선택 사항
   * B) Secret 암호화를 위해 모든 클러스터를 다시 생성해야 함
   * C) Base64 인코딩이 저장 시 암호화를 제공
   * D) 애플리케이션 사이드카가 EKS 컨트롤 플레인 데이터베이스를 암호화해야 함

<details>
<summary>정답 보기</summary>

**정답: A) 봉투 암호화가 기본 적용되며 고객 관리 KMS 키는 선택 사항**

Kubernetes **1.28 이상**의 EKS 클러스터는 **모든 Kubernetes API 데이터**에 KMS v2 봉투 암호화를 기본 적용합니다. 고객 관리 KMS 키를 연결하지 않았다면 AWS 소유 키를 사용합니다. Secret뿐 아니라 ConfigMap 등 저장되는 API 리소스도 포함됩니다. 이는 etcd 디스크 암호화에 더해 적용되며 노드나 EBS 볼륨의 애플리케이션 데이터를 암호화하지는 않습니다.

**변경 전에 현재 구성을 확인합니다.** `encryptionConfig`에 고객 관리 키 ARN이 없다고 Secret이 암호화되지 않았다는 뜻은 아닙니다. 콘솔은 AWS 소유 키의 ARN을 노출하지 않고 해당 모드를 표시합니다.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status,encryption:encryptionConfig}'

# Optional CMK inspection, only when a customer-managed key is required.
aws kms describe-key --key-id "${KMS_KEY_ARN:?Reviewed customer-managed key ARN}" \
  --region "$EXAMPLE_REGION" \
  --query 'KeyMetadata.{arn:Arn,state:KeyState,spec:KeySpec,usage:KeyUsage}'
```

**선택적인 고객 관리 키(CMK).** 고객의 키 제어가 필요하면 클러스터와 같은 리전의 대칭 암호화 키를 사용합니다. 키 가용성, 호출자의 IAM 권한, 키 정책·그랜트, 필요한 교차 계정 권한을 확인합니다. `eks.amazonaws.com`에 일부 KMS 작업만 허용한 일반 정책으로는 구성이 완성되지 않습니다. 프로비저닝·연결 자격 증명에는 문서화된 `kms:DescribeKey`, `kms:CreateGrant` 권한이 필요합니다. `CreateCluster`에서 `CreateGrant`를 제어할 때 `kms:GrantIsForAWSResource` 조건은 지원되지 않습니다.

`CreateCluster`에 provider를 지정하거나 조건에 맞는 기존 클러스터에 `AssociateEncryptionConfig`로 CMK를 연결할 수 있으므로 반드시 새 클러스터를 만들 필요는 없습니다. 이를 일반적인 키 교체나 암호화 비활성화 작업으로 사용하지 않습니다. 이미 CMK를 연결한 클러스터는 지원되는 키 관리 절차를 따라야 합니다.

```bash
# Optional CMK association for an eligible existing cluster.
# Review current configuration, key policy/grants and recovery procedures first.
KMS_CONFIG_DIR=$(mktemp -d /tmp/eks-kms-config.XXXXXX)
: "${KMS_CONFIG_DIR:?}"
jq -n --arg arn "${KMS_KEY_ARN:?}" \
  '[{resources:["secrets"],provider:{keyArn:$arn}}]' \
  > "$KMS_CONFIG_DIR/encryption.json" || exit 1
if ENCRYPTION_UPDATE_ID=$(aws eks associate-encryption-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --encryption-config "file://$KMS_CONFIG_DIR/encryption.json" \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$ENCRYPTION_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

업데이트 ID를 기록하고 `Successful` 또는 실패 상태까지 확인합니다. 요청 접수만으로 완료된 것은 아닙니다. 예제의 `resources: ["secrets"]`는 호환성을 위해 허용되지만 EKS 1.28 이상에서 암호화 범위를 Secret으로 제한하지 않습니다. 이 필드는 사용 중단되었으며 모든 Kubernetes API 데이터가 봉투 암호화됩니다. 현재 API는 resources 생략·null·빈 목록도 허용하지만 응답에는 기존 `["secrets"]` 값이 유지됩니다. Kubernetes 1.27 이하용 `enable-kms` 절차는 역사적 안내이며 현재 지원 버전으로의 전환 목표가 아닙니다.

클러스터가 있는 동안 연결된 키를 실습 정리 대상으로 비활성화하거나 삭제하지 않습니다. 키를 사용할 수 없으면 컨트롤 플레인이 비정상 상태가 될 수 있고 영구적인 키 손실은 복구 불능으로 이어질 수 있습니다. CMK 선택 전에 키 복구·접근·모니터링을 검토합니다. 기본 AWS 소유 키 암호화에는 고객의 키 구성이 필요하지 않으며 CMK에는 별도 KMS 비용이 발생합니다.

**Secret 사용 방식은 그대로입니다.** 권한 있는 API 클라이언트와 포드는 사용 가능한 값을 받으므로 저장 시 암호화가 RBAC, 워크로드 자격 증명, 로그·백업 보호를 대체하지는 않습니다. 다음 매니페스트는 공개된 더미 데이터이며 실제 운영 비밀이 아닙니다:

```yaml
# Public dummy data for a newly created secrets-lab namespace only.
apiVersion: v1
kind: Secret
metadata:
  name: example-credentials
  namespace: secrets-lab
type: Opaque
stringData:
  username: example-user
  password: public-training-placeholder
```

```bash
# Inspect keys and metadata without printing values.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  -n secrets-lab get secret example-credentials -o json |
  jq '{name:.metadata.name,type:.type,keys:(.data|keys)}'
```

실제 자격 증명은 평문·base64 매니페스트 커밋, 셸 이력에 남는 리터럴, 값을 출력하는 진단 명령을 피합니다. Base64는 되돌릴 수 있는 인코딩입니다. AWS Secrets Manager는 CSI 파일 마운트나 Kubernetes Secret 동기화 컨트롤러와 연동할 수 있으므로 모든 애플리케이션에 반드시 SDK 변경이 필요한 것은 아닙니다. 동기화된 Secret에는 Kubernetes 접근 통제가 계속 적용됩니다. 사이드카는 관리형 API 서버의 저장 시 암호화를 구성할 수 없습니다.

참고: [기본 봉투 암호화](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [AssociateEncryptionConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_AssociateEncryptionConfig.html), [기존 KMS 절차와 권한](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html), [EKS의 Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html).

</details>

5. AL2023 EC2 관리형 노드의 kubelet 설정은 어떻게 사용자 지정해야 하나요?
   * A) 콘솔에서 EKS 컨트롤 플레인의 kubelet 편집
   * B) eksctl·시작 템플릿 사용자 데이터로 지원되는 nodeadm NodeConfig 제공
   * C) kubectl edit node로 status.capacity 변경
   * D) AL2023 부팅마다 AL2 bootstrap.sh 실행

<details>
<summary>정답 보기</summary>

**정답: B) eksctl·시작 템플릿 사용자 데이터로 지원되는 nodeadm NodeConfig 제공**

**AL2023 EC2 노드**에서는 `nodeadm`의 `NodeConfig`와 지원되는 eksctl·시작 템플릿 연동을 사용합니다. AL2의 `/etc/eks/bootstrap.sh` 절차나 존재한다고 가정한 `eksctl create nodegroup --kubelet-extra-args` 플래그를 사용하지 않습니다. 이전 `kubeletExtraArgs` 맵은 이 예제의 지원되는 관리형 노드 그룹 필드가 아닙니다.

**eksctl:** AL2023의 `overrideBootstrapCommand`는 이름과 달리 YAML `NodeConfig`를 담습니다. eksctl이 이를 사용자 데이터 앞에 넣으면 nodeadm이 생성된 노드 구성과 병합합니다. EKS가 선택하는 기본 AMI에는 EKS가 필수 클러스터 구성을 제공합니다. 확대 적용 전에 테스트 노드에서 실제 병합 결과를 확인합니다:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-kubelet
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
    overrideBootstrapCommand: |
      apiVersion: node.eks.aws/v1alpha1
      kind: NodeConfig
      spec:
        kubelet:
          config:
            kubeReserved:
              cpu: 100m
              memory: 300Mi
            systemReserved:
              cpu: 200m
              memory: 512Mi
            evictionHard:
              memory.available: 500Mi
            mergeDefaultEvictionSettings: true
```

위의 예약 리소스와 500 MiB 축출 임계값은 **예시**이며 측정된 권장값이 아닙니다. 포드의 할당 가능 용량을 줄이고 부적절하면 축출을 일으킬 수 있습니다. Kubernetes 1.36에서 지원되는 `mergeDefaultEvictionSettings: true`는 kubelet이 일부 축출 맵을 처리할 때 생략된 기본 신호를 유지합니다. 적절히 병합하지 않고 신호 하나만 지정하면 다른 기본 임계값이 의도치 않게 0이 될 수 있습니다.

**사용자 지정 AMI·시작 템플릿 경로:** eksctl이 생성한 구성 밖에서 AMI ID를 직접 지정한다면 클러스터 이름, API 엔드포인트, base64 CA, 서비스 CIDR을 모두 제공합니다. [Part 1 퀴즈의 고급 문제 5](02-eks-cluster-creation-part1-quiz.md#고급-주제)의 메타데이터 생성 절차를 재사용하고 해당 NodeConfig에 검토한 `spec.kubelet.config`를 추가합니다. kubelet 항목만 있는 일부 객체는 독립적인 전체 부트스트랩 구성이 아닙니다.

AL2023은 사용자 데이터 전에 `nodeadm-config`, 이후에 `nodeadm-run`을 실행합니다. `nodeadm init`을 중복 실행하거나 해당 서비스와 충돌하도록 kubelet을 수동 시작·재설정하지 않습니다. Bottlerocket·Windows 등 다른 OS는 별도 구성 방식을 사용하며 이 예제는 EKS Auto Mode 노드용이 아닙니다.

| 설정 | 확인할 내용 |
| --- | --- |
| `maxPods` / nodeadm `maxPodsExpression` | 인스턴스 ENI·IP 한도, CNI 모드, prefix delegation, 지원 밀도; 110을 보편적인 값으로 강제하지 않음 |
| 노드 레이블·테인트 | 관리형 노드 그룹 필드를 우선 사용하고 EKS·AZ 레이블 대신 자체 접두사 사용 |
| `kubeReserved`, `systemReserved` | 실제 호스트·시스템 워크로드 요구와 Node Allocatable |
| `evictionHard`, 소프트 임계값 | 메모리·디스크·inode 신호와 기본값 병합; 관계없는 보호 기능을 끄지 않음 |
| Cgroup 드라이버 | OS·컨테이너 런타임 호환성; 검토한 변경이 필요하지 않으면 검증된 AMI 기본값 유지 |

**검증:** Node의 capacity·allocatable과 실제 서비스 구성·로그를 확인합니다. 노드가 Ready라는 사실만으로 사용자 지정 값이 모두 적용되었다고 볼 수 없습니다. 이 감사는 구성 구문과 공식 필드 정의를 확인했으며 해당 설정으로 노드를 부팅하지는 않았습니다.

```bash
# Kubernetes-side checks through the intended cluster context.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" describe node "${EXAMPLE_NODE_NAME:?}"

# Run separately on a specifically authorized AL2023 test node.
sudo systemctl status nodeadm-config nodeadm-run kubelet --no-pager
sudo systemctl cat kubelet
sudo journalctl -u nodeadm-config -u nodeadm-run -u kubelet --since '-15 min' --no-pager
```

모든 AMI에 `/etc/systemd/system/kubelet.service.d/10-kubelet-args.conf`가 있다고 가정하지 말고 서비스가 실제 사용하는 구성 경로를 확인합니다. 진단 로그도 적절한 범위로 수집·보호합니다.

`kubectl edit node`는 Node 메타데이터를 바꾸지만 kubelet 시작 설정을 지정하지 않습니다. SSM은 호스트 명령을 실행할 수 있으나 임시 호스트 변경은 관리형 노드 교체 후에도 유지할 구성이 아니며 중단을 유발하는 재시작이 필요할 수 있습니다. 검토한 설정을 프로비저닝 구성에 넣고 계획적으로 노드를 교체·시험합니다.

참고: [eksctl AL2023 부트스트랩](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [AL2023 서비스](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [nodeadm API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/), [KubeletConfiguration](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/), [Kubernetes 1.36 필드 정의](https://github.com/kubernetes/kubelet/blob/v0.36.0/config/v1beta1/types.go).

</details>

6. EKS에서 제거된 PodSecurityPolicy 통제를 대체할 수 있는 메커니즘은 무엇인가요?
   * A) EC2 보안 그룹만 사용
   * B) Pod Security Admission과 필요에 맞는 호환 정책 엔진
   * C) CloudWatch 로그 보존만 설정
   * D) 각 포드에 IAM 사용자 액세스 키 저장

<details>
<summary>정답 보기</summary>

**정답: B) Pod Security Admission과 필요에 맞는 호환 정책 엔진**

PodSecurityPolicy는 Kubernetes 1.21에서 사용 중단되었고 1.25에서 제거되었습니다. 기본 **Pod Security Admission(PSA)**으로 **Pod Security Standards(PSS)**를 적용하고, 그 이상의 요구사항에는 적절한 정책 엔진을 사용합니다.

**PSA:** Privileged·Baseline·Restricted는 PSS의 세 수준이며 `enforce`·`audit`·`warn`은 별도의 모드입니다. 새 실습 네임스페이스에서 다음 예제는 Baseline을 강제하면서 Restricted 위반을 보고합니다. 정책 버전은 EKS 1.36 예제에 맞춰 고정했으며 실제 클러스터가 지원하는 버전을 선택해야 합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: policy-engine-lab
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```

기존 공유 네임스페이스의 레이블을 검토 없이 바꾸지 않습니다. 먼저 audit·warn으로 확인하고 워크로드를 수정한 뒤 강제 수준을 높입니다. PSA는 포드를 자동 수정하거나 이미 실행 중인 포드를 축출하지 않습니다. 포드 승인 시 검증하며 워크로드 템플릿에 대한 경고·감사는 컨트롤러가 포드를 만들기 전에 위반을 찾는 데 도움이 됩니다.

**Kyverno:** 검토한 예제의 차트 3.9.1은 컨트롤러 1.19.1을 포함합니다. Kyverno 1.19는 기존 `ClusterPolicy`·`Policy` 유형을 사용 중단했고 마이그레이션 안내는 1.20에서 제거할 예정이라고 명시합니다. 새 예제에는 현재 CEL 기반 정책 API를 사용합니다. 컨트롤러 버전만 바꾸지 말고 호환되지 않는 업그레이드 전에 기존 정책을 전환합니다.

```bash
# Optional new installation; review existing controllers and release compatibility.
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

다음 `policies.kyverno.io/v1` **ValidatingPolicy**는 일반·init·ephemeral 컨테이너의 `privileged: true`를 거부하고 실습 네임스페이스만 선택합니다. 필드 생략이나 false는 허용합니다:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```

이 예제는 단일 통제 항목이며 Baseline·Restricted 전체가 아닙니다. 정책 적용 전에 엔진·CRD가 준비되어야 하고 실제 클러스터의 승인·서브리소스 동작도 확인해야 합니다. 백그라운드 평가는 기존 위반을 보고하지만 실행 중인 워크로드를 축출하지 않습니다.

**OPA Gatekeeper 대안:** 해당 정책 모델이 요구사항에 맞으면 검토한 Gatekeeper 릴리스를 설치합니다. 이 예제는 차트·컨트롤러 3.23.1을 고정합니다:

```bash
# Alternative policy-engine example, not a prerequisite for the Kyverno example.
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

Gatekeeper에는 먼저 `templates.gatekeeper.sh/v1` ConstraintTemplate이 필요합니다. 템플릿과 생성된 Constraint CRD가 준비된 뒤 일치하는 Constraint를 적용합니다. 다음 Rego 예제도 세 컨테이너 목록을 검사하고 Constraint 범위를 실습 네임스페이스로 제한합니다:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: "package k8snoprivilegedlab\n\ncontainers[c] {\n  c := input.review.object.spec.containers[_]\n\
      }\ncontainers[c] {\n  c := input.review.object.spec.initContainers[_]\n}\ncontainers[c]\
      \ {\n  c := input.review.object.spec.ephemeralContainers[_]\n}\nviolation[{\"\
      msg\": msg}] {\n  c := containers[_]\n  c.securityContext.privileged == true\n\
      \  msg := sprintf(\"Privileged container is not allowed: %v\", [c.name])\n}\n"
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```

Gatekeeper의 `enforcementAction: deny`는 일치하는 위반을 거부하며 `dryrun`·`warn`으로 단계적으로 도입할 수 있습니다. Constraint 없이 템플릿만 생성하면 정책이 강제되지 않습니다. 설치한 릴리스가 지원하는 API·스키마·Rego 모드를 사용합니다.

**검증과 한계:** Kyverno 1.19.1 CLI의 경고를 오류로 처리하고 Gatekeeper 3.23.1 Gator와 함께 각각 여섯 개의 로컬 사례를 실행했습니다. 명시적 false, 필드 생략, 일반·init·ephemeral 컨테이너의 privileged 설정, 범위 밖 네임스페이스에서 두 구현 모두 의도한 결과를 냈습니다. 클러스터 설치나 실제 승인 테스트는 수행하지 않았습니다.

```bash
# Offline policy logic checks using locally reviewed fixture files.
kyverno apply kyverno-policy.yaml --resource test-pod.yaml --warnings-as-errors
gator test --filename gatekeeper-policy.yaml --filename test-pod.yaml --output=json
```

PSA나 다른 웹훅도 거부할 수 있는 경우 실제 거부를 특정 엔진의 결과라고 단정하지 않습니다. 정책·컨트롤러 상태, 대상 범위, 실제 승인 응답과 보고서를 확인합니다. 호스트 네임스페이스, hostPath, capabilities, 권한 상승 등 다른 PSS 요구사항에는 전체 통제 집합을 사용합니다.

AWS Security Hub, AWS Config, EC2 보안 그룹은 역할이 다르며 이를 활성화하는 것만으로 Kubernetes 포드 승인 통제를 대체할 수는 없습니다.

참고: [PSA](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [PSS](https://kubernetes.io/docs/concepts/security/pod-security-standards/), [Kyverno CEL 전환](https://kyverno.io/docs/guides/migration-to-cel/), [Kyverno 1.19.1](https://github.com/kyverno/kyverno/releases/tag/v1.19.1), [Gatekeeper 3.23.1 사용 안내](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/howto.md).

</details>

7. IRSA의 web-identity 신뢰에 필요한 IAM 자격 증명 공급자 전제조건은 무엇인가요?
   * A) 모든 포드에 저장한 IAM 사용자 액세스 키
   * B) cluster-admin RoleBinding
   * C) 클러스터 발급자와 일치하는 IAM OIDC 공급자
   * D) 각 워커 노드의 퍼블릭 IP

<details>
<summary>정답 보기</summary>

**정답: C) 클러스터 발급자와 일치하는 IAM OIDC 공급자**

IRSA에는 대상 클러스터의 발급자와 일치하는 IAM OIDC 공급자가 필요합니다. 이미 존재하는지 확인하고 중복 공급자를 만들거나 다른 클러스터의 발급자를 재사용하지 않습니다. 워크로드가 IAM 역할을 수임하기 전에 이 조건이 충족되어야 하지만 서비스 계정 자체는 역할보다 먼저 만들고 나중에 주석을 추가할 수도 있습니다. 모든 리소스를 항상 하나의 엄격한 순서로 생성해야 하는 것은 아닙니다.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.identity.oidc.issuer --output text
eksctl utils associate-iam-oidc-provider \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --approve
```

과거의 고정 인증서 지문을 복사하지 말고 eksctl 또는 현재 IAM OIDC 공급자 절차를 사용합니다. `sts.amazonaws.com`을 의도한 client ID·audience로 구성합니다. 인터넷 송신이 없는 VPC 내부에서 공급자를 설정하려면 별도 `oidc-eks` 인터페이스 엔드포인트·private DNS 또는 접근 가능한 관리 경로가 필요할 수 있습니다. IRSA 토큰 교환에는 리전 STS 연결이 별도로 필요합니다.

이후 제한된 역할 권한 정책과 문제 1의 `aud`, `sub` 조건을 모두 포함하는 신뢰 정책을 만들고 정확한 서비스 계정에 주석을 추가한 뒤 이를 참조하는 새 포드를 생성합니다. 기존 포드는 서비스 계정 주석이 바뀌었다는 이유만으로 새 설정을 주입받지 않으므로 정상적인 컨트롤러 롤아웃으로 다시 생성합니다.

신원 확인에는 문제 1의 명시적인 포드 매니페스트를 사용합니다. `kubectl run --serviceaccount`는 현재 지원되는 플래그가 아닙니다:

```bash
# After deploying the identity-check Pod from question 1.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n irsa-lab \
  get pod irsa-identity-check -o jsonpath='{.status.phase}{"\n"}'
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n irsa-lab logs irsa-identity-check
```

포드 종료 상태와 반환된 계정·수임 역할을 예상한 역할과 비교합니다. 노드 역할이 반환되었다고 IRSA가 정상이라고 판단하지 않습니다. 이후에는 범위가 제한된 애플리케이션 작업만 시험합니다. 버킷 없이 `aws s3 ls`를 실행하면 전체 버킷 나열 권한이 필요하므로 단일 버킷 정책의 시험에 맞지 않습니다.

EKS Pod Identity는 다른 방식이며 클러스터마다 IAM OIDC 공급자를 만들 필요가 없습니다. 서비스 계정 연결, 에이전트, IAM 신뢰 요구사항을 IRSA와 구분합니다.

참고: [IAM OIDC 공급자 생성](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html), [IRSA 프라이빗 연결](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [포드 구성](https://docs.aws.amazon.com/eks/latest/userguide/pod-configuration.html).

</details>

8. EKS 컨트롤 플레인 로그 내보내기는 어떻게 활성화하나요?
   * A) 관리형 컨트롤 플레인 호스트에 에이전트 설치
   * B) EKS API·콘솔·eksctl로 클러스터 로깅 구성
   * C) 워커 노드에 Fluentd만 설치
   * D) 관리형 API 서버에 SSH로 접속하여 구성 수정

<details>
<summary>정답 보기</summary>

**정답: B) EKS API·콘솔·eksctl로 클러스터 로깅 구성**

EKS API, 콘솔 또는 eksctl로 컨트롤 플레인 로그 내보내기를 활성화합니다. 컨트롤 플레인 호스트는 AWS가 운영하므로 워커 노드에 CloudWatch·Fluentd 에이전트를 설치하는 것으로 해당 로그가 활성화되지는 않습니다. 운영자는 관리형 컨트롤 플레인 호스트에 SSH로 접속할 수 없습니다.

**AWS CLI:** 현재 설정을 확인하고 필요한 유형을 선택합니다. 비동기 업데이트이므로 ID를 기록하고 성공 또는 실패 상태까지 `describe-update`를 반복합니다. 로깅 업데이트에는 클러스터의 각 서브넷에서 최대 다섯 개의 여유 IP가 필요할 수 있습니다.

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

API·감사 로그만 켜고 나머지 세 유형을 명시적으로 끄려면 감사·보존 요구사항을 검토한 뒤 다음 **대안** 페이로드를 사용합니다. 두 구성을 순차 적용하거나 비용만을 이유로 필요한 로그를 끄지 않습니다:

```json
{
  "clusterLogging": [
    {"types": ["api", "audit"], "enabled": true},
    {"types": ["authenticator", "controllerManager", "scheduler"], "enabled": false}
  ]
}
```

**eksctl 대안:** 미리보기와 실제 적용은 별개이며 검토한 변경의 적용에는 `--approve`가 필요합니다. 의도적으로 일부 유형을 끄려면 `--disable-types`를 사용할 수 있습니다.

```bash
# Alternative interface; do not submit a second update while one is running.
# Without --approve this previews the logging change.
eksctl utils update-cluster-logging \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --enable-types api,audit,authenticator,controllerManager,scheduler

# Apply the reviewed change.
eksctl utils update-cluster-logging \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

**콘솔:** 클러스터의 **Observability**에서 **Control plane logging → Manage logging**을 선택합니다. 각 로그 유형을 정하고 검토한 설정을 저장합니다.

| 유형 | 목적 | 스트림 접두사 |
| --- | --- | --- |
| `api` | API 서버 구성 요소 진단; 시작 플래그는 로그 교체 전에 수집된 경우에만 확인 가능 | `kube-apiserver-` |
| `audit` | 관리형 감사 정책에 따라 기록된 Kubernetes API 활동 | `kube-apiserver-audit-` |
| `authenticator` | IAM 인증 진단 | `authenticator-` |
| `controllerManager` | 기본 Kubernetes 제어 루프 진단 | `kube-controller-manager-` |
| `scheduler` | 포드 스케줄링 진단 | `kube-scheduler-` |

감사 로그가 모든 애플리케이션 요청이나 노드의 모든 프로세스·네트워크 활동을 기록하는 것은 아닙니다. 관련 AWS API 활동은 CloudTrail에서 별도로 기록합니다. 컨트롤 플레인 로그는 보통 수 분 내에 최선 노력 방식으로 전달되며 활성화 전에 이미 교체된 로그를 복구하지는 않습니다.

**내보내기 확인:** 로그는 클러스터 계정·리전의 `/aws/eks/<cluster-name>/cluster`에 있습니다. 스트림 접미사는 교체되므로 고정된 하나의 스트림을 가정하지 말고 최근 이벤트 시간을 확인합니다.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.logging
aws logs describe-log-streams --region "$EXAMPLE_REGION" \
  --log-group-name "/aws/eks/$EXAMPLE_CLUSTER/cluster" \
  --order-by LastEventTime --descending --max-items 10
```

CloudWatch 수집·저장·쿼리에는 비용이 발생합니다. 요구사항에 맞는 보존·접근 통제를 설정하고 필요한 로그 유형이 실제 도착하는지 확인합니다. 구성 업데이트 성공이 모든 과거 이벤트의 존재를 입증하지는 않습니다. 워커·애플리케이션 로그 수집기는 별도의 데이터 플레인 영역입니다.

참고: [EKS 컨트롤 플레인 로깅](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

9. 사용자 지정 템플릿이 아니라 EKS 관리형 노드 그룹 요청에서 지정한 인스턴스 유형은 어떻게 변경하나요?
   * A) 콘솔에서 instanceTypes 필드를 제자리 수정
   * B) 대체 노드 그룹을 만들고 워크로드 이동 검증
   * C) kubectl edit node로 EC2 하드웨어 변경
   * D) update-nodegroup-config에 새 인스턴스 유형 전달

<details>
<summary>정답 보기</summary>

**정답: B) 대체 노드 그룹을 만들고 워크로드 이동 검증**

이 문제는 사용자 지정 시작 템플릿이 아니라 **관리형 노드 그룹 요청**에서 지정한 인스턴스 유형을 대상으로 합니다. 이 유형은 `update-nodegroup-config`로 변경할 수 없으므로 새 그룹을 만들고 워크로드를 이동합니다.

사용자 지정 시작 템플릿으로 그룹을 만들고 유형을 그 템플릿에 지정했다면 별도 경로가 있습니다. **같은** 템플릿의 새 버전을 검토하고 `update-nodegroup-version`으로 적용할 수 있으며, 이 경우에도 인스턴스는 교체됩니다. EKS가 생성한 템플릿을 직접 수정하거나 두 위치에 유형을 중복 지정하지 않습니다. 다른 CPU 아키텍처가 같은 AMI·이미지로 동작한다고 가정하지도 않습니다.

**1. 대체 용량 생성.** 인스턴스 제공 여부, 할당량, 아키텍처, CNI·IP 용량, AZ, 스토리지, 노드 역할 권한을 확인합니다. 다음 두 명령은 기존 테스트 클러스터에서 사용하는 대안입니다:

```bash
# Alternative 1: eksctl, for an unused managed node-group name.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name "${NEW_NODEGROUP_NAME:?}" \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large --nodes 3 --nodes-min 1 --nodes-max 5 \
  --node-labels "example.com/migration-target=true"

# Alternative 2: AWS CLI; do not run both for the same node group.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=1,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/migration-target":"true"}'
```

**2. 새 그룹 확인.** `ACTIVE` 상태와 정상 `Ready` 노드, CNI·DNS 동작을 기다립니다. 레이블 조회만으로 애플리케이션 준비 상태를 확인할 수는 없습니다:

```bash
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --query 'nodegroup.{status:status,health:health,types:instanceTypes,subnets:subnets}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l example.com/migration-target=true -o wide
```

**3. 이동과 테스트.** 애플리케이션에 맞는 롤링 또는 블루/그린 계획을 선택합니다. Service는 노드 그룹 이름이 아니라 선택된 준비 상태의 포드 엔드포인트로 트래픽을 보냅니다. 롤백 조건과 데이터 호환성을 파악할 때까지 기존 용량을 유지합니다.

수동 드레인에서는 기존 노드 하나를 선택하고 노드 그룹 레이블, PDB, 여유 용량, 로컬 스토리지를 먼저 확인합니다. 이 예제는 축출 제약을 우회하거나 `emptyDir` 데이터를 버리지 않습니다. 드레인이 실패하면 계속 진행하기 전에 원인을 확인합니다. 노드가 cordon 상태로 남을 수 있습니다.

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```

또는 실제 애플리케이션의 포드 템플릿을 변경하여 대체 그룹을 선택합니다. 다음 완전한 예제는 새 `migration-lab` 네임스페이스용 별도 데모이며 기존 애플리케이션을 덮어쓸 매니페스트가 아닙니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: migration-demo
  template:
    metadata:
      labels:
        app: migration-demo
    spec:
      nodeSelector:
        example.com/migration-target: "true"
      containers:
        - name: nginx
          image: nginx:1.30.4
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: migration-demo
```

PDB는 자발적 축출 중 일치하는 정상 포드 두 개를 요구합니다. 복제본이 세 개라면 다른 조건도 허용할 때 보통 하나씩 축출할 수 있습니다. 가용성, 직접 삭제 방지, 노드 로컬 데이터 보존을 보장하지는 않습니다. 대표 부하로 배치, 준비 상태, Service 라우팅, 영구 볼륨의 AZ 제약, 백업을 확인합니다.

**4. 검증 후에만 기존 그룹 제거.** eksctl과 AWS 삭제 명령을 모두 실행하거나 PDB를 우회하지 않습니다. 대상 클러스터·그룹을 검토하고 이번 이동 작업이 소유한 그룹만 제거합니다:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```

애플리케이션 검증에 실패하면 기존 그룹을 유지합니다. 블루/그린은 일시적으로 용량과 비용을 늘리며 상태 저장 변경의 쉬운 롤백을 보장하지 않습니다. `kubectl edit node`는 Kubernetes 메타데이터를 바꾸지만 실제 EC2 인스턴스 유형을 바꾸지는 않습니다.

참고: [시작 템플릿 업데이트](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [UpdateNodegroupConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_UpdateNodegroupConfig.html), [노드 드레인](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/).

</details>

10. EKS 관리형 노드 그룹의 테인트에 대한 올바른 설명은 무엇인가요?
   * A) kubectl로만 테인트를 설정할 수 있음
   * B) 콘솔·API·eksctl의 노드 그룹 구성으로 설정하고 기존 Node 상태는 별도 확인
   * C) EKS 콘솔은 테인트를 구성할 수 없음
   * D) 톨러레이션이 일치하는 테인트 그룹으로의 배치를 보장

<details>
<summary>정답 보기</summary>

**정답: B) 콘솔·API·eksctl의 노드 그룹 구성으로 설정하고 기존 Node 상태는 별도 확인**

관리형 노드 그룹 테인트는 EKS 콘솔·API 또는 eksctl 구성 파일로 설정할 수 있습니다. 콘솔도 유효한 방법이므로 CLI 방식이 있다는 이유만으로 오답으로 처리하면 안 됩니다. `kubectl taint`는 개별 Node 객체를 바꾸며 관리형 그룹의 대체 노드에 적용할 영속적인 그룹 설정은 아닙니다.

**eksctl 구성:** 기존 클러스터와 사용하지 않는 그룹 이름을 확인한 뒤 다음 구성을 `nodegroup.yaml`로 저장하고 `eksctl create nodegroup -f nodegroup.yaml`을 사용합니다. 존재한다고 가정한 CLI 플래그 대신 지원되는 `taints` 필드를 사용합니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    labels:
      example.com/pool: batch
    taints:
      - key: dedicated
        value: batch
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
```

**AWS CLI 대안:** Kubernetes·eksctl의 효과 이름은 CamelCase이지만 EKS API는 대문자 이름을 사용합니다:

| Kubernetes / eksctl | EKS API | 효과 |
| --- | --- | --- |
| `NoSchedule` | `NO_SCHEDULE` | 일치하는 톨러레이션 없는 새 포드의 스케줄링을 막으며 기존 포드는 유지 |
| `PreferNoSchedule` | `PREFER_NO_SCHEDULE` | 소프트 스케줄링 선호이며 보장 아님 |
| `NoExecute` | `NO_EXECUTE` | 일치하는 톨러레이션 없는 기존 포드도 축출; `tolerationSeconds`로 지연 가능 |

```bash
# Alternative to the eksctl file: create a new group through the EKS API.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/pool":"batch"}' \
  --taints '[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"},{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
```

```bash
# Separate update example for the intended existing group.
if TAINT_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --taints '{"addOrUpdateTaints":[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"}],"removeTaints":[{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$TAINT_UPDATE_ID" \
    --query 'update.{status:status,errors:errors}'
fi
```

업데이트는 비동기이므로 성공을 기다리고 실제 Node 테인트를 확인합니다. 누군가 기존 Node에서 관리형 그룹의 테인트를 수동 제거하면 그룹 구성에 남아 있어도 EKS가 그 Node에 자동으로 다시 추가하지는 않습니다. 노드 변경 권한을 제한하고 변경 후 실제 상태를 확인합니다.

**전용 워크로드 배치:** 톨러레이션은 스케줄링을 허용하지만 포드를 해당 그룹으로 강제하지 않습니다. 적절한 노드 선택기·어피니티를 함께 사용합니다. 다음 완전한 데모는 새 `taint-lab` 네임스페이스를 사용합니다:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: batch-example
  namespace: taint-lab
spec:
  nodeSelector:
    example.com/pool: batch
  tolerations:
    - key: dedicated
      operator: Equal
      value: batch
      effect: NoSchedule
  restartPolicy: Never
  containers:
    - name: task
      image: busybox:1.37
      command: ["sh", "-c", "echo batch-example-complete"]
      resources:
        requests:
          cpu: 100m
          memory: 32Mi
        limits:
          memory: 64Mi
```

GPU 그룹에는 호환 GPU 인스턴스·AMI와 지원되는 디바이스 플러그인이 추가로 필요하며 워크로드는 `nvidia.com/gpu` 같은 확장 리소스를 요청해야 합니다. `dedicated=gpu` 테인트만으로 드라이버가 설치되거나 GPU가 할당되지는 않습니다. 테인트는 스케줄링 통제이지 테넌트 보안 경계가 아닙니다.

**유지 관리:** 임시 노드 테인트는 일반적인 새 스케줄링을 막을 수 있지만 실행 중인 포드를 드레인하지는 않습니다. 다음 두 명령은 검토한 유지 관리 기간의 시작과 끝에 각각 적용합니다:

```bash
# Individual-node maintenance example; does not evict existing Pods.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" taint node \
  "${EXAMPLE_NODE_NAME:?}" maintenance=planned:NoSchedule

# After the maintenance window, remove only this exact example taint.
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" taint node \
  "$EXAMPLE_NODE_NAME" maintenance=planned:NoSchedule-
```

축출이 필요하면 PDB를 고려한 별도 드레인 절차를 사용합니다. 실행 중인 그룹에 `NoExecute`를 추가하기 전에는 즉시 축출 영향을 검토합니다. 부트스트랩 등록 플래그도 별도 방식이지만 이 사용 사례에서는 관리형 그룹 설정이 더 명확합니다.

참고: [EKS 관리형 노드 테인트](https://docs.aws.amazon.com/eks/latest/userguide/node-taints-managed-node-groups.html).

</details>

## 실습 문제

### 실습 1: IRSA(IAM Roles for Service Accounts) 구성

**시나리오:** 기존 EKS 클러스터의 Linux 워크로드가 S3 버킷 하나의 승인된 `training/` 접두사를 읽어야 합니다. 모든 노드에 넓은 S3 정책을 주는 대신 전용 워크로드 역할을 부여합니다.

**전제조건:** 상용 AWS 파티션의 승인된 교육용 클러스터와 AWS CLI v2·eksctl·jq를 사용합니다. 운영자는 이 실습에 필요한 IAM·Kubernetes 권한을 가져야 합니다. 승인된 버킷의 `training/` 아래에 비민감 테스트 객체를 준비하고 `S3_BUCKET`·`S3_TEST_KEY`를 설정합니다. 버킷 정책과 고객 관리 암호화 키가 대상 역할을 허용해야 하며 객체 암호화에 필요할 때만 별도로 제한한 KMS 권한을 추가합니다. 이 예제는 버킷이나 객체를 생성하지 않습니다.

<details>
<summary>정답 보기</summary>

**1. 고유한 네임스페이스·전용 kubeconfig·클러스터 OIDC 공급자 준비.** 정리가 끝날 때까지 생성된 디렉터리와 소유권 기록을 유지합니다. 같은 Bash 세션에서 순서대로 진행하고 단계가 실패하면 재시도 전에 기록된 리소스를 확인합니다.

```bash
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```

워크로드에서 STS와 S3에 연결할 수 있어야 합니다. 프라이빗 전용 환경에는 적절한 리전 STS·ECR·S3 경로가 필요하며 VPC 내부에서 IAM OIDC 공급자를 생성할 때는 `oidc-eks` 연결도 필요할 수 있습니다. IMDS와 서비스 계정 사용 권한은 별도로 제한합니다. IRSA만으로 포드 격리가 이루어지지는 않습니다.

**2. 전용 역할과 제한된 정책 생성.** 신뢰 정책은 audience와 정확한 네임스페이스·서비스 계정 subject를 함께 요구합니다. 권한 정책은 해당 버킷의 `training/` 접두사 나열과 그 아래 객체 읽기만 허용하며 `ListAllMyBuckets` 권한은 주지 않습니다.

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```

역할은 새로 생성되어야 합니다. 생성 실패 시 정책 연결 전에 중단하고 정리를 위해 불변 IAM `RoleId`를 기록합니다. 우연히 이름이 같은 기존 역할에 실습 정책을 추가하지 않도록 합니다.

**3. 서비스 계정과 단기 테스트 포드 생성.** 세 컨테이너가 호출자 신원, 허용된 접두사의 최대 한 객체 나열, 지정한 객체의 메타데이터 읽기를 확인합니다. 예제는 개수·길이만 출력하고 신원 메타데이터를 기록하며 토큰·비밀 키·객체 내용을 출력하지 않습니다.

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```

세 컨테이너가 모두 성공하고 신원이 예상 계정·역할과 일치해야 합니다. 노드 역할이 반환되면 실패입니다. 포드가 실패하면 컨테이너별 상태·로그와 IAM 신뢰, 접두사, 버킷·키 정책, 연결을 확인합니다. 권한 실패를 해결하려고 `AmazonS3ReadOnlyAccess`를 연결하지 않습니다.

IAM 변경은 전파에 시간이 걸릴 수 있습니다. 원인을 해결한 뒤 소유한 네임스페이스에서 테스트 포드를 계획적으로 다시 생성합니다. 실패한 최초 실행을 성공의 근거로 간주하지 않습니다. 허용된 작업의 성공만으로 다른 모든 작업의 거부가 입증되지는 않으므로 적용되는 IAM·리소스 정책을 검토하고 필요하면 승인된 부정 테스트를 수행합니다.

**4. 소유한 네임스페이스와 역할 정리.** 네임스페이스 UID와 IAM RoleId로 이름 재사용을 구분합니다. 네임스페이스가 이미 없다면 기록한 역할 정리를 계속할 수 있습니다. 예상하지 못한 인라인 정책이나 조회 실패는 후속 정리를 중단하므로 관계없는 리소스를 삭제하지 말고 부분 실패를 확인합니다.

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

클러스터, 공유 OIDC 공급자, 버킷·객체는 유지합니다. 네임스페이스·역할 삭제를 확인하고 실패가 있으면 소유권 기록을 보관합니다. 포드 종료가 이미 발급된 모든 STS 자격 증명의 즉시 무효화를 보장한다는 뜻은 아닙니다.

이번 감사에서는 역할을 프로비저닝하거나 AWS를 대상으로 포드를 실행하지 않았습니다. 로컬 검사는 생성된 매니페스트·정책과 실패 시 보호 동작을 검증하며 실제 IAM 전파·네트워크·S3 접근은 환경별 시험이 필요합니다.

참고: [IRSA 역할 구성](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [IRSA 프라이빗 연결](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [S3 정책 조건](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html).

</details>

### 실습 2: EKS 클러스터 보안 강화

**시나리오:** 전용 EKS 1.36 교육용 클러스터에서 개별 보안 통제를 평가합니다. 통합 실습이며 검증된 프로덕션 구성은 아닙니다.

**전제조건:** 승인된 클러스터 관리 권한, AWS CLI v2·kubectl·jq, 호환 EC2 Linux 노드, 네트워크 정책이 활성화된 지원 EKS 관리형 VPC CNI, `kube-system`의 일반 CoreDNS 포드가 필요합니다. 기본 문제 3의 현재 CNI·커널 요구사항을 따릅니다. 정책 적용 전 포드 통신이 가능해야 하며 조직 전체 정책이 있으면 다른 승인된 테스트 설계가 필요할 수 있습니다. 이 실습만을 위해 두 번째 CNI를 설치하지 않습니다.

<details>
<summary>정답 보기</summary>

**1. 대상 확인과 현재 설정 저장.** 문서용 예제 주소가 아니라 실제 승인된 관리 송신 CIDR을 설정합니다. 예제는 EKS 1.36과 활성화된 관리형 CNI 정책 구성을 확인한 뒤 진행합니다.

```bash
: "${EXAMPLE_CLUSTER:?Use a dedicated EKS 1.36 training cluster}"
: "${EXAMPLE_REGION:?}"
: "${APPROVED_API_CIDR:?Actual approved administration egress CIDR}"
SECURITY_LAB_DIR=$(mktemp -d /tmp/eks-security-lab.XXXXXX)
: "${SECURITY_LAB_DIR:?}"
SECURITY_NAMESPACE="security-quiz-$(date +%s)-$$"
SECURITY_KUBECONFIG="$SECURITY_LAB_DIR/kubeconfig"

aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$SECURITY_LAB_DIR/before-cluster.json" || exit 1
jq -e '.version == "1.36" and .status == "ACTIVE"' \
  "$SECURITY_LAB_DIR/before-cluster.json" >/dev/null || exit 1
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --query addon --output json > "$SECURITY_LAB_DIR/cni.json" || exit 1
jq -e '(.configurationValues // "{}" | fromjson | .enableNetworkPolicy) as $enabled |
  .status == "ACTIVE" and ($enabled == true or $enabled == "true")' \
  "$SECURITY_LAB_DIR/cni.json" >/dev/null || exit 1
aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$SECURITY_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1

# Serialize cluster configuration updates. A timeout does not cancel an AWS update.
security_wait_update() {
  local update_id="$1" status attempt
  for ((attempt=1; attempt<=60; attempt++)); do
    status=$(aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
      --update-id "$update_id" --query update.status --output text) || return 1
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled)
        printf 'EKS update %s ended as %s\n' "$update_id" "$status" >&2
        return 1 ;;
      InProgress) sleep 10 ;;
      *) printf 'Unexpected EKS update status: %s\n' "$status" >&2; return 1 ;;
    esac
  done
  printf '%s\n' 'Update still pending; inspect it before another configuration change.' >&2
  return 1
}
```

**2. 검토한 엔드포인트·로깅 설정을 순차 적용.** 다음은 두 API 경로를 유지하고 퍼블릭 경로를 승인 CIDR로 제한합니다. 프라이빗 전용 대안을 선택하려면 Part 1처럼 프라이빗 라우팅·DNS·API 접근을 먼저 별도 확인합니다. 폴링 타임아웃이 AWS 업데이트를 취소하지는 않으므로 다음 변경 전에 진행 상태를 확인합니다.

EKS 1.36은 Secret을 포함한 Kubernetes API 데이터를 이미 봉투 암호화합니다. 고객 관리 키 구성이 비어 있다는 사실은 평문 저장의 근거가 아닙니다. 이 단계를 위해 두 번째 클러스터나 중복 KMS 키를 생성하지 않습니다. CMK가 필요하면 기본 문제 4의 검토한 절차와 키 수명 주기 주의사항을 적용합니다.

```bash
# Keep both API paths; the supplied CIDR must include the intended administration path.
SECURITY_ENDPOINT_UPDATE=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_ENDPOINT_UPDATE" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" get nodes || exit 1

# EKS 1.36 already has default envelope encryption; inspect rather than create a new cluster.
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,encryption:encryptionConfig}'

SECURITY_LOGGING_UPDATE=$(aws eks update-cluster-config \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_LOGGING_UPDATE" || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.logging
```

컨트롤 플레인 로그에는 CloudWatch 비용과 최선 노력 전달 특성이 있습니다. `/aws/eks/<cluster-name>/cluster`에 필요한 유형이 실제 도착하는지 확인하고 보존·접근 통제를 정합니다. 엔드포인트 제한은 IAM·Kubernetes 권한을 보완하며 대체하지 않습니다.

**3. 격리된 Restricted 네임스페이스와 테스트 워크로드 생성.** 세 Deployment는 VPC CNI 정책 검증에 적합한 컨트롤러 소유 포드를 만듭니다. 비루트 사용자, RuntimeDefault seccomp, capabilities 제거, 읽기 전용 루트 파일 시스템, 백엔드 임시 파일용 `emptyDir`를 사용합니다. ServiceAccount API 토큰은 필요하지 않습니다.

```bash
jq -n --arg ns "${SECURITY_NAMESPACE:?}" '{
  apiVersion:"v1",kind:"Namespace",metadata:{name:$ns,labels:{
    "pod-security.kubernetes.io/enforce":"restricted",
    "pod-security.kubernetes.io/enforce-version":"v1.36",
    "pod-security.kubernetes.io/audit":"restricted",
    "pod-security.kubernetes.io/audit-version":"v1.36",
    "pod-security.kubernetes.io/warn":"restricted",
    "pod-security.kubernetes.io/warn-version":"v1.36"
  }}
}' > "${SECURITY_LAB_DIR:?}/namespace.json" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  create -f "$SECURITY_LAB_DIR/namespace.json" || exit 1
SECURITY_NAMESPACE_UID=$(kubectl --kubeconfig "$SECURITY_KUBECONFIG" \
  get namespace "$SECURITY_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${SECURITY_NAMESPACE_UID:?}"
jq -n --arg ns "$SECURITY_NAMESPACE" --arg uid "$SECURITY_NAMESPACE_UID" \
  '{namespace:$ns,uid:$uid}' > "$SECURITY_LAB_DIR/namespace-owner.json" || exit 1

jq -n --arg ns "$SECURITY_NAMESPACE" '
  def deployment($name;$command):
    {
      apiVersion:"apps/v1",kind:"Deployment",metadata:{name:$name,namespace:$ns},
      spec:{replicas:1,selector:{matchLabels:{app:$name}},template:{
        metadata:{labels:{app:$name}},
        spec:{
          nodeSelector:{"kubernetes.io/os":"linux"},
          automountServiceAccountToken:false,
          securityContext:{
            runAsNonRoot:true,runAsUser:1000,runAsGroup:1000,fsGroup:1000,
            seccompProfile:{type:"RuntimeDefault"}
          },
          volumes:[{name:"tmp",emptyDir:{}}],
          containers:[({
            name:"app",image:"busybox:1.37",command:$command,
            securityContext:{
              allowPrivilegeEscalation:false,readOnlyRootFilesystem:true,
              capabilities:{drop:["ALL"]}
            },
            volumeMounts:[{name:"tmp",mountPath:"/tmp"}],
            resources:{requests:{cpu:"50m",memory:"32Mi"},limits:{memory:"64Mi"}}
          } + if $name == "backend" then {
            ports:[{name:"http",containerPort:8080}],
            readinessProbe:{httpGet:{path:"/",port:8080}}
          } else {} end)]
        }
      }}
    };
  {
    apiVersion:"v1",kind:"List",items:[
      deployment("backend";["sh","-c","mkdir -p /tmp/www && printf \"policy-test-ok\\n\" > /tmp/www/index.html && exec httpd -f -p 8080 -h /tmp/www"]),
      deployment("frontend";["sleep","3600"]),
      deployment("outsider";["sleep","3600"]),
      {
        apiVersion:"v1",kind:"Service",metadata:{name:"backend",namespace:$ns},
        spec:{selector:{app:"backend"},ports:[{name:"http",port:8080,targetPort:8080}]}
      }
    ]
  }' > "$SECURITY_LAB_DIR/workloads.json" || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" create -f "$SECURITY_LAB_DIR/workloads.json" || exit 1
for app in backend frontend outsider; do
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
    rollout status "deployment/$app" --timeout=180s || exit 1
done

# Establish baseline connectivity before applying the policies.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ || exit 1
```

정책 적용 전에 두 클라이언트가 모두 백엔드에 접근할 수 있어야 합니다. 기준 연결이 실패하면 먼저 원인을 해결하고 이를 네트워크 정책 적용의 증거로 간주하지 않습니다.

**4. 기본 거부와 필요한 허용 규칙 적용.** 기본 문제 3과 같은 정책 설계를 생성한 네임스페이스로 제한합니다. frontend→backend TCP 8080과 일반 CoreDNS의 UDP·TCP 통신을 허용하며 Service·컨테이너 포트를 일치시킵니다.

```bash
cat > "${SECURITY_LAB_DIR:?}/networkpolicies.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
EOF
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" apply -f "$SECURITY_LAB_DIR/networkpolicies.yaml" || exit 1
```

**5. 새 연결과 정상 동작 대조군 검증.** 정책 반영 후 무관한 클라이언트의 요청 거부를 관찰하고 허용된 frontend 요청과 DNS가 계속 동작하는지 확인합니다. 결과는 이 테스트 토폴로지에 한정됩니다. 예상 밖 실패는 정책·에이전트 상태와 로그를 함께 확인합니다.

```bash
# Wait briefly for the expected denied fresh connection; do not treat baseline failures as success.
SECURITY_DENY_OBSERVED=false
for ((attempt=1; attempt<=6; attempt++)); do
  if kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" -n "${SECURITY_NAMESPACE:?}" \
    exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ >/dev/null 2>&1; then
    sleep 2
  else
    SECURITY_DENY_OBSERVED=true
    break
  fi
done
[ "$SECURITY_DENY_OBSERVED" = true ] || {
  printf '%s\n' 'Expected deny was not observed; inspect policy enforcement.' >&2
  exit 1
}

# Positive controls after the denial: allowed application traffic and DNS must still work.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- nslookup backend || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" get networkpolicies
```

PSA가 네임스페이스의 Restricted 표준을 적용합니다. PSA 이상의 요구에는 Kyverno·Gatekeeper를 선택적으로 사용합니다. 여기서 시험한다면 기본 문제 6의 현재 API를 사용하고 네임스페이스 일치 조건도 바꿉니다. 다른 네임스페이스를 대상으로 한 정책 생성 성공이 이 실습 워크로드에 적용되었다는 뜻은 아닙니다.

**6. 불완전한 예제로 대체하지 말고 관련 통제 검토.** 읽기 전용 `Describe*` IAM 정책으로 AWS Load Balancer Controller를 운영할 수는 없습니다. 컨트롤러 버전과 일치하는 공식 정책 및 검토한 리소스·태그 조건을 사용합니다. 노드 IAM, IMDS, 보안 그룹, 애드온 자격 증명도 확인합니다. `maxUnavailable`은 시작한 관리형 노드 업데이트의 중단 범위를 제어할 뿐 정기 교체를 예약하지 않습니다. 별도로 검토한 유지 관리·업그레이드 계획을 사용합니다.

**7. 실습 네임스페이스 정리.** 기록한 UID를 사용하고 정리에 실패하면 전용 소유권·설정 파일을 보관합니다.

```bash
CURRENT_SECURITY_UID=$(kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  get namespace "${SECURITY_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_SECURITY_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_SECURITY_UID" = "${SECURITY_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" delete namespace "$SECURITY_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace UID mismatch; no deletion attempted.' >&2
  exit 1
fi
```

클러스터를 유지한다면 최종 엔드포인트·로깅 설정과 로그 보존·비용을 검토합니다. 교육용 클러스터를 제거한다면 수명 주기 안내에 따라 보존된 CloudWatch 로그와 별도 관리 리소스도 확인합니다. 네임스페이스 정리를 위해 연결된 KMS 키를 삭제하지 않습니다.

이 감사에서는 AWS 업데이트나 포드 네트워킹을 실행하지 않았습니다. 로컬 검사는 생성 매니페스트, 정책 로직, 실패·정리 보호 동작을 다룹니다. 운영 IAM, 라우팅, 승인, 가용성, 복구는 여전히 환경별 검증이 필요합니다.

참고: [네트워크 정책 요구사항](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [기본 봉투 암호화](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [API 엔드포인트 접근](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [컨트롤 플레인 로그](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

## 고급 주제

다음은 Amazon EKS 클러스터 생성에 관한 고급 주제에 대한 질문입니다. 이 섹션은 EKS 클러스터 생성의 심화 개념과 모범 사례에 대한 이해를 테스트합니다.

1. EKS IPv6 클러스터의 요구사항이 아닌 것은 무엇인가요?
   * A) IPv4·IPv6 주소를 가진 VPC·서브넷
   * B) 지원되는 CNI 구성과 IPv6 IAM 권한
   * C) 지원되는 Nitro 기반 EC2 노드 또는 Fargate
   * D) 별도의 IPv6 전용 EC2 인스턴스 계열

<details>
<summary>정답 보기</summary>

**정답: D) 별도의 IPv6 전용 EC2 인스턴스 계열**

EKS는 별도의 “IPv6 전용 인스턴스 계열”을 요구하지 않습니다. 그러나 **지원되는 Nitro 기반 EC2 노드 또는 Fargate**가 필요하므로 일반 EC2 유형이면 모두 가능하다는 설명은 잘못입니다.

**전제조건:**

1. **새** 클러스터 생성 시 IPv6 IP 계열을 선택합니다. 생성 후 변경할 수 없으며 기존 IPv4 클러스터의 `ENABLE_IPV6`를 바꿔도 클러스터가 전환되지는 않습니다.
2. VPC·서브넷에 IPv4·IPv6 CIDR을 연결하고 노드 서브넷의 IPv6 자동 할당을 켭니다. IPv6 경로, 보안 그룹, DNS, 관리 접근을 검토합니다. 서브넷 ID가 의도한 VPC·AZ에 속해야 합니다.
3. IPv6와 prefix delegation으로 구성된 지원 VPC CNI 릴리스를 사용합니다. 1.10.1은 역사적 최소 버전이며 현재 설치 권장 버전이 아닙니다. 현재 관리형 애드온을 오래된 1.10 매니페스트로 덮어쓰지 않습니다.
4. 가능하면 CNI 전용 워크로드 역할에 IPv6 IAM 권한을 부여합니다. IPv4의 `AmazonEKS_CNI_Policy`는 IPv6 정책이 아닙니다. eksctl IPv6·애드온 절차가 생성한 역할·정책을 확인합니다.

```bash
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,ipv4:CidrBlock,ipv6:Ipv6CidrBlockAssociationSet,autoIPv6:AssignIpv6AddressOnCreation}'
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --kubernetes-version 1.36
```

**예제:** 이미 준비된 기존 듀얼 스택 프라이빗 서브넷과 Nitro 기반 AL2023 노드 그룹을 사용합니다. 예제 ID와 퍼블릭 접근 CIDR을 바꿉니다. `kubernetesNetworkConfig.ipFamily: IPv6`는 올바른 eksctl 표기이며 EKS API는 소문자 `ipv6`를 사용합니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-lab
  region: us-west-2
  version: "1.36"
kubernetesNetworkConfig:
  ipFamily: IPv6
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
iam:
  withOIDC: true
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
managedNodeGroups:
  - name: ipv6-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
```

검토한 구성을 `ipv6-cluster.yaml`로 저장합니다. 환경에 맞는 정확한 호환 애드온 버전을 선택·기록합니다. 위에서 버전을 생략하면 도구가 호환 기본값을 선택하며 특정 과거 CNI 빌드를 설치하라는 뜻은 아닙니다.

```bash
# After reviewing real IDs, routing, IAM, access and compatible addon versions.
eksctl create cluster -f ipv6-cluster.yaml --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

이 구성이 기존 서브넷의 경로·IPv6 속성을 대신 준비하지는 않습니다. 노드·애드온 준비 상태뿐 아니라 생성된 액세스 항목과 CNI 권한도 확인합니다. 이 감사에서는 IPv6 클러스터를 생성하지 않았습니다.

**주소와 통신:**

- EKS는 포드 IPv6 주소를 노출하고 IPv6 ClusterIP를 할당합니다. 듀얼 스택 VPC라고 EKS 포드·Service가 듀얼 스택이 되는 것은 아닙니다.
- 포드 IPv6는 서브넷 주소 공간에서 할당되고 Service IPv6는 EKS가 `fc00::/7` 내부에서 할당한 unique-local 범위를 사용합니다. 서비스 CIDR이 항상 `fd00::/108`이라고 가정하지 않습니다.
- EC2 노드는 IPv4·IPv6 주소를 가집니다. 포드는 외부 IPv4 목적지 접근에 사용할, API에 표시되지 않는 호스트 로컬 IPv4 주소를 받을 수도 있으며 노드를 거쳐 source NAT됩니다. 프라이빗 노드의 IPv4 인터넷 접근에는 여전히 NAT가 필요할 수 있습니다.
- 네이티브 IPv6 인터넷 통신은 방향·보안 설계에 따라 인터넷 게이트웨이 또는 이그레스 전용 인터넷 게이트웨이를 사용할 수 있습니다. 모든 IPv6 클러스터에 이그레스 전용 게이트웨이가 필수는 아닙니다.
- IPv6 포드로 로드 밸런싱하려면 호환되는 컨트롤러·로드 밸런서의 IP 대상 구성이 필요합니다. 적절한 듀얼 스택 프런트엔드로 IPv4 클라이언트를 지원할 수도 있으므로 포드와 클라이언트의 IP 계열을 동일시하지 않습니다.
- EKS IPv6 클러스터는 Windows와 VPC CNI 사용자 지정 네트워킹을 지원하지 않습니다. IP 계열 선택 전에 스토리지 드라이버, 애드온, 외부 의존성 지원을 확인합니다.

```bash
aws eks describe-cluster --name "${IPV6_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.kubernetesNetworkConfig
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get pods -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get services -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -o wide
```

실제 주소를 확인하고 DNS 및 필요한 IPv6·IPv4 목적지 통신을 시험합니다. IPv6 주소가 보이는 것만으로 연결·가용성을 검증한 것은 아닙니다. 클러스터 수명 주기 절차에 따라 기록한 실습 리소스만 정리합니다.

참고: [EKS IPv6 동작](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html), [eksctl IPv6 실습](https://docs.aws.amazon.com/eks/latest/userguide/deploy-ipv6-cluster.html), [CNI IAM 역할](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html), [네트워크 구성 응답](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigResponse.html).

</details>

2. VPC CNI 사용자 지정 네트워킹의 주요 기능은 무엇인가요?
   * A) 같은 VPC 안에서 노드 기본 인터페이스와 다른 포드 서브넷·보안 그룹 사용
   * B) 모든 CIDR 중복 자동 방지
   * C) 모든 노드 간 연결 암호화
   * D) 컨트롤 플레인 조정 속도 향상

<details>
<summary>정답 보기</summary>

**정답: A) 같은 VPC 안에서 노드 기본 인터페이스와 다른 포드 서브넷·보안 그룹 사용**

VPC CNI 사용자 지정 네트워킹은 **Linux IPv4 EC2 포드가 노드와 같은 VPC의 다른 서브넷·보안 그룹을 사용**하도록 합니다. 포드 주소가 VPC에 연결된 CIDR 밖에서 할당되는 것은 아닙니다. 보조 VPC CIDR로 주소 공간을 늘릴 수 있지만 다른 네트워크와의 중복이 자동으로 방지되지는 않습니다.

기본 VPC CNI는 노드의 기본 서브넷에 보조 ENI를 만들고 기본 ENI 및 보조 ENI에서 사용 가능한 주소를 포드에 할당합니다. 사용자 지정 네트워킹에서는 일반 포드 IP를 `ENIConfig`로 구성한 보조 ENI에서 할당하고 기본 ENI는 해당 포드 IP 할당에 사용하지 않습니다. 호스트 네트워크 포드는 계속 호스트 네트워크를 사용합니다.

**구성 순서:**

1. 사용 가능한 IPv4 공간, 라우팅, 권한을 계획합니다. 보조 CIDR을 추가한다면 VPC 연결 제한과 연결된 네트워크의 중복을 확인합니다. AWS의 `100.64.0.0/10` 공유 주소 예제가 해당 환경에서도 미사용 범위라는 보장은 없습니다.
2. 노드의 기본 서브넷과 **같은 VPC·대응 AZ**에 포드 서브넷을 준비합니다. API·DNS·워크로드 의존성을 포함한 경로와 보안 그룹 규칙을 검토합니다.
3. 대상 포드 서브넷별로 `ENIConfig`를 만듭니다. 다음은 AZ당 서브넷 하나를 사용하는 예제이며 모든 ID를 바꿔야 합니다. 다른 배포가 소유한 기존 클러스터 범위 구성을 덮어쓰지 않습니다.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
    - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2b
spec:
  subnet: subnet-0123456789abcdef1
  securityGroups:
    - sg-0123456789abcdef0
```

4. CNI를 소유한 설치 경로에서 사용자 지정 네트워킹과 ENIConfig 선택을 구성합니다. EKS 관리형 애드온이라면 설치 버전의 스키마를 확인한 뒤 검토한 전체 구성에 다음 환경 설정을 병합합니다:

```yaml
# Merge with existing managed-addon configuration; do not discard other env values.
env:
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG: "true"
  ENI_CONFIG_LABEL_DEF: topology.kubernetes.io/zone
```

자체 관리형 DaemonSet의 동등한 변경은 다음과 같습니다. 클러스터 전체 CNI 동작에 영향을 주므로 일반적인 애플리케이션 배포가 아니라 계획된 전환에 포함해야 합니다:

```bash
# Self-managed CNI alternative, after preparing ENIConfig/subnets and a rollout plan.
# For an EKS-managed addon, use its supported configuration-values workflow instead.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  set env daemonset/aws-node AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true \
  ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  rollout status daemonset/aws-node --timeout=5m
```

5. 필요한 구성으로 대체 노드를 만들고 검증한 뒤 PDB를 고려한 드레인과 애플리케이션 시험으로 워크로드를 이동합니다. 환경 변수 변경만으로 기존 포드의 주소가 바뀌지는 않습니다. AWS는 사용자 지정 네트워킹에 새 노드를 권장합니다. 전환이 검증될 때까지 기존 용량을 유지합니다.

`ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`이면 ENIConfig 이름을 해당 AZ로 지정합니다. 한 AZ의 여러 포드 서브넷에 별도 구성이 필요하면 고유한 이름과 검토한 사용자 지정 노드 레이블·주석 매핑을 사용합니다. 기존 ENIConfig 주석 선택이 레이블 기반 선택보다 우선할 수 있습니다. 다른 AZ의 서브넷을 강제로 사용하려고 노드의 실제 토폴로지 레이블을 바꾸지 않습니다.

**용량·보안 제약:**

- 기본 ENI를 제외하므로 보조 IP 모드의 포드 용량이 줄어듭니다. Prefix delegation으로 주소 용량을 늘릴 수 있지만 서브넷의 prefix 여유 공간, 인스턴스 한도, kubelet `maxPods`도 중요합니다. 보편적인 값을 복사하지 말고 밀도를 계산·시험합니다.
- 기본 `AWS_VPC_K8S_CNI_EXTERNALSNAT=false`에서는 VPC에 연결된 CIDR 밖으로 가는 트래픽이 노드 기본 인터페이스를 거쳐 source NAT되며 해당 서브넷·보안 그룹을 사용합니다. ENIConfig 보안 그룹이 모든 외부 흐름을 통제한다고 가정하지 않습니다.
- 포드 보안 그룹과 함께 사용하면 해당 포드의 `SecurityGroupPolicy` 그룹이 ENIConfig 그룹보다 우선합니다. 지원되는 적용·SNAT 모드를 확인합니다.
- 사용자 지정 네트워킹 자체가 암호화나 테넌트 격리 경계는 아니며 별도 네트워크 설계 없이 중복 CIDR 라우팅 문제를 해결하지 않습니다.
- EKS IPv6·Windows 노드에는 지원되지 않습니다. Fargate는 EC2 노드 ENIConfig 매핑 대신 프로필로 서브넷을 선택합니다.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get eniconfigs
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -L topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "${APPLICATION_NAMESPACE:?}" get pods -o wide
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${POD_SUBNET_A:?}" "${POD_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,az:AvailabilityZone,cidr:CidrBlock,free:AvailableIpAddressCount}'
```

포드 IP와 대상 서브넷·노드 AZ를 대조하고 DNS·API 및 필요한 애플리케이션 통신을 확인합니다. ENIConfig 목록만으로 전환·격리를 검증할 수는 없습니다. 이 예제는 정적으로 검토했으며 CNI 변경, 노드 이동, 네트워크 벤치마크는 수행하지 않았습니다.

참고: [사용자 지정 네트워킹](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html), [구성·전환](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network-tutorial.html), [사용자 지정 네트워킹 고려사항](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html).

</details>

3. EKS Windows 워크로드의 필수 요구사항이 아닌 것은 무엇인가요?
   * A) Amazon Linux 관리형 노드 그룹 최소 두 개
   * B) Linux 전용 시스템 포드용 Linux 또는 Fargate 용량
   * C) 호환 Windows AMI와 컨테이너 이미지
   * D) Windows IPAM과 올바른 IAM·노드 인증

<details>
<summary>정답 보기</summary>

**정답: A) Amazon Linux 관리형 노드 그룹 최소 두 개**

Amazon Linux 관리형 노드 그룹 두 개가 필수인 것은 아닙니다. EKS에는 **CoreDNS처럼 Linux에서만 실행되는 시스템 포드를 위한 Linux 또는 Fargate 용량**이 필요하며 특정 Linux 배포판이나 별도 그룹 두 개를 요구하지는 않습니다. 최소 조건을 HA 설계로 간주하지 말고 복제본과 장애 도메인 배치를 계획합니다.

**Windows 전제조건:**

1. 현재 지원되는 EKS **IPv4** 클러스터와 호환 EKS 최적화 Windows AMI를 사용합니다. AWS는 Windows Server 2019·2022·2025 변형을 제공하며 이 예제는 의도적으로 2022를 선택했습니다. 오래된 Kubernetes 1.14·1.23을 현재 지원 기준으로 사용하지 않습니다.
2. 클러스터 IAM 역할의 `AmazonEKSVPCResourceController` 권한을 확인하고 `kube-system/amazon-vpc-cni` 구성에서 Windows IPAM을 활성화합니다.
3. 관리형 VPC 리소스 컨트롤러가 Windows IPAM을 수행하도록 합니다. 과거의 데이터 플레인 리소스 컨트롤러·admission webhook 매니페스트를 고정되지 않은 `master` URL로 설치하지 않습니다.
4. Windows 전용 노드 IAM 역할과 올바른 노드 인증을 사용합니다. API 인증은 `EC2_WINDOWS` 액세스 항목을 사용하며 관리형 노드 그룹은 노드 액세스 항목을 관리합니다. 기존 `aws-auth` 방식은 bootstrap·node 그룹 외에 필요한 `eks:kube-proxy-windows` 그룹을 유지합니다.

```bash
aws iam list-attached-role-policies --role-name "${EKS_CLUSTER_ROLE_NAME:?}"

# If missing, attach to the reviewed cluster role, not to every worker role.
aws iam attach-role-policy --role-name "$EKS_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

Windows IPAM 설정은 기존 VPC CNI 구성에 포함합니다. EKS·Helm이 소유한다면 ConfigMap 전체를 대체하지 말고 해당 소유자의 지원 설정을 사용합니다:

```yaml
# Relevant ConfigMap data; merge through the owning addon/Helm configuration.
data:
  enable-windows-ipam: "true"
```

**노드 그룹 예제:** 기존 클러스터, 서브넷, AMI 제공 여부, IAM을 검토한 뒤 `windows-nodegroup.yaml`로 저장합니다. 테인트로 일반 Linux 워크로드의 우발적 배치를 막고 Linux 워크로드 템플릿에도 Linux 선택 조건을 명시합니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: windows-ng
    amiFamily: WindowsServer2022FullContainer
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    privateNetworking: true
    taints:
      - key: example.com/os
        value: windows
        effect: NoSchedule
```

```bash
# Existing, supported IPv4 cluster with Windows IPAM and IAM prerequisites ready.
eksctl create nodegroup -f windows-nodegroup.yaml
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name windows-ng \
  --query 'nodegroup.{status:status,ami:amiType,role:nodeRole,health:health}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l kubernetes.io/os=windows -L node.kubernetes.io/windows-build
```

**워크로드 예제:** 사용하지 않는 `windows-lab` 네임스페이스를 만들고 노드의 Windows 빌드와 호환되는 이미지를 배포합니다. EKS 최적화 Windows AMI에는 kubelet, **Windows kube-proxy**, containerd 등 호스트 구성 요소가 포함됩니다. kube-proxy는 Linux 전용이 아닙니다.

기존 ServiceMonitor 진입점이 포함된 공식 IIS 이미지를 사용합니다. 이전 `dotnetbinaries.blob.core.windows.net`의 ServiceMonitor 다운로드 위치는 폐기되었으며 여기서는 포드 시작마다 IIS를 설치하거나 실행 파일을 내려받을 필요가 없습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-iis
  namespace: windows-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-iis
  template:
    metadata:
      labels:
        app: windows-iis
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
        kubernetes.io/arch: amd64
        node.kubernetes.io/windows-build: "10.0.20348"
      tolerations:
        - key: example.com/os
          operator: Equal
          value: windows
          effect: NoSchedule
      containers:
        - name: iis
          image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
          ports:
            - containerPort: 80
          startupProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              memory: 1Gi
```

이미지 태그는 Microsoft 이미지 README와 레지스트리 메타데이터로 확인했습니다. 이 감사에서 이미지 레이어를 내려받거나 Windows 워크로드를 실행하지는 않았습니다. 리소스 값은 예시입니다. 운영 사용 전에 실제 롤아웃·준비 상태, DNS, 애플리케이션 통신, 호스트·컨테이너 빌드 호환성을 확인합니다.

**지원 기능 범위:**

- Windows는 EKS Fargate 포드, EKS Auto Mode 노드, EKS Hybrid Nodes로 실행할 수 없습니다. EKS IPv6, VPC CNI 사용자 지정 네트워킹, 포드 보안 그룹도 지원하지 않습니다.
- 일반 Windows 포드는 Linux privileged 컨테이너와 다릅니다. Windows **HostProcess** 포드는 호스트 네트워킹을 사용할 수 있으므로 “Windows는 hostNetwork를 전혀 지원하지 않는다”는 설명은 잘못입니다. HostProcess에는 별도 높은 권한 검토가 필요합니다.
- Windows의 네트워킹·IP 용량은 Linux와 다릅니다. Linux 포드 밀도 계산을 그대로 적용하지 말고 단일 ENI 제한과 지원되는 prefix delegation을 확인합니다.
- Windows 지원 스토리지 드라이버를 선택하고 볼륨·경로 동작을 검증합니다. Linux hostPath 권한이나 모든 CSI 기능이 그대로 동작한다고 가정하지 않습니다.
- EKS 최적화 Windows 노드는 containerd를 사용하며 Linux 애플리케이션 이미지는 Linux 노드에 배치합니다. 혼합 OS 클러스터에서 시스템 애드온과 애플리케이션 배치를 확인합니다.

참고: [EKS Windows 지원](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html), [최적화 Windows AMI](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-windows-ami.html), [Microsoft IIS 이미지](https://github.com/microsoft/iis-docker), [Windows HostProcess](https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/).

</details>



4. EC2 인스턴스 메타데이터 요청에 세션 토큰을 요구하는 설정은 무엇인가요?
   * A) HttpTokens=required(IMDSv2 전용)
   * B) 169.254.169.254에 대한 보안 그룹 규칙
   * C) Kubernetes Node 레이블
   * D) 애플리케이션 ServiceAccount 이름만 지정

<details>
<summary>정답 보기</summary>

**정답: A) HttpTokens=required(IMDSv2 전용)**

IMDSv2를 필수로 설정하면(`HttpTokens: required`) 토큰 없는 IMDSv1 호출을 차단하고 심층 방어를 추가합니다. 그러나 모든 SSRF를 막거나 호스트를 공유하는 컨테이너 사이의 보안 경계를 만드는 것은 아닙니다.

**시작 템플릿 설정:** 다음은 EC2 `LaunchTemplateData` 조각이며 `managedNodeGroups.metadataOptions` 필드가 아닙니다. 홉 제한 1은 일반 포드가 노드 자격 증명 대신 IRSA·Pod Identity를 사용하는 조건입니다:

```json
{
  "MetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1,
    "HttpEndpoint": "enabled"
  }
}
```

홉 제한은 모든 메타데이터 요청이 아니라 IMDS 토큰 **PUT 응답**에 적용됩니다. 컨테이너가 정당하게 IMDSv2를 사용해야 한다면 홉 제한 2가 필요할 수 있습니다. 호환성을 확인하고 애플리케이션 권한은 워크로드 역할로 옮깁니다. 원인을 모르는 오류를 감추기 위해 제한을 높이지 않습니다.

지원되는 eksctl `launchTemplate.id/version` 필드로 검토한 기존 템플릿 버전을 사용합니다. 아래 ID는 실제 값으로 바꿔야 합니다. `--launch-template-name`은 문서화된 `eksctl create nodegroup` 인터페이스가 아닙니다:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-template-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    privateNetworking: true
```

**eksctl 대안:** 새 노드 그룹에서 지원되는 `disableIMDSv1`, `disablePodIMDS` 필드를 사용할 수 있습니다. 필요한 워크로드 자격 증명을 먼저 준비합니다. `disablePodIMDS`는 호스트 네트워크가 아닌 포드를 대상으로 하며 `withAddonPolicies`와 함께 사용할 수 없습니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-restricted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    disableIMDSv1: true
    disablePodIMDS: true
```

두 구성은 대안입니다. 실제 생성된 템플릿과 노드 메타데이터 설정을 검토합니다. 기본값은 인스턴스 시작 설정, 계정·리전 기본값, AMI 메타데이터 지원에 따라 결정되고 시작 설정이 우선합니다. 모든 AMI·노드 그룹의 기본 홉 제한이 1이라고 가정하지 않습니다.

**기존 노드:** 같은 사용자 지정 시작 템플릿의 새 버전을 관리형 노드 그룹 업데이트로 적용할 수 있습니다. IAM·SCP가 허용하면 실행 중이거나 중지된 개별 EC2 인스턴스의 옵션도 변경할 수 있지만 그것만으로 향후 대체 노드의 설정이 바뀌지는 않습니다:

```bash
# Inspect the explicitly reviewed instance before changing its metadata settings.
aws ec2 describe-instances --region "${EXAMPLE_REGION:?}" \
  --instance-ids "${REVIEWED_INSTANCE_ID:?}" \
  --query 'Reservations[].Instances[].{id:InstanceId,tags:Tags,metadata:MetadataOptions}'

# Separate transition step for a tested instance with compatible host agents.
aws ec2 modify-instance-metadata-options --region "$EXAMPLE_REGION" \
  --instance-id "$REVIEWED_INSTANCE_ID" --http-tokens required \
  --http-put-response-hop-limit 1 --http-endpoint enabled
```

옵션이 `applied` 상태가 되고 노드 에이전트, 이미지 풀, 워크로드 자격 증명이 정상인지 확인합니다. 애플리케이션이 IRSA를 사용한다는 이유만으로 메타데이터 엔드포인트 전체를 끄지 않습니다. 호스트 구성 요소는 노드 인스턴스 프로필과 메타데이터에 의존할 수 있습니다.

**추가 통제:**

- 노드 역할을 제한하고 애플리케이션에 별도 역할을 부여합니다. IRSA·Pod Identity 자체가 노드 IMDS에 대한 다른 접근을 막지는 않습니다.
- `hostNetwork` 포드는 IMDS에 접근할 수 있고 높은 권한의 호스트 워크로드는 포드 네트워크 격리를 우회할 수 있습니다. 포드 권한과 호스트 접근을 별도로 통제합니다.
- 보안 그룹은 인스턴스의 링크 로컬 메타데이터 서비스를 필터링하지 않습니다. 추가 호스트·네트워크 제한에는 실제 포드 경로 및 IPv4뿐 아니라 선택적인 IPv6 IMDS 엔드포인트(`fd00:ec2::254`)도 고려합니다. 이전의 임의 `PREROUTING -i eth0` DNAT 규칙은 일반적인 포드 IMDS 차단 수단으로 신뢰할 수 없습니다.
- 지원되는 SDK로 시험하되 세션 토큰·IAM 자격 증명 값을 출력하지 않습니다. Kubernetes 노드 레이블만으로 적용 여부를 판단하지 말고 실제 인스턴스 메타데이터 옵션을 확인합니다.

참고: [IMDS 옵션·우선순위](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html), [IMDSv2 동작](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html), [eksctl 보안 옵션](https://docs.aws.amazon.com/eks/latest/eksctl/security.html), [IRSA 격리 한계](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html).

</details>

5. EC2 노드 부트스트랩 구성의 목적에 해당하지 않는 것은 무엇인가요?
   * A) EKS 관리형 컨트롤 플레인 프로세스 수정
   * B) 사용자 지정 AMI에 설치된 검토한 소프트웨어 구성
   * C) 워크로드로 검증한 호스트 설정 적용
   * D) 지원되는 노드 그룹 레이블·테인트 설정

<details>
<summary>정답 보기</summary>

**정답: A) EKS 관리형 컨트롤 플레인 프로세스 수정**

노드 부트스트랩은 **노드 호스트**를 구성하며 EKS가 관리하는 API 서버·스케줄러·컨트롤러 관리자·etcd를 수정하지 않습니다. AL2023에서는 `nodeadm`과 지원되는 eksctl·시작 템플릿 경로를 사용합니다. 이전 AL2 `bootstrap.sh`·`kubeletExtraArgs` 예제는 적용되지 않습니다.

**소프트웨어 설치·구성:** 대상 OS·아키텍처에 맞는 검증된 패키지를 사용하고 가능하면 검토한 AMI에 포함합니다. 부팅마다 검증하지 않은 `latest` RPM을 내려받는 것은 재현 가능한 설치가 아닙니다. 호스트 에이전트에는 적절한 IAM 권한과 프라이빗·퍼블릭 서비스 연결도 필요합니다.

다음 선택적 AL2023 호스트 예제는 CloudWatch 에이전트가 이미 설치되어 있다고 가정합니다. 호스트 메모리·swap 지표를 구성하고 에이전트를 시작하므로 AWS 접근이 가능하면 과금되는 텔레메트리를 전송합니다. 관리 워크스테이션, Bottlerocket, Auto Mode에서 실행하는 절차가 아닙니다:

```bash
#!/bin/bash
# AL2023 host example: the reviewed AMI must already contain the verified agent package.
set -euo pipefail
AGENT_CTL=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl
test -x "$AGENT_CTL" || {
  printf '%s\n' 'CloudWatch agent is not installed in this AMI.' >&2
  exit 1
}
cat > /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "swap": {"measurement": ["swap_used_percent"]}
    }
  }
}
EOF
"$AGENT_CTL" -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json -s
```

**커널 조정:** 워크로드 근거와 실제 커널·CNI 요구사항을 사용합니다. 이전 예제 값은 검증되지 않은 조정 참고값으로 보존하며 보편적인 성능 권장값이 아닙니다:

| 예제 설정 | 이전 예제 값 | 검토 조건 |
| --- | --- | --- |
| `net.ipv4.ip_forward` | `1` | 노드·CNI 라우팅 요구사항 |
| `net.bridge.bridge-nf-call-iptables` | `1` | bridge 모듈과 CNI 경로의 필요 여부 |
| `net.ipv4.tcp_keepalive_time` | `600` | 애플리케이션·연결 타임아웃 동작 |
| `net.ipv4.tcp_max_syn_backlog`, `net.core.somaxconn`, `net.core.netdev_max_backlog` | `40000` | 실제 큐 압력·메모리·워크로드 측정 |
| `vm.max_map_count` | `262144` | 특정 애플리케이션의 매핑 요구사항 |

표 전체를 일괄 적용하는 노드 스크립트로 사용하지 않습니다. 기준 상태를 기록하고 테스트 그룹에서 변경을 검증하며 되돌릴 경로를 유지합니다.

**디스크:** `/dev/nvme1n1`이라고 가정한 장치에 `mkfs`를 실행하지 않습니다. NVMe 열거 순서는 안정적인 소유권 식별자가 아니며 필요한 데이터가 있는 장치일 수 있습니다. 볼륨 ID·serial로 대상 EBS 볼륨을 식별하고 새로 만든 임시 장치 또는 명시적으로 준비한 장치임을 확인한 뒤 파티션·파일 시스템·마운트를 검사합니다. 영속적인 마운트 구성에는 파일 시스템 UUID 같은 안정적인 식별자를 사용합니다.

```bash
# Read-only inspection on the specifically authorized test node.
lsblk --output NAME,PATH,TYPE,SIZE,FSTYPE,UUID,MOUNTPOINTS,SERIAL
findmnt
sysctl net.ipv4.ip_forward vm.max_map_count
```

영구 애플리케이션 데이터는 노드의 임시 디스크에 결합하기보다 적절한 CSI·PV 수명 주기를 사용합니다. 위의 검사 명령은 포맷하거나 마운트하지 않습니다.

**레이블·테인트·보안:** 관리형 노드 그룹의 레이블·테인트 필드와 소유한 도메인을 사용하고 공급자가 관리하는 토폴로지·노드 그룹 레이블을 덮어쓰지 않습니다. 호스트 강화는 검토한 AMI와 보안 그룹·CNI 설계로 구성합니다. 부트스트랩 중 임의의 SSH·방화벽 수정은 기존 규칙과 충돌하거나 접근을 끊을 수 있으며 완전한 보안 강화 절차가 아닙니다.

**시작 템플릿 사용자 데이터:** 사용자 지정 `ImageId` 없이 EKS가 AL2023 AMI를 선택하면 필수 기본 NodeConfig를 EKS가 제공합니다. 최소 MIME 사용자 지정은 다음과 같습니다:

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_BOOTSTRAP_EXAMPLE"

--EKS_BOOTSTRAP_EXAMPLE
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_BOOTSTRAP_EXAMPLE--
```

```bash
# Prepare real EC2 UserData JSON from the reviewed MIME file; no placeholder base64.
BOOTSTRAP_DIR=$(mktemp -d /tmp/eks-bootstrap-example.XXXXXX)
: "${BOOTSTRAP_DIR:?}"
jq -n --rawfile data "${REVIEWED_MIME_FILE:?}" \
  '{UserData:($data|@base64)}' > "$BOOTSTRAP_DIR/launch-template-data.json" || exit 1
aws ec2 create-launch-template --region "${EXAMPLE_REGION:?}" \
  --launch-template-name "${NEW_LAUNCH_TEMPLATE_NAME:?}" \
  --version-description "Reviewed AL2023 customization" \
  --launch-template-data "file://$BOOTSTRAP_DIR/launch-template-data.json" \
  --query 'LaunchTemplate.{id:LaunchTemplateId,version:LatestVersionNumber}'
```

고급 문제 4처럼 반환된 템플릿 ID·버전을 `managedNodeGroups[].launchTemplate`에 지정합니다. eksctl이 생성한 구성 밖에서 사용자 지정 AMI ID를 사용한다면 기본 문제 5의 완전한 클러스터 NodeConfig도 제공합니다. kubelet을 수동 시작하거나 `nodeadm init`을 중복 호출하지 않습니다.

**eksctl 대안:** 다음 구성은 지원되는 노드 그룹 필드와 디렉터리 생성 pre-bootstrap 명령을 사용합니다. 검토한 호스트 사용자 지정만 추가합니다. `preBootstrapCommands`는 셸 명령을 담고, AL2023에서 NodeConfig 사용자 지정을 위한 `overrideBootstrapCommand`는 NodeConfig YAML을 담습니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
      example.com/node-type: compute
    taints:
      - key: dedicated
        value: compute
        effect: NoSchedule
    preBootstrapCommands:
      - install -d -m 0755 /opt/company
```

이 예제는 프로덕션 노드 절차로 부팅 검증하지 않았습니다. 실제 환경에서 패키지 출처, nodeadm·kubelet의 적용 구성, 시작 실패, 네트워킹, 워크로드 상태를 확인합니다.

**CoreDNS는 데이터 플레인 워크로드·애드온**이며 일반적으로 Linux EC2 또는 지원되는 Fargate 용량의 Deployment로 실행됩니다. EKS가 관리하는 컨트롤 플레인 프로세스가 아니므로 애드온·Kubernetes 경로로 구성합니다. 로깅처럼 EKS API가 제공하는 컨트롤 플레인 설정은 노드 사용자 데이터와 별개입니다.

참고: [AL2023 초기화](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [eksctl 부트스트랩](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [시작 템플릿 제약](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [CloudWatch 에이전트 구성](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html).

</details>
