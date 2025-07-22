# Amazon EKS 업그레이드 퀴즈

이 퀴즈는 Amazon EKS 클러스터 업그레이드 프로세스, 모범 사례, 문제 해결 및 관련 고려 사항에 대한 이해를 테스트합니다.

## 퀴즈 개요
- EKS 클러스터 업그레이드 계획
- 컨트롤 플레인 업그레이드
- 노드 그룹 업그레이드
- 애드온 및 구성 요소 업그레이드
- 업그레이드 테스트 및 검증
- 업그레이드 문제 해결

## 객관식 문제

### 1. Amazon EKS 클러스터 업그레이드를 계획할 때 가장 중요한 첫 번째 단계는 무엇인가요?

A. 즉시 컨트롤 플레인 업그레이드 수행  
B. 모든 워크로드를 한 번에 업그레이드  
C. 업그레이드 호환성 검토 및 테스트 계획 수립  
D. 모든 노드 그룹 동시 업그레이드  

<details>
<summary>정답 및 설명</summary>

**정답: C. 업그레이드 호환성 검토 및 테스트 계획 수립**

**설명:**
Amazon EKS 클러스터 업그레이드를 계획할 때 가장 중요한 첫 번째 단계는 업그레이드 호환성을 검토하고 테스트 계획을 수립하는 것입니다. 이 단계는 업그레이드 과정에서 발생할 수 있는 문제를 미리 식별하고, 워크로드 중단을 최소화하며, 성공적인 업그레이드를 위한 기반을 마련합니다.

**업그레이드 호환성 검토 및 테스트 계획의 주요 구성 요소:**

1. **버전 호환성 검토**:
   - Kubernetes 버전 간 API 변경 사항 확인
   - 사용 중인 API 버전 및 기능의 지원 여부 검토
   - 더 이상 사용되지 않거나 제거된 API 식별

2. **워크로드 호환성 평가**:
   - 애플리케이션 매니페스트의 API 버전 검토
   - 사용 중인 컨트롤러 및 운영자 호환성 확인
   - 커스텀 리소스 정의(CRD) 및 웹훅 호환성 검토

3. **애드온 및 도구 호환성 확인**:
   - CNI, CoreDNS, kube-proxy 버전 호환성
   - 인그레스 컨트롤러, 서비스 메시 등의 호환성
   - 모니터링, 로깅, 백업 도구 호환성

4. **테스트 계획 수립**:
   - 비프로덕션 환경에서의 업그레이드 테스트
   - 주요 워크로드 기능 테스트 계획
   - 롤백 절차 및 기준 정의

**구현 방법:**

1. **업그레이드 경로 및 호환성 검토**:
   ```bash
   # 현재 EKS 클러스터 버전 확인
   aws eks describe-cluster --name my-cluster --query "cluster.version"
   
   # 사용 가능한 EKS 버전 확인
   aws eks describe-addon-versions --kubernetes-version 1.28
   
   # 더 이상 사용되지 않는 API 확인
   kubectl get --raw /metrics | grep "deprecated_api_requests_total"
   
   # 사용 중인 API 버전 검토
   kubectl get deployment,statefulset,daemonset,cronjob,job -A -o json | jq '.items[].apiVersion' | sort | uniq
   ```

2. **워크로드 호환성 검사 도구 사용**:
   ```bash
   # pluto를 사용하여 더 이상 사용되지 않는 API 버전 검사
   pluto detect-helm --output wide
   pluto detect-kubectl --output wide
   
   # kube-no-trouble 사용
   kubectl-no-trouble
   ```

3. **테스트 클러스터 생성 및 업그레이드 테스트**:
   ```bash
   # 테스트 클러스터 생성
   eksctl create cluster \
     --name test-upgrade \
     --version 1.27 \
     --region us-west-2 \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes 2
   
   # 테스트 클러스터 업그레이드
   eksctl upgrade cluster \
     --name test-upgrade \
     --version 1.28 \
     --approve
   ```

4. **업그레이드 계획 문서 작성**:
   ```markdown
   # EKS 클러스터 업그레이드 계획
   
   ## 현재 상태
   - 클러스터 버전: 1.27
   - 노드 그룹: 3개 (시스템: 1.27, 앱: 1.27, 배치: 1.27)
   - 주요 애드온: AWS VPC CNI 1.12.0, CoreDNS 1.8.7, kube-proxy 1.27.1
   
   ## 대상 상태
   - 클러스터 버전: 1.28
   - 노드 그룹: 3개 (시스템: 1.28, 앱: 1.28, 배치: 1.28)
   - 주요 애드온: AWS VPC CNI 1.13.0, CoreDNS 1.9.3, kube-proxy 1.28.1
   
   ## 호환성 검토 결과
   - 더 이상 사용되지 않는 API: batch/v1beta1 CronJob -> batch/v1 CronJob
   - 애드온 호환성: 모두 호환됨
   - 커스텀 리소스: 업데이트 필요 없음
   
   ## 업그레이드 단계
   1. 비프로덕션 환경 업그레이드 및 테스트
   2. 컨트롤 플레인 업그레이드
   3. 애드온 업그레이드
   4. 노드 그룹 순차적 업그레이드
   5. 검증 및 모니터링
   
   ## 롤백 계획
   - 롤백 기준: 중요 워크로드 장애 발생 시
   - 롤백 절차: 새 노드 그룹 생성 (이전 버전), 워크로드 마이그레이션
   ```

**업그레이드 호환성 검토 주요 영역:**

1. **API 변경 사항**:
   - Kubernetes 1.22: 많은 베타 API가 제거됨
   - Kubernetes 1.25: PodSecurityPolicy 제거
   - Kubernetes 1.26: HorizontalPodAutoscaler v2beta2 제거
   - Kubernetes 1.27: FlowSchema 및 PriorityLevelConfiguration API 변경
   - Kubernetes 1.28: 일부 베타 API 제거 및 변경

2. **노드 구성 요소 호환성**:
   - kubelet 버전은 컨트롤 플레인보다 최대 2개 마이너 버전 이전까지 지원
   - kube-proxy는 컨트롤 플레인과 동일한 버전으로 유지 권장
   - 컨테이너 런타임 호환성 확인

3. **애드온 호환성**:
   - CNI 플러그인 버전 호환성
   - CoreDNS 버전 호환성
   - 인그레스 컨트롤러, 서비스 메시 등의 호환성

**테스트 계획 수립 모범 사례:**

1. **단계적 테스트 접근 방식**:
   - 개발 환경 먼저 업그레이드
   - 스테이징 환경에서 전체 테스트 수행
   - 프로덕션 환경 업그레이드 전 최종 검증

2. **주요 워크로드 기능 테스트**:
   - 핵심 비즈니스 기능 테스트
   - 성능 및 확장성 테스트
   - 장애 복구 테스트

3. **모니터링 및 알림 강화**:
   - 업그레이드 중 추가 모니터링 구성
   - 주요 메트릭 및 로그 모니터링
   - 신속한 대응을 위한 알림 설정

4. **롤백 절차 정의**:
   - 명확한 롤백 기준 설정
   - 롤백 절차 문서화 및 테스트
   - 데이터 일관성 보장 방안 마련

**실제 구현 예시:**

