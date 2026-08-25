# MLflow를 EKS에 배포하기 퀴즈

이 퀴즈는 EKS에서 MLflow 트래킹 서버 아키텍처 — 백엔드 저장소, 아티팩트 저장소, IAM 접근 패턴, 그리고 트래킹 서버를 팀 공유 서비스로 운영할 때의 고려사항 — 에 대한 이해를 확인합니다.

## 객관식 문제

1. SageMaker의 MLflow 호환 트래킹 기능 같은 관리형 대안 대신 MLflow 트래킹 서버를 EKS에 자체 호스팅할 때 핵심 트레이드오프는 무엇입니까?
   - A) 팀 규모와 무관하게 자체 호스팅이 항상 더 저렴하다
   - B) 이미 EKS를 운영 중인 팀은 기존 배포·관측성·IAM 패턴을 재사용할 수 있지만, 트래킹 서버·백엔드 저장소·아티팩트 저장소를 직접 운영해야 한다
   - C) 관리형 대안은 메트릭이나 파라미터를 전혀 기록할 수 없다
   - D) 트레이드오프는 없으며 두 옵션은 기능적으로 동일하다

<details>

<summary>정답 보기</summary>

**정답: B) 이미 EKS를 운영 중인 팀은 기존 배포·관측성·IAM 패턴을 재사용할 수 있지만, 트래킹 서버·백엔드 저장소·아티팩트 저장소를 직접 운영해야 한다**

**설명:**
자체 호스팅은 다른 워크로드에 이미 쓰던 Kubernetes 배포, 관측성, IAM(IRSA/Pod Identity) 패턴을 그대로 재사용할 수 있게 해주지만, 그 대가로 트래킹 서버와 백엔드 데이터베이스, 아티팩트 저장소를 관리형 대안에 위임하지 않고 직접 운영해야 합니다.
</details>

2. MLflow의 기본 SQLite 백엔드 저장소가 팀이 공유하는 트래킹 서버에 적합하지 않은 이유는 무엇입니까?
   - A) SQLite는 부동소수점 메트릭 값을 저장할 수 없다
   - B) SQLite는 공유 트래킹 서버가 필요로 하는 수준의 동시 쓰기를 지원하지 않는다
   - C) SQLite는 별도의 EKS 노드 그룹이 필요하다
   - D) SQLite의 아티팩트는 30일 후 만료된다

<details>

<summary>정답 보기</summary>

**정답: B) SQLite는 공유 트래킹 서버가 필요로 하는 수준의 동시 쓰기를 지원하지 않는다**

**설명:**
SQLite는 혼자 실험할 때는 문제가 없지만, 둘 이상의 프로세스가 동시에 쓰려는 순간 한계가 드러납니다 — 팀이 공유하는 트래킹 서버가 필요로 하는 동시 쓰기 규모를 지원하지 않습니다. 그래서 프로덕션에서는 RDS PostgreSQL이나 Aurora Serverless v2 같은 실제 데이터베이스로 대체합니다.
</details>

3. 백엔드 저장소와 아티팩트 저장소는 각각 어떤 종류의 데이터를 담습니까?
   - A) 백엔드 저장소는 직렬화된 모델 같은 대용량 바이너리 객체를 담고, 아티팩트 저장소는 구조화된 메타데이터를 담는다
   - B) 백엔드 저장소는 구조화된 메타데이터(실험, Run, 파라미터, 메트릭, Registered Model, Version, alias)를 담고, 아티팩트 저장소는 대용량 바이너리 객체(모델, 플롯, 데이터셋)를 담는다
   - C) 두 저장소는 중복성을 위해 모든 데이터를 동일하게 복사해서 담는다
   - D) 백엔드 저장소는 사용자명과 비밀번호만 담는다

<details>

<summary>정답 보기</summary>

**정답: B) 백엔드 저장소는 구조화된 메타데이터(실험, Run, 파라미터, 메트릭, Registered Model, Version, alias)를 담고, 아티팩트 저장소는 대용량 바이너리 객체(모델, 플롯, 데이터셋)를 담는다**

**설명:**
백엔드 저장소는 SQL로 조회 가능한 모든 것 — 실험, Run, 파라미터, 메트릭, Registered Model, Version, alias — 을 담는 관계형 데이터베이스입니다. 아티팩트 저장소(AWS에서는 S3)는 백엔드 저장소가 담지 않는 대용량 바이너리 객체, 즉 기록된 모델, 플롯, 데이터셋을 담습니다.
</details>

