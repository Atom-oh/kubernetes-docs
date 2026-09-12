# VPC Lattice

Amazon VPC Lattice connects applications across VPCs and AWS accounts. This chapter explains the resource model, an EKS integration, routing, IAM authorization, monitoring, and troubleshooting.

> Reviewed on 2026-09-11 against AWS Gateway API Controller **v2.1.3** and Gateway API **v1.5.0**. The examples describe configuration and validation steps; they have not been deployed to an AWS account as part of this review.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [EKS and VPC Lattice Integration](#eks-and-vpc-lattice-integration)
- [Installation and Configuration](#installation-and-configuration)
- [Service Management](#service-management)
- [Routing and Traffic Management](#routing-and-traffic-management)
- [Security and Authentication](#security-and-authentication)
- [Monitoring and Logging](#monitoring-and-logging)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Overview

### What is VPC Lattice?

VPC Lattice provides application networking without requiring a proxy beside every application. A **service network** groups services and resource configurations and connects them to authorized consumers. Services provide listeners, routing rules, target groups, and service DNS names.

The current product also connects **resource configurations** through resource gateways, including resources such as RDS databases that use TCP. This resource access model is distinct from an HTTP service backed by a target group; service-network/service IAM auth policies do not authorize resource-configuration traffic. A **service network VPC endpoint**, powered by PrivateLink, can provide access from clients reached through peering, Transit Gateway, Direct Connect, or VPN. A direct VPC association alone does not extend access to clients behind a transit gateway or peering connection.

Typical uses include cross-account application APIs, communication between EKS and other compute services, and shared data-resource access. Association, routing, security groups, authentication, and application authorization still require configuration.

### Comparison with Other Services

| Service | Main responsibility | Important distinction |
|---|---|---|
| VPC Lattice | Private application and resource connectivity | HTTP/HTTPS/gRPC service routing and separate TLS/TCP resource capabilities; not an Internet API front door |
| API Gateway | Managed API endpoints and API management | REST, HTTP, or WebSocket APIs have different features; GraphQL is not a separate API Gateway API type |
| AWS App Mesh | Envoy-based service mesh | AWS will end support on **2026-09-30**; as of this review that date is upcoming. Plan migration instead of a new installation |
| Transit Gateway | Network connectivity using IP routing | Connects networks; it does not replace per-service HTTP routing and authorization |
| Istio / Linkerd / Cilium | Mesh capabilities implemented with their respective data planes | Features and operating costs differ. Sidecars are not mandatory in every mesh architecture |

VPC Lattice eliminates the need to operate its managed data plane, but does not promise lower total cost or identical mesh functionality. Compare request/data/resource charges, controller operations, identity requirements, retries, routing features, and observability for the actual workload. See the [Istio–Lattice comparison](../service-mesh/istio/comparison/02-istio-vs-lattice.md).

## Architecture

### Components and Traffic Flow

| Component | Responsibility |
|---|---|
| Service network | Logical grouping and associations; optional IAM authorization boundary |
| Service | Application endpoint with its own DNS name |
| Listener and rules | Belong to a **service**; select actions and target groups |
| Target group | Registered instance, IP, Lambda, or ALB targets, with target-type-specific behavior |
| VPC association | Allows clients in an associated VPC to access the network, subject to security controls |
| Service network VPC endpoint | PrivateLink-based access, including supported transit/on-premises paths |
| Resource configuration / resource gateway | Separate resource access model, including TCP/database resources |

![Three VPCs in two AWS accounts associate with a service network, whose services use target groups for EC2, EKS, and Lambda workloads.](../.gitbook/assets/en-networking-02-vpc-lattice-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-02-vpc-lattice-1.html)

The figure shows logical associations, not a single router process. Access also depends on network reachability and the applicable policies. A request resolves the **service's** DNS name, reaches its listener, passes the applicable authorization checks, and is routed to a target according to the listener rules. A target group describes destinations; it is not another application hop.

Use `get-service --query dnsEntry` or the controller's route annotation to discover the real domain. Do not construct one from the service name and service-network ID. An assigned name contains service-specific identifiers; recreating a service can change it.

### Security Model

Network access, IAM authorization, and encryption are separate controls. `AWS_IAM` requires a supported signed request and appropriate policies. `NONE` disables IAM authentication at that particular layer; it does not bypass another layer's IAM policy, security groups, or application authorization. HTTPS protects client-to-Lattice traffic. Backend HTTP remains plaintext unless backend TLS is explicitly configured.

## EKS and VPC Lattice Integration

The AWS Gateway API Controller reconciles Kubernetes resources into VPC Lattice resources:

| Kubernetes resource | Lattice interpretation |
|---|---|
| GatewayClass | Selects `application-networking.k8s.aws/gateway-api-controller` |
| Gateway | Refers to a service network by the **Gateway name**, without its namespace |
| HTTPRoute / GRPCRoute | Creates a service with its own domain and listener/routing configuration |
| Backend Service and its endpoints | Define target groups and registered pod endpoints |
| TargetGroupPolicy | Configures the target group's protocol and health checks |
| IAMAuthPolicy | Attaches an auth policy to a Gateway's network or a Route's service |
| AccessLogPolicy | Configures a target resource's access-log destination |

Two Gateways with the same name can refer to the same service network even when their Kubernetes namespaces differ. A Gateway alone does **not** create the network or one shared ingress IP. The network can be managed externally, with the controller's `defaultServiceNetwork` option for simple cases, or with the controller's ServiceNetwork CRD. Choose one owner for each cloud resource.

The examples below use an externally managed network and VPC association. They leave `defaultServiceNetwork` unset and do not attach a VpcAssociationPolicy to that association. If adopting the CRD-based model, manage the network, VPC association, and authorization as separate resources; do not also manage the same resources with CloudFormation.

## Installation and Configuration

### Prerequisites

The controller's v2.1 upgrade guide requires **Kubernetes 1.31 or later** and Gateway API **1.5 or later**. This example pins the version against which v2.1 was built, **1.5.0**. This minimum is not an EKS support matrix or proof of compatibility with every newer Gateway API release. Check the EKS version lifecycle and all controllers that share the Gateway API CRDs before changing them. In particular, a v2.0 controller can fail after the TLSRoute storage/API transition introduced with Gateway API 1.5.

Use a supported EKS cluster, matching `kubectl`, Helm, AWS CLI v2, and an operator role permitted to configure the intended resources. The sample backend assumes Linux pods with IPs reachable by VPC Lattice. Confirm the cluster's CNI, subnet capacity, endpoint readiness, DNS, and network-policy configuration.

```bash
export AWS_REGION=us-west-2
export CLUSTER_NAME=my-cluster
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export VPC_ID="$(aws eks describe-cluster --name "$CLUSTER_NAME" \
  --query 'cluster.resourcesVpcConfig.vpcId' --output text)"
export NETWORK_NAME=my-network
export ASSOCIATION_SG_ID=sg-0123456789abcdef0
kubectl config current-context
kubectl version
```

Replace the example security group ID. The VPC-association security group must allow **approved clients** on TCP 443. Backend pod/node security groups must allow the applicable Lattice managed prefix list on the actual backend/health port, TCP 8080 here. Inspect the groups attached to the real pod ENI or node ENI instead of assuming that every node uses the EKS cluster security group. Also permit the EKS control plane to reach the controller webhook on its required port. Do not open every port to the entire Internet.

### IAM Role Setup

The **controller role** manages cloud resources. The **caller role** signs application requests and needs `vpc-lattice-svcs:Invoke`; they are different roles.

Use EKS Pod Identity on supported nodes, or IRSA. The IRSA example below assumes the cluster's IAM OIDC provider already exists and creates a dedicated service account. For Pod Identity, use the current EKS add-on and an association for this same namespace/service account, with the appropriate trust policy; do not also rely on an IRSA annotation for the same example.

The release's recommended controller policy includes broad `vpc-lattice:*` and logging/tagging permissions. Treat it as an upstream starting point, **not a least-privilege policy**. Review its resource scope and enabled features, retain the constrained service-linked-role conditions, and save the reviewed policy before creating it. Reuse an existing reviewed policy ARN instead of creating duplicate policies on later runs.

```bash
curl --fail --location --output controller-policy-upstream.json \
  https://raw.githubusercontent.com/aws/aws-application-networking-k8s/v2.1.3/files/controller-installation/recommended-inline-policy.json

# Use the policy reviewed for this account and the enabled controller features.
export REVIEWED_POLICY_FILE=controller-policy-reviewed.json
test -s "$REVIEWED_POLICY_FILE"
export CONTROLLER_POLICY_ARN="$(aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document "file://$REVIEWED_POLICY_FILE" \
  --query Policy.Arn --output text)"

# Prerequisite: this cluster's IAM OIDC provider already exists.
eksctl create iamserviceaccount \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace aws-application-networking-system \
  --name gateway-api-controller \
  --attach-policy-arn "$CONTROLLER_POLICY_ARN" \
  --approve
```

An existing service account needs an intentional ownership/role migration; the example does not overwrite it automatically.

### Install the Released Controller

```bash
curl --fail --location --output gateway-api-v1.5.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.0/standard-install.yaml
# Inspect changes first if any Gateway API controller is already installed.
kubectl apply --server-side -f gateway-api-v1.5.0.yaml

helm pull oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart \
  --version v2.1.3
helm show crds ./aws-gateway-controller-chart-v2.1.3.tgz > lattice-crds.yaml
kubectl apply --server-side -f lattice-crds.yaml

helm install gateway-api-controller ./aws-gateway-controller-chart-v2.1.3.tgz \
  --namespace aws-application-networking-system --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=gateway-api-controller \
  --set-string awsRegion="$AWS_REGION" \
  --set-string awsAccountId="$AWS_ACCOUNT_ID" \
  --set-string clusterVpcId="$VPC_ID" \
  --set-string clusterName="$CLUSTER_NAME" \
  --wait --timeout 5m

kubectl -n aws-application-networking-system get pods
kubectl -n aws-application-networking-system logs \
  -l control-plane=gateway-api-controller -c manager --tail=100
```

For an existing Helm release, use a reviewed `helm upgrade` plan with its saved values. Helm does not automatically upgrade CRDs in `crds/`; review their changes separately. Do not remove shared Gateway API CRDs or admission policies to make an upgrade pass.

For manifest-based delivery, render this **same chart** with `helm template --include-crds`, using the same values and service-account choice, then review and apply the resulting manifest. This preserves the released RBAC, EndpointSlice watches, leader-election permissions, and webhook configuration. Do not use the obsolete hand-written v1.0 deployment. The chart generates webhook certificates unless supplied explicitly or managed through its cert-manager option; keep the webhook Secret and CA bundle consistent during upgrades instead of independently regenerating one.

### Create the Service Network

Choose **CLI or CloudFormation**, not both for the same network. The CLI example creates an `AWS_IAM` network. Until an applicable Allow policy is installed and propagated, requests are denied.

Save the following as `api-auth-policy.json`, replacing the account and caller role. The network policy deliberately permits only this demo's `/api` endpoint and subpaths. A production network needs a reviewed policy covering its intended services and callers.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/api",
            "/api/*"
          ]
        }
      }
    }
  ]
}
```

```bash
aws vpc-lattice create-service-network --name "$NETWORK_NAME" \
  --auth-type AWS_IAM > service-network.json
