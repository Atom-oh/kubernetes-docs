# EKS 소개 퀴즈

> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 Amazon Elastic Kubernetes Service(EKS)의 기본 개념과 특징에 관한 이해도를 테스트합니다. EKS 아키텍처, 구성 요소, 관리 방법, 요금 모델 등의 주제를 다룹니다.

이 문서의 독립적인 API 예제는 `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `EXAMPLE_CONTEXT` 등 표시된 변수를 실제 검토 대상에 맞춰 설정해야 합니다. IRSA 예제의 `APP_POLICY_ARN`은 대상 버킷/접두사에 한정된 사전 검토 정책이며, `EXAMPLE_NAMESPACE`가 존재하고 앱이 IRSA를 지원하는 AWS SDK를 사용해야 합니다. 아래 두 실습의 `EKS_INTRO_*` 변수는 별도로 만든 전용 클러스터를 가리킵니다.

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
* **고가용성**: 리전 컨트롤 플레인은 여러 AZ에 분산됩니다. 워크로드 가용성은 복제본·배치·용량·종속 서비스에 따라 달라집니다.
* **관리형 유지 보수**: AWS가 컨트롤 플레인을 패치합니다. 운영자가 마이너 버전 업그레이드를 계획하며 지원 정책에 따른 자동 업그레이드도 있습니다.
* **AWS 서비스와의 통합**: IAM, VPC, ELB, ECR 등 다양한 AWS 서비스와 원활하게 통합됩니다.
* **표준 Kubernetes**: 표준을 준수하는 API는 이식성을 높이지만 AWS 전용 신원·스토리지·통합에는 별도 이전 작업이 필요합니다.

다른 옵션들의 문제점:

* EKS는 다른 관리형 Kubernetes 서비스보다 반드시 저렴하지는 않습니다. 실제로 컨트롤 플레인에 대한 시간당 요금이 있습니다.
* EKS는 AWS 서비스뿐만 아니라 모든 Kubernetes 호환 애플리케이션 및 서비스를 실행할 수 있습니다.
* 리전 EKS 컨트롤 플레인은 여러 AZ에 분산되며 워커 노드와 앱 복제본 배치는 별도로 구성해야 합니다.

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
* **다중 AZ 배포**: 리전 EKS 컨트롤 플레인 구성 요소는 여러 AZ에 분산됩니다.
* **자동 복구**: AWS는 컨트롤 플레인 구성 요소의 상태를 모니터링하고 장애가 발생한 구성 요소를 자동으로 교체합니다.
* **엔드포인트 접근성**: 퍼블릭·프라이빗 또는 두 접근 방식을 함께 구성합니다. 프라이빗 접근에는 VPC나 연결된 네트워크의 DNS·라우팅이 필요합니다.
* **자동 확장**: Standard 컨트롤 플레인 용량은 자동 조정되며 선택 기능인 Provisioned Control Plane 등급은 명시적으로 지정합니다.

다른 옵션들의 문제점:

* 컨트롤 플레인은 사용자의 VPC 내에 배포되지 않습니다. 대신, 사용자의 VPC와 AWS 관리 VPC 간에 ENI(Elastic Network Interface)를 통한 연결이 설정됩니다.
* 컨트롤 플레인은 단일 가용 영역이 아닌 여러 가용 영역에 배포되어 고가용성을 보장합니다.
* 컨트롤 플레인은 사용자의 EC2 인스턴스가 아닌 AWS 관리 인프라에서 실행됩니다.

</details>

3. EKS 컴퓨팅 관리 방식에 대한 설명 중 틀린 것은 무엇인가요?
   * A) 자체 관리형 EC2 노드
   * B) 관리형 노드 그룹
   * C) Fargate 프로필
   * D) 별도 서버리스 컴퓨팅 서비스인 Bottlerocket

<details>
<summary>정답 보기</summary>

**정답: D) 별도 서버리스 컴퓨팅 서비스인 Bottlerocket**

Bottlerocket은 컨테이너 노드용 운영체제입니다. 독립적인 서버리스 실행 옵션이 아닙니다.

1. **자체 관리형 노드**: 고객이 EC2/Auto Scaling 그룹과 AMI·업데이트·노드 구성을 관리합니다.
2. **관리형 노드 그룹**: AWS가 프로비저닝·교체 과정을 관리하지만, 운영자가 AMI/버전 업데이트를 시작합니다. 노드 그룹 최소·최대 크기만으로 Pod 수요 기반 확장이 활성화되지는 않습니다.
3. **Fargate**: 프로필로 선택된 Pod에 별도 컴퓨팅을 제공합니다. DaemonSet·GPU·EBS 등 지원 제약을 확인합니다.
4. **EKS Auto Mode**: AWS가 노드 프로비저닝·확장·교체를 자동화하는 실제 EKS 기능입니다.
5. **Hybrid Nodes**: 온프레미스/엣지 머신을 AWS 관리형 컨트롤 플레인에 연결합니다.

일반 EC2 노드의 수요 기반 확장은 Cluster Autoscaler나 자체 관리형 Karpenter를 별도로 구성할 수 있습니다.

</details>

4. 일반 EC2 기반 EKS 노드의 기본 CNI는 무엇인가요?
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
* **보안 그룹 통합**: Pod 보안 그룹에는 지원 인스턴스·VPC 리소스 컨트롤러 권한·CNI 설정·SecurityGroupPolicy가 필요합니다.
* **VPC 흐름 로그 가시성**: 포드 트래픽이 VPC 흐름 로그에 표시됩니다.
* **AWS 네트워킹 기능 활용**: VPC 피어링, Transit Gateway, PrivateLink 등의 기능을 포드에 직접 활용할 수 있습니다.

AWS VPC CNI는 오픈 소스 프로젝트이며, GitHub에서 코드를 확인할 수 있습니다: https://github.com/aws/amazon-vpc-cni-k8s

EC2 노드의 대체 CNI는 호환성과 지원 범위를 별도로 검토합니다. Fargate·Auto Mode에서 임의 CNI 교체는 지원되지 않으며, Hybrid Nodes에는 호환되는 온프레미스 CNI가 필요합니다. `hostNetwork` Pod는 노드 네트워크를 공유합니다.

</details>

5. IAM 신원에 EKS Kubernetes API 접근을 부여하는 방법은 무엇인가요?
   * A) ServiceAccount만으로 모든 IAM 사용자를 인증
   * B) IAM 인증과 access entry의 접근 정책 및/또는 Kubernetes RBAC
   * C) EKS IAM 정책이 모든 Kubernetes 리소스 권한을 자동 부여
   * D) Cognito를 모든 클러스터에 자동 연결

<details>
<summary>정답 보기</summary>

**정답: B) IAM 인증과 access entry의 접근 정책 및/또는 Kubernetes RBAC**

IAM 신원의 Kubernetes API 접근과 Pod의 AWS API 접근은 별도 경로입니다.

1. `aws eks get-token`은 IAM 자격증명으로 서명한 인증 토큰을 만듭니다.
2. EKS 인증 경로가 IAM 신원을 확인합니다. 새로운 접근 구성에는 **access entry**를 사용합니다.
3. access entry에 EKS 접근 정책을 연결하거나 Kubernetes 그룹을 지정하고 RoleBinding/ClusterRoleBinding을 구성합니다. RBAC와 EKS authorizer의 허용은 합산되며, 둘 다 허용하지 않으면 요청이 거부됩니다.
4. 기존 `aws-auth` ConfigMap 방식은 폐기 예정(deprecated)입니다. 기존 매핑은 자동으로 모두 이전되지 않으므로 access entry 전환 시 각 신원과 권한을 확인해야 합니다.

IAM 정책은 EKS 서비스 API 호출 권한을 제어합니다. EKS 접근 정책은 Kubernetes 권한 템플릿이며 IAM 정책이 아닙니다. IRSA/Pod Identity는 워크로드의 AWS 권한을 위한 별도 기능입니다. ServiceAccount 토큰이나 구성한 OIDC 제공자도 Kubernetes 인증에 사용할 수 있으므로 IAM만이 유일한 인증 방법이라는 뜻은 아닙니다.

</details>

6. OIDC 연동으로 Kubernetes ServiceAccount에 임시 AWS 자격증명을 부여하는 방식은 무엇인가요?
   * A) EC2 인스턴스 프로필을 사용하여 노드에 IAM 역할 부여
   * B) 장기 AWS 액세스 키를 Pod 환경변수에 직접 포함
   * C) IAM 역할을 Kubernetes 서비스 계정에 연결(IRSA)
   * D) AWS 자격 증명을 Kubernetes Secret으로 저장하여 마운트

<details>

<summary>정답 보기</summary>

**정답: C) IAM 역할을 Kubernetes 서비스 계정에 연결(IRSA)**

IRSA는 클러스터 OIDC 제공자와 ServiceAccount 토큰을 사용해 임시 AWS 자격증명을 얻습니다. 신뢰 정책은 대상 네임스페이스·ServiceAccount 및 `aud=sts.amazonaws.com`으로 제한합니다. EKS Pod Identity도 임시 자격증명을 제공하지만 별도 OIDC 제공자를 사용하지 않으며, 지원되는 컴퓨팅과 에이전트/SDK 구성을 확인해야 합니다. 이 예제는 IRSA 방식을 설명합니다.

IRSA의 주요 이점:

* **최소 권한 원칙**: 각 애플리케이션에 필요한 최소한의 권한만 부여할 수 있습니다.
* **권한 격리**: 같은 노드에서 실행되는 다른 포드는 서로 다른 IAM 권한을 가질 수 있습니다.
* **자격 증명 관리 간소화**: AWS 자격 증명을 직접 관리할 필요가 없습니다.
* **보안 강화**: 자격 증명이 코드나 구성에 하드코딩되지 않습니다.

IRSA 설정 방법:

1.  EKS 클러스터에 OpenID Connect(OIDC) 제공자 연결:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" --approve
    ```
