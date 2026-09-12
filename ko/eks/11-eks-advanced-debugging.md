# EKS 고급 디버깅과 장애 대응

> **지원 버전**: EKS 1.28+, kubectl 1.28+
> **마지막 업데이트**: 2026년 9월 9일

Amazon EKS 클러스터의 안정적인 운영을 위해서는 체계적인 장애 대응 프레임워크와 고급 디버깅 기술이 필수입니다. 이 문서에서는 프로덕션 환경에서 발생하는 복잡한 문제들을 신속하게 진단하고 해결하기 위한 실전 가이드를 제공합니다.

## 목차

1. [장애 대응 프레임워크](#1-장애-대응-프레임워크)
2. [컨트롤 플레인 디버깅](#2-컨트롤-플레인-디버깅)
3. [노드 레벨 문제 해결](#3-노드-레벨-문제-해결)
4. [워크로드 디버깅](#4-워크로드-디버깅)
5. [네트워킹 진단](#5-네트워킹-진단)
6. [스토리지 문제 해결](#6-스토리지-문제-해결)
7. [관측성 아키텍처](#7-관측성-아키텍처)
8. [장애 감지 아키텍처](#8-장애-감지-아키텍처)
9. [빠른 참조](#9-빠른-참조)
10. [다음 단계](#10-다음-단계)

---

## 1. 장애 대응 프레임워크

### 첫 5분 체크리스트 (Initial Triage)

기존 단계별 30초·영향 범위 확인 2분·전체 5분은 측정된 완료 시간이 아닌 계획 목표입니다. 고객 영향과 정확한 계정·cluster/context·namespace·최근 변경부터 확인합니다. API client 실패는 credential·authorization·DNS/network·control plane 문제일 수 있으며 실행 중인 모든 앱 중단을 뜻하지 않습니다.

Node condition·Pod/container state·controller rollout·최근 event·resource sample을 함께 봅니다. `phase!=Running`은 Running이면서 NotReady·CrashLooping인 Pod를 놓치고 정상 완료 Job은 포함합니다. Running phase가 readiness를 보장하지 않습니다. Deployment는 `1/1` 같은 화면 문자열 grep 대신 desired·updated·ready/available replica와 observed generation을 비교합니다.

표준 VPC CNI `aws-node` DaemonSet은 보통 `kube-system`에서 실행되며 `amazon-vpc-cni-system` namespace가 EKS 필수 전제는 아닙니다. 순수 Auto Mode는 networking·node system DNS를 달리 관리하므로 표준 add-on Pod 부재는 node·controller mode와 함께 해석합니다. Metrics Server는 수집된 resource sample이며 고객 가용성 신호가 아닙니다.

### 초기 진단 스크립트

선택한 workload namespace와 cluster node·system Pod 상태를 시간 제한 API 요청으로 수집해 비공개로 저장합니다. Secret data나 모든 Pod의 env·설정을 dump하지 않습니다. Log·event·오류 문구에도 앱의 민감 정보가 포함될 수 있으므로 공유 전 검사·삭제합니다. 실행 전 계정·context 입력과 기존 비공개 evidence directory를 확인합니다.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended account ID}"
: "${KUBE_CONTEXT:?Set the explicit kubectl context}"
: "${NAMESPACE:?Set the owned workload namespace}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
test -d "$EVIDENCE_PARENT"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
test "$ACTUAL_ACCOUNT_ID" = "$EXPECTED_ACCOUNT_ID" || { echo "Account mismatch" >&2; exit 1; }
CLUSTER_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.endpoint --output text)
KUBE_ENDPOINT=$(kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
test "$CLUSTER_ENDPOINT" = "$KUBE_ENDPOINT" || { echo "Context/cluster mismatch" >&2; exit 1; }

umask 077
TRIAGE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-triage.XXXXXXXX")
TRIAGE_FAILED=0
k() { kubectl --context "$KUBE_CONTEXT" --request-timeout=15s "$@"; }
collect() {
  local name=$1
  shift
  if "$@" > "$TRIAGE_DIR/$name.txt" 2> "$TRIAGE_DIR/$name.stderr"; then
    printf '%s\tok\n' "$name" >> "$TRIAGE_DIR/status.tsv"
  else
    local rc=$?
    TRIAGE_FAILED=$((TRIAGE_FAILED + 1))
    printf '%s\tfailed:%s\n' "$name" "$rc" >> "$TRIAGE_DIR/status.tsv"
  fi
}
node_health() {
  k get nodes -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
    unschedulable:.spec.unschedulable,taints:.spec.taints,conditions:.status.conditions
  }]'
}
pod_health() {
  k -n "$NAMESPACE" get pods -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,owners:.metadata.ownerReferences,
    deleting:.metadata.deletionTimestamp,phase:.status.phase,conditions:.status.conditions,
    containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
    initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
  }]'
}
deployment_health() {
  k -n "$NAMESPACE" get deployments -o json | jq '[.items[] | {
    name:.metadata.name,generation:.metadata.generation,observed:.status.observedGeneration,
    desired:(.spec.replicas // 1),updated:(.status.updatedReplicas // 0),
    ready:(.status.readyReplicas // 0),available:(.status.availableReplicas // 0),
    conditions:.status.conditions
  }]'
}
load_balancers() {
  k -n "$NAMESPACE" get services -o json | jq '[.items[] | select(.spec.type=="LoadBalancer") | {
    name:.metadata.name,class:.spec.loadBalancerClass,selector:.spec.selector,
    ports:.spec.ports,status:.status.loadBalancer
  }]'
}
collect nodes node_health
collect pods pod_health
collect deployments deployment_health
collect load-balancers load_balancers
collect events k -n "$NAMESPACE" get events --sort-by='.metadata.creationTimestamp'
collect system-pods k -n kube-system get pods -o wide
collect node-resources k top nodes
collect pod-resources k -n "$NAMESPACE" top pods --sort-by=memory
printf 'Private evidence: %s; failed collections: %s\n' "$TRIAGE_DIR" "$TRIAGE_FAILED"
test "$TRIAGE_FAILED" -eq 0
```

`status.tsv`와 각 실패 출력을 확인합니다. 권한 부족·metric 부재·API timeout을 수집 실패로 남기며 하나라도 실패하면 nonzero로 종료합니다. Incident가 해결되었다고 주장하지 않습니다. 완료·Pending·Running 상태를 그대로 보여 주므로 함께 해석합니다. 후속 log는 정확한 namespace·Pod UID·container와 제한한 기간·행 수를 사용합니다.

LoadBalancer 목록은 Service JSON을 로컬 filter합니다. `spec.type`은 기본 Service의 지원 field selector가 아닙니다. 초기 수집에 전체 `cluster-info dump`·자동 archive 업로드·자원 restart·delete를 포함하지 않습니다.

### 장애 심각도 매트릭스 (Severity Matrix)

| 심각도 | 분류 | 영향 범위 | 대응 시간 | 예시 |
|--------|------|-----------|-----------|------|
| **P1** | Critical | 전체 서비스 중단 | 15분 이내 | 컨트롤 플레인 장애, 전체 노드 NotReady |
| **P2** | High | 주요 기능 장애 | 1시간 이내 | 특정 워크로드 전체 실패, 네트워크 연결 문제 |
| **P3** | Medium | 부분적 영향 | 4시간 이내 | 일부 파드 재시작, 성능 저하 |
| **P4** | Low | 경미한 문제 | 24시간 이내 | 로그 수집 지연, 비핵심 모니터링 알림 |

위 심각도별 대응 시간은 조직 목표의 예시입니다. 실제 고객 영향으로 분류하며 control-plane만의 장애에서도 기존 workload traffic은 실행될 수 있습니다.

### 신속한 문제 식별을 위한 의사결정 트리

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![장애 감지 후 서비스 접근 가능 여부를 먼저 묻고, 접근 불가면 kubectl 작동, 노드 Ready, 파드 Running 순으로 컨트롤 플레인·노드·스케줄링·앱 설정 문제를, 접근 가능하면 응답 지연과 간헐적 오류 여부로 워크로드·클러스터 전반·네트워크/DNS 문제를 가려내는 초기 트리아지 의사결정 트리.](../.gitbook/assets/ko-eks-11-eks-advanced-debugging-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-11-eks-advanced-debugging-0.html)
-->

---

## 2. 컨트롤 플레인 디버깅

### EKS 컨트롤 플레인 로그 유형

EKS는 다섯 control-plane log 유형을 제공하며 활성화한 유형만 해당 region의 CloudWatch log group으로 전송합니다. 활성화가 누락된 과거 log를 복구하지는 않습니다. 접근·retention을 제한하고 ingestion·보관·query 비용을 고려합니다. Group·stream 부재는 logging 비활성화·미전송·잘못된 region·권한 거부일 수 있으며 control-plane 장애로 단정하지 않습니다.

| 유형 | 확인할 근거 |
| --- | --- |
| api | API server 동작·오류 |
| audit | API 요청 identity·verb·resource·응답 상태 |
| authenticator | IAM과 Kubernetes 사이 인증 |
| controllerManager | Controller 조정 |
| scheduler | Scheduling 결정·오류 |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
LOG_GROUP="/aws/eks/$CLUSTER_NAME/cluster"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
aws logs describe-log-streams --region "$AWS_REGION" --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime --descending --max-items 10 \
  --query 'logStreams[].{Name:logStreamName,LastEvent:lastEventTimestamp}'
```
```bash
# MUTATION: review cost, retention, access and available subnet IPs first.
set -euo pipefail
UPDATE_ID=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --update-id "$UPDATE_ID" --query update
```
변경은 비동기입니다. 반환 update ID가 Successful인지 추적하며 Failed·Cancelled·client timeout을 성공으로 처리하지 않습니다. 이후 describe-cluster와 새 log 전송을 확인합니다. Cluster ACTIVE만으로 해당 update 완료를 알 수 없습니다. 현재 EKS logging 전제에 따라 설정한 각 cluster subnet에 최대 다섯 개의 가용 IP가 필요할 수 있습니다.

### CloudWatch Logs Insights 쿼리

각 블록을 Bash·SQL이 아닌 **별도의 Logs Insights QL query**로 실행합니다. Console·StartQuery 요청에서 정확한 log group·기간을 선택합니다. CloudWatch가 발견한 EKS JSON audit field를 사용하므로 pipeline이 형식을 바꾸면 실제 record·중첩 log parsing을 확인합니다. 검색 결과가 없다고 서비스 정상·log 전송을 증명하지는 않습니다.

#### API error messages

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 100
```

#### Error counts within the selected time window

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| stats count(*) as error_count by bin(5m)
```

#### Authenticator messages requiring inspection

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /access denied|Unauthorized|unauthorized/
| sort @timestamp desc
| limit 50
```

#### Structured audit authentication/authorization denials

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 100
```

#### Structured audit activity for one reviewed identity

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_OBSERVED_KUBERNETES_USERNAME"
| sort @timestamp desc
| limit 50
```

#### Audit 429 events by identity and resource

```text
fields user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 429
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

#### API request volume, not necessarily throttling

```text
fields user.username, verb, objectRef.resource
| filter @logStream like /kube-apiserver-audit/
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

Audit 401·403은 요청 단위 거부이며 authenticator 문구 검색과 다릅니다. 전체 API 호출 수는 throttled 호출 수가 아니고 time-bin 집계 후에는 각 event의 @timestamp로 정렬할 수 없습니다. StartQuery의 query ID로 GetQueryResults가 Complete인지 확인하고 Failed·Cancelled·Timeout·missing-data를 보존합니다. [모니터링 장](06-eks-monitoring-logging.md)의 제한한 query·polling 절차를 참고합니다. 감사에서 live CloudWatch query는 실행하지 않았습니다.

[EKS control-plane logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html) · [AWS audit-field examples](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)

### IAM 인증 문제 해결

먼저 초기 triage의 계정·context guard를 실행합니다. Kubectl을 사용하는 사람·자동화 IAM identity, node bootstrap identity, 앱 Pod 내부 AWS identity를 구분합니다. Token 생성 성공이 Kubernetes 인증·인가 성공을 증명하지는 않습니다.

k8s-aws-v1으로 시작하는 EKS IAM token은 base64url로 인코딩한 presigned STS 요청이며 **세 부분 JWT가 아닙니다.** JSON처럼 decode·출력하거나 log에 복사하지 않습니다. Kubernetes projected ServiceAccount token은 별도의 JWT credential입니다.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
aws sts get-caller-identity
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,AuthenticationMode:accessConfig.authenticationMode}'
# Print only the credential expiry, not the bearer token.
aws eks get-token --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --query status.expirationTimestamp --output text
kubectl --context "$KUBE_CONTEXT" auth whoami
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" auth can-i get pods
```
AuthenticationMode에 맞춰 access를 확인합니다. API/API_AND_CONFIG_MAP은 principal의 access entry·연결 policy 범위·RBAC binding을, CONFIG_MAP은 기존 legacy mapping을 봅니다. 원인을 확인하지 않은 401·403 때문에 mode를 전환하거나 aws-auth를 교체하지 않습니다. Mode migration에는 별도 전제와 되돌릴 수 없는 전환이 있으며 IAM role path·STS session ARN을 문자열 치환으로 추정하지 않습니다.

```bash
# Run for API or API_AND_CONFIG_MAP authentication mode.
aws eks list-access-entries --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
: "${PRINCIPAL_ARN:?Use a reviewed IAM role/user ARN, not an STS assumed-role session ARN}"
aws eks describe-access-entry --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
aws eks list-associated-access-policies --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
```
```bash
# Read-only legacy mapping inspection for CONFIG_MAP/API_AND_CONFIG_MAP clusters.
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap aws-auth -o yaml
```
기존 node bootstrap mapping을 보존합니다. Group명만으로 권한이 생기지 않으며 대응 binding이 필요합니다. 진단 단계에서 system:masters를 추가하지 말고 검토한 최소 권한을 사용합니다. 403은 인가 거부, 401은 유효하지 않거나 만료한 credential일 수 있으며 network·TLS 실패와 구분합니다.

### IRSA 문제 해결

IRSA에는 올바른 OIDC issuer/provider, namespace·ServiceAccount subject와 sts.amazonaws.com audience에 맞는 trust policy, web-identity credential을 사용·갱신하는 SDK가 필요합니다. 아래 annotation은 일부 설정이며 namespace·role은 placeholder입니다. 이 YAML만으로 role·provider·bucket 권한이 생성되지 않습니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: diagnostics-example
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/owned-s3-access-role
```
```bash
set -euo pipefail
: "${SERVICE_ACCOUNT:?Set the actual ServiceAccount on the Pod}"
: "${POD_NAME:?Set an owned Pod}"; : "${CONTAINER_NAME:?Set its application container}"
: "${IRSA_ROLE_NAME:?Set the reviewed IAM role name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get serviceaccount "$SERVICE_ACCOUNT" \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text
aws iam get-role --role-name "$IRSA_ROLE_NAME" --query Role.AssumeRolePolicyDocument
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid,serviceAccount:.spec.serviceAccountName,
  envNames:[.spec.containers[] | {name,envNames:[.env[]?.name]}],
  projectedVolumes:[.spec.volumes[]? | select(.projected) | {name,projected}]
}'
```
Secret 값·token bytes 대신 env **이름**, token 경로·mount metadata·SDK credential chain을 확인합니다. Static credential이나 앞선 provider가 의도한 identity를 덮을 수 있습니다. 새 debug Pod·container는 identity·설정이 다를 수 있으므로 실제 앱 container를 확인합니다.

```bash
# Optional read-only identity request, only if AWS CLI is already in this container.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- aws sts get-caller-identity
```
STS 응답은 사용 identity를 나타내며 모든 bucket 목록·특정 object 접근 권한을 증명하지는 않습니다. Identity 검사만을 위해 계정 전체 aws s3 ls를 실행하지 않습니다.

### Pod Identity 문제 해결

```bash
aws eks list-pod-identity-associations --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --namespace "$NAMESPACE" --service-account "$SERVICE_ACCOUNT"
: "${ASSOCIATION_ID:?Use the exact matching association ID}"
aws eks describe-pod-identity-association --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --association-id "$ASSOCIATION_ID"
# Standard EC2-node setup only; Auto Mode provides the integration itself.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods \
  -l app.kubernetes.io/name=eks-pod-identity-agent
```
Association·role trust/권한·지원 SDK provider·agent/node 접근성을 확인합니다. Auto Mode에는 기능이 내장되어 agent를 중복 설치하지 않으며 Fargate는 EKS Pod Identity를 지원하지 않습니다. Association 생성·변경은 진단과 분리합니다. IRSA·Pod Identity는 token audience·credential 전달 경로가 다르며 운영자 AWS CLI identity와 기본적으로 같지 않습니다.

### ServiceAccount Token 만료와 갱신

Projected token에 보편적인 “최대 24시간” 규칙은 없습니다. 요청 기간과 API server의 설정 상한은 다릅니다. Kubelet은 TTL의 80%보다 오래되었거나 24시간이 지난 token의 갱신을 요청하며 앱은 교체된 file을 다시 읽어야 합니다. EKS는 Kubernetes API ServiceAccount token migration의 90일 호환성 연장·stale-token audit annotation을 문서화하지만 이를 안전한 cache 기간이나 IRSA·Pod Identity·임의 외부 verifier의 수명 보장으로 쓰지 않습니다.

다음 예시는 STS audience의 custom token을 한 시간으로 요청합니다. 기본 API token을 연장하거나 IRSA를 자동 구성하지 않습니다. 기존 namespace·ServiceAccount, 검토한 image, role trust, 앱 SDK·token-file 설정은 별도 전제입니다. STS audience token이 Kubernetes API에도 유효하다고 가정하지 않습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: audience-token-example
  namespace: diagnostics-example
spec:
  serviceAccountName: owned-app
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
      readOnly: true
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600
          audience: sts.amazonaws.com
```
[EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html) · [EKS token migration/rotation](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) · [Kubernetes projected tokens](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/) · [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) · [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)

### EKS Add-on 오류 패턴

변경 전 설치 version·owner·configuration/identity 설정과 health.issues를 읽습니다. ACTIVE는 add-on 상태이지 모든 고객 traffic 정상의 증명이 아니며 DEGRADED는 단순 속도 저하가 아닌 health issue를 뜻합니다. CREATE_FAILED·UPDATE_FAILED·DELETE_FAILED는 실제 issue 상세를 확인합니다. Auto Mode 관리 기능에는 표준 add-on 부재가 정상일 수 있습니다.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${ADDON_NAME:?Set the existing owned add-on}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" \
  --query 'addon.{Version:addonVersion,Status:status,Issues:health.issues,Configuration:configurationValues,Role:serviceAccountRoleArn,PodIdentity:podIdentityAssociations}'
CLUSTER_VERSION=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version "$CLUSTER_VERSION" \
  --query 'addons[].addonVersions[].{Version:addonVersion,Architectures:architecture,ComputeTypes:computeTypes,Compatibility:compatibilities}'
```
응답 첫 version을 “최신” 또는 모든 node 유형에 자동 호환되는 값으로 선택하지 않습니다. Architecture·compute type·default 표시·configuration schema·IAM/Pod Identity·component migration 순서를 검토합니다. Configuration 출력은 민감할 수 있으므로 비공개로 취급합니다. Version update는 초기 진단이 아닌 의도한 변경입니다.

```bash
# MUTATION: use a reviewed compatible version and configuration/identity plan.
set -euo pipefail
: "${REVIEWED_ADDON_VERSION:?Choose from the compatible versions after review}"
: "${REVIEWED_ADDON_CONFIG:?Set the path to the reviewed JSON configuration file}"
test -f "$REVIEWED_ADDON_CONFIG"
aws eks describe-addon-configuration --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --addon-version "$REVIEWED_ADDON_VERSION" --query configurationSchema --output text
# The configuration file must be checked against this version's schema before this request.
UPDATE_ID=$(aws eks update-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --addon-version "$REVIEWED_ADDON_VERSION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG" \
  --resolve-conflicts PRESERVE --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --update-id "$UPDATE_ID" --query update
```
PRESERVE는 conflict 처리에서 기존 custom 설정 보존을 요청하지만 backup이나 임의의 이전 설정이 새 release에서도 동작한다는 보장은 아닙니다. OVERWRITE는 충돌한 custom 설정을 초기화할 수 있어 별도 검토합니다. 정확한 update ID의 완료·오류와 변경 후 add-on health를 확인합니다. configurationValues·identity 변경을 조용히 생략·덮어쓰지 말고 명시적으로 검토합니다.

[Update an EKS add-on](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)

---

## 3. 노드 레벨 문제 해결

### 노드 조인 실패 진단

다음은 instance·NodeClaim·bootstrap log·endpoint 접근·authentication mode로 검증할 가설이며 확정 원인 목록이 아닙니다.

| 영역 | 확인할 항목 |
| --- | --- |
| Bootstrap·AMI | 정확한 cluster명·endpoint·CA, OS별 bootstrap, architecture·호환 kubelet/AMI; 모든 경우 version이 정확히 같아야 한다는 규칙은 아님 |
| Network·보안 | Node→API TCP 443, API→kubelet TCP 10250, DNS·workload별 경로; 방향·SG membership·routing 확인 |
| VPC DNS | DNS support/hostname·DHCP resolver/domain·실제로 사용하는 endpoint |
| Identity | Node IAM role과 Kubernetes node access entry/legacy mapping; instance-profile ARN과 role ARN 구분 |
| 소유·탐색 tag | Provisioner별 node ownership tag; LB 탐색용 subnet tag와 구분 |
| Private 접근 | 검토한 endpoint·egress를 통한 EKS/ECR/S3/STS 등 필수 경로; 모든 private cluster가 NAT를 요구하지 않음 |
| Launch 설정 | 해당 provisioner의 role/profile 처리, launch-template version, capacity·subnet IP |
| 초기화 | 선택 AMI에 맞는 nodeadm·cloud-init·bootstrap 근거; AL2023·Bottlerocket·Windows·Auto Mode의 경로는 같지 않음 |

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?Set the exact owned node name}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
  os:.status.nodeInfo.osImage,kernel:.status.nodeInfo.kernelVersion,
  kubelet:.status.nodeInfo.kubeletVersion,runtime:.status.nodeInfo.containerRuntimeVersion,
  labels:.metadata.labels,taints:.spec.taints,conditions:.status.conditions
}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.uid=$NODE_UID" --sort-by='.metadata.creationTimestamp'
```
```bash
# EC2-backed nodes only: map the Node providerID to an inspected instance ID/Region.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the verified EC2 ID, not a guessed node-name conversion}"
aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,AZ:Placement.AvailabilityZone,Subnet:SubnetId,Profile:IamInstanceProfile,Groups:SecurityGroups,Image:ImageId}'
aws ec2 describe-instance-status --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --include-all-instances
```
아직 등록되지 않은 instance에는 Node 객체가 없으므로 소유 managed-node-group·NodeClaim·instance 근거를 사용합니다. Ready=False와 heartbeat 부재로 인한 Ready=Unknown을 구분합니다. Resource pressure는 Ready와 함께 나타날 수 있으므로 화면 문자열 하나로 원인을 추정하지 않습니다. 신규 Auto Mode EC2 managed instance는 일반 목록에 기본 숨김일 수 있습니다. 직접 instance ID 조회·managed resource 포함과 계정 전체 visibility 변경을 구분합니다.

### NotReady 노드 의사결정 트리

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![EC2 상태부터 kubelet, 네트워크, 디스크/메모리 압력, 컨테이너 런타임까지 단계적으로 점검해 노드가 NotReady가 된 원인을 좁혀가는 체크리스트형 의사결정 트리.](../.gitbook/assets/ko-eks-11-eks-advanced-debugging-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-11-eks-advanced-debugging-1.html)
-->

### Host·관리 node 진단

고객이 접근 가능한 Linux node의 SSM에는 node agent·role/network 전제와 정확한 instance 접근 권한이 필요하며 session을 엽니다. EKS Auto Mode managed instance는 직접 SSH를 지원하지 않습니다. 문서화된 NodeDiagnostic·console-output 또는 지원 kubectl debug node 경로를 사용합니다. 현재 Auto Mode 가이드는 live log용 **명시적 sysadmin debug profile**을 지원합니다. 이는 privileged Pod 생성이며 SSH나 기본 debug 권한이 아닙니다. NodeDiagnostic은 민감한 log·capture를 S3에 업로드할 수 있어 별도 범위·저장 권한 검토가 필요합니다.

```bash
# Interactive host access: an operational session, not an automatic triage step.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the reviewed self-managed or managed-node-group instance}"
aws ssm start-session --region "$AWS_REGION" --target "$INSTANCE_ID"
```
```bash
# Read-only Linux/systemd host checks after authorized access.
sudo systemctl show kubelet containerd --no-pager \
  -p Id -p LoadState -p ActiveState -p SubState -p ExecMainStatus
sudo journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
sudo journalctl -u containerd --since "15 minutes ago" -n 100 --no-pager
sudo crictl info
sudo crictl ps
sudo crictl ps -a
sudo crictl images
df -h
df -i
sudo journalctl --disk-usage
```
```bash
# Exact container ID only; log content may be sensitive.
: "${CONTAINER_ID:?Use an inspected CRI container ID}"
sudo crictl logs --tail=100 "$CONTAINER_ID"
```
Systemd·CRI 명령은 선택 host에 해당 component·도구가 있다는 전제입니다. Crictl의 올바른 CRI endpoint를 확인합니다. Journal은 기간·행 수를 제한하며 journalctl -f를 tail에 연결하면 끝나지 않을 수 있습니다. Kubeconfig·client key를 출력하거나 log·종료 container·image cache를 일괄 삭제하지 않습니다. 증거이거나 kubelet GC가 관리하는 자원일 수 있습니다. Restart·drain·replacement·retention 변경은 원인 확인 뒤 별도 검토한 복구 단계입니다.

### Resource Pressure

DiskPressure는 df 용량뿐 아니라 가용 byte/inode·설정한 eviction threshold와 관련됩니다. df -h·df -i·mount·kubelet event를 함께 봅니다. Retention 정리를 허용한 경우에도 기존 journalctl --vacuum-size=500M은 정책 예시이며 필요한 증거를 먼저 확보하고 /var/log glob을 지우지 않습니다. MemoryPressure와 container OOM은 다릅니다. Limit·node 가용 memory·working set·log·pressure metric을 대조합니다. Limit·node 증가만으로 원인 해결을 증명하지 못합니다.

```bash
# Read-only host evidence, not remediation.
free -h
awk '/MemTotal|MemFree|MemAvailable|Buffers|Cached/ {print}' /proc/meminfo
cat /proc/sys/kernel/pid_max
cat /proc/sys/kernel/threads-max
ps -eLf --no-headers | wc -l
ps -eo pid,comm,nlwp --sort=-nlwp | head -20
if [ -r /proc/pressure/memory ]; then cat /proc/pressure/memory; fi
if [ -r /proc/pressure/cpu ]; then cat /proc/pressure/cpu; fi
```
/proc process directory 수는 전체 thread/task 수가 아닙니다. Ps NLWP·kernel limit는 단서이며 kubelet PID-pressure 계산·cgroup PID limit와 구분합니다. 일반 memory 사용률을 Kubernetes MemoryPressure condition이라고 표시하지 않습니다. Metric 부재는 근거 없음으로 처리합니다.

### Karpenter 프로비저닝 문제

```bash
# Self-managed Karpenter; use the actual release namespace and selected objects.
: "${KARPENTER_NAMESPACE:?Set the existing controller namespace}"
: "${NODEPOOL_NAME:?}"; : "${NODECLAIM_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$KARPENTER_NAMESPACE" logs \
  -l app.kubernetes.io/name=karpenter -c controller --since=15m --tail=200 --prefix
kubectl --context "$KUBE_CONTEXT" get nodepool "$NODEPOOL_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get nodeclaim "$NODECLAIM_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.name=$NODECLAIM_NAME" --sort-by='.metadata.creationTimestamp'
```
NodePool·NodeClass readiness, NodeClaim condition/event, constraints·limit·subnet IP·IAM·EC2 capacity를 확인합니다. Auto Mode는 내장 controller의 NodeClaim·NodeClass·event·audit log를 확인하며 self-managed karpenter Deployment·namespace를 기대하지 않습니다. 아래 self-managed v1 schema는 호환 release·검토한 기존 EC2NodeClass가 필요한 예시이며 기존 default pool 교체 명령이 아닙니다. CPU/memory limit는 예약 용량이 아닌 상한이고 capacity-type 목록이 Spot 전용·AZ 균형을 증명하지 않습니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-capacity-example
spec:
  template:
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      - key: karpenter.k8s.aws/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-existing-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
```
### Managed Node Group 오류 코드

| Issue | 의미·확인할 근거 |
| --- | --- |
| AccessDenied | Kubernetes API 인증·인가 실패; IAM뿐 아니라 node access·EKS node-manager RBAC 확인 |
| AsgInstanceLaunchFailures | ASG launch 실패; 실제 activity message·template·capacity·권한 확인 |
| ClusterUnreachable | Kubernetes API 연결·요청 처리 timeout; VPC endpoint 누락으로 단정하지 않음 |
| InsufficientFreeAddresses | 선택한 node subnet의 가용 IP 부족; 기존 subnet IPv4 CIDR은 제자리 확장 불가 |
| NodeCreationFailure | 시작한 instance 등록 실패; bootstrap·access·필수 network 경로 확인 |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${NODEGROUP_NAME:?Set the exact managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Issues:health.issues,Version:version,Release:releaseVersion,Subnets:subnets,Role:nodeRole,LaunchTemplate:launchTemplate,Repair:nodeRepairConfig}'
# For a Kubernetes authorization issue, inspect rather than blindly replace EKS-managed RBAC.
kubectl --context "$KUBE_CONTEXT" get clusterrole eks:node-manager -o yaml
kubectl --context "$KUBE_CONTEXT" get clusterrolebinding eks:node-manager -o yaml
```
각 issue의 message·resourceIds와 현재 AWS 복구 절차를 사용합니다. Troubleshooting 가이드는 managed node가 15분 안에 join하지 못하면 NodeCreationFailure가 나타날 수 있다고 설명하며 모든 boot가 그 안에 끝난다는 보장은 아닙니다. 공간이 부족하면 기존 CIDR 편집 대신 신규 주소 공간·subnet·provisioner별 migration을 계획합니다. EKS 관리 RBAC shape는 바뀔 수 있으므로 AccessDenied만 보고 이전 ClusterRole을 덮어쓰지 않습니다. Node repair·eviction은 진단과 별개이며 workload·budget·data·node 관리 mode를 고려합니다.

[EKS troubleshooting](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html) · [Auto Mode diagnostic paths](https://docs.aws.amazon.com/eks/latest/userguide/auto-troubleshoot.html) · [Security group paths](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html) · [Private clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html) · [Karpenter compatibility](https://karpenter.sh/docs/upgrading/compatibility/)

### Node Readiness Controller (단계별 부팅 검증)

Kubernetes SIGs Node Readiness Controller는 실제 별도 controller입니다. 검토한 v0.5.0은 cluster 범위의 `readiness.node.x-k8s.io/v1alpha1` `NodeReadinessRule`을 사용하며 EKS 내장 ConfigMap 처리기나 Node API의 GA field가 아닙니다.

Controller는 Node condition을 읽고 taint를 관리합니다. ConfigMap의 임의 `checks[].probe.exec`를 실행하지 않습니다. 기존 file 존재·containerd check에는 대응 condition을 게시하는 별도 구현·권한을 갖춘 reporter 또는 NPD custom monitor가 필요합니다. CNI 설정 file 존재만으로 CNI 준비 완료를 증명하지 못합니다. 프로젝트의 기본 reporter는 `CHECK_ENDPOINT`·`CONDITION_TYPE`·`NODE_NAME`으로 HTTP endpoint를 poll하며 이전 exec-probe 형식을 사용하지 않습니다.

아래는 명시적인 test 범위의 **taint 미리보기**입니다. 적용하면 cluster resource가 생성되고 controller가 status를 갱신하지만 `dryRun: true`는 node taint를 추가·제거하지 않습니다. 예제 condition명·node label은 EKS가 자동 공급하는 값이 아닌 custom 전제입니다.

```yaml
apiVersion: readiness.node.x-k8s.io/v1alpha1
kind: NodeReadinessRule
metadata:
  name: reviewed-bootstrap-readiness
spec:
  dryRun: true
  enforcementMode: bootstrap-only
  nodeSelector:
    matchLabels:
      audit.example.com/readiness-demo: 'true'
  conditions:
  - type: audit.example.com/CNIReady
    requiredStatus: 'True'
  - type: audit.example.com/ContainerRuntimeReady
    requiredStatus: 'True'
  taint:
    key: readiness.k8s.io/bootstrap-not-ready
    value: pending
    effect: NoSchedule
```

실제 enforcement 전에 `status.dryRunResults`·`status.nodeEvaluations`·failed node와 선택한 Node condition을 확인합니다.

```bash
# Read-only: the controller and released CRD must already be installed.
: "${KUBE_CONTEXT:?Set the verified context}"
kubectl --context "$KUBE_CONTEXT" get nodereadinessrule reviewed-bootstrap-readiness -o yaml
kubectl --context "$KUBE_CONTEXT" get nodes \
  -l audit.example.com/readiness-demo=true -o json
```

Bootstrap gate는 controller와 scheduling의 경합 전에 새 node가 일치하는 startup taint로 등록되어야 합니다. Reporter·필수 system DaemonSet은 해당 taint를 tolerate하고 API에 접근할 수 있어야 합니다. 모든 조건 충족 후 bootstrap-only는 taint를 제거하고 완료를 기록하며 이후 condition 장애에 gate를 다시 적용하지 않습니다. Continuous는 별도 정책 선택입니다.

`NoSchedule`은 taint를 tolerate하지 않는 새 Pod를 제한하며 기존 Pod를 eviction하지 않습니다. Bootstrap-only에 `defaultStatus`를 설정하는 조합은 release에서 거부합니다. 여기의 CRD 검증이 reporter health·admission webhook·모든 EKS node 유형의 운영 동작을 증명하지는 않습니다. 감사 중 node label·taint·controller·condition을 변경하지 않았습니다.

[Release v0.5.0](https://github.com/kubernetes-sigs/node-readiness-controller/releases/tag/v0.5.0) · [Enforcement and dry-run semantics](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/user-guide/concepts.md) · [Reporter configuration](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/reference/reporter-configuration.md)

---

## 4. 워크로드 디버깅

### Pod와 Container 상태

Pod phase는 Pending·Running·Succeeded·Failed·Unknown입니다. Container state는 Waiting·Running·Terminated이며 ContainerCreating·CrashLoopBackOff는 추가 Pod phase가 아닌 reason·표시 정보입니다. Running과 Ready는 다릅니다. Restart policy는 Pod 내 container를 재시작할 수 있지만 terminal Failed Pod를 Pending으로 되돌리지 않습니다. Controller가 교체한 Pod는 새로운 UID의 객체입니다.

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![파드가 Pending에서 이미지 풀과 실행을 거쳐 Succeeded로 끝나거나 Failed를 통해 재시작 정책에 따라 다시 Pending으로 돌아가는 생명주기와, 각 단계에서 흔히 발생하는 실패 원인을 보여주는 상태 다이어그램.](../.gitbook/assets/ko-eks-11-eks-advanced-debugging-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-11-eks-advanced-debugging-2.html)
-->

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,node:.spec.nodeName,
  phase:.status.phase,reason:.status.reason,conditions:.status.conditions,
  containers:.status.containerStatuses,initContainers:.status.initContainerStatuses,
  ephemeralContainers:.status.ephemeralContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=200
```
```bash
# Separate read: this can fail when no previous container log exists.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --previous --tail=200
```
Previous log는 선택 container의 가장 최근 종료 instance에 대한 것이며 전체 restart 이력이 아닙니다. Rotation·Pod 삭제로 없어질 수 있습니다. 수집 시 UID·시간·교체 여부를 기록하고 init·sidecar·ephemeral container별 실패를 구분합니다. Log·state message에도 민감 정보가 있을 수 있으므로 비공개로 보관합니다. 진단 편의를 위해 전체 env·앱 config를 출력하지 않습니다.

### kubectl debug: 세 가지 다른 작업

Ephemeral container는 기존 Pod를 변경하고 --copy-to는 다른 Pod를, node/는 node 진단 Pod를 생성합니다. 모두 변경 작업이며 대응 RBAC·admission 권한이 필요합니다. 확인한 kubectl 1.36.2의 기본 profile은 general이며 자동 privileged를 뜻하지 않습니다. Host namespace·filesystem 접근과 privileged=true도 구분합니다.

#### Ephemeral container

```bash
# MUTATION: adds a permanent-to-this-Pod-spec ephemeral-container entry.
: "${DEBUG_IMAGE:?Use a reviewed non-root diagnostic image with a compatible shell}"
: "${DEBUG_CONTAINER_NAME:?Choose an unused container name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" -it \
  --container="$DEBUG_CONTAINER_NAME" --target="$CONTAINER_NAME" \
  --image="$DEBUG_IMAGE" --profile=restricted -- sh
```
Restricted profile은 capability를 제거하고 privilege escalation을 막으며 non-root·RuntimeDefault seccomp를 요구합니다. Image·user·shell이 이를 지원해야 하며 임의 root 전용 BusyBox가 시작된다고 보장하지 않습니다. --target은 runtime이 지원할 때 대상 process namespace를 요청할 뿐 앱 filesystem·env 복제나 권한 우회가 아닙니다. 종료해도 기존 Pod spec의 ephemeral-container entry를 삭제할 수는 없습니다.

#### Pod 복사

```bash
# MUTATION: copy only a reviewed reproduction Pod; inspect all side effects first.
: "${DEBUG_POD_NAME:?Choose a new owned Pod name in the same namespace}"
: "${DEBUG_IMAGE:?Use a reviewed diagnostic image that provides sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --keep-labels=false --keep-annotations=false \
  --share-processes=true --profile=general -- sleep 3600
```
Native CLI 검증에서 선택 container image·command 교체, init container 제거, ServiceAccount 유지·process namespace 공유를 확인했습니다. 다른 일반 container·env/Secret 참조·volume은 남아 실행되거나 같은 data를 사용할 수 있습니다. 복사본은 같은 namespace에 있고 다른 node에 배치될 수 있으며 격리된 data clone이 아닙니다. Admission 변경·부작용·identity·persistent volume·정리를 먼저 검토합니다. General capability가 namespace policy에 거부될 수 있으며 policy를 조용히 낮추지 않습니다.

#### Node 진단

```bash
# MUTATION: privileged host diagnostic Pod, only where this access is authorized.
: "${NODE_NAME:?Use the exact reviewed Node}"
: "${NODE_DEBUG_IMAGE:?Use a reviewed image with nsenter}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" -it \
  --image="$NODE_DEBUG_IMAGE" --profile=sysadmin \
  -- nsenter -t 1 -m -- journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
```
Node debug는 /host에 host root를 mount하고 host namespace를 사용하며 명시적 sysadmin은 privileged를 추가합니다. 명령이 log 조회여도 광범위한 host 접근 권한입니다. Image에 필요한 도구가 준비되어야 합니다. Auto Mode guide는 이 경로를 지원하지만 일반 SSH 접근은 여전히 불가합니다. 다른 OS/node 유형은 지원 경로를 사용하며 kubelet/runtime/network가 고장 나면 새 debug Pod가 시작된다고 보장하지 않습니다.

실제 생성된 debug Pod명·UID를 기록하고 증거 검토 후 해당 별도 Pod만 제거합니다. Ephemeral container 정리를 이유로 application Pod를 삭제하지 않습니다.

```bash
# MUTATION: remove only the separately created debug Pod after checking its identity.
: "${DEBUG_POD_NAME:?}"; : "${EXPECTED_DEBUG_UID:?Use the UID recorded at creation}"
ACTUAL_DEBUG_UID=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$DEBUG_POD_NAME" \
  -o jsonpath='{.metadata.uid}')
test "$ACTUAL_DEBUG_UID" = "$EXPECTED_DEBUG_UID" || { echo "Debug Pod changed; stop" >&2; exit 1; }
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" delete pod "$DEBUG_POD_NAME" --timeout=2m
```
UID 확인은 안전 확인이며 원자적인 delete precondition은 아닙니다. 확인과 삭제 사이 이름 재사용이 없도록 작업을 조정합니다. 감사에서 debug container·privileged workload·node 명령을 실행하지 않았으며 native CLI 검증에는 로컬 모의 API만 사용했습니다.

### Deployment 롤아웃 관리

```bash
# Read-only rollout evidence.
: "${DEPLOYMENT_NAME:?Set the owned Deployment}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=2m
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout history "deployment/$DEPLOYMENT_NAME"
```
```bash
# MUTATION: workload revision rollback, not database/PVC/control-plane rollback.
set -euo pipefail
: "${REVIEWED_REVISION:?Set an inspected compatible revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout undo \
  "deployment/$DEPLOYMENT_NAME" --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=5m
```
Timeout·실패는 조사할 근거이지 성공이 아닙니다. GitOps·다른 reconciler와 조정하며 rollout rollback이 database·schema 변경을 복원하지는 않습니다. Deployment pause/resume은 rollout 진행을 제어하며 HPA·모든 Pod 생성을 중지하지 않습니다. Rollout restart는 같은 image 참조여도 template 변경·replacement를 일으키며 미고정 image는 다른 content로 해석될 수 있습니다. 정확한 namespace·Deployment의 검토한 계획으로 실행하고 restart·undo·scale을 triage에 묶지 않습니다.

### HPA/VPA 스케일링 문제

```bash
# Read-only: use the actual scaler names and workload namespace.
: "${HPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa "$HPA_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe hpa "$HPA_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: diagnostics-example
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```
```bash
# VPA is a separately installed controller/CRD, not built into EKS.
: "${VPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get vpa "$VPA_NAME" -o json | jq '{
  target:.spec.targetRef,updatePolicy:.spec.updatePolicy,resourcePolicy:.spec.resourcePolicy,
  recommendation:.status.recommendation,conditions:.status.conditions
}'
```
HPA 예시는 기존 Deployment·resource-metrics provider와 대상 container의 CPU/memory request가 필요합니다. Utilization은 limit가 아닌 request 대비 비율입니다. 여러 metric은 가장 큰 권장 replica를 선택하며 missing·error metric도 결정에 영향을 줍니다. Memory utilization이 leak·OOM의 보편적 해결은 아니며 scale-down 안정화·변경률 정책도 일시정지 스위치가 아닙니다.

VPA는 별도 설치합니다. 실제 recommendation·condition·update mode·지원 release를 확인합니다. 현재 안내에서 legacy Auto mode명은 deprecated이며 recommendation 전용 Off 또는 검토한 update mode를 선택합니다. HPA의 동일한 request 분모를 VPA가 변경하도록 할 때는 조정이 필요합니다.

### Probe 설정

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-probe-example
  namespace: diagnostics-example
spec:
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    ports:
    - name: http
      containerPort: 8080
    startupProbe:
      httpGet:
        path: /healthz
        port: http
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 30
    livenessProbe:
      httpGet:
        path: /healthz
        port: http
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: http
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
```
Placeholder image·health endpoint를 실제 앱 계약으로 교체합니다. Standalone Pod는 schema 예시이며 복제된 production workload가 아닙니다. Startup 성공 전 liveness·readiness가 억제됩니다. 5초 주기 30회와 initial delay는 대략적인 startup budget이며 정확한 150초 deadline이 아닙니다. Readiness 실패는 service routing의 readiness를 내리며 container를 재시작하지 않습니다. 외부 의존성이 느리다는 이유만으로 정상 process를 liveness가 재시작하게 하지 않습니다. Shutdown·resource pressure·실제 응답 시간을 별도 검증합니다.

[Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) · [Debug running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) · [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [VPA modes](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)

---

## 5. 네트워킹 진단

### VPC CNI·IP 할당

먼저 node·network 구현을 구분합니다. 아래 aws-node 설정은 표준 Amazon VPC CNI 경로입니다. Auto Mode는 자체 관리 networking·NodeClass 설정을 사용하므로 aws-node DaemonSet 변경이 Auto Mode node 설정은 아닙니다. Windows·Fargate·Hybrid Node의 적용 범위·진단 경로도 다릅니다. 초기 계정·context guard와 정확한 node·namespace 범위를 유지합니다.

```bash
# Standard Amazon VPC CNI on applicable nodes, not an Auto Mode control interface.
: "${KUBE_CONTEXT:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the inspected EC2 node ID}"
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset aws-node -o json | jq '{
  containers:[.spec.template.spec.containers[] | {name,image,settings:[
    .env[]? | select(.name | IN("ENABLE_PREFIX_DELEGATION","WARM_PREFIX_TARGET","WARM_IP_TARGET",
      "MINIMUM_IP_TARGET","AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG","ENI_CONFIG_LABEL_DEF"))
  ]}]
}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=aws-node -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=aws-node \
  -c aws-node --since=15m --tail=100 --prefix
aws ec2 describe-network-interfaces --region "$AWS_REGION" \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,Subnet:SubnetId,Description:Description,IPv4:PrivateIpAddresses[].PrivateIpAddress,IPv4Prefixes:Ipv4Prefixes,IPv6Prefixes:Ipv6Prefixes,Groups:Groups}'
```
```bash
# Read-only: use subnets actually selected by the node/provisioner, not all account subnets.
: "${SUBNET_ID:?Set an inspected subnet ID}"
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{ID:SubnetId,VPC:VpcId,AZ:AvailabilityZone,CIDR:CidrBlock,AvailableIPv4:AvailableIpAddressCount}'
```
ENI description은 소유권 경계가 아닙니다. 확인한 instance·subnet ID와 관련 custom-networking·Pod ENI를 사용합니다. Subnet의 free-address 수가 연속된 prefix 가용성을 증명하지 않고 VPC CIDR 추가만으로 Pod network가 설정되지 않습니다.

### Prefix Delegation

지원하는 Linux·Nitro·CNI 구성에서는 prefix delegation으로 IP 밀도·할당 동작을 개선할 수 있습니다. 연속 prefix 공간·예약, ENI/prefix limit, node maxPods·allocatable Pod와 migration 준비를 확인합니다. 실행 node에서 무조건 활성화하거나 가용 IPv4 수만으로 실제 용량을 추정하지 않습니다.

다음은 **검토용 configuration fragment**이며 실제 지원 add-on·chart 설정에 병합할 값입니다. 기존 설정 전체를 교체하는 파일이 아닙니다.

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
설정한 WARM_IP_TARGET·MINIMUM_IP_TARGET은 WARM_PREFIX_TARGET보다 우선합니다. Warm target은 여분 주소·prefix를 유지할 뿐 node 용량 예약이나 고갈·단편화 subnet 복구가 아닙니다. 저장 configuration·owner를 검토한 뒤 통제된 rollout을 수행하고 새 Pod·실제 IPAM 상태를 확인합니다.

### Custom Networking

CNI mode 변경 전에 겹치지 않는 VPC 주소 공간, 실제 AZ별 Pod subnet, routing·egress·SG와 migration 용량을 준비합니다. 기존 CIDR·subnet 생성 몇 줄과 env toggle은 완전한 운영 절차가 아니었습니다. 기존 subnet IPv4 CIDR은 제자리 확장할 수 없습니다. 아래 표준 ENIConfig 방식은 Auto Mode networking 제어와 구분합니다.

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```
```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
```
ENIConfig는 placeholder ID를 사용하는 한 AZ 예시입니다. Zone 기반 선택이면 모든 eligible zone에 정확한 설정과 대응 node label이 필요합니다. AZ당 Pod subnet이 여러 개면 별도 선택 체계를 설계합니다. Pod용 SG 설정에 따라 적용 SG가 달라질 수 있으므로 설치 CNI의 우선순위를 확인합니다. Controller 설정·새 node rollout·Pod 배치를 검증한 뒤 이전 용량을 정리합니다. 전체 설정은 [네트워킹 가이드](03-eks-networking-part1.md)를 참고합니다.

### CoreDNS·Resolver 문맥

순수 Auto Mode node는 CoreDNS를 node system service로 실행합니다. 혼합 cluster는 non-Auto node용 Deployment를 유지해야 하며 순수 Auto에서 Deployment 부재만으로 DNS 장애라 할 수 없습니다. Deployment 기반 DNS는 다음을 확인합니다.

```bash
# CoreDNS Deployment on standard/mixed clusters; Auto Mode node-system DNS differs.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --since=15m --tail=100 --prefix
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
# Inspect the actual resolver context in an owned application container with these tools.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- cat /etc/resolv.conf
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```
관련 logging 설정이 없으면 CoreDNS가 모든 DNS query를 기록하지는 않습니다. 새 test Pod는 장애 workload와 namespace·node·DNS·identity·policy 경로가 다를 수 있습니다. 실제 resolver 문맥에서 절대 해석 검증에는 끝에 점이 있는 FQDN을 사용합니다.

아래 ndots=2는 지연의 보편적 해결책이 아닌 실험 값입니다. Search 동작·부분 수식 이름에 영향을 줄 수 있습니다. Libc·언어 resolver·앱 cache가 다르므로 glibc의 single-request-reopen 같은 옵션을 이식 가능한 전제로 쓰지 않습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-options-example
  namespace: diagnostics-example
spec:
  dnsPolicy: ClusterFirst
  dnsConfig:
    options:
    - name: ndots
      value: '2'
    - name: timeout
      value: '2'
    - name: attempts
      value: '3'
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
```
다음 Corefile은 예시입니다. 설치 version·필수 plugin·custom zone/forwarder·managed add-on 설정과 비교하고 live ConfigMap을 통째로 덮어쓰지 않습니다. Cache·max_concurrent·lameduck 값은 traffic·health 검증이 필요합니다. Pods insecure는 Kubernetes plugin의 Pod-record mode이며 API TLS·인증을 끄는 옵션이 아닙니다.

```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
        max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
```
### Service·EndpointSlice 검증

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json | jq '{
  name:.metadata.name,type:.spec.type,clusterIP:.spec.clusterIP,ipFamilies:.spec.ipFamilies,
  externalName:.spec.externalName,selector:.spec.selector,ports:.spec.ports,
  trafficDistribution:.spec.trafficDistribution,externalTrafficPolicy:.spec.externalTrafficPolicy
}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o json | jq '[.items[] | {
    name:.metadata.name,addressType,ports,
    endpoints:[.endpoints[]? | {addresses,conditions,nodeName,zone,targetRef}]
  }]'
```
현재 endpoint 검증은 EndpointSlice를 사용하며 이전 Endpoints API는 deprecated입니다. Service selector·port/targetPort·address family·endpoint ready/serving/terminating을 확인합니다. Headless·ExternalName·selectorless Service는 동작이 다릅니다. Endpoint 주소 존재가 의도한 traffic 수신을 증명하지 않으며 Service port와 container port가 항상 같지는 않습니다.

### NetworkPolicy AND/OR 로직

한 peer의 namespaceSelector·podSelector는 AND이며 별도 peer·rule은 대안입니다. PodSelector만 있는 peer는 policy namespace 안의 Pod를 선택합니다. 모든 적용 NetworkPolicy의 허용은 합집합이며 제한적인 policy가 다른 broad allow를 덮어쓰지 않습니다. Manifest를 firewall로 믿기 전에 실제 CNI·node 유형의 enforcement 지원·mode를 확인합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reviewed-api-policy
  namespace: diagnostics-example
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app.kubernetes.io/name: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context "$KUBE_CONTEXT" get namespaces --show-labels
```
예시는 일치하는 CoreDNS Pod로 TCP·UDP DNS를 허용합니다. Database-only egress만 있으면 DNS가 빠집니다. Node-local·Auto Mode DNS는 경로가 다르므로 mode별 확인이 필요합니다. 실제 monitoring·database label·port와 검토한 외부 의존성만 적용합니다. 예시 policy이며 입증된 production allowlist가 아닙니다.

### 범위를 제한한 Network Test

```bash
# An intentional, bounded request from the actual workload context with curl installed.
: "${HEALTH_URL:?Set the owned safe health-check URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```
```bash
# In an approved diagnostic context with the named tools.
: "${SERVICE_FQDN:?Set the exact owned service DNS name}"
dig +time=2 +tries=1 "$SERVICE_FQDN"
# Packet capture needs the appropriate capabilities/privileges and an owned target.
: "${TARGET_IP:?Set one reviewed peer IP}"
umask 077
timeout 30 tcpdump -i any -nn -c 100 -s 96 "host $TARGET_IP and port 443" -w owned-capture.pcap
# Separate deliberate load test: only against an agreed iperf3 server.
: "${IPERF_SERVER:?Set the owned test server}"
iperf3 -c "$IPERF_SERVER" -p 5201 -t 10 -P 1 -b 10M
```
앞의 debug 절차로 검토한 image·도구 구현을 선택합니다. Netshoot Pod 생성은 수동 관찰이 아닌 변경입니다. Packet capture는 root 사용자명만이 아니라 capability·privilege가 필요하고 범위를 제한해도 민감 header·data가 포함될 수 있어 비공개 보관·공유 전 검토가 필요합니다. Dig +trace는 workload resolver만이 아닌 직접 iterative DNS 경로를 검사합니다. Iperf3는 의도적인 traffic 생성이며 throughput은 network latency도, 이 감사의 실측 결과도 아닙니다.

[Prefix mode](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html) · [Custom networking](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html) · [NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/) · [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)

---

## 6. 스토리지 문제 해결

### Driver·권한 식별

연결된 PV의 spec.csi.driver·volumeHandle과 StorageClass provisioner를 읽습니다. 표준 EBS는 ebs.csi.aws.com, Auto Mode는 ebs.csi.eks.amazonaws.com과 관리 controller를 사용하므로 표준 controller Deployment가 없을 수 있습니다. 아래 표준 driver log 명령은 해당 driver 설치를 전제합니다. Fargate Pod·EKS Hybrid Node에는 EBS를 mount할 수 없으며 표준 controller를 Fargate에 배치해도 data-plane 제약은 달라지지 않습니다.

```bash
# Read-only: identify the actual installed driver and workload owner first.
kubectl --context "$KUBE_CONTEXT" get csidrivers
: "${CSI_NAMESPACE:?Set the namespace of the installed standard CSI controller}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" get deployments,daemonsets,pods -o wide
: "${CSI_CONTROLLER_NAME:?Use an observed controller Deployment name}"
: "${CSI_CONTAINER_NAME:?Use the CSI plugin container name}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" logs "deployment/$CSI_CONTROLLER_NAME" \
  -c "$CSI_CONTAINER_NAME" --since=15m --tail=100
```
```bash
# Inspect only the role actually used by the standard EBS CSI controller.
: "${CSI_ROLE_NAME:?Set the reviewed role name}"
aws iam get-role --role-name "$CSI_ROLE_NAME" --query Role.AssumeRolePolicyDocument
aws iam list-attached-role-policies --role-name "$CSI_ROLE_NAME"
aws iam list-role-policies --role-name "$CSI_ROLE_NAME"
```
현재 EKS guide는 표준 driver 권한으로 AmazonEBSCSIDriverPolicyV2 검토를 권장합니다. Driver ownership tag로 volume·snapshot 관리 범위를 제한하고 CSI-migrated volume tag도 지원합니다. 이전 policy를 교체하기 전에 migration·기존 자원 tag를 확인합니다. 모든 변경 action을 Resource:*로 허용한 policy를 범용 해결책으로 붙이지 않습니다. 일부 AWS 조회 action의 wildcard 요구와 광범위한 변경 권한은 다릅니다.

실제 Pod Identity·IRSA role/trust를 확인하고 node identity로 추정하지 않습니다. 고객 KMS key에는 key policy·grant·encrypt/decrypt 권한이 필요하며 문서의 CreateGrant 조건은 kms:GrantIsForAWSResource를 포함합니다. Volume 생성 권한만으로 선택 KMS key 사용·대상 node attach를 증명하지 못합니다. 위 진단 명령은 IAM을 변경하지 않습니다.

### EFS Mount Target·Access Point

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${FILE_SYSTEM_ID:?Use the owned EFS filesystem}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-mount-targets --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
: "${MOUNT_TARGET_ID:?Use the relevant mount target}"
aws efs describe-mount-target-security-groups --region "$AWS_REGION" --mount-target-id "$MOUNT_TARGET_ID"
: "${EFS_SECURITY_GROUP_ID:?Use an observed mount-target security group}"
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$EFS_SECURITY_GROUP_ID"
```
Filesystem 유형·region·접근 가능한 mount target·DNS·TCP 2049·양방향 network를 확인합니다. Regional EFS와 One Zone은 장애 영역 동작이 다릅니다. IAM authorization·access-point POSIX identity/directory 권한·Pod security context도 별도 계층입니다. 아래는 placeholder ID를 사용하는 기존 filesystem 설정 예시이며 filesystem·role·network 전체 생성 절차가 아닙니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  gidRangeStart: '1000'
  gidRangeEnd: '2000'
  basePath: /diagnostics-example
mountOptions:
- tls
reclaimPolicy: Retain
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: diagnostics-example
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: reviewed-efs
  resources:
    requests:
      storage: 5Gi
```
5Gi PVC 요청은 EFS가 강제하는 용량 quota가 아닙니다. Access point는 server-side POSIX identity를 강제할 수 있으므로 client Pod UID만으로 접근을 판단하거나 일괄 chmod로 해결하지 않습니다. TLS mount 암호화와 filesystem at-rest 암호화는 별도입니다. Retain이면 access-point·data 정리 계획과 잔여 비용을 고려합니다. Fargate EFS는 별도 static provisioning 경로이며 모든 node 유형에 이 dynamic 예제가 적용되지는 않습니다.

### PVC/PV 상태·삭제 보호

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?Set the owned claim name}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{
  name:.metadata.name,namespace:.metadata.namespace,uid:.metadata.uid,
  deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
  phase:.status.phase,conditions:.status.conditions,volumeName:.spec.volumeName,
  hasStorageClassName:(.spec | has("storageClassName")),
  storageClassName:.spec.storageClassName,accessModes:.spec.accessModes,resources:.spec.resources
}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json | jq --arg claim "$PVC_NAME" '[
  .items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName? == $claim)) |
  {name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
   node:.spec.nodeName,phase:.status.phase,deleting:.metadata.deletionTimestamp}
]'
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -z "$PV_NAME" ]; then
  echo "No bound PV: inspect StorageClass, consumer scheduling and provisioning events."
