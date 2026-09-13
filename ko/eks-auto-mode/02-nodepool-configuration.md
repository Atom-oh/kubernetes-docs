# NodePool 구성 및 최적화

> **지원 버전**: EKS Auto Mode GA; 예제 기준 EKS 1.36
> **마지막 업데이트**: 2026년 9월 12일

AWS 관리 기본 풀, 커스텀 NodePool 제약과 AWS 전용 NodeClass API를 구분합니다. 먼저 [시작하기](./01-getting-started.md)를 완료하고 대상 계정·컨텍스트를 확인하세요. 적용 전에 모든 IAM/profile 이름과 네트워크 태그를 검토합니다. 예제의 용량 제한은 설명용이며 상당한 비용을 허용할 수도 있습니다.

NodePool 예제는 릴리스된 Karpenter 1.14.1 CRD의 구조 스키마로 검사하고 AWS 전용 NodeClass 필드는 AWS 문서와 대조했습니다. 이것이 Auto Mode 내부 컨트롤러 버전을 특정하거나 실제 클러스터의 admission/readiness를 입증하지는 않습니다. 이번 감사에서 노드를 프로비저닝하지 않았습니다.

## 기본 NodePool 이해

활성화하면 다음 풀을 제공합니다. AWS 관리 구성을 직접 수정하기보다 별도의 커스텀 풀을 만드세요.

| 풀 | 아키텍처 | 용량과 인스턴스 선택 | 용도 |
|----|----------|----------------------|------|
| `general-purpose` | `amd64` | On-Demand, C/M/R 계열, 5세대 이상 | 범용 워크로드 |
| `system` | `amd64`, `arm64` | On-Demand, C/M/R 계열, 5세대 이상 | `CriticalAddonsOnly`를 toleration으로 허용한 클러스터 중요 워크로드 |

기본 general-purpose 풀은 Spot을 활성화하지 않습니다. Spot이나 다른 아키텍처·인스턴스 제약이 필요하면 커스텀 풀을 사용하세요. Auto Mode는 노드 로컬 DNS와 서비스 네트워킹 기능을 제공하므로 순수 Auto Mode 클러스터에서 system 풀을 채우기 위해 일반 CoreDNS/kube-proxy Pod를 배치할 필요는 없습니다. 혼합 클러스터에서는 non-Auto 노드용 기존 CoreDNS Deployment가 필요합니다.

추측한 기본 YAML을 적용하지 말고 실제 관리 객체에서 disruption 설정과 taint 세부 값을 확인하세요.

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

AWS가 `default` NodeClass를 제공하려면 기본 풀 중 하나 이상이 활성화돼야 합니다. 둘 다 끄면 직접 NodeClass를 만들고 아래 참조를 바꿔야 합니다. `computeConfig.nodePools`에서 기본 풀 이름을 제거하면 해당 풀과 노드가 drain·종료됩니다. 새 워크로드에서만 숨기는 설정이 아닙니다.

## 커스텀 NodePool 생성

아래 예제는 배치 제약에 집중하도록 기존 `default` NodeClass를 참조합니다. 뒤에서 만드는 커스텀 NodeClass를 사용하려면 먼저 생성하고 대상 풀의 `nodeClassRef.name`을 바꾸세요. `template` 아래 label·taint가 새 노드에 적용되며, NodePool metadata에만 붙인 label은 노드 label이 아닙니다.

### 컴퓨팅 최적화 워크로드

`Gt ["6"]` 조건은 7세대 이상을 허용합니다. 최신 세대 하나만 선택하는 조건이 아닙니다. 예제는 x86 C 계열 On-Demand를 허용하고 메모리 예제보다 높은 프로비저닝 선호도를 지정합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '6'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - xlarge
        - 2xlarge
        - 4xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  weight: 10
