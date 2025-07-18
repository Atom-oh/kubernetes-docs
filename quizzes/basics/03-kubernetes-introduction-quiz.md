# Kubernetes 소개 퀴즈

이 퀴즈는 Kubernetes의 기본 개념, 아키텍처, 주요 구성 요소 및 기능에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kubernetes의 이름은 그리스어로 어떤 의미를 가지고 있나요?
   - A) 선장
   - B) 조타수 또는 파일럿
   - C) 컨테이너
   - D) 관리자
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) 조타수 또는 파일럿**
   
   **설명:**
   Kubernetes(κυβερνήτης)는 그리스어로 '조타수' 또는 '파일럿'을 의미합니다. 이는 컨테이너화된 애플리케이션의 항해를 안내하는 역할을 상징합니다. K8s라는 약어는 'K'와 's' 사이에 8개의 문자가 있기 때문에 사용됩니다.
   </details>

2. Kubernetes 컨트롤 플레인의 구성 요소가 아닌 것은 무엇인가요?
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) kubelet**
   
   **설명:**
   kubelet은 각 노드에서 실행되는 에이전트로, 컨트롤 플레인의 구성 요소가 아닙니다. 컨트롤 플레인 구성 요소는 kube-apiserver, etcd, kube-scheduler, kube-controller-manager, cloud-controller-manager입니다. kubelet은 노드 구성 요소로, 파드 내 컨테이너가 실행되도록 관리합니다.
   </details>

3. Kubernetes에서 가장 작은 배포 단위는 무엇인가요?
   - A) 컨테이너
   - B) 파드(Pod)
   - C) 디플로이먼트(Deployment)
   - D) 서비스(Service)
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) 파드(Pod)**
   
   **설명:**
   파드(Pod)는 Kubernetes의 가장 작은 배포 단위로, 하나 이상의 컨테이너 그룹을 나타냅니다. 파드 내의 컨테이너는 스토리지와 네트워크를 공유하며, 항상 같은 노드에서 함께 스케줄링됩니다. 컨테이너는 파드 내에 포함되는 더 작은 단위이지만, Kubernetes에서 직접 관리하는 배포 단위는 아닙니다.
   </details>

4. 다음 중 Kubernetes 서비스 유형이 아닌 것은 무엇인가요?
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: D) ExternalProxy**
   
   **설명:**
   Kubernetes의 서비스 유형은 ClusterIP, NodePort, LoadBalancer, ExternalName이 있습니다. ExternalProxy는 존재하지 않는 서비스 유형입니다. ClusterIP는 클러스터 내부에서만 접근 가능한 서비스, NodePort는 각 노드의 IP와 특정 포트를 통해 외부에서 접근 가능한 서비스, LoadBalancer는 클라우드 제공자의 로드 밸런서를 사용하여 외부에서 접근 가능한 서비스, ExternalName은 외부 서비스에 대한 CNAME 레코드를 생성하는 서비스입니다.
   </details>

5. Kubernetes에서 파드의 복제본 수를 관리하는 리소스는 무엇인가요?
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) ReplicaSet**
   
   **설명:**
   ReplicaSet은 지정된 수의 파드 복제본이 항상 실행되도록 보장합니다. 파드가 실패하거나 삭제되면 ReplicaSet은 자동으로 대체 파드를 생성합니다. Service는 파드 집합에 대한 단일 엔드포인트와 로드 밸런싱을 제공하고, ConfigMap은 구성 데이터를 저장하며, Namespace는 리소스 그룹을 격리하는 방법을 제공합니다.
   </details>

6. Kubernetes에서 상태 유지가 필요한 애플리케이션을 위한 워크로드 리소스는 무엇인가요?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) StatefulSet**
   
   **설명:**
   StatefulSet은 상태 유지가 필요한 애플리케이션을 위한 워크로드 리소스입니다. 각 파드에 고유한 식별자를 부여하고, 안정적인 네트워크 식별자와 영구 스토리지를 제공합니다. 데이터베이스와 같이 상태를 유지해야 하는 애플리케이션에 적합합니다. Deployment는 상태가 없는 애플리케이션을 위한 것이고, DaemonSet은 모든 노드에서 파드의 복사본을 실행하도록 보장하며, Job은 일회성 작업을 실행합니다.
   </details>