else
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o json | jq '{
    name:.metadata.name,uid:.metadata.uid,claimRef:.spec.claimRef,
    deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
    reclaimPolicy:.spec.persistentVolumeReclaimPolicy,csi:.spec.csi,nodeAffinity:.spec.nodeAffinity
  }'
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json | jq --arg pv "$PV_NAME" '[
    .items[] | select(.spec.source.persistentVolumeName == $pv) |
    {name:.metadata.name,driver:.spec.attacher,node:.spec.nodeName,status:.status}
  ]'
fi
```
PVC 이름은 namespace 안에서 고유하므로 consumer도 해당 namespace에서 검색해야 합니다. Claim/PV UID·controller owner·VolumeAttachment·finalizer를 확인합니다. Deletion timestamp에 따른 Terminating 표시는 별도 PVC status.phase가 아닙니다. WaitForFirstConsumer에서는 스케줄 가능한 consumer가 생기기 전 Pending이 정상일 수 있습니다. StorageClassName 생략과 class 없음을 명시한 빈 문자열은 다릅니다.

삭제를 끝내려고 PVC/PV finalizer를 모두 null로 만들지 않습니다. PVC protection·CSI detach/delete·reclaim policy는 다른 생명주기를 보호합니다. 재생성할 수 있는 controller를 포함한 consumer·attachment·controller 오류·backup·data owner를 먼저 확인합니다. 최후의 orphan 복구는 driver별 절차와 검증한 data/attachment 상태가 필요하며 metadata 제거가 안전한 detach·data 복원이 아닙니다. Delete는 backing storage를 지울 수 있고 Retain도 backup은 아닙니다.

### WaitForFirstConsumer·Topology·암호화

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-ebs-wffc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: 'true'
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```
위는 표준 EBS CSI provisioner입니다. WaitForFirstConsumer는 초기 provisioning·binding에 scheduler 제약을 반영하며 EBS를 cross-AZ로 만들거나 장애 AZ의 volume을 복구하지 않습니다. Ap-northeast-2a/2c 같은 zone으로 제한하려면 실제 CSI topology·가용 용량과 workload 배치를 맞춥니다. PV affinity 첫 expression이 항상 zone이거나 Pod가 요청한 affinity가 실제 위치라고 가정하지 않습니다.

