# Linkerd 설치 및 설정

> **검토일**: 2026년 9월 11일 · 공개 CLI: edge-26.9.1 · 대응 chart: 2026.9.1

통제된 Kubernetes 설치, Helm/CLI 소유권, HA, 선택적 확장, EKS 고려사항, 업그레이드와 제거를 다룹니다. Upstream은 edge 산출물을 배포하며 stable 배포판의 설치·지원은 vendor 안내를 따라야 합니다. 2.20 같은 milestone이 upstream stable-2.20.0 다운로드를 뜻하지는 않습니다.

PowerShell 표시 외의 명령은 Bash입니다. 의도한 kubeconfig/context와 설치 소유 도구를 사용하세요. CLI와 Helm 절차는 **대안**입니다. Helm 소유 release 위에 CLI 생성 리소스를 적용하지 않습니다. 오프라인 검증은 운영 sizing, storage, network 적용이나 애플리케이션 호환성의 증거가 아닙니다.

## 사전 요구사항

### Kubernetes와 Gateway API

| 구분·버전 | Kubernetes 근거 | Gateway API 근거 |
|---|---|---|
| Linkerd 2.20 milestone/배포판 | 공개 matrix 1.31–1.35. Vendor 지원도 확인 | 공개 matrix 1.2.1–1.5.1 |
| 이 문서의 edge-26.9.1 | 릴리스 CLI 최소 1.31.0. Edge-26.8.2에서 테스트 상한을 1.36으로 올림 | 1.5.1 지원. 이 문서는 해당 standard bundle 사용 |
| 과거 2.16 | 공개 matrix 1.22–1.29 | 현재 설치 권장이 아님 |
| 과거 2.15 / 2.14 | 공개 범위 1.22–1.29 / 1.21–1.28 | 해당 릴리스 확인. 이후 모든 Kubernetes를 지원한다고 해석하면 안 됨 |

CLI 최소 버전 검사는 지원 상한 검사가 아닙니다. check --pre 통과가 새 Kubernetes·Gateway API 호환성을 입증하지 않습니다. EKS에서는 제공 버전과 지원 기간도 확인하세요. 이번 Helm 검증은 Kubernetes 1.35 capability를 사용했습니다.

### 용량과 플랫폼

전체 컨트롤 플레인을 보편적인 CPU 100m·메모리 200Mi로 산정하지 마세요. Controller, policy container, proxy, init container와 확장의 render된 request·limit을 확인하고 실제 트래픽·연결 부하를 측정합니다. HA의 필수 node anti-affinity에는 대상 노드가 최소 3개 있어야 하며 rollout 용량도 필요합니다. Zone 분산은 선호이며 서로 다른 3개 zone을 보장하지 않습니다.

이 절차는 Linux Kubernetes node 대상입니다. Windows CLI 다운로드가 Windows workload 구성을 지원한다는 증거는 아닙니다. 선택한 릴리스의 workload·platform 지원은 별도 확인하세요. Cilium kube-proxy replacement에서는 socketLB.hostNamespaceOnly를 검토하고, Linkerd CNI를 chaining하면 cni.exclusive가 다른 plugin을 허용해야 합니다.

### 네트워크 경로와 사전 검사

모든 곳에 열 포트 목록이 아니라 출발지·목적지 경로를 확인하세요:

| 경로 | 고정한 render의 기본 예시 |
|---|---|
| API server → admission service | Service 443 → injector/SP-validator 8443, policy-validator 9443 |
| Proxy → control plane | Identity 8080, destination 8086, policy 8090 |
| Mesh 애플리케이션 통신 | Proxy inbound 4143과 실제 application/service 경로 |
| Viz 설치 시 | Tap API server 8089, tap gRPC 8088, metrics API 8085, Prometheus 9090 |
| 진단 | Proxy metrics 4191, web UI 8084, 별도 web admin/readiness 9994 |

이는 구성 요소 포트이며 무제한 security-group 규칙이 아닙니다. DNS, Kubernetes API와 선택한 CNI·NetworkPolicy 동작도 고려하고 실제 Service targetPort와 webhook 설정을 확인하세요.

```bash
LINKERD_CHART_VERSION=2026.9.1
CNI_ENABLED=false  # Set true only after installing/verifying Linkerd CNI.
kubectl config current-context
kubectl version
kubectl get nodes -L kubernetes.io/os,kubernetes.io/arch,topology.kubernetes.io/zone
kubectl get crd httproutes.gateway.networking.k8s.io \
  -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
# For a new lab without a conflicting installed bundle, after ownership review:
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
linkerd check --pre --linkerd-cni-enabled="$CNI_ENABLED"
```

