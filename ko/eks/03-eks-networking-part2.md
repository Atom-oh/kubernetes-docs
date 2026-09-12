# EKS 네트워킹 - Part 2: 서비스 및 로드 밸런싱, 네트워크 정책

> **예제 검증 버전**: EKS Kubernetes 1.36, AWS Load Balancer Controller 3.5.0, Gateway API 1.6.0
> **마지막 업데이트**: 2026년 9월 11일

## 개요

이 문서에서는 Amazon EKS에서의 서비스 및 로드 밸런싱, 네트워크 정책에 대해 알아보겠습니다. Kubernetes 서비스를 통해 애플리케이션을 노출하는 방법, AWS 로드 밸런서와의 통합, 그리고 네트워크 정책을 사용하여 포드 간 통신을 제어하는 방법을 다룹니다.

## Kubernetes 서비스 유형

Kubernetes에서는 다음과 같은 서비스 유형을 제공합니다:

![ClusterIP, NodePort, LoadBalancer, ExternalName 네 가지 Kubernetes 서비스 유형이 각각 클러스터 내부, 노드 IP:포트, 외부 로드 밸런서, DNS CNAME이라는 접근 방법에 1대1로 대응됨을 보여준다.](../.gitbook/assets/ko-eks-03-eks-networking-part2-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-03-eks-networking-part2-0.html)

1. **ClusterIP**: 클러스터 라우팅용 가상 IP; 접근 제어 경계는 아님
2. **NodePort**: 라우팅·방화벽 규칙이 허용하는 노드 주소와 할당 포트로 노출되는 서비스
3. **LoadBalancer**: 설치된 로드 밸런서 구현이 처리하는 서비스; 내부 로드 밸런서도 가능
4. **ExternalName**: 외부 서비스에 대한 CNAME 레코드 제공

### ClusterIP 서비스

ClusterIP는 기본 유형이며 가상 IP를 통한 클러스터 통신을 제공합니다. 네임스페이스 격리나 인증을 강제하지는 않습니다. Headless Service(`clusterIP: None`)는 DNS로 엔드포인트 주소를 제공합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

### NodePort 서비스

NodePort는 구성된 노드 주소와 할당 포트(기본 범위 30000–32767)를 사용합니다. 노드 상태, 서비스 프록시 설정, `externalTrafficPolicy`, 경로와 보안 규칙에 따라 실제 연결 가능성이 달라집니다. 서비스 하나를 위해 전체 포트 범위를 열 필요는 없습니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080
  type: NodePort
```

### LoadBalancer 서비스

설치된 컨트롤러가 Service를 처리합니다. 예제는 LBC를 명시적으로 선택하여 Pod IP를 대상으로 내부 NLB를 만듭니다. ALB는 Ingress 또는 ALB Gateway로 구성합니다. EKS Auto Mode는 `eks.amazonaws.com/nlb`와 별도 지원 설정을 사용합니다. 같은 `my-service` 예제를 중복 적용하지 마세요.
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
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

### ExternalName 서비스

ExternalName 서비스는 외부 서비스에 대한 CNAME 레코드를 제공합니다. 트래픽을 프록시하거나 TLS·포트·방화벽 접근을 구성하지 않습니다. HTTP Host 헤더와 인증서 이름이 실제 대상과 일치해야 합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ExternalName
  externalName: my-service.example.com
```

## AWS 로드 밸런서 통합

EKS는 Kubernetes 서비스를 AWS 로드 밸런서와 통합하여 외부에서 애플리케이션에 액세스할 수 있게 합니다.

<!-- Diagram repair pending: see batch report.
![인터넷 사용자가 CLB, NLB, ALB 세 종류의 AWS 로드 밸런서를 통해 EKS 클러스터에 접근하며, CLB와 NLB는 LoadBalancer 서비스로, ALB는 Ingress 리소스를 거쳐 NodePort 서비스로 연결되고 각 서비스가 최종적으로 Pod로 트래픽을 전달하는 흐름을 보여준다.](../.gitbook/assets/ko-eks-03-eks-networking-part2-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-03-eks-networking-part2-1.html)
-->

