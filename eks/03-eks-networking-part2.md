# EKS 네트워킹 - 2부: 서비스 및 로드 밸런싱, 네트워크 정책

## 개요

이 문서에서는 Amazon EKS에서의 서비스 및 로드 밸런싱, 네트워크 정책에 대해 알아보겠습니다. Kubernetes 서비스를 통해 애플리케이션을 노출하는 방법, AWS 로드 밸런서와의 통합, 그리고 네트워크 정책을 사용하여 포드 간 통신을 제어하는 방법을 다룹니다.

## Kubernetes 서비스 유형

Kubernetes에서는 다음과 같은 서비스 유형을 제공합니다:

1. **ClusterIP**: 클러스터 내부에서만 액세스 가능한 서비스
2. **NodePort**: 모든 노드의 특정 포트를 통해 액세스 가능한 서비스
3. **LoadBalancer**: 외부 로드 밸런서를 통해 액세스 가능한 서비스
4. **ExternalName**: 외부 서비스에 대한 CNAME 레코드 제공

### ClusterIP 서비스

ClusterIP 서비스는 클러스터 내부에서만 액세스할 수 있는 서비스입니다. 이는 기본 서비스 유형입니다.

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

NodePort 서비스는 모든 노드의 특정 포트를 통해 액세스할 수 있는 서비스입니다.

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

LoadBalancer 서비스는 외부 로드 밸런서를 통해 액세스할 수 있는 서비스입니다. EKS에서는 AWS 로드 밸런서(CLB, NLB, ALB)와 통합됩니다.

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
  type: LoadBalancer
```

### ExternalName 서비스

ExternalName 서비스는 외부 서비스에 대한 CNAME 레코드를 제공합니다.

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

### Classic Load Balancer(CLB)

기본적으로 `type: LoadBalancer`로 설정된 서비스는 Classic Load Balancer를 생성합니다. 그러나 CLB는 더 이상 권장되지 않으며, NLB 또는 ALB를 사용하는 것이 좋습니다.

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
  type: LoadBalancer
```

### Network Load Balancer(NLB)

NLB를 사용하려면 서비스에 특정 주석을 추가해야 합니다:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

NLB 추가 구성 옵션:

```yaml
metadata:
  annotations:
    # 내부 NLB 생성
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    
    # 교차 영역 로드 밸런싱 활성화
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    
    # 대상 유형 지정 (instance 또는 ip)
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    
    # TCP 프록시 프로토콜 활성화
    service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
```

### Application Load Balancer(ALB)

ALB를 사용하려면 AWS Load Balancer Controller를 설치하고 Ingress 리소스를 사용해야 합니다:

1. AWS Load Balancer Controller 설치:

```bash
# IAM 정책 다운로드
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

# IAM 정책 생성
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam-policy.json

# IAM 역할 생성 및 정책 연결 (eksctl 사용)
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Helm 저장소 추가
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# AWS Load Balancer Controller 설치
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=my-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

2. Ingress 리소스 생성:

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

ALB 추가 구성 옵션:

```yaml
metadata:
  annotations:
    # 내부 ALB 생성
    alb.ingress.kubernetes.io/scheme: internal
    
    # SSL 인증서 지정
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
    
    # HTTPS 리디렉션
    alb.ingress.kubernetes.io/actions.ssl-redirect: '{"Type": "redirect", "RedirectConfig": {"Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}'
    
    # 대상 유형 지정 (instance 또는 ip)
    alb.ingress.kubernetes.io/target-type: ip
    
    # 보안 그룹 지정
    alb.ingress.kubernetes.io/security-groups: sg-xxxx,sg-yyyy
```

### 서비스 및 로드 밸런서 모범 사례

1. **내부 서비스에는 ClusterIP 사용**: 클러스터 내부에서만 액세스하는 서비스에는 ClusterIP 유형을 사용합니다.
2. **외부 서비스에는 LoadBalancer 또는 Ingress 사용**: 외부에서 액세스해야 하는 서비스에는 LoadBalancer 유형 또는 Ingress 리소스를 사용합니다.
3. **ALB 사용**: 경로 기반 라우팅, SSL 종료, 인증 등의 기능이 필요한 경우 ALB를 사용합니다.
4. **NLB 사용**: TCP/UDP 트래픽, 고성능, 정적 IP가 필요한 경우 NLB를 사용합니다.
5. **내부 로드 밸런서 사용**: 클러스터 내부에서만 액세스하는 서비스에는 내부 로드 밸런서를 사용합니다.
6. **교차 영역 로드 밸런싱 활성화**: 고가용성을 위해 교차 영역 로드 밸런싱을 활성화합니다.
7. **적절한 대상 유형 선택**: 포드 IP를 직접 대상으로 사용하려면 `ip` 대상 유형을, 노드 IP를 대상으로 사용하려면 `instance` 대상 유형을 선택합니다.

## 네트워크 정책

네트워크 정책은 포드 간 통신을 제어하는 데 사용됩니다. EKS에서 네트워크 정책을 사용하려면 네트워크 정책을 지원하는 CNI 플러그인(예: Calico, Cilium)을 설치해야 합니다.

### Calico 설치

Calico는 EKS에서 네트워크 정책을 구현하는 데 널리 사용되는 CNI 플러그인입니다:

```bash
# Calico 설치
kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml

# Calico 상태 확인
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### 기본 네트워크 정책

기본적으로 네트워크 정책이 없는 경우 모든 포드는 서로 통신할 수 있습니다. 네트워크 정책을 적용하면 명시적으로 허용된 트래픽만 허용됩니다.

### 네임스페이스 격리 정책

특정 네임스페이스 내의 포드 간 통신만 허용하는 정책:

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

