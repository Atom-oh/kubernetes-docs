# Linux 기초 퀴즈

이 퀴즈는 Kubernetes와 컨테이너 기술의 기반이 되는 Linux 기초 개념에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Linux 커널의 주요 역할이 아닌 것은 무엇인가요?
   - A) 프로세스 관리
   - B) 메모리 관리
   - C) 사용자 인터페이스 제공
   - D) 장치 관리
<details>

<summary>정답 보기</summary>

**정답: C) 사용자 인터페이스 제공**

**설명:**
Linux 커널은 운영체제의 핵심으로, 하드웨어와 소프트웨어 사이의 중개자 역할을 합니다. 커널의 주요 역할은 프로세스 관리, 메모리 관리, 장치 관리, 시스템 호출 인터페이스 제공 등입니다. 사용자 인터페이스(GUI, CLI)는 사용자 공간에서 실행되는 별도의 프로그램이 제공하며, 커널의 역할이 아닙니다.

</details>

2. 다음 중 Linux 네임스페이스의 종류가 아닌 것은 무엇인가요?
   - A) PID 네임스페이스
   - B) 네트워크 네임스페이스
   - C) 메모리 네임스페이스
   - D) 사용자 네임스페이스
<details>

<summary>정답 보기</summary>

**정답: C) 메모리 네임스페이스**

**설명:**
Linux에는 다음과 같은 네임스페이스가 있습니다: PID(프로세스 ID), 네트워크, 마운트, UTS(호스트명), IPC(프로세스 간 통신), 사용자, cgroup 네임스페이스. 메모리 네임스페이스는 존재하지 않습니다. 메모리 격리는 주로 cgroups를 통해 관리됩니다.

</details>

3. cgroups(Control Groups)의 주요 기능은 무엇인가요?
   - A) 프로세스 그룹의 자원 사용 제한 및 격리
   - B) 파일 시스템 접근 제어
   - C) 네트워크 패킷 필터링
   - D) 사용자 인증 관리
   
<details>

<summary>정답 보기</summary>

**정답: A) 프로세스 그룹의 자원 사용 제한 및 격리**

**설명:**
cgroups는 프로세스 그룹의 자원 사용을 제한하고 격리하는 Linux 커널 기능입니다. CPU 시간, 메모리, 블록 I/O, 네트워크 대역폭 등의 자원 사용을 제한하고 모니터링할 수 있습니다. 이는 컨테이너의 자원 제한을 구현하는 데 핵심적인 기술입니다.
</details>

4. 파일 권한 "rwxr-xr--"에서 그룹 사용자의 권한은 무엇인가요?
   - A) 읽기, 쓰기, 실행
   - B) 읽기, 실행
   - C) 읽기만
   - D) 실행만
   
<details>

<summary>정답 보기</summary>

**정답: B) 읽기, 실행**

**설명:**
파일 권한 "rwxr-xr--"에서:
  - 첫 3자리(rwx): 소유자 권한 - 읽기, 쓰기, 실행
  - 중간 3자리(r-x): 그룹 권한 - 읽기, 실행
  - 마지막 3자리(r--): 기타 사용자 권한 - 읽기만

따라서 그룹 사용자는 읽기와 실행 권한을 가집니다.

</details>

5. 컨테이너 이미지 레이어를 구현하는 데 주로 사용되는 파일 시스템은 무엇인가요?
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>정답 보기</summary>

**정답: C) OverlayFS**

**설명:**
OverlayFS는 여러 디렉토리를 겹쳐서 단일 디렉토리로 표현하는 유니온 마운트 파일 시스템입니다. Docker와 같은 컨테이너 런타임에서 이미지 레이어를 구현하는 데 주로 사용됩니다. 이를 통해 기본 이미지는 읽기 전용으로 유지하면서 컨테이너별 쓰기 가능 레이어를 추가할 수 있습니다.
</details>

6. systemctl 명령어로 서비스를 관리할 때, 부팅 시 자동 시작을 설정하는 명령은 무엇인가요?
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>정답 보기</summary>

**정답: B) systemctl enable**

**설명:**
`systemctl enable`은 서비스가 시스템 부팅 시 자동으로 시작되도록 설정합니다. `start`는 서비스를 즉시 시작하고, `restart`는 서비스를 재시작하며, `reload`는 설정 파일만 다시 읽습니다. Kubernetes 노드에서 kubelet, containerd 같은 핵심 서비스는 `systemctl enable`로 자동 시작을 설정해야 합니다.
</details>

7. Kubernetes 클러스터 설정에 필수적인 커널 파라미터로, 컨테이너 네트워킹을 위해 IP 패킷 포워딩을 활성화하는 설정은 무엇인가요?
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>정답 보기</summary>

**정답: B) net.ipv4.ip_forward**

**설명:**
`net.ipv4.ip_forward`는 Linux 커널에서 IP 패킷 포워딩을 활성화하는 설정입니다. 이 설정이 1로 활성화되어야 컨테이너 간, 그리고 컨테이너와 외부 네트워크 간의 통신이 가능합니다. Kubernetes 노드 설정 시 이 파라미터는 반드시 활성화되어야 하며, `sysctl -w net.ipv4.ip_forward=1` 명령으로 설정할 수 있습니다.
</details>

8. systemd 유닛 파일에서 서비스 간의 시작 순서를 정의할 때, 특정 서비스 이후에 시작되도록 설정하는 지시어는 무엇인가요?
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>정답 보기</summary>

**정답: C) After**

**설명:**
systemd 유닛 파일에서 `After`는 현재 유닛이 지정된 유닛 이후에 시작되어야 함을 정의합니다. 예를 들어, `After=network-online.target`은 네트워크가 준비된 후에 서비스가 시작되도록 합니다. `Requires`는 강한 의존성을, `Wants`는 약한 의존성을 정의하며, `Before`는 현재 유닛이 다른 유닛보다 먼저 시작되어야 함을 나타냅니다.
</details>

9. CNI 플러그인이 정상적으로 작동하기 위해 필요한 커널 파라미터로, 브릿지 트래픽이 iptables를 통과하도록 하는 설정은 무엇인가요?
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>정답 보기</summary>

**정답: B) net.bridge.bridge-nf-call-iptables**

**설명:**
`net.bridge.bridge-nf-call-iptables`는 브릿지된 네트워크 트래픽이 iptables 규칙을 통과하도록 설정합니다. 이 설정은 Kubernetes CNI 플러그인(Calico, Flannel 등)이 네트워크 정책과 서비스 라우팅을 올바르게 적용하기 위해 필수적입니다. 이 설정을 활성화하려면 먼저 `br_netfilter` 커널 모듈을 로드해야 합니다.
</details>

10. 패키지 관리에서 Kubernetes 구성 요소의 자동 업그레이드를 방지하기 위해 Ubuntu/Debian에서 사용하는 명령은 무엇인가요?
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>정답 보기</summary>

**정답: B) apt-mark hold**

**설명:**
`apt-mark hold`는 특정 패키지가 자동으로 업그레이드되지 않도록 고정합니다. Kubernetes 클러스터에서는 kubelet, kubeadm, kubectl의 버전 호환성이 중요하므로, `sudo apt-mark hold kubelet kubeadm kubectl` 명령으로 버전을 고정하는 것이 권장됩니다. RHEL/CentOS에서는 `yum versionlock` 명령을 사용합니다.
</details>

## 단답형 문제

11. 프로세스가 종료되었지만 부모 프로세스가 상태를 확인하지 않은 상태의 프로세스를 무엇이라고 하나요?

<details>

<summary>정답 보기</summary>

**정답: 좀비 프로세스(Zombie Process)**

**설명:**
좀비 프로세스는 실행이 완료되었지만, 부모 프로세스가 `wait()` 시스템 호출을 통해 종료 상태를 확인하지 않아 프로세스 테이블에 남아있는 프로세스입니다. 좀비 프로세스는 자원을 거의 사용하지 않지만, 많이 누적되면 프로세스 테이블이 가득 차서 새로운 프로세스를 생성할 수 없게 될 수 있습니다.
</details>

12. 프로세스의 네트워크 스택을 격리하는 Linux 네임스페이스의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 네트워크 네임스페이스(Network Namespace)**

**설명:**
네트워크 네임스페이스는 네트워크 스택(네트워크 인터페이스, 라우팅 테이블, 방화벽 규칙, 소켓 등)을 격리합니다. 이를 통해 각 컨테이너는 자체 네트워크 환경을 가질 수 있으며, 호스트 시스템이나 다른 컨테이너의 네트워크와 독립적으로 동작할 수 있습니다.
</details>

