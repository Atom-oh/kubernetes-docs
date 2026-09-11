# Linux 운영 기술

> **지원 버전**: 지원 중인 Linux 배포판의 Bash; 사용 도구는 별도 설치 필요 **마지막 업데이트**: 2026년 9월 11일

이 문서는 Kubernetes 환경에서 효과적으로 작업하기 위한 필수 Linux 운영 기술을 다룹니다.

***

## 목차

1. [환경 변수와 쉘 설정](02-linux-advanced.md#1-환경-변수와-쉘-설정)
2. [쉘 스크립팅 기초](02-linux-advanced.md#2-쉘-스크립팅-기초)
3. [텍스트 처리 도구](02-linux-advanced.md#3-텍스트-처리-도구)
4. [SSH와 원격 접속](02-linux-advanced.md#4-ssh와-원격-접속)
5. [성능 모니터링 및 트러블슈팅](02-linux-advanced.md#5-성능-모니터링-및-트러블슈팅)
6. [스토리지 관리 기초](02-linux-advanced.md#6-스토리지-관리-기초)
7. [curl과 API 호출](02-linux-advanced.md#7-curl과-api-호출)
8. [실용적인 원라이너 모음](02-linux-advanced.md#8-실용적인-원라이너-모음)

***

## 1. 환경 변수와 쉘 설정

환경 변수는 Linux 시스템과 Kubernetes에서 설정을 관리하는 핵심 메커니즘입니다.

### 1.1 환경 변수 기초

```bash
env
echo "$HOME"
echo "$PATH"
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

### 1.4 .bashrc와 .bash\_profile

Bash의 대화형 비로그인 셸은 .bashrc를 읽으며 로그인 셸은 .bash_profile/.bash_login/.profile 중 첫 파일을 읽습니다. 로그인 설정에서 .bashrc를 명시적으로 읽을 수도 있습니다. 아래 블록은 한 번만 추가합니다.

```bash
cat >> ~/.bashrc << 'SCRIPT'
export KUBECONFIG=~/.kube/config
command -v kubectl >/dev/null && source <(kubectl completion bash)
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

***

## 2. 쉘 스크립팅 기초

### 2.1 변수

```bash
#!/bin/bash
NAME="kubernetes"
NAMESPACE=${1:-default}
: "${REQUIRED_VAR:?REQUIRED_VAR must be set}"
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

# Running phase does not imply readiness. A bounded wait propagates API errors/timeouts.
kubectl wait --for=condition=Ready pod/mypod --timeout=120s
```

### 2.4 함수

```bash
check_pod_exists() {
    local pod_name=${1:?Pod name required}
    local namespace=${2:-default}
    # Nonzero also includes authorization/connection errors; inspect stderr.
    kubectl get pod "$pod_name" -n "$namespace" -o name >/dev/null
}
```

### 2.5 Init Container 패턴

아래는 DNS 검색 대기의 유한 반복 예제입니다. DNS 성공은 데이터베이스 준비 완료가 아니므로 실제 애플리케이션은 연결 재시도/DB별 readiness 검사를 구현해야 합니다. Service mysql과 커스텀 myapp 이미지는 사전에 준비합니다. 실패 시 kubelet이 init 컨테이너를 다시 시작할 수 있으므로 전체 Pod 시작 기한과도 구분합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: wait-for-db-dns
    image: busybox:1.37.0
    command:
    - sh
    - -c
    - |
      for attempt in $(seq 1 60); do
        nslookup mysql.default.svc.cluster.local >/dev/null 2>&1 && exit 0
        sleep 2
      done
      echo "Database Service DNS did not become available" >&2
      exit 1
  containers:
  - name: app
    image: myapp:1.0
```

***

## 3. 텍스트 처리 도구

### 3.1 grep과 kubectl

```bash
kubectl get pods --field-selector=status.phase!=Running
kubectl logs nginx-pod | grep -i error
```

### 3.2 awk 필드 추출

```bash
kubectl get pods | awk 'NR>1 {print $1}'
kubectl get pods --no-headers | awk '$3 != "Running" {print $1, $3}'
```

### 3.3 sed 편집

```bash
# Text-only preview; this can match more than the intended YAML field.
sed 's/replicas: [0-9]*/replicas: 5/' deployment.yaml
# For a structured edit, use the yq example below.
```

### 3.4 jq로 JSON 파싱

```bash
kubectl get pod nginx -o json | jq '.metadata.name'
kubectl get pods -o json | jq -r '.items[].metadata.name'
```

### 3.5 yq로 YAML 파싱

이 예제는 Mike Farah yq v4 문법이며 Python yq와 옵션이 다릅니다.

```bash
yq '.metadata.name' deployment.yaml
yq -i '.spec.replicas = 5' deployment.yaml
```

***

## 4. SSH와 원격 접속

### 4.1 SSH 키 생성

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 4.2 SSH 터널링

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:localhost:80 user@server
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:6443:kubernetes-api:6443 user@bastion
```

API 터널에서는 kubeconfig의 원래 CA와 TLS 서버 이름을 유지합니다. 127.0.0.1로 접속할 때 tls-server-name을 실제 API 인증서 이름으로 설정하며 TLS 검증을 끄지 않습니다.

### 4.3 Bastion 호스트 사용

```bash
ssh -J bastion user@internal-server
```

### 4.4 rsync

```bash
rsync -avzP ./local/ user@remote:/path/
```

***

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

Metrics Server 등 metrics.k8s.io 제공자가 필요하며 kubectl top은 장기 모니터링 이력을 제공하지 않습니다.

```bash
kubectl top nodes
kubectl top pods --sort-by=memory
```

***

## 6. 스토리지 관리 기초

### 6.1 lsblk

```bash
lsblk -f
```

### 6.2 LVM

```bash
# Use only an explicitly selected empty training disk. These commands write storage metadata.
: "${LAB_DISK:?Set an unused lab block device after checking lsblk and backups}"
lsblk -f "$LAB_DISK"
sudo wipefs --no-act "$LAB_DISK"
# Stop if the disk contains data, mounted filesystems, or existing volume metadata.
sudo pvcreate "$LAB_DISK"
sudo vgcreate data_vg "$LAB_DISK"
sudo lvcreate -l 100%FREE -n data_lv data_vg
```

### 6.3 Kubernetes PV/PVC

아래 경로와 호스트명은 실제 파일 시스템이 마운트된 노드와 일치해야 합니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv
spec:
  capacity:
    storage: 100Gi
  accessModes: [ReadWriteOnce]
  storageClassName: local-storage
  persistentVolumeReclaimPolicy: Retain
  local:
    path: /mnt/disks/vol1
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values: [replace-with-actual-node-hostname]
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: local-pvc
spec:
  storageClassName: local-storage
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

***

로컬 볼륨은 노드 장애 시 다른 노드로 이동하지 않습니다. 위 StorageClass는 동적 디스크 생성을 하지 않으며 PVC는 소비 Pod가 스케줄될 때까지 Pending일 수 있습니다. PV 용량은 실제 파일 시스템 용량과 맞춰야 하며 값 자체가 디렉토리 사용량 제한을 만들지는 않습니다. Retain 볼륨 재사용/데이터 삭제는 별도 관리 작업입니다.

## 7. curl과 API 호출

### 7.1 HTTP 메서드

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"John"}' https://api.example.com/users
```

### 7.2 Kubernetes API 호출

```bash
# Run inside a Pod with projected ServiceAccount credentials and curl installed.
set -e
SERVICEACCOUNT=/var/run/secrets/kubernetes.io/serviceaccount
CACERT="$SERVICEACCOUNT/ca.crt"
NAMESPACE=$(cat "$SERVICEACCOUNT/namespace")
TOKEN=$(cat "$SERVICEACCOUNT/token")
curl --fail --silent --show-error --cacert "$CACERT" \
  -H "Authorization: Bearer $TOKEN" \
  "https://kubernetes.default.svc/api/v1/namespaces/$NAMESPACE/pods"
unset TOKEN
```

ServiceAccount에는 해당 네임스페이스의 pods list RBAC 권한이 필요합니다. automountServiceAccountToken: false이면 이 경로가 없으며 projected 토큰은 갱신되므로 장기 실행 클라이언트는 파일을 다시 읽어야 합니다. 토큰을 로그에 출력하지 않습니다.

### 7.3 유용한 curl 옵션

```bash
curl --silent --show-error -o /dev/null -w "%{http_code}\n" https://api.example.com/health
```

***

## 8. 실용적인 원라이너 모음

### 8.1 Kubernetes 운영

```bash
kubectl get pods -A | awk '$4 != "Running" && NR>1 {print $1, $2, $4}'
kubectl get pods -A -o json | jq -r '.items[] | select(any((.status.containerStatuses // [])[]; .restartCount > 5)) | [.metadata.namespace, .metadata.name] | @tsv'
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

***

## 결론

1. **환경 변수**: K8s ConfigMap/Secret의 기반
2. **쉘 스크립팅**: init container, health check에 필수
3. **텍스트 처리**: kubectl 출력 파싱의 핵심
4. **SSH**: 노드 디버깅에 중요
5. **성능 모니터링**: 트러블슈팅의 기초

***

[이전: Linux 기초](01-linux-basics.md) | [다음: 컨테이너 기초](03-container-technology.md)

## 검증 참고 자료

- https://kubernetes.io/docs/concepts/storage/volumes/#local
- https://kubernetes.io/docs/concepts/storage/storage-classes/#local
- https://kubernetes.io/docs/tasks/run-application/access-api-from-pod/
- https://kubernetes.io/docs/concepts/configuration/configmap/
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_wait/
- https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
- https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html
- https://download.samba.org/pub/rsync/rsync.1
- https://github.com/mikefarah/yq
- https://busybox.net/downloads/BusyBox.html
- https://github.com/docker-library/official-images/blob/master/library/busybox
