# Amazon EKS 클러스터 생성 퀴즈 (Part 5)

이 퀴즈는 Amazon EKS 클러스터의 고급 구성, 최적화 및 운영 모범 사례에 대한 이해를 테스트합니다. 비용 최적화, 고가용성 설계, 보안 강화 및 운영 자동화에 중점을 둡니다.

## 객관식 문제

### 1. Amazon EKS 클러스터에서 비용을 최적화하기 위한 가장 효과적인 방법은 무엇인가요?

A. 모든 워커 노드를 온디맨드 인스턴스로 실행  
B. 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용  
C. 모든 워커 노드를 예약 인스턴스로 실행  
D. 모든 워커 노드를 Fargate로 실행  

<details>
<summary>정답 및 설명</summary>

**정답: B. 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용**

**설명:**
EKS 클러스터에서 비용을 최적화하는 가장 효과적인 방법은 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용하는 것입니다:

- **스팟 인스턴스**: 온디맨드 가격보다 최대 90% 저렴하지만 AWS가 용량을 회수할 수 있어 중단될 가능성이 있습니다. 내결함성이 있는 상태 비저장(stateless) 워크로드에 적합합니다.
- **온디맨드 인스턴스**: 가격은 높지만 안정적이므로 중요한 상태 저장(stateful) 워크로드나 중단에 민감한 애플리케이션에 적합합니다.

이러한 혼합 접근 방식을 통해:
1. 중요한 워크로드는 온디맨드 인스턴스에서 실행
2. 내결함성이 있는 워크로드는 스팟 인스턴스에서 실행
3. 노드 선호도, 허용 오차(tolerations), 테인트(taints)를 사용하여 워크로드 배치 제어

추가적인 비용 최적화 전략으로는 Karpenter나 Cluster Autoscaler를 사용한 자동 스케일링, 적절한 인스턴스 크기 선택, Graviton(ARM) 인스턴스 사용, 예약 인스턴스 또는 Savings Plans 활용 등이 있습니다.
</details>

### 2. EKS 클러스터에서 여러 가용 영역(AZ)에 노드를 배포하는 주된 이유는 무엇인가요?

A. 네트워크 지연 시간 감소  
B. 데이터 처리량 증가  
C. 고가용성 및 내결함성 향상  
D. AWS 리전 간 데이터 복제 활성화  

<details>
<summary>정답 및 설명</summary>

**정답: C. 고가용성 및 내결함성 향상**

**설명:**
EKS 클러스터에서 여러 가용 영역(AZ)에 노드를 배포하는 주된 이유는 고가용성 및 내결함성을 향상시키기 위함입니다:

1. **가용 영역 장애 대응**: 한 가용 영역에 장애가 발생해도 다른 가용 영역의 노드는 계속 작동하므로 애플리케이션 가용성이 유지됩니다.

2. **인프라 이중화**: 여러 AZ에 걸쳐 워크로드를 분산함으로써 물리적 인프라 장애에 대한 보호 계층을 추가합니다.

3. **자동 복구**: Kubernetes는 장애가 발생한 노드의 파드를 정상 노드로 자동 재스케줄링하여 서비스 중단을 최소화합니다.

4. **롤링 업데이트 안정성**: 업데이트 중에도 여러 AZ에 걸쳐 워크로드가 분산되어 있어 가용성이 유지됩니다.

EKS는 기본적으로 컨트롤 플레인을 여러 AZ에 배포하지만, 워커 노드도 여러 AZ에 배포하여 전체 클러스터의 고가용성을 보장하는 것이 모범 사례입니다. 이를 위해 노드 그룹 생성 시 여러 서브넷(각각 다른 AZ에 위치)을 지정할 수 있습니다.
</details>

### 3. EKS 클러스터에서 파드 네트워킹을 위한 기본 CNI 플러그인은 무엇인가요?

A. Calico  
B. Flannel  
C. Amazon VPC CNI  
D. Weave Net  

<details>
<summary>정답 및 설명</summary>

**정답: C. Amazon VPC CNI**

**설명:**
Amazon EKS 클러스터에서 파드 네트워킹을 위한 기본 CNI(Container Network Interface) 플러그인은 Amazon VPC CNI입니다. 이 플러그인의 주요 특징은 다음과 같습니다:

1. **네이티브 VPC 네트워킹**: 각 파드는 VPC 내에서 고유한 IP 주소를 받아 AWS VPC 네트워킹을 직접 활용합니다.

2. **보안 그룹 통합**: 파드 수준에서 AWS 보안 그룹을 적용할 수 있어 세밀한 네트워크 보안 제어가 가능합니다.

