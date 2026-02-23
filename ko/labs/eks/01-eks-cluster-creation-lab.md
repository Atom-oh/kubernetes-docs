# EKS 클러스터 생성 실습 가이드

> **난이도**: 중급
> **예상 소요 시간**: 60분
> **마지막 업데이트**: 2026년 2월 11일

## 학습 목표
- eksctl을 사용하여 EKS 클러스터를 생성합니다
- kubectl로 클러스터에 접근하고 상태를 확인합니다
- 샘플 애플리케이션을 배포합니다
- 클러스터를 안전하게 삭제합니다

## 사전 요구 사항
- [ ] AWS 계정 및 AWS CLI 설정 (`aws sts get-caller-identity`로 확인)
- [ ] eksctl 설치 (`eksctl version`으로 확인)
- [ ] kubectl 설치
- [ ] [EKS 클러스터 생성](../../eks/02-eks-cluster-creation-part1.md) 학습 완료

> **비용 주의**: EKS 클러스터 운영에는 AWS 비용이 발생합니다. 실습 후 반드시 클러스터를 삭제하세요.

---

## 실습 1: eksctl 설정 확인

### 단계

**Step 1.1: 도구 버전 확인**
```bash
aws --version
eksctl version
kubectl version --client
```

**Step 1.2: AWS 자격 증명 확인**
```bash
aws sts get-caller-identity
```

예상 결과:
```json
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

**Step 1.3: 기본 리전 설정**
```bash
export AWS_DEFAULT_REGION=ap-northeast-2
echo "Region: $AWS_DEFAULT_REGION"
```

<details>
<summary>힌트가 필요하신가요?</summary>

- `aws configure list`로 현재 설정을 확인할 수 있습니다
- eksctl은 내부적으로 CloudFormation을 사용합니다
- IAM 사용자에게 EKS, EC2, CloudFormation, IAM 권한이 필요합니다
</details>

---

## 실습 2: EKS 클러스터 생성

### 단계

**Step 2.1: 클러스터 구성 파일 작성**
```bash
cat > /tmp/eks-cluster.yaml << 'EOF'
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: lab-cluster
  region: ap-northeast-2
  version: "1.31"
managedNodeGroups:
  - name: workers
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    volumeSize: 20
EOF
```

**Step 2.2: 클러스터 생성**
```bash
eksctl create cluster -f /tmp/eks-cluster.yaml
```

> 클러스터 생성에는 15-20분이 소요됩니다.

**Step 2.3: kubeconfig 확인**
```bash
kubectl config current-context
kubectl cluster-info
```

### 검증
```bash
kubectl get nodes
# 2개의 Ready 노드가 표시되어야 합니다
```

---

## 실습 3: 클러스터 탐색

### 단계

**Step 3.1: 노드 정보 확인**
```bash
kubectl get nodes -o wide
kubectl describe node $(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
```

**Step 3.2: 시스템 컴포넌트 확인**
```bash
kubectl get pods -n kube-system
kubectl get svc -n kube-system
```

**Step 3.3: 리소스 사용량 확인**
```bash
kubectl top nodes 2>/dev/null || echo "Metrics Server가 설치되지 않았습니다"
```

---

## 실습 4: 샘플 앱 배포

### 단계

**Step 4.1: Nginx 배포**
```bash
kubectl create deployment nginx --image=nginx:1.25 --replicas=2
kubectl expose deployment nginx --port=80 --type=LoadBalancer
kubectl wait --for=condition=available deployment/nginx --timeout=120s
```

**Step 4.2: 접근 확인**
```bash
# LoadBalancer External IP 확인 (ELB 생성에 몇 분 소요)
kubectl get svc nginx -w
# EXTERNAL-IP가 할당되면 Ctrl+C

# 접근 테스트
ELB_URL=$(kubectl get svc nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ELB URL: $ELB_URL"
curl -s "$ELB_URL" | head -5
```

**Step 4.3: 스케일링 테스트**
```bash
kubectl scale deployment nginx --replicas=4
kubectl get pods -l app=nginx -o wide
```

<details>
<summary>힌트가 필요하신가요?</summary>

- ELB URL이 DNS에 전파되기까지 몇 분이 걸릴 수 있습니다
- `kubectl get svc -w`로 EXTERNAL-IP 할당을 실시간 모니터링합니다
- AWS 콘솔의 EC2 > Load Balancers에서도 확인 가능합니다
</details>

### 검증
```bash
kubectl get deployment nginx -o jsonpath='{.status.readyReplicas}'
# 출력: 4
```

---

## 정리

> **중요**: 비용 발생을 방지하려면 반드시 클러스터를 삭제하세요.

```bash
# 1. 애플리케이션 정리 (LoadBalancer가 ELB를 삭제하도록)
kubectl delete svc nginx
kubectl delete deployment nginx

# 2. ELB 삭제 대기 (약 1분)
sleep 60

# 3. 클러스터 삭제
eksctl delete cluster -f /tmp/eks-cluster.yaml --wait

# 4. 설정 파일 정리
rm -f /tmp/eks-cluster.yaml
```

## 문제 해결

<details>
<summary>클러스터 생성이 실패합니다</summary>

- IAM 권한을 확인하세요 (AdministratorAccess 또는 EKS 관련 정책 필요)
- VPC/서브넷 제한을 확인하세요 (리전별 기본 VPC 개수 제한)
- `eksctl utils describe-stacks --region=ap-northeast-2 --cluster=lab-cluster`로 상세 확인
</details>

<details>
<summary>kubectl이 클러스터에 연결되지 않습니다</summary>

kubeconfig를 수동으로 업데이트하세요:
```bash
aws eks update-kubeconfig --name lab-cluster --region ap-northeast-2
```
</details>

## 다음 단계
- [EKS 클러스터 생성 퀴즈](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- 고급 주제 학습: [EKS 네트워킹](../../eks/03-eks-networking-part1.md)
