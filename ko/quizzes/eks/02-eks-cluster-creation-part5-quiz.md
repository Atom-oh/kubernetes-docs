# EKS 클러스터 생성 퀴즈 - Part 5

> **마지막 업데이트**: 2026년 9월 11일

EKS 운영·로그·정책 집행·테넌트 격리를 다루는 퀴즈입니다. 마지막 문항은 개념 문서의 접근 검증·폐기 절차와 연결합니다. 명령에는 검토된 클러스터·리전·kubeconfig, IAM·컨트롤러 선행조건이 필요하며 이번 감사에서 클라우드 배포·프로덕션 테스트를 실행하지 않았습니다.

## 객관식 문제

1. Spot이 아닌 기본 용량과 중단 가능한 용량을 함께 사용하는 방법은 무엇인가요?
   * A) 모든 노드를 On-Demand로 사용
   * B) On-Demand·Spot 그룹을 분리하고 워크로드 배치 설정
   * C) 모든 그룹의 capacityType을 Reserved로 지정
   * D) 모든 워크로드를 Fargate로 실행

<details>
<summary>정답 보기</summary>

**정답: B) On-Demand·Spot 그룹을 분리하고 워크로드 배치 설정**

중단에 민감한 기본 용량과 중단을 허용하는 용량을 함께 운영할 때 혼합 구성이 적합할 수 있습니다. On-Demand·Spot 관리형 그룹을 분리하고 워크로드 배치를 명시하세요. 보편적으로 “가장 효과적인” 비용 전략은 아닙니다. 활용률·신뢰성 요구·리전 및 인스턴스 가격·운영 노력이 결과를 결정합니다.

AWS가 안내하는 Spot의 On-Demand 대비 최대 90% 절감은 모든 용량 풀의 보장 할인이나 이 문서의 실측 절감률이 아닙니다. On-Demand는 Spot 회수 대상이 아니지만 유지 관리·장애 위험은 있습니다. Spot에는 체크포인트·재시도·여유 용량이 중요합니다.

적정 크기 선택, Cluster Autoscaler·Karpenter, 호환 Graviton 이미지와 적절한 약정 할인도 선택지입니다. Reserved Instances·Savings Plans는 결제 방식이며 일반 관리형 그룹의 별도 용량 설정이 아닙니다. Fargate가 적합한 수요도 있으므로 한 컴퓨팅 유형이 항상 유리하다고 가정하지 말고 프로비저닝 용량과 총비용을 비교하세요.

</details>

2. 적절한 워크로드를 여러 AZ에 분산하는 주된 이유는 무엇인가요?
   * A) 항상 지연 감소
   * B) 처리량 증가 보장
   * C) 단일 AZ 장애 노출 감소
   * D) 자동 리전 간 복제

<details>
<summary>정답 보기</summary>

**정답: C) 단일 AZ 장애 노출 감소**

여러 AZ는 단일 장애 영역에 대한 의존성을 줄입니다. EKS 관리형 제어 플레인은 여러 AZ에 분산되지만 애플리케이션 가용성에는 적절히 분산된 복제본·정상 엔드포인트·여유 용량·호환 네트워크 및 스토리지가 추가로 필요합니다.

Kubernetes 컨트롤러는 대체 Pod를 만들 수 있지만 독립 Pod는 자동 재생성되지 않으며 용량 부족·필수 어피니티·AZ에 묶인 EBS 볼륨이 복구를 막을 수 있습니다. 여러 서브넷을 나열해도 모든 애플리케이션 복제본이 분산되는 것은 아닙니다. 토폴로지 분산·안티어피니티와 실제 배치를 확인하세요.

PDB는 AZ 장애가 아닌 자발적 축출을 제어합니다. 롤링 업데이트·AZ 간 장애 복구는 애플리케이션 검증과 데이터 복구 설계가 필요합니다. 여러 AZ가 리전 간 복제를 자동 제공하지는 않으며 AZ 간 전송 비용이 추가될 수 있습니다.

