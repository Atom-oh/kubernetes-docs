# VPC Lattice Quiz

Review the guide and explain the prerequisites, not just the YAML.

## 1. What is the main purpose of Amazon VPC Lattice?

- A) Internet DNS-based global load balancing
- B) Private application and resource connectivity across VPCs and accounts
- C) Cross-region database replication
- D) Replacing all IP routing

<details>
<summary>Show answer</summary>

B. Lattice connects services and resource configurations. HTTP service routing and the resource-access model are distinct; association, network controls, and authorization still apply.

</details>

## 2. What does a service network represent?

- A) A physical network device
- B) A logical grouping with service/resource and client-network associations
- C) A subnet route table
- D) One shared HTTP listener for every service

<details>
<summary>Show answer</summary>

B. Listeners and rules belong to individual services. An association enables a path subject to security groups and applicable policies; it does not unconditionally authorize every request.

</details>

## 3. Which statement about App Mesh and Lattice is correct?

- A) Lattice requires an Envoy sidecar per pod
- B) App Mesh uses Envoy proxies, while Lattice provides a managed data plane without requiring application sidecars
- C) All other meshes require sidecars
- D) App Mesh support has already ended on the review date

<details>
<summary>Show answer</summary>

B. AWS App Mesh support ends on 2026-09-30, which is still upcoming on 2026-09-11. Plan migration rather than a new App Mesh deployment. Sidecar requirements differ among other mesh modes.

</details>

## 4. How does AWS Gateway API Controller map resources?

- A) Every Kubernetes Service creates one service network
- B) Gateway selects a network by name; each HTTPRoute creates its own Lattice service/domain
- C) Gateway always creates one ingress IP shared by all Routes
- D) The controller uses only the Ingress API

<details>
<summary>Show answer</summary>

B. GatewayClass selects the controller. A Gateway refers to an existing service network by its name without the namespace; backend Services/endpoints supply target groups. A Gateway alone does not create the network.

</details>

## 5. How should a client obtain the assigned Lattice service DNS name?

- A) Append the region to the Kubernetes Service name
- B) Put the service-network ID into a guessed hostname
- C) Read get-service dnsEntry or the Route's lattice-assigned-domain-name annotation
- D) Reuse Gateway.status.addresses as the address of every Route

<details>
<summary>Show answer</summary>

C. Each Route has its own service/domain. Use the actual returned value; recreating a service can change its assigned name. Custom domains require their own DNS and certificate setup.

</details>

## 6. Which statement about authentication is correct?

- A) NONE on the service disables every network policy
- B) AWS_IAM accepts an unsigned curl request if the client has an IAM role
- C) AWS_IAM uses supported signed requests; every applicable IAM authorization layer must allow access
- D) RAM sharing grants Invoke automatically

<details>
<summary>Show answer</summary>

C. VPC Lattice supports SigV4 and SigV4A. Use vpc-lattice-svcs and UNSIGNED-PAYLOAD when signing. Caller identity permissions and applicable network/service auth policies must allow access; explicit Deny wins. NONE affects only its own layer.

</details>

## 7. Which is not a named Lattice service target-group type?

- A) INSTANCE
- B) IP
- C) LAMBDA
- D) RDS

<details>
<summary>Show answer</summary>

D. Service target-group types include INSTANCE, IP, LAMBDA, and ALB. This does not mean Lattice cannot connect an RDS database: resource configurations and resource gateways provide a separate TCP resource-access model. Service auth policies do not govern that resource traffic.

</details>

## 8. What does a backendRefs weight ratio of 90:10 mean?

- A) Exactly one of every ten consecutive requests reaches canary
- B) Relative traffic distribution between the two backends
- C) A pod replica-count requirement
- D) An annotation unsupported by Gateway API

<details>
<summary>Show answer</summary>

B. Native backendRefs.weight configures relative distribution; a small request sample need not match exactly. Both backends must exist and be healthy. Observe errors and latency before increasing the canary share.

</details>

## 9. Explain cross-account sharing of a service network.

<details>
<summary>Show answer</summary>

The owner creates a RAM share for the network ARN and an intended account, organization, or OU. Consumers inside an organization with sharing enabled do not need invitations; other applicable arrangements require acceptance. The consumer associates its own VPC or creates an appropriate service-network endpoint. Sharing does not grant Invoke: caller policies, auth policies, network paths, and security groups must also permit access. Stopping a share leaves existing associations in place.

