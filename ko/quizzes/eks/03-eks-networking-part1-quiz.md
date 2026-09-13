# EKS 네트워킹 퀴즈 - Part 1

> **마지막 업데이트**: 2026년 9월 11일

EKS 네트워킹·주소 계획·정책·컨트롤러 소유권을 다룹니다. 별도 설명이 없으면 일반 Linux EC2 네트워킹 예제입니다. 공식 자료·로컬 스키마로 API·구성을 검토했으며 클라우드 네트워크 변경이나 실제 패킷 테스트는 실행하지 않았습니다.

## 객관식 문제

1. 일반 EKS EC2 노드의 기본 CNI는 무엇인가요?
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>정답 보기</summary>

**정답: C) Amazon VPC CNI**

일반 EKS EC2 노드는 Amazon VPC CNI를 사용합니다. Auto Mode는 관리형 네트워킹을 제공하고 Hybrid Nodes는 지원되는 대체 CNI를 사용하므로 “모든 EKS 클러스터가 이 DaemonSet을 실행한다”는 설명은 과도합니다.

CNI는 VPC 주소로 일반 Pod 네트워크를 구성하며 보조 IP·prefix·Pod 보안 그룹 경로는 서로 다릅니다. 라우팅 가능한 주소가 라우트·보안 그룹·NACL·정책을 우회하지는 않으며 오버레이를 피한다고 실측 성능이 보장되는 것도 아닙니다.

Linux 예제에서 소문자 `warm-ip-target`·`enable-pod-eni` 키의 기존 `amazon-vpc-cni` ConfigMap은 올바른 설정 경로가 아닙니다. 실제 애드온 스키마·Helm 값 또는 지원되는 `aws-node` 환경변수를 소유자를 통해 관리하세요. 설치 빌드를 먼저 확인합니다:

```bash
set -euo pipefail
CNI_ADDON_VERSION=$(aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni --query addon.addonVersion --output text)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" --addon-name vpc-cni \
  --addon-version "$CNI_ADDON_VERSION" --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{": "}{.image}{"\n"}{end}'
```
다음은 Kubernetes ConfigMap이 아닌 **애드온 설정 조각**입니다. Warm pool 값은 예시이며 검토한 기존 설정과 병합하고 선택 버전의 스키마를 확인하세요. Windows IPAM ConfigMap 설정은 별도 인터페이스입니다.

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```
Pod 보안 그룹·기본 NetworkPolicy에는 각각 추가 선행조건이 있습니다. IP pool 예제를 적용하면서 무관한 기능까지 켜거나 동작 중인 클러스터에 구성하지 않은 두 번째 CNI를 적용하지 마세요.

</details>

2. IPv4 보조 IP 모드에서 일반 Pod에 주소를 어떻게 할당하나요?
   * A) Pod마다 전용 VPC
   * B) 노드 ENI·IP pool의 주소
   * C) 오버레이 주소만
   * D) Pod마다 별도 서브넷

<details>
<summary>정답 보기</summary>

**정답: B) 노드 ENI·IP pool의 주소**

일반 IPv4 보조 IP 모드에서는 IPAMD가 노드의 ENI·IP pool을 관리하고 CNI 설정이 pool 주소를 Pod 네트워크 네임스페이스에 할당합니다. CNI 정리·재사용 대기 후 주소가 warm pool로 돌아갈 수 있으며 EC2에서 즉시 할당 해제되는 것은 아닙니다.

아래 일반 max-Pods 계산은 이 모드의 예제입니다. ENI마다 기본 주소를 제외하며 마지막 2는 호스트 네트워크 시스템 Pod를 반영한 전통적인 여유분입니다:

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
m5.large: 3 × (10 − 1) + 2 = 29
```
보편적인 워크로드 한도는 아닙니다. 서브넷 공간·kubelet maxPods·컴퓨팅 자원·커스텀 네트워킹·branch ENI 한도도 중요합니다. Prefix 모드는 ENI 주소 슬롯에 /28을 할당하며 ENI당 정확히 한 prefix만 사용하는 것이 아닙니다. Pod 보안 그룹은 별도 branch ENI 경로를 사용합니다. HostNetwork Pod는 노드 네트워크를 공유하므로 단순한 Pod당 보조 IP 설명의 또 다른 예외입니다.

</details>

3. 일반 VPC CNI의 VPC 내부 라우팅 모델을 가능하게 하는 것은 무엇인가요?
   * A) 모든 Pod가 한 서브넷 사용
   * B) 모든 Pod가 호스트 네트워크 공유
   * C) 필요한 경로·제어와 VPC 라우팅 가능한 Pod 주소
   * D) 필수 서비스 메시

<details>
<summary>정답 보기</summary>

**정답: C) 필요한 경로·제어와 VPC 라우팅 가능한 Pod 주소**

