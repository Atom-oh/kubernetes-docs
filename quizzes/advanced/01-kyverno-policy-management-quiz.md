# Kyverno를 사용한 정책 관리 퀴즈

이 퀴즈는 Kubernetes에서 Kyverno를 사용한 정책 관리에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kyverno는 무엇인가요?

A. Kubernetes 네이티브 정책 엔진  
B. 컨테이너 이미지 스캐너  
C. 클러스터 모니터링 도구  
D. 서비스 메시 구현체  

<details>
<summary>정답 및 설명</summary>

**정답: A. Kubernetes 네이티브 정책 엔진**

**설명:**
Kyverno는 Kubernetes 네이티브 정책 엔진으로, YAML 또는 JSON으로 작성된 정책을 사용하여 Kubernetes 리소스를 검증, 변경 및 생성할 수 있습니다. Kyverno는 Kubernetes 자체 API와 YAML 구문을 사용하므로 새로운 언어나 도구를 배울 필요 없이 정책을 정의하고 관리할 수 있습니다.

**주요 특징:**
1. **네이티브 Kubernetes 통합**: Kubernetes API와 직접 통합되어 작동합니다.
2. **선언적 정책 정의**: YAML 기반의 선언적 정책을 사용합니다.
3. **다양한 정책 유형 지원**: 검증(Validate), 변경(Mutate), 생성(Generate), 정리(Cleanup) 정책을 지원합니다.
4. **이미지 검증**: 컨테이너 이미지 보안 검증 기능을 제공합니다.
5. **감사 및 보고**: 정책 준수 여부에 대한 감사 및 보고 기능을 제공합니다.

**예시 정책:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
```

이 정책은 모든 Pod가 'team' 레이블을 가지도록 요구합니다.

**다른 옵션들의 문제점:**
- B. 컨테이너 이미지 스캐너: Kyverno는 이미지 검증 기능을 제공하지만, 주요 목적은 정책 관리입니다. 전문적인 이미지 스캐너로는 Trivy, Clair 등이 있습니다.
- C. 클러스터 모니터링 도구: Kyverno는 모니터링 도구가 아닙니다. Prometheus, Grafana 등이 모니터링 도구에 해당합니다.
- D. 서비스 메시 구현체: Kyverno는 서비스 메시가 아닙니다. Istio, Linkerd 등이 서비스 메시 구현체에 해당합니다.
</details>

### 2. Kyverno에서 지원하는 정책 유형이 아닌 것은 무엇인가요?

A. Validate  
B. Mutate  
C. Generate  
D. Authenticate  

<details>
<summary>정답 및 설명</summary>

**정답: D. Authenticate**

**설명:**
Kyverno는 다음과 같은 정책 유형을 지원합니다:

1. **Validate(검증)**: 리소스가 특정 조건을 충족하는지 검증합니다.
2. **Mutate(변경)**: 리소스를 자동으로 수정합니다.
3. **Generate(생성)**: 다른 리소스가 생성될 때 추가 리소스를 자동으로 생성합니다.
4. **Verify Images(이미지 검증)**: 컨테이너 이미지의 서명을 검증합니다.
5. **Cleanup(정리)**: 특정 조건에 따라 리소스를 자동으로 삭제합니다.

Kyverno는 인증(Authentication) 정책 유형을 직접 지원하지 않습니다. Kubernetes의 인증은 일반적으로 API 서버 수준에서 처리되며, RBAC(Role-Based Access Control), OIDC(OpenID Connect), 서비스 계정 등의 메커니즘을 통해 관리됩니다.

**각 정책 유형의 예시:**

1. **Validate 정책 예시**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits are required"
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

2. **Mutate 정책 예시**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-labels
spec:
  rules:
  - name: add-environment-label
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchStrategicMerge:
        metadata:
          labels:
            environment: "{{request.object.metadata.namespace}}"
```

3. **Generate 정책 예시**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

4. **Verify Images 정책 예시**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: enforce
  rules:
  - name: check-image-signatures
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - image: "docker.io/library/*"
      repository: "docker.io/library/*"
      key: |-
        -----BEGIN PUBLIC KEY-----
        MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8xOUetsCa8AKa9F1hx3gUw1RcyZg
        rjMqwNZcDzDv3PpFtpSdwGzA1GRk7XBqDJJQa9Jekky0yvEUDjtwLFp7aw==
        -----END PUBLIC KEY-----
