# Amazon EKS 클러스터 생성 퀴즈 (Part 4)

이 퀴즈는 Amazon EKS 클러스터 생성과 관련된 고급 구성, 확장성, 그리고 운영 관련 주제에 대한 이해를 테스트합니다. 클러스터 확장, 자동화, 비용 최적화, 그리고 운영 모범 사례 등의 주제를 다룹니다.

## 기본 개념 문제

1. Amazon EKS 클러스터에서 Cluster Autoscaler와 Karpenter의 주요 차이점은 무엇인가요?
   - A) Cluster Autoscaler는 AWS 서비스이고, Karpenter는 오픈 소스 도구이다
   - B) Cluster Autoscaler는 노드 그룹 단위로 확장하고, Karpenter는 워크로드 요구 사항에 맞는 개별 노드를 프로비저닝한다
   - C) Cluster Autoscaler는 CPU/메모리 사용량에 기반하여 확장하고, Karpenter는 포드 수에 기반하여 확장한다
   - D) Cluster Autoscaler는 수평적 확장만 지원하고, Karpenter는 수직적 확장도 지원한다
   
<details>
<summary>정답 보기</summary>

**정답: B) Cluster Autoscaler는 노드 그룹 단위로 확장하고, Karpenter는 워크로드 요구 사항에 맞는 개별 노드를 프로비저닝한다**

**설명:**
Amazon EKS 클러스터에서 Cluster Autoscaler와 Karpenter의 주요 차이점은 확장 방식에 있습니다. Cluster Autoscaler는 기존 Auto Scaling 그룹(ASG)을 기반으로 노드 그룹 단위로 확장하는 반면, Karpenter는 워크로드 요구 사항에 맞는 개별 노드를 직접 프로비저닝합니다.

#### Cluster Autoscaler의 특징:

1. **노드 그룹 기반 확장**:
   - 미리 정의된 Auto Scaling 그룹을 사용하여 확장
   - 노드 그룹 내에서 동일한 인스턴스 유형 또는 혼합 인스턴스 유형 사용
   - 예시:
     ```yaml
     # Cluster Autoscaler 배포
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: cluster-autoscaler
       namespace: kube-system
     spec:
       replicas: 1
       selector:
         matchLabels:
           app: cluster-autoscaler
       template:
         metadata:
           labels:
             app: cluster-autoscaler
         spec:
           containers:
           - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
             name: cluster-autoscaler
             command:
             - ./cluster-autoscaler
             - --v=4
             - --stderrthreshold=info
             - --cloud-provider=aws
             - --skip-nodes-with-local-storage=false
             - --expander=least-waste
             - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
     ```

2. **작동 방식**:
   - 스케줄링할 수 없는 포드가 있을 때 노드 그룹 확장
   - 노드 활용도가 낮을 때 노드 그룹 축소
   - ASG의 최소/최대 크기 내에서 작동

3. **제한 사항**:
   - 확장 속도가 상대적으로 느림 (2-10분)
   - 미리 정의된 인스턴스 유형으로 제한
   - 노드 그룹 단위로만 확장 가능

#### Karpenter의 특징:

1. **워크로드 기반 프로비저닝**:
   - 워크로드 요구 사항에 맞는 최적의 인스턴스 유형 선택
   - ASG 없이 EC2 인스턴스를 직접 프로비저닝
   - 예시:
     ```yaml
     # Karpenter Provisioner
     apiVersion: karpenter.sh/v1alpha5
     kind: Provisioner
     metadata:
       name: default
     spec:
       requirements:
         - key: karpenter.sh/capacity-type
           operator: In
           values: ["spot", "on-demand"]
         - key: kubernetes.io/arch
           operator: In
           values: ["amd64", "arm64"]
         - key: node.kubernetes.io/instance-type
           operator: In
           values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
       limits:
         resources:
           cpu: 1000
           memory: 1000Gi
       provider:
         subnetSelector:
           karpenter.sh/discovery: "true"
         securityGroupSelector:
           karpenter.sh/discovery: "true"
       ttlSecondsAfterEmpty: 30
     ```