Gateway API bundle은 필요할 때 기존 CRD 소유권과 모든 사용 controller를 검토한 뒤 적용하세요. Linkerd CNI를 선택하면 control plane 이전에 설치·검증하고 아래의 CNI 대응 검사를 사용합니다. 실제 출력과 종료 코드를 확인하세요. 과거의 긴 “모두 정상” 예시는 사용자 클러스터의 검사 결과가 아닙니다.

## Linkerd CLI 설치

### Linux/macOS 고정 binary

다음은 정확한 릴리스 asset을 선택하고 공식 metadata의 SHA256과 비교합니다. PATH는 현재 shell에서만 변경합니다:

```bash
set -euo pipefail
LINKERD_VERSION=edge-26.9.1
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) suffix=linux-amd64; expected=094e1de06215fbe76fc011cf62c96214f8dae0cd5a58135fb40307be88b6b176 ;;
  Linux/aarch64|Linux/arm64) suffix=linux-arm64; expected=f92eddc52dc1f3089b65fd16014cdb1bc6b07c3fd177091c365cf3d8c0ea1a8b ;;
  Darwin/x86_64) suffix=darwin; expected=acff9471f26552dd0ebb9560925a98d5ca1213a13dfc81464a2b815c9201664d ;;
  Darwin/arm64) suffix=darwin-arm64; expected=5050da9d974e0c2f548a2e9f145540ec035582cfd67f47c58c37411ae3008913 ;;
  *) echo "No verified asset for this OS/architecture in this example" >&2; exit 1 ;;
esac
CLI_DIR="$PWD/linkerd-cli/$LINKERD_VERSION"
mkdir -p "$CLI_DIR"
curl --proto '=https' --tlsv1.2 -fsSL \
  "https://github.com/linkerd/linkerd2/releases/download/$LINKERD_VERSION/linkerd2-cli-$LINKERD_VERSION-$suffix" \
  -o "$CLI_DIR/linkerd.download"
if command -v sha256sum >/dev/null; then
  actual=$(sha256sum "$CLI_DIR/linkerd.download" | awk '{print $1}')
else
  actual=$(shasum -a 256 "$CLI_DIR/linkerd.download" | awk '{print $1}')
fi
test "$actual" = "$expected"
chmod 755 "$CLI_DIR/linkerd.download"
mv "$CLI_DIR/linkerd.download" "$CLI_DIR/linkerd"
export PATH="$CLI_DIR:$PATH"
linkerd version --client
```

목록은 Linux amd64/arm64와 macOS Intel/Apple Silicon입니다. Installer의 일반 ARM 분기가 이 릴리스에 32비트 ARM binary가 있다는 뜻은 아닙니다. 이번 감사에서는 Linux arm64 CLI를 실행했고 다른 platform binary는 공식 release metadata에서 확인했습니다.

### 공식 installer 대안

기존 run.linkerd.io/install은 deprecated이며 stable이 아니라 edge를 설치합니다. 현재 installer는 LINKERD2_VERSION 환경 변수로 버전을 선택합니다. 이전 sh --version stable-2.16.0은 지원되는 upstream stable 산출물을 선택하지 않습니다.

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://run.linkerd.io/install-edge -o install-linkerd.sh
# Inspect the downloaded script before execution.
LINKERD2_VERSION=edge-26.9.1 INSTALLROOT="$PWD/linkerd-installer" sh ./install-linkerd.sh
export PATH="$PWD/linkerd-installer/bin:$PATH"
linkerd version --client
```

릴리스 호환 matrix로 Gateway API bundle을 선택하세요. Installer 완료 메시지는 자체 예시 버전을 제시하며 이 가이드는 선택한 릴리스에 맞춰 1.5.1을 고정합니다. Package manager·vendor 배포판은 다른 버전을 선택할 수 있습니다. Homebrew/Chocolatey가 여기의 고정 버전이라고 가정하지 말고 산출물 출처와 버전을 확인하세요. 이 절차에 shell profile 편집은 필요하지 않습니다.

### Windows binary

릴리스 asset 이름은 windows-amd64.exe가 아닌 windows.exe입니다:

```powershell
$ErrorActionPreference = "Stop"
$LinkerdVersion = "edge-26.9.1"
$ExpectedSha256 = "d50119c635a0052bfcc7e0b96dcc985676b237ebc87464380677c413344d99a9"
$Download = Join-Path (Get-Location) "linkerd.download.exe"
$Url = "https://github.com/linkerd/linkerd2/releases/download/$LinkerdVersion/linkerd2-cli-$LinkerdVersion-windows.exe"
Invoke-WebRequest -Uri $Url -OutFile $Download
if ((Get-FileHash -Algorithm SHA256 $Download).Hash.ToLowerInvariant() -ne $ExpectedSha256) {
    throw "Linkerd release checksum mismatch"
}
Move-Item $Download (Join-Path (Get-Location) "linkerd.exe") -Force
.\linkerd.exe version --client
```

이후 Bash 예제는 구성된 WSL 환경 같은 적절한 shell이나 PowerShell 명령 변환이 필요합니다. 이번 감사에서 PowerShell이나 Windows workload를 실행하지 않았습니다.

## 컨트롤 플레인 설치

### CLI 설치

새 CLI 소유 설치에서는 control plane 생성·설치 전에 Linkerd CRD를 적용합니다:

```bash
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-control-plane.yaml
# Review the generated resources and trust credentials before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

