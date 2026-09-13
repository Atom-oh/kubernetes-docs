# Linkerd 모범 사례

> **검토 기준**: 2026년 9월 11일 · Linkerd edge-26.9.1 / chart 2026.9.1

선택한 버전과 전제 조건은 [설치](01-installation.md), [보안](04-security.md), [관찰성](05-observability.md), [다중 클러스터](06-multi-cluster.md) 가이드를 따릅니다. 이 장은 해당 절차를 운영 검토로 연결하며 특정 환경의 운영 준비 완료를 인증하지 않습니다.

변경 전에 Kubernetes context, API endpoint, 리소스 소유자를 확인합니다. 아래 명령은 현재 context와 예제 namespace/workload 이름을 사용합니다. 이번 감사에서 실제 upgrade, rollback, migration, 부하 테스트는 수행하지 않았습니다.

## 준비 상태 검토

- [ ] Kubernetes/Linkerd/Gateway API 호환성과 선택한 배포판의 release note를 확인합니다.
- [ ] 실제 replica, 배치, 용량, disruption 동작, admission 정책을 확인합니다.
- [ ] Root, issuer, workload 인증서 수명을 구분하고 갱신/복구 절차를 검증합니다.
- [ ] 거부할 caller와 mesh 밖 경로를 포함한 identity/인가 동작을 시험합니다.
- [ ] 지표, 로그, trace 요구사항, 알림 전달, 데이터 누락 감지를 확인합니다.
- [ ] 리소스 소유권, 보호된 backup, 버전별 upgrade/복구 절차, 운영 책임을 기록합니다.

공유 trust는 의도한 linked mesh 관계에 필요하며 관계없는 모든 cluster의 요구사항은 아닙니다. ServiceProfile도 범용 준비 조건이 아닙니다. 현재 Gateway API 정책과 호환성 profile의 역할/우선순위가 다릅니다.

```bash
linkerd version
linkerd check
linkerd check --proxy
kubectl -n linkerd get deployments,pods,poddisruptionbudgets
kubectl -n my-app get pods -o wide
```

전체 check 출력과 종료 상태를 유지합니다. “valid” grep은 “invalid”에도 일치하고 grep 성공이 원래 명령 실패를 감출 수 있습니다.

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
if linkerd check --proxy > linkerd-check.log 2>&1; then
  cat linkerd-check.log
else
  check_status=$?
  cat linkerd-check.log >&2
  exit "$check_status"
fi
```

명령이 성공 종료해도 warning을 검토합니다. 정상 control-plane check가 애플리케이션 SLO나 Region failover를 입증하지는 않습니다.

## 리소스 할당

요청/connection 동시성, protocol, payload/stream 크기, discovery 규모, 지표 cardinality, memory pressure, CPU throttling을 측정하여 결정합니다. RPS만으로 proxy 리소스를 정할 수는 없습니다.

다음은 **시작점 예시**이며 용량 보장이 아닙니다.

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
```

하나의 일관된 YAML mapping을 사용합니다. 같은 mapping의 `proxy:`를 세 번 반복하면 유효하지 않으며 관대한 parser는 마지막 profile만 조용히 남길 수 있습니다.

기존 workload용 **merge patch**를 `proxy-resources-patch.yaml`로 저장합니다.

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/proxy-cpu-request: 500m
        config.linkerd.io/proxy-cpu-limit: 2000m
        config.linkerd.io/proxy-memory-request: 128Mi
        config.linkerd.io/proxy-memory-limit: 500Mi
```

```bash
# A merge patch for one existing, reviewed workload; this starts a rollout.
kubectl -n my-app patch deployment/api --type merge --patch-file proxy-resources-patch.yaml
kubectl -n my-app rollout status deployment/api --timeout=5m
kubectl -n my-app top pod --containers
```

`kubectl top pod --containers`는 container별 데이터를 요청합니다. 이 명령에는 `-c linkerd-proxy` filter가 없습니다. 수집 pipeline이 native init sidecar를 예상대로 보고하는지도 확인합니다. 한 조회에서 안 보인다는 이유만으로 없다고 판단하지 말고 Pod spec/status와 리소스 지표를 함께 봅니다.

### Runtime worker와 CPU quota

CPU request/limit은 scheduling과 CPU 할당을 설정합니다. Limit 4가 proxy worker thread 4개를 직접 요청하는 것은 아닙니다. 선택한 chart에는 별도의 runtime worker 범위가 있습니다.

```yaml
proxy:
  runtime:
    workers:
      minimum: 1
      maximum: 4
      maximumCPURatio: 1
