# SNAT 없는 Pod 연결과 PrivateLink 검증

> **지원 버전**: EKS 1.36, Cilium 1.18.13 (AWS 빌드), CoreDNS add-on v1.14.7-eksbuild.10, VPC CNI 기본 구성
> **마지막 업데이트**: 2026년 10월 19일

방화벽이 온프레미스 Pod를 노드 IP가 아니라 **Pod IP로 식별**해야 하는 경우가 있습니다. 이 글은 그 요구사항을 맞추려고 Cilium을 native routing과 masquerade 해제로 바꾼 뒤, 클러스터 안팎의 연결 38가지를 실제로 시험한 기록입니다. 온프레미스 Pod가 인터넷을 거치지 않고 AWS API(STS, S3)를 쓰는 PrivateLink 경로와, 링크가 끊겼을 때의 DNS 동작도 함께 확인했습니다.

시험 환경은 온프레미스를 **시뮬레이션한 구성**입니다. 두 번째 VPC를 Transit Gateway(TGW)로 연결하고, 그 안의 EC2를 hybrid node로 등록했습니다. EC2를 hybrid node로 쓰는 것은 지원되지 않으며 hybrid node 요금이 부과됩니다. 수치는 2026년 10월 19일 1회 측정값입니다. 실제 온프레미스(DX 또는 VPN) 구성에서는 다시 확인해야 합니다.

## 먼저 알아야 할 지원 범위

[CNI 구성 문서](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)의 "Supported capabilities" 표에서 AWS가 지원하는 Cilium **Networking Mode는 "VXLAN encapsulation"뿐**입니다. 같은 문서는 masquerade를 끌 수 있다고 설명하며, 이때 Pod CIDR이 온프레미스 네트워크에서 라우팅 가능해야 하고 이를 위해 Cilium BGP Control Plane을 권장합니다.

| 구성 | Pod IP가 보이는 구간 | AWS 지원 | Hybrid Nodes Gateway |
|---|---|---|---|
| VXLAN + masquerade (기본) | 없음. 클러스터 밖으로 나가면 노드 IP | 지원 | 사용 가능 |
| VXLAN + masquerade 해제 + BGP | 클라우드 ↔ 온프레미스, 온프레미스 서버 | 지원 | 사용 가능 |
| **native routing + masquerade 해제** (이 글) | 위 구간에 더해 **hybrid 노드 사이 구간** | **지원 범위 밖** | 사용 불가 (VTEP, 즉 VXLAN 필요) |

VXLAN을 유지하면 hybrid 노드 사이 트래픽은 바깥 헤더가 노드 IP라서, 그 구간의 방화벽은 Pod IP를 볼 수 없습니다. 이 구간까지 Pod IP가 필요한지에 따라 선택이 갈립니다. 대부분은 두 번째 줄(지원 범위 안)로 충분합니다. 세 번째 줄은 AWS 지원 대신 Cilium 상용 지원이나 내부 역량이 있을 때만 고려하세요.

## 구성

### 네트워크 대역

| 대역 | 값 | 비고 |
|---|---|---|
| 클라우드 VPC | `10.0.0.0/16` | 클라우드 노드와 Pod (VPC CNI) |
| remote node network | `172.18.0.0/16` | 시뮬레이션 온프레미스 VPC (hybrid 노드 호스트) |
| remote pod network | `172.17.0.0/16` | Cilium cluster-pool, 노드당 `/25` |
| Service | `172.16.0.0/16` | |

### Cilium 값 (기본 values 위에 덧씌움)

```yaml
routingMode: native
ipv4NativeRoutingCIDR: "172.17.0.0/16"   # remote pod network
autoDirectNodeRoutes: false              # 호스트가 서로 다른 서브넷, 온프레미스 라우터가 전달
enableIPv4Masquerade: false              # SNAT 없음
vtep:
  enabled: false                         # gateway를 쓰지 않음
```

Cilium chart는 ConfigMap이 바뀌어도 agent를 다시 시작하지 않습니다(`rollOutCiliumPods` 기본값 `false`). 값을 바꾼 뒤 `kubectl -n kube-system rollout restart ds/cilium`이 필요합니다. 재시작 뒤 `cilium-dbg status`가 `Routing: Network: Native`인지 확인합니다. ConfigMap에는 `tunnel-protocol: vxlan`이 남아 있지만 동작에는 영향이 없었고, 호스트 NIC 캡처에서 VXLAN(UDP 8472, 4789) 패킷은 0건이었습니다.

### 라우팅과 SNAT 예외

