# Amazon EKS 클러스터 생성 퀴즈 (Part 3)

이 퀴즈는 Amazon EKS 클러스터 생성과 관련된 고급 네트워킹, 스토리지 구성, 그리고 멀티 테넌시에 대한 이해를 테스트합니다. 클러스터 네트워킹, 스토리지 옵션, 멀티 테넌트 환경 구성 등의 주제를 다룹니다.

## 기본 개념 문제

1. Amazon EKS 클러스터에서 포드당 IP 주소 수를 제한하는 주요 요소는 무엇인가요?
   - A) VPC의 CIDR 블록 크기
   - B) 노드의 인스턴스 유형
   - C) 클러스터의 Kubernetes 버전
   - D) 서브넷의 가용 IP 주소 수
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드의 인스턴스 유형**

**설명:**
Amazon EKS 클러스터에서 포드당 IP 주소 수를 제한하는 주요 요소는 노드의 인스턴스 유형입니다. Amazon VPC CNI 플러그인은 각 노드의 탄력적 네트워크 인터페이스(ENI)와 보조 IP 주소를 사용하여 포드에 IP 주소를 할당합니다. 각 EC2 인스턴스 유형은 지원하는 최대 ENI 수와 ENI당 최대 IP 주소 수가 다르므로, 이것이 노드에서 실행할 수 있는 최대 포드 수를 결정합니다.

#### 인스턴스 유형별 최대 포드 수 계산:

최대 포드 수는 다음 공식으로 계산됩니다:
```
(ENI 수 × ENI당 IP 주소 수 - 1) + 2
```

여기서:
- 1을 빼는 이유는 기본 ENI의 기본 IP 주소가 노드 자체에 사용되기 때문입니다.
- 2를 더하는 이유는 kube-proxy와 aws-node 포드가 호스트 네트워킹을 사용하기 때문입니다.

#### 일반적인 인스턴스 유형의 최대 포드 수:

| 인스턴스 유형 | 최대 ENI 수 | ENI당 IP 주소 수 | 최대 포드 수 |
|--------------|------------|----------------|------------|
| t3.small     | 3          | 4              | 11         |
| t3.medium    | 3          | 6              | 17         |
| m5.large     | 3          | 10             | 29         |
| m5.xlarge    | 4          | 15             | 58         |
| m5.2xlarge   | 4          | 15             | 58         |
| m5.4xlarge   | 8          | 30             | 234        |
| c5.large     | 3          | 10             | 29         |
| c5.xlarge    | 4          | 15             | 58         |
| r5.large     | 3          | 10             | 29         |
| r5.xlarge    | 4          | 15             | 58         |

#### 최대 포드 수 확인 방법:

```bash
# 노드의 최대 포드 수 확인
kubectl get nodes -o jsonpath='{.items[*].status.capacity.pods}'

# 또는 max-pods 스크립트 사용
curl -s https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/scripts/max-pods-calculator.sh | bash -s -- --instance-type m5.large
```

#### 최대 포드 수 제한 요소:

1. **인스턴스 유형**:
   - 각 인스턴스 유형은 지원하는 최대 ENI 수와 ENI당 IP 주소 수가 다릅니다.
   - 더 큰 인스턴스 유형은 일반적으로 더 많은 ENI와 IP 주소를 지원합니다.

2. **CNI 구성**:
   - 기본 VPC CNI 구성은 각 포드에 전체 ENI를 할당하지 않고, 보조 IP 주소를 사용합니다.
   - 사용자 지정 네트워킹을 사용하면 이 동작을 변경할 수 있습니다.

3. **접두사 위임**:
   - VPC CNI 1.9.0 이상에서는 접두사 위임 기능을 사용하여 각 ENI에 /28 CIDR 블록(16개 IP)을 할당할 수 있습니다.
   - 이를 통해 노드당 최대 포드 수를 크게 늘릴 수 있습니다.
   ```bash
   kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
   ```

4. **사용자 지정 max-pods 값**:
   - kubelet의 `--max-pods` 플래그를 사용하여 노드당 최대 포드 수를 제한할 수 있습니다.
   - 이는 인스턴스 유형이 지원하는 것보다 낮은 값으로 설정할 수 있습니다.
   ```bash
   eksctl create nodegroup \
     --cluster my-cluster \
     --name my-nodegroup \
     --node-type m5.large \
     --nodes 3 \
     --kubelet-extra-args "--max-pods=110"
   ```

#### 다른 옵션들의 문제점:

- **VPC의 CIDR 블록 크기**: VPC CIDR 블록 크기는 VPC에서 사용 가능한 총 IP 주소 수를 제한하지만, 개별 노드의 최대 포드 수를 직접적으로 제한하지는 않습니다.

- **클러스터의 Kubernetes 버전**: Kubernetes 버전은 지원되는 기능에 영향을 미치지만, 노드당 최대 포드 수를 직접적으로 제한하지는 않습니다.

- **서브넷의 가용 IP 주소 수**: 서브넷의 가용 IP 주소 수는 해당 서브넷에 배포할 수 있는 총 포드 수에 영향을 미치지만, 개별 노드의 최대 포드 수를 직접적으로 제한하지는 않습니다.

노드의 인스턴스 유형은 지원하는 ENI 수와 ENI당 IP 주소 수를 통해 노드에서 실행할 수 있는 최대 포드 수를 결정하는 주요 요소입니다. 따라서 워크로드 요구 사항에 맞는 적절한 인스턴스 유형을 선택하는 것이 중요합니다.
</details>
2. Amazon EKS 클러스터에서 포드 간 통신을 위한 기본 네트워크 정책은 무엇인가요?
   - A) 모든 포드 간 통신 허용
   - B) 같은 네임스페이스 내 포드 간 통신만 허용
   - C) 명시적으로 허용된 포드 간 통신만 허용
   - D) 모든 포드 간 통신 차단
   
<details>
<summary>정답 보기</summary>

**정답: A) 모든 포드 간 통신 허용**

**설명:**
Amazon EKS 클러스터에서 포드 간 통신을 위한 기본 네트워크 정책은 모든 포드 간 통신을 허용하는 것입니다. 기본적으로 EKS는 네트워크 정책을 구현하지 않으며, 모든 포드는 클러스터 내의 다른 모든 포드와 자유롭게 통신할 수 있습니다. 이는 Kubernetes의 기본 동작으로, 포드 간 통신을 제한하려면 명시적으로 네트워크 정책을 구성해야 합니다.

#### EKS의 기본 네트워킹 동작:

1. **기본 허용 정책**:
   - 기본적으로 모든 포드는 클러스터 내의 다른 모든 포드와 통신할 수 있습니다.
   - 네임스페이스 간 통신도 제한 없이 허용됩니다.
   - 이는 Kubernetes의 "평면 네트워크" 모델을 따릅니다.

2. **Amazon VPC CNI**:
   - EKS의 기본 CNI 플러그인은 Amazon VPC CNI입니다.
   - 이 플러그인은 포드에 VPC IP 주소를 할당하여 VPC 내에서 직접 라우팅 가능하게 합니다.
   - 기본적으로 네트워크 정책을 구현하지 않습니다.

#### 네트워크 정책 구현 방법:

EKS에서 포드 간 통신을 제한하려면 다음과 같은 네트워크 정책 솔루션을 구현해야 합니다:

1. **Calico**:
   ```bash
   # Calico 설치
   kubectl create namespace tigera-operator
   helm repo add projectcalico https://docs.projectcalico.org/charts
   helm install calico projectcalico/tigera-operator --namespace tigera-operator
   ```

2. **Cilium**:
   ```bash
   # Cilium 설치
   helm repo add cilium https://helm.cilium.io/
   helm install cilium cilium/cilium --namespace kube-system
   ```

3. **AWS Network Firewall** (VPC 수준):
   - AWS Network Firewall을 사용하여 VPC 수준에서 트래픽을 필터링할 수 있습니다.
   - 이는 포드 수준의 세분화된 제어가 아닌 서브넷 수준의 제어를 제공합니다.

#### 네트워크 정책 예시:

1. **기본 거부 정책**:
   ```yaml
   # 모든 인그레스 트래픽 차단
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny-ingress
     namespace: default
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
   ```

2. **특정 포드 간 통신 허용**:
   ```yaml
   # frontend에서 backend로의 통신만 허용
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

3. **네임스페이스 간 통신 제한**:
   ```yaml
   # prod 네임스페이스에서만 접근 허용
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-from-prod-namespace
     namespace: default
   spec:
     podSelector:
       matchLabels:
         app: database
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: prod
       ports:
       - protocol: TCP
         port: 5432
   ```

#### 네트워크 정책 모범 사례:

1. **기본 거부 정책 적용**:
   - 모든 네임스페이스에 기본 거부 정책을 적용하여 명시적으로 허용되지 않은 모든 트래픽을 차단합니다.
   - 필요한 통신만 명시적으로 허용합니다.

2. **최소 권한 원칙 적용**:
   - 포드가 필요로 하는 최소한의 네트워크 접근만 허용합니다.
   - 특정 포트와 프로토콜만 허용합니다.

3. **네임스페이스 격리**:
   - 네임스페이스를 사용하여 워크로드를 논리적으로 분리합니다.
   - 네임스페이스 간 통신을 명시적으로 제어합니다.

4. **레이블 기반 정책**:
   - 포드 레이블을 사용하여 세분화된 네트워크 정책을 정의합니다.
   - 레이블 체계를 일관되게 유지합니다.

#### 다른 옵션들의 문제점:

- **같은 네임스페이스 내 포드 간 통신만 허용**: 기본적으로 EKS는 네임스페이스 간 통신을 포함한 모든 포드 간 통신을 허용합니다.

- **명시적으로 허용된 포드 간 통신만 허용**: 이는 네트워크 정책을 구현한 후의 동작이지만, 기본 동작은 아닙니다.

- **모든 포드 간 통신 차단**: 기본적으로 EKS는 포드 간 통신을 차단하지 않습니다.

EKS의 기본 네트워크 정책은 모든 포드 간 통신을 허용하는 것입니다. 이는 개발 및 테스트 환경에서는 편리할 수 있지만, 프로덕션 환경에서는 보안을 강화하기 위해 적절한 네트워크 정책을 구현하는 것이 중요합니다.
</details>

3. Amazon EKS 클러스터에서 포드가 VPC 외부의 인터넷에 접근하기 위해 필요한 것은 무엇인가요?
   - A) 포드가 위치한 서브넷에 인터넷 게이트웨이 연결
   - B) 포드가 위치한 서브넷에 NAT 게이트웨이 또는 NAT 인스턴스 연결
   - C) 포드에 퍼블릭 IP 주소 할당
   - D) 포드에 탄력적 IP 주소 연결
   
<details>
<summary>정답 보기</summary>

**정답: B) 포드가 위치한 서브넷에 NAT 게이트웨이 또는 NAT 인스턴스 연결**

**설명:**
Amazon EKS 클러스터에서 포드가 VPC 외부의 인터넷에 접근하기 위해서는 포드가 위치한 서브넷에 NAT 게이트웨이 또는 NAT 인스턴스가 연결되어 있어야 합니다. 이는 프라이빗 서브넷에 위치한 포드가 인터넷에 접근할 수 있도록 하는 표준 방법입니다.

#### EKS 네트워킹 아키텍처:

1. **프라이빗 서브넷의 포드**:
   - EKS 워커 노드는 일반적으로 보안을 위해 프라이빗 서브넷에 배치됩니다.
   - 프라이빗 서브넷의 포드는 직접 인터넷에 접근할 수 없습니다.
   - NAT 게이트웨이 또는 NAT 인스턴스를 통해 인터넷에 접근해야 합니다.

2. **퍼블릭 서브넷의 포드**:
   - 워커 노드가 퍼블릭 서브넷에 있더라도, 포드는 기본적으로 퍼블릭 IP 주소를 할당받지 않습니다.
   - 포드는 노드의 네트워크 인터페이스를 통해 NAT되어 인터넷에 접근합니다.

#### NAT 게이트웨이 구성:

```bash
# NAT 게이트웨이 생성
aws ec2 create-nat-gateway \
  --subnet-id subnet-public1 \
  --allocation-id eipalloc-12345