2.  서비스 계정에 대한 IAM 역할 생성:

    ```bash
    eksctl create iamserviceaccount \
      --name=app-sa \
      --namespace="${EXAMPLE_NAMESPACE:?}" \
      --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" \
      --attach-policy-arn="${APP_POLICY_ARN:?Use a reviewed policy scoped to the required bucket/prefix}" \
      --approve
    ```
3.  같은 네임스페이스의 Pod에서 서비스 계정을 참조합니다. 아래는 템플릿입니다. IRSA 호환 SDK를 사용하는 앱 이미지로 바꾸고 `-n "$EXAMPLE_NAMESPACE"`로 적용합니다:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: app-sa
      containers:
      - name: my-container
        image: registry.example.com/team/app:reviewed
    ```

다른 옵션들의 문제점:

* IMDS에 접근 가능한 Pod는 노드 역할의 자격증명을 얻을 수 있습니다. IMDS 접근을 제한하고 워크로드별 역할을 사용합니다. IRSA만으로 IMDS 접근이 차단되지는 않습니다.
* 장기 액세스 키를 Pod 환경변수에 넣으면 노출·회전 위험이 늘어납니다. IRSA/Pod Identity의 자격증명 제공자 설정용 환경변수와는 다른 방식입니다.
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
* **비용 고려**: CloudWatch Logs 수집·보존·쿼리 요금이 발생할 수 있습니다.

로깅 활성화 방법:

```bash
# AWS CLI를 사용한 로깅 활성화
aws eks update-cluster-config \
    --region "${EXAMPLE_REGION:?}" \
    --name "${EXAMPLE_CLUSTER:?}" \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# eksctl을 사용한 로깅 활성화
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
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
   * Standard/extended support의 클러스터 요금은 다르며, 선택한 Provisioned Control Plane 등급에는 추가 요금이 있습니다.
   * EKS 클러스터는 리전 리소스입니다. 여러 리전에는 별도 클러스터와 요금이 필요합니다.
   * Auto Mode, EKS Capabilities, Hybrid Nodes 및 AWS 인프라 요금도 별도로 계산합니다.
