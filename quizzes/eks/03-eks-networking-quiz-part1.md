# Amazon EKS 네트워킹 퀴즈 (Part 1)

이 퀴즈는 Amazon EKS의 네트워킹 기본 개념, VPC CNI, 네트워크 정책 및 서비스 디스커버리에 대한 이해를 테스트합니다. EKS 클러스터의 네트워킹 아키텍처와 구성 요소에 중점을 둡니다.

## 객관식 문제

### 1. Amazon EKS에서 기본적으로 사용하는 CNI(Container Network Interface) 플러그인은 무엇인가요?

A. Calico  
B. Flannel  
C. Amazon VPC CNI  
D. Weave Net  

<details>
<summary>정답 및 설명</summary>

**정답: C. Amazon VPC CNI**

**설명:**
Amazon EKS는 기본적으로 Amazon VPC CNI 플러그인을 사용합니다. 이 플러그인은 Kubernetes 파드에 VPC IP 주소를 할당하고, AWS VPC 네트워킹의 기본 기능을 활용하여 파드 간 통신을 가능하게 합니다.

**주요 특징:**

1. **네이티브 VPC 네트워킹**: 각 파드는 VPC 내에서 고유한 IP 주소를 받습니다. 이는 파드가 VPC 내의 다른 서비스와 직접 통신할 수 있게 해줍니다.

2. **보조 IP 주소 할당**: 각 노드의 탄력적 네트워크 인터페이스(ENI)에 보조 IP 주소를 할당하여 파드에 제공합니다.

3. **보안 그룹 통합**: 파드 수준에서 AWS 보안 그룹을 적용할 수 있어 세밀한 네트워크 보안 제어가 가능합니다.

4. **성능**: 오버레이 네트워크를 사용하지 않아 네트워크 성능이 향상됩니다.

5. **AWS 서비스 통합**: AWS Load Balancer Controller, AWS App Mesh 등 다른 AWS 서비스와 원활하게 통합됩니다.

**구성 예시:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-network-policy: "true"
  enable-pod-eni: "true"
  warm-ip-target: "5"
  minimum-ip-target: "10"
```

Amazon VPC CNI는 오픈 소스이며 GitHub에서 관리됩니다. 필요에 따라 Calico, Cilium 등 다른 CNI 플러그인으로 대체할 수 있지만, Amazon VPC CNI가 EKS의 기본 옵션이며 AWS에서 공식적으로 지원합니다.
</details>

### 2. Amazon EKS에서 VPC CNI가 파드에 IP 주소를 할당하는 방식은 무엇인가요?

A. 각 파드에 별도의 탄력적 네트워크 인터페이스(ENI)를 할당한다  
B. 노드의 탄력적 네트워크 인터페이스(ENI)에 보조 IP 주소를 할당하여 파드에 제공한다  
C. 오버레이 네트워크를 사용하여 가상 IP 주소를 할당한다  
D. 각 파드에 별도의 VPC 서브넷을 할당한다  

<details>
<summary>정답 및 설명</summary>

**정답: B. 노드의 탄력적 네트워크 인터페이스(ENI)에 보조 IP 주소를 할당하여 파드에 제공한다**

**설명:**
Amazon VPC CNI는 노드의 탄력적 네트워크 인터페이스(ENI)에 보조 IP 주소를 할당하고, 이 IP 주소를 파드에 제공하는 방식으로 작동합니다. 이 방식은 "IP-per-Pod" 모델이라고도 불립니다.

**작동 방식:**

1. **ENI 할당**: 각 EC2 인스턴스(노드)는 하나 이상의 ENI를 가질 수 있습니다. 인스턴스 유형에 따라 ENI당 할당할 수 있는 IP 주소 수가 결정됩니다.

2. **IP 주소 풀 관리**: VPC CNI의 `aws-node` DaemonSet는 각 노드에서 실행되며, 사용 가능한 IP 주소 풀을 관리합니다.

3. **IP 주소 할당**: 파드가 생성되면, CNI는 IP 주소 풀에서 IP 주소를 할당하고 파드의 네트워크 네임스페이스에 연결합니다.

4. **IP 주소 회수**: 파드가 종료되면, CNI는 IP 주소를 회수하여 풀로 반환합니다.

**예시 구성:**
```bash
# 노드당 최대 파드 수 계산
최대 파드 수 = (ENI 수 × (ENI당 IP 주소 수 - 1)) + 2

