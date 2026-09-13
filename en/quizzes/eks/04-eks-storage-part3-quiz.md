# EKS Storage Part 3 Quiz

> **Last Updated**: September 11, 2026

Review monitoring, diagnosis, cost and security using the chapter’s configured collectors and storage examples. The examples below were checked locally; they are not claims of executed AWS operations, production recovery or live dashboard verification. Replace placeholders and confirm resource ownership before deployment.

## Multiple Choice Questions

### 1. Which calculation gives read IOPS from VolumeReadOps?

- A. Use Average as IOPS directly
- B. Divide Sum by period seconds
- C. Multiply bytes by the number of Pods
- D. Use VolumeQueueLength as completed IOPS

<details>
<summary>Show Answer</summary>

**Answer: B**

Use Sum divided by the period in seconds. VolumeReadBytes/VolumeWriteBytes need the same normalization for bytes/s. VolumeTotalReadTime/VolumeTotalWriteTime are accumulated operation seconds: divide Sum by matching operation Sum for mean seconds/op, with zero-operation handling. Do not label every raw counter as a rate or latency.

Current Nitro metrics also include VolumeAvgIOPS, VolumeAvgThroughput and average-latency metrics with their documented units/restrictions. BurstBalance applies to gp2/st1/sc1, not gp3. EFS byte/metered-byte metrics and FSx per-OSS/per-OST metrics have different dimensions/statistics. kubelet_volume_stats_* may supply filesystem usage where supported; container_fs_usage_bytes is not a universal PVC measurement.

</details>

### 2. What should you check first for a Pending PVC/consumer?

- A. Delete the PVC immediately
- B. Grant every node full EC2 access
- C. Inspect events, binding mode and scheduling constraints
- D. Assume an unbound PVC already fixes the AZ

<details>
<summary>Show Answer</summary>

**Answer: C**

Inspect the actual namespace, claim, consumer events, class and topology. WaitForFirstConsumer can intentionally keep a new PVC Pending until scheduling; it is not automatically a driver failure. After binding, EBS PV node affinity/AZ and attachment limits matter. Avoid spec.nodeName when it bypasses the scheduler needed for binding.

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

Check the driver’s actual Pod Identity/IRSA role and KMS grants, not just the EC2 node instance profile. A multi-container controller requires selecting the relevant driver/sidecar log. ContainerCreating may instead reflect attach, mount, client software, image pull or application permissions. Do not delete data to reset the symptom.

</details>

### 3. Which approach is appropriate for database storage tuning?

- A. Measure and match volume, filesystem and instance constraints
- B. Always enable multiAttach:true
- C. Assume any hostPath is fast NVMe
- D. Change the root disk scheduler without identifying it

<details>
<summary>Show Answer</summary>

**Answer: A**