2. **워커 노드로 사용되는 EC2 인스턴스 비용**:
   * 자체 관리형 노드 그룹이나 관리형 노드 그룹에서 사용하는 EC2 인스턴스에 대한 비용이 발생합니다.
   * 인스턴스 유형, 크기, 수량, 실행 시간에 따라 비용이 달라집니다.
   * 예약 인스턴스, Savings Plans, 스팟 인스턴스 등을 통해 비용을 최적화할 수 있습니다.
3. **Fargate 포드 실행 비용**:
   * Fargate를 사용하는 경우, 포드에 할당된 vCPU 및 메모리 리소스에 따라 비용이 부과됩니다.
   * Linux Fargate 과금은 이미지 다운로드부터 시작하며 초 단위 올림·최소 1분이 적용됩니다. 요청 리소스도 지원되는 크기로 올림됩니다.
   * 프로비저닝 용량·사용률·운영 부담을 함께 비교합니다. Fargate나 EC2가 항상 더 저렴한 것은 아닙니다.
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

9. Auto Mode를 사용하지 않는 일반 EKS 클러스터에서 선언적으로 ALB/NLB를 관리하는 방식은 무엇인가요?
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

    * 선택한 컨트롤러가 로드 밸런서를 결정합니다. 이 예제는 설치·권한 설정이 완료된 AWS LBC를 `service.k8s.aws/nlb`로 명시합니다. 레거시 통합은 CLB를 생성할 수 있습니다.

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
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
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
    spec:
      ingressClassName: alb
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
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
        service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      selector:
        app: my-app
      ports:
      - port: 80
        targetPort: 8080
    ```

다른 옵션들의 문제점:

* Auto Mode는 `eks.amazonaws.com/nlb` 등 별도 클래스로 관리형 로드 밸런싱을 제공합니다. 클러스터 내 AWS LBC 설치가 필요 없으며 두 구현의 클래스·지원하지 않는 어노테이션을 혼용하지 않습니다.
* 수동으로 EC2 로드 밸런서를 생성하고 구성하는 것은 가능하지만, Kubernetes의 선언적 접근 방식과 일치하지 않으며 관리가 복잡해집니다.
* EKS는 로드 밸런싱을 완벽하게 지원합니다.

</details>

10. Amazon EKS 클러스터에서 스토리지를 관리하는 방법으로 올바르지 않은 것은 무엇인가요?
    * A) EBS CSI 드라이버를 사용하여 EBS 볼륨 프로비저닝
    * B) EFS CSI 드라이버를 사용하여 EFS 파일 시스템 마운트
    * C) Fargate Pod에 EBS 볼륨 마운트
    * D) FSx for Lustre CSI 드라이버를 사용하여 고성능 파일 시스템 연결

<details>

<summary>정답 보기</summary>

**정답: C) Fargate Pod에 EBS 볼륨 마운트**

Fargate에서는 EBS 볼륨을 마운트할 수 없습니다. 일반 EC2 노드는 IAM 권한을 가진 EBS CSI 드라이버를 설치해서 사용합니다. Auto Mode는 일반 `ebs.csi.aws.com`과 다른 `ebs.csi.eks.amazonaws.com`으로 관리형 EBS 프로비저닝을 제공합니다.

Amazon EKS 클러스터에서 스토리지를 관리하는 실제 방법은 다음과 같습니다:

1.  **EBS CSI 드라이버**:

    * Amazon EBS(Elastic Block Store) 볼륨을 Kubernetes 포드에 연결할 수 있습니다.
    * 블록 스토리지가 필요한 애플리케이션(데이터베이스 등)에 적합합니다.
    * 동적 프로비저닝, 스냅샷 컨트롤러를 통한 스냅샷, StorageClass에서 허용한 볼륨 확장을 지원합니다.
    * EBS는 AZ 범위 리소스입니다. ReadWriteOnce는 Pod 하나가 아니라 노드 하나에서의 읽기·쓰기를 뜻하며 같은 노드의 여러 Pod가 사용할 수 있습니다. 접근 모드가 AZ 범위를 정의하는 것은 아닙니다.

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
    ```
   용량은 StorageClass의 `storageCapacity`가 아니라 PVC의 `spec.resources.requests.storage`(예: `1200Gi`)에 지정합니다. 파일 시스템 유형별 최소/증분 용량, 서브넷·보안 그룹·Lustre 클라이언트 및 드라이버 IAM 권한을 별도로 확인합니다.

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

