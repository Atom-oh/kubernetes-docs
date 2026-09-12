# EKS 네트워킹 퀴즈 - Part 2

> **마지막 업데이트**: 2026년 9월 11일

답안은 [Part 2](../../eks/03-eks-networking-part2.md)의 컨트롤러 소유권과 전제 조건(LBC 3.5.0, Gateway API 1.6.0)을 따릅니다. 명령은 실행 시 리소스를 변경하는 예제이며 로컬 스키마·모의 검증은 EKS 배포 검증이 아닙니다. 계정·리전·리소스 자리표시자를 바꾸고 의도한 kubeconfig와 기존 IAM/Helm/IaC 소유자를 사용하세요.

### 1. AWS Load Balancer Controller가 Kubernetes Ingress 리소스를 위해 기본적으로 프로비저닝하는 AWS 로드 밸런서 유형은 무엇인가요?

A. Classic Load Balancer (CLB)\
B. Network Load Balancer (NLB)\
C. Application Load Balancer (ALB)\
D. Gateway Load Balancer (GWLB)

<details>

<summary>정답 보기</summary>

**정답: C. Application Load Balancer (ALB)**

**설명:** AWS Load Balancer Controller는 Kubernetes Ingress 리소스를 위해 기본적으로 Application Load Balancer(ALB)를 프로비저닝합니다. ALB는 HTTP/HTTPS 트래픽을 처리하는 Layer 7 로드 밸런서로, 경로 기반 라우팅, 호스트 기반 라우팅, TLS 종료 등의 기능을 제공하여 Ingress 리소스의 요구 사항을 충족합니다.

LBC가 해당 Ingress 클래스를 선택해야 하며 다른 컨트롤러는 Ingress를 다르게 구현할 수 있습니다. 아래 public scheme은 의도한 퍼블릭 서브넷·클라이언트 SG 접근과 준비된 백엔드 Service가 필요합니다.

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
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
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

* `spec.ingressClassName: alb`: 컨트롤러가 `ingress.k8s.aws/alb`인 IngressClass 선택
* `alb.ingress.kubernetes.io/scheme: internet-facing`: 인터넷 연결 가능한 ALB 생성
* `alb.ingress.kubernetes.io/target-type: ip`: 파드 IP를 대상으로 사용 (instance 대신)
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: 리스너 포트 구성
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: SSL 인증서 지정

다른 옵션들의 문제점:

* **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller는 Ingress 리소스를 위해 CLB를 사용하지 않습니다. CLB는 레거시 로드 밸런서로 간주됩니다.
* **B. Network Load Balancer (NLB)**: NLB는 주로 Service 타입 LoadBalancer에 사용되며, Ingress 리소스에는 기본적으로 사용되지 않습니다.
* **D. Gateway Load Balancer (GWLB)**: GWLB는 네트워크 가상 어플라이언스를 위한 것으로, Kubernetes Ingress 리소스와 함께 사용되지 않습니다.

</details>

### 2. 내부 ALB를 선택하는 Ingress 어노테이션은 무엇인가요?

- A. Service annotation `aws-load-balancer-internal`
- B. Ingress annotation `alb.ingress.kubernetes.io/scheme: internal`
- C. Any class named `internal-alb`
- D. `aws-load-balancer-type: internal`

<details>
<summary>정답 보기</summary>

**정답: B. `alb.ingress.kubernetes.io/scheme: internal`**

내부 ALB는 프라이빗 주소를 사용합니다. 경로·DNS·보안 제어가 허용하면 연결된 VPC나 온프레미스 클라이언트도 접근할 수 있으며 Pod나 해당 VPC에서만 접근하도록 정의된 것은 아닙니다.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
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
디스커버리 또는 명시한 서브넷 ID로 배치 위치를 선택하고 SG로 접근을 제어합니다. `inbound-cidrs`는 컨트롤러가 만드는 프론트엔드 SG에 적용되며 사용자 지정 SG를 주면 무시됩니다. Route 53 프라이빗 alias/CNAME은 별도로 만들어야 하며 ALB 로그 속성은 DNS 레코드를 만들지 않습니다. 실제 IngressClass/컨트롤러 설정이 있다면 `internal-alb` 같은 사용자 지정 이름도 가능하지만 이름만으로 scheme이 선택되지는 않습니다.

</details>

### 3. Ingress의 Pod IP 대상을 선택하는 어노테이션은 무엇인가요?

