# 노드 부트스트랩

< [이전: 인터넷 제한 환경 구성](./03-airgap-setup.md) | [목차](./README.md) | [다음: GPU 서버 통합](./05-gpu-integration.md) >

> **지원 버전**: EKS Hybrid Nodes; nodeadm v1.0.20 소스 확인. 대상 클러스터에 지원되는 OS·Kubernetes·CNI 조합을 선택합니다.
> **마지막 업데이트**: 2026년 9월 12일

이 문서는 준비한 온프레미스 호스트를 EKS에 연결합니다. 소프트웨어 설치, AWS 신원, 초기화와 실제 워크로드 준비 확인을 구분합니다. 예제의 변경 작업에는 대상 클러스터·호스트 식별과 운영자 승인이 필요합니다. 로컬 검증은 운영 네트워크, OS 이미지, PKI 또는 워크로드를 시험했다는 증거가 아닙니다.

## 부트스트랩 흐름

1. [사전 요구 사항](./01-prerequisites.md)과 [네트워크 구성](./02-network-configuration.md)에 따라 지원 OS·런타임, 고유 호스트 신원, 시각 동기화, 라우팅, DNS와 방화벽을 준비합니다.
2. **Hybrid Nodes IAM 역할**, SSM 또는 IAM Roles Anywhere 공급자와 `HYBRID_LINUX` 타입 클러스터 액세스 항목을 준비합니다. 일반 SSM 관리 역할만으로 충분하지 않습니다.
3. Hybrid nodeadm 릴리스를 검증한 뒤 호스트 또는 통제된 OS 이미지 빌드에서 의존성을 설치합니다.
4. 정확히 한 공급자를 사용하는 보호된 노드별 NodeConfig를 전달합니다. 필요하면 프록시·레지스트리 신뢰를 구성합니다.
5. 식별한 호스트에서 `nodeadm config check` 후 `nodeadm init`을 실행합니다.
6. 지원 Hybrid CNI와 필요한 애드온을 구성합니다. 등록된 Node도 `NotReady`일 수 있습니다.
7. 정확한 Node 신원, Ready 조건, CNI/DNS, 자격 증명 갱신과 제한된 워크로드를 확인한 뒤 서비스에 투입합니다.

## nodeadm과 의존성 설치

Hybrid nodeadm은 EC2용 `amazon-eks-ami`가 아닌 **`aws/eks-hybrid`**에서 제공합니다. 오래된 SSM 서명 키 문제 때문에 SSM 신규 설치·업그레이드에는 **nodeadm 1.0.19 이상**이 필요합니다. 이 검토는 릴리스된 **v1.0.20 소스**를 사용했습니다.

승인한 릴리스를 HTTPS 검증과 함께 받고 독립적으로 승인한 기록의 다이제스트와 비교한 뒤 root로 실행합니다. 변경 가능한 `latest` 다운로드로 `/usr/local/bin/nodeadm`을 무조건 교체하지 않습니다. [인터넷 제한 환경 구성](./03-airgap-setup.md)은 이미지 준비와 확인한 릴리스의 private manifest 옵션을 다룹니다. 감사 환경에서 공식 아티팩트 호스트의 TLS 호스트명 검증이 실패한 뒤 nodeadm 바이너리를 받거나 실행하지 않았습니다.

```bash
# Target host/image builder: installs software. Choose exactly one provider.
set -euo pipefail
: "${KUBERNETES_VERSION:?Approved cluster-compatible version}"
: "${CREDENTIAL_PROVIDER:?ssm or iam-ra}" "${REGION:?}"
: "${CONTAINERD_SOURCE:?distro, docker or none for this OS}"
case "$CREDENTIAL_PROVIDER" in ssm|iam-ra) ;; *) exit 1 ;; esac
case "$CONTAINERD_SOURCE" in distro|docker|none) ;; *) exit 1 ;; esac
sudo nodeadm install "$KUBERNETES_VERSION" \
  --credential-provider "$CREDENTIAL_PROVIDER" \
  --containerd-source "$CONTAINERD_SOURCE" --region "$REGION" --timeout 20m
```

새 노드는 컨트롤 플레인의 현재 마이너 버전을 우선합니다. kubelet 지원 스큐는 호환성 허용 범위이며 오래되어 지원되지 않는 EKS 버전을 설치할 이유가 아닙니다. kubelet은 API 서버보다 새 버전일 수 없으며 업스트림 스큐 정책 외에 EKS·CNI 지원도 확인합니다.

RHEL은 `distro`를 지원하지 않습니다. 문서화된 Docker 패키지 소스나 호환 런타임 사전 설치 후 `none`을 사용합니다. AL2023은 `docker`를 지원하지 않습니다. `none`은 containerd 설치를 건너뜁니다. Private mode도 OS 패키지를 건너뛰므로 누락된 런타임 의존성을 제공하지 않습니다.

| 구성 요소 | 문서화된 설치 위치 |
|---|---|
| kubelet | `/usr/bin/kubelet` |
| kubectl | `/usr/local/bin/kubectl` |
| ECR credential provider | `/etc/eks/image-credential-provider/ecr-credential-provider` |
| AWS IAM authenticator / signing helper | `/usr/local/bin/aws-iam-authenticator` / `/usr/local/bin/aws_signing_helper` |
| SSM setup CLI | `/opt/ssm/ssm-setup-cli` |
| SSM Agent | Ubuntu snap: `/snap/amazon-ssm-agent/current/amazon-ssm-agent`; AL2023/RHEL: `/usr/bin/amazon-ssm-agent` |
| containerd | Ubuntu/AL2023: `/usr/bin/containerd`; RHEL 문서는 `/bin/containerd` 사용 |
| nodeadm tracker | `/opt/nodeadm/tracker` |

`nodeadm install`은 서명된 setup CLI로 SSM 에이전트를 설치·설정하며 **SSM 등록은 `init`에서 수행**합니다. 수동 `dpkg`와 다른 nodeadm 설치 프로그램을 조합하는 절차가 아닙니다.

## NodeConfig와 자격 증명

### SSM

클러스터 이름·리전과 준비한 Hybrid 역할에 대한 유효한 활성화 코드·ID를 제공합니다.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: REPLACE_WITH_ACTIVATION_CODE
      activationId: REPLACE_WITH_ACTIVATION_ID
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=workload.example.com/location=onprem
```

이는 입력 템플릿이며 실제 비밀을 커밋하는 예제가 아닙니다. root 소유·`0600`으로 보호하고 로그나 셸 기록에 값을 노출하지 않고 전달합니다. 클러스터 조회는 Hybrid 역할의 EKS 권한으로 API 엔드포인트와 CA를 가져옵니다. Base64 CA 필드에 넣은 원본 PEM 블록은 API 표현과 바꿔 쓸 수 없습니다.

`maxPods`와 종료 시간은 계획 예시이며 용량 보장이 아닙니다. CNI 할당·예약 IP, 리소스와 워크로드 종료 요구 사항을 확인합니다. 선택적인 `NoSchedule` taint에는 워크로드·CNI의 대응 toleration이 필요합니다. 필수 에이전트나 애플리케이션을 조용히 막는 기본 taint를 추가하지 않습니다.

활성화는 자격 증명 소유자를 통해 준비한 Hybrid 역할, 올바른 리전, 명시적인 만료 시각과 제한된 등록 수로 생성합니다. 코드를 출력하기보다 응답을 비공개 파일에 저장합니다.

```bash
# AWS write: owner-approved activation for one new host.
set -euo pipefail
umask 077
: "${REGION:?}" "${HYBRID_ROLE_NAME:?Prepared Hybrid Nodes IAM role name}"
: "${ACTIVATION_EXPIRY:?Future UTC timestamp within SSM service limits}"
test ! -e activation.json
aws ssm create-activation --region "$REGION" \
  --iam-role "$HYBRID_ROLE_NAME" --registration-limit 1 \
  --expiration-date "$ACTIVATION_EXPIRY" \
  --default-instance-name eks-hybrid-node > activation.json
