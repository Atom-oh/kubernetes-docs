# EKS 클러스터 생성 퀴즈 - Part 5

이 퀴즈는 Amazon EKS 클러스터의 고급 구성, 최적화 및 운영 모범 사례에 대한 이해를 테스트합니다. 비용 최적화, 고가용성 설계, 보안 강화 및 운영 자동화에 중점을 둡니다.

## 객관식 문제

### 1. Amazon EKS 클러스터에서 비용을 최적화하기 위한 가장 효과적인 방법은 무엇인가요?

A. 모든 워커 노드를 온디맨드 인스턴스로 실행\
B. 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용\
C. 모든 워커 노드를 예약 인스턴스로 실행\
D. 모든 워커 노드를 Fargate로 실행

<details>

<summary>정답 및 설명</summary>

**정답: B. 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용**

**설명:** EKS 클러스터에서 비용을 최적화하는 가장 효과적인 방법은 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용하는 것입니다:

* **스팟 인스턴스**: 온디맨드 가격보다 최대 90% 저렴하지만 AWS가 용량을 회수할 수 있어 중단될 가능성이 있습니다. 내결함성이 있는 상태 비저장(stateless) 워크로드에 적합합니다.
* **온디맨드 인스턴스**: 가격은 높지만 안정적이므로 중요한 상태 저장(stateful) 워크로드나 중단에 민감한 애플리케이션에 적합합니다.

이러한 혼합 접근 방식을 통해:

1. 중요한 워크로드는 온디맨드 인스턴스에서 실행
2. 내결함성이 있는 워크로드는 스팟 인스턴스에서 실행
3. 노드 선호도, 허용 오차(tolerations), 테인트(taints)를 사용하여 워크로드 배치 제어

추가적인 비용 최적화 전략으로는 Karpenter나 Cluster Autoscaler를 사용한 자동 스케일링, 적절한 인스턴스 크기 선택, Graviton(ARM) 인스턴스 사용, 예약 인스턴스 또는 Savings Plans 활용 등이 있습니다.

</details>

### 2. EKS 클러스터에서 여러 가용 영역(AZ)에 노드를 배포하는 주된 이유는 무엇인가요?

A. 네트워크 지연 시간 감소\
B. 데이터 처리량 증가\
C. 고가용성 및 내결함성 향상\
D. AWS 리전 간 데이터 복제 활성화

<details>

<summary>정답 및 설명</summary>

**정답: C. 고가용성 및 내결함성 향상**

**설명:** EKS 클러스터에서 여러 가용 영역(AZ)에 노드를 배포하는 주된 이유는 고가용성 및 내결함성을 향상시키기 위함입니다:

1. **가용 영역 장애 대응**: 한 가용 영역에 장애가 발생해도 다른 가용 영역의 노드는 계속 작동하므로 애플리케이션 가용성이 유지됩니다.
2. **인프라 이중화**: 여러 AZ에 걸쳐 워크로드를 분산함으로써 물리적 인프라 장애에 대한 보호 계층을 추가합니다.
3. **자동 복구**: Kubernetes는 장애가 발생한 노드의 파드를 정상 노드로 자동 재스케줄링하여 서비스 중단을 최소화합니다.
4. **롤링 업데이트 안정성**: 업데이트 중에도 여러 AZ에 걸쳐 워크로드가 분산되어 있어 가용성이 유지됩니다.

EKS는 기본적으로 컨트롤 플레인을 여러 AZ에 배포하지만, 워커 노드도 여러 AZ에 배포하여 전체 클러스터의 고가용성을 보장하는 것이 모범 사례입니다. 이를 위해 노드 그룹 생성 시 여러 서브넷(각각 다른 AZ에 위치)을 지정할 수 있습니다.

</details>

### 3. EKS 클러스터에서 파드 네트워킹을 위한 기본 CNI 플러그인은 무엇인가요?

A. Calico\
B. Flannel\
C. Amazon VPC CNI\
D. Weave Net

<details>

<summary>정답 및 설명</summary>

**정답: C. Amazon VPC CNI**

**설명:** Amazon EKS 클러스터에서 파드 네트워킹을 위한 기본 CNI(Container Network Interface) 플러그인은 Amazon VPC CNI입니다. 이 플러그인의 주요 특징은 다음과 같습니다:

