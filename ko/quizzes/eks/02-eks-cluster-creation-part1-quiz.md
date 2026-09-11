# EKS 클러스터 생성 퀴즈 - Part 1

> **마지막 업데이트**: 2026년 9월 11일

> 명령은 각각 독립된 예제이며 처음부터 끝까지 실행하는 스크립트가 아닙니다. 전용 교육용 계정·클러스터, 검토한 IAM 권한, 전용 임시 kubeconfig(`EXAMPLE_KUBECONFIG`)를 사용하고 예제 ID와 필수 변수를 바꿉니다. 생성 명령은 비용을 발생시킵니다. 이번 감사는 출처·구문·로컬 예제를 검증했으며 AWS 프로비저닝이나 애플리케이션 가용성 검증을 수행하지 않았습니다.

이 퀴즈는 Amazon EKS 클러스터 생성과 관련된 개념, 도구, 모범 사례에 대한 이해를 테스트합니다. 클러스터 생성 방법, VPC 구성, 노드 그룹 설정 등의 주제를 다룹니다.

## 기본 개념 문제

1. EKS 컨트롤 플레인을 직접 프로비저닝하는 내장 명령이 없는 도구는 무엇인가요?
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>정답 보기</summary>

**정답: D) kubectl**

kubectl은 Kubernetes API 리소스를 관리하며 EKS 프로비저닝 내장 명령은 없습니다. 기존 관리 클러스터의 ACK 같은 인프라 컨트롤러가 kubectl로 제출한 리소스를 EKS 클러스터로 조정할 수는 있지만, 이는 컨트롤러 통합이며 kubectl 자체의 AWS 작업은 아닙니다.

Amazon EKS 클러스터를 생성하는 데 사용할 수 있는 도구는 다음과 같습니다:

1. **AWS Management Console**:
   * 웹 인터페이스를 통해 EKS 클러스터를 생성할 수 있습니다.
   * 시각적인 방식으로 클러스터 구성 요소를 설정할 수 있어 초보자에게 적합합니다.
   * 단계별 마법사를 통해 클러스터 생성 과정을 안내합니다.
2.  **AWS CLI**:

    * 명령줄에서 EKS 클러스터를 생성할 수 있습니다.
    * `aws eks create-cluster` 명령을 사용합니다.
    * 스크립트 및 자동화에 적합합니다.

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * EKS 클러스터 생성을 위해 특별히 설계된 명령줄 도구입니다.
    * Weaveworks에서 시작했으며 현재 프로젝트는 eksctl-io 조직에서 AWS·커뮤니티의 기여로 유지됩니다.
    * 단일 명령으로 클러스터를 생성할 수 있습니다.

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Infrastructure as Code (IaC) 도구**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    이러한 도구를 사용하면 코드로 EKS 클러스터를 정의하고 배포할 수 있습니다.

kubectl은 클러스터가 생성된 후에 Kubernetes 리소스(포드, 서비스, 배포 등)를 관리하는 데 사용됩니다. EKS 클러스터에 연결하려면 승인된 kubeconfig를 구성해야 하며 보통 `aws eks update-kubeconfig`를 사용합니다.

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

이후에 kubectl을 사용하여 클러스터 리소스를 관리할 수 있습니다.

</details>

2. Amazon EKS 클러스터를 생성할 때 필수적으로 지정해야 하는 VPC 구성 요소는 무엇인가요?
   * A) 퍼블릭 서브넷만
   * B) 프라이빗 서브넷만
   * C) 최소 2개의 가용 영역에 걸친 서브넷
   * D) NAT 게이트웨이

<details>

<summary>정답 보기</summary>

**정답: C) 최소 2개의 가용 영역에 걸친 서브넷**

**설명:** Amazon EKS 클러스터를 생성할 때 필수적으로 지정해야 하는 VPC 구성 요소는 최소 2개의 가용 영역에 걸친 서브넷입니다. 이는 EKS 클러스터의 고가용성을 보장하기 위한 AWS의 요구 사항입니다.

**EKS 클러스터 VPC 요구 사항:**

1. **최소 2개의 가용 영역(AZ)에 서브넷 필요**:
   * EKS 컨트롤 플레인은 여러 가용 영역에 걸쳐 배포되므로, 클러스터 생성 시 최소 2개의 가용 영역에 서브넷을 지정해야 합니다.
   * 리전 컨트롤 플레인 가용성을 위한 조건입니다. 워크로드 가용성에는 복제본 배치·용량·스토리지·종속 서비스 계획도 필요합니다.
2. **서브넷 유형**:
   * 퍼블릭 서브넷만 사용하거나, 프라이빗 서브넷만 사용하거나, 또는 퍼블릭과 프라이빗 서브넷을 혼합하여 사용할 수 있습니다.
   * 프로덕션 환경에서는 보안을 위해 프라이빗 서브넷에 워커 노드를 배치하고, 퍼블릭 서브넷은 로드 밸런서용으로 사용하는 것이 권장됩니다.
3. **서브넷 CIDR 크기**:
   * 클러스터 서브넷마다 EKS용 IP가 최소 6개 남아 있어야 하며 AWS는 16개 이상을 권장합니다. 노드·Pod·로드 밸런서 용량은 별도로 계획합니다.
   * EKS는 각 포드에 VPC IP 주소를 할당하므로, 예상되는 포드 수에 따라 충분히 큰 CIDR 블록이 필요합니다.
4. **태그 요구 사항**:
   * 아래 태그는 특정 통합의 검색·소유권에 관련되며 모든 EKS 생성의 필수 조건은 아닙니다:
     * 레거시 또는 컨트롤러별 소유권 태그: `kubernetes.io/cluster/<cluster-name>: shared`
     * 퍼블릭 서브넷: `kubernetes.io/role/elb: 1`
     * 프라이빗 서브넷: `kubernetes.io/role/internal-elb: 1`

**VPC 구성 예시 (eksctl 사용):**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["203.0.113.10/32"]
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
    public:
      us-west-2a:
        id: subnet-0123456789abcdef2
      us-west-2b:
        id: subnet-0123456789abcdef3
```

**AWS CLI를 사용한 VPC 구성:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

NAT 게이트웨이는 가능한 인터넷 출구 중 하나입니다. 필요한 VPC 엔드포인트·미러 이미지·사설 연결 경로가 있다면 인터넷 없이 운영할 수 있습니다. 서브넷을 프라이빗으로 배치하는 것과 인터넷 출구를 제거하는 것은 별도 결정입니다. 예시 VPC/서브넷/CIDR은 실제 값으로 바꿉니다.

</details>

3. 일반 EKS 컨트롤 플레인과 EC2 워커 노드를 함께 구성할 때 역할 구분으로 올바른 것은 무엇인가요?
   * A) 클러스터 역할만 필요
   * B) EC2 노드 역할만 필요
   * C) 별도의 클러스터 역할과 EC2 노드 역할
   * D) Fargate 실행 역할로 모두 대체

<details>
<summary>정답 보기</summary>

**정답: C) 별도의 클러스터 역할과 EC2 노드 역할**

클러스터 역할은 `eks.amazonaws.com`을 신뢰하고 EKS가 클러스터 인프라를 관리할 권한을 제공합니다. 일반 EKS에는 `AmazonEKSClusterPolicy` 또는 동등한 범위가 필요합니다. EC2 노드 역할은 `ec2.amazonaws.com`을 신뢰하고 인스턴스 프로필로 제공됩니다. 관리형 노드 그룹의 인스턴스 프로필은 EKS가 구성하며, 노드 부트스트랩이 IAM 역할을 생성하는 것은 아닙니다.

EC2 노드의 기본 정책은 `AmazonEKSWorkerNodePolicy`와 `AmazonEC2ContainerRegistryPullOnly` 또는 동등한 최소 권한입니다. CNI 권한도 필요하며 IRSA/Pod Identity의 별도 역할을 권장합니다. 그것을 사용하지 않으면 노드 역할에 해당 CNI 권한이 필요합니다. IPv4의 `AmazonEKS_CNI_Policy`를 IPv6에 그대로 적용하지 않습니다. 스토리지·로드 밸런서·로깅 컨트롤러 권한을 모든 노드에 일괄 부여하는 것은 필수 조건이 아닙니다.

다음은 새 일반 클러스터/노드 역할의 예제입니다. 승인된 계정·역할에서만 실행하고 오류 발생 시 중단합니다. 기존 역할과 충돌하면 해당 역할에 정책을 덧붙이지 않습니다.

```bash
IAM_EXAMPLE_DIR=$(mktemp -d /tmp/eks-iam-example.XXXXXX)
: "${IAM_EXAMPLE_DIR:?}"
: "${NEW_CLUSTER_ROLE_NAME:?Choose an unused role name for this example}"
: "${NEW_NODE_ROLE_NAME:?Choose a different unused role name}"
cat > "$IAM_EXAMPLE_DIR/cluster-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "eks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
cat > "$IAM_EXAMPLE_DIR/node-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
# Attach policies only after successfully creating the new role.
aws iam create-role --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/cluster-trust.json" &&
aws iam attach-role-policy --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