```

5. **Cleanup 정책 예시**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: cleanup-old-pods
spec:
  rules:
  - name: cleanup-completed-pods
    match:
      resources:
        kinds:
        - Pod
    preconditions:
      all:
      - key: "{{request.object.status.phase}}"
        operator: In
        value: ["Succeeded", "Failed"]
    cleanup:
      ttl: "24h"
```

**다른 옵션들의 설명:**
- A. Validate: Kyverno가 지원하는 정책 유형으로, 리소스가 특정 조건을 충족하는지 검증합니다.
- B. Mutate: Kyverno가 지원하는 정책 유형으로, 리소스를 자동으로 수정합니다.
- C. Generate: Kyverno가 지원하는 정책 유형으로, 다른 리소스가 생성될 때 추가 리소스를 자동으로 생성합니다.
</details>
### 3. Kyverno 정책에서 `validationFailureAction: enforce`의 의미는 무엇인가요?

A. 정책 위반 시 경고만 생성  
B. 정책 위반 시 리소스 생성 또는 업데이트 차단  
C. 정책 위반 시 자동으로 리소스 수정  
D. 정책 위반 시 리소스 삭제  

<details>
<summary>정답 및 설명</summary>

**정답: B. 정책 위반 시 리소스 생성 또는 업데이트 차단**

**설명:**
Kyverno 정책에서 `validationFailureAction: enforce`는 정책 위반 시 리소스 생성 또는 업데이트를 차단하는 설정입니다. 이 설정이 적용된 정책은 정책 조건을 충족하지 않는 리소스의 생성이나 수정을 거부하며, 사용자에게 정책 위반 메시지를 반환합니다.

`validationFailureAction`에는 두 가지 가능한 값이 있습니다:
1. **enforce**: 정책 위반 시 리소스 생성 또는 업데이트를 차단합니다.
2. **audit**: 정책 위반 시 리소스 생성이나 업데이트를 허용하지만, 위반 사항을 로그에 기록합니다. 이는 정책을 테스트하거나 현재 상태를 감사하는 데 유용합니다.

**예시 정책:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-probes
spec:
  validationFailureAction: enforce  # 정책 위반 시 리소스 생성/업데이트 차단
  rules:
  - name: check-readiness-probe
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Readiness probe is required"
      pattern:
        spec:
          containers:
          - readinessProbe:
              {}
```

이 정책은 모든 Pod의 컨테이너에 readinessProbe가 구성되어 있는지 확인하고, 그렇지 않은 경우 Pod 생성을 차단합니다.

**정책 적용 방법:**
```bash
# 정책 적용
kubectl apply -f require-probes.yaml

# readinessProbe가 없는 Pod 생성 시도
kubectl apply -f pod-without-probe.yaml
# 결과: Error from server: error when creating "pod-without-probe.yaml": admission webhook "validate.kyverno.svc" denied the request: 
# resource Pod/default/nginx was blocked due to the following policies: require-probes: check-readiness-probe: Readiness probe is required
```

**다른 옵션들의 문제점:**
- A. 정책 위반 시 경고만 생성: 이는 `validationFailureAction: audit`의 동작입니다.
- C. 정책 위반 시 자동으로 리소스 수정: 이는 mutate 정책의 동작이며, validationFailureAction과는 관련이 없습니다.
- D. 정책 위반 시 리소스 삭제: Kyverno는 정책 위반 시 기존 리소스를 자동으로 삭제하지 않습니다. cleanup 정책은 특정 조건에 따라 리소스를 삭제할 수 있지만, validationFailureAction과는 다른 메커니즘입니다.
</details>

### 4. Kyverno에서 정책을 적용할 리소스를 선택하는 데 사용되는 필드는 무엇인가요?

A. selector  
B. match  
C. target  
D. apply  

<details>
<summary>정답 및 설명</summary>

**정답: B. match**

**설명:**
Kyverno에서 정책을 적용할 리소스를 선택하는 데 사용되는 필드는 `match`입니다. 이 필드는 정책 규칙이 적용될 리소스의 종류, 이름, 네임스페이스, 레이블 등을 지정하는 데 사용됩니다.

`match` 필드는 다음과 같은 하위 필드를 포함할 수 있습니다:
1. **resources**: 리소스 종류, 이름, 네임스페이스 등을 지정합니다.
2. **subjects**: 정책이 적용될 사용자, 그룹, 서비스 계정을 지정합니다.
3. **roles**: 정책이 적용될 역할을 지정합니다.
4. **clusterRoles**: 정책이 적용될 클러스터 역할을 지정합니다.

또한 `exclude` 필드를 사용하여 특정 리소스를 정책 적용에서 제외할 수 있습니다.

**예시 정책:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels-for-deployments
spec:
  validationFailureAction: enforce
  rules:
  - name: check-required-labels
    match:
      resources:
        kinds:
        - Deployment
        namespaces:
        - "production"
        - "staging"
        selector:
          matchLabels:
            app.kubernetes.io/managed-by: kustomize
    validate:
      message: "Required labels are missing"
      pattern:
        metadata:
          labels:
            app.kubernetes.io/name: "?*"
            app.kubernetes.io/version: "?*"
            app.kubernetes.io/component: "?*"
```

