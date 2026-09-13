# EKS 클러스터 생성 실습 가이드

> **난이도**: 중급
> **예상 소요 시간**: 60–90분, 생성·삭제 시간은 환경에 따라 달라짐
> **마지막 업데이트**: 2026년 9월 12일

## 학습 목표

- eksctl로 전용 EKS 실습 클러스터를 생성합니다.
- 리소스를 변경하기 전에 AWS 계정과 클러스터 식별자를 확인합니다.
- 노드를 살펴보고 샘플 애플리케이션을 배포·확장합니다.
- 실습 리소스를 삭제하고 정리가 완료되지 않은 항목을 확인합니다.

## 사전 요구 사항

- [ ] 승인된 AWS 실습 계정과 임시 역할 자격 증명. 예를 들어 IAM Identity Center로 로그인합니다. 관리자에게 이 구성에 필요한 EKS, EC2, CloudFormation, IAM/PassRole 등의 권한을 검토받으세요. 이 실습을 위해 장기 자격 증명의 IAM 사용자를 만들거나 AdministratorAccess를 부여하지 않습니다.
- [ ] AWS CLI v2, eksctl, kubectl, Bash, Python 3, jq, curl.
- [ ] 승인된 공인 IPv4 클라이언트 CIDR. 일반적으로 워크스테이션의 현재 외부 출발지 주소 `/32`입니다. 생성기는 `/24`보다 넓은 범위를 거부하며, 조직 기준이 더 엄격하면 해당 기준을 적용합니다.
- [ ] [EKS 클러스터 생성](../../eks/02-eks-cluster-creation-part1.md) 학습 완료.

이 실습은 EKS 1.36 관리형 노드 그룹을 사용합니다. 검토일의 AWS 지원 목록에서 1.36은 표준 지원 대상이며, 이전 예제의 1.31은 확장 지원 대상입니다. 실행 전에 최신 AWS 지원 일정을 확인하세요. kubectl은 API 서버와 마이너 버전 차이가 1 이내여야 하며, 이 예제에서는 1.36을 권장합니다.

예제는 eksctl 0.229.0과 kubectl 1.36.2의 스키마 및 로컬 모의 환경으로 확인했습니다. **이번 감사에서 실제 클러스터를 생성하거나 배포 시간을 측정하지는 않았습니다.** 실습 계정의 권한, 할당량, 인스턴스 가용성과 네트워크 접근은 별도로 확인해야 합니다.

EKS, EC2, EBS, NAT Gateway 및 데이터 전송에는 비용이 발생합니다. 이 구성은 프라이빗 노드와 NAT Gateway 하나를 생성합니다. 이는 실습의 비용·가용성 선택이며 프로덕션 고가용성 설계가 아닙니다. `STANDARD` 지원 정책은 표준 지원 종료 후 자동 버전 업그레이드를 허용해 확장 지원으로 진입하지 않게 하는 설정입니다. 클러스터를 중지하거나 다른 비용을 없애지는 않습니다.

전용 Bash 터미널(**터미널 A**)에서 순서대로 실행하세요. 출력된 비공개 실습 디렉터리를 보관하고 kubeconfig나 식별 기록을 커밋하지 마세요. 뒤의 명령은 이 터미널의 변수와 함수에 의존합니다.

## 실습 1: 도구와 계정 확인

### 1.1 도구 확인

```bash
aws --version
eksctl version
kubectl version --client
python3 --version
jq --version
```

### 1.2 대상 계정과 클라이언트 범위 설정

다음 블록 전에 `EXPECTED_ACCOUNT_ID`와 `CLIENT_CIDR`을 승인된 실제 값으로 설정하세요. 예제 계정 ID나 문서 전용 IP 주소를 복사하지 마세요. `AWS_REGION`의 기본값은 서울이며 두 리전 환경 변수를 일치시킵니다.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended 12-digit lab account ID}"
: "${CLIENT_CIDR:?Set your approved public client IPv4 CIDR, usually a /32}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLIENT_CIDR
umask 077
export LAB_DIR
LAB_DIR=$(mktemp -d "$PWD/eks-lab.XXXXXXXX")
export LAB_RUN_ID
LAB_RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
export CLUSTER_NAME="eks-lab-$LAB_RUN_ID"
export KUBECONFIG="$LAB_DIR/kubeconfig"
printf 'Private lab directory: %s\nCluster: %s\nRegion: %s\n' "$LAB_DIR" "$CLUSTER_NAME" "$AWS_REGION"
```

아래 생성기는 입력을 검사하고 리소스 생성 전에 의도한 클러스터 정보를 기록합니다.

```bash
python3 - <<'PY'
import ipaddress, json, os, re
from pathlib import Path
account = os.environ["EXPECTED_ACCOUNT_ID"]
region = os.environ["AWS_REGION"]
name = os.environ["CLUSTER_NAME"]
run_id = os.environ["LAB_RUN_ID"]
network = ipaddress.ip_network(os.environ["CLIENT_CIDR"], strict=True)
if not re.fullmatch(r"\d{12}", account):
    raise SystemExit("Expected a 12-digit account ID")