if aws iam create-role --role-name "$NEW_NODE_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/node-trust.json"; then
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy &&
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
fi
```

`CreateCluster`만 호출하여 제어면을 만들 때는 EC2 노드 역할이 아직 필요하지 않습니다. EC2 노드 구성 시 추가합니다. Fargate는 별도의 Pod 실행 역할을 쓰며 앱의 AWS 권한과 다릅니다. Auto Mode는 클러스터의 추가 정책·`sts:TagSession`, 최소 노드 정책을 사용하는 별도 역할 구성이 필요합니다. 프로비저닝 사용자의 `iam:PassRole` 등 권한도 따로 검토합니다.

[Node role requirements](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Auto Mode roles](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

</details>

4. eksctl을 사용하여 EKS 클러스터를 생성할 때, 다음 중 올바른 명령어는 무엇인가요?
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>정답 보기</summary>

**정답: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**설명:** eksctl을 사용하여 EKS 클러스터를 생성하는 올바른 명령어는 `eksctl create cluster --name my-cluster --region us-west-2`입니다. 이 명령어는 지정된 이름과 리전으로 기본 설정의 EKS 클러스터를 생성합니다.

**eksctl 명령어 구조:**

* `eksctl`: 기본 명령어
* `create`: 리소스를 생성하는 작업
* `cluster`: 생성할 리소스 유형(클러스터)
* `--name my-cluster`: 클러스터 이름 지정
* `--region us-west-2`: AWS 리전 지정

**기본 클러스터 생성 명령어:**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

기본값은 eksctl 버전에 따라 달라집니다. 아래 파일에서 EKS 버전·AL2023·노드 수·엔드포인트를 명시합니다. 새 VPC·노드·IAM 리소스가 만들어질 수 있으므로 승인된 테스트 계정에서 구성과 비용을 먼저 검토합니다.

**추가 옵션을 포함한 고급 명령어:**

```bash
eksctl create cluster \
  --name my-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --with-oidc \
  --node-ami-family AmazonLinux2023 \
  --node-private-networking \
  --managed
```

**구성 파일을 사용한 클러스터 생성:**

```bash
# cluster.yaml 파일 생성
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR:?Set your approved client CIDR}"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    amiFamily: AmazonLinux2023
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: false
EOF

# 구성 파일을 사용한 클러스터 생성
eksctl create cluster -f cluster.yaml
```

**다른 옵션들의 문제점:**

* `eksctl create-cluster`: 잘못된 명령어 형식입니다. eksctl에서는 하이픈(-)이 아닌 공백을 사용하여 명령어를 구분합니다.
* `eksctl new cluster`: 'new'는 eksctl의 유효한 명령어가 아닙니다.
* `eksctl start cluster`: 'start'는 eksctl의 유효한 명령어가 아닙니다. 문서화된 수명 주기 명령을 사용해야 합니다.

eksctl은 EKS 클러스터 관리를 위한 다양한 명령어를 제공합니다:

* `eksctl create cluster`: 새 클러스터 생성
* `eksctl get cluster`: 클러스터 목록 조회
* `eksctl upgrade cluster`: 클러스터 업데이트
* `eksctl delete cluster`: 클러스터 삭제
* `eksctl create nodegroup`: 노드 그룹 추가
* `eksctl scale nodegroup`: 노드 그룹 크기 조정

</details>

5. 새 EKS 클러스터의 Kubernetes 버전은 어디에서 선택하나요?
   * A) 최신 업스트림 버전만
   * B) 항상 최신과 이전 2개만
   * C) 대상 리전에서 EKS가 제공하는 표준/연장 지원 버전
   * D) 모든 Kubernetes 버전

<details>
<summary>정답 보기</summary>

**정답: C) 대상 리전에서 EKS가 제공하는 표준/연장 지원 버전**

EKS 출시일부터 표준 지원 **14개월**, 이어서 추가 요금의 연장 지원 **12개월**을 제공합니다. 2026년 9월 11일 공식 목록은 표준 **1.34–1.36**, 연장 **1.31–1.33**입니다. 업스트림 1.37 출시만으로 EKS 지원을 추정하지 않습니다. 새 클러스터를 만들 수 있는 버전은 대상 리전의 EKS 목록으로 확인합니다.

연장 지원은 기본 활성화되며 지원 정책과 종료 시점에 따라 제어면이 자동 업그레이드될 수 있습니다. 노드·애드온 갱신은 별도로 계획합니다. 지원 종료 날짜는 AWS 공지를 따르고 업그레이드를 미루는 근거로 최대 지원 기간을 사용하지 않습니다.

다음은 버전 조회·구성 생성·AWS 생성 API·기존 클러스터 업그레이드의 서로 다른 예시입니다. 승인된 대상과 필요한 역할·서브넷·CIDR을 준비하고 생성/업그레이드 명령을 무조건 연속 실행하지 않습니다.

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table

# Generate a versioned config for review; this does not create the cluster.
EKS_VERSION_DIR=$(mktemp -d /tmp/eks-version.XXXXXX)
: "${EKS_VERSION_DIR:?}"
eksctl create cluster --name "${NEW_CLUSTER_NAME:?}" --region "$EXAMPLE_REGION" \
  --version 1.36 --dry-run > "$EKS_VERSION_DIR/version-example.yaml"
# Review all generated defaults, AMI, endpoint CIDRs and costs before creating.

# AWS API creation uses --version, not --kubernetes-version.
aws eks create-cluster --name "$NEW_CLUSTER_NAME" --region "$EXAMPLE_REGION" \
  --version 1.36 --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API \
  --resources-vpc-config "subnetIds=${SUBNET_A:?},${SUBNET_B:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"

# Updating an existing control plane is a separate operation.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query cluster.version
# Only after upgrade-readiness checks and choosing the next supported minor:
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

제어면 전방 업그레이드는 한 번에 한 마이너씩 수행해야 합니다. 기능 요구 사항, 남은 지원 기간과 애드온/워크로드 호환성을 함께 검토합니다. 이전 버전이 항상 더 안정적이라는 가정 대신 실제 대상 버전으로 검증합니다. 애드온 메타데이터의 버전 문자열을 grep하는 것은 클러스터 지원 목록 조회를 대신하지 못합니다.

[EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

</details>

6. EKS 워크로드의 컴퓨팅을 자체적으로 프로비저닝하지 않는 것은 무엇인가요?
   * A) 관리형 노드 그룹
   * B) 자체 관리형 노드 그룹
   * C) Fargate 프로필
   * D) Kubernetes 네임스페이스

<details>

<summary>정답 보기</summary>

**정답: D) Kubernetes 네임스페이스**

네임스페이스는 Kubernetes 리소스를 구분하지만 컴퓨팅을 제공하지는 않습니다. 관리형 EC2 노드 그룹·자체 관리형 EC2 노드·Fargate 프로필은 유효한 실행 방식입니다. EKS Auto Mode도 관리형 노드를 프로비저닝하며 Hybrid Nodes는 고객이 관리하는 온프레미스/엣지 용량을 연결합니다. 모든 방식이 관리형 노드 그룹 API를 사용하는 것은 아닙니다.


아래 생성 명령은 기존 클러스터와 사용하지 않는 그룹·프로필 이름에 적용하는 대안입니다. 필수 변수를 검토한 값으로 설정하고 CNI·노드 권한과 프라이빗 서브넷 연결을 확인합니다. Fargate에는 포드 실행 역할, 호환 포드, 프라이빗 서브넷이 필요하며 프로필 자체가 애플리케이션 포드를 만들지는 않습니다.

**1. 관리형 노드 그룹 (Managed Node Groups):**

* **특징**:
  * AWS에서 노드의 프로비저닝 및 수명 주기 관리
  * 자동 EC2 인스턴스 생성 및 등록
  * 자동 ASG(Auto Scaling Group) 구성
  * 운영자가 시작하는 노드 Kubernetes 버전 업데이트
  * EC2 헬스 교체 및 지원되는 상태 신호·설정에 따른 EKS 노드 복구
  * 운영자가 시작하는 관리형 AMI 업데이트
*   **생성 방법**:

    ```bash
    # eksctl을 사용한 관리형 노드 그룹 생성
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-mng --managed --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5

    # AWS CLI를 사용한 관리형 노드 그룹 생성
    aws eks create-nodegroup \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --nodegroup-name my-mng --ami-type AL2023_x86_64_STANDARD \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --instance-types t3.medium \
      --scaling-config minSize=1,maxSize=5,desiredSize=3 \
      --node-role "${NODE_ROLE_ARN:?}"
    ```

**2. 자체 관리형 노드 그룹 (Self-managed Node Groups):**

* **특징**:
  * 사용자가 노드의 프로비저닝 및 수명 주기 관리
  * 더 많은 사용자 지정 옵션
  * 특수 AMI 또는 부트스트랩 스크립트 사용 가능
  * 특정 인스턴스 유형 또는 구성 요구 사항에 적합
*   **생성 방법**:

    ```bash
    # eksctl을 사용한 자체 관리형 노드 그룹 생성
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-smng --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5 \
      --managed=false

    # CloudFormation 또는 EC2 시작 템플릿을 사용하여 수동으로 생성할 수도 있습니다.
    ```

**3. Fargate 프로필 (Fargate Profiles):**

* **특징**:
  * 서버리스 컨테이너 실행 환경
  * 노드 관리 불필요
  * 포드 단위로 리소스 할당 및 비용 청구
  * 특정 네임스페이스 및 레이블에 기반한 선택적 실행
*   **생성 방법**:

    ```bash
    # eksctl을 사용한 Fargate 프로필 생성
    eksctl create fargateprofile \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-fargate-profile \
      --namespace my-namespace \
      --labels app=my-app

    # AWS CLI를 사용한 Fargate 프로필 생성
    aws eks create-fargate-profile \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --fargate-profile-name my-fargate-profile \
      --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --selectors '[{"namespace":"my-namespace","labels":{"app":"my-app"}}]'
    ```

**각 옵션의 비교:**

| 특성 | 관리형 노드 그룹 | 자체 관리형 노드 | Fargate |
| --- | --- | --- | --- |
| 인프라 관리 | AWS가 교체 과정을 관리, 운영자가 업데이트·스케일러 구성 | 운영자가 AMI·부트스트랩·수명 주기 관리 | 호스트는 AWS가 관리, 앱·프로필·요청은 사용자 관리 |
| 비용 | 인스턴스·사용률·약정·운영 조건에 따라 평가 | 최적화 및 운영 비용을 함께 평가 | 할당된 Pod 크기·실행 시간·제약을 비교 |
| 확장 | 별도 노드 오토스케일러/정책 필요 | 별도 자동화 필요 | 프로필에 맞는 Pod별 컴퓨팅 제공; 앱 복제본 확장은 별도 |

Auto Mode의 NodePool과 Fargate 프로필은 EC2 관리형 노드 그룹과 다른 리소스입니다. Fargate에도 워크로드·보안·가용성 관리가 필요하며 계산 비용이 항상 더 높거나 낮다고 단정할 수 없습니다.

</details>

7. 새 EKS 1.36 노드용 AWS 게시 EKS 최적화 AMI 계열이 아닌 것은 무엇인가요?
   * A) Amazon Linux 2023
   * B) Bottlerocket
   * C) Windows Server 2022
   * D) Ubuntu Core

<details>
<summary>정답 보기</summary>

**정답: D) Ubuntu Core**

Ubuntu Core를 AWS 게시 EKS 최적화 AMI로 취급하지 않습니다. Ubuntu Server용 Canonical 이미지나 사용자 지정 AMI는 별도의 이미지 게시자·호환성·지원 경로이며, Ubuntu Core와 동일하지 않습니다.

**현재 예제의 선택지**

- **AL2023**: EKS 최적화 AMI와 `nodeadm` 부트스트랩을 사용합니다. Kubernetes 버전·CPU 아키텍처·리전·CNI 호환성을 확인합니다.
- **Bottlerocket**: 컨테이너 중심 OS이며 설정 방식과 업데이트 절차가 일반 Linux 노드와 다릅니다.
- **Windows**: 지원되는 Windows Server AMI와 호스트/컨테이너 버전을 맞추고 Windows 네트워킹·인증·시스템 워크로드 요구 사항을 준비합니다. Auto Mode/Fargate용 Windows 노드 예제가 아닙니다.

**AL2는 과거 환경의 이전 대상**입니다. EKS 최적화 AL2 AMI 게시/지원은 2025년 11월 26일, AL2 OS 지원은 2026년 6월 30일에 종료되었습니다. EKS Kubernetes 연장 지원이 AL2 지원을 연장하지 않습니다. 신규 EKS 1.36 배포에 AL2를 권장하지 않습니다.

```bash
# Alternative examples; create only the reviewed group needed by your workload.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}"   --name al2023-nodes --managed --node-ami-family AmazonLinux2023 --node-private-networking

eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name bottlerocket-nodes --managed --node-ami-family Bottlerocket --node-private-networking

# Only after preparing the cluster for Windows:
eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name windows-nodes --managed --node-ami-family WindowsServer2022FullContainer --node-private-networking
```

사용자 지정 AMI는 관리형 노드 그룹의 시작 템플릿에서도 사용할 수 있습니다. AMI를 고정하면 해당 OS/런타임·클러스터 메타데이터·부트스트랩 구성을 검증해야 합니다. 임의 Ubuntu 이미지에 `docker.io`만 설치해 EKS 노드가 된다고 가정하지 않습니다. Canonical의 대상 EKS 버전 이미지와 검토한 eksctl/시작 템플릿 구성을 사용합니다. 시작 템플릿의 `ImageId`, nodegroup `amiType`, 사용자 데이터 병합 제약은 고급 문제에서 구분합니다.

이미지 선택은 보안 업데이트, 실제 워크로드 성능, Kubernetes/드라이버 호환성, 운영 방법과 GPU 등 특수 요구 사항에 따라 검토합니다.

[AL2 transition](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html) · [AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [Windows prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)

</details>

8. CreateCluster API에서 엔드포인트 접근 설정을 생략하면 기본값은 무엇인가요?
   * A) 퍼블릭 활성, 프라이빗 비활성
   * B) 프라이빗만 활성
   * C) 두 엔드포인트 모두 활성
   * D) 생성 후 접근 설정 변경 불가

<details>
<summary>정답 보기</summary>

**정답: A) 퍼블릭 활성, 프라이빗 비활성**

API 기본값은 퍼블릭 활성·프라이빗 비활성입니다. eksctl, CDK나 콘솔 생성 경로는 다른 값을 명시할 수 있으므로 모든 도구의 기본값으로 일반화하지 않습니다. 접근 설정은 생성 후에도 변경할 수 있습니다.

| 퍼블릭 | 프라이빗 | 접근 경로 |
| --- | --- | --- |
| 켬 | 끔 | 공개 엔드포인트와 publicAccessCidrs; 노드/CI의 실제 출구 주소도 검토 |
| 켬 | 켬 | VPC 내 요청은 사설 경로, 외부는 허용된 공개 CIDR |
| 끔 | 켬 | VPC 또는 연결된 네트워크의 사설 경로만 사용 |
| 끔 | 끔 | 유효하지 않은 구성 |

**클러스터 보안 그룹은 프라이빗 엔드포인트와 kubelet 경로를 제어하며 퍼블릭 엔드포인트를 제한하지 않습니다.** `publicAccessCidrs`는 공개 엔드포인트용이고 사설 접근에는 적용되지 않습니다. 네트워크 도달성과 별개로 인증·권한 부여가 필요합니다. IPv4 예제의 CIDR을 실제 승인된 클라이언트 출구 주소로 바꿉니다.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.resourcesVpcConfig

# Select the actual approved client egress CIDR, not an arbitrary example range.
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text)
: "${ENDPOINT_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

이전 업데이트가 `Successful`인지 확인하고 관리자/CI 네트워크에서 사설 DNS·라우팅·API 접근을 검증한 후에만 공개 접근을 끕니다. 연속된 비동기 요청을 즉시 실행하지 않으며 두 플래그를 하나의 요청에서 함께 설정합니다.

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

프라이빗 API 접근과 인터넷 출구 제거는 별도 설계입니다. 보안 수준은 신원·네트워크·운영 통제를 함께 평가하며 프라이빗 설정만으로 가용성이나 보안을 보장하지 않습니다. VPN/Direct Connect/관리 호스트와 그 연결 비용도 고려합니다. IPv6 엔드포인트와 Hybrid Nodes는 별도 DNS·CIDR 제약이 있으므로 공식 지침을 확인합니다.

[Cluster endpoint access controls](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)

</details>

9. Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 선택할 때 고려해야 할 사항이 아닌 것은 무엇인가요?
   * A) 워크로드 요구 사항 (CPU, 메모리, 스토리지)
   * B) 비용 최적화
   * C) 로컬 kubeconfig 컨텍스트 별칭
   * D) 인스턴스 세대 (예: t3 vs t2)

<details>

<summary>정답 보기</summary>

**정답: C) 로컬 kubeconfig 컨텍스트 별칭**

kubeconfig 별칭은 로컬 클라이언트의 이름이며 인스턴스 성능·가격·가용성을 바꾸지 않습니다. 반면 요구되는 AZ에서 해당 인스턴스 유형을 제공하는지, 실제 용량과 할당량이 충분한지는 중요한 선택 조건입니다.

**노드 그룹 인스턴스 유형 선택 시 실제 고려 사항:**

1. **워크로드 요구 사항 (CPU, 메모리, 스토리지)**:
   * 애플리케이션의 리소스 요구 사항에 맞는 인스턴스 유형 선택
   * 메모리 집약적 워크로드: r5, r6g 등의 메모리 최적화 인스턴스
   * 컴퓨팅 집약적 워크로드: c5, c6g 등의 컴퓨팅 최적화 인스턴스
   * 균형 잡힌 워크로드: m5, m6g 등의 범용 인스턴스
   * GPU 워크로드: p3, g4dn 등의 가속 컴퓨팅 인스턴스
2. **비용 최적화**:
   * 온디맨드 vs 스팟 인스턴스
   * 예약 인스턴스 또는 Savings Plans 활용
   * 적절한 크기의 인스턴스 선택 (오버프로비저닝 방지)
   * ARM 기반 Graviton 인스턴스(예: m6g, c6g)를 통한 비용 절감
3. **인스턴스 세대**:
   * 실제 워크로드에서 세대별 가격·성능을 비교
   * 버스터블 계열은 CPU 크레딧과 기본 성능도 고려
   * 최신 세대는 향상된 네트워킹, 스토리지 성능 등의 기능 제공
4. **네트워킹 요구 사항**:
   * 향상된 네트워킹 지원 (ENA, EFA 등)
   * 네트워크 대역폭 요구 사항
   * 인스턴스당 최대 포드 수와 관련된 네트워킹 제한
5. **스토리지 요구 사항**:
   * 로컬 인스턴스 스토리지 필요 여부 (예: i3, d3 인스턴스)
   * EBS 최적화 지원
   * 스토리지 처리량 및 IOPS 요구 사항
6. **CPU 아키텍처**:
   * x86 (Intel, AMD) vs ARM (AWS Graviton)
   * 애플리케이션 호환성 고려

**가용 영역과 노드 그룹 배포:**

필요한 AZ 범위는 사용할 수 있는 인스턴스 유형에도 영향을 줍니다. 카탈로그에 있는 유형이라고 즉시 용량이 확보되는 것은 아닙니다:

* 노드 그룹은 여러 가용 영역에 걸쳐 배포하여 고가용성 확보
* 노드 용량과 Pod 토폴로지 분산을 계획하고 실제 배치를 확인
* 리전 내 모든 가용 영역 또는 특정 가용 영역 선택 가능

```bash
# 특정 가용 영역에 노드 그룹 배포
eksctl create nodegroup \
  --cluster "${EXAMPLE_CLUSTER:?}" --region us-west-2 \
  --name my-nodegroup --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

**인스턴스 유형 선택 예시:**

1. **웹 애플리케이션 서버**:
   * 범용 인스턴스: t3.medium, m5.large
   * 비용 효율적이면서 균형 잡힌 성능 제공
2. **데이터베이스**:
   * 메모리 최적화 인스턴스: r5.xlarge, r6g.xlarge
   * 높은 메모리 대 CPU 비율 제공
3. **배치 처리 작업**:
   * 컴퓨팅 최적화 인스턴스: c5.xlarge, c6g.xlarge
   * 높은 CPU 성능 제공
4. **기계 학습 워크로드**:
   * GPU 인스턴스: p3.2xlarge, g4dn.xlarge
   * 가속 컴퓨팅 기능 제공

위 계열은 예시이며 최신 제품 목록이나 측정된 성능 순위가 아닙니다. 워크로드·가격·아키텍처·드라이버·대상 AZ의 제공 여부와 용량을 함께 검토합니다.

