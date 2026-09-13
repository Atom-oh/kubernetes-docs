# EKS Storage Quiz - Part 2

> **Last Updated**: September 11, 2026

This quiz covers storage selection, StatefulSet claims, S3/Mountpoint, cloning, backups and recovery. Examples reuse the chapter’s prepared drivers/classes and dedicated namespaces. Cloud provisioning, database recovery and performance benchmarks were not executed during this review. Inspect ownership and replace placeholders before using examples.

## Multiple Choice Questions

### 1. How should a StatefulSet allocate a separate PVC for each ordinal?

- A. Manually name every claim in a ConfigMap
- B. Use volumeClaimTemplates
- C. Give all replicas the same database directory
- D. Disable the CSI driver

<details>
<summary>Show Answer</summary>

**Answer: B**

`volumeClaimTemplates` gives each StatefulSet ordinal its own claim, named `<template>-<statefulset>-<ordinal>`. A restarted Pod normally reuses its claim, subject to storage topology and claim lifecycle. StatefulSet does not copy database data between replicas.

`OrderedReady` is the default Pod management policy; `Parallel` changes scaling behavior. There is no universal guarantee that every PVC creation/deletion follows Pod order. PVC retention is configurable with `persistentVolumeClaimRetentionPolicy`; Retain is the default, while Delete can remove claims on scale-down/deletion. PV reclaimPolicy is a separate backend lifecycle choice.

The following three replicas only demonstrate independent persistent marker files. They are **not a replicated database**. The headless Service provides identity; this sleeping file demo does not implement an HTTP server on its illustrative service port. Reuse the chapter’s `ebs-gp3` class:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  clusterIP: None
  selector:
    app: stateful-files
  ports:
  - name: unused-demo
    port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  serviceName: stateful-files
  replicas: 3
  podManagementPolicy: OrderedReady
  selector:
    matchLabels:
      app: stateful-files
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: stateful-files
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
      - name: file-owner
        image: busybox:1.37.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          if [ ! -e /data/owner ]; then (set -C; printf "%s\n" "$POD_NAME" > /data/owner); fi
          cat /data/owner
          sleep 3600
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
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        storage-demo: stateful-files
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: ebs-gp3
      resources:
        requests:
          storage: 10Gi
```



```bash
kubectl -n storage-demo get pvc -l storage-demo=stateful-files -o wide
```

The claim-template labels make the inspection selector meaningful. Do not delete retained claims as routine Pod cleanup. WFFC selects a suitable volume AZ from scheduling constraints; it does not make EBS data available in every AZ. RWO is a node-level access constraint, not a one-Pod guarantee; use supported RWOP when one-Pod access is required.

</details>

### 2. What should drive EBS performance selection?

- A. Always choose io1
- B. Measured workload needs and volume/instance limits
- C. Always provision maximum capacity
- D. Put every application in one AZ

<details>
<summary>Show Answer</summary>

**Answer: B**

Measure latency, IOPS, I/O size, queue depth and throughput, then match the volume and instance EBS limits. The instance can bottleneck several volumes even when each volume is provisioned generously. Filesystem, initialization, cache and application behavior also matter.

| Type | Current published ceiling, subject to conditions | Typical consideration |
|---|---|---|
| gp3 | Regional:80,000IOPS /2,000MiB/s; Outposts lower | Baseline3,000IOPS /125MiB/s, independent paid performance settings |
| io1 |64,000IOPS /1,000MiB/s | Provisioned IOPS with instance/size limits |
| io2 Block Express |256,000IOPS /4,000MiB/s | Supported Nitro/size/IOPS and workload requirements |
| st1 |500MiB/s | Throughput-oriented HDD, sequential/burst behavior |
| sc1 |250MiB/s | Infrequent sequential HDD access |

The previous16,000IOPS/1,000MiB/s gp3 settings remain valid examples; they are not universal current maxima. gp2 size affects baseline/burst performance, while gp3 performance can be provisioned separately subject to its ratios. No volume type is automatically optimal for all databases, logs or web servers. RAID0 is a separate tradeoff, discussed below, not a default CSI optimization.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

</details>

### 3. What is the main architectural benefit of FSx for Lustre?

- A. Guaranteed lowest cost
- B. No driver or network prerequisites
- C. A parallel filesystem for suitable workloads
- D. A guarantee that every PVC reaches1,000GB/s

<details>
<summary>Show Answer</summary>

**Answer: C**

FSx for Lustre provides a managed parallel filesystem for supported HPC, ML, analytics and media workloads. Choose deployment type, client/kernel, capacity, provisioned throughput and network together. Marketing aggregate maxima are not the performance of an arbitrary small PVC.

SCRATCH_1/SCRATCH_2 target reproducible temporary data; SCRATCH_2 does not gain persistent-server replication simply by using a PV. PERSISTENT_1/PERSISTENT_2 have different supported storage and throughput choices. For example, PERSISTENT_2 SSD offers125/250/500/1000MB/s/TiB; do not apply a generic200MB/s/TiB or1,000GB/s statement to every filesystem. Those previous aggregate claims were not measurements verified by this review.

Prepare the managed add-on or an owned compatible driver as in the chapter. The example below preserves the supported `s3ImportPath` parameter; imports/exports need compatible deployment, permissions and repository policies/tasks. CSI creation alone is not automatic bidirectional S3 synchronization:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-import-demo
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: NONE
  s3ImportPath: s3://replace-with-owned-data-bucket/training/
```

