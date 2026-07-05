# EKS 소개 퀴즈

이 퀴즈는 Amazon Elastic Kubernetes Service(EKS)의 기본 개념과 특징에 관한 이해도를 테스트합니다. EKS 아키텍처, 구성 요소, 관리 방법, 요금 모델 등의 주제를 다룹니다.

## 객관식 문제

1. Amazon EKS(Elastic Kubernetes Service)의 주요 이점은 무엇인가요?
   * A) 자체 Kubernetes 컨트롤 플레인 인프라를 관리할 필요가 없음
   * B) 다른 관리형 Kubernetes 서비스보다 저렴한 비용
   * C) AWS 서비스만 사용 가능
   * D) 단일 가용 영역에서만 실행 가능

<details>

<summary>정답 보기</summary>

**정답: A) 자체 Kubernetes 컨트롤 플레인 인프라를 관리할 필요가 없음**

**설명:** Amazon EKS(Elastic Kubernetes Service)의 주요 이점은 자체 Kubernetes 컨트롤 플레인 인프라를 관리할 필요가 없다는 것입니다. AWS가 Kubernetes 컨트롤 플레인의 가용성과 확장성을 관리하므로, 사용자는 워크로드 실행에 집중할 수 있습니다.

EKS의 주요 이점:

* **관리형 컨트롤 플레인**: AWS가 컨트롤 플레인 노드, etcd 클러스터, API 서버 등을 관리합니다.
* **고가용성**: 컨트롤 플레인이 여러 가용 영역에 걸쳐 배포되어 단일 장애점이 없습니다.
* **자동 업그레이드 및 패치**: AWS가 Kubernetes 버전 업그레이드 및 보안 패치를 관리합니다.
* **AWS 서비스와의 통합**: IAM, VPC, ELB, ECR 등 다양한 AWS 서비스와 원활하게 통합됩니다.
* **표준 Kubernetes**: 완전히 호환되는 Kubernetes를 제공하여 벤더 종속성을 방지합니다.

다른 옵션들의 문제점:

* EKS는 다른 관리형 Kubernetes 서비스보다 반드시 저렴하지는 않습니다. 실제로 컨트롤 플레인에 대한 시간당 요금이 있습니다.
* EKS는 AWS 서비스뿐만 아니라 모든 Kubernetes 호환 애플리케이션 및 서비스를 실행할 수 있습니다.
* EKS 클러스터는 기본적으로 여러 가용 영역에 걸쳐 배포되어 고가용성을 제공합니다.

</details>

2. Amazon EKS 클러스터의 컨트롤 플레인은 어디에 배포되나요?
   * A) 사용자의 VPC 내
   * B) AWS가 관리하는 계정의 여러 가용 영역에 걸쳐 배포
   * C) 사용자가 선택한 단일 가용 영역
   * D) 사용자의 EC2 인스턴스에서 실행

<details>

<summary>정답 보기</summary>

**정답: B) AWS가 관리하는 계정의 여러 가용 영역에 걸쳐 배포**

**설명:** Amazon EKS 클러스터의 컨트롤 플레인은 AWS가 관리하는 계정의 여러 가용 영역에 걸쳐 배포됩니다. 이는 EKS의 핵심 관리형 서비스 측면 중 하나입니다.

EKS 컨트롤 플레인 배포의 주요 특징:

* **AWS 관리 인프라**: 컨트롤 플레인은 AWS가 소유하고 관리하는 계정에서 실행됩니다.
* **다중 AZ 배포**: 고가용성을 위해 최소 3개의 가용 영역에 걸쳐 배포됩니다.
* **자동 복구**: AWS는 컨트롤 플레인 구성 요소의 상태를 모니터링하고 장애가 발생한 구성 요소를 자동으로 교체합니다.
* **엔드포인트 접근성**: 컨트롤 플레인 엔드포인트는 공개적으로 접근 가능하거나 VPC 내에서만 접근 가능하도록 구성할 수 있습니다.
* **자동 확장**: 클러스터 부하에 따라 컨트롤 플레인 용량이 자동으로 조정됩니다.

다른 옵션들의 문제점:

* 컨트롤 플레인은 사용자의 VPC 내에 배포되지 않습니다. 대신, 사용자의 VPC와 AWS 관리 VPC 간에 ENI(Elastic Network Interface)를 통한 연결이 설정됩니다.
* 컨트롤 플레인은 단일 가용 영역이 아닌 여러 가용 영역에 배포되어 고가용성을 보장합니다.
* 컨트롤 플레인은 사용자의 EC2 인스턴스가 아닌 AWS 관리 인프라에서 실행됩니다.

</details>

3. Amazon EKS에서 워커 노드를 관리하는 방법으로 올바르지 않은 것은 무엇인가요?
   * A) 자체 관리형 노드 그룹
   * B) 관리형 노드 그룹
   * C) Fargate 프로필
   * D) EKS 자동 노드 프로비저닝

<details>

<summary>정답 보기</summary>

**정답: D) EKS 자동 노드 프로비저닝**

**설명:** "EKS 자동 노드 프로비저닝"은 Amazon EKS에서 공식적으로 제공하는 워커 노드 관리 방법이 아닙니다. 이는 존재하지 않는 기능입니다.

Amazon EKS에서 워커 노드를 관리하는 실제 방법은 다음과 같습니다:

1. **자체 관리형 노드 그룹**:
   * 사용자가 EC2 인스턴스를 직접 생성하고 관리합니다.
   * Auto Scaling 그룹을 통해 관리할 수 있습니다.
   * 노드 구성에 대한 완전한 제어가 가능합니다.
   * 운영 오버헤드가 가장 큽니다.
2. **관리형 노드 그룹**:
   * AWS가 노드의 프로비저닝 및 수명 주기를 관리합니다.
   * 노드 업그레이드, 패치, 조정이 자동화됩니다.
   * EC2 Auto Scaling 그룹을 기반으로 합니다.
   * 표준 Amazon Linux 또는 Bottlerocket AMI를 사용합니다.
3. **Fargate 프로필**:
   * 서버리스 컴퓨팅 옵션으로, 개별 EC2 인스턴스를 관리할 필요가 없습니다.
   * 포드 단위로 컴퓨팅 리소스를 프로비저닝합니다.
   * 인프라 관리 오버헤드가 가장 적습니다.
   * 특정 제한 사항이 있습니다(예: DaemonSet 미지원, 특정 리소스 제한).

노드 자동 확장을 위해 EKS는 Kubernetes Cluster Autoscaler 또는 Karpenter와 같은 도구를 지원하지만, "EKS 자동 노드 프로비저닝"이라는 공식 기능은 없습니다.

</details>

4. Amazon EKS 클러스터에서 포드 네트워킹을 위해 기본적으로 사용되는 CNI 플러그인은 무엇인가요?
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>정답 보기</summary>

**정답: C) AWS VPC CNI**

**설명:** Amazon EKS 클러스터에서 포드 네트워킹을 위해 기본적으로 사용되는 CNI(Container Network Interface) 플러그인은 AWS VPC CNI입니다. 이 플러그인은 Amazon VPC 네트워킹을 Kubernetes 포드에 직접 통합합니다.

AWS VPC CNI의 주요 특징:

