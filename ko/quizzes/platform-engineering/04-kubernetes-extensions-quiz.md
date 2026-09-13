# Kubernetes 확장 메커니즘 퀴즈

[Kubernetes extensions](../../platform-engineering/04-kubernetes-extensions.md)

원문의 20개 문제 주제를 현재 API·동작에 맞춰 검토했습니다.

## 1. CRD의 목적은 무엇인가요?

<details>
<summary>정답 보기</summary>

Kubernetes API에 사용자 리소스 타입과 입력 schema를 등록합니다. 자체로 workload 동작을 구현하지 않습니다.

</details>

## 2. reconciliation loop는 무엇을 하나요?

<details>
<summary>정답 보기</summary>

관찰된 상태와 원하는 상태의 차이를 조정합니다. 반복·중복 이벤트, 재시작과 conflict에도 일관되게 처리하고 상태가 같으면 불필요한 update를 줄입니다.

</details>

## 3. Operator의 핵심 구성과 한계는 무엇인가요?

<details>
<summary>정답 보기</summary>

사용자 API와 controller에 도메인 운영 지식을 구현하는 패턴입니다. CRD/controller를 만들었다는 이유만으로 안전한 backup·failover·upgrade가 완성되지는 않습니다.

</details>

## 4. mutating webhook은 무엇을 반환하나요?

<details>
<summary>정답 보기</summary>

AdmissionReview 응답으로 허용·거절과 선택적인 JSONPatch를 반환합니다. request UID와 version을 맞추며 patch byte는 Base64로 전달합니다.

</details>

## 5. Filter plugin의 역할은 무엇인가요?

<details>
<summary>정답 보기</summary>

Pod 조건을 충족하지 못하는 node를 후보에서 제외합니다. filter가 성공했다고 실제 binding이나 실행이 완료된 것은 아닙니다.

</details>

## 6. aggregation과 CRD는 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

CRD는 기존 API server의 사용자 리소스 저장·검증 기능을 사용합니다. aggregation은 별도 API server로 요청을 위임하므로 TLS·인증·인가·discovery·storage 운영이 필요합니다.

</details>

## 7. finalizer는 무엇을 보장하나요?

<details>
<summary>정답 보기</summary>

삭제 완료 전에 controller가 정리할 기회를 제공합니다. finalizer 문자열 자체가 정리 작업을 실행하지는 않으며, 원인 확인 없이 제거하면 외부 리소스를 남길 수 있습니다.

</details>

## 8. PostBind는 언제 실행되나요?

<details>
<summary>정답 보기</summary>

성공적인 binding 뒤의 정보성 단계입니다. 모든 작업 정리에 사용되는 보편적 오류 복구 hook이 아니며 Reserve 실패/취소에는 Unreserve 같은 해당 경로를 구현합니다.

</details>

## 9. 현재 Istio Pod별 주입 제어는 어디에 설정하나요?

<details>
<summary>정답 보기</summary>

Pod 또는 workload의 Pod template labels에 sidecar.istio.io/inject를 설정합니다. namespace의 istio-injection/revision label과 우선순위도 확인하며 이전 annotation을 새 기본값으로 쓰지 않습니다.

</details>

## 10. Score는 어떻게 사용되나요?

<details>
<summary>정답 보기</summary>

적합한 node의 점수를 정하고 NormalizeScore와 plugin weight를 반영해 결합합니다. 동률 선택과 실패 처리도 scheduler 동작의 일부입니다.

</details>

## 11. CRD의 schema와 required는 어디에 두나요?

<details>
<summary>정답 보기</summary>

spec.versions[].schema.openAPIV3Schema 아래에 정의합니다. 최상위 required: [spec]과 spec 내부 required: [image]는 서로 다른 조건입니다.

</details>

## 12. ownerReference는 무엇을 확인해야 하나요?

<details>
<summary>정답 보기</summary>

owner UID와 namespace/scope, 기존 controller 소유권을 확인합니다. GC는 propagation/finalizer 영향을 받으며 이름만 같다고 다른 workload를 가져오지 않습니다.

</details>

## 13. VAP와 validating webhook은 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