### Classic Load Balancer(CLB)

이전 AWS 서비스 컨트롤러 경로에서는 CLB를 만들 수 있었습니다. 이는 현재 LBC의 기본 동작이 아닙니다. LBC 2.5+는 일반적으로 새 LoadBalancer Service에 NLB 클래스를 지정합니다. 기존 Service를 이전하기 전에 실제 컨트롤러·클래스·소유권을 확인하세요. 소유권 어노테이션을 직접 바꾸면 리소스 누수나 노출 변경이 생길 수 있습니다.

### Network Load Balancer (NLB)

위의 명시적 NLB 예제를 사용합니다. 다음은 독립 매니페스트가 아니라 **해당 Service에 병합할 어노테이션 조각**입니다:
```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
```
`aws-load-balancer-nlb-target-type`이 대상 유형을 선택합니다. `preserve_client_ip.enabled`는 대상 유형이 아니라 소스 IP 동작을 바꿉니다. 교차 영역 로드 밸런싱은 용량·가용성·비용을 함께 판단하며 영역별 대상과 장애 동작을 확인해야 합니다. Proxy Protocol v2는 이를 해석하는 백엔드가 필요하므로 일반 HTTP 서버에 무조건 켜면 요청이 실패할 수 있습니다.

### Application Load Balancer(ALB)

ALB를 사용하려면 AWS Load Balancer Controller를 설치하고 Ingress 리소스를 사용해야 합니다:

![인터넷 트래픽이 퍼블릭 서브넷의 Application Load Balancer를 거쳐 프라이빗 서브넷 EKS 클러스터의 Ingress 리소스로 들어가고, AWS Load Balancer Controller가 ALB를 생성·구성하며, Ingress가 서비스 1과 서비스 2를 통해 각각의 Pod로 라우팅되는 경로를 보여준다.](../.gitbook/assets/ko-eks-03-eks-networking-part2-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-03-eks-networking-part2-2.html)

1. 플랫폼 관리자와 컨트롤러를 준비합니다. 아래 명령은 고정된 IAM 정책 다운로드와 차트 렌더링만 수행하며 IAM 신뢰 관계를 만들지 않습니다. 릴리스 정책 및 검토한 Pod Identity 연결 또는 IRSA 역할/OIDC 신뢰를 가진 `kube-system/aws-load-balancer-controller` ServiceAccount를 먼저 준비하세요. 기존 설치는 원래 Helm/IaC 소유자로 관리합니다. 서브넷 디스커버리, API/webhook 연결과 kubeconfig도 확인합니다.
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${VPC_ID:?Set the cluster VPC ID}"
curl --fail --show-error --location \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json \
  --output lbc-iam-policy-v3.5.0.json
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm template aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --namespace kube-system \
  --set-string clusterName="$CLUSTER_NAME" \
  --set-string region="$AWS_REGION" --set-string vpcId="$VPC_ID" \
  --set serviceAccount.create=false \
  --set-string serviceAccount.name=aws-load-balancer-controller \
  > lbc-rendered.yaml
```
렌더링 결과 검토와 IAM 준비를 마친 뒤 다음 명령을 실행하면 클러스터가 변경됩니다. CRD는 릴리스 절차대로 갱신하며 Helm upgrade가 모든 CRD를 자동 갱신하지는 않습니다.
```bash
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --namespace kube-system \
  --set-string clusterName="$CLUSTER_NAME" \
  --set-string region="$AWS_REGION" --set-string vpcId="$VPC_ID" \
  --set serviceAccount.create=false \
  --set-string serviceAccount.name=aws-load-balancer-controller
