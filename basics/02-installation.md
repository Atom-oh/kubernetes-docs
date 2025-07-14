# Kubernetes 설치 및 구성

Kubernetes를 사용하기 위해서는 먼저 클러스터를 설치하고 구성해야 합니다. 이 장에서는 다양한 환경에서 Kubernetes를 설치하는 방법을 알아보겠습니다.

## 목차

1. [로컬 환경 설정](#로컬-환경-설정)
   - [Minikube](#minikube)
   - [Kind (Kubernetes in Docker)](#kind-kubernetes-in-docker)
   - [Docker Desktop](#docker-desktop)

2. [클라우드 환경 설정](#클라우드-환경-설정)
   - [Amazon EKS (Elastic Kubernetes Service)](#amazon-eks-elastic-kubernetes-service)
   - [Google GKE (Google Kubernetes Engine)](#google-gke-google-kubernetes-engine)
   - [Microsoft AKS (Azure Kubernetes Service)](#microsoft-aks-azure-kubernetes-service)

3. [베어메탈 설치](#베어메탈-설치)
   - [요구 사항](#요구-사항)
   - [kubeadm을 사용한 설치](#kubeadm을-사용한-설치)
   - [kubespray를 사용한 설치](#kubespray를-사용한-설치)

4. [클러스터 구성](#클러스터-구성)
   - [kubectl 설정](#kubectl-설정)
   - [네트워크 플러그인 설치](#네트워크-플러그인-설치)
   - [스토리지 클래스 구성](#스토리지-클래스-구성)
   - [인그레스 컨트롤러 설치](#인그레스-컨트롤러-설치)

## 로컬 환경 설정

로컬 개발 및 테스트 목적으로 Kubernetes를 설치하는 여러 방법이 있습니다. 가장 인기 있는 옵션은 Minikube, Kind, Docker Desktop입니다.

### Minikube

Minikube는 로컬 머신에서 단일 노드 Kubernetes 클러스터를 쉽게 실행할 수 있는 도구입니다. 주로 개발, 테스트 및 학습 목적으로 사용됩니다.

#### 요구 사항

- 2 CPU 이상
- 2GB 이상의 여유 메모리
- 20GB 이상의 여유 디스크 공간
- 인터넷 연결
- 컨테이너 또는 가상 머신 관리자(Docker, Hyperkit, Hyper-V, KVM, Parallels, Podman, VirtualBox, VMware)

#### 설치 방법

**macOS**:

```bash
# Homebrew를 사용한 설치
brew install minikube

# 또는 직접 다운로드
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-darwin-amd64
sudo install minikube-darwin-amd64 /usr/local/bin/minikube
```

**Linux**:

```bash
# 직접 다운로드
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

**Windows**:

```powershell
# Chocolatey를 사용한 설치
choco install minikube

# 또는 직접 다운로드
New-Item -Path 'c:\' -Name 'minikube' -ItemType Directory -Force
Invoke-WebRequest -OutFile 'c:\minikube\minikube.exe' -Uri 'https://github.com/kubernetes/minikube/releases/latest/download/minikube-windows-amd64.exe'
Add-MemberPath 'c:\minikube'
```

#### Minikube 시작하기

```bash
# 기본 설정으로 시작
minikube start

# 리소스 제한 설정
minikube start --cpus=4 --memory=8g

# 특정 Kubernetes 버전 지정
minikube start --kubernetes-version=v1.24.0

# 특정 드라이버 지정
minikube start --driver=docker
```

#### 유용한 Minikube 명령어

```bash
# 상태 확인
minikube status

# 대시보드 열기
minikube dashboard

# 클러스터 중지
minikube stop

# 클러스터 삭제
minikube delete

# 애드온 활성화
minikube addons enable ingress

# 서비스 URL 가져오기
minikube service my-service --url
```

### Kind (Kubernetes in Docker)

Kind는 Docker 컨테이너를 노드로 사용하여 로컬에서 Kubernetes 클러스터를 실행하는 도구입니다. 주로 Kubernetes 자체 테스트에 사용되지만, 로컬 개발에도 적합합니다.

#### 요구 사항

- Docker 설치
- 2GB 이상의 여유 메모리

#### 설치 방법

**macOS**:

```bash
# Homebrew를 사용한 설치
brew install kind

# 또는 직접 다운로드
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.17.0/kind-darwin-amd64
chmod +x ./kind
mv ./kind /usr/local/bin/kind
```

**Linux**:

```bash
# 직접 다운로드
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.17.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

**Windows**:

```powershell
# Chocolatey를 사용한 설치
choco install kind

# 또는 직접 다운로드
curl.exe -Lo kind-windows-amd64.exe https://kind.sigs.k8s.io/dl/v0.17.0/kind-windows-amd64
Move-Item .\kind-windows-amd64.exe c:\some-dir-in-your-PATH\kind.exe
```

#### Kind 클러스터 생성

```bash
# 기본 클러스터 생성
kind create cluster

# 이름이 지정된 클러스터 생성
kind create cluster --name my-cluster

# 구성 파일을 사용한 다중 노드 클러스터 생성
cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
EOF
```

#### 유용한 Kind 명령어

```bash
# 클러스터 목록 보기
kind get clusters

# 클러스터 삭제
kind delete cluster --name my-cluster

# 로컬 이미지를 Kind 클러스터로 로드
kind load docker-image my-image:tag --name my-cluster
```

### Docker Desktop

Docker Desktop은 Mac 및 Windows 사용자를 위한 Docker 개발 환경으로, Kubernetes를 내장하고 있습니다.

#### 요구 사항

- macOS 10.14 이상 또는 Windows 10 Pro/Enterprise/Education
- 4GB 이상의 RAM

#### 설치 방법

1. [Docker Desktop 다운로드 페이지](https://www.docker.com/products/docker-desktop)에서 운영 체제에 맞는 설치 프로그램을 다운로드합니다.
2. 설치 프로그램을 실행하고 지시에 따라 설치를 완료합니다.
3. Docker Desktop을 시작합니다.
4. 설정(Preferences/Settings)에서 Kubernetes 탭으로 이동합니다.
5. "Enable Kubernetes" 체크박스를 선택하고 "Apply & Restart"를 클릭합니다.
6. Kubernetes가 시작될 때까지 기다립니다(Docker Desktop 상태 표시줄에 녹색 점이 표시됨).

#### 유용한 기능

- 통합 대시보드
- 간편한 리소스 관리
- Docker와 Kubernetes 간의 원활한 전환
- 로컬 이미지를 Kubernetes에서 직접 사용 가능
## 클라우드 환경 설정

대부분의 주요 클라우드 제공업체는 관리형 Kubernetes 서비스를 제공합니다. 이러한 서비스를 사용하면 컨트롤 플레인 관리, 노드 프로비저닝, 업그레이드 등의 운영 부담 없이 Kubernetes를 사용할 수 있습니다.

### Amazon EKS (Elastic Kubernetes Service)

Amazon EKS는 AWS에서 제공하는 관리형 Kubernetes 서비스입니다.

#### 주요 특징

- 여러 가용 영역에 걸쳐 고가용성 컨트롤 플레인 제공
- AWS 서비스(IAM, VPC, ELB 등)와의 통합
- 자동화된 버전 업그레이드
- Fargate를 통한 서버리스 컨테이너 실행 지원

#### 설치 방법

**eksctl을 사용한 설치**:

1. eksctl 설치:

```bash
# macOS
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Linux
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Windows (PowerShell)
chocolatey install eksctl
```

2. 클러스터 생성:

```bash
eksctl create cluster \
  --name my-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed
```

**AWS Management Console을 사용한 설치**:

1. AWS Management Console에 로그인합니다.
2. EKS 서비스로 이동합니다.
3. "클러스터 생성" 버튼을 클릭합니다.
4. 클러스터 이름, IAM 역할, VPC 및 서브넷 등의 필수 정보를 입력합니다.
5. 노드 그룹을 구성합니다.
6. 클러스터를 생성합니다.

#### kubectl 구성

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

### Google GKE (Google Kubernetes Engine)

GKE는 Google Cloud Platform에서 제공하는 관리형 Kubernetes 서비스입니다.

#### 주요 특징

- 자동 확장 및 자동 업그레이드
- 자동 노드 복구
- 로깅 및 모니터링 통합
- 클러스터 자동 확장
- 멀티 클러스터 지원

#### 설치 방법

**Google Cloud Console을 사용한 설치**:

1. Google Cloud Console에 로그인합니다.
2. Kubernetes Engine 페이지로 이동합니다.
3. "클러스터 만들기" 버튼을 클릭합니다.
4. 클러스터 기본 사항(이름, 위치 유형, 버전 등)을 구성합니다.
5. 노드 풀을 구성합니다.
6. "만들기" 버튼을 클릭합니다.

**gcloud CLI를 사용한 설치**:

1. gcloud CLI 설치:

```bash
# 다운로드 및 설치
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

2. 클러스터 생성:

```bash
gcloud container clusters create my-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type e2-medium
```

#### kubectl 구성

```bash
gcloud container clusters get-credentials my-cluster --zone us-central1-a
```

### Microsoft AKS (Azure Kubernetes Service)

AKS는 Microsoft Azure에서 제공하는 관리형 Kubernetes 서비스입니다.

#### 주요 특징

- 자동화된 업그레이드 및 패치
- Azure Active Directory 통합
- Azure Monitor를 통한 모니터링
- 가상 네트워크 통합
- HTTP 애플리케이션 라우팅

#### 설치 방법

**Azure Portal을 사용한 설치**:

1. Azure Portal에 로그인합니다.
2. "리소스 만들기"를 클릭하고 "Kubernetes Service"를 검색합니다.
3. "만들기" 버튼을 클릭합니다.
4. 기본 정보(구독, 리소스 그룹, 클러스터 이름 등)를 입력합니다.
5. 노드 풀을 구성합니다.
6. 네트워킹, 인증 등의 추가 설정을 구성합니다.
7. "검토 + 만들기" 버튼을 클릭한 후 "만들기"를 클릭합니다.

**Azure CLI를 사용한 설치**:

1. Azure CLI 설치:

```bash
# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'
```

2. Azure에 로그인:

```bash
az login
```

3. 리소스 그룹 생성:

```bash
az group create --name myResourceGroup --location eastus
```

4. AKS 클러스터 생성:

```bash
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys
```

#### kubectl 구성

```bash
az aks get-credentials --resource-group myResourceGroup --name myAKSCluster
```
## 베어메탈 설치

베어메탈 서버나 가상 머신에 직접 Kubernetes를 설치하는 것은 더 많은 제어와 유연성을 제공하지만, 설정과 유지 관리가 더 복잡합니다.

### 요구 사항

**최소 요구 사항**:
- 2 CPU 이상
- 2GB 이상의 RAM
- 20GB 이상의 디스크 공간
- 모든 노드 간의 네트워크 연결
- 각 노드의 고유한 호스트 이름, MAC 주소, product_uuid
- 특정 포트 개방
- 스왑 비활성화

**권장 요구 사항**:
- 마스터 노드: 4 CPU, 8GB RAM, 50GB 디스크
- 워커 노드: 2 CPU, 4GB RAM, 50GB 디스크

### kubeadm을 사용한 설치

kubeadm은 Kubernetes 클러스터를 빠르게 설치하기 위한 도구입니다.

#### 사전 준비 (모든 노드)

1. 컨테이너 런타임 설치 (예: Docker):

```bash
# Docker 설치
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce
```

2. kubeadm, kubelet, kubectl 설치:

```bash
# 저장소 추가
sudo apt-get update
sudo apt-get install -y apt-transport-https curl
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF
sudo apt-get update

# 패키지 설치
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

3. 스왑 비활성화:

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

#### 마스터 노드 설정

1. 클러스터 초기화:

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

2. kubectl 구성:

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

3. 네트워크 플러그인 설치 (예: Flannel):

```bash
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```

#### 워커 노드 설정

마스터 노드에서 `kubeadm init` 명령을 실행한 후 출력된 `kubeadm join` 명령을 워커 노드에서 실행합니다:

```bash
sudo kubeadm join <master-ip>:<master-port> --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

#### 클러스터 확인

```bash
kubectl get nodes
```

### kubespray를 사용한 설치

Kubespray는 Ansible 플레이북을 사용하여 Kubernetes 클러스터를 배포하는 도구입니다.

#### 사전 준비

1. Ansible 설치:

```bash
sudo apt-get update
sudo apt-get install -y python3-pip
pip3 install ansible
```

2. Kubespray 복제:

```bash
git clone https://github.com/kubernetes-sigs/kubespray.git
cd kubespray
pip3 install -r requirements.txt
```

#### 클러스터 배포

1. 인벤토리 파일 준비:

```bash
cp -rfp inventory/sample inventory/mycluster
```

2. 인벤토리 파일 편집:

```bash
# inventory/mycluster/inventory.ini
[all]
node1 ansible_host=192.168.1.1 ip=192.168.1.1
node2 ansible_host=192.168.1.2 ip=192.168.1.2
node3 ansible_host=192.168.1.3 ip=192.168.1.3

[kube_control_plane]
node1

[etcd]
node1

[kube_node]
node2
node3

[calico_rr]

[k8s_cluster:children]
kube_control_plane
kube_node
calico_rr
```

3. 클러스터 배포:

```bash
ansible-playbook -i inventory/mycluster/inventory.ini --become --become-user=root cluster.yml
```

## 클러스터 구성

Kubernetes 클러스터를 설치한 후에는 추가 구성이 필요합니다.

### kubectl 설정

kubectl은 Kubernetes 클러스터와 상호 작용하기 위한 명령줄 도구입니다.

#### 설치

**macOS**:

```bash
brew install kubectl
```

**Linux**:

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

**Windows**:

```powershell
curl -LO "https://dl.k8s.io/release/v1.24.0/bin/windows/amd64/kubectl.exe"
```

#### 구성

kubectl은 기본적으로 `~/.kube/config` 파일에서 클러스터 구성을 찾습니다. 이 파일은 클러스터 정보, 인증 정보 및 컨텍스트를 포함합니다.

```bash
# 현재 컨텍스트 확인
kubectl config current-context

# 컨텍스트 전환
kubectl config use-context my-cluster-name

# 클러스터 정보 확인
kubectl cluster-info
```

### 네트워크 플러그인 설치

Kubernetes는 CNI(Container Network Interface) 플러그인을 사용하여 포드 네트워킹을 구현합니다. 다양한 CNI 플러그인이 있으며, 각각 다른 기능과 성능 특성을 가지고 있습니다.

#### Calico

Calico는 확장성이 뛰어나고 네트워크 정책을 지원하는 인기 있는 CNI 플러그인입니다.

```bash
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
```

#### Flannel

Flannel은 간단하고 가벼운 CNI 플러그인입니다.

```bash
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```

#### Cilium

Cilium은 eBPF를 사용하여 고성능 네트워킹 및 보안을 제공하는 CNI 플러그인입니다.

```bash
kubectl create -f https://raw.githubusercontent.com/cilium/cilium/v1.12/install/kubernetes/quick-install.yaml
```

### 스토리지 클래스 구성

스토리지 클래스는 관리자가 제공하는 스토리지의 "클래스"를 설명합니다. 다양한 클래스가 서로 다른 품질의 서비스 수준이나 백업 정책을 가질 수 있습니다.

#### 로컬 스토리지

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
```

#### AWS EBS

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp2
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp2
  fsType: ext4
```

#### Azure Disk

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: managed-premium
provisioner: kubernetes.io/azure-disk
parameters:
  storageaccounttype: Premium_LRS
  kind: Managed
```

### 인그레스 컨트롤러 설치

인그레스 컨트롤러는 클러스터 외부에서 내부 서비스로의 HTTP 및 HTTPS 경로를 관리합니다.

#### NGINX 인그레스 컨트롤러

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.2.0/deploy/static/provider/cloud/deploy.yaml
```

#### Traefik

```bash
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm install traefik traefik/traefik
```

## 결론

이 장에서는 다양한 환경에서 Kubernetes를 설치하고 구성하는 방법을 살펴보았습니다. 로컬 개발 환경부터 클라우드 제공업체의 관리형 서비스, 베어메탈 설치에 이르기까지 다양한 옵션이 있습니다. 각 환경에는 장단점이 있으므로, 사용 사례와 요구 사항에 맞는 옵션을 선택하는 것이 중요합니다.

다음 장에서는 Kubernetes의 기본 개념과 리소스에 대해 알아보겠습니다.

## 참고 자료

- [Kubernetes 공식 설치 가이드](https://kubernetes.io/docs/setup/)
- [Minikube 문서](https://minikube.sigs.k8s.io/docs/)
- [Kind 문서](https://kind.sigs.k8s.io/)
- [Amazon EKS 문서](https://docs.aws.amazon.com/eks/)
- [Google GKE 문서](https://cloud.google.com/kubernetes-engine/docs)
- [Microsoft AKS 문서](https://docs.microsoft.com/azure/aks/)
- [kubeadm 문서](https://kubernetes.io/docs/reference/setup-tools/kubeadm/)
- [Kubespray 문서](https://kubespray.io/)