2. **작동 방식**:
   - 스케줄링할 수 없는 포드의 요구 사항을 분석
   - 요구 사항에 맞는 최적의 인스턴스 유형 선택
   - 인스턴스를 직접 프로비저닝하고 포드 스케줄링
   - 노드가 비어 있으면 자동으로 종료

3. **장점**:
   - 빠른 확장 속도 (1분 이내)
   - 워크로드에 최적화된 인스턴스 유형 선택
   - 비용 최적화 (Spot 인스턴스 활용, 적절한 크기 선택)
   - 간소화된 구성 (ASG 관리 불필요)

#### 두 도구의 비교:

| 특성 | Cluster Autoscaler | Karpenter |
|------|-------------------|-----------|
| 확장 단위 | 노드 그룹 (ASG) | 개별 노드 |
| 인스턴스 선택 | 미리 정의된 인스턴스 유형 | 워크로드 요구 사항에 맞는 최적의 인스턴스 |
| 확장 속도 | 느림 (2-10분) | 빠름 (1분 이내) |
| 구성 복잡성 | 중간 (ASG 구성 필요) | 낮음 (Provisioner 정의만 필요) |
| 비용 최적화 | 제한적 | 높음 (워크로드에 최적화된 인스턴스 선택) |
| 성숙도 | 높음 (오래된 프로젝트) | 중간 (비교적 새로운 프로젝트) |

#### 다른 옵션들의 문제점:

- **Cluster Autoscaler는 AWS 서비스이고, Karpenter는 오픈 소스 도구이다**: 둘 다 오픈 소스 도구입니다. Cluster Autoscaler는 Kubernetes SIG Autoscaling에서 관리하고, Karpenter는 AWS에서 시작했지만 오픈 소스 프로젝트입니다.

- **Cluster Autoscaler는 CPU/메모리 사용량에 기반하여 확장하고, Karpenter는 포드 수에 기반하여 확장한다**: 둘 다 기본적으로 스케줄링할 수 없는 포드(Pending 상태)를 기반으로 확장합니다. CPU/메모리 사용량 기반 확장은 Horizontal Pod Autoscaler(HPA)의 역할입니다.

- **Cluster Autoscaler는 수평적 확장만 지원하고, Karpenter는 수직적 확장도 지원한다**: 둘 다 수평적 확장(노드 수 증가)만 지원합니다. 수직적 확장(노드의 리소스 증가)은 지원하지 않습니다. 포드 수준의 수직적 확장은 Vertical Pod Autoscaler(VPA)의 역할입니다.

Cluster Autoscaler와 Karpenter는 모두 EKS 클러스터의 자동 확장을 위한 도구이지만, Karpenter는 더 빠르고 유연한 확장을 제공하며 워크로드 요구 사항에 맞는 최적의 인스턴스를 선택할 수 있는 장점이 있습니다.
</details>

2. Amazon EKS 클러스터에서 노드 그룹을 생성할 때 사용할 수 있는 용량 유형(capacity type)으로 올바른 것은 무엇인가요?
   - A) Reserved, On-Demand, Spot
   - B) On-Demand, Spot, Dedicated
   - C) On-Demand, Spot
   - D) Standard, Burstable, Compute-Optimized

<details>
<summary>정답 보기</summary>

**정답: C) On-Demand, Spot**

**설명:**
Amazon EKS 노드 그룹을 생성할 때 사용할 수 있는 용량 유형은 On-Demand와 Spot 두 가지입니다.

#### On-Demand 용량 유형:
- **특징**: 중단 없이 안정적으로 사용 가능한 인스턴스
- **가격**: 정해진 시간당 요금 지불
- **적합한 워크로드**: 
  - 중단에 민감한 프로덕션 애플리케이션
  - 상태 저장(stateful) 워크로드
  - 데이터베이스
  - 중요한 비즈니스 애플리케이션

