# 03. 재부팅 후에도 유지되는 네트워크 설정

> **지원 버전**: Ubuntu Server 24.04 LTS(기본), Rocky Linux 9(대안)
> **마지막 업데이트**: 2026년 9월 15일

`ip address add`로 주소를 추가하면 현재 커널의 설정이 바뀝니다. 다음 부팅에도 같은 주소를 쓰라는 지시가 저장되는 것은 아닙니다. 이 장에서는 네트워크 설정을 소유한 도구에 영구 설정을 전달하고, 저장된 내용과 실제 VM의 상태를 비교합니다.

## 준비 사항과 학습 목표

[주소와 인터페이스](02-addressing-interfaces.md)를 마치고 [과정 실습 환경](README.md)을 준비하세요. 폐기 가능한 VM 두 대와 하이퍼바이저 콘솔을 사용합니다. 두 VM 모두 Ubuntu여도 됩니다. Rocky를 동시에 배울 필요는 없습니다.

| 항목 | 필요한 상태 |
|---|---|
| 클라이언트 실습 NIC | 이 장을 마치면 `192.0.2.10/24` |
| 서버 실습 NIC | 이 장을 마치면 `192.0.2.20/24` |
| 실습망 | 같은 내부 가상 네트워크, DHCP 서버·라우터·업링크 없음 |
| 관리 NIC | 별도의 기존 NAT/DHCP 연결, 주소·경로·DNS 설정 유지 |
| NIC 식별 | 하이퍼바이저에서 각 MAC을 기록하고 게스트에서 대조 |
| 접근과 도구 | 게스트 콘솔, sudo 권한, 편집기, `ip`, 설치된 네트워크 관리 도구 |

명령은 **지정한 VM 안에서** 실행합니다. VM을 실행하는 워크스테이션에서는 실행하지 마세요. 대안 절차를 따라 하려고 두 번째 네트워크 관리자를 설치하거나 활성화하지 않습니다. 필요한 도구가 없다면 실습 환경 준비로 돌아가세요.

학습을 마치면 설정 소유자를 식별하고, 정적 주소를 저장하며, DHCP·게이트웨이·DNS 설정이 필요한 조건을 설명할 수 있습니다. 재부팅 검증과 실습 변경만 되돌리는 방법도 익힙니다. 먼저 VM 스냅샷을 만들고 콘솔을 열어 두세요. 각 단계를 따로 실행하고 오류가 나면 원인을 확인한 뒤 진행합니다.

## 1. NIC와 설정 소유자 확인

**각 VM**에서 설정을 변경하지 않고 현재 상태를 읽습니다.

```bash
cat /etc/os-release
ip -br link
ip -br address
ip -4 route show
ip -6 route show default
systemctl is-active systemd-networkd NetworkManager
```

`ip -br link`는 인터페이스 이름과 MAC 주소를 함께 표시합니다. 목록의 첫 NIC가 아니라 하이퍼바이저의 **실습용 MAC**과 일치하는 NIC를 찾으세요. NAT/DHCP NIC에는 보통 관리용 기본 경로가 있습니다. 관리 NIC의 식별 정보와 현재 경로·DNS 설정도 기록합니다. 두 서비스 중 하나가 없거나 비활성 상태이면 `systemctl is-active`가 0이 아닌 종료 코드를 반환할 수 있으며, 그것만으로 장애는 아닙니다.