명령은 매니페스트를 생성하고 kubectl이 설치를 수행합니다. CLI가 기본 생성하는 trust anchor와 issuer credential의 유효기간은 유한하므로 회전 계획이 필요합니다. 공유 trust multicluster는 각 클러스터에서 독립 생성한 root가 아니라 의도적으로 제공한 credential이 필요합니다.

### Helm 설치

Helm은 반복 가능한 release/values 관리 방식입니다. CLI tag와 별도로 chart version을 고정하세요:

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
helm show chart linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
```

공개 대응 chart는 linkerd-crds, linkerd-control-plane, linkerd-viz, linkerd-multicluster, linkerd2-cni의 2026.9.1입니다. Core chart appVersion은 edge-26.9.1입니다. 과거 stable 저장소의 버전 없는 chart가 이 CLI와 일치한다고 가정하면 안 됩니다.

#### Trust anchor와 issuer

Helm에는 trust anchor 인증서, issuer 인증서·개인 키 또는 의도적으로 구성한 지원 외부 issuer-secret 통합이 필요합니다. Root CA 개인 키를 Kubernetes에 올릴 필요는 없습니다.

공식 certificate-create 인터페이스를 제공하는 [Smallstep CLI](https://smallstep.com/docs/step-cli/installation/)를 설치해 사용하세요. 다음 ECDSA P-256 예시는 기존 실습 유효기간을 보존하면서 --not-after 뒤의 잘못된 줄 연결을 수정했습니다:

```bash
umask 077
mkdir linkerd-pki
(
  cd linkerd-pki
  # Demonstration lifetimes, not a universal certificate policy.
  step certificate create root.linkerd.cluster.local ca.crt ca.key \
    --profile root-ca --kty EC --curve P-256 \
    --not-after 87600h --no-password --insecure
  step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
    --profile intermediate-ca --kty EC --curve P-256 \
    --not-after 8760h --no-password --insecure \
    --ca ca.crt --ca-key ca.key
  openssl verify -CAfile ca.crt issuer.crt
  openssl x509 -in issuer.crt -noout -text
)
```

설치 전 chain, 알고리즘과 유효기간을 검사하세요. Root 개인 키는 Kubernetes 밖에 두고 아래에는 공개 trust anchor와 issuer 서명 credential만 제공합니다. --no-password/--insecure는 암호화하지 않은 로컬 키를 만들므로 제한된 directory/umask를 사용합니다. 운영 PKI에는 승인된 키 저장·회전 절차가 필요합니다. 감사에서는 공식 문서로 flag를 확인했으며 Smallstep 인증서 생성은 실행하지 않았습니다.

#### 사용자 지정 values

다음을 linkerd-values.yaml로 저장하세요. 수량은 예시이며 workload 보장이 아닙니다:

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
  logLevel: warn,linkerd=info
  logFormat: plain
identity:
  issuer:
    clockSkewAllowance: 20s
    issuanceLifetime: 24h0m0s
controllerResources: &id001
  cpu:
    request: 100m
    limit: 1000m
  memory:
    request: 50Mi
    limit: 250Mi
destinationResources: *id001
identityResources: *id001
proxyInjectorResources: *id001
```

실제 키는 proxy.logLevel과 proxy.logFormat입니다. destinationResources, identityResources, proxyInjectorResources는 base values에 모두 나열되지 않아도 지원됩니다. 포함된 HA 파일과 template에서 사용합니다. 이전 namespace.labels와 최상위 proxyLogLevel/proxyLogFormat은 소비되지 않았습니다. Chart가 기본적으로 header/request 로그 억제 규칙을 proxy log selector 뒤에 추가하므로 최종 환경 값을 확인하세요.

```bash
helm install linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --create-namespace --wait

helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  > linkerd-rendered.yaml
# Review the render, then install through Helm (do not apply the render as another owner).
helm install linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  --wait --timeout 10m
linkerd check
```