# m5.large 인스턴스의 경우
# ENI 수: 3, ENI당 IP 주소 수: 10
최대 파드 수 = (3 × (10 - 1)) + 2 = 29
```

**주요 고려 사항:**

1. **IP 주소 제한**: 인스턴스 유형에 따라 노드당 실행할 수 있는 최대 파드 수가 제한됩니다.

2. **워밍(Warm) IP**: VPC CNI는 `WARM_IP_TARGET` 설정을 통해 미리 일정 수의 IP 주소를 할당하여 파드 시작 시간을 단축할 수 있습니다.

3. **프리픽스 위임(Prefix Delegation)**: 최신 버전의 VPC CNI는 /28 CIDR 블록(16개 IP)을 각 ENI에 할당하는 프리픽스 위임 기능을 지원하여 IP 주소 밀도를 높일 수 있습니다.

4. **보안 그룹**: `ENABLE_POD_ENI` 설정을 활성화하면 특정 파드에 대해 별도의 보안 그룹을 구성할 수 있습니다(Security Groups for Pods 기능).

다른 옵션들의 문제점:
- **A**: 일반적으로 각 파드에 별도의 ENI를 할당하지 않습니다. 이는 EC2 인스턴스당 ENI 제한으로 인해 비효율적입니다.
- **C**: VPC CNI는 오버레이 네트워크를 사용하지 않습니다. 이는 Flannel이나 Weave Net과 같은 다른 CNI 플러그인의 특징입니다.
- **D**: 각 파드에 별도의 VPC 서브넷을 할당하는 것은 AWS VPC 아키텍처에서 불가능합니다.
</details>

### 3. Amazon EKS에서 파드 간 통신이 VPC 외부로 나가지 않고 VPC 내에서 직접 이루어지는 이유는 무엇인가요?

A. 모든 파드가 동일한 서브넷에 위치하기 때문에  
B. 파드가 노드의 네트워크 네임스페이스를 공유하기 때문에  
C. 파드가 VPC IP 주소를 직접 할당받기 때문에  
D. 파드 간 통신이 항상 서비스 메시를 통해 이루어지기 때문에  

<details>
<summary>정답 및 설명</summary>

**정답: C. 파드가 VPC IP 주소를 직접 할당받기 때문에**

**설명:**
Amazon EKS에서 파드 간 통신이 VPC 외부로 나가지 않고 VPC 내에서 직접 이루어지는 주된 이유는 Amazon VPC CNI 플러그인이 각 파드에 VPC IP 주소를 직접 할당하기 때문입니다.

**주요 메커니즘:**

1. **VPC IP 주소 할당**: 각 파드는 VPC 서브넷에서 고유한 IP 주소를 할당받습니다. 이 IP 주소는 노드의 ENI에 연결된 보조 IP 주소입니다.

2. **직접 라우팅**: 파드가 VPC IP 주소를 가지므로, VPC 내의 다른 리소스(다른 파드, EC2 인스턴스, RDS 데이터베이스 등)와 직접 통신할 수 있습니다.

3. **VPC 라우팅 테이블**: 파드 간 통신은 VPC 라우팅 테이블을 따르며, 동일한 VPC 내에서는 외부로 나가지 않고 직접 라우팅됩니다.

**장점:**

1. **네트워크 성능**: 오버레이 네트워크나 NAT를 사용하지 않아 지연 시간이 감소하고 처리량이 향상됩니다.

2. **보안**: VPC 보안 그룹, 네트워크 ACL 등 기존 AWS 네트워크 보안 메커니즘을 활용할 수 있습니다.

3. **가시성**: VPC 흐름 로그를 통해 파드 간 트래픽을 모니터링하고 분석할 수 있습니다.

4. **AWS 서비스 통합**: 파드가 VPC IP 주소를 가지므로 VPC 엔드포인트, PrivateLink 등의 AWS 서비스와 원활하게 통합됩니다.

**예시 시나리오:**

파드 A(IP: 10.0.1.23)가 파드 B(IP: 10.0.2.45)와 통신하는 경우:
1. 파드 A는 파드 B의 IP 주소(10.0.2.45)로 직접 패킷을 전송합니다.
2. 패킷은 VPC 라우팅 테이블에 따라 라우팅됩니다.
3. 패킷이 VPC 내에서 직접 파드 B에 도달합니다.
4. 이 과정에서 패킷은 VPC 외부로 나가지 않습니다.

다른 옵션들의 문제점:
- **A**: 파드는 여러 서브넷에 분산될 수 있으며, 서로 다른 서브넷에 있는 파드들도 VPC 내에서 직접 통신할 수 있습니다.
- **B**: 파드는 노드의 네트워크 네임스페이스를 공유하지 않습니다. 각 파드는 자체 네트워크 네임스페이스를 가집니다.
- **D**: 파드 간 통신이 항상 서비스 메시를 통해 이루어지는 것은 아닙니다. 서비스 메시는 선택적으로 사용되는 추가 계층입니다.
</details>

### 4. Amazon EKS에서 파드에 대한 인바운드 및 아웃바운드 트래픽을 제어하는 가장 적합한 Kubernetes 리소스는 무엇인가요?

A. Service  
B. Ingress  
C. NetworkPolicy  
D. SecurityContext  

<details>
<summary>정답 및 설명</summary>

**정답: C. NetworkPolicy**

**설명:**
Amazon EKS에서 파드에 대한 인바운드 및 아웃바운드 트래픽을 제어하는 가장 적합한 Kubernetes 리소스는 NetworkPolicy입니다. NetworkPolicy는 Kubernetes의 네트워크 보안 메커니즘으로, 파드 간 통신을 세밀하게 제어할 수 있습니다.

**NetworkPolicy의 주요 특징:**

1. **선택적 적용**: 레이블 선택기를 사용하여 특정 파드에 정책을 적용할 수 있습니다.

2. **인바운드 및 아웃바운드 규칙**: 인바운드(ingress) 및 아웃바운드(egress) 트래픽을 모두 제어할 수 있습니다.

3. **다양한 선택기**: 네임스페이스, 레이블, IP CIDR 블록, 포트 등을 기준으로 트래픽을 필터링할 수 있습니다.

4. **기본 거부 정책**: 명시적으로 허용되지 않은 트래픽은 기본적으로 거부됩니다.

**NetworkPolicy 예시:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          purpose: frontend
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          purpose: database
    ports:
    - protocol: TCP
      port: 5432
```