ValidatingAdmissionPolicy는 1.30부터 stable이며 API server 안에서 CEL을 평가합니다. webhook은 외부 호출과 TLS·가용성 관리가 필요합니다. VAP에는 적용 범위와 validationActions를 연결하는 binding도 필요합니다.

</details>

## 14. controller-runtime은 무엇을 제공하나요?

<details>
<summary>정답 보기</summary>

manager, client/cache, reconcile 구성과 leader election 등을 제공합니다. 사용자 API 타입·scheme·RBAC와 도메인 로직을 대신 만들어 주지는 않으며 library/Kubernetes Go module 버전을 맞춥니다.

</details>

## 15. conversion webhook의 역할은 무엇인가요?

<details>
<summary>정답 보기</summary>

같은 CRD의 API version 사이에서 표현을 변환합니다. serving/storage version, storedVersions와 기존 데이터의 의미 보존을 검토합니다. 모든 CRD가 conversion webhook을 필요로 하는 것은 아닙니다.

</details>

## 16. image가 필수이며 replica가 1~5인 WebApp CRD를 작성하세요.

<details>
<summary>정답 보기</summary>

아래 예제는 spec 자체도 필수로 지정하고 status/scale 경로를 분리합니다. controller가 실제 status.replicas와 selector를 채워야 합니다.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames: [wa]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [image]
              properties:
                replicas:
                  type: integer
                  default: 1
                  minimum: 1
                  maximum: 5
                image:
                  type: string
                  minLength: 1
                port:
                  type: integer
                  default: 8080
                  minimum: 1
                  maximum: 65535
            status:
              type: object
              properties:
                replicas:
                  type: integer
                availableReplicas:
                  type: integer
                selector:
                  type: string
                observedGeneration:
                  type: integer
                  format: int64
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
          labelSelectorPath: .status.selector
```

</details>

## 17. production namespace의 Deployment 검증 webhook을 어떻게 제한하나요?

<details>
<summary>정답 보기</summary>

rules를 apps/v1 deployments의 CREATE/UPDATE로 제한하고 namespaceSelector에 kubernetes.io/metadata.name: production을 사용합니다. 실제 validating server/Service/path, CA bundle, failurePolicy, timeoutSeconds, sideEffects와 admissionReviewVersions를 설정합니다. 본문의 /mutate handler는 Deployment validator가 아니므로 그 경로를 재사용하지 않습니다. replica 범위만 필요하면 본문의 VAP+binding 예제를 사용하고 `deployments`와 `deployments/scale`을 모두 매칭해 HPA 및 `kubectl scale` 갱신도 제한을 검사하도록 합니다.

</details>

## 18. 안전한 reconcile 순서를 설명하세요.

<details>
<summary>정답 보기</summary>

NotFound를 정상 종료하고 삭제 중이면 idempotent cleanup 후 자신의 finalizer만 제거합니다. 외부 자원을 만들기 전 finalizer를 저장하고, 기존 child 소유권을 확인한 뒤 관리 필드만 조정합니다. conflict를 재시도하고 관찰한 상태가 바뀔 때 status를 patch합니다. 의사코드를 완성된 실행 controller로 표시하지 않습니다.

</details>

## 19. 분산 DB Operator를 설계할 때 무엇이 필요한가요?

<details>
<summary>정답 보기</summary>

API/schema와 workload 생성 외에 primary fencing, quorum, replica 동기화, backup/WAL 복구 시험, storage lifecycle, migration 호환성과 실패 상태를 설계합니다. Service/StatefulSet/CronJob을 생성하는 것만으로 데이터 안전성이 검증되지 않습니다.

</details>

## 20. custom scheduler 구현과 검증 절차는 무엇인가요?

<details>
<summary>정답 보기</summary>

정확한 Kubernetes minor의 framework interface로 plugin을 compile·register한 binary를 만듭니다. profile plugin 이름과 Pod schedulerName을 맞추고 Filter/Score 및 Reserve/Unreserve/Permit/binding 실패를 검증합니다. YAML만 추가해서 plugin을 설치할 수 없으며 단순 zone 요구라면 node affinity를 먼저 검토합니다.

</details>