* **VPC 네이티브 IP 주소 할당**: 포드는 VPC의 IP 주소를 직접 할당받아 VPC 내의 다른 리소스와 동일한 네트워크 공간에 존재합니다.
* **보조 IP 주소 사용**: 각 노드의 탄력적 네트워크 인터페이스(ENI)에 연결된 보조 IP 주소를 포드에 할당합니다.
* **보안 그룹 통합**: 포드 수준에서 보안 그룹을 적용할 수 있습니다(SecurityGroupsForPods 기능).
* **VPC 흐름 로그 가시성**: 포드 트래픽이 VPC 흐름 로그에 표시됩니다.
* **AWS 네트워킹 기능 활용**: VPC 피어링, Transit Gateway, PrivateLink 등의 기능을 포드에 직접 활용할 수 있습니다.

AWS VPC CNI는 오픈 소스 프로젝트이며, GitHub에서 코드를 확인할 수 있습니다: https://github.com/aws/amazon-vpc-cni-k8s

다른 CNI 플러그인(Flannel, Calico, Weave Net 등)도 EKS에 설치할 수 있지만, 기본 제공되는 것은 AWS VPC CNI입니다.

</details>

5. Amazon EKS에서 Kubernetes 리소스에 대한 인증 및 권한 부여를 관리하는 방법은 무엇인가요?
   * A) Kubernetes 서비스 계정만 사용
   * B) AWS IAM과 Kubernetes RBAC의 통합
   * C) EKS 전용 권한 관리 시스템
   * D) AWS Cognito를 통한 사용자 인증

<details>

<summary>정답 보기</summary>

**정답: B) AWS IAM과 Kubernetes RBAC의 통합**

**설명:** Amazon EKS에서는 AWS IAM(Identity and Access Management)과 Kubernetes RBAC(Role-Based Access Control)을 통합하여 Kubernetes 리소스에 대한 인증 및 권한 부여를 관리합니다. 이 통합 접근 방식은 AWS의 강력한 ID 관리 기능과 Kubernetes의 세분화된 권한 제어를 결합합니다.

주요 특징:

* **IAM 인증**: AWS IAM 자격 증명을 사용하여 Kubernetes API 서버에 인증합니다.
* **aws-auth ConfigMap**: IAM 역할 또는 사용자를 Kubernetes 사용자 및 그룹에 매핑합니다.
* **RBAC 권한 부여**: Kubernetes RBAC 시스템을 사용하여 클러스터 내 권한을 제어합니다.
* **IRSA(IAM Roles for Service Accounts)**: Kubernetes 서비스 계정에 IAM 역할을 연결하여 포드가 AWS 서비스에 안전하게 접근할 수 있게 합니다.

작동 방식:

1. 사용자가 `aws eks get-token` 명령(AWS CLI 또는 AWS SDK를 통해)을 사용하여 Kubernetes API 서버에 대한 인증 토큰을 얻습니다.
2. 이 토큰은 IAM 자격 증명을 사용하여 서명됩니다.
3. Kubernetes API 서버는 AWS IAM 인증자를 사용하여 토큰을 검증합니다.
4. aws-auth ConfigMap의 매핑에 따라 사용자에게 Kubernetes 사용자 및 그룹이 할당됩니다.
5. Kubernetes RBAC 시스템이 해당 사용자 또는 그룹에 부여된 권한에 따라 요청을 허용하거나 거부합니다.

다른 옵션들의 문제점:

* Kubernetes 서비스 계정만 사용하는 것은 AWS 서비스와의 통합이 제한됩니다.
* EKS에는 별도의 전용 권한 관리 시스템이 없으며, 표준 Kubernetes RBAC와 AWS IAM을 통합하여 사용합니다.
* AWS Cognito는 EKS 인증에 직접 사용되지 않지만, OIDC 제공자로 구성하여 사용할 수는 있습니다.

</details>

\## 객관식 문제

1. Amazon EKS(Elastic Kubernetes Service)의 주요 이점은 무엇인가요?
   * A) 자체 Kubernetes 컨트롤 플레인 인프라를 관리할 필요가 없음
   * B) 다른 관리형 Kubernetes 서비스보다 저렴한 비용
   * C) AWS 서비스만 사용 가능
   * D) 단일 가용 영역에서만 실행 가능

<details>

<summary>정답 보기</summary>

**정답: A) 자체 Kubernetes 컨트롤 플레인 인프라를 관리할 필요가 없음**

**설명:** Amazon EKS(Elastic Kubernetes Service)의 주요 이점은 자체 Kubernetes 컨트롤 플레인 인프라를 관리할 필요가 없다는 것입니다. AWS가 Kubernetes 컨트롤 플레인의 가용성과 확장성을 관리하므로, 사용자는 워크로드 실행에 집중할 수 있습니다.

EKS의 주요 이점:

* **관리형 컨트롤 플레인**: AWS가 컨트롤 플레인 노드, etcd 클러스터, API 서버 등을 관리합니다.
* **고가용성**: 컨트롤 플레인이 여러 가용 영역에 걸쳐 배포되어 단일 장애점이 없습니다.
* **자동 업그레이드 및 패치**: AWS가 Kubernetes 버전 업그레이드 및 보안 패치를 관리합니다.
* **AWS 서비스와의 통합**: IAM, VPC, ELB, ECR 등 다양한 AWS 서비스와 원활하게 통합됩니다.
* **표준 Kubernetes**: 완전히 호환되는 Kubernetes를 제공하여 벤더 종속성을 방지합니다.

다른 옵션들의 문제점:

* EKS는 다른 관리형 Kubernetes 서비스보다 반드시 저렴하지는 않습니다. 실제로 컨트롤 플레인에 대한 시간당 요금이 있습니다.
* EKS는 AWS 서비스뿐만 아니라 모든 Kubernetes 호환 애플리케이션 및 서비스를 실행할 수 있습니다.
* EKS 클러스터는 기본적으로 여러 가용 영역에 걸쳐 배포되어 고가용성을 제공합니다.

</details>

2. Amazon EKS 클러스터의 컨트롤 플레인은 어디에 배포되나요?
   * A) 사용자의 VPC 내
   * B) AWS가 관리하는 계정의 여러 가용 영역에 걸쳐 배포
   * C) 사용자가 선택한 단일 가용 영역
   * D) 사용자의 EC2 인스턴스에서 실행

<details>

<summary>정답 보기</summary>

**정답: B) AWS가 관리하는 계정의 여러 가용 영역에 걸쳐 배포**

**설명:** Amazon EKS 클러스터의 컨트롤 플레인은 AWS가 관리하는 계정의 여러 가용 영역에 걸쳐 배포됩니다. 이는 EKS의 핵심 관리형 서비스 측면 중 하나입니다.

EKS 컨트롤 플레인 배포의 주요 특징:

* **AWS 관리 인프라**: 컨트롤 플레인은 AWS가 소유하고 관리하는 계정에서 실행됩니다.
* **다중 AZ 배포**: 고가용성을 위해 최소 3개의 가용 영역에 걸쳐 배포됩니다.
* **자동 복구**: AWS는 컨트롤 플레인 구성 요소의 상태를 모니터링하고 장애가 발생한 구성 요소를 자동으로 교체합니다.
* **엔드포인트 접근성**: 컨트롤 플레인 엔드포인트는 공개적으로 접근 가능하거나 VPC 내에서만 접근 가능하도록 구성할 수 있습니다.
* **자동 확장**: 클러스터 부하에 따라 컨트롤 플레인 용량이 자동으로 조정됩니다.