이 정책은 'production'과 'staging' 네임스페이스에 있는 Deployment 중 'app.kubernetes.io/managed-by: kustomize' 레이블이 있는 리소스에만 적용됩니다.

**복잡한 매칭 예시:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: complex-matching-policy
spec:
  validationFailureAction: enforce
  rules:
  - name: complex-match-rule
    match:
      resources:
        kinds:
        - Deployment
        - StatefulSet
        namespaces:
        - "production"
        - "staging"
        selector:
          matchLabels:
            tier: "frontend"
      subjects:
      - kind: User
        name: "admin@example.com"
      - kind: Group
        name: "system:masters"
    exclude:
      resources:
        namespaces:
        - "kube-system"
        names:
        - "critical-deployment"
    validate:
      message: "Policy validation failed"
      pattern:
        spec:
          template:
            spec:
              containers:
              - securityContext:
                  runAsNonRoot: true
```

이 정책은 'production'과 'staging' 네임스페이스에 있는 Deployment와 StatefulSet 중 'tier: frontend' 레이블이 있는 리소스에 적용되며, 'admin@example.com' 사용자나 'system:masters' 그룹이 생성하거나 수정하는 경우에만 적용됩니다. 또한 'kube-system' 네임스페이스의 리소스와 'critical-deployment'라는 이름의 리소스는 제외됩니다.

**다른 옵션들의 문제점:**
- A. selector: Kyverno에서는 `match.resources.selector`와 같이 하위 필드로 사용되지만, 최상위 필드는 아닙니다.
- C. target: Kyverno 정책에서 사용되지 않는 필드입니다.
- D. apply: Kyverno 정책에서 사용되지 않는 필드입니다.
</details>

### 5. Kyverno에서 정책 위반 시 자동으로 리소스를 수정하는 정책 유형은 무엇인가요?

A. Validate  
B. Mutate  
C. Generate  
D. Verify  

<details>
<summary>정답 및 설명</summary>

**정답: B. Mutate**

**설명:**
Kyverno에서 정책 위반 시 자동으로 리소스를 수정하는 정책 유형은 `Mutate`입니다. Mutate 정책은 리소스가 생성되거나 업데이트될 때 자동으로 리소스를 수정하여 정책 요구 사항을 충족시킵니다.

Mutate 정책은 다음과 같은 방법으로 리소스를 수정할 수 있습니다:
1. **patchStrategicMerge**: 전략적 병합 패치를 사용하여 리소스를 수정합니다.
2. **patchesJson6902**: JSON 패치(RFC 6902)를 사용하여 리소스를 수정합니다.
3. **overlay**: (구버전) patchStrategicMerge와 동일한 기능을 제공하는 레거시 필드입니다.

**예시 정책:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-resources
spec:
  rules:
  - name: add-default-cpu-memory
    match:
      resources:
        kinds:
        - Deployment
    mutate:
      patchStrategicMerge:
        spec:
          template:
            spec:
              containers:
              - (name): "*"
                resources:
                  limits:
                    memory: "{{ if hasKey .object.spec.template.spec.containers[0].resources.limits \"memory\" }}{{ .object.spec.template.spec.containers[0].resources.limits.memory }}{{ else }}512Mi{{ end }}"
                    cpu: "{{ if hasKey .object.spec.template.spec.containers[0].resources.limits \"cpu\" }}{{ .object.spec.template.spec.containers[0].resources.limits.cpu }}{{ else }}500m{{ end }}"
                  requests:
                    memory: "{{ if hasKey .object.spec.template.spec.containers[0].resources.requests \"memory\" }}{{ .object.spec.template.spec.containers[0].resources.requests.memory }}{{ else }}256Mi{{ end }}"
                    cpu: "{{ if hasKey .object.spec.template.spec.containers[0].resources.requests \"cpu\" }}{{ .object.spec.template.spec.containers[0].resources.requests.cpu }}{{ else }}250m{{ end }}"
```