1. **업그레이드 호환성 검토 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 클러스터 업그레이드 호환성 검토 스크립트
   
   CLUSTER_NAME="my-cluster"
   TARGET_VERSION="1.28"
   
   echo "=== EKS 클러스터 업그레이드 호환성 검토 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "대상 버전: $TARGET_VERSION"
   echo
   
   # 현재 클러스터 버전 확인
   CURRENT_VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.version" --output text)
   echo "현재 클러스터 버전: $CURRENT_VERSION"
   
   # 애드온 버전 확인
   echo
   echo "=== 현재 애드온 버전 ==="
   aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name vpc-cni --query "addon.addonVersion" --output text
   aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name coredns --query "addon.addonVersion" --output text
   aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name kube-proxy --query "addon.addonVersion" --output text
   
   echo
   echo "=== 대상 버전에서 사용 가능한 애드온 버전 ==="
   aws eks describe-addon-versions --kubernetes-version $TARGET_VERSION --query "addons[?addonName=='vpc-cni'].addonVersions[].addonVersion" --output text
   aws eks describe-addon-versions --kubernetes-version $TARGET_VERSION --query "addons[?addonName=='coredns'].addonVersions[].addonVersion" --output text
   aws eks describe-addon-versions --kubernetes-version $TARGET_VERSION --query "addons[?addonName=='kube-proxy'].addonVersions[].addonVersion" --output text
   
   # 더 이상 사용되지 않는 API 확인
   echo
   echo "=== 더 이상 사용되지 않는 API 사용 현황 ==="
   kubectl get --raw /metrics | grep "deprecated_api_requests_total" || echo "더 이상 사용되지 않는 API 요청이 없습니다."
   
   # 사용 중인 API 버전 검토
   echo
   echo "=== 사용 중인 API 버전 ==="
   kubectl get deployment,statefulset,daemonset,cronjob,job -A -o json | jq '.items[].apiVersion' | sort | uniq
   
   echo
   echo "=== 업그레이드 호환성 검토 완료 ==="
   ```

2. **업그레이드 테스트 계획 템플릿**:
   ```markdown
   # EKS 클러스터 업그레이드 테스트 계획
   
   ## 테스트 환경
   - 클러스터 이름: test-upgrade
   - 현재 버전: 1.27
   - 대상 버전: 1.28
   
   ## 테스트 범위
   
   ### 인프라 테스트
   - [ ] 컨트롤 플레인 업그레이드 성공
   - [ ] 노드 그룹 업그레이드 성공
   - [ ] 애드온 업그레이드 성공
   - [ ] 클러스터 상태 확인
   
   ### 워크로드 테스트
   - [ ] 배포 생성 및 확장
   - [ ] 스테이트풀셋 기능
   - [ ] 인그레스 및 서비스 기능
   - [ ] 크론잡 및 잡 실행
   - [ ] 커스텀 리소스 생성 및 관리
   
   ### 성능 테스트
   - [ ] 노드 리소스 사용량
   - [ ] 파드 시작 시간
   - [ ] API 서버 응답 시간
   - [ ] 네트워크 성능
   
   ### 장애 복구 테스트
   - [ ] 노드 장애 시 파드 재스케줄링
   - [ ] 네트워크 중단 시 동작
   - [ ] 리소스 압박 상황에서의 동작
   
   ## 테스트 결과 및 관찰 사항
   
   ## 결론 및 권장 사항
   ```

다른 옵션들의 문제점:
- **A. 즉시 컨트롤 플레인 업그레이드 수행**: 호환성 검토 및 테스트 없이 바로 업그레이드를 수행하면 예상치 못한 문제가 발생할 수 있으며, 워크로드 중단 위험이 높아집니다.
- **B. 모든 워크로드를 한 번에 업그레이드**: 이는 위험한 접근 방식으로, 문제 발생 시 전체 시스템에 영향을 미칠 수 있습니다. 단계적 접근이 더 안전합니다.
- **D. 모든 노드 그룹 동시 업그레이드**: 모든 노드를 동시에 업그레이드하면 전체 워크로드가 중단될 위험이 있으며, 문제 발생 시 롤백이 어려워집니다.
</details>
### 2. Amazon EKS 클러스터의 컨트롤 플레인을 업그레이드할 때 가장 올바른 접근 방식은 무엇인가요?

A. 노드 그룹을 먼저 업그레이드한 후 컨트롤 플레인 업그레이드  
B. 컨트롤 플레인을 업그레이드한 후 노드 그룹 업그레이드  
C. 컨트롤 플레인과 노드 그룹을 동시에 업그레이드  
D. 업그레이드 없이 새 클러스터를 생성하고 워크로드 마이그레이션  

<details>
<summary>정답 및 설명</summary>

**정답: B. 컨트롤 플레인을 업그레이드한 후 노드 그룹 업그레이드**

**설명:**
Amazon EKS 클러스터의 컨트롤 플레인을 업그레이드할 때 가장 올바른 접근 방식은 컨트롤 플레인을 먼저 업그레이드한 후 노드 그룹을 업그레이드하는 것입니다. 이 접근 방식은 Kubernetes의 버전 호환성 모델을 따르며, 업그레이드 과정에서 발생할 수 있는 문제를 최소화합니다.

**컨트롤 플레인 먼저 업그레이드하는 이유:**

1. **Kubernetes 버전 호환성 모델**:
   - 컨트롤 플레인은 노드보다 최대 2개 마이너 버전까지 앞설 수 있음
   - 노드는 컨트롤 플레인보다 앞설 수 없음
   - 이 모델은 하위 호환성을 보장하기 위함

2. **API 서버 호환성**:
   - 새 버전의 API 서버는 이전 버전의 kubelet과 통신 가능
   - 반대로 새 버전의 kubelet은 이전 버전의 API 서버와 호환성 문제 발생 가능

3. **점진적 업그레이드 가능**:
   - 컨트롤 플레인 업그레이드 후 노드 그룹을 점진적으로 업그레이드 가능
   - 문제 발생 시 영향 범위 제한 및 롤백 용이

**구현 방법:**

1. **컨트롤 플레인 업그레이드**:
   ```bash
   # AWS CLI를 사용한 컨트롤 플레인 업그레이드
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.28
   
   # 업그레이드 상태 확인
   aws eks describe-update \
     --name my-cluster \
     --update-id <update-id>
   ```

   ```bash
   # eksctl을 사용한 컨트롤 플레인 업그레이드
   eksctl upgrade cluster \
     --name my-cluster \
     --version 1.28 \
     --approve
   ```

2. **컨트롤 플레인 업그레이드 완료 확인**:
   ```bash
   # 클러스터 버전 확인
   aws eks describe-cluster \
     --name my-cluster \
     --query "cluster.version" \
     --output text
   
   # 클러스터 상태 확인
   kubectl get componentstatuses
   kubectl get nodes
   ```

3. **노드 그룹 업그레이드 준비**:
   ```bash
   # 현재 노드 그룹 확인
   aws eks list-nodegroups \
     --cluster-name my-cluster
   
   # 노드 그룹 버전 확인
   aws eks describe-nodegroup \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup \
     --query "nodegroup.version" \
     --output text
   ```

**컨트롤 플레인 업그레이드 프로세스:**

1. **업그레이드 전 준비**:
   - 클러스터 상태 확인
   - 백업 수행
   - 중요 워크로드 확인

2. **업그레이드 시작**:
   - AWS Management Console, AWS CLI 또는 eksctl 사용
   - 업그레이드 진행 상황 모니터링

3. **업그레이드 중 모니터링**:
   - 컨트롤 플레인 엔드포인트 가용성
   - 시스템 워크로드 상태
   - 로그 및 이벤트 모니터링

4. **업그레이드 완료 후 검증**:
   - 컨트롤 플레인 구성 요소 상태 확인
   - API 서버 기능 테스트
   - 시스템 워크로드 정상 작동 확인

**컨트롤 플레인 업그레이드 시 고려 사항:**

1. **업그레이드 시간**:
   - 일반적으로 20-30분 소요
   - 클러스터 크기 및 복잡성에 따라 다름
   - 유지 관리 기간 중 수행 권장

2. **업그레이드 중 API 서버 가용성**:
   - 업그레이드 중 일시적인 API 서버 중단 가능
   - 기존 워크로드는 계속 실행됨
   - 새로운 배포 및 구성 변경은 지연될 수 있음

3. **업그레이드 실패 시 대응**:
   - AWS 지원팀에 문의
   - 클러스터 상태 및 로그 수집
   - 대체 계획 실행

**모범 사례:**

1. **업그레이드 전 클러스터 상태 확인**:
   ```bash
   # 클러스터 상태 확인
   kubectl get nodes
   kubectl get pods --all-namespaces
   kubectl get componentstatuses
   
   # 이벤트 확인
   kubectl get events --all-namespaces --sort-by='.lastTimestamp'
   
   # 리소스 사용량 확인
   kubectl top nodes
   kubectl top pods --all-namespaces
   ```

2. **업그레이드 전 etcd 백업**:
   ```bash
   # etcd 백업 (자체 관리 클러스터의 경우)
   ETCDCTL_API=3 etcdctl snapshot save snapshot.db
   
   # EKS의 경우 주요 리소스 백업
   kubectl get all --all-namespaces -o yaml > all-resources.yaml
   ```

3. **점진적 노드 그룹 업그레이드 계획**:
   ```bash
   # 노드 그룹 업그레이드 계획
   # 1. 중요도가 낮은 노드 그룹부터 시작
   # 2. 한 번에 하나의 노드 그룹만 업그레이드
   # 3. 각 노드 그룹 업그레이드 후 검증
   ```

4. **업그레이드 후 시스템 구성 요소 확인**:
   ```bash
   # 시스템 파드 상태 확인
   kubectl get pods -n kube-system
   
   # CoreDNS 상태 확인
   kubectl get pods -n kube-system -l k8s-app=kube-dns
   
   # CNI 플러그인 상태 확인
   kubectl get pods -n kube-system -l k8s-app=aws-node
   ```

**실제 구현 예시:**

1. **컨트롤 플레인 업그레이드 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 컨트롤 플레인 업그레이드 스크립트
   
   CLUSTER_NAME="my-cluster"
   TARGET_VERSION="1.28"
   
   echo "=== EKS 클러스터 컨트롤 플레인 업그레이드 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "대상 버전: $TARGET_VERSION"
   echo
   
   # 현재 클러스터 버전 확인
   CURRENT_VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.version" --output text)
   echo "현재 클러스터 버전: $CURRENT_VERSION"
   
   # 클러스터 상태 확인
   echo
   echo "=== 클러스터 상태 확인 ==="
   kubectl get nodes
   kubectl get pods --all-namespaces | grep -v "Running\|Completed"
   
   # 사용자 확인
   echo
   read -p "클러스터 업그레이드를 시작하시겠습니까? (y/n): " confirm
   if [[ $confirm != "y" ]]; then
     echo "업그레이드가 취소되었습니다."
     exit 1
   fi
   
   # 업그레이드 시작
   echo
   echo "=== 컨트롤 플레인 업그레이드 시작 ==="
   UPDATE_ID=$(aws eks update-cluster-version \
     --name $CLUSTER_NAME \
     --kubernetes-version $TARGET_VERSION \
     --query "update.id" \
     --output text)
   
   echo "업그레이드 ID: $UPDATE_ID"
   
   # 업그레이드 상태 모니터링
   echo
   echo "=== 업그레이드 상태 모니터링 ==="
   
   STATUS="InProgress"
   while [ "$STATUS" == "InProgress" ]; do
     echo "업그레이드 진행 중... $(date)"
     sleep 60
     STATUS=$(aws eks describe-update \
       --name $CLUSTER_NAME \
       --update-id $UPDATE_ID \
       --query "update.status" \
       --output text)
   done
   
   echo
   echo "업그레이드 상태: $STATUS"
   
   if [ "$STATUS" == "Successful" ]; then
     echo
     echo "=== 컨트롤 플레인 업그레이드 완료 ==="
     echo "새 버전: $(aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.version" --output text)"
     
     echo
     echo "=== 클러스터 상태 확인 ==="
     kubectl get nodes
     kubectl get pods -n kube-system
   else
     echo
     echo "=== 업그레이드 실패 ==="
     aws eks describe-update \
       --name $CLUSTER_NAME \
       --update-id $UPDATE_ID
   fi
   ```

2. **Terraform을 사용한 EKS 클러스터 버전 관리**:
   ```hcl
   # EKS 클러스터 정의
   resource "aws_eks_cluster" "main" {
     name     = "my-cluster"
     role_arn = aws_iam_role.eks_cluster.arn
     version  = "1.28"  # 대상 버전 지정
     
     vpc_config {
       subnet_ids         = var.subnet_ids
       security_group_ids = [aws_security_group.eks_cluster.id]
     }
     
     # 버전 업그레이드 시 새 버전이 적용될 때까지 대기
     lifecycle {
       ignore_changes = []
     }
     
     depends_on = [
       aws_iam_role_policy_attachment.eks_cluster_policy
     ]
   }
   ```

