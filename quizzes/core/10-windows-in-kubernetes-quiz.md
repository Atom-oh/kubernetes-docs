# Windows in Kubernetes 퀴즈

이 퀴즈는 Kubernetes에서 Windows 노드 및 워크로드 관리에 관한 개념과 실무 지식을 테스트합니다. Windows 컨테이너 기초, Kubernetes에서의 Windows 노드 구성, 네트워킹, 스토리지, 보안 및 모니터링 등의 주제를 다룹니다.

## 객관식 문제

1. Kubernetes에서 Windows 노드를 사용할 때 컨테이너 런타임으로 지원되는 것은 무엇인가요?
   - A) Docker 및 containerd
   - B) CRI-O 및 Docker
   - C) containerd 및 CRI-O
   - D) Docker, containerd 및 gVisor
   
<details>
<summary>정답 보기</summary>

**정답: A) Docker 및 containerd**

**설명:**
Kubernetes에서 Windows 노드를 사용할 때 공식적으로 지원되는 컨테이너 런타임은 Docker와 containerd입니다. 

- **Docker**: Windows에서 Docker는 Windows 컨테이너를 실행하기 위한 전통적인 옵션이었습니다. 그러나 Kubernetes에서 Docker 지원은 점차 줄어들고 있으며, containerd로의 전환이 권장됩니다.

- **containerd**: 현재 Windows 노드에서 권장되는 컨테이너 런타임입니다. containerd는 경량화되고 안정적인 런타임으로, Kubernetes 1.20 이상에서 Windows 노드에 대한 공식 지원을 받습니다.

CRI-O는 현재 Windows 노드에서 공식적으로 지원되지 않습니다. CRI-O는 주로 Linux 컨테이너를 위한 컨테이너 런타임 인터페이스(CRI) 구현체입니다.

gVisor는 컨테이너 격리를 위한 샌드박스 런타임이지만, 현재 Windows 노드에서는 지원되지 않습니다.

Windows 노드에서 컨테이너 런타임을 설정할 때는 Kubernetes 버전과의 호환성을 확인하는 것이 중요합니다.
</details>

2. Kubernetes에서 Windows 노드와 Linux 노드가 혼합된 클러스터를 구성할 때 필요한 네트워크 솔루션은 무엇인가요?
   - A) 모든 CNI 플러그인이 Windows와 Linux 노드를 모두 지원함
   - B) Flannel, Calico, Antrea와 같은 Windows를 지원하는 CNI 플러그인
   - C) Windows 노드는 CNI 플러그인 없이 kubenet만 사용해야 함
   - D) Windows 노드는 항상 호스트 네트워크 모드만 사용해야 함
   
<details>
<summary>정답 보기</summary>

**정답: B) Flannel, Calico, Antrea와 같은 Windows를 지원하는 CNI 플러그인**

**설명:**
Kubernetes에서 Windows 노드와 Linux 노드가 혼합된 클러스터를 구성할 때는 Windows를 지원하는 특정 CNI(Container Network Interface) 플러그인을 사용해야 합니다. 모든 CNI 플러그인이 Windows를 지원하는 것은 아닙니다.

Windows 노드를 지원하는 주요 CNI 플러그인은 다음과 같습니다:

- **Flannel**: overlay 네트워크 모드(vxlan)로 Windows 노드를 지원합니다.
- **Calico**: Windows 노드에 대한 지원을 제공하며, BGP 모드와 VXLAN 모드를 모두 지원합니다.
- **Antrea**: Windows 노드에 대한 지원을 제공하며, OVS(Open vSwitch)를 사용합니다.

이외에도 Azure CNI, OVN-Kubernetes 등이 Windows 노드를 지원합니다.

Windows 노드에서 CNI 플러그인을 설정할 때 고려해야 할 사항:
- Windows 노드는 Linux 노드와 다른 네트워킹 스택을 가지고 있습니다.
- 일부 네트워킹 기능은 Windows에서 제한될 수 있습니다.
- CNI 플러그인의 Windows 지원 버전과 구성 요구 사항을 확인해야 합니다.

kubenet은 Windows 노드에서 지원되지 않으며, Windows 노드는 호스트 네트워크 모드를 사용할 수 없습니다(HostNetwork=true가 Windows 포드에서 지원되지 않음).
</details>

3. Windows 컨테이너의 기본 격리 모드는 무엇인가요?
   - A) Hyper-V 격리
   - B) 프로세스 격리
   - C) 가상 머신 격리
   - D) 샌드박스 격리
   
<details>
<summary>정답 보기</summary>

**정답: B) 프로세스 격리**

**설명:**
Windows 컨테이너의 기본 격리 모드는 프로세스 격리(Process Isolation)입니다. 이 모드에서 Windows 컨테이너는 호스트 운영 체제의 커널을 공유하며, 각 컨테이너는 격리된 프로세스 그룹으로 실행됩니다.

프로세스 격리 모드의 특징:
- 호스트 OS와 동일한 커널 버전을 사용해야 합니다.
- 리소스 사용량이 적고 시작 시간이 빠릅니다.
- Linux 컨테이너의 일반적인 격리 모델과 유사합니다.

Windows는 또한 Hyper-V 격리(Hyper-V Isolation)라는 대체 격리 모드를 제공합니다:
- 각 컨테이너는 경량 가상 머신에서 실행됩니다.
- 호스트 OS와 다른 커널 버전을 사용할 수 있습니다.
- 더 높은 수준의 격리를 제공하지만, 오버헤드가 더 큽니다.

Kubernetes에서 Hyper-V 격리를 사용하려면 포드 스펙에 다음과 같은 주석을 추가해야 합니다:
```yaml
annotations:
  io.kubernetes.cri-containerd.isolation: hyperv
```

가상 머신 격리는 Windows 컨테이너의 공식 격리 모드가 아니며, 샌드박스 격리는 Windows 컨테이너에서 사용되는 용어가 아닙니다.
</details>

4. Kubernetes에서 Windows 노드를 사용할 때의 제한 사항 중 올바르지 않은 것은 무엇인가요?
   - A) 특권 컨테이너(privileged containers)를 사용할 수 없음
   - B) HostPath 볼륨을 사용할 수 없음
   - C) 포드의 SecurityContext 기능 중 일부만 지원됨
   - D) 포드 네트워크 네임스페이스를 공유할 수 없음
   
<details>
<summary>정답 보기</summary>

**정답: B) HostPath 볼륨을 사용할 수 없음**

**설명:**
Windows 노드에서도 HostPath 볼륨을 사용할 수 있습니다. 따라서 "HostPath 볼륨을 사용할 수 없음"이라는 설명은 올바르지 않습니다.

Windows 노드에서 HostPath 볼륨을 사용할 때는 Windows 경로 형식을 따라야 합니다:
```yaml
volumes:
- name: data
  hostPath:
    path: C:\\data
```

Kubernetes에서 Windows 노드를 사용할 때의 실제 제한 사항은 다음과 같습니다:

- **특권 컨테이너(privileged containers)**: Windows 노드에서는 특권 컨테이너를 사용할 수 없습니다. Linux의 특권 모드와 동등한 개념이 Windows에 없기 때문입니다.

- **SecurityContext 제한**: Windows 노드에서는 포드의 SecurityContext 기능 중 일부만 지원됩니다. 예를 들어, runAsUser, runAsGroup, fsGroup, seccomp, SELinux 등은 지원되지 않습니다.

- **포드 네트워크 네임스페이스 공유**: Windows 노드에서는 포드 간에 네트워크 네임스페이스를 공유할 수 없습니다. 이는 hostNetwork: true, dnsPolicy: ClusterFirstWithHostNet, 포드 내 컨테이너 간 localhost 통신 등에 영향을 미칩니다.

기타 Windows 노드의 제한 사항:
- DaemonSet이 모든 노드(Linux 및 Windows)에서 실행되도록 하려면 nodeSelector를 사용해야 합니다.
- 일부 스토리지 드라이버와 볼륨 유형이 제한될 수 있습니다.
- Linux 전용 알파/베타 기능은 Windows 노드에서 작동하지 않을 수 있습니다.
</details>

5. Kubernetes에서 Windows 노드를 식별하기 위해 사용되는 노드 레이블은 무엇인가요?
   - A) kubernetes.io/os=windows
   - B) beta.kubernetes.io/os=windows
   - C) node.kubernetes.io/windows=true
   - D) kubernetes.io/windows=enabled
   
<details>
<summary>정답 보기</summary>

**정답: A) kubernetes.io/os=windows**

**설명:**
Kubernetes에서 Windows 노드를 식별하기 위해 사용되는 표준 노드 레이블은 `kubernetes.io/os=windows`입니다. 이 레이블은 노드의 운영 체제 유형을 나타내며, Kubernetes 스케줄러가 포드를 적절한 노드에 배치하는 데 사용됩니다.

Windows 포드를 Windows 노드에 스케줄링하려면 다음과 같이 nodeSelector를 사용합니다:
```yaml
nodeSelector:
  kubernetes.io/os: windows
```

또는 노드 어피니티를 사용할 수도 있습니다:
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/os
          operator: In
          values:
          - windows