PVC requests determine dynamic filesystem capacity; there is no generic StorageClass storageCapacity field. Compression and striping must be measured against data and concurrency. Higher parallelism, more stripes or LZ4 do not always improve performance. Use the managed EKS add-on catalog to select compatibility; “no native EKS integration” is not an accurate reason to reject FSx.

</details>

### 4. Which Mountpoint CSI provisioning model is correct?

- A. A dynamic s3-sc creates a bucket
- B. Static PV/PVC binding to an existing bucket
- C. A PVC capacity field sets the S3 quota
- D. A filesystem PVC automatically creates an EFS filesystem

<details>
<summary>Show Answer</summary>

**Answer: B**

Use `s3.csi.aws.com`, an existing bucket, empty storageClassName on both objects, explicit claimRef/volumeName and a unique volumeHandle. Put CLI options in PV mountOptions. Kubernetes capacity metadata is not an S3 capacity limit.

</details>

### 5. With authenticationSource: pod, which identity is used?

- A. Always the controller IAM role
- B. A static key embedded in the PV
- C. The application ServiceAccount’s supported Pod Identity or IRSA
- D. The PVC creator’s workstation credentials

<details>
<summary>Show Answer</summary>

**Answer: C**

CSI2.8 supports pod-level Pod Identity and IRSA; driver credentials are ignored for that volume. The role, association/trust, agent where needed and bucket/KMS permissions must exist. A ServiceAccount annotation alone is not an IAM role.

</details>

### 6. Where does CSI v2 place its configured emptyDir cache?

- A. The Mountpoint Pod
- B. Any app Pod emptyDir with the same path
- C. Inside the S3 bucket by definition
- D. Automatically on a GPU instance’s NVMe

<details>
<summary>Show Answer</summary>

**Answer: A**

Use cache volumeAttributes such as `cache: emptyDir` and `cacheEmptyDirSizeLimit`. Memory means tmpfs RAM. Mountpoint metadata TTL is seconds, standalone max-cache-size is MiB, and read/write part sizes are bytes. Version-specific flags must match the embedded Mountpoint binary.

</details>

### 7. Why might a cached mount not immediately show an external S3 change?

- A. S3 always has eventual list consistency
- B. Configured cache TTL can retain old/negative entries
- C. All S3 writes require a CSI restart
- D. The PV capacity is too small

<details>
<summary>Show Answer</summary>

