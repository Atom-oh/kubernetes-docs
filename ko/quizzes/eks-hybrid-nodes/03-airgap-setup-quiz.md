# EKS Hybrid Nodes 인터넷 제한 환경 구성 퀴즈

> **관련 문서**: [인터넷 제한 환경 구성](../../eks-hybrid-nodes/03-airgap-setup.md)
> **마지막 업데이트**: 2026년 9월 12일

### 1. EKS Hybrid Nodes 연결 요구 사항으로 올바른 것은?

A. 이미지를 물리적으로 전달하면 AWS 연결이 필요 없다

B. 노드는 EKS 컨트롤 플레인과 자격 증명 서비스 연결이 계속 필요하다

C. 프라이빗 S3 버킷이 EKS 컨트롤 플레인을 호스팅한다

D. VPN 연결은 물리적 격리와 같다

<details>
<summary>정답 보기</summary>

**정답: B. 노드는 EKS 컨트롤 플레인과 자격 증명 서비스 연결이 계속 필요하다**

**설명:** 퍼블릭 인터넷을 제한하면서 AWS에 프라이빗으로 연결할 수 있습니다. 물리적으로 단절된 네트워크는 Hybrid Nodes에 필요한 실시간 컨트롤 플레인·자격 증명 서비스 경로를 제공할 수 없습니다.

</details>

### 2. hybrid-assets.eks.amazonaws.com을 S3로 연결하는 PHZ 별칭만으로 부족한 이유는?

A. S3는 프라이빗 DNS를 전혀 지원하지 않는다

B. DNS보다 ECR을 먼저 설치해야 한다

C. DNS가 원래 TLS 호스트명, 객체 라우팅, 권한을 제공하지 않는다

D. 모든 HTTPS 요청이 자동으로 IAM 역할을 사용한다

<details>
<summary>정답 보기</summary>

**정답: C. DNS가 원래 TLS 호스트명, 객체 라우팅, 권한을 제공하지 않는다**

**설명:** S3 interface 엔드포인트는 프라이빗 DNS를 지원합니다. 그러나 별칭은 TLS SNI, HTTP Host 헤더, 객체 경로나 인증을 재작성하지 않습니다. 승인한 이미지 준비 또는 실제 사용자 지정 manifest URL을 사용하고 인증서 검증을 끄지 않습니다.

</details>

### 3. nodeadm v1.0.20의 private 설치 모드는 무엇을 하는가?

A. 모든 OS 의존성을 로컬 manifest에서 설치한다

B. OS 패키지 설치를 건너뛰지만 자격 증명·EKS 아티팩트는 설치한다

C. 모든 AWS API 호출을 선택 사항으로 만든다

D. 모든 S3 아티팩트 다운로드에 자동 서명한다

<details>
<summary>정답 보기</summary>

**정답: B. OS 패키지 설치를 건너뛰지만 자격 증명·EKS 아티팩트는 설치한다**

**설명:** 릴리스 소스는 --private-mode 사용 시 --manifest-override를 요구합니다. 런타임과 OS 의존성은 별도 준비합니다. SSM 설치 프로그램·서명 소스는 따로 구성되며 file:// manifest 지원이 file:// 아티팩트 지원을 뜻하지 않습니다.

</details>

### 4. 체크섬이 없거나 일치하지 않을 때 아티팩트 준비 스크립트는 어떻게 해야 하는가?

A. 경고 후 나머지 파일을 게시한다

B. 파일 하나라도 통과하면 전체 실행을 수용한다

C. 받은 파일로 새 예상 체크섬을 만든다

D. 중단하고 실패한 후보를 조사용으로 보존한다

<details>
<summary>정답 보기</summary>

**정답: D. 중단하고 실패한 후보를 조사용으로 보존한다**

**설명:** 모든 필수 파일이 신뢰하고 검토한 체크섬 기록과 일치해야 합니다. 예상값을 새로 생성하면 이 검사가 무의미해집니다. 해시 일치 자체가 독립적인 게시자 인증은 아닙니다.

</details>

### 5. IAM Roles Anywhere update 서비스의 올바른 적용 범위는?

A. SSM을 포함한 모든 설치에 존재한다

B. enableCredentialsFile을 켰을 때 사용하며 일반 credential-process는 별도 경로다

C. 실제로 존재하지 않으므로 항상 제거해야 한다

D. 인증서 갱신 필요성을 없앤다

<details>
<summary>정답 보기</summary>

**정답: B. enableCredentialsFile을 켰을 때 사용하며 일반 credential-process는 별도 경로다**