| 위치 | 설정 | 이유 |
|---|---|---|
| 온프레미스 라우터 | 노드별 Pod 블록(`/25`)을 해당 노드로 | 운영 환경은 Cilium BGP Control Plane으로 광고합니다. 시험에서는 온프레미스 VPC route table에 정적 라우트를 넣었습니다. 노드가 다시 조인해 Pod 블록이 바뀌면 정적 라우트가 틀어집니다. |
| 클라우드 route table, TGW | `172.17.0.0/16` → 온프레미스 방향 | 클라우드에서 Pod IP로 바로 돌아오도록 |
| VPC CNI | `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS=172.17.0.0/16,172.18.0.0/16` | 클라우드 Pod가 온프레미스로 갈 때도 Pod IP 유지. **노드 대역(172.18)을 빼면 온프레미스 서버에는 클라우드 노드 IP가 보입니다.** |
| 클러스터 SG | `172.17.0.0/16` 전체, `172.18.0.0/16`의 UDP/TCP 53 | Pod 트래픽, hostNetwork Pod의 DNS(노드 IP로 CoreDNS 호출) |

## 연결 매트릭스 결과

모든 항목은 HTTP 응답만 보지 않고 **서버가 기록한 출발지 주소**를 확인했습니다. 서버는 nginx 접근 로그(`$remote_addr`)나, 쿠버네티스 밖 서버의 경우 `socat`이 받은 peer 주소를 그대로 돌려주는 방식입니다. 결과는 38개 PASS, 0개 FAIL이었습니다.

| 구간 | 항목 | 확인한 것 | 결과 |
|---|---|---|---|
| Pod 간 직접 | 7 | 같은 hybrid 노드, hybrid 노드 사이, hybrid ↔ 클라우드 양방향, 클라우드 사이 | 서버가 본 출발지 = 클라이언트 Pod IP |
| ClusterIP Service | 3 | hybrid → hybrid 백엔드, hybrid → 클라우드 백엔드, 클라우드 → hybrid 백엔드 | kube-proxy는 목적지만 바꾸고 출발지 Pod IP 유지 |
| DNS | 4 | hybrid Pod 2개와 hostNetwork Pod의 Service 이름, 공용 이름 | CoreDNS(클라우드 노드)와 VPC resolver로 해석 |
| Kubernetes API | 2 | `kubernetes.default.svc/livez`, ServiceAccount 토큰 | 200, 403(인증됨, RBAC 없음) |
| control plane → hybrid | 3 | API server proxy(webhook 경로), `exec`와 `logs`, metrics-server | proxy 요청의 출발지는 클라우드 VPC의 EKS 관리 ENI |
| 쿠버네티스 밖 온프레미스 서버 | 2 | hybrid Pod, 클라우드 Pod → hybrid 호스트의 `socat` | 서버가 172.17.x, 10.0.x Pod IP를 받음 |
| 인터넷 | 3 | hybrid Pod 2개, 클라우드 Pod 1개 | 모두 클라우드 NAT gateway 하나로 나감 (경로상 유일한 주소 변환) |
| Cilium 정책 | 3 | hybrid Pod에 `fromCIDR: 10.0.0.0/16` | hybrid Pod 차단, 클라우드 Pod 허용, 삭제 후 복구 |
| MTU, 대용량 | 2 | 32 MiB 양방향 sha256 비교 | 일치. Pod MTU 9001, DF ping 8500 바이트 패킷 통과 |
| ALB ip 타깃 | 1 | hybrid Pod 2개 | healthy |
| PrivateLink | 8 | 아래 절 | 모두 PASS |

`fromCIDR` 정책이 동작한 것도 SNAT이 없다는 뜻입니다. 클라우드 Pod는 VPC CNI를 쓰므로 Cilium identity가 없습니다. 그래서 정책은 IP 대역으로만 쓸 수 있고, 그 정책이 맞으려면 Pod IP가 그대로 도착해야 합니다.

MTU는 Pod가 9001, TGW 한도가 8500입니다. TCP는 TGW가 MSS를 조정해 문제가 없었습니다. UDP처럼 MSS 조정이 없는 프로토콜이나 DX, VPN 경로에서는 경로 MTU를 따로 확인하세요.

### 처음 실행에서 실패한 세 가지