# 프라이빗 서브넷의 라우팅 테이블 업데이트
aws ec2 create-route \
  --route-table-id rtb-private \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id nat-12345
```

#### CloudFormation을 사용한 VPC 구성 예시:

```yaml
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway
```

#### eksctl을 사용한 VPC 구성:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  cidr: 192.168.0.0/16
  nat:
    gateway: Single  # NAT 게이트웨이 구성
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
```

#### 다른 옵션들의 문제점:

- **포드가 위치한 서브넷에 인터넷 게이트웨이 연결**: 인터넷 게이트웨이는 퍼블릭 서브넷에 연결되며, 프라이빗 서브넷의 리소스가 인터넷에 접근하기 위해서는 NAT 게이트웨이가 필요합니다. 또한 인터넷 게이트웨이만으로는 포드가 인터넷에 접근할 수 없습니다.

- **포드에 퍼블릭 IP 주소 할당**: Amazon VPC CNI 플러그인은 포드에 퍼블릭 IP 주소를 할당하는 기능을 지원하지 않습니다. 포드는 항상 프라이빗 IP 주소를 할당받습니다.

- **포드에 탄력적 IP 주소 연결**: 포드에 직접 탄력적 IP 주소를 연결할 수 없습니다. 탄력적 IP 주소는 EC2 인스턴스 또는 네트워크 인터페이스에만 연결할 수 있습니다.

NAT 게이트웨이 또는 NAT 인스턴스는 프라이빗 서브넷의 포드가 인터넷에 접근할 수 있도록 하는 표준 방법입니다. 이는 포드의 프라이빗 IP 주소를 NAT 게이트웨이의 퍼블릭 IP 주소로 변환하여 인터넷 통신을 가능하게 합니다. 프로덕션 환경에서는 고가용성을 위해 각 가용 영역에 NAT 게이트웨이를 배치하는 것이 좋습니다.
</details>

4. Amazon EKS 클러스터에서 SecurityGroupPolicy를 사용하여 포드에 보안 그룹을 적용하기 위한 요구 사항이 아닌 것은 무엇인가요?
   - A) Amazon VPC CNI 플러그인 버전 1.7.7 이상
   - B) ENIConfig 리소스 구성
   - C) 포드에 hostNetwork: true 설정
   - D) 보안 그룹을 적용할 포드에 대한 서비스 계정 지정
   
<details>
<summary>정답 보기</summary>

**정답: C) 포드에 hostNetwork: true 설정**

**설명:**
Amazon EKS 클러스터에서 SecurityGroupPolicy를 사용하여 포드에 보안 그룹을 적용하기 위한 요구 사항이 아닌 것은 "포드에 hostNetwork: true 설정"입니다. 실제로는 hostNetwork: true로 설정된 포드에는 보안 그룹을 적용할 수 없습니다. 포드에 보안 그룹을 적용하려면 포드가 자체 네트워크 네임스페이스를 사용해야 합니다.

#### 포드 보안 그룹 기능 요구 사항:

1. **Amazon VPC CNI 플러그인 버전 1.7.7 이상**:
   - 포드 보안 그룹 기능은 Amazon VPC CNI 플러그인 버전 1.7.7 이상에서 지원됩니다.
   - 최신 버전을 사용하는 것이 좋습니다.
   ```bash
   # CNI 버전 확인
   kubectl describe daemonset aws-node -n kube-system | grep Image
   
   # CNI 업데이트
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
   ```

2. **포드 보안 그룹 기능 활성화**:
   ```bash
   # 포드 보안 그룹 기능 활성화
   kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
   
   # 또는 eksctl 사용
   eksctl utils update-cluster-config \
     --name my-cluster \
     --region us-west-2 \
     --enable-pod-security-groups
   ```

3. **보안 그룹을 적용할 포드에 대한 서비스 계정 지정**:
   - SecurityGroupPolicy에서 포드 선택기 또는 서비스 계정 선택기를 사용하여 보안 그룹을 적용할 포드를 지정해야 합니다.
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

#### 포드 보안 그룹 구성 예시:

1. **SecurityGroupPolicy 생성**:
   ```yaml
   apiVersion: vpcresources.k8s.aws/v1beta1
   kind: SecurityGroupPolicy
   metadata:
     name: db-client-policy
     namespace: default
   spec:
     serviceAccountSelector:
       matchLabels:
         role: db-client
     securityGroups:
       groupIds:
         - sg-db-client
   ```

2. **서비스 계정 생성**:
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: db-client
     namespace: default
     labels:
       role: db-client
   ```

3. **포드 배포**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: db-client-pod
   spec:
     serviceAccountName: db-client
     containers:
     - name: db-client
       image: mysql:5.7
       command: ['sleep', '3600']
   ```

#### hostNetwork: true의 문제점:

`hostNetwork: true`로 설정된 포드는 노드의 네트워크 네임스페이스를 사용하므로, 포드에 별도의 보안 그룹을 적용할 수 없습니다. 이러한 포드는 노드의 보안 그룹을 상속받습니다.

```yaml
# 이 포드에는 보안 그룹을 적용할 수 없음
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # 노드의 네트워크 네임스페이스 사용
  containers:
  - name: nginx
    image: nginx
```

#### ENIConfig 리소스 구성:

ENIConfig 리소스는 사용자 지정 네트워킹을 구성할 때 필요하지만, 포드 보안 그룹 기능만 사용하는 경우에는 필수 요구 사항이 아닙니다. 그러나 포드 보안 그룹 기능과 사용자 지정 네트워킹을 함께 사용하는 경우에는 ENIConfig 리소스를 구성해야 합니다.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

#### 포드 보안 그룹 제한 사항:

1. **리소스 제한**:
   - 각 노드에는 포드 보안 그룹을 위한 추가 ENI가 필요합니다.
   - 인스턴스 유형에 따라 지원되는 최대 ENI 수가 제한됩니다.

2. **호환성 제한**:
   - hostNetwork: true로 설정된 포드에는 적용할 수 없습니다.
   - hostPort를 사용하는 포드에는 적용할 수 없습니다.
   - 일부 CNI 플러그인과 호환되지 않을 수 있습니다.

3. **성능 영향**:
   - 포드당 추가 ENI가 필요하므로, 포드 시작 시간이 길어질 수 있습니다.
   - 노드당 최대 포드 수가 제한될 수 있습니다.

포드 보안 그룹 기능은 포드 수준에서 세분화된 네트워크 보안을 제공하는 강력한 기능입니다. 그러나 hostNetwork: true로 설정된 포드에는 이 기능을 적용할 수 없으므로, 포드 보안 그룹을 사용하려면 포드가 자체 네트워크 네임스페이스를 사용해야 합니다.
</details>
4. Amazon EKS 클러스터에서 SecurityGroupPolicy를 사용하여 포드에 보안 그룹을 적용하기 위한 요구 사항이 아닌 것은 무엇인가요?
   - A) Amazon VPC CNI 플러그인 버전 1.7.7 이상
   - B) ENIConfig 리소스 구성
   - C) 포드에 hostNetwork: true 설정
   - D) 보안 그룹을 적용할 포드에 대한 서비스 계정 지정
   
<details>
<summary>정답 보기</summary>

**정답: C) 포드에 hostNetwork: true 설정**

**설명:**
Amazon EKS 클러스터에서 SecurityGroupPolicy를 사용하여 포드에 보안 그룹을 적용하기 위한 요구 사항이 아닌 것은 "포드에 hostNetwork: true 설정"입니다. 실제로는 hostNetwork: true로 설정된 포드에는 보안 그룹을 적용할 수 없습니다. 포드에 보안 그룹을 적용하려면 포드가 자체 네트워크 네임스페이스를 사용해야 합니다.

#### 포드 보안 그룹 기능 요구 사항:

1. **Amazon VPC CNI 플러그인 버전 1.7.7 이상**:
   - 포드 보안 그룹 기능은 Amazon VPC CNI 플러그인 버전 1.7.7 이상에서 지원됩니다.
   - 최신 버전을 사용하는 것이 좋습니다.
   ```bash
   # CNI 버전 확인
   kubectl describe daemonset aws-node -n kube-system | grep Image
   
   # CNI 업데이트
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
   ```

2. **포드 보안 그룹 기능 활성화**:
   ```bash
   # 포드 보안 그룹 기능 활성화
   kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
   
   # 또는 eksctl 사용
   eksctl utils update-cluster-config \
     --name my-cluster \
     --region us-west-2 \
     --enable-pod-security-groups
   ```

3. **보안 그룹을 적용할 포드에 대한 서비스 계정 지정**:
   - SecurityGroupPolicy에서 포드 선택기 또는 서비스 계정 선택기를 사용하여 보안 그룹을 적용할 포드를 지정해야 합니다.
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

#### 포드 보안 그룹 구성 예시:

1. **SecurityGroupPolicy 생성**:
   ```yaml
   apiVersion: vpcresources.k8s.aws/v1beta1
   kind: SecurityGroupPolicy
   metadata:
     name: db-client-policy
     namespace: default
   spec:
     serviceAccountSelector:
       matchLabels:
         role: db-client
     securityGroups:
       groupIds:
         - sg-db-client
   ```

2. **서비스 계정 생성**:
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: db-client
     namespace: default
     labels:
       role: db-client
   ```

3. **포드 배포**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: db-client-pod
   spec:
     serviceAccountName: db-client
     containers:
     - name: db-client
       image: mysql:5.7
       command: ['sleep', '3600']
   ```

#### hostNetwork: true의 문제점:

`hostNetwork: true`로 설정된 포드는 노드의 네트워크 네임스페이스를 사용하므로, 포드에 별도의 보안 그룹을 적용할 수 없습니다. 이러한 포드는 노드의 보안 그룹을 상속받습니다.

```yaml
# 이 포드에는 보안 그룹을 적용할 수 없음
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # 노드의 네트워크 네임스페이스 사용
  containers:
  - name: nginx
    image: nginx
```

#### ENIConfig 리소스 구성:

ENIConfig 리소스는 사용자 지정 네트워킹을 구성할 때 필요하지만, 포드 보안 그룹 기능만 사용하는 경우에는 필수 요구 사항이 아닙니다. 그러나 포드 보안 그룹 기능과 사용자 지정 네트워킹을 함께 사용하는 경우에는 ENIConfig 리소스를 구성해야 합니다.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

#### 포드 보안 그룹 제한 사항:

1. **리소스 제한**:
   - 각 노드에는 포드 보안 그룹을 위한 추가 ENI가 필요합니다.
   - 인스턴스 유형에 따라 지원되는 최대 ENI 수가 제한됩니다.

2. **호환성 제한**:
   - hostNetwork: true로 설정된 포드에는 적용할 수 없습니다.
   - hostPort를 사용하는 포드에는 적용할 수 없습니다.
   - 일부 CNI 플러그인과 호환되지 않을 수 있습니다.

3. **성능 영향**:
   - 포드당 추가 ENI가 필요하므로, 포드 시작 시간이 길어질 수 있습니다.
   - 노드당 최대 포드 수가 제한될 수 있습니다.

포드 보안 그룹 기능은 포드 수준에서 세분화된 네트워크 보안을 제공하는 강력한 기능입니다. 그러나 hostNetwork: true로 설정된 포드에는 이 기능을 적용할 수 없으므로, 포드 보안 그룹을 사용하려면 포드가 자체 네트워크 네임스페이스를 사용해야 합니다.
</details>

5. Amazon EKS 클러스터에서 접두사 위임(Prefix Delegation) 기능의 주요 이점은 무엇인가요?
   - A) 포드 간 통신 속도 향상
   - B) 노드당 최대 포드 수 증가
   - C) 포드에 퍼블릭 IP 주소 할당 가능
   - D) 포드 네트워크 격리 강화
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드당 최대 포드 수 증가**