```

실패했거나 결과를 알 수 없는 요청을 무조건 다시 생성하지 말고 자격 증명 소유자와 확인합니다. SSM은 등록된 `mi-*` 관리형 인스턴스 ID를 Node 이름으로 사용합니다. 일반 재부팅에서는 SSM 등록과 갱신되는 임시 자격 증명을 재사용합니다. 재등록에는 만료되지 않았고 등록 여유가 남은 활성화가 필요하며, 한도뿐 아니라 만료 시각도 중요합니다.

### IAM Roles Anywhere

[사전 요구 사항](./01-prerequisites.md)에서 준비한 trust anchor, 활성 프로필, Hybrid 역할과 노드별 인증서·키를 사용합니다. 이 문서를 실행할 때마다 trust anchor·프로필을 추가 생성하지 않습니다.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_ID
      roleArn: arn:aws:iam::111122223333:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

경로는 예시이며 여러 머신에서 인증서 하나를 재사용하라는 의미가 아닙니다. `nodeName`을 역할 신뢰 정책의 인증서 속성과 결합합니다. 일반적인 CN 조건에서는 두 값이 일치해야 합니다. 이름은 노드 명명 규칙을 따르고 최대 64자여야 합니다. 프로필의 **`acceptRoleSessionName: true`**를 활성화합니다.

역할 최대값을 12시간으로 설정하는 것만으로 세션이 늘어나지 않습니다. 요청·프로필의 유효 세션 시간은 역할 `MaxSessionDuration` 이하여야 하며 같은 값도 허용됩니다. 보안·가용성 요구 사항에 맞게 선택하고 갱신을 확인합니다. 정적 IAM 사용자 액세스 키는 세 번째 Hybrid nodeadm 지원 공급자가 아닙니다.

## 프라이빗 레지스트리 신뢰

내부 레지스트리 소유자를 통해 CA 지문과 인증서 호스트명을 확인합니다. 적절한 경우 레지스트리 범위 신뢰를 우선합니다. 서버가 제시한 임의 인증서를 전역 신뢰에 추가하거나 호스트명 검증을 끄지 않습니다.

승인한 레지스트리의 `hosts.toml` 예제:

```toml
# /etc/containerd/certs.d/registry.internal.example.com/hosts.toml
server = "https://registry.internal.example.com"

