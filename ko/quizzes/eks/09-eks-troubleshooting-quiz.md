# Amazon EKS 문제 해결 퀴즈

이 퀴즈는 Amazon EKS 클러스터에서 발생할 수 있는 다양한 문제를 진단하고 해결하는 능력을 테스트합니다.

## 퀴즈 개요
- 클러스터 생성 및 구성 문제
- 네트워킹 문제
- 노드 및 파드 문제
- 스토리지 문제
- 보안 및 액세스 문제
- 성능 및 확장성 문제

## 객관식 문제

### 1. Amazon EKS 클러스터 생성이 실패할 때 가장 먼저 확인해야 할 사항은 무엇인가요?

A. 클러스터 이름이 고유한지 확인  
B. IAM 권한, VPC 구성 및 서비스 할당량 확인  
C. 다른 리전에서 다시 시도  
D. 더 큰 인스턴스 유형 선택  

<details>
<summary>정답 및 설명</summary>

**정답: B. IAM 권한, VPC 구성 및 서비스 할당량 확인**

**설명:**
Amazon EKS 클러스터 생성이 실패할 때 가장 먼저 확인해야 할 사항은 IAM 권한, VPC 구성 및 서비스 할당량입니다. 이러한 요소들은 클러스터 생성 실패의 가장 일반적인 원인이며, 체계적으로 확인하면 문제를 신속하게 식별하고 해결할 수 있습니다.

**주요 확인 사항:**

1. **IAM 권한 확인**:
   - 클러스터 생성에 필요한 IAM 권한 보유 여부
   - 서비스 연결 역할 생성 권한
   - 클러스터 역할 및 정책 구성

2. **VPC 구성 확인**:
   - 서브넷 구성 (최소 2개의 가용 영역에 분산된 서브넷)
   - 서브넷 CIDR 크기 (최소 /28, 권장 /24)
   - 인터넷 연결 (NAT 게이트웨이 또는 인터넷 게이트웨이)
   - 보안 그룹 및 네트워크 ACL 설정

3. **서비스 할당량 확인**:
   - EKS 클러스터 수 할당량
   - EC2 인스턴스 할당량
   - VPC 및 서브넷 할당량
   - 기타 관련 서비스 할당량

**문제 해결 방법:**

1. **IAM 권한 문제 해결**:
   ```bash
   # IAM 권한 확인
   aws sts get-caller-identity
   
   # 필요한 정책 연결
   aws iam attach-user-policy \
     --user-name myuser \
     --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
   
   # 서비스 연결 역할 생성
   aws iam create-service-linked-role --aws-service-name eks.amazonaws.com
   ```

2. **VPC 구성 문제 해결**:
   ```bash
   # VPC 및 서브넷 확인
   aws ec2 describe-vpcs --vpc-ids vpc-12345678
   aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-12345678"
   
   # 서브넷 태그 확인
   aws ec2 describe-tags --filters "Name=resource-id,Values=subnet-12345678"
   
   # 서브넷 태그 추가
   aws ec2 create-tags \
     --resources subnet-12345678 subnet-87654321 \
     --tags Key=kubernetes.io/cluster/my-cluster,Value=shared
   ```

3. **서비스 할당량 문제 해결**:
   ```bash
   # 서비스 할당량 확인
   aws service-quotas list-service-quotas --service-code eks
   
   # 할당량 증가 요청
   aws service-quotas request-service-quota-increase \
     --service-code eks \
     --quota-code L-1194D53C \
     --desired-value 10
   ```

**일반적인 오류 메시지 및 해결 방법:**

1. **IAM 권한 부족**:
   - 오류: "User: arn:aws:iam::123456789012:user/myuser is not authorized to perform: eks:CreateCluster"
   - 해결: 필요한 IAM 권한 추가

2. **VPC 서브넷 문제**:
   - 오류: "Cannot create cluster 'my-cluster' because us-west-2a, the targeted availability zone, does not have sufficient capacity to support the cluster. Retry after some time or try other availability zones."
   - 해결: 다른 가용 영역의 서브넷 사용 또는 새 서브넷 생성

3. **서비스 할당량 초과**:
   - 오류: "Account cannot create more EKS clusters in region us-west-2. Current limit is 5"
   - 해결: 서비스 할당량 증가 요청 또는 불필요한 클러스터 삭제

**모범 사례:**

1. **클러스터 생성 전 준비 사항**:
   - 필요한 IAM 권한 확인
   - 적절한 VPC 및 서브넷 구성
   - 서비스 할당량 확인

2. **체계적인 문제 해결 접근 방식**:
   - 오류 메시지 분석
   - AWS CloudTrail 로그 확인
   - 단계별 구성 요소 검증

3. **자동화된 인프라 구성**:
   - AWS CloudFormation 또는 Terraform 사용
   - eksctl과 같은 도구 활용
   - 인프라 구성 버전 관리

**실제 구현 예시:**

1. **eksctl을 사용한 클러스터 생성 문제 해결**:
   ```bash
   # 디버그 모드로 클러스터 생성
   eksctl create cluster --name my-cluster --region us-west-2 --verbose 4
   
   # 클러스터 생성 상태 확인
   eksctl get cluster --name my-cluster --region us-west-2
   ```

2. **AWS CLI를 사용한 클러스터 생성 문제 해결**:
   ```bash
   # 클러스터 생성 시도
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
     --resources-vpc-config subnetIds=subnet-12345678,subnet-87654321,securityGroupIds=sg-12345678
   
   # 클러스터 상태 확인
   aws eks describe-cluster --name my-cluster
   ```

3. **Terraform을 사용한 클러스터 생성 문제 해결**:
   ```hcl
   # EKS 클러스터 정의
   resource "aws_eks_cluster" "main" {
     name     = "my-cluster"
     role_arn = aws_iam_role.eks_cluster.arn
     
     vpc_config {
       subnet_ids         = var.subnet_ids
       security_group_ids = [aws_security_group.eks_cluster.id]
     }
     
     # 의존성 명시
     depends_on = [
       aws_iam_role_policy_attachment.eks_cluster_policy,
       aws_iam_role_policy_attachment.eks_service_policy
     ]
   }
   
   # 오류 발생 시 디버그 출력
   output "cluster_status" {
     value = aws_eks_cluster.main.status
   }
   ```

다른 옵션들의 문제점:
- **A. 클러스터 이름이 고유한지 확인**: 클러스터 이름이 고유하지 않으면 오류가 발생할 수 있지만, 이는 가장 일반적인 실패 원인이 아닙니다.
- **C. 다른 리전에서 다시 시도**: 문제의 근본 원인을 해결하지 않고 회피하는 방법이며, 다른 리전에서도 동일한 문제가 발생할 수 있습니다.
- **D. 더 큰 인스턴스 유형 선택**: 인스턴스 유형은 노드 그룹에 적용되며, 클러스터 생성 자체에는 영향을 미치지 않습니다.
</details>
### 2. Amazon EKS 클러스터에서 노드가 NotReady 상태일 때 가장 효과적인 문제 해결 접근 방식은 무엇인가요?

A. 즉시 노드 종료 및 교체  
B. 노드 로그, 리소스 사용량 및 네트워크 연결 확인  
C. 클러스터 API 서버 재시작  
D. 모든 파드 삭제 및 재배포  

<details>
<summary>정답 및 설명</summary>

**정답: B. 노드 로그, 리소스 사용량 및 네트워크 연결 확인**

**설명:**
Amazon EKS 클러스터에서 노드가 NotReady 상태일 때 가장 효과적인 문제 해결 접근 방식은 노드 로그, 리소스 사용량 및 네트워크 연결을 확인하는 것입니다. 이 체계적인 접근 방식은 문제의 근본 원인을 식별하고 적절한 해결책을 적용하는 데 도움이 됩니다.

**주요 확인 사항:**

1. **노드 상태 및 이벤트 확인**:
   - 노드 상태 세부 정보
   - 노드 관련 이벤트
   - 노드 조건(conditions) 확인

2. **노드 로그 분석**:
   - kubelet 로그
   - 시스템 로그
   - 컨테이너 런타임 로그

3. **리소스 사용량 확인**:
   - CPU, 메모리, 디스크 사용량
   - 리소스 제한 및 압박
   - 시스템 프로세스 상태

4. **네트워크 연결 확인**:
   - 컨트롤 플레인과의 연결
   - DNS 해결
   - VPC 및 서브넷 구성

**문제 해결 방법:**

1. **노드 상태 및 이벤트 확인**:
   ```bash
   # 노드 상태 확인
   kubectl get nodes
   kubectl describe node <node-name>
   
   # 노드 이벤트 확인
   kubectl get events --field-selector involvedObject.name=<node-name>
   ```

2. **노드 로그 분석**:
   ```bash
   # SSH를 통한 노드 접근 (자체 관리형 노드의 경우)
   ssh ec2-user@<node-ip>
   
   # kubelet 로그 확인
   sudo journalctl -u kubelet
   
   # 시스템 로그 확인
   sudo tail -f /var/log/syslog
   
   # 컨테이너 런타임 로그 확인
   sudo journalctl -u docker  # Docker 사용 시
   sudo journalctl -u containerd  # containerd 사용 시
   ```

3. **리소스 사용량 확인**:
   ```bash
   # 노드 리소스 사용량 확인
   kubectl top node <node-name>
   
   # SSH를 통한 리소스 확인
   ssh ec2-user@<node-ip>
   
   # 디스크 사용량 확인
   df -h
   
   # 메모리 사용량 확인
   free -m
   
   # CPU 사용량 확인
   top
   ```

4. **네트워크 연결 확인**:
   ```bash
   # 노드에서 API 서버 연결 확인
   curl -k https://<api-server-endpoint>
   
   # DNS 해결 확인
   nslookup kubernetes.default.svc.cluster.local
   
   # 네트워크 인터페이스 확인
   ip addr show
   
   # 라우팅 테이블 확인
   ip route
   ```

**일반적인 NotReady 원인 및 해결 방법:**

1. **kubelet 문제**:
   - **증상**: kubelet 서비스가 실행되지 않거나 API 서버에 연결할 수 없음
   - **해결 방법**:
     ```bash
     # kubelet 서비스 상태 확인
     sudo systemctl status kubelet
     
     # kubelet 서비스 재시작
     sudo systemctl restart kubelet
     
     # kubelet 구성 확인
     sudo cat /etc/kubernetes/kubelet/kubelet-config.json
     ```

2. **네트워크 문제**:
   - **증상**: 노드가 컨트롤 플레인과 통신할 수 없음
   - **해결 방법**:
     ```bash
     # 보안 그룹 확인
     aws ec2 describe-security-groups --group-ids sg-12345678
     
     # 라우팅 테이블 확인
     aws ec2 describe-route-tables --route-table-ids rtb-12345678
     
     # VPC CNI 파드 상태 확인
     kubectl get pods -n kube-system -l k8s-app=aws-node
     kubectl logs -n kube-system -l k8s-app=aws-node
     ```

3. **리소스 부족**:
   - **증상**: 노드의 CPU, 메모리 또는 디스크 공간 부족
   - **해결 방법**:
     ```bash
     # 디스크 공간 확보
     sudo du -sh /var/log/*
     sudo journalctl --vacuum-time=1d
     
     # 불필요한 컨테이너 및 이미지 정리
     docker system prune -af  # Docker 사용 시
     ```

4. **인증서 문제**:
   - **증상**: 인증서 만료 또는 불일치
   - **해결 방법**:
     ```bash
     # 인증서 확인
     sudo ls -la /etc/kubernetes/pki/
     
     # 인증서 갱신 (자체 관리형 노드의 경우)
     sudo kubeadm alpha certs renew all
     
     # 관리형 노드 그룹의 경우 노드 교체
     eksctl replace nodegroup --cluster=my-cluster --name=my-nodegroup
     ```

**모범 사례:**

1. **체계적인 문제 해결 접근 방식**:
   - 증상 식별 및 문서화
   - 관련 로그 및 이벤트 수집
   - 가능한 원인 체계적 검증

2. **노드 상태 모니터링 구현**:
   - CloudWatch 경보 설정
   - 노드 상태 대시보드 구성
   - 자동화된 알림 시스템

3. **자동 복구 메커니즘 구현**:
   - 자체 복구 노드 그룹 구성
   - 상태 확인 및 자동 교체
   - 장애 노드 자동 드레이닝

**실제 구현 예시:**