```

독립적인 values 조각입니다. 최상위 YAML key를 중복하지 말고 하위 필드를 병합합니다. 해당 chart는 Kubernetes CPU limit과 별도로 worker minimum/maximum/CPU-ratio를 출력합니다. 실제 runtime은 사용 가능한 CPU와 부하에도 좌우되므로 상한만 높인다고 성능이 개선되지는 않습니다. 이전 고정 `proxy.cores` 설정은 template에서 deprecated입니다.

## 고가용성

### Core control plane

**같은 chart release의 HA profile**을 인증서 설정을 포함한 검토된 설치 values와 함께 사용합니다.

```bash
set -euo pipefail
umask 077
# Use the same reviewed chart version for the profile and render.
curl --fail --show-error --location \
  https://raw.githubusercontent.com/linkerd/linkerd2/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml \
  -o values-ha.yaml
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd \
  -f reviewed-core-values.yaml -f values-ha.yaml > reviewed-ha.yaml
```

패키지 profile은 controller replica 3개, control-plane PDB 3개, component별 필수 node anti-affinity, 선호 zone 분산, 실패 시 injection 거부를 설정합니다. 리소스와 rollout 설정도 제공합니다. 렌더링된 Deployment/PDB/webhook과 실제로 배치 가능한 node를 확인합니다. Values 파일은 순서대로 병합되므로 HA profile이 앞의 리소스 설정을 덮어쓸 수 있습니다. 최종 결과를 확인하고 추가 override에서도 필수 HA 제어를 유지합니다.

이전 예제의 `destination.replicas/resources`, `identity.replicas/resources`, `proxyInjector.replicas/resources`는 이 chart에서 무시되었습니다. 지원되는 controller 리소스 값은 `destinationResources`, `identityResources`, `proxyInjectorResources` 등 패키지 profile의 필드입니다. 임의의 `podAntiAffinity`, `topologySpreadConstraints`, `podDisruptionBudget` key가 자동으로 Pod 필드가 되지는 않습니다.

Replica 3개는 quorum 보장이 아닙니다. 적합한 node가 부족하면 필수 배치 조건 때문에 Pending이 될 수 있고 선호 zone 조건은 zone별 하나를 보장하지 않습니다. PDB는 지원되는 자발적 eviction을 제한하며 모든 장애나 controller rollout을 막지는 않습니다.

### Viz와 지표 가용성

의도한 retention, 인증, HA 동작을 갖춘 별도 Prometheus/query endpoint가 있을 때 stateless Viz component를 늘리는 값입니다.

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
tap:
  replicas: 2
metricsAPI:
  replicas: 2
tapInjector:
  replicas: 2
dashboard:
  replicas: 2
```

Replica 수만으로 장애 영역 분리, disruption 보호, 지표 가용성이 생기지 않습니다. 실제 배치와 replica 중복 제거를 포함한 외부 query 구조를 확인합니다.

대안으로 **단일 local Prometheus**의 데이터를 영속화할 수 있습니다.

```yaml
prometheus:
  enabled: true
  persistence:
    accessMode: ReadWriteOnce
    size: 50Gi
```

동작하는 default StorageClass 또는 chart의 적절한 명시적 storage-class 설정이 필요합니다. 선택한 Viz chart의 Prometheus는 replica 1개이며 PVC와 Recreate 전략을 사용합니다. 이전 `prometheus.replicas:2`는 무시되었고 accessMode 없는 `persistence.enabled:true`는 잘못된 PVC를 만들었습니다. Persistence는 재시작 후 데이터 보존에 도움이 되지만 Prometheus HA는 아닙니다.

## 업그레이드와 복구

### 버전 변경 전에 경로 선택

