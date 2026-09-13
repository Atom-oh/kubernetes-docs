# 노드 라이프사이클 관리

< [이전: 워크로드 배치 전략](./06-workload-placement.md) | [목차](./README.md) | [다음: 운영 및 유지보수](./08-operations.md) >

> **지원 버전**: AWS가 지원하는 Kubernetes 버전의 EKS Hybrid Nodes; nodeadm 1.0.20 기준 (SSM 신규 설치·업그레이드는 1.0.19 이상 필요)
> **마지막 업데이트**: 2026년 9월 13일

이 문서에서는 EKS Hybrid Nodes의 nodeadm 고급 설정, 대규모 노드 설치 자동화, 업그레이드 전략, 자격 증명 관리 및 헬스체크 자동화를 다룹니다.

## 1. nodeadm 고급 설정 (Advanced NodeConfig)

### kubelet 튜닝

프로덕션 환경에서는 kubelet의 리소스 예약, 축출 임계값, 이미지 가비지 컬렉션 등을 세밀하게 조정해야 합니다.

#### 리소스 예약 (system-reserved / kube-reserved)

이 설정은 Node Allocatable을 산정할 때 예약량을 차감합니다. 모든 호스트 프로세스에 보편적인 강제 상한을 거는 설정은 아닙니다. 기본 enforceNodeAllocatable은 Pod를 대상으로 하며 system/kube 예약의 강제 적용에는 별도 cgroup과 검토된 cgroup 계층이 필요합니다. OS·kubelet·런타임·CNI/드라이버 사용량을 측정해 값을 정합니다.

```yaml
kubelet:
  config:
    systemReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "10Gi"
    kubeReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "5Gi"
```

| 파라미터 | 설명 | 초기 산정 예 — 실측 후 조정 |
|----------|------|--------|
| `systemReserved.cpu` | OS 및 시스템 데몬용 CPU | 500m ~ 1000m |
| `systemReserved.memory` | OS 및 시스템 데몬용 메모리 | 1Gi ~ 2Gi |
| `kubeReserved.cpu` | kubelet, containerd용 CPU | 500m ~ 1000m |
| `kubeReserved.memory` | kubelet, containerd용 메모리 | 1Gi ~ 2Gi |

#### 축출 임계값 (Eviction Thresholds)

kubelet은 리소스 압박 시 노드 자원 회수를 시도하고 필요하면 Pod를 축출합니다. 안정성을 보장하는 기능은 아니며 노드 압박 축출은 API eviction 요청처럼 PodDisruptionBudget을 따르지 않습니다.

```yaml
kubelet:
  config:
    evictionHard:
      memory.available: 200Mi
      nodefs.available: 10%
      imagefs.available: 15%
      nodefs.inodesFree: 5%
      imagefs.inodesFree: 5%
    evictionSoft:
      memory.available: 500Mi
      nodefs.available: 15%
    evictionSoftGracePeriod:
      memory.available: 1m30s
      nodefs.available: 2m
    evictionMaxPodGracePeriod: 60
```

> **참고**: Hard 임계값에는 soft 관찰 유예 기간이 없으며 종료 유예 없이 처리됩니다. Soft 임계값은 evictionSoftGracePeriod 동안 지속되어야 하고, Pod 종료 유예의 상한은 별도 evictionMaxPodGracePeriod로 정합니다. Soft 설정으로 이후 hard 축출이나 OOM이 방지되지는 않습니다. evictionHard를 변경하면 inode를 포함한 전체 의도한 임계값을 명시합니다. 지원되는 기본값 병합을 명시적으로 켜지 않으면 누락한 기본 임계값은 0이 됩니다.

#### maxPods 계산

CPU·메모리·데몬 사용량과 Cilium 노드별 pool을 함께 고려합니다. Cilium cluster-pool은 CIDR당 IPv4 주소 두 개를 예약하므로 /25, /24, /26에서 사용 가능한 주소는 각각 126, 254, 62개입니다. 아래 값은 산정 예이며 검증된 플릿 권장값이나 ENI 기반 한도가 아닙니다. 기존 clusterPoolIPv4MaskSize를 단순 변경해 할당한 블록을 늘릴 수는 없습니다.

```yaml
kubelet:
  config:
    maxPods: 110  # /25의 사용 가능 IPv4는 126개; 데몬·운영 여유를 남김
```

| 마스크 크기 | 전체 IPv4 주소 수 | maxPods 산정 예 |
|-------------|-------|-------------|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### 이미지 가비지 컬렉션

디스크 공간 관리를 위해 미사용 이미지를 자동으로 정리합니다.

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### 셧다운 그레이스 기간

지원되는 Linux 호스트의 graceful node shutdown은 systemd inhibitor lock과 kubelet 설정에 의존합니다. 전원 상실이나 강제 종료 때도 정상 종료를 보장하지는 않습니다.

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **참고**: 이 두 그룹 설정에서 전체 60초에는 critical Pod용 20초가 포함되어 다른 Pod의 종료 창은 40초입니다. 모든 Pod가 항상 40초를 받는다는 뜻은 아니며 각 terminationGracePeriodSeconds와 실제 종료 상황도 영향을 줍니다.

### containerd 고급 설정

#### 프라이빗 레지스트리 미러 설정

아래는 containerd 1.x의 config version 2 문법입니다. containerd 2.x에는 config version 3과 io.containerd.cri.v1.images.registry 경로를 사용합니다. 런타임 재시작 전 설치 버전과 병합된 실제 설정을 확인합니다. 레지스트리 CA·mirror 경로 지원을 검증하고 TLS 검증을 끄지 않습니다.