1. **네이티브 VPC 네트워킹**: 각 파드는 VPC 내에서 고유한 IP 주소를 받아 AWS VPC 네트워킹을 직접 활용합니다.
2. **보안 그룹 통합**: 파드 수준에서 AWS 보안 그룹을 적용할 수 있어 세밀한 네트워크 보안 제어가 가능합니다.
3. **IP 주소 관리**: 각 노드는 VPC 서브넷에서 보조 IP 주소를 할당받아 파드에 제공합니다.
4. **성능**: 오버레이 네트워크를 사용하지 않아 네트워크 성능이 향상됩니다.
5. **AWS 서비스 통합**: AWS Load Balancer Controller, AWS App Mesh 등 다른 AWS 서비스와 원활하게 통합됩니다.

Amazon VPC CNI는 오픈 소스이며 GitHub에서 관리됩니다. 필요에 따라 Calico, Cilium 등 다른 CNI 플러그인으로 대체할 수 있지만, Amazon VPC CNI가 EKS의 기본 옵션이며 AWS에서 공식적으로 지원합니다.

</details>

### 4. EKS 클러스터에서 IAM 역할을 Kubernetes 서비스 계정에 연결하는 기능의 이름은 무엇인가요?

A. IAM for Service Accounts (IRSA)\
B. Pod Identity Webhook\
C. Kubernetes IAM Authenticator\
D. EKS Identity Manager

<details>

<summary>정답 및 설명</summary>

**정답: A. IAM for Service Accounts (IRSA)**

**설명:** EKS 클러스터에서 IAM 역할을 Kubernetes 서비스 계정에 연결하는 기능은 IAM for Service Accounts(IRSA)입니다. 이 기능의 주요 특징은 다음과 같습니다:

1. **세분화된 권한 제어**: 파드 수준에서 AWS 리소스에 대한 액세스를 제어할 수 있어, 노드 수준의 광범위한 권한 부여를 방지합니다.
2. **OIDC 기반 인증**: EKS는 OpenID Connect(OIDC) 제공자를 사용하여 Kubernetes 서비스 계정과 IAM 역할 간의 신뢰 관계를 설정합니다.
3. **보안 강화**: 애플리케이션별로 필요한 최소 권한만 부여하는 최소 권한 원칙을 구현할 수 있습니다.
4. **구현 방식**:
   * EKS 클러스터에 대한 OIDC 제공자 생성
   * 서비스 계정을 신뢰하는 IAM 역할 생성
   * 특정 주석(annotation)이 있는 Kubernetes 서비스 계정 생성
   * 해당 서비스 계정을 사용하는 파드 배포

IRSA를 사용하면 AWS SDK를 사용하는 애플리케이션이 노드의 IAM 역할에 의존하지 않고 자체 IAM 역할을 사용하여 AWS 서비스에 안전하게 액세스할 수 있습니다.

</details>

### 5. EKS 클러스터에서 노드 그룹의 Auto Scaling을 관리하는 Kubernetes 네이티브 도구는 무엇인가요?

A. Horizontal Pod Autoscaler\
B. Vertical Pod Autoscaler\
C. Cluster Autoscaler\
D. Node Autoscaler

<details>

<summary>정답 및 설명</summary>

**정답: C. Cluster Autoscaler**

**설명:** EKS 클러스터에서 노드 그룹의 Auto Scaling을 관리하는 Kubernetes 네이티브 도구는 Cluster Autoscaler입니다. 이 도구의 주요 특징은 다음과 같습니다:

1. **자동 스케일링**: 파드가 리소스 부족으로 스케줄링되지 못할 때 노드를 자동으로 추가하고, 노드가 충분히 활용되지 않을 때 노드를 제거합니다.
2. **AWS Auto Scaling 그룹 통합**: EKS에서는 AWS Auto Scaling 그룹과 통합되어 작동합니다.
3. **작동 방식**:
   * 스케일 아웃: 파드가 리소스 제약으로 Pending 상태일 때 노드 추가
   * 스케일 인: 노드의 활용도가 낮고 파드를 다른 노드로 이동할 수 있을 때 노드 제거
4. **구성 옵션**:
   * 스케일 업/다운 임계값 설정
   * 노드 그룹 검색 방법 지정
   * 스케일 다운 지연 설정
   * 파드 중단 예산(PDB) 존중

Horizontal Pod Autoscaler(HPA)는 파드 수를 자동으로 조정하고, Vertical Pod Autoscaler(VPA)는 파드의 리소스 요청을 자동으로 조정하지만, 노드 수를 조정하는 것은 Cluster Autoscaler의 역할입니다.