3. **업그레이드 후 검증 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 클러스터 업그레이드 후 검증 스크립트
   
   CLUSTER_NAME="my-cluster"
   
   echo "=== EKS 클러스터 업그레이드 검증 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo
   
   # 클러스터 버전 확인
   CLUSTER_VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.version" --output text)
   echo "클러스터 버전: $CLUSTER_VERSION"
   
   # 컨트롤 플레인 상태 확인
   echo
   echo "=== 컨트롤 플레인 상태 ==="
   kubectl get componentstatuses
   
   # 시스템 파드 상태 확인
   echo
   echo "=== 시스템 파드 상태 ==="
   kubectl get pods -n kube-system
   
   # 노드 상태 확인
   echo
   echo "=== 노드 상태 ==="
   kubectl get nodes
   
   # API 서버 기능 테스트
   echo
   echo "=== API 서버 기능 테스트 ==="
   kubectl create namespace test-upgrade
   kubectl run nginx --image=nginx -n test-upgrade
   kubectl get pods -n test-upgrade
   kubectl delete namespace test-upgrade
   
   echo
   echo "=== 검증 완료 ==="
   ```

다른 옵션들의 문제점:
- **A. 노드 그룹을 먼저 업그레이드한 후 컨트롤 플레인 업그레이드**: 이는 Kubernetes 버전 호환성 모델에 위배되며, 노드의 kubelet 버전이 API 서버 버전보다 앞서게 되어 호환성 문제가 발생할 수 있습니다.
- **C. 컨트롤 플레인과 노드 그룹을 동시에 업그레이드**: 동시 업그레이드는 위험하며, 문제 발생 시 전체 클러스터에 영향을 미칠 수 있습니다. 또한 점진적인 검증이 어렵습니다.
- **D. 업그레이드 없이 새 클러스터를 생성하고 워크로드 마이그레이션**: 이 방법은 가능하지만, 리소스 중복, 복잡한 마이그레이션 절차, 추가 비용 등의 문제가 있어 일반적인 업그레이드에는 권장되지 않습니다.
</details>
### 3. Amazon EKS 노드 그룹을 업그레이드하는 가장 안전하고 효과적인 방법은 무엇인가요?

A. 모든 노드를 동시에 종료하고 새 버전으로 교체  
B. 관리형 노드 그룹 업그레이드 또는 블루/그린 배포 전략 사용  
C. 노드 그룹 업그레이드 없이 컨트롤 플레인만 업그레이드  
D. 수동으로 각 노드의 kubelet 버전 업그레이드  

<details>
<summary>정답 및 설명</summary>

**정답: B. 관리형 노드 그룹 업그레이드 또는 블루/그린 배포 전략 사용**

**설명:**
Amazon EKS 노드 그룹을 업그레이드하는 가장 안전하고 효과적인 방법은 관리형 노드 그룹 업그레이드 기능을 사용하거나 블루/그린 배포 전략을 구현하는 것입니다. 이러한 접근 방식은 워크로드 중단을 최소화하면서 노드를 안전하게 업그레이드할 수 있게 해줍니다.

**관리형 노드 그룹 업그레이드 및 블루/그린 배포의 주요 이점:**

1. **관리형 노드 그룹 업그레이드**:
   - AWS에서 관리하는 롤링 업그레이드 프로세스
   - 파드 중단 예산(PDB) 존중
   - 자동 드레이닝 및 코드온
   - 업그레이드 실패 시 자동 롤백

2. **블루/그린 배포 전략**:
   - 새 버전의 노드 그룹 생성
   - 워크로드 점진적 마이그레이션
   - 검증 후 이전 노드 그룹 제거
   - 문제 발생 시 빠른 롤백 가능

**구현 방법:**

1. **관리형 노드 그룹 업그레이드**:
   ```bash
   # AWS CLI를 사용한 관리형 노드 그룹 업그레이드
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup \
     --kubernetes-version 1.28
   
   # 업그레이드 상태 확인
   aws eks describe-update \
     --name my-cluster \
     --nodegroup-name my-nodegroup \
     --update-id <update-id>
   ```

   ```bash
   # eksctl을 사용한 관리형 노드 그룹 업그레이드
   eksctl upgrade nodegroup \
     --cluster my-cluster \
     --name my-nodegroup \
     --kubernetes-version 1.28
   ```

2. **블루/그린 배포 전략**:
   ```bash
   # 새 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name my-nodegroup-v2 \
     --node-type m5.large \
     --nodes 3 \
     --nodes-min 3 \
     --nodes-max 6 \
     --node-labels "kubernetes.io/role=worker,environment=production,version=v2" \
     --node-ami auto \
     --kubernetes-version 1.28
   
   # 워크로드 마이그레이션 (노드 선호도 사용)
   kubectl apply -f - <<EOF
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: my-app
   spec:
     replicas: 3
     template:
       spec:
         affinity:
           nodeAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               preference:
                 matchExpressions:
                 - key: version
                   operator: In
                   values:
                   - v2
   EOF
   
   # 이전 노드 그룹 제거
   eksctl delete nodegroup \
     --cluster my-cluster \
     --name my-nodegroup-v1
   ```

**노드 그룹 업그레이드 프로세스:**

1. **관리형 노드 그룹 업그레이드 프로세스**:
   - 최대 사용 불가능 노드 수 설정
   - 새 노드 생성 및 클러스터 조인
   - 기존 노드 드레이닝 및 종료
   - 모든 노드가 업그레이드될 때까지 반복

2. **블루/그린 배포 프로세스**:
   - 새 버전의 노드 그룹 생성
   - 새 노드 그룹에 테스트 워크로드 배포
   - 점진적으로 워크로드 마이그레이션
   - 모든 워크로드 마이그레이션 후 이전 노드 그룹 제거

**노드 그룹 업그레이드 시 고려 사항:**

1. **파드 중단 예산(PDB) 구성**:
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: app-pdb
   spec:
     minAvailable: 2  # 또는 maxUnavailable: 1
     selector:
       matchLabels:
         app: my-app
   ```

2. **노드 선호도 및 반선호도 설정**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: my-app
   spec:
     template:
       spec:
         affinity:
           podAntiAffinity:
             requiredDuringSchedulingIgnoredDuringExecution:
             - labelSelector:
                 matchExpressions:
                 - key: app
                   operator: In
                   values:
                   - my-app
               topologyKey: "kubernetes.io/hostname"
   ```

3. **테인트 및 톨러레이션 활용**:
   ```yaml
   # 새 노드 그룹에 테인트 적용
   eksctl create nodegroup \
     --cluster my-cluster \
     --name my-nodegroup-v2 \
     --node-labels "version=v2" \
     --taints "upgrade=v2:NoSchedule" \
     --kubernetes-version 1.28
   
   # 특정 워크로드에 톨러레이션 적용
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: my-app
   spec:
     template:
       spec:
         tolerations:
         - key: "upgrade"
           operator: "Equal"
           value: "v2"
           effect: "NoSchedule"
   ```

**모범 사례:**

1. **업그레이드 전 준비**:
   ```bash
   # 노드 상태 확인
   kubectl get nodes
   
   # 파드 분포 확인
   kubectl get pods -o wide --all-namespaces
   
   # 리소스 사용량 확인
   kubectl top nodes
   kubectl top pods --all-namespaces
   ```

2. **점진적 업그레이드**:
   - 한 번에 하나의 노드 그룹만 업그레이드
   - 중요도가 낮은 워크로드부터 시작
   - 각 단계 검증 후 진행

3. **업그레이드 중 모니터링 강화**:
   - 노드 상태 모니터링
   - 파드 이벤트 모니터링
   - 애플리케이션 성능 및 가용성 모니터링

4. **롤백 계획 수립**:
   - 명확한 롤백 기준 정의
   - 롤백 절차 문서화
   - 빠른 롤백을 위한 준비

**실제 구현 예시:**

1. **관리형 노드 그룹 업그레이드 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 관리형 노드 그룹 업그레이드 스크립트
   
   CLUSTER_NAME="my-cluster"
   NODEGROUP_NAME="my-nodegroup"
   TARGET_VERSION="1.28"
   
   echo "=== EKS 관리형 노드 그룹 업그레이드 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "노드 그룹: $NODEGROUP_NAME"
   echo "대상 버전: $TARGET_VERSION"
   echo
   
   # 현재 노드 그룹 버전 확인
   CURRENT_VERSION=$(aws eks describe-nodegroup \
     --cluster-name $CLUSTER_NAME \
     --nodegroup-name $NODEGROUP_NAME \
     --query "nodegroup.version" \
     --output text)
   echo "현재 노드 그룹 버전: $CURRENT_VERSION"
   
   # 노드 상태 확인
   echo
   echo "=== 노드 상태 확인 ==="
   kubectl get nodes -l eks.amazonaws.com/nodegroup=$NODEGROUP_NAME
   
   # 파드 분포 확인
   echo
   echo "=== 파드 분포 확인 ==="
   NODE_NAMES=$(kubectl get nodes -l eks.amazonaws.com/nodegroup=$NODEGROUP_NAME -o jsonpath='{.items[*].metadata.name}')
   for NODE in $NODE_NAMES; do
     echo "노드: $NODE"
     kubectl get pods --all-namespaces -o wide | grep $NODE | wc -l
   done
   
   # 사용자 확인
   echo
   read -p "노드 그룹 업그레이드를 시작하시겠습니까? (y/n): " confirm
   if [[ $confirm != "y" ]]; then
     echo "업그레이드가 취소되었습니다."
     exit 1
   fi
   
   # 업그레이드 시작
   echo
   echo "=== 노드 그룹 업그레이드 시작 ==="
   UPDATE_ID=$(aws eks update-nodegroup-version \
     --cluster-name $CLUSTER_NAME \
     --nodegroup-name $NODEGROUP_NAME \
     --kubernetes-version $TARGET_VERSION \
     --query "update.id" \
     --output text)
   
   echo "업그레이드 ID: $UPDATE_ID"
   
   # 업그레이드 상태 모니터링
   echo
   echo "=== 업그레이드 상태 모니터링 ==="
   
   STATUS="InProgress"
   while [ "$STATUS" == "InProgress" ]; do
     echo "업그레이드 진행 중... $(date)"
     sleep 60
     STATUS=$(aws eks describe-update \
       --name $CLUSTER_NAME \
       --nodegroup-name $NODEGROUP_NAME \
       --update-id $UPDATE_ID \
       --query "update.status" \
       --output text)
   done
   
   echo
   echo "업그레이드 상태: $STATUS"
   
   if [ "$STATUS" == "Successful" ]; then
     echo
     echo "=== 노드 그룹 업그레이드 완료 ==="
     echo "새 버전: $(aws eks describe-nodegroup \
       --cluster-name $CLUSTER_NAME \
       --nodegroup-name $NODEGROUP_NAME \
       --query "nodegroup.version" \
       --output text)"
     
     echo
     echo "=== 노드 상태 확인 ==="
     kubectl get nodes -l eks.amazonaws.com/nodegroup=$NODEGROUP_NAME
   else
     echo
     echo "=== 업그레이드 실패 ==="
     aws eks describe-update \
       --name $CLUSTER_NAME \
       --nodegroup-name $NODEGROUP_NAME \
       --update-id $UPDATE_ID
   fi
   ```

