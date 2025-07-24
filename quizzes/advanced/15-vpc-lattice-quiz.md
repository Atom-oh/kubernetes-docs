# VPC Lattice 퀴즈

이 퀴즈는 AWS VPC Lattice의 개념, 기능 및 Kubernetes와의 통합에 대한 이해를 테스트합니다.

### 1. AWS VPC Lattice는 무엇인가요?

A. VPC 간 네트워크 연결을 위한 서비스  
B. 서비스 간 통신을 위한 완전 관리형 애플리케이션 네트워킹 서비스  
C. 컨테이너 오케스트레이션을 위한 AWS 서비스  
D. VPC 내 서브넷 관리를 위한 도구  

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 간 통신을 위한 완전 관리형 애플리케이션 네트워킹 서비스**

**설명:**
AWS VPC Lattice는 서비스 간 통신을 위한 완전 관리형 애플리케이션 네트워킹 서비스입니다. 이 서비스는 개발자와 네트워크 관리자가 서비스를 연결, 보호 및 모니터링할 수 있는 일관된 방법을 제공합니다. VPC Lattice를 사용하면 여러 계정과 VPC에 걸쳐 있는 서비스를 쉽게 연결하고 관리할 수 있습니다.

**VPC Lattice의 주요 특징:**

1. **서비스 네트워크**: 
   - 여러 계정과 VPC에 걸쳐 서비스를 연결하는 논리적 경계를 제공합니다.
   - 서비스 네트워크 내에서 서비스 검색 및 통신이 가능합니다.

2. **서비스 관리**: 
   - 서비스를 생성, 등록 및 관리할 수 있습니다.
   - 각 서비스는 고유한 DNS 이름을 가집니다.

3. **트래픽 관리**: 
   - 라우팅 규칙, 가중치 기반 라우팅, 경로 기반 라우팅을 지원합니다.
   - 블루/그린 배포, 카나리 배포 등의 고급 배포 전략을 구현할 수 있습니다.

4. **보안**: 
   - IAM 정책을 통한 액세스 제어를 제공합니다.
   - TLS 암호화를 통한 서비스 간 통신을 지원합니다.

5. **모니터링 및 관찰성**: 
   - Amazon CloudWatch와 통합되어 메트릭, 로그 및 추적을 제공합니다.
   - 서비스 간 통신에 대한 가시성을 제공합니다.

**VPC Lattice vs 다른 AWS 서비스:**

1. **VPC Lattice vs AWS App Mesh**:
   - **VPC Lattice**: 서비스 간 통신을 위한 네트워크 계층 서비스로, 여러 계정과 VPC에 걸쳐 작동합니다.
   - **AWS App Mesh**: 마이크로서비스를 위한 서비스 메시로, 주로 ECS 및 EKS 내에서 작동합니다.

2. **VPC Lattice vs AWS Transit Gateway**:
   - **VPC Lattice**: 애플리케이션 계층(L7)에서 서비스 간 통신에 중점을 둡니다.
   - **Transit Gateway**: 네트워크 계층(L3)에서 VPC 간 연결에 중점을 둡니다.

3. **VPC Lattice vs AWS PrivateLink**:
   - **VPC Lattice**: 서비스 검색, 라우팅 및 로드 밸런싱을 포함한 종합적인 서비스 네트워킹 솔루션입니다.
   - **PrivateLink**: VPC 간 또는 AWS 서비스에 대한 프라이빗 연결에 중점을 둡니다.

**VPC Lattice 아키텍처:**

```
+------------------+     +------------------+     +------------------+
|      VPC A       |     |   VPC Lattice    |     |      VPC B       |
|                  |     |                  |     |                  |
|  +------------+  |     |  +------------+  |     |  +------------+  |
|  | Service A  |<------>|  | Service    |<------>|  | Service B  |  |
|  +------------+  |     |  | Network    |  |     |  +------------+  |
|                  |     |  +------------+  |     |                  |
+------------------+     +------------------+     +------------------+
```

**VPC Lattice 사용 사례:**

1. **마이크로서비스 아키텍처**: 
   - 여러 마이크로서비스 간의 통신을 관리합니다.
   - 서비스 검색 및 로드 밸런싱을 제공합니다.

2. **멀티 계정 환경**: 
   - 여러 AWS 계정에 걸쳐 있는 서비스를 연결합니다.
   - 중앙 집중식 관리 및 거버넌스를 제공합니다.

3. **하이브리드 워크로드**: 
   - 컨테이너, 서버리스 및 EC2 기반 워크로드를 연결합니다.
   - 일관된 네트워킹 경험을 제공합니다.

4. **점진적 마이그레이션**: 
   - 모놀리식 애플리케이션에서 마이크로서비스로의 점진적 마이그레이션을 지원합니다.
   - 새로운 서비스와 레거시 서비스 간의 통신을 관리합니다.

**다른 옵션들의 문제점:**
- A. VPC 간 네트워크 연결을 위한 서비스: 이는 AWS Transit Gateway의 설명에 가깝습니다.
- C. 컨테이너 오케스트레이션을 위한 AWS 서비스: 이는 Amazon ECS 또는 EKS의 설명입니다.
- D. VPC 내 서브넷 관리를 위한 도구: VPC Lattice는 서브넷 관리가 아닌 서비스 네트워킹에 중점을 둡니다.
</details>

### 2. VPC Lattice의 주요 구성 요소가 아닌 것은 무엇인가요?

A. 서비스 네트워크(Service Network)  
B. 서비스(Service)  
C. 대상 그룹(Target Group)  
D. 서비스 메시(Service Mesh)  

<details>
<summary>정답 및 설명</summary>

**정답: D. 서비스 메시(Service Mesh)**

**설명:**
VPC Lattice의 주요 구성 요소가 아닌 것은 서비스 메시(Service Mesh)입니다. 서비스 메시는 AWS App Mesh와 같은 다른 서비스의 구성 요소입니다. VPC Lattice의 주요 구성 요소는 서비스 네트워크(Service Network), 서비스(Service), 대상 그룹(Target Group), 리스너(Listener), 그리고 라우팅 규칙(Routing Rule)입니다.

**VPC Lattice의 주요 구성 요소:**

1. **서비스 네트워크(Service Network)**:
   - 서비스 간 통신을 위한 논리적 경계를 제공합니다.
   - 여러 계정과 VPC에 걸쳐 서비스를 연결합니다.
   - 서비스 네트워크에 연결된 VPC의 리소스는 네트워크 내의 서비스에 액세스할 수 있습니다.

2. **서비스(Service)**:
   - 애플리케이션 또는 마이크로서비스를 나타냅니다.
   - 고유한 DNS 이름을 가지며, 클라이언트는 이 이름을 사용하여 서비스에 액세스합니다.
   - 리스너와 라우팅 규칙을 포함합니다.

3. **대상 그룹(Target Group)**:
   - 요청을 처리할 대상(EC2 인스턴스, IP 주소, Lambda 함수 등)을 정의합니다.
   - 상태 확인 및 로드 밸런싱 알고리즘을 구성할 수 있습니다.
   - 서비스의 라우팅 규칙과 연결됩니다.

4. **리스너(Listener)**:
   - 특정 포트와 프로토콜에서 연결 요청을 확인합니다.
   - HTTP, HTTPS, gRPC 프로토콜을 지원합니다.
   - 라우팅 규칙과 연결됩니다.

5. **라우팅 규칙(Routing Rule)**:
   - 요청을 어떤 대상 그룹으로 전달할지 결정합니다.
   - 경로, 헤더, 쿼리 파라미터 등을 기반으로 라우팅할 수 있습니다.
   - 가중치 기반 라우팅을 지원하여 트래픽 분할이 가능합니다.

**VPC Lattice 구성 요소 간의 관계:**

