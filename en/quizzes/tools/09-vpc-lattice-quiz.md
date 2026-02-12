# VPC Lattice Quiz

This quiz tests your understanding of Amazon VPC Lattice.

## Multiple Choice Questions

1. What is the main purpose of Amazon VPC Lattice?
   - A) Managing external traffic from the internet to AWS resources
   - B) Internal communication between services across different VPCs and accounts
   - C) Data replication between AWS regions
   - D) DNS-based global load balancing

<details>

<summary>Show Answer</summary>

**Answer: B) Internal communication between services across different VPCs and accounts**

**Explanation:**
VPC Lattice is an AWS application networking service whose main purpose is to securely connect and manage services across multiple VPCs and AWS accounts. It provides service discovery, traffic routing, authentication, and authorization within a logical boundary called Service Network. External traffic management is handled by API Gateway or ALB, and cross-region replication is handled by services like S3 Cross-Region Replication.
</details>

2. Which is correct about VPC Lattice's Service Network?
   - A) A layer connecting physical network equipment
   - B) A logical boundary that groups services and manages their communication
   - C) A routing table connecting subnets within a VPC
   - D) A replacement service for Internet Gateway

<details>

<summary>Show Answer</summary>

**Answer: B) A logical boundary that groups services and manages their communication**

**Explanation:**
Service Network is a core component of VPC Lattice that logically groups multiple services. When you associate a VPC with a Service Network, resources in that VPC can communicate with services in the network. Multiple VPCs (including from different accounts) can be connected to a single Service Network, and authentication policies and access controls for each service can be managed centrally.
</details>

3. What is the difference between VPC Lattice and AWS App Mesh?
   - A) VPC Lattice requires sidecar proxies but App Mesh doesn't
   - B) App Mesh is sidecar proxy-based while VPC Lattice doesn't require sidecars
   - C) VPC Lattice only supports TCP and App Mesh only supports HTTP
   - D) Both services use the same architecture

<details>

<summary>Show Answer</summary>

**Answer: B) App Mesh is sidecar proxy-based while VPC Lattice doesn't require sidecars**

**Explanation:**
AWS App Mesh is a service mesh that injects Envoy sidecar proxies into each service pod to control traffic. VPC Lattice, on the other hand, is a fully managed AWS service that provides inter-service communication, routing, and authentication without sidecar proxies. This makes VPC Lattice less operationally complex with lower resource overhead, though some of the fine-grained traffic control features provided by App Mesh may be limited.
</details>

4. What Kubernetes API is used when integrating EKS with VPC Lattice?
   - A) Ingress API
   - B) Service API
   - C) Gateway API
   - D) NetworkPolicy API

<details>

<summary>Show Answer</summary>

**Answer: C) Gateway API**

**Explanation:**
AWS Gateway API Controller converts Kubernetes Gateway API resources (GatewayClass, Gateway, HTTPRoute, etc.) into VPC Lattice resources. Gateway API is the next-generation ingress specification for Kubernetes, providing richer features and extensibility than Ingress. By specifying the amazon-vpc-lattice controller with GatewayClass and creating Gateway and HTTPRoute, the controller automatically creates VPC Lattice Services and Target Groups.
</details>

5. What is the correct DNS name format for VPC Lattice services?
   - A) service-name.region.amazonaws.com
   - B) service-name.vpc-lattice-svcs.region.on.aws
   - C) service-name.internal.aws
   - D) service-name.lattice.region.aws

<details>

<summary>Show Answer</summary>

**Answer: B) service-name.vpc-lattice-svcs.region.on.aws**

**Explanation:**
VPC Lattice services are automatically assigned DNS names. The format is `<service-name>.<service-network-id>.vpc-lattice-svcs.<region>.on.aws`. This DNS name is resolvable from all VPCs connected to the Service Network. Clients access services using this DNS name, and VPC Lattice internally routes to the appropriate targets. To use custom domains, you can set up CNAME or Alias records in Route 53, etc.
</details>

6. What authentication methods does VPC Lattice support?
   - A) API Key only
   - B) OAuth 2.0 only
   - C) AWS IAM or no authentication
   - D) SAML only

<details>

<summary>Show Answer</summary>

**Answer: C) AWS IAM or no authentication**

**Explanation:**
VPC Lattice supports two authentication modes. In AWS_IAM mode, requests require SigV4 (Signature Version 4) signatures, and access is controlled through IAM policies and resource policies. In NONE mode, all requests are allowed without authentication. Using IAM authentication enables fine-grained control over which IAM roles/users can access which paths of which services.
</details>

