# Linux 운영 기술 (Kubernetes 실무자를 위한)

> **지원 버전**: 모든 주요 Linux 배포판
> **마지막 업데이트**: 2025년 2월

이 문서는 Kubernetes 환경에서 효과적으로 작업하기 위한 필수 Linux 운영 기술을 다룹니다.

---

## 목차

1. [환경 변수와 쉘 설정](#1-환경-변수와-쉘-설정)
2. [쉘 스크립팅 기초](#2-쉘-스크립팅-기초)
3. [텍스트 처리 도구](#3-텍스트-처리-도구)
4. [SSH와 원격 접속](#4-ssh와-원격-접속)
5. [성능 모니터링 및 트러블슈팅](#5-성능-모니터링-및-트러블슈팅)
6. [스토리지 관리 기초](#6-스토리지-관리-기초)
7. [curl과 API 호출](#7-curl과-api-호출)
8. [실용적인 원라이너 모음](#8-실용적인-원라이너-모음)

---

## 1. 환경 변수와 쉘 설정

환경 변수는 Linux 시스템과 Kubernetes에서 설정을 관리하는 핵심 메커니즘입니다.

### 1.1 환경 변수 기초

```bash
env
echo $HOME
echo $PATH
printenv HOME
```

### 1.2 export 명령어

```bash
export MY_VAR="hello"
export DATABASE_URL="postgresql://localhost:5432/mydb"
export KUBECONFIG="/home/user/.kube/config"
```

### 1.3 source 명령어

```bash
cat > ~/my-env.sh << 'SCRIPT'
export APP_ENV="production"
export APP_PORT="8080"
alias k='kubectl'
SCRIPT

source ~/my-env.sh
```

### 1.4 .bashrc와 .bash_profile

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
source <(kubectl completion bash)
alias k='kubectl'
SCRIPT

source ~/.bashrc
```

### 1.5 Kubernetes ConfigMap 연동

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_HOST: "mysql.default.svc.cluster.local"
  DATABASE_PORT: "3306"
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    envFrom:
    - configMapRef:
        name: app-config
```

---

## 2. 쉘 스크립팅 기초

### 2.1 변수

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: ${REQUIRED_VAR:?"REQUIRED_VAR must be set"}
```

### 2.2 조건문

```bash
if [ "$ENV" = "production" ]; then
    echo "Production mode"
fi

case "$1" in
    start) echo "Starting..." ;;
    stop) echo "Stopping..." ;;
esac
```

### 2.3 반복문

```bash
for ns in default kube-system monitoring; do
    kubectl get pods -n "$ns"
done

while true; do
    STATUS=$(kubectl get pod mypod -o jsonpath='{.status.phase}')
    [ "$STATUS" = "Running" ] && break
    sleep 5
done
```

### 2.4 함수

```bash
check_pod_exists() {
    local pod_name=$1
    kubectl get pod "$pod_name" &>/dev/null
}
```

### 2.5 Init Container 패턴

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: wait-for-db
    image: busybox:1.35
    command: ['sh', '-c', 'until nc -z mysql 3306; do sleep 2; done']
  containers:
  - name: app
    image: myapp:1.0
```

---

## 3. 텍스트 처리 도구

### 3.1 grep과 kubectl

```bash
kubectl get pods | grep -v "Running"
kubectl logs nginx-pod | grep -i error
```

### 3.2 awk 필드 추출

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 sed 편집

```bash
sed -i 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
```

### 3.4 jq로 JSON 파싱

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 yq로 YAML 파싱

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

---

## 4. SSH와 원격 접속

### 4.1 SSH 키 생성

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH 터널링

```bash
ssh -L 8080:localhost:80 user@server
ssh -L 6443:kubernetes-api:6443 user@bastion
```

### 4.3 Bastion 호스트 사용

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

---

## 5. 성능 모니터링 및 트러블슈팅

### 5.1 top과 htop

```bash
top -b -n 1 | head -20
```

### 5.2 vmstat와 iostat

```bash
vmstat 1 5
iostat -dx 1 5
```

### 5.3 free와 df

```bash
free -h
df -h
```

### 5.4 kubectl top

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

---

## 6. 스토리지 관리 기초

### 6.1 lsblk

```bash
lsblk -f
```

### 6.2 LVM

```bash
sudo pvcreate /dev/nvme1n1
sudo vgcreate data_vg /dev/nvme1n1
sudo lvcreate -l 100%FREE -n data_lv data_vg
```

### 6.3 Kubernetes PV/PVC

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv
spec:
  capacity:
    storage: 100Gi
  accessModes: [ReadWriteOnce]
  storageClassName: local-storage
  local:
    path: /mnt/disks/vol1
```

---

## 7. curl과 API 호출

### 7.1 HTTP 메서드

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API 호출

```bash
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -s --cacert $CACERT -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/default/pods"
```

### 7.3 유용한 curl 옵션

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health
```

---

## 8. 실용적인 원라이너 모음

### 8.1 Kubernetes 운영

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 5) | .metadata.name'
```

### 8.2 로그 분석

```bash
kubectl logs deploy/app --since=1h | grep -i error
```

### 8.3 네트워크 디버깅

```bash
nslookup kubernetes.default.svc.cluster.local
nc -zv service-name 80
```

---

## 결론

1. **환경 변수**: K8s ConfigMap/Secret의 기반
2. **쉘 스크립팅**: init container, health check에 필수
3. **텍스트 처리**: kubectl 출력 파싱의 핵심
4. **SSH**: 노드 디버깅에 중요
5. **성능 모니터링**: 트러블슈팅의 기초

---

[이전: Linux 기초](01-linux-basics.md) | [다음: 컨테이너 기초](03-container-basics.md)