```bash
# Use the actual consumer node, not the Pod's requested node-affinity text.
: "${NODE_NAME:?Set an observed consumer node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  name:.metadata.name,providerID:.spec.providerID,
  topologyLabels:(.metadata.labels | with_entries(select(.key | contains("topology"))))
}'
kubectl --context "$KUBE_CONTEXT" get csinode "$NODE_NAME" -o json | jq '.spec.drivers'
# For an actual EBS-backed PV, inspect the volume handle and Region before this lookup.
: "${AWS_REGION:?}"; : "${EBS_VOLUME_ID:?Set the inspected EBS volume ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[].{ID:VolumeId,AZ:AvailabilityZone,State:State,Encrypted:Encrypted,KMS:KmsKeyId,Attachments:Attachments}'
```
Auto Mode는 별도 provisioner·node 호환 요구를 사용합니다. **encrypted: "true"를 명시하고 실제 volume·KMS key를 확인합니다.** 현재 Auto Mode StorageClass parameter 표의 encrypted 기본값은 false입니다. Auto Mode node root/data disk 암호화가 모든 workload PVC의 암호화를 증명하지 않습니다. StorageClass 변경이 기존 volume을 소급 변경하지도 않습니다.

WaitForFirstConsumer만으로 기존 EBS를 다른 AZ에 attach할 수 없습니다. Migration·복구는 문서의 snapshot 또는 통제된 static-volume 절차, 정확한 ownership tag·IAM·앱 일관성을 고려한 data 처리가 필요하며 driver명 편집으로 끝나지 않습니다. Snapshot controller·CRD도 별도 전제이고 snapshot 생성이 restore 성공의 증명은 아닙니다. ReadWriteOnce는 한 node 기준이며 보편적으로 “Pod 하나”를 뜻하지 않습니다. Auto Mode SELinux가 추가 cross-Pod 제약을 줄 수 있으므로 data를 보존하고 원하는 접근·일관성 모델을 검토합니다.