kubectl -n kube-system rollout status deployment/aws-load-balancer-controller --timeout=180s
```
2. `spec.ingressClassName: alb`인 Ingress를 만듭니다. 별도 로드 밸런서를 중복 생성하지 않도록 첫 예제의 **ClusterIP** `my-service`를 백엔드로 사용합니다. 선택된 Pod는 실제로 8080 포트를 리스닝해야 합니다. 위 그림은 논리적 구성 관계이며 트래픽이 Ingress API 객체나 컨트롤러 Pod를 통과한다는 뜻은 아닙니다.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
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
HTTPS 사용 시 아래 조각을 Ingress에 병합하고 ACM ARN과 보안 그룹을 같은 리전/VPC의 실제 리소스로 바꿉니다. 사용자 지정 프론트엔드 SG 규칙은 직접 구성하며 백엔드 규칙 관리는 별도 선택입니다. 참조되지 않은 action 어노테이션만으로 리디렉션이 생기지는 않습니다. 아래 `ssl-redirect`는 공식 단축 설정입니다.
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:123456789012:certificate/00000000-0000-4000-8000-000000000000
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
```

### 서비스 및 로드 밸런서 모범 사례

<!-- Diagram repair pending: see batch report.
![서비스 및 로드 밸런서 모범 사례 하나에서 ClusterIP 사용, LoadBalancer/Ingress 사용, ALB 사용 조건, NLB 사용 조건, 내부 로드 밸런서 사용, 교차 영역 로드 밸런싱 활성화, 적절한 대상 유형 선택이라는 일곱 가지 실천 항목이 뻗어나가는 구조를 보여준다.](../.gitbook/assets/ko-eks-03-eks-networking-part2-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-03-eks-networking-part2-3.html)
-->

1. **내부 서비스에는 ClusterIP 사용**: 클러스터 내부에서만 액세스하는 서비스에는 ClusterIP 유형을 사용합니다.
2. **외부 서비스에는 LoadBalancer 또는 Ingress 사용**: 외부에서 액세스해야 하는 서비스에는 LoadBalancer 유형 또는 Ingress 리소스를 사용합니다.
3. **ALB 사용**: 경로 기반 라우팅, SSL 종료, 인증 등의 기능이 필요한 경우 ALB를 사용합니다.
4. **NLB 사용**: TCP/UDP 트래픽, 고성능, 정적 IP가 필요한 경우 NLB를 사용합니다.
5. **내부 로드 밸런서 사용**: 허용된 연결 VPC·온프레미스 등 프라이빗 경로의 클라이언트에는 내부 로드 밸런서를 사용합니다. 클러스터 내부 통신에는 보통 ClusterIP로 충분합니다.
6. **교차 영역 로드 밸런싱 활성화**: 대상 용량·영역 장애 테스트·전송 비용에 따라 교차 영역 동작을 선택합니다. 활성화만으로 고가용성이 보장되지 않습니다.
7. **적절한 대상 유형 선택**: 포드 IP를 직접 대상으로 사용하려면 `ip` 대상 유형을, 노드 IP를 대상으로 사용하려면 `instance` 대상 유형을 선택합니다.

## 네트워크 정책

NetworkPolicy는 적용 엔진이 활성화된 경우 선택한 Pod와 방향의 L3/L4 통신을 제어합니다. 지원되는 EC2/Linux 환경의 Amazon VPC CNI는 네이티브 네트워크 정책을 지원하므로 다른 CNI 설치가 필수는 아닙니다. 정확한 add-on 버전, 커널·컴퓨팅 제약, standard/strict 모드와 관리되는 Pod 요건은 [AWS 안내](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)를 확인하세요.

<!-- Diagram repair pending: see batch report.
![외부 트래픽 제한, Pod 간 통신 허용, 이그레스 제한, 네임스페이스 격리라는 네 가지 네트워크 정책이 외부 서비스에서 프론트엔드 Pod로, 프론트엔드에서 백엔드 Pod로(TCP 80), 백엔드에서 데이터베이스 Pod로(TCP 5432), 백엔드에서 외부 HTTPS(443)로 향하는 트래픽을 각각 어떻게 제어하는지 보여준다.](../.gitbook/assets/ko-eks-03-eks-networking-part2-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-03-eks-networking-part2-4.html)
-->

