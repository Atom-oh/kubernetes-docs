# 트러블슈팅 플레이북 퀴즈

> **관련 문서**: [Kubernetes/EKS 트러블슈팅 플레이북](../../ops/16-troubleshooting-playbook.md)

## 객관식 문제

### 1. `Pending` 파드의 `FailedScheduling` 이벤트가 다음과 같습니다. 이 메시지를 올바르게 해석한 것은?

```
0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
```

- A) 15개 노드 모두 CPU와 메모리가 부족하다
- B) 이 파드가 갈 수 있는 노드는 1개뿐이고, 그 노드의 CPU·메모리가 부족하다
- C) 스케줄러가 고장나서 아무 노드도 평가하지 못했다
- D) 8개 노드에 파드가 너무 많아(`Too many pods`) 스케줄이 실패했다

<details>
<summary>정답 보기</summary>

**정답: B) 이 파드가 갈 수 있는 노드는 1개뿐이고, 그 노드의 CPU·메모리가 부족하다**

**설명:**
스케줄러는 노드별 탈락 이유를 합산해서 보여줍니다. 8개는 toleration이 없는 taint 때문에, 6개는 nodeSelector/affinity 라벨 불일치 때문에 탈락했고, 남은 1개 노드는 CPU와 메모리가 모자랐습니다. 즉 스케줄 제약을 만족하는 노드가 1개뿐인데 그 노드가 꽉 찬 상황이므로, toleration/라벨을 넓히거나 해당 조건의 노드를 늘려야(Karpenter라면 NodePool requirements에 라벨 키가 있어야) 합니다.

</details>

### 2. 프라이빗 ECR 이미지를 쓰는 파드가 `ImagePullBackOff`이고, `describe` 이벤트에 `Failed to pull image "...dkr.ecr...": ... 401 Unauthorized` 가 보입니다. 가장 먼저 의심할 원인은?

- A) 이미지 태그 오타
- B) 노드 IAM 역할에 ECR pull 권한(`AmazonEC2ContainerRegistryPullOnly` 또는 `ReadOnly`)이 없음
- C) Docker Hub rate limit(`toomanyrequests`)
- D) 프라이빗 서브넷에 NAT/VPC 엔드포인트가 없음

<details>
<summary>정답 보기</summary>

**정답: B) 노드 IAM 역할에 ECR pull 권한(`AmazonEC2ContainerRegistryPullOnly` 또는 `ReadOnly`)이 없음**

**설명:**
`Failed to pull image` 뒤에 붙는 문구가 곧 진단입니다. `401 Unauthorized` / `no basic auth credentials`는 레지스트리 인증 실패이며, ECR은 kubelet이 노드 IAM 역할로 인증하므로 노드 역할의 ECR pull 권한을 확인해야 합니다. 태그 오타는 `not found` / `manifest unknown`, 네트워크 경로 문제는 `dial tcp ... i/o timeout`, Docker Hub 제한은 `toomanyrequests`로 나타납니다.

</details>

### 3. `CrashLoopBackOff` 파드의 `lastState.terminated`가 `Reason: OOMKilled`, `Exit Code: 137`입니다. 다음 설명 중 옳은 것은?

- A) 앱이 스스로 오류를 감지해 exit 1로 종료했다
- B) 메모리 limit을 초과해 커널이 SIGKILL로 컨테이너를 죽였으며, limit 상향 또는 메모리 누수 수정이 필요하다
- C) SIGTERM을 받아 정상 종료(graceful shutdown)된 것이므로 조치가 필요 없다
- D) 이미지의 아키텍처(arm64/amd64)가 노드와 맞지 않는다

<details>
<summary>정답 보기</summary>

**정답: B) 메모리 limit을 초과해 커널이 SIGKILL로 컨테이너를 죽였으며, limit 상향 또는 메모리 누수 수정이 필요하다**

