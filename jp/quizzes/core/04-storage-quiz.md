# Storage Quiz

このクイズでは、Kubernetes storage concepts、volume types、persistent volumes、storage classes などの理解を確認します。

## Multiple Choice Questions

1. Kubernetes で Pod が再起動されても data を保持する storage resource は何ですか？
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir
   
<details>

<summary>答えを表示</summary>

**答え: C) PersistentVolume**

**解説:**
PersistentVolume (PV) は、cluster administrator によって provision されるか、storage class を使用して動的に provision される cluster storage です。PV は、Pod が再起動または削除されても data を保持します。ConfigMap と Secret はそれぞれ configuration data と sensitive information を保存するために使用される一方、emptyDir は Pod が実行されている間だけ存在する temporary directory です。
</details>

2. Kubernetes で PersistentVolume を request するために使用される resource は何ですか？
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding
   
<details>

<summary>答えを表示</summary>

**答え: B) PersistentVolumeClaim**

**解説:**
PersistentVolumeClaim (PVC) は、user が PersistentVolume を request する方法です。PVC は、特定の size と access mode を持つ storage request を表します。Kubernetes は PVC の requirements を満たす PV を見つけ、それらを bind します。
</details>

3. Kubernetes で dynamic volume provisioning に使用される resource はどれですか？
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner
   
<details>

<summary>答えを表示</summary>

**答え: B) StorageClass**

**解説:**
StorageClass は、administrator が提供する storage の "classes" を記述する方法を提供します。異なる classes は、service level、backup policy、または cluster administrator が決定した任意の policy に対応できます。StorageClass を使用すると、PVC が作成されたときに PV を動的に provision できます。
</details>

4. Kubernetes で Pod が削除されたときに PersistentVolumeClaim を自動的に削除する policy は何ですか？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) この機能は提供されていません
   
<details>

<summary>答えを表示</summary>

**答え: D) この機能は提供されていません**

**解説:**
Kubernetes は、Pod が削除されたときに PVC を自動的に削除する built-in functionality を提供していません。PVC は Pod とは独立して存在し、Pod が削除されても保持されます。これは data loss を防ぐための design choice です。StatefulSets では、`persistentVolumeClaimRetentionPolicy` を使用して PVC deletion policies を構成できます。
</details>

5. 次のうち、PersistentVolume access mode ではないものはどれですか？
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany
   
<details>

<summary>答えを表示</summary>

**答え: D) WriteOnlyMany**

**解説:**
Kubernetes における PersistentVolume の access modes は、ReadWriteOnce (RWO)、ReadOnlyMany (ROX)、ReadWriteMany (RWX) です。WriteOnlyMany は access mode として存在しません。ReadWriteOnce は single node による read-write mount を許可し、ReadOnlyMany は multiple nodes による read-only mount を許可し、ReadWriteMany は multiple nodes による read-write mount を許可します。
</details>

6. volume を削除せずに resource を解放する PersistentVolume Reclaim Policy はどれですか？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release
   
<details>

<summary>答えを表示</summary>

**答え: B) Retain**

**解説:**
Retain policy は、PVC が削除された後も PV とその data を保持します。volume は "Released" と見なされますが、他の claim には利用できません。administrator は data を手動で clean up し、volume を再利用可能にする必要があります。Delete policy は、PVC が削除されたときに PV と external infrastructure（例: AWS EBS、GCE PD）を削除します。Recycle policy は deprecated であり、代わりに dynamic provisioning を使用するべきです。
</details>

7. Kubernetes で temporary storage を提供する volume type はどれですか？
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) awsElasticBlockStore
   
<details>

<summary>答えを表示</summary>

**答え: B) emptyDir**

**解説:**
emptyDir volume は、Pod が node に割り当てられたときに初めて作成され、その Pod がその node 上で実行されている間だけ存在します。名前が示すように、volume は初期状態では空です。Pod 内のすべての container は emptyDir volume 内の同じ files を read/write できますが、各 container で同じ path または異なる path に mount できます。何らかの理由で Pod が node から削除されると、emptyDir 内の data は permanent に削除されます。
</details>

8. AWS EKS でデフォルトで使用される storage provisioner は何ですか？
   - A) kubernetes.io/aws-ebs
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
<details>

<summary>答えを表示</summary>

**答え: A) kubernetes.io/aws-ebs**

**解説:**
AWS EKS は persistent storage を提供するために、デフォルトで AWS EBS (Elastic Block Store) を使用します。provisioner name は 'kubernetes.io/aws-ebs' です。この provisioner は、PVC が作成されたときに EBS volumes を自動的に作成および管理します。AWS EKS は gp2、gp3、io1、sc1、st1 など、さまざまな EBS volume types をサポートします。
</details>

9. StatefulSets で使用される volume claim templates の正しい field name は何ですか？
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates
   
