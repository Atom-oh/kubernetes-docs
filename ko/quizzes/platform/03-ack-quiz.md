# AWS Controllers for Kubernetes (ACK) 퀴즈

이 퀴즈는 AWS Controllers for Kubernetes (ACK)의 개념, 아키텍처, 설치, 보안 및 운영에 대한 이해도를 테스트합니다.

## 객관식 문제

1. ACK(AWS Controllers for Kubernetes)의 주요 목적은 무엇인가요?
   - A) AWS 리소스를 AWS 콘솔에서만 관리
   - B) Kubernetes API를 통해 AWS 리소스를 선언적으로 관리
   - C) Kubernetes 클러스터를 AWS에서만 실행
   - D) AWS 비용을 자동으로 절감

<details>

<summary>정답 보기</summary>

**정답: B) Kubernetes API를 통해 AWS 리소스를 선언적으로 관리**

**설명:**
ACK는 Kubernetes 사용자가 익숙한 Kubernetes API와 도구(kubectl, Helm 등)를 사용하여 AWS 서비스와 리소스를 직접 관리할 수 있게 해주는 프로젝트입니다. 이를 통해 GitOps 워크플로우와 통합하고, 선언적 구성을 통해 AWS 인프라를 코드로 관리할 수 있습니다.
</details>

2. ACK 아키텍처에서 각 AWS 서비스에 대해 개별적으로 설치되는 구성 요소는 무엇인가요?
   - A) Kubernetes API Server
   - B) 서비스 컨트롤러
   - C) etcd 데이터베이스
   - D) kubelet

<details>

<summary>정답 보기</summary>

**정답: B) 서비스 컨트롤러**

**설명:**
ACK는 각 AWS 서비스(S3, RDS, DynamoDB 등)에 대해 별도의 서비스 컨트롤러를 제공합니다. 예를 들어 S3 버킷을 관리하려면 S3 컨트롤러를 설치하고, RDS 데이터베이스를 관리하려면 RDS 컨트롤러를 설치해야 합니다. 이러한 모듈식 접근 방식을 통해 필요한 서비스에 대해서만 컨트롤러를 설치할 수 있습니다.
</details>

3. ACK 컨트롤러가 AWS 리소스를 관리하기 위해 권장되는 IAM 권한 설정 방법은 무엇인가요?
   - A) EC2 인스턴스 프로필만 사용
   - B) AWS 액세스 키를 ConfigMap에 저장
   - C) IRSA(IAM Roles for Service Accounts) 사용
   - D) 모든 AWS 권한을 가진 루트 계정 사용

<details>

<summary>정답 보기</summary>

**정답: C) IRSA(IAM Roles for Service Accounts) 사용**

**설명:**
IRSA(IAM Roles for Service Accounts)는 Kubernetes 서비스 계정에 IAM 역할을 연결하는 방법으로, ACK 컨트롤러에 AWS 리소스 관리 권한을 부여하는 권장 방법입니다. 이 방식은 최소 권한 원칙을 따르며, 자격 증명을 안전하게 관리할 수 있고, 각 컨트롤러에 필요한 권한만 부여할 수 있습니다.
</details>

4. ACK에서 Kubernetes 리소스를 삭제할 때 AWS 리소스를 삭제하지 않고 유지하려면 어떤 annotation을 사용해야 하나요?
   - A) services.k8s.aws/keep-resource: "true"
   - B) services.k8s.aws/deletion-policy: "orphan"
   - C) services.k8s.aws/preserve: "true"
   - D) services.k8s.aws/no-delete: "true"

<details>

<summary>정답 보기</summary>

**정답: B) services.k8s.aws/deletion-policy: "orphan"**

**설명:**
기본적으로 ACK는 Kubernetes 리소스를 삭제할 때 해당 AWS 리소스도 함께 삭제합니다. 그러나 `services.k8s.aws/deletion-policy: "orphan"` annotation을 설정하면 Kubernetes 리소스가 삭제되더라도 AWS 리소스는 유지됩니다. 이는 프로덕션 환경에서 실수로 중요한 리소스가 삭제되는 것을 방지하는 데 유용합니다.
</details>

5. ACK에서 기존에 AWS에 존재하는 리소스를 Kubernetes로 가져오는 방법은 무엇인가요?
   - A) kubectl import 명령어 사용
   - B) AWS 콘솔에서 내보내기 기능 사용
   - C) 리소스 매니페스트에 services.k8s.aws/resource-imported: "true" annotation 추가
   - D) ACK CLI의 import 명령어 사용

<details>

<summary>정답 보기</summary>

**정답: C) 리소스 매니페스트에 services.k8s.aws/resource-imported: "true" annotation 추가**

**설명:**
기존 AWS 리소스를 ACK로 가져오려면 해당 리소스의 매니페스트를 작성하고 `services.k8s.aws/resource-imported: "true"` annotation을 추가합니다. 이렇게 하면 ACK 컨트롤러가 새 리소스를 생성하는 대신 기존 AWS 리소스와 연결합니다. 이를 통해 기존 인프라를 GitOps 워크플로우로 점진적으로 마이그레이션할 수 있습니다.
</details>