13. Linux에서 프로세스가 사용할 수 있는 시스템 호출을 제한하는 보안 기능의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: seccomp(Secure Computing Mode)**

**설명:**
seccomp는 프로세스가 사용할 수 있는 시스템 호출을 제한하는 Linux 커널 보안 기능입니다. 컨테이너 런타임은 seccomp 필터를 사용하여 컨테이너가 수행할 수 있는 시스템 호출을 제한함으로써 보안을 강화합니다.
</details>

14. Linux에서 전통적인 root 권한을 더 작은 권한 단위로 나눈 것을 무엇이라고 하나요?

<details>

<summary>정답 보기</summary>

**정답: 기능(Capabilities)**

**설명:**
Linux 기능(Capabilities)은 전통적인 root 권한을 더 작은 권한 단위로 나눈 것입니다. 이를 통해 프로세스에 필요한 최소한의 권한만 부여할 수 있어 보안을 강화할 수 있습니다. 예를 들어, 네트워크 설정을 변경하려면 `CAP_NET_ADMIN` 기능만 필요하며, 전체 root 권한이 필요하지 않습니다.
</details>

15. 컨테이너 네트워킹에서 호스트와 컨테이너 간의 네트워크 인터페이스 쌍을 무엇이라고 하나요?

<details>

<summary>정답 보기</summary>

**정답: veth 쌍(veth pair)**

**설명:**
veth 쌍은 가상 이더넷 인터페이스 쌍으로, 한쪽 끝은 컨테이너 내부에, 다른 쪽 끝은 호스트 네트워크 네임스페이스에 위치합니다. 이를 통해 컨테이너와 호스트 간의 네트워크 통신이 가능해집니다. 일반적으로 호스트 측 veth 인터페이스는 브릿지(예: docker0)에 연결되어 여러 컨테이너 간의 통신을 가능하게 합니다.
</details>

16. 프로세스가 열 수 있는 최대 파일 디스크립터 수를 확인하고 제한하는 데 사용하는 명령은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: ulimit**

**설명:**
ulimit은 사용자 및 프로세스의 리소스 제한을 확인하고 설정하는 명령입니다. `ulimit -n`으로 열 수 있는 파일 디스크립터 수를 확인하고, `ulimit -n 65536`으로 제한을 변경할 수 있습니다. Kubernetes 노드에서는 많은 파일 핸들이 필요하므로, `/etc/security/limits.conf`에서 영구적으로 높은 값을 설정하는 것이 일반적입니다.
</details>

17. systemd의 로깅 시스템으로, 서비스 로그를 통합적으로 관리하는 데 사용되는 도구의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: journald (또는 systemd-journald)**

**설명:**
journald는 systemd의 통합 로깅 시스템으로, 시스템 및 서비스 로그를 수집하고 저장합니다. `journalctl` 명령을 통해 로그를 조회할 수 있으며, `-u` 옵션으로 특정 서비스의 로그를, `-f` 옵션으로 실시간 로그를 확인할 수 있습니다. Kubernetes 노드에서 kubelet 로그는 `journalctl -u kubelet`으로 확인합니다.
</details>

18. 시스템의 시간을 NTP 서버와 동기화하는 데 사용되는 현대적인 데몬의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: chronyd (또는 chrony)**

**설명:**
chronyd는 현대적인 NTP 클라이언트/서버로, 기존 ntpd보다 빠르게 시간을 동기화합니다. `chronyc tracking` 명령으로 동기화 상태를 확인하고, `chronyc sources`로 NTP 서버 목록을 볼 수 있습니다. Kubernetes 클러스터에서는 모든 노드의 시간이 정확하게 동기화되어야 인증, 로깅 등이 올바르게 작동합니다.
</details>

19. Linux에서 DNS 이름 해석 설정이 저장되는 파일의 경로는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: /etc/resolv.conf**

**설명:**
`/etc/resolv.conf`는 DNS 이름 해석 설정을 저장하는 파일로, nameserver, search 도메인, options 등을 정의합니다. Kubernetes 환경에서 이 파일은 CoreDNS와 함께 중요한 역할을 하며, Pod의 DNS 설정에도 영향을 줍니다. 현대 시스템에서는 systemd-resolved가 이 파일을 동적으로 관리하기도 합니다.
</details>

