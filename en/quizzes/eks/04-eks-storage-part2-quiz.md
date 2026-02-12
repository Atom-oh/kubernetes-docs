# Amazon EKS Storage Quiz (Part 2)

This quiz tests your understanding of advanced storage concepts in Amazon EKS, including storage optimization, backup and recovery strategies, and storage solutions for various workloads.

## Multiple Choice Questions

### 1. What is the most effective method for creating PersistentVolumeClaims when using StatefulSet in Amazon EKS?

A. Manually create PVCs for each pod
B. Use volumeClaimTemplates
C. Use ConfigMap to define PVCs
D. Disable dynamic provisioning

<details>
<summary>Show Answer</summary>

**Answer: B. Use volumeClaimTemplates**

**Explanation:**
The most effective method for creating PersistentVolumeClaims (PVCs) when using StatefulSet in Amazon EKS is to use `volumeClaimTemplates`. This method automatically creates unique PVCs for each pod in the StatefulSet, and they are managed independently of the pod lifecycle.

**Key Features of volumeClaimTemplates:**

1. **Automatic PVC Creation**: Unique PVCs are automatically created for each pod in the StatefulSet.
   ```yaml
   volumeClaimTemplates:
   - metadata:
       name: data
     spec:
       accessModes: [ "ReadWriteOnce" ]
       storageClassName: ebs-sc
       resources:
         requests:
           storage: 10Gi
   ```

2. **Stable Storage**: The same PVC is reused even when a pod is restarted or rescheduled.

3. **Naming Convention**: PVC names are created in the format `<volumeClaimTemplate-name>-<statefulset-name>-<ordinal>`.
   Example: `data-mysql-0`, `data-mysql-1`, `data-mysql-2`

4. **Sequential Deployment**: StatefulSet creates and deletes pods sequentially, so storage operations are also processed sequentially.

**StatefulSet Example:**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 3
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:5.7
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 10Gi
```

**Benefits of volumeClaimTemplates:**

1. **Automation**: No need to manually create and manage PVCs.

2. **Scalability**: PVCs are automatically created when adjusting StatefulSet replicas.

3. **Data Persistence**: PVCs and data are retained even when pods are deleted.

4. **Order Guarantee**: Pod and PVC creation and deletion order is guaranteed.

**Cautions:**

1. **PVC Deletion Policy**: PVCs are not automatically deleted when StatefulSet is deleted. This is designed to prevent data loss.
   ```bash
   # Check PVCs after StatefulSet deletion
   kubectl get pvc -l app=mysql

   # Manually delete PVCs if needed
   kubectl delete pvc data-mysql-0 data-mysql-1 data-mysql-2
   ```

2. **Storage Class Selection**: Select an appropriate storage class to meet workload requirements.
   - EBS: Single node access (RWO)
   - EFS: Multi-node access (RWX)

3. **Volume Binding Mode**: Use `WaitForFirstConsumer` to ensure volumes are created in the availability zone where the pod is scheduled.
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-sc
   provisioner: ebs.csi.aws.com
   volumeBindingMode: WaitForFirstConsumer
   ```

Issues with other options:
- **A. Manually create PVCs for each pod**: Manual creation is error-prone, lacks scalability, and does not leverage StatefulSet automation benefits.
- **C. Use ConfigMap to define PVCs**: ConfigMap is used to store configuration data and cannot be used directly to create PVCs.
- **D. Disable dynamic provisioning**: Disabling dynamic provisioning increases management overhead as PVCs must be created manually.
</details>

### 2. What is the most effective method for optimizing EBS volume performance in Amazon EKS?

A. Use provisioned IOPS (io1) type for all EBS volumes
B. Select appropriate EBS volume types based on workload requirements
C. Provision maximum size for all EBS volumes
D. Place all pods in the same availability zone

<details>
<summary>Show Answer</summary>

**Answer: B. Select appropriate EBS volume types based on workload requirements**

**Explanation:**
The most effective method for optimizing EBS volume performance in Amazon EKS is to select appropriate EBS volume types based on workload requirements. Each EBS volume type has different performance characteristics and cost structures, so it's important to choose the volume type that matches your workload's characteristics.