신뢰하는 프라이빗 레지스트리를 미러로 사용합니다. 아래 server 항목은 upstream endpoint를 fallback으로 유지하므로 에어갭 구성이 아닙니다. 미러에 의존하기 전에 인증, proxy 프로젝트 경로와 CA 신뢰를 검증합니다.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

`hosts.toml` 파일을 통해 레지스트리별 미러를 구성합니다:

```bash
# /etc/containerd/certs.d/docker.io/hosts.toml
sudo mkdir -p /etc/containerd/certs.d/docker.io
cat <<EOF | sudo tee /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"

[host."https://harbor.internal.company.io/v2/dockerhub-proxy"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
  override_path = true
EOF
```

#### GPU 노드용 NVIDIA 런타임 클래스

아래 containerd 1.x fragment는 전용 GPU 노드에 NVIDIA 런타임 바이너리/툴킷과 호환 드라이버가 이미 설치되어 있다고 가정합니다. handler를 등록하는 설정이며 GPU 스택을 설치하지 않습니다. 필요하면 실제 RuntimeClass와 워크로드 설정으로 선택합니다. containerd 2.x에는 config version 3과 io.containerd.cri.v1.runtime 경로를 사용하고 두 형식을 혼합하지 않습니다. device plugin/DRA와 툴킷 전제는 GPU 장을 확인합니다.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".containerd]

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
      privileged_without_host_devices = false
      runtime_type = "io.containerd.runc.v2"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
      BinaryName = "/usr/bin/nvidia-container-runtime"
      SystemdCgroup = true
```

### 레이블 및 테인트 전략

#### nodeadm 자동 레이블

nodeadm은 하이브리드 노드를 초기화할 때 다음 레이블을 자동으로 부여합니다:

```
eks.amazonaws.com/compute-type=hybrid
```

이 레이블은 `--node-labels` 플래그에 수동으로 추가할 필요가 없습니다.

#### 추가 커스텀 레이블 전략

용도별, 환경별로 추가 레이블을 부여하여 워크로드 배치를 세밀하게 제어합니다.

```yaml
kubelet:
  flags:
    # 용도별 레이블
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training

    # 환경별 레이블 (프로덕션)
    # - --node-labels=environment=production,tier=compute

    # 데이터센터 위치별 레이블
    # - --node-labels=datacenter=dc-seoul-01,rack=rack-a3
```

#### 테인트 전략

| 전략 | 설명 | 사용 사례 |
|------|------|-----------|
| 자동 테인트 (NodeConfig) | 최초 Node 등록 시 적용; 기존 Node 테인트는 명시적으로 조정 | 모든 하이브리드 노드에 공통 적용 |
| 수동 테인트 (kubectl) | 운영 중 동적으로 적용 | GPU 노드 격리, 유지보수 모드 |

```yaml
# NodeConfig에서 자동 테인트
kubelet:
  flags:
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

```bash
# 운영 중 수동 테인트 추가
kubectl taint nodes hybrid-gpu-001 gpu=true:NoSchedule
kubectl taint nodes hybrid-node-005 maintenance=true:NoSchedule
```

<a id="전체-nodeconfig-예시-프로덕션급"></a>

### 전체 NodeConfig 검토용 템플릿

실행 검증하지 않은 설정 템플릿이며 운영 준비 완료를 뜻하지 않습니다. 앞의 kubelet/containerd fragment는 spec 아래에 배치합니다. 실제 cluster name과 Region을 지정하면 nodeadm이 권한 있는 discovery 경로로 메타데이터를 가져옵니다. 실제 activation 값은 승인된 비공개 NodeConfig 파일로 전달하며 containerd 문법과 자원 값을 호스트에 맞게 선택합니다.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: prod-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 60s
      shutdownGracePeriodCriticalPods: 20s
      systemReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 10Gi
      kubeReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 5Gi
      evictionHard:
        memory.available: 200Mi
        nodefs.available: 10%
        imagefs.available: 15%
        nodefs.inodesFree: 5%
        imagefs.inodesFree: 5%
      evictionSoft:
        memory.available: 500Mi
        nodefs.available: 15%
      evictionSoftGracePeriod:
        memory.available: 1m30s
        nodefs.available: 2m
      imageGCHighThresholdPercent: 85
      imageGCLowThresholdPercent: 80
      evictionMaxPodGracePeriod: 60
    flags:
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
  containerd:
    config: "version = 2\n[plugins.\"io.containerd.grpc.v1.cri\".registry]\n  config_path\
      \ = \"/etc/containerd/certs.d\"\n"
```

---

## 2. 대규모 노드 설치 자동화 (Fleet Installation)

### Ansible Playbook

승인한 인벤토리와 작은 배치로 [부트스트랩 절차](./04-node-bootstrap.md)를 실행합니다. 호스트 아키텍처별 Hybrid Nodes nodeadm 바이너리를 고정하고 검증합니다. 모든 호스트에 amd64 바이너리를 배포하거나 배치 도중 검토하지 않은 `latest`를 다시 받지 않습니다. SSM 신규 설치·업그레이드에는 오래된 설치 프로그램 서명 키 문제 때문에 AWS가 nodeadm **1.0.19 이상**을 요구합니다. 이 장은 1.0.20을 기준으로 확인했으며 실행 전 OS·Kubernetes·CNI·CSI·런타임 조합을 검토해야 합니다.

#### 인벤토리 구성

아래 주소는 문서용 예시입니다. 실제 호스트 접속 대상과 Kubernetes Node 이름·UID를 별도로 기록합니다. 특히 SSM 기반 Node 이름이 SSH로 접속할 수 있는 호스트 이름이라고 가정하지 않습니다.

```ini
[hybrid_nodes:children]
gpu_nodes
cpu_nodes