export SERVICE_NETWORK_ID="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["id"])')"
export SERVICE_NETWORK_ARN="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["arn"])')"

aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ID" \
  --vpc-identifier "$VPC_ID" --security-group-ids "$ASSOCIATION_SG_ID"

# Save the reviewed policy below as api-auth-policy.json, then compact it.
python3 -c 'import json; print(json.dumps(json.load(open("api-auth-policy.json")),separators=(",",":")))' \
  > api-auth-policy.compact.json
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_NETWORK_ID" \
  --policy file://api-auth-policy.compact.json
aws vpc-lattice get-service-network --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
```

Verify that the association is `ACTIVE`, the network still has `authType: AWS_IAM`, and `get-auth-policy` returns the intended policy before exposing a route. Policy propagation can take a few minutes.

The equivalent **network and association** CloudFormation template is:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: VPC Lattice service network and client VPC association
Parameters:
  NetworkName:
    Type: String
    Default: my-network
    MinLength: 3
    MaxLength: 63
    AllowedPattern: '^[a-z0-9]+(-[a-z0-9]+)*$'
    Description: Must match the Kubernetes Gateway name
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC containing the intended clients
  AssociationSecurityGroupIds:
    Type: List<AWS::EC2::SecurityGroup::Id>
    Description: Existing security groups allowing approved clients on listener ports
Resources:
  ServiceNetwork:
    Type: AWS::VpcLattice::ServiceNetwork
    Properties:
      Name: {Ref: NetworkName}
      AuthType: AWS_IAM
  ClientAssociation:
    Type: AWS::VpcLattice::ServiceNetworkVpcAssociation
    Properties:
      ServiceNetworkIdentifier: {Ref: ServiceNetwork}
      VpcIdentifier: {Ref: VpcId}
      SecurityGroupIds: {Ref: AssociationSecurityGroupIds}
Outputs:
  ServiceNetworkArn:
    Description: ARN used for authorization and sharing
    Value: {Fn::GetAtt: [ServiceNetwork, Arn]}
  ServiceNetworkId:
    Description: ID used with VPC Lattice API operations
    Value: {Fn::GetAtt: [ServiceNetwork, Id]}
```

