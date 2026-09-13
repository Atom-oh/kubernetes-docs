# Kube Resource Orchestrator (kro)

> **마지막 업데이트**: 2026년 9월 12일 · **기준 버전**: kro 0.9.4

## 개념과 적용 범위

kro의 공식 이름은 Kube Resource Orchestrator입니다. Kubernetes SIG Cloud Provider의 하위 프로젝트이며 ResourceGraphDefinition(RGD)으로 여러 Kubernetes 리소스의 입력 schema, 참조 관계와 상태를 정의합니다. RGD를 검증·컴파일한 뒤 생성한 CRD의 인스턴스를 동적으로 reconcile합니다.

RGD는 실행 중인 app 인스턴스가 아니라 API와 리소스 그래프의 정의입니다. 인스턴스 CR의 spec이 입력이고, spec.resources의 template이 Deployment·Service 같은 자원을 만듭니다. ACK 등 이미 설치된 CRD도 포함할 수 있지만 해당 controller의 역할이나 AWS IAM 권한을 kro가 대신 제공하지 않습니다.

YAML 안의 `${...}`는 CEL 표현식입니다. 예전 문서의 `.parent`, `.children`, childResources, resourceKind, statusMappings와 Go template 구문은 이 API의 예제가 아닙니다. 별도로 같은 app CRD를 손으로 생성해 RGD와 경쟁 관리하지 않습니다.

## Helm·Kustomize·Operator와 비교

| 도구 | 주된 역할과 경계 |
| --- | --- |
| Helm | Go template으로 chart를 렌더링하고 release 이력을 관리합니다. v2 chart dependency는 Chart.yaml에 선언합니다. |
| Kustomize | base와 patch로 manifest를 변환합니다. 자체 실행 중 controller는 아닙니다. |
| 사용자 정의 Operator | 서비스별 복구·migration·백업 같은 도메인 동작을 코드로 구현할 수 있습니다. |
| kro | CEL 참조를 분석해 리소스 그래프를 만들고 인스턴스를 reconcile합니다. 도메인별 DB 복구 알고리즘을 자동 생성하지 않습니다. |

Helm chart로 kro controller를 설치하고 GitOps로 RGD와 인스턴스를 관리할 수 있습니다. 도구들은 함께 사용할 수 있으며 Helm에서 kro로 옮긴다는 이유만으로 보안·복구·운영이 개선되는 것은 아닙니다. Kubernetes의 Deployment controller는 Helm으로 만든 Deployment도 계속 관리합니다.

## 설치와 권한

공식 저장소는 kubernetes-sigs/kro이며 과거 kro-run 경로는 redirect될 수 있습니다. 아래는 현재 OCI chart를 pin한 **오프라인 검사**입니다. 원문의 kro-project 다운로드 URL과 별도 kro CLI 설치 명령은 사용하지 않습니다. 이 release에 CLI 실행 파일은 배포되지 않으며 kubectl/Helm으로 조작합니다.

```bash
helm template kro oci://registry.k8s.io/kro/charts/kro \
  --version 0.9.4 --namespace kro-system \
  --set rbac.mode=aggregation --include-crds
```

실제 설치 전에는 지원 중인 Kubernetes 버전과 admission 정책, namespace, 기존 CRD·controller를 확인합니다. 예전 1.31~1.33 목록을 최신 지원 범위로 제시하지 않습니다. Helm upgrade는 crds/의 CRD를 자동 갱신하지 않으므로 0.9.4 release와 CRD 변경을 검토한 별도 절차가 필요합니다.

기본 rbac.mode=unrestricted는 광범위한 cluster 권한을 줍니다. 예제는 aggregation 모드를 렌더링했고, 이 모드에서도 CRD/RGD/GraphRevision·ConfigMap 등 기본 권한이 있습니다. app의 generated API와 자식 리소스에 대한 권한은 추가해야 합니다. 아래 ClusterRole은 이 예제의 타입을 허용하는 구성으로, cluster 전체에 해당 타입 권한을 줄 수 있으므로 신뢰된 platform 관리자가 RGD와 aggregation label을 관리해야 합니다.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kro:controller:reviewed-nginxapps
  labels:
    rbac.kro.run/aggregate-to-controller: "true"