1. **노드 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # EKS 노드 문제 해결 스크립트
   
   NODE_NAME=$1
   
   if [ -z "$NODE_NAME" ]; then
     echo "노드 이름을 지정하세요."
     exit 1
   fi
   
   echo "=== 노드 $NODE_NAME 문제 해결 ==="
   
   # 노드 상태 확인
   echo "=== 노드 상태 확인 ==="
   kubectl get node $NODE_NAME -o wide
   kubectl describe node $NODE_NAME
   
   # 노드 이벤트 확인
   echo
   echo "=== 노드 이벤트 확인 ==="
   kubectl get events --field-selector involvedObject.name=$NODE_NAME --sort-by='.lastTimestamp'
   
   # 노드 파드 확인
   echo
   echo "=== 노드 파드 확인 ==="
   kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=$NODE_NAME
   
   # 시스템 파드 로그 확인
   echo
   echo "=== 시스템 파드 로그 확인 ==="
   NODE_IP=$(kubectl get node $NODE_NAME -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')
   KUBE_PROXY_POD=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide | grep $NODE_IP | awk '{print $1}')
   AWS_NODE_POD=$(kubectl get pods -n kube-system -l k8s-app=aws-node -o wide | grep $NODE_IP | awk '{print $1}')
   
   if [ -n "$KUBE_PROXY_POD" ]; then
     echo "kube-proxy 로그:"
     kubectl logs -n kube-system $KUBE_PROXY_POD --tail=50
   fi
   
   if [ -n "$AWS_NODE_POD" ]; then
     echo
     echo "aws-node (VPC CNI) 로그:"
     kubectl logs -n kube-system $AWS_NODE_POD --tail=50
   fi
   
   # 노드 접근 방법 안내
   echo
   echo "=== 노드 접근 방법 ==="
   echo "노드에 직접 접근하려면 다음 명령을 사용하세요:"
   echo "aws ssm start-session --target <instance-id>"
   echo "또는"
   echo "ssh ec2-user@$NODE_IP  # SSH 키 및 보안 그룹 구성 필요"
   
   echo
   echo "=== 문제 해결 완료 ==="
   ```

2. **Terraform을 사용한 자체 복구 노드 그룹 구성**:
   ```hcl
   # 자체 복구 노드 그룹
   resource "aws_eks_node_group" "self_healing" {
     cluster_name    = aws_eks_cluster.main.name
     node_group_name = "self-healing"
     node_role_arn   = aws_iam_role.node_role.arn
     subnet_ids      = var.private_subnet_ids
     
     scaling_config {
       desired_size = 3
       min_size     = 3
       max_size     = 6
     }
     
     # 자체 복구 설정
     update_config {
       max_unavailable = 1
     }
     
     # 상태 확인 설정
     health_check {
       type = "EKS"
     }
     
     # 자동 스케일링 그룹 태그
     tags = {
       "k8s.io/cluster-autoscaler/enabled" = "true"
       "k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
     }
   }
   ```

3. **CloudWatch 경보 및 자동화된 복구 구성**:
   ```bash
   # CloudWatch 경보 생성
   aws cloudwatch put-metric-alarm \
     --alarm-name EKS-Node-NotReady \
     --metric-name NodeNotReady \
     --namespace AWS/EKS \
     --statistic Maximum \
     --period 60 \
     --threshold 0 \
     --comparison-operator GreaterThanThreshold \
     --dimensions Name=ClusterName,Value=my-cluster \
     --evaluation-periods 3 \
     --alarm-actions arn:aws:sns:us-west-2:123456789012:eks-alerts
   
   # AWS Lambda 함수를 사용한 자동 복구
   aws lambda create-function \
     --function-name EKS-Node-Recovery \
     --runtime python3.9 \
     --role arn:aws:iam::123456789012:role/EKS-Node-Recovery-Role \
     --handler index.handler \
     --zip-file fileb://node-recovery.zip
   ```

다른 옵션들의 문제점:
- **A. 즉시 노드 종료 및 교체**: 문제의 근본 원인을 파악하지 않고 노드를 교체하면 동일한 문제가 새 노드에서도 발생할 수 있으며, 진단 정보가 손실됩니다.
- **C. 클러스터 API 서버 재시작**: API 서버는 노드 상태와 직접적인 관련이 없으며, API 서버 재시작은 클러스터 전체에 영향을 미칠 수 있습니다.
- **D. 모든 파드 삭제 및 재배포**: 파드를 삭제해도 노드 자체의 문제는 해결되지 않으며, 불필요한 서비스 중단을 초래할 수 있습니다.
</details>
### 3. Amazon EKS 클러스터에서 파드가 "ImagePullBackOff" 상태일 때 가장 가능성 높은 원인과 해결 방법은 무엇인가요?

A. 파드 리소스 제한 초과 / 리소스 제한 증가  
B. 이미지 이름 오류 또는 인증 문제 / 이미지 이름 확인 및 이미지 풀 시크릿 구성  
C. 노드 디스크 공간 부족 / 디스크 공간 확보  
D. 네트워크 정책 제한 / 네트워크 정책 수정  

<details>
<summary>정답 및 설명</summary>

**정답: B. 이미지 이름 오류 또는 인증 문제 / 이미지 이름 확인 및 이미지 풀 시크릿 구성**

**설명:**
Amazon EKS 클러스터에서 파드가 "ImagePullBackOff" 상태일 때 가장 가능성 높은 원인은 이미지 이름 오류 또는 인증 문제입니다. 이 문제를 해결하기 위해서는 이미지 이름을 확인하고 필요한 경우 이미지 풀 시크릿을 구성해야 합니다.

**주요 원인 및 해결 방법:**

1. **이미지 이름 오류**:
   - 잘못된 이미지 이름 또는 태그
   - 존재하지 않는 이미지
   - 레지스트리 URL 오류

   **해결 방법**:
   ```bash
   # 파드 정의 확인
   kubectl describe pod <pod-name>
   
   # 이미지 이름 및 태그 수정
   kubectl edit deployment <deployment-name>
   # 또는
   kubectl set image deployment/<deployment-name> container-name=image:tag
   ```

2. **프라이빗 레지스트리 인증 문제**:
   - 인증 자격 증명 누락
   - 만료된 자격 증명
   - 권한 부족

   **해결 방법**:
   ```bash
   # Docker 레지스트리 시크릿 생성
   kubectl create secret docker-registry regcred \
     --docker-server=<registry-server> \
     --docker-username=<username> \
     --docker-password=<password> \
     --docker-email=<email>
   
   # 파드 또는 서비스 계정에 시크릿 연결
   kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "regcred"}]}'
   # 또는
   kubectl patch pod <pod-name> -p '{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}'
   ```

3. **Amazon ECR 인증 문제**:
   - ECR 권한 부족
   - 만료된 토큰
   - 크로스 계정 액세스 문제

   **해결 방법**:
   ```bash
   # ECR 인증 토큰 가져오기
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com
   
   # ECR 풀 시크릿 생성
   TOKEN=$(aws ecr get-authorization-token --output text --query 'authorizationData[].authorizationToken')
   echo $TOKEN | base64 -d | cut -d: -f2 > password.txt
   
   kubectl create secret docker-registry ecr-secret \
     --docker-server=123456789012.dkr.ecr.us-west-2.amazonaws.com \
     --docker-username=AWS \
     --docker-password="$(cat password.txt)" \
     --docker-email=no-reply@example.com
   
   rm password.txt
   ```

4. **네트워크 연결 문제**:
   - 레지스트리에 대한 네트워크 액세스 제한
   - DNS 해결 문제
   - 프록시 구성 문제

   **해결 방법**:
   ```bash
   # 노드에서 레지스트리 연결 확인
   ssh ec2-user@<node-ip>
   curl -v https://<registry-url>
   
   # DNS 해결 확인
   nslookup <registry-url>
   
   # 프라이빗 레지스트리에 대한 VPC 엔드포인트 구성
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.dkr \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 \
     --security-group-ids sg-12345678
   ```

**문제 해결 단계:**

1. **파드 상태 및 이벤트 확인**:
   ```bash
   # 파드 상태 확인
   kubectl get pod <pod-name>
   
   # 파드 세부 정보 및 이벤트 확인
   kubectl describe pod <pod-name>
   ```

2. **이미지 이름 및 레지스트리 확인**:
   ```bash
   # 이미지 이름 확인
   kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].image}'
   
   # 이미지 존재 여부 확인
   docker pull <image-name>  # 로컬 환경에서
   # 또는
   aws ecr describe-images \
     --repository-name <repository-name> \
     --image-ids imageTag=<tag>  # ECR의 경우
   ```

3. **인증 구성 확인**:
   ```bash
   # 서비스 계정 및 이미지 풀 시크릿 확인
   kubectl get serviceaccount default -o yaml
   
   # 시크릿 내용 확인
   kubectl get secret <secret-name> -o yaml
   ```

4. **임시 해결책 적용**:
   ```bash
   # 로컬에서 이미지 가져오기 및 노드로 전송 (긴급 상황용)
   docker pull <image-name>
   docker save <image-name> -o image.tar
   scp image.tar ec2-user@<node-ip>:~/
   ssh ec2-user@<node-ip> "docker load -i image.tar"
   ```

**모범 사례:**

1. **이미지 태그 관리**:
   - 특정 태그 대신 다이제스트 사용
   - `latest` 태그 사용 지양
   - 버전 관리 전략 구현

2. **이미지 풀 시크릿 관리**:
   - 서비스 계정에 시크릿 연결
   - 시크릿 정기적 갱신
   - 시크릿 관리 자동화

3. **이미지 레지스트리 접근성 보장**:
   - 프라이빗 레지스트리의 경우 VPC 엔드포인트 구성
   - 네트워크 정책 및 보안 그룹 구성
   - 이미지 캐싱 고려

4. **ECR 사용 시 모범 사례**:
   - IAM 역할 기반 인증 사용
   - 자동 토큰 갱신 구현
   - 이미지 스캔 및 수명 주기 정책 구성

**실제 구현 예시:**

1. **ECR 인증을 위한 Kubernetes 작업**:
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: ecr-credential-updater
     namespace: kube-system
   spec:
     schedule: "*/6 * * * *"  # 6시간마다 실행
     jobTemplate:
       spec:
         template:
           spec:
             serviceAccountName: ecr-credential-updater
             containers:
             - name: ecr-credential-updater
               image: amazon/aws-cli:latest
               command:
               - /bin/sh
               - -c
               - |
                 TOKEN=$(aws ecr get-authorization-token --output text --query 'authorizationData[].authorizationToken')
                 echo $TOKEN | base64 -d | cut -d: -f2 > /tmp/docker-password
                 kubectl delete secret ecr-secret --ignore-not-found
                 kubectl create secret docker-registry ecr-secret \
                   --docker-server=123456789012.dkr.ecr.us-west-2.amazonaws.com \
                   --docker-username=AWS \
                   --docker-password="$(cat /tmp/docker-password)" \
                   --docker-email=no-reply@example.com
                 kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "ecr-secret"}]}'
               env:
               - name: AWS_REGION
                 value: us-west-2
             restartPolicy: OnFailure
   ```

2. **Terraform을 사용한 ECR 풀 시크릿 구성**:
   ```hcl
   # ECR 리포지토리
   resource "aws_ecr_repository" "app" {
     name = "my-app"
   }
   
   # ECR 풀 시크릿을 위한 IAM 역할
   resource "aws_iam_role" "ecr_pull" {
     name = "ecr-pull-role"
     
     assume_role_policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Principal = {
           Service = "ec2.amazonaws.com"
         },
         Action = "sts:AssumeRole"
       }]
     })
   }
   
   # ECR 풀 정책
   resource "aws_iam_policy" "ecr_pull" {
     name = "ecr-pull-policy"
     
     policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Action = [
           "ecr:GetDownloadUrlForLayer",
           "ecr:BatchGetImage",
           "ecr:BatchCheckLayerAvailability",
           "ecr:GetAuthorizationToken"
         ],
         Resource = "*"
       }]
     })
   }
   
   # 정책 연결
   resource "aws_iam_role_policy_attachment" "ecr_pull" {
     role       = aws_iam_role.ecr_pull.name
     policy_arn = aws_iam_policy.ecr_pull.arn
   }
   ```

3. **이미지 풀 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # 이미지 풀 문제 해결 스크립트
   
   POD_NAME=$1
   
   if [ -z "$POD_NAME" ]; then
     echo "파드 이름을 지정하세요."
     exit 1
   fi
   
   echo "=== 파드 $POD_NAME 이미지 풀 문제 해결 ==="
   
   # 파드 상태 확인
   echo "=== 파드 상태 확인 ==="
   kubectl get pod $POD_NAME
   
   # 파드 이벤트 확인
   echo
   echo "=== 파드 이벤트 확인 ==="
   kubectl describe pod $POD_NAME | grep -A 20 "Events:"
   
   # 이미지 정보 확인
   echo
   echo "=== 이미지 정보 확인 ==="
   IMAGE=$(kubectl get pod $POD_NAME -o jsonpath='{.spec.containers[0].image}')
   echo "이미지: $IMAGE"
   
   # 이미지 레지스트리 확인
   REGISTRY=$(echo $IMAGE | cut -d/ -f1)
   echo "레지스트리: $REGISTRY"
   
   # 이미지 풀 시크릿 확인
   echo
   echo "=== 이미지 풀 시크릿 확인 ==="
   SA_NAME=$(kubectl get pod $POD_NAME -o jsonpath='{.spec.serviceAccountName}')
   if [ -z "$SA_NAME" ]; then
     SA_NAME="default"
   fi
   echo "서비스 계정: $SA_NAME"
   
   kubectl get serviceaccount $SA_NAME -o yaml
   
   # ECR 레지스트리인 경우
   if [[ $REGISTRY == *.dkr.ecr.*.amazonaws.com ]]; then
     echo
     echo "=== ECR 레지스트리 확인 ==="
     REGION=$(echo $REGISTRY | cut -d. -f4)
     ACCOUNT=$(echo $REGISTRY | cut -d. -f1)
     REPO=$(echo $IMAGE | cut -d/ -f2- | cut -d: -f1)
     TAG=$(echo $IMAGE | cut -d: -f2)
     
     echo "리전: $REGION"
     echo "계정: $ACCOUNT"
     echo "리포지토리: $REPO"
     echo "태그: $TAG"
     
     echo
     echo "ECR 인증 토큰 확인:"
     aws ecr get-authorization-token --region $REGION
   fi
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   echo "1. 이미지 이름과 태그가 올바른지 확인하세요."
   echo "2. 프라이빗 레지스트리의 경우 이미지 풀 시크릿을 구성하세요."
   echo "3. ECR의 경우 노드 IAM 역할에 ECR 액세스 권한이 있는지 확인하세요."
   echo "4. 네트워크 연결을 확인하세요."
   ```

다른 옵션들의 문제점:
- **A. 파드 리소스 제한 초과 / 리소스 제한 증가**: 리소스 제한 문제는 일반적으로 "ImagePullBackOff"가 아닌 "OOMKilled" 또는 "Pending" 상태를 유발합니다.
- **C. 노드 디스크 공간 부족 / 디스크 공간 확보**: 디스크 공간 부족은 "ImagePullBackOff"의 원인이 될 수 있지만, 이 경우 일반적으로 노드 이벤트에 디스크 공간 관련 오류가 표시되며, 가장 일반적인 원인은 아닙니다.
- **D. 네트워크 정책 제한 / 네트워크 정책 수정**: 네트워크 정책은 파드 간 통신에 영향을 미치지만, 일반적으로 이미지 풀 문제의 주요 원인은 아닙니다.
</details>
### 4. Amazon EKS 클러스터에서 서비스가 파드에 트래픽을 라우팅하지 않을 때 가장 효과적인 문제 해결 단계는 무엇인가요?

A. 즉시 새 서비스 생성  
B. 서비스 및 파드 레이블, 엔드포인트, 네트워크 정책 확인  
C. 모든 파드 재시작  
D. 클러스터 API 서버 재시작  

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 및 파드 레이블, 엔드포인트, 네트워크 정책 확인**

**설명:**
Amazon EKS 클러스터에서 서비스가 파드에 트래픽을 라우팅하지 않을 때 가장 효과적인 문제 해결 단계는 서비스 및 파드 레이블, 엔드포인트, 네트워크 정책을 확인하는 것입니다. 이 체계적인 접근 방식은 서비스 디스커버리 및 트래픽 라우팅 문제의 근본 원인을 식별하는 데 도움이 됩니다.

**주요 확인 사항:**

1. **서비스 및 파드 레이블 확인**:
   - 서비스 셀렉터와 파드 레이블 일치 여부
   - 레이블 구문 및 오타
   - 네임스페이스 확인

2. **엔드포인트 확인**:
   - 서비스 엔드포인트 생성 여부
   - 엔드포인트 IP 및 파드 IP 일치 여부
   - Ready 상태의 파드 수

3. **네트워크 정책 확인**:
   - 트래픽을 제한하는 네트워크 정책 존재 여부
   - 인그레스 및 이그레스 규칙
   - 네임스페이스 간 통신 제한

4. **서비스 및 파드 상태 확인**:
   - 파드 실행 및 준비 상태
   - 서비스 유형 및 포트 구성
   - 상태 확인 구성

**문제 해결 방법:**

1. **서비스 및 파드 레이블 확인**:
   ```bash
   # 서비스 셀렉터 확인
   kubectl get service <service-name> -o yaml | grep -A 5 selector
   
   # 파드 레이블 확인
   kubectl get pods --show-labels
   
   # 셀렉터와 일치하는 파드 확인
   kubectl get pods -l key=value
   ```

2. **엔드포인트 확인**:
   ```bash
   # 서비스 엔드포인트 확인
   kubectl get endpoints <service-name>
   
   # 엔드포인트 세부 정보 확인
   kubectl describe endpoints <service-name>
   
   # 엔드포인트 및 파드 IP 비교
   kubectl get pods -o wide
   ```

3. **네트워크 정책 확인**:
   ```bash
   # 네트워크 정책 확인
   kubectl get networkpolicy
   
   # 네트워크 정책 세부 정보 확인
   kubectl describe networkpolicy <policy-name>
   
   # 임시로 네트워크 정책 비활성화
   kubectl delete networkpolicy <policy-name>
   ```

4. **서비스 연결 테스트**:
   ```bash
   # 임시 디버그 파드 생성
   kubectl run -it --rm debug --image=nicolaka/netshoot -- bash
   
   # 서비스 DNS 해결 테스트
   nslookup <service-name>.<namespace>.svc.cluster.local
   
   # 서비스 연결 테스트
   curl <service-ip>:<port>
   
   # 파드 직접 연결 테스트
   curl <pod-ip>:<container-port>
   ```

**일반적인 서비스 문제 및 해결 방법:**

1. **레이블 불일치**:
   - **증상**: 서비스 엔드포인트가 비어 있음
   - **해결 방법**:
     ```bash
     # 서비스 셀렉터 수정
     kubectl edit service <service-name>
     # 또는
     kubectl patch service <service-name> -p '{"spec":{"selector":{"app":"correct-label"}}}'
     
     # 파드 레이블 수정
     kubectl label pods <pod-name> app=correct-label --overwrite
     ```

2. **포트 구성 오류**:
   - **증상**: 서비스는 연결되지만 애플리케이션 응답 없음
   - **해결 방법**:
     ```bash
     # 서비스 포트 구성 확인
     kubectl describe service <service-name>
     
     # 파드 컨테이너 포트 확인
     kubectl describe pod <pod-name>
     
     # 서비스 포트 수정
     kubectl edit service <service-name>
     ```

3. **네트워크 정책 제한**:
   - **증상**: 특정 소스에서만 서비스에 액세스할 수 없음
   - **해결 방법**:
     ```bash
     # 네트워크 정책 수정
     kubectl edit networkpolicy <policy-name>
     
     # 허용 규칙 추가
     kubectl apply -f - <<EOF
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-service-access
       namespace: <namespace>
     spec:
       podSelector:
         matchLabels:
           app: <app-label>
       ingress:
       - from:
         - namespaceSelector: {}
       policyTypes:
       - Ingress
     EOF
     ```

4. **CoreDNS 문제**:
   - **증상**: 서비스 이름 해결 실패
   - **해결 방법**:
     ```bash
     # CoreDNS 파드 확인
     kubectl get pods -n kube-system -l k8s-app=kube-dns
     
     # CoreDNS 로그 확인
     kubectl logs -n kube-system -l k8s-app=kube-dns
     
     # CoreDNS 구성 확인
     kubectl get configmap -n kube-system coredns -o yaml
     ```

**모범 사례:**

1. **체계적인 문제 해결 접근 방식**:
   - 서비스 구성부터 시작하여 파드, 네트워크 정책, DNS 순으로 확인
   - 각 단계에서 명확한 증거 수집
   - 한 번에 하나의 변수만 변경

2. **서비스 디버깅 도구 활용**:
   ```bash
   # kube-proxy 로그 확인
   kubectl logs -n kube-system -l k8s-app=kube-proxy
   
   # iptables 규칙 확인 (자체 관리형 노드의 경우)
   ssh ec2-user@<node-ip>
   sudo iptables-save | grep <service-ip>
   
   # DNS 디버깅
   kubectl run -it --rm dnsutils --image=tutum/dnsutils -- bash
   ```

3. **서비스 모니터링 구현**:
   - 서비스 엔드포인트 상태 모니터링
   - 서비스 연결 상태 확인
   - 트래픽 흐름 시각화

4. **서비스 구성 관리**:
   - 일관된 레이블 지정 전략
   - 명시적 포트 이름 지정
   - 서비스 문서화

**실제 구현 예시:**

1. **서비스 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # 서비스 문제 해결 스크립트
   
   SERVICE_NAME=$1
   NAMESPACE=${2:-default}
   
   if [ -z "$SERVICE_NAME" ]; then
     echo "서비스 이름을 지정하세요."
     exit 1
   fi
   
   echo "=== 서비스 $SERVICE_NAME 문제 해결 ==="
   echo "네임스페이스: $NAMESPACE"
   
   # 서비스 확인
   echo
   echo "=== 서비스 세부 정보 ==="
   kubectl get service $SERVICE_NAME -n $NAMESPACE -o wide
   
   # 서비스 셀렉터 확인
   echo
   echo "=== 서비스 셀렉터 ==="
   SELECTOR=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector}' | jq -r 'to_entries | map("\(.key)=\(.value)") | join(",")')
   echo "셀렉터: $SELECTOR"
   
   # 일치하는 파드 확인
   echo
   echo "=== 일치하는 파드 ==="
   if [ -n "$SELECTOR" ]; then
     kubectl get pods -n $NAMESPACE -l $SELECTOR -o wide
     POD_COUNT=$(kubectl get pods -n $NAMESPACE -l $SELECTOR --no-headers | wc -l)
     echo "일치하는 파드 수: $POD_COUNT"
   else
     echo "서비스에 셀렉터가 없습니다."
   fi
   
   # 엔드포인트 확인
   echo
   echo "=== 엔드포인트 ==="
   kubectl get endpoints $SERVICE_NAME -n $NAMESPACE
   kubectl describe endpoints $SERVICE_NAME -n $NAMESPACE
   
   # 네트워크 정책 확인
   echo
   echo "=== 네트워크 정책 ==="
   NETPOL_COUNT=$(kubectl get networkpolicy -n $NAMESPACE --no-headers | wc -l)
   if [ $NETPOL_COUNT -gt 0 ]; then
     kubectl get networkpolicy -n $NAMESPACE
     echo
     echo "네트워크 정책이 서비스 액세스를 제한할 수 있습니다."
   else
     echo "네임스페이스에 네트워크 정책이 없습니다."
   fi
   
   # 서비스 테스트
   echo
   echo "=== 서비스 테스트 ==="
   SERVICE_IP=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
   SERVICE_PORT=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}')
   
   echo "서비스 IP: $SERVICE_IP"
   echo "서비스 포트: $SERVICE_PORT"
   echo
   echo "서비스 연결 테스트를 위해 다음 명령을 실행하세요:"
   echo "kubectl run -it --rm debug --image=nicolaka/netshoot -- bash"
   echo "curl $SERVICE_IP:$SERVICE_PORT"
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   if [ $POD_COUNT -eq 0 ]; then
     echo "- 서비스 셀렉터와 일치하는 파드가 없습니다. 파드 레이블 또는 서비스 셀렉터를 확인하세요."
   fi
   
   READY_PODS=$(kubectl get pods -n $NAMESPACE -l $SELECTOR -o jsonpath='{.items[?(@.status.phase=="Running")].status.containerStatuses[0].ready}' | grep -o "true" | wc -l)
   if [ $READY_PODS -eq 0 ] && [ $POD_COUNT -gt 0 ]; then
     echo "- 일치하는 파드가 있지만 Ready 상태가 아닙니다. 파드 상태를 확인하세요."
   fi
   
   if [ $NETPOL_COUNT -gt 0 ]; then
     echo "- 네트워크 정책이 서비스 액세스를 제한할 수 있습니다. 네트워크 정책을 검토하세요."
   fi
   
   echo "- 서비스 포트와 파드 컨테이너 포트가 일치하는지 확인하세요."
   echo "- CoreDNS가 올바르게 작동하는지 확인하세요."
   ```

