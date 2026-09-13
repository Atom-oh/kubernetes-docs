# Linux 기초 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 45분
> **마지막 업데이트**: 2026년 9월 11일

## 학습 목표
- Linux 프로세스 관리 명령어를 실습합니다
- Linux 네임스페이스의 격리 효과를 직접 확인합니다
- cgroup을 통한 리소스 제한을 이해합니다
- 파일 권한과 소유자 관리를 실습합니다

## 사전 요구 사항
- [ ] 실습3을 위한 Bash·systemd·cgroup v2가 있는 유지보수 중인 Linux VM
- [ ] 도구: coreutils, procps/procps-ng, util-linux, iproute2/iproute, Python3
- [ ] sudo 권한
- [ ] [Linux 기초](../../basics/01-linux-basics.md) 학습 완료

변수를 유지할 수 있도록 같은 Bash 터미널에서 순서대로 실행하세요. sudo namespace·cgroup 실습은 격리된 VM에서 수행합니다. 컨테이너·제한된 환경에서는 sudo가 있어도 필요한 capability가 없을 수 있습니다. 아래 출력은 설명용이며 이번 감사에서 권한이 필요한 실습을 실행하지 않았습니다.

---

## 실습 1: 프로세스 관리

### 목표
프로세스 조회, 백그라운드 실행, 시그널 전송을 실습합니다.

### 단계

**Step 1.1: 현재 실행 중인 프로세스 확인**
```bash
# 현재 PID namespace에서 보이는 프로세스의 스냅샷
ps aux | head -20

# 트리 형태로 프로세스 관계 확인
ps auxf | head -30
```

**Step 1.2: 백그라운드 프로세스 실행**
```bash
sleep 300 &
LINUX_LAB_SLEEP_PID=$!
printf 'Lab child PID: %s\n' "$LINUX_LAB_SLEEP_PID"
jobs -l
```

**Step 1.3: 프로세스에 시그널 전송**
```bash
# Run in the same Bash session as Step 1.2.
: "${LINUX_LAB_SLEEP_PID:?Run Step 1.2 first}"
if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
  kill -TERM "$LINUX_LAB_SLEEP_PID"
fi
if wait "$LINUX_LAB_SLEEP_PID"; then
  LINUX_LAB_EXIT_STATUS=0
else
  LINUX_LAB_EXIT_STATUS=$?
fi
printf 'Lab child exit status: %s\n' "$LINUX_LAB_EXIT_STATUS"
unset LINUX_LAB_SLEEP_PID
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `kill -l`로 사용 가능한 시그널 목록을 확인할 수 있습니다
- `kill -9 PID`는 SIGKILL로 강제 종료합니다
- `$!`로 캡처한 PID를 사용하세요. 이름 패턴은 관계없는 작업과도 일치할 수 있습니다.
</details>

### 검증
```bash
printf 'Recorded lab child exit status: %s\n' "${LINUX_LAB_EXIT_STATUS:?Complete Step 1.3}"
jobs -l
```

---

## 실습 2: Linux 네임스페이스 격리

### 목표
네임스페이스를 생성하여 프로세스와 네트워크의 격리를 확인합니다.

### 단계

**Step 2.1: PID 네임스페이스 격리 확인**
```bash
# 새로운 PID 네임스페이스에서 bash 실행
sudo unshare --mount --pid --fork --mount-proc bash -c '
echo "새 네임스페이스 안의 PID 목록:"
ps aux
echo "현재 프로세스 PID: $$"
'
```

예상 결과:
```
새 네임스페이스 안의 PID 목록:
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0   ...   ...  ...      S    ...    0:00 bash -c ...
root         2  0.0  0.0   ...   ...  ...      R    ...    0:00 ps aux
현재 프로세스 PID: 1
```

**Step 2.2: 네트워크 네임스페이스 격리**
```bash
LINUX_LAB_NETNS="k8s-docs-netns-${UID}-$$"
(
  # Install cleanup only after creating this namespace successfully.
  sudo ip netns add "$LINUX_LAB_NETNS" || exit 1
  trap 'sudo ip netns delete "$LINUX_LAB_NETNS"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  sudo ip netns exec "$LINUX_LAB_NETNS" ip addr
)
```

<details>
<summary>힌트가 필요하신가요?</summary>

- 네트워크 네임스페이스 내부에서는 호스트의 네트워크 인터페이스가 보이지 않습니다
- `lo` (루프백) 인터페이스만 존재하며, 기본적으로 DOWN 상태입니다
- 이것이 컨테이너의 네트워크 격리 원리입니다
</details>

### 검증
```bash
if LINUX_LAB_NS_LIST=$(sudo ip netns list); then
  if printf '%s\n' "$LINUX_LAB_NS_LIST" | awk '{print $1}' | grep -Fxq -- "$LINUX_LAB_NETNS"; then
    printf 'Named handle still exists: %s\n' "$LINUX_LAB_NETNS"
  else
    printf 'Named handle is not listed: %s\n' "$LINUX_LAB_NETNS"
  fi