[gpu_nodes]
gpu-host-a ansible_host=192.0.2.10 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[cpu_nodes]
cpu-host-a ansible_host=192.0.2.20 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[hybrid_nodes:vars]
ansible_user=REPLACE_WITH_APPROVED_OPERATOR
```

#### 자동화 플레이북

다음은 **사전 설치한 호스트의 점검용**이며 완전한 설치 플레이북이 아닙니다. root 소유의 비공개 NodeConfig를 승인한 시크릿 파일 전달 절차로 먼저 배포합니다. 활성화 코드나 개인 키를 일반 inventory/group 변수 또는 템플릿 로그에 넣지 않습니다. 두 digest 자리표시자는 선택한 릴리스에서 독립적으로 확인한 값으로 교체합니다. install/init을 실행하거나 중지된 서비스를 시작하면서 건강 상태를 검증했다고 처리하지 않습니다.

```yaml
- name: Review preinstalled Hybrid Nodes before an approved bootstrap
  hosts: hybrid_nodes
  gather_facts: true
  become: true
  serial: 1
  any_errors_fatal: true
  vars:
    architecture_map:
      x86_64: amd64
      aarch64: arm64
    approved_nodeadm_sha256:
      amd64: REPLACE_WITH_REVIEWED_AMD64_SHA256
      arm64: REPLACE_WITH_REVIEWED_ARM64_SHA256
    nodeconfig_path: /etc/eks/nodeconfig.yaml
  tasks:
  - name: Require a reviewed architecture and binary digest
    ansible.builtin.assert:
      that:
      - ansible_facts.architecture in architecture_map
      - approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]] is match('^[a-f0-9]{64}$')
  - name: Inspect the existing nodeadm artifact
    ansible.builtin.stat:
      path: /usr/local/bin/nodeadm
      checksum_algorithm: sha256
      get_checksum: true
    register: nodeadm_artifact
  - name: Match the approved artifact
    ansible.builtin.assert:
      that:
      - nodeadm_artifact.stat.exists
      - nodeadm_artifact.stat.executable
      - nodeadm_artifact.stat.checksum == approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]]
  - name: Validate the privately delivered NodeConfig
    ansible.builtin.command:
      argv:
      - /usr/local/bin/nodeadm
      - config
      - check
      - -c
      - file://{{ nodeconfig_path }}
    changed_when: false
    no_log: true
```

`/usr/bin/kubelet` 파일 하나만으로 전체 설치 완료를 판정하지 않습니다. 사전 점검 후 부트스트랩 장의 전체 install/init 절차와 호스트별 작업 기록·식별자 검증을 사용합니다. 실패하면 배치를 멈추고 부분 완료·확인 불가 상태를 복구 대상으로 남기며 init을 무조건 재실행하지 않습니다. `changed_when: false`는 Ansible 표시를 바꿀 뿐 명령의 실제 동작을 제한하지 않습니다.

#### 롤별 변수 (GPU 노드 vs 일반 노드)

| 호스트 그룹 | 명시적으로 검토할 호스트별 설정 |
| --- | --- |
| CPU | OS·아키텍처, 런타임 설정 형식, 측정한 예약량, 워크로드 레이블과 테인트 |
| GPU | CPU 전제 조건과 실제 드라이버·툴킷, device-plugin/DRA 경로, 런타임 handler/RuntimeClass, GPU 검증 |

호스트별 템플릿을 명시적으로 선택합니다. `group_names[0]`은 신뢰할 수 있는 역할 선택 기준이 아닙니다. `nvidia.com/gpu.present=true` 레이블만 추가해도 드라이버가 설치되거나 GPU allocatable이 생기는 것은 아닙니다. [GPU 통합](./05-gpu-integration.md)을 참고합니다.

### 설치 검증 스크립트

클러스터에서 기대하는 **전체 Hybrid Nodes**의 `expected-nodes.json`을 별도로 승인해 저장합니다. 검증 대상 API 응답 자체에서 기대 목록을 만들면 누락된 노드를 발견할 수 없습니다. 교체 시에는 새 식별자를 확인한 뒤 인벤토리를 갱신합니다.

```json
[
  {"name": "REPLACE_WITH_REGISTERED_NODE_NAME", "uid": "REPLACE_WITH_APPROVED_NODE_UID"}
]
```

다음을 `check-fleet.sh`로 저장합니다. Bash·kubectl·jq가 필요합니다. 운영자 워크스테이션에서는 `KUBE_CONTEXT`를 지정하고, 아래 클러스터 내부 관측기는 ServiceAccount를 사용합니다. API 실패·권한 거부, 빈 목록, 다른 UID, 조건 누락·Unknown은 0이 아닌 종료 코드로 처리합니다.

```bash
#!/usr/bin/env bash
# Read-only Node inventory/condition snapshot; no workload or host mutations.
set -euo pipefail
EXPECTED_FILE="${1:?Usage: check-fleet.sh expected-nodes.json}"
umask 077
WORK_DIR=$(mktemp -d)
trap 'rm -rf -- "$WORK_DIR"' EXIT
KUBECTL=(kubectl --cache-dir "$WORK_DIR/kube-cache")
if [ -n "${KUBE_CONTEXT:-}" ]; then KUBECTL+=(--context "$KUBE_CONTEXT"); fi
"${KUBECTL[@]}" get nodes -l eks.amazonaws.com/compute-type=hybrid -o json > "$WORK_DIR/nodes.json"
jq -e --slurpfile expected "$EXPECTED_FILE" '
  def required($kind; $status):
    [.status.conditions[]? | select(.type == $kind)] as $c |
    ($c | length) == 1 and $c[0].status == $status;
  $expected[0] as $want |
  ($expected | length) == 1 and ($want | type) == "array" and
  ($want | length) > 0 and
  ($want | length) == ($want | map(.name) | unique | length) and
  all($want[]; (.name | type) == "string" and (.name | length) > 0 and
               (.uid | type) == "string" and (.uid | length) > 0) and
  (.items | type) == "array" and
  (.items | map(.metadata.name) | sort) == ($want | map(.name) | sort) and
  all(.items[];
    . as $node |
    any($want[]; .name == $node.metadata.name and .uid == $node.metadata.uid) and
    .metadata.deletionTimestamp == null and
    .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
    required("Ready"; "True") and
    required("MemoryPressure"; "False") and
    required("DiskPressure"; "False") and
    required("PIDPressure"; "False"))
