# EKS Networking - Part 2: Services, Load Balancing, and Network Policies

## Overview

In this document, we will learn about services, load balancing, and network policies in Amazon EKS. We cover how to expose applications through Kubernetes services, integration with AWS load balancers, and how to control pod-to-pod communication using network policies.

## Kubernetes Service Types

Kubernetes provides the following service types:

```mermaid
flowchart TD
    subgraph Service_Types ["Kubernetes Service Types"]
        ClusterIP[ClusterIP<br>Accessible only within the cluster]
        NodePort[NodePort<br>Accessible through a specific port on all nodes]
        LoadBalancer[LoadBalancer<br>Accessible through an external load balancer]
        ExternalName[ExternalName<br>Provides CNAME record for external services]
    end

    subgraph Access_Methods ["Access Methods"]
        Internal[Within cluster]
        Node_Access[Node IP:Port]
        External_LB[External load balancer]
        DNS[DNS CNAME]
    end

    ClusterIP --> Internal
    NodePort --> Node_Access
    LoadBalancer --> External_LB
    ExternalName --> DNS

    %% Class definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class ClusterIP,NodePort,LoadBalancer,ExternalName k8sComponent;
    class External_LB awsService;
    class Internal,Node_Access,DNS default;
```

1. **ClusterIP**: Service accessible only within the cluster
2. **NodePort**: Service accessible through a specific port on all nodes
3. **LoadBalancer**: Service accessible through an external load balancer
4. **ExternalName**: Provides CNAME record for external services

### ClusterIP Service

A ClusterIP service is accessible only within the cluster. This is the default service type.

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

### NodePort Service

A NodePort service is accessible through a specific port on all nodes.

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

### LoadBalancer Service

A LoadBalancer service is accessible through an external load balancer. In EKS, this integrates with AWS load balancers (CLB, NLB, ALB).

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

### ExternalName Service

An ExternalName service provides a CNAME record for external services.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ExternalName
  externalName: my-service.example.com
```

## AWS Load Balancer Integration

EKS integrates Kubernetes services with AWS load balancers to make applications accessible from outside.

```mermaid
flowchart TD
    subgraph Internet ["Internet"]
        Users((Users))
    end

    subgraph AWS_Cloud ["AWS Cloud"]
        subgraph Load_Balancers ["AWS Load Balancers"]
            CLB[Classic Load Balancer]
            NLB[Network Load Balancer]
            ALB[Application Load Balancer]
        end

        subgraph EKS_Cluster ["EKS Cluster"]
            subgraph Services ["Kubernetes Services"]
                Service1[LoadBalancer Service]
                Service2[NodePort Service]
                Ingress[Ingress Resource]
            end

            subgraph Pods ["Pods"]
                Pod1[Pod 1]
                Pod2[Pod 2]
                Pod3[Pod 3]
            end
        end
    end

    Users --> CLB
    Users --> NLB
    Users --> ALB
    CLB --> Service1
    NLB --> Service1
    ALB --> Ingress
    Ingress --> Service2
    Service1 --> Pod1
    Service1 --> Pod2
    Service2 --> Pod3

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CLB,NLB,ALB awsService;
    class Service1,Service2,Ingress k8sComponent;
    class Pod1,Pod2,Pod3 userApp;
    class Users default;
```

### Classic Load Balancer (CLB)

By default, services set to `type: LoadBalancer` create a Classic Load Balancer. However, CLB is no longer recommended, and using NLB or ALB is preferred.

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

### Network Load Balancer (NLB)

To use NLB, you need to add specific annotations to the service:

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

Additional NLB configuration options:

```yaml
metadata:
  annotations:
    # Create internal NLB
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"

    # Enable cross-zone load balancing
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

    # Specify target type (instance or ip)
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true

    # Enable TCP proxy protocol
    service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
```

### Application Load Balancer (ALB)

To use ALB, you need to install the AWS Load Balancer Controller and use Ingress resources:

```mermaid
flowchart TD
    subgraph AWS_Cloud ["AWS Cloud"]
        subgraph VPC ["VPC"]
            subgraph Public_Subnets ["Public Subnets"]
                ALB[Application Load Balancer]
            end

            subgraph Private_Subnets ["Private Subnets"]
                subgraph EKS_Cluster ["EKS Cluster"]
                    ALBIC[AWS Load Balancer Controller]
                    Ingress[Ingress Resource]
                    Service1[Service 1]
                    Service2[Service 2]
                    Pod1[Pod 1]
                    Pod2[Pod 2]
                end
            end
        end
    end

    Internet((Internet)) --> ALB
    ALB --> Ingress
    ALBIC --> ALB
    Ingress --> Service1
    Ingress --> Service2
    Service1 --> Pod1
    Service2 --> Pod2

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class ALB,Public_Subnets,Private_Subnets awsService;
    class ALBIC,Ingress,Service1,Service2 k8sComponent;
    class Pod1,Pod2 userApp;
    class Internet default;
```

1. Install AWS Load Balancer Controller:

```bash
# Download IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

