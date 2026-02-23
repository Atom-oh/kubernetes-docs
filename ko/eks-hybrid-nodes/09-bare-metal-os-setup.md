# 베어메탈 서버 OS 설치 및 마이그레이션 가이드

< [이전: 운영 및 유지보수](./08-operations.md) | [목차](./README.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+
> **마지막 업데이트**: 2026년 2월 23일

이 문서에서는 베어메탈 서버에 EKS Hybrid Nodes를 배포하기 위한 OS 설치 방법과 VMware/OpenShift에서의 마이그레이션 전략을 다룹니다.

## 개요

### 베어메탈을 선택하는 이유

베어메탈 서버에서 EKS Hybrid Nodes를 실행하면 다음과 같은 이점이 있습니다:

1. **VMware 라이선스 비용 절감**: Broadcom의 VMware 인수 후 구독 모델로 전환되면서 라이선스 비용이 크게 증가했습니다.
2. **OpenShift 구독 비용 절감**: Red Hat OpenShift의 노드당 구독 비용을 제거할 수 있습니다.
3. **하이퍼바이저 오버헤드 제거**: 가상화 레이어 없이 워크로드를 직접 실행하여 성능을 최적화합니다.
4. **라이선스 관리 단순화**: 복잡한 라이선스 계약 및 감사 대응 부담을 줄일 수 있습니다.

### OS 인프라 지원 매트릭스

| OS | 베어메탈 | VMware | 자격 증명 | 설정 도구 |
|----|---------|--------|-----------|-----------|
| Ubuntu 22.04/24.04 LTS | O | O | SSM / IAM RA | nodeadm (YAML) |
| RHEL 8/9 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Amazon Linux 2023 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Bottlerocket v1.37.0+ | X | O (VMware만) | SSM / IAM RA | govc (TOML) |

> **참고**: Bottlerocket은 VMware 환경에서만 지원됩니다. 베어메탈 서버에는 Ubuntu, RHEL, 또는 Amazon Linux 2023을 사용해야 합니다.

## 비용 비교 분석

### 라이선스/구독 비용 비교

#### VMware vSphere
Broadcom 인수 후 영구 라이선스에서 구독 모델로 전환되었습니다:
- Enterprise Plus 라이선스: CPU 소켓당 연간 약 $4,500-8,500
- vSAN, NSX-T 등 추가 구성 요소는 별도 비용

#### OpenShift
Red Hat 구독 기반:
- 노드당 연간 약 $2,500-5,000 (코어 기반 구독)
- 프리미엄 지원 포함

#### EKS Hybrid Nodes
- vCPU당 시간당 $0.01 (리전별 상이)
- 추가 라이선스 없음

### 규모별 연간 비용 비교 (32 vCPU 서버 기준)

| 규모 | VMware vSphere (연간) | OpenShift (연간) | EKS Hybrid Nodes (연간) |
|------|----------------------|------------------|------------------------|
| 10 노드 | ~$45,000-85,000 | ~$25,000-50,000 | ~$28,032 |
| 50 노드 | ~$225,000-425,000 | ~$125,000-250,000 | ~$140,160 |
| 100 노드 | ~$450,000-850,000 | ~$250,000-500,000 | ~$280,320 |

> **계산 방식**: EKS Hybrid Nodes = 32 vCPU × $0.01/시간 × 8,760시간 = $2,803.20/노드/년
>
> **참고**: 위 비용은 추정치이며 실제 비용은 계약 조건, 리전, 할인 등에 따라 달라질 수 있습니다.

### TCO(총 소유 비용) 고려 사항

라이선스/구독 비용 외에도 다음 요소를 고려해야 합니다:
- 운영 인력 교육 비용
- 라이선스 관리 및 감사 대응 오버헤드
- 기술 지원 및 컨설팅 비용
- 마이그레이션 비용 (일회성)

## OS별 베어메탈 설치

### 사전 준비

#### BIOS/UEFI 설정
- PXE 부트 우선순위 설정
- Secure Boot 비활성화 또는 서명된 부트로더 사용
- 가상화 확장(VT-x/AMD-V) 활성화 (containerd에서 사용)

#### 네트워크 인프라
- DHCP 서버: IP 주소 및 PXE 부트 정보 제공
- TFTP 서버: 부트로더 및 커널 이미지 제공
- HTTP 서버: OS 설치 이미지 및 설정 파일 제공

#### AWS Packer 템플릿
베어메탈용 이미지 생성 시 `CREDENTIAL_PROVIDER` 환경 변수 설정:

```bash
# Qcow2 또는 Raw 포맷 이미지 생성
export CREDENTIAL_PROVIDER=ssm  # 또는 iam-ra

packer build \
  -var "credential_provider=${CREDENTIAL_PROVIDER}" \
  -var "output_format=raw" \
  bare-metal-template.pkr.hcl
```

### Ubuntu LTS (22.04/24.04)

Ubuntu는 Autoinstall (cloud-init 기반)을 사용하여 PXE 자동 설치를 수행합니다.

#### Autoinstall 설정 예시

```yaml
#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  network:
    ethernets:
      ens0:
        dhcp4: true
    version: 2
  storage:
    layout:
      name: lvm
  identity:
    hostname: hybrid-node
    username: ubuntu
    password: "$6$rounds=4096$..."  # 암호화된 비밀번호
  ssh:
    install-server: true
    authorized-keys:
      - ssh-rsa AAAA...  # SSH 공개 키
  packages:
    - curl
    - jq
    - open-iscsi
    - nfs-common
  late-commands:
    - curtin in-target -- bash -c 'curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm && chmod +x nodeadm && mv nodeadm /usr/local/bin/'
```

#### Ubuntu 24.04 특이사항

Ubuntu 24.04에서는 containerd v1.7.19 이상이 필요하거나 AppArmor 프로파일 변경이 필요합니다 (Ubuntu 버그 #2065423):

```bash
# containerd 버전 확인
containerd --version

# 버전이 1.7.19 미만인 경우 AppArmor 프로파일 수정
sudo aa-remove-unknown

# 변경 적용을 위해 재부팅 필요
sudo reboot
```

> **중요**: AppArmor 변경 후 반드시 재부팅해야 합니다. 재부팅하지 않으면 Pod가 정상적으로 종료되지 않을 수 있습니다.

### RHEL 9

RHEL은 Kickstart를 사용하여 PXE 자동 설치를 수행합니다.

#### Kickstart 설정 예시

```bash
# ks.cfg
lang en_US.UTF-8
keyboard us
timezone Asia/Seoul --utc
rootpw --iscrypted $6$rounds=4096$...
network --bootproto=dhcp --device=ens0 --activate
autopart --type=lvm
clearpart --all --initlabel

%packages
@core
curl
jq
container-tools
%end

%post
# nodeadm 설치
curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm && mv nodeadm /usr/local/bin/

# SELinux 설정 (필요시)
semanage permissive -a container_t
%end
```

#### RHEL containerd 설치 주의사항

RHEL에서는 반드시 `--containerd-source docker` 옵션을 사용해야 합니다. 배포판 기본 소스는 지원되지 않습니다:

```bash
# 올바른 설치 방법
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker

# 잘못된 설치 방법 (실패함)
# sudo nodeadm install 1.31 --credential-provider ssm
```

#### 대규모 환경: Satellite/Foreman 통합

대규모 RHEL 배포 환경에서는 Red Hat Satellite 또는 Foreman을 사용하여:
- Kickstart 템플릿 중앙 관리
- 패키지 저장소 미러링
- 프로비저닝 워크플로우 자동화

### Amazon Linux 2023

Amazon Linux 2023은 cloud-init 기반 설정을 사용합니다.

```yaml
#cloud-config
hostname: hybrid-node
users:
  - name: ec2-user
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-rsa AAAA...

packages:
  - curl
  - jq

runcmd:
  - curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
  - chmod +x nodeadm && mv nodeadm /usr/local/bin/
```

> **AWS Support 주의사항**: Amazon Linux 2023을 EC2 외부(베어메탈)에서 실행하는 경우 AWS Support Plans이 적용되지 않습니다. 커뮤니티 지원만 제공됩니다.

### Bottlerocket on VMware (참고)

Bottlerocket은 VMware 환경에서만 지원됩니다 (v1.37.0+, x86_64만).

- nodeadm을 사용하지 않고 `settings.toml`로 설정
- govc를 사용한 배포 워크플로우: 템플릿 복제 → user-data 주입 → 전원 켜기

Bottlerocket TOML 설정에 대한 자세한 내용은 [04-node-bootstrap.md](./04-node-bootstrap.md)를 참조하세요.

## 자격 증명 프로바이더 설정 비교

### nodeadm 기반 설정 (Ubuntu/RHEL/AL2023)

```yaml
# nodeconfig.yaml - SSM 방식
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
```

```yaml
# nodeconfig.yaml - IAM Roles Anywhere 방식
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/...
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/...
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

### Bottlerocket 기반 설정 (VMware)

```toml
# settings.toml - SSM 방식
[settings.hybrid.ssm]
activation-code = "<activation-code>"
activation-id = "<activation-id>"

[settings.kubernetes]
cluster-name = "my-cluster"
```

```toml
# settings.toml - IAM Roles Anywhere 방식
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "arn:aws:rolesanywhere:..."
profile-arn = "arn:aws:rolesanywhere:..."
role-arn = "arn:aws:iam::..."
certificate-path = "/etc/eks/pki/node.crt"
private-key-path = "/etc/eks/pki/node.key"
```

### 자격 증명 프로바이더 선택 가이드

| 조건 | 권장 프로바이더 |
|------|----------------|
| PKI 인프라 없음 | SSM |
| 기존 PKI 인프라 있음 | IAM Roles Anywhere |
| 사용자 정의 노드 이름 필요 | IAM Roles Anywhere |
| 에어갭(air-gapped) 환경 | IAM Roles Anywhere |
| 간단한 설정, 인터넷 연결 가능 | SSM |

## 대규모 프로비저닝 자동화

### PXE 부트 인프라 구성

```
┌─────────────────────────────────────────────────────────┐
│                    PXE 부트 서버                         │
├─────────────────────────────────────────────────────────┤
│  DHCP 서버                                              │
│  ├── IP 주소 할당                                       │
│  ├── next-server: TFTP 서버 주소                        │
│  └── filename: pxelinux.0                              │
├─────────────────────────────────────────────────────────┤
│  TFTP 서버                                              │
│  ├── pxelinux.0 (부트로더)                              │
│  ├── vmlinuz (커널)                                     │
│  └── initrd.img (초기 RAM 디스크)                       │
├─────────────────────────────────────────────────────────┤
│  HTTP 서버                                              │
│  ├── OS 설치 이미지                                     │
│  ├── Autoinstall/Kickstart 설정 파일                    │
│  └── nodeadm 바이너리                                   │
└─────────────────────────────────────────────────────────┘
```

### Ansible 자동화 플레이북

```yaml
# provision-hybrid-nodes.yaml
---
- hosts: hybrid_nodes
  become: true
  vars:
    k8s_version: "1.31"
    cred_provider: "ssm"
    cluster_name: "my-cluster"
    region: "ap-northeast-2"

  tasks:
    - name: nodeadm 다운로드
      get_url:
        url: https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
        dest: /usr/local/bin/nodeadm
        mode: '0755'

    - name: EKS 컴포넌트 설치
      command: >
        nodeadm install {{ k8s_version }}
        --credential-provider {{ cred_provider }}
        {% if ansible_distribution == 'RedHat' %}--containerd-source docker{% endif %}
      args:
        creates: /usr/bin/kubelet

    - name: 노드 설정 파일 배포
      template:
        src: nodeconfig.yaml.j2
        dest: /etc/eks/nodeconfig.yaml
        mode: '0600'

    - name: 노드 초기화
      command: nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
      register: init_result
      changed_when: init_result.rc == 0
```

대규모 플릿 관리에 대한 자세한 내용은 [07-node-lifecycle.md](./07-node-lifecycle.md)를 참조하세요.

## 마이그레이션 전략

### VMware → 베어메탈 + EKS Hybrid Nodes

#### Phase 1: 병행 운영 인프라 구축
- EKS 클러스터 및 하이브리드 노드 인프라를 VMware와 병행하여 배포
- 네트워크 연결 구성 (Direct Connect/VPN)
- Bottlerocket on VMware를 사용하여 전환 기간 동안 공존 가능

#### Phase 2: 워크로드 컨테이너화
- VM 기반 워크로드를 컨테이너로 마이그레이션
- 상태 저장 워크로드는 CSI 드라이버 구성 후 이전
- 데이터베이스는 AWS 관리형 서비스로 이전 고려

#### Phase 3: 네트워크 전환
- NSX-T에서 Cilium BGP로 전환
- 로드 밸런서 및 인그레스 설정 이전
- DNS 레코드 업데이트

#### Phase 4: VMware 폐기
- 모든 워크로드 마이그레이션 완료 확인
- VMware 라이선스 종료
- 하드웨어 재활용 또는 폐기

### OpenShift → EKS Hybrid Nodes

#### 개념 매핑

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC (Security Context Constraints) | PSS (Pod Security Standards) |
| OLM (Operator Lifecycle Manager) | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD (CodeBuild, GitHub Actions) |
| DeploymentConfig | Deployment (표준 Kubernetes) |

#### 워크로드 마이그레이션 체크리스트

- [ ] Route를 Ingress 또는 Gateway API로 변환
- [ ] SCC를 PSS로 매핑하여 Pod 보안 설정 조정
- [ ] OLM 관리 Operator를 Helm Chart 또는 EKS Add-on으로 대체
- [ ] ImageStream 참조를 ECR 이미지 URL로 변경
- [ ] BuildConfig를 GitHub Actions/CodeBuild 파이프라인으로 재구성
- [ ] DeploymentConfig를 표준 Deployment로 변환
- [ ] 서비스 어카운트 및 RBAC 설정 검토

#### 단계별 마이그레이션

1. **평가 단계**: 현재 OpenShift 워크로드 인벤토리 작성
2. **파일럿 단계**: 비핵심 워크로드를 EKS Hybrid Nodes로 마이그레이션
3. **전환 단계**: 핵심 워크로드 순차적 마이그레이션
4. **완료 단계**: OpenShift 클러스터 폐기

## 설치 후 검증

```bash
#!/bin/bash
# verify-bare-metal.sh

echo "=== OS 레벨 검증 ==="
# OS 버전 확인
cat /etc/os-release

# 커널 버전 확인
uname -r

# containerd 상태 확인
systemctl status containerd

# nodeadm 버전 확인
nodeadm version

echo "=== EKS 통합 검증 ==="
# 설치 및 초기화
sudo nodeadm install 1.31 --credential-provider ssm
sudo nodeadm init --config-source file://nodeconfig.yaml

# 클러스터에서 노드 확인
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid

# 노드 상세 정보 확인
kubectl describe node <node-name> | grep -A 5 "Labels:"
```

부트스트랩 과정에 대한 자세한 내용은 [04-node-bootstrap.md](./04-node-bootstrap.md)를 참조하세요.

## 트러블슈팅

| 문제 | 증상 | 해결 방법 |
|------|------|----------|
| PXE 부트 실패 | 노드가 네트워크에서 부팅되지 않음 | DHCP/TFTP 설정 확인, BIOS 부트 순서 확인, 네트워크 케이블 점검 |
| Autoinstall 타임아웃 | Ubuntu 설치가 멈춤 | cloud-init YAML 문법 검증, HTTP 서버 접근성 확인 |
| Kickstart 오류 | RHEL 설치 실패 | ks.cfg 문법 검증, 미디어 접근성 확인 |
| Ubuntu 24.04 containerd | Pod가 종료되지 않음 | containerd를 v1.7.19+로 업데이트, AppArmor 변경 후 재부팅 |
| RHEL containerd | 설치 실패 | `--containerd-source docker` 플래그 사용 |
| nodeadm init 실패 | 연결 타임아웃 | VPN/Direct Connect 연결 확인, 방화벽 포트 점검 |

---

< [이전: 운영 및 유지보수](./08-operations.md) | [목차](./README.md) >
