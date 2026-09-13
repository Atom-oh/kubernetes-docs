# 인프라 구성 기초 퀴즈

> **관련 문서**: [인프라 구성 기초](../../ops/01-infrastructure-setup.md)

## 객관식 문제

### 1. 이 문서의 3개 운영 레이어는 무엇인가요?

- A) Network → Cluster → Platform
- B) Foundation → Workload → Database
- C) VPC → Pod → Container
- D) 모든 자원을 한 state에서 관리

<details>
<summary>정답 보기</summary>

**정답: A) Network → Cluster → Platform**

00-shared는 별도의 bootstrap입니다. Network는 VPC, Cluster는 EKS, Platform은 CoreDNS·Pod Identity·팀 접근 권한 등을 관리합니다. state를 나눠도 VPC나 DNS 장애의 영향이 다른 레이어로 전파될 수 있습니다.

</details>

### 2. Terraform 1.10 이상 S3 backend의 네이티브 잠금을 켜는 설정은?

- A) use_lockfile = true
- B) 항상 DynamoDB 테이블 생성
- C) bucket versioning만 활성화
- D) 각 레이어에 같은 key 지정

<details>
<summary>정답 보기</summary>

**정답: A) use_lockfile = true**

S3 conditional write 기반 잠금입니다. DynamoDB 잠금은 기존 구성과 전환을 위한 방식이며 신규 네이티브 S3 잠금에 필수는 아닙니다. 잠금 방식 변경만으로 state 저장 위치를 이동하는 것은 아닙니다.

</details>

### 3. terraform_remote_state의 보안 경계에 대한 설명으로 옳은 것은?

- A) output 외에는 state를 읽을 수 없다
- B) state 접근 권한이 있으면 전체 snapshot에 접근할 수 있으므로 신뢰 경계를 고려한다
- C) sensitive=true가 IAM 읽기 권한을 차단한다
- D) state에는 민감한 값이 들어가지 않는다

<details>
<summary>정답 보기</summary>

**정답: B) state 접근 권한이 있으면 전체 snapshot에 접근할 수 있으므로 신뢰 경계를 고려한다**

표현식은 root output을 제공하지만 backend에서 읽는 state 자체에는 더 많은 정보가 있습니다. 다른 신뢰 경계에는 필요한 값만 별도 게시하는 방식을 검토합니다.

</details>

### 4. 일반 리전 EKS 클러스터와 기본 Auto Mode pool의 AZ 배치에 대한 설명은?

- A) 컨트롤 플레인 subnet을 한 AZ만 지정해도 된다
- B) blue라는 이름이면 워커가 자동으로 AZ-a에 고정된다
- C) EKS subnet은 서로 다른 두 AZ 이상이 필요하며 워커 AZ 고정은 별도 설정이다
- D) Subnet에 Cluster=blue 태그만 있으면 노드 배치가 고정된다

<details>
<summary>정답 보기</summary>

**정답: C) EKS subnet은 서로 다른 두 AZ 이상이 필요하며 워커 AZ 고정은 별도 설정이다**

기본 pool은 구성된 여러 AZ를 사용할 수 있습니다. 워커가 단일 AZ인 셀을 원하면 NodePool/NodeClass 요구 사항과 장애 시 다른 셀의 수용 용량을 별도로 설계합니다.

</details>

### 5. compute_config.node_pools에 gpu라는 기본 pool을 추가하면 어떻게 되나요?

- A) 공식 기본 GPU pool이 생긴다
- B) gpu는 기본 pool 이름이 아니며 GPU 요구에 맞는 custom NodePool을 구성해야 한다
- C) 기존 노드가 즉시 GPU 인스턴스로 바뀐다
- D) 모든 cluster가 GPU 전용이 된다

<details>
<summary>정답 보기</summary>

**정답: B) gpu는 기본 pool 이름이 아니며 GPU 요구에 맞는 custom NodePool을 구성해야 한다**

기본 pool 이름은 general-purpose와 system입니다. 이 모듈 입력은 이름 목록이며 임의 GPU pool 정의 map이 아닙니다. custom NodePool은 이 가이드의 GitOps 영역입니다.

</details>

### 6. EKS Pod Identity의 올바른 용도와 조건은?

