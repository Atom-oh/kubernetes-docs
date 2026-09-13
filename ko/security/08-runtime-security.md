<span id="목차"></span>

# 런타임 보안 (Runtime Security)

> **마지막 업데이트**: 2026년 9월 13일
> **검증 기준**: Falco 0.44.1 / chart 9.1.0, Falcosidekick 2.35.0 / chart 0.14.0, Tetragon 1.7.1. 커널·OS·노드 종류에 따른 지원 범위를 별도로 확인합니다.

런타임 보안은 실행 중인 프로세스·파일·네트워크 활동을 관찰하고, 검증된 정책으로 일부 동작을 제한하는 일입니다. **경보는 침해의 확정 증거가 아니며, 탐지 성공과 차단 성공은 별도로 시험**해야 합니다. 이 문서는 로컬 CLI·schema·Helm·합성 이벤트로 확인했습니다. 실제 클러스터, 커널 BPF 프로그램, 알림 채널에는 연결하지 않았습니다.

<span id="컨테이너-런타임-위협"></span>
<span id="탐지-기술"></span>

## 런타임 위협 환경

| 관측 지점 | 확인 가능한 것 | 한계 |
|---|---|---|
| Syscall/커널 hook | 프로세스 실행, 파일 접근, 연결 시도 | 누락 이벤트·권한·커널 지원·필터 범위 확인 필요 |
| Kubernetes audit | API 요청자, verb, 대상, 응답 상태 | Pod 안의 모든 파일·프로세스 동작을 보여주지 않음 |
| 네트워크 flow | 연결·drop·정책 verdict | 포트나 암호화된 연결만으로 악성 여부를 확정하지 못함 |
| 이미지/배포 정책 | 취약점·서명·Pod 보안 설정 | 배포 이후의 행위를 모두 탐지하지 못함 |

eBPF라는 이유만으로 비용이 항상 낮거나 안전성이 보장되는 것은 아닙니다. hook·event rate·필터·출력량·CPU와 메모리를 해당 노드에서 측정합니다. 공격 명령 이름이 보였다는 이유만으로 운영 프로세스를 자동 종료하지 않습니다.

<span id="기본-제공-규칙-예시"></span>

## Falco

### Falco 개요

Falco는 event source의 데이터를 규칙으로 평가합니다. 일반적인 syscall 경로는 `Linux event → modern eBPF/kmod capture → Falco filter/rule → JSON output → Falcosidekick → 알림/저장소`입니다. Slack·PagerDuty는 별도 출력 연동이며 Falco 엔진의 내장 Slack 전송 기능으로 설명하지 않습니다.

0.44.1 배포에는 container plugin 0.7.1이 포함됩니다. container.id 등의 필드는 이 plugin에서 제공하므로 plugin을 모두 비활성화하면 해당 규칙을 검증·실행할 수 없습니다. 실제 runtime socket·Kubernetes metadata 수집과 권한을 확인합니다.

### Falco 설치 (EKS)

관리 가능한 Linux EC2 노드에 설치하는 예제입니다. Fargate나 호스트 접근이 제한된 노드에 DaemonSet을 배치할 수 있다고 가정하지 않습니다. modern eBPF의 커널·BTF·capability 요구사항과 사용 OS를 확인합니다. chart 9.1.0의 명시적 driver 종류는 `modern_ebpf` 또는 `kmod`이며 예전 `ebpf` 값을 그대로 사용하지 않습니다.

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update falcosecurity
helm upgrade --install falcosidekick falcosecurity/falcosidekick \
  --version 0.14.0 --namespace falco --create-namespace \
  --values falcosidekick-values.yaml
helm upgrade --install falco falcosecurity/falco \
  --version 9.1.0 --namespace falco \
  --values falco-values.yaml
```

Falcosidekick chart의 appVersion 표기와 기본 image tag가 다르므로 예제는 image.tag를 2.35.0으로 명시합니다. 출력 credential Secret과 Prometheus Operator CRD는 먼저 준비합니다. Secret이 없으면 해당 Pod가 시작되지 않을 수 있습니다. 실습에서 알림·metrics 연동을 사용하지 않으면 관련 설정을 끕니다.

```yaml
driver:
  kind: modern_ebpf