이 해설의 배포 명령은 실행하면 과금되는 AWS 리소스를 생성합니다. 감사에서는 실행하지 않았습니다. Bash, 현재 AWS CLI v2, kubectl 1.36 및 Helm을 준비하고, [공식 eksctl 설치 절차](https://eksctl.io/installation/)에서 OS/CPU 아키텍처와 체크섬을 확인합니다. 아래는 eksctl 0.230.0 스키마와 EKS 1.36을 기준으로 검토한 학습 예제이며 검증된 프로덕션 구성은 아닙니다.

같은 셸에서 순서대로 진행하고 명령 실패 시 중단합니다. `EKS_INTRO_ADMIN_CIDR`에는 승인된 클라이언트의 실제 외부 IPv4 CIDR(보통 `/32`)을 설정합니다. 새 클러스터는 프라이빗 노드·프라이빗 API 접근과 제한된 퍼블릭 API 접근을 사용합니다. 단일 NAT 게이트웨이는 이 개발 실습의 선택이며 프로덕션 가용성 설계를 대신하지 않습니다. 생성자의 관리자 권한도 이 전용 실습 클러스터의 초기 설정을 위한 것입니다.

**1. 전용 클러스터 생성**

```bash
# Use a dedicated nonproduction AWS account/role and an approved region.
eksctl version  # Example tool baseline: 0.230.0
aws --version
kubectl version --client
helm version

EKS_INTRO_DIR=$(mktemp -d /tmp/eks-intro.XXXXXX)
: "${EKS_INTRO_DIR:?}"
EKS_INTRO_CLUSTER=$(basename "$EKS_INTRO_DIR" | tr '[:upper:].' '[:lower:]-')
EKS_INTRO_REGION=us-west-2
: "${EKS_INTRO_ADMIN_CIDR:?Set your approved client egress IPv4 CIDR, normally /32}"
EKS_INTRO_KUBECONFIG="$EKS_INTRO_DIR/kubeconfig"
unset EKS_INTRO_CLUSTER_ARN EKS_INTRO_POLICY_ARN
aws sts get-caller-identity

cat > "$EKS_INTRO_DIR/eks-cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_INTRO_CLUSTER}
  region: ${EKS_INTRO_REGION}
  version: "1.36"
  tags:
    docs-lab: ${EKS_INTRO_CLUSTER}
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: true
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${EKS_INTRO_ADMIN_CIDR}"]
  nat:
    gateway: Single
managedNodeGroups:
- name: ng-1
  amiFamily: AmazonLinux2023
  instanceType: t3.medium
  privateNetworking: true
  disableIMDSv1: true
  disablePodIMDS: true
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

# Inspect the file, account, allowed CIDR and projected costs before provisioning.
cat "$EKS_INTRO_DIR/eks-cluster.yaml"
eksctl create cluster -f "$EKS_INTRO_DIR/eks-cluster.yaml" \
  --kubeconfig "$EKS_INTRO_KUBECONFIG" &&
  EKS_INTRO_CLUSTER_ARN=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
    --region "$EKS_INTRO_REGION" --query cluster.arn --output text)
: "${EKS_INTRO_CLUSTER_ARN:?Cluster creation/verification did not complete}"
```

클러스터 생성에 실패하면 이름을 재사용하지 말고 해당 이름의 CloudFormation 스택과 생성된 리소스를 확인해 정리합니다. `minSize`/`maxSize`는 범위일 뿐 수요 기반 노드 오토스케일러를 설치하지 않습니다. t3.medium은 예시이며 실제 용량·CPU 크레딧·지역 가격을 평가해야 합니다.

**2. 별도 kubeconfig와 연결 확인**

```bash
aws eks update-kubeconfig --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --kubeconfig "${EKS_INTRO_KUBECONFIG:?}"
intro_kubectl() {
  kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" "$@"
}
intro_kubectl get nodes
intro_kubectl cluster-info
```

**3. 기본 메트릭 구성**

Metrics Server 0.9.x는 Kubernetes 1.34 이상을 지원합니다. 리소스 메트릭용 구성으로, 로그·장기 모니터링을 대신하지 않습니다. kubelet 인증서와 네트워크 도달성을 검증하고 TLS 검증을 끄지 않습니다.

```bash
intro_kubectl get pods -n kube-system

# Fresh lab cluster only: do not overwrite an existing managed installation.
curl -fL https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml \
  -o "${EKS_INTRO_DIR:?}/metrics-server.yaml" &&
  intro_kubectl apply -f "$EKS_INTRO_DIR/metrics-server.yaml"
intro_kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s
intro_kubectl top nodes
```

**4. AWS Load Balancer Controller 설치**

정책·컨트롤러·차트는 3.5.0에 맞췄습니다. 노드 역할에 여러 애드온의 권한을 몰아주지 않고 IRSA 역할을 사용합니다. 명시한 리전/VPC ID로 IMDS 자동 탐색에 의존하지 않습니다. 서브넷 태그·보안 그룹·서비스 할당량은 별도로 확인합니다.

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use the new lab cluster}"
curl -fL https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json \
  -o "${EKS_INTRO_DIR:?}/lbc-policy.json" || exit 1
# Inspect the pinned policy before creating this lab-owned IAM policy.
EKS_INTRO_POLICY_ARN=$(aws iam create-policy \
  --policy-name "${EKS_INTRO_CLUSTER:?}-lbc" \
  --policy-document "file://$EKS_INTRO_DIR/lbc-policy.json" \
  --query Policy.Arn --output text)
: "${EKS_INTRO_POLICY_ARN:?Policy creation failed}"

# iam.withOIDC created the cluster OIDC provider in step1.
eksctl create iamserviceaccount \
  --cluster="$EKS_INTRO_CLUSTER" --region="${EKS_INTRO_REGION:?}" \
  --namespace=kube-system --name=aws-load-balancer-controller \
  --attach-policy-arn="$EKS_INTRO_POLICY_ARN" --approve

EKS_INTRO_VPC_ID=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query cluster.resourcesVpcConfig.vpcId --output text)
: "${EKS_INTRO_VPC_ID:?}"
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" install aws-load-balancer-controller \
  eks/aws-load-balancer-controller --version 3.5.0 -n kube-system \
  --set clusterName="$EKS_INTRO_CLUSTER" \
  --set region="$EKS_INTRO_REGION" --set vpcId="$EKS_INTRO_VPC_ID" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait --timeout 5m
```

**5. 클러스터 상태 확인**

```bash
intro_kubectl get nodes -o wide
intro_kubectl get pods -n kube-system
intro_kubectl get events --sort-by='.lastTimestamp'
intro_kubectl cluster-info
```

**6. 로컬 포트 포워딩으로 기본 앱 확인**

```bash
intro_kubectl create namespace intro-smoke
intro_kubectl -n intro-smoke create deployment nginx --image=nginx:1.30.4-alpine
intro_kubectl -n intro-smoke rollout status deployment/nginx --timeout=180s
intro_kubectl -n intro-smoke expose deployment nginx --port=80 --type=ClusterIP
intro_kubectl -n intro-smoke get deployment,service
# Run in a separate terminal using the same dedicated kubeconfig.
kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" -n intro-smoke \
  port-forward --address 127.0.0.1 service/nginx 8080:80