rules:
  - apiGroups: [platform.example.com]
    resources: [nginxapps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [platform.example.com]
    resources: [nginxapps/status, nginxapps/finalizers]
    verbs: [get, update, patch]
  - apiGroups: [apps]
    resources: [deployments]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [services]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [networking.k8s.io]
    resources: [ingresses]
    verbs: [get, list, watch, create, update, patch, delete]
```

## 완전한 NginxApp 예제

저장소의 examples/platform/kro에 아래 RGD, 인스턴스와 RBAC 파일이 있습니다. ingress는 기본 비활성화입니다. 활성화하려면 승인된 IngressClass/controller, host DNS와 같은 namespace의 TLS Secret을 먼저 준비하세요. className=internal이라는 문자열만으로 내부 load balancer가 구성되지는 않습니다.

image는 기존 Helm 예제와 같은 nginx-unprivileged tag를 사용합니다. 비특권 UID와 읽기 전용 root, /tmp volume을 구성했지만 실제 image 실행은 검증하지 않았습니다. 운영 시 digest·아키텍처·정책을 확인합니다.

### ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: reviewed-nginxapps
spec:
  schema:
    apiVersion: v1alpha1
    group: platform.example.com
    kind: NginxApp
    scope: Namespaced
    spec:
      replicas: integer | default=2 minimum=1 maximum=5
      image: string | default="nginxinc/nginx-unprivileged:1.30.4-alpine"
      ingress:
        enabled: boolean | default=false
        className: string | default="internal"
        host: string | default="app.example.com"
        tlsSecret: string | default="app-tls"
    status:
      availableReplicas: ${deployment.status.availableReplicas}
      serviceIP: ${service.spec.clusterIP}
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
                      drop: [ALL]
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
    - id: service
      template:
        apiVersion: v1
        kind: Service
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          type: ClusterIP
          selector: ${deployment.spec.selector.matchLabels}
          ports:
            - name: http
              port: 8080
              targetPort: http
    - id: ingress
      includeWhen:
        - ${schema.spec.ingress.enabled}
      template:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: ${schema.metadata.name}
          namespace: ${schema.metadata.namespace}
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          ingressClassName: ${schema.spec.ingress.className}
          tls:
            - hosts:
                - ${schema.spec.ingress.host}
              secretName: ${schema.spec.ingress.tlsSecret}
          rules:
            - host: ${schema.spec.ingress.host}
              http:
                paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service:
                        name: ${service.metadata.name}
                        port:
                          number: 8080
```

### 인스턴스

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

schema.spec의 SimpleSchema는 타입·default·범위를 표현하며 kro가 generated CRD의 OpenAPI schema로 변환합니다. CEL의 schema.metadata/spec은 인스턴스를 가리키고 deployment/service는 resource id를 가리킵니다. status는 schema.status의 CEL로 정의합니다.

이 예제의 readyWhen은 Deployment 자신의 availableReplicas와 observedGeneration을 확인합니다. 준비 조건이 없으면 자원이 존재하고 참조가 해석되는 수준에서 다음 단계로 갈 수 있습니다. readyWhen은 자신의 resource id만 참조하는 Boolean 식이어야 합니다. app SLO·DB 연결 검사는 별도입니다.

Service가 Deployment selector를, Ingress가 Service 이름을 참조하므로 dependency가 생깁니다. 독립 자원은 같은 wave에서 처리할 수 있으며 순환 dependency는 허용하지 않습니다. includeWhen은 조건부 포함이며 조건이 바뀌면 자원이 추가되거나 제거될 수 있습니다. Secret 같은 기존 리소스를 externalRef로 읽으면 해당 자원의 소유권을 가져와 생성·삭제하는 것과 다릅니다.

### 적용 순서와 확인

실제 cluster에서 승인된 RBAC와 RGD를 적용한 뒤 RGD가 Active인지, 생성된 nginxapps.platform.example.com CRD가 Established인지 확인하고 인스턴스를 적용합니다. 단순 kubectl apply 성공을 graph 컴파일이나 app readiness 성공으로 해석하지 않습니다.

```bash
kubectl get rgd reviewed-nginxapps -o yaml
kubectl get graphrevisions \
  -l internal.kro.run/resource-graph-definition-name=reviewed-nginxapps
kubectl get crd nginxapps.platform.example.com -o yaml
kubectl get nginxapps.platform.example.com reviewed-web -n example -o yaml
kubectl get deployments,services,ingresses -n example \
  -l app.kubernetes.io/name=reviewed-web
```

## GraphRevision와 변경 관리

0.9.4는 RGD spec의 변경을 immutable GraphRevision으로 기록하고 컴파일합니다. latest revision이 실패하면 이전 revision으로 자동 fallback하지 않고 인스턴스 진행이 멈출 수 있습니다. GraphAccepted, GraphVerified, GraphRevisionsResolved 등의 조건과 오류 메시지를 확인하고 유효한 spec을 다시 적용합니다.

GraphRevision은 internal.kro.run API이므로 관찰·진단 목적으로 사용하고 구조에 의존하는 외부 도구를 만들 때 버전 안정성을 가정하지 않습니다. Git 이전 spec으로 돌아가도 새 revision에서 다시 검증되며, DB 데이터·외부 부작용까지 되돌리는 transaction은 아닙니다.

group, kind, apiVersion, scope는 해당 RGD에서 immutable 필드입니다. 같은 API의 호환성 변경과 신규 API 마이그레이션을 구분하고 기존 인스턴스·schema·저장 데이터를 검토하세요. conversion webhook이 자동 생성된다고 가정하지 않습니다.

## 삭제와 소유권

인스턴스 삭제 시 kro는 ApplySet inventory와 삭제 wave를 사용해 dependent부터 정리하고, 관리 자원이 사라질 때까지 finalizer를 유지합니다. child finalizer가 다음 wave를 막을 수 있습니다. externalRef는 읽기 전용 참조이며 kro가 삭제하지 않습니다.

모든 child가 즉시 garbage collection된다는 설명은 부정확합니다. ResourcesReady=Unknown/UnderDeletion 조건, inventory와 child finalizer를 조사하세요. controller를 제거하기 전에 instance/RGD/CRD·데이터의 정리 및 보존 계획을 세워야 합니다. CRD 삭제는 인스턴스 데이터에도 영향을 줍니다.

## 마이그레이션과 운영 패턴

Helm과 kro가 같은 object를 동시에 관리하지 않도록 이름·selector·소유권·field manager·GitOps controller를 먼저 확인합니다. 새 이름의 graph를 검증하고 traffic을 전환하는 방법 또는 검토된 소유권 이전 절차를 선택합니다. 기존 release를 단순 uninstall해서 StatefulSet/PVC/DB를 정리하는 방식으로 마이그레이션하지 않습니다.

여러 환경에는 동일한 API 계약과 검증된 이미지 digest를 사용하되 namespace, replicas, ingress와 정책은 별도 인스턴스로 관리합니다. ApplicationSet 같은 fleet 도구를 사용하려면 각 cluster에 kro/RGD/권한을 먼저 준비해야 합니다. kro가 임의 원격 cluster에 자동 접속하는 기능은 아닙니다.

DB·stateful app은 전용 DB Operator 또는 관리형 서비스의 backup, restore, failover, schema migration 기능이 필요합니다. kro의 리소스 조정만으로 데이터 복구가 구현되지는 않습니다. RGD 크기와 권한을 제한하고 재사용 단위를 나누며 필요한 status만 공개하세요. Secret 내용을 status·label·로그로 내보내지 않습니다.

## 검증 범위와 참고 자료

원문 본문 504줄·퀴즈 423줄씩, 16개 고유 code block과 각 언어 20개 문제 주제를 검토했습니다. kro 0.9.4 OCI chart의 aggregation 렌더링과 공식 RGD 구조를 확인했고, 해당 버전이 사용하는 cel-go 0.31.0으로 본문의 14개 고유 식을 실제 컴파일·평가했습니다. ingress on/off, 준비 replica 부족과 오래된 observedGeneration의 4가지 합성 사례가 통과했습니다.

이 검사는 dynamic 합성 입력을 사용하는 CEL 검사이며 kro 전체 graph compiler의 타입 추론, Kubernetes API discovery, generated CRD admission이나 실제 controller 실행을 검증한 것은 아닙니다. container·Ingress·TLS·DB·클러스터 리소스는 실행하지 않았습니다.

- [kro 0.9.4](https://github.com/kubernetes-sigs/kro/releases/tag/v0.9.4)
- [Versioned API and source](https://github.com/kubernetes-sigs/kro/tree/v0.9.4)
- [RGD schema](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/concepts/rgd/01-schema.md)
- [Access control](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/01-access-control.md)
- [Graph revisions](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/05-graph-revisions.md)
- [Instance deletion](https://github.com/kubernetes-sigs/kro/blob/v0.9.4/website/docs/docs/advanced/06-instance-deletion.md)

[kro 퀴즈](../quizzes/platform-engineering/03-kro-quiz.md)
