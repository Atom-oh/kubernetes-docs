# Kubernetes 및 관련 도구의 API 버전 변경 가이드

이 문서는 Kubernetes 및 관련 도구(Cilium, Karpenter 등)의 API 버전 변경 사항을 정리하고, 마이그레이션 방법을 안내합니다.

## Kubernetes API 버전 변경

Kubernetes는 지속적으로 발전하면서 API 버전을 업데이트합니다. 이전 버전의 API는 일정 기간 지원 후 제거됩니다.

### 주요 API 버전 변경 사항

| 리소스 | 이전 버전 | 현재 버전 | 변경된 Kubernetes 버전 |
|-------|----------|----------|----------------------|
| Deployment | apps/v1beta1, apps/v1beta2 | apps/v1 | 1.16+ |
| StatefulSet | apps/v1beta1, apps/v1beta2 | apps/v1 | 1.16+ |
| DaemonSet | extensions/v1beta1, apps/v1beta2 | apps/v1 | 1.16+ |
| NetworkPolicy | extensions/v1beta1 | networking.k8s.io/v1 | 1.16+ |
| PodSecurityPolicy | extensions/v1beta1 | policy/v1beta1 | 1.16+ (1.25에서 제거) |
| Ingress | extensions/v1beta1 | networking.k8s.io/v1 | 1.22+ |
| CronJob | batch/v1beta1 | batch/v1 | 1.21+ |
| EndpointSlice | discovery.k8s.io/v1beta1 | discovery.k8s.io/v1 | 1.21+ |
| PriorityClass | scheduling.k8s.io/v1beta1 | scheduling.k8s.io/v1 | 1.17+ |
| CustomResourceDefinition | apiextensions.k8s.io/v1beta1 | apiextensions.k8s.io/v1 | 1.19+ |

## Cilium API 버전

Cilium은 자체 CRD(Custom Resource Definition)를 사용하여 네트워크 정책 및 기타 리소스를 정의합니다.

### Cilium 1.17 API 버전

| 리소스 | API 버전 | 설명 |
|-------|----------|------|
| CiliumNetworkPolicy | cilium.io/v2 | Cilium 네트워크 정책 |
| CiliumClusterwideNetworkPolicy | cilium.io/v2 | 클러스터 전체 네트워크 정책 |
| CiliumEndpoint | cilium.io/v2 | Cilium 엔드포인트 정보 |
| CiliumIdentity | cilium.io/v2 | Cilium 보안 ID |
| CiliumNode | cilium.io/v2 | Cilium 노드 정보 |
| CiliumExternalWorkload | cilium.io/v2 | 외부 워크로드 정의 |
| CiliumLocalRedirectPolicy | cilium.io/v2 | 로컬 리디렉션 정책 |

## Karpenter API 버전 변경

Karpenter는 1.6 버전에서 API 버전이 크게 변경되었습니다. 이전 버전의 `Provisioner` 리소스가 `NodePool`로 변경되었습니다.

### 이전 버전 (v1alpha5)

```yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: default
spec:
  requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values: ["spot"]
  limits:
    resources:
      cpu: 1000
  providerRef:
    name: default
  ttlSecondsAfterEmpty: 30
```

### 현재 버전 (v1)

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
  limits:
    cpu: 1000
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 주요 변경 사항

1. **리소스 이름 변경**: `Provisioner` → `NodePool`
2. **API 버전 변경**: `karpenter.sh/v1alpha5` → `karpenter.sh/v1`
3. **구조 변경**: 
   - `spec.requirements` → `spec.template.spec.requirements`
   - `spec.limits.resources` → `spec.limits`
   - `spec.ttlSecondsAfterEmpty` → `spec.disruption.consolidateAfter`
   - `providerRef` 제거 및 `NodeClass` 리소스 도입

### NodeClass 리소스 추가

```yaml
apiVersion: karpenter.sh/v1
kind: NodeClass
metadata:
  name: default
spec:
  # 클라우드 제공자별 설정
```

### 마이그레이션 방법

1. 기존 Provisioner 리소스 백업
2. Karpenter 1.6 이상으로 업그레이드
3. NodePool 및 NodeClass 리소스 생성
4. 기능 검증 후 이전 Provisioner 리소스 제거

## EKS AutoMode API 버전 호환성

EKS AutoMode는 특정 API 버전만 지원합니다. 자세한 내용은 [AWS 공식 문서](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)를 참조하세요.

### EKS AutoMode에서 지원되는 API 버전

| 리소스 | 지원되는 API 버전 | 비고 |
|-------|-----------------|------|
| Deployment | apps/v1 | |
| StatefulSet | apps/v1 | |
| DaemonSet | apps/v1 | |
| ReplicaSet | apps/v1 | |
| NetworkPolicy | networking.k8s.io/v1 | |
| Ingress | networking.k8s.io/v1 | |
| CronJob | batch/v1 | |
| Job | batch/v1 | |
| PodDisruptionBudget | policy/v1 | |
| HorizontalPodAutoscaler | autoscaling/v2 | |

## API 버전 변경 대응 방법

### 1. 현재 사용 중인 API 버전 확인

```bash
# 특정 리소스의 API 버전 확인
kubectl api-resources | grep <resource-name>

# 특정 네임스페이스의 모든 리소스 확인
kubectl get all -n <namespace> -o yaml | grep "apiVersion:"

# 클러스터 내 모든 CRD 확인
kubectl get crd -o custom-columns=NAME:.metadata.name,VERSION:.spec.versions[*].name
```

### 2. 매니페스트 파일 업데이트

```bash
# kubectl convert 명령어 사용 (플러그인 설치 필요)
kubectl convert -f old-deployment.yaml --output-version apps/v1 > new-deployment.yaml

# 또는 수동으로 apiVersion 필드 업데이트
```

### 3. CI/CD 파이프라인 업데이트

- 모든 CI/CD 파이프라인에서 사용하는 매니페스트 파일 업데이트
- Helm 차트 및 값 파일 업데이트
- Kustomize 구성 업데이트

### 4. 점진적 마이그레이션

1. 테스트 환경에서 먼저 변경 사항 적용 및 검증
2. 프로덕션 환경에 점진적으로 적용
3. 롤백 계획 준비

## 도구별 API 버전 확인 방법

### Cilium

```bash
# Cilium CRD 버전 확인
kubectl get crd ciliumnetworkpolicies.cilium.io -o jsonpath='{.spec.versions[*].name}'

# Cilium 버전 확인
cilium version
```

### Karpenter

```bash
# Karpenter CRD 버전 확인
kubectl get crd nodepools.karpenter.sh -o jsonpath='{.spec.versions[*].name}'
kubectl get crd nodeclaims.karpenter.sh -o jsonpath='{.spec.versions[*].name}'
kubectl get crd nodeclasses.karpenter.sh -o jsonpath='{.spec.versions[*].name}'

# 이전 버전 CRD 확인
kubectl get crd provisioners.karpenter.sh -o jsonpath='{.spec.versions[*].name}' 2>/dev/null || echo "Provisioner CRD not found"
```

## 참고 자료

- [Kubernetes API 제거 가이드](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- [Cilium 문서](https://docs.cilium.io/)
- [Karpenter 문서](https://karpenter.sh/docs/concepts/)
- [EKS AutoMode 마이그레이션 가이드](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
