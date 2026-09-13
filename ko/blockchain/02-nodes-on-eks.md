# EKS에서 블록체인 노드 운영

> **지원 버전**: Kubernetes 1.33+ (Amazon EKS), Hyperledger Fabric 2.5 / 3.x
> **마지막 업데이트**: 2026년 9월 13일

## 이 문서에서 다루는 것

- [기초 개념](./01-fundamentals.md)의 운영 특성을 실제 Kubernetes 구성으로 옮기는 방법 — StatefulSet, 스토리지, P2P 노출
- 동기화 상태를 헬스체크에 넣는 방법과, 그것이 왜 일반 헬스체크로는 안 되는가
- Ethereum 노드와 Hyperledger Fabric의 운영 차이, 그리고 하드포크를 일정 관리하는 방법

## 시작 질문 — EKS에서 운영해야 하는가

구성을 논하기 전에 이 질문이 먼저입니다. **블록체인 노드는 Kubernetes의 강점과 잘 맞지 않는 부분이 있습니다.**

| Kubernetes가 잘하는 것 | 블록체인 노드에서 |
|---|---|
| 빠른 스케줄링·재배치 | 상태 재구축 비용이 커서 재배치가 비쌈 |
| 수평 확장으로 처리량 증가 | Replica는 전체 RPC/read 용량·가용성을 늘릴 수 있지만 base-chain write/consensus 용량을 자동으로 높이지는 않음 |
| 선언적 롤링 업데이트 | 하드포크는 동시 전환 |
| 노드 간 Pod 이동 | 로컬 디스크에 묶임 |

그럼에도 EKS를 쓰는 근거는 있습니다.

| 근거 | 내용 |
|---|---|
| **운영 표준화** | 이미 EKS로 모든 워크로드를 운영 중이면 별도 스택을 늘리지 않는 것이 낫습니다 |
| **여러 체인·환경 운영** | 메인넷·테스트넷·여러 프로토콜을 같은 방식으로 관리 |
| **주변 구성요소와의 통합** | 인덱서, API 게이트웨이, 모니터링이 이미 클러스터에 있음 |
| **Fabric의 경우 공식 방향** | Hyperledger Fabric은 Kubernetes 오퍼레이터 생태계가 성숙 |

**반대로 EC2 단독이 나은 경우**: 노드가 소수(1~3개)이고 다른 클러스터 워크로드가 없다면, EKS의 추상화가 이점 없이 복잡도만 더합니다. 검증자 하나를 운영하는 데 EKS가 필요하지는 않습니다.

**판단 기준**: 블록체인 노드 **주변에 다른 워크로드가 있는가**입니다. 인덱서·API·모니터링이 클러스터에 있으면 노드도 함께 두는 것이 합리적이고, 노드만 덩그러니 있으면 EC2가 단순합니다.

## 기본 구성 — StatefulSet과 Headless Service

### 왜 Deployment가 아닌가

| 요구 | Deployment | StatefulSet |
|---|---|---|
| 안정적인 이름 (P2P 신원) | ✗ 랜덤 접미사 | ✓ `node-0`, `node-1` |
| Pod별 고정 볼륨 | ✗ 공유 또는 랜덤 | ✓ `volumeClaimTemplates`로 Pod별 PVC |
| 안정적인 DNS | ✗ | ✓ Headless Service와 함께 `node-0.svc...` |
| 순차적 기동·종료 | ✗ | ✓ |

[기초 개념](./01-fundamentals.md)에서 본 "안정적인 피어 신원"과 "Pod별 상태 유지" 요구가 정확히 StatefulSet의 제공 사항입니다.