**설명:**
Amazon EKS 클러스터에서 접두사 위임(Prefix Delegation) 기능의 주요 이점은 노드당 최대 포드 수를 증가시키는 것입니다. 이 기능은 각 탄력적 네트워크 인터페이스(ENI)에 개별 IP 주소 대신 /28 CIDR 블록(16개 IP 주소)을 할당하여, 노드가 지원할 수 있는 최대 포드 수를 크게 늘립니다.

#### 접두사 위임 작동 방식:

1. **기본 VPC CNI 동작**:
   - 기본적으로 VPC CNI는 각 포드에 대해 ENI의 보조 IP 주소를 할당합니다.
   - 각 EC2 인스턴스 유형은 지원하는 최대 ENI 수와 ENI당 IP 주소 수가 제한되어 있습니다.
   - 이로 인해 노드당 최대 포드 수가 제한됩니다.

2. **접두사 위임 동작**:
   - 접두사 위임을 활성화하면, 각 ENI에 개별 IP 주소 대신 /28 CIDR 블록(16개 IP)이 할당됩니다.
   - 이를 통해 각 ENI가 지원할 수 있는 IP 주소 수가 크게 증가합니다.
   - 결과적으로 노드당 최대 포드 수가 증가합니다.

#### 접두사 위임 활성화:

```bash
# 접두사 위임 활성화
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# 접두사 위임 상태 확인
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

#### 접두사 위임의 이점:

1. **노드당 최대 포드 수 증가**:
   - 접두사 위임을 사용하면 노드당 최대 포드 수가 크게 증가합니다.
   - 예를 들어, m5.large 인스턴스의 경우:
     - 기본 구성: 최대 29개 포드
     - 접두사 위임 활성화: 최대 110개 이상의 포드

2. **IP 주소 효율성**:
   - 대규모 클러스터에서 IP 주소 사용을 최적화합니다.
   - VPC CIDR 범위가 제한된 환경에서 유용합니다.

3. **노드 리소스 활용도 향상**:
   - 더 많은 포드를 실행할 수 있어 노드 리소스 활용도가 향상됩니다.
   - 클러스터 비용 최적화에 도움이 됩니다.

#### 접두사 위임 제한 사항:

1. **EC2 인스턴스 지원**:
   - Nitro 기반 인스턴스만 접두사 위임을 지원합니다.
   - 이전 세대 인스턴스에서는 사용할 수 없습니다.

2. **VPC CNI 버전 요구 사항**:
   - VPC CNI 버전 1.9.0 이상이 필요합니다.
   - 이전 버전에서는 이 기능을 사용할 수 없습니다.

3. **서브넷 크기 요구 사항**:
   - 충분한 IP 주소 공간이 있는 서브넷이 필요합니다.
   - 작은 서브넷에서는 IP 주소가 빠르게 소진될 수 있습니다.

4. **전환 시 고려 사항**:
   - 기존 클러스터에서 활성화하면 새 포드만 접두사 위임을 사용합니다.
   - 모든 포드에 적용하려면 기존 포드를 재시작해야 합니다.

#### 접두사 위임 구성 예시:

```yaml
# eksctl 구성 파일
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    disableIMDSv1: true
iam:
  withOIDC: true
addons:
  - name: vpc-cni
    version: latest
    configurationValues: |
      {
        "env": {
          "ENABLE_PREFIX_DELEGATION": "true"
        }
      }
```

#### 다른 옵션들의 문제점:

- **포드 간 통신 속도 향상**: 접두사 위임은 포드 간 통신 속도에 직접적인 영향을 미치지 않습니다. 포드 간 통신 성능은 주로 네트워크 인프라와 CNI 구현에 의해 결정됩니다.

- **포드에 퍼블릭 IP 주소 할당 가능**: 접두사 위임은 포드에 퍼블릭 IP 주소를 할당하는 기능을 제공하지 않습니다. VPC CNI는 포드에 항상 프라이빗 IP 주소를 할당합니다.

- **포드 네트워크 격리 강화**: 접두사 위임은 포드 네트워크 격리와 관련이 없습니다. 네트워크 격리는 네트워크 정책이나 보안 그룹을 통해 구현됩니다.

접두사 위임은 노드당 최대 포드 수를 증가시켜 클러스터의 밀도와 효율성을 향상시키는 강력한 기능입니다. 특히 대규모 클러스터나 고밀도 워크로드를 실행하는 환경에서 유용합니다.
</details>

6. Amazon EKS 클러스터에서 CoreDNS를 사용자 지정하는 올바른 방법은 무엇인가요?
   - A) AWS Management Console에서 CoreDNS 설정 수정
   - B) CoreDNS ConfigMap 수정
   - C) EKS 클러스터 생성 시 CoreDNS 구성 지정
   - D) AWS CLI를 사용하여 CoreDNS 애드온 파라미터 업데이트
   
<details>
<summary>정답 보기</summary>

**정답: B) CoreDNS ConfigMap 수정**

**설명:**
Amazon EKS 클러스터에서 CoreDNS를 사용자 지정하는 올바른 방법은 CoreDNS ConfigMap을 수정하는 것입니다. CoreDNS는 Kubernetes의 클러스터 DNS 서버로, ConfigMap을 통해 구성됩니다. EKS에서는 `coredns` ConfigMap을 수정하여 CoreDNS의 동작을 사용자 지정할 수 있습니다.

#### CoreDNS ConfigMap 수정 방법:

1. **현재 ConfigMap 확인**:
   ```bash
   kubectl get configmap coredns -n kube-system -o yaml
   ```

2. **ConfigMap 편집**:
   ```bash
   kubectl edit configmap coredns -n kube-system
   ```

3. **또는 패치 적용**:
   ```bash
   kubectl patch configmap coredns -n kube-system --type=merge -p '{"data":{"Corefile":".:53 {\n    errors\n    health {\n        lameduck 5s\n    }\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n        pods insecure\n        fallthrough in-addr.arpa ip6.arpa\n        ttl 30\n    }\n    prometheus :9153\n    forward . /etc/resolv.conf\n    cache 30\n    loop\n    reload\n    loadbalance\n    # 사용자 지정 설정 추가\n    hosts {\n        10.0.0.1 example.com\n        fallthrough\n    }\n}"}}'
   ```

#### 일반적인 CoreDNS 사용자 지정 사례:

1. **사용자 지정 DNS 레코드 추가**:
   ```
   hosts {
       10.0.0.1 example.com
       10.0.0.2 api.example.com
       fallthrough
   }
   ```

2. **특정 도메인에 대한 전달 구성**:
   ```
   forward example.org 10.0.0.1:53
   ```

3. **DNS 캐싱 조정**:
   ```
   cache {
       success 10000
       denial 5000
       prefetch 10 10 10%
   }
   ```

4. **로깅 구성**:
   ```
   log {
       class error
   }
   ```

5. **자동 완성 비활성화**:
   ```
   kubernetes cluster.local in-addr.arpa ip6.arpa {
       pods insecure
       fallthrough in-addr.arpa ip6.arpa
       ttl 30
       autopath off
   }
   ```

#### CoreDNS 변경 후 적용:

ConfigMap을 수정한 후에는 CoreDNS 포드를 재시작하여 변경 사항을 적용해야 합니다:

```bash
# CoreDNS 포드 확인
kubectl get pods -n kube-system -l k8s-app=kube-dns

# CoreDNS 포드 재시작
kubectl rollout restart deployment coredns -n kube-system

# 변경 사항 적용 확인
kubectl logs -n kube-system -l k8s-app=kube-dns
```

#### CoreDNS 성능 최적화:

1. **자동 확장 구성**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: coredns-autoscaler
     namespace: kube-system
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: coredns
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 60
   ```

2. **리소스 요청 및 제한 조정**:
   ```bash
   kubectl patch deployment coredns -n kube-system --type=json -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources", "value": {"requests": {"cpu": "100m", "memory": "70Mi"}, "limits": {"cpu": "200m", "memory": "170Mi"}}}]'
   ```

#### 다른 옵션들의 문제점:

- **AWS Management Console에서 CoreDNS 설정 수정**: AWS Management Console에서는 CoreDNS 설정을 직접 수정할 수 있는 인터페이스를 제공하지 않습니다.

- **EKS 클러스터 생성 시 CoreDNS 구성 지정**: EKS 클러스터 생성 시 CoreDNS의 세부 구성을 지정할 수 없습니다. 클러스터 생성 후 ConfigMap을 수정해야 합니다.

- **AWS CLI를 사용하여 CoreDNS 애드온 파라미터 업데이트**: AWS CLI를 사용하여 CoreDNS 애드온 버전을 업데이트할 수는 있지만, 세부 구성을 수정할 수는 없습니다. 구성 변경은 ConfigMap을 통해 이루어져야 합니다.

```bash
# CoreDNS 애드온 버전 업데이트 (구성 변경이 아님)
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name coredns \
  --addon-version v1.8.7-eksbuild.2 \
  --resolve-conflicts PRESERVE
```

CoreDNS ConfigMap을 수정하는 것은 EKS 클러스터에서 DNS 설정을 사용자 지정하는 표준 방법입니다. 이를 통해 사용자 지정 DNS 레코드 추가, 특정 도메인에 대한 전달 구성, 캐싱 동작 조정 등 다양한 사용자 지정이 가능합니다.
</details>
7. Amazon EKS 클러스터에서 멀티 테넌시를 구현하는 가장 효과적인 방법은 무엇인가요?
   - A) 테넌트별로 별도의 EKS 클러스터 생성
   - B) 테넌트별로 별도의 네임스페이스 사용 및 RBAC, 네트워크 정책, 리소스 쿼터 적용
   - C) 테넌트별로 별도의 노드 그룹 생성 및 노드 선택기 사용
   - D) 테넌트별로 별도의 VPC 사용
   
<details>
<summary>정답 보기</summary>

**정답: B) 테넌트별로 별도의 네임스페이스 사용 및 RBAC, 네트워크 정책, 리소스 쿼터 적용**

**설명:**
Amazon EKS 클러스터에서 멀티 테넌시를 구현하는 가장 효과적인 방법은 테넌트별로 별도의 네임스페이스를 사용하고, RBAC(역할 기반 접근 제어), 네트워크 정책, 리소스 쿼터를 적용하는 것입니다. 이 접근 방식은 단일 클러스터 내에서 여러 테넌트를 효율적으로 격리하면서도 리소스를 공유할 수 있게 해줍니다.

#### 네임스페이스 기반 멀티 테넌시 구현:

1. **테넌트별 네임스페이스 생성**:
   ```bash
   # 테넌트별 네임스페이스 생성
   kubectl create namespace tenant-a
   kubectl create namespace tenant-b
   ```

2. **RBAC 구성**:
   ```yaml
   # 테넌트 역할 생성
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: tenant-full-access
     namespace: tenant-a
   rules:
   - apiGroups: ["", "apps", "batch"]
     resources: ["*"]
     verbs: ["*"]
   ---
   # 테넌트 사용자에게 역할 바인딩
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: tenant-a-access
     namespace: tenant-a
   subjects:
   - kind: Group
     name: tenant-a-users
     apiGroup: rbac.authorization.k8s.io
   roleRef:
     kind: Role
     name: tenant-full-access
     apiGroup: rbac.authorization.k8s.io
   ```

3. **네트워크 정책 적용**:
   ```yaml
   # 테넌트 간 통신 제한
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: deny-cross-tenant-traffic
     namespace: tenant-a
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: tenant-a
     egress:
     - to:
       - namespaceSelector:
           matchLabels:
             name: tenant-a
     - to:
       - namespaceSelector:
           matchLabels:
             name: kube-system
   ```

4. **리소스 쿼터 설정**:
   ```yaml
   # 테넌트 리소스 쿼터
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: tenant-quota
     namespace: tenant-a
   spec:
     hard:
       requests.cpu: "10"
       requests.memory: 20Gi
       limits.cpu: "20"
       limits.memory: 40Gi
       pods: "50"
       services: "20"
       persistentvolumeclaims: "30"
       secrets: "100"
       configmaps: "100"
   ```

