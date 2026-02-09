# VPC Lattice 퀴즈

이 퀴즈는 Amazon VPC Lattice에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Amazon VPC Lattice의 주요 사용 목적으로 올바른 것은?
   - A) 인터넷에서 AWS 리소스로의 외부 트래픽 관리
   - B) 서로 다른 VPC와 계정에 걸쳐 있는 서비스 간 내부 통신
   - C) AWS 리전 간 데이터 복제
   - D) DNS 기반 글로벌 로드 밸런싱

<details>

<summary>정답 보기</summary>

**정답: B) 서로 다른 VPC와 계정에 걸쳐 있는 서비스 간 내부 통신**

**설명:**
VPC Lattice는 AWS의 애플리케이션 네트워킹 서비스로, 여러 VPC와 AWS 계정에 걸쳐 있는 서비스들을 안전하게 연결하고 관리하는 것이 주요 목적입니다. Service Network라는 논리적 경계 내에서 서비스 디스커버리, 트래픽 라우팅, 인증 및 권한 부여를 제공합니다. 외부 트래픽 관리는 API Gateway나 ALB가, 리전 간 복제는 S3 Cross-Region Replication 등이 담당합니다.
</details>

2. VPC Lattice의 Service Network에 대한 설명으로 올바른 것은?
   - A) 물리적인 네트워크 장비를 연결하는 계층
   - B) 서비스들을 그룹화하고 통신을 관리하는 논리적 경계
   - C) VPC 내부의 서브넷을 연결하는 라우팅 테이블
   - D) 인터넷 게이트웨이의 대체 서비스

<details>

<summary>정답 보기</summary>

**정답: B) 서비스들을 그룹화하고 통신을 관리하는 논리적 경계**

**설명:**
Service Network는 VPC Lattice의 핵심 구성 요소로, 여러 서비스를 논리적으로 그룹화하는 경계입니다. VPC를 Service Network에 연결(Associate)하면 해당 VPC의 리소스가 네트워크 내 서비스들과 통신할 수 있습니다. 하나의 Service Network에 여러 VPC(다른 계정 포함)를 연결할 수 있으며, 각 서비스에 대한 인증 정책과 접근 제어를 중앙에서 관리할 수 있습니다.
</details>

3. VPC Lattice와 AWS App Mesh의 차이점으로 올바른 것은?
   - A) VPC Lattice는 사이드카 프록시가 필요하지만 App Mesh는 필요없다
   - B) App Mesh는 사이드카 프록시 기반이고 VPC Lattice는 사이드카가 필요없다
   - C) VPC Lattice는 TCP만 지원하고 App Mesh는 HTTP만 지원한다
   - D) 두 서비스는 동일한 아키텍처를 사용한다

<details>

<summary>정답 보기</summary>

**정답: B) App Mesh는 사이드카 프록시 기반이고 VPC Lattice는 사이드카가 필요없다**

**설명:**
AWS App Mesh는 Envoy 사이드카 프록시를 각 서비스 파드에 주입하여 트래픽을 제어하는 서비스 메시입니다. 반면 VPC Lattice는 AWS에서 완전히 관리하는 서비스로, 사이드카 프록시 없이도 서비스 간 통신, 라우팅, 인증을 제공합니다. 이로 인해 VPC Lattice는 운영 복잡성이 낮고 리소스 오버헤드가 적지만, App Mesh가 제공하는 세밀한 트래픽 제어 기능은 일부 제한될 수 있습니다.
</details>

4. EKS와 VPC Lattice를 통합할 때 사용하는 Kubernetes API는?
   - A) Ingress API
   - B) Service API
   - C) Gateway API
   - D) NetworkPolicy API

<details>

<summary>정답 보기</summary>

**정답: C) Gateway API**

**설명:**
AWS Gateway API Controller는 Kubernetes Gateway API 리소스(GatewayClass, Gateway, HTTPRoute 등)를 VPC Lattice 리소스로 변환합니다. Gateway API는 Kubernetes의 차세대 인그레스 명세로, Ingress보다 더 풍부한 기능과 확장성을 제공합니다. GatewayClass로 amazon-vpc-lattice 컨트롤러를 지정하고, Gateway와 HTTPRoute를 생성하면 컨트롤러가 자동으로 VPC Lattice Service와 Target Group을 생성합니다.
</details>

