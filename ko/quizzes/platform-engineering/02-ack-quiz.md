# AWS Controllers for Kubernetes (ACK) 퀴즈

[ACK](../../platform-engineering/02-ack.md)

검토한 현재 controller 동작을 기준으로 원문의 15개 문제 주제를 유지했습니다.

## 1. ACK의 주요 목적은 무엇인가요?

<details>
<summary>정답 보기</summary>

Kubernetes API와 custom resource를 통해 AWS 리소스를 선언적으로 관리합니다. 자동 비용 절감이나 즉시 준비 완료를 보장하는 기능은 아닙니다.

</details>

## 2. 서비스마다 설치하는 구성 요소는 무엇인가요?

<details>
<summary>정답 보기</summary>

서비스 controller입니다. S3, IAM, SQS 등 필요한 controller와 해당 CRD를 선택합니다. 각 서비스의 지원 리소스와 필드는 versioned CRD에서 확인합니다.

</details>

## 3. controller의 AWS credential을 어떻게 제공하나요?

<details>
<summary>정답 보기</summary>

IRSA 또는 지원되는 EKS Pod Identity 같은 workload identity를 구성합니다. OIDC trust/association, ServiceAccount, SDK·agent 호환성과 최소 IAM 권한을 확인합니다. ConfigMap의 access key나 root credential을 사용하지 않습니다.

</details>

## 4. CR 삭제 후 AWS 리소스를 보존하는 값은 무엇인가요?

<details>
<summary>정답 보기</summary>

`services.k8s.aws/deletion-policy: retain`입니다. orphan은 현재 runtime의 허용 값이 아닙니다. 개별 CR, namespace의 서비스별 annotation, controller 기본값 순으로 우선합니다. 남은 AWS 리소스는 계속 관리해야 합니다.

</details>

## 5. 기존 AWS 리소스를 어떻게 가져오나요?

<details>
<summary>정답 보기</summary>

ResourceAdoption의 `adoption-policy: adopt`와 서비스에 맞는 adoption-fields를 사용합니다. feature gate·식별자·region·계정을 확인합니다. resource-imported:true는 이 설정이 아니며 adopt-or-create는 없으면 생성할 수 있습니다. 가져온 뒤 reconcile이 변경할 수 있으므로 읽기 전용 기능과 구분합니다.

</details>

## 6. GA 상태는 무엇을 보장하나요?

<details>
<summary>정답 보기</summary>

controller의 공식 제품 성숙도 단계입니다. 모든 AWS API나 사용자의 운영 요구를 지원한다는 뜻은 아닙니다. CRD의 v1alpha1 버전 문자열과 구분하고 서비스별 지원 필드·릴리스·운영 검증을 확인합니다.

</details>

## 7. 동기화를 나타내는 condition과 한계는 무엇인가요?

<details>
<summary>정답 보기</summary>

ACK.ResourceSynced=True입니다. controller의 동기화 상태이며 app readiness, DB 연결, 메시지 전달 성공과는 다릅니다. 다른 conditions와 AWS 서비스 상태도 확인합니다.

</details>

## 8. 팀별 namespace를 나누면 권한 격리가 끝나나요?

<details>
<summary>정답 보기</summary>

아닙니다. 기본 installScope=cluster이면 여러 namespace의 CR을 감시합니다. watchNamespace/installScope, ServiceAccount·IAM·RBAC와 cross-namespace/CARM 설정을 함께 제한합니다. namespace 모드도 namespace cache용 cluster 읽기 권한을 가질 수 있습니다.

</details>

## 9. 원하는 상태와 AWS 상태를 맞추는 패턴은 무엇인가요?

<details>
<summary>정답 보기</summary>

reconciliation loop입니다. 지원되는 필드와 controller 로직 범위에서 반복 처리하며 일시적 오류와 AWS quota 영향을 받을 수 있습니다. 모든 drift를 무조건 즉시 고치는 것은 아닙니다.

</details>

## 10. AWS 리소스 입력을 정의하는 Kubernetes 확장 방식은 무엇인가요?

<details>
<summary>정답 보기</summary>

CRD입니다. S3 예제는 Bucket.spec.policy를 사용합니다. 검토 버전에는 별도의 BucketPolicy 또는 IAM RolePolicyAttachment CRD가 없으므로 실제 kind와 schema를 확인합니다.

</details>

## 11. ARN은 어디에서 확인하나요?

<details>
<summary>정답 보기</summary>

해당 리소스에서 제공되면 status.ackResourceMetadata.arn에서 확인합니다. NLB와 TargetGroup에도 이 경로를 사용합니다. 모든 리소스가 동일한 추가 status 필드를 갖는 것은 아닙니다.

</details>

## 12. CARM과 여러 cluster의 리소스 참조는 어떤 차이가 있나요?

<details>
<summary>정답 보기</summary>

CARM은 controller가 다른 AWS 계정의 role을 가정해 관리하는 설정입니다. target role trust·AssumeRole·mapping과 controller 설정이 필요합니다. 여러 cluster가 같은 AWS 객체를 경쟁 수정해도 안전하다는 뜻이 아니며 변경 소유권과 읽기 전용 참조를 구분합니다.

</details>

## 13. Development 태그를 가진 S3 Bucket을 작성할 때 무엇을 포함하나요?

<details>
<summary>정답 보기</summary>

아래 예제처럼 전역 고유 이름, 실제 region, tagging.tagSet, Block Public Access 네 항목과 암호화를 포함합니다. ARN principal이 존재하고 IAM Role이 준비되어야 bucket policy를 적용할 수 있습니다. 예제의 이름·계정은 치환해야 합니다.

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: replace-with-globally-unique-bucket-name
  createBucketConfiguration:
    locationConstraint: us-west-2
  publicAccessBlock:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  encryption:
    rules:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  tagging:
    tagSet:
    - key: Environment
      value: Development
  policy: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"\
    Effect\": \"Allow\",\n      \"Principal\": {\n        \"AWS\": \"arn:aws:iam::123456789012:role/MyApplicationRole\"\
    \n      },\n      \"Action\": \"s3:GetObject\",\n      \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

</details>

## 14. ACK S3 chart를 검사하고 설치하기 위한 전제는 무엇인가요?

<details>
<summary>정답 보기</summary>

아래는 pin한 OCI chart의 오프라인 렌더링입니다. 실제 install/upgrade 전에는 infra namespace와 ServiceAccount, IRSA/Pod Identity·IAM 권한을 별도로 준비해야 합니다. template 성공을 AWS 설치 성공으로 해석하지 않습니다.

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.12.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

</details>

## 15. 문제 해결 시 어떤 상태와 로그를 확인하나요?

<details>
<summary>정답 보기</summary>

namespace와 fully qualified kind를 명시하고 conditions/events, controller image·로그, 실제 AWS 계정·region·권한과 참조를 확인합니다. 실제 chart label은 app.kubernetes.io/instance=ack-s3입니다. finalizer 제거를 일반 해결책으로 사용하지 않습니다.

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

</details>