</details>



10. Amazon EKS 클러스터를 생성한 후 kubectl을 구성하는 올바른 명령어는 무엇인가요?
   * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
   * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
   * C) `kubectl config set-cluster my-cluster --region us-west-2`
   * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>정답 보기</summary>

**정답: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**설명:** Amazon EKS 클러스터를 생성한 후 kubectl을 구성하는 올바른 명령어는 `aws eks update-kubeconfig --name my-cluster --region us-west-2`입니다. 이 명령어는 AWS CLI의 EKS 모듈을 사용하여 지정된 클러스터에 대한 kubeconfig 파일을 업데이트합니다.

**kubectl 구성 과정:**

1. **kubeconfig 파일 업데이트**:
   * kubeconfig 파일은 kubectl이 Kubernetes 클러스터와 통신하는 데 필요한 구성 정보를 저장합니다.
   * 명시한 `--kubeconfig`, `KUBECONFIG`의 첫 경로, `~/.kube/config` 순으로 선택합니다.
   * 이 명령은 선택한 파일에 클러스터·exec 인증 구성을 병합하고 현재 컨텍스트를 바꾸지만 클러스터 권한을 부여하지는 않습니다.
2. **명령어 구성 요소**:
   * `--name`: EKS 클러스터 이름
   * `--region`: 클러스터가 위치한 AWS 리전
   * `--kubeconfig` (선택 사항): 사용자 지정 kubeconfig 파일 경로
   * `--role-arn` (선택 사항): 클러스터 접근에 사용할 IAM 역할
3.  **전체 명령어 예시**:

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
4.  **추가 옵션**:

    ```bash
    # 사용자 지정 kubeconfig 파일 사용
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # 특정 IAM 역할 사용
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # 별칭 설정
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
5.  **구성 확인**:

    ```bash
    # 현재 컨텍스트 확인
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config current-context

    # 모든 컨텍스트 나열
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config get-contexts

    # 클러스터 연결 테스트
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" cluster-info
    ```

**다른 옵션들의 문제점:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: 이 명령어는 존재하지 않습니다. AWS CLI에는 `get-kubeconfig` 하위 명령어가 없습니다.
* `kubectl config set-cluster my-cluster --region us-west-2`: 이 명령어는 구문이 잘못되었습니다. `kubectl config set-cluster`는 `--region` 플래그를 지원하지 않으며, EKS 클러스터에 필요한 인증 정보를 자동으로 구성하지 않습니다.
* `eksctl configure kubectl --name my-cluster --region us-west-2`: 이 명령어는 존재하지 않습니다. eksctl에는 `configure kubectl` 하위 명령어가 없습니다. eksctl로 클러스터를 생성한 경우, 자동으로 kubeconfig를 구성하지만, 기존 클러스터에는 `aws eks update-kubeconfig` 또는 `eksctl utils write-kubeconfig`를 사용할 수 있습니다.

**eksctl을 사용한 기존 클러스터 구성 작성:**

기존 클러스터는 새 클러스터를 만들지 않고 다음과 같이 구성을 작성합니다:

```bash
eksctl utils write-kubeconfig --cluster my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

이 명령은 기존 클러스터의 kubeconfig를 작성합니다. IAM 인증과 access entry/RBAC 권한은 별도로 검증합니다. 클러스터 생성도 비활성화하지 않으면 기본적으로 kubeconfig를 작성합니다.

**여러 클러스터 관리:**

여러 EKS 클러스터를 관리하는 경우, 각 클러스터에 대해 `aws eks update-kubeconfig` 명령어를 실행하여 kubeconfig 파일에 추가할 수 있습니다:

```bash
# 첫 번째 클러스터 구성
aws eks update-kubeconfig --name cluster1 --region us-west-2 --alias cluster1-west --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# 두 번째 클러스터 구성
aws eks update-kubeconfig --name cluster2 --region us-east-1 --alias cluster2-east --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# 컨텍스트 전환
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --context cluster1-west get nodes
```

따라서, Amazon EKS 클러스터를 생성한 후 kubectl을 구성하는 올바른 명령어는 `aws eks update-kubeconfig --name my-cluster --region us-west-2`입니다.

</details>

## 실습 문제

### 실습 1: eksctl을 사용하여 EKS 클러스터 생성

**시나리오:** 개발 팀용 일반 EC2 관리형 노드 그룹 클러스터를 준비합니다. 교육용 설계이며, 검증된 프로덕션 준비 상태나 측정된 비용 결과를 의미하지 않습니다.

**요구사항:** AZ 두 개, 초기 `t3.medium` AL2023 노드 두 개, 노드 범위 2–5, 프라이빗 노드 네트워킹, 두 API 엔드포인트와 승인된 퍼블릭 CIDR을 사용합니다. 크기 범위만 설정하면 오토스케일러가 설치되는 것은 아닙니다. `t3.medium` 선택 전에 버스터블 인스턴스의 CPU 크레딧, 메모리, IP 용량, 할당량, 실제 워크로드 요구를 확인합니다.

<details>
<summary>정답 보기</summary>

**1. 도구와 자격 증명 준비.** [Part 1](../../eks/02-eks-cluster-creation-part1.md)의 체크섬 및 아키텍처별 설치 절차를 사용합니다. 예제는 EKS 1.36과 eksctl 0.230.0을 기준으로 검토했으며 실행 전에 리전의 EKS 버전과 클라이언트·애드온 호환성을 확인합니다. `kubectl`은 버전 차이 허용 범위에 맞아야 합니다. 현재 로그인에서 수임할 수 있는 승인된 기존 운영자 IAM 역할을 사용합니다. 프로비저닝 권한과 Kubernetes 접근 권한은 별개입니다.

**2. 전용 로컬 구성 생성·검토.** 생성된 이름은 새 교육용 클러스터에 사용합니다. 퍼블릭 CIDR은 실제 허용된 송신 주소 범위로 설정합니다. 두 AZ는 `us-west-2`용 예제이며 인스턴스 제공 여부와 용량을 확인해야 합니다.

```bash
# Use a dedicated training account/role with reviewed provisioning permissions.
aws sts get-caller-identity
eksctl version
kubectl version --client
EKS_LAB_DIR=$(mktemp -d /tmp/eks-creation-lab.XXXXXX)
: "${EKS_LAB_DIR:?}"
EKS_LAB_CLUSTER="creation-quiz-$(date +%s)-$$"
EKS_LAB_REGION=us-west-2
EKS_LAB_KUBECONFIG="$EKS_LAB_DIR/kubeconfig"
: "${APPROVED_API_CIDR:?Set your actual approved administration egress CIDR}"
: "${OPERATOR_ROLE_ARN:?Set an existing IAM role ARN, not an STS session ARN}"

cat > "$EKS_LAB_DIR/cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_LAB_CLUSTER}
  region: ${EKS_LAB_REGION}
  version: "1.36"
availabilityZones: ["us-west-2a", "us-west-2b"]
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR}"]
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: false
  accessEntries:
    - principalARN: "${OPERATOR_ROLE_ARN}"
      type: STANDARD
      accessPolicies:
        - policyARN: arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy
          accessScope:
            type: cluster
managedNodeGroups:
  - name: dev-ng
    amiFamily: AmazonLinux2023
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    privateNetworking: true
    disableIMDSv1: true
    ssh:
      allow: false
    tags:
      Environment: development
      Owner: training
EOF

# Review the local configuration; this command does not create resources.
eksctl create cluster -f "$EKS_LAB_DIR/cluster.yaml" --dry-run \
  > "$EKS_LAB_DIR/resolved.yaml"
```

이 구성은 실습을 위해 지정한 운영자에게 클러스터 관리자 접근을 부여하고 생성자의 자동 관리자 접근은 비활성화합니다. 운영자 역할을 생성하거나 호출자에게 그 역할을 수임할 권한을 주지는 않습니다. eksctl이 필요한 클러스터·노드 역할을 생성하므로 생성된 정책 범위를 검토합니다. 일반 구성에서는 노드 역할에 VPC CNI 권한이 포함될 수 있습니다. 워크로드 격리를 강화하려면 공식 CNI IAM 지침에 따라 전용 `aws-node` 역할을 구성합니다. 나중에 사용할 수도 있다는 이유만으로 이미지 푸시, DNS, 스토리지, 로드 밸런서, 로깅 권한을 모든 노드에 추가하지 않습니다.

**3. 구성과 비용을 검토한 뒤 프로비저닝.** 새 VPC 기본 구성에는 NAT 등 과금되는 인프라가 포함될 수 있습니다. eksctl은 CloudFormation으로 VPC·서브넷·보안 그룹·역할·클러스터·노드 그룹을 생성합니다. 실패하면 일부 리소스가 남을 수 있으므로 완전한 자동 정리를 가정하지 말고 스택 이벤트를 확인합니다.

```bash
# Provisioning step: creates billable AWS resources.
if eksctl create cluster -f "${EKS_LAB_DIR:?}/cluster.yaml" --write-kubeconfig=false; then
  EKS_LAB_ARN=$(aws eks describe-cluster \
    --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
    --query cluster.arn --output text)
  : "${EKS_LAB_ARN:?Could not record the created cluster ARN}"
  aws eks update-kubeconfig --name "$EKS_LAB_CLUSTER" \
    --region "$EKS_LAB_REGION" --role-arn "${OPERATOR_ROLE_ARN:?}" \
    --kubeconfig "${EKS_LAB_KUBECONFIG:?}" --alias "$EKS_LAB_CLUSTER"
fi
```

**4. 실제 상태·접근·크기 범위 확인.** 클러스터와 노드 그룹의 `ACTIVE`, 노드의 `Ready` 상태를 기다리고 비정상 시스템 포드 및 예상한 AZ 배치를 확인합니다. 생성 요청 성공이나 RBAC 목록 조회만으로 안전하고 정상적인 클러스터임을 입증할 수는 없습니다.