일반 VPC CNI 경로의 Pod는 VPC에서 라우팅 가능한 주소를 사용합니다. 노드 간 트래픽은 노드·ENI·VPC 라우팅을 사용할 수 있고 같은 노드의 트래픽은 호스트 네트워크 스택 안에 남을 수 있습니다. SG·NACL·정책·검사 장비용 커스텀 경로가 실제 도달 가능성을 결정합니다.

`10.0.1.23 → 10.0.2.45` 예제는 일반적인 VPC 내부 경로이며 모든 패킷이 항상 VPC 라우팅 테이블을 거치거나 구성된 검사 장비 경로를 절대 사용하지 않는다는 증명이 아닙니다. 같은 노드의 Pod 트래픽은 VPC Flow Logs에 완전히 보이지 않습니다. 대부분의 Pod는 자체 네트워크 네임스페이스를 가지지만 hostNetwork Pod는 예외입니다.

오버레이가 없다는 이유로 지연·처리량 개선을 보장하면 안 됩니다. 실제 경로를 측정하고 AZ 간 전송·대상 유형·SNAT·워크로드 동작을 고려하세요. 서비스 메시는 선택적 추가 계층이며 일반 Pod 라우팅의 필수조건은 아닙니다.

</details>

4. Pod ingress·egress 정책을 표현하는 Kubernetes 리소스는 무엇인가요?
   * A) Service
   * B) Ingress
   * C) NetworkPolicy
   * D) SecurityContext

<details>
<summary>정답 보기</summary>

**정답: C) NetworkPolicy**

NetworkPolicy는 Pod를 선택하고 지정한 트래픽 방향만 격리합니다. 해당 Pod·방향을 선택하는 정책이 없으면 격리되지 않습니다. 정책은 합산되므로 제한적으로 보이는 정책을 추가해도 다른 정책이 허용한 트래픽을 제거하지 못합니다.

호환 집행 구현을 사용하세요. 현재 Amazon VPC CNI는 활성화 시 기본 네트워크 정책을 지원하므로 집행할 수 없다는 기존 설명은 잘못되었습니다. 관리형 애드온은 추정한 `ENABLE_NETWORK_POLICY` 환경변수가 아닌 `enableNetworkPolicy` 설정 필드를 사용합니다:

```json
{"enableNetworkPolicy":"true"}
```
선택한 애드온 버전·스키마에 맞춰 소유자를 통해 병합할 설정 조각입니다. 테스트 전에 정책 에이전트와 AWS의 컴퓨팅·커널·Pod 소유자·인터페이스 제한을 확인하세요. Standard 시작 모드는 정책 연결 전 잠시 트래픽을 허용할 수 있고 strict 모드는 필요한 시스템·DNS 허용 규칙이 모두 필요합니다. 지원되는 마이그레이션 설계 없이 floating Calico 매니페스트와 기본 정책 집행을 동시에 설치하지 마세요.

