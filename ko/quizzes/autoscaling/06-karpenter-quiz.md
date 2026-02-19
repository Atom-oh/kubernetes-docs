# Karpenter 퀴즈

이 퀴즈는 Karpenter 노드 오토스케일러의 개념, NodePool/EC2NodeClass 구성, 비용 최적화, Consolidation, Drift, 인터럽션 처리 및 Amazon EKS 통합에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Karpenter가 기존 Cluster Autoscaler와 비교하여 가장 큰 차이점은 무엇인가요?
   - A) Kubernetes 버전 요구사항이 더 높음
   - B) Auto Scaling Group 없이 직접 EC2 인스턴스를 프로비저닝
   - C) AWS만 지원하고 다른 클라우드는 지원하지 않음
   - D) CPU 기반 스케일링만 지원

<details>

<summary>정답 보기</summary>

**정답: B) Auto Scaling Group 없이 직접 EC2 인스턴스를 프로비저닝**

**설명:**
Karpenter의 가장 큰 차별점은 Auto Scaling Group(ASG)을 우회하고 EC2 Fleet API를 직접 사용하여 노드를 프로비저닝한다는 것입니다. Cluster Autoscaler는 노드 그룹/ASG를 통해 스케일링하므로 노드 그룹 구성에 따라 인스턴스 유형이 제한됩니다. Karpenter는 파드 요구사항에 따라 다양한 인스턴스 유형 중 최적의 것을 동적으로 선택하며, 몇 초 내에 노드를 프로비저닝할 수 있습니다.
</details>

2. Karpenter v1beta1 API에서 노드 프로비저닝 정책을 정의하는 CRD는 무엇인가요?
   - A) Provisioner
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>정답 보기</summary>

**정답: B) NodePool**

**설명:**
Karpenter v1beta1 API에서는 기존의 Provisioner CRD가 NodePool로 대체되었습니다. NodePool은 노드 프로비저닝 정책(인스턴스 유형, 용량 유형, 아키텍처, 가용 영역 등)과 disruption 설정(consolidation, expireAfter 등)을 정의합니다. EC2NodeClass는 AWS 특정 구성(서브넷, 보안 그룹, AMI, 블록 디바이스 등)을 정의하며, NodePool은 nodeClassRef를 통해 EC2NodeClass를 참조합니다.
</details>

3. Karpenter에서 비용 최적화를 위해 Spot 인스턴스를 사용하도록 구성하는 방법은 무엇인가요?
   - A) disruption.capacityType: spot
   - B) requirements에서 karpenter.sh/capacity-type: spot 지정
   - C) nodeClassRef에서 spotEnabled: true 설정
   - D) limits에서 spot: true 설정

<details>

<summary>정답 보기</summary>

**정답: B) requirements에서 karpenter.sh/capacity-type: spot 지정**

**설명:**
NodePool의 `spec.template.spec.requirements`에서 `karpenter.sh/capacity-type` 키를 사용하여 용량 유형을 지정합니다. `values: ["spot"]`으로 Spot 인스턴스만 사용하거나, `values: ["spot", "on-demand"]`로 둘 다 허용할 수 있습니다. Karpenter는 가격과 가용성을 고려하여 최적의 인스턴스를 선택합니다. Spot 인스턴스는 On-Demand 대비 최대 90%까지 비용을 절감할 수 있습니다.
</details>

4. Karpenter의 Consolidation 기능이 수행하는 작업은 무엇인가요?
   - A) 여러 노드의 로그를 통합
   - B) 여러 노드의 워크로드를 더 적은 수의 노드로 통합하여 비용 절감
   - C) 여러 클러스터를 하나로 통합
   - D) 여러 NodePool을 하나로 통합

<details>

<summary>정답 보기</summary>

**정답: B) 여러 노드의 워크로드를 더 적은 수의 노드로 통합하여 비용 절감**