다른 옵션들의 문제점:

* 컨트롤 플레인은 사용자의 VPC 내에 배포되지 않습니다. 대신, 사용자의 VPC와 AWS 관리 VPC 간에 ENI(Elastic Network Interface)를 통한 연결이 설정됩니다.
* 컨트롤 플레인은 단일 가용 영역이 아닌 여러 가용 영역에 배포되어 고가용성을 보장합니다.
* 컨트롤 플레인은 사용자의 EC2 인스턴스가 아닌 AWS 관리 인프라에서 실행됩니다.

</details>

3. Amazon EKS에서 워커 노드를 관리하는 방법으로 올바르지 않은 것은 무엇인가요?
   * A) 자체 관리형 노드 그룹
   * B) 관리형 노드 그룹
   * C) Fargate 프로필
   * D) EKS 자동 노드 프로비저닝

<details>

<summary>정답 보기</summary>

**정답: D) EKS 자동 노드 프로비저닝**

**설명:** "EKS 자동 노드 프로비저닝"은 Amazon EKS에서 공식적으로 제공하는 워커 노드 관리 방법이 아닙니다. 이는 존재하지 않는 기능입니다.

Amazon EKS에서 워커 노드를 관리하는 실제 방법은 다음과 같습니다:

1. **자체 관리형 노드 그룹**:
   * 사용자가 EC2 인스턴스를 직접 생성하고 관리합니다.
   * Auto Scaling 그룹을 통해 관리할 수 있습니다.
   * 노드 구성에 대한 완전한 제어가 가능합니다.
   * 운영 오버헤드가 가장 큽니다.
2. **관리형 노드 그룹**:
   * AWS가 노드의 프로비저닝 및 수명 주기를 관리합니다.
   * 노드 업그레이드, 패치, 조정이 자동화됩니다.
   * EC2 Auto Scaling 그룹을 기반으로 합니다.
   * 표준 Amazon Linux 또는 Bottlerocket AMI를 사용합니다.
3. **Fargate 프로필**:
   * 서버리스 컴퓨팅 옵션으로, 개별 EC2 인스턴스를 관리할 필요가 없습니다.
   * 포드 단위로 컴퓨팅 리소스를 프로비저닝합니다.
   * 인프라 관리 오버헤드가 가장 적습니다.
   * 특정 제한 사항이 있습니다(예: DaemonSet 미지원, 특정 리소스 제한).

노드 자동 확장을 위해 EKS는 Kubernetes Cluster Autoscaler 또는 Karpenter와 같은 도구를 지원하지만, "EKS 자동 노드 프로비저닝"이라는 공식 기능은 없습니다.

</details>

4. Amazon EKS 클러스터에서 포드 네트워킹을 위해 기본적으로 사용되는 CNI 플러그인은 무엇인가요?
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>정답 보기</summary>

**정답: C) AWS VPC CNI**

**설명:** Amazon EKS 클러스터에서 포드 네트워킹을 위해 기본적으로 사용되는 CNI(Container Network Interface) 플러그인은 AWS VPC CNI입니다. 이 플러그인은 Amazon VPC 네트워킹을 Kubernetes 포드에 직접 통합합니다.

AWS VPC CNI의 주요 특징:

* **VPC 네이티브 IP 주소 할당**: 포드는 VPC의 IP 주소를 직접 할당받아 VPC 내의 다른 리소스와 동일한 네트워크 공간에 존재합니다.
* **보조 IP 주소 사용**: 각 노드의 탄력적 네트워크 인터페이스(ENI)에 연결된 보조 IP 주소를 포드에 할당합니다.
* **보안 그룹 통합**: 포드 수준에서 보안 그룹을 적용할 수 있습니다(SecurityGroupsForPods 기능).
* **VPC 흐름 로그 가시성**: 포드 트래픽이 VPC 흐름 로그에 표시됩니다.
* **AWS 네트워킹 기능 활용**: VPC 피어링, Transit Gateway, PrivateLink 등의 기능을 포드에 직접 활용할 수 있습니다.

AWS VPC CNI는 오픈 소스 프로젝트이며, GitHub에서 코드를 확인할 수 있습니다: https://github.com/aws/amazon-vpc-cni-k8s

다른 CNI 플러그인(Flannel, Calico, Weave Net 등)도 EKS에 설치할 수 있지만, 기본 제공되는 것은 AWS VPC CNI입니다.

</details>

5. Amazon EKS에서 Kubernetes 리소스에 대한 인증 및 권한 부여를 관리하는 방법은 무엇인가요?
   * A) Kubernetes 서비스 계정만 사용
   * B) AWS IAM과 Kubernetes RBAC의 통합
   * C) EKS 전용 권한 관리 시스템
   * D) AWS Cognito를 통한 사용자 인증

<details>

<summary>정답 보기</summary>

**정답: B) AWS IAM과 Kubernetes RBAC의 통합**

**설명:** Amazon EKS에서는 AWS IAM(Identity and Access Management)과 Kubernetes RBAC(Role-Based Access Control)을 통합하여 Kubernetes 리소스에 대한 인증 및 권한 부여를 관리합니다. 이 통합 접근 방식은 AWS의 강력한 ID 관리 기능과 Kubernetes의 세분화된 권한 제어를 결합합니다.

주요 특징:

* **IAM 인증**: AWS IAM 자격 증명을 사용하여 Kubernetes API 서버에 인증합니다.
* **aws-auth ConfigMap**: IAM 역할 또는 사용자를 Kubernetes 사용자 및 그룹에 매핑합니다.
* **RBAC 권한 부여**: Kubernetes RBAC 시스템을 사용하여 클러스터 내 권한을 제어합니다.
* **IRSA(IAM Roles for Service Accounts)**: Kubernetes 서비스 계정에 IAM 역할을 연결하여 포드가 AWS 서비스에 안전하게 접근할 수 있게 합니다.

작동 방식:

1. 사용자가 `aws eks get-token` 명령(AWS CLI 또는 AWS SDK를 통해)을 사용하여 Kubernetes API 서버에 대한 인증 토큰을 얻습니다.
2. 이 토큰은 IAM 자격 증명을 사용하여 서명됩니다.
3. Kubernetes API 서버는 AWS IAM 인증자를 사용하여 토큰을 검증합니다.
4. aws-auth ConfigMap의 매핑에 따라 사용자에게 Kubernetes 사용자 및 그룹이 할당됩니다.
5. Kubernetes RBAC 시스템이 해당 사용자 또는 그룹에 부여된 권한에 따라 요청을 허용하거나 거부합니다.

다른 옵션들의 문제점:

* Kubernetes 서비스 계정만 사용하는 것은 AWS 서비스와의 통합이 제한됩니다.
* EKS에는 별도의 전용 권한 관리 시스템이 없으며, 표준 Kubernetes RBAC와 AWS IAM을 통합하여 사용합니다.
* AWS Cognito는 EKS 인증에 직접 사용되지 않지만, OIDC 제공자로 구성하여 사용할 수는 있습니다.

</details>