' "$WORK_DIR/nodes.json" > /dev/null
printf 'Expected Node identities and conditions match this snapshot.\n'
# CNI readiness, DNS, network paths, storage, applications and freshness need
# separate checks; Node Ready is not an end-to-end health guarantee.
```

이 검사는 Node 목록과 조건의 스냅샷입니다. `Ready=True`만으로 현재 CNI·DNS·스토리지·애플리케이션 상태를 입증하지 않습니다. 선택한 CNI의 실제 DaemonSet/Pod, 사이트 사이 연결, DNS 응답, 스토리지 작업과 워크로드 endpoint를 별도로 점검합니다. 부분 문자열 비교로 `NotReady`를 Ready에 포함하지 않습니다.

## 3. 노드 업그레이드 전략 (Upgrade Strategies)

### 버전 스큐 정책

아래 1.31 표는 skew 계산을 설명하는 과거 버전 예시이며 지금 해당 버전의 노드를 배포하라는 권장이 아닙니다. 현재 AWS 문서에서 지원되는 EKS 대상 버전과 OS·CNI·CSI·런타임 호환성을 선택합니다.

Kubernetes는 kubelet과 API 서버 간 엄격한 버전 호환성 정책을 유지합니다.

| kubelet 버전 | API 서버 버전 | 호환 여부 |
|-------------|-------------|----------|
| 1.31 | 1.31 | ✅ 동일 버전 |
| 1.30 | 1.31 | ✅ n-1 |
| 1.29 | 1.31 | ✅ n-2 |
| 1.28 | 1.31 | ✅ n-3 |
| 1.27 | 1.31 | ❌ n-4 (미지원) |
| 1.32 | 1.31 | ❌ kubelet > API 서버 (미지원) |

> **업그레이드 순서**: 뒤처진 노드를 현재 컨트롤 플레인의 minor 버전으로 먼저 맞춥니다. 노드를 다음 minor 버전으로 올리기 전에는 컨트롤 플레인을 업그레이드합니다. kubelet은 API 서버보다 최신일 수 없으며, 지원되는 skew가 오래된 노드를 계속 유지하라는 권장은 아닙니다.

### 업그레이드 사전 체크리스트

배치마다 대상 major.minor와 실제 artifact 버전·checksum을 승인하고 컨트롤 플레인 skew, OS·CNI·CSI·런타임 호환성을 확인합니다. 축출할 워크로드를 수용할 여유 용량, Pod requests·배치 제약, PDB 허용 중단 수, local PV/emptyDir 소유권, 백업·복구와 관측성을 검토합니다. `kubectl top`의 사용량은 보조 관측값이며 모든 Pod가 다른 노드에 배치될 수 있다는 증거는 아닙니다.

Node 이름·UID, 실제 호스트 접속 대상, 자격 증명 공급자와 기존 `.spec.unschedulable` 상태를 기록합니다. `nodeadm upgrade`는 Node 이름을 보존하며 자격 증명 공급자를 바꾸는 작업이 아닙니다. 기본적으로 지정한 minor의 최신 artifact를 선택하므로 minor 고정만으로 재현 가능한 artifact 계획이 되지는 않습니다. 재현성이 필요하면 승인한 manifest·비공개 artifact 절차를 사용합니다.

### 롤링 업그레이드

**명시적으로 선택한 노드를 한 번에 하나씩** 처리하고 첫 실패에서 멈춥니다. 아래는 실행하지 않은 운영자 절차이며 가용성 보장을 검증한 fleet controller가 아닙니다. 첫·마지막 블록은 승인한 클러스터 관리 워크스테이션에서 같은 셸로 실행하거나 기록한 디렉터리·입력을 복원해 사용합니다. 운영자에게 Node·Lease·Pod/PDB 조회와 cordon/drain 권한이 필요합니다.

비공개 기록 경로를 보관합니다. 다음 명령은 선택한 Node를 cordon하고 drain합니다. PDB 차단이나 local emptyDir은 워크로드·데이터 보존 판단이 필요합니다. 실패를 없애기 위해 force, disable-eviction, delete-emptydir-data를 일괄 추가하지 않습니다.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the actual Kubernetes Node name}"
: "${EXPECTED_UID:?Set the approved Node UID}"
UPGRADE_RECORD_DIR=$(mktemp -d "$PWD/hybrid-upgrade.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/node-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null
' "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/lease-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | type) == "string"
' "$UPGRADE_RECORD_DIR/lease-before.private.json" > /dev/null
printf 'Private upgrade record: %s\n' "$UPGRADE_RECORD_DIR"
kubectl --context "$KUBE_CONTEXT" cordon "$NODE"
kubectl --context "$KUBE_CONTEXT" drain "$NODE" --ignore-daemonsets --timeout=10m
```

