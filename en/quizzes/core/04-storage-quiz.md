# Storage Quiz

This quiz tests your understanding of Kubernetes storage concepts, volume types, persistent volumes, storage classes, and more.

## Multiple Choice Questions

1. Which resource provides application storage with a lifecycle independent of an ordinary Pod being deleted and recreated?
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir
   
<details>

<summary>Show Answer</summary>

**Answer: C) PersistentVolume**

**Explanation:**
PersistentVolume (PV) is cluster storage that is either provisioned by a cluster administrator or dynamically provisioned using a storage class. PVs persist data even when pods are restarted or deleted. ConfigMap and Secret are used to store configuration data and sensitive information respectively, while emptyDir is a temporary directory that only exists while the pod is running.
</details>

2. What resource is used in Kubernetes to request a PersistentVolume?
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding
   
<details>

<summary>Show Answer</summary>

**Answer: B) PersistentVolumeClaim**

**Explanation:**
PersistentVolumeClaim (PVC) is how users request PersistentVolumes. A PVC represents a storage request with a specific size and access mode. Kubernetes finds a PV that meets the PVC's requirements and binds them together.
</details>

3. Which resource is used for dynamic volume provisioning in Kubernetes?
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner
   
<details>

<summary>Show Answer</summary>

**Answer: B) StorageClass**

**Explanation:**
StorageClass provides a way for administrators to describe the "classes" of storage they offer. Different classes may map to service levels, backup policies, or arbitrary policies determined by the cluster administrator. Using StorageClass, PVs can be dynamically provisioned when PVCs are created.
</details>

4. Does deleting an ordinary Pod automatically delete a separately created PVC referenced by it?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) No; the separately created PVC remains
   
<details>

<summary>Show Answer</summary>

**Answer: D) No; the separately created PVC remains**

**Explanation:**
A separately created PVC is not owned by the Pod and remains when that Pod is deleted. Generic ephemeral volume PVCs are different: they are owned by the Pod and garbage-collected with it. StatefulSet `persistentVolumeClaimRetentionPolicy` can delete template PVCs on set deletion or scale-down; PV reclaim policy determines subsequent storage cleanup.
</details>

5. Which of the following is NOT a PersistentVolume access mode?
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany
   
<details>

<summary>Show Answer</summary>

**Answer: D) WriteOnlyMany**

**Explanation:**
The access modes for PersistentVolumes in Kubernetes are ReadWriteOnce (RWO), ReadOnlyMany (ROX), and ReadWriteMany (RWX), and ReadWriteOncePod (RWOP, CSI only). WriteOnlyMany does not exist as an access mode. ReadWriteOnce allows read-write mounting by a single node, ReadOnlyMany allows read-only mounting by multiple nodes, and ReadWriteMany allows read-write mounting by multiple nodes.
</details>

6. Which PersistentVolume Reclaim Policy releases the resource without deleting the volume?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release
   
<details>

<summary>Show Answer</summary>

**Answer: B) Retain**

**Explanation:**
The Retain policy preserves the PV and its data after the PVC is deleted. The volume is considered "Released" but is not available for other claims. The administrator must manually clean up the data and make the volume available for reuse. The Delete policy deletes the PV and external infrastructure (e.g., AWS EBS, GCE PD) when the PVC is deleted. The Recycle policy is deprecated, and dynamic provisioning should be used instead.
</details>

7. Which volume type provides temporary storage in Kubernetes?
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) persistentVolumeClaim
   
<details>

<summary>Show Answer</summary>

**Answer: B) emptyDir**

**Explanation:**
An emptyDir volume is first created when a pod is assigned to a node and exists only as long as that pod is running on that node. As the name suggests, the volume is initially empty. All containers in the pod can read and write the same files in the emptyDir volume, though the volume can be mounted at the same or different paths in each container. When a pod is removed from a node for any reason, the data in the emptyDir is permanently deleted.
</details>

8. Which provisioner identifies the standard Amazon EBS CSI driver (not EKS Auto Mode)?
   - A) ebs.csi.aws.com
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
<details>

<summary>Show Answer</summary>

**Answer: A) ebs.csi.aws.com**

**Explanation:**
The standard EBS CSI driver uses `ebs.csi.aws.com`; its driver and IAM permissions must be installed/configured. A cluster does not automatically have a suitable default StorageClass. EKS Auto Mode uses `ebs.csi.eks.amazonaws.com`. The legacy in-tree provisioner should not be used for new examples.
</details>

9. What is the correct field name for volume claim templates used in StatefulSets?
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates
   
<details>

<summary>Show Answer</summary>

**Answer: C) volumeClaimTemplates**

**Explanation:**
StatefulSets use the `volumeClaimTemplates` field to automatically create PVCs for each pod. This template is used to create PVCs for each replica of the StatefulSet. The created PVC names follow the format `<volume-claim-template-name>-<pod-name>`.
</details>