```

`beta.kubernetes.io/os=windows`는 이전 버전의 Kubernetes에서 사용되었지만, 현재는 더 이상 사용되지 않습니다(deprecated).

`node.kubernetes.io/windows=true`와 `kubernetes.io/windows=enabled`는 표준 Kubernetes 레이블이 아닙니다.

참고: Linux 노드는 `kubernetes.io/os=linux` 레이블을 가집니다.
</details>

6. Windows 노드에서 컨테이너 이미지를 가져올 때 기본 기본 이미지(base image)는 무엇인가요?
   - A) mcr.microsoft.com/windows/servercore
   - B) mcr.microsoft.com/windows/nanoserver
   - C) mcr.microsoft.com/dotnet/framework/runtime
   - D) mcr.microsoft.com/powershell
   
<details>
<summary>정답 보기</summary>

**정답: A) mcr.microsoft.com/windows/servercore**

**설명:**
Windows 컨테이너의 가장 일반적인 기본 이미지는 `mcr.microsoft.com/windows/servercore`입니다. 이 이미지는 Windows Server Core 설치를 기반으로 하며, 대부분의 Windows 애플리케이션을 실행하는 데 필요한 핵심 구성 요소를 포함하고 있습니다.

Windows 컨테이너에 사용할 수 있는 주요 기본 이미지는 다음과 같습니다:

1. **Windows Server Core** (`mcr.microsoft.com/windows/servercore`):
   - 중간 크기의 이미지(약 2-4GB)
   - 대부분의 Windows 애플리케이션 지원
   - .NET Framework, PowerShell 등 포함
   - 가장 널리 사용되는 Windows 기본 이미지

2. **Nano Server** (`mcr.microsoft.com/windows/nanoserver`):
   - 매우 작은 크기의 이미지(약 100-200MB)
   - 제한된 Windows API 지원
   - .NET Core 애플리케이션에 적합
   - 최소한의 공격 표면

3. **.NET Framework** (`mcr.microsoft.com/dotnet/framework/runtime`):
   - .NET Framework 애플리케이션을 위한 이미지
   - Server Core 기반
   - 특정 버전의 .NET Framework 포함

4. **PowerShell** (`mcr.microsoft.com/powershell`):
   - PowerShell 스크립트 실행을 위한 이미지
   - Nano Server 또는 Server Core 기반 버전 제공

Windows 컨테이너 이미지를 선택할 때는 다음 사항을 고려해야 합니다:
- 애플리케이션 요구 사항(필요한 Windows API)
- 이미지 크기 및 시작 시간
- 보안 요구 사항
- Windows 버전 호환성(이미지 태그의 버전 번호 확인)

Windows 컨테이너 이미지는 호스트 OS와 동일한 버전이거나 호환되는 버전이어야 합니다.
</details>

7. Kubernetes에서 Windows 노드와 Linux 노드가 혼합된 클러스터에서 DaemonSet을 배포할 때 권장되는 방법은 무엇인가요?
   - A) 단일 DaemonSet을 사용하고 모든 노드에 배포
   - B) OS별로 별도의 DaemonSet을 생성하고 nodeSelector 사용
   - C) Windows 노드에는 DaemonSet 대신 StatefulSet 사용
   - D) 모든 DaemonSet에 tolerations 추가
   
<details>
<summary>정답 보기</summary>

**정답: B) OS별로 별도의 DaemonSet을 생성하고 nodeSelector 사용**

**설명:**
Kubernetes에서 Windows 노드와 Linux 노드가 혼합된 클러스터에서 DaemonSet을 배포할 때 권장되는 방법은 OS별로 별도의 DaemonSet을 생성하고 nodeSelector를 사용하는 것입니다.

이 접근 방식이 필요한 이유:
- Windows 컨테이너와 Linux 컨테이너는 서로 다른 이미지 형식을 사용합니다.
- 동일한 애플리케이션이라도 OS별로 다른 구성이 필요할 수 있습니다.
- 일부 기능은 특정 OS에서만 사용 가능할 수 있습니다.

Windows DaemonSet 예시:
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: windows-agent
spec:
  selector:
    matchLabels:
      app: monitoring-agent
  template:
    metadata:
      labels:
        app: monitoring-agent
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: contoso/windows-monitoring-agent:v1
```

Linux DaemonSet 예시:
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: linux-agent
spec:
  selector:
    matchLabels:
      app: monitoring-agent
  template:
    metadata:
      labels:
        app: monitoring-agent
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: agent
        image: contoso/linux-monitoring-agent:v1
```

단일 DaemonSet을 사용하면 컨테이너 이미지 호환성 문제로 인해 일부 노드에서 포드가 시작되지 않을 수 있습니다.

Windows 노드에서도 DaemonSet을 사용할 수 있으므로, StatefulSet으로 대체할 필요는 없습니다.

모든 DaemonSet에 tolerations를 추가하는 것은 테인트가 있는 노드에 포드를 스케줄링하는 데 도움이 될 수 있지만, OS 호환성 문제를 해결하지는 않습니다.
</details>

8. Windows 노드에서 포드의 DNS 구성에 대한 설명으로 올바른 것은 무엇인가요?
   - A) Windows 노드에서는 DNS 구성이 지원되지 않음
   - B) Windows 노드에서는 CoreDNS 대신 Windows DNS 서버를 사용해야 함
   - C) Windows 노드에서도 Linux 노드와 동일한 DNS 구성 사용 가능
   - D) Windows 노드에서는 포드마다 별도의 DNS 서버 구성 필요
   
<details>
<summary>정답 보기</summary>

**정답: C) Windows 노드에서도 Linux 노드와 동일한 DNS 구성 사용 가능**

**설명:**
Windows 노드에서도 Linux 노드와 동일한 DNS 구성을 사용할 수 있습니다. Kubernetes의 DNS 서비스(일반적으로 CoreDNS)는 Windows 포드에서도 동일하게 작동합니다.

Windows 포드의 DNS 구성:
- `/etc/resolv.conf`에 해당하는 구성이 Windows 포드 내에 자동으로 생성됩니다.
- 포드는 클러스터의 DNS 서비스(CoreDNS)를 사용하여 서비스 이름을 확인할 수 있습니다.
- `dnsPolicy` 및 `dnsConfig` 필드를 사용하여 DNS 설정을 구성할 수 있습니다.

예시:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-pod
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    command:
    - powershell.exe
    - -Command
    - "Start-Sleep -Seconds 3600"
  dnsPolicy: ClusterFirst
  dnsConfig:
    nameservers:
    - 8.8.8.8
    searches:
    - example.com
    options:
    - name: ndots
      value: "5"
```

Windows 노드에서 DNS 사용 시 고려 사항:
- Windows 컨테이너 내에서 DNS 클라이언트 동작이 Linux와 약간 다를 수 있습니다.
- 일부 DNS 관련 도구(예: nslookup, Resolve-DnsName)는 Windows 컨테이너에서 기본적으로 사용 가능합니다.
- 네트워크 플러그인이 DNS 확인을 올바르게 지원하는지 확인해야 합니다.

Windows 노드에서 별도의 DNS 서버를 구성하거나 Windows DNS 서버를 사용할 필요는 없습니다. Kubernetes의 표준 DNS 메커니즘이 Windows 포드에서도 작동합니다.
</details>

9. Windows 노드에서 포드 간 통신에 대한 설명으로 올바른 것은 무엇인가요?
   - A) Windows 노드에서는 포드 간 통신이 지원되지 않음
   - B) Windows 노드의 포드는 같은 노드의 포드와만 통신 가능
   - C) Windows 노드의 포드는 Linux 노드의 포드와 통신할 수 없음
   - D) Windows 노드의 포드는 CNI 플러그인을 통해 다른 모든 포드와 통신 가능
   
<details>
<summary>정답 보기</summary>

**정답: D) Windows 노드의 포드는 CNI 플러그인을 통해 다른 모든 포드와 통신 가능**

**설명:**
Windows 노드의 포드는 적절한 CNI(Container Network Interface) 플러그인을 통해 클러스터 내의 다른 모든 포드와 통신할 수 있습니다. 이는 같은 Windows 노드의 포드, 다른 Windows 노드의 포드, 그리고 Linux 노드의 포드를 모두 포함합니다.

Windows 노드에서 포드 간 통신의 주요 특징:
- Windows 노드의 포드는 클러스터 내 서비스를 이름으로 검색하고 접근할 수 있습니다.
- Windows 노드의 포드는 클러스터 IP 주소 범위 내에서 고유한 IP 주소를 할당받습니다.
- 포드 간 통신은 선택한 CNI 플러그인의 구현에 따라 이루어집니다.

Windows 노드에서 포드 간 통신을 지원하는 CNI 플러그인:
- Flannel (VXLAN 모드)
- Calico
- Antrea
- Azure CNI
- OVN-Kubernetes

예를 들어, Flannel을 사용하는 경우:
- Windows 노드의 포드는 VXLAN 캡슐화를 통해 다른 노드의 포드와 통신합니다.
- 각 포드는 클러스터 CIDR 범위 내에서 IP 주소를 할당받습니다.
- 라우팅 테이블은 포드 IP 주소를 적절한 노드로 라우팅하도록 구성됩니다.

Windows 노드에서 포드 간 통신 시 고려 사항:
- 일부 고급 네트워킹 기능은 Windows에서 제한될 수 있습니다.
- 네트워크 정책(NetworkPolicy)의 지원은 CNI 플러그인에 따라 다를 수 있습니다.
- Windows 방화벽 규칙이 포드 통신을 방해하지 않도록 해야 합니다.

Windows 노드의 포드는 Linux 노드의 포드와 완벽하게 통신할 수 있으며, 이는 Kubernetes의 핵심 기능 중 하나입니다.
</details>

10. Kubernetes에서 Windows 컨테이너의 리소스 제한에 대한 설명으로 올바른 것은 무엇인가요?
    - A) Windows 컨테이너는 리소스 제한을 지원하지 않음
    - B) CPU 제한은 지원하지만 메모리 제한은 지원하지 않음
    - C) 메모리 제한은 지원하지만 CPU 제한은 지원하지 않음
    - D) CPU 및 메모리 제한 모두 지원함
    
<details>
<summary>정답 보기</summary>

**정답: D) CPU 및 메모리 제한 모두 지원함**

**설명:**
Kubernetes에서 Windows 컨테이너는 CPU 및 메모리 리소스 제한을 모두 지원합니다. Windows 노드에서도 Linux 노드와 유사한 방식으로 컨테이너 리소스를 제한하고 요청할 수 있습니다.