**EKS에서의 NetworkPolicy 구현:**

Amazon EKS에서 NetworkPolicy를 사용하려면 네트워크 정책을 지원하는 CNI 플러그인이 필요합니다. 기본 Amazon VPC CNI는 네트워크 정책을 직접 지원하지 않으므로, 다음과 같은 추가 구성이 필요합니다:

1. **Calico 설치**: Calico는 EKS에서 NetworkPolicy를 구현하는 가장 일반적인 방법입니다.
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
   ```

2. **Amazon VPC CNI의 네트워크 정책 활성화**: 최신 버전의 Amazon VPC CNI는 네트워크 정책 지원을 제공합니다.
   ```bash
   kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true
   ```

다른 옵션들의 문제점:
- **A. Service**: Service는 파드에 대한 네트워크 액세스를 제공하지만, 트래픽 제어나 필터링 기능은 없습니다.
- **B. Ingress**: Ingress는 HTTP/HTTPS 트래픽을 클러스터 내 서비스로 라우팅하는 데 사용되지만, 일반적인 네트워크 정책을 정의하지는 않습니다.
- **D. SecurityContext**: SecurityContext는 파드 또는 컨테이너 수준의 보안 설정을 정의하지만, 네트워크 트래픽 제어와는 관련이 없습니다.
</details>

### 5. Amazon EKS에서 클러스터 내 서비스 디스커버리를 위해 사용되는 DNS 서비스는 무엇인가요?

A. Amazon Route 53  
B. CoreDNS  
C. kube-dns  
D. AWS Cloud Map  

<details>
<summary>정답 및 설명</summary>

**정답: B. CoreDNS**

**설명:**
Amazon EKS에서 클러스터 내 서비스 디스커버리를 위해 기본적으로 사용되는 DNS 서비스는 CoreDNS입니다. CoreDNS는 Kubernetes 클러스터 내에서 DNS 기반 서비스 디스커버리를 제공하는 유연하고 확장 가능한 DNS 서버입니다.

**CoreDNS의 주요 특징:**

1. **Kubernetes 통합**: CoreDNS는 Kubernetes API와 통합되어 서비스 및 파드의 DNS 레코드를 자동으로 생성합니다.

2. **플러그인 아키텍처**: CoreDNS는 다양한 플러그인을 통해 기능을 확장할 수 있습니다.

3. **고가용성**: EKS에서 CoreDNS는 일반적으로 여러 복제본으로 배포되어 고가용성을 보장합니다.

4. **구성 가능성**: Corefile을 통해 다양한 DNS 설정을 구성할 수 있습니다.

**EKS에서의 CoreDNS 배포:**

EKS 클러스터를 생성하면 CoreDNS가 자동으로 배포됩니다. CoreDNS는 `kube-system` 네임스페이스에서 Deployment로 실행됩니다:

```bash
kubectl get deployment coredns -n kube-system
```

**CoreDNS 구성 예시:**

CoreDNS의 구성은 ConfigMap에 저장됩니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

**서비스 디스커버리 작동 방식:**

1. **서비스 생성**: Kubernetes 서비스가 생성되면, CoreDNS는 자동으로 DNS 레코드를 생성합니다.

2. **DNS 이름 형식**: 
   - 서비스: `<service-name>.<namespace>.svc.cluster.local`
   - 파드: `<pod-ip>.<namespace>.pod.cluster.local`

3. **DNS 조회**: 클러스터 내 파드가 서비스 이름으로 DNS 조회를 수행하면, CoreDNS가 해당 서비스의 ClusterIP로 응답합니다.

**예시:**
```bash
# my-service라는 서비스가 default 네임스페이스에 있는 경우
nslookup my-service.default.svc.cluster.local

