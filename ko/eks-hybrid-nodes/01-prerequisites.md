# 사전 요구 사항

> **지원 버전**: 예제 검토 기준 EKS 1.36 / hybrid nodeadm 1.0.20; OS별 조건은 아래 참조
> **마지막 업데이트**: 2026년 9월 13일

Hybrid node join 전에 host·network·credential·cluster access를 준비합니다. 로컬 schema/crypto/input 검사는 실제 물리 네트워크·GPU runtime·프로덕션 cluster 검증이 아닙니다. 이번 감사에서 cloud·host network·GPU driver·image build 변경은 실행하지 않았습니다.

![Hybrid 사전 조건과 VPC/on-prem 양방향 routing. Remote CIDR 선언만으로 모든 route/firewall rule이 생성되지는 않는다.](../.gitbook/assets/ko-eks-hybrid-nodes-prereq-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-hybrid-nodes-prereq-0.html)

## OS와 Runtime

| AWS가 검증하는 hybrid 통합 | 버전/범위 |
|---------------------------|-----------|
| Ubuntu | 20.04·22.04·24.04; 배포판 security maintenance도 별도 검토 |
| RHEL | 8·9; kernel/CNI·Red Hat 구독/지원 검토 |
| AL2023 | On-prem **가상화** 환경; 일반 bare metal이나 EC2 밖 AWS OS 지원 권리가 아님 |
| Bottlerocket | VMware 변형 v1.37.0+, Kubernetes 1.28+용, **x86_64만** 제공; 별도 bootstrap 절차 |

위 기준이 오래된 Kubernetes 릴리스의 현재 EKS 지원을 뜻하지는 않습니다. 현재 지원되는 EKS·OS/runtime/CNI 조합을 고르세요. AWS는 Ubuntu/RHEL의 hybrid 통합을 지원하며 vendor OS 유지보수 자체를 대신하지 않습니다.

SSM 신규 설치/upgrade에는 **nodeadm 1.0.19+**가 필요합니다. 이전 binary에는 오래된 SSM signing key가 있습니다. 검토한 릴리스는 **v1.0.20**이며, EC2 EKS AMI의 동명 도구가 아닌 hybrid nodeadm을 사용합니다.

ARM의 EKS kube-proxy 1.31+에는 ARMv8.2+crypto가 필요합니다. Pi 5 이전/Cortex-A72는 충족하지 못하지만 Pi 5 CPU만으로 전체 stack이 검증되지는 않습니다. 이전 kube-proxy 1.30 workaround는 2026년 7월 EKS extended support가 종료됐습니다.

Containerd는 필요하지만 Docker Engine은 필수가 아닙니다. “containerd 1.6+”나 Docker 버전 확인만으로 현재 CRI 호환성이 입증되지는 않습니다.

| OS/선택 | nodeadm containerd source |
|---------|---------------------------|
| Ubuntu/AL2023 | 기본 지원 source는 `distro` |
| RHEL | `docker` 또는 호환 runtime 사전 설치 후 `none`; `distro`는 무효 |
| AL2023 | `docker`는 미지원 |
| 수동 runtime 설치 | `none`은 설치 생략이며 runtime 제공이 아님 |

Ubuntu 24.04의 과거 Pod 종료/AppArmor 수정에는 containerd 1.7.19+ 또는 적절한 AppArmor 갱신이 필요했습니다. 오래된 버전 설치 권장이 아닙니다. 선택한 CNI의 kernel 요구도 검토하며 “kernel 5.4+”나 무조건적 kernel 교체만으로 해결하지 마세요.

### 용량과 Host 확인

AWS는 **1 vCPU/1 GiB RAM 이상**을 권장하면서 엄격한 보편적 최소값은 없다고 설명합니다. OS/runtime/CNI/agent·image/log·실제 workload 용량을 추가해야 합니다. 이전 퀴즈의 2-core/2GB 최소값은 일치하지 않았습니다.

이전 disk 20/50/100GB, CPU 2/4-core, RAM 4/8GB는 계획 예시이며 검증된 workload 크기가 아닙니다.

```bash
# Run these read-only checks on the intended hybrid host.
cat /etc/os-release
uname -m
uname -r
free -h
df -h /
swapon --show
ip -j link show
# When already installed, inspect the actual CRI runtime:
containerd --version
```

