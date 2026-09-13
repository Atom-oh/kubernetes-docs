# Pod 네트워크 실측 벤치마크 — 같은 노드·같은 AZ·다른 AZ, 그리고 DNS ndots

> **기록된 측정 환경**: Kubernetes 1.36 (Amazon EKS), Amazon VPC CNI v1.21.1, kube-proxy iptables 모드
> **측정일**: 2026년 9월 2일 · **마지막 업데이트**: 2026년 9월 12일

이 문서는 서울 리전 `fsi-demo-cluster`의 **2026년 9월 2일** 벤치마크 기록을 보존합니다. Pod 간 RTT, HTTP/gRPC 지연, iperf3 처리량과 DNS 쿼리 수를 다룹니다. 해당 실행에서는 AZ 간 경로의 지연이 더 컸지만 두 노드 간 경로의 처리량은 비슷했습니다. 모든 AZ 경로에서 같은 대역폭이 보장된다는 뜻은 아닙니다. 측정 1·2의 애플리케이션 트래픽은 Pod IP를 직접 사용했고, 측정 3은 그 비용 모델이며, 측정 4는 기존 `kube-dns` ClusterIP를 사용했습니다. DNS 10쿼리 결과는 당시 리졸버·search 목록·응답 순서에 한정됩니다. 과거 버전과 측정값은 유지했으며, 이번 감사에서 EKS 벤치마크를 다시 실행하거나 청구서를 검증하지는 않았습니다.

![ap-northeast-2a의 노드 A에 있는 클라이언트 Pod가 같은 노드의 서버 Pod, 같은 AZ 노드 B의 서버 Pod, ap-northeast-2b 노드 C의 서버 Pod와 통신하는 세 경로를 각 경로의 실측 RTT(0.040 / 0.339 / 0.544 ms)와 단일 플로우 Gbps(29.97 / 4.96 / 4.96)와 함께 보여주는 토폴로지 다이어그램.](../.gitbook/assets/ko-networking-06-pod-network-benchmark-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-networking-06-pod-network-benchmark-0.html)

그림은 당시 테스트 배치입니다. +0.21 ms는 해당 실행 간 차이이고, $4.47은 아래에서 설명하는 과거의 십진 GB 비용 모델입니다. 검증된 청구액이나 AZ 하나당 고정 비용이 아닙니다.

## TL;DR — 측정 결과 요약

1. **기록된 RTT**: 같은 노드 **0.040 ms** → 같은 AZ **0.339 ms** → 다른 AZ **0.544 ms**(ping 200회 평균). 두 노드 간 경로의 관측 차이는 +0.21 ms, 같은 노드 대비는 +0.50 ms였습니다.
2. **HTTP p50 / p99** (fortio, 100 qps, 커넥션 4개, keepalive, 60 s): 0.259 / 0.350 ms → 0.461 / 0.667 ms → 0.704 / 0.812 ms. 같은 사다리를 애플리케이션 관점에서 본 값입니다.
3. **기록된 대역폭**: 두 노드 간 경로 모두 단일 TCP 플로우 **4.96 Gbps**, 8개 플로우 **9.94 Gbps**였습니다. 일반적인 클러스터 배치 그룹 외부의 5 Gbps 단일 플로우 한도와 m5.xlarge의 10 Gbps 버스트 피크에 부합하지만, 다른 인스턴스 기능과 경로에는 다른 한도가 적용될 수 있습니다.
4. **같은 노드 Pod 간**: 단일 플로우 **29.97 Gbps**(클라이언트 프로세스 CPU 99.8%로 CPU 부하 가능성을 뒷받침), 8개 플로우 **48.15 Gbps**. 당시 VPC CNI 구성에서는 양쪽 Pod의 veth 경로와 호스트 네트워크 스택을 지나며 물리 NIC를 사용하지 않습니다.
5. **비용 모델**: 180초 AZ 간 전송량은 **223.4 십진 GB**였습니다. 원문의 페이로드 기반 모델은 송신·수신 양 끝에 각각 $0.01/GB를 적용해 **약 $4.47**로 추정하지만, 청구서를 확인한 값은 아닙니다. 180초 안에 1.25 Gbps 베이스라인으로 내려가는 현상은 관측되지 않았습니다.
6. **기록된 DNS**: 당시 glibc Pod의 `ndots:5`에서 `sts.ap-northeast-2.amazonaws.com`은 **10쿼리**(NXDOMAIN 8개), 웜 중앙값 **3.78 ms**였습니다. 끝점을 붙이면 **2쿼리** / 0.80 ms, `ndots:1`이면 2쿼리 / 0.54 ms였습니다. 이 시간은 표본값이지 보장값이 아닙니다.
7. **새 커넥션**: keepalive를 끄자 p50이 0.259 → 0.664, 0.461 → 1.079, 0.704 → **1.517 ms**로 변했습니다. TCP 연결 수립이 증가분에 기여하지만 핸드셰이크·소켓·애플리케이션 비용을 분리한 실험은 아닙니다.

## 테스트 환경

| 항목 | 값 |
|------|-----|
| 클러스터 | Amazon EKS `fsi-demo-cluster`, ap-northeast-2 (서울), 컨트롤 플레인 `v1.36.2-eks-bca9cf6`, AZ 2개(2a, 2b) 사용 |
| 노드 | Karpenter `system` NodePool이 이 테스트를 위해 새로 띄운 **m5.xlarge × 3** — 2a 클라이언트 노드, 2a 서버 노드, 2b 서버 노드. 4 vCPU, Intel Xeon Platinum 8175M @ 2.50GHz |
| 노드 OS | Amazon Linux 2023.12.20260817, 커널 `6.18.41-94.142.amzn2023.x86_64`, containerd 2.2.5, kubelet v1.36.3-eks-cb19647 |
| CNI | Amazon VPC CNI `v1.21.1-eksbuild.8` (+ network-policy-agent v1.3.4); `ENABLE_PREFIX_DELEGATION=false`, `ENABLE_POD_ENI=false`, `AWS_VPC_K8S_CNI_EXTERNALSNAT=false`, `NETWORK_POLICY_ENFORCING_MODE=standard`, `WARM_ENI_TARGET=1`, `WARM_IP_TARGET=3` |
| kube-proxy | `v1.35.3-eksbuild.5`, `mode: "iptables"` |
| CoreDNS | `v1.14.2-eksbuild.4`, 2 replicas — AZ마다 1개(`10.0.2.106` / 2a, `10.0.3.14` / 2b); Service `kube-dns` ClusterIP `172.20.0.10`; Corefile `kubernetes cluster.local … { pods insecure }`, `forward . /etc/resolv.conf`, `cache 30`, `loadbalance`; **NodeLocal DNSCache 없음**, `autopath` 플러그인 없음 |
| Pod resolv.conf (기본) | `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` / `nameserver 172.20.0.10` / `options ndots:5` |
| Pod NIC | eth0 MTU **9001**(점보 프레임), TCP 혼잡 제어 `cubic`, iperf3 `tcp_mss_default: 8949` |
| EC2 네트워크 사양 | m5.xlarge "Up to 10 Gigabit" — 베이스라인 **1.25 Gbps**, 피크 **10 Gbps**, 4 vCPU (비교: m5.large 베이스라인 0.75 Gbps, 피크 10 Gbps, 2 vCPU). `aws ec2 describe-instance-types`로 확인, ENA 필수 |
| 요금 | usagetype `APN2-DataTransfer-Regional-Bytes` "Regional Data Transfer - in/out/between AZs or when using public IP or Elastic IP addresses" **$0.01/GB** (`aws pricing get-products --region us-east-1`, 2026-09 조회) |
| 도구 | `nicolaka/netshoot:v0.14` — iperf **3.19**, fortio **1.69.5**, iputils ping 20250605, tcpdump 4.99.5; DNS 클라이언트 `python:3.12-slim` (Debian 13, **glibc 2.41**, Python 3.12.14) |
| 측정 시각 | 2026-09-02 07:58–08:40 UTC (첫 Pod 07:58:22Z, DNS Pod 08:16:24Z) |

