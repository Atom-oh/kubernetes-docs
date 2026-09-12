# VPC Lattice 퀴즈

YAML뿐 아니라 사전 요구사항도 본문과 함께 확인하세요.

## 1. Amazon VPC Lattice의 주요 목적은 무엇인가요?

- A) 인터넷 DNS 기반 글로벌 부하 분산
- B) VPC·계정 간 프라이빗 애플리케이션 및 리소스 연결
- C) 리전 간 데이터베이스 복제
- D) 모든 IP 라우팅 대체

<details>
<summary>정답 보기</summary>

B. Lattice는 서비스와 리소스 구성을 연결합니다. HTTP 서비스 라우팅과 리소스 접근 모델은 구분되며 연결 관계, 네트워크 제어와 인가가 여전히 필요합니다.

</details>

## 2. 서비스 네트워크는 무엇을 나타내나요?

- A) 물리 네트워크 장비
- B) 서비스/리소스와 클라이언트 네트워크 연결을 묶는 논리적 그룹
- C) 서브넷 라우팅 테이블
- D) 모든 서비스가 공유하는 HTTP 리스너 하나

<details>
<summary>정답 보기</summary>

B. 리스너와 규칙은 개별 서비스에 속합니다. 연결은 보안 그룹과 해당 정책에 따른 경로를 제공하며 모든 요청을 무조건 인가하지 않습니다.

</details>

## 3. App Mesh와 Lattice에 대한 올바른 설명은 무엇인가요?

- A) Lattice는 파드마다 Envoy 사이드카가 필요함
- B) App Mesh는 Envoy 프록시를 사용하고 Lattice는 애플리케이션 사이드카 없이 관리형 데이터 플레인을 제공
- C) 다른 모든 메시는 사이드카가 필수
- D) 검토일에 App Mesh 지원은 이미 종료됨

<details>
<summary>정답 보기</summary>

B. AWS App Mesh 지원 종료일은 2026-09-30으로, 2026-09-11 검토일에는 아직 예정된 미래입니다. 신규 App Mesh 배포보다 마이그레이션을 계획하세요. 다른 메시 모드의 사이드카 요구사항은 각각 다릅니다.

</details>

## 4. AWS Gateway API Controller의 리소스 매핑은 어떻게 되나요?

- A) Kubernetes Service마다 서비스 네트워크 하나 생성
- B) Gateway는 이름으로 네트워크를 선택하고 HTTPRoute마다 고유 Lattice 서비스/도메인 생성
- C) Gateway는 항상 모든 Route가 공유하는 인그레스 IP 하나 생성
- D) Ingress API만 사용

<details>
<summary>정답 보기</summary>

B. GatewayClass는 컨트롤러를 선택합니다. Gateway는 네임스페이스를 제외한 이름으로 기존 서비스 네트워크를 참조하며 백엔드 Service/엔드포인트가 대상 그룹을 정의합니다. Gateway만으로 네트워크가 생성되지는 않습니다.

</details>

## 5. 클라이언트는 할당된 Lattice 서비스 DNS 이름을 어떻게 얻어야 하나요?

- A) Kubernetes Service 이름 뒤에 리전을 붙임
- B) 추측한 호스트 이름에 서비스 네트워크 ID를 삽입
- C) get-service의 dnsEntry 또는 Route의 lattice-assigned-domain-name 어노테이션 조회
- D) Gateway.status.addresses를 모든 Route의 주소로 재사용

<details>
<summary>정답 보기</summary>

C. Route마다 서비스/도메인이 있습니다. 반환된 실제 값을 사용해야 하며 서비스 재생성 시 할당 이름이 달라질 수 있습니다. 사용자 지정 도메인에는 별도 DNS와 인증서 구성이 필요합니다.

</details>

## 6. 인증에 대한 올바른 설명은 무엇인가요?

- A) 서비스의 NONE은 모든 네트워크 정책을 해제
- B) 클라이언트에 IAM 역할이 있으면 AWS_IAM에서 서명 없는 curl 요청 허용
- C) AWS_IAM은 지원되는 서명 요청을 사용하며 적용되는 각 IAM 인가 계층에서 허용 필요
- D) RAM 공유가 Invoke 권한을 자동 부여

<details>
<summary>정답 보기</summary>

C. VPC Lattice는 SigV4와 SigV4A를 지원합니다. 서명에는 vpc-lattice-svcs와 UNSIGNED-PAYLOAD를 사용하세요. 호출자 자격 증명 기반 권한과 해당 네트워크/서비스 인증 정책이 모두 허용해야 하며 명시적 Deny가 우선합니다. NONE은 해당 계층에만 적용됩니다.

</details>

## 7. Lattice 서비스 대상 그룹의 명명된 유형이 아닌 것은 무엇인가요?

- A) INSTANCE
- B) IP
- C) LAMBDA
- D) RDS

<details>
<summary>정답 보기</summary>