```

### 메모리 최적화 워크로드

6세대 이상 R 계열에서 두 아키텍처를 허용합니다. 스케줄러가 선택할 수 있는 아키텍처를 컨테이너 이미지와 애플리케이션 의존성도 지원해야 합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - 2xlarge
        - 4xlarge
        - 8xlarge
        - 12xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '500'
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

## AWS NodeClass 구성

Auto Mode는 `eks.amazonaws.com/v1`의 `NodeClass`를 사용합니다. 자체 관리 AWS Karpenter의 `EC2NodeClass`와 필드가 다릅니다. `amiFamily`, `blockDeviceMappings`, 임의의 셸 `userData`, `metadataOptions`를 이 API에 복사하지 마세요. AWS가 관리형 Bottlerocket 변형을 선택합니다.

다음 내용을 `custom-nodeclass.yaml`로 저장하고 예시 profile·selector 값을 검토된 리소스로 바꿉니다. `instanceProfile`은 지원되며 이름은 `eks`로 시작해야 합니다. 대신 `role`에 노드 IAM 역할 이름을 지정할 수도 있습니다. **`role`과 `instanceProfile` 중 하나만 지정하세요.** Profile에 담긴 역할에는 적절한 Auto Mode EKS access entry와 권한이 필요합니다. 이미 구성된 역할을 재사용하면 entry를 중복 생성하지 않습니다. 새 역할은 AWS NodeClass 참조의 access-entry 절차를 따르세요.

서브넷 태그는 리소스를 선택할 뿐 라우팅이나 격리를 입증하지 않습니다. VPC, AZ 가용성, 라우팅 테이블과 보안 그룹 규칙을 확인하세요. `associatePublicIPAddress: false`는 공인 IP 할당을 막지만 노드에는 적절한 아웃바운드 연결이 필요합니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: '1'
      Environment: production
  securityGroupSelectorTerms:
  - tags:
      kubernetes.io/cluster/my-cluster: owned
      Type: worker-node
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  advancedNetworking:
    associatePublicIPAddress: false
  advancedCompute:
    kernel:
      sysctl:
        vm.max_map_count: 262144
  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

클러스터 역할이 `spec.tags`의 커스텀 키로 리소스를 생성·태깅할 권한이 있는지 확인하세요. NodeClass 자체가 IAM 권한을 부여하지는 않습니다.

`ephemeralStorage`는 임의의 블록 디바이스 매핑이 아니라 노드 임시 스토리지를 구성합니다. `100Gi`, 3000 IOPS, 125 MiB/s는 예시입니다. 현재 Auto Mode 필드 제한, 인스턴스 스토리지 동작과 비용을 확인하세요. 고객 KMS 설정 위치는 `ephemeralStorage.kmsKeyID`이며 노드의 루트·데이터 **EBS** 볼륨에 적용됩니다. 로컬 NVMe instance store의 암호화 키를 선택하거나 애플리케이션 PVC 암호화를 보장하지 않습니다.

이전 bootstrap 예제는 `vm.max_map_count`를 바꿨습니다. 지원되는 대안은 노드 부팅 시 적용하는 `advancedCompute.kernel.sysctl`입니다. 지원되는 커널 설정을 바꾸면 기존 노드에 drift·교체가 발생하며, 실행 중인 노드에 즉시 셸 명령을 적용하는 방식이 아닙니다. 해당 설정이 필요한 워크로드에만 구성하고 중단 동작을 검토하세요.

### 고정된 IMDS 보안 설정

Auto Mode는 IMDSv2와 hop limit 1을 강제하며 NodeClass에서 변경할 수 없습니다. 일반 non-host-network Pod는 이 경로로 IMDS에 접근하지 못하지만 모든 Pod에 대한 격리 보장은 아닙니다. `hostNetwork` 사용 시 도달성이 달라집니다. 애플리케이션 AWS 접근에는 워크로드 ID를 사용하고, 노드 메타데이터에 의존하기보다 리전 등 필요한 설정을 명시하세요.

### 고객 KMS, CA bundle과 Pod 네트워크 분리

잘린 인증서 문자열을 manifest에 붙이지 마세요. 선택적인 다음 생성기는 검토한 기본 템플릿을 읽고 승인된 공개 PEM bundle을 검사한 뒤 `certificateBundles[].data`에 base64로 넣어 완전한 두 번째 NodeClass를 만듭니다. Python 3와 PyYAML이 필요합니다. `NODE_KMS_KEY_ARN`, `CA_BUNDLE_FILE`을 설정하고 이전 장에서 검토한 `AWS_REGION`·`EXPECTED_ACCOUNT_ID`를 유지하세요.

CA 발급자, fingerprint와 유효 기간은 별도로 승인받아야 합니다. 아래 형식 검사는 신뢰성, KMS 권한이나 클라우드 리소스의 존재를 입증하지 않습니다. 적용 전에 key policy/IAM grant와 Pod 네트워크 태그 선택을 검토하세요.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed cluster region}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${NODE_KMS_KEY_ARN:?Set the approved same-region customer-managed KMS key ARN}"
: "${CA_BUNDLE_FILE:?Set the path to an approved public CA PEM bundle}"
export AWS_REGION EXPECTED_ACCOUNT_ID NODE_KMS_KEY_ARN CA_BUNDLE_FILE
umask 077
python3 - <<'PY'
import base64, json, os, re, ssl
from pathlib import Path
import yaml

doc = yaml.safe_load(Path("custom-nodeclass.yaml").read_text())
if doc.get("kind") != "NodeClass" or doc.get("apiVersion") != "eks.amazonaws.com/v1":
    raise SystemExit("Expected the reviewed Auto Mode NodeClass template")
spec = doc["spec"]
if ("role" in spec) == ("instanceProfile" in spec):
    raise SystemExit("Set exactly one reviewed role or instanceProfile")
key = os.environ["NODE_KMS_KEY_ARN"]
prefix = "arn:aws:kms:" + os.environ["AWS_REGION"] + ":" + os.environ["EXPECTED_ACCOUNT_ID"] + ":key/"
if not key.startswith(prefix) or not re.fullmatch(r"(?:[a-f0-9-]{36}|mrk-[a-f0-9]{32})", key[len(prefix):]):
    raise SystemExit("KMS key ARN must match the reviewed account and region")
pem = Path(os.environ["CA_BUNDLE_FILE"]).read_bytes()
if b"PRIVATE KEY" in pem:
    raise SystemExit("Use public CA certificates only, never a private key")
ssl.create_default_context().load_verify_locations(cadata=pem.decode("ascii"))
doc["metadata"]["name"] = "secure-network-nodeclass"
spec["ephemeralStorage"]["kmsKeyID"] = key
spec["certificateBundles"] = [{"name": "corporate-ca",
                               "data": base64.b64encode(pem).decode("ascii")}]
spec["podSubnetSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
spec["podSecurityGroupSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
Path("secure-network-nodeclass.json").write_text(json.dumps(doc, indent=2) + "\n")
PY
```