| 증상 | 원인 | 조치 |
|---|---|---|
| hostNetwork Pod에서 Service 이름 해석 실패 | hostNetwork Pod는 노드 IP(172.18.x)로 CoreDNS를 부르는데, 클러스터 SG에 이 대역의 53번이 없었음 | 클러스터 SG에 `172.18.0.0/16`의 UDP, TCP 53 허용 |
| 클라우드 Pod → 온프레미스 서버에서 노드 IP가 보임 | VPC CNI SNAT 제외 대역에 Pod 대역만 있고 온프레미스 노드 대역이 없었음 | `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS`에 `172.18.0.0/16` 추가 |
| 익명 `GET /version`이 401 | EKS 1.36은 익명 요청을 health endpoint에만 허용 | 연결 확인은 `/livez`나 `/readyz`로 |

## 온프레미스 Pod에서 PrivateLink로 AWS API 호출

온프레미스 Pod가 AWS API를 쓸 때 인터넷으로 나가지 않게 하려면 클라우드 VPC에 interface endpoint를 두고 DX나 VPN으로 들어가게 합니다.

```
hybrid Pod (172.17.x)
  → CoreDNS → VPC resolver: sts.<region>.amazonaws.com, s3.<region>.amazonaws.com이 endpoint ENI(10.0.x)로 해석
  → TGW (실환경은 DX/VPN), 출발지 Pod IP 유지
  → STS, S3 interface endpoint (2 AZ, private DNS)
```

hybrid Pod는 클러스터 DNS(CoreDNS)를 거쳐 VPC resolver로 이름을 풀기 때문에, endpoint의 private DNS가 그대로 적용됩니다. 쿠버네티스 밖의 온프레미스 서버가 같은 endpoint를 쓰려면 [Route 53 Resolver inbound endpoint](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-inbound-queries.html)로 이름을 넘겨야 합니다.

### 구성 요소

| 구성 요소 | 설정 |
|---|---|
| STS interface endpoint | private DNS 사용 |
| S3 interface endpoint | private DNS 사용. **gateway endpoint가 없는 VPC에서는 `DnsOptions.PrivateDnsOnlyForInboundResolverEndpoint: AllResolvers`를 지정.** 지정하지 않은 첫 시도는 "To set PrivateDnsOnlyForInboundResolverEndpoint to true, the VPC must have a Gateway endpoint" 오류로 생성되지 않았습니다. |
| endpoint SG | TCP 443을 `10.0.0.0/16`(VPC)과 `172.17.0.0/16`(hybrid Pod)에서만 허용. 노드 대역 `172.18.0.0/16`은 일부러 넣지 않음 |
| IAM | 클러스터 OIDC provider, ServiceAccount에 연결한 역할(IRSA) |
| 버킷 정책 | 테스트 역할은 `aws:SourceVpce`가 S3 endpoint일 때만 허용 |

S3 gateway endpoint는 [온프레미스에서 접근할 수 없습니다](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html). 온프레미스 Pod용으로는 interface endpoint가 필요합니다.

버킷 정책은 아래처럼 특정 역할만 endpoint 밖에서 막습니다. 운영자 같은 다른 주체는 영향을 받지 않습니다.

```json
{
  "Sid": "TestRoleOnlyThroughEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::<bucket>", "arn:aws:s3:::<bucket>/*"],
  "Condition": {
    "StringNotEquals": {"aws:SourceVpce": "<s3-endpoint-id>"},
    "ArnEquals": {"aws:PrincipalArn": "<test-role-arn>"}
  }
}
```

### IRSA와 Pod Identity

IRSA는 Pod가 projected token으로 직접 STS `AssumeRoleWithWebIdentity`를 부르므로 그 호출부터 STS endpoint로 갑니다. 클러스터에 OIDC provider가 없으면 먼저 만들어야 합니다. Pod `env`에 `AWS_STS_REGIONAL_ENDPOINTS=regional`을 두면 리전 STS 이름을 써서 private DNS가 적용됩니다.

EKS Pod Identity는 hybrid 노드에서 [별도 설정](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)이 필요합니다. nodeadm 설정의 `enableCredentialsFile`과, Pod Identity Agent add-on 구성 `{"daemonsets":{"hybrid":{"create":true}}}`가 있어야 hybrid 노드에 agent가 뜹니다. 시험 클러스터의 기본 agent DaemonSet은 hybrid 노드를 제외하고 있어서 이번에는 IRSA를 썼습니다.

### 결과 (8개 모두 PASS)