4. AWS에서 MLflow 백엔드 저장소로 프로덕션에 표준적으로 쓰이는 두 서비스는 무엇입니까?
   - A) DynamoDB와 EFS
   - B) Amazon RDS for PostgreSQL과 Aurora Serverless v2
   - C) ElastiCache와 S3
   - D) Redshift와 Glacier

<details>

<summary>정답 보기</summary>

**정답: B) Amazon RDS for PostgreSQL과 Aurora Serverless v2**

**설명:**
둘 다 동시 쓰기를 지원하는 실제 관계형 데이터베이스입니다. Aurora Serverless v2는 특히 고려할 만한데, 연중 최대 부하에 맞춰 미리 크기를 정해 두지 않고도 순간적으로 몰리는 트래킹 부하를 흡수하며 스케일할 수 있기 때문입니다.
</details>

5. Kubernetes에 MLflow를 배포하기 위해 언급된 커뮤니티 Helm 차트는 무엇이며, 저장소는 어떻게 추가합니까?
   - A) `bitnami/mlflow`, `helm repo add bitnami https://charts.bitnami.com/bitnami`로 추가
   - B) `community-charts/mlflow`, `helm repo add community-charts https://community-charts.github.io/helm-charts`로 추가
   - C) MLflow를 위해 관리되는 커뮤니티 차트는 존재하지 않는다
   - D) `mlflow/mlflow-operator`, `kubectl apply -f`로만 설치

<details>

<summary>정답 보기</summary>

**정답: B) `community-charts/mlflow`, `helm repo add community-charts https://community-charts.github.io/helm-charts`로 추가**

**설명:**
`community-charts/helm-charts`는 백엔드 데이터베이스와 오브젝트 스토리지 설정을 구성할 수 있는 MLflow 차트를 유지 관리하며, Deployment/Service/Ingress 매니페스트를 직접 작성하는 대신 쓸 수 있는 실질적인 대안을 제공합니다.
</details>

6. 새로 배포하는 트래킹 서버의 ServiceAccount에 IAM 역할을 연결할 때, 더 현대적인 기본 선택으로 제시된 EKS 메커니즘은 무엇입니까?
   - A) ConfigMap에 저장된 정적 IAM 액세스 키
   - B) EKS Pod Identity이며, 이미 IRSA로 표준화된 클러스터에서는 IRSA도 여전히 유효한 선택이다
   - C) 워커 노드 EC2 인스턴스에 직접 연결된 인스턴스 프로파일
   - D) 컨테이너 이미지에 박아넣은 공유 루트 AWS 계정 자격 증명

<details>

<summary>정답 보기</summary>

**정답: B) EKS Pod Identity이며, 이미 IRSA로 표준화된 클러스터에서는 IRSA도 여전히 유효한 선택이다**

**설명:**
EKS Pod Identity는 IAM 역할을 Pod에 연결하는 더 새로운 메커니즘이며, 워크로드 종류와 무관하게 EKS에서 새로운 IAM-Pod 연결을 구성할 때 점점 더 기본으로 권장되고 있습니다. IRSA는 특히 이미 그 방식으로 표준화된 팀이나 클러스터에서는 여전히 유효한 선택입니다.
</details>

7. Postgres 기반 MLflow 트래킹 서버는 여러 replica를 안전하게 운영할 수 있는 반면, SQLite 기반 기본 구성은 전혀 스케일 아웃할 수 없는 이유는 무엇입니까?
   - A) Postgres replica는 Pod 간 인메모리 상태를 자동으로 동기화한다
   - B) Postgres와 S3를 백엔드로 쓰면 모든 공유 상태가 Pod 밖에 있어 트래킹 서버가 무상태가 되지만, SQLite는 동시 쓰기를 견디지 못한다
   - C) SQLite는 Postgres보다 CPU를 더 많이 소모하므로 스케일 아웃이 낭비다
   - D) Kubernetes는 데이터베이스를 사용하는 Deployment의 replica를 2개 이상 실행하는 것을 금지한다

<details>

<summary>정답 보기</summary>

**정답: B) Postgres와 S3를 백엔드로 쓰면 모든 공유 상태가 Pod 밖에 있어 트래킹 서버가 무상태가 되지만, SQLite는 동시 쓰기를 견디지 못한다**