6\. Amazon EKS 클러스터에서 포드가 AWS 서비스(예: S3, DynamoDB)에 접근하기 위한 권장 방법은 무엇인가요? - A) EC2 인스턴스 프로필을 사용하여 노드에 IAM 역할 부여 - B) AWS 자격 증명을 환경 변수로 포드에 직접 주입 - C) IAM 역할을 Kubernetes 서비스 계정에 연결(IRSA) - D) AWS 자격 증명을 Kubernetes Secret으로 저장하여 마운트

<details>

<summary>정답 보기</summary>

**정답: C) IAM 역할을 Kubernetes 서비스 계정에 연결(IRSA)**

**설명:** Amazon EKS 클러스터에서 포드가 AWS 서비스에 접근하기 위한 권장 방법은 IAM 역할을 Kubernetes 서비스 계정에 연결하는 것입니다. 이 기능은 IRSA(IAM Roles for Service Accounts)라고 불리며, 포드 수준에서 세분화된 권한을 제공합니다.

IRSA의 주요 이점:

* **최소 권한 원칙**: 각 애플리케이션에 필요한 최소한의 권한만 부여할 수 있습니다.
* **권한 격리**: 같은 노드에서 실행되는 다른 포드는 서로 다른 IAM 권한을 가질 수 있습니다.
* **자격 증명 관리 간소화**: AWS 자격 증명을 직접 관리할 필요가 없습니다.
* **보안 강화**: 자격 증명이 코드나 구성에 하드코딩되지 않습니다.

IRSA 설정 방법:

1.  EKS 클러스터에 OpenID Connect(OIDC) 제공자 연결:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster=<cluster-name> --approve
    ```
2.  서비스 계정에 대한 IAM 역할 생성:

    ```bash
    eksctl create iamserviceaccount \
      --name=<service-account-name> \
      --namespace=<namespace> \
      --cluster=<cluster-name> \
      --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
      --approve
    ```
3.  포드 매니페스트에서 서비스 계정 참조:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: <service-account-name>
      containers:
      - name: my-container
        image: my-image
    ```

다른 옵션들의 문제점:

* EC2 인스턴스 프로필을 사용하면 같은 노드의 모든 포드가 동일한 권한을 갖게 되어 최소 권한 원칙을 위반합니다.
* AWS 자격 증명을 환경 변수로 주입하는 것은 자격 증명이 노출될 위험이 있고 자격 증명 순환이 어렵습니다.
* AWS 자격 증명을 Kubernetes Secret으로 저장하는 것은 자격 증명 관리의 부담이 있고 자격 증명 순환이 복잡합니다.

</details>

7. Amazon EKS 클러스터의 로깅 기능에 대한 설명으로 올바른 것은 무엇인가요?
   * A) 모든 로그는 기본적으로 CloudWatch Logs로 전송됨
   * B) 컨트롤 플레인 로그는 선택적으로 CloudWatch Logs로 전송 가능
   * C) 워커 노드 로그만 CloudWatch Logs로 전송 가능
   * D) EKS는 로깅 기능을 제공하지 않음

<details>

<summary>정답 보기</summary>

**정답: B) 컨트롤 플레인 로그는 선택적으로 CloudWatch Logs로 전송 가능**

**설명:** Amazon EKS 클러스터에서는 컨트롤 플레인 로그를 선택적으로 CloudWatch Logs로 전송할 수 있습니다. 이 기능은 기본적으로 비활성화되어 있으며, 사용자가 필요한 로그 유형을 선택하여 활성화할 수 있습니다.

EKS 컨트롤 플레인 로깅의 주요 특징:

* **선택적 활성화**: 클러스터 생성 시 또는 기존 클러스터에서 활성화할 수 있습니다.
* **로그 유형 선택**: 다음 로그 유형 중 필요한 것만 선택할 수 있습니다:
  * API 서버(api)
  * 감사(audit)
  * 인증자(authenticator)
  * 컨트롤러 관리자(controllerManager)
  * 스케줄러(scheduler)
* **CloudWatch Logs 통합**: 선택한 로그는 AWS CloudWatch Logs로 전송되어 저장, 분석, 모니터링이 가능합니다.
* **비용 고려**: 로그 저장에는 CloudWatch Logs 요금이 적용됩니다.

로깅 활성화 방법:

```bash
# AWS CLI를 사용한 로깅 활성화
aws eks update-cluster-config \
    --region <region> \
    --name <cluster-name> \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# eksctl을 사용한 로깅 활성화
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster <cluster-name> --region <region>
```

워커 노드 로깅:

* 워커 노드 로그는 EKS 컨트롤 플레인 로깅 기능에 포함되지 않습니다.
* 워커 노드 로그를 CloudWatch Logs로 전송하려면 CloudWatch 에이전트를 설치하거나 Fluentd/Fluent Bit와 같은 로깅 솔루션을 구성해야 합니다.

다른 옵션들의 문제점:

* 모든 로그가 기본적으로 CloudWatch Logs로 전송되지는 않습니다. 사용자가 명시적으로 활성화해야 합니다.
* 워커 노드 로그만 CloudWatch Logs로 전송할 수 있는 것이 아니라, 컨트롤 플레인 로그도 전송 가능합니다.
* EKS는 컨트롤 플레인 로깅 기능을 제공합니다.

</details>

8. Amazon EKS 클러스터의 비용 구성 요소가 아닌 것은 무엇인가요?
   * A) EKS 컨트롤 플레인 시간당 요금
   * B) 워커 노드로 사용되는 EC2 인스턴스 비용
   * C) Fargate 포드 실행 비용
   * D) Kubernetes 라이선스 비용

<details>

<summary>정답 보기</summary>

**정답: D) Kubernetes 라이선스 비용**

**설명:** Kubernetes 라이선스 비용은 Amazon EKS 클러스터의 비용 구성 요소가 아닙니다. Kubernetes는 오픈 소스 소프트웨어로, Cloud Native Computing Foundation(CNCF)에서 관리하며 Apache 2.0 라이선스 하에 무료로 사용할 수 있습니다. 따라서 EKS 사용 시 별도의 Kubernetes 라이선스 비용은 발생하지 않습니다.

Amazon EKS 클러스터의 실제 비용 구성 요소는 다음과 같습니다:

1. **EKS 컨트롤 플레인 시간당 요금**:
   * 각 EKS 클러스터에 대해 시간당 고정 요금이 부과됩니다(예: 시간당 $0.10).
   * 이 비용은 클러스터 크기나 워크로드와 관계없이 일정합니다.
   * 여러 리전에 걸쳐 있는 경우 리전별로 요금이 부과됩니다.
2. **워커 노드로 사용되는 EC2 인스턴스 비용**:
   * 자체 관리형 노드 그룹이나 관리형 노드 그룹에서 사용하는 EC2 인스턴스에 대한 비용이 발생합니다.
   * 인스턴스 유형, 크기, 수량, 실행 시간에 따라 비용이 달라집니다.
   * 예약 인스턴스, Savings Plans, 스팟 인스턴스 등을 통해 비용을 최적화할 수 있습니다.
3. **Fargate 포드 실행 비용**:
   * Fargate를 사용하는 경우, 포드에 할당된 vCPU 및 메모리 리소스에 따라 비용이 부과됩니다.
   * 포드가 실행되는 시간에 따라 초 단위로 비용이 계산됩니다.
   * 노드 관리 오버헤드가 없지만, 일반적으로 EC2 기반 노드보다 비용이 높을 수 있습니다.
