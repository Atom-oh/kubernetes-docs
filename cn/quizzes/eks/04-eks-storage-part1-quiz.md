# EKS 存储测验 - 第 1 部分

> **最后更新**：September 11, 2026

这些答案采用[存储章节](../../eks/04-eks-storage-part1.md)中的所有权和前置条件。除非另有说明，示例使用常规 Linux EC2 存储；Auto Mode、Fargate 和 Hybrid 的支持情况有所不同。本地 schema/mock 检查不能证明 AWS 卷已挂载、数据已恢复或生产性能达到预期。

### 1. 哪个驱动使用 provisioner ebs.csi.aws.com 管理常规 EBS 卷？

- A. Amazon EFS CSI Driver
- B. Amazon EBS CSI Driver
- C. FSx for Lustre CSI Driver
- D. Mountpoint for Amazon S3 CSI Driver

<details>
<summary>显示答案</summary>

**答案：B. Amazon EBS CSI Driver**

该驱动作为 EKS add-on 提供；能够使用并不意味着它会自动安装在每个集群上。EKS Auto Mode 有自己的内置 `ebs.csi.eks.amazonaws.com` 路径。请检查所选计算资源、add-on 所有者、Kubernetes/驱动兼容性以及实际安装状态。

为控制器准备 Pod Identity 或 IRSA 信任关系，并审核 `AmazonEBSCSIDriverPolicyV2`/范围受限的权限；在需要时还要包括客户 KMS 密钥权限。照搬历史策略不能替代当前驱动策略和信任关系。使用源章节中带有防护措施的目录/安装工作流；不要使用字面值为 `latest` 的 AWS API add-on 版本，也不要覆盖其他所有者的安装。

此类支持加密 gp3、感知调度的卷配置、扩容和有意设置的保留策略：
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
快照还需要快照 CRD/控制器以及匹配的 VolumeSnapshotClass。该驱动支持多种 EBS 卷类型，每种都有大小/性能限制。普通 EBS 卷仍位于单个 AZ；Fargate Pod 无法挂载这些卷，不过单独设计的 EBS 控制器可以在 Fargate 上运行。EBS 与 Hybrid Nodes 不兼容。

EFS 和 FSx 有各自受支持的驱动。先前关于不存在官方 S3 CSI 驱动的说法是错误的：Mountpoint CSI 以有限的 POSIX 语义公开现有 S3 bucket，而 S3 Files 使用 EFS CSI 3.0+ 提供独立的共享文件系统接口。

</details>

### 2. 对于 Linux 节点间共享文件且无需 Lustre 客户端的场景，哪种托管 NFS 服务合适？

- A. 普通 gp3 文件系统
- B. Amazon EFS
- C. S3 对象 GET/PUT API
- D. FSx for Lustre

<details>
<summary>显示答案</summary>

**答案：B. Amazon EFS**

EFS 提供共享 NFS 访问并支持 RWX。仅凭有多个 Pod 并不能唯一确定应使用 EFS：RWO 允许多个 Pod 在同一节点上使用卷，FSx for Lustre 也支持共享。应根据实际的协议、一致性、延迟、吞吐量、持久性和成本需求进行选择。

使用受支持的 EFS CSI 安装，并准备所需的控制器 IAM 角色和现有的加密文件系统。在实际客户端所在的 AZ 中准备挂载目标，每个 AZ 最多一个子网，并准备 SG/DNS/NFS 路径。源章节中的设置会捕获 ID 并检查 AZ/VPC 所有权。使用不同的加密设置重用创建令牌，并不能就地加密现有文件系统。
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
5 Gi claim 是绑定元数据，不是目录配额。Access point 会强制执行 POSIX 身份和根目录；IAM/文件系统策略及网络控制决定允许的访问。动态 AP 配置不是 Fargate 的使用路径；请使用其受支持的静态集成。TLS/客户端挂载授权与控制器配置权限是分开的。

EFS Regional 和 One Zone 的故障特性不同。公布的持久性/设计目标以及服务级承诺，并不代表此应用的实测正常运行时间保证。存储自动增长并不能免除吞吐量/IOPS、配额、备份和成本规划。AWS 建议使用 General Purpose 性能模式；Max I/O 的操作延迟更高。请审慎选择 Elastic、Provisioned 或 Bursting，而不要假设存在适用于所有场景的默认选项。