# 결과
Name:   my-service.default.svc.cluster.local
Address: 10.100.43.150  # 서비스의 ClusterIP
```

**CoreDNS 스케일링 및 최적화:**

EKS에서 CoreDNS는 클러스터 크기에 따라 자동으로 스케일링되지 않으므로, 대규모 클러스터에서는 수동으로 스케일링해야 할 수 있습니다:

```bash
kubectl scale deployment coredns --replicas=4 -n kube-system
```

또한, 캐시 설정을 조정하여 성능을 최적화할 수 있습니다:

```yaml
cache {
    success 10000
    denial 1000
    prefetch 10 10m 20%
}
```

다른 옵션들의 문제점:
- **A. Amazon Route 53**: Route 53은 AWS의 DNS 서비스이지만, EKS 클러스터 내부의 서비스 디스커버리에는 기본적으로 사용되지 않습니다.
- **C. kube-dns**: kube-dns는 이전 버전의 Kubernetes에서 사용되었지만, EKS에서는 CoreDNS로 대체되었습니다.
- **D. AWS Cloud Map**: Cloud Map은 AWS의 서비스 디스커버리 서비스이지만, EKS 클러스터 내부의 기본 DNS 서비스로 사용되지 않습니다.
</details>
## 단답형 문제

### 6. Amazon EKS 클러스터에서 노드당 최대 파드 수를 제한하는 주요 요소는 무엇이며, 이를 늘리기 위한 방법은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답:**
Amazon EKS 클러스터에서 노드당 최대 파드 수를 제한하는 주요 요소는 **EC2 인스턴스 유형별 ENI(탄력적 네트워크 인터페이스) 수와 ENI당 할당 가능한 IP 주소 수**입니다. 이를 늘리기 위한 주요 방법은 **프리픽스 위임(Prefix Delegation) 기능을 활성화**하는 것입니다.

**상세 설명:**

1. **노드당 최대 파드 수 계산 공식**:
   ```
   최대 파드 수 = (ENI 수 × (ENI당 IP 주소 수 - 1)) + 2
   ```
   - 각 ENI의 첫 번째 IP 주소는 노드 자체를 위해 예약됩니다.
   - 추가 2개는 kube-proxy와 aws-node 파드를 위한 것입니다.

2. **인스턴스 유형별 제한 예시**:
   - **t3.small**: (3 ENI × (4 IP - 1)) + 2 = 11 파드
   - **m5.large**: (3 ENI × (10 IP - 1)) + 2 = 29 파드
   - **c5.4xlarge**: (8 ENI × (30 IP - 1)) + 2 = 234 파드

3. **프리픽스 위임(Prefix Delegation)을 통한 확장**:
   프리픽스 위임은 각 ENI에 개별 IP 주소 대신 /28 CIDR 블록(16개 IP)을 할당하는 기능입니다.

   **활성화 방법**:
   ```bash
   # ConfigMap 수정
   kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
   
   # 선택적으로 프리픽스 할당 모드 설정
   kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1
   ```

   **프리픽스 위임 활성화 후 계산 공식**:
   ```
   최대 파드 수 = (ENI 수 × (ENI당 프리픽스 수 × 프리픽스당 IP 수 - 1)) + 2
   ```

   예: m5.large에서 프리픽스 위임 활성화 시
   - 프리픽스 위임 없이: 29 파드
   - 프리픽스 위임 활성화: (3 ENI × (1 프리픽스 × 16 IP - 1)) + 2 = 47 파드

4. **기타 최대 파드 수를 늘리는 방법**:
   - **더 큰 인스턴스 유형 사용**: 더 많은 ENI와 IP 주소를 지원하는 인스턴스 유형으로 변경
   - **사용자 지정 CNI 구성**: `--max-pods` 플래그를 사용하여 kubelet 구성 조정 (권장하지 않음)
   - **대체 CNI 플러그인 사용**: Calico, Cilium 등 오버레이 네트워크를 사용하는 CNI 플러그인으로 전환

5. **고려 사항**:
   - 프리픽스 위임은 EC2 Nitro 기반 인스턴스에서만 지원됩니다.
   - 프리픽스 위임을 활성화하면 보안 그룹을 파드에 직접 할당하는 기능(SecurityGroupsForPods)을 사용할 수 없습니다.
   - 노드당 파드 수가 많아지면 노드 리소스(CPU, 메모리) 경합이 발생할 수 있으므로 적절한 인스턴스 크기 선택이 중요합니다.

6. **모니터링 및 최적화**:
   ```bash
   # 현재 IP 주소 사용량 확인
   kubectl exec -n kube-system ds/aws-node -- curl -s http://localhost:61679/v1/enis | jq
   
   # 프리픽스 위임 상태 확인
   kubectl describe daemonset aws-node -n kube-system | grep PREFIX
   ```

프리픽스 위임을 활성화하면 노드당 최대 파드 수를 크게 늘릴 수 있지만, 클러스터의 요구 사항과 워크로드 특성에 따라 적절한 구성을 선택하는 것이 중요합니다.
</details>

### 7. Amazon EKS에서 파드에 특정 AWS 보안 그룹을 할당하는 기능의 이름은 무엇이며, 이를 구성하는 방법을 설명하세요.

<details>
<summary>정답 및 설명</summary>

**정답:**
Amazon EKS에서 파드에 특정 AWS 보안 그룹을 할당하는 기능의 이름은 **Security Groups for Pods** 또는 **Pod ENI(Elastic Network Interface)**입니다. 이 기능은 VPC CNI의 **ENABLE_POD_ENI** 옵션을 활성화하여 구성할 수 있습니다.

**상세 설명:**

1. **Security Groups for Pods 개요**:
   이 기능은 특정 파드에 대해 별도의 ENI(트렁크 ENI라고도 함)를 생성하고, 이 ENI에 보안 그룹을 연결하여 파드 수준에서 세밀한 네트워크 보안 제어를 가능하게 합니다.

2. **사전 요구 사항**:
   - Amazon VPC CNI 플러그인 버전 1.7.7 이상
   - Kubernetes 버전 1.17 이상
   - EC2 Nitro 기반 인스턴스
   - 프리픽스 위임 기능이 비활성화되어 있어야 함

3. **구성 단계**:

   a. **VPC CNI에서 Pod ENI 기능 활성화**:
   ```bash
   kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
   ```

   b. **SecurityGroupPolicy 리소스 생성**:
   ```yaml
   apiVersion: vpcresources.k8s.aws/v1beta1
   kind: SecurityGroupPolicy
   metadata:
     name: allow-db-access
     namespace: app
   spec:
     podSelector:
       matchLabels:
         role: db-client
     securityGroups:
       groupIds:
         - sg-0123456789abcdef0
   ```

   c. **서비스 계정에 IAM 권한 부여**:
   VPC CNI의 서비스 계정에 다음 권한이 필요합니다:
   - ec2:CreateNetworkInterface
   - ec2:DeleteNetworkInterface
   - ec2:DescribeNetworkInterfaces
   - ec2:DescribeSecurityGroups
   - ec2:ModifyNetworkInterfaceAttribute
   - ec2:CreateTags

4. **파드 구성 예시**:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: db-client
     namespace: app
     labels:
       role: db-client
   spec:
     containers:
     - name: app
       image: amazonlinux:2
       command: ['sleep', '3600']
   ```

