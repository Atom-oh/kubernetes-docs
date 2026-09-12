# EKS 스토리지 Part 3 퀴즈

> **마지막 업데이트**: 2026년 9월 11일

본문의 수집기·스토리지 예제로 모니터링·진단·비용·보안을 점검합니다. 아래 예제는 로컬 검사한 것이며 AWS 작업·프로덕션 복구·실제 대시보드 검증을 실행했다는 주장이 아닙니다. 배포 전에 placeholder와 리소스 소유권을 확인하세요.

## 객관식 문제

### 1. VolumeReadOps에서 읽기 IOPS를 구하는 계산은 무엇인가요?

- A. Average를 그대로 IOPS로 사용
- B. Sum을 기간 초로 나눔
- C. Byte에 Pod 수를 곱함
- D. VolumeQueueLength를 완료 IOPS로 사용

<details>
<summary>정답 및 설명</summary>

**정답: B**

Sum을 기간 초로 나눕니다. VolumeReadBytes/VolumeWriteBytes도 같은 정규화로 byte/s를 구합니다. VolumeTotalReadTime/VolumeTotalWriteTime은 누적 작업 시간이며 대응 작업 수 Sum으로 나누고0건을 처리해야 평균 초/op가 됩니다. 모든 원시 카운터를 속도·지연으로 표시하면 안 됩니다.

현재 Nitro에는 문서화된 단위·제약을 가진 VolumeAvgIOPS·VolumeAvgThroughput·평균 지연 지표도 있습니다. BurstBalance는 gp2/st1/sc1에 적용되며 gp3에는 적용되지 않습니다. EFS byte/metered-byte와 FSx OSS/OST별 지표는 차원·통계가 다릅니다. 지원되는 경우 kubelet_volume_stats_*로 파일 시스템 사용량을 볼 수 있지만 container_fs_usage_bytes는 보편적인 PVC 측정값이 아닙니다.

</details>

### 2. Pending PVC·소비자에서 먼저 확인할 것은 무엇인가요?

- A. PVC 즉시 삭제
- B. 모든 노드에 EC2 전체 권한 부여
- C. 이벤트·바인딩 모드·스케줄 제약 확인
- D. 미바인딩 PVC에 이미 AZ가 확정됐다고 가정

<details>
<summary>정답 및 설명</summary>

**정답: C**

실제 네임스페이스·클레임·소비자 이벤트·class·topology를 확인합니다. WaitForFirstConsumer는 스케줄링까지 새 PVC를 의도적으로 Pending에 둘 수 있으며 자동으로 드라이버 장애를 뜻하지 않습니다. 바인딩 후에는 EBS PV node affinity/AZ·연결 한도가 중요합니다. 바인딩에 필요한 스케줄러를 우회하는 spec.nodeName 사용을 피합니다.

```bash
set -euo pipefail
: "${NAMESPACE:?Set the workload namespace}"
: "${PVC_NAME:?Set the claim name}"
: "${POD_NAME:?Set its intended consumer Pod}"
kubectl -n "$NAMESPACE" get pvc "$PVC_NAME" -o yaml
kubectl -n "$NAMESPACE" describe pvc "$PVC_NAME"
kubectl -n "$NAMESPACE" describe pod "$POD_NAME"
kubectl get storageclass
kubectl get nodes -L topology.kubernetes.io/zone
```



```bash
set -euo pipefail
: "${CSI_CONTROLLER_POD:?Select the actual controller Pod}"
: "${CSI_CONTAINER:?Select the relevant driver/sidecar container}"
kubectl -n kube-system get pod "$CSI_CONTROLLER_POD" \
  -o jsonpath='{.spec.containers[*].name}'
kubectl -n kube-system logs "$CSI_CONTROLLER_POD" -c "$CSI_CONTAINER" --since=15m --tail=200
```

EC2 node instance profile만이 아니라 드라이버의 실제 Pod Identity/IRSA 역할·KMS grant를 확인합니다. 다중 컨테이너 컨트롤러는 관련 드라이버·sidecar 로그를 선택해야 합니다. ContainerCreating은 attach·mount·client 소프트웨어·이미지 pull·앱 권한 문제일 수 있습니다. 증상을 초기화하려고 데이터를 삭제하지 마세요.

</details>

