# Amazon EKS 클러스터 생성 퀴즈 (Part 5)

이 퀴즈는 Amazon EKS 클러스터의 고급 구성, 최적화 및 운영 모범 사례에 대한 이해를 테스트합니다. 비용 최적화, 고가용성 설계, 보안 강화 및 운영 자동화에 중점을 둡니다.

## 객관식 문제

### 1. Amazon EKS 클러스터에서 비용을 최적화하기 위한 가장 효과적인 방법은 무엇인가요?

A. 모든 워커 노드를 온디맨드 인스턴스로 실행  
B. 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용  
C. 모든 워커 노드를 예약 인스턴스로 실행  
D. 모든 워커 노드를 Fargate로 실행  

<details>
<summary>정답 및 설명</summary>

**정답: B. 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용**

**설명:**
EKS 클러스터에서 비용을 최적화하는 가장 효과적인 방법은 스팟 인스턴스와 온디맨드 인스턴스를 혼합하여 사용하는 것입니다:

- **스팟 인스턴스**: 온디맨드 가격보다 최대 90% 저렴하지만 AWS가 용량을 회수할 수 있어 중단될 가능성이 있습니다. 내결함성이 있는 상태 비저장(stateless) 워크로드에 적합합니다.
- **온디맨드 인스턴스**: 가격은 높지만 안정적이므로 중요한 상태 저장(stateful) 워크로드나 중단에 민감한 애플리케이션에 적합합니다.

이러한 혼합 접근 방식을 통해:
1. 중요한 워크로드는 온디맨드 인스턴스에서 실행
2. 내결함성이 있는 워크로드는 스팟 인스턴스에서 실행
3. 노드 선호도, 허용 오차(tolerations), 테인트(taints)를 사용하여 워크로드 배치 제어

추가적인 비용 최적화 전략으로는 Karpenter나 Cluster Autoscaler를 사용한 자동 스케일링, 적절한 인스턴스 크기 선택, Graviton(ARM) 인스턴스 사용, 예약 인스턴스 또는 Savings Plans 활용 등이 있습니다.
</details>

### 2. EKS 클러스터에서 여러 가용 영역(AZ)에 노드를 배포하는 주된 이유는 무엇인가요?

A. 네트워크 지연 시간 감소  
B. 데이터 처리량 증가  
C. 고가용성 및 내결함성 향상  
D. AWS 리전 간 데이터 복제 활성화  

<details>
<summary>정답 및 설명</summary>

**정답: C. 고가용성 및 내결함성 향상**

**설명:**
EKS 클러스터에서 여러 가용 영역(AZ)에 노드를 배포하는 주된 이유는 고가용성 및 내결함성을 향상시키기 위함입니다:

1. **가용 영역 장애 대응**: 한 가용 영역에 장애가 발생해도 다른 가용 영역의 노드는 계속 작동하므로 애플리케이션 가용성이 유지됩니다.

2. **인프라 이중화**: 여러 AZ에 걸쳐 워크로드를 분산함으로써 물리적 인프라 장애에 대한 보호 계층을 추가합니다.

3. **자동 복구**: Kubernetes는 장애가 발생한 노드의 파드를 정상 노드로 자동 재스케줄링하여 서비스 중단을 최소화합니다.

4. **롤링 업데이트 안정성**: 업데이트 중에도 여러 AZ에 걸쳐 워크로드가 분산되어 있어 가용성이 유지됩니다.

EKS는 기본적으로 컨트롤 플레인을 여러 AZ에 배포하지만, 워커 노드도 여러 AZ에 배포하여 전체 클러스터의 고가용성을 보장하는 것이 모범 사례입니다. 이를 위해 노드 그룹 생성 시 여러 서브넷(각각 다른 AZ에 위치)을 지정할 수 있습니다.
</details>

### 3. EKS 클러스터에서 파드 네트워킹을 위한 기본 CNI 플러그인은 무엇인가요?

A. Calico  
B. Flannel  
C. Amazon VPC CNI  
D. Weave Net  

<details>
<summary>정답 및 설명</summary>

**정답: C. Amazon VPC CNI**