| 확인 | 결과 |
|---|---|
| hybrid Pod에서 `sts`, `s3`, 버킷 호스트 이름 해석 | 모두 endpoint ENI의 10.0.x 주소 |
| hybrid Pod: `sts get-caller-identity` (IRSA) | assumed-role ARN 반환, 토큰 교환이 STS endpoint로 |
| hybrid Pod: `PutObject` | 성공 (버킷 정책이 endpoint 밖을 막으므로 endpoint를 탔다는 증거) |
| 클라우드 Pod: 같은 객체 `GetObject` | 같은 내용 |
| 같은 노드의 Pod와 hostNetwork Pod에서 STS ENI:443 | Pod(172.17.x)는 HTTP 302, hostNetwork(172.18.x)는 타임아웃 |
| 같은 역할로 endpoint 밖(작업 PC)에서 S3 | `aws:SourceVpce` 조건으로 거부 |

같은 노드에서 나간 트래픽인데 Pod는 통과하고 hostNetwork는 막혔습니다. **AWS 쪽 SG에서도 온프레미스 Pod를 Pod 대역으로 구분할 수 있다**는 뜻이고, SNAT이 없다는 가장 직접적인 증거입니다.

## 링크가 끊기면 DNS는 어떻게 되나

TGW 라우트 테이블에 blackhole 라우트(온프레미스 노드와 Pod 대역, `/17`)를 넣어 DX나 VPN 단절을 약 95초 동안 재현했습니다. 라우트 변경이 반영되는 데 약 17초가 걸렸습니다. hybrid 노드마다 probe Pod가 1초 간격으로 온프레미스 Service 이름과 클라우드 Service 이름을 풀고, 온프레미스 Service를 이름과 ClusterIP로 각각 호출했습니다. 단절 중 hybrid 노드는 `NotReady`가 됐지만 Pod는 계속 실행됐고(probe 기록이 끊기지 않음), 첫 회차에서는 복구 뒤 약 23초에 `Ready`로 돌아왔습니다.

| 구성 | 단절 중 hybrid Pod (이름 해석) | 온프레미스 Service 호출 | 비고 |
|---|---|---|---|
| 기본: CoreDNS 2개가 모두 클라우드 노드 | **모든 이름 해석 실패** (샘플 43~44개 중 26개 실패) | ClusterIP는 200, 이름으로는 실패 | 온프레미스 안 통신은 살아 있지만 이름을 못 풂 |
| zone label + 3개 + `PreferSameZone` (문서 예시와 다른 값) | 절반가량 실패 (76~80개 중 38~44개) | 이름 호출이 간헐적으로 실패 | Cilium이 hint를 무시하고 끊긴 클라우드 CoreDNS로도 분산 |
| zone label + 4개 + **`PreferClose`** + zone 분산 강제 + Cilium 재시작 | **실패 0** (96~97개 모두 성공) | 이름, ClusterIP 모두 200 | 클라우드 Pod는 이름 해석 정상, 온프레미스 호출만 실패(예상대로) |

단계마다 확인한 원인은 다음과 같습니다.

1. **AWS 문서의 값 `PreferClose`를 그대로 쓰세요. Cilium은 `PreferSameZone`을 인식하지 않았습니다.** AWS 문서 예시는 `trafficDistribution: PreferClose`입니다. 시험에서는 Kubernetes 1.35에서 deprecated 별칭이 됐다는 이유로 새 이름 `PreferSameZone`을 넣었고, 이것이 절반 실패의 원인이었습니다. hybrid 노드의 ClusterIP 부하 분산은 kube-proxy가 아니라 Cilium BPF가 맡습니다(`kubeProxyReplacement: false`여도 마찬가지). EndpointSlice에 zone hint가 있었지만 `cilium-dbg bpf lb list`에는 CoreDNS 백엔드 3개가 모두 남아 있었습니다. `trafficDistribution: PreferClose`로 바꾸자 온프레미스 백엔드 2개만 남았습니다. EndpointSlice의 hint만 보면 두 값의 차이가 드러나지 않으므로, hybrid 노드의 Cilium에서 백엔드 목록을 직접 확인하세요.
2. **zone label은 조인할 때 붙이세요.** 시험에서는 label을 나중에 붙인 뒤 `kubectl -n kube-system rollout restart ds/cilium`으로 Cilium을 다시 시작했습니다. 재시작 없이도 반영되는지는 확인하지 않았습니다. nodeadm 설정의 kubelet `--node-labels=topology.kubernetes.io/zone=<이름>`으로 조인할 때 붙이면 이 문제를 피할 수 있습니다.
3. **CoreDNS가 없는 클라우드 AZ도 문제입니다.** 같은 zone에 CoreDNS가 없는 클라우드 Pod는 전체 백엔드로 분산되고, 단절 시 온프레미스 CoreDNS로 간 질의가 실패합니다. 클라우드 AZ마다 하나, 온프레미스에 하나 이상이 필요합니다.
4. **`preferred` anti-affinity는 배치를 보장하지 않았습니다.** CoreDNS를 재시작한 뒤 온프레미스 replica가 1개로 줄어든 적이 있습니다. `topologySpreadConstraints`에 `whenUnsatisfiable: DoNotSchedule`을 걸어 zone마다 최소 하나를 강제했습니다.
5. **hybrid 노드의 CoreDNS는 PrivateLink를 우회시킵니다.** hybrid 노드의 CoreDNS는 노드의 resolver(온프레미스 DNS)로 넘기므로 `sts`, `s3` 이름이 공인 IP로 풀렸습니다. 호출은 NAT를 거쳐 인터넷으로 성공해 겉보기에는 문제가 없지만, S3 요청은 `aws:SourceVpce` 버킷 정책에 거부되어 매트릭스에서 4개가 FAIL이 됐습니다. 클라우드 VPC에 Route 53 Resolver inbound endpoint를 두고 CoreDNS에 `amazonaws.com` 블록을 추가해 해결했습니다. 실제 온프레미스에서는 온프레미스 DNS 서버의 조건부 전달 규칙이 같은 역할을 합니다.