对于静态应用设置，ConfigMaps/Secrets 可能比共享存储更合适。共享可变文件需要应用锁定/一致性机制。S3 API、Mountpoint 和 S3 Files 是不同的接口；不要一概否定所有 S3 文件访问。FSx for Lustre 是一种并行文件系统替代方案，不能仅仅因为其设置不同就认为它不合适。

</details>

### 3. 哪项关于普通 EBS 文件系统限制的说法正确？

- A. 同一卷可以挂载到任意 AZ
- B. Fargate Pod 可以挂载任意 EBS 卷
- C. 卷位于一个 AZ；RWO 可供同一节点上的多个 Pod 使用
- D. RWO 保证恰好只有一个 Pod

<details>
<summary>显示答案</summary>

**答案：C. 卷位于一个 AZ；RWO 可供同一节点上的多个 Pod 共享。**

RWO 表示由一个节点读写，而不是由一个 Pod 读写。在安全完成分离/挂载后，替代 Pod 可以在该 AZ 中的另一合适节点上使用同一个 PVC。它不能跨 AZ 挂载同一个卷。快照恢复会在目标 AZ 中创建另一个卷；这不是就地迁移，也不是持续复制。
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
使用 `WaitForFirstConsumer`，让调度约束影响卷的初始放置位置。已绑定的 PVC 仍受其 PV 拓扑约束；更改节点选择器不能迁移其数据。StatefulSet 为每个副本创建的 PVC 对应独立卷，并不代表数据库复制。跨 AZ 可用性需要应用/数据复制或恢复设计。

EBS CSI 1.66.0 还支持 io2 原始块 Multi-Attach 路径，具有 RWX，并要求基础设施/应用进行兼容协调。这不会让普通 gp3/ext4 卷变成可供多节点共享的文件系统。Fargate Pod 仍不能挂载 EBS。若有共享文件系统需求，请使用合适的共享文件系统。

</details>

### 4. 每个动态配置的 EBS claim 是否都必须只使用 ReadWriteOnce？

<details>
<summary>显示答案</summary>

**答案：不必。RWO 是普通示例；RWOP 和专用原始块模式有不同的要求。**

RWOP 提供 RWO 不具备的单 Pod 约束。它自 Kubernetes 1.29 起已稳定，且需要兼容的 CSI sidecar 栈。对于不具备较新单节点能力的驱动，CSI 访问模式转换可以将 RWOP 映射为 SINGLE_NODE_WRITER；仅查看该驱动常量并不能证明不支持 RWOP。下面是单 Pod 工作负载可采用的**替代 claim**：
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
| 模式 | 含义 |
|---|---|
| RWO | 一个读写节点；该节点上的多个 Pod 可以共享它 |
| RWOP | 在兼容的 CSI/Kubernetes 支持下，整个集群中仅限一个 Pod |
| RWX | 只有在后端/驱动和应用支持时，才允许多节点写入 |
| ROX | 多节点读取能力；并非每个 CSI 驱动都普遍支持 |

访问模式匹配不能替代文件系统/IAM 权限或显式的只读挂载。从快照恢复出的独立卷是各自独立的副本；它们不是一个共享的 ROX 卷。不要将普通 ext4/XFS 文件系统分别挂载到多个写入方，以此替代集群存储设计。

</details>

### 5. 基于 EBS 的 Pod 在另一节点上被替换时会发生什么？

<details>
<summary>显示答案</summary>

**答案：保留的卷可以在同一个 AZ 中安全地分离/挂载；必须验证恢复时间和应用一致性。**

Kubernetes 会创建替代 Pod；它不会迁移原 Pod 对象。对于单一挂载卷，必须先停止/隔离旧写入方并安全分离卷，然后才能将其挂载到新节点。卷会按其生命周期继续存在，但突然故障可能导致未刷新的写入丢失，或者需要进行文件系统/数据库恢复。不要声称每次写入都保证能够保留。

原先的“10–30 秒”重新挂载时间在此处没有经过验证的测量来源。这里保留它作为**未经验证的历史估算**，而非 AWS SLA 或恢复保证。节点故障检测、隔离、控制器协调、卷操作和应用启动都可能耗时更长。

PDB 约束适用的自愿驱逐，不约束节点/AZ 故障。应根据实际副本数/法定人数设置 PDB；单个数据库副本不会因为有 PDB 就变成高可用。Readiness 应验证应用是否已就绪，而不只是检查持久化的 `/data/ready` 标记；liveness 会重启容器，但不会控制 Service 流量。StatefulSet 顺序和拓扑分散不会跨 AZ 复制一个 EBS 卷。按 AZ 设置 PDB 的方案还要求 Pod 具有实际匹配的标签；节点的 zone 标签不会自动复制到 Pod 上。