4. **추가 AWS 리소스 비용**:
   * EBS 볼륨
   * 로드 밸런서(NLB, ALB)
   * CloudWatch 로그 및 메트릭
   * NAT 게이트웨이
   * 데이터 전송

비용 최적화 전략:

* 적절한 인스턴스 유형 선택
* 자동 확장 구성
* 스팟 인스턴스 활용
* 클러스터 자동화 및 일정 기반 확장
* 리소스 요청 및 제한 최적화
* 비용 모니터링 및 분석

</details>

9. Amazon EKS 클러스터에서 로드 밸런싱을 구현하는 방법으로 올바른 것은 무엇인가요?
   * A) 기본 제공되는 EKS 로드 밸런서 사용
   * B) Kubernetes Service 리소스와 AWS Load Balancer Controller 통합
   * C) 수동으로 EC2 로드 밸런서 생성 및 구성
   * D) EKS는 로드 밸런싱을 지원하지 않음

<details>

<summary>정답 보기</summary>

**정답: B) Kubernetes Service 리소스와 AWS Load Balancer Controller 통합**

**설명:** Amazon EKS 클러스터에서 로드 밸런싱을 구현하는 올바른 방법은 Kubernetes Service 리소스와 AWS Load Balancer Controller를 통합하는 것입니다. 이 접근 방식은 Kubernetes의 선언적 리소스 관리와 AWS의 로드 밸런싱 기능을 결합합니다.

EKS에서 로드 밸런싱 구현 방법:

1.  **기본 LoadBalancer 유형 서비스**:

    * Kubernetes의 `LoadBalancer` 유형 Service를 생성하면 기본적으로 Classic Load Balancer(CLB) 또는 Network Load Balancer(NLB)가 프로비저닝됩니다.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2.  **AWS Load Balancer Controller**:

    * 더 고급 기능을 위해 AWS Load Balancer Controller를 설치하여 Application Load Balancer(ALB) 및 Network Load Balancer(NLB)를 관리할 수 있습니다.
    * Ingress 리소스를 통해 ALB를 프로비저닝하고 구성할 수 있습니다.
    * 어노테이션을 통해 로드 밸런서의 다양한 속성을 구성할 수 있습니다.

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
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
3.  **Service 어노테이션**:

    * 서비스에 어노테이션을 추가하여 로드 밸런서 유형 및 구성을 지정할 수 있습니다.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
        service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    spec:
      type: LoadBalancer
      # ...
    ```

다른 옵션들의 문제점:

* EKS에는 "기본 제공되는 EKS 로드 밸런서"라는 별도의 구성 요소가 없습니다. 로드 밸런싱은 Kubernetes Service 리소스와 AWS 로드 밸런서의 통합을 통해 제공됩니다.
* 수동으로 EC2 로드 밸런서를 생성하고 구성하는 것은 가능하지만, Kubernetes의 선언적 접근 방식과 일치하지 않으며 관리가 복잡해집니다.
* EKS는 로드 밸런싱을 완벽하게 지원합니다.

</details>

10. Amazon EKS 클러스터에서 스토리지를 관리하는 방법으로 올바르지 않은 것은 무엇인가요?
    * A) EBS CSI 드라이버를 사용하여 EBS 볼륨 프로비저닝
    * B) EFS CSI 드라이버를 사용하여 EFS 파일 시스템 마운트
    * C) EKS 내장 스토리지 관리자를 통한 자동 볼륨 프로비저닝
    * D) FSx for Lustre CSI 드라이버를 사용하여 고성능 파일 시스템 연결

<details>

<summary>정답 보기</summary>

**정답: C) EKS 내장 스토리지 관리자를 통한 자동 볼륨 프로비저닝**

**설명:** "EKS 내장 스토리지 관리자"는 존재하지 않는 기능입니다. Amazon EKS에는 자동 볼륨 프로비저닝을 위한 내장 스토리지 관리자가 없으며, 스토리지는 CSI(Container Storage Interface) 드라이버를 통해 관리됩니다.

Amazon EKS 클러스터에서 스토리지를 관리하는 실제 방법은 다음과 같습니다:

1.  **EBS CSI 드라이버**:

    * Amazon EBS(Elastic Block Store) 볼륨을 Kubernetes 포드에 연결할 수 있습니다.
    * 블록 스토리지가 필요한 애플리케이션(데이터베이스 등)에 적합합니다.
    * 동적 프로비저닝, 스냅샷, 볼륨 크기 조정 등을 지원합니다.
    * 단일 가용 영역 내에서만 접근 가능합니다(ReadWriteOnce 접근 모드).

    ```yaml
    # StorageClass 예시
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
2.  **EFS CSI 드라이버**:

    * Amazon EFS(Elastic File System)를 Kubernetes 포드에 마운트할 수 있습니다.
    * 여러 포드에서 동시에 접근해야 하는 공유 파일 시스템에 적합합니다.
    * 여러 가용 영역에 걸쳐 접근 가능합니다(ReadWriteMany 접근 모드).
    * 웹 서버, CMS, CI/CD 파이프라인 등에 적합합니다.

    ```yaml
    # StorageClass 예시
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    ```
3.  **FSx for Lustre CSI 드라이버**:

    * Amazon FSx for Lustre를 Kubernetes 포드에 연결할 수 있습니다.
    * 고성능 컴퓨팅, 기계 학습, 빅 데이터 분석과 같은 고성능 워크로드에 적합합니다.
    * 높은 처리량과 낮은 지연 시간을 제공합니다.

    ```yaml
    # StorageClass 예시
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: fsx-sc
    provisioner: fsx.csi.aws.com
    parameters:
      subnetId: subnet-0123456789abcdef0
      securityGroupIds: sg-0123456789abcdef0
      deploymentType: PERSISTENT_1
      automaticBackupRetentionDays: "1"
      dailyAutomaticBackupStartTime: "00:00"
      perUnitStorageThroughput: "200"
      storageCapacity: "1200"
    ```
4. **기타 스토리지 옵션**:
   * Amazon S3(Simple Storage Service)를 CSI 드라이버나 S3 마운터를 통해 사용
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * 타사 스토리지 솔루션(Portworx, Rook 등)

스토리지 관리 모범 사례:

* 워크로드 요구 사항에 맞는 적절한 스토리지 유형 선택
* 동적 프로비저닝을 위한 StorageClass 구성
* 백업 및 복구 전략 수립
* 스토리지 성능 모니터링
* 비용 최적화를 위한 적절한 스토리지 클래스 및 크기 선택

</details>

## 실습 문제

### 실습 1: EKS 클러스터 생성 및 구성

**시나리오:** 당신은 회사의 DevOps 엔지니어로, 개발 팀을 위한 Amazon EKS 클러스터를 설정해야 합니다. 클러스터는 개발 환경용이며, 비용 효율적이면서도 필요한 기능을 모두 제공해야 합니다.

**요구사항:**

1. 비용 효율적인 EKS 클러스터 생성
2. 적절한 노드 그룹 구성
3. 기본적인 모니터링 설정
4. kubectl을 사용하여 클러스터에 접근할 수 있도록 구성

**해결 방법:**

<details>

<summary>해결 방법 보기</summary>

**1. eksctl을 사용하여 EKS 클러스터 생성**