생성한 manifest와 Helm value backup에는 issuer 개인 키가 포함될 수 있습니다. 접근을 제한하고 진단 report에 붙여 넣지 마세요. 업그레이드에도 동일한 release·credential 소유 도구를 유지합니다.

## 고가용성(HA) 설치

고정한 chart에 포함된 values-ha.yaml을 사용합니다:

```bash
helm pull linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
tar -xOf "linkerd-control-plane-$LINKERD_CHART_VERSION.tgz" \
  linkerd-control-plane/values-ha.yaml > linkerd-ha.yaml
# For the Helm render/install above, use:
# -f linkerd-ha.yaml -f linkerd-values.yaml
# For a new CLI-owned installation, render with:
linkerd install --ha --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-ha-rendered.yaml
```

Helm render와 install 모두 사용자 지정 values **앞에** HA 파일을 사용하세요. 나중 override가 필요한 HA 설정을 끄지 않는지 확인합니다.

포함된 profile은 핵심 구성 요소 replica 3개, 필수 node 분리, 선호 zone 분리, PDB와 admission webhook Fail 정책을 설정합니다. 중복 serving instance이며 3개 투표자의 consensus quorum이 아닙니다. API server·network, credential, 용량과 애플리케이션도 가용성에 영향을 줍니다.

기존의 destination.replicas/identity.resources/proxyInjector.resources는 의도한 컨테이너를 설정하지 못했습니다. 최상위 podDisruptionBudget으로는 PDB가 생성되지 않았고 topologySpreadConstraints도 사용되지 않았습니다. 원래 예제를 오프라인 render하면 replica는 3개이지만 controller resource 설정과 PDB가 없었습니다. 실제 포함 profile을 사용하고 결과를 검사하세요.

```bash
kubectl -n linkerd get pods -o wide
kubectl -n linkerd get pdb
kubectl -n linkerd get deployments -o yaml
```

대상 node가 3개보다 적으면 필수 anti-affinity 때문에 replica가 Pending일 수 있습니다. HA에 의존하기 전에 admission Fail 동작과 disruption을 검사하고 webhook policy 완화를 일반적인 가용성 해결책으로 쓰지 마세요.


## 확장 기능 설치

### Viz: dashboard와 metrics

CLI 소유 확장:

```bash
linkerd viz install > linkerd-viz.yaml
# Review the optional extension and its metrics backend.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Helm은 다음을 viz-values.yaml로 저장하고 render된 PVC, Deployment와 resource 설정을 검사합니다:

```yaml
prometheus:
  enabled: true
  resources:
    cpu:
      request: 300m
      limit: 1000m
    memory:
      request: 300Mi
      limit: 1Gi
  persistence:
    storageClass: gp3
    size: 10Gi
    accessMode: ReadWriteOnce
dashboard:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
tap:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi
metricsAPI:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
```

```bash
helm install linkerd-viz linkerd-edge/linkerd-viz \
  --version "$LINKERD_CHART_VERSION" -n linkerd-viz --create-namespace \
  -f viz-values.yaml --wait --timeout 10m
linkerd viz check
```

선택한 chart는 persistence **map이 있으면** 영속 볼륨을 사용하며 persistence.enabled를 스위치로 사용하지 않습니다. PVC template에는 accessMode가 필요합니다. 이전 예시는 이를 빠뜨려 null access mode를 생성했습니다. Map을 생략하면 emptyDir를 사용합니다. gp3 StorageClass는 사전 조건의 예시이며 Viz가 만들지 않습니다. EKS에서는 EBS CSI driver, 권한과 볼륨 topology를 확인하세요.

기본 Prometheus는 replica 1개이며 persistence를 사용하면 Deployment strategy는 Recreate입니다. PVC는 적절한 Pod 교체에서 데이터를 유지하지만 metrics storage를 HA로 만들거나 무중단을 보장하지 않습니다. Chart 2026.9.1의 기본값은 Prometheus v2.55.1과 6시간 보존입니다. Backend 유지 관리, 보존과 가용성 요구를 명확히 선택하세요.

이미 구성한 외부 Prometheus를 사용하면 다음은 **대안** values입니다:

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
```

전환 전 외부 서버의 Linkerd scrape/relabeling과 접근 정책을 구성하세요. HTTP ready endpoint뿐 아니라 실제 Viz query와 metric을 확인합니다. dashboard, tap, metricsAPI resource는 지원됩니다. grafana.enabled는 배포 스위치가 아니며 chart에는 별도 Grafana의 링크 설정이 있습니다.

초기 절차에는 localhost dashboard 명령을 사용하세요. dashboard.enforcedHostRegexp는 Host 검증이며 사용자 인증이 아닙니다. 빈 값은 chart의 기본 host 제한을 선택합니다. 조직 ingress에는 별도 인증·인가, 승인한 network 노출과 허용 host가 필요합니다.

