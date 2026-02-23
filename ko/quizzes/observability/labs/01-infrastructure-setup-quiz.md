# Observability 실습 Part 1: 인프라 구성 퀴즈

> **마지막 업데이트**: 2026년 2월 22일

이 퀴즈는 Observability 실습 Part 1의 인프라 구성에 대한 이해도를 테스트합니다.

---

1. EKS 멀티 클러스터 아키텍처에서 Managed Cluster와 Service Cluster의 역할 차이로 올바른 것은?
   - A) Managed Cluster는 워크로드를 실행하고, Service Cluster는 모니터링 도구만 실행한다
   - B) Managed Cluster는 중앙 집중식 관리 도구(ArgoCD, Grafana 등)를 호스팅하고, Service Cluster는 실제 애플리케이션 워크로드를 실행한다
   - C) 두 클러스터는 동일한 역할을 수행하며 고가용성을 위해 분리된다
   - D) Managed Cluster는 개발 환경이고, Service Cluster는 프로덕션 환경이다
<details>
<summary>정답 보기</summary>

**정답: B) Managed Cluster는 중앙 집중식 관리 도구(ArgoCD, Grafana 등)를 호스팅하고, Service Cluster는 실제 애플리케이션 워크로드를 실행한다**

**설명:**
멀티 클러스터 아키텍처에서 Managed Cluster는 ArgoCD, Grafana, Prometheus 등 중앙 집중식 관리 및 모니터링 도구를 호스팅합니다. Service Cluster는 실제 비즈니스 애플리케이션과 마이크로서비스를 실행합니다. 이러한 분리를 통해 관리 도구의 장애가 서비스에 영향을 주지 않고, 보안 경계를 명확히 할 수 있습니다.

</details>

---

2. IRSA (IAM Roles for Service Accounts)를 사용하는 주된 이유는?
   - A) EC2 인스턴스 프로파일보다 설정이 간단하기 때문
   - B) Pod 수준에서 세분화된 AWS 권한을 부여하고 자격 증명을 코드에 하드코딩하지 않기 위해
   - C) Kubernetes의 필수 요구 사항이기 때문
   - D) AWS 비용을 절감하기 위해
<details>
<summary>정답 보기</summary>

**정답: B) Pod 수준에서 세분화된 AWS 권한을 부여하고 자격 증명을 코드에 하드코딩하지 않기 위해**

**설명:**
IRSA는 Kubernetes Service Account에 IAM Role을 연결하여 Pod가 AWS 서비스에 안전하게 접근할 수 있게 합니다. 노드 수준의 IAM Role과 달리 Pod 수준에서 최소 권한 원칙을 적용할 수 있으며, AWS SDK가 자동으로 임시 자격 증명을 획득하므로 액세스 키를 코드나 환경 변수에 저장할 필요가 없습니다.

</details>

---

3. EKS 클러스터 프로비저닝 시 Terraform을 사용하는 것의 장점으로 올바르지 않은 것은?
   - A) 인프라를 코드로 관리하여 버전 관리와 코드 리뷰가 가능하다
   - B) 모듈화를 통해 재사용 가능한 인프라 컴포넌트를 만들 수 있다
   - C) eksctl보다 항상 빠르게 클러스터를 생성할 수 있다
   - D) 상태 파일을 통해 인프라 변경 사항을 추적하고 드리프트를 감지할 수 있다
<details>
<summary>정답 보기</summary>

**정답: C) eksctl보다 항상 빠르게 클러스터를 생성할 수 있다**

**설명:**
Terraform은 IaC(Infrastructure as Code), 모듈화, 상태 관리 등의 장점이 있지만, 클러스터 생성 속도는 eksctl과 비슷하거나 오히려 복잡한 설정으로 인해 더 느릴 수 있습니다. eksctl은 EKS에 최적화된 도구로 빠른 클러스터 생성에 특화되어 있습니다. Terraform의 진정한 가치는 속도가 아닌 인프라의 일관성, 재현성, 협업 효율성에 있습니다.

</details>

---