- A) Pod의 ECR 이미지 pull을 자동 해결한다
- B) OIDC provider가 반드시 필요하다
- C) 지원 SDK의 AWS API 호출에 역할 자격 증명을 제공하며 association·신뢰 정책·노드 지원이 필요하다
- D) association이 ServiceAccount와 ESO를 자동 설치한다

<details>
<summary>정답 보기</summary>

**정답: C) 지원 SDK의 AWS API 호출에 역할 자격 증명을 제공하며 association·신뢰 정책·노드 지원이 필요하다**

Auto Mode는 agent 기능을 내장합니다. 일반 EKS 노드는 별도 agent가 필요할 수 있습니다. 같은 namespace/SA를 구성하고, kubelet의 이미지 pull 권한과 애플리케이션 SDK 권한을 구분합니다.

</details>

### 7. 환경과 클러스터 색상별 Terraform state를 분리하려면?

- A) TF_DATA_DIR만 바꾸면 같은 S3 key도 자동 분리된다
- B) 서로 다른 backend bucket/key를 선택하고 캐시 디렉터리도 해당 실행 범위에 맞춘다
- C) environment 변수만 바꾸면 prod backend가 dev로 이동한다
- D) S3 버전 관리를 끈다

<details>
<summary>정답 보기</summary>

**정답: B) 서로 다른 backend bucket/key를 선택하고 캐시 디렉터리도 해당 실행 범위에 맞춘다**

실제 state 위치는 backend 설정으로 결정됩니다. TF_DATA_DIR는 초기화 메타데이터·모듈·Provider 캐시의 혼동을 줄이며 state key를 대신하지 않습니다. bootstrap local state도 계정·환경별로 분리합니다.

</details>

### 8. 이 Auto Mode 예제의 CoreDNS와 StorageClass에 대한 설명은?

- A) 둘 다 아무 설정 없이 항상 자동 생성된다
- B) 순수 Auto Mode는 node-local DNS, 혼합 노드는 CoreDNS Deployment 유지, StorageClass는 별도 생성
- C) 일반 EBS CSI와 Pod Identity agent를 무조건 중복 설치한다
- D) CoreDNS 버전은 latest 문자열로 고정한다

<details>
<summary>정답 보기</summary>

**정답: B) 순수 Auto Mode는 node-local DNS, 혼합 노드는 CoreDNS Deployment 유지, StorageClass는 별도 생성**

순수 Auto Mode는 노드 시스템 서비스의 CoreDNS를 사용합니다. 일반 노드가 섞여 있으면 Deployment를 유지하고 Kubernetes 버전·리전에 맞는 add-on 버전을 고정합니다. Auto Mode StorageClass의 provisioner는 ebs.csi.eks.amazonaws.com입니다.

</details>

### 9. 관리자 access entry를 만들면 kubectl 접근이 무조건 완성되나요?

- A) IAM DescribeCluster와 네트워크 경로까지 자동 허용된다
- B) 아니다. 해당 principal로 인증하고 IAM 권한·private API 접근 경로도 준비해야 한다
- C) Terraform 실행자는 항상 자동 관리자가 된다
- D) 같은 principal을 Platform layer에서 다시 만들어야 한다

<details>
<summary>정답 보기</summary>

**정답: B) 아니다. 해당 principal로 인증하고 IAM 권한·private API 접근 경로도 준비해야 한다**

이 예제는 Terraform 실행자 자동 관리자 권한을 끕니다. EKS access policy는 Kubernetes 권한이며 IAM 권한과 다릅니다. 동일 principal의 access entry는 한 레이어에서 소유합니다.

</details>

### 10. 올바른 smoke-test 실패 처리는?

- A) Pod 생성 오류를 || true로 숨긴다
- B) 항상 smoke-test라는 기존 namespace를 지운다
- C) 실패를 nonzero로 반환하고 자신이 만든 임시 namespace만 확인 후 정리한다
- D) Running phase인 모든 파드를 무조건 정상으로 본다

<details>
<summary>정답 보기</summary>

**정답: C) 실패를 nonzero로 반환하고 자신이 만든 임시 namespace만 확인 후 정리한다**

이 예제는 workload scheduling과 cluster DNS를 확인합니다. 외부 LB나 모든 애플리케이션 의존성까지 검증한 것은 아닙니다. 컨테이너 READY 개수와 Pod Ready 조건도 구분합니다.

</details>