```

포트 포워딩이 실행 중일 때 `http://127.0.0.1:8080`에 접속하고 Ctrl-C로 종료합니다. 외부 ALB 노출은 다음 실습에서 구성합니다. 두 실습을 마친 뒤 아래 정리 절차를 실행하며, 예상 출력이나 비용 절감을 실측 결과로 간주하지 않습니다.

</details>

### 실습 2: EKS 클러스터에서 애플리케이션 배포 및 서비스 노출

**시나리오:** 당신의 팀은 마이크로서비스 아키텍처를 기반으로 한 웹 애플리케이션을 개발했습니다. 이 애플리케이션을 EKS 클러스터에 배포하고, 외부에서 접근할 수 있도록 구성해야 합니다.

**요구사항:**

1. 프론트엔드와 백엔드 서비스 배포
2. 서비스 간 통신 구성
3. 인그레스 컨트롤러를 통한 외부 접근 구성
4. 기본적인 스케일링 설정

**해결 방법:**

<details>
<summary>해결 방법 보기</summary>

실습 1의 전용 클러스터, 같은 셸 변수와 AWS LBC/IngressClass `alb`, 정상 Metrics Server가 필요합니다. 이 HTTP 예제에는 공개 더미 응답만 넣고 ALB 접근을 지정한 클라이언트 CIDR로 제한합니다. 실제 인증·TLS·프로덕션 부하 검증은 포함하지 않습니다.

**1. 네임스페이스 생성**

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Complete exercise1 first}"
unset EKS_INTRO_WEB_UID
EKS_INTRO_WEB_UID=$(intro_kubectl create namespace web-app -o jsonpath='{.metadata.uid}')
: "${EKS_INTRO_WEB_UID:?Stop if this namespace already exists}"
```

**2. 백엔드 구성**

NGINX가 실제로 80번 포트를 듣고 `/api`를 포함한 경로에 더미 JSON을 반환하도록 구성합니다.

```bash
cat > "${EKS_INTRO_DIR:?}/backend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location / {
            default_type application/json;
            return 200 '{"service":"backend","example":true}\n';
        }
    }
---
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
      automountServiceAccountToken: false
      containers:
      - name: backend
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: backend-config
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
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/backend-deployment.yaml"
```

**3. 프론트엔드와 서비스 간 통신 구성**

일반 NGINX 이미지는 `BACKEND_URL` 환경변수를 사용하지 않습니다. 아래 NGINX 설정의 `/proxy-api/`가 `backend-service`로 프록시하여 실제 서비스 간 통신 경로를 만듭니다.

```bash
cat > "${EKS_INTRO_DIR:?}/frontend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location /proxy-api/ {
            proxy_pass http://backend-service/;
        }
        location / {
            default_type text/plain;
            return 200 'frontend demo\n';
        }
    }
---
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
      automountServiceAccountToken: false
      containers:
      - name: frontend
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: frontend-config
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
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/frontend-deployment.yaml"
```

**4. AWS LBC용 Ingress 생성**

ALB는 `/api` 접두사를 자동 제거하지 않습니다. 여기서는 백엔드가 해당 경로를 직접 처리합니다. `/`와 `/proxy-api/`는 프론트엔드로 전달됩니다.

```bash
cat > "${EKS_INTRO_DIR:?}/ingress.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
    alb.ingress.kubernetes.io/inbound-cidrs: ${EKS_INTRO_ADMIN_CIDR:?}