尽可能使用优雅关闭，检查 VolumeAttachment/Pod 事件及实际节点状态，并遵循文档化的恢复流程。没有进行隔离就强制分离，或删除挂载元数据，并不是通用的延迟优化方法。请使用独立备份测试恢复后的应用数据和恢复目标。

</details>

### 6. 哪个资源用于请求 EBS 快照？怎样才能确保备份可用？

<details>
<summary>显示答案</summary>

**答案：`VolumeSnapshot`**

准备兼容的快照 CRD/控制器和 EBS snapshotter，并使用驱动与实际 provisioner 匹配的类。保留 add-on 所有权，不要应用浮动的 master 清单。快照一致性可能需要数据库感知的备份/静默操作；块快照显示就绪并不能证明应用能够恢复。
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
在同一 namespace 中恢复到一个新的 claim，其容量至少为 `status.restoreSize`；为 WaitForFirstConsumer 绑定使用一个使用者，并验证数据。此清单恢复的是上文**名称固定的 ebs-snapshot**；若恢复其他快照，请更改名称。
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
如需重复创建，可以使用以下**替代方案**：它会创建唯一快照并等待其就绪。请记录生成的名称。若要安排该任务，需要范围经过审慎限制的 ServiceAccount/RBAC、固定版本的工具、明确选择 UTC/时区、不重叠运行以及错误/保留处理；以前那些未指定的服务账户并不是已安装的备份系统。
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
如需设置保留策略，请解析绝对时间戳，并按 namespace、备份标签和源 PVC 限定范围。以下操作只生成**供审核的候选列表**，不会删除任何内容。自动删除前，请检查每个已绑定 VolumeSnapshotContent 的 deletionPolicy、所有权、依赖项和已验证的恢复点。Delete 策略可能删除 AWS 快照；Retain 会保留快照并可能产生存储费用。生产备份控制器需要 UID/前置条件处理和恢复测试，而不是无范围限制的 xargs 删除管道。
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
在集群/账户/Region 之间传输快照，需要显式进行快照导入/复制、配置 KMS 访问权限和恢复设置。将生产数据复制到测试环境时，也要同样谨慎地控制访问和保留。请验证实际数据，而不只是检查是否存在 VolumeSnapshot 对象。

</details>

### 7. 为数据库、共享文件和并行 ML 数据设计存储。

<details>
<summary>显示答案</summary>

**答案：根据每项需求选择后端和生命周期，并明确列出前置条件。**

这是一份经过审核的配置蓝图，**并非已部署的生产系统**。首先创建/审核 `database`、`application` 和 `ml-workloads` namespace、兼容的 CSI 驱动和 IAM 角色、KMS/网络权限、实际的 EFS/FSx/S3 资源，以及镜像/计算兼容性。StorageClass 是集群范围的；这些示例是由同一所有者管理的替代方案。必须在目标环境中测试容量、应用恢复能力和性能。

**1. 数据库块存储。** 保留原示例中的 16,000 IOPS/1,000 MiB/s 设置，但不要称其为所有 gp3 卷的通用最大值。目前 Regional gp3 支持最高 80,000 IOPS 和 2,000 MiB/s，但受卷大小/IOPS 比率和实例限制；Outposts 的限制有所不同。此示例只是一个配置选择，既不是基准测试，也不能证明数据库需要承担这笔费用。
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
StatefulSet 会根据其 `data` claim 模板创建 **data-postgres-0**。不要同时创建原先未使用的 `database-data` PVC，也不要为该未使用的 claim 创建快照。请以安全方式管理 `postgres-secret`，其中包含 `password` 键；此处未提供密码值。镜像会从已挂载的文件中读取密码；PGDATA 使用子目录，以免卷根目录的文件系统元数据干扰初始化。
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
此示例使用 PostgreSQL 14.24，即已经核实的 major 14 当前次要版本。Major 14 的支持将于 2026 年 11 月 12 日结束。请规划经过测试且迁移到受支持版本的方案，并在生产环境中固定使用已批准的镜像 digest。此处只有一个副本，并非复制/高可用数据库；没有数据库复制设计就扩展副本数并不能解决问题。显式 PVC 保留策略可在删除/缩容 StatefulSet 时保留 claims，但会遗留数据并可能产生存储费用。