**설명:**
Consolidation은 Karpenter의 핵심 비용 최적화 기능입니다. 사용률이 낮은 여러 노드의 워크로드를 더 적은 수의 노드로 통합(빈 패킹)하여 리소스 활용도를 높이고 비용을 절감합니다. `consolidationPolicy: WhenEmpty`는 노드가 비어 있을 때만 제거하고, `consolidationPolicy: WhenUnderutilized`는 사용률이 낮을 때도 통합을 수행합니다. `consolidateAfter`로 통합까지의 대기 시간을 설정합니다.
</details>

5. Karpenter의 expireAfter 설정의 목적은 무엇인가요?
   - A) 파드가 노드에서 실행될 수 있는 최대 시간
   - B) 노드가 생성된 후 자동으로 교체되기까지의 최대 시간
   - C) Karpenter 컨트롤러의 캐시 만료 시간
   - D) NodePool 정책의 유효 기간

<details>

<summary>정답 보기</summary>

**정답: B) 노드가 생성된 후 자동으로 교체되기까지의 최대 시간**

**설명:**
`expireAfter` 설정은 노드의 최대 수명을 정의합니다. 예를 들어 `expireAfter: 720h`(30일)로 설정하면 노드가 30일 후에 자동으로 교체됩니다. 이는 보안 패치 적용, AMI 업데이트, 최신 인스턴스 유형 활용 등을 위해 노드를 정기적으로 갱신하는 데 유용합니다. Karpenter는 PDB를 존중하여 워크로드를 안전하게 다른 노드로 이동시킨 후 기존 노드를 종료합니다.
</details>

6. Karpenter에서 NodePool의 리소스 제한을 설정하는 필드는 무엇인가요?
   - A) spec.template.limits
   - B) spec.limits
   - C) spec.maxResources
   - D) spec.resourceQuota

<details>

<summary>정답 보기</summary>

**정답: B) spec.limits**

**설명:**
NodePool의 `spec.limits`에서 해당 NodePool이 프로비저닝할 수 있는 리소스의 최대량을 정의합니다. 예를 들어 `limits: { cpu: 1000, memory: 1000Gi }`로 설정하면 총 CPU 1000 코어, 메모리 1000Gi까지만 프로비저닝됩니다. 이를 통해 비용 제어와 클러스터 용량 관리가 가능합니다. 제한에 도달하면 Karpenter는 추가 노드를 프로비저닝하지 않습니다.
</details>

7. Karpenter의 Drift 기능은 무엇을 감지하고 처리하나요?
   - A) 네트워크 트래픽 변화
   - B) NodePool/EC2NodeClass 변경으로 인해 기존 노드가 현재 구성과 일치하지 않는 상태
   - C) 파드 스케줄링 드리프트
   - D) Kubernetes 버전 변경

<details>

<summary>정답 보기</summary>

**정답: B) NodePool/EC2NodeClass 변경으로 인해 기존 노드가 현재 구성과 일치하지 않는 상태**

**설명:**
Drift 기능은 NodePool 또는 EC2NodeClass의 구성이 변경되었을 때, 기존 노드가 새 구성과 일치하지 않음을 감지합니다. 예를 들어 AMI를 업데이트하거나 보안 그룹을 변경한 경우, 기존 노드는 "drifted" 상태가 됩니다. Karpenter는 이러한 노드를 점진적으로 교체하여 클러스터의 모든 노드가 최신 구성을 사용하도록 합니다. `featureGates.drift=true`로 활성화합니다.
</details>

8. EC2NodeClass에서 노드의 루트 볼륨 크기와 유형을 설정하는 필드는 무엇인가요?
   - A) spec.rootVolume
   - B) spec.blockDeviceMappings
   - C) spec.storage
   - D) spec.ebsConfig

<details>

<summary>정답 보기</summary>

**정답: B) spec.blockDeviceMappings**

