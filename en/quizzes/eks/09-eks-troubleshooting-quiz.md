# Amazon EKS Troubleshooting Quiz

> **Last Updated**: September 12, 2026

This quiz tests your ability to diagnose and resolve various issues that may occur in Amazon EKS clusters.

## Quiz Overview

- Cluster creation and configuration issues
- Networking issues
- Node and pod issues
- Storage issues
- Security and access issues
- Performance and scalability issues

## Multiple Choice Questions

### 1. What is the most useful first response to an EKS control-plane creation failure?

- A. Only check whether the cluster name is unique
- B. Inspect the exact error/request and verify caller/service-role IAM, VPC/subnets and relevant quotas
- C. Immediately create another cluster in a different Region
- D. Select a larger worker instance type

<details>
<summary>Show Answer</summary>

**Answer: B. Inspect the exact error/request and verify caller/service-role IAM, VPC/subnets and relevant quotas**

Start from the failing request or CloudFormation event. IAM, networking, quota and name-conflict checks are useful hypotheses, not a statistical diagnosis before reading the error.

**What to verify**

| Area | Evidence |
| --- | --- |
| Caller | Correct account/Region/profile; required EKS actions, `iam:PassRole`, boundaries/session/SCP controls and service-linked-role permission where needed |
| Cluster service role | Exact role ARN, EKS trust and required service-role policies; distinct from the caller and worker-node role |
| Cluster subnets | Supported AZs, at least two different AZs and available addresses; node/Pod/LB capacity is a separate budget |
| Endpoint/dependencies | Intended private/public mode, DNS, routes, SG/NACL and required AWS service access |
| Quotas | Actual service/quota and current applied Region/account limit, including EC2 vCPU constraints when node creation is involved |
| Infrastructure owner | Original Terraform/CloudFormation/eksctl configuration, state and failed operation |

The current EKS requirement is at least **six IP addresses per selected cluster subnet**, with at least **16 recommended**, and subnets in at least two AZs. CIDR size alone does not prove that those addresses remain available. The former generic “minimum /28, recommended /24” wording also confused control-plane and workload sizing. A private setup can use required endpoints; NAT/general internet is not universally mandatory.

`AmazonEKSClusterPolicy` is for the cluster service role. Attaching it to a human user does not grant all creation/PassRole permissions or Kubernetes RBAC. Adding a cluster-ownership subnet tag is likewise not a universal creation fix.

**Read-only investigation**

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"; : "${CLUSTER_NAME:?}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch" >&2; exit 1
fi
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateCluster \
  --max-items 20 --output json
aws service-quotas list-service-quotas --service-code eks --region "$AWS_REGION"
: "${VPC_ID:?Set the VPC from the original request}"
aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,AZId:AvailabilityZoneId,AvailableIPs:AvailableIpAddressCount}'
# For an eksctl-owned creation attempt, inspect its existing stacks:
eksctl utils describe-stacks --cluster "$CLUSTER_NAME" --region "$AWS_REGION"
```

If a usable cluster already exists, inspect it with `describe-cluster`; if not, preserve the creation error rather than treating ResourceNotFound as a second root cause. For other CloudFormation owners, inspect the exact stack's events. `eksctl create cluster --verbose ...` and CLI debug mode still provision resources; they are not read-only diagnostics.

**Illustrative messages**

- A denied `eks:CreateCluster` call requires examining caller permissions; a service-role problem is a different permission path.
- The old example reporting insufficient capacity in `us-west-2a` illustrates an AZ/capacity response, not current regional availability.
- The old “Current limit is 5” message is preserved as a historical illustration; query the current applied quota before choosing an increase value.
- `UnsupportedAvailabilityZoneException` identifies unsupported EKS cluster AZs for the account, not merely missing EC2 instance-type offerings.

**Infrastructure configuration review**

Inspect and correct the original owner configuration. This Terraform excerpt illustrates explicit version/network intent and the status output; it is not a complete new-cluster module or a command to apply during diagnosis:

```hcl
# Excerpt of the original state-owned configuration, not a diagnostic apply.
# Preserve its other settings and role/policy dependencies.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.cluster_version
  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = var.cluster_security_group_ids
    endpoint_private_access = true
    endpoint_public_access  = false
  }
}

output "cluster_status" {
  value = aws_eks_cluster.main.status
}
```

Supply verified existing role/subnet/security-group inputs, preserve required role-policy dependencies and other settings, and review any private-endpoint access path. An output is evaluated from Terraform state; it is not guaranteed to appear or contain fresh failure details when creation fails. Use provider diagnostics and AWS request/stack evidence. No Terraform apply or cluster creation was run for this review.

After identifying the cause, review a targeted permission/network/quota correction and retry through the owner. A is a useful narrow check but insufficient by itself. C changes placement/data/networking and can add cost without fixing the cause. D changes workers, not the control-plane creation issue.

Sources: [EKS networking requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html), [EKS troubleshooting](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html), [Terraform EKS cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 2. What is the most effective first investigation of an EKS node in NotReady state?

- A. Immediately terminate the node
- B. Inspect node conditions/events, logs, resources and the actual network/identity path
- C. Restart the managed EKS API server yourself
- D. Delete every Pod in the cluster

<details>
<summary>Show Answer</summary>

**Answer: B. Inspect node conditions/events, logs, resources and the actual network/identity path**

Use the condition reason/time and actual node identity to investigate. Ready=False, missing heartbeats/Ready=Unknown, disk pressure and memory pressure are different evidence; none automatically identifies the root cause.

**Node and workload inventory**

The following read-only example selects the node by name/UID and its Pods by `spec.nodeName`, avoiding unreliable IP/grep matching:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,labels:.metadata.labels,providerID:.spec.providerID,taints:.spec.taints,unschedulable:.spec.unschedulable,nodeInfo:.status.nodeInfo,conditions:.status.conditions,capacity:.status.capacity,allocatable:.status.allocatable}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A --field-selector "involvedObject.uid=$NODE_UID" \
  --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" get pods -A --field-selector "spec.nodeName=$NODE_NAME" -o wide
```

Confirm the node ProviderID/account/Region and compute type before EC2 or host access. For managed groups, inspect their health and repair/update configuration:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,release:releaseVersion,nodeRole:nodeRole,repair:nodeRepairConfig,update:updateConfig}'
```

On an accessible standard Linux node, use the [source guide's remote-session procedure](../../eks/09-eks-troubleshooting.md) to inspect kubelet/containerd journals, bytes/inodes, memory and routing. A Docker daemon or `/var/log/syslog` may not exist on the actual image. Node DNS is not automatically the Pod's cluster DNS. Use the cluster CA for endpoint TLS; `curl -k` hides certificate problems.

Preserve evidence before pruning images, deleting journals or rebooting. `kubectl top` requires a functioning metrics path and may fail on an unhealthy node. Inspect configured certificate paths without exposing private keys. `kubeadm alpha certs renew all` is neither a current generic command nor an EKS node repair procedure; `eksctl replace nodegroup` is not supported.

**Recovery versus automatic repair**

After determining the cause, coordinate node replacement/restart with capacity, PDBs, data and the node owner. Stop when a bounded drain fails; do not proceed to termination or immediately uncordon after an asynchronous reboot.

Automatic node repair is an actual EKS mechanism. `update_config.max_unavailable` controls version-update disruption; it does not enable repair, and `health_check { type = "EKS" }` is not an `aws_eks_node_group` block. The current provider exposes `node_repair_config`:

```hcl
# Fragment of a reviewed EKS-optimized-AMI managed node group.
resource "aws_eks_node_group" "self_healing" {
  cluster_name    = var.cluster_name
  node_group_name = var.node_group_name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.node_kubernetes_version
  ami_type        = var.ami_type
  release_version = var.ami_release
  instance_types  = var.instance_types

  scaling_config {
    desired_size = 3
    min_size     = 3
    max_size     = 6
  }
  update_config {
    max_unavailable = 1
  }
  node_repair_config {
    enabled                           = true
    max_parallel_nodes_repaired_count = 1
  }
}
```

This is a configuration fragment, not a tested production module. Supply compatible reviewed Kubernetes/AMI/instance inputs and existing ownership. Coordinate desired capacity with an autoscaler if one manages it. Node-group tags are not automatically proof that the underlying ASG has the required CA discovery tags.

Repair defaults/thresholds differ by compute owner. Auto Mode enables its repair behavior by default; managed groups require enablement, and Karpenter has its own feature requirements. Node monitoring can report issues without repair being enabled. The current default repair table does **not** automatically repair MemoryPressure or DiskPressure. Fleet-health thresholds, parallelism and ARC controls can limit actions; do not promise unconditional replacement or PDB protection.

**Monitoring example**

`AWS/EKS` with metric name `NodeNotReady` is not a built-in metric this recipe can assume exists. An existing kube-state-metrics/Prometheus Operator installation can instead evaluate actual node conditions:

```yaml
# Existing single-cluster Prometheus Operator/KSM installation required.
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-readiness-example
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
    - name: node-readiness-example
      rules:
        - alert: NodeNotReady
          expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="Ready",status="true"}) == 0
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Node {{ $labels.node }} is not Ready"
            description: "Investigate node conditions, reachability and workload impact before recovery."