7. Which is NOT a supported target type in VPC Lattice Target Groups?
   - A) EC2 instances
   - B) EKS pods (IP type)
   - C) Lambda functions
   - D) RDS databases

<details>

<summary>Show Answer</summary>

**Answer: D) RDS databases**

**Explanation:**
VPC Lattice Target Groups support EC2 instances, IP addresses (including EKS pods), Lambda functions, and ALB as targets. RDS databases cannot be VPC Lattice targets because they use database protocols rather than HTTP/HTTPS. For EKS pods, IP type Target Groups are used, and the AWS Gateway API Controller automatically registers/deregisters pod IPs.
</details>

8. What is the main use case for weighted routing in VPC Lattice?
   - A) Load balancing only
   - B) Canary deployments and blue-green deployments
   - C) Geographic-based routing
   - D) Sticky sessions

<details>

<summary>Show Answer</summary>

**Answer: B) Canary deployments and blue-green deployments**

**Explanation:**
Weighted routing distributes traffic proportionally across multiple Target Groups. In canary deployments, 10% of traffic is sent to the new version for validation, then gradually increased. In blue-green deployments, 100% is switched from blue to green at once. Example: Setting `service-v1: weight 90, service-v2: weight 10` sends only 10% of traffic to v2. If issues are found, weights can be adjusted to rollback.
</details>

## Short Answer Questions

9. Explain how to share a VPC Lattice Service Network across accounts.

<details>

<summary>Show Answer</summary>

**Answer:**
Use AWS Resource Access Manager (RAM) to share the Service Network with other AWS accounts or organizations.

**Explanation:**
Cross-account sharing process:
1. **Owner account**: Create resource share for Service Network in RAM
   ```bash
   aws ram create-resource-share \
     --name my-service-network-share \
     --resource-arns arn:aws:vpc-lattice:region:account:servicenetwork/sn-xxx \
     --principals 123456789012  # Target account ID
   ```
2. **Target account**: Accept RAM invitation
3. **Target account**: Associate their VPC with the shared Service Network
4. After that, services from the target account can also register with the Service Network

Automatic sharing to the entire organization is also possible when using Organizations.
</details>

10. Explain why Health Check configuration is important in VPC Lattice.

<details>

<summary>Show Answer</summary>

**Answer:**
Health Checks automatically exclude unhealthy targets from traffic routing to ensure service availability.

**Explanation:**
How VPC Lattice Health Checks work:
1. **Periodic checks**: Requests are sent to target health check endpoints at configured intervals (e.g., 30 seconds)
2. **Threshold-based determination**: Status is determined by consecutive success/failure counts (healthyThresholdCount/unhealthyThresholdCount)
3. **Automatic exclusion/recovery**: Unhealthy targets are excluded from traffic and automatically restored when recovered
4. **Configuration example**:
   ```yaml
   healthCheck:
     enabled: true
     protocol: HTTP
     path: /health
     healthCheckIntervalSeconds: 30
     healthyThresholdCount: 5
     unhealthyThresholdCount: 2
     matcher:
       httpCode: "200-299"
   ```
Proper Health Check configuration prevents downtime during rolling updates and protects user experience by preventing requests to failed targets.
</details>

11. Explain the differences between VPC Lattice and Transit Gateway.

<details>

<summary>Show Answer</summary>

**Answer:**
Transit Gateway provides IP routing between VPCs at the network layer (L3), while VPC Lattice provides service-based communication at the application layer (L7).

**Explanation:**
Key differences:

| Aspect | Transit Gateway | VPC Lattice |
|--------|-----------------|-------------|
| Abstraction level | Network (IP-based) | Service (name-based) |
| Routing | IP routing tables | HTTP path/header-based |
| Protocols | All IP traffic | HTTP/HTTPS/gRPC |
| Authentication | Security Groups, NACLs | AWS IAM, resource policies |
| Visibility | Network flow logs | Application-level metrics/logs |

Transit Gateway is used when all IP communication between VPCs is needed, while VPC Lattice is suitable for HTTP-based communication between microservices. Both services can be used together.
</details>

12. Explain the role of Auth Policy in VPC Lattice and the levels at which it can be applied.

<details>

<summary>Show Answer</summary>

**Answer:**
Auth Policy defines IAM-based access control and is applied at both the Service Network level and individual Service level.

**Explanation:**
Auth Policy application levels:
1. **Service Network level**: Default policy applied to the entire network
   - Controls which IAM principals can connect to the network
2. **Service level**: Detailed policy applied to individual services
   - Controls which principals can access which paths of a specific service