Binary 버전이 kubelet의 실제 runtime socket을 입증하지는 않습니다. Swap·cgroup·forwarding·CNI module·firewall은 host owner 절차로 검토합니다. Blanket swapoff/fstab/sysctl/MTU 변경은 모든 지원 host에 이식 가능한 절차가 아닙니다.

### Install·검증·init 순서

준비된 Ubuntu/AL2023 host에서는 join 전에 의존성을 설치합니다. RHEL은 앞 표의 runtime source를 사용하며 Bottlerocket은 다른 경로를 사용합니다.

```bash
set -euo pipefail
# Installation/bootstrap sequence for prepared Ubuntu/AL2023 hosts.
# RHEL requires --containerd-source docker, or none with a preinstalled compatible runtime.
# These commands mutate the host; review OS/runtime/network/identity first.
sudo nodeadm install 1.36 --credential-provider ssm --containerd-source distro \
  --region ap-northeast-2 --timeout 20m
sudo nodeadm config check -c file:///etc/eks/nodeConfig.yaml
sudo nodeadm init -c file:///etc/eks/nodeConfig.yaml
```

Node config에 대상 cluster/provider 입력이 있어야 합니다. Credential이 있는 config는 mode 0600으로 보호하고 activation code를 golden image·log에 넣지 마세요. 이 명령은 host를 변경합니다. 실패를 숨기려고 validation phase를 건너뛰지 마세요. `nodeadm upgrade`는 disruptive 작업이며 workload를 먼저 이동해야 합니다.

## Packer Image 준비

AWS 예제는 Ubuntu 22.04/24.04·RHEL 8/9와 vSphere OVA·QEMU qcow2/raw target을 제공합니다. 검토한 **v1.0.20 template은 EKS 1.36에서 바로 실행할 image pipeline이 아닙니다.**

- `K8S_VERSION` validation이 아직 1.26–1.31만 허용합니다. 검토한 current fork를 유지하고 template 때문에 버전을 낮추지 마세요.
- `NODEADM_ARCH`는 **`amd` 또는 `arm`** 뒤에 `64`를 붙입니다. 이전 `amd64`는 `amd6464`가 됩니다.
- Packer의 `CREDENTIAL_PROVIDER=iam`은 nodeadm의 **`iam-ra`**로 변환됩니다.
- 실제 파일은 `hybrid-nodes-template.pkr.hcl`이며 `general-build.qemu.al2023` source는 없습니다.
- Mutable `releases/latest` 다운로드, vSphere `insecure_connection=true`, 기본 build password와 전역 변수 요구를 검토합니다. RHEL provisioner의 x86 repository는 고정돼 있어 binary 아키텍처만 바꿔도 ARM build가 되지는 않습니다.

| 입력 그룹 | 검토 사항 |
|-----------|-----------|
| 도구 | Packer ≥1.11, vSphere plugin ≥1.4 또는 QEMU 1.x; 검증한 조합 고정 |
| 공통 | `ISO_URL`, 검증한 `ISO_CHECKSUM`, `PKR_SSH_PASSWORD`, `K8S_VERSION`, `NODEADM_ARCH`, `CREDENTIAL_PROVIDER` |
| RHEL | `RH_USERNAME`, `RH_PASSWORD`, `RHEL_VERSION`; 최종 image/log에서 secret 제외 |
| vSphere | Server/user/password, datacenter, cluster, datastore, network, **VSPHERE_OUTPUT_FOLDER** |
| QEMU | **PACKER_OUTPUT_FORMAT** (`qcow2`/`raw`), CPU/가상화 호환성 |

소스에는 유료 AWS AMI builder도 있으며 cloud machine을 hybrid node로 운영하는 지원과는 별개입니다. 유지보수한 template과 결과 image를 검증하세요. 이번 감사에서는 Packer/VM build를 실행하지 않았습니다.

## GPU 호환성

GPU variant·CPU 아키텍처·OS/kernel·지원 NVIDIA driver·container toolkit/runtime·CUDA/framework image·memory를 함께 확인합니다. 이전 driver 525/535/545/550, CUDA 11.8/12.x는 과거 최소값·권장값이 섞여 있으며 보편적인 현재 Hybrid Nodes 요구가 아닙니다.