[EBS CSI/IAM](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Managed-policy scopes](https://docs.aws.amazon.com/eks/latest/userguide/security-iam-awsmanpol.html) · [Auto Mode parameters](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [PV lifecycle](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

---

## 7. 관측성 아키텍처

### Container Insights 설정

```bash
# CloudWatch Agent 및 Fluent Bit 설치
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v1.0.0-eksbuild.1

# 또는 Helm으로 설치
helm repo add aws-observability https://aws-observability.github.io/helm-charts
helm install amazon-cloudwatch-observability \
  aws-observability/amazon-cloudwatch-observability \
  --namespace amazon-cloudwatch --create-namespace \
  --set clusterName=my-cluster \
  --set region=ap-northeast-2
```

### PromQL 쿼리 예시

#### CPU 스로틀링 감지

```promql
# CPU 스로틀링 비율
sum(rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m])) by (pod, namespace)
/
sum(rate(container_cpu_cfs_periods_total{container!=""}[5m])) by (pod, namespace)
> 0.5

# CPU 스로틀링이 높은 파드 Top 10
topk(10,
  sum(rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m])) by (pod, namespace)
  /
  sum(rate(container_cpu_cfs_periods_total{container!=""}[5m])) by (pod, namespace)
)
```

#### OOMKilled 이벤트 감지

```promql
# OOMKilled 발생 파드
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1

# 최근 1시간 OOMKilled 횟수
sum(changes(kube_pod_container_status_restarts_total[1h])) by (pod, namespace)
* on (pod, namespace) group_left
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}

# 메모리 사용률이 높은 파드 (OOM 위험)
(
  sum(container_memory_working_set_bytes{container!=""}) by (pod, namespace)
  /
  sum(kube_pod_container_resource_limits{resource="memory"}) by (pod, namespace)
) > 0.9
```

#### 파드 재시작률

```promql
# 최근 1시간 재시작 횟수
sum(increase(kube_pod_container_status_restarts_total[1h])) by (pod, namespace) > 3

# 재시작이 많은 파드 Top 10
topk(10, sum(increase(kube_pod_container_status_restarts_total[1h])) by (pod, namespace))

# CrashLoopBackOff 상태 파드
kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} == 1
```

### CloudWatch Logs Insights 검색 패턴

```sql
-- 에러 로그 검색
fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name
| filter @message like /error|Error|ERROR|exception|Exception|EXCEPTION/
| sort @timestamp desc
| limit 100

-- 특정 파드의 로그
fields @timestamp, @message
| filter kubernetes.pod_name = "my-pod-name"
| sort @timestamp desc
| limit 500

-- 응답 시간 분석 (애플리케이션 로그에 응답 시간 포함 시)
fields @timestamp, @message
| parse @message /response_time=(?<response_time>\d+)ms/
| stats avg(response_time) as avg_response, max(response_time) as max_response by bin(5m)

-- OOMKilled 이벤트 추적
fields @timestamp, @message
| filter @message like /OOMKilled|Out of memory|oom-kill/
| sort @timestamp desc
| limit 50
```

### PrometheusRule 예시

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-alerts
  namespace: monitoring
spec:
  groups:
  - name: eks-node-alerts
    rules:
    - alert: NodeNotReady
      expr: kube_node_status_condition{condition="Ready",status="true"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "노드 {{ $labels.node }}가 NotReady 상태입니다"
        description: "노드가 5분 이상 NotReady 상태입니다. 즉시 확인이 필요합니다."

    - alert: NodeMemoryPressure
      expr: kube_node_status_condition{condition="MemoryPressure",status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "노드 {{ $labels.node }}에 메모리 압력이 발생했습니다"

    - alert: NodeDiskPressure
      expr: kube_node_status_condition{condition="DiskPressure",status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "노드 {{ $labels.node }}에 디스크 압력이 발생했습니다"

  - name: eks-pod-alerts
    rules:
    - alert: PodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[15m]) * 60 * 15 > 3
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "파드 {{ $labels.namespace }}/{{ $labels.pod }}가 반복적으로 재시작됩니다"

    - alert: PodNotReady
      expr: |
        sum by (namespace, pod) (
          max by(namespace, pod) (kube_pod_status_phase{phase=~"Pending|Unknown"}) *
          on(namespace, pod) group_left(owner_kind)
          topk by(namespace, pod) (1, max by(namespace, pod, owner_kind) (kube_pod_owner{owner_kind!="Job"}))
        ) > 0
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "파드 {{ $labels.namespace }}/{{ $labels.pod }}가 15분 이상 Ready 상태가 아닙니다"

    - alert: ContainerOOMKilled
      expr: kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
      for: 0m
      labels:
        severity: warning
      annotations:
        summary: "컨테이너 {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container }}가 OOMKilled되었습니다"

  - name: eks-resource-alerts
    rules:
    - alert: HighCPUThrottling
      expr: |
        sum(rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m])) by (pod, namespace)
        /
        sum(rate(container_cpu_cfs_periods_total{container!=""}[5m])) by (pod, namespace)
        > 0.5
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "파드 {{ $labels.namespace }}/{{ $labels.pod }}의 CPU 스로틀링이 50%를 초과합니다"
```

### ADOT (AWS Distro for OpenTelemetry) 설정

```yaml
# ADOT Collector 설정
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: adot-collector
  namespace: opentelemetry
spec:
  mode: deployment
  serviceAccount: adot-collector
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
      prometheus:
        config:
          scrape_configs:
            - job_name: 'kubernetes-pods'
              kubernetes_sd_configs:
                - role: pod
              relabel_configs:
                - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
                  action: keep
                  regex: true

    processors:
      batch:
        timeout: 30s
        send_batch_size: 8192
      memory_limiter:
        limit_mib: 500
        spike_limit_mib: 100
        check_interval: 5s

    exporters:
      awsxray:
        region: ap-northeast-2
      awsemf:
        region: ap-northeast-2
        namespace: ContainerInsights
        log_group_name: '/aws/containerinsights/{ClusterName}/performance'
      prometheusremotewrite:
        endpoint: "https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/ws-xxxxx/api/v1/remote_write"
        auth:
          authenticator: sigv4auth
        resource_to_telemetry_conversion:
          enabled: true

    extensions:
      sigv4auth:
        region: ap-northeast-2
        service: "aps"

    service:
      extensions: [sigv4auth]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch, memory_limiter]
          exporters: [awsxray]
        metrics:
          receivers: [otlp, prometheus]
          processors: [batch, memory_limiter]
          exporters: [awsemf, prometheusremotewrite]
