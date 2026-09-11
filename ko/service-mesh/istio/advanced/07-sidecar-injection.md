# Sidecar Injection

> **검증 기준**: Istio 1.31.0, Kubernetes 1.32–1.36
> **마지막 검토**: 2026년 9월 11일

자동 주입은 새로 생성되는 Pod를 수정하는 admission webhook입니다. 기존 실행 중인 Pod에 sidecar를 추가하거나 Deployment template 자체를 수정하지 않습니다. 수동 `istioctl kube-inject`는 프록시 구성이 포함된 애플리케이션 manifest를 렌더링합니다.

## 자동 주입 설정

### Namespace 레벨

기존 애플리케이션 namespace에 한 가지 주입 모드를 선택합니다. 변경 전에 라벨과 설치된 revision을 기록하고 실제 injector가 없는 revision/tag를 선택하지 마세요.

```bash
# Existing, reviewed application namespace; inspect before choosing one mode.
INJECTION_NAMESPACE=injection-demo
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode

# Legacy/default injection alternative, only when no revision/ambient mode is selected.
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection=enabled --overwrite
```

```bash
# Alternative: choose an already installed revision or existing revision tag.
istioctl tag list
kubectl get mutatingwebhookconfigurations -l istio.io/rev
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection-
kubectl label namespace "$INJECTION_NAMESPACE" istio.io/rev=<installed-revision-or-tag> --overwrite
```

Namespace에 `istio-injection`과 `istio.io/rev`가 모두 있으면 legacy `istio-injection` 라벨이 우선합니다. Namespace의 `istio-injection=disabled` 또는 Pod의 `sidecar.istio.io/inject="false"`는 다른 주입 라벨이 있어도 주입을 비활성화합니다. 명시적 라벨이 없으면 installer의 `enableNamespacesByDefault` 설정이 없는 한 일반적으로 주입하지 않습니다.

가용성·PDB·용량을 검토하고 의도한 workload만 새로 생성해 선택한 injector를 사용하게 합니다. Namespace 라벨만 바꾸어서는 기존 Pod가 바뀌지 않습니다. Ambient enrollment는 별도로 다루며 dataplane mode를 혼합하지 말고 [ambient migration 가이드](01-ambient-mode.md)를 따르세요.

### Pod 레벨

주입 **label**은 Pod metadata 또는 Deployment의 `spec.template.metadata`에 둡니다. 같은 이름의 옛 annotation은 deprecated되었습니다.

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "true"
```

이 조각은 주입 대상 Pod를 선택하지만 namespace disable을 무시하거나 앱을 배포하지 않습니다. 기존 앱 라벨·revision·workload 설정을 보존하세요. 임의의 `myapp:latest` 이미지로 실행 가능한 Pod가 아닌 template 조각입니다.

## 수동 주입

대상 control plane과 맞는 `istioctl` 버전·전체 설정을 사용합니다. kube-inject는 기본적으로 선택한 cluster 설정을 읽을 수 있으며, 재현 가능한 로컬 렌더를 위해서는 해당 revision의 실제 injector/mesh ConfigMap을 내보내 먼저 검토합니다.

```bash
# Obtain all three files from the same installed revision/configuration.
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.config}' > inject-config.yaml
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.values}' > inject-values.yaml
kubectl -n istio-system get configmap <mesh-configmap> -o jsonpath='{.data.mesh}' > mesh-config.yaml

# Render from the reviewed original application manifest with matching istioctl.
istioctl kube-inject --revision <actual-revision-or-default> --injectConfigFile inject-config.yaml --meshConfigFile mesh-config.yaml --valuesFile inject-values.yaml --filename deployment.yaml --output deployment-injected.yaml

# Review the generated file and deployment diff before the planned rollout.
kubectl diff -f deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

Istio1.31에서 `--revision`을 생략하면 로컬 파일이 있어도 기본 revision watcher가 cluster에 접속하여 대기할 수 있습니다. 내보낸 설정에 맞는 실제 revision을 명시하고, revision 없는 기본 설치는 `default`를 사용합니다. 명시한 revision과 세 로컬 설정 파일로 실행한 렌더는 cluster 조회 없이 검증했습니다.

`deployment.yaml`은 원본 애플리케이션 리소스여야 합니다. 생성된 출력과 분리하고 설정/버전 변경 때 원본에서 다시 렌더링하세요. 자동·수동 주입의 관리 방식을 명확히 하고 admission 결과를 확인하며 생성된 proxy container에 임의 수정을 중첩하지 않습니다. `kubectl diff`의 exit 1은 보통 차이가 있다는 뜻이며 적용 승인이나 검증 성공을 뜻하지 않습니다.

## Sidecar 리소스 설정

기존 예시 requests/limits를 workload별 튜닝 입력으로 유지하며 production sizing으로 보장하지 않습니다.

```yaml
# Existing Deployment: spec.template fragment
metadata:
  annotations:
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
```

Request와 limit을 함께 명확히 설정하세요. proxyCPU/proxyMemory만 지정하고 대응 limit을 생략하면 그 limit이 제거될 수 있습니다. 렌더된 proxy resource, namespace LimitRange/ResourceQuota, CPU throttling·메모리 사용량을 확인합니다. Pod template 변경은 새로 생성되는 Pod에 적용됩니다.

## Injection 제외

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "false"
```

이 라벨은 향후 sidecar 주입을 막지만 기존 proxy를 제거하거나 ambient capture를 해제하지 않습니다. 기존 라벨·annotation을 함께 검토하고 선택한 workload만 정상 rollout 절차로 재생성하세요.

## 문제 해결

```bash
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode
kubectl get mutatingwebhookconfigurations
kubectl get events -n "$INJECTION_NAMESPACE" --sort-by=.lastTimestamp

kubectl get pods -n "$INJECTION_NAMESPACE" -o json |
  jq '.items[] | {
    pod:.metadata.name,
    revision:.metadata.annotations["istio.io/rev"],
    proxies: ([.spec.containers[]?, .spec.initContainers[]?] |
      map(select(.name == "istio-proxy") | {name,image,restartPolicy}))
  }'
istioctl proxy-status
```

Native sidecar는 `spec.initContainers`와 `restartPolicy: Always`, classic sidecar는 `spec.containers`를 사용합니다. Kubernetes native sidecar는1.33부터 stable이고1.32에서도 기본 활성화되지만, Istio의 `sidecar.istio.io/nativeSidecar` annotation은 아직 Alpha로 문서화되어 있습니다. READY가 항상2/2일 것으로 가정하지 말고 실제 injector 결과를 확인하세요.

Pod 생성 자체가 실패하면 controller event, webhook 연결/인증서, namespace/object selector, revision 존재 여부와 리소스 admission 제한을 확인합니다. Proxy가 있으면 readiness·로그·xDS 동기화를 별도로 확인하세요. Proxy 이름만으로 올바른 mesh enrollment가 증명되지는 않습니다.

## 참고 자료

- [Istio sidecar injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Istio injection annotations](https://istio.io/latest/docs/reference/config/annotations/)
- [Istio revision upgrades](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Kubernetes native sidecar containers](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Istio 1.31 injection template](https://raw.githubusercontent.com/istio/istio/1.31.0/manifests/charts/istio-control/istio-discovery/files/injection-template.yaml)
- [Istio 1.31 local injection command](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/kubeinject/kubeinject.go)
- [Istio 1.31 default revision resolution](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/cli/context.go)
