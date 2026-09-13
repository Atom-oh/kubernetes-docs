# EKS Storage Quiz - Part 1

> **Last Updated**: September 11, 2026

These answers use the ownership and prerequisites in [the storage chapter](../../eks/04-eks-storage-part1.md). Examples use conventional Linux EC2 storage unless stated otherwise; Auto Mode, Fargate and Hybrid support differ. Local schema/mock checks are not proof of AWS volume attachment, data recovery or production performance.

### 1. Which driver manages conventional EBS volumes with provisioner ebs.csi.aws.com?

- A. Amazon EFS CSI Driver
- B. Amazon EBS CSI Driver
- C. FSx for Lustre CSI Driver
- D. Mountpoint for Amazon S3 CSI Driver

<details>
<summary>Show Answer</summary>

**Answer: B. Amazon EBS CSI Driver**

The driver is available as an EKS add-on; availability does not mean it is installed automatically on every cluster. EKS Auto Mode has its own built-in `ebs.csi.eks.amazonaws.com` path. Check the selected compute, add-on owner, Kubernetes/driver compatibility and real installation state.

Prepare the controller Pod Identity or IRSA trust and reviewed `AmazonEBSCSIDriverPolicyV2`/scoped permissions, including customer KMS-key permissions where needed. A copied historical policy is not a substitute for the current driver policy and trust relationship. Use the source chapter’s guarded catalog/install workflow; do not use the literal AWS API add-on version `latest` or overwrite another owner’s installation.

This class enables encrypted gp3, scheduler-aware provisioning, expansion and deliberate retention:
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
Snapshots additionally need snapshot CRDs/controller and a matching VolumeSnapshotClass. The driver supports several EBS volume types, each with size/performance restrictions. Ordinary EBS volumes remain in one AZ; Fargate Pods cannot mount them, although a separately designed EBS controller can run on Fargate. EBS is not compatible with Hybrid Nodes.

EFS and FSx have their own supported drivers. The earlier claim that no official S3 CSI driver exists was false: Mountpoint CSI exposes existing S3 buckets with limited POSIX semantics, while S3 Files uses EFS CSI 3.0+ for a separate shared-filesystem interface.

</details>

### 2. Which managed NFS service fits shared files across Linux nodes without a Lustre client?

- A. Ordinary gp3 filesystem
- B. Amazon EFS
- C. S3 object GET/PUT API
- D. FSx for Lustre

<details>
<summary>Show Answer</summary>

**Answer: B. Amazon EFS**

EFS provides shared NFS access and supports RWX. Multiple Pods alone would not uniquely select EFS: RWO allows several Pods on one node and FSx for Lustre also supports sharing. Choose from actual protocol, consistency, latency, throughput, durability and cost requirements.

Use a supported EFS CSI installation with the required controller IAM role and an existing encrypted filesystem. Prepare mount targets in the actual client AZs, at most one subnet per AZ, and SG/DNS/NFS paths. The source chapter’s setup captures IDs and checks AZ/VPC ownership. Reusing a creation token with different encryption settings does not encrypt an existing filesystem in place.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```
The 5 Gi claim is binding metadata, not a directory quota. Access points enforce a POSIX identity and root directory, while IAM/filesystem policies and network controls determine permitted access. Dynamic AP provisioning is not the Fargate path; use its supported static integration. TLS/client mount authorization is separate from controller provisioning permissions.

EFS Regional and One Zone have different failure properties. Published durability/design targets and service-level commitments are not measured uptime guarantees for this application. Automatic storage growth does not remove throughput/IOPS, quota, backup and cost planning. AWS recommends General Purpose performance mode; Max I/O has higher operation latency. Select Elastic, Provisioned or Bursting deliberately rather than assuming a universal default.

For static application settings, ConfigMaps/Secrets may fit better than shared storage. Shared mutable files require application locking/consistency. S3 APIs, Mountpoint and S3 Files are distinct interfaces; do not dismiss all S3 file access. FSx for Lustre is an alternative parallel filesystem, not inherently unsuitable merely because its setup differs.

</details>

### 3. Which statement correctly describes ordinary EBS filesystem constraints?

- A. The same volume attaches in any AZ
- B. Fargate Pods mount any EBS volume
- C. One AZ; RWO can serve multiple same-node Pods
- D. RWO guarantees exactly one Pod

<details>
<summary>Show Answer</summary>

**Answer: C. The volume stays in one AZ; RWO can be shared by Pods on the same node.**

RWO means read/write by one node, not one Pod. A replacement Pod can use the same PVC on another suitable node in that AZ after safe detach/attach. It cannot attach the same volume across AZs. A snapshot restore creates a different volume in the target AZ; it is not an in-place move or continuous replication.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```
Use `WaitForFirstConsumer` so scheduling constraints inform initial volume placement. A bound PVC remains constrained by its PV topology; changing a node selector cannot relocate its data. Per-replica StatefulSet PVCs give separate volumes, not database replication. Multi-AZ availability needs an application/data-replication or recovery design.

