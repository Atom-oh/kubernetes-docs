# 런타임 보안 (Runtime Security)

> **지원 버전**: Falco 0.39+, Tetragon 1.2+, Kubernetes 1.31, 1.32, 1.33
> **마지막 업데이트**: 2026년 2월 21일

런타임 보안은 컨테이너가 실행되는 동안 악성 활동과 비정상적인 동작을 탐지하고 대응하는 것입니다. 이 문서에서는 Falco와 Tetragon을 중심으로 런타임 보안 전략을 다룹니다.

## 목차

1. [런타임 위협 환경](#런타임-위협-환경)
2. [Falco](#falco)
3. [Tetragon](#tetragon)
4. [Falco vs Tetragon 비교](#falco-vs-tetragon-비교)
5. [Kubernetes 감사 로깅](#kubernetes-감사-로깅)
6. [런타임 위협 탐지 패턴](#런타임-위협-탐지-패턴)
7. [인시던트 대응](#인시던트-대응)
8. [SIEM/SOAR 통합](#siemsoar-통합)

---

## 런타임 위협 환경

### 컨테이너 런타임 위협

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    컨테이너 런타임 위협 유형                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      공격 벡터                                   │   │
│  │                                                                  │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │  │ 취약점    │  │ 잘못된   │  │ 악성      │  │ 공급망    │   │   │
│  │  │ 익스플로잇│  │ 설정     │  │ 이미지    │  │ 공격      │   │   │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘   │   │
│  │        │              │              │              │          │   │
│  │        └──────────────┴──────────────┴──────────────┘          │   │
│  │                              │                                  │   │
│  │                              ▼                                  │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                    런타임 위협                           │   │   │
│  │  │                                                          │   │   │
│  │  │  • 암호화폐 채굴 (Cryptomining)                         │   │   │
│  │  │  • 리버스 셸 (Reverse Shell)                            │   │   │
│  │  │  • 권한 상승 (Privilege Escalation)                     │   │   │
│  │  │  • 컨테이너 탈출 (Container Escape)                     │   │   │
│  │  │  • 데이터 유출 (Data Exfiltration)                      │   │   │
│  │  │  • 측면 이동 (Lateral Movement)                         │   │   │
│  │  │  • 지속성 확보 (Persistence)                            │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 탐지 기술

| 기술 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **시스콜 모니터링** | 커널 시스템 콜 추적 | 상세한 가시성 | 오버헤드 |
| **eBPF** | 커널 레벨 프로그래밍 | 고성능, 안전 | 복잡한 구현 |
| **감사 로그** | K8s API 호출 기록 | 컴플라이언스 | 런타임 가시성 제한 |
| **네트워크 모니터링** | 트래픽 패턴 분석 | 측면 이동 탐지 | 암호화 트래픽 |

---

## Falco

### Falco 개요

Falco는 클라우드 네이티브 런타임 보안 도구로, 시스템 콜을 분석하여 비정상적인 동작을 탐지합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Falco 아키텍처                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Kubernetes Node                             │   │
│  │                                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Container A │  │ Container B │  │ Container C │             │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │   │
│  │         │                │                │                     │   │
│  │         └────────────────┼────────────────┘                     │   │
│  │                          │ System Calls                         │   │
│  │                          ▼                                      │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                    Linux Kernel                          │   │   │
│  │  │  ┌─────────────────────────────────────────────────┐    │   │   │
│  │  │  │         Falco eBPF/Kernel Module               │    │   │   │
│  │  │  │         (시스템 콜 캡처)                        │    │   │   │
│  │  │  └─────────────────────────────────────────────────┘    │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                          │                                      │   │
│  │                          ▼                                      │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                    Falco Engine                          │   │   │
│  │  │  ┌───────────┐  ┌───────────┐  ┌───────────────────┐   │   │   │
│  │  │  │   Rules   │  │ Filtering │  │  Output Channels  │   │   │   │
│  │  │  │  Engine   │──▶│  Engine   │──▶│ • stdout         │   │   │   │
│  │  │  │           │  │           │  │ • file            │   │   │   │
│  │  │  │           │  │           │  │ • Slack           │   │   │   │
│  │  │  │           │  │           │  │ • PagerDuty       │   │   │   │
│  │  │  └───────────┘  └───────────┘  └───────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Falco 설치 (EKS)

```bash
# Helm을 사용한 Falco 설치
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

# eBPF 드라이버 사용 (권장)
helm install falco falcosecurity/falco \
    --namespace falco \
    --create-namespace \
    --set driver.kind=ebpf \
    --set falcosidekick.enabled=true \
    --set falcosidekick.webui.enabled=true
```

```yaml
# values.yaml (상세 설정)
driver:
  kind: ebpf

falco:
  jsonOutput: true
  jsonIncludeOutputProperty: true
  httpOutput:
    enabled: true
    url: http://falcosidekick:2801

customRules:
  custom-rules.yaml: |-
    # 커스텀 규칙은 여기에 추가

falcosidekick:
  enabled: true
  config:
    slack:
      webhookurl: "https://hooks.slack.com/services/xxx"
      outputformat: "all"
      minimumpriority: "warning"
    pagerduty:
      apikey: "xxx"
      minimumpriority: "critical"

  webui:
    enabled: true
    service:
      type: ClusterIP
```

### Falco 규칙 구조

```yaml
# 규칙 구조
- rule: <규칙 이름>
  desc: <설명>
  condition: <조건 표현식>
  output: <출력 메시지>
  priority: <심각도: EMERGENCY|ALERT|CRITICAL|ERROR|WARNING|NOTICE|INFO|DEBUG>
  tags: [<태그 목록>]
  enabled: true|false
```

### 기본 제공 규칙 예시

```yaml
# /etc/falco/falco_rules.yaml

# 컨테이너에서 셸 실행 탐지
- rule: Terminal shell in container
  desc: A shell was spawned in a container
  condition: >
    spawned_process and
    container and
    shell_procs and
    proc.tty != 0
  output: >
    Shell spawned in a container
    (user=%user.name user_loginuid=%user.loginuid container=%container.name
    shell=%proc.name parent=%proc.pname cmdline=%proc.cmdline
    terminal=%proc.tty exe_flags=%evt.arg.flags)
  priority: WARNING
  tags: [shell, container, mitre_execution]

# 민감한 파일 읽기 탐지
- rule: Read sensitive file untrusted
  desc: An untrusted program read a sensitive file
  condition: >
    sensitive_files and
    open_read and
    proc_name_exists and
    not user_trusted_containers
  output: >
    Sensitive file read by untrusted program
    (user=%user.name name=%proc.name command=%proc.cmdline
    file=%fd.name parent=%proc.pname gparent=%proc.aname[2]
    container=%container.name image=%container.image.repository)
  priority: WARNING
  tags: [filesystem, mitre_credential_access]

# 권한 상승 탐지
- rule: Detect su or sudo
  desc: Detect su or sudo execution
  condition: >
    spawned_process and
    (proc.name in (su, sudo))
  output: >
    Privilege escalation via su/sudo
    (user=%user.name command=%proc.cmdline container=%container.name)
  priority: WARNING
  tags: [privilege_escalation]
```

### 커스텀 규칙 작성

```yaml
# 암호화폐 채굴 탐지
- rule: Detect Cryptocurrency Mining
  desc: Detect cryptocurrency mining processes
  condition: >
    spawned_process and
    container and
    (
      proc.name in (xmrig, minerd, cgminer, cpuminer, bfgminer) or
      proc.cmdline contains "stratum+tcp://" or
      proc.cmdline contains "pool.minexmr.com" or
      proc.cmdline contains "cryptonight"
    )
  output: >
    Cryptocurrency mining detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository)
  priority: CRITICAL
  tags: [cryptomining, mitre_resource_hijacking]

# 리버스 셸 탐지
- rule: Reverse Shell Detection
  desc: Detect reverse shell connections
  condition: >
    spawned_process and
    container and
    (
      (proc.name = bash and proc.cmdline contains "/dev/tcp/") or
      (proc.name = nc and proc.args contains "-e") or
      (proc.name = python and proc.cmdline contains "socket" and
       proc.cmdline contains "subprocess") or
      (proc.name = perl and proc.cmdline contains "socket") or
      (proc.name = ruby and proc.cmdline contains "TCPSocket")
    )
  output: >
    Reverse shell detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository connection=%fd.name)
  priority: CRITICAL
  tags: [reverse_shell, mitre_execution]

# Kubernetes Secret 접근 탐지
- rule: Unauthorized K8s Secret Access
  desc: Detect unauthorized access to mounted Kubernetes secrets
  condition: >
    open_read and
    container and
    fd.name startswith "/var/run/secrets/kubernetes.io" and
    not proc.name in (kubelet, kube-proxy)
  output: >
    Kubernetes secret accessed
    (user=%user.name command=%proc.cmdline file=%fd.name
    container=%container.name image=%container.image.repository)
  priority: WARNING
  tags: [k8s, secrets, mitre_credential_access]

# 컨테이너 탈출 시도 탐지
- rule: Container Escape Attempt
  desc: Detect potential container escape attempts
  condition: >
    spawned_process and
    container and
    (
      proc.cmdline contains "nsenter" or
      proc.cmdline contains "/proc/1/root" or
      proc.cmdline contains "/.dockerenv" or
      (proc.name = mount and proc.args contains "cgroup")
    )
  output: >
    Container escape attempt detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository)
  priority: CRITICAL
  tags: [container_escape, mitre_privilege_escalation]
```

### Falco 알림 설정

```yaml
# Falcosidekick 설정으로 다양한 채널에 알림
falcosidekick:
  config:
    # Slack
    slack:
      webhookurl: "https://hooks.slack.com/services/xxx/yyy/zzz"
      channel: "#security-alerts"
      username: "Falco"
      outputformat: "all"
      minimumpriority: "warning"

    # PagerDuty
    pagerduty:
      routingkey: "xxx"
      minimumpriority: "critical"

    # AWS CloudWatch
    cloudwatchlogs:
      region: "ap-northeast-2"
      loggroup: "/falco/alerts"
      logstream: "eks-cluster"

    # AWS Security Hub
    securityhub:
      region: "ap-northeast-2"
      minimumpriority: "high"

    # Prometheus
    prometheus:
      extralabels: "cluster:production"

    # Elasticsearch
    elasticsearch:
      hostport: "https://elasticsearch:9200"
      index: "falco"
      type: "_doc"
```

---

## Tetragon

### Tetragon 개요

Tetragon은 Cilium 프로젝트의 eBPF 기반 보안 관찰성 및 런타임 강제 도구입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Tetragon 아키텍처                                 │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Kubernetes Cluster                            │   │
│  │                                                                  │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │                    Tetragon DaemonSet                      │  │   │
│  │  │                                                            │  │   │
│  │  │  ┌─────────────────────────────────────────────────────┐  │  │   │
│  │  │  │                   eBPF Programs                      │  │  │   │
│  │  │  │                                                      │  │  │   │
│  │  │  │  • Process Execution   • File Access                │  │  │   │
│  │  │  │  • Network Activity    • Capability Usage           │  │  │   │
│  │  │  │  • Namespace Changes   • Syscall Tracing            │  │  │   │
│  │  │  └─────────────────────────────────────────────────────┘  │  │   │
│  │  │                           │                                │  │   │
│  │  │                           ▼                                │  │   │
│  │  │  ┌─────────────────────────────────────────────────────┐  │  │   │
│  │  │  │               TracingPolicy CRD                      │  │  │   │
│  │  │  │                                                      │  │  │   │
│  │  │  │  • kprobes    • tracepoints    • uprobes            │  │  │   │
│  │  │  │  • Selectors  • Actions        • Filters            │  │  │   │
│  │  │  └─────────────────────────────────────────────────────┘  │  │   │
│  │  │                           │                                │  │   │
│  │  │                           ▼                                │  │   │
│  │  │  ┌─────────────────────────────────────────────────────┐  │  │   │
│  │  │  │                    Outputs                           │  │  │   │
│  │  │  │                                                      │  │  │   │
│  │  │  │  • JSON Events  • gRPC API  • Prometheus Metrics    │  │  │   │
│  │  │  └─────────────────────────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tetragon 설치

```bash
# Helm을 사용한 Tetragon 설치
helm repo add cilium https://helm.cilium.io
helm repo update

helm install tetragon cilium/tetragon \
    -n kube-system \
    --set tetragon.enableProcessCred=true \
    --set tetragon.enableProcessNs=true
```

### TracingPolicy 기본 구조

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: example-policy
spec:
  # kprobes: 커널 함수 추적
  kprobes:
    - call: "security_file_open"
      syscall: false
      args:
        - index: 0
          type: "file"
      selectors:
        - matchArgs:
            - index: 0
              operator: "Prefix"
              values:
                - "/etc/shadow"
          matchActions:
            - action: Sigkill  # 프로세스 종료
```

### 프로세스 모니터링

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: process-monitoring
spec:
  kprobes:
    # execve 시스템 콜 모니터링
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"  # 실행 파일 경로
      selectors:
        - matchBinaries:
            - operator: "In"
              values:
                - "/bin/bash"
                - "/bin/sh"
                - "/usr/bin/python"
          matchNamespaces:
            - namespace: Pid
              operator: NotIn
              values:
                - "host_ns"  # 호스트 네임스페이스 제외
```

### 파일 접근 모니터링

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: sensitive-file-access
spec:
  kprobes:
    - call: "security_file_open"
      syscall: false
      args:
        - index: 0
          type: "file"
      selectors:
        # 민감한 파일 접근 모니터링
        - matchArgs:
            - index: 0
              operator: "Prefix"
              values:
                - "/etc/shadow"
                - "/etc/passwd"
                - "/etc/sudoers"
                - "/root/.ssh"
                - "/var/run/secrets/kubernetes.io"
          matchActions:
            - action: Post  # 이벤트 기록
---
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-sensitive-file-write
spec:
  kprobes:
    - call: "security_file_open"
      syscall: false
      args:
        - index: 0
          type: "file"
        - index: 1
          type: "int"  # flags
      selectors:
        # 쓰기 모드로 민감한 파일 접근 차단
        - matchArgs:
            - index: 0
              operator: "Prefix"
              values:
                - "/etc/passwd"
                - "/etc/shadow"
            - index: 1
              operator: "Mask"
              values:
                - "2"  # O_WRONLY or O_RDWR
          matchActions:
            - action: Sigkill  # 프로세스 종료
```

### 네트워크 모니터링

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: network-monitoring
spec:
  kprobes:
    # 아웃바운드 연결 모니터링
    - call: "tcp_connect"
      syscall: false
      args:
        - index: 0
          type: "sock"
      selectors:
        - matchArgs:
            - index: 0
              operator: "DPort"
              values:
                - "22"    # SSH
                - "4444"  # 일반적인 리버스 셸 포트
                - "5555"  # 일반적인 리버스 셸 포트
          matchActions:
            - action: Post

    # DNS 쿼리 모니터링
    - call: "udp_sendmsg"
      syscall: false
      args:
        - index: 0
          type: "sock"
      selectors:
        - matchArgs:
            - index: 0
              operator: "DPort"
              values:
                - "53"
          matchActions:
            - action: Post
```

### 런타임 강제 (Enforcement)

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-crypto-miners
spec:
  kprobes:
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"
      selectors:
        # 암호화폐 채굴 프로세스 차단
        - matchArgs:
            - index: 0
              operator: "Postfix"
              values:
                - "xmrig"
                - "minerd"
                - "cgminer"
          matchActions:
            - action: Sigkill
---
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-reverse-shells
spec:
  kprobes:
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"
        - index: 1
          type: "string"  # argv
      selectors:
        # 리버스 셸 패턴 차단
        - matchArgs:
            - index: 1
              operator: "Contains"
              values:
                - "/dev/tcp/"
                - "bash -i"
                - "nc -e"
          matchActions:
            - action: Sigkill
```

### Tetragon CLI 사용

```bash
# 이벤트 스트림 확인
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents

# 프로세스 이벤트 필터링
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
    tetra getevents -o compact --process curl

# JSON 형식 출력
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
    tetra getevents -o json

# 네임스페이스 필터링
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
    tetra getevents --namespace production
```

---

## Falco vs Tetragon 비교

### 기능 비교표

| 기능 | Falco | Tetragon |
|------|-------|----------|
| **기술 기반** | 커널 모듈/eBPF | eBPF 전용 |
| **성능** | 좋음 | 매우 좋음 |
| **규칙 언어** | YAML + 조건식 | CRD (TracingPolicy) |
| **런타임 강제** | 제한적 | 네이티브 지원 |
| **Kubernetes 통합** | 좋음 | 매우 좋음 (Cilium) |
| **프로세스 추적** | ✓ | ✓ |
| **파일 모니터링** | ✓ | ✓ |
| **네트워크 모니터링** | 제한적 | ✓ (Cilium 연계) |
| **커뮤니티** | 크고 성숙함 | 성장 중 |
| **학습 곡선** | 중간 | 높음 |
| **알림 통합** | Falcosidekick | Prometheus, gRPC |

### 사용 사례별 권장

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      사용 사례별 권장 도구                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  탐지 중심 모니터링                                                      │
│  └─▶ Falco (성숙한 규칙셋, 다양한 알림 통합)                            │
│                                                                         │
│  런타임 강제 필요                                                        │
│  └─▶ Tetragon (프로세스 종료, 네트워크 차단)                            │
│                                                                         │
│  Cilium CNI 사용 환경                                                   │
│  └─▶ Tetragon (네이티브 통합)                                           │
│                                                                         │
│  컴플라이언스/감사                                                       │
│  └─▶ Falco + Tetragon (상호 보완)                                       │
│                                                                         │
│  최소 오버헤드 필요                                                      │
│  └─▶ Tetragon (순수 eBPF)                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Kubernetes 감사 로깅

### 감사 정책 구성

```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # 인증 실패 로깅
  - level: Metadata
    users: ["system:anonymous"]
    verbs: ["*"]

  # Secret 접근 상세 로깅
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["secrets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

  # Pod exec/attach 로깅
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["pods/exec", "pods/attach", "pods/portforward"]
    verbs: ["create"]

  # RBAC 변경 로깅
  - level: RequestResponse
    resources:
      - group: "rbac.authorization.k8s.io"
        resources: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
    verbs: ["create", "update", "patch", "delete"]

  # 일반 읽기 작업은 최소 로깅
  - level: Metadata
    verbs: ["get", "list", "watch"]

  # 기타 모든 요청
  - level: Request
    verbs: ["*"]
```

### EKS 감사 로그 분석

```bash
# CloudWatch Logs Insights 쿼리

# Secret 접근 이벤트
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100

# 권한 거부 이벤트
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter responseStatus.code = 403
| sort @timestamp desc

# exec/attach 이벤트
fields @timestamp, user.username, objectRef.name, requestURI
| filter objectRef.subresource in ["exec", "attach"]
| sort @timestamp desc
```

---

## 런타임 위협 탐지 패턴

### 암호화폐 채굴 탐지

```yaml
# Falco 규칙
- rule: Cryptocurrency Mining Activity
  desc: Detect processes commonly used for cryptocurrency mining
  condition: >
    spawned_process and container and
    (
      proc.name in (xmrig, minerd, cpuminer, cgminer) or
      proc.cmdline contains "stratum+tcp" or
      proc.cmdline contains "pool." and proc.cmdline contains ":" or
      proc.cmdline contains "--algo=cryptonight"
    )
  output: >
    Cryptocurrency mining activity detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository pod=%k8s.pod.name)
  priority: CRITICAL
  tags: [cryptomining, mitre_resource_hijacking]
```

### 리버스 셸 탐지

```yaml
- rule: Reverse Shell Activity
  desc: Detect outbound network connections that may be reverse shells
  condition: >
    spawned_process and container and
    (
      (proc.name = bash and proc.cmdline contains "/dev/tcp/") or
      (proc.name = nc and (proc.args contains "-e" or proc.args contains "-c")) or
      (proc.name = ncat and proc.args contains "--sh-exec") or
      (proc.name = python and proc.cmdline contains "socket" and
       proc.cmdline contains "subprocess") or
      (proc.name = perl and proc.cmdline contains "socket" and
       proc.cmdline contains "exec") or
      (proc.name = php and proc.cmdline contains "fsockopen")
    )
  output: >
    Reverse shell detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository pod=%k8s.pod.name)
  priority: CRITICAL
  tags: [reverse_shell, mitre_command_and_control]
```

### 권한 상승 탐지

```yaml
- rule: Privilege Escalation via SUID
  desc: Detect execution of SUID binaries
  condition: >
    spawned_process and container and
    proc.is_exe_upper_layer=false and
    user.uid != 0 and
    proc.suid != 0 and
    proc.suid != proc.uid
  output: >
    SUID binary executed
    (user=%user.name uid=%user.uid suid=%proc.suid command=%proc.cmdline
    container=%container.name)
  priority: WARNING
  tags: [privilege_escalation, mitre_privilege_escalation]

- rule: Setuid/Setgid Binary Created
  desc: Detect creation of setuid/setgid binaries
  condition: >
    evt.type = chmod and container and
    (evt.arg.mode contains "S_ISUID" or evt.arg.mode contains "S_ISGID")
  output: >
    Setuid/setgid binary created
    (user=%user.name file=%fd.name mode=%evt.arg.mode container=%container.name)
  priority: CRITICAL
  tags: [privilege_escalation, persistence]
```

---

## 인시던트 대응

### Pod 격리 절차

```bash
#!/bin/bash
# incident-response.sh

POD_NAME=$1
NAMESPACE=$2

# 1. Pod를 격리 네트워크 정책 적용
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-${POD_NAME}
  namespace: ${NAMESPACE}
spec:
  podSelector:
    matchLabels:
      app: $(kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o jsonpath='{.metadata.labels.app}')
  policyTypes:
    - Ingress
    - Egress
  # 모든 트래픽 차단
EOF

# 2. Pod 상태 수집
echo "=== Pod 정보 수집 ==="
kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o yaml > pod-${POD_NAME}-spec.yaml
kubectl describe pod ${POD_NAME} -n ${NAMESPACE} > pod-${POD_NAME}-describe.txt
kubectl logs ${POD_NAME} -n ${NAMESPACE} --all-containers > pod-${POD_NAME}-logs.txt

# 3. 프로세스 목록 수집 (가능한 경우)
kubectl exec ${POD_NAME} -n ${NAMESPACE} -- ps aux > pod-${POD_NAME}-processes.txt 2>/dev/null

# 4. 네트워크 연결 수집
kubectl exec ${POD_NAME} -n ${NAMESPACE} -- netstat -an > pod-${POD_NAME}-network.txt 2>/dev/null

# 5. 파일시스템 스냅샷 (필요시)
# kubectl debug ${POD_NAME} -n ${NAMESPACE} --image=busybox -- tar -cvf /tmp/fs.tar /

echo "=== 증거 수집 완료 ==="
echo "수집된 파일: pod-${POD_NAME}-*.txt"
```

### 포렌식 컨테이너 사용

```yaml
# Debug 컨테이너로 포렌식 수행
apiVersion: v1
kind: Pod
metadata:
  name: forensics-pod
  namespace: security
spec:
  containers:
  - name: forensics
    image: nicolaka/netshoot:latest
    command: ["sleep", "3600"]
    securityContext:
      capabilities:
        add:
          - SYS_PTRACE
          - NET_ADMIN
    volumeMounts:
      - name: host-proc
        mountPath: /host/proc
        readOnly: true
      - name: evidence
        mountPath: /evidence
  volumes:
    - name: host-proc
      hostPath:
        path: /proc
    - name: evidence
      emptyDir: {}
```

---

## SIEM/SOAR 통합

### Falco → Elasticsearch

```yaml
# Falcosidekick Elasticsearch 설정
falcosidekick:
  config:
    elasticsearch:
      hostport: "https://elasticsearch.logging:9200"
      index: "falco"
      type: "_doc"
      minimumpriority: "warning"
      mutualtls: false
      checkcert: true
      username: "elastic"
      password: "${ELASTIC_PASSWORD}"
```

### Prometheus + Grafana 대시보드

```yaml
# ServiceMonitor for Falco metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: falco
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: falco
  endpoints:
    - port: metrics
      interval: 30s
```

```yaml
# Grafana 대시보드 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: falco-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  falco-dashboard.json: |
    {
      "title": "Falco Security Alerts",
      "panels": [
        {
          "title": "Alerts by Priority",
          "type": "piechart",
          "targets": [
            {
              "expr": "sum by (priority) (falco_events_total)"
            }
          ]
        },
        {
          "title": "Alerts Over Time",
          "type": "timeseries",
          "targets": [
            {
              "expr": "rate(falco_events_total[5m])"
            }
          ]
        }
      ]
    }
```

---

## 요약

런타임 보안의 핵심:

1. **Falco**: 성숙한 규칙셋, 다양한 알림 통합, 탐지 중심
2. **Tetragon**: eBPF 기반 고성능, 런타임 강제 지원
3. **감사 로깅**: Kubernetes API 활동 추적, 컴플라이언스
4. **위협 탐지**: 암호화폐 채굴, 리버스 셸, 권한 상승
5. **인시던트 대응**: 격리, 증거 수집, 포렌식

### 권장 사항

- 탐지와 강제를 위해 Falco + Tetragon 조합 사용
- 중요 시스템에 커스텀 규칙 작성
- SIEM 통합으로 중앙 집중 모니터링
- 인시던트 대응 플레이북 준비

---

## 참고 자료

- [Falco 공식 문서](https://falco.org/docs/)
- [Tetragon 문서](https://tetragon.io/docs/)
- [MITRE ATT&CK for Containers](https://attack.mitre.org/matrices/enterprise/containers/)
- [Kubernetes 감사 로깅](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