</details>

3. 일반 EKS EC2 노드의 기본 CNI는 무엇인가요?
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>정답 보기</summary>

**정답: C) Amazon VPC CNI**

일반 EKS EC2 노드는 기본적으로 Amazon VPC CNI를 사용하며 지원되는 보조 IP·prefix 모드로 VPC 주소를 할당합니다. Auto Mode는 자체 관리형 네트워킹 기능을 제공하고 Hybrid Nodes는 지원되는 대체 CNI를 사용합니다. 기존 CNI 위에 구성하지 않은 대체 플러그인을 바로 설치하지 마세요.

Pod 보안 그룹에는 지원 인스턴스·CNI 설정과 정책 선택이 필요하며 모든 Pod에 자동으로 고유 보안 그룹이 생기는 것은 아닙니다. 기본 NetworkPolicy도 지원 컴퓨팅과 명시적 활성화가 필요합니다.

이 설계의 VPC 기본 라우팅은 일반적인 오버레이를 피하지만 실측 성능 보장은 아닙니다. 대역폭·라우팅·IP 용량·정책 동작·애플리케이션 요구를 검증하세요. Load Balancer Controller 같은 통합에도 별도 설치·권한이 필요합니다.

</details>

4. EKS OIDC 발급자와 projected ServiceAccount 토큰을 사용하는 워크로드 신원 방식은 무엇인가요?
   * A) IAM Roles for Service Accounts(IRSA)
   * B) EKS 접근 정책
   * C) Kubernetes RoleBinding만 사용
   * D) 노드 레이블

<details>
<summary>정답 보기</summary>

**정답: A) IAM Roles for Service Accounts(IRSA)**

**IAM Roles for Service Accounts(IRSA)**는 projected ServiceAccount 토큰, 클러스터 OIDC 발급자와 IAM 신뢰를 이용해 STS 임시 자격 증명을 얻습니다. 대상 audience(`sts.amazonaws.com`)와 정확한 네임스페이스·ServiceAccount subject로 신뢰를 제한하고 필요한 AWS 작업·리소스만 허용하세요.

Pod에서 의도한 ServiceAccount와 호환 SDK 자격 증명 체인을 사용합니다. AWS 접근 성공이 다른 자격 증명에서 올 수도 있으므로 실제 assumed role을 확인하세요. IRSA만으로 노드 IMDS 자격 증명 접근을 막지는 않습니다.

EKS Pod Identity도 역할·ServiceAccount를 연결하지만 에이전트·association 흐름이 다릅니다. 적격 EC2·Auto Mode와 전용 설정을 갖춘 Hybrid Nodes에 지원 경로가 있으며 Fargate에는 IRSA 같은 다른 지원 방식이 필요합니다. 두 방식 모두 EKS 액세스 엔트리와는 다릅니다. 워크로드 AWS 권한과 Kubernetes API 접근은 별개입니다.

</details>

5. Kubernetes 스케줄링 수요에 따라 기존 EKS 관리형 노드 그룹 ASG를 확장하는 컨트롤러는 무엇인가요?
   * A) Horizontal Pod Autoscaler
   * B) Vertical Pod Autoscaler
   * C) Cluster Autoscaler
   * D) ResourceQuota

<details>
<summary>정답 보기</summary>

**정답: C) Cluster Autoscaler**

Cluster Autoscaler는 검색된 기존 노드 그룹·ASG를 조정합니다. 호환 설치·Kubernetes RBAC·전용 AWS 권한·정확한 검색 태그가 필요하며 min/max를 설정한다고 설치되지는 않습니다.

확장 시 스케줄링 요청·제약을, 축소 시 이동·중단 조건을 고려합니다. 모든 Pending Pod가 노드 추가로 해결되는 것은 아니며 축소 활용률 로직은 CPU 사용률 HPA 임계값과 다릅니다.