```

Set the namespace/release/job selectors to the actual installation. The ten-minute wait is illustrative. Missing scrapes/condition data require separate telemetry-health monitoring and must not be treated as healthy nodes. This alert does not wire notifications or perform recovery; verify those independently. Creating an undefined `node-recovery.zip` Lambda would not establish safe automatic remediation.

C is not a customer-operated restart path for the managed EKS API server, and API connectivity can indeed cause node readiness problems. A and D widen disruption and can destroy evidence without resolving the underlying cause.

Sources: [EKS node repair](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html), [Terraform managed-node resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group), [node metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md).

</details>

### 3. Which approach properly investigates ImagePullBackOff on EKS?

- A. Increase every container memory limit
- B. Read the pull error, verify the image/platform and actual pull identity/network path
- C. Force a new image download without checking the error
- D. Delete all network policies

<details>
<summary>Show Answer</summary>

**Answer: B. Read the pull error, verify the image/platform and actual pull identity/network path**

ImagePullBackOff is a retry/backoff state, not proof of one “most likely” cause. Inspect all affected regular/init containers and the exact kubelet event:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
  node:.spec.nodeName,serviceAccount:.spec.serviceAccountName,
  imagePullSecrets:.spec.imagePullSecrets,
  containers:[.spec.containers[] | {name,image,imagePullPolicy,resources}],
  initContainers:[.spec.initContainers[]? | {name,image,resources}],
  phase:.status.phase,reason:.status.reason,message:.status.message,
  conditions:.status.conditions,containerStatuses:.status.containerStatuses,
  initContainerStatuses:.status.initContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
```

Distinguish missing repository/tag/digest, unsupported architecture, credentials/authorization, registry rate limits, node DNS/TLS/egress and local disk/runtime failures. A local Docker pull uses a different identity/path; it does not prove that the node can pull.

**ECR identity and networking**

EC2 nodes normally use the node pull-credential path; Fargate uses its Pod execution role. Application IRSA/Pod Identity is not the identity that downloads the image before the application starts. Verify repository policy and cross-account access as applicable. Creating a new IAM role without associating it with the relevant compute does not change image pulls.

Use explicit repository/account/Region and tag **or** digest rather than splitting an arbitrary image string with `cut`:

```bash
set -euo pipefail
: "${REGISTRY_REGION:?Set the image registry Region}"
: "${REGISTRY_ACCOUNT_ID:?Set its account ID}"
: "${REPOSITORY_NAME:?Set the exact repository path}"
: "${ECR_IMAGE_ID:?Set imageTag=... or imageDigest=sha256:...}"
aws ecr describe-images --region "$REGISTRY_REGION" \
  --registry-id "$REGISTRY_ACCOUNT_ID" --repository-name "$REPOSITORY_NAME" \
  --image-ids "$ECR_IMAGE_ID" \
  --query 'imageDetails[].{digest:imageDigest,tags:imageTags,pushedAt:imagePushedAt,mediaType:imageManifestMediaType}'
```

This checks image metadata using the operator's AWS credentials; it does not validate kubelet permissions. Private ECR access can require ECR API/DKR and S3 paths, endpoint policies/security groups and DNS. `ecr.dkr` is not an endpoint for arbitrary private registries. Normal Pod NetworkPolicy changes generally do not repair a node runtime's registry authentication.

**Permission example**

For a deliberately selected existing EC2 node role, these permissions illustrate one-repository pulls. `GetAuthorizationToken` has no repository resource scope, so its statement uses `*` with a Region condition; image reads are scoped to the repository:

```hcl
# Permission example for a reviewed existing EC2 node role.
# This does not create/associate a new role or create an image-pull Secret.
data "aws_iam_role" "node" {
  name = var.existing_node_role_name
}

resource "aws_iam_policy" "ecr_pull" {
  name = var.pull_policy_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:RequestedRegion" = var.registry_region }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = var.repository_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = data.aws_iam_role.node.name
  policy_arn = aws_iam_policy.ecr_pull.arn
}
```

Use the actual repository ARN/Region, and review existing grants/boundaries/SCPs and cross-account repository policy. Adding a narrow policy does not remove a broader existing policy. Fargate needs its own execution-role configuration; this EC2-role example does not create a Kubernetes Secret or configure a Fargate profile. No IAM change was executed during review.

**Image-pull Secrets**

For registries that need a Secret, use a protected self-contained Docker auth file and the [source guide's namespaced Secret/Pod-template procedure](../../eks/09-eks-troubleshooting.md). Do not print Secret data/tokens or pass passwords in diagnostic command lines. A desktop credential-helper reference is not sufficient auth data for kubelet.

An existing Pod's imagePullSecrets cannot generally be patched in place. Change the owning Deployment/StatefulSet template while preserving its current pull-secret list and perform a controlled rollout. Updating a ServiceAccount affects newly admitted Pods; avoid changing the default ServiceAccount for unrelated applications.

**Credential-renewal design**

Standard EKS ECR pulls do not require the former token-renewal CronJob. ECR authorization tokens are valid for 12 hours. If a non-native consumer truly needs a manually managed ECR pull Secret, use its supported credential mechanism or an explicitly engineered renewal workflow.

The old schedule `*/6 * * * *` means **every six minutes**, not six hours; a six-hour example is `0 */6 * * *`, with the controller timezone or an explicit supported `.spec.timeZone`. Scheduling alone is not a working renewer: it needs a reviewed image containing the required tools, AWS identity, scoped Kubernetes permissions, the exact target namespace, overlap/failure handling and tested rotation. Keep it suspended until those are validated. Update a pre-created named Secret rather than deleting it and leaving a credential gap. A stock AWS CLI image does not imply kubectl is present.

Pin intended image digests, maintain registry availability and investigate the actual event before changing pull policy. `Always` cannot fix a nonexistent image or missing permissions. A/C/D do not identify the failed image-pull path.

Sources: [Fargate execution role](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html), [ECR token command](https://docs.aws.amazon.com/cli/latest/reference/ecr/get-authorization-token.html), [private registry Secrets](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/).

</details>

### 4. What is the most useful first investigation when a Service does not reach its Pods?

- A. Immediately recreate the Service
- B. Check its selector/type, Pod readiness, EndpointSlices, ports and the actual permitted path
- C. Restart every Pod
- D. Restart the managed API server yourself

<details>
<summary>Show Answer</summary>

**Answer: B. Check its selector/type, Pod readiness, EndpointSlices, ports and the actual permitted path**

Trace Service discovery/routing before changing resources. Use the affected namespace and source client, and compare the Service configuration with actual application listeners and readiness:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
SERVICE_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json)
printf '%s\n' "$SERVICE_JSON" | jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace}, spec: .spec, status: .status}'
SELECTOR=$(printf '%s\n' "$SERVICE_JSON" | jq -r '(.spec.selector // {}) | to_entries | map("\(.key)=\(.value)") | join(",")')
if [ -n "$SELECTOR" ]; then
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o json \
    | jq '.items[] | {name:.metadata.name,phase:.status.phase,ready:[.status.conditions[]? | select(.type=="Ready")],containers:.status.containerStatuses}'