### 분산 추적

edge-26.9.1에는 linkerd jaeger 하위 명령이 없습니다. 공개 linkerd-jaeger chart 이력은 2025.9.4에서 끝나므로 2026.9.1에 대응하는 확장이 아닙니다. 기존 install/check/upgrade/uninstall 명령 대신 별도로 관리하는 collector/backend와 선택한 proxy tracing 구성을 사용합니다.

Tracing에는 들어오는 trace context, 앱의 전파와 호환 collector/export protocol이 필요합니다. Viz topology·metric graph는 distributed trace가 아닙니다. 전체 경로는 [관측성 가이드](05-observability.md)와 [공식 tracing 문서](https://linkerd.io/docs/features/distributed-tracing/)를 확인하세요. 이번 설치 감사가 미검증 collector/Jaeger의 종단 동작을 입증하지는 않습니다. 기존 설치에 linkerd-jaeger release가 있다면 데이터·리소스를 조사하고 마이그레이션한 뒤 원래 소유 도구로 정리하세요. 현재 CLI로 제거된 확장을 관리할 수는 없습니다.

### Multicluster

CLI로 기본 확장을 render할 수 있습니다:

```bash
linkerd multicluster install > linkerd-multicluster.yaml
# Review network exposure, shared trust and actual gateway configuration first.
kubectl apply -f linkerd-multicluster.yaml
linkerd multicluster check
```

적용 전에 network에 맞는 gateway 노출 방식을 선택하세요. 확장 설치만으로 cluster 연결, 공유 trust와 원격 Kubernetes API 권한이 생기지는 않습니다.

**AWS Load Balancer Controller**를 사용하는 EKS 예시는 internal NLB를 선택하고 Linkerd gateway까지 TCP 전송을 유지합니다:

```yaml
gateway:
  replicas: 1
  serviceType: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
remoteMirrorServiceAccountName: linkerd-service-mirror-remote-access-default
```

multicluster-values.yaml로 저장한 뒤 Helm 대안을 사용합니다:

```bash
helm install linkerd-multicluster linkerd-edge/linkerd-multicluster \
  --version "$LINKERD_CHART_VERSION" -n linkerd-multicluster --create-namespace \
  -f multicluster-values.yaml --wait --timeout 10m
```

loadBalancerClass는 소유 controller를 선택합니다. EKS Auto Mode는 다른 class·설정 계약을 사용하므로 가정을 섞거나 기존 Service 소유권을 무작정 바꾸지 마세요. 원격 network에서 internal gateway와 probe 경로를 해석·연결할 수 있어야 합니다. 관계없는 ACM listener에서 Linkerd transport mTLS를 종료하지 않습니다.

gateway.resources는 이 chart에서 사용되지 않습니다. Gateway proxy resource는 injection 설정에서 오므로 무시된 values가 limit을 바꿨다고 가정하지 말고 실제 Pod를 확인하세요. 이 chart의 HA override는 gateway.replicas와 anti-affinity를 사용합니다.

현재 edge의 원격 credential은 exec auth provider를 거부합니다. [Multicluster 가이드](06-multi-cluster.md)의 지원 credential 절차를 사용하고 생성된 service-mirror controller·버전과 최소 권한 API 접근을 확인하세요.

## CNI와 Amazon EKS 구성

### 선택적 Linkerd CNI

Linkerd CNI는 기본 CNI와 chaining하며 Amazon VPC CNI나 Cilium을 대체하지 않습니다. Control plane과 workload가 CNI-enabled 설정을 사용하기 **전에** 해당 node에서 준비되어야 합니다:

```bash
# Optional branch, before control-plane installation.
helm install linkerd-cni linkerd-edge/linkerd2-cni \
  --version "$LINKERD_CHART_VERSION" -n linkerd-cni --create-namespace --wait
kubectl -n linkerd-cni rollout status daemonset/linkerd-cni --timeout=180s
CNI_ENABLED=true
linkerd check --pre --linkerd-cni-enabled
# Use --linkerd-cni-enabled=true for CLI control-plane installation,
# or --set cniEnabled=true for the control-plane Helm chart.
```

Node의 CNI 설정·binary directory와 실제 plugin 동작을 확인하세요. 기본 경로 /etc/cni/net.d와 /opt/cni/bin은 모든 플랫폼의 경로가 아닙니다. 선택한 control-plane chart는 cniEnabled를 사용하며 render에서 의도대로 linkerd-init이 빠지는지 확인해야 합니다.

Linkerd CNI가 없으면 일반 init-container redirect 경로에 NET_ADMIN capability가 필요합니다. CNI를 쓰면 작업이 node plugin으로 이동합니다. 이 릴리스는 native sidecar가 기본이므로 주입 진단에서 containers와 initContainers를 모두 확인하세요. 릴리스의 Identity Deployment는 bootstrap을 위해 일반 proxy와 시작 대기 비활성화를 명시하므로 이 예외를 주입 실패로 판단하면 안 됩니다. Native sidecar를 끄면 init container의 network·시작 순서가 달라집니다. 우회 UID를 일반적인 보안 해결책으로 쓰지 않습니다.

Cilium kube-proxy replacement의 문서화된 구성은 socketLB.hostNamespaceOnly=true로 Pod의 Service 주소를 유지해 discovery에 사용합니다. Linkerd CNI chaining에는 cni.exclusive=false도 필요합니다. 기본 CNI 소유자와 변경을 검토하고 설정을 통째로 덮어쓰지 마세요.

### 기존 EKS 클러스터

기존 지원 cluster를 사용하고 Linkerd 구분과 EKS 제공 버전을 모두 확인하세요. 과거 EKS 1.28 생성 명령은 현재 설치 안내로 부적절합니다. 이 Linux 절차는 호환 EC2 node를 전제합니다. Fargate는 여기의 Linkerd CNI DaemonSet을 실행할 수 없으므로 같은 절차의 대체 대상이 아닙니다.

전용 kubeconfig를 준비한다면:

```bash
: "${EKS_CLUSTER_NAME:?Set the intended existing cluster}"
: "${EKS_REGION:?Set its region}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --query 'cluster.{version:version,endpoint:endpoint}' --output json
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --kubeconfig "$PWD/linkerd.kubeconfig" --alias linkerd-lab
export KUBECONFIG="$PWD/linkerd.kubeconfig"
kubectl config current-context
kubectl -n kube-system get daemonset aws-node   -o jsonpath='{.spec.template.spec.containers[*].image}'
```

Cluster 변경 전에 의도한 endpoint/context를 확인하세요. 표준 Linkerd controller는 Kubernetes API credential을 사용합니다. linkerd-destination이 Service를 발견한다는 이유만으로 IAM role이 필요하지 않습니다. AWS API 권한은 실제 호출자인 Load Balancer Controller, EBS CSI, telemetry collector 등에 지원 IRSA/Pod Identity 방식으로 부여합니다.

### EKS dashboard와 network 고려사항

이전 internet-facing ALB 예시는 인증 설계 없이 관리 dashboard를 공개했습니다. 인증된 조직 ingress를 구성·검증하기 전에는 localhost 관리 경로를 사용하세요.

web Service 8084는 유효한 포트입니다. 별도 admin/readiness는 9994이며 chart의 readiness probe는 그 포트의 /ready입니다. UI listener에도 같은 health 의미가 있다고 가정하지 마세요. ALB에는 target health, security group, host 검증, 인증서 소유와 사용자 인증을 함께 맞춰야 합니다. TLS 인증서만으로 dashboard 사용자가 인증되지는 않습니다.

실제 출발지·목적지 역할에 맞춰 security-group·NetworkPolicy 범위를 제한하세요. 구성 요소 포트 표는 진단 정보이며 모든 출발지에 proxy metric·webhook을 노출하라는 뜻이 아닙니다. 실제 cluster의 CNI 시작, DNS, admission, identity와 node 간 경로를 검증합니다.

## 설치 확인 및 검증

```bash
linkerd check
linkerd check --proxy -n my-app
linkerd viz check
linkerd multicluster check
kubectl -n linkerd get pods,services,pdb -o wide
kubectl -n linkerd-viz get pods,services -o wide
```

설치한 확장만 검사하세요. check --proxy는 데이터 플레인 검사이며 “모든 확장 포함”을 뜻하지 않습니다. 이 검사들이 애플리케이션 업무 로직을 검증하지도 않습니다.

샘플 앱은 고정된 manifest를 검토하고 선택한 namespace에 annotation을 적용한 뒤 대상 workload를 재생성합니다. 변경 가능한 emojivoto URL과 모든 live Deployment의 왕복 편집은 재현 가능한 입력이 아닙니다. Image·architecture, Service port, readiness와 실제 HTTP/TCP 결과를 확인하세요.

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
linkerd viz stat deploy/my-app -n my-app
linkerd viz top deploy/my-app -n my-app
```

my-app을 실제 namespace·Deployment로 바꾸세요. Metrics/tap/top은 확장과 지원 protocol에 의존하며 모든 트래픽 암호화나 업무 성공을 입증하지 않습니다.

## Linkerd 업그레이드

### 업그레이드 계획

정확한 target CLI/chart를 선택하고 release note, 호환성, 지원 version skew와 현재 상태를 확인합니다. 여기의 target이 모든 과거 2.14/2.16 설치에서 직접 업그레이드된다는 보장은 아닙니다. 필요한 중간 단계와 vendor 절차를 따르세요. Edge tag는 semantic version 보장이 아닙니다. 각 소유 도구로 CLI, CRD/control plane, 설치한 확장, data-plane proxy 순서로 갱신하세요.

기존 설치에는 check와 check --proxy를 사용합니다. check --pre는 namespace·설정 전제가 있는 신규 설치 검사이며 업그레이드 계획을 대체하지 않습니다. 기존 trust credential을 보존하고 제거된 CRD version을 검토하세요.

### CLI 소유 설치

```bash
# First install/verify the selected target CLI and review the supported upgrade path.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds > linkerd-crds-upgrade.yaml
kubectl apply -f linkerd-crds-upgrade.yaml
linkerd upgrade > linkerd-upgrade.yaml
# Review retained configuration and credentials before applying.
kubectl apply -f linkerd-upgrade.yaml
linkerd check
linkerd viz install > linkerd-viz-upgrade.yaml
kubectl apply -f linkerd-viz-upgrade.yaml
linkerd viz check
# Likewise review/install the selected multicluster extension if present.
linkerd prune > linkerd-obsolete.yaml
# Review ownership and contents before any kubectl delete -f linkerd-obsolete.yaml.
```

확장 update는 install로 render하며 viz upgrade 하위 명령은 없습니다. Help 종료 코드가 0이어도 상위 도움말일 수 있으므로 실제 명령 목록과 생성한 resource를 확인하세요. Prune 출력은 삭제 전에 검토합니다. Multicluster controller 갱신에는 지원 절차로 re-link가 필요할 수 있습니다.

### Helm 소유 설치

```bash
umask 077
helm get values linkerd-control-plane -n linkerd > current-values.yaml
helm get manifest linkerd-control-plane -n linkerd > current-manifest.yaml
# Migrate intentional overrides to reviewed-values.yaml; preserve current trust credentials.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --wait
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd \
  --reset-values -f reviewed-values.yaml --wait --timeout 10m
# Upgrade each installed extension with its own reviewed values and pinned chart.
linkerd check
```

검토한 values에는 의도한 HA/CNI와 **기존** trust/issuer 구성 또는 지원 external-secret 참조가 포함되어야 합니다. 이를 보존하지 않은 --reset-values는 동작을 바꾸거나 실패할 수 있고 --reuse-values는 오래된 설정을 유지할 수 있습니다. Target 기본값과 override를 비교하고 일반 업그레이드라는 이유로 CA를 재생성하지 마세요.

### 데이터 플레인 갱신

가용성 정책에 따라 의도한 workload를 하나씩 갱신합니다:

```bash
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy}))}'
```

stat은 트래픽 통계이며 proxy image version 목록이 아닙니다. 위에서는 일반·native sidecar 위치를 모두 검사합니다. 재생성 후 관련 version skew 안내와 실제 readiness·트래픽을 확인하세요.

## 문제 해결

### Admission과 리소스

```bash
kubectl -n linkerd get service linkerd-proxy-injector
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml
kubectl -n linkerd get networkpolicy
kubectl -n linkerd get events --sort-by='.lastTimestamp'
: "${LINKERD_POD:?Set a control-plane Pod name}"
kubectl -n linkerd describe pod "$LINKERD_POD"
```

주입 실패는 CA bundle, webhook 선택·network, 설정 거부나 Pod security 때문일 수 있으며 언제나 Service 연결 문제는 아닙니다. Pending은 anti-affinity, taint, volume, quota와 resource 등의 원인이 있습니다. Limit·보안 설정을 바꾸기 전에 실제 event를 확인하세요.

### 인증서

기본 설치의 trust root는 **ConfigMap**, issuer 서명 키·인증서는 Secret에 있습니다:

```bash
set -euo pipefail
kubectl -n linkerd get configmap linkerd-identity-trust-roots \
  -o jsonpath='{.data.ca-bundle\.crt}' > trust-bundle.pem