**Answer: B**

S3 has strong read/list consistency. Optional Mountpoint caching changes what the client observes until TTL expires. Do not mistake cache behavior for the S3 consistency model. Use immutable dataset prefixes or appropriate cache settings when reproducibility matters.

</details>

### 8. Which set of conditions fits native EBS PVC cloning?

- A. Any namespace and any AZ
- B. The source class is always inherited
- C. The clone is application-consistent without coordination
- D. Supported driver, same namespace/source AZ, compatible mode and adequate target size

<details>
<summary>Show Answer</summary>

**Answer: D**

EBS CSI1.66 uses the real native volume-copy path. Ordinary PVC dataSource requires the same namespace; EBS copies remain in the source AZ. Set the class explicitly and request at least the source size. Availability precedes completed background initialization; quiesce applications for the required consistency.

</details>

### 9. Which example matches EBS CSI1.66 dynamic Multi-Attach?

- A. gp3 + RWO + multiAttachEnabled:true
- B. io2 + RWOP + independent ext4 writers
- C. io2 + RWX + raw Block with coordinated application I/O
- D. Any EBS type spanning several AZs

<details>
<summary>Show Answer</summary>

**Answer: C**

The driver maps io2 multiwriter block capability to Multi-Attach; there is no generic SC multiAttachEnabled switch. Eligible Nitro instances must be in the volume AZ. A shared device does not provide write coordination or fencing automatically. io2 supports size/IOPS modification under service/driver conditions, unlike a blanket no-resize claim.

</details>

### 10. What happens to a CSI snapshot when its owning Velero backup expires?

- A. Velero can set content deletionPolicy to Delete and delete it even if the class was Retain
- B. Retain always preserves it forever
- C. Only the PVC is deleted
- D. The snapshot becomes a portable S3 object automatically

<details>
<summary>Show Answer</summary>

**Answer: A**

Velero1.18 owns its CSI snapshot lifecycle. Configure backup TTL deliberately and use a separate retention/archive process when required. Its integrated CSI support still needs EnableCSI; backup metadata, native CSI snapshots and copied volume data are different things.

</details>

## Short Answer Questions

### 11. What does RAID0 provide, and what must an EKS design account for?

<details>
<summary>Show Answer</summary>

**Answer: Striping, with no redundancy**

RAID0 distributes blocks across volumes and aggregates usable capacity. One member failure can make the whole array unusable; it is not a backup or HA solution. Two equal volumes can theoretically supply roughly twice one volume’s performance only if the application, filesystem, CPU and instance EBS limits allow it. This is a theoretical bound, not a measured2× result.

A filesystem-mode PVC mounted at `/volume1` is a directory, not a raw disk for mdadm. A real block design needs `volumeMode: Block`, `volumeDevices`, exact volume identity, an authorized storage component, and an explicit empty-device initialization versus existing-array assembly procedure. Never format on every application restart. Plan same-node/AZ attachment, rescheduling, permissions, growth and consistent multi-volume backup/restore.

The previous privileged Pod’s unconditional mdadm/mkfs sequence is therefore unsuitable as a copy/paste recipe. The old2–4-volume and4/64/128KiB stripe examples are tuning candidates without verified measurements, not universal optima. Compare a suitable single gp3/io2 volume, reproducible instance-store scratch data or FSx before accepting this extra complexity.

</details>

### 12. What do EFS rsize and wsize control?

<details>
<summary>Show Answer</summary>

**Answer: Maximum NFS read/write RPC payload sizes**

They are not TCP socket-buffer sizes. AWS recommends1,048,576bytes (1MiB) for both, with `hard,timeo=600,retrans=2,noresvport` through the supported NFS/EFS mount path. timeo is in tenths of a second, so600 means60seconds. On a hard mount, retrans=2 does not mean abandoning the operation after two attempts. Do not prescribe smaller values for random I/O or packet loss without workload evidence. Configure options on the StorageClass/PV, not Pod volumes; EFS does not support nconnect.