</details>

## 10. Write a Kubernetes health-check policy for the demo backend.

<details>
<summary>Show answer</summary>

Use TargetGroupPolicy in the same namespace as its target Service. The controller CRD uses intervalSeconds/timeoutSeconds/statusMatch, while the AWS API uses healthCheckIntervalSeconds/healthCheckTimeoutSeconds/matcher.

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

The backend must really listen on 8080 and return 200 at /health. Thresholds help determine readiness; they do not guarantee availability or zero downtime. Review target-type and protocol-specific behavior.

</details>

## 11. How do Transit Gateway and VPC Lattice differ?

<details>
<summary>Show answer</summary>

Transit Gateway routes IP traffic between networks. Lattice exposes services and resource configurations: HTTP service paths can use L7 routing, while TLS/TCP/resource capabilities have different features. They can be used together. A service-network VPC endpoint supports applicable clients arriving through transit/peering; a direct VPC association alone does not grant that transit access.

</details>

## 12. At which levels can an auth policy apply, and how do you restrict the demo API path?

<details>
<summary>Show answer</summary>

Auth policies apply to service networks and individual services configured with AWS_IAM. Both applicable layers and the caller's identity policy must allow the request. Use StringLike for wildcard matching and include the root path explicitly:

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

StringEquals would match /api/* literally. This policy concerns canonical paths; application normalization and controller path routing are separate behaviors. PutAuthPolicy, not PutResourcePolicy, manages invocation authorization.

</details>

## 13. Describe an IRSA installation of AWS Gateway API Controller v2.1.3.

<details>
<summary>Show answer</summary>

Verify the cluster's supported Kubernetes version, Gateway API compatibility, IAM OIDC provider, and network/webhook reachability. Review the release's recommended policy for the intended account/features; its broad upstream permissions are not a least-privilege guarantee. Use a dedicated controller service account and the released OCI chart:

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

The controller role manages resources; it is not the application caller role. Existing service accounts/releases require an ownership-aware upgrade. Helm does not automatically upgrade its CRDs. See the guide for the separate service-network/auth-policy setup.

</details>

## 14. Write an HTTPRoute for a 90:10 stable/canary split.

<details>
<summary>Show answer</summary>

Prerequisites: the guide's my-network HTTPS Gateway in lattice-demo, its existing service network and active auth policy, both backend Deployments/Services on 8080, and target-group health policies. Then apply:

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

Apply the guide's IAMAuthPolicy to this Route as well and inspect reconciliation. No weight annotation is needed. Use the Route's assigned domain and signed HTTPS requests; a successful apply does not prove the backends are healthy.

</details>

## 15. Allow only AdminRole and DevOpsRole to invoke a dedicated administrative service at /admin and its subpaths.

<details>
<summary>Show answer</summary>

Use the following as the complete service auth policy, with real account/role ARNs. Set that dedicated service to AWS_IAM and ensure the caller identity policy and the network auth policy also permit these roles and paths. The guide's API-only network policy would need a reviewed change for this separate administrative service.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
          "vpc-lattice-svcs:RequestPath": [
            "/admin",
            "/admin/*"
          ]
        }
      }
    }
  ]
}
```

For a controller-owned HTTPRoute named admin in lattice-demo, attach it using the real CRD:

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: admin-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: admin
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["arn:aws:iam::123456789012:role/AdminRole","arn:aws:iam::123456789012:role/DevOpsRole"]},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/admin","/admin/*"]}}}]}'
```

There is no broad AllowGeneralAccess statement. In this policy, other roles and paths have no Allow, and /admin is explicitly included rather than only /admin/*. Treat path normalization/encoding as an application security requirement; a dedicated role-restricted service and application authorization reduce dependence on path aliases. Direct backend access must also be protected. Deleting IAMAuthPolicy changes the target auth type to NONE and is not a deny or safe rollback mechanism.

</details>

Score: 13–15 indicates strong understanding of this chapter, 10–12 suggests reviewing missed topics, and 0–9 suggests rereading the guide. A quiz score does not establish production operating experience.

[Return to the guide](../../networking/02-vpc-lattice.md)