else
  printf 'Could not verify namespace handles\n' >&2
fi
```

---

netns 이름을 지워도 프로세스를 죽이거나 프로세스·파일 디스크립터가 참조하는 namespace를 즉시 없애지는 않습니다. 이 예제는 `ip addr` 종료 이후 이름을 정리합니다.

## 실습 3: cgroup 리소스 제한

### 목표
cgroup을 사용하여 프로세스의 메모리 사용을 제한합니다.

### 단계

**Step 3.1: cgroup 정보 확인**
```bash
# cgroup2fs identifies a cgroup v2 mount.
stat -fc '%T' /sys/fs/cgroup
cat /proc/self/cgroup
if [ -r /sys/fs/cgroup/cgroup.controllers ]; then
  cat /sys/fs/cgroup/cgroup.controllers
else
  printf 'Controllers are not readable here; inspect the mount and permissions\n'
fi
```

**Step 3.2: 메모리 사용량 확인**
```bash
# 시스템 메모리 정보
free -h

# 특정 프로세스의 메모리 사용량
ps aux --sort=-%mem | head -10
```

**Step 3.3: 임시 서비스에 실제 제한 적용**

systemd와 cgroup v2 memory controller를 사용할 수 있는 VM에서 자동 이름의 임시 서비스에128MiB 메모리 상한과 swap 허용량0을 설정합니다. 의도적으로 OOM을 일으키지 않고16MiB를 접근한 뒤 `--wait --collect`로 완료를 기다리고 임시 unit을 정리합니다. 상위 cgroup 제한이 더 엄격할 수 있습니다.

```bash
sudo systemd-run --wait --collect --pipe \
  --property=MemoryMax=128M --property=MemorySwapMax=0 \
  python3 -c '
from pathlib import Path
entry = next(line for line in Path("/proc/self/cgroup").read_text().splitlines()
             if line.startswith("0::"))
group = Path("/sys/fs/cgroup") / entry.split(":", 2)[2].lstrip("/")
print("Configured memory.max:", (group / "memory.max").read_text().strip())
data = bytearray(16 * 1024 * 1024)
for offset in range(0, len(data), 4096):
    data[offset] = 1
print("Touched allocation bytes:", len(data))
'
```

128M의 `memory.max` 설정값은134217728바이트이고 할당 크기는16777216바이트입니다. 설정·산술상의 예상값이며 이번 감사의 실측 결과가 아닙니다. 다음 매니페스트는 출력만 하며 Kubernetes Pod를 생성하지 않습니다.

**Step 3.4: Kubernetes에서의 리소스 제한 연계**
```bash
# Linux 컨테이너 메모리 제한 예시이며 이 블록은 YAML만 출력합니다
# Pod 매니페스트 예시를 확인합니다
cat << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: memory-demo
spec:
  containers:
  - name: memory-demo
    image: nginx:1.30.4
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>힌트가 필요하신가요?</summary>

