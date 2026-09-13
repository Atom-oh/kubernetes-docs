# WorkloadEntry

> **검토 버전**: Istio 1.31.0
> **마지막 업데이트**: 2026년 9월 11일

WorkloadEntry는 Virtual Machine (VM)이나 베어메탈 서버를 Istio 서비스 메시에 등록하기 위한 리소스입니다. 이를 통해 Kubernetes 외부의 워크로드도 메시의 트래픽 관리, 보안, 관찰성 기능을 활용할 수 있습니다.

## 목차

1. [개요](#개요)
2. [WorkloadEntry vs Kubernetes Pod](#workloadentry-vs-kubernetes-pod)
3. [아키텍처](#아키텍처)
4. [기본 사용법](#기본-사용법)
5. [ServiceEntry 통합](#serviceentry-통합)
6. [VM 등록 실전 가이드](#vm-등록-실전-가이드)
7. [보안 설정 (mTLS)](#보안-설정-mtls)
8. [헬스체크 및 모니터링](#헬스체크-및-모니터링)
9. [고급 구성](#고급-구성)
10. [문제 해결](#문제-해결)
11. [모범 사례](#모범-사례)

## 개요

WorkloadEntry는 워크로드를 기술합니다. 생성만으로 Envoy 설치, ID 초기화, 네트워크 연결, DNS 레코드가 만들어지지는 않습니다. 이 장은 Sidecar 모드 VM 통합을 사용합니다. 각 예제는 독립적이며 ServiceEntry, 선택할 WorkloadEntry, ServiceAccount의 네임스페이스를 맞추세요. 그림은 등록/구성 관계이며 추가 네트워크 홉이 아닙니다.

### WorkloadEntry란?

WorkloadEntry는 Istio Custom Resource Definition (CRD)으로, 메시 외부에 있는 워크로드(VM, 베어메탈)를 Istio 서비스 메시에 등록합니다.

### 사용 시나리오

![레거시 VM과 베어메탈 서버가 WorkloadEntry로 istiod에 등록되고, istiod가 Kubernetes 파드의 Envoy 사이드카에 구성을 전달하여 VM과 파드 워크로드가 mTLS로 통신하는 하이브리드 아키텍처를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-13-workload-entry-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-13-workload-entry-0.html)

**주요 사용 사례**:
1. **점진적 마이그레이션**: 레거시 애플리케이션을 단계적으로 Kubernetes로 이전
2. **하이브리드 아키텍처**: VM과 컨테이너를 동시에 운영
3. **데이터베이스 통합**: 외부 데이터베이스를 메시에 포함
4. **고성능 워크로드**: GPU 서버 등 특수 하드웨어 활용

## WorkloadEntry vs Kubernetes Pod

### 비교표

| 특성 | Kubernetes Pod | WorkloadEntry (VM) |
|------|---------------|--------------------|
| **배포 위치** | 클러스터 내부 | 클러스터 외부 |
| **Envoy 주입** | 자동 (사이드카) | 수동 설치 |
| **서비스 디스커버리** | 자동 (Service) | 수동 (WorkloadEntry) |
| **IP 관리** | Kubernetes CNI | 수동 지정 |
| **mTLS** | 자동 | 자동 (인증서 배포 필요) |
| **헬스체크** | 자동 (Liveness/Readiness) | 수동 구성 |
| **스케일링** | HPA | 수동 |
| **운영 복잡도** | 낮음 | 높음 |
| **사용 시나리오** | 클라우드 네이티브 앱 | 레거시 앱, 특수 하드웨어 |

### 트래픽 흐름 비교

![클라이언트 요청이 Kubernetes 파드 경로에서는 Service의 자동 디스커버리로 Pod에 도달하고, WorkloadEntry 경로에서는 수동 등록한 ServiceEntry를 거쳐 VM의 WorkloadEntry에 도달하는 두 흐름을 나란히 비교해 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-13-workload-entry-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-13-workload-entry-1.html)

## 아키텍처

### VM 워크로드 아키텍처

![VM에 수동 설치된 Envoy와 파드에 자동 주입된 Envoy가 mTLS로 통신하고, istiod가 양쪽에 xDS 구성을 배포하며 VM 측에는 인증서까지 별도로 발급하는 아키텍처를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-13-workload-entry-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-13-workload-entry-2.html)

### 주요 구성 요소

1. **WorkloadEntry**: VM 정보 등록 (IP, 포트, 레이블)
2. **ServiceEntry**: 서비스 정의 및 WorkloadEntry 참조
3. **Envoy Proxy**: VM에 수동 설치된 사이드카
4. **istiod**: 구성 배포 및 인증서 관리
5. **Service Account**: VM의 신원 인증

## 기본 사용법

### WorkloadEntry 리소스 정의

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm-1
  namespace: production
spec:
  # VM의 IP 주소
  address: 192.168.1.100

  # 서비스 선택을 위한 레이블
  labels:
    app: legacy-api
    version: v1.0
    tier: backend

  # mTLS 인증을 위한 서비스 계정
  serviceAccount: legacy-api-sa

  # 노출할 포트
  ports:
    http: 8080
    https: 8443
    metrics: 9090

  # 로컬리티 정보 (선택적)
  locality: us-west-2/us-west-2a

  # 가중치 (로드 밸런싱용, 선택적)
  weight: 100

  # 네트워크 (멀티 네트워크 환경, 선택적)
  network: vm-network
```

### 필수 필드 설명

| 필드 | 설명 | 예시 |
|------|------|------|
| **address** | 엔드포인트 주소 (IP 또는 DNS resolution의 DNS명; 구성된 원격 network는 생략 가능) | `192.168.1.100` |
| **labels** | ServiceEntry 매칭용 레이블 | `app: legacy-api` |
| **serviceAccount** | mTLS 인증용 SA | `legacy-api-sa` |
| **ports** | 노출할 포트 맵 | `http: 8080` |

### 여러 VM 등록

```yaml
# VM 1
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-1
  namespace: production
spec:
  address: 192.168.1.101
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
  ports:
    http: 8080
---
# VM 2
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-2
  namespace: production
spec:
  address: 192.168.1.102
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
  ports:
    http: 8080
---
# VM 3 (다른 버전)
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-3
  namespace: production
spec:
  address: 192.168.1.103
  labels:
    app: api-service
    version: v2  # 새 버전
  serviceAccount: api-sa
  ports:
    http: 8080
```

## ServiceEntry 통합

WorkloadEntry는 항상 ServiceEntry와 함께 사용됩니다.

### 기본 통합 패턴

```yaml
# 1. ServiceEntry로 서비스 정의
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-api
  namespace: production
spec:
  hosts:
  - api.legacy.internal
  addresses:
  - 240.240.1.1  # 가상 IP
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: legacy-api  # WorkloadEntry의 레이블과 매칭
---
# 2. WorkloadEntry로 VM 등록
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm-1
  namespace: production
spec:
  address: 192.168.1.100
  labels:
    app: legacy-api  # ServiceEntry와 매칭
    version: v1
  serviceAccount: legacy-api-sa
  ports:
    http: 8080
```

### 동작 흐름

![Kubernetes 파드가 Istio DNS로 가상 IP를 조회한 뒤 Envoy가 ServiceEntry의 workloadSelector로 WorkloadEntry를 찾아 VM으로 mTLS 연결을 맺고 응답을 돌려주는 순서를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-13-workload-entry-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-13-workload-entry-3.html)

### 로드 밸런싱

여러 WorkloadEntry가 있을 때 자동 로드 밸런싱됩니다:

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: database-cluster
  namespace: vm-workloads
spec:
  hosts:
  - db.cluster.internal
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
      tier: database
      role: primary
---
# Separate read-only replica service
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: database-replicas
  namespace: vm-workloads
spec:
  hosts:
  - db-replicas.cluster.internal
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
      tier: database
      role: replica
---
# Primary DB
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-primary
  namespace: vm-workloads
spec:
  serviceAccount: vm-postgres-sa
  address: 10.0.1.100
  labels:
    app: postgres
    tier: database
    role: primary
  weight: 100  # 가중치
---
# Replica DB 1
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-replica-1
  namespace: vm-workloads
spec:
  serviceAccount: vm-postgres-sa
  address: 10.0.1.101
  labels:
    app: postgres
    tier: database
    role: replica
  weight: 50
---
# Replica DB 2
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-replica-2
  namespace: vm-workloads
spec:
  serviceAccount: vm-postgres-sa
  address: 10.0.1.102
  labels:
    app: postgres
    tier: database
    role: replica
  weight: 50
```

쓰기는 primary 서비스로 보내고 복제 의미를 허용하는 읽기만 replica 서비스로 보내세요. 일반 엔드포인트 가중치는 PostgreSQL 역할을 이해하지 않습니다. 같은 포트의 서비스에는 DNS 캡처/고유 VIP를 준비하고 각 VM을 해당 ServiceAccount로 초기화하세요.

## VM 등록 실전 가이드

### 사전 요구사항

1. **VM 요구사항**:
   - 네트워크: Kubernetes 클러스터와 통신 가능
   - OS/CPU: 선택한 sidecar 패키지가 지원하는 Linux 배포판/아키텍처; 아래는 Debian 패키지 예제
   - 연결: 노출한 VM 게이트웨이를 통해 istiod xDS/CA(일반적으로 15012)에 접근하고 선택한 토폴로지로 워크로드 트래픽을 라우팅. 15017은 Kubernetes webhook 포트이며 VM 앱 요구사항이 아님.

2. **Kubernetes 준비**:
   - Istio 설치 완료
   - VM이 사용할 네임스페이스 생성
   - ServiceAccount 생성

초기 파일 생성 전에 [공식 VM 설치 절차](https://istio.io/latest/docs/setup/install/virtual-machine/)로 기존 Control Plane을 VM에 노출하세요. 클러스터 전용 istiod Service만으로는 부족합니다. 아래는 하나의 논리 네트워크에서 Pod와 VM의 라우팅이 가능한 구성이며 분리된 네트워크는 문서의 east-west/network 설정을 적용해야 합니다. 생성할 cluster ID는 istiod 구성과 일치해야 합니다.

### 1단계: ServiceAccount 생성

```bash
# 네임스페이스 생성
kubectl create namespace vm-workloads

# ServiceAccount 생성
kubectl create serviceaccount vm-postgres-sa -n vm-workloads

# VM ID 초기화에 Kubernetes Secret 목록 조회 권한은 필요하지 않습니다.
```

### 2단계: WorkloadGroup 초기 입력 준비

WorkloadGroup은 여러 WorkloadEntry의 템플릿 역할을 합니다:

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadGroup
metadata:
  name: postgres-vms
  namespace: vm-workloads
spec:
  metadata:
    labels:
      app: postgres
      version: v14
  template:
    serviceAccount: vm-postgres-sa
    network: ""  # Same logical network in this walkthrough
    ports:
      postgresql: 5432
      metrics: 9187
```

### 3단계: VM에 Envoy 설치

#### 자동 설치 스크립트 생성

```bash
# istioctl로 VM 등록 파일 생성
umask 077
istioctl x workload entry configure \
  -f workloadgroup.yaml \
  -o vm-postgres-1 \
  --clusterID Kubernetes

# 생성된 파일들:
# - cluster.env: 클러스터 정보
# - istio-token: 인증 토큰
# - mesh.yaml: 메시 구성
# - root-cert.pem: 루트 인증서
# - hosts: /etc/hosts 항목
```

#### VM에서 설치 실행

```bash
# Run on the administration workstation before entering the VM shell
ssh user@192.168.1.100 'install -d -m 700 "$HOME/istio-bootstrap"'
scp vm-postgres-1/* user@192.168.1.100:istio-bootstrap/
ssh user@192.168.1.100

# From this point, run on the VM
VM_BOOTSTRAP_DIR="$HOME/istio-bootstrap"
curl -fsSLo istio-sidecar.deb \
  https://blob.istio.io/istio-release/releases/1.31.0/deb/istio-sidecar.deb
sudo dpkg -i istio-sidecar.deb
sudo install -d -o istio-proxy -m 0750 \
  /etc/certs /var/run/secrets/tokens /var/lib/istio/envoy /etc/istio/config /etc/istio/proxy
sudo install -o istio-proxy -m 0644 "$VM_BOOTSTRAP_DIR/root-cert.pem" /etc/certs/root-cert.pem
sudo install -o istio-proxy -m 0600 "$VM_BOOTSTRAP_DIR/istio-token" /var/run/secrets/tokens/istio-token
sudo install -o istio-proxy -m 0600 "$VM_BOOTSTRAP_DIR/cluster.env" /var/lib/istio/envoy/cluster.env
sudo install -o istio-proxy -m 0600 "$VM_BOOTSTRAP_DIR/mesh.yaml" /etc/istio/config/mesh
# Review/merge once; replace stale istiod entries rather than appending duplicates
cat "$VM_BOOTSTRAP_DIR/hosts" | sudo tee -a /etc/hosts >/dev/null
sudo systemctl enable --now istio
sudo systemctl status istio
```



### 4단계: WorkloadEntry 등록

위 명령은 수동 등록 방식입니다. VM 에이전트 초기화 후 아래 WorkloadEntry를 적용하세요. 자동 등록된 VM에 같은 주소의 수동 항목을 중복 생성하지 마세요:

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: vm-workloads
spec:
  address: 192.168.1.100
  labels:
    app: postgres
    version: v14
  serviceAccount: vm-postgres-sa
  ports:
    postgresql: 5432
    metrics: 9187
```

```bash
kubectl apply -f workloadentry.yaml
```

### 5단계: ServiceEntry 생성

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: postgres-service
  namespace: vm-workloads
spec:
  hosts:
  - postgres.vm.internal
  addresses:
  - 240.240.2.1
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  - number: 9187
    name: metrics
    protocol: HTTP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
```

```bash
kubectl apply -f serviceentry.yaml
```

### 6단계: 연결 테스트

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pg-client
  namespace: vm-workloads
  labels:
    sidecar.istio.io/inject: "true"
  annotations:
    proxy.istio.io/config: |
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
spec:
  containers:
  - name: postgres
    image: postgres:14
    command: ["sleep", "infinity"]
```

```bash
kubectl apply -f pg-client.yaml
kubectl wait -n vm-workloads --for=condition=Ready pod/pg-client --timeout=120s
kubectl exec -it pg-client -n vm-workloads -c postgres -- \
  psql -h postgres.vm.internal -U dbuser -d mydb
```

Pod 매니페스트를 pg-client.yaml로 저장하세요. PostgreSQL 클라이언트 버전은 Istio 버전과 별개인 앱 예시입니다. DB 자격 증명은 대화형으로 제공하세요. 아래 제한 정책 적용 후에는 허용된 ServiceAccount로 검사해야 하며 기본 테스트 ID는 거부됩니다. 완료 후 테스트 Pod를 제거하세요.

## 보안 설정 (mTLS)

### mTLS 자동 활성화

선언한 ServiceAccount로 VM 에이전트를 초기화하면 메시 프록시가 자동 mTLS를 사용할 수 있습니다. WorkloadEntry만으로 일반 VM이 메시 참여자가 되지는 않습니다:

```yaml
# PeerAuthentication으로 mTLS 강제
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: vm-workloads
spec:
  mtls:
    mode: STRICT  # VM과 파드 모두 mTLS 필수
```

### VM 신원 확인

Pod Sidecar 초기화와 달리 VM 통합은 발급한 인증서/키를 /etc/certs에 보존하고 기존 mTLS ID로 갱신합니다. 성공적인 초기화 후 파일이 생성됩니다. 키를 보호하고 원인을 확인한 복구 절차에서 초기 자료를 재생성하며 자격 증명을 로그에 출력하지 마세요.

```bash
# VM에서 인증서 확인
sudo ls -la /etc/certs/
# cert-chain.pem: 인증서 체인
# key.pem: 개인 키
# root-cert.pem: 루트 CA

# 인증서 내용 확인
sudo openssl x509 -in /etc/certs/cert-chain.pem -text -noout

# Subject Alternative Name (SAN) 확인:
# spiffe://cluster.local/ns/vm-workloads/sa/vm-postgres-sa
```

### 접근 제어 (AuthorizationPolicy)

```yaml
# PostgreSQL 접근 제어
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: postgres-access
  namespace: vm-workloads
spec:
  selector:
    matchLabels:
      app: postgres  # WorkloadEntry의 레이블
  action: ALLOW
  rules:
  # API 서비스만 접근 허용
  - from:
    - source:
        principals:
        - cluster.local/ns/production/sa/api-service-sa
    to:
    - operation:
        ports: ["5432"]

  # 모니터링 서비스 접근 허용
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/prometheus
    to:
    - operation:
        ports: ["9187"]  # postgres_exporter
```

### mTLS 검증

```bash
# Use a PostgreSQL client in an authorized mesh workload; PostgreSQL is not HTTPS
kubectl exec -it <authorized-client-pod> -n production -c <app-container> -- \
  psql -h postgres.vm.internal -U dbuser -d mydb
# Inspect the client proxy's TLS transport and certificates separately
istioctl proxy-config clusters <authorized-client-pod> -n production --fqdn postgres.vm.internal -o json
istioctl proxy-config secret <authorized-client-pod> -n production
# On the VM, inspect public certificate information through its local admin interface
curl -fsS http://127.0.0.1:15000/certs
```

## 헬스체크 및 모니터링

### 헬스체크 구성

선택적 자동화 방식의 Control Plane 플래그는 `PILOT_ENABLE_WORKLOAD_ENTRY_AUTOREGISTRATION`, `PILOT_ENABLE_WORKLOAD_ENTRY_HEALTHCHECKS`입니다. 문서에 따라 기존 설치 설정에 병합하세요.

WorkloadGroup은 readiness probe를 지원합니다. 문서의 자동 등록/상태 점검 방식은 istiod 플래그 활성화, WorkloadGroup 적용, --autoregister를 사용한 초기 파일 생성이 필요하며 위 수동 경로와 구분되는 선택적 방식입니다. 아래 DestinationRule은 능동 probe가 아닌 연결 실패의 수동 관찰입니다:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: postgres-healthcheck
  namespace: vm-workloads
spec:
  host: postgres.vm.internal
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
    outlierDetection:
      consecutive5xxErrors: 5  # 5회 연속 실패 시
      interval: 30s         # 30초마다 확인
      baseEjectionTime: 30s # 30초 동안 제외
      maxEjectionPercent: 50 # 최대 50%까지 제외
      minHealthPercent: 0    # Panic fail-open 임계값 해제
```

```yaml
# Optional WorkloadGroup probe fragment for the documented auto-registration workflow
spec:
  probe:
    initialDelaySeconds: 5
    periodSeconds: 5
    timeoutSeconds: 3
    tcpSocket:
      host: 127.0.0.1
      port: 5432
```

### VM 헬스체크 엔드포인트

VM 애플리케이션에 헬스체크 엔드포인트를 추가하세요:

```python
# Python Flask 예시
from flask import Flask, jsonify
import psycopg2

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    try:
        # 데이터베이스 연결 확인
        conn = psycopg2.connect("dbname=mydb user=dbuser", connect_timeout=3)
        conn.close()
        return jsonify({"status": "healthy"}), 200
    except psycopg2.Error:
        return jsonify({"status": "unhealthy"}), 503

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
```

### Prometheus 메트릭 수집

ServiceMonitor는 WorkloadEntry/ServiceEntry가 아닌 Kubernetes Service/엔드포인트를 찾습니다. 이 VM에는 9187의 postgres_exporter를 설치하고 WorkloadEntry/ServiceEntry에 같은 포트를 등록한 뒤 기존 수집기 설정에 명시적 scrape job을 추가하세요. 수집기는 가상 호스트 DNS 조회, 메시 mTLS, exporter AuthorizationPolicy에서 허용한 ID가 필요합니다.

```yaml
# Fragment for the existing Prometheus scrape_configs
- job_name: workloadentry-postgres
  scrape_interval: 30s
  metrics_path: /metrics
  static_configs:
  - targets: ["postgres.vm.internal:9187"]
```

### Grafana 대시보드 쿼리

```promql
# Native PostgreSQL traffic has TCP counters, not HTTP status/latency metrics
sum(rate(istio_tcp_connections_opened_total{reporter="source",destination_service="postgres.vm.internal"}[5m]))
sum(rate(istio_tcp_sent_bytes_total{reporter="source",destination_service="postgres.vm.internal"}[5m]))

# Collector/exporter health; inspect the actual emitted labels
up{job="workloadentry-postgres"}
pg_up{job="workloadentry-postgres"}
```

## 고급 구성

### 멀티 네트워크 환경

network 이름은 토폴로지 식별자입니다. 연결성과 east-west 게이트웨이, 일치하는 mesh network 데이터를 별도 구성해야 하며 VPC 라우트·피어링·게이트웨이를 생성하지 않습니다. Locality는 region/zone/subzone이며 클라이언트 프록시와 맞는 실제 값을 사용하세요.

서로 다른 네트워크에 있는 VM 등록:

```yaml
# 네트워크 A의 VM
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-network-a
spec:
  address: 192.168.1.100
  labels:
    app: api-service
  serviceAccount: api-sa
  network: network-a
  ports:
    http: 8080
---
# 네트워크 B의 VM
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-network-b
spec:
  address: 10.0.1.100
  labels:
    app: api-service
  serviceAccount: api-sa
  network: network-b
  ports:
    http: 8080
```

### Locality-aware 로드 밸런싱

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-us-west
spec:
  address: 192.168.1.100
  labels:
    app: api-service
  locality: us-west-2/us-west-2a
  weight: 100
---
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-us-east
spec:
  address: 10.0.1.100
  labels:
    app: api-service
  locality: us-east-1/us-east-1a
  weight: 100
---
# DestinationRule로 locality-aware 라우팅
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-locality-lb
spec:
  host: api.service.internal
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west-2/*
          to:
            "us-west-2/*": 80
            "us-east-1/*": 20
        - from: us-east-1/*
          to:
            "us-east-1/*": 80
            "us-west-2/*": 20
```

### Canary 배포

WorkloadEntry에서도 Canary 배포를 적용할 수 있습니다:

```yaml
# v1 버전 VM
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-v1
spec:
  address: 192.168.1.100
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
---
# v2 버전 VM (Canary)
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-v2
spec:
  address: 192.168.1.101
  labels:
    app: api-service
    version: v2
  serviceAccount: api-sa
---
# VirtualService로 트래픽 분할
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-canary
spec:
  hosts:
  - api.service.internal
  http:
  - route:
    - destination:
        host: api.service.internal
        subset: v1
      weight: 90
    - destination:
        host: api.service.internal
        subset: v2
      weight: 10
---
# DestinationRule로 서브셋 정의
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-subsets
spec:
  host: api.service.internal
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## 문제 해결

### WorkloadEntry가 등록되지 않음

**증상**: `kubectl get workloadentry`에 리소스가 보이지만 트래픽이 라우팅되지 않음

**확인 사항**:

```bash
# 1. WorkloadEntry 상태 확인
kubectl get workloadentry -n vm-workloads -o yaml

# 2. ServiceEntry의 workloadSelector 확인
kubectl get serviceentry -n vm-workloads -o yaml | grep -A 5 workloadSelector

# 3. 레이블 매칭 확인
# WorkloadEntry labels:
#   app: postgres
# ServiceEntry workloadSelector:
#   labels:
#     app: postgres  # 일치해야 함

# 4. Envoy 구성 확인
istioctl proxy-config endpoints <pod-name> -n production

# 출력에 WorkloadEntry의 IP가 포함되어야 함:
# ENDPOINT            STATUS      CLUSTER
# 192.168.1.100:5432  HEALTHY     outbound|5432||postgres.vm.internal
```

**해결 방법**:

```yaml
# 레이블이 정확히 일치하도록 수정
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: vm-workloads
spec:
  address: 192.168.1.100
  serviceAccount: vm-postgres-sa
  labels:
    app: postgres  # ServiceEntry와 동일해야 함
    version: v14
```

### VM에서 mTLS 연결 실패

**증상**: `connection refused` 또는 `TLS handshake failed`

**확인 사항**:

```bash
# VM에서 Envoy 로그 확인
sudo journalctl -u istio -f | grep -i tls

# 인증서 확인
sudo ls -la /etc/certs/
sudo openssl x509 -in /etc/certs/cert-chain.pem -text -noout

# 인증서 만료 확인
sudo openssl x509 -in /etc/certs/cert-chain.pem -noout -dates

# ServiceAccount 토큰 확인
sudo ls -la /var/run/secrets/tokens/
sudo stat /var/run/secrets/tokens/istio-token
```

**해결 방법**:

```bash
# 관리 워크스테이션에서 초기 입력 재생성; 이 명령 자체가 인증서를 발급하지 않음
umask 077
istioctl x workload entry configure \
  -f workloadgroup.yaml \
  -o vm-postgres-1 \
  --clusterID Kubernetes

# VM에 복사 및 Envoy 재시작
scp vm-postgres-1/* user@192.168.1.100:istio-bootstrap/
# Reapply all reviewed runtime files and permissions using the VM installation steps,
# including the token and mesh configuration; then restart istio. Do not replace only the root CA.
```

### 헬스체크 실패로 트래픽이 가지 않음

**증상**: Envoy가 WorkloadEntry를 `UNHEALTHY`로 표시

**확인 사항**:

```bash
# Envoy 엔드포인트 상태 확인
istioctl proxy-config endpoints <pod-name> -n production | grep postgres

# 출력:
# 192.168.1.100:5432  UNHEALTHY  outbound|5432||postgres.vm.internal

# DestinationRule의 outlierDetection 확인
kubectl get destinationrule -n vm-workloads -o yaml
```

**해결 방법**:

```yaml
# OutlierDetection 설정 조정
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: postgres-healthcheck
  namespace: vm-workloads
spec:
  host: postgres.vm.internal
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 10     # 더 관대하게
      interval: 60s             # 체크 간격 늘림
      baseEjectionTime: 60s
      maxEjectionPercent: 50    # 제외 비율 제한; 100이면 전체 제외 허용
```

### DNS 조회 실패

ServiceEntry VIP만으로 CoreDNS 레코드가 생성되지 않습니다. 호출하는 Sidecar의 DNS 캡처를 활성화하고 Pod를 재생성하거나 실제 DNS 레코드를 제공하세요. VM 초기화의 DNS 프록시가 모든 Kubernetes 클라이언트의 캡처를 자동으로 켜지는 않습니다.

**증상**: 파드에서 `postgres.vm.internal` 조회 실패

**확인 사항**:

```bash
# ServiceEntry 확인
kubectl get serviceentry -n vm-workloads

# DNS 조회 테스트
kubectl exec pg-client -n vm-workloads -c postgres -- getent hosts postgres.vm.internal

# Istio DNS Proxy 활성화 확인
kubectl get pod <pod-name> -o yaml | grep ISTIO_META_DNS_CAPTURE
```

**해결 방법**:

```yaml
# ServiceEntry에 addresses 추가
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: postgres-service
  namespace: vm-workloads
spec:
  hosts:
  - postgres.vm.internal
  addresses:
  - 240.240.2.1  # 가상 IP 명시
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
```

## 모범 사례

### 1. 네이밍 규칙

```text
# WorkloadEntry 이름: <app>-<role>-<id>
name: postgres-primary-1
name: postgres-replica-2
name: api-backend-vm-3

# ServiceEntry 이름: <app>-service
name: postgres-service
name: api-service

# ServiceAccount 이름: <app>-sa
name: postgres-sa
name: api-sa
```

### 2. 레이블 전략

```yaml
spec:
  labels:
    # 필수 레이블
    app: postgres          # 애플리케이션 이름
    version: v14           # 버전

    # 선택 레이블
    tier: database         # 계층 (frontend, backend, database)
    role: primary          # 역할 (primary, replica, canary)
    environment: production # 환경
    team: platform         # 팀
```

### 3. ServiceAccount 관리

```bash
# 네임스페이스별 ServiceAccount 분리
kubectl create sa db-sa -n databases
kubectl create sa api-sa -n applications
kubectl create sa cache-sa -n middleware

# 최소 권한 원칙
kubectl create role db-limited \
  --verb=get \
  --resource=configmaps \
  -n databases
```

### 4. 모니터링 및 알림

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: workloadentry-alerts
  namespace: vm-workloads
spec:
  groups:
  - name: workloadentry
    rules:
    - alert: VMExporterScrapeDown
      expr: up{job="workloadentry-postgres"} == 0 or absent(up{job="workloadentry-postgres"})
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "VM exporter scrape target is unavailable"
    - alert: PostgresExporterReportsDown
      expr: pg_up{job="workloadentry-postgres"} == 0
      for: 5m
      labels:
        severity: warning
```



### 5. 문서화

각 WorkloadEntry에 대한 문서를 유지하세요:

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-primary-1
  annotations:
    description: "Primary PostgreSQL database for production"
    owner: "platform-team@example.com"
    provisioned-date: "2025-11-26"
    os: "Ubuntu 22.04 LTS"
    location: "us-west-2a"
    runbook: "https://wiki.example.com/postgres-vm-runbook"
spec:
  address: 192.168.1.100
  labels:
    app: postgres
    version: v14
```

### 6. 백업 및 재해 복구

진단용 export와 별도로 원본 WorkloadGroup/ServiceEntry/수동 WorkloadEntry 파일과 메시 버전을 보존하세요. VM의 보존된 ID 자료는 필요한 보안 백업 절차를 따릅니다. Export에는 서버 metadata/status가 있어 복구 전 검토해야 하며 자동 등록 항목은 컨트롤러가 재생성하도록 하고 수동 중복을 만들지 마세요. 네임스페이스·계정·Control Plane 연결성을 먼저 복구합니다.

```bash
# WorkloadEntry 백업
kubectl get workloadentry -n vm-workloads -o yaml > workloadentries-backup.yaml

# ServiceEntry 백업
kubectl get serviceentry -n vm-workloads -o yaml > serviceentries-backup.yaml

# 복원
kubectl apply -f serviceentry.yaml
# Manual-registration path only: use the reviewed declarative source, not raw status snapshots
kubectl apply -f workloadentry.yaml
```

### 7. 점진적 마이그레이션 전략

![WorkloadEntry로 메시에 등록한 VM 워크로드를 5단계에 걸쳐 Kubernetes로 옮기는 점진적 마이그레이션 흐름을, 4단계 트래픽 전환을 핵심 지점으로 강조해 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-13-workload-entry-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-13-workload-entry-4.html)

단계 시작 전에 레거시 VM ID를 초기화하고 아래 공유 ServiceEntry/subset을 생성하세요. Kubernetes 배포도 vm-workloads에 app=api, version=k8s 레이블로 만들고 프록시/DNS를 준비한 뒤 트래픽을 옮깁니다.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: api-migration-service
  namespace: vm-workloads
spec:
  hosts: [api.internal]
  addresses: [240.240.4.1]
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: api
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-migration-subsets
  namespace: vm-workloads
spec:
  host: api.internal
  subsets:
  - name: legacy
    labels:
      version: legacy
  - name: k8s
    labels:
      version: k8s
```

**1단계: VM 메시 등록**
```yaml
# WorkloadEntry 등록
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm
  namespace: vm-workloads
spec:
  serviceAccount: api-sa
  address: 192.168.1.100
  labels:
    app: api
    version: legacy
```

**2단계: 트래픽 분할 (100% VM)**
```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-migration
  namespace: vm-workloads
spec:
  hosts:
  - api.internal
  http:
  - route:
    - destination:
        host: api.internal
        subset: legacy
      weight: 100
```

**3단계: Kubernetes 배포**
```bash
kubectl apply -n vm-workloads -f kubernetes-deployment.yaml
```

**4단계: 점진적 트래픽 전환**
```yaml
# 10% Kubernetes
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-migration
  namespace: vm-workloads
spec:
  hosts:
  - api.internal
  http:
  - route:
    - destination:
        host: api.internal
        subset: legacy  # VM
      weight: 90
    - destination:
        host: api.internal
        subset: k8s     # Kubernetes
      weight: 10
```

**5단계: VM 제거**
```bash
# 트래픽 100% Kubernetes로 전환 후
kubectl delete workloadentry legacy-api-vm -n vm-workloads
```

## 참고 자료

### 공식 문서
- [WorkloadEntry Reference](https://istio.io/latest/docs/reference/config/networking/workload-entry/)
- [WorkloadGroup Reference](https://istio.io/latest/docs/reference/config/networking/workload-group/)
- [Virtual Machine Installation](https://istio.io/latest/docs/setup/install/virtual-machine/)

### 관련 문서
- [기본 개념 - VM 워크로드 등록](../02-basic-concepts.md#vm-워크로드-등록)
- [ServiceEntry](12-service-entry.md)
- [Egress 제어](11-egress-control.md)
- [보안 - mTLS](../security/01-mtls.md)

### 추가 자료
- [Istio VM Integration Guide](https://istio.io/latest/blog/2020/workload-entry/)
- [Envoy Proxy Documentation](https://www.envoyproxy.io/docs/envoy/latest/)

- [Primary reference 1](https://istio.io/latest/docs/setup/install/virtual-machine/)
- [Primary reference 2](https://istio.io/latest/docs/ops/diagnostic-tools/virtual-machines/)
- [Primary reference 3](https://istio.io/latest/docs/reference/config/networking/workload-entry/)
- [Primary reference 4](https://istio.io/latest/docs/reference/config/networking/workload-group/)
- [Primary reference 5](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [Primary reference 6](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Primary reference 7](https://prometheus-operator.dev/docs/api-reference/api/)
- [Primary reference 8](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