**설명:**
EC2NodeClass의 `spec.blockDeviceMappings`에서 EBS 볼륨 구성을 정의합니다. `deviceName: /dev/xvda`로 루트 볼륨을 지정하고, `ebs` 하위 필드에서 `volumeSize`, `volumeType`, `iops`, `throughput`, `encrypted`, `kmsKeyID` 등을 설정합니다. 예를 들어 gp3 볼륨 100Gi를 암호화하여 사용하려면 해당 속성들을 적절히 구성합니다.
</details>

## 단답형 문제

9. Karpenter가 스케줄링할 수 없는 파드를 감지하고 적절한 노드를 프로비저닝하기까지 걸리는 일반적인 시간은 얼마인가요?

<details>

<summary>정답 보기</summary>

**정답: 몇 초(수 초) 내**

**설명:**
Karpenter는 스케줄링할 수 없는 파드를 감지하면 몇 초 내에 노드를 프로비저닝합니다. 이는 Cluster Autoscaler가 ASG를 통해 스케일링하는 데 몇 분이 걸리는 것과 대조적입니다. Karpenter의 빠른 스케일링은 EC2 Fleet API를 직접 사용하고, 파드 요구사항을 분석하여 최적의 인스턴스를 즉시 선택하기 때문입니다. 이는 버스트 트래픽이나 빠른 스케일 아웃이 필요한 워크로드에 큰 장점입니다.
</details>

10. Karpenter에서 여러 NodePool이 존재할 때 우선순위를 결정하는 방법은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: weight 필드를 사용한 가중치 기반 우선순위**

**설명:**
여러 NodePool이 파드의 요구사항을 충족할 수 있을 때, `spec.weight` 필드를 사용하여 우선순위를 지정합니다. 더 높은 weight 값을 가진 NodePool이 우선적으로 선택됩니다. 예를 들어 Spot 인스턴스 NodePool에 높은 weight를 설정하고 On-Demand NodePool에 낮은 weight를 설정하면, Karpenter는 Spot을 먼저 시도하고 사용 불가 시 On-Demand를 사용합니다.
</details>

11. Karpenter가 노드를 제거할 때 워크로드 가용성을 보장하기 위해 존중하는 Kubernetes 리소스는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: PDB (PodDisruptionBudget)**

**설명:**
Karpenter는 노드를 제거(consolidation, expiration, drift 등)할 때 PodDisruptionBudget(PDB)을 존중합니다. PDB는 애플리케이션의 최소 가용성을 정의하며, Karpenter는 PDB를 위반하지 않는 범위에서만 노드를 드레이닝합니다. 예를 들어 `minAvailable: 2`인 PDB가 있으면, Karpenter는 최소 2개의 파드가 항상 실행되도록 보장하면서 노드를 제거합니다.
</details>

12. EC2NodeClass에서 Karpenter가 사용할 서브넷과 보안 그룹을 선택하는 방법은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: subnetSelectorTerms와 securityGroupSelectorTerms를 통한 태그 기반 선택**

**설명:**
EC2NodeClass에서 `subnetSelectorTerms`와 `securityGroupSelectorTerms`를 사용하여 태그 기반으로 서브넷과 보안 그룹을 선택합니다. 예를 들어 `tags: { karpenter.sh/discovery: "my-cluster" }`로 특정 태그가 있는 리소스를 선택합니다. 미리 AWS 리소스에 해당 태그를 설정해야 하며, 여러 서브넷이 선택되면 Karpenter는 가용 영역 분산을 위해 적절히 분배합니다.
</details>

## 실습 문제