- A. `target-type: pod`
- B. `alb.ingress.kubernetes.io/target-type: ip`
- C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`
- D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>
<summary>정답 보기</summary>

**정답: B. `alb.ingress.kubernetes.io/target-type: ip`**

`ip`는 라우팅 가능한 Pod IP와 Service의 실제 대상 포트를 등록합니다. `instance`는 보통 노드와 NodePort를 등록하며 컨트롤러/IngressClass 기본값의 영향을 받습니다. EKS Fargate에는 IP 대상이 필요합니다. IP 선택만으로 Pod 보안 그룹이 생성되거나 노드 장애가 사라지거나 성능 향상이 보장되지는 않습니다.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ip-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
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
| 특성 | IP 대상 | Instance 대상 |
|---|---|---|
| 경로 | LB → Pod 대상 | LB → NodePort → 선택된 엔드포인트 |
| 노드 장애 | 해당 Pod 소실; 헬스체크·재조정 후 수렴 | 장애 노드 대상 제거; 다른 정상 노드는 유지 가능 |
| Service 유형 | ClusterIP로 충분 | NodePort 또는 NodePort가 할당된 LoadBalancer |
| Fargate | 지원 경로 | EC2 NodePort 대상 없음 |

VPC에서 라우팅 가능한 Pod 네트워크와 애플리케이션·헬스체크 접근을 준비합니다. 일반 EC2에서는 VPC CNI를 사용하며 지원되는 하이브리드·다른 네트워크 설계는 별도 연결 검증이 필요합니다. NLB Service 대응 어노테이션은 `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`이며 `nlb`가 빠진 선택지는 올바르지 않습니다.

</details>

### 4. NLB-IP 어노테이션만으로 PrivateLink 엔드포인트 서비스가 생성되나요?

- A. Any `LoadBalancer` Service creates PrivateLink
- B. `nlb-ip` automatically creates and authorizes it
- C. Separate NLB, endpoint service and consumer configuration
- D. Only instance targets can use PrivateLink

<details>
<summary>정답 보기</summary>

**정답: C. 아니요. NLB, 엔드포인트 서비스 구성, 소비자 접근을 별도로 준비합니다.**

기존 `nlb-ip` 답안은 대상 선택과 PrivateLink 생성을 혼동했습니다. 엔드포인트 서비스는 NLB(어플라이언스는 GWLB)를 사용하며 IP 대상이나 내부 NLB가 필수는 아닙니다. 이 예제는 프라이빗 Pod 접근을 위해 내부 IP 대상 NLB를 선택합니다.
```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
의도한 네임스페이스에서 일치하는 정상 Pod와 함께 Service를 생성하고 NLB 준비를 기다립니다. 호스트명을 하이픈으로 자르지 말고 정확한 DNSName으로 찾습니다:
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${SERVICE_NAMESPACE:?Set the Service namespace}"
NLB_DNS=$(kubectl -n "$SERVICE_NAMESPACE" get service privatelink-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$NLB_DNS"
aws elbv2 describe-load-balancers --region "$AWS_REGION" --output json > privatelink-load-balancers.json
NLB_ARN=$(python3 - "$NLB_DNS" <<'PY'
import json, sys
with open("privatelink-load-balancers.json") as stream:
    matches = [lb for lb in json.load(stream)["LoadBalancers"]
               if lb["DNSName"] == sys.argv[1] and lb["Type"] == "network"]
if len(matches) != 1:
    raise SystemExit("Expected exactly one matching NLB; check Region, account and readiness")
print(matches[0]["LoadBalancerArn"])
PY
)
printf '%s\n' "$NLB_ARN"
```
아래 공급자 명령은 과금 리소스를 만들고 소비자 계정 하나에 서비스 접근을 허용합니다. 검토한 인프라 소유자로 실행하고 반환 ID를 저장하며 멱등 명령처럼 생성을 반복하지 마세요. 상용 AWS 파티션 예제이므로 다른 파티션은 ARN을 조정합니다.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${NLB_ARN:?Use the NLB ARN verified above}"
: "${CONSUMER_ACCOUNT_ID:?Set the allowed consumer account}"
aws ec2 create-vpc-endpoint-service-configuration \
  --region "$AWS_REGION" --network-load-balancer-arns "$NLB_ARN" \
  --acceptance-required --output json > endpoint-service-created.json
SERVICE_ID=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceId"])')
SERVICE_NAME=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceName"])')
aws ec2 modify-vpc-endpoint-service-permissions \
  --region "$AWS_REGION" --service-id "$SERVICE_ID" \
  --add-allowed-principals "arn:aws:iam::$CONSUMER_ACCOUNT_ID:root"
printf 'Service name: %s\n' "$SERVICE_NAME"
```
소비자 계정에서는 지원 AZ(계정 간에는 AZ ID 비교), 의도한 클라이언트를 허용하는 엔드포인트 SG와 반환된 서비스 이름을 사용합니다. 같은 리전 예제이며 리전 간 PrivateLink를 구성하지 않습니다.
```bash
set -euo pipefail
: "${CONSUMER_REGION:?Set the consumer Region}"
: "${CONSUMER_VPC_ID:?Set the consumer VPC}"
: "${CONSUMER_SUBNET_A:?Set a subnet in an available service AZ}"
: "${CONSUMER_SUBNET_B:?Set another supported AZ subnet}"
: "${CONSUMER_SG_ID:?Set the endpoint security group}"
: "${SERVICE_NAME:?Copy the exact name returned by the provider}"
aws ec2 create-vpc-endpoint \
  --region "$CONSUMER_REGION" --vpc-id "$CONSUMER_VPC_ID" \
  --service-name "$SERVICE_NAME" --vpc-endpoint-type Interface \
  --subnet-ids "$CONSUMER_SUBNET_A" "$CONSUMER_SUBNET_B" \
  --security-group-ids "$CONSUMER_SG_ID"
```
승인이 필요하도록 설정했으므로 공급자가 해당 pending 엔드포인트 요청을 승인해야 합니다. 선택적인 프라이빗 DNS는 소비자가 활성화하기 전에 도메인 소유권 검증이 필요합니다. 대상 상태·엔드포인트 상태·애플리케이션 인증을 확인하세요. 대상에서 보이는 PrivateLink 소스 IP는 NLB 주소이며 백엔드가 지원하면 Proxy Protocol v2로 소비자 메타데이터를 받을 수 있습니다. 규정 준수나 애플리케이션 권한을 자동 보장하지 않습니다. 종료 시 소비자 엔드포인트, 서비스 연결, Kubernetes 로드 밸런서를 각 소유 관리 도구로 정리합니다.

</details>

### 5. Amazon VPC CNI와 함께 사용할 수 있는 추가 정책 엔진은 무엇인가요?

- A. AWS Network Firewall
- B. Calico
- C. Security Groups for Pods
- D. VPC Flow Logs

<details>
<summary>정답 보기</summary>

**정답: B. Calico**

Calico는 VPC CNI가 IPAM·네트워킹을 담당하는 상태에서 정책을 적용할 수 있습니다. 필수 추가 요소가 아니라 VPC CNI 네이티브 정책 엔진의 대안입니다. 지원 버전, `cni.type: AmazonVPC`, `ANNOTATE_POD_IP`와 Pod patch 권한 등 [공식 EKS 정책 전용 절차](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)를 따릅니다. 두 엔진을 동시에 켜거나 실행 중 클러스터에 VXLAN 교체 매니페스트를 적용하지 마세요.

Calico API는 순서·계층 규칙, GlobalNetworkPolicy, NetworkSet, ServiceAccount 선택자와 호스트 엔드포인트 정책도 제공합니다. 합집합 방식의 Kubernetes NetworkPolicy와 의미가 다르며 NetworkSet은 Calico 정책에서 참조해야 효과가 있습니다. 전역 allow-all은 최소 권한 기본값이 아닙니다. 모든 VPC CNI 모드와의 호환성을 가정하지 마세요. 현재 Calico EKS 안내는 `ENABLE_V4_EGRESS=true`인 IPv6 Pod의 정책 적용을 지원하지 않는다고 명시합니다.

네임스페이스 소유의 Kubernetes 정책 예제로 `policy-lab`과 `role=frontend` 레이블을 가진 컨트롤러 관리 Pod를 준비합니다. 아래 egress 정책은 일반 CoreDNS와 승인된 HTTPS 목적지를 허용하되 다른 정책의 허용과 합쳐집니다. 문서용 CIDR은 실제 목적지로 바꾸고 NodeLocal DNS 사용 시 경로를 조정하세요.
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
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
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - protocol: TCP
      port: 443
```
정책을 신뢰하기 전에 기준 연결과 허용·거부 TCP 경로를 검증합니다. NetworkPolicy에는 이식 가능한 audit-only 모드가 없습니다. 선택한 엔진에서 지원하는 로깅·단계적 적용 기능을 확인하세요. Pod SG·VPC 방화벽은 별도 제어이며 Flow Logs는 이 API를 적용하는 대신 트래픽을 관찰합니다.

</details>

### 6. 사용자 지정 ALB 프론트엔드 SG와 백엔드 규칙은 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

**정답: `alb.ingress.kubernetes.io/security-groups`**

아래 어노테이션 조각을 의도한 Ingress에 병합합니다. SG ID는 명확하며 이름으로 찾을 때는 EC2 `groupName` 속성이 아니라 AWS `Name` 태그를 사용합니다.
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    alb.ingress.kubernetes.io/tags: Environment=training,Team=platform
```
사용자 지정 프론트엔드 inbound/outbound 규칙은 직접 구성합니다. 이 경우 `inbound-cidrs`와 prefix-list 어노테이션은 무시됩니다. `manage-backend-security-group-rules: "true"`는 백엔드 SG 메커니즘으로 대상 접근 규칙을 관리하도록 하며 사용자 지정 프론트엔드 SG의 클라이언트 제한 규칙을 만들어 주지는 않습니다. 이를 사용하지 않으면 노드/Pod SG 접근을 직접 준비해야 합니다. 애플리케이션·헬스체크 포트와 대상 ENI의 여러 SG 중 선택할 태그를 확인하세요.

릴리스 IAM 정책에는 전체 컨트롤러의 EC2/ELB 권한이 포함되며 SG 작업 몇 개를 나열한 것은 완성된 역할 정책이 아닙니다. 신뢰 영역 간 SG 재사용은 노출과 변경 영향 범위를 넓힐 수 있습니다. 실제 규칙과 VPC Flow Log 거부를 검토하세요. `tags`가 지원 리소스 태그를 추가하며 `load_balancing.cross_zone.enabled`는 태그가 아닌 분산 속성입니다. 이전 TLS 정책 이름을 현재 권장값으로 복사하지 말고 클라이언트 호환성과 요구에 맞는 지원 정책을 선택합니다.

</details>

### 7. NLB 클라이언트 IP 보존 설정과 제약은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`**

TCP/TLS 대상 그룹에서는 속성을 설정할 수 있으며 instance 대상은 기본 활성, IP 대상은 기본 비활성입니다. UDP/TCP_UDP/QUIC/TCP_QUIC 대상 그룹은 항상 클라이언트 IP를 보존하며 끌 수 없습니다. 아래 IPv4 IP 대상 TCP 예제는 변경 가능한 경우입니다:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
애플리케이션이 보는 주소는 전체 경로에 따라 달라집니다. NodePort 전달 과정은 local 트래픽 정책·토폴로지가 보존하지 않으면 SNAT할 수 있고 ALB는 HTTP 전달 헤더를 사용합니다. IPv6→IPv4 변환과 PrivateLink에서는 원래 패킷 소스가 유지되지 않습니다. 보존에는 같은 VPC 또는 같은 리전 피어링의 지원되는 직접 경로가 필요하며 Transit Gateway 경유는 지원되지 않습니다. 내부 NLB 뒤의 대상이 같은 NLB를 통해 자신에게 연결하는 hairpin 연결도 실패할 수 있습니다.

Proxy Protocol v2는 원본 주소 메타데이터를 전달하지만 호환 리스너·파서가 필요하므로 무조건 켜지 마세요. 프레임워크 `remote_addr`나 TCP `RemoteAddr()`는 직접 연결된 상대 주소이며 인터넷 원본 클라이언트를 자동 식별하지 않습니다. 명시적으로 신뢰한 프록시의 전달 헤더만 사용합니다. 보존 변경은 새 TCP 연결부터 적용됩니다. `deregistration_delay.timeout_seconds`는 TCP keep-alive가 아니라 드레이닝을 제어합니다. 근거 없는 오버헤드 수치 대신 실제 경로에서 측정하세요.

</details>

### 8. LBC가 관리하는 ALB에 AWS WAF를 어떻게 연결하나요?

<details>
<summary>정답 보기</summary>

**정답: `alb.ingress.kubernetes.io/wafv2-acl-arn` 및 같은 리전의 REGIONAL Web ACL.**

실제 `regional/webacl/...` ARN을 사용합니다. CloudFront의 `global/webacl/...` ARN은 리전 ALB에 연결할 수 없습니다. 이 연결은 해당 ALB를 통과하는 트래픽에 적용되며 Pod·NLB·Kubernetes API 서버에 WAF를 붙이는 것이 아닙니다.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: waf-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:123456789012:regional/webacl/eks-ingress-protection/00000000-0000-4000-8000-000000000000
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
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
규칙이 없고 기본 동작이 Allow인 Web ACL은 아무것도 차단하지 않습니다. 격리된 규칙 개발 예제로 아래 배열을 `waf-rules.json`에 저장합니다. 이 규칙은 `/admin` 접두사를 차단하지 않고 **계수**하며 인증 제어나 완성된 관리형 규칙 기본값이 아닙니다.
```json
[
  {
    "Name": "count-admin-path",
    "Priority": 1,
    "Action": {
      "Count": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "count-admin-path"
    },
    "Statement": {
      "ByteMatchStatement": {
        "SearchString": "/admin",
        "FieldToMatch": {
          "UriPath": {}
        },
        "TextTransformations": [
          {
            "Priority": 0,
            "Type": "NONE"
          }
        ],
        "PositionalConstraint": "STARTS_WITH"
      }
    }
  }
]
```
보안 소유자가 아래 명령으로 교육용 ACL을 만들 수 있으며 연결할 때 반환된 ARN을 사용합니다. binary-format 플래그는 AWS CLI v2가 JSON SearchString을 문자 그대로의 바이트로 읽게 합니다.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the ALB Region}"
aws wafv2 create-web-acl --region "$AWS_REGION" \
  --name eks-ingress-training --scope REGIONAL \
  --default-action '{"Allow":{}}' --rules file://waf-rules.json \
  --cli-binary-format raw-in-base64-out \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-training