7. Kubernetes에서 모든 노드에서 파드의 복사본을 실행하도록 보장하는 리소스는 무엇인가요?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) DaemonSet**
   
   **설명:**
   DaemonSet은 모든 노드(또는 특정 노드)에서 파드의 복사본을 실행하도록 보장합니다. 노드가 클러스터에 추가되면 파드가 자동으로 추가되고, 노드가 제거되면 파드도 제거됩니다. 로그 수집기, 모니터링 에이전트, 네트워크 플러그인과 같은 백그라운드 서비스를 실행하는 데 주로 사용됩니다.
   </details>

8. Kubernetes에서 일정에 따라 작업을 주기적으로 실행하는 리소스는 무엇인가요?
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: B) CronJob**
   
   **설명:**
   CronJob은 지정된 일정에 따라 Job을 주기적으로 실행합니다. 리눅스 크론 작업과 유사한 방식으로 작동하며, 백업, 보고서 생성, 이메일 전송 등의 정기적인 작업에 사용됩니다. Job은 일회성 작업을 실행하고, Deployment와 ReplicaSet은 지속적으로 실행되는 애플리케이션을 관리합니다.
   </details>

9. Kubernetes에서 클러스터 내에서 리소스 그룹을 격리하는 방법을 제공하는 것은 무엇인가요?
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap
   
   <details>
   <summary>정답 보기</summary>
   
   **정답: C) Namespace**
   
   **설명:**
   Namespace는 단일 클러스터 내에서 리소스 그룹을 격리하는 방법을 제공합니다. 이는 여러 팀이나 프로젝트가 동일한 클러스터를 사용할 때 유용합니다. Label은 객체에 연결된 키-값 쌍으로 객체를 식별하고 선택하는 데 사용되고, Annotation은 객체에 대한 비식별 메타데이터를 저장하는 키-값 쌍이며, ConfigMap은 구성 데이터를 저장합니다.
   </details>

10. Amazon EKS와 자체 관리형 Kubernetes의 주요 차이점이 아닌 것은 무엇인가요?
    - A) 컨트롤 플레인 관리
    - B) 기본 Kubernetes API
    - C) 고가용성 구성
    - D) 보안 패치 적용
    
    <details>
    <summary>정답 보기</summary>
    
    **정답: B) 기본 Kubernetes API**
    
    **설명:**
    Amazon EKS와 자체 관리형 Kubernetes 모두 동일한 표준 Kubernetes API를 사용합니다. 주요 차이점은 컨트롤 플레인 관리(EKS는 AWS에서 관리), 고가용성 구성(EKS는 기본 제공), 보안 패치 적용(EKS는 AWS에서 자동 적용) 등에 있습니다. EKS는 Kubernetes의 기본 기능을 모두 제공하면서도 AWS 서비스와의 통합과 관리 편의성을 추가로 제공합니다.
    </details>

## 단답형 문제

11. Kubernetes에서 모든 클러스터 데이터를 저장하는 일관성 있고 고가용성을 갖춘 키-값 저장소는 무엇인가요?

    <details>
    <summary>정답 보기</summary>
    
    **정답: etcd**
    
    **설명:**
    etcd는 모든 클러스터 데이터를 저장하는 일관성 있고 고가용성을 갖춘 키-값 저장소입니다. Kubernetes의 모든 객체 정보, 상태, 구성 등이 etcd에 저장됩니다. etcd는 분산 시스템으로 설계되어 있어 고가용성을 제공하며, 강한 일관성을 보장합니다.
    </details>

12. Kubernetes에서 새로 생성된 파드를 실행할 노드를 선택하는 컨트롤 플레인 구성 요소는 무엇인가요?

    <details>
    <summary>정답 보기</summary>
    
    **정답: kube-scheduler**
    
    **설명:**
    kube-scheduler는 새로 생성된 파드를 실행할 노드를 선택하는 컨트롤 플레인 구성 요소입니다. 스케줄링 과정은 필터링(파드를 실행할 수 있는 노드 식별)과 스코어링(적합한 노드에 점수 부여)으로 이루어지며, 최종적으로 최적의 노드에 파드를 할당합니다.
    </details>

13. Kubernetes에서 파드 내의 컨테이너에 마운트할 수 있는 디렉토리로, 파드가 삭제되면 함께 삭제되는 임시 볼륨 유형은 무엇인가요?

    <details>
    <summary>정답 보기</summary>
    
    **정답: emptyDir**
    
    **설명:**
    emptyDir은 빈 디렉토리로 시작하며, 파드가 삭제되면 함께 삭제되는 임시 볼륨 유형입니다. 파드 내의 컨테이너 간에 데이터를 공유하거나, 임시 데이터를 저장하는 데 사용됩니다. 파드가 노드에서 실행되는 동안에만 존재하며, 파드가 삭제되거나 노드에서 제거되면 emptyDir의 내용도 영구적으로 삭제됩니다.
    </details>

