# Storage Quiz

This quiz tests your understanding of Kubernetes storage concepts, volume types, persistent volumes, storage classes, and more.

## Multiple Choice Questions

1. What storage resource in Kubernetes persists data even when a pod is restarted?
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

4. What policy in Kubernetes automatically deletes a PersistentVolumeClaim when a pod is deleted?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) This functionality is not provided
   
<details>

<summary>Show Answer</summary>

**Answer: D) This functionality is not provided**

**Explanation:**
Kubernetes does not provide built-in functionality to automatically delete PVCs when pods are deleted. PVCs exist independently of pods and are retained even when pods are deleted. This is a design choice to prevent data loss. For StatefulSets, you can configure PVC deletion policies using `persistentVolumeClaimRetentionPolicy`.
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
The access modes for PersistentVolumes in Kubernetes are ReadWriteOnce (RWO), ReadOnlyMany (ROX), and ReadWriteMany (RWX). WriteOnlyMany does not exist as an access mode. ReadWriteOnce allows read-write mounting by a single node, ReadOnlyMany allows read-only mounting by multiple nodes, and ReadWriteMany allows read-write mounting by multiple nodes.
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
   - D) awsElasticBlockStore
   
<details>

<summary>Show Answer</summary>

**Answer: B) emptyDir**

**Explanation:**
An emptyDir volume is first created when a pod is assigned to a node and exists only as long as that pod is running on that node. As the name suggests, the volume is initially empty. All containers in the pod can read and write the same files in the emptyDir volume, though the volume can be mounted at the same or different paths in each container. When a pod is removed from a node for any reason, the data in the emptyDir is permanently deleted.
</details>

8. What storage provisioner is used by default in AWS EKS?
   - A) kubernetes.io/aws-ebs
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
<details>

<summary>Show Answer</summary>

**Answer: A) kubernetes.io/aws-ebs**

**Explanation:**
AWS EKS uses AWS EBS (Elastic Block Store) by default to provide persistent storage. The provisioner name is 'kubernetes.io/aws-ebs'. This provisioner automatically creates and manages EBS volumes when PVCs are created. AWS EKS supports various EBS volume types including gp2, gp3, io1, sc1, and st1.
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

4. **Enhanced Security**: CSI drivers run with limited privileges and can be granted only the necessary permissions.

5. **Diverse Storage Options**: Easily integrate cloud provider, open source, and commercial storage solutions.

6. **Plugin Architecture**: CSI drivers can be added or removed as needed.

**Real-World Implementation Example (AWS EBS CSI Driver):**

```bash
# Install AWS EBS CSI Driver (using Helm)
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  --namespace kube-system \
  --set enableVolumeScheduling=true \
  --set enableVolumeResizing=true \
  --set enableVolumeSnapshot=true

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

2. Design a highly available database cluster using StatefulSet and PersistentVolume, and explain the data persistence and backup strategy.

<details>

<summary>Show Answer</summary>

**Answer:**

**Highly Available Database Cluster Design:**

1. **Architecture Overview**:
  - Database cluster configured as a StatefulSet with 3 or more replicas
  - Each pod assigned a unique PersistentVolume
  - Stable network identifiers provided through a headless service
  - Master-slave configuration through leader election mechanism

2. **StorageClass Setup**:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iopsPerGB: "3000"
  encrypted: "true"
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

3. **Create Headless Service**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: db-cluster
spec:
  clusterIP: None
  selector:
    app: database
    ports:
      - port: 3306
    name: db
```

4. **Manage Configuration with ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: db-config
data:
  my.cnf: |
    [mysqld]
    server-id = ${HOSTNAME##*-}
    log_bin = /var/lib/mysql/mysql-bin.log
    binlog_format = ROW
    sync_binlog = 1
    innodb_flush_log_at_trx_commit = 1
```

5. **StatefulSet Definition**:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db-cluster
spec:
  serviceName: db-cluster
  replicas: 3
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      initContainers:
        - name: init-config
          image: busybox
          command: ['sh', '-c', 'cp /config-map/my.cnf /etc/mysql/conf.d/']
          volumeMounts:
            - name: config-map
              mountPath: /config-map
            - name: config-dir
              mountPath: /etc/mysql/conf.d/
      containers:
        - name: mysql
          image: mysql:8.0
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
          ports:
            - containerPort: 3306
              name: db
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
            - name: config-dir
              mountPath: /etc/mysql/conf.d/
          readinessProbe:
            exec:
              command: ["mysql", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}", "-e", "SELECT 1"]
            initialDelaySeconds: 30
            periodSeconds: 10
      volumes:
        - name: config-map
          configMap:
            name: db-config
        - name: config-dir
          emptyDir: {}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ "ReadWriteOnce" ]
        storageClassName: "fast-storage"
        resources:
          requests:
            storage: 50Gi
```

**Data Persistence and Backup Strategy:**

1. **Ensuring Data Persistence**:
  - Use `reclaimPolicy: Retain` to protect PVs from accidental deletion
  - Enable durability settings in the database engine (e.g., MySQL's `sync_binlog=1`, `innodb_flush_log_at_trx_commit=1`)
  - Ensure data redundancy through replication

2. **Backup Strategy**:
  - **Regular VolumeSnapshot Creation**:
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: db-snapshot-{{date}}
spec:
  volumeSnapshotClassName: csi-snapshot-class
  source:
    persistentVolumeClaimName: data-db-cluster-0
```

  - **Database Logical Backup**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: db-backup
spec:
  schedule: "0 2 * * *"  # Runs daily at 02:00
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: mysql:8.0
              command:
                - /bin/sh
                - -c
                - |
                  mysqldump -h db-cluster-0.db-cluster -u root -p"${MYSQL_ROOT_PASSWORD}" --all-databases > /backup/full-backup-$(date +%Y%m%d).sql
                  aws s3 cp /backup/full-backup-$(date +%Y%m%d).sql s3://my-backup-bucket/
              env:
                - name: MYSQL_ROOT_PASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: mysql-secret
                      key: password
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          volumes:
            - name: backup-volume
              emptyDir: {}
          restartPolicy: OnFailure
```

  - **Backup Verification and Recovery Testing**: Regularly perform recovery tests from backups to verify backup validity

3. **Disaster Recovery Strategy**:
  - Distribute pods across multiple availability zones
  - Replicate backups across regions
  - Implement automated recovery procedures

4. **Monitoring and Alerting**:
  - Set up alerts for backup job success/failure
  - Monitor storage usage
  - Monitor replication lag

This design combines StatefulSet's stable network identifiers with PersistentVolume's data persistence to provide a highly available database cluster. The multi-layered backup strategy prevents data loss in various failure scenarios.
</details>

## Conclusion

Through this quiz, you tested your understanding of Kubernetes storage concepts. We covered concepts including persistent volumes, persistent volume claims, storage classes, volume types, access modes, and reclaim policies. We also explored advanced topics such as storage configuration in AWS EKS, CSI drivers, and volume snapshots. Understanding and utilizing these concepts enables you to build reliable and scalable storage solutions in Kubernetes.