6. ACK 서비스 컨트롤러의 성숙도 단계 중 프로덕션 사용에 적합한 단계는 무엇인가요?
   - A) Alpha
   - B) Beta
   - C) GA (Generally Available)
   - D) Preview

<details>

<summary>정답 보기</summary>

**정답: C) GA (Generally Available)**

**설명:**
ACK 서비스 컨트롤러는 Alpha, Beta, GA 세 가지 성숙도 단계를 거칩니다. Alpha는 초기 개발 단계로 API 변경이 있을 수 있고, Beta는 기능이 완성되었지만 여전히 API 변경 가능성이 있습니다. GA(Generally Available)는 프로덕션 사용 준비가 완료된 단계로, 안정적인 API와 완전한 기능을 제공합니다.
</details>

7. ACK 리소스의 상태가 성공적으로 동기화되었음을 나타내는 Condition 타입은 무엇인가요?
   - A) ACK.Ready
   - B) ACK.ResourceSynced
   - C) ACK.Healthy
   - D) ACK.Available

<details>

<summary>정답 보기</summary>

**정답: B) ACK.ResourceSynced**

**설명:**
ACK 리소스의 상태는 `status.conditions` 필드에서 확인할 수 있습니다. `ACK.ResourceSynced` Condition이 True이면 Kubernetes 리소스의 원하는 상태(spec)가 실제 AWS 리소스의 상태와 성공적으로 동기화되었음을 의미합니다. 이를 통해 리소스가 올바르게 생성되거나 업데이트되었는지 확인할 수 있습니다.
</details>

8. ACK에서 여러 팀이나 환경에 대해 권한을 격리하는 권장 방법은 무엇인가요?
   - A) 단일 컨트롤러에서 모든 환경 관리
   - B) 별도의 네임스페이스와 IAM 역할을 사용한 격리
   - C) AWS Organizations만 사용
   - D) VPC 격리만 사용

<details>

<summary>정답 보기</summary>

**정답: B) 별도의 네임스페이스와 IAM 역할을 사용한 격리**

**설명:**
ACK에서 여러 팀이나 환경(개발, 스테이징, 프로덕션)에 대해 권한을 격리하려면 각각에 대해 별도의 Kubernetes 네임스페이스와 IAM 역할을 사용하는 것이 권장됩니다. 각 네임스페이스에 대해 별도의 컨트롤러를 설치하고, 해당 환경에 적합한 IAM 정책을 가진 역할을 연결하면 됩니다. 또한 Kubernetes RBAC를 사용하여 사용자별 ACK 리소스 접근을 제어할 수 있습니다.
</details>

## 단답형 문제

9. ACK 컨트롤러가 AWS API를 호출하여 리소스를 생성, 업데이트, 삭제하는 과정에서 원하는 상태와 실제 상태 간의 차이를 감지하고 해결하는 패턴을 무엇이라고 하나요?

<details>

<summary>정답 보기</summary>

**정답: 조정 루프(Reconciliation Loop) 또는 조정 패턴(Reconciliation Pattern)**

**설명:**
조정 루프는 Kubernetes 컨트롤러의 핵심 패턴으로, ACK도 이 패턴을 기반으로 합니다. ACK 컨트롤러는 지속적으로 Kubernetes 리소스의 원하는 상태(spec)와 실제 AWS 리소스의 상태를 비교합니다. 차이가 감지되면 컨트롤러는 AWS API를 호출하여 실제 상태를 원하는 상태와 일치시킵니다. 이 과정은 자동으로 반복되어 드리프트를 감지하고 수정합니다.
</details>

10. ACK에서 AWS 리소스를 Kubernetes API로 정의하기 위해 사용하는 Kubernetes 확장 메커니즘은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: CRD(Custom Resource Definition) 또는 사용자 정의 리소스 정의**

**설명:**
ACK는 CRD(Custom Resource Definition)를 사용하여 AWS 리소스를 Kubernetes API로 정의합니다. 예를 들어, S3 컨트롤러를 설치하면 `Bucket`, `BucketPolicy` 등의 CRD가 생성되어 S3 버킷을 Kubernetes 리소스처럼 관리할 수 있게 됩니다. 각 서비스 컨트롤러는 해당 AWS 서비스의 리소스에 대한 CRD를 제공합니다.
</details>

11. ACK 리소스의 상태를 확인할 때 AWS 리소스의 ARN(Amazon Resource Name)은 어떤 필드에서 확인할 수 있나요?

<details>

<summary>정답 보기</summary>

**정답: status.ackResourceMetadata.arn**

**설명:**
ACK 리소스가 성공적으로 생성되면 해당 AWS 리소스의 ARN은 `status.ackResourceMetadata.arn` 필드에 저장됩니다. `kubectl describe` 명령으로 리소스 상태를 확인하면 이 정보를 볼 수 있습니다. 또한 `status.ackResourceMetadata.ownerAccountID` 필드에서 리소스를 소유한 AWS 계정 ID도 확인할 수 있습니다.
</details>