```
+---------------------+
| Service Network     |
|                     |
|  +---------------+  |
|  | Service       |  |
|  |               |  |
|  |  +----------+ |  |
|  |  | Listener | |  |
|  |  +----------+ |  |
|  |       |       |  |
|  |  +----------+ |  |
|  |  | Routing  | |  |
|  |  | Rule     | |  |
|  |  +----------+ |  |
|  |       |       |  |
|  |  +----------+ |  |
|  |  | Target   | |  |
|  |  | Group    | |  |
|  |  +----------+ |  |
|  +---------------+  |
+---------------------+
```

**각 구성 요소의 AWS CLI 예시:**

1. **서비스 네트워크 생성**:
```bash
aws vpc-lattice create-service-network \
  --name my-service-network \
  --auth-type AWS_IAM
```

2. **서비스 생성**:
```bash
aws vpc-lattice create-service \
  --name my-service \
  --auth-type NONE
```

3. **대상 그룹 생성**:
```bash
aws vpc-lattice create-target-group \
  --name my-target-group \
  --type INSTANCE \
  --config '{"port":80,"protocol":"HTTP","vpcIdentifier":"vpc-1234567890abcdef0"}'
```

4. **리스너 생성**:
```bash
aws vpc-lattice create-listener \
  --service-identifier svc-1234567890abcdef0 \
  --name my-listener \
  --protocol HTTP \
  --port 80 \
  --default-action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"tg-1234567890abcdef0"}]}}'
```

5. **서비스를 서비스 네트워크에 연결**:
```bash
aws vpc-lattice associate-service \
  --service-identifier svc-1234567890abcdef0 \
  --service-network-identifier sn-1234567890abcdef0
```

6. **VPC를 서비스 네트워크에 연결**:
```bash
aws vpc-lattice associate-vpc \
  --service-network-identifier sn-1234567890abcdef0 \
  --vpc-identifier vpc-1234567890abcdef0
```

**서비스 메시(Service Mesh)와 VPC Lattice의 차이점:**

서비스 메시(예: AWS App Mesh)는 마이크로서비스 간의 통신을 관리하는 인프라 계층으로, 주로 다음과 같은 기능을 제공합니다:

1. **사이드카 프록시**: 각 서비스 인스턴스와 함께 실행되는 프록시(일반적으로 Envoy)를 배포합니다.
2. **트래픽 관리**: 서비스 간 트래픽의 라우팅, 분할, 미러링을 제어합니다.
3. **보안**: 서비스 간 통신의 인증, 권한 부여, 암호화를 관리합니다.
4. **관찰성**: 서비스 간 통신에 대한 메트릭, 로그, 추적을 제공합니다.

반면, VPC Lattice는:
1. **프록시 없음**: 사이드카 프록시를 배포하지 않고 AWS 인프라에 내장된 서비스로 작동합니다.
2. **계정 및 VPC 경계**: 여러 계정과 VPC에 걸쳐 서비스를 연결하는 데 중점을 둡니다.
3. **간소화된 관리**: 서비스 메시보다 더 간단한 구성과 관리를 제공합니다.
4. **다양한 컴퓨팅 유형**: EC2, ECS, EKS, Lambda 등 다양한 컴퓨팅 유형을 지원합니다.

**다른 옵션들의 설명:**
- A. 서비스 네트워크(Service Network): VPC Lattice의 핵심 구성 요소로, 서비스 간 통신을 위한 논리적 경계를 제공합니다.
- B. 서비스(Service): VPC Lattice의 주요 구성 요소로, 애플리케이션 또는 마이크로서비스를 나타냅니다.
- C. 대상 그룹(Target Group): VPC Lattice의 주요 구성 요소로, 요청을 처리할 대상을 정의합니다.
</details>

### 3. VPC Lattice 서비스 네트워크에 VPC를 연결하는 방법은 무엇인가요?

A. VPC 피어링 연결 생성  
B. VPC Lattice 콘솔 또는 API를 통해 VPC 연결(Association) 생성  
C. Transit Gateway 연결 설정  
D. VPC 엔드포인트 생성  

<details>
<summary>정답 및 설명</summary>

**정답: B. VPC Lattice 콘솔 또는 API를 통해 VPC 연결(Association) 생성**

**설명:**
VPC Lattice 서비스 네트워크에 VPC를 연결하는 방법은 VPC Lattice 콘솔 또는 API를 통해 VPC 연결(Association)을 생성하는 것입니다. 이 연결을 통해 VPC 내의 리소스가 서비스 네트워크에 등록된 서비스에 액세스할 수 있게 됩니다.

**VPC 연결 프로세스:**

1. **콘솔을 통한 연결**:
   - AWS Management Console에서 VPC Lattice 서비스로 이동합니다.
   - 서비스 네트워크를 선택하고 "VPC 연결" 탭을 클릭합니다.
   - "VPC 연결 생성" 버튼을 클릭하고 연결할 VPC를 선택합니다.
   - 필요에 따라 보안 그룹을 선택하고 연결을 생성합니다.

2. **AWS CLI를 통한 연결**:
```bash
aws vpc-lattice associate-vpc \
  --service-network-identifier sn-1234567890abcdef0 \
  --vpc-identifier vpc-1234567890abcdef0 \
  --security-group-ids sg-1234567890abcdef0
```

3. **AWS SDK를 통한 연결**:
```python
import boto3

client = boto3.client('vpc-lattice')

response = client.associate_vpc(
    serviceNetworkIdentifier='sn-1234567890abcdef0',
    vpcIdentifier='vpc-1234567890abcdef0',
    securityGroupIds=['sg-1234567890abcdef0']
)
```

**VPC 연결 후 동작:**

1. **DNS 해석**: 
   - VPC Lattice는 서비스 네트워크 내의 서비스에 대한 DNS 레코드를 생성합니다.
   - VPC 내의 리소스는 서비스의 DNS 이름을 사용하여 서비스에 액세스할 수 있습니다.

2. **트래픽 라우팅**: 
   - VPC 내의 리소스에서 서비스로 향하는 트래픽은 VPC Lattice 인프라를 통해 라우팅됩니다.
   - VPC Lattice는 구성된 라우팅 규칙에 따라 트래픽을 적절한 대상으로 전달합니다.

3. **보안 그룹**: 
   - 연결 시 지정한 보안 그룹은 VPC Lattice 서비스에 대한 인바운드 및 아웃바운드 트래픽을 제어합니다.
   - 보안 그룹 규칙을 통해 서비스에 대한 액세스를 세밀하게 제어할 수 있습니다.

**VPC 연결 제한 사항:**

1. **리전 제한**: 
   - VPC와 서비스 네트워크는 동일한 AWS 리전에 있어야 합니다.
   - 크로스 리전 연결은 지원되지 않습니다.

2. **VPC 수 제한**: 
   - 하나의 서비스 네트워크에 연결할 수 있는 VPC 수에는 제한이 있습니다(기본적으로 계정당 10개).
   - AWS Support를 통해 이 제한을 늘릴 수 있습니다.

3. **CIDR 중복**: 
   - 연결된 VPC 간에 CIDR 범위가 중복되지 않도록 해야 합니다.
   - CIDR 중복은 라우팅 문제를 일으킬 수 있습니다.

**VPC 연결 모범 사례:**

1. **최소 권한 원칙**: 
   - 필요한 최소한의 권한만 부여하는 보안 그룹 규칙을 구성합니다.
   - 특정 포트와 프로토콜에 대한 액세스만 허용합니다.

2. **네트워크 세분화**: 
   - 서로 다른 환경(개발, 테스트, 프로덕션)에 대해 별도의 서비스 네트워크를 사용합니다.
   - 필요한 VPC만 서비스 네트워크에 연결합니다.

3. **모니터링 및 로깅**: 
   - VPC Lattice 서비스에 대한 액세스를 모니터링하고 로깅합니다.
   - CloudWatch 메트릭과 로그를 활용하여 트래픽 패턴을 분석합니다.

4. **정기적인 검토**: 
   - VPC 연결을 정기적으로 검토하고 불필요한 연결을 제거합니다.
   - 보안 그룹 규칙을 정기적으로 감사합니다.