이 정책은 Deployment 리소스가 생성되거나 업데이트될 때 컨테이너에 리소스 제한과 요청이 설정되어 있지 않으면 기본값을 추가합니다.

**JSON 패치를 사용한 예시:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-labels-json-patch
spec:
  rules:
  - name: add-labels
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchesJson6902: |-
        - op: add
          path: /metadata/labels/app.kubernetes.io~1managed-by
          value: kyverno
        - op: add
          path: /metadata/labels/environment
          value: "{{ request.object.metadata.namespace }}"
```

이 정책은 JSON 패치를 사용하여 Pod에 레이블을 추가합니다.

**Mutate 정책의 적용 방법:**
```bash
# 정책 적용
kubectl apply -f add-default-resources.yaml

# 리소스 제한이 없는 Deployment 생성
kubectl apply -f deployment-without-resources.yaml

# 생성된 Deployment 확인
kubectl get deployment my-deployment -o yaml
# 결과: 리소스 제한과 요청이 자동으로 추가됨
```

**다른 옵션들의 문제점:**
- A. Validate: 리소스가 정책 조건을 충족하는지 검증만 하고, 수정하지는 않습니다.
- C. Generate: 다른 리소스가 생성될 때 추가 리소스를 생성하지만, 기존 리소스를 수정하지는 않습니다.
- D. Verify: 컨테이너 이미지의 서명을 검증하는 정책 유형으로, 리소스를 수정하지 않습니다.
</details>
### 6. Kyverno의 Generate 정책은 어떤 상황에서 유용한가요?

A. 리소스 생성 시 자동으로 관련 리소스 생성  
B. 리소스 검증 시 자동으로 오류 메시지 생성  
C. 리소스 삭제 시 자동으로 백업 생성  
D. 리소스 업데이트 시 자동으로 이전 버전 생성  

<details>
<summary>정답 및 설명</summary>

**정답: A. 리소스 생성 시 자동으로 관련 리소스 생성**

**설명:**
Kyverno의 Generate 정책은 특정 리소스가 생성될 때 자동으로 관련 리소스를 생성하는 데 유용합니다. 이 정책 유형은 리소스 간의 종속성을 관리하고, 표준 구성을 자동화하며, 일관된 환경을 유지하는 데 도움이 됩니다.

Generate 정책의 주요 사용 사례:
1. **네임스페이스 생성 시 기본 리소스 생성**: 네임스페이스가 생성될 때 NetworkPolicy, ResourceQuota, LimitRange 등의 리소스를 자동으로 생성합니다.
2. **애플리케이션 배포 시 관련 리소스 생성**: Deployment가 생성될 때 관련 Service, ConfigMap, Secret 등을 자동으로 생성합니다.
3. **표준 구성 자동화**: 특정 유형의 리소스가 생성될 때 표준 구성을 적용한 추가 리소스를 생성합니다.
4. **멀티 테넌시 환경 관리**: 새 테넌트를 위한 네임스페이스가 생성될 때 필요한 모든 리소스를 자동으로 생성합니다.

**예시 정책:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-default-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    exclude:
      resources:
        namespaces:
        - "kube-system"
        - "kube-public"
        - "kube-node-lease"
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

이 정책은 새 네임스페이스가 생성될 때(kube-system, kube-public, kube-node-lease 제외) 해당 네임스페이스에 기본 NetworkPolicy를 자동으로 생성합니다. 이 NetworkPolicy는 모든 인그레스 및 이그레스 트래픽을 차단합니다.

**synchronize 필드**:
- `synchronize: true`: 생성된 리소스를 소스 리소스와 동기화합니다. 소스 리소스가 변경되거나 삭제되면 생성된 리소스도 그에 따라 업데이트되거나 삭제됩니다.
- `synchronize: false`: 생성된 리소스는 소스 리소스와 독립적으로 존재합니다.

**클론 정책 예시:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: clone-secrets-across-namespaces
spec:
  rules:
  - name: clone-docker-registry-secret
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: Secret
      name: docker-registry
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      clone:
        namespace: default
        name: docker-registry
```