HPA는 복제본을 조정하고 VPA는 Pod 요청을 권장·변경하므로 둘 다 노드 수요에 간접 영향을 줄 수 있습니다. Karpenter는 NodePool·NodeClaim을 사용하는 별도 용량 프로비저너이며 보편적으로 더 빠른 대안이나 ASG 컨트롤러가 아닙니다. 제어 루프와 워크로드 제약을 검증하세요.

</details>

## 단답형 문제

6. EKS 제어 플레인의 CloudWatch 로깅을 어떻게 활성화·검증하나요?

<details>
<summary>정답 및 설명</summary>

필요한 제어 플레인 로그 유형인 `api`·`audit`·`authenticator`·`controllerManager`·`scheduler`를 활성화합니다. EKS 콘솔은 기존 Logging 탭 안내 대신 **Observability → Control plane logging → Manage logging** 경로를 사용합니다.

다음은 다섯 유형을 모두 켜는 예제이며 실제 환경에서 필요한 범위를 검토하세요:

```bash
set -euo pipefail
LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
반환된 업데이트 ID가 `Successful`이 될 때까지 확인하고 실패를 처리한 후 다른 변경을 수행합니다. eksctl 대안은 변경 적용에 `--approve`가 필요합니다:

```bash
# Alternative to the AWS CLI update, not a second concurrent update.
eksctl utils update-cluster-logging --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --enable-types=api,audit,authenticator,controllerManager,scheduler --approve
```
로그는 클러스터 리전의 `/aws/eks/<cluster-name>/cluster`에 전달됩니다. 스트림이 회전하며 유형별로 여러 개가 존재할 수 있습니다. 전달은 최선형이며 보통 수분이 걸립니다. 활성 설정·현재 스트림 시각·관련 실제 이벤트를 확인하세요. 로그 그룹만으로 성공을 입증할 수는 없습니다. 보존·접근 제어와 수집·저장 비용을 관리하고 민감한 감사 이벤트를 공개하지 않습니다. 워커·애플리케이션 로그는 별도 수집기가 필요합니다.

</details>

7. 일반 EKS Linux 노드의 kubelet 로그를 CloudWatch로 어떻게 수집할 수 있나요?

<details>
<summary>정답 및 설명</summary>

kubelet 로그는 EKS 제어 플레인 로깅과 별개의 노드 로그입니다. EKS 최적화 AL2023 Linux에서는 `kubelet.service`의 systemd journal을 확인하며 `/var/log/kubelet.log`·`/var/log/kube-proxy.log`가 있다고 가정하지 않습니다. kube-proxy는 보통 컨테이너로 로그를 남기고 VPC CNI 파일·stdout 경로는 설정에 따라 다릅니다.

관리형 **Amazon CloudWatch Observability EKS 애드온**은 에이전트·오퍼레이터·Fluent Bit를 설치합니다. raw quickstart 매니페스트는 이 관리형 애드온이 아닙니다. 소유자를 검토하지 않고 기존 ServiceAccount를 덮어쓰거나 Fluent Bit ConfigMap 전체를 교체하지 마세요.

이 예제는 Pod Identity Agent가 준비된 **Linux EC2 실습 환경**과 해당 클러스터의 `amazon-cloudwatch/cloudwatch-agent` ServiceAccount를 신뢰하는 기존 승인 역할을 사용합니다. CloudWatch 권한을 검토하세요. `CloudWatchAgentServerPolicy`는 AWS의 관리형 기준 정책이며 모든 권한이 각 로그 범위의 최소 권한이라는 뜻은 아닙니다. 현재 차트의 Fluent Bit도 같은 ServiceAccount를 사용하므로 이 설정에 별도의 `fluent-bit` IAM ServiceAccount는 필요하지 않습니다.

먼저 호환 애드온 빌드를 선택하고 스키마를 확인합니다. Helm 차트 버전과 EKS 애드온 빌드 문자열은 다릅니다:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible build with the configuration fields below}"
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --query configurationSchema --output text > cloudwatch-addon-schema.json
```
다음을 `cloudwatch-addon-values.yaml`로 저장합니다. 공식 차트 6.6.0으로 렌더링한 구성입니다. Linux `dataplane-log.conf` 전체를 재정의해 kubelet journal만 수집하며 application·host 파일을 비워 기본 로그 경로를 끕니다. 다른 Fluent Bit 전역 절은 기본값을 유지합니다. 애드온은 Container Insights 메트릭도 수집하므로 로그 전용 에이전트 설치는 아닙니다. 이 실습 때문에 서비스를 자동 계측하지 않도록 Application Signals 자동 모니터링을 명시적으로 끕니다.

