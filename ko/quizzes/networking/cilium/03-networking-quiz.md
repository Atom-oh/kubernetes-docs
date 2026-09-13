# Cilium 네트워킹 검증 실습

기대 결과가 있는 여덟 가지 실습입니다. 기준은 Cilium 1.20.1, CLI 0.20.0, 지원 Kubernetes 1.33–1.36이며 2026년 9월 12일 검토했습니다. “1.30 이상” 모든 버전의 호환성을 주장하지 않습니다.

## 사전 요구 사항

[네트워킹 가이드](../../../networking/cilium/03-networking.md)와 [설치 프로필](../../../networking/cilium/README.md)로 준비한 일회용 클러스터와 스케줄링 가능한 Linux 노드 두 개를 사용합니다. 아키텍처에 맞는 도구·이미지를 준비하고 kubectl 버전 차이를 지원 범위로 맞춥니다. 기존 CNI 전환이나 제공업체 관리 네트워킹 변경 실습이 아닙니다.

수동 정책 실습에는 새 namespace, Pod, Deployment, Service, namespace 범위 CiliumNetworkPolicy 생성 권한이 필요합니다. 기존 cluster-wide 정책·admission 제약을 확인합니다. 별도 namespace가 이를 무효화하지는 않습니다. 변수가 유지되도록 같은 셸에서 명령을 실행합니다.

## 1. 설치 및 기본 테스트

설치 가이드의 검증된 CLI 다운로드와 선택한 Cilium 프로필 하나를 사용합니다. 같은 release에 Helm·CLI 설치를 모두 실행하거나 검증되지 않은 `latest` AMD64 압축 파일을 사용하지 않습니다.

```bash
set -euo pipefail
kubectl config current-context
kubectl version -o yaml
cilium version
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

필요하면 일회용 클러스터에서 유지보수되는 연결성 suite를 실행합니다. Workload·정책을 생성하고 외부 대상으로 요청할 수 있으므로 선택한 테스트·사전 조건을 확인합니다.

```bash
cilium connectivity test --test-namespace cilium-net-smoke \
  --namespace-labels docs-audit-lab=cilium-networking-03
