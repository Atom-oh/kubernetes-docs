# EKS 스토리지 퀴즈 - Part 1

> **마지막 업데이트**: 2026년 9월 11일

답안은 [스토리지 본문](../../eks/04-eks-storage-part1.md)의 소유권·전제 조건을 따릅니다. 별도 표시가 없으면 일반 Linux EC2 스토리지 예제이며 Auto Mode·Fargate·Hybrid 지원은 다릅니다. 로컬 스키마·모의 검증이 실제 AWS 볼륨 연결·데이터 복구·프로덕션 성능을 증명하지는 않습니다.

### 1. ebs.csi.aws.com provisioner로 일반 EBS 볼륨을 관리하는 드라이버는 무엇인가요?

- A. Amazon EFS CSI Driver
- B. Amazon EBS CSI Driver
- C. FSx for Lustre CSI Driver
- D. Mountpoint for Amazon S3 CSI Driver

<details>
<summary>정답 보기</summary>

**정답: B. Amazon EBS CSI Driver**

EKS add-on으로 제공되지만 모든 클러스터에 자동 설치된다는 뜻은 아닙니다. EKS Auto Mode는 별도 내장 `ebs.csi.eks.amazonaws.com` 경로를 사용합니다. 컴퓨팅·add-on 소유권, Kubernetes/드라이버 호환성과 실제 설치 상태를 확인합니다.

컨트롤러의 Pod Identity 또는 IRSA 신뢰와 검토한 `AmazonEBSCSIDriverPolicyV2`/제한 권한을 준비하고 필요한 고객 KMS 키 권한도 포함합니다. 이전 정책 복사는 현재 드라이버 정책·신뢰 관계를 대체하지 못합니다. 본문의 목록·기존 소유자 검증 설치 절차를 사용하며 AWS API 버전 문자열 `latest`나 다른 소유자 설치 덮어쓰기를 사용하지 않습니다.

아래 class는 암호화 gp3, 스케줄러를 고려한 프로비저닝, 확장과 의도적인 보존을 설정합니다:
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
스냅샷에는 snapshot CRD·controller와 일치하는 VolumeSnapshotClass가 추가로 필요합니다. 여러 EBS 볼륨 유형은 각각 용량·성능 제약이 있습니다. 일반 EBS 볼륨은 한 AZ에 위치하고 Fargate Pod는 마운트할 수 없지만 별도로 설계한 EBS 컨트롤러 자체는 Fargate에 실행할 수 있습니다. Hybrid Nodes에는 EBS를 사용할 수 없습니다.

EFS·FSx에도 각각 지원 드라이버가 있습니다. 공식 S3 CSI가 없다는 기존 설명은 틀렸습니다. Mountpoint CSI는 기존 S3 버킷을 제한된 POSIX 의미로 제공하고, S3 Files는 EFS CSI3.0+의 별도 공유 파일 시스템 인터페이스를 사용합니다.

</details>

### 2. Lustre 클라이언트 없이 Linux 노드 간 파일을 공유하는 관리형 NFS 서비스는 무엇인가요?

- A. Ordinary gp3 filesystem
- B. Amazon EFS
- C. S3 object GET/PUT API
- D. FSx for Lustre

<details>
<summary>정답 보기</summary>

**정답: B. Amazon EFS**

EFS는 공유 NFS 접근과 RWX를 지원합니다. 여러 Pod라는 조건만으로 EFS가 유일한 답은 아닙니다. RWO는 같은 노드의 여러 Pod를 허용하고 FSx for Lustre도 공유를 지원합니다. 실제 프로토콜·일관성·지연·처리량·내구성·비용 요구로 선택합니다.

필요한 컨트롤러 IAM 역할과 기존 암호화 파일 시스템을 가진 지원 EFS CSI 설치를 사용합니다. 실제 클라이언트 AZ마다 서브넷 하나에 mount target을 준비하고 SG·DNS·NFS 경로를 확인합니다. 본문 절차는 ID를 저장하고 AZ/VPC 소유권을 검증합니다. 같은 creation token에 다른 암호화 설정을 주어도 기존 파일 시스템이 제자리에서 암호화되지는 않습니다.
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
5Gi 클레임은 디렉토리 quota가 아닌 바인딩 메타데이터입니다. Access point는 POSIX 신원·루트 디렉토리를 강제하며 IAM·파일 시스템 정책과 네트워크 제어가 접근을 정합니다. 동적 AP 프로비저닝은 Fargate 경로가 아니므로 지원 static 통합을 사용합니다. TLS·클라이언트 마운트 권한은 컨트롤러 프로비저닝 권한과 별개입니다.

