# AWS Load Balancer Controller Quiz

Based on the self-managed LBC v3.5.0 guide.

## 1. What does AWS Load Balancer Controller manage?

- A. All cloud-provider responsibilities, including node lifecycle
- B. Supported AWS load-balancer resources reconciled from Kubernetes resources
- C. kube-proxy packet forwarding
- D. CoreDNS records for every pod

<details>
<summary>Show answer</summary>

B. LBC manages supported ALB/NLB, target-group, listener, and related resources. It does not replace kube-proxy, the CNI, DNS, or every cloud-controller responsibility. Legacy AWS provider behavior and EKS Auto Mode are separate implementations; do not claim LBC implements every feature of every ELB product.

</details>

## 2. How do ALB ip and instance targets differ?

- A. ip registers pod IPs; instance routes through node NodePorts
- B. ip always routes through NodePort
- C. They are identical
- D. instance is IPv6-only

<details>
<summary>Show answer</summary>

A. IP targets require supported, VPC-routable pod addresses and endpoint/ENI discovery. Amazon VPC CNI is the common EKS choice, but a compatible alternative CNI configuration is possible. Instance targets need a NodePort-capable Service and suitable node networking. Direct targeting does not prove a specific latency advantage for every workload.

</details>

## 3. Why does the controller need an IAM role through IRSA or EKS Pod Identity?

- A. To replace pod networking
- B. To authenticate and authorize its AWS API calls
- C. To replace Kubernetes RBAC
- D. To make every backend request authenticated

<details>
<summary>Show answer</summary>

B. The controller calls AWS APIs to create/manage load balancers, target groups, listeners and relevant security groups. IRSA and supported Pod Identity configurations are alternatives. A role only grants the policy attached to it; using a role does not automatically make that policy least privilege. Kubernetes RBAC and application authentication are separate.

</details>

## 4. How can multiple Ingresses share one ALB?

- A. Being in the same namespace is sufficient
- B. Use the same alb.ingress.kubernetes.io/group.name
- C. All Ingresses always share an ALB
- D. Set the same pod name

<details>
<summary>Show answer</summary>

B. IngressGroup shares the ALB and rule space. Smaller group.order values are evaluated first; ties use namespace/name ordering. Use this only within an enforced trust boundary because an untrusted user who can join the group can affect routing. Review annotation merge/exclusive behavior, limits, and cost rather than assuming savings in every deployment.

</details>

## 5. Which annotation supplies an NLB TLS certificate?

- A. service.beta.kubernetes.io/aws-load-balancer-ssl-cert
- B. alb.ingress.kubernetes.io/certificate-arn
- C. service.beta.kubernetes.io/aws-load-balancer-tls-termination
- D. nlb.kubernetes.io/ssl-certificate

<details>
<summary>Show answer</summary>

A. For the self-managed LBC, a complete Service example is:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-tls-service
  namespace: default
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
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

Replace the certificate ARN and provide matching backend pods listening on 8080. Client-facing TLS terminates at NLB; tcp here leaves the backend connection without TLS. Use the appropriate certificate/security policy and network controls. Auto Mode uses its own loadBalancerClass and supported annotation set.

</details>

## 6. What is the purpose of an independently created TargetGroupBinding?

- A. Create every load balancer/listener automatically
- B. Register a Kubernetes Service’s targets in an existing target group
- C. Define ALB HTTP listener routing rules
- D. Replace IAM authorization

<details>
<summary>Show answer</summary>

B. The load balancer, listener and target group already exist and must match the Service/target protocol, address family and ports.

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
  namespace: default
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/1234567890abcdef
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

For a target group shared by multiple clusters/TGBs, every participant needs multiClusterTargetGroup: true from creation. The default assumes full ownership and can deregister foreign targets. nodeSelector applies to instance targets, not IP-mode pod filtering. Restrict TGB permissions to trusted users.

</details>

## 7. Which annotation attaches a regional WAF v2 Web ACL to an ALB?