2. **블루/그린 배포 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 노드 그룹 블루/그린 업그레이드 스크립트
   
   CLUSTER_NAME="my-cluster"
   OLD_NODEGROUP="my-nodegroup-v1"
   NEW_NODEGROUP="my-nodegroup-v2"
   TARGET_VERSION="1.28"
   NODE_TYPE="m5.large"
   NODE_COUNT=3
   
   echo "=== EKS 노드 그룹 블루/그린 업그레이드 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "이전 노드 그룹: $OLD_NODEGROUP"
   echo "새 노드 그룹: $NEW_NODEGROUP"
   echo "대상 버전: $TARGET_VERSION"
   echo
   
   # 현재 노드 그룹 확인
   echo "=== 현재 노드 그룹 확인 ==="
   aws eks list-nodegroups --cluster-name $CLUSTER_NAME
   
   # 새 노드 그룹 생성
   echo
   echo "=== 새 노드 그룹 생성 ==="
   eksctl create nodegroup \
     --cluster $CLUSTER_NAME \
     --name $NEW_NODEGROUP \
     --node-type $NODE_TYPE \
     --nodes $NODE_COUNT \
     --nodes-min $NODE_COUNT \
     --nodes-max $(($NODE_COUNT * 2)) \
     --node-labels "kubernetes.io/role=worker,environment=production,version=v2" \
     --node-ami auto \
     --kubernetes-version $TARGET_VERSION
   
   # 새 노드 그룹 상태 확인
   echo
   echo "=== 새 노드 그룹 상태 확인 ==="
   kubectl get nodes -l eks.amazonaws.com/nodegroup=$NEW_NODEGROUP
   
   # 워크로드 마이그레이션
   echo
   echo "=== 워크로드 마이그레이션 ==="
   echo "1. 노드 선호도를 사용하여 새 노드 그룹으로 워크로드 마이그레이션"
   echo "2. 다음 명령으로 파드 분포 확인:"
   echo "   kubectl get pods -o wide --all-namespaces | grep <node-name>"
   
   # 사용자 확인
   echo
   read -p "모든 워크로드가 새 노드 그룹으로 마이그레이션되었습니까? (y/n): " confirm
   if [[ $confirm != "y" ]]; then
     echo "이전 노드 그룹 삭제가 취소되었습니다. 수동으로 마이그레이션을 완료하세요."
     exit 1
   fi
   
   # 이전 노드 그룹에 코드온 설정
   echo
   echo "=== 이전 노드 그룹에 코드온 설정 ==="
   kubectl cordon -l eks.amazonaws.com/nodegroup=$OLD_NODEGROUP
   
   # 이전 노드 그룹 드레이닝
   echo
   echo "=== 이전 노드 그룹 드레이닝 ==="
   kubectl drain --ignore-daemonsets --delete-emptydir-data -l eks.amazonaws.com/nodegroup=$OLD_NODEGROUP
   
   # 이전 노드 그룹 삭제
   echo
   echo "=== 이전 노드 그룹 삭제 ==="
   eksctl delete nodegroup \
     --cluster $CLUSTER_NAME \
     --name $OLD_NODEGROUP
   
   echo
   echo "=== 블루/그린 업그레이드 완료 ==="
   echo "현재 노드 그룹:"
   aws eks list-nodegroups --cluster-name $CLUSTER_NAME
   ```

3. **Terraform을 사용한 블루/그린 배포**:
   ```hcl
   # 현재 활성 노드 그룹 버전 변수
   variable "active_version" {
     description = "현재 활성 노드 그룹 버전 (blue 또는 green)"
     default     = "blue"
   }
   
   # 블루 노드 그룹
   resource "aws_eks_node_group" "blue" {
     cluster_name    = aws_eks_cluster.main.name
     node_group_name = "blue-nodegroup"
     node_role_arn   = aws_iam_role.node_role.arn
     subnet_ids      = var.private_subnet_ids
     
     scaling_config {
       desired_size = var.active_version == "blue" ? var.desired_nodes : 0
       min_size     = var.active_version == "blue" ? var.min_nodes : 0
       max_size     = var.active_version == "blue" ? var.max_nodes : 0
     }
     
     version = "1.27"  # 현재 버전
     
     labels = {
       "environment" = "production"
       "version"     = "blue"
     }
     
     lifecycle {
       ignore_changes = [scaling_config[0].desired_size]
     }
   }
   
   # 그린 노드 그룹 (새 버전)
   resource "aws_eks_node_group" "green" {
     cluster_name    = aws_eks_cluster.main.name
     node_group_name = "green-nodegroup"
     node_role_arn   = aws_iam_role.node_role.arn
     subnet_ids      = var.private_subnet_ids
     
     scaling_config {
       desired_size = var.active_version == "green" ? var.desired_nodes : 0
       min_size     = var.active_version == "green" ? var.min_nodes : 0
       max_size     = var.active_version == "green" ? var.max_nodes : 0
     }
     
     version = "1.28"  # 새 버전
     
     labels = {
       "environment" = "production"
       "version"     = "green"
     }
     
     lifecycle {
       ignore_changes = [scaling_config[0].desired_size]
     }
   }
   ```

다른 옵션들의 문제점:
- **A. 모든 노드를 동시에 종료하고 새 버전으로 교체**: 이 방법은 모든 워크로드가 동시에 중단되어 서비스 가용성에 심각한 영향을 미칩니다.
- **C. 노드 그룹 업그레이드 없이 컨트롤 플레인만 업그레이드**: 노드 그룹을 업그레이드하지 않으면 새로운 Kubernetes 기능을 완전히 활용할 수 없으며, 버전 차이가 커질수록 호환성 문제가 발생할 수 있습니다.
- **D. 수동으로 각 노드의 kubelet 버전 업그레이드**: EKS 관리형 노드에서는 이 방법이 권장되지 않으며, 오류 가능성이 높고 일관성을 유지하기 어렵습니다.
</details>
### 4. Amazon EKS 클러스터 업그레이드 중 애드온 관리에 대한 가장 올바른 접근 방식은 무엇인가요?

A. 애드온 업그레이드 무시  
B. 컨트롤 플레인 업그레이드 전에 모든 애드온 업그레이드  
C. 컨트롤 플레인 업그레이드 후 호환되는 애드온 버전으로 업그레이드  
D. 모든 애드온 제거 후 재설치  

<details>
<summary>정답 및 설명</summary>

**정답: C. 컨트롤 플레인 업그레이드 후 호환되는 애드온 버전으로 업그레이드**

**설명:**
Amazon EKS 클러스터 업그레이드 중 애드온 관리에 대한 가장 올바른 접근 방식은 컨트롤 플레인 업그레이드 후 호환되는 애드온 버전으로 업그레이드하는 것입니다. 이 접근 방식은 Kubernetes 버전과 애드온 간의 호환성을 보장하고, 업그레이드 과정에서 발생할 수 있는 문제를 최소화합니다.

**컨트롤 플레인 업그레이드 후 애드온 업그레이드의 주요 이점:**

1. **버전 호환성 보장**:
   - 각 Kubernetes 버전에 맞는 호환 애드온 버전 선택 가능
   - 컨트롤 플레인 API와 애드온 간의 호환성 문제 방지
   - 안정적인 업그레이드 경로 제공

2. **단계적 업그레이드 가능**:
   - 컨트롤 플레인 업그레이드 검증 후 애드온 업그레이드
   - 문제 발생 시 원인 격리 용이
   - 각 단계별 검증 가능

3. **EKS 관리형 애드온 활용**:
   - AWS에서 관리하는 애드온 수명 주기
   - 호환성이 검증된 버전 제공
   - 자동 보안 패치 및 업데이트

**구현 방법:**

1. **EKS 관리형 애드온 업그레이드**:
   ```bash
   # 사용 가능한 애드온 버전 확인
   aws eks describe-addon-versions \
     --addon-name vpc-cni \
     --kubernetes-version 1.28
   
   # 애드온 업그레이드
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.13.0-eksbuild.1 \
     --resolve-conflicts PRESERVE
   ```

2. **주요 EKS 애드온 업그레이드**:
   ```bash
   # VPC CNI 업그레이드
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.13.0-eksbuild.1
   
   # CoreDNS 업그레이드
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name coredns \
     --addon-version v1.9.3-eksbuild.3
   
   # kube-proxy 업그레이드
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name kube-proxy \
     --addon-version v1.28.1-eksbuild.1
   ```

3. **자체 관리형 애드온 업그레이드**:
   ```bash
   # Helm을 사용한 애드온 업그레이드
   helm repo update
   helm upgrade --install metrics-server metrics-server/metrics-server \
     --namespace kube-system \
     --version 3.8.2 \
     --set apiService.create=true
   ```

**주요 EKS 애드온 및 호환성:**

1. **Amazon VPC CNI**:
   - 네트워크 인터페이스 관리
   - 파드 IP 할당
   - 버전 호환성 중요

2. **CoreDNS**:
   - 클러스터 내 DNS 서비스
   - 서비스 디스커버리
   - Kubernetes 버전별 권장 버전 존재

3. **kube-proxy**:
   - 네트워크 프록시
   - 서비스 IP 라우팅
   - 컨트롤 플레인 버전과 일치 권장

4. **기타 일반 애드온**:
   - Cluster Autoscaler
   - Metrics Server
   - AWS Load Balancer Controller
   - External DNS

**애드온 업그레이드 시 고려 사항:**

1. **충돌 해결 전략**:
   - OVERWRITE: 기존 설정 덮어쓰기
   - PRESERVE: 기존 사용자 지정 설정 유지
   - NONE: 충돌 시 업그레이드 실패

2. **업그레이드 순서**:
   - 중요도 및 의존성에 따른 순서 결정
   - 일반적으로 CNI → CoreDNS → kube-proxy → 기타 애드온

3. **업그레이드 검증**:
   - 각 애드온 업그레이드 후 기능 검증
   - 로그 및 이벤트 모니터링
   - 워크로드 영향 확인

**모범 사례:**

1. **애드온 버전 호환성 확인**:
   ```bash
   # 각 Kubernetes 버전에 대한 호환 애드온 버전 확인
   aws eks describe-addon-versions \
     --kubernetes-version 1.28 \
     --query "addons[].{Name:addonName,LatestVersion:addonVersions[0].addonVersion}"
   ```

2. **업그레이드 전 애드온 상태 확인**:
   ```bash
   # 현재 애드온 상태 확인
   aws eks describe-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni
   
   # 애드온 파드 상태 확인
   kubectl get pods -n kube-system -l k8s-app=aws-node
   ```

3. **단계적 애드온 업그레이드**:
   - 한 번에 하나의 애드온만 업그레이드
   - 각 업그레이드 후 검증
   - 문제 발생 시 롤백 준비

4. **사용자 지정 설정 백업**:
   ```bash
   # 애드온 구성 백업
   kubectl get configmap aws-node -n kube-system -o yaml > vpc-cni-configmap-backup.yaml
   ```

**실제 구현 예시:**

1. **애드온 업그레이드 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 애드온 업그레이드 스크립트
   
   CLUSTER_NAME="my-cluster"
   KUBERNETES_VERSION="1.28"
   
   echo "=== EKS 애드온 업그레이드 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "Kubernetes 버전: $KUBERNETES_VERSION"
   echo
   
   # 현재 애드온 버전 확인
   echo "=== 현재 애드온 버전 ==="
   aws eks describe-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name vpc-cni \
     --query "addon.addonVersion" \
     --output text
   
   aws eks describe-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name coredns \
     --query "addon.addonVersion" \
     --output text
   
   aws eks describe-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name kube-proxy \
     --query "addon.addonVersion" \
     --output text
   
   # 호환되는 애드온 버전 확인
   echo
   echo "=== 호환되는 애드온 버전 ==="
   VPC_CNI_VERSION=$(aws eks describe-addon-versions \
     --addon-name vpc-cni \
     --kubernetes-version $KUBERNETES_VERSION \
     --query "addons[0].addonVersions[0].addonVersion" \
     --output text)
   
   COREDNS_VERSION=$(aws eks describe-addon-versions \
     --addon-name coredns \
     --kubernetes-version $KUBERNETES_VERSION \
     --query "addons[0].addonVersions[0].addonVersion" \
     --output text)
   
   KUBE_PROXY_VERSION=$(aws eks describe-addon-versions \
     --addon-name kube-proxy \
     --kubernetes-version $KUBERNETES_VERSION \
     --query "addons[0].addonVersions[0].addonVersion" \
     --output text)
   
   echo "VPC CNI: $VPC_CNI_VERSION"
   echo "CoreDNS: $COREDNS_VERSION"
   echo "kube-proxy: $KUBE_PROXY_VERSION"
   
   # 사용자 확인
   echo
   read -p "애드온 업그레이드를 시작하시겠습니까? (y/n): " confirm
   if [[ $confirm != "y" ]]; then
     echo "업그레이드가 취소되었습니다."
     exit 1
   fi
   
   # VPC CNI 업그레이드
   echo
   echo "=== VPC CNI 업그레이드 ==="
   aws eks update-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name vpc-cni \
     --addon-version $VPC_CNI_VERSION \
     --resolve-conflicts PRESERVE
   
   # VPC CNI 상태 확인
   echo
   echo "=== VPC CNI 상태 확인 ==="
   sleep 30
   kubectl get pods -n kube-system -l k8s-app=aws-node
   
   # CoreDNS 업그레이드
   echo
   echo "=== CoreDNS 업그레이드 ==="
   aws eks update-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name coredns \
     --addon-version $COREDNS_VERSION \
     --resolve-conflicts PRESERVE
   
   # CoreDNS 상태 확인
   echo
   echo "=== CoreDNS 상태 확인 ==="
   sleep 30
   kubectl get pods -n kube-system -l k8s-app=kube-dns
   
   # kube-proxy 업그레이드
   echo
   echo "=== kube-proxy 업그레이드 ==="
   aws eks update-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name kube-proxy \
     --addon-version $KUBE_PROXY_VERSION \
     --resolve-conflicts PRESERVE
   
   # kube-proxy 상태 확인
   echo
   echo "=== kube-proxy 상태 확인 ==="
   sleep 30
   kubectl get pods -n kube-system -l k8s-app=kube-proxy
   
   echo
   echo "=== 애드온 업그레이드 완료 ==="
   echo "현재 애드온 버전:"
   aws eks describe-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name vpc-cni \
     --query "addon.addonVersion" \
     --output text
   
   aws eks describe-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name coredns \
     --query "addon.addonVersion" \
     --output text
   
   aws eks describe-addon \
     --cluster-name $CLUSTER_NAME \
     --addon-name kube-proxy \
     --query "addon.addonVersion" \
     --output text
   ```