H100 80GB·H200 141GB·A100 40/80GB·L40S 48GB는 일부 variant 예시이며 전체 인증 목록이 아닙니다. 모든 model에 4GB 최소값을 적용할 수도 없습니다. 올바른 GPU container 실행만을 위해 host CUDA compiler가 필수는 아니고 driver·compiler 버전의 의미도 다릅니다.

```bash
# On a host where the driver is already installed:
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
# Optional: nvcc reports the locally installed compiler, if present.
if command -v nvcc >/dev/null 2>&1; then nvcc --version; fi
```

선택한 조합의 현재 NVIDIA 호환성/platform 안내를 사용하세요. Drain한 test host에서 driver/kernel 변경을 검증합니다. 오래된 driver 설치나 live worker의 containerd 재시작은 무해한 사전 검사가 아닙니다.

## Network·CIDR·MTU

Control plane의 kubelet·hybrid webhook 접근을 포함해 안정적인 **private 양방향 연결**이 필요합니다. Public API는 node→API 경로를 바꾸며 필요한 private 역방향 경로를 없애지 않습니다.

AWS의 **100 Mbps/RTT ≤200ms**는 일반 권장이지 엄격한 보편적 최소값이 아닙니다. 이전 10Gbps/5ms, packet loss 0.1%/0.01%, MTU 1500/9000은 미검증 계획 예시입니다. 실제 수요·encapsulation/path MTU를 시험하며 모든 NIC를 9000으로 바꾸지 마세요.

Remote node/Pod CIDR은 IPv4 RFC1918/CGNAT이며 서로·VPC·service network와 겹치면 안 됩니다. 각 remote 종류의 CIDR 최대 15개를 **하나의** remote-node-network, **하나의** remote-pod-network wrapper에 넣습니다. Cluster 간 Pod routing 분리도 필요합니다.

검토한 `network-plan.json`을 저장합니다.

```json
{
  "vpcCidrs": [
    "10.0.0.0/16"
  ],
  "serviceCidrs": [
    "10.100.0.0/16"
  ],
  "remoteNodeCidrs": [
    "10.80.0.0/16"
  ],
  "remotePodCidrs": [
    "10.85.0.0/16"
  ]
}
```
```bash
: "${NETWORK_PLAN_JSON:?Set the reviewed local network plan JSON}"
export NETWORK_PLAN_JSON
python3 - <<'PY'
import ipaddress, itertools, json, os
from pathlib import Path
plan = json.loads(Path(os.environ["NETWORK_PLAN_JSON"]).read_text())
allowed = [ipaddress.ip_network(c) for c in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")]
groups = {}
for key in ("vpcCidrs", "serviceCidrs", "remoteNodeCidrs", "remotePodCidrs"):
    values = plan[key]
    if not isinstance(values, list) or not values:
        raise SystemExit(f"{key} must be a nonempty list for this example")
    groups[key] = [ipaddress.ip_network(v, strict=True) for v in values]
    if any(n.version != 4 for n in groups[key]):
        raise SystemExit("This Hybrid Nodes plan requires IPv4")
for key in ("remoteNodeCidrs", "remotePodCidrs"):
    if len(groups[key]) > 15 or any(not any(n.subnet_of(a) for a in allowed) for n in groups[key]):
        raise SystemExit("Remote CIDRs must use RFC1918/CGNAT ranges, at most 15 per kind")
flat = [(key, n) for key, networks in groups.items() for n in networks]
for (ka, a), (kb, other) in itertools.combinations(flat, 2):
    if a.overlaps(other):
        raise SystemExit(f"Overlapping CIDRs: {ka} {a}, {kb} {other}")
print("CIDR syntax/range/non-overlap checks passed; routing and reachability remain unverified")
PY
```

문법·범위·중첩 검사이지 reachability 검증은 아닙니다. 실제 TGW/VGW의 VPC return route와 on-prem return/per-node Pod route를 구성하세요.

| Flow | 검토 사항 |
|------|-----------|
| Remote node/Pod → API TCP443 | 대상 CIDR의 추가 cluster SG ingress |
| Control-plane ENI → node TCP10250 | 제한된 cluster egress·private route·on-prem host/firewall ingress |
| Control plane → webhook | 실제 Pod IP/port·route·firewall |
| Host/Pod → credential/image/DNS/time | Provider endpoint·registry·DNS·시각 동기화 |