if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid Region")
if not re.fullmatch(r"eks-lab-[0-9a-f]{12}", name) or name != "eks-lab-" + run_id:
    raise SystemExit("Unexpected lab name")
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed narrow IPv4 CIDR (/24 or narrower); never 0.0.0.0/0")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": name, "region": region, "version": "1.36",
                 "tags": {"content-lab-id": run_id}},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "vpc": {"clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [str(network)], "nat": {"gateway": "Single"}},
    "managedNodeGroups": [{
        "name": "workers", "instanceType": "t3.medium", "amiFamily": "AmazonLinux2023",
        "desiredCapacity": 2, "minSize": 1, "maxSize": 3,
        "privateNetworking": True, "volumeSize": 20, "volumeType": "gp3",
        "volumeEncrypted": True
    }]
}
directory = Path(os.environ["LAB_DIR"])
(directory / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
(directory / "lab-state.json").write_text(json.dumps({
    "account": account, "region": region, "cluster": name, "labId": run_id
}, indent=2) + "\n")
PY
```

```bash
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf '%s\n' 'Account mismatch; stop.' >&2; return 1; }
}
check_account
aws sts get-caller-identity --region "$AWS_REGION"
```

반환된 계정은 `EXPECTED_ACCOUNT_ID`와 같아야 합니다. 임시 자격 증명에서는 assumed-role ARN이 정상입니다. 계정이 다르거나 인증이 실패하면 중단하세요.

## 실습 2: 클러스터 생성과 식별

### 2.1 구성 검토

```bash
cat "$LAB_DIR/cluster.json"
```

구성은 EKS 1.36, API 기반 access entry, `t3.medium` 관리형 노드 2개, AL2023, 암호화된 20 GiB gp3 노드 디스크와 고유한 `content-lab-id` 태그를 지정합니다. API 엔드포인트는 둘 다 활성화합니다. 노드는 프라이빗 접근을 사용하고, 퍼블릭 엔드포인트에는 승인된 클라이언트 CIDR만 허용합니다. 노드에는 이미지·패키지 엔드포인트로의 아웃바운드 접근도 필요합니다.

### 2.2 클러스터 생성

다음 명령은 과금되는 리소스를 생성합니다. 생성과 정리에 충분한 시간을 확보하세요. 45분 timeout은 기다리는 시간의 상한이지 완료 보장이 아닙니다.

```bash
# MUTATION: creates billed CloudFormation/EKS/VPC/NAT/EC2/EBS resources.
check_account
eksctl create cluster --config-file "$LAB_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

생성 실패나 중단이 발생하면 **새 이름으로 클러스터를 추가 생성하거나 정상 정리 블록을 무작정 실행하지 마세요.** `lab-state.json`과 `cluster.json`을 보관하고 해당 이름의 CloudFormation 스택, 태그, 계정과 리소스를 먼저 대조합니다. CLI 오류가 리소스 미생성을 뜻하지 않으며, 미정리 리소스에는 비용이 계속 발생할 수 있습니다.

### 2.3 식별 정보와 전용 kubeconfig 저장

생성 성공 후에만 실행합니다. 앞의 `--write-kubeconfig=false`는 기존 kubeconfig를 변경하지 않으며, 다음 명령은 전용 실습 경로에만 기록합니다.

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,createdAt:createdAt,endpoint:endpoint,tags:tags}' \
  --output json > "$LAB_DIR/cluster-identity.json"