## 실습 문제

20. 새로운 네트워크 네임스페이스를 생성하고, 해당 네임스페이스 내에서 네트워크 인터페이스 목록을 확인하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 새로운 네트워크 네임스페이스 생성
ip netns add mynetns

# 해당 네임스페이스 내에서 네트워크 인터페이스 목록 확인
ip netns exec mynetns ip link list
```

**설명:**
첫 번째 명령어는 "mynetns"라는 이름의 새로운 네트워크 네임스페이스를 생성합니다. 두 번째 명령어는 해당 네임스페이스 내에서 `ip link list` 명령을 실행하여 네트워크 인터페이스 목록을 확인합니다. 새로 생성된 네트워크 네임스페이스에는 기본적으로 루프백 인터페이스(lo)만 존재하며, 이 인터페이스도 기본적으로는 down 상태입니다.
</details>

21. 특정 프로세스(PID: 1234)의 cgroup 정보를 확인하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
cat /proc/1234/cgroup
```

**설명:**
Linux에서는 `/proc/<PID>/cgroup` 파일을 통해 특정 프로세스의 cgroup 정보를 확인할 수 있습니다. 이 파일은 프로세스가 속한 모든 cgroup 계층 구조와 컨트롤러 정보를 보여줍니다. 또는 `systemd-cgls` 명령어를 사용하여 cgroup 계층 구조를 트리 형태로 볼 수도 있습니다.
</details>

22. 파일 "example.sh"에 소유자에게는 읽기, 쓰기, 실행 권한을, 그룹에게는 읽기와 실행 권한을, 다른 사용자에게는 읽기 권한만 부여하는 chmod 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
chmod 754 example.sh
```

또는

```bash
chmod u=rwx,g=rx,o=r example.sh
```

**설명:**
첫 번째 방법은 숫자 표기법을 사용합니다:
  - 7(rwx): 소유자에게 읽기(4), 쓰기(2), 실행(1) 권한 부여
  - 5(r-x): 그룹에게 읽기(4)와 실행(1) 권한 부여
  - 4(r--): 다른 사용자에게 읽기(4) 권한만 부여

두 번째 방법은 기호 표기법을 사용하여 동일한 권한을 설정합니다.
</details>

23. 시스템의 현재 메모리 사용량을 확인하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
free -h
```

**설명:**
`free` 명령어는 시스템의 메모리 사용량을 표시합니다. `-h` 옵션은 사람이 읽기 쉬운 형식(human-readable format)으로 출력합니다(예: GB, MB). 출력에는 총 메모리, 사용 중인 메모리, 여유 메모리, 버퍼/캐시에 사용된 메모리, 스왑 메모리 정보 등이 포함됩니다.
</details>

24. 특정 포트(예: 8080)에서 실행 중인 프로세스를 찾는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
lsof -i :8080
```

또는

```bash
netstat -tulpn | grep :8080
```

또는

```bash
ss -tulpn | grep :8080
```

**설명:**
  - `lsof -i :8080`: 8080 포트를 사용하는 프로세스를 표시합니다.
  - `netstat -tulpn | grep :8080`: TCP/UDP 연결 목록에서 8080 포트를 사용하는 항목을 찾습니다. `-t`(TCP), `-u`(UDP), `-l`(listening), `-p`(프로세스 정보), `-n`(숫자로 표시) 옵션을 사용합니다.
  - `ss -tulpn | grep :8080`: `netstat`의 현대적인 대체 명령어로, 동일한 정보를 제공합니다.
</details>

25. Kubernetes 노드에 필요한 커널 모듈 br_netfilter와 overlay를 부팅 시 자동으로 로드하도록 설정하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
EOF

# 현재 세션에서 즉시 로드
sudo modprobe overlay
sudo modprobe br_netfilter
```

**설명:**
`/etc/modules-load.d/` 디렉토리에 `.conf` 파일을 생성하면 systemd-modules-load 서비스가 부팅 시 해당 모듈을 자동으로 로드합니다. `overlay` 모듈은 OverlayFS 파일 시스템을 지원하여 컨테이너 이미지 레이어에 사용되고, `br_netfilter` 모듈은 브릿지 트래픽이 iptables를 통과하도록 하여 Kubernetes 네트워킹에 필수적입니다.
</details>