Measure the I/O pattern, queueing, latency and instance limits, then select storage/performance settings. This10,000IOPS io2 class is an illustrative allocation, not evidence that it meets a database SLO:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '10000'
```

Multi-Attach is not a generic read-only performance switch. The reviewed EBS CSI path uses io2, RWX and raw Block with application coordination, as described in Part2. A hostPath named /mnt/instance-store does not establish that it is physical instance store; use a prepared node-local storage design and treat its data as ephemeral. EC2 instance-store CSI is a real supported integration, with its own prerequisites.

Do not write noop to a guessed nvme0n1 scheduler: that may be the root/another disk, and modern blk-mq names differ. Identify the device and supported scheduler before a separately reviewed change. Filesystem choice and mount options also need workload evidence; neither XFS nor ext4 guarantees a performance result.

</details>

### 4. Does creating a default gp3 class migrate existing gp2 volumes?

- A. Yes, all attached volumes change immediately
- B. Yes, but only after renaming the class
- C. Yes, default classes encrypt/migrate old data
- D. No; existing volumes need a separate supported workflow

<details>
<summary>Show Answer</summary>

**Answer: D**

No. A StorageClass controls applicable provisioning; it does not rewrite every bound PV/backend. Default-class changes can affect unrelated new claims. Choose an owned supported modification or data migration, retain recovery points and validate application data. Capacity expansion and capacity reduction are different operations; PVC/EBS size cannot generally be shrunk in place.

Compare allocated capacity, provisioned IOPS/throughput, retention, requests and transfer costs. Compute discounts do not automatically reduce separate storage charges. A VolumeSnapshotClass is not a schedule; this example only defines deletion behavior for deliberately temporary snapshots:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: temporary-ebs-snapshots
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

Do not replace the chapter’s retained class with this temporary class as a blanket cost optimization. A backup owner must schedule and manage retention; Velero has its own CSI snapshot lifecycle.

</details>

### 5. Which statement correctly separates storage security controls?

- A. A PVC name guarantees encryption
- B. Each control needs its own correct scope and actual resource mapping
- C. A Role can grant every cluster PV permission
- D. PSS replaces IAM and KMS

<details>
<summary>Show Answer</summary>

**Answer: B**

IAM/KMS, network access, Kubernetes API authorization, admission and filesystem identities protect different operations. A region-only EC2 action list is not automatically a complete least-privilege CSI policy. Use the actual driver role policy and required key grants. A fake kmsKeyId does not create a KMS key.

Namespaced Roles can grant PVC access, not cluster-scoped PV access. A Pod creator may be able to mount namespace PVCs even without reading their object through this particular Role; protect workload creation and tenant boundaries too. The chapter’s namespace reader is an object inspection example:

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

EFS SGs apply to real mount targets/clients, not an invented securityGroupSelector fragment. Use the actual TCP2049 path; Lustre/EFA rules differ. Pod Security Standards do not establish cloud encryption or IAM permissions.

</details>

### 6. Which monitoring integration statement is correct?

- A. A Grafana ConfigMap automatically collects PVC metrics
- B. Prometheus always retains data forever
- C. Collectors, discovery, authorization and storage must be configured
- D. CloudWatch can never receive custom metrics

<details>
<summary>Show Answer</summary>

**Answer: C**

CloudWatch covers native service metrics; Prometheus can collect configured Kubernetes/application targets; Grafana visualizes configured data sources. Collectors, Service discovery, IAM/auth, retention, labels and alert routing still have to be configured. No dashboard ConfigMap creates the missing metrics by itself.

CloudWatch can ingest custom/Kubernetes metrics through a configured agent or integration, and Prometheus is not automatically a durable long-term store. Use retention and storage/remote-write architecture appropriate to the workload. Automated management should start with observation and bounded proposals, not unconditional changes.

</details>

### 7. Which observation authorizes volume deletion by itself?

- A. PV is Available
- B. PVC has no currently listed Pod
- C. A lastUsed annotation is old
- D. None of these alone

<details>
<summary>Show Answer</summary>

**Answer: D**

Retained data, scale-to-zero controllers, future Jobs, backup obligations and external owners can all matter. lastUsed is not a standard trustworthy PVC usage field. Preserve namespace/UID and review backend identity before any cleanup.

</details>

### 8. Does kubectl top pods measure PVC disk usage?

- A. No; it primarily reports CPU/memory
- B. Yes; memory usage equals disk usage
- C. Yes; it lists every EBS free block
- D. Only when the class is named gp3

<details>
<summary>Show Answer</summary>

**Answer: A**

Use supported filesystem statistics from the correct mounted path/driver and identify the actual PVC. df in a container may describe a different mount or the shared EFS filesystem; an EFS PVC request is not a per-directory quota.

</details>

### 9. How is EFS IA/Archive lifecycle configured?

- A. With arbitrary performanceMode parameters on an access-point StorageClass
- B. Through the filesystem lifecycle configuration, preserving intended transitions
- C. By reducing a PVC request
- D. By changing a Pod label to IA

<details>
<summary>Show Answer</summary>

**Answer: B**

EFS CSI access-point parameters do not configure every filesystem throughput or lifecycle property. Read existing policies before updating the array; an empty array disables lifecycle management. Elastic is the recommended starting point for unpredictable demand, while Archive availability and transition ordering have specific requirements.

</details>

### 10. What does aws s3 cp --sse AES256 select?

- A. TLS protocol version
- B. NetworkPolicy encryption
- C. SSE-S3 at-rest encryption
- D. EFS mount encryption

<details>
<summary>Show Answer</summary>

**Answer: C**

HTTPS/TLS protects transport; --sse does not enable it. Use the proper endpoint and certificate validation. FSx scratch data is encrypted with service-managed keys, while selectable customer keys are a persistent-filesystem choice.

</details>

## Short Answer Questions

### 11. How should rate calculations and capacity forecasts be validated?

<details>
<summary>Show Answer</summary>

**Answer: Check units, periods, missing data and representative scenarios**

For a300-second interval,30,000 completed read operations represent100 read IOPS.1,500 accumulated read seconds divided by30,000 operations is0.05seconds/op, or50milliseconds. Overlapping operations can make accumulated time exceed wall-clock time. Use aligned periods and handle zero/no samples separately.

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

These are arithmetic examples, not measured workload results. Forecast gauges with predict_linear, not counters; deduplicate redundant scrape series and exclude invalid capacity. A recent trend is not a guarantee of future exhaustion. The source rules were tested against sustained high usage, duplicate targets, zero capacity, missing series and increasing usage using synthetic data.

</details>

### 12. How do CSI identity, Multi-Attach and node-local storage differ?

<details>
<summary>Show Answer</summary>

**Answer: They solve authorization, attachment and placement problems respectively**

The CSI controller identity authorizes backend lifecycle APIs; it is not every application’s identity. EBS Multi-Attach provides shared raw-device attachment under service/driver/AZ restrictions and needs application write coordination/fencing. A random multiAttach StorageClass field is not a supported switch.

Node-local instance store is physically tied to a node lifecycle and requires correct device provisioning/scheduling. A hostPath string does not prove its backing device or durability. Reuse the chapter’s reviewed CSI paths instead of granting privilege or formatting a guessed disk to make a performance example run.

</details>

### 13. What can admission and EKS audit logging prove?

<details>
<summary>Show Answer</summary>

**Answer: Only their configured request scope and recorded events**

The chapter’s Kyverno policies.kyverno.io/v1 ValidatingPolicy checks the declared encrypted parameter on matching EBS StorageClasses. It does not inspect existing AWS volumes, static PV contents or every bypass path. Restrict administrative permissions and verify actual backend encryption in addition to admission.

EKS manages the control-plane audit policy; enable the supported audit log type through the cluster owner and inspect the delivered records. A pasted audit.k8s.io policy fragment is not an EKS API for replacing the managed policy. Kubernetes audit events and CloudTrail backend API events are complementary, with separate retention, access and coverage. Audit logging does not prevent data loss by itself.

</details>

## Hands-on Questions

### 14. Create a reviewable monitoring/dashboard configuration.

<details>
<summary>Show Answer</summary>

**Answer: Configure each dependency explicitly**

Use the chapter’s reviewed monitoring stack and collectors; do not assume a ConfigMap alone installs an agent. For a traditional CloudWatch agent installation, inspect its actual namespace/workload and identity. Adapt these names to the chosen integration and compute support:

```bash
set -euo pipefail
kubectl -n amazon-cloudwatch get daemonsets,pods
kubectl -n amazon-cloudwatch get serviceaccount cloudwatch-agent -o yaml
```

The [cluster monitoring example](../../eks/02-eks-cluster-creation-part3.md) covers the owned agent/add-on prerequisites. A StatsD receiver does not automatically produce EBS/PVC metrics. Do not add static AWS keys or enable a duplicate agent to fill a dashboard gap.

For EBS CSI, enable the supported metrics configuration through its existing owner. Use the chapter’s generated monitors **or** the standalone monitor below when the existing Service is present; avoid duplicate scraping. Prometheus must select the monitor namespace/labels and reach its named Service port:

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

Install the chapter’s recording/alert rules through the monitoring owner, then verify target Up status, expected series and alert delivery. An EBS driver endpoint reports CSI operation metrics, not every sidecar metric or raw filesystem usage.

This ConfigMap contains a **Classic dashboard model** for deployments that support that import/provisioning path. Current Grafana also has V1 Resource and default V2 Resource models; do not send this raw Classic object to a different API expecting a resource envelope. Replace the Prometheus data-source UID, ensure the source recording rules exist, and match the Grafana sidecar’s label/namespace configuration. Export/import against the target Grafana version before adopting it:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: storage-dashboard-reviewed
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  storage-dashboard.json: |
    {
      "id": null,
      "uid": "eks-storage-reviewed",
      "title": "EKS Storage: PVC Filesystem Usage",
      "tags": [
        "storage"
      ],
      "timezone": "browser",
      "schemaVersion": 42,
      "version": 1,
      "refresh": "30s",
      "time": {
        "from": "now-6h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "type": "timeseries",
          "title": "PVC filesystem utilization",
          "gridPos": {
            "x": 0,
            "y": 0,
            "w": 24,
            "h": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "(pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max) and (pvc:storage_capacity_bytes:max > 0)",
              "legendFormat": "{{cluster}} {{namespace}}/{{persistentvolumeclaim}}"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percentunit",
              "min": 0,
              "max": 1
            },
            "overrides": []
          }
        }
      ]
    }
```