5. **작동 방식**:
   - SecurityGroupPolicy와 일치하는 레이블을 가진 파드가 생성되면, VPC CNI는 해당 파드를 위한 브랜치 ENI를 생성합니다.
   - 이 브랜치 ENI에 지정된 보안 그룹이 연결됩니다.
   - 파드의 트래픽은 이 브랜치 ENI를 통해 라우팅되며, 연결된 보안 그룹 규칙이 적용됩니다.

6. **확인 방법**:
   ```bash
   # 파드의 ENI 정보 확인
   kubectl describe pod db-client -n app
   
   # SecurityGroupPolicy 확인
   kubectl get securitygrouppolicy -n app
   
   # VPC CNI 로그 확인
   kubectl logs -n kube-system -l k8s-app=aws-node
   ```

7. **제한 사항**:
   - 노드당 브랜치 ENI 수에 제한이 있습니다 (인스턴스 유형에 따라 다름).
   - 프리픽스 위임 기능과 함께 사용할 수 없습니다.
   - 파드가 생성된 후에는 보안 그룹을 변경할 수 없습니다.
   - 파드 시작 시간이 약간 증가할 수 있습니다.

8. **사용 사례**:
   - RDS, ElastiCache 등 보안 그룹으로 액세스를 제어하는 AWS 서비스에 접근하는 파드
   - 특정 파드에 대한 인바운드/아웃바운드 트래픽을 세밀하게 제어해야 하는 경우
   - 규제 요구 사항에 따라 네트워크 격리가 필요한 워크로드