执行应用一致性备份/静默步骤后，为数据库实际使用的 claim 创建快照。此处的类是前文定义的保留型 EBS 快照类：
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
**2. 共享文件。** 静态配置通常应放在 ConfigMaps/Secrets 中。如果需要共享可变文件，源章节中的 EFS 类会提供独立的 AP 目录以及 UID/GID 1000。请替换文件系统 ID 并验证客户端路径/权限；此 claim 不会强制执行 5 Gi 配额。
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
此初始化 Job 只写入不敏感的演示设置，并会保留已有文件。三个读取 Pod 以只读方式挂载该文件并检查其可读性。这只是演示文件分发；实际应用必须解析/重新加载其配置。将 `/etc/config` 挂载到未经其他配置的 nginx 中，并不会让 nginx 使用这些文件。
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
        image: busybox:1.38.0
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
        image: busybox:1.38.0
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
**3. 并行 ML 数据。** 准备受支持的 Lustre 客户端/内核、CSI/IAM 和文件系统/S3 集成。此 SCRATCH_2 示例适用于可重建数据；它省略了仅适用于持久类型的每单位吞吐量和自动备份设置。`s3ImportPath` 是有效的 FSx CSI 1.10.0 参数；请将 bucket/prefix 替换为归你所有且可访问的数据集，并审核受支持的集成/Region 设置。LZ4 是一项存储功能，并不能证明实际测得的压缩或吞吐量有所提升。
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
1200 Gi claim 是示例分配；请确认驱动的取整行为和服务容量选项。下面的 Job 是一个**模板**：请将占位符替换为经过测试的非 root GPU 镜像，该镜像包含 `/opt/training/train.py` 并接受所示参数；执行前还要填充数据集。训练代码应保留在镜像中，不要让它被数据挂载覆盖。四个并发 Pod 各请求四个 GPU，可能需要 **16 个 GPU**，此外还需要所请求的 CPU/内存以及适用的配额。Indexed completions 用于标识四个任务；它不会自动实现分布式训练/梯度同步。
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
原有的总体性能说法（“数百 GB/s”和“数百万 IOPS”）并非对这个小型 SCRATCH_2 示例进行的测量。请勿据此确定容量；应使用具有代表性的工作负载验证所选文件系统/客户端配置。此处未执行训练。

**恢复、监控和成本：** 明确选择后端以及文件系统/应用指标，监控实际配额/吞吐量/延迟/使用情况，并使用已知数据测试恢复。保留的 PV 或快照并不等同于备份计划。删除看似未使用的卷前，必须检查所有权、引用关系和已验证的恢复副本。安全方面应使用 Pod Security admission/securityContext、范围受限的 IAM、TLS 和文件系统权限；已移除的 PodSecurityPolicy 不是可选方案。此蓝图既不能证明生产就绪，也不能证明成本/性能已优化。

</details>

### 8. 删除 Pod 总会删除其卷数据吗？

- A. 是，所有卷都会被删除
- B. 不会，请检查其生命周期
- C. 仅当 Pod 有两个容器时才会
- D. 永远不会；所有卷都是持久化的

<details>
<summary>显示答案</summary>

**答案：B. 不会；生命周期取决于卷类型、PVC 所有权和回收策略。**

emptyDir 数据的作用范围是 Pod，而由保留型 PVC 支撑的卷可以在 Pod 结束后继续存在。通用临时 PVC 可以由 Pod 所有。即使 CSI 驱动将实例存储呈现为 PV，物理实例存储数据仍与节点/介质的生命周期绑定；真实的 2026 年 5 月 EC2 Instance Store CSI add-on 并不会将其变成持久化的复制存储。

</details>

### 9. 请求 5 Gi 的 EFS PVC 会强制执行 5 Gi 的目录配额吗？

- A. 会，写入超过 5 Gi 后会失败
- B. 会，每个 access point 都会获得一个块设备
- C. 不会，请求只是绑定元数据
- D. 仅在 directoryPerms700 时才会

<details>
<summary>显示答案</summary>

**答案：C. 不会；它是 Kubernetes 容量/绑定元数据。**

EFS 会随存储的数据增长；该 claim 不会预分配目录，也不会将目录限制在此大小。应另行规划文件系统吞吐量、access point、客户端行为、保留和成本。如需强制执行配额，请使用明确的应用/账户控制措施。

</details>