For additional native EBS IOPS/EFS throughput panels, configure the CloudWatch data source with reviewed IAM access and use the source’s metric dimensions/period-normalized math. Do not invent aws_ebs_* Prometheus series unless a configured exporter actually publishes those names and semantics. The JSON and expressions here were inspected locally; no authenticated Grafana import or live AWS query was performed.

</details>

### 15. Produce a storage inventory without unsafe cleanup assumptions.

<details>
<summary>Show Answer</summary>

**Answer: Report evidence; do not infer deletion eligibility**

Replace the old placeholder CronJob with a read-only report. The following script keeps namespace and UID, lists direct Pod references and explicitly refuses to authorize deletion. It does not infer age from lastUsed, consider Bound synonymous with unused, or drop namespaces from an all-namespace query.

```python
"""Report direct Pod/PVC references; never infer deletion eligibility."""
import json,sys
def inventory(namespace,claims,pods):
    refs={}
    for pod in pods['items']:
        meta=pod['metadata']
        if meta['namespace']!=namespace:raise ValueError('Pod list contains another namespace')
        seen=set()
        for volume in pod.get('spec',{}).get('volumes',[]):
            claim=volume.get('persistentVolumeClaim',{}).get('claimName')
            if claim and claim not in seen:
                seen.add(claim)
                refs.setdefault(claim,[]).append({'pod':meta['name'],'podUID':meta['uid'],'phase':pod.get('status',{}).get('phase','Unknown')})
    rows=[]
    for pvc in claims['items']:
        meta,spec=pvc['metadata'],pvc.get('spec',{})
        if meta['namespace']!=namespace:raise ValueError('PVC list contains another namespace')
        rows.append({'namespace':namespace,'name':meta['name'],'uid':meta['uid'],
          'phase':pvc.get('status',{}).get('phase','Unknown'),'volumeName':spec.get('volumeName'),
          'storageClassName':spec.get('storageClassName'),'requestedStorage':spec.get('resources',{}).get('requests',{}).get('storage'),
          'directPodReferences':refs.get(meta['name'],[]),'ownerReferences':meta.get('ownerReferences',[]),
          'deletionAuthorized':False,'nextAction':'Review owner, controller templates, retention, backups and actual backend before any change'})
    return {'reviewOnly':True,'namespace':namespace,'rows':sorted(rows,key=lambda x:x['name']),
      'limitations':['The two API reads are not an atomic snapshot.','No Pod reference does not mean unused: scale-to-zero controllers, future Jobs, retained data and indirect/ephemeral references need separate review.','lastUsed is not a standard trustworthy Kubernetes PVC field. This report never authorizes snapshot creation or deletion.']}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: storage-inventory.py namespace pvcs.json pods.json')
    with open(sys.argv[2]) as f:claims=json.load(f)
    with open(sys.argv[3]) as f:pods=json.load(f)
    print(json.dumps(inventory(sys.argv[1],claims,pods),indent=2))
```