```bash
aws eks describe-cluster --name "${EKS_LAB_CLUSTER:?}" \
  --region "${EKS_LAB_REGION:?}" \
  --query 'cluster.{status:status,version:version,endpoint:resourcesVpcConfig,access:accessConfig}'
aws eks describe-nodegroup --cluster-name "$EKS_LAB_CLUSTER" \
  --nodegroup-name dev-ng --region "$EKS_LAB_REGION" \
  --query 'nodegroup.{status:status,scaling:scalingConfig,ami:amiType}'
kubectl --kubeconfig "${EKS_LAB_KUBECONFIG:?}" config current-context
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get pods -n kube-system
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" auth can-i get nodes
```

**5. 필요한 구성 요소만 추가.** Cluster Autoscaler에는 고급 문제 2의 제한된 IAM·서비스 계정·검색 설정이 필요합니다. 크기 범위는 스스로 워크로드 수요에 반응하지 않습니다. `kubectl top`에는 정상 동작하는 Metrics Server가 필요합니다. 검토한 Metrics Server 0.9.0은 Kubernetes 1.34 이상을 지원하며 실제 설치 버전을 확인해야 합니다. 비용 절감이나 적절한 크기를 주장하기 전에 대표 부하를 측정합니다.

**6. 교육용 클러스터 정리.** 실습에서 추가한 LoadBalancer Service·Ingress가 있다면 먼저 삭제하고 컨트롤러가 AWS 리소스를 해제할 때까지 기다립니다. PVC 회수 정책과 보존 볼륨도 확인합니다. 이 실습 자체는 그런 애플리케이션 리소스를 만들지 않습니다. 이후 기록한 클러스터만 삭제합니다:

```bash
# Only after removing this lab's workloads and checking retained resources.
if CURRENT_LAB_ARN=$(aws eks describe-cluster \
  --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
  --query cluster.arn --output text) &&
  [ "$CURRENT_LAB_ARN" = "${EKS_LAB_ARN:?Original cluster ARN required}" ]; then
  eksctl delete cluster --name "$EKS_LAB_CLUSTER" --region "$EKS_LAB_REGION" --wait
else
  printf '%s\n' 'Cluster lookup/identity mismatch; no deletion attempted.' >&2
fi
```

이후 CloudFormation과 AWS 리소스 목록에서 삭제 실패, 보존 볼륨, 별도 생성한 역할·엔드포인트를 확인합니다. 정리가 확인될 때까지 구성과 ARN 기록을 보관하고, 더 이상 필요하지 않을 때 임시 kubeconfig 디렉터리를 로컬에서 제거합니다.

</details>

### 실습 2: AWS Management Console을 사용하여 EKS 클러스터 생성

**시나리오:** 향후 프로덕션 배포에 참고할 수 있는 일반 관리형 노드 그룹 설계를 검토합니다. 워크로드 크기, 라우팅, IAM, 가용성, 업그레이드, 복구는 환경별 검증이 필요한 가정입니다. 이 감사에서는 해당 구성을 프로비저닝하거나 부하 테스트하지 않았습니다.

<details>
<summary>정답 보기</summary>

**1. 별도 IAM 역할 준비.**

- 클러스터 역할: `eks.amazonaws.com`을 신뢰하고 `AmazonEKSClusterPolicy`를 연결합니다.
- EC2 노드 역할: `ec2.amazonaws.com`을 신뢰하고 `AmazonEKSWorkerNodePolicy`, `AmazonEC2ContainerRegistryPullOnly`를 연결합니다. 지원되는 경우 VPC CNI에 별도 IRSA·Pod Identity 역할을 부여합니다. 단순한 IPv4 노드 역할 방식을 의도적으로 선택했다면 `AmazonEKS_CNI_Policy`를 명시적으로 연결하고 공유 권한의 한계를 기록합니다.
- 프로비저닝·운영자 자격 증명: 승인된 리소스 범위의 IAM 권한과 대상 역할의 `iam:PassRole`을 사용합니다. 기존 운영자 역할에 실습용 접근 정책을 연결한 EKS 액세스 항목을 추가합니다. kubeconfig 생성 자체는 Kubernetes 권한을 부여하지 않습니다.

**2. VPC와 서브넷 검토.** 다음 공식 예제는 계속 참고할 수 있으며 URL의 날짜는 EKS 버전이 아닙니다:

```text
https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
```

고유한 교육용 스택을 생성하기 전에 CloudFormation 템플릿을 읽습니다. 기본값은 **AZ 두 개에 퍼블릭 서브넷 두 개와 프라이빗 서브넷 두 개, 인터넷 게이트웨이, NAT 게이트웨이·EIP 두 개**를 생성합니다. 따라서 인터넷 송신이 가능한 NAT 기반 설계이지 인터넷 차단 클러스터가 아닙니다. 프로덕션에 기본값을 그대로 적용하지 말고 CIDR 중복, AZ, IP 용량, NAT 비용을 검토합니다.

`VpcId`, `SubnetIds`, `SecurityGroups`를 기록합니다. `SubnetIds`에는 **퍼블릭·프라이빗 서브넷이 모두** 들어 있으므로 각각의 라우팅 테이블을 확인하고 실제 프라이빗 서브넷을 노드에 선택합니다. 출력의 사용자 지정 보안 그룹만으로 필요한 통신 규칙이 모두 있다는 뜻은 아닙니다. EKS 클러스터 보안 그룹, 추가 그룹, 컨트롤 플레인·노드 통신 규칙을 검토합니다.

**3. 일반 클러스터 생성.** EKS 콘솔의 사용자 지정 구성 경로에서 이 실습은 Auto Mode를 비활성화합니다. EKS 표준 지원 중이며 호환되는 사용 가능 버전(검토 예제는 1.36), 클러스터 서비스 역할, 검토한 VPC·서브넷을 선택합니다.

- API 액세스 항목 인증과 지정한 운영자의 권한을 구성합니다. 설명되지 않은 생성자 관리자 기본값에 의존하지 않습니다.
- 프라이빗 전용 API라면 관리 네트워크의 프라이빗 라우팅·DNS를 먼저 확인합니다. 또는 퍼블릭·프라이빗 접근을 함께 켜고 `publicAccessCidrs`를 승인된 관리 송신 범위로 제한합니다.
- 일반 EC2 클러스터에는 호환되는 VPC CNI, kube-proxy, CoreDNS 애드온을 유지하고 설정·권한을 검토합니다. 필요한 컨트롤 플레인 로그를 켜되 로그 비용도 반영합니다.
- 검토 후 생성하고 `ACTIVE`를 기다립니다. 생성 시간은 달라지며 몇 분이라는 예측은 완료 판정 기준이 아닙니다.

**4. 관리형 노드 그룹 추가.** EC2 노드 역할, AL2023 x86_64 AMI, 예시 `m5.large`처럼 지원되는 인스턴스 유형을 선택합니다. 예제는 루트 디스크 50 GiB, 원하는 크기 3, 최소 2, 최대 5와 검토한 프라이빗 서브넷을 사용합니다. 이는 크기 예시이지 프로덕션 권장값이 아닙니다. 필요한 접근·IMDS·스토리지 암호화를 구성하고 노드 그룹 `ACTIVE`, 노드 `Ready`를 기다립니다.

**5. 접근과 실제 AWS 보안 그룹 확인.** 콘솔에서 기록한 클러스터 이름과 승인된 운영자 역할을 사용합니다:

```bash
CONSOLE_LAB_DIR=$(mktemp -d /tmp/eks-console-lab.XXXXXX)
: "${CONSOLE_LAB_DIR:?}"
CONSOLE_KUBECONFIG="$CONSOLE_LAB_DIR/kubeconfig"
aws eks update-kubeconfig --name "${CONSOLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --role-arn "${OPERATOR_ROLE_ARN:?}" \
  --kubeconfig "$CONSOLE_KUBECONFIG" --alias "$CONSOLE_CLUSTER"
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get pods -n kube-system

# Security groups are AWS resources; kubeconfig does not contain their rules.
aws eks describe-cluster --name "$CONSOLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_CLUSTER_SG_ID:?Copy the cluster SG ID from the result above}"
```

**6. 선택적 NetworkPolicy 실습.** 먼저 선택한 CNI와 설정이 NetworkPolicy를 적용하는지 확인합니다. AWS VPC CNI의 정책 지원은 활성화되어 있어야 하고 노드·OS 구성도 이를 지원해야 합니다. 다음 인바운드 전용 기본 차단 정책은 새로 만든 빈 실습 네임스페이스에만 적용됩니다. 아웃바운드를 차단하지 않으며 `apply` 성공만으로 실제 정책 적용을 입증하지 못합니다.

```bash
# An optional isolated policy example, after enabling CNI policy enforcement.
NP_LAB_NAMESPACE="np-quiz-$(date +%s)-$$"
if kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" create namespace "$NP_LAB_NAMESPACE"; then
  NP_LAB_UID=$(kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    get namespace "$NP_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}')
  : "${NP_LAB_UID:?Namespace identity lookup failed}"
  cat > "${CONSOLE_LAB_DIR:?}/default-deny.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: ${NP_LAB_NAMESPACE}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
EOF
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    apply -f "$CONSOLE_LAB_DIR/default-deny.yaml"
fi
```

전용 테스트 포드로 허용·거부 트래픽을 확인하고 실제 워크로드에 적용하기 전에 필요한 허용 정책을 추가합니다. 기존 공유 `default` 네임스페이스에는 적용하지 않습니다. 실습이 끝나면 격리된 네임스페이스를 제거합니다:

```bash
# Remove only the namespace created above, after confirming its UID.
if CURRENT_NP_UID=$(kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" \
  get namespace "${NP_LAB_NAMESPACE:?}" -o jsonpath='{.metadata.uid}') &&
  [ "$CURRENT_NP_UID" = "${NP_LAB_UID:?Original namespace UID required}" ]; then
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" delete namespace "$NP_LAB_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace lookup/identity mismatch; no deletion attempted.' >&2
fi
```