참고로, AWS에서는 Cluster Autoscaler 외에도 Karpenter라는 새로운 노드 프로비저닝 도구를 제공하며, 이는 더 빠르고 유연한 노드 프로비저닝 기능을 제공합니다.

</details>

## 단답형 문제

### 6. EKS 클러스터에서 Kubernetes 컨트롤 플레인 로그를 활성화하고 CloudWatch Logs로 전송하려면 어떤 구성이 필요한가요?

<details>

<summary>정답 및 설명</summary>

EKS 클러스터에서 Kubernetes 컨트롤 플레인 로그를 CloudWatch Logs로 전송하려면 클러스터 생성 시 또는 기존 클러스터에서 특정 로그 유형을 활성화해야 합니다.

**필요한 구성:**

1. **로그 유형 활성화**: 다음 로그 유형 중 하나 이상을 활성화해야 합니다:
   * `api`: Kubernetes API 서버 로그
   * `audit`: Kubernetes 감사 로그
   * `authenticator`: AWS IAM 인증기 로그
   * `controllerManager`: 컨트롤러 매니저 로그
   * `scheduler`: 스케줄러 로그
2. **AWS Management Console을 통한 활성화**:
   * EKS 콘솔에서 클러스터 선택
   * "로깅" 탭 선택
   * 원하는 로그 유형 활성화
3. **AWS CLI를 통한 활성화**:

```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

4. **eksctl을 통한 활성화**:

```bash
eksctl utils update-cluster-logging \
    --region=region-code \
    --cluster=cluster-name \
    --enable-types=api,audit,authenticator,controllerManager,scheduler
```

활성화된 로그는 자동으로 CloudWatch Logs의 `/aws/eks/cluster-name/cluster` 로그 그룹으로 전송됩니다. 각 로그 유형은 별도의 로그 스트림으로 저장됩니다.

**주의사항:**

* 로그 활성화는 추가 비용이 발생합니다 (CloudWatch Logs 요금 적용).
* 감사 로그는 특히 많은 양의 데이터를 생성할 수 있으므로 비용 관리에 주의해야 합니다.
* 로그 보존 기간을 설정하여 비용을 관리할 수 있습니다.

</details>

### 7. EKS 클러스터에서 워커 노드의 kubelet 로그를 CloudWatch Logs로 전송하는 방법은 무엇인가요?

<details>

<summary>정답 및 설명</summary>

EKS 클러스터에서 워커 노드의 kubelet 로그를 CloudWatch Logs로 전송하려면 CloudWatch 에이전트를 설치하고 구성해야 합니다. 컨트롤 플레인 로그와 달리, 워커 노드의 로그는 자동으로 CloudWatch로 전송되지 않습니다.

**구현 단계:**

1. **CloudWatch 에이전트 설치**: Kubernetes에 CloudWatch 에이전트를 DaemonSet으로 배포합니다.
2. **Fluentd 또는 Fluent Bit 설정**: 로그 수집기를 구성하여 kubelet 로그를 CloudWatch Logs로 전송합니다.
3.  **권장 방법: Amazon EKS 애드온 사용**:

    ```bash
    # CloudWatch 로그 수집을 위한 네임스페이스 생성
    kubectl create namespace amazon-cloudwatch

    # AWS 관찰성 액세스를 위한 서비스 계정 생성
    eksctl create iamserviceaccount \
        --name cloudwatch-agent \
        --namespace amazon-cloudwatch \
        --cluster my-cluster \
        --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy \
        --approve \
        --override-existing-serviceaccounts

    # Fluent Bit를 위한 서비스 계정 생성
    eksctl create iamserviceaccount \
        --name fluent-bit \
        --namespace amazon-cloudwatch \
        --cluster my-cluster \
        --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy \
        --approve \
        --override-existing-serviceaccounts

    # CloudWatch 에이전트 및 Fluent Bit 설치
    kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
    ```
4.  **구성 사용자 지정**: 특정 로그 경로 및 형식을 수집하도록 ConfigMap을 수정합니다.

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: fluent-bit-config
      namespace: amazon-cloudwatch
    data:
      fluent-bit.conf: |
        [INPUT]
            Name tail
            Path /var/log/kubelet.log
            Tag kubelet
        [OUTPUT]
            Name cloudwatch
            Match kubelet
            region region-name
            log_group_name /aws/eks/my-cluster/nodes
            log_stream_prefix kubelet-
            auto_create_group true
    ```
