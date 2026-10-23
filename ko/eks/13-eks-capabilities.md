# Amazon EKS Capabilities: 관리형 Argo CD, kro, ACK

> **지원 버전**: EKS 1.36~1.37, Argo CD `3.4.6-eks-2`·`3.4.7-eks-1`, kro `0.9.4-eks-1`, ACK `46.186.1-eks-1`, AWS CLI 2.38.3
> **마지막 업데이트**: 2026년 10월 23일

EKS Capabilities는 Argo CD, kro(Kube Resource Orchestrator), ACK(AWS Controllers for Kubernetes) 컨트롤러를 AWS가 클러스터 밖에서 운영하는 기능입니다. 2025년 11월 30일에 정식 출시됐고, 2026년 6월에 컨트롤러 로그 전달(Vended Logs), 8월에 Argo CD의 `argocd-cm` 사용자 지정 구성이 추가됐습니다.

이 문서의 수치는 2026년 10월 ap-northeast-2의 시험 클러스터에서 잰 값입니다. 주 클러스터는 private 서브넷, authenticationMode `API`, m7g.large 노드 2대로 구성했고(업그레이드·멀티 클러스터용 hub와 spoke는 노드 1대씩), 같은 클러스터에 self-managed(OSS) 컨트롤러를 설치해 같은 시나리오를 반복했습니다. 시나리오마다 1~5회만 반복했으므로 수치는 범위로 읽고, 운영 판단 전에 자기 환경에서 다시 확인하세요. 실측하지 않고 문서로만 확인한 내용은 "문서 기준"으로 표시했습니다. 측정 과정과 원시 결과는 [EKS Capabilities 3부작 블로그](https://blog.atomai.click/eks-capabilities-argocd/)에 있습니다.

## 목차

1. [공통 구조](#common)
2. [생성과 공통 운영](#create)
3. [Argo CD capability](#argocd)
4. [kro capability](#kro)
5. [ACK capability](#ack)
6. [세 capability를 함께 쓸 때](#together)
7. [클러스터 업그레이드와 capability 버전](#upgrade)
8. [멀티 클러스터와 blue/green 교체](#multicluster)
9. [self-managed와 비교, 선택 기준](#compare)
10. [요금](#pricing)
11. [검증 범위와 참고 자료](#refs)

---

<span id="common"></span>

## 1. 공통 구조

| 항목 | 내용 |
|---|---|
| 컨트롤러 위치 | AWS 소유 인프라. 워커 노드에 Pod를 만들지 않음(세 capability 모두 실측 0개) |
| 클러스터 접근 | capability role(신뢰 주체 `capabilities.eks.amazonaws.com`)이 EKS 액세스 항목(access entry)으로 API 서버를 호출. API 엔드포인트가 private 전용이어도 동작 |
| 개수 | 클러스터마다 종류별 하나 |
| 버전 | AWS가 정하고 올림. 생성·변경 API에 버전 인자가 없어 고정하거나 고를 수 없음 |
| 삭제 | `--delete-propagation-policy RETAIN`만 지원. CRD, CR, 배포된 리소스, access entry가 남음 |
| 로그 | `kubectl logs`로 볼 수 없음. CloudWatch Vended Logs로 CloudWatch Logs, S3, Amazon Data Firehose에 전달([EKS 모니터링 및 로깅](./06-eks-monitoring-logging.md) 참고) |
| 요금 | capability 시간당 요금 + 관리 대상 수(Argo CD는 Application, kro는 인스턴스, ACK는 리소스)에 비례한 요금 |

세 capability에서 공통으로 확인한 특징은 기본 권한이 좁다는 점입니다. 자동으로 만들어지는 access entry 정책만으로는 Argo CD가 배포하지 못하고, kro는 RGD 컨트롤러를 시작하지 못하며, ACK는 서비스별 IAM 권한이 없으면 AWS 리소스를 만들지 못합니다. 반대로 OSS Helm 차트의 기본값은 Argo CD와 kro 모두 컨트롤러에 `apiGroups: ["*"], resources: ["*"], verbs: ["*"]`를 줍니다.

<span id="create"></span>

## 2. 생성과 공통 운영

### capability role과 생성 명령

capability role의 신뢰 정책에는 `capabilities.eks.amazonaws.com`을 주체로 두고 `sts:AssumeRole`, `sts:TagSession`을 허용합니다. kro는 AWS API를 부르지 않으므로 권한 정책이 필요 없습니다. 공개 Git 저장소만 쓰는 Argo CD도 권한 정책 없이 동작했습니다.

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| capability | `CREATING` → `ACTIVE` | 삭제 | 자동 생성 access entry 정책 | 설치되는 CRD |
|---|---|---|---|---|
| Argo CD | 349초(다른 클러스터에 `endpointPrefix`를 지정해 생성 385초, 같은 prefix로 재생성 338초) | 100.5초 | `AmazonEKSArgoCDClusterPolicy`(클러스터 범위), `AmazonEKSArgoCDPolicy`(`argocd` 네임스페이스) | `applications`, `applicationsets`, `appprojects` |
| kro | 70.1~70.4초 | 46.9초 | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`, `graphrevisions.internal.kro.run` |
| ACK | 385.7초(CRD가 남아 있으면 77초) | 67.3초 | `AmazonEKSACKPolicy` | 267개(서비스 API 그룹 66개 + `services.k8s.aws`의 `IAMRoleSelector`) |

### 운영 시 주의할 점

- **AWS CLI를 최신으로 유지합니다.** CLI 2.35.11은 `argoCd` 아래 `namespace`, `awsIdc`, `rbacRoleMappings`, `networkAccess`만 알았고 `endpointPrefix`가 없었으며, ACK 설정은 `Unknown parameter in configuration: "ack", must be one of: argoCd`로 거부했습니다. 2.38.3에서는 두 설정 모두 동작했습니다. "지원하지 않는다"고 결론 내리기 전에 CLI 버전부터 확인합니다.
- **capability 설정 변경은 하나씩 적용합니다.** 로그 delivery source를 하나 추가할 때마다 capability가 약 6.6~7초 동안 `UPDATING`이 되고, 그동안 다음 변경은 `ConflictException: ... currently in UPDATING state`로 거부됩니다. 변경 후 `ACTIVE`를 기다린 다음 진행합니다.
- **로그 전달은 처음부터 켭니다.** 컨트롤러가 클러스터 밖에 있어 컨트롤러 내부 동작을 나중에 볼 수 있는 곳은 로그뿐입니다(AWS API 호출 시각은 CloudTrail로도 볼 수 있음). 로그는 구조화된 JSON이며 Argo CD는 동기화 한 번의 단계별 소요 시간(`compare_app_state_ms`, `patch_ms` 등)까지 남깁니다.
- **RETAIN은 "컨트롤러만 없어진 상태"를 남깁니다.** capability를 지운 동안에는 CR을 바꿔도 반영되지 않습니다(kro 인스턴스의 replicas 변경으로 확인). 같은 CRD를 쓰는 OSS 컨트롤러를 설치하면 밀린 변경을 이어서 처리합니다.

<span id="argocd"></span>

## 3. Argo CD capability

### 로컬 클러스터 등록과 배포 권한

관리형 Argo CD는 자기가 붙은 클러스터도 자동으로 배포 대상에 넣지 않습니다. API 주소가 아니라 EKS ARN으로 cluster Secret을 만듭니다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: in-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
stringData:
  name: in-cluster
  server: arn:aws:eks:ap-northeast-2:111122223333:cluster/example-cluster
  project: default
```

자동 access entry만으로는 동기화가 시작되지 않습니다. Argo CD는 배포할 리소스뿐 아니라 클러스터의 모든 리소스 타입을 캐시하려고 목록을 조회하기 때문입니다.

| capability role의 클러스터 권한 | 결과 |
|---|---|
| 자동 access entry만 | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| + `AmazonEKSEditPolicy` | 141초 뒤에도 실패. `securitygrouppolicies.vpcresources.k8s.aws` 목록 조회 거부 |
| + `AmazonEKSAdminViewPolicy` | 11.6초 만에 Synced, Healthy |
| kro·ACK API의 CR(NginxApp 인스턴스, ACK Queue) 배포 | `nginxapps.platform.example.com is forbidden`. access entry에 Kubernetes 그룹을 붙이고 해당 API 그룹용 ClusterRole을 바인딩하자 16초 만에 Synced |

AWS 문서는 시작용으로 `AmazonEKSClusterAdminPolicy`(`system:masters` 상당)를 쓰고, 운영용 최소 권한 구성으로 클러스터 범위 읽기 권한과 네임스페이스 범위 `AmazonEKSEditPolicy`를 제시합니다. 실측에서는 클러스터 범위 Edit + AdminView에 플랫폼 CRD별 ClusterRole을 더한 조합으로 동작했으며, 이는 문서의 운영용 구성보다 넓습니다. 더 좁히려면 관리형이 지원하는 `resource.respectRBAC`로 권한이 있는 리소스만 감시하게 할 수 있습니다(시험하지 않음).

### Git 폴링과 webhook

| 방식 | commit → Synced(3회) |
|---|---|
| 관리형, 기본 폴링(문서상 6분) | 341.8초, 619.3초, 697.1초 |
| 관리형, GitHub webhook | 7.0~7.3초 |
| self-managed 3.4.6, 기본 폴링(120초 + jitter 60초) | 115.7~171.4초 |

관리형의 폴링 주기(`timeout.reconciliation`)는 바꿀 수 있는 키가 아니고 jitter도 공개되어 있지 않습니다. 배포 지연이 분 단위로 흔들리면 안 된다면 webhook이 사실상 필수입니다. capability가 만든 `argocd-webhook-creds-secret`의 `webhook.github.secret`에 무작위 문자열을 넣고, Git 저장소에 `<서버 URL>/api/webhook`을 같은 secret으로 등록합니다. 서버 URL이 AWS 호스팅 공개 주소이므로 webhook용 엔드포인트를 따로 노출할 필요가 없습니다. VPC 엔드포인트로 공개 접근을 막으면 GitHub webhook도 닿지 않을 것으로 보입니다(시험하지 않음).

drift self-heal은 관리형 2.08~2.32초, self-managed 1.05~3.06초로 같았습니다. 다만 같은 앱에서 새 commit 없이 self-heal이 반복되면 upstream 백오프(2초에서 3배씩, 최대 300초)로 복구가 최대 약 5분까지 늦어집니다(실측 251~254초). self-managed는 `--self-heal-backoff-*` 플래그로 조정하지만, 관리형에서 바꿀 수 있는 `argocd-cmd-params-cm` 키는 `hydrator.enabled`, `application.namespaces`, `applicationsetcontroller.namespaces` 3개뿐이고 AWS 문서는 self-heal 타이밍 조정을 AWS Support에 요청하라고 안내합니다. 급하면 수동 sync를 겁니다.

### 설정, health check, CLI

`argocd-cm` ConfigMap을 capability 네임스페이스에 만들고 `app.kubernetes.io/part-of: argocd` 레이블을 붙입니다. 지원하지 않는 키는 오류 없이 무시됩니다.

| 항목 | 결과 |
|---|---|
| `ui.bannercontent` | UI에 표시 |
| kro 인스턴스용 Lua health check | 적용, 스크립트 변경은 약 12초 뒤 반영 |
| Lua `string.upper()`, `os.time()` | `attempt to index a non-table object(nil)`, health `Unknown`. upstream 기본값(`useOpenLibs` 꺼짐)과 같지만 관리형은 켤 수 없음 |
| `argocd login --username admin`, `--sso` | 모두 실패 |
| UI에서 만든 토큰 + `ARGOCD_SERVER`, `ARGOCD_AUTH_TOKEN`, `ARGOCD_OPTS=--grpc-web` | `app list/get/sync`, `cluster list`, `proj list` 동작 |
| 150초 sleep하는 PreSync hook | 문서상 sync timeout은 120초지만 161초 만에 `Succeeded`. 제한이 어느 단계에 걸리는지는 미확인 |

Argo CD 3.x는 리소스 health를 기본으로 Application status에 저장하지 않으므로 `kubectl get application -o json`의 `.status.resources[].health`가 비어 있어도 정상입니다. health는 `argocd app get`이나 UI로 확인합니다.

문서상 지원하지 않는 기능은 Config Management Plugin(CMP), Notifications 컨트롤러, 사용자 지정 SSO, UI 확장, `argocd admin` 명령 등입니다. Notifications로 배포 알림을 보내거나 CMP로 사내 템플릿 도구를 붙였다면 관리형으로 그대로 옮길 수 없습니다.

### 로그인: Identity Center만 지원

인증은 IAM Identity Center 하나뿐이며 로컬 사용자가 없습니다. 권한은 capability 설정의 `rbacRoleMappings`로 Identity Center 사용자(`SSO_USER`)나 그룹(`SSO_GROUP`)을 ADMIN, EDITOR, VIEWER에 매핑합니다. Okta나 Microsoft Entra ID는 Argo CD에 직접 붙지 않고, Identity Center의 ID 소스를 외부 IdP로 두어 SAML(로그인)과 SCIM(사용자·그룹 동기화)으로 연결합니다(문서 기준).

- Identity Center 인스턴스에는 ID 소스가 하나뿐입니다. 조직 인스턴스가 이미 다른 IdP에 연결되어 있다면 Argo CD만 다른 IdP를 쓰는 데 계정 인스턴스가 필요합니다(시험하지 않음).
- 생성 후에는 연결한 Identity Center 인스턴스를 바꿀 수 없습니다(EKS 콘솔 도움말 기준). 매핑은 사용자·그룹 ID로 저장되며, ID 소스를 Active Directory로 바꾸면 사용자와 그룹이 지워져 매핑을 다시 써야 합니다.
- 매핑할 수 있는 ID는 capability당 1,000개이므로 그룹 단위로 매핑합니다. 전역 역할은 세 가지뿐이라 `argocd-rbac-cm`의 세밀한 정책은 AppProject 역할로 옮겨야 합니다.

<span id="kro"></span>

## 4. kro capability

AWS 문서는 관리형 kro가 같은 upstream 컨트롤러를 쓰고 완전히 호환된다고 설명합니다. 실측에서도 보고된 버전 `0.9.4-eks-1`이 OSS 최신 릴리스와 같았고, 같은 RGD와 CEL 식이 그대로 동작했습니다. 차이는 권한과 운영에서 나옵니다. kro 자체의 개념과 예제는 [kro 문서](../platform-engineering/03-kro.md)를 참고하세요.

### 기본 권한으로는 컨트롤러가 시작하지 않음

`AmazonEKSKROPolicy`는 `kro.run` 그룹과 CRD만 다룹니다. RGD 스키마의 group(예: `platform.example.com`)으로 생긴 API를 watch할 권한도, 하위 Deployment와 Service를 만들 권한도 없습니다. 그런데 오류는 forbidden이 아니라 cache sync timeout으로 나타납니다.

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

eksctl 가이드는 시작용으로 `AmazonEKSClusterAdminPolicy`를 붙이지만, access entry에 Kubernetes 그룹을 붙이고 RGD별 ClusterRole을 바인딩하는 방식으로 최소 권한을 줄 수 있습니다.

```bash
aws eks update-access-entry --cluster-name "$CLUSTER_NAME" \
  --principal-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --kubernetes-groups kro-workloads
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kro-workloads-reviewed-nginxapps
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kro:controller:reviewed-nginxapps
subjects:
  - kind: Group
    name: kro-workloads
    apiGroup: rbac.authorization.k8s.io
```

권한을 RGD보다 늦게 주자 228초 뒤에야 `Active`가 됐습니다(컨트롤러의 재시도 간격으로 추정, 로그로 확인하지 않음). ClusterRole을 RGD보다 먼저 적용한 두 번째 RGD는 바로 `Active`가 됐습니다. RGD와 ClusterRole은 같은 Git 경로에 두고 sync wave로 RBAC를 먼저 적용하는 편이 낫습니다(sync wave 적용은 시험하지 않음). OSS의 `rbac.mode: aggregation`도 레이블을 단 ClusterRole만 컨트롤러 권한에 합치므로 비슷한 작업이 필요합니다(차트 설명 기준, 시험하지 않음).

### 수명주기 성능과 이전

| 단계(각 5회) | 관리형 | OSS 0.9.4 |
|---|---|---|
| 생성 → `ACTIVE` | 2.49~3.73초 | 2.43~3.44초 |
| spec 변경 → Deployment 반영 | 0.50~0.52초(1회 51.6초, 원인 미확인) | 0.49~0.56초 |
| 삭제 → Deployment, Service 소멸 | 1.02~3.02초 | 1.01~4.38초 |

관리형에서 OSS로, 다시 관리형으로 바꿔도 RGD 2개와 인스턴스 4개가 그대로 이어졌습니다(한쪽을 지운 뒤 다른 쪽을 설치한 경우). 무중단 이전을 위한 리더 선출 lease 이동은 AWS 문서의 이전 절차를 따르되(시험하지 않음), 문서 예시의 차트 경로와 값 키가 오래됐습니다. 현재 차트는 `oci://registry.k8s.io/kro/charts/kro`이고 0.9.4의 키는 `config.leaderElectionNamespace`입니다.

### 함정: 같은 이름의 기존 CR을 가져감

같은 네임스페이스에 하위 리소스와 이름이 같은 CR이 이미 있으면 kro는 거부하지 않고 server-side apply로 덮어씁니다. 실측에서 기존 ACK Table CR에 `kro.run/owned=true`가 붙고 `spec.tableName`이 바뀌었고, ACK가 새 테이블을 만들면서 원래 테이블은 관리되지 않는 상태로 남았습니다. 인스턴스를 지우자 가져간 CR까지 삭제됐습니다. OSS 0.9.4에서도 똑같이 재현되므로 upstream 동작입니다.

- 하위 리소스 이름에 RGD 고유 접미사를 붙입니다(`${schema.metadata.name + "-os"}`).
- kro가 관리하는 네임스페이스와 사람이 CR을 직접 만드는 네임스페이스를 나눕니다.
- 데이터가 있는 ACK 리소스에는 `services.k8s.aws/deletion-policy: retain`을 겁니다. 다만 이름이 바뀌어 새 리소스로 옮겨 가는 것은 막지 못하므로 근본 대책은 이름 분리입니다(retain과 이 상황의 조합은 시험하지 않음).
- 멀티테넌트 클러스터에서는 인스턴스가 `ingressClassName`과 호스트 이름을 마음대로 정하지 않도록 RGD에서 고정하거나 인스턴스 이름으로 만듭니다.

<span id="ack"></span>

## 5. ACK capability

관리형 ACK는 upstream에서 GA인 서비스 컨트롤러를 모두 한 capability에 담습니다. preview 컨트롤러는 GA가 되면 자동으로 추가됩니다(문서 기준). ACK 자체의 리소스 모델과 adoption, retain은 [ACK 문서](../platform-engineering/02-ack.md)를 참고하세요.

### IAMRoleSelector로 팀별 IAM 분리

capability role에는 팀 역할을 assume하는 권한만 두고, 클러스터 범위 `IAMRoleSelector`로 네임스페이스와 역할을 연결합니다. 팀 역할의 신뢰 정책에는 capability role을 주체로 넣고 `sts:AssumeRole`, `sts:TagSession`을 허용합니다.

```json
{"Effect": "Allow", "Action": ["sts:AssumeRole", "sts:TagSession"],
 "Resource": ["arn:aws:iam::111122223333:role/ack-team-a",
              "arn:aws:iam::111122223333:role/ack-team-b"]}
```

```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: IAMRoleSelector
metadata:
  name: team-b
spec:
  arn: arn:aws:iam::111122223333:role/ack-team-b
  namespaceSelector:
    names: [team-b]
```

SQS 권한만 받은 team-b에서 만든 S3 Bucket은 `AccessDenied`로 막혔고, 거부 메시지에 실제로 쓰인 역할(`assumed-role/ack-team-b/...`)이 나왔습니다. CR 조건 `ACK.IAMRoleSelected=True`로 선택 여부도 확인할 수 있습니다. 확인한 세부 사항은 다음과 같습니다.

- S3 Bucket 컨트롤러는 먼저 `s3:ListAllMyBuckets`를 호출합니다. 버킷 이름 패턴으로 리소스를 좁히더라도 이 권한(리소스 `*`)은 따로 필요해 보입니다(빼고 시험하지는 않음).
- 선택자가 없는 네임스페이스는 capability role을 그대로 씁니다(문서 기준). capability role에 서비스 권한을 주지 않으면 기본이 거부가 됩니다.
- OSS 컨트롤러에서 같은 분리를 하려면 `featureGates.IAMRoleSelector=true`와 `enableCARM=false`를 함께 줘야 합니다. 차트 기본값(`enableCARM: true`)이면 `cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true`로 CrashLoopBackOff에 빠집니다.

### 리소스 생성, 태그, drift

| 리소스 | 관리형(3회) | OSS(2회) |
|---|---|---|
| SQS Queue | 1.04~1.06초 | 1.10~1.16초 |
| S3 Bucket | 3.10~3.14초 | 3.20~3.32초 |
| DynamoDB Table | 11.28~11.53초 | 10.15~11.54초 |

capability를 처음 만든 직후의 첫 생성만 Queue 7.3초, Bucket 10.9초, Table 16.5초로 느렸습니다.

관리형은 AWS 리소스에 `eks:controller-version`, `eks:kubernetes-namespace`, `eks:kubernetes-resource-name`, `eks:kubernetes-api-group`, `eks:eks-capability-arn` 태그 5개를 붙이고, 모든 AWS API 호출에 `eks:eks-capability-arn`, `eks:kubernetes-namespace`, `eks:kubernetes-api-group` 세션 태그를 붙입니다. OSS는 `services.k8s.aws/controller-version`, `services.k8s.aws/namespace` 2개입니다. OSS에서 옮기면 태그 접두사가 바뀌므로 비용 할당 태그와 태그 기반 IAM 조건을 함께 고칩니다.

ACK는 AWS 쪽 변경을 실시간으로 감시하지 않습니다. ACK 밖에서(CLI로) 바꾼 SQS `VisibilityTimeout`은 관리형(2회)과 OSS(1회) 모두 25분 동안 주기적으로 되돌아오지 않았습니다. 관리형에서 되돌아온 두 번은 capability가 로그 설정 추가로 `UPDATING`을 거친 86초 뒤와 capability 재생성 직후였습니다(CloudTrail의 호출 시각 기준). 컨트롤러 재시작이 계기로 보이지만 로그로 확인하지는 않았습니다. OSS의 기본 resync는 10시간(`reconcile.defaultResyncPeriod: 36000`)이고 조정할 수 있지만, 관리형의 주기는 공개되어 있지 않고 조정할 수 없습니다. 빠른 복구가 필요하면 SCP나 IAM 조건으로 ACK 밖의 변경 자체를 막습니다. 예를 들어 `aws:ResourceTag/eks:eks-capability-arn`이 있는 리소스는 같은 값의 `aws:PrincipalTag/eks:eks-capability-arn`을 가진 호출만 바꿀 수 있게 합니다(시험하지 않음).

### 관리형의 차이와 이전

- `FieldExport` CRD가 없습니다. status 값을 ConfigMap이나 Secret으로 내보내려면 kro로 status를 ConfigMap에 넣는 등 다른 방법을 씁니다.
- 서비스를 끄는 `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'`는 CLI 2.38.3에서 12.5초 만에 반영됐지만, 이미 설치된 해당 서비스의 CRD는 350초가 지나도 남았습니다. 쓰지 않을 서비스는 생성 시 지정하는 것이 맞아 보입니다(생성 시 지정은 시험하지 않음).
- 컨트롤러 버전은 OSS 최신보다 한 단계 낮았습니다(s3 1.12.2 대 1.13.1, sqs 1.7.1 대 1.8.2).
- adoption(`services.k8s.aws/adoption-policy: adopt-or-create`)과 retain 주석은 관리형에서도 동작했습니다. adoption은 4.7초 걸렸고, retain으로 지운 Queue는 AWS에 남았습니다(관리형에서 측정). capability를 지운 뒤 설치한 OSS 컨트롤러가 남은 CR 12개를 그대로 이어받았습니다.

<span id="together"></span>

## 6. 세 capability를 함께 쓸 때

Argo CD가 Git의 매니페스트를 동기화하고, kro가 여러 리소스를 하나의 API로 묶고, ACK가 그중 AWS 리소스를 만드는 분담이 자연스럽습니다. 시험한 `OrderService` RGD는 ACK Queue와 Table을 만들고 두 리소스의 status(큐 URL, 테이블 ARN)를 ConfigMap에 넣은 뒤 Deployment를 띄웠습니다.

| 조합 | 결과 | 추가로 필요했던 설정 |
|---|---|---|
| Argo CD → ACK Queue | Git의 Queue CR이 6.5초 만에 Synced | Argo CD capability role에 `queues.sqs.services.k8s.aws` RBAC |
| kro → ACK Queue·Table + ConfigMap + Deployment | 인스턴스 `ACTIVE`까지 13.2~34.3초(대부분 DynamoDB 테이블 생성 시간) | kro capability role에 ACK 리소스 RBAC, ACK 쪽은 IAMRoleSelector |

ACK CRD는 EKS 기본 access policy(`AmazonEKSEditPolicy` 등)에 포함되지 않으므로, ACK 리소스를 만드는 쪽(Argo CD든 kro든)에 해당 API 그룹 권한을 따로 줘야 합니다. 두 측정은 따로 했고 세 단계를 한 번에 잇지는 않았습니다.

<span id="upgrade"></span>

## 7. 클러스터 업그레이드와 capability 버전

### in-place 업그레이드 중 동작

세 capability를 모두 켠 클러스터를 1.36에서 1.37로 in-place 업그레이드했습니다. 컨트롤 플레인 업그레이드는 약 7분 걸렸고, 그동안 세 capability는 계속 `ACTIVE`였으며 버전, health, `modifiedAt`이 그대로였습니다.

| 구간 | Argo CD self-heal | kro 반영 | ACK Queue 동기화 |
|---|---|---|---|
| 업그레이드 전(3회) | 2.1~14.6초 | 1.02~1.04초 | 1.49~3.53초 |
| 업그레이드 중(4회) | 2.1초, 6.1초, 112.9초, 254.5초 | 1.02~1.07초 | 1.52~1.58초 |
| 업그레이드 후(5회) | 2.3초, 이후 251~252초 | 1.01~1.15초 | 1.47~1.57초 |

업그레이드 중 4회 가운데 kro와 ACK의 1회는 업그레이드가 끝난 직후에 잰 값입니다. 업그레이드 중 self-heal 지연은 업그레이드가 끝난 뒤에도 똑같이 재현됐으므로 업그레이드가 아니라 앞서 설명한 self-heal 백오프 때문입니다. API 서버 버전이 1.36.4와 1.37.0 사이를 오가던 약 3분 동안에는 kro와 ACK 반영 시간을 재지 못했습니다. 노드 그룹은 올리지 않았습니다.

in-place 업그레이드에서 capability를 따로 챙길 일은 없었습니다. self-managed라면 새 Kubernetes 버전을 컨트롤러가 지원하는지 확인하고 필요하면 컨트롤러부터 올려야 하지만, 관리형은 그 호환성 확인을 AWS에 맡기는 구조입니다. 다만 EKS upgrade insights의 점검 항목에는 capability를 다루는 항목이 없었습니다.

### 버전을 고를 수 없다는 점

`create-capability`와 `update-capability`에는 버전 인자가 없고, AWS 문서는 "automatic updates and security patches"라고만 설명합니다. 업데이트 시점, 사전 공지, 유지 관리 창, capability 버전별 릴리스 노트, 이전 버전으로 되돌리는 방법은 문서에서 찾지 못했습니다. 2026년 7월에 추가된 [클러스터 버전 rollback](./08-eks-upgrades.md)은 Kubernetes 마이너 버전을 되돌리는 기능이며, rollback 문서는 capability를 다루지 않습니다. capability에는 버전 인자가 없으므로 capability 버전을 되돌리는 수단으로 볼 수 없습니다(추론). 실측에서는 10월 21일에 만든 Argo CD가 `3.4.6-eks-2`, 하루 뒤 다른 클러스터에 만든 Argo CD가 `3.4.7-eks-1`이었습니다. 클러스터 업그레이드와 상관없이 컨트롤러 버전이 바뀔 수 있습니다.

새 버전에 버그가 있을 때를 대비해 다음을 준비합니다.

| 대비 | 방법 | 근거 |
|---|---|---|
| 버전 변화 기록 | `describe-capability`의 `capability.version`을 주기적으로 기록해 장애 시점과 맞춰 봄 | 실측(필드 확인) |
| 검증 클러스터 | 같은 capability를 켠 클러스터에서 운영 RGD, Application, ACK CR을 먼저 실행. 단, 버전이 바뀌는 순서를 정할 수 없어 운영보다 먼저 바뀐다는 보장은 없음 | 추론 |
| 동작을 Git에 고정 | health check(`resource.customizations`), sync 옵션, RBAC를 Git에 두어 재생성이나 이전 때 같은 동작을 재현 | 실측(설정 반영 확인) |
| AWS Support | 사용자가 되돌릴 방법이 없으므로 케이스로 문의. self-heal 타이밍 조정은 AWS 문서가 Support로 안내함 | 추론(self-heal 타이밍은 문서 기준) |
| self-managed로 일시 전환 | RETAIN으로 capability를 지우면 CRD와 리소스가 남고, 같은 CRD를 쓰는 OSS 컨트롤러가 이어받음(kro, ACK, Argo CD 모두 실측). Argo CD는 cluster Secret의 `server`를 EKS ARN에서 API 주소(로컬은 `https://kubernetes.default.svc`)로 바꿔야 했고, ARN으로 등록한 원격·private spoke는 OSS에서 네트워크 경로와 인증이 따로 필요함. 관리형으로 돌아가려면 다시 만들어야 함(Argo CD 약 6분) | 실측 |
| ACK 서비스 단위 되돌리기 | 문제가 있는 서비스만 `disabledServices`에 넣고 해당 서비스의 self-managed 컨트롤러를 설치하거나 다시 올림. OSS 컨트롤러에는 별도 IAM 연결이 필요하고, IAMRoleSelector를 쓰면 `featureGates.IAMRoleSelector=true`와 `enableCARM=false`도 필요. capability가 설치한 CRD 위에서 OSS 차트를 돌리는 것은 시험하지 않음. 이미 설치된 CRD는 남음(실측) | 문서 기준 |

버전을 고정해야 하는 요구가 분명하다면 AWS 문서도 self-managed를 권합니다("require specific Kubernetes resource API versions, custom controller builds").

<span id="multicluster"></span>

## 8. 멀티 클러스터와 blue/green 교체

### Argo CD hub와 private spoke

hub 클러스터의 Argo CD capability로, 같은 계정·같은 VPC에 있고 API 엔드포인트가 private 전용인 spoke 클러스터를 네트워크 설정(엔드포인트, 보안 그룹, 라우팅) 없이 등록했습니다. 다른 VPC의 워크스테이션에서는 spoke에 닿지 않았으므로 AWS가 제공하는 경로를 거친 것으로 보입니다. spoke에는 hub의 capability role로 access entry를 직접 만들어야 합니다.

| spoke access entry 권한 | 결과 |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | 연결·인증은 성공, `CreateNamespace=true` 때문에 `namespaces is forbidden`. 자동 재시도 5회(약 303초)를 쓰고 멈춤 |
| + `AmazonEKSArgoCDClusterPolicy`, 수동 sync | 11.1초 만에 Synced, Healthy |

- cluster Secret은 EKS ARN만 받으므로 EKS가 아닌 클러스터는 배포 대상이 될 수 없습니다(문서 기준).
- Application 요금은 대상 클러스터별 Application 수로 매기므로 hub든 클러스터별 배치든 같고, capability 요금만 Argo CD 수만큼 늘어납니다. 대신 hub의 capability role은 모든 spoke에 쓰기 권한을 가지므로 AppProject destination 제한이나 팀별 capability 분리를 함께 검토합니다.
- 다른 계정의 클러스터는 대상 클러스터에 hub capability role로 access entry를 만들면 된다고 문서에 나옵니다(시험하지 않음). 관리형 한도는 원격 클러스터 100개, Application 3,000개입니다.

### kro와 ACK의 위치

kro와 ACK capability는 자기 클러스터만 관리합니다. hub의 Argo CD가 spoke에 RGD 인스턴스나 ACK CR을 배포하려면 spoke에도 kro, ACK(관리형 또는 OSS)가 있어야 합니다.

| 구성 | 맞는 경우 | 고민할 점 |
|---|---|---|
| 클러스터마다 kro, RGD는 ApplicationSet으로 배포 | 앱 팀이 각 클러스터에서 같은 API를 씀 | capability 요금과 RBAC 작업이 클러스터 수만큼 늘고, 클러스터마다 kro 버전이 같다는 보장이 문서에 없음(시험하지 않음) |
| hub에만 kro, RGD가 ACK 리소스와 spoke용 Argo CD Application을 생성 | 플랫폼 추상화를 한곳에서 정의 | hub에 권한과 장애 영향이 모이고 spoke 앱 팀은 kro API를 직접 쓰지 못함(시험하지 않음) |
| ACK 중앙(hub) | DB, IAM, VPC처럼 플랫폼 팀이 관리하는 리소스 | hub capability role이 모든 계정·리소스 권한을 가짐 |
| ACK 분산(클러스터마다) | 큐, 버킷을 워크로드 옆에서 선언 | IAMRoleSelector 설정이 클러스터 수만큼 늘어남 |
| ACK 혼합 | 관리자 범위 리소스는 hub, 워크로드 범위 리소스는 spoke | 같은 리소스를 두 곳에서 선언하지 않도록 범위 규칙이 필요 |

어느 구성이든 같은 AWS 리소스를 두 클러스터가 동시에 선언하지 않도록 범위 규칙을 정합니다.

### blue/green 교체

- **Argo CD**: capability는 클러스터에 딸린 리소스이므로, Argo CD를 둔 클러스터를 교체하면 capability를 다시 만들어야 합니다. 기본 주소는 `argocd-<ID>-<계정 ID>.eks-capabilities.<리전>.amazonaws.com`으로 클러스터마다 달라 UI·webhook 주소가 바뀝니다. 생성 시 `endpointPrefix`를 지정하면 지우고 같은 prefix로 다시 만들었을 때 주소가 같았습니다(같은 클러스터에서만 시험). 주소에 클러스터를 가리키는 부분이 없으므로 다른 클러스터로 옮겨도 같은 주소를 쓸 수 있을 것으로 보입니다. 다만 prefix가 계정·리전 안에서 하나뿐이라면(시험하지 않음) 옛 클러스터와 새 클러스터가 동시에 가질 수 없어, 교체가 "지우고 다시 만들기"가 되고 그동안(실측 100초 + 338초) UI, webhook, 동기화가 멈춥니다. 멈출 수 없다면 새 prefix로 새 capability를 먼저 띄우고 Git webhook 주소를 바꾸되, 옛 쪽의 자동 sync를 끄거나 Application을 non-cascading으로 지운 뒤 새 쪽을 켜고, 새 capability role의 access entry를 대상 클러스터에 먼저 만들어 둡니다(시험하지 않음). prefix는 생성 후 바꿀 수 없습니다. Argo CD는 자주 교체하는 워크로드 클러스터가 아니라 별도 hub에 두는 편이 낫습니다.
- **kro**: ClusterRole과 바인딩은 Git으로 옮길 수 있지만 access entry에 Kubernetes 그룹을 붙이는 일은 EKS API 호출입니다. 클러스터를 만드는 IaC(eksctl, Terraform 등)에 넣어 둡니다.
- **ACK**: 옛 클러스터 CR에 `deletion-policy: retain`을 달아 지운 뒤, 새 클러스터에서 `adoption-policy: adopt-or-create`로 가져오는 순서를 생각할 수 있습니다(각 단계는 실측, 두 클러스터 사이의 전체 순서는 시험하지 않음). `eks:eks-capability-arn` 태그로 변경을 막는 SCP를 걸었다면 새 capability는 ARN이 달라 가져오기가 막힐 수 있으므로, 교체 기간에 조건을 풀거나 환경·팀 태그로 조건을 겁니다.

<span id="compare"></span>

## 9. self-managed와 비교, 선택 기준

| 항목 | 관리형 capability | self-managed(OSS) |
|---|---|---|
| 설치 시간 | Argo CD 349초, kro 70초, ACK 386초 | Argo CD 43.4초, kro 15.6초, ACK 컨트롤러 3개 46초 |
| 노드 리소스 | 없음 | Argo CD Pod 7개(메모리 339~624Mi), kro Pod 1개(요청 256m, 128Mi), ACK Pod 3개(각 요청 50m, 64Mi) |
| 버전 | AWS가 정함, 고정 불가 | 직접 선택(측정 시점 Argo CD v3.5.5, ACK s3 1.13.1이 최신) |
| 기본 권한 | 좁음. 배포·하위 리소스·IAM 권한을 직접 부여 | Argo CD, kro 차트 기본값 `*/*/*` |
| 성능 | kro, ACK, Argo CD self-heal은 OSS와 같음. Argo CD 기본 폴링은 더 느림 | 비교 기준(Argo CD 3.4.6, kro 0.9.4는 같은 버전으로 측정. ACK는 OSS가 한 단계 높은 버전) |
| SSO | Identity Center만, 설정 두 필드 | Dex, OIDC 등 직접 구성 |
| 원격 클러스터 | EKS ARN + access entry, private도 네트워크 설정 없이 | 클러스터마다 API 주소, 인증, 네트워크 경로 |
| 빠지는 기능 | Argo CD Notifications, CMP, `argocd admin`, Lua 표준 라이브러리, ACK FieldExport | 없음 |
| 직접 조정할 수 없는 값 | Argo CD 폴링, ACK resync 주기, 컨트롤러 플래그·리소스 한도. Argo CD self-heal 백오프는 AWS Support 경유 | 모두 조정 가능 |
| 로그 | Vended Logs | `kubectl logs`, 직접 수집 |

관리형이 맞는 경우는 다음과 같습니다.

- 여러 EKS 클러스터, 특히 private 클러스터나 다른 계정의 클러스터에 배포하는 hub를 만들 때
- 조직의 AWS 로그인이 이미 Identity Center로 모여 있고, Argo CD SSO를 직접 운영하고 싶지 않을 때
- 여러 AWS 서비스를 Kubernetes에서 다루지만 서비스마다 ACK 컨트롤러를 운영하기 부담스럽고, 팀별 IAM 분리가 필요할 때
- 플랫폼 컨트롤러 권한을 기본으로 좁게 두고 access entry와 RBAC에 명시적으로 남기고 싶을 때

self-managed를 유지하는 편이 나은 경우는 다음과 같습니다.

- Notifications, CMP, FieldExport, Lua 표준 라이브러리에 의존할 때
- EKS가 아닌 클러스터가 배포 대상에 섞여 있을 때
- Argo CD만 조직 Identity Center와 다른 IdP를 써야 하는데 계정 인스턴스를 쓸 수 없을 때
- 컨트롤러 버전과 업그레이드 시점, 폴링·resync 주기를 직접 통제해야 할 때

검토 시점은 클러스터가 두 개 이상으로 늘기 전이 좋습니다. hub 위치, Identity Center 인스턴스, `endpointPrefix`는 생성 후 바꿀 수 없거나 바꾸기 번거롭습니다. self-managed Argo CD의 HA 구성이나 메이저 업그레이드를 다시 해야 할 때도 검토할 만합니다. AWS 문서의 이전 절차는 기존 컨트롤러를 0으로 줄이고, Application과 Secret을 옮기고, `destination.server`를 ARN으로 바꾸는 순서이며, 그동안 동기화가 멈춥니다(시험하지 않음).

<span id="pricing"></span>

## 10. 요금

서울 리전(ap-northeast-2) 요금이며 2026년 10월 21일 AWS Pricing API로 조회했습니다. 한 달은 730시간으로 계산했습니다.

| capability | capability 요금 | 관리 대상 요금 | 예시(한 달) |
|---|---|---|---|
| Argo CD | 시간당 $0.034799(월 약 $25.4) | Application 하나당 시간당 $0.001726(대상 클러스터별로 셈) | 앱 9개 약 $36.7, 앱 100개 약 $151 |
| kro | 시간당 $0.006038(월 약 $4.4) | 인스턴스 하나당 시간당 $0.000061 | 인스턴스 100개 약 $8.9 |
| ACK | 시간당 $0.006038(월 약 $4.4) | 리소스 하나당 시간당 $0.000061 | 리소스 200개 약 $13.3 |

비교 기준으로, m7g.large(서울 시간당 $0.1003) 비용을 이번 기본 설치의 self-managed 컨트롤러가 쓰는 비율만큼 나누면 Argo CD 약 $5.6(메모리 624Mi 기준), kro 약 $9.4(CPU 요청 256m 기준), ACK 3개 약 $5.5(CPU 요청 150m 기준)입니다. HA 구성이나 앱·서비스 수가 늘면 OSS 쪽도 커집니다. Argo CD는 앱 수가 늘수록 관리형이 비싸지고, kro와 ACK는 차이가 작으므로 비용보다 운영 부담과 기능 차이로 고르게 됩니다.

<span id="refs"></span>

## 11. 검증 범위와 참고 자료

실측은 ap-northeast-2의 단일 계정에서 EKS 1.36.4 클러스터 하나와, 업그레이드·멀티 클러스터용 클러스터 두 개(hub 1.36 → 1.37, private spoke 1.37)로 했습니다. 시나리오는 1~5회 반복했고, Argo CD 앱은 최대 9개, kro 인스턴스는 최대 6개, ACK 리소스는 20개 안팎이었습니다. ACK는 S3, SQS, DynamoDB만 시험했습니다. 다음은 시험하지 않았으며 문서 기준입니다: Okta·Entra ID 연동과 Identity Center 계정 인스턴스, VPC 엔드포인트 비공개 접근, 다른 계정·다른 VPC의 클러스터 등록, Notifications와 CMP, 교차 계정 ACK, 관리형과 OSS를 동시에 띄운 무중단 이전, 두 클러스터 사이의 ACK retain·adoption 전체 순서. 시험 클러스터와 AWS 리소스는 측정 후 삭제했습니다.

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [EKS Capabilities considerations](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Capability Kubernetes resources](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Argo CD considerations](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [Comparing EKS Capability for Argo CD to self-managed Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [Register target clusters](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [Argo CD 관리형 구성](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [Configure kro permissions](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [Comparing EKS Capability for kro to self-managed kro](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [Configure ACK permissions](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [Comparing EKS Capability for ACK to self-managed ACK](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [Access EKS Capabilities controller logs](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [Roll back a cluster to a previous Kubernetes version](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Amazon EKS pricing](https://aws.amazon.com/eks/pricing/)
- 실측 블로그: [관리형 Argo CD](https://blog.atomai.click/eks-capabilities-argocd/), [관리형 kro](https://blog.atomai.click/eks-capabilities-kro/), [관리형 ACK](https://blog.atomai.click/eks-capabilities-ack/)
- 실측 매니페스트: [Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[EKS Capabilities 퀴즈](../quizzes/eks/13-eks-capabilities-quiz.md)
