# EKS Cluster Creation Quiz - Part 2

> **Last Updated**: September 11, 2026

> Question examples are independent alternatives. Use the Part 1 prerequisites and an explicitly selected training account/cluster. Within an exercise, run its steps in order in the same Bash session. Cloud/host commands below were reviewed but were not executed against AWS or nodes during this audit.

This quiz tests your understanding of advanced concepts, security settings, and networking configurations related to Amazon EKS cluster creation. It covers topics such as cluster security, network policies, and service accounts.

## Basic Concept Questions

1. What is the main purpose of IRSA in an EKS cluster?
   * A) Grant Kubernetes administrator access
   * B) Assign the EC2 node IAM role
   * C) Give workloads temporary AWS permissions through their Kubernetes service account
   * D) Modify the EKS control-plane role

<details>
<summary>Show Answer</summary>

**Answer: C) Give workloads temporary AWS permissions through their Kubernetes service account**

IRSA lets a workload obtain temporary AWS credentials using its Kubernetes service-account identity. The IAM role's permission policy determines which AWS operations it can perform. This is separate from Kubernetes RBAC and the IAM roles used by the EKS control plane or EC2 nodes.

**Trust flow:** EKS issues a projected service-account token. Register the cluster's actual OIDC issuer as an IAM OIDC provider, then trust the intended audience and namespace/service-account subject. A supported AWS SDK's default credential chain exchanges that token through STS `AssumeRoleWithWebIdentity`. Use the real provider ARN/issuer and exact service-account identity in this example:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:irsa-lab:my-service-account"
      }
    }
  }]
}
```

Annotate the service account with the role ARN and reference it in the Pod. Create an unused `irsa-lab` namespace first. These two manifests are an alternative to eksctl-managed service-account creation below; do not overwrite another application's service account:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: irsa-lab
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ReviewedIrsaRole
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: irsa-identity-check
  namespace: irsa-lab
spec:
  serviceAccountName: my-service-account
  restartPolicy: Never
  containers:
    - name: aws-cli
      image: public.ecr.aws/aws-cli/aws-cli:2.36.43
      command: ["aws"]
      args: ["sts", "get-caller-identity"]
```

The Pod uses a verified AWS CLI v2 image tag and prints its caller identity, not secret access keys or the web-identity token. Confirm that the returned role is the intended workload role. STS identity success alone does not prove access to S3 or any other target resource; test the required operation separately, as in exercise 1.

**eksctl alternative:** use a policy limited to the intended resources/actions, not a broad AWS-managed S3 policy for a single-bucket task. Review existing service accounts and role ownership first; do not add `--override-existing-serviceaccounts` as a generic fix.

```bash
# For a new service account and dedicated role, with a reviewed scoped policy.
eksctl utils associate-iam-oidc-provider \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
KUBECONFIG="${EXAMPLE_KUBECONFIG:?}" eksctl create iamserviceaccount \
  --name "${IRSA_SERVICE_ACCOUNT:?}" --namespace "${IRSA_NAMESPACE:?}" \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --attach-policy-arn "${SCOPED_POLICY_ARN:?}" --approve
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get serviceaccount "$IRSA_SERVICE_ACCOUNT" -o yaml
```

**Limits and responsibilities:**

- Use a supported SDK and its credential chain. Hardcoded credentials or earlier providers in the chain can override IRSA. The webhook injects role/token-file configuration; the SDK refreshes temporary credentials. Do not print or copy token/credential values.
- IRSA does not itself block access to node IMDS, and containers sharing a node are not a hard security boundary. Restrict IMDS and node permissions separately; `hostNetwork` Pods can still reach IMDS.
- IAM conditions scope role assumption, but anyone allowed to create a Pod using that service account may gain its AWS permissions. Control Kubernetes workload/service-account administration as well.
- EKS Pod Identity is another workload-identity option with its own support requirements. Its EKS Auth/agent credential flow differs from IRSA's OIDC/STS flow.
- Cluster users use EKS access entries/policies or the legacy `aws-auth` mapping where configured. These authorize Kubernetes access; they do not replace workload IAM permission policies.

References: [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html), [assign a service-account role](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [SDK requirements](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html), [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html).

</details>

2. What do AWS security groups control in an EKS design?
   * A) Kubernetes resource authorization
   * B) Permitted network traffic at associated interfaces, including supported Pod interfaces
   * C) Service-account token audiences
   * D) The number of replicas in a Deployment

<details>
<summary>Show Answer</summary>

**Answer: B) Permitted network traffic at associated interfaces, including supported Pod interfaces**

Security groups are stateful network filters associated with network interfaces. In EKS they help control traffic among cluster interfaces, nodes and, with the supported Security Groups for Pods feature, selected Pods. They do not implement Kubernetes RBAC or authenticate users.

**Default and required rules are different.** EKS creates `eks-cluster-sg-<cluster>-<id>` with self-referencing inbound rules, broad outbound access and a self-referencing outbound rule used for EFA. These are defaults to inspect, not a minimum-privilege recipe. EKS associates the cluster group with its cluster interfaces and normally with managed-node interfaces; custom launch-template security groups change that behavior.

If restricting the default outbound rules, retain the documented minimum traffic and the additional dependencies of your actual workloads:

| Required cluster-group outbound traffic | Destination |
| --- | --- |
| TCP 443 | Cluster security group |
| TCP 10250 | Cluster security group |
| TCP and UDP 53 | Cluster security group |

This table alone is not a complete network design. Review node-to-node/application ports, API and registry access, S3, DNS paths and IPv4/IPv6 rules. Private endpoints can provide AWS connectivity without general internet egress. EKS can recreate self-referencing rules during cluster updates, so do not describe their removal as a permanent restriction.

**Additional groups:** groups specified in a cluster's `resourcesVpcConfig.securityGroupIds` attach to cluster network interfaces; they do not automatically attach to node groups. If a node launch template supplies custom security groups, EKS does not also add the cluster security group, and the custom groups must permit required node/API traffic.

The following AWS CLI example shows selecting an additional group for a new control plane. It does not create node capacity or operator access entries. The provisioning identity needs permission to create the required operator access entry because automatic creator-admin access is disabled:

```bash
# Cluster creation fragment: use reviewed roles/subnets/groups and a new name.
aws eks create-cluster --name "${NEW_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --version 1.36 \
  --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API,bootstrapClusterCreatorAdminPermissions=false \
  --resources-vpc-config "subnetIds=${PRIVATE_SUBNET_A:?},${PRIVATE_SUBNET_B:?},securityGroupIds=${ADDITIONAL_CONTROL_PLANE_SG:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"
```

The equivalent eksctl networking fields belong in the full reviewed configuration from [Part 2](../../eks/02-eks-cluster-creation-part2.md). Replace the documentation CIDR and all IDs:

```yaml
# Networking example; merge into a reviewed full ClusterConfig.
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"
vpc:
  id: vpc-0123456789abcdef0
  controlPlaneSecurityGroupIDs:
    - sg-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
```

**Public versus private API:** the public Kubernetes endpoint is restricted with `publicAccessCidrs`, not the cluster security group. Cluster security-group rules govern private endpoint traffic. Neither a CIDR allowlist nor a security-group rule grants IAM/RBAC authorization.

**Security groups for Pods:** on supported compute, configure the feature and required IAM/VPC CNI settings before creating a `SecurityGroupPolicy`. Check instance trunking compatibility, CNI version, enforcement mode, DNS and actual security-group rules. Windows and EKS Auto Mode do not support this feature; EC2 `t` instance families are not supported. Fargate has its own supported setup.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: application-sg
  namespace: sg-lab
spec:
  podSelector:
    matchLabels:
      app: my-app
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

The policy selects Pods in a separately created `sg-lab` namespace; a CRD object alone does not prove security-group attachment. Standard/strict Pod security-group modes and SNAT affect which group filters traffic outside the VPC. Verify the documented mode-specific behavior for your setup.

Kubernetes NetworkPolicy is a separate mechanism enforced by a configured network plugin. Pod traffic is not automatically default-denied merely because a cluster supports NetworkPolicy. See question 3 for a deliberate policy configuration.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,publicAccess:endpointPublicAccess,privateAccess:endpointPrivateAccess,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_SECURITY_GROUP_ID:?}"
```

References: [cluster security groups](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html), [API endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [security groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html).

</details>

3. What is required to enforce Kubernetes NetworkPolicy in EKS?
   * A) Only a security-group rule
   * B) A supported and enabled policy implementation, such as Amazon VPC CNI, Calico or Cilium
   * C) Only VPC Flow Logs
   * D) A NetworkPolicy object with no enforcing implementation

<details>
<summary>Show Answer</summary>

**Answer: B) A supported and enabled policy implementation, such as Amazon VPC CNI, Calico or Cilium**

A configured network-policy implementation is required; creating a `NetworkPolicy` object alone does not enforce traffic rules. **Amazon VPC CNI supports NetworkPolicy**, so Calico or Cilium is not mandatory just to obtain this feature.

**Amazon VPC CNI path:** verify the supported cluster/platform, Linux kernel and CNI version, then enable its network-policy feature through the add-on's owning configuration. Current AWS guidance uses VPC CNI 1.21.0+ for both standard and admin policies and Linux kernel 5.10+. Earlier historical minimum versions are not upgrade targets for a current cluster.

```bash
aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --query 'addon.{version:addonVersion,status:status,configuration:configurationValues}'
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_CNI_VERSION:?}" \
  --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  get daemonset aws-node -o jsonpath='{.spec.template.spec.containers[*].name}{"\n"}'