5. **로그 확인**: CloudWatch Logs 콘솔에서 로그 그룹 `/aws/eks/my-cluster/nodes`를 확인합니다.

**주요 수집 대상 로그:**

* `/var/log/kubelet.log`: kubelet 로그
* `/var/log/kube-proxy.log`: kube-proxy 로그
* `/var/log/aws-routed-eni/ipamd.log`: VPC CNI 로그
* `/var/log/containers/*.log`: 컨테이너 로그

**대안적 방법:**

* AWS Distro for OpenTelemetry(ADOT) 사용
* Amazon OpenSearch와 Fluent Bit 조합 사용
* 사용자 지정 로깅 솔루션 구축 (예: ELK 스택)

**모범 사례:**

* 로그 보존 기간 설정으로 비용 관리
* 필요한 로그만 선택적으로 수집
* 로그 필터링을 통한 중요 정보만 수집
* 로그 그룹에 태그 지정으로 비용 추적

</details>

### 8. EKS 클러스터에서 파드 보안 정책(Pod Security Policy)이 더 이상 사용되지 않는 이유와 대안은 무엇인가요?

<details>

<summary>정답 및 설명</summary>

EKS 클러스터에서 파드 보안 정책(Pod Security Policy, PSP)은 Kubernetes 1.21 버전부터 더 이상 사용되지 않으며(deprecated), Kubernetes 1.25에서 완전히 제거되었습니다. 이에 따라 EKS에서도 PSP를 더 이상 지원하지 않습니다.

**사용 중단 이유:**

1. **복잡성**: PSP는 구성이 복잡하고 이해하기 어려웠습니다.
2. **디버깅 어려움**: PSP 위반 시 명확한 오류 메시지를 제공하지 않아 문제 해결이 어려웠습니다.
3. **제한된 유연성**: 특정 시나리오에서 세밀한 제어가 어려웠습니다.
4. **일관성 부족**: 다른 Kubernetes 보안 메커니즘과의 통합이 원활하지 않았습니다.

**대안:**

1. **Pod Security Standards (PSS) / Pod Security Admission (PSA)**:
   * Kubernetes 1.22부터 도입된 공식 대안
   * 세 가지 보안 수준 제공: Privileged, Baseline, Restricted
   * 네임스페이스 레이블을 통해 적용
   *   예시:

       ```yaml
       apiVersion: v1
       kind: Namespace
       metadata:
         name: my-namespace
         labels:
           pod-security.kubernetes.io/enforce: restricted
           pod-security.kubernetes.io/audit: restricted
           pod-security.kubernetes.io/warn: restricted
       ```
2. **Kyverno**:
   * 정책 엔진으로, YAML 기반 정책 정의
   * PSP보다 더 유연하고 강력한 기능 제공
   * 검증, 변형, 생성, 정리 정책 지원
   *   예시:

       ```yaml
       apiVersion: kyverno.io/v1
       kind: ClusterPolicy
       metadata:
         name: restrict-privileged
       spec:
         validationFailureAction: enforce
         rules:
         - name: privileged-containers
           match:
             resources:
               kinds:
               - Pod
           validate:
             message: "Privileged containers are not allowed"
             pattern:
               spec:
                 containers:
                   - name: "*"
                     securityContext:
                       privileged: false
       ```
3. **OPA Gatekeeper**:
   * Open Policy Agent 기반의 정책 컨트롤러
   * Rego 언어를 사용한 정책 정의
   * 제약 템플릿(ConstraintTemplate)과 제약(Constraint) 개념 사용
   *   예시:

       ```yaml
       apiVersion: templates.gatekeeper.sh/v1beta1
       kind: ConstraintTemplate
       metadata:
         name: k8spsprivilegedcontainer
       spec:
         crd:
           spec:
             names:
               kind: K8sPSPPrivilegedContainer
         targets:
           - target: admission.k8s.gatekeeper.sh
             rego: |
               package k8spsprivilegedcontainer
               violation[{"msg": msg}] {
                 c := input.review.object.spec.containers[_]
                 c.securityContext.privileged
                 msg := "Privileged containers are not allowed"
               }
       ```
4. **AWS 기본 제공 보안 기능**:
   * Amazon GuardDuty for EKS Protection
   * AWS Security Hub의 EKS 보안 표준
   * Amazon Inspector for EKS