[host."https://registry.internal.example.com"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/registry.internal.example.com/ca.crt"
```

대응하는 검토된 CA 파일이 각 노드에 있어야 합니다. containerd 1.x에서는 `config_path`가 `plugins."io.containerd.grpc.v1.cri".registry` 아래에, containerd 2.x/config version 3에서는 `plugins."io.containerd.cri.v1.images".registry` 아래에 위치합니다. nodeadm이 생성한 `/etc/containerd/config.toml`을 확인하고 설치한 런타임에 맞는 절을 사용합니다. 폐기 예정 inline registry `configs/auth`와 `config_path` 방식을 섞거나 NodeConfig에 레지스트리 비밀번호를 넣지 않습니다.

조직에 시스템 전체 CA 신뢰가 필요하면 Ubuntu는 `/usr/local/share/ca-certificates/`와 `update-ca-certificates`, RHEL/AL2023은 `/etc/pki/ca-trust/source/anchors/`와 `update-ca-trust extract`를 사용합니다. RHEL 예제에서 Ubuntu 경로를 참조하지 않습니다. 일반 ECR 인증서는 공인 신뢰를 사용하지만 OS에 정상 CA bundle은 필요합니다. 레지스트리 신뢰와 인증은 별개입니다.

## 초기화와 확인

```bash
# Identified target host; init changes local configuration and joins EKS.
set -euo pipefail
sudo nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml
sudo nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
```

프라이빗 manifest 설치에서는 [인터넷 제한 환경 구성](./03-airgap-setup.md)에 따라 `init`에 승인한 `--manifest-override`와 `--private-mode`를 전달합니다. 실제 nodeadm·데몬 프로세스에 프록시 설정이 전달되어야 합니다. `config check`는 로컬 설정 검사이며 전체 조인 시험이 아닙니다.

**클러스터 관리자** 워크스테이션에서 의도한 kubeconfig context와 정확한 예상 Node 이름(SSM `mi-*` 또는 승인한 IAM Roles Anywhere 이름)을 확인합니다.

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${EXPECTED_NODE_NAME:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o json > node-registration.json
jq -e '.metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid"
  and (.metadata.uid | type == "string" and length > 0)' node-registration.json
expected_uid=$(jq -er '.metadata.uid' node-registration.json)
# After CNI and required add-ons are ready:
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" wait \
  --for=condition=Ready "node/$EXPECTED_NODE_NAME" --timeout=5m
observed_uid=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o jsonpath='{.metadata.uid}')
test "$observed_uid" = "$expected_uid"
```

Node UID를 기록하고 provider·주소를 식별한 물리·가상 호스트와 대조합니다. Ready는 필요 조건이며 DNS, 이미지 풀, 연결, 자격 증명 갱신과 실제 요구 워크로드도 검증합니다. 이전 `v1.31.0` 출력은 역사적 예시이며 새 등록 실측이 아닙니다.

## 사전 설치 호스트용 systemd 자동화

통제된 빌드·설치 단계에서 `nodeadm install`로 소프트웨어를 준비합니다. 아래 자동화는 **초기화만** 실행하고 machine ID, 승인 nodeadm 바이너리, NodeConfig와 선택적 프라이빗 manifest에 결합된 기록을 남깁니다. 변경되었거나 부분 초기화된 상태를 거부하며 등록을 조용히 반복하지 않습니다. 등록 상태, machine ID, 키나 이 상태 디렉터리를 다른 노드로 복제하지 않습니다.

root 소유 `/etc/eks/bootstrap.env` 예제(`0600`):

```text
NODECONFIG_PATH=/etc/eks/nodeconfig.yaml
APPROVED_NODEADM_SHA256=REPLACE_WITH_APPROVED_64_HEX_DIGEST
# Only for the reviewed private-manifest path:
# LOCAL_MANIFEST=/etc/eks/manifest.json
```

아래 스크립트를 root 소유 `/usr/local/bin/eks-hybrid-bootstrap.sh`로 저장합니다. 보호된 상위 디렉터리·파일은 호스트 소유자가 관리해야 하며 악의적인 root에 대한 방어를 제공하는 예제가 아닙니다.

```bash
#!/usr/bin/env bash
# Initialize one preinstalled, uniquely identified host. Run as root.
set -euo pipefail
umask 077
[[ "$EUID" -eq 0 ]]
: "${NODECONFIG_PATH:?Absolute per-node config path}"
: "${APPROVED_NODEADM_SHA256:?Hash from the approved binary record}"
[[ "$NODECONFIG_PATH" = /* ]]
[[ "$APPROVED_NODEADM_SHA256" =~ ^[0-9a-f]{64}$ ]]
NODEADM=/usr/local/bin/nodeadm
STATE=/var/lib/eks-hybrid-bootstrap

private_file() {
  local path=$1 owner mode
  [[ -f "$path" && ! -L "$path" ]]
  owner=$(stat -c '%u' "$path")
  mode=$(stat -c '%a' "$path")
  [[ "$owner" == 0 && "$mode" == 600 ]]
}

private_file "$NODECONFIG_PATH"
test -s /etc/machine-id
test -s /opt/nodeadm/tracker
test -x "$NODEADM"
actual=$(sha256sum "$NODEADM")
[[ "${actual%% *}" == "$APPROVED_NODEADM_SHA256" ]]
if [[ -e /var/lib/eks/.nodeadm-installed || -e /var/lib/eks/.nodeadm-initialized ]]; then
  echo 'Legacy markers found: review existing installation and migrate state manually.' >&2
  exit 1
fi
[[ ! -L "$STATE" ]]
mkdir -p -m 700 "$STATE"
[[ "$(stat -c '%u:%a' "$STATE")" == 0:700 ]]
exec 9>"$STATE/lock"
flock -n 9

args=(--config-source "file://$NODECONFIG_PATH")
fingerprint_inputs=(/etc/machine-id "$NODEADM" "$NODECONFIG_PATH")
if [[ -n "${LOCAL_MANIFEST:-}" ]]; then
  [[ "$LOCAL_MANIFEST" = /* ]]
  private_file "$LOCAL_MANIFEST"
  fingerprint_inputs+=("$LOCAL_MANIFEST")
  args+=(--manifest-override "file://$LOCAL_MANIFEST" --private-mode)
fi
fingerprint=$(sha256sum "${fingerprint_inputs[@]}" | sha256sum)
fingerprint=${fingerprint%% *}
if [[ -e "$STATE/state" ]]; then
  private_file "$STATE/state"
  if [[ "$(cat "$STATE/state")" == "$fingerprint init-command-completed" ]]; then
    echo 'Matching initialization record; verify current Node readiness separately.'
    exit 0
  fi
  echo 'Changed identity/config or incomplete initialization: manual recovery required.' >&2
  exit 1
fi

"$NODEADM" config check --config-source "file://$NODECONFIG_PATH"
printf '%s started\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
# Failure/interruption retains started state and prevents an automatic retry.
"$NODEADM" init "${args[@]}"
systemctl is-active --quiet containerd
systemctl is-active --quiet kubelet
printf '%s init-command-completed\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
echo 'Init command completed; cluster registration/CNI/readiness still require verification.'
```

상태 기록은 init 명령이 완료되고 그 시점에 두 로컬 서비스가 active였음을 뜻합니다. **Kubernetes Node가 Ready라는 뜻은 아닙니다.** 실패하면 `started` 기록이 남습니다. 운영자가 기록을 정리하기 전에 실제 호스트·SSM·클러스터 상태를 조사합니다. 서비스 시간 초과나 명령 중단이 등록되지 않았다는 증거는 아닙니다.

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=Initialize one prepared EKS Hybrid Node
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
TimeoutStartSec=10min
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

호스트 구성 소유자를 통해 설치·활성화합니다. `network-online.target`은 네트워크 관리자의 wait 서비스 기준 부팅 순서이며 DNS, VPN, EKS나 자격 증명 서비스 접근을 보장하지 않습니다. `RemainAfterExit`는 서비스 상태 기록이며 노드 상태가 아닙니다. `EnvironmentFile`은 systemd가 파싱하며 스크립트가 셸 `source`로 실행하지 않습니다.

기존 마커 전용 설치는 명시적으로 마이그레이션합니다. `.nodeadm-installed` / `.nodeadm-initialized` 삭제 후 재부팅만으로 초기화하지 않습니다. Credentials file 활성화와 같은 승인된 설정 변경에는 문서화된 유지보수·init 절차를 사용하고 이후 자동화 기록을 맞춥니다.

일반 재부팅에서는 구성된 kubelet·자격 증명 서비스가 재개됩니다. Kubernetes Node 객체 삭제는 SSM 등록 취소나 kubelet 중지가 아닙니다. 실행 중이고 권한이 유효한 kubelet은 Node를 다시 생성할 수 있습니다. `delete node`를 호스트 폐기로 사용하거나 모든 장애 호스트가 반드시 다시 조인한다고 가정하지 않습니다.

## Cilium CNI

AWS는 현재 자체 유지 관리 **Cilium 1.17.x와 1.18.x** 빌드를 Hybrid Nodes에서 지원합니다. `oci://public.ecr.aws/eks/cilium/cilium`의 게시 예제에는 `1.17.9-0`, `1.18.3-0`이 있습니다. 임의의 더 새로운 업스트림 차트를 선택하라는 의미가 아닙니다.

현재 AWS CNI 페이지는 커널 요구 사항 때문에 **Cilium v1.18.3에서 Ubuntu 20.04와 RHEL 8을 명시적으로 제외**합니다. 커널만 바꾸면 AWS 지원이 성립한다고 주장하지 말고 문서화된 행렬 안의 OS·CNI 조합을 선택합니다.

Calico 예제는 `aws-samples/eks-hybrid-examples`로 이동했습니다. Calico 프로젝트 폐기나 기존 모든 배포의 계속 동작을 보장하는 의미가 아닙니다. 현재 전용 AWS CNI 지원 페이지는 AWS 유지 관리 Cilium 빌드와 지원 기능을 명시합니다.

### 설치 값

이 IPv4 cluster-pool 예제는 검토한 원격 Pod 네트워크가 `10.85.0.0/16`이며 Node/VPC/Service 네트워크와 겹치지 않는다고 가정합니다. **최초 설치 전** 클러스터의 승인한 값으로 바꿉니다.

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: eks.amazonaws.com/compute-type
              operator: In
              values: [hybrid]
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList: [10.85.0.0/16]
loadBalancer:
  serviceTopology: true
operator:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: In
                values: [hybrid]
  unmanagedPodWatcher:
    restart: false
envoy:
  enabled: false
kubeProxyReplacement: "false"
preflight:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
```

Preflight selector는 agent affinity와 별개입니다. `/25`에는 주소 128개가 있지만 Cilium cluster-pool은 2개를 예약하므로 사용 가능한 Pod 주소 128개를 보장하지 않습니다. kubelet `maxPods`, hostNetwork Pod와 다른 제약도 함께 검토합니다.

기존 pool 항목이나 `clusterPoolIPv4MaskSize`를 수정하지 않습니다. Cilium은 새 pool 항목 **추가**로 확장하는 방식을 문서화합니다. 먼저 EKS remote network, 라우팅/BGP, 겹침과 용량을 검토합니다. “목록 전체를 절대 확장할 수 없다”는 표현은 지나치게 강합니다.

```bash
# Cluster write; requires approved context, values and supported chart.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${CILIUM_VERSION:?Approved AWS chart version}"
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version "$CILIUM_VERSION" --namespace kube-system \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values cilium-values.yaml --wait --timeout 10m
```

대상 Hybrid Node마다 Cilium agent가 있는지와 operator, Node readiness, 노드 간 트래픽을 확인합니다. Affinity는 이 설치를 Hybrid Node로 한정하며 클라우드 노드 네트워킹은 기존 컨트롤러가 관리합니다. kube-proxy replacement 설계에는 별도 API 접근·마이그레이션 계획이 필요하며 같은 노드에 경쟁하는 kube-proxy 동작을 남기지 않습니다.

### 업그레이드와 제거 경계

Cilium 업그레이드 전에 현재 values·manifest와 명시적인 Helm revision을 저장하고, 버전별 업그레이드 문서를 읽고, 승인한 값으로 대상 차트를 렌더링합니다. Hybrid Node로 한정한 **별도 preflight 릴리스**를 `preflight.enabled=true`, `agent=false`, `operator.enabled=false`로 실행합니다. DaemonSet 대상 커버리지와 검증 Deployment readiness를 **모두** 기다립니다. Preflight 릴리스 생성은 검사 결과가 아닙니다.

통과한 뒤 그 preflight 릴리스만 제거합니다. 검토한 기존 값과 적절한 `upgradeCompatibility`로 업그레이드합니다. `--reuse-values`로 오래된 설정을 마이너 버전 사이에 무조건 넘기지 않습니다. 롤백은 명시적으로 확인한 revision과 CNI 상태·CRD 호환성 검토가 필요하며 데이터 경로 복구를 자동 보장하지 않습니다.

CNI 제거는 중단이 발생하는 폐기·마이그레이션 작업입니다. 워크로드를 이동하고 Cilium에 의존하는 노드·정책·CR을 확인합니다. 공유 클러스터에서 `kubectl get crds | grep cilium | xargs kubectl delete`를 실행하지 않습니다. Helm uninstall은 호스트 라우트·인터페이스·BPF 상태 제거를 보장하지 않습니다. 식별하고 비운 호스트에서 버전별 CNI 정리 절차를 사용하며 경로 삭제 전 활성 mount와 보존 데이터를 확인합니다.

## Bottlerocket은 별도 부트스트랩 계약 사용

AWS는 **1.37.0**부터 지원 x86_64 Kubernetes variant와 사전 요구 사항을 갖춘 VMware Bottlerocket을 지원합니다. nodeadm을 **사용하지 않습니다**. AWS 가이드는 Kubernetes/AWS 설정과 **`eks-hybrid-setup` bootstrap container**를 구성합니다. 이전 `[settings.hybrid.ssm]`, `[settings.hybrid.iam-roles-anywhere]` 예제는 문서화된 설정 계약이 아닙니다.

[Bottlerocket Hybrid Node 연결](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html)의 선택 공급자용 전체 설정을 사용합니다. 공통 필드 예제:

```toml
# Common fragment only: combine with the provider-specific settings from AWS.
[settings.kubernetes]
cluster-name = "my-hybrid-cluster"
api-server = "https://REPLACE_WITH_CLUSTER_ENDPOINT"
cluster-certificate = "REPLACE_WITH_BASE64_CLUSTER_CA"
hostname-override = "hybrid-node-001"
provider-id = "eks-hybrid:///ap-northeast-2/my-hybrid-cluster/hybrid-node-001"
authentication-mode = "aws"
cloud-provider = ""
server-tls-bootstrap = true

[settings.network]
hostname = "hybrid-node-001"

[settings.aws]
region = "ap-northeast-2"

[settings.kubernetes.node-labels]
"eks.amazonaws.com/compute-type" = "hybrid"

[settings.bootstrap-containers.eks-hybrid-setup]
mode = "always"
user-data = "REPLACE_WITH_BASE64_PROVIDER_BOOTSTRAP_INPUT"
```

이 조각은 완성된 부팅 설정이 아닙니다. SSM 공급자는 `eks-hybrid-ssm-setup` 활성화·리전 입력을 제공하고 등록 후 Node 이름은 `mi-*`로 바뀝니다. IAM Roles Anywhere는 `eks-hybrid-iam-ra-setup` 인증서·키 입력과 인증서 정책에 role-session-name을 결합한 AWS credential-process 설정을 제공합니다. 문서화된 ECR provider와 공급자별 노드 label·설정도 포함합니다.

Base64는 암호화가 아닌 인코딩입니다. 공급자 bootstrap data에는 활성화 비밀이나 개인 키가 들어갈 수 있으므로 VM 구성, guestinfo, 관리 권한과 진단 내보내기를 보호하고 공개 저장소·로그에 넣지 않습니다. Admin-container SSH는 선택 사항이며 별도 승인이 필요합니다. 이미 등록한 VM을 깨끗한 템플릿으로 복제하지 않습니다.

첫 전원 켜기 전에 승인한 **새로 준비한 전원 꺼진 VM**을 구성합니다. AWS 가이드는 `settings.toml`을 base64 인코딩하고 `guestinfo.userdata.encoding=base64`를 사용합니다. 평문 base64를 `gzip+base64`로 표시하지 않습니다. 배포할 govc/VMware 버전, datastore, 네트워크, 템플릿 소유권과 비밀 전달 경로를 확인한 뒤 프로비저닝합니다. 이번 감사에서 VMware 배포는 실행하지 않았습니다.

## 애드온 배치와 Pod Identity

API 서버 트래픽이 실제 webhook·aggregated API listener에 도달하도록 구성합니다. Hybrid Pod CIDR에 접근할 수 없으면 **웹훅 서버·operator**를 접근 가능한 클라우드 노드에 두거나 지원되는 적절한 hostNetwork 구성을 검증합니다. 모든 CloudWatch/ADOT 에이전트나 애플리케이션 Pod를 클라우드에 둬야 한다는 뜻은 아닙니다.

클라우드 노드 배치는 명시적으로 검토한 node label·affinity를 사용하고 용량·taint를 확인합니다. `NotIn [hybrid]`는 label이 없는 노드도 선택할 수 있으므로 승인한 EC2 대상이라는 증거가 아닙니다.

AWS는 혼합 클라우드/Hybrid 클러스터에서 양쪽에 CoreDNS 최소 1개를 권고합니다. 레플리카 4개와 soft spread만으로 각 2개를 보장하지 않습니다. [네트워크 구성](./02-network-configuration.md)의 배치·Service Traffic Distribution 절차를 적용하고 확인합니다.

| 노드 OS | Pod Identity 준비 |
|---|---|
| Ubuntu/RHEL/AL2023 | `spec.hybrid.enableCredentialsFile: true` 후 문서화된 `nodeadm init`; 에이전트 구성에서 `daemonsets.hybrid.create` 활성화 |
| Bottlerocket | OS **1.39.0 이상**; 공급자 bootstrap 명령의 `--enable-credentials-file=true`; `daemonsets.hybrid-bottlerocket.create` 활성화 |

호환성 최소값은 일반 OS 에이전트 **v1.3.3-eksbuild.1**, Bottlerocket **v1.3.7-eksbuild.2**이며 현재 설치 대상 버전이 아닙니다. 클러스터와 현재 호환되는 애드온 버전·설정 스키마를 선택합니다. 임시 자격 증명 mount 위치는 일반 `/eks-hybrid/.aws/credentials`, Bottlerocket `/var/eks-hybrid/.aws/credentials`로 다릅니다.

프라이빗 배포에는 `eks-auth` 서비스 경로, 노드 역할의 `eks-auth:AssumeRoleForPodIdentity` 권한과 워크로드별 Pod Identity association·신뢰·권한이 필요합니다. 에이전트 설치만으로 충분하지 않습니다. 애드온 소유자를 통해 필요한 DaemonSet 설정을 병합하고 기존 애드온에 무조건 `create-addon`을 실행하지 않습니다.

## 업그레이드, 복구와 제거

기존 노드를 비우기 전에 대체 용량을 추가하고 **초기화·검증을 완료**하는 방식을 우선합니다. 새 호스트에 바이너리만 설치해도 클러스터 용량이 늘어나지는 않습니다. DNS 가용성을 유지하고 “복원력”을 이유로 기존 CoreDNS 4개를 무조건 2개로 줄이지 않습니다.

식별한 기존 노드 하나에 대해 context, Node UID, 호스트 매핑과 워크로드·데이터 소유권을 확인합니다. Cordon 후 시간 제한을 둔 drain을 수행하고 PDB·eviction 오류가 있으면 중단합니다. `--delete-emptydir-data`는 로컬 emptyDir 손실을 명시적으로 허용하며 기본 안전 옵션이 아닙니다. 관리되지 않는 Pod, 로컬 영구 데이터와 DaemonSet은 별도 처리합니다. 막힌 drain을 성공처럼 만들려고 `--force`나 eviction 비활성화를 사용하지 않습니다.

인플레이스 업데이트는 비운 호스트에서 문서화된 `nodeadm upgrade`를 실행하고, 신원·소프트웨어 버전·Ready/CNI/DNS·워크로드를 확인한 뒤 uncordon합니다. 중단 작업이며 여유 용량이 없다는 이유로 안전해지지 않습니다.

폐기 시 자동 bootstrap·재조인 경로를 중지하고 nodeadm 제거와 공급자 등록 취소를 완료한 뒤 정확한 Node 객체를 제거하며 CNI 잔여 리소스는 소유자를 통해 정리합니다. 필요한 복구 증거는 비공개로 보존합니다.

`nodeadm uninstall`은 `kubectl drain`이나 `kubectl delete node`가 아닙니다. 기본적으로 남은 워크로드 Pod가 있으면 거부하며 모든 CNI·애드온 아티팩트를 제거하지 않습니다. **v1.0.9부터 문서화된 force/skip 제거 경로에서도 `/var/lib/kubelet`을 삭제하지 않습니다.** Mount 경로를 통해 호스트 파일시스템이 노출될 수 있기 때문입니다. `--force`는 추가 기본 CNI/Kubernetes 경로를 제거하는 옵션이며 “확인 생략 후 모두 삭제”가 아닙니다. 수동 제거 전에 mount·데이터를 조사합니다.

제거 후 실제 재설치를 승인했다면 유효한 자격 증명으로 **install → config check → init**을 다시 실행하고 자동화 기록을 맞춥니다. 인증 오류, 기존 프로필이나 부분 init만으로 운영 노드를 제거하지 않습니다.

## 문제 해결

| 관찰 사항 | 상태 변경 전 조사 |
|---|---|
| 오래된 nodeadm의 SSM 설치 서명 실패 | 승인 nodeadm이 최소 1.0.19인지 확인. 서명 검사 우회 금지 |
| 패키지 관리자·다운로드 실패 | 실제 저장소 접근, 프록시, CA 신뢰, 패키지 잠금, 지원 OS·런타임과 오류 확인. `dnf update`는 시스템 업그레이드이며 진단이 아님 |
| 시간 초과 | 실패 단계와 연결 확인. 시간 제한 증가만으로 해결되지 않음 |
| remote network 밖의 Node IP | 실제 IP와 EKS remote-node CIDR |
| API 접근 불가 / Unauthorized | DNS·라우팅·443·반환 경로, 의도한 Hybrid 역할, 신뢰·자격 증명 유효성, `HYBRID_LINUX` 액세스 항목 |
| NotReady | CNI·에이전트 로그, 선택 데이터 경로 포트, 런타임, 디스크·리소스 조건. 항상 CNI 누락인 것은 아님 |
| 이미지 풀 / x509 오류 | 정확한 이미지·인증 경로, ECR API/DKR/S3, 레지스트리 CA·호스트명. TLS 검증 유지 |
| 활성화 / 토큰 만료 | 활성화 만료·용량·리전과 실행 에이전트의 갱신·시각 동기화·AWS 접근 구분. 재시작은 보장된 해결책이 아님 |
| 기존 Hybrid 프로필 / 부분 init | 실제 nodeadm·공급자 상태와 의도한 클러스터 조사. 증거 보존, 자동 uninstall 금지 |

```bash
# Private diagnostic output on the identified node; no nonexistent nodeadm status.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet --since '-15 min' --lines 200 --no-pager
sudo nodeadm debug --config-source file:///etc/eks/nodeconfig.yaml
```

`nodeadm debug`는 AWS·클러스터 읽기와 자격 증명 검사를 수행합니다. 출력을 비공개로 보관하고 공유 전에 정제합니다. `sudo aws sts get-caller-identity`는 다른 root·관리자 자격 증명 경로를 사용할 수 있어 kubelet이 사용하는 신원을 증명하지 않습니다. TLS 검증으로 `curl -k`를 사용하지 않습니다. 서버 CA 신뢰와 kubelet 클라이언트 인증서 승인·발급도 별개입니다.

## 공식 참고 자료

- [Hybrid nodeadm 명령·파일 위치·제거 동작](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Hybrid 자격 증명](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [IAM Roles Anywhere CreateSession 시간](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [SSM CreateActivation](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html)
- [AWS Hybrid CNI 지원·수명 주기](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium cluster-pool 확장](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/concepts/ipam/cluster-pool.rst)
- [Bottlerocket Hybrid 부트스트랩](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html)
- [Hybrid 애드온·Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [containerd 레지스트리 호스트 구성](https://github.com/containerd/containerd/blob/v2.2.0/docs/hosts.md)
- [systemd network-online 의미](https://systemd.io/NETWORK_ONLINE/)
- [Kubernetes 버전 스큐](https://kubernetes.io/releases/version-skew-policy/)

< [이전: 인터넷 제한 환경 구성](./03-airgap-setup.md) | [목차](./README.md) | [다음: GPU 서버 통합](./05-gpu-integration.md) >