**설명:** aws_signing_helper_update.service는 credentials-file 모드에 실제로 존재합니다. nodeadm의 프록시 감지·--with-proxy 동작을 포함하여 해당 서비스와 호출 프로세스 환경을 구성합니다. 인증서 수명 주기와 AWS 연결 요구 사항은 유지됩니다.

</details>

### 6. Hybrid Nodes 전달 목록에는 어떤 이미지를 포함해야 하는가?

A. 모든 노드에 동일한 고정 VPC CNI 이미지 목록

B. CNI 이미지인 kubelet만

C. 실제 지원 CNI·DNS·데이터 경로·샌드박스·워크로드 이미지와 init container·플랫폼

D. Kubernetes 패치에 -eksbuild.1을 붙여 만든 임의 태그

<details>
<summary>정답 보기</summary>

**정답: C. 실제 지원 CNI·DNS·데이터 경로·샌드박스·워크로드 이미지와 init container·플랫폼**

**설명:** VPC CNI는 Hybrid Nodes용 CNI가 아닙니다. 실제 배포 manifest와 승인한 다이제스트를 사용합니다. 프라이빗 ECR 풀에는 S3 레이어 경로와 워크로드 이미지 풀 자격 증명도 필요하므로 저장소 목록 조회만으로 충분하지 않습니다.

</details>

### 7. 부트스트랩 전 nodeadm 설정을 확인하는 유효한 방법은?

A. nodeadm init --dry-run

B. nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml

C. curl -k 실행 후 준비 완료 보고

D. 설정 파일이 없으면 건너뛰고 성공 반환

<details>
<summary>정답 보기</summary>

**정답: B. nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml**

**설명:** 실제 값을 채우고 보호한 설정 파일을 사용합니다. config check는 설정을 검증하며 프라이빗 네트워크 동작을 증명하거나 노드를 등록하지 않습니다. 확인한 init 명령에는 --dry-run이 없습니다.

</details>

### 8. 기존 kube-proxy DaemonSet을 보존하는 프록시 변경은?

A. /containers/0/env를 새 JSON Patch 배열로 교체

B. 프록시에 필요 없다는 이유로 NODE_NAME 삭제

C. 컨테이너·환경 변수 이름으로 검토한 strategic merge를 적용하고 기존 인자·NODE_NAME 유지

D. .eks.amazonaws.com을 항상 프록시 우회에 포함

<details>
<summary>정답 보기</summary>

**정답: C. 컨테이너·환경 변수 이름으로 검토한 strategic merge를 적용하고 기존 인자·NODE_NAME 유지**

**설명:** 기존 env 항목을 대상으로 하는 JSON Patch add는 전체 배열을 교체할 수 있습니다. kube-proxy에 범위를 한정하고 다른 값을 보존합니다. 광범위한 .eks.amazonaws.com 우회는 퍼블릭 hybrid-assets 다운로드 호스트에도 적용됩니다.

</details>

### 9. 전달받은 OCI 이미지 아카이브를 사용하기 전에 필요한 것은?

A. tar 가져오기 성공만 확인

B. 승인 해시, 다이제스트·플랫폼 콘텐츠, 대상 이미지 참조와 실제 런타임 풀 동작 확인

C. 인증서 오류를 피하려고 소스 레지스트리 TLS 비활성화

D. 빌더 아키텍처만 필요하다고 가정

<details>
<summary>정답 보기</summary>

**정답: B. 승인 해시, 다이제스트·플랫폼 콘텐츠, 대상 이미지 참조와 실제 런타임 풀 동작 확인**

**설명:** Skopeo --all은 플랫폼 목록을 보존하고 --preserve-digests는 다이제스트를 유지할 수 없으면 실패합니다. 가져온 이름, containerd k8s.io 네임스페이스, imagePullPolicy와 가비지 컬렉션도 실제 Pod 시작에 영향을 줍니다.

</details>

### 10. 프라이빗 아티팩트 저장소의 적절한 업데이트 방식은?

A. 매주 운영 latest 키 자동 덮어쓰기

B. head-object의 AccessDenied를 객체 부재로 취급

C. 출처·호환성·대표 노드 검증 후 새 불변 후보 승인

D. 모든 환경에 대역폭 50–80% 절감 보장

<details>
<summary>정답 보기</summary>

**정답: C. 출처·호환성·대표 노드 검증 후 새 불변 후보 승인**

**설명:** 소유 버킷, 명시적인 예상 소유자, 분리된 게시·읽기 권한을 사용하고 알 수 없는 오류에서 중단합니다. 조건부 객체 쓰기는 전체 업로드를 원자적으로 만들지 않습니다. 이전 대역폭 비율은 미검증 역사적 예시이며 보장된 실측값이 아닙니다.

</details>