이 정책은 새 네임스페이스가 생성될 때 'default' 네임스페이스의 'docker-registry' Secret을 새 네임스페이스로 복제합니다.

**다른 옵션들의 문제점:**
- B. 리소스 검증 시 자동으로 오류 메시지 생성: 이는 Validate 정책의 기능입니다.
- C. 리소스 삭제 시 자동으로 백업 생성: Kyverno는 현재 리소스 삭제 시 자동 백업 기능을 기본적으로 제공하지 않습니다.
- D. 리소스 업데이트 시 자동으로 이전 버전 생성: 이는 Kubernetes의 리소스 버전 관리 메커니즘과 관련이 있으며, Kyverno의 Generate 정책과는 관련이 없습니다.
</details>

### 7. Kyverno에서 컨테이너 이미지 서명을 검증하는 정책 유형은 무엇인가요?

A. ImagePolicy  
B. VerifyImages  
C. SignaturePolicy  
D. ImageVerification  

<details>
<summary>정답 및 설명</summary>

**정답: B. VerifyImages**

**설명:**
Kyverno에서 컨테이너 이미지 서명을 검증하는 정책 유형은 `VerifyImages`입니다. 이 정책 유형은 컨테이너 이미지가 신뢰할 수 있는 소스에서 왔는지 확인하고, 이미지가 변조되지 않았는지 검증하는 데 사용됩니다.

VerifyImages 정책은 다음과 같은 기능을 제공합니다:
1. **이미지 서명 검증**: 디지털 서명을 사용하여 이미지의 무결성과 출처를 검증합니다.
2. **이미지 레지스트리 제한**: 특정 레지스트리에서만 이미지를 가져오도록 제한합니다.
3. **이미지 태그 제한**: 특정 태그(예: latest 태그 사용 금지)를 제한합니다.
4. **이미지 다이제스트 검증**: 이미지 다이제스트를 검증하여 정확한 이미지 버전을 사용하도록 합니다.

**예시 정책:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: enforce
  rules:
  - name: verify-signatures
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - image: "docker.io/library/*"
      repository: "docker.io/library/*"
      key: |-
        -----BEGIN PUBLIC KEY-----
        MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8xOUetsCa8AKa9F1hx3gUw1RcyZg
        rjMqwNZcDzDv3PpFtpSdwGzA1GRk7XBqDJJQa9Jekky0yvEUDjtwLFp7aw==
        -----END PUBLIC KEY-----
    - image: "ghcr.io/my-org/*"
      repository: "ghcr.io/my-org/*"
      roots: |-
        -----BEGIN CERTIFICATE-----
        MIICmTCCAj+gAwIBAgIUYzA4YTU5YjQ2OTk1MjNmMDI2OTVkMGYwDQYJKoZIhvcN
        AQELBQAwXDELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMRYwFAYDVQQHDA1TYW4g
        RnJhbmNpc2NvMQ8wDQYDVQQKDAZNeU9yZzEXMBUGA1UEAwwOY2EubXlvcmcubG9j
        YWwwHhcNMjMwNzIwMDAwMDAwWhcNMjQwNzE5MDAwMDAwWjBcMQswCQYDVQQGEwJV
        UzELMAkGA1UECAwCQ0ExFjAUBgNVBAcMDVNhbiBGcmFuY2lzY28xDzANBgNVBAoM
        Bk15T3JnMRcwFQYDVQQDDA5jYS5teW9yZy5sb2NhbDCBnzANBgkqhkiG9w0BAQEF
        AAOBjQAwgYkCgYEA1Jcpv/Gj0M3vaJQY4dLQJA9ZEMVCfOUzAFAgxm0DKJQSiQ+6
        HuQFTJjHnOJwYwKSAEGYe4JUg/fMUJMKl9BM7A9gjXKe0v8JMSyYGHVqTiPZ2RuW
        x7tO5Nh5jLz3GQYmZl0m7CRReY2zt9OUdRz2LR5xMPHitpy7aLGvGSsIZVECAwEA
        AaN7MHkwHQYDVR0OBBYEFPgVXUQGbNrGkFmXQkCXYvs8HzIIMB8GA1UdIwQYMBaA
        FPgVXUQGbNrGkFmXQkCXYvs8HzIIMA8GA1UdEwEB/wQFMAMBAf8wCwYDVR0PBAQD
        AgEGMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjANBgkqhkiG9w0BAQsF
        AAOBgQBB3TVGvZXKpZSzqPOzQzUNnCMzMEf1I7Qx9mKIqTKSZLqHYBDxHpQRQQNy
        aBBtMBgUn3KkZY8QdRUKj8Sw0PN+GV4bCXGwCJeRNZWO1FdaIVoUYKKWMPLYUUrJ
        UpZXfNQO8XUjIEqBK8RGn3MwYYwRF+OjDHGvpOf6hk0XPHGjlQ==
        -----END CERTIFICATE-----