EBS CSI 1.66.0 also supports an io2 raw-block Multi-Attach path with RWX and compatible infrastructure/application coordination. This does not make an ordinary gp3/ext4 volume a shared multi-node filesystem. Fargate Pods still cannot mount EBS. Use a suitable shared filesystem when that is the requirement.

</details>

### 4. Must every dynamically provisioned EBS claim use only ReadWriteOnce?

<details>
<summary>Show Answer</summary>

**Answer: No. RWO is the ordinary example; RWOP and specialized raw-block modes have different requirements.**

RWOP supplies the one-Pod constraint that RWO does not. It is stable since Kubernetes 1.29 and requires a compatible CSI sidecar stack. CSI access-mode translation can map RWOP to SINGLE_NODE_WRITER for drivers without the newer single-node capability; reading that driver constant alone is not proof that RWOP is unsupported. This is an **alternative claim** for a one-Pod workload:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-exclusive
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOncePod
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```
| Mode | Meaning |
|---|---|
| RWO | One read/write node; several Pods on that node may share it |
| RWOP | One Pod cluster-wide with compatible CSI/Kubernetes support |
| RWX | Multi-node writing only when the backend/driver and application support it |
| ROX | Multi-node reader capability; not universally supported by every CSI driver |

Access-mode matching does not replace filesystem/IAM permissions or an explicit read-only mount. Separate volumes restored from a snapshot are independent copies; they are not one shared ROX volume. Do not mount ordinary ext4/XFS independently on multiple writers as a substitute for a clustered storage design.

</details>

### 5. What happens when an EBS-backed Pod is replaced on another node?

<details>
<summary>Show Answer</summary>

**Answer: The retained volume can be safely detached/attached in the same AZ; recovery time and application consistency must be verified.**

Kubernetes creates a replacement Pod; it does not move the original Pod object. For a single-attach volume, the old writer must be stopped/fenced and the volume safely detached before attachment to the new node. The volume persists according to its lifecycle, but abrupt failure can lose unflushed writes or require filesystem/database recovery. Do not claim that every write is guaranteed to survive.

The original “10–30 seconds” reattachment time has no verified measurement source here. It is preserved as an **unverified historical estimate**, not an AWS SLA or recovery guarantee. Node-failure detection, fencing, controller reconciliation, volume operations and application startup can take longer.

PDBs constrain applicable voluntary evictions, not node/AZ failure. Set them from real replicas/quorum; a single database replica does not become highly available with a PDB. Readiness should verify application readiness, not only a persistent `/data/ready` marker; liveness restarts a container and does not gate Service traffic. StatefulSet ordering and topology spread do not replicate one EBS volume across AZs. Per-AZ PDB ideas also require actual matching Pod labels; node zone labels are not automatically copied onto Pods.

Use graceful shutdown where possible, diagnose VolumeAttachment/Pod events and actual node state, and follow documented recovery procedures. Force-detach or deleting attachment metadata without fencing is not a general latency optimization. Test restored application data and recovery objectives with an independent backup.

</details>

### 6. Which resource requests an EBS snapshot, and what makes the backup usable?

<details>
<summary>Show Answer</summary>

**Answer: `VolumeSnapshot`**

Prepare compatible snapshot CRDs/controller and the EBS snapshotter, with a class whose driver matches the actual provisioner. Preserve add-on ownership rather than applying floating master manifests. Snapshot consistency may require database-aware backup/quiescing; a ready block snapshot alone does not prove application recovery.
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-retain
driver: ebs.csi.aws.com
deletionPolicy: Retain
```

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-snapshot
  namespace: storage-demo
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: ebs-claim
```

```bash
set -euo pipefail
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  volumesnapshot/ebs-snapshot --timeout=300s
kubectl -n storage-demo get volumesnapshot ebs-snapshot -o yaml
```
Restore into a new claim in the same namespace with capacity at least `status.restoreSize`; use a consumer for WaitForFirstConsumer binding and verify the data. This manifest restores the **fixed-name ebs-snapshot above**; change the name if restoring another snapshot.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-restored
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 20Gi
  dataSource:
    name: ebs-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```
