# Karpenter 퀴즈

> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 Karpenter 노드 오토스케일러의 개념, NodePool/EC2NodeClass 구성, 비용 최적화, Consolidation, Drift, 인터럽션 처리 및 Amazon EKS 통합에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 이 AWS 예제에서 Karpenter와 Cluster Autoscaler를 구분하는 아키텍처 차이는 무엇인가요?
   - A) Kubernetes 버전 요구사항이 더 높음
   - B) Auto Scaling Group 없이 직접 EC2 인스턴스를 프로비저닝
   - C) AWS만 지원하고 다른 클라우드는 지원하지 않음
   - D) CPU 기반 스케일링만 지원

<details>

<summary>정답 보기</summary>

**정답: B) Auto Scaling Group 없이 직접 EC2 인스턴스를 프로비저닝**

**설명:**
AWS 공급자 구현은 Auto Scaling Group을 확장하는 대신 NodeClaim으로 EC2 Fleet 등을 통해 EC2 용량을 요청합니다. Cluster Autoscaler는 보통 설정된 노드 그룹을 조절합니다. 인스턴스 선택은 Pod·NodePool·NodeClass 제약, 할당량과 가용 용량에 제한됩니다. API 시작 시간, Node Ready, 애플리케이션 준비는 다르며 수 초 내 완료를 보장하지 않습니다.
</details>

2. Karpenter v1 API에서 노드 프로비저닝 정책(인스턴스 유형, 용량 유형, disruption 설정)을 정의하는 CRD는 무엇인가요?
   - A) NodeClaim
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>정답 보기</summary>

**정답: B) NodePool**

**설명:**
NodePool(karpenter.sh/v1)은 템플릿 요구사항과 수명주기 정책을 정의합니다. expireAfter는 spec.template.spec, 통합·예산은 spec.disruption 아래에 있습니다. EC2NodeClass(karpenter.k8s.aws/v1)는 nodeClassRef로 AWS 설정을 제공하며 NodeClaim은 개별 노드의 요구 용량·수명주기를 추적합니다.
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
NodePool 요구사항은 spot·on-demand와 구성된 reserved 용량을 허용할 수 있습니다. In 조건의 values는 집합이므로 순서가 선호도를 뜻하지 않습니다. Karpenter는 허용된 유형 중 reserved→Spot→On-Demand 순으로 제약과 가용 제공 용량을 고려합니다. Spot 가격·중단 위험은 달라지며 비용 절감이 보장되지는 않습니다.
</details>

4. Karpenter의 Consolidation 기능이 수행하는 작업은 무엇인가요?
   - A) 여러 노드의 로그를 통합
   - B) 워크로드 제약 아래 가능한 노드 삭제 또는 더 저렴한 대체를 평가
   - C) 여러 클러스터를 하나로 통합
   - D) 여러 NodePool을 하나로 통합

<details>

<summary>정답 보기</summary>

**정답: B) 워크로드 제약 아래 가능한 노드 삭제 또는 더 저렴한 대체를 평가**

**설명:**
Consolidation은 워크로드 제약과 해당 disruption 통제 아래에서 가능한 삭제 또는 더 저렴한 대체를 찾습니다. 노드 삭제·저가 노드로 일대일 교체·다중 노드 통합이 가능하므로 노드 수가 항상 감소하지는 않습니다. WhenEmpty는 적합한 빈 노드로 제한합니다. consolidateAfter는 관련 Pod 변경 후 후보가 되기까지의 지연이며 종료 완료 기한이나 CPU 사용률 임계값이 아닙니다.
</details>

5. Karpenter의 expireAfter 설정의 목적은 무엇인가요?
   - A) 파드가 노드에서 실행될 수 있는 최대 시간
   - B) 만료에 따른 드레이닝을 시작하는 노드 나이
   - C) Karpenter 컨트롤러의 캐시 만료 시간
   - D) NodePool 정책의 유효 기간

<details>

<summary>정답 보기</summary>

**정답: B) 만료에 따른 드레이닝을 시작하는 노드 나이**