Reuse the chapter’s owned EFS filesystem and access-point setup:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-tuned
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
- rsize=1048576
- wsize=1048576
- hard
- timeo=600
- retrans=2
- noresvport
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

If conducting an authorized write test, use a verified disposable directory and a unique file, not a predictable `/efs/testfile` that could overwrite data. The GNU dd example below writes64MiB and cleans up only its own file/directory. Its read may hit client cache, so these timings alone do not establish cold EFS throughput:

```bash
set -euo pipefail
: "${EFS_TEST_DIR:?Set an approved disposable directory on the verified EFS mount}"
test -d "$EFS_TEST_DIR" && test -w "$EFS_TEST_DIR"
EFS_TEST_PATH=$(mktemp -d "$EFS_TEST_DIR/efs-test.XXXXXX")
cleanup() { rm -f -- "$EFS_TEST_PATH/payload"; rmdir -- "$EFS_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$EFS_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$EFS_TEST_PATH/payload" of=/dev/null bs=1M
```

No EFS performance test was run in this review. Correlate client/application latency and concurrency with EFS TotalIOBytes, DataReadIOBytes, DataWriteIOBytes and MetadataIOBytes using the appropriate CloudWatch statistics/periods. A byte counter is not a throughput rate until divided by its measurement interval.

</details>

### 13. How do EBS availability SLA and durability design differ?

<details>
<summary>Show Answer</summary>

**Answer: They describe different properties and conditions**

The EBS SLA is an availability/service-credit agreement, not a universal99.999% data-durability SLA. Its Region-level commitment uses a99.99% threshold for qualifying concurrent deployments across multiple AZs; the single-volume commitment uses99.9%. Read the agreement’s definitions, exclusions and credit conditions rather than treating either number as an unconditional guarantee.

| Published design characteristic | Volume types |
|---|---|
|99.8–99.9% durability;0.1–0.2% AFR | gp3/gp2/io1 and HDD types |
|99.999% durability;0.001% AFR | io2 Block Express |

There is no separate io2 “five-nines availability SLA” in this agreement. AFR/design durability is not the probability that a particular application loses all its data; corruption, deletion, backups and recovery architecture matter. EBS replication is within one AZ, not automatic cross-AZ database replication.

Use application-consistent backups where required, retain independent recovery points, test restores and monitor volume/application health. To recover from AZ failure, restore accessible snapshots into a permitted AZ; to recover deleted records, use a suitable recovery point or database PITR mechanism. A block snapshot alone does not offer every arbitrary recovery timestamp.

Cross-Region snapshot copying is a separate operation with source/destination/KMS permissions and completion checks. The following is an illustrative creation command, not an executed recovery test. Confirm source ownership and allowed destination first, record the returned SnapshotId and wait/check that copy before relying on it:

```bash
set -euo pipefail
: "${SOURCE_REGION:?Set the source snapshot Region}"
: "${DESTINATION_REGION:?Set the recovery Region}"
: "${SOURCE_SNAPSHOT_ID:?Select an owned completed snapshot}"
: "${DESTINATION_KMS_KEY_ARN:?Set a usable customer managed key in the recovery Region}"
STATE=$(aws ec2 describe-snapshots --region "$SOURCE_REGION" \
  --snapshot-ids "$SOURCE_SNAPSHOT_ID" --query 'Snapshots[0].State' --output text)
test "$STATE" = completed || { echo "Snapshot is not completed"; exit 1; }
aws ec2 copy-snapshot --region "$DESTINATION_REGION" --source-region "$SOURCE_REGION" \
  --source-snapshot-id "$SOURCE_SNAPSHOT_ID" --encrypted --kms-key-id "$DESTINATION_KMS_KEY_ARN" \
  --description "Reviewed storage recovery copy" --output json
```