For repeated creation, this command is an **alternative** that creates a unique snapshot and waits for readiness. Record the resulting name. Scheduling it needs a deliberately scoped ServiceAccount/RBAC, pinned tooling, UTC/time-zone choice, non-overlapping runs and error/retention handling; the old unspecified service accounts were not an installed backup system.
```bash
set -euo pipefail
SNAPSHOT_NAME="ebs-snapshot-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
kubectl -n storage-demo create -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: $SNAPSHOT_NAME
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: ebs-claim
EOF
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  "volumesnapshot/$SNAPSHOT_NAME" --timeout=300s
```
For retention, parse absolute timestamps and scope by namespace, backup label and source PVC. The following produces a **review-only candidate list**; it deletes nothing. Check each bound VolumeSnapshotContent’s deletionPolicy, ownership, dependencies and a verified recovery point before automated removal. Delete policy can remove the AWS snapshot; Retain preserves it and can leave storage charges. A production backup controller needs UID/precondition handling and recovery tests, not an unscoped xargs delete pipeline.
```bash
set -euo pipefail
kubectl -n storage-demo get volumesnapshots -l storage-demo=ebs \
  -o json > storage-demo-snapshots.json
python3 - storage-demo-snapshots.json <<'PY'
import datetime, json, sys
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(days=30)
with open(sys.argv[1]) as stream:
    snapshots = json.load(stream)["items"]
candidates = []
for snapshot in snapshots:
    meta, spec, status = snapshot["metadata"], snapshot["spec"], snapshot.get("status", {})
    if meta.get("namespace") != "storage-demo" or meta.get("labels", {}).get("storage-demo") != "ebs":
        continue
    if spec.get("source", {}).get("persistentVolumeClaimName") != "ebs-claim":
        continue
    if status.get("readyToUse") is not True or meta.get("deletionTimestamp"):
        continue
    created = datetime.datetime.fromisoformat(meta["creationTimestamp"].replace("Z", "+00:00"))
    if created.tzinfo is None:
        raise SystemExit("Snapshot timestamp must include a timezone")
    if created < cutoff:
        candidates.append({"name": meta["name"], "uid": meta["uid"],
                           "content": status.get("boundVolumeSnapshotContentName"),
                           "createdAt": meta["creationTimestamp"]})
print(json.dumps({"reviewOnly": True, "candidates": candidates}, indent=2))
PY
```
Snapshot transfer between clusters/accounts/Regions needs explicit snapshot import/copy, KMS access and restore configuration. Treat production data copied into test environments with the same access/retention care. Verify actual data, not only the existence of VolumeSnapshot objects.

</details>

### 7. Design storage for a database, shared files and parallel ML data.

<details>
<summary>Show Answer</summary>

**Answer: Select the backend and lifecycle for each requirement, with explicit prerequisites.**

This is a reviewed configuration blueprint, **not a deployed production system**. First create/review the `database`, `application` and `ml-workloads` namespaces, compatible CSI drivers and IAM roles, KMS/network permissions, actual EFS/FSx/S3 resources, and image/compute compatibility. StorageClasses are cluster-scoped; the examples are alternatives managed by one owner. Capacity, application recovery and performance must be tested in the target environment.

**1. Database block storage.** Keep the original illustrative 16,000 IOPS/1,000 MiB/s settings, but do not call them the universal gp3 maxima. Current Regional gp3 supports up to 80,000 IOPS and 2,000 MiB/s subject to volume-size/IOPS ratios and instance limits; Outposts has different limits. The sample is a configuration choice, not a benchmark or proof that the database needs this spend.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-db
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '16000'
  throughput: '1000'
```
The StatefulSet creates **data-postgres-0** from its `data` claim template. Do not also create the original unused `database-data` PVC or snapshot that unused claim. Prepare `postgres-secret` with a securely managed `password` key; no password value is supplied here. The image reads it from a mounted file, and PGDATA uses a subdirectory so the volume root’s filesystem metadata does not interfere with initialization.
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
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: ebs-gp3-db
      resources:
        requests:
          storage: 100Gi
```
This example uses PostgreSQL 14.24, the verified current minor release of major 14. Major14 support ends November 12, 2026. Plan a tested supported-version migration and pin an approved image digest for production. This single replica is not a replicated/HA database; replica scaling without a database replication design is not a solution. The explicit PVC retention policy preserves claims when the StatefulSet is deleted/scaled, leaving data and possible storage charges.