14. Kubernetes에서 키-값 쌍의 형태로 구성 데이터를 저장하는 API 객체는 무엇인가요?

    <details>
    <summary>정답 보기</summary>
    
    **정답: ConfigMap**
    
    **설명:**
    ConfigMap은 키-값 쌍의 형태로 구성 데이터를 저장하는 API 객체입니다. 파드는 환경 변수, 명령줄 인수 또는 구성 파일로 ConfigMap의 데이터를 사용할 수 있습니다. ConfigMap을 사용하면 애플리케이션 코드와 구성을 분리할 수 있어, 동일한 애플리케이션 코드를 다양한 환경에서 다른 구성으로 실행할 수 있습니다.
    </details>

15. Kubernetes에서 암호, 토큰, 키와 같은 민감한 정보를 저장하는 API 객체는 무엇인가요?

    <details>
    <summary>정답 보기</summary>
    
    **정답: Secret**
    
    **설명:**
    Secret은 암호, 토큰, 키와 같은 민감한 정보를 저장하는 API 객체입니다. ConfigMap과 유사하지만, 민감한 데이터를 위해 설계되었습니다. Secret은 base64로 인코딩되어 저장되며, 파드에 환경 변수나 볼륨으로 마운트할 수 있습니다. Kubernetes는 다양한 유형의 Secret(Opaque, TLS, Docker registry 등)을 지원합니다.
    </details>

## 실습 문제

16. 다음 요구사항을 충족하는 Kubernetes Deployment YAML 파일을 작성하세요:
    - 이름: nginx-deployment
    - 레이블: app=nginx
    - 복제본 수: 3
    - 컨테이너 이미지: nginx:1.21
    - 컨테이너 포트: 80
    - 리소스 요청: CPU 100m, 메모리 128Mi
    - 리소스 제한: CPU 200m, 메모리 256Mi

    <details>
    <summary>정답 보기</summary>
    
    **정답:**
    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: nginx-deployment
      labels:
        app: nginx
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: nginx
      template:
        metadata:
          labels:
            app: nginx
        spec:
          containers:
          - name: nginx
            image: nginx:1.21
            ports:
            - containerPort: 80
            resources:
              requests:
                cpu: 100m
                memory: 128Mi
              limits:
                cpu: 200m
                memory: 256Mi
    ```
    
    **설명:**
    이 YAML 파일은 nginx:1.21 이미지를 사용하는 3개의 복제본을 가진 Deployment를 정의합니다. 각 컨테이너는 포트 80을 노출하고, CPU 요청 100m, 메모리 요청 128Mi, CPU 제한 200m, 메모리 제한 256Mi의 리소스 제약을 가집니다. selector 필드는 Deployment가 관리할 파드를 식별하는 방법을 정의합니다.
    </details>

17. 다음 요구사항을 충족하는 Kubernetes Service YAML 파일을 작성하세요:
    - 이름: nginx-service
    - 유형: LoadBalancer
    - 포트: 80 (서비스 포트)
    - 타겟 포트: 80 (컨테이너 포트)
    - 셀렉터: app=nginx

    <details>
    <summary>정답 보기</summary>
    
    **정답:**
    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: nginx-service
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 80
      selector:
        app: nginx
    ```
    
    **설명:**
    이 YAML 파일은 LoadBalancer 유형의 Service를 정의합니다. 이 서비스는 app=nginx 레이블을 가진 파드를 대상으로 하며, 서비스의 포트 80을 파드의 포트 80에 매핑합니다. LoadBalancer 유형은 클라우드 제공자의 로드 밸런서를 사용하여 서비스를 외부에 노출합니다.
    </details>