26. kubelet 서비스의 실시간 로그를 확인하면서, 에러 수준 이상의 메시지만 필터링하는 journalctl 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
journalctl -u kubelet -f -p err
```

또는

```bash
journalctl -u kubelet -f -p warning
```

**설명:**
  - `-u kubelet`: kubelet 서비스의 로그만 표시
  - `-f`: 실시간으로 새 로그 스트리밍 (tail -f와 유사)
  - `-p err`: 에러 수준 이상의 로그만 표시 (err, crit, alert, emerg)
  - `-p warning`: 경고 수준 이상의 로그 표시 (warning, err, crit, alert, emerg)

journalctl의 우선순위 레벨은 0(emerg)부터 7(debug)까지 있으며, 지정한 레벨과 그보다 높은 우선순위의 메시지가 표시됩니다.
</details>

27. 시스템의 현재 시간대를 확인하고, Asia/Seoul로 변경하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 현재 시간대 확인
timedatectl

# 시간대 변경
sudo timedatectl set-timezone Asia/Seoul
```

**설명:**
`timedatectl` 명령은 systemd의 시간 관리 유틸리티로, 시스템의 시간, 날짜, 시간대를 설정하고 확인할 수 있습니다. `timedatectl list-timezones` 명령으로 사용 가능한 시간대 목록을 확인할 수 있습니다. Kubernetes 클러스터에서 모든 노드는 동일한 시간대를 사용하거나, UTC를 사용하는 것이 로그 분석과 문제 해결에 도움이 됩니다.
</details>

