# EKS Networking Quiz - Part 2

> **Last Updated**: September 11, 2026

These answers use the controller ownership and prerequisites in [Part 2](../../eks/03-eks-networking-part2.md): LBC 3.5.0 and Gateway API 1.6.0. Commands are examples that change resources when run; local schema/mock tests do not constitute an EKS deployment. Replace account/Region/resource placeholders, use the intended kubeconfig and preserve the platform’s IAM/Helm/IaC ownership.

### 1. What type of AWS load balancer does AWS Load Balancer Controller provision by default for Kubernetes Ingress resources?

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>Show Answer</summary>

**Answer: C. Application Load Balancer (ALB)**

**Explanation:** AWS Load Balancer Controller provisions an Application Load Balancer (ALB) by default for Kubernetes Ingress resources. ALB is a Layer 7 load balancer that handles HTTP/HTTPS traffic and provides features such as path-based routing, host-based routing, and TLS termination to meet the requirements of Ingress resources.

LBC must select the Ingress class; another controller can implement an Ingress differently. The public scheme below requires intentionally configured public subnets, client SG access and ready backend Services.

**Key Features:**

1. **Path-Based Routing**: ALB can route traffic to different services based on URL paths, making it suitable for implementing path-based routing rules in Ingress.
2. **Host-Based Routing**: Multiple domains can be handled with a single ALB, supporting Ingress with multiple host rules.
3. **TLS Termination**: ALB can manage SSL/TLS certificates and terminate HTTPS traffic.
4. **WebSockets Support**: ALB supports the WebSockets protocol, suitable for real-time applications.
5. **Authentication Integration**: Can integrate with Amazon Cognito or OIDC to provide application-level authentication.

**Configuration Example:**

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

**Key Annotations:**

* `spec.ingressClassName: alb`: Selects an IngressClass whose controller is `ingress.k8s.aws/alb`
* `alb.ingress.kubernetes.io/scheme: internet-facing`: Creates internet-facing ALB
* `alb.ingress.kubernetes.io/target-type: ip`: Uses pod IPs as targets (instead of instance)
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: Configures listener ports
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: Specifies SSL certificate

Issues with other options:

* **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller does not use CLB for Ingress resources. CLB is considered a legacy load balancer.
* **B. Network Load Balancer (NLB)**: NLB is primarily used for Service type LoadBalancer and is not used by default for Ingress resources.
* **D. Gateway Load Balancer (GWLB)**: GWLB is for network virtual appliances and is not used with Kubernetes Ingress resources.

</details>

### 2. Which Ingress annotation selects an internal ALB?

- A. Service annotation `aws-load-balancer-internal`
- B. Ingress annotation `alb.ingress.kubernetes.io/scheme: internal`
- C. Any class named `internal-alb`
- D. `aws-load-balancer-type: internal`

<details>
<summary>Show Answer</summary>

**Answer: B. `alb.ingress.kubernetes.io/scheme: internal`**

An internal ALB has private addresses. Routed clients in connected VPCs or on-premises networks can also reach it when routing, DNS and security controls permit; it is not restricted to Pods or its own VPC by definition.
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
Subnet discovery or explicit subnet IDs select placement; SGs control access. `inbound-cidrs` configures a controller-created frontend SG but is ignored when custom SGs are supplied. A Route 53 private alias/CNAME must be created separately; ALB log attributes do not create DNS records. Custom IngressClass names such as `internal-alb` are possible when an actual matching IngressClass/controller configuration exists, but the name alone does not select the scheme.

</details>

### 3. Which Ingress annotation selects Pod IP targets?

