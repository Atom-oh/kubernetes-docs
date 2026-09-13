# Kube Resource Orchestrator (kro) 퀴즈

[kro](../../platform-engineering/03-kro.md)

kro 0.9.4 기준으로 원문의 20개 문제 주제를 유지했습니다.

## 1. kro의 핵심 개념은 무엇인가요?

<details>
<summary>정답 보기</summary>

RGD로 API schema와 리소스 그래프를 정의하고 CEL 참조에서 dependency를 추론하며 인스턴스를 reconcile합니다. 명령형 스크립트 실행기가 아닙니다.

</details>

## 2. 생성할 리소스 목록은 어느 필드에 정의하나요?

<details>
<summary>정답 보기</summary>

spec.resources입니다. 각 항목의 id와 template 또는 externalRef를 사용합니다. 예전 childResources는 현재 RGD 필드가 아닙니다.

</details>

## 3. Helm과 비교한 kro의 주요 역할은 무엇인가요?

<details>
<summary>정답 보기</summary>

리소스 참조 그래프와 인스턴스의 지속적 조정을 제공합니다. Helm은 chart 렌더링과 release 관리에 사용하며 두 도구를 함께 쓸 수 있습니다. 어느 하나가 모든 workload에 더 낫다는 뜻은 아닙니다.

</details>

## 4. 인스턴스 입력을 CEL에서 어떻게 참조하나요?

<details>
<summary>정답 보기</summary>

schema.spec 또는 schema.metadata를 사용합니다. 예를 들어 `${schema.spec.replicas}`입니다. .parent나 Go template 구문을 사용하지 않습니다.

</details>

## 5. 조건부 리소스 포함을 어떻게 설정하나요?

<details>
<summary>정답 보기</summary>

includeWhen의 Boolean CEL 목록을 사용합니다. 조건이 바뀌면 자원이 추가되거나 제거될 수 있으므로 stateful 자원에 사용할 때 lifecycle을 검토합니다.

</details>

## 6. 자식 리소스 상태를 어디에 투영하나요?

<details>
<summary>정답 보기</summary>

spec.schema.status에 CEL 식을 정의합니다. 예를 들어 availableReplicas에 `${deployment.status.availableReplicas}`를 사용합니다. statusMappings는 현재 필드가 아닙니다.

</details>

## 7. dependency와 준비 순서는 어떻게 정하나요?

<details>
<summary>정답 보기</summary>

다른 resource id를 참조하는 CEL에서 DAG를 추론합니다. readyWhen이 있으면 의존 자원은 해당 조건도 기다립니다. 순환 참조는 허용하지 않으며 YAML 나열 순서가 dependency를 대신하지 않습니다.

</details>

## 8. 인스턴스를 삭제하면 어떻게 되나요?

<details>
<summary>정답 보기</summary>

현재 kro는 ApplySet inventory와 삭제 wave로 dependent부터 정리하며 finalizer를 유지합니다. child finalizer가 진행을 막을 수 있습니다. externalRef 대상은 삭제하지 않습니다.

</details>

## 9. 누가 인스턴스 변경을 감시하나요?

<details>
<summary>정답 보기</summary>

kro의 동적 인스턴스 controller가 변경을 관찰하고 그래프를 조정합니다. RGD/GraphRevision의 검증·컴파일 상태가 인스턴스 진행에 영향을 줍니다.

</details>

## 10. kubectl apply는 어떤 역할을 하나요?

<details>
<summary>정답 보기</summary>

CR의 원하는 상태를 생성·갱신합니다. 그 뒤 controller가 reconcile하며, apply 성공은 graph 컴파일이나 app readiness 성공이 아닙니다. 외부 부작용의 transaction도 보장하지 않습니다.

</details>

## 11. RGD는 무엇인가요?

<details>
<summary>정답 보기</summary>

ResourceGraphDefinition입니다. 생성할 API의 schema와 관리 리소스·상태 관계를 정의하며, 앱 인스턴스 CR과 구분합니다.

</details>

## 12. Helm values에 대응하는 입력은 무엇인가요?

<details>
<summary>정답 보기</summary>

