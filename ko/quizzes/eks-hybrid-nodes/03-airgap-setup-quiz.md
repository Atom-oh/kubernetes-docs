# EKS Hybrid Nodes 에어갭 환경 구성 퀴즈

> **관련 문서**: [에어갭 환경 구성](../../eks-hybrid-nodes/03-airgap-setup.md)

## 객관식 문제

### 1. Harbor에서 이미지 복제(Replication)를 위한 정책 유형으로 올바르지 않은 것은?

A. Push-based
B. Pull-based
C. Event-based
D. Sync-based

<details>
<summary>정답 보기</summary>

**정답: D. Sync-based**

**설명:**
Harbor는 Push-based, Pull-based, Event-based 복제 정책을 지원합니다. "Sync-based"는 Harbor의 공식 용어가 아닙니다.

**Harbor 복제 정책 유형:**
1. **Push-based**: 소스 Harbor에서 타겟 레지스트리로 푸시
2. **Pull-based**: 타겟 Harbor가 소스에서 이미지를 가져옴
3. **Event-based**: 이미지 푸시 이벤트 발생 시 자동 복제

```yaml
# Harbor 복제 정책 API 예시
POST /api/v2.0/replication/policies
{
  "name": "ecr-replication",
  "trigger": {
    "type": "event_based"
  },
  "filters": [
    {"type": "name", "value": "myapp/**"},
    {"type": "tag", "value": "v*"}
  ]
}
```

</details>

### 2. Harbor 프라이빗 레지스트리를 Kubernetes와 연동할 때 사용하는 Secret 유형은?

A. Opaque
B. kubernetes.io/dockerconfigjson
C. kubernetes.io/tls
D. kubernetes.io/service-account-token

<details>
<summary>정답 보기</summary>

**정답: B. kubernetes.io/dockerconfigjson**

**설명:**
Docker/Container 레지스트리 인증 정보는 `kubernetes.io/dockerconfigjson` 타입의 Secret으로 저장합니다.

```bash
# Harbor 레지스트리 Secret 생성
kubectl create secret docker-registry harbor-secret \
  --docker-server=harbor.example.com \
  --docker-username=admin \
  --docker-password=Harbor12345 \
  --docker-email=admin@example.com
```

```yaml
# Pod에서 imagePullSecrets 사용
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: harbor.example.com/project/my-app:v1
  imagePullSecrets:
  - name: harbor-secret
```

</details>

### 3. Harbor에서 이미지 취약점 스캔을 위해 기본으로 제공되는 스캐너는 무엇인가요?

A. Clair
B. Trivy
C. Anchore
D. Snyk

<details>
<summary>정답 보기</summary>

**정답: B. Trivy**

**설명:**
Harbor 2.0부터 Trivy가 기본 취약점 스캐너로 포함되어 있습니다. Clair도 선택적으로 사용할 수 있습니다.

```bash
# Harbor 취약점 스캔 API
POST /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/scan

# 스캔 결과 조회
GET /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/additions/vulnerabilities
```

**Harbor 스캔 정책 설정:**
- Projects > Configuration > Vulnerability scanning
- Automatically scan images on push: enabled
- Prevent vulnerable images from running: enabled (CVE severity threshold)

</details>

### 4. 에어갭(Air-gap) 환경의 정의로 가장 적절한 것은?

A. 인터넷 연결이 느린 환경
B. 외부 네트워크와 물리적으로 완전히 격리된 환경
C. VPN으로만 연결된 환경
D. 방화벽이 설치된 환경

<details>
<summary>정답 보기</summary>

**정답: B. 외부 네트워크와 물리적으로 완전히 격리된 환경**

**설명:**
에어갭(Air-gap) 환경은 보안상의 이유로 인터넷이나 외부 네트워크와 물리적으로 완전히 분리된 환경입니다. 주로 다음과 같은 곳에서 사용됩니다:

- 군사/국방 시설
- 금융 기관의 핵심 시스템
- 원자력 발전소 제어 시스템
- 의료 기관의 민감 데이터 처리 시스템

```
에어갭 환경 특성:
+------------------+     물리적 격리     +------------------+
|   외부 네트워크   | <---- 연결 없음 ---> |   에어갭 환경     |
| (인터넷, 클라우드)|                     | (온프레미스 DC)   |
+------------------+                     +------------------+
```

에어갭 환경에서는 모든 소프트웨어와 이미지를 오프라인으로 전송해야 합니다.

</details>

### 5. 에어갭 환경에서 컨테이너 이미지를 Harbor로 미러링하는 올바른 순서는?

A. Harbor 설치 → 이미지 태그 → 이미지 푸시 → 이미지 풀
B. 이미지 풀 → 이미지 저장 → 오프라인 전송 → Harbor에 로드 및 푸시
C. Harbor 설치 → 직접 ECR 연결 → 자동 동기화
D. 이미지 빌드 → 직접 배포 → Harbor 건너뛰기