```bash
set -euo pipefail
: "${STORAGE_NAMESPACE:?Set the namespace being reviewed}"
kubectl -n "$STORAGE_NAMESPACE" get pvc -o json > inventory-pvcs.json
kubectl -n "$STORAGE_NAMESPACE" get pods -o json > inventory-pods.json
python3 storage-inventory.py "$STORAGE_NAMESPACE" inventory-pvcs.json inventory-pods.json
```

The querying identity only needs read permissions for this namespace. This Role is a scope example; bind it to the reviewed operator/automation identity if needed. It does not grant snapshot creation, resizing or deletion:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: storage-inventory-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - persistentvolumeclaims
  verbs:
  - get
  - list
```

Review scale-to-zero controller templates, Jobs/CronJobs, retained claims, indirect/ephemeral references, backup policy and actual backend IDs separately. No current Pod reference is not a deletion decision. If later scheduling this report, use a real reviewed image containing the script/client, bounded execution, scoped credentials and a defined report destination; storage-tools:latest and ellipsis commands are not an implementation.

Automate observation first, then bounded change proposals and independently validated recovery. EBS/PVC growth is not arbitrary scale-down. Keep audit evidence, lifecycle ownership and explicit approval/operational controls appropriate to the deployment rather than a script that silently destroys resources.

</details>

## Review Your Answers

There are15 questions, including10 multiple-choice questions. Use incorrect answers to identify topics to revisit; a quiz score alone does not establish production expertise. For hands-on answers, assess assumptions, resource scope and validation evidence as well as syntax.

## References

- [Source chapter](../../eks/04-eks-storage-part3.md)
- [EBS metrics](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [FSx metrics](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [EFS lifecycle API](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [EKS auditing](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)
- [Grafana dashboard models](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)