### 3. DB 스토리지 튜닝에 적절한 접근은 무엇인가요?

- A. 측정 후 볼륨·파일 시스템·인스턴스 제약을 맞춤
- B. 항상 multiAttach:true 활성화
- C. 모든 hostPath를 빠른 NVMe로 가정
- D. 신원 확인 없이 루트 disk scheduler 변경

<details>
<summary>정답 및 설명</summary>

**정답: A**

I/O 패턴·queue·지연·인스턴스 한도를 측정한 뒤 스토리지·성능을 선택합니다. 아래10,000IOPS io2 class는 예시 할당이지 DB SLO 충족의 증거가 아닙니다:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '10000'
```

Multi-Attach는 일반적인 읽기 전용 성능 스위치가 아닙니다. Part2의 검토한 EBS CSI 경로는 io2·RWX·raw Block와 애플리케이션 조정을 사용합니다. /mnt/instance-store라는 hostPath 이름만으로 실제 instance store가 되지는 않습니다. 준비한 node-local 스토리지 설계를 사용하고 데이터를 임시 데이터로 다루세요. EC2 instance-store CSI는 별도 전제를 가진 실제 지원 통합입니다.

추측한 nvme0n1 scheduler에 noop를 쓰지 마세요. 루트·다른 디스크일 수 있고 현대 blk-mq 이름도 다릅니다. 별도 검토한 변경 전에 장치·지원 scheduler를 확인합니다. 파일 시스템·mount option도 워크로드 근거가 필요하며 XFS·ext4 어느 것도 특정 성능을 보장하지 않습니다.

</details>

### 4. 기본 gp3 class를 만들면 기존 gp2 볼륨이 이전되나요?

- A. 예, 모든 연결 볼륨이 즉시 변경
- B. 예, class 이름 변경 후
- C. 예, 기본 class가 기존 데이터도 암호화·이전
- D. 아니요, 기존 볼륨은 별도 지원 절차 필요

<details>
<summary>정답 및 설명</summary>

**정답: D**

아닙니다. StorageClass는 해당 프로비저닝을 제어하며 모든 Bound PV·백엔드를 변경하지 않습니다. 기본 class 변경은 관련 없는 신규 클레임에도 영향을 줍니다. 소유자가 지원하는 변경·데이터 이전을 선택하고 복구 지점·앱 데이터 검증을 유지하세요. 용량 확장과 축소는 다르며 PVC/EBS 크기는 일반적으로 제자리 축소할 수 없습니다.

할당 용량·프로비저닝 IOPS/처리량·보존·요청·전송 비용을 비교합니다. 컴퓨팅 할인으로 별도 스토리지 요금이 자동 감소하지는 않습니다. VolumeSnapshotClass는 schedule이 아니며 다음 예제는 의도적으로 임시인 snapshot의 삭제 동작만 정의합니다:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: temporary-ebs-snapshots
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

비용 최적화를 이유로 본문의 보존 class를 이 임시 class로 일괄 대체하지 않습니다. 백업 소유자가 예약·보존을 관리해야 하며 Velero에는 별도의 CSI snapshot 수명이 있습니다.

</details>

### 5. 스토리지 보안 제어를 올바르게 구분한 설명은 무엇인가요?

- A. PVC 이름이 암호화를 보장
- B. 각 제어에 올바른 범위·실제 리소스 매핑 필요
- C. Role로 모든 클러스터 PV 권한 부여 가능
- D. PSS가 IAM·KMS 대체

<details>
<summary>정답 및 설명</summary>

**정답: B**

IAM/KMS·네트워크·Kubernetes API 권한·admission·파일 시스템 신원은 서로 다른 작업을 보호합니다. 리전 제한 EC2 action 목록만으로 완전한 최소 권한 CSI 정책이 되지는 않습니다. 실제 드라이버 역할 정책·필요한 key grant를 사용하고 가짜 kmsKeyId가 KMS 키를 생성하지 않는다는 점도 구분합니다.

네임스페이스 Role은 PVC 권한을 줄 수 있지만 클러스터 PV 권한은 줄 수 없습니다. 이 Role로 PVC 객체를 읽지 못해도 Pod 생성자는 네임스페이스 PVC를 마운트할 수 있으므로 워크로드 생성·테넌트 경계도 보호합니다. 본문의 reader는 객체 조회 예제입니다:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: storage-auditor
  namespace: storage-demo
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pvc-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - persistentvolumeclaims
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pvc-reader
  namespace: storage-demo
subjects:
- kind: ServiceAccount
  name: storage-auditor
  namespace: storage-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pvc-reader
```