다음은 검토한 실습 네임스페이스와 컨트롤러 관리 워크로드용입니다. **같은 피어 항목의** 네임스페이스·Pod 셀렉터는 AND이며 항목을 나누면 OR입니다. DNS 예외도 명시합니다:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: policy-lab
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend-lab
      podSelector:
        matchLabels: {role: frontend}
    ports:
    - {protocol: TCP, port: 8080}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: database-lab
      podSelector:
        matchLabels: {app: database}
    ports:
    - {protocol: TCP, port: 5432}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels: {k8s-app: kube-dns}
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
```
실제 네임스페이스·Pod 레이블과 리스너 포트를 사용하세요. NodeLocal DNSCache 등 다른 DNS 경로는 별도 허용이 필요합니다. Service·Ingress는 트래픽을 라우팅하며 이 L3·L4 접근 규칙을 대체하지 않습니다. SecurityContext는 워크로드 권한을 제어하며 선언적인 네트워크 허용 목록은 아닙니다.

</details>

5. 일반 EKS 클러스터 서비스 검색에 보통 구성하는 DNS 구성 요소는 무엇인가요?
   * A) Route 53 프라이빗 호스팅 영역만
   * B) CoreDNS
   * C) 필수 기존 kube-dns Deployment
   * D) Cloud Map만

<details>
<summary>정답 보기</summary>

**정답: B) CoreDNS**

일반 EKS는 클러스터 DNS로 CoreDNS를 사용합니다. 모든 EKS 모드가 보이는 CoreDNS Deployment를 자동 생성한다고 가정하면 안 됩니다. Auto Mode는 관리형 DNS를 제공하며 기본 부트스트랩 애드온을 끄는 도구는 선택한 애드온을 명시적으로 구성해야 합니다.

EKS 관리형 CoreDNS는 지원되는 `corefile` 설정 값과 정확한 버전의 스키마로 커스텀 구성을 보존합니다. ConfigMap 직접 수정은 애드온이 덮어쓸 수 있습니다. 자체 관리 CoreDNS는 매니페스트·GitOps 소유자를 통해 변경하세요. 일반 예제로 전체 ConfigMap을 교체하지 말고 필요한 `ready`·전달·Kubernetes 영역·reload 동작을 검토합니다.

DNS 응답은 리소스 유형에 따라 다릅니다:

| 리소스 | 일반적인 DNS 동작 |
| --- | --- |
| 일반 Service | `<service>.<namespace>.svc.<cluster-domain>`이 Service IP 주소군으로 해석 |
| Headless Service | 준비·게시 설정에 따른 엔드포인트 주소 |
| ExternalName Service | 설정된 외부 이름으로 CNAME |
| 기존 IPv4 Pod 레코드 | CoreDNS `pods` 모드에 따라 `10-0-1-23.<namespace>.pod.<cluster-domain>` 같은 하이픈 주소 사용 |

`cluster.local`은 흔한 기본값이지 보편적인 도메인이 아닙니다. `pods insecure`는 Pod 존재를 검증하지 않는 기존 IP 기반 응답이며 보안 보장이 아닙니다. 임의 노트북 DNS가 아닌 승인된 클러스터 내부 진단 워크로드에서 테스트하세요.

EKS 관리형 CoreDNS는 호환 애드온 버전에서 설정된 오토스케일링을 지원합니다. 복제본 제어자는 하나로 유지하며 관리형 오토스케일링·HPA가 활성화된 상태에서 수동 `kubectl scale`로 경쟁시키면 안 됩니다.

다음은 검토 후 기존 cache 구문을 대체하는 **Corefile 조각**이며 YAML이 아닙니다. CoreDNS 1.14.7은 `denial 1000`을 수용하지만 실제 최소 용량 1024로 보정합니다. 예제는 그 용량을 명시하며 `success 10000`은 9984로 내림 조정됩니다:

```text
cache {
    success 10000
    denial 1024
    prefetch 10 10m 20%
}
```
캐시 용량·TTL·prefetch 설정에는 워크로드 측정이 필요하며 이 예제는 성능 벤치마크가 아닙니다. 제어된 변경 후 DNS 오류·캐시 동작·CPU·메모리를 확인하세요.

</details>

## 단답형 문제

6. Pod 밀도를 제한하는 요소와 prefix delegation의 영향은 무엇인가요?

<details>
<summary>정답 보기</summary>

EC2 인터페이스·주소 용량, 서브넷 가용 주소, Kubernetes·컴퓨팅 용량을 구분합니다. 일반 IPv4 보조 IP 모드의 전통적인 식은 `ENI 수 × (ENI당 IP 수 − 1) + 2`이며 t3.small은 11, m5.large는 29, c5.4xlarge는 234입니다. 모든 관리형 그룹의 실제 한도가 아닌 계산식 결과입니다.

IPv4 prefix 모드에서 `/28` 하나는 주소 16개를 제공하고 보조 주소 슬롯 하나를 차지합니다. ENI에 여러 prefix를 할당할 수 있으므로 기존의 “ENI당 prefix 하나에서 주소 하나 제외”로 m5.large를 47로 계산한 식은 잘못되었습니다. 호환 관리형 그룹의 maxPods 상한은 30 vCPU 미만이면 110, 그 외에는 250이며 CPU·메모리·실제 CNI 설정에 따라 사용 가능한 워크로드 용량은 더 작을 수 있습니다.

관리형 애드온 설정 조각 예제는 다음과 같습니다:

```json
{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
```
정확한 버전 스키마와 기존 구성을 검토한 후 병합합니다. WARM_PREFIX_TARGET은 여유 prefix 용량이며 ENI당 prefix를 하나로 제한하는 값이 아닙니다. WARM_IP_TARGET·MINIMUM_IP_TARGET을 설정하면 해당 동작보다 우선합니다. Prefix 모드는 연속 /28 공간과 지원 인스턴스·CNI가 필요하며 서브넷을 확장하지 않습니다.

Prefix delegation과 Pod 보안 그룹은 함께 사용할 수 있습니다. Branch ENI Pod는 여전히 인스턴스별 branch 한도를 사용하며 prefix 밀도 증가 혜택을 받지 않습니다. 변수만 바꾸고 모든 실행 Pod·maxPods가 바뀌었다고 가정하지 말고 새 노드·교체 노드와 PDB를 고려한 이전을 계획하세요. 커스텀 AL2023 AMI에는 검토한 NodeConfig maxPods가 필요할 수 있으며 kubelet 한도만 높여도 IP·CPU가 생기지는 않습니다.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -o custom-columns=NAME:.metadata.name,PODS:.status.allocatable.pods,POD_ENI:.status.allocatable.vpc\\.amazonaws\\.com/pod-eni
```
실제 할당 가능 용량과 CNI·EC2 할당을 확인합니다. aws-node 컨테이너에 curl이 있다고 가정하지 말고 설치 빌드·대상 노드의 문서화된 introspection·디버그 경로를 사용하세요.

</details>

7. 일반 EKS EC2 노드의 선택된 Pod에 보안 그룹을 어떻게 지정하나요?

<details>
<summary>정답 보기</summary>

Pod 보안 그룹은 **노드의 trunk ENI와 선택된 Pod의 branch ENI**를 사용합니다. EKS VPC resource controller가 `AmazonEKSVPCResourceController` 등을 포함한 **클러스터 IAM 역할** 권한으로 경로를 생성·관리하며 단순히 Pod ServiceAccount에 권한을 주는 방식이 아닙니다.

일반 Linux EC2 예제는 trunking을 지원하는 인스턴스 유형(모든 Nitro 유형은 아님), 호환 VPC CNI와 소유자를 통해 설정한 `ENABLE_POD_ENI=true`를 확인합니다. `POD_SECURITY_GROUP_ENFORCING_MODE`, DNS·프로브·라우팅·SG 규칙도 검토하세요. Strict·standard 모드는 특히 VPC 외부·노드 내부 경로에서 SNAT와 적용 SG가 다릅니다.

전용 `sgp-lab` 네임스페이스를 만들고 SG 자리표시자를 올바른 VPC의 승인된 그룹으로 바꿉니다. 다음 컨트롤러 관리 대기 클라이언트는 선택 관계를 보여 주며 DB 접근 성공을 검증하지 않습니다:

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: sgp-lab
spec:
  podSelector:
    matchLabels: {role: db-client}
  securityGroups:
    groupIds: [sg-REPLACE_WITH_APPROVED_GROUP]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: sgp-lab
spec:
  replicas: 1
  selector:
    matchLabels: {role: db-client}
  template:
    metadata:
      labels: {role: db-client}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
필요에 따라 podSelector 또는 serviceAccountSelector를 사용합니다. 새 Pod, CNINode·branch 용량과 실제 허용·차단 연결을 확인하세요. SecurityGroupPolicy 선택 변경은 실행 중인 Pod에 소급 적용되지 않으며 SG 규칙 자체의 변경은 연결 추적 동작이 별도로 적용됩니다. HostNetwork Pod는 노드 네트워크를 사용합니다.

Prefix delegation과 호환되지만 branch ENI Pod 용량을 늘리지는 않습니다. 기존 SecurityGroupPolicy와 Auto Mode NodeClass의 Pod 서브넷·SG 선택 기능은 같은 API가 아니므로 해당 컴퓨팅의 문서를 따라야 합니다.

</details>

8. AWS Load Balancer Controller가 LoadBalancer Service에 만드는 로드 밸런서와 소유권 설정은 무엇인가요?

<details>
<summary>정답 보기</summary>

AWS Load Balancer Controller는 LoadBalancer Service로 **NLB**를 생성하며 CLB를 생성하지 않습니다. 기존 퀴즈는 이를 이전 in-tree Service 컨트롤러와 혼동했습니다. 현재 LBC의 명시적 소유권은 `service.k8s.aws/nlb`이며 v2.2부터 새 NLB의 기본 scheme은 **internal**입니다. 의도한 scheme을 명시하세요.

다음은 컨트롤러 설치·권한과 적격 서브넷·SG 규칙을 검증한 뒤 `lb-lab`의 검토된 기존 `app=echo` 워크로드를 대상으로 하는 새 Service입니다. 유료 내부 NLB를 생성하므로 프로덕션 네임스페이스에 임의로 적용하면 안 됩니다:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-nlb
  namespace: lb-lab
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector: {app: echo}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
```
IP 대상은 적격 Pod IP로 전달하고 instance 대상은 노드·NodePort 경로를 사용합니다. 예제는 IP 모드에서 사용하지 않는 NodePort 할당을 끕니다. Auto Mode는 별도 소유권 클래스(`eks.amazonaws.com/nlb`)와 지원 설정을 사용합니다. 기존 legacy Service의 컨트롤러 선택 어노테이션·클래스를 검토 없이 바꾸면 리소스가 남거나 외부로 노출될 수 있습니다.

**설정 선택**은 컨트롤러 버전과 리스너 설계에 맞춰야 합니다: 표의 어노테이션 이름은 공통 `service.beta.kubernetes.io/` 접두사를 생략했습니다.

| 요구 | 현재 설정·고려 사항 |
| --- | --- |
| 내부·퍼블릭 scheme | `aws-load-balancer-scheme: internal` 또는 `internet-facing`; 라우팅·서브넷도 일치해야 함 |
| IP 대상 | `aws-load-balancer-nlb-target-type: ip` |
| 커스텀 프런트엔드 SG | `aws-load-balancer-security-groups`; 백엔드 규칙 관리·상태 확인 경로 검토 |
| 명시적 서브넷 | `aws-load-balancer-subnets`; 적격성·AZ·IP 제약은 유지 |
| 교차 영역 동작 | `aws-load-balancer-attributes`의 `load_balancing.cross_zone.enabled`; 가용성·토폴로지·비용 평가 |
| 기존 S3 접근 로그 | `aws-load-balancer-attributes`의 `access_logs.s3.*`; NLB는 TLS 요청만 기록하며 버킷·전달 권한 검토 필요 |
| TLS 종료 | `aws-load-balancer-ssl-cert`와 Service 리스너에 맞는 `aws-load-balancer-ssl-ports`; NLB TLS 종료이지 ALB HTTP 라우팅은 아님 |

기존 `aws-load-balancer-internal`·교차 영역·접근 로그 어노테이션 대신 scheme·attributes 설정을 사용합니다. 현재 NLB는 향상된 CloudWatch 로그 전달도 제공하므로 S3 어노테이션이 그 기능까지 구성한다고 가정하지 말고 해당 통합 문서를 따르세요. 접근 로그는 최선형이며 전체 요청 회계 기록이 아닙니다.
**ALB 대안:** 구성된 `alb` IngressClass와 IP 대상으로 ClusterIP 백엔드에 연결합니다. 같은 예제 백엔드에 NLB·ALB를 실수로 모두 만드는 것을 피합니다:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-backend
  namespace: lb-lab
spec:
  type: ClusterIP
  selector: {app: echo}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: echo-alb
  namespace: lb-lab
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: echo-backend
            port: {number: 8080}
```
설치 전에 컨트롤러 ServiceAccount와 범위를 제한한 IAM 권한을 준비합니다. 검토한 차트 3.5.0은 컨트롤러 v3.5.0을 포함하며 IMDS 검색이 없는 환경을 위해 리전·VPC를 명시합니다. 배포 전에 렌더링·검토하세요:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm template aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --kube-version 1.36.0 --namespace kube-system \
  --set-string clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string region="${EXAMPLE_REGION:?}" --set-string vpcId="${EXAMPLE_VPC_ID:?}" \
  --set serviceAccount.create=false --set-string serviceAccount.name=aws-load-balancer-controller \
  > lbc-reviewed.yaml
```
| 기능 | CLB(기존) | NLB | ALB |
| --- | --- | --- | --- |
| 주요 라우팅 계층 | 기존 L4·L7 리스너 | L4 | HTTP·HTTPS L7 |
| 직접 IP 대상 | 아니요 | 예 | 예 |
| AZ별 정적 주소 선택 | 아니요 | 예 | 기본 정적 프런트엔드 IP 없음 |
| HTTP 경로 라우팅 | 아니요 | 아니요 | 예 |

현재 NLB는 TCP·TLS·UDP·TCP_UDP·QUIC·TCP_QUIC 리스너를 지원합니다. 컨트롤러 지원·설정은 별도로 확인해야 하며 LBC 3.5는 QUIC 포트 어노테이션을 문서화합니다. 기존 “좋음·매우 좋음” 성능 표는 벤치마크가 아니었습니다. 애플리케이션에 맞게 선택·측정하며 모든 환경의 교차 영역 활성화나 일괄 지연 순위를 프로덕션 규칙으로 삼지 마세요.

</details>

## 실습 문제

9. 같은 네임스페이스 통신·DNS 예외와 네임스페이스 간 TCP 차단을 구현·검증하세요.

<details>
<summary>정답 보기</summary>

대상 네임스페이스의 모든 Pod를 선택하고 같은 네임스페이스 피어와 명시적인 DNS 예외를 허용합니다. L3·L4 정책이며 완전한 테넌트·노드 격리를 입증하지는 않습니다.

**선행조건:** 승인된 일반 IPv4 Linux 테스트 클러스터, 지원 소유자·설정 경로로 이미 활성화된 VPC CNI NetworkPolicy, 컨트롤러 관리 테스트 Pod, 동작하는 CoreDNS와 충돌하지 않는 조직 정책이 필요합니다. 실습 중 Calico를 설치하거나 추정한 `ENABLE_NETWORK_POLICY` 변수를 켜지 마세요.

새 네임스페이스 두 개를 만들고 UID를 기록합니다. 아래 코드는 같은 Bash 세션에서 사용하세요:

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed IPv4 Linux lab cluster kubeconfig}"
NP_LAB_DIR=$(mktemp -d /tmp/eks-network-policy.XXXXXX)
NP_LAB_ID="$(date +%s)-$$"
NP_NAMESPACE_A="np-a-$NP_LAB_ID"
NP_NAMESPACE_B="np-b-$NP_LAB_ID"
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$ns" -o json \
    > "$NP_LAB_DIR/$ns-created.json"
  jq -e '.metadata.uid | type == "string" and length > 0' \
    "$NP_LAB_DIR/$ns-created.json" >/dev/null
done
```
HTTP 서버에서 확인 가능한 Python TCP 진단도 사용합니다. Service·컨테이너 포트는 모두 8080입니다. 프로덕션 사이징이 아닌 테스트 워크로드이며 재현성을 위해 이미지 digest를 기록하세요.

```bash
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: network-probe
spec:
  replicas: 1
  selector:
    matchLabels: {app: network-probe}
  template:
    metadata:
      labels: {app: network-probe}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: probe
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: network-probe
spec:
  type: ClusterIP
  selector: {app: network-probe}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" \
    rollout status deployment/network-probe --timeout=180s
done
```
**기본 연결:** 정책 적용 전에 네임스페이스 내부·상호 TCP 연결이 모두 성공해야 합니다. DNS·exec 실패는 TCP 차단과 구분합니다. ICMP ping은 이식 가능한 NetworkPolicy 집행 테스트가 아닙니다.

```bash
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$1" exec deployment/network-probe \
    -c probe -- python -c '
import socket, sys
try:
    address = socket.gethostbyname(sys.argv[1])
except OSError as error:
    print("DNS failed:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, 8080), timeout=3)
    connection.close()
except OSError as error:
    print("TCP failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP succeeded")
' "network-probe.$2"
}

# All four paths must work before applying the policy.
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"
```
**네임스페이스 A에만 적용:** 피어의 빈 podSelector는 정책과 같은 네임스페이스의 Pod를 선택합니다. DNS 피어는 kube-system 네임스페이스와 CoreDNS Pod 레이블을 함께 사용합니다. NodeLocal DNSCache 등 다른 DNS 경로는 수정해야 합니다. 정책 연결은 비동기이므로 허용 대조군과 양방향 차단으로 전파를 확인하세요:

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NP_NAMESPACE_A" create -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-boundary
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
EOF

expect_tcp_block() {
  if check_tcp "$1" "$2"; then
    return 1
  else
    result=$?
    [ "$result" -eq 42 ] || {
      printf '%s\n' 'DNS or exec failure is not proof of policy denial.' >&2
      exit 1
    }
    return 0
  fi
}
NP_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
  check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
  if expect_tcp_block "$NP_NAMESPACE_A" "$NP_NAMESPACE_B" &&
     expect_tcp_block "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"; then
    # Repeat positive controls after observing both blocked cross-namespace paths.
    check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
    check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
    NP_VERIFIED=true
    break
  fi
  sleep 2
done
[ "$NP_VERIFIED" = true ] || {
  printf '%s\n' 'Expected policy behavior was not observed; inspect the enforcement path.' >&2
  exit 1
}
```
성공은 DNS·서버 가용성을 확인한 상태에서 테스트한 TCP 경로가 예상대로 동작했다는 의미이며 모든 프로토콜·인터페이스가 필터링된다는 뜻은 아닙니다. 노드·메타데이터 서비스·보안 그룹 통제는 별도로 유지하세요.

**확장:** 같은 네임스페이스의 특정 Pod·포트만 허용하려면 광범위한 내부 허용을 교체·검토해야 합니다. 좁은 정책 추가로 기존 넓은 허용을 제거할 수는 없습니다. 검토한 외부 API에는 필요한 CIDR·포트를 선택하는 egress 정책을 추가할 수 있으며 아래 문서용 주소는 실제 목적지가 아닙니다:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-reviewed-external-api
  namespace: app-namespace
spec:
  podSelector:
    matchLabels: {app: web}
  policyTypes: [Egress]
  egress:
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - {protocol: TCP, port: 443}
```
표준 NetworkPolicy는 FQDN 허용 목록을 제공하지 않습니다. NAT·엔드포인트 선택에 따라 평가하는 IP가 달라질 수 있습니다. RFC1918만 제외한 `0.0.0.0/0`은 특정 외부 서비스 규칙도, 링크 로컬 메타데이터 엔드포인트의 완전한 보호도 아닙니다.

테스트 후 기록한 네임스페이스만 정리합니다:

```bash
for ns in "${NP_NAMESPACE_A:?}" "${NP_NAMESPACE_B:?}"; do
  expected_uid=$(jq -er '.metadata.uid' "${NP_LAB_DIR:?}/$ns-created.json") || exit 1
  current_uid=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get namespace "$ns" \
    --ignore-not-found -o jsonpath='{.metadata.uid}') || exit 1
  if [ -z "$current_uid" ]; then
    continue
  elif [ "$current_uid" = "$expected_uid" ]; then
    kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" delete namespace "$ns" --wait=true || exit 1
  else
    printf '%s\n' 'Namespace UID changed; no deletion attempted for this namespace.' >&2
    exit 1
  fi
done
```

</details>

## 고급 문제

10. VPC CNI 주소 부족 해결책을 비교하고 노드 밀도와 전체 주소 공간을 구분하세요.

<details>
<summary>정답 보기</summary>

먼저 부족한 자원이 서브넷 주소·연속 prefix 블록·노드 ENI 슬롯·branch ENI·kubelet maxPods·컴퓨팅 용량 중 무엇인지 확인합니다. 각각 해결책이 다르므로 “prefix delegation이 항상 가장 간단한 해법”이라는 기존 결론은 과도했습니다.

| 방식 | 도움이 되는 대상 | 중요한 한계 |
| --- | --- | --- |
| Prefix delegation | 일반 ENI 슬롯당 Pod 주소 증가·할당 효율 | 연속 /28 필요; IPv4 공간·branch ENI 용량은 늘리지 않음 |
| Warm·minimum pool 조정 | 사용하지 않는 사전 할당 주소 | 할당 준비·API 호출과 주소 사용의 균형 |
| 커스텀 네트워킹 | 노드·Pod 서브넷 수요 분리 | 같은 VPC·AZ, 라우팅·SG·계획된 노드 이전 필요 |
| VPC CIDR·서브넷 추가 | 할당 가능한 주소 공간 증가 | 중복·쿼터·라우팅·제어 플레인 반영 검토 |
| 더 큰 새 서브넷 | 계획된 주소 증가 | 기존 서브넷 단순 크기 변경 불가; 연결 VPC CIDR에 포함되어야 함 |
| IPv6 클러스터 설계 | 공유 IPv4 Pod 주소 압박 감소 | 새 클러스터·IP family 계획, 지원 컴퓨팅·CNI·egress 필요 |
| 대체 CNI | 다른 IPAM·라우팅 모델 | 지원·테스트한 이전 절차 필요; 매니페스트 토글만으로 전환 불가 |
| Fargate | 노드·IP 할당 운영 위임 | Pod마다 서브넷·VPC 주소를 사용하므로 고갈된 서브넷을 해결하지 않음 |

**Prefix 모드:** 일반 IPv4 prefix는 주소 슬롯 하나를 쓰는 /28 블록입니다. 기존 “최대 5배”는 검증되지 않은 일반적 주장이지 벤치마크가 아닙니다. 실제 인스턴스·CNI·kubelet 한도를 사용하세요. Pod 보안 그룹과 함께 사용할 수 있지만 branch Pod 한도는 그대로입니다. 단편화를 확인하고 필요하면 prefix 공간 예약·새 서브넷을 사용합니다. 개별 가용 IP 개수만으로 연속 블록 존재를 판단하지 마세요.

**Warm pool:** `WARM_IP_TARGET`은 여유 주소, `MINIMUM_IP_TARGET`은 최소 총 할당량입니다. Prefix·ENI warm target보다 우선할 수 있습니다. 예시 5·10은 워크로드·API 호출 예산에 맞춰 조정해야 합니다:

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```
`MAX_ENI`는 EC2 인스턴스 유형 상한 내에서 노드 할당을 제한합니다. 5로 설정해도 더 적은 ENI만 지원하는 유형이 5개를 사용할 수 있게 되지는 않습니다. 변경 전에 실제 할당 메트릭을 확인하세요.

**커스텀 네트워킹:** 같은 VPC·AZ의 Pod 서브넷·SG를 준비한 뒤 기존 CNI 소유자를 통해 설정을 병합합니다. 안정된 영역 레이블은 폐기된 beta 레이블이 아닌 `topology.kubernetes.io/zone`입니다:

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-REPLACE_WITH_POD_SUBNET_IN_SAME_VPC_AND_AZ
  securityGroups:
  - sg-REPLACE_WITH_APPROVED_POD_GROUP
```
사용하는 AZ마다 일치하는 ENIConfig를 만듭니다. 노드 annotation의 우선 적용도 검토하세요. 올바른 zone 레이블의 교체 노드는 기존 ENIConfig를 재사용하므로 매번 재생성할 필요가 없습니다. 실행 중인 모든 Pod의 네트워크가 즉시 바뀌지는 않습니다. 교체 노드를 검증하고 용량·PDB·데이터를 확인하며 이전합니다.

**CIDR·서브넷 변경:** 적격·비중복 CIDR과 서브넷을 IaC 소유자를 통해 추가하고 라우팅·보안·엔드포인트·검색 태그를 검토합니다. 새 VPC CIDR을 EKS 제어 플레인 작업이 인식하는 데 최대 한 시간이 걸릴 수 있습니다. /16 서브넷 생성에도 사용 가능한 연결 /16 범위가 필요하며 크기만 키운다고 VPC 한도를 우회하지는 않습니다.

**대체 CNI·IPv6:** 제어 플레인·DNS·Service 및 로드 밸런서·정책·부트스트랩·롤백 경로를 모두 계획합니다. 실행 중인 클러스터에 floating Calico overlay를 적용하고 aws-node를 끄는 것을 일반 전환 절차로 사용하지 마세요. 기존 EKS 클러스터의 IP family를 단순히 IPv6로 바꿀 수는 없습니다. 지원 범위·AWS 통합은 컴퓨팅·CNI 모드에 따라 달라집니다.

**Fargate:** 네임스페이스 레이블만으로 프로필이 생성되지 않으며 `eks.amazonaws.com/v1alpha1 kind: FargateProfile`은 기본 Kubernetes API가 아닙니다. EKS API·eksctl 또는 명시적으로 설치한 지원 컨트롤러를 사용합니다. 다음 API 예제는 미사용 프로필 이름·검토한 프라이빗 서브넷·실행 역할을 요구합니다:

```bash
# New profile example; this does not create or enlarge subnet address space.
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"ipam-fargate"}]'
```
일치하는 네임스페이스·워크로드를 별도로 만들고 프로필 활성화를 확인합니다. Fargate는 운영 책임을 바꾸지만 선택한 서브넷의 유한한 주소 용량을 바꾸지는 않습니다. 모든 전략을 함께 적용하지 말고 측정한 수요에 따라 비교하세요. 이번 감사에서 네트워크 이전이나 성능 벤치마크를 실행하지 않았습니다.

</details>


## VPC 기초 확인 문제

11. 퍼블릭 10.0.0.0/24·10.0.1.0/24와 겹치지 않고 정렬된 프라이빗 서브넷 쌍은 무엇인가요?
   * A) 10.0.2.0/22와 10.0.6.0/22
   * B) 10.0.4.0/22와 10.0.8.0/22
   * C) 10.0.0.0/22와 10.0.1.0/22
   * D) 문자열만 다르면 모두 가능