```

---

## 8. 장애 감지 아키텍처

### 4계층 감지 파이프라인

![메트릭·로그·트레이스·이벤트 등 데이터 소스가 수집 계층(CloudWatch Agent, Fluent Bit, ADOT Collector, Prometheus)을 거쳐 분석 계층(CloudWatch Logs Insights, 메트릭 알림, Anomaly Detection, Composite Alarms)에서 이상을 판정하고 SNS·Slack·PagerDuty·EventBridge로 알림이 전달되는 4단계 장애 감지 파이프라인.](../.gitbook/assets/ko-eks-11-eks-advanced-debugging-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-11-eks-advanced-debugging-3.html)

### 레퍼런스 아키텍처 1: AWS 네이티브

```yaml
# Fluent Bit ConfigMap for CloudWatch
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: amazon-cloudwatch
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Grace         30
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/fluent-bit/state/flb_kube.db
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       log_processed
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name                cloudwatch_logs
        Match               kube.*
        region              ap-northeast-2
        log_group_name      /aws/eks/my-cluster/containers
        log_stream_prefix   fluentbit-
        auto_create_group   true
```

### 레퍼런스 아키텍처 2: 오픈소스 스택

```yaml
# Prometheus + Alertmanager + Grafana
---
# Alertmanager 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'

    route:
      group_by: ['alertname', 'namespace', 'severity']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'default-receiver'
      routes:
        - match:
            severity: critical
          receiver: 'pagerduty-critical'
          continue: true
        - match:
            severity: warning
          receiver: 'slack-warnings'

    receivers:
      - name: 'default-receiver'
        slack_configs:
          - channel: '#alerts-default'
            send_resolved: true

      - name: 'pagerduty-critical'
        pagerduty_configs:
          - service_key: '<pagerduty-service-key>'
            severity: critical

      - name: 'slack-warnings'
        slack_configs:
          - channel: '#alerts-warnings'
            send_resolved: true
            title: '{{ .Status | toUpper }}: {{ .CommonAnnotations.summary }}'
            text: '{{ .CommonAnnotations.description }}'

    inhibit_rules:
      - source_match:
          severity: 'critical'
        target_match:
          severity: 'warning'
        equal: ['alertname', 'namespace']
