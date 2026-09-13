# Part 1: Calico 소개 및 기본 개념

> **검토 기준**: Calico Open Source 3.32.2, kind 0.33.0, Kubernetes 1.36.4
> **마지막 업데이트**: 2026년 9월 12일. Calico 3.32의 공식 Kubernetes 시험 대상은 1.34–1.36입니다.

## 실습 환경

iptables·VXLAN·Calico IPAM을 명시적으로 선택한 폐기 가능한 로컬 실습입니다. 기존 CNI를 교체하거나 EKS를 구성하는 절차가 아닙니다. 감사에서는 공개 파일과 설정을 확인했지만 클러스터 생성이나 실제 트래픽 시험은 하지 않았습니다.

| 도구·환경 | 요구사항 |
|---|---|
| kind | 0.33.0, 고정되지 않은 기본값 대신 아래 1.36.4 이미지 사용 |
| Docker | kind가 지원하는 정상 런타임과 노드 3개를 수용할 용량 |
| 노드 OS | [Calico 요구사항](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)을 충족하는 Linux 커널·모듈, macOS에서는 컨테이너 VM의 커널 |
| kubectl | API 서버 1.36과 마이너 차이 1 이내, 동일한 1.36 클라이언트 사용이 간편 |
| calicoctl | 선택적인 동일 버전 3.32.2 클라이언트, CLI 호스트의 실제 OS·아키텍처 선택 |
| curl / Python 3 | 아래 선택적 클라이언트 다운로드·SHA-256 검증 |
| Helm | [개요](README.md)의 대체 설치 방법에 사용, 이 실습에는 불필요 |

