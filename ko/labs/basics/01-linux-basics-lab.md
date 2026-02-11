# Linux 기초 실습 가이드

> **난이도**: 초급
> **예상 소요 시간**: 45분
> **마지막 업데이트**: 2025년 2월

## 학습 목표
- Linux 프로세스 관리 명령어를 실습합니다
- Linux 네임스페이스의 격리 효과를 직접 확인합니다
- cgroup을 통한 리소스 제한을 이해합니다
- 파일 권한과 소유자 관리를 실습합니다

## 사전 요구 사항
- [ ] Linux 터미널 접근 (Ubuntu 20.04+ 권장)
- [ ] sudo 권한
- [ ] [Linux 기초](../../basics/01-linux-basics.md) 학습 완료

---

## 실습 1: 프로세스 관리

### 목표
프로세스 조회, 백그라운드 실행, 시그널 전송을 실습합니다.

### 단계

**Step 1.1: 현재 실행 중인 프로세스 확인**
```bash
# 현재 터미널의 프로세스
ps aux | head -20

# 트리 형태로 프로세스 관계 확인
ps auxf | head -30
```

**Step 1.2: 백그라운드 프로세스 실행**
```bash
# 백그라운드에서 sleep 프로세스 실행
sleep 300 &
echo "PID: $!"

# 백그라운드 작업 확인
jobs -l
```

**Step 1.3: 프로세스에 시그널 전송**
```bash
# 프로세스 ID 확인
SLEEP_PID=$(pgrep -f "sleep 300")
echo "Sleep PID: $SLEEP_PID"

# SIGTERM으로 종료 요청
kill $SLEEP_PID

# 프로세스가 종료되었는지 확인
ps aux | grep "sleep 300" | grep -v grep
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `kill -l`로 사용 가능한 시그널 목록을 확인할 수 있습니다
- `kill -9 PID`는 SIGKILL로 강제 종료합니다
- `pkill -f "패턴"`으로 이름 기반 종료가 가능합니다
</details>

### 검증
```bash
# sleep 프로세스가 없어야 합니다
pgrep -f "sleep 300" && echo "아직 실행 중" || echo "종료 완료"
```

---

## 실습 2: Linux 네임스페이스 격리

### 목표
네임스페이스를 생성하여 프로세스와 네트워크의 격리를 확인합니다.

### 단계

**Step 2.1: PID 네임스페이스 격리 확인**
```bash
# 새로운 PID 네임스페이스에서 bash 실행
sudo unshare --pid --fork --mount-proc bash -c '
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
# 네트워크 네임스페이스 생성
sudo ip netns add test-ns

# 네임스페이스 목록 확인
sudo ip netns list

# 격리된 네임스페이스에서 네트워크 확인
sudo ip netns exec test-ns ip addr

# 정리
sudo ip netns delete test-ns
```

<details>
<summary>힌트가 필요하신가요?</summary>

- 네트워크 네임스페이스 내부에서는 호스트의 네트워크 인터페이스가 보이지 않습니다
- `lo` (루프백) 인터페이스만 존재하며, 기본적으로 DOWN 상태입니다
- 이것이 컨테이너의 네트워크 격리 원리입니다
</details>

### 검증
```bash
# 네임스페이스가 삭제되었는지 확인
sudo ip netns list | grep test-ns && echo "아직 존재" || echo "삭제 완료"
```

---

## 실습 3: cgroup 리소스 제한

### 목표
cgroup을 사용하여 프로세스의 메모리 사용을 제한합니다.

### 단계

**Step 3.1: cgroup 정보 확인**
```bash
# cgroup v2 마운트 확인
mount | grep cgroup

# 현재 프로세스의 cgroup 확인
cat /proc/self/cgroup

# cgroup 컨트롤러 확인
cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null || echo "cgroup v1 사용 중"
```

**Step 3.2: 메모리 사용량 확인**
```bash
# 시스템 메모리 정보
free -h

# 특정 프로세스의 메모리 사용량
ps aux --sort=-%mem | head -10
```

**Step 3.3: Kubernetes에서의 리소스 제한 연계**
```bash
# 이것이 K8s에서 resources.limits가 동작하는 원리입니다
# Pod 매니페스트 예시를 확인합니다
cat << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: memory-demo
spec:
  containers:
  - name: memory-demo
    image: nginx
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>힌트가 필요하신가요?</summary>

- K8s의 `resources.limits.memory`는 컨테이너의 cgroup 메모리 제한으로 변환됩니다
- 제한을 초과하면 OOMKilled 상태가 됩니다
- `kubectl describe pod`에서 리소스 제한을 확인할 수 있습니다
</details>

---

## 실습 4: 파일 권한 관리

### 목표
파일 권한과 소유자를 관리하는 방법을 실습합니다.

### 단계

**Step 4.1: 파일 생성 및 권한 확인**
```bash
# 테스트 파일 생성
mkdir -p /tmp/linux-lab
echo "Hello Linux" > /tmp/linux-lab/test.txt

# 현재 권한 확인
ls -la /tmp/linux-lab/test.txt
```

**Step 4.2: 권한 변경**
```bash
# 실행 권한 추가
chmod +x /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt

# 숫자 모드로 설정 (읽기/쓰기 - 읽기 - 없음)
chmod 640 /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt

# K8s Secret 볼륨의 기본 권한과 동일하게 설정
chmod 0644 /tmp/linux-lab/test.txt
```

**Step 4.3: 소유자 변경**
```bash
# 현재 사용자와 그룹 확인
id

# 그룹 변경 (실행 가능한 경우)
sudo chown $USER:root /tmp/linux-lab/test.txt
ls -la /tmp/linux-lab/test.txt
```

### 검증
```bash
# 권한이 -rw-r--r--인지 확인
stat -c "%a %U %G" /tmp/linux-lab/test.txt
```

---

## 정리
```bash
# 테스트 파일 삭제
rm -rf /tmp/linux-lab

# 남은 프로세스 정리
pkill -f "sleep 300" 2>/dev/null
```

## 문제 해결

<details>
<summary>unshare 명령어가 없다고 나옵니다</summary>

`util-linux` 패키지를 설치하세요:
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo yum install util-linux       # CentOS/RHEL
```
</details>

<details>
<summary>ip netns 명령어가 동작하지 않습니다</summary>

`iproute2` 패키지가 필요합니다:
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo yum install iproute          # CentOS/RHEL
```
</details>

## 다음 단계
- [Linux 기초 퀴즈](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux 실무 기술 실습](./02-linux-advanced-lab.md)