2. **Terraform을 사용한 서비스 및 파드 구성**:
   ```hcl
   # 서비스 정의
   resource "kubernetes_service" "app" {
     metadata {
       name      = "app-service"
       namespace = kubernetes_namespace.app.metadata[0].name
     }
     
     spec {
       selector = {
         app = kubernetes_deployment.app.spec[0].template[0].metadata[0].labels.app
       }
       
       port {
         name        = "http"
         port        = 80
         target_port = 8080
       }
       
       type = "ClusterIP"
     }
   }
   
   # 배포 정의
   resource "kubernetes_deployment" "app" {
     metadata {
       name      = "app-deployment"
       namespace = kubernetes_namespace.app.metadata[0].name
     }
     
     spec {
       replicas = 3
       
       selector {
         match_labels = {
           app = "my-app"
         }
       }
       
       template {
         metadata {
           labels = {
             app = "my-app"
           }
         }
         
         spec {
           container {
             name  = "app"
             image = "my-app:latest"
             
             port {
               container_port = 8080
             }
             
             readiness_probe {
               http_get {
                 path = "/health"
                 port = 8080
               }
               
               initial_delay_seconds = 10
               period_seconds        = 5
             }
           }
         }
       }
     }
   }
   ```

3. **서비스 연결 테스트 작업**:
   ```yaml
   apiVersion: batch/v1
   kind: Job
   metadata:
     name: service-test
   spec:
     template:
       spec:
         containers:
         - name: service-test
           image: nicolaka/netshoot
           command:
           - /bin/bash
           - -c
           - |
             echo "=== DNS 해결 테스트 ==="
             nslookup app-service
             nslookup app-service.default.svc.cluster.local
             
             echo
             echo "=== 서비스 연결 테스트 ==="
             curl -v app-service:80
             
             echo
             echo "=== 직접 파드 연결 테스트 ==="
             for POD_IP in $(kubectl get pods -l app=my-app -o jsonpath='{.items[*].status.podIP}'); do
               echo "테스트 파드 IP: $POD_IP"
               curl -v $POD_IP:8080
             done
         restartPolicy: Never
   ```

다른 옵션들의 문제점:
- **A. 즉시 새 서비스 생성**: 문제의 근본 원인을 파악하지 않고 새 서비스를 생성하면 동일한 문제가 발생할 수 있으며, 진단 정보가 손실됩니다.
- **C. 모든 파드 재시작**: 파드를 재시작해도 서비스 구성 문제는 해결되지 않으며, 불필요한 서비스 중단을 초래할 수 있습니다.
- **D. 클러스터 API 서버 재시작**: API 서버 재시작은 극단적인 조치이며, 서비스 라우팅 문제와 직접적인 관련이 없습니다. 또한 클러스터 전체에 영향을 미칠 수 있습니다.
</details>
### 5. Amazon EKS 클러스터에서 PersistentVolumeClaim이 "Pending" 상태로 유지될 때 가장 가능성 높은 원인과 해결 방법은 무엇인가요?

A. 노드 리소스 부족 / 더 큰 노드 추가  
B. 스토리지 클래스 문제 또는 볼륨 프로비저닝 권한 부족 / 스토리지 클래스 확인 및 IAM 권한 구성  
C. 파드 우선순위 낮음 / 파드 우선순위 증가  
D. 클러스터 자동 스케일러 비활성화 / 자동 스케일러 활성화  

<details>
<summary>정답 및 설명</summary>

**정답: B. 스토리지 클래스 문제 또는 볼륨 프로비저닝 권한 부족 / 스토리지 클래스 확인 및 IAM 권한 구성**

**설명:**
Amazon EKS 클러스터에서 PersistentVolumeClaim(PVC)이 "Pending" 상태로 유지될 때 가장 가능성 높은 원인은 스토리지 클래스 문제 또는 볼륨 프로비저닝 권한 부족입니다. 이 문제를 해결하기 위해서는 스토리지 클래스를 확인하고 필요한 IAM 권한을 구성해야 합니다.

**주요 원인 및 해결 방법:**

1. **스토리지 클래스 문제**:
   - 존재하지 않는 스토리지 클래스 지정
   - 스토리지 클래스 파라미터 오류
   - 프로비저너 구성 문제

   **해결 방법**:
   ```bash
   # 스토리지 클래스 확인
   kubectl get storageclass
   
   # 스토리지 클래스 세부 정보 확인
   kubectl describe storageclass <storage-class-name>
   
   # 기본 스토리지 클래스 설정
   kubectl patch storageclass <storage-class-name> -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
   ```

2. **IAM 권한 부족**:
   - EBS CSI 드라이버 서비스 계정 권한 부족
   - 노드 IAM 역할 권한 부족
   - 크로스 계정 액세스 문제

   **해결 방법**:
   ```bash
   # EBS CSI 드라이버 서비스 계정 확인
   kubectl get serviceaccount -n kube-system ebs-csi-controller-sa
   
   # IAM 역할 연결 확인
   kubectl describe serviceaccount -n kube-system ebs-csi-controller-sa
   
   # 필요한 IAM 정책 연결
   aws iam attach-role-policy \
     --role-name <role-name> \
     --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
   ```

3. **볼륨 바인딩 모드 문제**:
   - 가용 영역 불일치
   - WaitForFirstConsumer 설정 문제
   - 토폴로지 제약 조건

   **해결 방법**:
   ```bash
   # 볼륨 바인딩 모드 확인
   kubectl get storageclass <storage-class-name> -o jsonpath='{.volumeBindingMode}'
   
   # 스토리지 클래스 수정
   kubectl patch storageclass <storage-class-name> -p '{"volumeBindingMode":"WaitForFirstConsumer"}'
   
   # 새 스토리지 클래스 생성
   kubectl apply -f - <<EOF
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-sc-waitforfirstconsumer
   provisioner: ebs.csi.aws.com
   volumeBindingMode: WaitForFirstConsumer
   parameters:
     type: gp3
   EOF
   ```

4. **CSI 드라이버 문제**:
   - CSI 드라이버 미설치 또는 오류
   - 버전 호환성 문제
   - 컨트롤러 파드 오류

   **해결 방법**:
   ```bash
   # CSI 드라이버 파드 확인
   kubectl get pods -n kube-system -l app=ebs-csi-controller
   
   # CSI 드라이버 로그 확인
   kubectl logs -n kube-system -l app=ebs-csi-controller -c ebs-plugin
   
   # CSI 드라이버 재설치
   eksctl create addon --name aws-ebs-csi-driver --cluster <cluster-name> --force
   ```
**문제 해결 단계:**

1. **PVC 상태 및 이벤트 확인**:
   ```bash
   # PVC 상태 확인
   kubectl get pvc <pvc-name>
   
   # PVC 세부 정보 및 이벤트 확인
   kubectl describe pvc <pvc-name>
   ```

2. **스토리지 클래스 확인**:
   ```bash
   # 스토리지 클래스 목록 확인
   kubectl get storageclass
   
   # PVC에서 사용하는 스토리지 클래스 확인
   kubectl get pvc <pvc-name> -o jsonpath='{.spec.storageClassName}'
   
   # 스토리지 클래스 세부 정보 확인
   kubectl describe storageclass <storage-class-name>
   ```

3. **CSI 드라이버 확인**:
   ```bash
   # CSI 드라이버 파드 확인
   kubectl get pods -n kube-system -l app=ebs-csi-controller
   
   # CSI 드라이버 로그 확인
   kubectl logs -n kube-system -l app=ebs-csi-controller -c ebs-plugin
   ```

4. **IAM 권한 확인**:
   ```bash
   # 서비스 계정 확인
   kubectl get serviceaccount -n kube-system ebs-csi-controller-sa -o yaml
   
   # IRSA 구성 확인
   aws eks describe-addon \
     --cluster-name <cluster-name> \
     --addon-name aws-ebs-csi-driver \
     --query "addon.serviceAccountRoleArn"
   ```

**모범 사례:**

1. **적절한 스토리지 클래스 구성**:
   ```yaml
   # gp3 스토리지 클래스 예시
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
     annotations:
       storageclass.kubernetes.io/is-default-class: "true"
   provisioner: ebs.csi.aws.com
   volumeBindingMode: WaitForFirstConsumer
   parameters:
     type: gp3
     encrypted: "true"
   allowVolumeExpansion: true
   ```

2. **IRSA(IAM Roles for Service Accounts) 구성**:
   ```bash
   # EBS CSI 드라이버용 IRSA 생성
   eksctl create iamserviceaccount \
     --name ebs-csi-controller-sa \
     --namespace kube-system \
     --cluster <cluster-name> \
     --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
     --approve \
     --override-existing-serviceaccounts
   ```

3. **PVC 요청 최적화**:
   ```yaml
   # 최적화된 PVC 예시
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: my-pvc
   spec:
     accessModes:
       - ReadWriteOnce
     storageClassName: ebs-gp3
     resources:
       requests:
         storage: 10Gi
   ```

4. **볼륨 바인딩 모드 최적화**:
   - WaitForFirstConsumer 사용
   - 파드와 PV의 가용 영역 일치 보장
   - 토폴로지 인식 프로비저닝 활용
**실제 구현 예시:**