<details>

<summary>答えを表示</summary>

**答え: C) volumeClaimTemplates**

**解説:**
StatefulSets は、各 Pod に対して PVC を自動的に作成するために `volumeClaimTemplates` field を使用します。この template は、StatefulSet の各 replica に対する PVC を作成するために使用されます。作成される PVC names は `<volume-claim-template-name>-<pod-name>` という format に従います。
</details>

10. Kubernetes における CSI (Container Storage Interface) の主な目的は何ですか？
    - A) container 間の communication を standardize すること
    - B) storage driver を Kubernetes code の外部で開発できるようにすること
    - C) container image registries への access を standardize すること
    - D) cloud providers 間の storage migration を automate すること
    
<details>

<summary>答えを表示</summary>

**答え: B) storage driver を Kubernetes code の外部で開発できるようにすること**

**解説:**
CSI (Container Storage Interface) は、container orchestration systems（Kubernetes など）と storage providers の間の standard interface を定義します。CSI の主な目的は、storage driver を Kubernetes codebase の外部で開発、deploy、管理できるようにすることです。これにより、storage providers は Kubernetes release cycle とは独立して独自の plugins を開発および保守できます。
</details>

## Advanced Questions

1. Kubernetes で CSI (Container Storage Interface) drivers を使用して新しい storage types を統合する方法と、その利点を説明してください。

<details>

<summary>答えを表示</summary>

**答え:**

**CSI Driver Integration Method:**

1. **Deploy CSI Driver**: CSI drivers は通常、次の components で構成されます。
  - **Node Plugin DaemonSet**: 各 node で実行され、volume mount/unmount operations を実行します
  - **Controller Plugin Deployment/StatefulSet**: volume creation/deletion/snapshot operations を実行します
  - **RBAC Resources**: 必要な permissions を設定します

2. **Create StorageClass**: CSI driver を使用する StorageClass を定義します。
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

3. **Set up CSI Volume Snapshot Support**（任意）:
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **Test CSI Driver**: PVC を作成し、それを Pod に mount して functionality を verify します

**Benefits of Using CSI:**

1. **Independent Development Cycle**: storage providers は、Kubernetes release cycle とは独立して drivers を開発および deploy できます。

2. **Standardized Interface**: CSI は container orchestration systems と storage providers の間の standard interface を提供します。

3. **Advanced Storage Features**: volume snapshots、cloning、resizing などの advanced features を standardized な方法でサポートします。

4. **Enhanced Security**: CSI drivers は limited privileges で実行され、必要な permissions のみを付与できます。

5. **Diverse Storage Options**: cloud provider、open source、commercial storage solutions を簡単に統合できます。

6. **Plugin Architecture**: CSI drivers は必要に応じて追加または削除できます。

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

CSI は Kubernetes storage ecosystem の core part であり、さまざまな storage solutions の統合と advanced storage features の利用を可能にします。
</details>

2. StatefulSet と PersistentVolume を使用して highly available database cluster を設計し、data persistence と backup strategy を説明してください。

<details>

<summary>答えを表示</summary>

**答え:**

**Highly Available Database Cluster Design:**

1. **Architecture Overview**:
  - database cluster は 3 つ以上の replicas を持つ StatefulSet として構成されます
  - 各 Pod には一意の PersistentVolume が割り当てられます
  - stable network identifiers は headless service を通じて提供されます
  - leader election mechanism を通じた master-slave configuration

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
  - accidental deletion から PV を保護するために `reclaimPolicy: Retain` を使用します
  - database engine で durability settings（例: MySQL の `sync_binlog=1`、`innodb_flush_log_at_trx_commit=1`）を有効にします
  - replication によって data redundancy を確保します

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

  - **Backup Verification and Recovery Testing**: backup の validity を verify するために、backup からの recovery tests を定期的に実行します

3. **Disaster Recovery Strategy**:
  - Pod を multiple availability zones に分散します
  - backup を regions 間で replicate します
  - automated recovery procedures を実装します

4. **Monitoring and Alerting**:
  - backup job の success/failure に対する alerts を設定します
  - storage usage を monitor します
  - replication lag を monitor します

この design は、StatefulSet の stable network identifiers と PersistentVolume の data persistence を組み合わせて、highly available database cluster を提供します。multi-layered backup strategy により、さまざまな failure scenarios で data loss を防ぎます。
</details>

## Conclusion

このクイズを通じて、Kubernetes storage concepts の理解を確認しました。persistent volumes、persistent volume claims、storage classes、volume types、access modes、reclaim policies などの concepts を扱いました。また、AWS EKS での storage configuration、CSI drivers、volume snapshots などの advanced topics も確認しました。これらの concepts を理解し活用することで、Kubernetes で reliable かつ scalable な storage solutions を構築できます。
