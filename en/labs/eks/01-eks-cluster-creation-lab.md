# EKS Cluster Creation Lab Guide

> **Difficulty**: Intermediate
> **Estimated Time**: 60–90 minutes; provisioning and deletion times vary
> **Last Updated**: September 12, 2026

## Learning Objectives

- Create a dedicated EKS cluster using eksctl.
- Verify the AWS account and cluster identity before changing resources.
- Inspect nodes, deploy a sample application and scale it.
- Delete the lab resources and check for incomplete cleanup.

## Prerequisites

- [ ] An approved AWS lab account and temporary role credentials, for example through IAM Identity Center. Have an administrator approve the required EKS, EC2, CloudFormation, IAM/PassRole and related permissions for this configuration; do not create a long-lived IAM user or grant AdministratorAccess just for this guide.
- [ ] AWS CLI v2, eksctl, kubectl, Bash, Python 3, jq and curl.
- [ ] An approved public IPv4 client CIDR, normally your workstation's current egress `/32`. The generator rejects ranges broader than `/24`; use your organization's narrower limit where required.
- [ ] Completed [EKS Cluster Creation](../../eks/02-eks-cluster-creation-part1.md).

This lab uses an EKS 1.36 managed node group. On the review date, AWS lists 1.36 in standard support; the former 1.31 example is in extended support. Check the current AWS support calendar before running the lab. Use a kubectl minor version within one of the API server, preferably 1.36 for this example.

The examples were checked with eksctl 0.229.0 and kubectl 1.36.2 using schemas and local mocks. **This audit did not provision a cluster or measure deployment time.** Account permissions, quotas, instance availability and network access still require validation in your lab account.

EKS, EC2, EBS, the NAT gateway and data transfer incur charges. This configuration creates private nodes with one NAT gateway; that is a lab cost/availability choice, not a production availability design. `STANDARD` support policy avoids entering extended support by allowing a later automatic version upgrade; it does not stop the cluster or its other charges.

Run the commands in order in a dedicated Bash terminal (**Terminal A**). Keep the printed private lab directory and do not commit its kubeconfig or identity records. Later commands depend on its variables and functions.

## Exercise 1: Tools and Account

### 1.1 Check tools

```bash
aws --version
eksctl version
kubectl version --client
python3 --version
jq --version
```

### 1.2 Set the intended account and client range

Set `EXPECTED_ACCOUNT_ID` and `CLIENT_CIDR` to your approved values before this block. Do not copy an example account ID or a documentation-only IP address. `AWS_REGION` defaults to Seoul; both region variables are kept consistent.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended 12-digit lab account ID}"
: "${CLIENT_CIDR:?Set your approved public client IPv4 CIDR, usually a /32}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLIENT_CIDR
umask 077
export LAB_DIR
LAB_DIR=$(mktemp -d "$PWD/eks-lab.XXXXXXXX")
export LAB_RUN_ID
LAB_RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
export CLUSTER_NAME="eks-lab-$LAB_RUN_ID"
export KUBECONFIG="$LAB_DIR/kubeconfig"
printf 'Private lab directory: %s\nCluster: %s\nRegion: %s\n' "$LAB_DIR" "$CLUSTER_NAME" "$AWS_REGION"
```

The configuration generator validates those inputs and records the intended cluster before creation:

```bash
python3 - <<'PY'
import ipaddress, json, os, re
from pathlib import Path
account = os.environ["EXPECTED_ACCOUNT_ID"]
region = os.environ["AWS_REGION"]
name = os.environ["CLUSTER_NAME"]
run_id = os.environ["LAB_RUN_ID"]
network = ipaddress.ip_network(os.environ["CLIENT_CIDR"], strict=True)
if not re.fullmatch(r"\d{12}", account):
    raise SystemExit("Expected a 12-digit account ID")
