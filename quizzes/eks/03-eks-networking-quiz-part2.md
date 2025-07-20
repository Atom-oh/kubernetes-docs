# Amazon EKS 네트워킹 퀴즈 (Part 2)

이 퀴즈는 Amazon EKS의 고급 네트워킹 개념, AWS Load Balancer Controller, Ingress 리소스, 서비스 메시 및 네트워크 보안에 대한 이해를 테스트합니다.

## 객관식 문제

### 1. AWS Load Balancer Controller가 Kubernetes Ingress 리소스를 위해 기본적으로 프로비저닝하는 AWS 로드 밸런서 유형은 무엇인가요?

A. Classic Load Balancer (CLB)  
B. Network Load Balancer (NLB)  
C. Application Load Balancer (ALB)  
D. Gateway Load Balancer (GWLB)  

<details>
<summary>정답 및 설명</summary>

**정답: C. Application Load Balancer (ALB)**

**설명:**
AWS Load Balancer Controller는 Kubernetes Ingress 리소스를 위해 기본적으로 Application Load Balancer(ALB)를 프로비저닝합니다. ALB는 HTTP/HTTPS 트래픽을 처리하는 Layer 7 로드 밸런서로, 경로 기반 라우팅, 호스트 기반 라우팅, TLS 종료 등의 기능을 제공하여 Ingress 리소스의 요구 사항을 충족합니다.

**주요 특징:**

1. **경로 기반 라우팅**: ALB는 URL 경로에 따라 트래픽을 다른 서비스로 라우팅할 수 있어, Ingress의 경로 기반 라우팅 규칙을 구현하는 데 적합합니다.

2. **호스트 기반 라우팅**: 여러 도메인을 단일 ALB에서 처리할 수 있어, 여러 호스트 규칙이 있는 Ingress를 지원합니다.

3. **TLS 종료**: ALB는 SSL/TLS 인증서를 관리하고 HTTPS 트래픽을 종료할 수 있습니다.

4. **WebSockets 지원**: ALB는 WebSockets 프로토콜을 지원하여 실시간 애플리케이션에 적합합니다.

5. **인증 통합**: Amazon Cognito 또는 OIDC와 통합하여 애플리케이션 수준의 인증을 제공할 수 있습니다.

**구성 예시:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
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

**주요 어노테이션:**

- `kubernetes.io/ingress.class: alb`: ALB Ingress Controller를 사용하도록 지정
- `alb.ingress.kubernetes.io/scheme: internet-facing`: 인터넷 연결 가능한 ALB 생성
- `alb.ingress.kubernetes.io/target-type: ip`: 파드 IP를 대상으로 사용 (instance 대신)
- `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: 리스너 포트 구성
- `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: SSL 인증서 지정

다른 옵션들의 문제점:
- **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller는 Ingress 리소스를 위해 CLB를 사용하지 않습니다. CLB는 레거시 로드 밸런서로 간주됩니다.
- **B. Network Load Balancer (NLB)**: NLB는 주로 Service 타입 LoadBalancer에 사용되며, Ingress 리소스에는 기본적으로 사용되지 않습니다.
- **D. Gateway Load Balancer (GWLB)**: GWLB는 네트워크 가상 어플라이언스를 위한 것으로, Kubernetes Ingress 리소스와 함께 사용되지 않습니다.
</details>

### 2. Amazon EKS에서 AWS Load Balancer Controller를 사용하여 내부 Application Load Balancer를 생성하기 위해 Ingress 리소스에 추가해야 하는 어노테이션은 무엇인가요?

A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`  
B. `alb.ingress.kubernetes.io/scheme: internal`  
C. `kubernetes.io/ingress.class: internal-alb`  
D. `aws-load-balancer-type: internal`  

<details>
<summary>정답 및 설명</summary>

**정답: B. `alb.ingress.kubernetes.io/scheme: internal`**

**설명:**
Amazon EKS에서 AWS Load Balancer Controller를 사용하여 내부 Application Load Balancer를 생성하기 위해서는 Ingress 리소스에 `alb.ingress.kubernetes.io/scheme: internal` 어노테이션을 추가해야 합니다. 이 어노테이션은 ALB가 VPC 내부에서만 접근 가능하도록 설정합니다.

**내부 ALB 구성 예시:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internal
spec:
  rules:
  - host: internal.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-service
            port:
              number: 80
```

**주요 고려 사항:**

1. **서브넷 선택**: 내부 ALB는 프라이빗 서브넷에 생성됩니다. 서브넷을 명시적으로 지정할 수 있습니다:
   ```yaml
   alb.ingress.kubernetes.io/subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
   ```

2. **보안 그룹**: 내부 ALB에 특정 보안 그룹을 적용할 수 있습니다:
   ```yaml
   alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
   ```

3. **인바운드 CIDR 제한**: 특정 CIDR 블록에서만 접근을 허용할 수 있습니다:
   ```yaml
   alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
   ```

4. **내부 DNS**: 내부 ALB는 VPC 내에서 Route 53 프라이빗 호스팅 영역과 통합할 수 있습니다:
   ```yaml
   alb.ingress.kubernetes.io/load-balancer-attributes: routing.http.drop_invalid_header_fields.enabled=true,access_logs.s3.enabled=true
   ```

**내부 ALB의 사용 사례:**

- 마이크로서비스 간 내부 통신
- 백엔드 API 서비스
- 관리 인터페이스
- 개발 및 테스트 환경
- 규제 요구 사항이 있는 워크로드

**AWS Load Balancer Controller 설치 확인:**
```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
```

