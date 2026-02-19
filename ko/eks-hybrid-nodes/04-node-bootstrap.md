# 노드 부트스트랩

< [이전: 에어갭 환경 구성](./03-airgap-setup.md) | [목차](./README.md) | [다음: GPU 서버 통합](./05-gpu-integration.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 nodeadm CLI를 사용하여 온프레미스 노드를 EKS 클러스터에 부트스트랩하는 방법을 다룹니다.

## nodeadm CLI 설치

nodeadm은 EKS Hybrid Nodes를 초기화하고 관리하는 CLI 도구입니다.

```bash
# nodeadm 다운로드 (Linux x86_64)
curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# 버전 확인
nodeadm version
```

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
    #   trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
    #   profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
    #   roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
    #   certificatePath: /etc/eks/pki/node.crt
    #   privateKeyPath: /etc/eks/pki/node.key

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=topology.kubernetes.io/zone=on-premises,node.kubernetes.io/instance-type=on-prem-gpu
      - --register-with-taints=location=on-premises:NoSchedule

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        config_path = "/etc/containerd/certs.d"

      [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal.company.io".tls]
        ca_file = "/etc/ssl/certs/harbor-ca.crt"

      [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal.company.io".auth]
        username = "robot$k8s-pull-robot"
        password = "<robot-account-token>"
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

## CA 인증서 시스템 설치

```bash
# Harbor CA 인증서 시스템에 설치 (Ubuntu)
sudo cp ca.crt /usr/local/share/ca-certificates/harbor-ca.crt
sudo update-ca-certificates

# RHEL/CentOS
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/harbor-ca.crt
sudo update-ca-trust extract

# containerd가 인증서를 찾을 수 있도록 디렉토리 구성
sudo mkdir -p /etc/containerd/certs.d/harbor.internal.company.io
cat <<EOF | sudo tee /etc/containerd/certs.d/harbor.internal.company.io/hosts.toml
server = "https://harbor.internal.company.io"

[host."https://harbor.internal.company.io"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/harbor-ca.crt"
EOF
```

## 노드 초기화

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
# hybrid-node-001     Ready    <none>   5m    v1.31.0   topology.kubernetes.io/zone=on-premises

# 노드 상세 정보 확인
kubectl describe node hybrid-node-001

# Hybrid Node 필터링
kubectl get nodes -l topology.kubernetes.io/zone=on-premises
```

---

< [이전: 에어갭 환경 구성](./03-airgap-setup.md) | [목차](./README.md) | [다음: GPU 서버 통합](./05-gpu-integration.md) >