1. **PVC 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # PVC 문제 해결 스크립트
   
   PVC_NAME=$1
   NAMESPACE=${2:-default}
   
   if [ -z "$PVC_NAME" ]; then
     echo "PVC 이름을 지정하세요."
     exit 1
   fi
   
   echo "=== PVC $PVC_NAME 문제 해결 ==="
   echo "네임스페이스: $NAMESPACE"
   
   # PVC 상태 확인
   echo
   echo "=== PVC 상태 ==="
   kubectl get pvc $PVC_NAME -n $NAMESPACE
   
   # PVC 세부 정보 확인
   echo
   echo "=== PVC 세부 정보 ==="
   kubectl describe pvc $PVC_NAME -n $NAMESPACE
   
   # 스토리지 클래스 확인
   SC_NAME=$(kubectl get pvc $PVC_NAME -n $NAMESPACE -o jsonpath='{.spec.storageClassName}')
   if [ -z "$SC_NAME" ]; then
     SC_NAME="<default>"
   fi
   
   echo
   echo "=== 스토리지 클래스: $SC_NAME ==="
   kubectl get storageclass $SC_NAME
   kubectl describe storageclass $SC_NAME
   
   # CSI 드라이버 확인
   echo
   echo "=== CSI 드라이버 상태 ==="
   kubectl get pods -n kube-system -l app=ebs-csi-controller
   
   # CSI 드라이버 로그 확인
   echo
   echo "=== CSI 드라이버 로그 ==="
   CSI_POD=$(kubectl get pods -n kube-system -l app=ebs-csi-controller -o jsonpath='{.items[0].metadata.name}')
   if [ -n "$CSI_POD" ]; then
     kubectl logs -n kube-system $CSI_POD -c ebs-plugin --tail=20
   else
     echo "CSI 드라이버 파드를 찾을 수 없습니다."
   fi
   
   # 바인딩된 파드 확인
   echo
   echo "=== 바인딩된 파드 ==="
   kubectl get pods -n $NAMESPACE --field-selector=spec.volumes.persistentVolumeClaim.claimName=$PVC_NAME
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   PVC_STATUS=$(kubectl get pvc $PVC_NAME -n $NAMESPACE -o jsonpath='{.status.phase}')
   
   if [ "$PVC_STATUS" == "Pending" ]; then
     echo "1. 스토리지 클래스가 올바르게 구성되어 있는지 확인하세요."
     echo "2. EBS CSI 드라이버가 설치되어 있고 올바르게 작동하는지 확인하세요."
     echo "3. 서비스 계정에 볼륨 프로비저닝에 필요한 IAM 권한이 있는지 확인하세요."
     echo "4. 볼륨 바인딩 모드가 WaitForFirstConsumer인 경우 파드가 생성되었는지 확인하세요."
   elif [ "$PVC_STATUS" == "Bound" ]; then
     echo "PVC가 이미 바인딩되어 있습니다. 파드가 볼륨을 마운트할 수 있는지 확인하세요."
   else
     echo "PVC 상태를 확인하고 이벤트를 검토하세요."
   fi
   ```

2. **Terraform을 사용한 EBS CSI 드라이버 구성**:
   ```hcl
   # EBS CSI 드라이버용 IAM 역할
   module "ebs_csi_irsa" {
     source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
     version = "~> 5.0"
     
     role_name             = "ebs-csi-controller-role"
     attach_ebs_csi_policy = true
     
     oidc_providers = {
       main = {
         provider_arn               = module.eks.oidc_provider_arn
         namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
       }
     }
   }
   
   # EBS CSI 드라이버 애드온
   resource "aws_eks_addon" "ebs_csi_driver" {
     cluster_name             = module.eks.cluster_name
     addon_name               = "aws-ebs-csi-driver"
     addon_version            = "v1.16.0-eksbuild.1"
     service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
     
     configuration_values = jsonencode({
       controller = {
         extraVolumeTags = {
           Environment = "production"
           Terraform   = "true"
         }
       }
     })
   }
   
   # 스토리지 클래스
   resource "kubernetes_storage_class" "ebs_gp3" {
     metadata {
       name = "ebs-gp3"
       annotations = {
         "storageclass.kubernetes.io/is-default-class" = "true"
       }
     }
     
     storage_provisioner    = "ebs.csi.aws.com"
     volume_binding_mode    = "WaitForFirstConsumer"
     allow_volume_expansion = true
     
     parameters = {
       type      = "gp3"
       encrypted = "true"
     }
   }
   ```

3. **PVC 디버깅 작업**:
   ```yaml
   apiVersion: batch/v1
   kind: Job
   metadata:
     name: pvc-debug
   spec:
     template:
       spec:
         containers:
         - name: debug
           image: amazon/aws-cli:latest
           command:
           - /bin/bash
           - -c
           - |
             echo "=== AWS 계정 정보 ==="
             aws sts get-caller-identity
             
             echo
             echo "=== EBS 볼륨 목록 ==="
             aws ec2 describe-volumes \
               --filters "Name=tag:kubernetes.io/cluster/my-cluster,Values=owned" \
               --query "Volumes[*].{ID:VolumeId,Size:Size,Type:VolumeType,State:State,AZ:AvailabilityZone}"
             
             echo
             echo "=== 가용 영역 정보 ==="
             NODE_AZ=$(kubectl get nodes -o jsonpath='{.items[0].metadata.labels.topology\.kubernetes\.io/zone}')
             echo "노드 가용 영역: $NODE_AZ"
             
             echo
             echo "=== 볼륨 생성 테스트 ==="
             aws ec2 create-volume \
               --availability-zone $NODE_AZ \
               --size 1 \
               --volume-type gp3 \
               --tag-specifications 'ResourceType=volume,Tags=[{Key=test,Value=pvc-debug}]'
             
             sleep 10
             
             aws ec2 describe-volumes \
               --filters "Name=tag:test,Values=pvc-debug" \
               --query "Volumes[*].{ID:VolumeId,State:State}"
         restartPolicy: Never
   ```

다른 옵션들의 문제점:
- **A. 노드 리소스 부족 / 더 큰 노드 추가**: 노드 리소스 부족은 일반적으로 파드가 "Pending" 상태가 되는 원인이지만, PVC가 "Pending" 상태인 것과는 직접적인 관련이 없습니다.
- **C. 파드 우선순위 낮음 / 파드 우선순위 증가**: 파드 우선순위는 스케줄링 결정에 영향을 미치지만, PVC 프로비저닝에는 영향을 미치지 않습니다.
- **D. 클러스터 자동 스케일러 비활성화 / 자동 스케일러 활성화**: 자동 스케일러는 노드 수를 조정하는 데 도움이 되지만, PVC 프로비저닝 문제와는 직접적인 관련이 없습니다.
</details>
### 6. Amazon EKS 클러스터에서 자동 스케일링이 예상대로 작동하지 않을 때 가장 효과적인 문제 해결 접근 방식은 무엇인가요?

A. 모든 파드에 더 많은 리소스 할당  
B. 수동으로 노드 추가  
C. HPA, CA, VPA 구성, 메트릭, 권한 및 이벤트 확인  
D. 클러스터 재생성  

<details>
<summary>정답 및 설명</summary>

**정답: C. HPA, CA, VPA 구성, 메트릭, 권한 및 이벤트 확인**

**설명:**
Amazon EKS 클러스터에서 자동 스케일링이 예상대로 작동하지 않을 때 가장 효과적인 문제 해결 접근 방식은 HPA(Horizontal Pod Autoscaler), CA(Cluster Autoscaler), VPA(Vertical Pod Autoscaler) 구성, 메트릭, 권한 및 이벤트를 확인하는 것입니다. 이 체계적인 접근 방식은 자동 스케일링 문제의 근본 원인을 식별하고 해결하는 데 도움이 됩니다.

**주요 확인 사항:**

1. **HPA(Horizontal Pod Autoscaler) 확인**:
   - HPA 구성 및 상태
   - 메트릭 가용성 및 값
   - 스케일링 제한 및 동작

2. **CA(Cluster Autoscaler) 확인**:
   - CA 배포 및 구성
   - IAM 권한 및 역할
   - 노드 그룹 태그 및 설정

3. **VPA(Vertical Pod Autoscaler) 확인**:
   - VPA 구성 및 모드
   - 리소스 권장 사항
   - 업데이트 정책

4. **메트릭 및 이벤트 확인**:
   - 메트릭 서버 상태
   - CloudWatch 메트릭 가용성
   - 자동 스케일링 이벤트 및 로그

**문제 해결 방법:**

1. **HPA 문제 해결**:
   ```bash
   # HPA 상태 확인
   kubectl get hpa
   
   # HPA 세부 정보 확인
   kubectl describe hpa <hpa-name>
   
   # 메트릭 확인
   kubectl get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods"
   
   # 메트릭 서버 상태 확인
   kubectl get pods -n kube-system -l k8s-app=metrics-server
   kubectl logs -n kube-system -l k8s-app=metrics-server
   ```

2. **CA 문제 해결**:
   ```bash
   # CA 파드 상태 확인
   kubectl get pods -n kube-system -l app=cluster-autoscaler
   
   # CA 로그 확인
   kubectl logs -n kube-system -l app=cluster-autoscaler
   
   # 노드 그룹 태그 확인
   aws autoscaling describe-auto-scaling-groups \
     --auto-scaling-group-names <asg-name> \
     --query "AutoScalingGroups[].Tags"
   
   # CA 이벤트 확인
   kubectl get events --sort-by='.lastTimestamp' | grep -i "cluster-autoscaler"
   ```

3. **VPA 문제 해결**:
   ```bash
   # VPA 상태 확인
   kubectl get vpa
   
   # VPA 세부 정보 확인
   kubectl describe vpa <vpa-name>
   
   # VPA 권장 사항 확인
   kubectl get vpa <vpa-name> -o jsonpath='{.status.recommendation}'
   
   # VPA 컴포넌트 상태 확인
   kubectl get pods -n kube-system -l app=vpa-recommender
   ```

4. **메트릭 및 권한 문제 해결**:
   ```bash
   # 메트릭 서버 상태 확인
   kubectl get apiservices v1beta1.metrics.k8s.io
   
   # IAM 역할 및 정책 확인
   aws iam get-role --role-name <role-name>
   aws iam list-attached-role-policies --role-name <role-name>
   
   # CloudWatch 메트릭 확인
   aws cloudwatch list-metrics \
     --namespace AWS/EC2 \
     --metric-name CPUUtilization \
     --dimensions Name=AutoScalingGroupName,Value=<asg-name>
   ```

**일반적인 자동 스케일링 문제 및 해결 방법:**

1. **HPA 메트릭 문제**:
   - **증상**: HPA가 스케일링 결정을 내리지 않음
   - **원인**: 메트릭 서버 오류 또는 메트릭 가용성 문제
   - **해결 방법**:
     ```bash
     # 메트릭 서버 재설치
     kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
     
     # 메트릭 확인
     kubectl top pods
     kubectl top nodes
     ```

2. **CA 권한 문제**:
   - **증상**: CA가 노드를 추가하지 못함
   - **원인**: IAM 권한 부족 또는 ASG 태그 누락
   - **해결 방법**:
     ```bash
     # CA IAM 정책 연결
     aws iam attach-role-policy \
       --role-name <role-name> \
       --policy-arn arn:aws:iam::aws:policy/AutoScalingFullAccess
     
     # ASG 태그 추가
     aws autoscaling create-or-update-tags \
       --tags "ResourceId=<asg-name>,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true" \
       "ResourceId=<asg-name>,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/<cluster-name>,Value=owned,PropagateAtLaunch=true"
     ```

3. **스케일링 제한 문제**:
   - **증상**: 스케일링이 특정 값을 초과하지 않음
   - **원인**: HPA 또는 CA 제한 설정
   - **해결 방법**:
     ```bash
     # HPA 최대 복제본 수 수정
     kubectl patch hpa <hpa-name> -p '{"spec":{"maxReplicas":20}}'
     
     # ASG 최대 크기 수정
     aws autoscaling update-auto-scaling-group \
       --auto-scaling-group-name <asg-name> \
       --max-size 10
     ```

4. **VPA 업데이트 모드 문제**:
   - **증상**: VPA가 리소스를 업데이트하지 않음
   - **원인**: 업데이트 모드가 "Off" 또는 "Initial"로 설정됨
   - **해결 방법**:
     ```bash
     # VPA 업데이트 모드 수정
     kubectl patch vpa <vpa-name> -p '{"spec":{"updatePolicy":{"updateMode":"Auto"}}}'
     ```

**모범 사례:**

1. **체계적인 문제 해결 접근 방식**:
   - 각 자동 스케일링 구성 요소 개별 확인
   - 로그 및 이벤트 분석
   - 단계별 문제 해결

2. **자동 스케일링 모니터링 구현**:
   - 자동 스케일링 활동 모니터링
   - 스케일링 이벤트 알림 설정
   - 스케일링 메트릭 대시보드 구성

3. **자동 스케일링 구성 최적화**:
   - 워크로드 특성에 맞는 스케일링 임계값 설정
   - 스케일링 동작 및 쿨다운 기간 조정
   - 비용과 성능 균형 유지

4. **다중 자동 스케일링 구성 요소 통합**:
   - HPA, CA, VPA 조합 사용
   - 구성 요소 간 충돌 방지
   - 일관된 스케일링 전략 구현

**실제 구현 예시:**

1. **자동 스케일링 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # 자동 스케일링 문제 해결 스크립트
   
   CLUSTER_NAME=$1
   
   if [ -z "$CLUSTER_NAME" ]; then
     echo "클러스터 이름을 지정하세요."
     exit 1
   fi
   
   echo "=== 자동 스케일링 문제 해결 ==="
   echo "클러스터: $CLUSTER_NAME"
   
   # HPA 확인
   echo
   echo "=== HPA 상태 ==="
   kubectl get hpa --all-namespaces
   
   # 문제가 있는 HPA 확인
   PROBLEM_HPA=$(kubectl get hpa --all-namespaces -o json | jq -r '.items[] | select(.status.currentReplicas != .status.desiredReplicas) | .metadata.name')
   
   if [ -n "$PROBLEM_HPA" ]; then
     echo
     echo "=== 문제가 있는 HPA 세부 정보 ==="
     kubectl describe hpa $PROBLEM_HPA
   fi
   
   # 메트릭 서버 확인
   echo
   echo "=== 메트릭 서버 상태 ==="
   kubectl get apiservices v1beta1.metrics.k8s.io
   kubectl get pods -n kube-system -l k8s-app=metrics-server
   
   # 메트릭 확인
   echo
   echo "=== 메트릭 가용성 ==="
   kubectl top nodes || echo "노드 메트릭을 가져올 수 없습니다."
   kubectl top pods || echo "파드 메트릭을 가져올 수 없습니다."
   
   # CA 확인
   echo
   echo "=== Cluster Autoscaler 상태 ==="
   kubectl get pods -n kube-system -l app=cluster-autoscaler
   
   # CA 로그 확인
   CA_POD=$(kubectl get pods -n kube-system -l app=cluster-autoscaler -o jsonpath='{.items[0].metadata.name}')
   if [ -n "$CA_POD" ]; then
     echo
     echo "=== Cluster Autoscaler 로그 ==="
     kubectl logs -n kube-system $CA_POD --tail=50 | grep -i "scale"
   else
     echo "Cluster Autoscaler 파드를 찾을 수 없습니다."
   fi
   
   # ASG 확인
   echo
   echo "=== Auto Scaling Group 확인 ==="
   ASG_NAMES=$(aws autoscaling describe-auto-scaling-groups --query "AutoScalingGroups[?contains(Tags[?Key=='kubernetes.io/cluster/$CLUSTER_NAME'].Value, 'owned')].AutoScalingGroupName" --output text)
   
   for ASG in $ASG_NAMES; do
     echo "ASG: $ASG"
     aws autoscaling describe-auto-scaling-groups \
       --auto-scaling-group-names $ASG \
       --query "AutoScalingGroups[].{MinSize:MinSize,MaxSize:MaxSize,DesiredCapacity:DesiredCapacity,Instances:Instances[].LifecycleState}" \
       --output table
     
     echo "ASG 태그:"
     aws autoscaling describe-auto-scaling-groups \
       --auto-scaling-group-names $ASG \
       --query "AutoScalingGroups[].Tags[?Key=='k8s.io/cluster-autoscaler/enabled' || Key=='k8s.io/cluster-autoscaler/$CLUSTER_NAME']"
   done
   
   # VPA 확인
   echo
   echo "=== VPA 상태 ==="
   kubectl get vpa --all-namespaces || echo "VPA CRD가 설치되지 않았습니다."
   
   # 자동 스케일링 이벤트 확인
   echo
   echo "=== 자동 스케일링 이벤트 ==="
   kubectl get events --sort-by='.lastTimestamp' | grep -i -E "autoscal|hpa|scale"
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   if ! kubectl get apiservices v1beta1.metrics.k8s.io -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' | grep -q "True"; then
     echo "- 메트릭 서버가 사용 가능하지 않습니다. 메트릭 서버를 설치하거나 문제를 해결하세요."
   fi
   
   if [ -z "$CA_POD" ]; then
     echo "- Cluster Autoscaler가 설치되지 않았습니다. Cluster Autoscaler를 설치하세요."
   fi
   
   for ASG in $ASG_NAMES; do
     if ! aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $ASG --query "AutoScalingGroups[].Tags[?Key=='k8s.io/cluster-autoscaler/enabled'].Value" --output text | grep -q "true"; then
       echo "- ASG $ASG에 Cluster Autoscaler 태그가 없습니다. 필요한 태그를 추가하세요."
     fi
   done
   
   echo "- HPA 구성을 검토하고 적절한 메트릭 및 임계값을 설정하세요."
   echo "- 노드 그룹 IAM 역할에 필요한 권한이 있는지 확인하세요."
   ```

2. **Terraform을 사용한 자동 스케일링 구성**:
   ```hcl
   # Cluster Autoscaler IAM 역할
   module "cluster_autoscaler_irsa" {
     source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
     version = "~> 5.0"
     
     role_name                        = "cluster-autoscaler-role"
     attach_cluster_autoscaler_policy = true
     cluster_autoscaler_cluster_names = [module.eks.cluster_name]
     
     oidc_providers = {
       main = {
         provider_arn               = module.eks.oidc_provider_arn
         namespace_service_accounts = ["kube-system:cluster-autoscaler"]
       }
     }
   }
   
   # Cluster Autoscaler 배포
   resource "helm_release" "cluster_autoscaler" {
     name       = "cluster-autoscaler"
     repository = "https://kubernetes.github.io/autoscaler"
     chart      = "cluster-autoscaler"
     namespace  = "kube-system"
     
     set {
       name  = "autoDiscovery.clusterName"
       value = module.eks.cluster_name
     }
     
     set {
       name  = "rbac.serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
       value = module.cluster_autoscaler_irsa.iam_role_arn
     }
     
     set {
       name  = "extraArgs.scale-down-delay-after-add"
       value = "2m"
     }
     
     set {
       name  = "extraArgs.scale-down-unneeded-time"
       value = "5m"
     }
   }
   
   # 메트릭 서버 배포
   resource "helm_release" "metrics_server" {
     name       = "metrics-server"
     repository = "https://kubernetes-sigs.github.io/metrics-server/"
     chart      = "metrics-server"
     namespace  = "kube-system"
     
     set {
       name  = "args[0]"
       value = "--kubelet-preferred-address-types=InternalIP"
     }
     
     set {
       name  = "args[1]"
       value = "--kubelet-insecure-tls"
     }
   }
   
   # HPA 예시
   resource "kubernetes_horizontal_pod_autoscaler_v2" "app" {
     metadata {
       name      = "app-hpa"
       namespace = kubernetes_namespace.app.metadata[0].name
     }
     
     spec {
       scale_target_ref {
         api_version = "apps/v1"
         kind        = "Deployment"
         name        = kubernetes_deployment.app.metadata[0].name
       }
       
       min_replicas = 2
       max_replicas = 10
       
       metric {
         type = "Resource"
         resource {
           name = "cpu"
           target {
             type                = "Utilization"
             average_utilization = 70
           }
         }
       }
       
       metric {
         type = "Resource"
         resource {
           name = "memory"
           target {
             type                = "Utilization"
             average_utilization = 80
           }
         }
       }
       
       behavior {
         scale_up {
           stabilization_window_seconds = 60
           select_policy                = "Max"
           policy {
             type           = "Pods"
             value          = 4
             period_seconds = 60
           }
           policy {
             type           = "Percent"
             value          = 100
             period_seconds = 60
           }
         }
         
         scale_down {
           stabilization_window_seconds = 300
           select_policy                = "Min"
           policy {
             type           = "Percent"
             value          = 10
             period_seconds = 60
           }
         }
       }
     }
   }
   ```