Windows 컨테이너의 리소스 제한 예시:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: windows-resource-demo
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: windows-container
    image: mcr.microsoft.com/windows/servercore:ltsc2019
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
```

Windows 컨테이너의 리소스 관리 특징:
- **CPU 제한**: Windows는 CPU 공유 및 제한을 구현하여 컨테이너 간 CPU 리소스 할당을 관리합니다.
- **메모리 제한**: Windows는 컨테이너의 메모리 사용량을 제한하고 초과 시 OOM(Out of Memory) 종료를 수행합니다.
- **리소스 모니터링**: kubelet은 Windows 컨테이너의 리소스 사용량을 모니터링하고 Kubernetes API에 보고합니다.

Windows 컨테이너의 리소스 관리 고려 사항:
- Windows 컨테이너의 기본 리소스 오버헤드가 Linux 컨테이너보다 클 수 있습니다.
- 리소스 제한의 정확한 구현은 Windows 버전에 따라 다를 수 있습니다.
- 메모리 제한을 너무 낮게 설정하면 Windows 컨테이너가 제대로 작동하지 않을 수 있습니다.
- Hyper-V 격리 모드를 사용하는 경우 추가 리소스 오버헤드가 발생합니다.

Windows 노드에서도 `kubectl top pods` 및 `kubectl top nodes` 명령을 사용하여 리소스 사용량을 모니터링할 수 있습니다.
</details>
## 주관식 문제

1. Kubernetes 클러스터에 Windows 노드를 추가하기 위한 주요 단계와 요구 사항을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes 클러스터에 Windows 노드 추가 단계:**

1. **사전 요구 사항 확인:**
   - Kubernetes 버전 1.14 이상 (최신 버전 권장)
   - 컨트롤 플레인은 Linux 노드에서 실행되어야 함
   - Windows Server 2019 이상 (Windows Server 2022 권장)
   - 호환되는 CNI 플러그인 (Flannel, Calico, Antrea 등)

2. **네트워킹 구성:**
   - Windows 노드를 지원하는 CNI 플러그인 설치
   - 클러스터 CIDR 및 서비스 CIDR 구성
   - 예시 (Flannel 구성):
     ```yaml
     kind: ConfigMap
     apiVersion: v1
     metadata:
       name: kube-flannel-cfg
       namespace: kube-system
     data:
       cni-conf.json: |
         {
           "name": "cbr0",
           "plugins": [
             {
               "type": "flannel",
               "delegate": {
                 "hairpinMode": true,
                 "isDefaultGateway": true
               }
             },
             {
               "type": "portmap",
               "capabilities": {
                 "portMappings": true
               }
             }
           ]
         }
       net-conf.json: |
         {
           "Network": "10.244.0.0/16",
           "Backend": {
             "Type": "vxlan",
             "VNI": 4096,
             "Port": 4789
           }
         }
     ```

3. **Windows 노드 준비:**
   - Windows Server 설치 및 업데이트
   - 필수 Windows 기능 활성화:
     ```powershell
     Install-WindowsFeature -Name Containers
     Restart-Computer -Force
     ```
   - 컨테이너 런타임 설치 (containerd 권장):
     ```powershell
     # containerd 다운로드 및 설치
     curl.exe -L https://github.com/containerd/containerd/releases/download/v1.6.8/containerd-1.6.8-windows-amd64.tar.gz -o containerd.tar.gz
     tar.exe xvf containerd.tar.gz
     mkdir -p $env:ProgramFiles\containerd
     Copy-Item -Path ".\bin\*" -Destination "$env:ProgramFiles\containerd" -Recurse -Force
     
     # containerd 서비스 등록
     & $env:ProgramFiles\containerd\containerd.exe config default | Out-File $env:ProgramFiles\containerd\config.toml -Encoding ascii
     # 구성 파일 편집 (Windows 관련 설정 추가)
     
     # 서비스 등록 및 시작
     & $env:ProgramFiles\containerd\containerd.exe --register-service
     Start-Service containerd
     ```

4. **kubelet 및 kube-proxy 설치:**
   - Kubernetes 바이너리 다운로드:
     ```powershell
     curl.exe -L https://dl.k8s.io/v1.26.0/kubernetes-node-windows-amd64.tar.gz -o kubernetes-node-windows-amd64.tar.gz
     tar.exe xvf kubernetes-node-windows-amd64.tar.gz
     mkdir -p $env:ProgramFiles\Kubernetes\bin
     Copy-Item -Path "kubernetes\node\bin\*" -Destination "$env:ProgramFiles\Kubernetes\bin" -Recurse -Force
     ```
   - kubelet 구성 파일 생성:
     ```powershell
     New-Item -Path "$env:ProgramFiles\Kubernetes\kubelet-config.yaml" -ItemType File -Force
     # 구성 파일 내용 추가
     ```
   - kubelet 서비스 등록 및 시작:
     ```powershell
     & $env:ProgramFiles\Kubernetes\bin\kubelet.exe --windows-service --config=$env:ProgramFiles\Kubernetes\kubelet-config.yaml
     Start-Service kubelet
     ```
   - kube-proxy 설정 및 시작 (일반적으로 DaemonSet으로 배포)

5. **노드 조인:**
   - kubeadm 조인 명령 실행 또는 수동으로 TLS 인증서 및 kubeconfig 설정
   - 노드가 클러스터에 등록되었는지 확인:
     ```bash
     kubectl get nodes
     ```

6. **노드 레이블 추가:**
   - Windows 노드에 OS 레이블 추가 (자동으로 추가되지 않은 경우):
     ```bash
     kubectl label node <windows-node-name> kubernetes.io/os=windows
     ```

7. **테스트 워크로드 배포:**
   - Windows 컨테이너를 실행하는 간단한 포드 배포:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: windows-test-pod
     spec:
       nodeSelector:
         kubernetes.io/os: windows
       containers:
       - name: windows-server
         image: mcr.microsoft.com/windows/servercore:ltsc2019
         command:
         - powershell.exe
         - -Command
         - "Start-Sleep -Seconds 3600"
     ```

**주요 고려 사항:**

1. **버전 호환성:**
   - Windows Server 버전과 컨테이너 이미지 버전이 호환되어야 함
   - Kubernetes 버전과 Windows 지원 기능 확인

2. **네트워킹:**
   - Windows 노드에서 지원되는 CNI 플러그인 사용
   - 네트워크 정책 지원 확인
   - 포트 요구 사항 확인 (kubelet, containerd, CNI 등)

3. **스토리지:**
   - Windows 노드에서 지원되는 스토리지 드라이버 및 볼륨 유형 확인
   - CSI 드라이버 호환성 확인

4. **모니터링 및 로깅:**
   - Windows 노드에 적합한 모니터링 에이전트 배포
   - Windows 이벤트 로그 수집 구성

5. **보안:**
   - Windows 방화벽 규칙 구성
   - 그룹 관리 서비스 계정(gMSA) 설정 (필요한 경우)
   - 네트워크 보안 그룹 구성

6. **자동화:**
   - Windows 노드 프로비저닝 자동화 (Ansible, PowerShell DSC 등)
   - 노드 업그레이드 전략 수립
</details>

2. Windows 컨테이너와 Linux 컨테이너의 주요 차이점과 Kubernetes에서 이러한 차이점을 관리하는 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Windows 컨테이너와 Linux 컨테이너의 주요 차이점:**

1. **기반 기술:**
   - **Linux 컨테이너**: Linux 네임스페이스, cgroups, 커널 기능을 사용하여 격리
   - **Windows 컨테이너**: Windows 격리 기술(작업 객체, Hyper-V 격리 등)을 사용

2. **이미지 구조:**
   - **Linux 컨테이너**: 상대적으로 작은 크기(수십~수백 MB)
   - **Windows 컨테이너**: 일반적으로 더 큰 크기(수 GB), 기본 이미지가 더 큼

3. **격리 모드:**
   - **Linux 컨테이너**: 단일 격리 모드(네임스페이스 기반)
   - **Windows 컨테이너**: 프로세스 격리 및 Hyper-V 격리 두 가지 모드 지원

4. **파일 시스템:**
   - **Linux 컨테이너**: 계층화된 파일 시스템(OverlayFS 등)
   - **Windows 컨테이너**: NTFS 기반 필터 드라이버

5. **네트워킹:**
   - **Linux 컨테이너**: 다양한 네트워킹 모드 및 드라이버 지원
   - **Windows 컨테이너**: 제한된 네트워킹 모드, 특정 CNI 플러그인만 지원

6. **리소스 관리:**
   - **Linux 컨테이너**: cgroups를 통한 세밀한 리소스 제어
   - **Windows 컨테이너**: Job Objects를 통한 리소스 제어, 일부 제한 있음

7. **보안 컨텍스트:**
   - **Linux 컨테이너**: 다양한 보안 컨텍스트 옵션(SELinux, AppArmor 등)
   - **Windows 컨테이너**: 제한된 보안 컨텍스트 옵션, 특권 컨테이너 미지원

8. **호스트 OS 의존성:**
   - **Linux 컨테이너**: 다양한 Linux 배포판에서 실행 가능
   - **Windows 컨테이너**: 호스트 OS와 동일하거나 호환되는 버전 필요

**Kubernetes에서 이러한 차이점 관리 방법:**

1. **노드 선택 및 스케줄링:**
   - **노드 레이블 사용**: `kubernetes.io/os=windows` 또는 `kubernetes.io/os=linux`
   - **nodeSelector 사용**:
     ```yaml
     nodeSelector:
       kubernetes.io/os: windows
     ```
   - **노드 어피니티 사용**:
     ```yaml
     affinity:
       nodeAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
           nodeSelectorTerms:
           - matchExpressions:
             - key: kubernetes.io/os
               operator: In
               values:
               - windows
     ```

2. **워크로드 분리:**
   - **OS별 Deployment 생성**:
     ```yaml
     # Windows 워크로드용 Deployment
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: windows-app
     spec:
       selector:
         matchLabels:
           app: myapp
           os: windows
       template:
         metadata:
           labels:
             app: myapp
             os: windows
         spec:
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: windows-app
             image: myregistry/windows-app:latest
     
     # Linux 워크로드용 Deployment
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: linux-app
     spec:
       selector:
         matchLabels:
           app: myapp
           os: linux
       template:
         metadata:
           labels:
             app: myapp
             os: linux
         spec:
           nodeSelector:
             kubernetes.io/os: linux
           containers:
           - name: linux-app
             image: myregistry/linux-app:latest
     ```

3. **DaemonSet 관리:**
   - **OS별 DaemonSet 생성**:
     ```yaml
     # Windows 노드용 DaemonSet
     apiVersion: apps/v1
     kind: DaemonSet
     metadata:
       name: windows-agent
     spec:
       selector:
         matchLabels:
           app: monitoring-agent
       template:
         metadata:
           labels:
             app: monitoring-agent
         spec:
           nodeSelector:
             kubernetes.io/os: windows
           containers:
           - name: agent
             image: myregistry/windows-agent:latest
     ```

4. **이미지 관리:**
   - **멀티 아키텍처 이미지 사용**: 동일한 태그로 다양한 OS/아키텍처 지원
   - **OS별 이미지 태그 사용**: `myapp:linux` 및 `myapp:windows`
   - **이미지 풀 정책 설정**: `imagePullPolicy: Always`

5. **리소스 요청 및 제한:**
   - **OS별 적절한 리소스 설정**:
     ```yaml
     resources:
       requests:
         memory: "2Gi"  # Windows 컨테이너는 일반적으로 더 많은 메모리 필요
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```

6. **네트워킹:**
   - **호환되는 CNI 플러그인 선택**: Flannel, Calico, Antrea 등
   - **네트워크 정책 적용 시 OS 고려**:
     ```yaml
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-specific-traffic
     spec:
       podSelector:
         matchLabels:
           app: myapp
       ingress:
       - from:
         - podSelector:
             matchLabels:
               app: frontend
     ```

7. **스토리지:**
   - **OS 호환 스토리지 클래스 사용**:
     ```yaml
     apiVersion: v1
     kind: PersistentVolumeClaim
     metadata:
       name: windows-pvc
     spec:
       storageClassName: windows-storage  # Windows 노드 호환 스토리지 클래스
       accessModes:
         - ReadWriteOnce
       resources:
         requests:
           storage: 10Gi
     ```

