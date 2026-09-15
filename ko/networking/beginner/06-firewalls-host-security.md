# 6. 방화벽, SELinux, 범위를 제한한 SSH 보호

> **지원 버전**: Ubuntu Server 24.04 LTS(기본), Rocky Linux 9(대안)
> **마지막 업데이트**: 2026년 9월 15일

[이전: SSH](05-ssh-access.md) | [과정](README.md) | [퀴즈](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [다음: 모니터링](07-monitoring-performance.md)

애플리케이션이 대기 중이어도 방화벽이 연결을 거절할 수 있고, 연결을 받은 뒤에도 파일 읽기 권한이 없을 수 있습니다. 이번 장에서는 네트워크 정책, 프로세스·파일 정책, 반복 인증 실패에 대한 대응을 나누어 배웁니다.

## 사전 준비와 학습 목표

1–5장의 콘솔 접근 가능한 두 실습 게스트를 사용합니다. 클라이언트 `192.0.2.10/24`, 서버 `192.0.2.20/24`, DHCP·업링크 없는 내부 실습 NIC, 별도로 유지하는 NAT/DHCP 관리 NIC가 필요합니다. 5장에서 TCP 22가 막혀 이 장으로 왔다면 선택한 방화벽 분기만 마친 뒤 돌아갑니다. 그 분기를 위해 SSH 보안 강화 전체를 먼저 마칠 필요는 없습니다.

의도한 IPv4 클라이언트에서 서버 TCP **22와 8000**을 허용하고, 실제 적용 정책과 저장·실행 규칙을 확인하며, 자신의 변경만 복원합니다. 실습 파일 하나의 잘못된 SELinux 라벨을 복구하고 선택적으로 범위를 제한한 Fail2ban jail을 구성합니다. 변경은 서버 콘솔, 연결 시험은 클라이언트에서 수행합니다. 모든 명령·출력은 설명용이며 **실제 VM 실행 검증 결과가 아닙니다**.

서버 스냅샷 `before-host-security`를 만들고 기존 방화벽·실행 상태와 관리 SSH 경로를 기록합니다. 기존 관리 주체에 따라 **Ubuntu 경로의 UFW 또는 Rocky 경로의 firewalld 중 하나만** 선택하세요. 경쟁 관리자를 설치·활성화하거나 규칙을 flush하거나 시험을 통과하려고 보안 서비스를 끄지 않습니다. IPv4 실습 정책이며 IPv6 리스너 전체나 운영 환경 전체의 보안 정책은 아닙니다.

## 1. 방향과 관리 주체 이해하기

**인바운드**는 새 SSH 연결처럼 이 서버가 목적지인 트래픽입니다. **아웃바운드**는 패키지 저장소 요청처럼 이 서버가 생성한 트래픽입니다. **포워딩**은 이 서버를 지나 다른 호스트로 전달되는 트래픽입니다. 실습 서버는 라우터가 아니므로 포워딩·NAT·기본 경로 변경이 필요하지 않습니다.

상태 추적 방화벽은 대화를 기억하며 이미 성립한 연결의 응답을 흔히 허용합니다. 따라서 기존 SSH 세션이 살아 있다고 새 인바운드 세션까지 허용된 것은 아닙니다. 방화벽 허용 규칙이 대기 중인 프로그램을 만드는 것도 아닙니다.

**서버, 일반 사용자. 조회만 수행합니다.**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
ip -4 route
systemctl is-active ufw firewalld
```

없거나 inactive인 유닛 때문에 종료 상태가 0이 아니어도 반드시 장애는 아닙니다. UFW는 자체 `status`로 실제 활성화를 확인하며 systemd 유닛만으로 판단하지 않습니다. Docker, Kubernetes, 사용자 nftables·iptables 규칙, 다른 정책 관리자가 있다면 이 단순 정책이 전체를 소유한다고 가정하지 말고 깨끗한 실습 VM을 사용합니다.

**서버, 일반 사용자. 하이퍼바이저 MAC 대조 후 이름을 입력합니다.**

```bash
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
FW_NOTE=$(mktemp -d "$HOME/network-beginner-firewall.XXXXXX")
printf '%s\n' "$FW_NOTE"
```

디렉터리 생성 실패, 비었거나 같은 이름, MAC 불일치라면 멈춥니다. 값을 셸 밖에도 기록하세요. `.20/24`가 `LAB_IF`에 있음을 확인하고 관리 기준 상태를 저장합니다.

```bash
ip -4 -br address show dev "$MGMT_IF" > "$FW_NOTE/management.before"
ip -4 route > "$FW_NOTE/routes.before"
```

## 2A. Ubuntu: UFW

UFW가 관리하는 게스트에서만 이 분기를 사용합니다. 없다면 게스트 패키지 준비 절차로 `ufw`를 준비하고 원래 active·inactive 상태를 기록합니다.

**Ubuntu 서버, 일반 사용자가 sudo 호출:**

```bash
sudo ufw status verbose
sudo ufw status numbered
sudo ufw show added
sudo ufw show raw
sudo cat /etc/default/ufw
sudo ufw show added > "$FW_NOTE/ufw-added.before"
```

로컬 `/etc/ufw/before.rules`, `after.rules`와 해당 IPv6 파일의 수정 여부도 확인합니다. 먼저 적용되는 사용자 accept가 아래 user 규칙 제한을 우회할 수 있습니다. 이해한 기본 규칙과 충돌 없는 정책일 때만 진행하세요. 일반적인 `allow 22/tcp`는 목표보다 많은 출발지를 허용합니다. 좁은 allow 하나를 추가해도 기존 넓은 허용을 취소하지 못합니다.

UFW가 **inactive**이면 첫 활성화 경로는 예상한 기본 인바운드 거부·아웃바운드 허용 정책, 기본 DHCP·응답 처리, 그리고 **열린 방화벽에 의존하는 기존 인바운드 관리 서비스가 없음**을 전제로 합니다. 콘솔과 아웃바운드 NAT/DHCP 관리는 이 조건에 맞습니다. 기존 관리 SSH·인바운드 서비스를 유지해야 한다면 활성화 전에 이미 승인된 범위의 정책을 보존하세요. 넓은 관리 허용을 임의로 만들거나 콘솔 시험을 SSH 검증으로 여기지 않습니다. 조건이 불명확하면 정책을 해결하는 동안 UFW를 inactive로 둡니다.

SSH와 HTTP 클라이언트 허용을 각각 만든 뒤 같은 실습 끝점의 deny를 추가합니다. **SSH allow, HTTP allow, 실습 deny** 순서로 일반적인 넓은 user 규칙보다 앞에 둡니다. 세 규칙 모두 실습 NIC만 대상으로 합니다. 허용을 분리하면 [캡스톤 방화벽 실습](08-container-cloud-capstone.md#firewall-fault)에서 SSH 권한을 제거하지 않고 HTTP 권한만 제거할 수 있습니다.

**Ubuntu 서버, 일반 사용자가 sudo 호출:**

```bash
sudo ufw insert 1 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22 comment 'network-beginner-ssh'
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw insert 3 deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000 comment 'network-beginner-other'
sudo ufw show added
```

하나라도 실패하면 멈추고 아래 정확한 제거 방법으로 추가에 성공한 규칙만 되돌립니다. 같은 규칙이 원래 있었다면 중복 추가하지 말고 기존 소유 설정으로 기록하여 남겨 둡니다.

원래 inactive였고 위 활성화 조건을 만족했다면 **서버 콘솔**에서 `sudo ufw enable`을 실행합니다. `--force` 대신 경고를 읽으세요. 이미 active이면 규칙 변경이 즉시 적용됩니다.

**Ubuntu 서버, 일반 사용자가 sudo 호출:**

```bash
sudo ufw status numbered
sudo ufw status verbose
sudo ufw reload
sudo ufw status numbered
```

출발지 제한 allow 두 개가 같은 인터페이스·목적지 deny보다 앞에 위 순서대로 있고 reload 후에도 유지되어야 합니다. 이 방식의 UFW 규칙은 실행 상태와 저장 설정 모두에 적용됩니다. firewalld처럼 규칙별 runtime·`--permanent` 분리나 timeout을 사용하는 절차가 아닙니다. 번호는 현재 목록 위치일 뿐이므로 정리할 때 원래 규칙 내용을 사용합니다.

아래 공통 시험을 진행합니다. **이 규칙만 되돌리려면** Ubuntu 서버 콘솔에서 실행합니다.

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw delete deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000
sudo ufw show added
```

이 세 명령은 **이 장 전체 정리**의 역작업이며 HTTP만 고장 내는 실험에서 모두 실행할 명령이 아닙니다. 자신의 규칙만 승인합니다. 원래 inactive인 UFW를 이 실습 때문에 켰고 기준 상태로 복원하려면 저장 규칙을 제거한 **다음** `sudo ufw disable`을 실행합니다. 원래 active인 방화벽은 끄지 않습니다. `ufw-added.before`와 비교하세요. 7–8장까지 정책을 유지하려면 정리 상태로 두지 말고 세 규칙을 원래 순서로 다시 적용·검증합니다.

## 2B. Rocky: firewalld와 전용 실습 zone

firewalld가 기존 active 관리자인 경우에만 사용합니다. **zone**은 연결된 인터페이스·출발지에 적용할 정책 묶음입니다. NetworkManager 연결의 zone이 비어 있으면 firewalld 기본 zone을 사용하며 그곳은 이미 SSH를 넓게 허용할 수 있습니다. 여기에 좁은 허용만 추가해도 기존 허용을 제한하지 못합니다.

**Rocky 서버, 일반 사용자. 방화벽 조회는 sudo 호출:**

```bash
sudo firewall-cmd --state
sudo firewall-cmd --get-default-zone
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --list-all-zones
sudo firewall-cmd --permanent --list-all-zones
sudo firewall-cmd --list-all-policies
sudo firewall-cmd --permanent --list-all-policies
sudo firewall-cmd --direct --get-all-rules
sudo firewall-cmd --list-all-zones > "$FW_NOTE/firewalld-runtime.before"
sudo firewall-cmd --permanent --list-all-zones > "$FW_NOTE/firewalld-permanent.before"
nmcli -f NAME,UUID,TYPE,DEVICE connection show --active
```

두 NIC의 실제 zone과 기본 zone을 기록합니다. 출발지 연결, policy, rich rule, 사용자 direct rule도 확인합니다. direct 조회는 기존 방식의 상태 확인이며 새로 만들라는 권장이 아닙니다. 인터페이스 zone만으로 예상한 것과 다른 분류·허용이 생길 수 있습니다. 이 새 VM 절차는 경쟁하는 출발지 연결·policy가 없고 reload로 잃을 관련 없는 runtime 전용 변경도 없음을 전제로 합니다. 모르는 변경을 저장하려고 `--runtime-to-permanent`를 사용하지 마세요.

3장의 활성 **실습 전용** NetworkManager 프로필 UUID를 찾습니다. 관리·공유 프로필을 고르지 않습니다.

**Rocky 서버, 일반 사용자:**

```bash
read -r -p 'Active lab-only connection UUID: ' LAB_UUID
nmcli connection show uuid "$LAB_UUID"
LAB_OLD_ZONE=$(nmcli -g connection.zone connection show uuid "$LAB_UUID")
printf '%s\n' "$LAB_OLD_ZONE" > "$FW_NOTE/lab-zone.before"
```

프로필 NIC·MAC과 `.20/24`를 확인합니다. 기존 zone이 빈 값이어도 정상이며 그대로 기록합니다. runtime·permanent zone 목록 모두에서 `network-beginner`가 없는지 확인합니다. 이미 있다면 재사용하거나 다른 사람의 zone을 삭제하지 말고 멈춥니다.

**Rocky 서버, 일반 사용자가 sudo 호출:**

```bash
sudo firewall-cmd --permanent --new-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

이 절차는 새 zone을 영구 정의하고 불러온 뒤 runtime에서 사용합니다. reload는 permanent 정책으로 runtime을 교체하므로 관련 없는 runtime 변경을 먼저 해결해야 합니다. 아직 인터페이스는 이동하지 않았습니다.

정확한 rich rule 문자열 두 개를 설정합니다. IPv4, 출발지, 목적지, TCP 포트를 선택하며 zone을 `LAB_IF`에 연결하는 것이 인터페이스 경계가 됩니다.

**Rocky 서버, 일반 사용자:**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
```

**Rocky 서버, 일반 사용자가 sudo 호출. 10분 runtime 시험:**

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE22" --timeout=600
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000" --timeout=600
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone network-beginner
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
```

NetworkManager의 활성 연결에서 `connection.zone` 변경은 즉시 적용됩니다. 선택한 프로필의 방화벽 zone만 바꾸며 IP·DHCP·게이트웨이를 바꾸지 않습니다. `LAB_IF`는 새 빈 zone에 두 rich accept만 가지고, 관리 NIC는 원래 zone에 있어야 합니다. 새 zone에는 넓은 `ssh` 서비스나 trusted·ACCEPT target이 없습니다. 기본 처리는 허용하지 않은 새 TCP 연결을 거절하며 ICMP 같은 다른 프로토콜은 별도 정책 문제입니다.

시험 규칙은 runtime에만 있어야 합니다. 600초 후 만료되고 reload에도 사라지지만 zone·프로필 연결까지 없어지지는 않으므로 콘솔 복구가 중요합니다. `--timeout`과 `--permanent`를 함께 쓰지 마세요. 시험 시간 안에 공통 검증을 수행합니다.

정책을 유지하려면 **Rocky 서버에서 일반 사용자가 sudo 호출**:

```bash
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
sudo firewall-cmd --zone=network-beginner --list-rich-rules
sudo firewall-cmd --permanent --zone=network-beginner --list-rich-rules
```

그사이 관련 없는 runtime 변경이 없을 때만 진행합니다. reload 뒤 저장·실행 규칙 문자열이 같아야 하며 **새** SSH·HTTP 연결로 다시 시험합니다.

**복원**하려면 먼저 아래 선택 Fail2ban jail을 마치고 정지합니다. zone에 규칙을 추가할 수 있기 때문입니다. 이어서 Rocky 서버 콘솔에서 빈 값까지 포함해 기록한 프로필 zone을 복원합니다.

```bash
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone "$LAB_OLD_ZONE"
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
```

자신이 추가에 성공한 규칙 중 무엇이 남았는지 확인합니다. **Rocky 서버 콘솔, sudo:**

```bash
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

`yes`는 존재, `no`와 0이 아닌 종료 상태는 부재를 뜻합니다. 시험 timeout 이후처럼 없을 수 있습니다. **자신이 추가했고 현재 존재하는 규칙에 해당하는 제거만** 실행합니다.

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE8000"
```

마지막으로:

```bash
sudo firewall-cmd --permanent --delete-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

자신이 만든 이제 사용하지 않는 zone만 삭제하며 관련 없는 runtime 상태가 안전할 때만 reload합니다. 프로필 원래 zone, 기본 zone, 관리 zone·주소, 기준 정책을 비교하세요. 7–8장으로 계속한다면 검증한 저장 실습 zone을 유지합니다. 복원을 연습했다면 같은 시험·검증 단계로 다시 구성합니다.

## 3. 클라이언트에서 검증하고 증거 범위 이해하기

5장처럼 클라이언트에서 **새 키 전용 SSH 연결**을 만듭니다. 기존 세션은 새 규칙을 시험하지 못합니다. TCP 8000은 앞선 HTTP 장의 `python3`를 준비하고 다른 서비스가 포트를 소유하지 않는지 확인합니다.

**서버 콘솔 A, 일반 사용자:**

```bash
WEB_DIR=$(mktemp -d "$HOME/network-beginner-fw-web.XXXXXX")
printf '%s\n' "$WEB_DIR"
```

경로를 기록하고 생성 실패·빈 값이면 멈춥니다. 다음으로:

```bash
printf 'firewall lesson\n' > "$WEB_DIR/index.html"
timeout 120 python3 -m http.server 8000 --bind 192.0.2.20 --directory "$WEB_DIR"
```

최대 2분 동안 실습 IPv4에 바인딩하여 이 디렉터리만 제공합니다. 비밀이나 심볼릭 링크를 넣지 마세요. **서버 콘솔 B**의 `sudo ss -ltnp 'sport = :8000'`에 `.20:8000`이 보여야 합니다.

**클라이언트, 일반 사용자:**

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
```

HTTP 200과 본문 `firewall lesson`을 기대합니다. 실패했다고 넓은 허용을 추가하지 말고 리스너, 경로, zone·인터페이스, 출발지, 로그 순으로 확인하세요. 의도한 출발지 제한은 설정을 검토해 확인합니다. 허용 클라이언트의 성공이 **다른 모든 출발지의 거부를 시험한 것은 아닙니다**. localhost·서버 자기 접속은 외부 비허용 클라이언트 시험이 아닙니다.

시간 만료(상태 124는 정상)나 Ctrl+C로 서버가 끝난 뒤 **서버 콘솔 A, 일반 사용자**로 `rm -i -- "$WEB_DIR/index.html"`, `rmdir -- "$WEB_DIR"`를 실행합니다. 관리 주소·경로를 `FW_NOTE`와 비교하고 필요한 새 관리 SSH 로그인도 확인합니다. DHCP 임대 시간은 독립적으로 갱신될 수 있습니다.

## 4. Rocky SELinux: 전체 정책 대신 라벨 복구하기

SELinux는 Unix 소유자·권한 및 방화벽과 별도의 프로세스·자원 정책입니다. **Enforcing**은 정책을 집행하고 거부를 기록하며, **permissive**는 거부될 작업을 기록하되 집행하지 않습니다. **Disabled**에서는 SELinux 집행이 없습니다. 실습은 모드를 바꾸지 않습니다. Ubuntu는 흔히 AppArmor를 사용하므로 대안 분기를 따라 하려고 SELinux를 설치하거나 전환하지 마세요.

**Rocky 서버, 일반 사용자. 감사 로그 조회만 sudo:**

```bash
getenforce
sestatus
ls -Z "$HOME"
sudo ausearch -m AVC,USER_AVC -ts recent -i
```

SELinux가 활성화된 준비된 게스트에서 사용합니다. disabled라면 실행 중 전체 재라벨링을 시도하지 말고 올바르게 준비한 스냅샷으로 돌아갑니다. `ausearch`에는 `audit` 도구가 필요합니다. 검색 결과가 없다는 것은 그 시간 범위의 보관 기록 중 일치 항목이 없다는 뜻이지, 정책이 어떤 접근도 거부하지 않는다는 증거가 아닙니다.

AVC 기록에는 시도한 권한, 프로세스, 대상, 출발 문맥(`scontext`), 대상 문맥(`tcontext`)이 있습니다. 실행 파일·경로·시간을 함께 읽으세요. SELinux 문맥은 흔히 `user:role:type:level` 형태이고 targeted policy에서 **type**이 중요합니다. 모든 거부를 무조건 `audit2allow`에 넣지 마세요. 잘못된 라벨이나 애플리케이션 경로가 원인일 수 있습니다.

**Rocky 서버, 일반 사용자. 개인 실습 파일 하나 생성:**

```bash
SEL_DIR=$(mktemp -d "$HOME/network-beginner-selinux.XXXXXX")
printf '%s\n' "$SEL_DIR"
```

실패하면 멈추고 정확한 경로를 기록한 뒤 진행합니다.

```bash
touch "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
matchpathcon "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

정책 조회가 이 경로의 예상 문맥을 알려 줍니다. 먼저 기준 상태를 맞추며 모든 홈 구조가 같은 type이라고 외우지 않습니다. 이제 파일에 다른 존재하는 type을 의도적으로 지정한 뒤 복구합니다.

**Rocky 서버, 일반 사용자. 표시된 명령만 sudo 호출:**

```bash
sudo chcon -t httpd_sys_content_t "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
sudo restorecon -n -v "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

`chcon`은 파일 라벨을 바꾸며 영구 파일 문맥 규칙을 만들지 않습니다. `restorecon -n`은 변경 없이 미리 보여 주고 `restorecon`은 정책의 경로 라벨을 복원합니다. 마지막 검증에서 정책과 같아야 합니다. 상위 디렉터리가 개인 공간이므로 웹 배포가 아니라 라벨 실습입니다. 제한된 애플리케이션이 접근하도록 만들지 않았으므로 AVC 생성을 보장하지 않습니다.

영구 사용자 경로에는 정확한 범위의 `semanage fcontext` 매핑 후 `restorecon`이 필요할 수 있지만 여기서는 필요하지 않습니다. **Rocky 서버 일반 사용자**의 정리는 `rm -i -- "$SEL_DIR/probe.txt"`, `rmdir -- "$SEL_DIR"`입니다. `chcon` 직후 중단됐다면 같은 대상의 `restorecon`을 먼저 수행합니다. 파일 하나 때문에 SELinux 전역 비활성화나 전체 파일 시스템 재라벨링을 하지 마세요.

## 5. 선택 패키지와 Rocky 9 EPEL·CRB {#epel-prerequisites}

방화벽·SELinux 핵심 실습은 Fail2ban·`iftop` 없이도 완료할 수 있습니다. 이 절은 7장의 선택적 `iftop` 경로가 참고할 Rocky 준비도 설명합니다. 패키지는 관리 연결을 통해 **버려도 되는 게스트 안에서만** 설치합니다.

**Ubuntu 서버**는 먼저 `apt-cache policy fail2ban python3-systemd`를 조회합니다. 구성된 Ubuntu 저장소에 후보가 있으면 `sudo apt update`, `sudo apt install fail2ban python3-systemd`로 Fail2ban과 저널 backend를 준비합니다. 후보가 없다면 임의 다운로드 출처 대신 공식 저장소 구성 요소 설정을 확인하세요.

**Rocky 9**의 EPEL은 Fedora의 Enterprise Linux 추가 저장소이고 CRB는 의존성을 제공합니다. EPEL Next, 다른 EL 주 버전, 패키지 서명 검증 비활성화를 사용할 이유가 아닙니다.

**Rocky 게스트, 일반 사용자. 원래 저장소·패키지 상태 기록:**

```bash
dnf repolist --all
rpm -q epel-release dnf-plugins-core fail2ban-server python3-systemd
```

CRB·EPEL이 원래 활성 상태였는지, 어떤 패키지가 있었는지 기록하고 `before-optional-packages` 스냅샷을 만듭니다. 이어서 **Rocky 게스트에서 일반 사용자가 sudo 호출**:

```bash
sudo dnf install dnf-plugins-core
sudo dnf config-manager --set-enabled crb
sudo dnf install epel-release
dnf repolist --enabled
dnf info fail2ban-server python3-systemd iftop
```

EPEL이 **9**에 맞고 예상한 저장소·서명을 사용하며 게스트 아키텍처에 후보가 있는지 확인합니다. Fail2ban은 `sudo dnf install fail2ban-server python3-systemd`를 사용하고 7장의 선택 도구는 그 장에서 `iftop`만 설치합니다. 제안된 작업을 읽고 의존성을 해결하지 못하면 멈춥니다. 패키지 버전은 바뀌므로 특정 빌드를 가정하지 않습니다.

CRB·EPEL이 원래 있었거나 다른 소프트웨어에 필요하면 끄지 마세요. 잠깐의 실험이었다면 의존하는 모든 장을 마친 뒤 `before-optional-packages`로 복원합니다. 패키지·저장소의 정확한 복구 수단이며 저장소만 끈다고 설치된 패키지가 되돌아오지는 않습니다.

## 6. 선택 Fail2ban jail과 실습 범위 action

Fail2ban은 **filter**로 인증 실패 로그를 읽고 `findtime` 안의 이벤트를 세어 `maxretry`에 이르면 **action**을 실행합니다. **jail**은 이 설정을 묶습니다. 약한 키를 고치거나 기본 방화벽 정책을 대신하거나 모든 분산·저속 공격을 막지는 못합니다. filter·backend가 틀리면 실행 중이어도 아무것도 탐지하지 못할 수 있습니다.

선택 설정은 **기존 사용자 jail이 없는 새 Fail2ban 설치**를 전제로 합니다. 이미 사용 중이라면 소유자·설정부터 확인하고 다른 작업의 보호를 중단하지 않습니다. 원래 서비스 실행·활성화 상태를 기록하세요. 새 설치가 자동 시작되었다면 콘솔에서 `sudo systemctl stop fail2ban`으로 이 새 서비스만 준비 중 정지합니다. `/etc/fail2ban/jail.conf`, `jail.d`, 설치된 action을 검토하고 배포된 `jail.conf`는 수정하지 않습니다.

선택한 관리자용 새 action 파일 **하나**를 만들며 덮어쓰기를 거부합니다.

**서버, 일반 사용자가 sudo 호출:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/action.d/network-beginner.conf'
sudoedit /etc/fail2ban/action.d/network-beginner.conf
```

**UFW만** 사용한다면 새 파일에 다음 INI를 넣고 `REPLACE_WITH_LAB_NIC`를 MAC으로 검증한 서버 NIC 이름으로 바꿉니다. 자리표시자를 남기지 마세요.

```ini
[Definition]
actionstart =
actionstop =
actioncheck = LC_ALL=C ufw status | grep -q 'Status: active'
actionban = ufw insert 1 deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22 comment 'network-beginner-ban'
actionunban = ufw delete deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22
```

**firewalld만** 사용한다면 대신 다음 내용을 넣습니다. 실습 zone은 계속 실습 NIC에만 연결되어 있어야 합니다.

```ini
[Definition]
actionstart =
actionstop =
actioncheck = firewall-cmd --zone=network-beginner --list-all
actionban = firewall-cmd --zone=network-beginner --add-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
actionunban = firewall-cmd --zone=network-beginner --remove-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
```

탐지한 출발지를 **실습 인터페이스·zone, 목적지 `.20`, TCP 22**에 대해서만 제한합니다. 관리 주소나 TCP 8000에서는 차단하지 않습니다. UFW의 앞쪽 삽입과 firewalld의 음수 priority가 임시 거부를 실습 허용보다 먼저 적용합니다. Fail2ban이 `bantime` 후 규칙을 제거하므로 이 선택 실험 중에는 하위 방화벽을 reload하지 않습니다. 이 타이머는 UFW 규칙 자체가 아니라 Fail2ban에 속합니다. 데몬이 실패했다면 만료됐다고 가정하지 말고 남은 실습 차단을 확인한 뒤 정확한 `actionunban` 내용으로 그 규칙만 제거하세요.

**서버, 일반 사용자가 sudo 호출. jail 파일을 새로 만듭니다.**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/jail.d/99-network-beginner.local'
sudoedit /etc/fail2ban/jail.d/99-network-beginner.local
```

다음은 **Ubuntu**용 INI입니다. **Rocky**에서는 `journalmatch`의 `ssh.service`만 `sshd.service`로 바꿉니다.

```ini
[sshd]
enabled = false

[network-beginner-sshd]
enabled = true
filter = sshd
backend = systemd
journalmatch = _SYSTEMD_UNIT=ssh.service
usedns = no
ignoreip = 127.0.0.0/8 ::/0
port = 22
maxretry = 3
findtime = 60
bantime = 60
action = network-beginner
```

`[sshd]` 설정은 이 **새 설치**에서 패키지 기본 SSH jail이 두 번째 넓은 action을 적용하지 않도록 합니다. 다른 jail이 활성화되지 않았는지 확인하며 기존 사용자 보호를 끄는 데 사용하지 않습니다. 이름 붙인 jail은 `sshd` filter와 새 action을 명시합니다. `backend=systemd`는 저널을 읽으므로 `logpath`를 추가하지 **않습니다**. `journalmatch`는 실제 로그 유닛 메타데이터와 일치해야 합니다. `::/0`은 IPv4 전용 설명에서 IPv6를 의도적으로 제외한 것이며 운영 환경 보호 정책은 아닙니다.

**서버, 일반 사용자가 sudo 호출. 시작 전에 검증합니다.**

```bash
sudo journalctl -u ssh.service -b -n 10 -o verbose --no-pager
sudo fail2ban-client -t
sudo fail2ban-client -d
```

Rocky는 `-u sshd.service`를 사용합니다. 실제 인증 관련 기록의 `_SYSTEMD_UNIT`을 확인하세요. 맞는 기록이 없다면 backend 수집 범위는 아직 입증되지 않은 것입니다. `-t`는 설정 시험, `-d`는 집행을 시작하지 않고 해석한 설정을 출력합니다. jail 이름, journal backend·match, 예상한 action 하나, 제한된 시간, 경쟁하는 다른 enabled jail이 없음을 확인합니다.

**서버, 일반 사용자가 sudo 호출:**

```bash
sudo systemctl start fail2ban
sudo fail2ban-client status
sudo fail2ban-client status network-beginner-sshd
sudo fail2ban-client get network-beginner-sshd journalmatch
sudo fail2ban-client get network-beginner-sshd actions
sudo fail2ban-client get network-beginner-sshd action network-beginner actionban
sudo journalctl -u fail2ban -b -n 30 --no-pager
```

의도한 jail, 해석된 범위 제한 action, 시작 오류 없음을 확인합니다. 실패·차단 0건은 정상입니다. **무차별 대입 반복이나 의도적 자기 차단을 실행하지 마세요.** 이 확인은 설정·시작을 검증하며 실제 공격 탐지·집행까지 입증하지 않습니다. 서비스 메타데이터 오류, Python journal 지원 부재, filter 불일치, action 실행 오류를 해결하기 전 보호가 작동한다고 주장하면 안 됩니다.

실수로 차단된 목록에 알려진 실습 클라이언트가 있다면 **서버 콘솔에서 sudo**:

```bash
sudo fail2ban-client set network-beginner-sshd unbanip 192.0.2.10
sudo fail2ban-client status network-beginner-sshd
```

IP 하나만 정확히 해제합니다. 해당 UFW·rich rule이 없고 새 SSH 연결이 되는지 확인합니다. 기존 세션만으로 충분하지 않습니다. 모든 차단이나 방화벽 규칙을 flush하지 마세요.

정리할 때는 **이 jail**에 실제로 나열된 주소만 하나씩 정확히 unban하고 action 제거를 확인합니다. 이어서 `sudo fail2ban-client stop network-beginner-sshd`를 실행하고, 서비스가 원래 inactive·새 설치였을 때만 정지합니다. 자신이 만든 두 파일만 `sudo rm -i -- /etc/fail2ban/jail.d/99-network-beginner.local /etc/fail2ban/action.d/network-beginner.conf`로 지웁니다. jail과 실습 차단이 없음을 확인합니다. **firewalld zone 삭제 전에** 이 정리를 수행하세요. 기록한 서비스·활성화 상태를 복원하며 선택 설치 전체 복구는 스냅샷을 사용합니다.

## 완료 확인과 다음 장 연결

선택한 관리자, 올바른 인터페이스·zone, 정확한 `.10`→`.20` TCP 22·8000 규칙, 새 허용 SSH·HTTP 연결, 유지된 관리 경로와 역작업을 보여 줄 수 있어야 합니다. UFW 저장 규칙과 firewalld runtime·permanent의 차이, 올바른 파일 권한과 SELinux type의 차이를 설명하세요. 실제 추가 검증 증거가 없다면 선택 Fail2ban은 “설정 확인”으로 보고합니다.

[7장](07-monitoring-performance.md)을 위해 검증한 출발지 제한 **저장 방화벽 정책**을 유지합니다. 제거를 연습했다면 먼저 다시 적용·검증하세요. HTTP 프로세스, 의도적으로 잘못된 라벨, 임시 Fail2ban jail은 다음 장에 필요하지 않습니다.

기록이 더 이상 필요하지 않으면 `FW_NOTE`에서 자신이 만든 정확한 기준 파일(`management.before`, `routes.before`, 선택한 분기의 명시된 기준 파일)만 지우고 빈 디렉터리를 `rmdir`로 제거합니다. 기록한 프로필·방화벽 상태는 최종 과정 정리에서 복원합니다. 이름이 익숙하다는 이유만으로 모르는 zone·규칙을 지우지 마세요.

## 1차 참고 문서

2026년 9월 15일 확인:

- [Ubuntu UFW 매뉴얼](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html) — 방향, 인터페이스, 순서, 저장, 정확한 삭제.
- [firewalld CLI](https://firewalld.org/documentation/man-pages/firewall-cmd.html), [rich language](https://firewalld.org/documentation/man-pages/firewalld.richlanguage.html), [zone](https://firewalld.org/documentation/zone/connections-interfaces-and-sources.html) — timeout, reload, 출발지·목적지 규칙, 분류.
- [NetworkManager 연결 설정](https://networkmanager.dev/docs/api/latest/settings-connection.html) — 활성 연결의 즉시 zone 변경과 빈 값·기본값.
- [Rocky Linux 9 SELinux 안내](https://docs.rockylinux.org/9/guides/security/learning_selinux/), [SELinux 라벨 도구](https://github.com/SELinuxProject/selinux/tree/main/policycoreutils/setfiles) — AVC 진단과 대상 한정 문맥 복원.
- [Fedora EPEL 시작](https://docs.fedoraproject.org/en-US/epel/getting-started/), [Rocky 저장소 문서](https://wiki.rockylinux.org/rocky/repo/), [EPEL Fail2ban 패키지](https://packages.fedoraproject.org/pkgs/fail2ban/fail2ban-server/) — 선택 패키지 출처와 준비.
- [Fail2ban jail 설정](https://github.com/fail2ban/fail2ban/blob/master/config/jail.conf), [systemd backend](https://github.com/fail2ban/fail2ban/blob/master/fail2ban/server/filtersystemd.py), [client 매뉴얼](https://manpages.ubuntu.com/manpages/noble/man1/fail2ban-client.1.html) — filter·backend·action 구분, 설정 시험, 상태, 개별 unban.

[퀴즈](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [모니터링으로](07-monitoring-performance.md)