openssl crl2pkcs7 -nocrl -certfile trust-bundle.pem |
  openssl pkcs7 -print_certs -text -noout
kubectl -n linkerd get secret linkerd-identity-issuer -o json |
  jq -er '.data["crt.pem"] // .data["tls.crt"]' |
  base64 -d | openssl x509 -noout -dates
```

기본 issuer 형식은 crt.pem을 사용하고 구성한 kubernetes.io/tls 통합은 tls.crt를 사용합니다. 모든 Secret 필드가 같다고 가정하지 말고 실제 scheme을 확인하세요. 사용자 지정 trust 통합은 저장 소유 도구도 바꿀 수 있습니다. 전체 trust certificate, 시계·유효기간, issuer 가용성과 identity 오류를 확인하고 계획하지 않은 root 교체를 피합니다.

### 구성 요소와 proxy 로그

```bash
kubectl -n linkerd logs deployment/linkerd-destination -c destination
kubectl -n linkerd logs deployment/linkerd-destination -c policy
kubectl -n linkerd logs deployment/linkerd-identity -c identity
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector
: "${APP_POD:?Set an application Pod name}"
kubectl -n my-app logs "$APP_POD" -c linkerd-proxy
linkerd diagnostics proxy-metrics "$APP_POD" -n my-app
```

설치 버전의 실제 component/container 이름을 사용하고 Pod 삭제·교체 전에 관련 로그를 보관하세요.

## 제거

### 애플리케이션 proxy 먼저 제거

Mesh 전송 정책·라우팅·관측성 상실에 대비합니다. Workload 소유 도구로 주입 설정과 수동 proxy 구성을 제거하고 재생성한 뒤, control plane을 지우기 전에 두 container 위치를 검사하세요:

```bash
# Choose the actual application namespace/Deployment and review all injection sources.
kubectl annotate namespace my-app linkerd.io/inject-
# Also remove any Pod-template injection override/manual proxy using its manifest owner.
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, containers: ([.spec.containers[]?, .spec.initContainers[]?] | map(.name))}'
```

Namespace annotation 제거만으로 Pod-template annotation이 무효화되거나 수동 주입 proxy가 사라지지는 않습니다. Unmeshing 후 앱 연결·보안을 검증하세요. 남은 주입 workload 검사를 force로 우회하지 않습니다.

### CLI 소유 제거

```bash
# Only after applications are unmeshed and extension dependencies are removed.
linkerd viz uninstall > remove-viz.yaml
linkerd multicluster uninstall > remove-multicluster.yaml
# Inspect each manifest and remove only the extensions actually installed via CLI.
kubectl delete -f remove-viz.yaml
kubectl delete -f remove-multicluster.yaml
linkerd uninstall > remove-linkerd.yaml
# This includes namespace-scoped resources and cluster-wide CRDs.
kubectl delete -f remove-linkerd.yaml
```

설치한 확장만 제거하세요. 생성된 control-plane 제거에는 CRD도 포함되며 CRD 삭제는 해당 custom-resource instance를 삭제합니다. 남길 내용을 목록화·백업하세요. Deployment만 지우는 작업이 아닙니다.

### Helm 소유 제거

```bash
# Only the releases actually installed through Helm, after unmeshing applications.
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-multicluster -n linkerd-multicluster
helm uninstall linkerd-control-plane -n linkerd
# Inventory/back up CR instances before removing the CRDs.
helm uninstall linkerd-crds -n linkerd
```

Linkerd CNI를 설치했다면 의존 workload가 없어진 뒤 node-plugin cleanup을 별도로 수행하고 기본 CNI가 유지되는지 확인합니다. Namespace는 소유권과 남은 내용을 확인한 뒤 삭제하며 4개 namespace를 무조건 지우는 절차로 만들지 않습니다.

## 다음 단계

- [아키텍처](02-architecture.md)
- [트래픽 관리](03-traffic-management.md)
- [보안·인증서 수명 주기](04-security.md)
- [관측성](05-observability.md)
- [멀티클러스터](06-multi-cluster.md)
- [설치 퀴즈](../../quizzes/service-mesh/linkerd/installation.md)

## 참고 자료

- [릴리스 모델](https://linkerd.io/releases/)과 [edge-26.9.1 asset](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)
- [Kubernetes matrix](https://linkerd.io/docs/reference/k8s-versions/)와 [Gateway API 호환성](https://linkerd.io/docs/features/gateway-api/)
- [Helm 설치](https://linkerd.io/docs/tasks/install-helm/)와 [공식 edge chart index](https://helm.linkerd.io/edge/index.yaml)
- [HA 동작](https://linkerd.io/docs/features/ha/)과 [cluster/Cilium 설정](https://linkerd.io/docs/reference/cluster-configuration/)
- [인증서 생성](https://linkerd.io/docs/tasks/generate-certificates/)과 [Smallstep create 참조](https://smallstep.com/docs/step-cli/reference/certificate/create/)
- [CNI](https://linkerd.io/docs/features/cni/), [업그레이드](https://linkerd.io/docs/tasks/upgrade/), [제거](https://linkerd.io/docs/tasks/uninstall/)
- [AWS Load Balancer Controller Service 설정](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)과 [EKS Fargate 제약](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