This template does not attach an auth policy. Add an auth-policy resource in the same ownership model, or apply the reviewed network policy explicitly before testing requests. Obtain the network ID/ARN from stack outputs. Validate the template and inspect a change set before deployment; the example does not create the VPC or its security groups.

### Gateway and Application

Save and apply this as `gateway.yaml`. The Gateway name must match `my-network` created above.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lattice-demo
---
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-network
  namespace: lattice-demo
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: unused
```

`certificateRefs: [{name: unused}]` follows this controller's documented configuration: it satisfies the Gateway API TLS configuration but this controller does not read a Kubernetes TLS Secret there. With no custom hostname, Lattice supplies a certificate for its generated domain. This is **controller-specific**, not a portable certificate-management recipe.

Save the following as `stable.yaml`. It configures NGINX to actually listen on 8080 and serve `/health`; declaring `containerPort` alone would not do either.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-stable
  namespace: lattice-demo
data:
  nginx.conf: |
    worker_processes 1;
    pid /tmp/nginx.pid;
    error_log stderr notice;
    events { worker_connections 1024; }
    http {
        access_log /dev/stdout;
        default_type application/json;
        client_body_temp_path /tmp/client_temp;
        proxy_temp_path /tmp/proxy_temp;
        fastcgi_temp_path /tmp/fastcgi_temp;
        uwsgi_temp_path /tmp/uwsgi_temp;
        scgi_temp_path /tmp/scgi_temp;
        server {
            listen 8080;
            location = /health { return 200 '{"status":"ok"}\n'; }
            location = /api { return 200 '{"version":"stable"}\n'; }
            location /api/ { return 200 '{"version":"stable"}\n'; }
            location / { return 404 '{"error":"not found"}\n'; }
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  replicas: 2
  selector:
    matchLabels: &id001
      app: lattice-demo
      version: stable
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: nginx:1.30.4-alpine@sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c
        command:
        - nginx
        args:
        - -c
        - /etc/lattice/nginx.conf
        - -g
        - daemon off;
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
          periodSeconds: 5
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 250m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /etc/lattice
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: service-stable
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  selector:
    app: lattice-demo
    version: stable
  ports:
  - name: http
    port: 8080
    targetPort: http
```