metrics:
  enabled: true
serviceMonitor:
  create: true
falcosidekick:
  enabled: false
falco:
  json_output: true
  json_include_output_property: true
  http_output:
    enabled: true
    url: http://falcosidekick.falco.svc:2801
customRules:
  documentation-rules.yaml: "- macro: doc_spawned\n  condition: evt.type in (execve,\
    \ execveat) and evt.res = SUCCESS\n- macro: doc_container\n  condition: container.id\
    \ != host\n- rule: Documentation shell execution\n  desc: Observe successful shell\
    \ process execution in a container; not proof of compromise.\n  condition: doc_spawned\
    \ and doc_container and proc.name in (bash, sh, dash, zsh)\n  output: Shell process\
    \ observed (proc=%proc.name command=%proc.cmdline container=%container.id)\n \
    \ priority: NOTICE\n  tags:\n  - documentation\n  - process\n- rule: Documentation\
    \ service account token read\n  desc: Observe read access to the default projected\
    \ service account token path; legitimate\n    clients also read it.\n  condition:\
    \ evt.type in (open, openat, openat2) and evt.is_open_read\n    = true and fd.num\
    \ >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/\n\
    \  output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)\n\
    \  priority: NOTICE\n  tags:\n  - documentation\n  - credential_access\n"
```


이 구성은 별도 릴리스 `falcosidekick`의 ClusterIP Service에 HTTP로 전송합니다. 같은 namespace라는 사실만으로 통신이 인증되거나 암호화되지 않습니다. 실제 위협 모델에 따라 접근 정책·TLS/mTLS를 구성하고, 해당 endpoint에 노드/Falco가 접근 가능한지 확인합니다. Falco 설정은 json_output·http_output 같은 snake_case입니다. 예전 jsonOutput·httpOutput과 제거된 grpc 설정은 0.44.1 schema를 통과하지 못합니다.

### Falco 규칙 구조

다음 규칙은 필요한 macro를 자체 정의합니다. 기본 ruleset의 같은 이름을 덮어쓰지 않도록 별도 이름을 사용합니다. 기존 기본 규칙을 수정하려면 해당 Falco/rules 버전의 override 문법을 확인하세요.

```yaml
- macro: doc_spawned
  condition: evt.type in (execve, execveat) and evt.res = SUCCESS
- macro: doc_container
  condition: container.id != host
