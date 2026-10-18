# 存储测验

本测验检验你对 Kubernetes 存储概念、卷类型、持久卷、StorageClass 等内容的理解。

## 选择题

1. 哪种资源为应用提供存储，其生命周期独立于普通 Pod 的删除和重新创建？
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir

<details>

<summary>显示答案</summary>

**答案：C) PersistentVolume**

**解析：**
PersistentVolume（PV）是集群存储，可以由集群管理员预置，也可以通过 StorageClass 动态预置。即使 Pod 重启或删除，PV 中的数据仍会保留。ConfigMap 和 Secret 分别用于存储配置数据和敏感信息；emptyDir 则是仅在 Pod 运行期间存在的临时目录。
</details>

2. 在 Kubernetes 中，使用哪种资源来申请 PersistentVolume？
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding

<details>

<summary>显示答案</summary>

**答案：B) PersistentVolumeClaim**

**解析：**
PersistentVolumeClaim（PVC）是用户申请 PersistentVolume 的方式。PVC 表示具有特定容量和访问模式的存储请求。Kubernetes 会查找满足 PVC 要求的 PV，并将二者绑定。
</details>

3. Kubernetes 使用哪种资源动态预置卷？
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner

<details>

<summary>显示答案</summary>

**答案：B) StorageClass**

**解析：**
StorageClass 供管理员描述所提供的存储“类别”。不同类别可以对应不同服务级别、备份策略，或由集群管理员确定的其他策略。使用 StorageClass 时，可以在创建 PVC 时动态预置 PV。
</details>

4. 删除普通 Pod 时，Pod 引用的、单独创建的 PVC 会自动删除吗？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) 不会；单独创建的 PVC 会保留

<details>

<summary>显示答案</summary>

**答案：D) 不会；单独创建的 PVC 会保留**

**解析：**
单独创建的 PVC 不归 Pod 所有，因此 Pod 删除后 PVC 仍会保留。通用临时卷对应的 PVC 则不同：它归 Pod 所有，会随 Pod 一起被垃圾回收。StatefulSet 的 `persistentVolumeClaimRetentionPolicy` 可以在删除 StatefulSet 或缩容时删除模板 PVC；PV 的回收策略决定之后如何清理存储。
</details>

5. 以下哪一项不是 PersistentVolume 的访问模式？
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany

<details>

<summary>显示答案</summary>

**答案：D) WriteOnlyMany**

**解析：**
Kubernetes 中 PersistentVolume 的访问模式包括 ReadWriteOnce（RWO）、ReadOnlyMany（ROX）、ReadWriteMany（RWX）和 ReadWriteOncePod（RWOP，仅适用于 CSI）。WriteOnlyMany 并不是一种访问模式。ReadWriteOnce 允许单个节点以读写方式挂载；ReadOnlyMany 允许多个节点以只读方式挂载；ReadWriteMany 则允许多个节点以读写方式挂载。
</details>

6. 哪种 PersistentVolume 回收策略会释放资源，但不删除卷？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release

<details>

<summary>显示答案</summary>

**答案：B) Retain**

**解析：**
删除 PVC 后，Retain 策略会保留 PV 及其数据。此时卷处于“Released”状态，但不能供其他声明使用。管理员必须手动清理数据，并使卷重新可用。删除 PVC 时，Delete 策略会删除 PV 及外部基础设施（例如 AWS EBS、GCE PD）。Recycle 策略已弃用，应改用动态预置。
</details>

7. Kubernetes 中哪种卷类型提供临时存储？
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) persistentVolumeClaim

<details>

<summary>显示答案</summary>

**答案：B) emptyDir**

**解析：**
Pod 被调度到节点后，系统会首次创建 emptyDir 卷；只要 Pod 仍在该节点上运行，该卷就会存在。顾名思义，卷最初为空。Pod 中的所有容器都可以读写其中的同一批文件，但每个容器可以将卷挂载到相同或不同的路径。无论出于何种原因，只要 Pod 从节点上移除，emptyDir 中的数据就会永久删除。
</details>

8. 哪个 provisioner 标识标准 Amazon EBS CSI 驱动（不包括 EKS Auto Mode）？
   - A) ebs.csi.aws.com
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs

<details>

<summary>显示答案</summary>

**答案：A) ebs.csi.aws.com**

**解析：**
标准 EBS CSI 驱动使用 `ebs.csi.aws.com`；必须安装并配置该驱动及其 IAM 权限。集群不会自动拥有合适的默认 StorageClass。EKS Auto Mode 使用 `ebs.csi.eks.amazonaws.com`。新示例不应再使用旧式 Kubernetes 内置 provisioner。
</details>

9. StatefulSet 中用于卷声明模板的正确字段名是什么？
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates

<details>

<summary>显示答案</summary>

**答案：C) volumeClaimTemplates**

**解析：**
StatefulSet 使用 `volumeClaimTemplates` 字段为每个 Pod 自动创建 PVC。该模板会为 StatefulSet 的每个副本创建 PVC。生成的 PVC 名称遵循 `<volume-claim-template-name>-<pod-name>` 格式。
</details>

10. CSI（Container Storage Interface）在 Kubernetes 中的主要用途是什么？
    - A) 标准化容器之间的通信
    - B) 允许在 Kubernetes 代码之外开发存储驱动
    - C) 标准化对容器镜像仓库的访问
    - D) 自动在云服务商之间迁移存储