D. 서비스 대상 그룹 유형에는 INSTANCE, IP, LAMBDA, ALB가 있습니다. 그렇다고 Lattice로 RDS를 연결할 수 없다는 뜻은 아닙니다. 리소스 구성과 리소스 게이트웨이가 별도의 TCP 리소스 접근 모델을 제공합니다. 서비스 인증 정책은 해당 리소스 트래픽에 적용되지 않습니다.

</details>

## 8. backendRefs 가중치 90:10은 무엇을 의미하나요?

- A) 연속된 열 요청 중 정확히 하나가 카나리로 전달
- B) 두 백엔드 간 상대적인 트래픽 분배
- C) 파드 복제본 수 요구사항
- D) Gateway API에서 지원하지 않는 어노테이션

<details>
<summary>정답 보기</summary>

B. 기본 backendRefs.weight가 상대 분배를 설정하며 작은 요청 표본의 결과가 정확히 일치할 필요는 없습니다. 두 백엔드가 존재하고 정상이어야 합니다. 카나리 비중을 늘리기 전에 오류와 지연 시간을 관측하세요.

</details>

## 9. 서비스 네트워크를 계정 간 공유하는 절차를 설명하세요.

<details>
<summary>정답 보기</summary>

소유자가 네트워크 ARN과 대상 계정·조직·OU로 RAM 공유를 만듭니다. 조직 공유가 활성화된 조직 내부 소비자에는 초대가 필요 없고, 그 외 해당 구성에서는 수락이 필요합니다. 소비자가 자신의 VPC를 연결하거나 적절한 서비스 네트워크 엔드포인트를 생성합니다. 공유는 Invoke 권한이 아닙니다. 호출자 정책, 인증 정책, 네트워크 경로와 보안 그룹도 접근을 허용해야 합니다. 공유를 중단해도 기존 연결은 남습니다.

</details>

## 10. 데모 백엔드의 Kubernetes 상태 검사 정책을 작성하세요.

<details>
<summary>정답 보기</summary>

대상 Service와 같은 네임스페이스에 TargetGroupPolicy를 사용합니다. 컨트롤러 CRD는 intervalSeconds/timeoutSeconds/statusMatch를 사용하고 AWS API는 healthCheckIntervalSeconds/healthCheckTimeoutSeconds/matcher를 사용합니다.

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: TargetGroupPolicy
metadata:
  name: stable-health
  namespace: lattice-demo
spec:
  targetRef:
    group: ''
    kind: Service
    name: service-stable
  protocol: HTTP
  protocolVersion: HTTP1
  healthCheck:
    enabled: true
    protocol: HTTP
    protocolVersion: HTTP1
    port: 8080
    path: /health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThresholdCount: 2
    unhealthyThresholdCount: 2
    statusMatch: '200'
```

백엔드는 실제 8080에서 수신하고 /health에 200을 반환해야 합니다. 임계값은 준비 상태 판단을 돕지만 가용성이나 무중단을 보장하지 않습니다. 대상 유형·프로토콜별 동작을 검토하세요.

</details>

## 11. Transit Gateway와 VPC Lattice의 차이를 설명하세요.

<details>
<summary>정답 보기</summary>

Transit Gateway는 네트워크 간 IP 트래픽을 라우팅합니다. Lattice는 서비스와 리소스 구성을 노출합니다. HTTP 서비스 경로는 L7 라우팅을 사용할 수 있고 TLS/TCP/리소스 기능은 특성이 다릅니다. 두 서비스를 함께 사용할 수 있습니다. 서비스 네트워크 VPC 엔드포인트는 해당 전이·피어링 경로의 클라이언트를 지원하지만 직접 VPC 연결만으로 전이 접근 권한이 생기지는 않습니다.

</details>

## 12. 인증 정책의 적용 계층과 데모 API 경로 제한 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

AWS_IAM으로 구성된 서비스 네트워크와 개별 서비스에 인증 정책을 적용합니다. 해당 두 계층과 호출자의 자격 증명 기반 정책이 모두 요청을 허용해야 합니다. 와일드카드는 StringLike로 매칭하고 루트 경로도 명시합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/api",
            "/api/*"
          ]
        }
      }
    }
  ]
}
```