<details>
<summary>정답 보기</summary>

**정답: B) 10.0.4.0/22와 10.0.8.0/22**

/22는 세 번째 옥텟의 4 단위 경계에서 시작합니다. 10.0.2.0/22를 정규화하면 10.0.0.0/22가 되어 퍼블릭 범위와 겹칩니다.

</details>

12. 일반 AWS IPv4 /24 서브넷은 리소스 사용 전에 몇 개를 할당할 수 있나요?
   * A) 256
   * B) 254
   * C) 251
   * D) 항상 240

<details>
<summary>정답 보기</summary>

**정답: C) 251**

일반 서브넷마다 처음 4개·마지막 1개를 예약하므로 총 256개 중 251개를 할당할 수 있습니다. BYOIP에는 문서화된 예외가 있습니다.

</details>

13. elb 서브넷 역할 태그가 Internet Gateway 경로를 생성하나요?
   * A) 예
   * B) 아니요; 라우팅과 컨트롤러 검색은 별개
   * C) 프라이빗 서브넷에서만 가능
   * D) 모든 보안 그룹도 개방

<details>
<summary>정답 보기</summary>

**정답: B) 아니요; 라우팅과 컨트롤러 검색은 별개**

태그는 컨트롤러·버전·기능 게이트에 따라 검색에 영향을 주며 경로 생성이나 보안 경계를 제공하지 않습니다.