**마이그레이션 전략:**

1. 현재 PSP 정책 분석 및 문서화
2. 대체 솔루션 선택 (PSA, Kyverno, OPA Gatekeeper 등)
3. 새 정책을 감사(audit) 모드로 배포하여 영향 평가
4. 점진적으로 정책 적용 (enforce 모드로 전환)
5. 모니터링 및 로깅 설정으로 정책 위반 추적

EKS 1.25 이상으로 업그레이드하기 전에 PSP에서 대체 솔루션으로 마이그레이션하는 것이 중요합니다.

</details>

## 실습 문제

### 9. EKS 클러스터에서 비용 최적화를 위한 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용하는 노드 그룹 구성을 작성하세요. 다음 요구 사항을 충족해야 합니다:

* 중요한 워크로드용 온디맨드 노드 그룹 (2-5개 노드)
* 일반 워크로드용 스팟 노드 그룹 (2-10개 노드)
* 적절한 노드 레이블과 테인트 설정
* 워크로드 배치를 위한 노드 선호도 및 허용 오차 예시

<details>

<summary>정답 및 설명</summary>

EKS 클러스터에서 비용 최적화를 위한 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용하는 노드 그룹 구성은 다음과 같습니다:

#### 1. 온디맨드 노드 그룹 구성 (중요 워크로드용)

**eksctl을 사용한 구성:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: critical-workloads
    instanceType: m5.xlarge
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    capacityType: ON_DEMAND
    labels:
      workload-type: critical
      node-lifecycle: on-demand
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/my-cluster: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
    ssh:
      allow: false
```

**AWS CLI를 사용한 구성:**

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name critical-workloads \
  --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge \
  --capacity-type ON_DEMAND \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
  --labels workload-type=critical,node-lifecycle=on-demand \
  --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"
```

#### 2. 스팟 노드 그룹 구성 (일반 워크로드용)

**eksctl을 사용한 구성:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: general-workloads
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    desiredCapacity: 3
    minSize: 2
    maxSize: 10
    capacityType: SPOT
    labels:
      workload-type: general
      node-lifecycle: spot
    taints:
      - key: spot
        value: "true"
        effect: PreferNoSchedule
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/my-cluster: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
    ssh:
      allow: false
```

**AWS CLI를 사용한 구성:**

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name general-workloads \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large \
  --capacity-type SPOT \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
  --labels workload-type=general,node-lifecycle=spot \
  --taints "spot=true:PreferNoSchedule" \
  --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"
```

#### 3. 워크로드 배치를 위한 노드 선호도 및 허용 오차 예시

**중요 워크로드 배포 예시 (온디맨드 노드 선호):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-app
  template:
    metadata:
      labels:
        app: critical-app
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: workload-type
                operator: In
                values:
                - critical
              - key: node-lifecycle
                operator: In
                values:
                - on-demand
      containers:
      - name: critical-app
        image: my-critical-app:latest
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

**일반 워크로드 배포 예시 (스팟 노드 허용):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: general-app
  template:
    metadata:
      labels:
        app: general-app
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 1
            preference:
              matchExpressions:
              - key: node-lifecycle
                operator: In
                values:
                - spot
      tolerations:
      - key: "spot"
        operator: "Equal"
        value: "true"
        effect: "PreferNoSchedule"
      containers:
      - name: general-app
        image: my-general-app:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

#### 4. 추가 최적화 설정

**Cluster Autoscaler 배포:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
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
      serviceAccountName: cluster-autoscaler
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
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
```

**AWS Node Termination Handler (스팟 인스턴스 중단 처리):**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install aws-node-termination-handler \
  --namespace kube-system \
  --set enableSpotInterruptionDraining=true \
  --set enableRebalanceMonitoring=true \
  --set enableRebalanceDraining=true \
  eks/aws-node-termination-handler
```

#### 5. 모범 사례 및 고려 사항