# Create IAM policy
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam-policy.json

# Create IAM role and attach policy (using eksctl)
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Add Helm repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install AWS Load Balancer Controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=my-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

2. Create Ingress resource:

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

Additional ALB configuration options:

```yaml
metadata:
  annotations:
    # Create internal ALB
    alb.ingress.kubernetes.io/scheme: internal

    # Specify SSL certificate
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id

    # HTTPS redirect
    alb.ingress.kubernetes.io/actions.ssl-redirect: '{"Type": "redirect", "RedirectConfig": {"Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}'

    # Specify target type (instance or ip)
    alb.ingress.kubernetes.io/target-type: ip

    # Specify security groups
    alb.ingress.kubernetes.io/security-groups: sg-xxxx,sg-yyyy
```

### Service and Load Balancer Best Practices

```mermaid
flowchart TD
    A[Service and Load Balancer Best Practices] --> B[Use ClusterIP for internal services]
    A --> C[Use LoadBalancer or Ingress for external services]
    A --> D[Use ALB when path-based routing, SSL termination, authentication are needed]
    A --> E[Use NLB when TCP/UDP traffic, high performance, static IP are needed]
    A --> F[Use internal load balancers for services accessed only within the cluster]
    A --> G[Enable cross-zone load balancing for high availability]
    A --> H[Select appropriate target type]

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class A,B,C,D,E,F,G,H default;
```

1. **Use ClusterIP for internal services**: Use ClusterIP type for services accessed only within the cluster.
2. **Use LoadBalancer or Ingress for external services**: Use LoadBalancer type or Ingress resources for services that need external access.
3. **Use ALB**: Use ALB when features like path-based routing, SSL termination, and authentication are needed.
4. **Use NLB**: Use NLB when TCP/UDP traffic, high performance, and static IP are needed.
5. **Use internal load balancers**: Use internal load balancers for services accessed only within the cluster.
6. **Enable cross-zone load balancing**: Enable cross-zone load balancing for high availability.
7. **Select appropriate target type**: Choose `ip` target type to use pod IPs directly as targets, or `instance` target type to use node IPs as targets.

## Network Policies

Network policies are used to control pod-to-pod communication. To use network policies in EKS, you need to install a CNI plugin that supports network policies (e.g., Calico, Cilium).

```mermaid
flowchart TD
    subgraph EKS_Cluster ["EKS Cluster"]
        subgraph Network_Policies ["Network Policies"]
            NP1[Namespace Isolation Policy]
            NP2[Specific Pod Communication Allow Policy]
            NP3[External Traffic Restriction Policy]
            NP4[Egress Traffic Restriction Policy]
        end

        subgraph Namespaces ["Namespaces"]
            subgraph NS1 ["Namespace 1"]
                Pod1[Frontend Pod]
                Pod2[Backend Pod]
            end

            subgraph NS2 ["Namespace 2"]
                Pod3[Database Pod]
            end
        end

        NP1 --> NS1
        NP1 --> NS2
        NP2 --> Pod1
        NP2 --> Pod2
        NP3 --> Pod1
        NP4 --> Pod2
        Pod1 --> Pod2
        Pod2 --> Pod3
    end

    External((External Services)) --> Pod1
    Pod2 --> External

    %% Class definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class NP1,NP2,NP3,NP4,NS1,NS2 k8sComponent;
    class Pod1,Pod2 userApp;
    class Pod3 dataStore;
    class External default;
```

### Installing Calico

Calico is a widely used CNI plugin for implementing network policies in EKS:

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Default Network Policy

By default, without network policies, all pods can communicate with each other. When network policies are applied, only explicitly allowed traffic is permitted.

### Namespace Isolation Policy

A policy that allows communication only between pods within a specific namespace:

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

### Specific Pod Communication Allow Policy

A policy that allows communication only between pods with specific labels:

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

### External Traffic Restriction Policy

A policy that allows traffic only from specific IP ranges:

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

### Egress Traffic Restriction Policy

A policy that allows egress traffic only to specific destinations:

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

### Network Policy Best Practices

```mermaid
flowchart TD
    A[Network Policy Best Practices] --> B[Apply default deny policy]
    A --> C[Namespace isolation]
    A --> D[Apply principle of least privilege]
    A --> E[Restrict egress traffic]
    A --> F[Test policies]

    %% Class definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class A,B,C,D,E,F default;
```

1. **Apply default deny policy**: Deny all traffic by default and explicitly allow only necessary traffic.
2. **Namespace isolation**: Enhance security by restricting communication between namespaces.
3. **Apply principle of least privilege**: Allow only the minimum necessary communication.
4. **Restrict egress traffic**: Enhance security by restricting traffic going out from pods.
5. **Test policies**: Test network policies before applying them to prevent unintended communication blocking.

---

## Gateway API

> **Supported Versions**: AWS Load Balancer Controller v2.13.0+
> **Last Updated**: February 2025

### Overview

