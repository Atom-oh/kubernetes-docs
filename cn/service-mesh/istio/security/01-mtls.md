# mTLS

双向 TLS（mTLS）是 Istio 的核心安全功能，可自动加密并验证服务间通信。

## 目录

1. [mTLS 概述](#mtls-overview)
2. [mTLS 模式](#mtls-modes)
3. [证书管理](#certificate-management)
4. [PeerAuthentication 配置](#peerauthentication-configuration)
5. [mTLS 与 AWS 服务集成](#mtls-integration-with-aws-services)
6. [使用 mTLS 连接外部服务](#mtls-with-external-services)
7. [迁移策略](#migration-strategy)
8. [常见问题和解决方案](#common-issues-and-solutions)
9. [性能与监控](#performance-and-monitoring)

## mTLS 概述

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/id-prov.svg" alt="Istio 身份供应" width="700">
</p>

Istio 会自动将 mTLS 应用于服务间通信，从而实现零信任网络。

### 基于身份的安全性

Istio 使用 **SPIFFE（Secure Production Identity Framework for Everyone）** 标准为每个工作负载分配强身份：

```
spiffe://cluster.local/ns/default/sa/productpage
  |         |           |     |      |    |
  |         |           |     |      |    +- ServiceAccount name
  |         |           |     |      +----- "sa" (ServiceAccount)
  |         |           |     +------------ Namespace name
  |         |           +------------------ "ns" (Namespace)
  |         +------------------------------ Trust Domain
  +---------------------------------------- Protocol
```

**身份供应流程**：
1. Kubernetes 创建 Pod 并分配 ServiceAccount
2. Istio Agent 在 Pod 内启动
3. Agent 向 Istiod 发送 CSR（Certificate Signing Request）
4. Istiod 基于 SPIFFE ID 签发 X.509 证书
5. Agent 将证书交付给 Envoy（SDS 协议）
6. 自动续期证书（默认 TTL：24 小时）

```mermaid
flowchart LR
    subgraph Pod1["Pod A"]
        App1[Application]
        Envoy1[Envoy<br/>Proxy]
    end

    subgraph Pod2["Pod B"]
        Envoy2[Envoy<br/>Proxy]
        App2[Application]
    end

    Istiod[istiod<br/>Certificate Issuance]

    App1 -->|Plaintext| Envoy1
    Envoy1 <-->|mTLS Encrypted| Envoy2
    Envoy2 -->|Plaintext| App2

    Istiod -.->|Certificate| Envoy1
    Istiod -.->|Certificate| Envoy2

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef control fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Class applications
    class App1,App2 app;
    class Envoy1,Envoy2 proxy;
    class Istiod control;
```

## mTLS 模式

### STRICT 模式（推荐）

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Only mTLS allowed
```

### PERMISSIVE 模式（用于迁移）

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: PERMISSIVE  # Both mTLS and plaintext allowed
```

### DISABLE 模式

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: disable-mtls
  namespace: default
spec:
  mtls:
    mode: DISABLE  # mTLS disabled
```

## 证书管理

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/cert-hierarchy.svg" alt="证书层级" width="600">
</p>

### Istio 默认 CA 证书

Istio 在安装期间自动生成自签名根 CA。上图展示了 Istio 的证书层级：

- **根 CA**：顶级信任锚点
- **中间 CA**：用于签发工作负载证书的中间 CA
- **工作负载证书**：每个服务的 mTLS 证书（自动续期）

```mermaid
flowchart TD
    subgraph IstioCA["Istio CA (istiod)"]
        RootCA[Root CA<br/>Self-signed]
        IntermediateCA[Intermediate CA<br/>Workload Certificate Issuance]
    end

    subgraph Workloads["Workloads"]
        Cert1[Service A<br/>Certificate]
        Cert2[Service B<br/>Certificate]
        Cert3[Service C<br/>Certificate]
    end

    RootCA -->|Sign| IntermediateCA
    IntermediateCA -->|Issue| Cert1
    IntermediateCA -->|Issue| Cert2
    IntermediateCA -->|Issue| Cert3

    %% Style definitions
    classDef ca fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef cert fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class RootCA,IntermediateCA ca;
    class Cert1,Cert2,Cert3 cert;
```

**默认证书属性**：
- 有效期：**90 天**（自动续期：到期前 24 小时）
- 密钥长度：2048 位 RSA
- 签名算法：SHA-256

### 证书验证

```bash
# 1. Check CA certificate
kubectl get secret istio-ca-secret -n istio-system -o yaml

# 2. Check workload certificate
istioctl proxy-config secret <pod-name> -n <namespace>

# 3. Certificate details
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[0].secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -text -noout

# 4. Check certificate expiration date
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[0].secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -dates
```

### 使用自定义 CA 证书

在生产环境中，建议使用企业内部 CA 或公共 CA。

#### 第 1 步：生成 CA 证书和密钥

```bash
# 1. Generate Root CA
openssl genrsa -out root-key.pem 4096

openssl req -new -x509 -days 3650 -key root-key.pem \
  -out root-cert.pem \
  -subj "/C=US/ST=California/L=San Francisco/O=MyOrg/OU=IT/CN=Root CA"

# 2. Generate Intermediate CA
openssl genrsa -out ca-key.pem 4096

openssl req -new -key ca-key.pem -out ca-cert.csr \
  -subj "/C=US/ST=California/L=San Francisco/O=MyOrg/OU=IT/CN=Intermediate CA"

# 3. Sign Intermediate CA with Root CA
cat > ca-extensions.txt <<EOF
basicConstraints=CA:TRUE
keyUsage=keyCertSign,cRLSign
EOF

openssl x509 -req -days 1825 -in ca-cert.csr \
  -CA root-cert.pem -CAkey root-key.pem -CAcreateserial \
  -out ca-cert.pem -extfile ca-extensions.txt

# 4. Create Certificate Chain
cat ca-cert.pem root-cert.pem > cert-chain.pem
```

#### 第 2 步：创建 Kubernetes Secret

```bash
kubectl create secret generic cacerts -n istio-system \
  --from-file=ca-cert.pem=ca-cert.pem \
  --from-file=ca-key.pem=ca-key.pem \
  --from-file=root-cert.pem=root-cert.pem \
  --from-file=cert-chain.pem=cert-chain.pem
```

#### 第 3 步：重启 Istio

```bash
# Restart istiod to load new CA certificate
kubectl rollout restart deployment/istiod -n istio-system

# Restart all workloads to issue new certificates
kubectl rollout restart deployment -n <namespace>
```

#### 第 4 步：验证

```bash
# Verify CA certificate is loaded correctly
kubectl logs -l app=istiod -n istio-system | grep "Use plugged-in cert"

# Verify workload certificates are issued by new CA
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[0].secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -issuer
```

### AWS Certificate Manager（ACM）集成

您可以使用 ACM Private CA 管理 Istio 证书。

#### 第 1 步：创建 ACM Private CA

```bash
# Create ACM Private CA
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_4096,SigningAlgorithm=SHA256WITHRSA,Subject={CommonName=Istio CA}" \
  --certificate-authority-type ROOT \
  --tags Key=Name,Value=istio-root-ca

# Save CA ARN
CA_ARN=$(aws acm-pca list-certificate-authorities \
  --query 'CertificateAuthorities[0].Arn' --output text)

# Generate Root CA certificate
aws acm-pca get-certificate-authority-csr \
  --certificate-authority-arn $CA_ARN \
  --output text > ca.csr

aws acm-pca issue-certificate \
  --certificate-authority-arn $CA_ARN \
  --csr fileb://ca.csr \
  --signing-algorithm SHA256WITHRSA \
  --template-arn arn:aws:acm-pca:::template/RootCACertificate/V1 \
  --validity Value=10,Type=YEARS

# Install certificate
CERT_ARN=$(aws acm-pca list-certificates \
  --certificate-authority-arn $CA_ARN \
  --query 'Certificates[0].Arn' --output text)

aws acm-pca get-certificate \
  --certificate-authority-arn $CA_ARN \
  --certificate-arn $CERT_ARN \
  --output text > root-cert.pem

aws acm-pca import-certificate-authority-certificate \
  --certificate-authority-arn $CA_ARN \
  --certificate fileb://root-cert.pem
```

#### 第 2 步：安装 Cert-Manager + AWS PCA Issuer

```bash
# Install Cert-Manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Install AWS PCA Issuer
helm repo add awspca https://cert-manager.github.io/aws-privateca-issuer
helm install aws-pca-issuer awspca/aws-privateca-issuer -n cert-manager
```

#### 第 3 步：创建 AWSPCAIssuer

```yaml
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAClusterIssuer
metadata:
  name: istio-ca
spec:
  arn: ${CA_ARN}
  region: us-west-2
```

#### 第 4 步：在 Istio 中使用

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: istio-ca-cert
  namespace: istio-system
spec:
  secretName: cacerts
  commonName: "Istio CA"
  isCA: true
  duration: 87600h  # 10 years
  renewBefore: 720h  # 30 days
  issuerRef:
    kind: AWSPCAClusterIssuer
    name: istio-ca
```

### 证书续期策略

```yaml
# Configure certificate policy with Istio Operator
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-control-plane
  namespace: istio-system
spec:
  meshConfig:
    certificates:
      - secretName: dns.istio-system-service-account
        dnsNames:
          - istiod.istio-system.svc
          - istiod.istio-system
    caCertificates:
      - secretName: cacerts
        certProvider: cert-manager
  values:
    pilot:
      env:
        # Workload certificate TTL (default: 24 hours)
        CITADEL_CERT_TTL: "24h"
        # Certificate renewal grace period (default: 15 minutes)
        CITADEL_GRACE_PERIOD: "15m"
```

### 证书轮换

```bash
# 1. Generate new CA certificate (repeat steps above)

# 2. Update existing Secret
kubectl create secret generic cacerts -n istio-system \
  --from-file=ca-cert.pem=new-ca-cert.pem \
  --from-file=ca-key.pem=new-ca-key.pem \
  --from-file=root-cert.pem=new-root-cert.pem \
  --from-file=cert-chain.pem=new-cert-chain.pem \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Restart istiod (zero-downtime rolling update)
kubectl rollout restart deployment/istiod -n istio-system

# 4. Gradual workload certificate renewal
# Method 1: Wait for automatic renewal (within 24 hours)
# Method 2: Manual rolling restart
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  echo "Restarting deployments in namespace: $ns"
  kubectl rollout restart deployment -n $ns
done
```

## PeerAuthentication 配置

### 全局配置

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

### Namespace 级配置

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: namespace-policy
  namespace: production
spec:
  mtls:
    mode: STRICT
```

### 工作负载级配置

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: workload-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: reviews
      version: v1
  mtls:
    mode: STRICT
```

### 端口级配置

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: port-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  mtls:
    mode: STRICT
  portLevelMtls:
    8080:
      mode: DISABLE  # mTLS disabled for port 8080
```

## mTLS 与 AWS 服务集成

### AWS Application Load Balancer（ALB）与 mTLS

ALB 支持基于客户端证书的 mTLS。

```mermaid
flowchart LR
    Client[Client<br/>Client Cert]
    ALB[ALB<br/>mTLS Termination]
    Gateway[Istio Gateway<br/>TLS]
    Service[Backend Service<br/>Envoy mTLS]

    Client <-->|mTLS| ALB
    ALB <-->|TLS| Gateway
    Gateway <-->|mTLS| Service

    %% Style definitions
    classDef aws fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef client fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Client client;
    class ALB aws;
    class Gateway,Service istio;
```

#### 第 1 步：在 ALB 上配置 mTLS

```bash
# 1. Create Trust Store (upload CA certificate)
aws elbv2 create-trust-store \
  --name istio-client-trust-store \
  --ca-certificates-bundle-s3-bucket my-bucket \
  --ca-certificates-bundle-s3-key ca-bundle.pem

# 2. Configure mTLS on ALB listener
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:region:account:listener/app/my-alb/xxx \
  --mutual-authentication Mode=verify,TrustStoreArn=arn:aws:elasticloadbalancing:region:account:truststore/istio-client-trust-store/xxx
```

#### 第 2 步：AWS Load Balancer Controller 配置

```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-gateway
  namespace: istio-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    # mTLS configuration
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/xxx"
    service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy: "ELBSecurityPolicy-TLS13-1-2-2021-06"
    service.beta.kubernetes.io/aws-load-balancer-mutual-authentication: '[{"port": 443, "mode": "verify", "trustStore": "arn:aws:elasticloadbalancing:region:account:truststore/istio-client-trust-store/xxx"}]'
spec:
  type: LoadBalancer
  selector:
    istio: ingressgateway
  ports:
  - name: https
    port: 443
    targetPort: 8443
```

#### 第 3 步：在 Istio Gateway 验证客户端证书

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: public-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 8443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE  # ALB already completed mTLS verification
      credentialName: gateway-cert
    hosts:
    - "*.example.com"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio-envoy-custom
  namespace: istio-system
data:
  custom-bootstrap.yaml: |
    static_resources:
      listeners:
      - name: http_listener
        address:
          socket_address:
            address: 0.0.0.0
            port_value: 8443
        filter_chains:
        - filters:
          - name: envoy.filters.network.http_connection_manager
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
              # Verify client certificate headers forwarded from ALB
              forward_client_cert_details: APPEND_FORWARD
              set_current_client_cert_details:
                subject: true
                cert: true
                chain: true
                dns: true
                uri: true
```

#### 第 4 步：转发客户端证书信息

ALB 会将客户端证书信息作为 HTTP 标头转发：

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: verify-client-cert
  namespace: default
spec:
  action: ALLOW
  rules:
  - when:
    - key: request.headers[x-amzn-mtls-clientcert-serial-number]
      values: ["*"]
    - key: request.headers[x-amzn-mtls-clientcert-subject]
      values: ["CN=trusted-client,O=MyOrg*"]
```

**由 ALB 转发的标头**：
- `X-Amzn-Mtls-Clientcert-Serial-Number`：证书序列号
- `X-Amzn-Mtls-Clientcert-Subject`：证书 Subject DN
- `X-Amzn-Mtls-Clientcert-Issuer`：证书 Issuer DN
- `X-Amzn-Mtls-Clientcert-Validity`：有效期
- `X-Amzn-Mtls-Clientcert-Leaf`：客户端证书（PEM）

### Amazon CloudFront 与 mTLS

CloudFront 支持客户端证书验证。

```mermaid
flowchart LR
    Client[Client<br/>Client Cert]
    CloudFront[CloudFront<br/>mTLS + Edge]
    ALB[ALB<br/>TLS]
    Gateway[Istio Gateway]
    Service[Backend Service<br/>Envoy mTLS]

    Client <-->|mTLS| CloudFront
    CloudFront <-->|TLS| ALB
    ALB <-->|TLS| Gateway
    Gateway <-->|mTLS| Service

    %% Style definitions
    classDef aws fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef client fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Client client;
    class CloudFront,ALB aws;
    class Gateway,Service istio;
```

#### 第 1 步：创建 CloudFront Distribution

```bash
# 1. Upload Trust Store (CA certificate) to S3
aws s3 cp ca-bundle.pem s3://my-bucket/ca-bundle.pem

# 2. Create CloudFront distribution
cat > cloudfront-config.json <<EOF
{
  "CallerReference": "istio-mtls-$(date +%s)",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "istio-gateway",
        "DomainName": "k8s-istiosystem-istiogateway-xxx.elb.us-west-2.amazonaws.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only",
          "OriginSslProtocols": {
            "Quantity": 1,
            "Items": ["TLSv1.2"]
          }
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "istio-gateway",
    "ViewerProtocolPolicy": "https-only",
    "TrustedSigners": {
      "Enabled": false,
      "Quantity": 0
    },
    "ForwardedValues": {
      "QueryString": true,
      "Headers": {
        "Quantity": 1,
        "Items": ["*"]
      }
    },
    "MinTTL": 0
  },
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": false,
    "ACMCertificateArn": "arn:aws:acm:us-east-1:account:certificate/xxx",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  }
}
EOF

aws cloudfront create-distribution --distribution-config file://cloudfront-config.json

# 3. Configure mTLS on CloudFront
DIST_ID=$(aws cloudfront list-distributions --query 'DistributionList.Items[0].Id' --output text)

aws cloudfront update-distribution \
  --id $DIST_ID \
  --distribution-config '{
    "ViewerCertificate": {
      "ACMCertificateArn": "arn:aws:acm:us-east-1:account:certificate/xxx",
      "SSLSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021",
      "CertificateSource": "acm"
    },
    "CustomOriginConfig": {
      "OriginSslProtocols": {
        "Quantity": 1,
        "Items": ["TLSv1.2"]
      }
    }
  }'
```

#### 第 2 步：使用 CloudFront Function 验证证书

```javascript
function handler(event) {
    var request = event.request;
    var headers = request.headers;

    // Headers forwarded by CloudFront after client certificate verification
    var clientCertSerial = headers['cloudfront-viewer-tls-client-cert-serial-number'];
    var clientCertSubject = headers['cloudfront-viewer-tls-client-cert-subject'];

    if (!clientCertSerial || !clientCertSubject) {
        return {
            statusCode: 403,
            statusDescription: 'Forbidden',
            body: 'Client certificate required'
        };
    }

    // Check allowed certificate serial numbers
    var allowedSerials = ['1234567890ABCDEF', 'FEDCBA0987654321'];
    if (!allowedSerials.includes(clientCertSerial.value)) {
        return {
            statusCode: 403,
            statusDescription: 'Forbidden',
            body: 'Invalid client certificate'
        };
    }

    // Forward certificate information to Istio
    headers['x-client-cert-serial'] = clientCertSerial;
    headers['x-client-cert-subject'] = clientCertSubject;

    return request;
}
```

#### 第 3 步：在 Istio 中验证 CloudFront 标头

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: verify-cloudfront-client-cert
  namespace: default
spec:
  action: ALLOW
  rules:
  - when:
    - key: request.headers[x-client-cert-serial]
      values:
      - "1234567890ABCDEF"
      - "FEDCBA0987654321"
    - key: request.headers[x-client-cert-subject]
      values: ["CN=trusted-client,O=MyOrg*"]
```

### 端到端 mTLS 架构

从客户端到后端的整个路径均使用 mTLS：

```mermaid
flowchart TB
    Client[Client<br/>Client Cert]

    subgraph AWS ["AWS Edge"]
        CF[CloudFront<br/>mTLS Verification]
        ALB[ALB<br/>Header Forwarding]
    end

    subgraph EKS ["EKS Cluster"]
        Gateway[Istio Gateway<br/>Header Validation]

        subgraph Mesh ["Service Mesh"]
            ServiceA[Service A<br/>Envoy mTLS]
            ServiceB[Service B<br/>Envoy mTLS]
            ServiceC[Service C<br/>Envoy mTLS]
        end
    end

    Client <-->|1\. mTLS| CF
    CF -->|2\. TLS + Headers| ALB
    ALB -->|3\. TLS + Headers| Gateway
    Gateway <-->|4\. mTLS| ServiceA
    ServiceA <-->|5\. mTLS| ServiceB
    ServiceB <-->|6\. mTLS| ServiceC

    %% Style definitions
    classDef client fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef aws fill:#FF9900,stroke:#333,stroke-width:2px,color:black;
    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;

    %% Class applications
    class Client client;
    class CF,ALB aws;
    class Gateway,ServiceA,ServiceB,ServiceC istio;
```

**各段的安全性**：
1. **客户端 -> CloudFront**：mTLS（客户端证书验证）
2. **CloudFront -> ALB**：TLS + 证书信息标头
3. **ALB -> Istio Gateway**：TLS + 证书信息标头
4. **Istio Mesh 内部**：自动 mTLS（Envoy 到 Envoy）

## 使用 mTLS 连接外部服务

### 旧版系统集成

```yaml
# When legacy system doesn't support mTLS
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: legacy-system
  namespace: default
spec:
  host: legacy.external.com
  trafficPolicy:
    tls:
      mode: SIMPLE  # Use one-way TLS only
---
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: legacy-system
  namespace: default
spec:
  hosts:
  - legacy.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 外部 API mTLS 客户端认证

当 Istio 需要向外部 API 出示客户端证书时：

```yaml
# 1. Create client certificate Secret
apiVersion: v1
kind: Secret
metadata:
  name: client-mtls-credential
  namespace: istio-system
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
  ca.crt: <base64-encoded-ca>
---
# 2. Configure client certificate in DestinationRule
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: external-api-mtls
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    tls:
      mode: MUTUAL  # Use mTLS
      clientCertificate: /etc/certs/tls.crt
      privateKey: /etc/certs/tls.key
      caCertificates: /etc/certs/ca.crt
---
# 3. Register external API with ServiceEntry
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 通过 Egress Gateway 使用外部 mTLS

```yaml
# 1. Deploy Egress Gateway
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    egressGateways:
    - name: istio-egressgateway
      enabled: true
      k8s:
        serviceAnnotations:
          networking.istio.io/exportTo: "*"
---
# 2. Gateway resource
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-gateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - api.external.com
    tls:
      mode: ISTIO_MUTUAL  # mTLS inside mesh
---
# 3. Route traffic with VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-through-egress
  namespace: default
spec:
  hosts:
  - api.external.com
  gateways:
  - mesh  # From inside mesh
  - istio-system/egress-gateway  # To Egress Gateway
  http:
  - match:
    - gateways:
      - mesh
      port: 443
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/egress-gateway
      port: 443
    route:
    - destination:
        host: api.external.com
        port:
          number: 443
---
# 4. DestinationRule (from Egress Gateway to external)
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: external-api-mtls
  namespace: istio-system
spec:
  host: api.external.com
  trafficPolicy:
    tls:
      mode: MUTUAL
      clientCertificate: /etc/istio/egress-certs/tls.crt
      privateKey: /etc/istio/egress-certs/tls.key
      caCertificates: /etc/istio/egress-certs/ca.crt
```

## 迁移策略

### 第 1 步：检查当前状态

```bash
# Check current mTLS configuration
kubectl get peerauthentication -A

# Check mTLS status by service
istioctl authn tls-check <pod-name> -n <namespace>
```

### 第 2 步：切换到 PERMISSIVE 模式

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: PERMISSIVE  # Allow both mTLS and plaintext
```

### 第 3 步：监控

```bash
# Verify mTLS connections
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep ssl

# Verify plaintext connections
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep plaintext
```

### 第 4 步：切换到 STRICT 模式

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Only mTLS allowed
```

## 常见问题和解决方案

### 1. mTLS 连接失败

**症状**：
```
upstream connect error or disconnect/reset before headers. reset reason: connection failure
```

**根因分析**：

```bash
# 1. Check PeerAuthentication
kubectl get peerauthentication -A

# 2. Check DestinationRule mTLS mode
kubectl get destinationrule -A -o yaml | grep -A 5 "trafficPolicy"

# 3. Check certificates
istioctl proxy-config secret <pod-name> -n <namespace>

# 4. Verify TLS connection
istioctl authn tls-check <source-pod> <dest-service> -n <namespace>

# 5. Check Envoy logs in detail
kubectl logs <pod-name> -c istio-proxy -n <namespace> | grep -E "(TLS|SSL|certificate)"
```

**解决方案**：

1. **PeerAuthentication 与 DestinationRule 不匹配**：
```yaml
# Problem: PeerAuthentication is STRICT, DestinationRule is DISABLE
# Solution: Change DestinationRule to ISTIO_MUTUAL
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: fix-mtls
spec:
  host: myservice.default.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL  # Match STRICT mode
```

2. **未注入 sidecar 的 Pod**：
```bash
# Add istio-injection label to namespace
kubectl label namespace default istio-injection=enabled

# Restart pod
kubectl rollout restart deployment/<deployment-name> -n default
```

### 2. 证书过期问题

**症状**：
```
TLS error: Secret is not supplied by SDS
x509: certificate has expired
```

**检查证书到期时间**：

```bash
# Check workload certificate expiration date
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[0].secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -dates

# Check CA certificate expiration
kubectl get secret istio-ca-secret -n istio-system -o json | \
  jq -r '.data."ca-cert.pem"' | base64 -d | openssl x509 -noout -dates

# Check certificate expiration for all workloads
for pod in $(kubectl get pods -n default -o jsonpath='{.items[*].metadata.name}'); do
  echo "Pod: $pod"
  istioctl proxy-config secret $pod -n default -o json 2>/dev/null | \
    jq -r '.dynamicActiveSecrets[0].secret.tlsCertificate.certificateChain.inlineBytes' | \
    base64 -d 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "No cert found"
done
```

**解决方案**：

```bash
# 1. Restart istiod (trigger new certificate issuance)
kubectl rollout restart deployment/istiod -n istio-system

# 2. Restart specific workload (renew certificate)
kubectl delete pod <pod-name> -n <namespace>

# 3. Renew CA certificate (see "Certificate Rotation" section above)
```

### 3. 时钟偏差（时间同步问题）

**症状**：
```
certificate is not valid yet
certificate verify failed
```

**原因**：Pod/节点之间的时间差导致证书验证失败

**验证**：

```bash
# Check node time
kubectl get nodes -o wide
for node in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do
  echo "Node: $node"
  kubectl debug node/$node -it --image=busybox -- date
done

# Check pod time
kubectl exec -it <pod-name> -c istio-proxy -n <namespace> -- date

# Check time difference (acceptable range: +/- 5 minutes)
```

**解决方案**：

```bash
# 1. NTP configuration (node level)
sudo systemctl restart chrony
sudo chronyc tracking

# 2. NTP sync is default on EKS
# Verify Amazon Time Sync Service usage
curl http://169.254.169.123/latest/meta-data/system

# 3. Add grace period to certificate start time
# Istio Operator configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    pilot:
      env:
        CERT_NOTBEFORE_GRACE_DURATION: "10m"  # Start time grace period
```

### 4. 循环依赖

**症状**：
```
upstream connect error or disconnect/reset before headers
```

**原因**：Service A -> Service B -> Service A 调用期间的 mTLS 握手超时

**验证**：

```bash
# Check service call chain
istioctl analyze -n <namespace>

# Check Envoy clusters
istioctl proxy-config cluster <pod-name> -n <namespace>
```

**解决方案**：

```yaml
# Set appropriate timeout in DestinationRule
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: service-with-timeout
spec:
  host: myservice.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 30s  # Increase connection timeout
    tls:
      mode: ISTIO_MUTUAL
```

### 5. 混合协议（mTLS + 明文）

**症状**：
```
SSL routines:OPENSSL_internal:WRONG_VERSION_NUMBER
```

**原因**：部分服务使用 mTLS，其他服务使用明文

**验证**：

```bash
# Check mTLS status for all services
for svc in $(kubectl get svc -n default -o jsonpath='{.items[*].metadata.name}'); do
  echo "Service: $svc"
  istioctl authn tls-check $(kubectl get pod -n default -l app=test -o jsonpath='{.items[0].metadata.name}') $svc.default.svc.cluster.local -n default
done
```

**解决方案**：

```yaml
# Gradual migration with PERMISSIVE mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: migration-policy
  namespace: default
spec:
  mtls:
    mode: PERMISSIVE  # Allow both mTLS and plaintext
```

### 6. Headless Service mTLS

**症状**：headless Service 上的 mTLS 连接失败

**解决方案**：

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: headless-service-mtls
spec:
  host: headless-service.default.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    portLevelSettings:
    - port:
        number: 3306
      tls:
        mode: ISTIO_MUTUAL
```

### 7. mTLS 与 NetworkPolicy 冲突

**症状**：应用 NetworkPolicy 后 mTLS 连接失败

**解决方案**：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-istio-mtls
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: istio-system  # Allow istiod
    - podSelector: {}  # Allow pods in same namespace
    ports:
    - protocol: TCP
      port: 15008  # Envoy mTLS port
    - protocol: TCP
      port: 15012  # Pilot discovery
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: istio-system
    ports:
    - protocol: TCP
      port: 15012
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 15008
```

## 性能与监控

### mTLS 性能影响

| 指标 | 明文 | mTLS | 增幅 |
|--------|-----------|------|----------|
| **延迟（p50）** | 5ms | 6ms | +20% |
| **延迟（p99）** | 15ms | 18ms | +20% |
| **CPU 使用率** | 10% | 15% | +50% |
| **内存使用量** | 100MB | 120MB | +20% |
| **吞吐量（RPS）** | 10000 | 8500 | -15% |

**优化方法**：

1. **硬件加速（AES-NI）**：
```bash
# Check AES-NI support on CPU
grep -m1 -o aes /proc/cpuinfo

# Recommended EC2 instance types:
# - c5.*, c6i.*, c7g.*: AES-NI supported
# - m5.*, m6i.*, r5.*: General purpose
```

2. **使用 TLS 1.3**（更快的握手）：
```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        TLS_MIN_PROTOCOL_VERSION: TLSv1_3
```

3. **连接池**：
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: connection-pool
spec:
  host: myservice.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30ms
      http:
        http1MaxPendingRequests: 1024
        http2MaxRequests: 1024
        maxRequestsPerConnection: 10
        idleTimeout: 900s
```

### Prometheus 指标

**mTLS 连接指标**：

```promql
# mTLS connection success rate
sum(rate(istio_tcp_connections_opened_total{connection_security_policy="mutual_tls"}[5m])) by (destination_service_name)
/
sum(rate(istio_tcp_connections_opened_total[5m])) by (destination_service_name)

# mTLS handshake time (p99)
histogram_quantile(0.99,
  sum(rate(envoy_listener_ssl_connection_handshake_duration_bucket[5m])) by (le)
)

# Days until first certificate expires
envoy_server_days_until_first_cert_expiring

# mTLS error rate
sum(rate(istio_requests_total{response_code=~"5.*",connection_security_policy="mutual_tls"}[5m]))
/
sum(rate(istio_requests_total{connection_security_policy="mutual_tls"}[5m]))
```

### Grafana 仪表板

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio-mtls-dashboard
  namespace: istio-system
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "Istio mTLS Monitoring",
        "panels": [
          {
            "title": "mTLS Connection Success Rate",
            "targets": [{
              "expr": "sum(rate(istio_tcp_connections_opened_total{connection_security_policy=\"mutual_tls\"}[5m])) / sum(rate(istio_tcp_connections_opened_total[5m]))"
            }]
          },
          {
            "title": "Certificate Expiration",
            "targets": [{
              "expr": "envoy_server_days_until_first_cert_expiring"
            }]
          },
          {
            "title": "mTLS Handshake Duration (p99)",
            "targets": [{
              "expr": "histogram_quantile(0.99, sum(rate(envoy_listener_ssl_connection_handshake_duration_bucket[5m])) by (le))"
            }]
          }
        ]
      }
    }
```

### 证书过期告警

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-cert-expiration-alert
  namespace: istio-system
spec:
  groups:
  - name: istio-certificates
    interval: 30s
    rules:
    - alert: IstioCertificateExpiringSoon
      expr: envoy_server_days_until_first_cert_expiring < 7
      for: 1h
      labels:
        severity: warning
      annotations:
        summary: "Istio certificate expiring in {{ $value }} days"
        description: "Certificate for {{ $labels.pod }} will expire in {{ $value }} days"

    - alert: IstioCertificateExpired
      expr: envoy_server_days_until_first_cert_expiring < 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Istio certificate has expired"
        description: "Certificate for {{ $labels.pod }} has expired"

    - alert: IstioMTLSConnectionFailure
      expr: |
        sum(rate(istio_requests_total{response_code=~"5.*",connection_security_policy="mutual_tls"}[5m]))
        /
        sum(rate(istio_requests_total{connection_security_policy="mutual_tls"}[5m])) > 0.05
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High mTLS connection failure rate"
        description: "mTLS error rate is {{ $value | humanizePercentage }} for {{ $labels.destination_service_name }}"
```

### 日志记录与调试

```bash
# 1. Change Envoy log level dynamically
istioctl proxy-config log <pod-name> -n <namespace> --level connection:debug,tls:debug

# 2. Filter mTLS-related logs
kubectl logs <pod-name> -c istio-proxy -n <namespace> | grep -E "(TLS|SSL|certificate|handshake)"

# 3. Check certificates from Envoy Admin Interface
kubectl exec -it <pod-name> -c istio-proxy -n <namespace> -- \
  curl -s localhost:15000/certs | jq '.'

# 4. TLS connection statistics
kubectl exec -it <pod-name> -c istio-proxy -n <namespace> -- \
  curl -s localhost:15000/stats | grep ssl

# 5. Real-time mTLS traffic verification
istioctl dashboard envoy <pod-name>.<namespace>
# Check ssl metrics at http://localhost:15000/stats/prometheus
```

### 最佳实践

1. **生产环境**：
   - 使用 STRICT 模式
   - 使用自定义 CA 证书
   - 配置自动证书续期
   - 设置到期告警

2. **性能优化**：
   - 使用 TLS 1.3
   - 启用连接池
   - 使用支持 AES-NI 的实例

3. **监控**：
   - 跟踪证书到期时间
   - 监控 mTLS 连接成功率
   - 跟踪握手延迟

4. **安全性**：
   - 定期轮换 CA
   - 最小权限原则
   - 与 NetworkPolicy 配合使用

## 参考资料

- [Istio mTLS](https://istio.io/latest/docs/concepts/security/#mutual-tls-authentication)
- [PeerAuthentication 参考](https://istio.io/latest/docs/reference/config/security/peer_authentication/)
- [DestinationRule TLS](https://istio.io/latest/docs/reference/config/networking/destination-rule/#ClientTLSSettings)
- [Cert-Manager](https://cert-manager.io/docs/)
- [AWS Certificate Manager](https://docs.aws.amazon.com/acm/)
- [AWS ALB mTLS](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/mutual-authentication.html)