spec:
  ingressClassName: alb
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
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/ingress.yaml"
```

**5. HPA 구성**

CPU 요청 대비 사용률을 기준으로 Pod 수를 조정합니다. HPA는 노드를 생성하지 않으며 Metrics Server·여유 노드 용량이 필요합니다.

```bash
cat > "${EKS_INTRO_DIR:?}/hpa.yaml" << 'EOF'
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
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/hpa.yaml"
```

**6. 라우팅과 상태 확인**

ALB 주소가 생기는 것과 타깃이 정상인 것은 별개입니다. 응답이 실패하면 이벤트·타깃 상태·보안 그룹과 클라이언트 CIDR부터 확인합니다.

```bash
intro_kubectl -n web-app rollout status deployment/backend --timeout=180s
intro_kubectl -n web-app rollout status deployment/frontend --timeout=180s
intro_kubectl -n web-app get deployments,services,ingress,hpa
intro_kubectl -n web-app describe ingress web-app-ingress
ALB_ADDRESS=$(intro_kubectl -n web-app get ingress web-app-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
: "${ALB_ADDRESS:?Wait for ALB provisioning and inspect events}"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/api"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/proxy-api/"
```

**7. 제한된 부하 관찰**

이 부하는 예제이며 CPU 목표치를 넘거나 HPA가 확장한다는 보장은 없습니다. 정적 NGINX 응답은 CPU를 적게 사용할 수 있고, 프론트엔드 요청만 보내면 백엔드 부하는 늘지 않습니다. 실제 확장 여부는 메트릭·HPA 상태·Pending Pod와 함께 관찰합니다.

```bash
# Only target the lab ALB whose ownership and health you checked above.
: "${ALB_ADDRESS:?}"
ab -n 1000 -c 10 -s 10 "http://$ALB_ADDRESS/"
intro_kubectl -n web-app get hpa
intro_kubectl -n web-app top pods
intro_kubectl -n web-app get events --sort-by='.lastTimestamp'
# Optional observation; Ctrl-C stops watching, not the HPA.
intro_kubectl -n web-app get hpa -w
```

</details>

### 실습 리소스 정리

원래 실습에만 사용한 클러스터인지 계정·ARN·태그로 확인합니다. 앱 로드 밸런서를 컨트롤러보다 먼저 삭제하며 최종 처리가 끝날 때까지 기다립니다. 타임아웃이 나면 finalizer를 제거하지 말고 컨트롤러 오류를 조사합니다.

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use only the dedicated cluster created in exercise1}"
EKS_INTRO_CLEANUP_READY=false
current_arn=$(aws eks describe-cluster --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --query cluster.arn --output text)
current_tag=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query 'cluster.tags."docs-lab"' --output text)
if [[ "$current_arn" = "$EKS_INTRO_CLUSTER_ARN" && "$current_tag" = "$EKS_INTRO_CLUSTER" ]]; then
  # Keep the controller running until it removes ALB resources/finalizers.
  intro_kubectl -n web-app delete ingress web-app-ingress --ignore-not-found --wait=true --timeout=180s &&
    intro_kubectl delete namespace web-app intro-smoke --ignore-not-found --wait=true --timeout=180s &&
    EKS_INTRO_CLEANUP_READY=true
else
  printf 'Ownership check failed; stop cleanup and inspect the selected account/cluster\n' >&2
fi
```

소유권 확인과 Ingress/네임스페이스 삭제가 성공했을 때만 다음 단계로 진행합니다. IAM 역할 스택 삭제 완료와 정책 연결 해제를 확인한 뒤 정책을 삭제합니다.

```bash
if [[ ${EKS_INTRO_CLEANUP_READY:-false} = true ]]; then
  helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" uninstall aws-load-balancer-controller -n kube-system
  eksctl delete iamserviceaccount --cluster="${EKS_INTRO_CLUSTER:?}" \
    --region="${EKS_INTRO_REGION:?}" --namespace=kube-system --name=aws-load-balancer-controller --approve --wait
  # Wait for the related IAM-role stack deletion to finish before deleting its policy.
  aws iam list-entities-for-policy --policy-arn "${EKS_INTRO_POLICY_ARN:?}"
  # Continue only when no attachment remains.
  aws iam delete-policy --policy-arn "$EKS_INTRO_POLICY_ARN" &&
    eksctl delete cluster --config-file="${EKS_INTRO_DIR:?}/eks-cluster.yaml" --wait
else
  printf 'Complete ownership and load balancer cleanup checks first\n' >&2
fi
```

CloudFormation의 삭제 완료, 잔여 로드 밸런서·보안 그룹·NAT·EBS 및 로그 보존 비용을 확인합니다. CloudWatch 로그 그룹은 별도 보존/삭제 결정을 내립니다. 클러스터 생성이 중간에 실패했거나 아래 단계에서 사용하지 않은 리소스라면 자동으로 정리됐다고 가정하지 않습니다. 실습을 모두 마친 뒤 전용 디렉터리의 매니페스트·정책·kubeconfig도 삭제합니다.

## 고급 주제

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
* **IAM 역할**: Pod 실행 역할은 이미지 가져오기 등 Fargate 인프라가 사용합니다. 앱 컨테이너의 AWS API 접근에는 별도의 IRSA 역할이 필요합니다.

Fargate 프로필 생성 예시:

```bash
eksctl create fargateprofile \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
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
* 정적으로 프로비저닝한 EFS 볼륨으로 영구 저장소를 사용할 수 있습니다. Fargate는 EBS 마운트와 EFS 동적 프로비저닝을 지원하지 않습니다.

다른 옵션들의 문제점:

* Fargate 프로필은 모든 포드를 자동으로 Fargate에서 실행하지 않으며, 선택기와 일치하는 포드만 Fargate에서 실행됩니다.
* Fargate 프로필은 EC2 인스턴스 유형과 관련이 없으며, Fargate는 서버리스 컨테이너 실행 환경입니다.
* Fargate 프로필은 클러스터 전체의 리소스 할당량을 설정하지 않습니다. 리소스 할당량은 Kubernetes ResourceQuota를 통해 관리됩니다.

</details>

2. EKS 업그레이드를 계획하는 올바른 방법은 무엇인가요?
   * A) 노드를 대상 버전으로 먼저 올리고 호환성은 나중에 확인
   * B) 호환성/현재 버전을 정리한 뒤 컨트롤 플레인 → 노드, 각 애드온의 호환성에 맞춰 갱신
   * C) 모든 애드온을 무조건 최신으로 올리면 준비 완료
   * D) 모든 구성 요소를 동시에 변경

<details>
<summary>정답 보기</summary>

**정답: B) 호환성/현재 버전을 정리한 뒤 컨트롤 플레인 → 노드, 각 애드온의 호환성에 맞춰 갱신**

먼저 현재 클러스터·노드 버전, 업그레이드 인사이트, 제거 API, 웹훅·CRD·애드온 호환성, 서브넷 IP 여유와 복구 계획을 확인합니다. 노드가 뒤처져 있다면 현재 컨트롤 플레인 버전에 맞춘 뒤 다음 마이너 버전으로 진행합니다.

**1. 컨트롤 플레인**

다음 마이너 버전으로 한 단계씩 업데이트합니다. 현재 kubelet은 API 서버보다 새 버전일 수 없으며 최대 3개 마이너 버전까지 오래될 수 있지만, EKS는 업그레이드 전후 버전을 맞추는 것을 권장합니다. 허용되는 skew를 상시 운영 목표로 삼지 않습니다.

```bash
# Inspect the current version and node versions before choosing the next minor.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status}' --output table
kubectl --context "${EXAMPLE_CONTEXT:?}" get nodes

# Choose one interface, after prerequisite checks and workload testing.
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?Select the next supported minor}"
# Alternative:
# eksctl upgrade cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --version "$NEXT_MINOR_VERSION" --approve