다른 옵션들의 문제점:
- **A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`**: 이 어노테이션은 Service 타입 LoadBalancer에 사용되며, Ingress 리소스에는 적용되지 않습니다.
- **C. `kubernetes.io/ingress.class: internal-alb`**: 올바른 ingress.class는 'alb'이며, 'internal-alb'는 유효한 값이 아닙니다.
- **D. `aws-load-balancer-type: internal`**: 이러한 어노테이션은 존재하지 않습니다.
</details>

### 3. Amazon EKS에서 AWS Load Balancer Controller를 사용할 때, 파드 IP를 직접 대상으로 사용하도록 구성하는 어노테이션은 무엇인가요?

A. `alb.ingress.kubernetes.io/target-type: pod`  
B. `alb.ingress.kubernetes.io/target-type: ip`  
C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`  
D. `aws-load-balancer-target-node-labels: ip-mode=true`  

<details>
<summary>정답 및 설명</summary>

**정답: B. `alb.ingress.kubernetes.io/target-type: ip`**

**설명:**
Amazon EKS에서 AWS Load Balancer Controller를 사용할 때, 파드 IP를 직접 대상으로 사용하도록 구성하려면 `alb.ingress.kubernetes.io/target-type: ip` 어노테이션을 사용해야 합니다. 이 설정을 통해 로드 밸런서는 노드 IP 대신 파드 IP로 직접 트래픽을 라우팅합니다.

**대상 유형 옵션:**

1. **instance**: (기본값) 노드 IP와 NodePort를 사용하여 트래픽을 라우팅합니다.
2. **ip**: 파드 IP와 컨테이너 포트를 사용하여 트래픽을 직접 파드로 라우팅합니다.

**IP 모드 구성 예시:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

**IP 모드의 장점:**

1. **노드 장애 복원력**: 노드가 실패해도 다른 노드의 파드로 트래픽이 계속 라우팅됩니다.
2. **직접 라우팅**: NodePort를 통한 추가 홉 없이 파드로 직접 트래픽이 전달됩니다.
3. **Fargate 호환성**: AWS Fargate에서 실행되는 파드에 필요합니다.
4. **보안 그룹 통합**: 파드 수준에서 보안 그룹을 적용할 수 있습니다.

**IP 모드의 요구 사항:**

1. **VPC CNI**: Amazon VPC CNI 플러그인이 필요합니다.
2. **서브넷 구성**: 파드가 실행되는 서브넷이 로드 밸런서 서브넷과 라우팅 가능해야 합니다.
3. **보안 그룹 규칙**: 로드 밸런서의 보안 그룹이 파드 IP로의 트래픽을 허용해야 합니다.

**IP 모드와 instance 모드 비교:**

| 특성 | IP 모드 | Instance 모드 |
|------|---------|--------------|
| 대상 | 파드 IP | 노드 IP |
| 포트 | 컨테이너 포트 | NodePort |
| 트래픽 경로 | LB → 파드 | LB → 노드 → 파드 |
| 노드 장애 시 | 영향 없음 | 해당 노드의 파드 접근 불가 |
| 성능 | 더 나은 성능 | 추가 홉으로 인한 약간의 오버헤드 |
| Fargate 지원 | 지원 | 미지원 |

**추가 구성 옵션:**

```yaml
# 대상 그룹 속성 설정
alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30,stickiness.enabled=true

# 상태 확인 설정
alb.ingress.kubernetes.io/healthcheck-path: /health
alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
alb.ingress.kubernetes.io/success-codes: '200'
alb.ingress.kubernetes.io/healthy-threshold-count: '2'
alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
```

다른 옵션들의 문제점:
- **A. `alb.ingress.kubernetes.io/target-type: pod`**: 올바른 값은 'ip'이며, 'pod'는 유효한 값이 아닙니다.
- **C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`**: 이 어노테이션은 Service 타입 LoadBalancer에 사용되며, Ingress 리소스에는 적용되지 않습니다.
- **D. `aws-load-balancer-target-node-labels: ip-mode=true`**: 이러한 어노테이션은 존재하지 않습니다.
</details>

### 4. Amazon EKS에서 Kubernetes Service와 AWS PrivateLink를 통합하여 VPC 엔드포인트 서비스를 생성하는 데 사용되는 어노테이션은 무엇인가요?

A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb`  
B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"`  
C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`  
D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`  

<details>
<summary>정답 및 설명</summary>

**정답: C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`**

**설명:**
Amazon EKS에서 Kubernetes Service와 AWS PrivateLink를 통합하여 VPC 엔드포인트 서비스를 생성하려면 `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip` 어노테이션을 사용해야 합니다. 이 어노테이션은 IP 모드의 Network Load Balancer(NLB)를 생성하며, 이는 AWS PrivateLink와 통합하기 위한 필수 조건입니다.

**VPC 엔드포인트 서비스 구성 단계:**

1. **NLB-IP 모드로 Kubernetes Service 생성:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: my-app
```

2. **AWS CLI를 사용하여 VPC 엔드포인트 서비스 생성:**
```bash
# NLB ARN 가져오기
NLB_ARN=$(aws elbv2 describe-load-balancers --names $(kubectl get svc privatelink-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' | cut -d- -f1) --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# VPC 엔드포인트 서비스 생성
aws ec2 create-vpc-endpoint-service-configuration \
  --network-load-balancer-arns $NLB_ARN \
  --acceptance-required \
  --private-dns-name service.example.com
```

3. **VPC 엔드포인트 서비스 허용 목록 구성:**
```bash
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-id vpce-svc-0123456789abcdef0 \
  --add-allowed-principals arn:aws:iam::111122223333:root
```

**주요 고려 사항:**

1. **내부 NLB 요구 사항**: PrivateLink는 내부 NLB를 사용해야 하므로, `service.beta.kubernetes.io/aws-load-balancer-internal: "true"` 어노테이션도 필요합니다.