**Main EBS Volume Types and Characteristics:**

1. **gp3 (General Purpose SSD)**:
   - Baseline Performance: 3,000 IOPS, 125MB/s throughput
   - Maximum Performance: 16,000 IOPS, 1,000MB/s throughput
   - Use Cases: Boot volumes, development and test environments, small to medium databases
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: "8000"
     throughput: "500"
   ```

2. **io1/io2 (Provisioned IOPS SSD)**:
   - Maximum Performance: 64,000 IOPS, 1,000MB/s throughput
   - Use Cases: I/O-intensive databases, latency-sensitive workloads
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-io2
   provisioner: ebs.csi.aws.com
   parameters:
     type: io2
     iops: "25000"
   ```

3. **st1 (Throughput Optimized HDD)**:
   - Maximum Performance: 500 IOPS, 500MB/s throughput
   - Use Cases: Big data, data warehouses, log processing
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-st1
   provisioner: ebs.csi.aws.com
   parameters:
     type: st1
   ```

4. **sc1 (Cold HDD)**:
   - Maximum Performance: 250 IOPS, 250MB/s throughput
   - Use Cases: Infrequently accessed data, archives
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-sc1
   provisioner: ebs.csi.aws.com
   parameters:
     type: sc1
   ```

**Optimal Volume Type Selection by Workload:**

1. **Database Workloads**:
   - High performance needed: io2 or high-performance gp3
   - Medium performance needed: gp3
   ```yaml
   # StorageClass for high-performance database
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: database-storage
   provisioner: ebs.csi.aws.com
   parameters:
     type: io2
     iops: "25000"
   volumeBindingMode: WaitForFirstConsumer
   ```

2. **Log and Streaming Workloads**:
   - High throughput needed: st1 or high-throughput gp3
   ```yaml
   # StorageClass for log processing
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: log-storage
   provisioner: ebs.csi.aws.com
   parameters:
     type: st1
   volumeBindingMode: WaitForFirstConsumer
   ```

3. **Web and Application Servers**:
   - Medium performance needed: gp3
   ```yaml
   # StorageClass for web servers
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: web-storage
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: "3000"
     throughput: "125"
   volumeBindingMode: WaitForFirstConsumer
   ```

**Additional Performance Optimization Strategies:**

1. **Volume Size Optimization**: Some volume types (e.g., gp2) scale performance based on size.

2. **Instance Type Consideration**: Use EBS-optimized instances to secure dedicated bandwidth for EBS volumes.

3. **RAID Configuration**: Configure multiple EBS volumes in RAID 0 for improved performance
   ```yaml
   # RAID configuration within pod
   apiVersion: v1
   kind: Pod
   metadata:
     name: raid-pod
   spec:
     containers:
     - name: raid-container
       image: ubuntu:latest
       command: ["/bin/bash", "-c"]
       args:
       - |
         apt-get update && apt-get install -y mdadm
         mdadm --create --verbose /dev/md0 --level=0 --raid-devices=2 /dev/xvdf /dev/xvdg
         mkfs.ext4 /dev/md0
         mount /dev/md0 /data
         # Run application
       volumeMounts:
       - name: vol1
         mountPath: /dev/xvdf
       - name: vol2
         mountPath: /dev/xvdg
       - name: raid-mount
         mountPath: /data
     volumes:
     - name: vol1
       persistentVolumeClaim:
         claimName: ebs-claim-1
     - name: vol2
       persistentVolumeClaim:
         claimName: ebs-claim-2
     - name: raid-mount
       emptyDir: {}
   ```

4. **File System Optimization**: Select and optimize file system suitable for workload
   - XFS: Suitable for large files and parallel I/O
   - ext4: Suitable for general purposes

5. **Monitoring and Adjustment**: Monitor CloudWatch metrics and adjust volume type or configuration as needed

