# Karpenter 퀴즈

이 퀴즈는 Karpenter 노드 오토스케일러에 대한 이해도를 테스트합니다.

## 문제 1: Karpenter 기본 개념

<details>
<summary>Karpenter란 무엇이며 기존 Cluster Autoscaler와의 차이점은?</summary>

**답변:**
Karpenter는 Kubernetes를 위한 오픈소스 노드 프로비저닝 도구입니다.

**기존 Cluster Autoscaler와의 차이점:**
- **직접 프로비저닝**: Auto Scaling Group 없이 직접 EC2 인스턴스 생성
- **빠른 스케일링**: 몇 초 내에 노드 프로비저닝
- **유연한 인스턴스 선택**: 다양한 인스턴스 타입 자동 선택
- **비용 최적화**: Spot 인스턴스 및 다양한 인스턴스 타입 활용
- **간단한 구성**: NodePool 기반 간단한 설정
</details>

## 문제 2: 핵심 구성 요소

<details>
<summary>Karpenter의 주요 구성 요소는?</summary>

**답변:**
- **NodePool**: 노드 프로비저닝 정책 정의
- **EC2NodeClass**: AWS EC2 관련 설정 (AMI, 보안 그룹 등)
- **Karpenter Controller**: 노드 라이프사이클 관리
- **Webhook**: 포드 스케줄링 최적화
- **Provisioner**: 노드 프로비저닝 로직 (v0.32 이전)
- **AWSNodeTemplate**: AWS 리소스 템플릿 (v0.32 이전)
</details>

## 문제 3: NodePool 구성

<details>
<summary>기본적인 NodePool 구성 예시는?</summary>

**답변:**
```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        karpenter.sh/nodepool: default
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge", "c5.large"]
      nodeClassRef:
        apiVersion: karpenter.k8s.aws/v1beta1
        kind: EC2NodeClass
        name: default
      taints:
        - key: example.com/special-taint
          value: special-value
          effect: NoSchedule
  limits:
    cpu: 1000
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 30s
```
</details>

## 문제 4: EC2NodeClass 구성

<details>
<summary>EC2NodeClass 구성 예시는?</summary>

**답변:**
```yaml
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"
  instanceStorePolicy: RAID0
  userData: |
    #!/bin/bash
    /etc/eks/bootstrap.sh my-cluster
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        encrypted: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required
```
</details>

## 문제 5: 비용 최적화

<details>
<summary>Karpenter를 사용한 비용 최적화 전략은?</summary>

**답변:**
1. **Spot 인스턴스 활용**:
   ```yaml
   requirements:
     - key: karpenter.sh/capacity-type
       operator: In
       values: ["spot"]
   ```

2. **다양한 인스턴스 타입 허용**:
   ```yaml
   requirements:
     - key: node.kubernetes.io/instance-type
       operator: In
       values: ["m5.large", "m5.xlarge", "c5.large", "c5.xlarge"]
   ```

3. **통합 정책 활용**:
   ```yaml
   disruption:
     consolidationPolicy: WhenUnderutilized
     consolidateAfter: 30s
   ```

4. **적절한 리소스 제한**:
   ```yaml
   limits:
     cpu: 1000
     memory: 1000Gi
   ```
</details>

## 문제 6: 모니터링 및 문제 해결

<details>
<summary>Karpenter의 상태를 모니터링하고 문제를 해결하는 방법은?</summary>

**답변:**
1. **NodePool 상태 확인**:
   ```bash
   kubectl get nodepool
   kubectl describe nodepool default
   ```

2. **노드 상태 확인**:
   ```bash
   kubectl get nodes -l karpenter.sh/nodepool=default
   kubectl describe node <node-name>
   ```

3. **Karpenter 로그 확인**:
   ```bash
   kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter
   ```

4. **이벤트 모니터링**:
   ```bash
   kubectl get events --field-selector source=karpenter
   ```

5. **메트릭 확인**:
   - `karpenter_nodes_created_total`
   - `karpenter_nodes_terminated_total`
   - `karpenter_provisioner_scheduling_duration_seconds`

6. **일반적인 문제 해결**:
   - IAM 권한 확인
   - 서브넷 및 보안 그룹 태그 확인
   - 인스턴스 제한 확인
   - 리소스 요청 검토
</details>

---

**점수 계산:**
- 5-6개 정답: 우수 (Karpenter 전문가 수준)
- 3-4개 정답: 양호 (추가 학습 권장)
- 1-2개 정답: 보통 (기본 개념 복습 필요)
- 0개 정답: 미흡 (전체 내용 재학습 필요)
