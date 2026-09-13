# 베어메탈 서버 OS 설치 및 마이그레이션 가이드

< [이전: 운영 및 유지보수](./08-operations.md) | [목차](./README.md) | [다음: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

> **검증 기준**: 2026년 9월 13일 AWS Hybrid OS/nodeadm 문서·공개 요금 확인; nodeadm 1.0.20은 검토한 CLI 기준입니다. 현재 지원되는 EKS/OS/CNI 조합을 선택합니다.
> **마지막 업데이트**: 2026년 9월 13일

데이터를 지우는 OS 설치, 이미지 준비, 클러스터 가입, 읽기 전용 검증을 구분합니다. 예제에는 placeholder가 있으므로 호스트별 설치 계획이 필요합니다. 이번 검토에서는 OS 설치, Packer build, VM 생성, AWS/클러스터 작업을 실행하지 않았습니다.

## 개요

### 베어메탈을 선택하는 이유

하이퍼바이저를 제거하면 해당 라이선스와 실행 계층을 없앨 수 있지만 총비용 절감이나 애플리케이션 성능 향상을 보장하지는 않습니다. 가상화 기능, 가용성, 백업, storage, networking, 지원 계약과 이전 작업을 먼저 조사합니다. VM 애플리케이션이 자동으로 컨테이너가 되거나 파일럿 클러스터를 시작했다고 기존 계약 의무가 사라지는 것은 아닙니다.

### OS 인프라 지원 매트릭스

| OS | 베어메탈 | 온프레미스 가상화 | 구성과 지원 범위 |
| --- | --- | --- | --- |
| Ubuntu 20.04/22.04/24.04 | Hybrid에 명시된 OS 계열 | OS/kernel/CNI 조건을 충족한 호스트 | nodeadm/YAML; Ubuntu 수명주기·지원은 별도 확인 |
| RHEL 8/9 | Hybrid에 명시된 OS 계열 | OS/kernel/CNI 조건을 충족한 호스트 | nodeadm/YAML; Red Hat 구독·OS 지원은 별도 |
| AL2023 | **지원되는 배포 경로 아님** | 온프레미스 가상화 guest | nodeadm/YAML; EC2 밖 AL2023 OS에는 AWS Support Plans 미적용 |
| Bottlerocket VMware variant >=1.37.0 | **Hybrid bare metal 미지원** | VMware vSphere, **x86_64** | Bottlerocket settings/bootstrap; govc는 VMware VM 관리 |

AWS는 명시된 Ubuntu/RHEL 계열과의 Hybrid 통합을 지원하며 OS vendor의 지원을 대신하지 않습니다. 구체적 버전, architecture, CNI/kernel 조건도 확인합니다. EC2 밖 AL2023은 VM guest 선택지이며 일반 raw-image 베어메탈 권장이 아닙니다. Bottlerocket VMware용 Kubernetes variant가 1.28부터 있다는 설명은 과거 variant 범위이며 오래된 EKS 버전 사용 권장이 아닙니다. SSM 설치·업그레이드는 오래된 SSM 서명 키 문제를 피하도록 nodeadm >=1.0.19가 필요합니다.

## 비용 비교 분석

### 라이선스/구독 비용 비교

#### VMware vSphere

실제 제품 bundle, licensed core, 최소 수량, 기간과 지원 조건에 맞는 견적을 받습니다. 기존의 소켓당 연간 $4,500–8,500에는 여기서 검증한 출처가 없으므로 현재 vSphere 견적으로 사용할 수 없습니다.

#### OpenShift

실제 Red Hat entitlement, physical/virtual core·socket 산정과 지원 tier를 비교합니다. 기존 노드당 연간 $2,500–5,000과 “premium 지원 포함” 주장은 미검증이며 현재 요금·권리 보장이 아닙니다.

#### EKS Hybrid Nodes

[공식 요금](https://aws.amazon.com/eks/pricing/)은 **노드가 보고한 vCPU-hours**의 월별 구간 요금입니다. 처음 576,000은 $0.020, 다음 576,000은 $0.014, 다음 4,608,000은 $0.010, 다음 5,760,000은 $0.008, 11,520,000 초과분은 $0.006입니다. 모든 사용량에 적용되는 고정 $0.01 요금이 아닙니다.

동일 계정·리전에서 합산하며 AWS Organizations 통합 결제는 동일 리전의 조직 계정 사용량을 합산합니다. Hyperthreading한 bare-metal core 하나가 vCPU 2개로 보고될 수 있습니다. 노드 가입 시 과금이 시작하고 제거 시 종료하므로 workload가 idle이어도 노드 요금이 사라지지 않습니다. AWS는 머신당 32 vCPU를 초과하면 account team과 요금을 상담하도록 안내합니다. 클러스터, provisioned control plane/capability, 네트워크, 로그, storage, OS와 기타 지원 요금은 별도입니다.

### 규모별 연간 비용 비교 (32 vCPU 서버 기준)

다음은 청구서·실측이 아닌 결정적 **계산 모델**입니다. 노드당 보고된 32 vCPU, 매월 730시간, 동일 리전·합산 범위, 다른 Hybrid 사용량 없음, 같은 월을 12번 반복한 연환산을 가정합니다. 마지막 열은 기본 control-plane tier의 표준 지원 클러스터 1개($0.10/시간)를 더합니다. 다른 서비스, 할인·세금, 하드웨어, 전력, OS entitlement, 인력·이전 비용은 제외하며 실제 월 길이와 구간 초기화가 청구액에 영향을 줍니다.

| 노드 | 월 vCPU-hours | 월 노드 요금 | 연환산 노드 요금 | 노드 + 기본 tier 표준 지원 클러스터 1개 연환산 |
| --- | --- | --- | --- | --- |
| 10 | 233,600 | $4,672.00 | $56,064.00 | $56,940.00 |
| 50 | 1,168,000 | $19,744.00 | $236,928.00 | $237,804.00 |
| 100 | 2,336,000 | $31,424.00 | $377,088.00 | $377,964.00 |

<details>
<summary>보존한 과거 추정치 — 미검증이며 현재 요금 아님</summary>

원래 표를 추적 목적으로 보존합니다. Vendor 견적 출처는 확인하지 못했습니다. EKS 열은 폐기한 고정 요금 가정 `32 × $0.01 × 8,760 = $2,803.20/노드/년`을 사용했고 클러스터 요금·구간별 요금을 포함하지 않았습니다. 현재 TCO 비교 근거로 사용하지 않습니다.

| 규모 | VMware vSphere (과거 연간 추정치) | OpenShift (과거 연간 추정치) | EKS Hybrid (폐기한 고정 요금 추정치) |
| --- | --- | --- | --- |
| 10 nodes | ~$45,000–85,000 | ~$25,000–50,000 | ~$28,032 |
| 50 nodes | ~$225,000–425,000 | ~$125,000–250,000 | ~$140,160 |
| 100 nodes | ~$450,000–850,000 | ~$250,000–500,000 | ~$280,320 |

</details>

### TCO(총 소유 비용) 고려 사항

여유 용량, 시설·전력, OS/보안 패치, PKI/SSM 운영, storage/백업·복원, 연결성, 모니터링, 인력, 계약 의무와 rollback 용량을 포함합니다. 동등한 가용성·지원 범위로 비교하고 미검증 과거 표에서 절감률을 도출하지 않습니다.

## OS별 베어메탈 설치

### 사전 준비

#### BIOS/UEFI 설정

선택한 installer, firmware, boot mode, NIC/storage driver와 서명된 boot chain을 확인합니다. 검증한 bootloader/kernel/module이 지원하면 Secure Boot를 유지하며 컨테이너 설치의 기본 조건으로 비활성화하지 않습니다. 일반 Linux containerd/runc 컨테이너에는 VT-x/AMD-V 하드웨어 가상화가 필수가 아닙니다. VM 기반 sandbox, QEMU/KVM 이미지 builder 등의 요구사항은 별도입니다.

#### 네트워크 인프라

Legacy PXE는 주로 DHCP/ProxyDHCP·TFTP를 사용하지만 UEFI HTTP/iPXE 설계는 다른 boot transport를 사용할 수 있습니다. `pxelinux.0`은 모든 UEFI의 bootloader가 아닙니다. Firmware에 맞는 loader와 ISO/kernel/initrd 무결성을 확인하고 provisioning network를 workload와 분리합니다. 호스트별 설정을 보호하며 인증 없는 공유 HTTP/TFTP root에 activation code, private key, password를 두지 않습니다.

#### AWS Packer 템플릿

[AWS 예제 디렉터리](https://github.com/aws/eks-hybrid/tree/main/example/packer)의 실제 파일은 `hybrid-nodes-template.pkr.hcl`입니다. 기존 `bare-metal-template.pkr.hcl`은 제공된 파일이 아닙니다. 템플릿의 `CREDENTIAL_PROVIDER`는 `ssm`·`iam`을 받고 HCL이 `iam`을 nodeadm의 `iam-ra`로 바꿉니다. QEMU 출력은 존재하지 않는 `output_format` 변수가 아니라 `PACKER_OUTPUT_FORMAT`을 사용합니다. 승인한 commit의 template·provisioner script에서 builder별 필수 입력과 password/user-data 처리를 검토합니다.

```bash
# From a reviewed checkout of aws/eks-hybrid/example/packer:
export NODEADM_ARCH=amd       # This template uses amd/arm, not amd64/arm64.
export CREDENTIAL_PROVIDER=ssm # The template accepts ssm/iam; maps iam to nodeadm iam-ra.
export PACKER_OUTPUT_FORMAT=raw
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
: "${ISO_URL:?Set the approved Ubuntu or RHEL installer ISO}"
: "${ISO_CHECKSUM:?Set the verified vendor ISO checksum}"
export K8S_VERSION ISO_URL ISO_CHECKSUM
# Also prepare the selected builder's required inputs using the reviewed template.
packer validate -syntax-only hybrid-nodes-template.pkr.hcl
# A separate build action, not a validation step:
# packer build -only=general-build.qemu.ubuntu24 hybrid-nodes-template.pkr.hcl
```

템플릿에는 AMI/vSphere builder도 있으므로 별도 build 전에 의도한 builder만 선택합니다. Syntax-only 검증은 이미지 생성·실행 검증이 아닙니다. 오래된 Kubernetes 예제, 기본 builder password, 전체 읽기 가능한 credential 파일이나 등록된 machine/SSM identity를 재사용 이미지에 복사하지 않습니다.

수동으로 준비한 호스트에서는 승인된 nodeadm release·architecture와 검토한 checksum을 사용합니다. 다음은 상태 검사가 아니라 **설치 단계**입니다. 승인된 release 검증 경로로 checksum을 확보하고 값을 지어내거나 불일치를 우회하지 않습니다.

```bash
set -euo pipefail
: "${NODEADM_VERSION:?Set the approved release, at least 1.0.19 for SSM}"
: "${NODEADM_SHA256:?Set the approved SHA-256 for this release and architecture}"
: "${NODEADM_ARTIFACT:?Set the local file delivered through the approved artifact channel}"
case "$(uname -m)" in
  x86_64) NODEADM_ARCH=amd64 ;;
  aarch64|arm64) NODEADM_ARCH=arm64 ;;
  *) printf 'Unsupported architecture\n' >&2; exit 2 ;;
esac
[[ "$NODEADM_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 2
[[ "$NODEADM_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || exit 2
[[ "$(printf '%s\n' 1.0.19 "$NODEADM_VERSION" | sort -V | head -n 1)" == 1.0.19 ]] || exit 2
umask 077
STAGING_DIR=$(mktemp -d)
trap 'rm -f -- "$STAGING_DIR/nodeadm"; rmdir -- "$STAGING_DIR"' EXIT
cp -- "$NODEADM_ARTIFACT" "$STAGING_DIR/nodeadm"
printf '%s  %s\n' "$NODEADM_SHA256" "$STAGING_DIR/nodeadm" | sha256sum --check -
chmod 0700 "$STAGING_DIR/nodeadm"
# Check the verified staged binary before replacing the installed executable.
ACTUAL_VERSION=$("$STAGING_DIR/nodeadm" --version)
VERSION_RE="(^|[^0-9.])v?${NODEADM_VERSION//./\\.}([^0-9A-Za-z.+-]|$)"
[[ "$ACTUAL_VERSION" =~ $VERSION_RE ]] || { printf 'Artifact version mismatch\n' >&2; exit 2; }
printf '%s\n' "$ACTUAL_VERSION"
sudo install -m 0755 "$STAGING_DIR/nodeadm" /usr/local/bin/nodeadm
/usr/local/bin/nodeadm --version
```

### Ubuntu LTS (22.04/24.04)

Ubuntu Server의 Subiquity Autoinstall은 YAML을 사용하며 cloud-init으로 전달할 수 있습니다. 다음 템플릿은 storage를 대화형으로 유지하고 정확한 승인 disk serial·SSH key 입력을 요구합니다. 선택한 disk를 partition하면 기존 데이터가 지워집니다. 백업, disk 인벤토리, installer 전달, 접근·복구 경로와 firmware 호환성을 먼저 폐기 가능한 대상에서 확인합니다. 데이터 disk가 있는 호스트에 wildcard·빈 match·“가장 큰 disk” 가정을 사용하지 않습니다.

#### Autoinstall 설정 예시

```yaml
#cloud-config
autoinstall:
  version: 1
  interactive-sections: [storage]
  locale: en_US.UTF-8
  keyboard:
    layout: us
  storage:
    layout:
      name: lvm
      match:
        serial: REPLACE_WITH_APPROVED_DISK_SERIAL
  identity:
    hostname: replace-with-unique-hostname
    username: hybrid-admin
    password: "!"
  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
    - "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
  packages: [curl, jq]
  shutdown: poweroff
```

이 템플릿의 `password: "!"`는 password 인증을 잠급니다. 실제 승인된 SSH 접근과 복구 경로를 확인합니다. 호스트와 installer에 맞는 network/NIC/VLAN/bond 설정은 별도로 제공합니다. 로컬 schema 검증은 disk 선택·boot·login 시험이 아닙니다. nodeadm은 앞의 별도 단계에서 준비하며 installer가 무결성 확인 없는 `latest` binary를 내려받지 않습니다.

#### Ubuntu 24.04 특이사항

[Ubuntu 버그 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)은 컨테이너 종료 signal에 대한 AppArmor 거부 문제이며 패키지 수정이 배포되어 있습니다. AWS OS 문서는 여전히 1.7.19+ 수정 맥락을 설명합니다. 실제 배포판 패키지·backport, 로드된 profile, runtime과 denial log를 확인합니다. 모든 stuck Pod의 원인을 이 버그로 단정하거나 오래된 containerd에 머무르도록 권장하지 않습니다.

```bash
# Read-only investigation on the affected host:
containerd --version
dpkg-query -W 'containerd*' 'runc*' 'apparmor*'
sudo journalctl -k --since '30 minutes ago' --no-pager -n 200
if test -f /run/reboot-required.pkgs; then cat /run/reboot-required.pkgs; fi
```

문서화된 해당 패키지/profile 전환에는 수정된 profile을 로드하기 위한 재시작이 필요합니다. 수명주기 절차로 drain·reboot·workload 검증을 계획합니다. 모든 AppArmor 편집에 reboot가 필요하다고 일반화하지 않습니다. `aa-remove-unknown`은 `/etc/apparmor.d`에 없는 로드된 profile을 모두 제거하므로 특정 profile 편집 명령이나 기본 복구 명령이 아닙니다.

### RHEL 9

RHEL은 Kickstart를 사용합니다. 다음은 **Bash가 아닌 설치 템플릿**입니다. 승인한 단일 설치 disk 식별자, password hash, 전체 SSH public key를 대입합니다. `ignoredisk --only-use`와 `clearpart --drives`는 같은 확인된 disk를 지정해야 하며 제한 없는 `clearpart --all`을 사용하지 않습니다. 선택한 installer의 repository/stage2/bootloader/network 조건을 맞추고 해당 버전의 ksvalidator로 검증합니다.

#### Kickstart 설정 예시

```text
# Template: substitute and validate the approved target disk, key and password hash.
lang en_US.UTF-8
keyboard us
timezone UTC --utc
rootpw --lock
user --name=hybrid-admin --groups=wheel --iscrypted --password=REPLACE_WITH_CRYPT_HASH
sshkey --username=hybrid-admin "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
network --bootproto=dhcp --device=link --activate
ignoredisk --only-use=REPLACE_WITH_APPROVED_INSTALL_DISK
clearpart --all --initlabel --drives=REPLACE_WITH_APPROVED_INSTALL_DISK
autopart --type=lvm
selinux --enforcing
services --enabled=sshd
%packages
@core
openssh-server
curl
jq
%end
poweroff
```

SELinux enforcing을 유지하고 구체적인 policy/context 요구사항을 진단합니다. nodeadm 문서는 containerd SELinux·Pod security context 설정을 제공하므로 `container_t` 전체를 permissive로 바꾸지 않습니다. OS 패키지와 nodeadm/containerd 설치는 별도 단계입니다.

#### RHEL containerd 설치 주의사항

RHEL에서 nodeadm의 `distro` containerd source는 지원되지 않습니다. 호환되는 Docker 배포 패키지를 nodeadm으로 설치하려면 `docker`, 별도로 설치·관리한다면 `none`을 선택합니다. “RHEL은 항상 docker가 필수”라는 표현은 너무 넓습니다.

```bash
set -euo pipefail
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
sudo nodeadm install "$K8S_VERSION" --credential-provider ssm \
  --containerd-source docker
# If containerd is separately installed and maintained, choose --containerd-source none.
```

#### 대규모 환경: Satellite/Foreman 통합

Satellite/Foreman으로 검토한 Kickstart template, repository와 provisioning workflow를 관리할 수 있습니다. 호스트별 disk, hardware identity, 구독, artifact 무결성과 실패 복구를 확인합니다. 공유 template 문법이 맞다는 사실은 임의의 전체 fleet을 지워도 된다는 뜻이 아닙니다.

### Amazon Linux 2023

이 절은 베어메탈 설치가 아닌 **가상화 guest 참고 사항**입니다. AWS는 EC2 밖 AL2023에 KVM, VMware, Hyper-V VM 이미지를 제공합니다. 해당 OS 사용에는 AWS Support Plans이 적용되지 않으며 EKS Hybrid 통합 지원과 구분합니다. 적절한 이미지·cloud-init 전달 경로를 선택합니다. 최소 VM identity 조각은 다음과 같습니다.

```yaml
#cloud-config
# VM identity fragment only; it does not install or join a Hybrid Node.
hostname: replace-with-unique-hostname
manage_etc_hosts: true
ssh_pwauth: false
```

관리자 생성, key 삽입이나 node 초기화를 수행하는 예제가 아닙니다. 승인한 접근을 준비하고 별도로 검토한 bootstrap을 사용합니다. AL2023은 `--containerd-source docker`를 지원하지 않으므로 지원되는 distro source를 쓰거나 containerd를 별도로 관리합니다.

### Bottlerocket on VMware (참고)

EKS Hybrid Nodes에는 x86_64용 지원 VMware variant >=1.37.0을 사용합니다. OS/인증은 Bottlerocket settings와 bootstrap container가 구성하며 govc는 TOML parser가 아니라 VMware VM 관리 CLI입니다. 버전별 settings, private user-data·credential은 [전체 bootstrap 가이드](./04-node-bootstrap.md)를 따릅니다.

## 자격 증명 프로바이더 설정 비교

### nodeadm 기반 설정 (Ubuntu/RHEL/AL2023)

아래는 SSM과 IAM Roles Anywhere의 별도 선택지입니다. 모든 placeholder를 승인한 cluster/region/identity로 교체하고 NodeConfig를 root 소유·0600으로 보호하며 호스트별 private key를 비공개로 유지합니다. 등록된 SSM state나 공유 host key를 golden image에 포함하지 않습니다.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: "REPLACE_WITH_PRIVATE_ACTIVATION_CODE"
      activationId: "REPLACE_WITH_PRIVATE_ACTIVATION_ID"
```

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_WITH_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_WITH_ID
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

Nodeadm은 구성을 검증하고 설정된 AWS identity로 필요한 cluster metadata를 조회합니다. 가입 전에 실제 API 연결, EKS access entry, trust·권한과 certificate 경로를 확인합니다. YAML parser 통과는 인가 성공 증거가 아닙니다.

### Bottlerocket 기반 설정 (VMware)

이전의 `[settings.hybrid.ssm]`·`[settings.hybrid.iam-roles-anywhere]`는 유효한 Bottlerocket settings가 아니었습니다. [노드 bootstrap](./04-node-bootstrap.md)에 설명한 Kubernetes settings와 Hybrid bootstrap-container 입력을 사용합니다. Base64 user-data는 암호화가 아닌 인코딩이므로 VMware guestinfo·provisioning log를 보호합니다.

### 자격 증명 프로바이더 선택 가이드

| 상황 | 선택 시 검토할 사항 |
| --- | --- |
| 관리되는 PKI 없음 | SSM hybrid activation으로 인증서 관리 부담을 줄일 수 있음; identity·activation 수명주기 필요 |
| 관리되는 PKI 있음 | 호스트별 X.509를 IAM Roles Anywhere에 사용; 발급·신뢰·만료·폐기 운영 필요 |
| Public internet 없음 | 어느 방식이든 필요한 AWS API를 승인된 private/proxy 경로로 접근해야 함; endpoint 지원 확인 |
| 완전 단절/DDIL | EKS Hybrid Nodes의 지원 운영 모델이 아님; IAM Roles Anywhere도 AWS CreateSession 호출 필요 |
| 사용자 지정 node identity | Provider의 naming·수명주기 조건 검토; Node 이름이 호스트 DNS 이름이라는 가정 금지 |

[Private 연결](./03-airgap-setup.md)을 참고합니다. “Public internet 없음”과 “AWS 연결 없음”은 서로 다른 조건입니다.

## 대규모 프로비저닝 자동화

### PXE 부트 인프라 구성

```text
승인한 호스트/firmware 인벤토리
  → 일치하는 DHCP/HTTP/PXE boot 설정
  → 검증한 signed loader와 installer kernel/initrd
  → 보호된 호스트별 설치 설정
  → 명시한 승인 disk / OS 설치
  → 고유 host identity / 별도의 Hybrid bootstrap
```

위 TFTP/PXELINUX 조합은 legacy BIOS를 설명합니다. UEFI PXE도 TFTP를 사용할 수 있지만 UEFI 호환 loader가 필요하므로 실제 환경에 맞는 안전한 전달 경로를 선택합니다. ISO checksum·서명 신뢰는 DHCP 도달성과 별도입니다.

### Ansible 자동화 플레이북

다음은 **이미 준비된 호스트의 읽기 전용 preflight**입니다. 구성 요소·서비스가 없으면 중단하며 `/usr/bin/kubelet` 존재를 원하는 버전이 설치되었다는 증거로 사용하지 않습니다. Binary 설치, secret template 배포, nodeadm init 반복 실행을 하지 않습니다.

```yaml
# Read-only preflight; does not provision, install, or initialize hosts.
- name: Inspect approved Hybrid hosts
  hosts: hybrid_nodes
  become: true
  gather_facts: false
  serial: 1
  any_errors_fatal: true
  tasks:
  - name: Read OS release
    ansible.builtin.command:
      argv: [cat, /etc/os-release]
    changed_when: false
  - name: Read architecture
    ansible.builtin.command:
      argv: [uname, -m]
    changed_when: false
  - name: Read installed nodeadm version
    ansible.builtin.command:
      argv: [/usr/local/bin/nodeadm, --version]
    changed_when: false
  - name: Check each required service
    ansible.builtin.command:
      argv: [systemctl, is-active, --quiet, "{{ item }}"]
    loop: [containerd, kubelet]
    changed_when: false
```

Provisioning은 별도의 승인한 단계로 수행합니다: host/disk 인벤토리 확인 → 검증한 OS/artifact 준비 → private 호스트별 구성 공급 → [bootstrap state·identity 절차](./04-node-bootstrap.md) → 실제 Node UID, 버전, 새 Lease·workload 확인. 기존 호스트는 [수명주기 관리](./07-node-lifecycle.md)를 따릅니다. 한 호스트씩 조정하고 실패·부분 상태를 보존하며 `creates: /usr/bin/kubelet`로 필요한 변경을 가리지 않습니다.

## 마이그레이션 전략

### VMware → 베어메탈 + EKS Hybrid Nodes

#### Phase 1: 병행 운영 인프라 구축

Workload, VM, 계약, network/security 기능, storage·의존성을 조사합니다. 지원되는 병행 target, private 연결과 rollback 용량을 준비합니다. 전환 중 Bottlerocket on VMware를 유지할 수 있지만 이를 bare-metal OS로 바꾸는 것은 아닙니다.

#### Phase 2: 워크로드 컨테이너화

적합한 workload를 명시적으로 컨테이너화하며 일부 VM은 계속 VM으로 남아야 할 수 있습니다. Writer 이전 전에 데이터, CSI 동작, 권한, backup·restore를 검증합니다. AWS 관리형 DB는 설계 선택지이며 자동 변환이 아닙니다.

#### Phase 3: 네트워크 전환

NSX-T의 routing, overlay, firewall, load balancing과 policy를 각각 조사합니다. Cilium BGP는 경로를 교환하며 모든 NSX-T 기능을 동등하게 대체하지 않습니다. 트래픽 전환 전에 addressing, 반환 경로, ingress/TLS, DNS, policy와 기존 연결을 검증합니다.

#### Phase 4: VMware 폐기

Workload/data 수락, 합의한 rollback 기간, backup 복구와 계약·보존 판단 뒤 폐기합니다. 제거하는 실제 인프라를 확인하고 라이선스 취소·disk wipe를 pipeline의 자동 마무리 작업으로 만들지 않습니다.

### OpenShift → EKS Hybrid Nodes

#### 개념 매핑

| OpenShift | Target 후보 | 해결할 이전 차이 |
| --- | --- | --- |
| Route | Ingress / Gateway API controller | TLS termination/reencrypt/passthrough, weight·annotation·policy는 controller별 확인 |
| SCC | PSS/Pod Security Admission 및 필요한 policy/defaulting | PSS는 SCC UID/SELinux/group 전략·mutation을 재현하지 않음 |
| OLM | 지원되는 OLM, Helm 또는 EKS add-on/operator 공급 | OLM은 Kubernetes에서도 실행 가능; CRD conversion·upgrade·의존성은 자동 이전되지 않음 |
| MachineSet | Host lifecycle/provisioning automation | nodeadm/Ansible은 교체·scale을 담당하는 Machine API controller가 아님 |
| ImageStream | Registry 및 image promotion/trigger automation | ECR은 image 저장소이며 ImageStream import/tag/change trigger를 대체하지 않음 |
| BuildConfig | 검토한 외부 CI/CD | Source, image, credential·build policy 동작 재구성 |
| DeploymentConfig | Deployment 및 필요한 rollout automation | Trigger, hook, strategy·rollback 동작 보존 |

#### 워크로드 마이그레이션 체크리스트

- Route, policy/default, CRD/operator, image trigger, build·rollout hook을 모두 조사합니다.
- 대표 workload로 target 동작과 ServiceAccount/RBAC 범위를 검증합니다.
- 데이터 일관성, snapshot/restore, DNS/TLS, network 통제·관찰성을 확인합니다.
- 원본 폐기 전에 cutover·rollback을 연습합니다.

#### 단계별 마이그레이션

의존성 평가 → 대표 비핵심 workload pilot → 통제된 wave 전환 → 데이터·운영 수락과 복구 증거 보존 → 합의한 rollback 기간 후 폐기 순서로 진행합니다.

## 설치 후 검증

검증 중 패키지를 재설치하거나 가입한 호스트를 초기화하지 않습니다. 아래 읽기는 관측일 뿐이며 프로세스 활성 상태나 과거 Ready만으로 workload를 수락하지 않습니다.

```bash
# Read-only, on the host mapped to the intended Kubernetes Node:
set -euo pipefail
cat /etc/os-release
uname -m -r
/usr/local/bin/nodeadm --version
containerd --version
for service in containerd kubelet; do
  systemctl is-active --quiet "$service"
done
```

```bash
# From the approved administrative context; these are reads, not installation:
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved context}"
: "${NODE:?Set the actual registered Node name from inventory}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o yaml
```

Node와 실제 호스트의 인벤토리 대응을 사용하고 새 Lease·버전, CNI/DNS/storage와 [bootstrap](./04-node-bootstrap.md)·[수명주기](./07-node-lifecycle.md)의 승인한 workload 검증을 확인합니다. 실패·확인 불가를 통과로 처리하지 않습니다.

## 트러블슈팅

| 문제 | 확인과 제한된 다음 단계 |
| --- | --- |
| Boot 실패 | Firmware mode, signed loader, DHCP/HTTP/TFTP 설계, NIC driver·승인한 image checksum |
| Autoinstall/Kickstart 실패 | Installer log/schema, 대상 disk, repository/stage2·호스트별 설정; 파괴적인 partition 재시도 금지 |
| Ubuntu 종료 문제 | 실제 AppArmor signal-denial 증거, fixed package/backport·필요한 계획 reboot |
| RHEL containerd | 지원되는 docker/none source, 실제 runtime·SELinux policy |
| nodeadm/인증 | 현재 nodeadm, private config, AWS private 연결, identity·trust; 무조건 재등록 금지 |

## 검증 범위와 참고 자료

로컬에서 schema·구성·명령 대체 검사 50개, artifact/host/API 읽기 subprocess 사례 12개, pykickstart 3.78 RHEL9 parser와 Decimal 요금 검증 10개를 확인했습니다. Canonical Autoinstall schema는 추가 root key를 허용하므로 선택한 installer의 검증을 대신하지 않습니다. 실제 OS 설치, disk 삭제, boot/login, Packer image build, Ansible SSH 작업, nodeadm 실행, VM 생성, AWS/Kubernetes 호출은 수행하지 않았습니다. 시험 대상과 실행 파일은 합성 fixture였습니다.

- [AWS Hybrid OS requirements](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [AWS Hybrid nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS EKS pricing](https://aws.amazon.com/eks/pricing/)
- [AWS Packer example](https://github.com/aws/eks-hybrid/tree/main/example/packer)
- [Canonical Autoinstall reference](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [RHEL 9 Kickstart reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/automatically_installing_rhel/kickstart-commands-and-options-reference_rhel-installer)
- [Ubuntu bug 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)
- [aa-remove-unknown manual](https://manpages.ubuntu.com/manpages/noble/man8/aa-remove-unknown.8.html)
- [AL2023 outside EC2](https://docs.aws.amazon.com/linux/al2023/ug/outside-ec2.html)
- [Operator Lifecycle Manager](https://olm.operatorframework.io/docs/)
- [OpenShift SCC API](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_apis/securitycontextconstraints-security-openshift-io-v1)


---

< [이전: 운영 및 유지보수](./08-operations.md) | [목차](./README.md) | [다음: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >
