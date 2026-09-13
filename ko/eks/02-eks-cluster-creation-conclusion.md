# EKS 클러스터 생성 - 결론 및 모범 사례

> **마지막 업데이트**: 2026년 9월 11일

## EKS 클러스터 생성 방법 비교

지금까지 다양한 방법으로 EKS 클러스터를 생성하는 방법을 살펴보았습니다. 각 방법의 장단점을 비교해 보겠습니다.

도구는 재현성·검토 가능성·팀 역량·수명 주기 소유권으로 선택합니다. 어떤 도구로 만든 클러스터도 워크로드·네트워크·보안 검증이 필요합니다. 리소스별 의도한 소유자를 하나로 정하고 plan/change set을 검토하며 수동 변경과 IaC 상태를 조정합니다.

### eksctl

**장점:**
- EKS 중심의 간결한 워크플로우; 소요 시간은 생성 리소스에 따라 다름
- 단일 명령어로 클러스터 생성 가능
- YAML 파일을 통한 선언적 구성 지원
- 노드 그룹, Fargate 프로필 등 다양한 기능 지원

**단점:**
- 복잡한 인프라 요구 사항에는 제한적일 수 있음
- 기존 인프라와의 통합이 어려울 수 있음

**적합한 사용 사례:**
- 빠른 프로토타이핑
- 개발 및 테스트 환경
- 구성·소유권·수명 주기를 검토한 프로덕션 환경

### AWS Management Console

**장점:**
- 시각적 인터페이스로 쉽게 이해 가능
- 단계별 가이드를 통한 클러스터 생성
- 다양한 옵션을 시각적으로 확인 가능

**단점:**
- 수동 프로세스로 자동화가 어려움
- 반복적인 작업에 시간이 많이 소요됨
- 구성 관리 및 버전 관리가 어려움

**적합한 사용 사례:**
- 학습 및 탐색
- 일회성 클러스터 생성
- 소규모 팀 또는 프로젝트

### AWS CLI

**장점:**
- 스크립트를 통한 자동화 가능
- 세밀한 제어 가능
- AWS 서비스와의 통합이 용이

**단점:**
- 복잡한 명령어 구조
- 여러 단계의 명령어 실행 필요
- 오류 처리가 어려울 수 있음

**적합한 사용 사례:**
- 자동화 스크립트의 일부
- CI/CD 파이프라인 통합
- 세밀한 제어가 필요한 환경

### Terraform

**장점:**
- 인프라를 코드로 관리(IaC)
- 상태 관리 및 변경 추적
- 다양한 AWS 서비스와의 통합
- 모듈화 및 재사용성

**단점:**
- 학습 곡선이 있음
- 초기 설정에 시간이 소요됨
- 상태의 보호·잠금·복구 설계 필요; 로컬 backend 자체에 추가 인프라가 필수는 아님

**적합한 사용 사례:**
- 대규모 프로덕션 환경
- 다중 환경 관리(개발, 스테이징, 프로덕션)
- 복잡한 인프라 요구 사항

### AWS CDK

**장점:**
- 익숙한 프로그래밍 언어 사용(TypeScript, Python 등)
- 높은 수준의 추상화
- 코드 재사용 및 모듈화
- AWS 서비스와의 긴밀한 통합

**단점:**
- 학습 곡선이 있음
- 디버깅이 복잡할 수 있음
- Construct·버전별 지원 범위가 다름; 합성된 CloudFormation과 custom resource 동작 검토 필요

**적합한 사용 사례:**
- 개발자 중심 환경
- 복잡한 애플리케이션 인프라
- 기존 애플리케이션 코드와의 통합

## EKS 클러스터 생성 모범 사례

### 네트워킹