EFS SG는 가상의 securityGroupSelector 조각이 아닌 실제 mount target·client에 적용됩니다. 실제 TCP2049 경로를 사용하며 Lustre/EFA 규칙은 다릅니다. Pod Security Standards가 클라우드 암호화·IAM 권한을 구성하지는 않습니다.

</details>

### 6. 올바른 모니터링 통합 설명은 무엇인가요?

- A. Grafana ConfigMap이 PVC 지표 자동 수집
- B. Prometheus가 항상 영구 보존
- C. 수집기·discovery·권한·스토리지 구성 필요
- D. CloudWatch는 custom 지표 수신 불가

<details>
<summary>정답 및 설명</summary>

**정답: C**

CloudWatch는 서비스 native 지표, Prometheus는 설정한 Kubernetes·앱 target 수집, Grafana는 설정한 데이터소스 시각화를 담당할 수 있습니다. 수집기·Service discovery·IAM/인증·보존·레이블·알림 전달은 구성해야 합니다. 대시보드 ConfigMap만으로 누락된 지표가 생기지 않습니다.

CloudWatch도 설정한 agent·통합으로 custom/Kubernetes 지표를 받을 수 있고 Prometheus가 자동으로 내구성 있는 장기 저장소가 되지는 않습니다. 부하에 적합한 보존·스토리지/remote-write 구조를 사용합니다. 자동 관리는 무조건적인 변경이 아닌 관측·상한이 있는 제안부터 시작합니다.

</details>

### 7. 어느 관측만으로 볼륨 삭제가 승인되나요?

- A. PV가 Available
- B. 현재 조회된 Pod 참조가 없음
- C. lastUsed annotation이 오래됨
- D. 어느 것도 단독으로 승인하지 않음

<details>
<summary>정답 및 설명</summary>

**정답: D**

보존 데이터·scale-to-zero 컨트롤러·미래 Job·백업 의무·외부 소유자를 확인해야 합니다. lastUsed는 표준의 신뢰할 수 있는 PVC 사용 필드가 아닙니다. 네임스페이스/UID를 유지하고 정리 전에 백엔드 신원을 검토합니다.

</details>

### 8. kubectl top pods가 PVC 디스크 사용량을 측정하나요?

- A. 아니요, 주로 CPU·메모리 보고
- B. 예, 메모리 사용량과 디스크 사용량은 같음
- C. 예, 모든 EBS 여유 블록 표시
- D. class 이름이 gp3일 때만

<details>
<summary>정답 및 설명</summary>

**정답: A**

정확한 마운트·드라이버의 지원 파일 시스템 통계와 실제 PVC 신원을 사용합니다. 컨테이너 df가 다른 mount·공유 EFS 전체를 나타낼 수 있으며 EFS PVC 요청은 디렉터리별 quota가 아닙니다.

</details>

### 9. EFS IA/Archive 수명은 어떻게 구성하나요?

- A. Access-point StorageClass의 임의 performanceMode 파라미터
- B. 의도한 transition을 보존한 파일 시스템 lifecycle configuration
- C. PVC 요청 축소
- D. Pod 레이블을 IA로 변경

<details>
<summary>정답 및 설명</summary>

**정답: B**

EFS CSI access point 파라미터가 모든 파일 시스템 처리량·수명 속성을 구성하지는 않습니다. 배열 변경 전에 기존 정책을 읽고 빈 배열은 lifecycle 관리 비활성화임을 구분합니다. 예측하기 어려운 수요에는 Elastic이 권장 시작점이며 Archive 지원·transition 순서에는 별도 조건이 있습니다.

</details>

### 10. aws s3 cp --sse AES256가 선택하는 것은 무엇인가요?

- A. TLS 프로토콜 버전
- B. NetworkPolicy 암호화
- C. 저장 데이터의 SSE-S3 암호화
- D. EFS mount 암호화

<details>
<summary>정답 및 설명</summary>

**정답: C**