공개 Linkerd artifact는 edge track이며 vendor의 stable 배포판은 지원하는 upgrade 지침이 다를 수 있습니다. 공개 installer는 범용 stable 버전/downgrade installer가 아닙니다. 설치 가이드에 따라 선택한 CLI를 받아 검증합니다.

Edge 버전 번호는 semantic-version 호환성 보장이 아닙니다. Release별 변경과 control/data-plane skew를 검토하고 필요한 중간 release를 사용합니다. `check --pre`는 설치 전 검사이며 기존 mesh의 upgrade 가능 여부를 판단하는 검사가 아닙니다.

원하는 values와 필요한 credential을 소유자를 통해 backup하고 key 자료를 보호하며 복원을 시험합니다. `helm get values`는 issuer 자료를 노출할 수 있으므로 출력을 공개하지 않습니다. 이전 computed default를 새 chart에 무조건 적용하지 말고 검토한 target values를 준비합니다.

### CLI 소유 설치

지원 경로를 검토하고 기존 설정/credential을 보존한 뒤의 절차입니다.

```bash
set -euo pipefail
# The selected, verified target CLI must already be on PATH.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds | kubectl apply -f -
linkerd upgrade | kubectl apply -f -
linkerd check
# CLI-owned Viz only; preserve its complete reviewed configuration.
linkerd viz install -f reviewed-viz-values.yaml | kubectl apply -f -
linkerd viz check
```

CRD → core → 호환 extension → workload proxy 순서입니다. 현재 extension CLI는 전체 설정과 함께 `install`을 사용하며 `linkerd viz upgrade`는 없습니다. Release별 pruning/migration 지침을 확인하고 삭제할 stale resource 후보를 먼저 검토합니다.

Multicluster는 해당 가이드의 원하는 Helm `controllers` 목록과 현재 Link/credential 소유권을 유지합니다. Deprecated legacy link 소유 controller를 자동 upgrade 단계로 다시 만들지 않습니다.

### Helm 소유 설치

예제 target은 2026.9.1이며 실제 설치 버전에서 지원되는 경로를 확인한 경우에만 사용합니다.

```bash
set -euo pipefail
umask 077
helm get values linkerd-control-plane -n linkerd > current-core-values.yaml
helm get values linkerd-viz -n linkerd-viz > current-viz-values.yaml
# Prepare reviewed target values and approved migration steps before these changes.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version 2026.9.1 -n linkerd --wait --timeout 10m
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd -f reviewed-core-values.yaml \
  --wait --timeout 10m
linkerd check
helm upgrade linkerd-viz linkerd-edge/linkerd-viz \
  --version 2026.9.1 -n linkerd-viz -f reviewed-viz-values.yaml \
  --wait --timeout 10m
linkerd viz check
```

CRD, core, CNI, extension의 기존 소유자를 유지합니다. Manifest가 비슷하다는 이유만으로 Helm release에 CLI apply 절차를 섞지 않습니다.

### Workload rollout

관련 StatefulSet/DaemonSet/job을 포함한 실제 mesh workload controller를 선택하고 애플리케이션별 rollout을 조정합니다. Namespace 전체 루프는 무관한 workload도 재시작하며 고정 30초 sleep은 안정화 검증이 아닙니다.

```bash
# One explicitly selected meshed Deployment, after checking disruption/capacity.
kubectl -n my-app rollout restart deployment/api
kubectl -n my-app rollout status deployment/api --timeout=5m
linkerd check --proxy -n my-app
linkerd viz stat deployment/api -n my-app
```

다음 workload로 넘어가기 전에 readiness, identity/정책, 대표 애플리케이션 트래픽을 검증합니다. Namespace annotation은 새 Pod에 적용되며 실행 중인 sidecar를 제자리에서 갱신하지 않습니다.

### 복구와 여러 control plane

해당 버전/CRD의 검증된 복구 계획을 정의합니다. Core Helm release만 rollback해도 별도 관리 CRD, 모든 credential 변경, 실행 중인 workload proxy까지 되돌아가지는 않습니다. 임의의 이전 CLI를 받고 upgrade를 실행하는 것은 범용 downgrade 절차가 아닙니다.

이전 “blue-green” 예제는 다른 namespace에 설치한 뒤 `proxy-version`을 바꿨습니다. 이는 control plane이 아니라 proxy 이미지를 선택합니다. 두 namespace의 기본 chart 렌더링에는 admission webhook을 포함한 cluster-scoped 이름 충돌도 있습니다. Namespace 하나를 추가하는 것만으로 격리된 공존이나 안전한 workload 이전이 되지 않습니다. 배포판이 지원하는 설계에서 리소스 소유권, 트래픽/identity 선택을 명시하고 검증될 때까지 복구 가능성을 유지합니다.


## Mesh 등록과 Protocol 처리

새 Pod에 적용하는 namespace 등록입니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

기존 workload의 opt-out은 완전한 Deployment가 아닌 Pod-template merge patch입니다.

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: disabled
```

Annotation 변경만으로 실행 중이거나 수동으로 포함한 proxy가 제거되지는 않습니다. 실제 manifest를 소유자를 통해 정리하고 필요한 경우 workload를 재생성합니다. `containers`와 `initContainers`를 함께 확인합니다. 일반 container 목록에 없다고 native sidecar가 없는 것은 아닙니다.

Opaque port는 HTTP protocol detection을 생략하면서 관련 TCP proxy 경로, mTLS, 정책을 유지합니다. 준비된 MySQL workload의 Pod-template patch와 일관된 Service annotation입니다.

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/opaque-ports: '3306'
---
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: my-app
  annotations:
    config.linkerd.io/opaque-ports: '3306'
spec:
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
```

Pod와 Service port 매핑이 맞아야 하며 선택된 Server의 `proxyProtocol`도 protocol 처리에 영향을 줍니다. Opaque mode는 해당 stream의 HTTP route 지표를 제공하지 않습니다.

Skip-inbound/outbound-ports는 proxy 경로를 우회하여 mesh 암호화, 정책, 지표를 없앨 수 있습니다. Redis, Memcached, database port 우회를 범용적인 지연 최적화로 권장하지 않습니다.

ServiceProfile route timeout은 deadline이며 connection pool 설정이 아닙니다. Protocol 처리도 모든 애플리케이션의 HTTP/1 연결을 전체 구간 HTTP/2로 바꾼다고 보장하지 않습니다. 실제 connection 재사용, buffering, protocol 동작을 측정한 뒤 조정합니다.

## 인증서 운영

공개 root, issuer credential, proxy leaf, webhook 인증서를 각 소유자가 있는 별도 수명주기로 취급합니다. 기본 short-lived proxy leaf는 범용적인 잔여 60일 체크리스트를 만족할 수 없습니다. 설정된 수명과 갱신 여유에 따라 임계값을 정합니다.

보안 가이드에서 검증한 credential 조회, issuer reload/event, cert-manager 소유권 예제를 사용합니다. `isCA:true`만으로 Issuer 설치, root 배포, 모든 사용자 교체, 알림 전달이 이루어지지는 않습니다.

이전 인증서 CronJob은 검증되지 않은 오래된 CLI 이미지와 누락된 RBAC를 사용하고 grep으로 check 실패를 가렸습니다. 예약된 검사에는 지원되는 runtime, 범위를 제한한 credential, 명시적인 실패 처리, 검증된 전달 경로가 필요합니다. 위 check/log 예제는 종료 상태를 보존하며 보안 가이드에는 지표 기반 알림이 있습니다. 실제 전달 통합 없이 완성된 알림 서비스가 되지는 않습니다.

## 근거에 따른 문제 해결

Injection 문제는 namespace와 실제 Pod template/Pod metadata, 두 container 유형, webhook 설정, injector log를 확인합니다.

```bash
kubectl get namespace my-app -o yaml
kubectl -n my-app get deployment api -o yaml
# Set this to an actual API Pod.
api_pod=api-example-pod
kubectl -n my-app get pod "$api_pod" -o json | jq '{
  annotations: .metadata.annotations,
  containers: [.spec.containers[]? | {name,image,resources}],
  initContainers: [.spec.initContainers[]? | {name,image,restartPolicy,resources}],
  status: .status
}'
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector --tail=100
```

지연이나 불안정은 애플리케이션 동작, resource pressure, Pending Pod, endpoint, DNS, protocol detection, 인증서/정책 오류를 비교합니다. Timeout 증가나 control plane 전체 재시작은 진단이 아닙니다.

```bash
linkerd check
linkerd check --proxy
linkerd viz stat deploy -n my-app
linkerd viz tap deployment/api -n my-app --max-rps 20
linkerd viz edges deploy -n my-app
linkerd identity -n my-app -l app=api
kubectl -n my-app top pod --containers
kubectl -n my-app logs deployment/api -c linkerd-proxy --tail=100
kubectl -n linkerd logs deployment/linkerd-destination -c destination --tail=100
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
kubectl -n linkerd get events --sort-by=.lastTimestamp
```

공개 leaf 인증서는 `linkerd identity`로 조회하며 proxy 이미지에 고정된 `end-entity.crt` 파일이 있다고 가정하지 않습니다. ServiceProfile의 `viz routes`나 현재 정책 진단도 실제 설정된 리소스에 사용합니다. Controller log를 읽을 때 대상 container를 명시합니다.

대상을 좁혀 수정한 뒤 명령 완료뿐 아니라 원래 실패했던 경로를 다시 검증합니다.

## Istio에서 이전

전환을 설계하기 전에 workload별 기능과 보안 속성을 파악합니다. 다음은 **부분적인 기능 비교**이며 기계적인 manifest 변환표가 아닙니다.

| Istio 개념 | Linkerd에서 검토할 점 |
|---|---|
| VirtualService | 지원되는 Gateway API routing 기능; ServiceProfile은 호환성 인터페이스이며 전체 대응은 아님 |
| DestinationRule | Load balancing, failure accrual, connection 동작, TLS 요구사항을 개별 재평가 |
| PeerAuthentication STRICT | 기본 Linkerd 정책은 mesh 밖 평문을 허용할 수 있으므로 자동 mTLS만으로 부족하며 적절한 인가 필요 |
| AuthorizationPolicy | Linkerd target/인증 모델이 다르며 JWT/user claim 등 조건은 별도 설계 |
| Sidecar traffic scope | Injection annotation이나 network firewall과 일괄 대응하지 않음 |
| Gateway | 적합한 ingress/gateway 구현과 Linkerd 통합을 선택/구성 |

Classic injection label, revision label/tag, Pod annotation, 수동 주입 manifest, ambient 등록은 서로 다릅니다. `istio-injection`만 제거해서는 모두 처리되지 않습니다. Workload를 바꾸기 전에 실제 Istio/Linkerd CNI와 proxy 등록 상태를 확인합니다.

Istio와 Linkerd mesh mTLS가 자동 상호 운용한다고 가정하지 않습니다. 혼합 전환 단계에는 명시적인 traffic/security 경계와 검증한 애플리케이션 동작이 필요합니다. 같은 workload를 두 interception 경로에 실수로 등록하지 않아야 합니다. 의존성이 namespace 경계를 넘으면 namespace만으로 안전한 이전 단위를 정할 수 없습니다.

실제 검토 순서는 의존성/정책 파악, 격리 환경 재현, 허용/거부 흐름과 복구 시험, 의도적으로 선택한 workload 그룹의 이동입니다. 맞는 등록 제어를 정리하고 정확히 원하는 proxy 경로인지 확인하며 대표 트래픽을 측정한 뒤 범위를 넓힙니다. 필요한 사용자가 더는 없고 복구 계획이 유효한 뒤에만 이전 control plane/리소스를 제거합니다.

이 내용은 무조건적인 namespace label/restart/uninstall 절차와 그림의 잘못된 일대일 기능 대응을 대체합니다. 애플리케이션 호환성과 운영 이전은 환경별로 검증해야 합니다.

## 참고 자료

- [선택한 HA profile](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml)
- [Proxy 설정](https://linkerd.io/docs/reference/proxy-configuration/)
- [해당 버전 proxy runtime template](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/partials/templates/_proxy.tpl)
- [Upgrade 지침](https://linkerd.io/docs/tasks/upgrade/)
- [인가 정책](https://linkerd.io/docs/reference/authorization-policy/)
- [Istio injection](../istio/advanced/07-sidecar-injection.md)과 [ambient mode](../istio/advanced/01-ambient-mode.md)