TCP10250은 kubelet에서 API-server SG로 들어오는 ingress가 아닙니다. EKS 단독 API가 모든 remote custom rule을 만들지는 않으며 eksctl은 자신이 소유한 VPC 측 리소스를 자동화할 수 있습니다. 60을 불변 상한으로 보지 말고 실제 quota를 확인하세요.

AWS는 public-only/private-only를 권장합니다. 둘 다 켜면 VPC 밖 node가 public 주소를 해석하므로 경로·접근 규칙에 따라 join이 **실패할 수 있습니다**. API의 무조건적인 거부는 아닙니다. Private-only에는 private DNS·관리자 접근도 필요합니다.

## Provider별 자격 증명

대상 관리자 identity로 AWS 입력을 준비합니다. Activation 정보를 private directory에 저장하세요.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended account}"
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the intended cluster}"
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/hybrid-preflight.XXXXXXXX")
export EXPECTED_ACCOUNT_ID AWS_REGION CLUSTER_NAME
printf 'Private preparation directory: %s\n' "$WORK_DIR"
```

SSM·Roles Anywhere 모두 AWS 연결이 필요합니다. 로컬 CA나 더 긴 cached credential은 offline control plane을 만들지 않습니다.

### SSM Role과 Activation

Role에는 `eks:DescribeCluster`, ECR pull, SSM core/cleanup 권한이 필요합니다. **AmazonEKSWorkerNodeMinimalPolicy만으로 DescribeCluster를 얻지 못합니다.** Pod Identity의 `eks-auth:AssumeRoleForPodIdentity`는 별도 권한입니다.

예시 계정/리전/cluster 값을 일관되게 바꾸세요. 아래 list operation은 instance별 resource scope를 지원하지 않아 wildcard를 쓰며 대상 Region으로 제한합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:ssm:ap-northeast-2:123456789012:*"
        }
      }
    }
  ]
}
```
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "eks:DescribeCluster",
      "Resource": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DescribeInstanceInformation",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DeregisterManagedInstance",
      "Resource": "arn:aws:ssm:ap-northeast-2:123456789012:managed-instance/*",
      "Condition": {
        "StringEquals": {
          "ssm:resourceTag/EKSClusterARN": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
        }
      }
    }
  ]
}
```

검토한 `AmazonEC2ContainerRegistryPullOnly`·`AmazonSSMManagedInstanceCore` 또는 동등 권한을 연결합니다. Activation의 `EKSClusterARN` tag는 deregistration policy와 일치해야 합니다.

의도한 등록 한도·24시간 **등록** 만료를 준비합니다.

```bash
: "${HYBRID_ROLE_NAME:?Use the reviewed SSM-trusting role name}"
: "${REGISTRATION_LIMIT:?Set a deliberate node registration limit}"
export HYBRID_ROLE_NAME REGISTRATION_LIMIT
python3 - <<'PY'
import json, os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
account, region, cluster = (os.environ[k] for k in ("EXPECTED_ACCOUNT_ID", "AWS_REGION", "CLUSTER_NAME"))
if not re.fullmatch(r"\d{12}", account) or not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid account/Region")
if region.startswith(("cn-", "us-gov-")):
    raise SystemExit("Hybrid Nodes is not available in this Region family")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", cluster):
    raise SystemExit("Invalid cluster name")
role = os.environ["HYBRID_ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Use the actual IAM role name, not a role ARN")
limit = int(os.environ["REGISTRATION_LIMIT"])
if not 1 <= limit <= 1000:
    raise SystemExit("RegistrationLimit must be 1..1000 per activation; review service quotas separately")
