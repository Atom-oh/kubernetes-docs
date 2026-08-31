# SPIFFE/SPIRE를 활용한 워크로드 아이덴티티

> **지원 버전**: SPIRE 1.12+, Kubernetes 1.31, 1.32, 1.33
> **마지막 업데이트**: 2026년 2월 25일

## 개요

제로 트러스트(Zero Trust) 아키텍처에서 워크로드 아이덴티티는 핵심적인 구성 요소입니다. 전통적인 네트워크 경계 기반 보안 모델에서는 "내부 네트워크는 신뢰할 수 있다"는 가정이 있었지만, 현대 클라우드 네이티브 환경에서는 이러한 가정이 더 이상 유효하지 않습니다.

**SPIFFE**(Secure Production Identity Framework for Everyone)는 이기종 환경에서 워크로드 간 상호 인증을 위한 표준화된 아이덴티티 프레임워크를 제공합니다. **SPIRE**(SPIFFE Runtime Environment)는 SPIFFE 사양의 프로덕션 레디 구현체로, CNCF Graduated 프로젝트입니다.

### 왜 SPIFFE/SPIRE가 필요한가?

| 기존 방식의 문제점 | SPIFFE/SPIRE 솔루션 |
|-------------------|---------------------|
| IP 기반 인증 - 동적 환경에서 불안정 | 암호화된 아이덴티티 기반 인증 |
| 수동 인증서 관리 - 운영 부담 | 자동 인증서 발급 및 갱신 |
| 단일 클러스터 범위 - 확장성 제한 | 크로스 클러스터, 멀티 클라우드 페더레이션 |
| 플랫폼 종속적 아이덴티티 | 플랫폼 독립적 표준 |
| 장기 유효 자격 증명 - 보안 위험 | 단기 자동 갱신 SVID |

---

## 목차