2. **IP 모드의 중요성**: NLB-IP 모드는 파드 IP를 직접 대상으로 사용하여 노드 장애에 대한 복원력을 제공합니다.

3. **서비스 이름 해석**: 프라이빗 DNS 이름을 구성하여 VPC 내에서 서비스 이름 해석을 간소화할 수 있습니다.

4. **접근 제어**: `acceptance-required` 플래그를 사용하여 엔드포인트 연결 요청을 수동으로 승인할 수 있습니다.

5. **네트워크 ACL 및 보안 그룹**: 적절한 네트워크 ACL 및 보안 그룹 규칙이 구성되어 있는지 확인해야 합니다.

**PrivateLink 통합의 이점:**

- **보안 강화**: 트래픽이 공용 인터넷을 통과하지 않고 AWS 네트워크 내에서 유지됩니다.
- **규정 준수**: 데이터 주권 및 규정 준수 요구 사항을 충족합니다.
- **간소화된 네트워킹**: VPC 피어링, Transit Gateway 또는 VPN 연결 없이 서비스에 접근할 수 있습니다.
- **확장성**: 수천 개의 VPC에서 서비스에 접근할 수 있습니다.

**클라이언트 측 구성:**
```bash
# VPC 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-0123456789abcdef0 \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-group-ids sg-0123456789abcdef0
```

다른 옵션들의 문제점:
- **A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb`**: 이 어노테이션은 인스턴스 모드의 NLB를 생성하며, PrivateLink와의 통합에 최적화되지 않았습니다.
- **B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"`**: 이러한 어노테이션은 존재하지 않습니다.
- **D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`**: 이러한 어노테이션은 존재하지 않습니다.
</details>

### 5. Amazon EKS에서 Kubernetes NetworkPolicy 리소스를 구현하기 위해 Amazon VPC CNI와 함께 사용할 수 있는 추가 구성 요소는 무엇인가요?

A. AWS Network Firewall  
B. Calico  
C. AWS Security Groups for Pods  
D. VPC Flow Logs  

<details>
<summary>정답 및 설명</summary>

**정답: B. Calico**

**설명:**
Amazon EKS에서 Kubernetes NetworkPolicy 리소스를 구현하기 위해 Amazon VPC CNI와 함께 사용할 수 있는 추가 구성 요소는 Calico입니다. Calico는 Kubernetes NetworkPolicy API를 지원하는 오픈 소스 네트워킹 및 네트워크 보안 솔루션으로, Amazon VPC CNI와 함께 작동하여 EKS 클러스터에서 세밀한 네트워크 정책을 적용할 수 있습니다.

**Calico 설치 및 구성:**

1. **Calico 설치:**
```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

2. **설치 확인:**
```bash
kubectl get pods -n calico-system
```

3. **기본 NetworkPolicy 예시:**
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

**Calico의 주요 기능:**

1. **Kubernetes NetworkPolicy 지원**: 표준 Kubernetes NetworkPolicy API를 완벽하게 구현합니다.

2. **확장된 정책 기능**: Calico의 GlobalNetworkPolicy 및 NetworkSet과 같은 사용자 정의 리소스를 통해 Kubernetes NetworkPolicy를 넘어선 고급 네트워크 정책을 제공합니다.

3. **세밀한 제어**: 프로토콜, 포트, CIDR 블록, 서비스 계정 등을 기반으로 트래픽을 필터링할 수 있습니다.

4. **로깅 및 모니터링**: 네트워크 정책 위반을 로깅하고 모니터링할 수 있습니다.

5. **호스트 엔드포인트 보호**: Kubernetes 노드 자체에 대한 네트워크 정책을 적용할 수 있습니다.

**Calico 고급 정책 예시:**
```yaml
# GlobalNetworkPolicy 예시 (클러스터 전체 정책)
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-cluster-internal-traffic
spec:
  selector: all()
  types:
  - Ingress
  - Egress
  ingress:
  - action: Allow
    source:
      selector: all()
  egress:
  - action: Allow
    destination:
      selector: all()

# 특정 IP 범위에 대한 액세스 제한
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-services
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.0/24
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-services
  namespace: app
spec:
  podSelector:
    matchLabels:
      role: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    - ipBlock:
        cidr: 198.51.100.0/24
```

**Amazon VPC CNI와 Calico의 통합:**

1. **네트워크 모드**: Calico는 Amazon VPC CNI와 함께 사용할 때 오버레이 모드가 아닌 정책 전용 모드로 작동합니다.

2. **성능**: Amazon VPC CNI의 네이티브 VPC 네트워킹 성능을 유지하면서 Calico의 네트워크 정책 기능을 활용할 수 있습니다.

3. **호환성**: Calico는 Amazon VPC CNI의 모든 기능(프리픽스 위임, 사용자 지정 네트워킹 등)과 호환됩니다.

4. **업그레이드**: Calico와 Amazon VPC CNI는 독립적으로 업그레이드할 수 있습니다.

**모범 사례:**

- 기본 거부 정책으로 시작하여 필요한 통신만 명시적으로 허용합니다.
- 네임스페이스 간 통신에 대한 명확한 정책을 정의합니다.
- 정책을 적용하기 전에 로깅 모드에서 테스트합니다.
- 클러스터 필수 구성 요소에 대한 통신을 항상 허용합니다.
- 정기적으로 정책을 검토하고 업데이트합니다.

다른 옵션들의 문제점:
- **A. AWS Network Firewall**: AWS Network Firewall은 VPC 수준의 방화벽 서비스로, Kubernetes NetworkPolicy와 직접적인 통합이 없습니다.
- **C. AWS Security Groups for Pods**: Security Groups for Pods는 파드에 AWS 보안 그룹을 적용하는 기능이지만, Kubernetes NetworkPolicy API를 구현하지는 않습니다.
- **D. VPC Flow Logs**: VPC Flow Logs는 네트워크 트래픽을 모니터링하는 도구로, 네트워크 정책을 적용하지는 않습니다.
</details>
## 단답형 문제