</details>

14. 모든 EKS 노드에 퍼블릭 인터넷 경로가 필수인가요?
   * A) 예, 항상 NAT Gateway 필요
   * B) 예, 항상 IGW 필요
   * C) 아니요; 필요한 서비스 접근은 적절한 프라이빗 엔드포인트·미러로 가능
   * D) 네트워크 접근 자체가 불필요

<details>
<summary>정답 보기</summary>

**정답: C) 아니요; 필요한 서비스 접근은 적절한 프라이빗 엔드포인트·미러로 가능**

실제 API·레지스트리·DNS·워크로드 의존성을 계획합니다. AWS EKS 서비스 엔드포인트와 Kubernetes 클러스터 API는 다릅니다.

</details>

15. 제어 플레인에서 kubelet로 향하는 일반적인 목적지 포트는 무엇인가요?
   * A) TCP 1025–65535 전체
   * B) TCP 10250
   * C) 기본적으로 모든 NodePort
   * D) UDP 53만

<details>
<summary>정답 보기</summary>

**정답: B) TCP 10250**

프라이빗 API TCP443·DNS TCP/UDP53·실제 웹훅 및 워크로드 포트·SG 연결을 별도 검토합니다. 상태 저장 SG의 응답 트래픽과 비상태 저장 NACL 규칙은 다릅니다.

</details>

## 참고 자료

- [VPC/subnet requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [VPC CNI 1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS native policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [LBC 3.5 Service annotations](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/annotations.md)
- [LBC subnet discovery](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/subnet_discovery.md)
- [NLB listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [NLB logs](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-access-logs.html)
- [CoreDNS cache](https://coredns.io/plugins/cache/)
- [CoreDNS cache implementation](https://github.com/coredns/coredns/blob/v1.14.7/plugin/pkg/cache/cache.go)