drain이 성공한 뒤에만 **매핑한 실제 호스트**에 접속하여 식별자와 승인한 nodeadm 바이너리를 확인하고 다음 업그레이드를 실행합니다. 노드 중단이 발생하는 명령입니다. NodeConfig는 기존 자격 증명 공급자를 유지하며 node/pod/init 검증을 통상적으로 생략하지 않습니다.

```bash
set -euo pipefail
: "${TARGET_MINOR:?Set the approved EKS-supported major.minor target}"
sudo /usr/local/bin/nodeadm upgrade "$TARGET_MINOR" \
  -c file:///etc/eks/nodeconfig.yaml --timeout 20m
```

명령 오류나 세션 단절은 작업 실패·확인 불가로 취급합니다. Kubernetes에 이전 Ready 조건이 남아 있어도 성공으로 간주하지 않고 cordon을 유지합니다. 호스트 작업의 성공을 확인한 뒤 워크스테이션에서 관측합니다. artifact 계획의 build suffix까지 포함한 전체 kubelet 버전을 사용합니다.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the recorded Node name}"
: "${EXPECTED_UID:?Set the recorded Node UID}"
: "${EXPECTED_KUBELET_VERSION:?Set the full version from the approved artifact plan}"
: "${UPGRADE_RECORD_DIR:?Use the private record directory from the pre-upgrade step}"
jq -e --arg uid "$EXPECTED_UID" --arg node "$NODE" \
  '.metadata.uid == $uid and .metadata.name == $node' \
  "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