AWS는 네트워크 I/O 크레딧이 남아 있어도 버스트 대역폭은 best effort라고 설명하며, 송신과 수신의 크레딧 버킷은 별개입니다. 새 인스턴스는 최대 크레딧으로 시작하지만 피크 가용성과 지속 시간은 달라집니다. 이번 180초 실행은 그 기간에 베이스라인으로의 하락이 없었다는 것만 보여 줍니다. 기록된 m5.xlarge의 베이스라인 1.25 Gbps / 피크 10 Gbps는 공식 [M5 네트워크 사양](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html)에도 있으며, 버스트 동작은 [EC2 대역폭 가이드](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html)를 참고하세요.

픽스처 배치는 다음과 같았습니다.

| Pod | IP | 노드 | Zone | 역할 / requests |
|---|---|---|---|---|
| `cli` | 10.0.2.109 | ip-10-0-2-128 (nodeclaim `system-76r87`) | ap-northeast-2a | 클라이언트; 2500m / 1Gi |
| `srv-same` | 10.0.2.72 | ip-10-0-2-128 — `cli`와 같은 노드 (required podAffinity) | ap-northeast-2a | 서버; 200m / 256Mi |
| `srv-a` | 10.0.2.37 | ip-10-0-2-20 (nodeclaim `system-ksrbg`, `cli`에 podAntiAffinity) | ap-northeast-2a | 서버; 2800m / 1Gi |
| `srv-b` | 10.0.3.65 | ip-10-0-3-32 (nodeclaim `system-svdvk`) | ap-northeast-2b | 서버; 2500m / 1Gi |
| `dns-default` | 10.0.2.5 | ip-10-0-2-20 (`srv-a`에 podAffinity) | ap-northeast-2a | glibc 리졸버, 기본 `ndots:5` |
| `dns-ndots1` | 10.0.2.143 | ip-10-0-2-20 | ap-northeast-2a | glibc 리졸버, `dnsConfig.options ndots=1` |

서버 Pod는 `sh -c "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"`를 실행하고, 모든 벤치 Pod에 `karpenter.sh/do-not-disrupt: "true"`를 붙였습니다. `srv-a`는 처음에 m5.large / 1500m으로 요청했지만 Karpenter가 `no instance type has enough resources`를 보고했습니다 — m5.large의 allocatable 1930m 중 DaemonSet 오버헤드가 821m이어서 — 그래서 m5.xlarge / 2800m으로 바꿨습니다.

### 배포 매니페스트

아래는 과거의 selector·requests·이미지·명령·annotation을 보존한 측정 픽스처이며, 애플리케이션 Service 객체는 없습니다. selector만으로 새 노드나 격리된 노드가 보장되지는 않습니다. 새 실행에서는 복사본을 승인된 테스트 NodePool·사용 가능한 AZ·리소스 예산에 맞추고, 공유 `system` 풀에 그대로 배포하지 마세요. 이미지 digest와 도구 버전도 기록해야 합니다. 변경 가능한 태그와 netshoot의 빌드 시점 도구 다운로드는 과거 바이너리를 보장하지 않습니다. 아래의 보완된 재현 절차는 이 역사적 매니페스트와 구분합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-net
  labels:
    bench: net
---
# 클라이언트 — ap-northeast-2a의 새 m5.xlarge
apiVersion: v1
kind: Pod
metadata:
  name: cli
  namespace: bench-net
  labels: { app: cli, role: client }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
---
# same-node — required podAffinity로 cli와 같은 노드에
apiVersion: v1
kind: Pod
metadata:
  name: srv-same
  namespace: bench-net
  labels: { app: srv-same, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "200m", memory: "256Mi" }