```

이 정책은 두 가지 이미지 소스에 대한 서명을 검증합니다:
1. docker.io/library/* 이미지는 지정된 공개 키를 사용하여 검증합니다.
2. ghcr.io/my-org/* 이미지는 지정된 인증서를 사용하여 검증합니다.

**이미지 서명 도구:**
Kyverno는 다양한 이미지 서명 도구와 통합됩니다:
1. **Cosign**: Sigstore 프로젝트의 일부로, 컨테이너 이미지 서명 및 검증을 위한 도구입니다.
2. **Notary**: Docker의 컨텐츠 신뢰 프레임워크입니다.
3. **GnuPG (GPG)**: 오픈 소스 암호화 도구입니다.

**Cosign을 사용한 이미지 서명 및 검증 예시:**
```bash
# 키 쌍 생성
cosign generate-key-pair

# 이미지 서명
cosign sign --key cosign.key my-registry.io/my-image:tag

# Kyverno 정책에서 사용할 공개 키 추출
cat cosign.pub
```

**다른 옵션들의 문제점:**
- A. ImagePolicy: Kyverno에서 사용되지 않는 정책 유형입니다.
- C. SignaturePolicy: Kyverno에서 사용되지 않는 정책 유형입니다.
- D. ImageVerification: Kyverno에서 사용되지 않는 정책 유형입니다.
</details>

### 8. Kyverno 정책에서 `background: false` 설정의 의미는 무엇인가요?

A. 정책이 백그라운드에서 실행되지 않음  
B. 정책이 기존 리소스에 적용되지 않음  
C. 정책이 클러스터 백그라운드 작업에 영향을 주지 않음  
D. 정책이 백그라운드 프로세스에 의해 생성된 리소스에 적용되지 않음  

<details>
<summary>정답 및 설명</summary>

**정답: B. 정책이 기존 리소스에 적용되지 않음**

**설명:**
Kyverno 정책에서 `background: false` 설정은 정책이 기존 리소스에 적용되지 않고, 새로 생성되거나 업데이트되는 리소스에만 적용됨을 의미합니다. 기본값은 `background: true`로, 이 경우 정책은 기존 리소스를 포함한 모든 리소스에 적용됩니다.

`background` 설정의 주요 특징:
1. **기존 리소스 검사**: `background: true`일 때, Kyverno는 주기적으로 클러스터의 기존 리소스를 스캔하여 정책 준수 여부를 확인합니다.
2. **리소스 부하**: 대규모 클러스터에서 많은 리소스를 검사하는 것은 상당한 부하를 발생시킬 수 있으므로, 필요한 경우에만 `background: true`를 사용하는 것이 좋습니다.
3. **감사 보고서**: 백그라운드 검사 결과는 PolicyReport 및 ClusterPolicyReport CRD에 기록됩니다.
4. **적용 범위**: `background: false`일 때도 정책은 여전히 Admission Controller로 작동하여 새로 생성되거나 업데이트되는 리소스에는 적용됩니다.

**예시 정책:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  background: false  # 기존 리소스에는 적용되지 않음
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
```