13. Spot 인스턴스를 우선 사용하고, 다양한 인스턴스 유형(m5, c5, r5 계열)을 허용하며, 30분 후 빈 노드를 제거하는 NodePool을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    metadata:
      labels:
        nodepool: cost-optimized
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - m5.large
            - m5.xlarge
            - m5.2xlarge
            - c5.large
            - c5.xlarge
            - c5.2xlarge
            - r5.large
            - r5.xlarge
            - r5.2xlarge
      nodeClassRef:
        apiVersion: karpenter.k8s.aws/v1beta1
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**설명:**
이 NodePool은 비용 최적화를 위해 Spot 인스턴스를 우선 사용합니다(`capacity-type`에 spot을 먼저 나열). 다양한 인스턴스 유형을 허용하여 Spot 가용성과 가격 최적화를 높입니다. `consolidationPolicy: WhenEmpty`와 `consolidateAfter: 30m`으로 노드가 30분간 비어 있으면 제거합니다. `weight: 100`으로 다른 NodePool보다 높은 우선순위를 설정하여 이 NodePool이 먼저 선택되도록 합니다.
</details>

14. 100Gi gp3 암호화된 루트 볼륨, 특정 태그 기반 서브넷/보안 그룹 선택, IMDSv2 필수 설정을 포함하는 EC2NodeClass를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: AL2

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"
        kubernetes.io/role: "private"

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"

  instanceProfile: KarpenterNodeInstanceProfile-my-cluster

  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        deleteOnTermination: true

  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 필수

  tags:
    Environment: production
    ManagedBy: karpenter
```

**설명:**
이 EC2NodeClass는 보안 모범 사례를 따릅니다. `blockDeviceMappings`에서 gp3 볼륨을 100Gi 크기로 암호화하여 설정합니다. `metadataOptions.httpTokens: required`로 IMDSv2를 필수로 설정하여 SSRF 공격을 방지합니다. 태그 기반 선택기로 프라이빗 서브넷만 사용하도록 구성합니다. `instanceProfile`은 미리 생성된 IAM 인스턴스 프로필을 참조합니다.
</details>

15. Karpenter 설치 후 상태를 확인하고, 프로비저닝 문제를 디버깅하는 명령어들을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. Karpenter 파드 상태 확인
kubectl get pods -n karpenter

# 2. Karpenter 컨트롤러 로그 확인
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# 3. NodePool 상태 확인
kubectl get nodepool
kubectl describe nodepool default

# 4. EC2NodeClass 상태 확인
kubectl get ec2nodeclass
kubectl describe ec2nodeclass default

# 5. 스케줄링 대기 중인 파드 확인
kubectl get pods --all-namespaces --field-selector status.phase=Pending

# 6. Karpenter가 생성한 노드 확인
kubectl get nodes -l karpenter.sh/nodepool

# 7. 노드 상세 정보 및 레이블/테인트 확인
kubectl describe node <node-name>

# 8. Karpenter 이벤트 확인
kubectl get events --field-selector source=karpenter --sort-by='.lastTimestamp'

# 9. 노드 프로비저닝 관련 상세 로그 확인
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Karpenter 메트릭 확인 (Prometheus가 구성된 경우)
kubectl port-forward -n karpenter svc/karpenter 8080:8080 &
curl localhost:8080/metrics | grep karpenter_
```

**설명:**
Karpenter 문제 해결 시 여러 측면을 확인해야 합니다. 먼저 컨트롤러 파드가 정상 실행 중인지, 로그에 오류가 없는지 확인합니다. NodePool과 EC2NodeClass의 상태와 구성을 검토합니다. Pending 상태의 파드와 그 이유를 확인합니다. IAM 권한, 서브넷/보안 그룹 태그, 인스턴스 제한 등이 일반적인 문제 원인입니다. Karpenter 이벤트와 메트릭도 문제 진단에 유용합니다.
</details>

---

**점수 계산:**
- 13-15개 정답: 우수 (Karpenter 전문가 수준)
- 10-12개 정답: 양호 (실무 적용 가능)
- 7-9개 정답: 보통 (추가 학습 권장)
- 0-6개 정답: 미흡 (기본 개념 복습 필요)

[학습 자료로 돌아가기](../../autoscaling/02-karpenter.md)