```yaml
manager:
  applicationSignals:
    autoMonitor:
      monitorAllServices: false
containerLogs:
  fluentBit:
    config:
      extraFiles:
        application-log.conf: ''
        host-log.conf: ''
        dataplane-log.conf: |
          [INPUT]
            Name                systemd
            Tag                 dataplane.kubelet
            Systemd_Filter      _SYSTEMD_UNIT=kubelet.service
            DB                  /var/fluent-bit/state/kubelet.db
            Path                /var/log/journal
            Read_From_Tail      On

          [FILTER]
            Name                modify
            Match               dataplane.kubelet
            Rename              _HOSTNAME hostname
            Rename              MESSAGE message

          [OUTPUT]
            Name                cloudwatch_logs
            Match               dataplane.kubelet
            region              ${AWS_REGION}
            log_group_name      /aws/containerinsights/${CLUSTER_NAME}/dataplane
            log_stream_prefix   ${HOST_NAME}-
            auto_create_group   true
```
대상 노드의 마운트된 journal 경로와 쓰기 가능한 상태 디렉터리를 확인하세요. Linux 재정의는 Windows 수집을 구성하지 않으며 혼합·Hybrid·Auto Mode 환경은 각 문서의 경로를 따라야 합니다. 선택한 애드온 스키마를 확인하고 업데이트에 적용할 때는 다른 기존 구성을 보존합니다.

```bash
# New installation only, after the schema/role/configuration review.
: "${CLOUDWATCH_ROLE_ARN:?Existing approved Pod Identity role}"
CW_ASSOCIATIONS=$(jq -cn --arg role "$CLOUDWATCH_ROLE_ARN" \
  '[{serviceAccount:"cloudwatch-agent",roleArn:$role}]')
aws eks create-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$CW_ASSOCIATIONS" \
  --configuration-values file://cloudwatch-addon-values.yaml --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --query 'addon.{status:status,health:health,version:addonVersion}'
```
해당 애드온 작업의 완료를 기다리고 상태 오류·에이전트 및 Fluent Bit Pod·`/aws/containerinsights/<cluster>/dataplane`의 새 이벤트를 확인합니다. Helm 렌더링 성공이나 로그 그룹 존재가 수집을 입증하지는 않습니다. IAM·네트워크 엔드포인트·로그 보존·수집 및 메트릭 비용을 검토하세요. 기존 관측성 설치는 계획된 이전이 필요하며 로그를 중복 수집하거나 애플리케이션 재시작을 조용히 켜면 안 됩니다. 여기서는 실제 에이전트 설치·journal 수집·CloudWatch 전달을 테스트하지 않았습니다.

</details>

8. PSP의 대안과 동등한 admission 통제는 어떻게 평가해야 하나요?

<details>
<summary>정답 및 설명</summary>

PodSecurityPolicy는 Kubernetes 1.21에서 폐기 예정이 되었고 1.25에서 제거되었습니다. 현재 지원되는 EKS 버전에는 이 API가 없습니다. Pod Security Admission(PSA)은 Pod Security Standards(PSS) 프로파일을 집행하지만 PSP의 모든 필드를 일대일로 대체하지는 않습니다.