EFS Regional과 One Zone의 장애 특성은 다릅니다. 공표한 내구성·설계 목표와 서비스 수준 약정이 이 애플리케이션의 실측 uptime 보장은 아닙니다. 스토리지 자동 증가는 처리량·IOPS·quota·백업·비용 계획을 없애지 않습니다. AWS는 General Purpose를 권장하며 Max I/O는 연산 지연이 더 높습니다. Elastic·Provisioned·Bursting을 의도적으로 선택하고 기본값을 일반화하지 마세요.

정적 애플리케이션 설정에는 공유 스토리지보다 ConfigMap/Secret이 적합할 수 있습니다. 공유 가변 파일은 애플리케이션 locking·일관성 처리가 필요합니다. S3 API·Mountpoint·S3 Files는 별도 인터페이스이므로 모든 S3 파일 접근을 부정하면 안 됩니다. FSx for Lustre는 병렬 파일 시스템 대안이며 설치 방식이 다르다는 이유만으로 부적합하지는 않습니다.

</details>

### 3. 일반 EBS 파일 시스템 제약을 올바르게 설명한 것은 무엇인가요?

- A. The same volume attaches in any AZ
- B. Fargate Pods mount any EBS volume
- C. One AZ; RWO can serve multiple same-node Pods
- D. RWO guarantees exactly one Pod

<details>
<summary>정답 보기</summary>

**정답: C. 볼륨은 한 AZ에 위치하며 같은 노드의 여러 Pod가 RWO를 공유할 수 있습니다.**

RWO는 Pod 하나가 아니라 노드 하나의 읽기/쓰기입니다. 같은 AZ의 적합한 노드로 안전하게 detach/attach한 후 대체 Pod가 같은 PVC를 사용할 수 있습니다. 같은 볼륨을 다른 AZ에 연결할 수는 없습니다. 스냅샷 복원은 대상 AZ의 다른 볼륨 생성이며 제자리 이동이나 지속 복제가 아닙니다.
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
초기 볼륨 배치에 스케줄링 제약이 반영되도록 `WaitForFirstConsumer`를 사용합니다. 바인딩된 PVC는 PV 토폴로지에 제약되며 node selector 변경으로 데이터를 이동하지는 못합니다. StatefulSet의 복제본별 PVC는 별도 볼륨이지 DB 복제 기능이 아닙니다. 다중 AZ 가용성에는 애플리케이션·데이터 복제 또는 복구 설계가 필요합니다.

EBS CSI1.66.0은 호환 인프라와 애플리케이션 조정을 전제로 io2 raw block Multi-Attach/RWX 경로도 지원합니다. 이것이 일반 gp3/ext4를 여러 노드의 공유 파일 시스템으로 만들지는 않습니다. Fargate Pod에는 EBS를 마운트할 수 없습니다. 공유 파일 시스템이 필요하면 그 요구에 맞는 백엔드를 선택하세요.

</details>

### 4. 동적으로 프로비저닝하는 모든 EBS 클레임은 ReadWriteOnce만 사용해야 하나요?

<details>
<summary>정답 보기</summary>

**정답: 아니요. RWO는 일반 예제이며 RWOP와 특수 raw block 모드는 요건이 다릅니다.**

RWOP는 RWO가 제공하지 않는 Pod 하나 제약을 제공합니다. Kubernetes1.29부터 stable이며 호환 CSI sidecar 구성이 필요합니다. 최신 single-node capability가 없는 드라이버에는 CSI 변환 계층이 RWOP를 SINGLE_NODE_WRITER로 매핑할 수 있으므로 드라이버 상수만 보고 RWOP 미지원이라고 판단하면 안 됩니다. 아래는 Pod 하나 워크로드용 **대안 클레임**입니다:
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
| 모드 | 의미 |
|---|---|
| RWO | 읽기/쓰기 노드 하나; 그 노드의 여러 Pod가 공유 가능 |
| RWOP | 호환 CSI/Kubernetes에서 클러스터 전체 Pod 하나 |
| RWX | 백엔드·드라이버·애플리케이션이 지원할 때 다중 노드 쓰기 |
| ROX | 다중 노드 읽기 기능; 모든 CSI 드라이버가 보편적으로 지원하지 않음 |

