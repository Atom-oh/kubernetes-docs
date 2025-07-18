# 스토리지 퀴즈

이 퀴즈는 Kubernetes의 스토리지 개념, 볼륨 유형, 영구 볼륨, 스토리지 클래스 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes에서 포드가 재시작되어도 데이터가 유지되는 스토리지 리소스는 무엇인가요?
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) PersistentVolume**
   
   **설명:**
   PersistentVolume(PV)은 클러스터 관리자가 프로비저닝하거나 스토리지 클래스를 사용하여 동적으로 프로비저닝된 클러스터의 스토리지입니다. PV는 포드가 재시작되거나 삭제되어도 데이터가 유지됩니다. ConfigMap과 Secret은 구성 데이터와 민감한 정보를 저장하는 데 사용되며, emptyDir은 포드가 실행되는 동안에만 존재하는 임시 디렉토리입니다.
   </details>

2. Kubernetes에서 PersistentVolume을 요청하기 위해 사용하는 리소스는 무엇인가요?
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) PersistentVolumeClaim**
   
   **설명:**
   PersistentVolumeClaim(PVC)은 사용자가 PersistentVolume을 요청하는 방법입니다. PVC는 특정 크기와 접근 모드를 가진 스토리지 요청을 나타냅니다. Kubernetes는 PVC의 요구 사항을 충족하는 PV를 찾아 바인딩합니다.
   </details>

3. 다음 중 Kubernetes에서 동적 볼륨 프로비저닝을 위해 사용되는 리소스는 무엇인가요?
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) StorageClass**
   
   **설명:**
   StorageClass는 관리자가 제공하는 스토리지의 "클래스"를 설명하는 방법을 제공합니다. 다른 클래스는 서비스 수준, 백업 정책, 클러스터 관리자가 결정한 임의의 정책에 매핑될 수 있습니다. StorageClass를 사용하면 PVC가 생성될 때 동적으로 PV를 프로비저닝할 수 있습니다.
   </details>

4. Kubernetes에서 포드가 삭제될 때 PersistentVolumeClaim을 자동으로 삭제하는 정책은 무엇인가요?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) 이러한 기능은 제공되지 않음
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: D) 이러한 기능은 제공되지 않음**
   
   **설명:**
   Kubernetes에서는 포드가 삭제될 때 PVC를 자동으로 삭제하는 기능을 기본적으로 제공하지 않습니다. PVC는 포드와 독립적으로 존재하며, 포드가 삭제되어도 PVC는 유지됩니다. 이는 데이터 손실을 방지하기 위한 설계입니다. StatefulSet의 경우 `persistentVolumeClaimRetentionPolicy`를 사용하여 PVC 삭제 정책을 구성할 수 있습니다.
   </details>

5. 다음 중 PersistentVolume의 접근 모드가 아닌 것은 무엇인가요?
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: D) WriteOnlyMany**
   
   **설명:**
   Kubernetes에서 PersistentVolume의 접근 모드는 ReadWriteOnce(RWO), ReadOnlyMany(ROX), ReadWriteMany(RWX)입니다. WriteOnlyMany는 존재하지 않는 접근 모드입니다. ReadWriteOnce는 단일 노드에 의한 읽기-쓰기 마운트를 허용하고, ReadOnlyMany는 여러 노드에 의한 읽기 전용 마운트를 허용하며, ReadWriteMany는 여러 노드에 의한 읽기-쓰기 마운트를 허용합니다.
   </details>

6. PersistentVolume의 Reclaim Policy 중, 볼륨을 삭제하지 않고 리소스만 해제하는 정책은 무엇인가요?
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) Retain**
   
   **설명:**
   Retain 정책은 PVC가 삭제된 후에도 PV와 그 데이터를 유지합니다. 볼륨은 "Released" 상태로 간주되지만, 다른 클레임에서 사용할 수 없습니다. 관리자가 수동으로 데이터를 정리하고 볼륨을 재사용할 수 있도록 해야 합니다. Delete 정책은 PVC가 삭제될 때 PV와 외부 인프라(예: AWS EBS, GCE PD)를 삭제합니다. Recycle 정책은 더 이상 사용되지 않으며, 동적 프로비저닝을 대신 사용하는 것이 좋습니다.
   </details>

