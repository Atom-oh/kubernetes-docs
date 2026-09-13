# Amazon EKS 스토리지 - Part 3: 모니터링, 문제 해결, 비용 최적화, 보안

> **마지막 업데이트**: 2026년 9월 11일

이 문서는 Amazon EKS 스토리지 시리즈의 세 번째이자 마지막 부분으로, 스토리지 모니터링, 문제 해결, 비용 최적화 및 보안에 대해 다룹니다.

## 목차

1. [스토리지 모니터링](#스토리지-모니터링)
2. [스토리지 문제 해결](#스토리지-문제-해결)
3. [스토리지 비용 최적화](#스토리지-비용-최적화)
4. [스토리지 보안](#스토리지-보안)
5. [스토리지 관리 모범 사례](#스토리지-관리-모범-사례)

## 스토리지 모니터링

백엔드·Kubernetes·애플리케이션 관측을 함께 사용합니다. 백엔드 I/O 카운터는 파일 시스템 여유 공간을 측정하지 않으며 Kubernetes readiness가 DB 일관성을 입증하지도 않습니다. 경보를 만들기 전에 단위·차원·집계 기간·데이터 누락 동작을 기록하세요.

<!-- Diagram repair pending: ServiceMonitor configures Prometheus discovery; node-exporter is not a PVC usage exporter.
![AWS CloudWatch, Kubernetes 모니터링, 사용자 정의 솔루션 세 영역으로 나뉘어 EBS·EFS·FSx 지표가 주요 모니터링 지표를 거쳐 CloudWatch 경보와 대시보드로 이어지고, Prometheus가 ServiceMonitor/PodMonitor와 알림 규칙을 통해 Grafana로 연결되며, 볼륨 사용량 익스포터가 사용자 정의 지표·알림을 만드는 EKS 스토리지 모니터링 구조를 보여주는 다이어그램.](../.gitbook/assets/ko-eks-04-eks-storage-part3-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-04-eks-storage-part3-0.html)
-->

### CloudWatch를 사용한 모니터링

EBS/EFS/FSx는 Kubernetes exporter 없이 서비스 지표를 게시합니다. CloudWatch 조회·시각화에는 적절한 IAM 권한이 필요합니다. get-dashboard는 이미 존재하는 대시보드 정의를 가져오며 대시보드 생성·지표 활성화 명령이 아닙니다.

#### EBS 볼륨 지표

| 지표 | 올바른 해석 |
|---|---|
| VolumeReadBytes / VolumeWriteBytes | Sum은 선택 기간 전송 byte이며 기간 초로 나누면 byte/s |
| VolumeReadOps / VolumeWriteOps | Sum은 완료 작업 수이며 기간 초로 나누면 IOPS |
| VolumeTotalReadTime / VolumeTotalWriteTime | Sum은 누적 작업 시간(초); 대응 작업 수 Sum으로 나누면 평균 초/op, 작업0건은 별도 처리 |
| VolumeQueueLength | 대기 I/O gauge; Average/Maximum으로 지속 queue·peak 구분 |
| BurstBalance | gp2·st1·sc1의 남은 credit이며 gp3 credit 지표가 아님 |

지원 Nitro 연결에는 현재 VolumeAvgIOPS(Ops/s), VolumeAvgThroughput(KiB/s), VolumeAvgReadLatency/VolumeAvgWriteLatency(ms)와 exceeded/stalled-I/O 지표도 있습니다. 각각 Multi-Attach·컴퓨팅·zone 제약을 확인하세요. 일반 볼륨 지표는 연결된 볼륨에 게시되며 누락이 자동으로 사용량0을 의미하지 않습니다. 작업이 겹치면 기존 누적 시간 카운터가 실제 경과 기간보다 클 수 있습니다.

#### EFS 파일 시스템 지표

TotalIOBytes·DataReadIOBytes·DataWriteIOBytes·MetadataIOBytes는 이미 정규화된 전송률이 아니라 byte 지표입니다. 적절한 Sum을 기간으로 나누어 byte/s를 구합니다. MeteredIOBytes는 읽기 할인 등을 반영한 EFS 처리량 계량값이며 원시 전송 byte와 같지 않습니다. PermittedThroughput은 속도 지표입니다. 기간·단위를 맞추고 필요에 따라 ClientConnections·모드에 맞는 PercentIOLimit·스토리지 class를 모니터링합니다. BurstCreditBalance는 Bursting 처리량에 적용되며 Elastic에는 적용되지 않습니다.

#### FSx for Lustre 지표

DataReadBytes/DataWriteBytes·DataReadOperations/DataWriteOperations는 FileSystemId를 사용하며 Sum/기간으로 처리량·작업/s를 구합니다. **NetworkThroughputUtilization은 유효한 지표**이며 OSS별 FileSystemId·FileServer 차원의 사용률(%)입니다. FreeDataStorageCapacity는 FileSystemId·StorageTargetId의 OST별 지표입니다. Target 불균형과 같은 시점의 용량 gauge를 확인하며 gauge를 시간축으로 합산해 현재 여유 용량처럼 해석하지 않습니다.

LogicalDiskUsage·PhysicalDiskUsage도 유효하며 압축 전 논리 byte와 압축 후 물리 byte를 설명합니다. 파일 시스템 집계로 압축 효과를 평가할 수 있지만 프로비저닝 용량 요금이 사용량만의 요금으로 바뀌지는 않습니다.

### Prometheus 및 Grafana를 사용한 모니터링

모니터링 소유자의 기존 stack을 재사용합니다. 신규 설치를 검토한다면 배포된 kube-prometheus-stack90.1.1/operator0.93.1은 검증한 참고 조합이지 기존 클러스터의 자동 업그레이드 지시가 아닙니다. 다음은 매니페스트만 렌더링합니다. admin-user/admin-password 키를 가진 `monitoring/grafana-admin`과 본문의 확장 가능한 ebs-gp3 class를 준비합니다. 실제 클러스터 버전·스토리지 크기·보존 기간으로 조정하세요. 알림 전달·Grafana 영속성·가용성·kubelet TLS/인증 기본값은 배포별 검토가 필요합니다:

```yaml
grafana:
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
prometheus:
  prometheusSpec:
    retention: 14d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ebs-gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 20Gi
```



```bash
set -euo pipefail
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm template prometheus prometheus-community/kube-prometheus-stack \
  --version 90.1.1 --namespace monitoring --kube-version 1.36.0 \
  --include-crds -f monitoring-values.yaml > monitoring-review.yaml
```

ServiceMonitor는 **Service**와 그 endpoint를 선택하며 namespaceSelector와 Prometheus 인스턴스의 ServiceMonitor selector가 모두 맞아야 합니다. EBS CSI1.66 Helm chart의 controller.enableMetrics 기본값은 false입니다. 해당 chart로 관리하는 설치는 기존 소유자와 다음 값을 검토합니다. 드라이버3301 endpoint·sidecar metrics Service·생성되는 ServiceMonitor를 활성화하며 release 레이블을 실제 Prometheus selector와 맞춥니다:

```yaml
controller:
  enableMetrics: true
  serviceMonitor:
    labels:
      release: prometheus
```

EKS 관리형 add-on은 다른 설정 옵션을 노출할 수 있습니다. Helm values를 그대로 적용하지 말고 버전·configuration·실제 리소스를 확인합니다. 아래 독립 ServiceMonitor는 소유자가 표시한 Service를 이미 노출하고 대응 monitor를 생성하지 않았을 때의 **대안**입니다. 같은 생성 monitor와 함께 배포하지 않습니다:

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



```bash
set -euo pipefail
kubectl -n kube-system get svc ebs-csi-controller -o yaml
kubectl -n kube-system get endpointslice \
  -l kubernetes.io/service-name=ebs-csi-controller -o wide
kubectl -n monitoring get prometheus -o yaml
```

선택한 target의 Up 상태와 실제 지표를 확인합니다. 드라이버·provisioner/attacher/resizer/snapshotter는 별도 endpoint를 가지므로 드라이버 Service 하나가 모든 sidecar를 수집하지는 않습니다. CSI API 작업 지연과 애플리케이션/EBS 데이터 I/O 지연도 구분합니다.

### 파일 시스템 사용량과 알림

CSI 드라이버가 필요한 volume 통계를 구현한 경우 인증된 kubelet의 kubelet_volume_stats_*를 사용합니다. kube-state-metrics는 객체 상태·요청 정보, node-exporter는 host 파일 시스템 지표를 제공합니다. node-exporter DaemonSet을 하나 더 설치해도 PVC별 사용량 지표가 생기지 않습니다. kube-prometheus-stack에는 node-exporter 옵션이 이미 있으므로 host mount·특권을 중복하지 마세요.

Raw block과 통계를 지원하지 않는 드라이버는 파일 시스템 용량을 게시하지 않을 수 있습니다. EFS access point/PVC 요청은 디렉터리별 quota가 아니며 보고된 용량이 공유 파일 시스템을 가리킬 수 있습니다. container_fs_usage_bytes도 보편적 PVC 측정값이 아닙니다. 수집기·마운트·네임스페이스/클레임 매핑을 확인하고 누락 지표를 별도로 처리합니다.

다음 규칙은 같은 클레임의 중복 scrape를 합산하지 않고 max로 제거합니다. Federation 데이터에는 신뢰할 수 있는 cluster 레이블이 필요합니다. 용량0 series는 제외합니다. 예측은 gauge·최근 추세를 사용하며 조치 전에 scrape 누락·클레임 재생성/확장·워크로드 변화를 검토합니다. 읽기 전용·정적 데이터셋처럼 호출 경보 대상이 아닌 클레임에는 selector를 조정하세요:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: storage-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: storage-reviewed
    rules:
    - record: pvc:storage_used_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes)
    - record: pvc:storage_capacity_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_capacity_bytes)
    - alert: VolumeUsageHigh
      expr: (pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max > 0.85) and
        (pvc:storage_capacity_bytes:max > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Volume usage high ({{ $value | humanizePercentage }})
        description: PVC {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim
          }} requires capacity review.
    - alert: VolumeMayFillIn24Hours
      expr: (predict_linear(pvc:storage_used_bytes:max[6h], 86400) > pvc:storage_capacity_bytes:max)
        and (pvc:storage_capacity_bytes:max > 0) and (delta(pvc:storage_used_bytes:max[1h])
        > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Recent trend projects capacity exhaustion
        description: Review the trend and workload for PVC {{ $labels.namespace }}/{{
          $labels.persistentvolumeclaim }}; this is not a guarantee.
```

네임스페이스·release 레이블이 Prometheus rule selector와 맞아야 합니다. 규칙 문법·합성 시나리오를 검증한 뒤 대상 배포의 실제 지표 범위·알림 전달을 확인합니다. 이번 검토에서 실제 지표 수집·알림 전달을 실행하지 않았습니다.

## 스토리지 문제 해결

객체 신원·이벤트부터 확인합니다. Pending·ContainerCreating·느린 I/O는 원인이 다를 수 있으며 이미지 pull·스케줄링·앱 readiness가 반드시 스토리지 장애인 것은 아닙니다. 그림은 초기 분류 안내이지 모든 증상을 특정 원인에 대응시키는 표가 아닙니다.

![PVC Pending·볼륨 프로비저닝 실패·볼륨 마운트 문제·성능 문제 네 가지 증상이 각각 어떤 진단 지점을 거쳐 어떤 해결 조치로 이어지는지 두 그룹으로 나누어 보여주는 다이어그램. CSI 드라이버 로그·IAM 권한·스토리지 클래스 확인은 두 프로비저닝 문제가, 노드 상태 확인은 마운트·성능 문제가 공유한다.](../.gitbook/assets/ko-eks-04-eks-storage-part3-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-04-eks-storage-part3-1.html)

### 프로비저닝과 WaitForFirstConsumer

실제 워크로드 네임스페이스·클레임·대상 소비자를 사용합니다. 추측으로 광범위한 권한을 부여하지 말고 참조 class·컨트롤러 이벤트·드라이버 신원/KMS 권한·quota·노드 연결 한도를 확인합니다:

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

WaitForFirstConsumer는 스케줄 가능한 소비자가 topology를 결정할 때까지 새 PVC를 의도적으로 Pending으로 둡니다. 아직 바인딩되지 않은 새 PVC에는 노드풀을 이동시켜야 할 AZ가 이미 정해진 것이 아닙니다. Pod selector·affinity·taint·리소스·스토리지 topology를 확인하세요. spec.nodeName으로 스케줄러를 우회하면 이 바인딩이 진행되지 않을 수 있으므로 지원 스케줄 제약을 사용합니다. 바인딩 후에는 EBS PV의 AZ·node affinity가 중요합니다. Pending을 지우려고 클레임을 삭제하거나 PV capacity를 편집하지 않습니다.

### 마운트 실패

Attach 오류·node publish/mount 오류·파일 시스템 client 누락·신원/권한 오류·애플리케이션 권한을 구분합니다. 로그는 관련 CSI 드라이버/sidecar 컨테이너를 선택하며 다중 컨테이너 Pod의 기본 로그가 모든 구성 요소를 포함하지는 않습니다. 필요하면 VolumeAttachment·바인딩 PV의 driver/handle·배정된 노드를 확인합니다.

노드 로그는 소유자가 지원하는 접근·진단 경로를 사용합니다. Bottlerocket·Auto Mode·다른 관리형 컴퓨팅에서 ec2-user SSH·journalctl이 보편적인 방법은 아닙니다. 특권 amazonlinux:2 helper가 올바른 CSI/client 설정을 대체하지 않으며 AL2의2026년 OS 지원은 종료되었습니다. 별도 승인된 노드 수동 마운트 전에 본문의 지원 CSI 소비자 테스트·이벤트를 사용합니다.

EFS는 실제 mount client에서 mount target·DNS·TCP2049를 확인합니다. Lustre는 TCP988·1018–1023과 서비스의 client/server 규칙이 필요하고 EFA에는 추가 SG 참조 조건이 있습니다. NACL 반환 트래픽·route도 확인하세요. ICMP ping 실패가 NFS 불가의 증거는 아니며 AWS CLI 컨테이너에 ping·telnet·mount helper가 있다고 보장되지 않습니다. Pod 네트워크 테스트는 노드 CSI 마운트와 출발지·SG가 다를 수 있습니다.

### 느린 I/O

측정한 작업 크기·queue·앱 동시성·프로비저닝 성능·인스턴스 EBS 한도·초기화 상태를 확인합니다. 다음 이식 가능한 Python 시간 계산은 완료된5분 구간을 사용합니다. VolumeReadOps의 Sum/300이 읽기 IOPS이며 Average를 그대로 속도로 해석하지 않습니다:

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

파일 시스템 쓰기 테스트는 검증한 마운트의 승인된 폐기 가능 디렉터리를 사용합니다. 의도한 테스트 환경에 다음 스크립트를 저장하세요. 고유64MiB 파일을 만들고 자신의 파일·디렉터리만 정리합니다. 읽기는 캐시에 적중할 수 있으므로 이 시간만으로 cold storage 성능을 입증하지 않습니다. 운영 데이터에 고정 `/data/test` 덮어쓰기·raw 장치0 쓰기를 실행하지 마세요:

```bash
set -euo pipefail
: "${STORAGE_TEST_DIR:?Set an approved disposable directory on the verified disposable filesystem mount}"
test -d "$STORAGE_TEST_DIR" && test -w "$STORAGE_TEST_DIR"
STORAGE_TEST_PATH=$(mktemp -d "$STORAGE_TEST_DIR/storage-test.XXXXXX")
cleanup() { rm -f -- "$STORAGE_TEST_PATH/payload"; rmdir -- "$STORAGE_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$STORAGE_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$STORAGE_TEST_PATH/payload" of=/dev/null bs=1M
```

이번 검토에서는 스토리지 벤치마크를 실행하지 않았습니다. 단편화는 근거가 필요한 가설로 다루며 파일 시스템 재생성·포맷은 일반적인 첫 해결책이 아니라 데이터 이전입니다. 추측한 nvme0n1의 I/O scheduler를 바꾸지 마세요. 다른 볼륨·루트 장치일 수 있고 현대 blk-mq scheduler의 이름·지원도 다릅니다.

EFS는 General Purpose·실제 처리량 모드·client 한도·메타데이터 요구·동시성이 중요합니다. Part2의 hard/TLS·적절한 timeout/retry를 포함한 지원 mount-helper 옵션을 사용합니다. 파일 묶음·순차 접근 증가가 측정한 부하에는 도움이 될 수 있지만 앱 데이터 배치 변경이 항상 이로운 것은 아닙니다.

## 스토리지 비용 최적화

지연·내구성·복구·소유권 요구를 유지하면서 전체 워크로드 비용을 최적화합니다. 컴퓨팅 할인·할당 스토리지·프로비저닝 성능·요청/전송 요금·보존 백업은 별도 비용입니다.

<!-- Diagram repair pending: align each storage service with its actual optimization strategy; do not map S3 to FSx optimization or FSx to EFS optimization.
![EBS, EFS, FSx for Lustre, S3 네 가지 스토리지 유형이 볼륨 최적화, 수명 주기 관리, EFS 최적화, FSx 최적화 전략을 거쳐 Cost Explorer·Kubernetes 비용 할당·이상 탐지로 이루어진 비용 모니터링으로 수렴하는 구조를 보여주는 다이어그램.](../.gitbook/assets/ko-eks-04-eks-storage-part3-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-04-eks-storage-part3-2.html)
-->

### 볼륨 유형·크기·이전

실제 gp2 비용·성능과 gp3를 비교하고 HDD는 적합한 접근 패턴에만 고려합니다. 임의 최대 크기가 아닌 측정한 여유·경보를 준비합니다. EBS/PVC 용량은 일반적으로 확장하며 축소하지 않으므로 할당 용량 감소에는 더 작은 새 볼륨으로의 지원 이전·데이터 검증이 필요합니다.

gp3 StorageClass 생성·기본 class 지정은 **기존 gp2 볼륨을 이전하지 않습니다**. 기본 class 변경은 관련 없는 신규 클레임에도 영향을 줍니다. Part1의 명시적 class를 재사용하세요. 기존 볼륨은 배포 드라이버가 지원하는 변경 절차나 새 클레임으로의 검증한 백업/복원을 선택하고 스토리지 변경 전에 소유권·앱 일관성·되돌리기를 확인합니다.

### 수명과 보존

VolumeSnapshotClass는 드라이버·보존 동작을 정의하며 스냅샷 예약·나이별 삭제를 수행하지 않습니다. 백업 소유자의 schedule·보존 정책을 사용하세요. Part2는 원래 class가 Retain이어도 삭제될 수 있는 Velero CSI snapshot 수명을 설명합니다.

PV가 Available·Released라고 자동으로 폐기 가능하지 않으며 Bound도 실제 사용의 증거는 아닙니다. 정리 전에 claimRef/UID·워크로드 소유자·snapshot·보존 의무·실제 백엔드를 조사합니다. Retain은 과금 리소스를 남길 수 있고 Delete 동작은 드라이버에 따라 다릅니다. EFS access point 삭제와 파일 시스템·데이터 삭제는 다릅니다. S3/Archive 계층화에도 앱과 호환되는 복구·접근 계획이 필요합니다.

### EFS 비용 최적화

AWS는 예측하기 어려운·급증하는 워크로드에 Elastic 처리량을 권장합니다. 실제 metered I/O·현재 요금으로 지속 수요의 Provisioned, 용량/credit 모델의 Bursting과 비교합니다. 권장 성능 모드는 General Purpose입니다. Access point는 별도 POSIX 신원으로 파일 시스템을 공유하지만 PVC별 용량 예약·자동 앱별 과금은 제공하지 않습니다.

변경 제안 전에 기존 lifecycle configuration 전체를 조회합니다:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the filesystem Region}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned filesystem ID}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --output json > efs-filesystem-review.json
aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
  --file-system-id "$EFS_FILE_SYSTEM_ID" --output json > efs-lifecycle-before.json
```

put-lifecycle-configuration은 파일 시스템 구성을 변경하므로 의도한 기존 transition을 검토한 배열에 모두 보존합니다. 빈 배열은 lifecycle 관리를 비활성화하며 각 policy 객체는 transition 하나를 포함합니다. Archive는 지원 General Purpose/Elastic 구성과 IA보다 나중의 transition이 필요합니다. IA/Archive 접근·최소 보관 기간 요금도 분석하고 기존 정책을 단일30일 예제로 무조건 덮어쓰지 않습니다.

### FSx for Lustre와 비용 할당

Scratch는 재생성 가능한 데이터에만 선택하고 필요한 수명에는 persistent 배포·스토리지를 사용합니다. LZ4가 물리 데이터 크기를 줄일 수 있어도 이미 프로비저닝한 SSD 할당 요금이 자동으로 줄지는 않습니다. 선택한 요금 모델·압축률·처리량/CPU 영향을 평가하세요. S3 repository 통합은 버킷 이름만이 아닌 import/export/release 동작 구성이 필요합니다.

Cost Explorer·Kubernetes 비용 도구에는 과금 데이터 설정·필요한 비용 할당 tag 활성화·PVC/PV와 클라우드 ID의 검증한 매핑이 필요합니다. 네임스페이스 레이블만으로 모든 AWS 요금에 tag가 자동 부여되지는 않습니다. 보존 볼륨·snapshot·요청/전송·관측 데이터 보존 비용을 추적합니다. EC2 Reserved Instance/Compute Savings Plans는 적격 컴퓨팅 비용에 영향을 주며 별도 EBS/EFS/FSx 스토리지 요금을 자동으로 낮추지는 않습니다.

## 스토리지 보안

백엔드·노드/마운트 경로·Kubernetes 제어 영역을 각각 보호합니다. Class 이름·네임스페이스 정책·컨테이너 루트의 읽기 전용 설정만으로 쓰기 가능한 PVC의 내용이 보호되지는 않습니다.

<!-- Diagram repair pending: TLS, at-rest key management, IAM, network rules, RBAC and admission are distinct controls; neither RBAC nor PSS proves backend encryption.
![EBS·FSx, EFS, S3 스토리지 서비스의 보안 설정이 저장·전송 데이터 암호화를 거쳐 AWS KMS 키 관리로 모이고, 보안 그룹과 IAM 역할이 Kubernetes RBAC을 통해 OPA Gatekeeper/Kyverno 정책 적용으로 이어지며, 파드 보안 컨텍스트는 Pod Security Standards로 강제되는 구조를 보여주는 다이어그램.](../.gitbook/assets/ko-eks-04-eks-storage-part3-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-04-eks-storage-part3-3.html)
-->

### 데이터 암호화

EBS 암호화는 볼륨 프로비저닝 때 요청하며 StorageClass 변경으로 기존 볼륨이 소급 암호화되지는 않습니다. 아래 신규 class는 암호화된 gp3·지연 topology 바인딩·명시적 보존을 요청합니다. Customer managed key가 필요하면 실제 검토한 kmsKeyId와 key policy·드라이버 grant를 준비하세요. 예시 ARN은 동작하는 키가 아닙니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

EFS 암호화는 Part1의 검사를 포함한 인프라 절차로 파일 시스템 생성 때 설정합니다. 기존 비암호화 데이터는 mount option이 아닌 암호화 파일 시스템으로의 지원 이전 절차가 필요합니다. FSx for Lustre는 저장 데이터를 자동 암호화합니다. Scratch는 서비스 관리 키를 사용하며 선택 가능한 AWS managed/customer managed KMS 키는 **persistent 파일 시스템**의 선택지입니다. SCRATCH_2 예제에 customer kms-key-id를 전달하지 마세요.

EBS ID를 바인딩된 PV volumeHandle과 맞추고 계정·리전을 확인하여 실제 클라우드 리소스를 조회합니다. Scratch FSx 응답에 선택한 customer key가 없다고 비암호화된 것은 아닙니다:

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resources Region}"
: "${EBS_VOLUME_ID:?Identify the actual volume from its bound PV}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned EFS filesystem ID}"
: "${FSX_FILE_SYSTEM_ID:?Set the owned FSx filesystem ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[0].{Id:VolumeId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Type:LustreConfiguration.DeploymentType,KmsKeyId:KmsKeyId}' --output json
```

전송 데이터는 지원 EFS CSI/mount helper의 `tls` 옵션과 실제 마운트 경로를 확인합니다. FSx 전송 암호화는 지원 파일 시스템·클라이언트·인스턴스 구성 조건에 따라 서비스 안내를 따릅니다. **S3 HTTPS/TLS는 전송 보호이고 `aws s3 cp --sse AES256`는 저장 데이터의 SSE-S3 암호화 선택입니다.** 이 flag가 TLS를 켜지는 않습니다. HTTPS endpoint·인증서 검증을 사용하고 secure transport를 요구하는 버킷 정책을 검토하세요. KMS key policy와 전송 인증서 관리는 별개입니다.

### 액세스 제어

Part1에서 준비한 CSI 신원, 즉 컨트롤러의 지원 Pod Identity/IRSA 역할·정확한 드라이버 권한과 필요한 KMS grant를 사용합니다. 관련 없는 eksctl 명령으로 기존 관리형 add-on ServiceAccount를 재생성하거나 모든 노드·앱에 컨트롤러 권한을 옮기지 않습니다. Mountpoint pod-level 신원·EFS IAM mount·POSIX/access-point 신원은 서로 다른 권한 경로입니다.

네트워크는 실제 클라이언트/노드 SG에서 EFS mount target의 TCP2049 접근을 허용합니다. Lustre는 필요한 self/client 통신을 포함하여 클라이언트·파일 서버 사이의 TCP988·1018–1023 규칙이 필요합니다. EFA Lustre에는 지정된 SG 참조 all-traffic 규칙이 필요하며 인터넷 전체 CIDR로 대체할 수 없습니다. SG뿐 아니라 route·DNS·NACL·실제 CSI mount 출발지도 확인하세요. Kubernetes Pod NetworkPolicy가 노드에서 출발한 모든 파일 시스템 연결을 자동 제어하지는 않습니다.

아래 네임스페이스 reader는 PVC 객체를 조회하며 생성·확장·삭제하지 못합니다. 클러스터 범위 PV 조회는 별도로 검토한 ClusterRole이 필요합니다. 어느 Role도 파일 바이트를 직접 제어하지 않습니다. 네임스페이스에서 Pod를 생성할 수 있는 주체는 그 안의 PVC를 마운트할 수 있으므로 Pod 생성·워크로드 신원·POSIX/access point 권한·테넌트 격리도 제어해야 합니다:

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

### 파드 보안 컨텍스트

아래 완전한 예제는 Pod 수준 runAsUser/runAsGroup/fsGroup/seccomp와 컨테이너 수준 allowPrivilegeEscalation/capabilities/readOnlyRootFilesystem을 구분합니다. 선언되지 않은 data volume·쓰기 경로가 준비되지 않은 nginx 대신 준비한 암호화 class와 선언한 PVC를 사용합니다. 네임스페이스 정책 버전은 검토한 Kubernetes1.36 예제에 맞추었으므로 실제 클러스터에 적절한 버전을 사용하세요.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: secure-data
  namespace: secure-ns
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-encrypted
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: secure-ns
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
  - name: app
    image: busybox:1.37.0
    command:
    - sh
    - -c
    args:
    - test -w /data && sleep 3600
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
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: secure-data
```

읽기 전용 루트가 `/data`까지 읽기 전용으로 만들지는 않습니다. 이 워크로드는 의도적으로 쓰기 가능한 PVC를 확인합니다. fsGroup 동작은 CSI·파일 시스템에 따라 다르고 EFS access point가 다른 POSIX 신원을 강제할 수 있습니다. SELinux/AppArmor는 실제 노드·런타임 지원과 준비한 정책이 필요하므로 임의 MCS label·profile 이름을 복사하지 마세요. Pod Security Standards는 Pod 구성을 제한하며 클라우드 볼륨 암호화·IAM 권한을 제공하지 않습니다. Host 접근이 필요한 모니터링·CSI node agent는 별도로 검토한 네임스페이스·보안 설계가 필요합니다.

### 보안 정책 적용

PVC 이름 패턴·StorageClass allowlist만으로 EBS 암호화를 입증할 수는 없습니다. 다음 **Kyverno ValidatingPolicy**는 Kyverno1.19.1·CRD로 확인한 served `policies.kyverno.io/v1` API를 사용합니다. 설치된 컨트롤러·CRD와 적절한 admission 관리 주체가 필요합니다. 해당 릴리스에서 이전 ClusterPolicy 예제는 deprecated이므로 API 호환성을 가정하지 말고 계획하여 이전합니다.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-declared-ebs-encryption
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - storage.k8s.io
      apiVersions:
      - v1
      resources:
      - storageclasses
      operations:
      - CREATE
      - UPDATE
      scope: Cluster
  validations:
  - expression: '!(object.provisioner in [''ebs.csi.aws.com'', ''ebs.csi.eks.amazonaws.com''])
      || (has(object.parameters) && ''encrypted'' in object.parameters && object.parameters[''encrypted'']
      == ''true'')'
    message: EBS StorageClasses must explicitly request encryption.
```

이 정책은 Auto Mode provisioner를 포함한 **EBS StorageClass 생성·변경의 선언된 암호화 파라미터**를 검사합니다. 기존 AWS 볼륨·정적 PV·snapshot 내용·match 밖의 우회 경로를 검사하지 않습니다. Admission과 함께 StorageClass/PV 관리 권한 제한·백엔드 준수 검사를 사용하세요. 전체 강제 적용 전에 대표 리소스로 검증하고 정책 report·webhook 상태를 확인합니다. 기존 데이터 암호화에는 별도 이전 절차가 필요합니다.

## 스토리지 관리 모범 사례

![스토리지 수명 주기의 계획·구현·운영·최적화 네 단계가 각각 계획 및 설계, 자동화 및 IaC, 백업 및 재해 복구, 성능 및 비용 최적화라는 모범 사례 영역과 짝을 이루고, 각 영역 안의 세 실천 항목이 순서대로 이어지는 구조를 보여주는 다이어그램.](../.gitbook/assets/ko-eks-04-eks-storage-part3-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-04-eks-storage-part3-4.html)

### 계획과 용량

지연·IOPS/처리량·용량 증가·읽기/쓰기 패턴·동시성·가용성·내구성·RPO/RTO를 구분해 기록합니다. 그 요구로 블록·공유 NFS·병렬 Lustre·객체 접근을 선택합니다. 측정한 여유와 상한이 있는 확장 절차를 사용하며 autoscaler·PVC resize가 앱 복제·임의 용량 축소를 제공하지는 않습니다.

### 백업과 재해 복구

고유 백업 신원·보존 소유자가 있는 지원 schedule을 사용합니다. 고정 이름 snapshot을 반복 생성하는 shell cron은 첫 객체 생성 후 실패하며 daily-backup이라는 일회성 Velero 백업은 schedule이 아닙니다. Part2의 검토한 Velero/CSI 설치·DB 일관성 요구와 함께 다음 명령으로 일일 schedule을 검토용 출력합니다:

```bash
velero schedule create storage-daily --schedule="0 0 * * *" \
  --include-namespaces=storage-demo --ttl=720h0m0s -o yaml > storage-schedule-review.yaml
```

검토 후 소유자 경로로 배포하고 누락·실패 백업 경보와 격리 복원을 테스트합니다. S3 백업은 모든 볼륨 바이트 대신 native snapshot을 참조할 수 있습니다. 교차 AZ/리전 복구에는 접근 가능한 데이터·키·driver/storage 매핑·앱 검증이 필요합니다. 통제된 전환 성공까지 원본을 유지하며 schedule만으로 RPO/RTO를 주장하지 말고 실제 복구 시간을 기록합니다.

### Infrastructure as Code와 GitOps

Part1/Part2의 검사를 포함한 파일 시스템 생성 예제 또는 provider/schema 버전·subnet/mount-target/SG·삭제 보호를 검토한 소유자의 Terraform/CloudFormation 모듈을 사용합니다. 파일 시스템만의 Terraform 리소스는 EKS 마운트 경로 전체가 아닙니다. 백업 보존과 IaC destroy/prune 동작을 구분하세요.

Helm values는 chart별 입력입니다. Custom `storage.encrypted: true`는 template이 실제 지원 리소스 필드로 연결하지 않으면 아무 효과가 없습니다. 배포 전에 생성되는 StorageClass/PVC/워크로드를 렌더링·검증합니다. GitOps prune·chart uninstall·클레임 보존 설정은 데이터에 서로 다른 영향을 줄 수 있으므로 리소스별 소유 시스템을 기록하고 폐기 가능한 데이터로 수명 변경을 테스트합니다.

예를 들어 다음 파일 시스템 리소스는 암호화·Elastic 처리량을 요청하고30일 IA 학습 정책을 유지하며 Terraform destroy 방지를 추가합니다. Creation token을 프로젝트별 안정된 값으로 교체하고 provider·계정·리전과 검토한 네트워크·mount target을 구성합니다. prevent_destroy는 Terraform 작업 보호이지 백업·모든 외부 삭제에 대한 보호는 아닙니다:

```hcl
resource "aws_efs_file_system" "example" {
  creation_token   = "example"
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  encrypted        = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = "ExampleFileSystem"
  }
}
```

### 지속적인 검토

워크로드 변화에 따라 병목·프로비저닝 한도·보존 비용·보안 제어를 검토합니다. 소유권·백업/복구·삭제 영향을 확인하기 전까지 정리 보고서는 읽기 전용으로 유지합니다. 자동화 전에 경보·상한이 있는 변경 제안을 사용하세요. 본문 예제는 로컬 검사한 참고 구성이며 실제 백엔드 성능·admission 배포·복구는 대상 환경에서 검증해야 합니다.

## 결론

이 문서에서는 Amazon EKS 스토리지의 모니터링, 문제 해결, 비용 최적화 및 보안에 대해 알아보았습니다. 효과적인 스토리지 관리는 EKS 클러스터의 성능, 안정성 및 비용 효율성을 보장하는 데 중요합니다.

스토리지 요구사항은 애플리케이션마다 다르므로, 워크로드의 특성을 이해하고 적절한 스토리지 솔루션을 선택하는 것이 중요합니다. 또한, 정기적인 모니터링, 문제 해결, 비용 최적화 및 보안 검토를 통해 스토리지 리소스를 효과적으로 관리해야 합니다.

## 참고 자료

- [Amazon EKS 스토리지 모범 사례](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)
- [Kubernetes 스토리지 문제 해결](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-application/#debugging-pods)
- [Kubernetes 스토리지 보안](https://kubernetes.io/docs/concepts/security/)

- [EBS CloudWatch metrics](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [FSx Lustre metric dimensions](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [EFS performance modes](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [EFS lifecycle API](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [FSx encryption at rest](https://docs.aws.amazon.com/fsx/latest/LustreGuide/encryption-at-rest.html)
- [FSx network access](https://docs.aws.amazon.com/fsx/latest/LustreGuide/limit-access-security-groups.html)
- [S3 encryption at rest](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html)
- [Kyverno CEL migration](https://kyverno.io/docs/guides/migration-to-cel/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../quizzes/eks/04-eks-storage-part3-quiz.md)를 풀어보세요.