### 정책 구현 선택

EKS 관리형 VPC CNI add-on은 `describe-addon-configuration` 확인 후 아래 조각을 기존 구성에 병합하여 소유 관리 도구로 적용합니다. 다른 설정을 보존하세요. 정책 객체 존재 여부만 보지 말고 허용·거부 TCP 테스트로 실제 적용을 확인합니다.
```json
{"enableNetworkPolicy":"true"}
```
Calico는 대안 정책 엔진입니다. VPC CNI와 함께 사용할 때는 `cni.type: AmazonVPC`, Pod IP 주석 권한과 버전 호환성을 포함한 [공식 EKS 정책 전용 절차](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)를 따릅니다. VPC CNI 네이티브 정책 엔진을 동시에 활성화하지 마세요. 기존 VPC CNI 클러스터에 VXLAN 매니페스트를 적용하는 것은 정책 전용 설치가 아닙니다. 네트워크 교체에는 별도 이전 설계가 필요합니다.

### 기본 네트워크 정책

해당 방향을 선택하는 NetworkPolicy가 없으면 Pod는 그 방향에 대해 비격리 상태이지만 경로·보안 그룹 등 다른 제어는 적용됩니다. Ingress와 Egress 격리는 별개이며 일치하는 정책의 허용 규칙은 합집합입니다. 양쪽이 격리된 연결은 소스 egress와 대상 ingress 모두 허용해야 하며 응답 트래픽은 암묵적으로 허용됩니다. 아래 정책은 대안 예제이며 순서대로 누적 적용하여 더 제한하는 구성이 아닙니다. 네임스페이스 전체 ingress 허용을 함께 적용하면 뒤의 frontend 전용 정책이 의도한 제한이 완화됩니다.

### 네임스페이스 격리 정책

`my-namespace`의 모든 Pod를 선택하여 **ingress만** 격리하고 같은 네임스페이스에서 모든 포트의 연결을 허용합니다. Egress는 제한하지 않습니다. 네임스페이스와 워크로드 레이블을 먼저 준비하세요.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-isolation
  namespace: my-namespace
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector: {}
```

### 특정 포드 간 통신 허용 정책

특정 레이블을 가진 포드 간 통신만 허용하는 정책:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: my-namespace
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
```

### 외부 트래픽 제한 정책

소스 CIDR에 대한 ingress 허용 예제로 다른 정책의 허용과 합쳐집니다. 정책 적용 지점에서 보이는 소스 IP를 판단하므로 NAT·NodePort·로드 밸런서가 주소를 바꿀 수 있습니다. 프론트엔드 로드 밸런서 SG나 WAF 규칙을 대체하지 않습니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
  namespace: my-namespace
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 192.168.1.0/24
        except:
        - 192.168.1.10/32
    ports:
    - protocol: TCP
      port: 80
```

### 이그레스(Egress) 트래픽 제한 정책

특정 대상으로만 이그레스 트래픽을 허용하는 정책: `203.0.113.0/24`는 문서용 주소이므로 승인된 실제 외부 목적지로 바꿉니다. DNS 허용은 일반 CoreDNS Pod를 전제로 하며 NodeLocal DNS 등에서는 실제 경로에 맞춰야 합니다. `0.0.0.0/0`에서 RFC1918만 제외해도 특정 외부 서비스만 허용하거나 인스턴스 메타데이터를 확실히 차단하는 것은 아닙니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: limit-egress-traffic
  namespace: my-namespace
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: db
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - protocol: TCP
      port: 443
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
```

### 네트워크 정책 모범 사례

![네트워크 정책 모범 사례라는 원칙 하나에서 기본 거부 정책 적용, 네임스페이스 격리, 최소 권한 원칙 적용, 이그레스 트래픽 제한, 정책 테스트라는 다섯 가지 실천 항목이 뻗어나가는 구조를 보여준다.](../.gitbook/assets/ko-eks-03-eks-networking-part2-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-03-eks-networking-part2-5.html)