4. Aurora PostgreSQL에서 writer 인스턴스와 reader 인스턴스를 분리 구성하는 주된 이유는?
   - A) 비용 절감을 위해
   - B) 읽기 워크로드를 분산하여 writer의 부하를 줄이고 읽기 성능을 향상시키기 위해
   - C) AWS의 필수 요구 사항이기 때문
   - D) 데이터 암호화를 위해
<details>
<summary>정답 보기</summary>

**정답: B) 읽기 워크로드를 분산하여 writer의 부하를 줄이고 읽기 성능을 향상시키기 위해**

**설명:**
Aurora의 reader 인스턴스는 writer 인스턴스의 읽기 부하를 분산합니다. 마이크로서비스 환경에서는 읽기 작업이 쓰기보다 훨씬 많은 경우가 일반적이므로, reader 엔드포인트로 읽기 쿼리를 분산하면 writer 인스턴스가 쓰기 작업에 집중할 수 있어 전체 데이터베이스 성능이 향상됩니다. 또한 reader 인스턴스는 writer 장애 시 자동 failover 대상이 됩니다.

</details>

---

5. Amazon Managed Prometheus (AMP) 워크스페이스 생성 시 필수 구성 요소가 아닌 것은?
   - A) VPC 엔드포인트 (프라이빗 접근 시)
   - B) 워크스페이스 alias
   - C) Amazon S3 버킷
   - D) IAM 정책 (remote write 권한)
<details>
<summary>정답 보기</summary>

**정답: C) Amazon S3 버킷**

**설명:**
AMP 워크스페이스는 완전 관리형 서비스로 내부적으로 스토리지를 관리합니다. 사용자가 별도의 S3 버킷을 제공할 필요가 없습니다. 필수 구성 요소로는 워크스페이스 자체, remote write/query를 위한 IAM 정책, 그리고 프라이빗 접근이 필요한 경우 VPC 엔드포인트가 있습니다. 워크스페이스 alias는 선택 사항이지만 식별을 위해 권장됩니다.

</details>

---

6. Amazon Managed Grafana (AMG)에서 데이터소스를 연결하는 올바른 방식은?
   - A) 데이터소스 자격 증명을 Grafana UI에 직접 입력한다
   - B) AWS 데이터소스의 경우 서비스 관리형 권한을 사용하여 IAM 기반 인증을 설정한다
   - C) 모든 데이터소스는 퍼블릭 엔드포인트를 통해서만 접근 가능하다
   - D) 데이터소스 연결에 SSH 터널을 필수로 사용해야 한다
<details>
<summary>정답 보기</summary>

**정답: B) AWS 데이터소스의 경우 서비스 관리형 권한을 사용하여 IAM 기반 인증을 설정한다**

**설명:**
AMG는 AWS 서비스(AMP, CloudWatch, X-Ray 등)에 대해 서비스 관리형 권한을 지원합니다. 이를 통해 AMG가 자동으로 필요한 IAM 역할을 생성하고 데이터소스에 안전하게 접근할 수 있습니다. 자격 증명을 직접 입력하는 것보다 보안성이 높고 자격 증명 로테이션도 자동으로 처리됩니다.

</details>

---

7. ArgoCD에서 멀티 클러스터 등록 시 필요한 설정으로 올바른 것은?
   - A) 각 클러스터의 kubeconfig 파일을 ArgoCD 서버에 복사한다
   - B) `argocd cluster add` 명령으로 클러스터를 등록하고 ServiceAccount와 ClusterRoleBinding이 대상 클러스터에 생성된다
   - C) 모든 클러스터가 동일한 VPC에 있어야 한다
   - D) 클러스터 간 VPN 연결이 필수이다
<details>
<summary>정답 보기</summary>

**정답: B) `argocd cluster add` 명령으로 클러스터를 등록하고 ServiceAccount와 ClusterRoleBinding이 대상 클러스터에 생성된다**