Issues with other options:
- **A. Use provisioned IOPS (io1) type for all EBS volumes**: Using provisioned IOPS for all workloads is not cost-effective, and some workloads may be better suited for other volume types.
- **C. Provision maximum size for all EBS volumes**: Provisioning volumes larger than needed incurs unnecessary costs.
- **D. Place all pods in the same availability zone**: This compromises high availability, and the entire application may be affected by a single availability zone failure.
</details>

### 4. What is the main benefit of using FSx for Lustre in Amazon EKS?

A. Cost efficiency
B. Simple setup
C. High-performance parallel file system
D. Native EKS integration

<details>
<summary>Show Answer</summary>

**Answer: C. High-performance parallel file system**

**Explanation:**
The main benefit of using FSx for Lustre in Amazon EKS is that it provides a high-performance parallel file system. FSx for Lustre is a fully managed file system designed for compute-intensive workloads such as high-performance computing (HPC), machine learning, and big data analytics, offering hundreds of GB/s throughput, millions of IOPS, and sub-millisecond latency.

**Key Performance Characteristics of FSx for Lustre:**

1. **High Throughput**:
   - Up to 1,000GB/s throughput
   - Up to 200MB/s throughput per 1TiB of storage (SSD-based)
   - Suitable for processing large datasets

2. **Low Latency**:
   - Sub-millisecond latency
   - Suitable for latency-sensitive applications

3. **Parallel Access**:
   - Simultaneous access from thousands of compute instances
   - Performance improvement through parallel processing

4. **Scalability**:
   - Scales to hundreds of GB/s throughput
   - Supports petabyte-scale datasets

**FSx for Lustre Integration with EKS:**

1. **CSI Driver**:
   ```bash
   # Install FSx for Lustre CSI driver
   helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
   helm repo update
   helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
     --namespace kube-system \
     --set controller.serviceAccount.create=true \
     --set controller.serviceAccount.name=fsx-csi-controller-sa
   ```

2. **StorageClass Configuration**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: fsx-lustre
   provisioner: fsx.csi.aws.com
   parameters:
     subnetId: subnet-0123456789abcdef0
     securityGroupIds: sg-0123456789abcdef0
     deploymentType: SCRATCH_2
     perUnitStorageThroughput: "200"
     dataCompressionType: "LZ4"
   mountOptions:
     - flock
   ```

3. **PersistentVolumeClaim Creation**:
   ```yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: fsx-claim
   spec:
     accessModes:
       - ReadWriteMany
     storageClassName: fsx-lustre
     resources:
       requests:
         storage: 1200Gi  # Minimum 1.2TiB
   ```

**Workloads Suitable for FSx for Lustre:**

1. **Machine Learning and Deep Learning**:
   - Large dataset training
   - Distributed training jobs
   - Model serving

2. **High-Performance Computing (HPC)**:
   - Scientific simulations
   - Weather forecasting
   - Genomics

3. **Big Data Analytics**:
   - Large-scale data processing
   - Real-time analytics
   - ETL jobs

4. **Media Processing**:
   - Video rendering
   - Image processing
   - Content creation

**S3 Integration:**

FSx for Lustre seamlessly integrates with Amazon S3, making it easy to import and process S3 data with the high-performance file system.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-s3
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  perUnitStorageThroughput: "200"
  s3ImportPath: s3://my-bucket/prefix
  s3ExportPath: s3://my-bucket/export
```

**Deployment Type Options:**

1. **SCRATCH_1**:
   - Temporary storage and short-term processing
   - Cost-effective
   - No data replication

2. **SCRATCH_2**:
   - Temporary storage and short-term processing
   - Data replication in case of server failure
   - Better availability than SCRATCH_1

3. **PERSISTENT**:
   - Long-term storage and workloads
   - Data replication and automatic recovery
   - High durability

**Performance Optimization Tips:**

1. **Appropriate Throughput Selection**:
   - SSD storage: 50, 100, 200 MB/s/TiB
   - HDD storage: 12, 40 MB/s/TiB

2. **Enable Data Compression**:
   - Improved storage efficiency through LZ4 compression
   - Reduced network bandwidth usage