5. VPC Lattice 서비스의 DNS 이름 형식으로 올바른 것은?
   - A) service-name.region.amazonaws.com
   - B) service-name.vpc-lattice-svcs.region.on.aws
   - C) service-name.internal.aws
   - D) service-name.lattice.region.aws

<details>

<summary>정답 보기</summary>

**정답: B) service-name.vpc-lattice-svcs.region.on.aws**

**설명:**
VPC Lattice 서비스는 자동으로 DNS 이름을 할당받습니다. 형식은 `<service-name>.<service-network-id>.vpc-lattice-svcs.<region>.on.aws`입니다. 이 DNS 이름은 Service Network에 연결된 모든 VPC에서 해석 가능합니다. 클라이언트는 이 DNS 이름으로 서비스에 접근하며, VPC Lattice가 내부적으로 적절한 대상으로 라우팅합니다. 커스텀 도메인을 사용하려면 Route 53 등에서 CNAME이나 Alias 레코드를 설정할 수 있습니다.
</details>

6. VPC Lattice에서 지원하는 인증 방식은?
   - A) API Key만
   - B) OAuth 2.0만
   - C) AWS IAM 또는 인증 없음
   - D) SAML만

<details>

<summary>정답 보기</summary>

**정답: C) AWS IAM 또는 인증 없음**

**설명:**
VPC Lattice는 두 가지 인증 모드를 지원합니다. AWS_IAM 모드에서는 요청에 SigV4(Signature Version 4) 서명이 필요하며, IAM 정책과 리소스 정책으로 접근을 제어합니다. NONE 모드에서는 인증 없이 모든 요청을 허용합니다. IAM 인증을 사용하면 어떤 IAM 역할/사용자가 어떤 서비스의 어떤 경로에 접근할 수 있는지 세밀하게 제어할 수 있습니다.
</details>

7. VPC Lattice의 Target Group에서 지원하는 대상 유형이 아닌 것은?
   - A) EC2 인스턴스
   - B) EKS 파드 (IP 타입)
   - C) Lambda 함수
   - D) RDS 데이터베이스

<details>

<summary>정답 보기</summary>

**정답: D) RDS 데이터베이스**

**설명:**
VPC Lattice Target Group은 EC2 인스턴스, IP 주소(EKS 파드 포함), Lambda 함수, ALB를 대상으로 지원합니다. RDS 데이터베이스는 HTTP/HTTPS 기반이 아닌 데이터베이스 프로토콜을 사용하므로 VPC Lattice의 대상이 될 수 없습니다. EKS 파드의 경우 IP 타입 Target Group을 사용하며, AWS Gateway API Controller가 파드 IP를 자동으로 등록/해제합니다.
</details>

8. VPC Lattice에서 가중치 기반 라우팅의 주요 사용 사례는?
   - A) 로드 밸런싱만
   - B) 카나리 배포 및 블루-그린 배포
   - C) 지역 기반 라우팅
   - D) 세션 고정(Sticky Session)

<details>

<summary>정답 보기</summary>

**정답: B) 카나리 배포 및 블루-그린 배포**

**설명:**
가중치 기반 라우팅은 여러 Target Group에 트래픽을 비율로 분산시킵니다. 카나리 배포에서는 새 버전에 10%의 트래픽을 보내 검증한 후 점진적으로 증가시킵니다. 블루-그린 배포에서는 100%를 블루에서 그린으로 한 번에 전환합니다. 예: `service-v1: weight 90, service-v2: weight 10`으로 설정하면 10%의 트래픽만 v2로 전달됩니다. 문제 발견 시 가중치를 조정하여 롤백할 수 있습니다.
</details>

## 단답형 문제

9. VPC Lattice의 크로스 계정 서비스 네트워크 공유 방법을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
AWS Resource Access Manager(RAM)를 사용하여 Service Network를 다른 AWS 계정이나 조직과 공유합니다.

**설명:**
크로스 계정 공유 프로세스:
1. **소유 계정**: RAM에서 Service Network 리소스 공유 생성
   ```bash
   aws ram create-resource-share \
     --name my-service-network-share \
     --resource-arns arn:aws:vpc-lattice:region:account:servicenetwork/sn-xxx \
     --principals 123456789012  # 대상 계정 ID
   ```