<details>
<summary>정답 보기</summary>

**정답: B. 이미지 풀 → 이미지 저장 → 오프라인 전송 → Harbor에 로드 및 푸시**

**설명:**
에어갭 환경에서는 인터넷 연결이 없으므로 이미지를 수동으로 전송해야 합니다:

```bash
# 1. 인터넷이 연결된 시스템에서 이미지 풀
docker pull nginx:1.25

# 2. 이미지를 tar 파일로 저장
docker save nginx:1.25 -o nginx-1.25.tar

# 3. 오프라인 전송 (USB, 외장 하드 등)
# 물리적 매체로 에어갭 환경으로 이동

# 4. 에어갭 환경에서 이미지 로드
docker load -i nginx-1.25.tar

# 5. Harbor에 태그 및 푸시
docker tag nginx:1.25 harbor.airgap.local/library/nginx:1.25
docker push harbor.airgap.local/library/nginx:1.25
```

대량의 이미지를 관리할 때는 `skopeo`나 `crane` 같은 도구를 사용하면 더 효율적입니다.

</details>

### 6. nodeadm을 에어갭 환경에서 오프라인으로 설치하는 방법으로 올바른 것은?

A. curl로 GitHub에서 직접 다운로드
B. apt-get install nodeadm
C. 바이너리와 의존성을 미리 다운로드하여 오프라인으로 설치
D. pip install nodeadm

<details>
<summary>정답 보기</summary>

**정답: C. 바이너리와 의존성을 미리 다운로드하여 오프라인으로 설치**

**설명:**
에어갭 환경에서는 인터넷 접근이 불가능하므로 모든 필요한 파일을 미리 준비해야 합니다:

```bash
# 인터넷 연결된 시스템에서 준비
# 1. nodeadm 바이너리 다운로드
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64

# 2. 필요한 의존성 패키지 다운로드 (예: Ubuntu)
apt-get download containerd.io kubelet kubectl

# 3. 모든 파일을 에어갭 환경으로 전송

# 에어갭 환경에서 설치
# 4. nodeadm 설치
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# 5. 의존성 패키지 설치
sudo dpkg -i containerd.io_*.deb kubelet_*.deb kubectl_*.deb

# 6. nodeadm 실행
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

</details>

### 7. 에어갭 환경에서 프록시 서버를 구성할 때 설정해야 하는 환경 변수가 아닌 것은?

A. HTTP_PROXY
B. HTTPS_PROXY
C. NO_PROXY
D. FTP_PROXY

<details>
<summary>정답 보기</summary>

**정답: D. FTP_PROXY**

**설명:**
컨테이너 및 Kubernetes 환경에서 주로 사용되는 프록시 환경 변수는 HTTP_PROXY, HTTPS_PROXY, NO_PROXY입니다. FTP_PROXY는 거의 사용되지 않습니다.

```bash
# 프록시 환경 변수 설정
export HTTP_PROXY=http://proxy.company.local:8080
export HTTPS_PROXY=http://proxy.company.local:8080
export NO_PROXY=localhost,127.0.0.1,.cluster.local,10.0.0.0/8

# containerd 프록시 설정
sudo mkdir -p /etc/systemd/system/containerd.service.d
cat <<EOF | sudo tee /etc/systemd/system/containerd.service.d/proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.company.local:8080"
Environment="HTTPS_PROXY=http://proxy.company.local:8080"
Environment="NO_PROXY=localhost,127.0.0.1,.cluster.local"
EOF

sudo systemctl daemon-reload
sudo systemctl restart containerd
```

**NO_PROXY에 포함해야 할 주소:**
- 클러스터 내부 서비스 (*.cluster.local)
- Pod/Service CIDR
- 노드 IP 대역
- Harbor 레지스트리 주소

</details>

### 8. 에어갭 환경의 준비 상태를 검증하기 위한 체크리스트로 올바르지 않은 것은?

A. Harbor 레지스트리 접근 가능 여부
B. 필요한 컨테이너 이미지 존재 여부
C. 인터넷 연결 속도 테스트
D. DNS 해결 가능 여부

<details>
<summary>정답 보기</summary>

**정답: C. 인터넷 연결 속도 테스트**

**설명:**
에어갭 환경은 정의상 인터넷 연결이 없으므로, 인터넷 속도 테스트는 의미가 없습니다. 에어갭 준비 상태 검증 체크리스트:

```bash
# 1. Harbor 레지스트리 접근 확인
curl -k https://harbor.airgap.local/api/v2.0/health

# 2. 필요한 이미지 존재 확인
docker pull harbor.airgap.local/library/pause:3.9