8. **보안 컨텍스트:**
   - **OS별 적절한 보안 설정 적용**:
     ```yaml
     # Linux 포드용 보안 컨텍스트
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000
     
     # Windows 포드는 위 설정을 무시하고 다른 보안 메커니즘 사용
     ```

9. **모니터링 및 로깅:**
   - **OS별 모니터링 에이전트 배포**
   - **로그 수집 경로 조정**: Windows(`C:\k\logs`) vs Linux(`/var/log`)

10. **CI/CD 파이프라인:**
    - **OS별 빌드 및 테스트 파이프라인 구성**
    - **멀티 OS 배포 전략 수립**
</details>
3. Windows 컨테이너에서 그룹 관리 서비스 계정(Group Managed Service Accounts, gMSA)을 사용하는 방법과 이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**그룹 관리 서비스 계정(gMSA) 개요:**

그룹 관리 서비스 계정(Group Managed Service Accounts, gMSA)은 Windows 도메인 환경에서 서비스 인증을 위한 특별한 유형의 Active Directory 계정입니다. Kubernetes의 Windows 컨테이너에서 gMSA를 사용하면 도메인 인증이 필요한 애플리케이션을 실행할 수 있으며, 다음과 같은 시나리오에서 특히 유용합니다:

- Active Directory 통합이 필요한 .NET 애플리케이션
- Windows 인증을 사용하는 SQL Server 연결
- Kerberos 인증이 필요한 서비스
- 도메인 리소스에 접근해야 하는 애플리케이션

**Windows 컨테이너에서 gMSA 사용 방법:**

1. **사전 요구 사항:**
   - Active Directory 도메인 컨트롤러
   - Windows 노드가 도메인에 조인되어 있어야 함
   - Kubernetes 버전 1.14 이상
   - containerd 또는 Docker 컨테이너 런타임

2. **Active Directory에서 gMSA 설정:**
   ```powershell
   # 1. KDS 루트 키 생성 (도메인 컨트롤러에서 실행)
   Add-KdsRootKey -EffectiveTime (Get-Date).AddHours(-10)
   
   # 2. gMSA 계정 생성
   New-ADServiceAccount -Name "gmsa-k8s" -DnsHostName "gmsa-k8s.example.com" -ServicePrincipalNames "host/gmsa-k8s", "host/gmsa-k8s.example.com" -PrincipalsAllowedToRetrieveManagedPassword "Domain Computers"
   ```

3. **gMSA 자격 증명 스펙 생성:**
   ```yaml
   apiVersion: windows.k8s.io/v1
   kind: GMSACredentialSpec
   metadata:
     name: gmsa-k8s-credspec
   credspec:
     ActiveDirectoryConfig:
       GroupManagedServiceAccounts:
       - Name: gmsa-k8s
         Scope: EXAMPLE
     CmsPlugins:
     - ActiveDirectory
     DomainJoinConfig:
       DnsName: example.com
       DnsTreeName: example.com
       Guid: 12345678-1234-1234-1234-123456789012
       MachineAccountName: gmsa-k8s
       NetBiosName: EXAMPLE
   ```

4. **자격 증명 스펙을 Kubernetes 시크릿으로 저장:**
   ```bash
   kubectl create secret generic gmsa-k8s-secret --from-file=credspec.json=/path/to/gmsa-credspec.json
   ```

5. **포드 정의에 gMSA 구성 추가:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: iis-gmsa
     labels:
       app: iis-gmsa
   spec:
     securityContext:
       windowsOptions:
         gmsaCredentialSpecName: gmsa-k8s-credspec
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: iis
       image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
       ports:
       - containerPort: 80
   ```

6. **gMSA 사용 검증:**
   ```powershell
   # 컨테이너 내에서 실행
   whoami
   # 출력: EXAMPLE\gmsa-k8s$
   
   nltest /sc_verify:example.com
   # 출력: Trusted DC connections... Passed
   ```

**gMSA 사용의 이점:**

1. **향상된 보안:**
   - 컨테이너 내에서 하드코딩된 자격 증명 제거
   - 자동 비밀번호 관리 및 교체
   - 최소 권한 원칙 적용 가능

2. **Active Directory 통합:**
   - Windows 인증을 사용하는 기존 애플리케이션을 컨테이너화 가능
   - Kerberos 및 NTLM 인증 지원
   - 도메인 리소스에 대한 원활한 접근

3. **중앙 집중식 ID 관리:**
   - Active Directory를 통한 통합 ID 관리
   - 그룹 정책 적용 가능
   - 감사 및 규정 준수 향상

4. **애플리케이션 호환성:**
   - 도메인 인증이 필요한 레거시 .NET 애플리케이션 지원
   - Windows 통합 인증을 사용하는 SQL Server 연결 지원
   - IIS 웹 애플리케이션의 Windows 인증 지원

5. **운영 간소화:**
   - 자격 증명 관리 자동화
   - 컨테이너 재시작 시에도 자격 증명 유지
   - 여러 컨테이너 간 동일한 ID 공유 가능

**gMSA 사용 시 고려 사항:**

1. **네트워크 요구 사항:**
   - Windows 노드에서 도메인 컨트롤러로의 네트워크 연결 필요
   - 적절한 DNS 구성 필요
   - 필요한 포트 개방 (Kerberos, LDAP 등)

2. **권한 관리:**
   - gMSA에 필요한 최소 권한만 부여
   - 적절한 그룹 멤버십 구성
   - 정기적인 권한 검토

3. **확장성:**
   - 대규모 클러스터에서 도메인 컨트롤러 부하 고려
   - 여러 gMSA 계정을 사용하여 권한 분리

4. **문제 해결:**
   - 도메인 연결 문제 디버깅
   - 자격 증명 스펙 구성 오류 확인
   - 컨테이너 런타임 로그 검토
</details>

4. Kubernetes에서 Windows 노드의 로깅 및 모니터링을 구성하는 방법과 Linux 노드와의 차이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Windows 노드의 로깅 및 모니터링 구성:**

**1. 로깅 구성:**

**Windows 노드 로깅의 주요 소스:**
- Windows 이벤트 로그 (System, Application, Security)
- ETW(Event Tracing for Windows) 이벤트
- 애플리케이션 로그 파일 (일반적으로 `C:\` 드라이브 내)
- kubelet 및 컨테이너 런타임 로그 (일반적으로 `C:\k\logs` 또는 유사한 경로)

**Windows 노드 로깅 구성 방법:**

1. **Fluent Bit 또는 Fluentd 설정:**
   ```yaml
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: fluent-bit-windows
     namespace: logging
   spec:
     selector:
       matchLabels:
         app: fluent-bit-windows
     template:
       metadata:
         labels:
           app: fluent-bit-windows
       spec:
         nodeSelector:
           kubernetes.io/os: windows
         containers:
         - name: fluent-bit
           image: fluent/fluent-bit:windows-latest
           volumeMounts:
           - name: config
             mountPath: C:/fluent-bit/conf/
           - name: windows-logs
             mountPath: C:/Windows/System32/winevt/Logs
             readOnly: true
         volumes:
         - name: config
           configMap:
             name: fluent-bit-windows-config
         - name: windows-logs
           hostPath:
             path: C:/Windows/System32/winevt/Logs
   ```

2. **Windows 이벤트 로그 수집 구성:**
   ```ini
   # Fluent Bit Windows 구성
   [INPUT]
       Name            winlog
       Channels        System,Application,Security
       Interval_Sec    1
       DB              C:\\fluent-bit\\winlog.db
   
   [OUTPUT]
       Name            elasticsearch
       Match           *
       Host            elasticsearch-master
       Port            9200
       Index           windows_logs
       Type            _doc
   ```

3. **컨테이너 로그 수집:**
   - containerd 로그 경로: `C:\ProgramData\containerd\root\containers`
   - kubelet 로그 경로: `C:\k\logs` 또는 Windows 이벤트 로그

**2. 모니터링 구성:**

**Windows 노드 모니터링의 주요 메트릭:**
- CPU, 메모리, 디스크 사용량
- 네트워크 트래픽
- 프로세스 수
- 페이지 파일 사용량
- 컨테이너 리소스 사용량

**Windows 노드 모니터링 구성 방법:**

1. **Prometheus Windows Exporter 설정:**
   ```yaml
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: windows-exporter
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: windows-exporter
     template:
       metadata:
         labels:
           app: windows-exporter
       spec:
         nodeSelector:
           kubernetes.io/os: windows
         containers:
         - name: windows-exporter
           image: prometheuscommunity/windows-exporter:latest
           args:
           - --collectors.enabled=cpu,memory,disk,net,service,os,system,container
           ports:
           - containerPort: 9182
             name: metrics
             protocol: TCP
   ```

2. **Prometheus 스크래핑 구성:**
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: windows-exporter
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: windows-exporter
     endpoints:
     - port: metrics
       interval: 30s
   ```

3. **Grafana 대시보드 설정:**
   - Windows 노드 메트릭을 위한 전용 대시보드 생성
   - Windows 특화 패널 (예: 페이지 파일 사용량, 서비스 상태 등) 추가

**3. 문제 해결 도구:**

**Windows 노드 문제 해결을 위한 도구:**
- PowerShell 명령어 (`Get-Process`, `Get-Service`, `Get-EventLog`)
- Windows 성능 모니터 (PerfMon)
- 이벤트 뷰어
- `kubectl debug` 명령 (Windows 노드에서 제한적으로 지원)

**Windows 노드 문제 해결 예시:**
```powershell
# kubelet 로그 확인
Get-EventLog -LogName Application -Source kubelet -Newest 50

# containerd 상태 확인
Get-Service containerd

# 네트워크 연결 확인
Test-NetConnection -ComputerName api.kubernetes.cluster -Port 443
```

**Linux 노드와의 주요 차이점:**

1. **로그 저장 위치:**
   - **Linux**: `/var/log/` 디렉토리에 텍스트 파일로 저장
   - **Windows**: Windows 이벤트 로그(이진 형식) 및 다양한 위치의 텍스트 파일

2. **로그 수집 메커니즘:**
   - **Linux**: 파일 기반 로그 수집이 일반적 (tail, read)
   - **Windows**: Windows 이벤트 로그 API를 통한 수집 필요

3. **메트릭 수집:**
   - **Linux**: `/proc`, `/sys` 파일 시스템에서 메트릭 수집
   - **Windows**: WMI(Windows Management Instrumentation) 또는 성능 카운터 API 사용

4. **컨테이너 로그:**
   - **Linux**: 표준 출력/오류가 파일로 리디렉션됨
   - **Windows**: ETW 또는 파일 기반 로깅, 경로 구조가 다름