2. **Terraform을 사용한 애드온 관리**:
   ```hcl
   # EKS 클러스터 정의
   resource "aws_eks_cluster" "main" {
     name     = "my-cluster"
     role_arn = aws_iam_role.eks_cluster.arn
     version  = "1.28"
     
     vpc_config {
       subnet_ids         = var.subnet_ids
       security_group_ids = [aws_security_group.eks_cluster.id]
     }
   }
   
   # VPC CNI 애드온
   resource "aws_eks_addon" "vpc_cni" {
     cluster_name      = aws_eks_cluster.main.name
     addon_name        = "vpc-cni"
     addon_version     = "v1.13.0-eksbuild.1"  # 1.28 호환 버전
     resolve_conflicts = "PRESERVE"
     
     depends_on = [
       aws_eks_cluster.main
     ]
   }
   
   # CoreDNS 애드온
   resource "aws_eks_addon" "coredns" {
     cluster_name      = aws_eks_cluster.main.name
     addon_name        = "coredns"
     addon_version     = "v1.9.3-eksbuild.3"  # 1.28 호환 버전
     resolve_conflicts = "PRESERVE"
     
     depends_on = [
       aws_eks_cluster.main,
       aws_eks_node_group.main
     ]
   }
   
   # kube-proxy 애드온
   resource "aws_eks_addon" "kube_proxy" {
     cluster_name      = aws_eks_cluster.main.name
     addon_name        = "kube-proxy"
     addon_version     = "v1.28.1-eksbuild.1"  # 1.28 호환 버전
     resolve_conflicts = "PRESERVE"
     
     depends_on = [
       aws_eks_cluster.main
     ]
   }
   ```

3. **자체 관리형 애드온 업그레이드 스크립트**:
   ```bash
   #!/bin/bash
   # 자체 관리형 애드온 업그레이드 스크립트
   
   CLUSTER_NAME="my-cluster"
   KUBERNETES_VERSION="1.28"
   
   echo "=== 자체 관리형 애드온 업그레이드 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "Kubernetes 버전: $KUBERNETES_VERSION"
   echo
   
   # Helm 리포지토리 업데이트
   echo "=== Helm 리포지토리 업데이트 ==="
   helm repo update
   
   # Metrics Server 업그레이드
   echo
   echo "=== Metrics Server 업그레이드 ==="
   helm upgrade --install metrics-server metrics-server/metrics-server \
     --namespace kube-system \
     --version 3.8.2 \
     --set apiService.create=true
   
   # AWS Load Balancer Controller 업그레이드
   echo
   echo "=== AWS Load Balancer Controller 업그레이드 ==="
   helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
     --namespace kube-system \
     --set clusterName=$CLUSTER_NAME \
     --set serviceAccount.create=false \
     --set serviceAccount.name=aws-load-balancer-controller
   
   # Cluster Autoscaler 업그레이드
   echo
   echo "=== Cluster Autoscaler 업그레이드 ==="
   helm upgrade --install cluster-autoscaler autoscaler/cluster-autoscaler \
     --namespace kube-system \
     --set autoDiscovery.clusterName=$CLUSTER_NAME \
     --set awsRegion=$(aws configure get region) \
     --set rbac.create=true \
     --set extraArgs.skip-nodes-with-system-pods=false
   
   echo
   echo "=== 자체 관리형 애드온 업그레이드 완료 ==="
   kubectl get pods -n kube-system | grep -E 'metrics-server|aws-load-balancer-controller|cluster-autoscaler'
   ```

다른 옵션들의 문제점:
- **A. 애드온 업그레이드 무시**: 애드온을 업그레이드하지 않으면 Kubernetes 버전과의 호환성 문제가 발생할 수 있으며, 보안 패치나 버그 수정이 적용되지 않습니다.
- **B. 컨트롤 플레인 업그레이드 전에 모든 애드온 업그레이드**: 컨트롤 플레인 업그레이드 전에 애드온을 업그레이드하면 새 버전의 애드온이 이전 버전의 컨트롤 플레인과 호환되지 않을 수 있습니다.
- **D. 모든 애드온 제거 후 재설치**: 이 방법은 불필요하게 복잡하고 위험하며, 애드온 구성 및 설정이 손실될 수 있습니다.
</details>
### 5. Amazon EKS 클러스터 업그레이드 중 발생할 수 있는 문제를 해결하기 위한 가장 효과적인 접근 방식은 무엇인가요?

A. 즉시 새 클러스터 생성  
B. 문제 발생 시 AWS 지원팀에만 의존  
C. 체계적인 문제 해결 접근 방식 및 로그 분석 사용  
D. 업그레이드 문제 무시  

<details>
<summary>정답 및 설명</summary>

**정답: C. 체계적인 문제 해결 접근 방식 및 로그 분석 사용**

**설명:**
Amazon EKS 클러스터 업그레이드 중 발생할 수 있는 문제를 해결하기 위한 가장 효과적인 접근 방식은 체계적인 문제 해결 접근 방식 및 로그 분석을 사용하는 것입니다. 이 접근 방식은 문제의 근본 원인을 식별하고, 적절한 해결책을 적용하며, 유사한 문제의 재발을 방지하는 데 도움이 됩니다.