접근 모드 매칭은 파일 시스템·IAM 권한이나 명시적 read-only 마운트를 대체하지 않습니다. 스냅샷에서 각각 복원한 볼륨은 독립 복사본이지 하나의 공유 ROX 볼륨이 아닙니다. 일반 ext4/XFS의 독립적인 다중 writer 마운트를 클러스터 스토리지 설계 대신 사용하지 마세요.

</details>

### 5. EBS를 사용하는 Pod가 다른 노드에서 대체되면 어떻게 되나요?

<details>
<summary>정답 보기</summary>

**정답: 보존된 볼륨을 같은 AZ에서 안전하게 detach/attach할 수 있으며 복구 시간·애플리케이션 일관성을 검증해야 합니다.**

Kubernetes는 원래 Pod 객체를 이동하지 않고 대체 Pod를 만듭니다. Single-attach 볼륨은 이전 writer가 중지·fencing되고 안전하게 분리된 뒤 새 노드에 연결되어야 합니다. 볼륨은 수명 정책에 따라 유지되지만 갑작스러운 장애로 미반영 쓰기가 소실되거나 파일 시스템·DB 복구가 필요할 수 있습니다. 모든 쓰기가 무조건 보존된다고 주장하지 않습니다.

기존 “10–30초” 재연결 시간은 이 문서에서 검증된 측정 출처가 없습니다. **검증되지 않은 과거 추정값**으로 보존하며 AWS SLA나 복구 보장이 아닙니다. 노드 장애 탐지·fencing·컨트롤러 재조정·볼륨 작업·애플리케이션 시작은 더 오래 걸릴 수 있습니다.

PDB는 해당 자발적 eviction을 제한하며 노드/AZ 장애를 막지 못합니다. 실제 복제본·quorum에 맞춰 설정하고 단일 DB 복제본에 PDB를 추가했다고 고가용성이 되지는 않습니다. Readiness는 영구 `/data/ready` 파일 존재뿐 아니라 애플리케이션 준비 상태를 검증해야 합니다. Liveness는 컨테이너를 재시작하며 Service 트래픽을 차단하는 프로브가 아닙니다. StatefulSet 순서나 topology spread가 EBS 하나를 여러 AZ에 복제하지 않습니다. AZ별 PDB도 실제 Pod 레이블이 맞아야 하며 노드 zone 레이블이 Pod에 자동 복사되지는 않습니다.

가능하면 정상 종료를 사용하고 VolumeAttachment·Pod 이벤트와 실제 노드 상태를 진단하여 문서화된 복구 절차를 따릅니다. Fencing 없이 강제 detach나 연결 메타데이터 삭제를 지연 최적화처럼 사용하지 않습니다. 독립 백업으로 복원 데이터와 복구 목표를 검증하세요.

</details>

### 6. EBS 스냅샷을 요청하는 리소스는 무엇이며 사용 가능한 백업에는 무엇이 필요한가요?

<details>
<summary>정답 보기</summary>

**정답: `VolumeSnapshot`**

실제 provisioner와 일치하는 class, 호환 snapshot CRD·controller와 EBS snapshotter를 준비합니다. Floating master 매니페스트 대신 add-on 소유권을 보존합니다. 일관성을 위해 DB-aware 백업·quiescing이 필요할 수 있으며 준비된 블록 스냅샷만으로 애플리케이션 복구를 증명하지는 않습니다.
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
같은 네임스페이스에 `status.restoreSize` 이상 용량의 새 클레임으로 복원하고 WaitForFirstConsumer 소비 Pod와 데이터를 검증합니다. 아래는 **위의 고정 이름 ebs-snapshot** 복원용이며 다른 스냅샷이면 이름을 바꿉니다.
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
반복 생성에는 고유 이름과 준비 확인을 사용하는 아래 **대안** 명령을 쓸 수 있습니다. 반환 이름을 기록하세요. 예약 실행에는 범위를 정한 ServiceAccount/RBAC, 고정 도구, UTC/시간대 선택, 실행 중복 방지와 오류·보존 처리가 필요합니다. 이전에 이름만 적힌 ServiceAccount는 설치된 백업 시스템이 아니었습니다.
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
보존 관리는 절대 시각을 파싱하고 네임스페이스·백업 레이블·소스 PVC로 범위를 정합니다. 아래는 **검토용 후보 목록만** 출력하며 삭제하지 않습니다. 자동 제거 전에 연결된 VolumeSnapshotContent의 deletionPolicy, 소유권·의존성과 검증한 복구 지점을 확인하세요. Delete는 AWS 스냅샷을 제거할 수 있고 Retain은 보존하여 요금이 남을 수 있습니다. 프로덕션 백업 컨트롤러에는 UID/precondition 처리·복구 테스트가 필요하며 범위 없는 xargs 삭제 파이프라인으로 대체하지 않습니다.
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
클러스터·계정·리전 간 스냅샷 이동에는 명시적 import/copy, KMS 접근과 복원 구성이 필요합니다. 테스트 환경으로 복사한 프로덕션 데이터도 접근·보존을 관리하며 VolumeSnapshot 객체 존재만 보지 말고 실제 데이터를 검증합니다.