- A. alb.ingress.kubernetes.io/waf-acl-id
- B. alb.ingress.kubernetes.io/wafv2-acl-arn
- C. alb.ingress.kubernetes.io/web-acl
- D. alb.ingress.kubernetes.io/firewall-rules

<details>
<summary>Show answer</summary>

B. Supply the existing regional Web ACL ARN in the ALB’s region, configure its rules, and provide the controller’s required permissions. The WAF v2 integration must be enabled; its default is true, so an explicit enableWafv2 value is not universally required. A disabled integration does not apply the annotation. WAF and paid Shield Advanced protection are different features.

</details>

## 8. Which are the conventional subnet role tags?

- A. kubernetes.io/cluster/CLUSTER_NAME alone
- B. kubernetes.io/role/elb for public and kubernetes.io/role/internal-elb for private
- C. aws:cloudformation:stack-name
- D. Name=kubernetes-subnet only

<details>
<summary>Show answer</summary>

B. Values may be 1 or empty for self-managed LBC discovery. In v2.12.1+, the default reachability-based fallback can classify subnets from route tables when matching role tags are absent. Explicit subnets and IngressClassParams tag filters are other selection paths. Auto Mode still requires its documented tags. Check cluster tags, free IPs, and AZ requirements; tags do not modify routing.

</details>

## 9. How are ALB sticky sessions configured?

- A. alb.ingress.kubernetes.io/sticky-sessions=true
- B. target-group-attributes with stickiness.enabled=true
- C. session-affinity=cookie on the Ingress
- D. Always enabled by default

<details>
<summary>Show answer</summary>

B. Set alb.ingress.kubernetes.io/target-type: ip and combine stickiness.enabled=true with the appropriate cookie attributes in one target-group-attributes annotation. Do not repeat the YAML key for slow start or deregistration delay, since duplicate keys can discard settings. With a weighted forward action, configure its target-group stickiness consistently as documented.

</details>

## 10. Which statement about NLB client identity is correct?

- A. Proxy Protocol v2 changes the IP packet source to the client address
- B. externalTrafficPolicy: Local guarantees preservation for every target mode
- C. Proxy Protocol carries metadata; packet-source preservation is a separate setting with network/protocol constraints
- D. NLB always preserves client IP

<details>
<summary>Show answer</summary>

C. The backend must parse Proxy Protocol v2 before application data and support the applicable health checks. preserve_client_ip.enabled controls packet-source preservation where supported. In instance/NodePort mode, externalTrafficPolicy: Local can avoid a later kube-proxy SNAT hop; it does not solve every NLB path or IP-family translation case. For weighted NLB targets, ordinary reweighting affects new connections, but setting a weight to zero closes existing connections after a short period.

</details>

## 11. Which annotation configures ALB HTTP-to-HTTPS redirect?

- A. alb.ingress.kubernetes.io/force-ssl-redirect
- B. alb.ingress.kubernetes.io/ssl-redirect: "443"
- C. alb.ingress.kubernetes.io/http-to-https
- D. An HTTPRoute is always required

<details>
<summary>Show answer</summary>

B. Configure both the HTTP and destination HTTPS listeners and an appropriate certificate. Once enabled, HTTP listeners use the redirect default action and their other routing rules are ignored. It affects the IngressGroup, so review group-wide behavior. Cognito/OIDC/JWT authentication requires HTTPS; a redirect by itself is not application authorization.

</details>

## 12. What should you inspect first when an ALB is not created?

- A. Only kube-proxy logs
- B. The application’s cookie contents
- C. Controller logs/events, class selection, IAM, subnet eligibility and webhook/CRD health
- D. Only the number of pod replicas

<details>
<summary>Show answer</summary>

C. Check the reconciliation/control-plane path first. kube-proxy or an eBPF replacement can matter later for node/service traffic, but is not the first diagnostic for a failed AWS CreateLoadBalancer operation. A successful kubectl apply does not prove AWS reconciliation succeeded. Use real resource IDs, namespaces and bounded log output.

</details>

[Return to the guide](../../networking/03-aws-lb-controller.md)