5. **LimitRange 설정**:
   ```yaml
   # 기본 리소스 제한 설정
   apiVersion: v1
   kind: LimitRange
   metadata:
     name: tenant-limits
     namespace: tenant-a
   spec:
     limits:
     - default:
         cpu: 500m
         memory: 512Mi
       defaultRequest:
         cpu: 100m
         memory: 256Mi
       type: Container
   ```

#### 네임스페이스 기반 멀티 테넌시의 이점:

1. **리소스 효율성**:
   - 단일 클러스터를 여러 테넌트가 공유하므로 리소스 활용도가 향상됩니다.
   - 컨트롤 플레인 비용이 절감됩니다.

2. **관리 용이성**:
   - 단일 클러스터를 관리하므로 운영 오버헤드가 감소합니다.
   - 중앙 집중식 모니터링 및 로깅이 가능합니다.

3. **유연성**:
   - 테넌트 추가 및 제거가 간단합니다.
   - 테넌트별 정책을 쉽게 적용할 수 있습니다.

4. **비용 효율성**:
   - 클러스터 오버헤드를 여러 테넌트가 공유합니다.
   - 리소스 활용도가 향상되어 비용이 절감됩니다.

#### 네임스페이스 기반 멀티 테넌시의 단점:

1. **격리 수준 제한**:
   - 네임스페이스는 논리적 격리만 제공하며, 완전한 물리적 격리는 제공하지 않습니다.
   - 커널 수준 취약점에 노출될 수 있습니다.

2. **리소스 경합**:
   - 테넌트 간 리소스 경합이 발생할 수 있습니다.
   - 노이지 네이버(Noisy Neighbor) 문제가 발생할 수 있습니다.

3. **보안 위험**:
   - 클러스터 수준 권한 상승 위험이 있습니다.
   - 컨테이너 이스케이프 취약점에 노출될 수 있습니다.

#### 다른 멀티 테넌시 접근 방식:

1. **클러스터 기반 멀티 테넌시 (테넌트별 별도의 EKS 클러스터)**:
   - 가장 강력한 격리 제공
   - 관리 오버헤드 증가
   - 비용 증가
   - 대규모 엔터프라이즈 환경이나 규제가 엄격한 산업에 적합

2. **노드 기반 멀티 테넌시 (테넌트별 별도의 노드 그룹)**:
   - 중간 수준의 격리 제공
   - 테넌트별 노드 수준 사용자 지정 가능
   - 리소스 활용도 감소
   - 보안 요구 사항이 높지만 비용도 고려해야 하는 경우에 적합

3. **하이브리드 접근 방식**:
   - 중요한 테넌트에는 전용 클러스터 제공
   - 덜 중요한 테넌트는 공유 클러스터에서 네임스페이스로 분리
   - 유연성과 비용 효율성 균형

#### 다른 옵션들의 문제점:

- **테넌트별로 별도의 EKS 클러스터 생성**: 가장 강력한 격리를 제공하지만, 관리 오버헤드와 비용이 크게 증가합니다. 테넌트 수가 많은 경우 확장성 문제가 발생할 수 있습니다.

- **테넌트별로 별도의 노드 그룹 생성 및 노드 선택기 사용**: 노드 수준의 격리를 제공하지만, 리소스 활용도가 감소하고 관리가 복잡해질 수 있습니다. 또한 노드 그룹만으로는 완전한 격리를 제공하지 않습니다.

- **테넌트별로 별도의 VPC 사용**: EKS 클러스터는 단일 VPC 내에서 생성되므로, 테넌트별로 별도의 VPC를 사용하려면 테넌트별로 별도의 클러스터를 생성해야 합니다. 이는 관리 오버헤드와 비용을 크게 증가시킵니다.

네임스페이스 기반 멀티 테넌시는 대부분의 사용 사례에서 격리, 관리 용이성, 비용 효율성 간의 최적의 균형을 제공합니다. 그러나 보안 요구 사항이 매우 높은 경우에는 클러스터 기반 멀티 테넌시를 고려해야 할 수 있습니다.
</details>

8. Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 선택할 때 고려해야 할 요소가 아닌 것은 무엇인가요?
   - A) 워크로드의 CPU 및 메모리 요구 사항
   - B) 비용 최적화
   - C) 클러스터의 Kubernetes 버전
   - D) 필요한 포드 밀도
   
<details>
<summary>정답 보기</summary>

**정답: C) 클러스터의 Kubernetes 버전**

**설명:**
Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 선택할 때 고려해야 할 요소가 아닌 것은 "클러스터의 Kubernetes 버전"입니다. Kubernetes 버전은 지원되는 기능에 영향을 미치지만, 노드 그룹의 인스턴스 유형 선택에는 직접적인 영향을 미치지 않습니다. 인스턴스 유형은 주로 워크로드 요구 사항, 비용, 포드 밀도 등에 따라 결정됩니다.

#### 노드 그룹 인스턴스 유형 선택 시 실제 고려 요소:

1. **워크로드의 CPU 및 메모리 요구 사항**:
   - 워크로드의 리소스 요구 사항에 맞는 인스턴스 유형 선택
   - CPU 집약적 워크로드: c5, c6g 등의 컴퓨팅 최적화 인스턴스
   - 메모리 집약적 워크로드: r5, r6g 등의 메모리 최적화 인스턴스
   - 균형 잡힌 워크로드: m5, m6g 등의 범용 인스턴스
   - GPU 워크로드: p3, g4dn 등의 가속 컴퓨팅 인스턴스

2. **비용 최적화**:
   - 온디맨드 vs 스팟 인스턴스
   - 예약 인스턴스 또는 Savings Plans
   - ARM 기반 Graviton 인스턴스(예: m6g, c6g)를 통한 비용 절감
   - 적절한 크기의 인스턴스 선택 (오버프로비저닝 방지)

3. **필요한 포드 밀도**:
   - 인스턴스 유형에 따라 지원되는 최대 포드 수가 다름
   - 각 인스턴스 유형의 ENI 수와 ENI당 IP 주소 수 고려
   - 고밀도 워크로드의 경우 더 많은 ENI와 IP 주소를 지원하는 인스턴스 유형 선택

4. **네트워킹 요구 사항**:
   - 네트워크 대역폭 요구 사항
   - 향상된 네트워킹 지원 (ENA, EFA 등)
   - 인스턴스 유형에 따라 네트워크 성능이 다름

5. **스토리지 요구 사항**:
   - 로컬 인스턴스 스토리지 필요 여부 (예: i3, d3 인스턴스)
   - EBS 최적화 지원
   - 스토리지 처리량 및 IOPS 요구 사항

6. **가용성 요구 사항**:
   - 인스턴스 유형의 리전별 가용성
   - 스팟 인스턴스 사용 시 중단 가능성
   - 가용 영역별 인스턴스 유형 가용성

#### 인스턴스 유형 선택 예시:

1. **웹 애플리케이션 서버**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
     - name: web-servers
       instanceType: m5.large
       minSize: 2
       maxSize: 10
       labels:
         role: web
   ```

2. **데이터베이스 워크로드**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
     - name: database-nodes
       instanceType: r5.xlarge
       minSize: 3
       maxSize: 5
       labels:
         role: database
   ```

3. **배치 처리 워크로드**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
     - name: batch-processors
       instanceType: c5.2xlarge
       minSize: 0
       maxSize: 20
       labels:
         role: batch
   ```

4. **비용 최적화 워크로드**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   metadata:
     name: my-cluster
     region: us-west-2
   managedNodeGroups:
     - name: spot-workers
       instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
       minSize: 2
       maxSize: 10
       spot: true
       labels:
         lifecycle: spot
   ```

#### Kubernetes 버전과 인스턴스 유형의 관계:

Kubernetes 버전은 다음과 같은 측면에서 클러스터에 영향을 미치지만, 인스턴스 유형 선택에는 직접적인 영향을 미치지 않습니다:

1. **지원되는 기능**:
   - 새로운 Kubernetes 버전은 새로운 기능을 제공합니다.
   - 일부 기능은 특정 버전에서만 사용 가능합니다.

2. **API 호환성**:
   - 새로운 버전에서는 일부 API가 변경되거나 제거될 수 있습니다.
   - 애플리케이션이 특정 API에 의존하는 경우 버전 선택이 중요합니다.

3. **보안 패치**:
   - 최신 버전은 최신 보안 패치를 포함합니다.
   - 오래된 버전은 보안 취약점에 노출될 수 있습니다.

4. **지원 기간**:
   - 각 Kubernetes 버전은 제한된 기간 동안만 지원됩니다.
   - EKS는 각 버전을 약 14개월 동안 지원합니다.

인스턴스 유형 선택은 주로 워크로드의 리소스 요구 사항, 비용 최적화, 포드 밀도 등에 따라 결정되며, Kubernetes 버전과는 직접적인 관련이 없습니다. 따라서 "클러스터의 Kubernetes 버전"은 노드 그룹의 인스턴스 유형을 선택할 때 고려해야 할 주요 요소가 아닙니다.
</details>
9. Amazon EKS 클러스터에서 노드 그룹 업데이트 중 포드 중단을 최소화하기 위한 가장 효과적인 방법은 무엇인가요?
   - A) 롤링 업데이트 전략 사용
   - B) PodDisruptionBudget 구성
   - C) 노드 그룹 업데이트 전 모든 포드 수동 마이그레이션
   - D) 블루/그린 배포 전략 사용
   
<details>
<summary>정답 보기</summary>

**정답: B) PodDisruptionBudget 구성**

**설명:**
Amazon EKS 클러스터에서 노드 그룹 업데이트 중 포드 중단을 최소화하기 위한 가장 효과적인 방법은 PodDisruptionBudget(PDB)을 구성하는 것입니다. PDB는 자발적 중단(voluntary disruption) 중에 동시에 중단될 수 있는 포드의 수를 제한하여 애플리케이션의 가용성을 보장합니다. 노드 그룹 업데이트는 자발적 중단으로 간주되므로, PDB를 통해 업데이트 중 애플리케이션의 가용성을 유지할 수 있습니다.

#### PodDisruptionBudget 작동 방식:

1. **PDB 정의**:
   - `minAvailable`: 항상 사용 가능해야 하는 최소 포드 수 또는 비율 지정
   - `maxUnavailable`: 동시에 사용할 수 없는 최대 포드 수 또는 비율 지정
   - 두 옵션 중 하나만 지정해야 함

2. **PDB 적용**:
   - 노드 드레이닝(draining) 중 Kubernetes는 PDB를 준수
   - PDB 위반 시 드레이닝 프로세스가 일시 중지됨
   - 새 포드가 다른 노드에서 실행되면 드레이닝 계속 진행

#### PodDisruptionBudget 예시:

```yaml
# 최소 2개의 포드가 항상 사용 가능하도록 보장
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

```yaml
# 최대 50%의 포드만 동시에 사용 불가능하도록 제한
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  maxUnavailable: 50%
  selector:
    matchLabels:
      app: my-app