**7. 콘솔 정리:** 실습 워크로드를 지우고 연결된 클라우드 리소스 해제를 기다린 뒤, 이 실습의 관리형 노드 그룹을 삭제합니다. 완료 후 실습 클러스터를 삭제합니다. EKS 리소스와 외부 의존성이 제거된 후에만 실습 VPC CloudFormation 스택을 삭제합니다. 실습 전용으로 만든 IAM 역할·엔드포인트만 제거하고 공유 리소스는 유지하며 삭제 실패·보존 리소스를 확인합니다. 이 감사에서는 해당 작업을 실행하지 않았습니다.

</details>

## 고급 주제

다음은 Amazon EKS 클러스터 생성에 관한 고급 주제에 대한 질문입니다. 이 섹션은 EKS 클러스터 생성의 심화 개념과 모범 사례에 대한 이해를 테스트합니다.

1. EKS EC2 관리형 노드 그룹에서 사용자 지정 시작 템플릿을 사용하는 주요 이점은 무엇인가요?
   * A) 클러스터 생성 시간 단축 보장
   * B) 노드 사용자 데이터와 볼륨 구성 지정
   * C) 컨트롤 플레인 플러그인 설치
   * D) 새 AMI가 게시될 때마다 모든 기존 노드 자동 갱신

<details>
<summary>정답 보기</summary>

**정답: B) 노드 사용자 데이터와 볼륨 구성 지정**

시작 템플릿은 스토리지, 인스턴스 메타데이터, OS별 사용자 데이터 등 **EC2 관리형 노드 그룹**을 사용자 지정합니다. EKS 컨트롤 플레인이나 EKS Auto Mode 노드를 구성하는 수단은 아닙니다.

**AL2023 사용자 데이터:** MIME multipart 형식을 사용합니다. 템플릿에 `ImageId`가 없어 EKS가 AMI를 선택하면 EKS가 노드 구성을 제공·병합합니다. 사용자 지정 AMI ID가 있으면 고급 문제 5의 완전한 `NodeConfig`를 제공해야 합니다. AL2023의 systemd 서비스가 `nodeadm`을 실행하므로 `/etc/eks/bootstrap.sh`, 중복 `nodeadm init`, 수동 kubelet 시작을 사용하지 않습니다. 추가 소프트웨어는 선택한 OS와 호환되어야 하며 신뢰할 수 있는 패키지 저장소에 연결할 수 있어야 합니다.

다음 최소 예제는 EKS가 AL2023 AMI를 선택하는 경우이며 애플리케이션 디렉터리만 생성합니다:

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_CUSTOMIZATION"

--EKS_CUSTOMIZATION
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_CUSTOMIZATION--
```

**스토리지:** 다음은 올바른 `LaunchTemplateData` 조각입니다. AMI의 루트 디바이스 이름을 확인합니다. 볼륨 연결만으로 포맷이나 마운트가 이루어지지는 않습니다. 두 예제 볼륨은 암호화되지만 인스턴스 종료 시 삭제됩니다. 노드 교체 후에도 보존할 애플리케이션 데이터에는 CSI 기반 PV와 적절한 회수·백업 정책을 사용합니다.

```json
{
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 100,
        "VolumeType": "gp3",
        "Iops": 3000,
        "Throughput": 125,
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    },
    {
      "DeviceName": "/dev/sdf",
      "Ebs": {
        "VolumeSize": 500,
        "VolumeType": "gp3",
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    }
  ]
}
```

**네트워킹과 메타데이터:** 예제 보안 그룹을 컨트롤 플레인, 노드, DNS, 워크로드 통신에 필요한 규칙을 갖춘 실제 그룹으로 바꿉니다. 사용자 지정 보안 그룹을 제공하면 EKS가 클러스터 보안 그룹을 자동으로 추가하지 않습니다. 보안 그룹은 인스턴스 수준 또는 네트워크 인터페이스 수준 중 한 곳에 지정합니다.

```json
{
  "NetworkInterfaces": [
    {
      "DeviceIndex": 0,
      "Groups": ["sg-0123456789abcdef0"],
      "DeleteOnTermination": true
    }
  ],
  "MetadataOptions": {
    "HttpEndpoint": "enabled",
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1
  }
}
```

홉 제한 1은 포드가 노드 자격 증명 대신 IRSA 또는 EKS Pod Identity를 사용하는 조건입니다. 컨테이너에서 IMDSv2에 접근해야 하는 워크로드에는 홉 제한 2가 필요할 수 있습니다. 이 설정이나 IMDSv2가 `hostNetwork` 포드를 격리하는 경계는 아닙니다. 다중 인터페이스, 배치 설정, 인스턴스 스토어는 인스턴스 유형과 EKS 시작 템플릿 제한에 맞아야 하며 모든 조합에서 사용할 수 있는 옵션은 아닙니다.

**노드 그룹 생성:** 실제 ID, 권한, 네트워크 경로를 검토한 뒤 eksctl 구성 또는 AWS CLI 예제 중 하나를 선택합니다. 아래 두 예제는 순서대로 실행하는 절차가 아닙니다:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    subnets: ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
```

```bash
# Use an existing reviewed template version and a new node group name.
aws eks create-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --launch-template "id=${LAUNCH_TEMPLATE_ID:?},version=${LAUNCH_TEMPLATE_VERSION:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --node-role "${NODE_ROLE_ARN:?}"
```

시작 템플릿에는 `SubnetId`와 `IamInstanceProfile`을 넣지 않습니다. 서브넷과 노드 IAM 역할은 노드 그룹 요청에 지정합니다. 시작 템플릿 사용 시 노드 그룹의 `diskSize`, `remoteAccess`를 중복 지정하지 않습니다. 인스턴스 유형은 템플릿 또는 노드 그룹 요청 중 한 곳에서 설정합니다. `ImageId`가 있으면 노드 그룹의 `amiType`, `releaseVersion`, `version`을 생략하고 사용자 지정 AMI의 kubelet과 컨트롤 플레인 버전 호환성을 확인합니다.

명시적인 `ImageId`는 AMI를 고정하지만, 이를 생략한 템플릿은 EKS가 선택하는 AMI를 사용할 수 있습니다. 어느 경우에도 새 AMI가 게시될 때 기존 노드가 자동 갱신되지는 않습니다. 사용자 지정 템플릿 변경은 **같은** 템플릿의 새 버전을 만든 뒤 명시적으로 노드 그룹을 업데이트해야 하며, 이 과정에서 인스턴스가 교체됩니다.

참고: [시작 템플릿 제한](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [CreateNodegroup 필드](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [AL2023 초기화](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html).

</details>

2. EKS 비용 최적화를 위해 그 자체만으로는 충분하지 않은 접근 방식은 무엇인가요?
   * A) 중단 허용 워크로드에 Spot 사용
   * B) Cluster Autoscaler와 권한 구성
   * C) 측정 없이 모든 워크로드에 최신 인스턴스 세대 선택
   * D) 워크로드 요구와 총비용에 따라 Fargate 선택적 평가

<details>
<summary>정답 보기</summary>

**정답: C) 측정 없이 모든 워크로드에 최신 인스턴스 세대 선택**

모든 노드를 최신 세대라는 이유만으로 선택하는 것은 충분한 비용 분석이 아닙니다. 워크로드의 아키텍처, 처리량, 지연 시간, 메모리, 리전 가용성, 중단 허용도를 비교해야 합니다. 새 세대가 더 경제적일 수도 있으며, 같은 작업량에 대해 신형이나 구형이 항상 더 저렴한 것은 아닙니다.

1. **Spot과 유형 분산:** AWS의 Spot 온디맨드 대비 최대 90% 할인은 가능한 가격 할인이지 이 실습에서 측정하거나 보장한 절감률이 아닙니다. 중단과 대체 용량을 고려합니다. Cluster Autoscaler는 첫 번째 인스턴스 유형으로 스케줄링을 시뮬레이션하므로 한 그룹의 혼합 유형은 CPU·메모리·GPU 크기를 맞춥니다. 로컬 디스크 의존성은 별도로 확인합니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: spot-ng
    amiFamily: AmazonLinux2023
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    spot: true
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 5
```

2. **Cluster Autoscaler:** 최소·최대 크기는 확장 범위만 설정합니다. 스케줄링할 수 없는 포드와 제거 가능한 용량에 따라 원하는 용량을 변경하려면 컨트롤러와 권한이 필요합니다. 모든 노드에 광범위한 오토스케일링 권한을 부여하지 않습니다. 다음 **신규 설치** 전에 `kube-system/cluster-autoscaler` 서비스 계정과 해당 계정으로 OIDC 신뢰를 제한한 전용 IRSA 역할 또는 지원되는 Pod Identity 구성을 준비합니다. 용량 변경 권한은 대상 클러스터의 Auto Scaling 그룹으로 제한하고, 해당 그룹에 `k8s.io/cluster-autoscaler/enabled=true`, `k8s.io/cluster-autoscaler/<cluster-name>=owned` 태그를 설정합니다. 노드 그룹 리소스에 태그가 있다는 사실만으로 ASG 검색 구성이 완료되지는 않습니다.

컨트롤러 마이너 버전은 클러스터와 같아야 합니다. 차트 9.59.0의 기본 컨트롤러는 1.35.0이므로 EKS 1.36 예제에서는 1.36.1을 명시합니다. 다른 클러스터 버전에는 그에 맞는 컨트롤러를 선택합니다. 같은 그룹을 관리하는 기존 CA 설치가 없는지도 확인합니다.

```bash
# EKS 1.36 example: first prepare the dedicated service account/IAM role
# and discovery tags on the target Auto Scaling groups.
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  --set-string "autoDiscovery.clusterName=${EXAMPLE_CLUSTER:?}" \
  --set-string "awsRegion=${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  --wait --timeout 5m