```

For the EKS-managed add-on, the relevant configuration value is:

```json
{
  "enableNetworkPolicy": "true"
}
```

Merge this into the **full reviewed configuration**, preserving required existing settings; supplying a new `configurationValues` document is not a JSON patch. Do not downgrade the add-on or overwrite an EKS-managed DaemonSet with an old upstream manifest. For a Helm/self-managed installation, use that installation's documented configuration instead.

In standard startup mode, a new Pod can initially allow traffic until its policy is programmed. Strict mode starts with default deny, but requires all necessary connectivity policies, including CoreDNS dependencies, to be prepared. Do not switch an existing cluster blindly to strict mode.

**Alternative implementations:**

- **Calico with Amazon VPC networking:** keep AWS IPAM/CNI and configure the operator's `Installation` for `AmazonVPC`. Follow the pinned operator/CRD instructions and AWS Pod-IP annotation/RBAC prerequisites in the official EKS guide. Disable AWS's own policy enforcement for that Calico path; installing only the operator or an arbitrary VXLAN manifest is not the same design.

```yaml
# Installation resource for the Amazon VPC networking path, after operator/CRDs.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
```

- **Cilium with Amazon VPC CNI:** the documented chaining configuration is required; merely disabling tunnels/masquerading does not set up chaining. The following values are a reference from the released 1.20.1 guide. Check release/cluster compatibility and complete the guide's prerequisites. Existing Pods must be recreated through a controlled rollout for the new chaining path to take effect.

```yaml
# Relevant Helm values from the Cilium 1.20.1 AWS-CNI chaining guide.
# This is not a complete install or migration command.
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
```

Choose and validate the intended enforcement implementation rather than stacking unreviewed CNI/policy installations. Replacing an implementation can leave node-level rules behind and needs a planned migration.

**Policy example:** in a newly created `policy-lab` namespace, allow frontend-to-backend TCP 8080 and DNS while denying other traffic. The backend must actually listen on 8080. For the AWS implementation, use the same Service and container port. The DNS selectors below assume conventional CoreDNS Pods in `kube-system`; NodeLocal DNSCache or custom DNS needs different reviewed rules.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Egress]
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

Both frontend egress and backend ingress are allowed because both endpoints are otherwise isolated. Multiple standard NetworkPolicies add their allowed traffic; the default-deny object does not override an allow rule. DNS is allowed for the test namespace so a denied application connection is not confused with a DNS failure.

**Meaningful verification:** use Deployment-managed frontend, backend and unrelated-client Pods. AWS documents that enforcement may be unreliable for standalone Pods without `metadata.ownerReferences`, so do not use a bare `kubectl run` Pod as your only proof. Establish baseline connectivity, apply the policies, then verify frontend succeeds and the unrelated client fails while DNS still works. Test fresh connections after policy convergence. Merely finding CNI Pods or successfully applying YAML is insufficient.

AWS VPC CNI policy enforcement applies to supported EC2 Linux nodes, not Windows or Fargate. It applies to the Pod's primary interface and cluster IP family; additional interfaces and IPv4 egress from IPv6 Pods have limitations. Security groups, Network Firewall and flow logs serve different purposes and do not replace this Kubernetes policy configuration.

References: [VPC CNI policy configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [AWS policy limitations](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [Calico on EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks), [Cilium 1.20.1 chaining source](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst), [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

4. Which statement correctly describes encryption at rest for Kubernetes API data on EKS 1.28 or later?
   * A) Envelope encryption is enabled by default; a customer-managed KMS key is optional
   * B) Every cluster must be recreated before Secrets can be encrypted
   * C) Base64 encoding provides encryption at rest
   * D) An application sidecar must encrypt the EKS control-plane database

<details>
<summary>Show Answer</summary>

**Answer: A) Envelope encryption is enabled by default; a customer-managed KMS key is optional**

EKS clusters running Kubernetes **1.28 or later** have KMS v2 envelope encryption for **all Kubernetes API data** by default, using an AWS owned key unless a customer-managed KMS key is associated. Secrets are included, as are ConfigMaps and other stored API resources. This is additional to etcd disk encryption, and does not encrypt application data on nodes or EBS volumes.

**Inspect before changing anything.** A missing customer-managed key ARN in `encryptionConfig` does not mean Secrets are unencrypted. The console identifies the AWS owned key mode without revealing that key's ARN.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status,encryption:encryptionConfig}'

# Optional CMK inspection, only when a customer-managed key is required.
aws kms describe-key --key-id "${KMS_KEY_ARN:?Reviewed customer-managed key ARN}" \
  --region "$EXAMPLE_REGION" \
  --query 'KeyMetadata.{arn:Arn,state:KeyState,spec:KeySpec,usage:KeyUsage}'
```

**Optional customer-managed key (CMK).** Use a symmetric encryption key in the cluster's Region when your requirements call for customer key control. Verify key availability, the caller's IAM permissions, key policy/grants and cross-account permissions if applicable. A generic policy that grants only `eks.amazonaws.com` several KMS actions is not a complete setup: the provisioning/association identity needs the documented `kms:DescribeKey` and `kms:CreateGrant` permissions. The `kms:GrantIsForAWSResource` condition is not supported for controlling `CreateGrant` during `CreateCluster`.

You can supply a provider in `CreateCluster` or associate a CMK with an eligible existing cluster using `AssociateEncryptionConfig`; creating another cluster is not inherently required. Do not use this as a general key-replacement or encryption-disable operation. Clusters already associated with a CMK need their supported key-management procedure.

```bash
# Optional CMK association for an eligible existing cluster.
# Review current configuration, key policy/grants and recovery procedures first.
KMS_CONFIG_DIR=$(mktemp -d /tmp/eks-kms-config.XXXXXX)
: "${KMS_CONFIG_DIR:?}"
jq -n --arg arn "${KMS_KEY_ARN:?}" \
  '[{resources:["secrets"],provider:{keyArn:$arn}}]' \
  > "$KMS_CONFIG_DIR/encryption.json" || exit 1
if ENCRYPTION_UPDATE_ID=$(aws eks associate-encryption-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --encryption-config "file://$KMS_CONFIG_DIR/encryption.json" \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$ENCRYPTION_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

Record the update ID and check until `Successful` or a failure; request acceptance alone is not completion. The retained `resources: ["secrets"]` field is accepted for compatibility. On EKS 1.28+, it does **not** restrict encryption to Secrets: the field is deprecated and all Kubernetes API data is envelope encrypted. Current APIs also accept an omitted/null/empty resources list, while responses retain the legacy `["secrets"]` value. The old `enable-kms` walkthrough for Kubernetes 1.27 and earlier is historical guidance, not a supported-version migration target.

Do not disable or delete an associated key as lab cleanup while the cluster exists. Key unavailability can degrade the control plane, and permanent key loss can make the cluster unrecoverable. Review key recovery, access and monitoring before choosing a CMK. Default AWS owned key encryption needs no customer key setup; a CMK has separate KMS charges.

**Using Secrets does not change.** Authorized API clients and Pods receive usable values; encryption at rest does not replace RBAC, workload identity or protection of logs/backups. The following manifest intentionally contains public dummy data and is not a production secret:

```yaml
# Public dummy data for a newly created secrets-lab namespace only.
apiVersion: v1
kind: Secret
metadata:
  name: example-credentials
  namespace: secrets-lab
type: Opaque
stringData:
  username: example-user
  password: public-training-placeholder
```

```bash
# Inspect keys and metadata without printing values.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  -n secrets-lab get secret example-credentials -o json |
  jq '{name:.metadata.name,type:.type,keys:(.data|keys)}'
```

For real credentials, avoid committing manifests with plaintext or base64 values, shell-history literals and value-dumping diagnostics. Base64 is reversible encoding. AWS Secrets Manager can integrate through CSI-mounted files or a controller that synchronizes Kubernetes Secrets; every application does not necessarily need SDK changes. A synchronized Secret remains subject to Kubernetes access controls. A sidecar cannot configure the managed API server's at-rest encryption.

References: [default envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [AssociateEncryptionConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_AssociateEncryptionConfig.html), [legacy KMS procedure and permissions](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html), [Secrets Manager on EKS](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html).

</details>

5. How should kubelet settings be customized for AL2023 EC2 managed nodes?
   * A) Edit the EKS control-plane kubelet in the console
   * B) Use a supported nodeadm NodeConfig through eksctl or launch-template user data
   * C) Change status.capacity with kubectl edit node
   * D) Run the AL2 bootstrap.sh script on every AL2023 boot

<details>
<summary>Show Answer</summary>

**Answer: B) Use a supported nodeadm NodeConfig through eksctl or launch-template user data**

For **AL2023 EC2 nodes**, use `nodeadm`'s `NodeConfig` and the supported eksctl/launch-template integration. Do not use the AL2 `/etc/eks/bootstrap.sh` procedure or an assumed `eksctl create nodegroup --kubelet-extra-args` flag. The old `kubeletExtraArgs` map is not the supported managed-node-group field in this example.

**eksctl:** for AL2023, `overrideBootstrapCommand` contains a YAML `NodeConfig`, despite its name. eksctl prepends it to user data for nodeadm to merge with the generated node configuration. With an EKS-selected native AMI, EKS supplies the cluster's required default configuration. Review the effective merged settings on a test node before wider rollout:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-kubelet
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
    overrideBootstrapCommand: |
      apiVersion: node.eks.aws/v1alpha1
      kind: NodeConfig
      spec:
        kubelet:
          config:
            kubeReserved:
              cpu: 100m
              memory: 300Mi
            systemReserved:
              cpu: 200m
              memory: 512Mi
            evictionHard:
              memory.available: 500Mi
            mergeDefaultEvictionSettings: true
```

The resource reservations and 500 MiB eviction threshold above are **illustrative**, not measured recommendations. They reduce Pod allocatable capacity and can cause evictions if unsuitable. `mergeDefaultEvictionSettings: true` is supported in Kubernetes 1.36 and preserves unspecified default eviction signals when kubelet processes a partial eviction map. Without appropriate merging, specifying only one signal can unintentionally zero other default thresholds.