생성된 API의 인스턴스 spec입니다. SimpleSchema 타입·default·범위와 실제 template에서 참조하는 필드가 일치해야 합니다.

</details>

## 13. 형제 리소스를 어떻게 참조하나요?

<details>
<summary>정답 보기</summary>

resource id를 직접 사용합니다. `${deployment.spec.selector.matchLabels}` 또는 `${service.metadata.name}`처럼 참조하며 .children 경로는 사용하지 않습니다.

</details>

## 14. 관리 리소스 추적과 삭제 진단에서 무엇을 보나요?

<details>
<summary>정답 보기</summary>

현재 ApplySet inventory, owner metadata와 internal.kro.run/apply-order 삭제 wave를 확인합니다. 임의의 kro.run/owner annotation 하나가 전체 추적 계약이라고 가정하지 않습니다.

</details>

## 15. 입력 schema 검증은 어떻게 이루어지나요?

<details>
<summary>정답 보기</summary>

SimpleSchema를 generated CRD의 OpenAPI schema로 변환하고 Kubernetes가 인스턴스 입력을 검증합니다. RGD 구조 검사와 실제 graph compiler의 CEL 타입 검사, runtime 준비 상태는 별도 검증입니다.

</details>

## 16. 예제 NginxApp 인스턴스를 작성하세요.

<details>
<summary>정답 보기</summary>

먼저 관련 RGD가 Active이고 generated CRD가 Established여야 합니다. 아래 인스턴스는 ingress를 끕니다.

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

</details>

## 17. Deployment를 만드는 resource 항목을 작성하세요.

<details>
<summary>정답 보기</summary>

본문과 동일한 template입니다. readyWhen은 Deployment 자신만 참조하며 image·namespace·정책은 실제 환경에서 확인해야 합니다.

```yaml
resources:
- id: deployment
  readyWhen:
  - ${deployment.status.availableReplicas >= deployment.spec.replicas}
  - ${deployment.status.observedGeneration >= deployment.metadata.generation}
  template:
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: ${schema.metadata.name}
      namespace: ${schema.metadata.namespace}
      labels:
        app.kubernetes.io/name: ${schema.metadata.name}
    spec:
      replicas: ${schema.spec.replicas}
      selector:
        matchLabels:
          app.kubernetes.io/name: ${schema.metadata.name}
      template:
        metadata:
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 101
            runAsGroup: 101
            fsGroup: 101
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: web
            image: ${schema.spec.image}
            ports:
            - name: http
              containerPort: 8080
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            readinessProbe:
              httpGet:
                path: /
                port: http
            volumeMounts:
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: tmp
            emptyDir:
              sizeLimit: 64Mi
```

</details>

## 18. availableReplicas를 status에 노출하세요.

<details>
<summary>정답 보기</summary>

아래는 RGD spec.schema의 status 부분입니다. 값이 아직 없으면 해석을 기다릴 수 있으므로 app의 종합 건강 상태와 구분합니다.

```yaml
status:
  availableReplicas: ${deployment.status.availableReplicas}
  serviceIP: ${service.spec.clusterIP}
```

</details>

## 19. dev/staging/prod 전략을 설계하세요.

<details>
<summary>정답 보기</summary>

동일한 검증된 API 계약과 image digest를 사용하고 namespace, replica, ingress, 정책은 인스턴스별로 분리합니다. 다른 cluster에는 kro/RGD/권한을 먼저 배포하고 fleet 도구로 동기화합니다. 사용하지 않는 autoscaling 필드를 추가하는 것만으로 HPA가 생기지는 않습니다.

</details>

## 20. stateful app에서 Helm과 kro의 한계는 무엇인가요?

<details>
<summary>정답 보기</summary>

둘 다 DB backup·restore·failover·schema migration을 자동 완성하지 않습니다. 전용 Operator/관리형 서비스의 동작과 데이터 보존을 검증해야 합니다. Git spec 복원은 DB rollback이 아니며, 최신 GraphRevision 컴파일 실패 시 이전 revision으로 자동 fallback하지 않습니다.

</details>
