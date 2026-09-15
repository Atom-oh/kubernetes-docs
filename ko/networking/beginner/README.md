# Linux 네트워크 입문

> **학습 기준**: Ubuntu Server 24.04 LTS, Rocky Linux 9 대체 경로
>
> **마지막 업데이트**: 2026년 9월 15일

터미널을 처음 여는 사람을 위한 과정입니다. 파일을 만들고 프로그램을 설치하는 것부터 시작해 IP·DNS 설정, SSH 접속, 방화벽, 패킷 관측을 직접 수행합니다. 마지막에는 작은 웹 서비스의 장애를 진단하고 Docker·Kubernetes·클라우드 학습으로 이어갑니다.

명령어를 모두 외울 필요는 없습니다. **어느 장비에서 무엇을 바꾸는지, 성공을 무엇으로 확인하는지, 원래 상태로 어떻게 돌리는지** 설명할 수 있는 것이 목표입니다.

## 학습 순서 {#course-map}

처음이라면 1장부터 순서대로 진행하세요. Linux 경험이 있어도 2장의 주소·인터페이스 확인과 공통 실습 환경은 맞춰야 합니다. 시간은 개인 실습을 포함한 학습 계획용 추정치이며 숙련도에 따라 달라집니다.

| 순서 | 학습 내용 | 끝나면 할 수 있는 일 | 예상 시간 |
|---|---|---|---|
| 1 | [Linux와 CLI](01-linux-cli.md) · [퀴즈](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | 배포판을 확인하고 파일·편집기·패키지·서비스를 다룬다 | 2–3시간 |
| 2 | [주소와 인터페이스](02-addressing-interfaces.md) · [퀴즈](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | IP·서브넷·게이트웨이·DNS 역할을 구분하고 NIC를 식별한다 | 2–3시간 |
| 3 | [영구 네트워크 설정](03-persistent-configuration.md) · [퀴즈](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) | Netplan 또는 NetworkManager로 설정하고 재부팅·복구를 확인한다 | 3–4시간 |
| 4 | [DNS와 연결 진단](04-dns-connectivity.md) · [퀴즈](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) | 이름 해석·경로·포트·HTTP 문제를 나눠 조사한다 | 2–3시간 |
| 5 | [SSH 원격 접속](05-ssh-access.md) · [퀴즈](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | 호스트 키를 확인하고 사용자 키로 로그인한 뒤 설정을 검증한다 | 2–3시간 |
| 6 | [방화벽과 호스트 보안](06-firewalls-host-security.md) · [퀴즈](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | 필요한 통신만 허용하고 SELinux·Fail2ban의 역할을 설명한다 | 3–4시간 |
| 7 | [관측과 성능](07-monitoring-performance.md) · [퀴즈](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) | 소켓·패킷·트래픽을 관측하고 측정 결과의 한계를 설명한다 | 2–3시간 |
| 8 | [종합 실습과 클라우드 연결](08-container-cloud-capstone.md) · [퀴즈](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) | 작은 장애를 재현·분리·복구하고 다음 학습 경로를 고른다 | 3–4시간 |

각 장의 완료 기준을 충족하고 퀴즈 해설을 자신의 말로 설명한 뒤 넘어가세요. 1장에서 패키지 작업을 배운 다음 [게스트 도구 준비](#guest-tools)로 돌아와 2–4장 전에 완료합니다. 커널 튜닝과 CNI 구현 비교는 기본 실습을 마친 뒤 선택합니다.

## 시작 전: 실습 VM 준비 {#lab-environment}

### 첫 번째 VM부터

1. 자신의 PC에서 지원하는 가상화 프로그램을 준비합니다. OS 이미지와 가상 CPU 아키텍처를 맞춥니다. 예를 들어 Arm 장비에는 해당 가상화 도구가 지원하는 Arm 이미지가 필요합니다.
2. [Ubuntu Server 공식 다운로드](https://ubuntu.com/download/server)에서 **24.04 LTS** 이미지를 선택합니다. 이 과정의 버전과 다른 이미지를 사용하면 패키지·서비스 기본값을 다시 확인해야 합니다. [설치 안내](https://documentation.ubuntu.com/server/tutorial/basic-installation/)를 따라 일반 사용자와 비밀번호를 만듭니다. 이 문서의 예시 사용자 이름은 `student`이며 자신의 이름으로 바꿉니다.
3. 학습용 출발점으로 VM당 vCPU 2개, 메모리 2 GiB, 디스크 20 GiB를 배정할 수 있습니다. 이는 성능 보장이나 모든 가상화 도구의 최소 사양이 아닙니다.
4. 첫 NIC는 가상화 도구의 **NAT 네트워크와 DHCP**를 사용합니다. OS 설치·패키지 다운로드에 사용하며 이후 실습에서는 변경하지 않습니다.
5. 가상화 프로그램의 **콘솔 창에서 로그인**해 터미널을 엽니다. 아직 SSH가 없어도 됩니다. 전원을 끄기 전 정상 종료하고, 깨끗한 설치 상태의 스냅샷을 남깁니다.

1장은 VM 한 대면 됩니다. 일반 컨테이너는 전체 VM의 systemd·네트워크 관리자를 대체하지 못합니다. WSL에서 셸 연습은 가능하지만 이후 네트워크·방화벽 실습 환경과 동일하다고 가정하지 않습니다.

### 2장부터 사용할 두 대의 VM

동일한 Ubuntu로 두 대를 준비하면 한 배포판에 집중할 수 있습니다. Rocky Linux 9는 별도의 대체 학습 경로입니다. [Rocky 공식 이미지](https://rockylinux.org/download)와 [문서](https://docs.rockylinux.org/)를 사용하고, 처음부터 두 배포판을 동시에 배울 필요는 없습니다.

1. 두 번째 VM도 독립적으로 설치하고 각각 `net-client`, `net-server`로 구분합니다. 단순 복제는 머신 식별자·SSH 호스트 키까지 복사할 수 있으므로 처음에는 독립 설치를 사용합니다.
2. VM을 정상 종료한 뒤, 두 VM에 **두 번째 NIC**를 추가합니다.
3. 두 번째 NIC들을 같은 **내부 가상 네트워크**에 연결합니다. 예시 이름은 `linux-net-lab`입니다. 이 네트워크에는 DHCP 서버와 외부 uplink를 연결하지 않습니다. 제품의 “브리지”, “NAT”, “호스트 전용” 설정을 이름만 보고 같은 것으로 취급하지 말고 실제 연결 범위를 확인합니다.
4. 각 NIC의 MAC 주소를 가상화 설정에서 기록합니다. VM을 켠 뒤 2장의 `ip -br link` 출력과 대조합니다. 인터페이스 이름은 `eth1`, `enp0s8`, `ens19` 등 환경마다 다르므로 복사해서 쓰지 않습니다.
5. IP 주소는 2장과 3장에서 설정합니다. 설치 화면에서 두 번째 NIC에 임의의 게이트웨이나 DNS를 추가하지 않습니다.

| 항목 | 클라이언트 VM | 서버 VM |
|---|---|---|
| 역할 | SSH·curl 요청을 보내는 쪽 | SSH·HTTP 요청을 받는 쪽 |
| 관리 NIC | 기존 NAT/DHCP 설정 유지 | 기존 NAT/DHCP 설정 유지 |
| 실습 NIC | `192.0.2.10/24` | `192.0.2.20/24` |
| 실습 NIC 게이트웨이·DNS | 없음 | 없음 |
| 복구 경로 | 가상화 콘솔·스냅샷 | 가상화 콘솔·스냅샷 |

```text
클라이언트 실습 NIC                  서버 실습 NIC
192.0.2.10/24 ── 내부 가상 네트워크 ── 192.0.2.20/24
      │                                    │
별도의 NAT/DHCP 관리 NIC              별도의 NAT/DHCP 관리 NIC
```

`192.0.2.0/24`는 문서용 주소 대역이며 이 과정에서는 격리된 로컬 네트워크에만 사용합니다. 이 토폴로지는 인터넷에서 라우팅할 공인망 설계가 아닙니다. 두 VM의 관리 NIC는 여전히 다른 네트워크에 연결되므로 VM 전체가 air gap이라는 뜻도 아닙니다.

## 1장 이후 게스트 도구 준비 {#guest-tools}

먼저 [1장의 패키지 절차](01-linux-cli.md)를 배우고 **2–4장 전에 각 실습 게스트 안에서** 이 준비를 마칩니다. 저장소 연결은 기존 NAT/DHCP 관리 NIC를 사용하며 내부 실습 NIC에 업링크·게이트웨이·DNS 서버를 추가하지 않습니다. 최소 이미지는 네트워크가 정상이어도 진단 도구가 빠져 있을 수 있습니다.

### 없는 명령과 제공 패키지 확인

**각 게스트, 일반 사용자. 조회만 수행합니다.**

```bash
hostname
cat /etc/os-release
command -v ip ss ping getent grep timeout dig tracepath traceroute python3 curl nc ncat
```

실행 파일 경로가 나오면 사용할 수 있습니다. 결과가 불명확하면 `command -v dig`처럼 하나만 조회하세요. 없는 대안 도구에 경로가 나오지 않거나 종료 상태가 0이 아닌 것은 정상입니다. 없는 이름 전부가 아니라 **그 게스트에서 선택한 실습에 필요한 명령**을 기록합니다.

| 명령 / 용도 | Ubuntu Server 24.04 패키지 | Rocky Linux 9 패키지 | 필요한 위치 |
|---|---|---|---|
| `ip`, `ss`: 인터페이스·경로·소켓 | `iproute2` | `iproute` | 두 게스트 |
| `ping`: 제한된 ICMP 검사 | `iputils-ping` | `iputils` | 두 게스트 |
| `dig`: DNS 프로토콜 질의 | `bind9-dnsutils` | `bind-utils` | 4장 클라이언트 |
| `tracepath`: 기본 추적 도구 | `iputils-tracepath` | `iputils` | 클라이언트. 다음 행과 하나 선택 |
| Linux `traceroute`: 추적 대안 | `traceroute` | `traceroute` | 이 대안을 선택한 클라이언트만 |
| `python3`: 임시 HTTP 서버 | `python3`(인터프리터 패키지를 의존성으로 설치) | `python3` | 서버 |
| `curl`: HTTP 요청 | `curl` | 기존 `curl-minimal` **또는** `curl` 제공 패키지 | 클라이언트와 서버 자체 검사 |
| OpenBSD `nc` / Ncat `ncat`: TCP 검사 | `netcat-openbsd` → `nc` 사용 | `nmap-ncat` → `ncat` 사용 | 클라이언트 |

이 준비는 **`tracepath`를 기본 선택**으로 합니다. 이미 설치된 Linux `traceroute`가 있다면 4장의 해당 명령으로 대신 사용할 수 있으며 둘 다 요구하지 않습니다. Rocky의 `iputils`는 `ping`과 `tracepath`를 모두 제공합니다. 비슷한 명령 이름이 같은 옵션을 보장하지 않으므로 지정한 netcat 구현을 사용하세요.

`getent`, `grep`, `timeout`, sudo, 편집기는 게스트·1장의 기본 준비입니다. 이 확인이 실패하면 기본 준비부터 해결합니다. 이 표 때문에 두 번째 네트워크 관리자나 resolver를 설치하지 마세요. **이미 NetworkManager가 관리하는 Rocky 게스트**에서 선택 도구 `nmtui`는 `NetworkManager-tui` 패키지가 제공합니다. 그 인터페이스를 선택했을 때만 같은 패키지 선택 절차로 조회·설치하며 networkd 게스트에는 필요하지 않습니다.

### 변경 미리 보기와 선택한 누락 도구만 설치

첫 설치 전에 게스트 스냅샷 `before-guest-tools`를 만들고 설치된 패키지·제공자 상태를 기록합니다. 아래 **자신의 배포판 분기만** 사용하세요. 각 예시는 **`dig`가 없었던 경우**입니다. 이미 있으면 그 설치는 건너뜁니다. 다른 선택 도구가 없다면 `TOOL_PACKAGE`를 표의 해당 패키지 하나로 바꾸고 후보·작업 내역을 다시 확인합니다. 표 전체를 설치 명령에 붙여 넣지 않습니다.

**Ubuntu 게스트, 일반 사용자. 표시한 명령만 sudo:**

```bash
TOOL_PACKAGE=bind9-dnsutils
dpkg-query -W "$TOOL_PACKAGE"
sudo apt update
apt-cache policy "$TOOL_PACKAGE"
sudo apt-get --simulate install "$TOOL_PACKAGE"
```

없는 패키지의 로컬 조회에서 “No packages found”는 정상입니다. 저장소 목록 갱신이 성공하면 `Candidate` 버전과 모의 실행의 의존성·업그레이드·제거를 읽습니다. 후보가 없거나 저장소 오류가 나면 구성된 Ubuntu 저장소와 관리 경로를 확인하며 멈춥니다. 패키지는 설치되어 있지만 명령이 없다면 충돌하는 제공자를 설치하지 말고 파일과 명령 검색 경로를 조사합니다.

그 **선택 명령이 실제로 없고** 미리 보기에 의도한 패키지·의존성만 있을 때 **Ubuntu 게스트**에 설치합니다.

```bash
sudo apt install "$TOOL_PACKAGE"
```

미리 보기와 설치 사이에 메타데이터가 바뀔 수 있으므로 실제 질문도 확인합니다. 예상 밖의 업그레이드·제거를 자동 승인하지 마세요.

**Rocky 게스트, 일반 사용자:** 패키지를 선택하기 전에 curl 제공자를 별도로 확인합니다.

```bash
command -v curl
rpm -q curl curl-minimal
```

두 패키지 중 하나가 “not installed”여도 정상입니다. `curl`이 이미 동작하면 **그 제공 패키지를 유지**하고 다른 쪽을 설치 요청하지 않습니다. 명령 확인이 성공한 뒤 `rpm -qf "$(command -v curl)"`로 소유 패키지를 확인할 수 있습니다. 이 HTTP 실습에는 기존 `curl-minimal`로 충분합니다. `curl`과 `curl-minimal`은 충돌하므로 과정을 따라 하려고 `--allowerasing`이나 패키지 교체를 사용하지 마세요.

`curl`이 없고 **두 제공 패키지가 모두 설치되지 않았을 때** 아래 절차에서 `curl-minimal`을 선택합니다. 제공 패키지는 있는데 명령을 찾지 못한다면 교체 대신 파일·PATH를 확인합니다.

**Rocky 게스트, 일반 사용자. 아래는 `dig`가 없는 경우만의 예시입니다.**

```bash
TOOL_PACKAGE=bind-utils
rpm -q "$TOOL_PACKAGE"
dnf info "$TOOL_PACKAGE"
sudo dnf --assumeno install "$TOOL_PACKAGE"
```

설치 가능한 패키지, 아키텍처, 저장소, 제안된 의존성·제거를 확인합니다. `--assumeno`는 설치하지 않고 작업을 거절합니다. 거절 때문에 종료 상태가 0이 아닌 것은 네트워크 검사 실패가 아닙니다. 후보가 없으면 구성된 Rocky 9 저장소를 조사합니다. 필수 표에는 EPEL이 필요하지 않습니다. 이어서 **선택한 명령이 없을 때만 Rocky 게스트**에 설치합니다.

```bash
sudo dnf install "$TOOL_PACKAGE"
```

최종 작업 내역을 읽고 승인하며 기존 curl 제공자와 네트워크 관리자를 보존합니다. 패키지 후보·버전은 게스트에서 관찰할 값이지 이 문서가 보장하는 고정값이 아닙니다.

### 명령 재확인과 복구 기록

**두 게스트, 일반 사용자:** `command -v ip ss ping getent grep timeout`으로 기본 도구를 찾아야 합니다. 위 기본 선택에서는 지정한 게스트별로 다음을 확인합니다.

```bash
# 클라이언트, 어느 배포판에서든. traceroute를 선택한 경우에만 대체:
command -v dig tracepath curl
```

```bash
# Ubuntu 클라이언트에서만:
command -v nc
```

```bash
# Rocky 클라이언트에서만:
command -v ncat
```

```bash
# 서버, 어느 배포판에서든:
command -v python3 curl
python3 --version
```

선택한 도구 경로와 Python 3.9 이상을 확인합니다. 추가한 패키지를 기록하세요. 이것은 명령 사용 가능성 확인이지 네트워크 통신 성공의 증거가 아닙니다. 4장에서 필요한 명령이 없으면 여기로 돌아옵니다.

이후 장을 위해 도구를 유지합니다. 패키지 이름을 지정해 제거해도 의존성·설정·캐시·로그의 정확한 역작업은 아닙니다. 원래 있던 제공 패키지를 제거하거나 광범위한 autoremove를 정리 수단으로 사용하지 마세요. 이 준비를 완전히 되돌리려면 의존하는 실습을 마친 뒤 `before-guest-tools`로 복원합니다. 스냅샷 이후의 다른 게스트 작업도 사라집니다.

2026년 9월 15일 확인한 배포판 1차 자료: Ubuntu Noble의 [iproute2](https://packages.ubuntu.com/noble/amd64/iproute2/filelist), [ping](https://packages.ubuntu.com/noble/amd64/iputils-ping/filelist), [dig](https://packages.ubuntu.com/noble/amd64/bind9-dnsutils/filelist), [tracepath](https://packages.ubuntu.com/noble/amd64/iputils-tracepath/filelist), [traceroute](https://packages.ubuntu.com/noble/amd64/traceroute/filelist), [netcat](https://packages.ubuntu.com/noble/amd64/netcat-openbsd/filelist), [curl](https://packages.ubuntu.com/noble/amd64/curl/filelist) 파일 목록과 [Python 패키지 의존성](https://packages.ubuntu.com/noble/python3), Rocky 9의 [iproute](https://git.rockylinux.org/staging/rpms/iproute/-/blob/r9/SPECS/iproute.spec), [iputils](https://git.rockylinux.org/staging/rpms/iputils/-/blob/r9/SPECS/iputils.spec), [BIND 도구](https://git.rockylinux.org/staging/rpms/bind/-/blob/r9/SPECS/bind.spec), [Ncat](https://git.rockylinux.org/staging/rpms/nmap/-/blob/r9/SPECS/nmap.spec), [curl 제공 패키지](https://git.rockylinux.org/staging/rpms/curl/-/blob/r9/SPECS/curl.spec) 명세입니다. 실제 게스트 조회로 맞는 아키텍처·버전을 선택하며 예시 x86_64 파일 목록이 그 아키텍처 사용을 요구하는 것은 아닙니다.

## 실습 명령을 읽는 규칙 {#command-conventions}

- `클라이언트`, `서버`, `양쪽` 표시는 명령 실행 위치입니다. 실행 전에 호스트 이름을 확인합니다.
- `$`·`#` 셸 프롬프트는 명령 블록에 넣지 않습니다. `sudo`가 있으면 해당 명령만 관리자 권한을 요청합니다.
- `LAB_IF`처럼 대문자인 값은 현재 셸의 변수입니다. 새 터미널에서는 다시 설정합니다. 실제 NIC를 확인한 뒤 문서의 지시에 따라 값을 대입합니다.
- YAML·INI 블록은 설정 파일 내용이며 셸에 그대로 붙여넣는 명령이 아닙니다.
- “설명용 출력”은 실제 실행 결과의 보장이 아닙니다. 주소·인터페이스·카운터·시간은 자신의 환경과 비교합니다.
- 설정을 바꾸기 전에 현재 상태와 파일을 기록합니다. 변경은 한 번에 하나씩 하고, 실패하면 해당 장의 복구 절차를 적용합니다.

이 과정은 자신의 임시 VM에서 하는 실습입니다. 이 문서를 읽는 PC나 원격 운영 서버의 네트워크·방화벽을 바꾸는 과정이 아닙니다.

## 먼저 익힐 용어 {#starter-glossary}

| 용어 | 처음에는 이렇게 이해하세요 |
|---|---|
| 커널 / 사용자 공간 | 하드웨어·자원을 관리하는 핵심 / 그 위에서 실행되는 셸·프로그램 |
| NIC / 인터페이스 | 통신 장치 / OS가 그 장치를 다루는 이름과 설정 |
| MAC / IP | 같은 링크에서 프레임을 전달할 주소 / 네트워크 간 패킷 전달에 사용하는 주소 |
| 서브넷 / 프리픽스 | 주소의 앞부분을 공유하는 범위 / 그 앞부분의 비트 길이 |
| 게이트웨이 / 경로 | 다음으로 전달할 라우터 / 목적지에 따라 고르는 전달 규칙 |
| DHCP / DNS | 주소 등 네트워크 설정을 임대 / 이름에 대한 정보를 조회 |
| TCP / UDP / 포트 | 전송 방식 두 가지 / 같은 호스트의 통신 끝점을 구분하는 번호 |
| HTTP / SSH | 웹 요청·응답 프로토콜 / 인증된 암호화 원격 접속 프로토콜 |
| 소켓 / 리스너 | 프로그램의 통신 끝점 / 새 연결을 기다리는 소켓 |
| 방화벽 / SELinux | 트래픽 규칙 / 프로세스가 자원에 접근하는 것을 통제하는 정책 |
| NAT / CNI | 주소 변환 / 컨테이너 네트워크 설정을 위한 인터페이스와 구현 생태계 |

## 어디까지 배우는가 {#completion}

수료 확인은 “명령이 실행됐다”보다 구체적이어야 합니다.

- 자신의 배포판과 패키지 관리자를 설명하고 파일을 편집할 수 있습니다.
- 실습 NIC와 관리 NIC를 구분하고, IP·경로·DNS 설정이 어디서 관리되는지 찾습니다.
- SSH 호스트 키를 확인하고 키 로그인·유효 설정·복구 절차를 검증합니다.
- 필요한 클라이언트에만 실습 서비스 접근을 허용하고 변경한 규칙을 되돌립니다.
- DNS 실패, TCP 연결 실패, HTTP 오류를 관측 근거로 구분합니다.
- 소켓·패킷·애플리케이션 증거를 모아 [종합 실습 보고서](08-container-cloud-capstone.md#capstone-report)를 작성합니다.

이후 [프로토콜 심화](../../basics/06-network-fundamentals-part1.md), [커널 패킷 경로](../../kernel/02-network-stack.md), [Linux 진단 심화](../07-linux-network-diagnostics.md), [Kubernetes Service 실습](../../labs/core/03-services-networking-lab.md)으로 확장합니다. CNI 제품 설치부터 시작할 필요는 없습니다.

## 외부 과정 활용 {#further-study}

외부 강의를 수강해야 이 과정을 진행할 수 있는 것은 아닙니다. [Bootlin의 Linux networking 과정](https://bootlin.com/training/networking/)은 커널 네트워킹 쪽 후속 학습, [Linux Foundation networking 과정 모음](https://training.linuxfoundation.org/networking/)은 관심 분야별 후속 과정 탐색에 활용할 수 있습니다. 제공 범위·가격·일정은 해당 기관에서 확인합니다.

CentOS 7·예전 `ifconfig` 중심 자료를 볼 때는 개념과 실행 환경을 구분하세요. 여기서는 `ip`·`ss`와 위에 명시한 배포판을 기준으로 실습합니다.

**시작:** [1장 — Linux와 CLI](01-linux-cli.md)