이 장의 `REPLACE_WITH_LAB_NIC`를 방금 확인한 이름으로 바꾸세요. 변수는 현재 셸에만 존재하므로 독립적인 블록에는 다시 선언합니다. `HOME`, `PATH` 같은 셸 변수에 실습값을 대입하지 마세요.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
```

두 번째 명령은 현재 커널 주소를 보여 주지만 다음 부팅에 누가 그 주소를 다시 만들지는 알려 주지 않습니다. 02장의 임시 주소는 해당 장의 대상 한정 정리 절차로 먼저 제거하세요. 새 실습 NIC에는 임시 IPv4 주소가 남아 있지 않아야 합니다. 기존 프로필이 소유한 주소를 예상과 다르다는 이유만으로 삭제하지 않습니다.

다음 증거로 소유자를 판단합니다.

| 관측한 증거 | 설정 소유자와 진행 경로 |
|---|---|
| Ubuntu Netplan YAML이 `networkd`를 선택하고 `networkctl status`에 대응 네트워크 파일 표시 | A 경로 |
| Rocky NetworkManager에 관리 중인 장치와 프로필 표시 | B 경로 |
| Netplan이 `NetworkManager` 선택 | Netplan도 상위 설정 원본이므로 YAML과 생성된 프로필 확인 |
| cloud-init, 프로비저닝 도구, 직접 작성한 `.network` 파일, 와일드카드 또는 여러 정의가 같은 NIC 소유 | 중복 정의를 추가하기 전에 소유권 정리, 원본이 불명확하면 깨끗한 과정용 VM 사용 |

Netplan은 YAML을 백엔드 설정으로 변환합니다. `systemd-networkd`와 NetworkManager는 장치에 설정을 적용하며, `nmcli`와 `nmtui`는 둘 다 NetworkManager를 조작합니다. 서비스가 실행 중이라고 모든 NIC를 소유하는 것은 아닙니다. 이 장의 Ubuntu Server 경로가 모든 Ubuntu 이미지·Ubuntu Desktop·Debian 설치의 기본값이라는 뜻은 아닙니다.

### A 경로 소유권 확인: Ubuntu Netplan/networkd

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
sudo netplan get
sudo ls -l /etc/netplan
networkctl status "$LAB_IF"
sudo ls -l /etc/systemd/network /run/systemd/network
resolvectl status
```

`netplan get`은 병합된 설정입니다. 목록에 실제로 있는 이름으로 `sudo less /etc/netplan/ACTUAL_FILE.yaml`을 실행해 원본 YAML도 읽으세요. `/lib/netplan`, `/run/netplan` 디렉터리가 있다면 함께 확인합니다. `networkctl status`에는 일치하는 네트워크 파일이 표시될 수 있습니다. `resolvectl status`로 기존 DNS 서버와 연결도 기록합니다.