**체계적인 문제 해결 접근 방식의 주요 구성 요소:**

1. **문제 식별 및 정의**:
   - 증상 및 영향 범위 파악
   - 문제 발생 시점 및 조건 확인
   - 정상 동작과의 차이점 식별

2. **정보 수집 및 분석**:
   - 로그 및 이벤트 수집
   - 리소스 상태 및 구성 확인
   - 오류 메시지 및 패턴 분석

3. **가설 수립 및 검증**:
   - 가능한 원인 식별
   - 가설 테스트 및 검증
   - 근본 원인 확인

4. **해결책 구현 및 검증**:
   - 적절한 해결책 적용
   - 해결책 효과 검증
   - 문제 재발 방지 조치

**구현 방법:**

1. **업그레이드 문제 진단**:
   ```bash
   # 클러스터 상태 확인
   aws eks describe-cluster \
     --name my-cluster \
     --query "cluster.status"
   
   # 업그레이드 상태 확인
   aws eks describe-update \
     --name my-cluster \
     --update-id <update-id>
   
   # 컨트롤 플레인 로그 확인
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   
   # CloudWatch Logs에서 로그 확인
   aws logs filter-log-events \
     --log-group-name /aws/eks/my-cluster/cluster \
     --filter-pattern "Error"
   ```

2. **노드 그룹 문제 진단**:
   ```bash
   # 노드 그룹 상태 확인
   aws eks describe-nodegroup \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   
   # 노드 상태 확인
   kubectl get nodes
   kubectl describe node <node-name>
   
   # 노드 로그 확인
   kubectl logs -n kube-system <node-agent-pod>
   ```

3. **애드온 문제 진단**:
   ```bash
   # 애드온 상태 확인
   aws eks describe-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni
   
   # 애드온 파드 상태 확인
   kubectl get pods -n kube-system -l k8s-app=aws-node
   kubectl describe pod -n kube-system <addon-pod-name>
   kubectl logs -n kube-system <addon-pod-name>
   ```

**일반적인 업그레이드 문제 및 해결 방법:**

1. **컨트롤 플레인 업그레이드 실패**:
   - **증상**: 업그레이드 상태가 "Failed"로 표시됨
   - **원인**: API 서버 구성 문제, 리소스 제약, 네트워크 문제
   - **해결 방법**:
     - 업그레이드 오류 메시지 확인
     - AWS 지원팀에 문의
     - 클러스터 상태 및 로그 제공

2. **노드 그룹 업그레이드 실패**:
   - **증상**: 노드가 Ready 상태가 되지 않음, 파드 스케줄링 실패
   - **원인**: 인스턴스 시작 문제, kubelet 구성 오류, CNI 문제
   - **해결 방법**:
     - 노드 로그 확인
     - 인스턴스 상태 확인
     - 보안 그룹 및 IAM 권한 확인

3. **애드온 업그레이드 문제**:
   - **증상**: 애드온 파드가 CrashLoopBackOff 또는 Error 상태
   - **원인**: 버전 호환성 문제, 구성 충돌, 리소스 제약
   - **해결 방법**:
     - 파드 로그 확인
     - 구성 충돌 해결
     - 호환되는 버전으로 다시 시도

4. **워크로드 호환성 문제**:
   - **증상**: 애플리케이션 파드 시작 실패, API 오류
   - **원인**: 더 이상 사용되지 않는 API 사용, 호환되지 않는 기능
   - **해결 방법**:
     - 매니페스트 업데이트
     - 애플리케이션 로그 확인
     - 호환성 문제 해결

**모범 사례:**

1. **문제 해결을 위한 로그 수집**:
   ```bash
   # 클러스터 정보 수집
   kubectl cluster-info dump > cluster-info.txt
   
   # 노드 정보 수집
   kubectl describe nodes > nodes-info.txt
   
   # 시스템 파드 로그 수집
   kubectl logs -n kube-system -l k8s-app=aws-node > vpc-cni-logs.txt
   kubectl logs -n kube-system -l k8s-app=kube-dns > coredns-logs.txt
   kubectl logs -n kube-system -l k8s-app=kube-proxy > kube-proxy-logs.txt
   
   # 이벤트 수집
   kubectl get events --all-namespaces --sort-by='.lastTimestamp' > events.txt
   ```

2. **롤백 절차 준비**:
   ```bash
   # 노드 그룹 롤백 (새 노드 그룹 생성)
   eksctl create nodegroup \
     --cluster my-cluster \
     --name rollback-nodegroup \
     --node-type m5.large \
     --nodes 3 \
     --nodes-min 3 \
     --nodes-max 6 \
     --node-ami auto \
     --kubernetes-version 1.27  # 이전 버전
   
   # 워크로드 마이그레이션
   kubectl cordon -l eks.amazonaws.com/nodegroup=problematic-nodegroup
   kubectl drain --ignore-daemonsets --delete-emptydir-data -l eks.amazonaws.com/nodegroup=problematic-nodegroup
   ```

3. **문제 해결 문서화**:
   ```markdown
   # 업그레이드 문제 해결 보고서
   
   ## 문제 설명
   - 증상: 노드 그룹 업그레이드 후 CoreDNS 파드가 CrashLoopBackOff 상태
   - 영향: 서비스 디스커버리 실패, 애플리케이션 연결 문제
   - 발생 시점: 2023-07-15 14:30 UTC, 노드 그룹 업그레이드 직후
   
   ## 조사 과정
   1. CoreDNS 파드 상태 확인
   2. CoreDNS 로그 분석
   3. 노드 상태 및 리소스 확인
   4. 네트워크 정책 검토
   
   ## 발견 사항
   - CoreDNS 파드 로그에서 구성 오류 발견
   - 업그레이드 중 CoreDNS ConfigMap이 잘못 수정됨
   
   ## 해결 방법
   1. CoreDNS ConfigMap 복원
   2. CoreDNS 파드 재시작
   3. 서비스 연결 확인
   
   ## 예방 조치
   1. 업그레이드 전 중요 구성 백업
   2. 자동화된 검증 테스트 구현
   3. 단계적 업그레이드 프로세스 개선
   ```

4. **AWS 지원팀과 효과적으로 협력**:
   - 명확한 문제 설명 제공
   - 관련 로그 및 오류 메시지 공유
   - 수행한 문제 해결 단계 설명

**실제 구현 예시:**

1. **업그레이드 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 업그레이드 문제 해결 스크립트
   
   CLUSTER_NAME="my-cluster"
   PROBLEM_TYPE=$1  # control-plane, nodegroup, addon
   
   echo "=== EKS 업그레이드 문제 해결 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "문제 유형: $PROBLEM_TYPE"
   echo
   
   # 진단 정보 디렉토리 생성
   TIMESTAMP=$(date +%Y%m%d-%H%M%S)
   DIAG_DIR="eks-diag-$TIMESTAMP"
   mkdir -p $DIAG_DIR
   
   # 클러스터 정보 수집
   echo "=== 클러스터 정보 수집 ==="
   aws eks describe-cluster --name $CLUSTER_NAME > $DIAG_DIR/cluster-info.json
   kubectl cluster-info dump > $DIAG_DIR/cluster-info-dump.txt
   kubectl get nodes -o wide > $DIAG_DIR/nodes.txt
   kubectl get pods --all-namespaces -o wide > $DIAG_DIR/pods.txt
   kubectl get events --all-namespaces --sort-by='.lastTimestamp' > $DIAG_DIR/events.txt
   
   # 문제 유형별 진단
   case $PROBLEM_TYPE in
     control-plane)
       echo "=== 컨트롤 플레인 문제 진단 ==="
       # 업그레이드 상태 확인
       aws eks list-updates --name $CLUSTER_NAME > $DIAG_DIR/updates.json
       
       # 컨트롤 플레인 로그 확인
       echo "컨트롤 플레인 로그를 확인하려면 CloudWatch Logs 콘솔에서 다음 로그 그룹을 확인하세요:"
       echo "/aws/eks/$CLUSTER_NAME/cluster"
       ;;
       
     nodegroup)
       echo "=== 노드 그룹 문제 진단 ==="
       # 노드 그룹 목록 및 상태
       aws eks list-nodegroups --cluster-name $CLUSTER_NAME > $DIAG_DIR/nodegroups.json
       
       # 각 노드 그룹 상세 정보
       for NG in $(aws eks list-nodegroups --cluster-name $CLUSTER_NAME --query 'nodegroups[*]' --output text); do
         aws eks describe-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NG > $DIAG_DIR/nodegroup-$NG.json
       done
       
       # 노드 상태 및 정보
       kubectl describe nodes > $DIAG_DIR/nodes-describe.txt
       
       # 노드 관련 파드 로그
       kubectl logs -n kube-system -l k8s-app=aws-node > $DIAG_DIR/vpc-cni-logs.txt
       ;;
       
     addon)
       echo "=== 애드온 문제 진단 ==="
       # 애드온 목록 및 상태
       aws eks list-addons --cluster-name $CLUSTER_NAME > $DIAG_DIR/addons.json
       
       # 각 애드온 상세 정보
       for ADDON in $(aws eks list-addons --cluster-name $CLUSTER_NAME --query 'addons[*]' --output text); do
         aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name $ADDON > $DIAG_DIR/addon-$ADDON.json
       done
       
       # 주요 애드온 파드 로그
       kubectl logs -n kube-system -l k8s-app=kube-dns > $DIAG_DIR/coredns-logs.txt
       kubectl logs -n kube-system -l k8s-app=kube-proxy > $DIAG_DIR/kube-proxy-logs.txt
       kubectl logs -n kube-system -l k8s-app=aws-node > $DIAG_DIR/vpc-cni-logs.txt
       ;;
       
     *)
       echo "알 수 없는 문제 유형입니다. control-plane, nodegroup, addon 중 하나를 지정하세요."
       exit 1
       ;;
   esac
   
   echo
   echo "=== 진단 정보 수집 완료 ==="
   echo "진단 정보가 $DIAG_DIR 디렉토리에 저장되었습니다."
   echo "이 정보를 사용하여 문제를 분석하거나 AWS 지원팀에 제공하세요."
   ```

2. **업그레이드 롤백 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 업그레이드 롤백 스크립트
   
   CLUSTER_NAME="my-cluster"
   PREVIOUS_VERSION="1.27"
   PROBLEMATIC_NODEGROUP="my-nodegroup"
   
   echo "=== EKS 업그레이드 롤백 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo "이전 버전: $PREVIOUS_VERSION"
   echo "문제 노드 그룹: $PROBLEMATIC_NODEGROUP"
   echo
   
   # 롤백 노드 그룹 생성
   echo "=== 롤백 노드 그룹 생성 ==="
   eksctl create nodegroup \
     --cluster $CLUSTER_NAME \
     --name rollback-nodegroup \
     --node-type m5.large \
     --nodes 3 \
     --nodes-min 3 \
     --nodes-max 6 \
     --node-ami auto \
     --kubernetes-version $PREVIOUS_VERSION
   
   # 롤백 노드 그룹 상태 확인
   echo
   echo "=== 롤백 노드 그룹 상태 확인 ==="
   kubectl get nodes -l eks.amazonaws.com/nodegroup=rollback-nodegroup
   
   # 워크로드 마이그레이션
   echo
   echo "=== 워크로드 마이그레이션 ==="
   echo "문제 노드 그룹에 코드온 설정..."
   kubectl cordon -l eks.amazonaws.com/nodegroup=$PROBLEMATIC_NODEGROUP
   
   echo "파드 드레이닝..."
   kubectl drain --ignore-daemonsets --delete-emptydir-data -l eks.amazonaws.com/nodegroup=$PROBLEMATIC_NODEGROUP
   
   # 파드 재배포 확인
   echo
   echo "=== 파드 재배포 확인 ==="
   kubectl get pods --all-namespaces -o wide | grep -v "Running\|Completed"
   
   # 문제 노드 그룹 삭제
   echo
   read -p "문제 노드 그룹을 삭제하시겠습니까? (y/n): " confirm
   if [[ $confirm == "y" ]]; then
     echo "문제 노드 그룹 삭제..."
     eksctl delete nodegroup \
       --cluster $CLUSTER_NAME \
       --name $PROBLEMATIC_NODEGROUP
   else
     echo "문제 노드 그룹 삭제를 건너뜁니다."
   fi
   
   echo
   echo "=== 롤백 완료 ==="
   echo "현재 노드 상태:"
   kubectl get nodes
   ```