### 6. Amazon EKS에서 AWS Load Balancer Controller를 사용하여 Application Load Balancer를 생성할 때, 특정 보안 그룹을 할당하는 어노테이션은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답:**
`alb.ingress.kubernetes.io/security-groups: sg-xxxx,sg-yyyy`

**상세 설명:**

AWS Load Balancer Controller를 사용하여 Application Load Balancer(ALB)를 생성할 때, `alb.ingress.kubernetes.io/security-groups` 어노테이션을 사용하여 특정 보안 그룹을 할당할 수 있습니다. 이 어노테이션은 ALB에 연결할 보안 그룹의 ID를 쉼표로 구분하여 지정합니다.

**구현 방법:**

1. **보안 그룹 ID 지정:**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: example-ingress
     annotations:
       kubernetes.io/ingress.class: alb
       alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0,sg-0123456789abcdef1
   spec:
     rules:
     - http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: example-service
               port:
                 number: 80
   ```

2. **보안 그룹 이름 지정 (대체 방법):**
   ```yaml
   alb.ingress.kubernetes.io/security-groups: my-security-group-name
   ```

3. **보안 그룹 자동 생성:**
   ```yaml
   alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
   ```

**주요 고려 사항:**

1. **보안 그룹 규칙:**
   - 인바운드 규칙: 클라이언트 트래픽을 허용해야 합니다 (일반적으로 HTTP/80, HTTPS/443).
   - 아웃바운드 규칙: 대상 그룹(파드 또는 노드)으로의 트래픽을 허용해야 합니다.

2. **기본 동작:**
   어노테이션을 지정하지 않으면, AWS Load Balancer Controller는 자동으로 보안 그룹을 생성하고 필요한 규칙을 구성합니다.

3. **권한 요구 사항:**
   AWS Load Balancer Controller의 IAM 역할에는 다음 권한이 필요합니다:
   - ec2:CreateSecurityGroup
   - ec2:DeleteSecurityGroup
   - ec2:DescribeSecurityGroups
   - ec2:AuthorizeSecurityGroupIngress
   - ec2:RevokeSecurityGroupIngress

4. **보안 그룹 관리:**
   ```yaml
   # 컨트롤러가 보안 그룹 규칙을 관리하도록 설정
   alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
   ```

5. **태그 지정:**
   생성된 보안 그룹에 태그를 추가할 수 있습니다:
   ```yaml
   alb.ingress.kubernetes.io/tags: Environment=prod,Team=devops
   ```

**모범 사례:**

1. **최소 권한 원칙:**
   필요한 트래픽만 허용하는 제한적인 보안 그룹 규칙을 사용합니다.

2. **보안 그룹 재사용:**
   여러 Ingress 리소스에서 동일한 보안 그룹을 재사용하여 관리를 간소화합니다.

3. **문서화:**
   사용된 보안 그룹과 해당 규칙을 문서화하여 추적합니다.

4. **정기적인 검토:**
   보안 그룹 규칙을 정기적으로 검토하여 불필요한 액세스를 제거합니다.

5. **모니터링:**
   거부된 연결을 모니터링하여 보안 그룹 규칙의 효과를 평가합니다.

**관련 어노테이션:**

- **인바운드 CIDR 제한:**
  ```yaml
  alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
  ```

- **보안 그룹 태그:**
  ```yaml
  alb.ingress.kubernetes.io/load-balancer-attributes: load_balancing.cross_zone.enabled=true
  ```

- **SSL 정책:**
  ```yaml
  alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
  ```

AWS Load Balancer Controller를 사용하면 Kubernetes Ingress 리소스를 통해 ALB의 보안 그룹을 세밀하게 제어할 수 있으며, 이를 통해 클러스터의 네트워크 보안 태세를 강화할 수 있습니다.
</details>

### 7. Amazon EKS에서 Kubernetes Service 리소스를 Network Load Balancer로 노출할 때, 클라이언트 IP 주소를 보존하기 위한 어노테이션은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답:**
`service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`

**상세 설명:**

Amazon EKS에서 Kubernetes Service 리소스를 Network Load Balancer(NLB)로 노출할 때, 클라이언트 IP 주소를 보존하기 위해서는 `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true` 어노테이션을 사용해야 합니다. 이 설정은 NLB가 원본 클라이언트 IP 주소를 유지하도록 합니다.

**구현 방법:**

1. **기본 NLB 서비스 구성:**
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: example-service
     annotations:
       service.beta.kubernetes.io/aws-load-balancer-type: nlb
       service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
   spec:
     type: LoadBalancer
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: example
   ```