</details>

### 7. DB, 공유 파일, 병렬 ML 데이터의 스토리지를 설계하세요.

<details>
<summary>정답 보기</summary>

**정답: 요구별 백엔드·수명 주기를 선택하고 전제 조건을 명시합니다.**

아래는 검토한 구성 청사진이며 **배포된 프로덕션 시스템은 아닙니다**. `database`, `application`, `ml-workloads` 네임스페이스, 호환 CSI 드라이버·IAM 역할, KMS·네트워크 권한, 실제 EFS/FSx/S3 리소스와 이미지·컴퓨팅 호환성을 먼저 준비·검토합니다. StorageClass는 클러스터 범위이며 예제는 소유자 하나가 관리하는 대안입니다. 실제 환경에서 용량·애플리케이션 복구·성능을 테스트해야 합니다.

**1. 데이터베이스 블록 스토리지.** 기존 예시인16,000IOPS/1,000MiB/s 설정을 유지하되 gp3의 보편적 최댓값이라고 부르지 않습니다. 현재 Regional gp3는 볼륨 크기·IOPS 비율과 인스턴스 제한에 따라 최대80,000IOPS·2,000MiB/s를 지원하며 Outposts 제한은 다릅니다. 예제는 구성 선택이지 벤치마크나 DB에 이 비용이 필요하다는 증거는 아닙니다.
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
StatefulSet의 `data` 클레임 템플릿은 **data-postgres-0**을 만듭니다. 이전의 사용하지 않는 `database-data` PVC를 중복 생성하거나 그 클레임을 백업하지 마세요. 안전하게 관리한 `password` 키가 있는 `postgres-secret`을 준비하며 여기에 암호 값은 제공하지 않습니다. 이미지는 마운트된 파일에서 읽고 PGDATA는 하위 디렉토리를 사용하여 볼륨 루트의 파일 시스템 메타데이터가 초기화를 방해하지 않게 합니다.
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
예제는 PostgreSQL14 계열의 확인한 현재 minor14.24를 사용합니다. Major14 지원은2026년11월12일 종료되므로 검증한 지원 버전 이전을 계획하고 프로덕션 이미지는 승인한 digest로 고정합니다. 단일 복제본은 복제·HA DB가 아니며 DB 복제 설계 없이 replicas만 늘려 해결할 수 없습니다. 명시적 PVC 보존 정책은 StatefulSet 삭제·축소 후 클레임을 남겨 데이터와 스토리지 요금이 유지될 수 있습니다.