# Use the update ID returned above. Proceed only after status is Successful.
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "${CONTROL_PLANE_UPDATE_ID:?}" --query update.status
```

**2. 노드**

컨트롤 플레인 업데이트 완료 후 관리형 노드 그룹의 업데이트를 시작하고 해당 업데이트 상태와 노드 Ready·kubelet 버전을 확인합니다. 일반 노드 그룹은 컨트롤 플레인과 함께 자동 갱신되지 않습니다. 자체 관리형/Hybrid Nodes는 운영자가 업데이트하고, Fargate Pod는 재생성해야 새 버전을 사용합니다. Auto Mode 노드는 AWS가 점진적으로 갱신합니다.

```bash
aws eks update-nodegroup-version --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
# Alternative:
# eksctl upgrade nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --name "$EXAMPLE_NODEGROUP" --kubernetes-version "$NEXT_MINOR_VERSION"
```

**3. 애드온과 클라이언트**

기존 버전과 대상 버전 양쪽에서 필요한 호환성을 미리 확인합니다. 일부 CNI·웹훅·컨트롤러는 컨트롤 플레인보다 먼저 호환 버전으로 갱신해야 하므로 “애드온은 항상 마지막”이라는 규칙은 없습니다. 제어면 업그레이드 후 나머지 애드온·Cluster Autoscaler·kubectl 등을 지원 버전에 맞추고 각각 검증합니다.

```bash
aws eks describe-addon-versions --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}" \
  --query 'addons[].addonVersions[].addonVersion' --output table

# Select a compatible EKS add-on build after reviewing configuration changes.
aws eks update-addon --cluster-name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_ADDON_VERSION:?}" \
  --resolve-conflicts PRESERVE
```

`PRESERVE`는 기존 사용자 설정을 보존하기 위한 옵션이지 호환성 보장이 아닙니다. PDB, 여유 용량, graceful termination을 확인하고 강제 옵션으로 실패를 숨기지 않습니다. 단계마다 상태를 검증하며 복구 가능한 애플리케이션/데이터 백업을 준비합니다. AWS의 제어면 백업이 고객용 데이터 복구 계획을 대신하지는 않습니다.

현재 EKS는 조건을 충족한 업그레이드에 대해 완료 후 7일 이내 이전 마이너 버전으로의 롤백을 지원합니다. 노드·애드온·API 변경·지원 정책 제약을 확인해야 하며 앱 데이터가 자동 복구되는 것은 아닙니다. [업그레이드 절차](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)와 [롤백 조건](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)을 따릅니다.

</details>

3. Amazon EKS에서 VPC CNI 플러그인의 주요 기능이 아닌 것은 무엇인가요?
   * A) 포드에 VPC IP 주소 할당
   * B) 보안 그룹을 포드 수준에서 적용
   * C) 포드 간 네트워크 트래픽 암호화
   * D) 접두사 위임을 통한 IP 주소 확장

<details>

<summary>정답 보기</summary>

**정답: C) 포드 간 네트워크 트래픽 암호화**

Amazon VPC CNI가 모든 Pod 간 트래픽을 암호화하는 것은 아닙니다. 애플리케이션 TLS/mTLS 또는 지원되는 메시/CNI 암호화 기능을 명시적으로 구성해야 합니다. NetworkPolicy만으로는 트래픽을 필터링할 뿐 암호화하지 않습니다.

Amazon VPC CNI 플러그인의 실제 주요 기능은 다음과 같습니다:

1. **포드에 VPC IP 주소 할당**:
   * 일반 Pod는 VPC IP를 받으며 `hostNetwork` Pod는 노드 네트워크를 공유합니다.
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
   * ENI당 주소 수용량을 늘리지만 기존 서브넷 주소를 소비합니다. 연속된 여유 prefix가 필요하며 서브넷 용량 자체가 늘어나는 것은 아닙니다.
4. **사용자 지정 네트워킹**:
   * 포드를 특정 서브넷에 배치할 수 있습니다.
   * 다중 네트워크 인터페이스를 사용하여 포드 네트워킹을 구성할 수 있습니다.
5. **Kubernetes 호스트 네트워킹**:
   * `hostNetwork`는 Kubernetes Pod 설정으로 노드 네트워크를 사용하며 CNI 암호화·격리 기능이 아닙니다.
   * 이는 네트워크 성능이 중요한 워크로드에 유용합니다.

VPC CNI 기능은 선행 조건을 확인한 뒤 개별적으로 적용합니다.

| 설정 | 필요한 확인 |
| --- | --- |
| `ENABLE_PREFIX_DELEGATION` | 지원 인스턴스/CNI 버전, 연속된 `/28` 여유 블록, kubelet max-pods 및 신규 노드 전환 계획 |
| `ENABLE_POD_ENI` | 지원 trunk/branch ENI 인스턴스, VPC 리소스 컨트롤러 권한, SecurityGroupPolicy 및 DNS·보안 그룹 규칙 |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | IPv4, 동일 VPC/AZ의 Pod 서브넷·보안 그룹, 노드별 ENIConfig 연결 및 여유 IP |

설정 하나만 켜면 기존 Pod와 신규 Pod의 네트워크가 다르게 동작하거나 IP 할당이 실패할 수 있습니다. EKS 애드온 관리 설정과 충돌하지 않게 공식 전환 절차를 따릅니다. Auto Mode/Fargate/Hybrid Nodes에 아래 일반 EC2 DaemonSet 경로를 그대로 적용하지 않습니다.

```bash
# Inspect current non-secret CNI flags; this does not enable any feature.
kubectl --context "${EXAMPLE_CONTEXT:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="aws-node")].env}{"\n"}'
```


포드 간 네트워크 트래픽 암호화를 구현하려면 다음과 같은 대안을 고려할 수 있습니다:

* 기존 App Mesh 사용자는 2026년 9월 30일 지원 종료 전에 마이그레이션을 계획합니다.
* Istio 서비스 메시 구현
* Cilium의 투명한 암호화 기능 사용
* 애플리케이션 수준에서 TLS/mTLS 구현

</details>

4. 개발자 IAM 역할에 네임스페이스별 Kubernetes 조회 권한을 부여하는 방법은 무엇인가요?
   * A) IAM 사용자에게 Kubernetes Role을 직접 연결
   * B) EKS access entry로 IAM 역할을 Kubernetes 그룹에 연결하고 RBAC 바인딩 구성
   * C) 클러스터 IAM 역할에 S3 정책만 연결
   * D) 앱 ServiceAccount의 IRSA 설정만으로 개발자에게 kubectl 권한 부여

<details>
<summary>정답 보기</summary>

**정답: B) EKS access entry로 IAM 역할을 Kubernetes 그룹에 연결하고 RBAC 바인딩 구성**

신규 IAM 접근은 **EKS access entry**로 구성합니다. 클러스터 인증 모드가 `API` 또는 `API_AND_CONFIG_MAP`이어야 합니다. 기존 클러스터의 모드 전환은 매핑 이전과 관리자 복구 경로를 먼저 준비하고 수행합니다. `aws-auth`는 deprecated이며 유일한 매핑 방식이 아닙니다.

아래 예제는 이미 존재하는 개발자 IAM 역할을 `dev-readers` 그룹에 연결합니다. IAM 신원과 EKS access entry만으로 Kubernetes RBAC 객체가 자동 생성되지는 않습니다.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.accessConfig.authenticationMode

aws eks create-access-entry --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --principal-arn "${DEV_ROLE_ARN:?Existing developer IAM role}" \
  --type STANDARD --kubernetes-groups dev-readers
```