Create `canary.yaml` from the same three objects, changing every `service-stable` name to `service-canary`, both selector/template `version: stable` labels to `version: canary`, and the JSON response value `"stable"` to `"canary"`. Keep `app: lattice-demo`, the port, and the health endpoint unchanged. Apply both files in `lattice-demo`. The pinned image has Linux AMD64 and ARM64 variants. Resource requests and replica counts are demonstration settings, not measured production sizing.

Save and apply the following `TargetGroupPolicy`; create an equivalent `canary-health` policy targeting `service-canary`.

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: TargetGroupPolicy
metadata:
  name: stable-health
  namespace: lattice-demo
spec:
  targetRef:
    group: ''
    kind: Service
    name: service-stable
  protocol: HTTP
  protocolVersion: HTTP1
  healthCheck:
    enabled: true
    protocol: HTTP
    protocolVersion: HTTP1
    port: 8080
    path: /health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThresholdCount: 2
    unhealthyThresholdCount: 2
    statusMatch: '200'
```

The CRD uses `intervalSeconds`, `timeoutSeconds`, and `statusMatch`. The AWS CLI uses different field names, shown later. Changing the protocol/version can replace a target group; deleting the policy reverts its settings, including the default HTTP/HTTP1 behavior.

## Service Management

### Create a Service Through HTTPRoute

Save this as `api-route.yaml`. Also save the IAMAuthPolicy below as `api-iam.yaml`. Apply the application and health policies, then the route and auth policy. Keep the network-level `AWS_IAM` policy active while reconciliation creates and secures the route's service.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: api-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/MyAppRole"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/api","/api/*"]}}}]}'
```

`spec.policy` is a JSON **string**. This CRD enables `AWS_IAM` on the target service; an auth-type annotation or ConfigMap containing a policy does not replace it. A policy targeting `Gateway` would instead manage the network's policy, so it must not compete with the externally managed network policy in this example.

Inspect `Accepted` / `ResolvedRefs` and policy status, the relevant AWS resource state, and backend readiness. A successful `kubectl apply` is not proof that cloud reconciliation or log delivery succeeded.