애플리케이션 일관성을 확보하는 백업·quiesce 후 실제 DB 클레임을 스냅샷으로 만듭니다. Class는 앞서 정의한 EBS Retain snapshot class입니다:
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
**2. 공유 파일.** 정적 설정은 흔히 ConfigMap/Secret에 적합합니다. 가변 공유 파일이 필요하다면 본문의 EFS class가 별도 AP 디렉토리와 UID/GID1000을 제공합니다. 파일 시스템 ID를 바꾸고 클라이언트 경로·권한을 검증하세요. 클레임이5Gi quota를 강제하지는 않습니다.
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
아래 seed Job은 비민감 데모 설정만 쓰고 기존 파일을 보존합니다. Reader Pod 세 개가 읽기 전용으로 마운트하여 읽을 수 있는지 확인합니다. 이는 파일 전달 예제이며 실제 애플리케이션이 설정을 파싱·재로드해야 합니다. 별도 설정 없는 nginx에 `/etc/config`를 마운트해도 그 파일을 자동 사용하지 않습니다.
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
**3. 병렬 ML 데이터.** 지원 Lustre 클라이언트·커널, CSI/IAM과 파일 시스템·S3 통합을 준비합니다. SCRATCH_2 예제는 재생성 가능한 데이터용이며 persistent 전용 per-unit 처리량·자동 백업 설정을 생략합니다. `s3ImportPath`는 FSx CSI1.10.0의 유효한 파라미터이므로 소유한 접근 가능 데이터셋 버킷·접두사로 바꾸고 통합·리전 지원을 검토합니다. LZ4 기능이 실측 압축률·처리량 향상의 증거는 아닙니다.
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
1200Gi 클레임은 예시 할당이며 드라이버의 반올림·서비스 용량 선택을 확인합니다. 아래 Job은 **템플릿**입니다. `/opt/training/train.py`를 포함하고 표시한 인자를 받는 검증된 non-root GPU 이미지로 자리표시자를 바꾸며 실행 전에 데이터셋을 준비합니다. 코드는 데이터 마운트에 가려지지 않도록 이미지 안에 둡니다. Pod 네 개가 각각 GPU 네 개를 요청하면 **GPU16개**와 CPU·메모리·quota가 필요할 수 있습니다. Indexed completion은 작업 네 개를 구분할 뿐 분산 학습·gradient 동기화를 자동 구현하지 않습니다.
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
기존의 “수백GB/s”, “수백만IOPS” 집계 성능 문장은 이 작은 SCRATCH_2 예제의 실측값이 아닙니다. 이를 용량 근거로 사용하지 말고 선택한 파일 시스템·클라이언트 구성과 대표 부하로 검증합니다. 학습 작업은 실행하지 않았습니다.

**복구·모니터링·비용:** 백엔드와 파일 시스템·애플리케이션 메트릭을 명시적으로 선택하여 실제 quota·처리량·지연·사용량을 관찰하고 알려진 데이터로 복원을 테스트합니다. Retain PV·스냅샷이 백업 일정을 대신하지 않습니다. 사용하지 않는 것처럼 보이는 볼륨도 소유권·참조·검증한 복구 사본을 확인한 뒤 삭제합니다. 보안은 Pod Security admission/securityContext, 제한한 IAM, TLS와 파일 권한을 사용하며 제거된 PodSecurityPolicy는 선택지가 아닙니다. 이 청사진은 프로덕션 준비나 비용·성능 최적화를 입증하지 않습니다.

</details>

### 8. Pod를 삭제하면 볼륨 데이터도 항상 삭제되나요?

- A. Yes, every volume is deleted
- B. No, inspect its lifecycle
- C. Only if the Pod has two containers
- D. Never; all volumes are persistent

<details>
<summary>정답 보기</summary>

**정답: B. 아니요. 유형·PVC 소유권·reclaim policy에 따라 다릅니다.**

emptyDir 데이터는 Pod 수명에 종속되지만 보존된 PVC 볼륨은 Pod보다 오래 유지될 수 있습니다. Generic ephemeral PVC는 Pod가 소유할 수 있습니다. Instance store는 CSI가 PV로 제공해도 노드·매체 수명에 종속되며 실제 출시된2026년5월 EC2 Instance Store CSI add-on이 복제·영구 스토리지로 바꾸지는 않습니다.

</details>

### 9. EFS PVC의5Gi 요청이 디렉토리에5Gi quota를 강제하나요?

- A. Yes, writes fail after5Gi
- B. Yes, every access point gets a block device
- C. No, the request is binding metadata
- D. Only with directoryPerms700

<details>
<summary>정답 보기</summary>

**정답: C. 아니요. Kubernetes 용량·바인딩 메타데이터입니다.**

EFS는 저장 데이터에 따라 증가하며 클레임 크기로 디렉토리를 미리 할당하거나 제한하지 않습니다. 처리량·access point·클라이언트·보존·비용을 별도로 계획하고 quota가 필요하면 명시적인 애플리케이션·계정 제어를 사용합니다.

</details>

### 10. StorageClass에서 초기 reclaim policy를 설정하는 필드는 무엇인가요?

- A. `persistentVolumeReclaimPolicy`
- B. `reclaimPolicy`
- C. `deletionPolicy`
- D. `dataRetention`

<details>
<summary>정답 보기</summary>

**정답: B. `reclaimPolicy`**

`persistentVolumeReclaimPolicy`는 `PersistentVolume.spec`의 필드입니다. StorageClass 정책은 새 PV에 적용되며 class를 바꿔도 기존 PV 전체가 자동 변경되지 않습니다. Snapshot deletionPolicy는 또 다른 독립 수명 설정입니다.

</details>

### 11. EFS 동적 access point의 Delete는 보통 무엇을 제거하나요?

