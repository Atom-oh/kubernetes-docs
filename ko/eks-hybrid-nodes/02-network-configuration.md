# 네트워크 구성

< [이전: 사전 요구 사항](./01-prerequisites.md) | [목차](./README.md) | [다음: 에어갭 환경 구성](./03-airgap-setup.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 EKS Hybrid Nodes 환경에서 필요한 방화벽 포트, Pod CIDR 방화벽 전략, DNS 구성을 다룹니다.

## 필수 방화벽 포트

온프레미스와 AWS 간 통신을 위해 다음 포트를 열어야 합니다:

| 포트 | 프로토콜 | 방향 | 용도 |
|------|----------|------|------|
| 443 | TCP | 양방향 | Kubernetes API 서버 |
| 10250 | TCP | AWS → On-Prem | Kubelet API |
| 53 | TCP/UDP | 양방향 | DNS 쿼리 |
| 4500 | UDP | 양방향 | IPSec NAT-T (VPN) |
| 500 | UDP | 양방향 | IKE (VPN) |

### iptables 규칙 예시

```bash
# Kubernetes API 서버 통신 허용
sudo iptables -A INPUT -p tcp --dport 443 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 443 -d 10.0.0.0/8 -j ACCEPT

# Kubelet API 허용
sudo iptables -A INPUT -p tcp --dport 10250 -s 10.0.0.0/8 -j ACCEPT

# DNS 허용
sudo iptables -A INPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

# 규칙 저장
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

## Pod CIDR 방화벽 전략

Pod 간 통신을 위해 전체 Pod CIDR 범위에 대한 방화벽 규칙을 등록해야 합니다.

```bash
# Pod CIDR 범위 예시: 10.244.0.0/16
# 클러스터의 Pod CIDR 확인
kubectl cluster-info dump | grep -m 1 cluster-cidr

# Pod CIDR에 대한 방화벽 규칙 추가
sudo iptables -A INPUT -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -d 10.244.0.0/16 -j ACCEPT

# Service CIDR도 추가 (예: 172.20.0.0/16)
sudo iptables -A INPUT -s 172.20.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 172.20.0.0/16 -j ACCEPT
```

## DNS 구성

### Route 53 Resolver Inbound Endpoint

온프레미스에서 AWS 도메인을 쿼리할 수 있도록 Inbound Endpoint를 생성합니다.

```bash
# Inbound Endpoint 생성
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-inbound-$(date +%s)" \
  --name "hybrid-inbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction INBOUND \
  --ip-addresses SubnetId=subnet-111111111,Ip=10.0.1.10 SubnetId=subnet-222222222,Ip=10.0.2.10

# Endpoint IP 확인
aws route53resolver list-resolver-endpoint-ip-addresses \
  --resolver-endpoint-id rslvr-in-xxxxxxxxxxxxx
```

### Route 53 Resolver Outbound Endpoint

AWS에서 온프레미스 도메인을 쿼리할 수 있도록 Outbound Endpoint와 전달 규칙을 생성합니다.

```bash
# Outbound Endpoint 생성
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-outbound-$(date +%s)" \
  --name "hybrid-outbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction OUTBOUND \
  --ip-addresses SubnetId=subnet-111111111 SubnetId=subnet-222222222

# 전달 규칙 생성 (온프레미스 도메인)
aws route53resolver create-resolver-rule \
  --creator-request-id "forward-onprem-$(date +%s)" \
  --name "forward-to-onprem" \
  --rule-type FORWARD \
  --domain-name "internal.company.io" \
  --resolver-endpoint-id rslvr-out-xxxxxxxxxxxxx \
  --target-ips "Ip=192.168.1.10,Port=53" "Ip=192.168.1.11,Port=53"

# VPC에 규칙 연결
aws route53resolver associate-resolver-rule \
  --resolver-rule-id rslvr-rr-xxxxxxxxxxxxx \
  --vpc-id vpc-0123456789abcdef0
```

### CoreDNS 커스텀 도메인 구성

온프레미스 도메인에 대한 DNS 쿼리를 온프레미스 DNS 서버로 전달합니다.

```yaml
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
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
    internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
    harbor.internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
```

```bash
# CoreDNS ConfigMap 적용
kubectl apply -f coredns-configmap.yaml

# CoreDNS 재시작
kubectl rollout restart deployment coredns -n kube-system

# DNS 해석 테스트
kubectl run dns-test --rm -it --image=busybox --restart=Never -- nslookup harbor.internal.company.io
```

---

< [이전: 사전 요구 사항](./01-prerequisites.md) | [목차](./README.md) | [다음: 에어갭 환경 구성](./03-airgap-setup.md) >