**설명:**
exit code 137은 SIGKILL(128+9)입니다. Reason이 `OOMKilled`이면 메모리 limit 초과로 커널 OOM killer가 죽인 것이고, 같은 137이라도 Reason이 `Error`라면 liveness 실패 후 `terminationGracePeriodSeconds` 안에 종료되지 않아 강제 종료된 경우처럼 다른 이유의 SIGKILL입니다. SIGTERM 정상 종료는 143으로, 아키텍처 불일치는 셸 엔트리포인트라면 126(`cannot execute binary file: Exec format error`), 바이너리를 직접 실행하는 이미지라면 Reason `StartError`로 나타납니다. 죽기 직전 로그는 `kubectl logs <pod> -c <container> --previous`로 봅니다.

</details>

### 4. 파드가 모두 `1/1 Running`인데 Service로 요청이 가지 않습니다. `kubectl get endpointslices -l kubernetes.io/service-name=<svc>`의 ENDPOINTS 열이 비어 있습니다. 가장 가능성 높은 원인은?

- A) CoreDNS 파드가 죽어 이름 풀이가 안 된다
- B) Service의 `selector`가 파드 라벨과 일치하지 않는다
- C) `targetPort`가 컨테이너가 listen하는 포트와 다르다
- D) NetworkPolicy가 ingress를 차단한다

<details>
<summary>정답 보기</summary>

**정답: B) Service의 `selector`가 파드 라벨과 일치하지 않는다**

**설명:**
EndpointSlice는 Service 셀렉터에 매칭되는 **Ready 파드**의 IP 목록입니다. 파드가 모두 Ready인데도 비어 있다면 셀렉터와 파드 라벨이 다르다는 뜻입니다(Helm 차트에서 `selectorLabels`와 `podLabels`가 갈라진 경우가 흔함). `targetPort` 오류는 IP는 있는데 `connection refused`, NetworkPolicy 차단은 IP는 있는데 타임아웃, CoreDNS 장애는 `NXDOMAIN`/이름 풀이 실패로 나타납니다. Kubernetes 1.33+에서는 `kubectl get endpoints`가 deprecated 경고를 내므로 EndpointSlice로 확인합니다.

</details>

### 5. 노드 컨디션에 `DiskPressure=True (KubeletHasDiskPressure)`가 보입니다. 이때 노드 컨트롤러(kube-controller-manager)가 노드에 자동으로 추가하는 taint는?

- A) `node.kubernetes.io/unreachable`
- B) `node.kubernetes.io/not-ready`
- C) `node.kubernetes.io/disk-pressure`
- D) `node.kubernetes.io/memory-pressure`

<details>
<summary>정답 보기</summary>

**정답: C) `node.kubernetes.io/disk-pressure`**

**설명:**
노드 컨디션마다 대응하는 자동 taint가 있습니다. `DiskPressure` → `node.kubernetes.io/disk-pressure`, `MemoryPressure` → `node.kubernetes.io/memory-pressure`, `PIDPressure` → `node.kubernetes.io/pid-pressure`, `Ready=False` → `node.kubernetes.io/not-ready`, `Ready=Unknown`(kubelet이 상태 보고를 멈춤, reason `NodeStatusUnknown`) → `node.kubernetes.io/unreachable`. 그래서 노드는 `Ready`인데 새 파드가 `node(s) had untolerated taint(s)`로 그 노드를 피하는 증상이 생깁니다. DiskPressure의 흔한 원인은 이미지 캐시·컨테이너 로그가 루트 볼륨을 채운 것이며, 파드는 `The node was low on resource: ephemeral-storage`로 `Evicted`됩니다.

</details>

### 6. PVC가 `Pending`이고 `describe pvc` 이벤트에 `WaitForFirstConsumer: waiting for first consumer to be created before binding` 만 보입니다. 아직 이 PVC를 쓰는 파드는 배포하지 않았습니다. 올바른 판단은?

- A) StorageClass 이름 오타이므로 `kubectl get sc`로 이름을 확인해야 한다
- B) EBS CSI 컨트롤러의 IAM 권한이 부족하다
- C) 정상 동작이다 — `volumeBindingMode: WaitForFirstConsumer`는 파드가 스케줄될 때까지 볼륨을 만들지 않는다
- D) PV가 다른 AZ에 있어 `volume node affinity conflict`가 난 것이다

