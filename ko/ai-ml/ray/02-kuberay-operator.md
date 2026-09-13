# Part 2: KubeRay 오퍼레이터

> **검토 기준**: KubeRay 1.7.0 · Ray 2.58.0 · 2026-09-12

## 실습 환경 준비

지원 중인 Kubernetes와 호환되는 kubectl, Helm 3을 준비합니다. CPU 구성 검토에는 GPU나 Karpenter가 필수가 아닙니다. 실제 EKS worker 공급은 기존 managed node group, Karpenter, Cluster Autoscaler 등 클러스터 운영 방식에 맞춥니다.

이번 검증은 공식 chart 다운로드·Helm 렌더링, CRD schema 검사, Ray 2.58.0의 autoscaler 설정 생성 함수 실행입니다. **Kubernetes API admission/CEL, controller reconciliation, 실제 autoscaling 또는 GPU 실행을 검증한 것은 아닙니다.**

## KubeRay가 하는 일

KubeRay는 Ray CR의 원하는 상태를 바탕으로 Pod·Service 등 하위 리소스를 조정합니다. 일반적인 RayCluster worker group이 반드시 Deployment나 StatefulSet으로 만들어진다고 가정하지 않습니다. Ray의 node는 보통 Ray Pod에 대응하며, 그 Pod가 올라가는 Kubernetes/EC2 node와는 다른 단위입니다.

오퍼레이터를 설치한 것만으로 Ray workload가 시작되지는 않습니다. RayCluster/RayJob/RayService 같은 리소스를 별도로 생성해야 합니다. 모든 spec 변경이 실행 중인 Pod에 자동으로 in-place 적용되는 것도 아니므로 업데이트 경로를 확인합니다.

## CRD와 기능 게이트

1.7.0 chart에서 확인한 CRD는 **RayCluster, RayJob, RayService, RayCronJob** 네 가지입니다. 모두 `ray.io/v1`을 제공합니다. 앞의 세 CRD에는 deprecated `v1alpha1`도 남아 있으며 새 예제는 `v1`을 사용합니다.

| 리소스 | 역할과 주의점 |
|---|---|
| RayCluster | head Pod와 worker group 관리; head-only 구성도 가능 |
| RayJob | batch 제출과 선택적 RayCluster 수명주기 관리; 기존 cluster 사용·정리 정책을 구분 |
| RayService | RayCluster와 Serve application 관리; 업데이트 전략과 traffic 전환 조건 확인 |
| RayCronJob | RayJob을 일정에 따라 생성; CRD가 설치돼도 기본 chart의 해당 feature gate는 꺼져 있음 |

Chart 기본값에서 `RayServiceIncrementalUpgrade`는 beta/enabled입니다. mTLS, RayCluster NetworkPolicy, History collector 자동 주입 등 alpha gate는 기본 비활성입니다. History Server 자체의 beta 상태와 collector 자동 주입의 alpha 상태를 혼동하지 않습니다. Feature gate가 있다는 것과 실제 리소스에 기능을 구성했다는 것은 다릅니다.

### RayJob 정리

`shutdownAfterJobFinishes`는 생략 시 false입니다. `ttlSecondsAfterFinished` 기본값 0도 이것을 자동으로 켜지 않습니다. 정리 옵션, 재시도와 시작/실행 deadline을 명시해야 합니다. 1.7에는 `deletionStrategy`도 있으며 기존 onSuccess/onFailure 방식과 deletionRules를 섞을 수 없는 제약이 있습니다.

공유 cluster 선택과 operator가 생성한 cluster 정리를 구분하고, 결과·checkpoint·로그를 먼저 보존합니다. RayCluster 삭제가 외부 artifact/PVC나 모든 EC2 비용까지 자동 정리한다는 뜻은 아닙니다.

### RayService 업데이트