28. 파일 디스크립터 제한을 영구적으로 65536으로 설정하기 위해 /etc/security/limits.conf에 추가해야 하는 설정을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
*               soft    nofile          65536
*               hard    nofile          65536
```

또는 특정 사용자/서비스에 대해:
```bash
root            soft    nofile          65536
root            hard    nofile          65536
```

**설명:**
`/etc/security/limits.conf`는 PAM(Pluggable Authentication Modules)이 사용하는 설정 파일로, 사용자별 리소스 제한을 정의합니다. `*`는 모든 사용자를, `soft`는 기본 제한을, `hard`는 최대 제한을 의미합니다. `nofile`은 열 수 있는 파일 디스크립터 수를 지정합니다. Kubernetes 노드에서는 많은 네트워크 연결과 파일 핸들이 필요하므로 이 값을 높게 설정해야 합니다.
</details>

## 심화 문제

29. Linux 커널에서 컨테이너 격리를 위해 사용되는 주요 기술 3가지를 설명하고, 각각이 어떤 종류의 격리를 제공하는지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

1. **네임스페이스(Namespaces)**:
  - 네임스페이스는 프로세스 그룹을 격리하여 각 그룹이 시스템 자원을 독립적으로 볼 수 있게 합니다.
  - 주요 네임스페이스 유형:
  - PID 네임스페이스: 프로세스 ID 격리
  - 네트워크 네임스페이스: 네트워크 스택 격리 (인터페이스, 라우팅 테이블, 방화벽 등)
  - 마운트 네임스페이스: 파일 시스템 마운트 포인트 격리
  - UTS 네임스페이스: 호스트명과 도메인명 격리
  - IPC 네임스페이스: 프로세스 간 통신 자원 격리
  - 사용자 네임스페이스: 사용자 및 그룹 ID 격리
  - cgroup 네임스페이스: cgroup 루트 디렉토리 격리

2. **cgroups(Control Groups)**:
  - cgroups는 프로세스 그룹의 자원 사용을 제한하고 격리하는 기능입니다.
  - 제공하는 격리:
  - CPU 시간 제한
  - 메모리 사용량 제한
  - 블록 I/O 대역폭 제한
  - 네트워크 대역폭 제한
  - 장치 접근 제어

3. **기능(Capabilities)**:
  - Linux 기능은 전통적인 root 권한을 더 작은 권한 단위로 나눈 것입니다.
  - 제공하는 격리:
  - 권한 격리: 컨테이너에 필요한 최소한의 권한만 부여
  - 보안 강화: 불필요한 권한을 제거하여 보안 위험 감소
  - 예: `CAP_NET_ADMIN`(네트워크 설정 변경), `CAP_SYS_ADMIN`(시스템 관리 작업) 등

이 세 가지 기술을 조합하여 컨테이너는 호스트 시스템과 다른 컨테이너로부터 격리된 환경에서 실행될 수 있으며, 자원 사용을 제한하고 보안을 강화할 수 있습니다.
</details>

30. OverlayFS가 컨테이너 이미지 레이어를 관리하는 방식을 설명하고, 읽기 전용 레이어와 쓰기 가능 레이어의 관계를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

OverlayFS는 유니온 마운트 파일 시스템으로, 여러 디렉토리를 겹쳐서 단일 디렉토리로 표현합니다. 컨테이너 이미지 레이어 관리에 있어 OverlayFS는 다음과 같은 방식으로 작동합니다:

1. **레이어 구조**:
  - **Lower 디렉토리(읽기 전용 레이어)**: 기본 이미지 레이어들로, 여러 개가 존재할 수 있습니다. 이미지의 기본 파일 시스템과 애플리케이션 코드 등이 포함됩니다.
  - **Upper 디렉토리(쓰기 가능 레이어)**: 컨테이너 실행 시 생성되는 쓰기 가능한 레이어입니다. 컨테이너 내에서 발생하는 모든 변경사항이 이 레이어에 저장됩니다.
  - **Work 디렉토리**: OverlayFS의 내부 작업을 위한 임시 디렉토리입니다.
  - **Merged 디렉토리**: 모든 레이어가 통합되어 보이는 최종 뷰로, 컨테이너가 실제로 보는 파일 시스템입니다.

2. **읽기 전용 레이어와 쓰기 가능 레이어의 관계**:
  - **파일 읽기**: 파일을 읽을 때, OverlayFS는 먼저 Upper 디렉토리(쓰기 가능 레이어)에서 파일을 찾습니다. 없으면 Lower 디렉토리(읽기 전용 레이어)에서 순차적으로 찾습니다.
  - **파일 쓰기**: 파일을 수정할 때, Copy-on-Write(CoW) 방식이 사용됩니다. 읽기 전용 레이어의 파일을 수정하려고 하면, 해당 파일이 먼저 쓰기 가능 레이어로 복사된 후 수정됩니다. 원본 파일은 변경되지 않습니다.
  - **파일 삭제**: 읽기 전용 레이어의 파일을 삭제하려고 하면, 실제로 파일이 삭제되지 않고 쓰기 가능 레이어에 "whiteout" 파일이 생성되어 해당 파일이 삭제된 것처럼 보이게 합니다.

3. **이점**:
  - **공간 효율성**: 여러 컨테이너가 동일한 기본 이미지 레이어를 공유하므로 디스크 공간이 절약됩니다.
  - **빠른 시작 시간**: 새 컨테이너를 시작할 때 전체 파일 시스템을 복사할 필요 없이 쓰기 가능 레이어만 생성하면 됩니다.
  - **이미지 버전 관리**: 기본 이미지에 새 레이어를 추가하여 이미지를 업데이트할 수 있습니다.

이러한 방식으로 OverlayFS는 컨테이너의 이미지 레이어를 효율적으로 관리하며, 컨테이너가 독립적인 파일 시스템을 가지면서도 기본 이미지를 공유할 수 있게 합니다.
</details>

31. Linux 기능(capabilities)이 컨테이너 보안에 어떤 영향을 미치는지 설명하고, 컨테이너에 필요한 최소한의 기능만 부여하는 것이 왜 중요한지 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**Linux 기능(capabilities)과 컨테이너 보안:**

Linux 기능은 전통적인 root 권한을 더 작은 권한 단위로 나눈 것으로, 컨테이너 보안에 다음과 같은 영향을 미칩니다:

1. **권한 세분화**:
  - 전통적으로 프로세스는 root(UID 0) 또는 비root로만 구분되었습니다.
  - 기능을 통해 root 권한을 여러 개의 개별 권한으로 나눌 수 있어, 프로세스에 필요한 특정 권한만 부여할 수 있습니다.
  - 예: 네트워크 설정을 변경하려면 전체 root 권한 대신 `CAP_NET_ADMIN` 기능만 필요합니다.

2. **컨테이너 보안 강화**:
  - 컨테이너 런타임은 기본적으로 컨테이너에 제한된 기능 집합만 부여합니다.
  - 이를 통해 컨테이너가 호스트 시스템에 미치는 영향을 제한할 수 있습니다.
  - 컨테이너 내부에서 root로 실행되는 프로세스도 제한된 기능만 가지므로 보안 위험이 감소합니다.

3. **주요 컨테이너 관련 기능**:
  - `CAP_NET_ADMIN`: 네트워크 설정 변경
  - `CAP_SYS_ADMIN`: 시스템 관리 작업 (매우 강력한 기능)
  - `CAP_CHOWN`: 파일 소유권 변경
  - `CAP_DAC_OVERRIDE`: 파일 권한 무시
  - `CAP_SETUID`: UID 변경
  - `CAP_SETGID`: GID 변경

**최소 권한 원칙의 중요성:**

컨테이너에 필요한 최소한의 기능만 부여하는 것이 중요한 이유는 다음과 같습니다:

1. **공격 표면 감소**:
  - 불필요한 기능을 제거하면 공격자가 악용할 수 있는 벡터가 줄어듭니다.
  - 컨테이너가 침해되더라도 공격자가 할 수 있는 행동이 제한됩니다.

2. **컨테이너 이스케이프 방지**:
  - 강력한 기능(특히 `CAP_SYS_ADMIN`)은 컨테이너 이스케이프(컨테이너에서 호스트로 접근)를 가능하게 할 수 있습니다.
  - 이러한 기능을 제한함으로써 컨테이너 이스케이프 위험을 크게 줄일 수 있습니다.

3. **심층 방어 전략**:
  - 최소 권한 원칙은 보안의 심층 방어 전략의 일부입니다.
  - 다른 보안 메커니즘(seccomp, AppArmor, SELinux 등)과 함께 사용하면 더욱 강력한 보안을 제공합니다.

4. **규정 준수**:
  - 많은 보안 표준과 규정은 최소 권한 원칙을 요구합니다.
  - 컨테이너에 필요한 최소한의 기능만 부여함으로써 이러한 요구사항을 충족할 수 있습니다.

5. **문제 격리**:
  - 컨테이너에 제한된 기능만 부여하면 한 컨테이너의 문제가 다른 컨테이너나 호스트 시스템으로 확산되는 것을 방지할 수 있습니다.

실제 운영 환경에서는 컨테이너가 필요로 하는 기능을 정확히 파악하고, 그 외의 모든 기능은 제거하는 것이 좋은 보안 관행입니다. 이를 위해 Docker의 `--cap-drop`, `--cap-add` 옵션이나 Kubernetes의 `securityContext.capabilities` 필드를 사용할 수 있습니다.
</details>

32. systemd 서비스 유닛 파일의 구조와 주요 섹션([Unit], [Service], [Install])의 역할을 설명하고, Kubernetes kubelet 서비스를 위한 기본적인 유닛 파일 예시를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**systemd 유닛 파일의 주요 섹션:**

1. **[Unit] 섹션**: 유닛의 메타데이터와 의존성 정의
   - `Description`: 서비스 설명
   - `Documentation`: 문서 URL
   - `After/Before`: 시작 순서 정의
   - `Requires/Wants`: 의존성 정의

2. **[Service] 섹션**: 서비스 실행 방법 정의
   - `Type`: 서비스 유형 (simple, forking, oneshot 등)
   - `ExecStart`: 실행할 명령
   - `Restart`: 재시작 정책
   - `RestartSec`: 재시작 대기 시간

3. **[Install] 섹션**: 유닛 활성화(enable) 시 동작 정의
   - `WantedBy`: 이 유닛을 원하는 타겟

**kubelet 서비스 유닛 파일 예시:**

```ini
[Unit]
Description=kubelet: The Kubernetes Node Agent
Documentation=https://kubernetes.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/kubelet
Restart=always
StartLimitInterval=0
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**설명:**
이 유닛 파일은 kubelet 서비스를 정의합니다. 네트워크가 준비된 후에 시작되며(`After=network-online.target`), 실패 시 항상 재시작하고(`Restart=always`), 10초 간격으로 재시작을 시도합니다(`RestartSec=10`). `WantedBy=multi-user.target`은 시스템이 다중 사용자 모드로 부팅될 때 이 서비스가 시작됨을 의미합니다.
</details>

