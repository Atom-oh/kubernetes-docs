# NodePool Configuration and Optimization

> **Supported Versions**: EKS Auto Mode GA; example baseline EKS 1.36
> **Last Updated**: October 21, 2026

This chapter distinguishes AWS-managed defaults, custom NodePool constraints and the AWS-specific NodeClass API. Complete [Getting Started](./01-getting-started.md) first, use the intended account/context, and review all IAM/profile names and network tags before applying a template. The capacity limits shown are illustrative and can still permit substantial cost.

The NodePool examples were checked against the structural schema of the released Karpenter 1.14.1 CRD; AWS-specific NodeClass fields were compared with AWS documentation. This does not identify Auto Mode's internal controller version or prove admission/readiness on a live cluster. No nodes were provisioned during this audit.

## Understand the Built-in NodePools

When enabled, Auto Mode supplies the following pools. They are AWS-managed; create custom pools instead of editing their managed configuration.

| Pool | Architecture | Capacity and instance selection | Purpose |
|------|--------------|----------------------------------|---------|
| `general-purpose` | `amd64` | On-Demand, C/M/R families, generation 5 or newer | General workloads |
| `system` | `amd64` and `arm64` | On-Demand, C/M/R families, generation 5 or newer | Cluster-critical workloads that tolerate `CriticalAddonsOnly` |

The built-in general-purpose pool does **not** enable Spot. Use a custom pool when you need Spot or different architecture/instance constraints. Auto Mode provides node-local DNS and service-networking functions; a pure Auto Mode cluster does not need ordinary CoreDNS/kube-proxy Pods just to populate the system pool. Mixed clusters still need the traditional CoreDNS Deployment for non-Auto nodes.

Inspect the actual managed objects for disruption settings and taint details rather than applying a guessed default YAML:

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

At least one built-in pool must be enabled for AWS to provide the `default` NodeClass. If both are disabled, create your own NodeClass and update the references below. Removing a built-in name from `computeConfig.nodePools` deletes that pool and drains/terminates its nodes; it is not just hiding the pool from new workloads.

## Create Custom NodePools

These examples reference the existing `default` NodeClass to focus on scheduling constraints. To use the custom NodeClass later in this chapter, create it first and change `nodeClassRef.name` in the intended pool. All labels and taints under `template` apply to new nodes; a label only on NodePool metadata does not label the nodes.

### Compute-optimized workloads

The generation condition `Gt ["6"]` permits generation 7 and newer. It does not select only the latest generation. The example permits x86 C-family On-Demand instances and gives this pool a higher provisioning preference than the memory example.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '6'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - xlarge
        - 2xlarge
        - 4xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  weight: 10