7. 다음 중 Kubernetes에서 임시 스토리지를 제공하는 볼륨 유형은 무엇인가요?
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) awsElasticBlockStore
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) emptyDir**
   
   **설명:**
   emptyDir 볼륨은 포드가 노드에 할당될 때 처음 생성되며, 해당 노드에서 포드가 실행되는 동안에만 존재합니다. 이름에서 알 수 있듯이 볼륨은 처음에 비어 있습니다. 포드 내의 모든 컨테이너는 emptyDir 볼륨의 동일한 파일을 읽고 쓸 수 있지만, 볼륨은 각 컨테이너에서 동일하거나 다른 경로에 마운트될 수 있습니다. 포드가 어떤 이유로든 노드에서 제거되면 emptyDir의 데이터는 영구적으로 삭제됩니다.
   </details>

8. AWS EKS에서 기본적으로 사용되는 스토리지 프로비저너는 무엇인가요?
   - A) kubernetes.io/aws-ebs
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: A) kubernetes.io/aws-ebs**
   
   **설명:**
   AWS EKS에서는 기본적으로 AWS EBS(Elastic Block Store)를 사용하여 영구 스토리지를 제공합니다. 프로비저너 이름은 'kubernetes.io/aws-ebs'입니다. 이 프로비저너는 PVC가 생성될 때 자동으로 EBS 볼륨을 생성하고 관리합니다. AWS EKS에서는 gp2, gp3, io1, sc1, st1 등 다양한 EBS 볼륨 유형을 지원합니다.
   </details>

9. 다음 중 StatefulSet에서 사용하는 볼륨 클레임 템플릿의 올바른 필드 이름은 무엇인가요?
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) volumeClaimTemplates**
   
   **설명:**
   StatefulSet에서는 `volumeClaimTemplates` 필드를 사용하여 각 포드에 대한 PVC를 자동으로 생성합니다. 이 템플릿은 StatefulSet의 각 복제본에 대해 PVC를 생성하는 데 사용됩니다. 생성된 PVC의 이름은 `<볼륨 클레임 템플릿 이름>-<포드 이름>`의 형식을 따릅니다.
   </details>

10. Kubernetes에서 CSI(Container Storage Interface)의 주요 목적은 무엇인가요?
    - A) 컨테이너 간 통신을 표준화하기 위함
    - B) 스토리지 드라이버를 Kubernetes 코드 외부에서 개발할 수 있게 하기 위함
    - C) 컨테이너 이미지 저장소 접근을 표준화하기 위함
    - D) 클라우드 제공업체 간 스토리지 마이그레이션을 자동화하기 위함
    
    <details>
    <summary>정답 보기</summary>
    
    **정답: B) 스토리지 드라이버를 Kubernetes 코드 외부에서 개발할 수 있게 하기 위함**
    
    **설명:**
    CSI(Container Storage Interface)는 컨테이너 오케스트레이션 시스템(예: Kubernetes)과 스토리지 공급자 간의 표준 인터페이스를 정의합니다. CSI의 주요 목적은 스토리지 드라이버를 Kubernetes 코드베이스 외부에서 개발, 배포 및 관리할 수 있도록 하는 것입니다. 이를 통해 스토리지 공급자는 Kubernetes 릴리스 주기에 종속되지 않고 자체 플러그인을 개발하고 유지 관리할 수 있습니다.
    </details>

## 심화 문제