```

3. **Fargate와 적정 크기:** Fargate는 호스트 관리 부담을 줄이지만 실제 CPU 사용량만이 아니라 할당 리소스와 실행 시간을 기준으로 과금합니다. 지원되는 포드와 프라이빗 서브넷에 프로필을 맞추고 EC2와 총비용을 비교합니다. `kubectl top`에는 Metrics Server가 필요하며 짧은 측정만으로 용량 계획을 확정할 수 없습니다.
4. **Graviton:** ARM 노드 그룹 생성 전에 ARM64 이미지와 의존성을 검증합니다. 특정 세대의 “최대 40% 향상된 가격 대비 성능”은 모든 환경의 40% 요금 감소나 동일 성능을 보장하는 문장이 아닙니다.

```bash
# Metrics Server must already be installed and healthy.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top nodes
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top pods --all-namespaces

# Alternative compute examples: each creates separately billed resources.
eksctl create fargateprofile --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name fp-dev --namespace dev
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name arm-ng \
  --managed --node-ami-family AmazonLinux2023 \
  --node-type m6g.large --nodes 2 --node-private-networking
```

5. **약정:** Reserved Instances와 Savings Plans는 조건에 맞는 예측 가능한 사용량의 비용을 줄일 수 있습니다. 최대 72%와 같은 홍보 수치는 상품, 기간, 결제 방식, 사용량에 따라 달라지며 사용하지 않는 약정은 절감 효과를 없앨 수 있습니다.
6. **요청과 제한:** 대표적인 부하를 측정한 뒤 값을 선택합니다. 요청은 스케줄링과 오토스케일러 판단에 영향을 주고 지나치게 낮은 제한은 CPU 스로틀링이나 OOM 종료를 일으킬 수 있습니다. 다음은 컨테이너별 예시 값입니다:

```yaml
# Fragment inside spec.template.spec.containers[].
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

7. **비용 할당:** Cost Explorer와 구성된 비용 할당 보고서·도구를 사용합니다. Kubernetes 레이블이 자동으로 활성 AWS 비용 할당 태그가 되지는 않습니다. 컨트롤 플레인, 해당하는 Auto Mode 수수료, 스토리지, 로드 밸런서, NAT, 전송, 로깅 비용도 포함합니다.

참고: [EKS의 CA](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html), [CA 차트](https://github.com/kubernetes/autoscaler/tree/master/charts/cluster-autoscaler), [CA 1.36.1](https://github.com/kubernetes/autoscaler/releases/tag/cluster-autoscaler-1.36.1), [Spot 요금](https://aws.amazon.com/ec2/spot/), [Fargate 요금](https://aws.amazon.com/fargate/pricing/), [Graviton](https://aws.amazon.com/ec2/graviton/), [Savings Plans](https://aws.amazon.com/savingsplans/).

</details>

3. Kubernetes API의 프라이빗 전용 접근과 노드·포드의 아웃바운드 인터넷 차단을 모두 충족하는 설계는 무엇인가요?
   * A) 프라이빗 API, 인터넷 송신 경로 없는 프라이빗 노드 서브넷, 필요한 서비스 엔드포인트와 관리 경로
   * B) API·송신 설정은 그대로 두고 노드만 프라이빗 서브넷에 배치
   * C) 퍼블릭·프라이빗 Kubernetes API 엔드포인트를 모두 비활성화
   * D) 퍼블릭 API만 끄고 제한 없는 NAT 송신 유지

<details>
<summary>정답 보기</summary>

**정답: A) 프라이빗 API, 인터넷 송신 경로 없는 프라이빗 노드 서브넷, 필요한 서비스 엔드포인트와 관리 경로**

**Kubernetes API에 누가 접근할 수 있는가**와 **노드·포드가 어디로 통신할 수 있는가**는 별도 결정입니다. 프라이빗 전용 API가 NAT 경로를 제거하거나 워크로드의 외부 통신을 차단하거나 모든 패킷이 한 VPC 안에 머무르도록 보장하지는 않습니다. 라우팅, DNS, 보안 그룹, 권한이 허용하면 연결된 다른 네트워크에서도 프라이빗 API에 접근할 수 있습니다.

이 문제의 요구사항은 프라이빗 전용 API와 노드·포드의 아웃바운드 인터넷 차단을 모두 포함합니다. 프라이빗 엔드포인트를 켜고 퍼블릭 엔드포인트를 끄며, 인터넷으로 나가는 경로가 없는 프라이빗 노드 서브넷을 사용하고 필요한 서비스 엔드포인트·레지스트리 이미지·관리 경로를 마련합니다.

**엔드포인트 전환:** 먼저 프라이빗 접근을 활성화하고 해당 업데이트의 성공을 기다린 뒤, 사용할 프라이빗 네트워크에서 인증된 `kubectl` 접근을 확인합니다. 그 후에만 아래 프라이빗 전용 전환 예제를 사용합니다. 반환된 업데이트가 `Successful`인지 확인하고 접근을 다시 점검합니다. 퍼블릭 엔드포인트는 클러스터 보안 그룹이 아니라 `publicAccessCidrs`로 제한합니다. 클러스터 보안 그룹은 프라이빗 엔드포인트 통신에 적용됩니다.

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

**노드 배치:** 다음 조각은 기존 VPC와 프라이빗 서브넷을 사용합니다. 실제 ID와 경로를 확인해야 합니다. 이 구성 자체가 VPC 엔드포인트를 만들거나 기존 NAT 경로를 제거하지는 않습니다. 인터넷만 연결된 별도 워크스테이션에서 eksctl을 실행한다고 프라이빗 전용 Kubernetes API에 접근할 수 있는 것은 아닙니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
managedNodeGroups:
  - name: private-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 3
    privateNetworking: true
```

**AWS 서비스 연결:** 아래 ECR·S3 예제는 전체 설계의 일부입니다. private DNS 중복 충돌을 피하도록 기존 엔드포인트를 먼저 확인합니다. 인터페이스 엔드포인트에는 private DNS와 대상 클라이언트의 HTTPS 인바운드 허용이 필요합니다. S3 게이트웨이 엔드포인트에는 프라이빗 라우팅 테이블 및 적절한 엔드포인트·버킷 정책이 필요합니다.

```bash
# Example fragments for a reviewed no-internet VPC design.
# Interface endpoint SG must allow HTTPS from the intended nodes/clients.
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.api" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.dkr" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.s3" \
  --vpc-endpoint-type Gateway \
  --route-table-ids "${PRIVATE_ROUTE_TABLE_A:?}" "${PRIVATE_ROUTE_TABLE_B:?}"