**Custom AMI/launch-template route:** when supplying your own AMI ID outside the eksctl-generated configuration, provide complete cluster metadata: name, API endpoint, base64 CA and service CIDR. Reuse the metadata-generation procedure in [Part 1 quiz, advanced question 5](02-eks-cluster-creation-part1-quiz.md#advanced-topics), and add reviewed `spec.kubelet.config` settings to that NodeConfig. A partial kubelet-only object is not a complete standalone bootstrap configuration.

AL2023 runs `nodeadm-config` before user data and `nodeadm-run` afterward. Do not run `nodeadm init` again or manually start/reconfigure kubelet in a way that conflicts with those services. Other OS families, including Bottlerocket and Windows, use different configuration mechanisms; these examples do not apply to EKS Auto Mode nodes.

| Setting | What to verify |
| --- | --- |
| `maxPods` / nodeadm `maxPodsExpression` | Instance ENI/IP limits, CNI mode, prefix delegation and supported density; do not force a universal value of 110 |
| Node labels and taints | Prefer managed node-group fields; use your own label prefix rather than overwriting EKS/AZ labels |
| `kubeReserved`, `systemReserved` | Actual host/system workload requirements and Node Allocatable |
| `evictionHard`, soft thresholds | Memory/disk/inode signals and default-merging behavior; do not disable unrelated protections |
| Cgroup driver | Compatibility with the selected OS and container runtime; retain the tested AMI defaults unless a reviewed change is needed |

**Validation:** inspect Node capacity/allocatable and the effective service configuration/logs. Node readiness alone does not prove every custom value was applied. This audit checked the configuration syntax and official field definitions; it did not boot a node with these settings.

```bash
# Kubernetes-side checks through the intended cluster context.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" describe node "${EXAMPLE_NODE_NAME:?}"

# Run separately on a specifically authorized AL2023 test node.
sudo systemctl status nodeadm-config nodeadm-run kubelet --no-pager
sudo systemctl cat kubelet
sudo journalctl -u nodeadm-config -u nodeadm-run -u kubelet --since '-15 min' --no-pager
```

Use the configured service's actual config path rather than assuming every AMI has `/etc/systemd/system/kubelet.service.d/10-kubelet-args.conf`. Limit and protect diagnostic logs as appropriate.

`kubectl edit node` can change Node metadata but does not set the kubelet's startup configuration. SSM can run host commands, but an ad hoc host edit is not a durable managed-node replacement configuration and may require disruptive restarts. Put reviewed settings into the provisioning configuration and replace/test nodes deliberately.

References: [eksctl AL2023 bootstrapping](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [AL2023 services](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [nodeadm API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/), [KubeletConfiguration](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/), [Kubernetes 1.36 field definitions](https://github.com/kubernetes/kubelet/blob/v0.36.0/config/v1beta1/types.go).

</details>

6. Which mechanisms can replace removed PodSecurityPolicy controls in EKS?
   * A) EC2 security groups alone
   * B) Pod Security Admission and, where needed, a compatible policy engine
   * C) CloudWatch log retention alone
   * D) An IAM user access key stored in each Pod

<details>
<summary>Show Answer</summary>

**Answer: B) Pod Security Admission and, where needed, a compatible policy engine**

PodSecurityPolicy was deprecated in Kubernetes 1.21 and removed in 1.25. Use built-in **Pod Security Admission (PSA)** to enforce **Pod Security Standards (PSS)**, and use an appropriate policy engine for requirements beyond those controls.

**PSA:** Privileged, Baseline and Restricted are the three PSS levels; `enforce`, `audit` and `warn` are separate modes. For a newly created lab namespace, this example enforces Baseline while reporting Restricted violations. The policy version is pinned to the EKS 1.36 example; choose a version supported by the actual cluster.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: policy-engine-lab
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```

Do not blindly relabel an existing shared namespace. Audit/warn first, fix workload manifests, and then tighten enforcement. PSA does not mutate Pods into compliance or evict already running Pods. It evaluates Pod admission; warnings/audit on workload templates help identify violations before their controllers attempt to create Pods.

**Kyverno:** chart 3.9.1 packages controller 1.19.1 in this audited example. Kyverno 1.19 deprecates the legacy `ClusterPolicy`/`Policy` types and its migration guide schedules their removal in 1.20. New examples should use the current CEL-based policy APIs. Migrate existing policies before an incompatible upgrade rather than changing only the controller version.

```bash
# Optional new installation; review existing controllers and release compatibility.
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

The following `policies.kyverno.io/v1` **ValidatingPolicy** rejects `privileged: true` in regular, init and ephemeral containers, and matches only the lab namespace. It permits the field to be absent or false:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```

This demonstrates one control, not the whole Baseline or Restricted standard. The policy engine/CRDs must be ready before applying the policy, and live admission/subresource behavior must be verified in the intended cluster. Background evaluation reports existing violations; it does not evict running workloads.

**OPA Gatekeeper alternative:** install a reviewed Gatekeeper release if its policy model fits your requirements. This example pins chart/controller 3.23.1:

```bash
# Alternative policy-engine example, not a prerequisite for the Kyverno example.
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

Gatekeeper first needs a `templates.gatekeeper.sh/v1` ConstraintTemplate. Wait for the template and generated constraint CRD to be established before applying the matching Constraint. The Rego example below checks the same three container lists and scopes the Constraint to the lab namespace:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: "package k8snoprivilegedlab\n\ncontainers[c] {\n  c := input.review.object.spec.containers[_]\n\
      }\ncontainers[c] {\n  c := input.review.object.spec.initContainers[_]\n}\ncontainers[c]\
      \ {\n  c := input.review.object.spec.ephemeralContainers[_]\n}\nviolation[{\"\
      msg\": msg}] {\n  c := containers[_]\n  c.securityContext.privileged == true\n\
      \  msg := sprintf(\"Privileged container is not allowed: %v\", [c.name])\n}\n"
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```

Gatekeeper `enforcementAction: deny` rejects matching violations; `dryrun` or `warn` can support a staged rollout. A template without its Constraint is not an enforced policy. Use the API/schema and Rego mode supported by the installed release.

**Validation and limits:** the Kyverno 1.19.1 CLI (with warnings treated as errors) and Gatekeeper 3.23.1 Gator were run locally on six cases each: explicit false, omitted field, privileged regular/init/ephemeral containers, and an out-of-scope namespace. Both policy implementations produced the intended local results. No cluster installation or live admission test was performed.

```bash
# Offline policy logic checks using locally reviewed fixture files.
kyverno apply kyverno-policy.yaml --resource test-pod.yaml --warnings-as-errors
gator test --filename gatekeeper-policy.yaml --filename test-pod.yaml --output=json
```

Do not infer that a live rejection came from one particular engine when PSA or another webhook would also reject it. Verify policy/controller status, target scope, actual admission responses and reports. Use the full control set for host namespaces, hostPath, capabilities, privilege escalation and other PSS requirements.

AWS Security Hub, AWS Config and EC2 security groups have different roles; enabling them is not a replacement for Kubernetes Pod admission enforcement.

References: [PSA](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [PSS](https://kubernetes.io/docs/concepts/security/pod-security-standards/), [Kyverno CEL migration](https://kyverno.io/docs/guides/migration-to-cel/), [Kyverno 1.19.1](https://github.com/kyverno/kyverno/releases/tag/v1.19.1), [Gatekeeper 3.23.1 how-to](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/howto.md).

</details>

7. Which IAM identity-provider prerequisite is required for IRSA's web-identity trust?
   * A) An IAM user access key stored in every Pod
   * B) A cluster-admin RoleBinding
   * C) An IAM OIDC provider matching the cluster issuer
   * D) A public IP on each worker node

<details>
<summary>Show Answer</summary>

**Answer: C) An IAM OIDC provider matching the cluster issuer**

IRSA needs an IAM OIDC provider that matches the target cluster's issuer. Check whether it already exists; do not create duplicate providers or reuse another cluster's issuer. This prerequisite must be satisfied before the workload can assume its IAM role, but the service account itself can be created before the role and annotated later. There is no universal requirement that every resource be created in exactly the same order.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.identity.oidc.issuer --output text
eksctl utils associate-iam-oidc-provider \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --approve
```

Use eksctl or the current IAM OIDC-provider procedure instead of copying an old fixed certificate thumbprint. Configure `sts.amazonaws.com` as the intended client ID/audience. In a VPC without internet egress, setting up the provider from inside the VPC can require the separate `oidc-eks` interface endpoint/private DNS or another reachable administration path. IRSA's token exchange separately requires regional STS connectivity.

Then create the scoped role policy and the trust policy from question 1 with both `aud` and `sub`; annotate the correct service account and create a new Pod that references it. Existing Pods do not acquire newly injected configuration merely because a service-account annotation changes; recreate them through their normal controller rollout.

For an identity check, use the explicit Pod manifest from question 1. `kubectl run --serviceaccount` is not a supported current flag:

```bash
# After deploying the identity-check Pod from question 1.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n irsa-lab \
  get pod irsa-identity-check -o jsonpath='{.status.phase}{"\n"}'
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n irsa-lab logs irsa-identity-check
```

Check the Pod exit status and compare the returned account/assumed-role identity with the expected role. A node-role identity is not proof of working IRSA. Test only the scoped application operation next; `aws s3 ls` without a bucket would require listing all buckets and is inappropriate for a single-bucket policy.

EKS Pod Identity uses a different mechanism and does not require creating an IAM OIDC provider for each cluster. Keep its service account association, agent and IAM trust requirements separate from IRSA.