- A. `target-type: pod`
- B. `alb.ingress.kubernetes.io/target-type: ip`
- C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`
- D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>
<summary>Show Answer</summary>

**Answer: B. `alb.ingress.kubernetes.io/target-type: ip`**

`ip` registers routable Pod IPs and resolved Service target ports. `instance` normally registers nodes and NodePorts (subject to controller/IngressClass defaults). IP targets are required for EKS Fargate. Selecting IP targets does not itself create Pod security groups, eliminate node failures or guarantee higher performance.
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
| Property | IP targets | Instance targets |
|---|---|---|
| Path | LB → Pod target | LB → NodePort → selected endpoint |
| Node failure | Pods on failed node are lost; health checks/reconciliation converge | Failed node target is removed; other healthy nodes can remain |
| Service type | ClusterIP is sufficient | NodePort or LoadBalancer with allocated NodePorts |
| Fargate | Supported path | No EC2 NodePort target |

Use VPC-routable Pod networking and allow both application and health-check traffic. Native VPC CNI is the ordinary EC2 path; supported hybrid/network designs need their own reachability validation. `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip` is the NLB Service counterpart; the option omitting `nlb` is not the correct annotation.

</details>

### 4. Does the NLB-IP annotation create a PrivateLink endpoint service?

- A. Any `LoadBalancer` Service creates PrivateLink
- B. `nlb-ip` automatically creates and authorizes it
- C. Separate NLB, endpoint service and consumer configuration
- D. Only instance targets can use PrivateLink

<details>
<summary>Show Answer</summary>

**Answer: C. No; create the NLB, endpoint-service configuration and consumer access separately.**

The original `nlb-ip` answer confused target selection with PrivateLink provisioning. An endpoint service uses an NLB (or GWLB for appliances); it does not require IP targets or an internal NLB. This example deliberately chooses an internal IP-target NLB for private Pod access.
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
Create this Service in the intended namespace with ready matching Pods and wait for the NLB. Identify it by exact DNSName, not by splitting its hostname on hyphens:
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
The following provider-side commands create billable resources and grant endpoint-service access to one consumer account. Run under the reviewed infrastructure owner, record returned IDs, and avoid rerunning creation as if it were idempotent. This example is for the commercial AWS partition; adapt ARNs for another partition.
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
In the consumer account, choose supported AZs (compare AZ IDs across accounts), endpoint SGs that permit the intended clients, and the exact returned service name. This same-Region example does not configure cross-Region PrivateLink.
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
The provider must accept the specific pending endpoint request because acceptance is required. Optional private DNS requires domain ownership verification before consumers enable it. Validate healthy targets, endpoint state and application authentication. PrivateLink source IPs at the target are NLB addresses; Proxy Protocol v2 can carry consumer metadata if the backend understands it. It does not automatically satisfy compliance or authorize application requests. Retire consumer endpoints, endpoint-service associations and Kubernetes load-balancer resources through their respective owners.

</details>

### 5. Which additional policy engine can work with Amazon VPC CNI?

- A. AWS Network Firewall
- B. Calico
- C. Security Groups for Pods
- D. VPC Flow Logs

<details>
<summary>Show Answer</summary>

**Answer: B. Calico**

Calico can enforce policy while VPC CNI retains IPAM/networking. It is an alternative to the native VPC CNI policy engine, not a mandatory add-on. Follow the [official policy-only EKS procedure](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks), including supported versions, `cni.type: AmazonVPC`, `ANNOTATE_POD_IP` and the required Pod patch permission. Do not enable both engines simultaneously or apply a VXLAN replacement manifest to the running cluster.

Calico APIs also provide ordered/tiered rules, GlobalNetworkPolicy, NetworkSet, service-account selectors and host-endpoint policy. Their semantics differ from additive Kubernetes NetworkPolicy; a NetworkSet does not restrict traffic until a Calico policy references it. A global allow-all policy is not a least-privilege baseline. Do not assume every VPC CNI mode is compatible: the current Calico EKS guide specifically excludes enforcement for IPv6 Pods with `ENABLE_V4_EGRESS=true`.

For a namespace-owned Kubernetes policy example, create `policy-lab` and a controller-managed Pod labelled `role=frontend`. This egress policy allows ordinary CoreDNS and approved HTTPS destinations only, subject to all other additive policies. Replace the documentation CIDR with the real destination; adapt DNS for NodeLocal DNS.
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
Verify baseline connectivity and allowed/denied TCP paths before relying on enforcement. NetworkPolicy has no portable audit-only mode. Use the selected engine’s documented logging/staging features where available. SGs for Pods and VPC firewalls are separate controls; Flow Logs observe traffic rather than enforcing this API.

</details>

### 6. How do custom ALB frontend security groups and backend rules differ?

<details>
<summary>Show Answer</summary>

**Answer: `alb.ingress.kubernetes.io/security-groups`**

Merge this annotation fragment into the intended Ingress. SG IDs are unambiguous; a name lookup matches the AWS `Name` tag, not the EC2 `groupName` attribute.
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    alb.ingress.kubernetes.io/tags: Environment=training,Team=platform
```
Configure custom frontend inbound/outbound rules yourself. `inbound-cidrs` and prefix-list annotations are ignored for supplied frontend SGs. `manage-backend-security-group-rules: "true"` authorizes the controller to manage target access through its backend SG mechanism; it does not create rules restricting client access in the custom frontend SG. Without it, arrange node/Pod SG access yourself. Permit application and health-check ports, and review SG-selection tags when target ENIs have multiple SGs.

