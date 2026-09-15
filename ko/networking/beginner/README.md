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

각 장의 완료 기준을 충족하고 퀴즈 해설을 자신의 말로 설명한 뒤 넘어가세요. 커널 튜닝과 CNI 구현 비교는 기본 실습을 마친 뒤 선택합니다.

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