```bash
# eksctl 설치 (아직 설치되지 않은 경우)
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# 클러스터 생성
cat << EOF > eks-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: false
        ebs: true
        fsx: false
        efs: false
        albIngress: true
        xRay: false
        cloudWatch: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

eksctl create cluster -f eks-cluster.yaml
```

**2. kubectl 구성 및 확인**

```bash
# kubectl 구성 업데이트
aws eks update-kubeconfig --name dev-cluster --region us-west-2

# 클러스터 연결 확인
kubectl get nodes
kubectl cluster-info
```

**3. 기본 모니터링 구성 요소 확인**

```bash
# 기본 시스템 포드 확인
kubectl get pods -n kube-system

# 메트릭 서버 설치 (기본 제공되지 않는 경우)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 메트릭 서버 작동 확인
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
```

**4. AWS Load Balancer Controller 설치**

```bash
# IAM 정책 생성
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam-policy.json

# IRSA 설정
eksctl create iamserviceaccount \
  --cluster=dev-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Helm으로 컨트롤러 설치
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dev-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

**5. 클러스터 상태 확인**

```bash
# 노드 상태 확인
kubectl get nodes -o wide

# 시스템 포드 상태 확인
kubectl get pods -n kube-system

# 클러스터 이벤트 확인
kubectl get events --sort-by='.lastTimestamp'

# 클러스터 정보 확인
kubectl cluster-info
```

**6. 테스트 애플리케이션 배포**

```bash
# 간단한 nginx 배포
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# 배포 확인
kubectl get deployment nginx
kubectl get service nginx
```

이 실습을 통해 비용 효율적인 EKS 클러스터를 생성하고, 기본적인 모니터링을 설정하며, 로드 밸런서 컨트롤러를 구성하여 애플리케이션을 외부에 노출하는 방법을 배울 수 있습니다. t3.medium 인스턴스 타입은 개발 환경에 적합한 비용 효율적인 선택이며, 오토스케일링 설정을 통해 필요에 따라 노드를 확장할 수 있습니다.

</details>

\### 실습 2: EKS 클러스터에서 애플리케이션 배포 및 서비스 노출

**시나리오:** 당신의 팀은 마이크로서비스 아키텍처를 기반으로 한 웹 애플리케이션을 개발했습니다. 이 애플리케이션을 EKS 클러스터에 배포하고, 외부에서 접근할 수 있도록 구성해야 합니다.

**요구사항:**

1. 프론트엔드와 백엔드 서비스 배포
2. 서비스 간 통신 구성
3. 인그레스 컨트롤러를 통한 외부 접근 구성
4. 기본적인 스케일링 설정

**해결 방법:**

<details>

<summary>해결 방법 보기</summary>

**1. 네임스페이스 생성**

```bash
kubectl create namespace web-app
kubectl config set-context --current --namespace=web-app
```

**2. 백엔드 서비스 배포**

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: web-app
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
      - name: backend
        image: nginx:alpine  # 실제 백엔드 이미지로 대체
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: web-app
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 8080
```

```bash
kubectl apply -f backend-deployment.yaml
```

**3. 프론트엔드 서비스 배포**

```yaml
# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: web-app
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
      - name: frontend
        image: nginx:alpine  # 실제 프론트엔드 이미지로 대체
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_URL
          value: "http://backend-service"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: web-app
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
```

```bash
kubectl apply -f frontend-deployment.yaml
```

**4. 인그레스 리소스 생성 (AWS ALB Ingress Controller 사용)**

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

```bash
kubectl apply -f ingress.yaml
```

**5. 수평 포드 자동 확장(HPA) 구성**

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
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

```bash
kubectl apply -f hpa.yaml
```

**6. 배포 상태 확인**

```bash
# 배포 상태 확인
kubectl get deployments -n web-app

# 서비스 상태 확인
kubectl get services -n web-app

# 인그레스 상태 확인
kubectl get ingress -n web-app

# HPA 상태 확인
kubectl get hpa -n web-app

# ALB 주소 확인
kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

**7. 로드 테스트 및 스케일링 확인**

```bash
# ALB 주소 가져오기
ALB_ADDRESS=$(kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# 부하 테스트 (별도의 도구 필요)
# 예: Apache Bench 사용
ab -n 10000 -c 100 http://$ALB_ADDRESS/

# 스케일링 확인
kubectl get hpa -n web-app -w
```

이 실습을 통해 EKS 클러스터에 마이크로서비스 아키텍처 애플리케이션을 배포하고, AWS ALB Ingress Controller를 사용하여 외부에 노출하며, HPA를 통해 자동 스케일링을 구성하는 방법을 배울 수 있습니다. 리소스 요청과 제한을 적절히 설정하여 효율적인 리소스 사용을 보장하고, 인그레스 규칙을 통해 경로 기반 라우팅을 구현했습니다.

</details>

\## 고급 주제

다음은 Amazon EKS에 관한 고급 주제에 대한 질문입니다. 이 섹션은 EKS의 심화 기능과 통합에 대한 이해를 테스트합니다.

1. Amazon EKS에서 Fargate 프로필을 구성할 때 올바른 설명은 무엇인가요?
   * A) Fargate 프로필은 특정 네임스페이스와 레이블에 기반하여 포드를 Fargate에서 실행하도록 지정함
   * B) Fargate 프로필은 모든 포드를 자동으로 Fargate에서 실행하도록 설정함
   * C) Fargate 프로필은 특정 EC2 인스턴스 유형에서만 포드를 실행하도록 제한함
   * D) Fargate 프로필은 클러스터 전체의 리소스 할당량을 설정함

<details>

<summary>정답 보기</summary>

**정답: A) Fargate 프로필은 특정 네임스페이스와 레이블에 기반하여 포드를 Fargate에서 실행하도록 지정함**

**설명:** Amazon EKS Fargate 프로필은 특정 네임스페이스와 레이블에 기반하여 어떤 포드가 Fargate에서 실행될지 지정하는 구성입니다. 이를 통해 서버리스 컨테이너 실행 환경과 EC2 기반 노드를 함께 사용하는 하이브리드 아키텍처를 구성할 수 있습니다.

Fargate 프로필의 주요 특징:

* **선택적 실행**: 모든 포드가 아닌, 프로필에 정의된 조건과 일치하는 포드만 Fargate에서 실행됩니다.
* **네임스페이스 및 레이블 선택기**: 특정 네임스페이스와 레이블 조합을 기반으로 포드를 선택합니다.
* **서브넷 지정**: 포드가 실행될 프라이빗 서브넷을 지정할 수 있습니다.
* **IAM 역할**: Fargate 포드에 대한 IAM 실행 역할을 지정합니다.

Fargate 프로필 생성 예시:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

YAML을 사용한 Fargate 프로필 정의:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: my-fargate-profile
    selectors:
      - namespace: my-namespace
        labels:
          app: my-app
      - namespace: another-namespace
```

Fargate 사용 시 고려사항:

* DaemonSet은 Fargate에서 지원되지 않습니다.
* 특권(privileged) 컨테이너는 실행할 수 없습니다.
* HostNetwork, HostPort는 지원되지 않습니다.
* GPU 워크로드는 지원되지 않습니다.
* 포드당 비용이 발생하므로 비용 계획이 필요합니다.
* 스토리지는 임시 스토리지로 제한됩니다(영구 볼륨은 EFS를 통해 가능).

다른 옵션들의 문제점:

* Fargate 프로필은 모든 포드를 자동으로 Fargate에서 실행하지 않으며, 선택기와 일치하는 포드만 Fargate에서 실행됩니다.
* Fargate 프로필은 EC2 인스턴스 유형과 관련이 없으며, Fargate는 서버리스 컨테이너 실행 환경입니다.
* Fargate 프로필은 클러스터 전체의 리소스 할당량을 설정하지 않습니다. 리소스 할당량은 Kubernetes ResourceQuota를 통해 관리됩니다.

</details>

2. Amazon EKS에서 클러스터 업그레이드를 수행할 때 올바른 순서는 무엇인가요?
   * A) 워커 노드 업그레이드 → 컨트롤 플레인 업그레이드 → 애드온 업그레이드
   * B) 컨트롤 플레인 업그레이드 → 워커 노드 업그레이드 → 애드온 업그레이드
   * C) 애드온 업그레이드 → 컨트롤 플레인 업그레이드 → 워커 노드 업그레이드
   * D) 동시에 모든 구성 요소 업그레이드