**설명:**
expireAfter는 해당 나이에 도달하면 만료 드레이닝을 시작합니다. terminationGracePeriod가 없으면 PDB·do-not-disrupt Pod가 완료를 지연시킬 수 있습니다. terminationGracePeriod를 설정하면 기한 후 남은 Pod를 강제 삭제할 수 있고 외부 인터럽션 기한도 용량을 제거할 수 있습니다. 교체는 현재 적합한 AMI·유형을 사용하며 반드시 더 새로운 것은 아닙니다. 대체 노드가 먼저 Ready가 된다고 보장하지 않습니다.
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
spec.limits는 동적 NodePool의 총 리소스를 제한합니다. cpu: "1000" 같은 문자열 수량으로 API·GitOps 형식 차이를 피할 수 있습니다. 병렬 프로비저닝 검사는 최종 일관성이므로 급격한 확장 중 초과할 수 있으며 엄격한 비용·과금 상한은 아닙니다.
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
Drift는 기존 NodeClaim을 관련 요구·해석된 설정과 비교합니다. weight·budget처럼 드리프트를 만들지 않는 변경도 있고 가변 AMI 선택자는 매니페스트 변경 없이 결과가 바뀔 수 있습니다. 처리는 disruption 통제를 따르며 모든 노드가 즉시 수렴한다고 보장하지 않습니다. v1에서는 Drift가 stable이며 이전 피처 게이트는 제거되었습니다.
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
spec.blockDeviceMappings로 EBS 디바이스를 설정합니다. AL2023 예제의 루트는 /dev/xvda이며 다른 AMI는 실제 패밀리 레이아웃을 사용해야 합니다. Bottlerocket은 별도 데이터 디바이스도 사용합니다. 크기·유형·암호화·KMS 권한을 의도한 볼륨에 맞추세요. EBS 매핑 추가만으로 파일시스템이 자동 포맷·마운트되지는 않습니다.
</details>

## 단답형 문제

9. Karpenter 확장 지연을 평가할 때 어떤 단계를 나누어 측정해야 하나요?

<details>

<summary>정답 보기</summary>

**정답: 프로비저닝과 준비 단계를 나누어 측정하며 보편적인 고정 시간은 없습니다.**

**설명:**
수요 감지·배칭, EC2 요청·용량 확보, 부팅·부트스트랩, 노드 등록·Ready, 이미지 다운로드·애플리케이션 준비를 나누어 측정하세요. IAM/API 재시도·IP 용량·스토리지·애플리케이션 초기화가 각 단계에 영향을 줍니다. 문서에는 Cluster Autoscaler 대비 보편적인 우열을 입증할 역사적 실측 시간이 없습니다.
</details>

10. Karpenter에서 여러 NodePool이 존재할 때 우선순위를 결정하는 방법은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: weight 필드를 사용한 가중치 기반 우선순위**

**설명:**
적합한 동적 NodePool에서 높은 spec.weight는 프로비저닝 선호도를 나타냅니다. 스케줄링 배치·워크로드 조건·기존 용량·NodePool 한도·제공 용량에 따라 다른 풀이 선택될 수 있습니다. Pod별 절대 보장이나 고정 Spot/On-Demand 비율이 아니며 정적 NodePool에는 별도 제약이 있습니다. 풀 내부의 용량 유형 선호도는 배열 순서와 무관합니다.
</details>

11. 노드 제거 중 자발적인 Pod eviction을 제한하는 Kubernetes 리소스는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: PDB (PodDisruptionBudget)**

**설명:**
PDB는 일치하는 정상 복제본 수에 따라 자발적 eviction을 제한합니다. 복제본을 생성하거나 비자발적인 인스턴스 손실·강제 복구·설정된 terminationGracePeriod 만료를 막지는 않습니다. minAvailable: 2는 축출 제약이며 Pod2개가 항상 실행·서비스 중이라는 보장이 아닙니다.
</details>

12. EC2NodeClass에서 Karpenter가 사용할 서브넷과 보안 그룹을 선택하는 방법은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: subnetSelectorTerms·securityGroupSelectorTerms의 지원 태그·ID 등 문서화된 선택 조건을 사용합니다.**