33. Kubernetes 노드 설정에 필요한 sysctl 커널 파라미터들을 영구적으로 설정하는 방법과 각 파라미터의 역할을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**Kubernetes에 필요한 주요 sysctl 설정과 역할:**

```bash
# /etc/sysctl.d/99-kubernetes.conf 파일 생성
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
# IP 포워딩 활성화 - 컨테이너 간 패킷 라우팅에 필수
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# 브릿지 트래픽이 iptables를 통과 - CNI 네트워크 정책에 필수
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# 연결 추적 테이블 크기 (대규모 클러스터용)
net.netfilter.nf_conntrack_max = 1000000
EOF

# 설정 적용
sudo sysctl --system
```

**각 파라미터의 역할:**

1. **net.ipv4.ip_forward = 1**
   - Linux 커널이 네트워크 인터페이스 간에 패킷을 전달(포워딩)하도록 허용
   - Pod에서 다른 Pod 또는 외부 네트워크로의 통신에 필수
   - 비활성화 시 컨테이너 네트워킹이 작동하지 않음

2. **net.bridge.bridge-nf-call-iptables = 1**
   - 브릿지를 통과하는 트래픽이 iptables 규칙을 적용받도록 설정
   - Kubernetes 서비스(ClusterIP, NodePort)와 NetworkPolicy가 올바르게 작동하는 데 필수
   - kube-proxy가 서비스 라우팅을 위해 iptables를 사용하므로 반드시 필요