POSTCHECK_DIR=$(mktemp -d "$UPGRADE_RECORD_DIR/check.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$POSTCHECK_DIR/node-after.private.json"
jq -e --arg uid "$EXPECTED_UID" --arg version "$EXPECTED_KUBELET_VERSION" '
  [.status.conditions[]? | select(.type == "Ready")] as $ready |
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null and
  .status.nodeInfo.kubeletVersion == $version and
  ($ready | length) == 1 and $ready[0].status == "True"
' "$POSTCHECK_DIR/node-after.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$POSTCHECK_DIR/lease-after.private.json"
jq -e --arg uid "$EXPECTED_UID" \
  --slurpfile before "$UPGRADE_RECORD_DIR/lease-before.private.json" '
  def epoch: sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601;
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | epoch) > ($before[0].spec.renewTime | epoch)
' "$POSTCHECK_DIR/lease-after.private.json" > /dev/null
printf 'Node identity, target kubelet version, Ready and a newer Lease observed.\n'
# Workload/CNI/DNS/storage checks and the prior scheduling intent remain separate.
# This check never uncordons the node.
```

대상 버전·Node 식별자와 함께 저장한 스냅샷보다 새로운 Lease 갱신을 요구하지만, 이것도 애플리케이션 합격 검사는 아닙니다. CNI·DNS·볼륨·드라이버/런타임·워크로드 복구를 확인한 뒤 원래 스케줄 가능했던 Node만 명시적으로 uncordon합니다. EXIT trap에서 자동 uncordon하거나 원래 의도적으로 cordon했던 노드를 스케줄 가능하게 바꾸지 않습니다. 증거를 보관하고 다음 승인 노드를 처리합니다.

### 카나리 업그레이드

API 목록의 첫 번째 노드 대신 OS·아키텍처·런타임·자격 증명 공급자·워크로드를 대표하는 카나리를 선택합니다. 동일한 한 노드 절차를 적용하고 서비스에서 합의한 관측 기간 동안 오류·지연, 스토리지·네트워크와 실제 버전을 검증합니다. 고정된 sleep이나 Node Ready만으로 통과 처리하지 않습니다. 확인 후 작은 배치로 확대하고, cutover라면 합격 전까지 이전 호스트를 보존합니다.

<a id="롤백-절차"></a>

### 복구와 롤백의 한계

AWS는 여유 용량이 있으면 새 호스트를 준비해 제어된 방식으로 전환하는 절차를 권장합니다. 애플리케이션·스토리지·네트워크와 대상 버전 검사가 끝날 때까지 이전 호스트를 보존합니다. 인플레이스 `nodeadm upgrade`는 노드를 중단하며 일반적인 트랜잭션식 다운그레이드 기능이 아닙니다.

실패하면 해당 노드의 cordon을 유지하고 나머지 작업을 중단한 뒤 진단 자료와 설치된 구성 요소·자격 증명을 확인합니다. 현재 컨트롤 플레인과 호환되는 승인된 이미지/버전으로 복구합니다. 이전 `Ready=True` 상태가 남아 있다는 이유만으로 자동 uncordon하지 말고 예상 노드 식별자, 실제 kubelet 버전과 워크로드 준비 상태도 확인합니다.

`/var/lib/kubelet`이나 `/etc/kubernetes`의 재귀 삭제를 일반적인 롤백 단계로 사용하지 않습니다. Pod volume·subpath mount를 통해 호스트나 애플리케이션 데이터가 노출될 수 있습니다. nodeadm 1.0.9부터 강제 uninstall도 `/var/lib/kubelet`을 의도적으로 보존하므로 예외적인 정리에는 mount와 데이터 보존 검토가 필요합니다. Uninstall은 Kubernetes Node의 drain·삭제나 CNI 전체 제거를 대신하지 않으며 SSM 관리형 인스턴스 등록도 해제합니다. 따라서 재구축에는 완전한 install/부트스트랩과 식별자 대조가 필요하고 무조건 uninstall/reinstall하는 반복문을 사용하지 않습니다.

---

## 4. 자격 증명 라이프사이클 (Credential Lifecycle)

<a id="ssm-hybrid-activation-갱신"></a>

### SSM Hybrid Activation 만료

활성화의 만료는 **새 등록**을 제한합니다. 이미 등록한 노드는 명시적으로 등록 해제할 때까지 Systems Manager 관리형 노드로 남습니다. 원래 활성화가 만료됐다는 이유만으로 정상 노드를 uninstall하거나 재등록하지 않습니다. 등록, 에이전트의 자격 증명 회전, IAM 권한과 연결 상태는 서로 다른 수명 주기입니다.

추가 호스트 등록이나 승인된 복구 과정에서 재등록이 필요한 경우에만 새 활성화를 만듭니다. SSM용으로 구성한 실제 Hybrid Nodes IAM 역할을 사용하고 일반 Run Command 역할로 대체하지 않습니다. 아래 AWS 리소스 생성 명령 전에는 역할의 trust/권한, 계정, Region과 새 노드 수를 확인합니다. 활성화 코드는 비밀번호에 해당하는 비밀이므로 응답을 비공개 파일에 저장하고 승인된 NodeConfig 비밀 파일 전달 절차를 사용합니다.

```bash
set -euo pipefail
umask 077
: "${HYBRID_NODE_ROLE_NAME:?Set the reviewed Hybrid Nodes IAM role name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${NEW_NODE_COUNT:?Set the approved registration count}"
set -C  # Refuse to overwrite an existing private response file.
aws ssm create-activation   --iam-role "$HYBRID_NODE_ROLE_NAME"   --registration-limit "$NEW_NODE_COUNT"   --region "$AWS_REGION"   --output json > activation.private.json
```

AWS CLI가 실패하면 응답 파일도 불완전할 수 있으므로 중단하고 비공개로 확인한 뒤 재시도합니다. 활성화 코드를 출력하거나 파일을 커밋하지 않습니다. API의 기본 등록 기간이 맞지 않으면 승인된 만료 시각을 명시하며 최대 기간은 30일입니다. 등록 개수 제한은 유출된 활성화를 사용할 수 있는 호스트의 권한 경계를 대신하지 않습니다.

`nodeadm uninstall`은 SSM 기반 호스트의 등록을 해제하고 설치된 구성 요소를 제거합니다. 이후 `init`만 실행해도 `install`이 대체되지는 않습니다. 의도적인 복구라면 drain·데이터 보존과 식별자 변경을 검토한 뒤 완전한 [부트스트랩 절차](./04-node-bootstrap.md)를 사용합니다. 노드 이름·UID와 SSM 관리형 인스턴스 ID를 인벤토리와 다시 대조하며 이전 성공 기록을 그대로 재사용하지 않습니다.

### IAM Roles Anywhere 인증서 갱신

만료 전에 기존 PKI를 통해 노드의 **호스트 인증용 인증서**를 갱신합니다. kubelet client/server 인증서나 EKS 컨트롤 플레인 CA와는 별개입니다. 인증서 subject, 설정한 nodeName, role session 조건, profile·role·trust anchor가 계속 호환되어야 하며 CN 변경을 단순 파일 교체로 취급하지 않습니다.

#### 인증서 만료 모니터링

임의 경로 대신 NodeConfig의 실제 certificatePath를 검사합니다. 파일이 없거나 읽을 수 없거나 인증서가 잘못됐거나 30일 안에 만료되면 실패합니다. 30일은 운영 경고 임계값의 예시입니다.

```bash
#!/usr/bin/env bash
set -euo pipefail
CERT_PATH="${1:?Usage: check-cert-expiry.sh certificate.pem}"
test -r "$CERT_PATH" || { echo 'Certificate missing or unreadable' >&2; exit 1; }
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
# This is an expiration check only, not chain/key/CN/trust/IAM validation.
```

<a id="자동-갱신-스크립트"></a>

#### 인증서 갱신 절차

조직이 승인한 CA 클라이언트와 인증된 발급 정책을 사용합니다. 범용 무인증 `/sign` endpoint는 없습니다. 기존 개인 키를 재사용하면 보호 상태를 유지하고, 키도 바꾸려면 승인한 키 교체 절차를 따릅니다. 의도한 식별자의 CSR을 제출하고 발급받은 후보 인증서를 활성 파일과 분리해 저장합니다.

다음은 **로컬 검사만** 수행합니다. 잔여 유효 기간, 별도로 승인한 루트에 대한 인증서 체인, 공개 키 일치를 확인하며 중간 CA가 필요하면 `INTERMEDIATE_CHAIN`을 제공합니다. 모든 PKI/IAM 정책, 폐기 여부, nodeName/CN이나 실제 인증 성공을 검증하는 코드는 아닙니다.

```bash
set -euo pipefail
umask 077
: "${CANDIDATE_CERT:?Path to the issued candidate leaf certificate}"
: "${PRIVATE_KEY:?Path to its existing protected private key}"
: "${APPROVED_CA_PEM:?Path to the separately approved trust roots}"
CERT_CHECK_DIR=$(mktemp -d)
trap 'rm -rf -- "$CERT_CHECK_DIR"' EXIT
openssl x509 -in "$CANDIDATE_CERT" -checkend 2592000 -noout
VERIFY=(openssl verify -CAfile "$APPROVED_CA_PEM")
if [ -n "${INTERMEDIATE_CHAIN:-}" ]; then VERIFY+=(-untrusted "$INTERMEDIATE_CHAIN"); fi
"${VERIFY[@]}" "$CANDIDATE_CERT"
openssl x509 -in "$CANDIDATE_CERT" -pubkey -noout > "$CERT_CHECK_DIR/cert.pub"
openssl pkey -in "$PRIVATE_KEY" -pubout > "$CERT_CHECK_DIR/key.pub"
cmp "$CERT_CHECK_DIR/cert.pub" "$CERT_CHECK_DIR/key.pub"
```

반영 전에 subject/SAN·용도·CA 정책·폐기 여부와 정확한 nodeName/role 조건을 검토합니다. 현재 인증서를 비공개로 백업한 후 승인한 인증서 관리자가 소유자·권한을 보존하며 같은 파일시스템에서 검증한 인증서를 원자적으로 교체하도록 합니다. 키와 인증서를 함께 교체하면 소비자가 서로 다른 쌍을 읽지 않도록 조정해야 합니다.

nodeadm이 실제 구성한 credential process 또는 자격 증명 파일 갱신 모드를 확인하고 승인한 비공개 진단 경로에서 다음 credential refresh를 검증합니다. kubelet 재시작만으로 X.509 인증서가 갱신되거나 helper의 새 인증서 수용이 입증되지는 않습니다. 발급자 연동·후보 거부·원자적 반영·refresh·복구를 해당 환경에서 시험한 후 자동 갱신을 구성합니다. 이 장에서는 그러한 운영 환경 갱신을 실행하지 않았습니다.

#### Trust Anchor 업데이트

동일하게 신뢰하는 CA에서 leaf 인증서를 갱신하면 일반적으로 trust anchor를 교체할 필요가 없습니다. CA rollover는 의존하는 전체 호스트·profile·role에 영향을 줍니다. PKI/IAM 담당자와 신뢰 중첩·이전 계획을 세우고, source 유형과 의존 노드를 확인하며 복구 경로를 보존한 후 신뢰 설정을 바꿉니다.

**CERTIFICATE_BUNDLE** source는 PEM 줄바꿈을 보존하도록 JSON 파일로 전달합니다. 아래 sourceData union에는 x509CertificateData만 넣습니다. AWS_ACM_PCA 유형은 acmPcaArn을 사용하며 별도로 검토합니다. 아래 예시는 비공개 요청 파일 생성 후 AWS 업데이트까지 수행하므로 일상적인 인증서 만료 점검으로 실행하지 않습니다.

```bash
set -euo pipefail
umask 077
: "${APPROVED_CA_PEM:?Path to the reviewed CA certificate bundle}"
: "${TRUST_ANCHOR_ID:?Set the reviewed existing trust anchor ID}"
: "${AWS_REGION:?Set the trust anchor Region}"
set -C
jq -n --rawfile bundle "$APPROVED_CA_PEM" \
  '{sourceType:"CERTIFICATE_BUNDLE", sourceData:{x509CertificateData:$bundle}}' \
  > trust-anchor-source.private.json