References: [create an IAM OIDC provider](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html), [IRSA private connectivity](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [Pod configuration](https://docs.aws.amazon.com/eks/latest/userguide/pod-configuration.html).

</details>

8. How do you enable EKS control-plane log export?
   * A) Install an agent on the managed control-plane hosts
   * B) Configure cluster logging through EKS APIs, console or eksctl
   * C) Install Fluentd on worker nodes only
   * D) SSH to the managed API server and edit its configuration

<details>
<summary>Show Answer</summary>

**Answer: B) Configure cluster logging through EKS APIs, console or eksctl**

Enable EKS control-plane log export through the EKS API, console or eksctl. AWS operates the control-plane hosts; installing CloudWatch/Fluentd agents on worker nodes does not enable those control-plane logs. Operators cannot SSH to the managed control-plane hosts.

**AWS CLI:** inspect the current settings and choose the needed types. This is an asynchronous update: record its ID and repeat `describe-update` until it succeeds or reports a failure. EKS can require up to five free IP addresses in each cluster subnet for a logging update.

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

To enable only API/audit and explicitly disable the other three types, use the following **alternative** logging payload after reviewing audit/retention requirements. Do not run both configurations sequentially or disable required logs just to reduce cost:

```json
{
  "clusterLogging": [
    {"types": ["api", "audit"], "enabled": true},
    {"types": ["authenticator", "controllerManager", "scheduler"], "enabled": false}
  ]
}
```

**eksctl alternative:** the preview and apply operations are distinct; `--approve` is required to apply the reviewed change. `--disable-types` can explicitly disable selected types when that is intended.

```bash
# Alternative interface; do not submit a second update while one is running.
# Without --approve this previews the logging change.
eksctl utils update-cluster-logging \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --enable-types api,audit,authenticator,controllerManager,scheduler

# Apply the reviewed change.
eksctl utils update-cluster-logging \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

**Console:** select the cluster, open **Observability**, and use **Control plane logging → Manage logging**. Choose each log type and save the reviewed configuration.

| Type | Purpose | Stream prefix |
| --- | --- | --- |
| `api` | API-server component diagnostics; initial flags are available only if captured before log rotation | `kube-apiserver-` |
| `audit` | Kubernetes API activity recorded under the managed audit policy | `kube-apiserver-audit-` |
| `authenticator` | IAM authentication diagnostics | `authenticator-` |
| `controllerManager` | Built-in Kubernetes control-loop diagnostics | `kube-controller-manager-` |
| `scheduler` | Pod scheduling diagnostics | `kube-scheduler-` |

Audit logs are not a record of every application request or every process/network action on a node. CloudTrail records relevant AWS API activity separately. Control-plane log delivery is best effort, normally within minutes; enabling it does not recover already rotated logs.

**Verify export:** logs are in `/aws/eks/<cluster-name>/cluster` in the cluster's account/Region. Stream suffixes rotate, so inspect recent event times instead of assuming a single permanent stream name.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.logging
aws logs describe-log-streams --region "$EXAMPLE_REGION" \
  --log-group-name "/aws/eks/$EXAMPLE_CLUSTER/cluster" \
  --order-by LastEventTime --descending --max-items 10
```

CloudWatch ingestion, storage and queries have costs. Set retention/access controls to your requirements and verify that required log types are actually arriving. A successful configuration update is not proof that every expected historical event is present. Worker/application log collectors remain a separate data-plane concern.

Reference: [EKS control-plane logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

9. How do you change instance types that were specified in the EKS managed node-group request, without a custom-template instance type?
   * A) Edit the instanceTypes field in place in the console
   * B) Create a replacement node group and validate workload migration
   * C) Use kubectl edit node to change the EC2 hardware
   * D) Pass new instance types to update-nodegroup-config

<details>
<summary>Show Answer</summary>

**Answer: B) Create a replacement node group and validate workload migration**

This question concerns instance types specified in the **managed node-group request**, rather than in a custom launch template. Those types cannot be changed with `update-nodegroup-config`; create a new group and migrate workloads.

A separate path exists when the group was created with a custom launch template and the instance type is defined there: review a new version of the **same** template and apply it with `update-nodegroup-version`. Instances are still replaced. Do not modify EKS-generated templates, specify types in both locations, or assume a different CPU architecture will work with the same AMI/images.

**1. Create replacement capacity.** Check instance offerings, quotas, architecture, CNI/IP capacity, AZs, storage and node-role permissions. The two commands are alternatives for an existing test cluster:

```bash
# Alternative 1: eksctl, for an unused managed node-group name.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name "${NEW_NODEGROUP_NAME:?}" \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large --nodes 3 --nodes-min 1 --nodes-max 5 \
  --node-labels "example.com/migration-target=true"

# Alternative 2: AWS CLI; do not run both for the same node group.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=1,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/migration-target":"true"}'
```

**2. Verify the new group.** Wait for `ACTIVE`, healthy `Ready` nodes and working CNI/DNS. Listing labels alone does not prove application readiness:

```bash
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --query 'nodegroup.{status:status,health:health,types:instanceTypes,subnets:subnets}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l example.com/migration-target=true -o wide
```

**3. Migrate and test.** Choose an application-specific rolling or blue/green plan. A Service sends traffic to selected ready Pod endpoints, not directly to a node-group name. Retain old capacity until rollback needs and data compatibility are understood.

For manual draining, select one old node, confirm its node-group label and check PDBs, spare capacity and local storage first. This example intentionally does not bypass eviction or discard `emptyDir` data. If drain fails, inspect the cause before continuing; the node can remain cordoned.

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```

Alternatively, update the actual application's Pod template to select the replacement group. The complete example below is a separate demonstration for a newly created `migration-lab` namespace, not a replacement manifest for an existing application:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: migration-demo
  template:
    metadata:
      labels:
        app: migration-demo
    spec:
      nodeSelector:
        example.com/migration-target: "true"
      containers:
        - name: nginx
          image: nginx:1.30.4
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: migration-demo
```

The PDB requires two healthy matching Pods during voluntary eviction. With three replicas, one can normally be evicted at a time if the other conditions allow it. It does not guarantee availability, protect against direct deletions or preserve node-local data. Check placement, readiness, service routing, persistent-volume AZ affinity and backups using representative workload tests.

**4. Retire the old group only after validation.** Do not run both eksctl and AWS deletion commands or bypass PDBs to complete migration. Review the target cluster/group and remove only the group owned by this migration:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```

Keep the old group if application validation fails. Blue/green temporarily adds capacity and cost; it does not guarantee easy rollback for stateful changes. `kubectl edit node` changes Kubernetes metadata, not the underlying EC2 instance type.

References: [launch-template updates](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [UpdateNodegroupConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_UpdateNodegroupConfig.html), [drain](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/).

</details>

10. Which statement about EKS managed node-group taints is correct?
   * A) Only kubectl can configure taints
   * B) Use node-group configuration through the console/API or eksctl; verify existing Node state separately
   * C) The EKS console cannot configure taints
   * D) A toleration guarantees placement onto the matching tainted group

<details>
<summary>Show Answer</summary>

**Answer: B) Use node-group configuration through the console/API or eksctl; verify existing Node state separately**

Managed node-group taints can be configured through the EKS console/API or an eksctl configuration file. The console is a valid method, so a quiz must not mark it incorrect merely because a CLI method also exists. Direct `kubectl taint` changes an individual Node object and is not the persistent configuration of replacement nodes in a managed group.

**eksctl configuration:** save this as a reviewed node-group configuration for an existing cluster and an unused group name, then use `eksctl create nodegroup -f nodegroup.yaml`. Use the supported `taints` field rather than an assumed CLI flag.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    labels:
      example.com/pool: batch
    taints:
      - key: dedicated
        value: batch
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
```

**AWS CLI alternative:** Kubernetes/eksctl effect names use CamelCase, but the EKS API uses uppercase names:

| Kubernetes / eksctl | EKS API | Effect |
| --- | --- | --- |
| `NoSchedule` | `NO_SCHEDULE` | Scheduler rejects new Pods without a matching toleration; existing Pods remain |
| `PreferNoSchedule` | `PREFER_NO_SCHEDULE` | Soft scheduling preference, not a guarantee |
| `NoExecute` | `NO_EXECUTE` | Also evicts existing Pods without a matching toleration; `tolerationSeconds` can delay eviction |

```bash
# Alternative to the eksctl file: create a new group through the EKS API.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/pool":"batch"}' \
  --taints '[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"},{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
```

```bash
# Separate update example for the intended existing group.
if TAINT_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --taints '{"addOrUpdateTaints":[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"}],"removeTaints":[{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$TAINT_UPDATE_ID" \
    --query 'update.{status:status,errors:errors}'
fi
```

The update is asynchronous; wait for its successful completion and inspect actual Node taints. EKS does **not** automatically add a managed-group taint back if someone manually removes it from an existing Node, even when the group configuration still lists it. Restrict who can modify nodes and verify the state after changes.

**Dedicated workload placement:** a toleration permits scheduling but does not force a Pod onto the tainted group. Combine it with an appropriate node selector/affinity. This complete demonstration uses a new `taint-lab` namespace:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: batch-example
  namespace: taint-lab
spec:
  nodeSelector:
    example.com/pool: batch
  tolerations:
    - key: dedicated
      operator: Equal
      value: batch
      effect: NoSchedule
  restartPolicy: Never
  containers:
    - name: task
      image: busybox:1.37
      command: ["sh", "-c", "echo batch-example-complete"]
      resources:
        requests:
          cpu: 100m
          memory: 32Mi
        limits:
          memory: 64Mi
```

For GPU groups, also select compatible GPU instances/AMIs and install a supported device plugin; workloads must request an extended resource such as `nvidia.com/gpu`. A `dedicated=gpu` taint alone neither installs drivers nor allocates a GPU. Taints are scheduling controls, not tenant security boundaries.

**Maintenance:** a temporary node taint can prevent ordinary new scheduling, but it does not drain running Pods. The following two commands belong to the start and end of a reviewed maintenance window:

```bash
# Individual-node maintenance example; does not evict existing Pods.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" taint node \
  "${EXAMPLE_NODE_NAME:?}" maintenance=planned:NoSchedule

