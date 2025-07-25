# VPC Lattice 퀴즈

이 퀴즈는 Amazon VPC Lattice에 대한 이해도를 테스트합니다.

## 문제 1: VPC Lattice 기본 개념

<details>
<summary>Amazon VPC Lattice란 무엇이며 주요 특징은?</summary>

**답변:**
Amazon VPC Lattice는 AWS의 애플리케이션 네트워킹 서비스로, 서로 다른 VPC와 계정에 걸쳐 있는 서비스들을 안전하게 연결합니다.

**주요 특징:**
- **서비스 네트워크**: 논리적 경계 내에서 서비스 연결
- **크로스 VPC/계정**: 여러 VPC와 AWS 계정 간 연결
- **서비스 디스커버리**: 자동 서비스 검색 및 라우팅
- **보안 정책**: 세밀한 액세스 제어
- **로드 밸런싱**: 내장된 로드 밸런싱 기능
- **관찰성**: 상세한 메트릭 및 로깅
</details>

## 문제 2: 핵심 구성 요소

<details>
<summary>VPC Lattice의 주요 구성 요소는?</summary>

**답변:**
- **Service Network**: 서비스들을 그룹화하는 논리적 경계
- **Service**: 애플리케이션 또는 마이크로서비스
- **Target Group**: 서비스의 백엔드 리소스 그룹
- **Listener**: 서비스로 들어오는 트래픽을 처리
- **Rule**: 트래픽 라우팅 규칙
- **Auth Policy**: 서비스 액세스 권한 정책
- **Resource Policy**: 리소스 레벨 액세스 제어
</details>

## 문제 3: EKS 통합

<details>
<summary>VPC Lattice와 Amazon EKS를 통합하는 방법은?</summary>

**답변:**
```yaml
# AWS Gateway API Controller 설치
helm repo add eks-charts https://aws.github.io/eks-charts
helm install aws-gateway-controller eks-charts/aws-gateway-controller \
  --namespace aws-gateway-controller-system \
  --create-namespace

# Gateway 리소스 생성
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: my-hotel-gateway
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80

# HTTPRoute 생성
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: inventory-route
spec:
  parentRefs:
  - name: my-hotel-gateway
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /inventory
    backendRefs:
    - name: inventory-service
      port: 80
```
</details>

## 문제 4: 보안 정책

<details>
<summary>VPC Lattice에서 보안 정책을 구성하는 방법은?</summary>

**답변:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSpecificPrincipals",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::123456789012:role/MyServiceRole",
          "arn:aws:iam::123456789012:user/MyUser"
        ]
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "vpc-lattice-svcs:RequestMethod": ["GET", "POST"]
        },
        "IpAddress": {
          "aws:SourceIp": ["10.0.0.0/16", "192.168.1.0/24"]
        }
      }
    },
    {
      "Sid": "DenyUnauthorizedAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalTag/Department": ["Engineering", "DevOps"]
        }
      }
    }
  ]
}
```
</details>

## 문제 5: 트래픽 관리

<details>
<summary>VPC Lattice에서 트래픽 분할 및 라우팅을 구현하는 방법은?</summary>

**답변:**
```yaml
# 가중치 기반 트래픽 분할
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: canary-route
spec:
  parentRefs:
  - name: my-gateway
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: stable-service
      port: 80
      weight: 90
    - name: canary-service
      port: 80
      weight: 10

# 헤더 기반 라우팅
  - matches:
    - headers:
      - name: "X-User-Type"
        value: "premium"
    backendRefs:
    - name: premium-service
      port: 80

# 경로 기반 라우팅
  - matches:
    - path:
        type: Exact
        value: /admin
    backendRefs:
    - name: admin-service
      port: 80
```
</details>

## 문제 6: 모니터링 및 관찰성

<details>
<summary>VPC Lattice의 모니터링 및 로깅을 구성하는 방법은?</summary>

**답변:**
1. **CloudWatch 메트릭**:
   ```bash
   # 주요 메트릭
   - RequestCount: 요청 수
   - ResponseTime: 응답 시간
   - HTTPCode_Target_2XX_Count: 성공 응답
   - HTTPCode_Target_4XX_Count: 클라이언트 오류
   - HTTPCode_Target_5XX_Count: 서버 오류
   - ActiveConnectionCount: 활성 연결 수
   ```

2. **액세스 로깅 활성화**:
   ```bash
   aws vpc-lattice put-access-log-subscription \
     --resource-identifier sn-1234567890abcdef0 \
     --destination-arn arn:aws:s3:::my-access-logs-bucket
   ```

3. **CloudWatch 경보 설정**:
   ```json
   {
     "AlarmName": "VPCLattice-HighErrorRate",
     "MetricName": "HTTPCode_Target_5XX_Count",
     "Namespace": "AWS/VpcLattice",
     "Statistic": "Sum",
     "Period": 300,
     "EvaluationPeriods": 2,
     "Threshold": 10,
     "ComparisonOperator": "GreaterThanThreshold"
   }
   ```

4. **X-Ray 추적 통합**:
   ```yaml
   # 서비스에서 X-Ray 추적 활성화
   apiVersion: v1
   kind: Service
   metadata:
     annotations:
       vpc-lattice.amazonaws.com/enable-tracing: "true"
   ```

5. **로그 분석**:
   ```sql
   -- CloudWatch Logs Insights 쿼리
   fields @timestamp, sourceIp, targetIp, responseCode, responseTime
   | filter responseCode >= 400
   | stats count() by responseCode
   | sort count desc
   ```
</details>

---

**점수 계산:**
- 5-6개 정답: 우수 (VPC Lattice 전문가 수준)
- 3-4개 정답: 양호 (추가 학습 권장)
- 1-2개 정답: 보통 (기본 개념 복습 필요)
- 0개 정답: 미흡 (전체 내용 재학습 필요)
