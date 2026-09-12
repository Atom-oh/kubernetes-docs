# AWS Load Balancer Controller 퀴즈

직접 관리하는 LBC v3.5.0 본문을 기준으로 합니다.

## 1. AWS Load Balancer Controller는 무엇을 관리하나요?

- A. 노드 수명주기를 포함한 모든 클라우드 공급자 역할
- B. Kubernetes 리소스에서 조정하는 지원 AWS 로드밸런서 리소스
- C. kube-proxy 패킷 전달
- D. 모든 파드의 CoreDNS 레코드

<details>
<summary>정답 보기</summary>

B. LBC는 지원되는 ALB/NLB, 대상 그룹, 리스너와 관련 리소스를 관리합니다. kube-proxy, CNI, DNS 또는 모든 클라우드 컨트롤러 책임을 대체하지 않습니다. 기존 AWS 공급자와 EKS Auto Mode는 별도 구현이며 LBC가 모든 ELB 제품의 모든 기능을 구현한다고 설명하면 안 됩니다.

</details>

## 2. ALB의 ip 대상과 instance 대상은 어떻게 다른가요?

- A. ip는 파드 IP를 등록하고 instance는 노드 NodePort로 전달
- B. ip는 항상 NodePort를 사용
- C. 두 방식은 동일
- D. instance는 IPv6 전용

<details>
<summary>정답 보기</summary>

A. IP 대상에는 지원되는 VPC 라우팅 가능 파드 주소와 엔드포인트/ENI 탐색이 필요합니다. Amazon VPC CNI가 일반적인 EKS 선택이지만 호환되는 대안 CNI 구성도 가능합니다. Instance 대상에는 NodePort를 사용할 수 있는 Service와 적절한 노드 네트워킹이 필요합니다. 직접 대상 지정만으로 모든 워크로드의 지연 시간 이점이 증명되지는 않습니다.

</details>

## 3. 컨트롤러에 IRSA 또는 EKS Pod Identity를 통한 IAM 역할이 필요한 이유는 무엇인가요?

- A. 파드 네트워킹을 대체하기 위해
- B. AWS API 호출을 인증하고 인가하기 위해
- C. Kubernetes RBAC를 대체하기 위해
- D. 모든 백엔드 요청을 인증하기 위해

<details>
<summary>정답 보기</summary>

B. 컨트롤러는 로드밸런서, 대상 그룹, 리스너와 관련 보안 그룹을 만들고 관리하기 위해 AWS API를 호출합니다. IRSA와 지원되는 Pod Identity 구성은 대안입니다. 역할은 연결된 정책의 권한만 부여하며 역할 사용만으로 최소 권한이 자동 보장되지는 않습니다. Kubernetes RBAC와 애플리케이션 인증은 별도입니다.

</details>

## 4. 여러 Ingress가 하나의 ALB를 공유하는 방법은 무엇인가요?

- A. 같은 네임스페이스에 있으면 충분
- B. 같은 alb.ingress.kubernetes.io/group.name 사용
- C. 모든 Ingress는 항상 같은 ALB 공유
- D. 같은 파드 이름 설정

<details>
<summary>정답 보기</summary>

B. IngressGroup은 ALB와 규칙 공간을 공유합니다. 작은 group.order부터 평가하며 같은 값이면 네임스페이스/이름 순서입니다. 그룹에 참여할 수 있는 비신뢰 사용자가 라우팅에 영향을 줄 수 있으므로 강제된 신뢰 경계 내에서 사용하세요. 모든 배포에서 비용이 줄어든다고 가정하지 말고 어노테이션 병합/독점 동작, 제한과 비용을 검토합니다.

</details>

## 5. NLB TLS 인증서를 제공하는 어노테이션은 무엇인가요?

- A. service.beta.kubernetes.io/aws-load-balancer-ssl-cert
- B. alb.ingress.kubernetes.io/certificate-arn
- C. service.beta.kubernetes.io/aws-load-balancer-tls-termination
- D. nlb.kubernetes.io/ssl-certificate