5. **리소스 모니터링:**
   - **Linux**: cgroups를 통한 컨테이너 리소스 사용량 모니터링
   - **Windows**: Job Objects를 통한 리소스 모니터링, 일부 메트릭은 다르게 계산됨

6. **모니터링 에이전트:**
   - **Linux**: 다양한 에이전트 지원 (node-exporter, cAdvisor 등)
   - **Windows**: 제한된 에이전트 지원, Windows 전용 에이전트 필요

7. **디버깅 도구:**
   - **Linux**: 다양한 CLI 도구 (ps, top, netstat, strace 등)
   - **Windows**: PowerShell 명령어, GUI 도구, 제한된 CLI 도구

**모범 사례:**

1. **통합 로깅 솔루션:**
   - EFK(Elasticsearch, Fluent Bit, Kibana) 또는 ELK 스택 사용
   - Windows 및 Linux 노드 모두를 위한 구성 분리

2. **통합 모니터링 솔루션:**
   - Prometheus + Grafana로 모든 노드 모니터링
   - OS별 특화된 대시보드 생성

3. **알림 설정:**
   - Windows 특화 이벤트에 대한 알림 규칙 설정
   - 중요 Windows 서비스 상태 모니터링

4. **로그 보존 정책:**
   - Windows 이벤트 로그 크기 및 보존 기간 설정
   - 로그 순환 정책 구성

5. **보안 모니터링:**
   - Windows 보안 이벤트 로그 수집 및 분석
   - 권한 변경 및 로그인 시도 모니터링
</details>

5. Kubernetes에서 Windows 컨테이너를 위한 스토리지 옵션과 볼륨 마운트 구성 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Windows 컨테이너를 위한 스토리지 옵션:**

**1. 기본 볼륨 유형:**

1. **emptyDir:**
   - 포드 수명 동안 임시 데이터 저장
   - Windows 노드의 로컬 NTFS 볼륨에 생성됨
   - 포드가 삭제되면 데이터도 삭제됨
   
   ```yaml
   volumes:
   - name: temp-data
     emptyDir: {}
   ```

2. **hostPath:**
   - Windows 노드의 파일 시스템에 직접 접근
   - Windows 경로 형식 사용 필요 (백슬래시 이스케이프)
   - 노드 간 데이터 공유 불가
   
   ```yaml
   volumes:
   - name: logs
     hostPath:
       path: C:\\Logs
       type: DirectoryOrCreate
   ```

3. **configMap 및 secret:**
   - 구성 데이터 및 민감한 정보 저장
   - Windows 컨테이너에서도 동일하게 작동
   - 파일 권한 설정은 Windows에서 다르게 적용됨
   
   ```yaml
   volumes:
   - name: config
     configMap:
       name: app-config
   ```

4. **persistentVolumeClaim (PVC):**
   - 영구 스토리지 요청
   - Windows 호환 스토리지 클래스 필요
   - CSI 드라이버 지원 여부 확인 필요
   
   ```yaml
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: windows-pvc
   ```

**2. Windows 컨테이너 지원 스토리지 솔루션:**

1. **Azure Disk/File (AKS):**
   - Azure Kubernetes Service에서 Windows 노드 지원
   - SMB 프로토콜 기반 Azure Files 사용 가능
   - Azure Disk CSI 드라이버 지원
   
   ```yaml
   # Azure File PVC
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: azure-file-pvc
   spec:
     accessModes:
     - ReadWriteMany
     storageClassName: azurefile-csi
     resources:
       requests:
         storage: 100Gi
   ```

2. **AWS EBS (EKS):**
   - Amazon EKS의 Windows 노드 지원
   - EBS CSI 드라이버 사용 가능
   - 단일 AZ 내 접근 제한
   
   ```yaml
   # AWS EBS PVC
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: ebs-windows-pvc
   spec:
     accessModes:
     - ReadWriteOnce
     storageClassName: ebs-sc
     resources:
       requests:
         storage: 50Gi
   ```

3. **SMB/CIFS 볼륨:**
   - Windows 환경에 적합한 네트워크 파일 시스템
   - FlexVolume 또는 CSI 드라이버 필요
   - 여러 포드 간 ReadWriteMany 접근 지원
   
   ```yaml
   # SMB CSI 드라이버 사용 예시
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: smb-windows-pvc
   spec:
     accessModes:
     - ReadWriteMany
     storageClassName: smb-csi
     resources:
       requests:
         storage: 100Gi
   ```

4. **iSCSI:**
   - Windows 노드에서 iSCSI 이니시에이터 구성 필요
   - 블록 스토리지 접근 제공
   - 고성능 요구 사항에 적합
   
   ```yaml
   # iSCSI PV 예시
   apiVersion: v1
   kind: PersistentVolume
   metadata:
     name: iscsi-windows-pv
   spec:
     capacity:
       storage: 100Gi
     accessModes:
     - ReadWriteOnce
     persistentVolumeReclaimPolicy: Retain
     iscsi:
       targetPortal: 192.168.1.10:3260
       iqn: iqn.2000-01.com.example:storage.kube.sys1.xyz
       lun: 0
       fsType: ntfs
       readOnly: false
   ```

**3. Windows 컨테이너의 볼륨 마운트 구성:**

1. **볼륨 마운트 경로:**
   - Windows 컨테이너는 Windows 경로 형식 사용
   - 일반적으로 `C:\` 드라이브 내 경로 사용
   - 경로에 백슬래시 사용 시 YAML에서 이스케이프 필요
   
   ```yaml
   volumeMounts:
   - name: data
     mountPath: C:\\data
   ```

2. **읽기 전용 마운트:**
   - Windows 컨테이너에서도 지원됨
   - NTFS 권한으로 적용됨
   
   ```yaml
   volumeMounts:
   - name: config
     mountPath: C:\\config
     readOnly: true
   ```

3. **하위 경로 마운트:**
   - 볼륨의 특정 하위 경로만 마운트 가능
   - Windows 경로 구분자 주의
   
   ```yaml
   volumeMounts:
   - name: shared-data
     mountPath: C:\\app\\logs
     subPath: logs
   ```

**4. Windows 컨테이너 스토리지 구성 예시:**

1. **웹 애플리케이션 구성:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: windows-web-app
   spec:
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: web
       image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
       volumeMounts:
       - name: website
         mountPath: C:\\inetpub\\wwwroot
       - name: logs
         mountPath: C:\\inetpub\\logs
       - name: config
         mountPath: C:\\config
         readOnly: true
     volumes:
     - name: website
       persistentVolumeClaim:
         claimName: website-content-pvc
     - name: logs
       emptyDir: {}
     - name: config
       configMap:
         name: web-config
   ```

2. **데이터베이스 구성:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: windows-sql
   spec:
     nodeSelector:
       kubernetes.io/os: windows
     containers:
     - name: sql
       image: mcr.microsoft.com/mssql/server:2019-latest
       env:
       - name: ACCEPT_EULA
         value: "Y"
       - name: SA_PASSWORD
         valueFrom:
           secretKeyRef:
             name: sql-credentials
             key: sa-password
       volumeMounts:
       - name: data
         mountPath: C:\\var\\opt\\mssql\\data
       - name: backup
         mountPath: C:\\var\\opt\\mssql\\backup
     volumes:
     - name: data
       persistentVolumeClaim:
         claimName: sql-data-pvc
     - name: backup
       persistentVolumeClaim:
         claimName: sql-backup-pvc
   ```

**5. Windows 컨테이너 스토리지 사용 시 고려 사항:**

1. **경로 구분자:**
   - Windows는 백슬래시(`\`)를 사용하지만 YAML에서는 이스케이프 필요
   - 대안으로 슬래시(`/`)를 사용할 수 있지만 애플리케이션 호환성 확인 필요

2. **파일 권한:**
   - Windows는 NTFS 권한 모델 사용
   - Linux의 chmod/chown과 같은 권한 설정 불가
   - 컨테이너 내 권한은 컨테이너 사용자 컨텍스트에 따라 결정됨

3. **성능 고려 사항:**
   - 네트워크 스토리지(SMB/CIFS)는 지연 시간 발생 가능
   - 고성능 요구 사항에는 로컬 스토리지 또는 직접 연결 블록 스토리지 권장

4. **스토리지 클래스 호환성:**
   - Windows 노드와 호환되는 스토리지 클래스 확인
   - CSI 드라이버의 Windows 지원 여부 확인

5. **백업 및 복구:**
   - Windows 볼륨 섀도 복사본 서비스(VSS) 통합 고려
   - 애플리케이션 일관성 있는 백업 메커니즘 구현
</details>
## 실습 문제

1. Windows 노드와 Linux 노드가 혼합된 Kubernetes 클러스터에서 다음 요구 사항을 충족하는 Deployment 매니페스트를 작성하세요:
   - 애플리케이션 이름: web-app
   - Windows 컨테이너 이미지: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
   - 레플리카: 2
   - 포트: 80
   - 환경 변수: WEBSITE_NAME=MyWindowsApp
   - 볼륨: ConfigMap "web-config"를 C:\inetpub\wwwroot\web.config로 마운트

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: iis
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
        ports:
        - containerPort: 80
        env:
        - name: WEBSITE_NAME
          value: "MyWindowsApp"
        volumeMounts:
        - name: config-volume
          mountPath: C:\inetpub\wwwroot\web.config
          subPath: web.config
      volumes:
      - name: config-volume
        configMap:
          name: web-config
---
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**설명:**

1. **Deployment 리소스**:
   - `nodeSelector`를 사용하여 Windows 노드에만 스케줄링되도록 지정
   - 요구 사항에 따라 2개의 레플리카 설정
   - IIS 웹 서버 이미지 사용

2. **컨테이너 구성**:
   - 포트 80 노출
   - 환경 변수 `WEBSITE_NAME` 설정
   - ConfigMap을 특정 파일 경로에 마운트 (Windows 경로 형식 사용)

3. **볼륨 구성**:
   - ConfigMap을 볼륨으로 마운트
   - `subPath`를 사용하여 ConfigMap의 특정 키를 파일로 마운트

4. **서비스 정의**:
   - 애플리케이션에 접근하기 위한 ClusterIP 서비스 생성
   - 포트 80을 통해 접근 가능

**참고 사항**:
- Windows 경로에서 백슬래시(`\`)는 YAML에서 이스케이프 문자로 처리되므로 주의해야 합니다. 이 예제에서는 일반 백슬래시를 사용했지만, 더 복잡한 경로에서는 이중 백슬래시(`\\`)나 슬래시(`/`)를 사용할 수 있습니다.
- Windows 컨테이너는 Linux 컨테이너보다 리소스 요구 사항이 더 높을 수 있으므로, 프로덕션 환경에서는 적절한 리소스 요청 및 제한을 설정하는 것이 좋습니다.
</details>

2. Windows 노드와 Linux 노드 모두에서 실행되는 모니터링 에이전트를 배포하기 위한 DaemonSet 매니페스트를 작성하세요. 각 OS에 맞는 이미지와 구성을 사용해야 합니다.

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
# Linux 노드용 DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: monitoring-agent-linux
  namespace: monitoring
  labels:
    app: monitoring-agent
    os: linux
spec:
  selector:
    matchLabels:
      app: monitoring-agent
      os: linux
  template:
    metadata:
      labels:
        app: monitoring-agent
        os: linux
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: agent
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
          name: metrics
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        securityContext:
          runAsNonRoot: true
          runAsUser: 65534
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
---
# Windows 노드용 DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: monitoring-agent-windows
  namespace: monitoring
  labels:
    app: monitoring-agent
    os: windows
spec:
  selector:
    matchLabels:
      app: monitoring-agent
      os: windows
  template:
    metadata:
      labels:
        app: monitoring-agent
        os: windows
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: agent
        image: prometheuscommunity/windows-exporter:latest
        ports:
        - containerPort: 9182
          name: metrics
        args:
        - --collectors.enabled=cpu,memory,disk,net,service,os,system,container
---
# 모니터링 에이전트를 위한 서비스
apiVersion: v1
kind: Service
metadata:
  name: monitoring-agent
  namespace: monitoring
  labels:
    app: monitoring-agent
spec:
  type: ClusterIP
  ports:
  - name: linux-metrics
    port: 9100
    targetPort: 9100
    protocol: TCP
  - name: windows-metrics
    port: 9182
    targetPort: 9182
    protocol: TCP
  selector:
    app: monitoring-agent
```