3. **업그레이드 문제 해결 가이드**:
   ```markdown
   # EKS 업그레이드 문제 해결 가이드
   
   ## 컨트롤 플레인 업그레이드 문제
   
   ### 증상
   - 업그레이드 상태가 "Failed"로 표시됨
   - API 서버 응답 지연 또는 오류
   - 클러스터 작업 불가
   
   ### 진단 단계
   1. 업그레이드 상태 확인:
      ```
      aws eks describe-update --name my-cluster --update-id <update-id>
      ```
   
   2. 컨트롤 플레인 로그 확인:
      - CloudWatch Logs에서 `/aws/eks/my-cluster/cluster` 로그 그룹 검토
      - 오류 메시지 및 패턴 식별
   
   3. 클러스터 상태 확인:
      ```
      kubectl get componentstatuses
      kubectl get nodes
      kubectl get pods --all-namespaces
      ```
   
   ### 해결 방법
   1. AWS 지원팀에 문의
   2. 진단 정보 제공
   3. 지원팀 지침에 따라 조치
   
   ## 노드 그룹 업그레이드 문제
   
   ### 증상
   - 노드가 Ready 상태가 되지 않음
   - 파드 스케줄링 실패
   - 노드 그룹 업그레이드 상태가 "Failed"로 표시됨
   
   ### 진단 단계
   1. 노드 그룹 상태 확인:
      ```
      aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup
      ```
   
   2. 노드 상태 및 이벤트 확인:
      ```
      kubectl describe node <node-name>
      kubectl get events --field-selector involvedObject.name=<node-name>
      ```
   
   3. 인스턴스 상태 확인:
      - EC2 콘솔에서 인스턴스 상태 확인
      - 인스턴스 시작 문제 식별
   
   ### 해결 방법
   1. 롤백 노드 그룹 생성
   2. 워크로드 마이그레이션
   3. 문제 노드 그룹 삭제
   
   ## 애드온 업그레이드 문제
   
   ### 증상
   - 애드온 파드가 CrashLoopBackOff 또는 Error 상태
   - 네트워크 또는 DNS 문제
   - 애드온 업그레이드 상태가 "Failed"로 표시됨
   
   ### 진단 단계
   1. 애드온 상태 확인:
      ```
      aws eks describe-addon --cluster-name my-cluster --addon-name <addon-name>
      ```
   
   2. 애드온 파드 상태 및 로그 확인:
      ```
      kubectl get pods -n kube-system -l k8s-app=<addon-label>
      kubectl logs -n kube-system <addon-pod-name>
      ```
   
   3. 구성 충돌 확인:
      - 사용자 지정 구성과 기본 구성 비교
      - 충돌 식별
   
   ### 해결 방법
   1. 이전 버전으로 롤백:
      ```
      aws eks update-addon --cluster-name my-cluster --addon-name <addon-name> --addon-version <previous-version> --resolve-conflicts OVERWRITE
      ```
   
   2. 구성 충돌 해결 후 다시 시도:
      ```
      aws eks update-addon --cluster-name my-cluster --addon-name <addon-name> --addon-version <target-version> --resolve-conflicts PRESERVE
      ```
   ```

다른 옵션들의 문제점:
- **A. 즉시 새 클러스터 생성**: 이는 극단적인 접근 방식으로, 시간과 리소스가 많이 소요되며, 근본 원인을 해결하지 않고 회피하는 방법입니다.
- **B. 문제 발생 시 AWS 지원팀에만 의존**: AWS 지원팀은 중요한 리소스이지만, 기본적인 문제 해결 단계를 먼저 수행하면 해결 시간을 단축할 수 있습니다.
- **D. 업그레이드 문제 무시**: 업그레이드 문제를 무시하면 클러스터 안정성, 보안 및 성능에 장기적인 영향을 미칠 수 있습니다.
</details>
### 6. Amazon EKS 클러스터 업그레이드 후 검증을 위한 가장 포괄적인 접근 방식은 무엇인가요?

A. 노드 수 확인만 수행  
B. 클러스터 버전 확인만 수행  
C. 시스템 구성 요소, 워크로드 기능 및 성능 메트릭을 포함한 다단계 검증 수행  
D. 업그레이드 후 검증 없이 즉시 프로덕션 사용  

<details>
<summary>정답 및 설명</summary>

**정답: C. 시스템 구성 요소, 워크로드 기능 및 성능 메트릭을 포함한 다단계 검증 수행**

**설명:**
Amazon EKS 클러스터 업그레이드 후 검증을 위한 가장 포괄적인 접근 방식은 시스템 구성 요소, 워크로드 기능 및 성능 메트릭을 포함한 다단계 검증을 수행하는 것입니다. 이 접근 방식은 업그레이드가 성공적으로 완료되었고 클러스터가 예상대로 작동하는지 확인하는 데 도움이 됩니다.

**다단계 검증의 주요 구성 요소:**

1. **시스템 구성 요소 검증**:
   - 컨트롤 플레인 구성 요소 상태
   - 노드 상태 및 버전
   - 시스템 파드 및 애드온 상태

2. **워크로드 기능 검증**:
   - 애플리케이션 배포 및 확장
   - 서비스 연결 및 라우팅
   - 스토리지 및 볼륨 기능

3. **성능 메트릭 검증**:
   - 리소스 사용량 및 효율성
   - 지연 시간 및 처리량
   - 오류율 및 가용성

**구현 방법:**

1. **시스템 구성 요소 검증**:
   ```bash
   # 클러스터 버전 확인
   aws eks describe-cluster \
     --name my-cluster \
     --query "cluster.version" \
     --output text
   
   # 컨트롤 플레인 구성 요소 상태 확인
   kubectl get componentstatuses
   
   # 노드 상태 및 버전 확인
   kubectl get nodes -o wide
   
   # 시스템 파드 상태 확인
   kubectl get pods -n kube-system
   ```

2. **워크로드 기능 검증**:
   ```bash
   # 테스트 배포 생성
   kubectl create deployment nginx-test --image=nginx
   
   # 배포 확장
   kubectl scale deployment nginx-test --replicas=3
   
   # 서비스 생성 및 연결 테스트
   kubectl expose deployment nginx-test --port=80 --type=ClusterIP
   kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- nginx-test
   
   # 볼륨 기능 테스트
   kubectl apply -f - <<EOF
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: test-pvc
   spec:
     accessModes:
       - ReadWriteOnce
     resources:
       requests:
         storage: 1Gi
   EOF
   
   kubectl apply -f - <<EOF
   apiVersion: v1
   kind: Pod
   metadata:
     name: volume-test
   spec:
     containers:
     - name: volume-test
       image: busybox
       command: ["sh", "-c", "echo 'test' > /data/test.txt && sleep 3600"]
       volumeMounts:
       - name: data
         mountPath: /data
     volumes:
     - name: data
       persistentVolumeClaim:
         claimName: test-pvc
   EOF
   ```

3. **성능 메트릭 검증**:
   ```bash
   # 노드 리소스 사용량 확인
   kubectl top nodes
   
   # 파드 리소스 사용량 확인
   kubectl top pods --all-namespaces
   
   # 로드 테스트 수행
   kubectl run -it --rm --restart=Never loadtest --image=busybox -- sh -c "while true; do wget -q -O- http://nginx-test; done"
   ```

**검증 영역 및 체크리스트:**

1. **컨트롤 플레인 검증**:
   - API 서버 응답성
   - etcd 상태 및 성능
   - 컨트롤러 관리자 및 스케줄러 기능

2. **데이터 플레인 검증**:
   - 노드 상태 및 가용성
   - kubelet 기능
   - 컨테이너 런타임 상태

3. **네트워킹 검증**:
   - 파드 간 통신
   - 서비스 디스커버리
   - 인그레스 및 이그레스 트래픽

4. **스토리지 검증**:
   - 볼륨 프로비저닝
   - 데이터 지속성
   - 스토리지 클래스 기능

5. **보안 검증**:
   - 인증 및 권한 부여
   - 네트워크 정책
   - 암호화 및 보안 컨텍스트

**모범 사례:**