18. 다음 요구사항을 충족하는 Kubernetes ConfigMap YAML 파일을 작성하세요:
    - 이름: app-config
    - 데이터:
      - DATABASE_URL: "mysql://user:password@mysql:3306/db"
      - API_KEY: "abcdef123456"
      - LOG_LEVEL: "INFO"

    <details>
    <summary>정답 보기</summary>
    
    **정답:**
    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: app-config
    data:
      DATABASE_URL: "mysql://user:password@mysql:3306/db"
      API_KEY: "abcdef123456"
      LOG_LEVEL: "INFO"
    ```
    
    **설명:**
    이 YAML 파일은 app-config라는 이름의 ConfigMap을 정의합니다. ConfigMap은 키-값 쌍의 형태로 구성 데이터를 저장하며, 여기서는 DATABASE_URL, API_KEY, LOG_LEVEL이라는 세 개의 키와 그에 해당하는 값을 포함합니다. 이 ConfigMap은 파드에 환경 변수나 볼륨으로 마운트하여 사용할 수 있습니다.
    </details>

## 심화 문제

19. Kubernetes의 RBAC(Role-Based Access Control) 시스템에 대해 설명하고, 특정 네임스페이스에서 파드를 조회하고 로그를 볼 수 있는 권한을 가진 Role과 이를 사용자에게 바인딩하는 RoleBinding YAML을 작성하세요.

    <details>
    <summary>정답 보기</summary>
    
    **정답:**
    
    RBAC(Role-Based Access Control)는 Kubernetes API에 대한 접근을 제어하는 메커니즘입니다. 역할(Role)과 역할 바인딩(RoleBinding)을 사용하여 사용자나 서비스 계정에 특정 권한을 부여합니다.
    
    RBAC의 주요 구성 요소:
    - **Role**: 네임스페이스 내에서 권한 집합을 정의
    - **ClusterRole**: 클러스터 전체에서 권한 집합을 정의
    - **RoleBinding**: 역할을 사용자, 그룹 또는 서비스 계정에 바인딩
    - **ClusterRoleBinding**: 클러스터 역할을 사용자, 그룹 또는 서비스 계정에 바인딩
    
    특정 네임스페이스에서 파드를 조회하고 로그를 볼 수 있는 Role:
    ```yaml
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
      namespace: development
      name: pod-reader
    rules:
    - apiGroups: [""]
      resources: ["pods", "pods/log"]
      verbs: ["get", "watch", "list"]
    ```
    
    이 Role을 사용자에게 바인딩하는 RoleBinding:
    ```yaml
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: read-pods
      namespace: development
    subjects:
    - kind: User
      name: jane
      apiGroup: rbac.authorization.k8s.io
    roleRef:
      kind: Role
      name: pod-reader
      apiGroup: rbac.authorization.k8s.io
    ```
    
    이 YAML 파일들은 development 네임스페이스에서 파드를 조회하고 로그를 볼 수 있는 pod-reader라는 역할을 정의하고, 이 역할을 jane이라는 사용자에게 바인딩합니다. 이제 jane은 development 네임스페이스에서 파드 목록을 조회하고 로그를 볼 수 있지만, 파드를 생성, 수정 또는 삭제할 수는 없습니다.
    </details>

20. Kubernetes의 네트워크 정책(NetworkPolicy)에 대해 설명하고, 특정 네임스페이스의 데이터베이스 파드가 같은 네임스페이스의 백엔드 파드로부터만 트래픽을 받을 수 있도록 하는 NetworkPolicy YAML을 작성하세요.

    <details>
    <summary>정답 보기</summary>
    
    **정답:**
    
    네트워크 정책(NetworkPolicy)은 파드 간의 통신을 제어하는 방법을 제공합니다. 기본적으로 모든 파드는 서로 통신할 수 있지만, 네트워크 정책을 사용하면 이를 제한할 수 있습니다.
    
    네트워크 정책의 주요 기능:
    - 파드 간 통신 제어
    - 네임스페이스 간 통신 제어
    - 인그레스(수신) 및 이그레스(송신) 트래픽 제어
    - 포트 및 프로토콜 기반 필터링
    
    특정 네임스페이스의 데이터베이스 파드가 같은 네임스페이스의 백엔드 파드로부터만 트래픽을 받을 수 있도록 하는 NetworkPolicy:
    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: db-network-policy
      namespace: production
    spec:
      podSelector:
        matchLabels:
          role: database
      policyTypes:
      - Ingress
      ingress:
      - from:
        - podSelector:
            matchLabels:
              role: backend
        ports:
        - protocol: TCP
          port: 3306
    ```
    
    이 NetworkPolicy는 production 네임스페이스에서 role=database 레이블을 가진 파드에 적용됩니다. 이 정책은 같은 네임스페이스에서 role=backend 레이블을 가진 파드로부터의 TCP 포트 3306(MySQL 기본 포트)으로의 인그레스 트래픽만 허용합니다. 다른 모든 인그레스 트래픽은 차단됩니다. 이그레스 트래픽은 이 정책에 의해 제한되지 않습니다.
    </details>

---

[학습 자료로 돌아가기](../../basics/03-kubernetes-introduction.md) | [다음 퀴즈: 클러스터 아키텍처](../core/01-cluster-architecture-quiz.md)