if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid Region")
if not re.fullmatch(r"eks-lab-[0-9a-f]{12}", name) or name != "eks-lab-" + run_id:
    raise SystemExit("Unexpected lab name")
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed narrow IPv4 CIDR (/24 or narrower); never 0.0.0.0/0")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": name, "region": region, "version": "1.36",
                 "tags": {"content-lab-id": run_id}},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "vpc": {"clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [str(network)], "nat": {"gateway": "Single"}},
    "managedNodeGroups": [{
        "name": "workers", "instanceType": "t3.medium", "amiFamily": "AmazonLinux2023",
        "desiredCapacity": 2, "minSize": 1, "maxSize": 3,
        "privateNetworking": True, "volumeSize": 20, "volumeType": "gp3",
        "volumeEncrypted": True
    }]
}
directory = Path(os.environ["LAB_DIR"])
(directory / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
(directory / "lab-state.json").write_text(json.dumps({
    "account": account, "region": region, "cluster": name, "labId": run_id
}, indent=2) + "\n")
PY
```

```bash
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf '%s\n' 'Account mismatch; stop.' >&2; return 1; }
}
check_account
aws sts get-caller-identity --region "$AWS_REGION"
```

The returned account must match `EXPECTED_ACCOUNT_ID`; an assumed-role ARN is normal for temporary credentials. A mismatch or failed authentication is a reason to stop.

## Exercise 2: Create and Identify the Cluster

### 2.1 Review the configuration

```bash
cat "$LAB_DIR/cluster.json"
```

The configuration selects EKS 1.36, API-based access entries, two `t3.medium` managed nodes, AL2023, encrypted 20 GiB gp3 node disks, and a unique `content-lab-id` tag. Both API endpoints are enabled: nodes use private access, while the public endpoint permits only the approved client CIDR. Nodes still need outbound access to image/package endpoints.

### 2.2 Create the cluster

The next command creates billed resources. Allow enough time for both creation and cleanup; the 45-minute timeout is a waiting limit, not a completion guarantee.

```bash
# MUTATION: creates billed CloudFormation/EKS/VPC/NAT/EC2/EBS resources.
check_account
eksctl create cluster --config-file "$LAB_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

If creation fails or is interrupted, **do not start another randomly named cluster or run the normal cleanup block blindly**. Keep `lab-state.json` and `cluster.json`, inspect the named CloudFormation stacks, and reconcile their tags, account and resources first. A failed CLI response does not prove that no resources were created; unresolved resources can continue to incur charges.

### 2.3 Save identity and a private kubeconfig

Run this only after creation succeeds. `--write-kubeconfig=false` above leaves your usual kubeconfig untouched; the following command writes only the dedicated lab path.

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,createdAt:createdAt,endpoint:endpoint,tags:tags}' \
  --output json > "$LAB_DIR/cluster-identity.json"
jq -e --arg id "$LAB_RUN_ID" '.tags["content-lab-id"] == $id' "$LAB_DIR/cluster-identity.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
```

Define a guard that checks the account, cluster ARN, creation time, ownership tag and kubeconfig endpoint before subsequent changes:

```bash
check_lab() {
  check_account || return
  local current endpoint
  current=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --output json) || return
  jq -e --arg id "$LAB_RUN_ID" --slurpfile saved "$LAB_DIR/cluster-identity.json" '
    .cluster.arn == $saved[0].arn and
    .cluster.createdAt == $saved[0].createdAt and
    .cluster.tags["content-lab-id"] == $id and
    .cluster.endpoint == $saved[0].endpoint
  ' <<<"$current" >/dev/null || { printf '%s\n' 'Cluster identity mismatch; stop.' >&2; return 1; }
  endpoint=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CLUSTER_NAME" config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}') || return
  jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$LAB_DIR/cluster-identity.json" >/dev/null ||
    { printf '%s\n' 'Kubeconfig endpoint mismatch; stop.' >&2; return 1; }
}
check_lab
```

### Verification

```bash
check_lab
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -o wide
kubectl --context "$CLUSTER_NAME" wait node --selector=eks.amazonaws.com/nodegroup=workers \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/nodegroup=workers -o json |
  jq -e '(.items | length) == 2 and all(.items[];
    any(.status.conditions[]; .type == "Ready" and .status == "True"))'
```

Both nodes should be Ready. If fewer nodes register, inspect the node group and CloudFormation events; do not treat a successful control-plane creation as proof that the workers are healthy.

## Exercise 3: Explore the Cluster

Choose a `NODE_NAME` from the verified node list and set it before running this block. This lab uses ordinary managed nodes, so its system component view differs from a pure Auto Mode cluster.

```bash
check_lab
: "${NODE_NAME:?Choose a node name from the preceding list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe node "$NODE_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get pods
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get services
# Run separately; preserve the actual error if the metrics API is unavailable.
if ! kubectl --context "$CLUSTER_NAME" --request-timeout=15s top nodes; then
  printf 'Metrics query failed; inspect the error and metrics API status.\n' >&2