### 불완전한 시험용 구조 — 배포 가능한 manifest가 아님
이 조각에는 필수 StatefulSet selector/template label·image/argument·headless Service·StorageClass와 post-Merge EL/CL Engine API/JWT 설정이 없습니다. 그대로 적용하지 않습니다. **실제 자금이나 validator signing key 없이** 격리된 시험 환경에서 리소스를 완성·검증합니다. JSON-RPC와 Engine API는 사설/인증 경로로 유지하고 P2P 연결 때문에 RPC·signing endpoint가 노출되지 않도록 합니다.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: eth-node
spec:
  serviceName: eth-node          # Headless Service 이름
  replicas: 2
  template:
    spec:
      terminationGracePeriodSeconds: 300   # 정상 종료에 시간이 필요
      containers:
        - name: execution
          # ... 실행 클라이언트
          ports:
            - { name: p2p-tcp, containerPort: 30303, protocol: TCP }
            - { name: p2p-udp, containerPort: 30303, protocol: UDP }
            - { name: rpc,     containerPort: 8545 }
          volumeMounts:
            - { name: data, mountPath: /data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: gp3-high-iops
        resources: { requests: { storage: 2Ti } }
```

세 가지가 일반 워크로드와 다릅니다.

**① `terminationGracePeriodSeconds`가 깁니다.** 블록체인 클라이언트는 종료 시 메모리의 상태를 디스크에 flush해야 합니다. 강제 종료되면 **데이터베이스가 손상되어 재동기화가 필요할 수 있습니다.** 기본 30초는 대개 부족합니다.

**② P2P 포트가 TCP와 UDP 둘 다입니다.** 디스커버리(UDP)와 실제 연결(TCP)이 분리된 프로토콜이 많습니다. 한쪽만 열면 피어를 못 찾거나 연결이 안 됩니다.

**③ 볼륨이 큽니다.** 아래 스토리지 절에서 다룹니다.

## 스토리지 — 가장 중요한 설계 결정

### 무엇이 병목인가

블록체인 노드의 디스크 사용 패턴은 **랜덤 읽기·쓰기가 많은 것**이 특징입니다. 상태 트리(Merkle Patricia Trie 등)를 탐색하고 갱신하는 작업이 흩어진 키를 건드리기 때문입니다.

그래서 **용량보다 IOPS가 먼저 병목이 됩니다.** 용량이 남아도 IOPS가 부족하면 동기화가 따라가지 못하고, 뒤처진 노드는 서비스할 수 없습니다.

| 요구 | 이유 |
|---|---|
| **높은 IOPS** | 랜덤 접근 패턴 |
| **낮은 지연** | 상태 조회가 블록 처리 경로에 있음 |
| **꾸준한 처리량** | 버스트가 아니라 지속적 부하 |

### EBS 볼륨 선택

| 볼륨 타입 | 적합성 |
|---|---|
| **gp3** | 기본 선택. **IOPS와 throughput을 용량과 독립적으로 설정** 가능한 것이 핵심 이점 |
| **io2 / io2 Block Express** | 더 높은 IOPS와 일관된 지연이 필요할 때 |
| **gp2** | 권장하지 않음 — IOPS가 용량에 연동되어 조정 불가 |
| **인스턴스 스토어 (NVMe)** | 가장 빠르지만 **인스턴스 정지 시 소실** — 재동기화 감수 가능한 경우만 |

**gp3의 독립 설정이 왜 중요한가**: gp2는 용량당 IOPS가 정해져 있어 IOPS를 늘리려면 필요 없는 용량을 사야 했습니다. gp3는 용량과 IOPS를 따로 정하므로 **실제 필요에 맞출 수 있습니다.** 구체적 차이는 [EBS gp2 vs gp3 실측 벤치마크](../storage/01-ebs-gp2-gp3-benchmark.md)를 참고하십시오.

**인스턴스 스토어의 트레이드오프**는 명확합니다 — 성능은 최고지만 상태가 사라질 수 있습니다. 재동기화 시간을 감수할 수 있고(스냅샷 복원 체계가 있고), 노드가 여러 개라 하나가 재동기화 중이어도 서비스에 문제없다면 선택할 수 있습니다.

### 용량 계획 — 증가한다는 점이 핵심

체인 데이터는 **단조 증가**합니다. 이것이 용량 계획의 성격을 바꿉니다.

| 항목 | 함의 |
|---|---|
| 계속 증가 | **볼륨 확장 계획이 필수** — 언젠가 반드시 필요 |
| 증가율이 프로토콜 활동에 의존 | 여유를 두고 알람 설정 |
| 프루닝 옵션 | 클라이언트가 과거 데이터를 버리는 모드 제공 — 아카이브가 필요 없으면 사용 |

**EBS 볼륨은 온라인 확장이 가능**하므로(확장 후 파일시스템 확장 필요), PVC에 `allowVolumeExpansion: true` StorageClass를 쓰고 디스크 사용률 알람을 걸어두는 것이 표준 대응입니다.

### 공식 하드웨어 가이던스 — EIP-7870

[EIP-7870](https://eips.ethereum.org/EIPS/eip-7870)과 [Run a node 안내](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)를 **초기 권고**로 사용하며 EKS instance/EBS volume의 보장값으로 보지 않습니다. 선택한 client·fork·pruning·실측 증가율을 검증합니다.

| 항목 | 최소 | **권장 (EIP-7870, full node)** |
|---|---|---|
| **CPU** | 2+ 코어 | 4+ 코어 (**검증자는 8+**) |
| **RAM** | 16 GB (32 GB 권장) | 32 GB (**검증자는 64 GB**) |
| **디스크** | **2 TB NVMe SSD** | **4 TB NVMe SSD** (DRAM-less·QLC 드라이브는 **비권장**) |
| **대역폭** | 25+ Mbit/s | 50 Mbit/s 하향 / 15+ Mbit/s 상향 (**검증자는 상향 25+**) |

읽는 방법에서 중요한 세 가지입니다.

**① 병목은 디스크입니다.** ethereum.org가 명시합니다 — "The bottleneck for your hardware is mostly disk space. Syncing the Ethereum blockchain is very input/output intensive." 앞에서 IOPS를 먼저 다룬 이유입니다.

**② EIP-7870은 hardware 권고이며 특정 EBS 설정의 충족 증명이 아닙니다.** EC2/EBS 지연·instance bandwidth·volume IOPS/throughput은 local NVMe와 다릅니다. 선택한 client·storage 설정으로 sync와 정상 처리 성능을 측정합니다.

**③ 2 TB 최소치는 수명이 정해져 있습니다.** ethereum.org는 2 TB가 "likely exceeded by 2027"이라고 적고 있습니다. **용량 계획에 증가를 반드시 넣어야 하는 근거**입니다.

::: warning 확인 필요
위 수치는 **full node** 기준입니다. **아카이브 노드는 훨씬 큰 스토리지가 필요하고, 실제 사용량은 클라이언트 종류·프루닝 설정·포크 시점에 따라 달라집니다.**

특히 Fusaka의 PeerDAS로 블롭 처리 방식이 바뀌었으므로, 사용할 클라이언트의 릴리스 노트에서 현재 요건을 확인하고 **PoC로 증가율을 직접 측정**하십시오.
:::

### 스냅샷 전략

[기초 개념](./01-fundamentals.md)에서 본 대로 **체인 데이터는 네트워크에서 재획득 가능하지만 시간이 걸립니다.** 그래서 백업의 목적이 "데이터 보존"이 아니라 **"복구 시간 단축"**입니다.

| 방식 | 특성 |
|---|---|
| **EBS 스냅샷** | 볼륨 전체. 복원 시 초기화 지연(lazy loading) 고려 필요 |
| **클라이언트 스냅샷 내보내기** | 클라이언트가 제공하는 export. 정합성 보장이 명확 |
| **재동기화** | 백업 없이 처음부터 — 시간 비용 |

**주의할 점**: 실행 중인 노드의 볼륨을 그냥 스냅샷하면 **데이터베이스가 중간 상태일 수 있습니다.** 정합성 있는 스냅샷을 위해서는 클라이언트를 정지하거나 클라이언트가 제공하는 정합성 보장 메커니즘을 써야 합니다.

## 헬스체크 — 일반 방식으로는 안 되는 이유

동기화 상태를 무시하는 health check는 stale node로 앱 트래픽을 보낼 수 있습니다. 이는 시험할 설계 위험이며 실측 운영 실수 순위는 아닙니다.

### 문제

일반적인 헬스체크는 "프로세스가 응답하는가"를 봅니다. 블록체인 노드에서 이것은 **불충분하고 위험합니다.**

동기화가 뒤처진 노드는:

- RPC 포트가 열려 있고 응답합니다 → liveness 통과
- 그런데 **오래된 체인 상태를 기준으로 답합니다** → 틀린 데이터 반환
- Service가 트래픽을 보냅니다 → 애플리케이션이 잘못된 잔액·상태를 봅니다

### 올바른 구분

| 프로브 | 무엇을 확인해야 하는가 |
|---|---|
| **startup** | 초기 동기화가 진행 중임 — 완료까지 오래 걸리므로 **넉넉한 `failureThreshold`** |
| **liveness** | 프로세스가 살아있고 응답 — 여기서 동기화를 보면 안 됨 (뒤처졌다고 죽이면 영원히 못 따라감) |
| **readiness** | **체인 선두에서 N블록 이내** — 서비스 가능 여부 |

**liveness와 readiness의 구분이 결정적입니다.**

- liveness에 동기화 조건을 넣으면 → 뒤처진 노드가 재시작되고 → 재시작으로 더 뒤처지고 → 무한 루프
- readiness에 넣지 않으면 → 뒤처진 노드가 트래픽을 받아 틀린 답을 반환

### 구현 방향

동기화 상태는 클라이언트의 RPC로 확인합니다. 프로토콜·클라이언트마다 메서드가 다르므로 래퍼 스크립트나 사이드카로 판정하는 구성이 일반적입니다.

```yaml
# 개념적 형태 — 실제 판정 로직은 클라이언트별로 다릅니다
readinessProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-sync.sh"]   # 선두와의 블록 차이 판정
  periodSeconds: 15
  failureThreshold: 3

livenessProbe:
  httpGet: { path: /, port: rpc }     # 응답 여부만
  periodSeconds: 30
  failureThreshold: 5

startupProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-alive.sh"]
  periodSeconds: 30
  failureThreshold: 240               # 초기 동기화에 긴 시간 허용
```

**임계값(N블록)은 애플리케이션 요구에 따라 정해야 합니다.** [기초 개념](./01-fundamentals.md)의 confirmation depth와 함께 결정할 사항입니다.

## P2P 노출 — 인바운드 연결 받기

### 왜 인바운드가 필요한가

아웃바운드만으로도 동기화는 됩니다. 하지만 인바운드를 받으면:

- 피어 수가 늘어 **전파가 빠르고 안정적**
- 네트워크에 기여 (퍼블릭 체인에서 상호 이익)

검증자라면 특히 중요합니다 — 블록 전파 지연이 성능(보상)에 직접 영향을 줍니다.

### 방법과 트레이드오프

| 방법 | 특성 |
|---|---|
| **`hostNetwork: true`** | 가장 단순. Pod가 노드 IP·포트를 직접 사용. **노드당 하나** 제약, 보안 심의 대상 |
| **`hostPort`** | 특정 포트만 노드에 매핑. 노드당 포트 충돌 관리 필요 |
| **NodePort Service** | Kubernetes 표준. 포트 범위 제약, 노드 IP 광고 문제 |
| **Pod별 LoadBalancer (NLB)** | 안정적 주소. **Pod 수만큼 LB 비용** |
| **인바운드 포기** | 아웃바운드만. 구성 단순, 피어 품질 저하 |

### 공통 함정 — 광고 주소

P2P 프로토콜은 자기 주소를 다른 피어에게 **광고**합니다. 컨테이너 안에서 본 주소(Pod IP)와 외부에서 접근 가능한 주소(노드 공인 IP, LB 주소)가 **다르면 다른 피어가 접속하지 못합니다.**

대부분의 클라이언트가 광고 주소를 명시하는 옵션을 제공합니다(`--nat extip:<addr>` 형태 등). **이것을 설정하지 않으면 인바운드를 열어도 피어가 오지 않습니다** — 열었는데 안 되는 전형적 원인입니다.

Pod별로 다른 주소를 광고해야 하므로, StatefulSet의 ordinal이나 downward API로 각 Pod가 자기 주소를 알아내는 초기화 로직이 필요합니다.

## 리소스 — 버스트가 아니라 지속 부하

블록체인 노드는 **꾸준히 CPU와 IOPS를 씁니다.** 블록이 계속 오고, 계속 검증하고, 계속 상태를 갱신합니다.

| 항목 | 권고 |
|---|---|
| **CPU limit** | **신중히.** throttling이 블록 처리 지연으로 이어지고, 검증자는 성능이 보상에 연결됨. [커널 튜닝](../kernel/03-eks-node-tuning.md)의 throttling 진단 참고 |
| **메모리** | 클라이언트가 상태 캐시에 메모리를 많이 씀. **limit을 넉넉히**, OOM은 DB 손상 위험 |
| **request = limit** | Guaranteed QoS로 축출 우선순위를 낮춤 |
| **노드 전용화** | taint/toleration으로 다른 워크로드와 분리 — 노이지 네이버 방지 |
| **파일 디스크립터** | 피어 연결 수만큼 소켓. 한도 상향 검토 ([커널 튜닝](../kernel/03-eks-node-tuning.md)) |

**CPU limit에 대한 판단**이 특히 중요합니다. [커널 문서](../kernel/01-container-primitives.md)에서 본 대로 CPU limit은 대역폭 제한이라 주기 내에 할당량을 소진하면 강제로 멈춥니다. 블록 처리가 그 순간에 걸리면 지연이 생기고, 검증자에게는 놓친 기회가 됩니다.

전용 노드는 tenant 간 경합을 줄이지만 kubelet·CNI/CSI·관측성·OS 서비스는 노드를 공유합니다. 앱 CPU limit을 생략해도 reservation과 여유를 유지하고 지속 부하에서 지연·sync·node health를 시험합니다.

## Ethereum 노드 — 두 클라이언트 구조

Ethereum이 PoS로 전환한 뒤 노드는 **두 개의 프로세스**로 나뉩니다.

| 클라이언트 | 역할 | 예 |
|---|---|---|
| **실행 클라이언트** (EL) | 거래 실행, 상태 관리, EVM | Geth, Nethermind, Besu, Erigon, Reth |
| **컨센서스 클라이언트** (CL) | PoS 합의, 블록 제안·검증 | Prysm, Lighthouse, Teku, Nimbus, Lodestar |

둘은 **Engine API**로 통신하며, JWT 시크릿을 공유합니다.

### 배치 결정

| 방식 | 장단점 |
|---|---|
| **같은 Pod의 두 컨테이너** | `localhost` 통신으로 단순, 함께 스케줄·재시작. 리소스를 함께 요청 |
| **별개 StatefulSet** | 독립 스케일·업그레이드 가능. Engine API 연결 관리 필요 |

**같은 Pod가 기본 선택**입니다 — 두 클라이언트가 1:1로 짝지어 동작하고 Engine API 지연이 성능에 영향을 주므로, 같은 Pod의 `localhost`가 자연스럽습니다.

**클라이언트 다양성**도 언급할 가치가 있습니다. 특정 클라이언트에 버그가 있을 때 네트워크 전체가 영향받지 않도록, 커뮤니티는 클라이언트를 분산할 것을 권장합니다. 여러 노드를 운영한다면 **서로 다른 클라이언트 조합**을 쓰는 것이 방어적입니다.

### 최근 프로토콜 변경 — 운영에 영향을 준 것들

다음은 보장된 미래 주기가 아니라 **날짜가 정해진 프로토콜 이력**입니다. 업그레이드 계획 전 [roadmap](https://ethereum.org/roadmap/)·활성화 발표·선택한 client release note를 확인합니다.

| 시점 | 업그레이드 | 운영 관점의 의미 |
|---|---|---|
| **2025년 5월 7일** | **Pectra** mainnet | EIP-7251은 해당 validator의 최대 effective balance를 2,048 ETH로 높였으며 consolidation은 record를 바꾸지만 process/VM 수를 반드시 줄이지는 않음 |
| **2025년 12월 3일** | **Fusaka** 메인넷 (에폭 411392) | 핵심은 **PeerDAS**(Peer Data Availability Sampling) — 블롭 데이터를 전체가 아니라 샘플링으로 검증. 블롭 처리량 확대 |

Validator identity/key는 **별도 process나 VM과 동일하지 않습니다**. 하나의 validator client가 공유 beacon-node stack에서 여러 키를 관리할 수 있습니다. EIP-7251 consolidation은 validator record·키 관리 작업을 줄일 수 있지만 비례하는 인프라·비용 절감을 증명하지는 않습니다. 실제 client 구성을 측정하고 키 이전 시 slashing protection을 유지합니다.

**PeerDAS는 스토리지·대역폭 계획에 영향**을 줍니다. 블롭 처리 방식이 바뀌면 노드가 보관·전송하는 데이터 양이 달라지므로, 기존 사이징 기준을 재검토해야 합니다.

## Hyperledger Fabric — permissioned 체인의 운영

Fabric은 성격이 다릅니다. **참여자가 알려진 컨소시엄 체인**이므로 [기초 개념](./01-fundamentals.md)에서 본 대로 합의 방식과 운영 특성이 달라집니다.

### 구성요소

| 구성요소 | 역할 | Kubernetes 배치 |
|---|---|---|
| **Peer** | 원장 보관, 체인코드 실행, 거래 검증 | StatefulSet + 영구 볼륨 |
| **Orderer** | 설정한 consensus로 transaction 순서 결정: CFT Raft 또는 Fabric 3.x SmartBFT | StatefulSet + 영속 저장소. 유효 state 갱신은 peer validation이 결정 |
| **CA** (Fabric CA) | 멤버 인증서 발급 | Deployment + 영구 볼륨 |
| **Chaincode** | 스마트 컨트랙트 | 외부 빌더 또는 별도 Pod |

### 운영 포인트

**① Orderer의 영구 볼륨은 타협 불가입니다.** Raft 로그가 소실되면 합의 상태가 깨집니다. Pod는 업데이트로 재시작되므로 **영구 볼륨 없이 운영하면 데이터를 잃습니다.**

**② 인증서 관리가 핵심 작업입니다.** Fabric은 MSP(Membership Service Provider)로 조직과 신원을 관리하며, 모든 통신이 TLS입니다. 관리해야 할 것들:

- MSP 서명 인증서와 키
- TLS 인증서 (peer, orderer, CA 각각)
- **만료 관리** — 인증서 만료가 실제로 장애를 만듭니다

인증서 만료는 중요한 장애 위험이지만 이 문서에는 빈도 데이터가 없습니다. MSP·TLS credential 갱신을 감시·연습하고 operator/client 버전 호환성을 검증합니다.

**③ 오퍼레이터 활용.** Fabric은 Kubernetes 오퍼레이터 생태계가 있습니다.

| 오퍼레이터 | 특성 |
|---|---|
| [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) | CNCF 오퍼레이터 패턴. CA·Peer·Orderer·Console을 CR로 선언 |
| [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric) | Hyperledger Bevel 프로젝트. Fabric 2.3~3.x 지원 |

오퍼레이터를 쓰면 반복적인 구성 작업이 선언적 리소스 적용으로 바뀝니다. **직접 YAML을 조립하는 것보다 오퍼레이터로 시작하는 것을 권합니다** — Fabric의 구성 복잡도가 높아 수동 관리 시 실수가 잦습니다.

### Ethereum과 Fabric 비교

| 항목 | Ethereum 노드 | Hyperledger Fabric |
|---|---|---|
| **참여** | permissionless | permissioned (MSP) |
| **Consensus** | PoS | 설정한 orderer mode: Raft(CFT) 또는 SmartBFT(Fabric 3.x) |
| **Finality** | 프로토콜 가정 아래 checkpoint 기반 | Consensus 가정 아래 ordering은 확정되지만 peer가 transaction을 계속 검증하며 순서가 정해진 transaction도 invalid일 수 있음 |
| **주 운영 부담** | 동기화, 디스크 증가, 하드포크 | **인증서 만료**, 채널·정책 관리 |
| **P2P 노출** | 인바운드 권장 | 조직 간 연결 (알려진 엔드포인트) |
| **스토리지 증가** | 큼, 단조 증가 | 상대적으로 작음 (거래량 의존) |
| **업그레이드** | 외부 일정 (하드포크) | 컨소시엄 합의로 결정 |

**가장 큰 운영 차이**: Ethereum은 **외부에서 정해진 일정**(하드포크)에 맞춰야 하고, Fabric은 **컨소시엄이 일정을 정할 수 있습니다.** 대신 Fabric은 멤버 간 합의 절차가 필요합니다.

## 하드포크 일정 관리

[기초 개념](./01-fundamentals.md)에서 하드포크가 "기한 있는 마이그레이션"이라고 했습니다. 실무 절차로 정리하면:

| 단계 | 내용 |
|---|---|
| **1. 구독** | 프로토콜 공식 블로그, 클라이언트 릴리스 노트, 운영자 커뮤니티 |
| **2. 일정 등록** | 포크 예정 블록/시각을 팀 캘린더에 등록. **여유를 두고 목표일 설정** |
| **3. 테스트넷 검증** | 메인넷보다 먼저 포크되는 테스트넷에서 검증 |
| **4. 이미지 준비** | 포크 지원 버전으로 이미지 빌드·스캔 |
| **5. 순차 업그레이드** | 포크 시점 **이전에 완료.** 노드가 여러 개면 하나씩 |
| **6. 포크 시점 모니터링** | 체인 높이, 피어 수, 포크 인식 여부 |
| **7. 사후 확인** | 모든 노드가 같은 체인에 있는지 |

호환되지 않는 client는 활성화 후 canonical chain 추적을 중단하거나 갈라질 수 있습니다. 정상 전파/sync 지연을 고려하며 독립적인 신뢰 소스에서 **같은 block height와 finality 상태**를 비교합니다. 서로 다른 최신 head가 즉시 일치해야 한다고 판단하지 않습니다.

## 모니터링

| 카테고리 | 지표 | 왜 |
|---|---|---|
| **동기화** | 체인 선두와의 블록 차이 | 서비스 가능 여부의 핵심 |
| **동기화** | 블록 처리 지연 | 뒤처지기 시작하는 조기 신호 |
| **P2P** | 피어 수 | 급감은 네트워크·설정 문제 |
| **P2P** | 인바운드/아웃바운드 비율 | 인바운드 0이면 노출 설정 실패 |
| **스토리지** | 디스크 사용률·증가율 | 확장 시점 예측 |
| **스토리지** | IOPS, 큐 깊이, 지연 | 병목 확인 |
| **합의** | reorg 발생 | 애플리케이션에 알려야 함 |
| **검증자** | 참여율, 놓친 기회 | 보상에 직결 |
| **Fabric** | **인증서 만료까지 남은 기간** | 장애 예방 |
| **리소스** | CPU throttling (`nr_throttled`) | [커널 문서](../kernel/01-container-primitives.md) |

**"체인 선두와의 차이"가 가장 중요한 단일 지표**입니다. 이 값이 커지기 시작하면 원인(IOPS, CPU, 피어, 네트워크)을 찾아야 하고, 임계를 넘으면 readiness에서 빠져야 합니다.

## 정리

- **먼저 EKS에서 운영해야 하는지 판단하십시오.** 판단 기준은 노드 주변에 다른 워크로드가 있는가입니다. 노드만 있으면 EC2가 단순합니다.
- **StatefulSet + Headless Service + 영구 볼륨**이 기본 골격이고, `terminationGracePeriodSeconds`를 넉넉히 주어야 합니다(강제 종료 시 DB 손상 위험).
- 스토리지는 **용량보다 IOPS가 먼저 병목**입니다. gp3의 용량-IOPS 독립 설정이 핵심 이점이고, 볼륨 확장 계획은 필수입니다.
- Process liveness와 synchronization readiness를 분리·시험하며 이 장은 장애 빈도 순위를 제공하지 않습니다.
- P2P 인바운드를 열 때 **광고 주소 설정을 빠뜨리면 피어가 오지 않습니다.**
- 리소스는 버스트가 아니라 지속 부하입니다. **노드를 전용화하고 CPU limit을 신중히** 결정하십시오.
- Ethereum은 EL·CL client를 사용하며 validator identity/key와 process·VM 수는 별개입니다. Consolidation 자체로 비용 절감이 입증되지는 않습니다.
- Fabric의 주 운영 부담은 **인증서 만료**입니다. 오퍼레이터로 시작하고 갱신을 자동화하십시오.
- 하드포크 후에는 **다른 노드·익스플로러와 블록 해시를 대조**해 같은 체인에 있는지 확인해야 합니다.

다음: [Amazon Managed Blockchain](./03-managed-blockchain.md)에서 이 부담들을 관리형으로 넘길 수 있는 범위를 봅니다.

## 참고 자료

- [Ethereum — Run a node](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)
- [EIP-7870: Hardware and Bandwidth Recommendations](https://eips.ethereum.org/EIPS/eip-7870) — 공식 하드웨어 가이던스
- [Ethereum roadmap](https://ethereum.org/roadmap/) / [Pectra](https://ethereum.org/roadmap/pectra/) / [Fusaka](https://ethereum.org/roadmap/fusaka/)
- [Pectra Mainnet Announcement (Ethereum Foundation)](https://blog.ethereum.org/2025/04/23/pectra-mainnet)
- [Fusaka Mainnet Announcement (Ethereum Foundation)](https://blog.ethereum.org/2025/11/06/fusaka-mainnet-announcement)
- [Hyperledger Fabric — Deploying a production network](https://hyperledger-fabric.readthedocs.io/en/latest/deployment_guide_overview.html)
- [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) / [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric)
- [EBS gp2 vs gp3 실측 벤치마크](../storage/01-ebs-gp2-gp3-benchmark.md) / [EKS 노드 커널 튜닝](../kernel/03-eks-node-tuning.md)