3. **IP 주소 관리**: 각 노드는 VPC 서브넷에서 보조 IP 주소를 할당받아 파드에 제공합니다.

4. **성능**: 오버레이 네트워크를 사용하지 않아 네트워크 성능이 향상됩니다.

5. **AWS 서비스 통합**: AWS Load Balancer Controller, AWS App Mesh 등 다른 AWS 서비스와 원활하게 통합됩니다.

Amazon VPC CNI는 오픈 소스이며 GitHub에서 관리됩니다. 필요에 따라 Calico, Cilium 등 다른 CNI 플러그인으로 대체할 수 있지만, Amazon VPC CNI가 EKS의 기본 옵션이며 AWS에서 공식적으로 지원합니다.
</details>

### 4. EKS 클러스터에서 IAM 역할을 Kubernetes 서비스 계정에 연결하는 기능의 이름은 무엇인가요?

A. IAM for Service Accounts (IRSA)  
B. Pod Identity Webhook  
C. Kubernetes IAM Authenticator  
D. EKS Identity Manager  

<details>
<summary>정답 및 설명</summary>

**정답: A. IAM for Service Accounts (IRSA)**

**설명:**
EKS 클러스터에서 IAM 역할을 Kubernetes 서비스 계정에 연결하는 기능은 IAM for Service Accounts(IRSA)입니다. 이 기능의 주요 특징은 다음과 같습니다:

1. **세분화된 권한 제어**: 파드 수준에서 AWS 리소스에 대한 액세스를 제어할 수 있어, 노드 수준의 광범위한 권한 부여를 방지합니다.

2. **OIDC 기반 인증**: EKS는 OpenID Connect(OIDC) 제공자를 사용하여 Kubernetes 서비스 계정과 IAM 역할 간의 신뢰 관계를 설정합니다.

3. **보안 강화**: 애플리케이션별로 필요한 최소 권한만 부여하는 최소 권한 원칙을 구현할 수 있습니다.

4. **구현 방식**:
   - EKS 클러스터에 대한 OIDC 제공자 생성
   - 서비스 계정을 신뢰하는 IAM 역할 생성
   - 특정 주석(annotation)이 있는 Kubernetes 서비스 계정 생성
   - 해당 서비스 계정을 사용하는 파드 배포

IRSA를 사용하면 AWS SDK를 사용하는 애플리케이션이 노드의 IAM 역할에 의존하지 않고 자체 IAM 역할을 사용하여 AWS 서비스에 안전하게 액세스할 수 있습니다.
</details>

### 5. EKS 클러스터에서 노드 그룹의 Auto Scaling을 관리하는 Kubernetes 네이티브 도구는 무엇인가요?

A. Horizontal Pod Autoscaler  
B. Vertical Pod Autoscaler  
C. Cluster Autoscaler  
D. Node Autoscaler  

<details>
<summary>정답 및 설명</summary>

**정답: C. Cluster Autoscaler**

**설명:**
EKS 클러스터에서 노드 그룹의 Auto Scaling을 관리하는 Kubernetes 네이티브 도구는 Cluster Autoscaler입니다. 이 도구의 주요 특징은 다음과 같습니다:

1. **자동 스케일링**: 파드가 리소스 부족으로 스케줄링되지 못할 때 노드를 자동으로 추가하고, 노드가 충분히 활용되지 않을 때 노드를 제거합니다.

2. **AWS Auto Scaling 그룹 통합**: EKS에서는 AWS Auto Scaling 그룹과 통합되어 작동합니다.

3. **작동 방식**:
   - 스케일 아웃: 파드가 리소스 제약으로 Pending 상태일 때 노드 추가
   - 스케일 인: 노드의 활용도가 낮고 파드를 다른 노드로 이동할 수 있을 때 노드 제거

4. **구성 옵션**:
   - 스케일 업/다운 임계값 설정
   - 노드 그룹 검색 방법 지정
   - 스케일 다운 지연 설정
   - 파드 중단 예산(PDB) 존중

Horizontal Pod Autoscaler(HPA)는 파드 수를 자동으로 조정하고, Vertical Pod Autoscaler(VPA)는 파드의 리소스 요청을 자동으로 조정하지만, 노드 수를 조정하는 것은 Cluster Autoscaler의 역할입니다.

참고로, AWS에서는 Cluster Autoscaler 외에도 Karpenter라는 새로운 노드 프로비저닝 도구를 제공하며, 이는 더 빠르고 유연한 노드 프로비저닝 기능을 제공합니다.
</details>