#### Spot 용량 유형:
- **특징**: AWS의 여유 용량을 활용하며, AWS가 용량을 회수할 때 중단될 수 있음
- **가격**: On-Demand 대비 최대 90% 할인된 가격
- **적합한 워크로드**:
  - 내결함성이 있는 애플리케이션
  - 상태 비저장(stateless) 워크로드
  - 배치 처리 작업
  - 개발/테스트 환경

#### EKS 노드 그룹 생성 시 용량 유형 지정 예시:

AWS CLI를 사용한 예시:
```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-spot-nodegroup \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --instance-types t3.medium t3a.medium \
  --capacity-type SPOT \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole
```

eksctl을 사용한 예시:
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: ng-on-demand
    instanceType: m5.large
    desiredCapacity: 3
    capacityType: ON_DEMAND
  - name: ng-spot
    instanceType: m5.large
    desiredCapacity: 2
    capacityType: SPOT
    spotInstancePools: 3
```

#### 다른 옵션들의 문제점:

- **Reserved, On-Demand, Spot**: "Reserved"는 EC2 예약 인스턴스를 의미하지만, EKS 노드 그룹 생성 시 직접적인 용량 유형으로 지정할 수 없습니다. 예약 인스턴스는 결제 할인 모델이며, 노드 그룹의 용량 유형으로 직접 선택할 수 없습니다.

- **On-Demand, Spot, Dedicated**: "Dedicated"는 EC2 전용 인스턴스를 의미하지만, EKS 노드 그룹의 용량 유형으로 직접 지정할 수 없습니다. 전용 인스턴스는 별도의 테넌시 설정을 통해 구성할 수 있습니다.

- **Standard, Burstable, Compute-Optimized**: 이는 EC2 인스턴스 패밀리 유형을 나타내며, 용량 유형이 아닙니다. 인스턴스 유형(예: t3.medium, m5.large, c5.xlarge 등)을 선택할 때 고려하는 특성입니다.

#### 모범 사례:

1. **혼합 용량 전략 사용**:
   - 중요한 워크로드는 On-Demand 노드 그룹에 배치
   - 내결함성이 있는 워크로드는 Spot 노드 그룹에 배치
   - 노드 선호도와 허용 오차(tolerations)를 사용하여 워크로드 배치 제어

2. **Spot 인스턴스 사용 시 고려사항**:
   - 다양한 인스턴스 유형 지정 (중단 위험 분산)
   - 적절한 중단 처리 메커니즘 구현 (Pod Disruption Budgets, 정상 종료 훅)
   - AWS Node Termination Handler 배포

3. **비용 최적화**:
   - Savings Plans 또는 예약 인스턴스를 On-Demand 노드에 적용
   - Graviton(ARM) 인스턴스 고려
   - 적절한 인스턴스 크기 선택
</details>

3. Amazon EKS 클러스터에서 Fargate 프로필을 구성할 때 필수적으로 지정해야 하는 항목은 무엇인가요?
   - A) 인스턴스 유형과 용량 유형
   - B) 네임스페이스와 레이블 선택기
   - C) 서브넷 ID와 보안 그룹
   - D) 오토스케일링 설정과 최대 파드 수

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스와 레이블 선택기**

**설명:**
Amazon EKS Fargate 프로필을 구성할 때 필수적으로 지정해야 하는 항목은 네임스페이스와 선택적으로 레이블 선택기입니다. 이 정보를 통해 EKS는 어떤 파드가 Fargate에서 실행되어야 하는지 결정합니다.

#### Fargate 프로필의 구성 요소:

1. **필수 구성 요소**:
   - **프로필 이름**: Fargate 프로필의 고유 식별자
   - **파드 실행 역할(Pod execution role)**: Fargate 인프라에서 파드를 실행하는 데 필요한 IAM 역할
   - **서브넷**: Fargate 파드가 실행될 프라이빗 서브넷 (기본적으로 클러스터의 서브넷 사용)
   - **선택기**: 네임스페이스와 선택적 레이블로 구성된 배열

2. **선택기 구성**:
   - **네임스페이스**: 파드가 속한 Kubernetes 네임스페이스 (필수)
   - **레이블**: 키-값 쌍의 Kubernetes 레이블 (선택 사항)

#### Fargate 프로필 생성 예시:

AWS CLI를 사용한 예시:
```bash
aws eks create-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/AmazonEKSFargatePodExecutionRole \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --selectors namespace=default,labels={app=nginx} namespace=kube-system,labels={k8s-app=kube-dns}
```

eksctl을 사용한 예시:
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: fp-default
    selectors:
      - namespace: default
        labels:
          app: nginx
      - namespace: kube-system
        labels:
          k8s-app: kube-dns
```