<details>
<summary>정답 보기</summary>

**정답: C) 정상 동작이다 — `volumeBindingMode: WaitForFirstConsumer`는 파드가 스케줄될 때까지 볼륨을 만들지 않는다**

**설명:**
EKS가 기본 제공하는 `gp2` StorageClass는 `WaitForFirstConsumer` 바인딩 모드를 씁니다. EBS CSI 드라이버용으로 직접 만드는 `gp3` StorageClass는 `volumeBindingMode: WaitForFirstConsumer`를 명시했을 때만 그렇게 동작합니다 — API 기본값은 `Immediate`입니다 — 검증 클러스터의 `gp3`는 플레이북의 `kubectl get storageclass` 출력처럼 명시되어 있습니다. 파드가 어느 AZ에 스케줄될지 정해진 뒤 그 AZ에 EBS 볼륨을 만들기 위한 의도된 지연이므로, 파드가 없는 동안 PVC가 `Pending`인 것은 문제가 아닙니다. StorageClass 오타는 `storageclass.storage.k8s.io "<name>" not found`, IAM 권한 부족은 `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied`, AZ 불일치는 파드 쪽 `FailedScheduling`에 `volume node affinity conflict`로 각각 다르게 나타납니다.

</details>

### 7. 파드 안에서 AWS API 호출이 `AccessDenied`인데, 거부된 주체가 서비스 계정 역할이 아니라 노드 IAM 역할입니다. `kubectl get sa`에는 `eks.amazonaws.com/role-arn` 어노테이션이 있지만, 파드 env에 `AWS_ROLE_ARN`/`AWS_WEB_IDENTITY_TOKEN_FILE`이 없습니다. 원인과 조치는?

- A) IAM 역할의 권한 정책이 부족하다 → 정책에 액션 추가
- B) 어노테이션이 파드 생성 **이후**에 붙어 webhook이 자격 증명을 주입하지 못했다 → `kubectl rollout restart`
- C) OIDC provider가 없다 → 클러스터 재생성
- D) EKS Pod Identity 에이전트가 죽었다 → 에이전트 재시작

<details>
<summary>정답 보기</summary>

**정답: B) 어노테이션이 파드 생성 이후에 붙어 webhook이 자격 증명을 주입하지 못했다 → `kubectl rollout restart`**

**설명:**
IRSA는 pod-identity-webhook이 **파드 생성 시점**에 `AWS_ROLE_ARN`과 `AWS_WEB_IDENTITY_TOKEN_FILE` env(및 토큰 볼륨)를 주입하는 방식입니다. 주입 흔적이 전혀 없으면 파드가 어노테이션보다 먼저 만들어졌거나 SA 이름이 다른 경우이며, SDK는 자격 증명을 찾지 못해 노드 역할로 폴백합니다. 파드를 다시 만들면 해결됩니다. 권한 정책 부족(A)은 env는 정상인데 특정 API만 거부되는 패턴이고, Pod Identity(D)는 `AWS_CONTAINER_CREDENTIALS_FULL_URI` env로 구분됩니다.

</details>

### 8. 파드가 `Pending`인데 새 NodeClaim이 생기지 않고, Karpenter 이벤트에 `all available instance types exceed limits for nodepool "graviton"` 이 있습니다. 원인은?

- A) 파드의 nodeSelector 라벨 키가 NodePool requirements에 없다
- B) NodePool의 taint에 대한 toleration이 없다
- C) NodePool `spec.limits`(cpu/memory)에 이미 도달했다
- D) 해당 AZ에 EC2 용량이 없다(`InsufficientInstanceCapacity`)

<details>
<summary>정답 보기</summary>

**정답: C) NodePool `spec.limits`(cpu/memory)에 이미 도달했다**