An AWS CLI image does not implicitly contain kubectl or grant Kubernetes/IAM permissions. Use a supported backup owner such as Velero, Data Lifecycle Manager or AWS Backup with appropriate scope, not an unconfigured CronJob. Compare each storage service’s actual storage class/deployment SLA and durability design separately; a universal cross-service percentage table is misleading.

</details>

## Hands-on Questions

### 14. Design a database storage and recovery workflow with explicit limits.

<details>
<summary>Show Answer</summary>

**Answer: A reviewed blueprint, not an automatic recovery guarantee**

Design for a PostgreSQL workload with high I/O demand, scheduled backups, verified recovery and controlled expansion. The following is a **training blueprint**, not a tested production deployment. Reuse a dedicated `database` namespace, prepared Secret `postgres-secret/password`, compatible EBS/snapshot drivers and an owned Velero installation. Do not apply it over existing resources without their owner.

#### Storage and database

The original25,000IOPS allocation is retained as an illustrative io2 setting; sufficiency requires measurement and instance limits. Encryption uses the configured/default EBS key. If selecting a customer managed key, prepare the real ARN/key policy/driver grants instead of a fake kmsKeyId.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '25000'
```



```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  clusterIP: None
  selector:
    app: postgres
  ports:
  - name: postgres
    port: 5432
    targetPort: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: postgres
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: postgres
        image: postgres:14.24
        env:
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        - name: POSTGRES_PASSWORD_FILE
          value: /run/postgres-secret/password
        ports:
        - name: postgres
          containerPort: 5432
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          periodSeconds: 5
        resources:
          requests:
            cpu: '2'
            memory: 4Gi
          limits:
            cpu: '4'
            memory: 8Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        - name: socket
          mountPath: /var/run/postgresql
        - name: tmp
          mountPath: /tmp
        - name: password
          mountPath: /run/postgres-secret
          readOnly: true
      volumes:
      - name: socket
        emptyDir: {}
      - name: tmp
        emptyDir: {}
      - name: password
        secret:
          secretName: postgres-secret
          defaultMode: 288
          items:
          - key: password
            path: password
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        app: postgres
        storage-review: database-demo
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: postgres-io2
      resources:
        requests:
          storage: 100Gi
```

This uses the verified PostgreSQL14.24 image contract from Part1: UID/GID999, a mounted password file, writable socket/tmp volumes and a PGDATA subdirectory. Major14 reaches end of support on November12,2026; this preserved teaching version is not a default for a new production deployment. Choose and test an appropriate supported major and a migration plan. One StatefulSet replica is not HA; pg_isready is a connection readiness check, not a data-integrity or recovery test.

#### Backup and retention

Use the chapter’s snapshot-controller prerequisites and `ebs-snapshot-class`. For a manual recovery point, quiesce the database or use a supported database backup protocol before creation. The real StatefulSet claim is **data-postgres-0**:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-review-snapshot
  namespace: database
  labels:
    storage-review: database-demo
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: data-postgres-0
```

Wait for readyToUse and inspect restoreSize/content/driver before treating it as recoverable. Snapshot encryption follows the source/key configuration; unsupported encrypted/tagSpecification keys in VolumeSnapshotClass do not configure it. The current driver supports specific snapshot tag parameters, which must be checked against that driver’s release rather than copied from volume-class parameters.

The following emits a daily Velero schedule with a30-day TTL. Apply through the backup owner after checking the CSI class selection and database consistency hooks/protocol. Velero TTL may delete its CSI snapshots even with an original Retain class. Alert on failed/missing backups and regularly test restores; a schedule alone does not prove recoverability:

```bash
velero schedule create database-daily --schedule="0 1 * * *" \
  --include-namespaces=database --ttl=720h0m0s -o yaml > database-backup-schedule-review.yaml
```

#### Bounded expansion planning