[Kubernetes 버전 차이 정책](https://kubernetes.io/releases/version-skew-policy/)은 임의의 `kubectl 1.28+`가 이후 모든 서버와 호환됨을 뜻하지 않습니다. 실습 생성 전에 Pod·Service CIDR과 컨테이너 네트워크·호스트 LAN·VPN의 충돌을 확인하세요.

### 선택 사항: 일치하는 calicoctl

플랫폼 하나를 선택하고 해당 릴리스 파일의 공개 digest를 검증한 뒤 실습 디렉터리에 둡니다. 전역 설치나 홈 디렉터리 설정 변경은 필요하지 않습니다.

```bash
set -euo pipefail
CALICO_VERSION=v3.32.2
case "$(uname -s)" in
  Linux) CALICO_OS=linux ;;
  Darwin) CALICO_OS=darwin ;;
  *) echo "Select a supported calicoctl OS" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) CALICO_ARCH=amd64 ;;
  aarch64|arm64) CALICO_ARCH=arm64 ;;
  *) echo "Select a supported calicoctl architecture" >&2; exit 1 ;;
esac
CALICO_ASSET="calicoctl-$CALICO_OS-$CALICO_ARCH"
curl --fail --location --retry 3 \
  "https://api.github.com/repos/projectcalico/calico/releases/tags/$CALICO_VERSION" \
  --output calico-release.json
curl --fail --location --retry 3 \
  "https://github.com/projectcalico/calico/releases/download/$CALICO_VERSION/$CALICO_ASSET" \
  --output calicoctl
python3 - "$CALICO_ASSET" <<'PY'
import hashlib
import json
import pathlib
import sys

release = json.loads(pathlib.Path("calico-release.json").read_text())
if release["tag_name"] != "v3.32.2":
    raise SystemExit("Unexpected release")
asset = next(a for a in release["assets"] if a["name"] == sys.argv[1])
expected = asset.get("digest") or ""
actual = "sha256:" + hashlib.sha256(pathlib.Path("calicoctl").read_bytes()).hexdigest()
if not expected.startswith("sha256:") or actual != expected:
    raise SystemExit("Digest mismatch or missing published digest")
print("Verified", asset["name"], actual)
PY
chmod +x calicoctl
./calicoctl --help
```

실습 데이터스토어 설정 후 `./calicoctl version`으로 클라이언트·클러스터 정보를 확인합니다. 문서화된 `version` 명령에는 `--client` 옵션이 없습니다. 집계 API 서버가 준비되면 `kubectl`로도 Calico 리소스를 관리할 수 있으며 모든 작업에 calicoctl이 필수인 것은 아닙니다.

### 별도의 kind 클러스터 생성

사용하지 않는 클러스터 이름과 새로운 로컬 kubeconfig를 사용합니다. [kind 0.33.0 릴리스](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0)에 Calico 시험 대상 마이너 범위의 1.36.4 이미지가 공개되어 있습니다. 감사에서는 레지스트리 digest·amd64/arm64 매니페스트를 확인했고 노드 이미지 레이어는 내려받지 않았습니다.

```bash
set -euo pipefail
CALICO_LAB_KUBECONFIG="$PWD/calico-lab.kubeconfig"
test ! -e "$CALICO_LAB_KUBECONFIG"
cat > kind-calico.yaml <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  disableDefaultCNI: true
  kubeProxyMode: iptables
  podSubnet: 10.244.0.0/16
nodes:
  - role: control-plane
  - role: worker
  - role: worker
YAML
kind create cluster --name calico-lab --config kind-calico.yaml \
  --kubeconfig "$CALICO_LAB_KUBECONFIG" \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed
export KUBECONFIG="$CALICO_LAB_KUBECONFIG"
export DATASTORE_TYPE=kubernetes
kubectl config current-context
kubectl cluster-info
```

CNI 설치 전에는 노드와 일반 Pod가 준비되지 않을 수 있습니다. 이를 없애려고 다른 CNI를 설치하지 마세요. Pod CIDR이 충돌하면 클러스터 생성 전에 kind와 Installation 양쪽 값을 바꿉니다.

```bash
CALICO_VERSION=v3.32.2
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/v1_crd_projectcalico_org.yaml"
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml"
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=300s
kubectl apply -f - <<'YAML'
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: Kind
  cni:
    type: Calico
  calicoNetwork:
    linuxDataplane: Iptables
    bgp: Disabled
    ipPools:
      - cidr: 10.244.0.0/16
        blockSize: 26
        encapsulation: VXLAN
        natOutgoing: Enabled
        nodeSelector: all()
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
```

operator가 관리하는 워크로드가 생성되기를 기다린 뒤 rollout과 상태를 확인합니다. 빈 라벨 선택 결과나 컨트롤러 하나의 Available만으로 전체 노드 네트워킹이 동작한다고 판단하면 안 됩니다.

```bash
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl -n calico-system rollout status deployment/calico-kube-controllers --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl wait --for=condition=Ready nodes --all --timeout=300s
kubectl get ippools.projectcalico.org -o wide
kubectl get installations.operator.tigera.io default -o yaml
# Optional, if the matching local client was downloaded:
./calicoctl version
./calicoctl get nodes
```

여기서는 BGP를 끄므로 BIRD 세션과 `calicoctl node status`는 준비 상태 기준이 아닙니다. 해당 명령에는 노트북 kubeconfig만이 아니라 적절한 노드 환경도 필요합니다. CSI·Typha 복제 수는 고정이 아니므로 실제 컴포넌트 수를 확인하세요. 임시 워크로드로 Pod·Service·DNS 연결성과 정책의 허용·거부 흐름을 모두 점검합니다.

## Calico가 제공하는 기능

Calico는 Kubernetes 네트워킹·IPAM·정책 강제를 결합합니다. policy-only 통합에서는 다른 CNI가 네트워킹과 IPAM을 유지합니다. 기능은 운영체제·데이터플레인·에디션에 따라 다르며 플랫폼 목록이 동일 동작을 보장하지는 않습니다.

![Calico의 네트워킹·정책·관측성·IPAM 기능 개념도.](../../.gitbook/assets/ko-networking-calico-01-introduction-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-networking-calico-01-introduction-0.html)

기능 범위의 개념도이며 성능 보장이 아닙니다. EKS policy-only에서는 VPC CNI가 네트워킹과 IPAM을 담당합니다.

## 프로젝트 이력과 거버넌스

Project Calico는 2014년 Metaswitch에서 시작했으며 2016년에 설립된 Tigera가 주요 유지관리자입니다. 아래 릴리스 기록은 기존의 3.0·3.29 연도를 바로잡고 초기 eBPF preview와 이후 기능 제공을 구분합니다.

| 날짜 | 공식 릴리스 기록 |
|---|---|
| 2017년 12월 21일 | [Calico 3.0.0](https://github.com/projectcalico/calico/releases/tag/v3.0.0), 설치 권장이 아닌 과거 릴리스 |
| 2020년 2월 25일 | [eBPF 소개](https://www.tigera.io/blog/introducing-the-calico-ebpf-dataplane/), GA가 아닌 **3.13용 tech preview** |
| 2024년 10월 29일 | [Calico 3.29.0](https://github.com/projectcalico/calico/releases/tag/v3.29.0) |
| 2026년 8월 30일 | [Calico 3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2), 이번 검토 기준 |

기존의 “eBPF 완전 동등성”과 “Windows eBPF” 주장은 잘못된 내용입니다. 현재 [Windows 제약](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)도 Linux eBPF·IPIP·IPv6/dual stack·WireGuard를 제외합니다.

Calico는 Apache-2.0 라이선스이며 Tigera와 커뮤니티가 유지관리합니다. CNCF Landscape 등재는 CNCF 소유·인큐베이션·졸업을 뜻하지 않습니다. Enterprise는 상용 자체 관리 제품, Cloud는 SaaS이며 Open Source가 소규모나 비운영 클러스터에만 한정되지는 않습니다.

![Calico 생태계와 상용 제품의 관계.](../../.gitbook/assets/ko-networking-calico-01-introduction-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-networking-calico-01-introduction-1.html)

CNCF 상자는 Landscape·생태계 참여만 뜻합니다. Tigera는 상용 제품뿐 아니라 오픈소스도 유지관리하며 그림의 그룹 구성이 CNCF의 관리 권한을 뜻하지는 않습니다.

## 핵심 기능

### 1. 네트워킹과 데이터플레인

캡슐화와 구현은 별개의 선택입니다. Calico는 IPIP·VXLAN·라우팅된 언더레이를 사용할 수 있습니다. CrossSubnet은 IPIP·VXLAN의 조건부 설정이며 WAN 연결 서비스가 아닙니다. Linux 데이터플레인에는 iptables·nftables·eBPF가 있습니다. eBPF는 **커널 안에서** 실행되며 기존 패킷 처리 경로 일부를 우회할 수 있지만 커널 자체를 우회하지는 않습니다. 비캡슐화는 언더레이에 필요한 Pod 경로가 있을 때 터널 헤더를 없애며 모든 부하의 최저 지연을 보장하지 않습니다.

### 2. Kubernetes와 Calico 정책

Kubernetes NetworkPolicy는 네임스페이스 범위이며 허용을 합산합니다. Calico는 명시적 action·정렬된 정책·tier를 추가하며 Open Source도 tier를 제공합니다. GlobalNetworkPolicy는 클러스터 범위 리소스지만 한 네임스페이스만 선택할 수 있습니다. HostEndpoint는 보호할 호스트 엔드포인트이며 NetworkPolicy 아래의 세 번째 정책 종류나 고정 계층이 아닙니다.

다음은 전용 네임스페이스의 **서로 독립적인 예제**입니다. 기존 tier·우선 정책을 고려해야 하며 완전한 보안 기준선은 아닙니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: calico-demo
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress: []
```

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-trusted-ingress
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'backend'
  order: 100
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
        selector: trusted == 'true'
      destination:
        ports: [8080]
    - action: Deny
```

Calico 예제는 데모 네임스페이스의 매칭 엔드포인트에서 선택된 backend의 TCP 8080을 허용하고 다른 ingress를 거부합니다. `trusted`는 암호학적 신원이 아니므로 라벨 변경 권한을 통제하세요. 두 예제 모두 egress·DNS를 설정하지 않습니다. CIDR·포트 규칙을 지원하지만 큰 사설 CIDR은 신원 경계가 아닙니다. DNS/FQDN·애플리케이션 계층 정책은 해당 Enterprise/Cloud 기능이 필요합니다. [에디션 표](https://docs.tigera.io/calico/latest/about/calico-product-editions)를 확인하세요.

### 3. IP 주소 관리

Calico가 IPAM을 맡으면 pool·block으로 주소를 할당합니다. IPv4 /26 block은 주소 64개이며 모든 플랫폼에서 Pod 주소 64개를 보장하지는 않습니다. Windows 예약 주소와 IPv6의 다른 기본값을 고려해야 합니다. VPC CNI policy-only에서는 AWS가 IPAM을 맡습니다.

아래는 [IPPool API](https://docs.tigera.io/calico/latest/reference/resources/ippool) 예입니다. **operator 관리 pool과 중첩되게 추가 생성하지 마세요.** kind 실습에는 이미 pool이 있으며 캡슐화·IPAM 변경은 별도로 계획할 실습입니다.

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: example-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
```

중첩되지 않는 여러 pool과 node selector로 할당을 구분할 수 있습니다. `natOutgoing`은 일반적으로 Calico pool 밖으로 나가는 트래픽에 적용되며 방화벽·암호화 설정이 아닙니다. 직접 라우팅이나 CrossSubnet만으로 언더레이 설계 없이 사이트를 연결할 수는 없습니다.

### 4. BGP 라우팅

BGP는 경로를 배포하며 애플리케이션 패킷이 BIRD 프로세스를 통과하거나 BGP로 암호화되는 것은 아닙니다. 직접 라우팅을 지원하거나 IPIP와 함께 사용할 수 있으며 full mesh·라우트 리플렉터·외부 peer는 토폴로지별 선택입니다.

다음은 BGP를 끈 kind 예제가 아닌 **별도 라우팅 실습용**입니다. 문서용 주소·ASN·노드 라벨을 설계한 토폴로지와 대응 라우터 설정으로 바꾸세요. 대체 경로 배포가 동작하기 전에 노드 mesh를 끄면 안 됩니다.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: example-rack-tor
spec:
  peerIP: 192.0.2.1
  asNumber: 64513
  nodeSelector: rack == 'rack-1'
```

BGPPeer는 세션 인증에 `password.secretKeyRef`를 지원합니다. Secret은 Calico 노드 컴포넌트의 네임스페이스에 두고 라우터의 자격 증명도 맞춰야 합니다. 워크로드 트래픽 암호화는 아닙니다. Service CIDR 광고·mesh 제거에는 추가 시험이 필요합니다. [BGP 심층 분석](04-bgp-deep-dive.md)을 참고하세요.

### 5. 플랫폼과 확장 범위

| 환경 | 범위 |
|---|---|
| EKS | VPC CNI + Calico 정책은 통합 중 하나, 전체 Calico CNI는 별도의 새 클러스터 설계 |
| AKS | 제공자의 지원 CNI·정책 조합과 현재 설치 절차 확인 |
| GKE | Dataplane V2는 **Cilium**, Calico는 해당 legacy 구성에 적용하며 V2 위에 설치하지 않음 |
| 자체 관리 Kubernetes | 배포판·커널·CNI 소유권·경로·권한 확인 |
| Windows | 명시된 IPv4 구성, Linux eBPF·IPIP·IPv6/dual stack·WireGuard 동등성 없음 |
| 호스트 / VM | 별도 설치·기능 조건, KubeVirt·Enterprise 상태는 기본 호스트 보호와 다름 |

[GKE 문서](https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2)는 V2의 Cilium과 legacy Calico 경로를 명시적으로 구분합니다.

Typha는 별도 Pod 집합에서 업데이트를 캐시·분배해 Felix의 직접 데이터스토어 watch를 줄입니다. 복제 3개는 예일 뿐 보편적인 최소값이 아닙니다. 용량은 정책·엔드포인트·Service 변경률·하드웨어·데이터스토어·데이터플레인에 좌우됩니다. 이 소개 문서에는 “5,000노드 / 100,000 Pod / 수백만 규칙”이라는 고정 한도의 재현 가능한 근거가 없습니다.

## Calico·kube-proxy·성능

kube-proxy는 Service 전달을 구현하며 CNI 네트워킹이나 NetworkPolicy 엔진이 아닙니다. 이 실습처럼 Calico 표준 데이터플레인은 kube-proxy와 함께 동작할 수 있고 eBPF는 구성 시 Service 처리를 대체할 수 있습니다.

| 관심사 | 비교 대상 |
|---|---|
| Pod 네트워킹·IPAM | 같은 토폴로지의 CNI·IPAM 구현 |
| Service 전달 | 선택한 kube-proxy 백엔드 또는 eBPF 대체 구현 |
| 정책 | 동등한 규칙과 강제 범위 |
| 규모 | Service·엔드포인트·selector·변경률·연결 재사용 |
| CPU·메모리·지연 | 하드웨어·커널·버전·부하·준비 구간·반복·오류 |

kube-proxy는 iptables 전용이 아니며 현재 Kubernetes에는 nftables와 버전별 legacy 백엔드도 있습니다. IP set 조회가 Calico 전체 패킷 경로를 O(1)로 만들지는 않습니다. iptables Service NAT의 첫 선택과 이후 패킷의 conntrack 빠른 경로도 다릅니다. 기존의 출처 없는 1,000노드/50,000 Pod 규칙 수·지연·메모리 예제는 재현 가능한 벤치마크가 아니므로 용량 산정에 사용할 수 없습니다.

전통적인 VM 네트워크도 자동화·분산 구성이 가능합니다. Calico의 선언적 정책이 무제한 IP 용량이나 초 단위 수렴 보장을 뜻하지는 않습니다.

## 배포 시나리오

- **온프레미스**: Pod 경로·BGP peer/필터·반환 경로·호스트 보호를 조정합니다. 캡슐화만 끈다고 언더레이 경로가 생기지는 않습니다.
- **EKS**: AWS 네트워킹을 유지하려면 `cni.type: AmazonVPC`를 선택하고 정책 엔진 소유권·Pod IP annotation 등 [검토된 개요](README.md)를 따릅니다. EKS Installation을 이 Kind 실습에 적용하거나 정책 엔진 둘을 실행하지 마세요.
- **하이브리드·멀티클러스터**: 연결성·디스커버리·정책 관리는 별개입니다. CrossSubnet IPPool은 VPN·공유 신원·클러스터 간 디스커버리를 만들지 않습니다. 해당 cluster mesh·멀티클러스터 제품 기능과 언더레이를 별도로 평가해야 하며 “Calico Federation”이 보편적인 기본 연결은 아닙니다.
- **규제 대상 워크로드**: Enterprise/Cloud가 보고서·로그·보안 기능을 추가할 수 있지만 설치만으로 규정 준수가 성립하지 않습니다. API 감사 로그는 API 변경, 플로우 로그는 네트워크 관측을 기록하며 모든 정책 결정이 자동으로 기록되지는 않습니다. WireGuard는 지원되는 Open Source Linux 구성에도 있습니다.

## 커뮤니티와 소스 개발

현재 Slack·모임 링크는 [커뮤니티 페이지](https://www.tigera.io/project-calico/community/), 재현 가능한 보고는 [이슈 트래커](https://github.com/projectcalico/calico/issues), 기여 절차는 [기여 가이드](https://github.com/projectcalico/calico/blob/v3.32.2/CONTRIBUTING.md)를 사용합니다. 날짜 없는 격주 일정이나 오래된 포럼 주소가 현재도 유효하다고 가정하지 마세요.

소스 학습용 [개발자 가이드](https://github.com/projectcalico/calico/blob/v3.32.2/DEVELOPER_GUIDE.md)는 Linux·Docker·git·make 환경과 컴포넌트별 시험을 설명합니다. 루트의 `make dev-environment` target은 없습니다. 아래 선택적 소스 작업은 네트워킹 실습과 별개이며 감사에서 실행하지 않았습니다.

```bash
git clone --depth 1 --branch v3.32.2 https://github.com/projectcalico/calico.git calico-source-study
cd calico-source-study
# Read prerequisites and the selected component's Makefile before running tests.
cat DEVELOPER_GUIDE.md
make -C calicoctl test
```

Open Source는 실습뿐 아니라 운영 환경에도 커뮤니티 지원 네트워킹·정책을 제공합니다. Enterprise는 상용 기능·지원을 추가하고 Cloud는 SaaS 관리를 제공합니다. 단순한 “소규모 대규모” 구분 대신 [기능 표](https://docs.tigera.io/calico/latest/about/calico-product-editions)로 선택하세요.

## 폐기 가능한 실습 정리

결과 보관 후 이번 실습에서 만든 `calico-lab`만 `kind delete cluster --name calico-lab`으로 삭제합니다. 관련 없는 클러스터와 kubeconfig는 유지하세요. EKS 삭제 절차가 아닙니다.

[다음: Calico 아키텍처](02-architecture.md) · [Calico 개요](README.md) · [소개 퀴즈](../../quizzes/networking/calico/01-introduction-quiz.md)
