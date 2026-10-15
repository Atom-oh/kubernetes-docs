# 5. SSH로 원격 접속하기

> **지원 버전**: Ubuntu Server 24.04 LTS(기본), Rocky Linux 9(대안)
> **마지막 업데이트**: 2026년 9월 15일

[이전: DNS와 연결 진단](04-dns-connectivity.md) | [과정](README.md) | [퀴즈](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [다음: 호스트 보안](06-firewalls-host-security.md)

SSH는 다른 컴퓨터의 터미널을 암호화된 연결로 제공합니다. 암호화만으로 충분하지는 않습니다. 클라이언트는 서버가 누구인지 확인하고 서버는 접속 계정을 인증해야 합니다. 로그인 정책을 바꾸기 전에 이 두 신원을 따로 확인합니다.

## 사전 준비, 목표, 복구 경계

1–4장을 마칩니다. 클라이언트 `192.0.2.10/24`, 서버 `192.0.2.20/24`는 MAC으로 확인한 내부 전용 NIC를 사용하며 실습 DHCP·게이트웨이·업링크는 없습니다. 별도 NAT/DHCP 관리 NIC는 유지합니다. 일반 계정을 사용하고 **서버 하이퍼바이저 콘솔을 끝까지 열어 두세요**. 서버 sudo, 공개 키 설치에 사용할 일반 계정 비밀번호 또는 콘솔 접근, 패키지 다운로드를 위한 기존 관리 연결이 필요합니다.

SSH 도구 설치·확인, 호스트 지문 검증, 암호문구로 보호한 사용자 키 생성, 공개 부분만 설치, 두 번째 독립된 키 전용 로그인, 서버 유효 설정 확인, 정확한 복구를 배웁니다. 출력은 설명용이며 **실제 VM 실행 검증 기록이 아닙니다**. 모든 명령은 지정한 게스트에서만 실행하며 물리·문서 호스트에서 실행하지 않습니다. 예상 밖의 오류가 있으면 멈춥니다.

두 게스트에 `before-ssh-lesson` 스냅샷을 만들고 설치 전에 기존 SSH 리스너와 서비스·소켓 상태를 기록합니다. 패키지와 의존성 변경의 완전한 복구 수단은 스냅샷이며 패키지 제거는 정확한 역작업이 아닙니다. 예시를 맞추려고 기존 키나 설정 파일을 교체하지 마세요.

## 1. 클라이언트와 서버 확인하기

**SSH 클라이언트**는 접속할 때 실행하는 `ssh` 명령입니다. **SSH 서버**인 `sshd`는 보통 TCP 22에서 연결을 기다립니다. **호스트 키**는 서버 소유로 서버 신원을 증명하고, **사용자 키**는 사용자 소유로 계정 사용 권한을 증명합니다. 지문은 공개 키를 짧게 표현한 값으로 신뢰할 수 있는 경로를 통해 비교할 수 있습니다.

**두 게스트, 일반 사용자. 먼저 조회합니다.**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
command -v ssh
```

NIC MAC을 하이퍼바이저 기록과 맞추고 역할 주소를 확인합니다. 클라이언트의 `ip -4 route get 192.0.2.20`은 실습 NIC와 출발지 `.10`을 선택해야 합니다. 해석은 2장을 참고하세요.

**Ubuntu 서버, 일반 사용자. 상태를 기록한 뒤 없을 때만 설치합니다.**

```bash
dpkg-query -W openssh-server
systemctl status ssh.service ssh.socket --no-pager
```

없다면 `sudo apt update` 다음 `sudo apt install openssh-server`를 사용합니다. Ubuntu 24.04 설치 환경은 `ssh.socket` 소켓 활성화를 사용할 수 있으며 서비스 이름은 여전히 `ssh.service`입니다. 소켓을 끄지 말고 둘 다 조회하세요. 이번 장에서는 기존 리슨 주소·포트를 유지하므로 소켓 바인딩을 바꿀 필요가 없습니다.

**Rocky 서버, 일반 사용자. 상태를 기록한 뒤 없을 때만 설치합니다.**

```bash
rpm -q openssh-server
systemctl status sshd.service --no-pager
```

없다면 `sudo dnf install openssh-server`를 사용합니다. Ubuntu 클라이언트 도구 패키지는 `openssh-client`, Rocky는 `openssh-clients`입니다. 없다면 1장의 해당 배포판 패키지 관리 절차로 그 패키지만 설치합니다. 제안된 작업을 읽고 OpenSSH를 위해 외부 저장소를 추가하지 마세요.

**서버**에서 배포판을 확인한 뒤 서비스 변수 하나만 설정합니다.

```bash
# Ubuntu 서버에서만:
SSH_UNIT=ssh.service
```

```bash
# Rocky 서버에서만:
SSH_UNIT=sshd.service
```

**서버, 일반 사용자. 표시된 명령만 sudo 호출:**

```bash
sudo /usr/sbin/sshd -t
sudo systemctl start "$SSH_UNIT"
systemctl cat "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo ss -ltnp 'sport = :22'
```

`sshd -t`는 설정과 키의 기본 유효성을 검사하며 성공하면 보통 출력이 없습니다. 검증 오류 후에는 시작·reload하지 않습니다. `start`는 현재 실행 상태를 바꾸며 부팅 활성화는 바꾸지 않습니다. `systemctl cat`은 유닛과 override를 보여 줍니다. 이 절차는 기본 설정 경로를 전제로 하므로 사용자 `ExecStart`·환경 옵션에 `-f`나 `-o`가 있으면 이후 검증·유효 설정 조회에도 반영해 다른 설정을 검사하지 않도록 합니다. `0.0.0.0:22`·`[::]:22` 리스너는 실습 주소보다 넓게 연결을 받으며 출발지 제한이 아닙니다. 여기서 네트워크 바인딩을 바꾸면 관리 접근을 없앨 수 있습니다. 6장에서 출발지와 인터페이스로 실습 트래픽을 제한합니다.

현재 방화벽이 실습 연결을 막는다면 **6장의 맞는 방화벽 분기만** 수행해 `.10`에서 `.20` TCP 22를 허용한 다음 돌아오세요. 콘솔을 유지하고 방화벽을 끄지 않습니다. “Connection refused”는 흔히 리스너 부재·거절, 시간 초과는 필터링이나 경로 문제일 수 있습니다. 4장의 증거 수집 순서를 따릅니다.

## 2. 콘솔로 서버 호스트 키 검증하기

**서버 하이퍼바이저 콘솔, 일반 사용자가 sudo 호출:**

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

전체 `SHA256:...` 지문과 이것이 **ED25519 호스트 키**임을 기록합니다. 이 파일은 서버 공개 호스트 키이며 이후 만들 사용자 키가 아닙니다. 비공개 파일 `/etc/ssh/ssh_host_ed25519_key`는 출력하거나 복사하지 마세요. 이 경로는 일반적인 비-FIPS 게스트 기준입니다. Ed25519를 금지하는 암호 정책 환경은 보안 정책을 끄는 대신 승인된 알고리즘 경로를 사용해야 합니다.

**클라이언트, 일반 사용자:**

```bash
SSH_LAB_DIR=$(mktemp -d "$HOME/network-beginner-ssh.XXXXXX")
printf '%s\n' "$SSH_LAB_DIR"
read -r -p 'Normal account name on the server: ' SERVER_USER
```

디렉터리와 계정을 기록합니다. 생성 실패, 빈 경로, root 계정이면 멈춥니다. 개인 디렉터리에 전용 실습 키와 호스트 기록을 보관하므로 기존 클라이언트 `~/.ssh` 파일은 건드리지 않습니다.

**클라이언트, 일반 사용자:**

```bash
ssh -o HostKeyAlgorithms=ssh-ed25519 \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=ask \
  "$SERVER_USER@192.0.2.20"
```

첫 호스트 키 질문에서 **지문 전체**를 서버 콘솔과 비교합니다. 정확히 같을 때만 `yes`를 입력합니다. 다르면 VM·주소를 확인하고 멈춥니다. 호스트 검증을 끄거나 저장한 기록을 무작정 지우지 마세요. `ssh-keyscan`은 키를 수집할 수 있지만 그것만으로 키 제공자의 신원을 증명하지 못합니다.

비밀번호 로그인이 허용되면 **서버 계정 비밀번호**로 로그인하고 원격에서 `hostname`, `whoami`, `printf '%s\n' "$SSH_CONNECTION"`을 확인한 뒤 `exit`로 클라이언트에 돌아옵니다. `SSH_CONNECTION`은 클라이언트 IP·포트와 서버 IP·포트이며 실습 `.10`, `.20`이 보여야 합니다. 별도 하이퍼바이저 콘솔은 계속 유지합니다. 비밀번호가 이미 금지되었어도 인증 실패 전에 호스트 키 검증은 마칠 수 있습니다. 비밀번호를 켜지 말고 아래 콘솔 설치 대안을 사용하세요.

## 3. 사용자 키 만들고 서버 권한 준비하기

**클라이언트, 일반 사용자, 같은 셸:**

```bash
ssh-keygen -t ed25519 -a 64 -f "$SSH_LAB_DIR/id_ed25519" \
  -C "network-beginner-$(basename "$SSH_LAB_DIR")"
ssh-keygen -lf "$SSH_LAB_DIR/id_ed25519.pub"
ls -l "$SSH_LAB_DIR"
```

비어 있지 않은 암호문구를 두 번 입력합니다. 디스크의 개인 키를 암호화하는 값이며 서버 계정 비밀번호가 아닙니다. `-a 64`는 키 유도 작업 횟수 설정입니다. `id_ed25519`는 클라이언트에 남기고 `id_ed25519.pub`만 서버로 보냅니다. 고유 디렉터리는 기존 키 교체를 방지합니다. 예상하지 못한 덮어쓰기 질문에는 승인하지 말고 멈추세요.

설치 전에 `SERVER_USER`와 **같은 일반 서버 계정**의 복구 기록을 준비합니다.

**서버 콘솔, 해당 일반 계정으로 로그인한 상태:**

```bash
SERVER_NOTE=$(mktemp -d "$HOME/network-beginner-ssh-state.XXXXXX")
printf '%s\n' "$SERVER_NOTE"
stat -c '%a %U %n' "$HOME"
ls -ld "$HOME/.ssh" "$HOME/.ssh/authorized_keys"
```

디렉터리 생성이 실패하거나 출력 경로가 비어 있으면 멈춥니다. 새 경로와 원래 홈 권한을 기록합니다. 새 계정에서는 `.ssh`, `authorized_keys`의 “No such file”이 정상일 수 있으므로 무엇이 없었는지 기록하세요. 있다면 `stat -c '%a %U %n'`으로 숫자 권한을 기록하고 소유자를 확인합니다. 심볼릭 링크, 다른 소유자, 예상 밖의 ACL, 외부 관리 대상이라면 재귀 변경하지 말고 소유 관계부터 확인합니다.

`authorized_keys`가 이미 있다면 **서버 일반 사용자**로 `cp -p -- "$HOME/.ssh/authorized_keys" "$SERVER_NOTE/authorized_keys.before"`를 실행해 새 디렉터리에 백업합니다. `.ssh` 권한도 변경 전에 기록합니다. `.ssh`가 없을 때만 `mkdir -m 700 -- "$HOME/.ssh"`로 만드세요. 이 계정에 `chmod go-w "$HOME"`, `chmod 700 "$HOME/.ssh"`를 적용하되 원래 권한을 보관합니다. OpenSSH의 엄격한 검사는 안전하지 않은 소유권이나 그룹·전체 쓰기 가능한 경로를 거부합니다. 재귀 `chmod`를 쓰거나 다른 사람의 키를 이동하지 마세요.

## 4. 공개 키 설치와 키 전용 로그인 증명하기

**클라이언트, 일반 사용자:**

```bash
ssh-copy-id -i "$SSH_LAB_DIR/id_ed25519.pub" \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes \
  "$SERVER_USER@192.0.2.20"
```

`ssh-copy-id`는 기존 인증 수단으로 접속해 선택한 공개 키를 서버 계정의 `~/.ssh/authorized_keys`에 덧붙입니다. 개인 키를 복사하지 않습니다. 추가한 키 수를 읽으세요. 자신의 키 하나를 추가하거나 이미 설치되었다고 알려야 합니다. 강제 모드로 중복 추가하지 않습니다.

**비밀번호·초기 SSH 인증이 없는 경우의 콘솔 대안:** 클라이언트에서 `cat "$SSH_LAB_DIR/id_ed25519.pub"`로 공개 키만 표시합니다. 서버 콘솔에서 대상 사용자로 `nano "$HOME/.ssh/authorized_keys"`를 열고 기존 행을 보존하면서 **그 공개 키 전체를 한 줄로 덧붙입니다**. 저장 후 `ssh-keygen -lf "$HOME/.ssh/authorized_keys"`를 클라이언트 사용자 키 지문과 비교합니다. 2단계의 호스트 키 지문과 혼동하지 마세요.

**서버 콘솔, 대상 일반 사용자:**

```bash
chmod 600 "$HOME/.ssh/authorized_keys"
ls -ld "$HOME" "$HOME/.ssh"
ls -l "$HOME/.ssh/authorized_keys"
ssh-keygen -lf "$HOME/.ssh/authorized_keys"
```

대상 계정 소유, 개인 `.ssh` 권한, 기존 항목 사이의 새 공개 키 지문을 확인합니다. SELinux enforcing인 Rocky에서 표준 홈 경로의 라벨이 잘못되었다면 `sudo restorecon -v "$HOME/.ssh" "$HOME/.ssh/authorized_keys"`도 사용합니다. Unix 권한만으로 전체 정책을 설명할 수 없는 이유는 6장에서 배웁니다.

**클라이언트 콘솔 A, 일반 사용자. 세션을 열고 유지합니다.**

```bash
ssh -i "$SSH_LAB_DIR/id_ed25519" -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
  -o ControlMaster=no -o ControlPath=none \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes "$SERVER_USER@192.0.2.20"
```

개인 키 암호문구 질문은 정상입니다. 원격 계정 비밀번호 질문은 이 키 전용 시험에 포함되지 않습니다. `IdentitiesOnly`는 제시할 키를 제한하고 연결 공유를 끄면 기존 다중화 세션을 재사용하지 않고 새 인증을 시험할 수 있습니다.

그 **원격 서버 세션**에서 `whoami`, `printf '%s\n' "$SSH_CONNECTION"`을 실행하고 열어 둡니다. 이제 **클라이언트 콘솔 B**에서 `SSH_LAB_DIR`를 기록한 정확한 클라이언트 경로, `SERVER_USER`를 같은 계정으로 설정한 뒤 **위 키 전용 명령 전체**를 반복합니다. 계정과 `.10`→`.20` 연결을 다시 확인합니다. 두 번째 독립 로그인이 성공해야 이 단계를 통과합니다.

이미 **관리 NIC를 통한 SSH**를 사용한다면 서버 전체 비밀번호 인증을 끄기 전에 유지해야 할 모든 관리 계정·경로에서도 키 전용 로그인을 반복하세요. 기존 세션이 살아 있다는 사실만으로 충분하지 않습니다. 필요한 경로를 검증할 수 없다면 현재 인증 정책을 유지하고 준비를 마치세요. NIC IP가 그대로라고 로그인 접근도 유지되는 것은 아닙니다.

## 5. 보안 강화 전에 설정 우선순위 읽기

**서버 콘솔, 일반 사용자가 sudo 호출:**

```bash
sudo cat /etc/ssh/sshd_config
sudo ls -la /etc/ssh/sshd_config.d
sudo grep -RnsE '^[[:space:]]*(Include|Match|PasswordAuthentication|KbdInteractiveAuthentication|PermitRootLogin|PubkeyAuthentication|AuthenticationMethods|AuthorizedKeysFile)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d
```

`Include`가 가리키는 다른 경로까지 실제 파일을 읽습니다. `grep`은 도움 도구이지 완전한 설정 해석기가 아닙니다. OpenSSH는 보통 키워드의 **처음 얻은 값**을 사용합니다. Include는 등장한 위치에서 처리하고 glob 파일 이름은 사전순으로 읽습니다. 일치하는 `Match` 블록은 그 연결에 대해 전역 값을 바꿀 수 있으며 적용 가능한 Match 안의 같은 설정끼리도 순서가 중요합니다. 뒤쪽 `99-...conf`가 항상 덮어쓰는 방식은 아닙니다.

이 실습은 **전역 설정만 담는 새 drop-in**을 사용합니다. 주 파일의 전역 영역에서 `/etc/ssh/sshd_config.d/*.conf` Include가 활성화되어 있어야 합니다. 먼저 읽힌 값이 새 파일을 무력화하지 않는지 확인하세요. 실습 drop-in에 `Match` 블록을 넣거나 우선순위를 맞추려고 다른 include 파일을 바꾸지 않습니다. 현재 배치에서 의도대로 적용할 수 없다면 접속을 유지한 채 보안 강화 단계만 멈추고 설정 소유자·구조를 조사합니다.

**서버 콘솔. 이 셸에서 대상 계정을 다시 설정합니다.**

```bash
read -r -p 'Normal SSH account on this server: ' SERVER_USER
SSH_CASE="user=$SERVER_USER,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22"
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
```

`-T`는 유효 설정, `-C`는 Match 평가용 가상 연결 조건입니다. `host`는 호스트 이름 조건에서 사용할 접속 클라이언트이며 서버 이름이 아닙니다. 이 과정은 호스트 이름 기반 Match에 의존하지 않습니다. 자신의 설정에 있다면 sshd가 실제 평가하는 이름을 넣어야 합니다. `pubkeyauthentication`, `passwordauthentication`, `kbdinteractiveauthentication`, `permitrootlogin`, `authenticationmethods`, `authorizedkeysfile`을 확인하세요. 유효한 설정이라도 `AllowUsers`, `DenyUsers`, 그룹 제한, PAM, 계정 상태 때문에 거절될 수 있습니다.

추가하기 전에 유효 설정 기준값을 저장합니다.

```bash
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.before"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.before"
```

기존 관리 SSH 경로도 실제 출발지·로컬 주소와 계정으로 같은 기준값을 기록합니다. 관리 끝점에 예시 주소를 대신 넣지 마세요.

## 6. 소유한 정책 파일 하나를 추가하고 검증·reload·재시험하기

두 번째 키 전용 로그인과 필요한 관리 경로 시험이 성공한 뒤에만 진행합니다. 다음 설정은 유효 Match 조건에 따라 **서버 전체 인증**을 바꾸며 NIC 설정을 바꾸지 않습니다.

**서버 콘솔, 일반 사용자가 sudo 호출. 기존 파일이 있으면 생성을 거부합니다.**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/ssh/sshd_config.d/00-network-beginner.conf'
sudoedit /etc/ssh/sshd_config.d/00-network-beginner.conf
```

`set -C`는 기존 파일 덮어쓰기를 거부합니다. 실패하면 멈추세요. 이전 시도의 복구 기록 없이 편집·삭제하지 않습니다. 새로 만든 파일에 다음 **설정 텍스트**만 넣습니다.

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

`PasswordAuthentication no`만으로 비밀번호처럼 보이는 keyboard-interactive·PAM 인증까지 꺼지지는 않습니다. 일반 사용자 키 로그인과 sudo를 사용하면 root 직접 SSH 로그인을 피할 수 있습니다. PAM을 전역 비활성화하지 마세요.

**서버 콘솔, 일반 사용자가 sudo 호출:**

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22'
```

문법이 통과하고 의도한 연결에서 `pubkeyauthentication yes`, 비밀번호·keyboard-interactive 모두 `no`, `permitrootlogin no`일 때만 진행합니다. 필요한 관리 경로도 확인하세요. 먼저 읽은 설정이나 Match가 우선하면 **reload하지 않습니다**. 새 파일만 제거하고 복원된 설정을 검증한 뒤 우선순위를 조사합니다. 무작위로 파일 이름을 바꾸는 것은 해결책이 아닙니다.

**서버 콘솔, 일반 사용자가 sudo 호출:**

```bash
sudo systemctl reload "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo journalctl -u "$SSH_UNIT" -b -n 30 --no-pager
```

reload는 실행 중인 데몬에 설정을 다시 읽도록 요청합니다. 방화벽 reload나 소켓 바인딩 변경이 아닙니다. 콘솔과 원래 세션을 유지한 채 4단계의 **새 클라이언트 키 전용 로그인**을 다시 만들고 관리 SSH 경로도 확인합니다. 이미 인증된 세션이 계속 살아 있다고 새 로그인이 되는 것은 아닙니다.

## 완료 확인과 정확한 복구

성공 기준은 호스트 지문 검증, 암호문구로 보호한 전용 사용자 키, 올바른 소유권·권한, 보안 강화 전 두 번째 새 로그인, 관련 계정·경로의 예상 `-T -C` 값, 그리고 reload **후** 새 로그인 성공입니다. 인증 실패와 TCP 연결 거절이 왜 다른지 설명해 보세요.

**서버 콘솔**에서 정책 복원을 연습합니다.

```bash
sudo rm -i -- /etc/ssh/sshd_config.d/00-network-beginner.conf
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.restored"
diff -u "$SERVER_NOTE/effective.before" "$SERVER_NOTE/effective.restored"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.restored"
diff -u "$SERVER_NOTE/root-effective.before" "$SERVER_NOTE/root-effective.restored"
```

자신이 만든 파일만 삭제 승인합니다. diff 출력이 없으면 일반 계정의 유효 기준값과 같습니다. root와 기록한 관리 조건도 확인하세요. 다른 관리자·설정 관리자가 그사이 바꿨다면 오래된 디렉터리 전체를 복원하지 말고 차이를 조사합니다. 문법과 의도한 복원 값이 통과한 **뒤에만** `$SSH_UNIT`을 reload하고 새 로그인을 확인합니다. 강화 후 새 로그인이 실패한 경우에도 이 콘솔 절차로 복구합니다.

강화된 실습 구성을 유지하려면 같은 검증 절차로 소유한 drop-in을 다시 적용할 수 있습니다. 그렇지 않으면 다음 순서로 정리합니다.

1. **서버 대상 계정:** nano로 `~/.ssh/authorized_keys`를 열고 실습 주석과 기록한 사용자 키 지문으로 식별한 단 한 줄만 제거합니다. 다른 키는 보존합니다. 기존 파일이 있었다면 `"$SERVER_NOTE/authorized_keys.before"`와 비교하고 기록한 숫자 권한을 복원합니다. 원래 없었고 현재 비어 있다면 그 빈 파일만 지웁니다. `.ssh`도 자신이 만들었고 비어 있을 때만 `rmdir`로 지웁니다. 원래 있던 홈·`.ssh`의 기록한 권한을 복원합니다. 공유 계정에서는 중간 변경을 백업으로 덮어쓰지 말고 확인하세요.
2. **클라이언트:** 실습 세션을 닫고 공개 키 권한을 회수한 뒤 기록한 `SSH_LAB_DIR`의 `id_ed25519`, `id_ed25519.pub`, `known_hosts`만 `rm -i`로 지우고 `rmdir "$SSH_LAB_DIR"`를 실행합니다. 추가 파일이 있으면 정확한 이름을 확인하고 재귀 삭제하지 않습니다. 기존 클라이언트 SSH 파일은 교체하지 않았습니다.
3. **서버:** 확인을 마치면 `SERVER_NOTE`에서 실습이 만든 정확한 기준·백업 파일만 지우고 빈 디렉터리를 제거합니다. 별도 관리 기준 파일을 만들었다면 그 이름도 기록해 정확히 정리합니다.
4. 자신이 바꿨고 이후 장에 SSH가 필요하지 않을 때만 **기록한** 서비스·소켓 실행 상태를 복원합니다. Ubuntu 소켓이 원래 활성 상태였다면 유지하며, 서비스가 처음 inactive였다는 이유로 소켓을 끄지 않습니다. 새로 설치한 패키지는 이후 장을 위해 유지해도 됩니다. 완전한 패키지 복구에는 스냅샷을 사용하며 이후 게스트 작업도 사라집니다.

## 1차 참고 문서

2026년 9월 15일 확인:

- [Ubuntu Server OpenSSH](https://documentation.ubuntu.com/server/how-to/security/openssh-server/) — 설치, `ssh.service`, include 우선순위.
- [Ubuntu 24.04 릴리스 노트](https://discourse.ubuntu.com/t/noble-numbat-release-notes/39890) — OpenSSH 소켓 활성화와 소켓 설정 생성기.
- [Rocky Linux OpenSSH 키 설정](https://docs.rockylinux.org/9/guides/security/ssh_public_private_keys/) — Rocky OpenSSH 절차.
- [OpenSSH `ssh`](https://man.openbsd.org/ssh), [`ssh-keygen`](https://man.openbsd.org/ssh-keygen), [`sshd`](https://man.openbsd.org/sshd), [`sshd_config`](https://man.openbsd.org/sshd_config) — 신원, 키, 검증, Include·Match와 유효 설정.
- [Ubuntu 24.04 `ssh-copy-id`](https://manpages.ubuntu.com/manpages/noble/man1/ssh-copy-id.1.html) — 선택한 키 설치와 기존 키 처리.

[퀴즈](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [호스트 보안으로](06-firewalls-host-security.md)