1. **VPC 설계**
   - 최소 2개 이상의 가용 영역에 서브넷 배포
   - 실제 ingress/egress 요구에 따라 public/private 배치 선택; private-only 설계는 서비스 엔드포인트와 프라이빗 연결 사용 가능
   - 사용 가능 주소, CNI warm/prefix pool과 업그레이드 여유 계획; 서브넷 공간과 노드 ENI/maxPods 제한 구분
   - 선택한 컨트롤러의 서브넷 디스커버리 태그·구성 사용; 태그가 경로나 보안 경계를 만들지는 않음

2. **보안 그룹 구성**
   - 최소 권한 원칙 적용
   - 실제 API·kubelet·DNS·webhook·애플리케이션 경로 허용; kubelet은 임의의 광범위 임시 포트가 아닌 TCP 10250 사용
   - 소스 IP 제한
   - 보안 그룹 간 참조 활용

3. **네트워크 정책**
   - 지원 정책 엔진 선택: VPC CNI 네이티브 정책 또는 적절한 Calico/Cilium 설계; 충돌하는 엔진을 함께 활성화하지 않음
   - 포드 간 통신 제한
   - 네임스페이스 ingress/egress·DNS를 허용/거부 테스트로 검증; 일치하는 Kubernetes NetworkPolicy 허용은 합집합

### 보안

1. **IAM 역할 및 정책**
   - 최소 권한 원칙 적용
   - 컴퓨팅·agent/SDK·신뢰 요건에 맞춰 EKS Pod Identity 또는 IRSA 사용; 애플리케이션 권한 제한
   - 세분화된 권한 정책 구성

2. **암호화**
   - EBS 볼륨 암호화 활성화
   - EKS 기본 API 데이터 envelope encryption(1.28+ KMSv2)과 customer-managed KMS key 필요 여부 확인; base64는 암호화가 아님
   - 전송 중 데이터 암호화(TLS)

3. **인증 및 권한 부여**
   - EKS IAM 인증과 적절한 access entry/access policy 사용; AWS CLI 토큰 사용 시 클라이언트에 별도 aws-iam-authenticator 바이너리가 필수는 아님
   - Kubernetes RBAC와 EKS access-policy 권한을 함께 검토; 허용 권한은 합집합
   - 신원·네임스페이스를 분리하고 RBAC·Pod Security·네트워크 제어 적용; 네임스페이스만으로 완전한 테넌트 격리가 되지는 않음

### 확장성 및 가용성

1. **노드 그룹 구성**
   - 여러 가용 영역에 노드 배포
   - managed/self-managed node group, Karpenter, Auto Mode, Fargate 등 컴퓨팅 소유자 확인; 모든 모드를 운영자 관리 ASG로 가정하지 않음
   - 다양한 인스턴스 유형 활용(Spot 인스턴스 포함)

2. **클러스터 오토스케일러**
   - 필요한 경우 호환 Cluster Autoscaler/Karpenter 릴리스 사용; Auto Mode는 자체 용량 관리. 같은 pool의 소유자 충돌 방지
   - 워크로드 복제본 확장과 노드 프로비저닝 구분; requests·배치 불가 Pod·용량 제약 검증
   - 선택한 컨트롤러에서 disruption/consolidation 예산·시간 조정; 애플리케이션 드레인·복구 테스트

3. **고가용성 구성**
   - 다중 가용 영역 활용
   - 해당되는 자발적 eviction에 PodDisruptionBudget 사용; 노드 장애나 모든 강제 중단을 막지는 않음
   - 목표 장애 시나리오에 맞춰 복제본 수·topology spread·readiness·용량 설정

### 모니터링 및 로깅

1. **컨트롤 플레인 로깅**
   - 컨트롤 플레인 로그5종(api, audit, authenticator, controllerManager, scheduler)을 보존 기간·접근·비용 제어와 함께 검토
   - CloudWatch Logs와 통합

2. **노드 및 포드 모니터링**
   - 필요한 CloudWatch Container Insights/add-on 신호와 지원 컴퓨팅 구성 선택
   - Prometheus/Grafana 또는 기존 모니터링 플랫폼을 의도적으로 선택; 중복 수집·검토하지 않은 자동 계측 방지
   - 사용자 정의 메트릭 구성