**설명:**
ArgoCD 멀티 클러스터 등록 시 `argocd cluster add <context-name>` 명령을 사용합니다. 이 명령은 대상 클러스터에 argocd-manager ServiceAccount와 적절한 ClusterRoleBinding을 생성하여 ArgoCD가 해당 클러스터에 리소스를 배포할 수 있는 권한을 부여합니다. 클러스터는 네트워크 연결만 가능하면 되며 동일 VPC일 필요는 없습니다.

</details>

---

8. Amazon OpenSearch Service를 EKS와 연동할 때 권장되는 구성 방식은?
   - A) OpenSearch 도메인을 퍼블릭 액세스로 설정하고 IP 기반 접근 제어를 사용한다
   - B) VPC 내에 OpenSearch 도메인을 생성하고 Fine-grained access control과 IRSA를 통한 IAM 인증을 사용한다
   - C) 마스터 사용자 이름과 비밀번호를 환경 변수로 Pod에 전달한다
   - D) OpenSearch를 EKS 클러스터 내부에 직접 설치한다
<details>
<summary>정답 보기</summary>

**정답: B) VPC 내에 OpenSearch 도메인을 생성하고 Fine-grained access control과 IRSA를 통한 IAM 인증을 사용한다**

**설명:**
프로덕션 환경에서 OpenSearch는 VPC 내에 배치하여 네트워크 격리를 확보하고, Fine-grained access control을 활성화하여 세분화된 접근 제어를 적용합니다. IRSA를 사용하면 Pod가 IAM 역할을 통해 OpenSearch에 인증할 수 있어 자격 증명을 코드에 포함하지 않아도 됩니다. 퍼블릭 액세스나 하드코딩된 자격 증명은 보안 위험이 있습니다.

</details>

---

9. Amazon MWAA (Managed Workflows for Apache Airflow) 환경에서 S3 DAG 버킷의 역할은?
   - A) Airflow 로그만 저장한다
   - B) DAG 파일, plugins, requirements.txt 등 Airflow 코드와 의존성을 저장하고 MWAA가 이를 자동으로 동기화한다
   - C) 데이터 파이프라인의 입출력 데이터를 저장한다
   - D) Airflow 메타데이터 데이터베이스의 백업을 저장한다
<details>
<summary>정답 보기</summary>

**정답: B) DAG 파일, plugins, requirements.txt 등 Airflow 코드와 의존성을 저장하고 MWAA가 이를 자동으로 동기화한다**

**설명:**
MWAA의 S3 DAG 버킷은 Airflow 워크플로우 정의(DAG 파일), 커스텀 플러그인, Python 패키지 의존성(requirements.txt) 등을 저장합니다. MWAA는 이 버킷을 주기적으로 스캔하여 변경 사항을 자동으로 Airflow 환경에 반영합니다. 이를 통해 GitOps 방식으로 DAG를 관리할 수 있습니다.

</details>

---

10. Argo Rollouts를 Service Cluster가 아닌 Managed Cluster에 설치하는 이유로 올바른 것은?
    - A) Argo Rollouts는 Managed Cluster에서만 작동한다
    - B) 중앙 집중식 배포 관리를 위해 ArgoCD와 같은 클러스터에서 Rollouts 컨트롤러를 운영하고, Service Cluster에는 Rollout CRD만 배포한다
    - C) 라이선스 제한 때문이다
    - D) Service Cluster의 리소스를 절약하기 위해
<details>
<summary>정답 보기</summary>

**정답: B) 중앙 집중식 배포 관리를 위해 ArgoCD와 같은 클러스터에서 Rollouts 컨트롤러를 운영하고, Service Cluster에는 Rollout CRD만 배포한다**

**설명:**
Argo Rollouts 컨트롤러를 Managed Cluster에 설치하면 ArgoCD와 함께 중앙에서 모든 클러스터의 점진적 배포를 관리할 수 있습니다. Service Cluster에는 Rollout CRD(Custom Resource Definition)만 있으면 되고, 실제 컨트롤러 로직은 Managed Cluster에서 실행됩니다. 이 패턴은 운영 복잡성을 줄이고 일관된 배포 정책을 적용할 수 있게 합니다.

</details>