```

### 감지 패턴

#### 임계값 기반 감지

```yaml
# CloudWatch Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-High-CPU-Usage" \
  --alarm-description "EKS 노드 CPU 사용률이 80%를 초과" \
  --metric-name node_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-alerts
```

#### 이상 감지 (Anomaly Detection)

```yaml
# CloudWatch Anomaly Detection Alarm
aws cloudwatch put-anomaly-detector \
  --namespace ContainerInsights \
  --metric-name pod_cpu_utilization \
  --stat Average \
  --dimensions Name=ClusterName,Value=my-cluster

aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Anomaly-CPU" \
  --alarm-description "비정상적인 CPU 사용 패턴 감지" \
  --metrics '[
    {
      "Id": "m1",
      "MetricStat": {
        "Metric": {
          "Namespace": "ContainerInsights",
          "MetricName": "pod_cpu_utilization",
          "Dimensions": [{"Name": "ClusterName", "Value": "my-cluster"}]
        },
        "Period": 300,
        "Stat": "Average"
      }
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)"
    }
  ]' \
  --threshold-metric-id ad1 \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-anomaly-alerts
```

#### Composite Alarm

```bash
# 복합 알람 생성
aws cloudwatch put-composite-alarm \
  --alarm-name "EKS-Critical-State" \
  --alarm-description "클러스터 크리티컬 상태" \
  --alarm-rule "ALARM(EKS-High-CPU-Usage) AND ALARM(EKS-High-Memory-Usage)" \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-critical-alerts \
  --ok-actions arn:aws:sns:ap-northeast-2:123456789012:eks-resolved
