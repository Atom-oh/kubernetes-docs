# eBPF 기초와 Kubernetes 활용

> **지원 버전**: 프로그램별 커널/BTF/헬퍼 요구사항 및 도구/Kubernetes 호환성 표 확인
> **마지막 업데이트**: 2026년 9월 11일

eBPF는 Linux 커널 내에서 샌드박스화된 프로그램을 실행할 수 있게 해주는 혁신적인 기술입니다. 이 문서에서는 eBPF의 기본 개념부터 Kubernetes 환경에서의 활용까지 전반적인 내용을 다룹니다.

## 목차

* [1. eBPF 소개](#1-ebpf-소개)
* [2. eBPF 아키텍처](#2-ebpf-아키텍처)
* [3. eBPF 프로그램 유형](#3-ebpf-프로그램-유형)
* [4. eBPF 개발 도구](#4-ebpf-개발-도구)
* [5. eBPF와 Kubernetes 네트워킹](#5-ebpf와-kubernetes-네트워킹)
* [6. eBPF 기반 관찰성](#6-ebpf-기반-관찰성)
* [7. eBPF 기반 보안](#7-ebpf-기반-보안)
* [8. eBPF 실전 활용 예제](#8-ebpf-실전-활용-예제)
* [9. eBPF 제한 사항과 주의점](#9-ebpf-제한-사항과-주의점)
* [10. 다음 단계](#10-다음-단계)

## 실습 환경 설정

이 문서의 예제를 따라하기 위해서는 다음과 같은 환경이 필요합니다.

### 필수 환경
- 각 예제에 필요한 BTF/헬퍼/연결 유형을 지원하는 유지 관리 중인 배포판 커널
- bpftool, bcc-tools
- Kubernetes 클러스터 (선택 사항)

bpftrace 예제는 공식 0.27 언어 문법(args.field)을 기준으로 검토했습니다. 배포판 패키지가 더 오래되면 설치된 버전의 문법/기능을 확인합니다. tracepoint 필드는 `bpftrace -lv` 또는 tracefs의 format 파일로 검증하며 함수 kprobe/uprobes는 커널/라이브러리 버전과 아키텍처에 종속됩니다. 실제 trace/attach는 수행하지 않았습니다.

### 환경 설정

```bash
# Ubuntu/Debian에서 필요한 패키지 설치
sudo apt-get update
sudo apt-get install -y bpfcc-tools python3-bpfcc bpftrace
# Install bpftool for this distribution/kernel separately:
# Debian provides the bpftool package; Ubuntu uses matching linux-tools packages.

# 커널 버전 확인
uname -r

# eBPF 기능 지원 확인
sudo bpftool feature probe kernel
```

---

## 1. eBPF 소개

### 1.1 eBPF란 무엇인가?

**eBPF(extended Berkeley Packet Filter)**는 Linux 커널 내에서 안전하게 사용자 정의 프로그램을 실행할 수 있게 해주는 기술입니다. 원래 네트워크 패킷 필터링을 위해 설계되었던 BPF를 확장하여, 이제는 네트워킹, 보안, 추적, 성능 분석 등 다양한 영역에서 활용됩니다.

> **핵심 개념**: eBPF를 사용하면 커널 소스 코드를 수정하거나 커널 모듈을 로드하지 않고도 커널의 동작을 확장하고 관찰할 수 있습니다.

![사용자 공간에서 작성된 eBPF 프로그램이 컴파일과 커널 로드를 거쳐, 커널 공간에서 검증기와 JIT 컴파일을 통과한 뒤 네트워크 패킷·시스템 콜·함수 호출·트레이스포인트 등 다양한 이벤트 훅 포인트에서 실행되는 흐름을 보여주는 워크플로 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-0.html)

### 1.2 전통적인 BPF에서 eBPF로의 진화

**초기 BPF (1992년)**:
- UC 버클리에서 개발
- 네트워크 패킷 캡처 및 필터링 전용
- 2개의 32비트 레지스터
- Linux classic BPF의 일반적 한도는4096개이며 모든 역사적 BPF 구현의 규격은 아님

**eBPF (2014년~)**:
- 64비트 아키텍처 지원
- 11개의 레지스터
- 맵(Maps)을 통한 상태 저장
- 다양한 훅 포인트 지원
- JIT 컴파일을 통한 네이티브 성능

| 특성 | 전통적 BPF | eBPF |
|------|-----------|------|
| 레지스터 | 2개 (32비트) | 11개 (64비트) |
| 명령어 제한 | 일반적 Linux 한도4096 | 커널/권한별 상이; 프로그램 크기와 검증 복잡도는 별개 |
| 맵 지원 | 없음 | 다양한 맵 유형 |
| 용도 | 패킷 필터링 | 범용 커널 프로그래밍 |
| 호출 기능 | 없음 | 헬퍼 함수, BPF-to-BPF 호출 |
| 영속 상태 | 영속 맵 없음(한 실행 내 scratch 저장소는 존재) | 맵을 통해 가능 |

### 1.3 eBPF가 혁신적인 이유

eBPF는 다음과 같은 이유로 혁신적입니다:

1. **커널 수정 없는 기능 확장**: 커널 소스 코드를 변경하지 않고도 커널 기능을 확장
2. **안전한 실행**: 검증기가 정의된 메모리/제어 흐름 안전 속성을 검사
3. **높은 성능**: JIT 컴파일로 네이티브 코드 수준의 성능
4. **동적 로딩**: 재부팅 없이 프로그램 로드/언로드 가능
5. **프로덕션 안정성**: 실행 경계 검사가 위험을 줄이지만 정책 정확성, 커널/JIT 버그 및 운영 영향은 별도 검증 필요

![기존 커널 모듈 개발 방식은 커널 버전별 재컴파일과 시스템 불안정 위험을 동반하지만 eBPF 방식은 런타임 로드와 검증을 거쳐 검증을 수행하지만 정책 정확성과 호스트 안정성을 별도로 검증해야 함을 설명하는 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-1.html)

### 1.4 eBPF vs 커널 모듈 비교

| 측면 | eBPF | 커널 모듈 |
|------|------|----------|
| **안전성** | 검증 모델 범위의 안전성 검사 | 커널 크래시 가능 |
| **이식성** | CO-RE는 호환되는 커널 타입을 재배치하며 헬퍼/훅/의미/BTF 제약은 남음 | 커널 버전별 재컴파일 필요 |
| **로딩** | 동적 로드/언로드 | insmod/rmmod 필요 |
| **권한** | CAP_BPF/CAP_SYS_ADMIN 및 훅별 추가 권한 | root 권한 필요 |
| **디버깅** | 제한적 | 전체 커널 디버깅 가능 |
| **성능** | JIT 컴파일로 최적화 | 네이티브 성능 |
| **기능 범위** | 정해진 훅 포인트만 | 무제한 |
| **개발 난이도** | 상대적으로 쉬움 | 높은 전문성 필요 |

---

## 2. eBPF 아키텍처

### 2.1 eBPF 실행 흐름

![C/Rust로 작성된 eBPF 프로그램이 컴파일과 커널 로드, 검증기 통과를 거쳐 JIT 컴파일되고 이벤트 훅에 연결되어 실행된 뒤 맵에 데이터를 저장하고 사용자 공간에서 읽히는 절차를, 검증 실패 시 로드가 거부되는 분기와 함께 보여주는 순서도.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-2.html)

### 2.2 검증기 (Verifier)

검증기는 eBPF의 핵심 보안 메커니즘입니다. 프로그램이 커널에서 실행되기 전에 다음 사항을 검증합니다:

**검증 항목**:
- 종료/제한된 제어 흐름 검사; 지원 커널에서는 bounded loop 사용 가능
- 범위를 벗어난 메모리 접근 없음
- 초기화되지 않은 변수 사용 없음
- 올바른 헬퍼 함수 호출
- 프로그램 종료 보장

```c
// XDP fragments; compile as separate programs with linux/bpf.h and bpf_helpers.h.
SEC("xdp")
int bad_example(struct xdp_md *ctx) {
    unsigned char *data = (void *)(long)ctx->data;
    // No data_end check: the verifier cannot prove this packet byte exists.
    return data[0] == 0 ? XDP_DROP : XDP_PASS;
}

SEC("xdp")
int good_example(struct xdp_md *ctx) {
    unsigned char *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    if ((void *)(data + 1) > data_end)
        return XDP_PASS;
    return data[0] == 0 ? XDP_DROP : XDP_PASS;
}
```

### 2.3 JIT 컴파일러

JIT(Just-In-Time) 컴파일러는 eBPF 바이트코드를 네이티브 머신 코드로 변환합니다:

```bash
# JIT 컴파일러 상태 확인
cat /proc/sys/net/core/bpf_jit_enable

# JIT 컴파일러 활성화 (0: 비활성화, 1: 활성화, 2: 디버그 모드)
echo 1 | sudo tee /proc/sys/net/core/bpf_jit_enable
```

CONFIG_BPF_JIT_ALWAYS_ON을 사용하는 커널에서는 이 sysctl의 존재/변경 가능 여부가 다릅니다. 디버그 모드2는 커널 로그를 출력하므로 프로덕션 기본값으로 사용하지 않습니다.

**JIT 컴파일 이점**:
- 원문의 4~5배 향상 수치는 출처가 제시되지 않았으며 실제 차이는 프로그램/아키텍처/커널에 따라 다름
- 네이티브 CPU 명령어로 직접 실행
- 아키텍처별 최적화 적용

### 2.4 eBPF 맵 (Maps)

eBPF 맵은 커널과 사용자 공간 간 데이터를 공유하고 상태를 저장하는 데이터 구조입니다.

**주요 맵 유형**:

| 맵 유형 | 설명 | 사용 사례 |
|---------|------|----------|
| `BPF_MAP_TYPE_HASH` | 해시 테이블 | 키-값 저장, 연결 추적 |
| `BPF_MAP_TYPE_ARRAY` | 고정 크기 배열 | 인덱스 기반 접근, 설정 값 |
| `BPF_MAP_TYPE_PERF_EVENT_ARRAY` | 이벤트 배열 | 사용자 공간으로 이벤트 전송 |
| `BPF_MAP_TYPE_RINGBUF` | 링 버퍼 | 고성능 이벤트 스트리밍 |
| `BPF_MAP_TYPE_LRU_HASH` | LRU 해시 | 캐시, 자동 항목 제거 |
| `BPF_MAP_TYPE_PERCPU_ARRAY` | CPU별 배열 | 통계 수집의 CPU 간 경합 감소 |
| `BPF_MAP_TYPE_LPM_TRIE` | LPM 트라이 | IP 주소 매칭, 라우팅 |

```c
// 해시 맵 정의 예제
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);      // 키: 프로세스 ID
    __type(value, __u64);    // 값: 카운터
} packet_count SEC(".maps");
```

### 2.5 헬퍼 함수 (Helper Functions)

eBPF 프로그램은 커널이 제공하는 헬퍼 함수를 통해 커널 기능에 접근합니다.

**주요 헬퍼 함수**:

아래는 API 역할을 설명하는 축약 표기입니다. 실제 프로그램에서는 libbpf의 bpf_helpers.h를 포함하며 이 선언들을 재정의하지 않습니다. 헬퍼 사용 가능 여부는 프로그램 유형/커널에 따라 다릅니다.

```text
// 맵 조작
void *bpf_map_lookup_elem(void *map, const void *key);
long bpf_map_update_elem(void *map, const void *key, const void *value, u64 flags);
long bpf_map_delete_elem(void *map, const void *key);

// 시간 관련
u64 bpf_ktime_get_ns(void);  // 부팅 후 단조 시간(ns), suspend 제외; 실제 날짜/시각이 아님

// 패킷 조작
long bpf_skb_load_bytes(const void *skb, u32 offset, void *to, u32 len);
long bpf_xdp_adjust_head(struct xdp_md *xdp_md, int delta);

// 추적
long bpf_probe_read_kernel(void *dst, u32 size, const void *src);
long bpf_probe_read_user(void *dst, u32 size, const void *src);
long bpf_trace_printk(const char *fmt, u32 fmt_size, ...);

// 프로세스 정보
u64 bpf_get_current_pid_tgid(void);    // PID/TGID 획득
u64 bpf_get_current_uid_gid(void);     // UID/GID 획득
long bpf_get_current_comm(void *buf, u32 size);  // 프로세스 이름
```

### 2.6 프로그램 라이프사이클

![bpf()로 로드된 프로그램이 검증을 통과해 이벤트 훅에 연결되고 이벤트마다 반복 실행되다가 명시적 분리와 언로드로 종료되는 eBPF 프로그램의 생명주기를, 검증 실패 경로와 함께 보여주는 워크플로 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-3.html)

---

C 예제는 별도 프로그램/조각입니다. vmlinux.h 또는 필요한 UAPI 타입과 libbpf의 bpf_helpers.h, bpf_endian.h, bpf_tracing.h, bpf_core_read.h를 용도에 맞게 포함합니다. BPF_KPROBE/BPF_UPROBE는 올바른 대상 아키텍처 정의와 실제 attach 지점/ABI가 필요합니다. 로드/attach는 격리된 테스트 환경에서 검증해야 하며 이 감사에서는 수행하지 않았습니다. 경로 기반 LSM 예제는 읽기 오류에 fail-open하고 별칭/하드링크/다른 프로토콜까지 방어하지 않는 교육용입니다.

## 3. eBPF 프로그램 유형

### 3.1 XDP (eXpress Data Path)

XDP는 네트워크 드라이버 레벨에서 패킷을 처리하는 가장 빠른 방법입니다.

![NIC에 도착한 패킷이 XDP 프로그램의 판정에 따라 드롭, 커널 스택 전달, 같은 인터페이스로 반환, 다른 인터페이스로 리다이렉트, 에러 처리 중 하나의 경로로 분기하는 것을 보여주는 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-4.html)

**XDP 동작 모드**:
| 모드 | 설명 | 성능 |
|------|------|------|
| Native XDP | 지원 드라이버 수신 경로에서 실행 | 드라이버/워크로드에 따라 다름 |
| Offloaded XDP | 지원 NIC 하드웨어에서 실행 | 하드웨어/명령 제한 및 실제 측정 필요 |
| Generic XDP | 스택의 skb 기반 대체 경로 | 일반적으로 native보다 오버헤드 증가 |

```c
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

// Demonstration only: untagged, non-fragmented IPv4 TCP.
// VLAN, IPv6 and fragments pass through; this is not a complete firewall.
static __always_inline int packet_action(void *data, void *data_end) {
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end || eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end || ip->version != 4 || ip->ihl < 5)
        return XDP_PASS;
    __u32 ihl = (__u32)ip->ihl * 4;
    __u32 ip_len = bpf_ntohs(ip->tot_len);
    if ((void *)ip + ihl > data_end || ip_len < ihl || (void *)ip + ip_len > data_end)
        return XDP_PASS;
    if (ip->protocol != IPPROTO_TCP || (bpf_ntohs(ip->frag_off) & 0x3fffU))
        return XDP_PASS;
    if (ip_len < ihl + sizeof(struct tcphdr))
        return XDP_PASS;
    struct tcphdr *tcp = (void *)ip + ihl;
    if ((void *)(tcp + 1) > data_end || tcp->doff < 5)
        return XDP_PASS;
    __u32 tcp_len = (__u32)tcp->doff * 4;
    if (ihl + tcp_len > ip_len || (void *)tcp + tcp_len > data_end)
        return XDP_PASS;
    return tcp->dest == bpf_htons(8080) ? XDP_DROP : XDP_PASS;
}

SEC("xdp")
int xdp_drop_port(struct xdp_md *ctx) {
    return packet_action((void *)(long)ctx->data, (void *)(long)ctx->data_end);
}
char LICENSE[] SEC("license") = "GPL";
```

### 3.2 TC (Traffic Control)

TC 프로그램은 네트워크 스택의 트래픽 제어 계층에서 실행됩니다.

```bash
# TC 프로그램 연결 예제
set -e
: "${LAB_IFACE:?Select an isolated test veth interface, never a production interface}"
tc qdisc show dev "$LAB_IFACE"
# This assumes a fresh lab interface with no clsact qdisc.
sudo tc qdisc add dev "$LAB_IFACE" clsact
sudo tc filter add dev "$LAB_IFACE" ingress pref 49152 bpf da obj tc_prog.o sec classifier
sudo tc filter add dev "$LAB_IFACE" egress pref 49152 bpf da obj tc_prog.o sec classifier
# Cleanup only the filters created by this example, after the exercise:
# sudo tc filter del dev "$LAB_IFACE" ingress pref 49152
# sudo tc filter del dev "$LAB_IFACE" egress pref 49152
```

**TC vs XDP 비교**:
| 특성 | XDP | TC |
|------|-----|-----|
| 실행 위치 | 드라이버 레벨 | 네트워크 스택 |
| 성능 | 최고 | 높음 |
| SKB 접근 | 불가 | 가능 |
| 방향 | 수신만 | 송수신 모두 |
| 패킷 수정 | 제한적 | 자유로움 |

### 3.3 Kprobes/Uprobes

Kprobes와 Uprobes는 함수 호출을 동적으로 추적합니다.

```c
// Kprobe 예제: tcp_connect 함수 추적
SEC("kprobe/tcp_connect")
int BPF_KPROBE(trace_tcp_connect, struct sock *sk) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    // 목적지 IP 주소 획득
    u32 daddr = BPF_CORE_READ(sk, __sk_common.skc_daddr);
    u16 dport = BPF_CORE_READ(sk, __sk_common.skc_dport);

    bpf_printk("PID %d connecting to %pI4:%d\n", pid, &daddr, bpf_ntohs(dport));
    return 0;
}

// Uprobe 예제: malloc 함수 추적
// The userspace loader must select the real libc path, PID and malloc symbol.
SEC("uprobe")
int BPF_UPROBE(trace_malloc, size_t size) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    bpf_printk("PID %d malloc(%zu)\n", pid, size);
    return 0;
}
```

### 3.4 Tracepoints

Tracepoints는 커널에 미리 정의된 정적 추적점입니다.

```bash
# 사용 가능한 tracepoints 확인
sudo ls /sys/kernel/tracing/events/

# 특정 카테고리의 tracepoints
sudo ls /sys/kernel/tracing/events/sched/
sudo ls /sys/kernel/tracing/events/syscalls/
```

```c
// Tracepoint 예제: 프로세스 시작 추적
SEC("tracepoint/sched/sched_process_exec")
int handle_exec(struct trace_event_raw_sched_process_exec *ctx) {
    char comm[16];
    bpf_get_current_comm(&comm, sizeof(comm));

    u32 pid = bpf_get_current_pid_tgid() >> 32;
    bpf_printk("Process started: %s (PID: %d)\n", comm, pid);

    return 0;
}
```

### 3.5 LSM (Linux Security Module) BPF

LSM BPF는 보안 정책을 동적으로 적용합니다.

```c
// LSM BPF 예제: 파일 열기 제한
SEC("lsm/file_open")
int BPF_PROG(restrict_file_open, struct file *file, int ret) {
    if (ret != 0)
        return ret;

    char path[256];
    if (bpf_d_path(&file->f_path, path, sizeof(path)) < 0)
        return 0;  // Demo fails open on unresolved paths; not a complete access policy.

    // /etc/shadow 접근 차단
    if (bpf_strncmp(path, 11, "/etc/shadow") == 0)
        return -EACCES;

    return 0;
}
```

### 3.6 Socket Filter

소켓 레벨에서 패킷을 필터링합니다.

```c
// Socket Filter 예제
SEC("socket")
int socket_filter(struct __sk_buff *skb) {
    // IPv4 패킷만 허용
    if (skb->protocol != bpf_htons(ETH_P_IP))
        return 0;  // 드롭

    return skb->len;  // 패킷 길이 반환 (허용)
}
```

### 3.7 Cgroup 프로그램

컨테이너의 리소스와 네트워크를 제어합니다.

```c
// Cgroup 소켓 프로그램 예제: 외부 연결 차단
SEC("cgroup/connect4")
int restrict_connect(struct bpf_sock_addr *ctx) {
    // 로컬 네트워크가 아닌 연결 차단
    __u32 dst = bpf_ntohl(ctx->user_ip4);

    // 10.0.0.0/8 대역만 허용
    if ((dst & 0xff000000U) != 0x0a000000U)
        return 0;  // 연결 거부

    return 1;  // 연결 허용
}
```

---

## 4. eBPF 개발 도구

### 4.1 bpftool

bpftool은 BPF 프로그램/맵을 관리합니다. 실습에서 만든 맵만 수정하며 실제 CNI/보안 맵 변경은 실행 중인 워크로드에 영향을 줍니다. 아래 hex 예제는 앞의 맵과 일치하는 little-endian u32 키/u64 값을 가정합니다.

```bash
# 로드된 eBPF 프로그램 목록
sudo bpftool prog list

# 프로그램 상세 정보
sudo bpftool prog show id <ID>

# 프로그램 덤프 (바이트코드)
sudo bpftool prog dump xlated id <ID>

# JIT 컴파일된 코드 덤프
sudo bpftool prog dump jited id <ID>

# 맵 목록
sudo bpftool map list

# 맵 내용 조회
sudo bpftool map dump id <MAP_ID>

# 맵에 값 추가
sudo bpftool map update id <MAP_ID> key hex 01 00 00 00 value hex ff 00 00 00 00 00 00 00

# 커널의 eBPF 기능 확인
sudo bpftool feature probe kernel

# BTF (BPF Type Format) 정보
sudo bpftool btf list
```

### 4.2 bpftrace

bpftrace는 DTrace 스타일의 고수준 추적 언어입니다.

```bash
# 설치
sudo apt-get install -y bpftrace

# 시스템 콜 카운트
sudo bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'

# 프로세스별 읽기 바이트 수
sudo bpftrace -e 'tracepoint:syscalls:sys_exit_read /args.ret > 0/ { @bytes[comm] = sum(args.ret); }'

# 파일 열기 추적
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s opened %s\n", comm, str(args.filename)); }'

# TCP 연결 추적
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s -> %s\n", ntop(((struct sock *)arg0)->__sk_common.skc_rcv_saddr), ntop(((struct sock *)arg0)->__sk_common.skc_daddr)); }'

# 지연 시간 히스토그램
sudo bpftrace -e 'kprobe:vfs_read { @start[tid] = nsecs; } kretprobe:vfs_read /@start[tid]/ { @ns = hist(nsecs - @start[tid]); delete(@start[tid]); }'
```

**유용한 bpftrace 원라이너**:

```bash
# CPU 사용량 상위 프로세스
sudo bpftrace -e 'profile:hz:99 { @[comm] = count(); }'

# 블록 I/O 지연 시간
sudo biolatency-bpfcc 1 10  # Maintained request correlation; avoids dev/sector collisions

# 새 프로세스 추적
sudo bpftrace -e 'tracepoint:sched:sched_process_exec { printf("%-10d %-16s\n", pid, comm); }'

# 메모리 할당 추적
sudo bpftrace -e 'tracepoint:kmem:kmalloc { @bytes = hist(args.bytes_alloc); }'
```

### 4.3 BCC (BPF Compiler Collection)

BCC는 BPF C 컴파일/로딩을 제공하며 일반적으로 Python 추적 도구에 BPF C를 포함하여 사용합니다.

```bash
# 설치
sudo apt-get install -y bpfcc-tools python3-bpfcc

# 포함된 도구들
dpkg -L bpfcc-tools | head -40
```

**주요 BCC 도구**:

| 도구 | 설명 |
|------|------|
| `execsnoop` | 새로운 프로세스 실행 추적 |
| `opensnoop` | 파일 열기 추적 |
| `biolatency` | 블록 I/O 지연 시간 |
| `tcpconnect` | TCP 연결 추적 |
| `tcpaccept` | TCP 수신 연결 추적 |
| `tcpretrans` | TCP 재전송 추적 |
| `runqlat` | CPU 실행 큐 지연 시간 |
| `profile` | CPU 프로파일링 |
| `funccount` | 함수 호출 횟수 |
| `trace` | 범용 함수 추적 |

```bash
# 사용 예제
sudo execsnoop-bpfcc    # 프로세스 실행 추적
sudo tcpconnect-bpfcc   # TCP 연결 추적
sudo biolatency-bpfcc   # 디스크 I/O 지연 시간
sudo profile-bpfcc -F 99 10  # 10초간 CPU 프로파일링
```

### 4.4 libbpf와 CO-RE

libbpf는 eBPF 프로그램 로딩을 위한 C 라이브러리이며, CO-RE(Compile Once, Run Everywhere)를 지원합니다.

**CO-RE의 장점**:
- 컴파일된 eBPF 프로그램을 다양한 커널 버전에서 실행
- BTF(BPF Type Format)를 사용한 구조체 재배치
- 커널 헤더 의존성 감소

```c
// Independent tracing program. Generate vmlinux.h from the target kernel's BTF.
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx) {
    const char *filename = (const char *)BPF_CORE_READ(ctx, args[1]);
    char fname[256];
    if (bpf_probe_read_user_str(fname, sizeof(fname), filename) < 0)
        return 0;
    __u32 tgid = bpf_get_current_pid_tgid() >> 32;
    bpf_printk("TGID %u opened: %s", tgid, fname);
    return 0;
}
char LICENSE[] SEC("license") = "GPL";
```

**BTF 생성 및 확인**:

```bash
# BTF 지원 확인
ls /sys/kernel/btf/vmlinux

# vmlinux.h 생성 (CO-RE 개발용)
bpftool btf dump file /sys/kernel/btf/vmlinux format c > vmlinux.h

# 프로그램의 BTF 정보 확인
bpftool prog show id <ID> --pretty
```

---

## 5. eBPF와 Kubernetes 네트워킹

### 5.1 Cilium: eBPF 기반 CNI

Cilium은 eBPF를 활용한 가장 대표적인 Kubernetes CNI(Container Network Interface)입니다.

![Cilium Agent가 Kubernetes API로부터 받은 설정을 eBPF 데이터플레인으로 내려보내고, XDP·TC·소켓 프로그램이 각각 DDoS 방어, 네트워크 정책, 로드 밸런싱, 소켓 레벨 라우팅 기능을 구현하는 과정을 보여주는 아키텍처 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-5.html)

#### kube-proxy 대체

Cilium은 지원되는 구성에서 kube-proxy를 대체할 수 있습니다. 아래는 새 흐름의 백엔드 선택을 단순화한 그림이며 기존 흐름은 연결 추적을 사용할 수 있습니다. 실제 라우팅/터널링/NAT는 데이터 경로 설정에 따릅니다.

**기존 kube-proxy (iptables 모드)**:
```
패킷 → Netfilter → iptables 규칙 평가 → DNAT → 라우팅
```

**Cilium eBPF 모드**:
```
새 흐름 → eBPF 백엔드 조회 → 구성된 라우팅/터널링/NAT
```

```bash
# New, isolated self-managed lab only: configure the cluster for the selected
# CNI/proxy mode before bootstrap. Do not delete kube-proxy on a live cluster.
helm repo add cilium https://helm.cilium.io
helm repo update cilium
: "${CILIUM_CHART_VERSION:?Select a chart compatible with this Kubernetes/kernel}"
: "${CILIUM_VALUES_FILE:?Provide reviewed IPAM/routing/platform values}"
: "${API_SERVER_IP:?Set a directly reachable API endpoint, not the Service IP}"
: "${API_SERVER_PORT:?Set the API endpoint port}"
helm install cilium cilium/cilium --version "$CILIUM_CHART_VERSION" \
  --namespace kube-system -f "$CILIUM_VALUES_FILE" \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost="$API_SERVER_IP" --set k8sServicePort="$API_SERVER_PORT"
cilium status --wait
# Existing clusters require the Cilium migration procedure and a tested rollback plan.

```

#### 네트워크 정책

Cilium은 L3/L4에 eBPF를 사용하며 HTTP/L7 정책에는 Envoy 등 지원되는 프록시 처리가 필요합니다. DNS 관찰에는 DNS 프록시가 사용됩니다. Hubble의 HTTP/DNS 레코드는 해당 관찰 설정이 필요합니다.

```yaml
# Cilium 네트워크 정책 예제
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-http-only
spec:
  endpointSelector:
    matchLabels:
      app: web
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "80"
              protocol: TCP
          rules:
            http:
              - method: GET
                path: "/api/.*"
```

#### 로드 밸런싱

```yaml
# Cilium LoadBalancer 서비스 예제
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    lbipam.cilium.io/ips: "192.168.1.100"
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

위 요청 IP는 관리자가 소유한 CiliumLoadBalancerIPPool에 포함되어야 합니다. LB IPAM은 주소 할당만 담당하며 외부 도달성에는 BGP/L2 광고 또는 별도 로드 밸런서 구성이 필요합니다.

### 5.2 Calico eBPF 모드

Calico는 eBPF 데이터플레인을 지원합니다. 아래 패치는 호환되는 기존 Calico Operator 설치를 전제로 한 전환 절차의 일부입니다. 직접 API 접근을 구성하고 라우팅/복구를 검증한 뒤 Service 프록시를 변경합니다.

```bash
# Calico eBPF 모드 활성화
kubectl patch installation.operator.tigera.io default --type merge -p '{"spec":{"calicoNetwork":{"linuxDataplane":"BPF"}}}'
```

**Calico eBPF 모드 특징**:
- 소스 IP 보존
- 직접 서버 리턴 (DSR) 지원
- 호스트 엔드포인트 정책
- 별도로 구성하고 지원되는 경우 WireGuard 암호화; eBPF 선택만으로 자동 활성화되지 않음

### 5.3 성능 비교: iptables vs eBPF

| 측면 | iptables | eBPF |
|------|----------|------|
| **확장성** | O(n) - 서비스 수에 비례 | 해시 조회 평균 O(1); 맵 종류에 따라 다름 |
| **지연 시간** | 규칙 구조/워크로드에 따라 다름 | 맵 종류/워크로드/데이터 경로에 따라 다름 |
| **CPU 사용량** | 워크로드/설정에 따라 다름 | 워크로드/설정에 따라 다름 |
| **업데이트** | 현대 kube-proxy는 변경된 Service/엔드포인트 규칙 갱신 가능 | 구현에 따른 맵 갱신 |
| **관찰성** | 제한적 | Hubble 통합 |
| **메모리** | 규칙/엔드포인트/연결 추적 상태 | 맵/엔드포인트/연결 추적 상태 |

**벤치마크 결과** (1000개 서비스 기준):

원문에서 제시한 아래 수치는 테스트 출처, 하드웨어, 커널/CNI 버전 및 측정 방법이 제공되지 않았습니다. 재실행하지 않았으며 현재 성능이나 일반적 개선율로 사용할 수 없습니다. 비교를 재현하려면 원본 방법과 환경이 필요합니다.

```
| 지표              | iptables    | eBPF      | 개선율    |
|------------------|-------------|-----------|----------|
| 연결 설정 시간    | 2.5ms       | 0.3ms     | 8.3x     |
| CPU 사용량       | 15%         | 3%        | 5x       |
| 메모리 사용량    | 256MB       | 32MB      | 8x       |
| 초당 연결 수     | 50,000      | 250,000   | 5x       |
```

```bash
# Cilium 상태 확인
cilium status

# eBPF 맵 확인
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg bpf lb list
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg bpf ct list global

# 네트워크 정책 상태
kubectl get ciliumnetworkpolicies,ciliumclusterwidenetworkpolicies -A
```

---

## 6. eBPF 기반 관찰성 (Observability)

eBPF는 시스템과 애플리케이션의 동작을 심층적으로 관찰할 수 있게 해줍니다. 기존의 에이전트 기반 모니터링과 달리, eBPF는 커널 레벨에서 데이터를 수집하여 더 낮은 오버헤드로 더 풍부한 정보를 제공합니다.

### 6.1 Hubble: Cilium 네트워크 관찰성

Hubble은 Cilium 네트워크 관찰성을 제공합니다. 호환되는 Hubble CLI와 Relay를 준비하고 CLI 예제 전에 port-forward를 연결합니다. L7 관찰에는 해당 프록시 구성이 필요합니다.

![Cilium Agent가 eBPF 네트워크/정책 이벤트와 지원되는 DNS/HTTP 프록시 관찰을 결합하고 Hubble Observer가 이를 수집하여 Hubble Relay를 거쳐 UI와 CLI로 제공하는 과정을 보여주는 아키텍처 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-6.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-6.html)

```bash
# Use the installed, reviewed chart version; this is not a chart-version upgrade.
: "${CILIUM_CHART_VERSION:?Set the installed compatible chart version}"
# Hubble 설치
helm upgrade cilium cilium/cilium --version "$CILIUM_CHART_VERSION" \
  --namespace kube-system \
  --reuse-values \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# 먼저 별도 터미널에서 cilium hubble port-forward를 실행합니다.
# Hubble CLI 사용
hubble observe --pod my-pod
hubble observe --namespace default
hubble observe --protocol http
hubble observe --verdict DROPPED

# 특정 서비스 간 트래픽 관찰
hubble observe --from-pod default/frontend --to-pod default/backend

# 네트워크 플로우 실시간 모니터링
hubble observe -f --type trace

# 서비스 맵 생성
# Service maps are provided by Hubble UI; use the UI port-forward below.
```

**Hubble UI 접속**:

```bash
# 포트 포워딩
kubectl port-forward -n kube-system svc/hubble-ui 12000:80

# 브라우저에서 http://localhost:12000 접속
```

### 6.2 Pixie: 자동 계측 관찰성

Pixie는 eBPF를 사용하여 애플리케이션 코드 수정 없이 자동으로 텔레메트리를 수집합니다.

**Pixie 특징**:
- 자동 프로토콜 파싱 (HTTP, gRPC, MySQL, PostgreSQL, Kafka 등)
- 서비스 맵 자동 생성
- 분산 추적
- CPU 프로파일링
- 동적 로깅

```bash
# Pixie 설치
px deploy

# Pixie CLI 쿼리 예제
# HTTP 요청 지연 시간
px run px/http_data

# 서비스 간 트래픽
px run px/service_stats

# 느린 요청 분석
px run px/slow_http_requests --help
# Use the parameters advertised by the installed script bundle.

# Pod 리소스 사용량
px run px/pods
```

**PxL (Pixie Query Language) 예제**:

```python
# 느린 HTTP 요청 찾기
import px

df = px.DataFrame(table='http_events', start_time='-5m')
df.namespace = df.ctx['namespace']
df.pod = df.ctx['pod']
df = df[df.latency > 100000000]  # 100ms 이상
df = df.groupby(['namespace', 'pod', 'req_path']).agg(
    count=('latency', px.count),
    avg_latency=('latency', px.mean),
    latency_quantiles=('latency', px.quantiles)
)
df.p99_latency_ns = px.pluck_float64(df.latency_quantiles, 'p99')
px.display(df)
```

### 6.3 Coroot: "No-Code" 모니터링

Coroot는 eBPF를 사용하여 에이전트/저장소/권한/데이터 소스를 구성한 후 지원하는 애플리케이션을 자동 관찰합니다.

```bash
# Helm으로 Coroot 설치
helm repo add coroot https://coroot.github.io/helm-charts
# The old coroot/coroot chart is deprecated; use the operator and CE resource chart.
: "${COROOT_OPERATOR_VERSION:?Select a reviewed operator chart version}"
: "${COROOT_CE_VERSION:?Select a compatible CE chart version}"
helm install coroot-operator coroot/coroot-operator -n coroot --create-namespace \
  --version "$COROOT_OPERATOR_VERSION"
helm install coroot coroot/coroot-ce -n coroot --version "$COROOT_CE_VERSION"
```

**Coroot 기능**:
- 서비스 자동 발견
- 의존성 맵 자동 생성
- SLO 모니터링
- 이상 탐지
- 근본 원인 분석

### 6.4 Kepler: 에너지 소비 모니터링

Kepler의 초기 버전은 eBPF를 사용했지만 **0.10.0부터 전면 재작성**되어 호스트 /proc·/sys 읽기와 RAPL/powercap 및 CPU 사용량 기반 전력 배분을 사용합니다. CAP_BPF가 더 이상 필요하지 않습니다. 따라서 현재 Kepler를 eBPF 계측의 필수 사례로 설명하면 부정확합니다. 0.9 이하 코드는 frozen legacy이며 현재 메트릭/배포 방법과 구분합니다.

하드웨어/VM에서 전력 센서가 제공되는지 먼저 확인합니다. 컨테이너/Pod 값은 직접 전력계를 달아 측정한 값이 아니라 노드 에너지의 추정 배분이며 중첩 RAPL zone을 합산하면 중복 계산할 수 있습니다. GPU/HWMon/플랫폼 전력 지원은 버전별 실험 기능 범위를 확인합니다.

```bash
: "${KEPLER_CHART_VERSION:?Select a reviewed current Kepler chart}"
helm install kepler oci://quay.io/sustainable_computing_io/charts/kepler \
  --version "$KEPLER_CHART_VERSION" --namespace kepler --create-namespace
kubectl get pods -n kepler
# Run port-forward in a separate terminal; then query metrics from this machine.
kubectl port-forward -n kepler service/kepler 28282:28282
# curl --fail http://localhost:28282/metrics | grep kepler_node_cpu_watts
```

현재 CPU 메트릭 예: `kepler_node_cpu_joules_total`, `kepler_container_cpu_joules_total`, `kepler_pod_cpu_watts`. 실제 수집 가능 범위와 zone 레이블을 확인합니다.

### 6.5 기존 에이전트 vs eBPF 계측 비교

5–15%와 <1%는 원문의 출처 없는 수치를 보존한 것입니다. 검증한 오버헤드 범위가 아니며 eBPF도 사용자 공간 에이전트/버퍼/프로토콜 파서가 필요합니다. 모든 기존 에이전트가 코드 수정을 요구하거나 모든 eBPF 도구가 전체 시스템을 완전히 관찰하는 것은 아닙니다.

| 측면 | 기존 에이전트 | eBPF 계측 |
|------|-------------|-----------|
| **오버헤드** | 높음 (5-15%) | 낮음 (<1%) |
| **코드 수정** | SDK/에이전트 모델에 따라 다름 | 지원 데이터 소스에서는 대체로 불필요 |
| **커버리지** | 계측/에이전트에 따라 다름 | 지원 훅/프로토콜/가시성 범위; 자동으로 전체를 보장하지 않음 |
| **배포** | 앱/노드/수집기 형태에 따라 다름 | 보통 노드 에이전트; 앱 호환성은 여전히 필요 |
| **권한** | 에이전트별로 다름 | 프로그램/훅별 capability와 호스트 접근 필요 |
| **데이터 깊이** | 앱/호스트 계측에 따라 다름 | 커널 및 지원되는 사용자 공간 probe |
| **프로토콜 지원** | 도구별로 다름 | 지원되는 파서/라이브러리/가시성에서만 자동 파싱 |

![기존 방식은 애플리케이션에 SDK나 에이전트를 심어 메트릭을 수집하지만, eBPF 방식은 애플리케이션 코드 변경 없이 커널에서 eBPF 프로그램으로 직접 관측 데이터를 모니터링 백엔드로 전달한다는 것을 비교하는 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-7.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-7.html)

---

## 7. eBPF 기반 보안

### 7.1 Tetragon: 런타임 보안

Tetragon은 Cilium 프로젝트에서 제공하는 eBPF 기반 런타임 보안 솔루션입니다.

![TracingPolicy CRD로 정의된 정책에 따라 Tetragon Agent의 eBPF 센서가 프로세스, 네트워크, 파일 활동을 추적하고 위반 시 프로세스 킬, 네트워크 차단, 파일 접근 거부로 Post 관찰, Signal 프로세스 종료, 지원되는 Override 작업 거부를 구분하여 적용하는 과정을 보여주는 아키텍처 다이어그램.](../.gitbook/assets/ko-basics-05-ebpf-fundamentals-8.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-basics-05-ebpf-fundamentals-8.html)

```bash
# Tetragon 설치
helm repo add cilium https://helm.cilium.io
: "${TETRAGON_CHART_VERSION:?Select a compatible reviewed chart version}"
helm install tetragon cilium/tetragon -n kube-system --version "$TETRAGON_CHART_VERSION"

# 이벤트 관찰
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f | tetra getevents -o compact
```

ebpf-lab 네임스페이스와 app=ebpf-demo 테스트 Pod를 준비합니다. 아래 정책은 호스트 전체에 SIGKILL을 적용하지 않는 관찰 전용 Post 예제입니다. 예방적 차단은 지원되는 LSM/Override 동작을 별도 테스트해야 합니다.

**TracingPolicy 예제**:

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: sensitive-file-access
  namespace: ebpf-lab
spec:
  kprobes:
  - call: security_file_open
    syscall: false
    args:
    - index: 0
      type: file
    selectors:
    - matchArgs:
      - index: 0
        operator: Prefix
        values:
        - /etc/shadow
        - /etc/passwd
        - /etc/sudoers
      matchActions:
      - action: Post
  podSelector:
    matchLabels:
      app: ebpf-demo
```

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: observe-outbound
  namespace: ebpf-lab
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
        operator: NotDAddr
        values:
        - 10.0.0.0/8
      matchActions:
      - action: Post
  podSelector:
    matchLabels:
      app: ebpf-demo
```

### 7.2 Falco: eBPF 기반 이상 탐지

Falco는 CNCF 프로젝트로, eBPF를 사용하여 런타임 이상 동작을 탐지합니다.

```bash
# Falco 설치 (eBPF 드라이버)
helm repo add falcosecurity https://falcosecurity.github.io/charts
# Save the following Falco rule examples as ./ebpf-lab-rules.yaml before installation.
: "${FALCO_CHART_VERSION:?Select a compatible reviewed chart version}"
helm install falco falcosecurity/falco --version "$FALCO_CHART_VERSION" \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf \
  --set-file 'customRules.ebpf-lab-rules\.yaml=./ebpf-lab-rules.yaml'
```

**Falco 규칙 예제**:

```yaml
# /etc/shadow 읽기 탐지
- rule: eBPF lab read sensitive file
  desc: Detect reading of sensitive files
  condition: >
    open_read and
    fd.name in (/etc/shadow, /etc/sudoers) and
    not proc.name in (systemd, sudo, login)
  output: >
    Sensitive file opened (file=%fd.name user=%user.name
    process=%proc.name container=%container.name)
  priority: WARNING

# 컨테이너에서 셸 실행 탐지
- rule: eBPF lab shell in container
  desc: Detect shell execution in container
  condition: >
    spawned_process and
    container and
    proc.name in (bash, sh, zsh, dash) and
    proc.pname != containerd-shim
  output: >
    Shell spawned in container (container=%container.name
    shell=%proc.name parent=%proc.pname)
  priority: NOTICE

# 권한 상승 탐지
- rule: eBPF lab privilege escalation
  desc: Detect privilege escalation attempts
  condition: >
    spawned_process and
    proc.name in (sudo, su, doas) and
    container
  output: >
    Privilege escalation attempt (user=%user.name
    command=%proc.cmdline container=%container.name)
  priority: WARNING
```

### 7.3 seccomp-bpf: 시스템 콜 필터링

seccomp 필터는 일반 eBPF 프로그램 헬퍼/맵이 아닌 classic BPF 사용자 API를 사용합니다. 컨테이너 런타임이 OCI JSON 프로필을 해석하여 syscall 필터를 구성합니다.

```yaml
# Kubernetes Pod에서 seccomp 프로필 적용
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault  # 또는 Localhost
  containers:
    - name: app
      image: nginx:1.30.4
```

**커스텀 seccomp 프로필**:

아래는 x86-64 최소 예제의 **형식 설명**이며 NGINX/일반 애플리케이션에 적용할 수 있는 프로필이 아닙니다. 기본 RuntimeDefault를 사용하고, custom allowlist는 실제 아키텍처/런타임/워크로드의 syscall을 관찰하여 회귀 테스트한 후 배포합니다. 광범위한 mount/reboot/module/BPF 허용 목록을 안전한 기본값으로 사용하지 않습니다.

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": [
    "SCMP_ARCH_X86_64"
  ],
  "syscalls": [
    {
      "names": [
        "read",
        "write",
        "exit",
        "exit_group",
        "rt_sigreturn"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

### 7.4 LSM BPF: 동적 보안 정책

LSM BPF는 Linux Security Module과 eBPF를 결합하여 동적으로 보안 정책을 적용합니다.

```c
// LSM BPF 예제: 실행 파일 제한
SEC("lsm/bprm_check_security")
int BPF_PROG(restrict_exec, struct linux_binprm *bprm, int ret) {
    if (ret != 0)
        return ret;
    char filename[256];
    if (bpf_probe_read_kernel_str(filename, sizeof(filename), bprm->filename) < 0)
        return 0;  // Demo fails open on read error; define a real policy explicitly.

    // /tmp에서 실행 차단
    if (bpf_strncmp(filename, 5, "/tmp/") == 0)
        return -EPERM;

    return 0;
}

// LSM BPF 예제: 네트워크 소켓 제한
SEC("lsm/socket_connect")
int BPF_PROG(restrict_connect, struct socket *sock, struct sockaddr *address, int addrlen, int ret) {
    if (ret != 0)
        return ret;

    if (addrlen < sizeof(struct sockaddr_in) || address->sa_family != AF_INET)
        return 0;  // This example handles IPv4 only.
    struct sockaddr_in *addr = (struct sockaddr_in *)address;

    // 특정 포트 연결 차단
    if (bpf_ntohs(addr->sin_port) == 6666)
        return -EACCES;

    return 0;
}
```

---

## 8. eBPF 실전 활용 예제

### 8.1 bpftrace로 시스템 성능 분석하기

**TCP 연결 추적**:

```bash
# TCP 연결 추적
sudo bpftrace -e '
tracepoint:sock:inet_sock_set_state /args.protocol == 6 && args.newstate == 1/ {
    if (args.family == 2) {
        printf("IPv4 %s:%d -> %s:%d established\n", ntop(args.saddr), args.sport, ntop(args.daddr), args.dport);
    } else if (args.family == 10) {
        printf("IPv6 %s:%d -> %s:%d established\n", ntop(args.saddr_v6), args.sport, ntop(args.daddr_v6), args.dport);
    }
}'
```

**시스템 콜 지연 시간 분석**:

```bash
# read 시스템 콜 지연 시간 히스토그램
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_read { @start[tid] = nsecs; }
tracepoint:syscalls:sys_exit_read /@start[tid]/ {
    @latency = hist((nsecs - @start[tid]) / 1000);
    delete(@start[tid]);
}'
```

**디스크 I/O 분석**:

```bash
# 블록 I/O 요청 추적
sudo bpftrace -e '
tracepoint:block:block_rq_issue {
    printf("%s %s %d\n",
        comm,
        str(args.rwbs),
        args.nr_sector / 2);
}'

# I/O 지연 시간 히스토그램
sudo biolatency-bpfcc 1 10
```

### 8.2 Cilium Hubble로 네트워크 흐름 관찰

```bash
# 실시간 네트워크 플로우 관찰
hubble observe -f

# 특정 네임스페이스 트래픽
hubble observe --namespace production

# HTTP 트래픽만 필터링
hubble observe --protocol http

# 드롭된 패킷 분석
hubble observe --verdict DROPPED

# DNS 쿼리 추적
hubble observe --protocol dns

# 특정 Pod 간 트래픽
hubble observe --from-pod default/frontend --to-pod default/backend

# JSON 출력으로 상세 분석
hubble observe --namespace default -o json | jq '.flow.destination.pod_name'

# 보관된 흐름 관찰 이벤트 수이며 고유 연결 수나 전체 트래픽 통계가 아닙니다.
# Relay는 Hubble 인스턴스별로 지정 수만큼 반환합니다.
hubble observe --namespace default --last 1000 -o jsonpb | \
  jq -r '.flow | "\(.source.pod_name // .source.identity) -> \(.destination.pod_name // .destination.identity)"' | \
  sort | uniq -c | sort -rn | head -20
```

### 8.3 Tetragon으로 프로세스 보안 모니터링

```bash
# Tetragon 이벤트 실시간 모니터링
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f | \
  tetra getevents -o compact

# 프로세스 실행 이벤트만 필터링
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f | \
  tetra getevents -o compact --event-types PROCESS_EXEC

# 특정 네임스페이스 이벤트
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f | \
  tetra getevents -o json | jq 'select(.process_exec.process.pod.namespace == "default")'
```

**파일 접근 모니터링 정책**:

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: file-access-monitor
  namespace: ebpf-lab
spec:
  kprobes:
  - call: security_file_open
    syscall: false
    return: false
    args:
    - index: 0
      type: file
    selectors:
    - matchArgs:
      - index: 0
        operator: Prefix
        values:
        - /etc/
        - /var/run/secrets/
      matchActions:
      - action: Post
  podSelector:
    matchLabels:
      app: ebpf-demo
```

### 8.4 eBPF를 사용한 지연 시간 분석

**함수, 연결 수립 및 이름 해석 지연 시간**:

```bash
# libc read() 함수 실행 시간이며 HTTP 요청 지연 시간 메트릭이 아님
sudo funclatency-bpfcc 'c:read' -i 1

# TCP 핸드셰이크 지연 시간
sudo tcpconnlat-bpfcc  # Active TCP connection establishment latency

# DNS 조회 지연 시간
sudo gethostlatency-bpfcc  # libc name-resolution latency; includes cache/NSS work
```

아래는 x86-64 glibc 경로 예시입니다. 대상 프로세스/라이브러리 경로를 먼저 확인하며 컨테이너 마운트 네임스페이스는 다를 수 있습니다. malloc/tcp_sendmsg 실행 시간은 함수 지연이며 전체 요청 지연이 아닙니다.

**애플리케이션 성능 분석 스크립트**:

```bash
#!/bin/bash
# app-latency-analysis.bt

sudo bpftrace -e '
BEGIN {
    printf("Tracing application latency... Hit Ctrl-C to end.\n");
}

uprobe:/usr/lib/x86_64-linux-gnu/libc.so.6:malloc {
    @malloc_start[tid] = nsecs;
}

uretprobe:/usr/lib/x86_64-linux-gnu/libc.so.6:malloc /@malloc_start[tid]/ {
    @malloc_ns = hist(nsecs - @malloc_start[tid]);
    delete(@malloc_start[tid]);
}

kprobe:tcp_sendmsg {
    @send_start[tid] = nsecs;
}

kretprobe:tcp_sendmsg /@send_start[tid]/ {
    @tcp_send_ns = hist(nsecs - @send_start[tid]);
    delete(@send_start[tid]);
}

END {
    printf("\n=== Malloc Latency ===\n");
    print(@malloc_ns);
    printf("\n=== TCP Send Latency ===\n");
    print(@tcp_send_ns);
}
'
```

---

## 9. eBPF 제한 사항과 주의점

### 9.1 기술적 제한 사항

| 제한 사항 | 값 | 설명 |
|----------|-----|------|
| **스택 크기** | 512 bytes | 로컬 변수 저장 공간 제한 |
| **명령어 제한** | 권한/커널별 상이 | 프로그램 길이와 검증 중 처리 명령 수 한도는 별개이며 upstream 복잡도 한도는100만 |
| **최대 중첩 호출** | 8 레벨 | BPF-to-BPF 함수 호출 깊이 |
| **맵 항목 수** | 맵 유형별 상이 | 메모리 제한에 따름 |
| **프로그램 크기** | 커널/검증기/JIT 한도 | 맵 종류로 결정되지 않음 |

**스택 크기 제한 우회**:

```c
// 잘못된 예: 스택 크기 초과
int bad_function(void *ctx) {
    volatile char buffer[1024] = {};  // 스택 크기 초과!
    buffer[0] = 1;
    return buffer[1023];
}

// 올바른 예: 맵 사용
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, char[1024]);
} buffer_map SEC(".maps");

int good_function(void *ctx) {
    __u32 key = 0;
    char *buffer = bpf_map_lookup_elem(&buffer_map, &key);
    if (!buffer)
        return 0;
    // buffer 사용
    return 0;
}
```

### 9.2 루프 제한

eBPF 검증기는 프로그램 종료를 보장하기 위해 루프를 제한합니다.

```c
// n의 작은 상한을 증명할 수 없다면 검증 복잡도 문제가 될 수 있음.
for (int i = 0; i < n; i++) {  // 런타임 값도 증명 가능한 상한이 있을 수 있음
    // ...
}

// 검증기가 허용: 제한된 루프 (커널 5.3+)
#pragma clang loop unroll(disable)
for (int i = 0; i < 100 && i < n; i++) {  // 상한 명시
    // ...
}

// 검증기가 허용: 컴파일 타임 언롤링
#pragma unroll
for (int i = 0; i < 10; i++) {
    // ...
}

// bpf_loop 헬퍼 사용 (커널 5.17+)
static int callback(u32 index, void *ctx) {
    // 반복 작업
    return 0;
}

int main_prog(void *ctx) {
    bpf_loop(1000, callback, NULL, 0);
    return 0;
}
```

### 9.3 커널 버전 호환성

| 기능 | 최소 커널 버전 |
|------|--------------|
| 기본 eBPF | 3.18 |
| XDP | 4.8 |
| BTF | 4.18 |
| CO-RE | BTF와 호환 libbpf/기능 필요; 단일 최소 버전으로 보장 불가 |
| BPF 링 버퍼 | 5.8 |
| BPF 루프 | 5.3 |
| LSM BPF | 5.7 |
| bpf_loop 헬퍼 | 5.17 |

```bash
# 커널 버전 확인
uname -r

# eBPF 기능 지원 확인
sudo bpftool feature probe kernel

# BTF 지원 확인
ls /sys/kernel/btf/vmlinux
```

### 9.4 디버깅의 어려움

eBPF 프로그램 디버깅은 전통적인 방법과 다릅니다:

**디버깅 방법**:

```c
// bpf_printk (디버그용, 성능 영향)
bpf_printk("value = %d\n", value);

```

```bash
# tracefs 마운트/위치는 배포판별로 확인합니다.
sudo cat /sys/kernel/tracing/trace_pipe
```

```bash
# 검증기 로그 확인 (로드 실패 시)
sudo bpftool prog load my_prog.o /sys/fs/bpf/my_prog -d

# 프로그램 통계 확인
sudo bpftool -j prog show id <ID> | jq '.run_time_ns, .run_cnt'
# Runtime statistics require kernel.bpf_stats_enabled or a BPF stats FD; disabled by default and adds overhead.

# 맵 내용 덤프
sudo bpftool map dump id <MAP_ID>
```

### 9.5 권한 요구사항

| 권한 | 용도 |
|------|------|
| `CAP_BPF` | eBPF 프로그램 로드 (커널 5.8+) |
| `CAP_SYS_ADMIN` | 전통적인 eBPF 권한 |
| `CAP_PERFMON` | 성능 모니터링 이벤트 연결 |
| `CAP_NET_ADMIN` | XDP/TC 프로그램 연결 |

```bash
# 권한 확인
capsh --print

# 특정 권한으로 프로그램 실행
sudo setcap cap_bpf,cap_perfmon+ep ./my_bpf_loader
```

아래 Pod는 capability 필드 예시이며 실행 검증한 완성 에이전트가 아닙니다. 커널/BTF/프로그램 유형, seccomp의 bpf/perf_event_open 허용, LSM/lockdown, hostPath 마운트와 소유권, PSS 및 필요한 RBAC를 따로 확인합니다. capability만 추가해도 모든 프로그램이 로드되는 것은 아닙니다.

**Kubernetes에서의 권한 설정**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ebpf-pod
spec:
  containers:
    - name: ebpf-container
      image: my-ebpf-app
      securityContext:
        capabilities:
          add:
            - BPF
            - PERFMON
            - NET_ADMIN
        privileged: false
      volumeMounts:
        - name: bpf-maps
          mountPath: /sys/fs/bpf
        - name: debug
          mountPath: /sys/kernel/debug
  volumes:
    - name: bpf-maps
      hostPath:
        path: /sys/fs/bpf
    - name: debug
      hostPath:
        path: /sys/kernel/debug
```

### 9.6 보안 고려사항

eBPF는 강력한 도구이지만 보안 위험도 존재합니다:

- **정보 유출**: 민감한 데이터에 접근 가능
- **DoS 공격**: 성능 저하 유발 가능
- **권한 상승**: 잘못된 설정 시 취약점 발생 가능

**보안 모범 사례**:

```bash
# Inspect first. 0 enables unprivileged bpf(); 1 disables until reboot; 2 disables reversibly.
sysctl kernel.unprivileged_bpf_disabled
# On a kernel supporting value 2, disable only if currently enabled.
if [ "$(sysctl -n kernel.unprivileged_bpf_disabled)" = 0 ]; then
  sudo sysctl -w kernel.unprivileged_bpf_disabled=2
fi
# Inspect the real JIT-hardening setting; choose changes through host configuration management.
sysctl net.core.bpf_jit_harden
```

---

## 10. 다음 단계

### 10.1 관련 퀴즈

이 문서의 내용을 확인하려면 다음 퀴즈를 풀어보세요:

- [eBPF 기초 퀴즈](../quizzes/basics/05-ebpf-fundamentals-quiz.md)

### 10.2 심화 학습 자료

**공식 문서 및 리소스**:
- [eBPF.io](https://ebpf.io) - 공식 eBPF 문서
- [Cilium Documentation](https://docs.cilium.io) - Cilium 공식 문서
- [BPF Performance Tools](https://www.brendangregg.com/bpf-performance-tools-book.html) - Brendan Gregg의 BPF 성능 도구 책

**실습 환경**:
- [eBPF Tutorial](https://github.com/lizrice/learning-ebpf) - Liz Rice의 eBPF 튜토리얼
- [BCC Tutorial](https://github.com/iovisor/bcc/blob/master/docs/tutorial.md) - BCC 공식 튜토리얼
- [bpftrace Tutorial](https://github.com/iovisor/bpftrace/blob/master/docs/tutorial_one_liners.md) - bpftrace 원라이너 튜토리얼

**커뮤니티**:
- [eBPF Summit](https://ebpf.io/events/?conference=eBPF%20Summit) - 연례 eBPF 컨퍼런스
- [Cilium Slack](https://slack.cilium.io/) - Cilium 커뮤니티

### 10.3 관련 문서

이 문서와 관련된 심화 내용은 다음 문서를 참고하세요:

| 주제 | 문서 링크 | 설명 |
|------|----------|------|
| Cilium 소개 | [Cilium 개요](../networking/cilium/01-introduction.md) | eBPF 기반 CNI 소개 |
| eBPF 심층 분석 | [eBPF 기술 심층 분석](../networking/cilium/02-ebpf.md) | 고급 eBPF 기술 |
| 네트워킹 | [Cilium 네트워킹](../networking/cilium/03-networking.md) | eBPF 네트워킹 구현 |
| 보안 | [Cilium 보안](../networking/cilium/06-security-visibility.md) | eBPF 기반 보안 |
| Kubernetes 네트워킹 | [서비스와 네트워킹](../core/03-services-networking.md) | 기본 네트워킹 개념 |

### 10.4 실습 체크리스트

eBPF 학습을 위한 실습 체크리스트:

```
[ ] bpftool을 사용하여 로드된 eBPF 프로그램 확인
[ ] bpftrace로 시스템 콜 추적 실행
[ ] BCC 도구로 네트워크 트래픽 분석
[ ] Cilium 설치 및 Hubble로 네트워크 관찰
[ ] Tetragon으로 보안 이벤트 모니터링
[ ] 간단한 XDP 프로그램 작성 및 로드
```

---

## 요약

eBPF는 Linux 커널의 동작을 안전하게 확장하고 관찰할 수 있게 해주는 혁신적인 기술입니다. 이 문서에서 다룬 핵심 내용을 정리하면:

1. **eBPF 기본 개념**: 커널 내에서 안전하게 실행되는 샌드박스 프로그램
2. **아키텍처**: 검증기, JIT 컴파일러, 맵, 헬퍼 함수로 구성
3. **프로그램 유형**: XDP, TC, Kprobes, Tracepoints, LSM BPF 등
4. **개발 도구**: bpftool, bpftrace, BCC, libbpf
5. **Kubernetes 활용**: Cilium, Calico eBPF 모드로 고성능 네트워킹
6. **관찰성**: Hubble, Pixie, Coroot를 통한 깊은 시스템 관찰
7. **보안**: Tetragon, Falco, seccomp-bpf를 통한 런타임 보안
8. **제한 사항**: 스택 크기, 루프, 커널 버전 호환성 고려 필요

eBPF는 클라우드 네이티브 환경에서 네트워킹, 보안, 관찰성의 미래를 이끌어가는 핵심 기술입니다.

> Falco 규칙은 기본 ruleset의 open_read/open_write/spawned_process/container 매크로를 먼저 로드해야 합니다. 추가 규칙 파일을 배포하는 방법은 설치한 Helm 차트의 customRules/falco.rules_files 설정으로 확인합니다. Falco는 탐지/알림 엔진이며 규칙만으로 접근을 차단하지 않습니다. container/Kubernetes 메타데이터는 조회 지연으로 없을 수 있고 정상적인 서비스 계정 토큰 읽기도 탐지되므로 허용 조건을 테스트합니다.

## 검증 참고 자료

- https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html
- https://www.kernel.org/doc/html/latest/admin-guide/sysctl/net.html
- https://github.com/torvalds/linux/blob/master/include/linux/bpf.h
- https://github.com/torvalds/linux/blob/master/include/linux/filter.h
- https://github.com/torvalds/linux/blob/master/include/uapi/linux/bpf.h
- https://github.com/torvalds/linux/blob/master/kernel/bpf/syscall.c
- https://docs.kernel.org/bpf/prog_lsm.html
- https://docs.kernel.org/userspace-api/seccomp_filter.html
- https://github.com/torvalds/linux/blob/master/include/trace/events/sock.h
- https://github.com/bpftrace/bpftrace/blob/v0.27.0/docs/language.md
- https://github.com/bpftrace/bpftrace/blob/v0.27.0/docs/stdlib.md
- https://packages.debian.org/trixie/arm64/bpfcc-tools/filelist
- https://github.com/iovisor/bcc/blob/master/tools/tcpconnlat.py
- https://github.com/iovisor/bcc/blob/master/tools/gethostlatency.py
- https://github.com/libbpf/bpftool/blob/main/docs/bpftool-map.rst
- https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/kubeproxy-free.rst
- https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/lb-ipam.rst
- https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml
- https://github.com/cilium/cilium/blob/v1.20.1/hubble/cmd/observe/observe.go
- https://github.com/cilium/cilium/blob/v1.20.1/hubble/pkg/printer/printer_test.go
- https://github.com/cilium/tetragon/blob/main/docs/content/en/docs/concepts/enforcement/_index.md
- https://github.com/cilium/tetragon/blob/main/docs/content/en/docs/concepts/tracing-policy/selectors.md
- https://github.com/cilium/tetragon/blob/main/pkg/k8s/apis/cilium.io/v1alpha1/tracing_policy_types.go
- https://github.com/cilium/tetragon/blob/main/cmd/tetra/getevents/getevents.go
- https://github.com/cilium/tetragon/blob/main/examples/tracingpolicy/lsm_file_open.yaml
- https://github.com/cilium/tetragon/blob/main/install/kubernetes/tetragon/crds-yaml/cilium.io_tracingpoliciesnamespaced.yaml
- https://github.com/sustainable-computing-io/kepler/blob/main/README.md
- https://github.com/sustainable-computing-io/kepler/blob/main/docs/user/metrics.md
- https://github.com/coroot/helm-charts/blob/main/charts/coroot/Chart.yaml
- https://github.com/coroot/helm-charts/blob/main/charts/operator/Chart.yaml
- https://github.com/coroot/helm-charts/blob/main/charts/coroot-ce/Chart.yaml
- https://docs.px.dev/reference/pxl/udf/quantiles/
- https://github.com/pixie-io/pixie/blob/main/src/pixie_cli/pkg/cmd/run.go
- https://github.com/pixie-io/pixie/blob/main/src/pxl_scripts/px/http_data/data.pxl
- https://falco.org/docs/reference/rules/supported-fields/
- https://github.com/falcosecurity/charts/blob/master/charts/falco/values.yaml
- https://github.com/falcosecurity/rules/blob/main/rules/falco_rules.yaml