새 EKS 1.36 실습 네임스페이스는 정책 버전을 고정하여 이후 클러스터 업그레이드가 선택한 정책 버전을 조용히 바꾸지 않도록 합니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: psa-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```
기존 프로덕션 네임스페이스는 Restricted 집행 전에 audit·warn 결과와 애플리케이션 호환성을 평가합니다. PSA는 검증 기능이며 이전 PSP의 변형·기본값 설정 동작을 제공하지 않습니다. 호스트 네임스페이스·capability·볼륨·ID·seccomp 등 기존 통제를 적절한 대안에 매핑하세요.

**Kyverno 대안:** 다음은 검토한 Kyverno 1.19.1·차트 3.9.1 경로의 CEL 기반 `policies.kyverno.io/v1` ValidatingPolicy입니다. 기존 ClusterPolicy는 1.19에서 폐기 예정이며 이미 제거되었다는 뜻은 아닙니다. 호환 컨트롤러·CRD를 별도로 설치하고 검토한 `policy-engine-lab` 네임스페이스를 사용합니다. 일반·init·ephemeral 컨테이너를 모두 확인합니다:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```
**Gatekeeper 대안:** ConstraintTemplate만으로 규칙이 집행되지는 않습니다. 아래 템플릿·Constraint는 검토한 Gatekeeper 3.23.1 예제이며 `templates.gatekeeper.sh/v1`과 생성되는 Constraint API 버전은 서로 다릅니다:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8snoprivilegedlab

      containers[c] {
        c := input.review.object.spec.containers[_]
      }
      containers[c] {
        c := input.review.object.spec.initContainers[_]
      }
      containers[c] {
        c := input.review.object.spec.ephemeralContainers[_]
      }
      violation[{"msg": msg}] {
        c := containers[_]
        c.securityContext.privileged == true
        msg := sprintf("Privileged container is not allowed: %v", [c.name])
      }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```
두 엔진 예제는 대안이며 한 가지 통제를 보여 줄 뿐 완전한 PSP 대체나 프로덕션 강화 정책은 아닙니다. 정상·securityContext 생략 사례와 privileged 일반·init·ephemeral 컨테이너를 테스트하세요. admission 실패 정책·웹훅 가용성·예외도 검토합니다. GuardDuty·Security Hub·Inspector는 지원 리소스의 위협·보안 상태·취약점 기능을 보완하며 Pod 승인 시점의 거부를 대체하지 않습니다.

</details>

## 실습 문제

9. On-Demand·Spot 그룹을 분리하고 배치 제어와 오토스케일링 선행조건을 구성하세요.

<details>
<summary>정답 및 설명</summary>

중요 작업용 On-Demand 2–5개와 중단을 허용하는 작업용 Spot 2–10개의 관리형 그룹을 **분리**합니다. 실측 절감률·용량 보장이 아닌 예제입니다. 생성 방식 하나와 미사용 그룹 이름을 선택하고 프라이빗 서브넷 egress·엔드포인트·IAM·AMI 및 이미지 호환성을 먼저 확인하세요.

eksctl 구성은 지원되는 `managedNodeGroups`·`spot` 필드를 사용합니다. 모든 노드에 오토스케일러 컨트롤러 권한을 부여하면 안 됩니다:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: critical-workloads
  amiFamily: AmazonLinux2023
  instanceType: m5.xlarge
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  spot: false
  labels:
    workload-type: critical
    node-lifecycle: on-demand
- name: general-workloads
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large]
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    workload-type: general
    node-lifecycle: spot
  taints:
  - key: spot
    value: "true"
    effect: PreferNoSchedule
```
파일을 저장·검토한 후 기존 클러스터에 `eksctl create nodegroup -f nodegroups.yaml`을 사용합니다. AWS CLI 대안은 다음과 같습니다. EKS API 테인트 효과는 Kubernetes·eksctl의 CamelCase와 달리 대문자 이름과 구조화된 값을 사용합니다:

```bash
set -euo pipefail
# Alternative to eksctl; use unused group names and approved role/subnet IDs.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${CRITICAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge --capacity-type ON_DEMAND --ami-type AL2023_x86_64_STANDARD \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --node-role "${NODE_ROLE_ARN:?}" \
  --labels workload-type=critical,node-lifecycle=on-demand
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$CRITICAL_NODEGROUP_NAME"

aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "${GENERAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --subnets "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" \
  --node-role "$NODE_ROLE_ARN" --labels workload-type=general,node-lifecycle=spot \
  --taints '[{"key":"spot","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GENERAL_NODEGROUP_NAME"
```
새로 검토한 `placement-lab` 네임스페이스의 대기 컨테이너로 스케줄링만 확인합니다. 애플리케이션 동작을 검증하려면 검토한 실제 이미지로 바꾸세요. 중요 워크로드는 On-Demand 레이블을 필수로 요구하며 일반 워크로드는 Spot을 선호하지만 다른 노드에 배치될 수도 있습니다. 톨러레이션은 배치를 허용할 뿐 강제하지 않으며 `PreferNoSchedule`은 소프트 제어입니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
  namespace: placement-lab
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
      automountServiceAccountToken: false
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
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
  namespace: placement-lab
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
      automountServiceAccountToken: false
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
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      tolerations:
      - key: spot
        operator: Equal
        value: 'true'
        effect: PreferNoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-app-pdb
  namespace: placement-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: critical-app
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: general-app-hpa
  namespace: placement-lab
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
유지한 requests·limits 값은 예시입니다. PDB는 자발적 축출을 제한하며 Spot 회수·AZ 장애를 막지 않습니다. HPA에는 Metrics Server와 의미 있는 부하·메트릭 관계가 필요합니다. 대기 컨테이너 예제는 확장 벤치마크가 아닙니다.

전용 Cluster Autoscaler ServiceAccount·역할에 태그로 제한한 AWS 권한과 실제 ASG 검색 태그를 준비합니다. 노드 그룹 태그만으로 ASG 태그를 확인할 수는 없습니다. EKS 1.36에는 검토한 차트·이미지 조합을 렌더링하고 설치 전에 확인하세요:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
별도 검토 근거가 없다면 로컬 스토리지·시스템 Pod 보호를 유지합니다. CA의 혼합 그룹은 CPU·메모리·GPU 크기를 맞춰야 합니다. 관리형 노드 그룹에는 Spot 재분배·드레인 처리가 내장되어 있으므로 Node Termination Handler를 무조건 추가하지 마세요. 자체 관리 용량은 별도의 검토한 수명주기 처리가 필요합니다. 대표 워크로드 조건에서 중단 복구·배치·데이터 영속성과 총비용을 검증합니다.

</details>

## 고급 문제

10. EKS 테넌트 격리 방식과 실제 경계를 비교하세요.

<details>
<summary>정답 및 설명</summary>

실제 신뢰·데이터·가용성·거버넌스 요구에 따라 테넌트 경계를 선택합니다. 아래는 **대안 설계**이며 모든 예제를 하나의 공유 네임스페이스에 결합하라는 지침이 아닙니다.

**별도 클러스터·계정:** 전용 API·제어 플레인은 결합을 줄이고 독립적인 수명주기를 제공하지만 운영 비용이 늘어납니다. 공유 IAM·VPC·스토리지·쿼터·외부 서비스까지 자동 격리하거나 한 테넌트가 다른 테넌트에 절대 영향을 주지 않는다고 보장하지는 않습니다. 기본값의 `eksctl create cluster` 두 줄 대신 검토한 클러스터 생성 가이드를 사용하세요.