# After the maintenance window, remove only this exact example taint.
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" taint node \
  "$EXAMPLE_NODE_NAME" maintenance=planned:NoSchedule-
```

Use a separate PDB-aware drain procedure if eviction is required. Avoid adding `NoExecute` to a populated group without reviewing the immediate eviction impact. Node bootstrap registration flags are another mechanism, but managed-group configuration is clearer for this use case.

Reference: [EKS managed-node taints](https://docs.aws.amazon.com/eks/latest/userguide/node-taints-managed-node-groups.html).

</details>

## Hands-on Exercises

### Exercise 1: Configuring IRSA (IAM Roles for Service Accounts)

**Scenario:** a Linux workload in an existing EKS cluster needs to read an approved `training/` prefix in one S3 bucket. Give it a dedicated workload role instead of a broad S3 policy on every node.

**Prerequisites:** use an authorized training cluster in the commercial AWS partition, AWS CLI v2, eksctl and jq. The operator needs the IAM and Kubernetes permissions for this exercise. Prepare an existing, non-sensitive object under `training/` in an approved bucket and set `S3_BUCKET`/`S3_TEST_KEY`. The bucket policy and any customer-managed encryption key must allow the intended role; add separately scoped KMS permissions only when the object's encryption requires them. No bucket or object is created by this example.

<details>
<summary>Show Solution</summary>

**1. Prepare a unique namespace, private kubeconfig and the cluster's OIDC provider.** Keep the generated directory and ownership record until cleanup is complete. Run the steps in the same Bash session; if a step fails, inspect the recorded resources before retrying.

```bash
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```

IRSA needs STS connectivity and S3 access from the workload. Private-only environments need the appropriate regional STS/ECR/S3 paths; creating the IAM OIDC provider from inside the VPC can also require `oidc-eks` connectivity. Restrict IMDS and service-account use independently; IRSA alone is not a Pod isolation boundary.

**2. Create the dedicated role and scoped policy.** The trust policy requires both the intended audience and the exact namespace/service-account subject. The policy allows listing only the bucket's `training/` prefix and reading objects only under that prefix. It does not grant `ListAllMyBuckets`.

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```

The role must be newly created. A failed creation stops the script before policy attachment, and its immutable IAM `RoleId` is recorded for cleanup. This avoids attaching a lab policy to a coincidentally named existing role.

**3. Create the service account and a short-lived test Pod.** Three containers check the caller identity, list at most one object in the permitted prefix and read the selected object's metadata. The example outputs only counts/length and records identity metadata; it does not print tokens, secret keys or object contents.

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```

All three containers must succeed, and the identity check must match the expected account and role. A node-role identity is a failure. If the Pod fails, inspect its per-container status/logs and IAM trust, prefix, bucket/key policy and connectivity; do not solve an authorization failure by attaching `AmazonS3ReadOnlyAccess`.

IAM changes can take time to propagate. After resolving the cause, recreate the test Pod deliberately in the owned namespace rather than assuming the original failed run proved success. A successful allowed operation does not prove every other operation is denied; review all applicable IAM/resource policies and perform authorized negative tests if required.

**4. Clean up the owned namespace and role.** The namespace UID and IAM RoleId protect against name reuse. If the namespace is already absent, the cleanup can continue with the recorded role. Unexpected inline policies or failed lookups stop further cleanup; inspect partial failures rather than deleting unrelated resources.

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

The cluster, its shared OIDC provider, the bucket and its objects are retained. Verify the namespace/role removal and keep the ownership record if any step fails. Stopping Pods is not a claim that every previously issued STS credential is instantly invalidated.

This audit did not provision the role or run the Pod against AWS. Local checks validate the generated manifests/policies and failure guards; actual IAM propagation, network reachability and S3 access remain environment-specific tests.

References: [IRSA role configuration](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html), [IRSA private connectivity](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [S3 policy conditions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html).

</details>

### Exercise 2: Strengthening EKS Cluster Security

**Scenario:** evaluate specific security controls in a dedicated EKS 1.36 training cluster. This is an integration exercise, not a tested production-ready configuration.

**Prerequisites:** authorized cluster administration, AWS CLI v2, kubectl and jq; compatible EC2 Linux nodes; a supported EKS-managed VPC CNI with network policy enabled; and conventional CoreDNS Pods in `kube-system`. Use the current CNI/kernel requirements in basic question 3. The example requires working baseline Pod communication; existing organization-wide policies may require a different approved test design. Do not install a second CNI merely to perform this exercise.

<details>
<summary>Show Solution</summary>

**1. Inspect the target and save its current settings.** Set an actual approved administration egress CIDR, not the documentation-only ranges shown elsewhere. This example checks EKS 1.36 and an enabled managed CNI policy configuration before proceeding.

```bash
: "${EXAMPLE_CLUSTER:?Use a dedicated EKS 1.36 training cluster}"
: "${EXAMPLE_REGION:?}"
: "${APPROVED_API_CIDR:?Actual approved administration egress CIDR}"
SECURITY_LAB_DIR=$(mktemp -d /tmp/eks-security-lab.XXXXXX)
: "${SECURITY_LAB_DIR:?}"
SECURITY_NAMESPACE="security-quiz-$(date +%s)-$$"
SECURITY_KUBECONFIG="$SECURITY_LAB_DIR/kubeconfig"

aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$SECURITY_LAB_DIR/before-cluster.json" || exit 1
jq -e '.version == "1.36" and .status == "ACTIVE"' \
  "$SECURITY_LAB_DIR/before-cluster.json" >/dev/null || exit 1
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --query addon --output json > "$SECURITY_LAB_DIR/cni.json" || exit 1
jq -e '(.configurationValues // "{}" | fromjson | .enableNetworkPolicy) as $enabled |
  .status == "ACTIVE" and ($enabled == true or $enabled == "true")' \
  "$SECURITY_LAB_DIR/cni.json" >/dev/null || exit 1
aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$SECURITY_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1

# Serialize cluster configuration updates. A timeout does not cancel an AWS update.
security_wait_update() {
  local update_id="$1" status attempt
  for ((attempt=1; attempt<=60; attempt++)); do
    status=$(aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
      --update-id "$update_id" --query update.status --output text) || return 1
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled)
        printf 'EKS update %s ended as %s\n' "$update_id" "$status" >&2
        return 1 ;;
      InProgress) sleep 10 ;;
      *) printf 'Unexpected EKS update status: %s\n' "$status" >&2; return 1 ;;
    esac
  done
  printf '%s\n' 'Update still pending; inspect it before another configuration change.' >&2
  return 1
}
```

**2. Apply reviewed endpoint/logging settings serially.** The following keeps both API paths and restricts the public path to the approved CIDR. Before choosing a private-only alternative, separately verify private routing/DNS/API access as described in Part 1. A timeout in the polling helper does not cancel the AWS update; inspect it before submitting another change.

EKS 1.36 already envelope-encrypts Kubernetes API data, including Secrets. An empty customer-managed-key configuration is not evidence of plaintext storage. Do not create a second cluster or duplicate KMS keys for this step. If a CMK is required, use the reviewed procedure and key-lifecycle precautions from basic question 4.

```bash
# Keep both API paths; the supplied CIDR must include the intended administration path.
SECURITY_ENDPOINT_UPDATE=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_ENDPOINT_UPDATE" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" get nodes || exit 1

# EKS 1.36 already has default envelope encryption; inspect rather than create a new cluster.
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,encryption:encryptionConfig}'