```bash
kubectl -n lattice-demo get gateway my-network -o yaml
kubectl -n lattice-demo get httproute api -o yaml
kubectl -n lattice-demo get iamauthpolicy api-caller -o yaml
kubectl -n lattice-demo get endpointslices \
  -l kubernetes.io/service-name=service-stable
kubectl -n lattice-demo rollout status deployment/service-stable --timeout=120s
kubectl -n lattice-demo rollout status deployment/service-canary --timeout=120s

export SERVICE_DNS="$(kubectl -n lattice-demo get httproute api \
  -o jsonpath='{.metadata.annotations.application-networking\.k8s\.aws/lattice-assigned-domain-name}')"
test -n "$SERVICE_DNS"
# A caller inside the associated VPC, with MyAppRole credentials, runs:
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

Set up the signed client in the next section before running the last command. Run it from an authorized network location with **caller-role** credentials. Your workstation needs an appropriate network path as well as AWS credentials.

### Signed HTTPS Client

Save this as `lattice_get.py`. It uses the default AWS credential provider chain, freezes the credentials for each request, signs for **`vpc-lattice-svcs`**, and sets **`UNSIGNED-PAYLOAD`** as required by VPC Lattice. It validates TLS, does not follow redirects with a stale signature, and does not automatically retry requests.

```python
import argparse
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import BotoCoreError
from botocore.session import Session


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def signed_request(url: str, region: str, credentials) -> Request:
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username
            or parts.password or parts.fragment):
        raise ValueError("Use an HTTPS URL without user info or a fragment")
    request = AWSRequest(method="GET", url=url, headers={
        "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
    })
    request.context["payload_signing_enabled"] = False
    SigV4Auth(credentials, "vpc-lattice-svcs", region).add_auth(request)
    return Request(url, method="GET", headers=dict(request.headers.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        provider = Session().get_credentials()
        if provider is None:
            raise ValueError("No AWS credentials available")
        request = signed_request(args.url, args.region, provider.get_frozen_credentials())
        opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(request, timeout=10) as response:
            print(response.status)
            print(response.read(1048576).decode("utf-8", errors="replace"))
        return 0
    except HTTPError as exc:
        print(f"HTTP {exc.code}; check the policy and access logs", file=sys.stderr)
    except (URLError, BotoCoreError, ValueError) as exc:
        print(f"Request failed: {type(exc).__name__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

```bash
python3.12 -m venv lattice-client
lattice-client/bin/python -m pip install 'botocore==1.43.93'
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

This GET-only example was checked with Python 3.12 and botocore 1.43.93. Workloads should use their configured Pod Identity or IRSA credentials. Do not copy static credentials or signed headers into manifests, logs, or support tickets. SigV4A is also supported by VPC Lattice; this example uses regional SigV4.

### Direct AWS API Management

The following is an **alternative** for independently managed resources. Use a reachable, stable backend IP serving HTTP on 8080 and `/health`; a temporary pod IP requires a controller to track replacements. Do not manually change an HTTPRoute-owned service and expect the controller to retain the change.

```bash
# Separate API-managed example; do not use for controller-managed resources.
export TARGET_IP=10.0.1.25
export TARGET_GROUP_ID="$(aws vpc-lattice create-target-group \
  --name api-manual --type IP \
  --config "{\"port\":8080,\"protocol\":\"HTTP\",\"protocolVersion\":\"HTTP1\",\"vpcIdentifier\":\"${VPC_ID}\"}" \
  --query id --output text)"
aws vpc-lattice register-targets --target-group-identifier "$TARGET_GROUP_ID" \
  --targets "id=$TARGET_IP,port=8080"
export SERVICE_ID="$(aws vpc-lattice create-service \
  --name api-manual --auth-type AWS_IAM --query id --output text)"
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_ID" \
  --policy file://api-auth-policy.compact.json
export LISTENER_ID="$(aws vpc-lattice create-listener \
  --service-identifier "$SERVICE_ID" --name https --protocol HTTPS --port 443 \
  --default-action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TARGET_GROUP_ID}\",\"weight\":1}]}}" \
  --query id --output text)"
aws vpc-lattice create-service-network-service-association \
  --service-identifier "$SERVICE_ID" --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID" --query dnsEntry
```

Wait for healthy targets and active associations before calling the discovered HTTPS domain. This example uses an AWS-managed certificate for the generated domain, not a custom domain.

### Updating and Deleting Services

For Kubernetes-owned resources, change the Route, backend workload, or policy manifest and verify reconciliation. For API-owned resources, use the corresponding update API and check its resulting state. Capture resource IDs from responses rather than selecting the first service in the account.

Before removal, identify all consumers, network associations, listeners/rules, target-group references, and ownership. Remove the specific route/service associations and service resources in dependency order, then unused target groups. A shared Gateway/network can affect other namespaces or accounts. Retain the controller until finalizers and cloud cleanup complete; do not use blanket deletes.

**Deleting IAMAuthPolicy disables IAM authentication on its target (`NONE`) before detaching the policy.** It is not a way to deny access or safely roll back authorization. Keep a restrictive policy while removing a service, and verify the remaining network/service controls.

## Routing and Traffic Management

### Path and Header Matching

The route above matches `/api` and its path subtree. To add an explicit header-based canary rule, replace the **same** HTTPRoute with:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
      headers:
      - name: x-version
        value: canary
    backendRefs:
    - name: service-canary
      port: 8080
      weight: 1
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

The controller documents case-insensitive path matching, one method match per rule, up to five header matches, and no query-parameter matching. Do not assume that every Gateway API filter or match is implemented. A separate HTTPRoute creates another Lattice service/domain, rather than automatically adding a rule to the first service.

### Weighted Routing

`backendRefs.weight: 90` and `10` are native Gateway API configuration; no weighted-routing annotation is needed. They express a relative distribution, not an exact result for ten requests. Verify both versions' endpoints, health, errors, and latency over an appropriate sample before increasing the canary weight.

For independently managed AWS resources:

```bash
# TG_STABLE and TG_CANARY are existing target groups managed by this API workflow.
aws vpc-lattice create-rule --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID" --name api-canary --priority 10 \
  --match '{"httpMatch":{"pathMatch":{"match":{"prefix":"/api"},"caseSensitive":false}}}' \
  --action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TG_STABLE}\",\"weight\":90},{\"targetGroupIdentifier\":\"${TG_CANARY}\",\"weight\":10}]}}"
```

The CLI prefix match is a lexical prefix; review boundary behavior separately from Kubernetes `PathPrefix` semantics. Routing matches are not an authorization boundary. Do not use a path-routing test as proof that an IAM policy covers all normalized or encoded path variants.

### Health Checks

The Kubernetes example uses `TargetGroupPolicy`. The equivalent API update is:

```bash
aws vpc-lattice update-target-group --target-group-identifier "$TARGET_GROUP_ID" \
  --health-check '{"enabled":true,"protocol":"HTTP","protocolVersion":"HTTP1","port":8080,"path":"/health","healthCheckIntervalSeconds":30,"healthCheckTimeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}'
```

Health checks assess readiness according to thresholds; they do not guarantee availability or zero downtime. HTTP1 target groups enable them by default, while HTTP2 requires explicit consideration. gRPC targets use HTTP1/HTTP2 health checks, and Lambda/ALB target types have different health-check behavior. Check the current target-type documentation instead of applying the pod example to every target.

## Security and Authentication

### Auth Policies and Caller Permissions

`put-auth-policy` / `get-auth-policy` manage invocation authorization. `put-resource-policy` is a different management/sharing API. Use the **`vpc-lattice-svcs:Invoke`** action for callers.

When both network and service use `AWS_IAM`, the caller's identity policy and **both** applicable auth policies must permit access. An explicit Deny wins. `NONE` on one resource does not cancel another resource's IAM requirement. Direct traffic to a Kubernetes ClusterIP/Pod IP bypasses Lattice auth; protect those paths with appropriate network and application controls.

`StringEquals` does not interpret `/api/*` as a wildcard. The example uses `StringLike` and includes `/api` as well as `/api/*`. IAM condition matching and application path normalization can differ from controller routing. For administrative functionality, prefer a dedicated service restricted to administrative roles and retain application authorization; do not add a broad general Allow and assume a path wildcard protects every alias.

### Cross-Account Access

RAM sharing allows association with the shared entity; it does not itself grant application invocation. The network/service auth policies, caller permissions, association security groups, and network path must still allow the request.

```bash
# Owner account: choose a verified account ID or the actual Organizations ARN.
export CONSUMER_ACCOUNT_ID=111122223333
aws ram create-resource-share --name lattice-network-share \
  --resource-arns "$SERVICE_NETWORK_ARN" --principals "$CONSUMER_ACCOUNT_ID"

# Consumer account: inspect invitations only when the sharing mode requires one.
aws ram get-resource-share-invitations
# After verifying the owner, resources, and intended permissions:
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "$VERIFIED_INVITATION_ARN"

# Run with consumer credentials and that account's VPC/security group values.
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ARN" \
  --vpc-identifier "$CONSUMER_VPC_ID" \
  --security-group-ids "$CONSUMER_ASSOCIATION_SG_ID"
```

With Organizations sharing enabled, consumers inside the organization receive access without an invitation. Other supported sharing arrangements require invitation acceptance. To share with an organization or OU, use its **actual ARN from Organizations**, including the management-account identifier, rather than composing one from a member-account ID.

Owners can share services, networks, and resource configurations, not individual IAM roles as RAM consumers. Stopping a share prevents new associations but **does not remove existing associations**. Review them explicitly when revoking access.

### TLS and Custom Domains

The sample Gateway exposes only HTTPS. For a custom hostname, create the service with that hostname, obtain a matching ACM certificate, and configure DNS to the actual assigned domain. Only one custom domain is supported per service and it cannot be changed after service creation.

For the controller, set the HTTPRoute's `spec.hostnames` and the Gateway listener's `tls.options["application-networking.k8s.aws/certificate-arn"]`, or use its documented ACM discovery. Do not put private keys in an annotation. ExternalDNS automation additionally needs its controller, permissions, and the DNSEndpoint CRD; setting a hostname alone is not proof that DNS records exist.

```bash
# For an API-managed service created with the required custom domain name:
aws vpc-lattice update-service --service-identifier "$SERVICE_ID" \
  --certificate-arn "$ACM_CERTIFICATE_ARN"
# Create an HTTPS listener separately if the service does not already have one.
# create-listener uses --protocol HTTPS; there is no --tls mode=STRICT option.
```

Client-facing HTTPS and backend TLS are separate. A backend `TargetGroupPolicy` with `protocol: HTTPS` also needs a backend that actually speaks TLS and a compatible HTTPS health check. VPC Lattice **does not validate backend certificates**; this encrypts the connection without authenticating the backend's certificate identity. Use the separate TLSRoute/TLS passthrough model when that is the intended design, and review its feature limitations.

## Monitoring and Logging

### CloudWatch Metrics, Dashboard, and Alarm

Service metrics use the **`AWS/VpcLattice`** namespace:

| Metric | Meaning / statistic |
|---|---|
| `TotalRequestCount` | Request count; `Sum` |
| `HTTPCode_4XX_Count` | 4xx responses; `Sum` |
| `HTTPCode_5XX_Count` | 5xx responses; `Sum` |
| `RequestTime` | Request duration in **milliseconds**; average or a suitable percentile |

Service metrics use the `Service` dimension, optionally with `AvailabilityZone`; target-group metrics use `TargetGroup`. A name such as `ServiceName=my-service` does not identify these metrics. Discover the actual dimension values/set:

```bash
aws cloudwatch list-metrics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions Name=Service > metrics.json
python3 - <<'PY'
import json
for metric in json.load(open("metrics.json"))["Metrics"]:
    print(json.dumps(metric["Dimensions"]))
PY
```

After traffic has produced metrics, select the intended service's **service-wide** dimension array and save it as `service-dimensions.json`. Do not arbitrarily select the first result or mix an AZ metric with an aggregate. Verify the identifier against the service being observed. Build `dashboard.json` with:

```python
import json
import os

dimensions = json.load(open("service-dimensions.json"))
if {d["Name"] for d in dimensions} != {"Service"}:
    raise ValueError("Select the service-wide metric, without AvailabilityZone")
pairs = [item for d in dimensions for item in (d["Name"], d["Value"])]
dashboard = {"widgets": [{
    "type": "metric", "width": 12, "height": 6,
    "properties": {
        "title": "VPC Lattice requests and errors",
        "region": os.environ["AWS_REGION"], "period": 60, "stat": "Sum",
        "metrics": [["AWS/VpcLattice", name, *pairs] for name in
                    ("TotalRequestCount", "HTTPCode_4XX_Count", "HTTPCode_5XX_Count")],
    },
}]}
with open("dashboard.json", "w") as output:
    json.dump(dashboard, output)
```

```bash
aws cloudwatch put-dashboard --dashboard-name VPCLattice \
  --dashboard-body file://dashboard.json
aws cloudwatch put-metric-alarm --alarm-name LatticeApi5xx \
  --namespace AWS/VpcLattice --metric-name HTTPCode_5XX_Count \
  --dimensions file://service-dimensions.json \
  --statistic Sum --period 60 --evaluation-periods 3 --datapoints-to-alarm 2 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --treat-missing-data missing
```

The alarm means **more than five 5xx responses per minute in two of three periods**, not a 5% error rate. Configure reviewed alarm actions separately if notifications are required. The missing-data choice is explicit: metrics are published after traffic begins, and NoData must not be silently treated as proof of health. Dashboard and alarm settings are examples, not workload-specific SLOs.

### Access Logging

For CloudWatch Logs, use an existing destination or create a dedicated log group with a retention policy:

```bash
export LOG_GROUP=/aws/vendedlogs/vpc-lattice/api
aws logs create-log-group --log-group-name "$LOG_GROUP"
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
export LOG_DESTINATION_ARN="arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"

# API-managed service only; for an HTTPRoute use AccessLogPolicy below instead.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_DESTINATION_ARN"
```

The setup principal also needs the documented log-delivery permissions. AWS can create/update the log resource policy when the setup principal has the necessary permissions; otherwise preconfigure it. Verify the `delivery.logs.amazonaws.com` permissions and source-account/source-ARN conditions.

For the Kubernetes-managed route, use this **instead of** a competing CLI-created subscription:

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: AccessLogPolicy
metadata:
  name: api-logs
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  destinationArn: arn:aws:logs:us-west-2:123456789012:log-group:/aws/vendedlogs/vpc-lattice/api:*
```

Replace the ARN and confirm policy status plus actual delivered events. A policy can target a Gateway for network logs or a Route for service logs. There can be one destination of each supported destination type per target.

For S3, use a reviewed destination bucket with Block Public Access, encryption, retention/lifecycle rules, and appropriate delivery permissions:

```bash
# Existing reviewed destination bucket; no policy is overwritten by this snippet.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_BUCKET_ARN"
```

S3 delivery requires the documented `s3:GetBucketAcl` and `s3:PutObject` permissions for `delivery.logs.amazonaws.com`, the delivery prefix, `aws:SourceAccount`, and `aws:SourceArn` conditions. Existing policies must be merged, not overwritten. SSE-KMS requires a supported customer-managed key and its delivery key policy. `--destination-name` is not an access-log-subscription parameter.

### Log Analysis and Tracing

HTTP service access logs contain fields such as `sourceIpPort`, `requestMethod`, `requestPath`, `responseCode`, `durationMS`, `callerPrincipal`, and `authDeniedReason`. Resource/TCP logs have a different schema.

```bash
END_TIME="$(python3 -c 'import time; print(int(time.time()))')"
START_TIME="$((END_TIME - 3600))"
QUERY_ID="$(aws logs start-query --log-group-name "$LOG_GROUP" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --query-string 'fields @timestamp, sourceIpPort, requestMethod, requestPath, responseCode, durationMS, callerPrincipal, authDeniedReason | filter responseCode >= 400 | sort @timestamp desc | limit 100' \
  --query queryId --output text)"
aws logs get-query-results --query-id "$QUERY_ID"
# Repeat get-query-results until Complete; Failed/Cancelled/Timeout are errors.
```

VPC Lattice has no `update-service --tracing-config` option or controller annotation that automatically instruments applications for X-Ray. Instrument the applications with OpenTelemetry/ADOT or the appropriate tracing SDK, propagate trace context, and configure export/sampling. Correlate application traces with access logs and request IDs; a client-supplied request ID is not an authenticated identity.

## Best Practices

- **Design and ownership:** Use clear network/service naming and environment boundaries. Account for same-named Gateways across namespaces, shared network consumers, quotas, and the ownership of each policy and association.
- **Deployment:** Keep stable and canary backends independently selectable. Check endpoints, target health, and authorization before shifting weights. Record rollback criteria and preserve the last known configuration.
- **Performance:** Use bounded timeouts and appropriate connection reuse. Make health endpoints lightweight and meaningful. Cache or batch only where application semantics permit it. Private Lattice services do not become CDN origins merely by enabling caching.
- **Security:** Separate management and caller roles; keep credentials out of manifests. Test permitted and denied roles, root paths and subpaths, direct-backend access, and TLS behavior. Do not delete an IAM policy CRD to deny traffic.
- **Observability:** Monitor request count, error count/rate, latency, target health, and missing telemetry separately. Retain access logs for the required period and instrument application traces explicitly.
- **Cost:** Review current regional service/resource, request, data-processing, endpoint, and logging charges for the chosen model. Use tags, remove only confirmed unused resources, and size backend autoscaling separately from the managed Lattice data plane.

## Troubleshooting

Use identifiers from the controller annotations/status and AWS inventory. Do not assume the direct-API sample's `$SERVICE_ID` is the Kubernetes route's service.

```bash
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-service-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_ID"
aws vpc-lattice list-listeners --service-identifier "$SERVICE_ID"
aws vpc-lattice list-rules --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID"
aws vpc-lattice get-target-group --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
```

| Symptom | Check |
|---|---|
| DNS/connectivity failure | Actual assigned DNS, client VPC association or endpoint path, association state, SGs, NACLs, pod reachability |
| 403/auth failure | Caller role, credential expiry and signing region/service, `UNSIGNED-PAYLOAD`, both auth layers, propagation, denied-reason log fields |
| Wrong route or version | Route conditions, listener/rule priority and matches, target group membership, weights, distinct Route domains |
| Unhealthy targets | Actual listening port, `/health`, HTTP vs HTTPS, readiness, SGs, target type and health-check thresholds |
| No logs/metrics | Destination permissions and delivery state, correct metric dimensions, initial traffic, retention, query status |
| Controller reconciliation failure | `manager` logs, IAM role, EndpointSlices, CRD version compatibility, webhook and leader-election status |

Use a bounded metric interval without relying on GNU-only `date -d`:

```bash
export METRIC_END="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
export METRIC_START="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())')"
aws cloudwatch get-metric-statistics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions file://service-dimensions.json \
  --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Sum
```

For an AWS service incident, consult AWS Health and relevant account events. Account-specific API access and support operations depend on the applicable plan and endpoints. A support case should include reviewed resource IDs, time range, failure symptoms, and redacted logs. Select current service/category/severity options for the account; do not paste a hard-coded `urgent` case-creation command.

## References

- [VPC Lattice overview](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [Service network associations](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [Controller v2.1.3 installation](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/deploy.md)
- [Controller v2.1 upgrade requirements](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/upgrading-v2-0-x-to-v2-1-y.md)
- [Controller API reference](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs/api-types)
- [Controller HTTPS and backend TLS](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/https.md)
- [VPC Lattice auth policies](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [Signing requests](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [Sharing entities](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html)
- [CloudWatch metrics](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html)
- [Access logs](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [CloudWatch Logs delivery permissions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html)
- [S3 delivery permissions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-S3.html)

## Quiz

Test your understanding with the [VPC Lattice quiz](../quizzes/networking/02-vpc-lattice-quiz.md).