**집행되는 제어를 갖춘 네임스페이스:** 네임스페이스는 이름을 분리하며 모든 보안·용량을 격리하지는 않습니다. 플랫폼 관리자가 새 테넌트 네임스페이스를 생성하고 정책 레이블·쿼터·RBAC 경계를 관리합니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```
다음 완전한 tenant-a 예제에는 기존 RoleBinding에 빠져 있던 Role, 명시적 워크로드 권한, 네임스페이스 내부 통신·제한된 DNS, ResourceQuota·LimitRange가 포함됩니다. 인증된 `tenant-a-users` 그룹과 대응하는 tenant-b 리소스는 별도로 검토해 구성하세요:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
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
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
정책에는 호환 집행 엔진이 필요하며 일반 CoreDNS 레이블을 가정합니다. NodeLocal DNSCache 경로는 수정해야 합니다. 쿼터는 승인 한도이지 노드 예약·대역폭 보장이 아닙니다. 워크로드 생성으로 네임스페이스의 ServiceAccount·Secret을 사용할 수 있으므로 admission으로 제한하고 플랫폼 자격 증명은 테넌트 네임스페이스 밖에 두세요. 공유 커널·제어 플레인은 별도 위협 모델 검토가 필요합니다.

**가상 클러스터:** 가상 API·제어 플레인은 클러스터 범위 구성을 분리할 수 있지만 공유 노드 워크로드는 호스트 커널·CNI·CSI를 공유합니다. 검토한 vCluster 0.36.1 구성은 현재 `sync.fromHost.nodes` 필드를 사용하고 호스트 노드 동기화를 비활성화합니다. 테넌트 생성만을 위해 필요한 설정이 아니며 활성화하면 호스트 메타데이터를 노출할 수 있습니다. Private·전용 노드 아키텍처는 선행조건·격리 속성이 다릅니다.

다음을 `vcluster-values.yaml`로 저장하고 StorageClass를 승인된 동작 가능한 클래스로 바꾸세요. 플랫폼이 관리하는 별도 호스트 네임스페이스를 사용하여 테넌트가 호스트 RoleBinding으로 권한 있는 syncer·컨트롤러를 수정하지 못하게 합니다:

```yaml
sync:
  fromHost:
    nodes:
      enabled: false
controlPlane:
  statefulSet:
    persistence:
      volumeClaim:
        enabled: true
        storageClass: REPLACE_WITH_APPROVED_STORAGE_CLASS
        size: 5Gi
        retentionPolicy: Retain
    imagePullPolicy: IfNotPresent
```

```bash
helm repo add vcluster https://charts.loft.sh
helm repo update vcluster
helm template vcluster-tenant-a vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-a-host -f vcluster-values.yaml > tenant-a-reviewed.yaml
helm template vcluster-tenant-b vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-b-host -f vcluster-values.yaml > tenant-b-reviewed.yaml
```
렌더링한 RBAC·스토리지·리소스 요청·이미지·동기화 구성을 확인한 뒤 검토한 Helm·GitOps 소유자를 통해 배포합니다. 공개 차트는 기본적으로 `vcluster-pro:0.36.1`을 렌더링하므로 선택한 에디션·기능·라이선스를 확인하세요. 렌더링으로 사용 자격·영속성·클러스터 시작·프로덕션 격리가 검증되는 것은 아닙니다. 테넌트 상태를 백업하고 가상 클러스터·호스트 네임스페이스 삭제 전 PVC·PV 보존을 확인합니다.

**AWS 신원과 거버넌스:** 신뢰·리소스 권한을 제한한 테넌트별 IRSA 또는 지원되는 Pod Identity 역할을 사용합니다. AWS 신원은 Kubernetes 인가를 보완합니다. SCP는 해당 멤버 계정 주체의 최대 권한을 제한하며 접근을 부여하거나 Kubernetes 네임스페이스를 구분하지 않습니다.

다음 S3 거부 예제는 **테넌트 A의 멤버 계정·OU에만** 연결하고 검토한 테넌트 B 버킷을 대상으로 합니다. 공유 계정에 연결한 뒤 A·B를 구별한다고 기대하면 안 됩니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyTenantBStoreFromTenantAAccount",
    "Effect": "Deny",
    "Action": ["s3:*"],
    "Resource": [
      "arn:aws:s3:::amzn-s3-demo-tenant-b",
      "arn:aws:s3:::amzn-s3-demo-tenant-b/*"
    ]
  }]
}
```
SCP는 관리 계정·서비스 연결 역할을 제한하지 않으며 무관한 외부 계정 주체를 직접 통제하지 않습니다. 리소스 정책·IAM 권한·데이터 보호는 여전히 필요합니다. 계정 수준 제어 하나의 예제이며 완전한 테넌트 격리 정책이 아닙니다. 선택한 설계의 실제 접근과 복구·보존을 검증하세요. 여기서는 클러스터·가상 클러스터·SCP를 생성하지 않았습니다.