2. **IP 모드 NLB와 함께 사용:**
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: example-service
     annotations:
       service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
       service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
   spec:
     type: LoadBalancer
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: example
   ```

**클라이언트 IP 보존의 중요성:**

1. **보안 및 액세스 제어:**
   - 클라이언트 IP 기반 액세스 제어 구현
   - 의심스러운 IP 주소 차단
   - IP 기반 속도 제한 적용

2. **로깅 및 감사:**
   - 요청 소스 추적
   - 보안 이벤트 조사
   - 규정 준수 요구 사항 충족

3. **지리적 위치 기반 기능:**
   - 지역별 콘텐츠 제공
   - 지리적 분석 수행

**작동 방식:**

1. **Instance 모드 (aws-load-balancer-type: nlb):**
   - TCP 트래픽의 경우 클라이언트 IP가 자동으로 보존됩니다.
   - UDP 트래픽의 경우 preserve_client_ip.enabled=true 설정이 필요합니다.

2. **IP 모드 (aws-load-balancer-type: nlb-ip):**
   - TCP 및 UDP 트래픽 모두 preserve_client_ip.enabled=true 설정이 필요합니다.

**제한 사항 및 고려 사항:**

1. **프록시 프로토콜:**
   클라이언트 IP 보존은 프록시 프로토콜을 사용하지 않고 직접 패킷 라우팅을 통해 이루어집니다.

2. **대상 그룹 유형:**
   - Instance 모드: 노드 IP와 NodePort를 사용합니다.
   - IP 모드: 파드 IP와 포트를 직접 사용합니다.

3. **성능 영향:**
   클라이언트 IP 보존은 약간의 성능 오버헤드를 발생시킬 수 있습니다.

4. **호환성:**
   일부 레거시 애플리케이션은 클라이언트 IP 보존과 호환되지 않을 수 있습니다.

**애플리케이션에서 클라이언트 IP 액세스:**

1. **HTTP 애플리케이션:**
   ```python
   # Python Flask 예시
   from flask import Flask, request
   
   app = Flask(__name__)
   
   @app.route('/')
   def index():
       client_ip = request.remote_addr
       return f"Your IP address is: {client_ip}"
   ```

2. **TCP/UDP 애플리케이션:**
   ```go
   // Go 예시
   package main
   
   import (
       "fmt"
       "net"
   )
   
   func handleConnection(conn net.Conn) {
       addr := conn.RemoteAddr().String()
       fmt.Printf("Client connected from: %s\n", addr)
       // ...
   }
   ```

**관련 어노테이션:**

- **내부 NLB 구성:**
  ```yaml
  service.beta.kubernetes.io/aws-load-balancer-internal: "true"
  ```

- **교차 영역 로드 밸런싱:**
  ```yaml
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: load_balancing.cross_zone.enabled=true
  ```

- **TCP 연결 유지:**
  ```yaml
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true,deregistration_delay.timeout_seconds=30
  ```

클라이언트 IP 보존은 보안, 로깅, 액세스 제어 등 다양한 용도로 중요하며, 적절한 어노테이션을 사용하여 EKS 클러스터에서 쉽게 구성할 수 있습니다.
</details>

### 8. Amazon EKS에서 Kubernetes Ingress 리소스에 AWS WAF(Web Application Firewall)를 연결하기 위한 어노테이션은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답:**
`alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:region:account-id:global/webacl/name/id`

**상세 설명:**

Amazon EKS에서 Kubernetes Ingress 리소스에 AWS WAF(Web Application Firewall)를 연결하기 위해서는 `alb.ingress.kubernetes.io/wafv2-acl-arn` 어노테이션을 사용해야 합니다. 이 어노테이션은 AWS Load Balancer Controller가 생성하는 Application Load Balancer(ALB)에 AWS WAF WebACL을 연결합니다.

**구현 방법:**

1. **AWS WAF WebACL 생성:**
   먼저 AWS Management Console, AWS CLI 또는 AWS CloudFormation을 사용하여 WAF WebACL을 생성합니다.
   ```bash
   # AWS CLI 예시
   aws wafv2 create-web-acl \
     --name "eks-ingress-protection" \
     --scope "REGIONAL" \
     --default-action Allow={} \
     --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-protection \
     --region us-west-2
   ```

2. **Ingress 리소스에 WAF WebACL ARN 지정:**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: example-ingress
     annotations:
       kubernetes.io/ingress.class: alb
       alb.ingress.kubernetes.io/scheme: internet-facing
       alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef
   spec:
     rules:
     - host: example.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: example-service
               port:
                 number: 80
   ```

**AWS WAF의 주요 보호 기능:**

1. **일반적인 웹 취약점 방어:**
   - SQL 인젝션 공격
   - 크로스 사이트 스크립팅(XSS)
   - 경로 순회 공격
   - 명령어 인젝션

2. **봇 트래픽 제어:**
   - 악성 봇 차단
   - 스크래핑 방지
   - 자격 증명 스터핑 공격 방지

3. **속도 제한:**
   - DDoS 공격 완화
   - 브루트 포스 공격 방지

4. **지리적 제한:**
   - 특정 국가 또는 지역에서의 액세스 제한

5. **IP 평판 필터링:**
   - 알려진 악성 IP 주소 차단

**AWS WAF 규칙 그룹 예시:**

1. **AWS 관리형 규칙:**
   - AWS Core rule set (CRS)
   - SQL 데이터베이스 규칙
   - Linux 운영 체제 규칙
   - PHP 애플리케이션 규칙

2. **사용자 지정 규칙:**
   ```json
   {
     "Name": "block-specific-uri-paths",
     "Priority": 1,
     "Action": { "Block": {} },
     "VisibilityConfig": {
       "SampledRequestsEnabled": true,
       "CloudWatchMetricsEnabled": true,
       "MetricName": "block-specific-uri-paths"
     },
     "Statement": {
       "ByteMatchStatement": {
         "SearchString": "/admin",
         "FieldToMatch": { "UriPath": {} },
         "TextTransformations": [
           { "Priority": 0, "Type": "NONE" }
         ],
         "PositionalConstraint": "STARTS_WITH"
       }
     }
   }
   ```

**모니터링 및 로깅:**

1. **CloudWatch 로그 활성화:**
   ```yaml
   alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
   ```

2. **WAF 로깅 구성:**
   ```bash
   aws wafv2 put-logging-configuration \
     --logging-configuration ResourceArn=arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef,LogDestinationConfigs=arn:aws:firehose:us-west-2:111122223333:deliverystream/aws-waf-logs \
     --region us-west-2
   ```

