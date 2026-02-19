# EKS Hybrid Nodes 네트워크 구성 퀴즈

> **관련 문서**: [네트워크 구성](../../eks-hybrid-nodes/02-network-configuration.md)

## 객관식 문제

### 1. EKS Hybrid Nodes에서 온프레미스와 클라우드 간 네트워크 연결에 권장되는 방식은?

A. 인터넷 공용 연결
B. AWS Direct Connect 또는 Site-to-Site VPN
C. SSH 터널링
D. HTTP 프록시

<details>
<summary>정답 보기</summary>

**정답: B. AWS Direct Connect 또는 Site-to-Site VPN**

**설명:**
EKS Hybrid Nodes는 EKS 컨트롤 플레인과 안정적이고 보안된 네트워크 연결이 필요합니다. AWS Direct Connect(전용선) 또는 Site-to-Site VPN이 권장됩니다.

**네트워크 요구사항:**
- EKS API 서버 엔드포인트 접근 (443/TCP)
- AWS 서비스 엔드포인트 접근 (ECR, S3, STS 등)
- 안정적인 저지연 연결

```bash
# Site-to-Site VPN 설정 확인
aws ec2 describe-vpn-connections \
  --filters Name=state,Values=available

# VPN 연결 상태 모니터링
aws cloudwatch get-metric-statistics \
  --namespace AWS/VPN \
  --metric-name TunnelState \
  --dimensions Name=VpnId,Value=vpn-xxxxxx
```

</details>

### 2. Hybrid Nodes가 EKS 컨트롤 플레인과 통신하기 위해 필수로 열어야 하는 방화벽 포트는?

A. 22/TCP (SSH)
B. 443/TCP (HTTPS)
C. 8080/TCP (HTTP Proxy)
D. 3306/TCP (MySQL)

<details>
<summary>정답 보기</summary>

**정답: B. 443/TCP (HTTPS)**

**설명:**
Hybrid Nodes는 EKS API 서버와 HTTPS(443/TCP)로 통신합니다. 필수 방화벽 규칙:

| 포트 | 프로토콜 | 용도 | 방향 |
|-----|---------|-----|-----|
| 443 | TCP | EKS API 서버, AWS 서비스 | 아웃바운드 |
| 10250 | TCP | kubelet API | 인바운드 |
| 10255 | TCP | kubelet 읽기 전용 | 인바운드 (선택) |

```bash
# 방화벽 규칙 확인 (iptables)
sudo iptables -L -n

# 연결 테스트
curl -v https://<eks-api-endpoint>:443/healthz
```

</details>

### 3. EKS Hybrid Nodes에서 AWS 서비스 접근을 위해 필요한 VPC 엔드포인트 3가지를 나열하면?

A. ec2, ecr.api, sts
B. lambda, dynamodb, sns
C. rds, elasticache, sqs
D. cloudfront, route53, waf

<details>
<summary>정답 보기</summary>

**정답: A. ec2, ecr.api, sts**

**설명:**
Hybrid Nodes가 AWS 서비스에 접근하기 위해 필요한 주요 VPC 엔드포인트:

1. **ec2.region.amazonaws.com** (EC2 API)
2. **ecr.api.region.amazonaws.com** (ECR API)
3. **sts.region.amazonaws.com** (STS - IAM 인증)

**추가 권장 엔드포인트:**
- `ecr.dkr.region.amazonaws.com` (ECR Docker Registry)
- `s3.region.amazonaws.com` (S3 - ECR 이미지 저장소)
- `logs.region.amazonaws.com` (CloudWatch Logs)
- `ssm.region.amazonaws.com` (Systems Manager)

```bash
# VPC 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.ap-northeast-2.sts \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxx \
  --security-group-ids sg-xxx
```

</details>

### 4. Hybrid Nodes 환경에서 Pod 네트워크(CIDR)를 구성할 때 고려해야 할 사항으로 올바르지 않은 것은?

A. 온프레미스 네트워크와 CIDR 충돌 방지
B. VPC CIDR과 Pod CIDR 분리
C. Pod CIDR은 반드시 /8 대역이어야 함
D. 클러스터 간 Pod CIDR 중복 방지

<details>
<summary>정답 보기</summary>

**정답: C. Pod CIDR은 반드시 /8 대역이어야 함**

**설명:**
Pod CIDR은 /8 대역일 필요가 없습니다. 일반적으로 /16 ~ /24 범위를 사용합니다. 주요 고려사항:

- **CIDR 충돌 방지**: 온프레미스, VPC, Pod 네트워크 간 겹침 없어야 함
- **적절한 크기**: 예상 Pod 수에 따라 CIDR 크기 결정
- **라우팅 가능성**: 온프레미스에서 Pod CIDR로 라우팅 가능해야 함

```yaml
# nodeadm 설정에서 Pod CIDR 구성
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      podCIDR: "10.244.0.0/16"
```

| 네트워크 유형 | 권장 CIDR 예시 |
|-------------|---------------|
| VPC | 10.0.0.0/16 |
| Pod | 10.244.0.0/16 |
| Service | 10.100.0.0/16 |
| 온프레미스 | 192.168.0.0/16 |

</details>

### 5. Hybrid Nodes에서 DNS 구성 시 클러스터 DNS 서버 주소로 일반적으로 사용되는 IP는?

A. 8.8.8.8
B. 10.100.0.10
C. 192.168.1.1
D. 169.254.169.254

<details>
<summary>정답 보기</summary>

**정답: B. 10.100.0.10**

**설명:**
EKS 클러스터에서 CoreDNS 서비스는 일반적으로 Service CIDR 범위 내의 고정 IP를 사용합니다. 기본값은 `10.100.0.10`입니다.

```yaml
# nodeadm 설정에서 클러스터 DNS 구성
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      clusterDNS:
        - 10.100.0.10
      clusterDomain: cluster.local
```

```bash
# CoreDNS 서비스 IP 확인
kubectl get svc -n kube-system kube-dns

# DNS 해결 테스트
kubectl run test --image=busybox --rm -it -- nslookup kubernetes.default
```

</details>

### 6. Hybrid Nodes와 클라우드 노드 간 통신을 위한 네트워크 지연 시간(latency) 권장 값은?

A. 500ms 이하
B. 200ms 이하
C. 100ms 이하
D. 50ms 이하

<details>
<summary>정답 보기</summary>

**정답: C. 100ms 이하**

**설명:**
Kubernetes API 서버와의 안정적인 통신을 위해 네트워크 지연 시간은 100ms 이하가 권장됩니다.

| 지연 시간 | 영향 |
|---------|-----|
| < 50ms | 최적 (Direct Connect 권장) |
| 50-100ms | 양호 (VPN 사용 가능) |
| 100-200ms | 경고 (일부 타임아웃 발생 가능) |
| > 200ms | 부적합 (잦은 연결 끊김) |

```bash
# 지연 시간 측정
ping -c 10 <eks-api-endpoint>

# TCP 연결 시간 측정
curl -w "Connect: %{time_connect}s\n" -o /dev/null -s https://<eks-api-endpoint>
```

Direct Connect를 사용하면 10ms 미만의 일관된 지연 시간을 달성할 수 있습니다.

</details>