Policy example:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
    },
    "Action": "vpc-lattice-svcs:Invoke",
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "vpc-lattice-svcs:RequestPath": "/api/*"
      }
    }
  }]
}
```
This policy restricts MyAppRole to only access the /api/* path.
</details>

## Hands-on Questions

13. Write the IAM policy and IRSA configuration to install the AWS Gateway API Controller on EKS.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# 1. Create IAM policy for VPC Lattice permissions
cat <<EOF > vpc-lattice-controller-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc-lattice:*",
        "iam:CreateServiceLinkedRole",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeAvailabilityZones"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document file://vpc-lattice-controller-policy.json

# 2. Create service account using IRSA
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=aws-application-networking-system \
  --name=gateway-api-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/VPCLatticeControllerPolicy \
  --override-existing-serviceaccounts \
  --approve

# 3. Install AWS Gateway API Controller
kubectl apply -f https://raw.githubusercontent.com/aws/aws-application-networking-k8s/main/files/controller-installation/deploy-v1.0.yaml
```

**Explanation:**
The AWS Gateway API Controller watches Gateway API resources in the Kubernetes cluster and creates/manages VPC Lattice resources. Through IRSA (IAM Roles for Service Accounts), the controller pod gains permissions to call the required AWS APIs. The policy includes vpc-lattice operations, VPC/subnet lookup, and log delivery permissions.
</details>

14. Write an HTTPRoute that configures weighted routing (90:10) between two services using VPC Lattice.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
# GatewayClass definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
# Gateway definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: default
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
# Weighted routing HTTPRoute
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: weighted-routing
  namespace: default
spec:
  parentRefs:
  - name: my-gateway
    sectionName: http
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 80
      weight: 90
    - name: service-canary
      port: 80
      weight: 10
---
# Stable service
apiVersion: v1
kind: Service
metadata:
  name: service-stable
spec:
  selector:
    app: myapp
    version: stable
  ports:
  - port: 80
    targetPort: 8080
---
# Canary service
apiVersion: v1
kind: Service
metadata:
  name: service-canary
spec:
  selector:
    app: myapp
    version: canary
  ports:
  - port: 80
    targetPort: 8080
```

**Explanation:**
In this configuration, 90% of traffic to the `/api` path is routed to service-stable and 10% to service-canary. When the AWS Gateway API Controller detects this HTTPRoute, it creates two Target Groups in VPC Lattice and sets up listener rules to distribute traffic according to the specified weights. After validating the canary deployment, weights can be gradually adjusted.
</details>

15. Write an IAM-based Auth Policy for a VPC Lattice service. (Allow only specific IAM roles to access the /admin path)

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Apply Auth Policy to VPC Lattice service
aws vpc-lattice put-auth-policy \
  --resource-identifier svc-0123456789abcdef0 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowGeneralAccess",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringNotEquals": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "AllowAdminAccess",
        "Effect": "Allow",
        "Principal": {
          "AWS": [
            "arn:aws:iam::123456789012:role/AdminRole",
            "arn:aws:iam::123456789012:role/DevOpsRole"
          ]
        },
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "DenyUnauthorizedAdmin",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          },
          "StringNotEquals": {
            "aws:PrincipalArn": [
              "arn:aws:iam::123456789012:role/AdminRole",
              "arn:aws:iam::123456789012:role/DevOpsRole"
            ]
          }
        }
      }
    ]
  }'
```

**Kubernetes Gateway API method:**
```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: secure-gateway
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-type: "AWS_IAM"
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vpc-lattice-auth-policy
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-policy: |
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "AWS": "arn:aws:iam::123456789012:role/AdminRole"
            },
            "Action": "vpc-lattice-svcs:Invoke",
            "Resource": "*"
          }
        ]
      }
data: {}
```

**Explanation:**
This Auth Policy consists of three rules:
1. **AllowGeneralAccess**: Allow all principals for all paths except /admin/*
2. **AllowAdminAccess**: Allow AdminRole and DevOpsRole access to /admin/* path
3. **DenyUnauthorizedAdmin**: Explicitly deny /admin/* access for principals other than the above roles

Clients must sign requests with SigV4. You can use the AWS SDK or aws-sigv4 library for signing.
</details>

---

**Scoring:**
- 13-15 correct: Excellent (VPC Lattice expert level)
- 10-12 correct: Good (practical application capable)
- 7-9 correct: Average (additional learning recommended)
- 4-6 correct: Basic (basic concepts review needed)
- 0-3 correct: Insufficient (full content re-study needed)