**권한 요구 사항:**

AWS Load Balancer Controller의 IAM 역할에는 다음 권한이 필요합니다:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "wafv2:AssociateWebACL",
        "wafv2:DisassociateWebACL",
        "wafv2:GetWebACL",
        "wafv2:GetWebACLForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

**모범 사례:**

1. **다층 방어:**
   WAF를 네트워크 보안, 인증, 권한 부여 등 다른 보안 제어와 함께 사용합니다.

2. **정기적인 규칙 업데이트:**
   새로운 위협에 대응하기 위해 WAF 규칙을 정기적으로 검토하고 업데이트합니다.

3. **로깅 및 모니터링:**
   WAF 로그를 분석하여 공격 패턴을 식별하고 규칙을 개선합니다.

4. **테스트:**
   프로덕션 환경에 적용하기 전에 WAF 규칙을 테스트 환경에서 검증합니다.

5. **카운트 모드:**
   새 규칙을 처음 배포할 때는 차단 대신 카운트 모드로 설정하여 오탐을 모니터링합니다.

AWS WAF와 EKS Ingress의 통합은 애플리케이션 보안을 강화하는 강력한 방법이며, 적절한 어노테이션을 사용하여 쉽게 구성할 수 있습니다.
</details>
## 실습 문제

### 9. Amazon EKS 클러스터에서 AWS Load Balancer Controller를 사용하여 Application Load Balancer를 생성하고, 특정 경로에 따라 트래픽을 다른 서비스로 라우팅하는 Ingress 리소스를 작성하세요.

<details>
<summary>정답 및 설명</summary>

**정답:**
다음은 AWS Load Balancer Controller를 사용하여 Application Load Balancer를 생성하고, 특정 경로에 따라 트래픽을 다른 서비스로 라우팅하는 Ingress 리소스입니다:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  namespace: default
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-service
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

**상세 설명:**

1. **Ingress 리소스 구성 요소 설명**:

   - **metadata.annotations**: AWS Load Balancer Controller에 대한 구성 옵션을 지정합니다.
     - `kubernetes.io/ingress.class: alb`: AWS Load Balancer Controller를 사용하도록 지정합니다.
     - `alb.ingress.kubernetes.io/scheme: internet-facing`: 인터넷에서 접근 가능한 ALB를 생성합니다.
     - `alb.ingress.kubernetes.io/target-type: ip`: 파드 IP를 대상으로 사용합니다.
     - `alb.ingress.kubernetes.io/listen-ports`: HTTP(80)와 HTTPS(443) 포트를 모두 리스닝합니다.
     - `alb.ingress.kubernetes.io/certificate-arn`: HTTPS에 사용할 ACM 인증서를 지정합니다.
     - `alb.ingress.kubernetes.io/ssl-redirect`: HTTP 트래픽을 HTTPS로 리디렉션합니다.
     - `alb.ingress.kubernetes.io/healthcheck-*`: 상태 확인 설정을 구성합니다.

   - **spec.rules**: 호스트 및 경로 기반 라우팅 규칙을 정의합니다.
     - `/api` 경로는 `api-service`로 라우팅됩니다.
     - `/admin` 경로는 `admin-service`로 라우팅됩니다.
     - `/`(루트) 경로는 `frontend-service`로 라우팅됩니다.

2. **구현 단계**:

   a. **필수 서비스 생성**:
   ```yaml
   # api-service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: api-service
   spec:
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: api
   ---
   # admin-service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: admin-service
   spec:
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: admin
   ---
   # frontend-service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: frontend-service
   spec:
     ports:
     - port: 80
       targetPort: 8080
     selector:
       app: frontend
   ```

   b. **서비스에 대한 배포 생성**:
   ```yaml
   # api-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: api-deployment
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: api
     template:
       metadata:
         labels:
           app: api
       spec:
         containers:
         - name: api
           image: nginx
           ports:
           - containerPort: 8080
           readinessProbe:
             httpGet:
               path: /health
               port: 8080
   ```
   (admin 및 frontend 배포에 대해서도 유사한 구성 필요)

   c. **AWS Load Balancer Controller 설치 확인**:
   ```bash
   kubectl get deployment -n kube-system aws-load-balancer-controller
   ```

   d. **Ingress 리소스 적용**:
   ```bash
   kubectl apply -f multi-path-ingress.yaml
   ```

   e. **Ingress 상태 확인**:
   ```bash
   kubectl get ingress multi-path-ingress
   ```

3. **테스트 방법**:

   a. **DNS 설정**:
   Ingress가 생성한 ALB의 DNS 이름을 가져옵니다:
   ```bash
   kubectl get ingress multi-path-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
   ```
   
   이 DNS 이름을 `example.com`에 대한 CNAME 레코드로 설정합니다.

   b. **경로별 라우팅 테스트**:
   ```bash
   # API 서비스 테스트
   curl https://example.com/api
   
   # 관리자 서비스 테스트
   curl https://example.com/admin
   
   # 프론트엔드 서비스 테스트
   curl https://example.com/
   ```

4. **주의 사항 및 고려 사항**:

   a. **SSL 인증서**:
   HTTPS를 사용하려면 유효한 SSL 인증서가 필요합니다. AWS Certificate Manager(ACM)에서 인증서를 생성하고 ARN을 어노테이션에 지정합니다.

   b. **IAM 권한**:
   AWS Load Balancer Controller에는 ALB 및 관련 리소스를 생성하고 관리하기 위한 적절한 IAM 권한이 필요합니다.

   c. **상태 확인**:
   각 서비스는 상태 확인 엔드포인트(`/health`)를 제공해야 합니다.

   d. **대상 그룹 설정**:
   `target-type: ip`를 사용하면 파드 IP가 직접 대상으로 사용됩니다. 이는 Fargate 파드나 노드 장애에 대한 복원력을 제공합니다.

   e. **보안 그룹**:
   필요한 경우 ALB에 특정 보안 그룹을 적용할 수 있습니다:
   ```yaml
   alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
   ```