jq -e --arg id "$LAB_RUN_ID" '.tags["content-lab-id"] == $id' "$LAB_DIR/cluster-identity.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
```

계정, 클러스터 ARN, 생성 시각, 소유권 태그와 kubeconfig 엔드포인트를 대조하는 함수를 정의합니다. 이후 변경 전에 이 검사를 수행합니다.

```bash
check_lab() {
  check_account || return
  local current endpoint
  current=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --output json) || return
  jq -e --arg id "$LAB_RUN_ID" --slurpfile saved "$LAB_DIR/cluster-identity.json" '
    .cluster.arn == $saved[0].arn and
    .cluster.createdAt == $saved[0].createdAt and
    .cluster.tags["content-lab-id"] == $id and
    .cluster.endpoint == $saved[0].endpoint
  ' <<<"$current" >/dev/null || { printf '%s\n' 'Cluster identity mismatch; stop.' >&2; return 1; }
  endpoint=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CLUSTER_NAME" config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}') || return
  jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$LAB_DIR/cluster-identity.json" >/dev/null ||
    { printf '%s\n' 'Kubeconfig endpoint mismatch; stop.' >&2; return 1; }
}
check_lab
```

### 검증

```bash
check_lab
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -o wide
kubectl --context "$CLUSTER_NAME" wait node --selector=eks.amazonaws.com/nodegroup=workers \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/nodegroup=workers -o json |
  jq -e '(.items | length) == 2 and all(.items[];
    any(.status.conditions[]; .type == "Ready" and .status == "True"))'
```

노드 2개가 모두 Ready여야 합니다. 등록된 노드가 부족하면 노드 그룹과 CloudFormation 이벤트를 확인하세요. 컨트롤 플레인 생성 성공만으로 워커 노드의 정상 동작을 판단하지 않습니다.

## 실습 3: 클러스터 탐색

앞에서 확인한 노드 목록에서 `NODE_NAME`을 선택해 설정한 후 실행합니다. 이 실습은 일반 관리형 노드를 사용하므로 시스템 컴포넌트 구성은 순수 Auto Mode 클러스터와 다릅니다.

```bash
check_lab
: "${NODE_NAME:?Choose a node name from the preceding list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe node "$NODE_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get pods
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get services
# Run separately; preserve the actual error if the metrics API is unavailable.
if ! kubectl --context "$CLUSTER_NAME" --request-timeout=15s top nodes; then
  printf 'Metrics query failed; inspect the error and metrics API status.\n' >&2
fi
```

`kubectl top`에는 metrics API가 필요합니다. 실패 원인은 metrics-server 미설치, 메트릭 미수집, RBAC 또는 연결 문제일 수 있습니다. 실제 오류를 보존하고 원인을 진단하세요. 실패를 무조건 metrics-server 미설치로 해석하지 않습니다.

## 실습 4: 애플리케이션 배포와 확장

### 4.1 nginx 배포

Deployment에 리소스 requests/limits와 readiness probe를 지정합니다. Service 유형은 `ClusterIP`입니다. 이 실습에서는 로드 밸런서 컨트롤러를 설치하거나 공인 로드 밸런서를 생성하지 않습니다.

```bash
cat > "$LAB_DIR/app.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: eks-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.4
        ports:
        - containerPort: 80
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
          initialDelaySeconds: 2
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
  namespace: eks-lab
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
YAML
```

```bash
# MUTATION in the verified dedicated lab cluster.
check_lab
kubectl --context "$CLUSTER_NAME" create namespace eks-lab
kubectl --context "$CLUSTER_NAME" label namespace eks-lab "content-lab-id=$LAB_RUN_ID"
kubectl --context "$CLUSTER_NAME" apply -f "$LAB_DIR/app.yaml"
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
```

### 4.2 로컬 접근 확인

터미널 A에서 포트 전달을 시작한 뒤 같은 워크스테이션의 **터미널 B**에서 curl 명령을 실행합니다. 리스너는 루프백에만 바인딩합니다. 이 연결은 선택된 Pod를 확인하는 것이며 외부 로드 밸런싱이나 모든 복제본을 검증하지는 않습니다.

```bash
# Keep this in Terminal A; it binds only loopback. Stop with Ctrl+C before continuing.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab port-forward service/nginx 8080:80 --address=127.0.0.1 || test "$?" -eq 130
```

```bash
# Terminal B on the same workstation; no AWS credentials are needed for this local URL.
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
  http://127.0.0.1:8080/ --output /dev/null --write-out 'HTTP %{http_code}\n'
```

성공하면 `HTTP 200`을 출력합니다. 이후 단계로 진행하기 전에 터미널 A에서 Ctrl+C로 포트 전달을 중지하세요. 명령은 이 정상적인 사용자 중단을 허용하되 다른 실패는 계속 검사합니다.

### 4.3 복제본 4개로 확장

```bash
# MUTATION: after stopping port-forward in Terminal A.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab scale deployment/nginx --replicas=4
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n eks-lab get deployment nginx -o json |
  jq -e '.spec.replicas == 4 and .status.observedGeneration >= .metadata.generation and
         .status.readyReplicas == 4 and .status.availableReplicas == 4'
