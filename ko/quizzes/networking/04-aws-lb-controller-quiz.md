# AWS Load Balancer Controller 퀴즈

이 퀴즈는 AWS Load Balancer Controller의 아키텍처, ALB/NLB 설정, 그리고 운영에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. AWS Load Balancer Controller가 대체하는 기존 Kubernetes 컴포넌트는?

A. kube-proxy
B. in-tree AWS 클라우드 프로바이더
C. CoreDNS
D. CNI 플러그인

<details>
<summary>정답 및 설명</summary>

**정답: B. in-tree AWS 클라우드 프로바이더**

**설명:**
AWS Load Balancer Controller는 기존 Kubernetes in-tree AWS 클라우드 프로바이더의 로드밸런서 기능을 대체합니다:
- 더 많은 기능 (ALB, NLB 고급 설정)
- 더 빠른 업데이트 및 버그 수정
- AWS 서비스와의 더 나은 통합

in-tree 프로바이더는 기본적인 ELB Classic만 지원했지만, AWS Load Balancer Controller는 ALB와 NLB의 모든 기능을 지원합니다.

</details>

### 2. ALB Ingress에서 target-type annotation의 `ip`와 `instance` 차이점으로 올바른 것은?

A. `ip`는 Pod IP를 직접 타겟으로, `instance`는 NodePort를 통해 라우팅
B. `ip`는 NodePort를 통해 라우팅, `instance`는 Pod IP를 직접 타겟으로
C. 두 옵션 모두 동일한 방식으로 동작함
D. `ip`는 IPv4만, `instance`는 IPv6만 지원

<details>
<summary>정답 및 설명</summary>

**정답: A. `ip`는 Pod IP를 직접 타겟으로, `instance`는 NodePort를 통해 라우팅**

**설명:**
Target Type 비교:

| Target Type | 동작 방식 | 장점 | 단점 |
|-------------|----------|------|------|
| `ip` | Pod IP 직접 등록 | 낮은 지연, 효율적 | VPC CNI 필요 |
| `instance` | Node의 NodePort로 라우팅 | 범용적 | 추가 홉 발생 |

`ip` 타입 사용 시 AWS VPC CNI가 필요하며, Pod IP가 직접 Target Group에 등록됩니다.

</details>

### 3. AWS Load Balancer Controller에서 IRSA(IAM Roles for Service Accounts)가 필요한 이유는?

A. Pod 간 통신을 위해
B. 컨트롤러가 AWS API를 호출하여 리소스를 생성/관리하기 위해
C. Kubernetes API 서버 인증을 위해
D. TLS 인증서 관리를 위해

<details>
<summary>정답 및 설명</summary>

**정답: B. 컨트롤러가 AWS API를 호출하여 리소스를 생성/관리하기 위해**

**설명:**
AWS Load Balancer Controller는 다음 작업을 위해 AWS API를 호출해야 합니다:
- ALB/NLB 생성 및 관리
- Target Group 생성 및 타겟 등록
- Listener 및 규칙 설정
- 보안 그룹 관리
- ACM 인증서 조회

IRSA를 통해 Service Account에 IAM Role을 연결하면:
- Pod가 AWS API에 인증 가능
- 최소 권한 원칙 적용
- 노드 전체가 아닌 특정 Pod에만 권한 부여

</details>

### 4. ALB Ingress에서 여러 Ingress 리소스를 하나의 ALB로 통합하는 방법은?

A. 같은 namespace에 배포
B. `alb.ingress.kubernetes.io/group.name` annotation 사용
C. 같은 IngressClass 사용
D. ALB는 항상 하나의 Ingress만 지원

<details>
<summary>정답 및 설명</summary>

**정답: B. `alb.ingress.kubernetes.io/group.name` annotation 사용**

**설명:**
Ingress Group 기능:

```yaml
# Ingress 1
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "1"
---
# Ingress 2
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "2"
```

장점:
- ALB 비용 절감 (여러 서비스가 하나의 ALB 공유)
- 중앙집중화된 관리
- 순서 지정으로 규칙 우선순위 제어

</details>

### 5. NLB Service에서 TLS 종료를 구현하기 위한 annotation은?

A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`
B. `alb.ingress.kubernetes.io/certificate-arn`
C. `service.beta.kubernetes.io/aws-load-balancer-tls-termination`
D. `nlb.kubernetes.io/ssl-certificate`

<details>
<summary>정답 및 설명</summary>

**정답: A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`**

**설명:**
NLB TLS 종료 설정:

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:..."
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
  ports:
    - port: 443
      targetPort: 8080
```

`alb.ingress.kubernetes.io/certificate-arn`은 ALB Ingress용 annotation입니다.

</details>

### 6. TargetGroupBinding CRD의 주요 용도는?

A. 새로운 Target Group을 자동으로 생성
B. 기존 AWS Target Group을 Kubernetes Service와 연결
C. ALB Listener 규칙 정의
D. 보안 그룹 자동 생성

<details>
<summary>정답 및 설명</summary>

**정답: B. 기존 AWS Target Group을 Kubernetes Service와 연결**

**설명:**
TargetGroupBinding 사용 사례:
1. 기존 인프라 마이그레이션 - 이미 존재하는 Target Group 활용
2. 여러 클러스터 공유 - 하나의 ALB/NLB를 여러 클러스터에서 사용
3. 직접 Target Group 관리가 필요한 경우

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:...
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

</details>

### 7. ALB Ingress에서 WAF v2를 연동하기 위한 annotation은?

A. `alb.ingress.kubernetes.io/waf-acl-id`
B. `alb.ingress.kubernetes.io/wafv2-acl-arn`
C. `alb.ingress.kubernetes.io/web-acl`
D. `alb.ingress.kubernetes.io/firewall-rules`

<details>
<summary>정답 및 설명</summary>

**정답: B. `alb.ingress.kubernetes.io/wafv2-acl-arn`**

**설명:**
AWS WAF v2 연동:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:ap-northeast-2:ACCOUNT:regional/webacl/my-acl/xxx
```