<details>

<summary>정답 보기</summary>

**정답: B) 컨트롤 플레인 업그레이드 → 워커 노드 업그레이드 → 애드온 업그레이드**

**설명:** Amazon EKS 클러스터 업그레이드의 올바른 순서는 컨트롤 플레인을 먼저 업그레이드한 다음, 워커 노드를 업그레이드하고, 마지막으로 애드온을 업그레이드하는 것입니다. 이 순서는 Kubernetes의 버전 호환성 모델을 따르며, 업그레이드 과정에서 발생할 수 있는 문제를 최소화합니다.

**1. 컨트롤 플레인 업그레이드**

* 컨트롤 플레인은 클러스터의 두뇌 역할을 하므로 먼저 업그레이드해야 합니다.
* Kubernetes는 컨트롤 플레인이 노드보다 최대 2개의 마이너 버전까지 앞설 수 있도록 설계되었습니다.
* 컨트롤 플레인 업그레이드는 AWS 관리 콘솔, AWS CLI 또는 eksctl을 통해 수행할 수 있습니다.

```bash
# AWS CLI를 사용한 컨트롤 플레인 업그레이드
aws eks update-cluster-version --name my-cluster --kubernetes-version 1.28

# eksctl을 사용한 컨트롤 플레인 업그레이드
eksctl upgrade cluster --name=my-cluster --version=1.28 --approve
```

**2. 워커 노드 업그레이드**

* 컨트롤 플레인 업그레이드가 완료된 후, 워커 노드를 업그레이드합니다.
* 관리형 노드 그룹의 경우, AWS 관리 콘솔, AWS CLI 또는 eksctl을 통해 업그레이드할 수 있습니다.
* 자체 관리형 노드의 경우, 새 AMI로 노드를 교체해야 합니다.

```bash
# 관리형 노드 그룹 업그레이드
aws eks update-nodegroup-version --cluster-name my-cluster --nodegroup-name my-nodegroup

# eksctl을 사용한 관리형 노드 그룹 업그레이드
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

**3. 애드온 업그레이드**

* 마지막으로, 클러스터 애드온(kube-proxy, CoreDNS, Amazon VPC CNI 등)을 업그레이드합니다.
* 애드온은 특정 Kubernetes 버전과 호환되도록 설계되었으므로, 컨트롤 플레인과 노드 업그레이드 후 업그레이드해야 합니다.

```bash
# AWS CLI를 사용한 애드온 업그레이드
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni --addon-version v1.12.0-eksbuild.1

# eksctl을 사용한 애드온 업그레이드
eksctl update addon --name vpc-cni --version v1.12.0-eksbuild.1 --cluster my-cluster
```

**업그레이드 모범 사례:**

* 업그레이드 전 클러스터 상태 확인 및 백업
* 테스트 환경에서 먼저 업그레이드 테스트
* 블루/그린 배포 전략 고려
* 업그레이드 중 워크로드 중단 최소화를 위한 PodDisruptionBudget 구성
* 한 번에 한 마이너 버전씩 업그레이드
* 업그레이드 후 워크로드 및 시스템 구성 요소 검증

다른 옵션들의 문제점:

* 워커 노드를 컨트롤 플레인보다 먼저 업그레이드하면 버전 호환성 문제가 발생할 수 있습니다.
* 애드온을 먼저 업그레이드하면 새 버전의 애드온이 이전 버전의 Kubernetes와 호환되지 않을 수 있습니다.
* 모든 구성 요소를 동시에 업그레이드하는 것은 위험하며, 문제 발생 시 원인 파악이 어렵습니다.

</details>

3. Amazon EKS에서 VPC CNI 플러그인의 주요 기능이 아닌 것은 무엇인가요?
   * A) 포드에 VPC IP 주소 할당
   * B) 보안 그룹을 포드 수준에서 적용
   * C) 포드 간 네트워크 트래픽 암호화
   * D) 접두사 위임을 통한 IP 주소 확장

<details>

<summary>정답 보기</summary>

**정답: C) 포드 간 네트워크 트래픽 암호화**

**설명:** Amazon VPC CNI(Container Network Interface) 플러그인은 포드 간 네트워크 트래픽을 자동으로 암호화하지 않습니다. 포드 간 트래픽 암호화는 VPC CNI의 기본 기능이 아니며, 이를 위해서는 서비스 메시(예: AWS App Mesh, Istio)나 네트워크 정책 솔루션(예: Calico, Cilium)과 같은 추가 도구가 필요합니다.

Amazon VPC CNI 플러그인의 실제 주요 기능은 다음과 같습니다:

1. **포드에 VPC IP 주소 할당**:
   * 각 포드는 VPC 내의 고유한 IP 주소를 받습니다.
   * 이를 통해 포드는 VPC 내의 다른 리소스와 직접 통신할 수 있습니다.
   * 포드 IP는 VPC 내에서 라우팅 가능하므로, 복잡한 오버레이 네트워크가 필요하지 않습니다.
2. **보안 그룹을 포드 수준에서 적용**:
   * SecurityGroupsForPods 기능을 통해 개별 포드에 AWS 보안 그룹을 적용할 수 있습니다.
   * 이를 통해 포드 수준에서 세분화된 네트워크 보안 정책을 구현할 수 있습니다.
   *   예시 구성:

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
             - sg-0123456789abcdef0
       ```
3. **접두사 위임을 통한 IP 주소 확장**:
   * 기본적으로 각 노드는 제한된 수의 IP 주소(인스턴스 유형에 따라 다름)를 포드에 할당할 수 있습니다.
   * 접두사 위임 기능을 사용하면 각 노드에 /28 CIDR 블록(16개 IP)을 할당하여 사용 가능한 IP 주소 수를 늘릴 수 있습니다.
   * 이는 고밀도 배포 시나리오에서 IP 주소 부족 문제를 해결합니다.
4. **사용자 지정 네트워킹**:
   * 포드를 특정 서브넷에 배치할 수 있습니다.
   * 다중 네트워크 인터페이스를 사용하여 포드 네트워킹을 구성할 수 있습니다.
5. **호스트 네트워킹 통합**:
   * 포드는 호스트 네트워크 스택을 직접 사용할 수 있습니다.
   * 이는 네트워크 성능이 중요한 워크로드에 유용합니다.