3. **자동 스케일링 모니터링 대시보드**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: autoscaling-dashboard
     namespace: monitoring
   data:
     autoscaling-dashboard.json: |
       {
         "title": "Autoscaling Dashboard",
         "panels": [
           {
             "title": "HPA Scaling",
             "type": "graph",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "kube_horizontalpodautoscaler_status_current_replicas",
                 "legendFormat": "Current - {{horizontalpodautoscaler}}",
                 "refId": "A"
               },
               {
                 "expr": "kube_horizontalpodautoscaler_spec_min_replicas",
                 "legendFormat": "Min - {{horizontalpodautoscaler}}",
                 "refId": "B"
               },
               {
                 "expr": "kube_horizontalpodautoscaler_spec_max_replicas",
                 "legendFormat": "Max - {{horizontalpodautoscaler}}",
                 "refId": "C"
               },
               {
                 "expr": "kube_horizontalpodautoscaler_status_desired_replicas",
                 "legendFormat": "Desired - {{horizontalpodautoscaler}}",
                 "refId": "D"
               }
             ]
           },
           {
             "title": "Node Count",
             "type": "graph",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(kube_node_info)",
                 "legendFormat": "Total Nodes",
                 "refId": "A"
               }
             ]
           },
           {
             "title": "CPU Utilization",
             "type": "graph",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(rate(container_cpu_usage_seconds_total{container!=\"\"}[5m])) by (pod)",
                 "legendFormat": "{{pod}}",
                 "refId": "A"
               }
             ]
           },
           {
             "title": "Memory Utilization",
             "type": "graph",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(container_memory_working_set_bytes{container!=\"\"}) by (pod)",
                 "legendFormat": "{{pod}}",
                 "refId": "A"
               }
             ]
           }
         ]
       }
   ```

다른 옵션들의 문제점:
- **A. 모든 파드에 더 많은 리소스 할당**: 이는 근본 원인을 해결하지 않고 자원을 낭비할 수 있으며, 자동 스케일링 문제의 실제 원인을 파악하지 못합니다.
- **B. 수동으로 노드 추가**: 이는 임시 해결책일 뿐이며, 자동 스케일링 시스템의 근본적인 문제를 해결하지 않습니다.
- **D. 클러스터 재생성**: 이는 극단적인 조치이며, 문제의 근본 원인을 파악하지 못하고 불필요한 다운타임과 작업을 초래합니다.
</details>
### 7. Amazon EKS 클러스터에서 네트워크 정책이 예상대로 작동하지 않을 때 가장 효과적인 문제 해결 접근 방식은 무엇인가요?

A. 모든 네트워크 정책 삭제 및 기본값 사용  
B. 클러스터 CNI 플러그인, 네트워크 정책 구성, 로그 및 이벤트 확인  
C. 모든 파드에 hostNetwork: true 설정  
D. 클러스터 VPC 재구성  

<details>
<summary>정답 및 설명</summary>

**정답: B. 클러스터 CNI 플러그인, 네트워크 정책 구성, 로그 및 이벤트 확인**

**설명:**
Amazon EKS 클러스터에서 네트워크 정책이 예상대로 작동하지 않을 때 가장 효과적인 문제 해결 접근 방식은 클러스터 CNI 플러그인, 네트워크 정책 구성, 로그 및 이벤트를 체계적으로 확인하는 것입니다. 이 접근 방식은 네트워크 정책 문제의 근본 원인을 식별하고 해결하는 데 도움이 됩니다.

**주요 확인 사항:**

1. **CNI 플러그인 확인**:
   - 사용 중인 CNI 플러그인 유형 (AWS VPC CNI, Calico, Cilium 등)
   - CNI 플러그인 버전 및 호환성
   - 네트워크 정책 지원 여부

2. **네트워크 정책 구성 확인**:
   - 네트워크 정책 구문 및 선택기
   - 정책 우선순위 및 충돌
   - 네임스페이스 및 라벨 선택기

3. **로그 및 이벤트 확인**:
   - CNI 플러그인 로그
   - 네트워크 정책 컨트롤러 로그
   - 관련 이벤트 및 오류 메시지

4. **네트워크 연결 테스트**:
   - 파드 간 연결 테스트
   - 서비스 연결 테스트
   - 외부 연결 테스트

**문제 해결 방법:**

1. **CNI 플러그인 확인**:
   ```bash
   # CNI 플러그인 파드 확인
   kubectl get pods -n kube-system -l k8s-app=aws-node  # AWS VPC CNI
   kubectl get pods -n kube-system -l k8s-app=calico-node  # Calico
   kubectl get pods -n kube-system -l k8s-app=cilium  # Cilium
   
   # CNI 플러그인 로그 확인
   kubectl logs -n kube-system -l k8s-app=aws-node
   kubectl logs -n kube-system -l k8s-app=calico-node
   kubectl logs -n kube-system -l k8s-app=cilium
   
   # CNI 구성 확인
   kubectl describe daemonset -n kube-system aws-node
   kubectl describe daemonset -n kube-system calico-node
   kubectl describe daemonset -n kube-system cilium
   ```

2. **네트워크 정책 확인**:
   ```bash
   # 네트워크 정책 목록 확인
   kubectl get networkpolicies --all-namespaces
   
   # 특정 네트워크 정책 세부 정보 확인
   kubectl describe networkpolicy <policy-name> -n <namespace>
   
   # 네트워크 정책 YAML 확인
   kubectl get networkpolicy <policy-name> -n <namespace> -o yaml
   ```

3. **파드 네트워크 정보 확인**:
   ```bash
   # 파드 IP 및 노드 정보 확인
   kubectl get pods -o wide
   
   # 파드 네트워크 인터페이스 확인
   kubectl exec -it <pod-name> -- ip addr
   
   # 파드 라우팅 테이블 확인
   kubectl exec -it <pod-name> -- ip route
   ```

4. **네트워크 연결 테스트**:
   ```bash
   # 디버그 파드 생성
   kubectl run network-debug --rm -it --image=nicolaka/netshoot -- /bin/bash
   
   # 파드 간 연결 테스트
   ping <target-pod-ip>
   nc -zv <target-pod-ip> <port>
   
   # DNS 확인 테스트
   nslookup <service-name>.<namespace>.svc.cluster.local
   
   # 패킷 캡처
   tcpdump -i eth0 -n
   ```

**일반적인 네트워크 정책 문제 및 해결 방법:**

1. **CNI 플러그인 호환성 문제**:
   - **증상**: 네트워크 정책이 적용되지 않음
   - **원인**: 사용 중인 CNI 플러그인이 네트워크 정책을 지원하지 않음
   - **해결 방법**:
     ```bash
     # AWS VPC CNI에 Calico 정책 엔진 추가
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
     kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
     
     # 또는 Cilium으로 전환
     helm repo add cilium https://helm.cilium.io/
     helm install cilium cilium/cilium --namespace kube-system
     ```

2. **네트워크 정책 선택기 문제**:
   - **증상**: 정책이 예상 파드에 적용되지 않음
   - **원인**: 잘못된 라벨 선택기 또는 네임스페이스 선택기
   - **해결 방법**:
     ```bash
     # 파드 라벨 확인
     kubectl get pods --show-labels
     
     # 네트워크 정책 수정
     kubectl edit networkpolicy <policy-name> -n <namespace>
     ```

3. **정책 충돌 문제**:
   - **증상**: 예상치 못한 연결 차단 또는 허용
   - **원인**: 여러 정책 간의 충돌 또는 우선순위 문제
   - **해결 방법**:
     ```bash
     # 모든 네트워크 정책 검토
     kubectl get networkpolicies --all-namespaces -o yaml
     
     # 정책 단순화 또는 재구성
     kubectl apply -f updated-network-policy.yaml
     ```

4. **CNI 플러그인 버그 또는 구성 오류**:
   - **증상**: 간헐적인 연결 문제 또는 일관되지 않은 동작
   - **원인**: CNI 플러그인 버그 또는 잘못된 구성
   - **해결 방법**:
     ```bash
     # CNI 플러그인 업데이트
     kubectl set image daemonset/aws-node -n kube-system aws-node=<new-image-version>
     
     # CNI 구성 확인 및 수정
     kubectl edit configmap -n kube-system aws-node
     ```

**모범 사례:**

1. **체계적인 네트워크 정책 설계**:
   - 기본 거부 정책으로 시작
   - 필요한 연결만 명시적으로 허용
   - 네임스페이스 및 라벨 기반 정책 사용

2. **네트워크 정책 테스트 및 검증**:
   - 정책 적용 전 테스트
   - 연결 테스트 자동화
   - 점진적인 정책 적용

3. **네트워크 모니터링 및 로깅**:
   - 네트워크 트래픽 모니터링
   - 연결 거부 로깅
   - 네트워크 성능 모니터링

4. **CNI 플러그인 선택 및 구성**:
   - 워크로드 요구 사항에 맞는 CNI 선택
   - 최신 버전 유지
   - 적절한 리소스 할당

**실제 구현 예시:**

1. **기본 네트워크 정책 구성**:
   ```yaml
   # 기본 거부 정책
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
     namespace: production
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   
   # 특정 애플리케이션 허용 정책
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: api-allow
     namespace: production
   spec:
     podSelector:
       matchLabels:
         app: api
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: frontend
         podSelector:
           matchLabels:
             app: web
       ports:
       - protocol: TCP
         port: 8080
     egress:
     - to:
       - namespaceSelector:
           matchLabels:
             name: database
         podSelector:
           matchLabels:
             app: db
       ports:
       - protocol: TCP
         port: 5432
     - to:
       - namespaceSelector: {}
         podSelector:
           matchLabels:
             k8s-app: kube-dns
       ports:
       - protocol: UDP
         port: 53
       - protocol: TCP
         port: 53
   ```

2. **네트워크 정책 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # 네트워크 정책 문제 해결 스크립트
   
   NAMESPACE=$1
   POD_NAME=$2
   
   if [ -z "$NAMESPACE" ] || [ -z "$POD_NAME" ]; then
     echo "사용법: $0 <네임스페이스> <파드_이름>"
     exit 1
   fi
   
   echo "=== 네트워크 정책 문제 해결 ==="
   echo "네임스페이스: $NAMESPACE"
   echo "파드: $POD_NAME"
   
   # 파드 정보 확인
   echo
   echo "=== 파드 정보 ==="
   kubectl get pod $POD_NAME -n $NAMESPACE -o wide
   
   # 파드 라벨 확인
   echo
   echo "=== 파드 라벨 ==="
   kubectl get pod $POD_NAME -n $NAMESPACE --show-labels
   
   # 네임스페이스 라벨 확인
   echo
   echo "=== 네임스페이스 라벨 ==="
   kubectl get namespace $NAMESPACE --show-labels
   
   # 네트워크 정책 확인
   echo
   echo "=== 네임스페이스의 네트워크 정책 ==="
   kubectl get networkpolicies -n $NAMESPACE
   
   # 모든 네트워크 정책 세부 정보
   echo
   echo "=== 네트워크 정책 세부 정보 ==="
   POLICIES=$(kubectl get networkpolicies -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')
   for POLICY in $POLICIES; do
     echo
     echo "정책: $POLICY"
     kubectl describe networkpolicy $POLICY -n $NAMESPACE
   done
   
   # CNI 플러그인 확인
   echo
   echo "=== CNI 플러그인 확인 ==="
   if kubectl get pods -n kube-system -l k8s-app=aws-node &>/dev/null; then
     echo "AWS VPC CNI 사용 중"
     kubectl get pods -n kube-system -l k8s-app=aws-node
     
     # Calico 정책 엔진 확인
     if kubectl get pods -n kube-system -l k8s-app=calico-node &>/dev/null; then
       echo
       echo "Calico 정책 엔진 사용 중"
       kubectl get pods -n kube-system -l k8s-app=calico-node
     else
       echo
       echo "Calico 정책 엔진이 설치되지 않았습니다. AWS VPC CNI는 기본적으로 네트워크 정책을 지원하지 않습니다."
     fi
   elif kubectl get pods -n kube-system -l k8s-app=cilium &>/dev/null; then
     echo "Cilium CNI 사용 중"
     kubectl get pods -n kube-system -l k8s-app=cilium
   else
     echo "알 수 없는 CNI 플러그인 사용 중"
   fi
   
   # 연결 테스트
   echo
   echo "=== 연결 테스트 ==="
   echo "디버그 파드 생성 중..."
   kubectl run network-debug -n $NAMESPACE --rm -it --image=nicolaka/netshoot -- /bin/bash -c "
     echo '=== 파드 IP 정보 ===';
     ip addr;
     echo;
     echo '=== 라우팅 테이블 ===';
     ip route;
     echo;
     echo '=== DNS 확인 테스트 ===';
     nslookup kubernetes.default.svc.cluster.local;
     echo;
     echo '=== 대상 파드 연결 테스트 ===';
     POD_IP=\$(kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.status.podIP}');
     echo \"파드 IP: \$POD_IP\";
     ping -c 3 \$POD_IP || echo '핑 실패';
     echo;
     echo '=== 서비스 연결 테스트 ===';
     SERVICES=\$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}');
     for SVC in \$SERVICES; do
       echo \"서비스: \$SVC\";
       SVC_PORT=\$(kubectl get svc \$SVC -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}');
       nc -zv \$SVC.\$NAMESPACE.svc.cluster.local \$SVC_PORT -w 2 || echo '연결 실패';
     done;
   "
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   if ! kubectl get pods -n kube-system -l k8s-app=calico-node &>/dev/null && ! kubectl get pods -n kube-system -l k8s-app=cilium &>/dev/null; then
     echo "- 네트워크 정책을 지원하는 CNI 플러그인이 설치되지 않았습니다. Calico 또는 Cilium을 설치하세요."
   fi
   
   echo "- 파드 및 네임스페이스 라벨이 네트워크 정책 선택기와 일치하는지 확인하세요."
   echo "- 네트워크 정책이 필요한 모든 트래픽(인그레스 및 이그레스)을 허용하는지 확인하세요."
   echo "- 여러 네트워크 정책 간의 충돌이 있는지 확인하세요."
   echo "- CNI 플러그인 로그에서 오류를 확인하세요."
   ```

3. **Terraform을 사용한 네트워크 정책 구성**:
   ```hcl
   # Calico 정책 엔진 설치
   resource "helm_release" "calico" {
     name       = "calico"
     repository = "https://docs.projectcalico.org/charts"
     chart      = "tigera-operator"
     namespace  = "tigera-operator"
     create_namespace = true
     
     set {
       name  = "installation.kubernetesProvider"
       value = "EKS"
     }
   }
   
   # 기본 네트워크 정책
   resource "kubernetes_network_policy" "default_deny" {
     metadata {
       name      = "default-deny"
       namespace = kubernetes_namespace.app.metadata[0].name
     }
     
     spec {
       pod_selector {}
       
       policy_types = ["Ingress", "Egress"]
     }
   }
   
   # 애플리케이션별 네트워크 정책
   resource "kubernetes_network_policy" "app_policy" {
     metadata {
       name      = "app-network-policy"
       namespace = kubernetes_namespace.app.metadata[0].name
     }
     
     spec {
       pod_selector {
         match_labels = {
           app = "api"
         }
       }
       
       policy_types = ["Ingress", "Egress"]
       
       ingress {
         from {
           namespace_selector {
             match_labels = {
               name = "frontend"
             }
           }
           
           pod_selector {
             match_labels = {
               app = "web"
             }
           }
         }
         
         ports {
           port     = "8080"
           protocol = "TCP"
         }
       }
       
       egress {
         to {
           namespace_selector {
             match_labels = {
               name = "database"
             }
           }
           
           pod_selector {
             match_labels = {
               app = "db"
             }
           }
         }
         
         ports {
           port     = "5432"
           protocol = "TCP"
         }
       }
       
       # DNS 액세스 허용
       egress {
         to {
           namespace_selector {}
           
           pod_selector {
             match_labels = {
               "k8s-app" = "kube-dns"
             }
           }
         }
         
         ports {
           port     = "53"
           protocol = "UDP"
         }
         
         ports {
           port     = "53"
           protocol = "TCP"
         }
       }
     }
   }
   ```