The release IAM policy includes the EC2/ELB permissions needed for the whole controller; a short list of SG actions is not a complete role policy. Reusing SGs across trust domains broadens exposure and increases change coupling. Review actual rules and VPC Flow Log rejections. `tags` adds supported resource tags; `load_balancing.cross_zone.enabled` is a balancing attribute, not a tag. Select a supported TLS security policy based on client compatibility and requirements rather than copying a legacy policy name as current guidance.

</details>

### 7. How is NLB client IP preservation configured, and what are its limits?

<details>
<summary>Show Answer</summary>

**Answer: `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`**

For TCP/TLS target groups the attribute is configurable: instance targets default to enabled, IP targets default to disabled. UDP/TCP_UDP/QUIC/TCP_QUIC target groups always preserve client IP and cannot disable it. This IPv4 IP-target TCP example changes the configurable case:
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
The address seen by the application still depends on the full path. NodePort forwarding can SNAT unless local traffic policy/topology preserves it; ALB uses HTTP forwarded headers; IPv6-to-IPv4 translation and PrivateLink do not preserve the original packet source. Preservation requires supported direct same-VPC or same-Region peering paths and does not work through a transit gateway. Internal-NLB hairpin connections back to the same registered target can fail.

Proxy Protocol v2 can convey original address metadata but requires a compatible listener/parser; do not enable it blindly. Framework `remote_addr` or TCP `RemoteAddr()` reports the immediate peer, not automatically the original internet client. Only trust forwarded headers from explicitly trusted proxies. Changing preservation affects new TCP connections. `deregistration_delay.timeout_seconds` controls draining, not TCP keep-alive. Measure performance rather than assigning an unsupported overhead value.

</details>

### 8. How is AWS WAF attached to an LBC-managed ALB?

<details>
<summary>Show Answer</summary>

**Answer: `alb.ingress.kubernetes.io/wafv2-acl-arn` with a same-Region REGIONAL Web ACL.**

Use a real `regional/webacl/...` ARN. A CloudFront `global/webacl/...` ARN cannot be attached to the regional ALB. Association protects traffic through that ALB; it does not attach WAF to Pods, NLBs or the Kubernetes API server.
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
An empty Web ACL with default Allow blocks nothing. For an isolated rule-development example, save the following array as `waf-rules.json`. This rule **counts**, rather than blocks, `/admin` prefixes; it is not an authentication control or a complete managed-rule baseline.
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
A security owner may create that training ACL with the following command; use its returned ARN when associating it. The binary-format flag makes the JSON SearchString literal bytes in AWS CLI v2.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the ALB Region}"
aws wafv2 create-web-acl --region "$AWS_REGION" \
  --name eks-ingress-training --scope REGIONAL \
  --default-action '{"Allow":{}}' --rules file://waf-rules.json \
  --cli-binary-format raw-in-base64-out \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-training