1. **기본 거부 정책 적용**: 모든 트래픽을 기본적으로 거부하고 필요한 트래픽만 명시적으로 허용합니다.
2. **네임스페이스 격리**: 네임스페이스 간 통신을 제한하여 보안을 강화합니다.
3. **최소 권한 원칙 적용**: 필요한 최소한의 통신만 허용합니다.
4. **이그레스 트래픽 제한**: 포드에서 나가는 트래픽도 제한하여 보안을 강화합니다.
5. **정책 테스트**: 네트워크 정책을 적용하기 전에 테스트하여 의도하지 않은 통신 차단을 방지합니다.

---

## Gateway API

### 개요

Gateway API는 인프라 소유권(GatewayClass/Gateway)과 애플리케이션 경로를 분리합니다. LBC는 **ALB와 NLB Gateway를 각각** 사용하며 하나의 Gateway에 L4와 L7 경로를 혼합하지 않습니다. ALB는 HTTPRoute/GRPCRoute, NLB는 TCPRoute/UDPRoute/TLSRoute를 컨트롤러가 지원하는 기능 범위에서 처리합니다.

<!-- Diagram repair pending: see batch report.
![GatewayClass가 Gateway를 정의하고, Gateway가 L7 트래픽을 처리하는 HTTPRoute와 L4 트래픽을 처리하는 TCPRoute로 나뉘어 각각 ALB와 NLB를 통해 세 서비스로 라우팅되는 계층 구조를 보여준다.](../.gitbook/assets/ko-eks-03-eks-networking-part2-6.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-03-eks-networking-part2-6.html)
-->

### 사전 요구 사항

예제는 LBC **3.5.0**이 명시한 Gateway API **1.6.0**을 기준으로 합니다. 이전 L4 지원은 2.13.3, L7 지원은 2.14.0부터이므로 “2.13+에서 전부 지원”은 틀립니다. 3.5.0은 CRD를 감지하고 `NLBGatewayAPI`/`ALBGatewayAPI`를 기본 활성화합니다. `EnableGatewayAPI`라는 gate는 없습니다. TCPRoute와 UDPRoute는 이제 standard 채널의 v1 리소스이므로 이전 experimental CRD를 무조건 설치하지 마세요.
```bash
set -euo pipefail
curl --fail --show-error --location \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.0/standard-install.yaml \
  --output gateway-standard-v1.6.0.yaml
curl --fail --show-error --location \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/config/crd/gateway/gateway-crds.yaml \
  --output lbc-gateway-crds-v3.5.0.yaml
```
클러스터 범위 갱신을 적용하기 전에 다운로드 내용과 기존 CRD 소유권·저장 버전을 검토합니다. 기존 설치는 릴리스 이전 절차를 따르세요. CRD 없이 시작한 컨트롤러는 CRD 준비 후 재시작 또는 재조정하여 활성 상태를 확인합니다.
```bash
kubectl apply --server-side -f gateway-standard-v1.6.0.yaml
kubectl apply --server-side -f lbc-gateway-crds-v3.5.0.yaml
kubectl get crd gateways.gateway.networking.k8s.io \
  tcproutes.gateway.networking.k8s.io udproutes.gateway.networking.k8s.io \
  loadbalancerconfigurations.gateway.k8s.aws
```


### GatewayClass 및 Gateway 설정

`gateway-demo` 전용 네임스페이스, 아래에서 참조하는 Service와 준비된 워크로드를 먼저 만듭니다. ACM ARN과 소스 CIDR을 교체하고 ALB와 같은 리전에서 사용 가능한 인증서를 준비하세요. 구성 예제이며 프로덕션 실행 검증 결과는 아닙니다. 기본 TargetGroupConfiguration 참조로 ClusterIP 백엔드에 IP 대상을 사용합니다. 그렇지 않으면 컨트롤러 기본값인 instance 대상으로 NodePort가 필요할 수 있습니다. 이 LBC 전용 HTTPS 패턴은 LoadBalancerConfiguration으로 ACM을 지정하며 지원하지 않는 `tls.certificateRefs`를 생략합니다.
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-alb
spec:
  controllerName: gateway.k8s.aws/alb