1. **다양한 인스턴스 유형 사용**: 스팟 노드 그룹에서 여러 인스턴스 유형을 사용하면 중단 위험을 분산할 수 있습니다.
2.  **파드 중단 예산(PDB) 설정**: 중요한 애플리케이션에 대해 PDB를 설정하여 동시에 중단되는 파드 수를 제한합니다.

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: critical-app-pdb
    spec:
      minAvailable: 2
      selector:
        matchLabels:
          app: critical-app
    ```
3. **적절한 리소스 요청 및 제한 설정**: 노드 리소스를 효율적으로 활용하기 위해 컨테이너의 리소스 요청과 제한을 적절히 설정합니다.
4.  **Horizontal Pod Autoscaler 활용**: 워크로드 수요에 따라 파드 수를 자동으로 조정합니다.

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: general-app-hpa
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: general-app
      minReplicas: 3
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
    ```
5. **비용 모니터링 및 최적화**: AWS Cost Explorer와 Kubecost 같은 도구를 사용하여 클러스터 비용을 모니터링하고 최적화합니다.

</details>

## 고급 문제

### 10. EKS 클러스터에서 멀티 테넌시(Multi-tenancy)를 구현하기 위한 전략을 설명하고, 각 접근 방식의 장단점을 비교하세요.

<details>

<summary>정답 및 설명</summary>

EKS 클러스터에서 멀티 테넌시(Multi-tenancy)를 구현하는 것은 여러 팀, 애플리케이션 또는 고객이 동일한 Kubernetes 인프라를 공유하면서도 적절한 격리와 리소스 관리를 보장하는 것을 의미합니다. 다음은 EKS에서 멀티 테넌시를 구현하기 위한 주요 전략과 각 접근 방식의 장단점입니다.

### 1. 클러스터 수준 분리 (Hard Multi-tenancy)

**설명**: 테넌트별로 별도의 EKS 클러스터를 프로비저닝하는 방식입니다.

**구현 방법**:

```bash
# 테넌트 A를 위한 클러스터 생성
eksctl create cluster --name tenant-a-cluster --region us-west-2

# 테넌트 B를 위한 클러스터 생성
eksctl create cluster --name tenant-b-cluster --region us-west-2
```

**장점**:

* 완전한 격리 보장 (보안, 네트워킹, 리소스)
* 테넌트별 클러스터 버전 및 구성 사용자 지정 가능
* 한 테넌트의 문제가 다른 테넌트에 영향을 미치지 않음
* 규제 요구 사항이 엄격한 환경에 적합

**단점**:

* 높은 운영 오버헤드 (여러 클러스터 관리)
* 리소스 활용도 저하 (클러스터별 컨트롤 플레인 및 시스템 구성 요소 중복)
* 비용 증가 (클러스터당 컨트롤 플레인 비용 발생)
* 중앙 집중식 관리 및 정책 적용의 어려움

### 2. 네임스페이스 수준 분리 (Soft Multi-tenancy)

**설명**: 단일 EKS 클러스터 내에서 Kubernetes 네임스페이스를 사용하여 테넌트를 분리하는 방식입니다.

**구현 방법**:

```yaml
# 테넌트 A를 위한 네임스페이스 생성
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a

# 테넌트 B를 위한 네임스페이스 생성
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
```

**장점**:

* 단일 클러스터로 관리 간소화
* 리소스 활용도 향상
* 비용 효율성 (컨트롤 플레인 공유)
* 중앙 집중식 관리 및 정책 적용 용이

**단점**:

* 완전한 격리 보장이 어려움
* 클러스터 수준 리소스 공유로 인한 보안 위험
* 한 테넌트의 과도한 리소스 사용이 다른 테넌트에 영향을 줄 수 있음
* 클러스터 업그레이드 시 모든 테넌트에 영향

### 3. 네임스페이스 수준 분리 + 추가 보안 제어

**설명**: 네임스페이스 분리에 추가적인 보안 및 리소스 제어 메커니즘을 적용하는 방식입니다.

**구현 방법**:

1. **네트워크 정책**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-cross-tenant-traffic
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

2. **리소스 할당량**:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
```

3. **RBAC 권한 제어**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-admin
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-admins
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-admin-role
  apiGroup: rbac.authorization.k8s.io
```

**장점**:

* 네임스페이스 분리의 장점 유지
* 향상된 보안 및 리소스 격리
* 테넌트별 액세스 제어 및 리소스 할당
* 비용 효율성 유지

**단점**:

* 구성 및 관리 복잡성 증가
* 여전히 클러스터 수준 리소스에 대한 완전한 격리 부재
* 정책 설정 및 유지 관리에 추가 노력 필요

### 4. 가상 클러스터 (Virtual Clusters)