```

#### EKS 노드 그룹 업데이트 프로세스:

1. **업데이트 시작**:
   - 새 노드 생성
   - 새 노드가 클러스터에 조인

2. **노드 드레이닝**:
   - 기존 노드에 코드네이션(cordoning) 적용 (새 포드 스케줄링 방지)
   - 기존 노드에서 포드 드레이닝 (포드 이전)
   - PDB 준수하며 포드 이전

3. **노드 종료**:
   - 모든 포드가 이전되면 노드 종료
   - 다음 노드에 대해 프로세스 반복

#### PDB 구성 모범 사례:

1. **적절한 복제본 수 설정**:
   - PDB가 효과적으로 작동하려면 충분한 복제본이 필요
   - 최소 3개 이상의 복제본 권장

2. **적절한 PDB 값 선택**:
   - 애플리케이션 특성에 맞는 값 선택
   - 너무 제한적인 값은 업데이트를 지연시킬 수 있음
   - 너무 느슨한 값은 가용성에 영향을 줄 수 있음

3. **모든 중요 워크로드에 PDB 적용**:
   - 상태 저장(stateful) 애플리케이션
   - 사용자 대면(user-facing) 서비스
   - 시스템 구성 요소

4. **PDB 테스트**:
   - 업데이트 전 PDB 동작 테스트
   - 드레이닝 시뮬레이션으로 가용성 확인

#### 노드 그룹 업데이트 구성:

```bash
# 관리형 노드 그룹 업데이트 구성 수정
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# 또는 eksctl 사용
eksctl update nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --max-unavailable 1
```

#### 다른 옵션들의 문제점:

- **롤링 업데이트 전략 사용**: EKS 관리형 노드 그룹은 이미 기본적으로 롤링 업데이트 전략을 사용합니다. 그러나 롤링 업데이트만으로는 포드 중단을 제어할 수 없으며, PDB와 함께 사용해야 효과적입니다.

- **노드 그룹 업데이트 전 모든 포드 수동 마이그레이션**: 이는 시간이 많이 소요되고 오류가 발생하기 쉬운 수동 프로세스입니다. 또한 대규모 클러스터에서는 실용적이지 않습니다.

- **블루/그린 배포 전략 사용**: 블루/그린 배포는 새 노드 그룹을 생성하고 워크로드를 마이그레이션한 후 기존 노드 그룹을 삭제하는 방식입니다. 이는 효과적인 전략이지만, 리소스 중복으로 인한 비용 증가와 복잡한 구현이 단점입니다. 또한 PDB와 함께 사용하는 것이 좋습니다.

PodDisruptionBudget은 노드 그룹 업데이트 중 포드 중단을 제어하는 Kubernetes 네이티브 방식으로, 애플리케이션의 가용성을 보장하면서 노드 그룹을 안전하게 업데이트할 수 있게 해줍니다. 따라서 노드 그룹 업데이트 중 포드 중단을 최소화하기 위한 가장 효과적인 방법은 PodDisruptionBudget을 구성하는 것입니다.
</details>

10. Amazon EKS 클러스터에서 노드 그룹의 Auto Scaling 동작을 제어하는 데 사용되지 않는 것은 무엇인가요?
    - A) Cluster Autoscaler
    - B) Karpenter
    - C) Horizontal Pod Autoscaler
    - D) Vertical Pod Autoscaler
    
<details>
<summary>정답 보기</summary>

**정답: D) Vertical Pod Autoscaler**

**설명:**
Amazon EKS 클러스터에서 노드 그룹의 Auto Scaling 동작을 제어하는 데 사용되지 않는 것은 Vertical Pod Autoscaler(VPA)입니다. VPA는 포드의 CPU 및 메모리 요청을 자동으로 조정하는 데 사용되지만, 노드 그룹의 크기를 조정하는 데는 사용되지 않습니다. 노드 그룹의 Auto Scaling은 주로 Cluster Autoscaler, Karpenter, 그리고 간접적으로 Horizontal Pod Autoscaler(HPA)에 의해 제어됩니다.

#### 노드 그룹 Auto Scaling 도구:

1. **Cluster Autoscaler**:
   - 노드 그룹의 크기를 자동으로 조정하는 Kubernetes 구성 요소
   - 포드가 스케줄링될 수 없을 때 노드 추가
   - 노드가 충분히 활용되지 않을 때 노드 제거
   - AWS Auto Scaling Group과 통합

   ```yaml
   # Cluster Autoscaler 배포
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: cluster-autoscaler
     namespace: kube-system
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: cluster-autoscaler
     template:
       metadata:
         labels:
           app: cluster-autoscaler
       spec:
         serviceAccountName: cluster-autoscaler
         containers:
         - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
           name: cluster-autoscaler
           command:
           - ./cluster-autoscaler
           - --v=4
           - --stderrthreshold=info
           - --cloud-provider=aws
           - --skip-nodes-with-local-storage=false
           - --expander=least-waste
           - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
   ```

2. **Karpenter**:
   - AWS의 오픈 소스 노드 프로비저닝 프로젝트
   - 워크로드 요구 사항에 맞는 최적의 인스턴스 유형 선택
   - 빠른 노드 프로비저닝 (초 단위)
   - 비용 최적화 및 통합 수명 주기 관리

   ```yaml
   # Karpenter Provisioner
   apiVersion: karpenter.sh/v1alpha5
   kind: Provisioner
   metadata:
     name: default
   spec:
     requirements:
       - key: karpenter.sh/capacity-type
         operator: In
         values: ["spot", "on-demand"]
     limits:
       resources:
         cpu: 1000
         memory: 1000Gi
     provider:
       subnetSelector:
         karpenter.sh/discovery: "true"
       securityGroupSelector:
         karpenter.sh/discovery: "true"
     ttlSecondsAfterEmpty: 30
   ```

3. **Horizontal Pod Autoscaler (HPA)**:
   - 포드의 복제본 수를 자동으로 조정
   - CPU, 메모리 또는 사용자 지정 메트릭에 기반
   - 간접적으로 노드 그룹 Auto Scaling 트리거 가능
   - Cluster Autoscaler 또는 Karpenter와 함께 작동

   ```yaml
   # Horizontal Pod Autoscaler
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: my-app-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: my-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

#### Vertical Pod Autoscaler (VPA):

VPA는 포드의 CPU 및 메모리 요청을 자동으로 조정하는 데 사용되지만, 노드 그룹의 크기를 직접 조정하지는 않습니다:

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```

VPA는 다음과 같은 기능을 제공합니다:
- 포드의 리소스 요청 자동 조정
- 리소스 사용량 기반 권장 사항 제공
- 포드 재시작을 통한 리소스 요청 업데이트

그러나 VPA는 노드 그룹의 크기를 직접 조정하지 않으며, 포드 수준의 리소스 할당에만 영향을 미칩니다.

#### 노드 그룹 Auto Scaling 전략:

1. **반응형 확장 (Reactive Scaling)**:
   - Cluster Autoscaler 사용
   - 포드가 스케줄링될 수 없을 때 노드 추가
   - 리소스 활용도가 낮을 때 노드 제거
   - 예측 가능한 워크로드에 적합

2. **예측형 확장 (Predictive Scaling)**:
   - AWS Auto Scaling 예측 조정 사용
   - 과거 패턴을 기반으로 미래 수요 예측
   - 수요 증가 전에 미리 용량 확보
   - 주기적인 패턴이 있는 워크로드에 적합

3. **이벤트 기반 확장 (Event-driven Scaling)**:
   - KEDA(Kubernetes Event-driven Autoscaling) 사용
   - 외부 이벤트 또는 메트릭에 기반한 확장
   - 큐 길이, 이벤트 수 등에 따른 확장
   - 배치 처리, 이벤트 처리 워크로드에 적합

#### 다른 옵션들의 설명:

- **Cluster Autoscaler**: 노드 그룹의 Auto Scaling을 직접 제어하는 Kubernetes 구성 요소로, 포드 스케줄링 요구 사항에 따라 노드를 추가하거나 제거합니다.

- **Karpenter**: AWS의 오픈 소스 노드 프로비저닝 프로젝트로, 워크로드 요구 사항에 맞는 최적의 인스턴스를 빠르게 프로비저닝합니다. Cluster Autoscaler의 대안으로 사용될 수 있습니다.

- **Horizontal Pod Autoscaler**: 포드의 복제본 수를 자동으로 조정하며, 이로 인해 더 많은 포드가 생성되면 간접적으로 Cluster Autoscaler 또는 Karpenter를 트리거하여 노드 그룹의 크기를 조정할 수 있습니다.

Vertical Pod Autoscaler는 포드의 리소스 요청을 조정하는 데 사용되지만, 노드 그룹의 크기를 직접 조정하지는 않습니다. 따라서 노드 그룹의 Auto Scaling 동작을 제어하는 데 사용되지 않는 것은 Vertical Pod Autoscaler입니다.
</details>

## 실습 문제

### 실습 1: EKS 클러스터에서 네트워크 정책 구현

**시나리오:**
당신은 회사의 보안 엔지니어로, EKS 클러스터에서 마이크로서비스 간의 네트워크 트래픽을 제한해야 합니다. 특히, 프론트엔드 서비스만 백엔드 API에 접근할 수 있도록 하고, 데이터베이스는 백엔드 API에서만 접근할 수 있도록 해야 합니다.

**요구사항:**
1. Calico 네트워크 정책 엔진 설치
2. 기본 거부 정책 구현
3. 프론트엔드에서 백엔드로의 트래픽 허용
4. 백엔드에서 데이터베이스로의 트래픽 허용
5. 정책 테스트

**해결 방법:**

<details>
<summary>해결 방법 보기</summary>

#### 1. Calico 네트워크 정책 엔진 설치

```bash
# Tigera Operator 설치
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# 설치 확인
kubectl get pods -n calico-system
```

#### 2. 네임스페이스 및 샘플 애플리케이션 생성

```bash
# 네임스페이스 생성
kubectl create namespace microservices

# 프론트엔드 배포
cat > frontend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: microservices
  labels:
    app: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: microservices
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f frontend.yaml

# 백엔드 배포
cat > backend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: microservices
  labels:
    app: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: httpd
        image: httpd:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: microservices
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f backend.yaml

# 데이터베이스 배포
cat > database.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
  namespace: microservices
  labels:
    app: database
spec:
  replicas: 1
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      containers:
      - name: postgres
        image: postgres:13-alpine
        env:
        - name: POSTGRES_PASSWORD
          value: "password"
        ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: database
  namespace: microservices
spec:
  selector:
    app: database
  ports:
  - port: 5432
    targetPort: 5432
EOF

kubectl apply -f database.yaml

# 배포 확인
kubectl get pods -n microservices
kubectl get services -n microservices
```

#### 3. 기본 거부 정책 구현

```bash
# 기본 거부 정책 생성
cat > default-deny.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: microservices
spec:
  selector: all()
  types:
  - Ingress
  - Egress
EOF

kubectl apply -f default-deny.yaml
```

#### 4. 프론트엔드에서 백엔드로의 트래픽 허용

```bash
# 프론트엔드에서 백엔드로의 트래픽 허용 정책
cat > frontend-to-backend.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-to-backend
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'frontend'
    destination:
      ports:
      - 80
EOF

kubectl apply -f frontend-to-backend.yaml

# 프론트엔드에서 외부 DNS 및 API 접근 허용
cat > frontend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: microservices
spec:
  selector: app == 'frontend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'backend'
      ports:
      - 80
  # DNS 접근 허용
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f frontend-egress.yaml
```

#### 5. 백엔드에서 데이터베이스로의 트래픽 허용

```bash
# 백엔드에서 데이터베이스로의 트래픽 허용 정책
cat > backend-to-database.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-to-database
  namespace: microservices
spec:
  selector: app == 'database'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'backend'
    destination:
      ports:
      - 5432
EOF

kubectl apply -f backend-to-database.yaml

# 백엔드에서 외부 DNS 및 데이터베이스 접근 허용
cat > backend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-egress
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'database'
      ports:
      - 5432
  # DNS 접근 허용
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f backend-egress.yaml
```

#### 6. 정책 테스트

```bash
# 프론트엔드 포드 이름 가져오기
FRONTEND_POD=$(kubectl get pods -n microservices -l app=frontend -o jsonpath='{.items[0].metadata.name}')

# 백엔드 포드 이름 가져오기
BACKEND_POD=$(kubectl get pods -n microservices -l app=backend -o jsonpath='{.items[0].metadata.name}')

# 데이터베이스 포드 이름 가져오기
DATABASE_POD=$(kubectl get pods -n microservices -l app=database -o jsonpath='{.items[0].metadata.name}')

# 프론트엔드에서 백엔드로의 연결 테스트 (성공해야 함)
kubectl exec -it $FRONTEND_POD -n microservices -- wget -O- --timeout=2 http://backend

# 프론트엔드에서 데이터베이스로의 연결 테스트 (실패해야 함)
kubectl exec -it $FRONTEND_POD -n microservices -- nc -zv database 5432