---
apiVersion: gateway.k8s.aws/v1
kind: TargetGroupConfiguration
metadata:
  name: ip-targets
  namespace: gateway-demo
spec:
  defaultConfiguration:
    targetType: ip
---
apiVersion: gateway.k8s.aws/v1
kind: LoadBalancerConfiguration
metadata:
  name: alb-config
  namespace: gateway-demo
spec:
  scheme: internal
  sourceRanges:
  - 10.0.0.0/16
  defaultTargetGroupConfiguration:
    name: ip-targets
  listenerConfigurations:
  - protocolPort: HTTPS:443
    defaultCertificate: arn:aws:acm:us-west-2:123456789012:certificate/00000000-0000-4000-8000-000000000000
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-hotel-gateway
  namespace: gateway-demo
spec:
  gatewayClassName: amazon-alb
  infrastructure:
    parametersRef:
      group: gateway.k8s.aws
      kind: LoadBalancerConfiguration
      name: alb-config
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: app.example.com
    allowedRoutes:
      namespaces:
        from: Same
```


### HTTPRoute 예제 (L7 → ALB)

90/10 가중치는 `/api`에 일치하는 요청에 적용되며 정확한 요청 수 비율이나 상태 기반 장애 전환을 보장하지 않습니다. 호스트명이 일치하는 HTTPS 리스너에 연결합니다. 백엔드 포트는 Service 포트이며 다른 네임스페이스의 경로·백엔드는 allowedRoutes/ReferenceGrant 제어가 필요합니다.
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: gateway-demo
spec:
  parentRefs:
  - name: my-hotel-gateway
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: api-service
      port: 80
      weight: 90
    - name: api-service-v2
      port: 80
      weight: 10
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: frontend-service
      port: 80
```


### TCPRoute 예제 (L4 → NLB)

별도의 내부 NLB Gateway가 `ip-targets`를 재사용합니다. `postgres-service`는 `gateway-demo`에 존재하고 실제 targetPort에 준비된 라우팅 가능 대상이 있어야 합니다. TCP 리스너는 바이트를 전달하며 데이터베이스 인증이나 TLS를 대신 설정하지 않습니다.
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-nlb
spec:
  controllerName: gateway.k8s.aws/nlb
---
apiVersion: gateway.k8s.aws/v1
kind: LoadBalancerConfiguration
metadata:
  name: nlb-config
  namespace: gateway-demo
spec:
  scheme: internal
  sourceRanges:
  - 10.0.0.0/16
  defaultTargetGroupConfiguration:
    name: ip-targets
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-nlb-gateway
  namespace: gateway-demo
spec:
  gatewayClassName: amazon-nlb
  infrastructure:
    parametersRef:
      group: gateway.k8s.aws
      kind: LoadBalancerConfiguration
      name: nlb-config
  listeners:
  - name: tcp
    protocol: TCP
    port: 5432
    allowedRoutes:
      namespaces:
        from: Same
---
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


### QUIC/HTTP3 지원

ALB HTTPS 리스너가 자동으로 HTTP/3가 되지는 않습니다. LBC 3.5.0의 QUIC 지원은 `listenerConfigurations[].quicEnabled`를 사용하는 **NLB UDP/TCP_UDP 리스너**용입니다. IP 대상과 보안 그룹이 연결되지 않은 NLB가 필요하며 백엔드가 직접 QUIC/HTTP3를 종료해야 합니다. 다음은 UDP:443 리스너·UDPRoute가 있는 별도 NLB Gateway에 연결할 구성 요소이지 ALB 설정이나 완성된 배포가 아닙니다. SG 없는 설계 선택 전 대상 측 보안과 헬스체크를 계획하세요.
```yaml
apiVersion: gateway.k8s.aws/v1
kind: LoadBalancerConfiguration
metadata:
  name: quic-config
  namespace: gateway-demo
spec:
  scheme: internal
  disableSecurityGroup: true
  defaultTargetGroupConfiguration:
    name: ip-targets
  listenerConfigurations:
  - protocolPort: UDP:443
    quicEnabled: true
```