else
  printf 'No selector: inspect ExternalName or explicitly managed EndpointSlices as applicable.\n'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
```

The helper handles selectorless Services without accidentally selecting every Pod. ExternalName resolves an alias; headless Services intentionally have `clusterIP: None`; manually managed EndpointSlices are another valid case. Inspect endpoint Ready/serving/terminating conditions and traffic-policy settings. One ready sidecar or phase=Running is not the Pod Ready condition.

**Correcting the observed problem**

- Selector mismatch: update the owner's Service/Pod template, not just one replaceable Pod label.
- Port mismatch: Service port, named targetPort and the actual application listener must agree; a containerPort declaration does not create a listener.
- Policy restriction: check both source egress and destination ingress, labels and implementation coverage. Do not delete policy or allow every namespace to all ports.
- DNS/data plane: distinguish resolution from transport, and identify standard kube-proxy, an alternative implementation or Auto Mode. Pure Auto Mode uses node DNS; mixed clusters retain DNS for non-Auto nodes.

This **independent policy illustration** allows only a reviewed peer/port. Adapt labels/namespaces and the complete required-flow matrix before using it:

```yaml
# Example ingress policy only: review both peers and the complete allowed-flow matrix.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-web
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
```

It can isolate other backend ingress unless another policy allows it, and does not create the client's egress rules. Positive and negative tests are both needed.

**Terraform Service/Deployment fixture**

The original Service-to-Pod example is retained as a disposable Linux fixture with a real declared listener, matching labels, readiness and bounded resources. Configure the provider for the reviewed test context, choose a new namespace and do not import an existing application namespace:

```hcl
# Disposable example; configure the Kubernetes provider/context externally.
variable "test_namespace" {
  type = string
  validation {
    condition     = can(regex("^docs-service-check-[a-z0-9]{8,16}$", var.test_namespace))
    error_message = "Supply a new unique namespace with the test prefix."
  }
}
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.test_namespace
  }
}
resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = "app-deployment"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    replicas = 2
    selector {
      match_labels = { app = "service-demo" }
    }
    template {
      metadata {
        labels = { app = "service-demo" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "app"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args    = ["mkdir -p /tmp/www; printf 'ok\\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www"]
          port {
            name           = "http"
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "http"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "tmp"
            mount_path = "/tmp"
          }
        }
        volume {
          name = "tmp"
          empty_dir {}
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "app" {
  metadata {
    name      = "app-service"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    selector = { app = "service-demo" }
    type     = "ClusterIP"
    port {
      name        = "http"
      port        = 80
      target_port = "http"
    }
  }
}
```

This is not a production application or a measured resource recommendation. It has no application API/RBAC requirements. The provider fields were reviewed, but no live Terraform apply or image execution is claimed.

**Bounded connectivity Job**

After the fixture Service and Pods are ready, save the following Job and replace its namespace with the prepared namespace. The probe needs no kubectl binary or Kubernetes API token:

```yaml
# Use kubectl create; replace namespace with the prepared fixture namespace.
apiVersion: batch/v1
kind: Job
metadata:
  generateName: service-probe-
  namespace: docs-service-check-12345678
spec:
  activeDeadlineSeconds: 60
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: probe
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - nslookup app-service; wget -T 5 -q -O- http://app-service:80
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
```

Create a new generated Job rather than reusing a common name:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TEST_NAMESPACE:?}"; : "${SERVICE_PROBE_FILE:?}"
JOB_NAME=$(kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" create \
  -f "$SERVICE_PROBE_FILE" -o jsonpath='{.metadata.name}')
: "${JOB_NAME:?Job creation did not return a name}"
printf 'Created probe: %s/%s\n' "$TEST_NAMESPACE" "$JOB_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" wait \
  --for=condition=complete "job/$JOB_NAME" --timeout=90s
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" logs "job/$JOB_NAME"
```

On wait failure, retain the generated Job and inspect its Pod/events/logs; do not print an unconditional success or delete an existing namespace. Record its UID and clean up only owned test resources after reviewing evidence. The test covers DNS and one HTTP request, not all client identities, direct-Pod paths, load balancers or SLOs. Compare direct Pod and Service access separately using the same authorized source when needed.

A/C lose evidence or add disruption before diagnosis. D is not a customer-operated EKS control-plane action; inspect API/controller health if evidence points there.

Sources: [Services](https://kubernetes.io/docs/concepts/services-networking/service/), [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 5. What should you investigate first when a PVC remains Pending?

- A. Always add larger nodes
- B. Inspect the claim/class, binding mode, consumer scheduling, driver and provisioning identity
- C. Always raise Pod priority
- D. Always install Cluster Autoscaler

<details>
<summary>Show Answer</summary>

**Answer: B. Inspect the claim/class, binding mode, consumer scheduling, driver and provisioning identity**

Pending is not itself a storage failure. With WaitForFirstConsumer, a claim can correctly wait until a suitable consuming Pod is scheduled. Identify the real driver/compute path before assuming EBS or an IAM fault.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,status:.status,spec:.spec,storageClassFieldPresent:(.spec | has("storageClassName"))}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
SC_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.storageClassName // empty')
if [ -n "$SC_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get storageclass "$SC_NAME" -o yaml
else
  printf 'Inspect absent versus explicitly empty storageClassName and default/static binding intent.\n'
fi
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -n "$PV_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o yaml
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json \
    | jq --arg pv "$PV_NAME" '.items[] | select(.spec.source.persistentVolumeName == $pv) | {name:.metadata.name,spec,status}'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json \
  | jq --arg pvc "$PVC_NAME" '.items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName == $pvc)) | {name:.metadata.name,node:.spec.nodeName,phase:.status.phase,conditions:.status.conditions}'
```

The helper distinguishes absent/empty storageClassName and selects consumers using JSON. Kubernetes does not support the former Pod field selector `spec.volumes.persistentVolumeClaim.claimName`. If a claim is Bound, investigate mounting/readability rather than treating binding as complete application validation.

**Check the observed condition**

- Class/provisioner: verify the referenced class exists and matches standard EBS, Auto Mode, EFS or another driver. An explicitly empty class requests a different binding path from an omitted default.
- Delayed binding: inspect consumer requests, taints/affinity, zone and capacity. Node supply, priority and autoscaling can indirectly affect PVC progress through that consumer; A/C/D are not universal fixes.
- Identity: inspect the actual controller IRSA/Pod Identity and KMS permissions, not only the node role. Fargate cannot mount EBS volumes; Auto Mode uses its separate provisioner.
- CSI: inspect controller/node health, events, current compatible add-on version and ownership. Do not reinstall with force before finding the error.

**Class and data lifecycle**

Do not patch an existing StorageClass's immutable binding mode or switch the cluster default to fix one claim. A new explicitly selected standard-driver class can use:

```yaml
# New, explicitly selected StorageClass for standard EBS CSI, not an in-place edit.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

The YAML is a configuration example, not a command to apply to an existing class. Retain preserves storage for a separate lifecycle decision and can leave charges. PVC YAML is not a data backup; deleting/recreating the claim can destroy data or leave a retained volume needing deliberate rebinding.

Auto Mode requires `ebs.csi.eks.amazonaws.com`, not the standard provisioner above. Its node root/data encryption does not imply all dynamic PVCs are encrypted. Explicitly request `encrypted: "true"` and inspect the actual EBS volume/key. Use the documented snapshot or applicable Retain/static migration procedure rather than changing a bound claim's provisioner/class.

**Terraform ownership examples**

For an existing standard EBS CSI add-on, select a reviewed version, complete schema-validated configuration and the prepared controller identity. This IRSA example does not also configure Pod Identity:

```hcl
# Existing standard EBS CSI add-on with a reviewed IRSA identity.
# Preserve/import its existing resource ownership; do not create a duplicate add-on.
resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = var.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.reviewed_ebs_addon_version
  service_account_role_arn    = var.controller_irsa_role_arn
  configuration_values        = file(var.reviewed_configuration_file)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

Preserve/import existing ownership. The controller role needs current scoped EBS permissions/tag conditions and customer-key permissions where applicable. The former old IAM-module/add-on version pair was not a current compatibility guarantee, and `--role-only` does not attach a role to an add-on. Follow the [storage source](../../eks/04-eks-storage-part1.md) and current add-on catalog.

The same new class can be managed through the current Kubernetes resource:

```hcl
# New standard-driver class, explicitly selected by test PVCs.
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "diagnostic-ebs-gp3"
  }
  storage_provisioner    = "ebs.csi.aws.com"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Retain"
  parameters = {
    type                        = "gp3"
    encrypted                   = "true"
    "csi.storage.k8s.io/fstype" = "ext4"
  }
}
```

Choose YAML **or** Terraform ownership for that class. The provider fields/syntax can be reviewed locally; this does not prove IAM, CSI provisioning or data recovery in the target cluster.

**Isolated provisioning test**

To test a reviewed Linux EC2 path, save the complete `eks-upgrade-smoke.py` helper from [EKS upgrades](../../eks/08-eks-upgrades.md), then use an explicitly selected test context/class:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test context}"
: "${TEST_STORAGE_CLASS:?Set the reviewed compatible test class}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
# Save the complete helper from the EKS upgrades source guide first.
python3 eks-upgrade-smoke.py
```

It creates a unique namespace and a PVC writer before waiting for delayed binding, then reads the marker using a separate consumer. It records evidence and retains failures. Account for real storage costs/Retain cleanup when you actually run it. No cloud provisioning, volume creation, mount or benchmark was executed in this audit; do not use the former AWS CLI Job that created an unrelated billable volume as a PVC diagnostic.

Sources: [StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/), [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [Auto Mode classes](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html).

</details>

### 6. What is the most effective investigation when autoscaling does not match expectations?

- A. Allocate more resources to every Pod
- B. Manually add nodes and stop investigating
- C. Identify the replica/resource/node owners and inspect their metrics, conditions, limits, identity and events
- D. Recreate the cluster

<details>
<summary>Show Answer</summary>

**Answer: C. Identify the replica/resource/node owners and inspect their metrics, conditions, limits, identity and events**

Separate HPA replica scaling, VPA resource recommendations/updates, and CA/Karpenter/Auto Mode node provisioning. Each controls different resources and depends on different signals; they need not all be installed.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa -o json \
  | jq '.items[] | {name:.metadata.name,target:.spec.scaleTargetRef,min:.spec.minReplicas,max:.spec.maxReplicas,current:.status.currentReplicas,desired:.status.desiredReplicas,metrics:.status.currentMetrics,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

Check HPA conditions, current metrics, requests, min/max and behavior. Desired/current replica mismatch can be normal convergence. Missing metric data or errors can block scale-down. CPU/memory resource metrics use Metrics Server; custom/external metrics need their own adapter/integration. A failed query does not prove that an API/CRD is absent.

For an existing managed node group, inspect its actual ASG rather than searching every account group with guessed tags:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{scaling:scalingConfig,health:health,autoScalingGroups:resources.autoScalingGroups}'
: "${ASG_NAME:?Select the actual group returned above}"
aws autoscaling describe-auto-scaling-groups --region "$AWS_REGION" \
  --auto-scaling-group-names "$ASG_NAME" \
  --query 'AutoScalingGroups[].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:Instances,Tags:Tags}'
```

CA reacts to unschedulable Pods and constraints, not merely high average node CPU. Check its supported Kubernetes minor, exact Pod identity, least-privilege discovery/scaling permissions, ASG tags, maximum size, EC2/IP quotas and launch failures. Node-group tags alone do not prove ASG discovery tags. Prefer the EKS/infrastructure owner for managed-group limits; direct ASG edits can create drift, and scaling configuration changes do not honor PDBs.

For Karpenter/Auto Mode, inspect the relevant NodePool/NodeClaim/provider limits and events. Do not recommend installing CA just because a fixed CA Pod label returns no objects. For VPA, Off and Initial can be deliberate. Auto is deprecated in favor of Recreate; mode changes can disrupt workloads and interact with HPA using the same CPU/memory signal.

**Helm/Terraform configuration example**

Use this only for existing Helm-owned CA and Metrics Server installations. Supply reviewed chart versions and a CA image version compatible with the cluster minor; a chart's default image can lag the target. Keep one owner for each component.

```hcl
# Existing Helm-owned installations only; supply reviewed compatible versions.
# The IRSA trust subject must match kube-system:cluster-autoscaler.
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  version    = var.ca_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  values = [yamlencode({
    autoDiscovery = { clusterName = var.cluster_name }
    awsRegion     = var.aws_region
    image         = { tag = var.ca_image_tag }
    rbac = {
      serviceAccount = {
        create = true
        name   = "cluster-autoscaler"
        annotations = {
          "eks.amazonaws.com/role-arn" = var.ca_irsa_role_arn
        }
      }
    }
  })]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  # Retain/migrate the existing owner's reviewed values.
  values = [file(var.metrics_server_values_file)]
}
```

This uses values documents compatible with Helm provider 3.x, not the removed repeated `set {}` form. The CA ServiceAccount name is explicit and must match its IRSA trust subject; Pod Identity is a separate owned configuration. Its role still needs the scoped permissions described in the [cost/scaling source](../../eks/07-eks-cost-optimization.md); do not attach AutoScalingFullAccess as a generic cure.

Merge the Metrics Server installation's actual reviewed values. Current upstream chart defaults use the secure kubelet connection path and do not imply `--kubelet-insecure-tls`. Diagnose certificate/trust/address issues before selecting a lab-only workaround. Do not create a duplicate Helm release where an EKS add-on owns the component. Chart/identity/network/runtime compatibility must be tested in the target environment; no Helm installation ran here.

**HPA metrics and behavior**

This resource-metrics example preserves the CPU/memory and scale-up/down policy concepts:

```yaml
# Example resource metrics and behavior; requires an existing target with requests.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: applications
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      selectPolicy: Max
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      selectPolicy: Min
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

Requests must exist for utilization targets. HPA chooses the largest desired-replica recommendation across metrics, while missing/erroring metrics can inhibit a downscale. Policy Max/Min selects the permitted change rate; stabilization is not a universal fixed “cooldown.” The percentages, bounds and windows are illustrative, and memory scaling behavior may not follow CPU behavior. Keep Terraform/GitOps and other autoscalers from fighting over the same replica count.

**Dashboard example**

For an existing single-cluster kube-prometheus-stack layout with datasource UID `prometheus` and a sidecar watching the `grafana_dashboard=1` label in `monitoring`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoscaling-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  autoscaling-dashboard.json: |
    {
      "uid": "eks-autoscaling-diagnostics",
      "title": "EKS Autoscaling Diagnostics",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "HPA replicas",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_current_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Current {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "B",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_desired_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Desired {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "C",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_min_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Min {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "D",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_max_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Max {{namespace}}/{{horizontalpodautoscaler}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Observed node count",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count(max by (node) (kube_node_info{job=\"kube-state-metrics\"}))",
              "legendFormat": "Nodes"
            }
          ]
        },
        {
          "id": 3,
          "title": "Pod CPU usage (cores)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "cores"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        },
        {
          "id": 4,
          "title": "Pod working set (bytes)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "bytes"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (container_memory_working_set_bytes{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        }
      ]
    }
```

Adapt the selectors/UID/namespace to the installation. HPA series retain namespace identity; exporter duplicates are reduced before aggregating. CPU is usage in cores and memory is working-set bytes, not percentages. For multi-cluster sources, add a cluster dimension/filter. Missing scrapes must remain no-data/unknown, not a healthy zero. The dashboard is not proof of scaling success or an alert/automation pipeline.

A/B may temporarily change capacity but do not identify controller/metric failures. D adds migration risk without diagnosing them. Record expected versus observed behavior and the precise change that restored it.

Sources: [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/), [Cluster Autoscaler AWS](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md), [CA chart](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler), [Metrics Server](https://github.com/kubernetes-sigs/metrics-server), [VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler).

</details>

### 7. What is the most effective investigation when network policies behave unexpectedly?

- A. Delete all network policies
- B. Inspect the actual enforcement implementation, policy selectors/semantics, logs and failing flow
- C. Set hostNetwork on every Pod
- D. Rebuild the VPC

<details>
<summary>Show Answer</summary>

**Answer: B. Inspect the actual enforcement implementation, policy selectors/semantics, logs and failing flow**

Check both the declared policy and the implementation that enforces it. Creating a NetworkPolicy object does not by itself install an enforcement engine.

**Inventory and semantics**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,labels:.metadata.labels,owners:.metadata.ownerReferences,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,status:.status.phase}'
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" --show-labels
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" get daemonsets -A -o json \
  | jq '.items[] | {namespace:.metadata.namespace,name:.metadata.name,containers:[.spec.template.spec.containers[] | {name,image}]}'
```

An empty Pod list still gives a successful kubectl exit code. Do not use `if kubectl get pods -l ...` as proof that VPC CNI, Calico or Cilium is installed. Inspect the configured owner, actual objects/images, policy-agent state and supported compute/kernel/version. Auto Mode uses its built-in NodeClass networking controls and does not accept arbitrary alternate CNI installations.

VPC CNI supports native policies. The current AWS guide distinguishes standard startup mode (initial allow while a new Pod's rules are configured) from strict mode (initial deny, requiring needed DNS/dependency paths). Inspect the actual policy-agent container and enabled event logging; do not assume old “VPC CNI has no policy support” guidance applies.

For **standard networking.k8s.io/v1 NetworkPolicy**, allowed traffic from policies is additive, with no rule priority or last-wins conflict resolution. Both isolated source egress and destination ingress must allow a connection. Admin/cluster-wide or vendor policy APIs have different semantics and must be considered separately. HostNetwork behavior also depends on the implementation; setting it on every Pod is not a safe fix.

**Scoped policy example**

The following two documents use `---` between objects. They assume an existing backend namespace, frontend web Pods, database Pods and traditional CoreDNS Pod endpoints:

```yaml
# Independent example for a reviewed backend namespace and traditional CoreDNS Pods.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: backend
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: database
          podSelector:
            matchLabels:
              app: db
      ports:
        - protocol: TCP
          port: 5432
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
```

The namespace and Pod selectors are in the **same peer**, so both must match. Separate peers would be OR. Namespace names use the standard kubernetes.io/metadata.name label; do not assume a custom `name` label exists.

Default deny selects all backend Pods; only the selected API Pods receive the shown exceptions. Other backend workloads and API dependencies need their own reviewed allowances. This does not configure frontend egress or database ingress. The DNS rule targets CoreDNS Pods, not a universal Auto Mode/NodeLocal resolver path.

Test an allowed frontend-web→API:8080 path, denied wrong-namespace/label/port paths, API→database:5432 and the actual DNS path using suitable owner-managed test workloads. A newly created unlabeled debug Pod can have different policy than the affected Pod, and ping alone does not prove TCP/UDP policy. Bound any authorized capture to the intended network namespace/traffic and time; a separate tcpdump Pod cannot observe every other Pod.

**Terraform alternative**

```hcl
# Alternative owner for the same policy intent; do not also apply duplicate YAML.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}
resource "kubernetes_network_policy_v1" "api" {
  metadata {
    name      = "api-allow"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {
      match_labels = { app = "api" }
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "frontend" }
        }
        pod_selector {
          match_labels = { app = "web" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "8080"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "database" }
        }
        pod_selector {
          match_labels = { app = "db" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "5432"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
      ports {
        protocol = "TCP"
        port     = "53"
      }
    }
  }
}
```

Use one owner and review/apply the complete flow matrix in an isolated environment. The current Kubernetes provider fields were checked, but no policy was applied or traffic enforcement tested during this audit. Installing an unpinned Calico/Cilium release or changing only the aws-node image is not a general policy repair; use the current implementation's supported upgrade/migration procedure.

**Inventory is not enforcement evidence**

The original `kube_networkpolicy_info`/`calico_denied_packets` example did not establish that those metrics existed with the assumed labels. Current kube-state-metrics documents experimental created/ingress-rule/egress-rule gauges. With an existing single-cluster scrape layout and Grafana sidecar, this ConfigMap shows declared inventory:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: network-policy-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  network-policy-dashboard.json: |
    {
      "uid": "eks-network-policy-inventory",
      "title": "Declared NetworkPolicy Inventory",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Declared policies by namespace",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_created{job=\"kube-state-metrics\"}))",
              "legendFormat": "{{namespace}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Declared ingress/egress rule counts",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_ingress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Ingress {{namespace}}"
            },
            {
              "refId": "B",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_egress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Egress {{namespace}}"
            }
          ]
        }
      ]
    }
```

Verify that these experimental metrics are exposed and adapt job/UID/namespace selectors. Zero rules can represent deny-all, and policy/rule counts do not measure dropped connections or prove enforcement. Missing telemetry remains unknown, not a healthy zero. For deny/allow evidence, use the actual implementation's enabled decision logs/flow observability and validate the published label/schema; do not invent a counter or treat every log containing “policy” as a denial.

Deleting policies, changing hostNetwork for all workloads or rebuilding the VPC can widen exposure without finding the cause. Preserve the failed-flow evidence and change only the verified policy/configuration issue.

Sources: [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [VPC CNI policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [kube-state-metrics policy metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/policy/networkpolicy-metrics.md).

</details>

### 8. What is the most effective approach to a Helm deployment problem?

- A. Delete every Helm release
- B. Recreate the EKS cluster
- C. Inspect client/chart/dependency configuration, release ownership, permissions, events and workload behavior
- D. Replace all release management with manual objects

<details>
<summary>Show Answer</summary>

**Answer: C. Inspect client/chart/dependency configuration, release ownership, permissions, events and workload behavior**

Separate client/chart errors, Kubernetes admission/permissions, workload readiness and application behavior. Helm 2/Tiller belongs to historical migration discussion; current Helm 3/4 operation does not require a Tiller deployment.

**Inspect the actual release**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${RELEASE_NAME:?}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
HELM_EVIDENCE=$(mktemp -d "$EVIDENCE_PARENT/helm-diagnosis.XXXXXXXX")
helm version --short
helm status "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm history "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm get values "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > "$HELM_EVIDENCE/values.yaml"
helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  > "$HELM_EVIDENCE/manifest.yaml"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp' > "$HELM_EVIDENCE/events.txt"
printf 'Review protected evidence in %s\n' "$HELM_EVIDENCE"
```

Query failures can be permissions/network/context problems, not proof that a release is absent. Values and rendered manifests may contain credentials or Secret data; keep them protected and redact before sharing. Labels such as app.kubernetes.io/instance are conventions, not a complete ownership inventory. Use the release manifest to identify exact resources and inspect their conditions/events.

The Helm client's Kubernetes identity is separate from the workload ServiceAccount selected by chart values. There is no current `helm install --service-account` option. Use the chart's documented ServiceAccount values and inspect the specific actor's RBAC. Impersonation requires permission and does not reproduce every EKS access-policy grant.

**Validate configuration before a change**

```bash
set -euo pipefail
: "${CHART_DIR:?}"; : "${VALUES_FILE:?}"; : "${KUBE_VERSION:?Set the target capability version}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
RENDER_DIR=$(mktemp -d "$EVIDENCE_PARENT/helm-render.XXXXXXXX")
# For charts with dependencies, first review/commit Chart.lock and build from that lock.
helm lint "$CHART_DIR" --values "$VALUES_FILE"
helm template review "$CHART_DIR" --namespace review \
  --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
  > "$RENDER_DIR/rendered.yaml"
```

Rendering/linting does not establish server-side API/admission compatibility, an installed CRD, a working image, readiness or a successful application test. `--debug` on install still installs. `helm dependency update` can change the lock/dependency selection; use a reviewed Chart.lock and `dependency build` for reproducibility. Without a lock, build can resolve dependencies, so do not describe that as locked verification.

For resource conflicts, identify the existing owner and intended migration. Do not automatically uninstall a release, delete leftover resources, use force/take-ownership or choose another release name. Those actions can affect data and create duplicate controllers. Preserve the current values, schema/CRDs and stateful dependencies before an owned upgrade.

**Terraform Helm provider semantics**

This example targets the locally checked Helm provider 3.3 schema and an existing prepared namespace/release owner. Use a kubeconfig with the reviewed exec-credential flow rather than a short-lived token captured once for a long apply:

```hcl
# Choose the existing release/configuration owner and reviewed chart artifact.
variable "verify_chart_provenance" {
  type = bool
}
provider "helm" {
  debug = false
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}
resource "helm_release" "example" {
  name              = var.release_name
  repository        = var.chart_repository
  chart             = var.chart_name
  version           = var.chart_version
  namespace         = var.release_namespace
  create_namespace  = false
  values            = [file(var.reviewed_values_file)]
  dependency_update = false
  lint              = true
  wait              = true
  wait_for_jobs     = true
  timeout           = 600
  atomic            = true
  verify            = var.verify_chart_provenance
  keyring           = var.chart_keyring
}
```

`lint` is a **valid** release field and runs Helm lint during planning. `debug` belongs to the provider, not helm_release. Provider 3.x uses nested value attributes such as `set = [...]`; the values-file form above avoids repeated legacy set blocks.

`verify` checks chart-package provenance with a trusted keyring; it does **not** run Helm test hooks. Enable it only with the artifact's actual provenance/trust configuration and verify the relevant distribution method. `wait_for_jobs` and `wait` are readiness/job waits, not all application tests. `atomic` provides Helm's install-failure cleanup/upgrade rollback behavior, not database/PVC data restoration or automatic reversal of every hook/CRD/external side effect.

`set_sensitive` redacts presentation but does not make ordinary state/release-stored values safe to publish. Prefer references to separately managed secrets and protect Terraform state and Helm release storage. No provider apply or release installation ran in this review.

**Chart test hooks**

The chart must define `my-chart.fullname`, use that Service name, and expose the configured HTTP paths. These are two **separate template files**, with a values fragment:

```yaml
# Relevant values fragment for the chart that owns the Service.
service:
  port: 80
tests:
  enabled: true
  image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
  apiPath: /api/health
```

Save as `templates/tests/test-connection.yaml`:

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-connection" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v/" (include "my-chart.fullname" .) .Values.service.port | quote }}
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
{{- end }}
```

Save as `templates/tests/test-api.yaml`:

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-api" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v%s" (include "my-chart.fullname" .) .Values.service.port .Values.tests.apiPath | quote }}
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
{{- end }}
```