```
Managed SQLi/XSS, bot, reputation, rate-based and custom rules provide their respective protections only after configuration and tuning; charges/features vary. Review false positives in Count mode before enabling enforcement. Default Allow remains permissive while a rule counts.

ALB `access_logs.s3.*` attributes configure ALB access logs in S3, not WAF logs or CloudWatch Logs. Configure WAF logging separately with an approved CloudWatch Logs/S3/Firehose destination and required permissions; sampled requests and CloudWatch metrics are separate from full request logs. Use the reviewed release controller IAM policy for association and a separate security-administration role for ACL creation/rules/logging. Scope resource permissions where supported; do not paste an unconstrained standalone wildcard policy as a complete controller role.

</details>

### 9. Build and verify path routing for three distinguishable backends.

<details>
<summary>Show Answer</summary>

**Answer: Ingress + ClusterIP Services + ready HTTP workloads.**

Prerequisites: LBC with reviewed IAM/subnets, a routable private test client, an ACM certificate for a hostname you control, and permission to create a dedicated namespace. The example creates an internal ALB; `/admin` is only a routing label and has no authentication. It is a bounded training exercise, not production readiness evidence. Run the blocks in one shell with `set -euo pipefail`; preserve LAB_NS/LAB_UID until cleanup.
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
The HTTP server really listens on 8080 and answers `/health` plus all requested paths with its backend name. Declaring `containerPort: 8080` alone would not reconfigure a default nginx server. The mutable Python tag is an illustrative runtime; pin an approved image digest for repeatable use.
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
Wait for an ALB hostname, healthy targets and controller reconciliation. On failure inspect Ingress events, controller logs, EndpointSlices and SG/health-check paths. From the permitted private client, this test preserves the Host header and TLS SNI while connecting directly to the ALB hostname; it does not require a DNS record or disable certificate verification.
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
For persistent DNS, create an appropriate Route 53 alias; a CNAME is permitted at a subdomain, not the zone apex. Do not use a public CA placeholder ARN or `curl -k` to hide a certificate mismatch.

Optional weighted routing is a separate example with existing `service-v1`/`service-v2` backends. The action must be referenced by the `use-annotation` backend; adding the action annotation alone has no effect. Run in the intended namespace and avoid conflicting routes.
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
Clean up only this exercise’s namespace after checking its saved UID. Let LBC remove the Ingress load balancer before namespace deletion. If finalization fails, diagnose controller/IAM/deletion-protection state; do not force-remove finalizers. Shared certificates, controller roles and DNS records are not deleted by this block.
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

### 10. How does a service mesh change EKS networking, and what must be validated?

<details>
<summary>Show Answer</summary>

**Answer: It adds traffic/security/telemetry processing on top of a compatible Pod network.**

A control plane distributes configuration and workload identity; data-plane proxies process enrolled traffic. In a sidecar design, application and proxy share the **same Pod network namespace/IP**. A sidecar does not inherently consume another VPC IP or ENI. Extra mesh gateway/control-plane Pods do consume resources/IPs. Ambient designs instead use node proxies and optional waypoints, so “every Pod gets a sidecar” is not universal.
```text
Client application → client proxy → Pod network → destination proxy → destination application
```
This is a logical sidecar path, not a promise that every packet traverses a Service virtual IP or is intercepted. Excluded ports, UDP, host-network traffic, namespace enrollment and mode matter. VPC routes, SGs and NetworkPolicy still apply. L3/L4 policy must allow required data-plane, DNS, control-plane and health paths; mTLS authenticates/encrypts mesh peers and does not replace application authorization.

For Istio, choose one documented sidecar/ambient installation for the compute type. Fargate cannot run the node DaemonSets/privileged components required by some modes; verify support instead of claiming universal compatibility. Do not enable two mesh injectors on one namespace. Configure proxy resources through supported Helm/install/workload settings, not by overwriting an injector ConfigMap with unrelated `pilot.resources`. Keep Prometheus/tracing deployment and mesh export configuration separate; the removed `IstioOperator.addonComponents.prometheus` and invented App Mesh `Mesh.spec.tracing` are not usable installation recipes.

**Historical comparison:** AWS will discontinue App Mesh support on **September 30, 2026**, after which console/resources are unavailable. As of this audit date, an existing App Mesh deployment needs a migration plan; do not introduce it as a new EKS default. Its historical Fargate integration is not a future support guarantee. ECS Service Connect is an ECS option, not a direct EKS replacement. Use a supported EKS mesh/data-plane design and verify feature parity for routing, retries, certificates, authorization, tracing and failure handling.

The original “typically <10 ms” latency and “10–15%” CPU/memory overhead figures have no verified measurement source in this document. They are retained here as **unverified historical estimates**, not benchmarks or sizing guarantees. Measure p50/p95/p99 latency, throughput, errors and CPU/memory with the same request mix, TLS, telemetry sampling and load before/after enrollment. Include proxy rollout, node loss, control-plane loss, certificate rotation and retry amplification tests.

Adopt gradually in a dedicated namespace, validate one injector, ready workloads, mTLS and positive/negative policy tests, then expand. For LBC in front of a mesh ingress gateway, expose the gateway Service and verify target ports/probes; the Ingress API object is configuration, not another proxy hop. Use scoped controller IAM where required; `cloudmap:*` is not a valid substitute for the `servicediscovery` IAM service prefix. Prefix delegation is an IP-capacity design choice, not a sidecar prerequisite. See the maintained [Istio installation](../../service-mesh/istio/01-installation.md) and [AWS integration](../../service-mesh/istio/04-aws-integration.md) chapters for implementation.

</details>

### 11. What routing resource is used for L7 load balancing (ALB) in Kubernetes Gateway API?

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>Show Answer</summary>

**Answer: B. HTTPRoute**

**Explanation:** In Kubernetes Gateway API, the HTTPRoute resource is used for L7 load balancing. HTTPRoute defines rules for routing HTTP/HTTPS traffic to services, and when used with AWS Load Balancer Controller, it distributes traffic through an ALB.

**Gateway API Resource Hierarchy:**

1. **GatewayClass**: Defines load balancer type (e.g., `amazon-alb`, `amazon-nlb`)
2. **Gateway**: Actual load balancer instance (listener ports, TLS settings, etc.)
3. **HTTPRoute**: L7 routing rules (host, path, header-based routing)
4. **TCPRoute**: L4 routing rules (TCP traffic)

LBC uses separate ALB and NLB Gateways; controllerName selects the implementation, not the arbitrary GatewayClass object name. Confirm supported filters in the release conformance table.

**Key HTTPRoute Features:**

* Path and host-based routing
* Native weight-based traffic splitting
* Header and query parameter matching
* Routing to multiple backend services

Issues with other options:

* **A. IngressRoute**: This is not a standard Gateway API resource.
* **C. VirtualService**: This is a resource from the Istio service mesh.
* **D. ServiceRoute**: This resource does not exist.

</details>

### 12. How are LBC 3.5.0 Gateway controllers enabled?

- A. Always pass `--enable-gateway-api`
- B. Detect compatible CRDs with the real default-enabled gates
- C. Use `--feature-gates=EnableGatewayAPI=true`
- D. Install only experimental CRDs from 1.2.1

<details>
<summary>Show Answer</summary>

**Answer: B. Detect the required CRDs; ALBGatewayAPI/NLBGatewayAPI default to enabled.**

Install the release-compatible Gateway API 1.6.0 standard CRDs and LBC-specific Gateway CRDs. The default gates are `ALBGatewayAPI` and `NLBGatewayAPI`; `EnableGatewayAPI` is an unknown feature name. TCPRoute/UDPRoute are now served as v1 in the standard channel. Earlier controller releases have different compatibility/gating requirements: L4 support starts at 2.13.3 and L7 at 2.14.0. Check controller startup/logs after CRD installation; CRDs alone do not provide IAM, subnets or application backends.

</details>

### 13. What resource is used to route L4-level TCP traffic through an NLB in Gateway API?

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>Show Answer</summary>

**Answer: C. TCPRoute**

**Explanation:** In Gateway API, the TCPRoute resource is used to route L4-level TCP traffic. When used with AWS Load Balancer Controller, TCPRoute forwards TCP traffic to backend services through an NLB (Network Load Balancer).

**TCPRoute Configuration Example:**

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

**Gateway API Routing Resource Usage:**

| Resource  | Protocol   | AWS LB Type |
| --------- | ---------- | ----------- |
| HTTPRoute | HTTP/HTTPS | ALB         |
| TCPRoute  | TCP        | NLB         |
| TLSRoute  | TLS        | NLB         |
| GRPCRoute | gRPC       | ALB         |

Issues with other options:

* **A. HTTPRoute**: Used for HTTP/HTTPS L7 traffic with ALB.
* **B. TLSRoute**: For TLS traffic routing, but TCPRoute is appropriate for TCP-level routing.
* **D. GRPCRoute**: A routing resource specifically for gRPC protocol.

</details>
The `my-nlb-gateway` listener and backend Service must exist in `gateway-demo`. TLSRoute with this implementation does not provide SNI-based NLB routing; use the release-specific TLS behavior rather than assuming all Gateway API implementations behave alike.

### 14. How does LBC 3.5.0 configure a static certificate for an ALB Gateway?

- A. Create any Secret named tls-cert
- B. Use the ACM ARN in LoadBalancerConfiguration
- C. Add only a Route hostname
- D. Set backend Service port 443

<details>
<summary>Show Answer</summary>

**Answer: B. `LoadBalancerConfiguration.spec.listenerConfigurations[].defaultCertificate`**

Use a valid same-Region ACM certificate ARN for the HTTPS listener. Kubernetes Secret `certificateRefs` is not supported by this implementation. Hostname discovery also needs an existing matching ACM certificate and a secure listener. An HTTPRoute with backend port 443 alone does not configure client-side HTTPS.

</details>

### 15. Does a frontend-only ingress policy narrow an existing same-namespace allow-all policy?

- A. Yes, the newest policy wins
- B. Yes, the most specific selector wins
- C. No, matching allows form a union
- D. Only if the policy name sorts first

<details>
<summary>Show Answer</summary>

**Answer: C. No; matching NetworkPolicy allows are additive.**

Both policies select the backend, so the broader same-namespace allow still permits other same-namespace callers. Remove or narrow the broader policy through its owner, then test allowed and denied connections. Ingress and egress isolation are independent; DNS egress and the destination ingress can each affect a test result.

</details>

Official references: [LBC Gateway API](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/gateway/), [PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html), [NLB client IP](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html), [WAF associations](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html), [App Mesh retirement](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).
