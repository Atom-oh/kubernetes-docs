# Amazon EKS Networking Quiz (Part 2)

This quiz tests your understanding of advanced networking concepts in Amazon EKS, AWS Load Balancer Controller, Ingress resources, service mesh, and network security.

## Multiple Choice Questions

### 1. What type of AWS load balancer does AWS Load Balancer Controller provision by default for Kubernetes Ingress resources?

A. Classic Load Balancer (CLB)
B. Network Load Balancer (NLB)
C. Application Load Balancer (ALB)
D. Gateway Load Balancer (GWLB)

<details>
<summary>Show Answer</summary>

**Answer: C. Application Load Balancer (ALB)**

**Explanation:**
AWS Load Balancer Controller provisions an Application Load Balancer (ALB) by default for Kubernetes Ingress resources. ALB is a Layer 7 load balancer that handles HTTP/HTTPS traffic and provides features such as path-based routing, host-based routing, and TLS termination to meet the requirements of Ingress resources.

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

**Key Annotations:**

- `kubernetes.io/ingress.class: alb`: Specifies use of ALB Ingress Controller
- `alb.ingress.kubernetes.io/scheme: internet-facing`: Creates internet-facing ALB
- `alb.ingress.kubernetes.io/target-type: ip`: Uses pod IPs as targets (instead of instance)
- `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: Configures listener ports
- `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: Specifies SSL certificate

Issues with other options:
- **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller does not use CLB for Ingress resources. CLB is considered a legacy load balancer.
- **B. Network Load Balancer (NLB)**: NLB is primarily used for Service type LoadBalancer and is not used by default for Ingress resources.
- **D. Gateway Load Balancer (GWLB)**: GWLB is for network virtual appliances and is not used with Kubernetes Ingress resources.
</details>

### 2. What annotation should be added to an Ingress resource in Amazon EKS to create an internal Application Load Balancer using AWS Load Balancer Controller?

A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`
B. `alb.ingress.kubernetes.io/scheme: internal`
C. `kubernetes.io/ingress.class: internal-alb`
D. `aws-load-balancer-type: internal`

<details>
<summary>Show Answer</summary>

**Answer: B. `alb.ingress.kubernetes.io/scheme: internal`**

**Explanation:**
To create an internal Application Load Balancer using AWS Load Balancer Controller in Amazon EKS, the `alb.ingress.kubernetes.io/scheme: internal` annotation must be added to the Ingress resource. This annotation configures the ALB to be accessible only within the VPC.

**Internal ALB Configuration Example:**
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

**Key Considerations:**

1. **Subnet Selection**: Internal ALBs are created in private subnets. Subnets can be explicitly specified:
   ```yaml
   alb.ingress.kubernetes.io/subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
   ```

2. **Security Groups**: Specific security groups can be applied to internal ALBs:
   ```yaml
   alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
   ```

3. **Inbound CIDR Restriction**: Access can be allowed only from specific CIDR blocks:
   ```yaml
   alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
   ```

4. **Internal DNS**: Internal ALB can be integrated with Route 53 private hosted zones within the VPC:
   ```yaml
   alb.ingress.kubernetes.io/load-balancer-attributes: routing.http.drop_invalid_header_fields.enabled=true,access_logs.s3.enabled=true
   ```

**Use Cases for Internal ALB:**

- Internal communication between microservices
- Backend API services
- Administrative interfaces
- Development and test environments
- Workloads with regulatory requirements

**Verify AWS Load Balancer Controller Installation:**
```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
```

Issues with other options:
- **A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`**: This annotation is used for Service type LoadBalancer and does not apply to Ingress resources.
- **C. `kubernetes.io/ingress.class: internal-alb`**: The correct ingress.class is 'alb'; 'internal-alb' is not a valid value.
- **D. `aws-load-balancer-type: internal`**: This annotation does not exist.
</details>

### 3. What annotation is used to configure AWS Load Balancer Controller to use pod IPs directly as targets in Amazon EKS?