이 정책은 새로 생성되거나 업데이트되는 Pod에만 적용되며, 기존 Pod는 검사하지 않습니다.

**백그라운드 검사가 필요한 경우:**
1. **규정 준수 감사**: 클러스터의 모든 리소스가 정책을 준수하는지 정기적으로 확인해야 하는 경우
2. **보안 정책 적용**: 보안 취약점을 지속적으로 모니터링하고 보고해야 하는 경우
3. **구성 드리프트 감지**: 시간이 지남에 따라 리소스 구성이 정책에서 벗어나는지 감지해야 하는 경우

**백그라운드 검사가 필요하지 않은 경우:**
1. **성능 최적화**: 대규모 클러스터에서 리소스 사용량을 최소화해야 하는 경우
2. **새 리소스만 관리**: 기존 리소스는 그대로 두고 새 리소스만 정책을 준수하도록 하려는 경우
3. **점진적 정책 도입**: 기존 워크로드에 영향을 주지 않고 새 워크로드에만 정책을 적용하려는 경우

**다른 옵션들의 문제점:**
- A. 정책이 백그라운드에서 실행되지 않음: 이는 `background` 설정의 의미를 잘못 해석한 것입니다. 모든 Kyverno 정책은 Admission Controller로 작동합니다.
- C. 정책이 클러스터 백그라운드 작업에 영향을 주지 않음: 이는 `background` 설정과 관련이 없습니다.
- D. 정책이 백그라운드 프로세스에 의해 생성된 리소스에 적용되지 않음: 이는 `background` 설정과 관련이 없습니다. 리소스를 생성한 프로세스와 관계없이 정책은 적용됩니다.
</details>
### 9. Kyverno에서 정책 위반 보고서를 생성하는 데 사용되는 리소스는 무엇인가요?

A. PolicyViolation  
B. PolicyReport  
C. ComplianceReport  
D. AuditReport  

<details>
<summary>정답 및 설명</summary>

**정답: B. PolicyReport**

**설명:**
Kyverno에서 정책 위반 보고서를 생성하는 데 사용되는 리소스는 `PolicyReport`와 `ClusterPolicyReport`입니다. 이러한 리소스는 정책 검사 결과를 저장하고 보고하는 데 사용됩니다.

PolicyReport와 ClusterPolicyReport의 주요 특징:
1. **범위**:
   - `PolicyReport`: 특정 네임스페이스 내의 리소스에 대한 정책 검사 결과를 보고합니다.
   - `ClusterPolicyReport`: 클러스터 수준의 리소스에 대한 정책 검사 결과를 보고합니다.

2. **생성 방법**:
   - 백그라운드 스캔: `background: true`로 설정된 정책은 주기적으로 리소스를 스캔하고 결과를 보고서에 기록합니다.
   - Admission 검사: 리소스 생성 또는 업데이트 시 수행된 정책 검사 결과도 보고서에 기록됩니다.

3. **보고서 내용**:
   - 정책 이름
   - 검사된 리소스
   - 결과(pass, fail, warn, error, skip)
   - 메시지
   - 심각도
   - 카테고리
   - 타임스탬프

**예시 PolicyReport:**
```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: polr-ns-default
  namespace: default
summary:
  pass: 7
  fail: 3
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-labels
  rule: check-team-label
  resource:
    kind: Pod
    name: nginx
    namespace: default
  status: fail
  message: "label 'team' is required"
  severity: medium
  category: Best Practices
  timestamp:
    created: "2023-07-20T10:15:30Z"
- policy: require-probes
  rule: check-readiness-probe
  resource:
    kind: Pod
    name: nginx
    namespace: default
  status: pass
  timestamp:
    created: "2023-07-20T10:15:30Z"
```

**보고서 조회 방법:**
```bash
# 네임스페이스 정책 보고서 조회
kubectl get policyreport -n default

# 클러스터 정책 보고서 조회
kubectl get clusterpolicyreport

# 특정 보고서 세부 정보 조회
kubectl describe policyreport polr-ns-default -n default
```

**정책 보고서 통합:**
Kyverno의 정책 보고서는 Kubernetes Policy Working Group에서 정의한 PolicyReport CRD 사양을 따릅니다. 이를 통해 다양한 정책 엔진(Kyverno, OPA Gatekeeper 등)의 결과를 일관된 형식으로 보고할 수 있습니다.