**설명:**
Amazon EKS 클러스터에서 파드 네트워킹을 위한 기본 CNI(Container Network Interface) 플러그인은 Amazon VPC CNI입니다. 이 플러그인의 주요 특징은 다음과 같습니다:

1. **네이티브 VPC 네트워킹**: 각 파드는 VPC 내에서 고유한 IP 주소를 받아 AWS VPC 네트워킹을 직접 활용합니다.

2. **보안 그룹 통합**: 파드 수준에서 AWS 보안 그룹을 적용할 수 있어 세밀한 네트워크 보안 제어가 가능합니다.

3. **IP 주소 관리**: 각 노드는 VPC 서브넷에서 보조 IP 주소를 할당받아 파드에 제공합니다.

4. **성능**: 오버레이 네트워크를 사용하지 않아 네트워크 성능이 향상됩니다.

5. **AWS 서비스 통합**: AWS Load Balancer Controller, AWS App Mesh 등 다른 AWS 서비스와 원활하게 통합됩니다.

Amazon VPC CNI는 오픈 소스이며 GitHub에서 관리됩니다. 필요에 따라 Calico, Cilium 등 다른 CNI 플러그인으로 대체할 수 있지만, Amazon VPC CNI가 EKS의 기본 옵션이며 AWS에서 공식적으로 지원합니다.
</details>

### 4. EKS 클러스터에서 IAM 역할을 Kubernetes 서비스 계정에 연결하는 기능의 이름은 무엇인가요?

A. IAM for Service Accounts (IRSA)  
B. Pod Identity Webhook  
C. Kubernetes IAM Authenticator  
D. EKS Identity Manager  

<details>
<summary>정답 및 설명</summary>

**정답: A. IAM for Service Accounts (IRSA)**

**설명:**
EKS 클러스터에서 IAM 역할을 Kubernetes 서비스 계정에 연결하는 기능은 IAM for Service Accounts(IRSA)입니다. 이 기능의 주요 특징은 다음과 같습니다:

1. **세분화된 권한 제어**: 파드 수준에서 AWS 리소스에 대한 액세스를 제어할 수 있어, 노드 수준의 광범위한 권한 부여를 방지합니다.

2. **OIDC 기반 인증**: EKS는 OpenID Connect(OIDC) 제공자를 사용하여 Kubernetes 서비스 계정과 IAM 역할 간의 신뢰 관계를 설정합니다.

3. **보안 강화**: 애플리케이션별로 필요한 최소 권한만 부여하는 최소 권한 원칙을 구현할 수 있습니다.

4. **구현 방식**:
   - EKS 클러스터에 대한 OIDC 제공자 생성
   - 서비스 계정을 신뢰하는 IAM 역할 생성
   - 특정 주석(annotation)이 있는 Kubernetes 서비스 계정 생성
   - 해당 서비스 계정을 사용하는 파드 배포

IRSA를 사용하면 AWS SDK를 사용하는 애플리케이션이 노드의 IAM 역할에 의존하지 않고 자체 IAM 역할을 사용하여 AWS 서비스에 안전하게 액세스할 수 있습니다.
</details>

### 5. EKS 클러스터에서 노드 그룹의 Auto Scaling을 관리하는 Kubernetes 네이티브 도구는 무엇인가요?

A. Horizontal Pod Autoscaler  
B. Vertical Pod Autoscaler  
C. Cluster Autoscaler  
D. Node Autoscaler  

<details>
<summary>정답 및 설명</summary>

**정답: C. Cluster Autoscaler**

**설명:**
EKS 클러스터에서 노드 그룹의 Auto Scaling을 관리하는 Kubernetes 네이티브 도구는 Cluster Autoscaler입니다. 이 도구의 주요 특징은 다음과 같습니다:

1. **자동 스케일링**: 파드가 리소스 부족으로 스케줄링되지 못할 때 노드를 자동으로 추가하고, 노드가 충분히 활용되지 않을 때 노드를 제거합니다.

2. **AWS Auto Scaling 그룹 통합**: EKS에서는 AWS Auto Scaling 그룹과 통합되어 작동합니다.

3. **작동 방식**:
   - 스케일 아웃: 파드가 리소스 제약으로 Pending 상태일 때 노드 추가
   - 스케일 인: 노드의 활용도가 낮고 파드를 다른 노드로 이동할 수 있을 때 노드 제거