A. `alb.ingress.kubernetes.io/target-type: pod`
B. `alb.ingress.kubernetes.io/target-type: ip`
C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`
D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>
<summary>Show Answer</summary>

**Answer: B. `alb.ingress.kubernetes.io/target-type: ip`**

**Explanation:**
To configure AWS Load Balancer Controller to use pod IPs directly as targets in Amazon EKS, the `alb.ingress.kubernetes.io/target-type: ip` annotation must be used. This setting allows the load balancer to route traffic directly to pod IPs instead of node IPs.

**Target Type Options:**

1. **instance**: (default) Routes traffic using node IP and NodePort.
2. **ip**: Routes traffic directly to pods using pod IP and container port.

**IP Mode Configuration Example:**
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

**Advantages of IP Mode:**

1. **Node Failure Resilience**: Even if a node fails, traffic continues to be routed to pods on other nodes.
2. **Direct Routing**: Traffic is delivered directly to pods without additional hops through NodePort.
3. **Fargate Compatibility**: Required for pods running on AWS Fargate.
4. **Security Group Integration**: Security groups can be applied at the pod level.

**IP Mode Requirements:**

1. **VPC CNI**: Amazon VPC CNI plugin is required.
2. **Subnet Configuration**: Subnets where pods run must be routable to load balancer subnets.
3. **Security Group Rules**: Load balancer's security group must allow traffic to pod IPs.

**IP Mode vs Instance Mode Comparison:**

| Characteristic | IP Mode | Instance Mode |
|----------------|---------|--------------|
| Target | Pod IP | Node IP |
| Port | Container port | NodePort |
| Traffic Path | LB -> Pod | LB -> Node -> Pod |
| On Node Failure | No impact | Pods on that node inaccessible |
| Performance | Better performance | Slight overhead from additional hop |
| Fargate Support | Supported | Not supported |

**Additional Configuration Options:**

```yaml
# Target group attributes setting
alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30,stickiness.enabled=true

# Health check settings
alb.ingress.kubernetes.io/healthcheck-path: /health
alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
alb.ingress.kubernetes.io/success-codes: '200'
alb.ingress.kubernetes.io/healthy-threshold-count: '2'
alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
```

Issues with other options:
- **A. `alb.ingress.kubernetes.io/target-type: pod`**: The correct value is 'ip', not 'pod'.
- **C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`**: This annotation is used for Service type LoadBalancer and does not apply to Ingress resources.
- **D. `aws-load-balancer-target-node-labels: ip-mode=true`**: This annotation does not exist.
</details>

### 4. What annotation is used to integrate Kubernetes Service with AWS PrivateLink to create a VPC endpoint service in Amazon EKS?

A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb`
B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"`
C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`
D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`

<details>
<summary>Show Answer</summary>