**설명:**

1. **Linux 노드용 DaemonSet**:
   - `nodeSelector`를 사용하여 Linux 노드에만 스케줄링
   - Prometheus Node Exporter 이미지 사용
   - 호스트의 `/proc`, `/sys`, `/` 디렉토리를 마운트하여 시스템 메트릭 수집
   - 보안 컨텍스트 설정으로 비루트 사용자로 실행

2. **Windows 노드용 DaemonSet**:
   - `nodeSelector`를 사용하여 Windows 노드에만 스케줄링
   - Windows Exporter 이미지 사용
   - 수집할 메트릭 컬렉터 지정
   - Windows 특화 구성 적용

3. **공통 서비스**:
   - 두 DaemonSet의 포드를 모두 선택하는 서비스 생성
   - Linux 및 Windows 메트릭 포트 모두 노출
   - Prometheus가 이 서비스를 통해 메트릭을 스크래핑할 수 있음

**참고 사항**:
- 각 OS에 맞는 이미지와 구성을 사용하는 것이 중요합니다.
- Linux와 Windows 노드에서 메트릭 수집 방식이 다르므로 별도의 DaemonSet으로 분리했습니다.
- 레이블을 사용하여 OS 유형을 구분하면 모니터링 시스템에서 메트릭을 필터링하고 시각화하는 데 유용합니다.
- 프로덕션 환경에서는 리소스 요청 및 제한, 보안 컨텍스트, 서비스 계정 등을 추가로 구성해야 합니다.
</details>

3. Windows 컨테이너에서 Active Directory 인증을 사용하는 .NET 애플리케이션을 배포하기 위한 포드 매니페스트를 작성하세요. 그룹 관리 서비스 계정(gMSA)을 사용해야 합니다.

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
# gMSA 자격 증명 스펙을 위한 시크릿
apiVersion: v1
kind: Secret
metadata:
  name: gmsa-credential-spec
  namespace: default
type: Opaque
data:
  credspec.json: BASE64_ENCODED_CREDENTIAL_SPEC_HERE
---
# gMSA를 사용하는 Windows 포드
apiVersion: v1
kind: Pod
metadata:
  name: ad-auth-app
  labels:
    app: ad-auth-app
spec:
  nodeSelector:
    kubernetes.io/os: windows
  securityContext:
    windowsOptions:
      gmsaCredentialSpecName: gmsa-credential-spec
  containers:
  - name: dotnet-app
    image: myregistry/ad-auth-app:latest
    ports:
    - containerPort: 80
    env:
    - name: ASPNETCORE_ENVIRONMENT
      value: "Production"
    volumeMounts:
    - name: app-config
      mountPath: C:\app\appsettings.json
      subPath: appsettings.json
    resources:
      requests:
        memory: "2Gi"
        cpu: "500m"
      limits:
        memory: "4Gi"
        cpu: "1000m"
  volumes:
  - name: app-config
    configMap:
      name: ad-auth-app-config
---
# 애플리케이션 구성을 위한 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: ad-auth-app-config
data:
  appsettings.json: |
    {
      "Logging": {
        "LogLevel": {
          "Default": "Information",
          "Microsoft": "Warning"
        }
      },
      "ConnectionStrings": {
        "DefaultConnection": "Server=sql-server;Database=AppDB;Integrated Security=True;"
      },
      "ActiveDirectory": {
        "Domain": "example.com",
        "UseWindowsAuthentication": true
      }
    }
---
# 서비스 정의
apiVersion: v1
kind: Service
metadata:
  name: ad-auth-app
spec:
  selector:
    app: ad-auth-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**설명:**

1. **gMSA 자격 증명 스펙 시크릿**:
   - Active Directory gMSA 자격 증명 스펙을 Base64로 인코딩하여 시크릿으로 저장
   - 이 시크릿은 포드가 도메인 인증을 위해 사용

2. **Windows 포드 구성**:
   - `nodeSelector`를 사용하여 Windows 노드에 스케줄링
   - `securityContext.windowsOptions.gmsaCredentialSpecName`을 사용하여 gMSA 자격 증명 스펙 참조
   - .NET 애플리케이션 이미지 사용
   - 적절한 리소스 요청 및 제한 설정

3. **볼륨 및 구성**:
   - ConfigMap을 사용하여 애플리케이션 설정 제공
   - Windows 경로 형식으로 구성 파일 마운트
   - 통합 Windows 인증을 사용하는 SQL Server 연결 문자열 포함

4. **서비스 정의**:
   - 애플리케이션에 접근하기 위한 ClusterIP 서비스 생성

**gMSA 설정을 위한 사전 요구 사항**:

1. **Active Directory 도메인 컨트롤러 설정**:
   ```powershell
   # KDS 루트 키 생성 (도메인 컨트롤러에서 실행)
   Add-KdsRootKey -EffectiveTime (Get-Date).AddHours(-10)
   
   # gMSA 계정 생성
   New-ADServiceAccount -Name "k8s-gmsa" -DnsHostName "k8s-gmsa.example.com" -ServicePrincipalNames "host/k8s-gmsa", "host/k8s-gmsa.example.com" -PrincipalsAllowedToRetrieveManagedPassword "Domain Computers"
   ```

2. **자격 증명 스펙 생성**:
   ```powershell
   # Windows 노드에서 실행
   Import-Module ActiveDirectory
   $CredSpec = New-CimInstance -Namespace root/Microsoft/Windows/CredentialSpecification -ClassName Win32_CredentialSpecification -Property @{Name = "k8s-gmsa"; ActiveDirectoryCredentialSpec = Get-CredentialSpec -Name k8s-gmsa -Json}
   
   # 자격 증명 스펙 내용 확인
   Get-CredentialSpec -Name k8s-gmsa -Json
   ```

3. **자격 증명 스펙을 Kubernetes 시크릿으로 변환**:
   ```bash
   # 자격 증명 스펙 JSON을 Base64로 인코딩
   cat credspec.json | base64 -w 0
   
   # 인코딩된 값을 시크릿 YAML에 추가
   ```

**참고 사항**:
- Windows 노드가 Active Directory 도메인에 조인되어 있어야 합니다.
- containerd 또는 Docker가 gMSA를 지원하도록 구성되어 있어야 합니다.
- 실제 환경에서는 자격 증명 스펙 내용을 안전하게 관리해야 합니다.
- 애플리케이션이 Windows 인증을 올바르게 사용하도록 구성되어 있어야 합니다.
</details>

4. Windows 노드와 Linux 노드가 혼합된 클러스터에서 네트워크 정책(NetworkPolicy)을 사용하여 다음 요구 사항을 충족하는 매니페스트를 작성하세요:
   - Windows 웹 애플리케이션 포드(레이블: app=windows-web)는 Linux 데이터베이스 포드(레이블: app=linux-db)에만 접근 가능
   - 데이터베이스 포드는 포트 3306에서만 접근 허용
   - 웹 애플리케이션 포드는 외부에서 포트 80으로 접근 가능

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
# Windows 웹 애플리케이션을 위한 네트워크 정책
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: windows-web-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: windows-web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - ports:
    - port: 80
      protocol: TCP
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: linux-db
    ports:
    - port: 3306
      protocol: TCP
---
# Linux 데이터베이스를 위한 네트워크 정책
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: linux-db-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: linux-db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: windows-web
    ports:
    - port: 3306
      protocol: TCP
```

**설명:**

1. **Windows 웹 애플리케이션 네트워크 정책**:
   - `app=windows-web` 레이블이 있는 포드에 적용
   - **인그레스(Ingress) 규칙**: 모든 소스에서 포트 80으로의 접근 허용
   - **이그레스(Egress) 규칙**: `app=linux-db` 레이블이 있는 포드의 포트 3306으로만 접근 허용

2. **Linux 데이터베이스 네트워크 정책**:
   - `app=linux-db` 레이블이 있는 포드에 적용
   - **인그레스(Ingress) 규칙**: `app=windows-web` 레이블이 있는 포드에서만 포트 3306으로의 접근 허용

**참고 사항**:
- 네트워크 정책은 CNI 플러그인이 NetworkPolicy를 지원해야 작동합니다(예: Calico, Antrea).
- Windows 노드에서 네트워크 정책 지원은 CNI 플러그인에 따라 다를 수 있습니다.
- 이 예제에서는 기본 네임스페이스를 가정했지만, 실제 환경에서는 적절한 네임스페이스를 지정해야 합니다.
- 프로덕션 환경에서는 DNS 조회, 외부 서비스 접근 등을 위한 추가 이그레스 규칙이 필요할 수 있습니다.

**배포 예시**:

Windows 웹 애플리케이션 포드:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-web
  template:
    metadata:
      labels:
        app: windows-web
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: web
        image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
        ports:
        - containerPort: 80
```