# 백엔드에서 데이터베이스로의 연결 테스트 (성공해야 함)
kubectl exec -it $BACKEND_POD -n microservices -- nc -zv database 5432

# 백엔드에서 외부 사이트로의 연결 테스트 (실패해야 함)
kubectl exec -it $BACKEND_POD -n microservices -- wget -O- --timeout=2 https://www.example.com
```

#### 7. 네트워크 정책 시각화 (선택 사항)

```bash
# Calico 네트워크 정책 시각화 도구 설치
kubectl apply -f https://raw.githubusercontent.com/tigera/ccol/master/manifests/tigera-policies-viewer/tigera-policies-viewer.yaml

# 포트 포워딩 설정
kubectl port-forward -n tigera-policies-viewer svc/tigera-policies-viewer 8080:8080

# 브라우저에서 http://localhost:8080 접속하여 정책 시각화
```

이 실습을 통해 EKS 클러스터에서 Calico를 사용하여 마이크로서비스 간의 네트워크 트래픽을 제한하는 방법을 배웠습니다. 기본 거부 정책을 구현하고, 필요한 트래픽만 명시적으로 허용함으로써 최소 권한 원칙을 적용했습니다. 이러한 네트워크 정책은 클러스터 내 서비스 간의 통신을 제한하여 보안을 강화하고, 잠재적인 공격 표면을 줄이는 데 도움이 됩니다.
</details>
### 실습 2: EKS 클러스터에서 IRSA 구성 및 S3 접근

**시나리오:**
당신은 회사의 DevOps 엔지니어로, EKS 클러스터에서 실행되는 애플리케이션이 S3 버킷에 안전하게 접근해야 하는 상황에 있습니다. 보안 모범 사례에 따라 노드 IAM 역할을 공유하는 대신 IRSA(IAM Roles for Service Accounts)를 사용하여 특정 포드에만 필요한 권한을 부여하려고 합니다.

**요구사항:**
1. EKS 클러스터에 OIDC 제공자 연결
2. S3 접근 권한이 있는 IAM 역할 생성
3. Kubernetes 서비스 계정 생성 및 IAM 역할 연결
4. 서비스 계정을 사용하는 포드 배포
5. S3 접근 테스트

**해결 방법:**

<details>
<summary>해결 방법 보기</summary>

#### 1. EKS 클러스터에 OIDC 제공자 연결

```bash
# 클러스터 이름 설정
CLUSTER_NAME=my-cluster
REGION=us-west-2

# OIDC 제공자 URL 가져오기
OIDC_PROVIDER=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# OIDC 제공자가 이미 존재하는지 확인
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# OIDC 제공자가 없는 경우 생성
if [ $? -ne 0 ]; then
  echo "Creating OIDC provider..."
  eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --region $REGION --approve
else
  echo "OIDC provider already exists."
fi
```

#### 2. S3 접근 권한이 있는 IAM 역할 생성

```bash
# 계정 ID 가져오기
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 네임스페이스 및 서비스 계정 이름 설정
NAMESPACE=default
SERVICE_ACCOUNT_NAME=s3-access-sa

# 신뢰 정책 생성
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT_NAME}"
        }
      }
    }
  ]
}
EOF

# IAM 역할 생성
ROLE_NAME=eks-s3-access-role
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json

# S3 읽기 전용 정책 연결
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# 역할 ARN 가져오기
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query Role.Arn --output text)
echo "Role ARN: $ROLE_ARN"
```

#### 3. Kubernetes 서비스 계정 생성 및 IAM 역할 연결

```bash
# 서비스 계정 생성
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${SERVICE_ACCOUNT_NAME}
  namespace: ${NAMESPACE}
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml

# 서비스 계정 확인
kubectl get serviceaccount $SERVICE_ACCOUNT_NAME -o yaml
```

#### 4. 서비스 계정을 사용하는 포드 배포

```bash
# 테스트 포드 배포
cat > s3-test-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-test-pod
  namespace: ${NAMESPACE}
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f s3-test-pod.yaml

# 포드 상태 확인
kubectl get pod s3-test-pod
kubectl describe pod s3-test-pod
```

#### 5. S3 접근 테스트

```bash
# S3 버킷 목록 조회 테스트
kubectl exec -it s3-test-pod -- aws s3 ls

# 특정 S3 버킷의 객체 목록 조회 테스트 (버킷 이름 변경 필요)
kubectl exec -it s3-test-pod -- aws s3 ls s3://my-bucket/

# AWS 자격 증명 확인
kubectl exec -it s3-test-pod -- aws sts get-caller-identity

# 환경 변수 확인
kubectl exec -it s3-test-pod -- env | grep AWS
```

#### 6. 비교를 위한 일반 포드 배포

```bash
# 일반 서비스 계정을 사용하는 포드 배포
cat > regular-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: regular-pod
  namespace: ${NAMESPACE}
spec:
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f regular-pod.yaml

# 일반 포드에서 S3 접근 테스트 (노드 IAM 역할에 S3 접근 권한이 없다면 실패해야 함)
kubectl exec -it regular-pod -- aws s3 ls
```

#### 7. 정리

```bash
# 포드 삭제
kubectl delete pod s3-test-pod regular-pod

# 서비스 계정 삭제
kubectl delete serviceaccount $SERVICE_ACCOUNT_NAME

# IAM 역할 정리 (선택 사항)
aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name $ROLE_NAME
```

#### IRSA 작동 원리 설명:

1. **OIDC 제공자 연결**:
   - EKS 클러스터는 OIDC 제공자로 구성됩니다.
   - 이를 통해 Kubernetes 서비스 계정 토큰이 AWS IAM에서 신뢰할 수 있는 인증 메커니즘이 됩니다.

2. **IAM 역할 신뢰 정책**:
   - IAM 역할의 신뢰 정책은 특정 Kubernetes 서비스 계정만 역할을 맡을 수 있도록 제한합니다.
   - 조건문을 사용하여 특정 네임스페이스의 특정 서비스 계정으로 제한합니다.

3. **서비스 계정 주석**:
   - `eks.amazonaws.com/role-arn` 주석은 서비스 계정이 맡을 IAM 역할을 지정합니다.
   - 이 주석은 EKS Pod Identity Webhook에 의해 처리됩니다.

4. **환경 변수 주입**:
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

## 고급 주제

다음은 Amazon EKS 클러스터 생성에 관한 고급 주제에 대한 질문입니다. 이 섹션은 EKS 클러스터 생성의 심화 개념과 모범 사례에 대한 이해를 테스트합니다.

1. Amazon EKS 클러스터에서 접두사 위임(Prefix Delegation)을 활성화할 때 발생하는 변화가 아닌 것은 무엇인가요?
   - A) 각 ENI에 /28 CIDR 블록(16개 IP)이 할당됨
   - B) 노드당 최대 포드 수 증가
   - C) 포드 시작 시간 단축
   - D) IP 주소 사용 효율성 향상
   
<details>
<summary>정답 보기</summary>

**정답: C) 포드 시작 시간 단축**

**설명:**
Amazon EKS 클러스터에서 접두사 위임(Prefix Delegation)을 활성화할 때 발생하는 변화가 아닌 것은 "포드 시작 시간 단축"입니다. 실제로는 접두사 위임을 활성화하면 포드 시작 시간이 단축되지 않으며, 오히려 약간 증가할 수 있습니다. 접두사 위임의 주요 이점은 노드당 최대 포드 수 증가와 IP 주소 사용 효율성 향상입니다.

#### 접두사 위임 활성화 시 실제 변화:

1. **각 ENI에 /28 CIDR 블록(16개 IP)이 할당됨**:
   - 기본적으로 VPC CNI는 각 포드에 대해 ENI의 보조 IP 주소를 할당합니다.
   - 접두사 위임을 활성화하면, 각 ENI에 개별 IP 주소 대신 /28 CIDR 블록(16개 IP)이 할당됩니다.
   - 이를 통해 각 ENI가 지원할 수 있는 IP 주소 수가 크게 증가합니다.

2. **노드당 최대 포드 수 증가**:
   - 접두사 위임을 사용하면 노드당 최대 포드 수가 크게 증가합니다.
   - 예를 들어, m5.large 인스턴스의 경우:
     - 기본 구성: 최대 29개 포드
     - 접두사 위임 활성화: 최대 110개 이상의 포드

3. **IP 주소 사용 효율성 향상**:
   - 대규모 클러스터에서 IP 주소 사용을 최적화합니다.
   - VPC CIDR 범위가 제한된 환경에서 유용합니다.
   - 더 많은 포드를 동일한 IP 주소 공간 내에서 실행할 수 있습니다.

#### 접두사 위임이 포드 시작 시간에 미치는 영향:

접두사 위임은 포드 시작 시간을 단축하지 않으며, 오히려 다음과 같은 이유로 약간 증가할 수 있습니다:

1. **추가 설정 오버헤드**:
   - CIDR 블록 할당 및 관리에 추가 오버헤드가 발생할 수 있습니다.
   - 라우팅 테이블 업데이트에 시간이 소요될 수 있습니다.

2. **IP 주소 할당 복잡성**:
   - 개별 IP 주소 할당보다 CIDR 블록 할당 및 관리가 더 복잡할 수 있습니다.
   - 이로 인해 포드 시작 시 약간의 지연이 발생할 수 있습니다.

3. **초기 설정 시간**:
   - 새 ENI에 CIDR 블록을 할당하는 초기 설정 시간이 더 길 수 있습니다.
   - 그러나 한 번 설정되면 해당 ENI에서 여러 포드를 빠르게 시작할 수 있습니다.

#### 접두사 위임 활성화 방법:

```bash
# 접두사 위임 활성화
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# 접두사 위임 상태 확인
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

#### 접두사 위임 제한 사항:

1. **EC2 인스턴스 지원**:
   - Nitro 기반 인스턴스만 접두사 위임을 지원합니다.
   - 이전 세대 인스턴스에서는 사용할 수 없습니다.

2. **VPC CNI 버전 요구 사항**:
   - VPC CNI 버전 1.9.0 이상이 필요합니다.
   - 이전 버전에서는 이 기능을 사용할 수 없습니다.

3. **서브넷 크기 요구 사항**:
   - 충분한 IP 주소 공간이 있는 서브넷이 필요합니다.
   - 작은 서브넷에서는 IP 주소가 빠르게 소진될 수 있습니다.

4. **전환 시 고려 사항**:
   - 기존 클러스터에서 활성화하면 새 포드만 접두사 위임을 사용합니다.
   - 모든 포드에 적용하려면 기존 포드를 재시작해야 합니다.

접두사 위임은 노드당 최대 포드 수를 증가시키고 IP 주소 사용 효율성을 향상시키는 강력한 기능이지만, 포드 시작 시간을 단축하지는 않습니다. 따라서 "포드 시작 시간 단축"은 접두사 위임을 활성화할 때 발생하는 변화가 아닙니다.
</details>
2. Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 혼합하여 사용하는 주요 이점이 아닌 것은 무엇인가요?
   - A) 비용 최적화
   - B) 가용성 향상
   - C) 워크로드 특성에 맞는 인스턴스 유형 선택
   - D) 클러스터 관리 단순화
   
<details>
<summary>정답 보기</summary>

**정답: D) 클러스터 관리 단순화**

**설명:**
Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 혼합하여 사용하는 주요 이점이 아닌 것은 "클러스터 관리 단순화"입니다. 실제로는 다양한 인스턴스 유형을 혼합하여 사용하면 클러스터 관리가 더 복잡해질 수 있습니다. 인스턴스 유형을 혼합하여 사용하는 주요 이점은 비용 최적화, 가용성 향상, 워크로드 특성에 맞는 인스턴스 유형 선택입니다.

#### 인스턴스 유형 혼합 사용의 실제 이점:

1. **비용 최적화**:
   - 스팟 인스턴스와 온디맨드 인스턴스 혼합 사용
   - 다양한 인스턴스 패밀리의 가격 차이 활용
   - 워크로드 요구 사항에 맞는 최적의 가격 대비 성능 선택
   - 예시:
     ```yaml
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: mixed-spot-instances
         instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m5n.large"]
         spot: true
         minSize: 2
         maxSize: 10
     ```

2. **가용성 향상**:
   - 특정 인스턴스 유형의 용량 부족 시 대체 인스턴스 유형 사용
   - 스팟 인스턴스 중단 시 다른 유형으로 대체 가능
   - 여러 인스턴스 패밀리에 걸친 다양화로 리스크 분산
   - 예시:
     ```yaml
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: mixed-instance-types
         instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
         minSize: 3
         maxSize: 10
         spotAllocationStrategy: capacity-optimized
     ```

3. **워크로드 특성에 맞는 인스턴스 유형 선택**:
   - 다양한 워크로드 요구 사항에 맞는 인스턴스 유형 제공
   - 컴퓨팅 집약적 워크로드를 위한 C 시리즈
   - 메모리 집약적 워크로드를 위한 R 시리즈
   - 균형 잡힌 워크로드를 위한 M 시리즈
   - GPU 워크로드를 위한 G 또는 P 시리즈
   - 예시:
     ```yaml
     # 컴퓨팅 최적화 노드 그룹
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: compute-optimized
         instanceTypes: ["c5.2xlarge"]
         minSize: 2
         maxSize: 10
         labels:
           workload-type: compute
         taints:
           - key: workload-type
             value: compute
             effect: NoSchedule
     
       # 메모리 최적화 노드 그룹
       - name: memory-optimized
         instanceTypes: ["r5.2xlarge"]
         minSize: 2
         maxSize: 10
         labels:
           workload-type: memory
         taints:
           - key: workload-type
             value: memory
             effect: NoSchedule
     ```

#### 인스턴스 유형 혼합 사용의 단점:

1. **클러스터 관리 복잡성 증가**:
   - 다양한 인스턴스 유형에 대한 모니터링 및 관리 필요
   - 성능 특성 차이로 인한 문제 해결 복잡성
   - 다양한 인스턴스 유형에 맞는 리소스 요청 및 제한 조정 필요

2. **워크로드 예측 가능성 감소**:
   - 인스턴스 유형에 따라 성능 특성이 다를 수 있음
   - 특히 스팟 인스턴스 사용 시 워크로드 성능 변동 가능성

3. **리소스 할당 복잡성**:
   - 다양한 인스턴스 유형에 맞는 포드 리소스 요청 및 제한 설정 어려움
   - 노드 선택기 및 테인트를 사용한 복잡한 스케줄링 규칙 필요

4. **테스트 및 검증 부담**:
   - 다양한 인스턴스 유형에서 애플리케이션 테스트 필요
   - 성능 및 호환성 문제 발견 가능성 증가

#### 인스턴스 유형 혼합 사용 전략:

1. **워크로드 기반 노드 그룹 분리**:
   ```yaml
   # 웹 서버용 노드 그룹
   - name: web-servers
     instanceTypes: ["c5.large", "c5a.large"]
     labels:
       role: web
   
   # 데이터베이스용 노드 그룹
   - name: databases
     instanceTypes: ["r5.xlarge", "r5a.xlarge"]
     labels:
       role: database
   ```

2. **비용 최적화 전략**:
   ```yaml
   # 기본 온디맨드 노드 그룹
   - name: on-demand-base
     instanceTypes: ["m5.large"]
     minSize: 2
     maxSize: 5
     spot: false
   
   # 스케일링을 위한 스팟 노드 그룹
   - name: spot-scaling
     instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
     minSize: 0
     maxSize: 20
     spot: true
   ```

3. **가용성 최적화 전략**:
   ```yaml
   # 여러 인스턴스 패밀리에 걸친 다양화
   - name: high-availability
     instanceTypes: ["m5.large", "m5a.large", "c5.large", "c5a.large", "r5.large", "r5a.large"]
     minSize: 3
     maxSize: 10
     spotAllocationStrategy: capacity-optimized
   ```

인스턴스 유형을 혼합하여 사용하면 비용 최적화, 가용성 향상, 워크로드 특성에 맞는 인스턴스 유형 선택과 같은 이점이 있지만, 클러스터 관리는 단순화되지 않고 오히려 더 복잡해질 수 있습니다. 따라서 "클러스터 관리 단순화"는 인스턴스 유형을 혼합하여 사용하는 주요 이점이 아닙니다.
</details>

3. Amazon EKS 클러스터에서 노드 그룹 업데이트 전략으로 가장 안전한 것은 무엇인가요?
   - A) 인플레이스 업데이트
   - B) 블루/그린 배포
   - C) 카나리아 배포
   - D) 롤링 업데이트
   
<details>
<summary>정답 보기</summary>

**정답: B) 블루/그린 배포**

**설명:**
Amazon EKS 클러스터에서 노드 그룹 업데이트 전략으로 가장 안전한 것은 블루/그린 배포입니다. 블루/그린 배포는 새로운 노드 그룹(그린)을 생성하고 워크로드를 마이그레이션한 후, 기존 노드 그룹(블루)을 제거하는 방식으로, 업데이트 중 문제가 발생하면 즉시 이전 환경으로 롤백할 수 있어 가장 안전한 접근 방식입니다.

#### 노드 그룹 업데이트 전략 비교:

1. **블루/그린 배포**:
   - **작동 방식**: 새 노드 그룹 생성 → 워크로드 마이그레이션 → 기존 노드 그룹 제거
   - **장점**:
     - 즉각적인 롤백 가능
     - 업데이트 중 워크로드 중단 최소화
     - 업데이트 전후 환경 비교 가능
     - 테스트 후 전환 가능
   - **단점**:
     - 일시적으로 두 배의 리소스 필요
     - 구현 복잡성
     - 비용 증가
   - **구현 예시**:
     ```bash
     # 1. 새 노드 그룹 생성
     eksctl create nodegroup \
       --cluster my-cluster \
       --name my-nodegroup-v2 \
       --node-type m5.large \
       --nodes 3 \
       --node-ami-family AmazonLinux2 \
       --node-labels "version=v2,color=green"
     
     # 2. 워크로드 마이그레이션 (노드 선택기 업데이트)
     kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"color":"green"}}}}}'
     
     # 3. 모든 워크로드가 새 노드로 이동했는지 확인
     kubectl get pods -o wide
     
     # 4. 기존 노드 그룹 제거
     eksctl delete nodegroup --cluster my-cluster --name my-nodegroup-v1
     ```

2. **롤링 업데이트**:
   - **작동 방식**: 노드를 하나씩 교체 (코드네이션 → 드레이닝 → 종료 → 새 노드 추가)
   - **장점**:
     - 추가 리소스 필요 없음
     - EKS 관리형 노드 그룹의 기본 전략
     - 구현 간단
   - **단점**:
     - 롤백이 어려움
     - 업데이트 중 문제 발생 시 전체 클러스터에 영향
     - 업데이트 시간이 길어질 수 있음
   - **구현 예시**:
     ```bash
     # 관리형 노드 그룹 업데이트
     aws eks update-nodegroup-version \
       --cluster-name my-cluster \
       --nodegroup-name my-nodegroup
     
     # 업데이트 구성 수정
     aws eks update-nodegroup-config \
       --cluster-name my-cluster \
       --nodegroup-name my-nodegroup \
       --update-config '{"maxUnavailable": 1}'
     ```

3. **카나리아 배포**:
   - **작동 방식**: 소규모 새 노드 그룹 생성 → 일부 워크로드 마이그레이션 → 검증 → 완전 마이그레이션
   - **장점**:
     - 위험 최소화
     - 점진적 검증 가능
     - 문제 발생 시 영향 범위 제한
   - **단점**:
     - 구현 복잡성
     - 추가 리소스 필요
     - 완전한 마이그레이션까지 시간 소요
   - **구현 예시**:
     ```bash
     # 1. 소규모 카나리아 노드 그룹 생성
     eksctl create nodegroup \
       --cluster my-cluster \
       --name canary-nodegroup \
       --node-type m5.large \
       --nodes 1 \
       --node-labels "deployment=canary"
     
     # 2. 일부 워크로드 마이그레이션
     kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"deployment":"canary"}}}}}'
     
     # 3. 검증 후 완전 마이그레이션 진행
     ```

4. **인플레이스 업데이트**:
   - **작동 방식**: 기존 노드에서 직접 업데이트 수행
   - **장점**:
     - 추가 리소스 필요 없음
     - 간단한 변경에 적합
   - **단점**:
     - 위험성 높음
     - 롤백 어려움
     - 업데이트 실패 시 노드 손상 가능성
     - EKS에서는 권장되지 않음
   - **구현 예시**:
     ```bash
     # 노드에 SSH 접속하여 직접 업데이트 (권장되지 않음)
     ssh ec2-user@node-ip
     sudo yum update -y
     ```

#### 블루/그린 배포가 가장 안전한 이유:

1. **완전한 격리**:
   - 새 환경이 기존 환경과 완전히 분리되어 있어 영향 최소화
   - 업데이트 중 문제가 발생해도 기존 환경은 영향 받지 않음

2. **즉각적인 롤백**:
   - 문제 발생 시 트래픽을 기존 환경으로 즉시 되돌릴 수 있음
   - 다운타임 없이 롤백 가능

3. **검증 기회**:
   - 새 환경을 프로덕션 트래픽으로 전환하기 전에 철저히 테스트 가능
   - 실제 환경과 동일한 조건에서 검증 가능

4. **점진적 전환**:
   - 트래픽을 점진적으로 새 환경으로 전환할 수 있음
   - 문제 발생 시 영향 범위 제한

#### 블루/그린 배포 모범 사례:

1. **자동화**:
   - 배포 프로세스 자동화로 인적 오류 최소화
   - CI/CD 파이프라인 통합

2. **모니터링 강화**:
   - 새 환경의 성능 및 오류 지표 모니터링
   - 기존 환경과 비교 분석

3. **점진적 전환**:
   - 트래픽을 점진적으로 새 환경으로 전환
   - 문제 발생 시 즉시 롤백

4. **리소스 최적화**:
   - 전환 완료 후 불필요한 리소스 신속히 정리
   - 비용 최적화

블루/그린 배포는 추가 리소스와 구현 복잡성이라는 단점이 있지만, 안전성 측면에서는 가장 우수한 접근 방식입니다. 특히 중요한 프로덕션 환경이나 업데이트 실패 시 비즈니스 영향이 큰 경우에 권장됩니다.
</details>
4. Amazon EKS 클러스터에서 노드 그룹의 Auto Scaling을 최적화하기 위한 방법이 아닌 것은 무엇인가요?
   - A) Cluster Autoscaler의 스캔 간격 조정
   - B) 포드 우선순위 및 선점 구성
   - C) 노드 그룹별 Auto Scaling 그룹 태그 지정
   - D) 모든 노드에 동일한 인스턴스 유형 사용
   
<details>
<summary>정답 보기</summary>

**정답: D) 모든 노드에 동일한 인스턴스 유형 사용**

**설명:**
Amazon EKS 클러스터에서 노드 그룹의 Auto Scaling을 최적화하기 위한 방법이 아닌 것은 "모든 노드에 동일한 인스턴스 유형 사용"입니다. 실제로는 다양한 인스턴스 유형을 혼합하여 사용하는 것이 비용 최적화와 가용성 측면에서 더 효과적인 Auto Scaling 전략입니다. 특히 스팟 인스턴스를 사용할 때는 다양한 인스턴스 유형을 지정하여 용량 가용성을 높이고 중단 위험을 줄이는 것이 권장됩니다.

#### 노드 그룹 Auto Scaling 최적화를 위한 실제 방법:

1. **Cluster Autoscaler의 스캔 간격 조정**:
   - Cluster Autoscaler는 정기적으로 클러스터를 스캔하여 확장 또는 축소가 필요한지 확인합니다.
   - 스캔 간격을 조정하여 반응 시간과 리소스 사용량 간의 균형을 맞출 수 있습니다.
   - 예시:
     ```yaml
     # Cluster Autoscaler 배포 구성
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: cluster-autoscaler
       namespace: kube-system
     spec:
       template:
         spec:
           containers:
           - name: cluster-autoscaler
             image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
             command:
             - ./cluster-autoscaler
             - --v=4
             - --stderrthreshold=info
             - --cloud-provider=aws
             - --scan-interval=30s  # 스캔 간격 조정 (기본값: 10초)
             - --max-node-provision-time=15m
             - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
     ```

2. **포드 우선순위 및 선점 구성**:
   - 포드 우선순위 및 선점(PriorityClass)을 사용하여 중요한 워크로드가 먼저 스케줄링되도록 합니다.
   - 리소스가 부족할 때 우선순위가 낮은 포드를 선점하여 우선순위가 높은 포드를 위한 공간을 확보합니다.
   - 예시:
     ```yaml
     # 우선순위 클래스 정의
     apiVersion: scheduling.k8s.io/v1
     kind: PriorityClass
     metadata:
       name: high-priority
     value: 1000000
     globalDefault: false
     description: "High priority pods"
     ---
     # 우선순위가 높은 포드
     apiVersion: v1
     kind: Pod
     metadata:
       name: high-priority-pod
     spec:
       priorityClassName: high-priority
       containers:
       - name: nginx
         image: nginx
     ```

3. **노드 그룹별 Auto Scaling 그룹 태그 지정**:
   - Cluster Autoscaler가 특정 노드 그룹을 식별하고 관리할 수 있도록 태그를 지정합니다.
   - 노드 그룹별로 다른 Auto Scaling 동작을 구성할 수 있습니다.
   - 예시:
     ```bash
     # Auto Scaling 그룹 태그 지정
     aws autoscaling create-or-update-tags \
       --tags ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true \
              ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/my-cluster,Value=owned,PropagateAtLaunch=true
     
     # 노드 그룹별 Auto Scaling 설정
     aws autoscaling update-auto-scaling-group \
       --auto-scaling-group-name my-asg \
       --min-size 2 \
       --max-size 10 \
       --desired-capacity 2
     ```

#### 다양한 인스턴스 유형 혼합 사용의 이점:

1. **비용 최적화**:
   - 다양한 인스턴스 유형의 가격 차이 활용
   - 스팟 인스턴스 사용 시 가용성 향상
   - 예시:
     ```yaml
     # 다양한 인스턴스 유형을 사용하는 노드 그룹
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: mixed-instances
         instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
         minSize: 2
         maxSize: 10
         spot: true
     ```

2. **가용성 향상**:
   - 특정 인스턴스 유형의 용량 부족 시 대체 인스턴스 유형 사용
   - 스팟 인스턴스 중단 시 다른 유형으로 대체 가능
   - 예시:
     ```yaml
     # 용량 최적화 스팟 할당 전략
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: spot-nodes
         instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
         minSize: 2
         maxSize: 10
         spot: true
         spotAllocationStrategy: capacity-optimized
     ```

3. **워크로드 특성에 맞는 인스턴스 유형 선택**:
   - 다양한 워크로드 요구 사항에 맞는 인스턴스 유형 제공
   - 노드 선택기와 테인트를 사용하여 워크로드 배치 제어
   - 예시:
     ```yaml
     # 워크로드 특성별 노드 그룹
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: general-purpose
         instanceTypes: ["m5.large"]
         minSize: 2
         maxSize: 10
       
       - name: compute-intensive
         instanceTypes: ["c5.large"]
         minSize: 0
         maxSize: 10
         labels:
           workload-type: compute
     ```

#### Auto Scaling 최적화를 위한 추가 전략:

1. **오버프로비저닝**:
   - 일정량의 여유 리소스를 유지하여 급격한 확장 요청에 대비
   - 예시:
     ```yaml
     # 오버프로비저닝 포드
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: overprovisioning
       namespace: kube-system
     spec:
       replicas: 1
       selector:
         matchLabels:
           app: overprovisioning
       template:
         metadata:
           labels:
             app: overprovisioning
         spec:
           priorityClassName: overprovisioning
           containers:
           - name: reserve-resources
             image: k8s.gcr.io/pause:3.2
             resources:
               requests:
                 cpu: 1000m
                 memory: 1000Mi
     ```

2. **스케일링 정책 최적화**:
   - 대상 추적 조정 정책 사용
   - 단계 조정 정책 사용
   - 예측 조정 활성화
   - 예시:
     ```bash
     # 대상 추적 조정 정책 설정
     aws autoscaling put-scaling-policy \
       --auto-scaling-group-name my-asg \
       --policy-name cpu70-target-tracking-scaling-policy \
       --policy-type TargetTrackingScaling \
       --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":70.0,"DisableScaleIn":false}'
     ```

3. **Karpenter 사용**:
   - Cluster Autoscaler 대신 Karpenter 사용 고려
   - 더 빠른 노드 프로비저닝 및 더 유연한 인스턴스 유형 선택
   - 예시:
     ```yaml
     # Karpenter Provisioner
     apiVersion: karpenter.sh/v1alpha5
     kind: Provisioner
     metadata:
       name: default
     spec:
       requirements:
         - key: karpenter.sh/capacity-type
           operator: In
           values: ["spot", "on-demand"]
         - key: node.kubernetes.io/instance-type
           operator: In
           values: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
       limits:
         resources:
           cpu: 1000
           memory: 1000Gi
     ```

모든 노드에 동일한 인스턴스 유형을 사용하는 것은 Auto Scaling 최적화 전략이 아니며, 오히려 다양한 인스턴스 유형을 혼합하여 사용하는 것이 비용 최적화와 가용성 측면에서 더 효과적입니다. 따라서 "모든 노드에 동일한 인스턴스 유형 사용"은 노드 그룹의 Auto Scaling을 최적화하기 위한 방법이 아닙니다.
</details>

5. Amazon EKS 클러스터에서 노드 그룹 생성 시 고려해야 할 보안 모범 사례가 아닌 것은 무엇인가요?
   - A) IMDSv2 필수 설정
   - B) 최소 권한 IAM 정책 적용
   - C) 모든 노드에 퍼블릭 IP 주소 할당
   - D) 보안 그룹 규칙 제한
   
<details>
<summary>정답 보기</summary>

**정답: C) 모든 노드에 퍼블릭 IP 주소 할당**

**설명:**
Amazon EKS 클러스터에서 노드 그룹 생성 시 고려해야 할 보안 모범 사례가 아닌 것은 "모든 노드에 퍼블릭 IP 주소 할당"입니다. 보안 모범 사례는 오히려 그 반대로, 노드를 프라이빗 서브넷에 배치하고 퍼블릭 IP 주소를 할당하지 않는 것입니다. 이렇게 하면 노드가 인터넷에서 직접 접근할 수 없게 되어 공격 표면이 줄어듭니다.

#### EKS 노드 그룹 생성 시 실제 보안 모범 사례:

1. **IMDSv2 필수 설정**:
   - 인스턴스 메타데이터 서비스 버전 2(IMDSv2)를 필수로 설정하여 SSRF(Server-Side Request Forgery) 공격으로부터 보호
   - IMDSv2는 세션 기반 요청을 사용하여 보안 강화
   - 예시:
     ```yaml
     # eksctl 구성 파일
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: secure-nodes
         instanceType: m5.large
         minSize: 2
         maxSize: 5
         disableIMDSv1: true  # IMDSv1 비활성화
         metadataOptions:
           httpTokens: required  # IMDSv2 필수 설정
           httpPutResponseHopLimit: 1
     ```

2. **최소 권한 IAM 정책 적용**:
   - 노드 IAM 역할에 필요한 최소한의 권한만 부여
   - 기본 관리형 정책 외에 추가 권한이 필요한 경우 세분화된 정책 생성
   - 예시:
     ```yaml
     # 노드 IAM 역할에 대한 최소 권한 정책
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: secure-nodes
         instanceType: m5.large
         minSize: 2
         maxSize: 5
         iam:
           attachPolicyARNs:
             - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
             - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
             - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
           withAddonPolicies:
             imageBuilder: false
             autoScaler: false
             externalDNS: false
             certManager: false
             appMesh: false
             ebs: true
             fsx: false
             efs: false
             albIngress: false
             xRay: false
             cloudWatch: true
     ```

3. **보안 그룹 규칙 제한**:
   - 노드 보안 그룹의 인바운드 및 아웃바운드 규칙 제한
   - 필요한 최소한의 포트만 개방
   - 예시:
     ```bash
     # 보안 그룹 생성
     aws ec2 create-security-group \
       --group-name eks-node-sg \
       --description "Security group for EKS nodes" \
       --vpc-id vpc-12345
     
     # 클러스터 통신에 필요한 규칙만 추가
     aws ec2 authorize-security-group-ingress \
       --group-id sg-12345 \
       --protocol tcp \
       --port 443 \
       --source-group sg-cluster
     
     aws ec2 authorize-security-group-ingress \
       --group-id sg-12345 \
       --protocol tcp \
       --port 10250 \
       --source-group sg-cluster
     ```

#### 노드에 퍼블릭 IP 주소를 할당하지 않는 이유:

1. **공격 표면 감소**:
   - 퍼블릭 IP가 없으면 인터넷에서 노드에 직접 접근할 수 없음
   - SSH 접근 등의 관리 작업은 배스천 호스트나 AWS Systems Manager를 통해 수행

2. **보안 아키텍처 개선**:
   - 프라이빗 서브넷에 노드 배치
   - NAT 게이트웨이를 통한 아웃바운드 통신만 허용
   - 인바운드 트래픽은 로드 밸런서를 통해서만 허용

3. **규정 준수**:
   - 많은 보안 표준 및 규정은 직접적인 인터넷 노출 최소화 요구
   - PCI DSS, HIPAA 등의 규정 준수에 도움

#### 프라이빗 서브넷에 노드 배치 예시:

```yaml
# eksctl 구성 파일
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  subnets:
    private:
      us-west-2a: { id: subnet-private-a }
      us-west-2b: { id: subnet-private-b }
    public:
      us-west-2a: { id: subnet-public-a }
      us-west-2b: { id: subnet-public-b }
managedNodeGroups:
  - name: secure-nodes
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    privateNetworking: true  # 프라이빗 서브넷에 노드 배치
```

#### 추가 EKS 보안 모범 사례:

1. **암호화 활성화**:
   - EBS 볼륨 암호화
   - Secrets 암호화
   - 예시:
     ```yaml
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     secretsEncryption:
       keyARN: arn:aws:kms:us-west-2:123456789012:key/key-id
     nodeGroups:
       - name: secure-nodes
         volumeEncrypted: true
         volumeKmsKeyID: arn:aws:kms:us-west-2:123456789012:key/key-id
     ```

2. **컨테이너 보안**:
   - 권한 있는 컨테이너 비활성화
   - 읽기 전용 루트 파일 시스템 사용
   - 예시:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: secure-pod
     spec:
       containers:
       - name: secure-container
         image: nginx
         securityContext:
           privileged: false
           readOnlyRootFilesystem: true
           allowPrivilegeEscalation: false
     ```

3. **네트워크 정책 구현**:
   - 포드 간 통신 제한
   - 기본 거부 정책 적용
   - 예시:
     ```yaml
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
     ```

4. **로깅 및 모니터링**:
   - CloudWatch Logs 활성화
   - GuardDuty EKS Protection 활성화
   - 예시:
     ```bash
     # CloudWatch Logs 활성화
     aws eks update-cluster-config \
       --name my-cluster \
       --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
     ```

모든 노드에 퍼블릭 IP 주소를 할당하는 것은 보안 모범 사례가 아니며, 오히려 보안 위험을 증가시킵니다. 따라서 "모든 노드에 퍼블릭 IP 주소 할당"은 Amazon EKS 클러스터에서 노드 그룹 생성 시 고려해야 할 보안 모범 사례가 아닙니다.
</details>