- A. Every filesystem in the VPC
- B. The entire EFS filesystem always
- C. The AP; optional root-directory cleanup
- D. No AWS resource can ever be deleted

<details>
<summary>정답 보기</summary>

**정답: C. Access point이며 디렉토리 데이터 삭제는 컨트롤러 설정에 따라 다릅니다.**

Access point provisioner가 일반적으로 EFS 파일 시스템까지 삭제하지는 않습니다. 검토한 차트의 deleteAccessPointRootDir 기본값은 false이며 활성화하면 데이터 제거 동작이 달라집니다. 클레임 삭제 전 실제 컨트롤러 값과 공유·재사용 access point 소유권을 확인합니다.

</details>

### 12. EKS의 S3 접근을 올바르게 설명한 것은 무엇인가요?

- A. No official S3 CSI driver exists
- B. The interfaces and prerequisites differ
- C. Mountpoint automatically creates new buckets
- D. All S3 mounts support all POSIX operations

<details>
<summary>정답 보기</summary>

**정답: B. S3 API, Mountpoint CSI, S3 Files는 서로 다른 인터페이스·요건을 가집니다.**

공식 Mountpoint CSI는 기존 버킷을 제한된 POSIX 파일 인터페이스로 제공합니다. S3 Files는 EFS CSI3.0+가 지원하는 별도 공유 파일 시스템 서비스이며 컨트롤러·노드 권한도 다릅니다. S3 기반 경로라고 모두 같은 연산·컴퓨팅·프로비저닝을 지원한다고 가정하지 않습니다.

</details>

### 13. WaitForFirstConsumer PVC가 정상적으로 Pending인 이유는 무엇일 수 있나요?

- A. Every CSI driver is broken
- B. No suitable scheduled consumer yet
- C. Retain prohibits binding
- D. PVC must use an empty class

<details>
<summary>정답 보기</summary>

**정답: B. 적합한 소비 Pod가 아직 스케줄링되지 않았습니다.**

지연 바인딩은 스케줄러의 토폴로지·자원 제약을 배치에 반영하므로 항상 스토리지 장애는 아닙니다. spec.nodeName은 스케줄러를 우회하여 바인딩 흐름을 막을 수 있으므로 지원되는 스케줄링 제약을 사용합니다. Class 변경이나 수동 볼륨 생성 전에 이벤트를 확인하세요.

</details>

### 14. 호환 CSI에서 Pod 하나 제약을 제공하는 접근 모드는 무엇인가요?

- A. ReadWriteOnce
- B. ReadWriteMany
- C. ReadOnlyMany
- D. ReadWriteOncePod

<details>
<summary>정답 보기</summary>

**정답: D. ReadWriteOncePod**

RWO는 읽기/쓰기 노드를 하나로 제한하며 그 노드의 여러 Pod가 사용할 수 있습니다. RWOP가 별도의 Pod 하나 모드이지만 애플리케이션 일관성·백업·권한 설계를 대체하지는 않습니다. 같은 클레임에서 RWOP와 다른 접근 모드를 혼합하지 않습니다.

</details>

### 15. 10Gi EBS 예제를 확장하고 복구를 어떻게 검증하나요?

<details>
<summary>정답 보기</summary>

**정답: 지원 확장을 허용하고 PVC 요청을 늘린 뒤 실제 용량과 별도 복원을 검증합니다.**

StorageClass allowVolumeExpansion과 드라이버·파일 시스템 지원, 적절한 애플리케이션 일관성 백업을 확인한 뒤 소유 관리 도구로 클레임을 늘립니다. 이 데모는20Gi로 확장합니다. 볼륨을 줄이거나 PV capacity 수정으로 확장을 흉내 내지 마세요:
```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```
PVC 조건·상태, 마운트된 파일 시스템과 애플리케이션 I/O를 확인합니다. 파일 시스템 확장이 대기 중이면 문서화된 재마운트·재시작 절차를 따릅니다. 새 클레임에 스냅샷을 복원하고 적절한 소비 Pod에서 알려진 데이터를 검증하세요. PVC 요청 증가나 ready 스냅샷 객체만으로 데이터 복구 테스트가 완료되지는 않습니다.

</details>

공식 참고: [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html), [Kubernetes PVs](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [gp3 specifications](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html), [PostgreSQL support](https://www.postgresql.org/support/versioning/), [S3 Files](https://docs.aws.amazon.com/eks/latest/userguide/s3files-csi.html).