3. **net.ipv6.conf.all.forwarding = 1**
   - IPv6 환경에서의 패킷 포워딩 활성화
   - 듀얼 스택 클러스터에서 필요

**설정 적용 순서:**
1. 먼저 `br_netfilter` 모듈 로드: `modprobe br_netfilter`
2. sysctl 설정 파일 생성
3. `sysctl --system`으로 모든 설정 적용

이러한 설정 없이는 Kubernetes 클러스터의 네트워킹이 정상적으로 작동하지 않으며, 특히 Pod 간 통신과 서비스 디스커버리에 문제가 발생합니다.
</details>

34. journald와 logrotate를 사용한 Linux 로그 관리 전략을 설명하고, Kubernetes 노드에서 효율적인 로그 관리를 위한 설정 방법을 제시하세요.

<details>

<summary>정답 보기</summary>

**정답:**

**journald와 logrotate의 역할:**

**journald (systemd 기반 로깅):**
- systemd 서비스의 stdout/stderr 로그 수집
- 바이너리 형식으로 저장, journalctl로 조회
- 자동 로그 압축 및 순환 지원

**logrotate (전통적 로그 파일 관리):**
- 텍스트 로그 파일의 순환, 압축, 삭제 관리
- 크론잡으로 주기적 실행

**Kubernetes 노드 로그 관리 설정:**

**1. journald 설정 (/etc/systemd/journald.conf):**
```ini
[Journal]
# 디스크에 영구 저장
Storage=persistent

# 최대 디스크 사용량 (전체 /var/log/journal)
SystemMaxUse=2G

# 최대 파일 크기
SystemMaxFileSize=100M

# 최소 여유 공간 유지
SystemKeepFree=1G

# 최대 보관 기간
MaxRetentionSec=1month
```

**2. 컨테이너 로그를 위한 logrotate 설정:**
```bash
# /etc/logrotate.d/containers
/var/log/containers/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
```

**3. 로그 정리 명령:**
```bash
# journald 로그 정리
journalctl --vacuum-time=7d   # 7일 이전 로그 삭제
journalctl --vacuum-size=1G   # 1GB 이상 시 오래된 로그 삭제

# 디스크 사용량 확인
journalctl --disk-usage
```

**Kubernetes 로그 관리 모범 사례:**

1. **kubelet 로그**: journald가 관리, `/var/log/journal/`에 저장
2. **컨테이너 로그**: `/var/log/containers/`에 저장, logrotate로 관리
3. **중앙 집중 로깅**: Fluentd/Fluent Bit으로 외부 시스템에 전송 권장

적절한 로그 관리는 디스크 공간 부족으로 인한 노드 장애를 방지하고, 문제 해결을 위한 로그를 보존하는 균형을 유지합니다.
</details>

---

[학습 자료로 돌아가기](../../basics/01-linux-basics.md) | [다음 퀴즈: 컨테이너 기술](./02-container-technology-quiz.md)