| 필드 | 의미 |
|------|------|
| `ephemeralStorage.kmsKeyID` | 노드 루트·데이터 EBS 볼륨용 고객 관리 키. 클러스터와 같은 리전의 키 사용 |
| `certificateBundles[].data` | 노드 신뢰를 위한 base64 인코딩 인증서 bundle. 모든 애플리케이션 컨테이너의 trust store를 자동으로 변경하지 않음 |
| `podSubnetSelectorTerms` | 이 NodeClass용 별도 Pod 서브넷 선택 |
| `podSecurityGroupSelectorTerms` | Pod 네트워크 보안 그룹. Pod 서브넷 selector와 함께 구성 |

Pod 서브넷과 보안 그룹 selector는 함께 구성하고 VPC/AZ 범위를 맞춰야 합니다. 이 구분은 namespace나 ServiceAccount별 설정이 아니라 NodeClass 단위입니다. Host-network 트래픽은 노드 네트워크를 사용하며 egress SNAT도 출발지 주소와 적용 보안 그룹을 바꿀 수 있습니다. 모든 트래픽이 격리됐다고 판단하기 전에 라우팅, SNAT와 Pod 밀도 영향을 검토하세요.

## 워크로드와 환경 분리

### 프론트엔드·백엔드 풀

Taint는 맞는 toleration이 없는 Pod의 배치를 막습니다. Toleration은 배치를 허용할 뿐입니다. 지정한 노드를 사용해야 한다면 selector나 required affinity도 지정하세요.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      taints:
      - key: workload-tier
        value: frontend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      taints:
      - key: workload-tier
        value: backend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 800Gi