```

| 의존성 | 인터넷 경로가 없을 때의 프라이빗 연결 |
| --- | --- |
| 프라이빗 ECR 이미지 풀 | `ecr.api`, `ecr.dkr`, S3 게이트웨이; 퍼블릭 이미지를 접근 가능한 프라이빗 레지스트리에 복사 |
| 노드·CNI가 사용하는 EC2 API | `ec2`와 적절한 권한·엔드포인트 정책 |
| IRSA 자격 증명 | 리전 `sts`; SDK가 리전 엔드포인트를 사용하도록 구성 |
| VPC 내부의 OIDC discovery/JWKS 접근 | IAM OIDC 공급자 설정 등에 `oidc-eks` 사용; STS와 별도 |
| EKS Pod Identity 자격 증명 | `eks-auth`와 지원되는 Pod Identity Agent·구성 |
| EKS 관리 API | `eks`; Kubernetes API 프라이빗 엔드포인트를 대체하지 않음 |
| 로그·오토스케일링·로드 밸런싱·SSM | 실제 사용하는 서비스의 엔드포인트와 권한; SSM 메시징 연결도 필요 |

엔드포인트 서비스와 DNS 이름은 리전·파티션에 따라 다릅니다. 이미지 레지스트리, 패키지 다운로드, 외부 API, 애드온 기능 등 전체 의존성을 확인합니다. 한 AWS 서비스의 엔드포인트가 인터넷 연결 전체를 대체하지는 않습니다.

**관리 접근:** 라우팅된 VPN·Direct Connect 연결, 프라이빗 접근이 가능한 통제된 호스트, 적절히 구성한 SSM 세션을 사용합니다. 배스천에 반드시 퍼블릭 IP가 필요한 것은 아닙니다. SSM에도 에이전트, IAM 권한, 서비스 연결이 필요합니다.

프라이빗 API와 NAT를 사용하는 프라이빗 노드 역시 유효한 EKS 설계이지만 이 문제의 인터넷 송신 차단 조건에는 맞지 않습니다. 또한 서브넷의 퍼블릭 경로만으로 개별 노드의 인터넷 접근 가능성을 단정할 수 없으며, 주소 할당과 보안 통제가 함께 작용합니다.

참고: [프라이빗 클러스터 요구사항](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [API 엔드포인트 접근](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [EKS PrivateLink와 OIDC](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html).

</details>

4. 새 노드 AMI를 적용하는 EKS 관리형 노드 그룹의 방식이 아닌 것은 무엇인가요?
   * A) 관리형 롤링 업데이트로 인스턴스 교체
   * B) 별도 블루/그린 노드 그룹 생성 및 검증
   * C) 인스턴스 교체 대신 실행 중인 인스턴스의 OS 패키지만 갱신
   * D) 확대 교체 전에 작은 캐니리 노드 그룹에서 새 AMI 검증

<details>
<summary>정답 보기</summary>

**정답: C) 인스턴스 교체 대신 실행 중인 인스턴스의 OS 패키지만 갱신**

EKS 관리형 노드 그룹의 업데이트는 EC2 인스턴스를 교체합니다. 실행 중인 인스턴스의 OS 패키지를 갱신하는 것은 관리형 AMI 업데이트 방식이 아닙니다. 모든 “인플레이스 업그레이드”가 지원되지 않는다는 모호한 설명은 피해야 합니다. AWS는 노드 그룹 리소스를 유지하면서 시작 템플릿의 AMI 버전을 바꾸는 경우에도 이 표현을 사용하며, 이 경우에도 인스턴스는 교체됩니다.

**롤링 업데이트:** `DEFAULT`는 기존 노드를 제거하기 전에 대체 용량을 생성합니다. `MINIMAL`은 선택한 기존 노드를 먼저 종료하고 대체 노드를 만들 수 있습니다. `maxUnavailable`의 기본값은 1이지만 변경할 수 있으므로 항상 한 번에 정확히 한 노드만 교체하는 것은 아닙니다. 할당량, AZ 용량, 포드 배치, 업데이트 전략을 확인합니다. 사용자 지정 AMI이면 같은 시작 템플릿의 새 버전을 명시합니다. 다음 명령은 EKS가 AMI를 선택하는 경우의 예제입니다:

```bash
# EKS-selected AMI case: inspect first, then initiate a reviewed update.
aws eks describe-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'nodegroup.{status:status,version:version,ami:amiType,release:releaseVersion,update:updateConfig}'
if NODE_UPDATE_ID=$(aws eks update-nodegroup-version \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODE_UPDATE_ID" \
    --region "$EXAMPLE_REGION" \
    --query 'update.{status:status,errors:errors}'
fi
```

반환된 업데이트 ID를 기록하고 최종 상태까지 `describe-update`를 반복합니다. API 요청 접수 성공은 업데이트 완료가 아닙니다. 실패하면 보고된 오류를 조사한 뒤 진행합니다. PDB가 축출을 막으면 `PodEvictionFailure`가 발생할 수 있으며, 명령을 끝내기 위해 `--force`로 우회하지 않습니다.

**블루/그린:** 호환되는 AL2023 노드 그룹을 별도로 만들고 워크로드 스케줄링과 준비 상태를 시험한 뒤 점진적으로 이동합니다. 애플리케이션 점검, 볼륨·AZ 제약, 롤백 조건이 충족될 때까지 기존 용량을 유지합니다. 노드 레이블 조회만으로 검증이 끝나지는 않으며, 트래픽은 노드 그룹 이름이 아니라 Service 엔드포인트·포드를 따릅니다. 새 그룹 생성 직후 기존 그룹을 자동 삭제하지 않습니다.

**캐니리:** 별도 레이블과 테인트가 있는 작은 그룹을 사용합니다. 테인트는 관계없는 포드의 배치를 제한하며 테스트 워크로드만 이를 선택하고 허용합니다. 허용 조건이 맞는 시스템 DaemonSet은 여전히 실행될 수 있습니다. 다음은 기존 테스트 클러스터용 구성 예제입니다:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: canary-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 1
    minSize: 1
    maxSize: 2
    privateNetworking: true
    labels:
      example.com/upgrade-track: canary
    taints:
      - key: example.com/upgrade-track
        value: canary
        effect: NoSchedule
```

전용 테스트 컨텍스트에서 사용하지 않는 `upgrade-lab` 네임스페이스를 먼저 만든 뒤 다음 완전한 예제 Deployment를 적용합니다. 실제 캐니리는 애플리케이션 의존성과 대표 트래픽도 검증해야 합니다. 이 NGINX 포드는 기본 스케줄링과 준비 상태만 확인합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: upgrade-canary
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      nodeSelector:
        example.com/upgrade-track: canary
      tolerations:
        - key: example.com/upgrade-track
          operator: Equal
          value: canary
          effect: NoSchedule
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
```

**중단 예산과 용량:** 다음 별도 예제는 `app-namespace`의 실제 `my-app` 워크로드를 전제로 하며, 일반적으로 준비된 복제본이 3개 이상 있어야 합니다. 위의 단일 복제본 캐니리용 PDB가 아닙니다:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: app-namespace
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

PDB는 축출 API로 처리되는 자발적 축출을 제한합니다. 가용성을 보장하거나 하드웨어 장애를 막거나 직접적인 Pod·Deployment 삭제를 막지는 않습니다. `minAvailable: 2`는 정상 포드가 두 개뿐이면 축출을 차단합니다. 여유 용량, 토폴로지, 프로브, 종료 동작, 장애 복구를 확인합니다. 블루/그린이나 캐니리 계획만으로 안전한 롤백이 입증되지는 않으며 상태 저장 데이터는 특히 주의해야 합니다.

참고: [관리형 업데이트 동작](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [AL2023 전환](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [포드 중단 예산](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).

</details>

5. EKS 최적화 AL2023 EC2 노드 부트스트랩이 하는 일이 아닌 것은 무엇인가요?
   * A) kubelet/컨테이너 런타임 구성
   * B) AWS 관리형 제어면 구성 요소를 워커에 설치
   * C) 노드 클라이언트 인증·연결 구성
   * D) 노드 등록

<details>
<summary>정답 보기</summary>

**정답: B) AWS 관리형 제어면 구성 요소를 워커에 설치**

워커에 API 서버·etcd·컨트롤러 관리자·스케줄러를 설치하지 않습니다. 이들은 AWS 관리형 제어면에 속합니다. **일반 EKS의 CoreDNS는 데이터 플레인의 클러스터 애드온이며 이 제어면 목록에 포함되지 않습니다.**

AL2023 EKS 최적화 AMI는 `nodeadm`으로 containerd와 kubelet을 구성합니다. `nodeadm-config`는 사용자 데이터 전에 기본 구성을 만들고 `nodeadm-run`은 이후 구성을 완료하고 데몬을 실행합니다. AMI가 자동 실행하므로 사용자 데이터에서 `nodeadm init`을 추가로 호출하지 않습니다. AL2의 `/etc/eks/bootstrap.sh`를 현재 AL2023 경로로 제시하지 않습니다.

**노드 연결과 네트워킹의 구분**

1. 프로비저닝 단계에서 노드 IAM 역할·인스턴스 프로필과 필요한 노드 접근 권한을 준비합니다. 부트스트랩이 IAM 역할을 생성하지 않습니다. AMI의 생성된 kubeconfig/인증 경로를 사용하며 인스턴스 역할을 불필요하게 다시 AssumeRole하는 수동 kubeconfig를 만들지 않습니다.
2. kubelet이 노드를 등록합니다. 준비 상태에는 클러스터 연결뿐 아니라 런타임·CNI 상태도 영향을 줍니다.
3. 일반 EKS의 `aws-node`, `kube-proxy`, CoreDNS는 클러스터 애드온으로 배포·관리합니다. 호스트 부트스트랩이 이 애드온 전체를 설치한다는 뜻이 아닙니다. CNI 파일을 임의로 덮어쓰지 않습니다.
4. 제공자 소유 `eks.amazonaws.com/nodegroup`·`topology.kubernetes.io/zone` 레이블을 수동으로 조작하지 않습니다. 사용자 레이블/taint는 노드 그룹·프로비저너 설정에서 관리합니다.

**NodeConfig 입력 예제**

아래는 관리 워크스테이션에서 기존 IPv4 클러스터의 실제 메타데이터로 사용자 데이터를 생성합니다. 검토한 EKS 최적화 AL2023 기반 사용자 AMI/자체 관리 노드용이며, 사용자 AMI ID가 없는 관리형 노드 그룹은 EKS의 메타데이터 생성·병합 경로를 따릅니다. `NodeConfig`는 호스트 부트스트랩 설정으로 `kubectl apply`할 일반 Kubernetes 리소스가 아닙니다.

```bash
# Run on the administration workstation to prepare reviewed IPv4 node user data.
NODE_CONFIG_DIR=$(mktemp -d /tmp/eks-nodeconfig.XXXXXX)
: "${NODE_CONFIG_DIR:?}"
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster --output json > "$NODE_CONFIG_DIR/cluster.json" || exit 1

jq -e '
  (.name | type == "string" and length > 0) and
  (.endpoint | startswith("https://")) and
  (.certificateAuthority.data | type == "string" and length > 0) and
  (.kubernetesNetworkConfig.ipFamily == "ipv4") and
  (.kubernetesNetworkConfig.serviceIpv4Cidr | type == "string" and length > 0)
' "$NODE_CONFIG_DIR/cluster.json" >/dev/null || exit 1

jq '{
  apiVersion: "node.eks.aws/v1alpha1",
  kind: "NodeConfig",
  spec: {
    cluster: {
      name: .name,
      apiServerEndpoint: .endpoint,
      certificateAuthority: .certificateAuthority.data,
      cidr: .kubernetesNetworkConfig.serviceIpv4Cidr
    }
  }
}' "$NODE_CONFIG_DIR/cluster.json" > "$NODE_CONFIG_DIR/nodeconfig.json" || exit 1

{
  printf 'MIME-Version: 1.0\n'
  printf 'Content-Type: multipart/mixed; boundary="EKS_NODE_CONFIG"\n\n'
  printf '%s\n' '--EKS_NODE_CONFIG' 'Content-Type: application/node.eks.aws' ''
  cat "$NODE_CONFIG_DIR/nodeconfig.json"
  printf '\n%s\n' '--EKS_NODE_CONFIG--'
} > "$NODE_CONFIG_DIR/user-data.mime"
printf 'Review user data: %s\n' "$NODE_CONFIG_DIR/user-data.mime"
# An EC2 LaunchTemplateData.UserData JSON field needs the MIME file base64 encoded.
# The console user-data editor can accept raw text when its encoding option is set accordingly.
```

DNS 서비스 주소와 maxPods를 모든 노드에 동일한 상수로 고정하지 않습니다. 클러스터 서비스 CIDR, 인스턴스/CNI/프리픽스 구성과 공식 계산 규칙을 따릅니다. 아래 명령은 일반 EC2 구성의 확인 예시이며 Auto Mode/Fargate에서는 관리 구성 요소가 다릅니다.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" describe node "${EXAMPLE_NODE:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get daemonset aws-node kube-proxy
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get deployment coredns
```

노드 조인·데몬 실행·네트워크나 실측 로그는 이 감사에서 실행/수집하지 않았습니다.

[AL2023/nodeadm lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [NodeConfig API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)

</details>

## 공식 참고 자료

- [EKS supported versions](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [VPC CNI IAM role](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [NetworkPolicy prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Metrics Server requirements](https://github.com/kubernetes-sigs/metrics-server#requirements)
- [eksctl configuration schema](https://schema.eksctl.io/)
