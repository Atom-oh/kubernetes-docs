# Amazon EKS Storage - Part 3: Monitoring, Troubleshooting, Cost Optimization, and Security

> **Last Updated**: September 11, 2026

This document is the third and final part of the Amazon EKS storage series, covering storage monitoring, troubleshooting, cost optimization, and security.

## Table of Contents

1. [Storage Monitoring](#storage-monitoring)
2. [Storage Troubleshooting](#storage-troubleshooting)
3. [Storage Cost Optimization](#storage-cost-optimization)
4. [Storage Security](#storage-security)
5. [Storage Management Best Practices](#storage-management-best-practices)

## Storage Monitoring

Combine backend, Kubernetes and application observations. Backend I/O counters do not measure filesystem free space, and Kubernetes readiness does not establish database consistency. Record units, dimensions, aggregation periods and missing-data behavior before creating an alarm.

<!-- Diagram repair pending: ServiceMonitor configures Prometheus discovery; node-exporter is not a PVC usage exporter.
![Diagram showing three parallel EKS storage-monitoring pipelines: AWS CloudWatch turning EBS, EFS and FSx for Lustre metrics into key monitoring metrics, alarms and a dashboard; Prometheus feeding ServiceMonitor/PodMonitor discovery into Grafana plus PrometheusRule alert rules; and a volume-usage exporter DaemonSet driving custom metrics and alerts.](../.gitbook/assets/en-eks-04-eks-storage-part3-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-0.html)
-->

### Monitoring with CloudWatch

EBS/EFS/FSx publish their service metrics without a Kubernetes exporter. CloudWatch query/visualization access still needs the appropriate IAM permissions. A get-dashboard call retrieves an already existing dashboard definition; it does not create a dashboard or enable metrics.

#### EBS Volume Metrics

| Metric | Correct interpretation |
|---|---|
| VolumeReadBytes / VolumeWriteBytes | Sum is bytes transferred during the selected period; divide by period seconds for bytes/s |
| VolumeReadOps / VolumeWriteOps | Sum is completed operations; divide by period seconds for IOPS |
| VolumeTotalReadTime / VolumeTotalWriteTime | Sum is accumulated operation seconds; divide by the corresponding operation Sum for mean seconds/op, guarding zero operations |
| VolumeQueueLength | Pending I/O gauge; Average/Maximum help distinguish sustained queues and peaks |
| BurstBalance | Remaining credits for gp2, st1 and sc1; not a gp3 credit metric |

For supported Nitro attachments, current metrics also include VolumeAvgIOPS (Ops/s), VolumeAvgThroughput (KiB/s), VolumeAvgReadLatency/VolumeAvgWriteLatency (milliseconds), and exceeded/stalled-I/O checks. Check each metric’s Multi-Attach, compute and zone restrictions. Standard volume metrics are published for attached volumes; missing data is not automatically zero usage. The existing time counters can exceed the wall-clock period when operations overlap.

#### EFS File System Metrics

TotalIOBytes, DataReadIOBytes, DataWriteIOBytes and MetadataIOBytes describe bytes, not an already normalized transfer rate. Divide the appropriate Sum by the period for bytes/s. MeteredIOBytes reflects EFS throughput metering, including read discounts; it is not interchangeable with raw transferred bytes. PermittedThroughput is a rate. Compare matching periods/units, and monitor ClientConnections, mode-appropriate PercentIOLimit and storage classes as needed. BurstCreditBalance applies to Bursting throughput, not Elastic throughput.

#### FSx for Lustre Metrics

DataReadBytes/DataWriteBytes and DataReadOperations/DataWriteOperations use FileSystemId; Sum/period gives throughput or operations/s. **NetworkThroughputUtilization is valid**: it is per object storage server (OSS), with FileSystemId and FileServer dimensions, and reports percent utilization. FreeDataStorageCapacity is per OST with FileSystemId and StorageTargetId. Inspect per-target imbalance and aligned capacity gauges; summing a gauge over time does not give current free capacity.

LogicalDiskUsage and PhysicalDiskUsage are also valid metrics: they describe uncompressed logical and compressed physical bytes. Their filesystem-level aggregation helps assess compression; it does not turn provisioned-capacity pricing into usage-only pricing.

### Monitoring with Prometheus and Grafana

Reuse the monitoring owner’s existing stack. For a new reviewed installation, the published kube-prometheus-stack90.1.1 chart is a verified reference with operator0.93.1; it is not an automatic upgrade instruction for an existing cluster. The following renders manifests only. Prepare `monitoring/grafana-admin` with admin-user/admin-password keys and the chapter’s expandable ebs-gp3 class. Adjust the actual cluster version, storage sizing and retention. Alert delivery, Grafana persistence, availability and kubelet TLS/auth defaults still need deployment-specific review:

```yaml
grafana:
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
prometheus:
  prometheusSpec:
    retention: 14d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ebs-gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 20Gi
```



```bash
set -euo pipefail
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm template prometheus prometheus-community/kube-prometheus-stack \
  --version 90.1.1 --namespace monitoring --kube-version 1.36.0 \
  --include-crds -f monitoring-values.yaml > monitoring-review.yaml
```

A ServiceMonitor selects **Services**, then their endpoints; its namespaceSelector and the Prometheus instance’s ServiceMonitor selectors must both match. EBS CSI1.66’s Helm chart defaults controller.enableMetrics to false. For an installation managed by that chart, review these values with its existing owner; they enable the driver’s3301 metrics endpoint, sidecar metrics Services and generated ServiceMonitors. Match the release label to the actual Prometheus selector:

```yaml
controller:
  enableMetrics: true
  serviceMonitor:
    labels:
      release: prometheus
```

An EKS managed add-on may expose different configuration options; inspect its version/configuration and actual resources instead of applying Helm values to it. The following standalone ServiceMonitor is an **alternative** only when the owner already exposes the shown Service and has not created a matching monitor. Do not deploy it alongside an equivalent generated monitor:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: csi-metrics-reviewed
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
    - kube-system
  selector:
    matchLabels:
      app: ebs-csi-controller
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```



```bash
set -euo pipefail
kubectl -n kube-system get svc ebs-csi-controller -o yaml
kubectl -n kube-system get endpointslice \
  -l kubernetes.io/service-name=ebs-csi-controller -o wide
kubectl -n monitoring get prometheus -o yaml
```

Confirm the selected target is Up and exposes the intended metrics. The driver and provisioner/attacher/resizer/snapshotter have separate metric endpoints; one driver Service does not collect every sidecar. CSI API-operation latency is distinct from application/EBS data I/O latency.

### Filesystem Usage and Alerting

Use authenticated kubelet metrics for kubelet_volume_stats_* where the CSI driver implements the required volume statistics. kube-state-metrics supplies object state/request information, and node-exporter supplies host filesystem metrics; installing another node-exporter DaemonSet does not create per-PVC usage metrics. kube-prometheus-stack already includes a node-exporter option. Avoid duplicating its host mounts and privileges.

Raw block volumes and drivers without stats support may not publish filesystem capacity. EFS access-point/PVC requests are not per-directory quotas; reported capacity can describe the shared filesystem. container_fs_usage_bytes is not a universal PVC measurement. Verify the collector, mount and namespace/claim mapping, and handle missing metrics separately.

The following rules deduplicate equivalent scrapes with max rather than summing duplicate claims. Federated data must include a reliable cluster label. Capacity-zero series are excluded. Forecasts use gauges and recent trends; review scrape gaps, claim recreation/resizing and workload changes before acting. Adapt selectors for read-only/static datasets or other claims that should not page an operator:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: storage-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: storage-reviewed
    rules:
    - record: pvc:storage_used_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes)
    - record: pvc:storage_capacity_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_capacity_bytes)
    - alert: VolumeUsageHigh
      expr: (pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max > 0.85) and
        (pvc:storage_capacity_bytes:max > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Volume usage high ({{ $value | humanizePercentage }})
        description: PVC {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim
          }} requires capacity review.
    - alert: VolumeMayFillIn24Hours
      expr: (predict_linear(pvc:storage_used_bytes:max[6h], 86400) > pvc:storage_capacity_bytes:max)
        and (pvc:storage_capacity_bytes:max > 0) and (delta(pvc:storage_used_bytes:max[1h])
        > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Recent trend projects capacity exhaustion
        description: Review the trend and workload for PVC {{ $labels.namespace }}/{{
          $labels.persistentvolumeclaim }}; this is not a guarantee.
```

The namespace/release labels must match the Prometheus rule selector. Validate rule syntax and synthetic scenarios, then verify live metric coverage and alert routing in the intended deployment. No live metric collection or alert delivery was executed in this review.

## Storage Troubleshooting

Start with object identity and events. Pending, ContainerCreating and slow I/O can have different causes; image pulls, scheduling and application readiness are not necessarily storage failures. The diagram is a triage guide, not an exhaustive mapping of symptoms to causes.

![Four common EKS storage issues (PVC pending, provisioning failure, mount issues, performance issues) routed in two groups to shared diagnostic checks and fix actions: CSI driver logs, IAM permissions and StorageClass for the provisioning pair, node status for the mount and performance pair.](../.gitbook/assets/en-eks-04-eks-storage-part3-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-1.html)

### Provisioning and WaitForFirstConsumer

Use the workload’s actual namespace, claim and intended consumer. Inspect the referenced class, controller events, driver identity/KMS permissions, quotas and node attachment limits rather than granting broad access on a guess:

```bash
set -euo pipefail
: "${NAMESPACE:?Set the workload namespace}"
: "${PVC_NAME:?Set the claim name}"
: "${POD_NAME:?Set its intended consumer Pod}"
kubectl -n "$NAMESPACE" get pvc "$PVC_NAME" -o yaml
kubectl -n "$NAMESPACE" describe pvc "$PVC_NAME"
kubectl -n "$NAMESPACE" describe pod "$POD_NAME"
kubectl get storageclass
kubectl get nodes -L topology.kubernetes.io/zone
```



```bash
set -euo pipefail
: "${CSI_CONTROLLER_POD:?Select the actual controller Pod}"
: "${CSI_CONTAINER:?Select the relevant driver/sidecar container}"
kubectl -n kube-system get pod "$CSI_CONTROLLER_POD" \
  -o jsonpath='{.spec.containers[*].name}'
kubectl -n kube-system logs "$CSI_CONTROLLER_POD" -c "$CSI_CONTAINER" --since=15m --tail=200
```

WaitForFirstConsumer intentionally leaves a new PVC Pending until a schedulable consumer determines topology. A new unbound PVC does not already have an AZ to which a node pool must be moved. Inspect Pod selectors, affinity, taints, resources and storage topology. Using spec.nodeName bypasses the scheduler and can prevent this binding path; use supported scheduling constraints. Once bound, an EBS PV’s AZ/node affinity matters. Do not delete a claim or edit PV capacity merely to clear Pending.

### Mount Failures

Distinguish attach errors, node publish/mount errors, missing filesystem clients, identity/permission errors and application permissions. Select the relevant CSI driver/sidecar container when reading logs; a multi-container Pod’s default log is not every component. Inspect VolumeAttachment, the bound PV’s driver/handle and the assigned node as needed.

For node logs, use the node owner’s supported access/diagnostic mechanism. SSH as ec2-user and journalctl are not universal for Bottlerocket, Auto Mode or other managed compute. A privileged amazonlinux:2 helper is not a replacement for the correct CSI/client setup; AL2 is past its2026 OS support end. Reuse the chapter’s supported CSI consumer test and inspect its events before considering a separately approved node-level manual mount.

For EFS, inspect mount targets/DNS and TCP2049 from the actual mount client. Lustre requires TCP988 and1018–1023 plus the service’s client/server rules; EFA configurations have additional SG-reference requirements. Check NACL return traffic and routes too. ICMP ping failure is not proof that NFS is unavailable, and an AWS CLI container is not guaranteed to contain ping/telnet/mount helpers. A Pod network test may use a different source/security group from a node-originated CSI mount.

### Slow I/O

Check measured operation size, queueing, application concurrency, provisioned volume performance, instance EBS limits and initialization state. The following portable Python time calculation uses closed five-minute intervals; VolumeReadOps Sum/300 is read IOPS, unlike Average interpreted directly as a rate:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the volume Region}"
: "${EBS_VOLUME_ID:?Set the verified owned EBS volume ID}"
read -r START_TIME END_TIME < <(python3 - <<'PY'
import datetime, time
end = int(time.time()) // 300 * 300
fmt = lambda value: datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(fmt(end - 3600), fmt(end))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --namespace AWS/EBS --metric-name VolumeReadOps \
  --dimensions "Name=VolumeId,Value=$EBS_VOLUME_ID" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --period 300 --statistics Sum --output json > ebs-read-ops.json
python3 - ebs-read-ops.json <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    points = json.load(stream)["Datapoints"]
for point in sorted(points, key=lambda p: p["Timestamp"]):
    print(point["Timestamp"], "read IOPS:", point["Sum"] / 300)
if not points:
    print("No datapoints: check dimensions, attachment/activity, Region and publication delay")
PY
```

A filesystem write test must use an approved disposable directory on the verified mount. Save this script inside the intended test environment; it creates a unique64MiB file and cleans up only its own file/directory. The read can hit cache, so these timings do not establish cold-storage performance. Do not run a predictable `/data/test` overwrite or raw-device zero write on live data:

```bash
set -euo pipefail
: "${STORAGE_TEST_DIR:?Set an approved disposable directory on the verified disposable filesystem mount}"
test -d "$STORAGE_TEST_DIR" && test -w "$STORAGE_TEST_DIR"
STORAGE_TEST_PATH=$(mktemp -d "$STORAGE_TEST_DIR/storage-test.XXXXXX")
cleanup() { rm -f -- "$STORAGE_TEST_PATH/payload"; rmdir -- "$STORAGE_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$STORAGE_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$STORAGE_TEST_PATH/payload" of=/dev/null bs=1M
```

No storage benchmark was executed for this review. Treat fragmentation as a hypothesis requiring evidence; recreating/formatting a filesystem is a data migration, not a routine first fix. Do not change a guessed nvme0n1 I/O scheduler: it may be another volume/root device, and modern blk-mq scheduler names/support differ.

For EFS, General Purpose and the actual throughput mode, client limits, metadata demand and concurrency matter. Use the supported mount-helper options from Part2, including hard/TLS and appropriate timeout/retry behavior. File bundling or more sequential access may help a measured workload, but changing application data layout is not universally beneficial.

## Storage Cost Optimization

Optimize total workload cost while preserving latency, durability, recovery and ownership requirements. Compute discounts, allocated storage, provisioned performance, request/transfer charges and retained backups are separate costs.

<!-- Diagram repair pending: align each storage service with its actual optimization strategy; do not map S3 to FSx optimization or FSx to EFS optimization.
![Diagram showing four AWS storage types — EBS, EFS, FSx for Lustre, S3 — each feeding its matching optimization strategy (volume optimization, lifecycle management, EFS optimization, FSx optimization), with all four strategies rolling up into a single cost-monitoring node built on Cost Explorer, Kubernetes cost allocation, and anomaly detection.](../.gitbook/assets/en-eks-04-eks-storage-part3-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-2.html)
-->

### Volume Type, Size and Migration

Compare gp3 against the actual gp2 cost/performance profile; consider HDD types only for suitable access patterns. Provision measured headroom and alerts, not arbitrary maximum size. EBS/PVC capacity generally grows rather than shrinks; reducing allocated capacity requires a supported migration to a smaller new volume with data validation.

Creating a gp3 StorageClass or marking it default **does not migrate existing gp2 volumes**. A default-class change also affects unrelated new claims. Reuse the explicitly named class from Part1. For existing volumes, choose the deployed driver’s supported modification workflow or a tested backup/restore migration to a new claim; inspect ownership, application consistency and rollback before changing storage.

### Lifecycle and Retention

A VolumeSnapshotClass defines driver/retention behavior; it neither schedules snapshots nor deletes them by age. Use the backup owner’s schedule and retention policy. Part2 explains Velero’s CSI snapshot lifecycle, including deletion even when the original class was Retain.

A PV marked Available or Released is not automatically disposable, and Bound does not prove active use. Inventory claimRef/UID, workload owners, snapshots, retention obligations and actual backend resources before cleanup. Retain can leave chargeable resources; Delete behavior depends on the driver. Deleting an EFS access point is not the same as deleting its filesystem/data. Tiering files into S3/Archive also requires an application-compatible restore/access plan.

### EFS Cost Optimization

AWS recommends Elastic throughput for unpredictable/spiky workloads. Compare it with Provisioned for known sustained demand and Bursting for its size/credit model, using actual metered I/O and current pricing. General Purpose is the recommended performance mode. Access points can share a filesystem with distinct POSIX identities; they do not reserve per-PVC capacity or provide automatic per-application billing.

Read the entire existing lifecycle configuration before proposing a change:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the filesystem Region}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned filesystem ID}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --output json > efs-filesystem-review.json
aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
  --file-system-id "$EFS_FILE_SYSTEM_ID" --output json > efs-lifecycle-before.json
```

A put-lifecycle-configuration request updates the filesystem configuration; preserve all intended existing transitions in the reviewed array. An empty array disables lifecycle management. Each policy object contains one transition. Archive requires supported General Purpose/Elastic configuration and a transition later than IA. Include IA/Archive access and minimum-duration charges in the cost analysis; do not blindly overwrite an existing policy with a single30-day example.

### FSx for Lustre and Cost Attribution

Choose scratch only for data that can be recreated, and persistent deployment/storage options for the required lifecycle. LZ4 may reduce physical data size, but does not automatically reduce an already provisioned SSD allocation bill; evaluate the selected storage pricing model, compression ratio and throughput/CPU effects. S3 repository integration needs configured import/export/release behavior, not just a bucket name.

Cost Explorer and Kubernetes allocation tools need configured billing data, activated cost-allocation tags where applicable, and a tested mapping from PVC/PV to cloud resource IDs. Namespace labels alone do not automatically tag every AWS charge. Track retained volumes/snapshots, request/transfer costs and telemetry retention. EC2 Reserved Instances/Compute Savings Plans can change eligible compute costs; they do not automatically reduce the separate EBS/EFS/FSx storage bill.

## Storage Security

Protect the backend, node/mount path and Kubernetes control plane separately. A class name, namespace policy or read-only container root does not by itself protect the contents of a writable PVC.

<!-- Diagram repair pending: TLS, at-rest key management, IAM, network rules, RBAC and admission are distinct controls; neither RBAC nor PSS proves backend encryption.
![Diagram showing EBS/FSx, EFS, and S3 storage security feeding data-at-rest and data-in-transit encryption that converge on AWS KMS key management, security groups and IAM roles leading through Kubernetes RBAC to OPA Gatekeeper/Kyverno policy enforcement, and the pod security context enforced by Pod Security Standards.](../.gitbook/assets/en-eks-04-eks-storage-part3-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-3.html)
-->

### Data Encryption

EBS encryption is requested when provisioning a volume; changing a StorageClass does not retroactively encrypt an existing volume. This new-class example requests encrypted gp3 storage with delayed topology binding and explicit retention. If a customer managed key is required, add a real reviewed kmsKeyId and prepare its key policy/driver grants; a sample ARN is not a working key.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

Configure EFS encryption at filesystem creation using the guarded infrastructure workflow in Part1. Existing unencrypted data needs a supported migration to an encrypted filesystem, not a mount option. FSx for Lustre encrypts data at rest automatically: scratch filesystems use service-managed keys; a selectable AWS managed/customer managed KMS key is a **persistent-filesystem** choice. Do not pass a customer kms-key-id to the SCRATCH_2 example.

Inspect the actual cloud resources, matching EBS IDs to bound PV volumeHandles and confirming the account/Region. A scratch FSx response without a selected customer key is not evidence of unencrypted storage:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resources Region}"
: "${EBS_VOLUME_ID:?Identify the actual volume from its bound PV}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned EFS filesystem ID}"
: "${FSX_FILE_SYSTEM_ID:?Set the owned FSx filesystem ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[0].{Id:VolumeId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Type:LustreConfiguration.DeploymentType,KmsKeyId:KmsKeyId}' --output json
```

For data in transit, use the supported EFS CSI/mount-helper `tls` option and verify the actual mount path. FSx transit encryption depends on its supported filesystem/client/instance configuration; follow its service guidance. **S3 HTTPS/TLS protects transport; `aws s3 cp --sse AES256` selects SSE-S3 at-rest encryption.** That flag does not enable TLS. Use HTTPS endpoints and certificate validation, and review bucket policies that require secure transport. KMS key policy is distinct from transport certificate management.

### Access Control

Use the prepared CSI identity from Part1: the controller’s supported Pod Identity/IRSA role and exact driver permissions, plus KMS grants when applicable. Do not recreate an existing managed add-on ServiceAccount through an unrelated eksctl command or move controller permissions onto every node/application. Mountpoint pod-level identity, EFS IAM mounts and filesystem POSIX/access-point identities have different authorization paths.

For network access, allow the actual client/node source security group to reach EFS mount targets on TCP2049. Lustre requires the documented TCP988 and1018–1023 rules between clients and file servers, including required self/client traffic. EFA-enabled Lustre instead needs the specified security-group-referenced all-traffic rules; an internet-wide CIDR is not a substitute. Inspect routes, DNS, NACLs and the true CSI mount source as well as SGs. A Kubernetes Pod NetworkPolicy does not automatically control every node-originated filesystem connection.

The following namespace-scoped reader can inspect PVC objects; it cannot create, resize or delete them. Cluster-scoped PV access needs a separately reviewed ClusterRole. Neither role controls file bytes directly. A principal able to create Pods in a namespace may be able to mount its PVCs, so Pod creation, workload identity, POSIX/access-point permissions and tenant isolation must also be controlled:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: storage-auditor
  namespace: storage-demo
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pvc-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - persistentvolumeclaims
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pvc-reader
  namespace: storage-demo
subjects:
- kind: ServiceAccount
  name: storage-auditor
  namespace: storage-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pvc-reader
```

### Pod Security Context

This complete example separates Pod-level runAsUser/runAsGroup/fsGroup/seccomp from container-level allowPrivilegeEscalation/capabilities/readOnlyRootFilesystem. It uses a prepared encrypted class and a declared PVC, rather than an undefined data volume and an nginx image with unprovided writable runtime paths. The namespace policy version is tied to the reviewed Kubernetes1.36 example; use the policy version appropriate to your cluster.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: secure-data
  namespace: secure-ns
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-encrypted
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: secure-ns
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.37.0
    command:
    - sh
    - -c
    args:
    - test -w /data && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: secure-data
```

Read-only root does not make `/data` read-only: this workload deliberately checks a writable PVC. fsGroup behavior depends on the CSI/filesystem; an EFS access point can enforce a different POSIX identity. SELinux/AppArmor profiles require the actual node/runtime support and prepared policy. Do not copy arbitrary MCS labels or profile names. Pod Security Standards constrain Pod configuration; they do not encrypt cloud volumes or grant IAM permissions. Monitoring/CSI node agents with host access need their own reviewed namespace/security design.

### Security Policy Enforcement

A PVC name pattern or StorageClass allowlist alone cannot prove EBS encryption. The following **Kyverno ValidatingPolicy** uses the served `policies.kyverno.io/v1` API, checked with Kyverno1.19.1 and its CRD. It requires the installed controller/CRD and appropriate admission ownership. Older ClusterPolicy examples are deprecated in that release; migrate intentionally rather than assuming API compatibility.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-declared-ebs-encryption
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - storage.k8s.io
      apiVersions:
      - v1
      resources:
      - storageclasses
      operations:
      - CREATE
      - UPDATE
      scope: Cluster
  validations:
  - expression: '!(object.provisioner in [''ebs.csi.aws.com'', ''ebs.csi.eks.amazonaws.com''])
      || (has(object.parameters) && ''encrypted'' in object.parameters && object.parameters[''encrypted'']
      == ''true'')'
    message: EBS StorageClasses must explicitly request encryption.
```

The policy checks the **declared encryption parameter on EBS StorageClass create/update**, including the Auto Mode provisioner. It does not inspect existing AWS volumes, static PVs, snapshot contents or bypass paths outside its match. Restrict StorageClass/PV administration and use backend compliance checks in addition to admission. Roll out against representative resources and monitor policy reports/webhook health before broad enforcement. Existing-data encryption still requires its own migration.

## Storage Management Best Practices

![Diagram pairing the four storage lifecycle phases — planning, implementation, operation, optimization — with their matching best-practice areas (planning and design, automation and IaC, backup and disaster recovery, performance and cost optimization), each area listing its three practices in order.](../.gitbook/assets/en-eks-04-eks-storage-part3-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-4.html)

### Planning and Capacity

Document latency/IOPS/throughput, capacity growth, read/write patterns, concurrency, availability, durability and RPO/RTO separately. Select block, shared NFS, parallel Lustre or object access from those requirements. Use measured headroom and bounded expansion procedures; an autoscaler or PVC resize does not supply application replication or arbitrary capacity shrink.

### Backup and Disaster Recovery

Use a supported schedule with unique backup identities and a retention owner. A shell cron line repeatedly creating a fixed snapshot name fails after the first object exists; a one-off Velero backup named daily-backup is not a schedule. With the reviewed Velero/CSI installation and database consistency requirements from Part2, this command emits a daily schedule for review:

```bash
velero schedule create storage-daily --schedule="0 0 * * *" \
  --include-namespaces=storage-demo --ttl=720h0m0s -o yaml > storage-schedule-review.yaml
```

Deploy through the owner after review, then alert on missing/failed backups and test isolated restores. A backup in S3 may reference native snapshots rather than contain all volume bytes. Cross-AZ/Region recovery needs accessible data, keys, driver/storage mappings and application validation. Preserve the source until a controlled cutover succeeds; record measured recovery time instead of claiming RPO/RTO from a schedule.

### Infrastructure as Code and GitOps

Use the guarded filesystem creation examples in Part1/Part2 or an owned Terraform/CloudFormation module with reviewed provider/schema versions, subnet/mount-target/security-group configuration and deletion protection. A filesystem-only Terraform resource is not an EKS-ready mount path. Separate backup retention from IaC destroy/prune behavior.

Helm values are chart-specific inputs: a custom `storage.encrypted: true` value does nothing unless a template maps it to the actual supported resource field. Render and validate the resulting StorageClass/PVC/workload before deployment. GitOps pruning, chart uninstall and claim-retention settings can have different effects on data; document which system owns each resource and test lifecycle changes on disposable data.

For example, this filesystem resource requests encryption and Elastic throughput, retains the30-day IA teaching policy and adds a Terraform destroy guard. Replace the creation token with a stable project-specific value, configure the provider/account/Region and add the reviewed network/mount-target resources. prevent_destroy is a Terraform operation guard, not a backup or protection against every external deletion:

```hcl
resource "aws_efs_file_system" "example" {
  creation_token   = "example"
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  encrypted        = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = "ExampleFileSystem"
  }
}
```

### Ongoing Review

Review bottlenecks, provisioning limits, retention costs and security controls as workloads change. Keep cleanup reports read-only until resource ownership, backup/recovery and deletion effects are verified. Alert and propose bounded changes before automating them. The chapter’s examples are locally checked reference configurations; backend performance, admission deployment and recovery still require validation in the intended environment.

## Conclusion

In this document, we covered monitoring, troubleshooting, cost optimization, and security for Amazon EKS storage. Effective storage management is critical to ensuring performance, reliability, and cost-effectiveness of your EKS cluster.

Storage requirements vary by application, so it's important to understand the characteristics of your workload and select the appropriate storage solution. Additionally, you should effectively manage storage resources through regular monitoring, troubleshooting, cost optimization, and security reviews.

## References

- [Amazon EKS Storage Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)
- [Kubernetes Storage Troubleshooting](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-application/#debugging-pods)
- [Kubernetes Storage Security](https://kubernetes.io/docs/concepts/security/)

- [EBS CloudWatch metrics](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [FSx Lustre metric dimensions](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [EFS performance modes](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [EFS lifecycle API](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [FSx encryption at rest](https://docs.aws.amazon.com/fsx/latest/LustreGuide/encryption-at-rest.html)
- [FSx network access](https://docs.aws.amazon.com/fsx/latest/LustreGuide/limit-access-security-groups.html)
- [S3 encryption at rest](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html)
- [Kyverno CEL migration](https://kyverno.io/docs/guides/migration-to-cel/)

## Quiz

To test what you learned in this chapter, try the [topic quiz](../quizzes/eks/04-eks-storage-part3-quiz.md).