**다른 옵션들의 문제점:**
- A. VPC 피어링 연결 생성: VPC 피어링은 두 VPC 간의 직접 네트워크 연결을 제공하지만, VPC Lattice 서비스 네트워크에 VPC를 연결하는 방법은 아닙니다.
- C. Transit Gateway 연결 설정: Transit Gateway는 여러 VPC와 온프레미스 네트워크를 연결하는 데 사용되지만, VPC Lattice 서비스 네트워크에 VPC를 연결하는 방법은 아닙니다.
- D. VPC 엔드포인트 생성: VPC 엔드포인트는 AWS 서비스에 대한 프라이빗 연결을 제공하지만, VPC Lattice 서비스 네트워크에 VPC를 연결하는 방법은 아닙니다.
</details>
### 4. VPC Lattice에서 서비스에 대한 액세스를 제어하는 방법은 무엇인가요?

A. 네트워크 ACL만 사용  
B. IAM 정책과 리소스 정책만 사용  
C. 보안 그룹만 사용  
D. IAM 정책, 리소스 정책, 인증 정책을 조합하여 사용  

<details>
<summary>정답 및 설명</summary>

**정답: D. IAM 정책, 리소스 정책, 인증 정책을 조합하여 사용**

**설명:**
VPC Lattice에서 서비스에 대한 액세스를 제어하는 방법은 IAM 정책, 리소스 정책, 인증 정책을 조합하여 사용하는 것입니다. VPC Lattice는 다양한 수준에서 세밀한 액세스 제어를 제공하여 서비스에 대한 액세스를 안전하게 관리할 수 있게 합니다.

**VPC Lattice의 액세스 제어 메커니즘:**

1. **인증 유형(Auth Type)**:
   - 서비스 생성 시 다음 인증 유형 중 하나를 선택할 수 있습니다:
     - **NONE**: 인증 없이 모든 요청 허용
     - **AWS_IAM**: IAM 자격 증명을 사용한 인증 필요
   - 서비스 네트워크 수준에서도 인증 유형을 설정할 수 있습니다.

2. **IAM 정책**:
   - 사용자, 그룹, 역할에 연결하여 VPC Lattice 리소스에 대한 액세스를 제어합니다.
   - 예: 특정 사용자가 특정 서비스를 생성하거나 수정할 수 있는 권한을 부여합니다.

3. **리소스 정책**:
   - 서비스 또는 서비스 네트워크에 직접 연결되는 정책입니다.
   - 해당 리소스에 대한 액세스를 허용하거나 거부합니다.
   - 예: 특정 AWS 계정이 서비스에 액세스할 수 있도록 허용합니다.

4. **인증 정책**:
   - 서비스에 대한 요청을 인증하는 방법을 정의합니다.
   - IAM 자격 증명을 사용한 인증을 요구할 수 있습니다.

**IAM 정책 예시:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc-lattice:CreateService",
        "vpc-lattice:CreateServiceNetwork",
        "vpc-lattice:AssociateVPC"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc-lattice:InvokeService"
      ],
      "Resource": "arn:aws:vpc-lattice:us-west-2:123456789012:service/svc-1234567890abcdef0"
    }
  ]
}
```

**리소스 정책 예시:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyRole"
      },
      "Action": "vpc-lattice:InvokeService",
      "Resource": "arn:aws:vpc-lattice:us-west-2:123456789012:service/svc-1234567890abcdef0"
    }
  ]
}
```

**서비스 인증 구성 예시 (AWS CLI):**

```bash
aws vpc-lattice create-service \
  --name my-service \
  --auth-type AWS_IAM
```

**액세스 제어 모범 사례:**

1. **최소 권한 원칙**:
   - 필요한 최소한의 권한만 부여합니다.
   - 서비스별로 세분화된 정책을 사용합니다.

2. **인증 유형 선택**:
   - 공개 서비스의 경우 `NONE`을 사용할 수 있습니다.
   - 내부 또는 민감한 서비스의 경우 `AWS_IAM`을 사용합니다.

3. **조건 키 활용**:
   - IAM 정책에서 조건 키를 사용하여 액세스를 더 세밀하게 제어합니다.
   - 예: 특정 소스 IP 또는 시간에 따른 액세스 제한

4. **정기적인 감사**:
   - 액세스 정책을 정기적으로 검토하고 업데이트합니다.
   - 불필요한 권한을 제거합니다.

**VPC Lattice 액세스 제어의 계층:**

1. **네트워크 수준**:
   - VPC 연결 및 보안 그룹을 통해 네트워크 수준에서 액세스를 제어합니다.
   - 특정 VPC의 리소스만 서비스에 액세스할 수 있도록 제한합니다.

2. **서비스 네트워크 수준**:
   - 서비스 네트워크에 대한 리소스 정책을 통해 액세스를 제어합니다.
   - 서비스 네트워크에 대한 인증 유형을 설정합니다.

3. **서비스 수준**:
   - 서비스에 대한 리소스 정책을 통해 액세스를 제어합니다.
   - 서비스에 대한 인증 유형을 설정합니다.

4. **요청 수준**:
   - IAM 정책의 조건을 통해 특정 요청 속성(경로, 메서드 등)에 따라 액세스를 제어합니다.

**다른 옵션들의 문제점:**
- A. 네트워크 ACL만 사용: 네트워크 ACL은 서브넷 수준에서 트래픽을 제어하지만, VPC Lattice 서비스에 대한 세밀한 액세스 제어를 제공하지 않습니다.
- B. IAM 정책과 리소스 정책만 사용: 이는 부분적으로 맞지만, 인증 정책(Auth Type)도 VPC Lattice의 중요한 액세스 제어 메커니즘입니다.
- C. 보안 그룹만 사용: 보안 그룹은 네트워크 수준에서 트래픽을 제어하지만, VPC Lattice 서비스에 대한 세밀한 액세스 제어를 제공하지 않습니다.
</details>

### 5. VPC Lattice와 Kubernetes(EKS)를 통합하는 방법으로 올바른 것은 무엇인가요?

A. AWS Load Balancer Controller를 사용하여 Kubernetes 서비스를 VPC Lattice 서비스로 노출  
B. AWS VPC CNI 플러그인을 사용하여 자동으로 통합  
C. Kubernetes Operator를 사용하여 VPC Lattice 리소스 관리  
D. AWS App Mesh를 통해 VPC Lattice와 통합  

<details>
<summary>정답 및 설명</summary>

**정답: A. AWS Load Balancer Controller를 사용하여 Kubernetes 서비스를 VPC Lattice 서비스로 노출**

**설명:**
VPC Lattice와 Kubernetes(EKS)를 통합하는 올바른 방법은 AWS Load Balancer Controller를 사용하여 Kubernetes 서비스를 VPC Lattice 서비스로 노출하는 것입니다. AWS Load Balancer Controller는 Kubernetes 서비스 리소스를 AWS VPC Lattice 서비스로 매핑하는 기능을 제공합니다.

**통합 과정:**

1. **AWS Load Balancer Controller 설치**:
   - AWS Load Balancer Controller는 Kubernetes 클러스터에 설치되는 컨트롤러로, Kubernetes 서비스 리소스를 AWS 로드 밸런서로 변환합니다.
   - 버전 2.5.0 이상에서 VPC Lattice 통합을 지원합니다.

2. **IAM 권한 구성**:
   - AWS Load Balancer Controller가 VPC Lattice 리소스를 생성하고 관리할 수 있도록 적절한 IAM 권한을 구성해야 합니다.
   - 필요한 권한에는 `vpc-lattice:*` 작업이 포함됩니다.

3. **서비스 주석 추가**:
   - Kubernetes 서비스에 특정 주석을 추가하여 VPC Lattice 서비스로 노출하도록 지정합니다.
   - 주요 주석: `service.beta.kubernetes.io/aws-load-balancer-type: "vpc-lattice"`

**Kubernetes 서비스 예시:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "vpc-lattice"
    service.beta.kubernetes.io/aws-load-balancer-name: "my-lattice-service"
    service.beta.kubernetes.io/aws-load-balancer-vpc-lattice-service-network: "sn-1234567890abcdef0"
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
      protocol: TCP