```
SQLi/XSS·봇·평판·속도 기반·사용자 지정 규칙은 각각 구성하고 조정해야 해당 보호를 제공하며 기능·요금이 다릅니다. Count 모드에서 오탐을 검토한 뒤 차단을 활성화합니다. 규칙이 계수하는 동안 기본 Allow는 계속 허용합니다.

ALB의 `access_logs.s3.*`는 S3 ALB 접근 로그 설정이지 WAF 로그나 CloudWatch Logs 설정이 아닙니다. WAF 로깅은 승인한 CloudWatch Logs/S3/Firehose 목적지와 권한으로 별도 구성하며 샘플 요청·CloudWatch 메트릭도 전체 요청 로그와 다릅니다. 연결에는 검토한 릴리스 컨트롤러 IAM 정책, ACL 생성·규칙·로깅에는 별도 보안 관리 역할을 사용합니다. 지원되는 리소스 권한은 제한하고 제약 없는 wildcard 조각을 완성된 컨트롤러 역할로 복사하지 마세요.

</details>

### 9. 구별 가능한 백엔드 세 개의 경로 라우팅을 만들고 검증하세요.

<details>
<summary>정답 보기</summary>

**정답: Ingress + ClusterIP Services + 준비된 HTTP 워크로드.**

전제 조건은 검토한 IAM·서브넷을 사용하는 LBC, 프라이빗 경로의 테스트 클라이언트, 소유한 호스트명의 ACM 인증서와 전용 네임스페이스 생성 권한입니다. 내부 ALB를 생성하며 `/admin`은 라우팅 이름일 뿐 인증되지 않습니다. 제한된 교육 실습이지 프로덕션 준비 검증 결과가 아닙니다. 같은 셸에서 `set -euo pipefail`을 사용하고 정리할 때까지 LAB_NS/LAB_UID를 보존하세요.
```bash
set -euo pipefail
LAB_NS="alb-paths-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
kubectl create namespace "$LAB_NS"
LAB_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test -n "$LAB_UID"
kubectl label namespace "$LAB_NS" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.36
printf 'Namespace: %s UID: %s\n' "$LAB_NS" "$LAB_UID"
```
HTTP 서버는 실제 8080을 리스닝하며 `/health`와 요청 경로에 백엔드 이름으로 응답합니다. `containerPort: 8080` 선언만으로 기본 nginx 서버 포트가 바뀌지는 않습니다. Python 태그는 예시 런타임이므로 반복 실행에는 승인한 이미지 digest를 고정하세요.
```bash
for APP in api admin frontend; do
  kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $APP