- rule: Documentation shell execution
  desc: Observe successful shell process execution in a container; not proof of compromise.
  condition: doc_spawned and doc_container and proc.name in (bash, sh, dash, zsh)
  output: Shell process observed (proc=%proc.name command=%proc.cmdline container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - process
- rule: Documentation service account token read
  desc: Observe read access to the default projected service account token path; legitimate
    clients also read it.
  condition: evt.type in (open, openat, openat2) and evt.is_open_read
    = true and fd.num >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/
  output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - credential_access
```


Falco 0.44.1은 enter event 제거 이후 evt.dir 조건을 deprecated로 경고합니다. 위 예제는 성공한 exec와 읽기 이벤트를 직접 조건으로 사용합니다. 서비스 계정 token 읽기는 정상 Kubernetes client에서도 발생하므로 “무단 접근”으로 단정하지 않습니다. 애플리케이션별 baseline·승인된 binary·Pod identity와 함께 판단합니다.

### 커스텀 규칙 작성

| 패턴 | 가능한 신호 | 반드시 확인할 한계 |
|---|---|---|
| 채굴 의심 | 알려진 프로세스 이름, pool/stratum 문자열, 비정상 자원 사용 | 이름 변경·정상 계산 작업·오탐 가능 |
| 리버스 셸 의심 | shell argv의 연결 문자열, 비정상 외부 연결 | exec 이벤트의 fd.name을 실제 연결 증거로 해석하지 않음 |
| 권한 상승 | credential 변화, SUID 설정, capability 사용 | user.uid/proc.uid/proc.suid의 의미와 성공 여부를 함께 확인 |
| 컨테이너 탈출 의심 | namespace/host 경로 접근, 비정상 mount | nsenter 또는 /.dockerenv 문자열만으로 탈출 성공을 증명하지 못함 |

규칙 parser 통과는 실제 탐지율 검증이 아닙니다. 합성/승인된 실습 이벤트, 정상 워크로드, metadata 누락, drop counter를 포함해 평가하고 단계적으로 적용합니다. 명령 인자·파일명·로그에는 비밀이 포함될 수 있으므로 출력 범위·보존·접근 권한도 제한합니다.

### Falco 알림 설정

```yaml
config:
  existingSecret: falcosidekick-output-credentials
  slack:
    minimumpriority: warning
  pagerduty:
    minimumpriority: critical
  aws:
    region: ap-northeast-2
    cloudwatchlogs:
      loggroup: /falco/alerts
      logstream: documentation
      minimumpriority: warning
  elasticsearch:
    minimumpriority: warning
    checkcert: true
webui:
  enabled: false
serviceMonitor:
  enabled: true
image:
  tag: 2.35.0
```


`falcosidekick-output-credentials`는 같은 namespace의 기존 Secret입니다. chart는 envFrom으로 이를 읽습니다. 승인된 비밀 관리 방식으로 SLACK_WEBHOOKURL, PAGERDUTY_ROUTINGKEY, ELASTICSEARCH_HOSTPORT/USERNAME/PASSWORD 등 실제로 사용할 출력의 환경 변수를 제공합니다. `${ELASTIC_PASSWORD}` 문자열을 Helm values에 쓴다고 shell 치환이 일어나지 않습니다. 비밀을 Git·명령줄·리뷰 로그에 남기지 않습니다.

AWS 설정은 config.aws 하위입니다. EKS workload identity와 대상 log group/stream 등 필요한 IAM 작업·리소스를 제한하고 credential 해석 경로를 확인합니다. minimumpriority는 emergency/alert/critical/error/warning/notice/informational/debug 체계이며 `high`가 아닙니다. 출력별 활성화 조건, 재시도와 실패 metrics도 확인합니다. Web UI는 예제에서 비활성화했습니다.

<span id="tetragon-설치"></span>
<span id="tracingpolicy-기본-구조"></span>
<span id="프로세스-모니터링"></span>

## Tetragon

### Tetragon 개요

Tetragon은 Cilium CNI와 별도로 설치할 수 있는 eBPF 관찰·강제 도구입니다. 기본 process_exec/exit 이벤트와 TracingPolicy로 추가한 hook을 구분합니다. `kernel hook → selector → Post/지원 action → JSON·gRPC·metrics` 경로를 사용하며, Kubernetes CRD 자체가 커널에서 실행되는 것은 아닙니다.

```bash
helm repo add cilium https://helm.cilium.io
helm repo update cilium
helm upgrade --install tetragon cilium/tetragon \
  --version 1.7.1 --namespace kube-system --values tetragon-values.yaml
```

```yaml
tetragon:
  enableProcessCred: true
  enableProcessNs: true
```


Operator/CRD 준비와 대상 노드의 커널·BTF·capability를 확인합니다. Helm render는 hook 부착 성공을 검증하지 않습니다. namespace 범위 예제는 demo-app namespace의 워크로드만 대상으로 하지만 사용하는 리소스·hook에 따른 실제 범위를 확인해야 합니다.

### 파일 접근 모니터링

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-file-observe
  namespace: demo-app
spec:
  kprobes:
  - call: security_file_permission
    syscall: false
    args:
    - index: 0
      type: file
    - index: 1
      type: int
    selectors:
    - matchArgs:
      - index: 0
        operator: Prefix
        values:
        - /etc/shadow
        - /root/.ssh/
      - index: 1
        operator: Mask
        values:
        - '4'
      matchActions:
      - action: Post
```


`security_file_permission(struct file *, int mask)`의 두 번째 인자는 MAY_READ=4, MAY_WRITE=2 권한 mask입니다. 인자가 하나인 security_file_open에 “index 1 = open flags”를 붙이면 같은 의미가 아닙니다. open의 O_WRONLY=1/O_RDWR=2와 permission mask도 혼동하지 않습니다. 이 hook만으로 mmap·truncate 등 모든 파일 변경을 감시하지 못합니다.

### 네트워크 모니터링

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-outbound-observe
  namespace: demo-app
spec:
  kprobes:
  - call: tcp_connect
    syscall: false
    args:
    - index: 0
      type: sock
    selectors:
    - matchArgs:
      - index: 0
        operator: DPort
        values:
        - '22'
        - '4444'
        - '5555'
      matchActions:
      - action: Post
```


tcp_connect는 TCP 연결 시도를 관찰합니다. 해당 포트라는 이유만으로 악성 연결이나 정책 차단이라고 판단하지 않습니다. DNS 이름·응답을 분석하려면 UDP 53 연결 시도만으로 충분하지 않으며 별도 DNS 관측 경로가 필요합니다.

### 런타임 강제 (Enforcement)

처음에는 Post/monitor 모드로 정상 동작과 오탐을 확인합니다. Sigkill은 signal 전송이며, 선택한 hook 위치·커널 동작에 따라 이미 발생한 부작용을 되돌리지 못합니다. syscall/LSM 반환값 override는 지원되는 함수·커널 설정·오류 반환값을 확인해야 합니다. 모든 kprobe에서 임의 반환값 변경이 가능하지 않습니다.

실행 파일 이름·argv 문자열만으로 모든 채굴·리버스 셸을 차단한다는 예제는 사용하지 않습니다. 특히 execve의 argv는 문자열 하나가 아니라 포인터 배열입니다. 해당 유형을 string 인자 하나로 읽는 정책은 의도한 전체 명령줄 검사가 아닙니다. 프로세스 이벤트의 argument 필터와 kernel action을 구분하고, 운영에 적용할 강제 정책은 제한된 namespace에서 승인된 테스트로 검증합니다.

### Tetragon CLI 사용

```bash
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents -o json
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact --namespace production --process curl
# 저장된 합성 이벤트를 로컬에서 필터링할 수도 있습니다.
tetra getevents -o json --namespace demo-app < events.jsonl
```

DaemonSet exec는 선택된 Pod/노드의 agent에 연결합니다. 이를 전체 클러스터 이벤트 집계라고 해석하지 않습니다. 저장된 JSON을 stdin으로 전달하는 필터만 이번 검토에서 실행했습니다. tetra tracingpolicy modify도 1.7.1 구현상 gRPC client를 만들므로 오프라인 검증 명령으로 사용하지 않았습니다.

<span id="기능-비교표"></span>
<span id="사용-사례별-권장"></span>

## Falco vs Tetragon 비교

| 선택 기준 | Falco | Tetragon |
|---|---|---|
| 정책 | event 조건식·ruleset | kernel hook·selector·action |
| 일반 사용 | 경보·저장소 연계 중심 탐지 | process 가시성과 명시적 hook 강제 |
| 운영 확인 | driver/plugin/runtime metadata, dropped events | BTF/hook 지원, policy 범위, 부작용 |
| 성능 평가 | 실제 workload로 CPU·메모리·event drop 측정 | 같은 조건으로 측정; eBPF만으로 우열 단정 금지 |

두 도구를 함께 설치하는 것이 항상 최선은 아닙니다. 수집 중복·노드 권한·비용·운영 복잡도와 필요한 강제 범위를 기준으로 선택합니다.

## Kubernetes 감사 로깅

### 감사 정책 구성

다음은 **자체 관리형 Kubernetes API server**의 정책 예제입니다. EKS에서는 AWS가 관리하는 audit policy를 이 YAML로 교체하지 않습니다. EKS control-plane audit log를 활성화하고 CloudWatch 접근·보존·암호화를 설정합니다.

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages:
- RequestReceived
rules:
- level: Metadata
  resources:
  - group: ''
    resources:
    - secrets
    - serviceaccounts/token
- level: Metadata
  resources:
  - group: ''
    resources:
    - pods/exec
    - pods/attach
    - pods/portforward
- level: Request
  resources:
  - group: rbac.authorization.k8s.io
    resources:
    - roles
    - rolebindings
    - clusterroles
    - clusterrolebindings
  verbs:
  - create
  - update
  - patch
  - delete
- level: Metadata
```


Secret과 serviceaccounts/token의 Request/RequestResponse는 자격 증명 본문을 로그에 남길 수 있어 Metadata로 제한합니다. 정책은 첫 번째 일치 규칙을 적용하므로 민감 리소스 규칙을 앞에 둡니다. system:anonymous 요청만으로 모든 인증 실패를 식별하지 못하며 audit stage·responseStatus·인증 로그를 함께 확인합니다. exec audit은 세션 내부 명령 전체를 기록하는 터미널 녹화가 아닙니다.

### EKS 감사 로그 분석

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name, responseStatus.code
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

이것은 CloudWatch Logs Insights 쿼리이며 Bash 명령이 아닙니다. 403은 거부 응답이고 승인된 읽기는 별도로 분류합니다. 로그 활성화 이후의 수집 상태와 retention을 확인합니다.

<span id="암호화폐-채굴-탐지"></span>
<span id="리버스-셸-탐지"></span>
<span id="권한-상승-탐지"></span>

## 런타임 위협 탐지 패턴

Seccomp는 허용 syscall 범위를 제한하지만 거부가 항상 프로세스 종료인 것은 아닙니다. 프로파일 action에 따라 ERRNO 반환·종료·통지 등이 달라집니다. RuntimeDefault는 runtime의 프로파일이며 Pod에서 명시하거나 kubelet seccompDefault 설정을 확인합니다. Kubernetes 1.27 이상이라는 이유만으로 모든 Pod에 자동 적용되지 않습니다.

AppArmor는 해당 노드의 지원·프로파일 로드가 필요합니다. complain 모드는 일반 위반을 기록하지만 명시적 deny 규칙은 차단할 수 있습니다. readOnlyRootFilesystem은 container securityContext에 설정하며 writable volume·네트워크·메모리상의 악성 행위까지 막지 않습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: runtime-security-demo
  namespace: demo-app
  labels:
    app: runtime-security-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_APPROVED_VERSION
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 64Mi
```


GuardDuty Runtime Monitoring의 현재 EKS 지원 범위는 EC2 노드와 EKS Auto Mode이며 EKS Hybrid Nodes·EKS Fargate는 지원하지 않습니다. OS·커널·CPU architecture·agent 버전과 coverage 상태를 공식 표에서 확인합니다. 탐지 기능을 활성화했다고 모든 노드가 healthy coverage라는 뜻은 아닙니다.

Hubble의 `--verdict DROPPED`는 drop을 보여주며 모든 drop이 NetworkPolicy 거부인 것은 아닙니다. drop reason과 정책 verdict를 함께 확인합니다.

<span id="포렌식-컨테이너-사용"></span>

## 인시던트 대응

### Pod 격리 절차

표준 NetworkPolicy의 allow는 합집합입니다. ingress/egress 목록이 빈 정책을 추가해도 다른 정책이 허용한 연결을 덮어쓰는 deny가 되지 않습니다. app label로 선택하면 같은 애플리케이션의 여러 Pod를 함께 선택할 수 있습니다.

1. 대상 namespace·Pod UID·node·owner와 기존 네트워크 정책을 확인합니다.
2. 승인된 격리 수단을 선택합니다. CNI의 명시적 deny 정책이나 기존 allow 변경을 사용할 경우 정확한 대상과 영향·복구 경로를 검토합니다.
3. 기존 연결과 새 연결을 실제로 시험합니다. hostNetwork·node 트래픽·CNI 제약도 확인합니다.
4. 증거를 보호하고, 격리·중단·복구에 대한 incident 기록을 남깁니다.

### 증거 수집과 포렌식

```bash
#!/usr/bin/env bash
# Authorized read-only Kubernetes API collection. Sensitive output stays in a private directory.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  printf 'Usage: %s NAMESPACE POD OUTPUT_DIRECTORY\n' "$0" >&2
  exit 2
fi
namespace=$1
pod_name=$2
evidence_dir=$3
if [[ ! $namespace =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || [[ ! $pod_name =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]]; then
  printf 'Invalid namespace or pod name\n' >&2
  exit 2
fi
umask 077
mkdir -- "$evidence_dir"
kubectl get pod "$pod_name" -n "$namespace" -o json > "$evidence_dir/pod.json"
kubectl describe pod "$pod_name" -n "$namespace" > "$evidence_dir/describe.txt"
kubectl logs "$pod_name" -n "$namespace" --all-containers=true --timestamps=true > "$evidence_dir/logs.txt"
# Previous logs may not exist. Record this separately instead of calling collection complete silently.
if ! kubectl logs "$pod_name" -n "$namespace" --all-containers=true --previous=true --timestamps=true > "$evidence_dir/previous-logs.txt" 2> "$evidence_dir/previous-logs-error.txt"; then
  printf 'Previous logs unavailable; inspect previous-logs-error.txt\n' >&2
fi
(
  cd -- "$evidence_dir"
  sha256sum -- pod.json describe.txt logs.txt previous-logs.txt previous-logs-error.txt > SHA256SUMS
)
printf 'API evidence written to %s. This is not a memory or filesystem snapshot.\n' "$evidence_dir"
```


이 스크립트는 API에서 Pod 정보·로그를 수집하고 checksum을 기록합니다. 실제 Kubernetes 호출은 이번 검토에서 실행하지 않았으며 subprocess test double로 실패 처리·0700 출력 디렉터리를 검증했습니다. Pod spec과 로그에도 비밀·개인정보가 있을 수 있으므로 승인된 보관소와 접근 정책을 사용합니다.

새 forensic Pod가 같은 node나 대상 process namespace를 공유한다고 가정하지 않습니다. hostPath /proc, SYS_PTRACE, NET_ADMIN은 높은 권한이므로 필요한 경우에만 승인된 절차로 사용합니다. emptyDir는 영구 증거 보관소가 아닙니다. ephemeral container의 `/`를 tar로 묶는 것은 자동으로 대상 container filesystem snapshot이 되지 않습니다.

<span id="falco-→-elasticsearch"></span>
<span id="prometheus-grafana-대시보드"></span>

<span id="siemsoar-통합"></span>

## SIEM/SOAR 통합

ServiceMonitor의 namespace·selector·port와 실제 Service를 대조합니다. Falco chart는 metrics Service를, Falcosidekick은 HTTP port의 metrics를 노출합니다. Falcosidekick chart의 ServiceMonitor는 monitoring.coreos.com/v1 API가 존재할 때만 렌더링됩니다.

```promql
sum by (priority) (rate(falcosecurity_falcosidekick_falco_events_total[5m]))
```

이 metric은 Falcosidekick 2.35.0 수신 이벤트 counter입니다. 원래 예제의 falco_events_total을 모든 구성의 공통 이름으로 사용하지 않습니다. counter 누적값과 시간 구간 발생률을 구분하고 실제 scrape label·reset·출력 실패·누락 데이터를 확인합니다. 경보를 Slack/PagerDuty/SIEM에 연결할 때 합성 전송 테스트도 수신자의 동의와 운영 절차에 따라 실행합니다.

<span id="권장-사항"></span>

## 요약

로컬 검증: Falco 규칙 2개와 config schema 4개 사례, Tetragon JSON 필터 3개와 CRD 2개, Helm 차트 3종, 증거 수집 script 4개 실패/성공 사례를 확인했습니다. 커널 hook 부착·탐지율·실제 차단·GuardDuty coverage·Kubernetes audit/CloudWatch 수집·외부 알림은 실행하지 않았습니다.

## 참고 자료

- [Falco Kubernetes installation](https://falco.org/docs/setup/kubernetes/)
- [Falco 0.44.1 configuration](https://github.com/falcosecurity/falco/blob/0.44.1/falco.yaml)
- [Falcosidekick 2.35.0 configuration](https://github.com/falcosecurity/falcosidekick/blob/2.35.0/config_example.yaml)
- [Tetragon tracing policies](https://tetragon.io/docs/concepts/tracing-policy/)
- [Tetragon enforcement](https://tetragon.io/docs/concepts/enforcement/)
- [Tetragon 1.7.1 file monitoring](https://github.com/cilium/tetragon/blob/v1.7.1/examples/quickstart/file_monitoring.yaml)
- [Kubernetes audit](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [AppArmor](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [EKS control-plane logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [GuardDuty EKS runtime requirements](https://docs.aws.amazon.com/guardduty/latest/ug/prereq-runtime-monitoring-eks-support.html)
- [MITRE ATT&CK Containers](https://attack.mitre.org/matrices/enterprise/containers/)