Do not blindly grow by50% every six hours from stale metrics. The review-only planner below requires a Bound claim, matching expandable class, no pending resize, fresh metrics identifying the same PVC UID and valid filesystem byte counts. It supports common decimal/binary Kubernetes quantities and rejects unsupported input. At80% usage it proposes at least1.5× requested capacity, with an illustrative500Gi cap and UID/resourceVersion/current-size preconditions. It does not patch Kubernetes.

Capture fresh `pvc.json` and `storageclass.json` from the exact objects. `trusted-metrics.json` must contain namespace, pvcName, pvcUID, observedAt (timezone-aware), usedBytes and capacityBytes from the actual mounted filesystem. A caller-supplied UID does not by itself prove metric provenance. Validate collector/mount mapping, quota, cost and driver constraints before any operator/controller applies a reviewed patch.

```python
"""Generate a review-only plan from captured PVC, StorageClass and trusted metrics."""
import datetime,decimal,json,math,re,sys
D=decimal.Decimal
def quantity(s):
    match=re.fullmatch(r'([+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))([EPTGMK]i|[EPTGMk]|m|[eE][+-]?[0-9]+)?',s)
    if not match:raise ValueError('Unsupported/nonpositive quantity: '+s)
    value,suffix=D(match[1]),match[2] or ''
    if suffix.endswith('i'):value*=D(1024)**('KMGTPE'.index(suffix[0])+1)
    elif suffix in ['k','M','G','T','P','E']:value*=D(1000)**('kMGTPE'.index(suffix)+1)
    elif suffix=='m':value/=1000
    elif suffix:value*=D(10)**int(suffix[1:])
    if value<=0:raise ValueError('Capacity must be positive')
    return value
def plan(pvc,sc,metrics,now):
    meta,spec,status=pvc['metadata'],pvc['spec'],pvc['status']
    if (meta['namespace'],meta['name'])!=('database','data-postgres-0'):
        raise ValueError('Unexpected PVC')
    if status.get('phase')!='Bound' or not spec.get('volumeName'):
        raise ValueError('PVC is not Bound')
    if sc['metadata']['name']!=spec['storageClassName'] or sc.get('allowVolumeExpansion') is not True:
        raise ValueError('StorageClass mismatch or expansion disabled')
    if any(c.get('status')=='True' and c.get('type') in ['Resizing','FileSystemResizePending'] for c in status.get('conditions',[])):
        raise ValueError('Resize is pending')
    if status.get('allocatedResourceStatuses',{}).get('storage'):
        raise ValueError('Storage allocation is pending')
    requested=quantity(spec['resources']['requests']['storage'])
    if requested!=quantity(status['capacity']['storage']):
        raise ValueError('Request and capacity differ; inspect before another resize')
    if (metrics['namespace'],metrics['pvcName'],metrics['pvcUID'])!=(meta['namespace'],meta['name'],meta['uid']):
        raise ValueError('Metrics identify a different PVC')
    seen=datetime.datetime.fromisoformat(metrics['observedAt'].replace('Z','+00:00'))
    if seen.tzinfo is None or not 0<=(now-seen).total_seconds()<=300:
        raise ValueError('Metrics are stale or future-dated')
    used,capacity=D(str(metrics['usedBytes'])),D(str(metrics['capacityBytes']))
    if not used.is_finite() or not capacity.is_finite() or not 0<=used<=capacity<=requested or capacity<=0:
        raise ValueError('Invalid filesystem metrics')
    if used/capacity<D('0.8'):return {'reviewOnly':True,'action':'none','reason':'Below 80%'}
    target=math.ceil(max(requested*D('1.5'),used/D('0.7'))/D(1024**3))
    if target>500:return {'reviewOnly':True,'action':'manual-review','reason':'Illustrative 500Gi cap exceeded'}
    return {'reviewOnly':True,'action':'propose-resize','target':str(target)+'Gi','patch':[
      {'op':'test','path':'/metadata/uid','value':meta['uid']},
      {'op':'test','path':'/metadata/resourceVersion','value':meta['resourceVersion']},
      {'op':'test','path':'/spec/resources/requests/storage','value':spec['resources']['requests']['storage']},
      {'op':'replace','path':'/spec/resources/requests/storage','value':str(target)+'Gi'}]}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: resize-plan.py pvc.json storageclass.json trusted-metrics.json')
    inputs=[]
    for name in sys.argv[1:]:
        with open(name) as f:inputs.append(json.load(f))
    print(json.dumps(plan(*inputs,datetime.datetime.now(datetime.timezone.utc)),indent=2))
```