Linux 데이터베이스 포드:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: linux-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app: linux-db
  template:
    metadata:
      labels:
        app: linux-db
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
```
</details>

5. Windows 노드에서 실행되는 .NET Framework 애플리케이션을 위한 Deployment 매니페스트를 작성하세요. 애플리케이션은 Azure Blob Storage에 접근하기 위해 환경 변수로 연결 문자열을 필요로 합니다. 또한 로그를 위한 영구 볼륨을 구성하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
# Azure Storage 연결 문자열을 위한 시크릿
apiVersion: v1
kind: Secret
metadata:
  name: azure-storage-secret
type: Opaque
data:
  connection-string: QWNjb3VudE5hbWU9bXlzdG9yYWdlYWNjb3VudDtBY2NvdW50S2V5PW15YWNjb3VudGtleTtFbmRwb2ludFN1ZmZpeD1jb3JlLndpbmRvd3MubmV0
---
# 로그를 위한 영구 볼륨 클레임
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: windows-logs-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: managed-premium  # Azure Disk 스토리지 클래스 예시
  resources:
    requests:
      storage: 10Gi
---
# .NET Framework 애플리케이션 Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotnet-framework-app
  labels:
    app: dotnet-framework-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dotnet-framework-app
  template:
    metadata:
      labels:
        app: dotnet-framework-app
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: dotnet-app
        image: myregistry/dotnet-framework-app:latest
        ports:
        - containerPort: 80
        env:
        - name: AZURE_STORAGE_CONNECTION_STRING
          valueFrom:
            secretKeyRef:
              name: azure-storage-secret
              key: connection-string
        - name: LOG_LEVEL
          value: "Information"
        - name: ASPNET_ENVIRONMENT
          value: "Production"
        volumeMounts:
        - name: logs-volume
          mountPath: C:\app\logs
        - name: config-volume
          mountPath: C:\app\web.config
          subPath: web.config
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "1000m"
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 60
          periodSeconds: 15
      volumes:
      - name: logs-volume
        persistentVolumeClaim:
          claimName: windows-logs-pvc
      - name: config-volume
        configMap:
          name: dotnet-app-config
---
# 애플리케이션 구성을 위한 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: dotnet-app-config
data:
  web.config: |
    <?xml version="1.0" encoding="utf-8"?>
    <configuration>
      <system.web>
        <compilation debug="false" targetFramework="4.8" />
        <httpRuntime targetFramework="4.8" />
      </system.web>
      <system.webServer>
        <handlers>
          <remove name="ExtensionlessUrlHandler-Integrated-4.0" />
          <add name="ExtensionlessUrlHandler-Integrated-4.0" path="*." verb="*" type="System.Web.Handlers.TransferRequestHandler" preCondition="integratedMode,runtimeVersionv4.0" />
        </handlers>
      </system.webServer>
      <appSettings>
        <add key="BlobContainerName" value="appdata" />
        <add key="LogDirectory" value="C:\app\logs" />
      </appSettings>
    </configuration>
---
# 서비스 정의
apiVersion: v1
kind: Service
metadata:
  name: dotnet-framework-app
spec:
  selector:
    app: dotnet-framework-app
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**설명:**

1. **시크릿 구성**:
   - Azure Storage 연결 문자열을 Base64로 인코딩하여 시크릿으로 저장
   - 애플리케이션에서 환경 변수로 안전하게 접근 가능

2. **영구 볼륨 클레임**:
   - 로그 파일을 위한 10GB 영구 스토리지 요청
   - Azure Disk 스토리지 클래스 사용 (환경에 맞게 조정 필요)
   - ReadWriteOnce 접근 모드 사용

3. **Deployment 구성**:
   - `nodeSelector`를 사용하여 Windows 노드에만 스케줄링
   - .NET Framework 애플리케이션 이미지 사용
   - 환경 변수를 통해 Azure Storage 연결 문자열 제공
   - 로그 디렉토리를 위한 영구 볼륨 마운트
   - web.config 파일을 ConfigMap에서 마운트
   - 적절한 리소스 요청 및 제한 설정
   - 상태 확인을 위한 readiness 및 liveness 프로브 구성

4. **ConfigMap 구성**:
   - .NET Framework 애플리케이션의 web.config 파일 제공
   - 애플리케이션 설정 및 구성 포함

5. **서비스 정의**:
   - 애플리케이션에 접근하기 위한 ClusterIP 서비스 생성

**참고 사항**:
- 실제 환경에서는 이미지 레지스트리 주소, 스토리지 클래스, 리소스 요구 사항 등을 환경에 맞게 조정해야 합니다.
- .NET Framework 애플리케이션은 Windows Server Core 기반 이미지를 사용해야 합니다.
- 프로덕션 환경에서는 인그레스 컨트롤러나 로드 밸런서를 통해 외부 접근을 구성할 수 있습니다.
- Azure Storage 연결 문자열과 같은 민감한 정보는 Azure Key Vault와 같은 외부 시크릿 관리 시스템과 통합하는 것이 좋습니다.
</details>
## 고급 주제

1. Kubernetes에서 Windows 노드의 컨테이너 런타임으로 containerd를 구성할 때 가장 중요한 설정은 무엇인가요?
   - A) sandbox_image 설정
   - B) 로그 수준 및 로그 경로
   - C) 메모리 제한 및 CPU 공유
   - D) 이미지 풀 정책 및 레지스트리 구성

<details>
<summary>정답 보기</summary>

**정답: A) sandbox_image 설정**

**설명:**
Kubernetes에서 Windows 노드의 컨테이너 런타임으로 containerd를 구성할 때 가장 중요한 설정은 `sandbox_image` 설정입니다. 이 설정은 Windows 노드에서 포드 인프라 컨테이너(pause 컨테이너)로 사용할 이미지를 지정합니다.

Windows 노드의 containerd 구성에서 `sandbox_image` 설정이 중요한 이유:

1. **포드 네트워킹**: pause 컨테이너는 포드의 네트워크 네임스페이스를 설정하고 유지하는 역할을 합니다. Windows에서는 Linux와 다른 네트워킹 스택을 사용하므로, Windows 전용 pause 이미지가 필요합니다.

2. **OS 호환성**: Linux pause 이미지는 Windows 노드에서 작동하지 않으며, Windows pause 이미지는 Linux 노드에서 작동하지 않습니다.

3. **버전 호환성**: Windows 버전(예: Windows Server 2019, Windows Server 2022)과 호환되는 적절한 pause 이미지를 선택해야 합니다.

Windows 노드의 containerd 구성 예시:
```toml
[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "microsoft/windows"
  
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes."microsoft/windows"]
  runtime_type = "io.containerd.runhcs.v1"
  
[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2019"
```

일반적으로 사용되는 Windows pause 이미지:
- Windows Server 2019 LTSC: `mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2019`
- Windows Server 2022: `mcr.microsoft.com/oss/kubernetes/pause:3.6-windows-ltsc2022`

다른 옵션들도 중요하지만, `sandbox_image` 설정이 가장 중요합니다:
- 로그 수준 및 로그 경로는 디버깅에 유용하지만, 기능적으로 필수적이지 않습니다.
- 메모리 제한 및 CPU 공유는 성능 튜닝에 중요하지만, 기본 기능에는 영향을 미치지 않습니다.
- 이미지 풀 정책 및 레지스트리 구성은 이미지 관리에 중요하지만, 컨테이너 런타임의 기본 작동에는 영향을 미치지 않습니다.
</details>

2. Windows 컨테이너에서 Hyper-V 격리 모드를 사용하는 주요 이점은 무엇인가요?
   - A) 더 나은 성능과 더 적은 리소스 사용량
   - B) 호스트 OS와 다른 Windows 버전의 컨테이너 실행 가능
   - C) 컨테이너 간 네트워크 통신 속도 향상
   - D) 더 많은 Windows API 및 기능 지원

<details>
<summary>정답 보기</summary>

**정답: B) 호스트 OS와 다른 Windows 버전의 컨테이너 실행 가능**

**설명:**
Windows 컨테이너에서 Hyper-V 격리 모드를 사용하는 주요 이점은 호스트 OS와 다른 Windows 버전의 컨테이너를 실행할 수 있다는 것입니다. 이는 Windows 컨테이너의 중요한 특성 중 하나로, 특히 레거시 애플리케이션을 현대적인 인프라에서 실행해야 할 때 유용합니다.

Hyper-V 격리 모드의 주요 이점:

1. **버전 호환성**: 
   - 호스트 OS와 컨테이너 OS 간의 버전 불일치 문제를 해결합니다.
   - 예를 들어, Windows Server 2022 호스트에서 Windows Server 2019 기반 컨테이너를 실행할 수 있습니다.
   - 이는 프로세스 격리 모드에서는 불가능합니다(프로세스 격리에서는 호스트와 컨테이너가 동일한 커널 버전을 사용해야 함).

2. **향상된 보안 격리**:
   - 각 컨테이너는 경량 가상 머신에서 실행되어 더 강력한 격리를 제공합니다.
   - 컨테이너 간, 그리고 컨테이너와 호스트 간의 보안 경계가 더 강화됩니다.
   - 멀티 테넌트 환경이나 신뢰할 수 없는 코드를 실행할 때 유용합니다.

3. **커널 수준 격리**:
   - 각 컨테이너는 자체 Windows 커널 인스턴스를 가집니다.
   - 이로 인해 커널 수준 격리가 제공되어 한 컨테이너의 커널 문제가 다른 컨테이너나 호스트에 영향을 미치지 않습니다.

Kubernetes에서 Hyper-V 격리 모드를 사용하려면 포드 스펙에 다음과 같은 주석을 추가합니다:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: iis-hyper-v
  annotations:
    io.kubernetes.cri-containerd.isolation: "hyperv"
spec:
  nodeSelector:
    kubernetes.io/os: windows
  containers:
  - name: iis
    image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2019
```

Hyper-V 격리 모드의 단점:
- 더 많은 리소스(메모리, CPU)를 사용합니다.
- 시작 시간이 더 깁니다.
- 호스트에 Hyper-V 기능이 활성화되어 있어야 합니다.

다른 옵션들의 문제점:
- Hyper-V 격리는 실제로 성능이 더 낮고 리소스 사용량이 더 많습니다(A는 틀림).
- 컨테이너 간 네트워크 통신은 실제로 프로세스 격리 모드에서 더 빠릅니다(C는 틀림).
- Windows API 및 기능 지원은 컨테이너 OS 버전에 따라 다르며, Hyper-V 격리 자체가 더 많은 API를 제공하지는 않습니다(D는 틀림).
</details>

3. Kubernetes에서 Windows 노드를 사용할 때 포드 네트워킹에 대한 설명으로 올바른 것은 무엇인가요?
   - A) Windows 노드는 CNI 플러그인을 사용하지 않고 자체 네트워킹 스택을 사용함
   - B) Windows 노드는 Linux 노드와 동일한 CNI 플러그인을 사용하지만 구성이 다름
   - C) Windows 노드는 항상 호스트 네트워크 모드를 사용해야 함
   - D) Windows 노드는 오버레이 네트워크를 지원하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) Windows 노드는 Linux 노드와 동일한 CNI 플러그인을 사용하지만 구성이 다름**

