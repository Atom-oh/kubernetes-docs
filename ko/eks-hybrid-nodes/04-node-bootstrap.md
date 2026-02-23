# 노드 부트스트랩

< [이전: 에어갭 환경 구성](./03-airgap-setup.md) | [목차](./README.md) | [다음: GPU 서버 통합](./05-gpu-integration.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+
> **마지막 업데이트**: 2026년 2월 23일

이 문서에서는 nodeadm CLI를 사용하여 온프레미스 노드를 EKS 클러스터에 부트스트랩하는 방법을 다룹니다.

## 부트스트랩 워크플로우 개요

다음 단계는 IAM 자격 증명 설정부터 완전히 준비된 하이브리드 노드까지의 전체 노드 부트스트랩 프로세스를 설명합니다.

### 부트스트랩 단계

1. **IAM 자격 증명 준비** — SSM Hybrid Activation 생성 또는 IAM Roles Anywhere 구성
2. **nodeadm 다운로드** — 아키텍처에 맞는 CLI 도구 다운로드
3. **의존성 설치** — `nodeadm install`로 containerd, kubelet, kubectl, 자격 증명 프로바이더 설치
4. **NodeConfig YAML 작성** — 클러스터 세부 정보, 자격 증명, kubelet, containerd 구성
5. **CA 인증서 설치** — 프라이빗 레지스트리 CA 인증서를 시스템 신뢰 저장소에 추가 (필요 시)
6. **`nodeadm init` 실행** — 노드 초기화 및 EKS 클러스터에 등록
7. **CNI 설치** — Helm을 통해 Cilium 배포하여 파드 네트워킹 구성
8. **등록 확인** — `kubectl get nodes`에서 노드가 `Ready` 상태인지 확인

## nodeadm CLI 설치

nodeadm은 EKS Hybrid Nodes를 초기화하고 관리하는 CLI 도구입니다.

```bash
# nodeadm 다운로드 (Linux x86_64)
curl -OL 'https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm'

# ARM 노드의 경우:
# curl -OL 'https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/arm64/nodeadm'

chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/
```

## 의존성 설치

`nodeadm install` 명령으로 containerd, kubelet, kubectl, 자격 증명 프로바이더(SSM Agent 또는 IAM Roles Anywhere)를 설치합니다.

```bash
# SSM 자격 증명 프로바이더 사용 시
sudo nodeadm install 1.31 --credential-provider ssm

# IAM Roles Anywhere 사용 시
sudo nodeadm install 1.31 --credential-provider iam-ra

# 네트워크가 느린 환경에서는 타임아웃 증가
# sudo nodeadm install 1.31 --credential-provider ssm --timeout 20m0s
```

> **참고**: `nodeadm install`은 반드시 root 권한으로 실행해야 합니다. 이 단계에서 필요한 모든 Kubernetes 바이너리와 런타임 의존성이 설치됩니다.

### 설치 파일 경로

| 구성 요소 | Ubuntu/AL2023 경로 | RHEL 경로 |
|-----------|-------------------|-----------|
| kubelet | /usr/bin/kubelet | /usr/bin/kubelet |
| kubectl | /usr/bin/kubectl | /usr/bin/kubectl |
| SSM Agent | /snap/amazon-ssm-agent (Ubuntu) / systemd (AL2023) | /usr/bin/amazon-ssm-agent |
| containerd | /usr/bin/containerd | /usr/bin/containerd |
| nodeadm | /usr/local/bin/nodeadm | /usr/local/bin/nodeadm |

## NodeConfig YAML 작성

```yaml
# nodeconfig.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXXXXXXXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      -----BEGIN CERTIFICATE-----
      MIIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      -----END CERTIFICATE-----
    cidr: 10.100.0.0/16  # Service CIDR

  # 자격 증명 방식 선택 (SSM 또는 IAM Roles Anywhere)
  hybrid:
    # 방법 1: SSM Hybrid Activations
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

    # 방법 2: IAM Roles Anywhere (주석 해제하여 사용)
    # iamRolesAnywhere:
    #   nodeName: hybrid-node-001  # 인증서 CN과 일치해야 함 (최대 64자)
    #   trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
    #   profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
    #   roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
    #   certificatePath: /etc/iam/pki/server.pem   # 공식 기본 경로
    #   privateKeyPath: /etc/iam/pki/server.key     # 공식 기본 경로

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu
      - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule

  # containerd 추가 설정 (프라이빗 레지스트리 사용 시)
  # containerd:
  #   config: |
  #     version = 2
  #     [plugins."io.containerd.grpc.v1.cri".registry]
  #       config_path = "/etc/containerd/certs.d"
```

## SSM Hybrid Activation 생성

```bash
# SSM Hybrid Activation 생성
aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" \
  --registration-limit 100 \
  --region ap-northeast-2 \
  --tags "Key=Environment,Value=Production" "Key=NodeType,Value=Hybrid"

# 출력된 ActivationCode와 ActivationId를 nodeconfig.yaml에 입력
```

## IAM Roles Anywhere 설정 (대안)

SSM 대신 IAM Roles Anywhere를 사용하는 경우, Trust Anchor, Profile, 인증서를 구성합니다:

```bash
# Trust Anchor 생성
TRUST_ANCHOR_ARN=$(aws rolesanywhere create-trust-anchor \
  --name "eks-hybrid-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat ca.pem)}" \
  --enabled \
  --query 'trustAnchor.trustAnchorArn' --output text)

# Profile 생성
PROFILE_ARN=$(aws rolesanywhere create-profile \
  --name "eks-hybrid-profile" \
  --role-arns arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --enabled \
  --query 'profile.profileArn' --output text)

echo "Trust Anchor ARN: $TRUST_ANCHOR_ARN"
echo "Profile ARN: $PROFILE_ARN"
# 이 값들을 nodeconfig.yaml의 spec.hybrid.iamRolesAnywhere에 입력합니다
```

IAM Roles Anywhere용 NodeConfig YAML:

```yaml
spec:
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001  # 인증서 CN과 일치해야 함 (최대 64자)
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem   # 공식 기본 경로
      privateKeyPath: /etc/iam/pki/server.key     # 공식 기본 경로
```

> **참고**: IAM Roles Anywhere 프로필에서 반드시 **"Accept custom role session name"** (`acceptRoleSessionName: true`)을 활성화해야 합니다. 또한 IAM 역할의 `MaxSessionDuration`이 프로필의 `durationSeconds`보다 커야 합니다.

## CA 인증서 시스템 설치 (프라이빗 레지스트리 사용 시)

프라이빗 컨테이너 레지스트리를 사용하는 경우, CA 인증서를 시스템 신뢰 저장소에 추가합니다.

```bash
# Ubuntu
sudo cp ca.crt /usr/local/share/ca-certificates/registry-ca.crt
sudo update-ca-certificates

# RHEL/Amazon Linux 2023
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/registry-ca.crt
sudo update-ca-trust extract

# containerd가 인증서를 찾을 수 있도록 디렉토리 구성 (예시)
REGISTRY_HOST="registry.internal.company.io"
sudo mkdir -p /etc/containerd/certs.d/${REGISTRY_HOST}
cat <<EOF | sudo tee /etc/containerd/certs.d/${REGISTRY_HOST}/hosts.toml
server = "https://${REGISTRY_HOST}"

[host."https://${REGISTRY_HOST}"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
EOF
```

> **참고**: ECR VPC 엔드포인트를 통해 이미지를 가져오는 경우, CA 인증서 설치는 필요하지 않습니다. ECR은 AWS 공인 인증서를 사용합니다.

## 노드 초기화

### 구성 검증

노드 초기화 전에 구성 파일을 검증하는 것을 권장합니다:

```bash
# 구성 검증 (노드 초기화 전 실행 권장)
nodeadm config check --config-source file://nodeconfig.yaml
```

### 초기화 실행

```bash
# nodeadm을 사용하여 노드 초기화
sudo nodeadm init -c file://nodeconfig.yaml

# 초기화 로그 확인
sudo journalctl -u kubelet -f

# 노드 상태 확인 (EKS 클러스터에서)
kubectl get nodes -o wide
```

## 노드 등록 확인

```bash
# 노드 목록 확인
kubectl get nodes --show-labels

# 예상 출력:
# NAME                STATUS   ROLES    AGE   VERSION   LABELS
# ip-10-0-1-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2a
# ip-10-0-2-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2b
# hybrid-node-001     Ready    <none>   5m    v1.31.0   eks.amazonaws.com/compute-type=hybrid

# 노드 상세 정보 확인
kubectl describe node hybrid-node-001

# Hybrid Node 필터링
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid
```

---

## systemd를 통한 자동 부트스트랩

대규모 배포 환경에서는 노드가 부팅될 때 자동으로 `nodeadm install`과 `nodeadm init`이 실행되도록 systemd 서비스를 구성할 수 있습니다. 마커 파일을 사용하여 최초 부팅에서만 install이 실행되고, 이후 부팅에서는 건너뜁니다.

### 사전 준비

자동 부트스트랩을 사용하려면 다음 파일이 노드에 미리 배치되어 있어야 합니다:

- `/etc/eks/nodeconfig.yaml` — NodeConfig 설정 파일
- `/etc/eks/bootstrap.env` — 부트스트랩 환경 변수
- `/usr/local/bin/nodeadm` — nodeadm 바이너리

> **참고**: 이 파일들은 VM 이미지 빌드(Packer 등), cloud-init, 또는 구성 관리 도구(Ansible 등)를 통해 사전 배치할 수 있습니다.

### 환경 설정 파일

```bash
# /etc/eks/bootstrap.env
K8S_VERSION="1.31"
CREDENTIAL_PROVIDER="ssm"          # ssm 또는 iam-ra
NODECONFIG_PATH="/etc/eks/nodeconfig.yaml"
```

### 부트스트랩 스크립트

```bash
#!/bin/bash
# /usr/local/bin/eks-hybrid-bootstrap.sh
set -euo pipefail

LOG_TAG="eks-hybrid-bootstrap"
MARKER_DIR="/var/lib/eks"
INSTALL_MARKER="${MARKER_DIR}/.nodeadm-installed"
INIT_MARKER="${MARKER_DIR}/.nodeadm-initialized"

# 환경 변수 로드
source /etc/eks/bootstrap.env

log() { logger -t "$LOG_TAG" "$1"; echo "[$(date '+%H:%M:%S')] $1"; }

mkdir -p "$MARKER_DIR"

# --- install 단계 (최초 1회만) ---
if [ -f "$INSTALL_MARKER" ]; then
  log "nodeadm install 이미 완료됨 — 건너뜀"
else
  log "nodeadm install ${K8S_VERSION} 시작 (credential-provider: ${CREDENTIAL_PROVIDER})"
  nodeadm install "${K8S_VERSION}" --credential-provider "${CREDENTIAL_PROVIDER}"
  touch "$INSTALL_MARKER"
  log "nodeadm install 완료"
fi

# --- init 단계 (최초 1회만) ---
if [ -f "$INIT_MARKER" ]; then
  log "nodeadm init 이미 완료됨 — 건너뜀"
else
  log "nodeadm init 시작"
  nodeadm init -c "file://${NODECONFIG_PATH}"
  touch "$INIT_MARKER"
  log "nodeadm init 완료 — 노드가 EKS 클러스터에 등록됨"
fi
```

```bash
sudo chmod +x /usr/local/bin/eks-hybrid-bootstrap.sh
```

### systemd 서비스 유닛

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=EKS Hybrid Node Bootstrap (install + init)
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/eks/.nodeadm-initialized

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> **ConditionPathExists**: `!` 접두사는 해당 파일이 **없을 때만** 서비스가 실행됨을 의미합니다. init이 완료되면 마커 파일이 생성되어 이후 부팅에서는 서비스가 자동으로 건너뛰어집니다.

### 서비스 활성화

```bash
sudo systemctl daemon-reload
sudo systemctl enable eks-hybrid-bootstrap.service
```

### 동작 확인

```bash
# 서비스 상태 확인
sudo systemctl status eks-hybrid-bootstrap.service

# 부트스트랩 로그 확인
sudo journalctl -u eks-hybrid-bootstrap.service

# 마커 파일 확인
ls -la /var/lib/eks/.nodeadm-*
```

### 재설치가 필요한 경우

노드를 초기화부터 다시 시작하려면 마커 파일을 삭제한 후 재부팅합니다:

```bash
# 기존 상태 정리
sudo nodeadm uninstall
sudo rm -f /var/lib/eks/.nodeadm-installed /var/lib/eks/.nodeadm-initialized

# 재부팅 시 자동으로 install + init 재실행
sudo reboot
```

### 자주 묻는 질문

**Q: systemd 유닛 파일의 각 설정은 무엇을 의미하나요?**

| 설정 | 의미 |
|------|------|
| `Type=oneshot` | 부팅 시 한 번 실행되고 종료되는 서비스 |
| `After=network-online.target` | 네트워크가 완전히 준비된 후 실행 |
| `ConditionPathExists=!/var/lib/eks/.nodeadm-initialized` | `!` 접두사 — 마커 파일이 **없을 때만** 실행 |
| `RemainAfterExit=true` | 프로세스 종료 후에도 서비스가 active 상태로 유지 (상태 확인 가능) |
| `WantedBy=multi-user.target` | 일반 부팅 시 자동 실행 |

**Q: SSM activation code를 노드를 껐다 킬 때마다 다시 받아야 하나요?**

아닙니다. SSM Hybrid Activation의 `activationCode`/`activationId`는 `nodeadm init` 시 SSM 에이전트를 AWS에 등록할 때 한 번만 사용됩니다. 등록 이후에는 SSM 에이전트가 자체적으로 자격 증명을 갱신하므로, **일반적인 재부팅에서는 activation code가 다시 필요하지 않습니다**.

단, `nodeadm uninstall`을 실행하면 SSM 아티팩트가 삭제되어 재등록이 필요합니다. 이때 기존 activation의 `registration-limit`에 도달하지 않았다면 같은 코드를 재사용할 수 있습니다.

**Q: `nodeadm init`이 노드를 클러스터에 조인시키는 건가요?**

네. `nodeadm init`은 다음 단계를 순서대로 수행합니다:
1. kubelet 설정 파일 생성 (`/etc/kubernetes/`)
2. SSM 또는 IAM Roles Anywhere 자격 증명 등록
3. kubelet systemd 서비스 시작
4. kubelet이 EKS API 서버에 노드를 등록 (조인)

즉, `nodeadm init`이 실질적인 **클러스터 조인 명령**입니다.

**Q: SSM activation 등록은 `install`에서 되나요, `init`에서 되나요?**

| 단계 | SSM 관련 동작 |
|------|--------------|
| `nodeadm install --credential-provider ssm` | SSM Agent **바이너리 설치**만 수행 |
| `nodeadm init` | nodeconfig.yaml의 `activationCode`/`activationId`로 SSM Agent를 AWS에 **등록** |

SSM activation(등록)은 **init 단계**에서 수행됩니다.

**Q: SSM activation을 유지하면서 노드만 클러스터에서 제거/재등록하려면?**

`kubectl delete node <NODE_NAME>`을 실행해도 SSM 등록은 영향받지 않습니다 (SSM은 OS 레벨, 노드 등록은 Kubernetes 레벨). kubelet이 실행 중이면 자동으로 재등록됩니다:

```bash
# 클러스터에서 노드 제거
kubectl delete node hybrid-node-001

# kubelet이 실행 중이면 자동 재등록됨
# 중지된 경우 수동 재시작
sudo systemctl restart kubelet
```

**Q: `drain → delete → shutdown` 후 재부팅하면 systemd로 자동 재등록되나요?**

재등록은 되지만, systemd 부트스트랩 서비스가 아닌 **kubelet 서비스 자체**가 처리합니다:

1. `nodeadm init`은 kubelet을 systemd 서비스로 설치합니다
2. 재부팅 시 kubelet이 자동 시작되어 API 서버에 재등록됩니다
3. 부트스트랩 서비스는 마커 파일이 존재하므로 건너뛰어집니다 (이것이 정상 동작)

```bash
# 이 워크플로우에서는 마커 파일을 삭제할 필요 없음
kubectl drain hybrid-node-001 --ignore-daemonsets --delete-emptydir-data
kubectl delete node hybrid-node-001
# 노드 종료 후 재부팅 → kubelet이 자동으로 재등록
```

> **참고**: `nodeadm uninstall`을 실행한 경우에만 마커 파일을 삭제하고 부트스트랩 서비스를 통해 재설치해야 합니다.

---

## Cilium CNI 설치

Cilium은 EKS Hybrid Nodes를 위한 AWS 지원 CNI입니다. 하이브리드 노드는 CNI가 설치될 때까지 `Not Ready` 상태로 표시됩니다. Amazon VPC CNI는 하이브리드 노드와 **호환되지 않습니다**.

> **지원 버전**: Cilium v1.17.9 및 v1.18.3 (Amazon EKS 검증 버전)
> **Helm 저장소**: `oci://public.ecr.aws/eks/cilium/cilium`

> **Cilium 사전 요구 사항**:
> - **커널 요구 사항**: Cilium v1.18.x는 **Linux 커널 5.10 이상** 필요. Ubuntu 20.04 (커널 5.4), RHEL 8 (커널 4.18)은 기본 커널이 미달하므로 **지원되지 않습니다**
> - **하이브리드 노드 전용**: Cilium은 **하이브리드 노드에서만 지원**됩니다. AWS Cloud 노드에서는 VPC CNI를 사용하세요
> - **IPAM 설정 불변**: `clusterPoolIPv4PodCIDRList`와 `clusterPoolIPv4MaskSize`는 **초기 배포 후 변경할 수 없습니다**. 충분한 파드 CIDR 범위를 미리 계획하세요

### Cilium Values YAML 생성

```yaml
# cilium-values.yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: In
          values:
          - hybrid

ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList:
    - <POD_CIDR>  # EKS 클러스터의 원격 파드 네트워크와 동일

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
            values:
            - hybrid
  unmanagedPodWatcher:
    restart: false

envoy:
  enabled: false

kubeProxyReplacement: "false"
```

### Cilium 설치

```bash
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version 1.18.3-0 \
  --namespace kube-system \
  --values cilium-values.yaml
```

### 설치 확인

```bash
# Cilium 파드 실행 확인
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# 노드가 이제 Ready 상태로 표시되어야 함
kubectl get nodes -o wide
```

### Cilium 업그레이드

Cilium을 새 버전으로 업그레이드하는 절차입니다:

```bash
# 1. Preflight check (업그레이드 전 호환성 검증)
helm install cilium-preflight oci://public.ecr.aws/eks/cilium/cilium \
  --version NEW_VERSION \
  --namespace kube-system \
  --set preflight.enabled=true \
  --set agent=false --set operator.enabled=false

# 2. 기존 값 보존하여 업그레이드
helm upgrade cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version NEW_VERSION \
  --namespace kube-system \
  --reuse-values

# 3. 상태 확인
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# 4. 롤백 (문제 발생 시)
helm rollback cilium --namespace kube-system
```

### Cilium 삭제

Cilium을 완전히 제거하는 절차입니다:

```bash
# 1. Helm uninstall
helm uninstall cilium --namespace kube-system

# 2. CRD 삭제
kubectl get crds -o name | grep cilium | xargs kubectl delete

# 3. On-disk 정리 (각 노드에서 실행)
sudo rm -rf /var/run/cilium /var/lib/cilium /etc/cni/net.d/05-cilium.conflist
sudo rm -f /opt/cni/bin/cilium-cni
```

### Calico 지원 중단 안내

> **참고**: Calico는 EKS Hybrid Nodes에서 더 이상 공식 지원되지 않으며, `eks-hybrid-examples` 리포지토리로 이전되었습니다. 신규 배포에서는 Cilium을 사용하는 것을 권장합니다. 기존 Calico 배포는 계속 작동하지만 AWS의 공식 지원이 제한됩니다.

---

## Bottlerocket 설정

Bottlerocket은 VMware vSphere 환경에서만 지원되며 (v1.37.0+), x86_64 아키텍처만 지원됩니다. Bottlerocket은 **nodeadm을 사용하지 않으며**, TOML 기반 설정과 사용자 데이터를 통해 부트스트랩됩니다.

### SSM Hybrid Activation 설정 (settings.toml)

```toml
[settings.kubernetes]
cluster-name = "CLUSTER_NAME"
api-server = "API_SERVER_ENDPOINT"
cluster-certificate = "BASE64_CA_CERT"
service-cidr = "SERVICE_CIDR"

[settings.hybrid]
enable-credentials-file = true  # Pod Identity에 필요

[settings.hybrid.ssm]
activation-id = "ACTIVATION_ID"
activation-code = "ACTIVATION_CODE"
```

### IAM Roles Anywhere 설정 (settings.toml)

```toml
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "TRUST_ANCHOR_ARN"
profile-arn = "PROFILE_ARN"
role-arn = "ROLE_ARN"
node-name = "NODE_NAME"  # 인증서 CN과 일치해야 함
certificate-path = "/PATH/TO/CERT"
private-key-path = "/PATH/TO/KEY"
```

### govc를 사용한 VMware 배포

```bash
# VM 템플릿에서 복제
govc vm.clone -vm "/PATH/TO/TEMPLATE" -ds="DATASTORE" \
  -on=false -template=false -folder=/FOLDER "VM_NAME"

# 사용자 데이터 설정
govc vm.change -dc="DC" -vm "VM_NAME" \
  -e guestinfo.userdata="${USER_DATA}" \
  -e guestinfo.userdata.encoding=gzip+base64

# VM 시작
govc vm.power -on "VM_NAME"
```

> **참고**: `USER_DATA`는 settings.toml 내용을 gzip 압축 후 base64 인코딩한 값입니다.

---

## 웹훅 및 애드온 구성

### 웹훅 기반 애드온

웹훅을 사용하는 애드온(AWS Load Balancer Controller, CloudWatch Observability Agent, ADOT, cert-manager)은 컨트롤 플레인에서 파드 IP로의 네트워크 연결이 필요합니다.

- **라우팅 가능 파드 네트워크**: 하이브리드 노드에서 웹훅 실행 가능 (BGP 또는 정적 라우트 구성 필요)
- **라우팅 불가능 파드 네트워크**: 웹훅 기반 애드온은 **클라우드 노드에서만 실행** 필요

클라우드 노드에서만 실행하려면 다음 nodeAffinity를 설정하세요:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - hybrid
```

### CoreDNS 혼합 모드

하이브리드 노드와 클라우드 노드가 모두 있는 클러스터에서는 **양쪽에 최소 1개의 CoreDNS 레플리카**를 배포하세요. Kubernetes 1.31+에서는 Service Traffic Distribution을 활용하여 DNS 쿼리를 로컬 영역에서 처리할 수 있습니다.

### EKS Pod Identity Agent

Pod Identity를 사용하려면 NodeConfig에 `enableCredentialsFile: true`를 추가하고, 애드온 설치 시 하이브리드 DaemonSet을 활성화합니다:

```bash
aws eks create-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name eks-pod-identity-agent \
  --configuration-values '{"daemonsets":{"hybrid":{"create": true}}}'
```

---

## 노드 업그레이드

하이브리드 노드는 업스트림 Kubernetes와 동일한 버전 스큐 정책을 따릅니다 — 컨트롤 플레인보다 새로운 버전일 수 없으며 최대 3개의 마이너 버전까지 이전 버전일 수 있습니다.

### 컷오버 마이그레이션 (권장)

여유 용량이 있는 경우, 대상 버전으로 새 노드를 생성하고 워크로드를 점진적으로 마이그레이션합니다:

```bash
# 1. 대상 버전으로 새 호스트에 nodeadm 설치
nodeadm install K8S_VERSION --credential-provider CREDS_PROVIDER

# 2. 기존 노드 cordon
kubectl cordon NODE_NAME

# 3. 복원력을 위해 CoreDNS 스케일
kubectl scale deployments/coredns --replicas=2 -n kube-system

# 4. 기존 노드 drain
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 5. 기존 노드 제거
sudo nodeadm uninstall

# 6. 기존 노드 리소스 삭제
kubectl delete node NODE_NAME
```

### 인플레이스 업그레이드

여유 용량이 없는 경우, 노드를 인플레이스로 업그레이드합니다 (다운타임 발생):

```bash
# 1. 노드 cordon
kubectl cordon NODE_NAME

# 2. 워크로드 drain
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 3. nodeadm 업그레이드 실행
sudo nodeadm upgrade K8S_VERSION -c file://nodeConfig.yaml

# 4. 업그레이드 완료 후 uncordon
kubectl uncordon NODE_NAME

# 5. 모니터링
kubectl get nodes -o wide -w
```

---

## 트러블슈팅

### nodeadm debug

`nodeadm debug` 명령은 네트워크 액세스, 자격 증명 및 클러스터 연결을 검증합니다:

```bash
sudo nodeadm debug -c file://nodeConfig.yaml
```

검증 항목:
- AWS API에 대한 네트워크 액세스
- Hybrid Nodes IAM 역할에 대한 AWS 자격 증명 검색
- EKS Kubernetes API 엔드포인트에 대한 네트워크 액세스
- EKS 클러스터와의 노드 인증

### 일반적인 문제와 해결 방법

#### 설치 문제

| 문제 | 증상 | 해결 방법 |
|------|------|-----------|
| root로 실행해야 함 | `"msg":"Command failed","error":"must run as root"` | `sudo`로 `nodeadm` 실행 |
| 종속성 연결 불가 | `max retries achieved for http request` | 종속성 저장소에 대한 네트워크 액세스 확인 |
| 패키지 관리자 실패 | `failed to run update using package manager` | 먼저 `apt update` 또는 `dnf update` 실행 |
| 타임아웃 | `context deadline exceeded` | `--timeout 20m0s` 플래그 사용 |

#### 연결 문제

| 문제 | 증상 | 해결 방법 |
|------|------|-----------|
| 노드 IP가 CIDR에 없음 | `node IP is not in any of the remote network CIDR blocks` | `RemoteNodeNetworks`에 노드 IP 범위가 포함되어 있는지 확인 |
| API 서버 접근 불가 | `Unable to connect to the server` / `dial tcp: i/o timeout` | VPN/DX 터널 확인, 방화벽 포트 443, TGW/VGW로의 VPC 라우트 확인 |
| 인증 실패 | `Failed to ensure lease exists: Unauthorized` | IAM 역할, `HYBRID_LINUX` 타입의 EKS 액세스 항목 확인 |
| Node가 NotReady 상태 유지 | 노드 등록되었으나 NotReady 상태 | CNI(Cilium) 설치, VXLAN 포트 8472 확인 |
| DNS 해석 실패 | EKS API 엔드포인트에 대해 `no such host` | Route 53 Resolver Inbound Endpoint 구성, 온프레미스 DNS 업데이트 |
| 이미지 Pull 실패 | 시스템 파드에서 `ErrImagePull` | ECR VPC 엔드포인트, containerd 레지스트리 설정, CA 인증서 확인 |
| 인증서 오류 | `x509: certificate signed by unknown authority` | 시스템 신뢰 저장소에 CA 인증서 설치, `update-ca-certificates` 실행 |
| 하이브리드 프로필 존재 | `hybrid profile already exists` | `nodeadm uninstall` 후 `nodeadm install` 후 `nodeadm init` 실행 |

#### SSM 자격 증명 문제

| 문제 | 증상 | 해결 방법 |
|------|------|-----------|
| 유효하지 않은 활성화 | `InvalidActivation` | nodeConfig.yaml에서 region, activationCode, activationId 확인 |
| 만료된 활성화 | `ActivationExpired` | 새 SSM 하이브리드 활성화 생성, nodeConfig.yaml 업데이트 |
| 만료된 토큰 | `ExpiredTokenException` | SSM 에이전트 재시작: `systemctl restart amazon-ssm-agent` |

#### IAM Roles Anywhere 문제

| 문제 | 증상 | 해결 방법 |
|------|------|-----------|
| 인증서를 찾을 수 없음 | `open /etc/iam/pki/server.pem: no such file or directory` | `/etc/iam/pki/` 디렉토리 생성, 인증서 및 키 복사 |
| 권한 없음 | `not authorized to perform: sts:AssumeRole` | 신뢰 정책, Trust Anchor ARN, IAM RA 프로필 확인 |

### 진단 명령어

```bash
# kubelet 상태 및 로그 확인
sudo systemctl status kubelet
sudo journalctl -u kubelet -f

# containerd 확인
sudo systemctl status containerd

# 자격 증명 검증
sudo aws sts get-caller-identity

# SSM 에이전트 확인 (AL2023/RHEL)
sudo systemctl status amazon-ssm-agent

# SSM 에이전트 확인 (Ubuntu)
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent

# nodeadm 진단 실행
sudo nodeadm debug -c file://nodeConfig.yaml
```

### 노드 리셋

부트스트랩이 실패하여 처음부터 다시 시작해야 하는 경우:

```bash
# 기본 삭제
sudo nodeadm uninstall

# 강제 삭제 (모든 상태 정리, 확인 프롬프트 건너뜀)
sudo nodeadm uninstall --force

# 초기화 재실행
sudo nodeadm init -c file://nodeconfig.yaml
```

**nodeadm uninstall이 삭제하는 경로:**
- `/etc/kubernetes` - Kubernetes 구성 파일
- `/etc/eks` - EKS 관련 구성
- SSM/IAM Roles Anywhere 아티팩트

**v1.0.9+ 변경 사항:**
- `/var/lib/kubelet`은 기본적으로 **보존됨** (데이터 보호 개선)
- `--force` 옵션 사용 시 보존되는 아티팩트를 포함한 모든 항목 삭제

---

< [이전: 에어갭 환경 구성](./03-airgap-setup.md) | [목차](./README.md) | [다음: GPU 서버 통합](./05-gpu-integration.md) >