`NewCluster`와 `NewClusterWithIncrementalUpgrade`는 새 cluster를 만드는 전략입니다. 후자는 Gateway API와 해당 GatewayClass 구현을 이용해 traffic을 점진적으로 전환합니다. “기존 Pod 몇 개를 단순 rolling update한다”는 설명과 다릅니다.

1.7에서 incremental feature gate가 기본 활성화됐더라도 strategy, Gateway 설정, 여유 용량, readiness와 연결 draining 조건을 맞춰야 합니다. 무중단은 목표이며 모든 application에 대한 보장이 아닙니다. 자세한 Serve 동작은 [Part 4](04-ray-serve.md)에서 다룹니다.

## 오토스케일링의 계층

Ray autoscaling은 `enableInTreeAutoscaling: true`로 켭니다. KubeRay는 head Pod에 autoscaler sidecar와 필요한 권한을 구성합니다. 아래 예제는 `autoscalerOptions.version: v2`를 명시해 버전 의존 기본값에 기대지 않습니다.

Ray autoscaler는 task·actor·placement/resource 요청을 보고 worker group의 원하는 규모를 조정하고 KubeRay가 Pod를 조정합니다. `numOfHosts`를 사용하는 group은 replica 하나가 여러 Ray Pod에 대응할 수 있으므로 `replicas == Pod 수`를 항상 가정하면 안 됩니다.

Kubernetes는 Pod를 node에 배치하고, Karpenter 같은 공급자는 배치할 수 없는 Pod의 요구사항을 기준으로 EC2 용량을 제공합니다. Pending 원인이 image pull, PVC, 권한·quota 문제라면 node를 추가하는 것만으로 해결되지 않습니다. Karpenter의 consolidation·drift 처리도 별도의 제어 동작입니다.

Ray 2.58.0 설정 생성기의 global idle timeout 기본값은 60초이며, group별 idle timeout도 설정할 수 있습니다. Min/max replica, 활동 상태, polling과 drain 조건이 있으므로 정확히 60초 뒤 Pod 삭제를 보장하는 timer로 해석하지 않습니다.

![RayCluster spec을 KubeRay가 Pod로 조정하고, Ray autoscaler가 workload 요구에 따라 worker 규모를 요청하며, Kubernetes 배치 및 EC2 node 공급이 별도 계층으로 동작하는 구조.](../../.gitbook/assets/ko-ai-ml-ray-02-kuberay-operator-0.png)