### 10. StorageClass 中哪个字段设置初始回收策略？

- A. `persistentVolumeReclaimPolicy`
- B. `reclaimPolicy`
- C. `deletionPolicy`
- D. `dataRetention`

<details>
<summary>显示答案</summary>

**答案：B. `reclaimPolicy`**

`persistentVolumeReclaimPolicy` 属于 `PersistentVolume.spec`。StorageClass 中的策略会复制到新配置的 PV 上；更改 class 不会自动修改每一个现有 PV。快照 deletionPolicy 是另一项独立的生命周期设置。

</details>

### 11. 对于动态配置的 EFS access point，Delete 通常会删除什么？

- A. VPC 中的每个文件系统
- B. 总是删除整个 EFS 文件系统
- C. AP；可能还会清理根目录
- D. 永远无法删除任何 AWS 资源

<details>
<summary>显示答案</summary>

**答案：C. Access point；是否删除目录数据取决于控制器配置。**

access-point provisioner 通常不会删除 EFS 文件系统。经过审核的 chart 默认将 deleteAccessPointRootDir 设为 false；启用后会改变数据删除行为。删除任何 claim 前，请检查实际控制器值以及共享/重复使用的 access point 所有权。

</details>

### 12. 关于从 EKS 访问 S3，哪项说法正确？

- A. 不存在官方 S3 CSI 驱动
- B. 各种接口和前置条件有所不同
- C. Mountpoint 会自动创建新的 bucket
- D. 所有 S3 挂载都支持全部 POSIX 操作

<details>
<summary>显示答案</summary>

**答案：B. S3 API、Mountpoint CSI 和 S3 Files 提供不同的接口和要求。**

官方 Mountpoint CSI 通过文件接口支持访问现有 bucket，但 POSIX 语义有限。S3 Files 是独立的共享文件系统服务，由 EFS CSI 3.0+ 支持，且具有不同的控制器/节点权限。不要推断所有基于 S3 的路径都支持相同操作、计算模式或配置模型。

</details>

### 13. 哪些情况可能导致 WaitForFirstConsumer PVC 合理地保持 Pending？

- A. 每个 CSI 驱动都已损坏
- B. 尚未有合适的使用者完成调度
- C. Retain 禁止绑定
- D. PVC 必须使用空 class

<details>
<summary>显示答案</summary>

**答案：B. 尚未调度合适的使用者。**

延迟绑定让调度器的拓扑/资源约束影响放置位置。这不一定意味着存储故障。设置 spec.nodeName 会绕过调度器，并可能阻止此绑定流程；请使用受支持的调度约束。更改 StorageClass 或手动配置卷前，先检查事件。

</details>

### 14. 在 CSI 支持兼容的情况下，哪种访问模式提供单 Pod 约束？

- A. ReadWriteOnce
- B. ReadWriteMany
- C. ReadOnlyMany
- D. ReadWriteOncePod

<details>
<summary>显示答案</summary>

**答案：D. ReadWriteOncePod**

RWO 将读写挂载限制在一个节点，并允许该节点上的多个 Pod 使用。RWOP 是单独的单 Pod 模式；它仍不能替代应用一致性、备份或授权设计。请勿在同一 claim 上同时使用 RWOP 和其他访问模式。

</details>

### 15. 应如何扩展 10 Gi 的 EBS 示例并验证恢复？

<details>
<summary>显示答案</summary>

**答案：允许受支持的扩容，提高 PVC 请求值，验证实际容量并测试独立恢复。**

确认 StorageClass 的 allowVolumeExpansion 以及驱动/文件系统支持情况，进行适当的应用一致性备份，然后通过其所属资源提高 claim 请求值。本演示的目标是 20 Gi。不要缩小卷，也不要编辑 PV 容量来假装已完成调整大小：
```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```
检查 PVC 条件/状态、已挂载的文件系统以及应用 I/O。如果文件系统扩容仍处于待处理状态，请遵循文档化的重新挂载/重启流程。将快照恢复到新 claim 中，使用适当的使用者挂载，并验证已知的应用数据。PVC 请求容量增加或快照对象显示就绪，都不能单独证明数据恢复测试已完成。

</details>

官方参考资料：[EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)、[EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)、[Kubernetes PV](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)、[gp3 规格](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)、[PostgreSQL 支持](https://www.postgresql.org/support/versioning/)、[S3 Files](https://docs.aws.amazon.com/eks/latest/userguide/s3files-csi.html)。