1. **단계적 검증 접근 방식**:
   ```bash
   # 1단계: 시스템 구성 요소 검증
   ./validate-system-components.sh
   
   # 2단계: 기본 워크로드 기능 검증
   ./validate-basic-workloads.sh
   
   # 3단계: 고급 기능 검증
   ./validate-advanced-features.sh
   
   # 4단계: 성능 및 부하 테스트
   ./validate-performance.sh
   ```

2. **자동화된 검증 테스트**:
   ```yaml
   # 검증 작업 정의
   apiVersion: batch/v1
   kind: Job
   metadata:
     name: cluster-validation
   spec:
     template:
       spec:
         containers:
         - name: validation
           image: validation-tools:latest
           command: ["/scripts/validate-cluster.sh"]
         restartPolicy: Never
   ```

3. **검증 결과 문서화**:
   ```bash
   # 검증 결과 수집
   kubectl get nodes -o wide > validation-results/nodes.txt
   kubectl get pods --all-namespaces > validation-results/pods.txt
   kubectl get events --all-namespaces --sort-by='.lastTimestamp' > validation-results/events.txt
   
   # 성능 메트릭 수집
   kubectl top nodes > validation-results/node-metrics.txt
   kubectl top pods --all-namespaces > validation-results/pod-metrics.txt
   ```

4. **점진적인 프로덕션 트래픽 전환**:
   - 카나리 배포 사용
   - 트래픽 점진적 증가
   - 지표 모니터링 및 이상 탐지

**실제 구현 예시:**

1. **포괄적인 검증 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 클러스터 업그레이드 후 포괄적인 검증 스크립트
   
   CLUSTER_NAME="my-cluster"
   
   echo "=== EKS 클러스터 업그레이드 검증 ==="
   echo "클러스터: $CLUSTER_NAME"
   echo
   
   # 결과 디렉토리 생성
   TIMESTAMP=$(date +%Y%m%d-%H%M%S)
   RESULTS_DIR="validation-results-$TIMESTAMP"
   mkdir -p $RESULTS_DIR
   
   # 1. 시스템 구성 요소 검증
   echo "=== 1. 시스템 구성 요소 검증 ==="
   
   # 클러스터 버전 확인
   echo "클러스터 버전 확인..."
   CLUSTER_VERSION=$(aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.version" --output text)
   echo "클러스터 버전: $CLUSTER_VERSION"
   echo $CLUSTER_VERSION > $RESULTS_DIR/cluster-version.txt
   
   # 컨트롤 플레인 상태 확인
   echo
   echo "컨트롤 플레인 상태 확인..."
   kubectl get componentstatuses > $RESULTS_DIR/component-status.txt
   cat $RESULTS_DIR/component-status.txt
   
   # 노드 상태 확인
   echo
   echo "노드 상태 확인..."
   kubectl get nodes -o wide > $RESULTS_DIR/nodes.txt
   cat $RESULTS_DIR/nodes.txt
   
   # 시스템 파드 상태 확인
   echo
   echo "시스템 파드 상태 확인..."
   kubectl get pods -n kube-system > $RESULTS_DIR/system-pods.txt
   cat $RESULTS_DIR/system-pods.txt
   
   # 2. 워크로드 기능 검증
   echo
   echo "=== 2. 워크로드 기능 검증 ==="
   
   # 네임스페이스 생성
   echo "테스트 네임스페이스 생성..."
   kubectl create namespace validation-test
   
   # 배포 테스트
   echo
   echo "배포 테스트..."
   kubectl create deployment nginx-test --image=nginx -n validation-test
   sleep 10
   kubectl get deployment -n validation-test > $RESULTS_DIR/deployment-test.txt
   cat $RESULTS_DIR/deployment-test.txt
   
   # 확장 테스트
   echo
   echo "확장 테스트..."
   kubectl scale deployment nginx-test --replicas=3 -n validation-test
   sleep 10
   kubectl get pods -n validation-test > $RESULTS_DIR/scaling-test.txt
   cat $RESULTS_DIR/scaling-test.txt
   
   # 서비스 테스트
   echo
   echo "서비스 테스트..."
   kubectl expose deployment nginx-test --port=80 --type=ClusterIP -n validation-test
   sleep 5
   kubectl run -it --rm --restart=Never busybox --image=busybox -n validation-test -- wget -O- nginx-test > $RESULTS_DIR/service-test.txt 2>&1 || true
   cat $RESULTS_DIR/service-test.txt
   
   # 볼륨 테스트
   echo
   echo "볼륨 테스트..."
   cat <<EOF | kubectl apply -f - -n validation-test
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: test-pvc
   spec:
     accessModes:
       - ReadWriteOnce
     resources:
       requests:
         storage: 1Gi
   EOF
   
   sleep 5
   kubectl get pvc -n validation-test > $RESULTS_DIR/volume-test.txt
   cat $RESULTS_DIR/volume-test.txt
   
   # 3. 성능 메트릭 검증
   echo
   echo "=== 3. 성능 메트릭 검증 ==="
   
   # 노드 메트릭
   echo "노드 메트릭 수집..."
   kubectl top nodes > $RESULTS_DIR/node-metrics.txt
   cat $RESULTS_DIR/node-metrics.txt
   
   # 파드 메트릭
   echo
   echo "파드 메트릭 수집..."
   kubectl top pods --all-namespaces > $RESULTS_DIR/pod-metrics.txt
   head -n 10 $RESULTS_DIR/pod-metrics.txt
   
   # 이벤트 확인
   echo
   echo "클러스터 이벤트 확인..."
   kubectl get events --all-namespaces --sort-by='.lastTimestamp' > $RESULTS_DIR/events.txt
   tail -n 10 $RESULTS_DIR/events.txt
   
   # 정리
   echo
   echo "테스트 리소스 정리..."
   kubectl delete namespace validation-test
   
   echo
   echo "=== 검증 완료 ==="
   echo "검증 결과가 $RESULTS_DIR 디렉토리에 저장되었습니다."
   echo
   echo "검증 요약:"
   echo "- 클러스터 버전: $CLUSTER_VERSION"
   echo "- 노드 수: $(kubectl get nodes --no-headers | wc -l)"
   echo "- 시스템 파드 수: $(kubectl get pods -n kube-system --no-headers | wc -l)"
   echo "- 오류 상태 파드: $(kubectl get pods --all-namespaces | grep -v "Running\|Completed" | wc -l)"
   ```

2. **Terraform을 사용한 검증 인프라 구성**:
   ```hcl
   # 검증 네임스페이스
   resource "kubernetes_namespace" "validation" {
     metadata {
       name = "validation"
     }
   }
   
   # 검증 배포
   resource "kubernetes_deployment" "validation_app" {
     metadata {
       name      = "validation-app"
       namespace = kubernetes_namespace.validation.metadata[0].name
     }
     
     spec {
       replicas = 3
       
       selector {
         match_labels = {
           app = "validation-app"
         }
       }
       
       template {
         metadata {
           labels = {
             app = "validation-app"
           }
         }
         
         spec {
           container {
             name  = "nginx"
             image = "nginx:latest"
             
             resources {
               limits = {
                 cpu    = "200m"
                 memory = "256Mi"
               }
               requests = {
                 cpu    = "100m"
                 memory = "128Mi"
               }
             }
             
             liveness_probe {
               http_get {
                 path = "/"
                 port = 80
               }
               
               initial_delay_seconds = 3
               period_seconds        = 3
             }
           }
         }
       }
     }
   }
   
   # 검증 서비스
   resource "kubernetes_service" "validation_service" {
     metadata {
       name      = "validation-service"
       namespace = kubernetes_namespace.validation.metadata[0].name
     }
     
     spec {
       selector = {
         app = kubernetes_deployment.validation_app.spec[0].template[0].metadata[0].labels.app
       }
       
       port {
         port        = 80
         target_port = 80
       }
       
       type = "ClusterIP"
     }
   }
   
   # 검증 PVC
   resource "kubernetes_persistent_volume_claim" "validation_pvc" {
     metadata {
       name      = "validation-pvc"
       namespace = kubernetes_namespace.validation.metadata[0].name
     }
     
     spec {
       access_modes = ["ReadWriteOnce"]
       
       resources {
         requests = {
           storage = "1Gi"
         }
       }
     }
   }
   ```

3. **검증 대시보드 구성**:
   ```yaml
   # Grafana 대시보드 ConfigMap
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cluster-validation-dashboard
     namespace: monitoring
   data:
     cluster-validation.json: |
       {
         "title": "Cluster Validation Dashboard",
         "panels": [
           {
             "title": "Node Status",
             "type": "stat",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(kube_node_status_condition{condition=\"Ready\", status=\"true\"})",
                 "legendFormat": "Ready Nodes"
               }
             ]
           },
           {
             "title": "Pod Status",
             "type": "gauge",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(kube_pod_status_phase{phase=\"Running\"}) / sum(kube_pod_status_phase) * 100",
                 "legendFormat": "Running Pods (%)"
               }
             ]
           },
           {
             "title": "API Server Requests",
             "type": "timeseries",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(rate(apiserver_request_total[5m])) by (code)",
                 "legendFormat": "{{code}}"
               }
             ]
           },
           {
             "title": "Node Resource Usage",
             "type": "timeseries",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(node_cpu_seconds_total{mode=\"user\"}) by (instance)",
                 "legendFormat": "CPU - {{instance}}"
               },
               {
                 "expr": "sum(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) by (instance) / sum(node_memory_MemTotal_bytes) by (instance) * 100",
                 "legendFormat": "Memory - {{instance}}"
               }
             ]
           }
         ]
       }
   ```

다른 옵션들의 문제점:
- **A. 노드 수 확인만 수행**: 노드 수 확인은 기본적인 검증이지만, 노드 상태, 시스템 구성 요소, 워크로드 기능 등 중요한 측면을 놓칠 수 있습니다.
- **B. 클러스터 버전 확인만 수행**: 클러스터 버전 확인은 업그레이드가 완료되었는지 확인하는 데 도움이 되지만, 기능적 검증이 부족합니다.
- **D. 업그레이드 후 검증 없이 즉시 프로덕션 사용**: 검증 없이 프로덕션에 사용하는 것은 위험하며, 잠재적인 문제가 사용자에게 영향을 미칠 수 있습니다.
</details>