body = {"DefaultInstanceName": "eks-hybrid-node", "IamRole": role, "RegistrationLimit": limit,
        "Description": "Reviewed EKS hybrid activation",
        "Tags": [{"Key": "EKSClusterARN", "Value": f"arn:aws:eks:{region}:{account}:cluster/{cluster}"}],
        "ExpirationDate": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
(Path(os.environ["WORK_DIR"]) / "activation-request.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```
```bash
set -euo pipefail
# Run only after the role/trust/tag policy and registration scope are prepared.
check_account
aws ssm create-activation --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/activation-request.json" --output json \
  > "$WORK_DIR/activation-response.json"
chmod 600 "$WORK_DIR/activation-response.json"
# The response contains the secret ActivationCode. Do not print or commit it.
```

ActivationCode는 한 번 반환됩니다. ActivationId와 함께 안전하게 전달하세요. Activation 만료/삭제는 기존 managed instance의 deregistration이 아닙니다. [CreateActivation RegistrationLimit](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html)은 activation별 1–1,000 범위를 유지합니다. 전체 fleet의 무료 구간 한도가 아니며, 현재 요금 조건은 [자격 증명 provider 비교](README.md)에서 설명합니다.

SSM node name은 `mi-...`, credential 수명은 고정 1시간입니다. Network 복구 후에도 refresh backoff로 재연결이 지연될 수 있습니다. Credential을 log에 출력하지 마세요.

### Roles Anywhere Trust와 수명

Provider에 맞는 role·trust anchor·profile을 사용합니다. Session name을 인증서 identity/nodeName과 연결하며 이전 PrincipalTag/RequestTag 비교만으로는 강제되지 않았습니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": [
        "sts:TagSession",
        "sts:SetSourceIdentity"
      ],
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        },
        "StringEquals": {
          "sts:RoleSessionName": "${aws:PrincipalTag/x509Subject/CN}"
        }
      }
    }
  ]
}
```
```json
{
  "name": "hybrid-node-profile",
  "roleArns": [
    "arn:aws:iam::123456789012:role/EKSHybridNodeRole"
  ],
  "enabled": true,
  "acceptRoleSessionName": true,
  "durationSeconds": 3600
}
```

Anchor ARN을 바꾸고 scoped DescribeCluster/ECR 권한과 **acceptRoleSessionName=true**를 구성합니다.

```text
effectiveDuration = min(profileDuration, requestedDuration)
                    or profileDuration when the request omits duration
effectiveDuration <= role.MaxSessionDuration
```

Request/profile duration은 900–43,200초입니다. CreateSession은 **같은 값도 허용**합니다. Profile 3,600·override 없음·role maximum 3,600은 유효합니다. 이전 “더 커야 함”이라는 엄격한 표현은 부정확했습니다. 인증서 유효성/revocation·AWS 연결은 여전히 필요합니다.

### Node별 Key와 인증서

대상 새 node의 private directory에서 고유 key/CSR을 만듭니다. 예제는 단순 lowercase DNS label을 사용합니다. CSR을 승인된 issuer에 전달하고 CA signing key는 node에 두지 마세요.

```bash
set -euo pipefail
umask 077
: "${WORK_DIR:?Set a private preparation directory on this node}"
: "${NODE_NAME:?Use a unique certificate CN / node name}"
export NODE_NAME
python3 - <<'PY'
import os, re
name = os.environ["NODE_NAME"]
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", name):
    raise SystemExit("This example requires a lowercase DNS label of 2..63 characters")
PY
test ! -e "$WORK_DIR/node.key"
test ! -e "$WORK_DIR/node.csr"
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$WORK_DIR/node.key"
chmod 600 "$WORK_DIR/node.key"
openssl req -new -key "$WORK_DIR/node.key" -out "$WORK_DIR/node.csr" -subj "/CN=$NODE_NAME"
# Send the CSR to the approved PKI issuer; do not copy its CA private key to nodes.
```

발급 chain·승인된 CA·유효성/revocation·key 일치·CN을 확인하고 시각을 동기화합니다. 새 node에만 설치하세요.

```bash
set -euo pipefail
: "${ISSUED_NODE_CERT:?Set the verified certificate/chain issued for this node}"
: "${WORK_DIR:?Set the private directory containing the node key}"
# New-node installation only; do not overwrite an existing identity.
sudo test ! -e /etc/iam/pki/server.key
sudo test ! -e /etc/iam/pki/server.pem
sudo install -d -m 0700 /etc/iam/pki
sudo install -m 0644 "$ISSUED_NODE_CERT" /etc/iam/pki/server.pem
sudo install -m 0600 "$WORK_DIR/node.key" /etc/iam/pki/server.key
```

EKS Kubernetes API CA 파일과 다릅니다. Node identity를 image에 복제하거나 기존 key를 조용히 덮어쓰면 안 됩니다.

## CloudFormation 준비

고정된 v1.0.20 template은 provisioning의 출발점입니다. SSM template은 role을 만들며 **activation은 만들지 않습니다**. 여러 cluster에 쓰기 전 넓은 DescribeCluster scope와 고정 export 이름을 검토하세요.

IRA의 `CertAttributeTrustPolicy` 값은 `"CN"`이 아닌 literal **`${aws:PrincipalTag/x509Subject/CN}`**입니다. Python `cryptography` helper는 PEM을 정확히 serialize하고 기본 CA 형태·현재 유효성을 확인하며 issuer 권한·revocation 검증은 아닙니다.

```bash
: "${CA_PEM_FILE:?Set the approved CA certificate file, not a private key}"
: "${ROLE_NAME:?Set the new role name selected by the IaC owner}"
export CA_PEM_FILE ROLE_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
from cryptography import x509
from datetime import datetime, timezone
raw = Path(os.environ["CA_PEM_FILE"]).read_bytes()
if b"PRIVATE KEY" in raw or raw.count(b"-----BEGIN CERTIFICATE-----") != 1:
    raise SystemExit("Provide one reviewed CA certificate")