SECURITY_LOGGING_UPDATE=$(aws eks update-cluster-config \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_LOGGING_UPDATE" || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.logging
```

Control-plane logs have CloudWatch costs and best-effort delivery. Confirm the intended types actually arrive in `/aws/eks/<cluster-name>/cluster` and set retention/access controls. Endpoint restrictions supplement IAM/Kubernetes authorization; they do not replace it.

**3. Create an isolated Restricted namespace and test workloads.** The three Deployments provide controller-owned Pods for reliable VPC CNI policy testing. They use a non-root user, RuntimeDefault seccomp, dropped capabilities, a read-only root filesystem and an `emptyDir` for the backend's temporary files. No ServiceAccount API token is needed.

```bash
jq -n --arg ns "${SECURITY_NAMESPACE:?}" '{
  apiVersion:"v1",kind:"Namespace",metadata:{name:$ns,labels:{
    "pod-security.kubernetes.io/enforce":"restricted",
    "pod-security.kubernetes.io/enforce-version":"v1.36",
    "pod-security.kubernetes.io/audit":"restricted",
    "pod-security.kubernetes.io/audit-version":"v1.36",
    "pod-security.kubernetes.io/warn":"restricted",
    "pod-security.kubernetes.io/warn-version":"v1.36"
  }}
}' > "${SECURITY_LAB_DIR:?}/namespace.json" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  create -f "$SECURITY_LAB_DIR/namespace.json" || exit 1
SECURITY_NAMESPACE_UID=$(kubectl --kubeconfig "$SECURITY_KUBECONFIG" \
  get namespace "$SECURITY_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${SECURITY_NAMESPACE_UID:?}"
jq -n --arg ns "$SECURITY_NAMESPACE" --arg uid "$SECURITY_NAMESPACE_UID" \
  '{namespace:$ns,uid:$uid}' > "$SECURITY_LAB_DIR/namespace-owner.json" || exit 1

jq -n --arg ns "$SECURITY_NAMESPACE" '
  def deployment($name;$command):
    {
      apiVersion:"apps/v1",kind:"Deployment",metadata:{name:$name,namespace:$ns},
      spec:{replicas:1,selector:{matchLabels:{app:$name}},template:{
        metadata:{labels:{app:$name}},
        spec:{
          nodeSelector:{"kubernetes.io/os":"linux"},
          automountServiceAccountToken:false,
          securityContext:{
            runAsNonRoot:true,runAsUser:1000,runAsGroup:1000,fsGroup:1000,
            seccompProfile:{type:"RuntimeDefault"}
          },
          volumes:[{name:"tmp",emptyDir:{}}],
          containers:[({
            name:"app",image:"busybox:1.37",command:$command,
            securityContext:{
              allowPrivilegeEscalation:false,readOnlyRootFilesystem:true,
              capabilities:{drop:["ALL"]}
            },
            volumeMounts:[{name:"tmp",mountPath:"/tmp"}],
            resources:{requests:{cpu:"50m",memory:"32Mi"},limits:{memory:"64Mi"}}
          } + if $name == "backend" then {
            ports:[{name:"http",containerPort:8080}],
            readinessProbe:{httpGet:{path:"/",port:8080}}
          } else {} end)]
        }
      }}
    };
  {
    apiVersion:"v1",kind:"List",items:[
      deployment("backend";["sh","-c","mkdir -p /tmp/www && printf \"policy-test-ok\\n\" > /tmp/www/index.html && exec httpd -f -p 8080 -h /tmp/www"]),
      deployment("frontend";["sleep","3600"]),
      deployment("outsider";["sleep","3600"]),
      {
        apiVersion:"v1",kind:"Service",metadata:{name:"backend",namespace:$ns},
        spec:{selector:{app:"backend"},ports:[{name:"http",port:8080,targetPort:8080}]}
      }
    ]
  }' > "$SECURITY_LAB_DIR/workloads.json" || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" create -f "$SECURITY_LAB_DIR/workloads.json" || exit 1
for app in backend frontend outsider; do
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
    rollout status "deployment/$app" --timeout=180s || exit 1
done

# Establish baseline connectivity before applying the policies.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ || exit 1
```

Both clients must reach the backend before policies are applied. If baseline connectivity fails, resolve that first rather than treating the failure as proof of network-policy enforcement.

**4. Apply default deny plus the required allow rules.** This is the same policy design as basic question 3, scoped to the generated namespace. It permits frontend-to-backend TCP 8080 and conventional CoreDNS traffic in both UDP/TCP. Service and container ports match.

```bash
cat > "${SECURITY_LAB_DIR:?}/networkpolicies.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Egress]
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
EOF
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" apply -f "$SECURITY_LAB_DIR/networkpolicies.yaml" || exit 1
```

**5. Verify fresh connections and positive controls.** Observe the unrelated client's denied request after policy convergence, then confirm that the allowed frontend request and DNS still work. These observations apply to this test topology; inspect policy/agent status and logs when interpreting unexpected failures.

```bash
# Wait briefly for the expected denied fresh connection; do not treat baseline failures as success.
SECURITY_DENY_OBSERVED=false
for ((attempt=1; attempt<=6; attempt++)); do
  if kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" -n "${SECURITY_NAMESPACE:?}" \
    exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ >/dev/null 2>&1; then
    sleep 2
  else
    SECURITY_DENY_OBSERVED=true
    break
  fi
done
[ "$SECURITY_DENY_OBSERVED" = true ] || {
  printf '%s\n' 'Expected deny was not observed; inspect policy enforcement.' >&2
  exit 1
}

# Positive controls after the denial: allowed application traffic and DNS must still work.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- nslookup backend || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" get networkpolicies
```

PSA enforces the namespace's Restricted standard. Kyverno or Gatekeeper is optional for requirements beyond PSA; use the current APIs from basic question 6 and adapt their namespace match if testing them here. A successfully created policy outside this namespace would not enforce this lab's workloads.

**6. Review related controls without substituting incomplete recipes.** A read-only `Describe*` IAM policy cannot operate AWS Load Balancer Controller; use its version-matched official policy and reviewed resource/tag conditions. Inspect node IAM, IMDS, security groups and add-on identities. `maxUnavailable` controls an initiated managed-node update's disruption; it does not schedule periodic replacement. Use a separately reviewed maintenance/upgrade plan.

**7. Clean up the lab namespace.** Use the recorded UID; retain the private ownership/settings files if cleanup fails.

```bash
CURRENT_SECURITY_UID=$(kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  get namespace "${SECURITY_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_SECURITY_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_SECURITY_UID" = "${SECURITY_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" delete namespace "$SECURITY_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace UID mismatch; no deletion attempted.' >&2
  exit 1
fi
```

If retaining the cluster, review the resulting endpoint/logging posture and ongoing log retention/cost. If removing the training cluster, follow the cluster lifecycle guide and inspect retained CloudWatch logs and independently managed resources. Do not delete an associated KMS key as namespace cleanup.

This audit did not perform the AWS updates or run Pod networking. Local checks cover generated manifests, policy logic and failure/cleanup guards. Production IAM, routing, admission, availability and recovery still require environment-specific verification.

References: [network-policy requirements](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html), [default envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [API endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [control-plane logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

## Advanced Topics

The following are questions about advanced topics in Amazon EKS cluster creation. This section tests your understanding of advanced concepts and best practices in EKS cluster creation.

1. Which is NOT a requirement for an EKS IPv6 cluster?
   * A) VPC/subnets with IPv4 and IPv6 addressing
   * B) A supported CNI configuration and IPv6 IAM permissions
   * C) Supported Nitro-based EC2 nodes or Fargate
   * D) A separate IPv6-only EC2 instance family

<details>
<summary>Show Answer</summary>

**Answer: D) A separate IPv6-only EC2 instance family**

EKS does not require a separate “IPv6-only instance family.” It does require **supported Nitro-based EC2 nodes or Fargate**, so the statement that any ordinary EC2 instance type will work is incorrect.

**Prerequisites:**

1. Select the IPv6 IP family when creating a **new** cluster. It is immutable; patching `ENABLE_IPV6` on an existing IPv4 cluster does not convert the cluster.
2. Associate IPv4 and IPv6 CIDRs with the VPC/subnets and enable IPv6 auto-assignment on node subnets. Review IPv6 routes, security groups, DNS and administration connectivity. Subnet IDs must refer to the intended VPC/AZs.
3. Use a supported VPC CNI release configured for IPv6 and prefix delegation. Version 1.10.1 is the historical minimum, not a current recommended install. Do not apply an old 1.10 manifest over a current managed add-on.
4. Provide the CNI's IPv6 IAM permissions, preferably on its own workload role. The IPv4 `AmazonEKS_CNI_Policy` is not the IPv6 policy. Review the role/policies generated by the eksctl IPv6/add-on workflow.

```bash
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,ipv4:CidrBlock,ipv6:Ipv6CidrBlockAssociationSet,autoIPv6:AssignIpv6AddressOnCreation}'
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --kubernetes-version 1.36
```

**Example:** this uses existing, already prepared dual-stack private subnets and a Nitro-based AL2023 node group. Replace the example IDs and public-access CIDR. The `kubernetesNetworkConfig.ipFamily: IPv6` spelling is correct for eksctl; the EKS API uses lowercase `ipv6`.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-lab
  region: us-west-2
  version: "1.36"
kubernetesNetworkConfig:
  ipFamily: IPv6
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
iam:
  withOIDC: true
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
managedNodeGroups:
  - name: ipv6-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
```

Save the reviewed configuration as `ipv6-cluster.yaml`. Select and record the exact compatible add-on versions for your environment; the omitted versions above let the tool choose its compatible defaults. This is not a claim that a particular historical CNI build should be installed.

```bash
# After reviewing real IDs, routing, IAM, access and compatible addon versions.
eksctl create cluster -f ipv6-cluster.yaml --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

The configuration does not prepare the existing subnet routes/IPv6 attributes for you. Confirm the created access entries and CNI permissions as well as node/add-on readiness. This audit did not create an IPv6 cluster.

**Addressing and traffic:**

- EKS exposes IPv6 Pod addresses and assigns IPv6 ClusterIPs. A dual-stack VPC does not make EKS Pods/Services dual-stack.
- Pod IPv6 addresses come from subnet addressing; Service IPv6 addresses use an EKS-assigned unique-local range within `fc00::/7`. Do not assume a fixed `fd00::/108` service CIDR.
- EC2 nodes have IPv4 and IPv6 addresses. A Pod can also receive an unreported host-local IPv4 address for reaching external IPv4 destinations, with source NAT through the node. Private-node IPv4 internet access can still need NAT; IPv6 does not eliminate every NAT dependency.
- Native IPv6 internet traffic can use an internet gateway or an egress-only internet gateway, depending on the intended direction and security design. An egress-only gateway is not mandatory for every IPv6 cluster.
- Load balancing to IPv6 Pods requires a compatible controller/load-balancer configuration with IP targets. IPv4 client access can still be provided through an appropriate dual-stack front end; do not equate Pod addressing with the client's IP family.
- Windows and VPC CNI custom networking are not supported in EKS IPv6 clusters. Check the support of storage drivers, add-ons and external dependencies before choosing the family.

```bash
aws eks describe-cluster --name "${IPV6_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.kubernetesNetworkConfig
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get pods -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get services -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -o wide
```

Inspect actual addresses and test DNS plus required IPv6/IPv4 destinations. Listing IPv6 addresses alone is not a connectivity or availability test. Clean up only the recorded lab resources following the cluster lifecycle procedure.

References: [EKS IPv6 behavior](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html), [eksctl IPv6 tutorial](https://docs.aws.amazon.com/eks/latest/userguide/deploy-ipv6-cluster.html), [CNI IAM role](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html), [network configuration response](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigResponse.html).

</details>

2. What does VPC CNI custom networking primarily enable?
   * A) Pod subnets/security groups different from the node's primary interface, within the same VPC
   * B) Automatic prevention of all CIDR overlap
   * C) Encryption of every node-to-node connection
   * D) Faster control-plane reconciliation

<details>
<summary>Show Answer</summary>

**Answer: A) Pod subnets/security groups different from the node's primary interface, within the same VPC**

VPC CNI custom networking lets **Linux IPv4 EC2 Pods use alternate subnets/security groups within the same VPC as their nodes**. The Pod range is not outside the VPC's associated CIDRs. A secondary VPC CIDR can provide additional address space, but using one does not automatically prevent overlap with other networks.

By default, VPC CNI creates secondary ENIs in the node's primary subnet and uses addresses from those ENIs as well as eligible addresses on the primary ENI. With custom networking, regular Pod IPs come from secondary ENIs configured through `ENIConfig`; the primary ENI is not used to allocate those Pod IPs. Host-network Pods continue to use host networking.

**Configuration sequence:**

1. Plan available IPv4 space, routing and permissions. If adding a secondary CIDR, check VPC association restrictions and overlaps with connected networks. AWS's `100.64.0.0/10` shared-space examples are not a guarantee that the range is unused in your environment.
2. Prepare alternate Pod subnets in the **same VPC and corresponding AZ** as each node's primary subnet. Review subnet routes and security-group rules, including API/DNS/workload dependencies.
3. Create an `ENIConfig` per intended Pod subnet. The following uses one subnet per AZ; replace all IDs. Do not overwrite existing cluster-scoped configurations owned by another deployment.

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
    - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2b
spec:
  subnet: subnet-0123456789abcdef1
  securityGroups:
    - sg-0123456789abcdef0
```

4. Configure custom networking and ENIConfig selection using the owner of the CNI installation. For an EKS-managed add-on, merge these environment settings into its full reviewed configuration after checking the schema for the installed version:

```yaml
# Merge with existing managed-addon configuration; do not discard other env values.
env:
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG: "true"
  ENI_CONFIG_LABEL_DEF: topology.kubernetes.io/zone
```

For a self-managed DaemonSet, the equivalent update is below. This affects CNI behavior cluster-wide and belongs in a planned migration, not a casual application deployment:

```bash
# Self-managed CNI alternative, after preparing ENIConfig/subnets and a rollout plan.
# For an EKS-managed addon, use its supported configuration-values workflow instead.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  set env daemonset/aws-node AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true \
  ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  rollout status daemonset/aws-node --timeout=5m
```

5. Provision and validate replacement nodes with the required configuration, then migrate workloads using PDB-aware draining and application tests. Changing the environment variables does not readdress existing Pods. AWS recommends new nodes for the custom-networking configuration. Keep old capacity until the migration is verified.

When `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`, name each `ENIConfig` after that AZ. If multiple Pod subnets in one AZ need distinct configurations, use unique names and a reviewed custom node label/annotation mapping. Existing ENIConfig annotation selection can override label-based selection. Do not change a node's real topology label to force it to use a subnet in another AZ.

**Capacity and security limits:**

- Excluding the primary ENI reduces secondary-IP-mode Pod capacity. Prefix delegation can increase address capacity, but subnet prefix availability, supported instance limits and kubelet `maxPods` still matter. Calculate and test density rather than copying a universal value.
- With the default `AWS_VPC_K8S_CNI_EXTERNALSNAT=false`, traffic outside VPC-associated CIDRs is source-NATed through the node's primary interface and uses its subnet/security groups. Do not assume an ENIConfig security group filters every external flow.
- When combined with Security Groups for Pods, the Pod's `SecurityGroupPolicy` group takes precedence over the ENIConfig group for that Pod. Check supported enforcement/SNAT modes.
- Custom networking is not encryption or a tenant isolation boundary by itself, and does not solve overlapping-CIDR routing without an appropriate network design.
- It is not supported for EKS IPv6 or Windows nodes. Fargate selects subnets through its profiles rather than using EC2-node ENIConfig mappings.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get eniconfigs
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -L topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "${APPLICATION_NAMESPACE:?}" get pods -o wide
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${POD_SUBNET_A:?}" "${POD_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,az:AvailabilityZone,cidr:CidrBlock,free:AvailableIpAddressCount}'
```

Verify Pod IPs against the intended subnets, node AZs, DNS/API connectivity and required application flows. An `ENIConfig` listing alone does not prove migration or isolation. This example was reviewed statically; no CNI change, node migration or network benchmark was executed.

References: [custom networking](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html), [configuration and migration](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network-tutorial.html), [custom-networking considerations](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html).

</details>

3. Which is NOT a requirement for Windows workloads on EKS?
   * A) At least two Amazon Linux managed node groups
   * B) Linux or Fargate capacity for Linux-only system Pods
   * C) A compatible Windows AMI and container image
   * D) Windows IPAM and correct IAM/node authentication

<details>
<summary>Show Answer</summary>

**Answer: A) At least two Amazon Linux managed node groups**

There is no requirement for two Amazon Linux managed node groups. EKS needs **Linux or Fargate capacity for Linux-only system Pods such as CoreDNS**; this does not require a particular Linux distribution or two separate groups. Plan replicas and fault-domain placement for availability rather than treating the minimum as an HA design.

**Windows prerequisites:**

1. Use a currently supported EKS **IPv4** cluster and compatible EKS-optimized Windows AMI. AWS publishes Windows Server 2019, 2022 and 2025 variants; this example deliberately uses 2022, not an obsolete Kubernetes 1.14/1.23 support baseline.
2. Confirm `AmazonEKSVPCResourceController` permissions on the cluster IAM role and enable Windows IPAM in the `kube-system/amazon-vpc-cni` configuration.
3. Let the managed VPC resource controller perform Windows IPAM. Do not install the old data-plane resource-controller/admission-webhook manifests from a floating `master` URL.
4. Use a dedicated Windows node IAM role and the correct node authentication. API authentication uses an `EC2_WINDOWS` access entry; managed node groups manage their node access entries. With legacy `aws-auth`, preserve the required `eks:kube-proxy-windows` group in addition to the bootstrap/node groups.

```bash
aws iam list-attached-role-policies --role-name "${EKS_CLUSTER_ROLE_NAME:?}"

# If missing, attach to the reviewed cluster role, not to every worker role.
aws iam attach-role-policy --role-name "$EKS_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

The Windows IPAM setting belongs to the existing VPC CNI configuration. If EKS or Helm owns it, use that owner's supported settings rather than replacing the whole ConfigMap:

```yaml
# Relevant ConfigMap data; merge through the owning addon/Helm configuration.
data:
  enable-windows-ipam: "true"
```

**Node group example:** save this as `windows-nodegroup.yaml` after reviewing the existing cluster, subnets, AMI availability and IAM. The taint prevents ordinary Linux workloads from accidentally landing on these nodes; Linux workload templates should also select Linux explicitly.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: windows-ng
    amiFamily: WindowsServer2022FullContainer
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    privateNetworking: true
    taints:
      - key: example.com/os
        value: windows
        effect: NoSchedule
```

```bash
# Existing, supported IPv4 cluster with Windows IPAM and IAM prerequisites ready.
eksctl create nodegroup -f windows-nodegroup.yaml
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name windows-ng \
  --query 'nodegroup.{status:status,ami:amiType,role:nodeRole,health:health}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l kubernetes.io/os=windows -L node.kubernetes.io/windows-build
```

**Workload example:** create an unused `windows-lab` namespace and deploy an image compatible with the node's Windows build. EKS-optimized Windows AMIs include kubelet, **Windows kube-proxy**, containerd and related host components; kube-proxy is not Linux-only.

Use the official IIS image with its existing ServiceMonitor entrypoint. The old `dotnetbinaries.blob.core.windows.net` ServiceMonitor download location was retired; installing IIS and downloading a binary during every Pod start is unnecessary here.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-iis
  namespace: windows-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-iis
  template:
    metadata:
      labels:
        app: windows-iis
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
        kubernetes.io/arch: amd64
        node.kubernetes.io/windows-build: "10.0.20348"
      tolerations:
        - key: example.com/os
          operator: Equal
          value: windows
          effect: NoSchedule
      containers:
        - name: iis
          image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
          ports:
            - containerPort: 80
          startupProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              memory: 1Gi
```

The image tag was verified in Microsoft's image README and registry metadata. Its layers were not downloaded and the Windows workload was not run during this audit. Resource values are illustrative. Check actual rollout/readiness, DNS, application traffic and host/container build compatibility before production use.

**Supported-feature boundaries:**

- Windows cannot run as EKS Fargate Pods, EKS Auto Mode nodes or EKS Hybrid Nodes. It does not support EKS IPv6, VPC CNI custom networking or Security Groups for Pods.
- Ordinary Windows Pods differ from privileged Linux containers. Windows **HostProcess** Pods can use host networking, so a blanket “Windows never supports hostNetwork” statement is incorrect. HostProcess requires separate elevated-security review.
- Windows networking/IP capacity differs from Linux. Review single-ENI limits and supported prefix delegation rather than assuming Linux Pod-density calculations apply.
- Select storage drivers with Windows support and validate volume/path semantics. Do not assume Linux hostPath permissions or every CSI feature is portable.
- EKS-optimized Windows nodes use containerd; Linux application images belong on Linux nodes. Verify system add-on and application placement in mixed-OS clusters.

References: [EKS Windows support](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html), [optimized Windows AMIs](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-windows-ami.html), [Microsoft IIS image](https://github.com/microsoft/iis-docker), [Windows HostProcess](https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/).

</details>



4. Which setting requires a session token for EC2 instance metadata requests?
   * A) HttpTokens=required (IMDSv2 only)
   * B) A security-group rule for 169.254.169.254
   * C) A Kubernetes Node label
   * D) An application ServiceAccount name alone