3. **File System Size Optimization**:
   - Larger file systems provide more servers and higher aggregate performance

4. **Mount Option Optimization**:
   ```
   mount -t lustre -o noatime,flock file_system_dns_name@tcp:/mountname /mnt/fsx
   ```

Issues with other options:
- **A. Cost efficiency**: FSx for Lustre provides high performance but is generally more expensive than EBS or EFS.
- **B. Simple setup**: FSx for Lustre requires advanced configuration options and has more complex setup than EBS or EFS.
- **D. Native EKS integration**: FSx for Lustre is not natively integrated with EKS; the CSI driver must be installed separately.
</details>

## Short Answer Questions

### 6. What RAID configuration can be used to improve EBS volume performance in Amazon EKS?

<details>
<summary>Show Answer</summary>

**Answer:**
RAID 0 (Striping)

**Detailed Explanation:**

The RAID configuration that can be used to improve EBS volume performance in Amazon EKS is RAID 0 (striping). RAID 0 distributes data across multiple EBS volumes to improve I/O performance.

**How RAID 0 Works:**

RAID 0 stores data by distributing it across multiple disks, with each disk handling a portion of the total I/O workload, thereby improving overall performance. For example, configuring RAID 0 with 2 EBS volumes can theoretically double throughput and IOPS.

**Key Features of RAID 0:**

1. **Performance Improvement**: I/O operations are processed in parallel across multiple volumes, increasing throughput and IOPS.

2. **Capacity Aggregation**: Capacity from all volumes is aggregated and used as one large volume.

3. **No Fault Tolerance**: If one volume fails, all data in the entire RAID array is lost.

**How to Configure RAID 0 in EKS:**

1. **Create Multiple PVCs:**
   ```yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: ebs-claim-1
   spec:
     accessModes:
       - ReadWriteOnce
     storageClassName: ebs-sc
     resources:
       requests:
         storage: 100Gi
   ---
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: ebs-claim-2
   spec:
     accessModes:
       - ReadWriteOnce
     storageClassName: ebs-sc
     resources:
       requests:
         storage: 100Gi
   ```

2. **Configure RAID 0 in Pod:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: raid0-pod
   spec:
     containers:
     - name: raid-container
       image: ubuntu:latest
       command: ["/bin/bash", "-c"]
       args:
       - |
         apt-get update && apt-get install -y mdadm
         mdadm --create --verbose /dev/md0 --level=0 --raid-devices=2 /dev/xvdf /dev/xvdg
         mkfs.ext4 /dev/md0
         mount /dev/md0 /data
         # Run application
         while true; do sleep 30; done
       volumeMounts:
       - name: vol1
         mountPath: /dev/xvdf
       - name: vol2
         mountPath: /dev/xvdg
       - name: raid-mount
         mountPath: /data
       securityContext:
         privileged: true  # Permissions required for RAID configuration
     volumes:
     - name: vol1
       persistentVolumeClaim:
         claimName: ebs-claim-1
     - name: vol2
       persistentVolumeClaim:
         claimName: ebs-claim-2
     - name: raid-mount
       emptyDir: {}
   ```

**RAID 0 Performance Optimization Tips:**

1. **Number of Volumes**: Typically 2-4 volumes provide optimal performance. Too many volumes can increase management overhead.

2. **Volume Size**: Configure all volumes with the same size to evenly distribute performance.

3. **Stripe Size**: Select appropriate stripe size based on workload.
   - Small random I/O: Small stripe size (e.g., 4KB)
   - Large sequential I/O: Large stripe size (e.g., 64KB or 128KB)

4. **Instance Type**: Use EBS-optimized instances to secure dedicated bandwidth for EBS volumes.

**RAID 0 Use Cases:**

1. **High-Performance Databases**: Database workloads requiring high IOPS and throughput

2. **Big Data Processing**: Large-scale data processing and analytics workloads

3. **Media Processing**: I/O-intensive tasks like video encoding/decoding, rendering

**Cautions:**

1. **Data Durability**: RAID 0 has no fault tolerance, so proper backup strategy is needed for important data.

2. **Volume Failure**: If one volume fails, all data may be lost, so regular backups through snapshots are important.

3. **Complexity**: RAID configuration increases management complexity, so use only when really needed.

4. **Cost**: Using multiple EBS volumes increases storage costs.

**Alternative Considerations:**

1. **High-Performance Single Volume**: Use io2 or high-performance gp3 volumes for simplicity

2. **Instance Store**: Consider instance store volumes for temporary data

3. **FSx for Lustre**: Consider parallel file system when very high performance is required

RAID 0 is an effective way to improve EBS volume performance, but it should be used carefully considering data durability and management complexity.
</details>

### 7. What mount options can be used to set read and write buffer sizes to optimize EFS file system performance in Amazon EKS?

<details>
<summary>Show Answer</summary>

**Answer:**
rsize and wsize

**Detailed Explanation:**

The mount options that can be used to set read and write buffer sizes to optimize EFS file system performance in Amazon EKS are `rsize` (read buffer size) and `wsize` (write buffer size). These options determine the size of data chunks used when NFS clients communicate with the EFS file system.

**Role of rsize and wsize:**

1. **rsize (Read Buffer Size)**:
   - Maximum number of bytes used when NFS client reads from server
   - Larger values allow more data to be read with fewer network requests
   - Default is typically 1MB (1048576 bytes)

2. **wsize (Write Buffer Size)**:
   - Maximum number of bytes used when NFS client writes to server
   - Larger values allow more data to be written with fewer network requests
   - Default is typically 1MB (1048576 bytes)

**Setting rsize and wsize in EKS:**

1. **Setting in StorageClass:**
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: efs-sc-optimized
   provisioner: efs.csi.aws.com
   parameters:
     provisioningMode: efs-ap
     fileSystemId: fs-0123456789abcdef0
     directoryPerms: "700"
   mountOptions:
     - rsize=1048576
     - wsize=1048576
   ```