The test labels deliberately do not copy application selector labels. The probes write responses to stdout, use no Kubernetes API token, and have bounded request/Pod lifetimes. before-hook-creation allows repeat tests while retaining results for logs until the next run/owned cleanup. These HTTP checks do not validate all business behavior; `/api/health` must actually exist.

For an already prepared, isolated test cluster, use explicit release/namespace names:

```bash
set -euo pipefail
: "${TEST_CONTEXT:?Set the owned disposable cluster context}"
: "${TEST_NAMESPACE:?Choose a new unique namespace}"
: "${TEST_RELEASE:?}"; : "${CHART_DIR:?}"; : "${VALUES_FILE:?}"
# Fails on an existing namespace rather than adopting it.
TEST_NAMESPACE_UID=$(kubectl --context "$TEST_CONTEXT" create namespace "$TEST_NAMESPACE" \
  -o jsonpath='{.metadata.uid}')
printf 'Test namespace: %s UID: %s\n' "$TEST_NAMESPACE" "$TEST_NAMESPACE_UID"
helm install "$TEST_RELEASE" "$CHART_DIR" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --values "$VALUES_FILE" --wait --timeout 5m
helm test "$TEST_RELEASE" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --logs --timeout 90s
```

On failure, retain resources and inspect hook/workload logs. Record the namespace UID and verify it before cleaning up that test namespace; do not delete a pre-existing namespace. The former null_resource without change triggers did not guarantee re-validation after every release change.