VPC CNI 구성 예시:

```bash
# 접두사 위임 활성화
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# 보안 그룹 포드 기능 활성화
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# 사용자 지정 네트워킹 활성화
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
```

포드 간 네트워크 트래픽 암호화를 구현하려면 다음과 같은 대안을 고려할 수 있습니다:

* AWS App Mesh와 TLS 사용
* Istio 서비스 메시 구현
* Cilium의 투명한 암호화 기능 사용
* 애플리케이션 수준에서 TLS/mTLS 구현

</details>

4. Amazon EKS에서 클러스터 인증을 위한 IAM 역할 기반 접근 제어(RBAC)를 구성하는 올바른 방법은 무엇인가요?
   * A) IAM 사용자에게 직접 Kubernetes RBAC 역할 할당
   * B) aws-auth ConfigMap에 IAM 역할과 Kubernetes 그룹 매핑 구성
   * C) EKS 클러스터에 IAM 정책 직접 연결
   * D) Kubernetes 서비스 계정에 IAM 역할 연결

<details>

<summary>정답 보기</summary>

**정답: B) aws-auth ConfigMap에 IAM 역할과 Kubernetes 그룹 매핑 구성**

**설명:** Amazon EKS에서 클러스터 인증을 위한 IAM 역할 기반 접근 제어(RBAC)를 구성하는 올바른 방법은 `aws-auth` ConfigMap을 사용하여 IAM 역할과 Kubernetes 그룹 간의 매핑을 구성하는 것입니다. 이 방법을 통해 AWS IAM 자격 증명을 Kubernetes RBAC 시스템과 통합할 수 있습니다.

**aws-auth ConfigMap 작동 방식:**

1. EKS는 AWS IAM Authenticator를 사용하여 API 요청을 인증합니다.
2. `aws-auth` ConfigMap은 IAM 엔티티(사용자 또는 역할)를 Kubernetes 사용자 및 그룹에 매핑합니다.
3. Kubernetes RBAC 시스템은 이러한 사용자 및 그룹에 권한을 부여합니다.

**aws-auth ConfigMap 구성 예시:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EksAdminRole
      username: eks-admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-team
      groups:
        - dev-group
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin-user
      username: admin
      groups:
        - system:masters
    - userarn: arn:aws:iam::123456789012:user/read-only-user
      username: read-only
      groups:
        - read-only-group
```

**Kubernetes RBAC 역할 및 바인딩 구성:**

```yaml
# 개발자 역할 생성
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
# 개발자 그룹에 역할 바인딩
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-binding
  namespace: dev
subjects:
- kind: Group
  name: dev-group
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

**eksctl을 사용한 IAM 및 RBAC 구성:**

```bash
# IAM 역할 매핑 추가
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/EksAdminRole \
  --username eks-admin \
  --group system:masters

# IAM 사용자 매핑 추가
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:user/admin-user \
  --username admin \
  --group system:masters
```

**모범 사례:**

* 최소 권한 원칙 적용
* 개인 IAM 사용자보다 IAM 역할 사용 권장
* 네임스페이스별로 권한 분리
* 정기적인 접근 권한 검토
* 클러스터 관리자 권한(system:masters)은 제한적으로 부여

다른 옵션들의 문제점:

* IAM 사용자에게 직접 Kubernetes RBAC 역할을 할당할 수 없습니다. IAM과 Kubernetes는 별개의 시스템이므로 aws-auth ConfigMap을 통한 매핑이 필요합니다.
* EKS 클러스터에 IAM 정책을 직접 연결하는 것은 클러스터 내 RBAC 권한과 관련이 없습니다. IAM 정책은 클러스터 자체에 대한 API 호출 권한을 제어합니다.
* Kubernetes 서비스 계정에 IAM 역할 연결(IRSA)은 포드가 AWS 서비스에 접근하기 위한 것이며, 클러스터 인증 및 권한 부여와는 다른 목적입니다.

</details>

5. Amazon EKS에서 Kubernetes 버전 지원 정책에 대한 올바른 설명은 무엇인가요?
   * A) 모든 Kubernetes 버전이 무기한 지원됨
   * B) 각 Kubernetes 버전은 출시 후 12개월 동안 지원됨
   * C) 최신 버전과 이전 3개 버전만 지원됨
   * D) 각 Kubernetes 버전은 출시 후 14개월 동안 지원됨

<details>

<summary>정답 보기</summary>

**정답: D) 각 Kubernetes 버전은 출시 후 14개월 동안 지원됨**

**설명:** Amazon EKS의 Kubernetes 버전 지원 정책에 따르면, 각 Kubernetes 버전은 EKS에서 출시된 후 14개월 동안 지원됩니다. 이 기간이 지나면 해당 버전은 더 이상 지원되지 않으며, 클러스터를 지원되는 버전으로 업그레이드해야 합니다.

**EKS 버전 지원 정책의 주요 특징:**

1. **14개월 지원 기간**:
   * 각 Kubernetes 버전은 EKS에서 출시된 날짜로부터 14개월 동안 지원됩니다.
   * 지원 종료 날짜는 AWS에서 미리 공지합니다.
2. **표준 지원 일정**:
   * Kubernetes 커뮤니티는 약 4개월마다 새 버전을 출시합니다.
   * EKS는 일반적으로 새 Kubernetes 버전이 출시된 후 2-3개월 내에 해당 버전을 지원합니다.
   * 이로 인해 EKS에서는 보통 3-4개의 Kubernetes 버전이 동시에 지원됩니다.
3. **자동 업그레이드 없음**:
   * AWS는 지원 종료가 다가오더라도 클러스터를 자동으로 업그레이드하지 않습니다.
   * 클러스터 관리자가 명시적으로 업그레이드를 수행해야 합니다.
4. **지원 종료 후 영향**:
   * 지원이 종료된 버전에서 실행 중인 클러스터는 계속 작동하지만, AWS는 더 이상 보안 패치나 버그 수정을 제공하지 않습니다.
   * 지원되지 않는 버전에서는 새 클러스터를 생성할 수 없습니다.
   * AWS 지원을 받을 수 없습니다.

**버전 업그레이드 모범 사례:**

* 정기적인 업그레이드 일정 수립
* 지원 종료 날짜 모니터링
* 테스트 환경에서 먼저 업그레이드 테스트
* 업그레이드 전 클러스터 백업
* 한 번에 한 마이너 버전씩 업그레이드
* 블루/그린 배포 전략 고려

**버전 지원 상태 확인:**

```bash
# 사용 가능한 EKS 버전 확인
aws eks describe-addon-versions | grep kubernetesVersion

# 특정 클러스터의 버전 확인
aws eks describe-cluster --name my-cluster --query "cluster.version"
```

다른 옵션들의 문제점:

* 모든 Kubernetes 버전이 무기한 지원되지는 않습니다. 각 버전은 정해진 기간 동안만 지원됩니다.
* 각 버전은 12개월이 아닌 14개월 동안 지원됩니다.
* "최신 버전과 이전 3개 버전만 지원"이라는 고정된 규칙은 없으며, 지원되는 버전 수는 Kubernetes 커뮤니티의 출시 일정과 EKS의 지원 정책에 따라 달라집니다.

</details>