#### Fargate 프로필 작동 방식:

1. 파드가 생성되면 EKS는 파드의 네임스페이스와 레이블을 확인합니다.
2. 파드의 네임스페이스와 레이블이 Fargate 프로필의 선택기와 일치하면, 해당 파드는 Fargate 인프라에서 실행됩니다.
3. 일치하는 Fargate 프로필이 없으면, 파드는 EC2 노드에 스케줄링되거나 (EC2 노드가 있는 경우) 스케줄링되지 않고 Pending 상태로 남습니다.

#### 다른 옵션들의 문제점:

- **인스턴스 유형과 용량 유형**: Fargate는 서버리스 컴퓨팅 서비스이므로 인스턴스 유형이나 용량 유형을 지정할 필요가 없습니다. AWS가 자동으로 필요한 컴퓨팅 리소스를 프로비저닝합니다.

- **서브넷 ID와 보안 그룹**: 서브넷 ID는 필요하지만, 클러스터의 서브넷을 기본값으로 사용할 수 있습니다. 보안 그룹은 선택 사항이며, 지정하지 않으면 클러스터의 보안 그룹이 사용됩니다.

- **오토스케일링 설정과 최대 파드 수**: Fargate는 파드 단위로 자동으로 확장되므로 별도의 오토스케일링 설정이 필요하지 않습니다. 파드 수는 Kubernetes Deployment나 HPA(Horizontal Pod Autoscaler)를 통해 관리됩니다.

#### Fargate 사용 시 고려사항:

1. **비용**: Fargate는 실제 사용한 vCPU와 메모리 리소스에 대해서만 비용을 지불합니다. 유휴 노드에 대한 비용이 없습니다.

2. **제한 사항**:
   - DaemonSet 파드는 Fargate에서 지원되지 않습니다.
   - 특권(privileged) 컨테이너는 지원되지 않습니다.
   - HostNetwork, HostPort 등 호스트 네트워크 모드는 지원되지 않습니다.
   - 영구 볼륨은 Amazon EFS만 지원됩니다.

3. **사용 사례**:
   - 배치 처리 작업
   - 웹 애플리케이션
   - API 서버
   - 마이크로서비스
   - 개발/테스트 환경
</details>

4. Amazon EKS 클러스터에서 노드 그룹을 업데이트할 때 "업데이트 구성(update configuration)"에서 설정할 수 있는 항목이 아닌 것은?
   - A) 최대 사용 불가능(maxUnavailable) 노드 수
   - B) 최대 사용 불가능(maxUnavailable) 노드 비율
   - C) 노드 교체 전략(replacement strategy)
   - D) 노드 그룹 업데이트 타임아웃

<details>
<summary>정답 보기</summary>

**정답: C) 노드 교체 전략(replacement strategy)**

**설명:**
Amazon EKS 노드 그룹 업데이트 구성에서 "노드 교체 전략(replacement strategy)"은 공식적인 설정 항목이 아닙니다. EKS 관리형 노드 그룹은 기본적으로 롤링 업데이트 방식을 사용하며, 이 전략을 직접 변경할 수 있는 옵션은 제공하지 않습니다.