### 인증서 디스커버리

정적 인증서는 `LoadBalancerConfiguration.spec.listenerConfigurations[].defaultCertificate`에 지정하며 추가 ARN은 `certificates`를 사용합니다. 또는 보안 리스너가 있을 때 리스너와 연결된 경로의 호스트명으로 일치하는 ACM 인증서를 찾습니다. HTTPRoute만으로 HTTPS 리스너가 추가되거나 인증서가 발급되지는 않습니다. 이 LBC 릴리스는 Kubernetes Secret을 가리키는 Gateway `certificateRefs`를 지원하지 않으므로 Secret 생성만으로 ACM에 가져오지 않습니다.

### 보안 그룹

기본적으로 LBC는 프론트엔드/백엔드 SG 경로를 관리합니다. 사용자 지정 프론트엔드 SG는 `gateway.k8s.aws/security-group-ids`가 아니라 LoadBalancerConfiguration으로 지정합니다. 아래 필드를 기존 `alb-config`의 인증서·scheme·대상 설정을 보존하면서 병합하고 프론트엔드 규칙은 별도로 구성합니다. 명시한 프론트엔드 SG 위에 `sourceRanges`가 추가 필터로 적용되는 것은 아닙니다. 백엔드 규칙 소유권을 확인하고 필요한 대상·헬스체크 포트만 허용하세요.
```yaml
apiVersion: gateway.k8s.aws/v1
kind: LoadBalancerConfiguration
metadata:
  name: alb-config
  namespace: gateway-demo
spec:
  securityGroups:
  - sg-0123456789abcdef0
  manageBackendSecurityGroupRules: true
```


### Out-of-Band 대상 그룹

LBC 확장은 Kubernetes TargetGroupBinding이 아니라 `group: ""`, `kind: TargetGroupName`과 **기존 AWS 대상 그룹 이름**을 사용합니다. 등록·수명 주기·프로토콜·VPC·로드 밸런서 연결 호환성은 외부 소유자가 관리합니다. 아래는 앞의 루트 경로에 대한 대안이므로 같은 리스너에 충돌하는 루트 경로를 중복 생성하지 마세요.
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: oob-route
  namespace: gateway-demo
spec:
  parentRefs:
  - name: my-hotel-gateway
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - backendRefs:
    - group: ""
      kind: TargetGroupName
      name: existing-target-group
      weight: 1
```


### Gateway API vs Ingress 비교

| 기능 | LBC Ingress | LBC 3.5.0 Gateway API |
|---|---|---|
| 라우팅 | 호스트/경로와 컨트롤러 어노테이션 | HTTPRoute/GRPCRoute 조건과 지원 확장 |
| L4 | 별도 NLB Service 사용 | TCPRoute/UDPRoute/TLSRoute를 쓰는 별도 NLB Gateway |
| 트래픽 분할 | 참조된 weighted-forward action | Route 백엔드 가중치 |
| 소유권 | IngressClass와 Ingress | GatewayClass, Gateway, Route 역할 |
| TLS 인증서 | ACM 어노테이션/디스커버리 | ACM LoadBalancerConfiguration/디스커버리; Secret certificateRefs 미지원 |
| 이식성 | 컨트롤러별 어노테이션 | 컨트롤러 적합성 확인; 모든 표준 필터를 구현하지 않음 |

공식 참고: [LBC Gateway API](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/gateway/), [LoadBalancerConfiguration](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/loadbalancerconfig/), [Kubernetes Service](https://kubernetes.io/docs/concepts/services-networking/service/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../quizzes/eks/03-eks-networking-part2-quiz.md)를 풀어보세요.