**설명:**
지속적인 상태가 모두 Pod가 아니라 백엔드 저장소와 아티팩트 저장소에 있기 때문에, Postgres 기반 트래킹 서버는 무상태이며 수평 확장이 안전합니다. SQLite는 동시 쓰기를 지원하지 않으므로 단일 프로세스 기본 구성은 애초에 스케일 아웃이 안전하지 않습니다.
</details>

8. 모델이 Registered Model Version이나 alias를 갖게 된 이후 자연스러운 다음 단계로 언급된 것은 무엇이며, 왜 이 시리즈의 범위 밖입니까?
   - A) 학습 작업을 다시 실행하는 것; Part 1에서 학습을 이미 다뤘으므로 범위 밖이다
   - B) 그 모델 버전을 서빙 시스템(KServe, 직접 만든 래퍼, SageMaker 등)에 로드하는 것; 서빙 인프라 자체가 별도의 넓은 주제이므로 범위 밖이다
   - C) 모델 버전을 삭제하는 것; MLflow가 삭제를 지원하지 않으므로 범위 밖이다
   - D) 백엔드 저장소를 DynamoDB로 마이그레이션하는 것; DynamoDB가 지원되지 않으므로 범위 밖이다

<details>

<summary>정답 보기</summary>

**정답: B) 그 모델 버전을 서빙 시스템(KServe, 직접 만든 래퍼, SageMaker 등)에 로드하는 것; 서빙 인프라 자체가 별도의 넓은 주제이므로 범위 밖이다**

**설명:**
모델이 Registered Version이나 alias를 갖게 되면, 많은 팀이 다음으로 KServe, 직접 만든 FastAPI/Flask 래퍼, SageMaker 같은 서빙 시스템에 그것을 로드합니다. 서빙 계층은 그 자체로 넓은 주제이며 이 3부작 시리즈의 범위에서 명시적으로 제외됩니다.
</details>

## 서술형 문제

9. MLflow가 EKS에서 팀 공유 서비스로 동작하기 위해 배포되어야 하는 세 가지 핵심 아키텍처 구성 요소의 이름을 말하고, 각각이 무엇을 저장하거나 어떤 역할을 하는지 간단히 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
- MLflow 트래킹 서버: `mlflow server`를 실행하는 무상태 컨테이너로, REST API와 UI를 노출한다.
- 백엔드 저장소: 구조화된 메타데이터 — 실험, Run, 파라미터, 메트릭, Registered Model, Version, alias — 를 담는 관계형 데이터베이스(예: RDS PostgreSQL, Aurora Serverless v2).
- 아티팩트 저장소: 기록된 모델, 플롯, 데이터셋 같은 대용량 바이너리 객체를 담는 오브젝트 스토리지(AWS에서는 S3).

**설명:**
한 명 이상이 트래킹 서버를 공유하는 순간부터 셋 다 선택이 아니라 필수입니다. 트래킹 서버는 구조화된 메타데이터와 대용량 아티팩트 모두를 안정적으로 쓸 곳이 필요하며, 둘 다 트래킹 서버 Pod 자체에 있어서는 안 됩니다.
</details>

10. 트래킹 서버 Deployment에 readiness/liveness 프로브가 중요한 이유를 설명하고, 이 문서가 정확한 헬스 체크 엔드포인트 경로를 명시하지 않은 이유를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
readiness/liveness 프로브는 Service가 실제로 요청을 처리할 수 있는 Pod에만 트래픽을 보내도록 하고, 응답이 멈춘 Pod를 Kubernetes가 자동으로 재시작하도록 해줍니다 — 오래 실행되는 모든 Kubernetes 서비스에 적용되는 표준 관행입니다. 이 문서가 정확한 헬스 체크 경로를 명시하지 않은 이유는 MLflow 버전에 따라 달라질 수 있기 때문이며, 임의로 가정하지 말고 실제로 배포하는 버전에서 확인해야 합니다.

**설명:**
가상의 경로나 버전이 맞지 않는 경로에 프로브를 걸면 정상 Pod를 준비되지 않음으로 표시하거나, 실제로 멈춘 Pod를 잡아내지 못할 수 있습니다. 그래서 사용 중인 MLflow 버전의 실제 경로를 확인하는 것이 더 안전합니다.
</details>

---

[학습 자료로 돌아가기](../../../ai-ml/mlflow/03-eks-deployment.md)