1. Kubernetes에서 CSI(Container Storage Interface) 드라이버를 사용하여 새로운 스토리지 유형을 통합하는 방법과 그 이점을 설명하세요.

   <details>
   <summary>정답 보기</summary>
   
   **정답:**
   
   **CSI 드라이버 통합 방법:**
   
   1. **CSI 드라이버 배포**: CSI 드라이버는 일반적으로 다음 구성 요소로 구성됩니다:
      - **노드 플러그인 DaemonSet**: 각 노드에서 실행되며 볼륨 마운트/언마운트 작업 수행
      - **컨트롤러 플러그인 Deployment/StatefulSet**: 볼륨 생성/삭제/스냅샷 등의 작업 수행
      - **RBAC 리소스**: 필요한 권한 설정
   
   2. **StorageClass 생성**: CSI 드라이버를 사용하는 StorageClass 정의:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: csi-storage
   provisioner: example.csi.k8s.io  # CSI 드라이버 이름
   parameters:
     # 드라이버별 파라미터
     type: ssd
     fsType: ext4
   ```
   
   3. **CSI 볼륨 스냅샷 지원 설정** (선택 사항):
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: csi-snapshot-class
   driver: example.csi.k8s.io
   deletionPolicy: Delete
   ```
   
   4. **CSI 드라이버 테스트**: PVC 생성 및 포드에 마운트하여 기능 검증
   
   **CSI 사용의 이점:**
   
   1. **독립적인 개발 주기**: 스토리지 공급자는 Kubernetes 릴리스 주기와 독립적으로 드라이버를 개발하고 배포할 수 있습니다.
   
   2. **표준화된 인터페이스**: CSI는 컨테이너 오케스트레이션 시스템과 스토리지 공급자 간의 표준 인터페이스를 제공합니다.
   
   3. **고급 스토리지 기능**: 볼륨 스냅샷, 복제, 크기 조정 등의 고급 기능을 표준화된 방식으로 지원합니다.
   
   4. **보안 향상**: CSI 드라이버는 제한된 권한으로 실행되며, 필요한 권한만 부여받을 수 있습니다.
   
   5. **다양한 스토리지 옵션**: 클라우드 제공업체, 오픈 소스 및 상용 스토리지 솔루션을 쉽게 통합할 수 있습니다.
   
   6. **플러그인 아키텍처**: 필요에 따라 CSI 드라이버를 추가하거나 제거할 수 있습니다.
   
   **실제 구현 예시 (AWS EBS CSI 드라이버):**
   
   ```bash
   # AWS EBS CSI 드라이버 설치 (Helm 사용)
   helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
   helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
     --namespace kube-system \
     --set enableVolumeScheduling=true \
     --set enableVolumeResizing=true \
     --set enableVolumeSnapshot=true
   
   # StorageClass 생성
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
   
   CSI는 Kubernetes 스토리지 에코시스템의 핵심 부분으로, 다양한 스토리지 솔루션을 통합하고 고급 스토리지 기능을 활용할 수 있게 해줍니다.
   </details>

2. StatefulSet과 PersistentVolume을 사용하여 고가용성 데이터베이스 클러스터를 설계하고, 데이터 지속성과 백업 전략을 설명하세요.

   <details>
   <summary>정답 보기</summary>
   
   **정답:**
   
   **고가용성 데이터베이스 클러스터 설계:**
   
   1. **아키텍처 개요**:
      - 3개 이상의 복제본을 가진 StatefulSet으로 데이터베이스 클러스터 구성
      - 각 포드에 고유한 PersistentVolume 할당
      - 헤드리스 서비스를 통한 안정적인 네트워크 식별자 제공
      - 리더 선출 메커니즘을 통한 마스터-슬레이브 구성
   
   2. **StorageClass 설정**:
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
   
   3. **헤드리스 서비스 생성**:
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
   
   4. **ConfigMap으로 구성 관리**:
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
   
   5. **StatefulSet 정의**:
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
   
   **데이터 지속성 및 백업 전략:**
   
   1. **데이터 지속성 보장**:
      - `reclaimPolicy: Retain`을 사용하여 PV가 실수로 삭제되지 않도록 보호
      - 데이터베이스 엔진의 내구성 설정 활성화 (예: MySQL의 `sync_binlog=1`, `innodb_flush_log_at_trx_commit=1`)
      - 복제를 통한 데이터 중복성 확보
   
   2. **백업 전략**:
      - **정기적인 VolumeSnapshot 생성**:
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
      
      - **데이터베이스 논리적 백업**:
      ```yaml
      apiVersion: batch/v1
      kind: CronJob
      metadata:
        name: db-backup
      spec:
        schedule: "0 2 * * *"  # 매일 02:00에 실행
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
      
      - **백업 검증 및 복원 테스트**: 정기적으로 백업에서 복원 테스트를 수행하여 백업의 유효성 검증
   
   3. **재해 복구 전략**:
      - 다중 가용 영역에 포드 분산 배치
      - 지역 간 백업 복제
      - 자동화된 복구 절차 구현
   
   4. **모니터링 및 알림**:
      - 백업 작업 성공/실패 알림 설정
      - 스토리지 사용량 모니터링
      - 복제 지연 모니터링
   
   이 설계는 StatefulSet의 안정적인 네트워크 식별자와 PersistentVolume의 데이터 지속성을 결합하여 고가용성 데이터베이스 클러스터를 제공합니다. 다중 계층의 백업 전략은 다양한 장애 시나리오에서 데이터 손실을 방지합니다.
   </details>

## 결론

이 퀴즈를 통해 Kubernetes의 스토리지 개념에 대한 이해도를 테스트했습니다. 영구 볼륨, 영구 볼륨 클레임, 스토리지 클래스, 볼륨 유형, 접근 모드, 재확보 정책 등의 개념을 다루었습니다. 또한 AWS EKS에서의 스토리지 구성, CSI 드라이버, 볼륨 스냅샷 등의 고급 주제도 살펴보았습니다. 이러한 개념을 이해하고 활용하면 Kubernetes에서 안정적이고 확장 가능한 스토리지 솔루션을 구축할 수 있습니다.