**설명:**
Karpenter는 파드 하나에 대해 모든 NodePool을 순회하며 탈락 이유를 이벤트로 남깁니다. `exceed limits`는 어떤 인스턴스를 추가해도 NodePool의 `spec.limits`를 넘게 된다는 뜻이며, `kubectl get nodepool -o custom-columns=...spec.limits.cpu,...status.resources.cpu`로 보면 limit과 사용량이 같습니다. 라벨 키 누락은 `label "<key>" does not have known values`, toleration 누락은 `did not tolerate <key>=<value>:NoSchedule`, EC2 용량 부족은 Karpenter 컨트롤러 로그의 `InsufficientInstanceCapacity`로 각각 나타납니다.

</details>

### 9. EKS 노드의 파드들이 `ContainerCreating`에서 멈추고 이벤트에 `FailedCreatePodSandBox ... plugin type="aws-cni" ... failed to assign an IP address to container` 가 찍힙니다. 서브넷의 `AvailableIpAddressCount`는 한 자릿수이고, `aws-node`는 VPC CNI 기본값(`WARM_ENI_TARGET=1`, `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` 미설정)으로 돌고 있습니다. 옳은 설명은?

- A) 기본값 `WARM_ENI_TARGET=1`은 노드마다 여분 ENI 한 장 분량의 IP를 통째로 미리 붙여 두므로, 파드 수보다 훨씬 일찍 서브넷이 고갈된다. `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`을 설정하면 warm-ENI 규칙보다 우선 적용되어 그 여유 풀이 줄어든다
- B) `WARM_ENI_TARGET`이 설정되어 있는 동안에는 `WARM_IP_TARGET`이 무시되므로, `WARM_ENI_TARGET=0`만 넣으면 충분하다
- C) `ENABLE_PREFIX_DELEGATION=true`는 ENI를 더 붙여서 IP를 늘리므로 어떤 인스턴스 패밀리에서도 동작한다
- D) `FailedCreatePodSandBox`는 스케줄러가 노드를 못 찾았다는 뜻이므로 `Too many pods`와 같은 실패다

<details>
<summary>정답 보기</summary>

**정답: A) 기본값 `WARM_ENI_TARGET=1`은 노드마다 여분 ENI 한 장 분량의 IP를 통째로 미리 붙여 두므로, 파드 수보다 훨씬 일찍 서브넷이 고갈된다. `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`을 설정하면 warm-ENI 규칙보다 우선 적용되어 그 여유 풀이 줄어든다**

**설명:**
기본값 `WARM_ENI_TARGET=1`만 있으면 ipamd는 노드마다 여분 ENI 한 장을 통째로 붙여 둡니다(m5.xlarge는 ENI당 IP 15개). 작은 서브넷에서는 파드보다 이렇게 선점된 IP가 먼저 바닥납니다. `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`을 설정하면 warm-ENI 규칙을 덮어쓰는데, 플레이북의 검증 클러스터는 `WARM_IP_TARGET=3`, `MINIMUM_IP_TARGET=6`으로, 노드는 파드가 쓰는 것 외에 여분 IP를 3개만 쥐고 전체 할당 IP는 6개 아래로 내려가지 않습니다(`MINIMUM_IP_TARGET`은 사용 중 + 여분을 합친 전체 개수의 하한이며, 여분 개수의 하한이 아닙니다). B는 우선순위가 거꾸로입니다. 프리픽스 위임(C)은 ENI를 추가하는 것이 아니라 기존 ENI 슬롯에 /28 프리픽스를 할당하는 방식이고, Nitro 기반 인스턴스와 max-pods 재계산이 필요합니다. D는 두 증상을 혼동한 것입니다. `FailedCreatePodSandBox`는 스케줄링이 끝난 뒤 kubelet이 CNI에 IP를 요청했는데 노드에 남은 IP가 없을 때 발생하고, `Too many pods`는 `allocatable.pods`에 이미 도달해 스케줄러가 노드를 탈락시키는 것입니다. 근본 원인(내줄 IP가 없음)은 같지만 발생 단계가 다릅니다.

</details>