#### EKS 노드 그룹 업데이트 구성에서 설정할 수 있는 항목:

1. **maxUnavailable**:
   - 업데이트 중 동시에 사용할 수 없는 최대 노드 수
   - 절대 수치(예: 1, 2, 3) 또는 비율(예: 20%)로 지정 가능
   - 기본값: 1

2. **maxUnavailablePercentage**:
   - 업데이트 중 동시에 사용할 수 없는 최대 노드 비율
   - 1에서 100 사이의 값으로 지정
   - `maxUnavailable`과 함께 사용할 수 없음

3. **force**:
   - 노드 그룹 업데이트를 강제로 진행할지 여부
   - 기본값: false

4. **타임아웃**:
   - 노드 그룹 업데이트 작업의 최대 대기 시간
   - 기본값: 60분

#### 노드 그룹 업데이트 구성 예시:

AWS CLI를 사용한 예시:
```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailable=2
```

또는 비율로 지정:
```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailablePercentage=20
```

eksctl을 사용한 예시:
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: my-nodegroup
    updateConfig:
      maxUnavailable: 2
```

#### 노드 그룹 업데이트 프로세스:

1. **업데이트 시작**: AWS는 노드 그룹의 업데이트를 시작합니다.
2. **노드 드레이닝**: `maxUnavailable` 설정에 따라 지정된 수의 노드를 코든(cordon)하고 드레인(drain)합니다.
3. **노드 종료**: 드레인된 노드를 종료합니다.
4. **새 노드 생성**: 새로운 구성으로 노드를 생성합니다.
5. **반복**: 모든 노드가 업데이트될 때까지 2-4단계를 반복합니다.

#### 다른 옵션들의 설명:

- **최대 사용 불가능(maxUnavailable) 노드 수**: 업데이트 중 동시에 사용할 수 없는 최대 노드 수를 지정하는 유효한 설정입니다.

- **최대 사용 불가능(maxUnavailable) 노드 비율**: 업데이트 중 동시에 사용할 수 없는 최대 노드 비율을 지정하는 유효한 설정입니다.

- **노드 그룹 업데이트 타임아웃**: 노드 그룹 업데이트 작업의 최대 대기 시간을 지정하는 유효한 설정입니다.

#### 노드 그룹 업데이트 모범 사례:

1. **적절한 maxUnavailable 값 설정**:
   - 너무 작으면 업데이트 시간이 길어집니다.
   - 너무 크면 애플리케이션 가용성에 영향을 줄 수 있습니다.
   - 워크로드 특성과 노드 그룹 크기를 고려하여 설정합니다.

2. **파드 중단 예산(PDB) 구성**:
   - 중요한 워크로드에 대해 PDB를 설정하여 최소한의 가용성을 보장합니다.
   - 예시:
     ```yaml
     apiVersion: policy/v1
     kind: PodDisruptionBudget
     metadata:
       name: app-pdb
     spec:
       minAvailable: 2  # 또는 maxUnavailable: 1
       selector:
         matchLabels:
           app: my-app
     ```

3. **업데이트 전 테스트**:
   - 중요한 업데이트 전에 테스트 환경에서 먼저 검증합니다.
   - 롤백 계획을 준비합니다.

4. **모니터링**:
   - 업데이트 중 애플리케이션 상태를 모니터링합니다.
   - 문제가 발생하면 업데이트를 일시 중지하거나 롤백합니다.
</details>

5. EKS 클러스터에서 Kubernetes 버전 업그레이드 시 "건너뛰기(skipping)" 버전에 대한 설명으로 올바른 것은?
   - A) 마이너 버전은 건너뛸 수 있지만, 메이저 버전은 건너뛸 수 없다
   - B) 메이저 버전은 건너뛸 수 있지만, 마이너 버전은 건너뛸 수 없다
   - C) 메이저 버전과 마이너 버전 모두 건너뛸 수 없다
   - D) 메이저 버전과 마이너 버전 모두 건너뛸 수 있다

<details>
<summary>정답 보기</summary>

**정답: C) 메이저 버전과 마이너 버전 모두 건너뛸 수 없다**

**설명:**
Amazon EKS 클러스터 업그레이드 시, 메이저 버전과 마이너 버전 모두 순차적으로 업그레이드해야 합니다. 버전을 건너뛰는 것은 지원되지 않습니다.

#### EKS 버전 업그레이드 규칙:

1. **순차적 업그레이드 필요**:
   - 각 Kubernetes 버전은 이전 버전에서 순차적으로 업그레이드해야 합니다.
   - 예: 1.22 → 1.23 → 1.24 (1.22에서 1.24로 직접 업그레이드 불가)

2. **지원되는 업그레이드 경로**:
   - 현재 버전에서 다음 마이너 버전으로만 업그레이드 가능
   - 메이저 버전도 순차적으로 업그레이드해야 함

3. **컨트롤 플레인과 노드 버전 차이**:
   - 컨트롤 플레인은 노드보다 최대 2개의 마이너 버전까지 앞설 수 있음
   - 노드는 컨트롤 플레인보다 최대 1개의 마이너 버전까지 앞설 수 있음

#### EKS 버전 업그레이드 프로세스:

1. **업그레이드 계획 수립**:
   - 현재 버전과 대상 버전 간의 변경 사항 검토
   - 애플리케이션 호환성 확인
   - 업그레이드 일정 및 롤백 계획 수립

2. **권장 업그레이드 순서**:
   - 컨트롤 플레인 업그레이드
   - 애드온 업그레이드 (CoreDNS, kube-proxy, VPC CNI 등)
   - 노드 그룹 업그레이드

3. **업그레이드 명령 예시**:

   AWS CLI를 사용한 컨트롤 플레인 업그레이드:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.24
   ```

   eksctl을 사용한 컨트롤 플레인 업그레이드:
   ```bash
   eksctl upgrade cluster \
     --name=my-cluster \
     --version=1.24 \
     --approve
   ```

   노드 그룹 업그레이드:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