[인터랙티브 다이어그램](https://www.atomai.click/kubernetes-docs/archmaps/ko-ai-ml-ray-02-kuberay-operator-0.html)

## CPU/GPU 자원 선언

**Pod GPU limit만이 항상 유일한 설정 원천은 아닙니다.** 검토한 코드에서는 group의 structured `resources`, `rayStartParams`, 첫 번째 Ray container의 resource limit/request가 우선순위에 따라 사용됩니다. `num-gpus`가 명시돼 있으면 controller가 GPU limit으로 무조건 덮어쓰지 않습니다.

Ray 2.58.0 설정 생성 함수에서 GPU limit 1 → Ray GPU 1, `rayStartParams.num-gpus=2` → 2, group `resources.GPU=3` → 3의 우선순위를 확인했습니다. 이는 **하드웨어 GPU가 늘어난다는 의미가 아닙니다.** Kubernetes limit·device plugin·driver·Ray 논리 자원과 실제 가시 GPU를 일치시켜야 합니다.

GPU group의 minReplica, CPU/placement 요구 등도 규모에 영향을 줄 수 있으므로 “실행 대기 GPU task가 있을 때만 GPU Pod가 생긴다”고 단정하지 않습니다. CPU도 Ray의 논리 자원과 container 제한을 별도로 확인합니다.

## 오퍼레이터 설치와 업그레이드

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update kuberay
helm pull kuberay/kuberay-operator --version 1.7.0 --untar --untardir ./vendor
helm template kuberay-operator ./vendor/kuberay-operator \
  --namespace kuberay-system --include-crds > operator.rendered.yaml
```

렌더링 결과의 CRD, RBAC, namespace watch 범위와 feature gate를 검토합니다. 기본 chart는 leader election을 켜며 cluster 전체를 감시합니다. 범위를 제한하려면 `singleNamespaceInstall`, `watchNamespace`, 관련 RBAC 옵션을 함께 검토합니다.

실제 설치는 현재 context와 관리자 권한을 확인한 뒤 수행합니다.

```bash
helm upgrade --install kuberay-operator kuberay/kuberay-operator \
  --version 1.7.0 --namespace kuberay-system --create-namespace
kubectl rollout status deployment/kuberay-operator -n kuberay-system
```

Helm의 `crds/` 설치 방식은 **기존 CRD의 자동 upgrade/delete를 지원하지 않습니다.** Chart upgrade만으로 schema가 갱신됐다고 가정하지 말고, 저장된 CR·API version 호환성을 확인한 뒤 릴리스에 맞는 별도 CRD 갱신 절차를 수행합니다. CRD 삭제는 기존 custom resource 삭제로 이어질 수 있습니다.

## 최소 CPU 구성 예제

`ray-demo` namespace가 준비된 환경의 CPU 예제입니다. CRD schema를 검증했으며 실제 controller 실행·이미지 시작·autoscaling까지 확인한 결과는 아닙니다.

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: ray-cpu-demo
  namespace: ray-demo
spec:
  rayVersion: '2.58.0'
  enableInTreeAutoscaling: true
  autoscalerOptions:
    version: v2
    idleTimeoutSeconds: 60
  headGroupSpec:
    serviceType: ClusterIP
    rayStartParams:
      num-cpus: '0'
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.58.0-py312
            resources:
              requests:
                cpu: '1'
                memory: 2Gi
              limits:
                cpu: '1'
                memory: 2Gi
  workerGroupSpecs:
    - groupName: cpu
      replicas: 0
      minReplicas: 0
      maxReplicas: 2
      rayStartParams: {}
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.58.0-py312
              resources:
                requests:
                  cpu: '1'
                  memory: 2Gi
                limits:
                  cpu: '1'
                  memory: 2Gi
```

검증한 완전한 schema fixture는 head/worker에 `rayproject/ray:2.58.0-py312`와 CPU 1·memory 2 GiB request/limit을 사용했습니다. `rayVersion` 필드를 쓰는 것만으로 container image가 자동 업그레이드되지는 않습니다. Runtime·Python·image 호환성도 확인합니다.

Dashboard·Ray Client·job 제출 등의 진입점은 신뢰된 주체로 제한합니다. Token auth는 별도 설정이며 TLS나 모든 application endpoint의 접근 제어를 대신하지 않습니다. Secret 전달 방식은 조직 정책과 대조하고, 민감한 token을 공개 manifest·로그에 남기지 않습니다.

## 공식 근거

- [KubeRay 1.7.0 release](https://github.com/ray-project/kuberay/releases/tag/v1.7.0)
- [1.7.0 chart values](https://github.com/ray-project/kuberay/blob/v1.7.0/helm-chart/kuberay-operator/values.yaml)
- [Pod·자원 구성 코드](https://github.com/ray-project/kuberay/blob/v1.7.0/ray-operator/controllers/ray/common/pod.go)
- [Ray 2.58.0 autoscaler 설정 생성](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/autoscaler/_private/kuberay/autoscaling_config.py)
- [RayJob API](https://github.com/ray-project/kuberay/blob/v1.7.0/ray-operator/apis/ray/v1/rayjob_types.go)
- [RayService API](https://github.com/ray-project/kuberay/blob/v1.7.0/ray-operator/apis/ray/v1/rayservice_types.go)
- [Helm CRD 수명주기](https://helm.sh/docs/chart_best_practices/custom_resource_definitions/)

[다음: Train/Tune](03-ray-train-tune.md) · [메인 페이지](README.md) · [퀴즈](../../quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