```

공인 LoadBalancer 실습도 필요하다면 [EKS 네트워킹](../../eks/03-eks-networking-part1.md)을 따라 사용할 컨트롤러, IAM 권한과 노출 범위를 먼저 구성하세요. 추가 리소스와 비용을 별도로 기록하고 정리해야 합니다. 호스트 이름 할당이나 Deployment readiness만으로 로드 밸런서의 종단 간 정상 동작이 입증되지는 않습니다.

## 정리

먼저 포트 전달을 중지합니다. 다음 블록은 실습 태그를 확인한 namespace와 전용 클러스터를 삭제합니다. namespace가 이미 없는 경우는 허용하지만, 조회에 실패하거나 태그가 다르면 삭제 가능한 것으로 취급하지 않습니다.

```bash
# DESTRUCTIVE: only the verified dedicated lab resources.
check_lab
namespace_json=$(kubectl --context "$CLUSTER_NAME" --request-timeout=15s \
  get namespace eks-lab --ignore-not-found -o json)
if [ -n "$namespace_json" ]; then
  jq -e --arg id "$LAB_RUN_ID" '.metadata.labels["content-lab-id"] == $id' \
    <<<"$namespace_json" >/dev/null
  kubectl --context "$CLUSTER_NAME" delete namespace eks-lab --wait=true --timeout=180s
fi
check_lab
eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --wait --timeout=45m
aws eks wait cluster-deleted --name "$CLUSTER_NAME" --region "$AWS_REGION"
# Keep private config/identity records until remaining resources/billing are checked.
```

삭제 오류를 확인하려면 `--wait`가 필요합니다. EKS 삭제 waiter는 컨트롤 플레인 객체의 부재를 확인할 뿐 모든 종속 리소스와 비용이 사라졌음을 보장하지 않습니다. 저장된 실습의 CloudFormation 스택 상태와 태그가 있는 EC2/EBS/NAT/VPC 잔여 리소스에서 `DELETE_FAILED` 또는 보존된 항목을 확인하세요. 확인이 끝날 때까지 로컬 구성·식별 기록을 보관합니다. 고정된 sleep으로 삭제 검증을 대체하지 마세요.

생성이 식별 정보 저장 단계에 도달하지 못했다면 비공개 의도 기록과 CloudFormation 이벤트·태그로 수동 소유권 확인을 수행합니다. 검사를 통과시키기 위해 `cluster-identity.json`을 임의로 만들지 마세요.

## 문제 해결

<details>
<summary>클러스터 생성이 실패합니다</summary>

승인된 역할의 권한, 서비스 할당량, 서브넷/IP 용량과 선택한 리전의 인스턴스 가용성을 확인하세요. eksctl은 CloudFormation을 사용합니다. 관리자 권한을 광범위하게 부여하기 전에 실제 실패 원인을 확인합니다.

```bash
check_account
eksctl utils describe-stacks --region "$AWS_REGION" --cluster "$CLUSTER_NAME"
```

부분 생성 복구 중에는 비공개 실습 디렉터리를 보관합니다. 삭제 명령을 실행하기 전에 실제 소유권과 대조하세요.

</details>

<details>
<summary>kubectl이 클러스터에 연결되지 않습니다</summary>

역할 자격 증명, access entry, DNS와 워크스테이션의 현재 외부 출발지 주소가 승인된 CIDR에 포함되는지 확인하세요. 전용 kubeconfig를 다시 만들어야 한다면 먼저 클러스터 식별자를 확인하고 이 실습 경로에만 기록합니다.

```bash
check_account
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
check_lab
```

클라이언트 주소가 바뀌었다고 엔드포인트를 전체 인터넷에 개방하지 마세요.

</details>

## 참고 자료

- [EKS supported versions](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS upgrade policy](https://docs.aws.amazon.com/eks/latest/userguide/view-upgrade-policy.html)
- [Cluster endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [eksctl IAM permissions](https://docs.aws.amazon.com/eks/latest/eksctl/minimum-iam-policies.html)
- [eksctl creation/deletion](https://docs.aws.amazon.com/eks/latest/eksctl/creating-and-managing-clusters.html)
- [kubectl version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Port forwarding](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
- [Official nginx image definitions](https://github.com/docker-library/official-images/blob/master/library/nginx)

## 다음 단계

- [EKS 클러스터 생성 퀴즈](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- [EKS 네트워킹](../../eks/03-eks-networking-part1.md)