#### EKS 버전 지원 정책:

1. **지원 기간**:
   - 각 Kubernetes 버전은 EKS에서 출시 후 약 14개월 동안 지원됩니다.
   - AWS는 최소 4개의 프로덕션 Kubernetes 버전을 항상 지원합니다.

2. **지원 종료 알림**:
   - AWS는 버전 지원 종료 약 60일 전에 공지합니다.
   - 지원 종료 후에도 클러스터는 계속 작동하지만, 보안 패치나 버그 수정을 받지 못합니다.

3. **버전 출시 주기**:
   - AWS는 일반적으로 업스트림 Kubernetes 릴리스 후 2-3개월 내에 EKS에서 새 버전을 지원합니다.

#### 업그레이드 모범 사례:

1. **테스트 환경에서 먼저 업그레이드**:
   - 프로덕션 환경 업그레이드 전에 테스트 클러스터에서 검증

2. **업그레이드 전 백업**:
   - etcd 백업 및 중요 리소스의 YAML 백업

3. **점진적 업그레이드**:
   - 한 번에 모든 노드 그룹을 업그레이드하지 않고 점진적으로 진행

4. **업그레이드 후 검증**:
   - 워크로드 정상 작동 확인
   - 모니터링 시스템 확인
   - 로그 검토

5. **최신 버전 유지**:
   - 정기적인 업그레이드 일정 수립
   - 지원 종료 날짜 추적

#### 다른 옵션들의 문제점:

- **마이너 버전은 건너뛸 수 있지만, 메이저 버전은 건너뛸 수 없다**: 마이너 버전도 건너뛸 수 없습니다. 순차적으로 업그레이드해야 합니다.