<details>

<summary>显示答案</summary>

**答案：B) 允许在 Kubernetes 代码之外开发存储驱动**

**解析：**
CSI（Container Storage Interface）为容器编排系统（例如 Kubernetes）与存储提供商之间定义了一种标准接口。其主要用途是允许在 Kubernetes 代码库之外开发、部署和管理存储驱动。这样，存储提供商就能独立于 Kubernetes 发布周期开发和维护自己的插件。
</details>

## 进阶问题

1. 说明如何在 Kubernetes 中使用 CSI（Container Storage Interface）驱动集成新的存储类型，并说明这样做的优势。

<details>

<summary>显示答案</summary>

**答案：**

**集成 CSI 驱动的方法：**

1. **部署 CSI 驱动**：CSI 驱动通常包含以下组件：
  - **节点插件 DaemonSet**：在每个节点上运行，执行卷挂载和卸载操作。
  - **控制器插件 Deployment/StatefulSet**：执行卷创建、删除和快照操作。
  - **RBAC 资源**：配置所需权限。

2. **创建 StorageClass**：定义使用 CSI 驱动的 StorageClass：
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-storage
provisioner: example.csi.k8s.io  # CSI driver name
parameters:
  # Driver-specific parameters
  type: ssd
  fsType: ext4
```

3. **设置 CSI 卷快照支持**（可选）：
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **测试 CSI 驱动**：创建 PVC 并将其挂载到 Pod，以验证功能。

**使用 CSI 的优势：**

1. **独立的开发周期**：存储提供商可以独立于 Kubernetes 发布周期开发和部署驱动。

2. **标准化接口**：CSI 在容器编排系统与存储提供商之间提供标准接口。

3. **高级存储功能**：以标准化方式支持卷快照、克隆和扩容等高级功能。

4. **增强安全性**：将控制器的 IAM/RBAC 权限限制为所需操作。CSI 节点插件通常需要特权主机访问权限才能挂载卷，因此应单独审查其权限。

5. **丰富的存储选项**：轻松集成云服务商、开源项目和商业解决方案提供的存储。

6. **插件架构**：可以按需添加或移除 CSI 驱动。

**实际实现示例（AWS EBS CSI 驱动）：**
```bash
# First install the EKS EBS CSI add-on with its IAM role using the official guide.
# Snapshot support additionally needs snapshot CRDs and the snapshot controller.

# Create StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
EOF
```

CSI 是 Kubernetes 存储生态系统的核心部分，使各种存储解决方案能够集成进来，并支持使用高级存储功能。
</details>

2. 使用 StatefulSet 和持久化存储设计一个高可用数据库集群。请区分 Kubernetes 的职责与数据库复制机制，并说明备份和恢复方面的要求。

<details>
<summary>显示答案</summary>

**答案：**

1. 使用稳定的 Pod 标识、无头 Service，并为每个数据库成员配置独立 PVC。将成员分散到不同节点和可用区。每个 EBS 卷都属于单个可用区；若要在另一个可用区恢复，必须还原卷或使用数据库复制。
2. 配置数据库 Operator 或经过独立测试的复制系统，以管理唯一服务器 ID、初始数据同步、主节点选举、栅栏机制、复制凭证和客户端路由。仅将 StatefulSet 副本数设为 3 并不能构成高可用数据库。
3. 通过 `ebs.csi.aws.com` 预置加密的 EBS 卷，并配置 `WaitForFirstConsumer`、合适的 gp3 `iops` 值及明确的回收策略。删除声明后，`Retain` 会保留后端存储；但它不等同于备份，也无法防止所有删除途径。
4. ConfigMap 不会展开 `${HOSTNAME##*-}` 这类 shell 表达式。应在 init 容器中生成每个实例专属的配置；只有 MySQL 启动后才能执行 SQL。exec 探针若未通过 shell 执行，也不会展开 `${VARIABLE}`。
5. 使用 CSI 快照时，应安装快照所需的 CRD 和控制器，并使用 EBS `VolumeSnapshotClass`。应先暂停写入，或使用数据库感知型备份，以获得一致的恢复点；还要验证恢复所需的卷大小和驱动兼容性。
6. 执行逻辑备份时，镜像应包含兼容的数据库工具和上传工具（标准 MySQL 镜像不含 AWS CLI）。使用专用的数据库备份用户和权限范围受限的 AWS 身份。转储或上传失败时应让 Job 失败；成功备份应保存在 Pod 之外，并且必须测试恢复。Job 历史记录保留期限不会保留备份文件。
7. 监控复制延迟、存储使用量、备份时间和失败情况，以及恢复测试结果。记录恢复点目标和恢复时间目标，并测试节点和可用区故障下的切换流程。

请参阅 [EBS CSI 安装指南](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) 以及本章中的快照和保留策略示例。

</details>

## 总结

通过本测验，你检验了自己对 Kubernetes 存储概念的理解。我们涵盖了持久卷、持久卷声明、StorageClass、卷类型、访问模式和回收策略，也讨论了 AWS EKS 中的存储配置、CSI 驱动和卷快照等进阶主题。理解并运用这些概念，有助于你在 Kubernetes 中构建可靠且可扩展的存储解决方案。