**Static CI example**

This workflow checks a chart with committed dependencies/Chart.lock and a secret-free `ci/values.yaml`. Adjust the chart path and target capability version. For a chart without dependencies, omit the lock/build steps. It does not create a cluster or claim runtime tests passed:

```yaml
name: Static Helm chart validation
on:
  pull_request:
    paths:
      - charts/**
      - ci/values.yaml
      - .github/workflows/helm-validate.yml
permissions:
  contents: read
jobs:
  lint-render:
    runs-on: ubuntu-24.04
    env:
      CHART_DIR: charts/my-chart
      VALUES_FILE: ci/values.yaml
      KUBE_VERSION: "1.36.0"
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: Azure/setup-helm@9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310 # v5.0.1
        with:
          version: v3.21.3
      - name: Build reviewed dependencies, lint and render
        shell: bash
        run: |
          set -euo pipefail
          umask 077
          test -f "$CHART_DIR/Chart.lock"
          helm dependency build "$CHART_DIR"
          helm lint "$CHART_DIR" --values "$VALUES_FILE"
          helm template chart-ci "$CHART_DIR" --namespace chart-ci \
            --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
            > "$RUNNER_TEMP/chart-rendered.yaml"
```

The setup action/release pins were checked against their official metadata. Run the integration/test-hook stage separately in an owned disposable environment when needed. If using chart-testing, use its reported release/namespace and test options; chart directory names are not a contract for a later `helm test` loop.