전송은 HTTPS/TLS가 보호하며 --sse가 이를 켜지 않습니다. 적절한 endpoint·인증서 검증을 사용합니다. FSx scratch는 서비스 관리 키로 암호화되며 선택 가능한 customer key는 persistent 파일 시스템의 선택지입니다.

</details>

## 단답형 문제

### 11. 속도 계산과 용량 예측을 어떻게 검증하나요?

<details>
<summary>정답 및 설명</summary>

**정답: 단위·기간·누락 데이터·대표 시나리오를 확인합니다**

300초 구간의 완료 읽기30,000건은100 read IOPS입니다. 누적 읽기1,500초를30,000건으로 나누면0.05초/op, 즉50ms입니다. 겹친 작업 때문에 누적 시간이 실제 경과 시간보다 클 수 있습니다. 기간을 맞추고0건·누락을 구분합니다.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the volume Region}"
: "${EBS_VOLUME_ID:?Set the verified owned EBS volume ID}"
read -r START_TIME END_TIME < <(python3 - <<'PY'
import datetime, time
end = int(time.time()) // 300 * 300
fmt = lambda value: datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(fmt(end - 3600), fmt(end))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --namespace AWS/EBS --metric-name VolumeReadOps \
  --dimensions "Name=VolumeId,Value=$EBS_VOLUME_ID" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --period 300 --statistics Sum --output json > ebs-read-ops.json
python3 - ebs-read-ops.json <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    points = json.load(stream)["Datapoints"]
for point in sorted(points, key=lambda p: p["Timestamp"]):
    print(point["Timestamp"], "read IOPS:", point["Sum"] / 300)
if not points:
    print("No datapoints: check dimensions, attachment/activity, Region and publication delay")
PY
```

실측 부하 결과가 아닌 산술 예시입니다. predict_linear에는 counter가 아닌 gauge를 사용하고 중복 scrape·잘못된 용량을 처리합니다. 최근 추세가 미래 고갈의 보장은 아닙니다. 본문 규칙은 합성 데이터로 지속 높은 사용량·중복 target·용량0·누락·증가 추세를 검사했습니다.

</details>

### 12. CSI 신원·Multi-Attach·node-local 스토리지는 어떻게 다른가요?

<details>
<summary>정답 및 설명</summary>

**정답: 각각 권한·연결·배치 문제를 다룹니다**

CSI controller 신원은 백엔드 수명 API 권한이며 모든 앱의 신원이 아닙니다. EBS Multi-Attach는 서비스·드라이버·AZ 제약 아래 공유 raw 장치 연결을 제공하며 앱의 쓰기 조정·fencing이 필요합니다. 임의 multiAttach StorageClass 필드는 지원 스위치가 아닙니다.

Node-local instance store는 노드 수명에 연결되며 올바른 장치 준비·스케줄링이 필요합니다. HostPath 문자열만으로 실제 장치·내구성이 입증되지는 않습니다. 성능 예제를 실행하려고 특권을 부여하거나 추측한 disk를 포맷하지 말고 검토한 CSI 경로를 사용합니다.

</details>

### 13. Admission과 EKS 감사 로그가 입증할 수 있는 것은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

**정답: 설정한 요청 범위와 기록된 이벤트에 한정됩니다**

본문의 Kyverno policies.kyverno.io/v1 ValidatingPolicy는 일치하는 EBS StorageClass의 선언된 encrypted 파라미터를 검사합니다. 기존 AWS 볼륨·정적 PV 내용·모든 우회 경로를 검사하지는 않습니다. Admission 외에도 관리자 권한을 제한하고 실제 백엔드 암호화를 확인합니다.

EKS가 제어 영역 audit policy를 관리합니다. 클러스터 소유자를 통해 지원 audit log 유형을 활성화하고 전달된 기록을 조회합니다. 붙여 넣은 audit.k8s.io 정책 조각은 관리형 정책 교체용 EKS API가 아닙니다. Kubernetes audit·CloudTrail 백엔드 API 이벤트는 보존·권한·범위가 다른 보완 자료이며 로깅 자체가 데이터 손실을 방지하지는 않습니다.

</details>

## 실습 문제

### 14. 검토 가능한 모니터링·대시보드 구성을 작성하세요.

<details>
<summary>정답 및 설명</summary>

**정답: 각 의존성을 명시적으로 구성합니다**

본문의 검토한 stack·수집기를 사용하며 ConfigMap만으로 agent가 설치된다고 가정하지 않습니다. 전통적인 CloudWatch agent 설치는 실제 네임스페이스·워크로드·신원을 확인하고 선택한 통합·컴퓨팅 지원에 맞게 다음 이름을 조정합니다:

```bash
set -euo pipefail
kubectl -n amazon-cloudwatch get daemonsets,pods
kubectl -n amazon-cloudwatch get serviceaccount cloudwatch-agent -o yaml
```

[클러스터 모니터링 예제](../../eks/02-eks-cluster-creation-part3.md)의 소유자 관리 agent/add-on 전제를 따릅니다. StatsD receiver가 EBS/PVC 지표를 자동 생성하지는 않습니다. 대시보드 누락을 메우려고 정적 AWS 키·중복 agent를 추가하지 마세요.

EBS CSI의 지원 metrics 설정은 기존 소유자를 통해 활성화합니다. 본문의 생성 monitor **또는** 기존 Service가 있는 경우 아래 독립 monitor를 사용하여 중복 수집을 피합니다. Prometheus가 monitor 네임스페이스·레이블을 선택하고 Service의 이름 있는 port에 도달해야 합니다:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: csi-metrics-reviewed
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
    - kube-system
  selector:
    matchLabels:
      app: ebs-csi-controller
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

모니터링 소유자를 통해 본문의 recording/alert rule을 설치한 뒤 target Up·예상 series·알림 전달을 확인합니다. EBS driver endpoint는 CSI 작업 지표를 보고하며 모든 sidecar·원시 파일 시스템 사용량을 포함하지는 않습니다.

다음 ConfigMap은 해당 import/provisioning 경로를 지원하는 배포용 **Classic dashboard model**입니다. 현재 Grafana에는 V1 Resource·기본 V2 Resource 모델도 있으므로 resource envelope를 기대하는 다른 API에 이 Classic 객체를 그대로 전송하지 않습니다. Prometheus data-source UID를 교체하고 본문 recording rule·Grafana sidecar 레이블/네임스페이스 설정을 확인합니다. 채택 전에 대상 Grafana 버전에서 export/import를 검증하세요:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: storage-dashboard-reviewed
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  storage-dashboard.json: |
    {
      "id": null,
      "uid": "eks-storage-reviewed",
      "title": "EKS Storage: PVC Filesystem Usage",
      "tags": [
        "storage"
      ],
      "timezone": "browser",
      "schemaVersion": 42,
      "version": 1,
      "refresh": "30s",
      "time": {
        "from": "now-6h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "type": "timeseries",
          "title": "PVC filesystem utilization",
          "gridPos": {
            "x": 0,
            "y": 0,
            "w": 24,
            "h": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "(pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max) and (pvc:storage_capacity_bytes:max > 0)",
              "legendFormat": "{{cluster}} {{namespace}}/{{persistentvolumeclaim}}"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percentunit",
              "min": 0,
              "max": 1
            },
            "overrides": []
          }
        }
      ]
    }
```

Native EBS IOPS·EFS 처리량 패널을 추가하려면 검토한 IAM 권한의 CloudWatch 데이터소스와 본문의 차원·기간 정규화 계산을 사용합니다. 설정한 exporter가 해당 이름·의미를 실제 게시하지 않는다면 aws_ebs_* Prometheus series를 가정하지 마세요. 여기의 JSON·표현식은 로컬 검사했으며 인증된 Grafana import·실제 AWS 질의는 수행하지 않았습니다.

</details>

### 15. 위험한 정리 가정 없이 스토리지 조사 보고서를 만드세요.

<details>
<summary>정답 및 설명</summary>

**정답: 근거를 보고하고 삭제 가능성을 추정하지 않습니다**

이전 placeholder CronJob을 읽기 전용 보고서로 대체합니다. 아래 스크립트는 네임스페이스·UID·직접 Pod 참조를 유지하고 삭제를 승인하지 않습니다. lastUsed로 나이를 추정하거나 Bound를 미사용으로 간주하거나 전체 네임스페이스 결과에서 네임스페이스를 버리지 않습니다.

```python
"""Report direct Pod/PVC references; never infer deletion eligibility."""
import json,sys
def inventory(namespace,claims,pods):
    refs={}
    for pod in pods['items']:
        meta=pod['metadata']
        if meta['namespace']!=namespace:raise ValueError('Pod list contains another namespace')
        seen=set()
        for volume in pod.get('spec',{}).get('volumes',[]):
            claim=volume.get('persistentVolumeClaim',{}).get('claimName')
            if claim and claim not in seen:
                seen.add(claim)
                refs.setdefault(claim,[]).append({'pod':meta['name'],'podUID':meta['uid'],'phase':pod.get('status',{}).get('phase','Unknown')})
    rows=[]
    for pvc in claims['items']:
        meta,spec=pvc['metadata'],pvc.get('spec',{})
        if meta['namespace']!=namespace:raise ValueError('PVC list contains another namespace')
        rows.append({'namespace':namespace,'name':meta['name'],'uid':meta['uid'],
          'phase':pvc.get('status',{}).get('phase','Unknown'),'volumeName':spec.get('volumeName'),
          'storageClassName':spec.get('storageClassName'),'requestedStorage':spec.get('resources',{}).get('requests',{}).get('storage'),
          'directPodReferences':refs.get(meta['name'],[]),'ownerReferences':meta.get('ownerReferences',[]),
          'deletionAuthorized':False,'nextAction':'Review owner, controller templates, retention, backups and actual backend before any change'})
    return {'reviewOnly':True,'namespace':namespace,'rows':sorted(rows,key=lambda x:x['name']),
      'limitations':['The two API reads are not an atomic snapshot.','No Pod reference does not mean unused: scale-to-zero controllers, future Jobs, retained data and indirect/ephemeral references need separate review.','lastUsed is not a standard trustworthy Kubernetes PVC field. This report never authorizes snapshot creation or deletion.']}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: storage-inventory.py namespace pvcs.json pods.json')
    with open(sys.argv[2]) as f:claims=json.load(f)
    with open(sys.argv[3]) as f:pods=json.load(f)
    print(json.dumps(inventory(sys.argv[1],claims,pods),indent=2))
```



```bash
set -euo pipefail
: "${STORAGE_NAMESPACE:?Set the namespace being reviewed}"
kubectl -n "$STORAGE_NAMESPACE" get pvc -o json > inventory-pvcs.json
kubectl -n "$STORAGE_NAMESPACE" get pods -o json > inventory-pods.json
python3 storage-inventory.py "$STORAGE_NAMESPACE" inventory-pvcs.json inventory-pods.json
```

조회 신원에는 해당 네임스페이스 읽기 권한만 필요합니다. 아래 Role은 범위 예제이며 필요하면 검토한 운영자·자동화 신원에 바인딩합니다. Snapshot 생성·확장·삭제 권한은 부여하지 않습니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: storage-inventory-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - persistentvolumeclaims
  verbs:
  - get
  - list
```

Scale-to-zero controller template·Job/CronJob·보존 클레임·간접/ephemeral 참조·백업 정책·실제 백엔드 ID를 별도로 검토합니다. 현재 Pod 참조가 없다는 것은 삭제 결정이 아닙니다. 나중에 이 보고서를 예약한다면 스크립트·client가 포함된 실제 검토 이미지, 실행 상한·제한된 신원·정의된 보고서 목적지를 사용합니다. storage-tools:latest·생략 부호 명령은 구현이 아닙니다.

관측부터 자동화하고 상한이 있는 변경 제안·독립 검증한 복구로 확장합니다. EBS/PVC 증가는 임의 축소와 다릅니다. 리소스를 조용히 파괴하는 스크립트 대신 배포에 적절한 감사 근거·수명 소유권·승인/운영 제어를 유지합니다.

</details>

## 답변 점검

객관식10개를 포함한15문항입니다. 오답으로 다시 볼 주제를 찾고 점수만으로 프로덕션 전문성을 판단하지 않습니다. 실습 답변은 문법뿐 아니라 전제·리소스 범위·검증 근거도 평가하세요.

## 참고 자료

- [본문](../../eks/04-eks-storage-part3.md)
- [EBS metrics](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [FSx metrics](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [EFS lifecycle API](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [EKS auditing](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)
- [Grafana dashboard models](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)