5. **추가 구성 옵션**:

   a. **세션 고정성 활성화**:
   ```yaml
   alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true,stickiness.lb_cookie.duration_seconds=86400
   ```

   b. **액세스 로그 활성화**:
   ```yaml
   alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
   ```

   c. **IP 기반 제한**:
   ```yaml
   alb.ingress.kubernetes.io/inbound-cidrs: 192.168.0.0/16,10.0.0.0/8
   ```

   d. **가중치 기반 라우팅**:
   ```yaml
   alb.ingress.kubernetes.io/actions.weighted-routing: >
     {"Type":"forward","ForwardConfig":{"TargetGroups":[{"ServiceName":"service-v1","ServicePort":"80","Weight":80},{"ServiceName":"service-v2","ServicePort":"80","Weight":20}]}}
   ```

AWS Load Balancer Controller와 Ingress 리소스를 사용하면 EKS 클러스터에서 복잡한 라우팅 규칙을 구현할 수 있으며, ALB의 다양한 기능을 활용하여 애플리케이션의 가용성, 확장성 및 보안을 향상시킬 수 있습니다.
</details>

## 고급 문제

### 10. Amazon EKS 클러스터에서 서비스 메시(예: Istio, AWS App Mesh)를 구현할 때의 주요 고려 사항과 네트워킹 아키텍처 변화를 설명하세요. 또한, 서비스 메시가 EKS의 기본 네트워킹 모델과 어떻게 통합되는지 설명하세요.

<details>
<summary>정답 및 설명</summary>

**정답:**
Amazon EKS 클러스터에서 서비스 메시(예: Istio, AWS App Mesh)를 구현할 때의 주요 고려 사항과 네트워킹 아키텍처 변화, 그리고 서비스 메시가 EKS의 기본 네트워킹 모델과 어떻게 통합되는지에 대한 설명은 다음과 같습니다:

## 1. 서비스 메시 개요 및 주요 구성 요소

**서비스 메시란?**
서비스 메시는 마이크로서비스 간의 통신을 관리하는 인프라 계층으로, 서비스 디스커버리, 트래픽 관리, 보안, 관찰 가능성 등의 기능을 제공합니다.

**주요 구성 요소:**

1. **데이터 플레인**:
   - 사이드카 프록시(일반적으로 Envoy)가 각 파드에 주입됩니다.
   - 모든 인바운드 및 아웃바운드 트래픽을 가로채고 처리합니다.

2. **컨트롤 플레인**:
   - 정책 및 구성을 관리합니다.
   - 데이터 플레인 프록시를 구성합니다.
   - 서비스 디스커버리 및 라우팅 정보를 제공합니다.

## 2. EKS 네트워킹 아키텍처 변화

**기본 EKS 네트워킹 모델:**
- Amazon VPC CNI를 사용하여 파드에 VPC IP 주소를 할당합니다.
- 파드는 VPC 내에서 직접 통신합니다.
- Kubernetes Service 리소스가 서비스 디스커버리 및 로드 밸런싱을 제공합니다.

**서비스 메시 도입 후 변화:**

1. **트래픽 흐름 변경**:
   ```
   기본 EKS: 클라이언트 → 서비스 → 대상 파드
   서비스 메시: 클라이언트 → 클라이언트 사이드카 → 서비스 → 대상 사이드카 → 대상 파드
   ```

2. **네트워크 토폴로지**:
   - 각 파드에 사이드카 컨테이너가 추가됩니다.
   - 파드 내 로컬 네트워크를 통해 애플리케이션과 사이드카가 통신합니다.
   - 사이드카 간 통신은 여전히 VPC CNI를 통해 이루어집니다.

3. **포트 할당**:
   - 사이드카 프록시는 추가 포트를 사용합니다(관리, 메트릭, 상태 확인 등).
   - 파드 내에서 포트 리디렉션이 발생합니다.

## 3. 주요 서비스 메시 옵션 비교

### Istio

**아키텍처 통합:**
```yaml
# Istio 사이드카 주입 예시
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        sidecar.istio.io/inject: "true"  # 사이드카 자동 주입
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**네트워킹 기능:**
- 고급 트래픽 관리(가중치 기반 라우팅, 카나리 배포)
- 서킷 브레이커 및 결함 주입
- mTLS를 통한 서비스 간 암호화
- 세분화된 액세스 제어

**EKS 통합 고려 사항:**
- 리소스 요구 사항이 높음(특히 컨트롤 플레인)
- Fargate와의 호환성 제한
- 복잡한 설정 및 관리

### AWS App Mesh

**아키텍처 통합:**
```yaml
# App Mesh 사이드카 주입 예시
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        appmesh.k8s.aws/mesh: my-mesh  # App Mesh 메시 이름
        appmesh.k8s.aws/virtualNode: example-vn  # 가상 노드 이름
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**네트워킹 기능:**
- AWS 서비스와의 원활한 통합
- 교차 계정 및 하이브리드 메시 지원
- AWS X-Ray와의 통합
- 상대적으로 간단한 설정

**EKS 통합 고려 사항:**
- AWS 서비스와의 통합이 우수함
- Fargate와 호환됨
- 일부 고급 기능이 제한적일 수 있음

## 4. 네트워킹 고려 사항

### 성능 영향