**설명:**
선택자는 지원 태그나 명시적 리소스 ID, 지원되는 보안 그룹 이름을 사용할 수 있습니다. 한 term 안의 조건은 AND, term 사이는 OR입니다. 선택한 AZ 안에서는 보통 여유 IP가 가장 많은 일치 서브넷을 선택합니다. 이것만으로 균등 AZ 분산이나 사설 라우팅이 보장되지는 않으므로 토폴로지 제약·경로·실제 보안 그룹을 확인하세요.
</details>

## 실습 문제

13. Spot과 On-Demand 폴백, m5/c5/r5 유형을 허용하고 빈 노드가30분 후 통합 후보가 되는 동적 NodePool을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: karpenter.sh/v1
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
        values:
        - spot
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
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
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**설명:**
Spot 선호도는 배열의 첫 번째 위치가 아닌 Karpenter 용량 유형 정책에서 나옵니다. 적합한 유형을 늘리면 선택지가 넓어질 수 있지만 가용성을 보장하지는 않습니다. WhenEmpty/consolidateAfter: 30m은 지연 후 빈 노드를 후보로 만들며 예산·PDB·조정 주기가 제거를 늦출 수 있습니다. weight: 100은 상대 선호도이고 참조하는 default EC2NodeClass와 노드 인증이 유효해야 합니다.
</details>

14. 100Gi gp3 암호화된 루트 볼륨, 특정 태그 기반 서브넷/보안 그룹 선택, IMDSv2 필수 설정을 포함하는 EC2NodeClass를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
      example.com/network-role: private
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
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
    httpPutResponseHopLimit: 1
    httpTokens: required
  tags:
    Environment: production
    ManagedBy: karpenter
```

**설명:**
AL2023 학습 예제입니다. @latest는 해석된 AMI와 드리프트를 바꿀 수 있으므로 운영 전 승인 릴리스·AMI를 고정·검증하세요. private 표시는 실제 경로를 확인한 서브넷에 미리 붙이는 사용자 정의 태그입니다. IMDSv2는 여러 메타데이터 공격 경로를 줄이지만 모든 SSRF를 막지 않습니다. 홉 제한1은 여러 비-host-network 컨테이너 경로를 제한하므로 CNI·워크로드 인증 설계와 함께 시험해야 합니다. 지정한 인스턴스 프로필·노드 접근·KMS/볼륨·네트워크 경로가 필요합니다.
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
kubectl get events --all-namespaces --sort-by='.metadata.creationTimestamp'
kubectl get nodeclaims -o wide

# 9. 노드 프로비저닝 관련 상세 로그 확인
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. 메트릭 엔드포인트 포워딩; 조회가 끝날 때까지 이 터미널을 유지합니다.
kubectl port-forward -n karpenter svc/karpenter 8080:8080
```

포워딩 준비 메시지를 확인한 뒤 다른 터미널에서:

```bash
curl --fail --show-error http://127.0.0.1:8080/metrics | grep karpenter_
```

**설명:**
컨트롤러 준비 상태, NodePool·EC2NodeClass·NodeClaim 조건, Pod 스케줄링 이벤트와 AWS 사전 조건을 함께 확인하세요. Pending이 항상 컴퓨팅 부족을 뜻하지 않으며 필터된 로그가 없다고 성공이 증명되지는 않습니다. 별도 터미널에서 port-forward를 실행하고 준비 메시지 후 다른 터미널에서 메트릭을 조회한 뒤 Ctrl+C로 종료하세요. 직접 메트릭 조회에는 Prometheus 서버가 필요하지 않으며 여기의 명령을 실제 클러스터에서 실행하지 않았습니다.
</details>

---

**점수 계산:**
- 13-15개 정답: 우수 (Karpenter 전문가 수준)
- 10-12개 정답: 양호 (실무 적용 가능)
- 7-9개 정답: 보통 (추가 학습 권장)
- 0-6개 정답: 미흡 (기본 개념 복습 필요)

[학습 자료로 돌아가기](../../autoscaling/02-karpenter.md)