# 3. DNS 해결 확인
nslookup harbor.airgap.local

# 4. nodeadm 바이너리 확인
nodeadm version

# 5. 의존성 패키지 확인
dpkg -l | grep -E "containerd|kubelet"

# 6. TLS 인증서 확인
openssl s_client -connect harbor.airgap.local:443 -showcerts
```

**검증 스크립트 예시:**
```bash
#!/bin/bash
echo "=== 에어갭 환경 검증 ==="

# Harbor 연결
if curl -sk https://harbor.airgap.local/api/v2.0/health | grep -q "healthy"; then
  echo "[OK] Harbor 정상"
else
  echo "[FAIL] Harbor 연결 실패"
fi

# 필수 이미지 확인
REQUIRED_IMAGES="pause:3.9 coredns:v1.10.1"
for img in $REQUIRED_IMAGES; do
  if docker manifest inspect harbor.airgap.local/library/$img > /dev/null 2>&1; then
    echo "[OK] $img 존재"
  else
    echo "[FAIL] $img 없음"
  fi
done
```

</details>

### 9. 에어갭 환경에서 EKS Hybrid Nodes를 운영할 때 컨테이너 이미지 업데이트를 위한 권장 방법은?

A. 노드에서 직접 docker pull 실행
B. 주기적인 이미지 미러링 및 오프라인 전송 프로세스 수립
C. 이미지 업데이트 없이 고정 버전만 사용
D. 임시로 인터넷 연결 허용

<details>
<summary>정답 보기</summary>

**정답: B. 주기적인 이미지 미러링 및 오프라인 전송 프로세스 수립**

**설명:**
에어갭 환경에서는 체계적인 이미지 관리 프로세스가 필요합니다:

```
이미지 업데이트 워크플로우:

[인터넷 연결 환경]          [에어갭 환경]
+-----------------+         +-----------------+
| 1. 이미지 목록  |         | 4. 이미지 로드  |
|    확인/다운로드 |         |                 |
| 2. 취약점 스캔  | ------> | 5. Harbor 푸시  |
| 3. tar 패키징   | 오프라인 | 6. 배포 업데이트|
+-----------------+  전송    +-----------------+
```

```bash
# 이미지 목록 관리 (images.txt)
public.ecr.aws/eks-distro/kubernetes/pause:3.9
public.ecr.aws/eks-distro/coredns/coredns:v1.10.1
docker.io/library/nginx:1.25

# 일괄 다운로드 스크립트
#!/bin/bash
while read -r image; do
  echo "Pulling $image..."
  docker pull "$image"
  name=$(echo "$image" | tr '/:' '_')
  docker save "$image" -o "${name}.tar"
done < images.txt

# 일괄 업로드 스크립트 (에어갭 환경)
#!/bin/bash
for tarfile in *.tar; do
  docker load -i "$tarfile"
  # Harbor로 재태그 및 푸시
done
```

**권장 사항:**
- 월간 또는 분기별 이미지 업데이트 주기 설정
- 보안 취약점 패치 시 긴급 업데이트 절차 마련
- 이미지 서명 및 무결성 검증

</details>

### 10. Harbor에서 이미지를 미러링할 때 대역폭을 최적화하기 위한 방법으로 올바른 것은?

A. 매번 전체 이미지를 다시 전송
B. 레이어 기반 증분 전송 및 압축 사용
C. 이미지 크기와 관계없이 동일하게 처리
D. 미러링 대신 매번 새로 빌드

<details>
<summary>정답 보기</summary>

**정답: B. 레이어 기반 증분 전송 및 압축 사용**

**설명:**
컨테이너 이미지는 레이어로 구성되어 있으며, 변경된 레이어만 전송하면 대역폭을 크게 절약할 수 있습니다:

```bash
# skopeo를 사용한 효율적인 이미지 복사
skopeo copy \
  --src-tls-verify=false \
  docker://source-registry.com/myapp:v1 \
  docker://harbor.airgap.local/myapp:v1

# crane을 사용한 레이어 기반 복사
crane copy source-registry.com/myapp:v1 harbor.airgap.local/myapp:v1
```

**최적화 전략:**

| 방법 | 설명 | 절감 효과 |
|-----|-----|---------|
| 레이어 캐싱 | 변경된 레이어만 전송 | 50-80% |
| 압축 | gzip/zstd 압축 적용 | 30-50% |
| 멀티 아키텍처 | 필요한 아키텍처만 미러링 | 50% |
| 태그 필터링 | 필요한 태그만 미러링 | 가변적 |

```yaml
# Harbor 복제 정책에서 필터링
{
  "filters": [
    {"type": "tag", "value": "v*"},
    {"type": "label", "value": "production=true"}
  ]
}
```

</details>