If the resource changes, regenerate the plan; do not remove failed preconditions or log success after a failed patch. After an approved expansion, inspect PVC conditions and actual filesystem capacity. Keep the StatefulSet template’s future-claim sizing aligned through a supported ownership procedure; do not edit PV capacity to fake completion.

#### Recovery candidate

Never make a retrying Job scale down and delete the live claim as its first restore step. Use a separate candidate sized at least restoreSize; the100Gi example assumes this recovery point is no larger. If the original claim was expanded, adjust the candidate accordingly:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-restore-candidate
  namespace: database
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: postgres-io2
  resources:
    requests:
      storage: 100Gi
  dataSource:
    name: postgres-review-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

Schedule an isolated compatible PostgreSQL consumer with the required credentials/version, wait for binding/recovery and verify application queries/data before a controlled cutover. Keep the original data and a reversal plan. Setting a new POSTGRES_PASSWORD variable does not reset credentials in an existing restored database.

#### Monitoring

PostgreSQL5432 speaks the database protocol, not Prometheus HTTP. Prepare a reviewed postgres-exporter workload labelled `app: postgres-exporter`, with a named `metrics` port9187 and appropriately scoped database credentials. This Service and ServiceMonitor select that exporter; they do not install it. Ensure Prometheus selects this ServiceMonitor/namespace and that NetworkPolicy/TLS/auth settings match the deployment:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    monitoring: postgres-exporter
spec:
  selector:
    app: postgres-exporter
  ports:
  - name: metrics
    port: 9187
    targetPort: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-exporter
  namespace: database
spec:
  selector:
    matchLabels:
      monitoring: postgres-exporter
  namespaceSelector:
    matchNames:
    - database
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

Alert on backup freshness/failure, filesystem headroom, PVC resize errors and measured I/O latency/queue limits. This blueprint needs workload-specific HA, restore, credential rotation and load testing before any production-readiness claim.

</details>

### 15. How would you investigate a slow new clone and an old view of an S3 dataset?

<details>
<summary>Show Answer</summary>

**Answer: Separate initialization, caching and application consistency**

For the EBS clone, verify the actual driver version, source AZ/size, copy state, initialization progress and provisioned/instance performance. A newly available native copy may still initialize in the background. Do not zero-write it, treat it as an empty volume, or assume snapshot-only initialization accelerators apply.

For Mountpoint, inspect the installed CSI/binary version, PV options, pod identity, bucket/prefix and cache TTL, including negative entries. S3 strong consistency does not bypass a configured client cache. Verify whether the application operation is supported for that bucket type; append/rename assumptions differ for general purpose and directory buckets.

Use the chapter’s isolated clone marker and a versioned S3 dataset to test hypotheses. Preserve historical benchmark values as unverified context; record new measurements with their actual environment if tests are later authorized. Neither a read test nor a snapshot creation proves database application consistency.

</details>

## References

- [Chapter and source-aligned examples](../../eks/04-eks-storage-part2.md)
- [StatefulSet PVC retention](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [EBS volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- [EBS SLA](https://aws.amazon.com/ebs/sla/)
- [EBS native copy](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
- [EFS mount settings](https://docs.aws.amazon.com/efs/latest/ug/mounting-fs-nfs-mount-settings.html)
- [Mountpoint CSI configuration](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
- [Velero CSI lifecycle](https://velero.io/docs/v1.18/csi/)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [PostgreSQL version policy](https://www.postgresql.org/support/versioning/)