</details>


## 접근·수명주기 확인 문제

11. update-kubeconfig가 Kubernetes 권한을 부여하나요?
   * A) 예, 자동 cluster-admin
   * B) 아니요; 클라이언트 설정이며 권한은 엔트리·정책·RBAC가 결정
   * C) 예, CA 인증서로 부여
   * D) 새 네임스페이스에서만 부여

<details>
<summary>정답 보기</summary>

**정답: B) 아니요; 클라이언트 설정이며 권한은 엔트리·정책·RBAC가 결정**

초기 관리는 부트스트랩·도구 설정에 따라 다릅니다. 허용된 관리자 신원을 유지하고 대상 역할을 명시적으로 테스트하세요.

</details>

12. 네임스페이스 RoleBinding으로 EKS 클러스터 관리자 접근 정책을 좁힐 수 있나요?
   * A) 예, RBAC가 항상 우선
   * B) 아니요, 권한이 합산됨
   * C) 그룹이 system:masters이면 가능
   * D) kubectl --as로만 가능

<details>
<summary>정답 보기</summary>

**정답: B) 아니요, 권한이 합산됨**

의도한 접근 정책 범위나 사용자 정의 RBAC 그룹을 사용합니다. --as·--as-group은 Kubernetes RBAC를 사용하므로 EKS 접근 정책 권한을 검증하지 않습니다.

</details>

13. Pod의 Running 단계 외에 무엇을 확인해야 하나요?
   * A) 없음
   * B) 로그 그룹 이름만
   * C) 준비 상태·롤아웃 및 상태·의도한 애플리케이션 경로
   * D) 모든 Job이 계속 실행 중이어야 함

<details>
<summary>정답 보기</summary>

**정답: C) 준비 상태·롤아웃 및 상태·의도한 애플리케이션 경로**

Running 상태에도 준비되지 않은 컨테이너가 있을 수 있고 완료된 Job은 Succeeded가 정상입니다. 예상 컴퓨팅과 실제 DNS·Service 동작을 검증하세요.

</details>

14. 적절한 EKS 업그레이드 계획은 무엇인가요?
   * A) 임의의 최신 업스트림 버전 사용
   * B) 마이너 두 개를 바로 건너뜀
   * C) EKS 릴리스·준비 상태를 확인하고 한 마이너씩 이동
   * D) 롤백이 모든 영속 데이터를 복원한다고 가정

<details>
<summary>정답 보기</summary>

**정답: C) EKS 릴리스·준비 상태를 확인하고 한 마이너씩 이동**

7일 이내의 조건부 롤백도 etcd·워크로드·데이터를 이전 시점으로 되돌리지 않습니다. 구성 요소 호환성과 백업을 별도 검토하세요.

</details>

15. 클러스터를 폐기하기 전에 무엇을 해야 하나요?
   * A) 모든 PVC 즉시 삭제
   * B) 일반 IAM 역할 이름으로 삭제
   * C) VPC부터 삭제
   * D) 신원·소유권·백업 및 회수 정책·의존성·삭제 보호·Capability 검토

<details>
<summary>정답 보기</summary>

**정답: D) 신원·소유권·백업 및 회수 정책·의존성·삭제 보호·Capability 검토**

원래 IaC 소유자, 명시적으로 검토한 리소스와 완료 검사를 사용합니다. 공유 리소스와 복구 자료를 보존하세요.

</details>

## 참고 자료

- [CloudWatch Observability add-on](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
- [vCluster 0.36.1 configuration](https://github.com/loft-sh/vcluster/blob/v0.36.1/chart/values.yaml)
- [SCP scope](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