- **메이저 버전은 건너뛸 수 있지만, 마이너 버전은 건너뛸 수 없다**: 메이저 버전도 건너뛸 수 없습니다. 순차적으로 업그레이드해야 합니다.

- **메이저 버전과 마이너 버전 모두 건너뛸 수 있다**: EKS에서는 버전을 건너뛰는 것이 지원되지 않습니다.
</details>

## 단답형 문제

6. EKS 클러스터에서 노드 그룹의 인스턴스 유형을 변경하려면 어떤 작업이 필요한가요?

<details>
<summary>정답 및 설명</summary>

EKS 관리형 노드 그룹의 인스턴스 유형을 변경하려면 새로운 노드 그룹을 생성하고 워크로드를 마이그레이션한 후 기존 노드 그룹을 삭제해야 합니다. 관리형 노드 그룹의 인스턴스 유형은 생성 후 직접 변경할 수 없습니다.

대략적인 절차는 다음과 같습니다:
1. 원하는 인스턴스 유형으로 새 노드 그룹 생성
2. 필요한 경우 파드 중단 예산(PDB) 설정
3. 기존 노드에 cordon 및 drain 적용하여 워크로드를 새 노드로 마이그레이션
4. 모든 워크로드가 새 노드 그룹으로 이동했는지 확인
5. 기존 노드 그룹 삭제

자체 관리형 노드 그룹을 사용하는 경우 Auto Scaling 그룹의 시작 템플릿을 업데이트하고 인스턴스 새로 고침을 수행할 수 있습니다.
</details>

7. EKS 클러스터에서 Kubernetes API 서버에 대한 퍼블릭 액세스를 비활성화하고 프라이빗 액세스만 허용하려면 어떤 설정을 변경해야 하나요?

<details>
<summary>정답 및 설명</summary>

EKS 클러스터의 API 서버에 대한 퍼블릭 액세스를 비활성화하고 프라이빗 액세스만 허용하려면 클러스터의 엔드포인트 액세스 설정을 변경해야 합니다:

1. AWS Management Console에서:
   - EKS 콘솔로 이동
   - 해당 클러스터 선택
   - "네트워킹" 탭 선택
   - "클러스터 엔드포인트 액세스" 섹션에서 "편집" 클릭
   - "프라이빗"으로 설정 (퍼블릭 액세스 비활성화, 프라이빗 액세스 활성화)

2. AWS CLI를 사용하는 경우:
```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

이 설정을 변경하면 VPC 내부에서만 Kubernetes API 서버에 액세스할 수 있게 됩니다. 따라서 VPC 내에 있는 시스템이나 VPC와 연결된 네트워크에서만 클러스터를 관리할 수 있습니다.
</details>

8. EKS 클러스터에서 사용할 수 있는 Kubernetes 버전의 지원 기간은 일반적으로 얼마인가요?

<details>
<summary>정답 및 설명</summary>

Amazon EKS에서 각 Kubernetes 버전은 일반적으로 출시 후 약 14개월 동안 지원됩니다. AWS는 최소 4개의 프로덕션 Kubernetes 버전을 항상 지원하려고 노력합니다.

EKS의 버전 지원 주기는 다음과 같습니다:
1. 초기 릴리스: AWS가 새 Kubernetes 버전을 EKS에서 사용할 수 있도록 함
2. 표준 지원: 약 14개월 동안 보안 패치 및 버그 수정 제공
3. 지원 종료 발표: AWS는 버전 지원 종료 약 60일 전에 공지
4. 지원 종료: 지원이 종료된 버전에서 실행 중인 클러스터는 자동으로 업그레이드되지 않지만, 수동으로 업그레이드해야 함

AWS는 Kubernetes 커뮤니티 릴리스보다 약간 늦게 새 버전을 지원하기 시작하지만, 지원 기간은 일반적으로 더 깁니다. 업스트림 Kubernetes 프로젝트는 약 9개월 동안 각 버전을 지원하는 반면, EKS는 약 14개월 동안 지원합니다.
</details>
