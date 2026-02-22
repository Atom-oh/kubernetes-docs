# AWS Load Balancer Controller Quiz

This quiz tests your understanding of AWS Load Balancer Controller architecture, ALB/NLB configuration, and operations.

## Quiz Questions

### 1. Which existing Kubernetes component does AWS Load Balancer Controller replace?

A. kube-proxy
B. in-tree AWS cloud provider
C. CoreDNS
D. CNI plugin

<details>
<summary>Show Answer</summary>

**Answer: B. in-tree AWS cloud provider**

**Explanation:**
AWS Load Balancer Controller replaces the load balancer functionality of the existing Kubernetes in-tree AWS cloud provider:
- More features (advanced ALB, NLB configuration)
- Faster updates and bug fixes
- Better integration with AWS services

The in-tree provider only supported basic ELB Classic, while AWS Load Balancer Controller supports all features of ALB and NLB.

</details>

### 2. What is the correct difference between `ip` and `instance` target-type annotations in ALB Ingress?

A. `ip` targets Pod IP directly, `instance` routes through NodePort
B. `ip` routes through NodePort, `instance` targets Pod IP directly
C. Both options behave the same way
D. `ip` supports only IPv4, `instance` supports only IPv6

<details>
<summary>Show Answer</summary>

**Answer: A. `ip` targets Pod IP directly, `instance` routes through NodePort**

**Explanation:**
Target Type comparison:

| Target Type | Behavior | Pros | Cons |
|-------------|----------|------|------|
| `ip` | Register Pod IP directly | Low latency, efficient | Requires VPC CNI |
| `instance` | Route to Node's NodePort | Universal | Extra hop |

When using `ip` type, AWS VPC CNI is required, and Pod IPs are registered directly in the Target Group.

</details>

### 3. Why is IRSA (IAM Roles for Service Accounts) required for AWS Load Balancer Controller?

A. For Pod-to-Pod communication
B. For the controller to call AWS APIs to create/manage resources
C. For Kubernetes API server authentication
D. For TLS certificate management

<details>
<summary>Show Answer</summary>

**Answer: B. For the controller to call AWS APIs to create/manage resources**

**Explanation:**
AWS Load Balancer Controller needs to call AWS APIs for:
- Creating and managing ALB/NLB
- Creating Target Groups and registering targets
- Configuring Listeners and rules
- Managing security groups
- Querying ACM certificates

With IRSA linking IAM Role to Service Account:
- Pods can authenticate to AWS API
- Least privilege principle applied
- Permissions granted to specific Pods, not entire nodes

</details>

### 4. How do you consolidate multiple Ingress resources into a single ALB?

A. Deploy in the same namespace
B. Use `alb.ingress.kubernetes.io/group.name` annotation
C. Use the same IngressClass
D. ALB always supports only one Ingress

<details>
<summary>Show Answer</summary>

**Answer: B. Use `alb.ingress.kubernetes.io/group.name` annotation**

**Explanation:**
Ingress Group feature:

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

Benefits:
- ALB cost savings (multiple services share one ALB)
- Centralized management
- Rule priority control with order specification

</details>

### 5. What is the annotation for implementing TLS termination on an NLB Service?

A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`
B. `alb.ingress.kubernetes.io/certificate-arn`
C. `service.beta.kubernetes.io/aws-load-balancer-tls-termination`
D. `nlb.kubernetes.io/ssl-certificate`

<details>
<summary>Show Answer</summary>

**Answer: A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`**

**Explanation:**
NLB TLS termination configuration:

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

`alb.ingress.kubernetes.io/certificate-arn` is the annotation for ALB Ingress.

</details>

### 6. What is the primary purpose of the TargetGroupBinding CRD?

A. Automatically create new Target Groups
B. Connect existing AWS Target Groups to Kubernetes Services
C. Define ALB Listener rules
D. Auto-create security groups

<details>
<summary>Show Answer</summary>

**Answer: B. Connect existing AWS Target Groups to Kubernetes Services**

**Explanation:**
TargetGroupBinding use cases:
1. Migrating existing infrastructure - Leverage existing Target Groups
2. Multi-cluster sharing - Use one ALB/NLB across multiple clusters
3. When direct Target Group management is needed

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

### 7. What is the annotation for integrating WAF v2 with ALB Ingress?

A. `alb.ingress.kubernetes.io/waf-acl-id`
B. `alb.ingress.kubernetes.io/wafv2-acl-arn`
C. `alb.ingress.kubernetes.io/web-acl`
D. `alb.ingress.kubernetes.io/firewall-rules`