1. [핵심 개념](#1-핵심-개념)
2. [SPIRE 아키텍처](#2-spire-아키텍처)
3. [설치 및 구성](#3-설치-및-구성)
4. [노드 어테스테이션](#4-노드-어테스테이션)
5. [워크로드 어테스테이션](#5-워크로드-어테스테이션)
6. [Kubernetes 통합](#6-kubernetes-통합)
7. [서비스 메시 연동](#7-서비스-메시-연동)
8. [페더레이션](#8-페더레이션)
9. [EKS 통합](#9-eks-통합)
10. [모범 사례](#10-모범-사례)
11. [요약 및 참고 자료](#11-요약-및-참고-자료)

---

## 1. 핵심 개념

### SPIFFE ID

SPIFFE ID는 워크로드를 고유하게 식별하는 URI 형식의 식별자입니다.

```
spiffe://trust-domain/workload-identifier
```

**구성 요소**:
- `spiffe://` - SPIFFE 스키마 (고정)
- `trust-domain` - 신뢰 도메인 (예: `example.org`, `prod.acme.com`)
- `workload-identifier` - 워크로드 경로 (예: `/ns/default/sa/web-server`)

**SPIFFE ID 예시**:

```
# Kubernetes 워크로드
spiffe://prod.example.com/ns/payments/sa/payment-processor

# AWS EC2 인스턴스
spiffe://aws.example.com/region/us-east-1/instance/i-0123456789abcdef

# 데이터베이스 서비스
spiffe://example.com/database/mysql/primary
```

### SVID (SPIFFE Verifiable Identity Document)

SVID는 SPIFFE ID를 포함하는 암호화적으로 검증 가능한 문서입니다. 두 가지 형식을 지원합니다.

#### X.509-SVID vs JWT-SVID 비교

| 특성 | X.509-SVID | JWT-SVID |
|------|-----------|----------|
| **형식** | X.509 인증서 | JSON Web Token |
| **용도** | mTLS 연결, 장기 서비스 통신 | API 인증, 단기 토큰 교환 |
| **SPIFFE ID 위치** | SAN URI 확장 | `sub` 클레임 |
| **크기** | 상대적으로 큼 | 상대적으로 작음 |
| **TTL** | 일반적으로 1시간 | 일반적으로 5분 |
| **갱신** | 자동 갱신 필수 | 필요시 재발급 |
| **검증** | 인증서 체인 검증 | 서명 검증 + 클레임 확인 |
| **사용 사례** | 서비스 메시, 데이터베이스 연결 | REST API, 외부 서비스 호출 |

**X.509-SVID 구조**:

```
Certificate:
    Data:
        Version: 3
        Serial Number: ...
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: CN=SPIFFE Trust Domain (prod.example.com)
        Validity:
            Not Before: Feb 25 00:00:00 2026 GMT
            Not After : Feb 25 01:00:00 2026 GMT
        Subject: CN=SPIFFE ID: spiffe://prod.example.com/ns/default/sa/web
        X509v3 extensions:
            X509v3 Subject Alternative Name:
                URI:spiffe://prod.example.com/ns/default/sa/web
            X509v3 Key Usage: critical
                Digital Signature, Key Encipherment
            X509v3 Extended Key Usage:
                TLS Web Server Authentication, TLS Web Client Authentication
```

### Trust Bundle

Trust Bundle은 특정 Trust Domain의 루트 CA 인증서들을 포함하는 집합입니다. 워크로드는 Trust Bundle을 사용하여 상대방의 SVID를 검증합니다.

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "x509-svid",
      "n": "...",
      "e": "AQAB",
      "x5c": ["MIIBkTCB..."]
    }
  ],
  "spiffe_refresh_hint": 300
}
```

---

## 2. SPIRE 아키텍처

### 컴포넌트 개요

![SPIRE Server가 데이터스토어와 CA를 관리하며 각 노드의 SPIRE Agent로부터 노드 어테스테이션과 SVID 요청을 받고, Agent는 자신이 실행 중인 노드의 워크로드들에 Workload API로 SVID를 전달하며, Controller Manager가 등록 엔트리를 관리하는 구조를 보여준다.](../../assets/diagrams/rendered/ko-security-12-spiffe-spire-0.svg)

### SPIRE Server

SPIRE Server는 아이덴티티 관리의 중앙 컴포넌트로 다음 기능을 수행합니다:

- **Certificate Authority (CA)**: X.509-SVID 및 JWT-SVID 서명
- **Registration API**: 워크로드 등록 엔트리 관리
- **Node Attestation**: 에이전트 노드 검증
- **Datastore**: 등록 엔트리, CA 키 등 영속 데이터 저장

### SPIRE Agent

SPIRE Agent는 각 노드에서 실행되며 다음 기능을 수행합니다:

- **Workload API**: Unix 도메인 소켓을 통한 SVID 제공
- **Workload Attestation**: 로컬 워크로드 검증
- **SVID 캐싱 및 갱신**: 효율적인 인증서 라이프사이클 관리
- **SDS (Secret Discovery Service)**: Envoy와의 통합

### SVID 발급 플로우

![애플리케이션이 Workload API로 SVID를 요청하면 Agent가 프로세스 정보로 어테스테이션 셀렉터를 매칭하고 Server의 Node API가 등록 엔트리를 확인해 CA로 서명한 X.509-SVID를 발급, Agent가 캐시에 저장한 뒤 애플리케이션에 전달하는 과정을 보여준다.](../../assets/diagrams/rendered/ko-security-12-spiffe-spire-1.svg)

---

## 3. 설치 및 구성

### Helm 차트를 이용한 설치

SPIRE Helm 차트는 전체 SPIRE 인프라를 단일 명령으로 배포합니다.

```bash
# SPIRE Helm 저장소 추가
helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/
helm repo update

# 네임스페이스 생성
kubectl create namespace spire-system

# SPIRE 설치 (기본 구성)
helm install spire spiffe/spire \
  --namespace spire-system \
  --set global.spire.trustDomain=example.org
```

### 프로덕션 구성

```yaml
# values-production.yaml
global:
  spire:
    trustDomain: prod.example.com
    clusterName: eks-prod-cluster

spire-server:
  replicaCount: 3

  dataStore:
    sql:
      databaseType: postgres
      connectionString: "postgres://spire:password@postgres:5432/spire?sslmode=require"

  ca:
    # 외부 CA 사용 (선택사항)
    upstreamAuthority:
      awsPCA:
        region: us-east-1
        certificateAuthorityArn: arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/xxx

  nodeAttestor:
    k8sPsat:
      enabled: true
      serviceAccountAllowList:
        - spire-system:spire-agent

  # HA 구성
  controllerManager:
    enabled: true

  federation:
    enabled: true
    bundleEndpoint:
      port: 8443

spire-agent:
  nodeAttestor:
    k8sPsat:
      enabled: true

  workloadAttestors:
    - k8s
    - unix
```

```bash
# 프로덕션 설치
helm upgrade --install spire spiffe/spire \
  --namespace spire-system \
  --values values-production.yaml \
  --wait
```

### 설치 확인

```bash
# SPIRE Server 상태 확인
kubectl get pods -n spire-system -l app.kubernetes.io/name=server

# SPIRE Agent 상태 확인 (DaemonSet)
kubectl get pods -n spire-system -l app.kubernetes.io/name=agent

# Server 상태 상세 확인
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server healthcheck

# 등록된 에이전트 목록
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server agent list
```

---

## 4. 노드 어테스테이션

노드 어테스테이션은 SPIRE Agent가 실행되는 노드의 신원을 확인하는 프로세스입니다.

### 어테스테이션 방식 비교

| 방식 | 설명 | 사용 환경 | 보안 수준 |
|------|------|----------|----------|
| **k8s_psat** | Kubernetes Projected ServiceAccount Token | Kubernetes | 높음 |
| **aws_iid** | AWS Instance Identity Document | AWS EC2 | 높음 |
| **gcp_iit** | GCP Instance Identity Token | GCP Compute | 높음 |
| **azure_msi** | Azure Managed Identity | Azure VM | 높음 |
| **join_token** | 일회용 토큰 | 모든 환경 | 중간 |
| **x509pop** | 기존 X.509 인증서 | 하이브리드 | 높음 |

### 노드 및 워크로드 어테스테이션 플로우

![SPIRE Agent가 k8s_psat 토큰 또는 aws_iid 문서로 노드 어테스테이션을 거쳐 Node SVID를 발급받은 뒤, 이를 이용해 워크로드의 Pod 메타데이터와 UID/GID를 확인하고 등록 엔트리와 매칭해 Workload SVID를 발급하는 두 단계 절차를 보여준다.](../../assets/diagrams/rendered/ko-security-12-spiffe-spire-2.svg)

### Kubernetes PSAT 어테스테이션 구성

```yaml
# SPIRE Server 구성 - k8s_psat 노드 어테스터
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-server-config
  namespace: spire-system
data:
  server.conf: |
    server {
      bind_address = "0.0.0.0"
      bind_port = "8081"
      trust_domain = "prod.example.com"
      data_dir = "/run/spire/data"
      log_level = "INFO"

      ca_ttl = "24h"
      default_x509_svid_ttl = "1h"
      default_jwt_svid_ttl = "5m"
    }

    plugins {
      DataStore "sql" {
        plugin_data {
          database_type = "sqlite3"
          connection_string = "/run/spire/data/datastore.sqlite3"
        }
      }

      NodeAttestor "k8s_psat" {
        plugin_data {
          clusters = {
            "eks-prod" = {
              service_account_allow_list = ["spire-system:spire-agent"]
              kube_config_file = ""
              allowed_node_label_keys = ["topology.kubernetes.io/zone"]
              allowed_pod_label_keys = ["app.kubernetes.io/name"]
            }
          }
        }
      }

      KeyManager "disk" {
        plugin_data {
          keys_path = "/run/spire/data/keys.json"
        }
      }
    }
```

### AWS IID 어테스테이션 구성

```yaml
# AWS IID 노드 어테스터 (하이브리드 환경용)
plugins {
  NodeAttestor "aws_iid" {
    plugin_data {
      skip_block_device = true
      account_ids_for_local_validation = ["123456789012"]

      # IAM 역할 기반 추가 검증
      agent_path_template = "/aws/{{ .AccountID }}/{{ .Region }}/{{ .InstanceID }}"
    }
  }
}
```

---

## 5. 워크로드 어테스테이션

워크로드 어테스테이션은 SPIRE Agent가 로컬에서 실행 중인 워크로드의 신원을 확인하는 프로세스입니다.

### Kubernetes 워크로드 어테스터

Kubernetes 어테스터는 다음 셀렉터를 제공합니다:

| 셀렉터 | 설명 | 예시 |
|--------|------|------|
| `k8s:ns` | 네임스페이스 | `k8s:ns:payments` |
| `k8s:sa` | ServiceAccount | `k8s:sa:payment-processor` |
| `k8s:pod-label` | Pod 레이블 | `k8s:pod-label:app:web` |
| `k8s:pod-owner` | 소유자 종류 | `k8s:pod-owner:Deployment` |
| `k8s:pod-owner-uid` | 소유자 UID | `k8s:pod-owner-uid:xxx` |
| `k8s:pod-name` | Pod 이름 | `k8s:pod-name:web-xxx` |
| `k8s:pod-uid` | Pod UID | `k8s:pod-uid:xxx` |
| `k8s:container-name` | 컨테이너 이름 | `k8s:container-name:app` |
| `k8s:container-image` | 컨테이너 이미지 | `k8s:container-image:nginx:1.25` |
| `k8s:node-name` | 노드 이름 | `k8s:node-name:ip-10-0-1-5` |

### SPIRE Agent 구성 - 워크로드 어테스터

```yaml
# SPIRE Agent 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-agent-config
  namespace: spire-system
data:
  agent.conf: |
    agent {
      data_dir = "/run/spire/data"
      log_level = "INFO"
      server_address = "spire-server.spire-system.svc.cluster.local"
      server_port = "8081"
      socket_path = "/run/spire/sockets/agent.sock"
      trust_domain = "prod.example.com"
    }

    plugins {
      NodeAttestor "k8s_psat" {
        plugin_data {
          cluster = "eks-prod"
          token_path = "/var/run/secrets/tokens/spire-agent"
        }
      }

      KeyManager "memory" {
        plugin_data {}
      }

      WorkloadAttestor "k8s" {
        plugin_data {
          # Kubelet API를 통한 Pod 정보 조회
          skip_kubelet_verification = false
          kubelet_ca_path = "/run/secrets/kubernetes.io/serviceaccount/ca.crt"
          node_name_env = "MY_NODE_NAME"

          # 비활성화할 컨테이너 셀렉터
          disable_container_selectors = false
        }
      }

      WorkloadAttestor "unix" {
        plugin_data {
          # UID/GID 기반 어테스테이션
        }
      }
    }
```

### 등록 엔트리 생성

```bash
# CLI를 통한 등록 엔트리 생성
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://prod.example.com/ns/payments/sa/payment-processor \
  -parentID spiffe://prod.example.com/spire/agent/k8s_psat/eks-prod/xxx \
  -selector k8s:ns:payments \
  -selector k8s:sa:payment-processor \
  -ttl 3600

# DNS 이름 추가 (mTLS용)
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://prod.example.com/ns/payments/sa/payment-processor \
  -parentID spiffe://prod.example.com/spire/agent/k8s_psat/eks-prod/xxx \
  -selector k8s:ns:payments \
  -selector k8s:sa:payment-processor \
  -dns payment-processor.payments.svc.cluster.local \
  -dns payment-processor
```

---

## 6. Kubernetes 통합

### SPIFFE CSI Driver

SPIFFE CSI Driver는 Pod에 SVID를 파일 시스템으로 마운트합니다.

```yaml
# CSI Driver 설치 (Helm)
# values-csi.yaml
spiffe-csi-driver:
  enabled: true
  agentSocketPath: /run/spire/sockets/agent.sock
```

```yaml
# Pod에서 SVID 마운트
apiVersion: v1
kind: Pod
metadata:
  name: payment-processor
  namespace: payments
spec:
  serviceAccountName: payment-processor
  containers:
  - name: app
    image: payment-app:v1.0
    volumeMounts:
    - name: spiffe-workload-api
      mountPath: /spiffe-workload-api
      readOnly: true
    env:
    - name: SPIFFE_ENDPOINT_SOCKET
      value: unix:///spiffe-workload-api/spire-agent.sock
  volumes:
  - name: spiffe-workload-api
    csi:
      driver: "csi.spiffe.io"
      readOnly: true
```

### SPIRE Controller Manager (자동 등록)

SPIRE Controller Manager는 `ClusterSPIFFEID` CR을 감시하여 자동으로 등록 엔트리를 생성합니다.

```yaml
# ClusterSPIFFEID - 네임스페이스 기반 자동 등록
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: payments-workloads
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/ns/{{ .PodMeta.Namespace }}/sa/{{ .PodSpec.ServiceAccountName }}"
  podSelector:
    matchLabels:
      spiffe.io/spire-managed-identity: "true"
  namespaceSelector:
    matchLabels:
      spiffe.io/spire-enabled: "true"
  dnsNameTemplates:
    - "{{ .PodMeta.Name }}"
    - "{{ .PodMeta.Name }}.{{ .PodMeta.Namespace }}.svc.cluster.local"
  workloadSelectorTemplates:
    - "k8s:ns:{{ .PodMeta.Namespace }}"
    - "k8s:sa:{{ .PodSpec.ServiceAccountName }}"
  ttl: "1h"
  jwtTtl: "5m"
```

```yaml
# 컨테이너 이미지 기반 SPIFFE ID
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: nginx-workloads
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/workload/nginx"
  podSelector:
    matchExpressions:
    - key: app.kubernetes.io/name
      operator: In
      values: ["nginx", "nginx-ingress"]
  workloadSelectorTemplates:
    - "k8s:container-image:nginx:*"
  ttl: "30m"
```

```yaml
# 특정 Deployment를 위한 세밀한 제어
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: database-client
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/database/client/{{ .PodMeta.Namespace }}"
  podSelector:
    matchLabels:
      database-access: "true"
  namespaceSelector:
    matchExpressions:
    - key: environment
      operator: In
      values: ["production", "staging"]
  federatesWith:
    - "spiffe://database.example.com"
  ttl: "15m"
```

### Envoy SDS 연동

SPIRE Agent는 Envoy의 Secret Discovery Service(SDS)를 통해 인증서를 동적으로 제공합니다.

```yaml
# Envoy Bootstrap 구성
node:
  id: payment-proxy
  cluster: payments

static_resources:
  listeners:
  - name: mtls_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8443
    filter_chains:
    - transport_socket:
        name: envoy.transport_sockets.tls
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
          common_tls_context:
            tls_certificate_sds_secret_configs:
            - name: "spiffe://prod.example.com/ns/payments/sa/payment-processor"
              sds_config:
                resource_api_version: V3
                api_config_source:
                  api_type: GRPC
                  transport_api_version: V3
                  grpc_services:
                  - envoy_grpc:
                      cluster_name: spire_agent
            combined_validation_context:
              default_validation_context:
                match_typed_subject_alt_names:
                - san_type: URI
                  matcher:
                    prefix: "spiffe://prod.example.com/"
              validation_context_sds_secret_config:
                name: "spiffe://prod.example.com"
                sds_config:
                  resource_api_version: V3
                  api_config_source:
                    api_type: GRPC
                    transport_api_version: V3
                    grpc_services:
                    - envoy_grpc:
                        cluster_name: spire_agent

  clusters:
  - name: spire_agent
    connect_timeout: 1s
    type: STATIC
    http2_protocol_options: {}
    load_assignment:
      cluster_name: spire_agent
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              pipe:
                path: /run/spire/sockets/agent.sock
```

---

## 7. 서비스 메시 연동

### Istio + SPIRE

Istio는 기본적으로 자체 CA(istiod)를 사용하지만, SPIRE를 외부 CA로 사용하도록 구성할 수 있습니다.

```yaml
# Istio 설치 시 SPIRE 통합 구성
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-spire
spec:
  profile: default

  meshConfig:
    trustDomain: prod.example.com

  values:
    global:
      # SPIRE를 CA 소스로 사용
      caAddress: spire-server.spire-system.svc:8081

    pilot:
      env:
        # SPIFFE Identity 사용
        ENABLE_SPIFFE_IDENTITY: "true"
        # SPIRE 통합 활성화
        PILOT_ENABLE_SPIRE_INTEGRATION: "true"

  components:
    pilot:
      k8s:
        env:
        - name: SPIFFE_ENDPOINT_SOCKET
          value: "unix:///run/spire/sockets/agent.sock"
        volumes:
        - name: spire-agent-socket
          csi:
            driver: "csi.spiffe.io"
            readOnly: true
        volumeMounts:
        - name: spire-agent-socket
          mountPath: /run/spire/sockets
          readOnly: true
```

### Cilium + SPIRE

Cilium은 SPIRE와 연동하여 네트워크 정책과 워크로드 아이덴티티를 통합합니다.

```yaml
# Cilium Helm values - SPIRE 통합
cilium:
  authentication:
    enabled: true
    mode: required

    mutual:
      spire:
        enabled: true
        trustDomain: prod.example.com
        serverAddress: spire-server.spire-system.svc:8081

        # SPIRE Agent 소켓 경로
        agentSocketPath: /run/spire/sockets/agent.sock

        # Cilium용 SPIFFE ID 템플릿
        connectionTimeout: 30s

  # 네트워크 정책에서 SPIFFE ID 사용
  policyEnforcementMode: always
```

```yaml
# Cilium Network Policy with SPIFFE Identity
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-payment-to-database
  namespace: payments
spec:
  endpointSelector:
    matchLabels:
      app: database
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: payment-processor
    authentication:
      mode: required
    # SPIFFE ID 기반 추가 검증
    fromRequires:
    - matchLabels:
        io.cilium.spiffe/id: "spiffe://prod.example.com/ns/payments/sa/payment-processor"
```

### Linkerd + SPIRE

Linkerd는 자체 Identity 시스템을 사용하지만, Trust Anchor를 외부에서 주입할 수 있습니다.

```bash
# SPIRE에서 Trust Bundle 추출
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server bundle show -format spiffe > trust-bundle.json

# Trust Bundle에서 CA 인증서 추출
cat trust-bundle.json | jq -r '.keys[0].x5c[0]' | base64 -d > ca.crt

# Linkerd 설치 시 SPIRE CA 사용
linkerd install --identity-external-issuer \
  --identity-trust-anchors-file ca.crt \
  | kubectl apply -f -
```

---

## 8. 페더레이션

페더레이션은 서로 다른 Trust Domain 간에 신뢰를 설정하여 크로스 클러스터 또는 멀티 클라우드 환경에서 워크로드 간 인증을 가능하게 합니다.

### 페더레이션 아키텍처

![서로 다른 트러스트 도메인의 SPIRE Server가 각각 Bundle Endpoint를 통해 상대방의 Trust Bundle을 주기적으로 교환·저장하고, 이를 신뢰 기반으로 두 도메인의 워크로드가 직접 mTLS로 통신하는 구조를 보여준다.](../../assets/diagrams/rendered/ko-security-12-spiffe-spire-3.svg)

### 페더레이션 구성

**Trust Domain A (US 클러스터)**:

```yaml
# values-federation-us.yaml
global:
  spire:
    trustDomain: prod.us.example.com
    clusterName: eks-us-cluster

spire-server:
  federation:
    enabled: true

    bundleEndpoint:
      enabled: true
      port: 8443
      # 공개적으로 접근 가능한 주소
      address: "spire-us.example.com"

    # 신뢰할 외부 Trust Domain
    federatedTrustDomains:
      - name: prod.eu.example.com
        bundleEndpointURL: "https://spire-eu.example.com:8443"
        bundleEndpointProfile:
          type: https_spiffe
          endpointSPIFFEID: "spiffe://prod.eu.example.com/spire/server"
```

**Trust Domain B (EU 클러스터)**:

```yaml
# values-federation-eu.yaml
global:
  spire:
    trustDomain: prod.eu.example.com
    clusterName: eks-eu-cluster

spire-server:
  federation:
    enabled: true

    bundleEndpoint:
      enabled: true
      port: 8443
      address: "spire-eu.example.com"

    federatedTrustDomains:
      - name: prod.us.example.com
        bundleEndpointURL: "https://spire-us.example.com:8443"
        bundleEndpointProfile:
          type: https_spiffe
          endpointSPIFFEID: "spiffe://prod.us.example.com/spire/server"
```

### 크로스 클러스터 워크로드 등록

```yaml
# US 클러스터의 워크로드가 EU 클러스터와 통신
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: cross-region-workload
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/ns/{{ .PodMeta.Namespace }}/sa/{{ .PodSpec.ServiceAccountName }}"
  podSelector:
    matchLabels:
      cross-region-access: "true"
  # 페더레이션된 Trust Domain 지정
  federatesWith:
    - "spiffe://prod.eu.example.com"
  ttl: "1h"
```

### 페더레이션 상태 확인

```bash
# 페더레이션 번들 목록 확인
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server bundle list

# 특정 Trust Domain 번들 확인
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server bundle show -id spiffe://prod.eu.example.com

# 페더레이션 관계 확인
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server federation list
```

---

## 9. EKS 통합

### IRSA vs SPIFFE 비교

| 특성 | IRSA (IAM Roles for Service Accounts) | SPIFFE/SPIRE |
|------|--------------------------------------|--------------|
| **범위** | AWS 서비스 접근 | 워크로드 간 상호 인증 |
| **아이덴티티 형식** | OIDC + IAM Role ARN | X.509-SVID, JWT-SVID |
| **신뢰 범위** | 단일 AWS 계정/클러스터 | 크로스 클러스터, 멀티 클라우드 |
| **자동 갱신** | 자동 (12시간 TTL) | 자동 (구성 가능한 TTL) |
| **mTLS 지원** | 미지원 | 기본 지원 |
| **관리 주체** | AWS 관리형 | 자체 관리형 |
| **비용** | 무료 | 인프라 비용 |
| **사용 사례** | S3, DynamoDB 등 AWS 서비스 | 서비스 간 통신, 외부 시스템 |

### EKS Pod Identity vs SPIRE 비교

| 특성 | EKS Pod Identity | SPIRE |
|------|------------------|-------|
| **설정 복잡도** | 낮음 | 중간 |
| **플랫폼 독립성** | AWS 전용 | 플랫폼 독립 |
| **페더레이션** | AWS 계정 간 | 모든 Trust Domain |
| **인증서 기반 인증** | 미지원 | 기본 지원 |
| **운영 부담** | 낮음 | 중간 |

### 하이브리드 사용 사례

대부분의 EKS 환경에서는 IRSA/Pod Identity와 SPIRE를 함께 사용하는 것이 권장됩니다:

```yaml
# Pod에서 IRSA와 SPIRE 동시 사용
apiVersion: v1
kind: Pod
metadata:
  name: hybrid-workload
  namespace: payments
spec:
  serviceAccountName: payment-processor  # IRSA 연결
  containers:
  - name: app
    image: payment-app:v1.0
    env:
    # SPIRE Workload API
    - name: SPIFFE_ENDPOINT_SOCKET
      value: unix:///spiffe-workload-api/spire-agent.sock
    # AWS SDK는 자동으로 IRSA 사용
    volumeMounts:
    - name: spiffe-workload-api
      mountPath: /spiffe-workload-api
      readOnly: true
  volumes:
  - name: spiffe-workload-api
    csi:
      driver: "csi.spiffe.io"
      readOnly: true
---
# ServiceAccount with IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: payment-processor
  namespace: payments
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/PaymentProcessorRole
```

### AWS Private CA 통합

프로덕션 환경에서는 SPIRE의 내장 CA 대신 AWS Private CA를 사용할 수 있습니다:

```yaml
# SPIRE Server - AWS PCA Upstream Authority
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-server-config
  namespace: spire-system
data:
  server.conf: |
    server {
      trust_domain = "prod.example.com"
    }

    plugins {
      UpstreamAuthority "aws_pca" {
        plugin_data {
          region = "us-east-1"
          certificate_authority_arn = "arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/xxx"

          # 서명 알고리즘
          signing_algorithm = "SHA256WITHRSA"

          # CA 인증서 번들 (선택사항)
          ca_signing_template_arn = "arn:aws:acm-pca:::template/SubordinateCACertificate_PathLen0/V1"

          # 보조 리전 (선택사항, 고가용성)
          supplemental_bundle_path = "/run/spire/data/supplemental-bundle.pem"
        }
      }
    }
```

---

## 10. 모범 사례

### Trust Domain 네이밍 전략

```
# 권장 패턴
spiffe://{environment}.{organization}.{tld}

# 예시
spiffe://prod.acme.com          # 프로덕션
spiffe://staging.acme.com       # 스테이징
spiffe://dev.acme.com           # 개발

# 멀티 리전
spiffe://prod.us-east-1.acme.com
spiffe://prod.eu-west-1.acme.com

# 멀티 클라우드
spiffe://prod.aws.acme.com
spiffe://prod.gcp.acme.com
```

**주의사항**:
- Trust Domain은 변경하기 어려우므로 신중하게 설계
- 환경(dev/staging/prod)을 Trust Domain에 포함하여 격리
- DNS 호환 형식 권장

### SVID TTL 튜닝

| 사용 사례 | X.509-SVID TTL | JWT-SVID TTL | 근거 |
|----------|----------------|--------------|------|
| 일반 서비스 | 1시간 | 5분 | 표준 보안/성능 균형 |
| 고보안 서비스 | 15분 | 2분 | 키 노출 위험 최소화 |
| 배치 작업 | 2시간 | 10분 | 장기 실행 작업 허용 |
| CI/CD 파이프라인 | 30분 | 5분 | 빌드 시간 내 유효 |

```yaml
# ClusterSPIFFEID에서 TTL 설정
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: high-security-workload
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/hs/{{ .PodSpec.ServiceAccountName }}"
  podSelector:
    matchLabels:
      security-tier: high
  ttl: "15m"      # X.509-SVID
  jwtTtl: "2m"    # JWT-SVID
```

### 고가용성 배포

```yaml
# HA SPIRE Server 구성
spire-server:
  replicaCount: 3

  # Pod Anti-Affinity
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app.kubernetes.io/name: server
        topologyKey: topology.kubernetes.io/zone

  # PostgreSQL 데이터스토어 (SQLite 대신)
  dataStore:
    sql:
      databaseType: postgres
      connectionString: "host=postgres-ha port=5432 dbname=spire user=spire sslmode=require"

  # 리소스 제한
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

  # PodDisruptionBudget
  podDisruptionBudget:
    minAvailable: 2
```

### 키 로테이션

SPIRE는 자동으로 CA 키를 로테이션합니다. 수동 로테이션이 필요한 경우:

```bash
# 현재 CA 상태 확인
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server bundle show

# 키 로테이션 수동 트리거 (준비된 키가 있는 경우)
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server bundle set -id spiffe://prod.example.com -path /path/to/new-bundle.json

# 로테이션 상태 모니터링
kubectl logs -n spire-system -l app.kubernetes.io/name=server --tail=100 | grep -i rotation
```

### 보안 강화 체크리스트

- [ ] 프로덕션에서 SQLite 대신 PostgreSQL 사용
- [ ] SPIRE Server 네트워크 정책으로 접근 제한
- [ ] AWS Private CA 또는 Vault를 Upstream CA로 사용 고려
- [ ] Trust Bundle 변경 모니터링 설정
- [ ] SVID 발급 감사 로그 활성화
- [ ] 노드 어테스테이션 허용 목록 최소화
- [ ] 워크로드 어테스테이션 셀렉터 세분화

---

## 11. 요약 및 참고 자료

### 핵심 요약

| 구성 요소 | 역할 | 핵심 기능 |
|----------|------|----------|
| SPIFFE ID | 워크로드 식별자 | URI 형식의 고유 식별 |
| X.509-SVID | 인증서 기반 아이덴티티 | mTLS, 장기 서비스 통신 |
| JWT-SVID | 토큰 기반 아이덴티티 | API 인증, 단기 토큰 |
| SPIRE Server | 아이덴티티 관리 | CA, 등록, 어테스테이션 |
| SPIRE Agent | 로컬 아이덴티티 제공 | Workload API, 캐싱 |
| Trust Bundle | 신뢰 앵커 | 상대방 SVID 검증 |
| 페더레이션 | 크로스 도메인 신뢰 | 멀티 클러스터 통신 |

### 구현 로드맵

1. **1단계**: 개발 환경에 SPIRE 설치 및 기본 구성
2. **2단계**: 파일럿 워크로드에 SPIFFE 아이덴티티 적용
3. **3단계**: 서비스 메시 통합 (Istio/Cilium/Linkerd)
4. **4단계**: 크로스 클러스터 페더레이션 구성
5. **5단계**: 프로덕션 HA 배포 및 모니터링

### 참고 자료

**공식 문서**:
- [SPIFFE 사양](https://spiffe.io/docs/latest/spiffe-about/overview/)
- [SPIRE 문서](https://spiffe.io/docs/latest/spire-about/)
- [SPIRE Helm 차트](https://github.com/spiffe/helm-charts-hardened)
- [SPIFFE/SPIRE GitHub](https://github.com/spiffe/spire)

**통합 가이드**:
- [Istio + SPIRE 통합](https://istio.io/latest/docs/ops/integrations/spire/)
- [Cilium SPIRE 통합](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/spire/)
- [Envoy SDS 통합](https://spiffe.io/docs/latest/microservices/envoy/)

**AWS 관련**:
- [AWS Private CA with SPIRE](https://aws.amazon.com/blogs/security/using-spiffe-for-workload-identity-on-amazon-eks/)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)

---

> **다음 단계**: [Kubernetes 인증 및 권한 부여](./02-kubernetes-auth-authz.md)에서 RBAC과 함께 SPIFFE 아이덴티티를 활용하는 방법을 학습하세요.