2. **대상 계정**: RAM 초대 수락
3. **대상 계정**: 자신의 VPC를 공유된 Service Network에 연결
4. 이후 대상 계정의 서비스도 해당 Service Network에 등록 가능

Organizations 사용 시 조직 전체에 자동 공유도 가능합니다.
</details>

10. VPC Lattice의 Health Check(상태 확인) 설정이 중요한 이유를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Health Check는 비정상 대상을 자동으로 트래픽 라우팅에서 제외하여 서비스 가용성을 보장합니다.

**설명:**
VPC Lattice의 Health Check 작동 방식:
1. **정기적 검사**: 설정된 간격(예: 30초)마다 대상의 헬스체크 엔드포인트에 요청
2. **임계값 기반 판단**: 연속 성공/실패 횟수(healthyThresholdCount/unhealthyThresholdCount)로 상태 결정
3. **자동 제외/복귀**: 비정상 대상은 트래픽에서 제외되고, 복구되면 자동 복귀
4. **설정 예시**:
   ```yaml
   healthCheck:
     enabled: true
     protocol: HTTP
     path: /health
     healthCheckIntervalSeconds: 30
     healthyThresholdCount: 5
     unhealthyThresholdCount: 2
     matcher:
       httpCode: "200-299"
   ```
적절한 Health Check 설정은 롤링 업데이트 중 다운타임을 방지하고, 장애 대상으로의 요청을 막아 사용자 경험을 보호합니다.
</details>

11. VPC Lattice와 Transit Gateway의 차이점을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Transit Gateway는 네트워크 계층(L3)에서 VPC 간 IP 라우팅을 제공하고, VPC Lattice는 애플리케이션 계층(L7)에서 서비스 기반 통신을 제공합니다.

**설명:**
주요 차이점:

| 관점 | Transit Gateway | VPC Lattice |
|------|-----------------|-------------|
| 추상화 수준 | 네트워크 (IP 기반) | 서비스 (이름 기반) |
| 라우팅 | IP 라우팅 테이블 | HTTP 경로/헤더 기반 |
| 프로토콜 | 모든 IP 트래픽 | HTTP/HTTPS/gRPC |
| 인증 | 보안 그룹, NACL | AWS IAM, 리소스 정책 |
| 가시성 | 네트워크 흐름 로그 | 애플리케이션 수준 메트릭/로그 |

Transit Gateway는 VPC 간 모든 IP 통신이 필요할 때 사용하고, VPC Lattice는 마이크로서비스 간 HTTP 기반 통신에 적합합니다. 두 서비스를 함께 사용할 수도 있습니다.
</details>

12. VPC Lattice에서 Auth Policy(인증 정책)의 역할과 적용 수준을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Auth Policy는 IAM 기반 접근 제어를 정의하며, Service Network 수준과 개별 Service 수준에서 적용됩니다.

**설명:**
Auth Policy의 적용 수준:
1. **Service Network 수준**: 네트워크 전체에 적용되는 기본 정책
   - 어떤 IAM 보안 주체가 네트워크에 연결할 수 있는지 제어
2. **Service 수준**: 개별 서비스에 적용되는 세부 정책
   - 어떤 보안 주체가 특정 서비스의 어떤 경로에 접근할 수 있는지 제어

정책 예시:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
    },
    "Action": "vpc-lattice-svcs:Invoke",
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "vpc-lattice-svcs:RequestPath": "/api/*"
      }
    }
  }]
}
```
이 정책은 MyAppRole이 /api/* 경로에만 접근할 수 있도록 제한합니다.
</details>

## 실습 문제

13. AWS Gateway API Controller를 EKS에 설치하기 위한 IAM 정책과 IRSA 설정을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. VPC Lattice 권한을 위한 IAM 정책 생성
cat <<EOF > vpc-lattice-controller-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc-lattice:*",
        "iam:CreateServiceLinkedRole",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeAvailabilityZones"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document file://vpc-lattice-controller-policy.json

# 2. IRSA를 사용한 서비스 계정 생성
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=aws-application-networking-system \
  --name=gateway-api-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/VPCLatticeControllerPolicy \
  --override-existing-serviceaccounts \
  --approve

# 3. AWS Gateway API Controller 설치
kubectl apply -f https://raw.githubusercontent.com/aws/aws-application-networking-k8s/main/files/controller-installation/deploy-v1.0.yaml
```