2. **Setting in PersistentVolume:**
   ```yaml
   apiVersion: v1
   kind: PersistentVolume
   metadata:
     name: efs-pv
   spec:
     capacity:
       storage: 5Gi
     volumeMode: Filesystem
     accessModes:
       - ReadWriteMany
     persistentVolumeReclaimPolicy: Retain
     storageClassName: efs-sc
     mountOptions:
       - rsize=1048576
       - wsize=1048576
     csi:
       driver: efs.csi.aws.com
       volumeHandle: fs-0123456789abcdef0
   ```

**Selecting Optimal Values:**

1. **General Recommended Values**:
   - rsize=1048576 (1MB)
   - wsize=1048576 (1MB)

2. **Workload-Specific Optimization**:
   - Large sequential read/write: Larger values (e.g., 1MB)
   - Small random read/write: Smaller values (e.g., 32KB or 64KB)

3. **Network Conditions Consideration**:
   - Stable network: Larger values
   - Unstable network: Smaller values (reduces retransmission overhead on packet loss)

**Additional Performance Optimization Mount Options:**

1. **timeo**: Server response wait time (in 1/10 second units)
   ```
   timeo=600  # 60 seconds
   ```

2. **retrans**: Number of retries before timeout
   ```
   retrans=2
   ```

3. **noresvport**: Use new TCP port on connection recovery
   ```
   noresvport
   ```

4. **noatime**: Disable file access time updates
   ```
   noatime
   ```

**Complete Optimized Mount Options Example:**
```yaml
mountOptions:
  - rsize=1048576
  - wsize=1048576
  - timeo=600
  - retrans=2
  - noresvport
  - noatime
```

**Performance Monitoring and Tuning:**

1. **Performance Measurement**:
   ```bash
   # Read performance test
   dd if=/efs/testfile of=/dev/null bs=1M count=1000

   # Write performance test
   dd if=/dev/zero of=/efs/testfile bs=1M count=1000
   ```

2. **CloudWatch Metrics Monitoring**:
   - TotalIOBytes
   - DataReadIOBytes
   - DataWriteIOBytes
   - MetadataIOBytes