```

### Memory-optimized workloads

This example permits R-family generation 6 and newer on either architecture. Your container image and application dependencies must support whichever architecture the scheduler selects.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - 2xlarge
        - 4xlarge
        - 8xlarge
        - 12xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '500'
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

## Configure the AWS NodeClass

Auto Mode uses `eks.amazonaws.com/v1`, kind `NodeClass`. Its fields differ from the self-managed AWS Karpenter `EC2NodeClass`: do not copy `amiFamily`, `blockDeviceMappings`, arbitrary shell `userData` or `metadataOptions` into this API. AWS selects its managed Bottlerocket variant.

Save the following as `custom-nodeclass.yaml` and replace the illustrative profile and selector values with reviewed resources. `instanceProfile` is supported; its name must start with `eks`. Alternatively set `role` to the node IAM role name. **Specify exactly one of `role` or `instanceProfile`.** The role contained in the profile needs the appropriate Auto Mode EKS access entry and permissions; reusing a configured role does not require a duplicate entry. For a new role, follow the access-entry procedure in the AWS NodeClass reference.

Subnet tags select resources but do not establish routing or isolation. Verify VPC, AZ availability, route tables and security-group rules. `associatePublicIPAddress: false` prevents public IP assignment; nodes still need appropriate outbound connectivity.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: '1'
      Environment: production
  securityGroupSelectorTerms:
  - tags:
      kubernetes.io/cluster/my-cluster: owned
      Type: worker-node
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  advancedNetworking:
    associatePublicIPAddress: false
  advancedCompute:
    kernel:
      sysctl:
        vm.max_map_count: 262144
  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

Verify that the cluster role can create and tag resources using any custom keys in `spec.tags`; a NodeClass does not itself grant IAM permissions.

`ephemeralStorage` configures node ephemeral storage rather than arbitrary block-device mappings. The `100Gi` size and 3000 IOPS/125 MiB/s settings are examples; check current Auto Mode field limits, instance storage behavior and cost. Customer KMS configuration belongs at `ephemeralStorage.kmsKeyID` and applies to the node's root/data **EBS** volumes. It does not select the key for local NVMe instance-store encryption or establish encryption for application PVCs.

The old bootstrap example changed `vm.max_map_count`. The supported replacement is `advancedCompute.kernel.sysctl`, applied at node boot. Changing supported kernel settings marks existing nodes for drift/replacement; it is not an immediate in-place shell update. Configure it only for workloads that need that setting, and review disruption behavior.

### Kubelet settings

Auto Mode applies its own kubelet defaults. Override them only through `spec.advancedCompute.kubelet` when a workload needs different Pod density, eviction, log rotation or OOM behavior. The AWS-documented overrides below are the complete set; the self-managed Karpenter `EC2NodeClass` `spec.kubelet` fields that are not listed (for example `kubeReserved`, `systemReserved`, `clusterDNS`, `podsPerCore` and the image-GC thresholds) are not exposed by the Auto Mode NodeClass.

Save the following as `kubelet-nodeclass.yaml`. The values are illustrative, not recommendations; replace the identity and selector values with reviewed resources as in the previous example.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: kubelet-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: '1'
      Environment: production
  securityGroupSelectorTerms:
  - tags:
      kubernetes.io/cluster/my-cluster: owned
      Type: worker-node
  advancedCompute:
    kernel:
      sysctl:
        user.max_user_namespaces: 65536   # required because idsPerPod is set below
    kubelet:
      maxPods: 60
      podPidsLimit: 4096
      idsPerPod: 65536
      singleProcessOOMKill: false
      eviction:
        hard:
          memory.available: 100Mi
          nodefs.available: 10%
        soft:
          memory.available: 500Mi
          nodefs.available: 15%
        softGracePeriod:                  # required for every soft signal
          memory.available: 1m30s
          nodefs.available: 2m
        maxPodGracePeriod: 60
      logging:
        containerLogMaxSize: 10Mi
        containerLogMaxFiles: 5
      allowedUnsafeSysctls:
      - net.core.somaxconn
```

| Field | Meaning | Constraint |
|-------|---------|------------|
| `maxPods` | Upper bound on Pods per node | 1–110; the effective value is the lowest of this setting, the IP addresses the instance type can supply and Auto Mode's limit of 110 |
| `podPidsLimit` | Maximum process IDs per Pod | `-1` disables the limit; otherwise 100 or greater (0–99 is rejected) |
| `idsPerPod` | UIDs and GIDs the kubelet allocates to each Pod's user namespace | A multiple of 65536 from 65536 to 4294967295; requires `advancedCompute.kernel.sysctl.user.max_user_namespaces` greater than 0 on the same NodeClass |
| `singleProcessOOMKill` | Kill processes in a container one at a time on OOM instead of as a group | Needs Kubernetes 1.32 or later; on earlier versions it has no effect and EKS emits a warning event on the NodeClass |
| `eviction.hard` / `eviction.soft` | Eviction thresholds per signal, as a quantity (`500Mi`) or a percentage (`10%`) | Signals: `memory.available`, `nodefs.available`, `nodefs.inodesFree`, `imagefs.available`, `imagefs.inodesFree`, `pid.available` |
| `eviction.softGracePeriod` | How long a soft threshold must hold before eviction starts | Required for each signal that has a soft threshold |
| `eviction.maxPodGracePeriod` | Maximum termination grace, in seconds, for Pods evicted on a soft threshold | `0` uses each Pod's `terminationGracePeriodSeconds` |
| `logging.containerLogMaxSize` / `logging.containerLogMaxFiles` | Container log rotation size and retained file count | `containerLogMaxFiles` is at least 2 |
| `allowedUnsafeSysctls` | Unsafe sysctls, or patterns ending in `*`, that Pods on the node may set | Up to 64 entries; allowed patterns are `kernel.shm*`, `kernel.msg*`, `kernel.sem`, `fs.mqueue.*` and `net.*` |