<details>
<summary>Show Answer</summary>

**Answer: A) HttpTokens=required (IMDSv2 only)**

Requiring IMDSv2 (`HttpTokens: required`) disables tokenless IMDSv1 calls and adds defense in depth. It does **not** make all SSRF impossible or provide a security boundary between containers that share a host.

**Launch-template settings:** the following is an EC2 `LaunchTemplateData` fragment, not a `managedNodeGroups.metadataOptions` field. Hop limit 1 assumes ordinary Pods use IRSA/Pod Identity rather than retrieving node credentials:

```json
{
  "MetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1,
    "HttpEndpoint": "enabled"
  }
}
```

The hop limit applies to the IMDS token **PUT response**, not to every metadata request. A container that legitimately needs IMDSv2 can require hop limit 2. Inspect compatibility and move application permissions to workload roles; do not raise the limit merely to hide an unexplained failure.

Use an existing reviewed template version through the supported eksctl `launchTemplate.id/version` fields. The example ID below must be replaced; `--launch-template-name` is not the documented `eksctl create nodegroup` interface:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-template-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    privateNetworking: true
```

**eksctl alternative:** the supported `disableIMDSv1` and `disablePodIMDS` fields can be used for a new node group. Prepare required workload identities first. `disablePodIMDS` targets non-host-network Pods and cannot be combined with `withAddonPolicies`.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-restricted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    disableIMDSv1: true
    disablePodIMDS: true
```