**보고서 활용 방법:**
1. **규정 준수 모니터링**: 클러스터의 정책 준수 상태를 지속적으로 모니터링합니다.
2. **감사 증거**: 규정 준수 감사에 필요한 증거를 제공합니다.
3. **문제 해결**: 정책 위반 사항을 식별하고 해결하는 데 도움이 됩니다.
4. **추세 분석**: 시간에 따른 정책 준수 추세를 분석합니다.

**다른 옵션들의 문제점:**
- A. PolicyViolation: Kyverno에서 사용되지 않는 리소스 유형입니다.
- C. ComplianceReport: Kyverno에서 사용되지 않는 리소스 유형입니다.
- D. AuditReport: Kyverno에서 사용되지 않는 리소스 유형입니다.
</details>

### 10. Kyverno에서 정책을 테스트하는 데 사용할 수 있는 명령줄 도구는 무엇인가요?

A. kyverno-cli  
B. kubectl-kyverno  
C. kyverno-test  
D. policy-test  

<details>
<summary>정답 및 설명</summary>

**정답: B. kubectl-kyverno**

**설명:**
Kyverno에서 정책을 테스트하는 데 사용할 수 있는 명령줄 도구는 `kubectl-kyverno`입니다. 이 도구는 kubectl 플러그인으로 작동하며, Kyverno 정책을 테스트, 검증 및 관리하는 데 도움이 됩니다.

`kubectl-kyverno`의 주요 기능:
1. **정책 테스트**: 리소스에 대한 정책 적용 결과를 시뮬레이션합니다.
2. **정책 검증**: 정책 구문과 구조를 검증합니다.
3. **정책 생성**: 일반적인 사용 사례에 대한 정책 템플릿을 생성합니다.
4. **정책 적용**: 정책을 클러스터에 적용합니다.

**설치 방법:**
```bash
# krew를 사용한 설치
kubectl krew install kyverno

# 직접 다운로드 및 설치
curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
sudo mv kubectl-kyverno /usr/local/bin/
```

**주요 명령어:**

1. **정책 테스트**:
```bash
# 리소스에 대한 정책 적용 테스트
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml

# 여러 정책 테스트
kubectl kyverno apply /path/to/policies/ --resource /path/to/resources/

# 변경(mutate) 결과 확인
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml -o yaml
```

2. **정책 검증**:
```bash
# 정책 구문 및 구조 검증
kubectl kyverno validate /path/to/policy.yaml
```

3. **정책 생성**:
```bash
# 일반적인 정책 템플릿 생성
kubectl kyverno create disallow-latest-tag

# 사용 가능한 템플릿 목록 확인
kubectl kyverno create --help
```

4. **정책 적용**:
```bash
# 정책을 클러스터에 적용
kubectl kyverno apply /path/to/policy.yaml --cluster
```

**테스트 예시:**
```bash
# 정책 파일 생성
cat > require-labels.yaml << EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
EOF

# 리소스 파일 생성
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.19.0
EOF

# 정책 테스트
kubectl kyverno apply require-labels.yaml --resource pod.yaml

# 결과:
# applying 1 policy to 1 resource...
# resource Pod/default/nginx failed validation
# policy require-labels: rule check-team-label failed: label 'team' is required
```

**CI/CD 파이프라인에서의 활용:**
```yaml
# GitHub Actions 예시
name: Kyverno Policy Test

on:
  pull_request:
    paths:
      - 'policies/**'
      - 'resources/**'

jobs:
  test-policies:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2
      
      - name: Install kubectl-kyverno
        run: |
          curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
          sudo mv kubectl-kyverno /usr/local/bin/
      
      - name: Validate policies
        run: |
          kubectl kyverno validate policies/
      
      - name: Test policies against resources
        run: |
          kubectl kyverno apply policies/ --resource resources/
```

**다른 옵션들의 문제점:**
- A. kyverno-cli: Kyverno에서 사용되지 않는 도구 이름입니다.
- C. kyverno-test: Kyverno에서 사용되지 않는 도구 이름입니다.
- D. policy-test: Kyverno에서 사용되지 않는 도구 이름입니다.
</details>