WAF v2 기능:
- SQL 인젝션, XSS 보호
- Rate limiting
- IP 기반 차단/허용
- 커스텀 규칙

컨트롤러 설치 시 `enableWafv2: true` 설정 필요.

</details>

### 8. AWS Load Balancer Controller에서 서브넷 자동 감지를 위한 태그는?

A. `kubernetes.io/cluster/<cluster-name>=owned`
B. `kubernetes.io/role/elb=1` (퍼블릭), `kubernetes.io/role/internal-elb=1` (프라이빗)
C. `aws:cloudformation:stack-name`
D. `Name=kubernetes-subnet`

<details>
<summary>정답 및 설명</summary>

**정답: B. `kubernetes.io/role/elb=1` (퍼블릭), `kubernetes.io/role/internal-elb=1` (프라이빗)**

**설명:**
서브넷 태깅 규칙:

```bash
# 퍼블릭 서브넷 (internet-facing ALB/NLB용)
kubernetes.io/role/elb=1

# 프라이빗 서브넷 (internal ALB/NLB용)
kubernetes.io/role/internal-elb=1

# 클러스터 소유권 (선택)
kubernetes.io/cluster/<cluster-name>=shared 또는 owned
```

태그가 없으면 컨트롤러가 적절한 서브넷을 찾지 못해 로드밸런서 생성에 실패할 수 있습니다.

</details>

### 9. ALB Ingress에서 Sticky Session을 활성화하는 annotation은?

A. `alb.ingress.kubernetes.io/sticky-sessions=true`
B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`
C. `alb.ingress.kubernetes.io/session-affinity=cookie`
D. `alb.ingress.kubernetes.io/cookie-based-routing=true`

<details>
<summary>정답 및 설명</summary>

**정답: B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`**

**설명:**
Sticky Session 설정:

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/target-group-attributes: >-
      stickiness.enabled=true,
      stickiness.lb_cookie.duration_seconds=3600
```

Target Group 속성으로 설정:
- `stickiness.enabled=true` - 활성화
- `stickiness.lb_cookie.duration_seconds` - 쿠키 유효 시간
- `stickiness.type` - lb_cookie 또는 app_cookie

Sticky Session은 세션 상태를 유지해야 하는 레거시 애플리케이션에 유용합니다.

</details>

### 10. NLB에서 클라이언트 원본 IP를 보존하는 방법은?

A. `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"` 사용
B. externalTrafficPolicy: Local 사용
C. 두 방법 모두 가능
D. NLB는 항상 클라이언트 IP를 보존함

<details>
<summary>정답 및 설명</summary>

**정답: C. 두 방법 모두 가능**

**설명:**
클라이언트 IP 보존 방법:

1. **Proxy Protocol v2**:
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: proxy_protocol_v2.enabled=true
```
- 애플리케이션이 Proxy Protocol 지원 필요

2. **externalTrafficPolicy: Local**:
```yaml
spec:
  externalTrafficPolicy: Local
```
- 추가 홉 없이 동일 노드의 Pod로만 라우팅
- 불균형한 트래픽 분산 가능성

3. **IP Target Type** (ip 모드):
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
```

</details>

### 11. ALB Ingress에서 HTTP를 HTTPS로 리다이렉트하는 annotation은?

A. `alb.ingress.kubernetes.io/actions.ssl-redirect`
B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`
C. `alb.ingress.kubernetes.io/force-ssl-redirect: "true"`
D. `alb.ingress.kubernetes.io/http-to-https: "true"`

<details>
<summary>정답 및 설명</summary>

**정답: B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`**

**설명:**
SSL 리다이렉트 설정:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
```

동작:
- HTTP(80)로 들어오는 요청을 HTTPS(443)로 301 리다이렉트
- 보안 모범 사례로 권장됨
- ACM 인증서 필요

</details>

### 12. AWS Load Balancer Controller에서 ALB가 생성되지 않을 때 확인해야 할 사항이 아닌 것은?

A. IAM 권한 확인
B. 서브넷 태그 확인
C. IngressClass 지정 확인
D. kube-proxy 로그 확인

<details>
<summary>정답 및 설명</summary>

**정답: D. kube-proxy 로그 확인**

**설명:**
ALB 생성 실패 시 확인 사항:

1. **IAM 권한**: Service Account의 IAM Role에 필요한 권한이 있는지
2. **서브넷 태그**: `kubernetes.io/role/elb=1` 또는 `kubernetes.io/role/internal-elb=1`
3. **IngressClass**: `ingressClassName: alb` 또는 annotation으로 지정
4. **컨트롤러 로그**: `kubectl logs -n kube-system deployment/aws-load-balancer-controller`
5. **Ingress 이벤트**: `kubectl describe ingress <name>`

kube-proxy는 Service의 ClusterIP/NodePort 라우팅을 담당하며, ALB 생성과는 무관합니다.

</details>

---

## 추가 학습 자료

- [AWS Load Balancer Controller 문서](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [EKS 사용자 가이드](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [ALB Annotation 레퍼런스](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/)
