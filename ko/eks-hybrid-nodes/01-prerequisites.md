# 사전 요구 사항 및 시스템 요구 사항

< [목차](./README.md) | [다음: 네트워크 구성](./02-network-configuration.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 EKS Hybrid Nodes를 구성하기 위한 온프레미스 노드, GPU 서버, 네트워크 요구 사항을 다룹니다.

## 온프레미스 노드 요구 사항

### 지원 운영 체제

| 운영 체제 | 버전 | 아키텍처 |
|-----------|------|----------|
| Ubuntu LTS | 20.04, 22.04, 24.04 | x86_64, arm64 |
| RHEL | 8, 9 | x86_64, arm64 |
| Amazon Linux | 2023 | x86_64, arm64 |

### 컨테이너 런타임

```bash
# containerd 버전 확인
containerd --version
# 필요 버전: 1.6.x 이상

# Docker Engine 버전 확인 (containerd 포함)
docker --version
# 필요 버전: 20.10.10 이상
```

### 최소 하드웨어 사양

| 리소스 | 최소 사양 | 권장 사양 |
|--------|----------|----------|
| CPU | 2 코어 | 4 코어 이상 |
| RAM | 4 GB | 8 GB 이상 |
| 디스크 | 50 GB SSD | 100 GB NVMe SSD |
| 네트워크 | 1 Gbps | 10 Gbps 이상 |

### 시스템 설정 확인

```bash
# 스왑 비활성화 확인
free -h
# Swap이 0이어야 함

# 스왑 비활성화
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# 필요한 커널 모듈 로드
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# 커널 파라미터 설정
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

## GPU 서버 요구 사항 (선택사항)

### NVIDIA 드라이버

```bash
# NVIDIA 드라이버 버전 확인
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# 필요 버전: 550.x 이상

# CUDA 버전 확인
nvcc --version
# 권장 버전: CUDA 12.x
```

### 지원 GPU 모델

| GPU 모델 | VRAM | 주요 용도 |
|----------|------|----------|
| NVIDIA H100 | 80 GB | 대규모 LLM 학습/추론 |
| NVIDIA H200 | 141 GB | 초대규모 모델 |
| NVIDIA A100 | 40/80 GB | AI/ML 범용 |
| NVIDIA L40S | 48 GB | 추론 최적화 |

### GPU 드라이버 설치 (Ubuntu 예시)

```bash
# NVIDIA 드라이버 저장소 추가
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# 드라이버 설치 (버전 550)
sudo apt install -y nvidia-driver-550

# NVIDIA Container Toolkit 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

# containerd 설정 업데이트
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

## 네트워크 요구 사항

### 대역폭 및 지연 시간

| 항목 | 최소 요구 | 권장 사양 |
|------|----------|----------|
| 대역폭 | 1 Gbps | 10 Gbps 이상 |
| 지연 시간 | 50 ms 이하 | 5 ms 이하 |
| 패킷 손실 | 0.1% 이하 | 0.01% 이하 |
| MTU | 1500 | 9000 (Jumbo Frame) |

### Jumbo Frame 설정

```bash
# MTU 설정 확인
ip link show eth0 | grep mtu

# MTU 9000으로 설정 (임시)
sudo ip link set dev eth0 mtu 9000

# 영구 설정 (Ubuntu - Netplan)
cat <<EOF | sudo tee /etc/netplan/01-netcfg.yaml
network:
  version: 2
  ethernets:
    eth0:
      mtu: 9000
      dhcp4: true
EOF

sudo netplan apply
```

---

< [목차](./README.md) | [다음: 네트워크 구성](./02-network-configuration.md) >