StringEquals는 /api/*를 문자 그대로 매칭합니다. 이 정책은 정해진 경로를 대상으로 하며 애플리케이션 정규화와 컨트롤러 경로 라우팅은 별도 동작입니다. 호출 인가에는 PutResourcePolicy가 아니라 PutAuthPolicy를 사용합니다.

</details>

## 13. IRSA를 사용하는 AWS Gateway API Controller v2.1.3 설치를 설명하세요.

<details>
<summary>정답 보기</summary>

클러스터의 지원 Kubernetes 버전, Gateway API 호환성, IAM OIDC 공급자, 네트워크/웹훅 도달성을 확인합니다. 해당 계정과 기능에 맞게 릴리스 권장 정책을 검토하세요. 넓은 upstream 권한은 최소 권한을 보장하지 않습니다. 전용 컨트롤러 서비스 계정과 릴리스된 OCI 차트를 사용합니다.

```bash
curl --fail --location --output controller-policy-upstream.json \
  https://raw.githubusercontent.com/aws/aws-application-networking-k8s/v2.1.3/files/controller-installation/recommended-inline-policy.json

# Use the policy reviewed for this account and the enabled controller features.
export REVIEWED_POLICY_FILE=controller-policy-reviewed.json
test -s "$REVIEWED_POLICY_FILE"
export CONTROLLER_POLICY_ARN="$(aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document "file://$REVIEWED_POLICY_FILE" \
  --query Policy.Arn --output text)"

# Prerequisite: this cluster's IAM OIDC provider already exists.
eksctl create iamserviceaccount \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace aws-application-networking-system \
  --name gateway-api-controller \
  --attach-policy-arn "$CONTROLLER_POLICY_ARN" \
  --approve
```

```bash
curl --fail --location --output gateway-api-v1.5.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.0/standard-install.yaml
# Inspect changes first if any Gateway API controller is already installed.
kubectl apply --server-side -f gateway-api-v1.5.0.yaml

helm pull oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart \
  --version v2.1.3
helm show crds ./aws-gateway-controller-chart-v2.1.3.tgz > lattice-crds.yaml
kubectl apply --server-side -f lattice-crds.yaml

helm install gateway-api-controller ./aws-gateway-controller-chart-v2.1.3.tgz \
  --namespace aws-application-networking-system --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=gateway-api-controller \
  --set-string awsRegion="$AWS_REGION" \
  --set-string awsAccountId="$AWS_ACCOUNT_ID" \
  --set-string clusterVpcId="$VPC_ID" \
  --set-string clusterName="$CLUSTER_NAME" \
  --wait --timeout 5m

kubectl -n aws-application-networking-system get pods
kubectl -n aws-application-networking-system logs \
  -l control-plane=gateway-api-controller -c manager --tail=100
```

컨트롤러 역할은 리소스를 관리하며 애플리케이션 호출자 역할과 다릅니다. 기존 서비스 계정/릴리스는 소유권을 고려해 업그레이드해야 합니다. Helm은 CRD를 자동 업그레이드하지 않습니다. 별도 서비스 네트워크/인증 정책 구성은 본문을 참고하세요.

</details>

## 14. 안정 버전/카나리를 90:10으로 분배하는 HTTPRoute를 작성하세요.

<details>
<summary>정답 보기</summary>

사전 요구사항은 본문의 lattice-demo 내 my-network HTTPS Gateway, 기존 서비스 네트워크와 활성 인증 정책, 8080의 두 백엔드 Deployment/Service, 대상 그룹 상태 검사 정책입니다. 다음을 적용합니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

본문의 IAMAuthPolicy도 이 Route에 적용하고 조정 결과를 확인하세요. 가중치 어노테이션은 필요하지 않습니다. Route의 할당 도메인과 서명된 HTTPS 요청을 사용하며 apply 성공만으로 백엔드 정상 상태가 증명되지는 않습니다.

</details>

## 15. 전용 관리 서비스의 /admin 및 하위 경로를 AdminRole과 DevOpsRole만 호출하도록 구성하세요.

<details>
<summary>정답 보기</summary>

아래를 서비스의 완전한 인증 정책으로 사용하고 실제 계정/역할 ARN을 넣으세요. 전용 서비스에 AWS_IAM을 설정하고 호출자 자격 증명 기반 정책과 네트워크 인증 정책도 이 역할과 경로를 허용해야 합니다. 본문의 API 전용 네트워크 정책은 이 별도 관리 서비스를 위해 검토된 변경이 필요합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::123456789012:role/AdminRole",
          "arn:aws:iam::123456789012:role/DevOpsRole"
        ]
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/admin",
            "/admin/*"
          ]
        }
      }
    }
  ]
}
```

컨트롤러 소유인 lattice-demo의 admin HTTPRoute에는 실제 CRD로 연결합니다.

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: admin-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: admin
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["arn:aws:iam::123456789012:role/AdminRole","arn:aws:iam::123456789012:role/DevOpsRole"]},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/admin","/admin/*"]}}}]}'
```

광범위한 AllowGeneralAccess 문은 없습니다. 이 정책에서 다른 역할·경로에는 Allow가 없으며 /admin/*만이 아니라 /admin도 명시합니다. 경로 정규화·인코딩은 애플리케이션 보안 요구사항으로 다루세요. 역할이 제한된 전용 서비스와 애플리케이션 인가는 경로 별칭에 대한 의존을 줄입니다. 직접 백엔드 접근도 보호해야 합니다. IAMAuthPolicy 삭제는 대상 인증 유형을 NONE으로 바꾸므로 거부나 안전한 롤백 수단이 아닙니다.

</details>

13–15개 정답이면 이 장의 개념을 잘 이해한 상태이고, 10–12개는 틀린 주제를 복습하며, 0–9개는 본문을 다시 읽어보세요. 퀴즈 점수가 운영 경험을 증명하지는 않습니다.

[본문으로 돌아가기](../../networking/02-vpc-lattice.md)