4. **네트워크 정책 모니터링 구성**:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: network-policy-dashboard
     namespace: monitoring
   data:
     network-policy-dashboard.json: |
       {
         "title": "Network Policy Monitoring",
         "panels": [
           {
             "title": "Network Policy Count",
             "type": "stat",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(kube_networkpolicy_info)",
                 "legendFormat": "Total Network Policies",
                 "refId": "A"
               }
             ]
           },
           {
             "title": "Dropped Connections",
             "type": "graph",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "sum(rate(calico_denied_packets[5m])) by (namespace)",
                 "legendFormat": "{{namespace}}",
                 "refId": "A"
               }
             ]
           },
           {
             "title": "Network Policy Events",
             "type": "table",
             "datasource": "Loki",
             "targets": [
               {
                 "expr": "{app=\"calico-node\"} |~ \"policy\"",
                 "refId": "A"
               }
             ]
           }
         ]
       }
   ```

다른 옵션들의 문제점:
- **A. 모든 네트워크 정책 삭제 및 기본값 사용**: 이는 보안 위험을 초래하고 필요한 네트워크 격리를 제거하며, 근본 원인을 해결하지 않습니다.
- **C. 모든 파드에 hostNetwork: true 설정**: 이는 네트워크 정책을 우회하고 보안 위험을 초래하며, 파드 간 격리를 제거합니다.
- **D. 클러스터 VPC 재구성**: 이는 극단적인 조치이며, 대부분의 네트워크 정책 문제는 VPC 수준이 아닌 클러스터 내부의 CNI 및 정책 구성과 관련이 있습니다.
</details>
### 8. Amazon EKS 클러스터에서 Helm 차트 배포 문제를 해결하는 가장 효과적인 접근 방식은 무엇인가요?

A. 모든 Helm 차트 삭제 및 재설치  
B. 클러스터 재생성  
C. Helm 버전, 차트 구성, 종속성, 권한 및 로그 체계적 확인  
D. 수동으로 모든 리소스 배포  

<details>
<summary>정답 및 설명</summary>

**정답: C. Helm 버전, 차트 구성, 종속성, 권한 및 로그 체계적 확인**

**설명:**
Amazon EKS 클러스터에서 Helm 차트 배포 문제를 해결하는 가장 효과적인 접근 방식은 Helm 버전, 차트 구성, 종속성, 권한 및 로그를 체계적으로 확인하는 것입니다. 이 접근 방식은 Helm 배포 문제의 근본 원인을 식별하고 해결하는 데 도움이 됩니다.

**주요 확인 사항:**

1. **Helm 버전 및 호환성 확인**:
   - Helm 클라이언트 및 Tiller(Helm 2) 버전
   - Kubernetes API 버전 호환성
   - EKS 버전 호환성

2. **차트 구성 및 값 확인**:
   - 차트 구문 오류
   - 값 파일 구성
   - 템플릿 렌더링 문제

3. **종속성 및 리포지토리 확인**:
   - 차트 종속성 가용성
   - 리포지토리 접근성
   - 차트 버전 호환성

4. **권한 및 RBAC 확인**:
   - 서비스 계정 권한
   - RBAC 규칙
   - 네임스페이스 액세스

5. **로그 및 이벤트 확인**:
   - Helm 디버그 로그
   - Kubernetes 이벤트
   - 관련 파드 로그

**문제 해결 방법:**

1. **Helm 버전 및 구성 확인**:
   ```bash
   # Helm 버전 확인
   helm version
   
   # Helm 환경 변수 확인
   env | grep HELM
   
   # Helm 플러그인 확인
   helm plugin list
   
   # Helm 리포지토리 확인
   helm repo list
   helm repo update
   ```

2. **차트 검증 및 디버깅**:
   ```bash
   # 차트 구문 검증
   helm lint ./my-chart
   
   # 템플릿 렌더링 확인
   helm template ./my-chart --debug
   
   # 차트 종속성 업데이트
   helm dependency update ./my-chart
   
   # 디버그 모드로 설치
   helm install my-release ./my-chart --debug
   ```

3. **릴리스 상태 및 기록 확인**:
   ```bash
   # 릴리스 목록 확인
   helm list -A
   
   # 실패한 릴리스 포함
   helm list -A --failed
   
   # 릴리스 상태 확인
   helm status my-release
   
   # 릴리스 기록 확인
   helm history my-release
   
   # 릴리스 세부 정보 확인
   helm get all my-release
   ```

4. **리소스 및 이벤트 확인**:
   ```bash
   # 배포된 리소스 확인
   kubectl get all -n <namespace> -l app.kubernetes.io/instance=my-release
   
   # 이벤트 확인
   kubectl get events -n <namespace> --sort-by='.lastTimestamp'
   
   # 파드 로그 확인
   kubectl logs -n <namespace> -l app.kubernetes.io/instance=my-release
   
   # 파드 상태 확인
   kubectl describe pods -n <namespace> -l app.kubernetes.io/instance=my-release
   ```

5. **권한 및 RBAC 확인**:
   ```bash
   # 서비스 계정 확인
   kubectl get serviceaccount -n <namespace>
   
   # 역할 및 역할 바인딩 확인
   kubectl get roles,rolebindings -n <namespace>
   
   # 클러스터 역할 및 바인딩 확인
   kubectl get clusterroles,clusterrolebindings -l app.kubernetes.io/instance=my-release
   
   # 서비스 계정 권한 확인
   kubectl auth can-i --list --as=system:serviceaccount:<namespace>:<serviceaccount>
   ```

**일반적인 Helm 배포 문제 및 해결 방법:**

1. **차트 구문 오류**:
   - **증상**: `helm install` 또는 `helm template` 명령이 실패함
   - **원인**: YAML 구문 오류, 잘못된 템플릿 함수 또는 변수
   - **해결 방법**:
     ```bash
     # 차트 구문 검증
     helm lint ./my-chart
     
     # 템플릿 렌더링 확인
     helm template ./my-chart --debug
     
     # 특정 값으로 템플릿 렌더링
     helm template ./my-chart --set key=value --debug
     ```

2. **종속성 문제**:
   - **증상**: 차트 설치 중 종속성 오류
   - **원인**: 누락된 종속성, 버전 불일치 또는 리포지토리 접근 문제
   - **해결 방법**:
     ```bash
     # 종속성 업데이트
     helm dependency update ./my-chart
     
     # 리포지토리 추가 및 업데이트
     helm repo add bitnami https://charts.bitnami.com/bitnami
     helm repo update
     
     # 종속성 빌드
     helm dependency build ./my-chart
     ```

3. **권한 문제**:
   - **증상**: 권한 거부 오류
   - **원인**: 부족한 RBAC 권한 또는 잘못된 서비스 계정 구성
   - **해결 방법**:
     ```bash
     # 필요한 RBAC 리소스 생성
     kubectl apply -f rbac.yaml
     
     # 서비스 계정 지정
     helm install my-release ./my-chart --service-account=my-service-account
     
     # 권한 확인
     kubectl auth can-i create deployments --as=system:serviceaccount:<namespace>:<serviceaccount>
     ```

4. **리소스 충돌**:
   - **증상**: 이미 존재하는 리소스 오류
   - **원인**: 이전 설치의 리소스가 남아 있거나 이름 충돌
   - **해결 방법**:
     ```bash
     # 기존 릴리스 제거
     helm uninstall my-release
     
     # 남은 리소스 확인 및 삭제
     kubectl get all -n <namespace> -l app.kubernetes.io/instance=my-release
     kubectl delete <resource-type> <resource-name> -n <namespace>
     
     # 다른 릴리스 이름으로 설치
     helm install new-release ./my-chart
     ```

5. **값 구성 문제**:
   - **증상**: 배포된 애플리케이션이 예상대로 작동하지 않음
   - **원인**: 잘못된 구성 값 또는 누락된 필수 값
   - **해결 방법**:
     ```bash
     # 현재 값 확인
     helm get values my-release
     
     # 기본값 확인
     helm show values ./my-chart
     
     # 값 파일로 업그레이드
     helm upgrade my-release ./my-chart -f values.yaml
     
     # 특정 값 설정
     helm upgrade my-release ./my-chart --set key=value
     ```

**모범 사례:**

1. **체계적인 문제 해결 접근 방식**:
   - 단계별 확인 및 검증
   - 로그 및 이벤트 분석
   - 증상에서 원인으로 추적

2. **Helm 차트 테스트 및 검증**:
   - 배포 전 차트 검증
   - 테스트 환경에서 먼저 테스트
   - CI/CD 파이프라인에 검증 단계 포함

3. **버전 관리 및 호환성**:
   - 호환되는 Helm 및 Kubernetes 버전 사용
   - 차트 버전 명시적 지정
   - 종속성 버전 고정

4. **문서화 및 값 관리**:
   - 차트 값 문서화
   - 환경별 값 파일 관리
   - 민감한 값에 대한 보안 관행 적용

**실제 구현 예시:**

1. **Helm 차트 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # Helm 차트 문제 해결 스크립트
   
   RELEASE_NAME=$1
   NAMESPACE=$2
   
   if [ -z "$RELEASE_NAME" ] || [ -z "$NAMESPACE" ]; then
     echo "사용법: $0 <릴리스_이름> <네임스페이스>"
     exit 1
   fi
   
   echo "=== Helm 차트 문제 해결 ==="
   echo "릴리스: $RELEASE_NAME"
   echo "네임스페이스: $NAMESPACE"
   
   # Helm 버전 확인
   echo
   echo "=== Helm 버전 ==="
   helm version
   
   # 릴리스 상태 확인
   echo
   echo "=== 릴리스 상태 ==="
   helm status $RELEASE_NAME -n $NAMESPACE || echo "릴리스를 찾을 수 없습니다."
   
   # 릴리스 기록 확인
   echo
   echo "=== 릴리스 기록 ==="
   helm history $RELEASE_NAME -n $NAMESPACE || echo "릴리스 기록을 찾을 수 없습니다."
   
   # 릴리스 값 확인
   echo
   echo "=== 릴리스 값 ==="
   helm get values $RELEASE_NAME -n $NAMESPACE || echo "릴리스 값을 찾을 수 없습니다."
   
   # 배포된 리소스 확인
   echo
   echo "=== 배포된 리소스 ==="
   kubectl get all -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME
   
   # 파드 상태 확인
   echo
   echo "=== 파드 상태 ==="
   PODS=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME -o jsonpath='{.items[*].metadata.name}')
   if [ -n "$PODS" ]; then
     for POD in $PODS; do
       echo
       echo "파드: $POD"
       kubectl describe pod $POD -n $NAMESPACE
     done
   else
     echo "파드를 찾을 수 없습니다."
   fi
   
   # 파드 로그 확인
   echo
   echo "=== 파드 로그 ==="
   if [ -n "$PODS" ]; then
     for POD in $PODS; do
       echo
       echo "파드: $POD"
       kubectl logs $POD -n $NAMESPACE --tail=50
     done
   else
     echo "파드를 찾을 수 없습니다."
   fi
   
   # 이벤트 확인
   echo
   echo "=== 관련 이벤트 ==="
   kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | grep -i $RELEASE_NAME
   
   # 서비스 계정 및 RBAC 확인
   echo
   echo "=== 서비스 계정 및 RBAC ==="
   SA=$(kubectl get deployment -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME -o jsonpath='{.items[0].spec.template.spec.serviceAccountName}')
   if [ -n "$SA" ]; then
     echo "서비스 계정: $SA"
     kubectl get serviceaccount $SA -n $NAMESPACE -o yaml
     
     echo
     echo "역할 및 역할 바인딩:"
     kubectl get roles,rolebindings -n $NAMESPACE | grep -i $SA
     
     echo
     echo "클러스터 역할 및 바인딩:"
     kubectl get clusterroles,clusterrolebindings | grep -i $SA
   else
     echo "서비스 계정을 찾을 수 없습니다."
   fi
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   if ! helm status $RELEASE_NAME -n $NAMESPACE &>/dev/null; then
     echo "- 릴리스가 존재하지 않습니다. 설치 명령을 확인하세요."
   fi
   
   if [ -z "$PODS" ]; then
     echo "- 파드가 생성되지 않았습니다. 차트 구성 및 값을 확인하세요."
   else
     FAILED_PODS=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME -o jsonpath='{.items[?(@.status.phase!="Running")].metadata.name}')
     if [ -n "$FAILED_PODS" ]; then
       echo "- 일부 파드가 실행 중이 아닙니다. 파드 상태 및 로그를 확인하세요."
     fi
   fi
   
   echo "- 차트 구문 및 템플릿을 검증하세요: helm lint, helm template"
   echo "- 차트 종속성을 업데이트하세요: helm dependency update"
   echo "- 값 구성을 확인하세요: helm get values, helm show values"
   echo "- 서비스 계정 권한을 확인하세요: kubectl auth can-i --list --as=system:serviceaccount:$NAMESPACE:$SA"
   ```

2. **Terraform을 사용한 Helm 차트 배포**:
   ```hcl
   provider "helm" {
     kubernetes {
       host                   = data.aws_eks_cluster.cluster.endpoint
       cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
       token                  = data.aws_eks_cluster_auth.cluster.token
     }
   }
   
   resource "helm_release" "example" {
     name       = "my-app"
     repository = "https://charts.example.com/"
     chart      = "example-chart"
     version    = "1.2.3"
     namespace  = "my-namespace"
     create_namespace = true
     
     # 기본 타임아웃 증가
     timeout = 600
     
     # 디버그 활성화
     debug = true
     
     # 차트 값 설정
     values = [
       file("${path.module}/values.yaml")
     ]
     
     # 개별 값 설정
     set {
       name  = "replicaCount"
       value = "2"
     }
     
     set {
       name  = "image.tag"
       value = "latest"
     }
     
     # 민감한 값 설정
     set_sensitive {
       name  = "secrets.apiKey"
       value = var.api_key
     }
     
     # 종속성 업데이트
     dependency_update = true
     
     # 배포 전 검증
     lint = true
     
     # 배포 후 검증
     wait = true
     wait_for_jobs = true
     
     # 배포 실패 시 롤백
     atomic = true
     
     # 배포 후 테스트 실행
     verify = true
   }
   
   # 배포 후 검증
   resource "null_resource" "verify_deployment" {
     depends_on = [helm_release.example]
     
     provisioner "local-exec" {
       command = <<-EOT
         kubectl wait --for=condition=available --timeout=300s deployment/my-app -n my-namespace
         kubectl get pods -n my-namespace -l app.kubernetes.io/instance=my-app
       EOT
     }
   }
   ```

3. **Helm 차트 테스트 구성**:
   ```yaml
   # templates/tests/test-connection.yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: "{{ include "my-chart.fullname" . }}-test-connection"
     labels:
       {{- include "my-chart.labels" . | nindent 4 }}
       app.kubernetes.io/component: test
     annotations:
       "helm.sh/hook": test
       "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
   spec:
     containers:
       - name: wget
         image: busybox
         command: ['wget']
         args: ['{{ include "my-chart.fullname" . }}:{{ .Values.service.port }}']
     restartPolicy: Never
   
   # templates/tests/test-api.yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: "{{ include "my-chart.fullname" . }}-test-api"
     labels:
       {{- include "my-chart.labels" . | nindent 4 }}
       app.kubernetes.io/component: test
     annotations:
       "helm.sh/hook": test
       "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
   spec:
     containers:
       - name: api-test
         image: curlimages/curl
         command: ['curl']
         args: ['-f', 'http://{{ include "my-chart.fullname" . }}:{{ .Values.service.port }}/api/health']
     restartPolicy: Never
   ```

4. **CI/CD 파이프라인의 Helm 차트 검증**:
   ```yaml
   # .github/workflows/helm-validate.yml
   name: Validate Helm Chart
   
   on:
     pull_request:
       paths:
         - 'charts/**'
   
   jobs:
     lint-and-test:
       runs-on: ubuntu-latest
       steps:
         - name: Checkout
           uses: actions/checkout@v2
           
         - name: Set up Helm
           uses: azure/setup-helm@v1
           with:
             version: 'v3.8.0'
             
         - name: Set up Python
           uses: actions/setup-python@v2
           with:
             python-version: '3.9'
             
         - name: Set up chart-testing
           uses: helm/chart-testing-action@v2.1.0
             
         - name: Lint charts
           run: ct lint --all --config .github/ct.yaml
           
         - name: Set up kind cluster
           uses: helm/kind-action@v1.2.0
           
         - name: Install charts
           run: ct install --all --config .github/ct.yaml
           
         - name: Run chart tests
           run: |
             for chart in charts/*; do
               if [ -d "$chart" ]; then
                 chart_name=$(basename "$chart")
                 echo "Testing chart: $chart_name"
                 helm test "$chart_name" -n "$chart_name"
               fi
             done
   ```

다른 옵션들의 문제점:
- **A. 모든 Helm 차트 삭제 및 재설치**: 이는 극단적인 조치이며, 데이터 손실을 초래할 수 있고 근본 원인을 해결하지 않습니다.
- **B. 클러스터 재생성**: 이는 매우 극단적인 조치이며, 대부분의 Helm 배포 문제는 클러스터 수준이 아닌 차트 구성 또는 권한과 관련이 있습니다.
- **D. 수동으로 모든 리소스 배포**: 이는 Helm의 이점을 포기하는 것이며, 복잡한 애플리케이션의 경우 오류가 발생하기 쉽고 관리하기 어렵습니다.
</details>
### 9. Amazon EKS 클러스터에서 메모리 누수 문제를 해결하는 가장 효과적인 접근 방식은 무엇인가요?

A. 모든 파드 재시작  
B. 클러스터 노드 크기 증가  
C. 메모리 사용량 프로파일링, 컨테이너 제한 검토, 애플리케이션 코드 분석  
D. 더 많은 노드 추가  

<details>
<summary>정답 및 설명</summary>

**정답: C. 메모리 사용량 프로파일링, 컨테이너 제한 검토, 애플리케이션 코드 분석**

**설명:**
Amazon EKS 클러스터에서 메모리 누수 문제를 해결하는 가장 효과적인 접근 방식은 메모리 사용량 프로파일링, 컨테이너 제한 검토, 애플리케이션 코드 분석을 포함한 체계적인 접근법입니다. 이 방법은 메모리 누수의 근본 원인을 식별하고 해결하는 데 도움이 됩니다.

**주요 확인 사항:**

1. **메모리 사용량 프로파일링**:
   - 파드 및 노드 수준의 메모리 사용량 모니터링
   - 시간에 따른 메모리 사용 패턴 분석
   - 메모리 누수 징후 식별

2. **컨테이너 제한 검토**:
   - 메모리 요청 및 제한 설정 확인
   - 컨테이너 OOM(Out of Memory) 이벤트 분석
   - 리소스 할당 최적화

3. **애플리케이션 코드 분석**:
   - 애플리케이션 내부 메모리 사용 패턴 검토
   - 메모리 누수 가능성이 있는 코드 식별
   - 애플리케이션 프로파일링 도구 사용

4. **시스템 구성 요소 검토**:
   - kubelet 메모리 관리 설정
   - 노드 시스템 리소스 사용량
   - 클러스터 구성 요소 상태

**문제 해결 방법:**

1. **메모리 사용량 모니터링 및 분석**:
   ```bash
   # 노드 메모리 사용량 확인
   kubectl top nodes
   
   # 파드 메모리 사용량 확인
   kubectl top pods -A
   
   # 특정 네임스페이스의 파드 메모리 사용량 확인
   kubectl top pods -n <namespace>
   
   # 컨테이너별 메모리 사용량 확인
   kubectl top pods -n <namespace> --containers
   
   # 메모리 사용량이 높은 파드 식별
   kubectl top pods -A --sort-by=memory
   ```

2. **컨테이너 제한 및 OOM 이벤트 확인**:
   ```bash
   # 파드 메모리 제한 확인
   kubectl get pods -n <namespace> -o jsonpath='{.items[*].spec.containers[*].resources}'
   
   # 파드 세부 정보 확인
   kubectl describe pod <pod-name> -n <namespace>
   
   # OOM 이벤트 확인
   kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep -i "OOMKilled"
   
   # 노드 OOM 이벤트 확인
   kubectl get events --field-selector involvedObject.kind=Node --sort-by='.lastTimestamp' | grep -i "memory"
   ```

3. **애플리케이션 로그 및 프로파일링**:
   ```bash
   # 애플리케이션 로그 확인
   kubectl logs <pod-name> -n <namespace>
   
   # 이전 파드 로그 확인
   kubectl logs <pod-name> -n <namespace> --previous
   
   # 애플리케이션 프로파일링 도구 실행
   kubectl exec -it <pod-name> -n <namespace> -- <profiling-command>
   
   # 메모리 덤프 생성
   kubectl exec -it <pod-name> -n <namespace> -- <memory-dump-command>
   ```

4. **노드 및 시스템 리소스 확인**:
   ```bash
   # 노드 세부 정보 확인
   kubectl describe node <node-name>
   
   # 노드 메모리 압력 확인
   kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="MemoryPressure")]}'
   
   # kubelet 로그 확인
   kubectl logs -n kube-system <kubelet-pod-name>
   
   # 시스템 메모리 통계 확인
   kubectl debug node/<node-name> -it --image=busybox -- sh -c "cat /proc/meminfo"
   ```

**일반적인 메모리 누수 문제 및 해결 방법:**

1. **애플리케이션 메모리 누수**:
   - **증상**: 시간이 지남에 따라 메모리 사용량이 지속적으로 증가
   - **원인**: 애플리케이션 코드의 메모리 누수, 캐시 관리 부족
   - **해결 방법**:
     - 애플리케이션 코드 검토 및 수정
     - 메모리 프로파일링 도구 사용
     - 주기적인 가비지 컬렉션 구성
     - 캐시 크기 제한 및 만료 정책 구현