10. What is the main purpose of CSI (Container Storage Interface) in Kubernetes?
    - A) To standardize communication between containers
    - B) To allow storage drivers to be developed outside of Kubernetes code
    - C) To standardize access to container image registries
    - D) To automate storage migration between cloud providers
    
<details>

<summary>Show Answer</summary>

**Answer: B) To allow storage drivers to be developed outside of Kubernetes code**

**Explanation:**
CSI (Container Storage Interface) defines a standard interface between container orchestration systems (like Kubernetes) and storage providers. The main purpose of CSI is to allow storage drivers to be developed, deployed, and managed outside of the Kubernetes codebase. This enables storage providers to develop and maintain their own plugins independently of the Kubernetes release cycle.
</details>

## Advanced Questions

1. Explain how to integrate new storage types using CSI (Container Storage Interface) drivers in Kubernetes and its benefits.

<details>

<summary>Show Answer</summary>

**Answer:**

**CSI Driver Integration Method:**

1. **Deploy CSI Driver**: CSI drivers typically consist of the following components:
  - **Node Plugin DaemonSet**: Runs on each node and performs volume mount/unmount operations
  - **Controller Plugin Deployment/StatefulSet**: Performs volume creation/deletion/snapshot operations
  - **RBAC Resources**: Sets up required permissions

2. **Create StorageClass**: Define a StorageClass that uses the CSI driver:
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

3. **Set up CSI Volume Snapshot Support** (optional):
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **Test CSI Driver**: Verify functionality by creating a PVC and mounting it to a pod

**Benefits of Using CSI:**

1. **Independent Development Cycle**: Storage providers can develop and deploy drivers independently of the Kubernetes release cycle.

2. **Standardized Interface**: CSI provides a standard interface between container orchestration systems and storage providers.

3. **Advanced Storage Features**: Supports advanced features like volume snapshots, cloning, and resizing in a standardized way.

4. **Enhanced Security**: Scope controller IAM/RBAC to required operations. CSI node plugins commonly need privileged host access to mount volumes, so review their permissions separately.

5. **Diverse Storage Options**: Easily integrate cloud provider, open source, and commercial storage solutions.

6. **Plugin Architecture**: CSI drivers can be added or removed as needed.

**Real-World Implementation Example (AWS EBS CSI Driver):**

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

CSI is a core part of the Kubernetes storage ecosystem, enabling integration of various storage solutions and utilization of advanced storage features.
</details>

2. Design a highly available database cluster using StatefulSet and persistent storage. Distinguish Kubernetes responsibilities from database replication, and explain backup and recovery requirements.

<details>
<summary>Show Answer</summary>

**Answer:**

1. Use stable Pod identities, a headless Service, and a separate PVC per database member. Spread members across nodes/zones. Each EBS volume remains in one Availability Zone; recovering into another zone requires a restored volume or database replication.
2. Configure a database operator or an independently tested replication system for unique server IDs, initial data synchronization, primary election, fencing, replication credentials, and client routing. A StatefulSet with three replicas alone does not create an HA database.
3. Provision encrypted EBS volumes through `ebs.csi.aws.com`, with `WaitForFirstConsumer`, a suitable gp3 `iops` value, and a deliberate reclaim policy. `Retain` preserves backing storage after claim deletion; it is not a backup and does not prevent all deletion paths.
4. A ConfigMap does not expand shell expressions such as `${HOSTNAME##*-}`. Generate instance-specific configuration in an init container; execute SQL only after MySQL has started. Exec probes do not expand `${VARIABLE}` without a shell.
5. For CSI snapshots, install snapshot CRDs/controller and use an EBS `VolumeSnapshotClass`. Quiesce writes or use database-aware backups for consistent recovery points, and verify restore size/driver compatibility.
6. For logical backups, use an image containing the compatible database tools and any upload tool (a stock MySQL image does not include AWS CLI). Use a dedicated database backup user and scoped AWS identity. Fail the Job on dump/upload errors, retain a successful backup outside the Pod, and test restoration. Job history retention does not retain backup files.
7. Monitor replication lag, storage utilization, backup age/failures, and restore tests. Document recovery-point and recovery-time objectives and test failover under node and zone loss.

See the [EBS CSI installation guide](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) and the chapter's snapshot/retention examples.

</details>

## Conclusion

Through this quiz, you tested your understanding of Kubernetes storage concepts. We covered concepts including persistent volumes, persistent volume claims, storage classes, volume types, access modes, and reclaim policies. We also explored advanced topics such as storage configuration in AWS EKS, CSI drivers, and volume snapshots. Understanding and utilizing these concepts enables you to build reliable and scalable storage solutions in Kubernetes.