**Answer: C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`**

**Explanation:**
To integrate Kubernetes Service with AWS PrivateLink to create a VPC endpoint service in Amazon EKS, the `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip` annotation must be used. This annotation creates a Network Load Balancer (NLB) in IP mode, which is a prerequisite for integrating with AWS PrivateLink.

**VPC Endpoint Service Configuration Steps:**

1. **Create Kubernetes Service with NLB-IP Mode:**
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

2. **Create VPC Endpoint Service Using AWS CLI:**
```bash
# Get NLB ARN
NLB_ARN=$(aws elbv2 describe-load-balancers --names $(kubectl get svc privatelink-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' | cut -d- -f1) --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Create VPC endpoint service
aws ec2 create-vpc-endpoint-service-configuration \
  --network-load-balancer-arns $NLB_ARN \
  --acceptance-required \
  --private-dns-name service.example.com
```

3. **Configure VPC Endpoint Service Allow List:**
```bash
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-id vpce-svc-0123456789abcdef0 \
  --add-allowed-principals arn:aws:iam::111122223333:root
```

**Key Considerations:**

1. **Internal NLB Requirement**: PrivateLink requires an internal NLB, so the `service.beta.kubernetes.io/aws-load-balancer-internal: "true"` annotation is also needed.

2. **Importance of IP Mode**: NLB-IP mode provides resilience to node failures by using pod IPs directly as targets.

3. **Service Name Resolution**: Private DNS names can be configured to simplify service name resolution within the VPC.

4. **Access Control**: The `acceptance-required` flag can be used to manually approve endpoint connection requests.

5. **Network ACLs and Security Groups**: Ensure appropriate network ACL and security group rules are configured.

**Benefits of PrivateLink Integration:**

- **Enhanced Security**: Traffic stays within the AWS network without traversing the public internet.
- **Compliance**: Meets data sovereignty and compliance requirements.
- **Simplified Networking**: Services can be accessed without VPC peering, Transit Gateway, or VPN connections.
- **Scalability**: Services can be accessed from thousands of VPCs.

**Client-Side Configuration:**
```bash
# Create VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-0123456789abcdef0 \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-group-ids sg-0123456789abcdef0
```

Issues with other options:
- **A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb`**: This annotation creates an instance mode NLB and is not optimized for PrivateLink integration.
- **B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"`**: This annotation does not exist.
- **D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`**: This annotation does not exist.
</details>

### 5. What additional component can be used with Amazon VPC CNI to implement Kubernetes NetworkPolicy resources in Amazon EKS?

A. AWS Network Firewall
B. Calico
C. AWS Security Groups for Pods
D. VPC Flow Logs

<details>
<summary>Show Answer</summary>

**Answer: B. Calico**

**Explanation:**
Calico is the additional component that can be used with Amazon VPC CNI to implement Kubernetes NetworkPolicy resources in Amazon EKS. Calico is an open-source networking and network security solution that supports the Kubernetes NetworkPolicy API and works together with Amazon VPC CNI to apply fine-grained network policies in EKS clusters.

**Calico Installation and Configuration:**

1. **Install Calico:**
```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

2. **Verify Installation:**
```bash
kubectl get pods -n calico-system
```

3. **Basic NetworkPolicy Example:**
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

**Key Features of Calico:**

1. **Kubernetes NetworkPolicy Support**: Fully implements the standard Kubernetes NetworkPolicy API.

2. **Extended Policy Features**: Provides advanced network policies beyond Kubernetes NetworkPolicy through custom resources like Calico's GlobalNetworkPolicy and NetworkSet.

3. **Fine-Grained Control**: Can filter traffic based on protocols, ports, CIDR blocks, service accounts, etc.

4. **Logging and Monitoring**: Can log and monitor network policy violations.

5. **Host Endpoint Protection**: Can apply network policies to Kubernetes nodes themselves.

**Calico Advanced Policy Example:**
```yaml
# GlobalNetworkPolicy example (cluster-wide policy)
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

# Restrict access to specific IP ranges
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

**Integration of Amazon VPC CNI and Calico:**

1. **Network Mode**: When used with Amazon VPC CNI, Calico operates in policy-only mode rather than overlay mode.

2. **Performance**: Maintains Amazon VPC CNI's native VPC networking performance while leveraging Calico's network policy features.

3. **Compatibility**: Calico is compatible with all Amazon VPC CNI features (prefix delegation, custom networking, etc.).

4. **Upgrades**: Calico and Amazon VPC CNI can be upgraded independently.

**Best Practices:**

- Start with a default deny policy and explicitly allow only necessary communications.
- Define clear policies for inter-namespace communication.
- Test policies in logging mode before applying them.
- Always allow communication to cluster essential components.
- Review and update policies regularly.

Issues with other options:
- **A. AWS Network Firewall**: AWS Network Firewall is a VPC-level firewall service and does not have direct integration with Kubernetes NetworkPolicy.
- **C. AWS Security Groups for Pods**: Security Groups for Pods is a feature that applies AWS security groups to pods but does not implement the Kubernetes NetworkPolicy API.
- **D. VPC Flow Logs**: VPC Flow Logs is a tool for monitoring network traffic and does not apply network policies.
</details>

## Short Answer Questions

### 6. What annotation is used to assign specific security groups to an Application Load Balancer when creating it using AWS Load Balancer Controller in Amazon EKS?

<details>
<summary>Show Answer</summary>

**Answer:**
`alb.ingress.kubernetes.io/security-groups: sg-xxxx,sg-yyyy`

**Detailed Explanation:**

When creating an Application Load Balancer (ALB) using AWS Load Balancer Controller, the `alb.ingress.kubernetes.io/security-groups` annotation can be used to assign specific security groups. This annotation specifies security group IDs to attach to the ALB, separated by commas.

**Implementation Method:**

1. **Specify Security Group IDs:**
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

2. **Specify Security Group Names (alternative method):**
   ```yaml
   alb.ingress.kubernetes.io/security-groups: my-security-group-name
   ```

3. **Auto-Create Security Groups:**
   ```yaml
   alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
   ```

**Key Considerations:**

1. **Security Group Rules:**
   - Inbound rules: Must allow client traffic (typically HTTP/80, HTTPS/443).
   - Outbound rules: Must allow traffic to target groups (pods or nodes).

2. **Default Behavior:**
   When the annotation is not specified, AWS Load Balancer Controller automatically creates a security group and configures necessary rules.

3. **Permission Requirements:**
   AWS Load Balancer Controller's IAM role needs the following permissions:
   - ec2:CreateSecurityGroup
   - ec2:DeleteSecurityGroup
   - ec2:DescribeSecurityGroups
   - ec2:AuthorizeSecurityGroupIngress
   - ec2:RevokeSecurityGroupIngress

4. **Security Group Management:**
   ```yaml
   # Set controller to manage security group rules
   alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
   ```

5. **Tagging:**
   Tags can be added to created security groups:
   ```yaml
   alb.ingress.kubernetes.io/tags: Environment=prod,Team=devops
   ```

**Best Practices:**

1. **Principle of Least Privilege:**
   Use restrictive security group rules that allow only necessary traffic.

2. **Security Group Reuse:**
   Reuse the same security groups across multiple Ingress resources to simplify management.

3. **Documentation:**
   Document used security groups and their rules for tracking.

4. **Regular Review:**
   Regularly review security group rules to remove unnecessary access.

5. **Monitoring:**
   Monitor denied connections to evaluate the effectiveness of security group rules.

**Related Annotations:**

- **Inbound CIDR Restriction:**
  ```yaml
  alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
  ```

- **Security Group Tags:**
  ```yaml
  alb.ingress.kubernetes.io/load-balancer-attributes: load_balancing.cross_zone.enabled=true
  ```

- **SSL Policy:**
  ```yaml
  alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
  ```

Using AWS Load Balancer Controller allows fine-grained control of ALB security groups through Kubernetes Ingress resources, which helps strengthen your cluster's network security posture.
</details>

### 7. What annotation is used to preserve client IP addresses when exposing a Kubernetes Service resource as a Network Load Balancer in Amazon EKS?

<details>
<summary>Show Answer</summary>

**Answer:**
`service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`

**Detailed Explanation:**

When exposing a Kubernetes Service resource as a Network Load Balancer (NLB) in Amazon EKS, the `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true` annotation must be used to preserve client IP addresses. This setting makes the NLB maintain the original client IP addresses.

**Implementation Method:**

1. **Basic NLB Service Configuration:**
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

2. **Use with IP Mode NLB:**
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

**Importance of Client IP Preservation:**

1. **Security and Access Control:**
   - Implement client IP-based access control
   - Block suspicious IP addresses
   - Apply IP-based rate limiting

2. **Logging and Auditing:**
   - Track request sources
   - Investigate security events
   - Meet compliance requirements

3. **Geolocation-Based Features:**
   - Serve region-specific content
   - Perform geographic analysis

**How It Works:**

1. **Instance Mode (aws-load-balancer-type: nlb):**
   - For TCP traffic, client IP is automatically preserved.
   - For UDP traffic, preserve_client_ip.enabled=true setting is required.

2. **IP Mode (aws-load-balancer-type: nlb-ip):**
   - Both TCP and UDP traffic require preserve_client_ip.enabled=true setting.

**Limitations and Considerations:**

1. **Proxy Protocol:**
   Client IP preservation is done through direct packet routing without using proxy protocol.

2. **Target Group Types:**
   - Instance mode: Uses node IP and NodePort.
   - IP mode: Uses pod IP and port directly.

3. **Performance Impact:**
   Client IP preservation may incur slight performance overhead.

4. **Compatibility:**
   Some legacy applications may not be compatible with client IP preservation.

**Accessing Client IP in Applications:**

1. **HTTP Applications:**
   ```python
   # Python Flask example
   from flask import Flask, request

   app = Flask(__name__)

   @app.route('/')
   def index():
       client_ip = request.remote_addr
       return f"Your IP address is: {client_ip}"
   ```

2. **TCP/UDP Applications:**
   ```go
   // Go example
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

**Related Annotations:**

- **Internal NLB Configuration:**
  ```yaml
  service.beta.kubernetes.io/aws-load-balancer-internal: "true"
  ```

- **Cross-Zone Load Balancing:**
  ```yaml
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: load_balancing.cross_zone.enabled=true
  ```

- **TCP Connection Keep-Alive:**
  ```yaml
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true,deregistration_delay.timeout_seconds=30
  ```

Client IP preservation is important for various purposes including security, logging, and access control, and can be easily configured in EKS clusters using the appropriate annotation.
</details>

### 8. What annotation is used to attach AWS WAF (Web Application Firewall) to a Kubernetes Ingress resource in Amazon EKS?

<details>
<summary>Show Answer</summary>

**Answer:**
`alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:region:account-id:global/webacl/name/id`

**Detailed Explanation:**

To attach AWS WAF (Web Application Firewall) to a Kubernetes Ingress resource in Amazon EKS, the `alb.ingress.kubernetes.io/wafv2-acl-arn` annotation must be used. This annotation attaches an AWS WAF WebACL to the Application Load Balancer (ALB) created by AWS Load Balancer Controller.

**Implementation Method:**

1. **Create AWS WAF WebACL:**
   First, create a WAF WebACL using AWS Management Console, AWS CLI, or AWS CloudFormation.
   ```bash
   # AWS CLI example
   aws wafv2 create-web-acl \
     --name "eks-ingress-protection" \
     --scope "REGIONAL" \
     --default-action Allow={} \
     --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-protection \
     --region us-west-2
   ```

2. **Specify WAF WebACL ARN in Ingress Resource:**
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

**Key Protection Features of AWS WAF:**

1. **Common Web Vulnerability Defense:**
   - SQL injection attacks
   - Cross-site scripting (XSS)
   - Path traversal attacks
   - Command injection

2. **Bot Traffic Control:**
   - Block malicious bots
   - Prevent scraping
   - Prevent credential stuffing attacks

3. **Rate Limiting:**
   - DDoS attack mitigation
   - Prevent brute force attacks

4. **Geographic Restrictions:**
   - Restrict access from specific countries or regions

5. **IP Reputation Filtering:**
   - Block known malicious IP addresses

**AWS WAF Rule Group Examples:**

1. **AWS Managed Rules:**
   - AWS Core rule set (CRS)
   - SQL database rules
   - Linux operating system rules
   - PHP application rules

2. **Custom Rules:**
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

**Monitoring and Logging:**

1. **Enable CloudWatch Logs:**
   ```yaml
   alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
   ```

2. **Configure WAF Logging:**
   ```bash
   aws wafv2 put-logging-configuration \
     --logging-configuration ResourceArn=arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef,LogDestinationConfigs=arn:aws:firehose:us-west-2:111122223333:deliverystream/aws-waf-logs \
     --region us-west-2
   ```

**Permission Requirements:**

AWS Load Balancer Controller's IAM role needs the following permissions:
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

**Best Practices:**

1. **Defense in Depth:**
   Use WAF together with other security controls like network security, authentication, and authorization.

2. **Regular Rule Updates:**
   Review and update WAF rules regularly to respond to new threats.

3. **Logging and Monitoring:**
   Analyze WAF logs to identify attack patterns and improve rules.

4. **Testing:**
   Validate WAF rules in test environments before applying to production.

5. **Count Mode:**
   When first deploying new rules, set to count mode instead of block to monitor false positives.

Integration of AWS WAF with EKS Ingress is a powerful way to enhance application security and can be easily configured using the appropriate annotation.
</details>

## Hands-on Questions

### 9. Write an Ingress resource that creates an Application Load Balancer using AWS Load Balancer Controller in Amazon EKS cluster and routes traffic to different services based on specific paths.

<details>
<summary>Show Answer</summary>

**Answer:**
The following is an Ingress resource that creates an Application Load Balancer using AWS Load Balancer Controller and routes traffic to different services based on specific paths:

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

**Detailed Explanation:**

1. **Ingress Resource Component Explanation**:

   - **metadata.annotations**: Specifies configuration options for AWS Load Balancer Controller.
     - `kubernetes.io/ingress.class: alb`: Specifies use of AWS Load Balancer Controller.
     - `alb.ingress.kubernetes.io/scheme: internet-facing`: Creates internet-accessible ALB.
     - `alb.ingress.kubernetes.io/target-type: ip`: Uses pod IPs as targets.
     - `alb.ingress.kubernetes.io/listen-ports`: Listens on both HTTP(80) and HTTPS(443) ports.
     - `alb.ingress.kubernetes.io/certificate-arn`: Specifies ACM certificate for HTTPS.
     - `alb.ingress.kubernetes.io/ssl-redirect`: Redirects HTTP traffic to HTTPS.
     - `alb.ingress.kubernetes.io/healthcheck-*`: Configures health check settings.

   - **spec.rules**: Defines host and path-based routing rules.
     - `/api` path is routed to `api-service`.
     - `/admin` path is routed to `admin-service`.
     - `/` (root) path is routed to `frontend-service`.

2. **Implementation Steps**:

   a. **Create Required Services**:
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

   b. **Create Deployments for Services**:
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
   (Similar configurations needed for admin and frontend deployments)

   c. **Verify AWS Load Balancer Controller Installation**:
   ```bash
   kubectl get deployment -n kube-system aws-load-balancer-controller
   ```

   d. **Apply Ingress Resource**:
   ```bash
   kubectl apply -f multi-path-ingress.yaml
   ```

   e. **Check Ingress Status**:
   ```bash
   kubectl get ingress multi-path-ingress
   ```

3. **Testing Method**:

   a. **DNS Setup**:
   Get the DNS name of the ALB created by Ingress:
   ```bash
   kubectl get ingress multi-path-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
   ```

   Set this DNS name as a CNAME record for `example.com`.

   b. **Test Path-Based Routing**:
   ```bash
   # Test API service
   curl https://example.com/api

   # Test admin service
   curl https://example.com/admin

   # Test frontend service
   curl https://example.com/
   ```

4. **Notes and Considerations**:

   a. **SSL Certificate**:
   A valid SSL certificate is required to use HTTPS. Create a certificate in AWS Certificate Manager (ACM) and specify the ARN in the annotation.

   b. **IAM Permissions**:
   AWS Load Balancer Controller needs appropriate IAM permissions to create and manage ALB and related resources.

   c. **Health Checks**:
   Each service must provide a health check endpoint (`/health`).

   d. **Target Group Settings**:
   Using `target-type: ip` means pod IPs are used directly as targets. This provides resilience to node failures and supports Fargate pods.

   e. **Security Groups**:
   If needed, specific security groups can be applied to the ALB:
   ```yaml
   alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
   ```

5. **Additional Configuration Options**:

   a. **Enable Session Stickiness**:
   ```yaml
   alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true,stickiness.lb_cookie.duration_seconds=86400
   ```

   b. **Enable Access Logs**:
   ```yaml
   alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
   ```

   c. **IP-Based Restrictions**:
   ```yaml
   alb.ingress.kubernetes.io/inbound-cidrs: 192.168.0.0/16,10.0.0.0/8
   ```

   d. **Weighted Routing**:
   ```yaml
   alb.ingress.kubernetes.io/actions.weighted-routing: >
     {"Type":"forward","ForwardConfig":{"TargetGroups":[{"ServiceName":"service-v1","ServicePort":"80","Weight":80},{"ServiceName":"service-v2","ServicePort":"80","Weight":20}]}}
   ```

Using AWS Load Balancer Controller and Ingress resources allows implementing complex routing rules in EKS clusters and leveraging various ALB features to improve application availability, scalability, and security.
</details>

## Advanced Questions

### 10. Explain the key considerations and networking architecture changes when implementing a service mesh (e.g., Istio, AWS App Mesh) in an Amazon EKS cluster. Also explain how the service mesh integrates with EKS's default networking model.

<details>
<summary>Show Answer</summary>

**Answer:**
The following explains the key considerations and networking architecture changes when implementing a service mesh (e.g., Istio, AWS App Mesh) in an Amazon EKS cluster, and how the service mesh integrates with EKS's default networking model:

## 1. Service Mesh Overview and Key Components

**What is a Service Mesh?**
A service mesh is an infrastructure layer that manages communication between microservices, providing features such as service discovery, traffic management, security, and observability.

**Key Components:**

1. **Data Plane**:
   - Sidecar proxies (typically Envoy) are injected into each pod.
   - Intercepts and processes all inbound and outbound traffic.

2. **Control Plane**:
   - Manages policies and configuration.
   - Configures data plane proxies.
   - Provides service discovery and routing information.

## 2. EKS Networking Architecture Changes

**Default EKS Networking Model:**
- Uses Amazon VPC CNI to assign VPC IP addresses to pods.
- Pods communicate directly within the VPC.
- Kubernetes Service resources provide service discovery and load balancing.

**Changes After Service Mesh Introduction:**

1. **Traffic Flow Change**:
   ```
   Default EKS: Client -> Service -> Target Pod
   Service Mesh: Client -> Client Sidecar -> Service -> Target Sidecar -> Target Pod
   ```

2. **Network Topology**:
   - Sidecar containers are added to each pod.
   - Applications and sidecars communicate through the local network within the pod.
   - Sidecar-to-sidecar communication still uses VPC CNI.

3. **Port Allocation**:
   - Sidecar proxies use additional ports (management, metrics, health checks, etc.).
   - Port redirection occurs within the pod.

## 3. Major Service Mesh Options Comparison

### Istio

**Architecture Integration:**
```yaml
# Istio sidecar injection example
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
        sidecar.istio.io/inject: "true"  # Automatic sidecar injection
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**Networking Features:**
- Advanced traffic management (weighted routing, canary deployments)
- Circuit breakers and fault injection
- Service-to-service encryption via mTLS
- Fine-grained access control

**EKS Integration Considerations:**
- High resource requirements (especially control plane)
- Limited compatibility with Fargate
- Complex setup and management

### AWS App Mesh

**Architecture Integration:**
```yaml
# App Mesh sidecar injection example
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
        appmesh.k8s.aws/mesh: my-mesh  # App Mesh mesh name
        appmesh.k8s.aws/virtualNode: example-vn  # Virtual node name
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**Networking Features:**
- Seamless integration with AWS services
- Cross-account and hybrid mesh support
- Integration with AWS X-Ray
- Relatively simple setup

**EKS Integration Considerations:**
- Excellent integration with AWS services
- Compatible with Fargate
- Some advanced features may be limited

## 4. Networking Considerations

### Performance Impact

1. **Latency**:
   - Slight latency increase due to additional hops through sidecar proxies (typically <10ms)
   - Optimization techniques:
     ```yaml
     # Istio example: Proxy resource optimization
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

2. **Resource Usage**:
   - Additional CPU and memory overhead per pod (typically 10-15%)
   - Possible reduction in node density

### Network Policy Integration

1. **Relationship with Kubernetes NetworkPolicy**:
   - Service mesh provides L7 policies, while NetworkPolicy provides L3/L4 policies.
   - Both policy types can be used together to implement defense in depth.

2. **Policy Example**:
   ```yaml
   # Istio authentication policy
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

## 5. Service Mesh Implementation Steps

### 1. Verify Prerequisites

- Check cluster version compatibility
- Evaluate resource requirements
- Review networking model

### 2. Install Control Plane

**Istio Example:**
```bash
istioctl install --set profile=default
```

**App Mesh Example:**
```bash
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace
```

### 3. Configure Sidecar Injection

**Automatic Injection:**
```yaml
# Add label to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    istio-injection: enabled  # Istio
    appmesh.k8s.aws/sidecarInjectorWebhook: enabled  # App Mesh
```

### 4. Define Service Mesh Resources

**Istio Virtual Service and Destination Rule:**
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

**App Mesh Virtual Service and Virtual Router:**
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

## 6. Monitoring and Observability

### Metrics Collection

**Prometheus Integration:**
```yaml
# Istio Prometheus configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  addonComponents:
    prometheus:
      enabled: true
```

### Distributed Tracing

**X-Ray Integration (App Mesh):**
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

## 7. Service Mesh Adoption Best Practices

1. **Gradual Adoption**:
   - Start with non-business-critical workloads
   - Expand in stages

2. **Resource Planning**:
   - Consider increasing node size and count
   - Use dedicated node groups for control plane

3. **Networking Optimization**:
   - Prevent unnecessary sidecar injection
   - Configure appropriate timeouts and retry policies

4. **Security Enhancement**:
   - Gradual mTLS adoption
   - Apply principle of least privilege

5. **Monitoring Strategy**:
   - Compare performance before and after service mesh adoption
   - Configure key metrics dashboards

## 8. EKS-Specific Considerations

1. **Fargate Compatibility**:
   - Istio: Limited support (some features unavailable)
   - App Mesh: Full support

2. **AWS Load Balancer Controller Integration**:
   - Ingress gateway and ALB integration:
     ```yaml
     apiVersion: networking.k8s.io/v1
     kind: Ingress
     metadata:
       annotations:
         kubernetes.io/ingress.class: alb
         alb.ingress.kubernetes.io/scheme: internet-facing
         alb.ingress.kubernetes.io/target-type: ip
     ```

3. **IAM Roles and Permissions**:
   - IAM permissions required for App Mesh controller:
     - appmesh:*
     - servicediscovery:*
     - cloudmap:*

4. **VPC CNI Settings**:
   - Consider additional ENI and IP address requirements due to service mesh
   - Recommend enabling prefix delegation:
     ```bash
     kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
     ```

## 9. Service Mesh Selection Guide

| Factor | Istio | AWS App Mesh |
|--------|-------|--------------|
| Feature Set | Very comprehensive | Focused on core features |
| AWS Integration | Third-party integration | Native integration |
| Complexity | High | Medium |
| Resource Requirements | High | Medium |
| Fargate Support | Limited | Full support |
| Community | Very active | Growing |
| Hybrid/Multi-cloud | Strong support | AWS-centric |

Service mesh brings significant changes to the networking architecture of EKS clusters but provides powerful tools for managing the complexity of microservices architecture. Integration with the default EKS networking model is done through the sidecar pattern, which allows adding advanced networking features without changing existing application code. When adopting a service mesh, performance impact, operational complexity, and resource requirements should be carefully considered, and a gradual approach is recommended.
</details>

### 11. What routing resource is used for L7 load balancing (ALB) in Kubernetes Gateway API?

A. IngressRoute
B. HTTPRoute
C. VirtualService
D. ServiceRoute

<details>
<summary>Show Answer</summary>

**Answer: B. HTTPRoute**

**Explanation:**
In Kubernetes Gateway API, the HTTPRoute resource is used for L7 load balancing. HTTPRoute defines rules for routing HTTP/HTTPS traffic to services, and when used with AWS Load Balancer Controller, it distributes traffic through an ALB.

**Gateway API Resource Hierarchy:**

1. **GatewayClass**: Defines load balancer type (e.g., `amazon-alb`, `amazon-nlb`)
2. **Gateway**: Actual load balancer instance (listener ports, TLS settings, etc.)
3. **HTTPRoute**: L7 routing rules (host, path, header-based routing)
4. **TCPRoute**: L4 routing rules (TCP traffic)

**Key HTTPRoute Features:**
- Path and host-based routing
- Native weight-based traffic splitting
- Header and query parameter matching
- Routing to multiple backend services

Issues with other options:
- **A. IngressRoute**: This is not a standard Gateway API resource.
- **C. VirtualService**: This is a resource from the Istio service mesh.
- **D. ServiceRoute**: This resource does not exist.
</details>

### 12. What feature gate flag is required to enable Gateway API in AWS Load Balancer Controller?

A. `--enable-gateway-api`
B. `--feature-gates=EnableGatewayAPI=true`
C. `--gateway-api-enabled=true`
D. `--enable-feature=gateway-api`

<details>
<summary>Show Answer</summary>

**Answer: B. `--feature-gates=EnableGatewayAPI=true`**

**Explanation:**
To enable Gateway API in AWS Load Balancer Controller, the `--feature-gates=EnableGatewayAPI=true` flag must be added when deploying the controller. This feature gate enables the controller to watch and process Gateway API resources (GatewayClass, Gateway, HTTPRoute, TCPRoute, etc.).

**Complete Prerequisites for Gateway API Activation:**

1. Install AWS Load Balancer Controller v2.13.0 or later
2. Add `--feature-gates=EnableGatewayAPI=true` flag
3. Install Gateway API Standard CRDs
4. Install Experimental CRDs (when using TCPRoute, etc.)
5. Install AWS LBC-specific CRDs

Issues with other options:
- **A, C, D**: These flags are incorrect formats not used by AWS Load Balancer Controller.
</details>

### 13. What resource is used to route L4-level TCP traffic through an NLB in Gateway API?

A. HTTPRoute
B. TLSRoute
C. TCPRoute
D. GRPCRoute

<details>
<summary>Show Answer</summary>

**Answer: C. TCPRoute**

**Explanation:**
In Gateway API, the TCPRoute resource is used to route L4-level TCP traffic. When used with AWS Load Balancer Controller, TCPRoute forwards TCP traffic to backend services through an NLB (Network Load Balancer).

**TCPRoute Configuration Example:**
```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TCPRoute
metadata:
  name: db-route
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

| Resource | Protocol | AWS LB Type |
|----------|----------|-------------|
| HTTPRoute | HTTP/HTTPS | ALB |
| TCPRoute | TCP | NLB |
| TLSRoute | TLS | NLB |
| GRPCRoute | gRPC | ALB |

Issues with other options:
- **A. HTTPRoute**: Used for HTTP/HTTPS L7 traffic with ALB.
- **B. TLSRoute**: For TLS traffic routing, but TCPRoute is appropriate for TCP-level routing.
- **D. GRPCRoute**: A routing resource specifically for gRPC protocol.
</details>