- Linux 컨테이너는 런타임·kubelet이 memory cgroup 제한을 설정합니다.
- 메모리 pressure는 할당 종류·OOM 그룹 정책에 따라 reclaim·할당 실패·OOM kill로 이어질 수 있습니다. OOM으로 종료된 컨테이너는 `OOMKilled`를 보고할 수 있지만 모든 할당 실패가 그 상태가 되지는 않습니다.
- `kubectl describe pod`는 설정한 제한과 기록된 컨테이너 종료 상태를 보여주며 모든 커널 메모리 사건을 입증하지는 않습니다.
</details>

---

## 실습 4: 파일 권한 관리

### 목표
파일 권한과 소유자를 관리하는 방법을 실습합니다.

### 단계

**Step 4.1: 파일 생성 및 권한 확인**
```bash
LINUX_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-basics.XXXXXX)
: "${LINUX_LAB_DIR:?mktemp failed}"
printf 'Hello Linux\n' > "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -ld "$LINUX_LAB_DIR"
ls -l "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

**Step 4.2: 권한 변경**
```bash
# 실행 권한 추가
chmod +x "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# 숫자 모드로 설정 (읽기/쓰기 - 읽기 - 없음)
chmod 640 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# K8s Secret 볼륨의 기본 권한과 동일하게 설정
chmod 0644 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

실행 비트를 추가해도 임의의 텍스트가 유효한 프로그램이 되지는 않습니다. 0644는 경로 접근이 가능하면 그룹·기타 사용자에게 읽기를 허용하며 이 실습의 mktemp 디렉터리는 접근을 제한합니다. Kubernetes Secret 볼륨 기본값은0644이지만 실제 권한은 소비하는 사용자·그룹과 필요한 접근에 맞춰야 합니다.

**Step 4.3: 소유자 변경**
```bash
id
# Demonstrate an owner change only on the private lab file, then restore it.
sudo chown "root:$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
stat -c '%a %U %G' "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
sudo chown "$(id -u):$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

### 검증
```bash
# 644 모드와 복원한 사용자·그룹 확인
stat -c "%a %U %G" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

---

## 정리
```bash
# Delete only the file created by this lab; keep an unexpected nonempty directory.
if [[ -n ${LINUX_LAB_DIR:-} ]]; then
  rm -f -- "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
  if rmdir -- "$LINUX_LAB_DIR"; then
    unset LINUX_LAB_DIR
  fi
fi

# Only an unfinished job created in this Bash session may be terminated.
if [[ -n ${LINUX_LAB_SLEEP_PID:-} ]]; then
  if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
    kill -TERM "$LINUX_LAB_SLEEP_PID"
  fi
  wait "$LINUX_LAB_SLEEP_PID" 2>/dev/null || true
  unset LINUX_LAB_SLEEP_PID
fi
```

## 문제 해결

<details>
<summary>unshare 명령어가 없다고 나옵니다</summary>

`util-linux` 패키지를 설치하세요:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo dnf install util-linux       # Fedora/RHEL
```
</details>

<details>
<summary>ip netns 명령어가 동작하지 않습니다</summary>

`iproute2` 패키지가 필요합니다:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo dnf install iproute          # Fedora/RHEL
```
</details>


## 참고 자료와 검증 범위

* [systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)
* [systemd memory resource control](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
* [Kernel cgroup v2 memory controller](https://docs.kernel.org/admin-guide/cgroup-v2.html)
* [unshare](https://man7.org/linux/man-pages/man1/unshare.1.html)
* [ip netns](https://man7.org/linux/man-pages/man8/ip-netns.8.html)
* [GNU mktemp manual](https://man7.org/linux/man-pages/man1/mktemp.1.html)

감사에서는 격리한 비특권 프로세스·파일 검사와 구문 검사만 실행합니다. namespace 생성·소유자 변경·cgroup/systemd 작업은 실행하지 않았습니다.

## 다음 단계
- [Linux 기초 퀴즈](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux 실무 기술 실습](./02-linux-advanced-lab.md)