cert = x509.load_pem_x509_certificate(raw)
if not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
    raise SystemExit("Certificate is not a CA")
now = datetime.now(timezone.utc)
if not cert.not_valid_before.replace(tzinfo=timezone.utc) <= now <= cert.not_valid_after.replace(tzinfo=timezone.utc):
    raise SystemExit("CA certificate is not currently valid")
role = os.environ["ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Invalid IAM role name")
body = [
    {"ParameterKey": "RoleName", "ParameterValue": role},
    {"ParameterKey": "CertAttributeTrustPolicy", "ParameterValue": "${aws:PrincipalTag/x509Subject/CN}"},
    {"ParameterKey": "CABundleCert", "ParameterValue": raw.decode("ascii")}
]
(Path(os.environ["WORK_DIR"]) / "cfn-iamra-parameters.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

고정 template의 parameter key/AllowedValues를 대조하고 IaC owner가 policy scope·export 이름을 정한 뒤 change set을 검토합니다. 잘못된 PEM shorthand나 미검토 mutable-main template을 배포하지 마세요.

## Cluster Access와 생성 계획

Node IAM role에는 **HYBRID_LINUX access entry**를 권장합니다.

```json
{
  "clusterName": "my-hybrid-cluster",
  "principalArn": "arn:aws:iam::123456789012:role/EKSHybridNodeRole",
  "type": "HYBRID_LINUX"
}
```

Mapping은 `system:node:{{SessionName}}`과 node-bootstrap group을 사용합니다. API/API_AND_CONFIG_MAP 인증·소유권을 확인합니다. 기존 mapping을 지우는 한-role `aws-auth` ConfigMap을 적용하지 마세요. Legacy mapping 변경은 통제된 이전이 필요합니다.

아래 모든 ID를 검토한 실제 리소스로 바꿉니다. Private-only endpoint·IPv4·1.36이 명시돼 있습니다. Bootstrap creator admin 권한은 통제된 lab용이며 production operator 접근은 의도적으로 선택하세요.

eksctl 0.229.0에서는 문서화된 **SSM/IRA**를 사용합니다. RoleARN을 제공한다면 provider 리소스도 별도로 준비합니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-hybrid-cluster
  region: ap-northeast-2
  version: '1.36'
iam:
  serviceRoleARN: arn:aws:iam::123456789012:role/EKSClusterRole
accessConfig:
  authenticationMode: API_AND_CONFIG_MAP
  bootstrapClusterCreatorAdminPermissions: true
kubernetesNetworkConfig:
  ipFamily: IPv4
  serviceIPv4CIDR: 10.100.0.0/16
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      ap-northeast-2a:
        id: subnet-0123456789abcdef0
      ap-northeast-2c:
        id: subnet-0123456789abcdef1
  controlPlaneSecurityGroupIDs:
  - sg-0123456789abcdef0
  clusterEndpoints:
    privateAccess: true
    publicAccess: false
remoteNetworkConfig:
  iam:
    provider: SSM
    roleARN: arn:aws:iam::123456789012:role/EKSHybridNodeRole
  vpcGatewayID: tgw-0123456789abcdef0
  remoteNodeNetworks:
  - cidrs:
    - 10.80.0.0/16
  remotePodNetworks:
  - cidrs:
    - 10.85.0.0/16
```

eksctl provisioning 시 `--without-nodegroup`과 명시적인 private kubeconfig 경로를 사용하세요. Schema 유효성은 IAM·route·gateway reachability 증거가 아닙니다. 예전 eksctl의 launch-only 문서는 오래됐으며 현재 EKS API는 기존 cluster의 hybrid remote-network 구성도 지원합니다.

대응하는 EKS CreateCluster 요청입니다.

```json
{
  "name": "my-hybrid-cluster",
  "version": "1.36",
  "roleArn": "arn:aws:iam::123456789012:role/EKSClusterRole",
  "resourcesVpcConfig": {
    "subnetIds": [
      "subnet-0123456789abcdef0",
      "subnet-0123456789abcdef1"
    ],
    "securityGroupIds": [
      "sg-0123456789abcdef0"
    ],
    "endpointPrivateAccess": true,
    "endpointPublicAccess": false
  },
  "kubernetesNetworkConfig": {
    "ipFamily": "ipv4",
    "serviceIpv4Cidr": "10.100.0.0/16"
  },
  "accessConfig": {
    "authenticationMode": "API_AND_CONFIG_MAP",
    "bootstrapClusterCreatorAdminPermissions": true
  },
  "remoteNetworkConfig": {
    "remoteNodeNetworks": [
      {
        "cidrs": [
          "10.80.0.0/16"
        ]
      }
    ],
    "remotePodNetworks": [
      {
        "cidrs": [
          "10.85.0.0/16"
        ]
      }
    ]
  }
}
```

한 infrastructure owner를 선택하며 두 경로를 모두 실행하지 않습니다. 실제 cluster/endpoint identity·operator 권한·node access 확인 후 join합니다. 예시 AWS ID는 검증된 리소스가 아닙니다.

## Add-on

아래 공식 hybrid 호환 기준은 모든 Kubernetes 버전의 **설치 target이 아닙니다**.

| Add-on | Hybrid 호환 기준 |
|--------|-------------------|
| kube-proxy/CoreDNS | 1.25.14-eksbuild.2 / 1.9.3-eksbuild.7 |
| ADOT/CloudWatch Observability | 0.102.1-eksbuild.2 / 2.2.1-eksbuild.1 |
| Pod Identity Agent | 일반 1.3.3-eksbuild.1, **Bottlerocket 1.3.7-eksbuild.2**; **Bottlerocket OS 1.39.0 이상**도 필요 |
| Node monitoring/snapshot controller | 1.2.0-eksbuild.1 / 8.1.0-eksbuild.2 |
| Private CA Connector/FSx CSI/Secrets Store provider | 1.6.0-eksbuild.1 / 1.7.0-eksbuild.1 / 2.1.1-eksbuild.1 |
| Metrics Server/cert-manager | 0.7.2-eksbuild.1 / 1.17.2-eksbuild.1 |
| Node Exporter/kube-state-metrics/External DNS | 1.9.1-eksbuild.2 / 2.15.0-eksbuild.4 / 0.19.0-eksbuild.1 |

```bash
check_account
: "${ADDON_NAME:?Select one add-on to review}"
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version 1.36 --output json > "$WORK_DIR/addon-catalog.json"
jq '[.addons[].addonVersions[] |
     {addonVersion,architecture,computeTypes,compatibilities}]' "$WORK_DIR/addon-catalog.json"
```

선택한 버전의 hybrid/OS/kernel 설정을 검토합니다. VPC CNI는 hybrid node를 관리하지 않으므로 호환 CNI·cloud-only agent placement를 구성합니다. Catalog 존재는 설치·Ready 증거가 아닙니다.

## 참고 자료

- [Hybrid prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [Operating systems and nodeadm minimum](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm reference](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Hybrid networking](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Credentials and Hybrid Nodes IAM role](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Host credentials during disconnections](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [IAM Roles Anywhere CreateSession](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [Supported hybrid add-ons](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [eksctl hybrid configuration](https://docs.aws.amazon.com/eks/latest/eksctl/hybrid-nodes.html)
- [Released nodeadm v1.0.20](https://github.com/aws/eks-hybrid/releases/tag/v1.0.20)
- [Pinned Packer source](https://github.com/aws/eks-hybrid/tree/v1.0.20/example/packer)
- [Pinned SSM CloudFormation template](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ssm-cfn.yaml)
- [Pinned Roles Anywhere CloudFormation template](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ira-cfn.yaml)
- [NVIDIA CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [NVIDIA Container Toolkit installation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)


< [목차](./README.md) | [다음: 네트워크 구성](02-network-configuration.md) >