<details>
<summary>정답 보기</summary>

A. 직접 관리하는 LBC의 완전한 Service 예제는 다음과 같습니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-tls-service
  namespace: default
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:ap-northeast-2:123456789012:certificate/12345678-1234-1234-1234-123456789012
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: '443'
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: my-app
  ports:
  - name: https
    port: 443
    targetPort: 8080
    protocol: TCP
```

인증서 ARN을 교체하고 8080에서 수신하는 일치 백엔드 파드를 준비하세요. 클라이언트 TLS는 NLB에서 종료하며 여기서 tcp는 백엔드 연결에 TLS를 적용하지 않습니다. 적절한 인증서/보안 정책과 네트워크 제어가 필요합니다. Auto Mode는 별도의 loadBalancerClass와 지원 어노테이션 집합을 사용합니다.

</details>

## 6. 독립적으로 생성한 TargetGroupBinding의 목적은 무엇인가요?

- A. 모든 로드밸런서/리스너 자동 생성
- B. 기존 대상 그룹에 Kubernetes Service 대상 등록
- C. ALB HTTP 리스너 라우팅 규칙 정의
- D. IAM 인가 대체

<details>
<summary>정답 보기</summary>

B. 로드밸런서, 리스너와 대상 그룹은 이미 존재하며 Service/대상 프로토콜, 주소 계열과 포트가 맞아야 합니다.

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
  namespace: default
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:targetgroup/my-tg/1234567890abcdef
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

여러 클러스터/TGB가 대상 그룹을 공유하면 모든 참여자가 생성 시부터 multiClusterTargetGroup: true를 설정해야 합니다. 기본값은 전체 소유권을 가정하므로 외부 대상을 등록 해제할 수 있습니다. nodeSelector는 instance 대상에 적용되며 IP 모드 파드를 필터링하지 않습니다. TGB 권한은 신뢰할 수 있는 사용자로 제한하세요.

</details>

## 7. ALB에 리전 WAF v2 Web ACL을 연결하는 어노테이션은 무엇인가요?

- A. alb.ingress.kubernetes.io/waf-acl-id
- B. alb.ingress.kubernetes.io/wafv2-acl-arn
- C. alb.ingress.kubernetes.io/web-acl
- D. alb.ingress.kubernetes.io/firewall-rules

<details>
<summary>정답 보기</summary>

B. ALB와 같은 리전의 기존 regional Web ACL ARN을 지정하고 규칙 및 컨트롤러 권한을 구성합니다. WAF v2 연동은 활성화되어 있어야 하지만 기본값이 true이므로 enableWafv2를 반드시 명시해야 하는 것은 아닙니다. 연동이 비활성화되면 어노테이션을 적용하지 않습니다. WAF와 유료 Shield Advanced 보호는 서로 다른 기능입니다.

</details>

## 8. 일반적인 서브넷 역할 태그는 무엇인가요?

- A. kubernetes.io/cluster/CLUSTER_NAME만 사용
- B. 퍼블릭은 kubernetes.io/role/elb, 프라이빗은 kubernetes.io/role/internal-elb
- C. aws:cloudformation:stack-name
- D. Name=kubernetes-subnet만 사용

<details>
<summary>정답 보기</summary>

B. 직접 관리하는 LBC 탐색에서는 값으로 1 또는 빈 문자열을 사용할 수 있습니다. v2.12.1 이상은 일치하는 역할 태그가 없을 때 기본 도달성 기반 fallback으로 라우팅 테이블에서 서브넷을 분류할 수 있습니다. 명시적 서브넷과 IngressClassParams 태그 필터도 선택 경로입니다. Auto Mode에는 여전히 문서화된 태그가 필요합니다. 클러스터 태그, 가용 IP와 AZ 요구사항을 확인하며 태그가 라우팅을 변경하지는 않습니다.

</details>

## 9. ALB 고정 세션은 어떻게 구성하나요?

- A. alb.ingress.kubernetes.io/sticky-sessions=true
- B. target-group-attributes에 stickiness.enabled=true 설정
- C. Ingress에 session-affinity=cookie 설정
- D. 항상 기본 활성화

<details>
<summary>정답 보기</summary>

B. alb.ingress.kubernetes.io/target-type: ip를 설정하고 하나의 target-group-attributes 어노테이션에 stickiness.enabled=true와 적절한 쿠키 속성을 함께 넣습니다. 슬로우 스타트나 등록 해제 지연 때문에 같은 YAML 키를 반복하면 설정이 유실될 수 있습니다. 가중치 forward 동작을 사용하면 문서에 따라 해당 동작의 대상 그룹 고정 세션도 일관되게 구성하세요.

</details>

## 10. NLB 클라이언트 신원에 대한 올바른 설명은 무엇인가요?

- A. Proxy Protocol v2가 IP 패킷 소스를 클라이언트 주소로 변경
- B. externalTrafficPolicy: Local이 모든 대상 모드에서 원본 IP 보장
- C. Proxy Protocol은 메타데이터를 전달하고 패킷 소스 보존은 네트워크/프로토콜 제약을 가진 별도 설정
- D. NLB는 항상 클라이언트 IP 보존

<details>
<summary>정답 보기</summary>

C. 백엔드는 애플리케이션 데이터 전에 Proxy Protocol v2를 해석하고 해당 상태 검사도 지원해야 합니다. preserve_client_ip.enabled는 지원되는 경우 패킷 소스 보존을 제어합니다. Instance/NodePort 모드의 externalTrafficPolicy: Local은 이후 kube-proxy SNAT 홉을 피할 수 있지만 모든 NLB 경로나 IP 계열 변환을 해결하지는 않습니다. NLB 가중치는 일반적으로 새 연결에 영향을 주지만 0으로 설정하면 잠시 후 기존 연결도 닫힙니다.

</details>

## 11. ALB HTTP→HTTPS 리다이렉트 어노테이션은 무엇인가요?

- A. alb.ingress.kubernetes.io/force-ssl-redirect
- B. alb.ingress.kubernetes.io/ssl-redirect: "443"
- C. alb.ingress.kubernetes.io/http-to-https
- D. 항상 HTTPRoute가 필요

<details>
<summary>정답 보기</summary>

B. HTTP와 목적지 HTTPS 리스너 및 적절한 인증서를 구성합니다. 활성화하면 HTTP 리스너는 리다이렉트 기본 동작을 사용하고 다른 라우팅 규칙은 무시합니다. IngressGroup에 영향을 주므로 그룹 전체 동작을 검토하세요. Cognito/OIDC/JWT 인증에는 HTTPS가 필요하며 리다이렉트 자체가 애플리케이션 인가는 아닙니다.

</details>

## 12. ALB가 생성되지 않을 때 먼저 확인할 것은 무엇인가요?

- A. kube-proxy 로그만 확인
- B. 애플리케이션 쿠키 내용
- C. 컨트롤러 로그/이벤트, 클래스, IAM, 서브넷 적격성, 웹훅/CRD 상태
- D. 파드 복제본 수만 확인

<details>
<summary>정답 보기</summary>

C. 먼저 조정·제어 플레인 경로를 확인합니다. kube-proxy나 eBPF 대체 구현은 이후 노드/서비스 트래픽에서 중요할 수 있지만 실패한 AWS CreateLoadBalancer 작업의 첫 진단 대상은 아닙니다. kubectl apply 성공만으로 AWS 조정 성공이 증명되지는 않습니다. 실제 리소스 ID와 네임스페이스를 사용하고 로그 출력 범위를 제한하세요.

</details>

[본문으로 돌아가기](../../networking/03-aws-lb-controller.md)