These two configurations are alternatives; review the actual generated template and node metadata settings. Defaults depend on instance launch settings, account/Region defaults and AMI metadata support, with launch settings taking precedence. Do not assume every AMI/node group defaults to hop limit 1.

**Existing nodes:** a new version of the same custom launch template can be rolled out through a managed node-group update. Individual running/stopped EC2 instances can also have metadata options changed, subject to IAM/SCP restrictions, but that alone does not update the configuration of future replacement nodes:

```bash
# Inspect the explicitly reviewed instance before changing its metadata settings.
aws ec2 describe-instances --region "${EXAMPLE_REGION:?}" \
  --instance-ids "${REVIEWED_INSTANCE_ID:?}" \
  --query 'Reservations[].Instances[].{id:InstanceId,tags:Tags,metadata:MetadataOptions}'

# Separate transition step for a tested instance with compatible host agents.
aws ec2 modify-instance-metadata-options --region "$EXAMPLE_REGION" \
  --instance-id "$REVIEWED_INSTANCE_ID" --http-tokens required \
  --http-put-response-hop-limit 1 --http-endpoint enabled
```

Verify that the options reached the `applied` state and that node agents, image pulls and workload credentials still work. Do not disable the entire metadata endpoint merely because an application uses IRSA: host components can still depend on the node instance profile and metadata.

**Additional controls:**

- Scope the node role and give applications their own roles. IRSA/Pod Identity does not by itself prevent alternate access to node IMDS.
- `hostNetwork` Pods can access IMDS, and a sufficiently privileged host workload can bypass Pod network isolation. Control Pod privileges and host access separately.
- Security groups do not filter the instance's link-local metadata service. If enforcing additional host/network restrictions, account for the real Pod path and the optional IPv6 IMDS endpoint (`fd00:ec2::254`) as well as IPv4. The old ad hoc `PREROUTING -i eth0` DNAT rule is not a reliable general Pod IMDS restriction.
- Use supported SDKs and test metadata access without printing session tokens or IAM credential values. Observe actual instance metadata options rather than assuming a node's Kubernetes labels prove enforcement.

References: [IMDS options and precedence](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html), [IMDSv2 behavior](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html), [eksctl security options](https://docs.aws.amazon.com/eks/latest/eksctl/security.html), [IRSA isolation limits](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html).

</details>

5. Which task is outside the purpose of an EC2 node bootstrap configuration?
   * A) Modify EKS-managed control-plane processes
   * B) Configure reviewed software already installed in a custom AMI
   * C) Apply workload-validated host settings
   * D) Set supported node-group labels and taints

<details>
<summary>Show Answer</summary>

**Answer: A) Modify EKS-managed control-plane processes**

Node bootstrap configures **node hosts**, not the EKS-managed API server, scheduler, controller manager or etcd. For AL2023, use `nodeadm` and the supported eksctl/launch-template paths; the old AL2 `bootstrap.sh`/`kubeletExtraArgs` examples do not apply.

**Install and configure software deliberately.** Use a verified package for the target OS/architecture, preferably baked into a reviewed AMI. An unverified `latest` RPM downloaded at every boot is not a reproducible installation. A host agent also needs the appropriate IAM permissions and private/public service connectivity.

The following optional AL2023 host example assumes the CloudWatch agent is already installed. It configures host memory/swap metrics and starts the agent; it sends billable telemetry if run with working AWS access. It is not an instruction to run on the administration workstation, Bottlerocket or Auto Mode:

```bash
#!/bin/bash
# AL2023 host example: the reviewed AMI must already contain the verified agent package.
set -euo pipefail
AGENT_CTL=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl
test -x "$AGENT_CTL" || {
  printf '%s\n' 'CloudWatch agent is not installed in this AMI.' >&2
  exit 1
}
cat > /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "swap": {"measurement": ["swap_used_percent"]}
    }
  }
}
EOF
"$AGENT_CTL" -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json -s
```

**Kernel tuning:** use workload evidence and the actual kernel/CNI requirements. The original example values are retained here as unvalidated tuning references, not universal performance recommendations:

| Example setting | Original example value | Review requirement |
| --- | --- | --- |
| `net.ipv4.ip_forward` | `1` | Node/CNI routing requirements |
| `net.bridge.bridge-nf-call-iptables` | `1` | Whether the bridge module and CNI datapath require it |
| `net.ipv4.tcp_keepalive_time` | `600` | Application/connection timeout behavior |
| `net.ipv4.tcp_max_syn_backlog`, `net.core.somaxconn`, `net.core.netdev_max_backlog` | `40000` | Actual queue pressure, memory and workload measurements |
| `vm.max_map_count` | `262144` | The specific application's mapping requirements |

Do not apply this table as a blanket node script. Record the baseline, validate changes in a test group and retain a rollback path.

**Disks:** never run `mkfs` against an assumed `/dev/nvme1n1`. NVMe enumeration is not a stable ownership identifier and the device may contain required data. Identify the intended EBS volume by its volume ID/serial, confirm it is a newly provisioned disposable or otherwise explicitly prepared device, and inspect partitions/filesystems/mounts before any formatting. Use stable identifiers such as filesystem UUIDs for persistent mount configuration.

```bash
# Read-only inspection on the specifically authorized test node.
lsblk --output NAME,PATH,TYPE,SIZE,FSTYPE,UUID,MOUNTPOINTS,SERIAL
findmnt
sysctl net.ipv4.ip_forward vm.max_map_count
```

For persistent application data, prefer the appropriate CSI/PV lifecycle instead of coupling it to a node's disposable disks. The inspection commands above do not format or mount anything.

**Labels, taints and security:** use managed node-group label/taint fields and a domain you control; do not overwrite provider-owned topology/node-group labels. Use a reviewed AMI and security-group/CNI design for host hardening. Ad hoc SSH/firewall edits during bootstrap can conflict with existing rules or sever access and are not a complete hardening procedure.

**Launch-template user data:** with an EKS-selected AL2023 AMI and no custom `ImageId`, EKS supplies the required default NodeConfig. A minimal MIME customization can look like:

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_BOOTSTRAP_EXAMPLE"

--EKS_BOOTSTRAP_EXAMPLE
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_BOOTSTRAP_EXAMPLE--
```

```bash
# Prepare real EC2 UserData JSON from the reviewed MIME file; no placeholder base64.
BOOTSTRAP_DIR=$(mktemp -d /tmp/eks-bootstrap-example.XXXXXX)
: "${BOOTSTRAP_DIR:?}"
jq -n --rawfile data "${REVIEWED_MIME_FILE:?}" \
  '{UserData:($data|@base64)}' > "$BOOTSTRAP_DIR/launch-template-data.json" || exit 1
aws ec2 create-launch-template --region "${EXAMPLE_REGION:?}" \
  --launch-template-name "${NEW_LAUNCH_TEMPLATE_NAME:?}" \
  --version-description "Reviewed AL2023 customization" \
  --launch-template-data "file://$BOOTSTRAP_DIR/launch-template-data.json" \
  --query 'LaunchTemplate.{id:LaunchTemplateId,version:LatestVersionNumber}'
```

Use the returned template ID/version through `managedNodeGroups[].launchTemplate`, as in advanced question 4. If you specify a custom AMI ID outside an eksctl-generated configuration, also supply the complete cluster NodeConfig described in basic question 5. Do not start kubelet manually or call `nodeadm init` again.

**eksctl alternative:** the following configuration uses supported node-group fields and a harmless directory-creation pre-bootstrap command. Add only reviewed host customization. `preBootstrapCommands` contains shell commands; AL2023's `overrideBootstrapCommand`, when needed for NodeConfig customization, contains NodeConfig YAML.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
      example.com/node-type: compute
    taints:
      - key: dedicated
        value: compute
        effect: NoSchedule
    preBootstrapCommands:
      - install -d -m 0755 /opt/company
```

The examples have not been booted as a production node recipe. Validate package provenance, effective nodeadm/kubelet configuration, startup failures, networking and workload health in your environment.

**CoreDNS is a data-plane workload/add-on**, normally a Deployment on Linux EC2 or supported Fargate capacity, not an EKS-managed control-plane process. Configure it through the add-on/Kubernetes workflow. Exposed EKS control-plane API settings such as logging are separate from node user data.

References: [AL2023 initialization](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [eksctl bootstrapping](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html), [launch-template constraints](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [CloudWatch agent configuration](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html).

</details>
