# 5. 클라우드·CNI 네트워크 설계 워크북

> **마지막 업데이트**: 2026년 9월 15일

**선수 지식:** [프로토콜](01-protocol-projects.md), [라우팅](02-routing-policy-convergence.md), [Linux 관측](04-linux-performance.md), Kubernetes Pod·Service·EndpointSlice 개념. 실환경 관측에는 접근이 승인된 기존 실습 계정·클러스터와 필요한 조회 권한이 있어야 합니다.

**목표:** DNS 응답부터 backend와 반환 경로까지 설계·관측·정책을 연결합니다. 이 장의 명령은 기존 자원 조회입니다. 실제 장애 주입이나 리소스 생성은 포함하지 않습니다. 계정이 없으면 설계 과제를 수행하고 결과를 **설계 검토**로 표시합니다.

AWS CLI와 클러스터에 호환되는 kubectl을 먼저 준비하고, 실습 profile/context 설정을 확인합니다. 도구가 없다면 [AWS CLI 설치](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)와 [kubectl 설치](https://kubernetes.io/docs/tasks/tools/)의 플랫폼별 절차를 따릅니다. 이 워크북은 설치나 자격 증명 발급이 끝났다고 자동으로 가정하지 않습니다.

## 1. AWS 학습 범위를 질문으로 바꾸기 {#design-questions}

[AWS Advanced Networking 공식 범위](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)는 클라우드·하이브리드의 설계, 구현, 운영, 보안과 자동화를 다룹니다. 각 영역을 아래 질문으로 바꿔 자신의 설계에 적용합니다.

| 영역 | 답해야 할 질문 | 필요한 증거 |
|---|---|---|
| 주소·라우팅 | 목적지 prefix와 next hop은 무엇이며 반환 경로도 있는가? | VPC/subnet/TGW의 경로와 실제 출발·도착 주소 |
| 이름 해석 | 어느 resolver·zone·forwarding rule이 응답하는가? | 질의 이름·유형·resolver·응답·TTL·시각 |
| 진입점 | DNS가 가리키는 frontend와 등록된 backend는 무엇인가? | listener, target type, port, health check, 실제 대상 |
| 격리 | 허용할 흐름과 금지할 흐름을 어느 계층이 강제하는가? | SG/NACL/CNI 정책의 범위와 적용 결과 |
| 복원력 | 한 구성 요소가 실패하면 어떤 흐름이 영향을 받는가? | 가정한 고장 범위, 대체 경로, 상태 동기화·복구 계획 |
| 성능·비용 | 지연·처리량·주소 용량·데이터 이동의 조건은 무엇인가? | 측정 구간·방향·시간·자원 조건과 현재 비용 입력 |

시험 범위는 공부할 항목의 지도입니다. 실제 구현의 정답이나 특정 설계의 성능 보장이 아닙니다.

## 2. 환경과 권한부터 고정하기 {#inventory}

터미널에서 사용할 이름을 **실제 승인된 실습 값**으로 바꿉니다. 아래 문자열은 실행 가능한 계정 정보가 아닙니다.

```bash
LAB_AWS_PROFILE='REPLACE_WITH_LAB_PROFILE'
LAB_AWS_REGION='REPLACE_WITH_LAB_REGION'
LAB_CONTEXT='REPLACE_WITH_LAB_KUBERNETES_CONTEXT'
LAB_NAMESPACE='REPLACE_WITH_LAB_NAMESPACE'
LAB_SERVICE='REPLACE_WITH_LAB_SERVICE'
```

**운영자가 승인한 조회 터미널:**

```bash
aws --version
kubectl version --client
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  sts get-caller-identity
kubectl --context "$LAB_CONTEXT" auth can-i get services -n "$LAB_NAMESPACE"
kubectl --context "$LAB_CONTEXT" auth can-i list endpointslices.discovery.k8s.io \
  -n "$LAB_NAMESPACE"
```

계정·역할·context가 실습 대상과 다르면 중단합니다. `no`, `AccessDenied`, 만료된 자격 증명은 관측 권한이 없다는 결과입니다. 자동으로 관리자 권한을 부여하거나 다른 계정으로 재시도하지 않습니다. 권한이 없으면 승인된 운영자에게 필요한 최소 증거를 요청합니다.

원본 계정 ID·ARN·IP·리소스 이름은 승인된 노트에 보관합니다. 공개 보고서에는 같은 대상을 일관된 별칭으로 표시합니다. 설정 파일·Secret·토큰을 수집할 필요는 없습니다.

## 3. 요청 경로를 실제 자원에 대응시키기 {#request-path}

먼저 HTTP 요청 하나의 호스트 이름·프로토콜·포트·시각을 선택합니다. 다음 표는 확인할 관계이며, 모든 항목이 별개의 물리적 hop이라는 뜻은 아닙니다.

| 관측 대상 | 확인할 관계 | 흔한 오판 |
|---|---|---|
| DNS | 선택한 resolver가 반환한 frontend 주소 | 이름 해석 성공을 TCP/HTTP 성공으로 간주 |
| LB listener/target group | frontend 프로토콜·규칙과 target type/port | listener 포트와 backend 포트를 같은 값으로 가정 |
| Service | selector 또는 별도 관리 엔드포인트, port/targetPort | Service 객체가 있으면 endpoint가 있다고 가정 |
| EndpointSlice/Pod | 실제 주소·port·readiness·노드와 시각 | endpoint readiness를 LB health와 동일하게 취급 |
| CNI·노드·VPC | 주소 할당·경로·정책·전달 구현 | 모든 EKS 컴퓨팅 모드가 같은 DaemonSet·경로를 사용한다고 가정 |
| 반환 경로 | 응답의 목적지, SNAT·상태 추적·경로 | 정방향 도달성만으로 양방향 통신을 확정 |

AWS Load Balancer Controller는 AWS API를 통해 자원을 조정하는 **제어 평면**입니다. 애플리케이션 요청이 그 controller Pod를 통과하지는 않습니다.

일반적인 `ip` target은 등록된 backend IP로, `instance` target은 노드와 NodePort 경로로 연결됩니다. 지원되는 컴퓨팅/CNI 조합, 실제 target 등록, proxy 구현과 트래픽 정책을 확인해야 합니다. Service는 논리적인 엔드포인트 선택을 설명하며, ClusterIP를 항상 추가 패킷 hop으로 그리면 안 됩니다. [AWS의 target-type 설명](https://docs.aws.amazon.com/eks/latest/best-practices/load-balancing.html)과 [Kubernetes 가상 IP 구현](https://kubernetes.io/docs/reference/networking/virtual-ips/)을 함께 읽습니다.

### Service와 EndpointSlice 관측

```bash
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get service "$LAB_SERVICE" \
  -o jsonpath='{.spec.type}{"\n"}{.spec.selector}{"\n"}{.spec.ports}{"\n"}{.spec.externalTrafficPolicy}{"\n"}'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get endpointslices.discovery.k8s.io \
  -l "kubernetes.io/service-name=$LAB_SERVICE" -o json
```

EndpointSlice JSON에서 **같은 endpoint 객체의** 주소와 조건을 대응시킵니다. 여러 주소와 `ready` 값만 별도 배열로 펼쳐 놓고 위치를 임의로 맞추지 않습니다. `items: []`이면 이 선택 조건에서 엔드포인트를 관측하지 못한 것입니다. 그 원인이 DNS나 방화벽이라는 뜻은 아닙니다. selector 없는 Service와 수동 관리 엔드포인트도 고려합니다.

실제 selector를 확인한 뒤 필요한 Pod만 조회합니다.

```bash
LAB_SELECTOR='REPLACE_WITH_VERIFIED_KEY=VALUE'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get pods -l "$LAB_SELECTOR" -o wide
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" get networkpolicies
```

NetworkPolicy 객체 목록은 정책 엔진의 활성화나 강제 성공을 증명하지 않습니다. CNI·컴퓨팅 모드·지원 API·선택된 Pod·방향·포트와 실제 흐름을 별도로 확인합니다. 다른 정책 CRD나 관리형 정책이 있으면 해당 관리 주체의 증거도 필요합니다.

### AWS target과 경로 관측

운영자가 확인한 target group과 VPC를 지정합니다. 대상이 현재 Service와 연결된다는 근거도 함께 기록합니다.

```bash
LAB_TARGET_GROUP_ARN='REPLACE_WITH_VERIFIED_TARGET_GROUP_ARN'
LAB_VPC_ID='REPLACE_WITH_LAB_VPC_ID'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-groups --target-group-arns "$LAB_TARGET_GROUP_ARN" \
  --query 'TargetGroups[].{Type:TargetType,Port:Port,Protocol:Protocol,Vpc:VpcId,HealthPath:HealthCheckPath}'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-health --target-group-arn "$LAB_TARGET_GROUP_ARN"
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  ec2 describe-route-tables --filters "Name=vpc-id,Values=$LAB_VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
```

`healthy`는 설정된 health check의 결과이며 실제 사용자의 DNS·TLS·권한·요청 경로 전체를 검증하지 않습니다. 필드가 `null`이면 해당 프로토콜/설정에 필요한 필드인지부터 확인합니다. 이 워크북의 `ip`/`instance` 모델과 다른 target type이면 경로 모델을 다시 정합니다.

subnet의 명시적 route-table association이 없으면 main table 적용 여부를 확인합니다. 경로의 목적지·target·state와 실제 출발 subnet을 연결하고, 도착 측의 반환 경로도 읽습니다. 조회 권한이나 telemetry가 없으면 추정으로 채우지 않습니다.

## 4. 하이브리드 설계 과제 {#hybrid-design}

**설계용 시나리오:** 업무 VPC A는 공유 DNS/서비스에 접근해야 하고, 개발 VPC B는 A의 데이터 서비스에 직접 접근하면 안 됩니다. 온프레미스는 지정된 공유 서비스에만 접근합니다. 주소·실제 계정이 없는 경우 모두 별칭으로 그립니다.

1. 흐름 표에 출발지·목적지·프로토콜·허용/금지·반환 경로를 적습니다.
2. VPC/subnet/TGW route table과 attachment를 구분합니다.
3. TGW **association**은 attachment의 조회 경로, **propagation**은 경로를 배우는 위치임을 구분합니다. 하나의 attachment는 한 route table에 associate하고 여러 table에 propagate할 수 있습니다. 전파했다고 그 table을 조회하는 것은 아닙니다.
4. routing 분리와 SG/NACL/워크로드 정책 각각이 담당하는 조건을 적습니다.
5. 사설 DNS zone·resolver·forwarding rule과 양방향 질의 경로를 표시합니다.
6. 겹치는 CIDR, 누락된 반환 경로, propagation 오류를 하나씩 가정하고 어떤 흐름이 영향을 받는지 설명합니다.

[TGW association/propagation 근거](https://repost.aws/knowledge-center/transit-gateway-connect-vpcs-from-vpn)를 확인하고, 실제 환경은 [Cross-Org VPC 연결](../05-cross-org-vpc-connectivity.md)과 대조합니다. BGP policy 지식은 여기서 경로 의도를 설명하는 데 사용하며, 온프레미스 장비 명령을 TGW에 그대로 적용하지 않습니다.

## 5. 관측으로 판단하는 연습 {#failure-workbook}

아래는 **제공 증거나 자신이 승인받아 수집한 자료**로 분석할 문제입니다. 운영 계정의 정책을 변경하는 절차가 아닙니다.

| 관측 | 다음 확인 | 아직 결론 낼 수 없는 것 |
|---|---|---|
| DNS 응답은 있으나 TCP 연결 실패 | 대상·포트·경로·접근 제어·리스너 | DNS 정상만으로 backend 정상 확정 |
| EndpointSlice는 ready, target은 unhealthy | 등록 IP/port, health check 설정과 그 경로 | readiness와 LB health가 동일하다는 가정 |
| 같은 노드는 성공, 다른 노드는 실패 | 실제 CNI·노드/VPC 경로·정책·MTU·반환 경로 | “CNI 버그”라는 단일 원인 확정 |
| 작은 요청만 성공 | 패킷 크기·PMTU 피드백·재전송·애플리케이션 조건 | 모든 실패를 MTU로 분류 |
| TGW 한쪽 방향만 도달 | 각 attachment의 association과 양쪽 route table | propagation이 반환 경로까지 자동 보장 |

패킷/호스트 관측에는 별도 권한과 위치가 필요합니다. `get` 결과만으로 커널의 실제 전달 경로를 측정했다고 쓰지 않습니다. 노드·Pod namespace 관측은 승인된 운영자가 수행한 자료 또는 해당 실습 가이드의 별도 절차로 확보합니다.

## 6. 제출물과 완료 기준 {#completion}

- 허용·금지 흐름 표와 정방향·반환 경로 그림.
- 각 상자의 실제 역할: 제어 평면 / 라우팅 / 정책 / 애플리케이션.
- context·대상·시각이 연결된 Service/EndpointSlice/target/route 증거.
- 가설 두 개 이상을 비교하고, 확인·기각·미확인으로 구분한 이유.
- 배포 전 검증, 관측 범위, 복구 책임자와 복구 후 확인 항목.

실환경 증거가 없으면 **설계 검토 완료**까지 표시합니다. 클라우드 운영 검증 완료로 올리지 않습니다. 이 장의 조회는 자원을 변경하지 않으므로 네트워크 복구 명령이 필요하지 않습니다. 저장한 원본은 승인된 보관/폐기 규칙에 따라 관리합니다.

## 연결해서 읽기

- [EKS 네트워킹](../../eks/03-eks-networking-part1.md), [VPC CNI](../01-vpc-cni.md), [AWS Load Balancer Controller](../03-aws-lb-controller.md)
- [Pod 벤치마크의 측정 조건](../06-pod-network-benchmark.md), [Cilium 관측](../cilium/06-security-visibility.md)
- [EKS 네트워크 정책](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [NLB와 EKS의 지원 조건](https://docs.aws.amazon.com/eks/latest/userguide/network-load-balancing.html)
- [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [AWS CLI target health](https://docs.aws.amazon.com/cli/latest/reference/elbv2/describe-target-health.html)

[이전: Linux 성능](04-linux-performance.md) · [퀴즈](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) · [다음: 자동화·종합 평가](06-automation-capstone.md)