fi
```

`kubectl top` requires the metrics API. A failure can indicate missing metrics-server, unavailable metrics, RBAC or connectivity problems. Preserve the actual error and diagnose it rather than declaring that metrics-server is absent.

## Exercise 4: Deploy and Scale an Application

### 4.1 Deploy nginx

The Deployment has explicit resource requests/limits and a readiness probe. The Service is `ClusterIP`; this exercise does not install a load balancer controller or allocate a public load balancer.

```bash
cat > "$LAB_DIR/app.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: eks-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 2
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
  namespace: eks-lab
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
YAML
```

```bash
# MUTATION in the verified dedicated lab cluster.
check_lab
kubectl --context "$CLUSTER_NAME" create namespace eks-lab
kubectl --context "$CLUSTER_NAME" label namespace eks-lab "content-lab-id=$LAB_RUN_ID"
kubectl --context "$CLUSTER_NAME" apply -f "$LAB_DIR/app.yaml"
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
```

### 4.2 Verify local access

Start port forwarding in Terminal A, then run the curl command in **Terminal B** on the same workstation. The listener binds only to loopback. A forwarded connection exercises a selected Pod; it is not a test of external load balancing or every replica.

```bash
# Keep this in Terminal A; it binds only loopback. Stop with Ctrl+C before continuing.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab port-forward service/nginx 8080:80 --address=127.0.0.1 || test "$?" -eq 130
```

```bash
# Terminal B on the same workstation; no AWS credentials are needed for this local URL.
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
  http://127.0.0.1:8080/ --output /dev/null --write-out 'HTTP %{http_code}\n'
```

A successful check prints `HTTP 200`. Stop the foreground port-forward with Ctrl+C in Terminal A before continuing. The command permits that expected interrupt while retaining the other failure checks.

### 4.3 Scale to four replicas

```bash
# MUTATION: after stopping port-forward in Terminal A.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab scale deployment/nginx --replicas=4
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n eks-lab get deployment nginx -o json |
  jq -e '.spec.replicas == 4 and .status.observedGeneration >= .metadata.generation and
         .status.readyReplicas == 4 and .status.availableReplicas == 4'
```

If you also want a public LoadBalancer exercise, first follow [EKS Networking](../../eks/03-eks-networking-part1.md) to configure the intended controller, IAM permissions and exposure settings. Its resources and costs must be separately tracked and removed; an assigned hostname or Deployment readiness alone does not prove end-to-end load balancer health.

## Cleanup

Stop port forwarding first. This block deletes the tagged lab namespace and the dedicated cluster. A missing namespace is allowed; an unreadable or differently tagged namespace is not treated as safe to delete.

```bash
# DESTRUCTIVE: only the verified dedicated lab resources.
check_lab
namespace_json=$(kubectl --context "$CLUSTER_NAME" --request-timeout=15s \
  get namespace eks-lab --ignore-not-found -o json)
if [ -n "$namespace_json" ]; then
  jq -e --arg id "$LAB_RUN_ID" '.metadata.labels["content-lab-id"] == $id' \
    <<<"$namespace_json" >/dev/null
  kubectl --context "$CLUSTER_NAME" delete namespace eks-lab --wait=true --timeout=180s
fi
check_lab
eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --wait --timeout=45m
aws eks wait cluster-deleted --name "$CLUSTER_NAME" --region "$AWS_REGION"
# Keep private config/identity records until remaining resources/billing are checked.
```

`--wait` is required to surface deletion failures. An EKS deletion waiter confirms the control-plane object is gone, not that every dependent resource or charge has disappeared. Inspect the saved lab's CloudFormation stack status and any remaining tagged EC2/EBS/NAT/VPC resources, including `DELETE_FAILED` or retained resources. Keep local identity/configuration evidence until that check is complete. Do not substitute a fixed sleep for deletion verification.

If creation never reached identity capture, use the private intent record and CloudFormation events/tags for manual ownership verification. Do not invent a `cluster-identity.json` merely to make the guard pass.

## Troubleshooting

<details>
<summary>Cluster creation fails</summary>

Check the approved role permissions, service quotas, subnet/IP capacity and instance availability in the chosen region. eksctl uses CloudFormation; inspect the actual failure rather than granting broad administrator access as a default fix.

```bash
check_account
eksctl utils describe-stacks --region "$AWS_REGION" --cluster "$CLUSTER_NAME"
```

Retain the private lab directory during partial-creation recovery. Review any proposed deletion against actual ownership before executing it.

</details>

<details>
<summary>kubectl cannot connect</summary>

Check role credentials, access entries, DNS and whether the workstation's current egress address is still in the approved CIDR. If the private kubeconfig needs rebuilding, first verify the cluster identity and then write only this lab's path:

```bash
check_account
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
check_lab
```

Do not widen endpoint access to the entire internet to work around a changed client address.

</details>

## References

- [EKS supported versions](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS upgrade policy](https://docs.aws.amazon.com/eks/latest/userguide/view-upgrade-policy.html)
- [Cluster endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [eksctl IAM permissions](https://docs.aws.amazon.com/eks/latest/eksctl/minimum-iam-policies.html)
- [eksctl creation/deletion](https://docs.aws.amazon.com/eks/latest/eksctl/creating-and-managing-clusters.html)
- [kubectl version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Port forwarding](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
- [Official nginx image definitions](https://github.com/docker-library/official-images/blob/master/library/nginx)

## Next Steps

- [EKS Cluster Creation Quiz](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- [EKS Networking](../../eks/03-eks-networking-part1.md)