# AWS mutation: run only after the CA rollover and dependent-node review.
aws rolesanywhere update-trust-anchor --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --region "$AWS_REGION" --source file://trust-anchor-source.private.json \
  --output json > trust-anchor-update.private.json
```

의도한 anchor를 다시 조회하고 카나리의 새 자격 증명 발급을 검증한 뒤 rollover를 마칩니다. API 오류는 실패·확인 불가이며 기존 신뢰가 유효하다는 증거가 아닙니다. 발급받은 자격 증명을 로그에 남기거나 anchor 하나를 교체하면 모든 기존 인증서의 접근이 자동 보존된다고 가정하지 않습니다.

## 5. 노드 헬스체크 자동화 (Health Monitoring)

### 자동화된 헬스체크 CronJob

이 관측기는 2절의 Node 스냅샷 검사를 실행합니다. 호스트에서 nodeadm을 실행하거나 AWS 자격 증명을 검증하는 Job이 **아닙니다**. Bash·kubectl·jq를 포함하고 클러스터와 호환되며 UID10001로 실행 가능한 검토한 이미지를 준비해야 합니다. 배포 전 이미지 자리표시자를 교체해야 하며 이 장에서 이미지·클러스터 실행은 검증하지 않았습니다. monitoring namespace도 먼저 있어야 합니다.

저장한 check-fleet.sh와 승인한 expected-nodes.json으로 ConfigMap manifest를 만든 뒤 아래 ServiceAccount/RBAC/CronJob과 함께 검토·적용합니다. ClusterRole은 모든 Node를 나열할 수 있습니다. label selector는 조회 필터이며 권한 경계가 아닙니다. ConfigMap 수정과 이 ServiceAccount로 Pod를 실행할 수 있는 namespace 사용자의 권한도 검토합니다.

```bash
: "${KUBE_CONTEXT:?Set the approved cluster context}"
kubectl --context "$KUBE_CONTEXT" -n monitoring create configmap hybrid-node-check \
  --from-file=check-fleet.sh --from-file=expected-nodes.json \
  --dry-run=client -o yaml > hybrid-node-check.yaml