```

#### 로그 기반 메트릭

```bash
# 로그에서 메트릭 추출
aws logs put-metric-filter \
  --log-group-name "/aws/eks/my-cluster/containers" \
  --filter-name "ErrorCount" \
  --filter-pattern "[..., level=\"ERROR\", ...]" \
  --metric-transformations \
    metricName=ApplicationErrors,metricNamespace=EKS/Application,metricValue=1
```

### 성숙도 모델 (Maturity Model)

| 레벨 | 설명 | MTTD 목표 | 주요 기능 |
|------|------|-----------|-----------|
| **Level 1** | 기본 | 30분 | 기본 메트릭 알림, 수동 로그 검색 |
| **Level 2** | 반응형 | 15분 | 임계값 알림, 로그 기반 알림, 기본 대시보드 |
| **Level 3** | 선제적 | 5분 | 이상 감지, 복합 알람, 자동화된 런북 |
| **Level 4** | 예측적 | 2분 | ML 기반 예측, 자동 복구, 카오스 엔지니어링 |

### EventBridge + Lambda 자동 복구

```yaml
# EventBridge Rule
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "alarmName": ["EKS-Pod-CrashLooping"],
    "state": {
      "value": ["ALARM"]
    }
  }
}
```

```python
# Lambda 자동 복구 함수
import boto3
import json
from kubernetes import client, config

def lambda_handler(event, context):
    alarm_name = event['detail']['alarmName']

    # EKS 클러스터 자격 증명 가져오기
    eks = boto3.client('eks')
    cluster_info = eks.describe_cluster(name='my-cluster')

    # Kubernetes 클라이언트 설정
    # ... (kubeconfig 설정)

    # CrashLooping 파드 재시작
    if 'CrashLooping' in alarm_name:
        v1 = client.CoreV1Api()
        # 문제 파드 삭제 (Deployment가 재생성)
        v1.delete_namespaced_pod(
            name=extract_pod_name(event),
            namespace=extract_namespace(event),
            body=client.V1DeleteOptions()
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Auto-remediation executed')
    }
```

### 심각도별 알림 채널 매트릭스

| 심각도 | Slack | PagerDuty | Email | SMS | Auto-Remediation |
|--------|-------|-----------|-------|-----|------------------|
| **P1 Critical** | #incidents | Immediate | Team Lead | On-call | Yes |
| **P2 High** | #alerts-high | 15min delay | Team | - | Conditional |
| **P3 Medium** | #alerts | - | Team | - | No |
| **P4 Low** | #alerts-low | - | Daily digest | - | No |

---

## 9. 빠른 참조

### 오류 패턴 조회 테이블

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| **CrashLoopBackOff** | 애플리케이션 크래시, 잘못된 명령, 누락된 의존성 | `kubectl logs --previous`, 애플리케이션 코드/설정 검토 |
| **ImagePullBackOff** | 이미지 없음, 잘못된 태그, 인증 실패 | 이미지 이름 확인, `imagePullSecrets` 검토 |
| **OOMKilled** | 메모리 제한 초과 | 메모리 limit 증가, 메모리 누수 수정 |
| **CreateContainerConfigError** | ConfigMap/Secret 누락, 잘못된 참조 | `kubectl describe pod`, 참조된 리소스 존재 확인 |
| **Pending (리소스)** | CPU/메모리 요청을 충족하는 노드 없음 | 노드 스케일 업, 리소스 요청 조정 |
| **Pending (스케줄링)** | nodeSelector, affinity, taint 불일치 | `kubectl describe pod`의 Events 섹션 확인 |
| **ContainerCreating (지연)** | 볼륨 마운트 실패, 네트워크 플러그인 문제 | PVC 상태, CNI 파드 상태 확인 |
| **ErrImagePull** | 이미지 레지스트리 연결 실패 | 네트워크 연결, ECR 엔드포인트 확인 |
| **RunContainerError** | 잘못된 컨테이너 설정, securityContext 문제 | `kubectl describe pod`, securityContext 검토 |
| **PostStartHookError** | postStart 훅 실패 | 훅 명령어 검토, 타임아웃 조정 |
| **PreStopHookError** | preStop 훅 실패 | 훅 명령어 검토, terminationGracePeriodSeconds 조정 |
| **FailedScheduling** | 리소스 부족, PVC 바인딩 대기 | 노드 리소스, PVC 상태 확인 |
| **FailedMount** | 볼륨 마운트 실패, CSI 드라이버 문제 | CSI 드라이버 로그, PV/PVC 상태 확인 |
| **NetworkNotReady** | CNI 플러그인 미준비 | aws-node 파드 상태, CNI 로그 확인 |
| **NodeNotReady** | kubelet 문제, 네트워크 단절 | kubelet 로그, 노드 상태 확인 |
| **Evicted** | 노드 리소스 압력 (디스크, 메모리) | 노드 리소스 정리, 리소스 limit 조정 |
| **BackOff** | 재시도 백오프 상태 | 이전 에러 로그 확인, 근본 원인 해결 |
| **InvalidImageName** | 잘못된 이미지 이름 형식 | 이미지 이름 문법 확인 |

### 필수 kubectl 명령어 치트시트

```bash
# 클러스터 상태
kubectl cluster-info
kubectl get nodes -o wide
kubectl top nodes

# 파드 디버깅
kubectl get pods -A -o wide
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns> --tail=100 -f
kubectl logs <pod> -n <ns> --previous
kubectl exec -it <pod> -n <ns> -- /bin/sh

# 이벤트
kubectl get events -A --sort-by='.lastTimestamp'
kubectl get events -n <ns> --field-selector type=Warning

# 리소스 사용량
kubectl top pods -A --sort-by=memory
kubectl top pods -A --sort-by=cpu

# 디버그 컨테이너
kubectl debug -it <pod> --image=busybox --target=<container>
kubectl debug node/<node> -it --image=ubuntu

# 네트워크 테스트
kubectl run test --image=nicolaka/netshoot -it --rm -- /bin/bash

# 강제 삭제
kubectl delete pod <pod> -n <ns> --grace-period=0 --force

# 롤아웃
kubectl rollout status deployment/<deploy> -n <ns>
kubectl rollout undo deployment/<deploy> -n <ns>
kubectl rollout restart deployment/<deploy> -n <ns>

# 스케일링
kubectl scale deployment <deploy> -n <ns> --replicas=3

# ConfigMap/Secret
kubectl get configmap -n <ns> -o yaml
kubectl get secret -n <ns> -o yaml

# 서비스 엔드포인트
kubectl get endpoints -n <ns>
kubectl describe svc <service> -n <ns>
```

### 도구 추천

| 도구 | 용도 | 설치/사용 |
|------|------|-----------|
| **netshoot** | 네트워크 디버깅 | `kubectl run net --image=nicolaka/netshoot -it --rm` |
| **eks-node-viewer** | 노드 리소스 시각화 | `go install github.com/awslabs/eks-node-viewer/cmd/eks-node-viewer@latest` |
| **crictl** | 컨테이너 런타임 디버깅 | 노드에서 `sudo crictl ps`, `sudo crictl logs` |
| **kubeval** | YAML 검증 | `kubeval deployment.yaml` |
| **stern** | 멀티 파드 로그 | `stern <pod-pattern> -n <namespace>` |
| **k9s** | TUI 클러스터 관리 | `k9s -n <namespace>` |
| **kubectx/kubens** | 컨텍스트/네임스페이스 전환 | `kubectx <context>`, `kubens <namespace>` |

### EKS Log Collector (AWS Support용)

```bash
# EKS Log Collector 다운로드 및 실행
curl -O https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/log-collector-script/linux/eks-log-collector.sh
chmod +x eks-log-collector.sh

# 로그 수집 실행
sudo ./eks-log-collector.sh

# 수집된 로그는 /var/log/eks_i-xxxx_$(date +%Y-%m-%d_%H-%M-%S).tar.gz에 저장
# AWS Support 케이스에 첨부하여 제출
```

수집되는 정보:
- 시스템 정보 (OS, 커널, 메모리, CPU)
- kubelet 로그 및 설정
- containerd 로그 및 설정
- CNI 플러그인 로그
- 네트워크 설정 (iptables, 라우팅)
- 디스크 사용량

---

## 10. 다음 단계

### 퀴즈

이 문서에서 다룬 내용을 테스트하려면 [EKS 고급 디버깅 퀴즈](../quizzes/eks/11-eks-advanced-debugging-quiz.md)를 풀어보세요.

### 다음 문서

EKS 클러스터를 온프레미스 환경과 통합하는 방법을 알아보려면 [EKS Hybrid Nodes](../eks-hybrid-nodes/README.md)를 참조하세요.

### 추가 학습 자료

- [AWS EKS 공식 문서 - 문제 해결](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)
- [Kubernetes 공식 문서 - 디버깅](https://kubernetes.io/docs/tasks/debug/)
- [AWS Well-Architected Framework - EKS 렌즈](https://docs.aws.amazon.com/wellarchitected/latest/eks-lens/welcome.html)