<details>
<summary>Show Answer</summary>

**Answer: B. `alb.ingress.kubernetes.io/wafv2-acl-arn`**

**Explanation:**
AWS WAF v2 integration:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:ACCOUNT:regional/webacl/my-acl/xxx
```

WAF v2 features:
- SQL injection, XSS protection
- Rate limiting
- IP-based blocking/allowing
- Custom rules

`enableWafv2: true` setting required when installing the controller.

</details>

### 8. What are the tags for automatic subnet discovery in AWS Load Balancer Controller?

A. `kubernetes.io/cluster/<cluster-name>=owned`
B. `kubernetes.io/role/elb=1` (public), `kubernetes.io/role/internal-elb=1` (private)
C. `aws:cloudformation:stack-name`
D. `Name=kubernetes-subnet`

<details>
<summary>Show Answer</summary>

**Answer: B. `kubernetes.io/role/elb=1` (public), `kubernetes.io/role/internal-elb=1` (private)**

**Explanation:**
Subnet tagging rules:

```bash
# Public subnets (for internet-facing ALB/NLB)
kubernetes.io/role/elb=1

# Private subnets (for internal ALB/NLB)
kubernetes.io/role/internal-elb=1

# Cluster ownership (optional)
kubernetes.io/cluster/<cluster-name>=shared or owned
```

Without these tags, the controller may fail to find appropriate subnets and load balancer creation will fail.

</details>

### 9. What is the annotation to enable Sticky Sessions in ALB Ingress?

A. `alb.ingress.kubernetes.io/sticky-sessions=true`
B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`
C. `alb.ingress.kubernetes.io/session-affinity=cookie`
D. `alb.ingress.kubernetes.io/cookie-based-routing=true`

<details>
<summary>Show Answer</summary>

**Answer: B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`**

**Explanation:**
Sticky Session configuration:

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/target-group-attributes: >-
      stickiness.enabled=true,
      stickiness.lb_cookie.duration_seconds=3600
```

Configured as Target Group attributes:
- `stickiness.enabled=true` - Enable
- `stickiness.lb_cookie.duration_seconds` - Cookie validity duration
- `stickiness.type` - lb_cookie or app_cookie

Sticky Sessions are useful for legacy applications that need to maintain session state.

</details>

### 10. How do you preserve client source IP in NLB?

A. Use `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"`
B. Use externalTrafficPolicy: Local
C. Both methods are possible
D. NLB always preserves client IP

<details>
<summary>Show Answer</summary>

**Answer: C. Both methods are possible**

**Explanation:**
Methods to preserve client IP:

1. **Proxy Protocol v2**:
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: proxy_protocol_v2.enabled=true
```
- Application must support Proxy Protocol

2. **externalTrafficPolicy: Local**:
```yaml
spec:
  externalTrafficPolicy: Local
```
- Routes only to Pods on the same node without extra hops
- Possible uneven traffic distribution

3. **IP Target Type** (ip mode):
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
```

</details>

### 11. What is the annotation to redirect HTTP to HTTPS in ALB Ingress?

A. `alb.ingress.kubernetes.io/actions.ssl-redirect`
B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`
C. `alb.ingress.kubernetes.io/force-ssl-redirect: "true"`
D. `alb.ingress.kubernetes.io/http-to-https: "true"`

<details>
<summary>Show Answer</summary>

**Answer: B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`**

**Explanation:**
SSL redirect configuration:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
```

Behavior:
- 301 redirect requests coming to HTTP(80) to HTTPS(443)
- Recommended as security best practice
- Requires ACM certificate

</details>

### 12. Which is NOT something to check when ALB is not being created by AWS Load Balancer Controller?

A. Check IAM permissions
B. Check subnet tags
C. Check IngressClass specification
D. Check kube-proxy logs

<details>
<summary>Show Answer</summary>

**Answer: D. Check kube-proxy logs**

**Explanation:**
Things to check when ALB creation fails:

1. **IAM permissions**: Whether Service Account's IAM Role has required permissions
2. **Subnet tags**: `kubernetes.io/role/elb=1` or `kubernetes.io/role/internal-elb=1`
3. **IngressClass**: Specify `ingressClassName: alb` or via annotation
4. **Controller logs**: `kubectl logs -n kube-system deployment/aws-load-balancer-controller`
5. **Ingress events**: `kubectl describe ingress <name>`

kube-proxy handles Service ClusterIP/NodePort routing and is unrelated to ALB creation.

</details>

---

## Additional Learning Resources

- [AWS Load Balancer Controller Documentation](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [ALB Annotation Reference](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/)