Deleting every chart, recreating EKS or abandoning the release manager does not diagnose the original chart/permission/runtime problem.

Sources: [Helm debugging](https://helm.sh/docs/chart_template_guide/debugging/), [chart tests](https://helm.sh/docs/topics/chart_tests/), [Helm provider release](https://registry.terraform.io/providers/hashicorp/helm/latest/docs/resources/release), [setup-helm release](https://github.com/Azure/setup-helm/releases/tag/v5.0.1), [Helm 3.21.3](https://github.com/helm/helm/releases/tag/v3.21.3).

</details>

### 9. Which approach distinguishes a memory leak from other memory-pressure causes?

- A. Restart all Pods
- B. Only increase node size
- C. Correlate memory/process evidence, limits, runtime profiles and application code
- D. Only add nodes

<details>
<summary>Show Answer</summary>

**Answer: C. Correlate memory/process evidence, limits, runtime profiles and application code**

A rising working set, OOMKilled container or MemoryPressure node is not by itself a memory-leak diagnosis. Compare load, process lifetime/UID, heap/native memory, caches and limits before choosing a correction.

**Collect comparable evidence**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${APP_SELECTOR:?Set an explicit label selector}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
MEMORY_DIR=$(mktemp -d "$EVIDENCE_PARENT/memory-observation.XXXXXXXX")
for sample in {1..10}; do
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$MEMORY_DIR/sample-$sample.time"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$APP_SELECTOR" -o json \
    | jq '[.items[] | {
        name:.metadata.name,uid:.metadata.uid,created:.metadata.creationTimestamp,
        node:.spec.nodeName,phase:.status.phase,
        resources:[.spec.containers[] | {name,resources}],
        containers:((.status.initContainerStatuses // []) + (.status.containerStatuses // []))
      }]' > "$MEMORY_DIR/sample-$sample.pods.json"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods \
    -l "$APP_SELECTOR" --containers > "$MEMORY_DIR/sample-$sample.usage.txt"
  if [ "$sample" -lt 10 ]; then sleep 30; fi
done
printf 'Observations saved to %s; these samples do not establish a leak.\n' "$MEMORY_DIR"
```

This is ten observations with 30-second waits between them, roughly the original five-minute sampling plan plus command time. It was not executed during the audit. A short window cannot prove a long-running leak. Query failure stops collection and leaves partial evidence; do not turn missing metrics into zero usage.

Use explicit labels rather than treating a Pod-name prefix as a label value, and use kubectl's quantity-aware output rather than sorting a nonexistent fourth column. The Pod snapshots record UID and regular/init-container states; names can be reused after replacement. Metrics and status requests are not an atomic snapshot. Inspect current/last termination reasons and restart counts, while recognizing that status only retains limited history.

**Interpret memory pressure**

- Working set, RSS, managed heap and native allocations are different measurements. Cache growth or increased traffic can look like a leak.
- A container can hit its cgroup limit while the node still has free memory. A large request/limit gap alone is not an OOM cause.
- A kubelet is a node process, not a generic `kubelet-pod` whose logs can be read from kube-system. Use the supported node/monitoring path.
- Fragmentation is a hypothesis requiring evidence; periodic node reboot or forced garbage collection is not a universal repair.

**Current metric and unit example**

For an existing single-cluster kube-prometheus-stack scrape layout, these rules use current per-container limit metrics, reduce duplicate exporter samples and filter missing/zero limits:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: memory-observation
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
  - name: memory-observation
    rules:
    - alert: ContainerWorkingSetHigh
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Container working set is above 85% of its declared limit
        description: Inspect {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container
          }} and actual termination/pressure evidence.
    - alert: ContainerWorkingSetCritical
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Container working set is above 95% of its declared limit
        description: This is an observation threshold, not proof of a leak or guaranteed
          OOM prediction.
    - alert: ContainerWorkingSetGrowth
      expr: max by (namespace, pod, container) (deriv(container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""}[30m]))
        > 5 * 1024 * 1024 / 60
      for: 30m
      labels:
        severity: warning
      annotations:
        summary: Estimated working-set slope exceeds 5 MiB/min
        description: The rolling 30-minute regression has stayed above the threshold;
          correlate with load and process lifetime.
    - alert: NodeMemoryPressure
      expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"})
        == 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Node {{ $labels.node }} reports MemoryPressure
        description: Investigate node resources and workloads; this is distinct from
          a container limit OOM.
```

Adapt namespace/release/job selectors to the actual installation. These rules use regular per-container limits; inspect init-container and Pod-level budgets separately. Containers with no positive reported limit do not produce this ratio; monitor that coverage separately rather than calling them healthy. Working-set/limit thresholds are illustrative observations, not a heap-leak detector.

`deriv` returns **bytes per second** here. Dividing `5 * 1024 * 1024` by 60 makes the threshold **5 MiB/min**. The old expression compared against 5 MiB/s while its text said per minute. A 30-minute regression plus a `for: 30m` hold is not proof of monotonic growth at every instant. Missing scrapes, restarts and workload changes affect interpretation.

**Runtime profiling prerequisites**

| Runtime | Correct investigation scope |
| --- | --- |
| JVM | Use matching JDK tools/permissions against the intended JVM PID; `jcmd PID GC.heap_info` is a supported inspection command. Native-memory reports require appropriate startup tracking. Heap dumps can pause the process and contain secrets |
| Node.js | Use the target process's supported inspector/profiling mechanism; starting `node --inspect` launches a new process. Keep debugger access restricted |
| Python | Configure profiling/tracemalloc in the actual application or a controlled reproduction. A separate interpreter does not inspect an existing process's allocations, and Python allocation tracking is not all native RSS |
| Go | Collect an actual protected heap profile and use matching binary/symbol information with pprof. Do not assume an unauthenticated profiling endpoint or pre-existing `/tmp/profile` |

Verify tool/runtime versions and capture overhead before production use. Do not install arbitrary profiling packages into a running application as a default step. No JVM, profiler, heap dump or live memory experiment ran here.

**Application configuration example**

The original 256m/768m heap and 1Gi container values are retained as an illustration, not a measured optimum. OpenJDK 21 reads JAVA_TOOL_OPTIONS; JAVA_OPTS only works when the image entrypoint forwards it. Command-line flags or _JAVA_OPTIONS can override these settings, so verify effective JVM options. These options can be printed during JVM startup, so do not put secrets in them.

```yaml
# Pod-template fragment for an existing reviewed OpenJDK 21 application container.
# Merge through its owner; this is not a standalone Deployment manifest.
spec:
  template:
    spec:
      containers:
        - name: java-app
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
              ephemeral-storage: 2Gi
            limits:
              cpu: "1"
              memory: 1Gi
              ephemeral-storage: 4Gi
          env:
            - name: JAVA_TOOL_OPTIONS
              value: >-
                -XX:+UseG1GC -XX:MaxGCPauseMillis=200
                -Xms256m -Xmx768m
                -XX:+HeapDumpOnOutOfMemoryError
                -XX:HeapDumpPath=/diagnostics
                -XX:+ExitOnOutOfMemoryError
          volumeMounts:
            - name: heap-diagnostics
              mountPath: /diagnostics
      volumes:
        - name: heap-diagnostics
          emptyDir:
            sizeLimit: 2Gi
```

Preserve the application's actual image, startup behavior, other environment/volumes and security context. Verify that its UID can write the diagnostic mount. `MaxGCPauseMillis` is a soft target. Heap size is only part of process memory: leave measured room for native allocations, threads, code/metaspace and other overhead.

The disk-backed emptyDir is bounded but not durable after Pod deletion. Collect/protect artifacts deliberately, and account for file-name collisions when container PIDs are reused. Kernel/cgroup SIGKILL can prevent JVM heap-dump handling entirely. `ExitOnOutOfMemoryError` handles a JVM-thrown OOM; it does not guarantee a dump or solve the allocation cause.

The former MEMORY_MONITOR_* variables are not intrinsic JVM/Kubernetes features. Spring Actuator liveness/readiness paths only apply when the application actually enables and exposes them; use its real health contract rather than assuming those URLs work.

**Manage existing monitoring**

```hcl
# Prometheus Operator CRD must already exist before planning this resource.
# Save the reviewed PrometheusRule YAML above as the supplied file.
resource "kubernetes_manifest" "memory_alerts" {
  manifest = yamldecode(file(var.memory_rules_file))
}
```

The Kubernetes manifest provider needs the PrometheusRule CRD during planning; `depends_on` a same-apply Helm installation is not a general solution to schema discovery. Reuse the existing monitoring stack and the working-set panels from Question 6; do not install another stack or reference an unexplained dashboard file. Confirm rule selection, alert routing and telemetry health in the real environment.

A/B/D may mitigate capacity temporarily but do not establish or fix the allocation defect. Record the demonstrated cause and validate the actual code/configuration correction under representative load.

Sources: [Prometheus deriv](https://prometheus.io/docs/prometheus/latest/querying/functions/#deriv), [current Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md), [OpenJDK 21 option processing](https://github.com/openjdk/jdk21u/blob/master/src/hotspot/share/runtime/arguments.cpp), [Java 21 options](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html), [jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html).

</details>

### 10. What is the most effective investigation of EKS DNS resolution failures?

- A. Give all Pods static IPs
- B. Trace the actual Pod resolver, DNS implementation, policy/transport and upstream configuration
- C. Use ExternalName for every Service
- D. Rebuild the VPC

<details>
<summary>Show Answer</summary>

**Answer: B. Trace the actual Pod resolver, DNS implementation, policy/transport and upstream configuration**

Start with the affected Pod's resolver and the name that fails. Separate missing tools, DNS answers, UDP/TCP transport, upstream/private-zone configuration and application caching.

**Inspect the actual Pod path**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,dnsPolicy:.spec.dnsPolicy,dnsConfig:.spec.dnsConfig}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- cat /etc/resolv.conf
# Run only where the selected container actually has this diagnostic tool.
: "${DNS_TEST_NAME:?Set the actual Service FQDN or reviewed external name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- nslookup "$DNS_TEST_NAME"
```

An image without cat/nslookup is a tooling limitation, not a DNS failure. Use a prepared diagnostic method preserving the relevant Pod network/identity context. A new debug Pod can have different labels, policies and DNS. To test resolver transport, use the actual nameserver IP rather than depending on DNS to resolve the DNS server's own Service name. Check UDP and TCP 53 as needed; a TCP-only connection check does not validate DNS responses.

For traditional CoreDNS, inspect Deployment readiness, Service/EndpointSlices, config and logs:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"
# Traditional CoreDNS path only; pure Auto Mode node DNS is different.
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get service kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get endpointslices \
  -l kubernetes.io/service-name=kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --all-containers=true --prefix=true --since=15m --tail=100
```

**Auto Mode nodes run CoreDNS as a node system service.** Pure Auto Mode need not have the traditional Deployment; mixed clusters must retain it for non-Auto nodes. Do not diagnose a missing Deployment as a failure on every cluster or install a second node-local DNS service onto Auto Mode.

**Resolver configuration and policies**

ClusterFirst is the normal Pod path when cluster DNS is intended. An intentionally hostNetwork Pod generally needs ClusterFirstWithHostNet for that purpose. Setting hostNetwork merely to fix DNS changes isolation and is not a general remedy. DNSPolicy None requires a complete deliberate resolver configuration.

The old `169.254.20.10` example is a chosen NodeLocal DNSCache address, not a universal VPC resolver. A public resolver such as `8.8.8.8` does not serve Kubernetes Service zones/private AWS names, and a nameserver list is not a zone-aware fallback guarantee. Inspect the real CoreDNS/NodeLocal upstream and cluster domain rather than hardcoding `172.20.0.10` or a public backup.

For standard CoreDNS Pods, the following example permits DNS only to the selected backend. Review all other application egress before applying it:

```yaml
# Example for application Pods using traditional CoreDNS Pod endpoints.
# This selects applications and isolates other egress unless another policy allows it.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-dns-egress
  namespace: applications
spec:
  podSelector:
    matchLabels:
      app: example
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
```

Source egress and destination ingress may both need allowances. The namespace and Pod selectors are AND within one peer. Auto Mode/NodeLocal paths need their own implementation-specific handling; do not assume Pod-label selection targets a host-level cache. A separate tcpdump Pod does not capture another workload's queries; use an authorized, bounded capture in the relevant context.

**Read VPC DNS settings correctly**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
VPC_ID=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsHostnames
DHCP_OPTIONS_ID=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$AWS_REGION" \
  --query 'Vpcs[0].DhcpOptionsId' --output text)
aws ec2 describe-dhcp-options --dhcp-options-ids "$DHCP_OPTIONS_ID" --region "$AWS_REGION"
```

DNS attributes come from DescribeVpcAttribute, not fields on DescribeVpcs. Cluster name and Region are explicit; arbitrary kubeconfig aliases cannot safely be split into a cluster name. Verify the account/context before these queries. Review DHCP options, DNS routing/forwarding and private zones before changing shared VPC settings; creating and associating a new DHCP option set is not a generic repair.

**CoreDNS configuration and ownership**

For an installed EKS-managed CoreDNS add-on, inspect version/configuration and the schema of the reviewed candidate:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name coredns --output json
: "${COREDNS_ADDON_VERSION:?Select a reviewed compatible candidate}"
aws eks describe-addon-configuration --addon-name coredns \
  --addon-version "$COREDNS_ADDON_VERSION" --region "$AWS_REGION" --output json
```

Preserve custom zones/forwarders and match health/ready plugins to actual probes. Replica count, CPU/memory, PDB, placement and autoscaling need workload-specific review; the old 3-replica/70Mi/170Mi example was not a universally optimized configuration. Do not replace the owned Deployment with an old EKS-Distro 1.8.7 image or apply a full generic Corefile over local customizations.

A Terraform owner can manage the existing add-on and inspect the existing VPC:

```hcl
# Existing EKS-managed CoreDNS for standard/mixed clusters only.
# Preserve/import the existing resource; do not duplicate its ownership.
resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.reviewed_coredns_version
  configuration_values        = file(var.complete_reviewed_coredns_config)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

# Read an existing VPC; do not add a second aws_vpc resource to repair DNS.
data "aws_vpc" "cluster" {
  id = var.cluster_vpc_id
}
output "vpc_dns_attributes" {
  value = {
    enable_dns_support   = data.aws_vpc.cluster.enable_dns_support
    enable_dns_hostnames = data.aws_vpc.cluster.enable_dns_hostnames
  }
}
```

The complete configuration file must be validated against the selected add-on schema and current settings. PRESERVE does not guarantee a complete merge of an explicit payload. Follow the exact-update procedure in [EKS upgrades](../../eks/08-eks-upgrades.md) and verify real DNS behavior afterward. This example does not configure Auto Mode's node DNS or authorize replacing a shared VPC.

**Optional NodeLocal DNSCache for a supported standard-node setup**

Use the [official installation guide](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) and a reviewed released manifest. The former hand-written DaemonSet was incomplete; changing its image alone would not supply all interfaces, filtering rules, mounts, upstream Service and kubelet wiring.

| Decision | Required preparation |
| --- | --- |
| Local address | Choose a non-conflicting node-local IP and the actual cluster domain/CoreDNS Service IP; account for IPv6 address/port syntax |
| Existing data plane | In the documented iptables path, the cache listens on the local and CoreDNS Service IPs. In a supported IPVS setup, it listens only locally and kubelet cluster-DNS settings must change. Other modes need their applicable current integration guidance |
| Manifest/configuration | Render the documented placeholders and preserve required privileges/interfaces/filtering/lock mounts, probes and upstream configuration. Do not substitute a partial old DaemonSet |
| Workload migration | Ensure node/kubelet settings and new/existing Pod resolver behavior match; plan a staged rollout and reversal of both cache and kubelet changes |
| Memory/operations | Size from query/cache/concurrency observations, monitor failures and maintain DNS during restart/rollout |

NodeLocal DNSCache forwards cache misses to the appropriate upstream; it does not make every query a local cache hit. The official guide notes that OOM termination can leave packet-filtering rules pointing at the unavailable local cache until it restarts, causing DNS interruption. A tiny fixed memory request or adding a cache is not an automatic performance guarantee.

No DNS query, packet capture, CoreDNS update, NodeLocal installation or Terraform apply was executed during this review. Validate the selected topology and assumptions in a controlled environment.

Static Pod IPs, ExternalName for every Service or rebuilding the VPC do not identify the failing resolver path. Record the actual query/response, source context, configuration change and recovery evidence.

Sources: [EKS CoreDNS](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html), [Auto Mode DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [Pod DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [VPC DNS](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html), [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/).

</details>