---
# same-AZ — cli와 같은 AZ, 다른 노드(podAntiAffinity). m5.large는 DaemonSet 오버헤드 때문에 들어가지 않아 m5.xlarge
apiVersion: v1
kind: Pod
metadata:
  name: srv-a
  namespace: bench-net
  labels: { app: srv-a, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2800m", memory: "1Gi" }
---
# cross-AZ — ap-northeast-2b의 새 m5.xlarge
apiVersion: v1
kind: Pod
metadata:
  name: srv-b
  namespace: bench-net
  labels: { app: srv-b, role: server, zone: b }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2b
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
```

DNS Pod 두 개는 `srv-a`와 같은 노드에 배치되었다고 기록되어 있습니다. `app` 이미지는 Debian 13 / glibc 2.41로 보고되었으며 musl 등 다른 리졸버는 측정하지 않았습니다. `sniffer`는 같은 Pod 네트워크 네임스페이스를 사용하므로 클러스터가 패킷 캡처를 허용하면 해당 DNS 패킷을 볼 수 있습니다. 아래 예제에서 DNS 객체 두 개를 만들려면 복제한 두 번째 객체의 이름과 `app` 라벨을 `dns-ndots1`로 바꾸고, 그 객체에서만 `dnsConfig` 주석을 해제하세요. 새 실행에서는 두 Pod에 동일한 이미지를 사용하고 기록한 digest로 고정합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-default          # 두 번째 Pod는 name: dns-ndots1 + 아래 dnsConfig 블록만 추가
  namespace: bench-net
  labels: { app: dns-default, role: dns }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: srv-a } }
          topologyKey: kubernetes.io/hostname
  # dns-ndots1에만 있는 블록:
  # dnsConfig:
  #   options:
  #     - name: ndots
  #       value: "1"
  terminationGracePeriodSeconds: 5
  containers:
    - name: app
      image: python:3.12-slim
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
    - name: sniffer
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
```

## 측정 1 — RTT와 HTTP 레이턴시: 같은 노드 → 같은 AZ → 다른 AZ

ICMP(`ping -c 200 -i 0.05 -q`)는 엔드포인트 커널 처리와 스케줄링을 포함한 유휴 경로를 관찰합니다. 이후 같은 경로를 HTTP/1.1과 gRPC로 측정했습니다. 참고용으로 새 연결을 쓰는 `curl` 1회의 connect / total도 적었습니다.

| 경로 | RTT min / **avg** / max / mdev (ms) | 손실 | curl 1회 (콜드) connect / total |
|---|---|---|---|
| 같은 노드 → 10.0.2.72 | 0.021 / **0.040** / 0.089 / 0.007 | 0/200 | 0.194 ms / 0.497 ms |
| 같은 AZ → 10.0.2.37 | 0.300 / **0.339** / 0.450 / 0.017 | 0/200 | 0.497 ms / 2.333 ms |
| 다른 AZ → 10.0.3.65 | 0.504 / **0.544** / 0.625 / 0.015 | 0/200 | 0.694 ms / 4.038 ms |

관측 차이는 같은 AZ − 같은 노드 = +0.30 ms, 다른 AZ − 같은 AZ = **+0.21 ms**, 다른 AZ − 같은 노드 = +0.50 ms입니다. 이 표본의 mdev는 모두 0.017 ms 이하였습니다. curl의 `time_total`은 전송 작업 시간이며 프로세스 기동 시간은 포함하지 않습니다. 1회 값으로 분포를 판단할 수는 없습니다. [curl 시간 정의](https://curl.se/docs/manpage.html)를 참고하세요.

### HTTP/1.1 — 100 qps, 커넥션 4개, keepalive, 60 s (요청 6,000개), ms

| 경로 | avg | **p50** | p90 | p99 | p99.9 | max | min |
|---|---|---|---|---|---|---|---|
| 같은 노드 | 0.260 | **0.259** | 0.299 | 0.350 | 1.267 | 2.080 | 0.111 |
| 같은 AZ | 0.468 | **0.461** | 0.560 | 0.667 | 0.783 | 2.823 | 0.336 |
| 다른 AZ | 0.706 | **0.704** | 0.782 | 0.812 | 1.150 | 4.581 | 0.551 |

### gRPC ping — 100 qps, 커넥션 4개, 30 s (요청 3,000개), ms

| 경로 | avg | **p50** | p90 | p99 | p99.9 | max | min |
|---|---|---|---|---|---|---|---|
| 같은 노드 | 0.410 | **0.397** | 0.449 | 0.869 | 1.187 | 1.314 | 0.241 |
| 같은 AZ | 0.601 | **0.592** | 0.687 | 0.889 | 1.052 | 1.105 | 0.448 |
| 다른 AZ | 0.878 | **0.865** | 0.967 | 1.209 | 2.582 | 2.826 | 0.692 |

기록은 빈 요청 페이로드의 HTTP echo 응답 본문이 약 75바이트이고 실행별 오류가 0건이었다고 설명합니다. 프로토콜별 결과는 구분해야 합니다. HTTP 200, gRPC Ping 결과, gRPC health check의 `SERVING`은 서로 다르며, `-grpc -ping`은 기본 health check가 아닌 Ping 부하를 선택합니다.

**읽는 법.** HTTP p50과 ping 평균의 차이는 약 0.22 / 0.12 / 0.16 ms이지만, 서로 다른 프로토콜과 통계량을 빼서 유저 공간 오버헤드를 분리할 수는 없습니다. HTTP p50의 관측 단계는 +0.202 / +0.243 ms이며 노드·AZ당 고정 비용이 아닙니다. gRPC p50은 HTTP보다 0.138 / 0.131 / 0.161 ms 높았지만 HTTP/2·직렬화·스케줄링·구현별 기여도는 측정하지 않았습니다. HTTP p99는 0.350 → 0.667 → 0.812 ms, gRPC p99.9는 1.187 → 1.052 → **2.582 ms**였습니다. 각 셀은 한 번 실행한 분포입니다.

> **메시 벤치마크와의 비교.** [Istio sidecar vs ambient 기록](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)의 p50 **+1.29 ms**(2.11 − 0.82 ms)는 사이드카 시나리오 전체의 차이이며 프록시 하나의 독립 비용이 아닙니다. Graviton 하드웨어·200 qps·커넥션 16개·Fortio 1.69.4로, 여기의 M5·100 qps·커넥션 4개와 조건이 다릅니다. 두 값을 보편적인 “메시 홉”과 “AZ 홉” 비용으로 더하거나 순위를 매길 수 없습니다.

### 새 커넥션의 비용 — keepalive=false, 100 qps, 커넥션 4개, 30 s (요청 3,000개), ms

요청마다 TCP 커넥션을 새로 맺으면(fortio `-keepalive=false`) 지연은 어떻게 변할까요?

| 경로 | avg | **p50** | p90 | p99 | p99.9 | max | min | keepalive p50 대비 |
|---|---|---|---|---|---|---|---|---|
| 같은 노드 | 0.672 | **0.664** | 0.782 | 0.957 | 1.253 | 1.306 | 0.364 | **+0.405 ms** |
| 같은 AZ | 1.066 | **1.079** | 1.185 | 1.369 | 1.582 | 1.795 | 0.769 | **+0.618 ms** |
| 다른 AZ | 1.530 | **1.517** | 1.678 | 1.796 | 1.981 | 2.009 | 1.300 | **+0.813 ms** |

관측 증가분은 **+0.405 / +0.618 / +0.813 ms**입니다. 새 TCP 연결은 수립 작업을 추가하지만 이 측정만으로 “RTT 한 번 + 0.3 ms”라는 고정 분해를 입증할 수는 없습니다. 연결 재사용은 실제 부하로 평가할 유용한 최적화이며 AZ 간 호출의 정확성을 위한 필수 조건은 아닙니다. 연결 종료 방식에 따라 active close를 수행한 쪽에 TIME_WAIT가 늘 수 있지만, 소켓 상태나 TIME_WAIT 수는 여기서 측정하지 않았습니다.

### 고정 커넥션 풀의 최대 qps — 지연이 곧 처리량 (closed-loop, 커넥션 16개, 20 s)

`-qps 0`(무제한, 닫힌 루프)으로 16개 커넥션이 낼 수 있는 최대 요청률을 재면 지연 차이가 처리량 차이로 바뀝니다.

| 경로 | 요청 수 | **달성 qps** | avg ms | p50 | p90 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|
| 같은 노드 | 899,827 | **44,991** | 0.355 | 0.249 | 0.733 | 1.695 | 3.389 | 13.593 |
| 같은 AZ | 770,156 | **38,507** | 0.415 | 0.396 | 0.537 | 0.728 | 1.147 | 4.502 |
| 다른 AZ | 512,060 | **25,602** | 0.624 | 0.597 | 0.770 | 0.949 | 1.293 | 4.725 |

평균 약 16개 요청이 진행 중이고 클라이언트 대기 시간이 작은 정상상태 폐루프에서는 Little의 법칙으로 처리량 ≈ 동시성 / 평균 지연을 얻습니다. 16 / 0.000355 = 45,070(기록 44,991), 16 / 0.000415 = 38,554(38,507), 16 / 0.000624 = 25,641(25,602)입니다. 이 테스트의 다른 AZ 요청률은 같은 AZ보다 **33.5% 낮았습니다**. 이 관계가 지연의 단독 원인이나 보편적인 AZ 페널티를 입증하지는 않습니다. 같은 노드의 꼬리 지연이 더 큰 원인으로 CPU 경합을 의심할 수 있지만 프로파일링으로 확인하지 않았습니다.

## 측정 2 — 처리량: 단일 플로우 5 Gbps 상한과 인스턴스 10 Gbps 상한

iperf3 3.19, TCP, 실행당 20초, `-J`, 클라이언트 `cli`. CPU 열은 iperf3가 보고하는 프로세스별 값으로 100% = vCPU 1개입니다.

| 경로 | 플로우 (-P) | 송신 Gbps | 수신 Gbps | 재전송 | 전송 바이트 | 클라이언트 CPU | 서버 CPU | 송신측 TCP 평균 RTT (stream 1) | 최대 snd_cwnd |
|---|---|---|---|---|---|---|---|---|---|
| 같은 노드 (cli→srv-same) | 1 | **29.97** | 29.97 | 13 | 74,921,541,632 | **99.8 %** | 80.9 % | 34 µs | 1,861,392 B |
| 같은 노드 | 8 | **48.15** | 48.08 | 14,567 | 120,375,083,008 | 179.0 % | 186.9 % | 201 µs / 767 µs (stream 1, 2) | 5,888,442 B |
| 같은 AZ (cli→srv-a, 2a→2a) | 1 | **4.96** | 4.96 | 4 | 12,411,731,968 | 19.5 % | 15.4 % | **5,641 µs** | 4,349,214 B |
| 같은 AZ | 8 | **9.94** | 9.93 | 5,874 | 24,846,139,392 | 36.3 % | 159.3 % | 2,720 µs / 1,626 µs | 1,163,370 B |
| 다른 AZ (cli→srv-b, 2a→2b) | 1 | **4.96** | 4.96 | 2 | 12,411,994,112 | 20.0 % | 22.5 % | **5,420 µs** | 4,304,469 B |
| 다른 AZ | 8 | **9.94** | 9.93 | 5,979 | 24,845,090,816 | 36.7 % | 138.2 % | 3,671 µs / 3,237 µs | 1,226,013 B |

네 가지를 읽어야 합니다.

1. **같은 노드에서는 물리 NIC를 우회했습니다.** 단일 플로우 29.97 Gbps에서 클라이언트 프로세스 CPU가 99.8%였고, 8개 플로우는 48.15 Gbps였습니다. 호스트 라우팅, 양쪽 Pod의 veth 경로, 커널 처리와 CPU 스케줄링은 여전히 영향을 줍니다. CPU 부하 징후가 있는 네트워크 측정이지 순수 메모리 복사 속도 측정은 아닙니다.
2. **두 노드 간 단일 플로우는 모두 4.96 Gbps였습니다.** 클러스터 배치 그룹 외부의 일반적인 5 Gbps 한도에 부합합니다. AWS는 클러스터 배치 그룹 내부에서는 최대 10 Gbps, 같은 AZ의 지원되는 ENA Express 경로에서는 최대 25 Gbps도 문서화합니다. iperf3 프로세스 CPU가 낮다는 사실만으로 모든 호스트·네트워크 처리 한계를 배제할 수는 없습니다.
3. **8개 플로우는 두 경로 모두 9.94 Gbps였습니다.** 해당 관측 구간에서 비슷한 처리량을 얻었다는 근거입니다. 재전송은 단일 플로우에서도 4 / 2회 있었고 8개에서 5,874 / 5,979회로 늘었습니다. 재전송 수만으로 ENA 셰이핑이나 손실 위치를 특정할 수 없으며, ENA allowance 카운터는 수집하지 않았습니다.
4. **부하 중 TCP RTT가 유휴 ICMP RTT보다 컸습니다.** 단일 플로우 송신측 값은 약 **5.6 / 5.4 ms**, 혼잡 윈도우는 약 4.3 MB였고 유휴 ping 평균은 0.34 / 0.54 ms였습니다. 큐잉이 가능한 설명이지만 프로토콜·표본 방식·부하가 다릅니다. 큐의 위치나 다중화된 모든 RPC에 정확히 5 ms가 추가된다는 주장은 측정하지 않았습니다.

기록된 MSS 8949는 MTU 9001과 당시 IPv4/TCP 오버헤드에 부합하지만, 유효 MSS는 헤더와 경로 MTU에도 좌우됩니다. 전송 바이트는 애플리케이션 전송량이며 별도로 검증된 과금 사용량은 아닙니다.

> 당시의 일반 EC2 경로에서는 병렬 플로우가 단일 플로우보다 인스턴스 버스트 대역폭을 더 사용했습니다. 병렬도를 높이면 CPU·혼잡·비용도 바뀝니다. Kafka fetcher나 전송 동시성을 바꾸기 전에 실제 인스턴스·경로 한도를 확인하세요. “모든 커넥션은 5 Gbps 한도”나 “같은 AZ면 대역폭 두 배” 모두 이 결과로 일반화할 수 없습니다.

### 3분 지속 테스트와 버스트 크레딧

기록된 m5.xlarge 베이스라인은 1.25 Gbps, best-effort 피크는 최대 10 Gbps입니다. 과거의 AZ 간 4개 플로우 테스트는 180초 동안 10초 간격으로 관찰했습니다(`iperf3 -c 10.0.3.65 -p 5201 -t 180 -P 4 -i 10 -J`). 이 IP는 당시 픽스처 주소이므로 새 테스트에서는 현재 Pod IP를 조회해야 합니다.

| 항목 | 값 |
|---|---|
| 10초 구간별 Gbps (18구간) | 9.94, 9.93 ×12, 9.92, 9.93 ×4 — **최소 9.92, 최대 9.94** |
| 총 전송 | 223,376,179,200 B = **223.4 GB** / 180.0 s (9.93 Gbps) |
| 재전송 | 44,842 (≈ 249/s; 10초 구간당 2,273–2,669) |
| CPU | 클라이언트 30.7 % (system 30.1 %), 서버 54.2 % (system 52.2 %) |

**180초 동안 1.25 Gbps로의 하락은 관측되지 않았습니다.** 무제한 크레딧이나 지속적인 피크 대역폭 보장을 뜻하지는 않습니다. AWS는 가변적인 best-effort 버스트와 크레딧 소진 시 베이스라인 제한을 설명합니다. 장시간 백업과 리밸런스는 이 짧은 실행을 외삽하지 말고 해당 베이스라인과 실제 부하 요구를 기준으로 계획하세요.

## 측정 3 — AZ 간 데이터 전송 비용 모델

이 절은 원문의 비용 산술을 추정 모델로 보존합니다. 벤치마크에 제공된 것은 페이로드 바이트 수와 공개 정가이며, 비용 및 사용량 보고서(CUR)나 청구서가 아닙니다.

같은 리전의 AZ 간 EC2 사설 IP 직접 전송에 대해 [EC2 요금 페이지](https://aws.amazon.com/ec2/pricing/on-demand/)는 양 끝에 각각 $0.01/GB를 문서화합니다. 기록된 공개 Pricing API 항목은 `APN2-DataTransfer-Regional-Bytes`, **$0.0100000000 USD/GB**였습니다. `get-products`는 카탈로그 가격이며 계정의 실제 지불 단가가 아닙니다. 한 방향 페이로드도 송신측 “out”과 수신측 “in”에 과금될 수 있으며, 같은 양의 역방향 전송이 있어야 한다는 뜻은 아닙니다. 다른 AWS 서비스 경로에는 다른 과금 규칙이 적용될 수 있습니다.

| 시나리오 | 과거 십진 GB 모델의 페이로드 양 | 추정 비용 (모델 GB × $0.01 × 2) |
|---|---|---|
| 180초 실행 (페이로드 실측, 비용 추정) | 223.4 GB | 223.4 × $0.01 ≈ **양 끝 각각 $2.23, 합계 $4.47** |
| 측정 2의 AZ 간 iperf3 전송 (12.41 + 24.85 + 223.38 GB) | 260.6 GB | 양 끝 각각 ≈ $2.61, **합계 ≈ $5.21** (그 외 트래픽 제외) |
| 평균 1 Gbps가 30일 내내 AZ를 넘는다면 (**가정**) | 0.125 GB/s × 86,400 s × 30일 = 324,000 GB ≈ **324 TB** | 324,000 × $0.02 ≈ **$6,480 / 월** |
| RF3 StatefulSet를 3개 AZ에 분산, 리더 ingest 100 MiB/s (**가정**, 복제 트래픽만 계산) | 팔로워 2개가 각각 다른 AZ → 2 × 100 MiB/s = 209,715,200 B/s × 2,592,000 s ≈ 543,600 GB ≈ **544 TB / 월** | 543,600 × $0.02 ≈ **$10,870 / 월** |

네 행의 비용은 모두 원문의 **십진 환산, 1 GB = 페이로드 10⁹바이트**를 모델 가정으로 사용합니다. 이번 감사에서는 EC2 과금 사용량이 이 환산과 같다는 근거를 확보하지 못했습니다. 원시 합계는 지속 실행 223,376,179,200 B, AZ 간 iperf3 세 실행 합계 260,633,264,128 B입니다. 실제 계량 단위·단가·양 끝의 사용량·프로토콜 오버헤드와 재전송·크레딧 및 할인을 [CUR 전송 기록](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html)과 대조해야 합니다. 아래 두 행은 30일 연속 전송도 가정하며 복제량에서 프로듀서·컨슈머 트래픽은 제외합니다. **$4.47과 $5.21은 추정값이며 실제 지출이 확인된 금액이 아닙니다.**

**운영자가 할 일.**

- **지원되는 경로에서 적합한 로컬 엔드포인트를 우선합니다.** 현재 Kubernetes 문서의 값은 `Service.spec.trafficDistribution: PreferSameZone`이며 `PreferClose`는 폐기 예정인 이전 별칭입니다. 폴백이 있는 선호도이지 엄격한 존 제한은 아닙니다. API 서버·kube-proxy 버전과 기능 지원을 확인하세요. 당시에는 1.36 컨트롤 플레인과 1.35 kube-proxy를 사용했습니다. 이 선호도와 애플리케이션 Service 경로 모두 측정하지 않았으며 Pod IP 직접 통신에는 적용되지 않습니다.
- **지역성과 장애 내성을 함께 고려합니다.** 존 인식 읽기나 클라이언트 배치로 불필요한 전송을 줄일 수 있지만 RF3 복제본을 모두 한 AZ에 모으면 AZ 장애 보호를 잃습니다. 필요한 복제·장애 전환 설계를 유지하세요. [Zonal 클러스터 운영 전략](../ops/15-zonal-operations-guide.md)을 참고하세요.
- **과금되는 양 끝을 측정합니다.** 백업·리밸런스·리플레이의 출발/목적 AZ와 계량 사용량을 기록하고 관련 “in”·“out” 항목을 합산합니다. 서로 다른 계정에 청구될 수도 있으므로 페이로드 바이트만으로 최종 요금을 단정하지 마세요.

## 측정 4 — DNS: ndots:5가 만드는 쿼리 증폭

![glibc 리졸버가 ndots:5에서 search 접미사 4개를 A+AAAA 쿼리로 차례로 시도해 NXDOMAIN 8개를 받은 뒤 마지막에 절대 이름으로 답을 얻는 10쿼리 경로와, 끝에 점을 붙였을 때 A+AAAA 2쿼리로 바로 끝나는 경로를 대비한 시퀀스 다이어그램.](../.gitbook/assets/ko-networking-06-pod-network-benchmark-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-networking-06-pod-network-benchmark-1.html)

그림은 당시 glibc search 순서입니다. 4.37 ms는 기록된 A 응답까지이며 전체 `getaddrinfo` 호출 시간이 아닙니다. Pod 캡처에서 보이지 않은 업스트림 화살표는 설명용입니다. “cache 30”은 TTL 상한이며 30초 동안 캐시 히트를 보장하지 않습니다.

기록된 Pod에는 search 도메인 4개와 `ndots:5`가 있었지만 모든 EKS·DNS 정책·운영체제·노드 설정이 같지는 않습니다. 당시 glibc `AF_UNSPEC` 호출은 후보마다 A와 AAAA를 질의했고 search 후보 4개가 NXDOMAIN인 뒤 절대 STS 이름이 성공했습니다. A/AAAA 동시성과 쿼리 수는 리졸버 옵션·주소 패밀리·조기 성공·재시도·TCP 폴백에 따라 달라집니다. 과거 캡처의 `tcpdump -i eth0 -nn udp port 53`은 UDP DNS만 관측합니다. 기록은 프로세스 첫 조회 1회와 이후 20회 반복을 구분하지만, 첫 호출이라고 CoreDNS나 업스트림 캐시까지 비어 있었다고 볼 수는 없습니다. [Kubernetes Pod DNS 설정](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)을 참고하세요.

### 한 번의 이름 풀이가 보내는 쿼리 수와 웜 지연 (20회 반복), ms

| Pod / ndots | 이름 (점 개수) | 보낸 쿼리 | NXDOMAIN 응답 | warm min | **median** | p90 | max |
|---|---|---|---|---|---|---|---|
| default / 5 | `kubernetes.default` (1) | 4 | 2 | 0.87 | **1.71** | 1.97 | 2.61 |
| default / 5 | `kubernetes.default.svc.cluster.local` (4) | **10** | 8 | 1.53 | **3.63** | 4.45 | 6.41 |
| default / 5 | `kubernetes.default.svc.cluster.local.` (끝점) | 2 | 0 | 0.33 | **0.46** | 1.09 | 1.58 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com` (3) | **10** | 8 | 3.08 | **3.78** | 4.66 | 4.84 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com.` (끝점) | 2 | 0 | 0.42 | **0.80** | 1.25 | 2.17 |
| default / 5 | `www.amazon.com` (2) | **10** | 8 | 2.51 | **3.46** | 3.74 | 5.86 |
| ndots1 / 1 | `kubernetes.default` (1) | **6** | 4 | 1.16 | **2.04** | 2.80 | 4.54 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local` (4) | 2 | 0 | 0.35 | **0.97** | 1.08 | 1.35 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local.` | 2 | 0 | 0.34 | **0.40** | 0.97 | 1.17 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com` (3) | 2 | 0 | 0.45 | **0.54** | 1.22 | 1.42 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com.` | 2 | 0 | 0.47 | **0.75** | 1.20 | 1.30 |
| ndots1 / 1 | `www.amazon.com` (2) | 2 | 0 | 0.63 | **0.90** | 1.27 | 2.74 |

기록된 프로세스 첫 조회 시간은 default/`sts` 6.22 ms, default/`sts.` 2.87 ms, default/`www.amazon.com` 9.58 ms, default/`kubernetes.default.svc.cluster.local` 7.40 ms, ndots1/`kubernetes.default` 10.52 ms, ndots1/`sts` 2.84 ms였습니다. 리졸버 초기화 작업을 포함하며 아래 패킷 타임라인과는 다른 값입니다.

**읽는 법.** 이 표본의 외부 이름과 끝점 없는 클러스터 FQDN은 **10쿼리 / NXDOMAIN 8개**였습니다. 끝점을 붙인 STS의 중앙값은 3.78 → 0.80 ms, 클러스터 FQDN은 3.63 → 0.46 ms로 줄었습니다. `kubernetes.default`는 두 번째 후보에서 성공해 4쿼리만 필요했으므로 항상 search 목록 전체를 소비하지는 않습니다. [CoreDNS cache](https://coredns.io/plugins/cache/)는 음성 응답도 캐시하지만 `cache 30`은 최대 TTL입니다. 응답 TTL과 최소 TTL이 적용되고 replica마다 캐시가 별개입니다. Kubernetes 플러그인의 기본 TTL은 별도 설정이 없으면 5초입니다. 캐시 히트에서도 순차 질의는 남지만, 이 캡처가 모든 웜 조회에서 업스트림을 피했음을 입증하지는 않습니다.

### 실제 순서 — `sts.ap-northeast-2.amazonaws.com` 콜드 풀이 1회 (ndots:5, tcpdump, 첫 패킷 기준 ms)

| t (ms) | 172.20.0.10으로 보낸 후보 (A + AAAA 병렬) | 응답 |
|---|---|---|
| 0.00 | `sts.ap-northeast-2.amazonaws.com.bench-net.svc.cluster.local.` | NXDomain (권한 응답, CoreDNS kubernetes 플러그인) 0.92 / 1.14 |
| 1.21 | `sts.ap-northeast-2.amazonaws.com.svc.cluster.local.` | NXDomain 2.01 / 2.26 |
| 2.32 | `sts.ap-northeast-2.amazonaws.com.cluster.local.` | NXDomain 3.15 / 3.41 |
| 3.47 | `sts.ap-northeast-2.amazonaws.com.ap-northeast-2.compute.internal.` | NXDomain (VPC 리졸버로 forward — 비권한) 3.68 / 3.93 |
| 3.99 | `sts.ap-northeast-2.amazonaws.com.` | **A 10.0.3.84, A 10.0.2.129** 4.37 (AAAA: no data) |

표에는 쿼리 10개와 NXDOMAIN 8개가 기록되어 있습니다. **4.37 ms**는 첫 질의부터 A 응답까지이며 AAAA 완료 시각은 없으므로 프로세스 첫 호출 6.22 ms 전체와 같지 않습니다. 후보별 RTT도 일률적인 0.8–1.1 ms가 아닙니다. 네 번째 쌍은 0.21 / 0.46 ms, 마지막 A는 0.38 ms였습니다. kube-proxy iptables는 패킷마다가 아니라 새 conntrack 플로우에 대해 엔드포인트를 선택하며 A/AAAA가 같은 플로우를 사용할 수 있습니다. 엔드포인트 둘을 같은 확률로 고르면 새 플로우의 절반이라는 모델을 세울 수 있지만, **AZ 간 DNS 쿼리 비율을 측정한 결과는 아닙니다**. Service VIP `172.20.0.10`을 본 Pod 캡처만으로 선택된 백엔드 AZ를 알 수 없습니다. 원문은 STS 사설 주소 둘을 인터페이스 엔드포인트 ENI로 설명하며, 별도로 클러스터 FQDN의 포워딩 후보 2.2 ms / 패킷 walk 5.6 ms와 끝점 사용 시 0.4–0.5 ms를 기록합니다.

### `ndots:1`이 하는 일과 부작용

- **이 표본의 외부 이름**: 10 → **2쿼리**, 중앙값 약 3.5–3.8 → **0.5–0.9 ms**. 이득은 이름과 리졸버 동작에 따라 달라집니다.
- **짧은 이름은 실패한 시도가 하나 더 생길 수 있습니다.** 여기서 `kubernetes.default`는 점 1개로 `ndots:1`을 만족해 절대 이름을 먼저 시도했습니다. CoreDNS가 포워딩한 뒤 기록상 1.6 ms에 NXDOMAIN을 받고, 네임스페이스 접미사를 거쳐 `svc.cluster.local`에서 `172.20.0.1`을 얻었습니다. 6쿼리·NXDOMAIN 4개·중앙값 2.04 ms로 기존 1.71 ms보다 컸습니다. 내부 이름이 업스트림에 노출될 수 있으므로 `ndots` 변경 전에 애플리케이션의 이름 사용을 모두 시험하세요. 전체 Service 이름을 쓰면 이런 모호성을 줄일 수 있습니다.
- **끝점은 리졸버 이름을 절대 이름으로 만들어** search 확장을 피합니다. 재시도·주소 패밀리 설정·캐시가 달라져도 반드시 2쿼리나 일정한 지연을 보장한다는 뜻은 아닙니다.

### 증폭 산술 (파생)

**같은 응답 패턴**에서 애플리케이션 DNS 캐시가 없고 요청마다 한 번 조회한다고 가정하면, 초당 조회 1,000회 × 10쿼리 = 10,000쿼리/s이며 2쿼리 형태는 2,000쿼리/s입니다. 이 중 8,000개(80%)가 NXDOMAIN을 받는다는 쿼리 수 모델이지 CoreDNS CPU나 AZ 간 비율 측정은 아닙니다. 관측 중앙값 차이는 STS 3.78 − 0.80 = 2.98 ms, 클러스터 FQDN 3.63 − 0.46 = 3.17 ms이며 요청마다 고정으로 추가되는 비용은 아닙니다.

**실제 애플리케이션과 함께 시험할 선택지:**

- 클라이언트가 지원하면 절대 DNS 이름을 사용합니다. HTTPS나 AWS SDK 엔드포인트 URL에 무조건 점을 붙이지 마세요. Host 처리·SNI·인증서 검증·요청 서명이 계속 동작해야 합니다.
- `dnsConfig: {options: [{name: ndots, value: "1"}]}`을 짧은 이름 동작 및 애플리케이션 DNS 캐시와 함께 평가합니다.
- 적합한 환경에서 [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)를 평가합니다. 히트는 로컬이지만 미스는 업스트림으로 갈 수 있습니다. 현재 [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)는 이미 노드 로컬 CoreDNS 시스템 서비스를 사용합니다. 순수 Auto Mode 클러스터에는 CoreDNS Deployment가 불필요하지만, 혼합 클러스터의 비 Auto 노드에는 여전히 필요합니다.
- [CoreDNS autopath](https://coredns.io/plugins/autopath/)는 서버에서 search를 처리할 수 있지만 Kubernetes 연동에는 `pods verified`, 원래 Pod IP 식별, 관련 Pod watch·RBAC·메모리가 필요합니다. 기록된 `pods insecure` 구성은 이 조건을 충족하지 않습니다. 여기서는 이 최적화를 시험하지 않았습니다.

## 재현 방법 — 보완된 절차

승인된 격리 실습 환경과 이 테스트 전용의 사용하지 않는 네임스페이스를 사용합니다. 첫 픽스처를 환경에 맞게 복사해 `bench-net.yaml`, DNS 객체 두 개를 `bench-dns.yaml`로 저장하고 네임스페이스 이름을 맞춥니다. 적용 전에 NodePool 용량·AZ·스케줄링·패킷 캡처 권한을 확인하세요. 실험을 위해 운영 환경의 admission이나 보안 통제를 약화하지 마세요. 시간이 제한된 명령도 노드를 포화시키고 요금을 발생시킬 수 있습니다.

모든 명령은 `cli` 내부 대화형 셸로 들어가지 않고 **운영자 Bash 셸**에서 실행합니다. 감사에서는 구문과 일부 로컬 도구 동작을 확인했지만 이 픽스처를 EKS에 배포하거나 네트워크 부하를 실행하지 않았습니다.

**1. 수정한 픽스처를 배포하고 배치를 확인합니다.**

```bash
set -euo pipefail
BENCH_NS=bench-net
kubectl apply -f bench-net.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready \
  pod/cli pod/srv-same pod/srv-a pod/srv-b --timeout=300s
kubectl -n "$BENCH_NS" get pods -o wide
kubectl get nodes -L topology.kubernetes.io/zone,node.kubernetes.io/instance-type,karpenter.sh/nodepool

SAME_IP=$(kubectl -n "$BENCH_NS" get pod srv-same -o jsonpath='{.status.podIP}')
AZ_IP=$(kubectl -n "$BENCH_NS" get pod srv-a -o jsonpath='{.status.podIP}')
CROSS_IP=$(kubectl -n "$BENCH_NS" get pod srv-b -o jsonpath='{.status.podIP}')
: "${SAME_IP:?missing srv-same IP}" "${AZ_IP:?missing srv-a IP}" "${CROSS_IP:?missing srv-b IP}"
for bench_pod in srv-same srv-a srv-b; do
  kubectl -n "$BENCH_NS" logs "$bench_pod" --tail=30
  kubectl -n "$BENCH_NS" exec "$bench_pod" -- ss -lnt
done
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- \
    curl --fail --silent --show-error --max-time 5 "http://$bench_ip:8080/" >/dev/null
done
```

계속하기 전에 `cli`와 `srv-same`은 같은 노드, `srv-a`는 같은 AZ의 다른 노드, `srv-b`는 다른 AZ인지 확인합니다. 5201/8080/8079 리스너와 시작 오류도 확인하세요. 과거 픽스처에는 readiness probe가 없으므로 Pod Ready만으로 프로세스 리슨을 보장할 수 없습니다. 노드 ID·IP·image ID와 실제 `iperf3 --version` / `fortio version`을 기록하고, Pod가 재생성되면 중지한 뒤 주소를 다시 조회합니다.

**2. RTT와 참고용 HTTP 1회를 측정합니다.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- ping -c 200 -i 0.05 -q "$bench_ip"
done
kubectl -n "$BENCH_NS" exec cli -- curl --fail --silent --show-error --max-time 5 \
  -o /dev/null -w 'connect=%{time_connect} total=%{time_total}\n' "http://$CROSS_IP:8080/"
```

**3. 시간을 제한해 처리량을 측정하고 운영자 로컬에 결과를 저장합니다.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 1 -J > "t1-$bench_ip-P1.json"
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 8 -J > "t1-$bench_ip-P8.json"
done
kubectl -n "$BENCH_NS" exec cli -- \
  iperf3 -c "$CROSS_IP" -p 5201 -t 180 -P 4 -i 10 -J > t1-cross-sustained180-P4.json
```

종료 코드뿐 아니라 JSON 오류도 확인합니다. `end.sum_sent.bits_per_second`, `end.sum_sent.retransmits`, `end.cpu_utilization_percent.host_total` / `remote_total`, `end.streams[].sender.mean_rtt` / `max_snd_cwnd`를 읽습니다. iperf3 3.19 프로세스 CPU의 100%는 경과 시간 동안 CPU 하나의 시간을 사용한 값으로, 여러 스레드는 100%를 넘을 수 있습니다. TCP RTT 필드는 마이크로초입니다.

**4. 요청 지연을 측정합니다. 확인한 서버 주소마다 반복합니다.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 60s "http://$bench_ip:8080/" > "http-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 30s -keepalive=false "http://$bench_ip:8080/" > "new-connection-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 0 -c 16 -t 20s "http://$bench_ip:8080/" > "closed-loop-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -grpc -ping -qps 100 -c 4 -t 30s "$bench_ip:8079" > "grpc-$bench_ip.json"
done
```

Fortio 1.69.5의 `-r`은 초 단위의 가장 작은 히스토그램 버킷 해상도입니다. 기본 `0.001`은 1 ms, `0.00001`은 10 µs이며 큰 버킷은 폭이 넓어질 수 있습니다. 분위수는 버킷 경계 안에서 보간하고 양 끝에는 관측 최소·최대값이 반영됩니다. 따라서 버킷 하나에 모였다고 **p50이 반드시 0.5 ms인 것은 아닙니다**. 원문은 첫 실행의 거친 분위수를 버리고 10 µs 해상도로 다시 측정했다고 기록합니다. 이 이력은 유지하되 모든 보간 분위수를 가짜라고 부르면 안 됩니다. 표의 일부 꼬리 값과 새 연결 중앙값은 1 ms를 넘습니다. 평균과 함께 전체 히스토그램과 오류 카운터를 저장하세요.

**5. DNS: 한 번의 조회 캡처와 반복 시간 측정을 분리합니다.**

```bash
kubectl apply -f bench-dns.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready pod/dns-default pod/dns-ndots1 --timeout=300s
for bench_pod in dns-default dns-ndots1; do
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- cat /etc/resolv.conf
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- ldd --version
done
```

터미널 1에서 단일 조회 전에 캡처를 시작합니다. 이 필터는 53번 포트의 일반 UDP·TCP DNS를 포함하지만 암호화 DNS나 CoreDNS의 업스트림 구간은 포함하지 않습니다. 한 번의 조회가 끝나면 Ctrl-C로 중지하고 그 뒤 웜 반복을 실행합니다.

```bash
kubectl -n bench-net exec -it dns-default -c sniffer -- \
  tcpdump -l -i eth0 -nn '(udp or tcp) and port 53'
```

터미널 2에서 로컬 헬퍼를 만들고 **`kubectl exec -i`**로 입력을 전달합니다. first 모드는 리졸버를 정확히 한 번 호출합니다. warm 모드는 같은 프로세스에서 준비 호출 1회 후 20회를 측정합니다. 이 보완 절차는 캡처 범위를 명확히 구분합니다.

```bash
cat > dns-probe.py <<'PY'
import json
import socket
import statistics
import sys
import time

name, mode = sys.argv[1:3]
if mode not in ("first", "warm"):
    raise SystemExit("mode must be first or warm")

def one():
    started = time.perf_counter()
    socket.getaddrinfo(name, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return (time.perf_counter() - started) * 1000

first = one()
if mode == "first":
    print(json.dumps({"name": name, "first_process_ms": first}))
else:
    samples = [one() for _ in range(20)]
    ordered = sorted(samples)
    print(json.dumps({
        "name": name, "warmup_ms": first, "samples_ms": samples,
        "min_ms": ordered[0], "median_ms": statistics.median(ordered),
        "p90_ms": ordered[17], "max_ms": ordered[-1],
    }))
PY
BENCH_NS=bench-net
DNS_POD=dns-default
DNS_NAME=sts.ap-northeast-2.amazonaws.com
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" first < dns-probe.py
```

캡처를 중지한 뒤:

```bash
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" warm < dns-probe.py
```

표의 이름들과 `DNS_POD=dns-ndots1`로 반복하고 캡처 대상도 같이 바꿉니다. first 전용 구간에서 질의·응답을 세고 21번의 조회를 한 번으로 집계하지 마세요. digest·리졸버 버전·설정을 맞춰도 시간과 캐시 상태는 달라질 수 있습니다. 이 페이지에는 원래 이미지 digest와 전체 패킷·JSON 자료가 없어 정확한 재현은 보장할 수 없습니다.

**6. 이번 테스트의 리소스만 정리합니다.** `bench-net`을 이 실행 전용으로 만들었다면 결과를 보관한 뒤 `kubectl delete namespace bench-net`으로 삭제합니다. 남은 노드와 비용은 별도로 확인하세요. Karpenter consolidation은 정책·예산·다른 워크로드에 좌우되므로 네임스페이스 삭제가 즉각적인 노드 제거를 보장하지 않습니다. `do-not-disrupt`도 모든 강제 중단을 막지는 않습니다.

## 해석 시 주의사항

- **새 노드였지만 완전히 혼자는 아니었습니다.** Karpenter가 이 테스트용으로 띄운 m5.xlarge 3대에 곧 consolidation이 다른 네임스페이스의 작은 Pod 몇 개를 옮겨 왔습니다(`cli` 노드에 1개, `srv-b` 노드에 3개 — 소규모 내부 서비스와 컨트롤러이며, 벤치마크 트래픽과는 무관합니다). 측정 중 유휴·저트래픽이었고 부하는 최대 180초 버스트로 제한했습니다. `cli` 노드의 CPU *요청*은 3901m / 3920m(99%)였지만 실제 사용량이 그렇다는 뜻은 아닙니다.
- **하루에 셀당 한 번(n = 1) 측정했습니다.** 분산 추정을 위한 독립 반복이 없습니다. 순위·비율·인과 설명도 이 표본 크기의 제약을 받으며 SLA로 사용할 수 없습니다.
- **애플리케이션 ClusterIP와 트래픽 분산은 측정하지 않았습니다.** 기록에 따르면 벤치마크 네임스페이스의 Service 생성이 `failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`로 실패했습니다. `failurePolicy: Fail`인 실패 웹훅은 매칭되는 요청을 거부하며, 범위는 rules·namespace/object selector·match condition에 달려 있습니다. 과거 사건을 현재 클러스터의 모든 Service 생성이 불가능하다는 뜻으로 읽으면 안 됩니다. 웹훅은 우회하지 않았고 DNS는 기존 `kube-dns` Service를 사용했습니다. [트러블슈팅 플레이북](../ops/16-troubleshooting-playbook.md)을 참고하세요.
- **ENA allowance 카운터는 수집하지 않았습니다.** `ethtool -S`는 적절한 권한으로 호스트의 실제 ENA 인터페이스를 대상으로 해야 합니다. Pod 자신의 `eth0`는 대개 veth이며 `hostNetwork`만으로 올바른 장치나 권한이 보장되지 않습니다. 관련 카운터는 `bw_in_allowance_exceeded`, `bw_out_allowance_exceeded`, `pps_allowance_exceeded`, `conntrack_allowance_exceeded`, `linklocal_allowance_exceeded`입니다. 재전송 수는 이를 대신하지 못합니다.
- **버스트 크레딧 소진은 180초 안에서 관측되지 않았을 뿐입니다.** "Up to" 인스턴스에서 더 긴 지속 전송은 베이스라인(1.25 Gbps) 쪽으로 제한될 수 있습니다. 180초 이상은 테스트하지 않았습니다.
- **DNS 캐시 상태를 통제하지 않았습니다.** 프로세스 첫 조회와 반복 조회는 다르지만 `cache 30`이 30초 히트를 보장하지는 않습니다. replica 선택과 업스트림 상태가 두 집단 모두에 영향을 주므로 비교는 관측 결과로 해석해야 합니다.
- **같은 노드의 CPU 부하는 가능한 설명입니다.** 클라이언트 프로세스 CPU 99.8%는 29.97 Gbps 결과의 이 해석을 뒷받침하지만 모든 병목을 특정하거나 29.97 / 48.15 Gbps를 다른 인스턴스에 보장하지는 않습니다.
- **다른 CNI 모드와 정책 강제는 비교하지 않았습니다.** Prefix delegation과 Security Groups for Pods는 꺼져 있었고 네임스페이스에는 NetworkPolicy가 없었습니다. 이 bare Pod 테스트는 지원되는 컨트롤러 소유 워크로드의 VPC CNI NetworkPolicy 강제를 검증한 것이 아닙니다.

## 함께 읽기

- [Amazon VPC CNI](./01-vpc-cni.md) — 이 측정의 데이터 플레인: Pod가 VPC IP를 직접 받는 구조, prefix delegation, ENI/IP 워밍
- [Zonal 클러스터 운영 전략](../ops/15-zonal-operations-guide.md) — 측정 3의 요금을 줄이는 존 정렬 배치와 AZ 장애 전환 설계
- [트러블슈팅 플레이북](../ops/16-troubleshooting-playbook.md) — 웹훅 실패 진단; 이 문서의 사건은 과거 기록
- [사이드카 vs Ambient 모드 선택 가이드](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) — 별도의 하드웨어·부하 실험; +1.29 ms는 시나리오 전체의 차이
- [EBS gp2 vs gp3 실측 벤치마크](../storage/01-ebs-gp2-gp3-benchmark.md) — 같은 클러스터의 스토리지 경로 실측
- [Kafka on EKS 실측 벤치마크](../data-on-eks/kafka/09-kafka-benchmark.md) — 복제 트래픽·플로우 한도·가용성의 관계
- [가이드북 로드맵 — 실측 벤치마크 시리즈](../roadmap.md)
- [퀴즈: Pod 네트워크 실측 벤치마크](../quizzes/networking/06-pod-network-benchmark-quiz.md)


### 검토에 사용한 공식 근거

- [Fortio 1.69.5 histogram implementation](https://github.com/fortio/fortio/blob/v1.69.5/stats/stats.go) · [CLI flags](https://github.com/fortio/fortio/blob/v1.69.5/cli/fortio_main.go)
- [glibc 2.41 search ordering](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_query.c) · [A/AAAA transport](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_send.c)
- [CoreDNS Kubernetes / autopath requirements](https://coredns.io/plugins/kubernetes/)
- [Kubernetes Service traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/) · [virtual IP handling](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [EC2 ENA network metrics](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html)
- [Karpenter disruption and cleanup conditions](https://karpenter.sh/docs/concepts/disruption/)