Security Groups for Pods 기능은 EKS의 네트워킹 보안을 강화하는 강력한 도구이지만, 추가 ENI 사용으로 인한 리소스 오버헤드와 제한 사항을 고려하여 적절히 사용해야 합니다.
</details>

### 8. Amazon EKS에서 서비스 타입 LoadBalancer를 사용할 때, AWS Load Balancer Controller가 기본적으로 생성하는 로드 밸런서 유형은 무엇이며, 이를 변경하는 방법은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답:**
Amazon EKS에서 서비스 타입 LoadBalancer를 사용할 때, AWS Load Balancer Controller는 기본적으로 **Classic Load Balancer(CLB)**를 생성합니다. 이를 **Network Load Balancer(NLB)**로 변경하려면 서비스에 특정 **어노테이션(annotation)**을 추가해야 합니다.

**상세 설명:**

1. **기본 동작**:
   Kubernetes의 `LoadBalancer` 타입 서비스를 생성하면, AWS 클라우드 컨트롤러 매니저는 기본적으로 Classic Load Balancer를 프로비저닝합니다.

2. **Network Load Balancer로 변경하는 방법**:
   서비스에 다음 어노테이션을 추가합니다:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-type: nlb
   ```

3. **완전한 서비스 예시 (NLB 사용)**:
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: my-service
     annotations:
       service.beta.kubernetes.io/aws-load-balancer-type: nlb
   spec:
     type: LoadBalancer
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: my-app
   ```