Netplan은 이름이 다른 YAML 파일을 사전식 순서로 병합합니다. 나중 파일의 단일 값은 앞의 값을 바꾸지만, 목록은 **이어 붙을 수 있습니다**. 뒤 파일에 빈 주소·DNS 목록을 쓰는 것이 앞 목록을 지우는 일반적인 방법은 아닙니다. 이름이 다른 정의가 같은 NIC에 일치할 수도 있습니다. [Netplan 파일 병합 규칙](https://netplan.readthedocs.io/en/stable/netplan-generate/)을 참고하세요.

아래 절차는 직접 작성한 networkd 파일의 와일드카드까지 포함하여 실습 NIC에 **기존 영구 정의가 없는 경우**입니다. 설치 프로그램이 이미 정의했다면 파일의 소유자를 확인하고 백업한 뒤, 그 파일의 정확한 실습 NIC 항목을 의도적으로 편집하는 경로를 선택해야 합니다. 아래 문서 전체로 설치 프로그램 파일을 덮어쓰거나 두 정의를 공존시키지 마세요. cloud-init 주석은 프로비저닝 원본을 확인하라는 단서이며, cloud-init 전체를 끄라는 뜻이 아닙니다. 첫 실습에서는 OS 초기 설정 후 내부 NIC를 추가하면 이런 충돌을 줄일 수 있습니다.

### B 경로 소유권 확인: Rocky NetworkManager

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
nmcli --version
nmcli device status
nmcli -f GENERAL,IP4,IP6,CONNECTIONS device show "$LAB_IF"
nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
```

`device`는 NIC, `connection`은 저장된 프로필입니다. 이름이 같을 필요는 없습니다. `GENERAL.CON-UUID`는 현재 활성 프로필이 있을 때 그 UUID를 보여 줍니다. `CONNECTIONS`에서 비활성 프로필을 포함한 호환 프로필을 찾을 수 있습니다. 이전 실습 프로필의 UUID와 활성 여부를 기록하고 관리용 프로필은 유지하세요.

각 호환 프로필을 `nmcli connection show uuid ACTUAL_UUID`로 읽습니다. `connection.interface-name`, `802-3-ethernet.mac-address`, `connection.autoconnect`, `connection.autoconnect-priority`를 기록하세요. 장치·MAC 제한이 비어 있으면 하나의 Ethernet 프로필이 여러 NIC에 적용될 수 있습니다. 실습을 간단하게 만들려고 이런 공유 프로필을 수정하지 마세요.

Rocky 9는 NetworkManager keyfile을 지원하며 이전 ifcfg 프로필이 남아 있을 수도 있습니다. 인터페이스 이름만으로 저장 형식을 단정하지 않습니다. [Rocky 9 버전의 안내](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)는 해당 릴리스를 다루며, [버전 없는 안내](https://docs.rockylinux.org/guides/network/basic_network_configuration/)는 현재 Rocky 10을 설명합니다.

## 2A. Netplan/networkd로 주소 저장

A 경로의 소유권 확인을 마친 경우에만 진행합니다. 클라이언트와 서버 각각에 **자신의 MAC과 주소**를 사용해 반복하세요.

### 백업하고 실습 소유 파일 하나 만들기

각 **Ubuntu VM**에서 새로운 복구 디렉터리를 만듭니다. 이미 존재한다면 이전 시도를 확인하고 멈추세요. 기존 백업을 대체하지 않습니다.

```bash
sudo mkdir -m 700 /root/network-beginner-03
sudo cp -a /etc/netplan /root/network-beginner-03/netplan-before
sudo sh -c 'umask 077; set -C; : > /etc/netplan/90-beginner-lab.yaml'
sudoedit /etc/netplan/90-beginner-lab.yaml
```

`cp -a`는 원본 파일과 권한을 보존합니다. 짧은 `sh` 명령은 root만 접근할 빈 파일을 만들며, `set -C`는 기존 파일 덮어쓰기를 거부합니다. `sudoedit`은 설정된 편집기로 편집용 복사본을 엽니다.

아래 **완전한 YAML 문서**를 붙여 넣습니다. 탭 대신 공백을 쓰세요. 예시 MAC을 클라이언트의 실제 실습 MAC으로 바꿉니다. 서버에서는 서버의 실습 MAC과 `192.0.2.20/24`를 사용합니다.

```yaml
network:
  version: 2
  ethernets:
    beginner-lab:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:10"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 192.0.2.10/24
      optional: true
```

| 설정 | 이 실습에서의 의미 |
|---|---|
| `version: 2` | Netplan 설정 스키마 버전 |
| `beginner-lab` | 정의 ID, NIC 이름 변경 없이 MAC으로 장치 선택 |
| 장치 수준 `renderer` | 전역 renderer를 바꾸지 않고 이 정의에 networkd 선택 |
| `dhcp4: false` | DHCP 서버 없는 망에서 DHCP 요청하지 않음 |
| IPv6·link-local 설정 | 이 NIC의 격리 실습을 IPv4로 한정, 호스트 전체의 IPv6 비활성화 권장은 아님 |
| `addresses` | `/24` 주소 하나, 직접 연결된 서브넷에는 게이트웨이 불필요 |
| `optional: true` | networkd가 부팅을 이 NIC 때문에 기다리게 하지 않음, 설정 자체는 수행 |

`routes`, `nameservers`를 의도적으로 넣지 않았습니다. 두 VM 모두 라우터나 DNS 서버가 아닙니다. `192.0.2.1`을 게이트웨이로 추측해 입력해도 라우터가 생기지 않습니다. 관리 NIC는 원래 설정을 유지합니다.

### 검증하고 시험 적용한 뒤 관측하기

```bash
sudo chmod 600 /etc/netplan/90-beginner-lab.yaml
sudo netplan generate
sudo netplan get
```

`chmod 600`은 root만 읽고 쓰도록 합니다. `generate`는 이미 부팅된 일반 세션에서 설정을 검사하고 백엔드 파일을 생성하지만 적용하지 않습니다. 성공하면 보통 출력이 없습니다. 병합 결과에서 의도한 실습 주소·MAC 하나, 실습 게이트웨이·DNS 추가 없음, 기존 관리 정의 유지를 확인하세요. YAML 문법이 맞아도 MAC이나 주소가 틀릴 수 있습니다.

**VM 콘솔**에서 시험 적용합니다.

```bash
sudo netplan try --timeout 120
```

확인 프롬프트가 기다리는 동안 두 번째 콘솔·로그인에서 확인합니다.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route show default
ip -6 route show default
networkctl status "$LAB_IF"
resolvectl status
```

기대 결과는 `192.0.2.0/24` 직접 연결 경로, 정확한 `.10` 또는 `.20` 주소, 실습 NIC가 추가한 기본 경로·DNS 없음, 기존 관리 경로 접근 가능입니다. 이를 확인한 뒤에만 시험 설정을 승인하세요. 상대 ping 성공은 두 VM을 모두 설정한 다음 확인합니다.

`try`, `apply`는 새 파일 하나만이 아니라 **병합된 설정 전체**에 작용하며 다른 장치의 네트워크도 다시 적용할 수 있습니다. 관리 정의를 편집하지 않았어도 콘솔은 필요합니다. `try`는 미승인 설정을 되돌리려 하지만 [공식 문서에 롤백 버그가 명시되어 있습니다](https://netplan.readthedocs.io/en/stable/netplan-try/). 시간 만료나 Ctrl+C만으로 **복구됐다고 판단하지 말고** 실행 상태와 디스크 파일을 확인하세요.

### Netplan 복구와 원복

정상 설정은 다음 장을 위해 유지합니다. 이번 변경을 취소하려면 **콘솔**에서 진행하세요.

1. `/etc/netplan/90-beginner-lab.yaml`이 이번에 만든 파일인지 확인합니다.
2. 그 파일만 Netplan 입력 디렉터리 밖으로 옮깁니다.
3. 남아 있는 이전 설정을 생성·적용합니다.

```bash
sudo mv -i /etc/netplan/90-beginner-lab.yaml /root/network-beginner-03/90-beginner-lab.failed.yaml
sudo netplan generate
sudo netplan apply
```

`mv -i`는 이전 실패 복사본을 대체하기 전에 묻습니다. `generate`가 실패하면 `apply` 전에 멈추세요. 새 NIC 경로 대신 기존 소유 파일을 편집했다면 `netplan-before`의 대응 파일과 비교하여 **정확히 편집한 파일만** 복원한 뒤 생성·적용합니다. 디렉터리 전체를 교체하지 마세요.

주소·경로·관리 접근을 다시 확인합니다. 더 이상 관리되지 않는 실습 NIC에 실행 중 설정이 남을 수 있습니다. **이번 장의 정확한 주소가 아직 보이는 경우에만** 그 주소를 삭제하세요.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_CIDR='192.0.2.10/24'
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

서버에서는 `LAB_CIDR='192.0.2.20/24'`로 바꿉니다. 최초 기록에서 실습 NIC가 관리적으로 down이었다면 같은 셸에서 `sudo ip link set dev "$LAB_IF" down`으로 되돌립니다. 관리 경로를 삭제하거나 인터페이스 설정을 일괄 비우지 마세요. 최종 복구 수단으로 재부팅하기 전에도 디스크 설정이 복원됐는지 확인합니다. 소유권이나 복구 상태가 불명확하면 실습 전 VM 스냅샷을 복원하세요.

## 2B. NetworkManager로 주소 저장

각 **Rocky VM**에서 B 경로의 조사 결과를 사용합니다. 게스트마다 `beginner-lab-static`이라는 새 프로필을 만듭니다. 이미 그 이름이 있다면 중복 생성하지 말고 이전 시도를 확인하세요.

호환되는 이전 프로필은 복구용으로 보존합니다. 재부팅 후 선택을 예측할 수 있도록, 원래 값을 기록한 다음 **실습 NIC에만 묶인 프로필**의 자동 연결만 끕니다.

```bash
OLD_LAB_UUID='REPLACE_WITH_CONFIRMED_LAB_PROFILE_UUID'
nmcli -f connection connection show uuid "$OLD_LAB_UUID"
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect no
```

이전 실습 프로필이 없으면 이 블록을 건너뜁니다. 다른 실습 전용 후보가 있으면 각각 반복하되 현재 활성 연결은 그대로 둡니다. 후보가 공유·미지정 프로필이거나 소유권이 불명확하면 먼저 그 문제를 해결하세요. `DEVICE=--`는 비활성이라는 뜻이지 영향이 없다는 뜻이 아닙니다.

새 프로필을 **자동 활성화 없이 저장**합니다.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_MAC='REPLACE_WITH_LAB_MAC'
LAB_CIDR='192.0.2.10/24'
sudo nmcli connection add type ethernet con-name beginner-lab-static \
  ifname "$LAB_IF" 802-3-ethernet.mac-address "$LAB_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses "$LAB_CIDR" \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv6.method disabled
nmcli -f connection,802-3-ethernet,ipv4,ipv6 connection show id beginner-lab-static
```

서버는 `.20/24`를 사용합니다. `manual`에는 주소·접두사가 필요합니다. 이름과 MAC 제한은 이 프로필을 적용할 장치를 한정합니다. `mac-address`는 영구 MAC과 비교하며 MAC 자체를 변경하지 않습니다. 빈 게이트웨이·DNS와 `never-default yes`는 실습망을 로컬로 유지합니다. IPv6는 이 프로필에서만 비활성화합니다. `connection add`는 기본적으로 영구 저장하지만 **저장됨과 활성화됨은 다릅니다**.

출력의 새 UUID를 기록합니다. 그 프로필을 정확히 활성화하고 실행 상태를 확인하세요.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli --wait 30 connection up uuid "$LAB_UUID" ifname "$LAB_IF"
nmcli -f GENERAL,IP4,IP6 device show "$LAB_IF"
ip -4 route show
```

활성화하면 이 NIC의 이전 활성 프로필을 대체할 수 있습니다. 의도한 주소·직접 연결 경로가 있고 실습 게이트웨이·DNS가 없어야 합니다. 관리 경로를 최초 기록과 비교하세요. 활성화 실패 시 `journalctl -u NetworkManager -b -n 50 --no-pager`를 읽습니다. 시간 초과는 저장 프로필까지 없어졌다는 뜻이 아닙니다.

관측이 정상이면 다음 부팅의 자동 연결을 활성화합니다.

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect yes
nmcli -f connection.id,connection.uuid,connection.autoconnect connection show uuid "$LAB_UUID"
```

### nmtui에서 같은 프로필 다루기

`nmtui`가 이미 있다면 **기존 실습 전용 프로필**을 엽니다.

```bash
sudo nmtui edit beginner-lab-static
```

Tab으로 이동하고 화살표로 선택하며 Space로 체크하고 Enter로 확정합니다. 프로필 이름·장치를 확인하고 IPv4를 **Manual**로 선택하여 펼친 뒤 `.10/24` 또는 `.20/24` 주소 하나를 확인하세요. Gateway·DNS servers·search domains는 비웁니다. Routes에 **Never use this network for default route**가 있으면 선택합니다. IPv6는 **Disabled**, 검증 후에는 자동 연결을 활성화한 상태로 둡니다.

보기만 했다면 **Cancel**, 의도한 편집을 저장하려면 **OK**를 선택합니다. 저장 대상은 `nmcli`와 같은 NetworkManager 프로필이며 별도의 설정 계층이 아닙니다. 저장 후 `nmcli connection show`로 확인하고 앞 블록의 기록된 UUID를 활성화하세요. 메뉴는 패키지 버전에 따라 다를 수 있습니다. 없는 속성은 `nmcli`로 설정하고 확인합니다. 관리 연결을 일반적인 비활성화·재활성화 메뉴로 조작하지 마세요.

### NetworkManager 복구와 원복

**콘솔**에서 기록한 새 UUID를 확인하고 자신이 만든 프로필만 제거합니다. 프로필 생성 자체가 실패했다면 새 프로필 삭제 블록은 건너뛰되, 변경한 이전 프로필의 자동 연결 값은 반드시 복원하세요.

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
nmcli -f connection,ipv4 connection show uuid "$LAB_UUID"
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect no
sudo nmcli connection down uuid "$LAB_UUID"
sudo nmcli connection delete uuid "$LAB_UUID"
```

UUID를 확인했다면 `down`의 “이미 비활성” 결과는 허용할 수 있지만 다른 오류는 조사해야 합니다. 연결이 내려가면 다른 호환 프로필이 자동 활성화될 수도 있으므로 장치를 다시 확인하세요.

이전 실습 프로필이 있었다면 변경한 모든 자동 연결 값을 기록대로 복원합니다. **실습 전에 활성 상태였을 때만** 다시 활성화하세요.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
OLD_LAB_UUID='REPLACE_WITH_PREVIOUS_LAB_PROFILE_UUID'
OLD_AUTOCONNECT='yes'
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect "$OLD_AUTOCONNECT"
sudo nmcli --wait 30 connection up uuid "$OLD_LAB_UUID" ifname "$LAB_IF"
```

`yes` 또는 `no`는 추측하지 말고 기록한 값을 사용합니다. 이전 프로필이 비활성이었다면 `up` 행은 생략하세요. 이전 프로필이 없으면 복원할 프로필도 없습니다. 실습 주소가 없어졌는지 확인합니다. 필요하면 실습 링크의 원래 up/down 상태를 복원하고 관리 주소·경로·DNS를 최초 기록과 비교하세요. Ethernet 프로필 전체 삭제나 전역 네트워크 재시작은 하지 않습니다.

## 3. DHCP·게이트웨이·DNS가 필요한 조건

정적 주소는 관리자가 정한 주소를 사용합니다. DHCP는 실제 DHCP 서버에서 임대를 요청하며 경로와 DNS도 받을 수 있습니다. 이 과정의 내부망에서 DHCP를 켜도 임대해 줄 서버는 없습니다. DNS 서버는 이름에 답하고, 게이트웨이는 직접 연결된 망 밖으로 패킷을 전달합니다. 한 장치가 두 역할을 할 수 있지만 IP가 `.1`로 끝난다는 이유로 어느 역할도 자동 부여되지 않습니다.

다음은 **선택적인 응용 예제이며 과정의 두 VM을 바꾸는 절차가 아닙니다**. 하이퍼바이저 MAC으로 식별한 별도의 폐기 가능한 연습 VM·NIC, 콘솔, 충돌 없는 소유권, 실제 DHCP 가상망 또는 관리자가 지정한 라우팅망이 필요합니다. 두 과정 VM의 관리 NIC를 대신 넣지 마세요.

### 실제 DHCP 서버가 있는 망의 동적 주소

DHCP 연습망의 여분 **networkd 소유 NIC**에는 다음과 같은 완전한 Netplan 정의를 사용할 수 있습니다.

```yaml
network:
  version: 2
  ethernets:
    practice-dhcp:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:30"
      dhcp4: true
      dhcp4-overrides:
        use-routes: false
        use-dns: false
        use-domains: false
      dhcp6: false
      accept-ra: false
      link-local: []
      optional: true
```

예시 MAC을 여분 NIC의 MAC으로 바꿉니다. 이 override는 주소를 받되 DHCP 경로·DNS·검색 도메인은 받지 않아 연습 VM의 기존 관리 경로를 유지합니다. 직접 연결된 서브넷 경로는 생깁니다. 의도적으로 선택한 주 업링크라면 관리자가 DHCP 경로·DNS를 받도록 할 수 있지만 이 과정에서는 기존 업링크를 바꾸지 않습니다.

`90-beginner-dhcp.yaml`처럼 별도 이름으로 새 파일·백업 절차를 수행하고 권한 600, `generate`, 병합 결과 확인, `try`를 거칩니다. `networkctl status`, `ip address`에서 임대를 확인하세요. 없다면 링크 연결, 가상망 선택, DHCP 서비스·주소 풀을 조사합니다. 원복은 새 파일만 제거하고 이전 설정을 적용하며, A 경로처럼 남은 실습 주소도 확인합니다.

기존 정의가 없는 **NetworkManager 소유 여분 NIC**의 대응 프로필은 다음과 같습니다.

```bash
PRACTICE_IF='REPLACE_WITH_SPARE_NIC'
PRACTICE_MAC='REPLACE_WITH_SPARE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-dhcp \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no ipv4.method auto \
  ipv4.never-default yes ipv4.ignore-auto-routes yes ipv4.ignore-auto-dns yes \
  ipv6.method disabled
sudo nmcli --wait 60 connection up id beginner-practice-dhcp ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4,DHCP4 device show "$PRACTICE_IF"
```

사용하지 않는 프로필 이름이어야 합니다. UUID를 기록하고 B 경로의 UUID 원복으로 이 새 프로필만 삭제합니다. `autoconnect no`이므로 설정은 저장되지만 재부팅 후에는 수동 활성화가 필요합니다. 기존 **연습 전용 프로필**을 정적 주소에서 DHCP로 바꾼다면, 한 번의 `connection modify`에서 `ipv4.method auto`와 함께 `ipv4.addresses`, `ipv4.gateway`, `ipv4.routes`, `ipv4.dns`, `ipv4.dns-search`를 비워야 합니다. 그렇지 않으면 이전 정적 값이 DHCP와 함께 남을 수 있습니다. 먼저 값을 기록하고 취소할 때 그 값을 복원하세요.

### 라우팅 연습망에서 게이트웨이·DNS 영구 저장

과정의 두 VM이 아닌 **별도 연습 VM**에 관리자가 `10.77.0.10/24`, 실제 같은 링크의 라우터 `10.77.0.1`, `training.example`에 답하는 접근 가능한 resolver `10.77.0.53`을 지정했다고 가정합니다. 연습 NIC를 명시적인 기본 업링크로 선택하며 **경쟁하는 관리 기본 경로가 없어야** 합니다. 하이퍼바이저 콘솔을 사용하세요. 관리자가 이 예시 값들이 실제 연습망과 일치하는지 확인해야 실행할 수 있습니다.

Netplan/networkd의 완전한 정의는 다음과 같습니다.

```yaml
network:
  version: 2
  ethernets:
    practice-uplink:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:40"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 10.77.0.10/24
      routes:
        - to: default
          via: 10.77.0.1
      nameservers:
        addresses:
          - 10.77.0.53
        search:
          - training.example
```

`to: default`는 더 구체적인 경로가 없는 목적지의 경로이고, `via`는 같은 링크에 있는 라우터 주소입니다. `nameservers.addresses`는 resolver, `search`는 `web` 같은 짧은 이름을 `web.training.example`로 확장할 수 있는 검색 접미사입니다. DNS 레코드를 만들지는 않습니다. 별도 백업한 소유 파일을 사용하고 MAC을 바꾼 뒤 A 경로의 권한·검증·시험·복구 절차를 반복하세요.

NetworkManager에서 동일한 조건의 새 연습 NIC라면 다음과 같습니다.

```bash
PRACTICE_IF='REPLACE_WITH_PRACTICE_UPLINK'
PRACTICE_MAC='REPLACE_WITH_PRACTICE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-routed \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses 10.77.0.10/24 \
  ipv4.gateway 10.77.0.1 ipv4.never-default no \
  ipv4.dns 10.77.0.53 ipv4.dns-search training.example \
  ipv6.method disabled
sudo nmcli --wait 30 connection up id beginner-practice-routed ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4 device show "$PRACTICE_IF"
```

활성화 전에 새 프로필을 확인하고 UUID를 기록합니다. 부팅 활성화가 필요하다면 검증 성공 후에만 autoconnect를 켜세요. 원복은 B 경로처럼 UUID로 해당 프로필만 제거합니다. 두 백엔드 모두 `ip route get 10.77.0.53`, 기본 경로, 관리자가 제공한 DNS 레코드를 확인합니다. resolved가 실행 중이면 `resolvectl status`, 아니면 NetworkManager의 활성 DNS와 `/etc/resolv.conf`를 읽으세요. 생성된 `resolv.conf`를 직접 편집하거나 일시적인 `resolvectl dns` 명령을 영구 프로필 변경으로 취급하지 않습니다.

## 4. 재부팅 후 과정 실습망 검증

두 과정 VM의 정적 설정으로 돌아옵니다. 작업을 저장하고 콘솔에서 `sudo reboot`로 **폐기 가능한 게스트**를 각각 재부팅하세요. 로그인한 뒤 MAC으로 NIC를 다시 확인합니다. 셸 변수는 재부팅 후 남지 않습니다.

**클라이언트**에서 실행합니다.

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
ping -n -c 3 -W 2 192.0.2.20
```

**서버**에서는 `.20/24`를 확인하고 `ip -4 route get 192.0.2.10`, `ping -n -c 3 -W 2 192.0.2.10`을 실행합니다. 경로 조회는 `via` 없이 실습 NIC와 자신의 실습 출발지 주소를 선택해야 합니다. 관리 기본 경로는 남아 있을 수 있으며 원래 설정과 일치해야 합니다. DHCP 임대 세부 정보는 정상 갱신될 수 있습니다.

| 관측 | 먼저 조사할 대상 |
|---|---|
| 재부팅 후 주소 없음 | 틀린 MAC, 미저장 파일·프로필, 자동 연결 비활성, 경쟁 소유자 |
| 실습 주소·DNS·기본 경로가 추가로 존재 | YAML 목록 병합, 다른 일치 정의·프로필, 임시 설정 잔존 |
| `NO-CARRIER` | 하이퍼바이저 케이블·어댑터 상태와 내부망 연결 |
| 경로는 맞지만 ping 응답 없음 | 상대 주소, 같은 내부망 여부, 이웃 탐색, ICMP 정책; 04장에서 계속 조사 |
| 관리 접근 변화 | 콘솔에서 해당 원복 절차 사용, 경로 일괄 삭제 금지 |

## 완료 확인

- 두 VM의 실습·관리 NIC를 MAC 증거로 구분합니다.
- 실습 NIC를 소유한 파일·프로필과 저장 상태·활성 상태의 차이를 설명합니다.
- `.10/24`, `.20/24`와 상대의 직접 연결 경로가 재부팅 후 유지됨을 확인합니다.
- 실습 NIC에 게이트웨이·DNS가 추가되지 않았고 관리 설정이 보존됐음을 확인합니다.
- 상대 ping 결과를 기록하고 실패하면 게이트웨이를 추측하지 않고 조사합니다.
- 원복할 정확한 새 파일·프로필과 복원할 이전 상태를 지정합니다.
- 선택적 DHCP·라우팅 예제에 왜 별도 준비된 망이 필요한지 설명합니다.

다음 장을 위해 정상 정적 주소를 유지하세요. 과정이 끝날 때까지 백업 기록도 보존합니다.

## 공식 자료와 더 읽기

- [Ubuntu Server 네트워크 설정](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)
- [Netplan 예제](https://netplan.readthedocs.io/en/stable/examples/), [YAML 참조](https://netplan.readthedocs.io/en/stable/netplan-yaml/), [파일 권한](https://netplan.readthedocs.io/en/stable/security/)
- [Netplan generate와 병합](https://netplan.readthedocs.io/en/stable/netplan-generate/), [Netplan try와 복구 주의점](https://netplan.readthedocs.io/en/stable/netplan-try/)
- [NetworkManager nmcli 예제](https://www.networkmanager.dev/docs/api/latest/nmcli-examples.html), [nmcli 매뉴얼](https://www.networkmanager.dev/docs/api/latest/nmcli.html), [프로필 속성](https://www.networkmanager.dev/docs/api/latest/nm-settings-nmcli.html), [nmtui](https://www.networkmanager.dev/docs/api/latest/nmtui.html)
- [Rocky Linux 9 네트워크 설정](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)

[이전: 주소와 인터페이스](02-addressing-interfaces.md) · [퀴즈](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) · [다음: DNS와 연결 진단](04-dns-connectivity.md)