Review these behaviors before changing a production NodeClass:

- **Nodes are replaced, not patched.** Changing kubelet settings on an existing NodeClass marks its nodes as drifted and EKS replaces them with nodes that use the new configuration. Settings are never applied to a running node in place, so review disruption budgets and PDBs first.
- **`maxPods` is a ceiling.** Confirm the result on a replacement node with `kubectl get node <node> -o jsonpath='{.status.capacity.pods}'` rather than assuming the configured value.
- **Soft thresholds must trigger earlier than hard ones.** A soft threshold must be less aggressive than the hard threshold for the same signal. A quantity and a percentage can be mixed; EKS resolves both for each instance type and marks instance types that break the rule as incompatible with the NodeClass.
- **`allowedUnsafeSysctls` only permits.** It lets Pods on the node request the sysctl; each Pod must still list it in `securityContext.sysctls`. Node-level kernel values are set separately through `advancedCompute.kernel.sysctl`.

### Fixed IMDS security configuration

Auto Mode enforces IMDSv2 and a hop limit of 1; those defaults cannot be changed through NodeClass. Normal non-host-network Pods cannot reach IMDS by that path, but this is not a universal Pod isolation guarantee: `hostNetwork` changes reachability. Prefer workload identity for application AWS access, and explicitly supply region or other configuration rather than depending on node metadata.

### Customer KMS, CA bundles and separate Pod networking

Do not paste a truncated certificate into a manifest. This optional generator reads the reviewed basic template, checks an approved public PEM bundle, base64-encodes it into `certificateBundles[].data`, and produces a complete second NodeClass. It requires Python 3 with PyYAML. Set `NODE_KMS_KEY_ARN` and `CA_BUNDLE_FILE`, and retain the reviewed `AWS_REGION`/`EXPECTED_ACCOUNT_ID` from the previous chapter.

Approve the CA issuer, fingerprints and validity separately. The syntax check below does not establish trustworthiness, KMS permissions or cloud resource existence. Review the key policy/IAM grants and the Pod-network tag selections before applying the result.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed cluster region}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${NODE_KMS_KEY_ARN:?Set the approved same-region customer-managed KMS key ARN}"
: "${CA_BUNDLE_FILE:?Set the path to an approved public CA PEM bundle}"
export AWS_REGION EXPECTED_ACCOUNT_ID NODE_KMS_KEY_ARN CA_BUNDLE_FILE
umask 077
python3 - <<'PY'
import base64, json, os, re, ssl
from pathlib import Path
import yaml

doc = yaml.safe_load(Path("custom-nodeclass.yaml").read_text())
if doc.get("kind") != "NodeClass" or doc.get("apiVersion") != "eks.amazonaws.com/v1":
    raise SystemExit("Expected the reviewed Auto Mode NodeClass template")
spec = doc["spec"]
if ("role" in spec) == ("instanceProfile" in spec):
    raise SystemExit("Set exactly one reviewed role or instanceProfile")
key = os.environ["NODE_KMS_KEY_ARN"]
prefix = "arn:aws:kms:" + os.environ["AWS_REGION"] + ":" + os.environ["EXPECTED_ACCOUNT_ID"] + ":key/"
if not key.startswith(prefix) or not re.fullmatch(r"(?:[a-f0-9-]{36}|mrk-[a-f0-9]{32})", key[len(prefix):]):
    raise SystemExit("KMS key ARN must match the reviewed account and region")
pem = Path(os.environ["CA_BUNDLE_FILE"]).read_bytes()
if b"PRIVATE KEY" in pem:
    raise SystemExit("Use public CA certificates only, never a private key")