4. **내부 로드 밸런서 구성**:
   기본적으로 생성되는 로드 밸런서는 인터넷 연결이 가능합니다. 내부 로드 밸런서로 구성하려면:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-internal: "true"
   ```

5. **추가 구성 옵션**:

   a. **대상 유형 설정 (IP 모드)**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
   ```

   b. **보안 그룹 지정**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-0123456789abcdef0
   ```

   c. **서브넷 지정**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
   ```

   d. **교차 영역 로드 밸런싱 비활성화**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "false"
   ```

   e. **액세스 로그 활성화**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-access-log-enabled: "true"
   service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name: "my-elb-logs"
   service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix: "my-app"
   ```

   f. **SSL 인증서 구성 (HTTPS)**:
   ```yaml
   service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:region:account-id:certificate/certificate-id
   service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
   ```

6. **AWS Load Balancer Controller 사용**:
   최신 EKS 클러스터에서는 AWS Load Balancer Controller를 사용하여 더 많은 기능을 활용할 수 있습니다:

   a. **설치**:
   ```bash
   helm repo add eks https://aws.github.io/eks-charts
   helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
     -n kube-system \
     --set clusterName=my-cluster \
     --set serviceAccount.create=false \
     --set serviceAccount.name=aws-load-balancer-controller
   ```

   b. **Application Load Balancer (ALB) 사용 (Ingress)**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: my-ingress
     annotations:
       kubernetes.io/ingress.class: alb
       alb.ingress.kubernetes.io/scheme: internet-facing
   spec:
     rules:
     - http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: my-service
               port:
                 number: 80
   ```

7. **로드 밸런서 유형 비교**:

   | 특성 | Classic Load Balancer | Network Load Balancer | Application Load Balancer |
   |------|----------------------|----------------------|--------------------------|
   | 프로토콜 | TCP, SSL, HTTP, HTTPS | TCP, UDP, TLS | HTTP, HTTPS |
   | 레이어 | 4 & 7 | 4 | 7 |
   | 성능 | 좋음 | 매우 좋음 | 좋음 |
   | 지연 시간 | 중간 | 매우 낮음 | 낮음 |
   | 정적 IP | 아니오 | 예 | 아니오 |
   | 경로 기반 라우팅 | 아니오 | 아니오 | 예 |
   | WebSockets | 제한적 | 예 | 예 |
   | 컨테이너 기반 대상 | 아니오 | 예 (IP 모드) | 예 (IP 모드) |

8. **모범 사례**:
   - 대부분의 HTTP/HTTPS 트래픽은 Ingress와 ALB 사용
   - TCP/UDP 트래픽이나 매우 높은 처리량이 필요한 경우 NLB 사용
   - 레거시 애플리케이션이나 특별한 요구 사항이 없는 경우 CLB 대신 NLB 또는 ALB 사용 권장
   - 프로덕션 환경에서는 항상 교차 영역 로드 밸런싱 활성화

AWS Load Balancer Controller를 사용하면 Kubernetes 서비스와 Ingress 리소스를 통해 AWS 로드 밸런서를 더 효과적으로 관리할 수 있으며, 다양한 어노테이션을 통해 세밀한 구성이 가능합니다.
</details>