**설명:**
Kubernetes에서 Windows 노드는 Linux 노드와 동일한 CNI(Container Network Interface) 플러그인을 사용할 수 있지만, Windows의 네트워킹 스택이 다르기 때문에 구성이 다릅니다. 이는 혼합 OS 클러스터에서 일관된 네트워킹 모델을 제공하면서도 각 OS의 특성을 고려할 수 있게 합니다.

Windows 노드의 포드 네트워킹 특징:

1. **CNI 플러그인 지원**:
   - Windows 노드는 Flannel, Calico, Antrea 등 여러 CNI 플러그인을 지원합니다.
   - 이러한 플러그인은 Linux와 Windows 노드 모두에서 작동하도록 설계되었습니다.
   - 각 플러그인은 Windows용 특정 구성 요소나 설정을 제공합니다.

2. **네트워킹 모드**:
   - Windows 노드는 일반적으로 오버레이 네트워크(VXLAN, GENEVE 등)를 지원합니다.
   - L2bridge, L2tunnel, overlay 등 다양한 네트워크 모드를 지원합니다.
   - 특히 Flannel의 VXLAN 모드는 Windows 노드에서 널리 사용됩니다.

3. **구성 차이점**:
   - Windows 노드에서는 HNS(Host Network Service)를 사용하여 네트워크 구성을 관리합니다.
   - 네트워크 엔드포인트 생성 및 관리 방식이 Linux와 다릅니다.
   - 일부 고급 네트워킹 기능은 Windows에서 제한될 수 있습니다.

예시 - Flannel CNI 구성:
```yaml
# Linux 및 Windows 노드 모두를 위한 Flannel ConfigMap
kind: ConfigMap
apiVersion: v1
metadata:
  name: kube-flannel-cfg
  namespace: kube-system
data:
  cni-conf.json: |
    {
      "name": "cbr0",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "flannel",
          "delegate": {
            "hairpinMode": true,
            "isDefaultGateway": true
          }
        },
        {
          "type": "portmap",
          "capabilities": {
            "portMappings": true
          }
        }
      ]
    }
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",
      "Backend": {
        "Type": "vxlan",
        "VNI": 4096,
        "Port": 4789
      }
    }
```

Windows 노드에서는 추가 구성이 필요할 수 있습니다:
```powershell
# Windows 노드에서 실행되는 스크립트
$env:KUBE_NETWORK = "cbr0"
$networkName = "vxlan0"
$networkMode = "overlay"
```

다른 옵션들의 문제점:
- Windows 노드는 CNI 플러그인을 사용하며, 자체 네트워킹 스택만 사용하지 않습니다(A는 틀림).
- Windows 노드는 호스트 네트워크 모드를 지원하지 않습니다. `hostNetwork: true`는 Windows 포드에서 작동하지 않습니다(C는 틀림).
- Windows 노드는 오버레이 네트워크(VXLAN 등)를 지원합니다(D는 틀림).
</details>

4. Kubernetes에서 Windows 노드의 리소스 관리에 대한 설명으로 올바른 것은 무엇인가요?
   - A) Windows 노드는 리소스 제한을 지원하지 않음
   - B) Windows 노드는 Linux 노드보다 더 정확한 리소스 제한을 제공함
   - C) Windows 노드는 Job Objects를 사용하여 리소스 제한을 구현함
   - D) Windows 노드는 cgroups를 사용하여 리소스 제한을 구현함

<details>
<summary>정답 보기</summary>

**정답: C) Windows 노드는 Job Objects를 사용하여 리소스 제한을 구현함**

**설명:**
Kubernetes에서 Windows 노드는 Job Objects라는 Windows 운영 체제 기능을 사용하여 컨테이너의 리소스 제한을 구현합니다. 이는 Linux 노드가 cgroups를 사용하는 것과 대조적입니다.

Windows 노드의 리소스 관리 특징:

1. **Job Objects**:
   - Windows에서는 Job Objects를 사용하여 프로세스 그룹의 리소스 사용을 제한합니다.
   - 컨테이너 런타임(containerd 또는 Docker)은 Job Objects API를 사용하여 CPU 및 메모리 제한을 적용합니다.
   - Job Objects는 프로세스 그룹에 대한 CPU 시간, 메모리 사용량, 작업 시간 등을 제한할 수 있습니다.

2. **CPU 제한**:
   - Windows에서 CPU 제한은 CPU 공유(weights) 메커니즘을 통해 구현됩니다.
   - 이는 Linux의 CPU 공유와 유사하지만 구현 방식이 다릅니다.
   - Windows는 CPU 코어 수에 따라 CPU 공유를 조정합니다.

3. **메모리 제한**:
   - Windows 컨테이너의 메모리 제한은 Job Objects의 메모리 제한 기능을 통해 구현됩니다.
   - 컨테이너가 메모리 제한을 초과하면 OOM(Out of Memory) 종료가 발생합니다.
   - Windows의 메모리 관리는 Linux와 다르게 작동하므로, 동일한 메모리 제한 값이라도 실제 동작이 다를 수 있습니다.

4. **리소스 요청 및 제한 구성**:
   - Windows 포드에서도 Linux 포드와 동일한 방식으로 리소스 요청 및 제한을 지정합니다:
     ```yaml
     resources:
       requests:
         memory: "2Gi"
         cpu: "500m"
       limits:
         memory: "4Gi"
         cpu: "1"
     ```
   - kubelet은 이러한 값을 Windows 컨테이너 런타임에 전달하고, 런타임은 Job Objects를 사용하여 제한을 적용합니다.

5. **모니터링 및 보고**:
   - kubelet은 Windows 성능 카운터를 사용하여 컨테이너 리소스 사용량을 모니터링합니다.
   - 이 정보는 `kubectl top pods` 및 `kubectl top nodes` 명령을 통해 확인할 수 있습니다.
   - 메트릭 서버는 이 정보를 수집하여 Kubernetes API를 통해 제공합니다.

Windows 노드의 리소스 관리 고려 사항:
- Windows 컨테이너는 일반적으로 Linux 컨테이너보다 더 많은 기본 리소스를 사용합니다.
- Windows 컨테이너의 메모리 오버헤드가 더 클 수 있으므로, 충분한 여유 메모리를 확보해야 합니다.
- 리소스 제한의 정확한 동작은 Windows 버전에 따라 다를 수 있습니다.

다른 옵션들의 문제점:
- Windows 노드는 리소스 제한을 지원합니다(A는 틀림).
- Windows 노드는 일반적으로 Linux 노드보다 덜 정확한 리소스 제한을 제공합니다(B는 틀림).
- Windows 노드는 cgroups가 아닌 Job Objects를 사용합니다(D는 틀림).
</details>

5. Kubernetes에서 Windows 노드를 사용할 때 보안 모범 사례로 가장 적절하지 않은 것은 무엇인가요?
   - A) 컨테이너 이미지를 정기적으로 스캔하고 업데이트하여 보안 취약점 해결
   - B) 모든 Windows 포드에 특권 모드(privileged mode) 활성화
   - C) Active Directory 통합을 위해 gMSA(그룹 관리 서비스 계정) 사용
   - D) 네트워크 정책을 사용하여 포드 간 통신 제한

<details>
<summary>정답 보기</summary>

**정답: B) 모든 Windows 포드에 특권 모드(privileged mode) 활성화**

**설명:**
Kubernetes에서 Windows 노드를 사용할 때 "모든 Windows 포드에 특권 모드(privileged mode) 활성화"는 보안 모범 사례로 적절하지 않습니다. 사실, Windows 컨테이너는 특권 모드를 지원하지 않으며, 이러한 설정을 시도하면 포드 생성이 실패합니다.

이 옵션이 부적절한 이유:

1. **특권 모드 미지원**:
   - Windows 컨테이너는 Linux 컨테이너의 특권 모드와 같은 개념을 지원하지 않습니다.
   - Windows의 보안 모델은 Linux와 다르며, 호스트 수준의 특권을 컨테이너에 부여하는 메커니즘이 없습니다.

2. **최소 권한 원칙 위반**:
   - 설령 지원된다 하더라도, 모든 포드에 특권 모드를 활성화하는 것은 최소 권한 원칙에 위배됩니다.
   - 각 워크로드는 필요한 최소한의 권한만 가져야 합니다.

3. **보안 위험 증가**:
   - 특권 모드는 컨테이너가 호스트 시스템에 접근할 수 있게 하므로 보안 위험이 크게 증가합니다.
   - 컨테이너 이스케이프 취약점이 발생할 경우 전체 호스트 시스템이 위험에 노출될 수 있습니다.

다른 옵션들은 모두 적절한 보안 모범 사례입니다:

A) **컨테이너 이미지를 정기적으로 스캔하고 업데이트하여 보안 취약점 해결**:
   - 이미지 스캐닝은 알려진 취약점을 식별하고 해결하는 데 중요합니다.
   - Windows 이미지는 정기적으로 보안 업데이트를 받아야 합니다.
   - 이미지 스캐닝 도구를 CI/CD 파이프라인에 통합하는 것이 좋습니다.

C) **Active Directory 통합을 위해 gMSA(그룹 관리 서비스 계정) 사용**:
   - gMSA는 Windows 컨테이너가 Active Directory 서비스에 안전하게 인증할 수 있게 합니다.
   - 하드코딩된 자격 증명 대신 gMSA를 사용하면 보안이 향상됩니다.
   - 자동 비밀번호 관리 및 교체 기능을 제공합니다.

D) **네트워크 정책을 사용하여 포드 간 통신 제한**:
   - 네트워크 정책은 최소 권한 원칙을 네트워크 통신에 적용합니다.
   - 포드 간 통신을 필요한 경우로만 제한하여 공격 표면을 줄입니다.
   - 네트워크 세분화는 측면 이동(lateral movement) 공격을 방지하는 데 도움이 됩니다.

Windows 노드의 보안을 강화하기 위한 추가 모범 사례:
- Windows 노드를 최신 보안 패치로 유지
- 불필요한 Windows 기능 및 역할 비활성화
- Windows 방화벽 규칙 적절히 구성
- 강력한 인증 메커니즘 사용
- 컨테이너 이미지에 불필요한 도구 및 구성 요소 제거
- 런타임 보안 모니터링 구현
</details>