기존 `dev` 네임스페이스에서 관리자가 다음 Role과 RoleBinding을 적용합니다. 이 예제는 Pod·Deployment 조회만 허용하며 Secret이나 변경 권한을 부여하지 않습니다. 워크로드 생성 권한은 해당 네임스페이스의 Secret 사용으로 이어질 수 있으므로 별도로 검토합니다.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: dev-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-readers
  namespace: dev
subjects:
- kind: Group
  name: dev-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: dev-reader
  apiGroup: rbac.authorization.k8s.io
```

역할을 AssumeRole할 수 있는 신원으로 별도 kubeconfig를 만들고 실제 권한을 검증합니다. 첫 조회는 허용, 두 번째 조회는 거부가 예상되지만 다른 RBAC/EKS 접근 정책의 추가 허용이 있으면 결과가 달라집니다.

```bash
aws eks update-kubeconfig --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --role-arn "${DEV_ROLE_ARN:?}" --kubeconfig "${DEV_KUBECONFIG:?Use a dedicated file}"
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get pods -n dev
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get secrets -n dev
```

대안으로 access entry에 네임스페이스 범위 EKS 접근 정책을 연결할 수 있습니다. 접근 정책과 RBAC 권한은 합산되며 IAM 정책만 연결해서 Kubernetes 권한을 부여할 수는 없습니다. IRSA/Pod Identity는 Pod가 AWS API를 호출하는 별도 경로입니다. 일반 개발자에게 `system:masters`를 부여하거나 전체 `aws-auth`를 덮어쓰지 않습니다.

</details>

5. EKS 버전 지원 정책에 대한 올바른 설명은 무엇인가요?
   * A) 모든 버전을 무기한 지원
   * B) 전체 지원이 12개월에 종료
   * C) 항상 최신 버전과 이전 3개만 지원
   * D) EKS 출시 후 표준 14개월 + 유료 연장 12개월

<details>
<summary>정답 보기</summary>

**정답: D) EKS 출시 후 표준 14개월 + 유료 연장 12개월**

EKS 마이너 버전은 **EKS 출시일**부터 표준 지원 14개월, 이어서 추가 요금의 연장 지원 12개월을 제공합니다. 업스트림 출시일을 기준으로 계산하지 않습니다.

* 2026년 9월 11일 공식 목록: 표준 지원 **1.34–1.36**, 연장 지원 **1.31–1.33**. 업스트림 1.37 출시가 EKS 지원을 뜻하지는 않습니다.
* 연장 지원이 기본 활성화됩니다. `STANDARD` 업그레이드 정책으로 연장 지원을 끄면 표준 지원 종료 후 자동 업그레이드 대상이 됩니다.
* 연장 지원 종료 후에는 AWS가 컨트롤 플레인을 지원되는 버전으로 자동 업그레이드합니다. 구체적인 실행 시간을 보장하지 않으므로 운영자가 사전에 업그레이드를 계획해야 합니다.
* 관리형/자체 관리형/Hybrid 노드는 자동 제어면 업그레이드만으로 갱신되지 않습니다. Fargate Pod 재생성과 애드온 갱신도 별도로 계획하며 Auto Mode 노드는 관리형 갱신 경로를 따릅니다.
* 지원 기간에는 보안 패치를 제공하지만 “모든 버전 무기한 유지”는 지원하지 않습니다. 지원 종료 버전으로 새 클러스터를 만들 수 없습니다.

릴리스 캘린더와 실제 리전의 버전 정보를 확인합니다. 애드온 목록을 grep한 결과는 클러스터 버전 지원 목록을 대신하지 못합니다.

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,upgradePolicy:upgradePolicy}' --output json
```

정기적인 일정, 제거 API/호환성 검토, 테스트 환경 검증, 애플리케이션·데이터 복구 계획을 준비하고 한 번에 한 마이너 버전씩 진행합니다. EKS는 최소 3개 표준 지원 버전을 제공하지만 “항상 최신+이전 3개만”이라는 고정 규칙은 아닙니다.

</details>


## 공식 자료와 검증 범위

- [EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Pod Identity and IRSA](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)
- [Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Auto Mode load balancing](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [FSx CSI configuration and PVC capacity](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)
- [Fargate limitations](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Prefix delegation](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [Custom networking](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [Fargate pricing](https://aws.amazon.com/fargate/pricing/)
- [eksctl 0.230.0 schema](https://github.com/eksctl-io/eksctl/blob/v0.230.0/pkg/apis/eksctl.io/v1alpha5/assets/schema.json)
- [LBC 3.5.0 installation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/installation.md)
- [Metrics Server 0.9.0 compatibility](https://github.com/kubernetes-sigs/metrics-server/blob/v0.9.0/README.md)

공식 문서·릴리스 스키마에 대한 정적 검토입니다. 클러스터·IAM·로드 밸런서 생성, 앱 배포, 업그레이드·롤백, NGINX 실행, 부하 테스트나 비용 측정은 수행하지 않았습니다. 예제의 예상 동작은 실측 결과가 아닙니다.