특정 IP 범위에서만 트래픽을 허용하는 정책:

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

특정 대상으로만 이그레스 트래픽을 허용하는 정책:

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
        cidr: 0.0.0.0/0
        except:
        - 10.0.0.0/8
        - 172.16.0.0/12
        - 192.168.0.0/16
    ports:
    - protocol: TCP
      port: 443
```

### 네트워크 정책 모범 사례

1. **기본 거부 정책 적용**: 모든 트래픽을 기본적으로 거부하고 필요한 트래픽만 명시적으로 허용합니다.
2. **네임스페이스 격리**: 네임스페이스 간 통신을 제한하여 보안을 강화합니다.
3. **최소 권한 원칙 적용**: 필요한 최소한의 통신만 허용합니다.
4. **이그레스 트래픽 제한**: 포드에서 나가는 트래픽도 제한하여 보안을 강화합니다.
5. **정책 테스트**: 네트워크 정책을 적용하기 전에 테스트하여 의도하지 않은 통신 차단을 방지합니다.

## AWS VPC CNI

AWS VPC CNI(Container Network Interface)는 EKS의 기본 네트워킹 플러그인으로, 포드에 VPC IP 주소를 할당합니다.

### AWS VPC CNI 작동 방식

AWS VPC CNI는 다음과 같은 방식으로 작동합니다:

1. 각 노드는 VPC의 보조 IP 주소를 할당받습니다.
2. 포드가 생성되면 CNI는 이러한 보조 IP 주소 중 하나를 포드에 할당합니다.
3. 포드는 VPC 내에서 고유한 IP 주소를 가지게 됩니다.
4. 포드 간 통신은 VPC 네트워킹을 통해 이루어집니다.

### AWS VPC CNI 구성

AWS VPC CNI는 다음과 같은 구성 옵션을 제공합니다:

1. **WARM_IP_TARGET**: 각 노드에 유지할 사용 가능한 IP 주소 수
2. **WARM_ENI_TARGET**: 각 노드에 유지할 사용 가능한 ENI(Elastic Network Interface) 수
3. **AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG**: 사용자 정의 네트워킹 활성화
4. **ENI_CONFIG_LABEL_DEF**: ENI 구성에 사용할 노드 레이블
5. **DISABLE_TCP_EARLY_DEMUX**: TCP 조기 역다중화 비활성화

```bash
# AWS VPC CNI 구성 확인
kubectl describe daemonset aws-node -n kube-system

# AWS VPC CNI 구성 업데이트
kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5
```

### 사용자 정의 네트워킹

AWS VPC CNI는 사용자 정의 네트워킹을 지원하여 포드에 특정 서브넷의 IP 주소를 할당할 수 있습니다:

1. 사용자 정의 네트워킹 활성화:

```bash
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
```

2. ENIConfig 생성:

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-xxxxxxxxxxxxxxxxx
  securityGroups:
  - sg-xxxxxxxxxxxxxxxxx
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2b
spec:
  subnet: subnet-yyyyyyyyyyyyyyyyy
  securityGroups:
  - sg-yyyyyyyyyyyyyyyyy
```

3. 노드에 레이블 지정:

```bash
kubectl label node ip-192-168-1-100.us-west-2.compute.internal k8s.amazonaws.com/eniConfig=us-west-2a
kubectl label node ip-192-168-2-200.us-west-2.compute.internal k8s.amazonaws.com/eniConfig=us-west-2b
```

### 보조 CIDR 블록

VPC에 보조 CIDR 블록을 추가하여 포드 IP 주소 공간을 확장할 수 있습니다:

1. VPC에 보조 CIDR 블록 추가:

```bash
aws ec2 associate-vpc-cidr-block \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --cidr-block 100.64.0.0/16
```

2. 보조 CIDR 블록에 서브넷 생성:

```bash
aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --cidr-block 100.64.0.0/19 \
  --availability-zone us-west-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Pod-Subnet-1}]'

aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --cidr-block 100.64.32.0/19 \
  --availability-zone us-west-2b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Pod-Subnet-2}]'
```

3. 사용자 정의 네트워킹 구성:

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-xxxxxxxxxxxxxxxxx  # 100.64.0.0/19 서브넷
  securityGroups:
  - sg-xxxxxxxxxxxxxxxxx
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2b
spec:
  subnet: subnet-yyyyyyyyyyyyyyyyy  # 100.64.32.0/19 서브넷
  securityGroups:
  - sg-yyyyyyyyyyyyyyyyy
```

### AWS VPC CNI 모범 사례

1. **IP 주소 계획**: 노드 및 포드 수에 맞게 충분한 IP 주소 공간을 계획합니다.
2. **보조 CIDR 블록 사용**: 포드 IP 주소 공간을 확장하기 위해 보조 CIDR 블록을 사용합니다.
3. **사용자 정의 네트워킹**: 포드를 특정 서브넷에 배치하기 위해 사용자 정의 네트워킹을 구성합니다.
4. **WARM_IP_TARGET 최적화**: 노드당 유지할 사용 가능한 IP 주소 수를 최적화합니다.
5. **보안 그룹**: 포드에 적절한 보안 그룹을 할당합니다.

## 결론

이 문서에서는 EKS에서의 서비스 및 로드 밸런싱, 네트워크 정책에 대해 알아보았습니다. Kubernetes 서비스를 통해 애플리케이션을 노출하는 방법, AWS 로드 밸런서와의 통합, 그리고 네트워크 정책을 사용하여 포드 간 통신을 제어하는 방법을 다루었습니다. 다음 부분에서는 EKS 네트워킹의 성능 최적화, 문제 해결, 고급 사용 사례에 대해 알아보겠습니다.