1. **지연 시간**:
   - 사이드카 프록시로 인한 추가 홉으로 약간의 지연 시간 증가(일반적으로 <10ms)
   - 최적화 기법:
     ```yaml
     # Istio 예시: 프록시 리소스 최적화
     apiVersion: v1
     kind: ConfigMap
     metadata:
       name: istio-sidecar-injector
       namespace: istio-system
     data:
       values: |-
         pilot:
           resources:
             requests:
               cpu: 500m
               memory: 2048Mi
     ```

2. **리소스 사용량**:
   - 각 파드에 대한 추가 CPU 및 메모리 오버헤드(일반적으로 10-15%)
   - 노드 밀도 감소 가능성

### 네트워크 정책 통합

1. **Kubernetes NetworkPolicy와의 관계**:
   - 서비스 메시는 L7 정책을 제공하는 반면, NetworkPolicy는 L3/L4 정책을 제공합니다.
   - 두 정책 유형을 함께 사용하여 심층 방어를 구현할 수 있습니다.

2. **정책 예시**:
   ```yaml
   # Istio 인증 정책
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ---
   # Kubernetes NetworkPolicy
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-same-namespace
   spec:
     podSelector: {}
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             kubernetes.io/metadata.name: default
   ```

## 5. 서비스 메시 구현 단계

### 1. 사전 요구 사항 확인

- 클러스터 버전 호환성 확인
- 리소스 요구 사항 평가
- 네트워킹 모델 검토

### 2. 컨트롤 플레인 설치

**Istio 예시:**
```bash
istioctl install --set profile=default
```

**App Mesh 예시:**
```bash
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace
```

### 3. 사이드카 주입 구성

**자동 주입:**
```yaml
# 네임스페이스에 레이블 추가
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    istio-injection: enabled  # Istio
    appmesh.k8s.aws/sidecarInjectorWebhook: enabled  # App Mesh
```

### 4. 서비스 메시 리소스 정의

**Istio 가상 서비스 및 대상 규칙:**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**App Mesh 가상 서비스 및 가상 라우터:**
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: reviews
  namespace: my-app
spec:
  awsName: reviews.my-app.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: reviews-router
---
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: reviews-router
  namespace: my-app
spec:
  listeners:
    - portMapping:
        port: 9080
        protocol: http
  routes:
    - name: reviews-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: reviews-v1
              weight: 90
            - virtualNodeRef:
                name: reviews-v2
              weight: 10
```

## 6. 모니터링 및 관찰 가능성

### 메트릭 수집

**Prometheus 통합:**
```yaml
# Istio Prometheus 구성
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  addonComponents:
    prometheus:
      enabled: true
```

### 분산 추적

**X-Ray 통합 (App Mesh):**
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  serviceDiscovery:
    ipPreference: IPv4_PREFERRED
  egressFilter:
    type: ALLOW_ALL
  tracing:
    awsXRay:
      logLevel: INFO
```

## 7. 서비스 메시 도입 모범 사례

1. **점진적 도입**:
   - 비즈니스에 중요하지 않은 워크로드부터 시작
   - 단계적으로 확장

2. **리소스 계획**:
   - 노드 크기 및 수 증가 고려
   - 컨트롤 플레인에 전용 노드 그룹 사용

3. **네트워킹 최적화**:
   - 불필요한 사이드카 주입 방지
   - 적절한 타임아웃 및 재시도 정책 구성

4. **보안 강화**:
   - mTLS 점진적 도입
   - 최소 권한 원칙 적용

5. **모니터링 전략**:
   - 서비스 메시 도입 전후 성능 비교
   - 주요 메트릭 대시보드 구성

## 8. EKS 특화 고려 사항

1. **Fargate 호환성**:
   - Istio: 제한된 지원 (일부 기능 사용 불가)
   - App Mesh: 완전 지원

2. **AWS Load Balancer Controller 통합**:
   - 인그레스 게이트웨이와 ALB 통합:
     ```yaml
     apiVersion: networking.k8s.io/v1
     kind: Ingress
     metadata:
       annotations:
         kubernetes.io/ingress.class: alb
         alb.ingress.kubernetes.io/scheme: internet-facing
         alb.ingress.kubernetes.io/target-type: ip
     ```

3. **IAM 역할 및 권한**:
   - App Mesh 컨트롤러에 필요한 IAM 권한:
     - appmesh:*
     - servicediscovery:*
     - cloudmap:*

4. **VPC CNI 설정**:
   - 서비스 메시로 인한 추가 ENI 및 IP 주소 요구 사항 고려
   - 프리픽스 위임 활성화 권장:
     ```bash
     kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
     ```

## 9. 서비스 메시 선택 가이드

| 요소 | Istio | AWS App Mesh |
|------|-------|--------------|
| 기능 세트 | 매우 포괄적 | 핵심 기능에 집중 |
| AWS 통합 | 제3자 통합 | 네이티브 통합 |
| 복잡성 | 높음 | 중간 |
| 리소스 요구 사항 | 높음 | 중간 |
| Fargate 지원 | 제한적 | 완전 지원 |
| 커뮤니티 | 매우 활발 | 성장 중 |
| 하이브리드/멀티클라우드 | 강력한 지원 | AWS 중심 |

서비스 메시는 EKS 클러스터의 네트워킹 아키텍처에 상당한 변화를 가져오지만, 마이크로서비스 아키텍처의 복잡성을 관리하는 데 강력한 도구를 제공합니다. 기본 EKS 네트워킹 모델과의 통합은 사이드카 패턴을 통해 이루어지며, 이는 기존 애플리케이션 코드를 변경하지 않고도 고급 네트워킹 기능을 추가할 수 있게 합니다. 서비스 메시 도입 시에는 성능 영향, 운영 복잡성, 리소스 요구 사항을 신중하게 고려해야 하며, 점진적인 접근 방식이 권장됩니다.
</details>