```

**AWS Load Balancer Controller의 동작:**

1. **서비스 감지**:
   - 컨트롤러는 `type: LoadBalancer`와 VPC Lattice 관련 주석이 있는 Kubernetes 서비스를 감지합니다.

2. **VPC Lattice 리소스 생성**:
   - 컨트롤러는 VPC Lattice 서비스, 대상 그룹, 리스너 등의 리소스를 생성합니다.
   - Kubernetes 서비스의 선택기와 일치하는 파드를 VPC Lattice 대상 그룹에 등록합니다.

3. **DNS 구성**:
   - VPC Lattice 서비스의 DNS 이름이 Kubernetes 서비스의 외부 이름으로 설정됩니다.
   - 클라이언트는 이 DNS 이름을 사용하여 서비스에 액세스할 수 있습니다.

4. **상태 동기화**:
   - 컨트롤러는 Kubernetes 서비스와 VPC Lattice 리소스 간의 상태를 지속적으로 동기화합니다.
   - 서비스가 업데이트되거나 삭제되면 해당 VPC Lattice 리소스도 업데이트되거나 삭제됩니다.

**지원되는 주석:**

| 주석 | 설명 | 예시 |
|------|------|------|
| `service.beta.kubernetes.io/aws-load-balancer-type` | 로드 밸런서 유형을 VPC Lattice로 지정 | `"vpc-lattice"` |
| `service.beta.kubernetes.io/aws-load-balancer-name` | VPC Lattice 서비스의 이름 | `"my-service"` |
| `service.beta.kubernetes.io/aws-load-balancer-vpc-lattice-service-network` | 서비스를 연결할 서비스 네트워크 ID | `"sn-1234567890abcdef0"` |
| `service.beta.kubernetes.io/aws-load-balancer-vpc-lattice-auth-type` | 인증 유형 | `"AWS_IAM"` 또는 `"NONE"` |
| `service.beta.kubernetes.io/aws-load-balancer-healthcheck-path` | 상태 확인 경로 | `"/health"` |
| `service.beta.kubernetes.io/aws-load-balancer-healthcheck-port` | 상태 확인 포트 | `"8080"` |

**통합 모범 사례:**

1. **네임스페이스 분리**:
   - 다른 환경(개발, 테스트, 프로덕션)에 대해 별도의 서비스 네트워크를 사용합니다.
   - Kubernetes 네임스페이스를 사용하여 서비스를 논리적으로 그룹화합니다.

2. **서비스 명명 규칙**:
   - 일관된 명명 규칙을 사용하여 Kubernetes 서비스와 VPC Lattice 서비스를 쉽게 연관시킬 수 있도록 합니다.
   - 예: `<환경>-<애플리케이션>-<구성 요소>`

3. **상태 확인 구성**:
   - 애플리케이션에 적합한 상태 확인 경로와 포트를 구성합니다.
   - 상태 확인 간격과 임계값을 조정하여 빠른 장애 감지와 불필요한 장애 전환 사이의 균형을 맞춥니다.

4. **모니터링 및 로깅**:
   - CloudWatch 메트릭과 로그를 활용하여 VPC Lattice 서비스를 모니터링합니다.
   - Kubernetes 이벤트를 모니터링하여 AWS Load Balancer Controller의 문제를 감지합니다.

**다른 옵션들의 문제점:**
- B. AWS VPC CNI 플러그인을 사용하여 자동으로 통합: AWS VPC CNI 플러그인은 Kubernetes 파드에 VPC IP 주소를 할당하는 데 사용되지만, VPC Lattice 통합과는 직접적인 관련이 없습니다.
- C. Kubernetes Operator를 사용하여 VPC Lattice 리소스 관리: 현재 VPC Lattice에 대한 공식 Kubernetes Operator는 없으며, AWS Load Balancer Controller가 이 역할을 수행합니다.
- D. AWS App Mesh를 통해 VPC Lattice와 통합: AWS App Mesh는 서비스 메시 솔루션으로, VPC Lattice와는 별개의 서비스입니다. 두 서비스를 함께 사용할 수는 있지만, App Mesh를 통해 VPC Lattice와 통합하는 것은 아닙니다.
</details>

### 6. VPC Lattice에서 트래픽 라우팅을 구성하는 방법으로 올바르지 않은 것은 무엇인가요?

A. 경로 기반 라우팅(Path-based routing)  
B. 헤더 기반 라우팅(Header-based routing)  
C. 지리적 위치 기반 라우팅(Geolocation-based routing)  
D. 가중치 기반 라우팅(Weighted routing)  

<details>
<summary>정답 및 설명</summary>

**정답: C. 지리적 위치 기반 라우팅(Geolocation-based routing)**

**설명:**
VPC Lattice에서 트래픽 라우팅을 구성하는 방법으로 올바르지 않은 것은 지리적 위치 기반 라우팅(Geolocation-based routing)입니다. VPC Lattice는 현재 지리적 위치 기반 라우팅을 지원하지 않습니다. VPC Lattice에서 지원하는 라우팅 방법에는 경로 기반 라우팅, 헤더 기반 라우팅, 쿼리 파라미터 기반 라우팅, 가중치 기반 라우팅 등이 있습니다.

**VPC Lattice에서 지원하는 라우팅 방법:**

1. **경로 기반 라우팅(Path-based routing)**:
   - URL 경로를 기반으로 트래픽을 다른 대상 그룹으로 라우팅합니다.
   - 예: `/api/*`로 시작하는 요청은 API 서비스로, `/admin/*`로 시작하는 요청은 관리자 서비스로 라우팅

```json
{
  "priority": 1,
  "match": {
    "pathMatch": {
      "match": {
        "prefix": "/api/"
      }
    }
  },
  "action": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-1234567890abcdef0",
          "weight": 100
        }
      ]
    }
  }
}
```

2. **헤더 기반 라우팅(Header-based routing)**:
   - HTTP 헤더 값을 기반으로 트래픽을 라우팅합니다.
   - 예: `User-Agent` 헤더에 따라 다른 버전의 서비스로 라우팅

```json
{
  "priority": 2,
  "match": {
    "headerMatches": [
      {
        "name": "User-Agent",
        "match": {
          "contains": "Mozilla"
        }
      }
    ]
  },
  "action": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-0987654321fedcba0",
          "weight": 100
        }
      ]
    }
  }
}
```

3. **쿼리 파라미터 기반 라우팅(Query parameter-based routing)**:
   - URL 쿼리 파라미터를 기반으로 트래픽을 라우팅합니다.
   - 예: `version=v2` 쿼리 파라미터가 있는 요청은 새 버전의 서비스로 라우팅

```json
{
  "priority": 3,
  "match": {
    "queryParameterMatches": [
      {
        "name": "version",
        "match": {
          "exact": "v2"
        }
      }
    ]
  },
  "action": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-abcdef1234567890",
          "weight": 100
        }
      ]
    }
  }
}
```

4. **가중치 기반 라우팅(Weighted routing)**:
   - 트래픽을 여러 대상 그룹에 가중치에 따라 분산합니다.
   - 예: 트래픽의 90%는 안정적인 버전으로, 10%는 새 버전으로 라우팅(카나리 배포)

```json
{
  "priority": 4,
  "action": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-stable-version",
          "weight": 90
        },
        {
          "targetGroupIdentifier": "tg-new-version",
          "weight": 10
        }
      ]
    }
  }
}
```

5. **HTTP 메서드 기반 라우팅(HTTP method-based routing)**:
   - HTTP 메서드(GET, POST, PUT 등)를 기반으로 트래픽을 라우팅합니다.
   - 예: GET 요청은 읽기 전용 서비스로, POST/PUT/DELETE 요청은 쓰기 가능 서비스로 라우팅

```json
{
  "priority": 5,
  "match": {
    "method": "GET"
  },
  "action": {
    "forward": {
      "targetGroups": [
        {
          "targetGroupIdentifier": "tg-read-only-service",
          "weight": 100
        }
      ]
    }
  }
}
```

**라우팅 규칙 우선순위:**

VPC Lattice에서는 라우팅 규칙에 우선순위를 할당할 수 있습니다. 낮은 숫자가 높은 우선순위를 나타냅니다. 요청이 들어오면 VPC Lattice는 우선순위에 따라 규칙을 평가하고 첫 번째로 일치하는 규칙을 적용합니다.

**라우팅 규칙 생성 예시 (AWS CLI):**

```bash
aws vpc-lattice create-rule \
  --listener-identifier listener-1234567890abcdef0 \
  --service-identifier svc-1234567890abcdef0 \
  --priority 1 \
  --match '{"pathMatch":{"match":{"prefix":"/api/"}}}' \
  --action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"tg-1234567890abcdef0","weight":100}]}}'
```

**고급 라우팅 시나리오:**

1. **블루/그린 배포**:
   - 두 버전의 서비스를 배포하고 가중치 기반 라우팅을 사용하여 트래픽을 전환합니다.
   - 초기에는 모든 트래픽을 블루(현재) 버전으로 라우팅하고, 테스트 후 모든 트래픽을 그린(새) 버전으로 전환합니다.

2. **카나리 배포**:
   - 새 버전에 트래픽의 작은 비율(예: 5%)만 라우팅하여 위험을 최소화합니다.
   - 새 버전이 안정적으로 작동하면 점진적으로 트래픽 비율을 늘립니다.

3. **A/B 테스팅**:
   - 헤더 또는 쿼리 파라미터를 기반으로 특정 사용자 그룹을 다른 버전의 서비스로 라우팅합니다.
   - 사용자 반응을 측정하여 어떤 버전이 더 효과적인지 평가합니다.

4. **기능 플래그**:
   - 쿼리 파라미터나 헤더를 사용하여 특정 기능이 활성화된 버전의 서비스로 라우팅합니다.
   - 예: `?feature=new-ui`가 있는 요청은 새 UI를 제공하는 서비스로 라우팅

**지리적 위치 기반 라우팅이 지원되지 않는 이유:**

VPC Lattice는 주로 AWS 리전 내에서 서비스 간 통신을 관리하는 데 중점을 둡니다. 지리적 위치 기반 라우팅은 일반적으로 글로벌 트래픽 관리에 사용되며, 이는 Amazon Route 53이나 AWS Global Accelerator와 같은 서비스의 영역입니다.

지리적 위치 기반 라우팅이 필요한 경우, 다음과 같은 대안을 고려할 수 있습니다:
1. **Amazon Route 53**: 지리적 위치 기반 라우팅 정책을 제공합니다.
2. **AWS Global Accelerator**: 사용자의 위치에 따라 가장 가까운 AWS 리전으로 트래픽을 라우팅합니다.
3. **Amazon CloudFront**: 엣지 로케이션을 통해 콘텐츠를 전달하고 사용자의 위치에 따라 라우팅할 수 있습니다.

**다른 옵션들의 설명:**
- A. 경로 기반 라우팅(Path-based routing): VPC Lattice에서 지원하는 라우팅 방법으로, URL 경로를 기반으로 트래픽을 라우팅합니다.
- B. 헤더 기반 라우팅(Header-based routing): VPC Lattice에서 지원하는 라우팅 방법으로, HTTP 헤더를 기반으로 트래픽을 라우팅합니다.
- D. 가중치 기반 라우팅(Weighted routing): VPC Lattice에서 지원하는 라우팅 방법으로, 가중치에 따라 트래픽을 여러 대상 그룹에 분산합니다.
</details>
### 7. VPC Lattice에서 서비스 간 트래픽을 모니터링하는 방법으로 올바른 것은 무엇인가요?

A. VPC Flow Logs만 사용  
B. CloudWatch 메트릭, CloudWatch Logs, AWS X-Ray를 통합하여 사용  
C. Prometheus와 Grafana만 사용  
D. AWS Config를 사용하여 서비스 구성 변경 추적  

<details>
<summary>정답 및 설명</summary>

**정답: B. CloudWatch 메트릭, CloudWatch Logs, AWS X-Ray를 통합하여 사용**

**설명:**
VPC Lattice에서 서비스 간 트래픽을 모니터링하는 올바른 방법은 CloudWatch 메트릭, CloudWatch Logs, AWS X-Ray를 통합하여 사용하는 것입니다. VPC Lattice는 이러한 AWS 서비스와 기본적으로 통합되어 서비스 간 통신에 대한 포괄적인 모니터링 및 관찰성을 제공합니다.

**VPC Lattice 모니터링 구성 요소:**

1. **CloudWatch 메트릭**:
   - VPC Lattice는 자동으로 서비스 및 대상 그룹 수준의 메트릭을 CloudWatch에 게시합니다.
   - 주요 메트릭에는 요청 수, 오류 수, 지연 시간, 처리된 바이트 등이 포함됩니다.
   - 이러한 메트릭을 사용하여 대시보드를 생성하고 경보를 설정할 수 있습니다.

2. **CloudWatch Logs**:
   - VPC Lattice 액세스 로그를 활성화하여 서비스에 대한 모든 요청의 세부 정보를 캡처할 수 있습니다.
   - 로그에는 클라이언트 IP, 요청 시간, 요청 경로, 응답 코드, 지연 시간 등의 정보가 포함됩니다.
   - CloudWatch Logs Insights를 사용하여 로그를 쿼리하고 분석할 수 있습니다.

3. **AWS X-Ray**:
   - VPC Lattice는 X-Ray와 통합되어 서비스 간 요청의 엔드-투-엔드 추적을 제공합니다.
   - X-Ray 추적을 통해 서비스 간 통신의 병목 현상과 오류를 식별할 수 있습니다.
   - 서비스 맵을 통해 서비스 간 의존성을 시각화할 수 있습니다.

**CloudWatch 메트릭 예시:**

VPC Lattice는 다음과 같은 메트릭을 CloudWatch에 게시합니다:

| 메트릭 이름 | 설명 | 차원 |
|------------|------|------|
| `RequestCount` | 처리된 요청 수 | ServiceId, TargetGroupId |
| `HTTP_4xx_Count` | 4xx 오류 응답 수 | ServiceId, TargetGroupId |
| `HTTP_5xx_Count` | 5xx 오류 응답 수 | ServiceId, TargetGroupId |
| `Latency` | 요청 처리 시간(ms) | ServiceId, TargetGroupId |
| `ProcessedBytes` | 처리된 바이트 수 | ServiceId, TargetGroupId |
| `HealthyTargetCount` | 정상 대상 수 | TargetGroupId |
| `UnhealthyTargetCount` | 비정상 대상 수 | TargetGroupId |

**CloudWatch 대시보드 생성:**

```bash
aws cloudwatch put-dashboard \
  --dashboard-name VPCLatticeMonitoring \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/VpcLattice", "RequestCount", "ServiceId", "svc-1234567890abcdef0"]
          ],
          "period": 60,
          "stat": "Sum",
          "region": "us-west-2",
          "title": "Request Count"
        }
      },
      {
        "type": "metric",
        "x": 12,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/VpcLattice", "HTTP_5xx_Count", "ServiceId", "svc-1234567890abcdef0"]
          ],
          "period": 60,
          "stat": "Sum",
          "region": "us-west-2",
          "title": "5xx Error Count"
        }
      }
    ]
  }'
```

**액세스 로그 활성화:**

```bash
aws vpc-lattice put-access-log-subscription \
  --resource-identifier svc-1234567890abcdef0 \
  --destination-arn "arn:aws:logs:us-west-2:123456789012:log-group:/aws/vpc-lattice/my-service" \
  --destination-type "cloudwatchlogs"
```

**CloudWatch Logs Insights 쿼리 예시:**

```
fields @timestamp, client_ip, request_path, status_code, request_processing_time
| filter status_code >= 500
| sort @timestamp desc
| limit 100
```

**X-Ray 추적 활성화:**

애플리케이션에서 X-Ray SDK를 사용하여 추적을 활성화하고, VPC Lattice 서비스를 통과하는 요청에 추적 헤더를 포함시킵니다.

```java
// Java 예시
import com.amazonaws.xray.AWSXRay;
import com.amazonaws.xray.entities.Segment;

public void processRequest() {
    Segment segment = AWSXRay.beginSegment("ServiceA");
    try {
        // VPC Lattice 서비스 호출
        URL url = new URL("https://my-service.vpc-lattice-svcs.us-west-2.on.aws/api/resource");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        // X-Ray 추적 헤더가 자동으로 추가됩니다
        
        // 응답 처리
    } catch (Exception e) {
        segment.addException(e);
        throw e;
    } finally {
        AWSXRay.endSegment();
    }
}
```

**모니터링 모범 사례:**

1. **다중 계층 모니터링**:
   - 인프라 수준(CPU, 메모리 등)
   - 서비스 수준(요청 수, 오류율 등)
   - 비즈니스 수준(트랜잭션 성공률, 사용자 활동 등)

2. **경보 설정**:
   - 주요 메트릭에 대한 CloudWatch 경보를 설정합니다.
   - 예: 5xx 오류율이 1% 이상이면 경보 트리거

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name VPCLattice-HighErrorRate \
  --alarm-description "Alarm when error rate exceeds 1%" \
  --metric-name HTTP_5xx_Count \
  --namespace AWS/VpcLattice \
  --dimensions Name=ServiceId,Value=svc-1234567890abcdef0 \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 5 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-west-2:123456789012:alert-topic
```

3. **로그 분석 자동화**:
   - CloudWatch Logs Insights를 사용하여 정기적인 보고서를 생성합니다.
   - 로그 기반 메트릭을 생성하여 특정 패턴을 모니터링합니다.

4. **대시보드 생성**:
   - 주요 메트릭을 표시하는 CloudWatch 대시보드를 생성합니다.
   - 서비스 상태, 트래픽 패턴, 오류율 등을 한눈에 볼 수 있도록 구성합니다.

**다른 옵션들의 문제점:**
- A. VPC Flow Logs만 사용: VPC Flow Logs는 네트워크 트래픽에 대한 정보를 제공하지만, 애플리케이션 수준의 메트릭이나 로그는 제공하지 않습니다.
- C. Prometheus와 Grafana만 사용: 이들은 강력한 모니터링 도구이지만, VPC Lattice와 기본적으로 통합되지 않으며 추가 구성이 필요합니다.
- D. AWS Config를 사용하여 서비스 구성 변경 추적: AWS Config는 리소스 구성을 추적하는 데 유용하지만, 서비스 간 트래픽 모니터링에는 적합하지 않습니다.
</details>

### 8. VPC Lattice에서 서비스 검색(Service Discovery)이 작동하는 방식은 무엇인가요?

A. 서비스 레지스트리에 수동으로 서비스를 등록해야 함  
B. AWS Cloud Map을 사용하여 서비스를 등록하고 검색  
C. VPC Lattice가 각 서비스에 대해 자동으로 DNS 레코드를 생성  
D. Kubernetes의 CoreDNS를 통해 서비스 검색  

<details>
<summary>정답 및 설명</summary>

**정답: C. VPC Lattice가 각 서비스에 대해 자동으로 DNS 레코드를 생성**

**설명:**
VPC Lattice에서 서비스 검색(Service Discovery)이 작동하는 방식은 VPC Lattice가 각 서비스에 대해 자동으로 DNS 레코드를 생성하는 것입니다. 서비스를 생성하면 VPC Lattice는 해당 서비스에 대한 고유한 DNS 이름을 자동으로 생성하고, 연결된 VPC 내의 리소스는 이 DNS 이름을 사용하여 서비스에 액세스할 수 있습니다.

**VPC Lattice 서비스 검색 메커니즘:**

1. **DNS 기반 서비스 검색**:
   - 각 VPC Lattice 서비스는 다음 형식의 고유한 DNS 이름을 받습니다:
     `<service-name>.<domain-owner-id>.vpc-lattice-svcs.<region>.on.aws`
   - 예: `my-service.12345678901.vpc-lattice-svcs.us-west-2.on.aws`
   - 이 DNS 이름은 서비스 생성 시 자동으로 생성되며, AWS 관리형 DNS 서버에 등록됩니다.

2. **VPC 연결 및 DNS 해석**:
   - VPC를 서비스 네트워크에 연결하면, VPC Lattice는 해당 VPC의 Route 53 Resolver에 DNS 레코드를 자동으로 등록합니다.
   - VPC 내의 리소스는 표준 DNS 해석을 통해 서비스 이름을 IP 주소로 해석할 수 있습니다.

3. **서비스 엔드포인트 해석**:
   - 클라이언트가 서비스 DNS 이름을 쿼리하면, DNS 서버는 VPC Lattice 서비스 엔드포인트의 IP 주소를 반환합니다.
   - 이 IP 주소는 VPC Lattice 인프라를 가리키며, 트래픽은 구성된 라우팅 규칙에 따라 적절한 대상으로 전달됩니다.

**서비스 검색 예시:**

1. **서비스 생성**:
```bash
aws vpc-lattice create-service \
  --name my-service \
  --auth-type NONE
```

2. **서비스 DNS 이름 확인**:
```bash
aws vpc-lattice get-service \
  --service-identifier svc-1234567890abcdef0

# 응답에서 DNS 이름 확인
# "dnsEntry": {
#   "domainName": "my-service.12345678901.vpc-lattice-svcs.us-west-2.on.aws",
#   "hostedZoneId": "Z01234567ABCDEFGHIJKL"
# }
```

3. **VPC 연결**:
```bash
aws vpc-lattice associate-vpc \
  --service-network-identifier sn-1234567890abcdef0 \
  --vpc-identifier vpc-1234567890abcdef0
```

4. **클라이언트에서 서비스 액세스**:
```bash
# EC2 인스턴스 또는 ECS/EKS 컨테이너에서
curl https://my-service.12345678901.vpc-lattice-svcs.us-west-2.on.aws/api/resource
```

**사용자 지정 도메인 이름:**

VPC Lattice 서비스에 사용자 지정 도메인 이름을 사용할 수도 있습니다:

1. **사용자 지정 도메인 인증서 생성**:
```bash
aws acm request-certificate \
  --domain-name api.example.com \
  --validation-method DNS
```

2. **사용자 지정 도메인 구성**:
```bash
aws vpc-lattice create-service \
  --name my-service \
  --auth-type NONE \
  --custom-domain-name '{"certificate":"arn:aws:acm:us-west-2:123456789012:certificate/12345678-1234-1234-1234-123456789012","name":"api.example.com"}'
```

3. **DNS CNAME 레코드 생성**:
Route 53 또는 다른 DNS 공급자에서 CNAME 레코드를 생성하여 사용자 지정 도메인을 VPC Lattice 서비스 도메인으로 가리킵니다.

**서비스 검색의 이점:**

1. **투명한 서비스 액세스**:
   - 클라이언트는 서비스의 물리적 위치나 인스턴스 수에 관계없이 일관된 DNS 이름을 사용하여 서비스에 액세스할 수 있습니다.
   - 서비스 인스턴스가 추가되거나 제거되어도 DNS 이름은 변경되지 않습니다.

2. **자동 로드 밸런싱**:
   - VPC Lattice는 서비스 DNS 이름을 통한 요청을 자동으로 로드 밸런싱합니다.
   - 클라이언트는 로드 밸런싱 로직을 구현할 필요가 없습니다.

3. **서비스 마이그레이션 용이성**:
   - 서비스 구현이 변경되어도 DNS 이름은 동일하게 유지됩니다.
   - 클라이언트 코드를 수정하지 않고도 서비스를 마이그레이션할 수 있습니다.

4. **크로스 계정 액세스**:
   - 서비스 네트워크를 통해 여러 AWS 계정의 서비스에 액세스할 수 있습니다.
   - 각 계정의 서비스는 고유한 DNS 이름을 통해 검색 가능합니다.

**서비스 검색 모범 사례:**

1. **의미 있는 서비스 이름**:
   - 서비스의 목적이나 기능을 명확히 나타내는 이름을 사용합니다.
   - 예: `user-service`, `payment-api`, `product-catalog`

2. **서비스 문서화**:
   - 각 서비스의 DNS 이름, 엔드포인트, 인증 요구사항 등을 문서화합니다.
   - 개발자 포털이나 내부 위키에 서비스 카탈로그를 유지합니다.

3. **상태 확인 엔드포인트**:
   - 각 서비스에 `/health` 또는 `/status`와 같은 상태 확인 엔드포인트를 구현합니다.
   - 클라이언트가 서비스 상태를 확인할 수 있도록 합니다.

4. **버전 관리**:
   - API 버전을 URL 경로(예: `/v1/resource`)나 헤더에 포함합니다.
   - 이를 통해 여러 버전의 API를 동시에 제공할 수 있습니다.

**다른 옵션들의 문제점:**
- A. 서비스 레지스트리에 수동으로 서비스를 등록해야 함: VPC Lattice는 서비스 생성 시 자동으로 DNS 레코드를 생성하므로 수동 등록이 필요하지 않습니다.
- B. AWS Cloud Map을 사용하여 서비스를 등록하고 검색: VPC Lattice는 자체 DNS 기반 서비스 검색 메커니즘을 사용하며, AWS Cloud Map에 의존하지 않습니다.
- D. Kubernetes의 CoreDNS를 통해 서비스 검색: VPC Lattice는 Kubernetes와 통합될 수 있지만, 서비스 검색은 Kubernetes의 CoreDNS가 아닌 VPC Lattice의 DNS 메커니즘을 통해 이루어집니다.
</details>
### 9. VPC Lattice 서비스 네트워크에 여러 AWS 계정의 서비스를 연결하는 방법으로 올바른 것은 무엇인가요?

A. VPC 피어링을 사용하여 계정 간 연결 설정  
B. RAM(Resource Access Manager)을 사용하여 서비스 네트워크 공유  
C. 각 계정에서 동일한 서비스 네트워크를 생성  
D. IAM 역할을 사용하여 크로스 계정 액세스 구성  

<details>
<summary>정답 및 설명</summary>

**정답: B. RAM(Resource Access Manager)을 사용하여 서비스 네트워크 공유**

**설명:**
VPC Lattice 서비스 네트워크에 여러 AWS 계정의 서비스를 연결하는 올바른 방법은 RAM(Resource Access Manager)을 사용하여 서비스 네트워크를 공유하는 것입니다. AWS RAM을 사용하면 한 계정에서 생성한 서비스 네트워크를 다른 계정과 공유할 수 있으며, 공유받은 계정은 해당 서비스 네트워크에 자신의 서비스를 등록하거나 VPC를 연결할 수 있습니다.

**RAM을 사용한 서비스 네트워크 공유 과정:**

1. **RAM 리소스 공유 생성**:
   - 서비스 네트워크를 소유한 계정(소유자 계정)에서 RAM 리소스 공유를 생성합니다.
   - 공유할 서비스 네트워크를 리소스로 지정합니다.
   - 공유 대상 계정 또는 조직을 지정합니다.

```bash
# 소유자 계정에서 실행
aws ram create-resource-share \
  --name "VPCLatticeNetworkShare" \
  --resource-arns "arn:aws:vpc-lattice:us-west-2:123456789012:servicenetwork/sn-1234567890abcdef0" \
  --principals "arn:aws:organizations::123456789012:organization/o-aa111bb222" \
  --permission-arns "arn:aws:ram::aws:permission/AWSRAMDefaultPermissionVPCLatticeServiceNetwork"
```

2. **공유 수락**:
   - 대상 계정(소비자 계정)에서 리소스 공유 초대를 수락합니다.
   - 조직 내 공유의 경우 자동으로 수락될 수 있습니다.

```bash
# 소비자 계정에서 실행
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "arn:aws:ram:us-west-2:123456789012:resource-share-invitation/1234567890abcdef0"
```

3. **소비자 계정에서 서비스 등록**:
   - 소비자 계정은 공유된 서비스 네트워크에 자신의 서비스를 등록할 수 있습니다.

```bash
# 소비자 계정에서 실행
aws vpc-lattice create-service \
  --name "consumer-service" \
  --auth-type NONE

aws vpc-lattice associate-service \
  --service-identifier svc-0987654321fedcba0 \
  --service-network-identifier sn-1234567890abcdef0
```

4. **소비자 계정에서 VPC 연결**:
   - 소비자 계정은 자신의 VPC를 공유된 서비스 네트워크에 연결할 수 있습니다.

```bash
# 소비자 계정에서 실행
aws vpc-lattice associate-vpc \
  --service-network-identifier sn-1234567890abcdef0 \
  --vpc-identifier vpc-0987654321fedcba0
```

**크로스 계정 서비스 액세스:**

1. **서비스 검색**:
   - 서비스 네트워크에 연결된 모든 VPC의 리소스는 네트워크 내의 모든 서비스를 DNS 이름으로 검색할 수 있습니다.
   - 예: 계정 A의 EC2 인스턴스는 계정 B의 서비스를 `service-b.vpc-lattice-svcs.us-west-2.on.aws`와 같은 DNS 이름으로 액세스할 수 있습니다.

2. **인증 및 권한 부여**:
   - 서비스가 AWS_IAM 인증 유형을 사용하는 경우, 적절한 IAM 정책이 필요합니다.
   - 소비자 계정의 IAM 보안 주체에게 `vpc-lattice:InvokeService` 권한을 부여해야 합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "vpc-lattice:InvokeService",
      "Resource": "arn:aws:vpc-lattice:us-west-2:123456789012:service/svc-1234567890abcdef0"
    }
  ]
}
```

**크로스 계정 서비스 네트워크의 이점:**

1. **중앙 집중식 관리**:
   - 한 계정에서 서비스 네트워크를 관리하고 여러 계정과 공유할 수 있습니다.
   - 일관된 네트워킹 정책과 보안 제어를 적용할 수 있습니다.

2. **계정 간 서비스 통합**:
   - 다른 계정의 서비스를 쉽게 통합할 수 있습니다.
   - 계정 경계를 넘어 마이크로서비스 아키텍처를 구현할 수 있습니다.

3. **환경 분리**:
   - 개발, 테스트, 프로덕션 환경을 별도의 계정에 배포하면서도 서비스 간 통신을 유지할 수 있습니다.
   - 각 환경의 독립성을 유지하면서 필요한 서비스 간 통합을 구현할 수 있습니다.

4. **팀 자율성**:
   - 각 팀이 자체 AWS 계정에서 서비스를 관리하면서도 다른 팀의 서비스와 통합할 수 있습니다.
   - 팀 간의 명확한 책임 경계를 유지할 수 있습니다.

**크로스 계정 서비스 네트워크 모범 사례:**

1. **명확한 소유권 정의**:
   - 서비스 네트워크의 소유자와 책임을 명확히 정의합니다.
   - 변경 관리 및 문제 해결을 위한 프로세스를 수립합니다.

2. **최소 권한 원칙**:
   - 필요한 최소한의 권한만 공유합니다.
   - 서비스 네트워크 관리 권한과 서비스 호출 권한을 분리합니다.

3. **서비스 문서화**:
   - 공유된 서비스의 API, 인증 요구사항, 사용 제한 등을 문서화합니다.
   - 서비스 변경 시 모든 소비자 계정에 알립니다.

4. **모니터링 및 로깅**:
   - 크로스 계정 서비스 호출을 모니터링하고 로깅합니다.
   - CloudWatch 대시보드를 통해 전체 서비스 네트워크의 상태를 확인합니다.

**다른 옵션들의 문제점:**
- A. VPC 피어링을 사용하여 계정 간 연결 설정: VPC 피어링은 VPC 간 네트워크 연결을 제공하지만, VPC Lattice 서비스 네트워크를 공유하는 방법은 아닙니다.
- C. 각 계정에서 동일한 서비스 네트워크를 생성: 서비스 네트워크는 계정별로 고유하며, 동일한 서비스 네트워크를 여러 계정에서 생성할 수 없습니다.
- D. IAM 역할을 사용하여 크로스 계정 액세스 구성: IAM 역할은 서비스 호출 권한을 부여하는 데 사용될 수 있지만, 서비스 네트워크 자체를 공유하는 방법은 아닙니다.
</details>

### 10. VPC Lattice를 사용하여 블루/그린 배포를 구현하는 방법으로 가장 적합한 것은 무엇인가요?

A. 두 버전의 서비스를 위한 별도의 VPC Lattice 서비스 생성  
B. 가중치 기반 라우팅 규칙을 사용하여 트래픽을 점진적으로 전환  
C. 서비스 네트워크를 복제하여 새 버전 배포  
D. Route 53 가중치 기반 레코드 세트 사용  

<details>
<summary>정답 및 설명</summary>

**정답: B. 가중치 기반 라우팅 규칙을 사용하여 트래픽을 점진적으로 전환**

**설명:**
VPC Lattice를 사용하여 블루/그린 배포를 구현하는 가장 적합한 방법은 가중치 기반 라우팅 규칙을 사용하여 트래픽을 점진적으로 전환하는 것입니다. VPC Lattice의 라우팅 규칙을 통해 동일한 서비스 내에서 트래픽을 여러 대상 그룹으로 분산할 수 있으며, 가중치를 조정하여 트래픽을 점진적으로 새 버전(그린)으로 전환할 수 있습니다.

**블루/그린 배포 구현 단계:**

1. **두 개의 대상 그룹 생성**:
   - 현재 버전(블루)을 위한 대상 그룹과 새 버전(그린)을 위한 대상 그룹을 생성합니다.

```bash
# 블루 대상 그룹 생성
aws vpc-lattice create-target-group \
  --name blue-target-group \
  --type INSTANCE \
  --config '{"port":80,"protocol":"HTTP","vpcIdentifier":"vpc-1234567890abcdef0"}'

# 그린 대상 그룹 생성
aws vpc-lattice create-target-group \
  --name green-target-group \
  --type INSTANCE \
  --config '{"port":80,"protocol":"HTTP","vpcIdentifier":"vpc-1234567890abcdef0"}'
```

2. **대상 등록**:
   - 각 대상 그룹에 해당 버전의 인스턴스나 IP를 등록합니다.

```bash
# 블루 대상 그룹에 대상 등록
aws vpc-lattice register-targets \
  --target-group-identifier tg-blue-1234567890abcdef0 \
  --targets '[{"id":"i-0123456789abcdef0","port":80}]'

# 그린 대상 그룹에 대상 등록
aws vpc-lattice register-targets \
  --target-group-identifier tg-green-0987654321fedcba0 \
  --targets '[{"id":"i-0987654321fedcba0","port":80}]'
```

3. **초기 라우팅 규칙 생성**:
   - 처음에는 모든 트래픽(100%)을 블루 대상 그룹으로 라우팅합니다.

```bash
aws vpc-lattice create-rule \
  --listener-identifier listener-1234567890abcdef0 \
  --service-identifier svc-1234567890abcdef0 \
  --priority 1 \
  --action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"tg-blue-1234567890abcdef0","weight":100}]}}'
```

4. **점진적 트래픽 전환**:
   - 라우팅 규칙을 업데이트하여 트래픽의 일부를 그린 대상 그룹으로 전환합니다.
   - 예: 블루 90%, 그린 10%

```bash
aws vpc-lattice update-rule \
  --rule-identifier rule-1234567890abcdef0 \
  --service-identifier svc-1234567890abcdef0 \
  --action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"tg-blue-1234567890abcdef0","weight":90},{"targetGroupIdentifier":"tg-green-0987654321fedcba0","weight":10}]}}'
```

5. **모니터링 및 검증**:
   - 그린 버전의 성능과 오류율을 모니터링합니다.
   - 문제가 없으면 점진적으로 더 많은 트래픽을 그린 버전으로 전환합니다.

6. **완전 전환**:
   - 검증이 완료되면 모든 트래픽(100%)을 그린 대상 그룹으로 전환합니다.

```bash
aws vpc-lattice update-rule \
  --rule-identifier rule-1234567890abcdef0 \
  --service-identifier svc-1234567890abcdef0 \
  --action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"tg-green-0987654321fedcba0","weight":100}]}}'
```

7. **롤백 계획**:
   - 문제 발생 시 빠르게 블루 버전으로 롤백할 수 있도록 계획을 수립합니다.
   - 라우팅 규칙을 원래 상태로 되돌리는 것만으로 롤백이 가능합니다.

**블루/그린 배포의 이점:**

1. **무중단 배포**:
   - 사용자 요청을 중단하지 않고 새 버전을 배포할 수 있습니다.
   - 서비스 가용성이 유지됩니다.

2. **빠른 롤백**:
   - 문제 발생 시 라우팅 규칙을 변경하여 즉시 이전 버전으로 롤백할 수 있습니다.
   - 다운타임 없이 복구가 가능합니다.

3. **점진적 검증**:
   - 소량의 트래픽으로 새 버전을 테스트할 수 있습니다.
   - 실제 프로덕션 환경에서 새 버전의 성능과 안정성을 검증할 수 있습니다.

4. **세밀한 제어**:
   - 트래픽 전환 속도를 세밀하게 제어할 수 있습니다.
   - 모니터링 결과에 따라 전환 계획을 조정할 수 있습니다.

**고급 배포 전략:**

1. **카나리 배포**:
   - 트래픽의 작은 비율(예: 5%)만 새 버전으로 라우팅합니다.
   - 새 버전의 성능과 안정성을 모니터링한 후 점진적으로 트래픽을 늘립니다.

2. **특정 사용자 그룹 대상 배포**:
   - 헤더 기반 라우팅을 사용하여 특정 사용자 그룹(예: 내부 사용자)의 요청만 새 버전으로 라우팅합니다.

```bash
aws vpc-lattice create-rule \
  --listener-identifier listener-1234567890abcdef0 \
  --service-identifier svc-1234567890abcdef0 \
  --priority 1 \
  --match '{"headerMatches":[{"name":"User-Group","match":{"exact":"internal"}}]}' \
  --action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"tg-green-0987654321fedcba0","weight":100}]}}'
```

3. **다크 런칭**:
   - 프로덕션 트래픽을 복제하여 새 버전으로 전송하고 응답은 폐기합니다.
   - 실제 사용자에게 영향을 주지 않고 새 버전을 테스트할 수 있습니다.

**블루/그린 배포 모범 사례:**

1. **자동화**:
   - 배포 및 롤백 프로세스를 자동화합니다.
   - CI/CD 파이프라인에 통합하여 일관된 배포를 보장합니다.

2. **모니터링 강화**:
   - 배포 중에는 더 자주 메트릭을 확인합니다.
   - 오류율, 지연 시간, 처리량 등의 핵심 지표를 모니터링합니다.

3. **점진적 전환**:
   - 한 번에 모든 트래픽을 전환하지 않고 단계적으로 전환합니다.
   - 예: 10% → 30% → 50% → 100%

4. **롤백 임계값 정의**:
   - 자동 롤백을 트리거할 오류율이나 지연 시간 임계값을 정의합니다.
   - 예: 오류율이 1%를 초과하면 자동으로 롤백

**다른 옵션들의 문제점:**
- A. 두 버전의 서비스를 위한 별도의 VPC Lattice 서비스 생성: 이 방법은 가능하지만, 클라이언트가 다른 서비스 엔드포인트를 사용해야 하므로 무중단 전환이 어렵습니다.
- C. 서비스 네트워크를 복제하여 새 버전 배포: 서비스 네트워크는 서비스 간 통신을 위한 논리적 경계이며, 배포 버전 관리에는 적합하지 않습니다.
- D. Route 53 가중치 기반 레코드 세트 사용: 이 방법도 가능하지만, VPC Lattice 내에서 가중치 기반 라우팅을 사용하는 것이 더 간단하고 통합된 방법입니다.
</details>