3. **알림 및 경고**
   - CloudWatch 경보 구성
   - 승인된 알림 목적지와 전달·소유권 확인; 구독 확인 완료를 가정하지 않음
   - 중요 이벤트에 대한 알림 구성

### 비용 최적화

1. **인스턴스 유형 선택**
   - 워크로드에 적합한 인스턴스 유형 선택
   - 중단을 허용할 수 있는 워크로드에 Spot 사용; 용량·장애 처리 검증
   - 애플리케이션·이미지·agent·add-on의 아키텍처 호환성 검증 후 Graviton 고려

2. **오토스케일링**
   - 수요에 따른 자동 스케일링 구성
   - 스케일 다운 정책 최적화
   - 예약 스케일링 고려

3. **리소스 요청 및 제한**
   - 적절한 CPU 및 메모리 요청 설정
   - 워크로드 동작에 맞춰 제한 설정; 메모리 OOM·CPU throttling 영향을 고려
   - 리소스 쿼터 및 제한 범위 설정

4. **Fargate 활용**
   - 스케줄링·네트워킹·스토리지·권한 제약이 맞는 워크로드에 Fargate 사용
   - Fargate 프로필 최적화
   - 비용 대비 성능 평가

## 다음 단계

EKS 클러스터를 성공적으로 생성한 후에는 다음과 같은 단계를 고려해 볼 수 있습니다:

1. **클러스터 업그레이드 전략 수립**
   - Upstream Kubernetes 릴리스뿐 아니라 EKS 지원 목록과 정확한 add-on·client·node 호환성에 따라 업그레이드 계획
   - In-place와 클러스터 교체 전략 비교; 현재 EKS control-plane rollback은 조건부이며 애플리케이션 데이터를 복원하지 않음
   - 업그레이드 테스트 자동화

2. **재해 복구 계획**
   - RPO/RTO 정의 후 애플리케이션 데이터·구성·필요 키 백업; 스냅샷 생성뿐 아니라 일관성·복원 검증
   - 복제·DNS/failover·IAM/KMS·비용 전제를 명시하여 다중 리전 복구 선택
   - 장애 시나리오 테스트

3. **CI/CD 파이프라인 통합**
   - GitOps 워크플로우 구현
   - 자동화된 배포 파이프라인 구축
   - 테스트 및 검증 자동화

4. **추가 서비스 통합**
   - 선택한 컴퓨팅·ingress 경로에 필요한 AWS Load Balancer Controller; Auto Mode 관리 컨트롤러 중복 설치 방지
   - DNS 소유권·IAM 권한을 제한한 ExternalDNS
   - Kubernetes 인증서 발급이 필요한 경우 cert-manager; ALB ACM 인증서 관리는 별도 경로
   - 컴퓨팅 지원·프로비저닝 소유자에 맞는 EBS/EFS 스토리지; Auto Mode EBS·Fargate 경로는 일반 EC2 add-on과 다름

5. **보안 강화**
   - 취약점 스캐닝 구현
   - 컴플라이언스 모니터링
   - 보안 정책 자동화

EKS 클러스터 생성은 Kubernetes 여정의 시작일 뿐입니다. 지속적인 관리, 모니터링, 최적화를 통해 안정적이고 효율적인 Kubernetes 환경을 유지하는 것이 중요합니다.


## 검증 참고 자료

- [EKS networking requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Private EKS clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [API-data envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)
- [Access policy permissions](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Conditional cluster rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

구현과 로컬 검증 예제는 [생성 Part 4](02-eks-cluster-creation-part4.md), [Part 5](02-eks-cluster-creation-part5.md), [네트워킹 Part 2](03-eks-networking-part2.md)에 있습니다. 프로덕션 준비 여부는 해당 환경의 장애·복원 테스트로 확인해야 합니다.