**설명**: 단일 물리적 EKS 클러스터 내에서 가상 Kubernetes 컨트롤 플레인을 생성하여 각 테넌트에게 자체 "클러스터"를 제공하는 방식입니다.

**구현 방법**:

```bash
# vcluster 설치
helm repo add vcluster https://charts.loft.sh
helm repo update

# 테넌트 A를 위한 가상 클러스터 생성
helm install vcluster-tenant-a vcluster/vcluster \
  --namespace tenant-a \
  --create-namespace \
  --set sync.nodes.enabled=true

# 테넌트 B를 위한 가상 클러스터 생성
helm install vcluster-tenant-b vcluster/vcluster \
  --namespace tenant-b \
  --create-namespace \
  --set sync.nodes.enabled=true
```

**장점**:

* 클러스터 수준 분리와 네임스페이스 수준 분리의 장점 결합
* 테넌트별 Kubernetes API 서버 및 컨트롤 플레인 제공
* 리소스 활용도 향상 및 비용 효율성
* 테넌트별 클러스터 버전 및 구성 가능

**단점**:

* 추가 오버헤드 및 복잡성
* 가상 클러스터 기술의 성숙도 및 지원 제한
* 일부 Kubernetes 기능의 제한적 지원
* 디버깅 및 문제 해결의 복잡성

### 5. AWS 서비스 통합을 활용한 멀티 테넌시

**설명**: AWS IAM, AWS Organizations, AWS Resource Access Manager 등의 AWS 서비스를 활용하여 EKS 클러스터의 멀티 테넌시를 강화하는 방식입니다.

**구현 방법**:

1. **IAM Roles for Service Accounts (IRSA)**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tenant-a-sa
  namespace: tenant-a
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tenant-a-role
```

2. **AWS Organizations 및 SCP (Service Control Policies)**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAccessToOtherTenantsResources",
      "Effect": "Deny",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::tenant-b-*"]
    }
  ]
}
```

**장점**:

* AWS 서비스에 대한 세밀한 액세스 제어
* 조직 구조와 정책을 활용한 강화된 거버넌스
* AWS 서비스 수준에서의 추가 격리 계층
* 기존 AWS 보안 모델과의 통합

**단점**:

* AWS 서비스에 대한 의존성 증가
* 구성 및 관리 복잡성 증가
* AWS 특화 솔루션으로 이식성 제한
* 추가 AWS 서비스 비용 발생 가능

### 멀티 테넌시 구현을 위한 모범 사례

1. **요구 사항 분석**:
   * 테넌트 간 필요한 격리 수준 평가
   * 규제 및 컴플라이언스 요구 사항 고려
   * 운영 오버헤드와 비용 제약 고려
2. **하이브리드 접근 방식 고려**:
   * 중요한 테넌트에는 전용 클러스터 제공
   * 덜 중요한 테넌트는 네임스페이스 수준 분리로 그룹화
3. **자동화 및 IaC (Infrastructure as Code)**:
   * Terraform, AWS CDK 또는 eksctl을 사용한 클러스터 및 네임스페이스 프로비저닝 자동화
   * GitOps 워크플로우를 통한 구성 관리
4. **모니터링 및 비용 할당**:
   * 테넌트별 리소스 사용량 모니터링
   * 비용 할당 태그를 사용한 테넌트별 비용 추적
   * Kubecost 또는 AWS Cost Explorer를 활용한 비용 분석
5. **보안 강화**:
   * 정기적인 보안 감사 및 취약점 스캔
   * 최소 권한 원칙 적용
   * 네트워크 정책 및 서비스 메시 활용

### 결론

EKS에서 멀티 테넌시를 구현하는 최적의 전략은 조직의 특정 요구 사항, 보안 요구 사항, 운영 역량 및 비용 제약에 따라 달라집니다. 많은 조직에서는 단일 접근 방식보다 여러 전략을 결합한 하이브리드 접근 방식을 채택하고 있습니다. 예를 들어, 중요한 워크로드나 규제 대상 워크로드에는 전용 클러스터를 사용하고, 개발 및 테스트 환경에는 네임스페이스 수준 분리를 적용하는 방식입니다.

멀티 테넌시 전략을 선택할 때는 보안, 격리, 리소스 활용도, 운영 오버헤드, 비용 등의 요소를 균형 있게 고려해야 합니다. 또한 선택한 전략이 시간이 지남에 따라 조직의 요구 사항 변화에 적응할 수 있는지 평가하는 것이 중요합니다.

</details>