3. **Gradual Tuning**:
   - Test with various rsize/wsize values
   - Select optimal values based on workload patterns

Properly setting rsize and wsize options can significantly improve EFS file system performance, especially for workloads involving large file transfers or high throughput requirements.
</details>

### 9. What is AWS's SLA (Service Level Agreement) for data durability when using EBS volumes in Amazon EKS?

<details>
<summary>Show Answer</summary>

**Answer:**
99.999% (5 9's)

**Detailed Explanation:**

AWS's SLA (Service Level Agreement) for data durability when using EBS volumes in Amazon EKS is 99.999% (5 9's). This means Amazon EBS has less than 0.001% probability of annual data loss.

**Key Features of EBS Durability:**

1. **Design Durability**: Amazon EBS volumes are designed to provide 99.999% durability.

2. **Availability Zone Replication**: EBS volume data is automatically replicated across multiple servers within a single availability zone.

3. **Annual Failure Rate (AFR)**: Targets 0.1% - 0.2% annual failure rate range.

**EBS Volume Type Durability:**

All EBS volume types (gp2, gp3, io1, io2, st1, sc1) have the same 99.999% durability design. However, io2 volumes provide additional durability guarantees:

- **io2 Block Express**: 99.999% availability SLA in addition to 99.999% durability

**Data Protection Enhancement Methods:**