ssl.create_default_context().load_verify_locations(cadata=pem.decode("ascii"))
doc["metadata"]["name"] = "secure-network-nodeclass"
spec["ephemeralStorage"]["kmsKeyID"] = key
spec["certificateBundles"] = [{"name": "corporate-ca",
                               "data": base64.b64encode(pem).decode("ascii")}]
spec["podSubnetSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
spec["podSecurityGroupSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
Path("secure-network-nodeclass.json").write_text(json.dumps(doc, indent=2) + "\n")
PY
```

| Field | Meaning |
|-------|---------|
| `ephemeralStorage.kmsKeyID` | Customer-managed key for node root/data EBS volumes; use a key in the cluster's region |
| `certificateBundles[].data` | Base64-encoded certificate bundle for node trust; it does not automatically alter every application's container trust store |
| `podSubnetSelectorTerms` | Separate Pod subnets selected for this NodeClass |
| `podSecurityGroupSelectorTerms` | Pod network security groups; configure together with Pod subnet selectors |

The Pod subnet and security-group selectors must be configured together, with compatible VPC/AZ coverage. The arrangement is per NodeClass, not per namespace or ServiceAccount. Host-network traffic uses node networking; egress SNAT can also change the source address and applicable security groups. Review routing, SNAT and Pod-density effects before claiming that all traffic is isolated.

## Separate Workloads and Environments

### Frontend and backend pools

Taints keep Pods without matching tolerations off these nodes. Tolerations only permit scheduling; add a selector or required affinity when a workload must use its designated nodes.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      taints:
      - key: workload-tier
        value: frontend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      taints:
      - key: workload-tier
        value: backend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 800Gi
```

For example, create an owned `nodepool-lab` namespace and use both a selector and toleration for a frontend placement check:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend-placement-check
  namespace: nodepool-lab
spec:
  automountServiceAccountToken: false
  nodeSelector:
    workload-tier: frontend
  tolerations:
  - key: workload-tier
    operator: Equal
    value: frontend
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
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
      periodSeconds: 5
```

Review before applying: this Pod can cause billed node provisioning. Check its assigned node, readiness and node labels, then delete the test Pod from that namespace. `NoSchedule` does not evict an already running Pod, and labels/taints alone are not a security boundary between untrusted tenants.

### Development pool

The current AWS supported-instance list includes T-family burstable types as well as M-family types. Do not remove T solely based on older Auto Mode assumptions. Auto Mode requires more than one CPU and excludes nano/micro/small sizes; still verify regional type availability, CPU-credit behavior and workload suitability.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - t
        - m
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - medium
        - large
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      taints:
      - key: environment
        value: development
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 1
```

## Resource Limits, Weights and Validation

`limits.cpu` and `limits.memory` bound aggregate pool resources; they are not a maximum node count or a currency budget. Quote CPU quantities to avoid integer/string GitOps drift. For example, `memory: 4000Gi` is 4000 GiB (about 3.91 TiB), not exactly 4 TB.

Upstream Karpenter documents eventual consistency and possible limit overruns during rapid provisioning. Do not promise an instantaneous billing cap from these fields. Leave replacement headroom, monitor usage and test the behavior of the managed environment.

`weight` influences provisioning preference among eligible pools. It does not give a node Kubernetes scheduler priority, evict existing workloads, or force a Pod to use a particular pool. Use explicit workload constraints and avoid unintended overlap.

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

Server dry-run can check admission but does not prove IAM, network connectivity, provisioning, storage or application behavior. Resolve false/unknown readiness conditions and validate controlled workloads before production use.

## References

- [Built-in NodePools](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Auto Mode NodePool fields and labels](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode NodeClass specification](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Managed instance types and IMDS restrictions](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Auto Mode node security](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [Upstream Karpenter NodePool limits](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter weighted provisioning](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [Node CA, KMS and network features](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [Previous: Getting Started](./01-getting-started.md) | [Table of Contents](./README.md) | [Next: Scaling Behavior](./03-scaling-behavior.md) >