```

CLI 0.20.0은 순번을 붙이므로 기본 단일 suite의 namespace는 `cilium-net-smoke-1`입니다. 실패·생략된 case를 읽습니다. 명령 종료만으로 시험하지 않은 클라우드·기능 조합이 작동한다고 판단하지 않습니다.

<details>
<summary>기대 결과와 확인 문제</summary>

설치 버전이 지원표에 맞고 에이전트가 Ready가 되며 선택한 연결성 case가 통과합니다. Ready DaemonSet만으로 노드 간 라우팅을 증명하지 못하는 이유와 새 API 서버에서 “kubectl 1.31+”만으로 부족한 이유를 설명하세요.

</details>

## 2. 네트워크 정책 테스트

### 독립적인 Namespace와 Workload 생성

```bash
kubectl create namespace cilium-net-lab
kubectl label namespace cilium-net-lab docs-audit-lab=cilium-networking-03
```

Namespace가 이미 존재한다면 중단하고 모든 파일·명령에서 일관되게 새 이름을 선택합니다. 다른 사람의 namespace를 다시 label하거나 재사용하지 않습니다.

다음 digest는 공식 CLI 0.20.0 테스트 기본값입니다. 해당 배포 소스는 curl 이미지의 `/usr/bin/pause`와 TCP 8080, `/` readiness의 JSON mock server를 사용합니다. 운영 애플리케이션 추천이 아닌 테스트 이미지입니다. Backend anti-affinity로 frontend와 다른 노드에 배치합니다.

**`lab-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-net-lab
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-net-lab
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lab-app.yaml
kubectl -n cilium-net-lab wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
kubectl -n cilium-net-lab rollout status deployment/backend --timeout=120s
kubectl -n cilium-net-lab get pods -o wide
kubectl -n cilium-net-lab get endpointslices -l kubernetes.io/service-name=backend
BACKEND_IP=$(kubectl -n cilium-net-lab get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
```

Backend Pending은 anti-affinity 조건을 만족하는 노드 부족일 수 있으며 정책 실패로 해석하지 않습니다. 새 정책 적용 전에 **두 클라이언트 모두** 정상 backend에 도달하는지 확인합니다. DNS 실패를 ingress 테스트에서 분리하기 위해 Service IP를 사용합니다.

```bash
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

### 정책 적용과 확인

**`allow-frontend.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-net-lab
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-net-lab
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


```bash
kubectl apply -f allow-frontend.yaml
kubectl -n cilium-net-lab get ciliumnetworkpolicy allow-frontend-to-backend -o yaml
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

관련 endpoint에 정책이 실현될 때까지 기다리고 정상 요청을 다시 확인합니다. 이전 연결의 허용 결과로 새 정책의 준비 상태를 증명할 수는 없습니다. 위 명령은 각각 새 curl 프로세스를 시작합니다.

```bash
if kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"; then
  echo "Unexpected allowed request: inspect combined policy and realization" >&2
  exit 1
else
  denied_rc=$?
  printf 'Outsider request failed with exit %s; correlate the flow before declaring a policy pass.\n' "$denied_rc"
fi
```

0이 아닌 종료 코드가 자동으로 차단 테스트 통과를 뜻하지는 않습니다. Exec/RBAC, 없는 curl, 라우팅, backend 등 다른 실패일 수 있습니다. Curl timeout은 흔히 28이지만 성공한 기준 요청·계속 작동하는 frontend와 함께 출발지·목적지·포트 및 정책 거부 플로우를 대조합니다. 이 namespace 규칙이 다른 정책의 독립적인 허용을 막는 것은 아닙니다.

<details>
<summary>기대 결과와 확인 문제</summary>

정책 전에는 두 클라이언트가 성공합니다. 정책 실현 후 frontend는 계속 성공하고 outsider는 정책 근거와 함께 거부됩니다. EndpointSlice 누락, DNS 오류, 임의의 비정상 종료 코드로 격리를 증명할 수 없는 이유를 설명하세요. 이 L3/L4 정책은 HTTP 파싱을 추가하지 않습니다.

</details>

## 3. Hubble 가시성 테스트

프로필의 Hubble Relay/UI와 적절한 Hubble CLI를 사용합니다. 별도 터미널에서 port-forward를 유지한 뒤 다른 터미널에서 관찰합니다.

```bash
cilium hubble port-forward
```

```bash
hubble status
hubble observe --namespace cilium-net-lab --last 50
hubble observe --from-pod cilium-net-lab/outsider --verdict DROPPED --last 20
cilium hubble ui
```

관찰하면서 새 요청을 만듭니다. 이벤트 유실·집계·필터가 가시성에 영향을 줍니다. HTTP 플로우에는 지원되는 L7 프록시·가시성 설정이 필요하며 위 L4 규칙은 이를 만들지 않습니다. 설정된 L7 거부는 패킷 DROPPED 대신 HTTP 403일 수 있습니다.

<details>
<summary>기대 결과와 확인 문제</summary>

Relay에 연결되고 의도한 endpoint의 플로우를 확인하며 차단 근거가 해당 요청과 일치합니다. L4 전용 실습에 HTTP 레코드가 없다는 사실이 Hubble 장애 증거가 아닌 이유를 설명하세요.

</details>

## 4. 성능 테스트

맞는 client/server workload를 생성하는 [본문의 `cilium connectivity perf` 예제](../../../networking/cilium/03-networking.md)를 사용합니다. 같은 노드·다른 노드 결과를 분리하고 노드 배치, 버전, route MTU, 정책·암호화를 기록합니다.

기존 테스트는 맞지 않는 `netperf-*` Pod 이름, iperf3 이미지, TCP 전용 Service를 조합했습니다. 별도로 준비한 iperf3에서 UDP 테스트를 하려면 설정 포트의 **TCP 제어 연결과 UDP 데이터**가 모두 필요합니다. `-b 1G` 요청만으로 1 Gbit/s 전달이 증명되지 않습니다.

<details>
<summary>기대 결과와 확인 문제</summary>

선택된 테스트 workload가 Ready이고 결과가 시나리오별로 구분됩니다. TCP request/response, 연결 생성, stream 처리량, UDP 제공률·손실의 차이를 설명하세요. 결과는 기록한 구성에 적용되며 모든 Cilium 모드·클라우드에 일반화되지 않습니다.

</details>

## 5. 선택적 고급 기능 확인

각 기능은 별도로 준비한 문서화된 프로필에서 구성합니다. **확인 사이에 클러스터 CNI를 제거하지 않습니다.** Helm flag 하나로 없는 키·경로·API 연결·BGP peer가 준비되지는 않습니다.

| 기능 | 준비 | 관찰 |
|---|---|---|
| kube-proxy 대체 | `kubeProxyReplacement: true`, 도달 가능한 `k8sServiceHost`/`k8sServicePort`, 지원 datapath와 전환 계획 | 실제 agent 상태와 Service 트래픽. `strict`는 현재 값이 아님 |
| IPsec/WireGuard | 암호화 모드, 키 운영, 포트·MTU와 트래픽 적용 범위 | 에이전트 암호화 상태와 실제 노드 간 경로 |
| BGP Control Plane | `bgpControlPlane.enabled: true`, 버전별 BGP 리소스와 도달 가능한 peer 설정 | Session·광고 경로. 로컬 전달 테이블 자동 프로그래밍으로 가정하지 않음 |

관련 노드의 에이전트를 선택합니다.

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
cilium bgp peers
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
```

기능을 구성한 경우에만 해당 명령의 결과를 해석합니다. 기본 프로필의 비활성·미구성 상태는 정상입니다. 독립 CLI의 `cilium bgp peers`는 클러스터 노드 상태를 조회하며 이전 에이전트 로컬 BGP 명령은 폐기 예정입니다. BGP에는 해당 `cilium.io/v2` 설정 리소스가 필요하며 제거된 `bgp.enabled`, `bgp.announce.loadbalancerIP` 값으로 session이 만들어지지 않습니다.

<details>
<summary>기대 결과와 확인 문제</summary>

관측 상태가 선택한 프로필에 맞고 트래픽·경로 근거가 결과를 뒷받침합니다. “BGP established”가 내부 Pod 라우팅을 증명하지 않는 이유와 암호화 상태만으로 모든 경로의 암호화를 증명할 수 없는 이유를 설명하세요.

</details>

## 6. 호환성 확인

```bash
kubectl version -o yaml
cilium version
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.kernelVersion}{"\n"}{end}'
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl -n kube-system get daemonset cilium -o yaml
```

문서화된 커널 백포트를 포함해 지원표와 버전·기능을 비교합니다. 호스트 설정 파일을 읽기 전에 실제 CNI 값과 volume mount를 확인합니다. `/etc/cni/net.d/05-cilium.conf`가 모든 컨테이너의 경로·파일명은 아니며 chaining·custom 설정도 다릅니다. 파일이 존재한다는 사실만으로 실행 호환성이 확인되지 않습니다.

<details>
<summary>기대 결과와 확인 문제</summary>

버전·커널 조건이 플랫폼과 맞고 의도한 CNI에서 Pod 주소를 할당하며 트래픽 테스트가 통과합니다. CNI 설치, IPAM 할당, 종단 간 전달의 차이를 설명하세요.

</details>

## 7. 문제 해결

```bash
cilium status --verbose
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
kubectl -n kube-system logs deployment/cilium-operator --tail=100
kubectl -n kube-system logs deployment/hubble-relay --tail=100
```

Frontend endpoint를 볼 때는 먼저 frontend 노드의 에이전트를 선택합니다.

```bash
kubectl -n cilium-net-lab get pod frontend -o wide
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get pod-name:cilium-net-lab:frontend
```

Ingress 거부는 backend의 에이전트·endpoint도 확인합니다. 의도한 정책, 실현 상태, 경로·backend 상태와 관측 플로우를 비교합니다. 제거된 `policy trace`나 따옴표 없는 `<pod-name>` 셸 자리표시자로 사람이 읽는 표를 파싱하지 않습니다.

필요하면 `cilium sysdump`로 진단 정보를 수집하고 공유 전에 로그·리소스 내용을 확인합니다. `cilium clustermesh status`는 Cluster Mesh를 구성한 경우에만 해당하며 Relay는 연결 설정 후 `hubble status`로 확인합니다.

<details>
<summary>기대 결과와 확인 문제</summary>

kubectl이 우연히 고른 DaemonSet Pod가 아니라 올바른 노드·endpoint의 근거를 확인합니다. Backend 미준비, 경로 실패, 정책 거부, 관측 누락을 어떤 근거로 구분하는지 설명하세요.

</details>

## 8. 정리

먼저 이번 실행이 만든 namespace와 보존할 결과를 확인합니다.

```bash
kubectl get namespaces -l docs-audit-lab=cilium-networking-03
LAB_OWNER=$(kubectl get namespace cilium-net-lab -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-networking-03
kubectl delete namespace cilium-net-lab
```

CLI suite를 실행했다면 생성된 `cilium-net-smoke-1` / `cilium-net-perf-1`도 소유를 별도로 확인한 후 정리합니다. 무관한 namespace를 일괄 삭제하거나 애플리케이션 정리 목적으로 Cilium을 제거하지 않습니다. 로컬 port-forward는 Ctrl-C로 종료합니다.

<details>
<summary>기대 결과와 확인 문제</summary>

이번 실행의 테스트 리소스만 삭제되고 설치된 CNI와 다른 workload는 계속 작동합니다. 기능 비교를 위해 CNI를 반복 제거하는 것이 적절하지 않았던 이유를 설명하세요.

</details>

## 검증 한계와 참고 자료

공개한 YAML·Helm values, 셸 문법과 CLI/API 계약은 workload를 배포하지 않고 확인했습니다. 호스트 재시작 이후 실제 클러스터, 이미지 실행, Helm 렌더링, 처리량 결과를 주장하지 않습니다. Admission, 이미지 아키텍처·pull 정책, 용량, 실제 datapath와 기대 결과는 준비한 환경에서 검증해야 합니다.

- [CLI 0.20.0 image defaults](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/defaults/defaults.go), [test deployments](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/connectivity/check/deployment.go), [connectivity/perf flags](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go)
- [Cilium 1.20.1 policy API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml), [L7 behavior](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst), [BGP configuration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst), [BGP CLI](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/cli/bgp.go), [agent commands](https://github.com/cilium/cilium/tree/v1.20.1/Documentation/cmdref)
- [Kubernetes version skew](https://kubernetes.io/releases/version-skew-policy/), [iperf3 invocation](https://software.es.net/iperf/invoking.html), [networking guide](../../../networking/cilium/03-networking.md)