**설명:**
AWS Gateway API Controller는 Kubernetes 클러스터에서 Gateway API 리소스를 감시하고 VPC Lattice 리소스를 생성/관리합니다. IRSA(IAM Roles for Service Accounts)를 통해 컨트롤러 파드가 필요한 AWS API를 호출할 수 있는 권한을 얻습니다. 정책에는 vpc-lattice 작업, VPC/서브넷 조회, 로그 배달 권한이 포함됩니다.
</details>

14. VPC Lattice를 사용하여 두 서비스 간 가중치 기반 라우팅(90:10)을 구성하는 HTTPRoute를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
# GatewayClass 정의
apiVersion: gateway.networking.k8s.io/v1beta1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
# Gateway 정의
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: default
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
# 가중치 기반 라우팅 HTTPRoute
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: weighted-routing
  namespace: default
spec:
  parentRefs:
  - name: my-gateway
    sectionName: http
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 80
      weight: 90
    - name: service-canary
      port: 80
      weight: 10
---
# Stable 서비스
apiVersion: v1
kind: Service
metadata:
  name: service-stable
spec:
  selector:
    app: myapp
    version: stable
  ports:
  - port: 80
    targetPort: 8080
---
# Canary 서비스
apiVersion: v1
kind: Service
metadata:
  name: service-canary
spec:
  selector:
    app: myapp
    version: canary
  ports:
  - port: 80
    targetPort: 8080
```

**설명:**
이 구성에서 `/api` 경로로 들어오는 트래픽의 90%는 service-stable로, 10%는 service-canary로 라우팅됩니다. AWS Gateway API Controller가 이 HTTPRoute를 감지하면 VPC Lattice에 두 개의 Target Group을 생성하고, 지정된 가중치로 트래픽을 분산하는 리스너 규칙을 설정합니다. 카나리 배포 검증 후 가중치를 점진적으로 조정할 수 있습니다.
</details>

15. VPC Lattice 서비스에 대한 IAM 기반 Auth Policy를 작성하세요. (특정 IAM 역할만 /admin 경로 접근 허용)

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# VPC Lattice 서비스에 Auth Policy 적용
aws vpc-lattice put-auth-policy \
  --resource-identifier svc-0123456789abcdef0 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowGeneralAccess",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringNotEquals": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "AllowAdminAccess",
        "Effect": "Allow",
        "Principal": {
          "AWS": [
            "arn:aws:iam::123456789012:role/AdminRole",
            "arn:aws:iam::123456789012:role/DevOpsRole"
          ]
        },
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "DenyUnauthorizedAdmin",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          },
          "StringNotEquals": {
            "aws:PrincipalArn": [
              "arn:aws:iam::123456789012:role/AdminRole",
              "arn:aws:iam::123456789012:role/DevOpsRole"
            ]
          }
        }
      }
    ]
  }'
```

**Kubernetes Gateway API 방식:**
```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: secure-gateway
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-type: "AWS_IAM"
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vpc-lattice-auth-policy
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-policy: |
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "AWS": "arn:aws:iam::123456789012:role/AdminRole"
            },
            "Action": "vpc-lattice-svcs:Invoke",
            "Resource": "*"
          }
        ]
      }
data: {}
```

**설명:**
이 Auth Policy는 세 가지 규칙으로 구성됩니다:
1. **AllowGeneralAccess**: /admin/* 이외의 모든 경로에 대해 모든 보안 주체 허용
2. **AllowAdminAccess**: AdminRole과 DevOpsRole에게 /admin/* 경로 접근 허용
3. **DenyUnauthorizedAdmin**: 위 역할이 아닌 보안 주체의 /admin/* 접근을 명시적 거부

클라이언트는 SigV4로 요청에 서명해야 합니다. AWS SDK나 aws-sigv4 라이브러리를 사용하여 서명할 수 있습니다.
</details>

---

**점수 계산:**
- 13-15개 정답: 우수 (VPC Lattice 전문가 수준)
- 10-12개 정답: 양호 (실무 적용 가능)
- 7-9개 정답: 보통 (추가 학습 권장)
- 4-6개 정답: 기초 (기본 개념 복습 필요)
- 0-3개 정답: 미흡 (전체 내용 재학습 필요)