After an application-consistent backup/quiesce step, snapshot the claim the database actually uses. The class is the retained EBS snapshot class defined earlier:
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: database-snapshot
  namespace: database
  labels:
    backup-set: postgres-demo
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: data-postgres-0
```
**2. Shared files.** Static configuration often belongs in ConfigMaps/Secrets. If mutable shared files are required, the EFS class from the source chapter provides separate AP directories and UID/GID1000. Replace the filesystem ID and validate client paths/permissions; this claim does not impose a 5 Gi quota.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage
  namespace: application
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```
This seed Job writes only a nonsensitive demonstration setting and preserves an existing file. The three reader Pods mount it read-only and check readability. This demonstrates file delivery; a real application must parse/reload its configuration. Mounting `/etc/config` into an otherwise unconfigured nginx would not make nginx use those files.
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: config-seed
  namespace: application
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: seed
        image: busybox:1.37.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          if test -e /config/settings.txt; then
            echo "Existing settings preserved"
          else
            (set -C; printf 'MODE=demo\n' > /config/settings.txt)
          fi
          sync
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
        - name: config
          mountPath: /config
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: config-storage
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: config-reader
  namespace: application
spec:
  replicas: 3
  selector:
    matchLabels:
      app: config-reader
  template:
    metadata:
      labels:
        app: config-reader
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
      - name: reader
        image: busybox:1.37.0
        command:
        - sleep
        - '3600'
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        readinessProbe:
          exec:
            command:
            - test
            - -r
            - /etc/config/settings.txt
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 64Mi
        volumeMounts:
        - name: config
          mountPath: /etc/config
          readOnly: true
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: config-storage
```
**3. Parallel ML data.** Prepare the supported Lustre client/kernel, CSI/IAM and filesystem/S3 integration. This SCRATCH_2 example is for rebuildable data; it omits persistent-only per-unit throughput and automatic-backup settings. `s3ImportPath` is a valid FSx CSI 1.10.0 parameter—replace the bucket/prefix with an owned, accessible dataset and review supported integration/Region settings. LZ4 is a storage feature, not proof of a measured compression or throughput improvement.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: LZ4
  s3ImportPath: s3://example-training-data/dataset/
mountOptions:
- flock
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-training-data
  namespace: ml-workloads
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi
```
The1200 Gi claim is an example allocation; confirm the driver’s rounding and service capacity choices. The Job below is a **template**: replace the placeholder with a tested non-root GPU image that contains `/opt/training/train.py` and accepts the shown arguments, and populate the dataset before execution. Training code stays in the image rather than being hidden by the data mount. Four concurrent Pods requesting four GPUs each can require **16 GPUs**, plus the requested CPU/memory and applicable quotas. Indexed completions identify four tasks; they do not automatically implement distributed training/gradient synchronization.
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: ml-workloads
spec:
  parallelism: 4
  completions: 4
  completionMode: Indexed
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: training
        image: registry.example.com/team/trainer:reviewed
        command:
        - python
        - /opt/training/train.py
        args:
        - --data-dir
        - /training
        - --shard-index
        - $(JOB_COMPLETION_INDEX)
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
        resources:
          limits:
            nvidia.com/gpu: '4'
          requests:
            cpu: '8'
            memory: 32Gi
        volumeMounts:
        - name: data
          mountPath: /training
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: ml-training-data
```
The original aggregate-performance statements (“hundreds of GB/s” and “millions of IOPS”) were not measurements of this small SCRATCH_2 example. Do not size from them; verify the selected filesystem/client configuration with a representative workload. No training run was performed.

**Recovery, monitoring and cost:** select backend and filesystem/application metrics explicitly, monitor actual quota/throughput/latency/usage, and test restores with known data. A retained PV or snapshot is not a backup schedule. Deleting an unused-looking volume requires checking ownership, references and a verified recovery copy first. For security use Pod Security admission/securityContext, scoped IAM, TLS and filesystem permissions; removed PodSecurityPolicy is not an option. This blueprint establishes neither production readiness nor optimized cost/performance.

</details>

### 8. Does deleting a Pod always delete its volume data?

- A. Yes, every volume is deleted
- B. No, inspect its lifecycle
- C. Only if the Pod has two containers
- D. Never; all volumes are persistent

<details>
<summary>Show Answer</summary>

**Answer: B. No; lifetime depends on the volume type, PVC ownership and reclaim policy.**

emptyDir data is Pod-scoped, while a retained PVC-backed volume can outlive the Pod. Generic ephemeral PVCs can be owned by the Pod. Physical instance-store data remains tied to node/media lifetime even when a CSI driver presents it as a PV; the real May 2026 EC2 Instance Store CSI add-on does not turn it into durable replicated storage.

</details>

### 9. Does an EFS PVC requesting 5 Gi impose a 5 Gi directory quota?

- A. Yes, writes fail after5 Gi
- B. Yes, every access point gets a block device
- C. No, the request is binding metadata
- D. Only with directoryPerms700

<details>
<summary>Show Answer</summary>

**Answer: C. No; it is Kubernetes capacity/binding metadata.**

EFS grows with stored data and the claim does not preallocate or cap a directory at that size. Plan filesystem throughput, access points, client behavior, retention and costs separately. Use explicit application/account controls where quota enforcement is required.

</details>

### 10. Which field sets the initial reclaim policy in a StorageClass?

- A. `persistentVolumeReclaimPolicy`
- B. `reclaimPolicy`
- C. `deletionPolicy`
- D. `dataRetention`

<details>
<summary>Show Answer</summary>

**Answer: B. `reclaimPolicy`**

`persistentVolumeReclaimPolicy` belongs to `PersistentVolume.spec`. A StorageClass policy is copied to newly provisioned PVs; changing the class does not automatically modify every existing PV. Snapshot deletionPolicy is another independent lifecycle setting.

</details>

### 11. What does Delete normally remove for an EFS dynamically provisioned access point?

- A. Every filesystem in the VPC
- B. The entire EFS filesystem always
- C. The AP; optional root-directory cleanup
- D. No AWS resource can ever be deleted

<details>
<summary>Show Answer</summary>

**Answer: C. The access point; directory-data deletion depends on controller configuration.**

The EFS filesystem is not normally deleted by the access-point provisioner. The reviewed chart defaults deleteAccessPointRootDir to false; enabling it changes data-removal behavior. Inspect the actual controller values and shared/reused access-point ownership before deleting any claim.

</details>

### 12. Which statement about S3 access from EKS is correct?

- A. No official S3 CSI driver exists
- B. The interfaces and prerequisites differ
- C. Mountpoint automatically creates new buckets
- D. All S3 mounts support all POSIX operations

<details>
<summary>Show Answer</summary>

**Answer: B. S3 APIs, Mountpoint CSI and S3 Files provide different interfaces and requirements.**

Official Mountpoint CSI supports existing buckets through a file interface with limited POSIX semantics. S3 Files is a separate shared-filesystem service supported by EFS CSI 3.0+, with different controller/node permissions. Do not infer that every S3-backed path supports the same operations, compute modes or provisioning model.

</details>

### 13. What can keep a WaitForFirstConsumer PVC legitimately Pending?

- A. Every CSI driver is broken
- B. No suitable scheduled consumer yet
- C. Retain prohibits binding
- D. PVC must use an empty class

<details>
<summary>Show Answer</summary>

**Answer: B. A suitable consumer has not yet been scheduled.**

Delayed binding lets scheduler topology/resource constraints inform placement. It is not always a storage failure. Setting spec.nodeName bypasses the scheduler and can prevent this binding flow; use supported scheduling constraints. Check events before changing the storage class or provisioning volumes manually.

</details>

### 14. Which access mode supplies a one-Pod constraint with compatible CSI support?

- A. ReadWriteOnce
- B. ReadWriteMany
- C. ReadOnlyMany
- D. ReadWriteOncePod

<details>
<summary>Show Answer</summary>

**Answer: D. ReadWriteOncePod**

RWO limits read/write attachment to one node and can serve several Pods on that node. RWOP is the separate one-Pod mode; it still does not replace application consistency, backup or authorization design. Do not combine RWOP with other access modes on the same claim.

</details>

### 15. How should you expand the 10 Gi EBS example and verify recovery?

<details>
<summary>Show Answer</summary>

**Answer: Allow supported expansion, increase the PVC request, verify actual capacity and test a separate restore.**

Confirm StorageClass allowVolumeExpansion and driver/filesystem support, take a suitable application-consistent backup, then increase the claim through its owner. For this demo the target is 20 Gi. Do not shrink a volume or edit PV capacity to imitate resizing:
```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```
Check PVC conditions/status, the mounted filesystem and application I/O. Follow the documented remount/restart procedure if filesystem resizing remains pending. Restore a snapshot into a new claim, mount it with an appropriate consumer and verify known application data. A bigger PVC request or ready snapshot object alone is not a completed data-recovery test.

</details>

Official references: [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html), [Kubernetes PVs](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [gp3 specifications](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html), [PostgreSQL support](https://www.postgresql.org/support/versioning/), [S3 Files](https://docs.aws.amazon.com/eks/latest/userguide/s3files-csi.html).