2. **컨테이너 메모리 제한 문제**:
   - **증상**: 빈번한 OOM 종료, 파드 재시작
   - **원인**: 부적절한 메모리 제한 설정, 리소스 요청과 제한 간의 큰 차이
   - **해결 방법**:
     ```yaml
     # 적절한 메모리 요청 및 제한 설정
     apiVersion: v1
     kind: Pod
     metadata:
       name: memory-optimized-pod
     spec:
       containers:
       - name: app
         image: app-image
         resources:
           requests:
             memory: "256Mi"
           limits:
             memory: "512Mi"
     ```

3. **시스템 구성 요소 메모리 문제**:
   - **증상**: 노드 불안정성, kubelet 또는 다른 시스템 구성 요소의 높은 메모리 사용량
   - **원인**: kubelet 구성 문제, 시스템 구성 요소 버그
   - **해결 방법**:
     - kubelet 구성 최적화
     - 시스템 구성 요소 업데이트
     - 노드 리소스 예약 조정

4. **메모리 단편화 문제**:
   - **증상**: 사용 가능한 총 메모리가 충분함에도 OOM 발생
   - **원인**: 메모리 단편화, 큰 페이지 할당 실패
   - **해결 방법**:
     - 노드 주기적 재부팅 일정 설정
     - 메모리 압력이 높은 워크로드 분산
     - 노드 메모리 오버커밋 감소

**모범 사례:**

1. **체계적인 메모리 모니터링**:
   - 클러스터, 노드, 파드 수준의 메모리 모니터링
   - 시간에 따른 메모리 사용 패턴 추적
   - 이상 징후에 대한 알림 설정

2. **적절한 리소스 제한 설정**:
   - 워크로드 특성에 맞는 메모리 요청 및 제한 설정
   - 메모리 요청과 제한 간의 적절한 비율 유지
   - 정기적인 리소스 사용량 검토 및 조정

3. **애플리케이션 최적화**:
   - 메모리 효율적인 코드 작성
   - 주기적인 메모리 프로파일링 및 최적화
   - 적절한 캐시 전략 구현

4. **클러스터 구성 최적화**:
   - 노드 메모리 예약 최적화
   - 적절한 kubelet 메모리 관리 설정
   - 워크로드 분산 및 격리

**실제 구현 예시:**