spec:
  replicas: 2
  selector:
    matchLabels:
      app: $APP
  template:
    metadata:
      labels:
        app: $APP
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: http
        image: python:3.13-alpine
        command: ["python", "-u", "-c"]
        args:
        - |
          import os
          from http.server import BaseHTTPRequestHandler, HTTPServer
          class Handler(BaseHTTPRequestHandler):
              def do_GET(self):
                  self.send_response(200)
                  self.end_headers()
                  self.wfile.write((os.environ["APP_NAME"] + "\\n").encode())
          HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
        env:
        - name: APP_NAME
          value: $APP
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 200m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
---
apiVersion: v1
kind: Service
metadata:
  name: $APP-service
spec:
  type: ClusterIP
  selector:
    app: $APP
  ports:
  - port: 80
    targetPort: http
EOF
  kubectl -n "$LAB_NS" rollout status "deployment/$APP" --timeout=180s
done
```

```bash
set -euo pipefail
: "${LAB_NS:?Run the namespace setup first}"
: "${LAB_HOST:?Set a DNS hostname you control, for example app.example.com}"
: "${ACM_CERT_ARN:?Set a matching certificate ARN in the ALB Region}"
: "${CLIENT_CIDR:?Set the permitted private client CIDR}"
kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/inbound-cidrs: "$CLIENT_CIDR"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: "$ACM_CERT_ARN"
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  ingressClassName: alb
  rules:
  - host: "$LAB_HOST"
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
EOF
kubectl -n "$LAB_NS" get ingress multi-path-ingress
kubectl -n "$LAB_NS" get endpointslices
```
ALB 호스트명, 정상 대상과 컨트롤러 재조정 완료를 기다립니다. 실패 시 Ingress 이벤트, 컨트롤러 로그, EndpointSlice와 SG·헬스체크 경로를 확인하세요. 허용된 프라이빗 클라이언트에서 아래 테스트는 Host 헤더와 TLS SNI를 유지하면서 ALB 호스트명으로 직접 연결합니다. DNS 레코드나 인증서 검증 해제가 필요하지 않습니다.
```bash
ALB_DNS=$(kubectl -n "$LAB_NS" get ingress multi-path-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$ALB_DNS"
for ROUTE in api admin frontend; do
  URL_PATH="/$ROUTE"
  test "$ROUTE" != frontend || URL_PATH=/
  RESPONSE=$(curl --fail --show-error --silent --max-time 15 \
    --connect-to "$LAB_HOST:443:$ALB_DNS:443" "https://$LAB_HOST$URL_PATH")
  test "$RESPONSE" = "$ROUTE" || { printf 'Unexpected backend: %s\n' "$RESPONSE"; exit 1; }
done
```
지속적인 DNS에는 적절한 Route 53 alias를 만들며 CNAME은 서브도메인에서 가능하고 존 apex에서는 사용할 수 없습니다. 인증서 불일치를 자리표시자 ARN이나 `curl -k`로 숨기지 마세요.

선택적인 가중치 라우팅은 기존 `service-v1`/`service-v2`를 사용하는 별도 예제입니다. action은 `use-annotation` 백엔드로 참조해야 하며 어노테이션만 추가하면 효과가 없습니다. 의도한 네임스페이스에서 충돌하는 경로 없이 사용합니다.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: weighted-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/actions.weighted-routing: >-
      {"type":"forward","forwardConfig":{"targetGroups":[{"serviceName":"service-v1","servicePort":"80","weight":80},{"serviceName":"service-v2","servicePort":"80","weight":20}]}}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: weighted-routing
            port:
              name: use-annotation
```
저장한 UID를 확인한 뒤 이 실습 네임스페이스만 정리합니다. 네임스페이스 삭제 전에 LBC가 Ingress 로드 밸런서를 제거하게 합니다. 종료가 실패하면 컨트롤러·IAM·삭제 보호 상태를 진단하고 finalizer를 강제 제거하지 마세요. 이 블록은 공유 인증서·컨트롤러 역할·DNS 레코드를 삭제하지 않습니다.
```bash
set -euo pipefail
: "${LAB_NS:?Use the namespace from this exercise}"
: "${LAB_UID:?Use the UID saved when that namespace was created}"
case "$LAB_NS" in alb-paths-*) ;; *) echo "Unexpected namespace"; exit 1 ;; esac
CURRENT_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test "$CURRENT_UID" = "$LAB_UID" || { echo "Namespace identity changed"; exit 1; }
kubectl -n "$LAB_NS" delete ingress multi-path-ingress --ignore-not-found --wait=true --timeout=300s
kubectl delete namespace "$LAB_NS" --wait=true --timeout=300s
```

</details>

### 10. 서비스 메시는 EKS 네트워킹을 어떻게 바꾸며 무엇을 검증해야 하나요?

<details>
<summary>정답 보기</summary>

**정답: 호환되는 Pod 네트워크 위에 트래픽·보안·텔레메트리 처리를 추가합니다.**

컨트롤 플레인은 구성·워크로드 신원을 배포하고 데이터 플레인 프록시는 등록된 트래픽을 처리합니다. 사이드카 방식에서는 애플리케이션과 프록시가 **동일한 Pod 네트워크 네임스페이스/IP**를 공유하므로 사이드카 자체가 VPC IP·ENI를 하나 더 소비하지 않습니다. 별도 메시 게이트웨이·컨트롤 플레인 Pod는 자원과 IP를 사용합니다. Ambient 방식은 노드 프록시와 선택적 waypoint를 사용하므로 “모든 Pod에 사이드카”는 보편적 설명이 아닙니다.
```text
Client application → client proxy → Pod network → destination proxy → destination application
```
이는 논리적 사이드카 경로이며 모든 패킷이 Service 가상 IP를 지나거나 가로채진다는 보장은 아닙니다. 제외 포트, UDP, host-network 트래픽, 네임스페이스 등록과 모드를 확인합니다. VPC 경로·SG·NetworkPolicy는 계속 적용됩니다. L3/L4 정책은 데이터 플레인·DNS·컨트롤 플레인·헬스체크의 실제 경로를 허용해야 하며 mTLS의 피어 인증·암호화는 애플리케이션 권한 검사를 대체하지 않습니다.

Istio는 컴퓨팅 유형에 맞는 사이드카/ambient 설치 하나를 선택합니다. Fargate는 일부 모드에 필요한 노드 DaemonSet·특권 구성 요소를 실행할 수 없으므로 보편적 호환성을 주장하지 말고 지원 경로를 확인하세요. 한 네임스페이스에 메시 injector 두 개를 켜지 않습니다. 프록시 자원은 지원되는 Helm·설치·워크로드 설정으로 구성하며 관련 없는 `pilot.resources`로 injector ConfigMap을 덮어쓰지 않습니다. Prometheus·트레이싱 배포와 메시 내보내기 설정도 구분합니다. 제거된 `IstioOperator.addonComponents.prometheus`와 존재하지 않는 App Mesh `Mesh.spec.tracing`는 사용할 수 있는 설치 절차가 아닙니다.

**이전 제품 비교:** AWS는 **2026년 9월 30일** App Mesh 지원을 종료하며 이후 콘솔·리소스에 접근할 수 없다고 공지했습니다. 감사일 현재 기존 App Mesh 배포에는 이전 계획이 필요하며 새 EKS 기본 선택지로 도입하지 마세요. 과거 Fargate 통합도 향후 지원 보장이 아닙니다. ECS Service Connect는 ECS용이지 EKS의 직접 대체품이 아닙니다. 지원되는 EKS 메시·데이터 플레인 설계에서 라우팅·재시도·인증서·권한·트레이싱·장애 처리의 동등성을 검증합니다.

기존 “일반적으로 <10 ms” 지연 및 “10–15%” CPU·메모리 오버헤드 수치는 이 문서에서 검증된 측정 출처가 없습니다. **검증되지 않은 과거 추정값**으로 보존하며 벤치마크나 용량 보장으로 사용하지 않습니다. 등록 전후 동일한 요청 구성·TLS·텔레메트리 샘플링·부하에서 p50/p95/p99 지연, 처리량, 오류와 CPU·메모리를 측정합니다. 프록시 롤아웃, 노드·컨트롤 플레인 장애, 인증서 회전과 재시도 증폭도 테스트하세요.

전용 네임스페이스에서 injector 하나, 준비된 워크로드, mTLS와 허용·거부 정책을 검증하고 점진적으로 확장합니다. LBC를 메시 ingress gateway 앞에 둘 때는 해당 gateway Service와 대상 포트·프로브를 확인하며 Ingress API 객체는 또 다른 프록시 홉이 아닌 구성입니다. 필요한 컨트롤러 IAM을 제한하고 `cloudmap:*`를 실제 `servicediscovery` IAM 접두사 대신 사용하지 않습니다. Prefix delegation은 IP 용량 선택이지 사이드카 필수 요건이 아닙니다. 구현은 유지 관리되는 [Istio 설치](../../service-mesh/istio/01-installation.md)와 [AWS 통합](../../service-mesh/istio/04-aws-integration.md) 문서를 참고하세요.

</details>

### 11. Kubernetes Gateway API에서 L7 로드 밸런싱(ALB)을 위해 사용하는 라우팅 리소스는 무엇인가요?

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>정답 보기</summary>

**정답: B. HTTPRoute**

**설명:** Kubernetes Gateway API에서 L7 로드 밸런싱을 위해 HTTPRoute 리소스를 사용합니다. HTTPRoute는 HTTP/HTTPS 트래픽을 서비스로 라우팅하는 규칙을 정의하며, AWS Load Balancer Controller와 함께 사용할 경우 ALB를 통해 트래픽을 분배합니다.

**Gateway API 리소스 계층 구조:**

1. **GatewayClass**: 로드 밸런서 유형 정의 (예: `amazon-alb`, `amazon-nlb`)
2. **Gateway**: 실제 로드 밸런서 인스턴스 (리스너 포트, TLS 설정 등)
3. **HTTPRoute**: L7 라우팅 규칙 (호스트, 경로, 헤더 기반 라우팅)
4. **TCPRoute**: L4 라우팅 규칙 (TCP 트래픽)

LBC는 ALB와 NLB Gateway를 별도로 사용합니다. 임의의 GatewayClass 이름이 아니라 controllerName이 구현을 선택하며 지원 필터는 릴리스 적합성 표를 확인합니다.

**HTTPRoute의 주요 기능:**

* 경로 및 호스트 기반 라우팅
* 네이티브 가중치 기반 트래픽 분할
* 헤더 및 쿼리 파라미터 매칭
* 여러 백엔드 서비스로의 라우팅

다른 옵션들의 문제점:

* **A. IngressRoute**: 이는 표준 Gateway API 리소스가 아닙니다.
* **C. VirtualService**: 이는 Istio 서비스 메시의 리소스입니다.
* **D. ServiceRoute**: 이러한 리소스는 존재하지 않습니다.

</details>

### 12. LBC 3.5.0의 Gateway 컨트롤러는 어떻게 활성화되나요?

- A. Always pass `--enable-gateway-api`
- B. Detect compatible CRDs with the real default-enabled gates
- C. Use `--feature-gates=EnableGatewayAPI=true`
- D. Install only experimental CRDs from 1.2.1

<details>
<summary>정답 보기</summary>

**정답: B. 필요한 CRD를 감지하며 ALBGatewayAPI/NLBGatewayAPI는 기본 활성입니다.**

릴리스와 호환되는 Gateway API 1.6.0 standard CRD와 LBC 전용 Gateway CRD를 설치합니다. 기본 활성 gate는 `ALBGatewayAPI`, `NLBGatewayAPI`이며 `EnableGatewayAPI`는 알 수 없는 feature 이름입니다. TCPRoute/UDPRoute는 이제 standard 채널에서 v1으로 제공됩니다. 이전 컨트롤러의 호환성·gate 조건은 다르며 L4 지원은 2.13.3, L7 지원은 2.14.0부터입니다. CRD 설치 후 컨트롤러 시작·로그를 확인하고 IAM·서브넷·백엔드도 준비해야 합니다.

</details>

### 13. Gateway API에서 L4 레벨의 TCP 트래픽을 NLB를 통해 라우팅하기 위해 사용하는 리소스는 무엇인가요?

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>정답 보기</summary>

**정답: C. TCPRoute**

**설명:** Gateway API에서 L4 레벨의 TCP 트래픽을 라우팅하기 위해 TCPRoute 리소스를 사용합니다. AWS Load Balancer Controller와 함께 사용할 경우, TCPRoute는 NLB(Network Load Balancer)를 통해 TCP 트래픽을 백엔드 서비스로 전달합니다.

**TCPRoute 설정 예시:**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: db-route
  namespace: gateway-demo
spec:
  parentRefs:
  - name: my-nlb-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: postgres-service
      port: 5432
```

**Gateway API 라우팅 리소스별 용도:**

| 리소스       | 프로토콜       | AWS LB 유형 |
| --------- | ---------- | --------- |
| HTTPRoute | HTTP/HTTPS | ALB       |
| TCPRoute  | TCP        | NLB       |
| TLSRoute  | TLS        | NLB       |
| GRPCRoute | gRPC       | ALB       |

다른 옵션들의 문제점:

* **A. HTTPRoute**: HTTP/HTTPS L7 트래픽용으로 ALB와 함께 사용됩니다.
* **B. TLSRoute**: TLS 트래픽 라우팅용이지만, TCP 레벨 라우팅에는 TCPRoute가 적합합니다.
* **D. GRPCRoute**: gRPC 프로토콜 전용 라우팅 리소스입니다.

</details>
`my-nlb-gateway` 리스너와 백엔드 Service는 `gateway-demo`에 있어야 합니다. 이 구현의 TLSRoute는 NLB의 SNI 기반 라우팅을 제공하지 않으므로 모든 Gateway API 구현이 같다고 가정하지 말고 릴리스별 TLS 동작을 확인합니다.

### 14. LBC 3.5.0은 ALB Gateway의 정적 인증서를 어떻게 구성하나요?

- A. Create any Secret named tls-cert
- B. Use the ACM ARN in LoadBalancerConfiguration
- C. Add only a Route hostname
- D. Set backend Service port 443

<details>
<summary>정답 보기</summary>

**정답: B. `LoadBalancerConfiguration.spec.listenerConfigurations[].defaultCertificate`**

HTTPS 리스너에 같은 리전의 유효한 ACM 인증서 ARN을 사용합니다. 이 구현은 Kubernetes Secret `certificateRefs`를 지원하지 않습니다. 호스트명 디스커버리도 기존의 일치하는 ACM 인증서와 보안 리스너가 필요합니다. 백엔드 포트가 443인 HTTPRoute만으로 클라이언트 HTTPS가 구성되지는 않습니다.

</details>

### 15. frontend 전용 ingress 정책이 기존 같은 네임스페이스 전체 허용 정책을 좁히나요?

- A. Yes, the newest policy wins
- B. Yes, the most specific selector wins
- C. No, matching allows form a union
- D. Only if the policy name sorts first

<details>
<summary>정답 보기</summary>

**정답: C. 아니요. 일치하는 NetworkPolicy 허용은 합집합입니다.**

두 정책이 백엔드를 선택하면 더 넓은 같은 네임스페이스 허용에 의해 다른 호출자도 계속 허용됩니다. 소유 관리 도구로 넓은 정책을 제거하거나 좁힌 뒤 허용·거부 연결을 테스트하세요. Ingress와 egress 격리는 별개이며 DNS egress와 대상 ingress도 테스트 결과에 영향을 줍니다.

</details>

공식 참고: [LBC Gateway API](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/gateway/), [PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html), [NLB client IP](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html), [WAF associations](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html), [App Mesh retirement](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).