1. **EBS Snapshots**:
   - Data backup through regular snapshots
   - Snapshots are stored in S3 with 99.999999999% (11 9's) durability
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot-class
   driver: ebs.csi.aws.com
   deletionPolicy: Retain
   ```

2. **Cross-Region Snapshot Copy**:
   - Copy snapshots to different regions for disaster recovery
   ```bash
   aws ec2 copy-snapshot \
     --source-region us-west-2 \
     --source-snapshot-id snap-0123456789abcdef0 \
     --destination-region us-east-1 \
     --description "Cross-region backup"
   ```

3. **Automated Backup Policies**:
   - Automated backups using Amazon Data Lifecycle Manager or Kubernetes CronJob
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: ebs-snapshot-job
   spec:
     schedule: "0 0 * * *"  # Daily at midnight
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: snapshot-creator
               image: amazon/aws-cli:latest
               command:
               - /bin/sh
               - -c
               - |
                 # Get volume ID from PVC
                 VOLUME_ID=$(kubectl get pvc my-pvc -o jsonpath='{.spec.volumeName}' | xargs kubectl get pv -o jsonpath='{.spec.csi.volumeHandle}')
                 # Create snapshot
                 aws ec2 create-snapshot --volume-id $VOLUME_ID --description "Daily backup"
             restartPolicy: OnFailure
   ```

**EBS Volume Failure Scenarios and Recovery:**

1. **Volume Corruption**:
   - Symptoms: I/O errors, performance degradation
   - Recovery: Create new volume from latest snapshot

2. **Availability Zone Failure**:
   - Symptoms: Volume inaccessible
   - Recovery: Restore volume from snapshot in different availability zone

3. **Accidental Data Deletion**:
   - Recovery: Restore to specific point-in-time from snapshot

**EBS Durability Best Practices:**

1. **Regular Snapshots**:
   - Create daily or more frequent snapshots for important data
   - Implement snapshot retention policies

2. **Snapshot Testing**:
   - Regularly test restoring from snapshots
   - Document and practice recovery processes

3. **Multi-Region Strategy**:
   - Copy snapshots to different regions for critical data
   - Establish disaster recovery plans

4. **Monitoring and Alerting**:
   - Monitor EBS volume health
   - Set up CloudWatch alarms

**EBS vs Other AWS Storage Services Durability Comparison:**

| Service | Durability | Availability |
|---------|-----------|--------------|
| Amazon EBS | 99.999% | 99.95-99.999% (varies by type) |
| Amazon EFS | 99.999999999% (11 9's) | 99.99% |
| Amazon S3 | 99.999999999% (11 9's) | 99.99% |
| FSx for Lustre | 99.999% | 99.95% |

Amazon EBS's 99.999% durability provides sufficient data protection for most workloads, but for critical data, implementing additional protection layers through regular snapshots and multi-region backup strategies is recommended.
</details>

## Hands-on Questions

### 10. Design a high-performance storage solution for database workloads in an Amazon EKS cluster. Create storage classes, persistent volume claims, and StatefulSet that meet the following requirements:
- PostgreSQL database requiring high IOPS
- Automatic backup and recovery functionality
- Volume expansion capability

<details>
<summary>Show Answer</summary>

**Answer:**

Here's how to design a high-performance storage solution for database workloads in an Amazon EKS cluster:

## 1. High-Performance StorageClass Definition

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: io2
  iops: "25000"  # High IOPS provision
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:region:account-id:key/key-id"  # Optional: Encryption with KMS key
allowVolumeExpansion: true  # Allow volume expansion
reclaimPolicy: Retain  # Retain PV on PVC deletion
```

## 2. PostgreSQL StatefulSet Definition

```yaml
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
  template:
    metadata:
      labels:
        app: postgres
    spec:
      securityContext:
        fsGroup: 999  # PostgreSQL group ID
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        ports:
        - containerPort: 5432
          name: postgres
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 15
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: postgres-io2
      resources:
        requests:
          storage: 100Gi
```

## 3. PostgreSQL Service Definition

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None  # Headless service
```

## 4. VolumeSnapshotClass and CronJob for Automated Backups

```yaml
# VolumeSnapshotClass Definition
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: postgres-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain
parameters:
  # Enable snapshot encryption
  encrypted: "true"
  # Add snapshot tags
  tagSpecification_0_resourceType: "snapshot"
  tagSpecification_0_tags_Purpose: "PostgreSQL Backup"
  tagSpecification_0_tags_Environment: "Production"

# CronJob for automated backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: database
spec:
  schedule: "0 1 * * *"  # Daily at 1 AM
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: postgres-backup-sa  # Service account with appropriate permissions
          containers:
          - name: snapshot-creator
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              # Create snapshot name based on current date
              SNAPSHOT_NAME="postgres-snapshot-$(date +%Y%m%d-%H%M%S)"

              # Create snapshot
              cat <<EOF | kubectl apply -f -
              apiVersion: snapshot.storage.k8s.io/v1
              kind: VolumeSnapshot
              metadata:
                name: $SNAPSHOT_NAME
                namespace: database
              spec:
                volumeSnapshotClassName: postgres-snapshot-class
                source:
                  persistentVolumeClaimName: data-postgres-0
              EOF

              # Delete snapshots older than 30 days
              kubectl get volumesnapshot -n database -o json | \
                jq -r '.items[] | select(.metadata.name | startswith("postgres-snapshot-")) |
                select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) |
                .metadata.name' | \
                xargs -r kubectl delete volumesnapshot -n database
          restartPolicy: OnFailure
```

## 5. Volume Expansion Automation Script

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-volume-monitor
  namespace: database
spec:
  schedule: "0 */6 * * *"  # Run every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: postgres-volume-monitor-sa
          containers:
          - name: volume-monitor
            image: bitnami/kubectl:latest
            command:
            - /bin/bash
            - -c
            - |
              # Get PostgreSQL pod name
              POD_NAME=$(kubectl get pods -n database -l app=postgres -o jsonpath='{.items[0].metadata.name}')

              # Check volume usage
              USAGE_PERCENT=$(kubectl exec -n database $POD_NAME -- df -h /var/lib/postgresql/data | tail -1 | awk '{print $5}' | sed 's/%//')

              # Expand volume if usage is 80% or higher
              if [ $USAGE_PERCENT -ge 80 ]; then
                # Get current PVC size
                CURRENT_SIZE=$(kubectl get pvc data-postgres-0 -n database -o jsonpath='{.spec.resources.requests.storage}')

                # Increase by 50% from current size
                NEW_SIZE=$(echo $CURRENT_SIZE | sed 's/Gi//' | awk '{print int($1 * 1.5)}')

                # Expand PVC
                kubectl patch pvc data-postgres-0 -n database -p "{\"spec\":{\"resources\":{\"requests\":{\"storage\":\"${NEW_SIZE}Gi\"}}}}"

                # Log message
                echo "$(date): Volume expanded from ${CURRENT_SIZE} to ${NEW_SIZE}Gi due to high usage (${USAGE_PERCENT}%)"
              fi
          restartPolicy: OnFailure
```

## 6. Job Template for Recovery Procedures

```yaml
# Job template for recovering from snapshot
apiVersion: batch/v1
kind: Job
metadata:
  name: postgres-restore
  namespace: database
spec:
  template:
    spec:
      serviceAccountName: postgres-restore-sa
      containers:
      - name: restore-manager
        image: bitnami/kubectl:latest
        command:
        - /bin/bash
        - -c
        - |
          # 1. Scale down StatefulSet
          kubectl scale statefulset postgres -n database --replicas=0

          # 2. Delete existing PVC (caution: data will be lost)
          kubectl delete pvc data-postgres-0 -n database

          # 3. Create PVC from snapshot
          cat <<EOF | kubectl apply -f -
          apiVersion: v1
          kind: PersistentVolumeClaim
          metadata:
            name: data-postgres-0
            namespace: database
          spec:
            accessModes:
              - ReadWriteOnce
            storageClassName: postgres-io2
            resources:
              requests:
                storage: 100Gi
            dataSource:
              name: ${SNAPSHOT_NAME}  # Snapshot name to restore
              kind: VolumeSnapshot
              apiGroup: snapshot.storage.k8s.io
          EOF

          # 4. Scale up StatefulSet
          kubectl scale statefulset postgres -n database --replicas=1

          # 5. Check recovery status
          sleep 60
          kubectl get pods -n database -l app=postgres
      restartPolicy: OnFailure
```

## 7. Monitoring and Alerting Setup

```yaml
# ServiceMonitor for PostgreSQL metrics collection (assuming Prometheus)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-monitor
  namespace: database
spec:
  selector:
    matchLabels:
      app: postgres
  endpoints:
  - port: postgres
    interval: 15s
  namespaceSelector:
    matchNames:
    - database
```

## Design Explanation

### 1. High-Performance Storage Selection

- **io2 Volume Type**: EBS volume type optimized for database workloads requiring high IOPS
- **25,000 IOPS**: Sufficient IOPS provision for high-performance database operations
- **Encryption**: Enable EBS volume encryption for data-at-rest security

### 2. Benefits of Using StatefulSet

- **Stable Network ID**: Provides predictable DNS names for each pod
- **Sequential Deployment**: Ensures safe updates for database pods
- **Volume Management**: Automatic PVC creation and management through volumeClaimTemplates

### 3. Automated Backup Strategy

- **Regular Snapshots**: Automated daily snapshot creation
- **Retention Policy**: Automatic deletion of snapshots older than 30 days
- **Tagging**: Add tags to snapshots for improved manageability

### 4. Volume Expansion Automation

- **Usage Monitoring**: Regular volume usage checks
- **Automatic Expansion**: Automatically increase volume size when usage reaches 80% or higher
- **allowVolumeExpansion**: Enable volume expansion in StorageClass

### 5. Recovery Procedures

- **Snapshot-Based Restore**: Create new PVC from snapshot
- **Phased Approach**: Scale down StatefulSet, replace PVC, scale up
- **Status Check**: Verify database status after recovery

### 6. Performance and Stability Considerations

- **Resource Requests and Limits**: Appropriate CPU and memory allocation
- **Health Checks**: Monitor database status through readinessProbe and livenessProbe
- **fsGroup**: Set appropriate file system permissions

### 7. Security Considerations

- **Encrypted Volumes**: Protect data at rest
- **Encrypted Snapshots**: Protect backup data
- **Secrets**: Secure management of database credentials

This design provides a high-performance storage solution for PostgreSQL databases requiring high IOPS, including automatic backup and recovery functionality and volume expansion capability. Additionally, monitoring and alerting setup enables proactive detection and response to storage-related issues.
</details>