1. **메모리 누수 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # 메모리 누수 문제 해결 스크립트
   
   NAMESPACE=$1
   POD_PREFIX=$2
   
   if [ -z "$NAMESPACE" ] || [ -z "$POD_PREFIX" ]; then
     echo "사용법: $0 <네임스페이스> <파드_접두사>"
     exit 1
   fi
   
   echo "=== 메모리 누수 문제 해결 ==="
   echo "네임스페이스: $NAMESPACE"
   echo "파드 접두사: $POD_PREFIX"
   
   # 노드 메모리 상태 확인
   echo
   echo "=== 노드 메모리 상태 ==="
   kubectl top nodes --sort-by=memory
   
   # 메모리 사용량이 높은 파드 확인
   echo
   echo "=== 메모리 사용량이 높은 파드 ==="
   kubectl top pods -n $NAMESPACE | grep $POD_PREFIX | sort -k4 -nr
   
   # 파드 메모리 제한 확인
   echo
   echo "=== 파드 메모리 제한 ==="
   PODS=$(kubectl get pods -n $NAMESPACE -l app=$POD_PREFIX -o jsonpath='{.items[*].metadata.name}')
   for POD in $PODS; do
     echo
     echo "파드: $POD"
     kubectl get pod $POD -n $NAMESPACE -o jsonpath='{.spec.containers[*].resources}' | jq
   done
   
   # OOM 이벤트 확인
   echo
   echo "=== OOM 이벤트 ==="
   kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | grep -i "OOMKilled" | grep $POD_PREFIX
   
   # 파드 재시작 확인
   echo
   echo "=== 파드 재시작 횟수 ==="
   kubectl get pods -n $NAMESPACE -l app=$POD_PREFIX -o custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount,STATUS:.status.phase
   
   # 메모리 사용량 추세 수집
   echo
   echo "=== 메모리 사용량 추세 수집 중 ==="
   echo "5분 동안 30초마다 메모리 사용량을 수집합니다..."
   
   for i in {1..10}; do
     echo
     echo "수집 $i/10 ($(date))"
     kubectl top pods -n $NAMESPACE | grep $POD_PREFIX
     sleep 30
   done
   
   # 로그에서 메모리 관련 메시지 확인
   echo
   echo "=== 로그에서 메모리 관련 메시지 ==="
   for POD in $PODS; do
     echo
     echo "파드: $POD"
     kubectl logs $POD -n $NAMESPACE --tail=100 | grep -i "memory\|heap\|GC\|out of memory"
   done
   
   # 애플리케이션별 메모리 프로파일링 명령 예시
   echo
   echo "=== 애플리케이션별 메모리 프로파일링 명령 예시 ==="
   echo
   echo "Java 애플리케이션:"
   echo "kubectl exec -it <pod-name> -n $NAMESPACE -- jmap -heap 1"
   echo "kubectl exec -it <pod-name> -n $NAMESPACE -- jstat -gcutil 1 1000 10"
   echo
   echo "Node.js 애플리케이션:"
   echo "kubectl exec -it <pod-name> -n $NAMESPACE -- node --inspect"
   echo
   echo "Python 애플리케이션:"
   echo "kubectl exec -it <pod-name> -n $NAMESPACE -- python -m memory_profiler <script.py>"
   echo
   echo "Go 애플리케이션:"
   echo "kubectl exec -it <pod-name> -n $NAMESPACE -- go tool pprof <binary> /tmp/profile"
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   echo "1. 메모리 사용량이 지속적으로 증가하는 파드 식별"
   echo "2. 애플리케이션 코드에서 메모리 누수 가능성 검토"
   echo "3. 적절한 메모리 제한 설정 확인 및 조정"
   echo "4. 애플리케이션별 메모리 프로파일링 도구 사용"
   echo "5. 필요한 경우 애플리케이션 코드 최적화 또는 수정"
   ```

2. **메모리 모니터링 및 알림 구성**:
   ```yaml
   # Prometheus 메모리 사용량 알림 규칙
   apiVersion: monitoring.coreos.com/v1
   kind: PrometheusRule
   metadata:
     name: memory-alerts
     namespace: monitoring
   spec:
     groups:
     - name: memory
       rules:
       - alert: PodMemoryUsageHigh
         expr: sum(container_memory_working_set_bytes{container!="", image!=""}) by (namespace, pod) / sum(kube_pod_container_resource_limits_memory_bytes) by (namespace, pod) > 0.85
         for: 10m
         labels:
           severity: warning
         annotations:
           summary: "Pod 메모리 사용량 높음"
           description: "파드 {{ $labels.pod }}의 메모리 사용량이 제한의 85%를 초과했습니다."
       
       - alert: PodMemoryUsageCritical
         expr: sum(container_memory_working_set_bytes{container!="", image!=""}) by (namespace, pod) / sum(kube_pod_container_resource_limits_memory_bytes) by (namespace, pod) > 0.95
         for: 5m
         labels:
           severity: critical
         annotations:
           summary: "Pod 메모리 사용량 심각"
           description: "파드 {{ $labels.pod }}의 메모리 사용량이 제한의 95%를 초과했습니다."
       
       - alert: PodMemoryGrowth
         expr: deriv(container_memory_working_set_bytes{container!="", image!=""}[30m]) > 1024 * 1024 * 5
         for: 30m
         labels:
           severity: warning
         annotations:
           summary: "Pod 메모리 지속적 증가"
           description: "파드 {{ $labels.pod }}의 메모리 사용량이 30분 동안 지속적으로 증가하고 있습니다(>5MB/분)."
       
       - alert: NodeMemoryPressure
         expr: kube_node_status_condition{condition="MemoryPressure", status="true"} == 1
         for: 5m
         labels:
           severity: critical
         annotations:
           summary: "노드 메모리 압력"
           description: "노드 {{ $labels.node }}에 메모리 압력이 있습니다."
   ```

3. **메모리 효율적인 애플리케이션 구성**:
   ```yaml
   # Java 애플리케이션을 위한 메모리 최적화 구성
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: java-app
     namespace: production
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: java-app
     template:
       metadata:
         labels:
           app: java-app
       spec:
         containers:
         - name: java-app
           image: java-app:1.0
           resources:
             requests:
               memory: "512Mi"
               cpu: "500m"
             limits:
               memory: "1Gi"
               cpu: "1000m"
           env:
           - name: JAVA_OPTS
             value: "-XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heapdump.bin -XX:+ExitOnOutOfMemoryError -Xms256m -Xmx768m"
           - name: MEMORY_MONITOR_ENABLED
             value: "true"
           - name: MEMORY_MONITOR_INTERVAL
             value: "60"
           livenessProbe:
             httpGet:
               path: /actuator/health/liveness
               port: 8080
             initialDelaySeconds: 60
             periodSeconds: 30
           readinessProbe:
             httpGet:
               path: /actuator/health/readiness
               port: 8080
             initialDelaySeconds: 30
             periodSeconds: 10
           lifecycle:
             preStop:
               exec:
                 command: ["sh", "-c", "sleep 10"]
   ```

4. **Terraform을 사용한 메모리 모니터링 구성**:
   ```hcl
   # Prometheus 및 Grafana 설치
   resource "helm_release" "prometheus" {
     name       = "prometheus"
     repository = "https://prometheus-community.github.io/helm-charts"
     chart      = "kube-prometheus-stack"
     namespace  = "monitoring"
     create_namespace = true
     
     set {
       name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
       value = "false"
     }
     
     set {
       name  = "prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues"
       value = "false"
     }
     
     set {
       name  = "grafana.enabled"
       value = "true"
     }
     
     set {
       name  = "grafana.persistence.enabled"
       value = "true"
     }
     
     set {
       name  = "grafana.persistence.size"
       value = "10Gi"
     }
   }
   
   # 메모리 대시보드 구성
   resource "kubernetes_config_map" "memory_dashboard" {
     metadata {
       name      = "memory-dashboard"
       namespace = "monitoring"
       labels = {
         grafana_dashboard = "1"
       }
     }
     
     data = {
       "memory-dashboard.json" = file("${path.module}/dashboards/memory-dashboard.json")
     }
     
     depends_on = [helm_release.prometheus]
   }
   
   # 메모리 알림 규칙
   resource "kubernetes_manifest" "memory_alerts" {
     manifest = {
       apiVersion = "monitoring.coreos.com/v1"
       kind       = "PrometheusRule"
       metadata = {
         name      = "memory-alerts"
         namespace = "monitoring"
       }
       spec = {
         groups = [
           {
             name = "memory"
             rules = [
               {
                 alert = "PodMemoryUsageHigh"
                 expr  = "sum(container_memory_working_set_bytes{container!=\"\", image!=\"\"}) by (namespace, pod) / sum(kube_pod_container_resource_limits_memory_bytes) by (namespace, pod) > 0.85"
                 for   = "10m"
                 labels = {
                   severity = "warning"
                 }
                 annotations = {
                   summary     = "Pod 메모리 사용량 높음"
                   description = "파드 {{ $labels.pod }}의 메모리 사용량이 제한의 85%를 초과했습니다."
                 }
               },
               {
                 alert = "PodMemoryGrowth"
                 expr  = "deriv(container_memory_working_set_bytes{container!=\"\", image!=\"\"}[30m]) > 1024 * 1024 * 5"
                 for   = "30m"
                 labels = {
                   severity = "warning"
                 }
                 annotations = {
                   summary     = "Pod 메모리 지속적 증가"
                   description = "파드 {{ $labels.pod }}의 메모리 사용량이 30분 동안 지속적으로 증가하고 있습니다(>5MB/분)."
                 }
               }
             ]
           }
         ]
       }
     }
     
     depends_on = [helm_release.prometheus]
   }
   ```

다른 옵션들의 문제점:
- **A. 모든 파드 재시작**: 이는 일시적인 해결책일 뿐이며, 메모리 누수의 근본 원인을 해결하지 않습니다. 파드가 다시 시작되면 문제가 재발할 것입니다.
- **B. 클러스터 노드 크기 증가**: 이는 근본 원인을 해결하지 않고 증상을 숨기는 것에 불과합니다. 메모리 누수가 계속되면 더 큰 노드도 결국 메모리 부족 상태가 될 것입니다.
- **D. 더 많은 노드 추가**: 이는 B와 유사하게 근본 원인을 해결하지 않고 증상을 숨기는 것에 불과합니다. 메모리 누수 문제는 노드 수와 관계없이 계속될 것입니다.
</details>
### 10. Amazon EKS 클러스터에서 DNS 해결 문제를 해결하는 가장 효과적인 접근 방식은 무엇인가요?

A. 모든 파드에 고정 IP 할당  
B. CoreDNS 구성, 네트워크 정책, DNS 정책, 연결성 체계적 확인  
C. 모든 서비스에 ExternalName 사용  
D. 클러스터 VPC 재구성  

<details>
<summary>정답 및 설명</summary>

**정답: B. CoreDNS 구성, 네트워크 정책, DNS 정책, 연결성 체계적 확인**

**설명:**
Amazon EKS 클러스터에서 DNS 해결 문제를 해결하는 가장 효과적인 접근 방식은 CoreDNS 구성, 네트워크 정책, DNS 정책, 연결성을 체계적으로 확인하는 것입니다. 이 접근 방식은 DNS 문제의 근본 원인을 식별하고 해결하는 데 도움이 됩니다.

**주요 확인 사항:**

1. **CoreDNS 구성 및 상태 확인**:
   - CoreDNS 파드 상태 및 로그
   - CoreDNS ConfigMap 구성
   - CoreDNS 서비스 및 엔드포인트

2. **네트워크 정책 및 연결성 확인**:
   - DNS 포트(53/UDP, 53/TCP)에 대한 네트워크 정책
   - 파드와 CoreDNS 간의 네트워크 연결
   - VPC DNS 설정

3. **DNS 정책 및 구성 확인**:
   - 파드 DNS 정책 설정
   - DNS 구성 옵션
   - 호스트 네임스페이스 설정

4. **클러스터 및 VPC 구성 확인**:
   - EKS 클러스터 DNS 설정
   - VPC DNS 속성
   - DHCP 옵션 세트

**문제 해결 방법:**

1. **CoreDNS 상태 및 구성 확인**:
   ```bash
   # CoreDNS 파드 상태 확인
   kubectl get pods -n kube-system -l k8s-app=kube-dns
   
   # CoreDNS 로그 확인
   kubectl logs -n kube-system -l k8s-app=kube-dns
   
   # CoreDNS ConfigMap 확인
   kubectl get configmap coredns -n kube-system -o yaml
   
   # CoreDNS 서비스 확인
   kubectl get service kube-dns -n kube-system
   
   # CoreDNS 엔드포인트 확인
   kubectl get endpoints kube-dns -n kube-system
   ```

2. **DNS 해결 테스트**:
   ```bash
   # 디버그 파드 생성
   kubectl run dns-test --rm -it --image=busybox -- sh
   
   # 클러스터 내부 DNS 해결 테스트
   nslookup kubernetes.default.svc.cluster.local
   
   # 서비스 DNS 해결 테스트
   nslookup <service-name>.<namespace>.svc.cluster.local
   
   # 외부 도메인 해결 테스트
   nslookup google.com
   
   # DNS 서버 확인
   cat /etc/resolv.conf
   ```

3. **네트워크 정책 및 연결성 확인**:
   ```bash
   # DNS 관련 네트워크 정책 확인
   kubectl get networkpolicies --all-namespaces
   
   # CoreDNS로의 연결 테스트
   kubectl run netcat-test --rm -it --image=busybox -- sh -c "nc -zv kube-dns.kube-system.svc.cluster.local 53"
   
   # DNS 패킷 캡처
   kubectl run tcpdump-test --rm -it --image=nicolaka/netshoot -- tcpdump -i any port 53
   ```

4. **파드 DNS 구성 확인**:
   ```bash
   # 파드 DNS 정책 확인
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsPolicy}'
   
   # 파드 DNS 구성 확인
   kubectl get pod <pod-name> -o jsonpath='{.spec.dnsConfig}'
   
   # 파드 내부 resolv.conf 확인
   kubectl exec -it <pod-name> -- cat /etc/resolv.conf
   ```

5. **VPC 및 클러스터 DNS 설정 확인**:
   ```bash
   # VPC DNS 속성 확인
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].EnableDnsSupport'
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].EnableDnsHostnames'
   
   # DHCP 옵션 세트 확인
   aws ec2 describe-vpcs --vpc-id <vpc-id> --query 'Vpcs[0].DhcpOptionsId'
   aws ec2 describe-dhcp-options --dhcp-options-id <dhcp-options-id>
   
   # 노드 DNS 구성 확인
   kubectl debug node/<node-name> -it --image=busybox -- cat /etc/resolv.conf
   ```

**일반적인 DNS 문제 및 해결 방법:**

1. **CoreDNS 파드 문제**:
   - **증상**: DNS 쿼리 실패, CoreDNS 파드 비정상
   - **원인**: CoreDNS 파드 충돌, 리소스 부족, 구성 오류
   - **해결 방법**:
     ```bash
     # CoreDNS 파드 재시작
     kubectl rollout restart deployment coredns -n kube-system
     
     # CoreDNS 리소스 증가
     kubectl edit deployment coredns -n kube-system
     # resources 섹션에서 requests 및 limits 증가
     
     # CoreDNS 로그 확인
     kubectl logs -n kube-system -l k8s-app=kube-dns
     ```

2. **네트워크 정책 문제**:
   - **증상**: 특정 네임스페이스 또는 파드에서만 DNS 해결 실패
   - **원인**: 제한적인 네트워크 정책이 DNS 트래픽 차단
   - **해결 방법**:
     ```yaml
     # DNS 트래픽을 허용하는 네트워크 정책
     apiVersion: networking.k8s.io/v1
     kind: NetworkPolicy
     metadata:
       name: allow-dns
       namespace: <namespace>
     spec:
       podSelector: {}
       policyTypes:
       - Egress
       egress:
       - to:
         - namespaceSelector:
             matchLabels:
               kubernetes.io/metadata.name: kube-system
           podSelector:
             matchLabels:
               k8s-app: kube-dns
         ports:
         - protocol: UDP
           port: 53
         - protocol: TCP
           port: 53
     ```

3. **DNS 정책 및 구성 문제**:
   - **증상**: 특정 유형의 DNS 쿼리만 실패
   - **원인**: 부적절한 DNS 정책 또는 구성
   - **해결 방법**:
     ```yaml
     # 사용자 지정 DNS 구성으로 파드 생성
     apiVersion: v1
     kind: Pod
     metadata:
       name: dns-custom-pod
     spec:
       containers:
       - name: app
         image: busybox
         command: ["sleep", "3600"]
       dnsPolicy: "None"
       dnsConfig:
         nameservers:
         - "169.254.20.10"  # VPC DNS 서버
         - "8.8.8.8"        # 백업 DNS 서버
         searches:
         - <namespace>.svc.cluster.local
         - svc.cluster.local
         - cluster.local
         options:
         - name: ndots
           value: "5"
     ```

4. **VPC DNS 설정 문제**:
   - **증상**: 외부 도메인 해결 실패
   - **원인**: VPC DNS 속성 비활성화 또는 DHCP 옵션 세트 문제
   - **해결 방법**:
     ```bash
     # VPC DNS 속성 활성화
     aws ec2 modify-vpc-attribute --vpc-id <vpc-id> --enable-dns-support
     aws ec2 modify-vpc-attribute --vpc-id <vpc-id> --enable-dns-hostnames
     
     # 사용자 지정 DHCP 옵션 세트 생성
     aws ec2 create-dhcp-options \
       --dhcp-configurations \
       "Key=domain-name-servers,Values=AmazonProvidedDNS" \
       "Key=domain-name,Values=<region>.compute.internal"
     
     # VPC에 DHCP 옵션 세트 연결
     aws ec2 associate-dhcp-options --dhcp-options-id <dhcp-options-id> --vpc-id <vpc-id>
     ```

5. **CoreDNS 구성 문제**:
   - **증상**: 특정 도메인 해결 실패 또는 느린 DNS 해결
   - **원인**: CoreDNS 구성 오류 또는 최적화되지 않은 설정
   - **해결 방법**:
     ```yaml
     # CoreDNS ConfigMap 최적화
     apiVersion: v1
     kind: ConfigMap
     metadata:
       name: coredns
       namespace: kube-system
     data:
       Corefile: |
         .:53 {
             errors
             health {
                lameduck 5s
             }
             ready
             kubernetes cluster.local in-addr.arpa ip6.arpa {
                pods insecure
                fallthrough in-addr.arpa ip6.arpa
                ttl 30
             }
             prometheus :9153
             forward . /etc/resolv.conf {
                max_concurrent 1000
                health_check 5s
             }
             cache 30
             loop
             reload
             loadbalance
         }
     ```

**모범 사례:**

1. **CoreDNS 모니터링 및 확장**:
   - CoreDNS 성능 및 상태 모니터링
   - 클러스터 크기에 따른 CoreDNS 복제본 확장
   - 적절한 리소스 할당

2. **DNS 캐싱 및 최적화**:
   - 적절한 TTL 및 캐시 설정
   - 노드 수준 DNS 캐싱 구현
   - 애플리케이션 수준 DNS 캐싱 고려

3. **네트워크 정책 설계**:
   - DNS 트래픽을 명시적으로 허용
   - 최소 권한 원칙 적용
   - 네트워크 정책 테스트 및 검증

4. **DNS 문제 해결 도구 및 프로세스**:
   - DNS 문제 해결 도구 및 스크립트 준비
   - 체계적인 문제 해결 프로세스 수립
   - DNS 관련 이벤트 및 로그 모니터링

**실제 구현 예시:**

1. **DNS 문제 해결 스크립트**:
   ```bash
   #!/bin/bash
   # DNS 문제 해결 스크립트
   
   NAMESPACE=$1
   POD_NAME=$2
   
   if [ -z "$NAMESPACE" ] || [ -z "$POD_NAME" ]; then
     echo "사용법: $0 <네임스페이스> <파드_이름>"
     exit 1
   fi
   
   echo "=== DNS 문제 해결 ==="
   echo "네임스페이스: $NAMESPACE"
   echo "파드: $POD_NAME"
   
   # CoreDNS 상태 확인
   echo
   echo "=== CoreDNS 상태 ==="
   kubectl get pods -n kube-system -l k8s-app=kube-dns
   
   # CoreDNS 서비스 및 엔드포인트 확인
   echo
   echo "=== CoreDNS 서비스 및 엔드포인트 ==="
   kubectl get service kube-dns -n kube-system
   kubectl get endpoints kube-dns -n kube-system
   
   # CoreDNS 구성 확인
   echo
   echo "=== CoreDNS 구성 ==="
   kubectl get configmap coredns -n kube-system -o yaml
   
   # 파드 DNS 구성 확인
   echo
   echo "=== 파드 DNS 구성 ==="
   kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.spec.dnsPolicy}'
   echo
   kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.spec.dnsConfig}'
   
   # 파드 내부 DNS 구성 확인
   echo
   echo "=== 파드 내부 DNS 구성 ==="
   kubectl exec -it $POD_NAME -n $NAMESPACE -- cat /etc/resolv.conf
   
   # DNS 해결 테스트
   echo
   echo "=== DNS 해결 테스트 ==="
   echo "클러스터 내부 DNS 해결 테스트:"
   kubectl exec -it $POD_NAME -n $NAMESPACE -- nslookup kubernetes.default.svc.cluster.local
   
   echo
   echo "외부 도메인 해결 테스트:"
   kubectl exec -it $POD_NAME -n $NAMESPACE -- nslookup google.com
   
   # DNS 연결 테스트
   echo
   echo "=== DNS 연결 테스트 ==="
   kubectl exec -it $POD_NAME -n $NAMESPACE -- nc -zv kube-dns.kube-system.svc.cluster.local 53 -w 5
   
   # 네트워크 정책 확인
   echo
   echo "=== 네트워크 정책 확인 ==="
   kubectl get networkpolicies -n $NAMESPACE
   
   # CoreDNS 로그 확인
   echo
   echo "=== CoreDNS 로그 ==="
   kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50
   
   # VPC DNS 설정 확인
   echo
   echo "=== VPC DNS 설정 ==="
   VPC_ID=$(aws eks describe-cluster --name $(kubectl config current-context | cut -d'/' -f2) --query "cluster.resourcesVpcConfig.vpcId" --output text)
   echo "VPC ID: $VPC_ID"
   
   echo "DNS 지원 활성화:"
   aws ec2 describe-vpcs --vpc-id $VPC_ID --query 'Vpcs[0].EnableDnsSupport'
   
   echo "DNS 호스트 이름 활성화:"
   aws ec2 describe-vpcs --vpc-id $VPC_ID --query 'Vpcs[0].EnableDnsHostnames'
   
   echo "DHCP 옵션 세트:"
   DHCP_OPTIONS_ID=$(aws ec2 describe-vpcs --vpc-id $VPC_ID --query 'Vpcs[0].DhcpOptionsId' --output text)
   aws ec2 describe-dhcp-options --dhcp-options-id $DHCP_OPTIONS_ID
   
   echo
   echo "=== 문제 해결 권장 사항 ==="
   if ! kubectl get pods -n kube-system -l k8s-app=kube-dns -o jsonpath='{.items[*].status.phase}' | grep -q "Running"; then
     echo "- CoreDNS 파드가 실행 중이 아닙니다. CoreDNS 파드 상태 및 로그를 확인하세요."
   fi
   
   if ! kubectl exec -it $POD_NAME -n $NAMESPACE -- nslookup kubernetes.default.svc.cluster.local &>/dev/null; then
     echo "- 클러스터 내부 DNS 해결에 실패했습니다. 파드와 CoreDNS 간의 네트워크 연결을 확인하세요."
   fi
   
   if ! kubectl exec -it $POD_NAME -n $NAMESPACE -- nslookup google.com &>/dev/null; then
     echo "- 외부 도메인 해결에 실패했습니다. CoreDNS 구성 및 VPC DNS 설정을 확인하세요."
   fi
   
   if kubectl get networkpolicies -n $NAMESPACE -o json | jq -r '.items[] | select(.spec.egress != null)' | grep -q .; then
     echo "- 네트워크 정책이 DNS 트래픽을 차단할 수 있습니다. DNS 트래픽(UDP/TCP 포트 53)을 허용하는지 확인하세요."
   fi
   
   echo "- CoreDNS ConfigMap 구성을 검토하고 필요한 경우 최적화하세요."
   echo "- 파드 DNS 정책 및 구성을 검토하세요."
   echo "- VPC DNS 속성이 활성화되어 있는지 확인하세요."
   ```

2. **CoreDNS 최적화 및 확장 구성**:
   ```yaml
   # CoreDNS 배포 최적화
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: coredns
     namespace: kube-system
   spec:
     replicas: 3  # 클러스터 크기에 따라 조정
     selector:
       matchLabels:
         k8s-app: kube-dns
     template:
       metadata:
         labels:
           k8s-app: kube-dns
       spec:
         priorityClassName: system-cluster-critical
         serviceAccountName: coredns
         affinity:
           podAntiAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               podAffinityTerm:
                 labelSelector:
                   matchExpressions:
                   - key: k8s-app
                     operator: In
                     values:
                     - kube-dns
                 topologyKey: kubernetes.io/hostname
         containers:
         - name: coredns
           image: public.ecr.aws/eks-distro/coredns/coredns:v1.8.7-eks-1-23-13
           resources:
             limits:
               memory: 170Mi
             requests:
               cpu: 100m
               memory: 70Mi
           args: [ "-conf", "/etc/coredns/Corefile" ]
           volumeMounts:
           - name: config-volume
             mountPath: /etc/coredns
             readOnly: true
           ports:
           - containerPort: 53
             name: dns
             protocol: UDP
           - containerPort: 53
             name: dns-tcp
             protocol: TCP
           - containerPort: 9153
             name: metrics
             protocol: TCP
           livenessProbe:
             httpGet:
               path: /health
               port: 8080
               scheme: HTTP
             initialDelaySeconds: 60
             timeoutSeconds: 5
             successThreshold: 1
             failureThreshold: 5
           readinessProbe:
             httpGet:
               path: /ready
               port: 8181
               scheme: HTTP
         volumes:
         - name: config-volume
           configMap:
             name: coredns
             items:
             - key: Corefile
               path: Corefile
   ```

3. **노드 수준 DNS 캐싱 구성**:
   ```yaml
   # NodeLocal DNSCache 배포
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: node-local-dns
     namespace: kube-system
   ---
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: node-local-dns
     namespace: kube-system
     labels:
       k8s-app: node-local-dns
   spec:
     selector:
       matchLabels:
         k8s-app: node-local-dns
     template:
       metadata:
         labels:
           k8s-app: node-local-dns
       spec:
         priorityClassName: system-node-critical
         serviceAccountName: node-local-dns
         hostNetwork: true
         dnsPolicy: Default
         containers:
         - name: node-cache
           image: public.ecr.aws/eks-distro/kubernetes-dns/k8s-dns-node-cache:1.21.4
           resources:
             requests:
               cpu: 25m
               memory: 5Mi
           args:
           - -localip=169.254.20.10
           - -metrics=0.0.0.0:9253
           - -health-port=9254
           - -config=/etc/coredns/Corefile
           livenessProbe:
             httpGet:
               host: 169.254.20.10
               path: /health
               port: 9254
             initialDelaySeconds: 60
             timeoutSeconds: 5
           volumeMounts:
           - name: config-volume
             mountPath: /etc/coredns
         volumes:
         - name: config-volume
           configMap:
             name: node-local-dns
             items:
             - key: Corefile
               path: Corefile
   ---
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: node-local-dns
     namespace: kube-system
   data:
     Corefile: |
       cluster.local:53 {
           errors
           cache {
               success 9984 30
               denial 9984 5
           }
           reload
           loop
           bind 169.254.20.10
           forward . 172.20.0.10 {
               force_tcp
           }
           prometheus :9253
           health 169.254.20.10:9254
       }
       in-addr.arpa:53 {
           errors
           cache 30
           reload
           loop
           bind 169.254.20.10
           forward . 172.20.0.10 {
               force_tcp
           }
           prometheus :9253
       }
       ip6.arpa:53 {
           errors
           cache 30
           reload
           loop
           bind 169.254.20.10
           forward . 172.20.0.10 {
               force_tcp
           }
           prometheus :9253
       }
       .:53 {
           errors
           cache 30
           reload
           loop
           bind 169.254.20.10
           forward . /etc/resolv.conf {
               max_concurrent 1000
           }
           prometheus :9253
           health 169.254.20.10:9254
       }
   ```

4. **Terraform을 사용한 DNS 구성**:
   ```hcl
   # CoreDNS 구성 업데이트
   resource "kubernetes_config_map" "coredns" {
     metadata {
       name      = "coredns"
       namespace = "kube-system"
     }
     
     data = {
       Corefile = <<-EOT
         .:53 {
             errors
             health {
                lameduck 5s
             }
             ready
             kubernetes cluster.local in-addr.arpa ip6.arpa {
                pods insecure
                fallthrough in-addr.arpa ip6.arpa
                ttl 30
             }
             prometheus :9153
             forward . /etc/resolv.conf {
                max_concurrent 1000
                health_check 5s
             }
             cache 30
             loop
             reload
             loadbalance
         }
       EOT
     }
   }
   
   # CoreDNS 배포 확장
   resource "kubernetes_deployment" "coredns" {
     metadata {
       name      = "coredns"
       namespace = "kube-system"
     }
     
     spec {
       replicas = 3
       
       selector {
         match_labels = {
           k8s-app = "kube-dns"
         }
       }
       
       template {
         metadata {
           labels = {
             k8s-app = "kube-dns"
           }
         }
         
         spec {
           priority_class_name = "system-cluster-critical"
           service_account_name = "coredns"
           
           affinity {
             pod_anti_affinity {
               preferred_during_scheduling_ignored_during_execution {
                 weight = 100
                 pod_affinity_term {
                   label_selector {
                     match_expressions {
                       key = "k8s-app"
                       operator = "In"
                       values = ["kube-dns"]
                     }
                   }
                   topology_key = "kubernetes.io/hostname"
                 }
               }
             }
           }
           
           container {
             name  = "coredns"
             image = "public.ecr.aws/eks-distro/coredns/coredns:v1.8.7-eks-1-23-13"
             
             resources {
               limits = {
                 memory = "170Mi"
               }
               requests = {
                 cpu    = "100m"
                 memory = "70Mi"
               }
             }
             
             args = ["-conf", "/etc/coredns/Corefile"]
             
             volume_mount {
               name       = "config-volume"
               mount_path = "/etc/coredns"
               read_only  = true
             }
             
             port {
               container_port = 53
               name           = "dns"
               protocol       = "UDP"
             }
             
             port {
               container_port = 53
               name           = "dns-tcp"
               protocol       = "TCP"
             }
             
             port {
               container_port = 9153
               name           = "metrics"
               protocol       = "TCP"
             }
             
             liveness_probe {
               http_get {
                 path   = "/health"
                 port   = 8080
                 scheme = "HTTP"
               }
               initial_delay_seconds = 60
               timeout_seconds       = 5
               success_threshold     = 1
               failure_threshold     = 5
             }
             
             readiness_probe {
               http_get {
                 path   = "/ready"
                 port   = 8181
                 scheme = "HTTP"
               }
             }
           }
           
           volume {
             name = "config-volume"
             config_map {
               name = "coredns"
               items {
                 key  = "Corefile"
                 path = "Corefile"
               }
             }
           }
         }
       }
     }
   }
   
   # VPC DNS 속성 활성화
   resource "aws_vpc" "main" {
     # 기존 VPC 구성...
     
     enable_dns_support   = true
     enable_dns_hostnames = true
   }
   ```

다른 옵션들의 문제점:
- **A. 모든 파드에 고정 IP 할당**: 이는 DNS 문제를 해결하지 않으며, 파드 IP 할당과 DNS 해결은 별개의 문제입니다. 또한 파드에 고정 IP를 할당하는 것은 Kubernetes의 동적 특성에 반하며 관리 복잡성을 증가시킵니다.
- **C. 모든 서비스에 ExternalName 사용**: 이는 특정 사용 사례에만 적합하며, 대부분의 DNS 문제를 해결하지 않습니다. ExternalName은 외부 서비스에 대한 별칭을 제공하는 데 사용되며, 클러스터 내부 DNS 해결 문제를 해결하지 않습니다.
- **D. 클러스터 VPC 재구성**: 이는 극단적인 조치이며, 대부분의 DNS 문제는 VPC 수준이 아닌 클러스터 내부의 DNS 구성과 관련이 있습니다. VPC 재구성은 불필요한 다운타임과 복잡성을 초래할 수 있습니다.
</details>