# Review this manifest and the observer/RBAC manifest before applying either.
```
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: hybrid-node-observer
rules:
- apiGroups:
  - ''
  resources:
  - nodes
  verbs:
  - get
  - list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: hybrid-node-observer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: hybrid-node-observer
subjects:
- kind: ServiceAccount
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hybrid-node-observer
  namespace: monitoring
spec:
  schedule: '*/30 * * * *'
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 120
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      ttlSecondsAfterFinished: 1800
      template:
        spec:
          serviceAccountName: hybrid-node-observer
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            fsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: observer
            image: example.invalid/hybrid-observer:replace-with-reviewed-build
            command:
            - /bin/bash
            - /config/check-fleet.sh
            - /config/expected-nodes.json
            env:
            - name: TMPDIR
              value: /work
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            volumeMounts:
            - name: config
              mountPath: /config
              readOnly: true
            - name: work
              mountPath: /work
          volumes:
          - name: config
            configMap:
              name: hybrid-node-check
              defaultMode: 292
          - name: work
            emptyDir:
              sizeLimit: 64Mi
```

Job 실패뿐 아니라 **실행 누락·최근 성공 없음**에도 알립니다. 30분 주기로 즉각적인 장애 탐지를 보장할 수 없습니다. 알림은 관측 시스템의 보호된 연동을 사용합니다. Slack webhook bearer URL을 Pod 환경 변수에 넣거나 알림 전송 실패를 건강 상태 검증 성공으로 취급하지 않습니다.

### kubelet/containerd 상태 모니터링 (노드 레벨)

다음 root 소유 스크립트는 서비스를 재시작하지 않고 로컬 서비스 상태와 루트 파일시스템을 관찰합니다. kubelet/containerd/image 경로가 별도 마운트이면 추가 점검이 필요하며 루트 디스크 사용률만으로 충분하지 않습니다. 명령 실행 불가나 잘못된 측정값을 정상으로 처리하지 않습니다.

```bash
#!/usr/bin/env bash
# Observe local services/filesystem; do not restart anything automatically.
set -euo pipefail
failed=0
for service in kubelet containerd; do
  if ! systemctl is-active --quiet "$service"; then
    printf '%s is not active\n' "$service" >&2
    failed=1
  fi
done
usage=$(df --output=pcent / | tail -n 1 | tr -d ' %')
case "$usage" in ''|*[!0-9]*) echo 'Unknown filesystem usage' >&2; exit 1;; esac
if [ "$usage" -ge 90 ]; then
  printf 'Root filesystem usage: %s%%\n' "$usage" >&2
  failed=1
fi
exit "$failed"
```

검토한 호스트 관리 절차로 `/usr/local/bin/node-health-check.sh`에 실행 권한을 주어 설치하고 신뢰하지 않는 사용자가 수정하지 못하도록 합니다. timer/unit은 구성 예시이며 journal·failed unit 감시를 별도로 연결해야 합니다. `PrivateTmp`가 자격 증명을 로그에 남겨도 된다는 의미는 아닙니다.

```ini
[Unit]
Description=Periodic Hybrid Node local observation

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```
```ini
[Unit]
Description=Observe Hybrid Node local services and root filesystem

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/node-health-check.sh
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
```

특정 네트워크·자격 증명 문제를 진단할 때 운영자가 root 권한으로 `nodeadm debug -c file:///etc/eks/nodeconfig.yaml`을 별도로 실행할 수 있습니다. AWS와 클러스터에 접속하고 진단 문맥을 출력하므로 결과는 비공개로 보관합니다. 매 타이머마다 조용히 실행해 오류를 버리거나 장애별 판단 없이 kubelet/containerd를 자동 재시작하지 않습니다.

## 검증 범위와 근거

로컬 검증 범위는 예제 구문, 가상 Node/API 실패 사례와 합성 인증서 검사입니다. 실제 fleet 설치·호스트 업그레이드·credential rollover·Kubernetes admission·CNI/DNS/스토리지 시험이나 운영 SLO 달성을 입증하지 않습니다.

- [AWS Hybrid Nodes nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS Hybrid Nodes upgrades](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [SSM registration and activation lifetime](https://docs.aws.amazon.com/systems-manager/latest/userguide/hybrid-activation-managed-nodes.html)
- [IAM Roles Anywhere credential configuration](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [UpdateTrustAnchor input](https://docs.aws.amazon.com/botocore/latest/reference/services/rolesanywhere/client/update_trust_anchor.html)
- [Kubernetes version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Node pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Allocatable](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Graceful node shutdown](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/)
- [containerd configuration](https://github.com/containerd/containerd/blob/main/docs/cri/config.md)
- [Cilium 1.20.1 cluster-pool allocator](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool.rst)

---

< [이전: 워크로드 배치 전략](./06-workload-placement.md) | [목차](./README.md) | [다음: 운영 및 유지보수](./08-operations.md) >