4. **구성 옵션**:
   - 스케일 업/다운 임계값 설정
   - 노드 그룹 검색 방법 지정
   - 스케일 다운 지연 설정
   - 파드 중단 예산(PDB) 존중

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
   - `api`: Kubernetes API 서버 로그
   - `audit`: Kubernetes 감사 로그
   - `authenticator`: AWS IAM 인증기 로그
   - `controllerManager`: 컨트롤러 매니저 로그
   - `scheduler`: 스케줄러 로그

2. **AWS Management Console을 통한 활성화**:
   - EKS 콘솔에서 클러스터 선택
   - "로깅" 탭 선택
   - 원하는 로그 유형 활성화

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
- 로그 활성화는 추가 비용이 발생합니다 (CloudWatch Logs 요금 적용).
- 감사 로그는 특히 많은 양의 데이터를 생성할 수 있으므로 비용 관리에 주의해야 합니다.
- 로그 보존 기간을 설정하여 비용을 관리할 수 있습니다.
</details>

### 7. EKS 클러스터에서 워커 노드의 kubelet 로그를 CloudWatch Logs로 전송하는 방법은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

EKS 클러스터에서 워커 노드의 kubelet 로그를 CloudWatch Logs로 전송하려면 CloudWatch 에이전트를 설치하고 구성해야 합니다. 컨트롤 플레인 로그와 달리, 워커 노드의 로그는 자동으로 CloudWatch로 전송되지 않습니다.

**구현 단계:**

1. **CloudWatch 에이전트 설치**: Kubernetes에 CloudWatch 에이전트를 DaemonSet으로 배포합니다.

2. **Fluentd 또는 Fluent Bit 설정**: 로그 수집기를 구성하여 kubelet 로그를 CloudWatch Logs로 전송합니다.

3. **권장 방법: Amazon EKS 애드온 사용**:
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

4. **구성 사용자 지정**: 특정 로그 경로 및 형식을 수집하도록 ConfigMap을 수정합니다.
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
- `/var/log/kubelet.log`: kubelet 로그
- `/var/log/kube-proxy.log`: kube-proxy 로그
- `/var/log/aws-routed-eni/ipamd.log`: VPC CNI 로그
- `/var/log/containers/*.log`: 컨테이너 로그

**대안적 방법:**
- AWS Distro for OpenTelemetry(ADOT) 사용
- Amazon OpenSearch와 Fluent Bit 조합 사용
- 사용자 지정 로깅 솔루션 구축 (예: ELK 스택)

**모범 사례:**
- 로그 보존 기간 설정으로 비용 관리
- 필요한 로그만 선택적으로 수집
- 로그 필터링을 통한 중요 정보만 수집
- 로그 그룹에 태그 지정으로 비용 추적
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
   - Kubernetes 1.22부터 도입된 공식 대안
   - 세 가지 보안 수준 제공: Privileged, Baseline, Restricted
   - 네임스페이스 레이블을 통해 적용
   - 예시:
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
   - 정책 엔진으로, YAML 기반 정책 정의
   - PSP보다 더 유연하고 강력한 기능 제공
   - 검증, 변형, 생성, 정리 정책 지원
   - 예시:
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
   - Open Policy Agent 기반의 정책 컨트롤러
   - Rego 언어를 사용한 정책 정의
   - 제약 템플릿(ConstraintTemplate)과 제약(Constraint) 개념 사용
   - 예시:
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
   - Amazon GuardDuty for EKS Protection
   - AWS Security Hub의 EKS 보안 표준
   - Amazon Inspector for EKS

**마이그레이션 전략:**
1. 현재 PSP 정책 분석 및 문서화
2. 대체 솔루션 선택 (PSA, Kyverno, OPA Gatekeeper 등)
3. 새 정책을 감사(audit) 모드로 배포하여 영향 평가
4. 점진적으로 정책 적용 (enforce 모드로 전환)
5. 모니터링 및 로깅 설정으로 정책 위반 추적

EKS 1.25 이상으로 업그레이드하기 전에 PSP에서 대체 솔루션으로 마이그레이션하는 것이 중요합니다.
</details>