최종 CoreDNS add-on 구성 값입니다(`aws eks update-addon --configuration-values`).

```json
{
  "replicaCount": 4,
  "trafficDistribution": "PreferClose",
  "topologySpreadConstraints": [{
    "maxSkew": 1, "topologyKey": "topology.kubernetes.io/zone", "whenUnsatisfiable": "DoNotSchedule",
    "labelSelector": {"matchLabels": {"k8s-app": "kube-dns"}}
  }],
  "corefile": "...기본 .:53 블록...\namazonaws.com:53 {\n    errors\n    cache 30\n    forward . <inbound endpoint IP 1> <inbound endpoint IP 2>\n}"
}
```

`corefile` 값은 Corefile 전체를 바꾸므로 기본 `.:53` 블록을 그대로 포함해야 합니다. Corefile을 바꾼 뒤 hybrid 노드의 CoreDNS 하나는 ConfigMap 반영이 늦어 한동안 옛 설정으로 답했습니다. `rollout restart deploy/coredns`로 맞췄습니다. inbound endpoint의 SG는 53번을 VPC 대역과 hybrid Pod 대역에만 엽니다. 단절 중에는 inbound endpoint에도 닿지 않으므로 AWS API 이름은 풀리지 않습니다. 어차피 endpoint에도 닿을 수 없는 상황입니다.

## 운영할 때 볼 것

- **CoreDNS 위치**: AWS는 mixed mode 클러스터에서 hybrid 노드와 클라우드 노드에 CoreDNS를 각각 1개 이상 두라고 권장합니다([Configure CoreDNS replicas](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)). 위 절의 실측처럼 zone label, zone 분산, `trafficDistribution`, Cilium `loadBalancer.serviceTopology: true`가 모두 맞아야 단절 중에 효과가 있습니다. 바꾼 뒤에는 링크를 실제로 끊어 확인하세요.
- **webhook과 control plane 경로**: API server proxy의 출발지는 클라우드 VPC의 EKS 관리 ENI였습니다. hybrid 노드에서 webhook을 돌리려면 Pod CIDR이 라우팅 가능해야 하고, 온프레미스 방화벽에서 이 ENI가 있는 VPC 대역을 허용해야 합니다.
- **정적 라우트 드리프트**: 노드가 다시 조인하면 Pod 블록이 바뀔 수 있습니다. BGP를 쓰지 않는다면 조인 뒤 라우트를 다시 맞추는 절차가 필요합니다.
- **인터넷 egress**: 이 구성은 온프레미스 기본 경로를 클라우드로 보내 NAT gateway 하나로 나갔습니다. 온프레미스 자체 인터넷 경로를 쓰는 경우, 그 경로의 NAT와 방화벽 정책이 Pod 대역을 알아야 합니다.
- **비용**: interface endpoint는 AZ별 시간 요금과 처리 GB 요금이 있습니다.

## 퀴즈

* [SNAT 없는 Pod 연결과 PrivateLink 검증 퀴즈](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## 참고 자료

* [Configure CNI for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html): 지원 Networking Mode, masquerade, BGP 권장
* [Prepare networking for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Configure webhooks for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html): CoreDNS replica 배치
* [Configure add-ons for hybrid nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html): Pod Identity Agent
* [Best practices for stability through network disconnections](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
* [AWS PrivateLink for Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
* [Access AWS services through AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html)
* [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md), [네트워크 구성](02-network-configuration.md), [보안팀 관점의 망분리 검토](11-network-separation-security.md)
