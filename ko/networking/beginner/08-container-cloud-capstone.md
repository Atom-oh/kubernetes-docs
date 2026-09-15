# 8. 종합 실습 — 웹 서비스 장애에서 컨테이너·클라우드까지

> **학습 기준**: Ubuntu Server 24.04 LTS, Rocky Linux 9 대체 경로
>
> **마지막 업데이트**: 2026년 9월 15일

**선수 조건:** [1–7장](README.md#course-map), 두 VM의 실습 주소, 검증된 SSH 키 로그인, TCP 8000에 대한 실습 클라이언트 허용 규칙. 7장의 웹 서버는 종료된 상태여야 합니다.

**학습 목표:** 작은 웹 서비스의 정상 상태를 기록하고, 서로 다른 계층의 장애를 하나씩 재현·진단·복구합니다. 이후 같은 질문을 Docker와 Kubernetes에 적용합니다. 예상 시간은 3–4시간입니다.

## 과제와 정상 상태 {#baseline}

과제는 “클라이언트가 서버의 `/health.txt`를 읽는다”입니다. 웹 프레임워크나 클라우드 계정은 필요 없습니다.

**서버 콘솔 A:**

```bash
LAB_WEB=$(mktemp -d /tmp/net-capstone.XXXXXX)
printf 'healthy\n' > "$LAB_WEB/health.txt"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

5분 제한이 만료되면 같은 명령으로 다시 시작합니다. 서버가 정지한 상태를 네트워크 장애로 오인하지 않도록 콘솔도 확인합니다. 이 디렉터리에는 위의 실습 파일만 둡니다.

**서버 콘솔 B:**

```bash
ip -br address
ip route get 192.0.2.10
sudo ss -ltnp 'sport = :8000'
```

**클라이언트:**

```bash
ip route get 192.0.2.20
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve lesson.test:8000:192.0.2.20 \
  -i http://lesson.test:8000/health.txt
```

성공 기준은 양쪽 경로가 실습 NIC를 사용하고 리스너가 `192.0.2.20:8000`이며, 두 요청이 HTTP 200과 `healthy` 본문을 반환하는 것입니다. `--resolve`는 **이 curl 실행의 호스트·포트 주소 매핑**만 지정합니다. 시스템 DNS·다른 프로그램 설정은 바꾸지 않습니다.

실패하면 먼저 4–6장의 설정과 허용 규칙을 확인합니다. 정상 상태를 만들기 전에 다음 장애를 추가하지 않습니다.

## 장애를 하나씩 재현하기 {#faults}

각 실험은 위 정상 상태에서 시작합니다. 실험이 끝나면 정상 요청을 다시 보내 복구를 확인합니다. `curl`의 일반 요청은 HTTP 404에도 종료 코드 0을 반환할 수 있으므로 HTTP 상태 줄을 읽습니다. 자동화에서 HTTP 오류도 실패로 다루려면 지원하는 `--fail-with-body` 등을 별도로 선택합니다.

### A. 이름 해석과 IP 연결 구분

클라이언트에서 `--resolve` 없는 요청을 비교합니다.

```bash
getent ahostsv4 lesson.test
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://lesson.test:8000/health.txt
```

`lesson.test`를 따로 등록하지 않은 이 실습에서는 보통 이름 해석이 실패합니다. 이미 `/etc/hosts`·로컬 DNS에 등록했다면 실패를 기대하지 말고 실제 매핑을 기록합니다. 같은 환경에서 앞의 IP 요청과 `--resolve` 요청이 성공하는지 확인합니다.

**판정:** IP로는 성공하지만 이름 조회가 실패하면 이름 해석 경로를 먼저 조사합니다. 이것만으로 특정 DNS 서버 고장이나 인터넷 전체 장애를 단정하지 않습니다. **복구:** 정상 요청의 `--resolve` 매핑을 다시 사용합니다. 임시 실험을 위해 시스템 리졸버를 덮어쓸 필요가 없습니다.

### B. 애플리케이션 경로 오류

클라이언트에서 존재하지 않는 파일을 요청합니다.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/missing.txt
```

**판정:** HTTP 404가 오면 해당 요청의 HTTP 서버와 응답을 주고받은 것입니다. 라우팅·방화벽을 전부 초기화할 이유가 아닙니다. 서버 로그에서 요청 경로를 대조합니다. **복구:** `/health.txt`로 다시 요청합니다.

### C. 잘못된 리스닝 주소

서버 콘솔 A에서 자신이 시작한 서버를 Ctrl+C로 종료합니다. **같은 터미널**에서 바인딩 주소만 바꿉니다.

```bash
timeout 300 python3 -m http.server 8000 \
  --bind 127.0.0.1 --directory "$LAB_WEB"
```

서버 콘솔 B:

```bash
sudo ss -ltnp 'sport = :8000'
curl --disable --noproxy '*' --max-time 5 \
  -i http://127.0.0.1:8000/health.txt
```

클라이언트의 기존 `192.0.2.20:8000` 요청은 실패하고 서버 자신의 루프백 요청은 성공하는지 확인합니다. 실패가 거부인지 타임아웃인지는 방화벽 동작에도 영향을 받습니다. `ss`에서 `127.0.0.1` 리스너를 확인하는 것이 핵심 증거입니다.

**복구:** 콘솔 A에서 Ctrl+C 후 정상 상태의 `--bind 192.0.2.20` 명령으로 재시작합니다. 같은 VM의 루프백은 다른 VM의 루프백이 아닙니다.

### D. 방화벽 가설은 증거와 함께 {#firewall-fault}

서버 하이퍼바이저 콘솔에서 **6장에서 선택한 관리자만** 사용합니다. 이 장애는 실습에서 소유한 TCP 8000 allow만 제거합니다. TCP 22 allow, 실습 deny, 기본 정책, zone·프로필 연결, 관리 NIC는 유지합니다. 백그라운드 차단 변경이 시험에 섞이지 않도록 선택 Fail2ban 실험을 먼저 정리하세요.

**서버 콘솔 B, 일반 사용자:** 기록한 하이퍼바이저 MAC으로 두 NIC를 다시 식별합니다. 6장의 변수가 남아 있다고 가정하지 않습니다.

```bash
ip -br link
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -4 -br address show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route
sudo ss -ltnp 'sport = :8000'
```

실습 NIC의 `.20/24`, 서로 다른 NIC 이름, 유지된 관리 상태와 정상 `.20:8000` 리스너를 확인합니다. 아래 절차대로 현재 규칙도 기록합니다. 서버 타이머가 끝났다면 서버 콘솔 A에서 기존 디렉터리를 사용하는 `timeout 300 python3 -m http.server 8000 --bind 192.0.2.20 --directory "${LAB_WEB:?missing existing web directory}"`만 다시 실행합니다. 서버 정지 장애를 동시에 만들지 마세요.

**클라이언트, 일반 사용자:** 기록에서 기존 5장 키 디렉터리와 일반 서버 계정을 복구합니다. 새 키를 만들거나 검증한 호스트 기록을 우회하지 않습니다.

```bash
read -r -p 'Existing lesson-5 client key directory: ' SSH_LAB_DIR
read -r -p 'Normal account on the server: ' SERVER_USER
ls -l -- "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
  "${SSH_LAB_DIR:?missing key directory}/known_hosts"
```

그 클라이언트 터미널에 다음 짧은 셸 함수를 한 번 정의합니다. `check_lab_ssh`를 부르면 **새** SSH 연결로 원격 계정·연결을 출력한 뒤 클라이언트로 돌아옵니다. 파일이나 서비스를 만들지는 않습니다.

```bash
check_lab_ssh() {
  ssh -F /dev/null -b 192.0.2.10 \
    -i "${SSH_LAB_DIR:?missing key directory}/id_ed25519" \
    -o "UserKnownHostsFile=${SSH_LAB_DIR:?missing key directory}/known_hosts" \
    -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
    -o ControlMaster=no -o ControlPath=none -o ControlPersist=no \
    -o BatchMode=no -o ConnectTimeout=5 \
    "${SERVER_USER:?missing account}@192.0.2.20" \
    'whoami; printf "%s\n" "$SSH_CONNECTION"'
}
check_lab_ssh
```

개인 키 **암호문구 질문을 허용**하므로 잠금 해제된 agent가 없어도 됩니다. 원격 계정 비밀번호 대체 인증은 끕니다. `-F /dev/null`은 관련 없는 클라이언트 설정을 제외하고 다중화를 끄면 기존 인증 연결을 재사용하지 않습니다. 일반 계정과 `.10`에서 `.20`의 22번 포트로 접속한 정보가 나와야 합니다. 이 **장애 전** 확인이나 정상 HTTP가 실패하면 규칙 변경 전에 멈춥니다. 별도로 필요한 관리 SSH 경로도 보존·재확인하세요.

#### UFW: 저장·적용된 HTTP allow만 변경

**Ubuntu 서버 콘솔 B, sudo:**

```bash
sudo ufw status numbered
sudo ufw show added
```

UFW가 active이고 6장의 세 실습 규칙이 다음 순서일 때만 진행합니다. **1: `LAB_IF`의 `.10`→`.20` TCP 22 allow, 2: 별도의 TCP 8000 allow, 3: 같은 인터페이스·목적지의 TCP `22,8000` deny**입니다. 전체 규칙 내용을 기록하세요. 예전의 `22,8000` 결합 allow가 남았거나 순서가 다르면 먼저 6장 구성을 맞춥니다. 포트 하나 삭제는 여러 포트를 묶은 규칙의 역작업이 아닙니다.

HTTP만 제거합니다.

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw status numbered
sudo ufw show added
```

TCP 22 allow가 첫째로 유지되고 실습 deny가 둘째가 되었는지 확인합니다. UFW 저장·적용 상태 모두 바뀝니다. 남은 두 규칙과 기본 정책은 그대로 두고 아래 **장애 중 확인**을 수행합니다.

**같은 Ubuntu 콘솔에서 복원:** deny가 여전히 둘째인지 확인하고 HTTP를 2번 위치, 즉 **그 deny 앞에** 삽입합니다.

```bash
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw status numbered
sudo ufw show added
```

원래 SSH allow → HTTP allow → 실습 deny 순서와 출발지·인터페이스·목적지 범위가 같아야 합니다. deny 뒤에 allow를 덧붙이면 HTTP는 여전히 막히므로 역작업에는 위치 복원도 포함됩니다. 다른 규칙 때문에 위치가 달라졌다면 오래된 번호를 쓰지 말고 멈춰 기록한 순서를 확인합니다. 이어서 아래 복구 후 확인을 수행하세요.

#### firewalld: runtime HTTP만 제거하고 저장 정책 유지

**Rocky 서버 콘솔 B. 변수 대입은 일반 사용자, 방화벽 조회는 sudo:**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

`network-beginner`에는 실습 NIC만 있고 관리 zone은 원래대로이며 네 질의 모두 `yes`여야 합니다. 6장의 만료되는 시험 규칙이 아니라 유지한 영구 규칙을 전제로 합니다. 두 구성을 기록하고 HTTP를 여전히 허용할 수 있는 더 넓은 정책도 확인하세요.

**runtime HTTP 규칙만** 제거합니다.

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

결과는 `no`, `yes`, `yes`, `yes`여야 합니다. `no`의 0이 아닌 종료 상태는 여기서는 예상한 결과입니다. 장애 중 확인을 수행하세요. reload·재부팅·`--runtime-to-permanent`를 실행하지 않습니다. reload는 저장된 HTTP 규칙을 다시 가져오고 runtime을 permanent로 복사하면 의도치 않게 장애를 영구 저장합니다.

**같은 Rocky 콘솔에서 복원**하며 전체 reload나 permanent 변경은 하지 않습니다.

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
```

네 질의가 다시 모두 `yes`여야 합니다. runtime·permanent 목록을 기록한 기준과 비교합니다. 저장 규칙은 바꾸지 않았고 runtime HTTP만 같은 범위로 복원했습니다. 예상 밖의 저장 정책 변경은 일괄 덮어쓰기 대신 기록과 대조하여 조사합니다.

#### 장애 중과 복구 후 확인

**클라이언트, 일반 사용자, 같은 터미널:** 장애 전 확인에 더해 **HTTP 제거 후와 복원 후 각각** 다음 두 명령을 실행합니다.

```bash
check_lab_ssh
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/health.txt
```

장애 중에도 새 키 전용 SSH는 성공해야 합니다. 기록한 실습 정책에서 HTTP는 실패하되 서버 리스너는 `.20:8000`을 유지해야 합니다. SSH가 실패하면 서버 콘솔에서 제거한 HTTP 권한만 복구하고 변경하지 않은 SSH 규칙·경로를 대조한 뒤 멈춥니다. HTTP만의 장애를 입증한 상태가 아닙니다. HTTP가 계속 성공하면 다른 허용, zone·기본 동작, 리스너·패킷 증거를 확인합니다. 규칙 하나를 제거했다는 이유만으로 차단됐다고 기록하지 마세요.

복구 후에는 새 키 전용 SSH 성공과 HTTP 200·`healthy` 본문을 모두 요구합니다. 서버 콘솔 B에서 `sudo ss -ltnp 'sport = :8000'`, 해당 규칙 조회·목록, `ip -4 -br address show dev "$MGMT_IF"`, `ip -4 route`를 반복해 장애 전 기록과 비교하고 필요한 관리 접근도 재확인합니다. 세 단계 관측을 따로 기록하세요. 이 절차가 문서 작성 과정에서 실제 게스트 실행을 수행했다는 뜻은 아닙니다.

## 결과 보고서와 통과 기준 {#capstone-report}

비밀번호·개인키·사용자 트래픽 대신 실습 주소와 결과만 기록합니다.

| 기록 항목 | 적을 내용 |
|---|---|
| 환경 | 배포판·커널·실습 NIC·클라이언트/서버 주소·방화벽 관리자 |
| 정상 상태 | 경로, 리스너, HTTP 상태와 본문 |
| 증상 | 어느 호스트에서 어떤 요청이 어떤 결과를 보였는가 |
| 가설 | DNS / 경로 / 리스너 / 방화벽 / HTTP 중 무엇을 의심하는가 |
| 근거 | 관련 명령·시간·주소/포트·관측 결과 |
| 반증 | 해당 가설이 틀렸다면 무엇이 보여야 하는가 |
| 변경과 복구 | 한 번에 바꾼 항목과 정확한 복구 방법 |
| 재확인 | 정상 HTTP 200, 키 SSH 접근, 실습 NIC/관리 NIC 상태 |

**통과:** A–C에서 다른 원인을 구분하고 복구하며, D에서는 실제 규칙과 결과가 일치하는지 설명합니다. 총 5개 항목을 각각 충족합니다: 환경 식별, 계층별 가설, 관측 근거, 좁은 변경·복구, 복구 후 재확인. 미충족 항목은 해당 장으로 돌아가 반복합니다. 속도가 빠르다는 이유로 통과하는 과제가 아닙니다.

## 같은 질문을 Docker와 Kubernetes에 적용하기 {#container-cloud-map}

VM 사이의 진단을 이해한 뒤 컨테이너를 추가합니다. 다음 표는 후속 학습을 위한 역할 대응이며 모든 패킷이 표 순서대로 지난다는 뜻은 아닙니다.

| 지금 배운 것 | Docker | Kubernetes | 클라우드 |
|---|---|---|---|
| 프로세스의 주소·포트 | 컨테이너 안의 리스너와 네트워크 네임스페이스 | Pod 안의 리스너, 같은 Pod의 네트워크 공유 | 백엔드 프로세스와 로드밸런서 대상 포트 |
| 링크·경로 | veth·Linux bridge, 환경에 따른 NAT | CNI가 설정한 Pod 경로·overlay 또는 native routing | VPC 서브넷·라우팅·연결 경계 |
| 이름 해석 | 사용자 정의 bridge의 컨테이너 이름 해석 | Service 이름과 클러스터 DNS | 조직·클라우드 DNS와 사설 이름 |
| 접근 규칙 | 포트 게시와 호스트의 전달 규칙 | NetworkPolicy와 구현의 실제 강제 | Security Group 등 계층별 접근 제어 |
| 관측 위치 | 호스트와 컨테이너 네임스페이스 구분 | 노드·Pod·Service 구현 구분 | 클라이언트·로드밸런서·노드·AZ 경계 구분 |

Docker의 **bridge**는 같은 호스트에서 연결하는 흔한 방식이고, **overlay**는 하부 네트워크 위에 가상 네트워크를 만드는 방식입니다. Docker Swarm overlay 실습은 여러 호스트 등 추가 준비가 필요합니다. Kubernetes의 CNI는 별도 인터페이스·플러그인 생태계이며 Docker bridge를 그대로 복제하면 Kubernetes가 된다는 뜻은 아닙니다.

또한 `localhost`·Pod IP·Service IP·외부 진입점은 서로 다른 관측 대상입니다. 호스트 방화벽, 컨테이너 전달 규칙, CNI 정책을 같은 규칙 목록으로 취급하지 않습니다.

## 후속 실습 순서 {#next-path}

1. [컨테이너 기술](../../basics/03-container-technology.md)에서 네임스페이스·bridge·포트 게시를 확인합니다.
2. [Linux 네트워크 진단](../07-linux-network-diagnostics.md)으로 다음 홉·ICMP·PMTU를 측정합니다. 해당 문서의 Docker 준비·범위·정리 절차를 먼저 읽습니다.
3. [Kubernetes 소개](../../basics/04-kubernetes-introduction.md)와 [Pod와 워크로드](../../core/02-pods-and-workloads.md)를 배운 뒤 [Service·DNS 실습](../../labs/core/03-services-networking-lab.md)을 수행합니다.
4. [eBPF 기초](../../basics/05-ebpf-fundamentals.md)를 거쳐 [Cilium](../cilium/README.md)·[Calico](../calico/README.md)의 구현 차이를 비교합니다.
5. AWS 환경이 필요할 때 [EKS 네트워킹](../../eks/03-eks-networking-part1.md), [VPC CNI](../01-vpc-cni.md), [로드밸런서](../03-aws-lb-controller.md)를 학습합니다. 실제 리소스 생성은 각 문서의 비용·권한·정리 조건을 별도로 확인한 뒤 수행합니다.
6. 성능에 관심이 있으면 [커널 네트워킹 스택](../../kernel/02-network-stack.md)과 [Pod 벤치마크](../06-pod-network-benchmark.md)의 측정 조건을 읽습니다. 앞의 작은 HTTP 실습 결과를 클라우드 처리량으로 일반화하지 않습니다.

## 정리

서버 콘솔 A의 실습 서버를 종료하고 같은 터미널에서 파일을 삭제합니다.

```bash
rm -- "${LAB_WEB:?}/health.txt"
rmdir -- "${LAB_WEB:?}"
```

6장에서 생성한 실습 규칙을 유지할지 다음 실습을 위해 기록합니다. 전체 과정을 종료한다면 각 장의 복구 절차 또는 **자신의 VM 스냅샷**으로 돌아갑니다. 관리 NIC와 기존 SSH 접근이 정상인지 확인하고 VM을 정상 종료합니다.

## 참고 자료

- [Python http.server](https://docs.python.org/3.12/library/http.server.html)
- [curl 주소 매핑 옵션](https://curl.se/docs/manpage.html)
- [Ubuntu 24.04 UFW: 규칙 순서·다중 포트·삭제](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)
- [firewalld: runtime·permanent 설정과 rich rule 작업](https://firewalld.org/documentation/man-pages/firewall-cmd.html)
- [OpenSSH 클라이언트 옵션과 연결 공유](https://man.openbsd.org/ssh_config)
- [Docker bridge](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker overlay](https://docs.docker.com/engine/network/drivers/overlay/)
- [Kubernetes 네트워킹 모델](https://kubernetes.io/docs/concepts/services-networking/)

[이전: 관측과 성능](07-monitoring-performance.md) · [퀴즈](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) · [과정으로 돌아가기](README.md)