12. ACK에서 여러 클러스터에서 동일한 AWS 리소스를 참조하거나 다른 AWS 계정의 리소스를 관리하는 기능을 무엇이라고 하나요?

<details>

<summary>정답 보기</summary>

**정답: 크로스 계정 리소스 관리(Cross-Account Resource Management) 또는 멀티 클러스터 지원**

**설명:**
ACK는 여러 Kubernetes 클러스터에서 동일한 AWS 리소스를 참조하거나, 다른 AWS 계정의 리소스를 관리하는 기능을 제공합니다. 이를 위해 IAM 역할 체인이나 크로스 계정 IAM 정책을 설정하여 ACK 컨트롤러가 다른 계정의 리소스에 접근할 수 있도록 합니다. 이 기능은 멀티 클러스터 또는 멀티 계정 환경에서 중앙 집중식 리소스 관리를 가능하게 합니다.
</details>

## 실습 문제

13. ACK를 사용하여 S3 버킷을 생성하는 Kubernetes 매니페스트를 작성하세요. 버킷 이름은 "my-ack-demo-bucket-2025"이고, 태그로 Environment: Development를 추가하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-ack-demo-bucket
  namespace: default
spec:
  name: my-ack-demo-bucket-2025
  tagging:
    tagSet:
      - key: Environment
        value: Development
  createBucketConfiguration:
    locationConstraint: us-west-2
```

**설명:**
ACK S3 컨트롤러를 사용하여 S3 버킷을 생성하는 매니페스트입니다. `metadata.name`은 Kubernetes 리소스 이름이고, `spec.name`은 실제 AWS S3 버킷 이름입니다. 버킷 이름은 전역적으로 고유해야 하므로 실제 사용 시에는 고유한 이름을 지정해야 합니다. `tagging.tagSet`을 통해 AWS 리소스 태그를 설정할 수 있으며, `createBucketConfiguration.locationConstraint`로 버킷이 생성될 리전을 지정합니다.
</details>

14. ACK S3 컨트롤러를 Helm을 사용하여 설치하고, IRSA를 구성하는 명령어를 작성하세요. 클러스터 이름은 "my-eks-cluster", 네임스페이스는 "ack-system"을 사용하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. Helm 차트 저장소 추가
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts
helm repo update

# 2. IRSA를 위한 IAM 서비스 계정 생성
eksctl create iamserviceaccount \
  --cluster=my-eks-cluster \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve \
  --override-existing-serviceaccounts

# 3. S3 컨트롤러 설치
helm install ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --namespace ack-system \
  --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set aws.region=us-west-2
```

**설명:**
먼저 ACK Helm 차트 저장소를 추가합니다. 그 다음 eksctl을 사용하여 IRSA 설정을 위한 IAM 서비스 계정을 생성합니다. 이 서비스 계정에는 S3 관리에 필요한 IAM 정책이 연결됩니다. 마지막으로 Helm을 사용하여 S3 컨트롤러를 설치하며, 이미 생성된 서비스 계정을 사용하도록 설정합니다. 프로덕션 환경에서는 AmazonS3FullAccess 대신 최소 권한 원칙에 따른 커스텀 정책을 사용하는 것이 좋습니다.
</details>

15. ACK로 생성한 리소스의 문제를 해결하기 위해 컨트롤러 로그를 확인하고, 리소스 상태를 점검하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. ACK 컨트롤러 로그 확인
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller

# 2. 특정 리소스의 상태 및 이벤트 확인
kubectl describe bucket my-ack-demo-bucket

# 3. 리소스의 상세 상태 확인 (JSON 형식)
kubectl get bucket my-ack-demo-bucket -o json | jq '.status'

# 4. 리소스 관련 이벤트 확인
kubectl get events --field-selector involvedObject.name=my-ack-demo-bucket

# 5. CRD 설치 상태 확인
kubectl get crd | grep services.k8s.aws

# 6. 컨트롤러 배포 상태 확인
kubectl get deployment -n ack-system
```

**설명:**
ACK 리소스 생성에 문제가 있을 때, 먼저 컨트롤러 로그를 확인하여 AWS API 호출 오류나 권한 문제를 파악합니다. `kubectl describe`로 리소스 상태와 Conditions를 확인하고, 이벤트를 통해 최근 변경 사항을 추적합니다. CRD가 올바르게 설치되었는지, 컨트롤러 파드가 정상 실행 중인지도 확인해야 합니다. 일반적인 문제로는 IAM 권한 부족, 잘못된 리전 설정, 리소스 이름 충돌 등이 있습니다.
</details>

---

**점수 계산:**
- 13-15개 정답: 우수 (ACK 전문가 수준)
- 10-12개 정답: 양호 (실무 적용 가능)
- 7-9개 정답: 보통 (추가 학습 권장)
- 0-6개 정답: 미흡 (기본 개념 복습 필요)

[학습 자료로 돌아가기](../../platform/01-ack.md)
