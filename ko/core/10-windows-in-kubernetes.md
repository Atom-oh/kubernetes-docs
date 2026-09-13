# Windows in Kubernetes

> **검토한 upstream Kubernetes 버전**: Kubernetes 1.35, 1.36, 1.37
> **마지막 업데이트**: 2026년 9월 11일

Kubernetes는 원래 Linux 컨테이너를 위해 설계되었지만, 버전 1.14부터 Windows 컨테이너에 대한 프로덕션 지원이 추가되었습니다. 이 장에서는 Kubernetes에서 Windows 워크로드를 실행하는 방법, 아키텍처, 제한 사항, 그리고 Amazon EKS에서의 Windows 지원에 대해 알아보겠습니다.

## 목차
1. [Windows 컨테이너 개요](#windows-컨테이너-개요)
2. [Kubernetes의 Windows 지원 아키텍처](#kubernetes의-windows-지원-아키텍처)
3. [Windows 노드 제한 사항](#windows-노드-제한-사항)
4. [Windows 노드 설정](#windows-노드-설정)
5. [Windows 컨테이너 배포](#windows-컨테이너-배포)
6. [네트워킹](#네트워킹)
7. [스토리지](#스토리지)
8. [모니터링 및 로깅](#모니터링-및-로깅)
9. [보안](#보안)
10. [Amazon EKS에서의 Windows 지원](#amazon-eks에서의-windows-지원)
11. [모범 사례](#모범-사례)
12. [결론](#결론)

## Windows 컨테이너 개요

Windows 컨테이너는 Windows 운영 체제에서 실행되는 컨테이너로, Windows 애플리케이션을 컨테이너화하여 배포할 수 있게 해줍니다.

### Windows 컨테이너 유형

Windows에는 두 가지 격리 유형이 있지만 Kubernetes는 **프로세스 격리만 지원**합니다. 아래 Hyper-V 설명은 운영 체제 배경 지식이며 Kubernetes 배포 옵션이 아닙니다:

1. **Windows Server 컨테이너**: Linux 컨테이너와 유사하게 호스트 OS 커널을 공유합니다. 가볍고 빠르게 시작되지만, Microsoft가 지원하는 호스트/이미지 조합이 필요합니다.

2. **Hyper-V 격리 컨테이너**: 각 컨테이너가 경량 VM에서 실행되어 더 높은 수준의 격리를 제공합니다. 호스트와 다른 Windows 버전을 실행할 수 있지만, 더 많은 리소스를 사용합니다.

다음 다이어그램은 두 가지 Windows 컨테이너 유형의 아키텍처 차이를 보여줍니다:

![Windows Server 컨테이너는 여러 Windows 앱이 하나의 컨테이너 런타임과 호스트 OS 커널을 공유하고, Hyper-V 격리 컨테이너는 앱마다 경량 VM과 전용 Windows OS 커널을 가진 채 Hyper-V 하이퍼바이저를 거쳐 같은 Windows Server OS와 물리적 하드웨어에 연결되는 구조를 비교한다.](../.gitbook/assets/ko-core-10-windows-in-kubernetes-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-core-10-windows-in-kubernetes-0.html)

### Windows 컨테이너 이미지

Windows 컨테이너 이미지는 Microsoft에서 제공하는 기본 이미지를 기반으로 합니다:

1. **Windows Server Core**: 최소한의 Windows Server 환경을 제공하는 경량 이미지
2. **Nano Server**: 더 작은 공간을 차지하는 초경량 이미지
3. **Windows**: 더 넓은 Windows API를 제공하는 이미지이며 전체 데스크톱/GUI 서버는 아님

예시 Dockerfile:

```dockerfile
FROM mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
COPY website/ C:/inetpub/wwwroot/
EXPOSE 80
# Inherit the IIS image entrypoint (ServiceMonitor.exe).
```

## Kubernetes의 Windows 지원 아키텍처

Kubernetes에서 Windows 지원은 혼합 환경을 기반으로 합니다. 컨트롤 플레인 구성 요소는 항상 Linux에서 실행되며, 워커 노드는 Linux 또는 Windows일 수 있습니다.

### 아키텍처 개요

Kubernetes의 Windows 지원 아키텍처는 다음과 같습니다:

1. **Linux 컨트롤 플레인**: kube-apiserver, kube-controller-manager, kube-scheduler, etcd는 항상 Linux에서 실행됩니다.
2. **Linux 워커 노드**: 시스템 구성 요소(CoreDNS, metrics-server 등)를 실행합니다.
3. **Windows 워커 노드**: Windows 애플리케이션 워크로드를 실행합니다.

![Linux에서만 실행되는 컨트롤 플레인(kube-apiserver, kube-controller-manager, kube-scheduler, etcd)이 CoreDNS·metrics-server 등 시스템 Pod를 실행하는 Linux 워커 노드와, kubelet·kube-proxy로 Windows 컨테이너를 실행하는 두 개의 Windows 워커 노드를 함께 관리하는 혼합 클러스터 구조를 보여준다.](../.gitbook/assets/ko-core-10-windows-in-kubernetes-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-core-10-windows-in-kubernetes-1.html)

### Windows 노드 구성 요소

Windows 노드에서 실행되는 Kubernetes 구성 요소:

1. **kubelet**: 노드에서 포드 및 컨테이너 관리
2. **kube-proxy**: 네트워크 규칙 관리
3. **CNI 플러그인**: 네트워킹 구성
4. **CSI 플러그인**: 스토리지 관리

## Windows 노드 제한 사항

Kubernetes에서 Windows 노드를 사용할 때 알아야 할 몇 가지 제한 사항이 있습니다.

### 기능 제한 사항

1. `privileged`는 지원하지 않습니다. 노드 에이전트에는 hostProcess와 hostNetwork를 함께 설정한 **HostProcess 컨테이너**를 사용하며 호스트 권한을 신중하게 제한합니다.
2. 일반 Windows Pod는 hostNetwork를 지원하지 않습니다. HostProcess는 예외입니다.
3. `spec.os.name: windows`인 Pod는 runAsUser, fsGroup, seccomp, capabilities, readOnlyRootFilesystem 등 Linux 전용 필드를 설정할 수 없습니다.
4. OS별 이미지와 nodeSelector로 DaemonSet을 분리할 수 있습니다.
5. 메모리 기반 emptyDir, raw block volumeDevices, PIDPressure, Linux 방식 OOM eviction은 지원하지 않습니다.
6. CPU/메모리 제한은 Windows 방식으로 구현됩니다. Windows에는 Linux OOM killer가 없으며 메모리 부족 시 할당 실패나 페이징으로 성능이 저하될 수 있습니다.

### 네트워킹 제한 사항

Windows HNS와 CNI의 L2bridge/overlay 등 지원 모드를 확인합니다. 같은 Pod의 컨테이너는 네트워크와 localhost를 공유하지만 프로세스 네임스페이스와 루트 파일 시스템은 공유하지 않습니다. NetworkPolicy, 서비스 및 DSR 지원은 OS/CNI/클러스터 조합에 따라 확인해야 합니다.

### 운영 체제 버전 호환성

Kubernetes v1.37의 Windows 워커 지원 대상은 Windows Server 2022와 2025입니다. 이 장의 예제는 **Windows Server 2022 + ltsc2022** 조합을 사용합니다. Microsoft 호환성 표와 배포판 지원 범위를 함께 확인하고 월별 보안 패치를 적용합니다. Hyper-V 격리로 Kubernetes의 호환성 제한을 우회할 수 없습니다.

## Windows 노드 설정

Kubernetes 클러스터에 Windows 노드를 추가하는 과정을 알아보겠습니다.

### 사전 요구 사항

지원 중인 Kubernetes/Windows 조합, Linux 컨트롤 플레인, Windows 지원 CNI 및 CRI 호환 containerd가 필요합니다. Docker Engine 자체는 CRI를 제공하지 않으며 내장 dockershim은 Kubernetes 1.24에서 제거되었습니다. EKS 노드는 아래 EKS 절차를 사용합니다.

### Windows 노드 준비

관리자 PowerShell에서 Containers 기능을 활성화하고 필요한 재부팅을 완료합니다. 아래는 **자체 관리 kubeadm 워커**용입니다. 공식 sig-windows-tools의 `hostprocess/Install-Containerd.ps1`과 `hostprocess/PrepareNode.ps1`을 검토한 커밋에서 다운로드하고 체크섬을 확인한 후 실행합니다. 지원되는 containerd 패치와 클러스터 버전에 맞는 kubelet을 선택합니다. 설치 스크립트가 만든 방화벽 규칙도 검토하여 10250 접근을 필요한 컨트롤 플레인 소스로 제한합니다.

```powershell
$ErrorActionPreference = "Stop"
$ContainerdVersion = Read-Host "Validated containerd version (without v)"
$KubernetesVersion = Read-Host "Cluster-compatible Kubernetes version (vX.Y.Z)"
if (-not $ContainerdVersion -or -not $KubernetesVersion) { throw "Versions required" }
.\Install-Containerd.ps1 -ContainerDVersion $ContainerdVersion
.\PrepareNode.ps1 -KubernetesVersion $KubernetesVersion
```

### kubeadm을 사용한 Windows 노드 조인

Linux 컨트롤 플레인에서 조인 토큰 생성:

```bash
kubeadm token create --print-join-command
```

Windows 노드에서 조인 명령 실행:

```powershell
# kubeadm 조인 명령 실행
kubeadm join <control-plane-host>:<control-plane-port> --token <token> --discovery-token-ca-cert-hash sha256:<hash>

```

### Windows 노드 레이블 설정

kubelet이 게시한 OS/아키텍처/빌드 레이블을 확인합니다. 잘못된 OS 레이블을 덮어써서 스케줄링을 강제하지 않습니다. `spec.os.name`은 OS를 명시하지만 스케줄러 선택자를 대신하지 않으므로 nodeSelector도 사용합니다.

```bash
kubectl get nodes -L kubernetes.io/os,kubernetes.io/arch,node.kubernetes.io/windows-build
```

## Windows 컨테이너 배포

Windows 컨테이너를 Kubernetes에 배포하는 방법을 알아보겠습니다.

### 노드 셀렉터 사용

Windows 워크로드를 배포할 때는 노드 셀렉터를 사용하여 Windows 노드에 스케줄링되도록 해야 합니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: iis-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: iis
  template:
    metadata:
      labels:
        app: iis
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
        resources:
          limits:
            cpu: 1
            memory: 800Mi
          requests:
            cpu: .1
            memory: 300Mi
        ports:
        - containerPort: 80
```

### 리소스 요청 및 제한

Windows 컨테이너의 리소스 요청 및 제한은 Linux 컨테이너와 다르게 처리됩니다:

1. **CPU 제한**: Windows에서는 CPU 제한이 다르게 적용됩니다. 예를 들어, CPU 제한이 1이면 단일 CPU 코어의 100%를 사용할 수 있습니다.
2. **메모리 제한**: Windows 컨테이너는 메모리 제한을 준수하지만, 일부 시스템 프로세스로 인해 추가 오버헤드가 발생할 수 있습니다.

### 컨테이너 사용자 지정

Windows 컨테이너에서 사용자 지정 스크립트 실행:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-custom-script
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command:
    - powershell.exe
    - -Command
    - |
      while ($true) {
        Write-Host "Hello from Windows container"
        Start-Sleep -Seconds 10
      }
```

### 다중 컨테이너 포드

Windows에서도 다중 컨테이너 포드를 지원하지만, 일부 제한 사항이 있습니다:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-multi-container
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: writer
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command: [powershell.exe, -Command, 'while ($true) { Add-Content C:\shared-logs\app.log "Log at $(Get-Date)"; Start-Sleep 10 }']
    volumeMounts:
    - name: logs
      mountPath: C:\shared-logs
  - name: logger
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command: [powershell.exe, -Command, 'while (-not (Test-Path C:\shared-logs\app.log)) { Start-Sleep 2 }; Get-Content C:\shared-logs\app.log -Wait']
    volumeMounts:
    - name: logs
      mountPath: C:\shared-logs
      readOnly: true
  volumes:
  - name: logs
    emptyDir: {}
```

## 네트워킹

Windows 노드의 네트워킹은 Linux 노드와 다른 특성을 가집니다.

다음 다이어그램은 Windows 노드와 Linux 노드가 혼합된 Kubernetes 클러스터의 네트워킹 아키텍처를 보여줍니다:

![외부 클라이언트의 요청이 로드 밸런서와 Kubernetes 서비스를 거쳐 Linux Pod와 Windows Pod로 분산되고, 두 Pod가 서로 다른 OS의 노드에 있어도 클러스터 네트워크로 직접 통신할 수 있음을 보여준다.](../.gitbook/assets/ko-core-10-windows-in-kubernetes-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-core-10-windows-in-kubernetes-2.html)

### 지원되는 네트워크 플러그인

Windows 노드에서 지원되는 네트워크 플러그인:

1. **Flannel**: VXLAN 또는 host-gw 모드
2. **Calico**: VXLAN 모드
3. **Antrea**: OVS 기반 네트워킹
4. **Azure CNI**: Azure 환경에서 사용
5. **AWS VPC CNI**: AWS 환경에서 사용

### Flannel 설정 예시

Flannel의 Linux 매니페스트를 Windows DaemonSet으로 복사하면 동작하지 않습니다. Windows 바이너리, HNS, CNI 경로, RBAC 및 HostProcess 구성이 필요합니다. 클러스터 배포판의 Windows 지원 설치 절차를 사용하고 Linux 측 네트워크와 Windows 측 win-overlay/win-bridge 구성을 함께 맞춥니다. Windows Flannel VXLAN은 VNI 4096/UDP 4789 조건을 확인합니다. 일반 애플리케이션 Pod에 hostNetwork를 추가하는 방식으로 설치하지 않습니다.

### 서비스 노출

Windows 노드에서 서비스를 노출하는 방법:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: iis-service
spec:
  selector:
    app: iis
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### 네트워크 정책

Windows 노드에서 네트워크 정책을 사용하려면 네트워크 정책을 지원하는 CNI 플러그인(예: Calico)이 필요합니다:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
      os: windows
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
```

## 스토리지

Windows 노드에서 사용할 수 있는 스토리지 옵션을 알아보겠습니다.

다음 다이어그램은 Windows 노드에서 사용 가능한 다양한 스토리지 옵션을 보여줍니다:

![Windows Pod의 컨테이너가 Windows 노드의 emptyDir·hostPath 볼륨(hostPath는 노드 디스크로 연결), Kubernetes API에서 전달되는 ConfigMap·Secret 볼륨, 그리고 CSI 드라이버를 거쳐 Azure Disk/File, AWS EBS, SMB 공유에 연결되는 PersistentVolume을 마운트하는 세 가지 스토리지 경로를 보여준다.](../.gitbook/assets/ko-core-10-windows-in-kubernetes-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-core-10-windows-in-kubernetes-3.html)

### 지원되는 볼륨 유형

Windows 노드에서 지원되는 볼륨 유형:

1. **emptyDir**: 임시 스토리지 (메모리 기반 emptyDir은 지원되지 않음)
2. **hostPath**: 호스트 노드의 파일 시스템
3. **configMap**: 구성 데이터
4. **secret**: 민감한 데이터
5. **CSI/PVC**: Windows 호환 Azure Files, Azure Disk, EBS 또는 SMB CSI 드라이버와 파일 시스템 볼륨을 사용하며 OS/파일 시스템 지원을 확인합니다.

### emptyDir 볼륨 예시

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-emptydir
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    volumeMounts:
    - name: temp-volume
      mountPath: C:\temp
    command:
    - powershell.exe
    - -Command
    - |
      Set-Content -Path C:\temp\test.txt -Value "Hello from Windows"
      while ($true) {
        Get-Content -Path C:\temp\test.txt
        Start-Sleep -Seconds 10
      }
  volumes:
  - name: temp-volume
    emptyDir: {}
```

### hostPath 볼륨 예시

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-hostpath
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    volumeMounts:
    - name: logs-volume
      mountPath: C:\logs
    command:
    - powershell.exe
    - -Command
    - |
      Set-Content -Path C:\logs\app.log -Value "Application log"
      while ($true) {
        Add-Content -Path C:\logs\app.log -Value "Log entry at $(Get-Date)"
        Start-Sleep -Seconds 10
      }
  volumes:
  - name: logs-volume
    hostPath:
      path: C:\k\logs
      type: DirectoryOrCreate
```

### ConfigMap 및 Secret 볼륨 예시

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: windows-config
data:
  config.json: |
    {
      "setting1": "value1",
      "setting2": "value2"
    }
---
apiVersion: v1
kind: Secret
metadata:
  name: windows-secret
type: Opaque
data:
  username: YWRtaW4=  # admin
  password: cGFzc3dvcmQ=  # password
---
apiVersion: v1
kind: Pod
metadata:
  name: windows-config-secret
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    volumeMounts:
    - name: config-volume
      mountPath: C:\config
    - name: secret-volume
      mountPath: C:\secret
      readOnly: true
    command:
    - powershell.exe
    - -Command
    - |
      Get-Content -Path C:\config\config.json
      if (-not (Test-Path C:\secret\username) -or -not (Test-Path C:\secret\password)) { throw "Secret files missing" }
      while ($true) { Start-Sleep -Seconds 10 }
  volumes:
  - name: config-volume
    configMap:
      name: windows-config
  - name: secret-volume
    secret:
      secretName: windows-secret
```

### CSI 드라이버 사용

사전 요구 사항: Windows 호환 CSI 드라이버와 파일 시스템(예: NTFS 및 WaitForFirstConsumer를 사용하는 EBS CSI)으로 windows-csi StorageClass를 먼저 생성합니다. 이름만으로 드라이버가 설치되지 않습니다. EBS는 AZ에 종속되며 raw block 대신 파일 시스템 모드를 사용합니다.

예시:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: windows-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: windows-csi
---
apiVersion: v1
kind: Pod
metadata:
  name: windows-csi-pod
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    volumeMounts:
    - name: data-volume
      mountPath: C:\data
    command:
    - powershell.exe
    - -Command
    - |
      Set-Content -Path C:\data\file.txt -Value "Persistent data"
      while ($true) { Start-Sleep -Seconds 10 }
  volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: windows-pvc
```
## 모니터링 및 로깅

Windows 노드 및 컨테이너의 모니터링 및 로깅 방법을 알아보겠습니다.

### 모니터링

Windows 노드 모니터링을 위한 도구:

1. **Prometheus Windows Exporter**: Windows 노드 메트릭 수집
2. **metrics-server**: 기본 리소스 사용량 메트릭 제공
3. **Datadog, Dynatrace, New Relic**: 상용 모니터링 솔루션

Windows 노드에 Prometheus Windows Exporter 설치:

```powershell
# Download a supported release MSI, verify its checksum, then install locally.
$ExporterMsi = (Resolve-Path .\windows_exporter.msi).Path
Start-Process msiexec.exe -ArgumentList "/i `"$ExporterMsi`" ENABLED_COLLECTORS=cpu,memory,logical_disk,net,service,os,system REMOVE=FirewallException /quiet" -Wait
# Restrict any separately configured port 9182 firewall rule to Prometheus sources.
```

Prometheus 구성:

```yaml
scrape_configs:
  - job_name: 'windows-nodes'
    static_configs:
      - targets: ['windows-node-1:9182', 'windows-node-2:9182']
```

### 로깅

Windows 컨테이너 로그 수집을 위한 도구:

1. **Fluent Bit**: 경량 로그 수집기
2. **Fluentd**: 로그 수집 및 전달
3. **Elasticsearch**: 로그 저장 및 검색
4. **Azure Monitor**: Azure 환경에서 사용
5. **CloudWatch Logs**: AWS 환경에서 사용

Windows 노드에 Fluent Bit 설치:

실제 Elasticsearch 주소/인증 및 신뢰할 CA를 구성합니다. 서비스 계정에는 Security 이벤트 로그 읽기 권한과 체크포인트 경로 쓰기 권한이 필요합니다.

```powershell
# Install a supported Windows Fluent Bit release, verify its checksum,
# and arrange bin/ and conf/ under C:\fluent-bit before continuing.

# 구성 파일 생성
@"
[SERVICE]
    Flush        5
    Daemon       Off
    Log_Level    info

[INPUT]
    Name         winlog
    Channels     Application,System,Security
    DB           C:\fluent-bit\winlog.db

[OUTPUT]
    Name         es
    Match        *
    Host         elasticsearch-host
    Port         9200
    Index        windows_logs
    Suppress_Type_Name On
    tls          On
    tls.verify   On
"@ | Out-File -FilePath C:\fluent-bit\conf\fluent-bit.conf -Encoding ascii

# 서비스 등록
sc.exe create fluent-bit binPath= "C:\fluent-bit\bin\fluent-bit.exe -c C:\fluent-bit\conf\fluent-bit.conf"
Start-Service fluent-bit
```

### 애플리케이션 로그 수집

IIS의 파일/ETW/Event Log를 stdout으로 내보내려면 Microsoft LogMonitor를 애플리케이션 이미지에 통합하고 LogMonitorConfig.json에 실제 소스를 정의합니다. ServiceMonitor와 IIS 수명을 유지하는 진입점을 테스트합니다. 위 shared-file sidecar는 볼륨 공유를 설명하는 예제이며 파일 회전/재시작 중 중복·유실 처리를 제공하지 않습니다. 운영 수집기는 체크포인트와 회전을 처리해야 합니다. `kubectl logs`는 stdout/stderr만 보여 주며 IIS 파일을 자동 수집하지 않습니다.

## 보안

Windows 노드 및 컨테이너의 보안 고려 사항을 알아보겠습니다.

### Windows 노드 보안

Windows 노드 보안을 위한 권장 사항:

1. **최신 업데이트 적용**: Windows 보안 업데이트 정기적 적용
2. **방화벽 구성**: Windows Defender 방화벽 적절히 구성
3. **최소 권한 원칙**: 필요한 최소한의 권한만 부여
4. **안티바이러스 소프트웨어**: 적절한 안티바이러스 소프트웨어 설치
5. **그룹 정책**: 보안 강화를 위한 그룹 정책 적용

### Windows 컨테이너 보안

Windows 컨테이너 보안을 위한 권장 사항:

1. **최소 기본 이미지**: 가능한 작은 기본 이미지 사용(Nano Server 등)
2. **이미지 스캐닝**: 컨테이너 이미지 취약점 스캐닝
3. **파일 시스템 권한**: NTFS ACL 및 지원되는 읽기 전용 데이터 마운트를 사용합니다. Windows는 readOnlyRootFilesystem을 지원하지 않습니다.
4. **비특권 사용자**: 비특권 사용자로 애플리케이션 실행
5. **네트워크 정책**: 적절한 네트워크 정책 적용

### RunAsUsername

Windows 컨테이너에서는 `runAsUser` 대신 `securityContext.windowsOptions.runAsUserName`을 사용하여 컨테이너 내에서 실행할 사용자를 지정할 수 있습니다:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-runasusername
spec:
  os:
    name: windows
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      runAsUserName: "ContainerUser"
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command:
    - powershell.exe
    - -Command
    - |
      whoami
      while ($true) { Start-Sleep -Seconds 10 }
```

### 그룹 관리 서비스 계정(gMSA)

`gmsaCredentialSpecName`은 Secret이 아닌 클러스터 범위 **GMSACredentialSpec**을 참조합니다. CRD, mutating/validating webhook 및 ServiceAccount의 `use` RBAC 권한이 필요합니다. 아래 도메인/호스트 이름은 실제 값으로 바꾸고 CredentialSpec 모듈로 AD의 SID/GUID/NetBIOS/DNS 범위를 생성합니다. 도메인 가입 호스트 방식의 예이며 지원되는 비도메인 호스트용 portable identity 구성은 별도 준비가 필요합니다.

`Get-KdsRootKey`로 기존 키를 확인합니다. 새 키가 필요하면 AD 관리자가 `Add-KdsRootKey -EffectiveImmediately` 후 복제 대기 시간(최대 10시간)을 확보합니다. 10시간 backdate는 단일 DC 테스트 환경 전용입니다. gMSA는 네트워크 인증 자격이며 컨테이너를 도메인에 가입시키거나 `whoami`를 gMSA 이름으로 바꾸지 않습니다. 실제 서비스의 Kerberos 인증과 `klist`로 검증합니다.

```powershell
# On an authorized AD administration host, after KDS readiness is confirmed:
Import-Module ActiveDirectory
New-ADGroup -Name 'WebAppHosts' -SamAccountName 'WebAppHosts' -GroupScope DomainLocal
Add-ADGroupMember -Identity 'WebAppHosts' -Members 'ContainerHost01$'
New-ADServiceAccount -Name WebApp1 -DNSHostName WebApp1.contoso.com -ServicePrincipalNames http/WebApp1.contoso.com -PrincipalsAllowedToRetrieveManagedPassword WebAppHosts
# Install/review the official CredentialSpec PowerShell module first.
Import-Module CredentialSpec
New-CredentialSpec -AccountName WebApp1 -Path C:\gmsa-credspec.json
$spec = Get-Content C:\gmsa-credspec.json -Raw | ConvertFrom-Json
@{ apiVersion='windows.k8s.io/v1'; kind='GMSACredentialSpec'; metadata=@{name='gmsa-cred-spec'}; credspec=$spec } |
    ConvertTo-Json -Depth 20 | Set-Content C:\gmsa-resource.json -Encoding utf8
```

```bash
# Requires the GMSA CRD and mutating/validating webhooks installed by an administrator.
kubectl apply -f gmsa-resource.json
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: windows-app
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: use-webapp-gmsa
rules:
- apiGroups: [windows.k8s.io]
  resources: [gmsacredentialspecs]
  resourceNames: [gmsa-cred-spec]
  verbs: [use]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: use-webapp-gmsa
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: use-webapp-gmsa
subjects:
- kind: ServiceAccount
  name: windows-app
  namespace: default
---
apiVersion: v1
kind: Pod
metadata:
  name: windows-gmsa
  namespace: default
spec:
  os:
    name: windows
  serviceAccountName: windows-app
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      gmsaCredentialSpecName: gmsa-cred-spec
      runAsUserName: 'NT AUTHORITY\NETWORK SERVICE'
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2022
    command: [powershell.exe, -Command, 'whoami; Start-Sleep -Seconds 3600']
```

## Amazon EKS에서의 Windows 지원

Amazon EKS에서 Windows 워크로드를 실행하는 방법을 알아보겠습니다.

다음 다이어그램은 Amazon EKS에서의 Windows 지원 아키텍처를 보여줍니다:

![EKS 컨트롤 플레인이 Linux 노드 그룹(CoreDNS·VPC CNI·kube-proxy 시스템 Pod)과 Windows 노드 그룹(Windows 애플리케이션 Pod)을 함께 관리하며 AWS IAM·Amazon VPC·CloudWatch와 연동하고, Windows 애플리케이션 Pod가 Elastic Load Balancer를 통해 사용자에게 서비스를 제공하는 구조를 보여준다.](../.gitbook/assets/ko-core-10-windows-in-kubernetes-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-core-10-windows-in-kubernetes-4.html)

### EKS에서 Windows 지원 활성화

Windows IPAM은 EKS가 관리하는 VPC resource controller가 담당합니다. 예전 release-1.11 controller/webhook 매니페스트를 설치하지 않습니다. 클러스터 IAM 역할에 `AmazonEKSVPCResourceController` 권한을 부여하고 현재 AWS 절차에 따라 `kube-system/amazon-vpc-cni` ConfigMap의 `enable-windows-ipam: "true"`를 설정합니다. 기존 키를 보존하며 Helm/애드온 관리 설정과 충돌하지 않게 적용합니다.

CoreDNS용 Linux 노드 또는 지원되는 Fargate 구성이 필요합니다. Windows는 EKS Auto Mode, Fargate 워크로드, Hybrid Nodes, IPv6, 사용자 지정 네트워킹 및 Pod별 보안 그룹을 지원하지 않습니다. Windows 노드 역할의 access entry 유형은 `EC2_WINDOWS`이며, 레거시 aws-auth 구성에서는 `eks:kube-proxy-windows` 그룹을 확인합니다.

### Windows 노드 그룹 생성

eksctl을 사용하여 Windows 노드 그룹 생성:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name windows-ng \
  --node-type t3.large \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed \
  --node-ami-family WindowsServer2022FullContainer
```

AWS Management Console을 사용하여 Windows 노드 그룹 생성:

1. EKS 콘솔에서 클러스터 선택
2. "컴퓨팅" 탭 선택
3. "노드 그룹 추가" 클릭
4. 노드 그룹 세부 정보 입력
5. AMI 유형으로 "Windows" 선택
6. 나머지 설정 구성 및 생성

### EKS에서 Windows 애플리케이션 배포

EKS에서 Windows 애플리케이션 배포 예시:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
        ports:
        - name: http
          containerPort: 80
        resources:
          limits:
            cpu: 1
            memory: 800Mi
          requests:
            cpu: .1
            memory: 300Mi
---
apiVersion: v1
kind: Service
metadata:
  name: windows-server-iis-service
  labels:
    app: windows-server-iis
spec:
  ports:
  - port: 80
    protocol: TCP
  selector:
    app: windows-server-iis
  type: LoadBalancer
```

### EKS에서 Windows 컨테이너 로깅

Windows 노드의 Container Insights는 CloudWatch Observability EKS 애드온 1.5.0 이상에서 지원합니다. 클러스터와 호환되는 애드온 버전, IAM 권한 및 Windows 노드용 에이전트 구성을 선택합니다. Windows Application Signals는 지원하지 않습니다.

Windows stdout/stderr는 kubelet의 CRI 로그 경로(일반적으로 `C:\var\log\pods` 및 `C:\var\log\containers`)에서 수집합니다. 실제 배포판 경로를 확인하며 Linux `/var/log`/Docker parser 설정을 그대로 복사하지 않습니다. EKS의 kubelet/kube-proxy 로그는 **EKS Windows** 이벤트 로그에 기록됩니다. 일반 컨테이너에 .evtx 파일만 마운트해도 winlog 입력이 호스트 이벤트 API를 읽게 되지는 않습니다. 호스트 서비스나 검토된 HostProcess 수집기를 사용합니다.

## 모범 사례

Kubernetes에서 Windows 워크로드를 실행하기 위한 모범 사례를 알아보겠습니다.

### 클러스터 설계 모범 사례

1. **혼합 노드 풀**: Linux 노드와 Windows 노드를 적절히 혼합하여 사용
2. **노드 레이블 및 테인트**: 적절한 노드 레이블 및 테인트를 사용하여 워크로드 분리
3. **버전 호환성**: Kubernetes 버전과 Windows 버전 간의 호환성 확인
4. **네트워크 플러그인 선택**: Windows를 지원하는 적절한 네트워크 플러그인 선택
5. **고가용성**: 중요한 워크로드에 대한 고가용성 구성

### 애플리케이션 설계 모범 사례

1. **컨테이너 이미지 최적화**: 작고 효율적인 컨테이너 이미지 사용
2. **리소스 요청 및 제한**: 적절한 리소스 요청 및 제한 설정
3. **상태 비저장 설계**: 가능한 상태 비저장 애플리케이션 설계
4. **로깅 및 모니터링**: 효과적인 로깅 및 모니터링 구성
5. **보안 강화**: 적절한 보안 컨텍스트 및 네트워크 정책 적용

### 운영 모범 사례

1. **정기적인 업데이트**: Windows 노드 및 컨테이너 이미지 정기적 업데이트
2. **자동화**: 배포 및 관리 작업 자동화
3. **백업 및 복구**: 중요한 데이터 정기적 백업
4. **문제 해결 도구**: 적절한 문제 해결 도구 및 프로세스 구축
5. **문서화**: 구성 및 절차 문서화

### EKS 특화 모범 사례

1. **관리형 노드 그룹**: 가능한 경우 관리형 노드 그룹 사용
2. **IAM 역할 서비스 계정(IRSA)**: 포드별 IAM 권한 관리
3. **VPC CNI 구성**: 네트워킹 요구 사항에 맞게 VPC CNI 구성
4. **보안 그룹**: 적절한 보안 그룹 구성
5. **비용 최적화**: 적절한 인스턴스 유형 및 크기 선택

## 결론

Kubernetes에서 Windows 지원은 계속 발전하고 있으며, 이제 프로덕션 환경에서 Windows 워크로드를 실행할 수 있습니다. Windows 노드는 Linux 노드와 함께 동일한 클러스터에서 실행될 수 있으며, 이를 통해 다양한 워크로드를 단일 Kubernetes 클러스터에서 관리할 수 있습니다.

Windows 컨테이너는 .NET Framework 애플리케이션, Windows 서비스, 기타 Windows 전용 워크로드를 컨테이너화하여 Kubernetes의 오케스트레이션 기능을 활용할 수 있게 해줍니다. 그러나 Linux 컨테이너와 비교하여 일부 제한 사항이 있으므로, 이러한 제한 사항을 이해하고 적절히 대응하는 것이 중요합니다.

Amazon EKS는 Windows 노드에 대한 관리형 서비스를 제공하여 Windows 워크로드를 쉽게 배포하고 관리할 수 있게 해줍니다. EKS의 Windows 지원을 활용하면 Windows 애플리케이션을 현대적인 컨테이너 환경으로 마이그레이션하는 과정을 간소화할 수 있습니다.

Windows in Kubernetes를 성공적으로 구현하려면 적절한 계획, 설계, 운영 모범 사례를 따르는 것이 중요합니다. 이를 통해 Windows 및 Linux 워크로드를 효율적으로 관리하고 Kubernetes의 모든 이점을 활용할 수 있습니다.

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [Windows in Kubernetes 퀴즈](../quizzes/core/10-windows-in-kubernetes-quiz.md)를 풀어보세요.

## 검증 참고 자료

- https://kubernetes.io/docs/concepts/windows/intro/
- https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/adding-windows-nodes/
- https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-gmsa/
- https://learn.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/version-compatibility
- https://github.com/microsoft/windows-container-tools/tree/main/LogMonitor
- https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html