```

예를 들어 소유한 `nodepool-lab` namespace를 준비한 뒤 프론트엔드 배치를 확인하는 Pod에 selector와 toleration을 함께 지정합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend-placement-check
  namespace: nodepool-lab
spec:
  automountServiceAccountToken: false
  nodeSelector:
    workload-tier: frontend
  tolerations:
  - key: workload-tier
    operator: Equal
    value: frontend
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.4
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
        port: 80
      periodSeconds: 5
```

적용 전에 검토하세요. 이 Pod는 과금되는 노드 프로비저닝을 유발할 수 있습니다. 배치된 노드, readiness와 node label을 확인한 뒤 해당 namespace에서 테스트 Pod를 삭제합니다. `NoSchedule`은 이미 실행 중인 Pod를 축출하지 않으며 label·taint만으로 신뢰하지 않는 테넌트 사이의 보안 경계를 만들 수는 없습니다.

### 개발용 풀

현재 AWS 지원 목록에는 M 계열과 함께 T 계열 burstable 인스턴스도 있습니다. 과거 Auto Mode 가정만으로 T를 제거하지 마세요. Auto Mode는 CPU가 1개보다 많아야 하며 nano/micro/small 크기를 제외합니다. 그래도 리전별 타입 가용성, CPU credit 동작과 워크로드 적합성을 확인해야 합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - t
        - m
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - medium
        - large
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      taints:
      - key: environment
        value: development
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 1
```

## 리소스 제한, 가중치와 검증

`limits.cpu`와 `limits.memory`는 풀의 합산 리소스 기준이며 최대 노드 수나 금액 예산이 아닙니다. 정수·문자열 GitOps 차이를 피하도록 CPU quantity를 따옴표로 감싸세요. 예를 들어 `memory: 4000Gi`는 4000 GiB(약 3.91 TiB)이지 정확한 4 TB가 아닙니다.

Upstream Karpenter는 빠른 프로비저닝 시 eventual consistency로 제한을 넘을 수 있다고 설명합니다. 이 필드로 즉시 적용되는 과금 상한을 약속하지 마세요. 노드 교체 여유를 두고 사용량을 관찰하며 관리형 환경의 실제 동작을 검증합니다.

`weight`는 적합한 풀 사이에서 프로비저닝 선호도에 영향을 줍니다. Kubernetes 스케줄러의 노드 우선순위를 부여하거나 기존 워크로드를 축출하거나 Pod를 특정 풀에 고정하지 않습니다. 워크로드 제약을 명시하고 의도하지 않은 풀 중첩을 피하세요.

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

Server dry-run은 admission을 검사할 수 있지만 IAM, 네트워크 연결, 프로비저닝, 스토리지나 애플리케이션 동작을 입증하지는 않습니다. False/unknown readiness를 해결하고 통제된 워크로드로 검증한 뒤 프로덕션에 적용하세요.

## 참고 자료

- [Built-in NodePools](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Auto Mode NodePool fields and labels](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode NodeClass specification](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Managed instance types and IMDS restrictions](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Auto Mode node security](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [Upstream Karpenter NodePool limits](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter weighted provisioning](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [Node CA, KMS and network features](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [이전: 시작하기](./01-getting-started.md) | [목차](./README.md) | [다음: 스케일링 동작](./03-scaling-behavior.md) >