Gateway API is Kubernetes' next-generation service networking API that overcomes the limitations of traditional Ingress resources and provides richer routing capabilities. AWS Load Balancer Controller supports Gateway API, enabling L4 (NLB) and L7 (ALB) routing configuration through Gateway resources.

```mermaid
flowchart TD
    GC[GatewayClass] --> GW[Gateway]
    GW --> HR[HTTPRoute - L7/ALB]
    GW --> TR[TCPRoute - L4/NLB]
    HR --> SVC1[Service A]
    HR --> SVC2[Service B]
    TR --> SVC3[Service C]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    class GC,GW,HR,TR k8sComponent;
    class SVC1,SVC2,SVC3 awsService;
```

### Prerequisites

1. **AWS Load Balancer Controller v2.13.0 or later** installed
2. **Feature Gates enabled**: Add `--feature-gates=EnableGatewayAPI=true` flag when deploying the controller
3. **Gateway API CRD installation**:

```bash
# Install Standard CRDs
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml

# Install Experimental CRDs (TCPRoute, etc.)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/experimental-install.yaml

# Install AWS LBC-specific CRDs
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/config/crd/gateway-api/crds.yaml
```

### GatewayClass and Gateway Setup

GatewayClass defines the type of load balancer, and Gateway represents the actual load balancer instance.

```yaml
# GatewayClass definition
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-alb
spec:
  controllerName: gateway.k8s.aws/alb

---
# Gateway definition (L7 - ALB)
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-hotel-gateway
  namespace: default
spec:
  gatewayClassName: amazon-alb
  listeners:
  - name: http
    protocol: HTTP
    port: 80
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: my-tls-secret
```

### HTTPRoute Example (L7 → ALB)

HTTPRoute defines rules for routing HTTP/HTTPS traffic to services. HTTPRoutes attached to a Gateway distribute traffic through an ALB.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: default
spec:
  parentRefs:
  - name: my-hotel-gateway
    sectionName: http
  hostnames:
  - "app.example.com"
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

### TCPRoute Example (L4 → NLB)

TCPRoute handles TCP traffic and provides L4-level load balancing through an NLB.

```yaml
# GatewayClass for NLB
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-nlb
spec:
  controllerName: gateway.k8s.aws/nlb

---
# NLB Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-nlb-gateway
spec:
  gatewayClassName: amazon-nlb
  listeners:
  - name: tcp
    protocol: TCP
    port: 5432

---
# TCPRoute
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

### QUIC/HTTP3 Support

ALBs created through Gateway API automatically support the QUIC/HTTP3 protocol. When an HTTPS listener is configured, the ALB automatically handles QUIC protocol upgrades.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quic-gateway
  annotations:
    gateway.k8s.aws/quic-enabled: "true"
spec:
  gatewayClassName: amazon-alb
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: tls-cert
```

### Certificate Discovery

AWS Load Balancer Controller supports two certificate discovery methods:

1. **Static certificate reference**: Directly specified in the Gateway's `tls.certificateRefs`
2. **Hostname-based auto-discovery**: Automatically searches ACM for matching certificates based on the HTTPRoute's `hostnames` field

```yaml
# Hostname-based auto-discovery example
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: auto-cert-route
spec:
  parentRefs:
  - name: my-gateway
  hostnames:
  - "secure.example.com"  # Auto-discovers matching certificate from ACM
  rules:
  - backendRefs:
    - name: secure-service
      port: 443
```

### Security Groups

Load balancers created through Gateway API automatically have security groups created:

- **Frontend security group**: Allows inbound traffic from clients to the load balancer
- **Backend security group**: Allows traffic from the load balancer to target pods

Custom security groups can also be specified through Gateway annotations:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: custom-sg-gateway
  annotations:
    gateway.k8s.aws/security-group-ids: sg-0123456789abcdef0,sg-0987654321fedcba0
spec:
  gatewayClassName: amazon-alb
  listeners:
  - name: http
    protocol: HTTP
    port: 80
```

### Out-of-Band Target Groups

Using `TargetGroupName` backendRef allows connecting pre-existing target groups to Gateway API routing. This is useful for integration with existing infrastructure or migration scenarios.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: oob-route
spec:
  parentRefs:
  - name: my-gateway
  rules:
  - backendRefs:
    - group: gateway.k8s.aws
      kind: TargetGroupBinding
      name: existing-target-group
```

### Gateway API vs Ingress Comparison

| Feature | Ingress | Gateway API |
|---------|---------|-------------|
| Routing Model | Host/Path based | Host/Path/Header/Query based |
| Protocol Support | HTTP/HTTPS | HTTP, HTTPS, TCP, TLS, gRPC |
| Traffic Splitting | Annotation based | Native weight-based |
| Role Separation | Single resource | GatewayClass/Gateway/Route separation |
| Extensibility | Limited via annotations | Extensible via Policy attachment |
| L4 Load Balancing | Not supported | TCPRoute/UDPRoute supported |

## Quiz

To test what you learned in this chapter, try the [Topic Quiz](../quizzes/eks/03-eks-networking-part2-quiz.md).
